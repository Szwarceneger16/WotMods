# -*- coding: ascii -*-
"""Show the verified CAV, Leopard, and Hirsch stock snapshots in our host.

Only our compiled adapter's selections change. This tool does not read,
rewrite, copy or render stock graphics. All method edits preserve instruction
offsets, exception tables and the library/class-loading contract.
"""
from __future__ import absolute_import, print_function

import binascii
import hashlib
import struct
import zlib

from patch_decoration_ancestry import OwnedAbc
from patch_decoration_host import _method_record, _tags, _u30, _uncompress

REFERENCE = '912e87d4dc04085dbfb0ef1e11f87d63b2f9c08d892039a512b5ba7b00909121'


def _hex(value):
    return binascii.unhexlify(value.replace(' ', ''))


def _edit(abc, method, edits):
    record = _method_record(abc, method)
    if record is None:
        raise ValueError('Owned method is absent')
    offset, code, unused_catches, unused_traits = record
    start = offset + len(_u30(len(code)))
    for position, original, replacement in edits:
        if (not original or len(replacement) > len(original) or
                code[position:position + len(original)] != original):
            raise ValueError('Unexpected owned timeline setup instruction')
        # Edited branches lie wholly within an individual replacement.
        # Padding preserves the surrounding instruction offsets.
        replacement += b'\x02' * (len(original) - len(replacement))
        code = code[:position] + replacement + code[position + len(original):]
    return abc[:start] + code + abc[start + len(code):]


def _string_operand(strings, value):
    return b'\x2c' + _u30(strings.index(value))  # pushstring


