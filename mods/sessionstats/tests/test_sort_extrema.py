# -*- coding: utf-8 -*-
"""Min/Max references belong to the complete owned group, not a visible page."""
from __future__ import unicode_literals

import copy
import unittest

from test_core import EXPECTED, result
from grz_session_stats.core import ExpectedTable
from grz_session_stats.localization import Localizer
from grz_session_stats.map_names import LANGUAGES, bundled_names
from grz_session_stats.projection import DEFAULT_ORDER, ScopeIndex, contribution


METRICS = ('xp_base', 'xp_received', 'battle_wn8', 'credits_net', 'credits_gross', 'credits_costs')


class SortExtremaTests(unittest.TestCase):
    def setUp(self):
        self.table = ExpectedTable(EXPECTED)
        self.rows = []
        for identifier, start, xp, damage, gross, cost, net in (
                ('z-zero', 101, 0, 0, 0, 0, -100),
                ('a-zero', 150, 0, 0, 0, 0, -100),
                ('z-high', 102, 900, 4000, 200, 180, 100),
                ('a-high', 110, 900, 4000, 200, 180, 100),
                ('middle', 120, 250, 1000, 100, 25, -25)):
            row = result(identifier, started_at=start, xp_base=xp, xp_received=xp * 2,
                         damage=damage, frags=0 if not damage else 1,
                         spots=0 if not damage else 1, defense=0 if not damage else 1,
                         outcome='loss' if not damage else 'win')
            row['currencies']['credits'] = {'income': gross, 'costs': cost, 'net': net}
            self.rows.append(row)
        missing = result('missing', started_at=170, xp_base=None, xp_received=None, vehicle_id=999)
        missing['currencies']['credits'] = {'income': None, 'costs': None, 'net': None}
        pending = result('pending', started_at=180, outcome=None, complete=False,
                         xp_base=99999, xp_received=99999)
        pending['currencies']['credits'] = {'income': 99999, 'costs': 99999, 'net': 99999}
        self.rows.extend((missing, pending))
        self.index = self.build(self.rows)

    def build(self, rows):
        index = ScopeIndex('synthetic-period', self.table)
        index.build([contribution(row, self.table) for row in rows])
        return index

    def snapshot(self, kind, metric, statistic, index=None, **extra):
        order = dict(DEFAULT_ORDER, metric=metric, statistic=statistic)
        return (index or self.index).snapshot('Synthetic', 0, orders={kind: order}, **extra)

    def group(self, kind, metric, statistic, index=None, **extra):
        rows = self.snapshot(kind, metric, statistic, index=index, **extra)[kind]
        identifier = '1' if kind == 'vehicles' else 'map-a' if kind == 'maps' else '8'
        return next(row for row in rows if row['id'] == identifier)

    def test_all_metrics_and_aggregate_tabs_name_the_exact_extremum_with_stable_ties(self):
        for kind in ('maps', 'vehicles', 'tiers'):
            for metric in METRICS:
                for statistic, wanted in (('min', 'a-zero'), ('max', 'a-high')):
                    row = self.group(kind, metric, statistic)
                    winner = row['sort_battle']
                    self.assertEqual(winner['id'], wanted, (kind, metric, statistic))
                    self.assertEqual(winner['metric'], metric)
                    self.assertEqual(winner['statistic'], statistic)
                    self.assertEqual(winner['value'], row['sort_value'])
                    self.assertEqual(winner['value'], row['stats'][metric][statistic])
                    self.assertEqual(winner['name'], 'Czołg testowy')
                    self.assertEqual(winner['map_id'], 'map-a')
                    self.assertEqual(winner['started_at'], 150 if statistic == 'min' else 110)
        # A different saved chronology cannot choose a different tied result.
        first = self.group('maps', 'xp_base', 'max')['sort_battle']
        order = dict(DEFAULT_ORDER, metric='xp_base', statistic='max', chronology='oldest')
        other = self.index.snapshot('Synthetic', 0, orders={'maps': order})['maps'][0]['sort_battle']
        self.assertEqual(first, other)

    def test_zero_is_linkable_missing_is_not_and_nonextrema_never_invent_a_battle(self):
        for kind in ('maps', 'vehicles', 'tiers'):
            self.assertEqual(self.group(kind, 'xp_base', 'min')['sort_battle']['value'], 0)
            for statistic in ('avg', 'sum'):
                self.assertNotIn('sort_battle', self.group(kind, 'xp_base', statistic))
            for metric in ('off', 'battles', 'win_rate'):
                self.assertTrue(all('sort_battle' not in row for row in
                                    self.snapshot(kind, metric, 'max')[kind]))
            unknown = result('only-missing', xp_base=None, xp_received=None, vehicle_id=999)
            unknown['currencies']['credits'] = {'income': None, 'costs': None, 'net': None}
            index = self.build([unknown])
            for metric in METRICS:
                for statistic in ('min', 'max'):
                    row = self.snapshot(kind, metric, statistic, index=index)[kind][0]
                    self.assertIsNone(row['sort_value'])
                    self.assertNotIn('sort_battle', row)
        self.assertTrue(all('sort_battle' not in row for row in
                            self.snapshot('battles', 'xp_base', 'max')['battles']))

    def test_winner_is_outside_both_loaded_histories_and_battle_page(self):
        rows = [result('page-%03d' % position, started_at=100 + position,
                       xp_base=9999 if position == 0 else position) for position in range(85)]
        index = self.build(rows)
        for kind in ('maps', 'vehicles', 'tiers'):
            extra = {'map_pages': {'map-a': 0}} if kind == 'maps' else {'vehicle_pages': {'1': 0}} if kind == 'vehicles' else {}
            snapshot = self.snapshot(kind, 'xp_base', 'max', index=index, **extra)
            row = snapshot[kind][0]
            self.assertEqual(row['sort_battle']['id'], 'page-000')
            self.assertEqual(row['sort_battle']['value'], 9999)
            self.assertNotIn('page-000', [item['id'] for item in snapshot['battles']])
            if kind != 'tiers':
                self.assertNotIn('page-000', [item['id'] for item in row['battle_list']['items']])

    def test_corrections_removals_and_group_moves_retire_every_old_pair(self):
        corrected = result('a-high', started_at=110, xp_base=None, xp_received=0,
                           vehicle_id=2, vehicle_tier=9, map_id='another-map', damage=None)
        corrected['currencies']['credits'] = {'income': None, 'costs': 0, 'net': None}
        self.index.replace(corrected, contribution(corrected, self.table))
        for kind in ('maps', 'vehicles', 'tiers'):
            self.assertEqual(self.group(kind, 'xp_base', 'max')['sort_battle']['id'], 'z-high')
            self.assertEqual(self.group(kind, 'credits_costs', 'max')['sort_battle']['id'], 'z-high')
        self.index.discard('z-high')
        for kind in ('maps', 'vehicles', 'tiers'):
            for metric in METRICS:
                self.assertEqual(self.group(kind, metric, 'max')['sort_battle']['id'], 'middle')
        self.index.discard('a-zero')
        self.assertEqual(self.group('maps', 'xp_base', 'min')['sort_battle']['id'], 'z-zero')
        rebuilt = self.build([pair[0] for pair in self.index.records.values()])
        for kind in ('maps', 'vehicles', 'tiers'):
            for metric in METRICS:
                for statistic in ('min', 'max'):
                    self.assertEqual(self.snapshot(kind, metric, statistic)[kind],
                                     self.snapshot(kind, metric, statistic, index=rebuilt)[kind])

    def test_filtered_projection_cannot_reference_a_battle_outside_its_records(self):
        index = self.build([row for row in self.rows if row['started_at'] >= 120])
        for kind in ('maps', 'vehicles', 'tiers'):
            self.assertEqual(self.group(kind, 'xp_base', 'max', index=index)['sort_battle']['id'], 'middle')
            self.assertEqual(self.group(kind, 'xp_base', 'min', index=index)['sort_battle']['id'], 'a-zero')

    def test_snapshot_reuses_indexed_winners_without_scanning_group_records(self):
        class NoScan(dict):
            def __iter__(self):
                raise AssertionError('A snapshot must not scan records to find its extremum')
            def items(self):
                raise AssertionError('A snapshot must not scan records to find its extremum')
            def values(self):
                raise AssertionError('A snapshot must not scan records to find its extremum')
        for kind in ('maps', 'vehicles', 'tiers'):
            for group in self.index.groups[kind].values():
                group.records = NoScan(group.records)
            for metric in METRICS:
                for statistic in ('min', 'max'):
                    self.assertEqual(self.group(kind, metric, statistic)['sort_battle']['value'],
                                     self.group(kind, metric, statistic)['sort_value'])

    def test_build_steps_yield_during_association_indexing(self):
        rows = [result(str(position), xp_base=position) for position in range(600)]
        index = ScopeIndex('cooperative', self.table)
        iterator = index.build_steps([contribution(row, self.table) for row in rows])
        self.assertGreater(sum(1 for unused in iterator), 20)
        self.assertEqual(self.group('maps', 'xp_base', 'max', index=index)['sort_battle']['id'], '599')

    def test_selected_language_translates_sort_reference_maps_and_fallbacks_without_mutating_save(self):
        snapshot = self.snapshot('maps', 'xp_base', 'max')
        winner = snapshot['maps'][0]['sort_battle']
        winner['map_id'], winner['map'], winner['name'] = '59_asia_great_wall', 'Saved native name', 'Unknown vehicle'
        original = copy.deepcopy(snapshot)
        names = bundled_names()['59_asia_great_wall']
        payload = {'warnings': [], 'scopes': {'launch': snapshot}}
        for language in LANGUAGES:
            shown = Localizer(language).snapshot(copy.deepcopy(payload))['scopes']['launch']['maps'][0]['sort_battle']
            self.assertEqual(shown['map'], names[language])
            self.assertEqual(shown['name'], Localizer(language).text('unknown.vehicle'))
            self.assertEqual(shown['id'], winner['id'])
            self.assertEqual(shown['metric'], 'xp_base')
            self.assertEqual(shown['value'], 900)
        self.assertEqual(snapshot, original)


if __name__ == '__main__':
    unittest.main()
