#!/usr/bin/env python3
"""Build self-contained ZIP_STORED WoT .wotmod with Python 2.7 bootstrap.

CPython 2.7's EXEC_STMT loads ASCII Py2 compatible code embedded in .pyc,
using the same working bootstrap technique as versions 1.0.0-1.4.0.
Nothing is fetched or installed at runtime.
"""
import base64
import hashlib
import importlib.util
import math
import os
import re
import zlib
from pathlib import Path
import struct
import zipfile
from xml.etree import ElementTree

HERE = Path(__file__).resolve().parent
SOURCE = HERE / 'mod_staysharp_medkit.py'
ASSETS = HERE.parent / 'assets'
_audio_spec = importlib.util.spec_from_file_location('staysharp_audio_builder', HERE / 'build_audio_bank.py')
audio = importlib.util.module_from_spec(_audio_spec)
_audio_spec.loader.exec_module(audio)
MOD_ID = 'com.staysharp.medkitreminder'
BASE_VERSION = (HERE.parent / 'VERSION').read_text(encoding='ascii').strip()
VERSION = os.environ.get('WOTMOD_VERSION', BASE_VERSION)
base_parts = BASE_VERSION.split('.')
if len(base_parts) != 3 or not all(part.isdigit() for part in base_parts):
    raise ValueError('Invalid baseline VERSION file')
if not re.fullmatch(r'\d+\.\d+\.(0|[1-9]\d*)', VERSION):
    raise ValueError('Invalid WOTMOD_VERSION')
if VERSION.split('.')[:2] != base_parts[:2] or int(VERSION.split('.')[-1]) < int(base_parts[-1]):
    raise ValueError('Release version must belong to current major.minor series')
PYC_PATH = 'res/scripts/client/gui/mods/mod_staysharp_medkit.pyc'
DDS_PREFIX = 'res/gui/maps/staysharp/medkit_pulse_'
FRAME_COUNT = 21
MAGIC_PY27 = b'\x03\xf3\x0d\x0a'


def int32(number):
    return struct.pack('<i', number)


def pstring(value):
    if isinstance(value, str):
        value = value.encode('ascii')
    return b's' + int32(len(value)) + value


def tup(items):
    return b'(' + int32(len(items)) + b''.join(items)


def make_py27_entrypoint(source):
    if not source.isascii():
        raise ValueError('embedded source must be ASCII')
    # LOAD_CONST(source), LOAD_CONST(None), LOAD_CONST(None), EXEC_STMT,
    # LOAD_CONST(None), RETURN_VALUE; co_stacksize=3, co_flags=CO_NOFREE.
    code = bytes((100,0,0,100,1,0,100,1,0,85,100,1,0,83))
    body = (b'c' + int32(0) + int32(0) + int32(3) + int32(64)
            + pstring(code) + tup((pstring(source), b'N'))
            + tup(()) + tup(()) + tup(()) + tup(())
            + pstring('mod_staysharp_medkit.py') + pstring('<module>')
            + int32(1) + pstring(b''))
    return MAGIC_PY27 + struct.pack('<I',0) + body


def render_source():
    """Patch the runtime VERSION constant for automatic releases."""
    original = SOURCE.read_bytes()
    baseline = ("VERSION = '%s'" % BASE_VERSION).encode('ascii')
    replacement = ("VERSION = '%s'" % VERSION).encode('ascii')
    if original.count(baseline) != 1:
        raise ValueError('Runtime version constant no longer matches VERSION')
    result = original.replace(baseline, replacement, 1)
    if VERSION != BASE_VERSION:
        original_heading = ('Reminder v%s ' % BASE_VERSION).encode('ascii')
        new_heading = ('Reminder v%s ' % VERSION).encode('ascii')
        if result.count(original_heading) != 1:
            raise ValueError('Runtime source heading no longer matches VERSION')
        result = result.replace(original_heading, new_heading, 1)
    return result


def load_master():
    content = (ASSETS / 'medkit_pulse_master.dds.b85').read_text(encoding='ascii')
    payload = zlib.decompress(base64.b85decode(''.join(content.split()).encode('ascii')))
    expected = (ASSETS / 'medkit_pulse_master.sha256').read_text(encoding='ascii').strip()
    if not re.fullmatch(r'[0-9a-f]{64}', expected):
        raise ValueError('Malformed DDS master checksum')
    if hashlib.sha256(payload).hexdigest() != expected:
        raise ValueError('Master DDS integrity mismatch')
    return payload


