# -*- coding: utf-8 -*-
"""Group chronology independently selects the first/last date and direction."""
from __future__ import unicode_literals

import unittest

from test_core import EXPECTED, result
from grz_session_stats.core import ExpectedTable
from grz_session_stats.projection import DEFAULT_ORDER, ScopeIndex, contribution, valid_order


class ChronologyModesTests(unittest.TestCase):
    def setUp(self):
        self.table = ExpectedTable(EXPECTED)
        self.index = ScopeIndex('synthetic-chronology', self.table)
        self.records = []
        for identifier, vehicle, tier, starts in [('a', 1, 6, [100, 400]),
                                                 ('b', 2, 7, [200, 300]),
                                                 ('c', 3, 8, [150, 500])]:
            for started in starts:
                self.records.append(result(identifier + str(started), started_at=started,
                    vehicle_id=vehicle, vehicle_tier=tier, map_id=identifier, xp_base=100))
        self.index.build([contribution(row, self.table) for row in self.records])

    def ordered(self, kind, chronology, metric='off'):
        options = dict(DEFAULT_ORDER, chronology=chronology, metric=metric)
        return self.index.snapshot('Synthetic', 0, orders={kind: options})[kind]

    def test_four_group_orders_select_the_correct_boundary_and_direction(self):
        expected = {'oldest': [0, 2, 1], 'first_desc': [1, 2, 0],
                    'last_asc': [1, 0, 2], 'newest': [2, 0, 1]}
        for kind, ids in [('vehicles', ['1', '2', '3']), ('maps', ['a', 'b', 'c']),
                          ('tiers', ['6', '7', '8'])]:
            for chronology, order in expected.items():
                options = dict(DEFAULT_ORDER, chronology=chronology)
                self.assertTrue(valid_order(options, kind))
                self.assertEqual([row['id'] for row in self.ordered(kind, chronology)],
                                 [ids[index] for index in order], (kind, chronology))

    def test_single_battles_retain_two_dates_and_tier_modes_remain_group_specific(self):
        for chronology in ('first_desc', 'last_asc'):
            self.assertFalse(valid_order(dict(DEFAULT_ORDER, chronology=chronology), 'battles'))
        for chronology in ('newest', 'oldest'):
            self.assertTrue(valid_order(dict(DEFAULT_ORDER, chronology=chronology), 'battles'))
        for chronology in ('tier_asc', 'tier_desc'):
            self.assertTrue(valid_order(dict(DEFAULT_ORDER, chronology=chronology), 'tiers'))
            self.assertFalse(valid_order(dict(DEFAULT_ORDER, chronology=chronology), 'maps'))

    def test_advanced_metric_ties_ignore_all_four_saved_date_modes(self):
        for kind in ('vehicles', 'maps', 'tiers'):
            baseline = [row['id'] for row in self.ordered(kind, 'newest', 'xp_base')]
            for chronology in ('oldest', 'first_desc', 'last_asc'):
                self.assertEqual([row['id'] for row in self.ordered(kind, chronology, 'xp_base')], baseline)

    def test_unknown_group_dates_are_last_in_each_direction_and_ties_are_stable(self):
        for identifier, started in [('missing', None), ('tied-a', 100), ('tied-b', 100)]:
            row = result(identifier, started_at=started, vehicle_id=identifier, map_id=identifier)
            self.index.replace(row, contribution(row, self.table))
        for chronology in ('oldest', 'first_desc', 'last_asc', 'newest'):
            rows = self.ordered('maps', chronology)
            self.assertEqual(rows[-1]['id'], 'missing')
            tied = [row['id'] for row in rows if row['id'].startswith('tied-')]
            self.assertEqual(tied, ['tied-a', 'tied-b'])

    def test_more_pages_use_selected_direction_without_reversing_the_full_history(self):
        rows = [result('history-' + str(index), started_at=1000+index,
                       vehicle_id=9, map_id='history') for index in range(25)]
        for row in rows:
            self.index.replace(row, contribution(row, self.table))
        for kind, identifier in [('maps', 'history'), ('vehicles', '9')]:
            for chronology in ('oldest', 'last_asc', 'first_desc', 'newest'):
                for metric in ('off', 'xp_base'):
                    options = dict(DEFAULT_ORDER, chronology=chronology, metric=metric)
                    actual = []
                    for page in range(3):
                        result_page = self.index._group_battles(kind, identifier, page, options)
                        self.assertEqual(result_page['chronology'], chronology)
                        self.assertEqual(result_page['page'], page)
                        actual.extend(row['started_at'] for row in result_page['items'])
                    ascending = chronology in ('oldest', 'last_asc')
                    self.assertEqual(actual, sorted(range(1000, 1025), reverse=not ascending))


if __name__ == '__main__':
    unittest.main()
