# -*- coding: ascii -*-
"""Add the verified inert class hierarchy to our owned decoration host.

The legacy adapter's top-level stubs extended MovieClip directly. A stock
linked symbol captures its complete ancestry when its script initializes,
before the selected timeline can display. Supply that hierarchy in our own
movie domain, keeping the stock SWFs and the host renderer code unchanged.
"""
from __future__ import absolute_import, print_function

import hashlib
import struct
import zlib

from patch_decoration_host import Reader, _tags, _traits, _u30, _uncompress


REFERENCE = '7e61e2f9a5dfab97e4ca7560a9e5cf9aeb042bd86ae009e02002d4ad4cd2e857'
PACKAGE_NS = 0x16
QNAME = 0x07
CLIP = (b'flash.display', b'MovieClip')
SPRITE = (b'flash.display', b'Sprite')
COMPONENTS = b'net.wg.gui.battle.components'
BASE = b'net.wg.infrastructure.base'
META = b'net.wg.infrastructure.base.meta.impl'
DECOR = b'net.wg.gui.battle.views.decorativeCrosshair'
WIDGET = b'net.wg.gui.battle.views.widgetsPanel'

UI = (COMPONENTS, b'BattleUIComponent')
BASE_META = (META, b'BaseBattleDAAPIComponentMeta')
BASE_COMPONENT = (BASE, b'BaseBattleDAAPIComponent')
DISPLAYABLE = (COMPONENTS, b'BattleDisplayable')
DECOR_META = (META, b'BaseDecorativeCrosshairMeta')
DECOR_BASE = (DECOR, b'BaseDecorativeCrosshair')
PANEL_META = (META, b'DecorativeCrosshairPanelMeta')
WIDGET_META = (META, b'BaseVehicleMechanicsWidgetMeta')
WIDGET_BASE = (WIDGET, b'BaseVehicleMechanicsWidget')
SURGE_META = (META, b'AutoreloaderSurgeWidgetMeta')
DECOR_ADAPTERS = (
    b'AccuracyStackDecorativeCrosshair', b'ConcentrationDecorativeCrosshair',
    b'FuryDecorativeCrosshair', b'OverheatDecorativeCrosshair',
    b'PillboxSiegeDecorativeCrosshair', b'TemperatureGunOverheatDecorativeCrosshair',
)
ANCESTORS = (
    (UI, CLIP), (BASE_META, UI), (BASE_COMPONENT, BASE_META), (DISPLAYABLE, BASE_COMPONENT),
    (DECOR_META, DISPLAYABLE), (DECOR_BASE, DECOR_META), (PANEL_META, DISPLAYABLE),
    (WIDGET_META, DISPLAYABLE), (WIDGET_BASE, WIDGET_META), (SURGE_META, WIDGET_BASE),
) + tuple(((META, name + b'Meta'), DECOR_BASE) for name in DECOR_ADAPTERS)
RETARGETS = tuple(((DECOR, name), (META, name + b'Meta')) for name in DECOR_ADAPTERS) + (
    ((DECOR, b'DecorativeCrosshairPanel'), PANEL_META),
    ((WIDGET, b'AutoreloaderSurgeWidget'), SURGE_META),
    ((DECOR + b'.shared', b'TextWrapper'), SPRITE),
)

_CLIP_INIT = b'\xd0\x30\xd0\x49\x00\x5d\x0a\x4f\x0a\x00\x5e\x0b\x27\x61\x0b\x5e\x0c\x27\x61\x0c\x47'
_CLASS_INIT = b'\xd0\x30\x47'
_ANCESTOR_INIT = b'\xd0\x30\xd0\x49\x00\x47'
_PRIMITIVE_BASES = (
    b'Object', b'EventDispatcher', b'DisplayObject', b'InteractiveObject',
    b'DisplayObjectContainer', b'Sprite', b'MovieClip',
)


def ancestry_bindings():
    """The fixed public-package class graph used by this transform."""
    return ANCESTORS + RETARGETS


def _join(values):
    return b''.join(values)


def _list(values):
    return _u30(len(values)) + _join(values)


