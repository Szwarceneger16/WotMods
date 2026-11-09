#!/usr/bin/env python3
"""Plan and assemble one immutable monorepo release from independent mod builds.

The coordinator is offline and has no GitHub credentials. GitHub CLI provides
read-only Release downloads and a separate protected publisher creates the tag.
"""
import argparse
import fnmatch
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess

from release_installers import (KINDS, installer_name, normalize,
                                verify, verify_directory)

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / 'scripts/release_modules.json'
SEMVER = re.compile(r'(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\Z')
TAG_PREFIX = 'wotmods-v1.0.'
LEGACY_TAG = re.compile(r'(?:staysharp|sessionstats)-v[0-9]+\.[0-9]+\.[0-9]+\Z')


def run_git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT).decode('utf-8').strip()


def version_parts(value):
    if not isinstance(value, str) or not SEMVER.fullmatch(value):
        raise ValueError('Invalid strict SemVer: %r' % value)
    return tuple(map(int, value.split('.')))


def next_version(baseline, previous):
    base = version_parts(baseline)
    if previous is None:
        chosen = base
    else:
        major, minor, patch = version_parts(previous)
        chosen = max(base, (major, minor, patch + 1))
    return '.'.join(map(str, chosen))


def next_release_tag(previous_tag, commit_count):
    # A client-only update can publish a new installer snapshot without any
    # source commit. The global tag must therefore advance per PUBLICATION,
    # not per Git commit; never reuse or move an immutable tag.
    if previous_tag is None:
        return TAG_PREFIX + str(commit_count)
    if previous_tag.startswith(TAG_PREFIX):
        suffix = previous_tag[len(TAG_PREFIX):]
        if not re.fullmatch(r'(?:0|[1-9][0-9]*)', suffix):
            raise ValueError('Invalid previous unified release tag: ' + previous_tag)
        return TAG_PREFIX + str(int(suffix) + 1)
    if not LEGACY_TAG.fullmatch(previous_tag):
        raise ValueError('Unrecognized previous Latest Release tag: ' + previous_tag)
    return TAG_PREFIX + str(commit_count)


