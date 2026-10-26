# -*- coding: utf-8 -*-
"""Independent failure injection at shared-client and durable-commit boundaries."""
from __future__ import unicode_literals

import copy
import json
import shutil
import tempfile
import unittest

import test_runtime as fixtures
from grz_session_stats import footer, storage
from grz_session_stats.cache_observer import CacheObserver, OWN_CALLBACK
from grz_session_stats.core import StatsService, aggregate_stats, wn8_from_totals
from test_core import EXPECTED, result
from test_normalize import raw_result, START


class CacheCompatibilityTests(unittest.TestCase):
    def observe(self, cache):
        captured = []
        handle = CacheObserver(cache, lambda: 'owner', lambda *args: captured.append(args))
        self.addCleanup(handle.close)
        return handle, captured

    def test_native_keyword_arena_id_remains_accepted(self):
        class Cache(object):
            def get(self, arenaUniqueID, callback):
                return callback(1, {'arenaUniqueID': arenaUniqueID})
        handle, captured = self.observe(Cache())
        consumer = []
        self.assertEqual(handle.cache.get(arenaUniqueID=17, callback=lambda *args: consumer.append(args) or 73), 73)
        self.assertEqual(len(captured), 1)
        self.assertEqual(len(consumer), 1)

    def test_earlier_mod_extension_arguments_are_forwarded_unchanged(self):
        class Cache(object):
            def get(self, arenaUniqueID, callback, marker, **kwargs):
                self.call = (arenaUniqueID, marker, kwargs)
                return callback(1, {})
        cache = Cache()
        handle, captured = self.observe(cache)
        marker = object()
        self.assertEqual(cache.get(17, lambda *args: 73, marker, custom=marker), 73)
        self.assertEqual(cache.call, (17, marker, {'custom': marker}))
        self.assertEqual(len(captured), 1)

    def test_unrelated_instance_preserves_the_extended_contract(self):
        class Cache(object):
            def get(self, arenaUniqueID, callback=None, **kwargs):
                return arenaUniqueID, callback, kwargs
        handle, captured = self.observe(Cache())
        self.assertEqual(Cache().get(arenaUniqueID=18, flag=True), (18, None, {'flag': True}))
        self.assertEqual(captured, [])

    def test_teardown_restores_inheritance_instead_of_shadowing_other_mods(self):
        class Base(object):
            def get(self, arenaUniqueID, callback):
                return 'original'
        class Cache(Base):
            pass
        cache = Cache()
        handle, unused = self.observe(cache)
        handle.close()
        self.assertNotIn('get', Cache.__dict__)
        Base.get = lambda *args: 'replacement'
        self.assertEqual(cache.get(17, None), 'replacement')

    def test_consumer_exception_and_invalid_calls_keep_native_semantics(self):
        class Cache(object):
            def get(self, arenaUniqueID, callback):
                return callback(1, {})
        cache = Cache()
        self.observe(cache)
        def fail(*args):
            raise ValueError('consumer failure')
        with self.assertRaises(ValueError):
            cache.get(17, fail)
        with self.assertRaises(TypeError):
            cache.get(17, fail, callback=fail)

    def test_callable_proxy_rejecting_marker_lookup_still_receives_the_result(self):
        class Cache(object):
            def get(self, arenaUniqueID, callback):
                return callback(1, {})
        class Callback(object):
            def __getattr__(self, name):
                raise RuntimeError('proxy does not expose attributes')
            def __call__(self, *args):
                return 'consumer-result'
        cache = Cache()
        handle, captured = self.observe(cache)
        self.assertEqual(cache.get(17, Callback()), 'consumer-result')
        self.assertEqual(captured, [])

    def test_own_keyword_request_does_not_duplicate_observation_or_retry_errors(self):
        calls = []
        class Cache(object):
            def get(self, arenaUniqueID, callback):
                calls.append(arenaUniqueID)
                return callback(1, {})
        def callback(*args):
            raise ValueError('native consumer failure')
        setattr(callback, OWN_CALLBACK, True)
        cache = Cache()
        handle, captured = self.observe(cache)
        with self.assertRaises(ValueError):
            cache.get(arenaUniqueID=17, callback=callback)
        self.assertEqual(calls, [17])
        self.assertEqual(captured, [])


