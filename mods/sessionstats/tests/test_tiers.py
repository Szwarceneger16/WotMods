# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import copy
import unittest
from test_history_performance import HistoryPerformanceTests
from test_core import result, aggregate_stats, EXPECTED
from grz_session_stats.projection import DEFAULT_ORDER


class TierTests(HistoryPerformanceTests):
    def test_tiers_include_eleven_and_unknown_without_losing_battles(self):
        for i, tier in enumerate((8, 8, 10, 11, None)):
            self.assertTrue(self.service.record_result(result(str(i),vehicle_tier=tier)))
        scope = self.service.snapshot()['scopes']['manual']
        tiers = dict((row['id'], row) for row in scope['tiers'])
        self.assertEqual(set(tiers), set(('8','10','11','__unknown__')))
        self.assertEqual(tiers['11']['name'],'XI')
        self.assertEqual(tiers['8']['stats']['battles'],2)
        self.assertEqual(sum(row['stats']['battles'] for row in tiers.values()),5)
        rows = list(self.service._state['battles'].values())
        for row in tiers.values():
            self.assert_numbers(row['stats'],aggregate_stats([r for r in rows if r.get('vehicle_tier') == row['tier']],EXPECTED))

    def test_unknown_tier_name_is_localized_without_changing_the_identifier(self):
        from grz_session_stats.localization import Localizer
        self.service.record_result(result('unknown',vehicle_tier=None))
        snapshot=Localizer('pl').snapshot(self.service.snapshot())
        row=snapshot['scopes']['manual']['tiers'][0]
        self.assertEqual(row['id'],'__unknown__')
        self.assertEqual(row['name'],'Nieznany poziom')

    def test_corrected_tier_moves_statistics_and_removes_empty_group(self):
        self.service.record_result(result('a',vehicle_tier=8))
        self.service.record_result(result('a',vehicle_tier=11,reconcile=True))
        tiers=self.service.snapshot()['scopes']['manual']['tiers']
        self.assertEqual([row['id'] for row in tiers],['11'])
        self.assertEqual(tiers[0]['stats']['battles'],1)
        self.assertEqual(self.reopen().snapshot()['scopes']['manual']['tiers'],tiers)

    def test_group_sort_uses_per_battle_min_average_max_instead_of_total(self):
        for identifier,tier,xp in [('a',8,100),('b',8,900),('c',10,600)]:
            self.service.record_result(result(identifier,vehicle_tier=tier,xp_base=xp))
        period=self.service.snapshot()['scopes']['manual']['period_id']
        for statistic,expected in [('min','10'),('avg','10'),('max','8')]:
            options=dict(DEFAULT_ORDER,metric='xp_base',statistic=statistic,direction='desc')
            self.assertTrue(self.service.set_order('manual','tiers',options,period))
            self.assertEqual(self.service.snapshot()['scopes']['manual']['tiers'][0]['id'],expected)
        self.service.reset_manual()
        self.assertEqual(self.service.snapshot()['scopes']['manual']['tiers'],[])
        self.assertFalse(self.service.set_order('manual','tiers',DEFAULT_ORDER,period))


if __name__ == '__main__': unittest.main()
