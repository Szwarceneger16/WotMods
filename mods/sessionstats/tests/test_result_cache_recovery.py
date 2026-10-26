# -*- coding: utf-8 -*-
"""Native cache consumption, server retry scheduling and durable offline recovery.

The transport is a fixture; these tests do not assert server retention duration.
"""
from __future__ import unicode_literals

import unittest

import test_runtime_health as fixtures
from test_runtime import FakeAPI, Obj
from test_normalize import raw_result, ARENA_ID, START
from grz_session_stats import runtime
from grz_session_stats.cache_observer import CacheObserver, OWN_CALLBACK, _function


class NativeCache(object):
    def __init__(self):
        self.requests = []

    def get(self, arena_id, callback):
        self.requests.append((arena_id, callback))
        return 'native-return'


class RecoveryAPI(FakeAPI):
    def __init__(self):
        FakeAPI.__init__(self)
        self.cache = NativeCache()

    def player(self):
        return Obj(battleResultsCache=self.cache)

    result_cache = runtime.GameAPI.__dict__['result_cache']
    request_result = runtime.GameAPI.__dict__['request_result']

    def result_status(self, code):
        return {-5: 'cooldown', -14: 'rate_limited', -3: 'not_ready',
                -7: 'disconnected', -10: 'unavailable', -2: 'rejected'}.get(code, 'not_returned')


class CacheObserverTests(unittest.TestCase):
    def setUp(self):
        self.original = _function(NativeCache.get)
        self.cache = NativeCache()
        self.received = []
        self.handle = CacheObserver(self.cache, lambda: 'context',
                                    lambda *args: self.received.append(args))

    def tearDown(self):
        self.handle.close()
        NativeCache.get = self.original

    def test_preserves_arguments_return_and_consumer_after_observation(self):
        calls = []
        result = self.cache.get(17, lambda *args, **kwargs: calls.append((args, kwargs, len(self.received))))
        self.assertEqual(self.cache.get.__name__, 'get')
        self.assertEqual(result, 'native-return')
        arena_id, callback = self.cache.requests.pop()
        raw = {'opaque': 'fixture'}
        callback(1, raw, 'extra', flag=True)
        self.assertEqual(self.received, [('context', 17, (1, raw, 'extra'))])
        self.assertEqual(calls, [((1, raw, 'extra'), {'flag': True}, 1)])

    def test_observer_failure_never_swallows_original_consumer(self):
        def broken(*args):
            raise RuntimeError('fixture observer failure')
        self.handle._consume = broken
        calls = []
        self.cache.get(17, lambda *args: calls.append(args))
        self.cache.requests.pop()[1](1, {})
        self.assertEqual(calls, [(1, {})])

    def test_none_consumer_and_other_cache_instance_keep_native_behavior(self):
        other = NativeCache()
        other.get(18, None)
        self.assertIsNone(other.requests[-1][1])
        self.cache.get(17, None)
        self.cache.requests.pop()[1](1, {})
        self.assertEqual(len(self.received), 1)

    def test_own_requests_are_not_processed_twice(self):
        def callback(*args):
            return None
        setattr(callback, OWN_CALLBACK, True)
        self.cache.get(17, callback)
        self.assertIs(self.cache.requests[-1][1], callback)
        callback(1, {})
        self.assertEqual(self.received, [])

    def test_close_restores_owned_method_and_retained_callback_is_inert(self):
        calls = []
        self.cache.get(17, lambda *args: calls.append(args))
        callback = self.cache.requests.pop()[1]
        self.handle.close()
        self.assertIs(_function(NativeCache.get), self.original)
        callback(1, {})
        self.assertEqual(self.received, [])
        self.assertEqual(calls, [(1, {})])

    def test_later_mod_wrapper_is_preserved_and_can_still_call_our_inert_link(self):
        observed = _function(NativeCache.get)
        calls = []
        def later(instance, arena_id, callback):
            calls.append(arena_id)
            return observed(instance, arena_id, callback)
        NativeCache.get = later
        self.handle.close()
        self.assertIs(_function(NativeCache.get), later)
        self.cache.get(19, None)
        self.assertEqual(calls, [19])
        self.assertEqual(self.cache.requests[-1], (19, None))
        self.assertIsNone(self.handle._capture)
        self.assertIsNone(self.handle._consume)


