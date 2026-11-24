# -*- coding: ascii -*-
"""Compile the isolated battle widget preview from checked stock timelines.

The owned loader and its bridge stay the same. Its widget registry and
timeline actions are generated from the catalog, with game resources read
only for compatibility validation and public ActionScript class names.
"""
from __future__ import absolute_import

import hashlib
import json
import math
import os
import re
import struct
import zlib

from patch_decoration_ancestry import CLIP, OwnedAbc, _add_ancestor, _script_parts
from patch_decoration_host import Reader, _method_record, _tags, _u30, _uncompress
from verify_stock_flash import (
    Movie, _cstring, _expected_ancestors, _movie_body, _placement, _read_assets, _sprite_tags,
)


PROFILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'battle_panel_profiles.json')
HOST_NAME = 'grzBattleMechanicsPreview.swf'
REFERENCE = '353d25b9d980d578d3c5ae6311b7c3e056e935a6dff1a1c421dd630e5119ece7'
WIDGET_PREFIX = 'net.wg.gui.battle.views.widgetsPanel'
COMMON_FILES = ('gfxfontlib.swf', 'widgetsCommon.swf')
TEMPERATURE_RADIUS = 280.0
TEMPERATURE_SWEEP = math.radians(73.5)
PROPELLANT_RADIUS = 400.0
PROPELLANT_SWEEP = math.radians(32.0)
BITMAP_DATA = (b'flash.display', b'BitmapData')
DIAL_START = math.pi * .75
DIAL_SWEEP = math.pi * 1.5
DIAL_RADIUS = 70.0
DIAL_STEPS = 100
DIAL_MASKS = {'baseSpeed': 0xff0000, 'baseSpeedActive': 0xff0000, 'passiveActive': 0xff0000,
              'unavailableSpeed': 0x00ff00, 'unavailableTurboSpeed': 0x0000ff,
              'chargeZone': 0xff00ff, 'chargeZoneActive': 0x0000ff}
LABEL = re.compile(r'^[a-zA-Z_][a-zA-Z_0-9]*\Z')
STOCK_FILE = re.compile(r'^[a-zA-Z][a-zA-Z0-9]*\.swf\Z')
STOCK_PATH = 'gui/flash/'

# Operands from the SHA-256 pinned owned adapter. Stock class QNames are
# generated separately and never treated as adapter-private members.
GRAPHIC = 0x48
LINKAGE = 0x49
FILES = 0x38
LINKAGES = 0x39
LOADED = 0x3e
DOMAIN = 0x36
MODE = 0x52
LOAD_NEXT = 0x5a
ENQUEUE = 0x61
SCHEDULE = 0x62
REQUEST_GRAPHIC = 0x64
CLIP_AT_PATH = 0x70
AT_FRAME = 0x71
CHILD = 0x72
LENGTH = 0x92
VISIBLE = 0xc5

try:
    STRING = basestring
except NameError:
    STRING = str


def _load_profiles(profile_path):
    with open(profile_path, 'rb') as stream:
        panels = json.load(stream)['panels']
    if not isinstance(panels, dict) or not panels:
        raise ValueError('Battle widget catalog is empty')
    selected = tuple(panels[key] for key in sorted(panels)
                     if panels[key].get('snapshot_status') != 'pending')
    if not selected:
        raise ValueError('Battle widget catalog has no verified snapshots')
    return selected


def _qname(value):
    namespace, name = value.split('::', 1) if '::' in value else ('', value)
    return namespace.encode('ascii'), name.encode('ascii')


def _library_name(panel):
    path = panel['stock_library']
    name = path[len(STOCK_PATH):]
    if not path.startswith(STOCK_PATH) or not STOCK_FILE.match(name):
        raise ValueError('Invalid stock battle widget library path')
    return name


def _dependencies(library, movies):
    ordered = []

    def visit(name, parents):
        if name in ordered:
            return
        if name not in movies or name in parents:
            raise ValueError('Unexpected battle widget library dependency: ' + name)
        for imported in sorted(movies[name].imports):
            if imported not in COMMON_FILES:
                raise ValueError('Unrecognized battle widget import: ' + imported)
            visit(imported, parents + (name,))
        ordered.append(name)

    visit(library, ())
    return tuple(ordered)


