# -*- coding: utf-8 -*-
"""Persistent shared history and reset boundaries belong to one installation."""
from __future__ import unicode_literals

import copy
import json
import os
import shutil
import tempfile
import unittest

import test_core as core_fixtures
import test_runtime as runtime_fixtures
import test_account_sessions as account_fixtures
from test_config_path import changed
from test_normalize import raw_result
from grz_session_stats import config_path, runtime
from grz_session_stats.sessions import InstallationSession, installation_key
from grz_session_stats.storage import StorageError


class InstallationLedgerTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.mkdtemp(prefix='grz-installation-test-')
        self.game = os.path.join(self.directory, 'game-a')
        self.clock = core_fixtures.Clock()
        self.session = self.open('run-a')

    def tearDown(self):
        shutil.rmtree(self.directory)

    def open(self, launch, game=None):
        return InstallationSession(self.directory, game or self.game, launch,
                                   core_fixtures.EXPECTED, self.clock)

    def record(self, account='EU:7', arena='1', started=110, complete=True):
        self.clock.value = started
        record = core_fixtures.result(arena_id=arena, started_at=started)
        self.session.begin(account, record)
        if complete:
            self.session.result(account, record)

    def stats(self, session=None):
        return (session or self.session).snapshot()[0]['summary']

    def test_restart_keeps_results_from_every_account_without_loading_the_accounts(self):
        self.record()
        self.record('EU:8', '2', 120)
        self.clock.value = 200
        restored = self.open('run-b')
        self.assertEqual(self.stats(restored)['battles'], 2)
        self.assertEqual(restored.snapshot()[0], self.session.snapshot()[0])

    def test_manual_installation_reset_survives_restart_and_excludes_late_old_results(self):
        self.record(complete=False)
        self.clock.value = 130
        self.assertIsNotNone(self.session.reset())
        reset_epoch = self.session.service._state['current_manual_id']
        self.clock.value = 200
        self.session = self.open('run-b')
        self.session.result('EU:7', core_fixtures.result())
        self.assertEqual(self.stats()['observed_battles'], 0)
        self.assertEqual(self.session.service._state['current_manual_id'], reset_epoch)
        self.record('EU:8', '2', 210)
        self.clock.value = 300
        self.assertEqual(self.stats(self.open('run-c'))['battles'], 1)

    def test_same_account_in_two_installations_has_separate_shared_histories(self):
        self.record()
        other = self.open('run-a', os.path.join(self.directory, 'game-b'))
        self.assertEqual(self.stats(other)['observed_battles'], 0)
        self.clock.value = 120
        other.begin('EU:7', core_fixtures.result(arena_id='2', started_at=120))
        other.result('EU:7', core_fixtures.result(arena_id='2', started_at=120))
        self.clock.value = 200
        self.assertEqual(self.stats(self.open('run-b'))['battles'], 1)
        self.assertNotEqual(self.session.service.store.directory, other.service.store.directory)

    def test_shared_record_identity_deduplicates_accounts_and_restarts_without_raw_identifiers(self):
        self.record('PRIVATE_ACCOUNT_A')
        self.record('PRIVATE_ACCOUNT_B')
        self.clock.value = 200
        restored = self.open('run-b')
        restored.result('PRIVATE_ACCOUNT_A', core_fixtures.result())
        self.assertEqual(self.stats(restored)['battles'], 2)
        state = json.dumps(restored.service.store.load())
        for private in ('PRIVATE_ACCOUNT_A', 'PRIVATE_ACCOUNT_B', self.game):
            self.assertNotIn(private, state)
        self.assertEqual(installation_key(self.game), installation_key(os.path.join(self.game, '.')))

    def test_unknown_historical_result_has_no_installation_provenance(self):
        self.assertFalse(self.session.result('EU:7', core_fixtures.result()))
        self.assertEqual(self.stats()['observed_battles'], 0)

    def test_failed_reset_preserves_the_durable_epoch_and_results(self):
        self.record()
        before = copy.deepcopy(self.session.service._state)
        def fail(unused):
            raise StorageError('injected installation write failure')
        self.session.service.store.save = fail
        self.clock.value = 130
        self.assertIsNone(self.session.reset())
        self.assertEqual(self.session.service._state, before)
        self.clock.value = 200
        self.assertEqual(self.stats(self.open('run-b'))['battles'], 1)

    def test_corrupt_latest_generation_restores_the_previous_installation_history(self):
        self.record()
        self.record('EU:8', '2', 120)
        latest = self.session.service.store._files()[0][1]
        with open(latest, 'wb') as handle:
            handle.write(b'corrupt generation')
        self.clock.value = 200
        restored = self.open('run-b')
        stats = self.stats(restored)
        self.assertEqual((stats['battles'], stats['observed_battles'], stats['missing_results']), (1, 2, 1))
        self.assertTrue(restored.snapshot()[2])
        with open(latest, 'rb') as handle:
            self.assertEqual(handle.read(), b'corrupt generation')


