# -*- coding: utf-8 -*-
"""Credit expenses sort by positive magnitude, independently of income or net."""
from __future__ import unicode_literals

import copy
import unittest

from test_core import EXPECTED, result
from grz_session_stats.core import ExpectedTable, aggregate_stats, _clean_record
from grz_session_stats.projection import DEFAULT_ORDER, ScopeIndex, contribution, valid_order


class CostsSortingTests(unittest.TestCase):
    def setUp(self):
        self.table = ExpectedTable(EXPECTED)
        self.rows = []
        for identifier, group, costs, income, net in (
                ('a1', 1, 10, 400, 390), ('a2', 1, 10, 300, 290),
                ('b', 2, 15, 1000, 985), ('zero', 3, 0, -10, -10),
                ('unknown', 4, None, 5000, None),
                ('partial-known', 5, 30, None, None),
                ('partial-missing', 5, None, 0, None)):
            row = result(identifier, started_at=110 + len(self.rows), vehicle_id=group,
                         vehicle_tier=group, map_id=str(group))
            row['currencies']['credits'] = {'costs': costs, 'income': income, 'net': net}
            self.rows.append(row)
        pending = result('pending', vehicle_id=1, vehicle_tier=1, map_id='1',
                         outcome=None, complete=False)
        pending['currencies']['credits'] = {'costs': 99999, 'income': 99999, 'net': 0}
        self.rows.append(pending)
        self.index = ScopeIndex('costs-fixture', self.table)
        self.index.build([contribution(row, self.table) for row in self.rows])

    def ordered(self, kind, statistic='sum', direction='desc', metric='credits_costs'):
        options = dict(DEFAULT_ORDER, metric=metric, statistic=statistic, direction=direction)
        return self.index.snapshot('Fixture', 100, orders={kind: options})[kind]

    def test_each_aggregate_kind_sorts_expense_magnitudes_with_missing_last(self):
        expected = {
            'sum': (['3', '2', '1', '5', '4'], [0, 15, 20, 30, None]),
            'min': (['3', '1', '2', '5', '4'], [0, 10, 15, 30, None]),
            'avg': (['3', '1', '2', '5', '4'], [0, 10, 15, 30, None]),
            'max': (['3', '1', '2', '5', '4'], [0, 10, 15, 30, None])}
        for kind in ('vehicles', 'maps', 'tiers'):
            for statistic, (ids, values) in expected.items():
                for direction in ('asc', 'desc'):
                    rows = self.ordered(kind, statistic, direction)
                    wanted_ids = ids if direction == 'asc' else list(reversed(ids[:-1])) + ids[-1:]
                    wanted_values = values if direction == 'asc' else list(reversed(values[:-1])) + values[-1:]
                    self.assertEqual([row['id'] for row in rows], wanted_ids, (kind, statistic, direction))
                    self.assertEqual([row['sort_value'] for row in rows], wanted_values)

    def test_sum_differs_from_average_and_expenses_are_independent_of_income(self):
        for kind in ('vehicles', 'maps', 'tiers'):
            sums = [row['id'] for row in self.ordered(kind)]
            averages = [row['id'] for row in self.ordered(kind, 'avg')]
            self.assertLess(sums.index('1'), sums.index('2'))
            self.assertGreater(averages.index('1'), averages.index('2'))
            self.assertEqual(self.ordered(kind, metric='credits_gross')[0]['id'], '4')
            self.assertEqual(self.ordered(kind, metric='credits_net')[0]['id'], '2')
            self.assertEqual(self.ordered(kind)[0]['id'], '5')

    def test_expense_coverage_keeps_known_zero_and_excludes_pending_results(self):
        for kind in ('vehicles', 'maps', 'tiers'):
            groups = dict((row['id'], row['stats']) for row in self.ordered(kind))
            self.assertEqual(groups['1']['observed_battles'], 3)
            self.assertEqual(groups['1']['credits_costs']['count'], 2)
            self.assertEqual(groups['1']['credits_costs']['sum'], 20)
            self.assertEqual(groups['5']['observed_battles'], 2)
            self.assertEqual(groups['5']['credits_costs']['count'], 1)
            self.assertEqual(groups['5']['credits_gross']['count'], 1)
            self.assertEqual(groups['3']['credits_costs']['sum'], 0)
            self.assertIsNone(groups['4']['credits_costs']['sum'])
        invalid = result('negative-expense')
        invalid['currencies']['credits'] = {'costs': -50, 'income': -5, 'net': -5}
        clean = _clean_record(invalid)
        self.assertIsNone(aggregate_stats([clean], self.table)['credits_costs']['sum'])
        self.assertEqual(aggregate_stats([clean], self.table)['credits_gross']['sum'], -5)

    def test_incremental_and_recomputed_expense_series_match_money_column(self):
        expected = aggregate_stats(self.rows, self.table)
        actual = self.index.totals.snapshot()
        self.assertEqual(actual['credits_costs'], expected['credits_costs'])
        self.assertEqual(actual['credits_costs']['sum'], 65)
        self.assertEqual(actual['credits_costs']['count'], 5)
        self.assertEqual(actual['credits_costs']['sum'], actual['currencies']['credits']['costs'])
        self.assertEqual(actual['credits_costs']['count'], actual['currencies']['credits']['costs_count'])

    def test_corrections_and_removals_invalidate_cached_expense_orders(self):
        self.assertEqual(self.ordered('maps')[0]['id'], '5')
        updated = result('b', started_at=112, vehicle_id=2, vehicle_tier=2, map_id='2')
        updated['currencies']['credits'] = {'costs': 50, 'income': 0, 'net': -50}
        self.index.replace(updated, contribution(updated, self.table))
        self.assertEqual(self.ordered('maps')[0]['id'], '2')
        self.assertEqual(self.ordered('maps')[0]['sort_value'], 50)
        self.index.discard('a1')
        self.assertEqual(next(row for row in self.ordered('maps') if row['id'] == '1')['sort_value'], 10)
        updated = copy.deepcopy(updated)
        updated['currencies']['credits']['costs'] = None
        self.index.replace(updated, contribution(updated, self.table))
        self.assertEqual(set(row['id'] for row in self.ordered('maps')[-2:]), set(['2', '4']))

    def test_costs_accept_all_only_for_additive_aggregate_order(self):
        for kind in ('vehicles', 'maps', 'tiers'):
            for statistic in ('min', 'avg', 'max', 'sum'):
                self.assertTrue(valid_order(dict(DEFAULT_ORDER, metric='credits_costs', statistic=statistic), kind))
        for statistic in ('min', 'avg', 'max'):
            self.assertTrue(valid_order(dict(DEFAULT_ORDER, metric='credits_costs', statistic=statistic), 'battles'))
        self.assertFalse(valid_order(dict(DEFAULT_ORDER, metric='credits_costs', statistic='sum'), 'battles'))
        for metric in ('battle_wn8', 'win_rate', 'battles'):
            self.assertFalse(valid_order(dict(DEFAULT_ORDER, metric=metric, statistic='sum'), 'vehicles'))

    def test_individual_battles_use_recorded_cost_and_keep_unknown_results_last(self):
        for statistic in ('min', 'avg', 'max'):
            rows = self.ordered('battles', statistic)
            self.assertEqual(rows[0]['id'], 'partial-known')
            self.assertEqual(rows[0]['stats']['credits_costs']['sum'], 30)
            self.assertEqual(rows[0]['stats']['currencies']['credits']['costs'], 30)
            self.assertEqual(set(row['id'] for row in rows[-3:]), set(['unknown', 'partial-missing', 'pending']))


if __name__ == '__main__':
    unittest.main()
