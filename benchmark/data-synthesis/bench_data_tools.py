#!/usr/bin/env python3
"""
bench_data_tools.py — MetaClaw Evolution Benchmark 数据制造工具

子命令：
  init      创建弧目录骨架，生成 UUID，创建 benchmark 输出目录结构
  validate  验证单天 session + questions.json 格式
  count     估算 token 量（含 runner 注入后的完整对话）
  preview   展示 agent 实际收到的消息序列（全对 / 全错两条路径）

路径约定（均相对于本脚本所在目录的上级，即项目根目录）：
  benchmark data:  benchmark/data/metaclaw-bench/
  data-synthesis:  data-synthesis/              ← 本脚本所在目录
  data-spec:       data-spec/
"""

from __future__ import annotations

import argparse
import json
import uuid
from pathlib import Path

# ---------------------------------------------------------------------------
# 路径配置
# ---------------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = SCRIPT_DIR.parent
DEFAULT_BENCH_DATA_DIR = PROJECT_ROOT / "benchmark" / "data" / "metaclaw-bench"

# ---------------------------------------------------------------------------
# 弧-天映射（6 弧 × 5 天 = 30 天）
# ---------------------------------------------------------------------------

ARC_LETTERS = list("ABCDEF")
AGENT_ID = "metaclaw_agent"


def arc_days(arc: str) -> list[int]:
    """返回弧对应的天编号列表（1-indexed，如弧 A → [1,2,3,4,5]）"""
    idx = ARC_LETTERS.index(arc.upper())
    start = idx * 5 + 1
    return list(range(start, start + 5))


def day_str(n: int) -> str:
    return f"day{n:02d}"


