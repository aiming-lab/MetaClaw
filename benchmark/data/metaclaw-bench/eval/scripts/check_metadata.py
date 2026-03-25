#!/usr/bin/env python3
"""check_metadata.py — validate P3 metadata completeness."""
import argparse, json, re, sys

REQUIRED_FIELDS = ['created_at', 'author', 'status']
VALID_STATUSES = {'pending', 'in_progress', 'done'}
ISO_PATTERN = re.compile(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?\+08:00$')


def fail(msg):
    print(f"FAIL: {msg}")
    sys.exit(1)


def check_json(path):
    try:
        data = json.load(open(path, encoding='utf-8'))
    except Exception as e:
        fail(f"cannot parse JSON: {e}")
    meta = data.get('meta')
    if not meta or not isinstance(meta, dict):
        fail("missing top-level 'meta' object")
    for f in REQUIRED_FIELDS:
        if f not in meta:
            fail(f"meta.{f} is missing")
        if meta[f] is None or meta[f] == '':
            fail(f"meta.{f} is empty")
    if not ISO_PATTERN.match(str(meta.get('created_at', ''))):
        fail(f"meta.created_at is not valid ISO 8601 +08:00: {meta.get('created_at')!r}")
    if meta.get('status') not in VALID_STATUSES:
        fail(f"meta.status must be one of {VALID_STATUSES}, got {meta.get('status')!r}")
    print("OK")
    sys.exit(0)


def check_md(path):
    text = open(path, encoding='utf-8').read()
    if not text.startswith('---'):
        fail("missing YAML frontmatter (file must start with ---)")
    end = text.find('\n---', 3)
    if end == -1:
        fail("YAML frontmatter not closed with ---")
    fm = text[3:end]
    found = {}
    for line in fm.splitlines():
        if ':' in line:
            k, _, v = line.partition(':')
            found[k.strip()] = v.strip()
    for f in REQUIRED_FIELDS:
        if f not in found or not found[f]:
            fail(f"frontmatter missing or empty field: {f}")
    if not ISO_PATTERN.match(found.get('created_at', '')):
        fail(f"frontmatter created_at is not valid ISO 8601 +08:00: {found.get('created_at')!r}")
    if found.get('status') not in VALID_STATUSES:
        fail(f"frontmatter status must be one of {VALID_STATUSES}, got {found.get('status')!r}")
    print("OK")
    sys.exit(0)


def check_py(path):
    text = open(path, encoding='utf-8').read()
    # Look for module docstring containing Meta: section
    m = re.search(r'"""(.*?)"""', text, re.DOTALL)
    if not m:
        fail("missing module docstring")
    docstring = m.group(1)
    meta_section = re.search(r'Meta:(.*?)(?:\n\n|\Z)', docstring, re.DOTALL)
    if not meta_section:
        fail("module docstring missing 'Meta:' section")
    meta_text = meta_section.group(1)
    found = {}
    for line in meta_text.splitlines():
        if ':' in line:
            k, _, v = line.partition(':')
            found[k.strip().lower()] = v.strip()
    for f in REQUIRED_FIELDS:
        if f not in found or not found[f]:
            fail(f"Meta section missing or empty field: {f}")
    if not ISO_PATTERN.match(found.get('created_at', '')):
        fail(f"Meta created_at is not valid ISO 8601 +08:00: {found.get('created_at')!r}")
    print("OK")
    sys.exit(0)


def check_csv(path):
    first_line = open(path, encoding='utf-8').readline().strip()
    if not first_line.startswith('# meta:'):
        fail("first line must be '# meta: created_at=... author=... status=...'")
    meta_str = first_line[len('# meta:'):].strip()
    found = {}
    for part in meta_str.split():
        if '=' in part:
            k, _, v = part.partition('=')
            found[k.strip()] = v.strip()
    for f in REQUIRED_FIELDS:
        if f not in found or not found[f]:
            fail(f"meta comment missing field: {f}")
    if not ISO_PATTERN.match(found.get('created_at', '')):
        fail(f"meta created_at is not valid ISO 8601 +08:00: {found.get('created_at')!r}")
    print("OK")
    sys.exit(0)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('filepath')
    parser.add_argument('--type', choices=['json', 'md', 'py', 'csv'], default=None)
    args = parser.parse_args()
    ftype = args.type or args.filepath.rsplit('.', 1)[-1].lower()
    dispatch = {'json': check_json, 'md': check_md, 'txt': check_md,
                'py': check_py, 'csv': check_csv}
    fn = dispatch.get(ftype)
    if not fn:
        fail(f"unsupported file type: {ftype}")
    fn(args.filepath)


if __name__ == '__main__':
    main()
