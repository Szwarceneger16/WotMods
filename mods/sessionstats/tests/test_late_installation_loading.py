# -*- coding: utf-8 -*-
"""Late installation discovery must retain live provenance during startup."""
from __future__ import unicode_literals

import errno
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
import uuid

from test_core import Clock, EXPECTED
from test_config_path import changed
from test_normalize import normalize_result, raw_result, START, ARENA_ID
from test_runtime import FakeAPI, FakeWindow, Obj, wait_for_combat_capture
from grz_session_stats import capture_order, config_path, runtime
from grz_session_stats.combat_intake import CombatIntake
from grz_session_stats.core import StatsService
from grz_session_stats.localization import message
from grz_session_stats.sessions import InstallationSession


_DELAYED_PUBLISHER = '''
import json, os, sys, time

source, directory, account, payload, lock_held, fallback_wall = sys.argv[1:]
sys.path.insert(0, source)
from grz_session_stats import capture_order
from grz_session_stats.combat_intake import CombatIntake

if fallback_wall:
    capture_order._boot_clock = lambda: (None, None)
    capture_order.time = type('WallClock', (object,), {'time': staticmethod(lambda: float(fallback_wall))})
payload = json.loads(payload)
writer = CombatIntake(directory, payload['launch_id'])
payload['record']['_capture_order'] = order = writer.capture_order()
ready, release = [os.path.join(directory, name) for name in ('older-started', 'publish-older')]

def wait(callback):
    def blocked(*args):
        with open(ready, 'w') as handle:
            json.dump(order, handle)
        deadline = time.time() + 15
        while not os.path.isfile(release):
            if time.time() > deadline:
                raise AssertionError('Test never released the foreign producer')
            time.sleep(0.01)
        return callback(*args)
    return blocked

if lock_held == 'yes':
    writer._write = wait(writer._write)
else:
    writer._publish_queue = wait(writer._publish_queue)
assert writer.submit(account, 'result', payload)
writer.close(wait=True)
assert not writer.failed and len(writer.pending(account, limit=3)) >= 1
'''


class LateInstallationLoadingTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.mkdtemp(prefix='grz-late-installation-')
        self.clock = Clock(START - 10)
        self.api = FakeAPI()
        self.resolver = changed(config_path, 'find_installation_root', lambda: None)
        self.resolver.__enter__()
        self.mod = self.open()

    def tearDown(self):
        wait_for_combat_capture(self.mod)
        self.mod.stop()
        self.resolver.__exit__(None, None, None)
        shutil.rmtree(self.directory)

    def open(self, root=None):
        mod = runtime.Runtime(api=self.api, data_dir=self.directory, expected_table=EXPECTED,
                              now=self.clock, window=FakeWindow(), footer_installer=lambda unused: None,
                              installation_dir=root)
        mod.start()
        return mod

    def begin(self):
        self.clock.value = START + 10
        self.api.battle = True
        self.api.context = {'arena_id': str(ARENA_ID), 'started_at': START,
                            'vehicle_id': 1, 'map_id': 'map'}
        self.mod._on_avatar()
        self.assertIsNone(self.mod._instance_session)
        self.assertTrue(self.mod.active_service.loading)
        wait_for_combat_capture(self.mod)

    def discover(self):
        self.mod._installation_dir = self.directory
        self.api.battle = False
        self.api.events.onAccountShowGUI()
        self.assertIsNotNone(self.mod._instance_session)

    def finish(self):
        self.api.battle = False
        self.api.events.onAccountShowGUI()
        self.load_history()
        self.api.fire(self.mod._tick_id)

    def load_history(self):
        for unused in range(10000):
            if self.mod._load_id is None:
                break
            self.api.fire(self.mod._load_id)
        self.assertFalse(self.mod._loading_services())
        self.assertTrue(self.mod.active_service.ready, self.mod.active_service.last_error)
        if self.mod._instance_session is not None:
            self.assertTrue(self.mod._instance_session.service.ready)

    def test_automatic_result_rebases_both_ledgers_cooperatively_and_replays_the_receipt(self):
        self.discover()
        self.finish()
        account = self.mod.active_key
        service = self.mod.active_service
        installation = self.mod._instance_session
        self.clock.value = START + 400
        peer = StatsService(self.directory, account, 'peer', EXPECTED, self.clock)
        peer_installation = InstallationSession(self.directory, self.directory, 'peer', EXPECTED, self.clock)
        peer_id = str(int(ARENA_ID) + (1 << 32))
        peer_result = normalize_result(raw_result(arena_id=peer_id))
        self.assertTrue(peer.record_result(peer_result))
        self.assertTrue(peer_installation.result(account, peer_result, allow_new=True))

        self.api.events.onBattleResultsReceived(True, raw_result())
        self.assertTrue(service.history_reloading)
        self.assertIsNotNone(self.mod._load_id)
        self.assertFalse(service._state['battles'])
        self.assertFalse(installation.service._state['battles'])
        wait_for_combat_capture(self.mod)
        self.assertEqual(len(self.mod._combat_intake.pending(account)), 1)

        self.load_history()
        self.assertEqual(set(service._state['battles']), {ARENA_ID, peer_id})
        self.assertEqual(set(installation.service._state['battles']),
                         {installation.battle_key(account, arena) for arena in (ARENA_ID, peer_id)})
        self.assertEqual(self.mod._combat_intake.pending(account), [])

    def test_automatic_result_keeps_its_receipt_while_only_the_installation_reloads(self):
        self.discover()
        self.finish()
        account = self.mod.active_key
        service = self.mod.active_service
        installation = self.mod._instance_session
        self.clock.value = START + 400
        peer = InstallationSession(self.directory, self.directory, 'peer', EXPECTED, self.clock)
        peer_id = str(int(ARENA_ID) + (1 << 32))
        peer_result = normalize_result(raw_result(arena_id=peer_id))
        self.assertTrue(peer.result('EU:8', peer_result, allow_new=True))

        self.api.events.onBattleResultsReceived(True, raw_result())
        self.assertIn(ARENA_ID, service._state['battles'])
        self.assertTrue(installation.service.history_reloading)
        self.assertFalse(installation.service._state['battles'])
        self.assertEqual(len(self.mod._combat_intake.pending(account)), 1)

        self.load_history()
        self.assertEqual(set(service._state['battles']), {ARENA_ID})
        self.assertEqual(set(installation.service._state['battles']),
                         {installation.battle_key(account, ARENA_ID), installation.battle_key('EU:8', peer_id)})
        self.assertEqual(self.mod._combat_intake.pending(account), [])

    def discover_after_failed_binding(self):
        self.begin()
        self.clock.value = START + 400
        self.api.events.onBattleResultsReceived(True, raw_result())
        wait_for_combat_capture(self.mod)
        intake = self.mod._combat_intake
        publish = intake._publish
        attempts = []

        def fail_first_marker(path, encoded):
            if path.endswith('.installation'):
                attempts.append(path)
                if len(attempts) == 1:
                    raise OSError(errno.EACCES, 'Synthetic temporary file lock')
            return publish(path, encoded)

        intake._publish = fail_first_marker
        self.mod._installation_dir = self.directory
        self.api.battle = False
        self.assertIsNotNone(self.mod._ensure_installation_session())
        self.mod._schedule_loading()
        self.load_history()
        account, service = self.mod.active_key, self.mod.active_service
        self.mod._drain_account_captures(intake, account, service)
        self.assertEqual(len(attempts), 1)
        self.assertIsNone(intake.bound_installation(runtime.LAUNCH_ID))
        self.assertEqual(service.snapshot()['scopes']['manual']['summary']['battles'], 1)
        self.assertEqual(self.mod._instance_session.snapshot()[0]['summary']['battles'], 0)
        self.assertEqual([row[1] for row in intake.pending(account, limit=2)], ['begin', 'result'])
        return intake, attempts

    def test_transient_marker_failure_retries_in_garage_before_acknowledging(self):
        intake, attempts = self.discover_after_failed_binding()
        account = self.mod.active_key
        self.mod._drain_installation_captures(intake, account, self.mod.active_service)
        self.assertEqual(self.mod._instance_session.snapshot()[0]['summary']['battles'], 0)
        self.assertEqual([row[1] for row in intake.pending(account, limit=2)], ['begin', 'result'])
        self.api.fire(self.mod._tick_id)
        self.assertEqual(len(attempts), 2)
        session = self.mod._instance_session
        self.assertEqual(intake.bound_installation(runtime.LAUNCH_ID), session.service.account_key)
        self.assertEqual(session.snapshot()[0]['summary']['battles'], 1)
        self.assertEqual(intake.pending(self.mod.active_key), [])

    def test_transient_marker_failure_retries_at_shutdown_and_recovers_after_restart(self):
        intake, attempts = self.discover_after_failed_binding()
        self.mod.stop()
        self.clock.value = START + 86400
        with changed(runtime, 'LAUNCH_ID', uuid.uuid4().hex):
            self.mod = self.open(self.directory)
            self.finish()
            self.assertEqual(self.mod.active_service.snapshot()['scopes']['manual']['summary']['battles'], 1)
            session = self.mod._instance_session
            self.assertEqual(self.mod._combat_intake.pending(self.mod.active_key), [])
            self.assertEqual(session.snapshot()[0]['summary']['battles'], 1)
        self.assertEqual(len(attempts), 2)
        self.assertIsNotNone(intake.bound_installation(runtime.LAUNCH_ID))

    def test_garage_revision_survives_late_binding_and_restart_between_replay_batches(self):
        self.begin()
        self.clock.value = START + 410
        self.api.events.onBattleResultsReceived(True, raw_result())
        wait_for_combat_capture(self.mod)
        self.finish()
        self.assertIsNone(self.mod._instance_session)
        account = self.mod.active_key
        self.assertEqual(self.mod.active_service._state['battles'][ARENA_ID]['damage'], 2100)

        self.clock.value = START + 490
        revised = raw_result()
        revised['personal'][1]['damageDealt'] = 2700
        self.api.events.onBattleResultsReceived(True, revised)
        wait_for_combat_capture(self.mod)
        self.api.fire(self.mod._tick_id)
        self.assertEqual(self.mod.active_service._state['battles'][ARENA_ID]['damage'], 2700)

        self.discover()
        self.load_history()
        self.api.fire(self.mod._tick_id)
        # Installation replay consumes at most two captures per tick. The
        # correction must still exist after the earlier beginning and result.
        pending = self.mod._combat_intake.pending(account, limit=3)
        self.mod.stop()
        self.clock.value = START + 86400
        with changed(runtime, 'LAUNCH_ID', uuid.uuid4().hex):
            self.mod = self.open(self.directory)
            self.finish()
            installation = self.mod._instance_session
            battle_key = installation.battle_key(account, ARENA_ID)
            self.assertEqual(installation.service._state['battles'][battle_key]['damage'], 2700)
            self.assertEqual(self.mod.active_service._state['battles'][ARENA_ID]['damage'], 2700)
            self.assertEqual(self.mod._combat_intake.pending(account), [])
        self.assertEqual([(kind, capture['record']['damage']) for receipt, kind, capture in pending],
                         [('result', 2700)])

    def _delay_foreign_result(self, lock_held, fallback_wall=''):
        account = self.mod.active_key
        installation = self.mod._instance_session.service.account_key
        record = normalize_result(raw_result(), {'account_dbid': 7})
        payload = {'at': START + 410, 'launch_id': uuid.uuid4().hex, 'record': record,
                   'observed': True, 'installation': installation}
        source = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src')
        child = subprocess.Popen([sys.executable, '-B', '-c', _DELAYED_PUBLISHER, source,
                                  self.directory, account, json.dumps(payload), 'yes' if lock_held else 'no',
                                  fallback_wall])
        try:
            ready = os.path.join(self.directory, 'older-started')
            deadline = time.time() + 12
            while time.time() < deadline and child.poll() is None:
                try:
                    with open(ready) as handle:
                        return child, json.load(handle)
                except (IOError, ValueError):
                    time.sleep(0.01)
            self.fail('The independent older producer never reached its write barrier.')
        except BaseException:
            if child.poll() is None:
                child.terminate()
            child.wait()
            raise

    def _release_foreign_result(self, child):
        if child.poll() is None:
            with open(os.path.join(self.directory, 'publish-older'), 'wb'):
                pass
        deadline = time.time() + 12
        while child.poll() is None and time.time() < deadline:
            time.sleep(0.01)
        if child.poll() is None:
            child.terminate()
        self.assertEqual(child.wait(), 0)

    def _recorded_battle_pair(self):
        account = self.mod.active_service._state['battles'][ARENA_ID]
        installation = self.mod._instance_session
        identifier = installation.battle_key(self.mod.active_key, ARENA_ID)
        return account, installation.service._state['battles'][identifier]

    def test_foreign_lock_defers_newer_garage_write_and_commits_fifo(self):
        self.discover()
        self.finish()
        child, unused_order = self._delay_foreign_result(lock_held=True)
        try:
            self.clock.value = START + 600
            revised = raw_result()
            revised['personal'][1]['damageDealt'] = 2777
            self.mod._on_results(True, revised)
            self.assertNotIn(ARENA_ID, self.mod.active_service._state['battles'])
            self.assertEqual(self.mod._combat_intake.waiting(self.mod.active_key), 1)
        finally:
            self._release_foreign_result(child)
        wait_for_combat_capture(self.mod)
        self.mod._drain_combat_intake()
        self.assertEqual([row['damage'] for row in self._recorded_battle_pair()], [2777, 2777])
        self.assertEqual(self.mod._combat_intake.pending(self.mod.active_key), [])

    def test_newer_duplicate_survives_older_producer_delayed_before_lock_and_restart(self):
        self.discover()
        self.finish()
        self.clock.value = START + 580
        revised = raw_result()
        revised['personal'][1]['damageDealt'] = 2777
        del revised['personal'][1]['kills']
        self.mod._on_results(True, revised)
        original = [dict(row) for row in self._recorded_battle_pair()]
        child, older_order = self._delay_foreign_result(lock_held=False)
        try:
            self.clock.value = START + 600
            # A hardware monotonic clock still orders the two independent
            # processes when the wall clock retreats during the second read.
            if older_order[1] and older_order[1] == self.mod._combat_intake.clock_domain:
                class Rollback(object):
                    @staticmethod
                    def time():
                        return older_order[0] / 1000000.0 - 3600
                with changed(capture_order, 'time', Rollback):
                    self.mod._on_results(True, revised)
            else:
                self.mod._on_results(True, revised)
            for old, new in zip(original, self._recorded_battle_pair()):
                self.assertEqual(new['revision'], old['revision'])
                self.assertNotEqual(new['_capture_order'], old['_capture_order'])
        finally:
            self._release_foreign_result(child)
        self.mod.stop()
        self.clock.value = START + 86400
        with changed(runtime, 'LAUNCH_ID', uuid.uuid4().hex):
            self.mod = self.open(self.directory)
            self.finish()
            for battle in self._recorded_battle_pair():
                self.assertEqual(battle['damage'], 2777)
                self.assertEqual(battle['frags'], 2)  # Older receipt still fills a missing fact.
            self.assertEqual(self.mod._combat_intake.pending(self.mod.active_key), [])

    def test_unknown_boot_cannot_use_reversed_wall_clock_to_replace_durable_facts(self):
        self.mod.stop()
        with changed(capture_order, '_boot_clock', lambda: (None, None)):
            self.mod = self.open(self.directory)
            self.discover()
            self.finish()
            child, older = self._delay_foreign_result(lock_held=False, fallback_wall='2000')
            try:
                self.assertIsNone(older[1])
                self.clock.value = START + 600
                revised = raw_result()
                revised['personal'][1]['damageDealt'] = 2777
                del revised['personal'][1]['kills']
                with changed(capture_order, 'time', Obj(time=lambda: 1000)):
                    self.mod._on_results(True, revised)
                before = [dict(row) for row in self._recorded_battle_pair()]
                self.assertTrue(all(row['_capture_order'][0] < older[0] for row in before))
            finally:
                self._release_foreign_result(child)
            self.mod.stop()
            self.clock.value = START + 86400
            with changed(runtime, 'LAUNCH_ID', uuid.uuid4().hex):
                self.mod = self.open(self.directory)
                self.finish()
                for battle, saved in zip(self._recorded_battle_pair(), before):
                    self.assertEqual(battle['damage'], 2777)
                    self.assertEqual(battle['frags'], 2)
                    self.assertEqual(battle['_capture_order'], saved['_capture_order'])
                self.assertEqual(self.mod._combat_intake.pending(self.mod.active_key), [])

    def test_foreign_reader_leaves_unbound_receipts_for_late_discovery_and_reload(self):
        self.finish()
        self.clock.value = START + 410
        self.api.battle = True
        self.api.context = {'arena_id': str(ARENA_ID), 'started_at': START,
                            'vehicle_id': 1, 'map_id': 'map'}
        self.mod._on_avatar()
        self.mod._on_results(True, raw_result())
        wait_for_combat_capture(self.mod)
        account = self.mod.active_key
        original_launch = runtime.LAUNCH_ID
        observer = FakeAPI()
        with changed(runtime, 'LAUNCH_ID', uuid.uuid4().hex):
            other = runtime.Runtime(api=observer, data_dir=self.directory, expected_table=EXPECTED,
                                    now=Clock(START + 600), window=FakeWindow(),
                                    footer_installer=lambda unused: None, installation_dir=self.directory)
            other.start()
            try:
                for unused in range(10000):
                    if other._load_id is None:
                        break
                    observer.fire(other._load_id)
                other._drain_combat_intake()
                self.assertEqual(other.active_service._state['battles'][ARENA_ID]['damage'], 2100)
                self.assertTrue(other._combat_intake.launch_is_alive(original_launch))
                self.assertEqual(len(other._combat_intake.pending(account, limit=3)), 2)
                self.assertEqual(other._instance_session.service._state['battles'], {})
                # This correction arrives before the foreign beginning can
                # enter the local installation history. Keep it for replay.
                revised = raw_result()
                revised['personal'][1]['damageDealt'] = 2777
                other._on_results(True, revised)
                wait_for_combat_capture(other)
                self.assertEqual(len(other._combat_intake.pending(account, limit=4)), 3)
                self.assertEqual(other._instance_session.service._state['battles'], {})
            finally:
                other.stop()
        self.discover()
        self.finish()
        self.mod._drain_combat_intake()
        self.assertEqual([row['damage'] for row in self._recorded_battle_pair()], [2777, 2777])
        self.assertEqual(self.mod._combat_intake.pending(account), [])
        self.mod.stop()
        self.clock.value = START + 86400
        with changed(runtime, 'LAUNCH_ID', uuid.uuid4().hex):
            self.mod = self.open(self.directory)
            self.finish()
            self.assertEqual([row['damage'] for row in self._recorded_battle_pair()], [2777, 2777])

    def test_rereading_unchanged_posted_result_keeps_both_ledgers_write_free(self):
        self.discover()
        self.finish()
        self.clock.value = START + 600
        raw = raw_result()
        raw['personal'][1]['damageDealt'] = 2777
        self.mod._on_results(True, raw)
        self.api.posts[ARENA_ID] = Obj(results=raw, reusable=None)
        services = (self.mod.active_service, self.mod._instance_session.service)
        saved = [service.store.sequence for service in services]
        for unused in range(3):
            self.mod._refresh_posted()
        self.assertEqual([service.store.sequence for service in services], saved)
        stale = raw_result()
        reusable = Obj(personal=Obj(xpProgress={1: {'xp': 4550}}, isAddXPBonusApplied=True))
        self.api.posts[ARENA_ID] = Obj(results=stale, reusable=reusable)
        self.mod._refresh_posted()
        self.assertEqual([row['damage'] for row in self._recorded_battle_pair()], [2777, 2777])
        self.assertEqual([row['xp_received'] for row in self._recorded_battle_pair()], [4550, 4550])
        self.assertEqual([service.store.sequence for service in services], [sequence + 1 for sequence in saved])

    def test_passive_reread_repairs_saved_map_and_vehicle_placeholders_only(self):
        self.discover()
        self.finish()
        self.clock.value = START + 600
        revised = raw_result()
        revised['personal'][1]['damageDealt'] = 2777

        def unavailable(unused):
            raise LookupError('Synthetic resolver initially unavailable')

        self.api.vehicle_info = self.api.map_info = unavailable
        self.mod._on_results(True, revised)
        for row in self._recorded_battle_pair():
            self.assertEqual((row['vehicle_name'], row['map_id'], row['map_name']),
                             ('Vehicle 1', 'arena:17', 'Map 17'))
            self.assertNotIn('_arena_type_id', row)
            self.assertIn(message('normalize.vehicle'), row['warnings'])
            self.assertIn(message('normalize.map'), row['warnings'])

        services = (self.mod.active_service, self.mod._instance_session.service)
        self.api.posts[ARENA_ID] = Obj(results=raw_result(), reusable=None)  # Stores only 2100 damage.
        self.api.vehicle_info = lambda unused: {'name': 'Confirmed Vehicle'}
        self.api.map_info = lambda unused: {'id': 'resolved-geometry'}  # Native label still missing.
        self.mod._refresh_posted()
        for row in self._recorded_battle_pair():
            self.assertEqual((row['vehicle_name'], row['map_id'], row['map_name'], row['damage']),
                             ('Confirmed Vehicle', 'resolved-geometry', 'Map 17', 2777))
            self.assertIn(message('normalize.map'), row['warnings'])
        for service in services:
            self.assertEqual([item['id'] for item in service.snapshot()['scopes']['manual']['maps']],
                             ['resolved-geometry'])

        self.api.map_info = lambda unused: {'id': 'resolved-geometry', 'name': 'Confirmed Map'}
        self.mod._refresh_posted()
        for row in self._recorded_battle_pair():
            self.assertEqual(row['map_name'], 'Confirmed Map')
            self.assertNotIn(message('normalize.vehicle'), row['warnings'])
            self.assertNotIn(message('normalize.map'), row['warnings'])

        before = [service.store.sequence for service in services]
        self.api.vehicle_info = lambda unused: {'name': 'Other Vehicle'}
        self.api.map_info = lambda unused: {'id': 'other-geometry', 'name': 'Other Map'}
        self.mod._refresh_posted()
        for row in self._recorded_battle_pair():
            self.assertEqual((row['vehicle_name'], row['map_id'], row['map_name'], row['damage']),
                             ('Confirmed Vehicle', 'resolved-geometry', 'Confirmed Map', 2777))
        self.assertEqual([service.store.sequence for service in services], before)

    def test_old_applied_bonus_cannot_replace_a_newer_applied_bonus(self):
        self.discover()
        self.finish()
        self.clock.value = START + 600

        def bonus(xp):
            return Obj(personal=Obj(xpProgress={1: {'xp': xp}}, isAddXPBonusApplied=True))

        self.api.posts[ARENA_ID] = Obj(results=raw_result(), reusable=bonus(4550))
        self.mod._on_results(True, raw_result())
        revised = raw_result()
        revised['personal'][1]['damageDealt'] = 2777
        self.mod._on_posted(bonus(5000), Obj(getResults=lambda: Obj(results=revised)))
        self.mod._refresh_posted()
        for row in self._recorded_battle_pair():
            self.assertEqual((row['xp_received'], row['damage']), (5000, 2777))

        revised['personal'][1]['damageDealt'] = 2800
        self.mod._on_results(True, revised)
        for row in self._recorded_battle_pair():
            self.assertEqual((row['xp_received'], row['damage']), (5000, 2800))

        self.mod._on_posted(bonus(5100), Obj(getResults=lambda: Obj(results=revised)))
        self.assertEqual([row['xp_received'] for row in self._recorded_battle_pair()], [5100, 5100])

    def test_garage_result_survives_exit_between_ledger_writes(self):
        self.discover()
        self.finish()
        self.clock.value = START + 600
        account = self.mod.active_key
        identifier = self.mod._instance_session.battle_key(account, ARENA_ID)

        def interrupted(*args, **kwargs):
            raise KeyboardInterrupt()

        with changed(self.mod, '_record_installation', interrupted):
            with self.assertRaises(KeyboardInterrupt):
                self.mod._on_results(True, raw_result())
        self.assertTrue(self.mod.active_service._state['battles'][ARENA_ID]['complete'])
        self.assertNotIn(identifier, self.mod._instance_session.service._state['battles'])
        self.assertEqual(len(self.mod._combat_intake.pending(account)), 1)
        self.api.battle = True  # Prevent an orderly garage drain before reopening.
        self.restart()
        self.assertEqual([row['damage'] for row in self._recorded_battle_pair()], [2100, 2100])
        self.assertEqual(self.mod._combat_intake.pending(account), [])

    def test_live_unbound_producer_does_not_block_other_installation_receipts(self):
        self.discover()
        self.finish()
        self.clock.value = START + 600
        account = self.mod.active_key
        launch_id = 'a' * 32
        foreign = CombatIntake(self.directory, launch_id)
        install_key = self.mod._combat_installation
        keys = [str((number << 32) | START) for number in (12346, 12347, 12348)]

        def send(writer, launch, arena_id, origin):
            payload = self.mod._capture_payload(account, normalize_result(raw_result(arena_id=arena_id)), True)
            payload.update(launch_id=launch, installation=origin)
            self.assertTrue(writer.submit(account, 'result', payload))
            deadline = time.time() + 3
            while writer.waiting(account) and time.time() < deadline:
                time.sleep(0.005)
            self.assertFalse(writer.waiting(account))

        try:
            send(foreign, launch_id, keys[0], None)
            send(foreign, launch_id, keys[1], install_key)
            self.assertTrue(self.mod._combat_intake.launch_is_alive(launch_id))
            send(self.mod._combat_intake, runtime.LAUNCH_ID, keys[2], install_key)
            for unused in range(3):
                self.mod._drain_combat_intake()
            installation = self.mod._instance_session
            ids = [installation.battle_key(account, key) for key in keys]
            self.assertEqual(sorted(installation.service._state['battles']), [ids[2]])
            self.assertTrue(foreign.bind_installation(launch_id, install_key))
            self.mod._drain_combat_intake()
            self.assertEqual(sorted(installation.service._state['battles']), sorted(ids))
        finally:
            foreign.close(wait=True)

    def test_bound_receipts_recover_installation_while_logged_into_another_account(self):
        self.discover()
        self.finish()
        self.clock.value = START + 600
        account = self.mod.active_key
        self.api.battle = True
        for number in (12340, 12341):
            older_arena = str((number << 32) | (START - 60))
            record = normalize_result(raw_result(arena_id=older_arena))
            self.mod._stage_combat_capture('result', account, record, observed=False)
        self.api.context = {'arena_id': ARENA_ID, 'started_at': START, 'vehicle_id': 1, 'map_id': 'map'}
        self.mod._on_avatar()
        self.mod._on_results(True, raw_result())
        wait_for_combat_capture(self.mod)
        intake = self.mod._combat_intake
        with intake.account_transaction(account) as locked:
            self.assertTrue(locked)
            # A receipt written by 0.9.37 has no opaque installation battle key.
            begin, kind, capture = intake.pending(account, limit=4)[2]
            self.assertEqual(kind, 'begin')
            capture.pop('installation_battle')
            self.assertTrue(intake.ack(begin))
            intake._write(begin, kind, capture)
        self.assertEqual(len(intake.pending(account, limit=5)), 4)
        self.mod.stop()
        self.api.battle = False
        self.api.dbid = 8
        self.clock.value = START + 900
        with changed(runtime, 'LAUNCH_ID', uuid.uuid4().hex):
            self.mod = self.open(self.directory)
            self.finish()
            installation = self.mod._instance_session
            identifier = installation.battle_key(account, ARENA_ID)
            self.assertEqual(sorted(self.mod.services), ['EU:8'])
            self.assertEqual(installation.service._state['battles'][identifier]['damage'], 2100)
            self.assertEqual(len(self.mod._combat_intake.pending(account, limit=5)), 4)
            self.api.dbid = 7
            self.finish()
            self.mod._drain_combat_intake()
            self.assertEqual(self.mod.active_service._state['battles'][ARENA_ID]['damage'], 2100)
            self.assertEqual(self.mod._combat_intake.pending(account), [])

    def test_complete_history_recovers_metadata_after_restart_without_cached_result(self):
        self.discover()
        self.finish()
        self.clock.value = START + 600

        def unavailable(unused):
            raise LookupError('Synthetic resolver unavailable before restart')

        self.api.vehicle_info = self.api.map_info = unavailable
        revised = raw_result()
        revised['personal'][1]['damageDealt'] = 2777
        self.mod._on_results(True, revised)
        for row in self._recorded_battle_pair():
            self.assertTrue(row['complete'])
            self.assertEqual((row['vehicle_name'], row['map_id']), ('Vehicle 1', 'arena:17'))

        self.api.vehicle_info = lambda unused: {'name': 'Recovered Vehicle'}
        self.api.map_info = lambda unused: {'id': 'recovered-map', 'name': 'Recovered Map'}
        self.restart()
        for row in self._recorded_battle_pair():
            self.assertEqual((row['vehicle_name'], row['map_id'], row['map_name'], row['damage']),
                             ('Recovered Vehicle', 'recovered-map', 'Recovered Map', 2777))
        self.assertEqual(self.mod.active_service.metadata_candidates(None, 5), [])

    def test_repairs_installation_metadata_when_account_was_already_repaired(self):
        self.discover()
        self.finish()
        self.clock.value = START + 600
        self.api.vehicle_info = lambda unused: {'name': 'Resolved Vehicle'}
        self.api.map_info = lambda unused: {'id': 'resolved-map', 'name': 'Resolved Map'}
        self.mod._on_results(True, raw_result())
        installation = self.mod._instance_session
        identifier = installation.battle_key(self.mod.active_key, ARENA_ID)
        self.assertTrue(installation.service.record_result({
            'arena_id': identifier, 'reconcile': True,
            'map_id': 'arena:17', 'map_name': 'Map 17', 'vehicle_name': 'Vehicle 1'}))
        self.assertEqual(self.mod.active_service.metadata_candidates(None, 5), [])
        self.assertEqual(installation.service.metadata_candidates(None, 5), [identifier])
        self.restart()
        for row in self._recorded_battle_pair():
            self.assertEqual((row['vehicle_name'], row['map_id'], row['map_name']),
                             ('Resolved Vehicle', 'resolved-map', 'Resolved Map'))

    def restart(self):
        wait_for_combat_capture(self.mod)
        self.mod.stop()
        self.api.battle = False
        self.clock.value = START + 86400
        with changed(runtime, 'LAUNCH_ID', runtime.LAUNCH_ID + '-restart'):
            self.mod = self.open(self.directory)
        self.finish()

    def assert_recovered_once(self):
        self.mod._on_results(True, raw_result())
        session = self.mod._instance_session
        self.assertEqual(session.snapshot()[0]['summary']['battles'], 1)
        scope = session.snapshot()[0]
        self.mod._on_results(True, raw_result())
        self.assertEqual(session.snapshot()[0], scope)
        self.assertEqual(session.snapshot()[0]['summary']['battles'], 1)

    def test_shutdown_before_loading_finishes_retains_beginning_for_recovered_result(self):
        self.begin()
        self.discover()
        self.assertTrue(self.mod.active_service.loading)
        self.restart()
        self.assert_recovered_once()

    def test_shutdown_after_loading_finishes_retains_beginning_for_recovered_result(self):
        self.begin()
        self.discover()
        self.finish()
        self.restart()
        self.assert_recovered_once()

    def test_ready_backfill_keeps_result_with_original_account_after_switch(self):
        self.begin()
        first = self.mod.active_service
        self.clock.value = START + 400
        self.mod._on_results(True, raw_result())
        wait_for_combat_capture(self.mod)
        self.discover()
        self.api.battle = False
        self.api.dbid = 8
        self.mod._on_account()
        self.finish()
        self.assertTrue(first.ready, first.last_error)
        session = self.mod._instance_session
        records = session.service._state['battles']
        self.assertIn(InstallationSession.battle_key('EU:7', ARENA_ID), records)
        self.assertNotIn(InstallationSession.battle_key('EU:8', ARENA_ID), records)
        self.assertEqual(session.snapshot()[0]['summary']['battles'], 1)
