# -*- coding: utf-8 -*-
"""Synthetic Windows CRT translation and checksum-verified legacy recovery."""
from __future__ import unicode_literals

from contextlib import contextmanager
import copy
import os
import shutil
import tempfile
import unittest

from test_core import Clock, EXPECTED, result
from grz_session_stats.core import StatsService
from grz_session_stats import storage


@contextmanager
def windows_crt(force_legacy=False):
    """Model descriptor translation, independent of the host's fdopen semantics.

    Native descriptors stay binary; only descriptors opened without O_BINARY
    expand LF. force_legacy reproduces the old writer even after the fix.
    """
    native_binary = getattr(os, 'O_BINARY', None)
    binary = native_binary if native_binary is not None else 0x40000000
    original_open, original_fdopen = os.open, os.fdopen
    modes = {}

    class Stream(object):
        def __init__(self, handle, translate):
            self.handle, self.translate = handle, translate

        def write(self, data):
            self.handle.write(data.replace(b'\n', b'\r\n') if self.translate else data)

        def __getattr__(self, key):
            return getattr(self.handle, key)

        def __enter__(self):
            return self

        def __exit__(self, *unused):
            self.handle.close()

    def create(path, flags, mode=0o777):
        descriptor = original_open(path, (flags & ~binary) | (native_binary or 0), mode)
        modes[descriptor] = force_legacy or not flags & binary
        return descriptor

    def wrap(descriptor, mode):
        return Stream(original_fdopen(descriptor, mode), modes.pop(descriptor))

    os.O_BINARY, os.open, os.fdopen = binary, create, wrap
    try:
        yield
    finally:
        os.open, os.fdopen = original_open, original_fdopen
        if native_binary is None:
            del os.O_BINARY
        else:
            os.O_BINARY = native_binary


class WindowsJournalTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.mkdtemp(prefix='grz-windows-journal-')
        self.clock = Clock(100)

    def tearDown(self):
        shutil.rmtree(self.directory)

    def service(self, launch='launch', deferred=False):
        return StatsService(self.directory, 'EU:7', launch, EXPECTED, self.clock, deferred=deferred)

    @staticmethod
    def read(path):
        with open(path, 'rb') as handle:
            return handle.read()

    def contents(self):
        return dict((os.path.join(root, name), self.read(os.path.join(root, name)))
                    for root, unused, files in os.walk(self.directory) for name in files)

    def legacy(self, count=5):
        with windows_crt(force_legacy=True):
            service = self.service()
            for index in range(count):
                self.clock.value += 10
                self.assertTrue(service.record_result(result(str(index), started_at=self.clock.value)))
        journal = service.store._writer_path
        raw = self.read(journal)
        self.assertIn(b'}\r{', raw)
        self.assertNotIn(b'\r\n', raw)
        return service, journal

    def test_crt_fixture_expands_lf_despite_fdopen_binary_mode_without_descriptor_flag(self):
        path = os.path.join(self.directory, 'translation-control')
        with windows_crt():
            descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(descriptor, 'wb') as handle:
                handle.write(b'header\n')
        self.assertEqual(self.read(path), b'header\r\n')

    def test_binary_descriptor_preserves_offsets_and_hashes_under_windows_text_defaults(self):
        with windows_crt():
            service = self.service()
            for index in range(5):
                self.clock.value += 10
                self.assertTrue(service.record_result(result(str(index), started_at=self.clock.value)))
            raw = self.read(service.store._writer_path)
            self.assertNotIn(b'\r', raw)
            self.assertEqual(raw.count(b'\n'), 6)
            restored = self.service()
        self.assertTrue(restored.ready, restored.last_error)
        self.assertEqual(restored._state, service._state)

    def test_legacy_latest_generation_loads_without_rewriting_any_original_bytes(self):
        service, unused = self.legacy()
        before = self.contents()
        restored = storage.GenerationStore(service.store.directory)
        self.assertEqual(restored.load(), service._state)
        self.assertEqual(restored.sequence, service.store.sequence)
        self.assertFalse(restored.read_only)
        self.assertEqual(self.contents(), before)

    def test_deferred_recovery_drains_pending_results_once_and_restarts_mixed_journals(self):
        original, journal = self.legacy()
        original_journal = self.read(journal)
        self.clock.value += 10
        restored = self.service('new-launch', deferred=True)
        self.assertTrue(restored.begin_battle('pending', started_at=self.clock.value))
        self.assertTrue(restored.record_result(result('pending', started_at=self.clock.value)))
        for unused in range(10000):
            if not restored.loading:
                break
            restored.advance_loading(max_steps=8)
        self.assertTrue(restored.ready, restored.last_error)
        self.assertEqual(len(restored._state['battles']), 6)
        for key, record in original._state['battles'].items():
            self.assertEqual(restored._state['battles'][key], record)
        before = copy.deepcopy(restored._state)
        again = self.service('new-launch')
        self.assertTrue(again.ready, again.last_error)
        # Restart may add a new startup receipt, never another copy of a result.
        for field in ('battles', 'launch_sessions', 'manual_sessions', 'current_manual_id'):
            self.assertEqual(again._state[field], before[field])
        self.assertEqual(storage.GenerationStore(again.store.directory).load(), again._state)
        self.assertEqual(self.read(journal), original_journal)
        self.assertEqual(again.snapshot()['scopes']['manual']['summary']['battles'], 6)

    def test_damaged_primary_legacy_segment_uses_its_verified_mirror(self):
        service, journal = self.legacy()
        with open(journal, 'wb') as handle:
            handle.write(b'broken')
        restored = storage.GenerationStore(service.store.directory)
        self.assertEqual(restored.load(), service._state)
        self.assertIsNotNone(restored.warning)

    def test_torn_legacy_tail_recovers_previous_commit_and_accepts_a_new_result(self):
        service, journal = self.legacy()
        generations = service.store._files()
        generation, path = generations[1]
        previous = storage.GenerationStore(service.store.directory)._decode(path, generation)
        for path in (journal, journal + '.bak'):
            with open(path, 'r+b') as handle:
                handle.truncate(len(self.read(path)) - 8)
        restored = self.service()
        self.assertTrue(restored.ready, restored.last_error)
        self.assertEqual(restored._state, previous)
        self.clock.value += 10
        self.assertTrue(restored.record_result(result('new', started_at=self.clock.value)))
        self.assertEqual(self.service()._state, restored._state)

    def test_legacy_header_correction_cannot_hide_transaction_tampering(self):
        service, journal = self.legacy()
        for path in (journal, journal + '.bak'):
            raw = self.read(path)
            changed = raw.replace(b'"xp_base":500', b'"xp_base":501', 1)
            self.assertNotEqual(raw, changed)
            with open(path, 'wb') as handle:
                handle.write(changed)
        before = self.contents()
        restored = storage.GenerationStore(service.store.directory)
        self.assertRaises(storage.StorageError, restored.load)
        self.assertTrue(restored.read_only)
        self.assertEqual(self.contents(), before)

    def test_recovery_does_not_normalize_transaction_line_endings(self):
        service, journal = self.legacy()
        for path in (journal, journal + '.bak'):
            raw = self.read(path).replace(b'\n', b'\r', 1)
            with open(path, 'wb') as handle:
                handle.write(raw)
        restored = storage.GenerationStore(service.store.directory)
        self.assertRaises(storage.StorageError, restored.load)
        self.assertTrue(restored.read_only)

    def test_uncommitted_tail_is_ignored_without_changing_the_legacy_segment(self):
        service, journal = self.legacy()
        for path in (journal, journal + '.bak'):
            with open(path, 'ab') as handle:
                handle.write(b'{uncommitted tail')
        before = self.contents()
        self.assertEqual(storage.GenerationStore(service.store.directory).load(), service._state)
        self.assertEqual(self.contents(), before)

    def test_legacy_first_transaction_near_size_limit_keeps_bounded_header_read(self):
        writer = storage.GenerationStore(self.directory)
        writer.save({'schema_version': 1, 'battles': {}})
        patch = storage.StateDelta({'padding': ''}, {})
        length = storage.MAX_TRANSACTION_BYTES - len(storage.canonical_bytes(patch)) - 1
        patch['fields']['padding'] = 'a' * length
        with windows_crt(force_legacy=True):
            writer.save(patch)
        restored = storage.GenerationStore(self.directory)
        self.assertEqual(restored.load()['padding'], 'a' * length)


if __name__ == '__main__':
    unittest.main()
