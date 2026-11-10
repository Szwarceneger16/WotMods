# -*- coding: utf-8 -*-
"""Opt-in, garage-only export to the owner's private ChatGPT Site.

Compatible with the Python 2.7 interpreter embedded in World of Tanks.
No service, scheduler, background executable, battle hook or remote telemetry.
Only local, rotating diagnostic logs are written to the user's AppData folder.
"""
from __future__ import absolute_import, unicode_literals

import base64
import datetime
import errno
import hashlib
import json
import logging
from logging.handlers import RotatingFileHandler
import os
import re
import struct
import sys
import threading
import time
try:
    from urlparse import urlsplit
except ImportError:
    from urllib.parse import urlsplit
try:
    _INTEGER_TYPES = (int, long)
except NameError:
    _INTEGER_TYPES = (int,)

LOG = logging.getLogger('grz.hangarsync')
MISSION_LOG = logging.getLogger('grz.hangarsync.missions')
VERSION = '0.13.0'
CONFIG_FILE = 'GRZ_Hangar_Sync.json'
LOG_DIR = 'GRZ_Hangar_Sync'
LOG_FILE = 'hangar_sync.log'
MISSION_LOG_FILE = 'missions_diagnostics.log'
MISSION_CATEGORIES = ('daily', 'daily_bonus', 'daily_epic', 'premium',
                      'weekly', 'personal', 'crucible')
MAX_MISSIONS = 160
MAX_CRUCIBLE_CHAINS = 48
MAX_CRUCIBLE_STAGES = 32
LOG_MAX_BYTES = 524288
MAX_CONFIG_BYTES = 8192
MAX_PAYLOAD_BYTES = 1900000
MAX_VEHICLES = 1200
MAX_PLAYLISTS = 100
MAX_PLAYLIST_BYTES = 32768
_VALID_FIELDS = frozenset((
    'enabled', 'endpoint_url', 'device_token', 'sites_access_token', 'region',
    'display_name', 'allowed_players', 'include_crew', 'interval_seconds',
    'include_missions', 'mission_diagnostics',
))
_SAFE_CONFIG_ERRORS = frozenset((
    'config_too_large', 'duplicate_fields', 'unexpected_fields', 'missing_fields',
    'boolean_fields_invalid', 'interval_invalid', 'region_invalid',
    'display_name_invalid', 'players_list_invalid', 'players_list_empty',
    'token_fields_invalid',
    'endpoint_url_invalid', 'tokens_missing_or_invalid', 'game_root_ambiguous',
))
_CLASSES = {
    'heavyTank': 'HT', 'mediumTank': 'MT', 'lightTank': 'LT',
    'AT-SPG': 'TD', 'SPG': 'SPG',
}
_NATIONS = {
    'ussr': 'U.S.S.R.', 'usa': 'U.S.A.', 'uk': 'U.K.',
    'germany': 'Germany', 'france': 'France', 'china': 'China',
    'japan': 'Japan', 'czech': 'Czechoslovakia', 'sweden': 'Sweden',
    'poland': 'Poland', 'italy': 'Italy',
}
_state = None
_mission_probe = None


class ConfigError(ValueError):
    """A constant diagnostic code; never contains config text or tokens."""


class MissionSourcePending(RuntimeError):
    """The game's service is still loading."""


class TLSUnavailable(RuntimeError):
    """Safe marker for clients missing the verified HTTPS implementation."""


def start_diagnostics(environ=None, logger=LOG, filename=LOG_FILE):
    """Write bounded, local-only logs under the signed-in Windows user's AppData."""
    if logger.handlers:
        return True
    env = os.environ if environ is None else environ
    base = env.get('APPDATA') or env.get('LOCALAPPDATA')
    if isinstance(base, bytes):
        # Python 2 on Windows may supply a local-codepage path with accents.
        try:
            base = base.decode(sys.getfilesystemencoding() or 'mbcs')
        except (LookupError, UnicodeError):
            return False
    if not base or not os.path.isabs(base):
        return False
    folder = os.path.join(base, LOG_DIR)
    try:
        if not os.path.isdir(folder):
            os.makedirs(folder)
        handler = RotatingFileHandler(os.path.join(folder, filename),
                                      maxBytes=LOG_MAX_BYTES, backupCount=2,
                                      encoding='utf-8')
    except (IOError, OSError):
        return False
    formatter = logging.Formatter('%(asctime)sZ %(levelname)s %(message)s')
    formatter.converter = time.gmtime
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    logger.propagate = False
    logger.info('event=mod_initialized version=%s', VERSION)
    return True


def _config_error_code(error):
    if isinstance(error, ConfigError):
        code = str(error)
        return code if code in _SAFE_CONFIG_ERRORS else 'invalid_config'
    if isinstance(error, (IOError, OSError)):
        if getattr(error, 'errno', None) == errno.ENOENT:
            return 'file_not_found'
        if getattr(error, 'errno', None) in (errno.EACCES, errno.EPERM):
            return 'access_denied'
        return 'file_io_failed'
    if isinstance(error, (ValueError, UnicodeError, TypeError)):
        return 'malformed_json'
    return 'unexpected_failure'


def _safe_exception_type(error):
    name = type(error).__name__
    if name in ('ImportError', 'AttributeError', 'KeyError', 'TypeError',
                'ValueError', 'RuntimeError', 'IndexError', 'IOError',
                'OSError', 'OverflowError', 'UnicodeError', 'ConfigError'):
        return name
    return 'unexpected'


def _network_error_kind(error):
    """Never format arbitrary exception messages, URLs or response bodies."""
    status = getattr(error, 'code', None)
    if type(status) is int and 100 <= status <= 599:
        return 'http', status
    reason = getattr(error, 'reason', None)
    names = (type(error).__name__, type(reason).__name__ if reason is not None else '')
    if 'SSLError' in names or 'CertificateError' in names:
        return 'tls', 0
    if 'TLSUnavailable' in names:
        return 'tls', 0
    if 'timeout' in names or 'TimeoutError' in names:
        return 'timeout', 0
    if 'URLError' in names:
        return 'connection', 0
    if 'ConfigError' in names:
        return 'configuration', 0
    if any(name in names for name in ('RuntimeError', 'ValueError',
                                     'TypeError', 'JSONDecodeError')):
        return 'protocol', 0
    return 'unexpected', 0


def _valid_sync_endpoint(url):
    """Accept only a private ChatGPT Site's sync route, not arbitrary receivers."""
    if (not isinstance(url, type('')) or not 20 <= len(url) <= 400 or
            '?' in url or '#' in url or
            any(ord(character) <= 32 or ord(character) >= 127 for character in url)):
        return False
    try:
        parts = urlsplit(url)
        host = parts.hostname
        return bool(parts.scheme == 'https' and parts.netloc == host and
                    parts.path == '/api/sync' and not parts.query and
                    not parts.fragment and not parts.username and
                    not parts.password and parts.port is None and
                    host is not None and len(host) <= 253 and
                    re.match(r'^(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+chatgpt\.site$', host))
    except (AttributeError, TypeError, ValueError):
        return False


def _text(value, limit=120):
    """Return bounded, nonempty Unicode text from game-owned display strings."""
    if value is None:
        return ''
    try:
        if isinstance(value, bytes):
            value = value.decode('utf-8', 'replace')
        elif not isinstance(value, type('')):
            value = type('')(value)
        value = value.strip()
        return value[:limit]
    except (TypeError, ValueError, UnicodeError):
        return ''


def _integer(value, default=None):
    try:
        return int(value) if not isinstance(value, bool) else default
    except (ValueError, TypeError, OverflowError):
        return default


def _unique_pairs(pairs):
    document = {}
    for key, value in pairs:
        if key in document:
            raise ConfigError('duplicate_fields')
        document[key] = value
    return document


def _game_roots(value, xml=False):
    """Accept only a proven game root; do not infer it from arbitrary paths."""
    paths = []
    if isinstance(value, bytes):
        for enc in ('utf-8', sys.getfilesystemencoding() or 'utf-8'):
            try:
                paths.append(value.decode(enc))
            except (UnicodeError, LookupError):
                pass
    else:
        paths.append(value)
    roots = set()
    for path in paths:
        if not path or not isinstance(path, type('')) or '\x00' in path or not os.path.isabs(path):
            continue
        if xml and (os.path.basename(path).lower() != 'paths.xml' or not os.path.isfile(path)):
            continue
        candidates = (os.path.dirname(path),) if xml else (path, os.path.dirname(path))
        for candidate in candidates:
            if os.path.isfile(os.path.join(candidate, 'paths.xml')) and os.path.isdir(os.path.join(candidate, 'mods')):
                roots.add(os.path.normcase(os.path.realpath(candidate)))
    return roots