class RecoveryRuntimeTests(unittest.TestCase):
    tearDown = fixtures.RuntimeHealthTests.__dict__['tearDown']
    new_runtime = fixtures.RuntimeHealthTests.__dict__['new_runtime']
    enter_battle = fixtures.RuntimeHealthTests.__dict__['enter_battle']
    garage = fixtures.RuntimeHealthTests.__dict__['garage']
    tick = fixtures.RuntimeHealthTests.__dict__['tick']
    summary = fixtures.RuntimeHealthTests.__dict__['summary']
    log = fixtures.RuntimeHealthTests.__dict__['log']

    def setUp(self):
        fixtures.RuntimeHealthTests.__dict__['setUp'](self)
        self.mod.stop()
        self.api = RecoveryAPI()
        self.footer = fixtures.ActivityFooter()
        self.mod = self.new_runtime()

    def receive(self, code, raw):
        arena_id, callback = self.api.cache.requests.pop(0)
        callback(code, raw)
        return str(arena_id)

    def test_native_ui_read_is_saved_before_its_consumer_without_result_events(self):
        self.enter_battle()
        self.garage()
        calls = []
        def consumer(code, raw):
            calls.append((code, self.summary()['battles'], self.mod.active_service.store.sequence))
        self.api.cache.get(int(ARENA_ID), consumer)
        before = self.mod.active_service.store.sequence
        self.receive(1, raw_result())
        self.assertEqual(calls, [(1, 1, before + 1)])
        self.assertEqual(self.mod.active_service.pending_arena_ids(), [])
        self.mod.stop()
        self.api.cache = NativeCache()  # The stock client discards its disk cache on startup.
        self.clock.value += 86400
        self.mod = self.new_runtime()
        self.assertEqual(self.summary()['battles'], 1)
        self.assertEqual(self.mod.active_service.pending_arena_ids(), [])

    def test_result_finishing_while_client_offline_recovers_into_original_period(self):
        self.enter_battle()
        self.garage()
        original_launch = self.mod.active_service.launch_id
        original_manual = self.mod.active_service._state['current_manual_id']
        self.mod.stop()
        server_result = raw_result()  # No mod callback runs while the client is closed.
        self.clock.value += 86400
        self.api.cache = NativeCache()
        old_launch = runtime.LAUNCH_ID
        try:
            runtime.LAUNCH_ID = 'new-offline-recovery-client'
            self.mod = self.new_runtime()
        finally:
            runtime.LAUNCH_ID = old_launch
        self.assertEqual(self.summary()['battles'], 0)
        self.assertEqual(self.mod.snapshot()['scopes']['manual']['summary']['missing_results'], 1)
        self.tick()
        self.assertEqual(self.receive(1, server_result), ARENA_ID)
        row = self.mod.active_service._state['battles'][ARENA_ID]
        self.assertEqual(row['_launch_id'], original_launch)
        self.assertEqual(row['_manual_id'], original_manual)
        self.assertEqual(self.summary()['battles'], 1)
        self.assertEqual(self.mod.snapshot()['scopes']['launch']['summary']['battles'], 0)
        self.assertEqual(self.mod.snapshot()['scopes']['manual']['summary']['missing_results'], 0)
        self.assertEqual(self.log().count('Result normalized: source=cache'), 1)
        self.api.events.onBattleResultsReceived(True, server_result)
        self.assertEqual(self.summary()['battles'], 1)

    def test_new_live_battle_is_requested_before_historical_backlog(self):
        old = str(int(ARENA_ID) - 100)
        self.mod.active_service.begin_battle(old, started_at=START-100, mode='random')
        self.enter_battle()
        self.garage()
        self.tick()
        self.assertEqual(str(self.api.cache.requests[0][0]), ARENA_ID)

    def test_untried_backlog_is_not_starved_by_the_first_failed_record(self):
        first = str(int(ARENA_ID) - 100)
        second = str(int(ARENA_ID) - 200)
        for arena_id in (first, second):
            self.mod.active_service.begin_battle(arena_id, started_at=START-100, mode='random')
        self.tick()
        requested = self.receive(-1, None)
        self.tick()
        next_requested = self.receive(-1, None)
        self.assertNotEqual(requested, next_requested)
        self.assertEqual(set((requested, next_requested)), set((first, second)))

    def test_client_cooldown_and_login_delays_do_not_inflate_failure_backoff(self):
        self.enter_battle()
        self.garage()
        key = (self.mod.active_key, ARENA_ID)
        for code, seconds in ((-5, 5), (-3, 5), (-7, 5), (-14, 30)):
            self.tick(seconds=30)
            self.receive(code, None)
            attempts, due = self.mod.retries[key]
            self.assertEqual(attempts, 0)
            self.assertEqual(due, self.clock.value + seconds)
        self.assertFalse(self.mod.monitor.has_problems)

    def test_unavailable_server_keeps_explicit_gap_and_logs_no_identifiers(self):
        self.enter_battle()
        self.garage()
        self.tick()
        self.receive(-10, None)
        snapshot = self.mod.snapshot()
        self.assertEqual(snapshot['scopes']['manual']['summary']['missing_results'], 1)
        self.assertEqual(snapshot['scopes']['manual']['summary']['battles'], 0)
        self.assertEqual(snapshot['recovery']['states'], {'unavailable': 1})
        self.assertIn('Result recovery: status=unavailable code=-10', self.log())
        self.assertNotIn(ARENA_ID, self.log())
        self.assertNotIn('EU:7', self.log())
        self.assertEqual(self.mod.active_service.pending_arena_ids(), [ARENA_ID])

    def test_unknown_native_status_never_logs_arbitrary_numeric_values(self):
        self.enter_battle()
        self.garage()
        self.tick()
        self.receive(-987654321, None)
        self.assertIn('status=not_returned code=unknown', self.log())
        self.assertNotIn('987654321', self.log())

    def test_observed_response_keeps_original_account_after_account_switch(self):
        self.enter_battle()
        self.garage()
        first = self.mod.active_service
        calls = []
        self.api.cache.get(int(ARENA_ID), lambda *args: calls.append(args))
        self.api.dbid = 8
        self.api.events.onAccountBecomePlayer()
        self.receive(1, raw_result())
        self.assertEqual(self.summary(first)['battles'], 1)
        self.assertEqual(self.summary()['battles'], 0)
        self.assertEqual(self.footer.states[-1], (0, False))
        self.assertEqual(len(calls), 1)

    def test_mismatched_observed_identity_and_other_owner_never_mutate_ledger(self):
        for results in (raw_result(arena_id=str(int(ARENA_ID)+1)), raw_result(dbid=8)):
            calls = []
            self.api.cache.get(int(ARENA_ID), lambda *args: calls.append(args))
            self.receive(1, results)
            self.assertEqual(self.summary()['battles'], 0)
            self.assertEqual(len(calls), 1)

    def test_consumer_exception_cannot_lose_the_already_saved_result(self):
        self.enter_battle()
        self.garage()
        def broken(*args):
            raise RuntimeError('fixture native consumer failure')
        self.api.cache.get(int(ARENA_ID), broken)
        with self.assertRaises(RuntimeError):
            self.receive(1, raw_result())
        self.assertEqual(self.summary()['battles'], 1)

    def test_player_transition_does_not_detach_an_outstanding_native_read(self):
        self.enter_battle()
        self.garage()
        self.api.cache.get(int(ARENA_ID), None)
        self.api.result_cache = lambda: None
        self.api.battle = True
        self.mod._ensure_service()
        self.receive(1, raw_result())
        self.assertEqual(self.summary()['battles'], 1)

    def test_stopped_observer_never_saves_old_lifecycle_but_preserves_consumer(self):
        self.enter_battle()
        self.garage()
        calls = []
        self.api.cache.get(int(ARENA_ID), lambda *args: calls.append(args))
        self.mod.stop()
        self.mod.start()
        self.receive(1, raw_result())
        self.assertEqual(self.summary()['battles'], 0)
        self.assertEqual(len(calls), 1)

    def test_late_stream_recovers_data_without_consuming_a_newer_request(self):
        self.enter_battle()
        self.garage()
        self.tick()
        original = self.api.cache.requests.pop()[1]
        self.tick(seconds=31)
        current = self.mod.inflight[(self.mod.active_key, ARENA_ID)]
        original(1, raw_result())
        self.assertIs(self.mod.inflight[(self.mod.active_key, ARENA_ID)], current)
        self.assertEqual(self.summary()['battles'], 1)
        self.receive(1, raw_result())
        self.assertEqual(self.summary()['battles'], 1)
        self.assertEqual(self.mod.inflight, {})

    def test_late_stream_never_revises_a_newer_confirmed_result(self):
        self.enter_battle()
        self.garage()
        self.tick()
        original = self.api.cache.requests.pop()[1]
        self.tick(seconds=31)
        current = self.mod.inflight[(self.mod.active_key, ARENA_ID)]
        newest = raw_result()
        newest['personal'][1]['damageDealt'] = 2400
        self.api.events.onBattleResultsReceived(True, newest)
        original(1, raw_result())
        self.assertEqual(self.mod.active_service._state['battles'][ARENA_ID]['damage'], 2400)
        self.assertIs(self.mod.inflight[(self.mod.active_key, ARENA_ID)], current)

    def test_late_stream_cannot_mark_an_unapplied_xp_value_as_bonus_applied(self):
        self.enter_battle()
        self.garage()
        self.tick()
        original = self.api.cache.requests.pop()[1]
        self.tick(seconds=31)
        raw = raw_result()
        self.api.events.onBattleResultsReceived(True, raw)
        known_xp = raw['personal'][1]['xp']
        self.api.posts[ARENA_ID] = Obj(results=raw, reusable=Obj(personal=Obj(
            xpProgress={1: {'xp': known_xp * 3}}, isAddXPBonusApplied=True)))
        original(1, raw)
        row = self.mod.active_service._state['battles'][ARENA_ID]
        self.assertEqual(row['xp_received'], known_xp)
        self.assertFalse(row['xp_bonus_applied'])
        self.receive(1, raw)
        row = self.mod.active_service._state['battles'][ARENA_ID]
        self.assertEqual(row['xp_received'], known_xp * 3)
        self.assertTrue(row['xp_bonus_applied'])

    def test_failed_late_normalization_keeps_new_token_and_hides_exception_values(self):
        self.enter_battle()
        self.garage()
        self.tick()
        original = self.api.cache.requests.pop()[1]
        self.tick(seconds=31)
        key = (self.mod.active_key, ARENA_ID)
        current = self.mod.inflight[key]
        def broken(*args, **kwargs):
            raise RuntimeError('PRIVATE-fixture-payload')
        self.mod._process = broken
        original(1, raw_result())
        self.assertIs(self.mod.inflight[key], current)
        self.assertEqual(self.summary()['battles'], 0)
        self.assertNotIn('PRIVATE-fixture-payload', self.log())


if __name__ == '__main__':
    unittest.main()
