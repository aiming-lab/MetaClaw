# MetaClaw Benchmark CLI

Command-line interface for running and evaluating the MetaClaw Evolution Benchmark.

## Entry point

```
metaclaw-bench <command> [options]
```

Or via Python module:

```
python -m benchmark.src.cli <command> [options]
```

## Commands

### `check`

Validate a MetaClaw benchmark dataset before running inference.

```
metaclaw-bench check <path/to/all_tests.json>
```

**Checks performed (8 total):**

| # | Checker | Description |
|---|---------|-------------|
| 1 | AllTests Structure | Top-level fields and test array structure; unique agent id |
| 2 | Basic Integrity | Referenced files exist on disk |
| 3 | ID Consistency | Session IDs unique; internal IDs match filenames |
| 4 | File Format | JSONL and questions.json are valid JSON |
| 5 | Directory Structure | eval/ and sessions/ directories exist |
| 6 | Workspace Integrity | workspace_src has required identity files |
| 7 | Session Format | Session JSONL first/second line roles |
| 8 | Questions Integrity | round types, feedback strings, eval field structure |

---

### `infer`

Run the openclaw agent for each scenario and save results.

```
metaclaw-bench infer <path/to/all_tests.json> --output <output_dir> [--retry N]
```

Tests run serially (workers=1 enforced) due to per-test workspace isolation.

**questions.json format:**

```json
{
  "id": "day01",
  "desc": "Time format preference",
  "rounds": [
    {
      "id": "r1",
      "type": "file_check",
      "question": "Save meeting notes to tasks/day01/meeting.json.",
      "feedback": {
        "correct": "Format is correct!",
        "incorrect": "Please use ISO 8601 for time fields."
      },
      "eval": {
        "command": "python scripts/check_meeting.py day01/meeting.json",
        "expect_exit": 0,
        "expect_stdout": "OK"
      }
    },
    {
      "id": "r2",
      "type": "multi_choice",
      "question": "Which time format did you use?",
      "feedback": { "correct": "Correct!", "incorrect": "Review ISO 8601." },
      "eval": {
        "options": { "A": "ISO 8601", "B": "Unix timestamp", "C": "Plain text" },
        "answer": ["A"]
      }
    }
  ]
}
```

Feedback injection: each round (except the first) receives the previous round's feedback prepended as `[上一步反馈] <text>\n\n<question>`. A standalone feedback message is sent after the last round.

---

### `score`

Score inference results.

```
metaclaw-bench score <path/to/all_tests.json> --result <result_dir>
```

`file_check` rounds are scored from the `inline_score.passed` field written during inference. `multi_choice` rounds extract `\bbox{X}` and compare to `eval.answer`.

---

### `report`

Generate a summary report from scoring results.

```
metaclaw-bench report --result <result_dir> --output <output_dir>
```

---

### `run`

Full pipeline: infer → score → report.

```
metaclaw-bench run <path/to/all_tests.json> --output <output_dir>
```

---

### `clean`

Remove work/ directories created during inference.

```
metaclaw-bench clean <root_dir>
```
