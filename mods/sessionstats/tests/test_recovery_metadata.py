# -*- coding: utf-8 -*-
"""Recovery hints and user actions never manufacture battle results."""
from __future__ import unicode_literals

import copy
import io
import os
import shutil
import tempfile
import unittest

import test_result_cache_recovery as cache_fixtures
from test_normalize import raw_result, ARENA_ID, START
from grz_session_stats import recovery


def entry(**changes):
    value = {'attempts': 1, 'failures': 1, 'unavailable_count': 1,
             'last_attempt': 100, 'next_attempt': 105,
             'status': 'unavailable', 'code': -10, 'source': 'cache'}
    value.update(changes)
    return value


class RecoveryStoreTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.mkdtemp(prefix='grz-recovery-hints-')

    def tearDown(self):
        shutil.rmtree(self.directory)

    def test_restore_and_no_writes_when_identical(self):
        hints = recovery.RecoveryStore(self.directory, 'EU:7')
        self.assertTrue(hints.put('1', entry(), 130))
        sequence = hints.store.sequence
        self.assertFalse(hints.put('1', entry(), 130))
        self.assertEqual(hints.store.sequence, sequence)
        restored = recovery.RecoveryStore(self.directory, 'EU:7')
        self.assertEqual(restored.entries['1'], recovery.clean_entry(entry()))
        self.assertEqual(restored.pause_until, 130)
        self.assertFalse(restored.warning)

    def test_accounts_and_regions_have_distinct_metadata(self):
        first = recovery.RecoveryStore(self.directory, 'EU:7')
        first.put('1', entry())
        for owner in ('EU:8', 'NA:7'):
            other = recovery.RecoveryStore(self.directory, owner)
            self.assertEqual(other.entries, {})
            self.assertNotEqual(other.store.directory, first.store.directory)

    def test_corrupt_latest_generation_falls_back_without_touching_ledger(self):
        hints = recovery.RecoveryStore(self.directory, 'EU:7')
        hints.put('1', entry())
        hints.put('1', entry(attempts=2))
        latest = hints.store._files()[0][1]
        with io.open(latest, 'wb') as handle:
            handle.write(b'not-json')
        restored = recovery.RecoveryStore(self.directory, 'EU:7')
        self.assertEqual(restored.entries['1']['attempts'], 1)
        self.assertFalse(restored.warning)

    def test_concurrent_writer_never_overwrites_other_installations_hints(self):
        first = recovery.RecoveryStore(self.directory, 'EU:7')
        second = recovery.RecoveryStore(self.directory, 'EU:7')
        first.put('1', entry())
        second.put('2', entry(attempts=2))
        self.assertTrue(second.warning)
        restored = recovery.RecoveryStore(self.directory, 'EU:7')
        self.assertEqual(set(restored.entries), {'1'})

    def test_invalid_ids_and_unsafe_fields_cannot_enter_metadata(self):
        hints = recovery.RecoveryStore(self.directory, 'EU:7')
        for identifier in ('', '0', '-1', '1.5', 'x' * 100, None, 1):
            self.assertFalse(hints.put(identifier, entry()))
        hints.put(b'1', entry(source='PRIVATE', reason='PRIVATE', code=-987654321))
        restored = recovery.RecoveryStore(self.directory, 'EU:7').entries['1']
        self.assertIsNone(restored['source'])
        self.assertIsNone(restored['reason'])
        self.assertIsNone(restored['code'])
        self.assertNotIn('PRIVATE', str(restored))

    def test_bounded_metadata_evicts_complete_first_and_compacts(self):
        previous = recovery.MAX_ENTRIES
        recovery.MAX_ENTRIES = 8
        try:
            hints = recovery.RecoveryStore(self.directory, 'EU:7')
            hints.put('1', entry(status='complete', last_attempt=1000))
            for index in range(2, 11):
                hints.put(str(index), entry(last_attempt=index))
            self.assertEqual(len(hints.entries), 8)
            self.assertNotIn('1', hints.entries)
            self.assertNotIn('2', hints.entries)
            self.assertEqual(recovery.RecoveryStore(self.directory, 'EU:7').entries, hints.entries)
            for index in range(130):
                hints.put('10', entry(attempts=index, last_attempt=index))
            self.assertEqual(recovery.RecoveryStore(self.directory, 'EU:7').entries, hints.entries)
            self.assertEqual(len(hints.store._files()), 3)
        finally:
            recovery.MAX_ENTRIES = previous