def _direct_widget_bases(stock, movies, libraries):
    # Select the external classes required by these library initializers. The
    # original battle application is inspected as data and is never loaded.
    bindings = {}

    def visit(name):
        if name in bindings or not name.startswith('net.wg.'):
            return
        parent = stock.get(name)
        if parent is None:
            raise ValueError('Battle widget class has no inspectable stock parent: ' + name)
        visit(parent)
        bindings[name] = parent

    for library in sorted(libraries):
        definitions = movies[library].class_bases()
        for parent in sorted(set(definitions.values()) - set(definitions)):
            if parent is not None:
                visit(parent)
    return bindings


class StockDisplay(object):
    """Resolve original exported symbols, including imported library children."""

    def __init__(self, raw_assets, movies):
        self.movies = movies
        self.exports, self.imports, self.text_fields = {}, {}, set()
        self.bitmaps = set()
        self.timelines = {}
        for library, raw in sorted(raw_assets.items()):
            self.exports[library] = dict(movies[library].symbols)
            for _, _, tag, data in _tags(_movie_body(raw)):
                if tag == 37:  # DefineEditText
                    self.text_fields.add((library, struct.unpack_from('<H', data)[0]))
                elif tag == 36:  # DefineBitsLossless2
                    self.bitmaps.add((library, struct.unpack_from('<H', data)[0]))
                elif tag == 56:  # ExportAssets
                    self.exports[library].update(self._entries(data, 0))
                elif tag in (57, 71):  # ImportAssets, ImportAssets2
                    source, offset = _cstring(data, 0)
                    for name, character in self._entries(data, offset + (2 if tag == 71 else 0)):
                        self.imports[library, character] = (source, name)

    @staticmethod
    def _entries(data, offset):
        count, = struct.unpack_from('<H', data, offset)
        offset += 2
        entries = []
        for unused in range(count):
            character, = struct.unpack_from('<H', data, offset)
            name, offset = _cstring(data, offset + 2)
            entries.append((name, character))
        if offset != len(data):
            raise ValueError('Unrecognized battle widget export/import format')
        return entries

    def _local(self, asset):
        visited = set()
        while asset in self.imports:
            if asset in visited:
                raise ValueError('Circular stock battle widget symbol reference')
            visited.add(asset)
            source, name = self.imports[asset]
            if source not in self.exports or name not in self.exports[source]:
                raise ValueError('Stock battle widget import is unavailable: ' + name)
            asset = (source, self.exports[source][name])
        return asset

    def _class_ref(self, library, tag, data):
        if tag not in (70, 94) or not struct.unpack_from('B', data, 1)[0] & 8:
            return None
        name, _ = _cstring(data, 4)
        if name in self.exports[library]:
            return library, self.exports[library][name]
        matches = [(source, self.exports[source][name]) for source in _dependencies(library, self.movies)[:-1]
                   if name in self.exports[source]]
        return matches[0] if len(matches) == 1 else None

    def frames(self, asset):
        asset = self._local(asset)
        if asset in self.timelines:
            return self.timelines[asset]
        library, character = asset
        labels, current, timeline = {}, {}, []
        sprite = self.movies[library].sprites.get(character)
        if sprite:
            for tag, data in _sprite_tags(sprite):
                if tag == 43:  # FrameLabel
                    labels[_cstring(data, 0)[0]] = len(timeline) + 1
                elif tag in (26, 70, 94):
                    depth, character, name, move = _placement(tag, data)
                    placed = (library, character) if character else self._class_ref(library, tag, data)
                    old_placed, old_name = current.get(depth, (None, None)) if move else (None, None)
                    current[depth] = (placed or old_placed, name or old_name)
                elif tag == 28:
                    current.pop(struct.unpack_from('<H', data)[0], None)
                elif tag == 1:  # ShowFrame
                    timeline.append(dict((name, placed) for placed, name in current.values() if name and placed))
        self.timelines[asset] = labels, timeline
        return labels, timeline

    def path(self, root, path, selected=None, mounted=None):
        refs, components = [root], []
        for part in path.split('/') if path else ():
            candidates = []
            for item in refs:
                _, frames = self.frames(item)
                if selected is not None:
                    frame = selected.get('/'.join(components), 1)
                    frames = frames[frame - 1:frame]
                candidates.extend(frame[part] for frame in frames if part in frame)
            refs = sorted(set(candidates))
            components.append(part)
            if mounted is not None and '/'.join(components) in mounted:
                refs.append(mounted['/'.join(components)])
        return [self._local(ref) for ref in refs]


