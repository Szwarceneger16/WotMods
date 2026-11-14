# -*- coding: utf-8 -*-
"""Optional native thumbnails, resolved at presentation time, never persisted.

Verified EU client sources (2.4.1.5493):
  gui/shared/gui_items/Vehicle.py: getIconPath, getSmallIconPath,
    getIconResourceName
  gui/shared/utils/functions.py: getArenaImage, getAbsoluteUrl
  gui/impl/backport/backport_r.py: image -> wulf.getImagePath
  items/vehicles.py: getVehicleType and VehicleType.compactDescr
  gui/shared/gui_items/Vehicle.py: role, roleLabel, getType44x44IconResource
  gui/shared/formatters: getRoleText; formatters/icons.py: getRoleIcon
  R.strings.menu.roleExp.roleDescr supplies the original client definition.
Assets / Gameface loader: Kurzdor/wot.assets 2.4.1.0 #977,
  commit 3605bd36c53d10c16be5d93f5414aa5fd129e84e.

R selects the exact vehicle/map image; ResMgr confirms its local backing file.
The native img:// loader also accepts DDS. No remote graphics or URL guessing.
"""
from __future__ import absolute_import, unicode_literals

from .localization import message

import re
import copy

try:
    text_type = unicode
    integer_types = (int, long)
except NameError:
    text_type = str
    integer_types = (int,)

_PREFIXES = {'vehicle': 'gui/maps/icons/vehicle/', 'map': 'gui/maps/icons/map/',
             'outcome': 'gui/maps/icons/library/',
             'vehicle_class': 'gui/maps/icons/vehicleTypes/',
             'vehicle_role': 'gui/maps/icons/roleExp/roles/24x24/'}
_OUTCOME_FILES = dict((key, _PREFIXES['outcome'] + 'BgBattleResultIcon' + name + '-1.png')
                      for key, name in (('win', 'Victory'), ('loss', 'Defeat'), ('draw', 'Draw')))
_SAFE_PATH = re.compile(r'^[A-Za-z0-9_./-]+\Z')
_SAFE_GEOMETRY = re.compile(r'^[A-Za-z0-9_-]{1,128}\Z')
_DECIMAL = re.compile(r'^[0-9]+\Z')
_DEFAULT_RESOLVER = None
_CLASSES = dict((key, key) for key in ('lightTank', 'mediumTank', 'heavyTank', 'AT_SPG', 'SPG'))
_CLASSES['AT-SPG'] = 'AT_SPG'
_ROLE_KEY = re.compile(r'\Arole_[A-Za-z0-9_]{1,64}\Z')


def canonical_vehicle_class(value):
    """Normalize the client's AT-SPG spelling without inferring from a name."""
    return _CLASSES.get(_text(value)) if isinstance(value, (bytes, text_type)) else None


def _native_role_text(value, limit=240):
    """Retain resolved client paragraphs, never native markup or format tokens."""
    if not isinstance(value, (bytes, text_type)):
        return None
    try:
        value = _text(value)[:16384].replace('&zwnbsp;', '')
        try:
            from HTMLParser import HTMLParser
            value = HTMLParser().unescape(value)
        except ImportError:
            from html import unescape
            value = unescape(value)
        value = re.sub(r'<br\s*/?>|</p\s*>', '\n', value, flags=re.I)
        value = re.sub(r'<[^>]*>', ' ', value)
        value = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f\ufeff\u200b\u2060]', ' ', value)
        value = '\n'.join(' '.join(line.split()) for line in value.splitlines() if line.strip())
        if (not value or re.search(r'#[A-Za-z][A-Za-z0-9_]*:', value) or
                re.search(r'%\([^)]+\)[A-Za-z]|%[sd]|\{[^{}]+\}', value)):
            return None
        return value[:limit]
    except Exception:
        return None


def _text(value):
    if isinstance(value, bytes) and not isinstance(value, text_type):
        return value.decode('utf-8', 'replace')
    return text_type(value)


def _compact_id(value):
    if isinstance(value, bool):
        return None
    if isinstance(value, integer_types):
        return value if value > 0 else None
    if isinstance(value, (bytes, text_type)):
        value = _text(value)
        if value and len(value) <= 20 and _DECIMAL.match(value):
            number = int(value)
            return number if number > 0 else None
    return None


