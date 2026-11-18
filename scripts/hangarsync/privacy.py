#!/usr/bin/env python3
"""Audit Hangar publication inputs and recursive archives; report labels only."""
import argparse
import importlib.util
import io
import json
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import tempfile
from urllib.parse import urlsplit
import zipfile

ROOT = Path(__file__).resolve().parents[2]
MOD = ROOT / 'mods/hangarsync'
spec = importlib.util.spec_from_file_location('hangar_base_privacy', ROOT / 'scripts/privacy_audit.py')
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)
PATTERNS = dict(base.PATTERNS)
PATTERNS.update({
    'build_workspace': re.compile('/work' + r'space/(?:scratch/)?[^\s\x00"\']+'),
    'wot_device_token': re.compile(r'\bwgs_[0-9a-f]{64}\b', re.I),
    'literal_game_account_id': re.compile(r'''(?im)["']?(?:databaseID|account_dbid|account_id)["']?\s*[:=]\s*["']?[1-9][0-9]{5,}'''),
})
URL = re.compile(r'''https?://[^\s<>"'\\]+''', re.I)
SECRET_LITERAL = re.compile(r'''(?im)["']?(?:device_token|sites_access_token)["']?\s*[:=]\s*["']([^"']+)["']''')
FORBIDDEN = {'.log', '.dmp', '.mdmp', '.db', '.sqlite', '.sqlite3', '.token', '.credentials',
             '.p12', '.pfx', '.pem', '.key', '.png', '.jpg', '.jpeg', '.webp'}
SKIP = {'.git', '__pycache__', '.pytest_cache', 'dist'}
EXAMPLE = {'enabled': False, 'endpoint_url': '', 'device_token': '', 'sites_access_token': '',
           'region': 'EU', 'display_name': '', 'allowed_players': [], 'include_crew': False,
           'interval_seconds': 120, 'include_missions': False, 'mission_diagnostics': True}
MAX_BYTES = 16 * 1024 * 1024


def is_fixture(name):
    return 'tests/' in name.replace('\\', '/')


def text_labels(text, fixture=False, documentation=False):
    labels = {name for name, pattern in PATTERNS.items() if pattern.search(text)}
    if not fixture and SECRET_LITERAL.search(text):
        labels.add('credential_literal')
    for match in URL.finditer(text):
        try:
            host = (urlsplit(match.group()).hostname or '').lower()
        except ValueError:
            continue
        if host == 'chatgpt.site' or host.endswith('.chatgpt.site'):
            if documentation and host == 'your-site.chatgpt.site' and match.group().startswith('https://' + 'YOUR-SITE.chatgpt.site/'):
                continue
            # Existing configuration tests declare these exact synthetic hosts,
            # including intentionally malformed labels. No runtime exemption.
            if not fixture or host not in {'private-example.chatgpt.site', 'private-example..chatgpt.site', '-private.chatgpt.site'}:
                labels.add('private_site_endpoint')
    return sorted(labels)


def clean_example(data):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('Duplicate example field')
            result[key] = value
        return result

    try:
        value = json.loads(data.decode('utf-8'), object_pairs_hook=unique)
        return value == EXAMPLE and all(type(value[key]) is type(expected) for key, expected in EXAMPLE.items())
    except (ValueError, UnicodeError, KeyError, TypeError):
        return False


def bytecode_labels(data, python27):
    if not python27:
        return ['python27_required']
    with tempfile.TemporaryDirectory(prefix='hangarsync-audit-') as temporary:
        temporary = Path(temporary)
        module = temporary / 'module.pyc'
        patterns = temporary / 'patterns.json'
        module.write_bytes(data)
        # Match package constants without ever printing source or credential values.
        rules = [(name, pattern.pattern) for name, pattern in PATTERNS.items()]
        rules.extend([('private_site_endpoint', r'https?://[^\s<>"\'\\]*chatgpt\.site'),
                      ('credential_literal', SECRET_LITERAL.pattern)])
        patterns.write_text(json.dumps(rules), encoding='utf-8')
        try:
            result = subprocess.run([python27, '-B', str(Path(__file__).with_name('bootstrap_smoke.py')),
                                     '--audit-pyc', str(module), '--patterns', str(patterns)],
                                    capture_output=True, text=True, timeout=30)
            if result.returncode:
                return ['invalid_python27_bytecode']
            labels = json.loads(result.stdout)
            if not isinstance(labels, list) or any(not isinstance(label, str) for label in labels):
                return ['invalid_python27_audit_result']
            return labels
        except (OSError, ValueError, subprocess.TimeoutExpired):
            return ['python27_audit_failed']


