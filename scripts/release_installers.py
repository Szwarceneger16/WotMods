#!/usr/bin/env python3
"""Package verified builds, migrate legacy snapshots, and write release download notes.

No builds or GitHub mutations happen here. Unchanged current-format installers
are validated and carried byte-for-byte by release_snapshot.sh.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import re
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
DATE = (2026, 10, 24, 0, 0, 0)
SEMVER = r'(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)'
CLIENT = '2.4.1.0'
SESSIONSTATS_PACKAGE = 'grz_sessions_stats.wotmod'
PREVIOUS_SESSIONSTATS_PACKAGE = 'GRZ_Session_Stats.wotmod'
KINDS = {
    'staysharp': ('StaySharp-Medkit-v', 'com.staysharp.medkitreminder_', 'Stay Sharp Medkit'),
    'sessionstats': ('Session-Stats-v', 'grz.sessionstats_', 'Session Stats'),
}
MEDKIT_INSTALLED_PACKAGE = 'GRZ_Medkit_Reminder.wotmod'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def safe(name):
    return (name and not any(c in name for c in '\\\r\n\x00:') and
            not name.startswith('/') and
            all(p not in ('', '.', '..') for p in name.split('/')))


def read_zip(path):
    with zipfile.ZipFile(path) as archive:
        infos = archive.infolist()
        if len(infos) != len({i.filename for i in infos}):
            raise ValueError('Duplicate ZIP members')
        if sum(i.file_size for i in infos) > 100 * 1024 * 1024:
            raise ValueError('Installer exceeds size limit')
        result = {}
        for info in infos:
            if not safe(info.filename.rstrip('/')) or info.flag_bits & 1:
                raise ValueError('Unsafe ZIP member')
            if (info.external_attr >> 16) & 0o170000 == 0o120000:
                raise ValueError('Symlink ZIP member')
            if not info.is_dir():
                result[info.filename] = archive.read(info)
        return result


def check_manifest(files, manifest='SHA256SUMS.txt'):
    rows = files[manifest].decode('ascii').splitlines()
    expected = {}
    for row in rows:
        match = re.fullmatch(r'([0-9a-f]{64})  (.+)', row)
        if not match or not safe(match[2]) or match[2] in expected:
            raise ValueError('Invalid checksum manifest')
        expected[match[2]] = match[1]
    actual = {n: digest(b) for n, b in files.items() if n != manifest}
    if not actual or actual != expected:
        raise ValueError('Checksum manifest does not match complete contents')


def directory_files(directory):
    paths = list(Path(directory).iterdir())
    if any(not p.is_file() or p.is_symlink() for p in paths):
        raise ValueError('Expected regular release files')
    return {p.name: p.read_bytes() for p in paths}


def manifest(directory):
    files = directory_files(directory)
    (Path(directory) / 'SHA256SUMS.txt').write_text(''.join(
        digest(b) + '  ' + n + '\n' for n, b in sorted(files.items())
        if n != 'SHA256SUMS.txt'), encoding='ascii')


def identity(name):
    for kind, (prefix, _, _) in KINDS.items():
        if name.startswith(prefix) and name.endswith('.zip'):
            version = name[len(prefix):-4]
            if re.fullmatch(SEMVER, version):
                return kind, version
    raise ValueError('Unknown installer filename: ' + name)


def installer_name(kind, version):
    if not re.fullmatch(SEMVER, version):
        raise ValueError('Invalid version')
    return KINDS[kind][0] + version + '.zip'


def installed_package(kind, version, report=None):
    legacy = KINDS[kind][1] + version + '.wotmod'
    if kind != 'sessionstats':
        return legacy
    name = (report or {}).get('installed_package', legacy)
    if name not in (legacy, SESSIONSTATS_PACKAGE, PREVIOUS_SESSIONSTATS_PACKAGE):
        raise ValueError('Invalid installed package filename')
    return name


def bundled_languages(report, package):
    resource = report.get('languages_resource')
    if resource != 'res/grz_session_stats/languages.json' or 'languages_config_sha256' in report:
        raise ValueError('Invalid bundled language metadata')
    if resource not in package or digest(package[resource]) != report.get('languages_resource_sha256'):
        raise ValueError('Bundled language resource hash mismatch')
    catalog = json.loads(package[resource].decode('utf-8'))
    if (type(catalog.get('schema_version')) is not int or catalog['schema_version'] != 1 or
            set(catalog.get('languages', {})) != {'en', 'pl', 'ru', 'fr', 'de', 'es', 'uk'}):
        raise ValueError('Bundled language catalog does not match supported languages')
    return resource


def verify(path):
    kind, version = identity(path.name)
    files = read_zip(path)
    doc = 'docs/' + kind + '/'
    check_manifest(files, doc + 'SHA256SUMS.txt')
    report = json.loads(files[doc + 'INSTALLER.json'])
    if report != {'format': 1, 'mod': kind, 'version': version,
                  'client_version': report.get('client_version')}:
        raise ValueError('Installer identity mismatch')
    client = report['client_version']
    if not isinstance(client, str) or not re.fullmatch(r'[0-9]+(?:\.[0-9]+){3}', client):
        raise ValueError('Invalid client version')
    build_report = json.loads(files.get(doc + 'BUILD.json', b'{}')) if kind == 'sessionstats' else None
    primary = 'mods/' + client + '/' + installed_package(kind, version, build_report)
    if primary not in files:
        stable = 'mods/' + client + '/' + MEDKIT_INSTALLED_PACKAGE
        if kind == 'staysharp' and stable in files:
            primary = stable
        else:
            raise ValueError('Missing primary mod')
    package = read_zip(io.BytesIO(files[primary]))
    import xml.etree.ElementTree as ET
    meta = ET.fromstring(package['meta.xml'])
    if meta.findtext('id') != KINDS[kind][1][:-1] or meta.findtext('version') != version:
        raise ValueError('Primary metadata does not match installer')
    for name in files:
        if name.startswith('mods/'):
            if name.startswith('mods/configs/'):
                if not name.endswith('.json.example'):
                    raise ValueError('Active configuration in installer')
                json.loads(files[name].decode('utf-8'))
            elif not (name.startswith('mods/' + client + '/') and name.endswith('.wotmod')):
                raise ValueError('Unexpected installation path')
        elif not name.startswith(doc):
            raise ValueError('Unexpected documentation path')
    wanted = {primary}
    if kind == 'sessionstats':
        wanted.add('mods/' + client + '/net.openwg/net.openwg.gameface_1.2.2.wotmod')
        if not wanted <= files.keys():
            raise ValueError('Missing OpenWG dependency')
        embedded = build_report.get('languages_resource')
        examples = ('grz.sessionstats.json',) if embedded else ('grz.sessionstats.json', 'grz.sessionstats.languages.json')
        if embedded:
            bundled_languages(build_report, package)
            if 'mods/configs/grz.sessionstats.languages.json.example' in files:
                raise ValueError('External translations in bundled-language installer')
        for filename in examples:
            if 'mods/configs/' + filename + '.example' not in files:
                raise ValueError('Missing configuration example')
    elif 'mods/configs/staysharp.medkit.json.example' not in files:
        raise ValueError('Missing configuration example')
    if {n for n in files if n.startswith('mods/') and n.endswith('.wotmod')} != wanted:
        raise ValueError('Unexpected mod package')
    return kind, version, client, files, primary


def write_installer(directory, kind, version, client, files):
    doc = 'docs/' + kind + '/'
    files[doc + 'INSTALLER.json'] = (json.dumps({
        'format': 1, 'mod': kind, 'version': version, 'client_version': client
    }, sort_keys=True) + '\n').encode('ascii')
    upgrade = ('Target client: ' + client + '. Remove older versions of this same mod\n'
               'from the active mods/' + client + '/ folder before starting the game.\n\n')
    if kind == 'staysharp':
        upgrade = ('Target client: ' + client + '. Installed file: ' + MEDKIT_INSTALLED_PACKAGE + '.\n'
                   'When upgrading from versioned filenames, first remove the old\n'
                   'com.staysharp.medkitreminder_*.wotmod files from mods/' + client + '/.\n'
                   'Later updates overwrite the same ' + MEDKIT_INSTALLED_PACKAGE + ' file.\n'
                   'The ZIP filename and the mod metadata retain the version number.\n\n')
    files[doc + 'INSTALL.txt'] = (
        KINDS[kind][2] + ' ' + version + '\n\n'
        'Close World of Tanks. Extract this ZIP into the game installation folder\n'
        '(the folder containing WorldOfTanks.exe), preserving the mods/ paths.\n'
        + upgrade +
        'The mod works with its built-in defaults. Configuration examples in\n'
        'mods/configs/ end in .json.example and are not loaded. To customize,\n'
        'copy the desired example, remove only .example, then edit the JSON.\n'
        'Keep your existing .json files when updating. Restart the game after edits.\n'
        'OpenWG is included in Session Stats; no separate download is required.\n'
    ).encode('utf-8')
    files[doc + 'SHA256SUMS.txt'] = ''.join(digest(b) + '  ' + n + '\n'
        for n, b in sorted(files.items())).encode('ascii')
    target = directory / installer_name(kind, version)
    with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, data in sorted(files.items()):
            info = zipfile.ZipInfo(name, DATE)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data)
    verify(target)
    return target


def package(source, destination, kind, client=CLIENT):
    source, destination = Path(source), Path(destination)
    files = directory_files(source)
    check_manifest(files)
    _, primary_prefix, _ = KINDS[kind]
    primaries = [n for n in files if n.startswith(primary_prefix) and n.endswith('.wotmod')]
    if len(primaries) != 1:
        raise ValueError('Expected exactly one primary package')
    primary = primaries[0]
    version = primary[len(primary_prefix):-7]
    installer_name(kind, version)
    payload = {}
    if kind == 'sessionstats':
        report = json.loads(files['BUILD.json'])
        if report['version'] != version:
            raise ValueError('Build version mismatch')
        client = report['client_target']
        installed_primary = installed_package(kind, version, report)
        config_name = 'grz.sessionstats.json' + ('.example' if installed_primary in
            (SESSIONSTATS_PACKAGE, PREVIOUS_SESSIONSTATS_PACKAGE) else '')
        bundle = read_zip(io.BytesIO(files['wot-statystyki-sesji-v' + version + '.zip']))
        # Check the exact files against the separately verified build; a stale
        # installer must never replace the validated package/config/dependency.
        for name, expected in (
            ('mods/' + client + '/' + installed_primary, files[primary]),
            ('mods/' + client + '/net.openwg/net.openwg.gameface_1.2.2.wotmod',
             files['net.openwg.gameface_1.2.2.wotmod']),
            ('mods/configs/' + config_name, files['grz.sessionstats.json']),
        ):
            if bundle.get(name) != expected:
                raise ValueError('Installer and verified build disagree')
        embedded = report.get('languages_resource')
        if embedded:
            resources = read_zip(io.BytesIO(files[primary]))
            bundled_languages(report, resources)
            if 'mods/configs/grz.sessionstats.languages.json' in bundle:
                raise ValueError('External translations in bundled-language build')
        else:
            # Preserve previously published installers byte-for-byte on carry-forward.
            language = bundle['mods/configs/grz.sessionstats.languages.json']
            if digest(language) != report['languages_config_sha256']:
                raise ValueError('Language configuration hash mismatch')
        for name, data in bundle.items():
            if name == 'SHA256SUMS.txt':
                continue
            if name.startswith('mods/configs/'):
                payload[name if name.endswith('.json.example') else name + '.example'] = data
            elif name.startswith('mods/'):
                payload[name] = data
            else:
                # Preserve licenses, source and build information; keep guides
                # for each mod separate when both ZIPs are extracted together.
                payload['docs/sessionstats/' + name] = data
    else:
        payload['mods/' + client + '/' + MEDKIT_INSTALLED_PACKAGE] = files[primary]
        sample = ROOT / 'staysharp.medkit.example.json'
        payload['mods/configs/staysharp.medkit.json.example'] = (
            sample.read_bytes() if sample.is_file() else b'{\n  "language": "auto"\n}\n')
        for name in ('CHANGELOG.md', 'docs/AUDIO.md', 'assets/VOICE_NOTICE.txt'):
            path = ROOT / name
            if path.is_file():
                payload['docs/staysharp/' + path.name] = path.read_bytes()
    destination.mkdir(parents=True, exist_ok=True)
    return write_installer(destination, kind, version, client, payload)


def normalize(directory, client=CLIENT):
    """Validate a new snapshot, or convert a checksum-verified legacy snapshot."""
    directory = Path(directory)
    files = directory_files(directory)
    modern = [n for n in files if n.startswith(tuple(v[0] for v in KINDS.values()))]
    if modern:
        if set(files) - set(modern):
            raise ValueError('Mixed legacy/current snapshot')
        seen = set()
        for name in modern:
            kind = verify(directory / name)[0]
            if kind in seen:
                raise ValueError('Multiple versions of the same installer')
            seen.add(kind)
    else:
        check_manifest(files)
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            for kind, (_, prefix, _) in KINDS.items():
                if any(n.startswith(prefix) and n.endswith('.wotmod') for n in files):
                    package(directory, output, kind, client)
            if not list(output.iterdir()):
                raise ValueError('No known mod in previous release')
            # Only retire recognized legacy assets after the entire snapshot
            # has verified and every available mod has converted successfully.
            known = {'SHA256SUMS.txt', 'BUILD.json', 'grz.sessionstats.json'}
            if any(n not in known and not re.fullmatch(
                r'(?:com\.staysharp\.medkitreminder_|grz\.sessionstats_|net\.openwg\.gameface_).+\.wotmod|wot-statystyki-sesji-v.+\.zip', n)
                for n in files):
                raise ValueError('Unknown legacy release asset')
            converted = {p.name: p.read_bytes() for p in output.iterdir()}
            for p in directory.iterdir():
                p.unlink()
            for name, data in converted.items():
                (directory / name).write_bytes(data)
    manifest(directory)


def verify_directory(directory):
    paths = list(Path(directory).iterdir())
    if len(paths) != 2 or any(not p.is_file() or p.is_symlink() for p in paths):
        raise ValueError('Release must contain exactly two installer ZIPs')
    reports = [verify(p) for p in paths]
    if {r[0] for r in reports} != set(KINDS):
        raise ValueError('Release needs one installer for each mod')
    if len({r[2] for r in reports}) != 1:
        raise ValueError('Installers target different game clients')
    # Compare IDs and resource paths without compiling/rebuilding either mod.
    resources, ids = set(), set()
    import xml.etree.ElementTree as ET
    for report in reports:
        for name, data in report[3].items():
            if not name.startswith('mods/') or not name.endswith('.wotmod'):
                continue
            contents = read_zip(io.BytesIO(data))
            identifier = ET.fromstring(contents['meta.xml']).findtext('id')
            paths = {n for n in contents if n.startswith('res/')}
            if not identifier or identifier in ids or paths & resources:
                raise ValueError('Conflicting package IDs/resources')
            ids.add(identifier)
            resources.update(paths)
    return reports


def notes(directory, output, repository, tag):
    reports = verify_directory(directory)
    lines = ['## Downloads', '', '| Mod | Version | Download |', '| --- | --- | --- |']
    for kind, version, _, _, _ in sorted(reports):
        name = installer_name(kind, version)
        url = 'https://github.com/' + repository + '/releases/download/' + tag + '/' + name
        lines.append('| ' + KINDS[kind][2] + ' | ' + version + ' | [' + name + '](' + url + ') |')
    lines += ['', '## Installation', '',
        'Close WoT and extract the ZIP into the folder containing `WorldOfTanks.exe`. '
        'Keep the nested `mods/` folders. Both installers target client **' + reports[0][2] + '**.', '',
        'Session Stats includes OpenWG Gameface. Install either mod or both. '
        'Remove older `.wotmod` versions of the same mod from the active version folder.', '',
        'Configuration files are optional examples in `mods/configs/*.json.example`. '
        'Defaults work without renaming them. To customize, copy the example and remove '
        'the final `.example`. Existing `.json` settings are preserved. Restart WoT after editing.', '',
        'Instructions, licenses, source where applicable and build/checksum information '
        'are inside `docs/staysharp/` or `docs/sessionstats/` in each ZIP. '
        'GitHub source archives are for developers.', '',
        '<details>', '<summary>Installer SHA-256 checksums</summary>', '', '```text']
    for path in sorted(Path(directory).iterdir()):
        lines.append(digest(path.read_bytes()) + '  ' + path.name)
    lines += ['```', '', '</details>', '', '## Changes', '']
    Path(output).write_text('\n'.join(lines), encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=['package', 'normalize', 'verify', 'notes'])
    parser.add_argument('directory', type=Path)
    parser.add_argument('--source', type=Path)
    parser.add_argument('--mod', choices=KINDS)
    parser.add_argument('--client-version', default=CLIENT)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--repository')
    parser.add_argument('--tag')
    args = parser.parse_args()
    if args.operation == 'package':
        if args.source is None or args.mod is None:
            parser.error('package requires --source and --mod')
        package(args.source, args.directory, args.mod, args.client_version)
        manifest(args.directory)
    elif args.operation == 'normalize':
        normalize(args.directory, args.client_version)
    elif args.operation == 'verify':
        verify_directory(args.directory)
    else:
        if not all((args.output, args.repository, args.tag)):
            parser.error('notes requires --output, --repository and --tag')
        notes(args.directory, args.output, args.repository, args.tag)


if __name__ == '__main__':
    main()
