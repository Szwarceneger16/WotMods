"""Primitive keyboard chords; no client or GUI imports are needed."""
import importlib.util
from pathlib import Path
import types
import unittest

SOURCE = Path(__file__).resolve().parents[1] / 'source/staysharp_medkit/hotkeys.py'
spec = importlib.util.spec_from_file_location('medkit_hotkeys_test', SOURCE)
hotkeys = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hotkeys)


class HotkeyTests(unittest.TestCase):
    def test_normalize_aliases_order_and_disabled_chords(self):
        self.assertEqual(hotkeys.normalize_chord('m + Alt + Control'), ['CTRL', 'ALT', 'M'])
        self.assertEqual(hotkeys.normalize_chord(['KEY_RCONTROL', 'key_LSHIFT', 'a']),
                         ['RCTRL', 'LSHIFT', 'A'])
        for disabled in (None, [], (), ''):
            self.assertEqual(hotkeys.normalize_chord(disabled), [])
        self.assertEqual(hotkeys.format_chord(['m', 'ctrl']), 'CTRL+M')
        self.assertEqual(hotkeys.normalize_chord(['CTRL', 'CTRL', 'M']), ['CTRL', 'M'])

    def test_reject_invalid_keys_types_mouse_and_oversized_chords(self):
        for value in (23, {}, ['MOUSE1'], ['KEY_LEFTMOUSE'], ['JOY0'], ['NOT_A_REAL_KEY'],
                      [True], [15], 'CTRL++M', ['CTRL', 'LCTRL'], ['A'] * 33):
            with self.subTest(value=value), self.assertRaises(ValueError):
                hotkeys.normalize_chord(value)

    def test_dynamic_client_key_codes_and_unusual_keyboard_names(self):
        keys = types.SimpleNamespace(KEY_LCONTROL=29, KEY_RCONTROL=157,
                                     KEY_M=50, KEY_ABNT_C1=115, KEY_LEFTMOUSE=1,
                                     KEY_JOY0=200, KEY_NONE=0)
        self.assertEqual(hotkeys.key_name(29, keys), 'LCTRL')
        self.assertEqual(hotkeys.key_name(115, keys), 'ABNT_C1')
        self.assertIsNone(hotkeys.key_name(1, keys))
        self.assertIsNone(hotkeys.key_name(200, keys))
        self.assertIsNone(hotkeys.key_name(0, keys))
        self.assertIsNone(hotkeys.key_name(True, keys))
        self.assertEqual(hotkeys.normalize_chord(['ABNT_C1'], keys), ['ABNT_C1'])
        tracker = hotkeys.ChordTracker({'power': ['CTRL', 'M']}, keys)
        self.assertEqual(tracker.feed(29, True)['actions'], [])
        self.assertEqual(tracker.feed(50, True)['actions'], ['power'])
        tracker = hotkeys.ChordTracker({'voice': ['CTRL', 'ABNT_C1']}, keys)
        tracker.feed(157, True)
        self.assertEqual(tracker.feed(115, True)['actions'], ['voice'])
        tracker.begin_capture()
        tracker.feed(115, True)
        self.assertEqual(tracker.feed(115, False)['captured'], ['ABNT_C1'])

    def test_generic_modifiers_accept_either_side(self):
        tracker = hotkeys.ChordTracker({'power': 'CTRL+ALT+M'})
        for ctrl, alt in (('LCTRL', 'LALT'), ('RCTRL', 'RALT')):
            tracker.reset()
            tracker.feed(ctrl, True)
            tracker.feed(alt, True)
            self.assertEqual(tracker.feed('M', True)['actions'], ['power'])

    def test_side_specific_modifiers_and_both_sides_remain_distinct(self):
        tracker = hotkeys.ChordTracker({'voice': ['LCTRL', 'RCTRL', 'M']})
        tracker.feed('LCTRL', True)
        self.assertEqual(tracker.feed('M', True)['actions'], [])
        self.assertEqual(tracker.feed('RCTRL', True)['actions'], ['voice'])

    def test_four_key_nonmodifier_chord_matches_in_any_press_order(self):
        tracker = hotkeys.ChordTracker({'voice': ['A', 'S', 'D', 'F']})
        for name in ('D', 'F', 'S'):
            self.assertEqual(tracker.feed(name, True)['actions'], [])
        self.assertEqual(tracker.feed('A', True)['actions'], ['voice'])

    def test_hold_and_repeat_emit_once_until_a_chord_key_releases(self):
        tracker = hotkeys.ChordTracker({'power': 'CTRL+M'})
        tracker.feed('LCTRL', True)
        self.assertEqual(tracker.feed('M', True)['actions'], ['power'])
        self.assertEqual(tracker.feed('M', True, repeated=True)['actions'], [])
        self.assertEqual(tracker.feed('M', True)['actions'], [])
        tracker.feed('A', True)
        tracker.feed('A', False)
        self.assertEqual(tracker.feed('M', True)['actions'], [])
        tracker.feed('M', False)
        self.assertEqual(tracker.feed('M', True)['actions'], ['power'])

    def test_unrelated_held_key_prevents_activation_and_release_does_not_fire(self):
        tracker = hotkeys.ChordTracker({'power': 'CTRL+M'})
        tracker.feed('A', True)
        tracker.feed('LCTRL', True)
        self.assertEqual(tracker.feed('M', True)['actions'], [])
        self.assertEqual(tracker.feed('A', False)['actions'], [])
        tracker.feed('M', False)
        self.assertEqual(tracker.feed('M', True)['actions'], ['power'])

    def test_two_actions_and_disabled_binding_are_independent(self):
        tracker = hotkeys.ChordTracker({'toggle_mod': 'CTRL+M', 'toggle_voice': 'ALT+V', 'off': []})
        tracker.feed('LCTRL', True)
        self.assertEqual(tracker.feed('M', True)['actions'], ['toggle_mod'])
        tracker.reset()
        tracker.feed('RALT', True)
        self.assertEqual(tracker.feed('V', True)['actions'], ['toggle_voice'])

    def test_blocked_chat_or_modal_clears_keys_and_cancels_capture(self):
        tracker = hotkeys.ChordTracker({'power': 'CTRL+M'})
        tracker.feed('LCTRL', True)
        self.assertEqual(tracker.feed('M', True, blocked=True)['actions'], [])
        self.assertEqual(tracker.held_keys, ())
        self.assertEqual(tracker.feed('M', True, repeated=True)['actions'], [])
        tracker.begin_capture()
        self.assertTrue(tracker.feed('A', True, blocked=True)['cancelled'])
        self.assertFalse(tracker.capture_active)

    def test_capture_completes_only_after_all_keys_release(self):
        tracker = hotkeys.ChordTracker({'power': 'CTRL+ALT+M'})
        tracker.begin_capture()
        for name in ('LCTRL', 'RALT', 'LSHIFT', 'M'):
            result = tracker.feed(name, True)
            self.assertEqual(result['actions'], [])
            self.assertIsNone(result['captured'])
        for name in ('M', 'LCTRL', 'RALT'):
            self.assertIsNone(tracker.feed(name, False)['captured'])
        self.assertEqual(tracker.feed('LSHIFT', False)['captured'], ['CTRL', 'ALT', 'SHIFT', 'M'])
        self.assertFalse(tracker.capture_active)

    def test_capture_records_simultaneous_keys_not_sequential_union(self):
        tracker = hotkeys.ChordTracker()
        tracker.begin_capture()
        tracker.feed('LCTRL', True)
        tracker.feed('A', True)
        tracker.feed('A', False)
        tracker.feed('B', True)
        tracker.feed('B', False)
        self.assertEqual(tracker.feed('LCTRL', False)['captured'], ['CTRL', 'B'])

    def test_capture_side_specific_escape_cancel_and_backspace_assignment(self):
        tracker = hotkeys.ChordTracker()
        tracker.begin_capture(side_specific=True)
        tracker.feed('RCTRL', True)
        tracker.feed('BACKSPACE', True)
        tracker.feed('RCTRL', False)
        self.assertEqual(tracker.feed('BACKSPACE', False)['captured'], ['RCTRL', 'BACKSPACE'])
        tracker.begin_capture()
        tracker.feed('A', True)
        self.assertTrue(tracker.feed('ESC', True)['cancelled'])
        self.assertEqual(tracker.held_keys, ())
        self.assertIsNone(tracker.feed('A', False)['captured'])

    def test_reset_and_reconfiguration_discard_pending_state(self):
        tracker = hotkeys.ChordTracker({'power': 'CTRL+M'})
        tracker.feed('LCTRL', True)
        tracker.begin_capture()
        tracker.feed('A', True)
        tracker.reset()
        self.assertFalse(tracker.capture_active)
        self.assertIsNone(tracker.feed('A', False)['captured'])
        tracker.set_chords({'voice': 'ALT+V'})
        self.assertEqual(tracker.feed('M', True)['actions'], [])

    def test_semantic_collisions_include_generic_and_specific_modifiers(self):
        self.assertTrue(hotkeys.chords_conflict('CTRL+M', 'LCTRL+M'))
        self.assertTrue(hotkeys.chords_conflict('CTRL+M', 'LCTRL+RCTRL+M'))
        self.assertFalse(hotkeys.chords_conflict('LCTRL+M', 'RCTRL+M'))
        self.assertTrue(hotkeys.chords_conflict('CTRL+M', 'CTRL+ALT+M'))
        self.assertFalse(hotkeys.chords_conflict([], []))

    def test_subset_shortcuts_conflict_regardless_of_order_or_modifier_side(self):
        self.assertTrue(hotkeys.chords_conflict('CTRL+ALT+M', 'CTRL+ALT+M+X'))
        self.assertTrue(hotkeys.chords_conflict('CTRL+ALT+M+X', 'CTRL+ALT+M'))
        self.assertTrue(hotkeys.chords_conflict('RCTRL+M', 'CTRL+ALT+M+X'))
        self.assertTrue(hotkeys.chords_conflict('A+S+D', 'A+S+D+F'))
        self.assertFalse(hotkeys.chords_conflict('CTRL+ALT+M', 'CTRL+ALT+V'))

    def test_reconcile_lost_modifier_release_prevents_later_shortcut(self):
        keys = types.SimpleNamespace(KEY_LCONTROL=29, KEY_M=50, KEY_A=30)
        tracker = hotkeys.ChordTracker({'power': 'CTRL+M'}, keys)
        tracker.feed(29, True)
        queries = []
        def state(code):
            queries.append(code)
            return False
        self.assertTrue(tracker.reconcile(state, current_key=50))
        self.assertEqual(queries, [29])
        self.assertEqual(tracker.held_keys, ())
        self.assertEqual(tracker.feed(50, True)['actions'], [])

    def test_reconcile_cancels_capture_on_lost_key_up(self):
        keys = types.SimpleNamespace(KEY_LCONTROL=29, KEY_M=50)
        tracker = hotkeys.ChordTracker(keys_module=keys)
        tracker.begin_capture()
        tracker.feed(29, True)
        self.assertTrue(tracker.reconcile(lambda code: False, current_key=50))
        self.assertFalse(tracker.capture_active)
        self.assertIsNone(tracker.feed(29, False)['captured'])

    def test_reconcile_ignores_incoming_release_and_preserves_capture_peak(self):
        keys = types.SimpleNamespace(KEY_LCONTROL=29, KEY_M=50)
        tracker = hotkeys.ChordTracker(keys_module=keys)
        tracker.begin_capture()
        tracker.feed(29, True)
        tracker.feed(50, True)
        queries = []
        def state(code):
            queries.append(code)
            return code == 29
        self.assertFalse(tracker.reconcile(state, current_key=50))
        self.assertEqual(queries, [29])
        tracker.feed(50, False)
        self.assertFalse(tracker.reconcile(lambda code: False, current_key=29))
        self.assertEqual(tracker.feed(29, False)['captured'], ['CTRL', 'M'])

    def test_reconcile_query_failure_fails_closed_without_idle_queries(self):
        keys = types.SimpleNamespace(KEY_LCONTROL=29, KEY_M=50)
        tracker = hotkeys.ChordTracker({'power': 'CTRL+M'}, keys)
        def broken(code):
            raise RuntimeError('Native state query failed')
        self.assertFalse(tracker.reconcile(broken))
        tracker.feed(29, True)
        self.assertTrue(tracker.reconcile(broken, current_key=50))
        self.assertEqual(tracker.held_keys, ())


if __name__ == '__main__':
    unittest.main()