def scan_bytes(name, data, python27, depth=0, budget=None):
    budget = [0] if budget is None else budget
    budget[0] += len(data)
    if depth > 4 or budget[0] > MAX_BYTES:
        return [(name, ['archive_budget'])]
    path = PurePosixPath(name.rsplit(':', 1)[-1])
    if path.suffix.lower() in FORBIDDEN or path.name == 'GRZ_Hangar_Sync.json':
        return [(name, ['forbidden_resource'])]
    if path.suffix.lower() in ('.zip', '.wotmod'):
        problems = []
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                members = archive.infolist()
                if len(members) > 200 or sum(member.file_size for member in members) > MAX_BYTES - budget[0]:
                    return [(name, ['archive_budget'])]
                if archive.testzip() is not None:
                    return [(name, ['invalid_archive'])]
                seen = set()
                for member in members:
                    inner = PurePosixPath(member.filename)
                    if (member.filename in seen or inner.is_absolute() or '..' in inner.parts or
                            '\\' in member.filename or ':' in member.filename or stat.S_ISLNK(member.external_attr >> 16)):
                        problems.append((name, ['unsafe_archive_member']))
                        continue
                    seen.add(member.filename)
                    if not member.is_dir():
                        if member.file_size > MAX_BYTES - budget[0]:
                            problems.append((name, ['archive_budget']))
                            continue
                        problems.extend(scan_bytes(name + ':' + member.filename, archive.read(member),
                                                   python27, depth + 1, budget))
        except (OSError, ValueError, zipfile.BadZipFile, RuntimeError):
            return [(name, ['invalid_archive'])]
        return problems
    if path.suffix.lower() == '.pyc':
        labels = bytecode_labels(data, python27)
    else:
        try:
            labels = text_labels(data.decode('utf-8'), is_fixture(name), path.name == 'README.md')
        except UnicodeError:
            labels = ['not_utf8']
        if path.name == 'GRZ_Hangar_Sync.json.example' and not clean_example(data):
            labels.append('personalized_example')
    return [(name, sorted(set(labels)))] if labels else []


def audit(python27, scan_dist=False):
    problems = []
    scopes = [MOD, ROOT / 'scripts/hangarsync']
    files = list((ROOT / 'tests').glob('test_hangarsync_*.py'))
    for scope in scopes:
        for path in scope.rglob('*'):
            if any(part in SKIP for part in path.relative_to(scope).parts):
                continue
            if path.is_symlink():
                problems.append((path.relative_to(ROOT).as_posix(), ['forbidden_symlink']))
            elif path.is_file() and path.suffix not in ('.pyc', '.pyo'):
                files.append(path)
    for path in files:
        problems.extend(scan_bytes(path.relative_to(ROOT).as_posix(), path.read_bytes(), python27))
    if scan_dist:
        directory = MOD / 'dist'
        version = (MOD / 'VERSION').read_text(encoding='ascii').strip()
        expected = {'GRZ_Hangar_Sync.wotmod', 'GRZ_Hangar_Sync-v' + version + '.zip'}
        entries = list(directory.iterdir()) if directory.is_dir() else []
        if ({path.name for path in entries} != expected or
                any(not path.is_file() or path.is_symlink() for path in entries)):
            problems.append(('mods/hangarsync/dist', ['unexpected_build_assets']))
        else:
            for path in entries:
                problems.extend(scan_bytes(path.name, path.read_bytes(), python27))
    return problems


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--python27', required=True)
    parser.add_argument('--scan-dist', action='store_true')
    args = parser.parse_args()
    problems = audit(args.python27, args.scan_dist)
    for index, (name, labels) in enumerate(problems, 1):
        # A suspicious filename can itself contain an account name or secret.
        print('BLOCKED: item=%d' % index, ','.join(labels))
    if problems:
        raise SystemExit(1)
    print('Privacy audit OK: Hangar source, recursive archives, embedded source and Python 2.7 constants')


if __name__ == '__main__':
    main()
