"""Named keyboard chords and primitive input state; compatible with Python 2.7.

Callers own event subscriptions and chat/modal checks. No native event object is
retained or forwarded, and no GUI component participates in keyboard dispatch.
"""
try:
    string_types = (basestring,)
    integer_types = (int, long)
except NameError:
    string_types = (str,)
    integer_types = (int,)

MAX_CHORD_KEYS = 32
_FAMILIES = {
    'CTRL': frozenset(('CTRL', 'LCTRL', 'RCTRL')),
    'ALT': frozenset(('ALT', 'LALT', 'RALT')),
    'SHIFT': frozenset(('SHIFT', 'LSHIFT', 'RSHIFT')),
}
_ORDER = ('CTRL', 'LCTRL', 'RCTRL', 'ALT', 'LALT', 'RALT',
          'SHIFT', 'LSHIFT', 'RSHIFT', 'LWIN', 'RWIN')
_ALIASES = {
    'CONTROL': 'CTRL', 'LCONTROL': 'LCTRL', 'RCONTROL': 'RCTRL',
    'LEFTCTRL': 'LCTRL', 'RIGHTCTRL': 'RCTRL',
    'LEFTCONTROL': 'LCTRL', 'RIGHTCONTROL': 'RCTRL',
    'LMENU': 'LALT', 'RMENU': 'RALT', 'MENU': 'ALT',
    'LEFTALT': 'LALT', 'RIGHTALT': 'RALT',
    'LEFTSHIFT': 'LSHIFT', 'RIGHTSHIFT': 'RSHIFT',
    'ESCAPE': 'ESC', 'RETURN': 'ENTER', 'BACK': 'BACKSPACE',
    'CAPITAL': 'CAPSLOCK', 'PRIOR': 'PAGEUP', 'NEXT': 'PAGEDOWN',
    'PGUP': 'PAGEUP', 'PGDN': 'PAGEDOWN', 'DEL': 'DELETE',
    'INS': 'INSERT', 'SPACEBAR': 'SPACE', 'NUMLOCKCLEAR': 'NUMLOCK',
    'ADD': 'NUMADD', 'SUBTRACT': 'NUMSUBTRACT', 'MULTIPLY': 'NUMMULTIPLY',
    'DIVIDE': 'NUMDIVIDE', 'DECIMAL': 'NUMDECIMAL',
}
_STANDARD = set('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789')
_STANDARD.update(('ESC', 'ENTER', 'BACKSPACE', 'TAB', 'SPACE', 'CAPSLOCK',
                  'PAGEUP', 'PAGEDOWN', 'HOME', 'END', 'INSERT', 'DELETE',
                  'UP', 'DOWN', 'LEFT', 'RIGHT', 'NUMLOCK', 'SCROLL', 'PAUSE',
                  'SYSRQ', 'APPS', 'LWIN', 'RWIN', 'MINUS', 'EQUALS',
                  'LBRACKET', 'RBRACKET', 'SEMICOLON', 'APOSTROPHE', 'GRAVE',
                  'BACKSLASH', 'COMMA', 'PERIOD', 'SLASH', 'OEM_102',
                  'NUMADD', 'NUMSUBTRACT', 'NUMMULTIPLY', 'NUMDIVIDE',
                  'NUMDECIMAL', 'NUMPADENTER', 'NUMPADEQUALS'))
_STANDARD.update('F%d' % value for value in range(1, 25))
_STANDARD.update('NUMPAD%d' % value for value in range(10))
for _family in _FAMILIES.values():
    _STANDARD.update(_family)


