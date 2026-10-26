# -*- coding: utf-8 -*-
"""Performance regressions assert bounded work, not host-specific timing limits."""
from __future__ import unicode_literals

import copy
import json
import os
import random
import shutil
import tempfile
import unittest

from test_core import Clock, EXPECTED, result
from grz_session_stats.core import StatsService, aggregate_stats
from grz_session_stats import storage, projection


class HistoryPerformanceTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.mkdtemp(prefix='grz-history-performance-')
        self.clock = Clock(100)
        self.service = StatsService(self.directory, 'EU:7', 'run', EXPECTED, self.clock)
        self.clock.value = 200

    def tearDown(self):
        shutil.rmtree(self.directory)

    def reopen(self, launch='run'):
        service = StatsService(self.directory, 'EU:7', launch, EXPECTED, self.clock)
        self.assertFalse(service.store.read_only, service.last_error)
        return service

    def seed(self, count, groups=False):
        self.service.record_result(result('0'))
        sample = self.service._state['battles']['0']
        self.service._state['battles'] = dict((str(index), dict(copy.deepcopy(sample),
            arena_id=str(index), vehicle_id=index if groups else 1,
            map_id=str(index) if groups else 'map')) for index in range(count))
        self.service.store.save(self.service._state)
        self.service = self.reopen()

    def test_legacy_upgrade_only_encodes_changed_record_and_small_commit(self):
        self.seed(400)
        encoded, copied = [], []
        original_encode, original_copy = storage.canonical_bytes, copy.deepcopy
        def encode(value):
            data = original_encode(value)
            encoded.append(len(data))
            return data
        def deepcopy(value, *args, **kwargs):
            copied.append(value)
            if value is self.service._state or value is self.service._state['battles']:
                raise AssertionError('whole-history copy on a battle update')
            return original_copy(value, *args, **kwargs)
        storage.canonical_bytes, copy.deepcopy = encode, deepcopy
        try:
            self.assertTrue(self.service.begin_battle('new'))
            self.assertTrue(self.service.record_result(result('1', reconcile=True, xp_received=2345)))
        finally:
            storage.canonical_bytes, copy.deepcopy = original_encode, original_copy
        self.assertTrue(encoded)
        self.assertLess(max(encoded), 5000)
        self.assertEqual(self.reopen()._state, self.service._state)

    def test_all_groupings_are_paged_with_complete_period_totals(self):
        self.seed(125, groups=True)
        scope = self.service.snapshot()['scopes']['manual']
        self.assertEqual(scope['summary']['battles'], 125)
        for kind in ('battles', 'vehicles', 'maps'):
            seen = []
            for page in range(4):
                self.assertTrue(self.service.set_page('manual', kind, page))
                current = self.service.snapshot()['scopes']['manual']
                self.assertLessEqual(len(current[kind]), projection.PAGE_SIZE)
                seen.extend(row['id'] for row in current[kind])
                self.assertEqual(current['summary'], scope['summary'])
                self.assertEqual(current['pagination'][kind]['total'], 125)
            self.assertEqual(len(seen), 125)
            self.assertEqual(len(set(seen)), 125)
        self.service.set_page('manual', 'battles', 999999)
        self.assertEqual(self.service.snapshot()['scopes']['manual']['pagination']['battles']['page'], 3)

    def test_snapshot_only_rates_visible_battles_and_returns_independent_data(self):
        self.seed(400)
        calls = []
        original = projection.aggregate_stats
        def aggregate(records, table):
            calls.append(len(records))
            return original(records, table)
        projection.aggregate_stats = aggregate
        try:
            snapshot = self.service.snapshot()
        finally:
            projection.aggregate_stats = original
        self.assertEqual(sum(calls), projection.PAGE_SIZE * 2)
        snapshot['scopes']['manual']['summary']['xp_base']['sum'] = -999
        snapshot['scopes']['manual']['battles'][0]['stats']['wins'] = -999
        self.assertGreater(self.service.snapshot()['scopes']['manual']['summary']['xp_base']['sum'], 0)

    def assert_numbers(self, actual, expected):
        self.assertEqual(set(actual), set(expected))
        for key, value in expected.items():
            if isinstance(value, dict):
                self.assert_numbers(actual[key], value)
            elif isinstance(value, float):
                self.assertAlmostEqual(actual[key], value, places=6, msg=key)
            else:
                self.assertEqual(actual[key], value, key)

    def test_incremental_totals_match_full_recomputation_through_corrections_and_resets(self):
        rng = random.Random(19281)
        for index in range(90):
            self.clock.value += 1
            identifier = str(rng.randrange(20))
            if index % 4 == 0:
                self.service.begin_battle(identifier, started_at=self.clock.value, vehicle_id=1)
            else:
                record = result(identifier, started_at=105 + int(identifier),
                                xp_base=rng.randrange(2500), xp_received=rng.randrange(6000),
                                vehicle_id=rng.choice([1, 2]), outcome=rng.choice(['win', 'draw', 'loss']),
                                reconcile=True, complete=index % 3 != 0)
                record['currencies']['credits']['net'] = rng.randrange(-20000, 30000)
                record['warnings'] = ['partial'] if index % 7 else []
                self.service.record_result(record)
            if index == 45:
                self.service.reset_manual()
            for scope_name, field, identifier in (('launch', '_launch_id', self.service.launch_id),
                    ('manual', '_manual_id', self.service._state['current_manual_id'])):
                rows = [row for row in self.service._state['battles'].values() if row.get(field) == identifier]
                current = self.service.snapshot()['scopes'][scope_name]
                self.assert_numbers(current['summary'], aggregate_stats(rows, EXPECTED))
            if index in (30, 60):
                self.service = self.reopen()

    def test_overflow_recovers_after_revision_and_keeps_extrema(self):
        for identifier in ('a', 'b'):
            self.service.record_result(result(identifier, xp_base=1e308))
        self.assertIsNone(self.service.snapshot()['scopes']['manual']['summary']['xp_base']['sum'])
        self.service.record_result(result('a', xp_base=100, reconcile=True))
        stats = self.service.snapshot()['scopes']['manual']['summary']['xp_base']
        self.assertEqual(stats['sum'], 1e308)
        self.assertEqual(stats['min'], 100)
        self.service.record_result(result('b', xp_base=200, reconcile=True))
        self.assertEqual(self.service.snapshot()['scopes']['manual']['summary']['xp_base']['sum'], 300)

    def test_failed_commit_does_not_change_indexes_and_retry_discards_only_uncommitted_tail(self):
        self.service.record_result(result('a'))
        before = copy.deepcopy(self.service._state)
        summary = self.service.snapshot()['scopes']['manual']['summary']
        original = storage.os.rename
        def fail(*args):
            raise OSError('crash before commit marker')
        storage.os.rename = fail
        try:
            self.assertFalse(self.service.record_result(result('a', xp_received=9999, reconcile=True)))
        finally:
            storage.os.rename = original
        self.assertEqual(self.service._state, before)
        self.assertEqual(self.service.snapshot()['scopes']['manual']['summary'], summary)
        self.assertTrue(self.service.record_result(result('b')))
        restored = self.reopen()
        self.assertEqual(restored._state, self.service._state)
        self.assertNotEqual(restored._state['battles']['a']['xp_received'], 9999)

    def test_mirror_recovers_a_damaged_early_transaction_after_backup_rotation(self):
        for index in range(8):
            self.service.record_result(result(str(index)))
        journal = self.service.store._writer_path
        with open(journal, 'r+b') as handle:
            handle.readline()
            handle.write(b'BROKEN')
        restored = self.reopen()
        self.assertEqual(restored._state, self.service._state)
        self.assertIsNotNone(restored.store.warning)
        self.assertTrue(restored.record_result(result('later')))
        self.assertEqual(self.reopen()._state, restored._state)

    def test_torn_last_transaction_in_both_copies_recovers_previous_committed_prefix(self):
        self.service.record_result(result('a'))
        previous = copy.deepcopy(self.service._state)
        offset = self.service.store._writer_offset
        self.service.record_result(result('b'))
        journal = self.service.store._writer_path
        for path in (journal, journal + '.bak'):
            with open(path, 'r+b') as handle:
                handle.truncate(offset + 8)
        restored = self.reopen()
        self.assertEqual(restored._state, previous)
        self.assertIsNotNone(restored.store.warning)
        self.assertTrue(restored.record_result(result('c')))
        self.assertEqual(set(self.reopen()._state['battles']), {'a', 'c'})

    def test_damaged_base_copy_recovers_from_mirror(self):
        self.service.record_result(result('a'))
        directory = os.path.join(self.service.store.directory, 'journal')
        base = next(name for name in os.listdir(directory) if name.endswith('.json'))
        with open(os.path.join(directory, base), 'wb') as handle:
            handle.write(b'broken')
        self.assertEqual(self.reopen()._state, self.service._state)

    def test_repeated_restart_chain_preserves_sessions_and_rejects_stale_writers(self):
        stale = self.reopen()
        for index in range(12):
            self.clock.value += 1
            self.service.record_result(result(str(index), started_at=self.clock.value))
            self.service = self.reopen('run-' + str(index))
        self.assertEqual(len(self.service._state['battles']), 12)
        self.assertFalse(stale.record_result(result('stale')))
        self.assertEqual(len(self.reopen('run-11')._state['battles']), 12)

    def test_oversized_transaction_and_snapshot_fail_closed(self):
        before = copy.deepcopy(self.service._state)
        self.assertFalse(self.service.record_result(result('big', vehicle_name='X' * storage.MAX_TRANSACTION_BYTES)))
        self.assertEqual(self.service._state, before)
        original = storage.MAX_SNAPSHOT_BYTES
        storage.MAX_SNAPSHOT_BYTES = 10
        try:
            restored = StatsService(self.directory, 'EU:7', 'run', EXPECTED, self.clock)
            self.assertTrue(restored.store.read_only)
        finally:
            storage.MAX_SNAPSHOT_BYTES = original
        self.assertEqual(self.reopen()._state, before)

    def test_reset_rejects_old_page_commands_and_retains_old_battles(self):
        self.seed(50)
        token = self.service.snapshot()['scopes']['manual']['period_id']
        self.service.set_page('manual', 'battles', 1, token)
        self.service.reset_manual()
        self.assertFalse(self.service.set_page('manual', 'battles', 1, token))
        self.assertEqual(self.service.snapshot()['scopes']['manual']['pagination']['battles']['page'], 0)
        self.assertEqual(len(self.service._state['battles']), 50)

    def test_display_strings_and_warning_lists_are_bounded_without_truncating_history(self):
        for index in range(220):
            self.service.record_result(result(str(index), vehicle_name='X' * 2000,
                                              warnings=['notice-' + str(index)]))
        snapshot = self.service.snapshot()
        self.assertEqual(len(snapshot['warnings']), 201)
        self.assertEqual(len(snapshot['scopes']['manual']['battles'][0]['name']), 256)
        self.assertEqual(len(self.service._state['battles']['0']['vehicle_name']), 2000)
        self.assertEqual(len(self.service._state['battles']), 220)

    def test_journal_name_collision_cannot_overwrite_committed_bytes(self):
        self.service.record_result(result('a'))
        journal = self.service.store._writer_path
        with open(journal, 'rb') as stream:
            before = stream.read()
        other = storage.GenerationStore(self.service.store.directory)
        other.load()
        original = storage.uuid.uuid4
        class Fixed(object):
            hex = os.path.basename(journal).split('.')[0]
        storage.uuid.uuid4 = lambda: Fixed()
        try:
            self.assertRaises(OSError, other.prepare)
        finally:
            storage.uuid.uuid4 = original
        with open(journal, 'rb') as stream:
            self.assertEqual(stream.read(), before)
        self.assertEqual(self.reopen()._state, self.service._state)

    def test_failed_mirror_flush_preserves_memory_and_accepts_a_later_retry(self):
        self.service.record_result(result('a'))
        original, calls = storage.os.fsync, []
        before = copy.deepcopy(self.service._state)
        def fsync(descriptor):
            calls.append(descriptor)
            if len(calls) == 2:
                raise OSError('second journal flush failed')
            return original(descriptor)
        storage.os.fsync = fsync
        try:
            self.assertFalse(self.service.record_result(result('failed')))
        finally:
            storage.os.fsync = original
        self.assertEqual(self.service._state, before)
        self.assertTrue(self.service.record_result(result('retry')))
        self.assertEqual(set(self.reopen()._state['battles']), {'a', 'retry'})

    def test_malformed_new_head_recovers_but_future_format_refuses_downgrade(self):
        self.service.record_result(result('a'))
        store = self.service.store
        generation = store.sequence + 1
        payload = {'schema_version': 1, 'journal': '../../escape', 'offset': 1, 'checksum': 'invalid'}
        envelope = {'storage_version': 2, 'generation': generation, 'payload': payload,
                    'payload_checksum': storage.hashlib.sha256(storage.canonical_bytes(payload)).hexdigest()}
        path = os.path.join(store.directory, 'state-%020d.json' % generation)
        with open(path, 'wb') as stream:
            stream.write(storage.canonical_bytes(envelope))
        self.assertEqual(self.reopen()._state, self.service._state)
        envelope['storage_version'] = 999
        with open(path, 'wb') as stream:
            stream.write(storage.canonical_bytes(envelope))
        restored = StatsService(self.directory, 'EU:7', 'run', EXPECTED, self.clock)
        self.assertTrue(restored.store.read_only)
        self.assertFalse(restored.begin_battle('rejected'))


