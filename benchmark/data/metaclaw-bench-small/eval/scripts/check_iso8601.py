#!/usr/bin/env python3
"""check_iso8601.py — validate ISO 8601 +08:00 fields in a JSON file."""
import json, re, sys

PATTERN = re.compile(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?\+08:00$')


def get_values(obj, path):
    """Yield (display_path, value) for each value at path. Supports list[]."""
    parts = path.split('.')
    def _walk(cur, parts_left, prefix):
        if not parts_left:
            yield prefix, cur
            return
        p = parts_left[0]
        rest = parts_left[1:]
        if p.endswith('[]'):
            key = p[:-2]
            arr = cur.get(key, [])
            for i, item in enumerate(arr):
                yield from _walk(item, rest, f"{prefix}.{key}[{i}]")
        else:
            if isinstance(cur, dict) and p in cur:
                yield from _walk(cur[p], rest, f"{prefix}.{p}")
            else:
                yield f"{prefix}.{p}", None
    yield from _walk(obj, parts, '')


def main():
    if len(sys.argv) < 3:
        print("Usage: check_iso8601.py <json_file> <field> [<field> ...]")
        sys.exit(2)

    try:
        with open(sys.argv[1], encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"FAIL: cannot read {sys.argv[1]}: {e}")
        sys.exit(1)

    for field in sys.argv[2:]:
        for path, val in get_values(data, field):
            if val is None:
                print(f"FAIL: {field}: field not found")
                sys.exit(1)
            if not PATTERN.match(str(val)):
                print(f"FAIL: {field}: {val!r}")
                sys.exit(1)

    print("OK")
    sys.exit(0)


if __name__ == '__main__':
    main()