class FooterRegistrationTests(unittest.TestCase):
    def installation(self):
        class Child(object):
            uniqueID = 42
        class Footer(object):
            def __init__(self):
                self.child = None
                self.on_register = lambda: None
                self.fail_remove = False
            def _onLoading(self, *args, **kwargs):
                return 'native-result'
            def getChildView(self, position):
                return self.child
            def _registerChild(self, position, child):
                self.on_register()
                self.child = child
            def _unregisterChild(self, identifier, destroy):
                if self.fail_remove:
                    raise RuntimeError('temporary removal failure')
                self.child = None
        handle = footer.FooterInstallation(Footer, Child, lambda: None)
        self.addCleanup(handle.uninstall)
        return handle, Footer()

    def test_uninstall_during_registration_removes_the_late_child(self):
        handle, view = self.installation()
        view.on_register = handle.uninstall
        self.assertEqual(view._onLoading(), 'native-result')
        self.assertIsNone(view.child)
        self.assertEqual(handle._children, [])

    def test_late_child_cleanup_failure_remains_owned_until_retry(self):
        handle, view = self.installation()
        view.fail_remove = True
        view.on_register = handle.uninstall
        self.assertEqual(view._onLoading(), 'native-result')
        self.assertIsNotNone(view.child)
        self.assertEqual(len(handle._children), 1)
        self.assertFalse(handle.open())
        view.fail_remove = False
        self.assertTrue(handle.uninstall())
        self.assertIsNone(view.child)

    def test_attachment_exception_cannot_break_native_loading_or_later_mod(self):
        handle, view = self.installation()
        def fail(unused):
            raise TypeError('optional child adapter failed')
        handle._attach = fail
        self.assertEqual(view._onLoading(), 'native-result')

    def test_uninstall_during_construction_does_not_register_a_child(self):
        handle, view = self.installation()
        original = handle.child_class
        def construct():
            handle.uninstall()
            return original()
        handle.child_class = construct
        view._onLoading()
        self.assertIsNone(view.child)


class CommitBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.mkdtemp(prefix='grz-commit-boundary-')
        self.addCleanup(shutil.rmtree, self.directory)

    def test_post_commit_directory_failure_cannot_discard_the_saved_battle(self):
        service = StatsService(self.directory, 'EU:7', 'launch', {}, now=lambda: 100)
        original = service.store._files
        calls = []
        def files():
            calls.append(True)
            if len(calls) > 1:
                raise OSError('directory enumeration failed after commit')
            return original()
        service.store._files = files
        self.assertTrue(service.begin_battle('1'))
        service.store._files = original
        self.assertTrue(service.begin_battle('2'))
        restored = StatsService(self.directory, 'EU:7', 'launch', {}, now=lambda: 101)
        self.assertEqual(set(restored._state['battles']), {'1', '2'})

    def test_post_commit_unlock_failure_publishes_the_committed_state(self):
        service = StatsService(self.directory, 'EU:7', 'launch', {}, now=lambda: 100)
        original = storage._WriteLock.__exit__
        def exit_then_fail(lock, *args):
            original(lock, *args)
            raise OSError('unlock notification failed after commit')
        storage._WriteLock.__exit__ = exit_then_fail
        try:
            self.assertTrue(service.begin_battle('1'))
        finally:
            storage._WriteLock.__exit__ = original
        self.assertTrue(service.begin_battle('2'))
        restored = StatsService(self.directory, 'EU:7', 'launch', {}, now=lambda: 101)
        self.assertEqual(set(restored._state['battles']), {'1', '2'})

    def test_failure_before_commit_keeps_memory_and_disk_unchanged(self):
        service = StatsService(self.directory, 'EU:7', 'launch', {}, now=lambda: 100)
        before = copy.deepcopy(service._state)
        original = storage.os.rename
        def fail(*args):
            raise OSError('rename failed')
        storage.os.rename = fail
        try:
            self.assertFalse(service.begin_battle('1'))
        finally:
            storage.os.rename = original
        self.assertEqual(service._state, before)
        self.assertEqual(storage.GenerationStore(service.store.directory).load(), before)


