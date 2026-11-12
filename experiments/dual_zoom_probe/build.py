#!/usr/bin/env python3
"""Deterministic offline packaging for the isolated dual-zoom experiment.

The Python 2.7 bytecode bootstrap matches the repository's verified Medkit
builder. No native libraries, hooks, downloads, or shader files are packaged.
"""
import hashlib
from pathlib import Path
import re
import struct
import zipfile
from xml.etree import ElementTree

HERE = Path(__file__).resolve().parent
SOURCE = HERE / 'mod_dual_zoom_probe.py'
VERSION = '0.1.0'
MOD_ID = 'com.grz.dualzoomprobe'
PYC = 'res/scripts/client/gui/mods/mod_dual_zoom_probe.pyc'
TEXTURE = 'res/gui/maps/dual_zoom_probe/solid.dds'
MAGIC_PY27 = b'\x03\xf3\x0d\x0a'


def _i32(value):
    return struct.pack('<i', value)


def _string(value):
    if isinstance(value, str):
        value = value.encode('ascii')
    return b's' + _i32(len(value)) + value


def _tuple(values):
    return b'(' + _i32(len(values)) + b''.join(values)


def make_py27_entrypoint(source):
    if not source.isascii():
        raise ValueError('Runtime must use ASCII-only Python 2.7 source')
    # CPython 2.7 LOAD_CONST(source), LOAD_CONST(None) twice, EXEC_STMT,
    # LOAD_CONST(None), RETURN_VALUE. co_flags=CO_NOFREE; stacksize=3.
    code = bytes((100, 0, 0, 100, 1, 0, 100, 1, 0, 85, 100, 1, 0, 83))
    body = (b'c' + _i32(0) + _i32(0) + _i32(3) + _i32(64)
            + _string(code) + _tuple((_string(source), b'N'))
            + _tuple(()) * 4 + _string('mod_dual_zoom_probe.py')
            + _string('<module>') + _i32(1) + _string(b''))
    return MAGIC_PY27 + struct.pack('<I', 0) + body


def solid_dds():
    """One reusable opaque 16x16 BGRA texture for the non-interactive frame."""
    side = 16
    header = bytearray(128)
    header[:4] = b'DDS '
    struct.pack_into('<I', header, 4, 124)
    struct.pack_into('<I', header, 8, 0x100F)
    struct.pack_into('<III', header, 12, side, side, side * 4)
    struct.pack_into('<IIIIIIII', header, 76,
                     32, 65, 0, 32, 0x00FF0000, 0x0000FF00,
                     0x000000FF, 0xFF000000)
    struct.pack_into('<I', header, 108, 0x1000)
    return bytes(header) + bytes((255, 255, 255, 255)) * (side * side)


def metadata():
    return (('<?xml version="1.0" encoding="UTF-8"?>\n'
             '<root>\n'
             '  <id>{}</id>\n'
             '  <version>{}</version>\n'
             '  <name>Dual Zoom - Engine Probe</name>\n'
             '  <description>Experimental replay-only native scene renderer probe.</description>\n'
             '</root>\n').format(MOD_ID, VERSION)).encode('ascii')


def resources():
    source = SOURCE.read_bytes()
    if source.count(('VERSION = %r' % VERSION).encode('ascii')) != 1:
        raise ValueError('Game runtime version must match package version')
    if not re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+', VERSION):
        raise ValueError('Invalid package version')
    return [('meta.xml', metadata()),
            (PYC, make_py27_entrypoint(source)),
            (TEXTURE, solid_dds())]


def verify(path, expected=None):
    if expected is None:
        expected = dict(resources())
    with zipfile.ZipFile(path, 'r') as archive:
        entries = archive.infolist()
        if (len(entries) != len(expected)
                or set(archive.namelist()) != set(expected)
                or archive.testzip() is not None):
            raise ValueError('Unexpected package contents')
        for info in entries:
            if info.compress_type != zipfile.ZIP_STORED or info.flag_bits & 1:
                raise ValueError('Unexpected compression/encryption')
            if archive.read(info.filename) != expected[info.filename]:
                raise ValueError('Package bytes differ from reviewed sources')
        root = ElementTree.fromstring(archive.read('meta.xml'))
        if root.findtext('id') != MOD_ID or root.findtext('version') != VERSION:
            raise ValueError('Incorrect module metadata')
    return True


def build():
    destination = HERE / 'dist'
    destination.mkdir(exist_ok=True)
    target = destination / ('%s_%s.wotmod' % (MOD_ID, VERSION))
    entries = resources()
    with zipfile.ZipFile(target, 'w', compression=zipfile.ZIP_STORED) as archive:
        for path, content in entries:
            info = zipfile.ZipInfo(path, date_time=(2026, 11, 12, 12, 0, 0))
            info.compress_type = zipfile.ZIP_STORED
            info.create_system = 0
            archive.writestr(info, content)
    verify(target, dict(entries))
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    print('Built: %s' % target)
    print('Bytes: %d' % target.stat().st_size)
    print('SHA-256: %s' % digest)
    return target


if __name__ == '__main__':
    build()