def verified_image_url(native_url, kind, file_exists):
    """Keep native img://, requiring the exact local PNG or its DDS backing.

    Coherent's ordinary file loader is not substituted for WoT's texture loader.
    A DDS candidate is used only when ResMgr confirms that actual local file.
    """
    if kind not in _PREFIXES or not isinstance(native_url, (bytes, text_type)):
        return None
    url = _text(native_url)
    if not url.startswith('img://'):
        return None
    path = url[len('img://'):]
    if kind == 'outcome' and path not in tuple(_OUTCOME_FILES.values()) + tuple(
            value[:-4] + '.dds' for value in _OUTCOME_FILES.values()):
        return None
    if not path.startswith(_PREFIXES[kind]) or not _SAFE_PATH.match(path):
        return None
    if any(part in ('', '.', '..') for part in path.split('/')):
        return None
    try:
        if file_exists(path):
            return 'img://' + path
        if path.lower().endswith('.png'):
            dds_path = path[:-4] + '.dds'
            if file_exists(dds_path):
                return 'img://' + dds_path
    except Exception:
        # Images must never prevent a row or the statistics window from loading.
        return None
    return None


class NativeVisualResolver(object):
    """A small, lazily initialized adapter around the client's resource registry."""

    def __init__(self, resources=None, vehicle_getter=None, image_getter=None,
                 icon_name_getter=None, absolute_url_getter=None, file_exists=None,
                 role_label_getter=None, role_name_getter=None, text_getter=None):
        if resources is None:
            from gui.impl.gen.resources import R
            resources = R
        if image_getter is None:
            from gui.impl.backport import image
            image_getter = image
        if absolute_url_getter is None:
            from gui.shared.utils.functions import getAbsoluteUrl
            absolute_url_getter = getAbsoluteUrl
        if file_exists is None:
            import ResMgr
            file_exists = ResMgr.isFile
        self._resources = resources
        self._vehicle_getter = vehicle_getter
        self._image_getter = image_getter
        self._icon_name_getter = icon_name_getter
        self._absolute_url_getter = absolute_url_getter
        self._file_exists = file_exists
        self._role_label_getter = role_label_getter
        self._role_name_getter = role_name_getter
        self._text_getter = text_getter
        self._vehicles = {}
        self._vehicle_metadata = {}
        self._maps = {}
        self._map_previews = {}
        self._outcomes = {}

    def vehicle_metadata(self, compact):
        """Resolve class/role from the live descriptor for historic as well as new rows.

        Vehicle.roleLabel maps descriptor.type.role through ROLE_TYPE_TO_LABEL.
        getRoleText supplies the groupName placeholder used by native role names.
        Definitions are the running client's localized text, as in Hangar Sync.
        """
        compact = _compact_id(compact)
        if compact is None:
            return None
        if compact in self._vehicle_metadata:
            return copy.deepcopy(self._vehicle_metadata[compact])
        try:
            if self._vehicle_getter is None:
                from items.vehicles import getVehicleType
                self._vehicle_getter = getVehicleType
            vehicle = self._vehicle_getter(compact)
            if getattr(vehicle, 'compactDescr', None) != compact:
                return None
            try:
                kind = canonical_vehicle_class(getattr(vehicle, 'classTag', None))
            except Exception:
                kind = None
            if not kind:
                try:
                    kinds = set(canonical_vehicle_class(tag) for tag in getattr(vehicle, 'tags', ()))
                    kinds.discard(None)
                    kind = next(iter(kinds)) if len(kinds) == 1 else None
                except Exception:
                    pass
            result = {}
            try:
                tier = getattr(vehicle, 'level', None)
            except Exception:
                tier = None
            if not isinstance(tier, bool) and isinstance(tier, integer_types) and 1 <= tier <= 11:
                result['tier'] = tier
            if kind:
                result['class'] = kind
                try:
                    root = self._resources.images.gui.maps.icons.vehicleTypes
                    for branch in ('c_44x44', 'big'):
                        try:
                            icon = self._resource_url(getattr(root, branch).dyn(kind), 'vehicle_class')
                            if icon:
                                result['class_icon'] = {'kind': 'vehicle_class', 'src': icon}
                                break
                        except Exception:
                            pass
                except Exception:
                    pass
            key = None
            try:
                if self._role_label_getter is None:
                    from constants import ROLE_TYPE_TO_LABEL
                    self._role_label_getter = lambda descriptor: ROLE_TYPE_TO_LABEL.get(descriptor.role)
                key = self._role_label_getter(vehicle)
                if not isinstance(key, (bytes, text_type)) or not _ROLE_KEY.match(_text(key)):
                    key = None
                else:
                    key = _text(key)
            except Exception:
                pass
            if key:
                role = {'key': key}
                try:
                    if self._role_name_getter is None:
                        from gui.shared.formatters import getRoleText
                        self._role_name_getter = getRoleText
                    name = _native_role_text(self._role_name_getter(key))
                    if name:
                        role['name'] = name
                except Exception:
                    pass
                try:
                    if self._text_getter is None:
                        from gui.impl.backport import text
                        self._text_getter = text
                    strings = self._resources.strings.menu.roleExp
                    for field, branch, bound in (('group_name', 'roleGroupName', 240),
                                                 ('description', 'roleDescr', 1400)):
                        try:
                            value = _native_role_text(self._text_getter(getattr(strings, branch).dyn(key)()), bound)
                            if value:
                                role[field] = value
                        except Exception:
                            pass
                except Exception:
                    pass
                if key != 'role_SPG':
                    try:
                        # Native getRoleIcon intentionally omits SPG; no fake glyph.
                        node = self._resources.images.gui.maps.icons.roleExp.roles.c_24x24.dyn(key)
                        icon = self._resource_url(node, 'vehicle_role')
                        if icon:
                            role['icon'] = {'kind': 'vehicle_role', 'src': icon}
                    except Exception:
                        pass
                result['role'] = role
                if (result.get('class_icon') and role.get('name') and role.get('description') and
                        (role.get('icon') or key == 'role_SPG')):
                    self._vehicle_metadata[compact] = copy.deepcopy(result)
            return result or None
        except Exception:
            return None

    def _resource_url(self, node, kind):
        try:
            if not node.exists():
                return None
            resource_id = node()
            if isinstance(resource_id, bool) or not isinstance(resource_id, integer_types) or resource_id <= 0:
                return None
            native_path = self._image_getter(resource_id)
            if not isinstance(native_path, (bytes, text_type)):
                return None
            native_url = self._absolute_url_getter(_text(native_path))
            return verified_image_url(native_url, kind, self._file_exists)
        except Exception:
            return None

    def vehicle_src(self, compact):
        compact = _compact_id(compact)
        if compact is None:
            return None
        if compact in self._vehicles:
            return self._vehicles[compact]
        try:
            # These helpers belong only to vehicle thumbnails. Resolve them
            # lazily so a changed vehicle API cannot also disable map images.
            # Failed imports are retried later, not cached as a permanent loss.
            if self._vehicle_getter is None:
                from items.vehicles import getVehicleType
                self._vehicle_getter = getVehicleType
            if self._icon_name_getter is None:
                from gui.shared.gui_items.Vehicle import getIconResourceName
                self._icon_name_getter = getIconResourceName
            vehicle = self._vehicle_getter(compact)
            # getVehicleType extracts bit fields: reject a malformed ID that
            # would otherwise alias a different, valid vehicle descriptor.
            if getattr(vehicle, 'compactDescr', None) != compact:
                return None
            icon_name = self._icon_name_getter(vehicle.name)
            root = self._resources.images.gui.maps.icons.vehicle
            source = self._resource_url(root.dyn(icon_name), 'vehicle')
            if not source:
                source = self._resource_url(root.small.dyn(icon_name), 'vehicle')
            if source:
                self._vehicles[compact] = source
            return source
        except Exception:
            return None

    def outcome_src(self, outcome):
        # Exact neutral-language WG notification artwork, verified in 2.4.1.
        # Localized captions are supplied separately; never modify client art.
        if not isinstance(outcome, text_type) or outcome not in _OUTCOME_FILES:
            return None
        if outcome not in self._outcomes:
            source = verified_image_url('img://' + _OUTCOME_FILES[outcome], 'outcome', self._file_exists)
            if source:
                self._outcomes[outcome] = source
            return source
        return self._outcomes[outcome]

    def map_src(self, geometry):
        if not isinstance(geometry, (bytes, text_type)):
            return None
        geometry = _text(geometry)
        if not _SAFE_GEOMETRY.match(geometry):
            return None
        if geometry in self._maps:
            return self._maps[geometry]
        try:
            # Matches getArenaImage(geometry, 'small'), used by native training
            # lists (100x60). Do not derive a map from its translated name.
            root = self._resources.images.gui.maps.icons.map
            try:
                source = self._resource_url(root.dyn('small').num(geometry), 'map')
            except Exception:
                source = None
            if not source:
                # Only a verified default icon of this exact same geometry.
                source = self._resource_url(root.num(geometry), 'map')
            if source:
                self._maps[geometry] = source
            return source
        except Exception:
            return None

    def map_preview(self, geometry, mode='image'):
        """Resolve a larger native hover image without changing card artwork.

        The screen branch supplies landscape loading art (2560x1600 in the
        reviewed catalogue). The default map branch is the native lobby's
        300x300 minimap. Both are selected through R, never a guessed URL.
        """
        if not isinstance(geometry, (bytes, text_type)) or mode not in ('image', 'minimap'):
            return None
        geometry = _text(geometry)
        if not _SAFE_GEOMETRY.match(geometry):
            return None
        key = (mode, geometry)
        if key in self._map_previews:
            return {'src': self._map_previews[key], 'mode': mode}
        try:
            root = self._resources.images.gui.maps.icons.map
            node = root.num(geometry) if mode == 'minimap' else root.dyn('screen').num(geometry)
            source = self._resource_url(node, 'map')
        except Exception:
            source = None
        if source:
            self._map_previews[key] = source
            return {'src': source, 'mode': mode}
        # Do not cache a fallback as a permanently successful large preview:
        # the registry or texture can become available on a later snapshot.
        source = self.map_src(geometry)
        return {'src': source, 'mode': 'image'} if source else None


