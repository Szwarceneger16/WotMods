# -*- coding: utf-8 -*-
"""Bounded local settings with atomic, Python 2.7-compatible replacement."""
from __future__ import absolute_import

from copy import deepcopy
import ctypes
import errno
import json
import os
import sys
import tempfile

from .hotkeys import chords_conflict, normalize_chord

try:
    _TEXT_TYPE = unicode
    _STRING_TYPES = (basestring,)
    _NUMBER_TYPES = (int, long, float)
except NameError:
    _TEXT_TYPE = str
    _STRING_TYPES = (str, bytes)
    _NUMBER_TYPES = (int, float)

CONFIG_MAX_BYTES = 16384
VOICE_LANGUAGES = ('auto', 'en', 'pl', 'ru', 'fr', 'de', 'es', 'uk')
DEFAULT_HOTKEYS = {'toggle_mod': ['CTRL', 'ALT', 'M'],
                   'toggle_voice': ['CTRL', 'ALT', 'V']}
DEFAULTS = {'language': 'auto', 'enabled': True, 'voice_enabled': True,
            'voice_volume': 70, 'hotkeys': DEFAULT_HOTKEYS}


class _ChangedConfiguration(Exception):
    pass


def _reject_constant(unused_value):
    raise ValueError('non-finite JSON constant')


def _json_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate JSON key')
        result[key] = value
    return result


def _read_document(path):
    """Return a JSON object and its exact bounded snapshot; None means absent."""
    try:
        with open(path, 'rb') as handle:
            raw = handle.read(CONFIG_MAX_BYTES + 1)
    except IOError as error:
        if error.errno == errno.ENOENT:
            return {}, None
        raise
    if len(raw) > CONFIG_MAX_BYTES:
        raise ValueError('configuration exceeds size limit')
    document = json.loads(raw.decode('utf-8-sig'), parse_constant=_reject_constant,
                          object_pairs_hook=_json_object)
    if not isinstance(document, dict):
        raise ValueError('configuration must be an object')
    return document, raw


def _effective_hotkeys(document):
    source = document.get('hotkeys', {})
    result = deepcopy(source) if isinstance(source, dict) else {}
    for action, default in DEFAULT_HOTKEYS.items():
        try:
            result[action] = normalize_chord(source.get(action, default))
        except (AttributeError, TypeError, ValueError):
            result[action] = list(default)
    if chords_conflict(result['toggle_mod'], result['toggle_voice']):
        for action, default in DEFAULT_HOTKEYS.items():
            result[action] = list(default)
    return result


def _effective_payload(document):
    result = deepcopy(document)
    language = document.get('language', 'auto')
    if isinstance(language, _STRING_TYPES):
        try:
            if not isinstance(language, _TEXT_TYPE):
                language = language.decode('utf-8')
            language = language.strip().lower().replace('_', '-').split('-')[0]
        except (UnicodeError, AttributeError):
            language = 'auto'
    result['language'] = language if language in VOICE_LANGUAGES else 'auto'
    for key in ('enabled', 'voice_enabled'):
        value = document.get(key, True)
        result[key] = value if isinstance(value, bool) else True
    value = document.get('voice_volume', 70)
    result['voice_volume'] = (value if not isinstance(value, bool) and
                              isinstance(value, _NUMBER_TYPES) and 0 <= value <= 100 else 70)
    result['hotkeys'] = _effective_hotkeys(document)
    return result


def _windows_path(path):
    if not isinstance(path, _TEXT_TYPE):
        path = path.decode(sys.getfilesystemencoding() or 'utf-8')
    path = os.path.abspath(path)
    if path.startswith('\\\\?\\'):
        return path
    if path.startswith('\\\\'):
        return '\\\\?\\UNC\\' + path[2:]
    return '\\\\?\\' + path


def _replace_file(source, destination, replace_existing):
    """Only move the completed temp file; never delete the live config first."""
    if os.name == 'nt':
        # https://learn.microsoft.com/windows/win32/api/winbase/nf-winbase-movefileexw
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        move = kernel.MoveFileExW
        move.argtypes = (ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_uint32)
        move.restype = ctypes.c_int
        flags = 0x8 | (0x1 if replace_existing else 0)  # WRITE_THROUGH / REPLACE_EXISTING
        if not move(_windows_path(source), _windows_path(destination), flags):
            raise OSError(ctypes.get_last_error(), 'configuration replacement failed')
    elif replace_existing:
        os.rename(source, destination)
    else:
        # Link the complete file into place exclusively. A config created by
        # another writer must not be overwritten during first-time setup.
        os.link(source, destination)
        try:
            os.unlink(source)
        except OSError:
            # The complete destination is already committed; a leftover private
            # temp file must not make disk and in-memory settings disagree.
            pass


