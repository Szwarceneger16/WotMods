# -*- coding: utf-8 -*-
"""Consume the already loaded Session Stats provider without importing it.

No result collection, ledger reads, rating formulas or finance calculations live
in this adapter. Only the provider's explicit, bounded JSON contract is copied.
"""
from __future__ import absolute_import, unicode_literals

import datetime
import math
import re
import sys

try:
    _INTS = (int, long)
except NameError:
    _INTS = (int,)
_NUMBERS = _INTS + (float,)
_RUNTIME_MODULE = 'gui.mods.grz_session_stats.runtime'
_STATUSES = ('available', 'not_loaded', 'unsupported', 'pending', 'unavailable')
_MAX_VEHICLES = 1200


def _empty(status):
    return {'schemaVersion': 1, 'provider': 'grz-session-stats', 'status': status,
            'scope': 'recordedRandomBattles', 'vehicles': []}


def _number(value, minimum, maximum, integer=False, nullable=False):
    if value is None and nullable:
        return None
    if (type(value) not in (_INTS if integer else _NUMBERS) or
            not minimum <= value <= maximum or
            isinstance(value, float) and (math.isnan(value) or math.isinf(value))):
        raise ValueError('invalid_stats_number')
    return value


def _day(value):
    if isinstance(value, bytes):
        value = value.decode('ascii')
    if not isinstance(value, type('')) or not re.match(r'\A\d{4}-\d{2}-\d{2}\Z', value):
        raise ValueError('invalid_stats_day')
    return datetime.datetime.strptime(value, '%Y-%m-%d').date()


def _validate(value, vehicle_ids):
    if (not isinstance(value, dict) or value.get('schemaVersion') != 1 or
            value.get('provider') != 'grz-session-stats' or
            value.get('scope') != 'recordedRandomBattles' or
            value.get('status') not in _STATUSES):
        raise ValueError('invalid_stats_provider')
    result = _empty(value['status'])
    version = value.get('providerVersion')
    if version is not None:
        if isinstance(version, bytes):
            version = version.decode('ascii')
        if (not isinstance(version, type('')) or len(version) > 32 or
                not re.match(r'\A\d+\.\d+\.\d+(?:-[A-Za-z0-9.-]+)?(?:\+[A-Za-z0-9.-]+)?\Z', version)):
            raise ValueError('invalid_stats_version')
        result['providerVersion'] = version
    if result['status'] != 'available':
        return result
    day_range = value.get('dayRange')
    if not isinstance(day_range, dict) or day_range.get('basis') != 'gameLocalTime':
        raise ValueError('invalid_stats_range')
    first, last = _day(day_range.get('from')), _day(day_range.get('through'))
    if not 0 <= (last - first).days <= 365:
        raise ValueError('invalid_stats_range')
    result['dayRange'] = {'from': first.isoformat(), 'through': last.isoformat(),
                          'basis': 'gameLocalTime'}
    rows = value.get('vehicles')
    if not isinstance(rows, list) or len(rows) > _MAX_VEHICLES:
        raise ValueError('invalid_stats_vehicles')
    allowed, seen = set(vehicle_ids), set()
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError('invalid_stats_vehicle')
        identifier = _number(row.get('vehicleId'), 1, 0xffffffff, integer=True)
        if identifier in seen:
            raise ValueError('duplicate_stats_vehicle')
        seen.add(identifier)
        if identifier not in allowed:
            continue
        record = {'vehicleId': identifier,
                  'battles': _number(row.get('battles'), 0, 10 ** 9, integer=True),
                  'wn8': _number(row.get('wn8'), 0, 10 ** 9, nullable=True),
                  'creditsNet': _number(row.get('creditsNet'), -(10 ** 15), 10 ** 15, nullable=True),
                  'lastPlayedAt': _number(row.get('lastPlayedAt'), 0, 10 ** 12, nullable=True),
                  'battlesToday': _number(row.get('battlesToday'), 0, 10 ** 9, integer=True, nullable=True),
                  'ownedSince': None}
        by_day = row.get('battlesByDay')
        if by_day is not None:
            if not isinstance(by_day, dict) or len(by_day) > 366:
                raise ValueError('invalid_stats_days')
            clean_days = {}
            for day, count in by_day.items():
                parsed = _day(day)
                if not first <= parsed <= last:
                    raise ValueError('stats_day_outside_range')
                clean_days[parsed.isoformat()] = _number(count, 0, 10 ** 9, integer=True)
            record['battlesByDay'] = clean_days
        result['vehicles'].append(record)
    result['vehicles'].sort(key=lambda row: row['vehicleId'])
    return result


def collect_session_stats(vehicle_ids, modules=None):
    """Read only a loaded provider. Absence never initializes another mod."""
    modules = sys.modules if modules is None else modules
    runtime = modules.get(_RUNTIME_MODULE)
    if runtime is None:
        return _empty('not_loaded')
    provider = getattr(runtime, 'read_hangar_stats', None)
    if not callable(provider):
        return _empty('unsupported')
    try:
        identifiers = list(vehicle_ids)
        if len(identifiers) > _MAX_VEHICLES:
            raise ValueError('too_many_stats_vehicles')
        for identifier in identifiers:
            _number(identifier, 1, 0xffffffff, integer=True)
        identifiers = sorted(set(identifiers))
        return _validate(provider(identifiers), identifiers)
    except Exception:
        # Provider exceptions may include private local paths or account IDs.
        return _empty('unavailable')