def arc_from_day(n: int) -> str:
    return ARC_LETTERS[(n - 1) // 5]


# ---------------------------------------------------------------------------
# Feedback 注入（与 runner 行为一致，见 data-structure.md）
# ---------------------------------------------------------------------------

FEEDBACK_PREFIX = "[上一步反馈] {feedback}\n\n{question}"
FEEDBACK_ONLY = "[上一步反馈] {feedback}"


def build_multi_choice_feedback(agent_selected: set[str], round_record: dict) -> tuple[bool, str]:
    """
    生成 multi_choice 的 feedback_text。
    返回 (passed, feedback_text)。

    - 精确匹配 → (True, feedback.correct)
    - 否则 → (False, 漏选+错选的 per-option 解释拼接)
    """
    correct = set(round_record.get("eval", {}).get("answer", []))
    passed = agent_selected == correct
    if passed:
        return True, round_record.get("feedback", {}).get("correct", "")

    options_fb = round_record.get("feedback", {}).get("options", {})
    lines = []
    missed = correct - agent_selected          # 应选未选
    wrong = agent_selected - correct           # 不该选但选了
    for opt in sorted(missed):
        lines.append(f"你漏选了 {opt}：{options_fb.get(opt, '')}")
    for opt in sorted(wrong):
        lines.append(f"你错选了 {opt}：{options_fb.get(opt, '')}")
    return False, "\n".join(lines)


def build_injected_messages(rounds: list[dict], assume_correct: bool) -> list[str]:
    """
    模拟 runner 的 feedback 注入，返回完整消息列表。

    返回值长度 = len(rounds) + 1（最后一条是 standalone feedback）。
    assume_correct=True  → 每轮精确匹配路径（feedback.correct）
    assume_correct=False → 每轮错误路径：
        - file_check: feedback.incorrect
        - multi_choice: 模拟 agent 选了所有错误选项（不在 answer 中的选项）
    """
    messages = []
    prev_feedback: str | None = None

    for r in rounds:
        question = r["question"]
        rtype = r.get("type")

        if assume_correct:
            feedback_text = r.get("feedback", {}).get("correct", "")
        elif rtype == "multi_choice":
            all_opts = set(r.get("eval", {}).get("options", {}).keys())
            correct_opts = set(r.get("eval", {}).get("answer", []))
            wrong_opts = all_opts - correct_opts   # 模拟只选错误选项
            _, feedback_text = build_multi_choice_feedback(wrong_opts, r)
        else:
            feedback_text = r.get("feedback", {}).get("incorrect", "")

        if prev_feedback:
            msg = FEEDBACK_PREFIX.format(feedback=prev_feedback, question=question)
        else:
            msg = question

        messages.append(msg)
        prev_feedback = feedback_text

    # 最后一轮结束后的 standalone feedback
    if prev_feedback:
        messages.append(FEEDBACK_ONLY.format(feedback=prev_feedback))

    return messages


# ---------------------------------------------------------------------------
# Token 计数（tiktoken 优先，无则 char/4 估算）
# ---------------------------------------------------------------------------

def make_token_counter():
    try:
        import tiktoken
        enc = tiktoken.get_encoding("cl100k_base")
        return lambda text: len(enc.encode(text)), "tiktoken cl100k_base"
    except ImportError:
        return lambda text: len(text) // 4, "char/4 (tiktoken not installed)"


# ---------------------------------------------------------------------------
# 子命令：init
# ---------------------------------------------------------------------------

def cmd_init(args):
    arc = args.arc.upper()
    if arc not in ARC_LETTERS:
        print(f"Error: invalid arc '{arc}', must be one of A–F")
        return

    bench_data_dir = Path(args.bench_data_dir)
    synth_arc_dir = SCRIPT_DIR / f"arc-{arc}"
    days = arc_days(arc)

    # 1. 创建 data-synthesis/arc-X/dayXX/ 工作目录
    for d in days:
        (synth_arc_dir / day_str(d)).mkdir(parents=True, exist_ok=True)
    print(f"[init] Created data-synthesis/arc-{arc}/day{days[0]:02d}/ – day{days[-1]:02d}/")

    # 2. 生成 UUID，保存到 uuid_registry.json
    registry_path = synth_arc_dir / "uuid_registry.json"
    if registry_path.exists() and not args.force:
        print(f"[init] uuid_registry.json already exists (use --force to regenerate)")
        registry = json.loads(registry_path.read_text())
    else:
        registry = {day_str(d): str(uuid.uuid4()) for d in days}
        registry_path.write_text(json.dumps(registry, indent=2, ensure_ascii=False) + "\n")
        print(f"[init] Generated UUIDs → {registry_path}")

    for ds, uid in registry.items():
        print(f"       {ds}: {uid}")

    # 3. 创建 benchmark data 输出目录结构
    for d in days:
        ds = day_str(d)
        (bench_data_dir / "eval" / ds).mkdir(parents=True, exist_ok=True)
        (bench_data_dir / "workspaces" / "shared" / ds).mkdir(parents=True, exist_ok=True)

    sessions_dir = bench_data_dir / "openclaw_state" / "agents" / AGENT_ID / "sessions"
    sessions_dir.mkdir(parents=True, exist_ok=True)

    agent_dir = bench_data_dir / "openclaw_state" / "agents" / AGENT_ID / "agent"
    agent_dir.mkdir(parents=True, exist_ok=True)

    print(f"[init] Created output dirs under: {bench_data_dir}")
    print(f"       eval/day{days[0]:02d}/ – eval/day{days[-1]:02d}/")
    print(f"       workspaces/shared/day{days[0]:02d}/ – workspaces/shared/day{days[-1]:02d}/")
    print(f"       openclaw_state/agents/{AGENT_ID}/sessions/")

    # 4. 提示共享 workspace 文件
    shared_dir = bench_data_dir / "workspaces" / "shared"
    required_shared = ["AGENTS.md", "IDENTITY.md", "SOUL.md", "TOOLS.md", "USER.md"]
    missing = [f for f in required_shared if not (shared_dir / f).exists()]
    if missing:
        print(f"\n[init] Note: shared workspace files not yet created: {missing}")
        print(f"       Create these once for the whole benchmark (not per arc).")

    # 5. 创建 all_tests.json 骨架（仅首次）
    all_tests_path = bench_data_dir / "all_tests.json"
    if not all_tests_path.exists():
        skeleton = {
            "name": "MetaClaw-Evolution-Bench",
            "openclaw_state_dir": str(bench_data_dir / "openclaw_state"),
            "eval_dir": str(bench_data_dir / "eval"),
            "workspace_src": str(bench_data_dir / "workspaces" / "shared"),
            "test": [],
        }
        all_tests_path.write_text(json.dumps(skeleton, indent=2, ensure_ascii=False) + "\n")
        print(f"\n[init] Created skeleton all_tests.json → {all_tests_path}")
    else:
        print(f"\n[init] all_tests.json already exists, not modified.")

    print(f"\n[init] Arc {arc} initialized. Next: follow data-spec/arc-{arc}/GUIDE.md")


# ---------------------------------------------------------------------------
# 子命令：validate
# ---------------------------------------------------------------------------

VALID_TYPES = {"multi_choice", "file_check"}


def validate_session(session_path: Path) -> list[str]:
    errors = []
    if not session_path.exists():
        return [f"file not found: {session_path}"]

    lines = [l.strip() for l in session_path.read_text(encoding="utf-8").splitlines() if l.strip()]

    if len(lines) < 2:
        errors.append(f"has {len(lines)} line(s), expected 2–4")
        return errors
    if len(lines) > 4:
        errors.append(f"has {len(lines)} lines, expected 2–4")

    parsed = []
    for i, line in enumerate(lines, 1):
        try:
            parsed.append(json.loads(line))
        except json.JSONDecodeError as e:
            errors.append(f"line {i}: invalid JSON — {e}")
            return errors

    for i, obj in enumerate(parsed):
        if "role" not in obj:
            errors.append(f"line {i+1}: missing 'role'")
        if "content" not in obj:
            errors.append(f"line {i+1}: missing 'content'")

    if parsed and parsed[0].get("role") != "user":
        errors.append(f"first line role must be 'user', got '{parsed[0].get('role')}'")

    roles = [obj.get("role") for obj in parsed]
    for i in range(1, len(roles)):
        expected = "assistant" if roles[i - 1] == "user" else "user"
        if roles[i] != expected:
            errors.append(f"line {i+2}: expected role='{expected}', got '{roles[i]}'")

    return errors


def validate_questions(q_path: Path) -> list[str]:
    errors = []
    if not q_path.exists():
        return [f"file not found: {q_path}"]

    try:
        q = json.loads(q_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return [f"invalid JSON: {e}"]

    for field in ("id", "desc", "rounds"):
        if field not in q:
            errors.append(f"missing top-level field '{field}'")

    rounds = q.get("rounds")
    if not rounds:
        errors.append("'rounds' is empty or missing")
        return errors

    seen_ids: set[str] = set()
    for i, r in enumerate(rounds):
        prefix = f"rounds[{i}] (id={r.get('id', '?')!r})"

        for field in ("id", "type", "question", "feedback", "eval"):
            if field not in r:
                errors.append(f"{prefix}: missing field '{field}'")

        rid = r.get("id")
        if rid:
            if rid in seen_ids:
                errors.append(f"{prefix}: duplicate round id")
            seen_ids.add(rid)

        rtype = r.get("type")
        if rtype and rtype not in VALID_TYPES:
            errors.append(f"{prefix}: invalid type '{rtype}', valid: {sorted(VALID_TYPES)}")

        feedback = r.get("feedback") or {}
        if rtype == "multi_choice":
            if "correct" not in feedback:
                errors.append(f"{prefix}: missing feedback.correct")
            opts_fb = feedback.get("options")
            if not opts_fb or not isinstance(opts_fb, dict):
                errors.append(f"{prefix}: feedback.options must be a non-empty dict")
            else:
                for k, v in opts_fb.items():
                    if not v:
                        errors.append(f"{prefix}: feedback.options[{k!r}] is empty")
        else:
            for key in ("correct", "incorrect"):
                if key not in feedback:
                    errors.append(f"{prefix}: missing feedback.{key}")

        ev = r.get("eval") or {}
        if rtype == "multi_choice":
            opts = ev.get("options", {})
            if len(opts) < 2:
                errors.append(f"{prefix}: eval.options must have >= 2 entries, got {len(opts)}")
            answer = ev.get("answer")
            if not answer:
                errors.append(f"{prefix}: eval.answer is missing or empty")
            else:
                for a in answer:
                    if a not in opts:
                        errors.append(f"{prefix}: answer key '{a}' not in eval.options")
            # feedback.options keys must match eval.options keys
            opts_fb = (r.get("feedback") or {}).get("options", {})
            if opts_fb and opts:
                for k in opts:
                    if k not in opts_fb:
                        errors.append(f"{prefix}: feedback.options missing key '{k}' (present in eval.options)")
                for k in opts_fb:
                    if k not in opts:
                        errors.append(f"{prefix}: feedback.options has extra key '{k}' (not in eval.options)")
        elif rtype == "file_check":
            if "command" not in ev:
                errors.append(f"{prefix}: eval.command is missing")

    return errors


def cmd_validate(args):
    bench_data_dir = Path(args.bench_data_dir)
    sessions_dir = bench_data_dir / "openclaw_state" / "agents" / AGENT_ID / "sessions"

    days_to_check: list[int]
    if args.day:
        days_to_check = [int(args.day)]
    elif args.arc:
        days_to_check = arc_days(args.arc.upper())
    else:
        print("Error: specify --day N or --arc X")
        return

    all_passed = True
    for d in days_to_check:
        ds = day_str(d)
        print(f"\n{'─' * 52}")
        print(f"  {ds}")
        print(f"{'─' * 52}")

        # session
        session_files = sorted(sessions_dir.glob(f"{ds}_*.jsonl")) if sessions_dir.exists() else []
        if not session_files:
            print(f"  [session]   ERROR: no file matching {ds}_*.jsonl")
            all_passed = False
        else:
            errs = validate_session(session_files[0])
            if errs:
                print(f"  [session]   FAILED ({session_files[0].name})")
                for e in errs:
                    print(f"              - {e}")
                all_passed = False
            else:
                print(f"  [session]   OK    ({session_files[0].name})")

        # questions.json
        q_path = bench_data_dir / "eval" / ds / "questions.json"
        errs = validate_questions(q_path)
        if errs:
            print(f"  [questions] FAILED")
            for e in errs:
                print(f"              - {e}")
            all_passed = False
        else:
            q = json.loads(q_path.read_text(encoding="utf-8"))
            rounds = q.get("rounds", [])
            type_counts = {}
            for r in rounds:
                t = r.get("type", "?")
                type_counts[t] = type_counts.get(t, 0) + 1
            summary = ", ".join(f"{v}×{k}" for k, v in sorted(type_counts.items()))
            print(f"  [questions] OK    ({len(rounds)} rounds: {summary})")

    print(f"\n{'=' * 52}")
    if all_passed:
        print("  All validations PASSED.")
    else:
        print("  Some validations FAILED. See errors above.")
    print(f"{'=' * 52}")


# ---------------------------------------------------------------------------
# 子命令：count
# ---------------------------------------------------------------------------

def cmd_count(args):
    bench_data_dir = Path(args.bench_data_dir)
    count_tokens, method = make_token_counter()
    print(f"Token counting method: {method}\n")

    if args.day:
        days_to_check = [int(args.day)]
    elif args.arc:
        days_to_check = arc_days(args.arc.upper())
    else:
        # 统计所有已存在的 eval/dayXX 目录
        eval_dir = bench_data_dir / "eval"
        days_to_check = []
        if eval_dir.exists():
            for p in sorted(eval_dir.iterdir()):
                if p.is_dir() and p.name.startswith("day"):
                    try:
                        days_to_check.append(int(p.name[3:]))
                    except ValueError:
                        pass

    sessions_dir = bench_data_dir / "openclaw_state" / "agents" / AGENT_ID / "sessions"
    rows = []

    for d in days_to_check:
        ds = day_str(d)

        # session init tokens
        s_files = sorted(sessions_dir.glob(f"{ds}_*.jsonl")) if sessions_dir.exists() else []
        session_tokens = count_tokens(s_files[0].read_text(encoding="utf-8")) if s_files else 0

        # workspace/dayXX 文件 tokens
        ws_dir = bench_data_dir / "workspaces" / "shared" / ds
        ws_tokens = 0
        if ws_dir.exists():
            for fp in ws_dir.rglob("*"):
                if fp.is_file():
                    ws_tokens += count_tokens(fp.read_text(encoding="utf-8", errors="replace"))

        # questions.json → 模拟完整注入对话（全错路径，最长）
        q_path = bench_data_dir / "eval" / ds / "questions.json"
        injected_tokens = 0
        n_rounds = 0
        if q_path.exists():
            rounds = json.loads(q_path.read_text(encoding="utf-8")).get("rounds", [])
            n_rounds = len(rounds)
            msgs = build_injected_messages(rounds, assume_correct=False)
            injected_tokens = sum(count_tokens(m) for m in msgs)

        total = session_tokens + ws_tokens + injected_tokens
        rows.append((ds, n_rounds, session_tokens, ws_tokens, injected_tokens, total))

    hdr = f"{'Day':<8} {'Rnds':>5} {'Session':>8} {'Workspace':>10} {'Injected':>9} {'Total':>8}"
    sep = "─" * 56
    print(hdr)
    print(sep)
    for ds, nr, st, wt, it, tot in rows:
        warn = "  ⚠ >20k" if tot > 20_000 else ""
        print(f"{ds:<8} {nr:>5} {st:>8,} {wt:>10,} {it:>9,} {tot:>8,}{warn}")
    print(sep)
    print(
        f"{'TOTAL':<8} {sum(r[1] for r in rows):>5} "
        f"{sum(r[2] for r in rows):>8,} "
        f"{sum(r[3] for r in rows):>10,} "
        f"{sum(r[4] for r in rows):>9,} "
        f"{sum(r[5] for r in rows):>8,}"
    )
    print()
    print("Note: 'Injected' = all questions + all feedback texts (full-incorrect path).")
    print("      Agent responses are NOT counted (unknown until inference).")
    print("      MetaClaw context window: 20,000 tokens.")


# ---------------------------------------------------------------------------
# 子命令：preview
# ---------------------------------------------------------------------------

def cmd_preview(args):
    bench_data_dir = Path(args.bench_data_dir)
    d = int(args.day)
    ds = day_str(d)

    q_path = bench_data_dir / "eval" / ds / "questions.json"
    if not q_path.exists():
        print(f"Error: {q_path} not found")
        return

    rounds = json.loads(q_path.read_text(encoding="utf-8")).get("rounds", [])
    sessions_dir = bench_data_dir / "openclaw_state" / "agents" / AGENT_ID / "sessions"
    s_files = sorted(sessions_dir.glob(f"{ds}_*.jsonl")) if sessions_dir.exists() else []

    print(f"{'=' * 70}")
    print(f"  Preview: {ds}  ({len(rounds)} rounds)")
    print(f"{'=' * 70}")

    # session init
    print(f"\n[INITIAL SESSION CONTEXT]")
    if s_files:
        print(f"  file: {s_files[0].name}")
        for line in s_files[0].read_text(encoding="utf-8").splitlines():
            if line.strip():
                obj = json.loads(line)
                role = obj["role"].upper()
                content = obj["content"]
                snippet = content[:160] + ("..." if len(content) > 160 else "")
                print(f"  {role}: {snippet}")
    else:
        print(f"  (no session file found for {ds})")

    # 两条路径
    for label, assume_correct in [("ALL CORRECT", True), ("ALL INCORRECT", False)]:
        print(f"\n{'─' * 70}")
        print(f"  PATH: {label}")
        print(f"{'─' * 70}")

        msgs = build_injected_messages(rounds, assume_correct)
        round_msgs = msgs[:-1]   # 对应 rounds
        final_msg = msgs[-1]     # standalone feedback

        for i, (msg, r) in enumerate(zip(round_msgs, rounds)):
            rid = r.get("id", f"r{i+1}")
            rtype = r.get("type", "?")
            print(f"\n  Round {i+1}/{len(rounds)} [{rid}] [{rtype}]")
            print(f"  USER MESSAGE:")
            for line in msg.split("\n")[:10]:
                print(f"    {line}")
            if msg.count("\n") >= 10:
                print(f"    ...")

            ev = r.get("eval") or {}
            if rtype == "multi_choice":
                opts = ev.get("options", {})
                ans = ev.get("answer", [])
                print(f"  EVAL: answer={ans}  options=[{', '.join(opts.keys())}]")
            elif rtype == "file_check":
                cmd = ev.get("command", "")
                exit_code = ev.get("expect_exit", 0)
                print(f"  EVAL: command={cmd!r}  expect_exit={exit_code}")

        print(f"\n  FINAL STANDALONE FEEDBACK:")
        snippet = final_msg[:200] + ("..." if len(final_msg) > 200 else "")
        print(f"    {snippet}")

    print(f"\n{'=' * 70}")


# ---------------------------------------------------------------------------
# CLI 入口
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="MetaClaw Evolution Benchmark 数据制造工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  python bench_data_tools.py init --arc A
  python bench_data_tools.py validate --day 1
  python bench_data_tools.py validate --arc A
  python bench_data_tools.py count --arc A
  python bench_data_tools.py preview --day 1
""",
    )
    parser.add_argument(
        "--bench-data-dir",
        default=str(DEFAULT_BENCH_DATA_DIR),
        metavar="PATH",
        help=f"benchmark data 根目录（默认: <project>/benchmark/data/metaclaw-bench）",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    # init
    p_init = sub.add_parser("init", help="创建弧目录骨架，生成 UUID，创建输出目录结构")
    p_init.add_argument("--arc", required=True, metavar="X", help="弧字母 A–F")
    p_init.add_argument("--force", action="store_true", help="强制重新生成 UUID（覆盖已有 uuid_registry.json）")

    # validate
    p_val = sub.add_parser("validate", help="验证单天或整弧数据格式")
    g_val = p_val.add_mutually_exclusive_group(required=True)
    g_val.add_argument("--day", metavar="N", help="天编号（如 1 或 01）")
    g_val.add_argument("--arc", metavar="X", help="弧字母，验证整弧")

    # count
    p_cnt = sub.add_parser("count", help="估算 token 量")
    g_cnt = p_cnt.add_mutually_exclusive_group()
    g_cnt.add_argument("--day", metavar="N", help="单天")
    g_cnt.add_argument("--arc", metavar="X", help="整弧")

    # preview
    p_prev = sub.add_parser("preview", help="展示 agent 实际收到的消息序列")
    p_prev.add_argument("--day", required=True, metavar="N", help="天编号")

    args = parser.parse_args()
    dispatch = {
        "init": cmd_init,
        "validate": cmd_validate,
        "count": cmd_count,
        "preview": cmd_preview,
    }
    dispatch[args.cmd](args)


if __name__ == "__main__":
    main()
