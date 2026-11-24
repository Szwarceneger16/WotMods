# -*- coding: ascii -*-
"""Pure aim-time estimate, presentation settings and bounded persistence.

No game modules or native input interfaces are imported here. The Windows
Python-2 fallback is recoverable, not a single atomic replace operation.
"""
from __future__ import absolute_import

import errno
import json
import math
import os
import stat
import tempfile

from .preview_catalog import profile as _preview_profile
from .preview_catalog import translations


try:
    _NUMBERS = (int, long, float)
    _TEXT = (str, unicode)
except NameError:
    _NUMBERS = (int, float)
    _TEXT = (str,)

CONFIG_MAX_BYTES = 16384
BACKUP_SUFFIX = '.aimtimer-backup'
_WINDOWS = os.name == 'nt'
_UNSET = object()

DEFAULTS = {
    'schema_version': 4,
    'enabled': True,
    'hud_offset_arcade_x': 0,
    'hud_offset_arcade_y': 40,
    'hud_offset_sniper_x': 0,
    'hud_offset_sniper_y': 40,
    'hud_offset_arty_x': 0,
    'hud_offset_arty_y': 40,
    'preview_variant_arcade': 'standard',
    'preview_variant_sniper': 'standard',
    'preview_variant_arty': 'standard',
    'hud_font_px': 16,
    'hud_background_opacity': 0.50,
    'hud_frame_scale_pct': 110,
}
COLOURS = {
    'green': (102, 225, 118),
    'neutral': (185, 193, 203),
}
_FACTOR_BOUNDS = (1e-12, 1e12)
_AIMING_TIME_BOUNDS = (1e-6, 3600.0)
_MAX_REMAINING_SECONDS = 86400.0
_READY_RATIO_EPSILON = 1e-9


def _number(value, minimum, maximum):
    """Accept only finite, owned built-in numeric primitives, excluding bool."""
    if type(value) not in _NUMBERS:
        return None
    try:
        result = float(value)
        if math.isnan(result) or math.isinf(result) or not minimum <= result <= maximum:
            return None
        return result
    except (OverflowError, ValueError, TypeError):
        return None


def _choice(value, choices):
    return value if type(value) in _TEXT and value in choices else None


def _setting(key, value):
    if key == 'schema_version':
        return 4 if type(value) is int and value == 4 else None
    if key in ('preview_variant_arcade', 'preview_variant_sniper',
               'preview_variant_arty'):
        mode = key[len('preview_variant_'):]
        if value == 'cav_mod_71':
            value = 'autoreloader_surge'
        return value if _preview_profile(value, mode) is not None else None
    if key == 'enabled':
        return value if type(value) is bool else None
    if key in ('hud_offset_arcade_x', 'hud_offset_arcade_y',
               'hud_offset_sniper_x', 'hud_offset_sniper_y',
               'hud_offset_arty_x', 'hud_offset_arty_y',
               'hud_font_px', 'hud_frame_scale_pct'):
        bounds = ((12, 40) if key == 'hud_font_px' else
                  (100, 300) if key == 'hud_frame_scale_pct' else
                  (-32768, 32768))
        number = _number(value, *bounds)
        return int(number) if number is not None and number == int(number) else None
    if key == 'hud_background_opacity':
        return _number(value, 0.0, 1.0)
    return None


def validate_config(raw, strict=False):
    """Return a complete primitive configuration with per-camera 2D positions.

    Loading expands a valid legacy global Y offset into all three camera modes,
    then applies valid explicit per-mode values. Strict saves accept only the
    current schema/fields; merely loading never rewrites the settings file.
    """
    if type(raw) is not dict:
        if strict:
            raise ValueError('configuration_not_object')
        return dict(DEFAULTS)
    result = dict(DEFAULTS)
    if not strict:
        legacy = _setting('hud_offset_arcade_y', raw.get('hud_offset_y'))
        if legacy is not None:
            for field in ('hud_offset_arcade_y', 'hud_offset_sniper_y',
                          'hud_offset_arty_y'):
                result[field] = legacy
    for key, value in raw.items():
        if type(key) not in _TEXT or key not in DEFAULTS:
            if strict:
                raise ValueError('unknown_setting')
            continue
        checked = _setting(key, value)
        if checked is None:
            if strict:
                raise ValueError('invalid_' + key)
        else:
            result[key] = checked
    legacy_schema = ('schema_version' not in raw or
                     (type(raw.get('schema_version')) is int and
                      raw['schema_version'] == 1))
    if (not strict and legacy_schema and
            _setting('hud_font_px', raw.get('hud_font_px')) == 24):
        # Reduce the old default while preserving other user-chosen sizes.
        result['hud_font_px'] = DEFAULTS['hud_font_px']
    return result