def config_path(resmgr=None, cwd=None):
    """Resolve only the physical installation's mods/configs directory."""
    if resmgr is None:
        import ResMgr
        resmgr = ResMgr
    try:
        resolver = getattr(resmgr, 'resolveToAbsolutePath', None)
        roots = _game_roots(resolver('../paths.xml'), xml=True) if callable(resolver) else set()
        if len(roots) == 1:
            return os.path.join(roots.pop(), 'mods', 'configs', CONFIG_FILE)
        if len(roots) > 1:
            return None
    except Exception:
        pass
    roots = set()
    try:
        getter = getattr(resmgr, 'appDirectory', None)
        if callable(getter):
            roots.update(_game_roots(getter()))
    except Exception:
        pass
    if cwd is None:
        try:
            cwd = getattr(os, 'getcwdu', os.getcwd)()
        except Exception:
            cwd = None
    roots.update(_game_roots(cwd))
    if len(roots) != 1:
        return None
    return os.path.join(roots.pop(), 'mods', 'configs', CONFIG_FILE)


def parse_config(raw):
    """Parse the complete external config without supplying sync defaults."""
    if len(raw) > MAX_CONFIG_BYTES:
        raise ConfigError('config_too_large')
    if isinstance(raw, bytes):
        raw = raw.decode('utf-8-sig')
    return _validate_config(json.loads(raw, object_pairs_hook=_unique_pairs))


def _valid_label(value):
    return (isinstance(value, type('')) and len(value) <= 80 and
            value == value.strip() and
            not re.search(r'[\x00-\x1f\x7f-\x9f]', value))


def _validate_config(value):
    if not isinstance(value, dict) or set(value) - _VALID_FIELDS:
        raise ConfigError('unexpected_fields')
    if _VALID_FIELDS - set(value):
        raise ConfigError('missing_fields')
    if any(type(value[key]) is not bool for key in
           ('enabled', 'include_crew', 'include_missions', 'mission_diagnostics')):
        raise ConfigError('boolean_fields_invalid')
    interval = value['interval_seconds']
    if type(interval) is not int or not 30 <= interval <= 600:
        raise ConfigError('interval_invalid')
    if value['region'] not in ('EU', 'NA', 'ASIA'):
        raise ConfigError('region_invalid')
    enabled = value['enabled']
    label = value['display_name']
    if not _valid_label(label) or (enabled and not label):
        raise ConfigError('display_name_invalid')
    players = value['allowed_players']
    if not isinstance(players, list) or any(not _valid_label(name) or not name for name in players):
        raise ConfigError('players_list_invalid')
    if len({name.lower() for name in players}) != len(players):
        raise ConfigError('players_list_invalid')
    if enabled and not players:
        raise ConfigError('players_list_empty')
    device = value['device_token']
    gateway = value['sites_access_token']
    endpoint = value['endpoint_url']
    if not isinstance(device, type('')) or not isinstance(gateway, type('')):
        raise ConfigError('token_fields_invalid')
    if not isinstance(endpoint, type('')):
        raise ConfigError('endpoint_url_invalid')
    if (enabled or endpoint) and not _valid_sync_endpoint(endpoint):
        raise ConfigError('endpoint_url_invalid')
    if ((enabled or device) and not re.match(r'\Awgs_[a-f0-9]{64}\Z', device) or
            (enabled or gateway) and not re.match(r'\A[A-Za-z0-9._~+/=-]{12,4096}\Z', gateway)):
        raise ConfigError('tokens_missing_or_invalid')
    return value


def load_config(path):
    if not path:
        raise ConfigError('game_root_ambiguous')
    with open(path, 'rb') as handle:
        raw = handle.read(MAX_CONFIG_BYTES + 1)
    return parse_config(raw)


MAX_ARTWORK_BYTES = 128 * 1024
MAX_ARTWORK_PENDING_BYTES = 32 * 1024 * 1024
MAX_ARTWORK_PATHS = 24000
MAX_ARTWORK_BATCH_BYTES = 650000
MAX_ARTWORK_BATCH_COUNT = 24
_ARTWORK_PREFIXES = {
    'vehicle': 'gui/maps/icons/vehicle/',
    'item': 'gui/maps/icons/artefact/',
    'crew': 'gui/maps/icons/tankmen/',
}
_ARTWORK_FILENAME = re.compile(r'\A[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*\Z')


def _artwork_text(value):
    if isinstance(value, bytes):
        try:
            return value.decode('ascii')
        except UnicodeError:
            return ''
    return value if isinstance(value, type('')) else ''


def _artwork_attr(value, key):
    # Native UI accessors can be absent in older clients or unavailable while loading.
    try:
        return getattr(value, key, None)
    except Exception:
        return None


def _artwork_path(value, kind):
    path = _artwork_text(value)
    if path.startswith('img://'):
        path = path[6:]
    elif path.startswith('../maps/'):
        path = 'gui/' + path[3:]
    prefix = _ARTWORK_PREFIXES[kind]
    if not path.startswith(prefix) or len(path) > 240:
        return None
    tail = path[len(prefix):]
    if (not _ARTWORK_FILENAME.match(tail) or
            any(part.startswith('.') for part in tail.split('/')) or
            not tail.lower().endswith(('.png', '.jpg', '.jpeg'))):
        return None
    return path


def vehicle_artwork_paths(vehicle):
    name = _artwork_text(_artwork_attr(vehicle, 'name')).replace(':', '-')
    fallback = 'gui/maps/icons/vehicle/' + name + '.png' if name else ''
    return (_artwork_attr(vehicle, 'icon'), fallback, _artwork_attr(vehicle, 'iconSmall'))


def item_artwork_paths(item):
    icon = _artwork_attr(item, 'icon')
    if _artwork_text(icon) and '/' not in _artwork_text(icon):
        icon = 'gui/maps/icons/artefact/' + _artwork_text(icon)
    descriptor = _artwork_attr(item, 'descriptor')
    icon_name = _artwork_text(_artwork_attr(descriptor, 'iconName'))
    fallback = 'gui/maps/icons/artefact/' + icon_name + '.png' if icon_name else ''
    return (icon, fallback)


def crew_artwork_paths(tankman):
    try:
        from gui.impl import backport
        icon = tankman.getExtensionLessIconWithSkin().replace('-', '_')
        resource = tankman.bigIconDynAccessorWithSkin().dyn(icon)
        return (backport.image(resource()),)
    except Exception:
        return ()


def _static_icon_name(value):
    name = _artwork_text(value).replace('\\', '/').rsplit('/', 1)[-1]
    name = re.sub(r'\.(?:png|jpe?g)\Z', '', name, flags=re.IGNORECASE)
    if re.match(r'\A[A-Za-z0-9][A-Za-z0-9_.-]{0,179}\Z', name) and '..' not in name:
        return name
    return None


def static_item_icon(item):
    descriptor = _artwork_attr(item, 'descriptor')
    name = _static_icon_name(_artwork_attr(descriptor, 'iconName'))
    if not name:
        name = _static_icon_name(_artwork_attr(item, 'icon'))
    return 'item:' + name if name else None


def static_crew_icon(tankman):
    skin = _artwork_attr(tankman, 'skin')
    if skin is not None:
        try:
            name = _static_icon_name(skin.getIconID())
            if name:
                return 'crew:crewSkins/' + name
        except Exception:
            pass
    name = _static_icon_name(_artwork_attr(tankman, 'icon'))
    if name:
        return 'crew:' + name
    for path in crew_artwork_paths(tankman):
        name = _static_icon_name(path)
        if name:
            prefix = 'crew:crewSkins/' if '/crewSkins/' in _artwork_text(path) else 'crew:'
            return prefix + name
    return None


def _read_game_artwork(path):
    import ResMgr
    native_path = path.encode('ascii') if sys.version_info[0] == 2 else path
    section = ResMgr.openSection(native_path)
    return section.asBinary if section is not None else None


def _valid_artwork_bytes(data):
    if not isinstance(data, bytes) or len(data) > MAX_ARTWORK_BYTES:
        return False
    if data.startswith(b'\x89PNG\r\n\x1a\n'):
        return _valid_png(data)
    return _valid_jpeg(data)


def _artwork_dimensions(width, height):
    return 0 < width <= 4096 and 0 < height <= 4096


def _valid_png(data):
    if len(data) < 57 or data[8:16] != b'\x00\x00\x00\x0dIHDR':
        return False
    if not _artwork_dimensions(*struct.unpack_from('!II', data, 16)):
        return False
    offset = 33
    has_data = False
    while offset + 12 <= len(data):
        size, kind = struct.unpack_from('!I4s', data, offset)
        offset += size + 12
        if offset > len(data):
            return False
        if kind == b'IDAT' and size:
            has_data = True
        if kind == b'IEND':
            return has_data and size == 0 and offset == len(data)
    return False


def _valid_jpeg(data):
    end = len(data) - 2
    if end < 12 or not data.startswith(b'\xff\xd8') or not data.endswith(b'\xff\xd9'):
        return False
    offset = 2
    has_frame = False
    while offset + 4 <= end:
        if data[offset:offset + 1] != b'\xff':
            return False
        offset += 1
        while offset < end and data[offset:offset + 1] == b'\xff':
            offset += 1
        if offset + 3 > end:
            return False
        marker = data[offset:offset + 1]
        offset += 1
        size = struct.unpack_from('!H', data, offset)[0]
        if size < 2 or offset + size > end:
            return False
        if marker == b'\xda':
            return has_frame and size >= 6 and offset + size < end
        if marker in (b'\xc0', b'\xc1', b'\xc2'):
            if size < 8 or not _artwork_dimensions(*struct.unpack_from('!HH', data, offset + 3)):
                return False
            has_frame = True
        offset += size
    return False


