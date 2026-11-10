# -*- coding: utf-8 -*-
"""Statistics and sessions; no dependency on the World of Tanks runtime."""
from __future__ import unicode_literals

from .battle_details import clean_details, merge_details
from .localization import message

import bisect
import copy
import hashlib
import itertools
import math
import os
import time
import uuid

from .loading import complete, items, values

from . import VERSION
from .storage import GenerationStore, StateDelta, SCHEMA_VERSION, StorageError

try:
    text_type = unicode
    number_types = (int, long, float)
except NameError:
    text_type = str
    number_types = (int, float)

_OUTCOMES = ('win', 'loss', 'draw')
_CURRENCIES = ('credits', 'bonds', 'gold')
_BREAKDOWN = ('repair', 'ammo', 'consumables', 'directives')
_NUMBERS = ('damage', 'frags', 'spots', 'defense', 'xp_base', 'xp_received', 'free_xp')
_UNKNOWN_MEMBERSHIP = message('core.membership')
MAX_TIME_POINTS = 1000


def _text(value):
    if isinstance(value, bytes) and not isinstance(value, text_type):
        return value.decode('utf-8', 'replace')
    return text_type(value)


def _number(value, nonnegative=False):
    if isinstance(value, bool) or not isinstance(value, number_types):
        return None
    try:
        if math.isnan(value) or math.isinf(value):
            return None
    except (ValueError, OverflowError):
        return None
    if nonnegative and value < 0:
        return None
    return value


def _series(values):
    known = [value for value in values if value is not None]
    if not known:
        return {'min': None, 'avg': None, 'max': None, 'sum': None, 'count': 0}
    total = _number(sum(known))
    # Finite source values can still overflow during aggregation. Unknown
    # derived values must not make the native JSON payload unrenderable.
    return {'min': min(known), 'avg': total / float(len(known)) if total is not None else None,
            'max': max(known), 'sum': total, 'count': len(known)}


def wn8_from_totals(actual, expected):
    """Exact aggregate formula. Wins and expected wins are counts, not percents."""
    ratios = {}
    for key in ('damage', 'frags', 'spots', 'defense', 'wins'):
        got = _number(actual.get(key), True)
        reference = _number(expected.get(key), True)
        if got is None or reference is None or reference <= 0:
            return None
        ratios[key] = got / float(reference)
        if _number(ratios[key], True) is None:
            return None
    damage = max(0.0, (ratios['damage'] - 0.22) / 0.78)
    wins = max(0.0, (ratios['wins'] - 0.71) / 0.29)
    frags = max(0.0, min(damage + 0.2, (ratios['frags'] - 0.12) / 0.88))
    spots = max(0.0, min(damage + 0.1, (ratios['spots'] - 0.38) / 0.62))
    defense = max(0.0, min(damage + 0.1, (ratios['defense'] - 0.10) / 0.90))
    return _number(980.0 * damage + 210.0 * damage * frags + 155.0 * frags * spots +
                   75.0 * defense * frags + 145.0 * min(1.8, wins), True)


class ExpectedTable(object):
    def __init__(self, document):
        document = document if isinstance(document, dict) else {}
        header = document.get('header', {})
        header = header if isinstance(header, dict) else {}
        self.metadata = {'version': _text(header.get('version', document.get('version', message('unknown')))),
                         'source': 'XVM Wargaming', 'count': 0}
        raw = document.get('data', document)
        if isinstance(raw, list):
            entries = [(item.get('IDNum', item.get('id', item.get('vehicle_id'))), item)
                       for item in raw if isinstance(item, dict)]
        elif isinstance(raw, dict):
            entries = list(raw.items())
        else:
            entries = []
        self.values = {}
        for identifier, item in entries:
            if identifier is None or not isinstance(item, dict):
                continue
            fields = {}
            for key, official in (('damage', 'expDamage'), ('frags', 'expFrag'),
                                  ('spots', 'expSpot'), ('defense', 'expDef'), ('wins', 'expWinRate')):
                value = _number(item.get(official, item.get(key)), True)
                if value is None or value <= 0:
                    fields = None
                    break
                fields[key] = value / 100.0 if key == 'wins' and official in item else value
            # Expected values are rating coefficients. The WG table can contain
            # an extrapolated expWinRate above 100; preserve it, do not clamp it.
            if fields is not None:
                self.values[_text(identifier)] = fields
        self.metadata['count'] = len(self.values)

    def for_record(self, record):
        if record.get('vehicle_id') is None or record.get('outcome') not in _OUTCOMES:
            return None
        expected = self.values.get(_text(record['vehicle_id']))
        if expected is None or any(record.get(key) is None for key in ('damage', 'frags', 'spots', 'defense')):
            return None
        return expected


def _money(records, currency):
    money = {}
    for key in ('income', 'costs', 'net'):
        values = [record.get('currencies', {}).get(currency, {}).get(key) for record in records]
        known = [value for value in values if value is not None]
        money[key] = _number(sum(known)) if known else None
        money[key + '_count'] = len(known)
    money['breakdown'] = {}
    money['breakdown_counts'] = {}
    for key in _BREAKDOWN:
        values = [record.get('currencies', {}).get(currency, {}).get('breakdown', {}).get(key)
                  for record in records]
        known = [value for value in values if value is not None]
        money['breakdown'][key] = _number(sum(known)) if known else None
        money['breakdown_counts'][key] = len(known)
    return money


def aggregate_stats(records, expected_table):
    observed = [record for record in records if record.get('mode') in (None, 'random')]
    records = [record for record in observed if record.get('mode') == 'random' and record.get('outcome') in _OUTCOMES]
    table = expected_table if isinstance(expected_table, ExpectedTable) else ExpectedTable(expected_table)
    count = len(records)
    stats = {'battles': count, 'observed_battles': len(observed),
             'missing_results': len(observed) - count,
             'partial_results': sum(1 for record in records if not record.get('complete')),
             'wins': sum(1 for record in records if record['outcome'] == 'win'),
             'losses': sum(1 for record in records if record['outcome'] == 'loss'),
             'draws': sum(1 for record in records if record['outcome'] == 'draw')}
    stats['win_rate'] = stats['wins'] * 100.0 / count if count else None
    for key in ('xp_base', 'xp_received', 'free_xp'):
        stats[key] = _series([record.get(key) for record in records])
    stats['credits_net'] = _series([record.get('currencies', {}).get('credits', {}).get('net') for record in records])
    actual = dict((key, 0.0) for key in ('damage', 'frags', 'spots', 'defense', 'wins'))
    reference = dict((key, 0.0) for key in actual)
    per_battle = []
    for record in records:
        expected = table.for_record(record)
        if expected is None:
            continue
        values = dict((key, record.get(key)) for key in ('damage', 'frags', 'spots', 'defense'))
        values['wins'] = 1 if record['outcome'] == 'win' else 0
        rating = wn8_from_totals(values, expected)
        if rating is None:
            continue
        for key in actual:
            actual[key] += values[key]
            reference[key] += expected[key]
        per_battle.append(rating)
    stats['wn8_count'] = len(per_battle)
    stats['wn8'] = wn8_from_totals(actual, reference) if per_battle else None
    stats['battle_wn8'] = _series(per_battle)
    stats['currencies'] = dict((currency, _money(records, currency)) for currency in _CURRENCIES)
    return stats


