# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import copy
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src'))
from grz_session_stats.normalize import arena_start, normalize_result, normalize_currencies


START = 1700000010
ARENA_ID = str((12345 << 32) | START)


def raw_result(arena_id=ARENA_ID, dbid=7, vehicle_id=1):
    return {
        'arenaUniqueID': int(arena_id),
        'common': {'bonusType': 1, 'winnerTeam': 1, 'arenaTypeID': 17, 'duration': 400},
        'personal': {
            'avatar': {'accountDBID': dbid, 'team': 1},
            vehicle_id: {
                'typeCompDescr': vehicle_id, 'damageDealt': 2100, 'kills': 2,
                'spotted': 1, 'droppedCapturePoints': 8,
                'originalXP': 650, 'xp': 1950, 'freeXP': 98,
                'originalCredits': 20000, 'credits': 75000,
                'originalCreditsToDraw': 0, 'originalCreditsToDrawSquad': 0,
                'appliedPremiumCreditsFactor100': 150, 'premSquadCreditsFactor100': 110,
                'autoRepairCost': 10000, 'autoLoadCost': (18000, 0),
                'autoEquipCost': (15000, 5, 12),
                'autoEquipBoostersCost': (5000, 0, 12),
                'originalCrystal': 10, 'crystal': 40, 'gold': 6,
                'piggyBank': 3500,
            },
        },
        # The much better teammate must never influence our statistics.
        'vehicles': {90: [{'damageDealt': 99999, 'typeCompDescr': 99}]},
    }


