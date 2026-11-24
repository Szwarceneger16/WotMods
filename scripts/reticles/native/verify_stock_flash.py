# -*- coding: ascii -*-
"""Verify the preview's stock SWF contracts without extracting game files."""
from __future__ import absolute_import, print_function

import argparse
import hashlib
import json
import os
import re
import struct
import sys
import xml.etree.ElementTree as ET
import zipfile
import zlib

from patch_decoration_host import Reader, _tags


MANIFEST = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'stock_flash_contract.json')
MAX_MOVIE = 16 * 1024 * 1024
MOVIE_CLIP = 'flash.display::MovieClip'
SPRITE = 'flash.display::Sprite'
DISPLAY_CHAIN = (
    'Object', 'flash.events::EventDispatcher', 'flash.display::DisplayObject',
    'flash.display::InteractiveObject', 'flash.display::DisplayObjectContainer', SPRITE,
)
STRUCTURE_ERROR = 'Stock preview SWF format or structure is incompatible'


class Abc(object):
    """The constant pool and declaration tables needed by the linkage audit."""

    def __init__(self, data):
        reader = Reader(data)
        self.version = struct.unpack('<HH', reader.take(4))
        self._read_names(reader)
        self._skip_methods(reader)
        class_count = reader.variable()
        self.names = []
        self.bases = {}
        for unused in range(class_count):
            name = self._qualified(reader.variable())
            base = self._qualified(reader.variable())
            if name is None or name in self.bases:
                raise ValueError(STRUCTURE_ERROR)
            self.names.append(name)
            self.bases[name] = base
            if reader.byte() & 8:
                reader.variable()  # Protected namespace.
            reader.variables(reader.variable())
            reader.variable()  # Constructor.
            self._read_traits(reader)
        for unused in range(class_count):
            reader.variable()
            self._read_traits(reader)
        self.initializers = {}
        initializer_ids = set()
        for unused in range(reader.variable()):
            method = reader.variable()
            for name, class_id in self._read_traits(reader):
                if name != self.names[class_id] or name in self.initializers:
                    raise ValueError(STRUCTURE_ERROR)
                self.initializers[name] = (method, class_id)
                initializer_ids.add(method)
        self.scripts = {}
        for unused in range(reader.variable()):
            method = reader.variable()
            reader.variables(4)  # Stack/local/scope constraints.
            code = reader.take(reader.variable())
            reader.variables(reader.variable() * 5)
            self._read_traits(reader)
            if method in initializer_ids:
                self.scripts[method] = code
        if reader.pos != len(data):
            raise ValueError(STRUCTURE_ERROR)

    def _read_names(self, reader):
        for unused in range(2):
            reader.variables(max(0, reader.variable() - 1))
        reader.take(max(0, reader.variable() - 1) * 8)
        self.strings = [b'']
        self.strings += [reader.take(reader.variable()) for unused in range(reader.variable() - 1)]
        self.namespaces = [None]
        self.namespaces += [(reader.byte(), reader.variable()) for unused in range(reader.variable() - 1)]
        for unused in range(reader.variable() - 1):
            reader.variables(reader.variable())
        self.multinames = [None]
        for unused in range(reader.variable() - 1):
            kind = reader.byte()
            value = None
            if kind in (7, 13):
                value = (reader.variable(), reader.variable())
            elif kind in (9, 14):
                reader.variables(2)
            elif kind in (15, 16, 27, 28):
                reader.variable()
            elif kind == 29:
                reader.variable()
                reader.variables(reader.variable())
            elif kind not in (17, 18):
                raise ValueError(STRUCTURE_ERROR)
            self.multinames.append(value)

    def _qualified(self, index):
        value = self.multinames[index]
        if value is None:
            return None
        namespace, name = value
        unused_kind, package = self.namespaces[namespace]
        package, name = self.strings[package].decode('utf-8'), self.strings[name].decode('utf-8')
        return package + '::' + name if package else name

    @staticmethod
    def _skip_methods(reader):
        for unused in range(reader.variable()):
            params = reader.variable()
            reader.variables(params + 2)
            flags = reader.byte()
            if flags & 8:
                for unused_option in range(reader.variable()):
                    reader.variable()
                    reader.byte()
            if flags & 128:
                reader.variables(params)
        for unused in range(reader.variable()):
            reader.variable()
            reader.variables(reader.variable() * 2)

    def _read_traits(self, reader):
        classes = []
        for unused in range(reader.variable()):
            name, attributes = reader.variable(), reader.byte()
            reader.variable()  # Slot or dispatch ID.
            kind = attributes & 15
            if kind in (0, 6):
                reader.variable()
                if reader.variable():
                    reader.byte()
            elif kind == 4:
                classes.append((self._qualified(name), reader.variable()))
            elif kind in (1, 2, 3, 5):
                reader.variable()
            else:
                raise ValueError(STRUCTURE_ERROR)
            if attributes & 64:
                reader.variables(reader.variable())
        return classes

    def linkage_ancestry(self, name):
        """Read getlex/pushscope ancestry in a stock timeline class initializer."""
        method, class_id = self.initializers[name]
        code = Reader(self.scripts[method])
        if _initializer_opcode(code) != 0xd0 or _initializer_opcode(code) != 0x30:
            raise ValueError(STRUCTURE_ERROR)
        context = _initializer_opcode(code)
        if context == 0x65:  # getscopeobject global
            if code.byte() != 0:
                raise ValueError(STRUCTURE_ERROR)
        elif context == 0x5d:  # findpropstrict, class already declared as a script trait
            code.variable()
        else:
            raise ValueError(STRUCTURE_ERROR)
        parents = []
        while _initializer_opcode(code) == 0x60:  # getlex
            parent = self._qualified(code.variable())
            op = _initializer_opcode(code)
            if op == 0x58:  # newclass receives the already resolved final superclass.
                if code.variable() != class_id or not parents or parent != parents[-1]:
                    break
                return parents
            if op != 0x30:  # pushscope
                break
            parents.append(parent)
        raise ValueError(STRUCTURE_ERROR)