def mode_group(mode):
    """Return the owned placement family for a native camera mode."""
    checked = _choice(mode, ('arcade', 'dualgun', 'twinGun', 'sniper',
                             'strategic', 'arty'))
    return ('sniper' if checked == 'sniper' else
            'arty' if checked in ('strategic', 'arty') else 'arcade')


def mode_preview(config, mode):
    """Read one supported editor preview ID for the native camera family."""
    group = mode_group(mode)
    return validate_config(config)['preview_variant_' + group]


def mode_position(config, mode):
    """Read both signed logical-pixel offsets for one camera family."""
    group = mode_group(mode)
    result = validate_config(config)
    return (result['hud_offset_' + group + '_x'],
            result['hud_offset_' + group + '_y'])


def with_mode_position(config, mode, x, y):
    """Return an owned configuration, changing only one camera position.

    Legacy configuration is normalized without modifying its input. Coordinates
    are finite integral numeric primitives; arbitrary objects are never coerced.
    """
    if type(config) is not dict:
        raise ValueError('configuration_not_object')
    group = mode_group(mode)
    x_field, y_field = 'hud_offset_' + group + '_x', 'hud_offset_' + group + '_y'
    x, y = _setting(x_field, x), _setting(y_field, y)
    if x is None or y is None:
        raise ValueError('invalid_position')
    result = validate_config(config)
    result[x_field], result[y_field] = x, y
    return validate_config(result, strict=True)


def mode_offset(config, mode):
    """Compatibility helper for callers needing only the vertical offset."""
    return mode_position(config, mode)[1]


def estimate_remaining(current_factor, base_factor, aiming_time):
    """Invert the client's exponential decay to its stationary hard floor.

    Inputs are dimensionless current/base dispersion factors and the current
    battle aiming-time constant in seconds. The adapter owns native-state
    freshness and mechanic support checks. This estimate assumes no additional
    movement, firing or other bloom. Invalid or implausible inputs return None.
    """
    current = _number(current_factor, *_FACTOR_BOUNDS)
    base = _number(base_factor, *_FACTOR_BOUNDS)
    constant = _number(aiming_time, *_AIMING_TIME_BOUNDS)
    if current is None or base is None or constant is None:
        return None
    ratio = current / base
    if ratio <= 1.0 + _READY_RATIO_EPSILON:
        return 0.0
    return _number(constant * math.log(ratio), 0.0, _MAX_REMAINING_SECONDS)


def format_reading(remaining_s, config, language='en'):
    """Return one opaque seconds reading, rounding positive estimates upward to hundredths.

    Appearance settings are consumed by the HUD; background opacity must never
    dim the text. A tilde distinguishes a positive prediction from ready state.
    """
    number = _number(remaining_s, 0.0, _MAX_REMAINING_SECONDS)
    condition = True if number == 0.0 else None
    category = 'green' if condition is True else 'neutral'
    if number is None:
        text = '-- s'
    else:
        # Suppress binary-float noise at exact hundredths (1.1 * 100 can
        # exceed110), while keeping every positive result above displayed0.
        rounded = (max(1.0, math.ceil(number * 100.0 - 1e-9)) / 100.0
                   if number > 0.0 else 0.0)
        text = ('~' if number > 0.0 else '') + '%.2f s' % rounded
        text = translations.localize_decimal(text, language)
    return {
        'text': text,
        'condition': condition,
        'colour': COLOURS[category] + (255,),
    }


class _ChangedConfiguration(Exception):
    pass


class _UnsafePath(Exception):
    pass


def _validate_path(path):
    if type(path) not in _TEXT or not path or '\x00' in path or not os.path.isabs(path):
        raise _UnsafePath('absolute_path_required')
    current = os.path.abspath(path)
    # Do not follow symlink components. This is not a defence against a hostile
    # process racing directory replacements with equal privileges.
    while True:
        try:
            mode = os.lstat(current).st_mode
            if stat.S_ISLNK(mode):
                raise _UnsafePath('symlink_path')
            if current == os.path.abspath(path) and not stat.S_ISREG(mode):
                raise _UnsafePath('not_regular_file')
        except OSError as error:
            if error.errno != errno.ENOENT:
                raise
        parent = os.path.dirname(current)
        if current == parent:
            break
        current = parent


