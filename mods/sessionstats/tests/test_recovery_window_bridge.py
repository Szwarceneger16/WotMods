# -*- coding: utf-8 -*-
"""Recovery commands must cross the same owned native bridge as other actions."""
from __future__ import unicode_literals

import unittest

import test_runtime as fixtures


class RecoveryWindowBridgeTests(unittest.TestCase):
    setUp = fixtures.NativeBindingTests.__dict__['setUp']
    tearDown = fixtures.NativeBindingTests.__dict__['tearDown']
    inject_module = fixtures.NativeBindingTests.__dict__['inject_module']

    def test_retry_result_reaches_runtime_only_from_the_current_open_window(self):
        self.assertTrue(self.window.open())
        generation = self.window._generation
        command = {'action': 'retry_result', 'account_key': 'EU:1', 'arena_id': '42'}
        self.window._handle_action(generation, command)
        self.assertEqual(self.actions, [command])
        self.window.close()
        self.window._handle_action(generation, command)
        self.assertEqual(self.actions, [command])
        self.assertTrue(self.window.open())
        self.window._handle_action(generation, command)
        self.assertEqual(self.actions, [command])
        self.window._handle_action(self.window._generation, command)
        self.assertEqual(self.actions, [command, command])


if __name__ == '__main__':
    unittest.main()