def _copy_record(reader, consume):
    start = reader.pos
    consume(reader)
    return reader.data[start:reader.pos]


def _skip_options(reader):
    parameters = reader.variable()
    reader.variables(parameters + 2)
    flags = reader.byte()
    if flags & 8:
        for unused in range(reader.variable()):
            reader.variable()
            reader.byte()
    if flags & 128:
        reader.variables(parameters)


def _skip_name(reader, kind):
    if kind in (7, 13, 9, 14):
        reader.variables(2)
    elif kind in (15, 16, 27, 28):
        reader.variable()
    elif kind not in (17, 18):
        if kind != 29:
            raise ValueError('Unexpected name kind in owned ABC')
        reader.variable()
        reader.variables(reader.variable())


class Instance(object):
    def __init__(self, reader):
        self.name, self.parent = reader.variable(), reader.variable()
        start = reader.pos
        if reader.byte() & 8:
            reader.variable()
        reader.variables(reader.variable())
        self.initializer = reader.variable()
        list(_traits(reader))
        self.tail = reader.data[start:reader.pos]

    def encode(self):
        return _u30(self.name) + _u30(self.parent) + self.tail


class Script(object):
    def __init__(self, reader):
        start = reader.pos
        self.initializer = reader.variable()
        if reader.variable() != 1:
            raise ValueError('Expected a single class export in owned script')
        self.name = reader.variable()
        attrs = reader.byte()
        if attrs & 15 != 4:
            raise ValueError('Expected owned script class trait')
        reader.variable()  # slot ID
        self.class_id = reader.variable()
        if attrs & 64:
            reader.variables(reader.variable())
        self.raw = reader.data[start:reader.pos]


class MethodBody(object):
    def __init__(self, reader):
        self.method = reader.variable()
        self.limits = tuple(reader.variable() for unused in range(4))
        self.code = reader.take(reader.variable())
        start = reader.pos
        reader.variables(reader.variable() * 5)
        list(_traits(reader))
        self.tail = reader.data[start:reader.pos]

    def encode(self):
        return (_u30(self.method) + _join(_u30(value) for value in self.limits) +
                _u30(len(self.code)) + self.code + self.tail)


class OwnedAbc(object):
    def __init__(self, data):
        reader = Reader(data)
        reader.take(4)
        for unused in range(2):
            reader.variables(reader.variable() - 1)
        reader.take(max(0, reader.variable() - 1) * 8)
        self.numeric_prefix = data[:reader.pos]
        self.strings = [b''] + [reader.take(reader.variable())
                                for unused in range(reader.variable() - 1)]
        self.namespaces = [None] + [(reader.byte(), reader.variable())
                                    for unused in range(reader.variable() - 1)]
        start = reader.pos
        for unused in range(reader.variable() - 1):
            reader.variables(reader.variable())
        self.namespace_sets = data[start:reader.pos]
        self.names = [None]
        for unused in range(reader.variable() - 1):
            start = reader.pos
            _skip_name(reader, reader.byte())
            self.names.append(data[start:reader.pos])
        self.methods = [_copy_record(reader, _skip_options) for unused in range(reader.variable())]
        start = reader.pos
        for unused in range(reader.variable()):
            reader.variable()
            reader.variables(reader.variable() * 2)
        self.metadata = data[start:reader.pos]

        count = reader.variable()
        self.instances = [Instance(reader) for unused in range(count)]
        self.class_traits = []
        self.cinits = []
        for unused in range(count):
            start = reader.pos
            self.cinits.append(reader.variable())
            list(_traits(reader))
            self.class_traits.append(data[start:reader.pos])
        self.scripts = [Script(reader) for unused in range(reader.variable())]
        self.bodies = [MethodBody(reader) for unused in range(reader.variable())]
        self.by_method = dict((body.method, body) for body in self.bodies)
        if reader.pos != len(data) or len(self.by_method) != len(self.bodies):
            raise ValueError('Unexpected owned ABC method table')

    def encode(self):
        return (self.numeric_prefix + _u30(len(self.strings)) +
                _join(_u30(len(value)) + value for value in self.strings[1:]) +
                _u30(len(self.namespaces)) +
                _join(struct.pack('B', kind) + _u30(index) for kind, index in self.namespaces[1:]) +
                self.namespace_sets + _u30(len(self.names)) + _join(self.names[1:]) +
                _list(self.methods) + self.metadata + _u30(len(self.instances)) +
                _join(instance.encode() for instance in self.instances) + _join(self.class_traits) +
                _list([script.raw for script in self.scripts]) +
                _list([body.encode() for body in self.bodies]))

    def qname(self, index):
        reader = Reader(self.names[index])
        if reader.byte() != QNAME:
            raise ValueError('Expected a public QName')
        kind, prefix = self.namespaces[reader.variable()]
        if kind != PACKAGE_NS:
            raise ValueError('Unexpected package namespace in owned class')
        return self.strings[prefix], self.strings[reader.variable()]

    def qname_index(self, qname):
        namespace, name = qname
        for text in (namespace, name):
            if text not in self.strings:
                self.strings.append(text)
        namespace_entry = (PACKAGE_NS, self.strings.index(namespace))
        if namespace_entry not in self.namespaces:
            self.namespaces.append(namespace_entry)
        entry = b'\x07' + _u30(self.namespaces.index(namespace_entry)) + _u30(self.strings.index(name))
        if entry not in self.names:
            self.names.append(entry)
        return self.names.index(entry)

    def append_body(self, code, limits):
        index = len(self.methods)
        self.methods.append(b'\x00\x00\x00\x00')  # no arguments, name, or optional flags
        body = MethodBody(Reader(_u30(index) + _join(_u30(value) for value in limits) +
                                 _u30(len(code)) + code + b'\x00\x00'))
        self.bodies.append(body)
        self.by_method[index] = body
        return index


