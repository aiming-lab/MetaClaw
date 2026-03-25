#!/usr/bin/env python3
"""check_filename.py — validate P2 file naming convention."""
import argparse, os, re, sys

PATTERN = re.compile(r'^\d{8}_[a-z][a-z0-9_]*\.[a-z0-9]+$')


def check_file(path):
    basename = os.path.basename(path)
    if PATTERN.match(basename):
        print("OK")
        sys.exit(0)
    else:
        print(f"FAIL: '{basename}' does not match YYYYMMDD_snake_case.ext pattern")
        sys.exit(1)


def check_dir(directory, ext, min_count):
    if not os.path.isdir(directory):
        print(f"FAIL: directory not found: {directory}")
        sys.exit(1)
    ext_lower = ext.lstrip('.').lower()
    matches = [
        f for f in os.listdir(directory)
        if PATTERN.match(f) and f.rsplit('.', 1)[-1].lower() == ext_lower
    ]
    if len(matches) >= min_count:
        print(f"OK ({len(matches)} matching file(s): {', '.join(sorted(matches))})")
        sys.exit(0)
    else:
        print(f"FAIL: expected >= {min_count} P2-compliant .{ext_lower} file(s) in {directory}, found {len(matches)}")
        sys.exit(1)


def main():
    if len(sys.argv) >= 2 and not sys.argv[1].startswith('--'):
        check_file(sys.argv[1])
    parser = argparse.ArgumentParser()
    parser.add_argument('--dir', required=True)
    parser.add_argument('--ext', required=True)
    parser.add_argument('--min-count', type=int, default=1)
    args = parser.parse_args()
    check_dir(args.dir, args.ext, args.min_count)


if __name__ == '__main__':
    main()
