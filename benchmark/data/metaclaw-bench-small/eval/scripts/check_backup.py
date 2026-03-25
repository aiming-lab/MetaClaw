#!/usr/bin/env python3
"""check_backup.py — validate P4 pre-modification backup."""
import sys, os

def main():
    if len(sys.argv) < 2:
        print("Usage: check_backup.py <original_file>")
        sys.exit(2)
    orig = sys.argv[1]
    bak = orig + '.bak'
    if not os.path.exists(orig):
        print(f"FAIL: original file not found: {orig}")
        sys.exit(1)
    if not os.path.exists(bak):
        print(f"FAIL: backup file not found: {bak} (must create .bak before modifying)")
        sys.exit(1)
    orig_content = open(orig, 'rb').read()
    bak_content = open(bak, 'rb').read()
    if orig_content == bak_content:
        print(f"FAIL: {bak} has identical content to {orig} — backup was not made before modification")
        sys.exit(1)
    print("OK")
    sys.exit(0)

if __name__ == '__main__':
    main()
