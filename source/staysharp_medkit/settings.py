# -*- coding: utf-8 -*-
"""Bounded settings with recoverable writes using embedded Python 2.7 stdlib."""
from __future__ import absolute_import

from copy import deepcopy
import errno
import json
import os
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
BACKUP_SUFFIX = '.staysharp-backup'
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


def _read_document_raw(path):
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


def _recover_backup(path):
    """Recover a stopped Windows rename transaction before creating defaults.

    A complete primary always wins. Never replace malformed user data, discard
    an invalid backup, or overwrite a concurrently created primary.
    """
    backup = path + BACKUP_SUFFIX
    if not os.path.lexists(backup):
        return
    unused_document, primary_snapshot = _read_document_raw(path)
    if primary_snapshot is None:
        unused_document, backup_snapshot = _read_document_raw(backup)
        if backup_snapshot is not None:
            _replace_file(backup, path, False)
        return
    try:
        unused_document, backup_snapshot = _read_document_raw(backup)
    except Exception:
        # An unexpected recovery artifact is retained. A valid primary can be
        # read, but another fallback write must not overwrite that artifact.
        return
    if backup_snapshot is not None:
        try:
            os.unlink(backup)
        except OSError:
            # Reading a valid committed primary must not fail on cleanup.
            pass


def _read_document(path):
    _recover_backup(path)
    return _read_document_raw(path)


def _replace_file(source, destination, replace_existing, expected_snapshot=None):
    """Publish a complete file without optional native Python extensions.

    Windows Python 2.7 has no replacing rename. Its fallback keeps one bounded
    recovery backup, rolls back ordinary failures, and recovers after restart.
    The two renames have a brief missing-primary window; they are not one atomic
    OS operation. POSIX rename and an available os.replace remain atomic.
    """
    if not replace_existing:
        if os.name == 'nt':
            # Windows rename is create-only: a concurrent config wins.
            os.rename(source, destination)
        else:
            os.link(source, destination)
            try:
                os.unlink(source)
            except OSError:
                # Publication succeeded; temporary cleanup cannot undo it.
                pass
        return
    if os.name != 'nt':
        os.rename(source, destination)
        return
    replace = getattr(os, 'replace', None)
    if callable(replace):
        replace(source, destination)
        return
    backup = destination + BACKUP_SUFFIX
    if os.path.lexists(backup):
        # Recovery runs before each read/write. Leftover evidence must never
        # be overwritten if it could not be recovered or cleaned safely.
        raise _ChangedConfiguration()
    os.rename(destination, backup)
    try:
        unused_document, moved_snapshot = _read_document_raw(backup)
        if expected_snapshot is not None and moved_snapshot != expected_snapshot:
            raise _ChangedConfiguration()
        os.rename(source, destination)
    except Exception:
        if not os.path.lexists(destination):
            try:
                os.rename(backup, destination)
            except Exception:
                # The complete original remains at the fixed recovery name.
                # The next load retries restoration before creating defaults.
                pass
        raise
    try:
        os.unlink(backup)
    except OSError:
        # The new primary is committed. Keep memory/callbacks consistent even
        # if the previous complete file can only be cleaned on the next load.
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
        _replace_file(temporary, path, expected_snapshot is not None, expected_snapshot)
        temporary = None
    finally:
        if temporary is not None:
            try:
                os.unlink(temporary)
            except OSError:
                pass


class SettingsStore(object):
    """Keep the last usable payload; update memory and listeners after saving.

    ``load()`` recovers an interrupted Windows transaction before creating a
    missing configuration, and never rewrites an existing malformed file.
    ``update_hotkeys`` merges with a fresh disk read so language,
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