def _snapshot_code(abc, strings):
    # CAV's three stored charges are READY, before spending one. The stock
    # ACTIVE beam/glow follows a spend and must not be frozen in this state.
    old_label = _string_operand(strings, b'active_instantly')
    ready = _string_operand(strings, b'ready_instantly')
    if len(ready) != len(old_label):
        raise ValueError('Unexpected width of ready frame label')
    abc = _edit(abc, b'prepareRoot', ((81, old_label, ready),))
    abc = _edit(abc, b'prepareSurgeChildren', (
        (132, b'\x24\x22', b'\x24\x01'),  # initial actionLine frame
        (155, b'\x26', b'\x27'),             # hide actionLine.pointer
        # The availability pulse ends transparent on its own. The original
        # timerBlink overlay holds at frame 10 while a charge can be spent.
        (173, _hex('5d72 6048 2ce802 467202 27 61c501 '
                   '5d72 6048 2ce902 467202 27 61c501'),
         _hex('5d71 5d70 6048 2ce902 467002 240a 4f7102')),
        (213, b'\x24\x0f', b'\x24\x01'),  # initial timerGlow frame
    ))
    abc = _edit(abc, b'prepareSurgeGrandchildren', (
        (301, _hex('d2 24 00 14 07 00 00 25 96 01 10 02 00 00 24 01'),
         b'\x25' + _u30(150)),  # all sectors, original maximum progress frame
    ))

    # Leopard's 4th stack fills both original bars (600 frames). The full
    # subclip stops at the end of its SHOW expansion, frame 16. Stock hides
    # both progress marks and the speed-limit badge at the maximum.
    old_bar, full_bar = b'\x25' + _u30(375), b'\x25' + _u30(600)
    if len(old_bar) != len(full_bar):
        raise ValueError('Unexpected width of accuracy-bar frame instruction')
    abc = _edit(abc, b'prepareChildren', (
        (130, old_bar, full_bar), (148, old_bar, full_bar),
    ))
    abc = _edit(abc, b'prepareAccuracy', (
        # Replace mark.gotoAndStop("cycle") with mark.visible = false.
        (8, _hex('5d 71 5d 70 d1 2c de 02 46 70 02 2c 82 03 4f 71 02'),
         _hex('5d 72 d1 2c de 02 46 72 02 27 61 c5 01')),
        (36, b'\x24\x18', b'\x24\x10'),  # full.gotoAndStop(16)
    ))
    old_damage = _string_operand(strings, b'400')
    max_damage = _string_operand(strings, b'750')
    if len(old_damage) != len(max_damage):
        raise ValueError('Unexpected width of overheat counter instruction')
    abc = _edit(abc, b'prepareGrandchildren', (
        # Stock hides the speed limit at max; the former 20 km/h text setter
        # is replaced by hiding the original markLeft object.
        (94, _hex('5d 70 60 48 2c c8 02 46 70 02 80 01 d5 '
                  '5d 03 5d 72 d1 2c cf 02 46 72 02 46 03 01 80 03 d6 '
                  '5d c3 01 5d 72 d2 2c d2 02 46 72 02 46 c3 01 01 '
                  '2c aa 03 61 c2 01'),
         _hex('5d 72 60 48 2c c8 02 46 72 02 27 61 c5 01')),
        # Both stock fields show the same maximum Hirsch damage: 600 x 1.25.
        (274, old_damage, max_damage), (339, old_damage, max_damage),
    ))
    # This phase runs one display frame after progress.gotoAndStop(150).
    # The full progress frame creates the original highlight as child 3.
    # Snapshot its authored terminal frame before validating each sector.
    return _edit(abc, b'validateGraphic', (
        (39, _hex('5d6f 5d72 6048 2ce202 467202 4f6f01 '
                  '5d6f 5d72 6048 2ce602 467202 4f6f01 '
                  '5d70 6048 2ce202 467002 8001 d5 2400 73 d6 10130000 '
                  '09 5d6f 5d72 d1 2ce402 d2 a0 467202 4f6f01 '
                  'c202 d2 2403 15e6ffff'),
         _hex('5d70 6048 2ce202 467002 8001 d5 2400 73 d6 102d0000 '
              '09 5d72 d1 2ce402 d2 a0 467202 d7 '
              '5d71 5d70 d3 2ce002 467002 2403 46e70101 8001 2414 4f7102 '
              '5d6f d3 4f6f01 c202 d2 2403 15ccffff')),
        # The separate speed badge is hidden at max Leopard accuracy.
        (159, _hex('5d 6f 5d 72 60 48 2c c8 02 46 72 02 4f 6f 01'), b''),
    ))


def patch_samples(raw):
    if hashlib.sha256(raw).hexdigest() != REFERENCE:
        raise ValueError('Refusing to patch an unrecognized owned host')
    body = _uncompress(raw)
    tags = list(_tags(body))
    matches = [entry for entry in tags if entry[2] == 82]
    if len(matches) != 1:
        raise ValueError('Expected one owned ABC tag')
    start, end, kind, data = matches[0]
    header_end = data.index(b'\0', 4) + 1
    header, original = data[:header_end], data[header_end:]
    model = OwnedAbc(original)
    if model.encode() != original or any(text in model.strings for text in (b'ready_instantly', b'750')):
        raise ValueError('Unexpected owned class table or string pool')
    model.strings.extend((b'ready_instantly', b'750'))
    changed = _snapshot_code(model.encode(), model.strings)
    verified = OwnedAbc(changed)
    if verified.encode() != changed:
        raise ValueError('Updated snapshot ABC does not round trip')
    tag = header + changed
    new_body = body[:start] + struct.pack('<HI', (kind << 6) | 63, len(tag)) + tag + body[end:]
    payload = zlib.compress(new_body, 9) if raw[:3] == b'CWS' else new_body
    result = raw[:4] + struct.pack('<I', len(new_body) + 8) + payload
    if [(kind, item) for _, _, kind, item in _tags(_uncompress(result)) if kind != 82] != [
            (kind, item) for _, _, kind, item in tags if kind != 82]:
        raise ValueError('Unexpected non-code changes to owned SWF')
    return result
