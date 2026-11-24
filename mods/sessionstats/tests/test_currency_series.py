# -*- coding: utf-8 -*-
"""Summary finance modes use actual per-field distributions, not total guesses."""
from __future__ import unicode_literals

import copy
import shutil
import tempfile
import unittest

from test_core import Clock, EXPECTED, result
from grz_session_stats.core import ExpectedTable, StatsService, aggregate_stats
from grz_session_stats.projection import Totals, contribution


def financial_row(identifier, started_at=110, factor=1):
    return result(identifier, started_at=started_at, currencies={
        'credits': {'income': 100 * factor, 'costs': 20 * factor,
                    'net': 80 * factor, 'income_base': 80 * factor,
                    'net_base': 60 * factor},
        'bonds': {'income': 10 * factor, 'costs': factor - 1,
                  'net': 9 * factor + 1},
        'gold': {'income': 5 * (factor - 1), 'costs': factor - 1,
                 'net': 4 * (factor - 1)}})


class CurrencySeriesTests(unittest.TestCase):
    def test_summary_distributions_include_zero_and_exclude_pending_results(self):
        first, second = financial_row('a'), financial_row('b', factor=3)
        pending = financial_row('pending', factor=1000)
        pending['outcome'] = None
        rows = [first, second, pending]
        ordinary = aggregate_stats(rows, EXPECTED)
        summary = aggregate_stats(rows, EXPECTED, include_currency_series=True)
        self.assertNotIn('currency_series', ordinary)
        series = summary.pop('currency_series')
        self.assertEqual(summary, ordinary)
        self.assertEqual(series['bonds']['income'],
                         {'min': 10, 'avg': 20.0, 'max': 30, 'sum': 40, 'count': 2})
        self.assertEqual(series['gold']['costs'],
                         {'min': 0, 'avg': 1.0, 'max': 2, 'sum': 2, 'count': 2})
        self.assertEqual(series['credits']['income_base']['sum'], 320)
        credits = summary['currencies']['credits']
        self.assertEqual(summary['observed_battles'], 3)
        self.assertEqual(summary['battles'], 2)
        self.assertEqual(credits['income_base'], 320)
        self.assertEqual(credits['net_base'], 240)
        self.assertTrue(credits['income_base_complete'])
        self.assertTrue(credits['net_base_complete'])
        series['credits']['income']['count'] = -1
        self.assertEqual(summary['credits_income_received']['count'], 2)

    def test_missing_field_has_no_fabricated_minimum_or_zero(self):
        row = financial_row('a')
        row['currencies']['bonds']['costs'] = None
        row['currencies']['gold']['net'] = None
        summary = aggregate_stats([row], EXPECTED, include_currency_series=True)
        for currency, field in [('bonds', 'costs'), ('gold', 'net')]:
            self.assertEqual(summary['currency_series'][currency][field],
                             {'min': None, 'avg': None, 'max': None, 'sum': None, 'count': 0})

    def test_incremental_corrections_and_removal_update_real_extrema(self):
        table = ExpectedTable(EXPECTED)
        rows = [financial_row('a'), financial_row('b', factor=3)]
        items = [contribution(row, table) for row in rows]
        totals = Totals()
        totals.build(items)
        self.assertNotIn('currency_series', totals.snapshot())
        self.assertEqual(totals.snapshot(True)['currency_series'],
                         aggregate_stats(rows, table, True)['currency_series'])
        changed = copy.deepcopy(rows[1])
        changed['currencies']['bonds'].update(income=95, costs=6, net=89)
        totals.change(items[1], -1)
        totals.change(contribution(changed, table), 1)
        self.assertEqual(totals.snapshot(True)['currency_series']['bonds']['income'],
                         {'min': 10, 'avg': 52.5, 'max': 95, 'sum': 105, 'count': 2})
        totals.change(items[0], -1)
        self.assertEqual(totals.snapshot(True)['currency_series']['bonds']['income'],
                         {'min': 95, 'avg': 95.0, 'max': 95, 'sum': 95, 'count': 1})
        totals.snapshot(True)['currency_series']['bonds']['income']['count'] = -1
        self.assertEqual(totals.snapshot(True)['currency_series']['bonds']['income']['count'], 1)

    def test_service_range_reset_changes_only_summary_distribution(self):
        directory = tempfile.mkdtemp(prefix='grz-currency-series-')
        try:
            clock = Clock(100)
            service = StatsService(directory, 'EU:7', 'currency-series', EXPECTED, clock)
            clock.value = 125
            self.assertTrue(service.record_result(financial_row('a')))
            clock.value = 130
            self.assertTrue(service.reset_manual())
            clock.value = 160
            self.assertTrue(service.record_result(financial_row('b', started_at=140, factor=3)))
            scopes = service.snapshot()['scopes']
            self.assertEqual(scopes['launch']['summary']['currency_series']['bonds']['income']['avg'], 20.0)
            self.assertEqual(scopes['manual']['summary']['currency_series']['bonds']['income']['avg'], 30.0)
            for scope in scopes.values():
                for kind in ('vehicles', 'maps', 'tiers', 'battles'):
                    self.assertTrue(all('currency_series' not in row['stats'] for row in scope[kind]))
            projected = service.project_scope([financial_row('a')], 'Synthetic scope', 100)
            self.assertEqual(projected['summary']['currency_series']['bonds']['income']['avg'], 10.0)
            self.assertNotIn('currency_series', projected['vehicles'][0]['stats'])
        finally:
            shutil.rmtree(directory)


if __name__ == '__main__':
    unittest.main()
