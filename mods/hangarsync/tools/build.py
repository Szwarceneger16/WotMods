#!/usr/bin/env python3
"""Deterministically package the isolated GRZ Hangar Sync WoT client mod.

The bootstrap technique is the same tested Python 2.7 EXEC_STMT layout as the
existing Stay Sharp builder. Nothing is downloaded or executed by the mod.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
from zipfile import ZIP_DEFLATED, ZIP_STORED, ZipFile, ZipInfo

ROOT = Path(__file__).resolve().parents[1]
BASE_VERSION = (ROOT / 'VERSION').read_text(encoding='ascii').strip()
MODULE = ROOT / 'source' / 'mod_grz_hangar_sync.py'
CONFIG = ROOT / 'GRZ_Hangar_Sync.json.example'
PYC_PATH = 'res/scripts/client/gui/mods/mod_grz_hangar_sync.pyc'
HELPERS = {
    'grz_hangar_crew': ROOT / 'source' / 'hangar_crew.py',
    'grz_hangar_stats': ROOT / 'source' / 'hangar_stats.py',
    'grz_hangar_mission_metadata': ROOT / 'source' / 'hangar_mission_metadata.py',
}
WOTMOD_NAME = 'GRZ_Hangar_Sync.wotmod'
MOD_ID = 'com.grz.hangarsync'
MAGIC_PY27 = b'\x03\xf3\r\n'
ZIP_DATE = (2026, 11, 3, 0, 0, 0)


def _int32(value):
    return struct.pack('<i', value)


def _str(value):
    if isinstance(value, str):
        value = value.encode('ascii')
    return b's' + _int32(len(value)) + value


def _tuple(entries):
    return b'(' + _int32(len(entries)) + b''.join(entries)


def build_py27_bootstrap(source):
    """LOAD_CONST/EXEC_STMT self-contained CPython 2.7 module (8-byte header)."""
    if not source.isascii():
        raise ValueError('WoT bootstrap source must be ASCII')
    code = bytes((100, 0, 0, 100, 1, 0, 100, 1, 0, 85, 100, 1, 0, 83))
    body = (b'c' + _int32(0) + _int32(0) + _int32(3) + _int32(64)
            + _str(code) + _tuple((_str(source), b'N'))
            + _tuple(()) + _tuple(()) + _tuple(()) + _tuple(())
            + _str('mod_grz_hangar_sync.py') + _str('<module>')
            + _int32(1) + _str(b''))
    return MAGIC_PY27 + struct.pack('<I', 0) + body


def _put(archive, name, data, compression):
    info = ZipInfo(name, ZIP_DATE)
    info.compress_type = compression
    info.external_attr = 0o644 << 16
    archive.writestr(info, data)


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def build(version=None, client_version='2.4.1.1'):
    version = version or BASE_VERSION
    if not re.fullmatch(r'\d+\.\d+\.\d+', version):
        raise ValueError('Version must use semantic X.Y.Z notation')
    if not re.fullmatch(r'\d+\.\d+\.\d+\.\d+', client_version):
        raise ValueError('Client version must have four numeric parts')
    source = MODULE.read_bytes()
    expected = ("VERSION = '%s'" % BASE_VERSION).encode('ascii')
    if source.count(expected) != 1:
        raise ValueError('Source version marker is missing or ambiguous')
    source = source.replace(expected, ("VERSION = '%s'" % version).encode('ascii'))
    config_bytes = CONFIG.read_bytes()
    example = json.loads(config_bytes)
    private_fields = ('endpoint_url', 'device_token', 'sites_access_token',
                      'display_name')
    if (example.get('enabled') is not False or
            example.get('allowed_players') != [] or 'expected_player' in example or
            any(example.get(field) != '' for field in private_fields)):
        raise ValueError('Installer must contain an opt-out, credential-free example')
    if b'https://' in source or b'http://' in source:
        raise ValueError('Mod source must not embed any specific sync destination')
    metadata = ('<?xml version="1.0" encoding="UTF-8"?>\n'
                '<root>\n'
                '  <id>%s</id>\n'
                '  <version>%s</version>\n'
                '  <name>GRZ Hangar Sync</name>\n'
                '  <description>Opt-in private garage and mission snapshots during the game session.</description>\n'
                '</root>\n' % (MOD_ID, version)).encode('utf-8')
    dist = ROOT / 'dist'
    dist.mkdir(exist_ok=True)
    mod_path = dist / WOTMOD_NAME
    with ZipFile(mod_path, 'w', compression=ZIP_STORED) as archive:
        _put(archive, 'meta.xml', metadata, ZIP_STORED)
        _put(archive, PYC_PATH, build_py27_bootstrap(source), ZIP_STORED)
        for name, helper in sorted(HELPERS.items()):
            _put(archive, 'res/scripts/client/gui/mods/' + name + '.pyc',
                 build_py27_bootstrap(helper.read_bytes()), ZIP_STORED)
    with ZipFile(mod_path) as archive:
        assert archive.testzip() is None
        assert set(archive.namelist()) == {'meta.xml', PYC_PATH} | {
            'res/scripts/client/gui/mods/' + name + '.pyc' for name in HELPERS}
        assert archive.read(PYC_PATH).startswith(MAGIC_PY27)
        assert source in archive.read(PYC_PATH)
        assert all(f.compress_type == ZIP_STORED for f in archive.infolist())

    installer_path = dist / ('GRZ_Hangar_Sync-v%s.zip' % version)
    target = 'mods/%s/%s' % (client_version, WOTMOD_NAME)
    config_target = 'mods/configs/GRZ_Hangar_Sync.json.example'
    mod_bytes = mod_path.read_bytes()
    digest_lines = ('%s  %s\n%s  %s\n' % (
        _sha(mod_bytes), target, _sha(config_bytes), config_target)).encode('ascii')
    with ZipFile(installer_path, 'w', compression=ZIP_DEFLATED, compresslevel=9) as archive:
        _put(archive, target, mod_bytes, ZIP_DEFLATED)
        _put(archive, config_target, config_bytes, ZIP_DEFLATED)
        _put(archive, 'README.md', (ROOT / 'README.md').read_bytes(), ZIP_DEFLATED)
        _put(archive, 'SHA256SUMS.txt', digest_lines, ZIP_DEFLATED)
    with ZipFile(installer_path) as archive:
        assert archive.testzip() is None
        assert len(archive.namelist()) == len(set(archive.namelist())) == 4
        assert archive.read(target) == mod_bytes
        assert archive.read(config_target) == config_bytes
    return {'wotmod': str(mod_path), 'installer': str(installer_path),
            'sha256': _sha(installer_path.read_bytes()), 'client_version': client_version}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version', default=BASE_VERSION)
    parser.add_argument('--client-version', default='2.4.1.1')
    args = parser.parse_args()
    print(json.dumps(build(args.version, args.client_version), sort_keys=True, indent=2))


if __name__ == '__main__':
    main()
