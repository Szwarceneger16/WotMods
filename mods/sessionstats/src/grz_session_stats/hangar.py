# -*- coding: utf-8 -*-
"""Read-only public vehicle summary for an already running Stats instance.

WN8 and finances come from the same unfiltered timeline groups as the Stats UI.
Calendar counts use confirmed Random Battle records within those groups; no
other mod needs access to this mod's private ledger, identity or calculations.
"""
from __future__ import absolute_import, unicode_literals

import copy
import datetime
import time
import weakref

from . import VERSION
from .normalize import text_type

try:
    _INTS = (int, long)
except NameError:
    _INTS = (int,)

_CACHE = weakref.WeakKeyDictionary()
_MAX_VEHICLES = 1200


def _empty(status):
    return {'schemaVersion': 1, 'provider': 'grz-session-stats',
            'providerVersion': text_type(VERSION), 'status': status,
            'scope': 'recordedRandomBattles', 'vehicles': []}


def read_snapshot(runtime, vehicle_ids):
    """Called on the game's main thread; never start services or read files."""
    if not isinstance(vehicle_ids, (list, tuple)) or len(vehicle_ids) > _MAX_VEHICLES:
        raise ValueError('Invalid requested vehicle IDs')
    if any(type(value) not in _INTS or not 0 < value <= 0xffffffff for value in vehicle_ids):
        raise ValueError('Invalid requested vehicle ID')
    vehicle_ids = tuple(sorted(set(vehicle_ids)))
    if runtime is None or not runtime.running or runtime.api is None:
        return _empty('unavailable')
    api = runtime.api
    if api.is_replay() or api.in_battle():
        return _empty('unavailable')
    dbid = api.account_dbid()
    key = '{0}:{1}'.format(api.region, int(dbid)) if dbid else None
    service = runtime.active_service
    if (not key or key != runtime.active_key or service is None or
            service.account_key != key or getattr(service, '_closed', False)):
        return _empty('unavailable')
    if service.loading:
        return _empty('pending')
    if not service.ready:
        return _empty('unavailable')
    # The full index is intentionally independent of UI pages, sorting and the
    # user's selected timeline bounds. Launch/reset scopes are not lifetime data.
    indexes = getattr(service, '_indexes', None) or {}
    index = indexes.get('timeline')
    if index is None:
        return _empty('unsupported')
    now = runtime.now()
    today = datetime.date.fromtimestamp(now)
    first = today - datetime.timedelta(days=365)
    # Include timezone state so an OS timezone change invalidates calendar counts.
    calendar_key = (today.isoformat(), tuple(time.tzname), time.timezone,
                    time.localtime(now).tm_isdst)
    signature = (service.store.sequence, calendar_key, vehicle_ids)
    cached = _CACHE.get(service)
    if cached is not None and cached[0] == signature:
        return copy.deepcopy(cached[1])
    result = _empty('available')
    result['dayRange'] = {'from': first.isoformat(), 'through': today.isoformat(),
                          'basis': 'gameLocalTime'}
    groups = index.groups['vehicles']
    for identifier in vehicle_ids:
        group = groups.get(text_type(identifier))
        if group is None:
            continue
        totals = group.totals.snapshot()
        if not totals['battles']:
            continue
        by_day = {}
        last_played = None
        missing_dates = False
        for record in group.records.values():
            # Match the existing Totals definition of a received Random Battle.
            if record.get('mode') != 'random' or record.get('outcome') not in ('win', 'loss', 'draw'):
                continue
            started_at = record.get('started_at')
            if started_at is None:
                missing_dates = True
                continue
            last_played = max(last_played or started_at, started_at)
            date = datetime.date.fromtimestamp(started_at)
            if first <= date <= today:
                day = date.isoformat()
                by_day[day] = by_day.get(day, 0) + 1
        row = {
            'vehicleId': identifier, 'battles': totals['battles'], 'wn8': totals['wn8'],
            'creditsNet': totals['credits_net']['sum'], 'lastPlayedAt': last_played,
            'battlesToday': None if missing_dates else by_day.get(today.isoformat(), 0),
            # First recorded battle never proves purchase or continuous ownership.
            'ownedSince': None,
        }
        if not missing_dates:
            row['battlesByDay'] = by_day
        result['vehicles'].append(row)
    _CACHE[service] = (signature, result)
    return copy.deepcopy(result)
