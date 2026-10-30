# -*- coding: utf-8 -*-
"""Incremental period totals and bounded presentation, independent of the game."""
from __future__ import unicode_literals

import bisect
import math
from collections import Counter

from .core import (_number, _text, _OUTCOMES, _CURRENCIES, _BREAKDOWN,
                   aggregate_stats, wn8_from_totals)
from .localization import message
from .loading import complete

PAGE_SIZE = 40
GROUP_FIELDS = (('vehicles', 'vehicle_id'), ('maps', 'map_id'), ('tiers', 'vehicle_tier'))


def tier_name(tier):
    numerals = ('I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X', 'XI')
    return numerals[tier - 1] if isinstance(tier, int) and not isinstance(tier, bool) and 1 <= tier <= len(numerals) else str(tier) if tier is not None else message('unknown.tier')


DEFAULT_ORDER = {'metric': 'off', 'statistic': 'avg', 'direction': 'desc', 'chronology': 'newest'}


def valid_order(options):
    return (isinstance(options, dict) and set(options) == set(DEFAULT_ORDER) and
            options.get('metric') in ('off', 'xp_base', 'xp_received', 'credits_net', 'battle_wn8') and
            options.get('statistic') in ('min', 'avg', 'max') and
            options.get('direction') in ('asc', 'desc') and
            options.get('chronology') in ('newest', 'oldest'))


_COUNTS = ('battles', 'observed_battles', 'missing_results', 'partial_results',
           'wins', 'losses', 'draws', 'wn8_count')
_XP = ('xp_base', 'xp_received', 'free_xp', 'battle_wn8')
_RATING = ('damage', 'frags', 'spots', 'defense', 'wins')


class Series(object):
    """Removable extrema and sums, including recovery from numeric overflow."""
    def __init__(self):
        self.values = Counter()
        self.ordered = []
        self.count = 0
        self.total = 0

    def build(self, values):
        complete(self.build_steps(values))

    def build_steps(self, values):
        self.values, self.count, self.total = Counter(), 0, 0
        for position, value in enumerate(values):
            if value is not None:
                self.values[value] += 1
                self.count += 1
                self.total += value
            if position % 128 == 0:
                yield None
        self.ordered = sorted(self.values)
        self.total = _number(self.total)
        yield None

    def change(self, value, direction):
        if value is None:
            return
        if not self.values[value]:
            bisect.insort(self.ordered, value)
        self.values[value] += direction
        self.count += direction
        if not self.values[value]:
            del self.values[value]
            self.ordered.pop(bisect.bisect_left(self.ordered, value))
        if direction < 0 and (isinstance(value, float) or isinstance(self.total, float)):
            # Removing a large float must recover small values lost to rounding.
            self.total = None
        elif self.total is not None:
            total = self.total + direction * value
            self.total = None if isinstance(total, float) and (math.isinf(total) or math.isnan(total)) else total
        if not self.count:
            self.total = 0

    def sum(self):
        if self.total is None:
            self.total = _number(sum(value * count for value, count in self.values.items()))
        return _number(self.total) if self.count else None

    def snapshot(self):
        total = self.sum()
        return {'count': self.count, 'sum': total,
                'min': self.ordered[0] if self.count else None,
                'max': self.ordered[-1] if self.count else None,
                'avg': total / float(self.count) if total is not None and self.count else None}


def contribution(record, table):
    actual, expected, rating = {}, {}, None
    if record.get('mode') == 'random' and record.get('outcome') in _OUTCOMES:
        expected = table.for_record(record) or {}
        if expected:
            actual = dict((key, record[key]) for key in _RATING if key != 'wins')
            actual['wins'] = 1 if record['outcome'] == 'win' else 0
            rating = wn8_from_totals(actual, expected)
    return record, rating, actual, expected