class NormalizerTests(unittest.TestCase):
    def test_base_and_awarded_xp_are_distinct_and_never_multiplied_twice(self):
        value = normalize_result(raw_result(), {'account_dbid': 7})
        self.assertEqual(value['xp_base'], 650)
        self.assertEqual(value['xp_received'], 1950)
        self.assertEqual(value['free_xp'], 98)
        self.assertEqual(value['damage'], 2100)
        self.assertEqual(value['vehicle_id'], 1)
        self.assertTrue(value['complete'])
        self.assertTrue(value['reconcile'])
        self.assertFalse(value['xp_bonus_applied'])

    def test_bonds_and_gold_include_income_and_auto_supply_costs(self):
        money = normalize_result(raw_result())['currencies']
        self.assertEqual(money['bonds'], {'income': 40, 'costs': 12, 'net': 28})
        self.assertEqual(money['gold'], {'income': 6, 'costs': 5, 'net': 1})

    def test_directives_are_not_counted_twice_and_bank_is_not_spendable(self):
        record = normalize_result(raw_result())
        money = record['currencies']['credits']
        self.assertEqual(money['income'], 75000)
        self.assertEqual(money['costs'], 43000)
        self.assertEqual(money['net'], 32000)
        self.assertEqual(money['breakdown'], {'repair': 10000, 'ammo': 18000,
                                             'consumables': 10000, 'directives': 5000})
        self.assertTrue(any('Deferred credits' in item for item in record['warnings']))

    def test_credit_replay_rounds_first_deduction_but_preserves_subcoeff(self):
        raw = raw_result()
        personal = raw['personal'][1]
        personal['originalCreditsToDraw'] = 1
        personal['originalCreditsToDrawSquad'] = 1
        # Native makeReplayValueRound(1*1.5) => 2; SUBCOEFF(1*1.1) => 1.1.
        record = normalize_result(raw)
        self.assertAlmostEqual(record['currencies']['credits']['income'], 74996.9)
        self.assertAlmostEqual(record['currencies']['credits']['net'], 31996.9)

    def test_large_deduction_can_make_income_and_net_negative(self):
        raw = raw_result()
        raw['personal'][1]['credits'] = 100
        raw['personal'][1]['originalCreditsToDraw'] = 1000
        record = normalize_result(raw)
        self.assertEqual(record['currencies']['credits']['income'], -1400)
        self.assertEqual(record['currencies']['credits']['net'], -44400)

    def test_missing_money_is_unknown_and_does_not_discard_battle_performance(self):
        raw = raw_result()
        del raw['personal'][1]['crystal']
        record = normalize_result(raw)
        self.assertEqual(record['outcome'], 'win')
        self.assertEqual(record['damage'], 2100)
        self.assertIsNone(record['currencies']['bonds']['income'])
        self.assertIsNone(record['currencies']['bonds']['net'])
        self.assertEqual(record['currencies']['bonds']['costs'], 12)
        self.assertFalse(record['complete'])

    def test_missing_expense_does_not_become_zero(self):
        raw = raw_result()
        del raw['personal'][1]['autoEquipCost']
        record = normalize_result(raw)
        for currency in ('credits', 'bonds', 'gold'):
            self.assertIsNone(record['currencies'][currency]['costs'])
            self.assertIsNone(record['currencies'][currency]['net'])

    def test_missing_squad_deduction_prevents_false_credit_total(self):
        raw = raw_result()
        del raw['personal'][1]['originalCreditsToDraw']
        record = normalize_result(raw)
        self.assertIsNone(record['currencies']['credits']['income'])
        self.assertEqual(record['currencies']['credits']['costs'], 43000)
        self.assertFalse(record['complete'])

    def test_zero_directives_does_not_require_a_missing_multiplier(self):
        raw = raw_result()
        del raw['personal'][1]['appliedPremiumCreditsFactor100']
        del raw['personal'][1]['premSquadCreditsFactor100']
        self.assertEqual(normalize_result(raw)['currencies']['credits']['income'], 75000)

    def test_personal_keys_are_compact_descriptors_not_arena_entity_ids(self):
        raw = raw_result(vehicle_id=54289)
        del raw['personal'][54289]['typeCompDescr']
        record = normalize_result(raw)
        self.assertEqual(record['vehicle_id'], 54289)
        self.assertEqual(record['damage'], 2100)

    def test_ambiguous_personal_vehicle_requires_captured_descriptor(self):
        raw = raw_result()
        raw['personal'][2] = dict(raw['personal'][1], typeCompDescr=2, damageDealt=50)
        self.assertIsNone(normalize_result(raw))
        record = normalize_result(raw, {'vehicle_id': 2})
        self.assertEqual(record['vehicle_id'], 2)
        self.assertEqual(record['damage'], 50)

    def test_account_mismatch_missing_identity_and_replays_are_rejected(self):
        self.assertIsNone(normalize_result(raw_result(), {'account_dbid': 8}))
        self.assertIsNone(normalize_result(raw_result(), {'account_dbid': 7, 'replay': True}))
        raw = raw_result()
        del raw['personal']['avatar']['accountDBID']
        self.assertIsNone(normalize_result(raw, {'account_dbid': 7}))

    def test_unsupported_random_variants_and_special_modes_are_excluded(self):
        for bonus_type in (0, 24, 46, 3, None):
            raw = raw_result()
            raw['common']['bonusType'] = bonus_type
            self.assertIsNone(normalize_result(raw))

    def test_draw_is_countable_but_unknown_outcome_is_not_invented(self):
        raw = raw_result()
        raw['common']['winnerTeam'] = 0
        self.assertEqual(normalize_result(raw)['outcome'], 'draw')
        raw['common']['winnerTeam'] = 2
        self.assertEqual(normalize_result(raw)['outcome'], 'loss')
        del raw['common']['winnerTeam']
        record = normalize_result(raw)
        self.assertIsNone(record['outcome'])
        self.assertFalse(record['complete'])

    def test_server_arena_time_wins_over_receive_or_context_time(self):
        record = normalize_result(raw_result(), {'started_at': START + 9999})
        self.assertEqual(record['started_at'], START)
        self.assertEqual(record['ended_at'], START + 400)
        self.assertEqual(arena_start(ARENA_ID), START)
        self.assertIsNone(arena_start('12'))
        self.assertIsNone(arena_start(-1))

    def test_resolvers_preserve_polish_names_and_stable_map_geometry(self):
        record = normalize_result(raw_result(), vehicle_resolver=lambda cd: {
            'name': 'Czołg próbny', 'tier': 8, 'type': 'heavyTank'},
            map_resolver=lambda ident: {'id': '17_map', 'name': 'Święta dolina'})
        self.assertEqual(record['vehicle_name'], 'Czołg próbny')
        self.assertEqual(record['vehicle_type'], 'heavyTank')
        self.assertEqual(record['vehicle_tier'], 8)
        self.assertEqual(record['map_id'], '17_map')
        self.assertEqual(record['map_name'], 'Święta dolina')

    def test_resolver_failure_keeps_result_with_explicit_fallback(self):
        def fail(value):
            raise AttributeError('changed client metadata API')
        record = normalize_result(raw_result(), vehicle_resolver=fail, map_resolver=fail)
        self.assertEqual(record['vehicle_name'], 'Vehicle 1')
        self.assertEqual(record['map_id'], 'arena:17')
        self.assertEqual(record['damage'], 2100)
        self.assertTrue(record['warnings'])

    def test_invalid_numbers_are_unknown_and_input_is_not_mutated(self):
        raw = raw_result()
        raw['personal'][1]['damageDealt'] = float('nan')
        raw['personal'][1]['xp'] = float('inf')
        raw['personal'][1]['crystal'] = True
        raw['personal'][1]['gold'] = -3
        record = normalize_result(raw)
        self.assertIsNone(record['damage'])
        self.assertIsNone(record['xp_received'])
        self.assertIsNone(record['currencies']['bonds']['income'])
        self.assertIsNone(record['currencies']['gold']['income'])
        ordinary = raw_result()
        before = copy.deepcopy(ordinary)
        normalize_result(ordinary)
        self.assertEqual(ordinary, before)


if __name__ == '__main__':
    unittest.main()