def _read_bytes(path):
    _validate_path(path)
    flags = os.O_RDONLY | getattr(os, 'O_BINARY', 0) | getattr(os, 'O_NOFOLLOW', 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as error:
        if error.errno == errno.ENOENT:
            return None
        raise
    with os.fdopen(descriptor, 'rb') as handle:
        if not stat.S_ISREG(os.fstat(handle.fileno()).st_mode):
            raise _UnsafePath('not_regular_file')
        content = handle.read(CONFIG_MAX_BYTES + 1)
    if len(content) > CONFIG_MAX_BYTES:
        raise ValueError('configuration_too_large')
    return content


def _reject_constant(unused):
    raise ValueError('nonfinite_json')


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate_json_key')
        result[key] = value
    return result


def _parse(content):
    document = json.loads(content.decode('utf-8-sig'), parse_constant=_reject_constant,
                          object_pairs_hook=_unique_object)
    if type(document) is not dict:
        raise ValueError('configuration_not_object')
    return document


def _read_state(path):
    primary = _read_bytes(path)
    if primary is not None:
        return _parse(primary), ('primary', primary)
    backup = _read_bytes(path + BACKUP_SUFFIX)
    if backup is not None:
        return _parse(backup), ('backup', backup)
    return {}, ('missing', None)


def _clear_valid_backup(path):
    backup = path + BACKUP_SUFFIX
    raw = _read_bytes(backup)
    if raw is not None:
        _parse(raw)
        os.unlink(backup)


def _create_only(source, destination):
    if _WINDOWS:
        # Real Windows rename refuses an existing destination.
        os.rename(source, destination)
    else:
        os.link(source, destination)
        try:
            os.unlink(source)
        except OSError:
            # The complete destination is already committed.
            pass


def _publish(source, destination, snapshot):
    origin, original = snapshot
    if origin != 'primary':
        _create_only(source, destination)
        return
    if not _WINDOWS:
        os.rename(source, destination)
        return
    replace = getattr(os, 'replace', None)
    if callable(replace):
        replace(source, destination)
        return
    backup = destination + BACKUP_SUFFIX
    # A previous complete primary makes an old validated recovery copy
    # redundant. This cleanup happens only during an explicit save.
    _clear_valid_backup(destination)
    os.rename(destination, backup)
    try:
        if _read_bytes(backup) != original:
            raise _ChangedConfiguration('moved_snapshot_changed')
        os.rename(source, destination)
    except Exception:
        if not os.path.lexists(destination):
            try:
                os.rename(backup, destination)
            except Exception:
                # The intact original remains readable at the backup name.
                pass
        raise


def _write_state(path, document, expected_snapshot):
    raw = (json.dumps(document, ensure_ascii=True, allow_nan=False,
                      indent=2, sort_keys=True) + '\n').encode('ascii')
    if len(raw) > CONFIG_MAX_BYTES:
        raise ValueError('configuration_too_large')
    _validate_path(path)
    folder = os.path.dirname(path)
    if not os.path.isdir(folder):
        try:
            os.makedirs(folder)
        except OSError:
            if not os.path.isdir(folder):
                raise
    _validate_path(path)
    descriptor, temporary = tempfile.mkstemp(prefix='.grz-aimtimer-', suffix='.tmp', dir=folder)
    try:
        with os.fdopen(descriptor, 'wb') as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        unused, current = _read_state(path)
        if current != expected_snapshot:
            raise _ChangedConfiguration('configuration_changed')
        _publish(temporary, path, expected_snapshot)
        temporary = None
        # Publication has succeeded. Backup cleanup cannot reverse success or
        # leave memory describing the previous version.
        try:
            _clear_valid_backup(path)
        except Exception:
            pass
        return ('primary', raw)
    finally:
        if temporary is not None:
            try:
                os.unlink(temporary)
            except OSError:
                pass


class SettingsStore(object):
    """Bounded local settings; loading never creates, rewrites or renames.

    A missing primary can be read from an intact recovery backup. Explicit
    save publishes a complete new file. Detected concurrent edits are left
    intact and require load() before another save. Successful saves update
    memory even if cleanup of a now-redundant backup fails.
    """
    def __init__(self, path):
        self.path = path
        self._data = dict(DEFAULTS)
        self._snapshot = _UNSET
        self.last_error = None
        self.recovery_used = False

    @property
    def data(self):
        return dict(self._data)

    def load(self):
        try:
            document, snapshot = _read_state(self.path)
            self._data = validate_config(document)
            self._snapshot = snapshot
            self.recovery_used = snapshot[0] == 'backup'
            self.last_error = None
        except _UnsafePath:
            self.last_error = 'unsafe_path'
        except (ValueError, UnicodeError):
            self.last_error = 'invalid_configuration'
        except Exception:
            self.last_error = 'load_failed'
        return self.data

    def save(self, config):
        try:
            checked = validate_config(config, strict=True)
        except (ValueError, TypeError, OverflowError):
            self.last_error = 'invalid_configuration'
            return False
        try:
            if self._snapshot is _UNSET:
                unused, snapshot = _read_state(self.path)
            else:
                snapshot = self._snapshot
            committed = _write_state(self.path, checked, snapshot)
        except _UnsafePath:
            self.last_error = 'unsafe_path'
            return False
        except _ChangedConfiguration:
            self.last_error = 'configuration_changed'
            return False
        except (ValueError, UnicodeError):
            self.last_error = 'invalid_configuration'
            return False
        except Exception:
            self.last_error = 'save_failed'
            return False
        self._data = checked
        self._snapshot = committed
        self.recovery_used = False
        self.last_error = None
        return True
