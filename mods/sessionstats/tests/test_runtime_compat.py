# -*- coding: utf-8 -*-
"""Observed integration boundaries under missing or changed client APIs.

These are failure-injection tests with the same server-result fixture and real
StatsService as the runtime suite, not a claim of running a future WoT client.
"""
from __future__ import unicode_literals

import importlib
import logging
import shutil
import tempfile
import unittest

try:
    import builtins
except ImportError:
    import __builtin__ as builtins

from test_runtime import FakeAPI, FakeEvent, FakeWindow, Clock, Obj, EXPECTED
from test_normalize import raw_result, ARENA_ID
from grz_session_stats import runtime, views, visuals


class RejectEvent(FakeEvent):
    def __iadd__(self, handler):
        self.handlers.append(handler)
        raise RuntimeError('changed subscribe contract')


class RetainedEvent(FakeEvent):
    def __isub__(self, handler):
        raise RuntimeError('changed unsubscribe contract')


class RejectRetainedEvent(RejectEvent, RetainedEvent):
    pass


class BrokenWindow(FakeWindow):
    def close(self):
        raise RuntimeError('changed native window API')

    def refresh(self):
        raise RuntimeError('changed native view API')


class BrokenReusable(object):
    def __init__(self, error):
        self.error = error

    @property
    def personal(self):
        raise self.error('changed native bonus API')


def broken(*args, **kwargs):
    raise RuntimeError('injected unavailable client API')


class RuntimeCompatibilityTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.mkdtemp(prefix='grz-runtime-compat-')
        self.clock = Clock()
        self.api = FakeAPI()
        self.window = FakeWindow()
        self.mod = None
        self.log_level = logging.root.manager.disable
        logging.disable(logging.CRITICAL)

    def tearDown(self):
        if self.mod is not None:
            self.mod.stop()
        logging.disable(self.log_level)
        shutil.rmtree(self.directory)

    def start(self, native_window=False):
        self.mod = runtime.Runtime(deferred_loading=False, api=self.api, data_dir=self.directory,
                                   expected_table=EXPECTED, now=self.clock,
                                   window=None if native_window else self.window,
                                   footer_installer=lambda unused_callback: None)
        self.mod.start()
        return self.mod

    def begin(self, emit=True):
        self.clock.value = runtime.arena_start(ARENA_ID)
        self.api.battle = True
        self.api.context = {'arena_id': ARENA_ID, 'started_at': self.clock.value,
                            'vehicle_id': 1, 'map_id': '17_map', 'mode': 'random'}
        if emit:
            self.api.events.onAvatarReady()

    def summary(self, service=None):
        service = service or self.mod.active_service
        return service.snapshot()['scopes']['launch']['summary']

    def tick(self):
        self.clock.value += 5
        self.api.fire(self.mod._tick_id)

    def test_keyboard_absence_does_not_disable_result_collection(self):
        self.api.keys = None
        self.api.input = None
        self.start()
        self.begin()
        self.api.battle = False
        self.api.events.onBattleResultsReceived(True, raw_result())
        self.assertTrue(self.mod.running)
        self.assertEqual(self.summary()['battles'], 1)
        self.assertEqual(self.summary()['currencies']['bonds']['net'], 28)
        self.assertTrue(self.mod.open_window())
        self.assertTrue(any('Keyboard shortcut' in value for value in self.mod.snapshot()['warnings']))

    def test_window_constructor_failure_keeps_collection_and_can_recover(self):
        original = views.StatsWindow
        try:
            views.StatsWindow = broken
            self.start(native_window=True)
            self.begin()
            self.api.battle = False
            self.api.events.onBattleResultsReceived(True, raw_result())
            self.assertIsNone(self.mod.window)
            self.assertEqual(self.summary()['battles'], 1)
            self.assertFalse(self.mod.open_window())
            views.StatsWindow = lambda *args: self.window
            self.assertTrue(self.mod.open_window())
            self.assertEqual(self.summary()['battles'], 1)
            self.assertNotIn('window:init', self.mod.compatibility_warnings)
        finally:
            views.StatsWindow = original

    def test_broken_window_does_not_block_account_switch_or_next_client_handler(self):
        self.window = BrokenWindow()
        self.start()
        self.begin()
        self.api.battle = False
        visited = []
        self.api.events.onBattleResultsReceived += lambda *args: visited.append(True)
        self.api.events.onBattleResultsReceived(True, raw_result())
        first = self.mod.active_service
        self.assertEqual(self.summary(first)['battles'], 1)
        self.assertEqual(visited, [True])
        self.api.dbid = 8
        self.api.events.onAccountBecomePlayer()
        self.assertEqual(self.mod.active_key, 'EU:8')
        self.assertIsNot(self.mod.active_service, first)
        self.assertEqual(self.summary()['battles'], 0)

    def test_missing_raw_event_uses_posted_channel_and_reports_the_gap(self):
        self.api.events.onBattleResultsReceived = None
        self.start()
        self.begin()
        self.api.battle = False
        bundle = Obj(results=raw_result())
        self.api.results_service.onResultPosted(None, Obj(getResults=lambda: bundle))
        self.assertEqual(self.summary()['battles'], 1)
        warnings = self.mod.snapshot()['warnings']
        self.assertTrue(any('Direct result events' in value for value in warnings))
        self.assertFalse(any('Powiadomienie o przetworzonym' in value for value in warnings))

    def test_posted_event_and_bonus_bus_failure_leave_raw_results_enabled(self):
        self.api.results_service.onResultPosted = RejectEvent()
        self.api.event_bus.addListener = broken
        self.start()
        self.assertEqual(self.api.results_service.onResultPosted.handlers, [])
        self.begin()
        self.api.battle = False
        self.api.events.onBattleResultsReceived(True, raw_result())
        self.assertEqual(self.summary()['battles'], 1)
        self.assertIn('results:posted', self.mod.compatibility_warnings)
        self.assertIn('event:bonus', self.mod.compatibility_warnings)
        self.assertNotIn('results:raw', self.mod.compatibility_warnings)

    def test_broken_bonus_helper_preserves_valid_raw_results_and_currencies(self):
        self.start()
        self.begin()
        self.api.battle = False
        for offset, error in enumerate((RuntimeError, KeyError)):
            arena_id = str(int(ARENA_ID) + offset)
            self.clock.value = runtime.arena_start(arena_id) + 400
            raw = raw_result(arena_id=arena_id)
            reusable = BrokenReusable(error)
            self.api.posts[arena_id] = Obj(results=raw, reusable=reusable)
            self.api.events.onBattleResultsReceived(True, raw)
            summary = self.summary()
            self.assertEqual(summary['battles'], offset + 1)
            self.assertEqual(summary['xp_base']['sum'], 650 * (offset + 1))
            self.assertEqual(summary['xp_received']['sum'], 1950 * (offset + 1))
            self.assertEqual(summary['currencies']['credits']['net'], 32000 * (offset + 1))
            self.assertEqual(summary['currencies']['bonds']['net'], 28 * (offset + 1))
            self.assertEqual(summary['currencies']['gold']['net'], offset + 1)
            self.assertFalse(self.mod.active_service._state['battles'][arena_id]['xp_bonus_applied'])
        warnings = self.mod.snapshot()['warnings']
        self.assertTrue(any('received XP may be incomplete' in value for value in warnings))
        self.assertEqual(warnings.count(self.mod.compatibility_warnings['results:bonus']), 1)

    def test_rejected_lifecycle_subscription_does_not_interrupt_remaining_setup(self):
        rejected = RejectEvent()
        self.api.events.onAccountBecomePlayer = rejected
        self.start()
        self.assertEqual(rejected.handlers, [])
        self.assertEqual(len(self.api.events.onBattleResultsReceived.handlers), 1)
        self.assertEqual(len(self.api.input.onKeyDown.handlers), 1)
        self.assertIsNotNone(self.mod._tick_id)

    def test_failed_partial_subscription_stays_inert_when_rollback_fails(self):
        retained = RejectRetainedEvent()
        self.api.events.onBattleResultsReceived = retained
        self.start()
        self.assertEqual(len(retained.handlers), 1)
        self.begin()
        self.api.battle = False
        visited = []
        retained.handlers.append(lambda *args: visited.append(True))
        retained(True, raw_result())
        self.assertEqual(visited, [True])
        self.assertEqual(self.summary()['battles'], 0)
        self.assertIn('results:raw', self.mod.compatibility_warnings)
        bundle = Obj(results=raw_result())
        self.api.results_service.onResultPosted(None, Obj(getResults=lambda: bundle))
        self.assertEqual(self.summary()['battles'], 1)

    def test_missing_player_events_use_observed_arena_and_pending_cache(self):
        self.api.events = None
        self.start()
        self.begin(emit=False)
        self.tick()
        self.assertEqual(self.mod.active_service.pending_arena_ids(), [ARENA_ID])
        self.api.battle = False
        self.tick()
        arena_id, callback = self.api.pending_callbacks.pop()
        self.assertEqual(arena_id, ARENA_ID)
        callback(1, raw_result())
        self.assertEqual(self.summary()['battles'], 1)
        self.assertEqual(self.mod.active_service.pending_arena_ids(), [])

    def test_changed_callback_arity_is_contained_and_does_not_invent_results(self):
        self.start()
        self.begin()
        self.api.battle = False
        visited = []
        self.api.events.onBattleResultsReceived += lambda *args: visited.append(True)
        self.api.events.onBattleResultsReceived(raw_result())
        self.assertEqual(visited, [True])
        self.assertEqual(self.summary()['battles'], 0)
        self.api.events.onBattleResultsReceived(True, raw_result())
        self.assertEqual(self.summary()['battles'], 1)
        self.assertEqual(visited, [True, True])

    def test_broken_thumbnail_adapter_does_not_hide_numeric_snapshot(self):
        self.start()
        self.begin()
        self.api.battle = False
        self.api.events.onBattleResultsReceived(True, raw_result())
        original = visuals.enrich_snapshot
        try:
            visuals.enrich_snapshot = broken
            snapshot = self.mod.snapshot()
            self.assertEqual(snapshot['scopes']['launch']['summary']['battles'], 1)
            self.assertEqual(snapshot['scopes']['launch']['summary']['currencies']['bonds']['net'], 28)
            self.assertTrue(any('Thumbnails' in value for value in snapshot['warnings']))
        finally:
            visuals.enrich_snapshot = original
        self.mod.snapshot()
        self.assertNotIn('visuals', self.mod.compatibility_warnings)

    def test_broken_scheduler_does_not_disable_events_or_leak_into_bonus_bus(self):
        self.api.schedule = broken
        self.start()
        self.assertIsNone(self.mod._tick_id)
        self.begin()
        self.api.battle = False
        self.api.events.onBattleResultsReceived(True, raw_result())
        visited = []
        self.api.event_bus.addListener('fixture-tail', lambda *args: visited.append(True))
        self.api.event_bus.emit()
        self.assertEqual(visited, [True])
        self.assertEqual(self.summary()['battles'], 1)
        self.assertIn('timer:results', self.mod.compatibility_warnings)
        self.assertIn('timer:bonus', self.mod.compatibility_warnings)

    def test_broken_cache_is_visible_and_pending_membership_survives(self):
        self.start()
        self.begin()
        self.api.battle = False
        original = self.api.request_result
        self.api.request_result = broken
        self.tick()
        self.assertEqual(self.mod.inflight, {})
        self.assertEqual(self.mod.active_service.pending_arena_ids(), [ARENA_ID])
        self.assertIn('results:cache', self.mod.compatibility_warnings)
        self.api.request_result = original
        self.tick()
        unused_id, callback = self.api.pending_callbacks.pop()
        callback(1, raw_result())
        self.assertEqual(self.summary()['battles'], 1)
        self.assertNotIn('results:cache', self.mod.compatibility_warnings)

    def test_cleanup_continues_after_changed_unsubscribe_and_window_errors(self):
        retained = RetainedEvent()
        self.api.events.onBattleResultsReceived = retained
        self.window = BrokenWindow()
        self.start()
        removed = []
        self.mod.footer_handle = Obj(uninstall=lambda: removed.append(True))
        self.mod.stop()
        self.assertEqual(removed, [True])
        self.assertEqual(self.api.callbacks, {})
        self.assertEqual(self.api.input.onKeyDown.handlers, [])
        self.assertEqual(self.api.event_bus.handlers, [])
        self.assertTrue(retained.handlers)
        retained(True, raw_result())
        self.assertEqual(self.summary()['battles'], 0)

    def test_footer_cleanup_failure_stays_owned_across_stop_and_start(self):
        for throws in (False, True):
            state = {'reject': True, 'cleanup': 0, 'installed': 0}

            def cleanup():
                state['cleanup'] += 1
                if state['reject']:
                    if throws:
                        raise RuntimeError('temporary footer cleanup failure')
                    return False
                return True

            handle = Obj(uninstall=cleanup)

            def installer(callback):
                state['installed'] += 1
                return handle

            self.mod = runtime.Runtime(deferred_loading=False, api=self.api, data_dir=self.directory, now=self.clock,
                                       expected_table=EXPECTED, window=self.window,
                                       footer_installer=installer)
            self.mod.start()
            self.mod.stop()

            self.assertIs(self.mod.footer_handle, handle)
            self.mod.start()
            self.assertEqual(state['installed'], 1)
            self.assertIs(self.mod.footer_handle, handle)
            self.assertTrue(self.mod.running)
            state['reject'] = False
            self.mod.stop()
            self.assertIsNone(self.mod.footer_handle)
            self.mod.start()
            self.assertEqual(state['installed'], 2)
            self.mod.stop()

    def _check_loader_cleanup_ownership(self, fail_start):
        self.window.open()
        original_close = self.window.close
        state = {'reject': True, 'constructed': 0, 'fail_start': fail_start}

        def close():
            if state['reject']:
                raise RuntimeError('native window remains open')
            return original_close()

        self.window.close = close
        mod = runtime.Runtime(deferred_loading=False, api=self.api, data_dir=self.directory, now=self.clock,
                              expected_table=EXPECTED, window=self.window,
                              footer_installer=lambda callback: None)
        original_start = mod.start

        def start():
            original_start()
            if state['fail_start']:
                raise RuntimeError('partial initialization failure')

        mod.start = start
        previous_class, previous_instance = runtime.Runtime, runtime._runtime

        def construct():
            state['constructed'] += 1
            return mod

        runtime.Runtime, runtime._runtime = construct, None
        try:
            runtime.init()
            if not fail_start:
                runtime.fini()
            self.assertFalse(mod.running)
            self.assertIs(runtime._runtime, mod)
            self.assertTrue(self.window.is_open())
            state['fail_start'] = False
            runtime.init()
            self.assertTrue(mod.running)
            self.assertIs(runtime._runtime, mod)
            self.assertEqual(state['constructed'], 1)
            self.assertEqual(len(self.api.events.onBattleResultsReceived.handlers), 1)
            state['reject'] = False
            runtime.fini()
            self.assertIsNone(runtime._runtime)
            self.assertFalse(self.window.is_open())
        finally:
            state['reject'] = False
            mod.stop()
            runtime.Runtime, runtime._runtime = previous_class, previous_instance

    def test_loader_retains_failed_teardown_owner_for_next_initialization(self):
        self._check_loader_cleanup_ownership(False)

    def test_loader_retains_partial_initialization_owner_after_failed_cleanup(self):
        self._check_loader_cleanup_ownership(True)
    def test_failed_unsubscribe_and_cancel_leave_old_callbacks_inert_after_restart(self):
        retained = RetainedEvent()
        self.api.events.onBattleResultsReceived = retained
        self.start()
        old_tick = self.api.callbacks[self.mod._tick_id][1]
        old_event = retained.handlers[0]
        self.api.cancel = broken
        self.mod.stop()
        self.mod.start()
        self.begin()
        self.api.battle = False
        timer_id = self.mod._tick_id
        callbacks_before = len(self.api.callbacks)
        old_event(True, raw_result())
        old_tick()
        self.assertEqual(self.summary()['battles'], 0)
        self.assertEqual(self.mod._tick_id, timer_id)
        self.assertEqual(len(self.api.callbacks), callbacks_before)
        retained(True, raw_result())
        self.assertEqual(self.summary()['battles'], 1)

    def test_cache_callback_cannot_replace_its_account_using_extra_arguments(self):
        self.start()
        self.begin()
        self.api.battle = False
        self.tick()
        unused_id, callback = self.api.pending_callbacks.pop()
        original_service = self.mod.active_service
        self.api.dbid = 8
        self.api.events.onAccountBecomePlayer()
        callback(1, raw_result(), ('EU:8', ARENA_ID), self.mod.active_service)
        self.assertEqual(self.summary(original_service)['battles'], 1)
        self.assertEqual(self.summary()['battles'], 0)

    def test_old_cache_callback_cannot_clear_new_inflight_after_runtime_restart(self):
        self.start()
        self.begin()
        self.api.battle = False
        self.tick()
        unused_id, old_callback = self.api.pending_callbacks.pop()
        self.mod.stop()
        self.mod.start()
        self.tick()
        unused_id, new_callback = self.api.pending_callbacks.pop()
        key = (self.mod.active_key, ARENA_ID)
        self.assertIn(key, self.mod.inflight)
        old_callback(1, raw_result())
        self.assertEqual(self.summary()['battles'], 0)
        self.assertIn(key, self.mod.inflight)
        new_callback(1, raw_result())
        self.assertEqual(self.summary()['battles'], 1)

    def test_diagnostic_warning_is_deduplicated_for_repeated_failure(self):
        self.start()
        old_warning = runtime.LOG.warning
        logged = []
        try:
            runtime.LOG.warning = lambda *args, **kwargs: logged.append(args)
            for unused in range(5):
                self.mod._warn_once('fixture', 'The same compatibility problem.')
            self.assertEqual(len(logged), 1)
            self.assertEqual(self.mod.snapshot()['warnings'].count('The same compatibility problem.'), 1)
        finally:
            runtime.LOG.warning = old_warning

    def test_gameapi_optional_imports_are_separate_from_required_identity_and_replay(self):
        original_import = builtins.__import__
        bw = Obj()
        replay = Obj(isPlaying=lambda: False)
        constants = Obj(ARENA_BONUS_TYPE=Obj(REGULAR=1), AUTH_REALM='EU')

        def imports(name, *args, **kwargs):
            if name == 'BigWorld':
                return bw
            if name == 'BattleReplay':
                return replay
            if name == 'constants':
                return constants
            if name in ('Keys', 'PlayerEvents', 'gui', 'gui.shared', 'helpers'):
                raise ImportError('injected missing optional module')
            return original_import(name, *args, **kwargs)
        try:
            builtins.__import__ = imports
            api = runtime.GameAPI()
            self.assertIs(api.bw, bw)
            self.assertIsNone(api.keys)
            self.assertIsNone(api.input)
            self.assertIsNone(api.events)
            self.assertEqual(api.region, 'EU')
            self.assertFalse(api.is_replay())
        finally:
            builtins.__import__ = original_import

    def test_loader_contains_runtime_import_failure(self):
        loader = importlib.import_module('mod_grz_session_stats')
        original_import = builtins.__import__

        def imports(name, *args, **kwargs):
            if name == 'gui.mods.grz_session_stats':
                raise ImportError('injected client namespace unavailable')
            return original_import(name, *args, **kwargs)
        try:
            builtins.__import__ = imports
            loader.init()
            loader.fini()
        finally:
            builtins.__import__ = original_import


if __name__ == '__main__':
    unittest.main()