import test_runtime as runtime_fixtures


class PaginationRuntimeTests(unittest.TestCase):
    setUp = runtime_fixtures.RuntimeTests.__dict__['setUp']
    tearDown = runtime_fixtures.RuntimeTests.__dict__['tearDown']
    no_footer = runtime_fixtures.RuntimeTests.__dict__['no_footer']

    def command(self, **kwargs):
        values = {'action': 'page', 'scope': 'manual', 'group': 'battles', 'page': '1',
                  'account_key': self.mod.active_key,
                  'period_id': self.mod.active_service._state['current_manual_id']}
        values.update(kwargs)
        return values

    def test_valid_page_routes_to_current_service_only(self):
        self.mod.on_action(self.command())
        self.assertEqual(self.mod.active_service._pages['manual']['battles'], 1)

    def test_invalid_page_arguments_and_stale_accounts_are_inert(self):
        for page in (None, True, [], {}, '', '-1', '1.5', '999999999', '\u00b2'):
            self.mod.on_action(self.command(page=page))
        self.mod.on_action(self.command(account_key='EU:other'))
        self.mod.on_action(self.command(account_key=None))
        self.mod.on_action(self.command(period_id='old-period'))
        self.mod.on_action(self.command(scope='instance'))
        self.assertEqual(self.mod.active_service._pages, {})

    def test_reset_invalidates_queued_page_command(self):
        command = self.command()
        self.mod.active_service.reset_manual()
        self.mod.on_action(command)
        self.assertEqual(self.mod.active_service._pages, {})

    def test_stopped_runtime_ignores_pagination(self):
        command = self.command()
        self.mod.stop()
        self.mod.on_action(command)
        self.assertEqual(self.mod.active_service._pages, {})


if __name__ == '__main__':
    unittest.main()