def _number(value):
    return (isinstance(value, (float, int)) and not isinstance(value, bool) and
            -2048 <= value <= 2048)


def _snapshot(panel, library, display):
    actions = panel.get('snapshot', ())
    if not actions:
        raise ValueError('Battle widget has no verified preview snapshot: ' + panel['linkage'])
    root = library, display.movies[library].symbols[panel['linkage']]
    for requirement in panel.get('timeline', ()):
        refs = display.path(root, requirement['path'])
        labels = set(requirement.get('labels', ()))
        minimum = requirement.get('min_frames', 0)
        if not refs or ((labels or minimum) and not any(
                len(frames) >= minimum and labels.issubset(numbered)
                for numbered, frames in (display.frames(ref) for ref in refs))):
            raise ValueError('Stock battle widget timeline changed: ' + panel['linkage'] + '/' + requirement['path'])
    phases = ([], [], [])
    selected, mounted = {}, {}
    for action in sorted(actions, key=lambda action: action['phase']):
        path, phase = action['path'], action['phase']
        if (not isinstance(path, STRING) or not isinstance(phase, int) or phase not in (0, 1, 2)
                or not all(LABEL.match(part) for part in path.split('/') if path)):
            raise ValueError('Invalid battle widget display path or phase')
        refs = display.path(root, path, selected, mounted)
        if len(refs) != 1:
            raise ValueError('Battle widget snapshot child changed: ' + panel['linkage'] + '/' + path)
        setters = set(action) - {'path', 'phase'}
        if len(setters) != 1:
            raise ValueError('A battle widget action needs exactly one display operation')
        setter = setters.pop()
        value = action[setter]
        if setter == 'frame':
            labels, frames = display.frames(refs[0])
            frame = labels.get(value, 0) if isinstance(value, STRING) else value
            allowed = isinstance(frame, int) and not isinstance(frame, bool) and 1 <= frame <= len(frames)
            if allowed:
                selected[path] = frame
        elif setter == 'visible':
            allowed = isinstance(value, bool)
        elif setter == 'text':
            allowed = (path and refs[0] in display.text_fields and
                       isinstance(value, STRING) and 0 < len(value) <= 24)
        elif setter == 'textColor':
            allowed = (path and refs[0] in display.text_fields and isinstance(value, int) and
                       not isinstance(value, bool) and 0 <= value <= 0xffffff)
        elif setter in ('x', 'y', 'rotation', 'alpha'):
            allowed = _number(value) and (setter != 'alpha' or 0 <= value <= 1)
        elif setter == 'blend':
            allowed = value in ('normal', 'screen', 'add', 'multiply')
        elif setter == 'stock_bitmap_arc':
            symbol_name, start, end = value['symbol'], value['start'], value['end']
            symbol = display.movies[library].symbols.get(symbol_name)
            target_library, target_symbol = refs[0]
            allowed_geometry = (
                (library == 'temperatureGun.swf' and set(value) == {'symbol', 'start', 'end'} and end <= 1) or
                (library == 'propellantGun.swf' and set(value) == {'symbol', 'start', 'end', 'geometry', 'align'}
                 and value['geometry'] == 'propellant' and value['align'] in ('none', 'toMin', 'toMax') and end <= 1.1)
            ) if _number(start) and _number(end) else False
            allowed = (allowed_geometry and
                       display.movies[library].class_bases().get(symbol_name) == 'flash.display::BitmapData' and
                       (library, symbol) in display.bitmaps and
                       display.exports[target_library].get('ContentSpriteUI') == target_symbol and
                       0 <= start <= end)
        elif setter == 'stock_dial_mask':
            start, end = value['start'], value['end']
            parent_path, _, target_layer = path.rpartition('/')
            parents = display.path(root, parent_path, selected, mounted)
            speedometer = display.exports[library].get('SpeedWidgetUI')
            allowed = (library == 'stanceDance.swf' and set(value) == {'start', 'end'} and
                       speedometer and parents == [(library, speedometer)] and target_layer in DIAL_MASKS and
                       _number(start) and _number(end) and 0 <= start <= end <= 1)
        elif setter == 'mount':
            symbol_name, name = value['symbol'], value['name']
            symbol = display.movies[library].symbols.get(symbol_name)
            key = path + '/' + name if path else name
            allowed = (set(value).issubset({'symbol', 'name', 'x', 'y', 'rotation'}) and
                       LABEL.match(symbol_name) and LABEL.match(name) and name.startswith('grz') and
                       symbol and symbol in display.movies[library].sprites and
                       not display.path(root, key, selected, mounted) and
                       all(_number(value[component]) for component in value
                           if component in ('x', 'y', 'rotation')))
            if allowed:
                mounted[key] = (library, symbol)
        else:
            allowed = False
        if not allowed:
            raise ValueError('Invalid original battle widget display state: ' + panel['linkage'] + '/' + path)
        phases[phase].append((path, setter, value))
    return phases


