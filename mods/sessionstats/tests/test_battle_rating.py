# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src'))
from grz_session_stats.core import StatsService, aggregate_stats
from test_core import Clock, EXPECTED, result


class BattleRatingTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.mkdtemp(prefix='grz-battle-rating-')
        self.clock = Clock(100)
        self.service = StatsService(self.directory, 'EU:1', 'launch-one', EXPECTED, self.clock)
        self.clock.value = 120

    def tearDown(self):
        shutil.rmtree(self.directory)

    def test_ready_reuses_the_single_battle_formula_and_returns_an_independent_value(self):
        record = result()
        self.assertTrue(self.service.record_result(record))
        rating = self.service.battle_rating(1)
        self.assertEqual(rating['account_key'], 'EU:1')
        self.assertEqual(rating['arena_id'], '1')
        self.assertEqual(rating['status'], 'ready')
        self.assertAlmostEqual(rating['wn8'], aggregate_stats([record], EXPECTED)['wn8'])
        rating['wn8'] = -1
        self.assertGreaterEqual(self.service.battle_rating('1')['wn8'], 0)

    def test_zero_rating_is_ready(self):
        self.service.record_result(result(outcome='loss', damage=0, frags=0, spots=0, defense=0))
        self.assertEqual(self.service.battle_rating('1')['status'], 'ready')
        self.assertEqual(self.service.battle_rating('1')['wn8'], 0.0)

    def test_missing_xp_and_finances_do_not_block_known_wn8(self):
        record = result(complete=False, xp_base=None, xp_received=None, free_xp=None, currencies={})
        self.service.record_result(record)
        self.assertIn('1', self.service.pending_arena_ids())
        rating = self.service.battle_rating('1')
        self.assertEqual(rating['status'], 'ready')
        self.assertAlmostEqual(rating['wn8'], aggregate_stats([record], EXPECTED)['wn8'])

    def test_beginning_and_incomplete_rating_inputs_stay_pending(self):
        self.service.begin_battle('1', started_at=110, vehicle_id=1, mode='random')
        self.assertEqual(self.service.battle_rating('1')['status'], 'pending')
        self.service.record_result(result(complete=False, spots=None))
        self.assertEqual(self.service.battle_rating('1')['status'], 'pending')
        self.assertIsNone(self.service.battle_rating('1')['wn8'])
        self.service.record_result(result())
        self.assertEqual(self.service.battle_rating('1')['status'], 'ready')

    def test_archived_result_is_available_outside_both_current_indexes(self):
        self.service.record_result(result())
        self.clock.value = 200
        restored = StatsService(self.directory, 'EU:1', 'launch-two', EXPECTED, self.clock)
        restored.reset_manual()
        self.assertNotIn('1', restored._indexes['launch'].records)
        self.assertNotIn('1', restored._indexes['manual'].records)
        self.assertNotIn('timeline', restored._indexes)
        self.assertEqual(restored.battle_rating('1')['status'], 'ready')
        self.assertAlmostEqual(restored.battle_rating('1')['wn8'], self.service.battle_rating('1')['wn8'])

    def test_the_same_arena_id_cannot_read_another_accounts_rating(self):
        self.service.record_result(result())
        other = StatsService(self.directory, 'EU:2', 'other-launch', EXPECTED, self.clock)
        self.assertEqual(other.battle_rating('1')['status'], 'unavailable')
        self.assertEqual(other.battle_rating('1')['account_key'], 'EU:2')
        other.record_result(result(outcome='loss', damage=0, frags=0, spots=0, defense=0))
        self.assertEqual(other.battle_rating('1')['wn8'], 0.0)
        self.assertGreater(self.service.battle_rating('1')['wn8'], 0.0)

    def test_unsupported_vehicle_or_expected_table_is_unavailable(self):
        self.service.record_result(result(vehicle_id=999))
        self.assertEqual(self.service.battle_rating('1')['status'], 'unavailable')
        self.assertIsNone(self.service.battle_rating('1')['wn8'])
        empty = StatsService(self.directory, 'EU:2', 'empty-table', {}, self.clock)
        empty.record_result(result())
        self.assertEqual(empty.battle_rating('1')['status'], 'unavailable')

    def test_loading_closed_and_failed_services_do_not_expose_a_partial_history(self):
        self.service.record_result(result())
        self.clock.value = 200
        loading = StatsService(self.directory, 'EU:1', 'loading', EXPECTED, self.clock, deferred=True)
        self.assertEqual(loading.battle_rating('1')['status'], 'pending')
        self.assertIsNone(loading.battle_rating('1')['wn8'])
        loading.cancel_loading()
        self.assertEqual(loading.battle_rating('1')['status'], 'unavailable')
        self.service._fail_loading(ValueError('synthetic load failure'))
        self.assertEqual(self.service.battle_rating('1')['status'], 'unavailable')

    def test_invalid_or_absent_ids_do_not_project_or_enumerate_history(self):
        self.service.record_result(result())

        class LookupOnly(dict):
            def __iter__(self):
                raise AssertionError('A single rating must not enumerate history')

            def values(self):
                raise AssertionError('A single rating must not enumerate history')

            def items(self):
                raise AssertionError('A single rating must not enumerate history')

        def no_snapshot():
            raise AssertionError('A single rating must not build a full snapshot')

        self.service._state['battles'] = LookupOnly(self.service._state['battles'])
        self.service.snapshot = no_snapshot
        self.assertEqual(self.service.battle_rating('1')['status'], 'ready')
        for identifier in (None, '', 'x' * 129, 10 ** 10000, True, 1.5, [], {}, object(), 'missing'):
            self.assertEqual(self.service.battle_rating(identifier)['status'], 'unavailable')
            self.assertIsNone(self.service.battle_rating(identifier)['wn8'])


if __name__ == '__main__':
    unittest.main()