def _clean_record(record):
    if not isinstance(record, dict) or record.get('arena_id') is None:
        raise ValueError(message('core.missing_id'))
    clean = {'arena_id': _text(record['arena_id'])}
    if not clean['arena_id'] or len(clean['arena_id']) > 128:
        raise ValueError(message('core.invalid_id'))
    for key in ('started_at', 'ended_at') + _NUMBERS:
        if key in record:
            clean[key] = _number(record[key], True)
    for key in ('vehicle_id', 'vehicle_tier'):
        if key in record:
            value = _number(record[key], True)
            clean[key] = int(value) if value is not None and int(value) == value else None
    for key in ('vehicle_name', 'vehicle_type', 'map_id', 'map_name', 'mode'):
        if key in record:
            clean[key] = _text(record[key]) if record[key] is not None else None
    if 'outcome' in record:
        clean['outcome'] = record['outcome'] if record['outcome'] in _OUTCOMES else None
    if 'complete' in record:
        clean['complete'] = record['complete'] is True
    if 'reconcile' in record:
        clean['reconcile'] = record['reconcile'] is True
    if 'xp_bonus_applied' in record:
        clean['xp_bonus_applied'] = record['xp_bonus_applied'] is True
    if 'warnings' in record:
        warnings = record['warnings'] if isinstance(record['warnings'], (list, tuple)) else []
        clean['warnings'] = [_text(warning)[:240] for warning in warnings[:40]]
    if isinstance(record.get('currencies'), dict):
        clean['currencies'] = {}
        for currency in _CURRENCIES:
            incoming = record['currencies'].get(currency)
            if not isinstance(incoming, dict):
                continue
            values = {}
            for key in ('income', 'costs', 'net'):
                if key in incoming:
                    # The client's after-penalty income can be negative.
                    # Costs alone must be nonnegative; do not erase a fine.
                    values[key] = _number(incoming[key], key == 'costs')
            if isinstance(incoming.get('breakdown'), dict):
                values['breakdown'] = dict((key, _number(incoming['breakdown'][key], True))
                                           for key in _BREAKDOWN if key in incoming['breakdown'])
            clean['currencies'][currency] = values
    details = clean_details(record.get('details'))
    if details:
        clean['details'] = details
    return clean


def _merge_known(existing, incoming, revise=False):
    """Unknown updates never erase facts; authoritative readings may revise."""
    merged = copy.deepcopy(existing)
    for key, value in incoming.items():
        if key in ('complete', 'xp_bonus_applied'):
            merged[key] = bool(merged.get(key)) or bool(value)
        elif key == 'warnings':
            merged[key] = list(value) if revise else sorted(set(merged.get(key, []) + value))
        elif key == 'details':
            merged[key] = merge_details(merged.get(key, {}), value, revise)
        elif isinstance(value, dict):
            merged[key] = _merge_known(merged.get(key, {}) or {}, value, revise)
        elif value is not None and (revise or merged.get(key) is None):
            merged[key] = value
        elif key not in merged:
            merged[key] = value
    return merged


