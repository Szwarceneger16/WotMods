# -*- coding: utf-8 -*-
"""Manual reset guards must use activity committed by the real service paths."""
from __future__ import unicode_literals

import copy
import os
import shutil
import tempfile
import unittest

from test_core import Clock, EXPECTED, result
from grz_session_stats.core import StatsService
from grz_session_stats.sessions import InstallationSession
from grz_session_stats.storage import GenerationStore, StorageError


class ManualActivityTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.mkdtemp(prefix='grz-manual-activity-')
        self.clock = Clock(100)
        self.service = self.open('run-a')

    def tearDown(self):
        shutil.rmtree(self.directory)

    def open(self, launch):
        return StatsService(self.directory, 'EU:1', launch, EXPECTED, self.clock)

    def manual(self, service=None):
        return (service or self.service)._state['manual_sessions'][-1]

    def files(self, service=None):
        contents = {}
        for unused, path in (service or self.service).store._files():
            with open(path, 'rb') as stream:
                contents[path] = stream.read()
        return contents

    def assert_reset_rejected(self, service=None, reset_time=160):
        service = service or self.service
        state = copy.deepcopy(service._state)
        before = self.files(service)
        self.clock.value = reset_time
        self.assertIsNone(service.reset_manual())
        self.assertIsNotNone(service.last_error)
        self.assertEqual(service._state, state)
        self.assertEqual(self.files(service), before)

    def test_normal_result_activity_blocks_a_backdated_reset(self):
        self.clock.value = 200
        self.assertTrue(self.service.record_result(result(started_at=190, ended_at=200)))
        self.assert_reset_rejected()
        self.assertEqual(self.manual()['last_seen_at'], 200)
        self.assertEqual(self.service.store.load()['manual_sessions'][-1]['last_seen_at'], 200)
        self.clock.value = 210
        self.assertIsNotNone(self.service.reset_manual())
        old_manual, new_manual = self.service._state['manual_sessions']
        self.assertEqual(old_manual['last_seen_at'], 200)
        self.assertEqual(old_manual['ended_at'], 210)
        self.assertEqual(new_manual['last_seen_at'], 210)
        # A delayed beginning predating the actual reset cannot enter its scope.
        self.clock.value = 220
        self.assertTrue(self.service.begin_battle('2', started_at=180, mode='random'))
        row = self.service._state['battles']['2']
        self.assertEqual(row['_manual_id'], old_manual['id'])
        self.assertEqual(self.service.snapshot()['scopes']['manual']['summary']['observed_battles'], 0)

    def test_normal_begin_activity_uses_observation_time_not_server_start(self):
        self.clock.value = 200
        self.assertTrue(self.service.begin_battle('1', started_at=150, mode='random'))
        self.assert_reset_rejected()
        self.assertEqual(self.manual()['last_seen_at'], 200)
        self.assertIsNotNone(self.service.reset_manual(now=200))

    def test_activity_high_water_mark_survives_clock_rollback_and_restart(self):
        self.clock.value = 200
        self.service.begin_battle('1', started_at=110, mode='random')
        self.clock.value = 150
        self.assertTrue(self.service.record_result(result()))
        self.assertEqual(self.manual()['last_seen_at'], 200)
        restored = self.open('run-b')
        self.assertIsNone(restored.last_error)
        self.assertIsNone(restored.store.warning)
        self.assertEqual(self.manual(restored)['last_seen_at'], 200)
        self.assert_reset_rejected(restored)
        self.clock.value = 200
        self.assertIsNotNone(restored.reset_manual())
        reopened = self.open('run-c')
        self.assertIsNone(reopened.last_error)
        self.assertIsNone(reopened.store.warning)

    def test_late_old_period_result_touches_only_the_current_manual_period(self):
        self.clock.value = 120
        self.service.begin_battle('1', started_at=110, mode='random')
        self.clock.value = 140
        self.service.reset_manual()
        closed = copy.deepcopy(self.service._state['manual_sessions'][0])
        current_id = self.manual()['id']
        self.clock.value = 200
        self.assertTrue(self.service.record_result(result()))
        self.assertEqual(self.service._state['manual_sessions'][0], closed)
        self.assertEqual(self.service._state['battles']['1']['_manual_id'], closed['id'])
        self.assertEqual(self.manual()['id'], current_id)
        self.assertEqual(self.manual()['last_seen_at'], 200)
        self.assert_reset_rejected()

    def test_failed_write_does_not_publish_a_manual_activity_boundary(self):
        self.clock.value = 200
        state = copy.deepcopy(self.service._state)
        before = self.files()
        save = self.service.store.save
        def fail(unused):
            raise StorageError('Injected write failure.')
        self.service.store.save = fail
        try:
            self.assertFalse(self.service.record_result(result()))
        finally:
            self.service.store.save = save
        self.assertEqual(self.service._state, state)
        self.assertEqual(self.files(), before)
        self.assertEqual(self.manual()['last_seen_at'], 100)
        self.assertTrue(self.service.record_result(result()))
        self.assertEqual(self.manual()['last_seen_at'], 200)
        self.assert_reset_rejected()

    def test_legacy_missing_or_null_manual_activity_is_populated_on_next_write(self):
        for null in (False, True):
            directory = os.path.join(self.directory, 'legacy-%s' % null)
            service = StatsService(directory, 'EU:1', 'run-a', EXPECTED, self.clock)
            legacy = copy.deepcopy(service._state)
            if null:
                legacy['manual_sessions'][-1]['last_seen_at'] = None
            else:
                legacy['manual_sessions'][-1].pop('last_seen_at', None)
            service.store.save(legacy)
            restored = StatsService(directory, 'EU:1', 'run-b', EXPECTED, self.clock)
            self.assertIsNone(restored.last_error)
            self.assertIsNone(restored.store.warning)
            self.clock.value = 200
            self.assertTrue(restored.record_result(result()))
            self.assertEqual(self.manual(restored)['last_seen_at'], 200)
            self.assert_reset_rejected(restored)

    def test_legacy_activity_is_restored_before_reset_without_another_battle(self):
        self.clock.value = 200
        self.service.begin_battle('1', started_at=110, mode='random')
        # Reproduce the prior writer after a later update during clock rollback:
        # the latest record is stamped 150; the launch still knows activity 200.
        self.clock.value = 150
        self.service.record_result(result())
        legacy = copy.deepcopy(self.service._state)
        legacy['manual_sessions'][-1].pop('last_seen_at', None)
        self.service.store.save(legacy)
        latest = self.service.store.sequence
        before = self.files()
        restored = self.open('run-a')
        self.assertIsNone(restored.last_error)
        self.assertIsNone(restored.store.warning)
        self.assertEqual(self.manual(restored)['last_seen_at'], 200)
        self.assertEqual(restored.store.sequence, latest + 1)
        self.assert_reset_rejected(restored)
        for path, content in before.items():
            if os.path.exists(path):
                with open(path, 'rb') as stream:
                    self.assertEqual(stream.read(), content)
        reopened = self.open('run-a')
        self.assertIsNone(reopened.last_error)
        self.assertEqual(reopened.store.sequence, restored.store.sequence)
        self.assertEqual(self.manual(reopened)['last_seen_at'], 200)

    def test_legacy_record_activity_can_restore_an_incomplete_launch_boundary(self):
        self.clock.value = 200
        self.service.record_result(result())
        legacy = copy.deepcopy(self.service._state)
        legacy['manual_sessions'][-1]['last_seen_at'] = None
        legacy['launch_sessions'][0].pop('last_seen_at', None)
        self.service.store.save(legacy)
        restored = self.open('run-b')
        self.assertIsNone(restored.last_error)
        self.assertEqual(self.manual(restored)['last_seen_at'], 200)
        self.assert_reset_rejected(restored)

    def test_failed_legacy_upgrade_stays_read_only_without_publishing_or_rewriting(self):
        self.clock.value = 200
        self.service.record_result(result())
        legacy = copy.deepcopy(self.service._state)
        legacy['manual_sessions'][-1].pop('last_seen_at', None)
        self.service.store.save(legacy)
        before = self.files()
        save = GenerationStore.save
        def fail(unused_store, unused_candidate):
            raise StorageError('Injected upgrade write failure.')
        GenerationStore.save = fail
        try:
            restored = self.open('run-a')
        finally:
            GenerationStore.save = save
        self.assertTrue(restored.store.read_only)
        self.assertIsNotNone(restored.last_error)
        self.assertEqual(restored._state, legacy)
        self.assertEqual(self.files(), before)
        self.assertFalse(restored.record_result(result('2', started_at=190)))
        self.assertIsNone(restored.reset_manual())
        self.assertEqual(restored._state, legacy)
        self.assertEqual(self.files(), before)

    def test_accounts_and_regions_keep_separate_manual_activity_boundaries(self):
        self.clock.value = 200
        self.service.record_result(result())
        self.clock.value = 150
        for key in ('EU:2', 'NA:1'):
            other = StatsService(self.directory, key, 'run-a', EXPECTED, self.clock)
            self.assertIsNotNone(other.reset_manual(now=160))
        self.assert_reset_rejected()

    def test_installation_begin_and_result_activity_guard_its_independent_reset(self):
        shared = InstallationSession(self.directory, self.directory, 'run-a', EXPECTED, self.clock)
        self.clock.value = 200
        self.assertTrue(shared.begin('EU:1', result(started_at=150)))
        self.assert_reset_rejected(shared.service)
        self.assertEqual(self.manual(shared.service)['last_seen_at'], 200)
        self.clock.value = 220
        self.assertTrue(shared.result('EU:1', result(started_at=150)))
        self.assertEqual(self.manual(shared.service)['last_seen_at'], 220)
        restored = InstallationSession(self.directory, self.directory, 'run-b', EXPECTED, self.clock)
        self.assertIsNone(restored.service.last_error)
        self.assertEqual(self.manual(restored.service)['last_seen_at'], 220)
        self.assert_reset_rejected(restored.service, reset_time=210)
        # The unrelated account's reset does not advance the installation ledger.
        self.clock.value = 230
        self.assertIsNotNone(self.service.reset_manual())
        self.assertEqual(self.manual(restored.service)['last_seen_at'], 220)
        self.assertIsNotNone(restored.reset())
        self.assertEqual(self.manual(restored.service)['last_seen_at'], 230)
        self.assertEqual(self.manual()['last_seen_at'], 230)

    def test_duplicate_result_does_not_create_uncommitted_activity(self):
        self.clock.value = 200
        self.service.record_result(result())
        sequence = self.service.store.sequence
        self.clock.value = 300
        self.assertFalse(self.service.record_result(result()))
        self.assertEqual(self.service.store.sequence, sequence)
        self.assertEqual(self.manual()['last_seen_at'], 200)


if __name__ == '__main__':
    unittest.main()
