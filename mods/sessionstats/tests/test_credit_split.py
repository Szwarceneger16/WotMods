# -*- coding: utf-8 -*-
"""Independent credit metrics and permanent, indexed source-battle references."""
from __future__ import unicode_literals

import copy
import shutil
import tempfile
import unittest

from test_core import EXPECTED, Clock, result
from test_normalize import raw_result
from grz_session_stats.core import ExpectedTable, StatsService, _clean_record, aggregate_stats
from grz_session_stats.normalize import normalize_result
from grz_session_stats.projection import DEFAULT_ORDER, ScopeIndex, contribution, valid_order
from grz_session_stats.localization import Localizer
from grz_session_stats.map_names import bundled_names


METRICS = ('credits_income_base', 'credits_income_received', 'credits_net_base', 'credits_net_received', 'credits_costs')
EXTREMA = ('xp_base', 'xp_received', 'battle_wn8') + METRICS


def credit_result(identifier, base, received, costs, **updates):
    row = result(identifier, **updates)
    row['currencies']['credits'] = {
        'income_base': base, 'income': received, 'costs': costs,
        'net_base': base - costs if base is not None and costs is not None else None,
        'net': received - costs if received is not None and costs is not None else None}
    return row


class CreditNormalizationTests(unittest.TestCase):
    def test_base_is_original_earning_and_received_keeps_settled_sharing(self):
        raw = raw_result()
        data = raw['personal'][1]
        data.update(originalCredits=20000, credits=75000,
                    originalCreditsToDraw=101, originalCreditsToDrawSquad=1,
                    appliedPremiumCreditsFactor100=150, premSquadCreditsFactor100=110,
                    achievementCredits=7000)
        row = normalize_result(raw)
        money = row['currencies']['credits']
        self.assertEqual(money['income_base'], 20000)
        self.assertAlmostEqual(money['income'], 75000 - 152 - 1.1)
        self.assertEqual(money['net_base'], 20000 - 43000)
        self.assertAlmostEqual(money['net'], money['income'] - 43000)
        # It is deliberately neither the native first earnings row nor a
        # guessed "without premium" total obtained by dividing received income.
        self.assertNotEqual(money['income_base'], 20000 - 101 - 7000)
        self.assertNotEqual(money['income_base'], money['income'] / 1.5)
        self.assertTrue(row['complete'])

    def test_missing_originals_do_not_erase_received_or_change_result_completeness(self):
        raw = raw_result()
        del raw['personal'][1]['originalCredits']
        row = normalize_result(raw)
        self.assertIsNone(row['currencies']['credits']['income_base'])
        self.assertIsNone(row['currencies']['credits']['net_base'])
        self.assertEqual(row['currencies']['credits']['income'], 75000)
        self.assertEqual(row['currencies']['credits']['net'], 32000)
        self.assertTrue(row['complete'])

    def test_base_and_received_have_independent_unknown_factors_and_costs(self):
        raw = raw_result()
        data = raw['personal'][1]
        data['originalCreditsToDraw'] = 10
        del data['appliedPremiumCreditsFactor100']
        money = normalize_result(raw)['currencies']['credits']
        self.assertEqual(money['income_base'], 20000)
        self.assertEqual(money['net_base'], -23000)
        self.assertIsNone(money['income'])
        self.assertIsNone(money['net'])
        del data['autoRepairCost']
        money = normalize_result(raw)['currencies']['credits']
        self.assertEqual(money['income_base'], 20000)
        self.assertIsNone(money['net_base'])

    def test_zero_signed_base_and_invalid_values_are_not_conflated(self):
        for value, wanted in ((0, 0), (-25, -25), (True, None), (float('nan'), None),
                              (float('inf'), None), ('123', None)):
            raw = raw_result()
            raw['personal'][1]['originalCredits'] = value
            money = normalize_result(raw)['currencies']['credits']
            self.assertEqual(money['income_base'], wanted)
            self.assertEqual(money['net_base'], wanted - 43000 if wanted is not None else None)
            self.assertEqual(money['income'], 75000)

    def test_cleaning_and_durable_reopen_preserve_new_values_without_inventing_old_base(self):
        directory = tempfile.mkdtemp(prefix='grz-credit-split-')
        try:
            clock = Clock(120)
            service = StatsService(directory, 'synthetic-account', 'launch', EXPECTED, clock, started_at=100)
            old = result('old')
            old['currencies']['credits']['net'] = 80
            new = credit_result('new', 0, 100, 20)
            self.assertTrue(service.record_result(old))
            self.assertTrue(service.record_result(new))
            self.assertTrue(service._state['battles']['old']['complete'])
            self.assertNotIn('income_base', service._state['battles']['old']['currencies']['credits'])
            reopened = StatsService(directory, 'synthetic-account', 'launch', EXPECTED, clock, started_at=100)
            summary = reopened.snapshot()['scopes']['launch']['summary']
            self.assertEqual(summary['credits_income_base']['count'], 1)
            self.assertEqual(summary['credits_income_base']['sum'], 0)
            self.assertEqual(summary['credits_net_base']['sum'], -20)
            self.assertEqual(summary['credits_income_received']['count'], 2)
            self.assertEqual(summary['credits_income_received']['sum'], 200)
            self.assertEqual(summary['credits_net_received']['sum'], 160)
            self.assertEqual(summary['battles'], 2)
            # A new settled cost can revise base net even when the partial
            # rereading omits originalCredits; the known base is preserved.
            update = credit_result('new', None, None, 30, reconcile=True)
            self.assertTrue(reopened.record_result(update))
            self.assertEqual(reopened._state['battles']['new']['currencies']['credits']['net_base'], -30)
            self.assertEqual(reopened.snapshot()['scopes']['launch']['summary']['credits_net_base']['sum'], -30)
            invalid = credit_result('invalid', True, -5, -10)
            invalid['currencies']['credits']['net_base'] = float('inf')
            clean = _clean_record(invalid)['currencies']['credits']
            self.assertIsNone(clean['income_base'])
            self.assertIsNone(clean['net_base'])
            self.assertIsNone(clean['costs'])
            self.assertEqual(clean['income'], -5)
        finally:
            shutil.rmtree(directory)


