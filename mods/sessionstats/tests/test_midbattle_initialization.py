# -*- coding: utf-8 -*-
"""Live observation can begin before an account service or mod is initialized."""
from __future__ import unicode_literals

import os
import unittest

import test_runtime as fixtures
from test_normalize import ARENA_ID, START, raw_result
from grz_session_stats import runtime


class MidbattleInitializationTests(unittest.TestCase):
    setUp = fixtures.RuntimeTests.__dict__['setUp']
    tearDown = fixtures.RuntimeTests.__dict__['tearDown']
    no_footer = fixtures.RuntimeTests.__dict__['no_footer']

    def enter_ongoing_battle(self):
        self.clock.value = START + 60
        self.api.battle = True
        self.api.context = {'arena_id': ARENA_ID, 'started_at': START,
                            'vehicle_id': 1, 'map_id': '17_map', 'mode': 'random'}

    def assert_observed_and_completed(self):
        service = self.mod.active_service
        for scope in ('launch', 'manual'):
            stats = service.snapshot()['scopes'][scope]['summary']
            self.assertEqual(stats['observed_battles'], 1)
            self.assertEqual(stats['missing_results'], 1)
        self.api.events.onBattleResultsReceived(True, raw_result(dbid=self.api.dbid))
        for scope in ('launch', 'manual'):
            self.assertEqual(service.snapshot()['scopes'][scope]['summary']['battles'], 1)
        self.assertEqual(self.mod._instance_session.snapshot()[0]['summary']['battles'], 1)
        sequence = service.store.sequence
        self.api.events.onAvatarReady()
        self.api.events.onBattleResultsReceived(True, raw_result(dbid=self.api.dbid))
        self.assertEqual(service.store.sequence, sequence)
        self.assertEqual(service._state['battles'][ARENA_ID]['started_at'], START)

    def test_mod_starts_during_an_ongoing_battle(self):
        self.mod.stop()
        self.enter_ongoing_battle()
        self.mod = runtime.Runtime(deferred_loading=False, api=self.api, data_dir=os.path.join(self.directory, 'fresh'),
                                   expected_table=fixtures.EXPECTED, now=self.clock,
                                   window=self.window, footer_installer=self.no_footer,
                                   installation_dir=self.directory)
        self.mod.start()
        self.assert_observed_and_completed()

    def test_account_service_is_first_created_during_an_ongoing_battle(self):
        self.enter_ongoing_battle()
        self.api.dbid = 8
        self.mod._installation_dir = self.directory
        self.api.events.onAvatarReady()
        self.assertEqual(self.mod.active_key, 'EU:8')
        self.assert_observed_and_completed()


if __name__ == '__main__':
    unittest.main()