class ArtworkStore(object):
    """Session-local resource cache; game thread alone reads virtual archive files."""
    def __init__(self, reader=None):
        self._reader = reader or _read_game_artwork
        self._path_ids = {}
        self._pending = {}
        self._uploaded = set()
        self._pending_bytes = 0
        self._lock = threading.Lock()

    def resolve(self, paths):
        for path in paths:
            if path in self._path_ids:
                image_id = self._path_ids[path]
                if image_id is None:
                    continue
                with self._lock:
                    if image_id in self._pending or image_id in self._uploaded:
                        return image_id
            elif len(self._path_ids) >= MAX_ARTWORK_PATHS:
                return None
            with self._lock:
                if self._pending_bytes >= MAX_ARTWORK_PENDING_BYTES:
                    return None
            try:
                data = self._reader(path)
            except Exception:
                data = None
            if not _valid_artwork_bytes(data):
                self._path_ids[path] = None
                continue
            image_id = hashlib.sha256(data).hexdigest()
            with self._lock:
                if image_id not in self._uploaded and image_id not in self._pending:
                    if self._pending_bytes + len(data) > MAX_ARTWORK_PENDING_BYTES:
                        return None
                    self._pending[image_id] = data
                    self._pending_bytes += len(data)
            self._path_ids[path] = image_id
            return image_id
        return None

    def pending(self, image_ids):
        with self._lock:
            return [(image_id, self._pending[image_id]) for image_id in sorted(image_ids)
                    if image_id in self._pending]

    def has_pending(self, image_ids):
        with self._lock:
            return any(image_id in self._pending for image_id in image_ids)

    def uploaded(self, image_ids):
        with self._lock:
            for image_id in image_ids:
                data = self._pending.pop(image_id, None)
                if data is not None:
                    self._pending_bytes -= len(data)
                self._uploaded.add(image_id)

    def prune(self, image_ids):
        with self._lock:
            for image_id in set(self._pending).difference(image_ids):
                self._pending_bytes -= len(self._pending.pop(image_id))


class ArtworkCapture(object):
    """Resolve bounded slices in the lobby instead of reading every image at once."""
    def __init__(self, store):
        self._store = store
        self._targets = []
        self._remaining = None
        self.player = None
        self.image_ids = set()
        self.requested = dict.fromkeys(_ARTWORK_PREFIXES, 0)
        self.resolved = dict.fromkeys(_ARTWORK_PREFIXES, 0)

    def add(self, row, kind, candidates):
        self.requested[kind] += 1
        paths = []
        for candidate in candidates:
            path = _artwork_path(candidate, kind)
            if path and path not in paths:
                paths.append(path)
        if paths:
            self._targets.append((row, kind, paths))

    def drop_references(self):
        for row, _, _ in self._targets:
            row.pop('imageId', None)
        self.image_ids.clear()

    def step(self, clock=time.time):
        if self._remaining is None:
            self._remaining = iter(self._targets)
        deadline = clock() + 0.008
        for _ in range(24):
            target = next(self._remaining, None)
            if target is None:
                return True
            row, kind, paths = target
            image_id = self._store.resolve(paths)
            if image_id:
                row['imageId'] = image_id
                self.image_ids.add(image_id)
                self.resolved[kind] += 1
            if clock() >= deadline:
                break
        return False


def artwork_batches(images):
    start, end = b'{"images":[', b']}'
    records, image_ids = [], []
    size = len(start) + len(end)
    for image_id, data in images:
        encoded = base64.b64encode(data).decode('ascii')
        record = json.dumps({'id': image_id, 'data': encoded}, ensure_ascii=True,
                            separators=(',', ':')).encode('ascii')
        if records and (len(records) >= MAX_ARTWORK_BATCH_COUNT or
                        size + len(record) + 1 > MAX_ARTWORK_BATCH_BYTES):
            yield image_ids, start + b','.join(records) + end
            records, image_ids = [], []
            size = len(start) + len(end)
        size += len(record) + bool(records)
        records.append(record)
        image_ids.append(image_id)
    if records:
        yield image_ids, start + b','.join(records) + end


def _item_name(item):
    for key in ('userName', 'shortUserName', 'name'):
        name = _text(getattr(item, key, None))
        if name:
            return name
    raise ValueError('Installed item lacks a display name')


def installed_items(collector, category, with_count=False, artwork=None):
    """Read the active setup, preserving the actual in-game slot number."""
    if collector is None or getattr(collector, 'installed', None) is None:
        raise ValueError('Vehicle equipment collection is not ready')
    output = []
    for index, item in enumerate(collector.installed):
        if not item or not getattr(item, 'intCD', None):
            continue
        if index >= 32:
            raise ValueError('Equipment slot outside supported range')
        row = {'name': _item_name(item), 'slot': index + 1, 'category': category}
        if category == 'equipment':
            if bool(getattr(item, 'isModernized', False)):
                row['detail'] = 'Experimental equipment'
            elif bool(getattr(item, 'isDeluxe', False)):
                row['detail'] = 'Bond equipment'
            elif bool(getattr(item, 'isTrophy', False)):
                row['detail'] = 'Bounty equipment'
            else:
                row['detail'] = 'Standard equipment'
            level = _integer(getattr(item, 'level', None))
            if level is not None and 1 <= level <= 10:
                row['tier'] = level
        if with_count:
            count = _integer(getattr(item, 'count', None))
            if count is None or not 0 <= count <= 999999:
                raise ValueError('Invalid shell count')
            row['quantity'] = count
        icon_key = static_item_icon(item)
        if icon_key:
            row['iconKey'] = icon_key
        output.append(row)
    return output


def _mod_name(action):
    try:
        from gui.impl import backport
        loc = action.getLocNameRes()
        name = _text(backport.text(loc()))
        if name:
            return name
    except Exception:
        pass
    name = _text(action.getTechName())
    if not name:
        raise ValueError('Field modification has no name')
    return name


def field_modifications(vehicle):
    """Include acquired progression choices and the selected side of each pair."""
    progression = getattr(vehicle, 'postProgression', None)
    if progression is None or not progression.isExists():
        return []
    entries = []
    for step in progression.iterUnorderedSteps():
        if not step.isReceived():
            continue
        action = step.action
        if action.getActiveID() is None:
            continue
        if action.isMultiAction():
            action = action.getPurchasedModification()
            if action is None:
                continue
        level = _integer(step.getLevel())
        row = {'name': _mod_name(action), 'category': 'field_modification'}
        if level is not None:
            row['detail'] = 'Field modification level %d' % level
        entries.append(row)
    if len(entries) > 30:
        raise ValueError('Too many field modifications')
    return entries


def _crew_member(tankman, vehicle=None, skill_catalog=None):
    """Copy current character details, never native member/inventory IDs."""
    name = _text(getattr(tankman, 'fullUserName', None))
    role = _text(getattr(tankman, 'roleUserName', None), 80)
    if not name or not role:
        raise ValueError('Crew member has incomplete identity')
    member = {'name': name, 'role': role, 'perks': []}
    qualification = _integer(getattr(tankman, 'roleLevel', None))
    if qualification is not None and 0 <= qualification <= 100:
        member['qualification'] = qualification
    for skill in getattr(tankman, 'skills', ()):
        label = _text(getattr(skill, 'userName', None), 100) or _text(getattr(skill, 'name', None), 100)
        if label:
            member['perks'].append(label)
    if len(member['perks']) > 20:
        raise ValueError('Too many crew skills')
    icon_key = static_crew_icon(tankman)
    if icon_key:
        member['iconKey'] = icon_key
    try:
        from gui.mods.grz_hangar_crew import collect_crew_skills
        member.update(collect_crew_skills(tankman, vehicle,
                                        {} if skill_catalog is None else skill_catalog))
    except Exception:
        pass
    return member


def installed_crew(vehicle, artwork=None, skill_catalog=None):
    entries = []
    for _, tankman in getattr(vehicle, 'crew', ()):
        if tankman is not None:
            entries.append(_crew_member(tankman, vehicle, skill_catalog))
    if len(entries) > 10:
        raise ValueError('Too many crew members')
    return entries


def _remembered_member_location(tankman, native_data, items, owned_rows):
    """Resolve actual assignment; training specialization is not a location."""
    unknown = {'kind': 'unknown'}
    try:
        assigned = native_data.vehicle
        if type(assigned) not in _INTEGER_TYPES:
            return unknown
        if assigned > 0:
            vehicle = items.getVehicle(assigned)
            if vehicle is None or vehicle.invID != assigned:
                return unknown
            compact = vehicle.intCD
            if type(compact) not in _INTEGER_TYPES or compact not in owned_rows:
                return unknown
            return {'kind': 'vehicle', 'vehicleId': compact,
                    'vehicleName': owned_rows[compact]['name']}
        from constants import VEHICLE_NO_INV_ID
        if (assigned == VEHICLE_NO_INV_ID and tankman.vehicleInvID == VEHICLE_NO_INV_ID and
                tankman.isInTank is False):
            return {'kind': 'barracks'}
    except Exception:
        pass
    return unknown


