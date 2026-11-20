# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import copy
import shutil
import sys
import tempfile
import unittest

from test_core import EXPECTED, result
from test_normalize import raw_result
import test_runtime as runtime_fixtures
from test_runtime import Clock, Obj
from grz_session_stats import battle_details
from grz_session_stats.battle_details import game_active_crucible, game_mission_metadata
from grz_session_stats.core import StatsService
from grz_session_stats.sessions import InstallationSession
from grz_session_stats.normalize import normalize_result


class TimelineAndBattleDetailsTests(unittest.TestCase):
    inject_module = runtime_fixtures.NativeBindingTests.__dict__['inject_module']

    def setUp(self):
        self.directory = tempfile.mkdtemp()
        self.clock = Clock(100)
        self.service = self.open_service('first')

    def tearDown(self):
        shutil.rmtree(self.directory)

    def open_service(self, launch, account='EU:7'):
        return StatsService(self.directory, account, launch, EXPECTED, now=self.clock, timeline_enabled=True)

    def test_timeline_keeps_legacy_boundaries_and_filters_all_groups_by_battle_start(self):
        self.clock.value = 130
        self.assertTrue(self.service.record_result(result('old', 110)))
        legacy = self.service.reset_manual()
        self.clock.value = 140
        self.assertTrue(self.service.create_time_point())
        self.assertEqual(self.service.timeline_snapshot()['summary']['battles'], 1)
        points = self.service.timeline_snapshot()['time_points']
        self.assertEqual(points[0], (legacy, 130))
        cutoff = points[1][0]
        self.clock.value = 190
        self.assertTrue(self.service.record_result(result('first', 130)))
        self.assertTrue(self.service.record_result(result('last', 140)))
        self.assertTrue(self.service.record_result(result('unknown', None)))
        self.assertTrue(self.service.set_timeline_range(legacy, cutoff))
        self.assertTrue(self.service.timeline_snapshot()['loading'])
        while self.service.advance_timeline():
            pass
        scope = self.service.timeline_snapshot()
        self.assertEqual([row['id'] for row in scope['battles']], ['first'])
        self.assertEqual(scope['summary']['battles'], 1)
        self.assertEqual(scope['vehicles'][0]['stats']['battles'], 1)
        self.assertTrue(self.service.set_page('timeline', 'battles', 0, scope['period_id']))
        self.assertFalse(self.service.set_timeline_range(cutoff, legacy))
        self.assertFalse(self.service.set_timeline_range('another-account', ''))
        self.assertEqual(self.service.timeline_snapshot(), scope)
        self.clock.value = 200
        self.assertTrue(self.service.record_result(result('late', 135)))
        self.assertEqual(self.service.timeline_snapshot()['summary']['battles'], 2)
        self.assertTrue(self.service.set_timeline_range('', ''))
        self.assertEqual(self.service.timeline_snapshot()['summary']['battles'], 5)
        restored = self.open_service('second')
        self.assertEqual(restored.timeline_snapshot()['time_points'], points)
        self.assertEqual(restored.timeline_snapshot()['summary']['battles'], 5)
        self.assertEqual(self.open_service('other', 'EU:8').timeline_snapshot()['time_points'], [])

    def test_normalize_confirmed_crucible_and_points_without_counting_allocations_twice(self):
        raw = raw_result()
        active = 'challenge:8:2'
        avatar = raw['personal']['avatar']
        avatar.update(bpTopPoints=8, eventBattlePassPoints=10, bpBonusPoints=15,
                      bpNonChapterPointsDiff=33, bpChaptersInfo={5: (10, 43)},
                      fairplayViolations=(0, 2, 0),
                      questsProgress={active + ':fail': ('group', {}, {'bonusCount': 1})})
        raw['personal'][1].update(boosterCredits=1000, dailyXPFactor10=20,
                                  questsProgress={'daily:test': ('group', {}, {'bonusCount': 1})})
        details = normalize_result(raw, {'active_crucible': active})['details']
        self.assertEqual(details['pass_points'], {'battle': 8, 'missions': 10, 'vehicle': 15, 'credited': 33})
        self.assertEqual(details['bonuses']['boosterCredits'], 1000)
        self.assertEqual(details['bonuses']['dailyXPFactor10'], 20)
        self.assertTrue(details['suicide'])
        self.assertEqual(details['missions'][active]['status'], 'failed')
        self.assertEqual(details['missions']['daily:test']['status'], 'completed')
        avatar['questsProgress'][active] = ('group', {}, {'bonusCount': 1})
        self.assertEqual(normalize_result(raw)['details']['missions'][active]['status'], 'completed')

    def test_active_crucible_and_confirmed_result_survive_reopen_and_partial_retry(self):
        active = 'challenge:8:2'
        self.clock.value = 110
        self.assertTrue(self.service.begin_battle('1', 110, mode='random', details={
            'active_crucible': active, 'missions': {active: {'name': '<b>Fixture mission</b>', 'kind': 'crucible', 'stage': 2}},
        }))
        self.assertNotIn('status', self.service.timeline_snapshot()['battles'][0]['details']['missions'][active])
        self.assertTrue(self.service.record_result(result(details={'missions': {active: {'status': 'completed'}}})))
        self.service.record_result(result(details={'missions': {active: {'status': 'observed'}}}, reconcile=True))
        self.clock.value = 120
        restored = self.open_service('second')
        self.assertEqual(restored.result_context('1')['active_crucible'], active)
        mission = restored.timeline_snapshot()['battles'][0]['details']['missions'][active]
        self.assertEqual(mission, {'kind': 'crucible', 'stage': 2, 'name': 'Fixture mission', 'status': 'completed'})

    def test_native_current_crucible_counter_selects_first_middle_and_last_stage(self):
        self.modules = {}
        originals = self.modules

        def restore_modules():
            for name, original in originals.items():
                if original is None:
                    sys.modules.pop(name, None)
                else:
                    sys.modules[name] = original

        self.addCleanup(restore_modules)
        challenge = Obj(challengeID=8, questsIDs=['challenge:8:1', 'challenge:8:2', 'challenge:8:3'],
                        name='Fixture challenge')
        progress = {'quests': 1}
        controller = Obj(isEnabled=True, activeChallengeID=8,
                         getChallenge=lambda unused: challenge, getChallengeProgress=lambda unused: progress)
        self.inject_module('helpers', dependency=Obj(instance=lambda unused: controller))
        self.inject_module('skeletons.gui.challenges', IChallengesController=object())
        resolver = battle_details.game_mission_metadata
        self.addCleanup(setattr, battle_details, 'game_mission_metadata', resolver)
        battle_details.game_mission_metadata = lambda unused: None
        for stage in (1, 2, 3):
            progress['quests'] = stage
            active = 'challenge:8:{0}'.format(stage)
            details = game_active_crucible()
            self.assertEqual(details['active_crucible'], active)
            self.assertEqual(details['missions'], {
                active: {'kind': 'crucible', 'stage': stage, 'name': 'Fixture challenge'}})
        for invalid in (0, -1, 4, None, True, '1'):
            progress['quests'] = invalid
            self.assertEqual(game_active_crucible(), {})

    def test_legacy_next_stage_placeholder_is_repaired_by_result_and_stays_repaired(self):
        actual, phantom = 'challenge:8:1', 'challenge:8:2'
        context = {'active_crucible': phantom, 'missions': {
            phantom: {'name': 'Fixture challenge', 'kind': 'crucible', 'stage': 2,
                      'description': 'Next stage objective'}}}
        self.clock.value = 110
        self.assertTrue(self.service.begin_battle('1', 110, mode='random', details=context))
        report = battle_details.result_details({'questsProgress': {
            actual + ':fail': ('group', {}, {'bonusCount': 1})}}, {}, active=phantom)
        self.assertTrue(self.service.record_result(result(details=report)))
        expected = {'active_crucible': actual, 'missions': {
            actual: {'name': 'Fixture challenge', 'kind': 'crucible', 'stage': 1, 'status': 'failed'}}}
        self.assertEqual(self.service.timeline_snapshot()['battles'][0]['details'], expected)
        self.service.record_result(result(details=context, reconcile=True))
        self.clock.value = 120
        restored = self.open_service('second')
        self.assertEqual(restored.result_context('1')['active_crucible'], actual)
        self.assertEqual(restored.timeline_snapshot()['battles'][0]['details'], expected)

    def test_saved_legacy_duplicate_loads_and_displays_a_single_actual_mission(self):
        actual, phantom = 'challenge:8:1', 'challenge:8:2'
        self.clock.value = 110
        self.assertTrue(self.service.record_result(result()))
        legacy = copy.deepcopy(self.service._state)
        details = {'active_crucible': phantom, 'missions': {
            phantom: {'name': 'Fixture challenge', 'kind': 'crucible', 'stage': 2,
                      'description': 'Next stage objective'},
            actual: {'kind': 'crucible', 'stage': 1, 'status': 'failed'}}}
        legacy['battles']['1']['details'] = details
        self.service.store.save(legacy)
        self.clock.value = 120
        restored = self.open_service('second')
        self.assertTrue(restored.ready)
        self.assertEqual(restored._state['battles']['1']['details'], details)
        scopes = restored.snapshot()['scopes']
        for scope in (scopes['manual'], restored.timeline_snapshot()):
            displayed = scope['battles'][0]['details']
            self.assertEqual(displayed['active_crucible'], actual)
            self.assertEqual(displayed['missions'], {
                actual: {'name': 'Fixture challenge', 'kind': 'crucible', 'stage': 1, 'status': 'failed'}})

    def test_all_mission_sources_resolve_to_named_outcomes_and_fossa_honors(self):
        self.modules = {}
        inject = self.inject_module

        def restore_modules():
            for name, original in self.modules.items():
                if original is None:
                    sys.modules.pop(name, None)
                else:
                    sys.modules[name] = original

        self.addCleanup(restore_modules)
        branches = ('regular', 'pm2', 'pm3', 'pm4')
        fossa = Obj(getUserName=lambda: 'Fixture Fossa mission',
                    getUserDescription=lambda: 'Fixture objective',
                    getMainQuestID=lambda: 'fixture_pm4_main',
                    getAddQuestID=lambda: 'fixture_pm4_add',
                    getOperationID=lambda: 11)
        old = Obj(getUserName=lambda: 'Fixture PM2 mission',
                  getMainQuestID=lambda: 'fixture_pm2_main',
                  getAddQuestID=lambda: 'fixture_pm2_add', getOperationID=lambda: 5)
        daily = Obj(getID=lambda: 'dq:fixture', getUserName=lambda: 'Fixture daily',
                    isBonus=lambda: True, bonusCond=Obj(isInRow=lambda: True))
        weekly = Obj(getID=lambda: 'wq::fixture', getUserName=lambda: 'Fixture weekly')
        special = Obj(getID=lambda: 'seasonal:fixture', getUserName=lambda: 'Fixture seasonal')

        def get_quests(requested):
            self.assertEqual(requested, branches)
            return {123: fossa, 456: old}

        def get_operations(requested):
            self.assertEqual(requested, branches)
            return {11: Obj(getUserName=lambda: 'Operation Fossa')}

        quest_cache = Obj(getAllQuests=get_quests, getAllOperations=get_operations)
        cache = Obj(getQuests=lambda predicate: {q.getID(): q for q in (daily, weekly) if predicate(q)},
                    getHiddenQuests=lambda predicate, makeRelations: {
                        special.getID(): special} if predicate(special) else {},
                    getPersonalMissions=lambda: quest_cache)
        ids = {'fixture_pm4_main': 123, 'fixture_pm4_add': 123}
        inject('helpers', dependency=Obj(instance=lambda unused: cache))
        inject('skeletons.gui.server_events', IEventsCache=object())
        inject('personal_missions', PM_BRANCH=Obj(ALL_NAMES=branches),
               g_cache=Obj(isPersonalMission=lambda key: key in ids,
                           getPersonalMissionIDByUniqueID=lambda key: ids[key]))
        inject('gui.server_events.events_helpers',
               isDailyEpicReward=lambda key: 'QUEST_EPIC_REWARD' in key,
               isDailyQuest=lambda key: key.startswith('dq:'),
               isWeeklyQuest=lambda key: key.startswith('wq::'),
               isBattleMattersQuestID=lambda key: key.startswith('battle_matters'),
               isPremium=lambda key: key.startswith('prem_acc'))

        raw = raw_result()
        done = ('fixture', {}, {'bonusCount': 1})
        raw['personal']['avatar']['questsProgress'] = {
            'dq:fixture': ('fixture', {'battlesCount': 3}, {'battlesCount': 0}),
            'dq:QUEST_EPIC_REWARD': done,
            'seasonal:fixture': done,
            'fixture_pm4_main': done,
        }
        raw['personal'][1]['questsProgress'] = {'wq::fixture': done, 'fixture_pm4_add': done}
        raw['personal'][1]['PM2Progress'] = {
            456: {'fixture_pm2_add': False, 'fixture_pm2_main': True, 'technical': True}}
        missions = normalize_result(raw, mission_resolver=game_mission_metadata)['details']['missions']
        self.assertEqual(len(missions), 6)
        self.assertEqual(missions['personal:123'], {
            'kind': 'personal', 'name': 'Fixture Fossa mission', 'operation': 'Operation Fossa',
            'description': 'Fixture objective', 'status': 'honors', 'progress_state': 'unavailable'})
        self.assertEqual(missions['personal:456']['status'], 'completed')
        self.assertEqual(missions['dq:fixture']['kind'], 'daily_bonus')
        self.assertEqual(missions['dq:fixture']['status'], 'reset')
        self.assertEqual(missions['dq:QUEST_EPIC_REWARD']['kind'], 'daily_epic')
        self.assertEqual(missions['wq::fixture']['kind'], 'weekly')
        self.assertEqual(missions['wq::fixture']['status'], 'completed')
        self.assertEqual(missions['seasonal:fixture']['name'], 'Fixture seasonal')

    def test_named_time_points_survive_journal_replay_and_keep_old_points(self):
        self.assertTrue(self.service.create_time_point())
        self.clock.value = 120
        self.assertTrue(self.service.create_time_point('  Zażółć · evening <fixture>  '))
        scope = self.service.timeline_snapshot()
        identifier = scope['time_points'][-1][0]
        self.assertEqual(scope['time_point_names'], {identifier: 'Zażółć · evening <fixture>'})
        self.assertTrue(self.service.set_timeline_range(identifier, ''))
        reopened = self.open_service('named-reopen')
        self.assertTrue(reopened.ready)
        self.assertEqual(reopened.timeline_snapshot()['time_points'], scope['time_points'])
        self.assertEqual(reopened.timeline_snapshot()['time_point_names'], scope['time_point_names'])
        self.assertEqual(self.open_service('separate', 'EU:8').timeline_snapshot()['time_point_names'], {})

    def test_invalid_point_names_do_not_add_a_point_or_change_saved_names(self):
        self.assertTrue(self.service.create_time_point('Valid'))
        before = self.service.timeline_snapshot()
        for name in ('x' * 81, 'embedded\nnewline', 'embedded\x00zero', 123, {}):
            self.assertFalse(self.service.create_time_point(name))
            self.assertEqual(self.service.timeline_snapshot()['time_points'], before['time_points'])
            self.assertEqual(self.service.timeline_snapshot()['time_point_names'], before['time_point_names'])

    def test_battle_and_account_bond_earnings_reach_every_statistics_group_once(self):
        raw = raw_result()
        raw['personal']['avatar'].update(crystal=13, eventCrystal=13)
        raw['personal'][1]['eventCrystal'] = 30  # Already included in the vehicle's 40.
        record = normalize_result(raw)
        self.clock.value = record['started_at'] + 1
        self.service.begin_battle(record['arena_id'], started_at=record['started_at'], mode='random')
        self.assertTrue(self.service.record_result(record))
        installation = InstallationSession(self.directory, self.directory, 'first', EXPECTED, self.clock)
        self.assertTrue(installation.begin('EU:7', record))
        self.assertTrue(installation.result('EU:7', record))
        scopes = [self.service.snapshot()['scopes']['launch'], self.service.timeline_snapshot(),
                  installation.snapshot()[0]]
        for scope in scopes:
            for stats in [scope['summary']] + [scope[group][0]['stats'] for group in ('vehicles', 'maps', 'tiers', 'battles')]:
                bonds = stats['currencies']['bonds']
                self.assertEqual((bonds['income'], bonds['costs'], bonds['net']), (53, 12, 41))
        self.assertEqual(record['details']['bonuses']['eventCrystal'], 43)
        del raw['personal'][1]['crystal']
        del raw['personal']['avatar']['crystal']
        self.assertEqual(normalize_result(raw)['currencies']['bonds']['income'], 53)
