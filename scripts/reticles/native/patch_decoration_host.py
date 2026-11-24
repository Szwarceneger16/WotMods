# -*- coding: ascii -*-
"""Update our compiled preview host without changing the stock artwork.

The stock WoT SWFs are neither read nor changed by this transform. The host
still loads stock symbols and checks its existing instances, visibility,
opacity, bounds, linkage names and timeline frames. Passing those checks
establishes structural readiness only. The second scoped edit sets the
Leopard 120 speed label to the verified 20 km/h threshold.
"""
from __future__ import absolute_import, print_function

import hashlib
import os
import struct
import zlib


ORIGINAL = 'd487007b777cfff823ae7d0365cacda864322456fab4ea1c5d7c1fb8af235841'
REFERENCE = os.path.join(os.path.dirname(__file__), 'legacy_decoration_host.swf')
STRUCTURAL_END = 165
ORIGINAL_CODE_LENGTH = 424


class Reader(object):
    def __init__(self, data):
        self.data = data
        self.pos = 0

    def take(self, length):
        value = self.data[self.pos:self.pos + length]
        if len(value) != length:
            raise ValueError('Truncated SWF or ABC')
        self.pos += length
        return value

    def byte(self):
        return struct.unpack('B', self.take(1))[0]

    def variable(self):
        value = 0
        for shift in (0, 7, 14, 21, 28):
            part = self.byte()
            value |= (part & 127) << shift
            if not part & 128:
                return value
        raise ValueError('Invalid ABC variable-length integer')

    def variables(self, count):
        for unused in range(count):
            self.variable()


def _u30(value):
    parts = []
    while value >= 128:
        parts.append(struct.pack('B', value & 127 | 128))
        value >>= 7
    parts.append(struct.pack('B', value))
    return b''.join(parts)


def _constant_pool(reader):
    for unused in range(2):
        reader.variables(reader.variable() - 1)
    reader.take(max(0, reader.variable() - 1) * 8)
    pool_offset = reader.pos
    count = reader.variable()
    strings_start = reader.pos
    strings = [b'']
    for unused in range(count - 1):
        strings.append(reader.take(reader.variable()))
    strings_end = reader.pos
    for unused in range(reader.variable() - 1):
        reader.byte()
        reader.variable()
    for unused in range(reader.variable() - 1):
        reader.variables(reader.variable())

    names = [b'']
    for unused in range(reader.variable() - 1):
        kind = reader.byte()
        name = b''
        if kind in (7, 13):
            reader.variable()  # namespace
            name = strings[reader.variable()]
        elif kind in (15, 16):
            name = strings[reader.variable()]
        elif kind in (17, 18):
            pass
        elif kind in (9, 14):
            name = strings[reader.variable()]
            reader.variable()  # namespace set
        elif kind in (27, 28):
            reader.variable()
        elif kind == 29:
            reader.variable()
            reader.variables(reader.variable())
        else:
            raise ValueError('Unexpected ABC name kind')
        names.append(name)
    return names, strings, (pool_offset, strings_start, strings_end)


def _traits(reader):
    for unused in range(reader.variable()):
        name = reader.variable()
        attributes = reader.byte()
        kind = attributes & 15
        reader.variable()  # slot or dispatch ID
        method = None
        if kind in (0, 6):
            reader.variable()  # type
            if reader.variable():
                reader.byte()  # kind of initial value
        elif kind in (1, 2, 3, 5):
            method = reader.variable()
        elif kind == 4:
            reader.variable()
        else:
            raise ValueError('Unexpected ABC trait')
        if attributes & 64:
            reader.variables(reader.variable())
        if method is not None:
            yield name, method


def _method_record(abc, member):
    reader = Reader(abc)
    reader.take(4)  # ABC versions
    names, unused_strings, unused_bounds = _constant_pool(reader)
    for unused in range(reader.variable()):
        parameters = reader.variable()
        reader.variables(parameters + 2)
        flags = reader.byte()
        if flags & 8:
            for unused_option in range(reader.variable()):
                reader.variable()
                reader.byte()
        if flags & 128:
            reader.variables(parameters)
    for unused in range(reader.variable()):
        reader.variable()  # metadata name
        reader.variables(reader.variable() * 2)

    classes = reader.variable()
    targets = []
    for unused in range(classes):
        owner = names[reader.variable()]
        reader.variable()  # base name
        if reader.byte() & 8:
            reader.variable()  # protected namespace
        reader.variables(reader.variable())
        reader.variable()  # instance initializer
        for name, method in _traits(reader):
            if owner == b'GRZReticlePreview' and names[name] == member:
                targets.append(method)
    for unused in range(classes):
        reader.variable()  # class initializer
        list(_traits(reader))
    for unused in range(reader.variable()):
        reader.variable()  # script initializer
        list(_traits(reader))

    records = []
    for unused in range(reader.variable()):
        method = reader.variable()
        reader.variables(4)  # stack, locals and scope bounds
        code_length_offset = reader.pos
        code = reader.take(reader.variable())
        exceptions = reader.variable()
        reader.variables(exceptions * 5)
        traits_offset = reader.pos
        list(_traits(reader))
        if method in targets:
            records.append((code_length_offset, code, exceptions, traits_offset))
    if not targets:
        return None
    if len(targets) != 1 or len(records) != 1 or reader.pos != len(abc):
        raise ValueError('Expected one complete owned validation method')
    return records[0]


