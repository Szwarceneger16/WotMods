# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import copy
import hashlib
import json
import os
import shutil
import tempfile
import unittest

from test_core import Clock, EXPECTED, result
from grz_session_stats.core import StatsService, aggregate_stats
from grz_session_stats import loading, storage, intake, runtime
from test_runtime import FakeAPI, FakeWindow
from test_normalize import raw_result, START, ARENA_ID


class StagedLoadingTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.mkdtemp(prefix='grz-staged-')
        self.clock = Clock(100)

    def tearDown(self):
        shutil.rmtree(self.directory)

    def service(self, launch='launch', deferred=True):
        return StatsService(self.directory, 'EU:7', launch, EXPECTED, self.clock, deferred=deferred)

    def finish(self, service):
        for unused in range(50000):
            if not service.loading:
                break
            service.advance_loading(max_steps=64)
        self.assertFalse(service.loading)
        self.assertTrue(service.ready, service.last_error)

    @staticmethod
    def contents(path):
        with open(path, 'rb') as handle:
            return handle.read()

    def seed(self, count=250):
        service = self.service(deferred=False)
        self.clock.value = 200
        service.record_result(result('0', started_at=110))
        sample = service._state['battles']['0']
        service._state['battles'] = dict((str(i), dict(copy.deepcopy(sample), arena_id=str(i))) for i in range(count))
        service.store.save(service._state)
        return service

    def test_deferred_constructor_does_not_decode_history_or_publish_partial_totals(self):
        seeded = self.seed()
        files = dict((name, self.contents(name)) for unused, name in seeded.store._files())
        service = self.service()
        self.assertTrue(service.loading)
        self.assertFalse(service.ready)
        self.assertEqual(service._state['battles'], {})
        self.assertTrue(service.snapshot()['loading'])
        self.assertFalse(service.set_page('manual', 'battles', 0))
        self.assertIsNone(service.reset_manual())
        self.assertEqual(files, dict((name, self.contents(name)) for name in files))
        self.finish(service)
        self.assertEqual(service.snapshot()['scopes']['manual']['summary']['battles'], 250)

    def test_loading_exposes_detached_current_process_beginnings_only(self):
        old = self.service('old-process')
        old.begin_battle('old', started_at=100, mode='random')
        old.cancel_loading()
        self.clock.value = 120
        service = self.service('current-process')
        service.begin_battle('live', started_at=121, mode='random')
        service.record_result(result('unobserved', started_at=110))
        for unused in range(50000):
            if not service.loading:
                break
            rows = service.launch_records()
            self.assertEqual([row['arena_id'] for row in rows], ['live'])
            rows[0]['vehicle_name'] = 'mutated copy'
            self.assertNotEqual(service.launch_records()[0].get('vehicle_name'), 'mutated copy')
            service.advance_loading(max_steps=1)
        self.assertTrue(service.ready, service.last_error)

    def test_clock_skewed_intake_preserves_original_ownership_after_restart(self):
        old = self.service('old-process')
        old.begin_battle('1', started_at=101, mode='random')
        old.record_result(result(started_at=101, ended_at=102))
        old.cancel_loading()
        self.clock.value = 200
        service = self.service('new-process')
        self.finish(service)
        row = service._state['battles']['1']
        self.assertEqual(row['_launch_id'], 'old-process')
        self.assertIsNotNone(row['_manual_id'])
        self.assertEqual(service.snapshot()['scopes']['manual']['summary']['battles'], 1)
        self.assertEqual(service.snapshot()['scopes']['launch']['summary']['battles'], 0)

    def test_all_load_phases_yield_and_match_full_recomputation(self):
        self.seed()
        service = self.service()
        phases = set()
        for unused in range(50000):
            phases.add(service.loading_phase)
            if not service.loading:
                break
            service.advance_loading(max_steps=1)
        self.assertTrue(service.ready, service.last_error)
        self.assertTrue({'history', 'storage', 'indexes', 'receipts'}.issubset(phases), phases)
        self.assertEqual(service.snapshot()['scopes']['manual']['summary'],
                         aggregate_stats(list(service._state['battles'].values()), service.expected_table))

    def test_new_results_before_and_during_index_build_are_preserved(self):
        self.seed()
        service = self.service()
        self.assertTrue(service.begin_battle('new', started_at=200, mode='random'))
        self.assertTrue(service.record_result(result('new', started_at=200, xp_received=2500)))
        while service.loading_phase != 'indexes' and service.loading:
            service.advance_loading(max_steps=1)
        self.assertTrue(service.record_result(result('0', started_at=110, xp_received=7777, reconcile=True)))
        self.finish(service)
        self.assertEqual(service._state['battles']['0']['xp_received'], 7777)
        self.assertEqual(service._state['battles']['new']['xp_received'], 2500)
        self.assertEqual(service.snapshot()['scopes']['manual']['summary']['battles'], 251)
        self.assertEqual(service._intake.events, [])

    def test_crash_before_any_history_load_preserves_original_launch(self):
        service = self.service('old-process')
        self.clock.value = 120
        service.begin_battle('1', started_at=110, mode='random')
        service.record_result(result('1', started_at=110))
        service.cancel_loading()
        self.clock.value = 300
        restored = self.service('new-process')
        self.finish(restored)
        self.assertEqual(restored._state['battles']['1']['_launch_id'], 'old-process')
        self.assertEqual(restored.snapshot()['scopes']['launch']['summary']['battles'], 0)
        self.assertEqual(restored.snapshot()['scopes']['manual']['summary']['battles'], 1)
        self.assertEqual(restored._state['launch_sessions'][0]['last_seen_at'], 120)

    def test_crash_between_ledger_commit_and_queue_cleanup_does_not_reapply(self):
        service = self.service()
        self.clock.value = 120
        service.record_result(result('1', started_at=110, xp_received=4321))
        original = service._intake.remove
        def fail_result(event):
            if event['kind'] == 'result':
                raise storage.StorageError('injected cleanup failure')
            return original(event)
        service._intake.remove = fail_result
        while service.loading:
            service.advance_loading()
        self.assertFalse(service.ready)
        revision = service._state['battles']['1']['revision']
        self.clock.value = 300
        restored = self.service('next')
        self.finish(restored)
        self.assertEqual(restored._state['battles']['1']['revision'], revision)
        self.assertEqual(restored._state['battles']['1']['xp_received'], 4321)
        self.assertFalse(restored._intake.events)

    def test_failed_intake_write_does_not_accept_or_publish_event(self):
        service = self.service()
        events = copy.deepcopy(service._intake.events)
        original = service._intake.store.save
        def fail(unused):
            raise storage.StorageError('injected disk failure')
        service._intake.store.save = fail
        try:
            self.assertFalse(service.record_result(result('1')))
            self.assertTrue(service.last_error)
            self.assertEqual(service._intake.events, events)
            self.assertFalse(service._received_context)
        finally:
            service._intake.store.save = original
        self.assertTrue(service.record_result(result('1')))
        self.finish(service)

    def test_queued_context_is_independent_of_caller_mutation(self):
        seeded = self.seed(1)
        expected = seeded._state['battles']['0']['vehicle_name']
        service = self.service()
        update = result('0', vehicle_name='Temporary fallback', reconcile=True)
        update['_deferred_context'] = {'fields': ['vehicle_name']}
        self.assertTrue(service.record_result(update))
        update['_deferred_context']['fields'][:] = []
        update['vehicle_name'] = 'Changed after receipt'
        self.finish(service)
        self.assertEqual(service._state['battles']['0']['vehicle_name'], expected)

    def test_writer_advancing_during_load_preserves_both_history_and_receipts(self):
        seeded = self.seed(1)
        service = self.service()
        service.record_result(result('queued', started_at=110))
        while service.loading_phase != 'storage' and service.loading:
            service.advance_loading(max_steps=1)
        self.assertTrue(seeded.record_result(result('other-writer', started_at=110)))
        while service.loading:
            service.advance_loading()
        self.assertFalse(service.ready)
        self.assertTrue(service._intake.events)
        restored = self.service('restart')
        self.finish(restored)
        self.assertIn('other-writer', restored._state['battles'])
        self.assertIn('queued', restored._state['battles'])

    def test_cancelled_service_rejects_late_writes_and_restart_replays(self):
        self.seed()
        service = self.service()
        service.record_result(result('late', started_at=110))
        for unused in range(3):
            service.advance_loading(max_steps=1)
        service.cancel_loading()
        self.assertFalse(service.record_result(result('ignored')))
        self.assertFalse(service.begin_battle('ignored'))
        restored = self.service('restart')
        self.finish(restored)
        self.assertIn('late', restored._state['battles'])
        self.assertNotIn('ignored', restored._state['battles'])

    def test_missing_metadata_uses_loaded_context_before_reconciliation(self):
        seeded = self.seed(1)
        old = seeded._state['battles']['0']
        service = self.service()
        update = result('0', started_at=None, vehicle_name='Unknown vehicle', map_name='Unknown map', reconcile=True)
        update['_deferred_context'] = {'fields': ['started_at', 'vehicle_name', 'map_name'], 'duration': 60}
        service.record_result(update)
        self.finish(service)
        row = service._state['battles']['0']
        self.assertEqual(row['vehicle_name'], old['vehicle_name'])
        self.assertEqual(row['map_name'], old['map_name'])
        self.assertEqual(row['started_at'], old['started_at'])
        self.assertEqual(row['ended_at'], old['started_at'] + 60)

    def test_unknown_installation_results_are_not_created_during_loading(self):
        service = self.service()
        service.record_result(dict(result('unknown'), _require_known=True))
        service.begin_battle('known', started_at=100, mode='random')
        service.record_result(dict(result('known'), _require_known=True))
        self.finish(service)
        self.assertNotIn('unknown', service._state['battles'])
        self.assertIn('known', service._state['battles'])

    def test_queued_receipt_older_than_a_manual_reset_keeps_original_period(self):
        seeded = self.seed(1)
        original_period = seeded._state['current_manual_id']
        self.clock.value = 300
        seeded.reset_manual()
        service = self.service()
        service.record_result(result('delayed', started_at=150))
        self.finish(service)
        self.assertEqual(service._state['battles']['delayed']['_manual_id'], original_period)
        self.assertEqual(service.snapshot()['scopes']['manual']['summary']['battles'], 0)

    def test_damaged_history_is_not_replaced_by_queued_events(self):
        seeded = self.seed(1)
        paths = [path for unused, path in seeded.store._files()]
        for path in paths:
            with open(path, 'wb') as handle:
                handle.write(b'broken')
        service = self.service()
        service.record_result(result('queued'))
        while service.loading:
            service.advance_loading()
        self.assertTrue(service.store.read_only)
        self.assertFalse(service.ready)
        self.assertTrue(service._intake.events)
        for path in paths:
            with open(path, 'rb') as handle:
                self.assertEqual(handle.read(), b'broken')

    def test_ambiguous_personal_vehicle_uses_saved_identity_after_loading(self):
        from grz_session_stats.normalize import normalize_result
        seeded = self.seed(2)
        old = seeded._state['battles']['1']
        raw = raw_result()
        raw['arenaUniqueID'] = 1
        personal = raw['personal']
        original = next(value for key, value in personal.items() if key != 'avatar')
        personal[2] = dict(original, typeCompDescr=2, damageDealt=9999)
        deferred = normalize_result(raw, {'account_dbid': 7, '_loading': True})
        self.assertEqual(len(deferred['_deferred_candidates']), 2)
        service = self.service()
        service.record_result(deferred)
        self.finish(service)
        row = service._state['battles']['1']
        self.assertEqual(row['vehicle_id'], old['vehicle_id'])
        self.assertNotEqual(row['damage'], 9999)
        self.assertEqual(row['vehicle_name'], old['vehicle_name'])

    def test_intake_limit_rejects_unaccepted_event_without_truncation(self):
        service = self.service()
        previous = copy.deepcopy(service._intake.events)
        limit = intake.MAX_INTAKE_BYTES
        intake.MAX_INTAKE_BYTES = 1500
        try:
            self.assertFalse(service.record_result(result('large', vehicle_name='x' * 2000)))
            self.assertEqual(service._intake.events, previous)
            self.assertTrue(service.last_error)
        finally:
            intake.MAX_INTAKE_BYTES = limit
        self.finish(service)
        self.assertNotIn('large', service._state['battles'])

    def test_corrupt_intake_cannot_be_discarded_by_loading_history(self):
        service = self.service()
        service.cancel_loading()
        for unused, path in service._intake.store._files():
            with open(path, 'wb') as handle:
                handle.write(b'broken intake')
        restored = self.service()
        self.assertFalse(restored.loading)
        self.assertFalse(restored.ready)
        self.assertTrue(restored.store.read_only)
        self.assertFalse(restored.record_result(result('rejected')))

    def test_streaming_reader_and_digest_match_standard_json_across_small_blocks(self):
        document = {'payload': {'battles': dict((str(i), {'text': 'Zażółć \\"\\n', 'number': 1.23e-45,
                     'values': [True, False, None, 12345678901234567890]}) for i in range(25))}}
        raw = storage.canonical_bytes(document)
        path = os.path.join(self.directory, 'stream.json')
        with open(path, 'wb') as handle:
            handle.write(raw)
        old_block = loading.BLOCK
        try:
            for block in (7, 16, 31, 64):
                loading.BLOCK = block
                output = [None]
                loading.complete(loading.read_json_steps(path, len(raw), ValueError('oversize'), output))
                self.assertEqual(output[0][0], document)
                self.assertEqual(output[0][1], hashlib.sha256(raw).hexdigest())
                digest = [None]
                loading.complete(loading.digest_steps(document, digest))
                self.assertEqual(digest[0], hashlib.sha256(raw).hexdigest())
        finally:
            loading.BLOCK = old_block

    def test_streaming_reader_rejects_trailing_tokens_commas_and_truncation(self):
        path = os.path.join(self.directory, 'bad.json')
        old_block = loading.BLOCK
        loading.BLOCK = 7
        try:
            for raw in (b'{"a": 1,}', b'[true,]', b'{"a": 1e}', b'{"a": []} false', b'{"a": [1, 2'):
                with open(path, 'wb') as handle:
                    handle.write(raw)
                steps = loading.read_json_steps(path, 100, ValueError('oversize'), [None])
                self.assertRaises(ValueError, loading.complete, steps)
        finally:
            loading.BLOCK = old_block


class StagedRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.mkdtemp(prefix='grz-staged-runtime-')
        self.clock = Clock(START - 10)
        self.api, self.window = FakeAPI(), FakeWindow()
        self.mod = runtime.Runtime(api=self.api, data_dir=self.directory, expected_table=EXPECTED,
                                   now=self.clock, window=self.window, footer_installer=lambda unused: None,
                                   installation_dir=self.directory)
        self.mod.start()

    def tearDown(self):
        self.mod.stop()
        shutil.rmtree(self.directory)

    def finish(self):
        for unused in range(10000):
            if self.mod._load_id is None:
                break
            self.api.fire(self.mod._load_id)
        self.assertFalse(self.mod._loading_services())
        self.assertTrue(self.mod.active_service.ready, self.mod.active_service.last_error)

    def test_default_runtime_receives_results_while_loading_and_updates_panel(self):
        self.assertTrue(self.mod.active_service.loading)
        self.assertTrue(self.mod.snapshot()['loading'])
        self.clock.value = START + 400
        self.mod._on_results(True, raw_result())
        self.finish()
        self.assertIn(str(ARENA_ID), self.mod.active_service._state['battles'])
        self.assertGreater(self.window.refreshes, 0)

    def test_battle_pauses_history_work_but_keeps_durable_capture(self):
        service = self.mod.active_service
        self.api.battle = True
        self.api.context = {'arena_id': str(ARENA_ID), 'started_at': START, 'vehicle_id': 1, 'map_id': 'map'}
        self.clock.value = START + 10
        self.mod._on_avatar()
        self.api.fire(self.mod._load_id)
        self.assertEqual(service.loading_phase, 'history')
        self.assertEqual(service._state['battles'], {})
        self.assertTrue(any(event['kind'] == 'begin' for event in service._intake.events))
        self.api.battle = False
        self.finish()
        self.assertIn(str(ARENA_ID), service._state['battles'])

    def test_account_switch_and_old_callback_keep_receipts_with_original_account(self):
        first = self.mod.active_service
        self.clock.value = START + 400
        self.mod._on_results(True, raw_result())
        self.api.dbid = 8
        self.mod._on_account()
        second = self.mod.active_service
        self.finish()
        self.assertTrue(first.ready)
        self.assertIn(str(ARENA_ID), first._state['battles'])
        self.assertNotIn(str(ARENA_ID), second._state['battles'])

    def test_stop_and_restart_preserve_intake_and_disable_retained_callback(self):
        old = self.mod.active_service
        callback = self.api.callbacks[self.mod._load_id][1]
        self.clock.value = START + 400
        self.mod._on_results(True, raw_result())
        self.mod.stop()
        callback()
        self.assertTrue(old._closed)
        self.mod.start()
        self.assertIsNot(self.mod.active_service, old)
        self.finish()
        self.assertIn(str(ARENA_ID), self.mod.active_service._state['battles'])

    def test_failed_scheduling_keeps_capture_and_recovers_on_retry(self):
        self.api.cancel(self.mod._load_id)
        self.mod._load_id = None
        schedule = self.api.schedule
        def fail(seconds, callback):
            raise RuntimeError('injected timer failure')
        self.api.schedule = fail
        self.mod._schedule_loading()
        self.assertIn('timer:loading', self.mod.compatibility_warnings)
        self.clock.value = START + 400
        self.mod._on_results(True, raw_result())
        self.assertTrue(any(event['kind'] == 'result' for event in self.mod.active_service._intake.events))
        self.api.schedule = schedule
        self.mod._ensure_service()
        self.assertNotIn('timer:loading', self.mod.compatibility_warnings)
        self.finish()
        self.assertIn(str(ARENA_ID), self.mod.active_service._state['battles'])