def _same_current_crew(vehicle, remembered):
    current = {}
    try:
        for slot, tankman in vehicle.crew:
            if type(slot) not in _INTEGER_TYPES or slot in current:
                return False
            identifier = None if tankman is None else tankman.invID
            if identifier is not None and (type(identifier) not in _INTEGER_TYPES or identifier <= 0):
                return False
            current[slot] = identifier
    except Exception:
        return False
    return current == dict(enumerate(remembered))


def _add_remembered_crew(snapshot, vehicles, items):
    """Export the game's previous-battle roster separately from installed crew.

    Native member IDs are used only for local resolution and slot comparisons.
    Profiles/training are today's readings, not historical skill snapshots.
    """
    owned_rows = {row['id']: row for row in snapshot['vehicles']}
    catalog = {row['id']: row for row in snapshot.get('crewSkillCatalog', [])}
    try:
        synced = items.inventory.isSynced()
    except Exception:
        synced = False
    for vehicle in vehicles:
        try:
            row = owned_rows.get(vehicle.intCD)
        except Exception:
            continue
        if row is None:
            continue
        row['lastCrewSource'] = 'previous_battle'
        row['lastCrewStatus'] = 'unavailable'
        if not synced:
            continue
        try:
            remembered = vehicle.lastCrew
            if remembered is None:
                row.update(lastCrewStatus='none', lastCrewExpectedCount=0, lastCrewMissingCount=0)
                continue
            if not isinstance(remembered, (tuple, list)) or len(remembered) > 10:
                continue
            if any(value is not None and (type(value) not in _INTEGER_TYPES or
                                         not 0 < value < 2 ** 63) for value in remembered):
                continue
            if not remembered or not any(value is not None for value in remembered):
                row.update(lastCrewStatus='none', lastCrewExpectedCount=0, lastCrewMissingCount=0)
                continue
            expected = len(remembered)
            row['lastCrewExpectedCount'] = expected
            if _same_current_crew(vehicle, remembered):
                row.update(lastCrewStatus='same_as_current', lastCrewMissingCount=0)
                continue
            members = []
            seen = set()
            for slot, identifier in enumerate(remembered):
                if identifier is None or identifier in seen:
                    continue
                seen.add(identifier)
                try:
                    # getTankman() otherwise falls back to restorable dismissed
                    # characters. Require an active own-inventory record first.
                    native_data = items.inventory.getTankmanData(identifier)
                    if native_data is None:
                        continue
                    tankman = items.getTankman(identifier)
                    if tankman is None or tankman.invID != identifier or tankman.isDismissed is not False:
                        continue
                    member = _crew_member(tankman, None, catalog)
                    member['slot'] = slot
                    member['location'] = _remembered_member_location(tankman, native_data, items, owned_rows)
                    members.append(member)
                except Exception:
                    # Never log exception text: it may contain local identifiers.
                    continue
            missing = expected - len(members)
            row.update(lastCrew=members, lastCrewMissingCount=missing,
                       lastCrewStatus='partial' if missing else 'available')
        except Exception:
            continue
    if catalog:
        snapshot['crewSkillCatalog'] = [catalog[key] for key in sorted(catalog)]


def _role_text(value):
    """Copy only resolved, bounded native role display text."""
    if not isinstance(value, (type(''), bytes)):
        return None
    try:
        if isinstance(value, bytes) and not isinstance(value, type('')):
            value = value.decode('utf-8', 'replace')
        value = value[:16384].replace('&zwnbsp;', '')
        try:
            from HTMLParser import HTMLParser
            value = HTMLParser().unescape(value)
        except ImportError:
            from html import unescape
            value = unescape(value)
        value = re.sub(r'<[^>]*>', ' ', value)
        value = re.sub(r'[\x00-\x1f\x7f-\x9f\ufeff\u200b\u2060]', ' ', value)
        value = ' '.join(value.split())
        if (not value or re.search(r'#[A-Za-z][A-Za-z0-9_]*:', value) or
                re.search(r'%\([^)]+\)[A-Za-z]|%[sd]|\{[^{}]+\}', value)):
            return None
        return value[:240]
    except Exception:
        return None


def _vehicle_role(vehicle):
    """Export the native role label without inferring a role from vehicle data."""
    try:
        key = vehicle.roleLabel
        if not isinstance(key, (type(''), bytes)):
            return None
        if isinstance(key, bytes) and not isinstance(key, type('')):
            key = key.decode('utf-8', 'strict')
        if not re.match(r'\Arole_[A-Za-z0-9_]{1,64}\Z', key):
            return None
    except Exception:
        return None
    role = {'key': key, 'name': None, 'groupName': None}
    try:
        # The native formatter supplies the groupName placeholder used by some
        # role names. A raw localization key alone is not a display string.
        from gui.shared.formatters import getRoleText
        role['name'] = _role_text(getRoleText(key))
    except Exception:
        pass
    try:
        from gui.impl import backport
        from gui.impl.gen import R
        role['groupName'] = _role_text(backport.text(
            R.strings.menu.roleExp.roleGroupName.dyn(key)()))
    except Exception:
        pass
    return role


def normalize_vehicle(vehicle, include_crew, artwork=None, skill_catalog=None):
    kind = _CLASSES.get(getattr(vehicle, 'type', None))
    tier = _integer(getattr(vehicle, 'level', None))
    compact = _integer(getattr(vehicle, 'intCD', None))
    if not kind or tier is None or not 1 <= tier <= 11 or compact is None or compact <= 0:
        raise ValueError('Unsupported vehicle identification')
    nation = _text(getattr(vehicle, 'nationName', None), 60)
    name = _text(getattr(vehicle, 'shortUserName', None)) or _text(getattr(vehicle, 'userName', None))
    if not name or not nation:
        raise ValueError('Vehicle lacks a display name or nation')
    row = {
        'id': compact, 'name': name, 'tier': tier,
        'nation': _NATIONS.get(nation, nation), 'type': kind,
        'premium': bool(getattr(vehicle, 'isPremium', False)),
        'elite': bool(getattr(vehicle, 'isElite', False)),
        'equipment': installed_items(vehicle.optDevices, 'equipment', artwork=artwork),
        'consumables': installed_items(vehicle.consumables, 'consumable', artwork=artwork),
        'ammunition': installed_items(vehicle.shells, 'ammunition', with_count=True),
        'directives': installed_items(vehicle.battleBoosters, 'directive', artwork=artwork),
        'fieldMods': field_modifications(vehicle),
        'crew': installed_crew(vehicle, artwork, skill_catalog) if include_crew else [],
    }
    role = _vehicle_role(vehicle)
    if role is not None:
        row['role'] = role
    native_name = _text(getattr(vehicle, 'name', None), 160).split(':')[-1]
    if re.match(r'\A[A-Za-z0-9_-]{1,120}\Z', native_name):
        row['iconKey'] = native_name
    for field, maximum in (('equipment', 12), ('consumables', 12), ('ammunition', 20), ('directives', 12)):
        if len(row[field]) > maximum:
            raise ValueError('Vehicle exceeds schema %s limit' % field)
    return row


def make_snapshot(display_name, vehicles, region, include_crew, artwork=None):
    if not display_name or not vehicles or len(vehicles) > MAX_VEHICLES:
        raise ValueError('No complete garage snapshot is available')
    skill_catalog = {}
    if include_crew:
        try:
            from gui.mods.grz_hangar_crew import prime_crew_catalog
            prime_crew_catalog(skill_catalog)
        except Exception:
            pass
    rows = [normalize_vehicle(vehicle, include_crew, artwork, skill_catalog) for vehicle in vehicles]
    rows.sort(key=lambda v: (v['tier'], v['name']), reverse=True)
    ids = [row['id'] for row in rows]
    if len(ids) != len(set(ids)):
        raise ValueError('Duplicate garage vehicle identifier')
    snapshot = {
        'schemaVersion': 1,
        'capturedAt': datetime.datetime.utcnow().replace(microsecond=0).isoformat() + 'Z',
        'player': {'name': display_name, 'region': region},
        'vehicles': rows,
    }
    if skill_catalog:
        snapshot['crewSkillCatalog'] = [skill_catalog[key] for key in sorted(skill_catalog)]
    return snapshot


def _inventory_vehicles(items):
    """Enumerate account inventory slots independently of any carousel view."""
    inventory = items.inventory
    if not inventory.isSynced():
        return []
    vehicles = []
    for inv_id in inventory.getInvIDsIterator():
        if len(vehicles) >= MAX_VEHICLES:
            raise ValueError('Inventory exceeds snapshot limit')
        vehicle = items.getVehicle(inv_id)
        if vehicle is None:
            raise ValueError('Owned vehicle details are unavailable')
        vehicles.append(vehicle)
    return vehicles


