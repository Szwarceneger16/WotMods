# -*- coding: utf-8 -*-
"""Clock rollback must not move unseen delayed results into a new launch."""
from __future__ import unicode_literals

import copy
import json
import os
import shutil
import tempfile
import unittest

from test_core import Clock, EXPECTED, result
from grz_session_stats.core import StatsService
from grz_session_stats.sessions import InstallationSession
from grz_session_stats.storage import GenerationStore, StorageError, canonical_bytes


class LaunchOverlapTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.mkdtemp(prefix='grz-launch-overlap-')
        self.clock = Clock(100)
        self.service = self.open('run-a')
        self.clock.value = 200
        self.service.record_result(result('known', started_at=110, ended_at=200))

    def tearDown(self):
        shutil.rmtree(self.directory)

    def open(self, launch):
        return StatsService(self.directory, 'EU:1', launch, EXPECTED, self.clock)

    def files(self, service=None):
        contents = {}
        for unused, path in (service or self.service).store._files():
            with open(path, 'rb') as stream:
                contents[path] = stream.read()
        return contents

    def assert_valid(self, service):
        service._validate_state(json.loads(canonical_bytes(service._state).decode('utf-8')))
        for kind in ('launch_sessions', 'manual_sessions'):
            periods = service._state[kind]
            for previous, following in zip(periods, periods[1:]):
                self.assertIsNotNone(previous.get('ended_at'))
                self.assertLessEqual(previous['ended_at'], following['started_at'])

    def summary(self, service, scope='launch'):
        return service.snapshot()['scopes'][scope]['summary']

    def test_rollback_restart_keeps_unseen_delayed_results_in_the_old_launch(self):
        self.clock.value = 150
        restored = self.open('run-b')
        self.assertIsNone(restored.last_error)
        previous, current = restored._state['launch_sessions']
        self.assertEqual(previous['ended_at'], 200)
        self.assertEqual(current['started_at'], 200)
        self.assertEqual(current['last_seen_at'], 200)
        self.clock.value = 230
        self.assertTrue(restored.record_result(result('late', started_at=175)))
        self.assertEqual(restored._state['battles']['late']['_launch_id'], 'run-a')
        self.assertEqual(self.summary(restored)['battles'], 0)
        self.assertEqual(self.summary(restored, 'manual')['battles'], 2)
        self.assertTrue(restored.record_result(result('new', started_at=210)))
        self.assertEqual(self.summary(restored)['battles'], 1)
        self.assert_valid(restored)
        reopened = self.open('run-b')
        self.assertIsNone(reopened.last_error)
        self.assertIsNone(reopened.store.warning)
        self.assertEqual(self.summary(reopened)['battles'], 1)

    def test_touching_boundary_prefers_previous_observed_activity_for_unseen_results(self):
        self.clock.value = 150
        restored = self.open('run-b')
        self.clock.value = 230
        restored.record_result(result('at-boundary', started_at=200))
        self.assertEqual(restored._state['battles']['at-boundary']['_launch_id'], 'run-a')
        self.assertEqual(self.summary(restored)['battles'], 0)

    def test_live_observation_below_clamped_start_still_belongs_to_this_launch(self):
        self.clock.value = 150
        restored = self.open('run-b')
        self.assertTrue(restored.begin_battle('live', started_at=140, mode='random'))
        self.assertEqual(restored._state['battles']['live']['_launch_id'], 'run-b')
        self.assertEqual(restored._state['battles']['live']['started_at'], 140)
        self.clock.value = 230
        self.assertTrue(restored.record_result(result('live', started_at=140)))
        self.assertEqual(self.summary(restored)['battles'], 1)
        self.assert_valid(restored)

    def test_closed_launch_end_also_limits_the_next_start(self):
        closed = copy.deepcopy(self.service._state)
        closed['launch_sessions'][0]['ended_at'] = 220
        self.service.store.save(closed)
        self.clock.value = 150
        restored = self.open('run-b')
        self.assertEqual(restored._state['launch_sessions'][-1]['started_at'], 220)
        self.clock.value = 230
        restored.record_result(result('gap', started_at=210))
        self.assertIsNone(restored._state['battles']['gap']['_launch_id'])
        self.assertEqual(self.summary(restored)['battles'], 0)
        self.assert_valid(restored)

    def test_repeated_rollbacks_and_equal_starts_do_not_create_overlapping_ranges(self):
        for index, timestamp in enumerate((150, 140, 90)):
            self.clock.value = timestamp
            restored = self.open('run-%s' % index)
            self.assertIsNone(restored.last_error)
            self.assert_valid(restored)
            self.assertEqual(restored._state['launch_sessions'][-1]['started_at'], 200)
        self.clock.value = 230
        restored.record_result(result('boundary', started_at=200))
        self.assertEqual(restored._state['battles']['boundary']['_launch_id'], 'run-a')
        restored.record_result(result('current', started_at=210))
        self.assertEqual(self.summary(restored)['battles'], 1)

    def test_normal_restart_keeps_the_real_gap_and_original_start_time(self):
        self.clock.value = 300
        restored = self.open('run-b')
        self.assertEqual(restored._state['launch_sessions'][-1]['started_at'], 300)
        self.clock.value = 320
        restored.record_result(result('gap', started_at=250))
        self.assertIsNone(restored._state['battles']['gap']['_launch_id'])
        restored.record_result(result('new', started_at=310))
        self.assertEqual(self.summary(restored)['battles'], 1)
        self.assert_valid(restored)

    def test_rollback_does_not_change_saved_memberships_or_manual_reset(self):
        self.clock.value = 220
        manual_id = self.service.reset_manual()
        known = copy.deepcopy(self.service._state['battles']['known'])
        self.clock.value = 150
        restored = self.open('run-b')
        self.assertEqual(restored._state['battles']['known'], known)
        self.assertEqual(restored._state['current_manual_id'], manual_id)
        self.clock.value = 230
        restored.record_result(result('late', started_at=175))
        self.assertEqual(self.summary(restored, 'manual')['battles'], 0)
        self.assertEqual(self.summary(restored)['battles'], 0)
        self.assert_valid(restored)

    def test_overlapping_launches_recover_before_selecting_a_generation(self):
        damaged = copy.deepcopy(self.service._state)
        damaged['launch_sessions'][0]['ended_at'] = 200
        damaged['launch_sessions'].append({'id': 'bad-run', 'started_at': 150,
                                           'last_seen_at': 160, 'ended_at': None})
        latest = self.service.store.save(damaged)
        before = self.files()
        self.clock.value = 150
        restored = self.open('run-b')
        self.assertIsNone(restored.last_error)
        self.assertIsNotNone(restored.store.warning)
        self.assertEqual([period['id'] for period in restored._state['launch_sessions']],
                         ['run-a', 'run-b'])
        self.assertEqual(restored.store.sequence, latest + 1)
        self.assertEqual(restored._state['battles'], self.service._state['battles'])
        for path, content in before.items():
            if os.path.exists(path):
                with open(path, 'rb') as stream:
                    self.assertEqual(stream.read(), content)
        self.assert_valid(restored)

    def test_unclosed_historical_launches_are_rejected_during_selection(self):
        damaged = copy.deepcopy(self.service._state)
        damaged['launch_sessions'].append({'id': 'bad-run', 'started_at': 210,
                                           'last_seen_at': 210, 'ended_at': None})
        self.service.store.save(damaged)
        self.clock.value = 230
        restored = self.open('run-b')
        self.assertIsNone(restored.last_error)
        self.assertIsNotNone(restored.store.warning)
        self.assertEqual([period['id'] for period in restored._state['launch_sessions']],
                         ['run-a', 'run-b'])
        self.assert_valid(restored)

    def test_overlapping_manual_periods_use_the_same_recovery_rule(self):
        self.clock.value = 220
        manual_id = self.service.reset_manual()
        damaged = copy.deepcopy(self.service._state)
        damaged['manual_sessions'][-1]['started_at'] = 210
        self.service.store.save(damaged)
        self.clock.value = 230
        restored = self.open('run-b')
        self.assertIsNone(restored.last_error)
        self.assertIsNotNone(restored.store.warning)
        self.assertEqual(restored._state['current_manual_id'], manual_id)
        self.assertEqual(restored._state['manual_sessions'][-1]['started_at'], 220)
        self.assert_valid(restored)

    def test_live_beginning_at_a_touching_boundary_can_select_this_launch(self):
        self.clock.value = 150
        restored = self.open('run-b')
        self.clock.value = 200
        restored.begin_battle('live-at-boundary', started_at=200, mode='random')
        restored.record_result(result('late-at-boundary', started_at=200))
        self.assertEqual(restored._state['battles']['live-at-boundary']['_launch_id'], 'run-b')
        self.assertEqual(restored._state['battles']['late-at-boundary']['_launch_id'], 'run-a')
        self.assertEqual(self.summary(restored)['observed_battles'], 1)
        self.assert_valid(restored)

    def test_all_overlapping_generations_stay_read_only_without_reinitialization(self):
        damaged = copy.deepcopy(self.service._state)
        damaged['launch_sessions'][0]['ended_at'] = 200
        damaged['launch_sessions'].append({'id': 'bad-run', 'started_at': 150,
                                           'last_seen_at': 160, 'ended_at': None})
        for unused in range(self.service.store.keep_generations):
            self.service.store.save(damaged)
        before = self.files()
        self.clock.value = 230
        restored = self.open('run-b')
        self.assertTrue(restored.store.read_only)
        self.assertIsNotNone(restored.last_error)
        self.assertFalse(restored.record_result(result('new', started_at=210)))
        self.assertIsNone(restored.reset_manual())
        self.assertEqual(self.files(), before)

    def test_failed_clamped_launch_commit_preserves_existing_history_for_retry(self):
        before = self.files()
        original = copy.deepcopy(self.service._state)
        self.clock.value = 150
        save = GenerationStore.__dict__['save']
        def fail(unused_store, unused_candidate):
            raise StorageError('Injected launch write failure.')
        GenerationStore.save = fail
        try:
            restored = self.open('run-b')
        finally:
            GenerationStore.save = save
        self.assertTrue(restored.store.read_only)
        self.assertIsNotNone(restored.last_error)
        self.assertEqual(restored._state, original)
        self.assertEqual(self.files(), before)
        retried = self.open('run-b')
        self.assertIsNone(retried.last_error)
        self.assertEqual(retried._state['launch_sessions'][-1]['started_at'], 200)
        self.assert_valid(retried)

    def test_installation_launches_obey_the_same_rollback_boundary(self):
        self.clock.value = 100
        shared = InstallationSession(self.directory, self.directory, 'run-a', EXPECTED, self.clock)
        self.clock.value = 200
        shared.begin('EU:1', result(started_at=110))
        shared.result('EU:1', result(started_at=110))
        self.clock.value = 150
        restored = InstallationSession(self.directory, self.directory, 'run-b', EXPECTED, self.clock)
        self.assertIsNone(restored.service.last_error)
        self.assertEqual(restored.service._state['launch_sessions'][-1]['started_at'], 200)
        self.clock.value = 230
        restored.result('EU:1', result('late', started_at=175), allow_new=True)
        key = restored.battle_key('EU:1', 'late')
        self.assertEqual(restored.service._state['battles'][key]['_launch_id'], 'run-a')
        self.assertEqual(self.summary(restored.service)['battles'], 0)
        self.assertEqual(restored.snapshot()[0]['summary']['battles'], 2)
        self.assert_valid(restored.service)


if __name__ == '__main__':
    unittest.main()