class NumericBoundaryTests(unittest.TestCase):
    def test_valid_json_wn8_override_cannot_make_the_panel_payload_infinite(self):
        table = copy.deepcopy(EXPECTED)
        table['data'][0]['expDamage'] = 1e-308
        self.assertTrue(fixtures.runtime._looks_like_expected(table))
        stats = aggregate_stats([result()], table)
        json.dumps(stats, allow_nan=False)
        self.assertIsNone(stats['wn8'])
        self.assertEqual(stats['wn8_count'], 0)
        self.assertEqual(stats['xp_received']['sum'], 1500)

    def test_finite_ratios_with_overflowing_formula_do_not_escape_as_infinity(self):
        actual = {'damage': 1e150, 'frags': 1e150, 'spots': 1e150,
                  'defense': 1e150, 'wins': 1}
        expected = dict((key, 1e-5) for key in actual)
        self.assertIsNone(wn8_from_totals(actual, expected))

    def test_finite_records_with_overflowing_sums_still_have_a_renderable_snapshot(self):
        row = result(xp_base=1e308, xp_received=1e308, free_xp=1e308)
        row['currencies']['credits'] = {'income': 1e308, 'costs': 0, 'net': 1e308,
                                        'breakdown': {'repair': 1e308}}
        stats = aggregate_stats([row, copy.deepcopy(row)], EXPECTED)
        json.dumps(stats, allow_nan=False)
        self.assertIsNone(stats['xp_received']['sum'])
        self.assertEqual(stats['xp_received']['max'], 1e308)
        self.assertIsNone(stats['currencies']['credits']['net'])
        self.assertIsNone(stats['currencies']['credits']['breakdown']['repair'])
        self.assertEqual(stats['battles'], 2)


class NativeDispatchMatrixTests(unittest.TestCase):
    setUp = fixtures.RuntimeTests.__dict__['setUp']
    tearDown = fixtures.RuntimeTests.__dict__['tearDown']
    no_footer = fixtures.RuntimeTests.__dict__['no_footer']

    def test_malformed_result_matrix_keeps_later_native_listeners_and_valid_recovery(self):
        delivered = []
        event = self.api.events.onBattleResultsReceived
        event += lambda own, raw: delivered.append(raw)
        self.clock.value = START + 600
        paths = [(), ('common',), ('personal',), ('personal', 'avatar'), ('personal', 1),
                 ('personal', 1, 'xp'), ('personal', 1, 'credits'),
                 ('common', 'duration'), ('common', 'winnerTeam')]
        values = [None, True, 0, -1, 1.5, 'changed', [], {}, float('inf')]
        for path in paths:
            for value in values:
                raw = raw_result()
                if path:
                    target = raw
                    for key in path[:-1]:
                        target = target[key]
                    target[path[-1]] = value
                else:
                    raw = value
                before = copy.deepcopy(raw)
                count = len(delivered)
                event(True, raw)
                self.assertEqual(len(delivered), count + 1, (path, value))
                self.assertIs(delivered[-1], raw)
                self.assertEqual(raw, before)
                self.assertEqual(self.mod._processing, {})
        event(True, raw_result())
        summary = self.mod.active_service.snapshot()['scopes']['manual']['summary']
        self.assertEqual(summary['battles'], 1)
        self.assertEqual(summary['xp_received']['sum'], 1950)


if __name__ == '__main__':
    unittest.main()
