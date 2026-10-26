# -*- coding: utf-8 -*-
"""Delivered result health, real local logs and garage activity transitions."""
from __future__ import unicode_literals

import io
import logging
import os
import shutil
import tempfile
import unittest

from test_runtime import FakeAPI, FakeWindow, Clock, Obj, EXPECTED
from test_normalize import raw_result, ARENA_ID, START
from grz_session_stats import runtime


class ActivityFooter(object):
    def __init__(self):
        self.states = []
        self.removed = False

    def set_activity(self, pending, processing):
        self.states.append((pending, processing))

    def uninstall(self):
        self.removed = True


class RuntimeHealthTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.mkdtemp(prefix='grz-health-runtime-')
        self.clock = Clock()
        self.api = FakeAPI()
        self.footer = ActivityFooter()
        self.old_disable = logging.root.manager.disable
        self.old_propagate = runtime.LOG.propagate
        logging.disable(logging.NOTSET)
        runtime.LOG.propagate = False
        self.mod = self.new_runtime()

    def new_runtime(self):
        mod = runtime.Runtime(deferred_loading=False, api=self.api, data_dir=self.directory,
                              expected_table=EXPECTED, now=self.clock,
                              window=FakeWindow(), footer_installer=lambda callback: self.footer)
        mod.start()
        return mod

    def tearDown(self):
        self.mod.stop()
        runtime.LOG.propagate = self.old_propagate
        logging.disable(self.old_disable)
        shutil.rmtree(self.directory)

    def enter_battle(self):
        self.clock.value = START
        self.api.battle = True
        self.api.context = {'arena_id': ARENA_ID, 'started_at': START,
                            'vehicle_id': 1, 'map_id': '17_map', 'mode': 'random'}
        self.api.events.onAvatarReady()

    def garage(self):
        self.api.battle = False
        self.api.events.onAccountShowGUI()

    def tick(self, seconds=5):
        self.clock.value += seconds
        self.api.fire(self.mod._tick_id)

    def log(self):
        self.mod._log_handle.flush()
        with io.open(self.mod.log_path, 'r', encoding='utf-8') as handle:
            return handle.read()

    def summary(self, service=None):
        return (service or self.mod.active_service).snapshot()['scopes']['manual']['summary']

    def test_changed_currency_shape_warns_logs_and_preserves_combat_then_reconciles(self):
        self.enter_battle()
        self.garage()
        raw = raw_result()
        raw['personal'][1]['autoEquipCost'] = (15000, 5, 12, 999)
        self.api.events.onBattleResultsReceived(True, raw)
        self.assertEqual(len(self.api.notices), 1)
        self.assertIn('autoEquipCost', self.api.notices[0])
        self.assertIn(self.mod.log_path, self.api.notices[0])
        self.assertIn('code=unsupported_shape', self.log())
        self.assertEqual(self.summary()['battles'], 1)
        self.assertEqual(self.summary()['xp_base']['sum'], 650)
        self.assertIsNone(self.summary()['currencies']['bonds']['net'])
        self.assertEqual(self.footer.states[-1], (1, False))
        self.api.events.onBattleResultsReceived(True, raw_result())
        self.assertEqual(self.footer.states[-1], (0, False))
        self.assertEqual(self.summary()['battles'], 1)
        self.assertEqual(self.summary()['currencies']['bonds']['net'], 28)

    def test_duplicate_raw_posted_and_cache_issues_do_not_repeat_warning_or_log(self):
        self.enter_battle()
        self.garage()
        raw = raw_result()
        raw['personal'][1]['xp'] = 'PRIVATE_PLAYER_987654321'
        for source in ('event', 'posted', 'cache', 'event'):
            self.mod._process(raw, self.mod.active_key, self.mod.active_service, source=source)
            self.clock.value += 65
        self.assertEqual(len(self.api.notices), 1)
        content = self.log()
        self.assertEqual(content.count('path=personal.vehicle.xp '), 1)
        self.assertNotIn('PRIVATE_PLAYER_987654321', content)
        self.assertNotIn('PRIVATE_PLAYER_987654321', self.api.notices[0])

    def test_no_spinner_for_live_battle_but_waiting_after_early_garage_return(self):
        self.assertEqual(self.footer.states[-1], (0, False))
        self.enter_battle()
        self.assertEqual(self.footer.states[-1], (0, False))
        self.garage()
        self.assertEqual(self.footer.states[-1], (1, False))
        self.assertFalse(self.mod.monitor.has_problems)
        self.assertEqual(self.api.notices, [])

    def test_not_ready_cache_keeps_waiting_without_false_format_alarm(self):
        self.enter_battle()
        self.garage()
        self.tick()
        unused, callback = self.api.pending_callbacks.pop()
        callback(-1, None)
        self.assertEqual(self.footer.states[-1], (1, False))
        self.assertEqual(self.api.notices, [])
        self.assertNotIn('HEALTHCHECK', self.log())
        self.tick()
        unused, callback = self.api.pending_callbacks.pop()
        callback(1, raw_result())
        self.assertEqual(self.footer.states[-1], (0, False))
        self.assertEqual(self.summary()['battles'], 1)

    def test_success_cache_with_malformed_result_warns_and_keeps_pending(self):
        self.enter_battle()
        self.garage()
        self.tick()
        unused, callback = self.api.pending_callbacks.pop()
        callback(1, [])
        self.assertEqual(len(self.api.notices), 1)
        self.assertEqual(self.summary()['battles'], 0)
        self.assertEqual(self.footer.states[-1], (1, False))
        self.assertEqual(self.mod.inflight, {})

    def test_cache_wrong_identity_never_records_an_unrequested_battle(self):
        self.enter_battle()
        self.garage()
        self.tick()
        unused, callback = self.api.pending_callbacks.pop()
        callback(1, raw_result(arena_id=str(int(ARENA_ID) + 10)))
        self.assertEqual(self.summary()['battles'], 0)
        self.assertEqual(self.mod.active_service.pending_arena_ids(), [ARENA_ID])
        self.assertIn('code=cache_identity', self.log())
        self.assertEqual(len(self.api.notices), 1)

    def test_processing_state_is_published_around_actual_normalization(self):
        self.enter_battle()
        self.garage()
        self.footer.states = []
        self.api.events.onBattleResultsReceived(True, raw_result())
        self.assertIn((1, True), self.footer.states)
        self.assertEqual(self.footer.states[-1], (0, False))
        self.assertEqual(self.mod._processing, {})
        self.assertIn('Result normalized: source=event complete=True changed=True', self.log())

    def test_pending_is_restored_after_runtime_restart_without_busy_footer(self):
        self.enter_battle()
        self.garage()
        manual_id = self.mod.active_service._state['current_manual_id']
        self.mod.stop()
        self.footer = ActivityFooter()
        self.mod = self.new_runtime()
        self.assertEqual(self.footer.states[-1], (0, False))
        self.assertEqual(self.mod.active_service.pending_arena_ids(), [ARENA_ID])
        self.assertEqual(self.mod.active_service._state['current_manual_id'], manual_id)

    def test_old_account_cache_result_does_not_animate_new_account(self):
        self.enter_battle()
        self.garage()
        first = self.mod.active_service
        self.tick()
        unused, callback = self.api.pending_callbacks.pop()
        self.api.dbid = 8
        self.api.events.onAccountBecomePlayer()
        self.footer.states = []
        callback(1, raw_result())
        self.assertTrue(self.footer.states)
        self.assertTrue(all(value == (0, False) for value in self.footer.states))
        self.assertEqual(self.summary(first)['battles'], 1)
        self.assertEqual(self.summary()['battles'], 0)

    def test_known_other_account_and_mode_do_not_generate_format_alerts(self):
        self.api.events.onBattleResultsReceived(True, raw_result(dbid=8))
        other_mode = raw_result()
        other_mode['common']['bonusType'] = 2
        other_mode['newOtherModeField'] = {'anything': True}
        self.api.events.onBattleResultsReceived(True, other_mode)
        self.assertEqual(self.api.notices, [])
        self.assertEqual(self.summary()['battles'], 0)
        self.assertEqual(self.footer.states[-1], (0, False))

    def test_new_unused_field_warns_but_keeps_complete_result(self):
        self.enter_battle()
        self.garage()
        raw = raw_result()
        raw['common']['newProtocolField'] = 1
        self.api.events.onBattleResultsReceived(True, raw)
        self.assertEqual(len(self.api.notices), 1)
        self.assertIn('newProtocolField', self.api.notices[0])
        self.assertEqual(self.summary()['battles'], 1)
        self.assertEqual(self.footer.states[-1], (0, False))

    def test_wrong_native_callback_signature_warns_without_blocking_next_listener(self):
        self.enter_battle()
        self.garage()
        tail = []
        self.api.events.onBattleResultsReceived += lambda *args: tail.append(True)
        self.api.events.onBattleResultsReceived(raw_result())
        self.assertEqual(tail, [True])
        self.assertEqual(len(self.api.notices), 1)
        self.assertEqual(self.summary()['battles'], 0)
        self.assertIn('code=callback_contract', self.log())

    def test_notification_failure_retains_warning_for_later_garage_retry(self):
        self.enter_battle()
        self.garage()
        original = self.api.notify
        self.api.notify = lambda message: False
        self.api.events.onBattleResultsReceived(True, [])
        self.assertEqual(self.api.notices, [])
        self.api.notify = original
        self.clock.value += 61
        self.mod._service_diagnostics()
        self.assertEqual(len(self.api.notices), 1)
        self.mod._service_diagnostics()
        self.assertEqual(len(self.api.notices), 1)

    def test_warning_waits_for_garage_instead_of_interrupting_active_battle(self):
        self.enter_battle()
        self.api.events.onBattleResultsReceived(True, [])
        self.assertTrue(self.mod.monitor.has_problems)
        self.assertEqual(self.api.notices, [])
        self.garage()
        self.assertEqual(len(self.api.notices), 1)

    def test_failed_log_flush_cannot_stop_tick_rescheduling_or_result_collection(self):
        handle = self.mod._log_handle
        original = handle.flush
        def broken():
            raise RuntimeError('fixture failed diagnostics')
        try:
            handle.flush = broken
            self.tick()
            self.assertIsNotNone(self.mod._tick_id)
            self.enter_battle()
            self.garage()
            self.api.events.onBattleResultsReceived(True, raw_result())
            self.assertEqual(self.summary()['battles'], 1)
            self.assertEqual(self.footer.states[-1], (0, False))
        finally:
            handle.flush = original

    def test_same_activity_is_retried_after_a_silent_native_model_write_failure(self):
        self.enter_battle()
        applied = []
        attempts = []
        def setter(pending, processing):
            attempts.append((pending, processing))
            if len(attempts) > 1:
                applied.append((pending, processing))
        self.footer.set_activity = setter
        self.api.battle = False
        self.mod._publish_activity()
        self.assertEqual(applied, [])
        self.mod._publish_activity()
        self.assertEqual(applied, [(1, False)])

    def test_bonus_timer_marks_processing_then_returns_to_idle(self):
        self.enter_battle()
        self.garage()
        self.api.events.onBattleResultsReceived(True, raw_result())
        self.api.event_bus.emit()
        self.assertEqual(self.footer.states[-1], (0, True))
        self.api.fire(self.mod._bonus_callback_id)
        self.assertEqual(self.footer.states[-1], (0, False))

    def test_stopping_clears_spinner_and_stale_result_cannot_revive_it(self):
        self.enter_battle()
        self.garage()
        self.tick()
        unused, callback = self.api.pending_callbacks.pop()
        self.mod.stop()
        states = list(self.footer.states)
        self.assertEqual(states[-1], (0, False))
        self.assertTrue(self.footer.removed)
        self.assertEqual(self.api.callbacks, {})
        callback(1, raw_result())
        self.assertEqual(self.footer.states, states)


if __name__ == '__main__':
    unittest.main()