def _stock_contract(game_root, panels):
    filenames = set(_library_name(panel) for panel in panels)
    if set(COMMON_FILES).intersection(filenames) or 'battle.swf' in filenames:
        raise ValueError('Invalid stock battle widget library name')
    raw_assets = _read_assets(game_root, filenames.union(COMMON_FILES, ('battle.swf',)))
    stock = Movie(raw_assets.pop('battle.swf')).class_bases()
    movies = dict((name, Movie(raw)) for name, raw in raw_assets.items())
    display = StockDisplay(raw_assets, movies)
    if any(0 in movie.symbols.values() for movie in movies.values()):
        raise ValueError('Battle widget dependencies must be standalone libraries')
    fixtures, libraries = {}, set()
    for panel in panels:
        linkage, filename = panel['linkage'], _library_name(panel)
        movie = movies[filename]
        parent = movie.class_bases().get(linkage, '')
        if (linkage in fixtures or not LABEL.match(linkage) or not movie.symbols.get(linkage)
                or not parent.startswith(WIDGET_PREFIX + '::')):
            raise ValueError('Invalid or unavailable stock battle widget linkage: ' + linkage)
        if movie.imports != set(panel['imports']):
            raise ValueError('Stock battle widget imports changed: ' + linkage)
        actual_chain = movie.ancestors(linkage)
        if not actual_chain or actual_chain[-1] != parent:
            raise ValueError('Stock battle widget linking scope changed: ' + linkage)
        for child, direct_parent in zip(actual_chain[1:], actual_chain):
            if child.startswith('net.wg.') and stock.get(child) != direct_parent:
                raise ValueError('Stock battle widget linking scope changed: ' + child)
        files = _dependencies(filename, movies)
        fixtures[linkage] = (files, _snapshot(panel, filename, display))
        libraries.update(files)
    return fixtures, _direct_widget_bases(stock, movies, libraries)


def _extend_ancestry(abc, bindings):
    first = abc.scripts[0]
    _, runtime = _script_parts(abc.by_method[first.initializer].code, first.class_id, first.name)
    scopes = dict((abc.qname(name), runtime[:index + 1]) for index, name in enumerate(runtime))
    for script in abc.scripts:
        parent = abc.qname(abc.instances[script.class_id].parent)
        name = abc.qname(script.name)
        if name in scopes or parent not in scopes:
            raise ValueError('Unexpected registered class in owned widget host')
        scopes[name] = scopes[parent] + (script.name,)
    if CLIP not in scopes:
        raise ValueError('Original host Flash runtime scope is unavailable')
    pending = dict((_qname(name), _qname(parent)) for name, parent in bindings.items())
    added = []
    for name, parent in sorted(pending.items()):
        if name in scopes and scopes[name][:-1] != scopes.get(parent):
            raise ValueError('Original widget superclass conflicts with owned stubs')
    while pending:
        available = sorted(name for name, parent in pending.items() if parent in scopes)
        if not available:
            raise ValueError('Unresolvable stock battle widget class hierarchy')
        for name in available:
            parent = pending.pop(name)
            if name not in scopes:
                added.append(_add_ancestor(abc, name, scopes[parent]))
                scopes[name] = scopes[parent] + (abc.qname_index(name),)
    # Added classes subclass existing stubs and must be registered after them.
    abc.scripts[-1:-1] = added


