#!/usr/bin/env python3
"""check_done_log.py — validate P5 done.log entries."""
import argparse, re, sys, os

LINE_PATTERN = re.compile(
    r'^\[DONE\] (\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?\+08:00) \| ([^\|]+) \| (.+)$'
)


def fail(msg):
    print(f"FAIL: {msg}")
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('logfile')
    parser.add_argument('--task-prefix', default=None)
    parser.add_argument('--min-entries', type=int, default=1)
    args = parser.parse_args()

    if not os.path.exists(args.logfile):
        fail(f"done.log not found: {args.logfile}")

    lines = [l.rstrip('\n') for l in open(args.logfile, encoding='utf-8') if l.strip()]
    if len(lines) < args.min_entries:
        fail(f"expected >= {args.min_entries} entries, found {len(lines)}")

    for i, line in enumerate(lines):
        m = LINE_PATTERN.match(line)
        if not m:
            fail(f"line {i+1} does not match format: {line!r}")
        summary = m.group(4).strip()
        if len(summary) > 80:
            fail(f"line {i+1} summary exceeds 80 chars ({len(summary)}): {summary!r}")

    if args.task_prefix:
        last = lines[-1]
        m = LINE_PATTERN.match(last)
        task_id = m.group(3).strip()
        if not task_id.startswith(args.task_prefix):
            fail(f"last entry task_id {task_id!r} does not start with {args.task_prefix!r}")

    print(f"OK ({len(lines)} entries)")
    sys.exit(0)


if __name__ == '__main__':
    main()
