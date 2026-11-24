#!/usr/bin/env python3
"""Derive a unique SemVer patch from this workflow's GitHub run number.

No git writes, repo API or credentials needed. Initial run #1 == VERSION.
"""
import argparse
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
BASE_VERSION = ROOT / 'mods/staysharp/VERSION'


def release_version(base, run_number):
    if not re.fullmatch(r'(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)', base):
        raise ValueError('Invalid base semantic version')
    number = int(run_number)
    if number < 1:
        raise ValueError('GitHub workflow run number must be >= 1')
    major, minor, patch = map(int, base.split('.'))
    return '%d.%d.%d' % (major, minor, patch + number - 1)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run-number', type=int, required=True)
    args = parser.parse_args()
    print(release_version(BASE_VERSION.read_text(encoding='ascii').strip(), args.run_number))


if __name__ == '__main__':
    main()