def _script_parts(code, class_id, name):
    reader = Reader(code)

    def opcode(expected):
        if reader.byte() != expected:
            raise ValueError('Unexpected owned class initializer instruction')

    opcode(0xd0)  # getlocal0
    opcode(0x30)  # pushscope
    opcode(0x5d)  # findpropstrict
    lookup = reader.variable()
    scopes = []
    while True:
        opcode(0x60)  # getlex
        target = reader.variable()
        next_op = reader.byte()
        if next_op == 0x58:
            if reader.variable() != class_id:
                raise ValueError('Wrong newclass index in owned initializer')
            break
        if next_op != 0x30:
            raise ValueError('Expected pushscope after ancestor lookup')
        scopes.append(target)
    for unused in scopes:
        opcode(0x1d)  # popscope
    opcode(0x68)  # initproperty
    if reader.variable() != name:
        raise ValueError('Wrong class binding in script initializer')
    opcode(0x47)  # returnvoid
    if not scopes or target != scopes[-1] or reader.pos != len(code):
        raise ValueError('Unbalanced ancestor scopes in owned initializer')
    return lookup, tuple(scopes)


def _script_code(lookup, scopes, class_id, name):
    return (b'\xd0\x30\x5d' + _u30(lookup) +
            _join(b'\x60' + _u30(ancestor) + b'\x30' for ancestor in scopes) +
            b'\x60' + _u30(scopes[-1]) + b'\x58' + _u30(class_id) +
            b'\x1d' * len(scopes) + b'\x68' + _u30(name) + b'\x47')


def _script_limits(scopes):
    return 2, 1, 1, len(scopes) + 2


def _cinit_limits(scopes):
    return 1, 1, len(scopes) + 2, len(scopes) + 3


def _iinit_limits(scopes, stack=2):
    return stack, 1, len(scopes) + 3, len(scopes) + 4


def _add_ancestor(abc, name, scopes):
    name_index = abc.qname_index(name)
    class_id = len(abc.instances)
    script = abc.append_body(_script_code(name_index, scopes, class_id, name_index),
                             _script_limits(scopes))
    cinit = abc.append_body(_CLASS_INIT, _cinit_limits(scopes))
    iinit = abc.append_body(_ANCESTOR_INIT, _iinit_limits(scopes, stack=1))
    abc.instances.append(Instance(Reader(
        _u30(name_index) + _u30(scopes[-1]) + b'\x00\x00' + _u30(iinit) + b'\x00')))
    abc.class_traits.append(_u30(cinit) + b'\x00')
    abc.cinits.append(cinit)
    return Script(Reader(_u30(script) + b'\x01' + _u30(name_index) + b'\x04\x00' + _u30(class_id)))


