# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import copy
import json
import logging
import os
import shutil
import tempfile
import unittest

from test_runtime import runtime, FakeAPI, FakeWindow, Clock, Obj, EXPECTED
from test_normalize import raw_result, ARENA_ID
from test_core import result


class ResultDisplay(object):
    def __init__(self, provider):
        self.provider = provider
        self.arena = None
        self.account = None
        self.states = []
        self.labels = None
        self.enabled = True
        self.release = True
        self.fail_refresh = False

    def set_language(self, labels):
        self.labels = labels

    def refresh(self):
        if self.fail_refresh:
            raise RuntimeError('synthetic display failure')
        if self.enabled and self.arena is not None:
            value = self.provider(self.arena, self.account)
            if self.account is None and value.get('account_key') is not None:
                self.account = value['account_key']
            self.states.append(value)

    def uninstall(self):
        self.enabled = False
        return self.release


class RuntimePostbattleTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.mkdtemp(prefix='grz-postbattle-runtime-')
        self.clock = Clock()
        self.api = FakeAPI()
        self.displays = []
        self.previous_log = logging.root.manager.disable
        logging.disable(logging.CRITICAL)
        self.mod = runtime.Runtime(api=self.api, data_dir=self.directory,
                                   expected_table=EXPECTED, now=self.clock,
                                   deferred_loading=False, window=FakeWindow(),
                                   footer_installer=lambda unused: None,
                                   postbattle_installer=self.install)
        self.mod.start()

    def install(self, provider):
        display = ResultDisplay(provider)
        self.displays.append(display)
        return display

    def tearDown(self):
        for display in self.displays:
            display.release = True
        self.mod.stop()
        logging.disable(self.previous_log)
        shutil.rmtree(self.directory)

    def test_result_display_is_independent_of_the_optional_garage_button(self):
        self.mod.stop()
        with open(os.path.join(self.directory, 'config.json'), 'w') as stream:
            json.dump({'footer_button': False}, stream)
        self.mod.start()
        self.assertIs(self.mod.postbattle_handle, self.displays[-1])
        self.assertIsNone(self.mod.footer_handle)

    def test_processing_result_updates_spinner_state_then_its_own_value_immediately(self):
        display = self.displays[-1]
        display.arena = ARENA_ID
        display.refresh()
        self.assertEqual(display.states[-1]['state'], 'pending')
        self.api.events.onBattleResultsReceived(True, raw_result())
        self.assertIn('pending', [state['state'] for state in display.states])
        self.assertEqual(display.states[-1]['state'], 'ready')
        self.assertAlmostEqual(display.states[-1]['value'], self.mod.active_service.battle_rating(ARENA_ID)['wn8'])
        self.assertIn('format.thousands', display.labels)

    def test_newer_results_and_account_wide_processing_cannot_replace_displayed_battle(self):
        self.api.events.onBattleResultsReceived(True, raw_result())
        expected = self.mod.result_rating(ARENA_ID)['value']
        other = raw_result(str(int(ARENA_ID) + 1))
        other['personal'][1].update(damageDealt=0, kills=0, spotted=0, droppedCapturePoints=0)
        other['common']['winnerTeam'] = 2
        self.api.events.onBattleResultsReceived(True, other)
        self.mod._processing[self.mod.active_key] = 1
        self.assertEqual(self.mod.result_rating(ARENA_ID)['value'], expected)
        self.assertEqual(self.mod.result_rating(other['arenaUniqueID'])['value'], 0)

    def test_zero_and_incomplete_finances_are_ready_without_aggregate_snapshot(self):
        service = self.mod.active_service
        service.record_result(result(arena_id=ARENA_ID, outcome='loss', damage=0,
                                     frags=0, spots=0, defense=0, complete=False,
                                     xp_base=None, xp_received=None, free_xp=None, currencies={}))

        def forbidden():
            raise AssertionError('The result display must not project all history')

        service.snapshot = forbidden
        answer = self.mod.result_rating(ARENA_ID)
        self.assertEqual(answer['state'], 'ready')
        self.assertEqual(answer['value'], 0)

    def test_known_pending_result_times_out_but_late_success_still_replaces_the_dash(self):
        self.mod.active_service.begin_battle(ARENA_ID, vehicle_id=1)
        self.assertEqual(self.mod.result_rating(ARENA_ID)['state'], 'pending')
        self.clock.value += runtime.RESULT_RATING_WAIT_SECONDS + 1
        self.assertEqual(self.mod.result_rating(ARENA_ID)['state'], 'unavailable')
        self.api.events.onBattleResultsReceived(True, raw_result())
        self.assertEqual(self.mod.result_rating(ARENA_ID)['state'], 'ready')

    def test_missing_result_uses_cached_posted_controller_without_an_extra_request(self):
        self.api.posts[ARENA_ID] = Obj(results=raw_result(), reusable=None)
        answer = self.mod.result_rating(ARENA_ID)
        self.assertEqual(answer['state'], 'ready')
        self.assertEqual(self.api.pending_callbacks, [])
        self.assertEqual(len(self.mod.active_service._state['battles']), 1)

    def test_missing_result_deadline_is_finite_and_a_late_cached_bundle_can_recover(self):
        self.assertEqual(self.mod.result_rating(ARENA_ID)['state'], 'pending')
        self.clock.value += runtime.RESULT_RATING_WAIT_SECONDS + 1
        self.assertEqual(self.mod.result_rating(ARENA_ID)['state'], 'unavailable')
        self.api.posts[ARENA_ID] = Obj(results=raw_result(), reusable=None)
        self.assertEqual(self.mod.result_rating(ARENA_ID)['state'], 'ready')
        self.assertEqual(self.api.pending_callbacks, [])

    def test_foreign_posted_identity_does_not_record_or_display_the_other_result(self):
        self.api.posts[ARENA_ID] = Obj(results=raw_result(str(int(ARENA_ID) + 1)), reusable=None)
        self.assertEqual(self.mod.result_rating(ARENA_ID)['state'], 'pending')
        self.assertEqual(self.mod.active_service._state['battles'], {})
        self.api.posts[ARENA_ID] = Obj(results=raw_result(dbid=8), reusable=None)
        self.assertEqual(self.mod.result_rating(ARENA_ID)['state'], 'unavailable')
        self.assertEqual(self.mod.active_service._state['battles'], {})

    def test_existing_view_never_follows_a_new_login_even_when_arena_ids_match(self):
        display = self.displays[-1]
        display.arena = ARENA_ID
        self.api.events.onBattleResultsReceived(True, raw_result())
        self.assertEqual(display.account, 'EU:7')
        self.api.dbid = 8
        display.refresh()
        self.assertEqual(display.states[-1]['state'], 'unavailable')
        self.api.events.onAccountShowGUI()
        other = raw_result(dbid=8)
        other['personal'][1].update(damageDealt=0, kills=0, spotted=0, droppedCapturePoints=0)
        other['common']['winnerTeam'] = 2
        self.api.events.onBattleResultsReceived(True, other)
        self.assertEqual(self.mod.result_rating(ARENA_ID)['value'], 0)
        self.assertEqual(display.states[-1]['account_key'], 'EU:7')
        self.assertEqual(display.states[-1]['state'], 'unavailable')

    def test_context_change_during_posted_lookup_cannot_publish_old_or_new_account_values(self):
        def switched(unused):
            self.api.dbid = 8
            return Obj(results=raw_result(dbid=8), reusable=None)

        self.api.posted_bundle = switched
        self.assertEqual(self.mod.result_rating(ARENA_ID, 'EU:7')['state'], 'unavailable')
        self.assertEqual(self.mod.active_service._state['battles'], {})

    def test_invalid_ids_replay_and_broken_native_context_do_not_reach_a_reader(self):
        for identifier in (None, True, False, 0, -1, 1.5, [], {}, 'not-an-arena', '1' * 25):
            self.assertEqual(self.mod.result_rating(identifier)['state'], 'unavailable')
        self.api.replay = True
        self.assertEqual(self.mod.result_rating(ARENA_ID)['state'], 'unavailable')
        self.api.replay = False

        def broken():
            raise RuntimeError('synthetic native account error')

        self.api.account_dbid = broken
        self.assertEqual(self.mod.result_rating(ARENA_ID)['state'], 'unavailable')
        self.assertEqual(self.api.pending_callbacks, [])

    def test_missing_expected_table_is_terminal_without_a_spinner_or_reader(self):
        self.mod.active_service.expected_table.values.clear()
        self.assertEqual(self.mod.result_rating(ARENA_ID)['state'], 'unavailable')
        self.assertEqual(self.api.pending_callbacks, [])

    def test_unavailable_login_binding_is_bounded_and_context_tracking_is_bounded(self):
        self.api.dbid = None
        self.assertEqual(self.mod.result_rating(ARENA_ID)['state'], 'pending')
        self.clock.value += runtime.RESULT_RATING_WAIT_SECONDS + 1
        self.assertEqual(self.mod.result_rating(ARENA_ID)['state'], 'unavailable')
        self.api.dbid = 7
        for identifier in range(1, 141):
            self.mod.result_rating(identifier)
        self.assertLessEqual(len(self.mod._postbattle_queries), 128)

    def test_retained_provider_is_inert_after_restart_and_failed_removal_retains_ownership(self):
        display = self.displays[-1]
        previous = display.provider
        display.release = False
        self.mod.stop()
        self.assertFalse(self.mod.cleanup_complete())
        self.mod.start()
        self.assertEqual(len(self.displays), 1)
        self.assertEqual(previous(ARENA_ID, 'EU:7')['state'], 'unavailable')
        display.release = True
        self.mod.stop()
        self.assertTrue(self.mod.cleanup_complete())
        self.mod.start()
        self.assertEqual(len(self.displays), 2)
        self.assertEqual(previous(ARENA_ID, 'EU:7')['state'], 'unavailable')

    def test_optional_display_errors_do_not_block_result_collection(self):
        self.displays[-1].fail_refresh = True
        self.api.events.onBattleResultsReceived(True, raw_result())
        self.assertEqual(self.mod.result_rating(ARENA_ID)['state'], 'ready')
        self.assertFalse(self.mod._postbattle_refreshing)
        self.assertNotIn('postbattle:refresh', self.mod.compatibility_warnings)


if __name__ == '__main__':
    unittest.main()
