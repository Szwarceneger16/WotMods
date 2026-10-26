# -*- coding: utf-8 -*-
"""Account isolation is the default; the durable installation view is explicit."""
from __future__ import unicode_literals

import copy
import io
import json
import os
import unittest

import test_runtime as fixtures
from grz_session_stats import appearance, runtime
from grz_session_stats.core import aggregate_stats
from test_normalize import ARENA_ID, raw_result


class AccountSessionTests(unittest.TestCase):
    setUp = fixtures.RuntimeTests.__dict__['setUp']
    tearDown = fixtures.RuntimeTests.__dict__['tearDown']
    no_footer = fixtures.RuntimeTests.__dict__['no_footer']
    begin = fixtures.RuntimeTests.__dict__['begin']
    garage = fixtures.RuntimeTests.__dict__['garage']

    def switch(self, dbid, region='EU'):
        self.api.battle = False
        self.api.dbid, self.api.region = dbid, region
        self.api.events.onAccountBecomePlayer()
        return self.mod.active_service

    def battle(self, dbid=7, offset=0, resolved=True):
        service = self.switch(dbid)
        arena_id = str(int(ARENA_ID) + offset)
        self.begin(arena_id)
        self.garage()
        if resolved:
            self.api.events.onBattleResultsReceived(True, raw_result(arena_id=arena_id, dbid=dbid))
        return service, arena_id

    def scopes(self):
        return self.mod.snapshot()['scopes']

    def enable_instance(self, value=True):
        self.mod._installation_dir = self.directory
        self.mod._appearance_override_path = os.path.join(self.directory, 'grz.sessionstats.json')
        with io.open(self.mod._appearance_override_path, 'w', encoding='utf-8') as handle:
            handle.write(json.dumps({'sessions': {'instance_tab': value}}, ensure_ascii=False))
        self.mod._load_appearance()

    def test_default_manual_reset_is_per_account_and_switch_back_restores_it(self):
        first, unused = self.battle()
        self.assertNotIn('instance', self.scopes())
        second, unused = self.battle(8, 10)
        self.battle(8, 20)
        self.assertEqual(self.scopes()['manual']['summary']['battles'], 2)
        self.mod.on_action({'action': 'reset'})
        self.assertEqual(self.scopes()['manual']['summary']['battles'], 0)
        self.assertEqual(self.scopes()['launch']['summary']['battles'], 2)
        self.switch(7)
        self.assertIs(self.mod.active_service, first)
        self.assertEqual(self.scopes()['manual']['summary']['battles'], 1)
        self.switch(8)
        self.assertIs(self.mod.active_service, second)
        self.assertEqual(self.scopes()['manual']['summary']['battles'], 0)

    def test_identical_account_numbers_in_different_regions_are_separate(self):
        first, unused = self.battle()
        self.switch(7, 'NA')
        self.assertEqual(self.scopes()['manual']['summary']['battles'], 0)
        self.mod.on_action({'action': 'reset'})
        self.switch(7, 'EU')
        self.assertIs(self.mod.active_service, first)
        self.assertEqual(self.scopes()['manual']['summary']['battles'], 1)

    def test_stale_confirmation_or_unknown_scope_cannot_reset_current_account(self):
        first, unused = self.battle()
        second, unused = self.battle(8, 10)
        before = [copy.deepcopy(service._state) for service in (first, second)]
        for action in ({'scope': 'manual', 'account_key': 'EU:7'},
                       {'scope': 'invalid'}, {'scope': 'launch'}, {'scope': 'instance'}):
            self.mod.on_action(dict(action, action='reset'))
        self.assertEqual([first._state, second._state], before)

    def test_shared_view_uses_all_current_accounts_without_collision_or_ledger_changes(self):
        self.enable_instance()
        first, unused = self.battle()
        second, unused = self.battle(8)  # Same synthetic arena ID on two accounts.
        raw = raw_result(dbid=8)
        raw['personal'][1]['damageDealt'] = 0
        raw['common']['winnerTeam'] = 2
        self.api.events.onBattleResultsReceived(True, raw)
        before = [copy.deepcopy(service._state) for service in (first, second)]
        shared = self.scopes()['instance']
        records = first.launch_records() + second.launch_records()
        self.assertEqual(shared['summary'], aggregate_stats(records, first.expected_table))
        self.assertEqual(shared['summary']['battles'], 2)
        self.assertEqual(self.scopes()['manual']['summary']['battles'], 1)
        self.assertEqual(len(set(row['id'] for row in shared['battles'])), 2)
        self.assertEqual(shared, self.scopes()['instance'])
        self.assertNotIn('EU:7', json.dumps(shared))
        self.assertNotIn('EU:8', json.dumps(shared))
        self.assertEqual([first._state, second._state], before)

    def test_manual_reset_does_not_change_other_account_or_shared_scope(self):
        self.enable_instance()
        first, unused = self.battle()
        self.battle(8, 10)
        shared = copy.deepcopy(self.scopes()['instance'])
        self.mod.on_action({'action': 'reset', 'scope': 'manual', 'account_key': 'EU:8'})
        self.assertEqual(self.scopes()['manual']['summary']['battles'], 0)
        self.assertEqual(self.scopes()['instance'], shared)
        self.switch(7)
        self.assertEqual(self.scopes()['manual']['summary']['battles'], 1)
        self.assertEqual(first.snapshot()['scopes']['manual']['summary']['battles'], 1)

    def test_instance_reset_does_not_change_any_account_and_only_new_battles_enter(self):
        self.enable_instance()
        first, unused = self.battle()
        second, unused = self.battle(8, 10)
        before = [copy.deepcopy(service._state) for service in (first, second)]
        self.mod.on_action({'action': 'reset', 'scope': 'instance'})
        self.assertEqual(self.scopes()['instance']['summary']['observed_battles'], 0)
        self.assertEqual([first._state, second._state], before)
        self.battle(7, 30)
        self.assertEqual(self.scopes()['instance']['summary']['battles'], 1)
        self.assertEqual(self.scopes()['manual']['summary']['battles'], 2)
        self.switch(8)
        self.assertEqual(self.scopes()['manual']['summary']['battles'], 1)

    def test_result_from_before_shared_reset_cannot_reenter_even_at_same_second(self):
        self.enable_instance()
        unused, arena_id = self.battle(resolved=False)
        self.assertEqual(self.scopes()['instance']['summary']['missing_results'], 1)
        self.mod.on_action({'action': 'reset', 'scope': 'instance'})
        self.api.events.onBattleResultsReceived(True, raw_result(arena_id=arena_id))
        self.assertEqual(self.scopes()['instance']['summary']['observed_battles'], 0)
        self.assertEqual(self.scopes()['manual']['summary']['battles'], 1)

    def test_unseen_late_result_before_shared_reset_is_excluded(self):
        self.enable_instance()
        self.clock.value += 100
        self.mod.on_action({'action': 'reset', 'scope': 'instance'})
        self.api.events.onBattleResultsReceived(True, raw_result())
        self.assertEqual(self.scopes()['instance']['summary']['observed_battles'], 0)
        self.assertEqual(self.scopes()['manual']['summary']['battles'], 1)

    def test_toggle_or_invalid_configuration_does_not_reset_accounts_or_shared_epoch(self):
        self.enable_instance()
        self.battle()
        before = copy.deepcopy(self.mod.active_service._state)
        self.mod.on_action({'action': 'reset', 'scope': 'instance'})
        for enabled in (False, 'true', 1):
            self.enable_instance(enabled)
            self.assertNotIn('instance', self.scopes())
            self.assertEqual(self.mod.active_service._state, before)
        self.enable_instance(True)
        self.assertEqual(self.scopes()['instance']['summary']['observed_battles'], 0)
        self.assertEqual(self.mod.active_service._state, before)

    def test_new_game_process_keeps_shared_scope_and_account_manual_history(self):
        self.enable_instance()
        self.battle()
        self.mod.stop()
        self.api.battle = False
        self.clock.value += 86400
        previous = runtime.LAUNCH_ID
        try:
            runtime.LAUNCH_ID = previous + '-new-game-process'
            self.mod = runtime.Runtime(deferred_loading=False, api=self.api, data_dir=self.directory,
                                       expected_table=fixtures.EXPECTED, now=self.clock,
                                       window=self.window, footer_installer=self.no_footer,
                                       appearance_path=os.path.join(self.directory, 'grz.sessionstats.json'),
                                       installation_dir=self.directory)
            self.mod.start()
        finally:
            runtime.LAUNCH_ID = previous
        scopes = self.scopes()
        self.assertEqual(scopes['manual']['summary']['battles'], 1)
        self.assertEqual(scopes['launch']['summary']['battles'], 0)
        self.assertEqual(scopes['instance']['summary']['observed_battles'], 1)

    def test_detached_launch_records_cannot_mutate_account_history(self):
        self.battle()
        records = self.mod.active_service.launch_records()
        records[0]['currencies']['credits']['net'] = -1
        records[0]['arena_id'] = 'changed'
        self.assertEqual(self.scopes()['manual']['summary']['currencies']['credits']['net'], 32000)
        self.assertEqual(self.scopes()['manual']['battles'][0]['id'], ARENA_ID)


class SessionConfigurationTests(unittest.TestCase):
    def test_instance_tab_requires_an_explicit_boolean_opt_in(self):
        self.assertFalse(appearance.default_config()['sessions']['instance_tab'])
        self.assertTrue(appearance.validate_config({'sessions': {'instance_tab': True}})['sessions']['instance_tab'])
        for invalid in ('true', 1, 0, None, [], {}):
            self.assertFalse(appearance.validate_config({'sessions': {'instance_tab': invalid}})['sessions']['instance_tab'])


if __name__ == '__main__':
    unittest.main()
