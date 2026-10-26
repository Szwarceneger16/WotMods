# -*- coding: utf-8 -*-
"""Delayed bonus work belongs to its scheduling account, not the next login."""
from __future__ import unicode_literals

import copy
import unittest

import test_runtime as fixtures
from test_normalize import ARENA_ID, raw_result


class BonusAccountOwnershipTests(unittest.TestCase):
    setUp = fixtures.RuntimeTests.__dict__['setUp']
    tearDown = fixtures.RuntimeTests.__dict__['tearDown']
    no_footer = fixtures.RuntimeTests.__dict__['no_footer']
    begin = fixtures.RuntimeTests.__dict__['begin']
    garage = fixtures.RuntimeTests.__dict__['garage']
    summary = fixtures.RuntimeTests.__dict__['summary']

    def schedule_then_switch(self):
        self.begin()
        self.garage()
        self.api.events.onBattleResultsReceived(True, raw_result())
        original = self.mod.active_service
        self.api.event_bus.emit()
        timer = self.mod._bonus_callback_id
        self.api.dbid = 8
        self.api.events.onAccountBecomePlayer()
        current = self.mod.active_service
        self.api.events.onBattleResultsReceived(True, raw_result(dbid=8))
        reusable = fixtures.Obj(personal=fixtures.Obj(xpProgress={1: {'xp': 4550}},
                                                      isAddXPBonusApplied=True))
        self.api.posts[ARENA_ID] = fixtures.Obj(results=raw_result(dbid=8), reusable=reusable)
        return timer, original, current

    def test_previous_account_timer_cannot_read_or_revise_new_account(self):
        timer, original, current = self.schedule_then_switch()
        before = [copy.deepcopy(service._state) for service in (original, current)]
        reads, processing = [], []
        posted_bundle = self.api.posted_bundle
        process = self.mod._process

        def observe_read(arena_id):
            reads.append(arena_id)
            return posted_bundle(arena_id)

        def observe_process(*args, **kwargs):
            processing.append(args[1])
            return process(*args, **kwargs)

        self.api.posted_bundle = observe_read
        self.mod._process = observe_process
        self.api.fire(timer)
        self.assertEqual(reads, [])
        self.assertEqual(processing, [])
        self.assertEqual([original._state, current._state], before)
        self.assertIsNone(self.mod._bonus_callback_id)
        self.assertIsNone(self.mod._bonus_account_key)
        # The new account can still schedule and reconcile its own bonus.
        self.api.event_bus.emit()
        self.api.fire(self.mod._bonus_callback_id)
        self.assertEqual(processing, ['EU:8'])
        self.assertEqual(self.summary()['xp_received']['sum'], 4550)

    def test_manual_refresh_on_new_account_does_not_consume_previous_timer(self):
        timer, original, current = self.schedule_then_switch()
        self.mod._refresh_posted()
        self.assertEqual(self.summary()['xp_received']['sum'], 4550)
        self.assertEqual(self.mod._bonus_callback_id, timer)
        self.assertEqual(self.mod._bonus_account_key, 'EU:7')
        after_manual = [copy.deepcopy(service._state) for service in (original, current)]
        self.api.fire(timer)
        self.assertEqual([original._state, current._state], after_manual)
        self.assertIsNone(self.mod._bonus_callback_id)
        self.assertIsNone(self.mod._bonus_account_key)

    def test_old_account_cache_result_cannot_borrow_current_accounts_xp_bonus(self):
        self.begin()
        self.garage()
        self.mod._poll_one(self.mod.active_service, self.mod.active_key)
        unused, callback = self.api.pending_callbacks.pop()
        original = self.mod.active_service
        self.api.dbid = 8
        self.api.events.onAccountBecomePlayer()
        current = self.mod.active_service
        reusable = fixtures.Obj(personal=fixtures.Obj(xpProgress={1: {'xp': 9876}},
                                                      isAddXPBonusApplied=True))
        self.api.posts[ARENA_ID] = fixtures.Obj(results=raw_result(dbid=8), reusable=reusable)
        callback(1, raw_result())
        row = original._state['battles'][ARENA_ID]
        self.assertEqual(row['xp_received'], raw_result()['personal'][1]['xp'])
        self.assertFalse(row['xp_bonus_applied'])
        self.assertEqual(current._state['battles'], {})
        # The same bundle is valid for its own account and must remain usable.
        self.api.events.onBattleResultsReceived(True, raw_result(dbid=8))
        self.assertEqual(current._state['battles'][ARENA_ID]['xp_received'], 9876)

    def test_posted_bonus_requires_matching_account_and_battle_identity(self):
        self.begin()
        self.garage()
        raw = raw_result()
        wrong_battle = raw_result()
        wrong_battle['arenaUniqueID'] += 1
        for posted_raw in (raw_result(dbid=8), wrong_battle, None, {'personal': {}}):
            reusable = fixtures.Obj(personal=fixtures.Obj(xpProgress={1: {'xp': 9876}},
                                                          isAddXPBonusApplied=True))
            self.api.posts[ARENA_ID] = fixtures.Obj(results=posted_raw, reusable=reusable)
            self.api.events.onBattleResultsReceived(True, raw)
            row = self.mod.active_service._state['battles'][ARENA_ID]
            self.assertEqual(row['xp_received'], raw['personal'][1]['xp'])
            self.assertFalse(row['xp_bonus_applied'])


if __name__ == '__main__':
    unittest.main()
