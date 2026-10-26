# -*- coding: utf-8 -*-
"""Appearance bridge retains independent activity and native recovery semantics."""
from __future__ import unicode_literals

import gc
import unittest
import weakref

import test_footer_activity as fixtures
from grz_session_stats import footer


class FooterAppearanceTests(unittest.TestCase):
    setUp = fixtures.FooterActivityTests.__dict__['setUp']
    tearDown = fixtures.FooterActivityTests.__dict__['tearDown']
    inject_module = fixtures.FooterActivityTests.__dict__['inject_module']
    fake_inject = fixtures.FooterActivityTests.__dict__['fake_inject']
    install = fixtures.FooterActivityTests.__dict__['install']
    attach = fixtures.FooterActivityTests.__dict__['attach']
    state = fixtures.FooterActivityTests.__dict__['state']

    def appearance(self, commands):
        return commands.props[1][1]

    def test_configuration_loaded_before_footer_is_replayed_to_new_native_child(self):
        handle, lobby_class = self.install()
        css = '.grz-session-footer-bar { background-color:#8899aa; }'
        handle.set_appearance(css)
        handle.set_activity(3, False)
        lobby, child, commands = self.attach(lobby_class)
        self.assertEqual([p[0] for p in commands.props], ['activity', 'appearance'])
        self.assertEqual(self.appearance(commands), css)
        self.assertEqual(self.state(commands), {'pending': 3, 'processing': False})
        commands.onAction({'action': 'open'})
        self.assertEqual(self.opened, [True])
        self.assertEqual(lobby.original_calls, 1)

    def test_live_appearance_changes_and_clearing_do_not_reset_activity(self):
        handle, lobby_class = self.install()
        lobby, child, commands = self.attach(lobby_class)
        writes = []
        original = commands._setString

        def recorded(index, value):
            writes.append((index, value))
            original(index, value)

        commands._setString = recorded
        handle.set_activity(2, True)
        css = '.grz-session-footer-button { opacity:0.7; }'
        self.assertTrue(handle.set_appearance(css))
        self.assertFalse(handle.set_appearance(css))
        self.assertEqual([index for index, value in writes], [0, 1])
        self.assertEqual(self.state(commands), {'pending': 2, 'processing': True})
        self.assertTrue(handle.set_appearance(''))
        self.assertEqual(self.appearance(commands), '')
        self.assertEqual(self.state(commands), {'pending': 2, 'processing': True})

    def test_one_failed_native_appearance_write_does_not_block_activity_or_other_children(self):
        handle, lobby_class = self.install()
        bad_lobby, bad_child, bad_model = self.attach(lobby_class)
        good_lobby, good_child, good_model = self.attach(lobby_class)
        original = bad_model._setString

        def rejected(index, value):
            if index == 1:
                raise TypeError('injected native appearance failure')
            original(index, value)

        bad_model._setString = rejected
        css = '.grz-session-footer-rating { color:#aabbcc; }'
        handle.set_appearance(css)
        handle.set_activity(4, True)
        self.assertEqual(self.appearance(good_model), css)
        self.assertEqual(self.appearance(bad_model), '')
        self.assertEqual(self.state(bad_model), {'pending': 4, 'processing': True})
        bad_model._setString = original
        self.assertFalse(handle.set_appearance(css))
        self.assertEqual(self.appearance(bad_model), css)
        self.assertEqual(self.state(good_model), {'pending': 4, 'processing': True})

    def test_recreated_child_receives_latest_configuration_and_detached_child_is_untouched(self):
        handle, lobby_class = self.install()
        old_lobby, old_child, old_model = self.attach(lobby_class)
        handle.set_appearance('.grz-session-footer-button { opacity:0.6; }')
        before = self.appearance(old_model)
        old_lobby._unregisterChild(old_child.uniqueID, True)
        fresh = '.grz-session-footer-button { opacity:0.9; }'
        handle.set_appearance(fresh)
        new_lobby, new_child, new_model = self.attach(lobby_class)
        self.assertEqual(self.appearance(old_model), before)
        self.assertEqual(self.appearance(new_model), fresh)
        self.assertEqual(len(handle._children), 1)

    def test_uninstall_prevents_appearance_or_retained_commands_from_reviving_ui(self):
        handle, lobby_class = self.install()
        lobby, child, commands = self.attach(lobby_class)
        handle.set_appearance('.grz-session-footer-button { opacity:0.8; }')
        before = self.appearance(commands)
        handle.uninstall()
        self.assertFalse(handle.set_appearance(''))
        self.assertEqual(self.appearance(commands), before)
        self.assertEqual(lobby.children, {})
        commands.onAction({'action': 'open'})
        self.assertEqual(self.opened, [])

    def test_invalid_bridge_payload_clears_override_but_preserves_usable_button_and_activity(self):
        handle, lobby_class = self.install()
        lobby, child, commands = self.attach(lobby_class)
        handle.set_activity(1, False)
        for invalid in (None, True, 7, {}, [], 'x' * (footer.MAX_APPEARANCE_CHARS + 1),
                        '<style>body{color:red}</style>', '.x{color:red}\x00'):
            handle.set_appearance('.grz-session-footer-button { opacity:0.8; }')
            handle.set_appearance(invalid)
            self.assertEqual(self.appearance(commands), '')
            self.assertEqual(self.state(commands), {'pending': 1, 'processing': False})
        commands.onAction({'action': 'open'})
        self.assertEqual(self.opened, [True])

    def test_parent_lookup_error_is_isolated_and_same_configuration_can_be_retried(self):
        handle, lobby_class = self.install()
        first_lobby, first_child, first_model = self.attach(lobby_class)
        other_lobby, other_child, other_model = self.attach(lobby_class)
        original = first_lobby.getChildView

        def rejected(*args):
            raise RuntimeError('injected parent lookup failure')

        first_lobby.getChildView = rejected
        css = '.grz-session-footer-rating { color:#112233; }'
        handle.set_appearance(css)
        self.assertEqual(self.appearance(other_model), css)
        first_lobby.getChildView = original
        handle.set_appearance(css)
        self.assertEqual(self.appearance(first_model), css)
        self.assertEqual(len(handle._children), 2)

    def test_configuration_does_not_retain_destroyed_footer_objects(self):
        handle, lobby_class = self.install()
        lobby, child, commands = self.attach(lobby_class)
        lobby_ref, child_ref = weakref.ref(lobby), weakref.ref(child)
        del lobby, child, commands
        gc.collect()
        self.assertIsNone(lobby_ref())
        self.assertIsNone(child_ref())
        handle.set_appearance('.grz-session-footer-rating { color:#112233; }')
        self.assertEqual(handle._children, [])


if __name__ == '__main__':
    unittest.main()
