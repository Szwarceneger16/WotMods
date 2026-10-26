# -*- coding: utf-8 -*-
"""A restored incomplete ledger is not live result activity in a new client."""
from __future__ import unicode_literals

import copy
import unittest

import test_runtime_health as fixtures
from test_normalize import raw_result, ARENA_ID, START
from grz_session_stats import runtime


class BacklogActivityTests(unittest.TestCase):
    setUp = fixtures.RuntimeHealthTests.__dict__['setUp']
    tearDown = fixtures.RuntimeHealthTests.__dict__['tearDown']
    new_runtime = fixtures.RuntimeHealthTests.__dict__['new_runtime']
    enter_battle = fixtures.RuntimeHealthTests.__dict__['enter_battle']
    garage = fixtures.RuntimeHealthTests.__dict__['garage']
    tick = fixtures.RuntimeHealthTests.__dict__['tick']
    summary = fixtures.RuntimeHealthTests.__dict__['summary']

    def restart_in_garage(self):
        self.mod.stop()
        self.api.battle = False
        self.clock.value += 86400
        self.footer = fixtures.ActivityFooter()
        previous_launch = runtime.LAUNCH_ID
        try:
            runtime.LAUNCH_ID = previous_launch + '-new-client'
            self.mod = self.new_runtime()
        finally:
            runtime.LAUNCH_ID = previous_launch

    def test_no_battle_after_restart_keeps_spinner_idle_and_history_intact(self):
        self.enter_battle()
        self.garage()
        before = copy.deepcopy(self.mod.active_service._state['battles'])
        manual_id = self.mod.active_service._state['current_manual_id']
        self.restart_in_garage()
        self.assertEqual(self.footer.states[-1], (0, False))
        self.assertEqual(self.mod.active_service._state['battles'], before)
        self.assertEqual(self.mod.active_service._state['current_manual_id'], manual_id)
        snapshot = self.mod.snapshot()
        self.assertEqual(snapshot['scopes']['launch']['pending'], 0)
        self.assertEqual(snapshot['scopes']['manual']['pending'], 1)
        self.assertTrue(any('Incomplete earlier battle results: 1.' in warning
                            for warning in snapshot['warnings']))

    def test_background_cache_not_ready_cannot_restart_historical_spinner(self):
        self.enter_battle()
        self.garage()
        self.restart_in_garage()
        self.footer.states = []
        for unused in range(3):
            self.tick(seconds=300)
            arena_id, callback = self.api.pending_callbacks.pop()
            self.assertEqual(arena_id, ARENA_ID)
            callback(-1, None)
        self.assertTrue(self.footer.states)
        self.assertTrue(all(state == (0, False) for state in self.footer.states))
        self.assertEqual(self.mod.active_service.pending_arena_ids(), [ARENA_ID])

    def test_historical_result_can_still_recover_and_count_once(self):
        self.enter_battle()
        self.garage()
        self.restart_in_garage()
        self.tick()
        unused, callback = self.api.pending_callbacks.pop()
        self.footer.states = []
        callback(1, raw_result())
        self.assertIn((0, True), self.footer.states)
        self.assertEqual(self.footer.states[-1], (0, False))
        self.assertEqual(self.summary()['battles'], 1)
        self.assertEqual(self.mod.active_service.pending_arena_ids(), [])
        self.assertFalse(any('Incomplete earlier battle results:' in warning
                             for warning in self.mod.snapshot()['warnings']))
        self.api.events.onBattleResultsReceived(True, raw_result())
        self.assertEqual(self.summary()['battles'], 1)

    def test_current_battle_waits_without_adding_the_historical_backlog(self):
        self.enter_battle()
        self.garage()
        self.restart_in_garage()
        arena_id = str(int(ARENA_ID) + 86401)
        self.clock.value += 1
        self.api.battle = True
        self.api.context = {'arena_id': arena_id, 'started_at': self.clock.value,
                            'vehicle_id': 1, 'map_id': '17_map', 'mode': 'random'}
        self.api.events.onAvatarReady()
        self.assertEqual(self.footer.states[-1], (0, False))
        self.garage()
        self.assertEqual(self.footer.states[-1], (1, False))
        self.assertEqual(len(self.mod.active_service.pending_arena_ids()), 2)
        self.api.events.onBattleResultsReceived(True, raw_result(arena_id=arena_id))
        self.assertEqual(self.footer.states[-1], (0, False))
        self.assertEqual(self.mod.active_service.pending_arena_ids(), [ARENA_ID])

    def test_manual_refresh_retries_backlog_without_reviving_waiting(self):
        self.enter_battle()
        self.garage()
        self.restart_in_garage()
        self.mod.on_action({'action': 'refresh'})
        self.assertEqual(len(self.api.pending_callbacks), 1)
        unused, callback = self.api.pending_callbacks.pop()
        callback(-1, None)
        self.assertEqual(self.footer.states[-1], (0, False))
        self.assertEqual(self.mod.active_service.pending_arena_ids(), [ARENA_ID])

    def test_manual_reset_does_not_erase_backlog_or_reanimate_it(self):
        self.enter_battle()
        self.garage()
        self.restart_in_garage()
        self.mod.on_action({'action': 'reset'})
        self.mod._publish_activity()
        self.assertEqual(self.footer.states[-1], (0, False))
        self.assertEqual(self.mod.active_service.pending_arena_ids(), [ARENA_ID])

    def test_account_switch_selects_only_that_accounts_live_waiting(self):
        self.enter_battle()
        self.garage()
        self.restart_in_garage()
        first = self.mod.active_service
        self.api.dbid = 8
        self.api.events.onAccountBecomePlayer()
        self.assertEqual(self.footer.states[-1], (0, False))
        self.api.battle = True
        self.api.context = {'arena_id': ARENA_ID, 'started_at': START,
                            'vehicle_id': 1, 'map_id': '17_map', 'mode': 'random'}
        self.api.events.onAvatarReady()
        self.garage()
        self.assertEqual(self.footer.states[-1], (1, False))
        self.api.dbid = 7
        self.api.events.onAccountBecomePlayer()
        self.assertEqual(self.footer.states[-1], (0, False))
        self.assertIs(self.mod.active_service, first)
        self.assertEqual(first.pending_arena_ids(), [ARENA_ID])

    def test_stop_and_start_same_runtime_drops_previous_live_activity(self):
        self.enter_battle()
        self.garage()
        self.mod.stop()
        self.footer = fixtures.ActivityFooter()
        self.mod.start()
        self.assertEqual(self.footer.states[-1], (0, False))
        self.assertEqual(self.mod.active_service.pending_arena_ids(), [ARENA_ID])

    def test_reconnect_into_running_battle_is_observed_in_new_runtime(self):
        self.enter_battle()
        self.mod.stop()
        self.footer = fixtures.ActivityFooter()
        self.mod = self.new_runtime()
        self.assertEqual(self.footer.states[-1], (0, False))
        self.garage()
        self.assertEqual(self.footer.states[-1], (1, False))

    def test_old_partial_event_after_login_does_not_make_old_battle_live(self):
        self.enter_battle()
        self.garage()
        self.restart_in_garage()
        raw = raw_result()
        raw['personal'][1]['xp'] = None
        self.api.events.onBattleResultsReceived(True, raw)
        self.assertEqual(self.footer.states[-1], (0, False))
        self.assertEqual(self.mod.active_service.pending_arena_ids(), [ARENA_ID])

    def test_fresh_partial_result_without_avatar_event_still_waits(self):
        self.clock.value = START + 30
        raw = raw_result()
        raw['personal'][1]['xp'] = None
        self.api.events.onBattleResultsReceived(True, raw)
        self.assertEqual(self.footer.states[-1], (1, False))
        self.api.events.onBattleResultsReceived(True, raw_result())
        self.assertEqual(self.footer.states[-1], (0, False))


if __name__ == '__main__':
    unittest.main()
