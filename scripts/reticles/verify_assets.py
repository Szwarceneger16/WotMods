#!/usr/bin/env python3
"""Verify the curated preview art in a freshly built, standalone mod."""
import hashlib
import struct
import sys
from pathlib import Path
from zipfile import ZipFile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from privacy_audit import scan_text

ASSETS = Path(__file__).resolve().parent / 'assets'
PNG_SIGNATURE = b'\x89PNG\r\n\x1a\n'
PNG_IMAGE_CHUNKS = {b'IHDR', b'IDAT', b'IEND', b'PLTE', b'tRNS', b'gAMA', b'cHRM', b'pHYs', b'sRGB'}
SCENES = {'scenes/arty_trajectory_2.png'} | {
    f'scenes/{view}_{step}.png'
    for view in ('arcade', 'sniper', 'arty_top')
    for step in range(5)
}


def verify_image(name, data):
    if not data.startswith(PNG_SIGNATURE) or struct.unpack_from('>II', data, 16) != (1920, 1080):
        raise ValueError(f'Expected a Full HD preview image: {name}')
    offset = len(PNG_SIGNATURE)
    while offset + 12 <= len(data):
        count, chunk = struct.unpack_from('>I4s', data, offset)
        if chunk not in PNG_IMAGE_CHUNKS:
            raise ValueError(f'Unexpected image metadata: {name}')
        offset += 12 + count
        if chunk == b'IEND':
            if offset == len(data):
                return
            break
    raise ValueError(f'Unexpected image structure: {name}')


def verify(module, version, archive):
    reviewed = {}
    for entry in (ASSETS / 'scene-checksums.txt').read_text(encoding='ascii').splitlines():
        checksum, name = entry.split('  ', 1)
        if name in reviewed:
            raise ValueError('Duplicate preview checksum')
        reviewed[name] = checksum
    if set(reviewed) != SCENES:
        raise ValueError('Expected the reviewed set of scene images')
    prefix = f"res/gui/gameface/mods/grz_{module}/v{version.replace('.', '_')}/"
    with ZipFile(archive) as package:
        names = package.namelist()
        actual = {name[len(prefix):] for name in names if name.startswith(prefix + 'scenes/')}
        if actual != SCENES or len(set(names)) != len(names):
            raise ValueError('Unexpected package image set')
        for name, expected in reviewed.items():
            data = package.read(prefix + name)
            verify_image(name, data)
            if hashlib.sha256(data).hexdigest() != expected:
                raise ValueError(f'Preview content differs from the reviewed image: {name}')
        for name in names:
            if Path(name).suffix in {'.html', '.css', '.js', '.json', '.xml'}:
                problems = scan_text(Path(name), package.read(name))
                if problems:
                    raise ValueError(f'Privacy audit blocked {name}: {", ".join(problems)}')


if __name__ == '__main__':
    verify(*sys.argv[1:])
    print('Verified reviewed Full HD scene bytes and distributable UI text')