class Totals(object):
    def __init__(self):
        self.counts = dict((key, 0) for key in _COUNTS)
        self.series = dict((key, Series()) for key in _XP)
        self.money = dict((currency, dict((key, Series()) for key in
                          ('income', 'costs', 'net') + _BREAKDOWN)) for currency in _CURRENCIES)
        self.actual = dict((key, Series()) for key in _RATING)
        self.expected = dict((key, Series()) for key in _RATING)

    def build(self, items):
        complete(self.build_steps(items))

    def build_steps(self, items):
        records, rated = [], []
        for position, item in enumerate(items):
            if item[0].get('mode') == 'random' and item[0].get('outcome') in _OUTCOMES:
                records.append(item[0])
            if item[1] is not None:
                rated.append(item)
            if position % 128 == 0:
                yield None
        self.counts.update(battles=len(records), observed_battles=len(items),
                           missing_results=len(items) - len(records), wn8_count=len(rated),
                           partial_results=sum(1 for row in records if not row.get('complete')))
        for outcome, key in (('win', 'wins'), ('loss', 'losses'), ('draw', 'draws')):
            self.counts[key] = sum(1 for row in records if row['outcome'] == outcome)
            yield None
        for key in _XP:
            source = (item[1] for item in rated) if key == 'battle_wn8' else (row.get(key) for row in records)
            for step in self.series[key].build_steps(source):
                yield step
        for currency, fields in self.money.items():
            money = []
            for position, row in enumerate(records):
                money.append(row.get('currencies', {}).get(currency, {}))
                if position % 128 == 0:
                    yield None
            for key, series in fields.items():
                source = (row.get('breakdown', {}).get(key) if key in _BREAKDOWN else row.get(key) for row in money)
                for step in series.build_steps(source):
                    yield step
        for key in _RATING:
            for step in self.actual[key].build_steps(item[2][key] for item in rated):
                yield step
            for step in self.expected[key].build_steps(item[3][key] for item in rated):
                yield step

    def change(self, item, direction):
        record, rating, actual, expected = item
        known = record.get('mode') == 'random' and record.get('outcome') in _OUTCOMES
        self.counts['observed_battles'] += direction
        self.counts['battles'] += direction * int(known)
        self.counts['missing_results'] += direction * int(not known)
        if not known:
            return
        self.counts['partial_results'] += direction * int(not record.get('complete'))
        self.counts[{'win': 'wins', 'loss': 'losses', 'draw': 'draws'}[record['outcome']]] += direction
        for key in _XP:
            self.series[key].change(rating if key == 'battle_wn8' else record.get(key), direction)
        for currency, fields in self.money.items():
            values = record.get('currencies', {}).get(currency, {})
            for key, series in fields.items():
                series.change(values.get('breakdown', {}).get(key) if key in _BREAKDOWN else values.get(key), direction)
        if rating is not None:
            self.counts['wn8_count'] += direction
            for key in actual:
                self.actual[key].change(actual[key], direction)
                self.expected[key].change(expected[key], direction)

    def snapshot(self):
        result = dict(self.counts)
        count = result['battles']
        result['win_rate'] = result['wins'] * 100.0 / count if count else None
        result.update((key, series.snapshot()) for key, series in self.series.items())
        result['wn8'] = wn8_from_totals(dict((key, series.sum()) for key, series in self.actual.items()),
                                      dict((key, series.sum()) for key, series in self.expected.items()))
        result['credits_net'] = self.money['credits']['net'].snapshot()
        result['currencies'] = {}
        for currency, fields in self.money.items():
            values = {'breakdown': {}, 'breakdown_counts': {}}
            for key, series in fields.items():
                if key in _BREAKDOWN:
                    values['breakdown'][key] = series.sum()
                    values['breakdown_counts'][key] = series.count
                else:
                    values[key] = series.sum()
                    values[key + '_count'] = series.count
            result['currencies'][currency] = values
        return result


def _remove(ordered, value):
    ordered.pop(bisect.bisect_left(ordered, value))