def _op(opcode, *operands):
    return struct.pack('B', opcode) + b''.join(_u30(value) for value in operands)


def _skip_if(opcode, code):
    return _jump(opcode, len(code)) + code


def _jump(opcode, displacement):
    return struct.pack('B', opcode) + struct.pack('<i', displacement)[:3]


class DisplayCode(object):
    """Emit the small AVM2 subset needed to select existing display states."""

    def __init__(self, abc):
        self.abc = abc

    def string(self, value):
        value = value.encode('utf-8')
        if value not in self.abc.strings:
            self.abc.strings.append(value)
        return _op(0x2c, self.abc.strings.index(value))

    def array(self, strings):
        return b''.join(self.string(value) for value in strings) + _op(0x56, len(strings))

    def number(self, value):
        if isinstance(value, int) and -128 <= value <= 127:
            return b'\x24' + struct.pack('b', value)
        reader = Reader(self.abc.numeric_prefix)
        reader.take(4)
        for unused in range(2):
            reader.variables(max(0, reader.variable() - 1))
        doubles_start = reader.pos
        count = reader.variable()
        doubles = reader.take(max(0, count - 1) * 8)
        packed = struct.pack('<d', value)
        for index in range(0, len(doubles), 8):
            if doubles[index:index + 8] == packed:
                return _op(0x2f, index // 8 + 1)
        index = max(1, count)
        self.abc.numeric_prefix = self.abc.numeric_prefix[:doubles_start] + _u30(index + 1) + doubles + packed
        return _op(0x2f, index)

    def public(self, name):
        return self.abc.qname_index((b'', name))

    def command(self, name, argc):
        return _op(0x4f, self.public(name), argc)

    def new_stock(self, symbol, class_name):
        return (_op(0x60, DOMAIN) + self.string(symbol) + _op(0x46, self.public(b'getDefinition'), 1) +
                b'\x42\x00' + _op(0x80, self.abc.qname_index(class_name)))

    def select(self, choices):
        # Each true branch returns. The false branch falls through its own
        # body, so no instruction outside the generated case is targeted.
        blocks = []
        for linkage, commands in choices:
            blocks.append(_op(0x60, LINKAGE) + self.string(linkage) + _skip_if(0x14, commands + b'\x47'))
        return b''.join(blocks) + b'\x47'

    def child(self, path, clip=False):
        if not path:
            return _op(0x60, GRAPHIC)
        parent, _, name = path.rpartition('/')
        method = CLIP_AT_PATH if clip else CHILD
        return _op(0x5d, method) + self.child(parent) + self.string(name) + _op(0x46, method, 2)

    def bitmap_arc(self, path, spec):
        # Build the clipping path only. Fill samples the original game bitmap
        # directly in its stock matrix orientation, without generating artwork.
        if spec['start'] == spec['end']:
            return b''
        matrix = self.abc.qname_index((b'flash.geom', b'Matrix'))
        graphics = self.abc.qname_index((b'flash.display', b'Graphics'))
        width = _op(0x66, self.public(b'width'))
        height = _op(0x66, self.public(b'height'))
        propellant = spec.get('geometry') == 'propellant'
        translation = (self.number(360) + b'\xd2' + width + b'\xa1\xd2' + height + b'\x90\x24\x01\xa6'
                       if propellant else b'\xd2' + width + b'\x90\x24\x00')
        code = [self.child(path), _op(0x66, self.public(b'graphics')), _op(0x80, graphics), b'\xd5',
                self.new_stock(spec['symbol'], BITMAP_DATA), b'\xd6',
                _op(0x5d, matrix), _op(0x4a, matrix, 0), b'\xd7',
                b'\xd3', translation, self.command(b'translate', 2)]
        if propellant and spec['align'] != 'none':
            angle = -spec['start'] if spec['align'] == 'toMin' else 1 - spec['end']
            code.extend((b'\xd3', self.number(angle * PROPELLANT_SWEEP), self.command(b'rotate', 1)))
        code.extend((b'\xd1', self.command(b'clear', 0), b'\xd1', self.command(b'lineStyle', 0),
                     b'\xd1\xd2\xd3\x27\x26', self.command(b'beginBitmapFill', 4)))
        initial, curves = _stock_wedge(spec['start'], spec['end'], propellant)
        code.extend((b'\xd1', self.number(initial[0]), self.number(initial[1]), self.command(b'lineTo', 2)))
        for curve in curves:
            code.extend((b'\xd1', b''.join(self.number(value) for value in curve), self.command(b'curveTo', 4)))
        code.extend((b'\xd1\x24\x00\x24\x00', self.command(b'lineTo', 2),
                     b'\xd1', self.command(b'endFill', 0)))
        return b''.join(code)

    def dial_mask(self, path, spec):
        # The original speed dial clips each authored layer through a sibling
        # Sprite mask, centered in the layer's own display bounds.
        sprite = self.abc.qname_index((b'flash.display', b'Sprite'))
        graphics = self.abc.qname_index((b'flash.display', b'Graphics'))
        code = [self.child(path), b'\xd5', _op(0x5d, sprite), _op(0x4a, sprite, 0), b'\xd6',
                b'\xd1', _op(0x66, self.public(b'parent')), b'\xd2', self.command(b'addChild', 1),
                b'\xd1\xd2', _op(0x61, self.public(b'mask')),
                b'\xd2', _op(0x66, self.public(b'graphics')), _op(0x80, graphics), b'\xd7']
        for coordinate, size, register in ((b'x', b'width', 4), (b'y', b'height', 5)):
            code.extend((b'\xd1', _op(0x66, self.public(size)), b'\x24\x02\xa3', _op(0x63, register),
                         b'\xd2\xd1', _op(0x66, self.public(coordinate)), _op(0x61, self.public(coordinate))))
        color = DIAL_MASKS[path.rsplit('/', 1)[1]]
        center = b'\xd3\x62\x04\x62\x05'
        code.extend((b'\xd3', self.number(color), self.command(b'beginFill', 1), center, self.command(b'moveTo', 2)))
        start = DIAL_START + spec['start'] * DIAL_SWEEP
        sweep = (spec['end'] - spec['start']) * DIAL_SWEEP
        math_class = self.abc.qname_index((b'', b'Math'))
        angle = (self.number(start) + self.number(sweep) + b'\x62\x06' + self.number(DIAL_STEPS) +
                 b'\xa3\xa2\xa0\x63\x07')
        vector = []
        for coordinate, trig in ((4, b'cos'), (5, b'sin')):
            vector.extend((_op(0x62, coordinate), _op(0x60, math_class), b'\x62\x07',
                           _op(0x46, self.public(trig), 1), self.number(DIAL_RADIUS), b'\xa2\xa0'))
        # Loop locals 6 and 7 hold the segment index and its angle. The
        # explicit back edge returns to that mask's own bounds test.
        condition = b'\x62\x06' + self.number(DIAL_STEPS)
        line = angle + b'\xd3' + b''.join(vector) + self.command(b'lineTo', 2) + b'\xc2\x06'
        back_edge = _jump(0x10, -(len(condition) + len(line) + 8))
        code.extend((b'\x24\x00\x73\x63\x06', condition, _skip_if(0x17, line + back_edge)))
        code.extend((center, self.command(b'lineTo', 2), b'\xd3', self.command(b'endFill', 0)))
        return b''.join(code)

    def action(self, path, setter, value):
        if setter == 'frame':
            frame = self.string(value) if isinstance(value, STRING) else _op(0x25, value)
            return _op(0x5d, AT_FRAME) + self.child(path, True) + frame + _op(0x4f, AT_FRAME, 2)
        if setter == 'visible':
            return self.child(path) + (b'\x26' if value else b'\x27') + _op(0x61, VISIBLE)
        if setter in ('x', 'y', 'rotation', 'alpha'):
            return self.child(path) + self.number(value) + _op(0x61, self.public(setter.encode('ascii')))
        if setter == 'blend':
            return self.child(path) + self.string(value) + _op(0x61, self.public(b'blendMode'))
        if setter == 'stock_bitmap_arc':
            return self.bitmap_arc(path, value)
        if setter == 'stock_dial_mask':
            return self.dial_mask(path, value)
        if setter == 'mount':
            # This is the same child-domain definition lookup as the main
            # linkage. The original asset constructor creates its timeline.
            code = (self.child(path, True) + self.new_stock(value['symbol'], CLIP) +
                    b'\x2a' + self.string(value['name']) + _op(0x61, self.public(b'name')))
            for component in ('x', 'y', 'rotation'):
                if component in value:
                    code += b'\x2a' + self.number(value[component]) + _op(0x61, self.public(component.encode('ascii')))
            return code + _op(0x4f, self.public(b'addChild'), 1)
        # The stock timeline already contains its own authored TextField.
        field = self.abc.qname_index((b'flash.text', b'TextField'))
        content = self.string(value) if setter == 'text' else self.number(value)
        return self.child(path) + _op(0x80, field) + content + _op(0x61, self.public(setter.encode('ascii')))


def _stock_wedge(start, end, propellant=False):
    # Screen coordinates use the negated stock geometric angle. Both widgets
    # call the same native subdivision into quadratics no wider than pi/6.
    span = -PROPELLANT_SWEEP if propellant else TEMPERATURE_SWEEP
    angle = (PROPELLANT_SWEEP / 2 if propellant else math.pi / 2) + start * span
    sweep = (end - start) * span
    segment_count = int(math.ceil(abs(sweep) / (math.pi / 6)))
    step = sweep / segment_count
    radius = PROPELLANT_RADIUS if propellant else TEMPERATURE_RADIUS
    initial = radius * math.cos(angle), radius * math.sin(angle)
    control_radius = radius / math.cos(step / 2)
    curves = []
    for unused in range(segment_count):
        midpoint = angle + step / 2
        angle += step
        curves.append((control_radius * math.cos(midpoint), control_radius * math.sin(midpoint),
                       radius * math.cos(angle), radius * math.sin(angle)))
    return initial, curves


def _body(abc, original, name):
    record = _method_record(original, name)
    matches = [body for body in abc.bodies if record and body.code == record[1]]
    if len(matches) != 1:
        raise ValueError('Owned battle widget host method is ambiguous')
    return matches[0]


def _replace(body, code, stack=None):
    if body.tail != b'\x00\x00':
        raise ValueError('Owned method with a catch or local traits cannot be resized')
    body.code = code
    if stack is not None:
        body.limits = (max(body.limits[0], stack),) + body.limits[1:]


def _compile_loader(abc, original, fixtures):
    code = DisplayCode(abc)
    registry = sorted(fixtures)
    root = next(instance for instance in abc.instances
                if abc.qname(instance.name) == (b'', b'GRZReticlePreview'))
    init = abc.by_method[root.initializer]
    empty_files = b'\xd0' + code.array(()) + _op(0x61, FILES)
    allowed_linkages = b'\xd0' + code.array(registry) + _op(0x61, LINKAGES)
    _replace(init, init.code[:7] + empty_files + allowed_linkages + init.code[47:131] + b'\x47',
             len(registry) + 1)
    # The first valid request selects only the resource graph for that widget.
    request = _body(abc, original, b'as_setPreview')
    begin_load = _op(0x5d, LOAD_NEXT) + _op(0x4f, LOAD_NEXT, 0)
    load_choices = [(key, _op(0x5e, FILES) + code.array(fixtures[key][0]) +
                     _op(0x61, FILES) + begin_load) for key in registry]
    refresh = _op(0x5d, REQUEST_GRAPHIC) + _op(0x4f, REQUEST_GRAPHIC, 0) + b'\x47'
    loading = _op(0x60, FILES) + _op(0x66, LENGTH) + b'\x24\x00' + _skip_if(0x13, b'\x47')
    _replace(request, request.code[:242] + _op(0x60, LOADED) + _skip_if(0x12, refresh) +
             loading + code.select(load_choices),
             max(len(files) for files, _ in fixtures.values()) + 1)
    # Keep the legacy loader/error handling. Queue just the selected linkage
    # after its libraries are ready instead of preflighting the entire list.
    load = _body(abc, original, b'loadNext')
    replacement = (_op(0x5e, LOADED) + b'\x26' + _op(0x61, LOADED) +
                   _op(0x5d, ENQUEUE) + _op(0x60, LINKAGE) + _op(0x60, MODE) + _op(0x4f, ENQUEUE, 2) +
                   _op(0x5d, SCHEDULE) + _op(0x4f, SCHEDULE, 0) + b'\x47')
    load.code = load.code[:41] + replacement.ljust(78, b'\x02') + load.code[119:]


def _compile_snapshots(abc, original, fixtures):
    code = DisplayCode(abc)
    methods = (b'prepareRoot', b'prepareChildren', b'prepareGrandchildren')
    for phase, method in enumerate(methods):
        choices = []
        stack = 1
        locals_count = 1
        for linkage, (_, actions) in sorted(fixtures.items()):
            commands = b''.join(code.action(*action) for action in actions[phase])
            if commands:
                choices.append((linkage, commands))
                stack = max(stack, max(path.count('/') + 5 for path, _, _ in actions[phase]))
                for _, setter, _ in actions[phase]:
                    locals_count = max(locals_count, {'stock_bitmap_arc': 4, 'stock_dial_mask': 8}.get(setter, 1))
        body = _body(abc, original, method)
        _replace(body, b'\xd0\x30' + code.select(choices), stack)
        if body.limits[1] < locals_count:
            body.limits = (body.limits[0], locals_count) + body.limits[2:]
    geometry = _body(abc, original, b'configureGeometry')
    _replace(geometry, geometry.code[:55] + b'\x47')
    validate = _body(abc, original, b'validateGraphic')
    _replace(validate, validate.code[:30] + b'\x47')


def _verify_host(raw, fixtures, bindings):
    host = Movie(raw)
    native_classes = host.class_bases()
    if host.symbols != {'GRZReticlePreview': 0} or any(
            bindings[name] != native_classes.get(name) for name in bindings):
        raise ValueError('Generated battle widget host lifecycle or ancestry does not match the stock contract')
    for name in bindings:
        if host.ancestors(name) != _expected_ancestors(bindings[name], bindings):
            raise ValueError('Generated battle widget host initializer does not match its stock parent')
    return {'widgets': len(fixtures), 'native_classes': len(bindings)}


def verify_widget_host(game_root, raw, profile_path=PROFILE_PATH):
    """Check the generated host with the current game's original asset contract."""
    fixtures, bindings = _stock_contract(game_root, _load_profiles(profile_path))
    return _verify_host(raw, fixtures, bindings)


def build_widget_host(raw, game_root, profile_path=PROFILE_PATH):
    """Build the owned host after verifying the local original stock assets."""
    if hashlib.sha256(raw).hexdigest() != REFERENCE:
        raise ValueError('Unrecognized owned adapter input for battle widgets')
    fixtures, bindings = _stock_contract(game_root, _load_profiles(profile_path))
    body = _uncompress(raw)
    start, end, tag, contents = next(entry for entry in _tags(body) if entry[2] == 82)
    offset = contents.index(b'\0', 4) + 1
    header, original = contents[:offset], contents[offset:]
    abc = OwnedAbc(original)
    if abc.encode() != original:
        raise ValueError('Original widget host class table did not round trip')
    _compile_loader(abc, original, fixtures)
    _compile_snapshots(abc, original, fixtures)
    _extend_ancestry(abc, bindings)
    updated = abc.encode()
    if OwnedAbc(updated).encode() != updated:
        raise ValueError('Generated widget host class table did not round trip')
    movie_tag = header + updated
    body = body[:start] + struct.pack('<HI', (tag << 6) | 63, len(movie_tag)) + movie_tag + body[end:]
    payload = zlib.compress(body, 9) if raw[:3] == b'CWS' else body
    result = raw[:4] + struct.pack('<I', len(body) + 8) + payload
    if ([(tag, data) for _, _, tag, data in _tags(_movie_body(result)) if tag != 82] !=
            [(tag, data) for _, _, tag, data in _tags(_movie_body(raw)) if tag != 82]):
        raise ValueError('Battle widget host changed owned non-code resources')
    _verify_host(result, fixtures, bindings)
    return result
