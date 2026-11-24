# -*- coding: utf-8 -*-
"""Persistent shared history and reset boundaries belong to one installation."""
from __future__ import unicode_literals

import copy
import io
import json
import os
import shutil
import subprocess
import tempfile
import unittest

import test_core as core_fixtures
import test_runtime as runtime_fixtures
import test_account_sessions as account_fixtures
from test_config_path import Resources, changed
from test_normalize import raw_result
from grz_session_stats import config_path, runtime, sessions
from grz_session_stats.sessions import InstallationSession, installation_key
from grz_session_stats.storage import GenerationStore, StorageError, native_data_path


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
        previous = copy.deepcopy(self.session.snapshot()[0])
        current = copy.deepcopy(restored.snapshot()[0])
        # Restarting replaces the projection and its sort acknowledgements.
        self.assertNotEqual(current.pop('data_revision'), previous.pop('data_revision'))
        self.assertNotEqual(current.pop('order_epoch'), previous.pop('order_epoch'))
        self.assertEqual(current, previous)

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

        store = self.mod._instance_session.service.store
        save = store.save
        store.save = fail
        try:
            service, unused = self.battle()
            self.garage()
            snapshot = self.mod.snapshot()
            self.assertEqual(snapshot['scopes']['manual']['summary']['battles'], 1)
            self.assertTrue(snapshot['warnings'])
            self.assertEqual(snapshot['scopes']['instance']['summary']['battles'], 0)
            self.assertTrue(self.mod._combat_intake.pending(self.mod.active_key))
        finally:
            store.save = save
        sequence = service.store.sequence
        self.garage()
        self.assertEqual(service.store.sequence, sequence)
        self.assertEqual(self.scopes()['instance']['summary']['battles'], 1)
        self.assertEqual(self.mod._combat_intake.pending(self.mod.active_key), [])

    def test_direct_installation_write_race_preserves_both_accounts(self):
        self.enable_instance()
        account, arena = self.battle(resolved=False)
        installation = self.mod._instance_session
        key = self.mod.active_key
        target = installation.service.store
        competing = []
        save = GenerationStore.save

        def save_with_peer(writer, data):
            if writer is target and not competing:
                # The peer publishes after the refreshed writer built its
                # candidate. GenerationStore must reject that stale writer.
                peer = InstallationSession(self.directory, self.directory, 'peer-session',
                                           runtime_fixtures.EXPECTED, self.clock)
                competing.append(peer)
                row = core_fixtures.result(arena_id='2', started_at=self.clock.value)
                peer.begin('EU:8', row)
                self.assertTrue(peer.result('EU:8', row))
            return save(writer, data)

        with changed(GenerationStore, 'save', save_with_peer):
            self.api.events.onBattleResultsReceived(True, raw_result(arena_id=arena))
        self.assertEqual(len(competing), 1)
        self.assertTrue(account._state['battles'][arena]['_result_seen'])
        self.assertFalse(installation.service._state['battles'][installation.battle_key(key, arena)]['_result_seen'])
        runtime_fixtures.wait_for_combat_capture(self.mod)
        self.assertEqual(len(self.mod._combat_intake.pending(key)), 1)
        self.restart()
        self.assertEqual(self.scopes()['instance']['summary']['battles'], 2)
        self.assertEqual(self.scopes()['manual']['summary']['battles'], 1)
        self.assertEqual(self.mod._combat_intake.pending(key), [])

    def test_direct_account_io_exception_is_staged_and_applied_after_recovery(self):
        self.enable_instance()
        account, arena = self.battle(resolved=False)
        key = self.mod.active_key

        def fail(unused, before_commit=None):
            raise IOError('injected direct account I/O failure')

        with changed(account, 'record_result', fail):
            self.api.events.onBattleResultsReceived(True, raw_result(arena_id=arena))
        self.assertFalse(account._state['battles'][arena]['_result_seen'])
        runtime_fixtures.wait_for_combat_capture(self.mod)
        self.assertEqual(len(self.mod._combat_intake.pending(key)), 1)
        self.garage()
        self.assertTrue(account._state['battles'][arena]['_result_seen'])
        self.assertEqual(self.scopes()['instance']['summary']['battles'], 1)
        self.assertEqual(self.mod._combat_intake.pending(key), [])

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


class InstallationAliasMigrationTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.mkdtemp(prefix='grz-installation-alias-')
        self.game = os.path.join(self.directory, 'game')
        self.alias = os.path.join(self.directory, 'junction')
        os.mkdir(self.game)
        self.clock = core_fixtures.Clock()
        self.key = installation_key(self.game)
        self.old_key = sessions._installation_digest(self.alias)

    def tearDown(self):
        shutil.rmtree(self.directory)

    def open(self, game, launch, deferred=False):
        return InstallationSession(self.directory, game, launch, core_fixtures.EXPECTED,
                                   self.clock, deferred=deferred)

    def old_session(self, launch='old-alias', deferred=False):
        # Emulate the key used by previous Windows Python 2.7 builds.
        with changed(sessions, '_installation_keys', lambda root: (self.old_key, self.old_key)):
            return self.open(self.alias, launch, deferred=deferred)

    def record(self, session, arena, started, **fields):
        self.clock.value = started
        record = core_fixtures.result(arena_id=arena, started_at=started, **fields)
        session.begin('EU:7', record)
        session.result('EU:7', record)

    def test_first_use_through_alias_opens_one_new_history(self):
        with changed(sessions, '_installation_keys', lambda root: (self.key, self.old_key)):
            session = self.open(self.alias, 'new-through-alias')
        self.assertTrue(session.service.ready, session.service.last_error)
        self.assertTrue(session.accepts_installation(self.old_key))
        self.record(session, '1', 110)
        self.clock.value = 120
        restored = self.open(self.game, 'new-direct')
        self.assertEqual(restored.snapshot()[0]['summary']['battles'], 1)

    def test_alias_only_restore_preserves_its_reset_and_recognizes_pending_provenance(self):
        old = self.old_session()
        self.record(old, '1', 110)
        self.clock.value = 125
        reset = old.reset()
        self.record(old, '2', 140)
        original = copy.deepcopy(old.service.store.load())
        self.clock.value = 150
        with changed(sessions, '_installation_keys', lambda root: (self.key, self.old_key)):
            migrated = self.open(self.alias, 'migrate', deferred=True)
        while migrated.service.loading:
            migrated.service.advance_loading(budget=1.0)
        self.assertTrue(migrated.service.ready, migrated.service.last_error)
        self.assertEqual(migrated.service.account_key, self.key)
        self.assertTrue(migrated.accepts_installation(self.old_key))
        self.assertFalse(migrated.accepts_installation('installation:' + '0' * 64))
        self.assertEqual(migrated.service._state['current_manual_id'], reset)
        self.assertEqual(migrated.snapshot()[0]['summary']['battles'], 1)
        self.assertEqual(old.service.store.load(), original)
        self.clock.value = 160
        restored = self.open(self.game, 'direct-restart')
        self.assertTrue(restored.accepts_installation(self.old_key))
        self.assertEqual(restored.snapshot()[0]['summary']['battles'], 1)
        self.assertEqual(len(restored.service._state['battles']), 2)

    def test_both_ledgers_merge_and_keep_latest_facts_and_reset_boundaries(self):
        primary = self.open(self.game, 'direct')
        old = self.old_session()
        self.record(old, '1', 105, damage=1000, xp_bonus_applied=True, xp_received=2111)
        self.record(primary, '2', 110)
        self.clock.value = 130
        first_reset = primary.reset()
        self.clock.value = 150
        latest_reset = old.reset()
        self.record(old, '3', 155)
        self.record(primary, '4', 160)
        self.clock.value = 170
        primary.result('EU:7', core_fixtures.result(arena_id='1', started_at=105, damage=2777), allow_new=True)
        self.clock.value = 180
        with changed(sessions, '_installation_keys', lambda root: (self.key, self.old_key)):
            migrated = self.open(self.alias, 'migrate-both')
        self.assertTrue(migrated.service.ready, migrated.service.last_error)
        state = migrated.service._state
        self.assertEqual(state['current_manual_id'], latest_reset)
        self.assertEqual([period['id'] for period in state['manual_sessions'][1:]], [first_reset, latest_reset])
        self.assertEqual(len(state['battles']), 4)
        merged = state['battles'][migrated.battle_key('EU:7', '1')]
        self.assertEqual((merged['damage'], merged['xp_received']), (2777, 2111))
        self.assertTrue(merged['xp_bonus_applied'])
        self.assertEqual(migrated.snapshot()[0]['summary']['battles'], 2)
        self.clock.value = 190
        with changed(sessions, '_installation_keys', lambda root: (self.key, self.old_key)):
            repeat = self.open(self.alias, 'repeat-alias')
        self.assertEqual(repeat.service._state['battles'], state['battles'])
        self.assertEqual(repeat.snapshot()[0]['summary']['battles'], 2)

    def test_alias_startup_replay_recovers_after_exit_before_first_ledger_generation(self):
        old = self.old_session(deferred=True)
        self.record(old, '1', 110, damage=2100)
        self.assertIsNone(old.service.store.load())
        original_intake = copy.deepcopy(old.service._intake.store.load())
        self.assertEqual([event['kind'] for event in original_intake['events']], ['open', 'begin', 'result'])
        old.service.cancel_loading()
        self.clock.value = 200
        with changed(sessions, '_installation_keys', lambda root: (self.key, self.old_key)):
            migrated = self.open(self.alias, 'recover-staged')
        self.assertTrue(migrated.service.ready, migrated.service.last_error)
        key = migrated.battle_key('EU:7', '1')
        self.assertEqual(migrated.service._state['battles'][key]['damage'], 2100)
        self.assertEqual(migrated.snapshot()[0]['summary']['battles'], 1)
        self.assertIsNone(old.service.store.load())
        self.assertEqual(old.service._intake.store.load(), original_intake)
        self.clock.value = 300
        restored = self.open(self.game, 'direct-after-migration')
        self.assertEqual(restored.snapshot()[0]['summary']['battles'], 1)
        self.assertTrue(restored.accepts_installation(self.old_key))

    def test_older_alias_startup_correction_does_not_replace_newer_known_facts(self):
        old = self.old_session()
        self.record(old, '1', 110, damage=1000)
        self.clock.value = 120
        staged = self.old_session('old-pending', deferred=True)
        self.clock.value = 125
        staged.result('EU:7', core_fixtures.result(damage=2100, free_xp=321, reconcile=True))
        staged.service.cancel_loading()
        self.clock.value = 130
        primary = self.open(self.game, 'direct')
        self.clock.value = 150
        primary.result('EU:7', core_fixtures.result(damage=2777, free_xp=None), allow_new=True)
        self.clock.value = 200
        with changed(sessions, '_installation_keys', lambda root: (self.key, self.old_key)):
            migrated = self.open(self.alias, 'recover-both')
        self.assertTrue(migrated.service.ready, migrated.service.last_error)
        key = migrated.battle_key('EU:7', '1')
        battle = migrated.service._state['battles'][key]
        self.assertEqual((battle['damage'], battle['free_xp']), (2777, 321))
        self.assertEqual(staged.service._intake.events[-1]['record']['damage'], 2100)

    def test_stamped_canonical_result_wins_over_a_later_legacy_wall_timestamp(self):
        old = self.old_session()
        self.record(old, '1', 110, damage=1000)
        self.clock.value = 400
        staged = self.old_session('later-wall-clock', deferred=True)
        self.clock.value = 500
        staged.result('EU:7', core_fixtures.result(damage=2100, free_xp=321, reconcile=True))
        staged.service.cancel_loading()
        self.clock.value = 200
        primary = self.open(self.game, 'direct-stamped')
        self.clock.value = 250
        observation = [250000000, None, 0, 'a' * 32, 1]
        corrected = core_fixtures.result(damage=2777, free_xp=None, reconcile=True, _capture_order=observation)
        primary.result('EU:7', corrected, allow_new=True)
        self.clock.value = 600
        with changed(sessions, '_installation_keys', lambda root: (self.key, self.old_key)):
            migrated = self.open(self.alias, 'recover-during-clock-rollback')
        self.assertTrue(migrated.service.ready, migrated.service.last_error)
        key = migrated.battle_key('EU:7', '1')
        battle = migrated.service._state['battles'][key]
        self.assertEqual((battle['damage'], battle['free_xp'], battle['_capture_order']), (2777, 321, observation))

    def test_alias_without_comparable_capture_order_only_fills_missing_facts(self):
        old = self.old_session()
        for arena in ('1', '2'):
            self.record(old, arena, 110, damage=1000)
        self.clock.value = 400
        staged = self.old_session('later-wall-clock', deferred=True)
        self.clock.value = 500
        for arena in ('1', '2'):
            correction = core_fixtures.result(arena_id=arena, damage=2100, free_xp=321, reconcile=True)
            if arena == '2':
                correction['_capture_order'] = [500000000, None, 0, 'a' * 32, 1]
            staged.result('EU:7', correction)
        staged.service.cancel_loading()

        self.clock.value = 200
        primary = self.open(self.game, 'direct-unstamped')
        self.clock.value = 250
        for arena in ('1', '2'):
            corrected = core_fixtures.result(arena_id=arena, damage=2777, free_xp=None, reconcile=True,
                                             vehicle_name='Vehicle 1', map_id='arena:17', map_name='Map 17')
            primary.result('EU:7', corrected, allow_new=True)
        self.clock.value = 600
        with changed(sessions, '_installation_keys', lambda root: (self.key, self.old_key)):
            migrated = self.open(self.alias, 'merge-unstamped')
        self.assertTrue(migrated.service.ready, migrated.service.last_error)
        for arena in ('1', '2'):
            key = migrated.battle_key('EU:7', arena)
            row = migrated.service._state['battles'][key]
            self.assertEqual((row['damage'], row['free_xp']), (2777, 321))
            resolved = core_fixtures.result(arena_id=arena)
            self.assertEqual([row[field] for field in ('vehicle_name', 'map_id', 'map_name')],
                             [resolved[field] for field in ('vehicle_name', 'map_id', 'map_name')])
            self.assertNotIn('_capture_order', row)
            self.assertEqual(row['_launch_id'], 'old-alias')

    def test_alias_accepts_a_provably_newer_result_and_preserves_known_launches(self):
        primary = self.open(self.game, 'direct')
        first = [500000000, None, 0, 'a' * 32, 1]
        confirmed = [100000000, None, 0, 'a' * 32, 2]
        self.record(primary, '1', 110, damage=1000, reconcile=True, _capture_order=first)
        primary.begin('EU:7', {'arena_id': '2', 'started_at': 110, 'vehicle_id': 1})
        legacy = self.old_session()
        self.record(legacy, '1', 110, damage=3000, reconcile=True, _capture_order=confirmed)
        self.record(legacy, '2', 110, damage=2000)
        self.clock.value = 200
        with changed(sessions, '_installation_keys', lambda root: (self.key, self.old_key)):
            migrated = self.open(self.alias, 'merge-newer-alias')
        self.assertTrue(migrated.service.ready, migrated.service.last_error)
        first_battle, second_battle = [migrated.service._state['battles'][migrated.battle_key('EU:7', arena)]
                                       for arena in ('1', '2')]
        self.assertEqual((first_battle['damage'], first_battle['_capture_order']), (3000, confirmed))
        self.assertEqual(second_battle['damage'], 2000)
        self.assertEqual([row['_launch_id'] for row in (first_battle, second_battle)], ['direct', 'direct'])

    def test_alias_merge_persists_net_from_the_final_credit_components(self):
        primary = self.open(self.game, 'direct')
        first = core_fixtures.result(complete=False, free_xp=None)
        first['currencies']['credits'].update(income=90000, costs=None)
        self.assertTrue(primary.result('EU:7', first, allow_new=True))
        legacy = self.old_session()
        second = core_fixtures.result(complete=False, damage=None)
        second['currencies']['credits'].update(income=75000, costs=43000)
        self.assertTrue(legacy.result('EU:7', second, allow_new=True))

        self.clock.value = 200
        with changed(sessions, '_installation_keys', lambda root: (self.key, self.old_key)):
            migrated = self.open(self.alias, 'merge-credits')
        self.assertTrue(migrated.service.ready, migrated.service.last_error)
        saved = migrated.service.store.load()
        row = saved['battles'][migrated.battle_key('EU:7', '1')]
        self.assertEqual(row['currencies']['credits']['net'], 47000)
        self.assertTrue(row['complete'])

    @unittest.skipUnless(os.name == 'nt', 'Requires an NTFS directory junction')
    def test_observed_windows_junction_and_physical_path_share_saved_history(self):
        with io.open(os.path.join(self.game, 'paths.xml'), 'wb') as handle:
            handle.write(b'<root><Paths><Path mask="*.wotmod" mode="recursive">./mods</Path></Paths></root>')
        code = subprocess.call([os.environ.get('COMSPEC', 'cmd.exe'), '/d', '/c', 'mklink', '/J',
                                self.alias, self.game], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if code:
            self.skipTest('The test drive cannot create directory junctions')
        try:
            observed = config_path.find_installation_root(Resources(xml=os.path.join(self.alias, 'paths.xml')))
            self.assertEqual(os.path.normcase(observed), os.path.normcase(self.alias))
            self.assertEqual(installation_key(observed), self.key)
            self.assertEqual(installation_key(native_data_path(observed)), self.key)
            self.assertNotEqual(self.old_key, self.key)
            old = self.old_session()
            self.record(old, '1', 110)
            self.clock.value = 120
            session = self.open(observed, 'resolved')
            self.assertEqual(session.snapshot()[0]['summary']['battles'], 1)
            self.assertTrue(session.accepts_installation(self.old_key))
            self.clock.value = 130
            restored = self.open(self.game, 'direct')
            self.assertEqual(restored.snapshot()[0]['summary']['battles'], 1)
            self.assertEqual(restored.service.store.directory, session.service.store.directory)
        finally:
            os.rmdir(self.alias)


if __name__ == '__main__':
    unittest.main()