class InstallationRuntimeTests(unittest.TestCase):
    setUp = account_fixtures.AccountSessionTests.__dict__['setUp']
    tearDown = account_fixtures.AccountSessionTests.__dict__['tearDown']
    no_footer = account_fixtures.AccountSessionTests.__dict__['no_footer']
    begin = account_fixtures.AccountSessionTests.__dict__['begin']
    garage = account_fixtures.AccountSessionTests.__dict__['garage']
    switch = account_fixtures.AccountSessionTests.__dict__['switch']
    battle = account_fixtures.AccountSessionTests.__dict__['battle']
    scopes = account_fixtures.AccountSessionTests.__dict__['scopes']
    enable_instance = account_fixtures.AccountSessionTests.__dict__['enable_instance']

    def restart(self):
        self.mod.stop()
        self.api.battle = False
        self.clock.value += 86400
        previous = runtime.LAUNCH_ID
        try:
            runtime.LAUNCH_ID = previous + '-installation-restart'
            self.mod = runtime.Runtime(deferred_loading=False, api=self.api, data_dir=self.directory,
                                       expected_table=runtime_fixtures.EXPECTED, now=self.clock,
                                       window=self.window, footer_installer=self.no_footer,
                                       installation_dir=self.directory,
                                       appearance_path=os.path.join(self.directory, 'grz.sessionstats.json'))
            self.mod.start()
        finally:
            runtime.LAUNCH_ID = previous

    def test_shutdown_before_result_preserves_installation_entry_and_recovers_once(self):
        self.enable_instance()
        self.battle(resolved=False)
        self.restart()
        self.assertEqual(self.scopes()['instance']['summary']['missing_results'], 1)
        self.api.events.onBattleResultsReceived(True, raw_result())
        self.api.events.onBattleResultsReceived(True, raw_result())
        scopes = self.scopes()
        self.assertEqual(scopes['instance']['summary']['battles'], 1)
        self.assertEqual(scopes['manual']['summary']['battles'], 1)
        self.assertEqual(scopes['launch']['summary']['battles'], 0)

    def test_installation_storage_failure_does_not_block_account_results(self):
        self.enable_instance()
        self.scopes()
        def fail(unused):
            raise StorageError('injected installation write failure')
        self.mod._instance_session.service.store.save = fail
        self.battle()
        snapshot = self.mod.snapshot()
        self.assertEqual(snapshot['scopes']['manual']['summary']['battles'], 1)
        self.assertTrue(snapshot['warnings'])
        self.assertEqual(snapshot['scopes']['instance']['summary']['battles'], 0)

    def test_hidden_tab_does_not_stop_collection_or_erase_saved_installation_results(self):
        self.enable_instance()
        self.battle()
        self.enable_instance(False)
        self.battle(8, 10)
        self.restart()
        self.assertNotIn('instance', self.scopes())
        self.enable_instance()
        self.assertEqual(self.scopes()['instance']['summary']['battles'], 2)

    def test_late_installation_identity_can_adopt_only_the_current_process_records(self):
        with changed(config_path, 'find_installation_root', lambda: None):
            self.battle()
        self.clock.value += 100
        self.enable_instance()
        self.assertEqual(self.scopes()['instance']['summary']['battles'], 1)

    def test_unknown_installation_root_never_falls_back_to_one_shared_global_ledger(self):
        self.mod._instance_tab_enabled = True
        with changed(config_path, 'find_installation_root', lambda: None):
            self.battle()
            snapshot = self.mod.snapshot()
        self.assertEqual(snapshot['scopes']['manual']['summary']['battles'], 1)
        self.assertNotIn('instance', snapshot['scopes'])
        self.assertIn('installation:identity', self.mod.compatibility_warnings)


if __name__ == '__main__':
    unittest.main()