def _initializer_opcode(code):
    """Skip non-semantic compiler instrumentation in class initializers."""
    while True:
        op = code.byte()
        if op == 0xef:  # debug
            code.byte()
            code.variable()
            code.byte()
            code.variable()
        elif op in (0xf0, 0xf1):  # debugline, debugfile
            code.variable()
        elif op != 0x02:  # nop
            return op


def _movie_body(raw):
    if len(raw) < 8:
        raise ValueError(STRUCTURE_ERROR)
    length, = struct.unpack('<I', raw[4:8])
    if not 8 < length <= MAX_MOVIE:
        raise ValueError(STRUCTURE_ERROR)
    if raw[:3] == b'FWS':
        body = raw[8:]
    elif raw[:3] == b'CWS':
        decoder = zlib.decompressobj()
        body = decoder.decompress(raw[8:], length - 7)
        if decoder.unconsumed_tail or decoder.unused_data:
            raise ValueError(STRUCTURE_ERROR)
    else:
        raise ValueError(STRUCTURE_ERROR)
    if len(body) + 8 != length:
        raise ValueError(STRUCTURE_ERROR)
    return body


def _cstring(data, offset):
    stop = data.index(b'\0', offset)
    return data[offset:stop].decode('utf-8'), stop + 1


def _sprite_tags(data):
    reader = Reader(data)
    reader.take(4)  # Sprite id and frame count.
    while reader.pos < len(data):
        header, = struct.unpack('<H', reader.take(2))
        tag, size = header >> 6, header & 63
        if size == 63:
            size, = struct.unpack('<I', reader.take(4))
        yield tag, reader.take(size)