def _token(value):
    if not isinstance(value, string_types) or not 0 < len(value) <= 64:
        raise ValueError('Key names must be short strings')
    value = value.strip().upper().replace(' ', '')
    if value.startswith('KEY_'):
        value = value[4:]
    value = _ALIASES.get(value, value)
    if (not value or any(char not in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_' for char in value)
            or 'MOUSE' in value or value.startswith(('JOY', 'AXIS', 'BUTTON'))
            or value in ('NONE', 'UNKNOWN', 'UNDEFINED', 'MAX', 'TOTAL', 'NUMKEYS', 'DEBUG')):
        raise ValueError('Unsupported keyboard key name')
    return value


def _registry(keys_module=None):
    if keys_module is None:
        try:
            import Keys
            keys_module = Keys
        except ImportError:
            pass
    names, by_code = set(_STANDARD), {}
    if keys_module is not None:
        for attribute in sorted(dir(keys_module)):
            if not attribute.startswith('KEY_'):
                continue
            try:
                name = _token(attribute)
                code = getattr(keys_module, attribute)
                if isinstance(code, bool) or not isinstance(code, integer_types):
                    continue
            except (ValueError, AttributeError):
                continue
            names.add(name)
            # Prefer a physical side over an alias such as KEY_CONTROL.
            previous = by_code.get(code)
            if previous is None or (previous in _FAMILIES and name not in _FAMILIES):
                by_code[code] = name
    return names, by_code


def _sort_key(name):
    return (_ORDER.index(name), '') if name in _ORDER else (len(_ORDER), name)


def normalize_chord(value, keys_module=None):
    """Return canonical names, or [] for disabled; reject untrusted key codes."""
    if value is None:
        return []
    if isinstance(value, string_types):
        if not value.strip():
            return []
        if len(value) > MAX_CHORD_KEYS * 65:
            raise ValueError('Chord is too long')
        value = value.split('+')
    if not isinstance(value, (list, tuple)) or len(value) > MAX_CHORD_KEYS:
        raise ValueError('Chord must contain at most 32 named keyboard keys')
    allowed, unused_codes = _registry(keys_module)
    names = set()
    for raw in value:
        name = _token(raw)
        if name not in allowed:
            raise ValueError('Unknown keyboard key name')
        names.add(name)
    for generic, family in _FAMILIES.items():
        if generic in names and len(names.intersection(family)) > 1:
            raise ValueError('Generic and side-specific modifiers cannot be combined')
    return sorted(names, key=_sort_key)


def format_chord(value):
    return '+'.join(normalize_chord(value))


def key_name(key, keys_module=None):
    """Convert a primitive key code/name; return None for unsupported input."""
    allowed, by_code = _registry(keys_module)
    if isinstance(key, string_types):
        try:
            name = _token(key)
            return name if name in allowed else None
        except ValueError:
            return None
    if isinstance(key, bool) or not isinstance(key, integer_types):
        return None
    return by_code.get(key)


def _matches(chord, held, exact=True):
    remaining = set(held)
    for name in chord:
        if name in _FAMILIES:
            family = _FAMILIES[name]
            if not remaining.intersection(family):
                return False
            remaining.difference_update(family)
        elif name in remaining:
            remaining.remove(name)
        else:
            return False
    return not remaining if exact else True


def _variants(chord):
    variants = [frozenset()]
    for name in chord:
        if name in _FAMILIES:
            left, right = ('L' + name, 'R' + name)
            choices = (frozenset((left,)), frozenset((right,)), frozenset((left, right)))
        else:
            choices = (frozenset((name,)),)
        variants = [before | choice for before in variants for choice in choices]
    return set(variants)


def chords_conflict(first, second):
    """Whether physical variants overlap or one chord can precede the other.

    A subset can fire while the user is still pressing a longer chord, even
    though action dispatch requires an exact match at each individual edge.
    """
    first, second = normalize_chord(first), normalize_chord(second)
    if not first or not second:
        return False
    return any(a.issubset(b) or b.issubset(a)
               for a in _variants(first) for b in _variants(second))


class ChordTracker(object):
    """Track held keys and capture the largest simultaneous chord on release-all.

    Escape cancels capture; Backspace remains assignable. Capture uses generic
    modifiers by default; side_specific=True preserves left/right variants.
    A blocked event cancels capture and clears state. Call reset on focus loss,
    unsubscribe, or a battle/garage transition so released keys cannot get stuck.
    """
    def __init__(self, chords=None, keys_module=None):
        self._keys_module = keys_module
        self._chords = {}
        self._held = set()
        self._latched = set()
        self._capturing = False
        self._capture_peak = set()
        self._side_specific = False
        self.set_chords(chords or {})

    @property
    def capture_active(self):
        return self._capturing

    @property
    def held_keys(self):
        return tuple(sorted(self._held, key=_sort_key))

    def set_chords(self, chords):
        if not isinstance(chords, dict):
            raise ValueError('Registered chords must be a mapping')
        normalized = {}
        for action, chord in chords.items():
            if not isinstance(action, string_types) or not 0 < len(action) <= 64:
                raise ValueError('Action names must be short strings')
            normalized[action] = normalize_chord(chord, self._keys_module)
        self._chords = normalized
        self.reset()

    def reset(self):
        self._held.clear()
        self._latched.clear()
        self._capturing = False
        self._capture_peak.clear()

    def begin_capture(self, side_specific=False):
        self.reset()
        self._capturing = True
        self._side_specific = bool(side_specific)

    def cancel_capture(self):
        self.reset()

    def reconcile(self, key_state, current_key=None):
        """Discard stale held state after lost key-up events or focus changes.

        Only keys already held by this tracker are queried. The incoming event's
        key is excluded because its native state can change before dispatch.
        Lookup/query failures clear the state too; no background polling occurs.
        """
        if not self._held:
            return False
        unused_names, by_code = _registry(self._keys_module)
        current = key_name(current_key, self._keys_module)
        pending = self._held.difference((current,))
        if not pending:
            return False
        by_name = {}
        for code, name in by_code.items():
            by_name.setdefault(name, []).append(code)
        try:
            if not callable(key_state):
                raise ValueError('Native key state is unavailable')
            for name in pending:
                codes = by_name.get(name)
                if not codes or not any(bool(key_state(code)) for code in codes):
                    self.reset()
                    return True
        except Exception:
            self.reset()
            return True
        return False

    def feed(self, key, is_down, repeated=False, blocked=False):
        result = {'actions': [], 'captured': None, 'cancelled': False}
        if blocked:
            result['cancelled'] = self._capturing
            self.reset()
            return result
        name = key_name(key, self._keys_module)
        if name is None or (is_down and repeated):
            return result
        if self._capturing and is_down and name == 'ESC':
            self.cancel_capture()
            result['cancelled'] = True
            return result
        if is_down:
            if name in self._held:
                return result
            if len(self._held) >= MAX_CHORD_KEYS:
                self.reset()
                result['cancelled'] = True
                return result
            self._held.add(name)
        else:
            self._held.discard(name)
        if self._capturing:
            if is_down and len(self._held) >= len(self._capture_peak):
                self._capture_peak = set(self._held)
            if not self._held and self._capture_peak:
                captured = set(self._capture_peak)
                if not self._side_specific:
                    for generic, family in _FAMILIES.items():
                        if captured.intersection(family):
                            captured.difference_update(family)
                            captured.add(generic)
                result['captured'] = normalize_chord(list(captured), self._keys_module)
                self.reset()
            return result
        for action, chord in sorted(self._chords.items()):
            if not chord:
                continue
            if not _matches(chord, self._held, exact=False):
                self._latched.discard(action)
            elif is_down and action not in self._latched and _matches(chord, self._held):
                self._latched.add(action)
                result['actions'].append(action)
        return result
