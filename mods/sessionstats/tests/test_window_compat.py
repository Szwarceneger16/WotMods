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

    def test_resize_tracks_global_cursor_until_release_and_anchors_corners_and_edges(self):
        self.assertTrue(self.window.open())
        native = self.window._window
        cursor = runtime_fixtures.Obj(position=(0, 0), inFocus=True)
        held = [True]
        self.inject_module('GUI', mcursor=lambda: cursor)
        self.inject_module('Keys', KEY_LEFTMOUSE=1)
        sys.modules['BigWorld'].isKeyDown = lambda key: held[0]
        clock = [0.0]
        self.window._resize_clock = lambda: clock[0]
        for corner in ('se', 'ne', 'sw', 'nw', 'n', 'e', 's', 'w'):
            cursor.position = (0, 0)
            held[0] = True
            self.window.resize(700, 620)
            native.resize_surface(700, 620)
            native.drag_surface(370, 140)
            self.window._handle_action(self.window._generation,
                                      {'action': 'resize_begin', 'corner': corner, 'token': '1'})
            self.assertIsNotNone(self.window._resize_gesture)
            # No document mousemove is dispatched, including at release.
            cursor.position = (-0.2 if 'w' in corner else 0.2, 0.1 if 'n' in corner else -0.1)
            clock[0] += 0.11
            self.timer.fire(self.window._resize_callback_id)
            payload = json.loads(self.window._model._payload)['resize_gesture']
            self.assertAlmostEqual(payload['width'], 892 if ('w' in corner or 'e' in corner) else 700)
            self.assertAlmostEqual(payload['height'], 674 if ('n' in corner or 's' in corner) else 620)
            self.window.resize(payload['width'], payload['height'])
            native.resize_surface(payload['width'], payload['height'])
            self.assertEqual(native.position, (178 if 'w' in corner else 370,
                                               86 if 'n' in corner else 140))
            held[0] = False
            self.timer.fire(self.window._resize_callback_id)
            self.assertIsNone(self.window._resize_gesture)
            self.assertIsNone(self.window._resize_callback_id)
            self.assertIsNone(self.window._resize_anchor)
            self.assertFalse(json.loads(self.window._model._payload)['resize_gesture']['active'])

    def test_resize_at_200_percent_keeps_the_opposite_corner_and_waits_for_final_surface(self):
        self.main.size = (3840, 2160)
        self.loader.scale = 2.0
        self.assertTrue(self.window.open())
        native = self.window._window
        cursor = runtime_fixtures.Obj(position=(0, 0), inFocus=True)
        held = [True]
        self.inject_module('GUI', mcursor=lambda: cursor)
        self.inject_module('Keys', KEY_LEFTMOUSE=1)
        sys.modules['BigWorld'].isKeyDown = lambda key: held[0]
        for corner in ('se', 'ne', 'sw', 'nw', 'n', 'e', 's', 'w'):
            cursor.position = (0, 0)
            held[0] = True
            native.resize_surface(1400, 1240)
            self.window.resize(1400, 1240)
            native.drag_surface(1000, 460)
            self.window._begin_resize(corner, '2')
            # Jump away from the grip, then release without a document event.
            cursor.position = (-0.2 if 'w' in corner else 0.2, 0.1 if 'n' in corner else -0.1)
            held[0] = False
            self.timer.fire(self.window._resize_callback_id)
            payload = json.loads(self.window._model._payload)['resize_gesture']
            width = 892 if ('w' in corner or 'e' in corner) else 700
            height = 674 if ('n' in corner or 's' in corner) else 620
            self.assertEqual((payload['width'], payload['height']), (width, height))
            self.assertFalse(payload['active'])
            self.assertIsNone(self.window._resize_gesture)
            self.assertIsNotNone(self.window._resize_anchor)
            native.resize_surface(width * 2, height * 2)
            self.assertEqual(native.position, (616 if 'w' in corner else 1000,
                                               352 if 'n' in corner else 460))
            self.assertIsNone(self.window._resize_anchor)

    def test_resize_samples_at_60_hz_but_limits_published_sizes_and_flushes_release(self):
        self.assertTrue(self.window.open())
        cursor = runtime_fixtures.Obj(position=(0, 0), inFocus=True)
        self.inject_module('GUI', mcursor=lambda: cursor)
        self.inject_module('Keys', KEY_LEFTMOUSE=1)
        held = [True]
        clock = [0.0]
        sys.modules['BigWorld'].isKeyDown = lambda key: held[0]
        self.window._resize_clock = lambda: clock[0]
        self.window._begin_resize('se', '1')
        first_payload = self.window._model._payload
        for tick in range(1, 6):
            callback_id = self.window._resize_callback_id
            self.assertAlmostEqual(self.timer.callbacks[callback_id][0], 1.0 / 60)
            clock[0] = tick / 60.0
            cursor.position = (tick * 0.04, -tick * 0.02)
            self.timer.fire(callback_id)
            self.assertEqual(self.window._model._payload, first_payload)
        clock[0] = 0.101
        cursor.position = (0.25, -0.15)
        self.timer.fire(self.window._resize_callback_id)
        payload = json.loads(self.window._model._payload)['resize_gesture']
        self.assertEqual((payload['width'], payload['height']), (940, 701))
        # Release inside the next throttle window must still use this position.
        clock[0] = 0.12
        cursor.position = (0.3, -0.2)
        held[0] = False
        self.timer.fire(self.window._resize_callback_id)
        payload = json.loads(self.window._model._payload)['resize_gesture']
        self.assertEqual((payload['width'], payload['height']), (988, 728))
        self.assertFalse(payload['active'])
        self.assertIsNone(self.window._resize_callback_id)

    def test_same_size_release_does_not_leave_an_anchor_for_a_later_resize(self):
        self.assertTrue(self.window.open())
        self.inject_module('GUI', mcursor=lambda: runtime_fixtures.Obj(position=(0, 0), inFocus=True))
        self.inject_module('Keys', KEY_LEFTMOUSE=1)
        held = [True]
        sys.modules['BigWorld'].isKeyDown = lambda key: held[0]
        self.window._begin_resize('nw', '1')
        held[0] = False
        self.timer.fire(self.window._resize_callback_id)
        self.assertIsNone(self.window._resize_anchor)
        before = self.window._window.position
        self.window.resize(600, 500)
        self.assertEqual(self.window._window.position, before)

    def test_old_resize_callback_cannot_poll_or_replace_a_new_gesture(self):
        self.assertTrue(self.window.open())
        self.inject_module('GUI', mcursor=lambda: runtime_fixtures.Obj(position=(0, 0), inFocus=True))
        self.inject_module('Keys', KEY_LEFTMOUSE=1)
        sys.modules['BigWorld'].isKeyDown = lambda key: True
        self.window._begin_resize('se', '1')
        stale = self.timer.callbacks[self.window._resize_callback_id][1]
        self.window._handle_action(self.window._generation, {'action': 'resize_end', 'token': '1'})
        self.window._begin_resize('nw', '2')
        before = self.window._model._payload
        callback_id = self.window._resize_callback_id
        stale()
        self.assertEqual(self.window._model._payload, before)
        self.assertEqual(self.window._resize_callback_id, callback_id)

    def test_resize_timer_returning_after_close_is_cancelled(self):
        self.assertTrue(self.window.open())
        self.inject_module('GUI', mcursor=lambda: runtime_fixtures.Obj(position=(0, 0), inFocus=True))
        self.inject_module('Keys', KEY_LEFTMOUSE=1)
        sys.modules['BigWorld'].isKeyDown = lambda key: True
        original = self.timer.schedule

        def late(seconds, callback):
            self.window.close()
            return original(seconds, callback)

        sys.modules['BigWorld'].callback = late
        self.window._begin_resize('se', '1')
        self.assertEqual(self.timer.callbacks, {})
        self.assertIsNone(self.window._resize_callback_id)
        self.assertIsNone(self.window._resize_gesture)

    def test_cursor_failure_ends_renderer_capture_and_discards_its_anchor(self):
        self.assertTrue(self.window.open())
        cursor = runtime_fixtures.Obj(position=(0, 0), inFocus=True)
        self.inject_module('GUI', mcursor=lambda: cursor)
        self.inject_module('Keys', KEY_LEFTMOUSE=1)
        sys.modules['BigWorld'].isKeyDown = lambda key: True
        self.window._begin_resize('nw', '1')
        cursor.position = (float('nan'), 0)
        self.timer.fire(self.window._resize_callback_id)
        self.assertIsNone(self.window._resize_gesture)
        self.assertIsNone(self.window._resize_anchor)
        self.assertIsNone(self.window._resize_callback_id)
        self.assertFalse(json.loads(self.window._model._payload)['resize_gesture']['active'])

    def test_resize_poll_is_cancelled_on_close_and_cannot_reach_a_new_window(self):
        self.assertTrue(self.window.open())
        self.inject_module('GUI', mcursor=lambda: runtime_fixtures.Obj(position=(0, 0), inFocus=True))
        self.inject_module('Keys', KEY_LEFTMOUSE=1)
        sys.modules['BigWorld'].isKeyDown = lambda key: True
        self.window._begin_resize('se', '1')
        callback_id = self.window._resize_callback_id
        stale = self.timer.callbacks[callback_id][1]
        self.window.close()
        self.assertNotIn(callback_id, self.timer.callbacks)
        self.assertTrue(self.window.open())
        before = self.window._model._payload
        stale()
        self.assertEqual(self.window._model._payload, before)
        self.assertIsNone(self.window._resize_gesture)

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
