"""Garage recording, persisted settings and battle keyboard integration."""
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import test_mod as runtime


class SettingsIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.game = runtime.Tests()
        self.game.setUp()
        self.mod = self.game.mod
        self.panel = self.game.panel
        self.arena = self.game.world.avatar.arena
        self.path = Path(self.mod._settings_store.path)
        # These tests drive root actions directly; native popup focus itself
        # is covered by the garage view tests.
        self.capture_guard = patch.object(self.mod, '_garage_capture_allowed', return_value=True, create=True)
        self.capture_allowed = self.capture_guard.start()

    def tearDown(self):
        self.game.tearDown()
        self.capture_guard.stop()

    def garage(self):
        self.game.emit_unregister()
        self.game.world.avatar.arena = None
        self.action('open')
        self.assertTrue(self.mod._garage_open)

    def battle(self):
        self.game.world.avatar.arena = self.arena
        self.game.emit_register()
        self.assertIs(self.mod._panel, self.panel)

    def action(self, action, binding=None):
        command = {'action': action}
        if binding is not None:
            command['binding'] = binding
        self.mod._garage_action(command)

    def capture(self, binding, codes):
        self.action('begin_capture', binding)
        self.assertEqual(self.mod._capture_target, binding)
        for code in codes:
            self.game.key(code)
        for code in reversed(codes):
            self.game.key(code, False)
        self.assertIsNone(self.mod._capture_target)

    def disk(self):
        return json.loads(self.path.read_text())

    def configure_u_i_shortcuts(self):
        self.garage()
        self.capture('toggle_mod', (22,))
        self.capture('toggle_voice', (23,))
        self.assertEqual(self.disk()['hotkeys'],
                         {'toggle_mod': ['U'], 'toggle_voice': ['I']})
        self.action('close')
        self.battle()

    def test_persisted_u_i_shortcuts_toggle_once_while_native_w_stays_held(self):
        import Keys
        with patch.multiple(Keys, KEY_W=17, KEY_U=22, KEY_I=23, create=True):
            self.configure_u_i_shortcuts()
            with patch.object(self.mod, '_toggle_reminder', wraps=self.mod._toggle_reminder) as power, \
                    patch.object(self.mod, '_toggle_voice', wraps=self.mod._toggle_voice) as voice:
                self.game.key(Keys.KEY_W)
                self.game.key(Keys.KEY_U)
                self.game.key(Keys.KEY_U, repeated=True)
                self.game.key(Keys.KEY_I)
                self.game.key(Keys.KEY_I, repeated=True)
                self.assertFalse(self.mod._reminder_enabled)
                self.assertFalse(self.mod._voice_enabled)
                self.assertEqual((power.call_count, voice.call_count), (1, 1))
                self.assertTrue(self.game.world.isKeyDown(Keys.KEY_W))
                self.game.key(Keys.KEY_I, False)
                self.game.key(Keys.KEY_U, False)
                self.assertEqual(self.game.physical_keys, {Keys.KEY_W})
                self.assertEqual(self.mod._shortcut_tracker.held_keys, ('W',))
                self.game.key(Keys.KEY_W, False)
                self.assertEqual((power.call_count, voice.call_count), (1, 1))

    def test_chat_and_modal_still_block_custom_shortcuts_while_driving(self):
        import Keys
        with patch.multiple(Keys, KEY_W=17, KEY_U=22, KEY_I=23, create=True):
            self.configure_u_i_shortcuts()
            self.game.key(Keys.KEY_W)
            with patch.object(self.mod, '_toggle_reminder', wraps=self.mod._toggle_reminder) as power, \
                    patch.object(self.mod, '_toggle_voice', wraps=self.mod._toggle_voice) as voice:
                self.game.chat_focused = True
                self.game.press_shortcut((Keys.KEY_U,))
                self.game.chat_focused = False
                self.panel.app.isModalViewShown = lambda: True
                self.game.press_shortcut((Keys.KEY_I,))
                self.assertTrue(self.mod._reminder_enabled)
                self.assertTrue(self.mod._voice_enabled)
                power.assert_not_called()
                voice.assert_not_called()
                self.assertEqual(self.game.physical_keys, {Keys.KEY_W})
                self.panel.app.isModalViewShown = lambda: False
                self.game.press_shortcut((Keys.KEY_U,))
                self.game.press_shortcut((Keys.KEY_I,))
                self.assertEqual((power.call_count, voice.call_count), (1, 1))
                self.assertFalse(self.mod._reminder_enabled)
                self.assertFalse(self.mod._voice_enabled)
                self.assertEqual(self.game.physical_keys, {Keys.KEY_W})
            self.game.key(Keys.KEY_W, False)

    def test_garage_capture_keeps_w_u_i_and_the_saved_chord_requires_w(self):
        import Keys
        with patch.multiple(Keys, KEY_W=17, KEY_U=22, KEY_I=23, create=True):
            self.garage()
            before = self.path.read_bytes()
            self.action('begin_capture', 'toggle_mod')
            with patch.object(self.mod, '_toggle_reminder') as power, \
                    patch.object(self.mod, '_toggle_voice') as voice:
                for code in (Keys.KEY_W, Keys.KEY_U, Keys.KEY_I):
                    self.game.key(code)
                self.assertEqual(self.mod._garage_payload()['preview'], ['I', 'U', 'W'])
                self.game.key(Keys.KEY_I, False)
                self.game.key(Keys.KEY_U, False)
                self.assertEqual(self.path.read_bytes(), before)
                self.assertEqual(self.mod._capture_target, 'toggle_mod')
                self.assertTrue(self.game.world.isKeyDown(Keys.KEY_W))
                self.game.key(Keys.KEY_W, False)
                power.assert_not_called()
                voice.assert_not_called()
            self.assertEqual(self.disk()['hotkeys']['toggle_mod'], ['I', 'U', 'W'])
            self.action('close')
            self.battle()
            self.game.press_shortcut((Keys.KEY_U, Keys.KEY_I))
            self.assertTrue(self.mod._reminder_enabled)
            self.game.press_shortcut((Keys.KEY_W, Keys.KEY_U, Keys.KEY_I))
            self.assertFalse(self.mod._reminder_enabled)
            self.assertTrue(self.mod._voice_enabled)

    def test_three_and_four_key_capture_persists_then_toggles_in_battle(self):
        self.garage()
        before = self.path.read_bytes()
        self.action('begin_capture', 'toggle_mod')
        with patch.object(self.mod, '_toggle_reminder') as power, patch.object(self.mod, '_toggle_voice') as voice:
            for code in (30, 48, 46):  # A+B+C
                self.game.key(code)
            self.assertEqual(self.path.read_bytes(), before)
            self.game.key(46, False)
            self.game.key(48, False)
            self.assertEqual(self.path.read_bytes(), before)
            self.game.key(30, False)
            power.assert_not_called()
            voice.assert_not_called()
        self.assertEqual(self.disk()['hotkeys']['toggle_mod'], ['A', 'B', 'C'])
        self.capture('toggle_voice', (50, 47, 45, 30))  # M+V+X+A
        self.assertEqual(self.disk()['hotkeys']['toggle_voice'], ['A', 'M', 'V', 'X'])
        self.assertEqual(list(self.path.parent.glob('.staysharp-medkit-*.tmp')), [])
        self.action('close')
        self.action('open')
        self.assertEqual(self.mod._garage_payload()['display']['toggle_mod'], 'A + B + C')
        self.assertEqual(self.mod._garage_payload()['display']['toggle_voice'], 'A + M + V + X')
        self.action('close')
        self.battle()
        self.game.press_shortcut((30, 48, 46))
        self.assertFalse(self.mod._reminder_enabled)
        self.assertTrue(self.mod._voice_enabled)
        self.game.press_shortcut((50, 47, 45, 30))
        self.assertFalse(self.mod._voice_enabled)
        self.game.press_shortcut((30, 48, 46))
        self.assertTrue(self.mod._reminder_enabled)

    def test_side_specific_four_key_capture_preserves_sides(self):
        self.garage()
        self.capture('toggle_mod', (29, 184, 42, 45))  # left Ctrl, right Alt, left Shift, X
        self.assertEqual(self.disk()['hotkeys']['toggle_mod'], ['LCTRL', 'RALT', 'LSHIFT', 'X'])
        self.action('close')
        self.battle()
        self.game.press_shortcut((157, 184, 42, 45))
        self.assertTrue(self.mod._reminder_enabled)
        self.game.press_shortcut((29, 184, 42, 45))
        self.assertFalse(self.mod._reminder_enabled)

    def test_existing_default_shortcut_is_recorded_without_running_actions(self):
        self.garage()
        with patch.object(self.mod, '_toggle_reminder') as power, patch.object(self.mod, '_toggle_voice') as voice:
            self.capture('toggle_mod', (29, 56, 50))
            power.assert_not_called()
            voice.assert_not_called()
        self.assertEqual(self.disk()['hotkeys']['toggle_mod'], ['LCTRL', 'LALT', 'M'])

    def test_overlapping_capture_preserves_file_and_previous_active_binding(self):
        self.garage()
        before = self.path.read_bytes()
        old = self.mod._settings_store.get_payload()['hotkeys']
        self.capture('toggle_mod', (29, 56, 47))  # overlaps the voice default
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(self.mod._settings_store.get_payload()['hotkeys'], old)
        self.assertEqual(self.mod._settings_store.last_error, 'conflicting_hotkeys')
        self.assertTrue(self.mod._settings_error)
        self.action('close')
        self.battle()
        self.game.press_shortcut()
        self.assertFalse(self.mod._reminder_enabled)
        self.assertTrue(self.mod._voice_enabled)

    def test_failed_atomic_replacement_preserves_file_and_active_binding(self):
        self.garage()
        before = self.path.read_bytes()
        old = self.mod._settings_store.get_payload()['hotkeys']
        settings_module = sys.modules['staysharp_medkit.settings']
        with patch.object(settings_module, '_replace_file', side_effect=OSError('simulated replacement failure')):
            self.capture('toggle_mod', (30, 48, 46))
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(self.mod._settings_store.get_payload()['hotkeys'], old)
        self.assertTrue(self.mod._settings_error)
        self.assertEqual(list(self.path.parent.glob('.staysharp-medkit-*.tmp')), [])
        self.action('close')
        self.battle()
        self.game.press_shortcut((30, 48, 46))
        self.assertTrue(self.mod._reminder_enabled)
        self.game.press_shortcut()
        self.assertFalse(self.mod._reminder_enabled)

    def test_clear_binding_disables_only_its_keyboard_action(self):
        self.garage()
        self.action('clear_binding', 'toggle_mod')
        self.assertEqual(self.disk()['hotkeys']['toggle_mod'], [])
        self.action('close')
        self.action('open')
        self.assertEqual(self.mod._garage_payload()['display']['toggle_mod'], '')
        self.action('close')
        self.battle()
        self.game.press_shortcut()
        self.assertTrue(self.mod._reminder_enabled)
        self.game.press_shortcut((29, 56, 47))
        self.assertFalse(self.mod._voice_enabled)

    def test_battle_transition_cancels_partial_capture_and_rejects_late_command(self):
        self.garage()
        before = self.path.read_bytes()
        self.action('begin_capture', 'toggle_mod')
        self.game.key(30)
        self.game.key(48)
        self.battle()
        self.assertIsNone(self.mod._capture_target)
        self.assertFalse(self.mod._shortcut_tracker.capture_active)
        self.game.key(48, False)
        self.game.key(30, False)
        self.action('begin_capture', 'toggle_voice')
        self.assertIsNone(self.mod._capture_target)
        self.assertEqual(self.path.read_bytes(), before)
        self.game.press_shortcut()
        self.assertFalse(self.mod._reminder_enabled)

    def test_close_and_unload_cancel_capture_without_saving_or_handlers(self):
        self.garage()
        before = self.path.read_bytes()
        for terminate in ('close', 'unload'):
            self.action('open')
            self.action('begin_capture', 'toggle_mod')
            self.game.key(30)
            if terminate == 'close':
                self.action('close')
            else:
                self.mod.fini()
            self.assertIsNone(self.mod._capture_target)
            self.assertFalse(self.mod._shortcut_tracker.capture_active)
            self.assertEqual(self.game.key_event.handlers, [])
            self.assertEqual(self.game.key_up_event.handlers, [])
            self.game.key(30, False)
            self.assertEqual(self.path.read_bytes(), before)

    def test_chat_and_modal_suppress_configured_battle_chords(self):
        self.game.chat_focused = True
        self.game.press_shortcut()
        self.assertTrue(self.mod._reminder_enabled)
        self.game.chat_focused = False
        self.panel.app.isModalViewShown = lambda: True
        self.game.press_shortcut((29, 56, 47))
        self.assertTrue(self.mod._voice_enabled)
        self.panel.app.isModalViewShown = lambda: False
        self.game.press_shortcut()
        self.assertFalse(self.mod._reminder_enabled)

    def test_mouse_input_is_ignored_before_crew_or_modal_lookup(self):
        import Keys
        Keys.KEY_RIGHTMOUSE = 2
        with patch.object(self.mod, '_crew_perk_status') as crew, patch.object(self.mod, '_input_blocked') as blocked:
            self.game.key(2)
            self.game.key(2, False)
            crew.assert_not_called()
            blocked.assert_not_called()
        self.assertTrue(self.mod._reminder_enabled)
        self.assertTrue(self.mod._voice_enabled)

    def test_native_popup_focus_guard_cancels_capture_without_saving(self):
        self.garage()
        before = self.path.read_bytes()
        self.action('begin_capture', 'toggle_mod')
        self.game.key(30)
        self.capture_allowed.return_value = False
        self.game.key(48)
        self.assertIsNone(self.mod._capture_target)
        self.assertFalse(self.mod._shortcut_tracker.capture_active)
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(self.game.key_event.handlers, [])
        self.assertEqual(self.game.key_up_event.handlers, [])

    def test_unknown_nested_hotkey_field_is_preserved_and_not_registered(self):
        self.garage()
        document = self.disk()
        document['hotkeys']['future_binding_metadata'] = {'layout': {'keys': [1, 2, 3]}}
        self.path.write_text(json.dumps(document))
        self.action('open')
        self.assertTrue(self.mod._garage_open)
        self.assertEqual(set(self.mod._garage_payload()['display']), {'toggle_mod', 'toggle_voice'})
        self.capture('toggle_mod', (30, 48, 46))
        self.assertEqual(self.disk()['hotkeys']['future_binding_metadata'], {'layout': {'keys': [1, 2, 3]}})
        self.action('close')
        self.battle()
        self.game.press_shortcut((30, 48, 46))
        self.assertFalse(self.mod._reminder_enabled)

    def test_reopening_during_capture_cancels_then_allows_a_new_recording(self):
        self.garage()
        before = self.path.read_bytes()
        self.action('begin_capture', 'toggle_mod')
        self.game.key(30)
        self.game.key(48)
        self.action('open')
        self.assertIsNone(self.mod._capture_target)
        self.assertFalse(self.mod._shortcut_tracker.capture_active)
        self.assertEqual(self.path.read_bytes(), before)
        self.game.key(48, False)
        self.game.key(30, False)
        self.capture('toggle_mod', (30, 48, 46))
        self.assertEqual(self.disk()['hotkeys']['toggle_mod'], ['A', 'B', 'C'])

    def test_arena_arriving_before_battle_panel_cancels_garage_capture(self):
        self.garage()
        before = self.path.read_bytes()
        self.action('begin_capture', 'toggle_mod')
        self.game.key(30)
        self.game.world.avatar.arena = self.arena
        self.game.key(48)
        self.assertIsNone(self.mod._capture_target)
        self.assertFalse(self.mod._shortcut_tracker.capture_active)
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(self.game.key_event.handlers, [])

    def test_lost_battle_modifier_release_cannot_complete_a_later_shortcut(self):
        self.game.key(29)
        self.game.physical_keys.discard(29)  # OS focus change lost the key-up event.
        self.game.key(56)
        self.game.key(50)
        self.assertTrue(self.mod._reminder_enabled)
        self.game.key(50, False)
        self.game.key(56, False)
        self.game.press_shortcut()
        self.assertFalse(self.mod._reminder_enabled)

    def test_lost_capture_key_release_cancels_before_new_keys_can_be_recorded(self):
        self.garage()
        before = self.path.read_bytes()
        self.action('begin_capture', 'toggle_mod')
        self.game.key(30)
        self.game.physical_keys.discard(30)
        self.game.key(48)
        self.assertIsNone(self.mod._capture_target)
        self.assertFalse(self.mod._shortcut_tracker.capture_active)
        self.assertEqual(self.path.read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