def _rewrite(abc):
    if len(abc.instances) != 22 or len(abc.scripts) != 22 or len(abc.methods) != 106:
        raise ValueError('Unexpected original host layout')
    original_scripts = dict((script.class_id, script) for script in abc.scripts)
    if len(original_scripts) != 22 or abc.qname(abc.scripts[-1].name) != (b'', b'GRZReticlePreview'):
        raise ValueError('Unexpected original host script layout')

    original = dict((abc.qname(instance.name), (index, instance))
                    for index, instance in enumerate(abc.instances))
    first = original_scripts[0]
    unused_lookup, primitives = _script_parts(abc.by_method[first.initializer].code,
                                              first.class_id, first.name)
    if tuple(abc.qname(item)[1] for item in primitives) != _PRIMITIVE_BASES:
        raise ValueError('Unexpected Flash primitive chain')
    if abc.qname(primitives[-1]) != CLIP or abc.qname(primitives[-2]) != SPRITE:
        raise ValueError('Unexpected Flash MovieClip/Sprite namespaces')
    scopes = {CLIP: primitives, SPRITE: primitives[:-1]}

    new_scripts = []
    for name, parent in ANCESTORS:
        if name in original or name in scopes or parent not in scopes:
            raise ValueError('Invalid or duplicate inert class ancestry')
        new_scripts.append(_add_ancestor(abc, name, scopes[parent]))
        scopes[name] = scopes[parent] + (abc.qname_index(name),)

    for name, parent in RETARGETS:
        class_id, leaf = original[name]
        script = original_scripts[class_id]
        script_body = abc.by_method[script.initializer]
        cinit = abc.by_method[abc.cinits[class_id]]
        iinit = abc.by_method[leaf.initializer]
        lookup, old_scopes = _script_parts(script_body.code, class_id, leaf.name)
        if (old_scopes != primitives or leaf.parent != primitives[-1] or
                script_body.limits != _script_limits(primitives) or
                cinit.limits != _cinit_limits(primitives) or
                iinit.limits != _iinit_limits(primitives) or
                iinit.code != _CLIP_INIT or cinit.code != _CLASS_INIT):
            raise ValueError('Unexpected original inert leaf')
        new_scopes = scopes[parent]
        leaf.parent = new_scopes[-1]
        script_body.code = _script_code(lookup, new_scopes, class_id, leaf.name)
        script_body.limits = _script_limits(new_scopes)
        cinit.limits = _cinit_limits(new_scopes)
        iinit.limits = _iinit_limits(new_scopes)
        if parent == SPRITE:
            # Sprite supports the existing input flags, but has no stop().
            iinit.code = iinit.code[:5] + iinit.code[10:]
    abc.scripts[:0] = new_scripts