def _tags(body):
    rect_bits = 5 + 4 * (struct.unpack('B', body[:1])[0] >> 3)
    reader = Reader(body)
    reader.take((rect_bits + 7) // 8 + 4)  # frame size, rate, count
    while reader.pos < len(body):
        start = reader.pos
        tag, = struct.unpack('<H', reader.take(2))
        kind, length = tag >> 6, tag & 63
        if length == 63:
            length, = struct.unpack('<I', reader.take(4))
        data = reader.take(length)
        yield start, reader.pos, kind, data


def _uncompress(raw):
    if raw[:3] == b'CWS':
        body = zlib.decompress(raw[8:])
    elif raw[:3] == b'FWS':
        body = raw[8:]
    else:
        raise ValueError('Expected our SWF')
    if len(body) + 8 != struct.unpack('<I', raw[4:8])[0]:
        raise ValueError('Incorrect SWF length')
    return body


def inspect(raw, member=b'visiblePixels'):
    body = _uncompress(raw)
    matches = []
    for start, end, kind, tag in _tags(body):
        if kind != 82:  # DoABC
            continue
        header_end = tag.index(b'\0', 4) + 1
        abc = tag[header_end:]
        record = _method_record(abc, member)
        if record is not None:
            matches.append((start, end, tag[:header_end], abc, record))
    if len(matches) != 1:
        raise ValueError('Expected one owned validation method in SWF')
    return body, matches[0]


def _accuracy_label_patch(abc):
    """Edit one setup instruction for the original Leopard accuracy symbol."""
    reader = Reader(abc)
    reader.take(4)
    unused_names, strings, (count_offset, string_start, string_end) = _constant_pool(reader)
    if strings.count(b'15') != 1 or b'20' in strings:
        raise ValueError('Unexpected string pool in accuracy widget setup')
    setup_offset, setup_code, unused_catches, unused_traits = _method_record(abc, b'prepareGrandchildren')
    old_push = b'\x2c' + _u30(strings.index(b'15'))  # pushstring
    new_push = b'\x2c' + _u30(len(strings))
    if (setup_code.count(old_push) != 1 or setup_code.index(old_push) != 140 or
            len(old_push) != len(new_push)):
        raise ValueError('Expected one fixed-width accuracy label instruction')
    target = setup_offset + len(_u30(len(setup_code))) + setup_code.index(old_push)
    extra_string = _u30(2) + b'20'
    # Keep the old string index intact. Only the accuracy setup instruction
    # uses the additional constant. The timeline has no branch changes.
    return (abc[:count_offset] + _u30(len(strings) + 1) +
            abc[string_start:string_end] + extra_string +
            abc[string_end:target] + new_push + abc[target + len(old_push):])


def patch(raw):
    if hashlib.sha256(raw).hexdigest() != ORIGINAL:
        raise ValueError('Refusing to patch an unrecognized decoration host')
    body, (start, end, abc_header, abc, record) = inspect(raw)
    offset, code, catches, traits_offset = record
    # The successful branch of the last structural check lands at offset 165.
    # The following instructions allocate and read back BitmapData.
    if (len(code) != ORIGINAL_CODE_LENGTH or catches != 2 or
            code[142:146] != b'\x12\x13\x00\x00'):
        raise ValueError('Unexpected validation code or structural branch')
    structural = code[:STRUCTURAL_END] + b'\x47'  # returnvoid
    structural_abc = abc[:offset] + _u30(len(structural)) + structural + b'\0' + abc[traits_offset:]
    new_abc = _accuracy_label_patch(structural_abc)
    new_tag = abc_header + new_abc
    new_body = (body[:start] + struct.pack('<HI', (82 << 6) | 63, len(new_tag)) +
                new_tag + body[end:])
    payload = zlib.compress(new_body, 9) if raw[:3] == b'CWS' else new_body
    result = raw[:4] + struct.pack('<I', len(new_body) + 8) + payload
    checked_body, (checked_start, checked_end, checked_header, checked_abc, checked_record) = inspect(result)
    unused_offset, checked_code, checked_catches, unused_traits_offset = checked_record
    if (checked_body[:checked_start] != body[:start] or checked_body[checked_end:] != body[end:] or
            checked_header != abc_header or checked_abc != new_abc or
            checked_code != structural or checked_catches != 0):
        raise ValueError('SWF verification found another change')
    return result
