#!/usr/bin/env python3
"""Build real Python 2.7 .wotmod and a complete, reproducible source bundle.

Usage: python3 tools/build.py --python27 /path/to/python2.7
No network or game installation access is performed by this builder.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
VERSION = (ROOT / 'VERSION').read_text(encoding='ascii').strip()
ZIP_DATE = (2026, 10, 21, 0, 0, 0)
MAGIC27 = b'\x03\xf3\r\n'
# Only these release-identifying fields are stamped; historical prose is retained.
RELEASE_GUIDES = {
    'README_PL.txt': (r'(?m)^(Version )',),
    'README.md': (r'(?m)^(Version )',),
    'CONTRACT.txt': (r'(?m)^(GRZ SESSION STATS — IMPLEMENTATION CONTRACT v)',
                     r"(?m)^( version: ')"),
    'docs/APPEARANCE_CONFIG.md': (r'(?m)^(# Appearance and scrolling configuration — )',),
}


def put(archive, name, data):
    info = zipfile.ZipInfo(name, ZIP_DATE)
    info.compress_type = archive.compression
    info.external_attr = 0o644 << 16
    archive.writestr(info, data)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def render_guide(relative, content, version, client_version):
    """Stamp active installation guides; keep historical changelogs/evidence intact."""
    if relative not in RELEASE_GUIDES:
        return content
    text = content.decode('utf-8')
    text = text.replace('grz.sessionstats_'+VERSION+'.wotmod', 'grz.sessionstats_'+version+'.wotmod')
    text = text.replace('wot-statystyki-sesji-v'+VERSION+'.zip', 'wot-statystyki-sesji-v'+version+'.zip')
    # A source bundle may already be stamped for a different client. Keep
    # installation paths and active target/command fields consistent on rebuild.
    text = re.sub(r'(?<![A-Za-z0-9_])mods/[0-9]+(?:\.[0-9]+){3}\b',
                  lambda unused: 'mods/' + client_version, text)
    for prefix in (r'(target: Wargaming EU )', r'(?m)^(Target: World of Tanks PC Wargaming EU )',
                   r'(For client )', r'(active mods directory is not )', r'(--client-version )'):
        text = re.sub(prefix + r'[0-9]+(?:\.[0-9]+){3}\b',
                      lambda match: match.group(1) + client_version, text)
    for prefix in RELEASE_GUIDES[relative]:
        text = re.sub(prefix + re.escape(VERSION) + r'\b',
                      lambda match: match.group(1) + version, text)
    return text.encode('utf-8')


def installer_checksums(package, dependency, config, client_version, languages=None):
    target = 'mods/'+client_version+'/'
    entries = [(package, target+package.name),
               (dependency, target+'net.openwg/'+dependency.name),
               (config, 'mods/configs/'+config.name)]
    if languages is not None:
        entries.append((languages, 'mods/configs/'+languages.name))
    return ''.join(digest(path)+'  '+name+'\n' for path, name in entries).encode('ascii')


def check_package(path):
    with zipfile.ZipFile(path) as package:
        assert package.testzip() is None, 'Corrupt ZIP entry'
        names = package.namelist()
        assert len(set(names)) == len(names), 'Duplicate ZIP paths'
        assert 'res/scripts/client/gui/mods/mod_grz_session_stats.pyc' in names
        assert all(i.compress_type == zipfile.ZIP_STORED for i in package.infolist())
        assert not any(n.endswith('.py') for n in names), 'Production package must use bytecode'
        for name in names:
            if name.endswith('.pyc'):
                assert package.read(name)[:4] == MAGIC27, 'Wrong bytecode magic: '+name
        registry = json.loads(package.read('res/gui/gen_resources/grz.sessionstats.json'))
        assert registry[0]['id'] == 'R.mods.grz.sessionstats.views.SessionStats'
        layout = registry[0]['path'].replace('coui://', 'res/')
        assert layout in names, 'Registered layout missing'
        expected = json.loads(package.read('res/grz_session_stats/wn8exp.json'))
        assert len(expected['data']) >= 300
        languages = json.loads(package.read('res/grz_session_stats/languages.json'))
        assert set(languages['languages']) == {'en', 'ru', 'fr', 'pl', 'de', 'es', 'uk'}
        assert isinstance(languages['languages']['en'].get('title'), str)
    return len(names)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--python27', required=True, help='Path to a CPython 2.7 interpreter')
    parser.add_argument('--client-version', default='2.4.1.0')
    parser.add_argument('--version', default=os.environ.get('SESSIONSTATS_VERSION', VERSION))
    args = parser.parse_args()
    global_version = args.version
    if not re.fullmatch(r'(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)', global_version):
        parser.error('Version must be a semantic version without a suffix')
    version_tag = global_version
    if not re.fullmatch(r'[0-9]+(?:\.[0-9]+){3}', args.client_version):
        parser.error('Client version must have four numeric parts')
    compiler = str(Path(args.python27).resolve())
    version = subprocess.check_output([compiler, '-c', 'import sys; print("%d.%d" % sys.version_info[:2])']).decode().strip()
    if version != '2.7':
        raise RuntimeError('WoT requires Python 2.7 bytecode; selected '+version)
    dist = ROOT / 'dist'
    dist.mkdir(exist_ok=True)
    package = dist / ('grz.sessionstats_'+version_tag+'.wotmod')
    required = ['SessionStats.html', 'session_stats.css', 'session_stats.js', 'footer.js', 'footer.css']
    for name in required:
        if not (ROOT/'ui'/name).is_file():
            raise RuntimeError('UI file missing: '+name)
    source_paths = sorted((ROOT/'src').rglob('*.py'))
    expected_modules = ['core', 'storage', 'runtime', 'normalize', 'views', 'footer', 'visuals',
                        'health', 'monitor', 'diagnostics', 'appearance', 'config_path', 'config_files',
                        'localization', 'language_defaults']
    for name in expected_modules:
        if not (ROOT/'src'/'grz_session_stats'/(name+'.py')).is_file():
            raise RuntimeError('Python module missing: '+name)
    sys.path.insert(0, str(ROOT/'src'))
    from grz_session_stats.appearance import CONFIG_FILENAME, default_config
    config_path = ROOT/CONFIG_FILENAME
    languages_path = ROOT/'grz.sessionstats.languages.json'
    subprocess.check_call([sys.executable, str(ROOT/'tools/sync_languages.py'), '--check'])
    if json.loads(config_path.read_text(encoding='utf-8')) != default_config():
        raise RuntimeError('Shipped appearance configuration must match built-in defaults')
    with tempfile.TemporaryDirectory(prefix='grz-wotmod-') as temporary:
        temporary = Path(temporary)
        compile_script = temporary/'compile27.py'
        compile_script.write_text(
            'import json, py_compile, sys\n'
            'for src, dst, virtual in json.load(open(sys.argv[1], "rb")):\n'
            '    py_compile.compile(src, cfile=dst, dfile=virtual, doraise=True)\n', encoding='ascii')
        manifest = []
        for i, path in enumerate(source_paths):
            virtual = 'res/scripts/client/gui/mods/'+path.relative_to(ROOT/'src').as_posix()
            compile_path = path
            if path == ROOT/'src'/'grz_session_stats'/'__init__.py':
                compile_path = temporary/'version.py'
                compile_path.write_text(re.sub(r"(?m)^VERSION = '[^']+'$", "VERSION = '"+version_tag+"'",
                                              path.read_text(encoding='utf-8')), encoding='utf-8')
            manifest.append([str(compile_path), str(temporary/(str(i)+'.pyc')), virtual])
        manifest_path = temporary/'compile.json'
        manifest_path.write_text(json.dumps(manifest), encoding='ascii')
        subprocess.check_call([compiler, str(compile_script), str(manifest_path)])
        with zipfile.ZipFile(package, 'w', zipfile.ZIP_STORED) as z:
            metadata = re.sub(r'<version>[^<]+</version>', '<version>'+version_tag+'</version>',
                              (ROOT/'meta.xml').read_text(encoding='utf-8')).encode('utf-8')
            put(z, 'meta.xml', metadata)
            put(z, 'LICENSE.txt', (ROOT/'LICENSE.txt').read_bytes())
            for _, compiled, virtual in manifest:
                bytecode = Path(compiled).read_bytes()
                assert bytecode[:4] == MAGIC27
                bytecode = bytecode[:4]+b'\x00\x00\x00\x00'+bytecode[8:]
                put(z, virtual+'c', bytecode)
            for name in required:
                put(z, 'res/gui/gameface/mods/grz_session_stats/'+name, (ROOT/'ui'/name).read_bytes())
            put(z, 'res/gui/gen_resources/grz.sessionstats.json', (ROOT/'resources'/'grz.sessionstats.json').read_bytes())
            for path in sorted((ROOT/'data').glob('*.json')):
                put(z, 'res/grz_session_stats/'+path.name, path.read_bytes())
            put(z, 'res/grz_session_stats/languages.json', languages_path.read_bytes())
    entries = check_package(package)
    dependency = ROOT/'third_party'/'openwg'/'net.openwg.gameface_1.2.2.wotmod'
    depmeta = json.loads((dependency.parent/'source.json').read_text())
    if digest(dependency) != depmeta['sha256']:
        raise RuntimeError('Bundled OpenWG checksum mismatch')
    bundle = dist / ('wot-statystyki-sesji-v'+version_tag+'.zip')
    shutil.copyfile(dependency, dist/dependency.name)
    shutil.copyfile(config_path, dist/CONFIG_FILENAME)
    inner_checksums = installer_checksums(package, dependency, config_path, args.client_version, languages_path)
    report = {
        'version': version_tag, 'client_target': args.client_version, 'python_bytecode': '2.7',
        'package_compression': 'ZIP_STORED', 'package_entries': entries,
        'package_sha256': digest(package), 'openwg_sha256': digest(dependency),
        'appearance_config': CONFIG_FILENAME, 'appearance_config_sha256': digest(config_path),
        'languages_config': languages_path.name, 'languages_config_sha256': digest(languages_path),
        'config_directory': 'mods/configs',
        'expected': json.loads((ROOT/'data'/'wn8-source.json').read_text()),
        'live_client_tested': False,
    }
    (dist/'BUILD.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n',encoding='utf-8')
    with zipfile.ZipFile(bundle, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        target = 'mods/'+args.client_version+'/'
        put(z, target+package.name, package.read_bytes())
        put(z, 'mods/configs/'+CONFIG_FILENAME, config_path.read_bytes())
        put(z, 'mods/configs/'+languages_path.name, languages_path.read_bytes())
        put(z, target+'net.openwg/'+dependency.name, dependency.read_bytes())
        for name in ['README_PL.txt', 'ZMIANY.txt', 'LICENSE.txt', 'THIRD_PARTY.txt']:
            put(z, name, render_guide(name, (ROOT/name).read_bytes(), version_tag, args.client_version))
        put(z, 'BUILD.json', (dist/'BUILD.json').read_bytes())
        put(z, 'SHA256SUMS.txt', inner_checksums)
        for directory in ['src','ui','tools','tests','data','resources','third_party','preview','docs']:
            for path in sorted((ROOT/directory).rglob('*')):
                if not path.is_file() or '__pycache__' in path.parts or path.suffix in ('.pyc','.pyo','.wotmod','.png') or path.name.endswith('-report.json') or 'node_modules' in path.parts:
                    continue
                content = path.read_bytes()
                if path == ROOT/'src'/'grz_session_stats'/'__init__.py':
                    content = re.sub(rb"(?m)^VERSION = '[^']+'$", ("VERSION = '"+version_tag+"'").encode('ascii'), content)
                relative = path.relative_to(ROOT).as_posix()
                put(z, 'source/'+relative, render_guide(relative, content, version_tag, args.client_version))
        for name in ['meta.xml','VERSION','README.md','CONTRACT.txt','LICENSE.txt','README_PL.txt','ZMIANY.txt','THIRD_PARTY.txt',CONFIG_FILENAME,languages_path.name]:
            content = (ROOT/name).read_bytes()
            if name == 'meta.xml': content = metadata
            if name == 'VERSION': content = (version_tag+'\n').encode('ascii')
            put(z, 'source/'+name, render_guide(name, content, version_tag, args.client_version))
        # Dependency remains available to a source rebuild without network.
        put(z, 'source/third_party/openwg/'+dependency.name, dependency.read_bytes())
        preview = ROOT/'preview'/'PODGLAD.html'
        if preview.is_file():
            put(z, 'PODGLAD.html', preview.read_bytes())
    # The outer manifest covers every downloadable asset, including the bundle.
    outputs = [package, bundle, dist/dependency.name, dist/CONFIG_FILENAME, dist/'BUILD.json']
    (dist/'SHA256SUMS.txt').write_text(''.join(digest(p)+'  '+p.name+'\n' for p in outputs), encoding='ascii')
    print(json.dumps({'wotmod':str(package), 'zip':str(bundle), 'bytes':bundle.stat().st_size,
                      'sha256':digest(bundle), 'entries':entries},ensure_ascii=False,indent=2))


if __name__ == '__main__':
    main()