class RecoveryMetadataRuntimeTests(unittest.TestCase):
    setUp = cache_fixtures.RecoveryRuntimeTests.__dict__['setUp']
    tearDown = cache_fixtures.RecoveryRuntimeTests.__dict__['tearDown']
    new_runtime = cache_fixtures.RecoveryRuntimeTests.__dict__['new_runtime']
    enter_battle = cache_fixtures.RecoveryRuntimeTests.__dict__['enter_battle']
    garage = cache_fixtures.RecoveryRuntimeTests.__dict__['garage']
    tick = cache_fixtures.RecoveryRuntimeTests.__dict__['tick']
    receive = cache_fixtures.RecoveryRuntimeTests.__dict__['receive']
    summary = cache_fixtures.RecoveryRuntimeTests.__dict__['summary']

    def view(self):
        return self.mod.snapshot()['scopes']['manual']['battles'][0]['recovery']

    def test_never_received_partial_and_unknown_outcome_have_separate_reasons(self):
        self.enter_battle()
        self.garage()
        self.assertEqual(self.view()['report_state'], 'never_received')
        self.assertEqual(self.view()['status'], 'queued')
        raw = raw_result()
        raw['common'].pop('winnerTeam')
        self.api.events.onBattleResultsReceived(True, raw)
        self.assertEqual(self.view()['report_state'], 'outcome_missing')
        self.assertEqual(self.view()['reason'], 'winner_missing')
        self.assertEqual(self.view()['source'], 'event')
        raw = raw_result()
        raw['personal'][1]['xp'] = None
        self.api.events.onBattleResultsReceived(True, raw)
        # Complementary reports may already have supplied the missing XP.
        self.assertEqual(self.view()['report_state'], 'complete')
        self.assertFalse(self.view()['retry_allowed'])
        self.assertIsNone(self.view()['next_attempt'])

    def test_repeated_unavailable_backoff_and_attempts_survive_restart(self):
        self.enter_battle()
        self.garage()
        key = (self.mod.active_key, ARENA_ID)
        for index in range(11):
            due = self.mod.retries.get(key, (0, self.clock.value))[1]
            self.tick(seconds=max(5, due - self.clock.value))
            self.receive(-10, None)
            delay = self.mod.retries[key][1] - self.clock.value
            self.assertLessEqual(delay, recovery.MAX_DELAY)
            if index >= 2:
                self.assertGreaterEqual(delay, 1800)
        before = copy.deepcopy(self.mod._recovery_details[key])
        ledger = copy.deepcopy(self.mod.active_service._state['battles'])
        self.mod.stop()
        self.api.cache = cache_fixtures.NativeCache()
        self.clock.value += 1
        self.mod = self.new_runtime()
        self.assertEqual(self.mod._recovery_details[key], before)
        self.tick()
        self.assertEqual(self.api.cache.requests, [])
        self.assertEqual(self.view()['status'], 'unavailable')
        self.assertEqual(self.view()['attempts'], 11)
        self.assertEqual(self.mod.active_service._state['battles'], ledger)

    def test_refresh_retry_and_restart_cannot_bypass_shared_rate_limit(self):
        self.enter_battle()
        self.garage()
        second = str(int(ARENA_ID) + 1)
        self.mod.active_service.begin_battle(second, started_at=START + 1, mode='random')
        self.tick()
        self.receive(-14, None)
        pause = self.mod._recovery_pause[self.mod.active_key]
        self.mod.on_action({'action': 'retry_result', 'account_key': self.mod.active_key, 'arena_id': second})
        self.mod.on_action({'action': 'refresh'})
        self.assertEqual(self.api.cache.requests, [])
        self.assertFalse(self.view()['retry_allowed'])
        self.mod.stop()
        self.api.cache = cache_fixtures.NativeCache()
        self.clock.value += 1
        self.mod = self.new_runtime()
        self.mod.on_action({'action': 'refresh'})
        self.assertEqual(self.api.cache.requests, [])
        self.assertEqual(self.mod._recovery_pause[self.mod.active_key], pause)
        self.tick(seconds=30)
        self.assertEqual(len(self.api.cache.requests), 1)

    def test_retry_validates_ledger_account_battle_and_native_byte_id(self):
        self.enter_battle()
        self.garage()
        for owner, identifier in (('EU:8', ARENA_ID), ('EU:7', '1'), ('EU:7', '-1')):
            self.mod.on_action({'action': 'retry_result', 'account_key': owner, 'arena_id': identifier})
        self.api.battle = True
        self.mod.on_action({'action': 'retry_result', 'account_key': 'EU:7', 'arena_id': ARENA_ID})
        self.assertEqual(self.api.cache.requests, [])
        self.api.battle = False
        self.mod.on_action({'action': 'retry_result', 'account_key': 'EU:7', 'arena_id': ARENA_ID.encode('ascii')})
        self.assertEqual(len(self.api.cache.requests), 1)
        self.assertEqual(self.view()['status'], 'in_flight')
        self.mod.on_action({'action': 'retry_result', 'account_key': 'EU:7', 'arena_id': ARENA_ID})
        self.assertEqual(len(self.api.cache.requests), 1)
        self.receive(1, raw_result())
        self.mod.on_action({'action': 'retry_result', 'account_key': 'EU:7', 'arena_id': ARENA_ID})
        self.assertEqual(self.api.cache.requests, [])

    def test_invalid_callbacks_and_timeout_leave_explainable_states(self):
        self.enter_battle()
        self.garage()
        for code, raw, reason in ((1, [], 'identity_mismatch'),
                                  ('private', None, 'invalid_status')):
            self.tick(seconds=300)
            self.receive(code, raw)
            self.assertEqual(self.view()['status'], 'rejected')
            self.assertEqual(self.view()['reason'], reason)
        self.tick(seconds=300)
        old = self.api.cache.requests.pop()[1]
        self.clock.value += 31
        # Keep a native pause so expiration is observable before redispatch.
        self.mod._recovery_pause[self.mod.active_key] = self.clock.value + 5
        self.mod._poll_one(self.mod.active_service, self.mod.active_key)
        self.assertEqual(self.view()['reason'], 'timeout')
        old(-10, None)
        self.assertEqual(self.view()['reason'], 'timeout')

    def test_metadata_only_polling_does_not_write_idle_hints(self):
        self.enter_battle()
        self.garage()
        self.tick()
        self.receive(-10, None)
        hints = self.mod._recovery_stores[self.mod.active_key]
        sequence = hints.store.sequence
        for unused in range(20):
            self.mod.snapshot()
            self.mod._poll_one(self.mod.active_service, self.mod.active_key)
        self.assertEqual(hints.store.sequence, sequence)

    def test_open_panel_receives_changed_states_without_idle_repainting(self):
        self.enter_battle()
        self.garage()
        self.mod.open_window()
        before = self.mod.window.refreshes
        self.tick()
        self.assertEqual(self.mod.window.refreshes, before + 1)
        self.receive(-10, None)
        self.assertEqual(self.mod.window.refreshes, before + 2)
        for unused in range(10):
            self.mod._publish_activity()
        self.assertEqual(self.mod.window.refreshes, before + 2)

    def test_refresh_of_1000_pending_records_performs_at_most_one_hint_write(self):
        class PendingService(object):
            ready = True
            loading = False
            def pending_arena_ids(self):
                return list(identifiers)
        identifiers = [str(int(ARENA_ID) + index) for index in range(1000)]
        self.mod.active_service = PendingService()
        hints = self.mod._recovery_stores[self.mod.active_key]
        for identifier in identifiers:
            key = (self.mod.active_key, identifier)
            detail = recovery.clean_entry(entry(last_attempt=self.clock.value - 20,
                                                next_attempt=self.clock.value + 999))
            hints.entries[identifier] = detail
            self.mod._recovery_details[key] = dict(detail)
            self.mod.retries[key] = (1, detail['next_attempt'])
        sequence = hints.store.sequence
        self.mod.on_action({'action': 'refresh'})
        self.assertEqual(len(self.api.cache.requests), 1)
        self.assertLessEqual(hints.store.sequence - sequence, 1)

    def test_soft_details_follow_store_eviction_and_do_not_grow_forever(self):
        previous = recovery.MAX_ENTRIES
        recovery.MAX_ENTRIES = 8
        try:
            for index in range(40):
                identifier = str(int(ARENA_ID) + index)
                self.mod._update_recovery((self.mod.active_key, identifier), status='complete')
            self.assertEqual(len(self.mod._recovery_details), 8)
            self.assertEqual(self.mod._recovery_states, {})
            self.assertEqual(self.mod.retries, {})
        finally:
            recovery.MAX_ENTRIES = previous

    def test_manual_retry_has_one_dynamic_acknowledgment_for_cached_rows(self):
        self.enter_battle()
        self.garage()
        self.mod.on_action({'action': 'retry_result', 'account_key': 'EU:7', 'arena_id': ARENA_ID})
        selected = self.mod.snapshot()['recovery']['selected']
        self.assertEqual(selected['id'], ARENA_ID)
        self.assertEqual(selected['status'], 'in_flight')
        self.receive(1, raw_result())
        selected = self.mod.snapshot()['recovery']['selected']
        self.assertEqual(selected['report_state'], 'complete')
        self.assertFalse(selected['retry_allowed'])

    def test_8_100_1000_due_records_are_serial_and_old_work_is_fair(self):
        class PendingService(object):
            ready = True
            loading = False
            def __init__(self, identifiers):
                self.identifiers = identifiers
            def pending_arena_ids(self):
                return list(self.identifiers)
        for size in (8, 100, 1000):
            identifiers = [str(int(ARENA_ID) + index) for index in range(size)]
            service = PendingService(identifiers)
            self.mod.retries.clear()
            self.mod.inflight.clear()
            self.mod._recovery_details.clear()
            self.mod._recovery_states.clear()
            self.mod._recovery_stores[self.mod.active_key] = recovery.RecoveryStore(None, self.mod.active_key)
            self.mod._observed_arenas = {(self.mod.active_key, identifiers[0])}
            self.mod._recovery_pause.clear()
            self.mod._recovery_live_streak = 0
            seen = set()
            for unused in range(size * 2):
                self.clock.value += 5
                self.mod._poll_one(service, self.mod.active_key)
                self.assertEqual(len(self.api.cache.requests), 1)
                identifier = self.receive(-1, None)
                seen.add(identifier)
                if len(seen) == size:
                    break
            self.assertEqual(seen, set(identifiers))
            self.assertLessEqual(unused + 1, size * 2)
            self.assertLessEqual(self.mod._recovery_live_streak, 3)


if __name__ == '__main__':
    unittest.main()