class CreditProjectionTests(unittest.TestCase):
    def setUp(self):
        self.table = ExpectedTable(EXPECTED)
        self.rows = [credit_result('a', 0, 100, 25, vehicle_id=1, vehicle_tier=1, map_id='1'),
                     credit_result('b', 80, 20, 10, vehicle_id=2, vehicle_tier=2, map_id='2'),
                     credit_result('c', 20, 200, 90, vehicle_id=3, vehicle_tier=3, map_id='3'),
                     credit_result('d', None, -5, 0, vehicle_id=4, vehicle_tier=4, map_id='4'),
                     credit_result('e', -10, None, None, vehicle_id=5, vehicle_tier=5, map_id='5'),
                     credit_result('pending', 99999, 99999, 0, outcome=None, complete=False),
                     credit_result('wrong-mode', 99999, 99999, 0, mode='other')]
        self.index = self.build(self.rows)

    def build(self, rows):
        index = ScopeIndex('synthetic-period', self.table)
        index.build([contribution(row, self.table) for row in rows])
        return index

    def test_incremental_and_recomputed_metrics_keep_independent_coverage(self):
        expected = aggregate_stats(self.rows, self.table)
        actual = self.index.totals.snapshot()
        for metric, count in (('credits_income_base', 4), ('credits_income_received', 4),
                               ('credits_net_base', 3), ('credits_net_received', 4), ('credits_costs', 4)):
            self.assertEqual(actual[metric], expected[metric], metric)
            self.assertEqual(actual[metric]['count'], count, metric)
        self.assertEqual(actual['credits_income_base']['sum'], 90)
        self.assertEqual(actual['currencies']['credits']['income_base'], 90)
        self.assertEqual(actual['currencies']['credits']['income_base_count'], 4)
        self.assertEqual(actual['credits_gross'], actual['credits_income_received'])
        self.assertEqual(actual['credits_net'], actual['credits_net_received'])

    def test_all_credit_orders_are_global_for_aggregates_and_battles(self):
        expected = {'credits_income_base': '2', 'credits_income_received': '3',
                    'credits_net_base': '2', 'credits_net_received': '3', 'credits_costs': '3'}
        for kind in ('maps', 'vehicles', 'tiers', 'battles'):
            for metric in METRICS:
                for statistic in ('min', 'avg', 'max', 'sum'):
                    order = dict(DEFAULT_ORDER, metric=metric, statistic=statistic)
                    self.assertEqual(valid_order(order, kind), kind != 'battles' or statistic != 'sum')
                    if not valid_order(order, kind):
                        continue
                    rows = self.index.snapshot('Synthetic', 0, orders={kind: order})[kind]
                    self.assertEqual(rows[0]['id'], {'2': 'b', '3': 'c'}[expected[metric]] if kind == 'battles' else expected[metric])
                    if kind != 'battles':
                        self.assertEqual(rows[0]['stats'][metric][statistic], rows[0]['sort_value'])

    def test_global_and_group_min_max_refs_are_permanent_and_do_not_depend_on_order(self):
        wanted = {'credits_income_base': ('e', 'b'), 'credits_income_received': ('d', 'c'),
                  'credits_net_base': ('c', 'b'), 'credits_net_received': ('d', 'c'), 'credits_costs': ('d', 'c')}
        baseline = self.index.snapshot('Synthetic', 0)
        for metric, identifiers in wanted.items():
            for statistic, identifier in zip(('min', 'max'), identifiers):
                reference = baseline['extrema_battles'][metric][statistic]
                self.assertEqual(reference['id'], identifier)
                self.assertEqual(reference['value'], baseline['summary'][metric][statistic])
        for kind in ('maps', 'vehicles', 'tiers'):
            for metric in ('off', 'xp_base', 'credits_income_received', 'win_rate'):
                order = dict(DEFAULT_ORDER, metric=metric)
                snapshot = self.index.snapshot('Synthetic', 0, orders={kind: order})
                self.assertEqual(snapshot['extrema_battles'], baseline['extrema_battles'])
                for row in snapshot[kind]:
                    for linked, pair in row['extrema_battles'].items():
                        self.assertIn(linked, EXTREMA)
                        for statistic, reference in pair.items():
                            self.assertEqual(reference['value'], row['stats'][linked][statistic])
                            self.assertEqual(reference['metric'], linked)
                            self.assertEqual(reference['statistic'], statistic)
            self.assertNotIn('credits_gross', baseline[kind][0]['extrema_battles'])

    def test_full_period_refs_survive_pagination_ties_corrections_and_removals(self):
        rows = [credit_result('old-high', 9999, 9999, 1, started_at=1)]
        rows.extend(credit_result('page-%03d' % i, i, i, 1, started_at=100 + i) for i in range(85))
        rows.append(credit_result('a-tied', 9999, 9999, 1, started_at=2))
        index = self.build(rows)
        snapshot = index.snapshot('Synthetic', 0)
        self.assertNotIn('a-tied', [row['id'] for row in snapshot['battles']])
        for kind in ('maps', 'vehicles', 'tiers'):
            self.assertEqual(snapshot[kind][0]['extrema_battles']['credits_income_base']['max']['id'], 'a-tied')
        changed = credit_result('a-tied', None, 0, 0, vehicle_id=2, vehicle_tier=9, map_id='moved')
        index.replace(changed, contribution(changed, self.table))
        self.assertEqual(index.snapshot('Synthetic', 0)['extrema_battles']['credits_income_base']['max']['id'], 'old-high')
        index.discard('old-high')
        self.assertEqual(index.snapshot('Synthetic', 0)['extrema_battles']['credits_income_base']['max']['id'], 'page-084')
        rebuilt = self.build([pair[0] for pair in index.records.values()])
        self.assertEqual(index.snapshot('Synthetic', 0)['extrema_battles'], rebuilt.snapshot('Synthetic', 0)['extrema_battles'])
        for kind in ('maps', 'vehicles', 'tiers'):
            self.assertEqual(index.snapshot('Synthetic', 0)[kind], rebuilt.snapshot('Synthetic', 0)[kind])

    def test_snapshot_reads_indexed_associations_without_history_scans(self):
        class NoScan(dict):
            def __iter__(self):
                raise AssertionError('A snapshot must not scan source records')
            def items(self):
                raise AssertionError('A snapshot must not scan source records')
            def values(self):
                raise AssertionError('A snapshot must not scan source records')
        self.index.records = NoScan(self.index.records)
        for kind in ('maps', 'vehicles', 'tiers'):
            for group in self.index.groups[kind].values():
                group.records = NoScan(group.records)
        snapshot = self.index.snapshot('Synthetic', 0)
        self.assertEqual(snapshot['extrema_battles']['credits_income_base']['max']['id'], 'b')

    def test_rebuilding_the_same_scope_removes_old_groups_and_associations(self):
        replacement = credit_result('new-period', 12, 34, 1, vehicle_id=9, vehicle_tier=9, map_id='new-map')
        self.index.build([contribution(replacement, self.table)])
        snapshot = self.index.snapshot('Replacement', 0)
        for kind, identifier in (('maps', 'new-map'), ('vehicles', '9'), ('tiers', '9')):
            self.assertEqual([row['id'] for row in snapshot[kind]], [identifier])
            self.assertEqual(snapshot[kind][0]['extrema_battles']['credits_income_base']['max']['id'], 'new-period')
        self.assertEqual(snapshot['extrema_battles']['credits_income_base']['max']['id'], 'new-period')

    def test_permanent_refs_use_selected_map_language_without_mutating_records(self):
        row = credit_result('localized', 20, 30, 1, map_id='59_asia_great_wall', map_name='Saved native name')
        index = self.build([row])
        payload = {'warnings': [], 'scopes': {'launch': index.snapshot('Synthetic', 0)}}
        names = bundled_names()['59_asia_great_wall']
        for language in ('en', 'pl', 'ru', 'fr', 'de', 'es', 'uk'):
            localized = Localizer(language).snapshot(copy.deepcopy(payload))['scopes']['launch']
            self.assertEqual(localized['extrema_battles']['credits_income_base']['min']['map'], names[language])
            for kind in ('maps', 'vehicles', 'tiers'):
                self.assertEqual(localized[kind][0]['extrema_battles']['xp_base']['min']['map'], names[language])
        self.assertEqual(payload['scopes']['launch']['extrema_battles']['credits_income_base']['min']['map'], 'Saved native name')


if __name__ == '__main__':
    unittest.main()