def _write_document(path, document, expected_snapshot):
    encoded = (json.dumps(document, ensure_ascii=False, allow_nan=False,
                          indent=2, sort_keys=True) + '\n').encode('utf-8')
    if len(encoded) > CONFIG_MAX_BYTES:
        raise ValueError('configuration exceeds size limit')
    folder = os.path.dirname(path)
    if not os.path.isdir(folder):
        try:
            os.makedirs(folder)
        except OSError:
            if not os.path.isdir(folder):
                raise
    descriptor, temporary = tempfile.mkstemp(prefix='.staysharp-medkit-', suffix='.tmp', dir=folder)
    try:
        with os.fdopen(descriptor, 'wb') as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        # Refresh immediately before publishing. A detected concurrent edit is
        # left intact; callers can reload and retry from its current contents.
        unused_document, snapshot = _read_document(path)
        if snapshot != expected_snapshot:
            raise _ChangedConfiguration()
        _replace_file(temporary, path, expected_snapshot is not None)
        temporary = None
    finally:
        if temporary is not None:
            try:
                os.unlink(temporary)
            except OSError:
                pass


class SettingsStore(object):
    """Keep the last usable payload; update memory and listeners after saving.

    ``load()`` creates a missing configuration, but never rewrites an existing
    malformed file. ``update_hotkeys`` merges with a fresh disk read so language,
    volume, switches and unknown fields survive a later garage edit.
    """
    def __init__(self, path, log=None, on_change=None):
        self.path = path
        self.log = log
        self.on_change = on_change
        self.last_error = None
        self._payload = deepcopy(DEFAULTS)

    def _report(self, code):
        self.last_error = code
        if callable(self.log):
            try:
                self.log('settings ' + code)
            except Exception:
                pass

    def _has_path(self):
        return isinstance(self.path, _STRING_TYPES) and bool(self.path) and os.path.isabs(self.path)

    def get_payload(self):
        return deepcopy(self._payload)

    def payload(self):
        return self.get_payload()

    def set_on_change(self, callback):
        self.on_change = callback

    def load(self):
        if not self._has_path():
            self._report('unavailable_path')
            return self.get_payload()
        try:
            document, snapshot = _read_document(self.path)
            if snapshot is None:
                document = deepcopy(DEFAULTS)
                _write_document(self.path, document, None)
            self._payload = _effective_payload(document)
            self.last_error = None
        except Exception:
            self._report('load_failed')
        return self.get_payload()

    def update_hotkeys(self, changes):
        if not self._has_path():
            self._report('unavailable_path')
            return False
        if not isinstance(changes, dict) or not changes or any(key not in DEFAULT_HOTKEYS for key in changes):
            self._report('invalid_hotkeys')
            return False
        try:
            normalized = {action: normalize_chord(value) for action, value in changes.items()}
        except (TypeError, ValueError):
            self._report('invalid_hotkeys')
            return False
        try:
            document, snapshot = _read_document(self.path)
        except Exception:
            self._report('load_failed')
            return False
        if snapshot is None:
            document = deepcopy(DEFAULTS)
        hotkeys = _effective_hotkeys(document)
        hotkeys.update(normalized)
        try:
            if chords_conflict(hotkeys['toggle_mod'], hotkeys['toggle_voice']):
                self._report('conflicting_hotkeys')
                return False
            document['hotkeys'] = hotkeys
            candidate = _effective_payload(document)
            _write_document(self.path, document, snapshot)
        except _ChangedConfiguration:
            self._report('changed_configuration')
            return False
        except Exception:
            self._report('save_failed')
            return False
        self._payload = candidate
        self.last_error = None
        if callable(self.on_change):
            try:
                self.on_change(self.get_payload())
            except Exception:
                # The configuration is already committed. A listener failure
                # cannot be reported as a failed save or roll the disk back.
                if callable(self.log):
                    try:
                        self.log('settings callback_failed')
                    except Exception:
                        pass
        return True
