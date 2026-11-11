#!/usr/bin/env python3
"""Avoid the failing Azure entry in the hosted runner's Ubuntu mirror list."""
from pathlib import Path
import re


DEFAULT_MIRROR_PATH = Path('/etc/apt/apt-mirrors.txt')
AZURE_MIRROR = b'http://azure.archive.ubuntu.com/ubuntu/'
OFFICIAL_FALLBACKS = frozenset((b'https://archive.ubuntu.com/ubuntu/',
                                b'https://security.ubuntu.com/ubuntu/'))
PRIORITY = re.compile(rb'priority:[0-9]+\Z')


def _fields(line):
    fields = line.split()
    return fields if fields and not fields[0].startswith(b'#') else []


def transform_mirrors(data):
    """Remove only the known Azure entry, after verifying both safe fallbacks."""
    lines = data.splitlines(keepends=True)
    if not any(_fields(line)[:1] == [AZURE_MIRROR] for line in lines):
        return data
    found = set()
    for line in lines:
        fields = _fields(line)
        if not fields or fields[0] not in OFFICIAL_FALLBACKS:
            continue
        options = []
        for field in fields[1:]:
            if field.startswith(b'#'):
                break
            options.append(field)
        if len(options) > 1 or (options and not PRIORITY.fullmatch(options[0])):
            raise ValueError('Unexpected official Ubuntu mirror options; file unchanged.')
        found.add(fields[0])
    if found != OFFICIAL_FALLBACKS:
        raise ValueError('Both official HTTPS Ubuntu fallbacks are required; file unchanged.')
    return b''.join(line for line in lines if _fields(line)[:1] != [AZURE_MIRROR])


def prepare_mirrors(path=DEFAULT_MIRROR_PATH):
    """Leave absent or unaffected files alone; validate before opening for writing."""
    try:
        original = path.read_bytes()
    except FileNotFoundError:
        return False
    updated = transform_mirrors(original)
    if updated == original:
        return False
    path.write_bytes(updated)
    return True


if __name__ == '__main__':
    import sys
    if len(sys.argv) != 1:
        raise SystemExit('This helper accepts no path or command-line arguments.')
    changed = prepare_mirrors()
    print('Removed the Azure Ubuntu mirror; official HTTPS fallbacks retained.' if changed
          else 'Ubuntu mirror list is absent or has no matching Azure entry; unchanged.')
