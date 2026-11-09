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

    def test_unrelated_held_key_does_not_block_activation_or_rearm_latch(self):
        tracker = hotkeys.ChordTracker({'power': 'CTRL+M'})
        tracker.feed('A', True)
        tracker.feed('LCTRL', True)
        self.assertEqual(tracker.feed('M', True)['actions'], ['power'])
        self.assertEqual(tracker.feed('A', False)['actions'], [])
        self.assertEqual(tracker.feed('A', True)['actions'], [])
        tracker.feed('M', False)
        self.assertEqual(tracker.feed('M', True)['actions'], ['power'])

    def test_u_and_i_work_while_driving_with_ordinary_keys_held(self):
        for driving_keys in (('W',), ('W', 'A'), ('UP',), ('UP', 'LEFT'), ('Q', 'E')):
            with self.subTest(driving_keys=driving_keys):
                tracker = hotkeys.ChordTracker({'toggle_mod': ['U'], 'toggle_voice': ['I']})
                for key in driving_keys:
                    self.assertEqual(tracker.feed(key, True)['actions'], [])
                self.assertEqual(tracker.feed('U', True)['actions'], ['toggle_mod'])
                self.assertEqual(tracker.feed('I', True)['actions'], ['toggle_voice'])
                self.assertEqual(tracker.feed('U', True, repeated=True)['actions'], [])
                tracker.feed('U', False)
                self.assertEqual(tracker.feed('U', True)['actions'], ['toggle_mod'])
                self.assertTrue(set(driving_keys).issubset(tracker.held_keys))

    def test_extra_modifiers_block_plain_shortcut_until_required_key_is_pressed_again(self):
        for modifier in ('CTRL', 'LCTRL', 'RCTRL', 'ALT', 'LALT', 'RALT',
                         'SHIFT', 'LSHIFT', 'RSHIFT', 'LWIN', 'RWIN'):
            with self.subTest(modifier=modifier):
                tracker = hotkeys.ChordTracker({'toggle_mod': ['U']})
                tracker.feed(modifier, True)
                tracker.feed('W', True)
                self.assertEqual(tracker.feed('U', True)['actions'], [])
                self.assertEqual(tracker.feed(modifier, False)['actions'], [])
                self.assertEqual(tracker.feed('A', True)['actions'], [])
                self.assertEqual(tracker.feed('A', False)['actions'], [])
                self.assertEqual(tracker.feed('W', False)['actions'], [])
                tracker.feed('U', False)
                self.assertEqual(tracker.feed('U', True)['actions'], ['toggle_mod'])

    def test_movement_keydown_cannot_activate_an_already_held_unlatched_shortcut(self):
        tracker = hotkeys.ChordTracker({'toggle_mod': ['U']})
        tracker.feed('LSHIFT', True)
        self.assertEqual(tracker.feed('U', True)['actions'], [])
        tracker.feed('LSHIFT', False)
        self.assertEqual(tracker.feed('W', True)['actions'], [])
        self.assertEqual(tracker.feed('UP', True)['actions'], [])
        self.assertEqual(tracker.feed('W', False)['actions'], [])
        tracker.feed('U', False)
        self.assertEqual(tracker.feed('U', True)['actions'], ['toggle_mod'])

    def test_required_generic_modifier_can_complete_chord_while_driving(self):
        tracker = hotkeys.ChordTracker({'toggle_mod': ['CTRL', 'U']})
        tracker.feed('W', True)
        self.assertEqual(tracker.feed('U', True)['actions'], [])
        self.assertEqual(tracker.feed('RCTRL', True)['actions'], ['toggle_mod'])
        self.assertEqual(tracker.feed('A', True)['actions'], [])
        self.assertEqual(tracker.feed('RCTRL', False)['actions'], [])
        self.assertEqual(tracker.feed('LCTRL', True)['actions'], ['toggle_mod'])

    def test_generic_modifier_latch_survives_one_side_releasing_while_driving(self):
        tracker = hotkeys.ChordTracker({'toggle_mod': ['CTRL', 'U']})
        tracker.feed('W', True)
        tracker.feed('LCTRL', True)
        self.assertEqual(tracker.feed('U', True)['actions'], ['toggle_mod'])
        self.assertEqual(tracker.feed('RCTRL', True)['actions'], [])
        self.assertEqual(tracker.feed('LCTRL', False)['actions'], [])
        self.assertEqual(tracker.feed('A', True)['actions'], [])
        self.assertEqual(tracker.feed('LCTRL', True)['actions'], [])
        tracker.feed('U', False)
        self.assertEqual(tracker.feed('U', True)['actions'], ['toggle_mod'])

    def test_extra_modifier_sides_and_windows_keys_remain_strict_while_driving(self):
        for extra in ('RCTRL', 'LALT', 'LSHIFT', 'LWIN', 'RWIN'):
            with self.subTest(extra=extra):
                tracker = hotkeys.ChordTracker({'toggle_mod': ['LCTRL', 'U']})
                tracker.feed('LCTRL', True)
                tracker.feed('W', True)
                tracker.feed(extra, True)
                self.assertEqual(tracker.feed('U', True)['actions'], [])
                self.assertEqual(tracker.feed(extra, False)['actions'], [])
                self.assertEqual(tracker.feed('D', True)['actions'], [])
                tracker.feed('U', False)
                self.assertEqual(tracker.feed('U', True)['actions'], ['toggle_mod'])

    def test_explicit_movement_binding_requires_its_keys_in_either_order(self):
        tracker = hotkeys.ChordTracker({'toggle_mod': ['W', 'U']})
        tracker.feed('UP', True)
        self.assertEqual(tracker.feed('U', True)['actions'], [])
        self.assertEqual(tracker.feed('W', True)['actions'], ['toggle_mod'])
        tracker.feed('W', False)
        self.assertEqual(tracker.feed('A', True)['actions'], [])
        self.assertEqual(tracker.feed('W', True)['actions'], ['toggle_mod'])
        tracker.reset()
        self.assertEqual(tracker.feed('W', True)['actions'], [])
        self.assertEqual(tracker.feed('U', True)['actions'], ['toggle_mod'])

    def test_explicit_four_key_binding_keeps_all_members_with_other_driving_keys(self):
        tracker = hotkeys.ChordTracker({'toggle_voice': ['W', 'A', 'U', 'I']})
        tracker.feed('UP', True)
        tracker.feed('E', True)
        for key in ('W', 'U', 'I'):
            self.assertEqual(tracker.feed(key, True)['actions'], [])
        self.assertEqual(tracker.feed('A', True)['actions'], ['toggle_voice'])
        tracker.feed('I', False)
        self.assertEqual(tracker.feed('D', True)['actions'], [])
        self.assertEqual(tracker.feed('I', True)['actions'], ['toggle_voice'])

    def test_recording_keeps_movement_and_all_other_chosen_keys(self):
        tracker = hotkeys.ChordTracker()
        tracker.begin_capture(side_specific=True)
        for key in ('W', 'A', 'U', 'I'):
            result = tracker.feed(key, True)
            self.assertEqual(result['actions'], [])
            self.assertIsNone(result['captured'])
        self.assertEqual(tracker.held_keys, ('A', 'I', 'U', 'W'))
        for key in ('W', 'A', 'U'):
            self.assertIsNone(tracker.feed(key, False)['captured'])
        captured = tracker.feed('I', False)['captured']
        self.assertEqual(captured, ['A', 'I', 'U', 'W'])
        self.assertEqual(hotkeys.normalize_chord(captured), captured)
        self.assertTrue(hotkeys.chords_conflict(['U'], captured))

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

    def modifier_keys(self):
        return types.SimpleNamespace(KEY_LCONTROL=29, KEY_RCONTROL=157,
                                     KEY_LALT=56, KEY_RALT=184,
                                     KEY_LSHIFT=42, KEY_RSHIFT=54,
                                     KEY_LWIN=219, KEY_RWIN=220,
                                     KEY_M=50, KEY_A=30, KEY_W=17)

    def test_reconcile_recovers_unobserved_modifiers_after_blocked_reset(self):
        keys = self.modifier_keys()
        for code, name in ((29, 'LCTRL'), (157, 'RCTRL'), (56, 'LALT'), (184, 'RALT'),
                           (42, 'LSHIFT'), (54, 'RSHIFT'), (219, 'LWIN'), (220, 'RWIN')):
            with self.subTest(modifier=name):
                tracker = hotkeys.ChordTracker({'power': ['M']}, keys)
                tracker.feed(code, True, blocked=True)
                self.assertEqual(tracker.held_keys, ())
                self.assertFalse(tracker.reconcile(lambda native: native == code, current_key=50))
                self.assertEqual(tracker.held_keys, (name,))
                self.assertEqual(tracker.feed(50, True)['actions'], [])
                # Native state may already report this incoming release; the
                # event owns removing the current modifier from held state.
                self.assertFalse(tracker.reconcile(lambda native: native == 50, current_key=code))
                self.assertEqual(tracker.feed(code, False)['actions'], [])
                tracker.feed(50, False)
                tracker.reconcile(lambda native: False, current_key=50)
                self.assertEqual(tracker.feed(50, True)['actions'], ['power'])
                self.assertEqual(tracker.feed(50, True, repeated=True)['actions'], [])

    def test_reconcile_recovers_required_generic_and_side_specific_modifiers(self):
        keys = self.modifier_keys()
        for chord in (['CTRL', 'M'], ['LCTRL', 'M']):
            with self.subTest(chord=chord):
                tracker = hotkeys.ChordTracker({'power': chord}, keys)
                tracker.feed(29, True, blocked=True)
                self.assertFalse(tracker.reconcile(lambda code: code == 29, current_key=50))
                self.assertEqual(tracker.feed(50, True)['actions'], ['power'])
                tracker.reset()
                self.assertFalse(tracker.reconcile(lambda code: code in (29, 157), current_key=50))
                expected = ['power'] if chord[0] == 'CTRL' else []
                self.assertEqual(tracker.feed(50, True)['actions'], expected)

    def test_reconcile_stale_ordinary_key_retains_fresh_unobserved_ctrl(self):
        keys = self.modifier_keys()
        tracker = hotkeys.ChordTracker({'power': ['M']}, keys)
        tracker.feed(30, True)
        self.assertTrue(tracker.reconcile(lambda code: code == 29, current_key=50))
        self.assertEqual(tracker.held_keys, ('LCTRL',))
        self.assertEqual(tracker.feed(50, True)['actions'], [])
        tracker = hotkeys.ChordTracker({'power': ['CTRL', 'M']}, keys)
        tracker.feed(30, True)
        self.assertTrue(tracker.reconcile(lambda code: code == 29, current_key=50))
        self.assertEqual(tracker.feed(50, True)['actions'], ['power'])

    def test_reconcile_excludes_current_modifier_edge_and_preserves_latches(self):
        keys = self.modifier_keys()
        tracker = hotkeys.ChordTracker({'power': ['CTRL', 'M']}, keys)
        tracker.feed(50, True)
        queries = []
        def state(code):
            queries.append(code)
            if code == 29:
                raise AssertionError('incoming modifier must not be queried')
            return code == 50
        self.assertFalse(tracker.reconcile(state, current_key=29))
        self.assertNotIn(29, queries)
        self.assertEqual(tracker.feed(29, True)['actions'], ['power'])
        queries[:] = []
        self.assertFalse(tracker.reconcile(state, current_key=29))
        self.assertEqual(tracker.held_keys, ('LCTRL', 'M'))
        self.assertEqual(tracker.feed(29, False)['actions'], [])
        self.assertNotIn(29, queries)
        self.assertEqual(tracker.held_keys, ('M',))
        self.assertFalse(tracker.reconcile(state, current_key=29))
        self.assertEqual(tracker.feed(29, True)['actions'], ['power'])

    def test_reconcile_omits_aggregate_alias_when_physical_sides_exist(self):
        keys = types.SimpleNamespace(KEY_CONTROL=17, KEY_LCONTROL=29,
                                     KEY_RCONTROL=157, KEY_M=50)
        tracker = hotkeys.ChordTracker({'power': ['LCTRL', 'M']}, keys)
        queries = []
        def state(code):
            queries.append(code)
            if code == 17:
                raise AssertionError('aggregate alias must not be queried')
            return code == 29
        self.assertFalse(tracker.reconcile(state, current_key=50))
        self.assertEqual(set(queries), {29, 157})
        self.assertEqual(tracker.held_keys, ('LCTRL',))
        self.assertEqual(tracker.feed(50, True)['actions'], ['power'])
        # An incoming aggregate edge must not indirectly query its physical
        # sides either; that edge is not yet reflected in tracked state.
        tracker = hotkeys.ChordTracker({'power': ['CTRL', 'M']}, keys)
        tracker.feed(50, True)
        queries[:] = []
        def current_state(code):
            queries.append(code)
            if code in (17, 29, 157):
                raise AssertionError('incoming family must not be queried')
            return code == 50
        self.assertFalse(tracker.reconcile(current_state, current_key=17))
        self.assertEqual(queries, [50])
        self.assertEqual(tracker.feed(17, True)['actions'], ['power'])

    def test_reconcile_does_not_hydrate_unrecorded_modifiers_during_capture(self):
        keys = types.SimpleNamespace(KEY_LCONTROL=29, KEY_M=50)
        tracker = hotkeys.ChordTracker(keys_module=keys)
        tracker.begin_capture(side_specific=True)
        queries = []
        def state(code):
            queries.append(code)
            return code == 29
        self.assertFalse(tracker.reconcile(state, current_key=50))
        tracker.feed(50, True)
        self.assertFalse(tracker.reconcile(state, current_key=50))
        self.assertEqual(tracker.feed(50, False)['captured'], ['M'])
        self.assertEqual(queries, [])

    def test_reconcile_movement_remains_held_while_modifiers_are_refreshed(self):
        keys = self.modifier_keys()
        tracker = hotkeys.ChordTracker({'power': ['W', 'M']}, keys)
        tracker.feed(17, True)
        self.assertFalse(tracker.reconcile(lambda code: code == 17, current_key=50))
        self.assertEqual(tracker.held_keys, ('W',))
        self.assertEqual(tracker.feed(50, True)['actions'], ['power'])

    def test_reconcile_query_failure_aborts_normal_dispatch_even_when_empty(self):
        keys = types.SimpleNamespace(KEY_LCONTROL=29, KEY_M=50)
        tracker = hotkeys.ChordTracker({'power': ['M']}, keys)
        def broken(code):
            raise RuntimeError('Native state query failed')
        for state in (None, broken):
            with self.subTest(state=state):
                with self.assertRaises(RuntimeError):
                    tracker.reconcile(state, current_key=50)
                self.assertEqual(tracker.held_keys, ())
                tracker.feed(29, True)
                with self.assertRaises(RuntimeError):
                    tracker.reconcile(state, current_key=50)
                self.assertEqual(tracker.held_keys, ())
        self.assertFalse(tracker.reconcile(lambda code: False, current_key=50))
        self.assertEqual(tracker.feed(50, True)['actions'], ['power'])

    def test_reconcile_capture_query_failure_returns_cancelled_reset(self):
        keys = types.SimpleNamespace(KEY_LCONTROL=29, KEY_M=50)
        tracker = hotkeys.ChordTracker(keys_module=keys)
        def broken(code):
            raise RuntimeError('Native state query failed')
        for state in (None, broken):
            with self.subTest(state=state):
                tracker.begin_capture()
                tracker.feed(29, True)
                self.assertTrue(tracker.reconcile(state, current_key=50))
                self.assertFalse(tracker.capture_active)
                self.assertEqual(tracker.held_keys, ())
                self.assertIsNone(tracker.feed(29, False)['captured'])


if __name__ == '__main__':
    unittest.main()