def _add_stats_creation_dates(snapshot, items, now=None):
    """Copy only existing own-account dossier dates from the synced GUI cache."""
    try:
        requester = items.dossiers
        if not requester.isSynced():
            return
        latest = (time.time() if now is None else now) + 300
    except Exception:
        return
    for row in snapshot['vehicles']:
        try:
            # The GUI factory creates a new empty dossier for an absent raw
            # descriptor. Its default creationTime must never become a date.
            if not requester.getVehicleDossier(row['id']):
                continue
            dossier = items.getVehicleDossier(row['id'])
            if (dossier is None or not dossier.isCurrentUser() or
                    dossier.getCompactDescriptor() != row['id']):
                continue
            stats = dossier.getGlobalStats()
            created = stats.getCreationTime()
            last_battle = stats.getLastBattleTime()
            # A native recorded battle proves this is not an empty dossier.
            if (type(created) in _INTEGER_TYPES and 0 < created <= latest and
                    type(last_battle) in _INTEGER_TYPES and 0 < last_battle <= latest):
                row['statsCreatedAt'] = created
        except Exception:
            # Optional history metadata cannot block an otherwise valid garage.
            continue


def _parse_playlist(playlist_id, raw):
    playlist_id = _text(playlist_id, 65)
    if not re.match(r'\A[A-Za-z0-9_-]{1,64}\Z', playlist_id):
        raise ValueError('Invalid playlist identifier')
    if not isinstance(raw, (type(''), bytes)) or len(raw) > MAX_PLAYLIST_BYTES:
        raise ValueError('Invalid playlist data')
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError('Invalid playlist data')
    name = data.get('title')
    members = data.get('list')
    if not isinstance(name, type('')) or not isinstance(members, list) or len(members) > MAX_VEHICLES:
        raise ValueError('Invalid playlist fields')
    name = _text(re.sub(r'[\x00-\x1f\x7f-\x9f]', ' ', name))
    if not name:
        raise ValueError('Missing playlist name')
    vehicle_ids = []
    seen = set()
    for member in members:
        if type(member) not in _INTEGER_TYPES or not 0 < member <= 0xffffffff:
            raise ValueError('Invalid playlist vehicle identifier')
        if member not in seen:
            seen.add(member)
            vehicle_ids.append(member)
    return {'id': playlist_id, 'name': name, 'vehicleIds': vehicle_ids}


def _collect_playlists():
    """Read saved account playlists through the native client controller."""
    from helpers import dependency
    from skeletons.gui.game_control import IVehiclePlaylistsController
    controller = dependency.instance(IVehiclePlaylistsController)
    if controller is None or not controller.isEnabled:
        return None
    rows = []
    seen = set()
    skipped = 0
    for index, (playlist_id, raw) in enumerate(controller.iterPlaylists()):
        if index >= MAX_PLAYLISTS:
            raise ValueError('Playlist count exceeds snapshot limit')
        try:
            row = _parse_playlist(playlist_id, raw)
            if row['id'] in seen:
                raise ValueError('Duplicate playlist identifier')
        except (ValueError, TypeError):
            skipped += 1
            continue
        seen.add(row['id'])
        rows.append(row)
    LOG.debug('event=playlists_read count=%d skipped=%d', len(rows), skipped)
    return sorted(rows, key=lambda row: (row['name'].lower(), row['id'])) if rows or not skipped else None


def collect_game_snapshot(config, artwork=None):
    """Use only documented GUI inventory objects on WoT's main thread."""
    import BigWorld
    import BattleReplay
    player = BigWorld.player()
    if player is None or getattr(player, 'arena', None) is not None or BattleReplay.isPlaying():
        LOG.debug('event=capture_skipped reason=not_in_garage')
        return None
    name = getattr(player, 'name', None)
    if isinstance(name, bytes):
        try:
            name = name.decode('utf-8')
        except UnicodeError:
            name = None
    if not _valid_label(name) or not name:
        LOG.debug('event=capture_skipped reason=player_not_ready')
        return None
    nickname = name.lower()
    if not any(nickname == allowed.lower() for allowed in config['allowed_players']):
        LOG.warning('event=capture_skipped reason=player_not_allowed')
        return None
    if artwork is not None:
        artwork.player = player
    from helpers import dependency
    from skeletons.gui.shared import IItemsCache
    cache = dependency.instance(IItemsCache)
    if cache is None:
        LOG.debug('event=capture_skipped reason=inventory_service_not_ready')
        return None
    vehicles = _inventory_vehicles(cache.items)
    if not vehicles:
        LOG.debug('event=capture_skipped reason=no_owned_vehicles_ready')
        return None
    snapshot = make_snapshot(config['display_name'], vehicles, config['region'],
                             config['include_crew'], artwork)
    if config['include_crew']:
        _add_remembered_crew(snapshot, vehicles, cache.items)
    _add_stats_creation_dates(snapshot, cache.items)
    from gui.mods.grz_hangar_stats import collect_session_stats
    snapshot['sessionStats'] = collect_session_stats([vehicle['id'] for vehicle in snapshot['vehicles']])
    try:
        playlists = _collect_playlists()
        if playlists is not None:
            snapshot['playlists'] = playlists
    except Exception as error:
        LOG.warning('event=playlists_read_failed error_type=%s', _safe_exception_type(error))
    if config['include_missions']:
        try:
            snapshot['battlePass'] = collect_battle_pass()
        except Exception as error:
            LOG.warning('event=battle_pass_capture_failed error_type=%s', _safe_exception_type(error))
        try:
            missions = collect_missions()
            if missions is not None:
                snapshot['missions'] = missions
        except Exception as error:
            LOG.warning('event=mission_capture_failed error_type=%s', _safe_exception_type(error))
    return snapshot


def collect_battle_pass():
    """Use the same explicit mission opt-in; never inspect account credentials."""
    from gui.mods.grz_hangar_battle_pass import collect_battle_pass as read
    return read()


def _mission_text(value):
    """Read only game display strings. Never stringify a container or object."""
    if not isinstance(value, (bytes, type(''))):
        return ''
    value = _text(value, 8192)
    value = re.sub(r'<[^<>]*>', ' ', value)
    value = re.sub(r'[\x00-\x1f\x7f]+', ' ', value)
    value = ' '.join(value.split())
    if value.startswith('#') and not any(c.isspace() for c in value):
        return ''
    return value[:1400]


def _mission_call(target, name, *args, **kwargs):
    method = getattr(target, name, None)
    return method(*args, **kwargs) if callable(method) else None


def _mission_number(value):
    return value if type(value) in _INTEGER_TYPES and 0 <= value <= 10 ** 12 else None


def _mission_rewards(quest, **kwargs):
    result = []
    for bonus in (_mission_call(quest, 'getBonuses', **kwargs) or [])[:32]:
        if _mission_call(bonus, 'isShowInGUI') is False:
            continue
        for value in (_mission_call(bonus, 'formattedList') or [])[:16]:
            label = _mission_text(value)
            if label:
                result.append(label)
    return result[:48]


def _condition_node(node, condition_api, budget, depth=0):
    budget[0] -= 1
    if depth >= 6 or budget[0] < 0:
        return None
    if isinstance(node, (condition_api.AndGroup, condition_api.OrGroup)):
        children = []
        for item in node.items:
            if budget[0] <= 0:
                break
            child = _condition_node(item, condition_api, budget, depth + 1)
            if child is not None:
                children.append(child)
        if not children:
            return None
        return {'operator': 'any' if isinstance(node, condition_api.OrGroup) else 'all',
                'negated': bool(node.isNegative), 'conditions': children}
    if _mission_call(node, 'isHidden'):
        return None
    label = (_mission_text(_mission_call(node, 'getCustomDescription')) or
             _mission_text(_mission_call(node, 'getCustomTitle')) or
             _mission_text(_mission_call(node, 'getUserString')))
    result = {'text': label}
    if isinstance(node, condition_api.Cumulativable):
        groups = _mission_call(node, 'getProgressPerGroup')
        # Use the ungrouped progress only. Group keys can contain vehicle IDs.
        if groups and None in groups:
            current, total, _, _ = groups[None]
            current, total = _mission_number(current), _mission_number(total)
            if current is not None and total:
                result['progress'] = {'current': current, 'target': total}
    return result if label or 'progress' in result else None


def _quest_requirements(quest):
    from gui.server_events import conditions
    groups = []
    budget = [48]
    for scope in ('vehicleReqs', 'preBattleCond', 'bonusCond', 'postBattleCond'):
        parser = getattr(quest, scope, None)
        root = _mission_call(parser, 'getConditions')
        if root is not None:
            requirement = None
            if scope in ('bonusCond', 'postBattleCond'):
                from gui.mods.grz_hangar_mission_metadata import quest_conditions
                model = quest_conditions(quest, scope)
                if model is not None:
                    native_budget = [budget[0]]
                    requirement = _packed_condition(model, native_budget)
                    if requirement is not None:
                        budget[0] = native_budget[0]
            if requirement is None:
                requirement = _condition_node(root, conditions, budget)
            if requirement is not None:
                groups.append({'scope': scope, 'requirement': requirement})
    return groups


