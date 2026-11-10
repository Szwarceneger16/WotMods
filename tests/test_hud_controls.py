"""Cursor polling regressions: never bind native GUI KeyEvent callbacks."""
import types
import unittest
from unittest.mock import patch

import test_mod as runtime


class HudControlTests(unittest.TestCase):
    def setUp(self):
        self.game = runtime.Tests()
        self.game.TEST_CONTROLS = True
        self.game.setUp()
        self.mod = self.game.mod
        self.panel = self.game.panel
        self.button_down = False
        self.ctrl = False
        self.right_down = False
        self.queried_keys = []
        import Keys
        Keys.KEY_LEFTMOUSE = 1
        Keys.KEY_RIGHTMOUSE = 2
        Keys.KEY_LCONTROL = 29
        Keys.KEY_RCONTROL = 157
        def key_state(key):
            self.queried_keys.append(key)
            if key != Keys.KEY_LEFTMOUSE:
                raise AssertionError('only primitive LMB state may be queried')
            return self.button_down
        self.game.world.isKeyDown = key_state
        self.cursor = types.SimpleNamespace(active=True, visible=True, position=(0.0, 0.0))
        self.game.gui.mcursor = lambda: self.cursor
        self.pointer_calls = []
        self.pointer_manager = types.SimpleNamespace(setCursorForced=self.pointer_calls.append)
        self.panel.app.cursorMgr = self.pointer_manager
        original_setattr = runtime.Component.__setattr__
        def reject_native_input(component, name, value):
            if name in ('focus', 'moveFocus', 'mouseButtonFocus') and value:
                raise AssertionError('native GUI input would bind BW::KeyEvent')
            if name == 'script' and value is not None:
                raise AssertionError('native GUI scripts are unsafe in this client')
            original_setattr(component, name, value)
        self.input_guard = patch.object(runtime.Component, '__setattr__', reject_native_input)
        self.input_guard.start()

    def tearDown(self):
        if self.mod._panel is not None:
            self.game.emit_unregister()
        self.flush('detach_control_roots')
        self.input_guard.stop()
        self.game.tearDown()

    def flush(self, name):
        for job, (unused_delay, callback) in list(self.game.world.jobs.items()):
            if callback.__name__ == name:
                self.game.world.jobs.pop(job, None)
                callback()

    def sync(self, baseline=True):
        self.mod._sync_controls(self.panel)
        if baseline and self.mod._controls_poll_callback is not None:
            self.poll()

    def poll(self):
        job = self.mod._controls_poll_callback
        self.assertIsNotNone(job)
        delay, callback = self.game.world.jobs.pop(job)
        self.game.world.clock += delay
        callback()

    def sample(self, down, index=None, position=None):
        self.button_down = down
        if index is not None:
            self.cursor.position = self.mod._controls[index][0].position[:2]
        elif position is not None:
            self.cursor.position = position
        self.poll()

    def click(self, index):
        self.sample(True, index)
        self.sample(False, index)
        self.flush('apply_control_action')

    def test_state_tick_creates_visual_only_icons_above_medkit_and_one_timer(self):
        self.game.state()
        self.assertEqual(len(self.mod._controls), 2)
        geometry, unused_origin = self.mod._geometry(self.panel, 3)
        for component, unused_owner, unused_mount, unused_state in self.mod._controls:
            self.assertTrue(component.visible)
            self.assertFalse(component.focus)
            self.assertFalse(component.moveFocus)
            self.assertFalse(component.mouseButtonFocus)
            self.assertIsNone(component.script)
            self.assertGreater(component.position[1], geometry[1])
            self.assertEqual(component.size, (16.0, 16.0))
        for unused in range(5):
            self.mod._sync_controls(self.panel)
        polls = [callback for delay, callback in self.game.world.jobs.values()
                 if callback.__name__ == '_poll_controls']
        self.assertEqual(len(polls), 1)

    def test_controls_remain_available_during_cooldown_and_with_reminder_disabled(self):
        self.game.item.isAvailableToUse = False
        self.mod._reminder_enabled = False
        self.sync()
        self.assertTrue(all(entry[0].visible for entry in self.mod._controls))
        self.assertTrue(self.mod._controls[0][0].textureName.endswith('power_off.dds'))
        self.click(0)
        self.assertTrue(self.mod._reminder_enabled)

    def test_plain_and_ctrl_click_toggle_both_icons_using_only_lmb_query(self):
        self.sync()
        for ctrl in (False, True):
            self.ctrl = ctrl
            for index, setting in ((0, '_reminder_enabled'), (1, '_voice_enabled')):
                with self.subTest(ctrl=ctrl, setting=setting):
                    before = getattr(self.mod, setting)
                    self.click(index)
                    self.assertEqual(getattr(self.mod, setting), not before)
                    self.mod._sync_controls(self.panel)
                    suffix = 'on.dds' if not before else 'off.dds'
                    self.assertTrue(self.mod._controls[index][0].textureName.endswith(suffix))
        self.assertEqual(set(self.queried_keys), {1})

    def test_hold_and_release_queue_one_action_then_apply_outside_poll(self):
        self.sync()
        self.sample(True, 0)
        for unused in range(8):
            self.poll()
        self.assertTrue(self.mod._reminder_enabled)
        self.assertEqual(self.mod._controls_pending_actions, [])
        self.sample(False, 0)
        self.assertTrue(self.mod._reminder_enabled)
        self.assertEqual(len(self.mod._controls_pending_actions), 1)
        self.poll()
        self.assertEqual(len(self.mod._controls_pending_actions), 1)
        self.flush('apply_control_action')
        self.assertFalse(self.mod._reminder_enabled)
        self.flush('apply_control_action')
        self.assertFalse(self.mod._reminder_enabled)

    def test_releasing_ctrl_between_press_and_release_does_not_cancel_click(self):
        self.sync()
        self.ctrl = True
        self.sample(True, 0)
        self.ctrl = False
        self.sample(False, 0)
        self.flush('apply_control_action')
        self.assertFalse(self.mod._reminder_enabled)

    def test_mouse_held_before_allocation_is_not_a_click(self):
        self.button_down = True
        self.sync()
        self.sample(False, 0)
        self.flush('apply_control_action')
        self.assertTrue(self.mod._reminder_enabled)
        self.click(0)
        self.assertFalse(self.mod._reminder_enabled)

    def test_mouse_held_before_cursor_activation_is_not_a_click(self):
        self.cursor.active = False
        self.sync()
        self.button_down = True
        self.cursor.active = True
        self.sample(True, 0)
        self.sample(False, 0)
        self.flush('apply_control_action')
        self.assertTrue(self.mod._reminder_enabled)
        self.click(0)
        self.assertFalse(self.mod._reminder_enabled)

    def test_poll_uses_20ms_active_and_100ms_inactive_intervals(self):
        self.sync()
        self.assertEqual(self.game.world.jobs[self.mod._controls_poll_callback][0], 0.02)
        self.cursor.visible = False
        self.poll()
        self.assertEqual(self.game.world.jobs[self.mod._controls_poll_callback][0], 0.10)
        self.cursor.visible = True
        self.poll()
        self.assertEqual(self.game.world.jobs[self.mod._controls_poll_callback][0], 0.02)

    def test_pointing_hand_follows_both_icons_without_changing_native_input(self):
        self.sync()
        roots = list(self.game.gui.roots)
        self.assertEqual(self.pointer_calls, [])
        self.cursor.position = self.mod._controls[0][0].position[:2]
        self.poll()
        self.assertEqual(self.pointer_calls, ['button'])
        for unused in range(5):
            self.poll()
        self.cursor.position = self.mod._controls[1][0].position[:2]
        self.poll()
        self.assertEqual(self.pointer_calls, ['button'], 'Stable hover never forces a cursor every tick')
        self.cursor.position = (-0.9, 0.9)
        self.poll()
        self.assertEqual(self.pointer_calls, ['button', 'arrow'])
        self.assertEqual(self.game.gui.roots, roots)
        for component, unused_owner, unused_mount, unused_state in self.mod._controls:
            self.assertIsNone(component.script)
            self.assertFalse(component.focus or component.mouseButtonFocus or component.moveFocus)

    def test_pointer_checks_full_hud_eligibility_only_after_a_visible_icon_hit(self):
        self.sync()
        with patch.object(self.mod, '_controls_cursor_active', wraps=self.mod._controls_cursor_active) as eligible:
            for unused in range(4):
                self.poll()
            eligible.assert_not_called()
            self.cursor.position = self.mod._controls[0][0].position[:2]
            self.poll()
            eligible.assert_called_once_with()

    def test_pointing_hand_releases_when_cursor_or_battle_hud_becomes_unavailable(self):
        self.sync()
        changes = (
            (self.cursor, 'active', False, True),
            (self.cursor, 'visible', False, True),
            (self.panel.app, 'isModalViewShown', lambda: True, lambda: False),
            (self.panel, 'native_visible', False, True),
            (self.panel, 'camera_mode', 'sniper', 'arcade'))
        for target, attribute, unavailable, available in changes:
            with self.subTest(attribute=attribute):
                self.cursor.position = self.mod._controls[0][0].position[:2]
                self.poll()
                self.assertEqual(self.pointer_calls[-1], 'button')
                setattr(target, attribute, unavailable)
                self.poll()
                self.assertEqual(self.pointer_calls[-1], 'arrow')
                self.assertIsNone(self.mod._controls_pointer_owner)
                setattr(target, attribute, available)

    def test_hide_and_dispose_release_the_owned_native_manager_once(self):
        self.sync()
        self.cursor.position = self.mod._controls[0][0].position[:2]
        self.poll()
        self.mod._hide_controls()
        self.mod._hide_controls()
        self.assertEqual(self.pointer_calls, ['button', 'arrow'])
        self.mod._sync_controls(self.panel)
        self.poll()
        self.assertEqual(self.pointer_calls[-1], 'button')
        self.game.emit_unregister()
        self.mod._delete_controls()
        self.assertEqual(self.pointer_calls, ['button', 'arrow', 'button', 'arrow'])
        self.assertIsNone(self.mod._controls_pointer_owner)

    def test_manager_replacement_is_not_overwritten_until_a_new_hover(self):
        self.sync()
        self.cursor.position = self.mod._controls[0][0].position[:2]
        self.poll()
        replacement_calls = []
        self.panel.app.cursorMgr = types.SimpleNamespace(setCursorForced=replacement_calls.append)
        self.poll()
        self.poll()
        self.assertEqual(self.pointer_calls, ['button'])
        self.assertEqual(replacement_calls, [])
        self.assertIsNone(self.mod._controls_pointer_owner)
        self.cursor.position = (-0.9, 0.9)
        self.poll()
        self.cursor.position = self.mod._controls[1][0].position[:2]
        self.poll()
        self.assertEqual(replacement_calls, ['button'])
        self.mod._delete_controls()
        self.assertEqual(replacement_calls, ['button', 'arrow'])

    def test_optional_cursor_api_failure_warns_once_and_keeps_clicks_working(self):
        def unavailable(shape):
            self.pointer_calls.append(shape)
            raise RuntimeError('optional native cursor unavailable')
        self.pointer_manager.setCursorForced = unavailable
        self.sync()
        messages = []
        with patch.object(self.mod, '_log', side_effect=messages.append):
            self.cursor.position = self.mod._controls[0][0].position[:2]
            self.poll()
            for unused in range(4):
                self.poll()
            self.click(0)
            self.assertFalse(self.mod._reminder_enabled)
            self.cursor.position = (-0.9, 0.9)
            self.poll()
            self.cursor.position = self.mod._controls[1][0].position[:2]
            self.poll()
        self.assertEqual(sum('HUD pointer unavailable' in message for message in messages), 1)
        self.assertEqual(self.pointer_calls, ['button', 'arrow', 'button', 'arrow'])
        self.assertFalse(self.mod._controls_disabled)
        self.assertEqual(len(self.mod._controls), 2)
        self.assertIn(self.mod._controls_poll_callback, self.game.world.jobs)

    def test_missing_cursor_manager_does_not_disable_clicks(self):
        self.sync()
        for manager in (None, object()):
            with self.subTest(manager=manager):
                self.panel.app.cursorMgr = manager
                self.cursor.position = (-0.9, 0.9)
                self.poll()
                before = self.mod._reminder_enabled
                self.click(0)
                self.assertEqual(self.mod._reminder_enabled, not before)
                self.assertFalse(self.mod._controls_disabled)
        self.assertEqual(self.pointer_calls, [])

    def test_perk_loss_releases_pointer_before_control_cleanup(self):
        self.sync()
        self.cursor.position = self.mod._controls[0][0].position[:2]
        self.poll()
        self.assertEqual(self.pointer_calls, ['button'])
        self.game.world.avatar.vehicle.crewCompactDescrs = ()
        self.poll()
        self.assertEqual(self.pointer_calls, ['button', 'arrow'])
        self.mod._refresh(self.panel)
        self.assertEqual(self.pointer_calls, ['button', 'arrow'])
        self.assertEqual(self.mod._controls, [])

    def test_poll_early_return_releases_pointer_after_panel_disappears(self):
        self.sync()
        self.cursor.position = self.mod._controls[0][0].position[:2]
        self.poll()
        self.mod._panel = None
        try:
            self.poll()
            self.assertEqual(self.pointer_calls, ['button', 'arrow'])
            self.assertIsNone(self.mod._controls_pointer_owner)
        finally:
            self.mod._panel = self.panel

    def test_release_outside_or_over_other_icon_cancels_press(self):
        self.sync()
        for position in ((-0.9, 0.9), self.mod._controls[1][0].position[:2]):
            with self.subTest(position=position):
                self.sample(True, 0)
                self.sample(False, position=position)
                self.flush('apply_control_action')
                self.assertTrue(self.mod._reminder_enabled)
                self.assertTrue(self.mod._voice_enabled)
        self.click(0)
        self.assertFalse(self.mod._reminder_enabled)

    def test_hidden_cursor_modal_camera_and_hidden_hud_cancel_pending_press(self):
        self.sync()
        changes = (
            (self.cursor, 'active', False, True),
            (self.cursor, 'visible', False, True),
            (self.panel.app, 'isModalViewShown', lambda: True, lambda: False),
            (self.panel, 'camera_mode', 'sniper', 'arcade'),
            (self.panel, 'native_visible', False, True))
        for target, attribute, disabled, enabled in changes:
            with self.subTest(attribute=attribute):
                self.poll()  # activation baseline after a previously hidden cursor
                self.sample(True, 0)
                setattr(target, attribute, disabled)
                self.sample(False, 0)
                self.flush('apply_control_action')
                self.assertTrue(self.mod._reminder_enabled)
                setattr(target, attribute, enabled)
        self.poll()
        self.click(0)
        self.assertFalse(self.mod._reminder_enabled)

    def test_regular_sniper_hides_icons_and_artillery_views_keep_them(self):
        self.sync()
        self.panel.camera_mode = 'sniper'
        self.mod._sync_controls(self.panel)
        self.assertFalse(any(entry[0].visible for entry in self.mod._controls))
        for mode in ('strategic', 'trajectory'):
            self.panel.camera_mode = mode
            self.mod._sync_controls(self.panel)
            self.assertTrue(all(entry[0].visible for entry in self.mod._controls))
        self.panel.camera_mode = 'sniper'
        self.game.world.avatar.vehicle.typeDescriptor.type.tags = {'SPG'}
        self.mod._sync_controls(self.panel)
        self.assertTrue(all(entry[0].visible for entry in self.mod._controls))

    def test_rmb_artillery_transitions_never_create_native_input_callbacks(self):
        self.sync()
        self.right_down = True
        for mode in ('strategic', 'trajectory', 'arcade', 'strategic'):
            self.panel.camera_mode = mode
            self.mod._sync_controls(self.panel)
            self.poll()
            self.assertTrue(all(entry[0].visible for entry in self.mod._controls))
            for component, unused_owner, unused_mount, unused_state in self.mod._controls:
                self.assertIsNone(component.script)
                self.assertFalse(component.focus or component.mouseButtonFocus or component.moveFocus)
        self.assertTrue(self.mod._reminder_enabled)
        self.assertEqual(self.mod._controls_pending_actions, [])
        self.assertEqual(set(self.queried_keys), {1})

    def test_disposal_cancels_poll_and_action_and_defers_native_root_removal(self):
        self.sync()
        self.sample(True, 0)
        self.sample(False, 0)
        stale_action = next(callback for delay, callback in self.game.world.jobs.values()
                            if callback.__name__ == 'apply_control_action')
        roots = list(self.game.gui.roots)
        native_dispatch_active = [True]
        original_del = self.game.gui.delRoot
        def guarded_del(component):
            if native_dispatch_active[0]:
                raise AssertionError('root vector must not change inside native dispatch')
            original_del(component)
        self.game.gui.delRoot = guarded_del
        self.game.emit_unregister()
        self.assertEqual(self.mod._controls, [])
        self.assertIsNone(self.mod._controls_poll_callback)
        self.assertEqual(self.mod._controls_pending_actions, [])
        self.assertEqual(self.game.gui.roots, roots)
        self.assertTrue(all(not component.visible for component in roots))
        stale_action()
        self.assertTrue(self.mod._reminder_enabled)
        native_dispatch_active[0] = False
        self.flush('detach_control_roots')
        self.assertEqual(self.game.gui.roots, [])
        self.assertEqual(self.mod._controls_pending_detaches, [])

    def test_deferred_old_battle_cleanup_preserves_new_icons_and_poll(self):
        self.sync()
        old_roots = list(self.game.gui.roots)
        self.game.emit_unregister()
        self.game.emit_register()
        self.sync()
        new_roots = [entry[0] for entry in self.mod._controls]
        self.assertEqual(len(self.game.gui.roots), 4)
        self.assertTrue(all(not component.visible for component in old_roots))
        self.flush('detach_control_roots')
        self.assertEqual(self.game.gui.roots, new_roots)
        self.assertTrue(all(component.visible for component in new_roots))
        self.assertIn(self.mod._controls_poll_callback, self.game.world.jobs)

    def test_deferred_click_is_cancelled_if_modal_opens_before_apply(self):
        self.sync()
        self.sample(True, 0)
        self.sample(False, 0)
        self.panel.app.isModalViewShown = lambda: True
        self.flush('apply_control_action')
        self.assertTrue(self.mod._reminder_enabled)
        self.assertEqual(self.mod._controls_pending_actions, [])

    def test_destroyed_vehicle_and_perk_loss_cancel_controls(self):
        self.sync()
        self.sample(True, 0)
        self.game.world.avatar.vehicle.health = 0
        self.sample(False, 0)
        self.flush('apply_control_action')
        self.assertTrue(self.mod._reminder_enabled)
        self.game.world.avatar.vehicle.health = 1000
        self.game.world.avatar.vehicle.crewCompactDescrs = ()
        self.mod._refresh(self.panel)
        self.assertEqual(self.mod._controls, [])
        self.assertIsNone(self.mod._controls_poll_callback)
        self.flush('detach_control_roots')
        self.assertEqual(self.game.gui.roots, [])

    def test_partial_attachment_failure_hides_then_detaches_created_roots(self):
        original_add = self.game.gui.addRoot
        count = [0]
        def partial_add(component):
            count[0] += 1
            original_add(component)
            if count[0] == 2:
                raise RuntimeError('native attachment raised after registration')
        self.game.gui.addRoot = partial_add
        self.mod._sync_controls(self.panel)
        self.assertTrue(self.mod._controls_disabled)
        self.assertEqual(self.mod._controls, [])
        self.assertIsNone(self.mod._controls_poll_callback)
        self.assertEqual(len(self.game.gui.roots), 2)
        self.assertTrue(all(not component.visible for component in self.game.gui.roots))
        self.flush('detach_control_roots')
        self.assertEqual(self.game.gui.roots, [])

    def assert_poll_api_failure_is_safe(self):
        self.poll()
        self.assertTrue(self.mod._controls_disabled)
        self.assertEqual(self.mod._controls, [])
        self.assertIsNone(self.mod._controls_poll_callback)
        self.flush('detach_control_roots')
        self.assertEqual(self.game.gui.roots, [])

    def test_missing_button_query_api_hides_controls_without_event_fallback(self):
        self.sync()
        del self.game.world.isKeyDown
        self.assert_poll_api_failure_is_safe()

    def test_raising_button_query_api_hides_controls_without_event_fallback(self):
        self.sync()
        def unavailable(key):
            raise RuntimeError('primitive button query unavailable')
        self.game.world.isKeyDown = unavailable
        self.assert_poll_api_failure_is_safe()


if __name__ == '__main__':
    unittest.main()
