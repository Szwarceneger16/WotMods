# -*- coding: utf-8 -*-
"""Additive ordering keeps known totals distinct from per-battle averages."""
from __future__ import unicode_literals

import unittest

from test_core import EXPECTED, result
from grz_session_stats.core import ExpectedTable, aggregate_stats
from grz_session_stats.projection import DEFAULT_ORDER, ScopeIndex, contribution, valid_order


class SumSortingTests(unittest.TestCase):
    def setUp(self):
        self.table = ExpectedTable(EXPECTED)
        self.rows = []
        # More low-valued battles can total more than one higher-valued battle.
        for identifier, group, base, received, gross, net in (
                ('a1', 1, 10, 100, 50, -10), ('a2', 1, 10, 100, 50, -10),
                ('b', 2, 15, 150, 120, -15), ('zero', 3, 0, 0, 0, 0),
                ('unknown', 4, None, None, None, None),
                ('partial-known', 5, 5, 50, 40, -5),
                ('partial-missing', 5, None, 0, None, None)):
            row = result(identifier, started_at=110 + len(self.rows), vehicle_id=group,
                         vehicle_tier=group, map_id=str(group), xp_base=base, xp_received=received)
            row['currencies']['credits'] = {'income': gross, 'net': net, 'costs': None}
            self.rows.append(row)
        pending = result('pending', vehicle_id=1, vehicle_tier=1, map_id='1',
                         xp_base=99999, xp_received=99999, outcome=None, complete=False)
        pending['currencies']['credits'] = {'income': 99999, 'net': 99999, 'costs': None}
        self.rows.append(pending)
        self.index = ScopeIndex('fixture', self.table)
        self.index.build([contribution(row, self.table) for row in self.rows])

    def ordered(self, kind, metric, statistic='sum', direction='desc'):
        options = dict(DEFAULT_ORDER, metric=metric, statistic=statistic, direction=direction)
        return self.index.snapshot('Fixture', 100, orders={kind: options})[kind]

    def test_each_aggregate_kind_sorts_known_sums_with_missing_values_last(self):
        expected = {
            'xp_base': (['3', '5', '2', '1', '4'], [0, 5, 15, 20, None]),
            'xp_received': (['3', '5', '2', '1', '4'], [0, 50, 150, 200, None]),
            'credits_gross': (['3', '5', '1', '2', '4'], [0, 40, 100, 120, None]),
            'credits_net': (['1', '2', '5', '3', '4'], [-20, -15, -5, 0, None])}
        for kind in ('vehicles', 'maps', 'tiers'):
            for metric, (ids, values) in expected.items():
                for direction in ('asc', 'desc'):
                    rows = self.ordered(kind, metric, direction=direction)
                    wanted_ids = ids if direction == 'asc' else list(reversed(ids[:-1])) + ids[-1:]
                    wanted_values = values if direction == 'asc' else list(reversed(values[:-1])) + values[-1:]
                    self.assertEqual([row['id'] for row in rows], wanted_ids, (kind, metric, direction))
                    self.assertEqual([row['sort_value'] for row in rows], wanted_values)

    def test_total_order_differs_from_average_and_credit_income_is_not_net(self):
        self.assertEqual(self.ordered('vehicles', 'xp_base')[0]['id'], '1')
        self.assertEqual(self.ordered('vehicles', 'xp_base', statistic='avg')[0]['id'], '2')
        self.assertEqual(self.ordered('maps', 'credits_gross')[0]['id'], '2')
        self.assertEqual(self.ordered('maps', 'credits_net')[0]['id'], '3')
        for statistic in ('min', 'avg', 'max'):
            gross = self.ordered('tiers', 'credits_gross', statistic=statistic)
            self.assertEqual([row['sort_value'] for row in gross], [120, 50, 40, 0, None])

    def test_partial_sum_coverage_is_independent_and_pending_results_do_not_add(self):
        for kind in ('vehicles', 'maps', 'tiers'):
            groups = dict((row['id'], row) for row in self.ordered(kind, 'xp_base'))
            partial = groups['5']['stats']
            self.assertEqual(partial['xp_base']['count'], 1)
            self.assertEqual(partial['xp_received']['count'], 2)
            self.assertEqual(partial['credits_gross']['count'], 1)
            self.assertEqual(partial['credits_net']['count'], 1)
            self.assertEqual(groups['1']['stats']['observed_battles'], 3)
            self.assertEqual(groups['1']['stats']['xp_base']['sum'], 20)
            self.assertEqual(groups['1']['stats']['credits_gross']['sum'], 100)
            self.assertEqual(groups['3']['stats']['credits_gross']['sum'], 0)
            self.assertIsNone(groups['4']['stats']['credits_gross']['sum'])

    def test_core_and_incremental_credit_series_match_including_zero_and_unknown(self):
        expected = aggregate_stats(self.rows, self.table)
        actual = self.index.totals.snapshot()
        for metric in ('credits_gross', 'credits_net', 'xp_base', 'xp_received'):
            self.assertEqual(actual[metric], expected[metric], metric)
        self.assertEqual(actual['credits_gross']['sum'], 260)
        self.assertEqual(actual['credits_gross']['count'], 5)
        self.assertEqual(actual['currencies']['credits']['income'], actual['credits_gross']['sum'])

    def test_correction_invalidates_cached_total_and_updates_gross_and_net_independently(self):
        self.assertEqual(self.ordered('vehicles', 'credits_gross')[0]['id'], '2')
        corrected = result('b', started_at=112, vehicle_id=2, vehicle_tier=2, map_id='2')
        corrected['currencies']['credits'] = {'income': 0, 'net': -200, 'costs': 200}
        self.index.replace(corrected, contribution(corrected, self.table))
        rows = self.ordered('vehicles', 'credits_gross')
        self.assertEqual(rows[0]['id'], '1')
        self.assertEqual(next(row for row in rows if row['id'] == '2')['sort_value'], 0)
        self.assertEqual(self.ordered('vehicles', 'credits_net', direction='asc')[0]['id'], '2')
        self.index.discard('a1')
        self.assertEqual(next(row for row in self.ordered('vehicles', 'credits_gross')
                              if row['id'] == '1')['sort_value'], 50)

    def test_validation_accepts_additive_aggregate_totals_only(self):
        for kind in ('vehicles', 'maps', 'tiers'):
            for metric in ('off', 'xp_base', 'xp_received', 'credits_net', 'credits_gross'):
                self.assertTrue(valid_order(dict(DEFAULT_ORDER, metric=metric, statistic='sum'), kind))
            for metric in ('battle_wn8', 'win_rate', 'battles'):
                self.assertFalse(valid_order(dict(DEFAULT_ORDER, metric=metric, statistic='sum'), kind))
        for metric in ('off', 'xp_base', 'xp_received', 'credits_net', 'credits_gross', 'battle_wn8'):
            self.assertFalse(valid_order(dict(DEFAULT_ORDER, metric=metric, statistic='sum'), 'battles'))
        for statistic in ('min', 'avg', 'max'):
            self.assertTrue(valid_order(dict(DEFAULT_ORDER, metric='credits_gross', statistic=statistic), 'battles'))

    def test_individual_gross_order_uses_income_without_a_total_statistic(self):
        options = dict(DEFAULT_ORDER, metric='credits_gross', statistic='max')
        rows = self.index.snapshot('Fixture', 100, orders={'battles': options})['battles']
        self.assertEqual(rows[0]['id'], 'b')
        self.assertEqual(rows[0]['stats']['credits_gross']['sum'], 120)
        self.assertEqual(set(row['id'] for row in rows[-2:]), set(['unknown', 'pending']))


if __name__ == '__main__':
    unittest.main()
