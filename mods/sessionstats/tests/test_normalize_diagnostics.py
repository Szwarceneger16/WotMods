# -*- coding: utf-8 -*-
"""Normalization diagnostics expose finite codes, never payload data."""
from __future__ import unicode_literals

import copy
import unittest

from test_normalize import raw_result
from grz_session_stats.normalize import normalize_result, report_diagnostics


class NormalizationDiagnosticTests(unittest.TestCase):
    def rejected(self, raw, reason, context=None, ignored=False):
        before = copy.deepcopy(raw)
        diagnostic = {'raw': 'must be cleared'}
        self.assertIsNone(normalize_result(raw, context, diagnostics=diagnostic))
        self.assertEqual(diagnostic, {'reason': reason, 'ignored': ignored})
        self.assertEqual(raw, before)

    def test_rejection_codes_distinguish_identity_mode_and_structure(self):
        self.rejected([], 'invalid_container')
        self.rejected({'common': []}, 'invalid_common')
        raw = raw_result()
        raw['common']['bonusType'] = 24
        self.rejected(raw, 'unsupported_mode', ignored=True)
        self.rejected(raw_result(), 'replay', {'replay': True}, ignored=True)
        self.rejected(raw_result(), 'wrong_account', {'account_dbid': 8}, ignored=True)
        raw = raw_result()
        del raw['personal']['avatar']['accountDBID']
        self.rejected(raw, 'account_missing', {'account_dbid': 7})
        raw = raw_result()
        del raw['arenaUniqueID']
        self.rejected(raw, 'missing_arena_id')
        raw = raw_result()
        raw['personal'] = []
        self.rejected(raw, 'invalid_personal')
        raw = raw_result()
        raw['personal']['avatar'] = []
        self.rejected(raw, 'invalid_avatar')
        raw = raw_result()
        del raw['personal'][1]
        self.rejected(raw, 'missing_vehicle')
        self.rejected(raw_result(), 'vehicle_mismatch', {'vehicle_id': 2})

    def test_single_wrong_vehicle_is_not_used_to_revise_saved_battle(self):
        self.assertIsNone(normalize_result(raw_result(vehicle_id=2),
                                          {'account_dbid': 7, 'vehicle_id': 1}))

    def test_outcome_missing_distinguishes_winner_and_own_team(self):
        for field, target, reason in (('winnerTeam', 'common', 'winner_missing'),
                                      ('team', 'avatar', 'team_missing')):
            raw = raw_result()
            del (raw['common'] if target == 'common' else raw['personal']['avatar'])[field]
            diagnostic = {}
            record = normalize_result(raw, {'account_dbid': 7}, diagnostics=diagnostic)
            self.assertIsNotNone(record)
            self.assertIsNone(record['outcome'])
            self.assertFalse(record['complete'])
            self.assertEqual(diagnostic, {'reason': reason, 'ignored': False})
            self.assertEqual(report_diagnostics(record, result_seen=True)['report_status'], 'outcome_missing')

    def test_partial_combat_xp_finance_are_independent_of_outcome(self):
        for field, reason in (('damageDealt', 'missing_combat'), ('xp', 'missing_xp'),
                              ('autoEquipCost', 'missing_finance')):
            raw = raw_result()
            del raw['personal'][1][field]
            diagnostic = {}
            record = normalize_result(raw, diagnostics=diagnostic)
            self.assertEqual(record['outcome'], 'win')
            self.assertFalse(record['complete'])
            self.assertEqual(diagnostic, {'reason': reason, 'ignored': False})
            self.assertEqual(report_diagnostics(record, result_seen=True),
                             {'report_status': 'partial_report', 'reason': reason})

    def test_malformed_context_is_bounded_and_does_not_escape(self):
        self.rejected(raw_result(), 'malformed_structure', ['private-unexpected-value'])

    def test_complete_record_and_draw_without_team(self):
        raw = raw_result()
        raw['common']['winnerTeam'] = 0
        del raw['personal']['avatar']['team']
        diagnostic = {}
        record = normalize_result(raw, diagnostics=diagnostic)
        self.assertTrue(record['complete'])
        self.assertEqual(record['outcome'], 'draw')
        self.assertEqual(diagnostic, {'reason': 'complete', 'ignored': False})


if __name__ == '__main__':
    unittest.main()