def _verify(before, after):
    expected = dict(ancestry_bindings())
    count = len(before.instances)
    if (len(after.instances) != count + len(ANCESTORS) or len(after.scripts) != len(after.instances)
            or len(after.methods) != len(before.methods) + len(ANCESTORS) * 3
            or after.numeric_prefix != before.numeric_prefix
            or after.strings[:len(before.strings)] != before.strings
            or after.namespaces[:len(before.namespaces)] != before.namespaces
            or after.names[:len(before.names)] != before.names
            or after.methods[:len(before.methods)] != before.methods
            or after.class_traits[:count] != before.class_traits
            or after.namespace_sets != before.namespace_sets or after.metadata != before.metadata
            or [s.raw for s in after.scripts[-count:]] != [s.raw for s in before.scripts]):
        raise ValueError('Unexpected change to existing host definitions')
    definitions = {}
    script_order = {}
    scopes = {}
    allowed_method_changes = set()
    for order, script in enumerate(after.scripts):
        leaf = after.instances[script.class_id]
        name = after.qname(script.name)
        if leaf.name != script.name or name in definitions:
            raise ValueError('Duplicate or mismatched package class export')
        definitions[name] = after.qname(leaf.parent)
        script_order[name] = order
        if name not in expected:
            continue
        parent = expected[name]
        if definitions[name] != parent:
            raise ValueError('Incorrect direct superclass')
        init = after.by_method[script.initializer]
        cinit = after.by_method[after.cinits[script.class_id]]
        iinit = after.by_method[leaf.initializer]
        unused_lookup, indices = _script_parts(init.code, script.class_id, script.name)
        chain = tuple(after.qname(index) for index in indices)
        if (chain[-1] != parent or len(set(chain)) != len(chain) or
                init.limits != _script_limits(indices) or cinit.limits != _cinit_limits(indices)
                or iinit.limits != _iinit_limits(indices, stack=1 if script.class_id >= count else 2)
                or cinit.code != _CLASS_INIT or any(body.tail != b'\x00\x00' for body in (init, cinit, iinit))):
            raise ValueError('Invalid emitted class scope or initializer')
        scopes[name] = chain
        if script.class_id < count:
            old = before.instances[script.class_id]
            allowed_method_changes.update((script.initializer, before.cinits[script.class_id], old.initializer))
            constructor = _CLIP_INIT if parent != SPRITE else _CLIP_INIT[:5] + _CLIP_INIT[10:]
            if old.name != leaf.name or old.tail != leaf.tail or iinit.code != constructor:
                raise ValueError('Unexpected modification of a legacy inert class')
        elif iinit.code != _ANCESTOR_INIT:
            raise ValueError('New class constructor is not inert')

    if set(scopes) != set(expected):
        raise ValueError('Expected ancestry or adapter class is absent')
    for name, chain in scopes.items():
        parent = expected[name]
        if parent in script_order:
            if script_order[parent] >= script_order[name] or chain != scopes[parent] + (parent,):
                raise ValueError('Owned class ancestors are not initialized in dependency order')
        elif tuple(part[1] for part in chain) != _PRIMITIVE_BASES[:len(chain)]:
            raise ValueError('Wrong primitive scope chain')
    for index, instance in enumerate(before.instances):
        if before.qname(instance.name) not in expected and instance.encode() != after.instances[index].encode():
            raise ValueError('Unrelated class was modified')
    for method, body in before.by_method.items():
        if method not in allowed_method_changes and body.encode() != after.by_method[method].encode():
            raise ValueError('Unrelated host or adapter method was modified')


def patch_ancestry(raw):
    if hashlib.sha256(raw).hexdigest() != REFERENCE:
        raise ValueError('Refusing to patch an unrecognized owned host')
    body = _uncompress(raw)
    tags = list(_tags(body))
    abc_tags = [entry for entry in tags if entry[2] == 82]
    if len(abc_tags) != 1:
        raise ValueError('Expected one owned ABC tag')
    start, end, kind, data = abc_tags[0]
    header_end = data.index(b'\x00', 4) + 1
    if data[:4] != b'\x00\x00\x00\x00' or data[4:header_end - 1] != b'GRZReticlePreview':
        raise ValueError('Unexpected owned ABC loading policy')
    header, original = data[:header_end], data[header_end:]
    before, updated = OwnedAbc(original), OwnedAbc(original)
    if before.encode() != original:
        raise ValueError('Original owned ABC does not round trip')
    _rewrite(updated)
    changed = updated.encode()
    _verify(before, OwnedAbc(changed))
    tag = header + changed
    new_body = body[:start] + struct.pack('<HI', (kind << 6) | 63, len(tag)) + tag + body[end:]
    payload = zlib.compress(new_body, 9) if raw[:3] == b'CWS' else new_body
    result = raw[:4] + struct.pack('<I', len(new_body) + 8) + payload
    if [(kind, tag) for _, _, kind, tag in _tags(_uncompress(result)) if kind != 82] != [
            (kind, tag) for _, _, kind, tag in tags if kind != 82]:
        raise ValueError('Unexpected non-code changes to owned SWF')
    return result