def previous_module_ids(tag):
    """Read the registry FROM the last released commit, not today's registry.

    This permits 2 -> 3 (and later) mod migrations without pretending that an
    existing, immutable two-installer Release is missing a published asset.
    """
    if LEGACY_TAG.fullmatch(tag):
        return {'staysharp', 'sessionstats'}
    if not tag.startswith(TAG_PREFIX):
        raise ValueError('Unrecognized previous Latest Release tag: ' + tag)
    try:
        raw = subprocess.check_output(['git', 'show', tag + ':scripts/release_modules.json'],
                                      cwd=ROOT, stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError as exc:
        raise ValueError('Previous unified Release has no module registry') from exc
    data = json.loads(raw.decode('utf-8'))
    if data.get('schema_version') != 1 or not isinstance(data.get('modules'), list):
        raise ValueError('Previous unified Release registry is invalid')
    ids = [entry['id'] for entry in data['modules']]
    if not ids or len(ids) != len(set(ids)) or not set(ids) <= set(KINDS):
        raise ValueError('Previous Release modules cannot be safely migrated')
    return set(ids)


def registry(path=REGISTRY):
    data = json.loads(Path(path).read_text(encoding='utf-8'))
    if set(data) != {'schema_version', 'modules', 'shared_build_paths'} or data['schema_version'] != 1:
        raise ValueError('Invalid release registry schema')
    modules = data['modules']
    if not isinstance(modules, list) or not modules:
        raise ValueError('Release registry must contain modules')
    ids = []
    prefixes = []
    for entry in modules:
        if set(entry) != {'id', 'display_name', 'base_version_file', 'installer_prefix', 'source_paths'}:
            raise ValueError('Invalid module registry entry')
        mod = entry['id']
        if not isinstance(mod, str) or not re.fullmatch(r'[a-z][a-z0-9_-]*', mod):
            raise ValueError('Invalid module identifier')
        for key in ('display_name', 'base_version_file', 'installer_prefix'):
            if not isinstance(entry[key], str) or not entry[key]:
                raise ValueError('Missing registry field: ' + key)
        if mod not in KINDS or entry['installer_prefix'] != KINDS[mod][0]:
            raise ValueError('Module installer not registered for safe verification: ' + mod)
        if not isinstance(entry['source_paths'], list) or not entry['source_paths']:
            raise ValueError('Module must declare source paths')
        version_parts((ROOT / entry['base_version_file']).read_text(encoding='ascii').strip())
        ids.append(mod)
        prefixes.append(entry['installer_prefix'])
    if len(set(ids)) != len(ids) or len(set(prefixes)) != len(prefixes) or set(ids) != set(KINDS):
        raise ValueError('Registry must match the independently verified installers')
    for patterns in [data['shared_build_paths']] + [m['source_paths'] for m in modules]:
        if not isinstance(patterns, list) or not all(isinstance(p, str) and p and
            not p.startswith('/') and '..' not in p.split('/') for p in patterns):
            raise ValueError('Invalid source path patterns')
    return data


def selected_modules(paths, config):
    paths = list(paths)
    modules = config['modules']
    if any(fnmatch.fnmatchcase(path, pattern) for path in paths
           for pattern in config['shared_build_paths']):
        return [mod['id'] for mod in modules]
    selected = [mod['id'] for mod in modules if any(
        fnmatch.fnmatchcase(path, pattern) for path in paths
        for pattern in mod['source_paths'])]
    # A new module without a verifier/builder must never be silently omitted.
    for path in paths:
        if path.startswith('mods/') and not any(
            fnmatch.fnmatchcase(path, pattern) for mod in modules
            for pattern in mod['source_paths']):
            raise ValueError('Unregistered mod source changed: ' + path)
    return selected


def make_plan(config, changes, previous_versions, previous_tag, source_sha,
              commit_count, client_version, previous_client=None):
    if not re.fullmatch(r'[0-9a-f]{40}', source_sha):
        raise ValueError('Invalid source commit SHA')
    if not isinstance(commit_count, int) or commit_count < 1:
        raise ValueError('Invalid commit count')
    if not re.fullmatch(r'[0-9]+(?:\.[0-9]+){3}', client_version):
        raise ValueError('Invalid World of Tanks client version')
    modules = config['modules']
    if not set(previous_versions) <= {m['id'] for m in modules}:
        raise ValueError('Previous Release contains a removed or unknown mod')
    selected = selected_modules(changes, config)
    for module in modules:
        if module['id'] not in previous_versions and module['id'] not in selected:
            selected.append(module['id'])
    is_migration = previous_tag is not None and not previous_tag.startswith(TAG_PREFIX)
    release = bool(selected or previous_tag is None or is_migration or
                   (previous_client is not None and previous_client != client_version))
    versions = {}
    matrix = []
    for module in modules:
        mod = module['id']
        previous = previous_versions.get(mod)
        baseline = (ROOT / module['base_version_file']).read_text(encoding='ascii').strip()
        version_parts(baseline)
        if mod in selected:
            version = next_version(baseline, previous)
            matrix.append({'mod': mod, 'version': version})
        else:
            if previous is None:
                raise ValueError('Missing unchanged mod in previous release: ' + mod)
            version = previous
        versions[mod] = version
    return {
        'schema_version': 1,
        'source_sha': source_sha,
        'release_tag': next_release_tag(previous_tag, commit_count),
        'previous_tag': previous_tag,
        'previous_modules': sorted(previous_versions),
        'previous_versions': previous_versions,
        'client_version': client_version,
        'modules': [m['id'] for m in modules],
        'changed': selected,
        'versions': versions,
        'matrix': matrix if matrix else [{'mod': 'noop', 'version': '0.0.0'}],
        'publish': release,
        'migration': is_migration,
    }


def plan(args):
    config = registry()
    source_sha = run_git('rev-parse', args.head)
    commit_count = int(run_git('rev-list', '--count', source_sha))
    previous = {}
    previous_client = None
    if args.previous_tag:
        if not args.previous_dir:
            raise ValueError('Previous release directory required with previous tag')
        reports = verify_directory(args.previous_dir,
                                   expected_kinds=previous_module_ids(args.previous_tag))
        previous = {kind: version for kind, version, _, _, _ in reports}
        previous_clients = {client for _, _, client, _, _ in reports}
        if len(previous_clients) != 1:
            raise ValueError('Previous release clients do not match')
        previous_client = previous_clients.pop()
        base_sha = run_git('rev-parse', args.previous_tag + '^{commit}')
        if (base_sha != source_sha and subprocess.run(
                ['git', 'merge-base', '--is-ancestor', source_sha, base_sha],
                cwd=ROOT, check=False).returncode == 0):
            # GitHub may start a newer merge's queued workflow before an older
            # one. That release already contains all older source changes.
            # Never publish a stale commit or retarget the Latest backwards.
            result = make_plan(config, [], previous, args.previous_tag,
                               source_sha, commit_count, args.client_version, previous_client)
            result['publish'] = False
            result['changed'] = []
            result['matrix'] = [{'mod': 'noop', 'version': '0.0.0'}]
            result['versions'] = previous
            Path(args.output).write_text(json.dumps(result, indent=2, sort_keys=True) + '\n', encoding='utf-8')
            print('Source commit already superseded by Latest; no release')
            return
        subprocess.check_call(['git', 'merge-base', '--is-ancestor', base_sha, source_sha], cwd=ROOT)
        changes = subprocess.check_output(['git', 'diff', '-z', '--name-only',
                                           base_sha, source_sha], cwd=ROOT).decode('utf-8').split('\0')
    else:
        if args.previous_dir:
            raise ValueError('Previous release directory without a previous tag')
        changes = []
    result = make_plan(config, changes, previous, args.previous_tag,
                       source_sha, commit_count, args.client_version, previous_client)
    Path(args.output).write_text(json.dumps(result, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    print('Planned mods:', ', '.join(result['changed']) or '(carry forward only)')
    print('Publish:', result['publish'], 'tag:', result['release_tag'])


def write_release_notes(reports, result, repository, output, release_directory):
    tag = result['release_tag']
    lines = ['## Downloads', '', '| Mod | Version | Installer |',
             '| --- | --- | --- |']
    for kind, version, _, _, _ in sorted(reports):
        mod = next(m for m in registry()['modules'] if m['id'] == kind)
        filename = installer_name(kind, version)
        link = 'https://github.com/%s/releases/download/%s/%s' % (repository, tag, filename)
        lines.append('| %s | %s | [%s](%s) |' %
                     (mod['display_name'], version, filename, link))
    changes = result['changed']
    display = {mod['id']: mod['display_name'] for mod in registry()['modules']}
    summary = ', '.join(display[m] for m in changes) if changes else 'No mod binary changes'
    lines.extend(['', '**Updated in this release:** ' + summary + '.', '',
                  '**WoT EU client:** `' + result['client_version'] + '`.',
                  'Close the game and extract the selected ZIP into the folder containing '
                  '`WorldOfTanks.exe`, preserving the `mods/` directories.', '',
                  '[Full installation and configuration guide](https://github.com/' + repository +
                  '/blob/main/docs/BUILD_RELEASE.md). '
                  'A carried-forward binary is not automatically verified as compatible '
                  'with a newer game client.', '',
                  '<details>', '<summary>SHA-256 installer checksums</summary>', '', '```text'])
    for kind, version, _, _, _ in sorted(reports):
        filename = installer_name(kind, version)
        # These are release assets, not the GitHub-generated source archives.
        data = (Path(release_directory) / filename).read_bytes()
        lines.append(hashlib.sha256(data).hexdigest() + '  ' + filename)
    lines.extend(['```', '', '</details>', ''])
    Path(output).write_text('\n'.join(lines), encoding='utf-8')


def assemble(args):
    config = registry()
    result = json.loads(Path(args.plan).read_text(encoding='utf-8'))
    valid = {m['id'] for m in config['modules']}
    changed = result['changed']
    expected_previous = result['previous_modules']
    if (result['schema_version'] != 1 or set(result['modules']) != valid or
            not isinstance(changed, list) or len(changed) != len(set(changed)) or
            not set(changed) <= valid or set(result['versions']) != valid or
            not isinstance(expected_previous, list) or
            len(expected_previous) != len(set(expected_previous)) or
            not set(expected_previous) <= valid or
            set(result['previous_versions']) != set(expected_previous) or
            bool(result['previous_tag']) != bool(expected_previous) or
            not result['publish']):
        raise ValueError('Invalid release plan')
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    if any(output.iterdir()):
        raise ValueError('Release destination must be empty')
    if result['previous_tag']:
        if not args.previous_dir:
            raise ValueError('Previous Release missing')
        previous_reports = verify_directory(args.previous_dir,
                                             expected_kinds=expected_previous)
        if {kind: version for kind, version, _, _, _ in previous_reports} != result['previous_versions']:
            raise ValueError('Previous Release modules/versions changed since planning')
        for entry in Path(args.previous_dir).iterdir():
            shutil.copy2(entry, output / entry.name)
        normalize(output, result['client_version'])
        (output / 'SHA256SUMS.txt').unlink()
    elif args.previous_dir:
        raise ValueError('Unexpected previous Release')
    built = Path(args.built_dir)
    expected = {installer_name(mod, result['versions'][mod]) for mod in changed}
    received = {p.name for p in built.iterdir()} if built.exists() else set()
    if received != expected:
        raise ValueError('Build artifacts mismatch: expected %r, got %r' % (expected, received))
    if any(not p.is_file() or p.is_symlink() for p in built.iterdir()):
        raise ValueError('Build artifacts must be regular files')
    for mod in changed:
        newname = installer_name(mod, result['versions'][mod])
        report = verify(built / newname)
        if report[:3] != (mod, result['versions'][mod], result['client_version']):
            raise ValueError('Built artifact identity/client mismatch: ' + newname)
        for old in list(output.iterdir()):
            if old.name.startswith(KINDS[mod][0]) and old.name.endswith('.zip'):
                old.unlink()
        shutil.copy2(built / newname, output / newname)
    reports = verify_directory(output)
    if {mod: version for mod, version, _, _, _ in reports} != result['versions']:
        raise ValueError('Final assembled release versions differ from plan')
    if {client for _, _, client, _, _ in reports} != {result['client_version']}:
        raise ValueError('Final assembled release targets an unexpected client')
    write_release_notes(reports, result, args.repository, args.notes, output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('plan')
    p.add_argument('--previous-tag')
    p.add_argument('--previous-dir', type=Path)
    p.add_argument('--head', default='HEAD')
    p.add_argument('--client-version', required=True)
    p.add_argument('--output', type=Path, required=True)
    a = sub.add_parser('assemble')
    a.add_argument('--plan', type=Path, required=True)
    a.add_argument('--previous-dir', type=Path)
    a.add_argument('--built-dir', type=Path, required=True)
    a.add_argument('--output', type=Path, required=True)
    a.add_argument('--notes', type=Path, required=True)
    a.add_argument('--repository', required=True)
    args = parser.parse_args()
    (plan if args.command == 'plan' else assemble)(args)


if __name__ == '__main__':
    main()
