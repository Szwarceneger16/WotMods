# -*- coding: utf-8 -*-
"""WR ordering follows received outcomes rather than pending battle counts."""
from __future__ import unicode_literals

import unittest

from test_core import EXPECTED, result
from grz_session_stats.core import ExpectedTable
from grz_session_stats.projection import (DEFAULT_ORDER, PAGE_SIZE, ScopeIndex,
                                          contribution, valid_order)


class WinRateSortingTests(unittest.TestCase):
    def setUp(self):
        self.table = ExpectedTable(EXPECTED)
        self.index = ScopeIndex('synthetic-win-rate', self.table)
        rows = []
        for group, outcomes in ((1, ('win', 'win', None)),
                                (2, ('win', 'draw')),
                                (3, ('loss', 'draw')),
                                (4, (None,))):
            for position, outcome in enumerate(outcomes):
                rows.append(result('g{0}-{1}'.format(group, position),
                                   vehicle_id=group, vehicle_tier=group,
                                   map_id='map-{0}'.format(group), outcome=outcome,
                                   started_at=100 + group * 10 + position,
                                   complete=outcome is not None))
        self.rows = dict((row['arena_id'], row) for row in rows)
        self.index.build([contribution(row, self.table) for row in rows])

    def snapshot(self, group, **updates):
        options = dict(DEFAULT_ORDER, metric='win_rate')
        options.update(updates)
        return self.index.snapshot('Synthetic period', 0, orders={group: options})

    def test_contract_accepts_win_rate_for_all_groups_and_retained_statistics(self):
        for group in ('vehicles', 'maps', 'tiers', 'battles'):
            for statistic in ('min', 'avg', 'max'):
                self.assertTrue(valid_order(dict(DEFAULT_ORDER, metric='win_rate',
                                                 statistic=statistic), group))
        self.assertFalse(valid_order(dict(DEFAULT_ORDER, metric='winrate'), 'maps'))

    def test_aggregate_order_matches_displayed_rate_with_draws_and_pending(self):
        for group, identifiers in (('vehicles', ['1', '2', '3', '4']),
                                   ('maps', ['map-1', 'map-2', 'map-3', 'map-4']),
                                   ('tiers', ['1', '2', '3', '4'])):
            for statistic in ('min', 'avg', 'max'):
                descending = self.snapshot(group, statistic=statistic)[group]
                self.assertEqual([row['id'] for row in descending], identifiers)
                self.assertEqual([row['sort_value'] for row in descending], [100.0, 50.0, 0.0, None])
                self.assertEqual([row['sort_value'] for row in descending],
                                 [row['stats']['win_rate'] for row in descending])
                # Two wins and one unknown result must remain 100%, not 66.7%.
                self.assertEqual(descending[0]['stats']['battles'], 2)
                self.assertEqual(descending[0]['stats']['observed_battles'], 3)
                ascending = self.snapshot(group, statistic=statistic, direction='asc')[group]
                self.assertEqual([row['id'] for row in ascending],
                                 [identifiers[index] for index in (2, 1, 0, 3)])
                self.assertEqual([row['sort_value'] for row in ascending], [0.0, 50.0, 100.0, None])

    def test_battle_order_is_binary_and_missing_is_last_in_both_directions(self):
        for direction in ('asc', 'desc'):
            rows = self.snapshot('battles', direction=direction)['battles']
            values = [row['sort_value'] for row in rows]
            self.assertEqual(values[-2:], [None, None])
            known = values[:-2]
            self.assertEqual(known, sorted(known, reverse=direction == 'desc'))
            for row in rows:
                expected = 100.0 if row['outcome'] == 'win' else 0.0 if row['outcome'] in ('loss', 'draw') else None
                self.assertEqual(row['sort_value'], expected)
                self.assertEqual(row['stats']['win_rate'], expected)

    def test_partial_known_outcomes_count_but_non_random_outcomes_do_not(self):
        partial = result('g5-partial', vehicle_id=5, vehicle_tier=5,
                         map_id='map-5', complete=False, outcome='win')
        unidentified = result('g6-unidentified', vehicle_id=6, vehicle_tier=6,
                              map_id='map-6', complete=False, mode=None, outcome='win')
        for row in (partial, unidentified):
            self.index.replace(row, contribution(row, self.table))
        for group in ('vehicles', 'maps', 'tiers', 'battles'):
            rows = self.snapshot(group)[group]
            if group == 'battles':
                partial_row = next(row for row in rows if row['id'] == 'g5-partial')
                unknown_row = next(row for row in rows if row['id'] == 'g6-unidentified')
            else:
                prefix = 'map-' if group == 'maps' else ''
                partial_row = next(row for row in rows if row['id'] == prefix + '5')
                unknown_row = next(row for row in rows if row['id'] == prefix + '6')
            self.assertEqual(partial_row['sort_value'], 100.0)
            self.assertEqual(partial_row['stats']['partial_results'], 1)
            self.assertIsNone(unknown_row['sort_value'])
            self.assertEqual(unknown_row['stats']['battles'], 0)

    def test_corrections_invalidate_cached_rates_and_unavailable_positions(self):
        for group in ('vehicles', 'maps', 'tiers', 'battles'):
            self.snapshot(group)
        for identifier in ('g3-0', 'g3-1'):
            row = dict(self.rows[identifier], outcome='win')
            self.index.replace(row, contribution(row, self.table))
        for group, identifier in (('vehicles', '3'), ('maps', 'map-3'), ('tiers', '3')):
            rows = self.snapshot(group)[group]
            self.assertEqual(rows[0]['id'], identifier)
            self.assertEqual(rows[0]['sort_value'], 100.0)
        for identifier in ('g3-0', 'g3-1'):
            row = dict(self.rows[identifier], outcome=None, complete=False)
            self.index.replace(row, contribution(row, self.table))
        for group, identifier in (('vehicles', '3'), ('maps', 'map-3'), ('tiers', '3')):
            rows = self.snapshot(group)[group]
            row = next(row for row in rows if row['id'] == identifier)
            self.assertIsNone(row['sort_value'])
            self.assertEqual(row['stats']['battles'], 0)
            self.assertTrue(all(item['sort_value'] is None for item in rows[-2:]))

    def test_metric_ties_ignore_ordinary_chronology(self):
        for group in ('vehicles', 'maps', 'tiers', 'battles'):
            newest = self.snapshot(group, chronology='newest')[group]
            oldest = self.snapshot(group, chronology='oldest')[group]
            self.assertEqual([row['id'] for row in newest], [row['id'] for row in oldest])

    def test_win_rate_order_and_battle_location_are_global_across_pages(self):
        rows = [result(str(index), started_at=100 + index,
                       outcome='win' if index < 20 else 'draw' if index < 45 else None,
                       complete=index < 45) for index in range(50)]
        self.index.build([contribution(row, self.table) for row in rows])
        options = dict(DEFAULT_ORDER, metric='win_rate', direction='desc')
        first = self.index.snapshot('Synthetic period', 0, orders={'battles': options})
        second = self.index.snapshot('Synthetic period', 0, pages={'battles': 1}, orders={'battles': options})
        values = [row['sort_value'] for row in first['battles'] + second['battles']]
        self.assertEqual(len(first['battles']), PAGE_SIZE)
        self.assertEqual(values, [100.0] * 20 + [0.0] * 25 + [None] * 5)
        for page, scope in enumerate((first, second)):
            for row in scope['battles']:
                self.assertEqual(self.index.battle_page(row['id'], options), page)


if __name__ == '__main__':
    unittest.main()
