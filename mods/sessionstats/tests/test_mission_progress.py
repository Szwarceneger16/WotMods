# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import copy
import shutil
import sys
import tempfile
import unittest

from test_core import Clock, EXPECTED, result
import test_runtime as runtime_fixtures
from test_runtime import Obj
from test_normalize import raw_result
from grz_session_stats.battle_details import (
    _common_objectives, _personal_mission_rows, clean_details, merge_details, result_details)
from grz_session_stats.core import StatsService
from grz_session_stats.normalize import normalize_result


class MissionProgressTests(unittest.TestCase):
    inject_module = runtime_fixtures.NativeBindingTests.__dict__['inject_module']

    def quest(self, *conditions):
        return Obj(bonusCond=Obj(getConditions=lambda: Obj(items=list(conditions))))

    def condition(self, key, target, packed=None, event_count=False):
        def progress(current, previous, battle):
            self.assertTrue(battle)
            self.assertEqual(list(current), ['vehicle-group'])
            current, previous = current['vehicle-group'], previous['vehicle-group']
            values = packed if packed is not None else (
                current[key], target, current[key] - previous[key], False)
            return {'vehicle-group': values}
        return Obj(getKey=lambda: key, getProgressPerGroup=progress,
                   getUserString=lambda: '<b>Fixture objective</b>',
                   isEventCount=lambda: event_count)

    def ordinary(self, previous, current, *conditions):
        def resolve(rows):
            _common_objectives(self.quest(*conditions), rows['fixture:quest'])
        return result_details({'questsProgress': {
            'fixture:quest': ('vehicle-group', previous, current)}}, {},
            mission_resolver=resolve)['missions']['fixture:quest']

    def test_native_damage_kills_and_xp_have_real_deltas_and_targets(self):
        previous = dict(vehicleDamage=1000, vehicleKills=2, xp=100)
        current = dict(vehicleDamage=2400, vehicleKills=3, xp=750)
        row = self.ordinary(previous, current, self.condition('vehicleDamage', 5000),
                            self.condition('vehicleKills', 5), self.condition('xp', 1000))
        self.assertEqual(row['status'], 'progress')
        self.assertEqual(row['progress_state'], 'changed')
        self.assertEqual([(item['unit'], item['before'], item['after'], item['delta'], item['target'])
                          for item in row['objectives']],
                         [('damage', 1000, 2400, 1400, 5000), ('kills', 2, 3, 1, 5),
                          ('xp', 100, 750, 650, 1000)])
        self.assertEqual(row['objectives'][0]['label'], 'Fixture objective')

    def test_native_repeat_completion_uses_earned_value_instead_of_raw_reset(self):
        row = self.ordinary(dict(vehicleDamage=4800, bonusCount=0),
                            dict(vehicleDamage=0, bonusCount=1),
                            self.condition('vehicleDamage', 5000, (5000, 5000, 200, True)))
        self.assertEqual(row['status'], 'completed')
        self.assertEqual(row['objectives'][0]['before'], 4800)
        self.assertEqual(row['objectives'][0]['after'], 5000)
        self.assertEqual(row['objectives'][0]['delta'], 200)

    def test_explicit_unchanged_zero_is_no_progress_not_unknown(self):
        row = self.ordinary({'vehicleKills': 0}, {'vehicleKills': 0}, self.condition('vehicleKills', 5))
        self.assertEqual(row['progress_state'], 'unchanged')
        self.assertEqual(row['objectives'][0]['delta'], 0)
        self.assertEqual(row['status'], 'observed')

    def test_missing_previous_counter_is_not_an_invented_zero(self):
        row = self.ordinary({}, {'vehicleKills': 2}, self.condition('vehicleKills', 5))
        self.assertEqual(row['progress_state'], 'unavailable')
        self.assertEqual(row['status'], 'observed')
        self.assertNotIn('objectives', row)
        row = result_details({'questsProgress': {'fixture:quest': (
            None, {}, {'battlesCount': 2})}}, {})['missions']['fixture:quest']
        self.assertNotIn('before', row)
        self.assertNotIn('objectives', row)

    def test_partial_objective_set_cannot_confirm_no_progress(self):
        row = self.ordinary({'vehicleKills': 0}, {'vehicleKills': 0},
                            self.condition('vehicleKills', 5), self.condition('vehicleDamage', 5000))
        self.assertEqual(row['progress_state'], 'unavailable')
        self.assertEqual(row['objectives'][0]['delta'], 0)

    def test_technical_dictionary_changes_and_pm_booleans_do_not_claim_progress(self):
        rows = result_details({'questsProgress': {'fixture:quest': (
            None, {'technical': 1}, {'technical': 2})},
            'PM2Progress': {123: {'fixture_main': False, 'technical': True}}}, {})['missions']
        for key in ('fixture:quest', 'personal:123'):
            self.assertEqual(rows[key]['status'], 'observed')
            self.assertEqual(rows[key]['progress_state'], 'unavailable')
            self.assertNotIn('objectives', rows[key])

    def test_event_damage_count_is_not_labelled_hit_points(self):
        row = self.ordinary({'vehicleDamage': 1}, {'vehicleDamage': 3},
                            self.condition('vehicleDamage', 5, event_count=True))
        self.assertEqual(row['objectives'][0]['unit'], 'counter')

    def test_native_stun_seconds_and_streak_reset_keep_their_meaning(self):
        row = self.ordinary({'vehicleStun': 4.5}, {'vehicleStun': 8.5},
                            self.condition('vehicleStun', 30))
        self.assertEqual(row['objectives'][0]['unit'], 'seconds')
        self.assertEqual(row['objectives'][0]['delta'], 4)
        condition = self.condition('vehicleKills', 5)
        quest = self.quest(condition)
        quest.bonusCond.isInRow = lambda: True
        def resolve(rows):
            _common_objectives(quest, rows['fixture:quest'])
        row = result_details({'questsProgress': {'fixture:quest': (
            'vehicle-group', {'vehicleKills': 3}, {'vehicleKills': 0})}}, {},
            mission_resolver=resolve)['missions']['fixture:quest']
        self.assertEqual(row['status'], 'reset')
        self.assertEqual(row['objectives'][0]['delta'], -3)

    def test_battle_and_unique_vehicle_counters_require_both_result_values(self):
        row = result_details({'questsProgress': {'fixture:quest': (
            None, {'battlesCount': 3, 'battlesUniqueVehicles': {1: True}},
            {'battlesCount': 4, 'battlesUniqueVehicles': {1: True, 2: True}})}}, {})['missions']['fixture:quest']
        self.assertEqual([(item['unit'], item['delta']) for item in row['objectives']],
                         [('battles', 1), ('vehicles', 1)])
        row = result_details({'questsProgress': {'fixture:quest': (
            None, {}, {'battlesUniqueVehicles': {2: True}})}}, {})['missions']['fixture:quest']
        self.assertNotIn('objectives', row)

    def personal(self, current, config, values, completed=False):
        module_name = 'gui.server_events.personal_progress.storage'

        class Storage(object):
            def __init__(self, unused, configuration, supplied, one_battle):
                configuration['fixture']['config']['native_mutation'] = True
            def getBodyProgresses(self):
                return values

        self.modules = {}
        self.inject_module(module_name, PostBattleProgressStorage=Storage)
        def restore_modules():
            for name, original in self.modules.items():
                if original is None:
                    sys.modules.pop(name, None)
                else:
                    sys.modules[name] = original
        self.addCleanup(restore_modules)
        quest = Obj(getConditionsConfig=lambda: config, getGeneralQuestID=lambda: 'fixture',
                    isOneBattleQuest=lambda: False, getMainQuestID=lambda: 'main',
                    getAddQuestID=lambda: 'add', getOperationID=lambda: 5,
                    getUserName=lambda: 'Fixture personal mission')
        def resolve(rows):
            _personal_mission_rows(rows, {'personal:123': 123}, {123: quest}, {})
        return result_details({'PM2Progress': {123: dict(current=current, main=completed, add=completed)}}, {},
                              mission_resolver=resolve)['missions']['personal:123']

    def test_pm_current_and_target_are_not_misrepresented_as_a_battle_delta(self):
        config = {'fixture': {'config': {'goal': 5000}}}
        original = copy.deepcopy(config)
        row = self.personal({'fixture': {'state': 1, 'value': 1200}}, config, {
            'fixture': Obj(getCurrent=lambda: 1200, getGoal=lambda: 5000,
                           getDescription=lambda: 'Fixture damage objective')}, completed=True)
        self.assertEqual(row['status'], 'honors')
        self.assertEqual(row['progress_state'], 'unavailable')
        self.assertEqual(row['objectives'][0]['after'], 1200)
        self.assertEqual(row['objectives'][0]['target'], 5000)
        self.assertNotIn('delta', row['objectives'][0])
        self.assertNotIn('before', row['objectives'][0])
        self.assertEqual(config, original)

    def test_pm_omitted_progress_does_not_leak_native_zero_defaults(self):
        config = {'fixture': {'config': {'goal': 5}}, 'missing': {'config': {'goal': 5}}}
        zero = Obj(getCurrent=lambda: 0, getGoal=lambda: 5, getDescription=lambda: 'Fixture counter')
        row = self.personal({'fixture': {'state': 1, 'value': 0}}, config,
                            {'fixture': zero, 'missing': zero})
        self.assertEqual(len(row['objectives']), 1)
        self.assertEqual(row['objectives'][0]['key'], 'pm:fixture')
        self.assertEqual(row['objectives'][0]['after'], 0)
        self.assertEqual(row['progress_state'], 'unavailable')

    def test_pm_missing_dynamic_goal_keeps_explicit_current_without_fake_zero_target(self):
        row = self.personal({'fixture': {'state': 1, 'value': 1200}},
                            {'fixture': {'config': {'dynamicGoal': True}}}, {
                                'fixture': Obj(getCurrent=lambda: 0, getGoal=lambda: 0,
                                               getDescription=lambda: 'Fixture objective')})
        self.assertEqual(row['objectives'][0]['after'], 1200)
        self.assertNotIn('target', row['objectives'][0])

    def test_legacy_unknown_and_cleaner_bounds_are_preserved(self):
        old = {'missions': {'fixture:quest': {'status': 'progress', 'name': 'Legacy'}}}
        self.assertEqual(clean_details(old), old)
        items = [dict(key='objective' + str(index), unit='damage', after=1, delta=-1,
                      label='<b>Safe</b>', target=float('nan')) for index in range(30)]
        clean = clean_details({'missions': {'fixture:quest': {'objectives': items}}})['missions']['fixture:quest']
        self.assertEqual(len(clean['objectives']), 12)
        self.assertEqual(clean['objectives'][0], dict(key='objective0', unit='damage', after=1,
                                                    delta=-1, label='Safe'))

    def test_partial_retry_cannot_erase_known_objectives_or_completion(self):
        old = {'missions': {'fixture:quest': dict(status='honors', progress_state='changed',
                objectives=[dict(key='vehicleKills', unit='kills', before=1, after=2, delta=1)])}}
        incoming = {'missions': {'fixture:quest': dict(status='observed', progress_state='unavailable')}}
        self.assertEqual(merge_details(old, incoming, True), old)

    def test_metadata_retry_enriches_objectives_without_erasing_other_known_counters(self):
        old = {'missions': {'fixture:quest': dict(status='progress', progress_state='changed',
                objectives=[dict(key='battlesCount', unit='battles', before=1, after=2, delta=1)])}}
        incoming = {'missions': {'fixture:quest': dict(status='progress', progress_state='changed',
                objectives=[dict(key='vehicleDamage', unit='damage', before=100, after=500, delta=400)])}}
        for revise in (False, True):
            row = merge_details(old, incoming, revise)['missions']['fixture:quest']
            self.assertEqual([item['key'] for item in row['objectives']], ['battlesCount', 'vehicleDamage'])
            self.assertEqual(row['progress_state'], 'changed')

    def test_normalized_reconcile_without_resolver_preserves_known_objective_metadata(self):
        directory = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, directory)
        raw = raw_result()
        raw['personal'][1]['questsProgress'] = {
            'fixture:quest': ('vehicle-group', {'battlesCount': 1}, {'battlesCount': 2})}
        def resolve(rows):
            _common_objectives(self.quest(self.condition('battlesCount', 7)), rows['fixture:quest'])
        first = normalize_result(raw, mission_resolver=resolve)
        clock = Clock(first['started_at'] - 10)
        service = StatsService(directory, 'EU:7', 'first', EXPECTED, now=clock)
        clock.value = first['ended_at'] + 1
        self.assertTrue(service.record_result(first))
        expected = first['details']['missions']['fixture:quest']['objectives'][0]
        self.assertEqual(expected['label'], 'Fixture objective')
        self.assertEqual(expected['target'], 7)

        # The result retry still knows the battle counter; only the optional
        # mission catalog/resolver is now unavailable.
        retry = normalize_result(raw)
        self.assertTrue(retry['reconcile'])
        self.assertNotIn('label', retry['details']['missions']['fixture:quest']['objectives'][0])
        self.assertNotIn('target', retry['details']['missions']['fixture:quest']['objectives'][0])
        service.record_result(retry)
        stored = service.snapshot()['scopes']['manual']['battles'][0]['details']['missions']['fixture:quest']
        self.assertEqual(stored['objectives'][0], expected)

        raw['personal'][1]['questsProgress']['fixture:quest'] = (
            'vehicle-group', {'battlesCount': 1}, {'battlesCount': 3})
        self.assertTrue(service.record_result(normalize_result(raw)))
        stored = service.snapshot()['scopes']['manual']['battles'][0]['details']['missions']['fixture:quest']
        self.assertEqual(stored['objectives'][0], dict(expected, after=3, delta=2))

    def test_objective_fields_enrich_without_revision_and_explicit_revision_can_replace_them(self):
        original = dict(key='battlesCount', unit='battles', before=1, after=2, delta=1,
                        label='Fixture objective', target=7)
        revised = dict(key='battlesCount', unit='counter', after=0, delta=-1,
                       label='Revised fixture objective', target=0)
        old = {'missions': {'fixture:quest': dict(status='progress', progress_state='changed',
                                                 objectives=[original])}}
        incoming = {'missions': {'fixture:quest': dict(status='progress', progress_state='changed',
                                                      objectives=[revised])}}
        saved = copy.deepcopy(old)
        partial = copy.deepcopy(old)
        del partial['missions']['fixture:quest']['objectives'][0]['label']
        del partial['missions']['fixture:quest']['objectives'][0]['target']
        self.assertEqual(merge_details(partial, incoming, False)['missions']['fixture:quest']['objectives'],
                         [dict(original, label=revised['label'], target=0)])
        self.assertEqual(merge_details(old, incoming, False)['missions']['fixture:quest']['objectives'], [original])
        self.assertEqual(merge_details(old, incoming, True)['missions']['fixture:quest']['objectives'],
                         [dict(original, **revised)])
        self.assertEqual(old, saved)

    def test_objectives_survive_journal_reopen(self):
        directory = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, directory)
        details = result_details({'questsProgress': {'fixture:quest': (
            None, {'battlesCount': 2}, {'battlesCount': 3})}}, {})
        clock = Clock(100)
        service = StatsService(directory, 'EU:7', 'first', EXPECTED, now=clock)
        clock.value = 120
        self.assertTrue(service.record_result(result(details=details)))
        clock.value = 130
        reopened = StatsService(directory, 'EU:7', 'second', EXPECTED, now=clock)
        self.assertEqual(reopened.snapshot()['scopes']['manual']['battles'][0]['details'], details)

    def test_teammate_quest_data_is_never_used(self):
        raw = raw_result()
        raw['vehicles'][90][0]['questsProgress'] = {'teammate:quest': (None, {'battlesCount': 0}, {'battlesCount': 99})}
        raw['personal'][1]['questsProgress'] = {'own:quest': (None, {'battlesCount': 1}, {'battlesCount': 2})}
        missions = normalize_result(raw)['details']['missions']
        self.assertEqual(set(missions), {'own:quest'})
        self.assertEqual(missions['own:quest']['objectives'][0]['delta'], 1)
