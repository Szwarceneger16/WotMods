# -*- coding: utf-8 -*-
"""Exercise paging through the native command bridge and the real ledgers."""
from __future__ import unicode_literals

import json
import shutil
import tempfile
import unittest

from test_core import Clock, EXPECTED, result
import test_runtime as fixtures
from grz_session_stats.core import StatsService
from grz_session_stats.runtime import Runtime
from grz_session_stats.sessions import InstallationSession


class NativePaginationTests(unittest.TestCase):
    inject_module = fixtures.NativeBindingTests.__dict__['inject_module']

    def setUp(self):
        fixtures.NativeBindingTests.__dict__['setUp'](self)
        self.directory = tempfile.mkdtemp(prefix='grz-native-pages-')
        self.clock = Clock(100)
        service = StatsService(self.directory, 'EU:7', 'launch', EXPECTED, self.clock)
        session = InstallationSession(self.directory, self.directory, 'launch', EXPECTED, self.clock)
        self.clock.value = 200
        for index in range(45):
            row = result(str(index), vehicle_id=index + 1, map_id=str(index))
            self.assertTrue(service.record_result(row))
            self.assertTrue(session.result('EU:7', row, allow_new=True))
        self.mod = Runtime(api=fixtures.FakeAPI(), now=self.clock, window=self.window)
        self.mod.running = True
        self.mod.active_key, self.mod.active_service = 'EU:7', service
        self.mod.services = {'EU:7': service}
        self.mod._instance_tab_enabled, self.mod._instance_session = True, session
        self.window._snapshot = self.mod.snapshot
        self.window._on_action = self.mod.on_action
        self.assertTrue(self.window.open())

    def tearDown(self):
        fixtures.NativeBindingTests.__dict__['tearDown'](self)
        shutil.rmtree(self.directory)

    def payload(self):
        return json.loads(self.window._model._payload)

    def command(self, scope='manual', group='battles', **updates):
        command = {'action': 'page', 'scope': scope, 'group': group, 'page': '1',
                   'account_key': 'EU:7', 'period_id': self.payload()['scopes'][scope]['period_id']}
        command.update(updates)
        return command

    def test_each_scope_and_group_publishes_next_and_previous_page(self):
        for scope in ('launch', 'manual', 'instance'):
            for group in ('battles', 'vehicles', 'maps'):
                before = self.payload()['scopes'][scope]
                identifiers = set(row['id'] for row in before[group])
                self.assertEqual(len(identifiers), 40)
                self.window._model.onAction(self.command(scope, group))
                after = self.payload()['scopes'][scope]
                self.assertEqual(after['pagination'][group]['page'], 1, (scope, group))
                self.assertEqual(len(after[group]), 5)
                self.assertFalse(identifiers.intersection(row['id'] for row in after[group]))
                self.assertEqual(after['summary'], before['summary'])
                self.window._model.onAction(self.command(scope, group, page='0'))
                restored = self.payload()['scopes'][scope]
                self.assertEqual(restored['pagination'][group]['page'], 0)
                self.assertEqual(restored[group], before[group])

    def test_invalid_account_period_and_page_are_rejected_through_native_bridge(self):
        for updates in ({'account_key': 'EU:8'}, {'period_id': 'expired'}, {'page': '-1'},
                        {'page': '1.5'}, {'group': 'invalid'}, {'action': 'unknown'}):
            self.window._model.onAction(self.command(**updates))
        self.assertEqual(self.mod.active_service._pages, {})
        self.assertEqual(self.payload()['scopes']['manual']['pagination']['battles']['page'], 0)

    def test_closed_window_cannot_page_its_replacement(self):
        command, old_model = self.command(), self.window._model
        self.window.close()
        self.assertTrue(self.window.open())
        old_model.onAction(command)
        self.assertEqual(self.mod.active_service._pages, {})
        self.window._model.onAction(command)
        self.assertEqual(self.payload()['scopes']['manual']['pagination']['battles']['page'], 1)

    def test_native_python2_byte_page_is_accepted_but_invalid_bytes_are_rejected(self):
        self.window._model.onAction(self.command(page=b'1'))
        self.assertEqual(self.payload()['scopes']['manual']['pagination']['battles']['page'],1)
        for value in [b'\xff', b'-1', b'1\n', b'1.5']:
            self.window._model.onAction(self.command(page=value))
        self.assertEqual(self.payload()['scopes']['manual']['pagination']['battles']['page'],1)

    def test_reset_invalidates_a_page_request_from_the_previous_period(self):
        command = self.command()
        self.window._model.onAction({'action': 'reset', 'scope': 'manual', 'account_key': 'EU:7'})
        self.window._model.onAction(command)
        scope = self.payload()['scopes']['manual']
        self.assertNotEqual(scope['period_id'], command['period_id'])
        self.assertEqual(scope['battles'], [])
        self.assertEqual(self.mod.active_service._pages, {})


if __name__ == '__main__':
    unittest.main()
