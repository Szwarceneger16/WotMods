# -*- coding: utf-8 -*-
"""Update-boundary regressions with strict native doubles; no live-client claim."""
from __future__ import unicode_literals

import json
import sys
import unittest

import test_runtime as runtime_fixtures
import test_visuals as visual_fixtures
from grz_session_stats import footer, visuals


class RetainedEvent(runtime_fixtures.FakeEvent):
    def __isub__(self, callback):
        raise TypeError('changed unsubscribe contract')


class PartialSubscriptionEvent(RetainedEvent):
    def __iadd__(self, callback):
        self.handlers.append(callback)
        raise TypeError('changed subscribe contract after registration')


class WindowCompatibilityTests(unittest.TestCase):
    # Reuse the verified Wulf setup without inheriting and rerunning its tests.
    setUp = runtime_fixtures.NativeBindingTests.__dict__['setUp']
    tearDown = runtime_fixtures.NativeBindingTests.__dict__['tearDown']
    inject_module = runtime_fixtures.NativeBindingTests.__dict__['inject_module']

    def test_changed_notification_signature_cannot_interrupt_native_listeners(self):
        self.assertTrue(self.window.open())
        native = self.window._window
        later = []
        native.onSizeChanged += lambda *args: later.append(args)
        previous = self.window._native_size
        native.onSizeChanged(native.uniqueID, {'width': 700, 'height': 620})
        self.assertEqual(len(later), 1)
        self.assertEqual(self.window._native_size, previous)
        self.assertTrue(self.window.is_open())
        native.resize_surface(701, 621)
        self.assertEqual(self.window._native_size, (701, 621))
        self.assertEqual(len(later), 2)

    def test_changed_subscription_is_optional_and_partial_listener_is_inert(self):
        changed = PartialSubscriptionEvent()
        self.main.onSizeChanged = changed
        self.assertTrue(self.window.open())
        self.assertEqual(len(changed.handlers), 1)
        self.stats['probe'] = 'must not be published by failed listener'
        changed()
        payload = json.loads(self.window._model._payload)
        self.assertNotIn('probe', payload)
        self.window.refresh()
        self.assertIn('probe', json.loads(self.window._model._payload))

    def test_failed_unsubscribe_does_not_let_old_window_refresh_new_one(self):
        retained = RetainedEvent()
        self.main.onSizeChanged = retained
        self.assertTrue(self.window.open())
        stale = retained.handlers[0]
        self.window.close()
        self.assertTrue(self.window.open())
        self.stats['probe'] = 'belongs to next explicit refresh'
        stale()
        self.assertNotIn('probe', json.loads(self.window._model._payload))
        retained()
        self.assertIn('probe', json.loads(self.window._model._payload))

    def test_changed_timer_cancellation_cannot_prevent_native_destruction(self):
        self.assertTrue(self.window.open())
        native = self.window._window

        def changed_cancel(callback_id):
            raise TypeError('changed callback cancellation contract')

        sys.modules['BigWorld'].cancelCallback = changed_cancel
        self.window.close()
        self.assertIsNone(native.proxy)
        self.assertFalse(self.window.is_open())
        self.assertEqual(self.window._events, [])

    def test_subscription_returning_after_close_is_removed_and_cannot_resume_loading(self):
        window = self.window
        observed = []

        class LateEvent(runtime_fixtures.FakeEvent):
            def __iadd__(self, callback):
                observed.append(window._window)
                window.close()
                self.handlers.append(callback)
                return self

        event = LateEvent()
        self.main.onSizeChanged = event
        self.assertFalse(self.window.open())
        self.assertIsNone(observed[0].proxy)
        self.assertFalse(observed[0].shown)
        self.assertEqual(observed[0].windowStatus, self.status.DESTROYED)
        self.assertEqual(event.handlers, [])
        self.assertEqual(self.window._events, [])
        self.assertEqual(self.timer.callbacks, {})

    def test_watchdog_returning_after_close_is_cancelled_without_showing_the_old_window(self):
        original = self.timer.schedule
        observed = []

        def late(seconds, callback):
            observed.append(self.window._window)
            self.window.close()
            return original(seconds, callback)

        sys.modules['BigWorld'].callback = late
        self.assertFalse(self.window.open())
        self.assertIsNone(observed[0].proxy)
        self.assertFalse(observed[0].shown)
        self.assertIsNone(self.window._watchdog_id)
        self.assertEqual(self.timer.callbacks, {})

    def test_late_old_watchdog_cannot_overwrite_a_replacement_windows_timer(self):
        original = self.timer.schedule
        observed = []

        def late(seconds, callback):
            if not observed:
                observed.append(self.window._window)
                self.window.close()
                self.assertTrue(self.window.open())
            return original(seconds, callback)

        sys.modules['BigWorld'].callback = late
        self.assertTrue(self.window.open())
        self.assertIsNot(self.window._window, observed[0])
        self.assertIsNone(observed[0].proxy)
        self.assertFalse(observed[0].shown)
        self.assertEqual(len(self.timer.callbacks), 1)
        self.assertIn(self.window._watchdog_id, self.timer.callbacks)
        self.assertTrue(self.window._window.shown)

    def test_failed_destroy_keeps_ownership_blocks_duplicate_open_and_allows_close_retry(self):
        retained = RetainedEvent()
        self.main.onSizeChanged = retained
        self.assertTrue(self.window.open())
        native, model = self.window._window, self.window._model
        stale_event = retained.handlers[0]
        stale_timer = self.timer.callbacks[self.window._watchdog_id][1]
        original_destroy = native.destroy
        attempts = []

        def fail():
            attempts.append(True)
            raise RuntimeError('native surface was not released')

        native.destroy = fail
        self.addCleanup(setattr, native, 'destroy', original_destroy)
        self.window.close()
        self.assertIs(self.window._window, native)
        self.assertTrue(self.window.is_open())
        self.assertIsNotNone(native.proxy)
        self.assertIsNone(self.window._model)
        self.assertEqual(self.timer.callbacks, {})
        self.assertEqual(self.window._events, [])
        self.assertFalse(self.window.open())
        self.assertIs(self.window._window, native)
        self.assertEqual(len(attempts), 2)
        self.assertEqual(len(retained.handlers), 1)
        native.shown = False
        native._onReady()
        stale_event()
        stale_timer()
        model.onAction({'action': 'reset'})
        self.window.refresh()
        self.window.resize(900, 800)
        self.assertFalse(native.shown)
        self.assertEqual(self.actions, [])
        self.assertEqual(self.timer.callbacks, {})
        self.assertIsNone(self.window._reported_size)
        native.destroy = original_destroy
        self.window.close()
        self.assertIsNone(native.proxy)
        self.assertIsNone(self.window._window)
        self.assertFalse(self.window.is_open())
        self.assertTrue(self.window.open())
        current = self.window._window
        model.onAction({'action': 'close'})
        stale_event()
        stale_timer()
        self.assertIs(self.window._window, current)

    def test_open_retries_failed_cleanup_before_creating_a_replacement(self):
        self.assertTrue(self.window.open())
        native = self.window._window
        original_destroy = native.destroy

        def fail():
            raise RuntimeError('temporary destroy failure')

        native.destroy = fail
        self.addCleanup(setattr, native, 'destroy', original_destroy)
        self.window.close()
        native.destroy = original_destroy
        self.assertTrue(self.window.open())
        self.assertIsNone(native.proxy)
        self.assertIsNot(self.window._window, native)
        self.assertEqual(len(self.main.onSizeChanged.handlers), 1)

    def test_destroy_throwing_after_release_does_not_keep_a_dead_handle(self):
        self.assertTrue(self.window.open())
        native = self.window._window
        original_destroy = native.destroy

        def release_then_fail():
            original_destroy()
            raise RuntimeError('destroy failed after releasing its surface')

        native.destroy = release_then_fail
        self.window.close()
        self.assertIsNone(native.proxy)
        self.assertIsNone(self.window._window)
        self.assertFalse(self.window.is_open())
        self.assertTrue(self.window.open())

    def test_asynchronous_destroy_keeps_the_handle_until_native_release(self):
        self.assertTrue(self.window.open())
        native = self.window._window
        original_destroy = native.destroy

        def begin_destroy():
            native.windowStatus = self.status.DESTROYING

        native.destroy = begin_destroy
        self.addCleanup(setattr, native, 'destroy', original_destroy)
        self.window.close()
        self.assertTrue(self.window.is_open())
        self.assertIs(self.window._window, native)
        self.assertFalse(self.window.open())
        self.assertIs(self.window._window, native)
        original_destroy()
        self.assertFalse(self.window.is_open())
        self.assertTrue(self.window.open())
        self.assertIsNot(self.window._window, native)

    def test_native_destroying_status_invalidates_actions_but_retains_the_surface(self):
        self.assertTrue(self.window.open())
        native, model = self.window._window, self.window._model
        native.windowStatus = self.status.DESTROYING
        native.onStatusChanged(self.status.DESTROYING)
        self.assertIs(self.window._window, native)
        self.assertTrue(self.window.is_open())
        self.assertEqual(self.window._events, [])
        self.assertEqual(self.timer.callbacks, {})
        model.onAction({'action': 'reset'})
        native.shown = False
        native._onReady()
        self.assertFalse(native.shown)
        self.assertEqual(self.actions, [])
        self.window.close()
        self.assertIsNone(native.proxy)
        self.assertFalse(self.window.is_open())

    def test_destroy_cannot_reenter_close_or_create_another_window(self):
        self.assertTrue(self.window.open())
        native = self.window._window
        original_destroy = native.destroy
        attempts = []

        def reenter():
            attempts.append(True)
            self.window.close()
            self.assertFalse(self.window.open())
            original_destroy()

        native.destroy = reenter
        self.window.close()
        self.assertEqual(attempts, [True])
        self.assertIsNone(self.window._window)
        self.assertIsNone(native.proxy)

    def test_failed_load_and_destroy_retains_the_partial_window_for_retry(self):
        base = sys.modules['gui.impl.pub'].WindowImpl
        original_load, original_destroy = base.load, base.destroy

        def fail(*args):
            raise RuntimeError('temporary native failure')

        base.load = base.destroy = fail
        try:
            self.assertFalse(self.window.open())
            native = self.window._window
            self.assertIsNotNone(native)
            self.assertIsNotNone(native.proxy)
            self.assertTrue(self.window.is_open())
            self.assertFalse(self.window.open())
            self.assertIs(self.window._window, native)
        finally:
            base.load, base.destroy = original_load, original_destroy
        self.assertTrue(self.window.open())
        self.assertIsNone(native.proxy)
        self.assertIsNot(self.window._window, native)

    def test_footer_wrapper_preserves_original_arguments_and_return_value(self):
        marker = object()
        received = []

        class LobbyFooter(self.component):
            def _onLoading(self, *args, **kwargs):
                received.append((args, kwargs))
                return marker

        handle = footer.FooterInstallation(LobbyFooter, self.component, lambda: None)
        self.addCleanup(handle.uninstall)
        lobby = LobbyFooter()
        self.assertIs(lobby._onLoading('native', ready=True), marker)
        self.assertEqual(received, [(('native',), {'ready': True})])
        self.assertIsNotNone(lobby.getChildView(footer.POSITION_ID))

    def test_footer_does_not_mask_errors_in_original_game_callback(self):
        class LobbyFooter(self.component):
            def _onLoading(self, *args, **kwargs):
                raise ValueError('native callback error')

        handle = footer.FooterInstallation(LobbyFooter, self.component, lambda: None)
        self.addCleanup(handle.uninstall)
        lobby = LobbyFooter()
        with self.assertRaises(ValueError):
            lobby._onLoading()
        self.assertEqual(lobby.children, {})

    def test_missing_optional_footer_contract_leaves_native_class_untouched(self):
        class LobbyFooter(self.component):
            _registerChild = None

        original = LobbyFooter._onLoading
        with self.assertRaises(TypeError):
            footer.FooterInstallation(LobbyFooter, self.component, lambda: None)
        current = LobbyFooter._onLoading
        self.assertIs(getattr(current, '__func__', current), getattr(original, '__func__', original))
        self.assertNotIn('_onLoading', LobbyFooter.__dict__)

    def test_vehicle_helper_loss_preserves_maps_and_can_recover_later(self):
        fixture = visual_fixtures.ResolverFixture()
        vehicle_module = self.inject_module('items.vehicles')
        icon_module = self.inject_module('gui.shared.gui_items.Vehicle')
        resolver = visuals.NativeVisualResolver(
            resources=fixture.resources,
            image_getter=lambda identifier: fixture.paths[identifier],
            absolute_url_getter=lambda path: path.replace('../', 'img://gui/'),
            file_exists=fixture.exists)
        self.assertEqual(resolver.map_src('01_karelia'), 'img://' + visual_fixtures.MAP_PATH)
        self.assertIsNone(resolver.vehicle_src(visual_fixtures.VEHICLE_ID))
        vehicle_module.getVehicleType = fixture.vehicle_type
        self.assertIsNone(resolver.vehicle_src(visual_fixtures.VEHICLE_ID))
        self.assertEqual(resolver.map_src('01_karelia'), 'img://' + visual_fixtures.MAP_PATH)
        icon_module.getIconResourceName = lambda name: name.replace(':', '_').replace('-', '_')
        self.assertEqual(resolver.vehicle_src(visual_fixtures.VEHICLE_ID),
                         'img://' + visual_fixtures.VEHICLE_PATH)


if __name__ == '__main__':
    unittest.main()
