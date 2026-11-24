#!/usr/bin/env python3
"""Fail closed on common secrets/private identifiers in distributable material.

Scans content, not author identity or GitHub account metadata. No dependency
on network services, credentials, git, or proprietary scanners.
"""
import argparse
import re
from pathlib import Path
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
TEXT_SUFFIXES = {'.py', '.md', '.yaml', '.yml', '.xml', '.json', '.txt', '.toml', '.sh'}
SAFE_NAMES = {'.gitignore', 'VERSION'}
PATTERNS = {
    'email_address': re.compile(r'\b[A-Za-z0-9._%+\-]+\x40[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b'),
    'windows_user_profile': re.compile(r'[A-Za-z]:\\(?:Users|Documents and Settings)\\[^\\/\r\n\s]+', re.IGNORECASE),
    'unix_home_directory': re.compile(r'/(?:home|Users)/[A-Za-z0-9_.\-]+(?:/|$)'),
    'private_key': re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----'),
    'github_classic_token': re.compile(r'\bgh[pousr]_[A-Za-z0-9_]{24,}\b'),
    'github_fine_grained_token': re.compile(r'\bgithub_pat_[A-Za-z0-9_]{24,}\b'),
    'aws_access_key': re.compile(r'\bAKIA[0-9A-Z]{16}\b'),
    'slack_token': re.compile(r'\bxox[baprs]-[0-9A-Za-z-]{16,}\b'),
    'generic_secret_assignment': re.compile(r'(?im)^\s*(?:api_key|api_token|password|client_secret)\s*[:=]\s*[\"\']?[A-Za-z0-9_./+=-]{20,}[\"\']?\s*$'),
}


def match_private_data(text):
    return sorted(label for label, pattern in PATTERNS.items() if pattern.search(text))


def tracked_candidates():
    for path in ROOT.rglob('*'):
        if not path.is_file():
            continue
        relative = path.relative_to(ROOT)
        if any(part in {'.git', 'dist', '__pycache__', '.pytest_cache'} for part in relative.parts):
            continue
        if path.suffix in TEXT_SUFFIXES or path.name in SAFE_NAMES:
            yield path


def scan_text(path, data):
    try:
        text = data.decode('utf-8')
    except UnicodeDecodeError:
        return ['not_utf8']
    return match_private_data(text)


def scan_root():
    problems = []
    for path in tracked_candidates():
        labels = scan_text(path, path.read_bytes())
        if labels:
            problems.append((str(path.relative_to(ROOT)), labels))
    return problems


def scan_dist():
    problems = []
    archives = [*(ROOT / 'mods/staysharp/dist').glob('*.wotmod'),
                *(ROOT / 'dist').glob('*.wotmod')]
    for archive_path in archives:
        with ZipFile(archive_path) as archive:
            if archive.testzip() is not None:
                problems.append((archive_path.name, ['corrupt_archive']))
            for info in archive.infolist():
                if info.filename.endswith(('.py', '.xml', '.txt', '.md')):
                    labels = scan_text(Path(info.filename), archive.read(info))
                    if labels:
                        problems.append((archive_path.name + ':' + info.filename, labels))
                if (info.filename.endswith(('.dmp', '.mdmp', '.p12', '.pfx', '.pem', '.key'))
                        or 'log' in Path(info.filename).name.lower()):
                    problems.append((archive_path.name + ':' + info.filename, ['forbidden_release_resource']))
    return problems


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--scan-dist', action='store_true', help='also check distributable archives')
    args = parser.parse_args()
    problems = scan_root()
    if args.scan_dist:
        problems += scan_dist()
    if problems:
        for name, labels in problems:
            # Do not print contents of a suspected credential or personal identifier.
            print('BLOCKED:', name, ','.join(labels))
        raise SystemExit(1)
    print('Privacy audit OK: source, notes and selected release archives contain no matched private data')


if __name__ == '__main__':
    main()