class StatsService(object):
    def __init__(self, data_dir, account_key, launch_id, expected_table, now=None,
                 deferred=False, started_at=None, timeline_enabled=False):
        self.account_key = _text(account_key)
        self.launch_id = self._requested_launch = _text(launch_id)
        self._now = now or time.time
        self.expected_table = ExpectedTable(expected_table)
        account_dir = hashlib.sha256(self.account_key.encode('utf-8')).hexdigest()
        self.store = GenerationStore(os.path.join(data_dir, account_dir))
        self.last_error = None
        self._warnings = []
        self._indexes = None
        self._timeline_enabled = timeline_enabled
        self._timeline_range = ('', '')
        self._timeline_dates = (None, None)
        self._timeline_bounds = (0, None)
        self._filtered_timeline = None
        self._timeline_job = None
        self._timeline_error = None
        self._pages = {}
        self._page_requests = {}
        self._empty_view_revision = uuid.uuid4().hex
        self._orders = {}
        self._map_pages = {}
        self._vehicle_pages = {}
        self._history_request = {}
        self._battle_focus = {}
        self._receipt = None
        self._intake = None
        self._received_context = {}
        self._received_records = {}
        self._pending_ids = set()
        self._unassigned = 0
        self.loading, self.ready, self._closed = True, False, False
        self.loading_phase = 'history'
        current_time = self._time() if started_at is None else _number(started_at, True)
        if current_time is None:
            raise ValueError(message('core.time'))
        self._initial_time = current_time
        self._state = self._empty_state(current_time)
        try:
            if deferred or os.path.isdir(os.path.join(self.store.directory, 'startup-intake')):
                from .intake import Intake
                self._intake = Intake(self.store.directory, self.account_key)
                self._intake.append('open', self._requested_launch, current_time)
                if self._intake.store.warning:
                    self._warnings.append(self._intake.store.warning)
        except (StorageError, IOError, OSError, ValueError, TypeError) as error:
            self._fail_loading(error)
        self._loader = self._initialize_steps() if self.loading else None
        if not deferred:
            while self.loading:
                self.advance_loading(budget=1.0)

    def _fail_loading(self, error):
        self.store.read_only = True
        self.loading, self.ready = False, False
        self.last_error = _text(error) if isinstance(error, StorageError) else message('core.load')

    def advance_loading(self, budget=0.002, max_steps=512):
        if not self.loading or self._closed:
            return False
        timer = getattr(time, 'perf_counter', time.time)
        deadline = timer() + max(0, budget)
        try:
            for unused in range(max(1, max_steps)):
                try:
                    next(self._loader)
                except StopIteration:
                    self._loader = None
                    self.loading = False
                    self.ready = not self.store.read_only
                    break
                if timer() >= deadline:
                    break
        except Exception as error:
            self._fail_loading(error)
            self.cancel_loading()
        return self.loading

    def cancel_loading(self):
        self._closed = True
        self.cancel_timeline()
        if self._loader is not None:
            self._loader.close()
            self._loader = None
        self.loading = False

    def _initialize_steps(self):
        output = [None]
        for step in self.store.load_steps(output, self._validate_state_steps):
            yield step
        existing = output[0]
        if existing is not None:
            self._state = existing
        elif self._intake is not None and self._intake.events:
            first = _number(self._intake.events[0].get('at'), True)
            if first is None:
                raise StorageError(message('core.time'))
            self._state = self._empty_state(first)
        if self.store.warning:
            self._warnings.append(self.store.warning)
        if existing is not None:
            self.loading_phase = 'storage'
            for step in self.store.prepare_steps():
                yield step
        self.loading_phase = 'receipts'
        if self._intake is not None:
            for step in self._drain_intake_steps():
                yield step
        else:
            for step in self._open_launch_steps(self._requested_launch, self._initial_time):
                yield step
        for step in self.store.prepare_steps():
            yield step
        self.launch_id = self._requested_launch
        self.loading_phase = 'indexes'
        for step in self._rebuild_indexes_steps():
            yield step
        self.loading_phase = 'receipts'
        for step in self._drain_intake_steps():
            yield step
        self.launch_id = self._requested_launch
        self._received_context.clear()
        self._received_records.clear()
        self.last_error = None
        self.loading_phase = 'ready'

    def _open_launch_steps(self, launch_id, current_time):
        self.launch_id = launch_id
        candidate = self._candidate()
        manual = candidate['manual_sessions'][-1]
        latest = self._last_seen(manual)
        for position, battle in enumerate(values(candidate['battles'])):
            latest = max(latest, battle.get('_updated_at', 0))
            if position % 128 == 0:
                yield None
        for epoch in candidate['launch_sessions']:
            latest = max(latest, self._last_seen(epoch))
            yield None
        manual['last_seen_at'] = latest
        found = self._launch(candidate, launch_id)
        if found is None:
            launch_start = current_time
            for previous in candidate['launch_sessions']:
                if previous.get('ended_at') is None:
                    previous['ended_at'] = self._last_seen(previous)
                launch_start = max(launch_start, previous['ended_at'])
                yield None
            candidate['launch_sessions'].append({'id': launch_id, 'started_at': launch_start,
                                                 'last_seen_at': launch_start, 'ended_at': None})
        elif found.get('ended_at') is not None:
            raise StorageError(message('core.closed'))
        if not self.store.sequence or candidate != self._state or self._receipt is not None:
            if not self._commit(candidate, {} if self.store.sequence else None):
                raise StorageError(self.last_error or message('core.create'))

    def _drain_intake_steps(self):
        if self._intake is None:
            return
        while self._intake.events:
            event = self._intake.events[0]
            producer, sequence = event['producer'], event['sequence']
            acknowledged = self._state.get('_startup_receipts', {}).get(producer, 0)
            if sequence > acknowledged:
                timestamp = _number(event.get('at'), True)
                if timestamp is None:
                    raise StorageError(message('core.time'))
                self._receipt = (producer, sequence)
                self.last_error = None
                try:
                    self.launch_id = event['launch_id']
                    if event['kind'] == 'open':
                        for step in self._open_launch_steps(event['launch_id'], timestamp):
                            yield step
                    else:
                        if self._launch(self._state, event['launch_id']) is None:
                            raise StorageError('Startup receipt has no launch boundary.')
                        record = dict(event['record'])
                        context = event.get('context', {})
                        stored = self.result_context(record['arena_id'], include_received=False)
                        candidates = context.get('candidates', [])
                        if candidates:
                            matching = [item for item in candidates if stored.get('vehicle_id') is not None and
                                        item['record'].get('vehicle_id') == stored['vehicle_id']]
                            if len(matching) == 1:
                                record = dict(matching[0]['record'])
                                context = dict(matching[0].get('context', {}), require_known=context.get('require_known', False))
                            else:
                                record['warnings'] = [message('runtime.results')]
                        for field in context.get('fields', []):
                            if field in stored:
                                record[field] = stored[field]
                        if 'started_at' in context.get('fields', []) and record.get('started_at') is not None:
                            duration = _number(context.get('duration'), True)
                            if duration is not None:
                                record['ended_at'] = record['started_at'] + duration
                        if not context.get('require_known') or record['arena_id'] in self._state['battles']:
                            self._apply(record, timestamp, event['kind'] == 'result')
                    if self.last_error:
                        raise StorageError(self.last_error)
                    if self._state.get('_startup_receipts', {}).get(producer, 0) < sequence:
                        if not self._commit(self._candidate(), {}):
                            raise StorageError(self.last_error)
                finally:
                    self._receipt = None
            # The watermark and battle were committed together. If this cleanup
            # fails or the process dies here, replay skips the acknowledged event.
            self._intake.remove(event)
            yield None

    def _queue_record(self, record, timestamp, is_result):
        try:
            if self._intake is None or self._closed or self.store.read_only:
                raise StorageError(message('storage.readonly'))
            context = copy.deepcopy(record.get('_deferred_context') or {})
            if record.get('_deferred_candidates'):
                context['candidates'] = [{'record': _clean_record(candidate),
                                          'context': copy.deepcopy(candidate.get('_deferred_context', {}))}
                                         for candidate in record['_deferred_candidates']]
            if record.get('_require_known'):
                context['require_known'] = True
            cleaned = _clean_record(record)
            key = (is_result, cleaned['arena_id'])
            if self._received_records.get(key) == (cleaned, context):
                return False
            self._intake.append('result' if is_result else 'begin', self._requested_launch,
                                timestamp, cleaned, context)
            self._received_records[key] = (cleaned, context)
            self._received_context.setdefault(cleaned['arena_id'], {}).update(
                (field, value) for field, value in cleaned.items() if value is not None)
            self.last_error = None
            return True
        except (StorageError, ValueError, TypeError, OverflowError) as error:
            self.last_error = _text(error)
            return False

    def _rebuild_indexes(self):
        complete(self._rebuild_indexes_steps())

    def _rebuild_indexes_steps(self):
        from .projection import ScopeIndex, contribution
        self._indexes = {
            'launch': ScopeIndex(self.launch_id, self.expected_table),
            'manual': ScopeIndex(self._state['current_manual_id'], self.expected_table)}
        if self._timeline_enabled:
            self._indexes['timeline'] = ScopeIndex('timeline', self.expected_table)
        self._pending_ids = set()
        self._unassigned = 0
        members = dict((name, []) for name in self._indexes)
        for record in values(self._state['battles']):
            if record.get('mode') not in (None, 'random'):
                continue
            if self._pending(record):
                self._pending_ids.add(record['arena_id'])
            if record.get('_manual_id') is None or record.get('_launch_id') is None:
                self._unassigned += 1
            item = None
            for name, field in (('launch', '_launch_id'), ('manual', '_manual_id')):
                if record.get(field) == self._indexes[name].identifier:
                    if item is None:
                        item = contribution(record, self.expected_table)
                    members[name].append(item)
            if self._timeline_enabled:
                members['timeline'].append(item or contribution(record, self.expected_table))
            yield None
        for name, index in self._indexes.items():
            for step in index.build_steps(members[name]):
                yield step

    def _index_record(self, record, item):
        if record.get('mode') not in (None, 'random'):
            return
        identifier = record['arena_id']
        self._pending_ids.discard(identifier)
        if self._pending(record):
            self._pending_ids.add(identifier)
        for name, field in (('launch', '_launch_id'), ('manual', '_manual_id')):
            index = self._indexes[name]
            if record.get(field) == index.identifier:
                index.replace(record, item)
        if self._timeline_enabled:
            self._indexes['timeline'].replace(record, item)
            filtered = self._filtered_timeline or (self._timeline_job or {}).get('index')
            if filtered is not None:
                self._update_timeline_record(filtered, record, item)
        if record.get('_manual_id') is None or record.get('_launch_id') is None:
            self._unassigned += 1

    def _view_index(self, scope):
        if scope == 'timeline' and self._timeline_enabled:
            return self._timeline_index()
        if scope in ('launch', 'manual'):
            return self._indexes[scope]
        return None

    def set_page(self, scope, group, page, period_id=None, request_id=None):
        if not self.ready or self._closed:
            return False
        if group not in ('battles', 'vehicles', 'maps', 'tiers'):
            return False
        index = self._view_index(scope)
        if index is None:
            return False
        if period_id is not None and period_id != index.identifier:
            return False
        if request_id is not None:
            if not isinstance(request_id, (text_type, bytes)):
                return False
            request_id = _text(request_id)
            if (not 1 <= len(request_id) <= 64 or any(char not in
                    'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.:-' for char in request_id)):
                return False
        self._pages.setdefault(scope, {})[group] = page
        requests = self._page_requests.setdefault(scope, {})
        if request_id is None:
            requests.pop(group, None)
        else:
            requests[group] = {'period_id': index.identifier, 'request_id': request_id}
        self._battle_focus.pop(scope, None)
        return True

    def set_order(self, scope, group, options, period_id):
        from .projection import valid_order
        if (not valid_order(options, group) or not self.ready or self._closed or
                group not in ('battles', 'vehicles', 'maps', 'tiers')):
            return False
        index = self._view_index(scope)
        if index is None or period_id != index.identifier:
            return False
        self._orders.setdefault(scope, {})[group] = dict(options)
        self._pages.setdefault(scope, {})[group] = 0
        self._page_requests.get(scope, {}).pop(group, None)
        self._battle_focus.pop(scope, None)
        return True

    def set_map_battles(self, scope, map_id, page, period_id):
        return self._set_group_battles(scope, 'maps', map_id, page, period_id, self._map_pages)

    def set_vehicle_battles(self, scope, vehicle_id, page, period_id):
        return self._set_group_battles(scope, 'vehicles', vehicle_id, page, period_id, self._vehicle_pages)

    def _set_group_battles(self, scope, kind, group_id, page, period_id, opened):
        if (not self.ready or self._closed or not isinstance(group_id, (text_type, bytes)) or
                isinstance(page, bool) or not isinstance(page, int) or not 0 <= page < 10 ** 8):
            return False
        index = self._view_index(scope)
        group_id = _text(group_id)
        if index is None or period_id != index.identifier or group_id not in index.groups[kind]:
            return False
        current = opened.get(scope)
        if current is None or current['period_id'] != period_id:
            current = {'period_id': period_id, 'pages': {}}
            opened[scope] = current
        current['pages'][group_id] = page
        self._history_request[scope] = {'period_id': period_id, 'kind': kind, 'id': group_id, 'page': page}
        return True

    def select_battle(self, scope, identifier, period_id, request_id):
        if (not self.ready or self._closed or
                not isinstance(identifier, (text_type, bytes)) or
                not isinstance(request_id, (text_type, bytes))):
            return False
        identifier, request_id = _text(identifier), _text(request_id)
        if (not 1 <= len(request_id) <= 64 or any(char not in
                'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.:-' for char in request_id)):
            return False
        index = self._view_index(scope)
        if index is None or period_id != index.identifier:
            return False
        page = index.battle_page(identifier, self._orders.get(scope, {}).get('battles'))
        if page is None:
            return False
        self._pages.setdefault(scope, {})['battles'] = page
        self._page_requests.get(scope, {}).pop('battles', None)
        self._battle_focus[scope] = {'period_id': period_id, 'id': identifier, 'request_id': request_id}
        return True

    def _scope_snapshot(self, name, index, label, started_at):
        opened = self._map_pages.get(name, {})
        map_pages = opened.get('pages') if opened.get('period_id') == index.identifier else None
        vehicles = self._vehicle_pages.get(name, {})
        vehicle_pages = vehicles.get('pages') if vehicles.get('period_id') == index.identifier else None
        scope = index.snapshot(label, started_at, self._pages.get(name), self._orders.get(name), map_pages, vehicle_pages)
        history = self._history_request.get(name)
        if history and history['period_id'] == index.identifier:
            battle_list = index._group_battles(history['kind'], history['id'], history['page'])
            if battle_list is not None:
                scope['battle_history'] = {'kind': history['kind'], 'id': history['id'], 'battle_list': battle_list}
        for group, request in self._page_requests.get(name, {}).items():
            if request['period_id'] == index.identifier:
                scope['pagination'][group]['request_id'] = request['request_id']
        focus = self._battle_focus.get(name)
        if (focus and focus['period_id'] == index.identifier and
                any(row['id'] == focus['id'] for row in scope['battles'])):
            scope['battle_focus'] = dict((key, focus[key]) for key in ('id', 'request_id'))
        return scope

    def _time(self):
        value = _number(self._now(), True)
        if value is None:
            raise ValueError(message('core.time'))
        return value

    def _empty_state(self, timestamp):
        manual_id = uuid.uuid4().hex
        return {'schema_version': SCHEMA_VERSION, 'account_key': self.account_key,
                'launch_sessions': [],
                'manual_sessions': [{'id': manual_id, 'started_at': timestamp,
                                     'last_seen_at': timestamp, 'ended_at': None}],
                'current_manual_id': manual_id, 'battles': {}}

    def _validate_state(self, state):
        complete(self._validate_state_steps(state))

    def _validate_state_steps(self, state):
        if state.get('account_key') != self.account_key:
            raise StorageError(message('core.account'))
        if not isinstance(state.get('battles'), dict) or not isinstance(state.get('launch_sessions'), list):
            raise StorageError(message('core.ledger'))
        if not isinstance(state.get('manual_sessions'), list) or not state['manual_sessions']:
            raise StorageError(message('core.periods'))
        period_ids = {}
        for kind in ('launch_sessions', 'manual_sessions'):
            periods = state[kind]
            identifiers = set()
            period_ids[kind] = identifiers
            previous = None
            for epoch in periods:
                if (not isinstance(epoch, dict) or not isinstance(epoch.get('id'), text_type)
                        or not epoch['id'] or epoch['id'] in identifiers
                        or _number(epoch.get('started_at'), True) is None):
                    raise StorageError(message('core.boundaries'))
                identifiers.add(epoch['id'])
                for key in ('ended_at', 'last_seen_at'):
                    if epoch.get(key) is not None and _number(epoch[key], True) is None:
                        raise StorageError(message('core.boundaries'))
                # A numeric boundary can still reverse/truncate the interval.
                # Reject it before selection and before crash closure writes it.
                last_seen = self._last_seen(epoch)
                ended = epoch.get('ended_at')
                if (last_seen < epoch['started_at'] or
                        (ended is not None and (ended < epoch['started_at'] or last_seen > ended))):
                    raise StorageError(message('core.boundaries'))
                if previous is not None and (previous.get('ended_at') is None or
                        epoch['started_at'] < previous['ended_at']):
                    raise StorageError(message('core.boundaries'))
                previous = epoch
                yield None
        manual_periods = state['manual_sessions']
        if (state.get('current_manual_id') != manual_periods[-1]['id']
                or manual_periods[-1].get('ended_at') is not None
                or any(epoch.get('ended_at') is None for epoch in manual_periods[:-1])):
            raise StorageError(message('core.current'))
        points = state.get('time_points', {})
        if not isinstance(points, dict) or len(points) > MAX_TIME_POINTS:
            raise StorageError(message('core.boundaries'))
        for identifier, at in items(points):
            if (not isinstance(identifier, text_type) or len(identifier) != 32 or
                    any(char not in '0123456789abcdef' for char in identifier) or
                    identifier in period_ids['manual_sessions'] or _number(at, True) is None):
                raise StorageError(message('core.boundaries'))
            yield None
        names = state.get('time_point_names', {})
        if not isinstance(names, dict) or len(names) > len(points):
            raise StorageError(message('core.boundaries'))
        for identifier, name in items(names):
            if (identifier not in points or not isinstance(name, text_type) or
                    not name.strip() or len(name) > 80 or any(ord(char) < 32 for char in name)):
                raise StorageError(message('core.boundaries'))
            yield None
        receipts = state.get('_startup_receipts', {})
        if not isinstance(receipts, dict):
            raise StorageError(message('core.ledger'))
        for producer, sequence in items(receipts):
            if (not isinstance(producer, text_type) or len(producer) != 32 or
                    any(char not in '0123456789abcdef' for char in producer) or
                    isinstance(sequence, bool) or not isinstance(sequence, number_types[:2] if len(number_types) == 3 else (int,)) or sequence < 1):
                raise StorageError(message('core.ledger'))
            yield None
        for arena_id, battle in items(state['battles']):
            if not isinstance(battle, dict) or battle.get('arena_id') != arena_id:
                raise StorageError(message('core.battle'))
            # Validate the same optional fields that later merges, summaries and
            # sorting consume. Never repair a rejected generation in place.
            clean = _clean_record(battle)
            for key in ('started_at', 'ended_at') + _NUMBERS + ('vehicle_id', 'vehicle_tier',
                    'vehicle_name', 'vehicle_type', 'map_id', 'map_name', 'mode', 'outcome',
                    'warnings', 'currencies', 'details'):
                if key in battle and (key not in clean or battle[key] != clean[key]):
                    raise StorageError(message('core.battle'))
            for key in ('complete', 'xp_bonus_applied', '_result_seen'):
                if key in battle and not isinstance(battle[key], bool):
                    raise StorageError(message('core.battle'))
            for key in ('revision', '_updated_at'):
                if key in battle and _number(battle[key], True) is None:
                    raise StorageError(message('core.battle'))
            for key, kind in (('_manual_id', 'manual_sessions'), ('_launch_id', 'launch_sessions')):
                if battle.get(key) is not None and (not isinstance(battle[key], text_type)
                        or battle[key] not in period_ids[kind]):
                    raise StorageError(message('core.battle'))

            yield None

    @staticmethod
    def _last_seen(epoch):
        value = epoch.get('last_seen_at')
        return epoch['started_at'] if value is None else value

    @staticmethod
    def _launch(state, identifier):
        for epoch in state['launch_sessions']:
            if epoch['id'] == identifier:
                return epoch
        return None

    def _candidate(self):
        candidate = dict(self._state)
        candidate['launch_sessions'] = copy.deepcopy(self._state['launch_sessions'])
        candidate['manual_sessions'] = copy.deepcopy(self._state['manual_sessions'])
        return candidate

    def _commit(self, candidate, changes=None):
        try:
            if self._receipt is not None:
                producer, sequence = self._receipt
                candidate['_startup_receipts'] = dict(candidate.get('_startup_receipts', {}))
                candidate['_startup_receipts'][producer] = sequence
            payload = candidate
            if changes is not None:
                kinds = ('launch_sessions', 'manual_sessions')
                periods = {}
                for kind in kinds:
                    old, new = self._state[kind], candidate[kind]
                    entries = dict((_text(position), period) for position, period in enumerate(new)
                                   if position >= len(old) or period != old[position])
                    if entries:
                        periods[kind] = {'length': len(new), 'entries': entries}
                payload = StateDelta(dict((key, value) for key, value in candidate.items()
                                          if key not in kinds + ('battles',)), changes, periods)
            self.store.save(payload)
        except StorageError as error:
            self.last_error = _text(error)
            return False
        self._state = candidate
        self.last_error = None
        return True

    def _touch(self, candidate, timestamp):
        # Activity is observed at commit time, independently of the battle's
        # historical memberships. Both active periods protect reset boundaries.
        for epoch in (self._launch(candidate, self.launch_id), candidate['manual_sessions'][-1]):
            if epoch is not None:
                epoch['last_seen_at'] = max(self._last_seen(epoch), timestamp)

    def _memberships(self, timestamp, current_time):
        if timestamp is None or timestamp > current_time:
            return None, None
        manual_id = None
        launch_id = None
        for epoch in reversed(self._state['manual_sessions']):
            if timestamp >= epoch['started_at'] and (epoch.get('ended_at') is None or timestamp < epoch['ended_at']):
                manual_id = epoch['id']
                break
        # Launch activity includes its last observed instant. At a touching
        # boundary, historical evidence wins over an unseen result-only reading.
        # Live begin_battle observations still explicitly select this launch.
        for epoch in self._state['launch_sessions']:
            if timestamp < epoch['started_at']:
                continue
            if epoch['id'] == self.launch_id and epoch.get('ended_at') is None:
                launch_id = epoch['id']
                break
            if timestamp <= self._last_seen(epoch):
                launch_id = epoch['id']
                break
        return launch_id, manual_id

    def begin_battle(self, arena_id, started_at=None, vehicle_id=None, map_id=None, mode=None,
                     vehicle_name=None, vehicle_tier=None, vehicle_type=None, map_name=None, details=None):
        if self._closed or (not self.ready and not self.loading):
            self.last_error = self.last_error or message('storage.readonly')
            return False
        if mode not in (None, 'random'):
            return False
        timestamp = self._time()
        record = {'arena_id': arena_id, 'started_at': timestamp if started_at is None else started_at,
                  'vehicle_id': vehicle_id, 'map_id': map_id, 'mode': mode, 'complete': False,
                  'vehicle_name': vehicle_name, 'vehicle_tier': vehicle_tier,
                  'vehicle_type': vehicle_type, 'map_name': map_name, 'details': details}
        if self.loading:
            return self._queue_record(record, timestamp, False)
        return self._apply(record, timestamp, is_result=False)

    def record_result(self, record):
        if self._closed or (not self.ready and not self.loading):
            self.last_error = self.last_error or message('storage.readonly')
            return False
        if not isinstance(record, dict):
            self.last_error = message('core.result')
            return False
        if record.get('mode') not in (None, 'random') or record.get('is_replay') or record.get('isReplay'):
            return False
        if self.loading:
            return self._queue_record(record, self._time(), True)
        return self._apply(record, self._time(), is_result=True)

    def result_context(self, arena_id, include_received=True):
        """Known metadata for one result, including after a client restart.

        Presentation fallbacks must not replace previously resolved names or
        map identities when a later client no longer supplies that metadata.
        Return only contextual fields, never a mutable reference to the ledger.
        """
        record = dict(self._state['battles'].get(_text(arena_id), {}))
        if include_received and self.loading:
            record.update(self._received_context.get(_text(arena_id), {}))
        fields = ('started_at', 'vehicle_id', 'vehicle_name', 'vehicle_tier',
                  'vehicle_type', 'map_id', 'map_name')
        context = dict((key, record[key]) for key in fields if record.get(key) is not None)
        details = record.get('details', {})
        if details.get('active_crucible'):
            context['active_crucible'] = details['active_crucible']
        return context

    def battle_rating(self, arena_id):
        """Read one account-local battle rating without projecting its history.

        A result can have a usable WN8 while XP or financial recovery continues.
        Only rating inputs and the bundled expected table determine readiness.
        """
        answer = {'account_key': self.account_key, 'arena_id': '',
                  'status': 'unavailable', 'wn8': None}
        if isinstance(arena_id, bool) or not isinstance(arena_id, (text_type, bytes) + number_types[:-1]):
            return answer
        try:
            identifier = _text(arena_id)
        except (ValueError, TypeError, OverflowError):
            return answer
        if not identifier or len(identifier) > 128:
            return answer
        answer['arena_id'] = identifier
        if self._closed:
            return answer
        if self.loading:
            answer['status'] = 'pending'
            return answer
        if not self.ready:
            return answer
        record = self._state['battles'].get(identifier)
        if not record or record.get('mode') not in (None, 'random') or not self.expected_table.values:
            return answer
        vehicle_id = record.get('vehicle_id')
        if vehicle_id is not None and _text(vehicle_id) not in self.expected_table.values:
            return answer
        from .projection import contribution
        rating = contribution(record, self.expected_table)[1]
        if _number(rating, True) is not None:
            answer['status'], answer['wn8'] = 'ready', rating
        elif not record.get('_result_seen') or not record.get('complete'):
            answer['status'] = 'pending'
        return answer

    def _apply(self, record, timestamp, is_result):
        try:
            incoming = _clean_record(record)
        except (ValueError, TypeError, OverflowError) as error:
            self.last_error = _text(error)
            return False
        arena_id = incoming['arena_id']
        old = self._state['battles'].get(arena_id, {})
        # Authority and completeness are separate: a new XP bonus can arrive
        # while a currency is unavailable. This control flag is not ledger data.
        revise = incoming.pop('reconcile', False)
        # The raw server-result cache may predate an already applied premium XP
        # bonus even after restart. Only another bonus-aware reading can revise it.
        if old.get('xp_bonus_applied') and not incoming.get('xp_bonus_applied'):
            incoming.pop('xp_received', None)
        merged = _merge_known(old, incoming, revise)
        if merged.get('mode') not in (None, 'random'):
            return False
        if old:
            # A known beginning is authoritative even if a result arrives later.
            if old.get('_launch_id') is not None:
                merged['_launch_id'] = old['_launch_id']
            if old.get('_manual_id') is not None:
                merged['_manual_id'] = old['_manual_id']
        started_at = merged.get('started_at')
        # A live observation proves that a valid server timestamp is not a
        # future battle, even when the local clock lags. Keep known reset
        # boundaries authoritative when choosing its manual period.
        membership_time = (max(started_at, timestamp)
                           if not is_result and started_at is not None else timestamp)
        launch_id, manual_id = self._memberships(started_at, membership_time)
        if not is_result and started_at is not None:
            # begin_battle is a live observation, unlike a delayed cache result.
            # It can precede service creation (late initialization/reconnect).
            # Existing durable memberships below still take precedence.
            launch_id = self.launch_id
            if (manual_id is None and len(self._state['manual_sessions']) == 1
                    and started_at < self._state['manual_sessions'][0]['started_at']):
                manual_id = self._state['current_manual_id']
        if merged.get('_launch_id') is None:
            merged['_launch_id'] = launch_id
        if merged.get('_manual_id') is None:
            merged['_manual_id'] = manual_id
        merged['_result_seen'] = bool(old.get('_result_seen')) or is_result
        merged.setdefault('complete', False)
        merged.setdefault('warnings', [])
        # Infer a net value only when both components are confirmed. Reconcile it
        # when an authoritative update revises a component but does not supply net.
        for currency, values in merged.get('currencies', {}).items():
            update = incoming.get('currencies', {}).get(currency, {})
            has_components = values.get('income') is not None and values.get('costs') is not None
            if has_components and (values.get('net') is None or
                                   (revise and update.get('net') is None and
                                    (update.get('income') is not None or update.get('costs') is not None))):
                values['net'] = values['income'] - values['costs']
        if merged == old:
            return False
        merged['revision'] = old.get('revision', 0) + 1
        merged['_updated_at'] = timestamp
        candidate = self._candidate()
        self._touch(candidate, timestamp)
        if not self._commit(candidate, {arena_id: merged}):
            return False
        # Publish the single immutable replacement only after durable commit.
        candidate['battles'][arena_id] = merged
        if self._indexes is not None:
            from .projection import contribution
            if old and (old.get('_manual_id') is None or old.get('_launch_id') is None):
                self._unassigned -= 1
            self._index_record(merged, contribution(merged, self.expected_table))
        return True

    def reset_manual(self, now=None):
        if self.loading or self._closed:
            self.last_error = self.last_error or message('core.loading')
            return None
        timestamp = self._time() if now is None else _number(now, True)
        active = self._state['manual_sessions'][-1]
        if timestamp is None or timestamp < self._last_seen(active):
            self.last_error = message('core.reset_time')
            return None
        new_id = uuid.uuid4().hex
        candidate = self._candidate()
        candidate['manual_sessions'][-1]['ended_at'] = timestamp
        candidate['manual_sessions'].append({'id': new_id, 'started_at': timestamp, 'ended_at': None})
        candidate['current_manual_id'] = new_id
        self._touch(candidate, timestamp)
        if not self._commit(candidate, {}):
            return None
        from .projection import ScopeIndex
        self._indexes['manual'] = ScopeIndex(new_id, self.expected_table)
        self._pages.pop('manual', None)
        self._page_requests.pop('manual', None)
        self._map_pages.pop('manual', None)
        self._vehicle_pages.pop('manual', None)
        self._history_request.pop('manual', None)
        self._battle_focus.pop('manual', None)
        return new_id

    def _time_points(self):
        points = dict((epoch['id'], epoch['started_at']) for epoch in self._state['manual_sessions'][1:])
        points.update(self._state.get('time_points', {}))
        return points

    def create_time_point(self, name=None):
        if not self._timeline_enabled or not self.ready or self._closed:
            return False
        if name is not None:
            if not isinstance(name, (text_type, bytes)):
                return False
            name = _text(name).strip()
            if len(name) > 80 or any(ord(char) < 32 for char in name):
                self.last_error = message('timeline.create_error')
                return False
        points = self._state.get('time_points', {})
        timestamp = self._time()
        if len(points) >= MAX_TIME_POINTS:
            self.last_error = message('timeline.create_error')
            return False
        candidate = self._candidate()
        candidate['time_points'] = dict(points)
        identifier = _text(uuid.uuid4().hex)
        candidate['time_points'][identifier] = timestamp
        if name:
            candidate['time_point_names'] = dict(self._state.get('time_point_names', {}))
            candidate['time_point_names'][identifier] = name
        return self._commit(candidate, {})

    def set_timeline_range(self, start, end, from_date=None, to_date=None):
        if not self._timeline_enabled or not self.ready or self._closed:
            return False
        if not all(isinstance(value, (text_type, bytes)) for value in (start, end)):
            return False
        start, end = _text(start), _text(end)
        points = self._time_points()
        custom = '__custom__'
        if ((start and start != custom and start not in points) or
                (end and end != custom and end not in points)):
            return False
        dates = []
        for point, supplied in ((start, from_date), (end, to_date)):
            value = _number(supplied, True) if point == custom else None
            if (point == custom and value is None) or (point != custom and supplied is not None):
                return False
            dates.append(float(value) if value is not None else None)
        lower = dates[0] if start == custom else points.get(start, 0)
        upper = dates[1] if end == custom else points[end] if end else None
        if upper is not None and lower >= upper:
            return False
        selected = (start, end)
        dates = tuple(dates)
        if selected != self._timeline_range or dates != self._timeline_dates or self._timeline_error:
            self.cancel_timeline()
            self._timeline_range = selected
            self._timeline_dates = dates
            self._timeline_bounds = (lower, upper)
            self._filtered_timeline = None
            self._timeline_error = None
            self._pages.pop('timeline', None)
            self._page_requests.pop('timeline', None)
            self._map_pages.pop('timeline', None)
            self._vehicle_pages.pop('timeline', None)
            self._history_request.pop('timeline', None)
            self._battle_focus.pop('timeline', None)
            if start or end:
                from .projection import ScopeIndex
                self._timeline_job = {
                    'index': ScopeIndex(self._timeline_period_id(), self.expected_table),
                    'lower': self._timeline_bounds[0], 'upper': self._timeline_bounds[1],
                    'cursor': None}
        return True

    def _timeline_period_id(self):
        start, end = self._timeline_range
        if not start and not end:
            return 'timeline'
        identifier = 'timeline:{0}:{1}'.format(start, end)
        if '__custom__' in (start, end):
            identifier += ':{0}:{1}'.format(*self._timeline_dates)
        return identifier

    @property
    def timeline_loading(self):
        return self._timeline_job is not None

    def cancel_timeline(self):
        self._timeline_job = None

    def _update_timeline_record(self, index, record, item):
        started_at = record.get('started_at')
        lower, upper = self._timeline_bounds
        member = (started_at is not None and started_at >= lower and
                  (upper is None or started_at < upper))
        if member:
            previous = index.records.get(record['arena_id'])
            # A live update can add a record before the cooperative cursor
            # reaches it. Never remove/re-add the same immutable contribution.
            if previous is None or previous[1] is not item:
                index.replace(record, item)
        else:
            index.discard(record['arena_id'])

    def advance_timeline(self, budget=0.002, max_steps=512):
        """Build the selected projection cooperatively; never publish a prefix."""
        if self._timeline_job is None or self._closed or not self.ready:
            return False
        timer = getattr(time, 'perf_counter', time.time)
        deadline = timer() + max(0, budget)
        job = self._timeline_job
        full = self._indexes['timeline']
        try:
            for unused in range(max(1, max_steps)):
                # Re-seek after each record rather than holding list offsets:
                # durable corrections can move/insert records between slices.
                position = (bisect.bisect_right(full.order, job['cursor']) if job['cursor'] is not None else
                            bisect.bisect_left(full.order, (job['lower'], '')))
                if position >= len(full.order) or (job['upper'] is not None and full.order[position][0] >= job['upper']):
                    self._filtered_timeline = job['index']
                    self._timeline_job = None
                    break
                key = full.order[position]
                job['cursor'] = key
                record, item = full.records[key[1]]
                self._update_timeline_record(job['index'], record, item)
                if timer() >= deadline:
                    break
        except Exception:
            # A projection failure must not make the durable account read-only
            # or expose partial totals as a completed selected range.
            self._timeline_job = None
            self._timeline_error = message('error.snapshot')
        return self.timeline_loading

    def _timeline_index(self):
        start, end = self._timeline_range
        if not start and not end:
            return self._indexes['timeline']
        return self._filtered_timeline

    def timeline_snapshot(self):
        if not self._timeline_enabled:
            return None
        from .projection import ScopeIndex
        ready = self.ready and not self.loading
        points = self._time_points() if ready else {}
        start, end = self._timeline_range
        index = self._timeline_index() if ready else None
        if index is None:
            identifier = self._timeline_period_id()
            index = ScopeIndex(identifier, self.expected_table)
        scope = self._scope_snapshot('timeline', index, message('scope.timeline'),
                                     self._timeline_dates[0] if start == '__custom__' else points.get(start))
        if not ready or self.timeline_loading or self._timeline_error:
            scope['data_revision'] = self._empty_view_revision
        scope['loading'] = self.timeline_loading
        if ready and self._timeline_error:
            scope['load_error'] = self._timeline_error
        scope['time_points'] = sorted(points.items(), key=lambda point: (point[1], point[0]))
        scope['time_point_names'] = dict(self._state.get('time_point_names', {})) if ready else {}
        scope['from_point'], scope['to_point'] = start, end
        scope['from_date'], scope['to_date'] = self._timeline_dates
        return scope

    def pending_arena_ids(self):
        return [] if self.loading else sorted(self._pending_ids)

    @staticmethod
    def _pending(record):
        return not record.get('complete') or record.get('outcome') not in _OUTCOMES

    def _scope(self, key, identifier, label, started_at):
        name = 'launch' if key == '_launch_id' else 'manual'
        return self._scope_snapshot(name, self._indexes[name], label, started_at)

    def launch_records(self):
        """Independent records from this account and game process only."""
        if self.loading:
            # Only beginnings durably captured by this process prove where a
            # battle was played. Restored intake and unobserved cache results
            # can belong to a different installation. During replay launch_id
            # temporarily names an earlier process, so do not use partial state.
            return [copy.deepcopy(record) for (is_result, unused), (record, context)
                    in self._received_records.items()
                    if not is_result and record.get('started_at') is not None]
        if not self.ready:
            return []
        return [copy.deepcopy(record) for record in self._state['battles'].values()
                if record.get('_launch_id') == self._requested_launch and record.get('mode') in (None, 'random')]

    def project_scope(self, records, label, started_at):
        """Project known records without changing their account/session ledger."""
        scope = {'label': label, 'started_at': started_at,
                 'pending': sum(1 for record in records if self._pending(record)),
                 'summary': aggregate_stats(records, self.expected_table), 'vehicles': [], 'maps': [], 'battles': [], 'tiers': []}
        for group_type, field, name_field in (('vehicles', 'vehicle_id', 'vehicle_name'), ('maps', 'map_id', 'map_name'), ('tiers', 'vehicle_tier', 'vehicle_tier')):
            groups = {}
            for record in records:
                identifier = _text(record[field]) if record.get(field) is not None else '__unknown__'
                groups.setdefault(identifier, []).append(record)
            for identifier, group_records in groups.items():
                named = [row for row in group_records if row.get(name_field)]
                latest = max(named or group_records, key=lambda row: row.get('_updated_at', 0))
                fallback = message('unknown.vehicle') if group_type == 'vehicles' else message('unknown.map')
                group = {'id': identifier, 'name': latest.get(name_field) or fallback,
                         'tier': latest.get('vehicle_tier') if group_type == 'vehicles' else None,
                         'type': latest.get('vehicle_type') if group_type == 'vehicles' else None,
                         'stats': aggregate_stats(group_records, self.expected_table)}
                if group_type == 'tiers':
                    from .projection import tier_name
                    group['tier'] = latest.get('vehicle_tier')
                    group['name'] = tier_name(group['tier'])
                group['started_at'] = max((row.get('started_at') or 0 for row in group_records))
                group['first_started_at'] = min((row.get('started_at') or 0 for row in group_records))
                scope[group_type].append(group)
            scope[group_type].sort(key=lambda group: (-group['stats']['battles'], group['name'].lower(), group['id']))
        for record in sorted(records, key=lambda row: (row.get('started_at') or 0, row['arena_id']), reverse=True):
            scope['battles'].append({'id': record['arena_id'], 'name': record.get('vehicle_name') or message('unknown.vehicle'),
                                     'map': record.get('map_name') or message('unknown.map'), 'started_at': record.get('started_at'),
                                     'outcome': record.get('outcome'), 'tier': record.get('vehicle_tier'),
                                     'stats': aggregate_stats([record], self.expected_table)})
        return scope

    def snapshot(self):
        if self.loading or not self.ready:
            from .projection import ScopeIndex
            scopes = dict((name, ScopeIndex('', self.expected_table).snapshot(message('scope.' + name), self._initial_time))
                          for name in ('launch', 'manual'))
            for scope in scopes.values():
                scope['data_revision'] = self._empty_view_revision
            return {'version': VERSION, 'account_key': self.account_key, 'generated_at': self._time(),
                    'loading': self.loading, 'load_error': None if self.loading else self.last_error,
                    'expected': copy.deepcopy(self.expected_table.metadata), 'scopes': scopes,
                    'warnings': [self.last_error or message('core.loading')]}
        timestamp = self._time()
        launch = self._launch(self._state, self.launch_id)
        manual = next(epoch for epoch in self._state['manual_sessions']
                      if epoch['id'] == self._state['current_manual_id'])
        warnings = list(self._warnings)
        if self.store.warning:
            warnings.append(self.store.warning)
        if self.last_error:
            warnings.append(self.last_error)
        if not self.expected_table.values:
            warnings.append(message('core.wn8'))
        if self._unassigned:
            warnings.append(_UNKNOWN_MEMBERSHIP)
        truncated = False
        for index in self._indexes.values():
            warnings.extend(itertools.islice(index.warnings, 200))
            truncated = truncated or len(index.warnings) > 200
        warnings = sorted(set(warnings))
        if truncated or len(warnings) > 200:
            warnings = warnings[:200] + [message('core.more_notices')]
        return {'version': VERSION, 'account_key': self.account_key, 'generated_at': timestamp,
                'expected': copy.deepcopy(self.expected_table.metadata), 'warnings': sorted(set(warnings)),
                'scopes': {'launch': self._scope('_launch_id', self.launch_id, message('scope.launch'),
                                                 launch['started_at'] if launch else timestamp),
                           'manual': self._scope('_manual_id', manual['id'], message('scope.manual'), manual['started_at'])}}
