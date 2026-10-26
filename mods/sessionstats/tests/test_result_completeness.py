# -*- coding: utf-8 -*-
"""Missing results remain visible without contributing invented statistics."""
from __future__ import unicode_literals

import unittest

import test_core as fixtures


class ResultCompletenessTests(unittest.TestCase):
    setUp = fixtures.ServiceTests.__dict__['setUp']
    tearDown = fixtures.ServiceTests.__dict__['tearDown']
    summary = fixtures.ServiceTests.__dict__['summary']

    def test_missing_result_is_visible_in_each_group_and_finance_coverage(self):
        self.service.record_result(fixtures.result())
        self.service.begin_battle('2', started_at=115, vehicle_id=1, map_id='map-a', mode='random')
        scope = self.service.snapshot()['scopes']['launch']
        stats = scope['summary']
        self.assertEqual((stats['battles'], stats['observed_battles'], stats['missing_results']), (1, 2, 1))
        self.assertEqual(stats['wins'], 1)
        self.assertEqual(stats['currencies']['credits']['net'], 80)
        self.assertEqual(stats['currencies']['credits']['net_count'], 1)
        self.assertEqual(scope['vehicles'][0]['stats']['observed_battles'], 2)
        self.assertEqual(scope['vehicles'][0]['name'], fixtures.result()['vehicle_name'])
        missing = next(row for row in scope['battles'] if row['id'] == '2')
        self.assertIsNone(missing['outcome'])
        self.assertEqual(missing['stats']['battles'], 0)
        self.assertIsNone(missing['stats']['win_rate'])
        self.assertIsNone(missing['stats']['currencies']['credits']['net'])

    def test_partial_known_outcome_is_distinct_from_missing_result(self):
        self.service.record_result(fixtures.result(complete=False, xp_base=None))
        stats = self.summary()
        self.assertEqual((stats['battles'], stats['observed_battles'], stats['missing_results'], stats['partial_results']), (1, 1, 0, 1))
        self.assertIsNone(stats['xp_base']['avg'])

    def test_recovery_clears_gap_without_creating_a_second_battle(self):
        self.service.begin_battle('1', started_at=110, vehicle_id=1, mode='random')
        self.assertEqual(self.summary()['missing_results'], 1)
        self.service.record_result(fixtures.result())
        self.assertEqual((self.summary()['battles'], self.summary()['observed_battles'], self.summary()['missing_results']), (1, 1, 0))
        self.service.record_result(fixtures.result())
        self.assertEqual(self.summary()['observed_battles'], 1)


if __name__ == '__main__':
    unittest.main()