def _personal_ui_requirements(quest):
    if not _mission_call(quest, 'getConditionsConfig'):
        return {}
    from gui.server_events.personal_progress.formatters import PMCardConditionsFormatter
    formatter = PMCardConditionsFormatter(quest)
    result = {}
    for scope, is_main in (('primary', True), ('secondary', False)):
        groups = []
        for item in formatter.bodyFormat(is_main)[:48]:
            info = item.get('initData') or {}
            label = (_mission_text(info.get('description')) or
                     _mission_text(info.get('title')))
            if not label:
                continue
            requirement = {'text': label}
            from gui.mods.grz_hangar_mission_metadata import condition_icon
            icon_key = condition_icon(info)
            if icon_key:
                requirement['iconKey'] = icon_key
            if info.get('isInOrGroup'):
                requirement['alternative'] = True
            progress = item.get('progressData') or {}
            current = _mission_number(progress.get('current'))
            target = _mission_number(progress.get('goal'))
            if current is not None and target:
                requirement['progress'] = {'current': current, 'target': target}
            groups.append({'scope': 'missionCondition', 'requirement': requirement})
        if groups:
            result[scope] = {'scope': scope, 'text': '', 'groups': groups}
    return result


def _packed_condition(model, budget, depth=0):
    budget[0] -= 1
    if depth >= 6 or budget[0] < 0:
        return None
    items = _mission_call(model, 'getItems')
    if items is not None:
        children = []
        for item in items:
            if budget[0] <= 0:
                break
            condition = _packed_condition(item, budget, depth + 1)
            if condition is not None:
                children.append(condition)
        if not children:
            return None
        kind = model.getConditionType()
        return {'operator': 'any' if kind == 'or' else 'all',
                'negated': kind == 'not', 'conditions': children}
    label = (_mission_text(model.getDescrData()) or _mission_text(model.getTitleData()))
    result = {'text': label}
    current = _mission_number(_mission_call(model, 'getCurrent'))
    target = _mission_number(_mission_call(model, 'getTotal'))
    if current is not None and target:
        result['progress'] = {'current': current, 'target': target}
    from gui.mods.grz_hangar_mission_metadata import condition_icon
    icon_key = condition_icon(model)
    if icon_key:
        result['iconKey'] = icon_key
    return result if label or 'progress' in result else None


def _crucible_post_battle_requirement(quest):
    from gui.impl.gen.view_models.common.missions.conditions.condition_group_model import ConditionGroupModel
    from gui.shared.missions.packers.conditions import ChallengePostBattleConditionPacker
    model = ConditionGroupModel()
    ChallengePostBattleConditionPacker().pack(quest, model)
    return _packed_condition(model, [48])


def _quest_row(quest, personal=False, cache=None, crucible=False, category=None):
    quest_id = _mission_call(quest, 'getID')
    if _mission_number(quest_id) is not None:
        quest_id = type('')(quest_id)
    quest_id = _mission_text(quest_id)[:160]
    if not quest_id:
        raise ValueError('missing_mission_id')
    row = {'id': quest_id, 'title': _mission_text(_mission_call(quest, 'getUserName')),
           'description': _mission_text(_mission_call(
               quest, 'getUserDescription' if personal else 'getDescription')),
           'completed': bool(quest.isCompleted()), 'requirements': [],
           'rewards': [], 'missing': []}
    if not row['description']:
        row['missing'].append('description')
    available = _mission_call(quest, 'isAvailable')
    if available is not None:
        row['available'] = bool(getattr(available, 'isValid', available))

    try:
        if personal:
            try:
                formatted = _personal_ui_requirements(quest)
            except Exception:
                formatted = {}
                row['missing'].append('requirements_error')
            # Older missions may still expose the linked main and additional quests.
            for key, getter in (('primary', 'getMainQuestID'), ('secondary', 'getAddQuestID')):
                if key in formatted:
                    row['requirements'].append(formatted[key])
                    continue
                linked_id = _mission_call(quest, getter)
                linked = cache.getQuestByID(linked_id) if linked_id else None
                if linked is None:
                    if linked_id:
                        row['missing'].append(key + '_source')
                    continue
                requirements = _quest_requirements(linked)
                description = (_mission_text(_mission_call(linked, 'getConditionsDescription')) or
                               _mission_text(_mission_call(linked, 'getDescription')))
                if requirements or description:
                    row['requirements'].append({'scope': key, 'text': description,
                                                'groups': requirements})
                else:
                    row['missing'].append(key + '_fields')
            minimum = _mission_number(_mission_call(quest, 'getVehMinLevel'))
            maximum = _mission_number(_mission_call(quest, 'getVehMaxLevel'))
            if minimum and maximum and minimum <= maximum <= 11:
                row['vehicleTiers'] = {'min': minimum, 'max': maximum}
        else:
            row['requirements'] = _quest_requirements(quest)
            row['conditionText'] = _mission_text(_mission_call(quest, 'getConditionsDescription'))
            if crucible:
                post_battle = _crucible_post_battle_requirement(quest)
                if post_battle is not None:
                    row['requirements'] = [group for group in row['requirements']
                                           if group['scope'] != 'postBattleCond']
                    row['requirements'].append({'scope': 'postBattleCond',
                                                'requirement': post_battle})
    except Exception:
        if 'requirements_error' not in row['missing']:
            row['missing'].append('requirements_error')
    if not row['requirements'] and not row.get('conditionText'):
        row['missing'].append('requirements')

    try:
        row['rewards'] = _mission_rewards(quest)
    except Exception:
        row['missing'].append('rewards_error')
    if not row['rewards']:
        row['missing'].append('rewards')
    try:
        from gui.mods.grz_hangar_mission_metadata import reward_items
        details = reward_items(quest, category=category, personal=personal, crucible=crucible)
        if details:
            row['rewardItems'] = details
    except Exception:
        pass
    return row


def _mission_bucket(loader):
    rows = []
    failed = 0
    try:
        for quest, normalize in loader():
            if len(rows) + failed == MAX_MISSIONS:
                return {'status': 'partial', 'items': rows, 'failures': failed, 'truncated': True}
            try:
                rows.append(normalize(quest))
            except Exception:
                failed += 1
    except MissionSourcePending:
        return {'status': 'pending', 'items': rows, 'failures': failed}
    except Exception as error:
        return {'status': 'partial' if rows else 'unavailable',
                'items': rows, 'failures': failed + 1,
                'errorType': _safe_exception_type(error)}
    status = 'partial' if failed or any(row['missing'] for row in rows) else 'ok'
    return {'status': status, 'items': rows, 'failures': failed}


def _ordinary_missions(cache, getter, bonus=None):
    quests = getattr(cache, getter)()
    if getter == 'getDailyEpicQuest':
        if quests is not None:
            yield quests, _daily_epic_row
        return
    for _, quest in sorted(quests.items(), key=lambda item: item[0]):
        if bonus is not None and bool(quest.isBonus()) != bonus:
            continue
        if getter == 'getPremiumQuests' and (
                quest.isHidden() or not (quest.isAvailable().isValid or quest.isCompleted())):
            continue
        category = {'getDailyQuests': 'daily_bonus' if bonus else 'daily',
                    'getPremiumQuests': 'premium', 'getWeeklyQuests': 'weekly'}.get(getter)
        yield quest, lambda quest, category=category: _quest_row(quest, category=category)


def _daily_epic_row(quest):
    row = _quest_row(quest, category='daily_epic')
    # The game's epic mission card uses the description as the objective.
    if 'requirements' in row['missing'] and row['description']:
        row['conditionText'] = row['description']
        row['missing'].remove('requirements')
    return row


def _personal_missions(cache):
    from personal_missions import PM_BRANCH
    personal = cache.getPersonalMissions()
    if personal is None or not personal.isQuestsProgressSynced():
        raise MissionSourcePending()
    branches = PM_BRANCH.ALL_NAMES
    operations = personal.getAllOperations(branches)
    campaigns = personal.getAllCampaigns(branches)

    def normalize(quest):
        row = _quest_row(quest, personal=True, cache=cache)
        row['active'] = bool(quest.isInProgress())
        campaign = campaigns.get(quest.getCampaignID())
        operation = operations.get(quest.getOperationID())
        row['campaign'] = _mission_text(_mission_call(campaign, 'getUserName'))
        row['operation'] = _mission_text(_mission_call(operation, 'getUserName'))
        operation_icon = _mission_call(operation, 'getIconID')
        if _mission_number(operation_icon) is not None:
            operation_icon = type('')(operation_icon)
        if isinstance(operation_icon, (type(''), bytes)):
            operation_icon = _mission_text(operation_icon)
            if re.match(r'\A[0-9]{1,12}\Z', operation_icon):
                row['iconKey'] = 'operation:' + operation_icon
        try:
            row['series'] = _mission_text(_mission_call(operation, 'getChainName', quest.getChainID()))
        except Exception:
            row['missing'].append('series')
        if not row['operation']:
            row['missing'].append('operation')
        return row

    for _, quest in sorted(personal.getAllQuests(branches).items(), key=lambda item: item[0]):
        if (not quest.isDisabled() and not quest.isFullCompleted() and
                (quest.isInProgress() or quest.isAvailableToPerform())):
            yield quest, normalize


