# -*- coding: utf-8 -*-
"""Footer activity bridge with the verified native model/transaction contract."""
from __future__ import unicode_literals

import gc
import json
import unittest
import weakref

import test_runtime as fixtures
from grz_session_stats import footer


class FooterActivityTests(unittest.TestCase):
    setUp = fixtures.NativeBindingTests.__dict__['setUp']
    tearDown = fixtures.NativeBindingTests.__dict__['tearDown']
    inject_module = fixtures.NativeBindingTests.__dict__['inject_module']
    fake_inject = fixtures.NativeBindingTests.__dict__['fake_inject']

    def install(self):
        class Component(self.component):
            # ViewComponent -> ViewImpl -> Wulf View supplies this method.
            def getViewModel(self):
                return self.model

        class LobbyFooter(Component):
            pass

        self.inject_module('gui.impl.pub.view_component', ViewComponent=Component)
        self.inject_module('openwg_gameface', gf_mod_inject=self.fake_inject)
        self.inject_module('gui.impl.lobby.page.lobby_footer', LobbyFooter=LobbyFooter)
        self.opened = []
        return footer.install(lambda: self.opened.append(True)), LobbyFooter

    def attach(self, lobby_class):
        lobby = lobby_class()
        lobby._onLoading()
        child = lobby.getChildView(footer.POSITION_ID)
        commands = child.model.props[1][1]
        return lobby, child, commands

    def state(self, commands):
        return json.loads(commands.props[0][1])

    def test_language_updates_preserve_activity_and_survive_footer_recreation(self):
        from grz_session_stats.localization import Localizer
        handle, lobby_class = self.install()
        handle.set_activity(3, True)
        handle.set_language(Localizer('ru').footer_labels())
        lobby, child, commands = self.attach(lobby_class)
        payload = self.state(commands)
        self.assertEqual((payload['pending'], payload['processing']), (3, True))
        self.assertEqual(payload['labels']['footer.idle'], Localizer('ru').text('footer.idle'))
        handle.set_language(Localizer('uk').footer_labels())
        self.assertEqual(self.state(commands)['labels'], Localizer('uk').footer_labels())
        handle.set_activity(0, False)
        next_lobby, next_child, next_commands = self.attach(lobby_class)
        self.assertEqual(self.state(next_commands)['labels'], self.state(commands)['labels'])
        self.assertEqual(self.state(next_commands)['pending'], 0)

    def test_pending_state_before_footer_exists_reaches_new_child(self):
        handle, lobby_class = self.install()
        handle.set_activity(3, False)
        lobby, child, commands = self.attach(lobby_class)
        self.assertEqual(commands.props[0][0], 'activity')
        self.assertEqual(self.state(commands), {'pending': 3, 'processing': False})
        self.assertEqual([p[0] for p in child.model.props], ['ModInjectModel', 'grzSessionFooter'])
        commands.onAction({'action': 'open'})
        self.assertEqual(self.opened, [True])
        self.assertEqual(lobby.original_calls, 1)

    def test_transitions_commit_once_per_changed_state_and_keep_processing_only(self):
        handle, lobby_class = self.install()
        lobby, child, commands = self.attach(lobby_class)
        writes = []
        original = commands._setString

        def counted(index, value):
            writes.append(value)
            original(index, value)

        commands._setString = counted
        self.assertEqual(self.state(commands), {'pending': 0, 'processing': False})
        self.assertTrue(handle.set_activity(2, False))
        self.assertFalse(handle.set_activity(2, False))
        self.assertEqual(len(writes), 1)
        handle.set_activity(2, True)
        handle.set_activity(0, True)
        self.assertEqual(self.state(commands), {'pending': 0, 'processing': True})
        handle.set_activity(0, False)
        self.assertEqual(self.state(commands), {'pending': 0, 'processing': False})
        self.assertEqual(len(writes), 4)

    def test_recreated_footer_gets_latest_state_and_detached_child_is_not_updated(self):
        handle, lobby_class = self.install()
        old_lobby, old_child, old_commands = self.attach(lobby_class)
        handle.set_activity(2, False)
        old_lobby._unregisterChild(old_child.uniqueID, True)
        handle.set_activity(1, True)
        new_lobby, new_child, new_commands = self.attach(lobby_class)
        self.assertEqual(self.state(new_commands), {'pending': 1, 'processing': True})
        self.assertEqual(self.state(old_commands), {'pending': 2, 'processing': False})
        self.assertEqual(len(handle._children), 1)
        self.assertIs(new_lobby.getChildView(footer.POSITION_ID), new_child)

    def test_failed_native_write_does_not_stop_other_child_and_can_retry_same_state(self):
        handle, lobby_class = self.install()
        broken_lobby, broken_child, broken_model = self.attach(lobby_class)
        good_lobby, good_child, good_model = self.attach(lobby_class)
        original = broken_model._setString

        def rejected(*args):
            raise TypeError('injected changed native property API')

        broken_model._setString = rejected
        handle.set_activity(4, True)
        self.assertEqual(self.state(good_model), {'pending': 4, 'processing': True})
        self.assertEqual(self.state(broken_model), {'pending': 0, 'processing': False})
        broken_model._setString = original
        self.assertFalse(handle.set_activity(4, True))
        self.assertEqual(self.state(broken_model), {'pending': 4, 'processing': True})
        self.assertIs(broken_lobby.getChildView(footer.POSITION_ID), broken_child)
        self.assertIs(good_lobby.getChildView(footer.POSITION_ID), good_child)

    def test_parent_query_failure_is_isolated_and_retryable(self):
        handle, lobby_class = self.install()
        first_lobby, first_child, first_model = self.attach(lobby_class)
        other_lobby, other_child, other_model = self.attach(lobby_class)
        original = first_lobby.getChildView

        def rejected(*args):
            raise RuntimeError('injected parent lifecycle failure')

        first_lobby.getChildView = rejected
        handle.set_activity(7, False)
        self.assertEqual(self.state(other_model), {'pending': 7, 'processing': False})
        first_lobby.getChildView = original
        handle.set_activity(7, False)
        self.assertEqual(self.state(first_model), {'pending': 7, 'processing': False})
        self.assertEqual(len(handle._children), 2)

    def test_weak_children_do_not_retain_destroyed_footers(self):
        handle, lobby_class = self.install()
        lobby, child, commands = self.attach(lobby_class)
        lobby_ref = weakref.ref(lobby)
        child_ref = weakref.ref(child)
        del lobby, child, commands
        gc.collect()
        self.assertIsNone(lobby_ref())
        self.assertIsNone(child_ref())
        handle.set_activity(1, False)
        self.assertEqual(handle._children, [])

    def test_uninstall_makes_activity_and_retained_commands_inert(self):
        handle, lobby_class = self.install()
        lobby, child, commands = self.attach(lobby_class)
        handle.set_activity(1, True)
        before = self.state(commands)
        handle.uninstall()
        self.assertFalse(handle.set_activity(9, True))
        self.assertEqual(self.state(commands), before)
        self.assertEqual(lobby.children, {})
        commands.onAction({'action': 'open'})
        self.assertEqual(self.opened, [])

    def test_failed_child_removal_is_retained_and_retried_without_reviving_commands(self):
        handle, lobby_class = self.install()
        lobby, child, commands = self.attach(lobby_class)
        healthy, healthy_child, unused_commands = self.attach(lobby_class)
        original = lobby._unregisterChild

        def rejected(*args):
            raise RuntimeError('native cleanup temporarily unavailable')

        lobby._unregisterChild = rejected
        self.addCleanup(setattr, lobby, '_unregisterChild', original)
        self.assertFalse(handle.uninstall())
        self.assertIs(footer._installed, handle)
        self.assertEqual(len(handle._children), 1)
        self.assertIs(lobby.getChildView(footer.POSITION_ID), child)
        self.assertIsNone(healthy.getChildView(footer.POSITION_ID))
        commands.onAction({'action': 'open'})
        self.assertEqual(self.opened, [])
        self.assertIsNone(footer.install(lambda: self.opened.append('replacement')))
        self.assertIs(footer._installed, handle)
        lobby._unregisterChild = original
        replacement = footer.install(lambda: self.opened.append('replacement'))
        self.assertIsNotNone(replacement)
        self.assertIsNot(replacement, handle)
        self.assertIsNone(lobby.getChildView(footer.POSITION_ID))
        lobby._onLoading()
        current = lobby.getChildView(footer.POSITION_ID)
        current.model.props[1][1].onAction({'action': 'open'})
        commands.onAction({'action': 'open'})
        self.assertEqual(self.opened, ['replacement'])

    def test_silent_child_removal_failure_cannot_be_mistaken_for_release(self):
        handle, lobby_class = self.install()
        lobby, child, unused_commands = self.attach(lobby_class)
        original = lobby._unregisterChild
        lobby._unregisterChild = lambda *args: None
        self.addCleanup(setattr, lobby, '_unregisterChild', original)
        self.assertFalse(handle.uninstall())
        self.assertEqual(len(handle._children), 1)
        self.assertIs(footer._installed, handle)
        lobby._unregisterChild = original
        self.assertTrue(handle.uninstall())
        self.assertEqual(handle._children, [])
        self.assertIsNone(footer._installed)

    def test_partial_child_registration_keeps_failed_rollback_owned(self):
        handle, lobby_class = self.install()
        lobby = lobby_class()
        original_register = lobby._registerChild
        original_remove = lobby._unregisterChild

        def partial(position, child):
            original_register(position, child)
            raise RuntimeError('registered before failing')

        def rejected(*args):
            raise RuntimeError('rollback temporarily unavailable')

        lobby._registerChild = partial
        lobby._unregisterChild = rejected
        self.addCleanup(setattr, lobby, '_unregisterChild', original_remove)
        lobby._onLoading()
        child = lobby.getChildView(footer.POSITION_ID)
        self.assertIsNotNone(child)
        self.assertEqual(len(handle._children), 1)
        self.assertFalse(handle.uninstall())
        lobby._unregisterChild = original_remove
        self.assertTrue(handle.uninstall())
        self.assertIsNone(lobby.getChildView(footer.POSITION_ID))

    def test_failed_cleanup_never_removes_a_replacement_owned_by_another_mod(self):
        handle, lobby_class = self.install()
        lobby, child, unused_commands = self.attach(lobby_class)
        original = lobby._unregisterChild
        lobby._unregisterChild = lambda *args: None
        self.assertFalse(handle.uninstall())
        foreign = self.component()
        lobby.children[footer.POSITION_ID] = foreign
        attempts = []
        lobby._unregisterChild = lambda *args: attempts.append(args)
        self.assertTrue(handle.uninstall())
        self.assertEqual(attempts, [])
        self.assertIs(lobby.getChildView(footer.POSITION_ID), foreign)
        lobby._unregisterChild = original

    def test_invalid_activity_counts_cannot_create_false_pending_work(self):
        handle, lobby_class = self.install()
        lobby, child, commands = self.attach(lobby_class)
        for value in (True, False, -1, '3', None, 2.5, float('nan')):
            handle.set_activity(value, 'false')
            self.assertEqual(self.state(commands), {'pending': 0, 'processing': False})
        handle.set_activity(1234, True)
        self.assertEqual(self.state(commands), {'pending': 1234, 'processing': True})


if __name__ == '__main__':
    unittest.main()