def load_frames():
    """Exactly reconstruct 21 production frames from one DDS master."""
    master = load_master()
    out = []
    previous = None
    for i in range(FRAME_COUNT):
        frame = bytearray(master)
        for offset in range(131, len(frame), 4):
            frame[offset] = (master[offset] * i + 10) // 20
        payload = bytes(frame)
        path = 'medkit_pulse_%02d.dds' % i
        if len(payload) != 128 + 128*128*4 or payload[:4] != b'DDS ':
            raise ValueError('Bad DDS: %s' % path)
        size, = struct.unpack_from('<I', payload, 4)
        h, w = struct.unpack_from('<II', payload, 12)
        pfsize, flags, fourcc, bpp, r, g, b, a = struct.unpack_from('<IIIIIIII',payload,76)
        if (size, h, w, pfsize, flags, fourcc, bpp, r, g, b, a) != (
                 124, 128, 128, 32, 65, 0, 32, 0xff0000, 0xff00, 0xff, 0xff000000):
            raise ValueError('DDS pixel-format mismatch: %s' % path)
        alpha = payload[131::4]
        if i == 0 and max(alpha) != 0:
            raise ValueError('First frame not transparent')
        if previous is not None and any(x < y for x,y in zip(alpha,previous)):
            raise ValueError('Opacity decreases between consecutive frames')
        previous = alpha
        out.append((DDS_PREFIX + ('%02d.dds' % i), payload))
    if max(out[-1][1][131::4]) < 240:
        raise ValueError('Last frame not sufficiently opaque')
    return out


def load_control_icons():
    """Draw compact native-style power/speaker glyphs into deterministic DDS."""
    size = 64
    header = bytearray(load_master()[:128])
    struct.pack_into('<III', header, 12, size, size, size * 4)
    icons = []
    for action in ('power', 'voice'):
        for enabled in (True, False):
            pixels = bytearray()
            for y in range(size):
                for x in range(size):
                    dx, dy = x - 31.5, y - 31.5
                    # Rounded dark panel with a shallow metallic upper highlight.
                    corner = math.hypot(max(abs(dx) - 24.0, 0), max(abs(dy) - 24.0, 0))
                    if corner > 7.0:
                        pixels.extend((0, 0, 0, 0))
                        continue
                    shade = int(34 + max(0.0, 1.0 - y / 34.0) * 18)
                    colour = (shade + 5, shade + 2, shade, 235)
                    if corner > 5.0 or max(abs(dx), abs(dy)) > 29:
                        colour = (100, 92, 72, 245)
                    if action == 'power':
                        radius = math.hypot(dx, dy)
                        glyph = (17.0 <= radius <= 22.0 and (dy > -13.0 or abs(dx) > 11.0)) or (abs(dx) <= 2.5 and -23 <= dy <= -1)
                    else:
                        speaker = (14 <= x <= 23 and 26 <= y <= 38) or (23 <= x <= 36 and abs(y - 32) <= 6 + (x - 23) * 0.8)
                        radius = math.hypot(x - 34, y - 32)
                        waves = x > 40 and (12 <= radius <= 15 or 21 <= radius <= 24)
                        glyph = speaker or waves
                    if glyph:
                        colour = (223, 200, 119, 255) if enabled else (130, 132, 132, 255)
                    if not enabled and abs((x + y) - 63) <= 2 and 12 <= x <= 51 and 12 <= y <= 51:
                        colour = (221, 81, 61, 255)
                    red, green, blue, alpha = colour
                    pixels.extend((blue, green, red, alpha))
            name = 'res/gui/maps/staysharp/control_%s_%s.dds' % (action, 'on' if enabled else 'off')
            icons.append((name, bytes(header) + bytes(pixels)))
    return icons


def verify(target, source, frames, sounds):
    wanted = {'meta.xml', PYC_PATH} | {p for p, _ in frames + sounds}
    with zipfile.ZipFile(target) as archive:
        assert archive.testzip() is None
        assert set(archive.namelist()) == wanted
        assert all(x.compress_type == zipfile.ZIP_STORED for x in archive.infolist())
        assert all(not x.flag_bits & 1 for x in archive.infolist())
        pyc = archive.read(PYC_PATH)
        assert pyc.startswith(MAGIC_PY27)
        assert source in pyc
        for path, bytes_ in frames + sounds:
            assert archive.read(path) == bytes_
        meta = ElementTree.fromstring(archive.read('meta.xml'))
        assert meta.findtext('id') == MOD_ID
        assert meta.findtext('version') == VERSION


def build():
    dest = HERE.parent / 'dist'
    dest.mkdir(exist_ok=True)
    source = render_source()
    frames = load_frames() + load_control_icons()
    sounds = audio.resources()
    pyc = make_py27_entrypoint(source)
    metadata = (('<?xml version="1.0" encoding="UTF-8"?>\n'
                 '<root>\n'
                 '  <id>{}</id>\n'
                 '  <version>{}</version>\n'
                 '  <name>Stay Sharp - Medkit Reminder</name>\n'
                 '  <description>Medkit outline with repeating ready voice and a battle toggle.</description>\n'
                 '</root>\n').format(MOD_ID, VERSION)).encode('utf-8')
    target = dest / ('%s_%s.wotmod' % (MOD_ID,VERSION))
    with zipfile.ZipFile(target, 'w', compression=zipfile.ZIP_STORED) as archive:
        for path, payload in [('meta.xml', metadata), (PYC_PATH, pyc)] + frames + sounds:
            info=zipfile.ZipInfo(path, date_time=(2026,10,21,11,0,0))
            info.compress_type=zipfile.ZIP_STORED
            info.create_system=0
            archive.writestr(info, payload)
    verify(target,source,frames,sounds)
    sha = hashlib.sha256(target.read_bytes()).hexdigest()
    print('Build:',target,'bytes:',target.stat().st_size,'SHA256:',sha)
    return target


if __name__=='__main__':
    build()
