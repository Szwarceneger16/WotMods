# -*- coding: utf-8 -*-
"""Keep known 0.9.8 statistics while newer metrics and reports are added."""
from __future__ import unicode_literals

import copy
import io
import json
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src'))
from grz_session_stats.core import StatsService
from grz_session_stats.normalize import normalize_result


class LegacyCreditIntegrityTests(unittest.TestCase):
    def setUp(self):
        path = os.path.join(os.path.dirname(__file__), 'fixtures', 'legacy_0_9_8_credits.json')
        with io.open(path, encoding='utf-8') as handle:
            self.legacy = json.load(handle)
        self.directory = tempfile.mkdtemp(prefix='grz-legacy-credit-integrity-')
        self.service = self.reopen()

    def tearDown(self):
        shutil.rmtree(self.directory)

    def reopen(self):
        return StatsService(self.directory, self.legacy['account_key'], self.legacy['launch_id'],
                            self.legacy['expected_table'], lambda: self.legacy['clock'],
                            started_at=self.legacy['started_at'])

    def assertLegacyShape(self, actual, expected, path='statistics'):
        """Every old key and value must survive; additive new fields are allowed."""
        if isinstance(expected, dict):
            self.assertIsInstance(actual, dict, path)
            for key, value in expected.items():
                self.assertIn(key, actual, path)
                self.assertLegacyShape(actual[key], value, path + '/' + key)
        else:
            self.assertEqual(actual, expected, path)

    def assertLegacyMetrics(self):
        snapshot = self.service.snapshot()['scopes']
        for name in ('launch', 'manual'):
            scope = snapshot[name]
            self.assertLegacyShape(scope['summary'], self.legacy['expected_summary'], name)
            for grouping, identifiers in self.legacy['groups'].items():
                self.assertEqual([row['id'] for row in scope[grouping]], identifiers)
                # The frozen old fixture has one group per dimension. All four
                # synthetic records belong to each group, just as in its summary.
                for row in scope[grouping]:
                    self.assertLegacyShape(row['stats'], self.legacy['expected_summary'], grouping)
            battles = dict((row['id'], row['stats']) for row in scope['battles'])
            self.assertEqual(set(battles), set(self.legacy['expected_battles']))
            for identifier, expected in self.legacy['expected_battles'].items():
                self.assertLegacyShape(battles[identifier], expected, 'battle/' + identifier)
            for owner in [scope] + scope['vehicles'] + scope['maps'] + scope['tiers']:
                stats = owner.get('stats', owner.get('summary'))
                for metric in ('xp_base', 'xp_received', 'battle_wn8',
                               'credits_income_received', 'credits_net_received', 'credits_costs'):
                    for statistic in ('min', 'max'):
                        reference = owner['extrema_battles'][metric][statistic]
                        self.assertEqual(reference['value'], stats[metric][statistic])
        self.assertEqual(self.service.pending_arena_ids(), [])

    def test_upgrade_partial_updates_reopen_and_cached_report_preserve_all_known_statistics(self):
        # These records and the expected distributions were emitted by pinned
        # 0.9.8 code. The fixture is synthetic and needs no Git or network at run time.
        for record in self.legacy['records']:
            self.assertNotIn('income_base', record['currencies']['credits'])
            self.assertNotIn('net_base', record['currencies']['credits'])
            self.assertTrue(self.service.record_result(copy.deepcopy(record)))
        self.service = self.reopen()
        self.assertLegacyMetrics()
        self.assertEqual(self.service.snapshot()['scopes']['launch']['summary']['credits_income_base']['count'], 0)

        # A partial authoritative result must not turn already known values
        # into missing fields, and missing new base data must not queue refetches.
        for record in self.legacy['records']:
            partial = {'arena_id': record['arena_id'], 'mode': 'random', 'reconcile': True,
                       'complete': False, 'xp_base': None, 'xp_received': None,
                       'damage': None, 'frags': None, 'spots': None, 'defense': None,
                       'currencies': {'credits': {'income': None, 'net': None, 'costs': None,
                                                   'income_base': None, 'net_base': None},
                                      'bonds': {'income': None, 'net': None, 'costs': None},
                                      'gold': {'income': None, 'net': None, 'costs': None}}}
            self.service.record_result(partial)
        self.assertLegacyMetrics()
        self.service = self.reopen()
        self.assertLegacyMetrics()
        self.assertIsNone(self.service.snapshot()['scopes']['launch']['summary']['credits_income_base']['sum'])

        # This is the normalizer-to-ledger path used when the stock client
        # delivers a full cached report. It adds the newly recorded base value;
        # its stale raw XP must not undo a previously confirmed XP multiplier.
        source = copy.deepcopy(self.legacy['cached_report'])
        metadata = self.legacy['records'][1]
        enriched = normalize_result(source,
                                    vehicle_resolver=lambda cd: {'name': metadata['vehicle_name'],
                                                                  'tier': metadata['vehicle_tier'],
                                                                  'type': metadata['vehicle_type']},
                                    map_resolver=lambda identifier: {'id': metadata['map_id'],
                                                                      'name': metadata['map_name']})
        expected = self.legacy['expected_enrichment']
        self.assertEqual(enriched['arena_id'], expected['arena_id'])
        self.assertLess(enriched['xp_received'], metadata['xp_received'])
        self.assertTrue(self.service.record_result(enriched))
        self.assertLegacyMetrics()
        self.service = self.reopen()
        self.assertLegacyMetrics()
        credits = self.service._state['battles'][expected['arena_id']]['currencies']['credits']
        self.assertEqual(credits['income_base'], expected['income_base'])
        self.assertEqual(credits['net_base'], expected['net_base'])
        summary = self.service.snapshot()['scopes']['launch']['summary']
        self.assertEqual(summary['credits_income_base']['count'], 1)
        self.assertEqual(summary['credits_income_base']['sum'], expected['income_base'])


if __name__ == '__main__':
    unittest.main()