class Group(object):
    def __init__(self, kind, identifier):
        self.kind, self.identifier = kind, identifier
        self.name_field = 'vehicle_name' if kind == 'vehicles' else 'map_name'
        self.records = {}
        self.order = []
        self.totals = Totals()
        self.starts = Series()

    def build(self, items):
        complete(self.build_steps(items))

    def build_steps(self, items):
        self.records, self.order = {}, []
        for position, item in enumerate(items):
            row = item[0]
            self.records[row['arena_id']] = row
            self.order.append((bool(row.get(self.name_field)), row.get('_updated_at', 0), row['arena_id']))
            if position % 128 == 0:
                yield None
        self.order.sort()
        for step in self.starts.build_steps(item[0].get('started_at') for item in items):
            yield step
        yield None
        for step in self.totals.build_steps(items):
            yield step

    def change(self, record, item, direction):
        identifier = record['arena_id']
        key = (bool(record.get(self.name_field)), record.get('_updated_at', 0), identifier)
        if direction > 0:
            self.records[identifier] = record
            bisect.insort(self.order, key)
        else:
            del self.records[identifier]
            _remove(self.order, key)
        self.totals.change(item, direction)
        self.starts.change(record.get('started_at'), direction)

    def metadata(self):
        latest = self.records[self.order[-1][-1]]
        vehicle = self.kind == 'vehicles'
        if self.kind == 'tiers':
            tier = latest.get('vehicle_tier')
            return {'id': self.identifier, 'name': tier_name(tier), 'tier': tier, 'type': None}
        return {'id': self.identifier,
                'name': (latest.get(self.name_field) or message('unknown.vehicle' if vehicle else 'unknown.map'))[:256],
                'tier': latest.get('vehicle_tier') if vehicle else None,
                'type': latest.get('vehicle_type') if vehicle else None}

    def snapshot(self):
        row = self.metadata()
        times = self.starts.snapshot()
        row['started_at'], row['first_started_at'] = times['max'], times['min']
        row['stats'] = self.totals.snapshot()
        return row


