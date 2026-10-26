# -*- coding: utf-8 -*-
"""Real result fixtures with changes in the contract, not battle value baselines."""
from __future__ import unicode_literals

import copy
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src'))
from grz_session_stats.health import inspect_result, MAX_ISSUES, MAX_FIELDS, MAX_RECORDS
from grz_session_stats.normalize import normalize_result
from test_normalize import raw_result


class ResultHealthTests(unittest.TestCase):
    def issues(self, raw, **context):
        values = {'account_dbid': 7}
        values.update(context)
        return inspect_result(raw, values)

    def paths(self, raw):
        return [value['path'] for value in self.issues(raw)]

    def test_current_result_is_healthy_and_read_only(self):
        raw = raw_result()
        before = copy.deepcopy(raw)
        self.assertEqual(self.issues(raw), [])
        self.assertEqual(raw, before)
        self.assertEqual(normalize_result(raw)['currencies']['bonds']['net'], 28)

    def test_changed_battle_values_and_record_identifiers_do_not_learn_or_drift(self):
        first = raw_result()
        second = raw_result(vehicle_id=54289)
        second['personal'][54289].update(damageDealt=0, kills=0, originalXP=100, xp=100)
        second['personal']['avatar']['team'] = 2
        second['common']['winnerTeam'] = 0
        second['vehicles'] = {25: [{'damageDealt': 20}], 67: [{'damageDealt': 2}]}
        second['players'] = {7: {'name': 'private-name', 'team': 2}, 999: {'name': 'other-private-name'}}
        second['avatars'] = {7: {'avatarDamageDealt': 100, 'credits': 50}}
        self.assertEqual(self.issues(first), [])
        self.assertEqual(self.issues(second), [])

    def test_known_conditional_and_random_extension_fields_do_not_alarm(self):
        raw = raw_result()
        raw['personal']['avatar'].update(avatarPlayerSatisfactionRating=(-1, 0.0),
                                         bpChaptersInfo={}, hasBattlePass=False,
                                         questsProgress={'variable-quest-name': {'progress': 3}})
        raw['common']['bonusCapsOverrides'] = {}
        raw['personal'][1]['prestigeResults'] = {}
        raw['personal'][1]['details'] = {'changing-interaction-id': {'irrelevant': []}}
        self.assertEqual(self.issues(raw), [])

    def test_unused_optional_fields_may_be_absent_and_cost_lists_are_supported(self):
        raw = raw_result()
        data = raw['personal'][1]
        for name in ('piggyBank', 'originalCredits', 'originalCrystal',
                     'appliedPremiumCreditsFactor100', 'premSquadCreditsFactor100'):
            del data[name]
        for name in ('autoLoadCost', 'autoEquipCost', 'autoEquipBoostersCost'):
            data[name] = list(data[name])
        self.assertEqual(self.issues(raw), [])
        self.assertEqual(normalize_result(raw)['currencies']['credits']['net'], 32000)

    def test_missing_consumed_fields_are_reported_explicitly(self):
        for name in ('damageDealt', 'kills', 'spotted', 'droppedCapturePoints',
                     'originalXP', 'xp', 'freeXP', 'credits', 'crystal', 'gold',
                     'autoRepairCost', 'autoLoadCost', 'autoEquipCost', 'autoEquipBoostersCost',
                     'originalCreditsToDraw', 'originalCreditsToDrawSquad'):
            raw = raw_result()
            del raw['personal'][1][name]
            self.assertIn('personal.vehicle.' + name, self.paths(raw), name)

    def test_deductions_only_require_factor_when_nonzero(self):
        for name, factor in (('originalCreditsToDraw', 'appliedPremiumCreditsFactor100'),
                             ('originalCreditsToDrawSquad', 'premSquadCreditsFactor100')):
            raw = raw_result()
            del raw['personal'][1][factor]
            self.assertEqual(self.issues(raw), [])
            raw['personal'][1][name] = 10
            self.assertIn('personal.vehicle.' + factor, self.paths(raw))
            self.assertIsNone(normalize_result(raw)['currencies']['credits']['income'])

    def test_booleans_text_nonfinite_and_negative_amounts_are_not_valid_numbers(self):
        raw = raw_result()
        raw['personal'][1].update(damageDealt='secret-value', xp=float('nan'),
                                  originalXP=float('inf'), crystal=True, gold=-2)
        issues = self.issues(raw)
        for name in ('damageDealt', 'xp', 'originalXP', 'crystal', 'gold'):
            self.assertIn('personal.vehicle.' + name, [item['path'] for item in issues])
        serialized = json.dumps(issues)
        self.assertNotIn('secret-value', serialized)
        self.assertNotIn('Infinity', serialized)
        self.assertNotIn('NaN', serialized)

    def test_signed_credit_income_is_valid(self):
        raw = raw_result()
        raw['personal'][1]['credits'] = -10
        self.assertEqual(self.issues(raw), [])
        self.assertLess(normalize_result(raw)['currencies']['credits']['net'], 0)

    def test_integer_transport_changed_to_float_is_visible_without_guessing_values(self):
        raw = raw_result()
        raw['personal'][1]['xp'] = 1950.0
        raw['personal'][1]['autoEquipCost'] = (15000, 5, 12.0)
        issues = self.issues(raw)
        self.assertIn('personal.vehicle.xp', [item['path'] for item in issues])
        self.assertIn('personal.vehicle.autoEquipCost[2]', [item['path'] for item in issues])
        self.assertEqual(normalize_result(raw)['xp_received'], 1950)

    def test_team_and_winner_ranges_are_not_inferred(self):
        raw = raw_result()
        raw['common']['winnerTeam'] = 4
        self.assertIn('common.winnerTeam', self.paths(raw))
        self.assertIsNone(normalize_result(raw)['outcome'])
        raw['common']['winnerTeam'] = 1
        raw['personal']['avatar']['team'] = 4
        self.assertIn('personal.avatar.team', self.paths(raw))
        raw['personal']['avatar']['team'] = True
        self.assertIn('personal.avatar.team', self.paths(raw))

    def test_team_fallback_and_draw_do_not_require_an_unused_avatar_team(self):
        raw = raw_result()
        del raw['personal']['avatar']['team']
        raw['personal'][1]['team'] = 1
        self.assertEqual(self.issues(raw), [])
        del raw['personal'][1]['team']
        self.assertIn('personal.vehicle.team', self.paths(raw))
        raw['common']['winnerTeam'] = 0
        self.assertEqual(self.issues(raw), [])

    def test_unrecognized_envelope_and_common_container_are_detected(self):
        self.assertEqual(inspect_result([])[0]['path'], 'result')
        for name in ('common', 'personal'):
            raw = raw_result()
            raw[name] = []
            self.assertIn('result.' + name, self.paths(raw))
        raw = raw_result()
        raw['personal']['avatar'] = []
        self.assertIn('personal.avatar', self.paths(raw))

    def test_missing_identity_and_uint64_violation_are_detected_without_values(self):
        raw = raw_result()
        secret_id = (1 << 80) + 123
        raw['arenaUniqueID'] = secret_id
        del raw['personal']['avatar']['accountDBID']
        issues = self.issues(raw)
        self.assertIn('result.arenaUniqueID', [item['path'] for item in issues])
        self.assertIn('personal.avatar.accountDBID', [item['path'] for item in issues])
        self.assertNotIn(str(secret_id), json.dumps(issues))

    def test_vehicle_identity_can_use_compact_key_but_conflicts_are_reported(self):
        raw = raw_result()
        del raw['personal'][1]['typeCompDescr']
        self.assertEqual(self.issues(raw), [])
        raw['personal'][1]['typeCompDescr'] = 54289
        self.assertIn('personal.vehicle.typeCompDescr', self.paths(raw))

    def test_multiple_personal_vehicles_use_only_an_unambiguous_context(self):
        raw = raw_result()
        raw['personal'][2] = dict(raw['personal'][1], typeCompDescr=2, damageDealt=300)
        self.assertTrue(any(x['code'] == 'unresolved_vehicle' for x in self.issues(raw)))
        self.assertEqual(self.issues(raw, vehicle_id=2), [])

    def test_other_account_and_unsupported_modes_are_excluded_before_format_alarms(self):
        raw = raw_result(dbid=8)
        raw['common'] = []
        raw['newSchemaField'] = 'private-value'
        self.assertEqual(self.issues(raw), [])
        for mode in (3, 24, 46):
            raw = {'common': {'bonusType': mode}, 'anythingChanged': object()}
            self.assertEqual(self.issues(raw), [])
        self.assertEqual(inspect_result([], {'replay': True}), [])

    def test_unknown_fields_are_reported_but_do_not_discard_healthy_performance(self):
        raw = raw_result()
        raw['newEnvelopeField'] = {'private': 'value'}
        raw['common']['newCommonField'] = 900
        raw['personal']['avatar']['newAvatarField'] = 'private-name'
        raw['personal'][1]['newVehicleField'] = [1, 2, 3]
        issues = self.issues(raw)
        self.assertEqual(len(issues), 4)
        self.assertTrue(all(item['code'] == 'unknown_field' for item in issues))
        self.assertNotIn('private', json.dumps(issues))
        record = normalize_result(raw, {'account_dbid': 7})
        self.assertEqual(record['damage'], 2100)
        self.assertEqual(record['currencies']['bonds']['net'], 28)

    def test_arbitrary_field_names_are_redacted_and_output_is_bounded(self):
        raw = raw_result()
        raw['sensitive' + chr(64) + 'example.com'] = 'secret'
        raw['x' * 3000] = {'secret': 'value'}
        issues = self.issues(raw)
        dumped = json.dumps(issues)
        self.assertNotIn('sensitive', dumped)
        self.assertNotIn('secret', dumped)
        self.assertLess(len(dumped), 500)
        for i in range(100):
            raw['newField{0}'.format(i)] = object()
        issues = self.issues(raw)
        self.assertLessEqual(len(issues), MAX_ISSUES)
        self.assertEqual(issues[-1]['code'], 'inspection_limit')

    def test_oversized_mappings_stop_bounded_scans(self):
        raw = raw_result()
        for i in range(MAX_FIELDS + 1):
            raw['newField{0}'.format(i)] = object()
        self.assertTrue(any(x['code'] == 'inspection_limit' and x['path'] == 'result' for x in self.issues(raw)))
        raw = raw_result()
        raw['vehicles'] = dict((i + 1, []) for i in range(MAX_RECORDS + 1))
        self.assertTrue(any(x['code'] == 'inspection_limit' and x['path'] == 'vehicles' for x in self.issues(raw)))

    def test_other_record_containers_detect_drift_without_exposing_dynamic_keys(self):
        raw = raw_result()
        raw['players'] = {123456789: []}
        raw['avatars'] = []
        raw['vehicles'] = {987654321: {'changedContainer': True}}
        issues = self.issues(raw)
        self.assertTrue(any(x['path'] == 'players.<record>' for x in issues))
        self.assertTrue(any(x['path'] == 'result.avatars' for x in issues))
        self.assertTrue(any(x['path'] == 'vehicles.<record>' for x in issues))
        self.assertNotIn('123456789', json.dumps(issues))
        self.assertNotIn('987654321', json.dumps(issues))

    def test_unused_record_keys_allow_zero_and_negative_ids_without_relaxing_own_identity(self):
        for record_id in (0, -17, '0', '-17'):
            raw = raw_result()
            raw['players'] = {record_id: {'name': 'not-logged'}}
            raw['avatars'] = {record_id: {'avatarDamageDealt': 0}}
            raw['vehicles'] = {record_id: [{'damageDealt': 0}]}
            self.assertEqual(self.issues(raw), [])
        for section, field, path in (('result', 'arenaUniqueID', 'result.arenaUniqueID'),
                                     ('avatar', 'accountDBID', 'personal.avatar.accountDBID'),
                                     ('vehicle', 'typeCompDescr', 'personal.vehicle.typeCompDescr')):
            raw = raw_result()
            target = raw if section == 'result' else raw['personal']['avatar' if section == 'avatar' else 1]
            target[field] = 0
            self.assertIn(path, self.paths(raw))
        raw = raw_result()
        raw['players'] = {'not-an-id': {}}
        self.assertTrue(any(x['code'] == 'invalid_key' for x in self.issues(raw)))

    def test_extended_or_short_financial_tuples_are_never_read_by_old_positions(self):
        for name, width in (('autoLoadCost', 2), ('autoEquipCost', 3), ('autoEquipBoostersCost', 3)):
            for changed in ((1,) * (width + 1), (1,) * (width - 1)):
                raw = raw_result()
                raw['personal'][1][name] = changed
                self.assertIn('personal.vehicle.' + name, self.paths(raw))
                record = normalize_result(raw)
                self.assertEqual(record['damage'], 2100)
                self.assertEqual(record['xp_base'], 650)
                if name == 'autoEquipCost':
                    self.assertTrue(all(x['costs'] is None and x['net'] is None
                                        for x in record['currencies'].values()))
                elif name == 'autoLoadCost':
                    self.assertIsNone(record['currencies']['credits']['net'])
                    self.assertIsNone(record['currencies']['gold']['net'])
                    self.assertEqual(record['currencies']['bonds']['net'], 28)
                else:
                    self.assertIsNone(record['currencies']['credits']['breakdown']['directives'])
                    self.assertEqual(record['currencies']['credits']['net'], 32000)

    def test_unknown_one_currency_amount_does_not_remove_other_confirmed_amounts(self):
        raw = raw_result()
        raw['personal'][1]['autoEquipCost'] = (15000, 5, None)
        self.assertIn('personal.vehicle.autoEquipCost[2]', self.paths(raw))
        record = normalize_result(raw)
        self.assertIsNone(record['currencies']['bonds']['net'])
        self.assertEqual(record['currencies']['credits']['net'], 32000)
        self.assertEqual(record['currencies']['gold']['net'], 1)

    def test_changed_financial_mapping_and_inconsistent_directives_are_explicit(self):
        raw = raw_result()
        raw['personal'][1]['autoEquipCost'] = {'credits': 15000, 'gold': 5, 'bonds': 12}
        self.assertIn('personal.vehicle.autoEquipCost', self.paths(raw))
        self.assertIsNone(normalize_result(raw)['currencies']['bonds']['net'])
        raw = raw_result()
        raw['personal'][1]['autoEquipBoostersCost'] = (5000, 0, 13)
        self.assertTrue(any(x['code'] == 'inconsistent_costs' for x in self.issues(raw)))

    def test_unsupported_objects_are_never_stringified(self):
        class DoNotPrint(object):
            def __repr__(self):
                raise AssertionError('payload repr must never be called')
            __str__ = __repr__
        raw = raw_result()
        raw['personal'][1]['xp'] = DoNotPrint()
        issues = self.issues(raw)
        self.assertEqual([x['actual'] for x in issues if x['path'] == 'personal.vehicle.xp'],
                         ['unsupported object'])


if __name__ == '__main__':
    unittest.main()

