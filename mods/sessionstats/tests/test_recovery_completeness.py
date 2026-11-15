# -*- coding: utf-8 -*-
"""Complementary reports settle only the fields confirmed by actual results."""
from __future__ import unicode_literals

import copy
import unittest

import test_core as fixtures
from grz_session_stats.core import StatsService
from grz_session_stats.normalize import result_complete, report_diagnostics
from grz_session_stats.storage import canonical_bytes, MAX_TRANSACTION_BYTES


class RecoveryCompletenessTests(unittest.TestCase):
    setUp = fixtures.ServiceTests.__dict__['setUp']
    tearDown = fixtures.ServiceTests.__dict__['tearDown']

    def test_complementary_partial_reports_become_complete_and_keep_original_periods(self):
        self.service.begin_battle('1', started_at=110, vehicle_id=1, mode='random')
        original = copy.deepcopy(self.service._state['battles']['1'])
        first = fixtures.result(complete=False, xp_base=None, xp_received=None, free_xp=None,
                                currencies={'credits': {'income': 100, 'costs': None, 'net': None}})
        self.assertTrue(self.service.record_result(first))
        self.assertEqual(self.service.pending_arena_ids(), ['1'])
        self.clock.value = 140
        self.service.reset_manual()
        self.clock.value = 200
        restored = StatsService(self.directory, 'EU:1', 'launch-two', fixtures.EXPECTED, self.clock)
        second = fixtures.result(complete=False, outcome=None, damage=None, frags=None,
                                 spots=None, defense=None)
        self.assertTrue(restored.record_result(second))
        stored = restored._state['battles']['1']
        self.assertTrue(stored['complete'])
        self.assertTrue(stored['_result_seen'])
        self.assertEqual(stored['_launch_id'], original['_launch_id'])
        self.assertEqual(stored['_manual_id'], original['_manual_id'])
        self.assertEqual(stored['xp_received'], 1500)
        self.assertEqual(stored['currencies']['credits']['net'], 80)
        self.assertEqual(restored.pending_arena_ids(), [])
        sequence = restored.store.sequence
        self.assertFalse(restored.record_result(second))
        self.assertEqual(restored.store.sequence, sequence)
        reloaded = StatsService(self.directory, 'EU:1', 'launch-two', fixtures.EXPECTED, self.clock)
        self.assertTrue(reloaded._state['battles']['1']['complete'])
        self.assertEqual(reloaded.pending_arena_ids(), [])

    def test_complete_flag_cannot_supply_missing_outcome_xp_or_currency(self):
        for identifier, update in (('1', {'outcome': None}), ('2', {'xp_base': None}),
                                   ('3', {'currencies': {'credits': {'net': 100}}})):
            self.service.record_result(fixtures.result(identifier, complete=True, **update))
            self.assertFalse(self.service._state['battles'][identifier]['complete'])
        self.assertEqual(self.service.pending_arena_ids(), ['1', '2', '3'])

    def test_entry_and_zero_flags_without_result_are_not_evidence(self):
        self.service.begin_battle('1', started_at=110, vehicle_id=1, mode='random')
        stored = self.service._state['battles']['1']
        self.assertFalse(stored['complete'])
        self.assertEqual(report_diagnostics(stored),
                         {'report_status': 'never_received', 'reason': 'never_received'})
        complete = fixtures.result()
        for money in complete['currencies'].values():
            money['net'] = 0
        self.assertFalse(result_complete(complete, result_seen=False))
        self.assertTrue(result_complete(complete))

    def test_startup_repairs_legacy_stale_flag_once_without_reassigning_history(self):
        self.service.record_result(fixtures.result())
        legacy = copy.deepcopy(self.service._state)
        legacy['battles']['1']['complete'] = False
        old = copy.deepcopy(legacy['battles']['1'])
        self.service.store.save(legacy)
        self.clock.value = 200
        restored = StatsService(self.directory, 'EU:1', 'launch-two', fixtures.EXPECTED, self.clock)
        actual = restored._state['battles']['1']
        self.assertTrue(actual['complete'])
        for key in old:
            if key not in ('complete', 'revision'):
                self.assertEqual(actual[key], old[key])
        revision = actual['revision']
        reloaded = StatsService(self.directory, 'EU:1', 'launch-two', fixtures.EXPECTED, self.clock)
        self.assertEqual(reloaded._state['battles']['1']['revision'], revision)
        self.assertEqual(reloaded.pending_arena_ids(), [])

    def test_late_partial_fill_retains_newer_xp_bonus_and_facts(self):
        self.service.record_result(fixtures.result(complete=False, xp_received=4500,
                                                  xp_bonus_applied=True, free_xp=None))
        self.service.record_result(fixtures.result(complete=False, xp_received=1500,
                                                  damage=9999, reconcile=False))
        stored = self.service._state['battles']['1']
        self.assertEqual(stored['damage'], 1000)
        self.assertEqual(stored['xp_received'], 4500)
        self.assertEqual(stored['free_xp'], 75)
        self.assertTrue(stored['complete'])

    def test_large_legacy_repair_is_batched_below_the_journal_limit(self):
        self.service.record_result(fixtures.result())
        legacy = copy.deepcopy(self.service._state)
        template = legacy['battles']['1']
        legacy['battles'] = dict((str(index), dict(template, arena_id=str(index),
                                                 vehicle_name='Synthetic vehicle ' + 'v' * 10000,
                                                 complete=False)) for index in range(130))
        self.assertGreater(len(canonical_bytes(legacy['battles'])), MAX_TRANSACTION_BYTES)
        self.service.store.save(legacy)
        sequence = self.service.store.sequence
        self.clock.value = 200
        restored = StatsService(self.directory, 'EU:1', 'launch-two', fixtures.EXPECTED, self.clock)
        self.assertTrue(restored.ready)
        self.assertIsNone(restored.last_error)
        self.assertEqual(len(restored._state['battles']), 130)
        self.assertEqual(restored.pending_arena_ids(), [])
        self.assertGreater(restored.store.sequence, sequence + 2)
        for record in restored._state['battles'].values():
            self.assertTrue(record['complete'])
            self.assertEqual(record['_launch_id'], template['_launch_id'])
            self.assertEqual(record['_manual_id'], template['_manual_id'])
        with open(restored.store._writer_path, 'rb') as handle:
            self.assertTrue(all(len(line) <= MAX_TRANSACTION_BYTES for line in handle))


if __name__ == '__main__':
    unittest.main()