def _crucible_missions(cache):
    from helpers import dependency
    from skeletons.gui.challenges import IChallengesController
    controller = dependency.instance(IChallengesController)
    if controller is None:
        raise MissionSourcePending()
    if not controller.isEnabled:
        return

    chains = controller.getSortedChallenges()
    if not chains:
        return
    quest_ids = {quest_id for chain in chains[:MAX_CRUCIBLE_CHAINS]
                 for quest_id in chain.questsIDs[:MAX_CRUCIBLE_STAGES]}
    quests = cache.getHiddenQuests(lambda q: q.getID() in quest_ids, makeRelations=False)

    def normalize(chain):
        quest_rows = []
        missing = []
        for position, quest_id in enumerate(chain.questsIDs[:MAX_CRUCIBLE_STAGES], 1):
            quest = quests.get(quest_id)
            if quest is None:
                missing.append('stage_unavailable')
                continue
            try:
                row = _quest_row(quest, crucible=True)
            except Exception:
                missing.append('stage_error')
                continue
            row['stage'] = position
            quest_rows.append(row)
        if len(chain.questsIDs) > MAX_CRUCIBLE_STAGES:
            missing.append('stages_truncated')
        if any(row['missing'] for row in quest_rows):
            missing.append('stage_fields')
        active = chain.challengeID == controller.activeChallengeID
        progress = controller.getChallengeProgress(chain.challengeID)
        current_stage = _mission_number(progress.get('quests'))
        completed_stages = max(0, current_stage - 1) if current_stage is not None else None
        completed = bool(controller.isChallengeCompleted(chain))
        if completed:
            completed_stages = len(chain.questsIDs)
        first_quest = quests.get(chain.questsIDs[0]) if chain.questsIDs else None
        return {'id': type('')(chain.challengeID),
                'title': _mission_text(_mission_call(first_quest, 'getUserName')),
                'difficulty': _mission_number(chain.difficulty.value), 'active': active,
                'completed': completed,
                'configuredShields': _mission_number(chain.attempts),
                'completedStages': completed_stages,
                'totalStages': len(chain.questsIDs),
                'expiresAt': _mission_number(chain.finishTime),
                'stages': quest_rows, 'missing': missing}

    for chain in chains[:MAX_CRUCIBLE_CHAINS]:
        yield chain, normalize
    if len(chains) > MAX_CRUCIBLE_CHAINS:
        raise ValueError('crucible_chains_truncated')


def collect_missions():
    from helpers import dependency
    from skeletons.gui.server_events import IEventsCache
    cache = dependency.instance(IEventsCache)
    if cache is None or not cache.isStarted or cache.waitForSync:
        return None
    categories = {}
    sources = (('daily', 'getDailyQuests', False), ('daily_bonus', 'getDailyQuests', True),
               ('daily_epic', 'getDailyEpicQuest', None), ('premium', 'getPremiumQuests', None),
               ('weekly', 'getWeeklyQuests', None))
    for name, getter, bonus in sources:
        categories[name] = _mission_bucket(
            lambda getter=getter, bonus=bonus: _ordinary_missions(cache, getter, bonus))
    categories['personal'] = _mission_bucket(lambda: _personal_missions(cache))
    categories['crucible'] = _mission_bucket(lambda: _crucible_missions(cache))
    return {'schemaVersion': 1, 'categories': categories}


def _mission_log_summary(missions):
    """Return only fixed categories/statuses and bounded counts, never game data."""
    for name in MISSION_CATEGORIES:
        bucket = missions['categories'][name]
        rows = bucket['items']
        stages = [stage for chain in rows for stage in chain.get('stages', [])]
        details = stages if name == 'crucible' else rows
        yield (name, bucket['status'], bucket.get('errorType', 'none'),
               len(rows), len(stages), bucket['failures'],
               sum(bool(row['description']) for row in details),
               sum(bool(row['requirements'] or row.get('conditionText')) for row in details),
               sum(bool(row['rewards']) for row in details),
               sum('requirements_error' in row['missing'] for row in details),
               sum('rewards_error' in row['missing'] for row in details),
               sum(row['missing'].count('stage_unavailable') for row in rows),
               sum(row['missing'].count('stage_error') for row in rows),
               sum(any(group['scope'] == 'primary' for group in row['requirements'])
                   for row in details),
               sum(any(group['scope'] == 'secondary' for group in row['requirements'])
                   for row in details))


class MissionDiagnostics(object):
    """Short, local-only probe that works without a configured network sender."""
    def __init__(self, game):
        self.game = game
        self.callback_id = None
        self.stopped = False
        self.scans = 0

    def start(self):
        self.callback_id = self.game.callback(5, self.tick)

    def tick(self):
        self.callback_id = None
        if self.stopped:
            return
        previous_scans = self.scans
        try:
            import BattleReplay
            player = self.game.player()
            if (player is not None and getattr(player, 'name', None) and
                    getattr(player, 'arena', None) is None and not BattleReplay.isPlaying()):
                self.scans += 1
                MISSION_LOG.info('event=mission_scan scan=%d', self.scans)
                missions = collect_missions()
                if missions is None:
                    MISSION_LOG.info('event=mission_cache_pending')
                else:
                    for summary in _mission_log_summary(missions):
                        MISSION_LOG.info(
                            'event=mission_source category=%s status=%s error_type=%s rows=%d '
                            'stages=%d failures=%d descriptions=%d requirements=%d rewards=%d '
                            'requirement_errors=%d reward_errors=%d missing_stages=%d '
                            'stage_errors=%d primary_conditions=%d secondary_conditions=%d',
                            *summary)
        except Exception as error:
            self.scans = previous_scans + 1
            MISSION_LOG.warning('event=mission_scan_failed error_type=%s',
                                _safe_exception_type(error))
        if self.scans < 9:
            self.callback_id = self.game.callback(20, self.tick)
        else:
            MISSION_LOG.info('event=mission_probe_finished')

    def stop(self):
        self.stopped = True
        if self.callback_id is not None:
            try:
                self.game.cancelCallback(self.callback_id)
            except Exception:
                pass
            self.callback_id = None


def encode_snapshot(snapshot, artwork=None):
    if artwork is None or not artwork.image_ids:
        try:
            from gui.mods.grz_hangar_crew import compact_tooltip_shorts
            snapshot = compact_tooltip_shorts(snapshot)
        except Exception:
            pass
    payload = json.dumps(snapshot, ensure_ascii=True, separators=(',', ':'), sort_keys=True,
                         allow_nan=False).encode('utf-8')
    if len(payload) > MAX_PAYLOAD_BYTES and artwork is not None and artwork.image_ids:
        LOG.warning('event=artwork_upload_skipped reason=payload_limit')
        artwork.drop_references()
        return encode_snapshot(snapshot)
    stats = snapshot.get('sessionStats')
    if len(payload) > MAX_PAYLOAD_BYTES and stats and stats.get('status') == 'available':
        snapshot = dict(snapshot)
        if any('battlesByDay' in row for row in stats['vehicles']):
            LOG.warning('event=stats_daily_counts_skipped reason=payload_limit')
            compact_stats = dict(stats)
            compact_stats['vehicles'] = [dict((key, value) for key, value in row.items()
                                              if key != 'battlesByDay') for row in stats['vehicles']]
            snapshot['sessionStats'] = compact_stats
        else:
            LOG.warning('event=stats_upload_skipped reason=payload_limit')
            snapshot['sessionStats'] = {'schemaVersion': 1, 'provider': 'grz-session-stats',
                                       'status': 'unavailable', 'scope': 'recordedRandomBattles',
                                       'vehicles': []}
        return encode_snapshot(snapshot)
    if len(payload) > MAX_PAYLOAD_BYTES and 'missions' in snapshot:
        LOG.warning('event=mission_upload_skipped reason=payload_limit')
        snapshot = dict(snapshot)
        del snapshot['missions']
        return encode_snapshot(snapshot)
    if len(payload) > MAX_PAYLOAD_BYTES and 'playlists' in snapshot:
        LOG.warning('event=playlists_upload_skipped reason=payload_limit')
        snapshot = dict(snapshot)
        del snapshot['playlists']
        return encode_snapshot(snapshot)
    if len(payload) > MAX_PAYLOAD_BYTES and 'battlePass' in snapshot:
        LOG.warning('event=battle_pass_upload_skipped reason=payload_limit')
        snapshot = dict(snapshot)
        del snapshot['battlePass']
        return encode_snapshot(snapshot)
    if len(payload) > MAX_PAYLOAD_BYTES:
        raise ValueError('Garage exceeds the private Site payload limit')
    # capturedAt changes every read; only the normalized garage determines change.
    stable = dict(snapshot)
    del stable['capturedAt']
    digest = hashlib.sha256(json.dumps(stable, ensure_ascii=True, sort_keys=True,
                                      separators=(',', ':'), allow_nan=False).encode('utf-8')).hexdigest()
    return payload, digest