class ScopeIndex(object):
    def __init__(self, identifier, table):
        self.table = table
        self.identifier = identifier
        self.records = {}
        self.order = []
        self.groups = dict((kind, {}) for kind, unused in GROUP_FIELDS)
        self.totals = Totals()
        self.pending = 0
        self._sort_cache = {}
        self.warnings = Counter()

    def build(self, items):
        complete(self.build_steps(items))

    def build_steps(self, items):
        self.records, self.order, self.pending, self.warnings = {}, [], 0, Counter()
        self._sort_cache = {}
        for position, item in enumerate(items):
            row = item[0]
            self.records[row['arena_id']] = (row, item)
            self.order.append((row.get('started_at') or 0, row['arena_id']))
            self.pending += int(not row.get('complete') or row.get('outcome') not in _OUTCOMES)
            self.warnings.update(row.get('warnings', []))
            if position % 128 == 0:
                yield None
        self.order.sort()
        yield None
        for step in self.totals.build_steps(items):
            yield step
        for kind, field in GROUP_FIELDS:
            grouped = {}
            for position, item in enumerate(items):
                row = item[0]
                identifier = _text(row[field]) if row.get(field) is not None else '__unknown__'
                grouped.setdefault(identifier, []).append(item)
                if position % 128 == 0:
                    yield None
            for identifier in grouped:
                group = Group(kind, identifier)
                for step in group.build_steps(grouped[identifier]):
                    yield step
                self.groups[kind][identifier] = group

    def replace(self, record, item):
        identifier = record['arena_id']
        old = self.records.get(identifier)
        if old:
            self._change(old[0], old[1], -1)
        self._change(record, item, 1)

    def _change(self, record, item, direction):
        self._sort_cache = {}
        identifier = record['arena_id']
        key = (record.get('started_at') or 0, identifier)
        if direction > 0:
            self.records[identifier] = (record, item)
            bisect.insort(self.order, key)
        else:
            del self.records[identifier]
            _remove(self.order, key)
        self.totals.change(item, direction)
        self.pending += direction * int(not record.get('complete') or record.get('outcome') not in _OUTCOMES)
        for warning in record.get('warnings', []):
            self.warnings[warning] += direction
            if not self.warnings[warning]:
                del self.warnings[warning]
        for kind, field in GROUP_FIELDS:
            group_id = _text(record[field]) if record.get(field) is not None else '__unknown__'
            groups = self.groups[kind]
            if group_id not in groups:
                groups[group_id] = Group(kind, group_id)
            group = groups[group_id]
            group.change(record, item, direction)
            if not group.records:
                del groups[group_id]

    def _ordered(self, kind, options):
        signature = tuple(options[key] for key in sorted(DEFAULT_ORDER))
        cached = self._sort_cache.get(kind)
        if cached and cached[0] == signature:
            return cached[1]
        metric, statistic = options['metric'], options['statistic']
        ascending_time = options['chronology'] == 'oldest'
        def key(entry):
            if kind == 'battles':
                record, item = self.records[entry[1]]
                identifier, time = record['arena_id'], record.get('started_at')
                known = record.get('mode') == 'random' and record.get('outcome') in _OUTCOMES
                value = None
                if known:
                    value = (item[1] if metric == 'battle_wn8' else
                             record.get('currencies', {}).get('credits', {}).get('net') if metric == 'credits_net' else
                             record.get(metric))
            else:
                identifier = entry.identifier
                times = entry.starts.ordered
                time = (times[0] if ascending_time else times[-1]) if times else None
                series = (entry.totals.money['credits']['net'] if metric == 'credits_net' else
                          entry.totals.series.get(metric))
                value = series.snapshot().get(statistic) if series else None
            chronology = (time is None, (time or 0) if ascending_time else -(time or 0), identifier)
            if metric == 'off':
                return chronology
            return (value is None, (value or 0) if options['direction'] == 'asc' else -(value or 0)) + chronology
        ordered = sorted(self.order if kind == 'battles' else self.groups[kind].values(), key=key)
        self._sort_cache[kind] = (signature, ordered)
        return ordered

    def snapshot(self, label, started_at, pages=None, orders=None):
        pages, orders = pages or {}, orders or {}
        result = {'label': label, 'started_at': started_at, 'pending': self.pending,
                  'summary': self.totals.snapshot(), 'pagination': {}, 'ordering': {}, 'period_id': self.identifier}
        for kind in ('vehicles', 'maps', 'battles', 'tiers'):
            options = orders.get(kind, DEFAULT_ORDER)
            options = options if valid_order(options) else DEFAULT_ORDER
            result['ordering'][kind] = dict(options)
            # Default battle chronology uses the existing time index without a full copy.
            direct = kind == 'battles' and options['metric'] == 'off'
            ordered = self.order if direct else self._ordered(kind, options)
            total = len(ordered)
            page = pages.get(kind, 0)
            if isinstance(page, bool) or not isinstance(page, int):
                page = 0
            page = max(0, min(page, max(0, (total - 1) // PAGE_SIZE)))
            start = page * PAGE_SIZE
            if kind == 'battles':
                # Slice from the end; never copy/reverse the full history to obtain a page.
                if direct and options['chronology'] == 'newest':
                    keys = reversed(ordered[max(0, total - start - PAGE_SIZE):total - start])
                else:
                    keys = ordered[start:start + PAGE_SIZE]
                rows = []
                for key in keys:
                    record, item = self.records[key[1]]
                    rows.append({'id': record['arena_id'],
                                 'name': (record.get('vehicle_name') or message('unknown.vehicle'))[:256],
                                 'map': (record.get('map_name') or message('unknown.map'))[:256],
                                 'started_at': record.get('started_at'), 'outcome': record.get('outcome'),
                                 'tier': record.get('vehicle_tier'), 'stats': aggregate_stats([record], self.table)})
            else:
                rows = [group.snapshot() for group in ordered[start:start + PAGE_SIZE]]
            result[kind] = rows
            result['pagination'][kind] = {'page': page, 'page_size': PAGE_SIZE, 'total': total,
                                          'pages': max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)}
        return result
