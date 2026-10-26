# -*- coding: utf-8 -*-
"""Recover reversed periods without writing them back during launch/reset."""
from __future__ import unicode_literals

import copy
import json
import unittest

import test_ledger_recovery as fixtures
from test_core import EXPECTED, result
from grz_session_stats.core import StatsService
from grz_session_stats.sessions import InstallationSession
from grz_session_stats.storage import canonical_bytes


class PeriodChronologyTests(unittest.TestCase):
    setUp = fixtures.LedgerRecoveryTests.__dict__['setUp']
    tearDown = fixtures.LedgerRecoveryTests.__dict__['tearDown']
    files = fixtures.LedgerRecoveryTests.__dict__['files']
    write_envelope = fixtures.LedgerRecoveryTests.__dict__['write_envelope']
    restore_case = fixtures.LedgerRecoveryTests.__dict__['restore_case']
    assert_recovery = fixtures.LedgerRecoveryTests.__dict__['assert_recovery']

    def assert_valid_state(self, service):
        # The selection validator consumes decoded JSON. Python 2's UUID hex
        # values become unicode at that boundary, just as on actual restart.
        decoded = json.loads(canonical_bytes(service._state).decode('utf-8'))
        service._validate_state(decoded)

    def test_end_before_start_recovers_both_period_types(self):
        for kind in ('launch_sessions', 'manual_sessions'):
            self.restore_case()
            damaged = copy.deepcopy(self.good)
            damaged[kind][0]['ended_at'] = 99
            self.assert_recovery(damaged)

    def test_last_seen_before_start_recovers_both_period_types(self):
        for kind in ('launch_sessions', 'manual_sessions'):
            self.restore_case()
            damaged = copy.deepcopy(self.good)
            damaged[kind][0]['last_seen_at'] = 99
            self.assert_recovery(damaged)

    def test_activity_after_end_recovers_both_period_types(self):
        for kind in ('launch_sessions', 'manual_sessions'):
            self.restore_case()
            damaged = copy.deepcopy(self.good)
            damaged[kind][0].update(ended_at=150, last_seen_at=160)
            self.assert_recovery(damaged)

    def test_same_launch_rejects_reversed_activity_before_closed_launch_check(self):
        for changes in ({'ended_at': 99}, {'last_seen_at': 99},
                        {'ended_at': 150, 'last_seen_at': 160}):
            self.restore_case()
            damaged = copy.deepcopy(self.good)
            damaged['launch_sessions'][0].update(changes)
            latest = self.service.store.save(damaged)
            before = self.files()
            restored = StatsService(self.directory, 'EU:1', 'run-a', EXPECTED, self.clock)
            self.assertIsNone(restored.last_error)
            self.assertFalse(restored.store.read_only)
            self.assertIsNotNone(restored.store.warning)
            self.assertEqual(restored._state, self.good)
            self.assertEqual(self.files(), before)
            self.assertTrue(restored.record_result(result('3', started_at=150)))
            self.assertEqual(restored.store.sequence, latest + 1)

    def test_recovered_period_memberships_preserve_delayed_results(self):
        damaged = copy.deepcopy(self.good)
        damaged['manual_sessions'][0]['ended_at'] = 99
        damaged['launch_sessions'][0]['last_seen_at'] = 99
        self.service.store.save(damaged)
        self.clock.value = 200
        restored = StatsService(self.directory, 'EU:1', 'run-b', EXPECTED, self.clock)
        self.assertTrue(restored.record_result(result('delayed', started_at=130)))
        record = restored._state['battles']['delayed']
        self.assertEqual(record['_manual_id'], self.good['manual_sessions'][0]['id'])
        self.assertEqual(record['_launch_id'], 'run-a')
        self.assertEqual(restored.snapshot()['scopes']['manual']['summary']['battles'], 1)
        self.assertEqual(restored.snapshot()['scopes']['launch']['summary']['battles'], 0)
        self.assert_valid_state(restored)

    def test_installation_recovers_reversed_period_without_changing_its_reset(self):
        shared = InstallationSession(self.directory, self.directory, 'run-a', EXPECTED, self.clock)
        shared.begin('EU:1', result())
        shared.result('EU:1', result())
        good = copy.deepcopy(shared.service._state)
        damaged = copy.deepcopy(good)
        damaged['manual_sessions'][0]['last_seen_at'] = 159
        latest = shared.service.store.save(damaged)
        self.clock.value = 200
        restored = InstallationSession(self.directory, self.directory, 'run-b', EXPECTED, self.clock)
        self.assertIsNone(restored.service.last_error)
        self.assertIsNotNone(restored.service.store.warning)
        self.assertEqual(restored.service._state['current_manual_id'], good['current_manual_id'])
        self.assertEqual(restored.snapshot()[0]['summary']['battles'], 1)
        self.assertEqual(restored.service.store.sequence, latest + 1)
        self.assert_valid_state(restored.service)

    def test_equal_boundaries_are_valid_including_timestamp_zero(self):
        for timestamp in (0, 100):
            self.restore_case()
            valid = copy.deepcopy(self.good)
            valid['launch_sessions'][0].update(started_at=timestamp, last_seen_at=timestamp,
                                                ended_at=timestamp)
            valid['manual_sessions'][0].update(started_at=timestamp, last_seen_at=timestamp,
                                                ended_at=timestamp)
            self.service.store.save(valid)
            restored = StatsService(self.directory, 'EU:1', 'run-b', EXPECTED, self.clock)
            self.assertIsNone(restored.last_error)
            self.assertIsNone(restored.store.warning)
            self.assertEqual(restored._state['battles'], self.good['battles'])
            self.assert_valid_state(restored)

    def test_manual_reset_cannot_precede_an_accepted_last_seen_boundary(self):
        valid = copy.deepcopy(self.good)
        valid['manual_sessions'][-1]['last_seen_at'] = 180
        self.service.store.save(valid)
        restored = StatsService(self.directory, 'EU:1', 'run-a', EXPECTED, self.clock)
        self.assertIsNone(restored.last_error)
        before = self.files()
        for reset_time in (160, 179):
            self.assertIsNone(restored.reset_manual(now=reset_time))
            self.assertEqual(restored._state, valid)
            self.assertEqual(self.files(), before)
        self.assertIsNotNone(restored.reset_manual(now=180))
        self.assert_valid_state(restored)
        reopened = StatsService(self.directory, 'EU:1', 'run-b', EXPECTED, self.clock)
        self.assertIsNone(reopened.last_error)
        self.assertIsNone(reopened.store.warning)

    def test_clock_rollback_cannot_write_a_reversed_manual_or_launch_period(self):
        self.clock.value = 90
        before = self.files()
        self.assertIsNone(self.service.reset_manual())
        self.assertEqual(self.files(), before)
        self.assertTrue(self.service.record_result(result('late', started_at=80)))
        self.assert_valid_state(self.service)
        reopened = StatsService(self.directory, 'EU:1', 'run-b', EXPECTED, self.clock)
        self.assertIsNone(reopened.last_error)
        self.assertIsNone(reopened.store.warning)
        self.assert_valid_state(reopened)
        previous = reopened._state['launch_sessions'][0]
        self.assertGreaterEqual(previous['ended_at'], previous['started_at'])

    def test_only_reversed_generations_remain_read_only_without_reinitialization(self):
        damaged = copy.deepcopy(self.good)
        damaged['launch_sessions'][0]['last_seen_at'] = 99
        for unused in range(self.service.store.keep_generations):
            self.service.store.save(damaged)
        before = self.files()
        restored = StatsService(self.directory, 'EU:1', 'run-b', EXPECTED, self.clock)
        self.assertTrue(restored.store.read_only)
        self.assertIsNotNone(restored.last_error)
        self.assertFalse(restored.record_result(result('3')))
        self.assertIsNone(restored.reset_manual())
        self.assertEqual(self.files(), before)

    def test_reversed_generations_above_unsupported_schema_cannot_bypass_protection(self):
        latest = self.service.store.sequence
        unsupported = dict(self.good, schema_version=999)
        self.write_envelope(latest + 1, unsupported)
        damaged = copy.deepcopy(self.good)
        damaged['launch_sessions'][0]['last_seen_at'] = 99
        self.write_envelope(latest + 2, damaged)
        before = self.files()
        restored = StatsService(self.directory, 'EU:1', 'run-b', EXPECTED, self.clock)
        self.assertTrue(restored.store.read_only)
        self.assertIsNotNone(restored.last_error)
        self.assertIsNone(restored.store.warning)
        self.assertEqual(self.files(), before)


if __name__ == '__main__':
    unittest.main()