class _RejectRedirects(object):
    """Create an urllib2 redirect handler lazily (urllib2 is Python 2 only)."""

    @staticmethod
    def new():
        import urllib2
        class NoRedirect(urllib2.HTTPRedirectHandler):
            def redirect_request(self, req, fp, code, msg, headers, newurl):
                return None
        return NoRedirect()


def send_snapshot(payload, config):
    return _send_sites_payload(payload, config)


def send_artwork(payload, config):
    return _send_sites_payload(payload, config, artwork=True)


def _send_sites_payload(payload, config, artwork=False):
    """Config-selected Sites host, verified TLS, no proxy or redirects."""
    _validate_config(config)
    if not config['enabled']:
        raise ConfigError('sync_disabled')
    import ssl
    if not hasattr(ssl, 'create_default_context'):
        raise TLSUnavailable('verified_tls_unavailable')
    import urllib2
    context = ssl.create_default_context()
    context.verify_mode = ssl.CERT_REQUIRED
    context.check_hostname = True
    opener = urllib2.build_opener(
        urllib2.ProxyHandler({}), urllib2.HTTPSHandler(context=context),
        _RejectRedirects.new())
    endpoint = config['endpoint_url']
    if artwork:
        endpoint += '/assets'
    request = urllib2.Request(endpoint, data=payload, headers={
        'Content-Type': 'application/json',
        'X-WoT-Device-Token': config['device_token'],
        'OAI-Sites-Authorization': 'Bearer ' + config['sites_access_token'],
        'User-Agent': 'GRZ-Hangar-Sync/' + VERSION,
    })
    response = opener.open(request, timeout=8)
    try:
        if response.getcode() != 200:
            raise RuntimeError('Unexpected synchronization response')
        # Never log a response body or leak credentials in exceptions.
        body = response.read(4097)
        if len(body) > 4096 or not json.loads(body).get('ok'):
            raise RuntimeError('Synchronization response was rejected')
    finally:
        response.close()


class SyncRuntime(object):
    def __init__(self, config, game=None, transport=None, artwork_transport=None):
        self.config = config
        self.game = game
        self.transport = transport or send_snapshot
        self.artwork_transport = artwork_transport or send_artwork
        self.artwork_store = ArtworkStore()
        self.artwork_capture = None
        self.stopped = threading.Event()
        self.lock = threading.Lock()
        self.pending = None
        self.last_sent = None
        self.last_attempt = None
        self.next_retry = 0
        self.failures = 0
        self.callback_id = None
        self.worker = None

    def start(self):
        if self.game is None:
            import BigWorld
            self.game = BigWorld
        LOG.info('event=worker_starting interval_seconds=%d include_crew=%d',
                 self.config['interval_seconds'], int(self.config['include_crew']))
        self.worker = threading.Thread(target=self._worker_loop, name='GRZHangarSync')
        self.worker.daemon = True
        self.worker.start()
        self._schedule(5)

    def _schedule(self, delay):
        if not self.stopped.is_set():
            self.callback_id = self.game.callback(delay, self.tick)

    def tick(self):
        self.callback_id = None
        if self.stopped.is_set():
            return
        delay = self.config['interval_seconds']
        try:
            if self.artwork_capture is None:
                if time.time() < self.next_retry:
                    return
                artwork = ArtworkCapture(self.artwork_store)
                snapshot = collect_game_snapshot(self.config, artwork)
                if snapshot is None:
                    return
                self.artwork_capture = (snapshot, artwork)
            snapshot, artwork = self.artwork_capture
            if artwork.player is not None:
                player = self.game.player()
                if player is not artwork.player or getattr(player, 'arena', None) is not None:
                    self.artwork_capture = None
                    return
            if not artwork.step():
                delay = 0.03
                return
            self.artwork_capture = None
            self._queue_capture(snapshot, artwork)
        except Exception as error:
            self.artwork_capture = None
            LOG.warning('event=capture_failed error_type=%s; will_retry=1',
                        _safe_exception_type(error))
        finally:
            self._schedule(delay)

    def _queue_capture(self, snapshot, artwork):
        LOG.debug('event=artwork_read vehicle=%d/%d item=%d/%d crew=%d/%d',
                  artwork.resolved['vehicle'], artwork.requested['vehicle'],
                  artwork.resolved['item'], artwork.requested['item'],
                  artwork.resolved['crew'], artwork.requested['crew'])
        payload, digest = encode_snapshot(snapshot, artwork)
        image_ids = frozenset(artwork.image_ids)
        LOG.debug('event=capture_ready vehicle_count=%d payload_bytes=%d',
                  len(snapshot['vehicles']), len(payload))
        with self.lock:
            if self.pending is not None:
                LOG.debug('event=send_skipped reason=previous_request_pending')
                return
            self.artwork_store.prune(image_ids)
            needs_artwork = self.artwork_store.has_pending(image_ids)
            if digest == self.last_attempt or (digest == self.last_sent and not needs_artwork):
                LOG.debug('event=send_skipped reason=unchanged_snapshot')
                return
            self.pending = (payload, digest, image_ids)
            LOG.debug('event=send_queued payload_bytes=%d', len(payload))

    def _worker_loop(self):
        while not self.stopped.wait(0.25):
            with self.lock:
                request = self.pending
                self.pending = None
                if request:
                    self.last_attempt = request[1]
            if request is None:
                continue
            try:
                if self.stopped.is_set():
                    continue
                if request[1] != self.last_sent:
                    LOG.info('event=send_attempt payload_bytes=%d attempt=%d',
                             len(request[0]), self.failures + 1)
                    self.transport(request[0], self.config)
                    with self.lock:
                        self.last_sent = request[1]
                    LOG.info('event=send_success http_status=200 payload_bytes=%d',
                             len(request[0]))
            except Exception as error:
                self.failures += 1
                retry_seconds = min(900, 30 * (2 ** min(5, self.failures)))
                self.next_retry = time.time() + retry_seconds
                kind, http_status = _network_error_kind(error)
                LOG.warning('event=send_failed kind=%s http_status=%d retry_seconds=%d',
                            kind, http_status, retry_seconds)
            else:
                self.failures = 0
                self.next_retry = 0
                self._upload_artwork(request[2])
            finally:
                with self.lock:
                    self.last_attempt = None

    def _upload_artwork(self, image_ids):
        try:
            batches = artwork_batches(self.artwork_store.pending(image_ids))
            for ids, payload in batches:
                with self.lock:
                    if self.stopped.is_set() or self.pending is not None:
                        return
                self.artwork_transport(payload, self.config)
                self.artwork_store.uploaded(ids)
                LOG.info('event=artwork_send_success count=%d payload_bytes=%d', len(ids), len(payload))
        except Exception as error:
            kind, http_status = _network_error_kind(error)
            LOG.warning('event=artwork_send_failed kind=%s http_status=%d', kind, http_status)

    def stop(self):
        self.stopped.set()
        self.artwork_capture = None
        if self.callback_id is not None:
            try:
                self.game.cancelCallback(self.callback_id)
            except Exception:
                pass
            self.callback_id = None
        with self.lock:
            self.pending = None
        LOG.info('event=worker_stop_requested')


def init():
    global _state, _mission_probe
    if _state is not None:
        return
    if not start_diagnostics():
        # Refuse network access if the requested private log cannot be opened.
        LOG.warning('event=diagnostics_unavailable sync_disabled=1')
        return
    LOG.info('event=config_loading')
    try:
        config = load_config(config_path())
    except Exception as error:
        code = _config_error_code(error)
        LOG.warning('event=config_failed code=%s sync_disabled=1', code)
        config = None
    if (config is None or config['mission_diagnostics']) and _mission_probe is None:
        if start_diagnostics(logger=MISSION_LOG, filename=MISSION_LOG_FILE):
            try:
                import BigWorld
                probe = MissionDiagnostics(BigWorld)
                probe.start()
                _mission_probe = probe
            except Exception as error:
                MISSION_LOG.warning('event=mission_probe_start_failed error_type=%s',
                                    _safe_exception_type(error))
    if config is None:
        return
    if not config['enabled']:
        LOG.info('event=sync_disabled reason=configuration')
        return
    try:
        _state = SyncRuntime(config)
        _state.start()
        LOG.info('event=sync_enabled')
    except Exception as error:
        if _state is not None:
            _state.stop()
        _state = None
        LOG.warning('event=sync_start_failed error_type=%s', _safe_exception_type(error))


def fini():
    global _state, _mission_probe
    if _mission_probe is not None:
        _mission_probe.stop()
        _mission_probe = None
    running = _state
    _state = None
    if running is not None:
        running.stop()
    LOG.info('event=mod_shutdown')