def _get_native_resolver():
    global _DEFAULT_RESOLVER
    if _DEFAULT_RESOLVER is None:
        try:
            _DEFAULT_RESOLVER = NativeVisualResolver()
        except Exception:
            # The resource manager may not be ready on an early account event.
            # Retry on the next snapshot; never cache initialization failure.
            return None
    return _DEFAULT_RESOLVER


def enrich_snapshot(payload, battle_records=None, resolver=None, map_preview_mode='image'):
    """Add row.visual to a fresh snapshot; read the existing ledger only for IDs.

    Existing tank/map rows already carry the stable group ID. A battle row has
    an arena ID, so use its saved record for the original vehicle/map IDs. Names
    are alt text only. Missing metadata never triggers a guess from a row name.
    """
    if not isinstance(payload, dict) or not isinstance(payload.get('scopes'), dict):
        return payload
    resolver = resolver if resolver is not None else _get_native_resolver()
    records = battle_records if isinstance(battle_records, dict) else {}
    cache = {}
    if map_preview_mode not in ('image', 'minimap'):
        map_preview_mode = 'image'

    def visual(kind, identifier, name):
        if resolver is None or identifier is None:
            return None
        key = (kind, _text(identifier))
        if key not in cache:
            try:
                getter = getattr(resolver, kind + '_src')
                cache[key] = getter(identifier)
            except Exception:
                cache[key] = None
        source = cache[key]
        if not source:
            return None
        return {'kind': kind, 'src': source,
                'alt': _text(name) if name else (message('visual.vehicle') if kind == 'vehicle' else message('visual.map'))}

    def map_visual(identifier, name):
        image = visual('map', identifier, name)
        if image is None:
            return None
        key = ('map_preview', _text(identifier))
        if key not in cache:
            try:
                cache[key] = resolver.map_preview(identifier, map_preview_mode)
            except Exception:
                cache[key] = None
        preview = cache[key]
        if (isinstance(preview, dict) and preview.get('src') and
                preview.get('mode') in ('image', 'minimap') and
                (preview['src'] != image['src'] or preview['mode'] == 'minimap')):
            image['preview_src'] = preview['src']
            image['preview_mode'] = preview['mode']
        return image

    def vehicle_metadata(identifier):
        if resolver is None or identifier is None:
            return None
        key = ('vehicle_metadata', _text(identifier))
        if key not in cache:
            try:
                cache[key] = resolver.vehicle_metadata(identifier)
            except Exception:
                cache[key] = None
        return copy.deepcopy(cache[key])

    for scope in payload['scopes'].values():
        if not isinstance(scope, dict):
            continue
        for grouping in ('vehicles', 'maps', 'battles'):
            rows = scope.get(grouping)
            if not isinstance(rows, list):
                continue
            for row in rows:
                if not isinstance(row, dict):
                    continue
                row.pop('visual', None)
                row.pop('map_visual', None)
                row.pop('outcome_visual', None)
                row.pop('vehicle_meta', None)
                if grouping == 'battles' and row.get('outcome') in ('win', 'loss', 'draw'):
                    outcome = visual('outcome', row['outcome'], message('outcome.' + row['outcome']))
                    if outcome is not None:
                        row['outcome_visual'] = outcome
                if grouping == 'vehicles':
                    image = visual('vehicle', row.get('id'), row.get('name'))
                    metadata = vehicle_metadata(row.get('id'))
                elif grouping == 'maps':
                    image = map_visual(row.get('id'), row.get('name'))
                    metadata = None
                else:
                    record = records.get(_text(row.get('id')), {})
                    if not isinstance(record, dict):
                        continue
                    image = visual('vehicle', record.get('vehicle_id'), row.get('name'))
                    metadata = vehicle_metadata(record.get('vehicle_id'))
                    map_image = map_visual(record.get('map_id'), record.get('map_name') or row.get('map'))
                    if map_image is not None:
                        row['map_visual'] = map_image
                if image is not None:
                    row['visual'] = image
                if metadata:
                    row['vehicle_meta'] = metadata
                    if metadata.get('class'):
                        row['type'] = metadata['class']
                    if metadata.get('tier') and not row.get('tier'):
                        row['tier'] = metadata['tier']
    return payload
