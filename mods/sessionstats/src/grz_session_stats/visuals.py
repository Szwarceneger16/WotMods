# -*- coding: utf-8 -*-
"""Optional native thumbnails, resolved at presentation time, never persisted.

Verified EU client sources (2.4.1.5493):
  gui/shared/gui_items/Vehicle.py: getIconPath, getSmallIconPath,
    getIconResourceName
  gui/shared/utils/functions.py: getArenaImage, getAbsoluteUrl
  gui/impl/backport/backport_r.py: image -> wulf.getImagePath
  items/vehicles.py: getVehicleType and VehicleType.compactDescr
Assets / Gameface loader: Kurzdor/wot.assets 2.4.1.0 #977,
  commit 3605bd36c53d10c16be5d93f5414aa5fd129e84e.

R selects the exact vehicle/map image; ResMgr confirms its local backing file.
The native img:// loader also accepts DDS. No remote graphics or URL guessing.
"""
from __future__ import absolute_import, unicode_literals

from .localization import message

import re

try:
    text_type = unicode
    integer_types = (int, long)
except NameError:
    text_type = str
    integer_types = (int,)

_PREFIXES = {'vehicle': 'gui/maps/icons/vehicle/', 'map': 'gui/maps/icons/map/',
             'outcome': 'gui/maps/icons/library/'}
_OUTCOME_FILES = dict((key, _PREFIXES['outcome'] + 'BgBattleResultIcon' + name + '-1.png')
                      for key, name in (('win', 'Victory'), ('loss', 'Defeat'), ('draw', 'Draw')))
_SAFE_PATH = re.compile(r'^[A-Za-z0-9_./-]+\Z')
_SAFE_GEOMETRY = re.compile(r'^[A-Za-z0-9_-]{1,128}\Z')
_DECIMAL = re.compile(r'^[0-9]+\Z')
_DEFAULT_RESOLVER = None


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
                 icon_name_getter=None, absolute_url_getter=None, file_exists=None):
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
        self._vehicles = {}
        self._maps = {}
        self._outcomes = {}

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


def enrich_snapshot(payload, battle_records=None, resolver=None):
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
                row.pop('outcome_visual', None)
                if grouping == 'battles' and row.get('outcome') in ('win', 'loss', 'draw'):
                    outcome = visual('outcome', row['outcome'], message('outcome.' + row['outcome']))
                    if outcome is not None:
                        row['outcome_visual'] = outcome
                if grouping == 'vehicles':
                    image = visual('vehicle', row.get('id'), row.get('name'))
                elif grouping == 'maps':
                    image = visual('map', row.get('id'), row.get('name'))
                else:
                    record = records.get(_text(row.get('id')), {})
                    if not isinstance(record, dict):
                        continue
                    image = visual('vehicle', record.get('vehicle_id'), row.get('name'))
                    if image is None:
                        image = visual('map', record.get('map_id'), record.get('map_name') or row.get('map'))
                if image is not None:
                    row['visual'] = image
    return payload