def _bits(data, offset, count):
    out = 0
    for bit in range(offset, offset + count):
        byte = struct.unpack_from('B', data, bit // 8)[0]
        out = out * 2 + ((byte >> (7 - bit % 8)) & 1)
    return out


def _matrix_end(data, offset):
    bit = offset * 8
    # Scale and rotation specify paired values using a bit width of their own.
    for unused in range(2):
        if _bits(data, bit, 1):
            bit += 6 + 2 * _bits(data, bit + 1, 5)
        else:
            bit += 1
    bit += 5 + 2 * _bits(data, bit, 5)  # X/Y translation.
    return (bit + 7) // 8


def _color_end(data, offset):
    bit = offset * 8
    has_add, has_multiply = _bits(data, bit, 1), _bits(data, bit + 1, 1)
    count = _bits(data, bit + 2, 4)
    return (bit + 6 + 4 * count * (has_add + has_multiply) + 7) // 8


def _placement(tag, data):
    flags = struct.unpack_from('B', data, 0)[0]
    wide = tag in (70, 94)
    flags2 = struct.unpack_from('B', data, 1)[0] if wide else 0
    depth, = struct.unpack_from('<H', data, 2 if wide else 1)
    offset = 4 if wide else 3
    if flags2 & 8 or (flags2 & 16 and flags & 2):  # Optional class name.
        unused_name, offset = _cstring(data, offset)
    character = None
    if flags & 2:
        character, = struct.unpack_from('<H', data, offset)
        offset += 2
    name = None
    if flags & 32:
        if flags & 4:
            offset = _matrix_end(data, offset)
        if flags & 8:
            offset = _color_end(data, offset)
        if flags & 16:
            offset += 2
        name, unused = _cstring(data, offset)
    return depth, character, name, bool(flags & 1)


class Timeline(object):
    def __init__(self, data):
        unused_id, self.frame_count = struct.unpack_from('<HH', data)
        self.labels, self.children = set(), {}
        self.last_frame_children = ()
        placements = {}
        frame = 0
        for tag, value in _sprite_tags(data):
            if tag == 1:  # ShowFrame
                frame += 1
                if frame == self.frame_count:
                    self.last_frame_children = tuple(placements[depth][0] for depth in sorted(placements))
            elif tag == 43:  # FrameLabel
                label, unused = _cstring(value, 0)
                self.labels.add(label)
            elif tag in (26, 70, 94):  # PlaceObject2, PlaceObject3, PlaceObject4
                depth, char, name, move = _placement(tag, value)
                previous_char, previous_name = placements.get(depth, (None, None)) if move else (None, None)
                char, name = char or previous_char, name or previous_name
                placements[depth] = (char, name)
                if char is not None and name is not None:
                    self.children.setdefault(name, set()).add(char)
            elif tag == 28:  # RemoveObject2
                placements.pop(struct.unpack_from('<H', value)[0], None)


class Movie(object):
    def __init__(self, raw):
        self.abcs, self.symbols, self.sprites, self.imports = [], {}, {}, set()
        for unused_start, unused_end, tag, value in _tags(_movie_body(raw)):
            if tag == 82:  # DoABC
                unused_name, offset = _cstring(value, 4)
                self.abcs.append(Abc(value[offset:]))
            elif tag == 76:  # SymbolClass
                count, = struct.unpack_from('<H', value)
                offset = 2
                for unused in range(count):
                    symbol, = struct.unpack_from('<H', value, offset)
                    name, offset = _cstring(value, offset + 2)
                    if name in self.symbols:
                        raise ValueError(STRUCTURE_ERROR)
                    self.symbols[name] = symbol
            elif tag == 39:  # DefineSprite
                symbol, = struct.unpack_from('<H', value)
                self.sprites[symbol] = value
            elif tag in (57, 71):  # ImportAssets, ImportAssets2
                name, unused = _cstring(value, 0)
                self.imports.add(name)
        self._timelines = {}

    def class_bases(self):
        bases = {}
        for abc in self.abcs:
            if set(bases).intersection(abc.bases):
                raise ValueError(STRUCTURE_ERROR)
            bases.update(abc.bases)
        return bases

    def ancestors(self, name):
        matches = [abc for abc in self.abcs if name in abc.initializers]
        if len(matches) != 1:
            raise ValueError(STRUCTURE_ERROR)
        return matches[0].linkage_ancestry(name)

    def timelines(self, symbols):
        for symbol in symbols:
            if symbol in self.sprites:
                if symbol not in self._timelines:
                    self._timelines[symbol] = Timeline(self.sprites[symbol])
                yield self._timelines[symbol]

    def resolve_path(self, root, path):
        symbols = {root}
        for component in path.split('/') if path else ():
            symbols = set(child for timeline in self.timelines(symbols)
                          for child in timeline.children.get(component, ()))
        return symbols


def _load_manifest():
    with open(MANIFEST, 'rb') as stream:
        manifest = json.load(stream)
    if manifest.get('schema') != 1:
        raise ValueError('Unexpected stock preview verification schema')
    return manifest


def _read_assets(game_root, asset_names):
    packages = os.path.join(game_root, 'res', 'packages')
    expected = dict(('gui/flash/' + name, name) for name in asset_names)
    result = {}
    for archive in sorted(os.listdir(packages)):
        if re.match(r'gui-part[1-9][0-9]?\.pkg\Z', archive) is None:
            continue
        filename = os.path.join(packages, archive)
        with zipfile.ZipFile(filename, 'r') as package:
            for info in package.infolist():
                name = expected.get(info.filename)
                if name is None:
                    continue
                if name in result or not 8 < info.file_size <= MAX_MOVIE:
                    raise ValueError('Stock preview asset is duplicated or oversized: ' + name)
                result[name] = package.read(info)
    if set(result) != set(asset_names):
        raise ValueError('Required stock preview assets are missing')
    return result


def _checked_movie(raw, version):
    try:
        movie = Movie(raw)
    except (ValueError, KeyError, IndexError, TypeError, struct.error, zlib.error):
        raise ValueError(STRUCTURE_ERROR)
    if not movie.abcs or any(list(abc.version) != version for abc in movie.abcs):
        raise ValueError('Stock preview SWF AVM2 version is incompatible')
    return movie


def _expected_ancestors(parent, bases):
    ancestors = []
    while parent not in (SPRITE, MOVIE_CLIP):
        if parent in ancestors or parent not in bases:
            raise ValueError('Invalid stock preview ancestry manifest')
        ancestors.append(parent)
        parent = bases[parent]
    runtime = DISPLAY_CHAIN + ((MOVIE_CLIP,) if parent == MOVIE_CLIP else ())
    return list(runtime) + list(reversed(ancestors))


def _matches_timeline(movie, timeline, rules):
    if (timeline.frame_count != rules.get('frames', timeline.frame_count) or
            timeline.frame_count < rules.get('min_frames', 1) or
            not set(rules.get('labels', ())).issubset(timeline.labels)):
        return False
    child = rules.get('last_frame_child')
    if child is None:
        return True
    index = child['index']
    if not 0 <= index < len(timeline.last_frame_children):
        return False
    identifier = timeline.last_frame_children[index]
    return identifier == movie.symbols.get(child['symbol']) and any(
        clip.frame_count == child['frames'] for clip in movie.timelines((identifier,)))


def _check_symbols(movie, requirements, bases):
    definitions = movie.class_bases()
    for name, spec in sorted(requirements.items()):
        parent = spec['base']
        if not movie.symbols.get(name) or definitions.get(name) != parent:
            raise ValueError('Stock preview symbol changed: ' + name)
        try:
            ancestry = movie.ancestors(name)
        except (ValueError, KeyError, IndexError, TypeError, struct.error):
            raise ValueError('Stock preview symbol ancestry is unreadable: ' + name)
        if ancestry != _expected_ancestors(parent, bases):
            raise ValueError('Stock preview symbol ancestry changed: ' + name)
        for path, rules in sorted(spec.get('timeline', {}).items()):
            try:
                symbols = movie.resolve_path(movie.symbols[name], path)
                if not symbols:
                    raise ValueError(STRUCTURE_ERROR)
                if rules and not any(_matches_timeline(movie, timeline, rules)
                                     for timeline in movie.timelines(symbols)):
                    raise ValueError(STRUCTURE_ERROR)
            except (ValueError, KeyError, IndexError, TypeError, struct.error):
                raise ValueError('Stock preview timeline changed: ' + name + ('/' + path if path else ''))


def verify_game(game_root, host=None):
    """Read and verify the local stock contract; optionally verify owned host bytes."""
    manifest = _load_manifest()
    try:
        version_data = ET.parse(os.path.join(game_root, 'version.xml')).getroot().findtext('version') or ''
        version = re.search(r'\b(\d+\.\d+\.\d+\.\d+)\b', version_data)
        build = re.search(r'#(\d+)\b', version_data)
    except (IOError, OSError, ET.ParseError):
        raise ValueError('Could not read the game version for stock preview validation')
    if version is None:
        raise ValueError('Could not recognize the game version for stock preview validation')
    try:
        raw_assets = _read_assets(game_root, manifest['assets'])
    except (IOError, OSError, zipfile.BadZipfile, RuntimeError, zlib.error):
        raise ValueError('Could not read required stock preview assets from the client packages')
    assets = {}
    for name, spec in sorted(manifest['assets'].items()):
        raw = raw_assets[name]
        movie = _checked_movie(raw, manifest['format']['abc'])
        if not set(spec.get('imports', ())).issubset(movie.imports):
            raise ValueError('Required stock preview library import changed: ' + name)
        symbols = spec.get('symbols', {})
        _check_symbols(movie, symbols, manifest['bases'])
        for root in spec.get('movie_roots', ()):
            namespace, separator, simple_name = root.rpartition('.')
            qualified = namespace + '::' + simple_name if separator else simple_name
            if movie.symbols.get(root) != 0 or qualified not in movie.class_bases():
                raise ValueError('Required stock preview movie root changed: ' + name)
        assets[name] = {'sha256': hashlib.sha256(raw).hexdigest(), 'symbols': len(symbols)}
    if host is not None:
        owned = _checked_movie(host, manifest['format']['abc'])
        actual_bases = owned.class_bases()
        if owned.symbols.get('GRZReticlePreview') != 0:
            raise ValueError('Owned preview host main class is missing')
        for name, base in sorted(manifest['bases'].items()):
            if actual_bases.get(name) != base:
                raise ValueError('Owned preview host class ancestry is incompatible: ' + name)
            try:
                ancestry = owned.ancestors(name)
            except (ValueError, KeyError, IndexError, TypeError, struct.error):
                raise ValueError('Owned preview host class ancestry is unreadable: ' + name)
            if ancestry != _expected_ancestors(base, manifest['bases']):
                raise ValueError('Owned preview host initializer has incompatible scopes: ' + name)
    return {'client': version.group(1), 'build': build.group(1) if build else None,
            'baseline': manifest['baseline'], 'assets': assets,
            'structural_stock_compatibility': True, 'host_verified': host is not None}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--game-root', required=True)
    parser.add_argument('--host', help='Optional path to built owned preview SWF')
    args = parser.parse_args()
    try:
        host = None
        if args.host:
            with open(args.host, 'rb') as stream:
                host = stream.read(MAX_MOVIE + 1)
            if len(host) > MAX_MOVIE:
                raise ValueError('Owned preview host is oversized')
        report = verify_game(args.game_root, host=host)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except (IOError, OSError):
        print('Could not read the preview verifier inputs', file=sys.stderr)
        return 1
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == '__main__':
    sys.exit(main())
