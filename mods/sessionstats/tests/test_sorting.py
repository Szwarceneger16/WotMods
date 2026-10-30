# -*- coding: utf-8 -*-
"""Global sorting, missing values, corrections, and native request ownership."""
from __future__ import unicode_literals

import copy
from test_native_pagination import NativePaginationTests
from test_core import result
from grz_session_stats.projection import DEFAULT_ORDER


class SortingTests(NativePaginationTests):
    def sort(self, scope='manual', group='battles', **options):
        command = self.command(scope, group, action='sort')
        command.update(DEFAULT_ORDER)
        command.update(options)
        self.window._model.onAction(command)
        return self.payload()['scopes'][scope]

    def test_sorting_is_global_for_every_metric_statistic_and_direction(self):
        service = self.mod.active_service
        for i in range(45):
            row = result(str(i), started_at=110+i, xp_base=45-i, xp_received=i*2,
                         damage=(i+1)*1000, vehicle_id=1, ended_at=190, reconcile=True)
            row['currencies']['credits']['net'] = i-20
            self.assertTrue(service.record_result(row))
        for metric, expected_low, expected_high in [('xp_base','44','0'), ('xp_received','0','44'),
                                                  ('credits_net','0','44'), ('battle_wn8','0','44')]:
            for statistic in ('min','avg','max'):
                for direction, first in [('asc',expected_low), ('desc',expected_high)]:
                    scope = self.sort(metric=metric, statistic=statistic, direction=direction)
                    self.assertEqual(scope['battles'][0]['id'], first, (metric,statistic,direction))
                    self.assertEqual(scope['pagination']['battles']['page'], 0)
                    self.window._model.onAction(self.command())
                    self.assertEqual(len(self.payload()['scopes']['manual']['battles']),5)

    def test_missing_is_last_negative_credits_are_numeric_and_corrections_invalidate_order(self):
        service = self.mod.active_service
        self.assertTrue(service.record_result(result('missing', xp_base=None)))
        self.assertTrue(service.record_result(result('low', xp_base=1)))
        self.assertEqual(self.sort(metric='xp_base',direction='asc')['battles'][0]['id'],'low')
        self.assertTrue(service.record_result(result('low', xp_base=9999, reconcile=True)))
        self.assertEqual(self.sort(metric='xp_base',direction='desc')['battles'][0]['id'],'low')
        self.window._model.onAction(self.command())
        self.assertEqual(self.payload()['scopes']['manual']['battles'][-1]['id'],'missing')

    def test_chronology_works_in_all_scopes_and_sorting_is_independent_of_paging(self):
        for scope in ('launch','manual','instance'):
            for group in ('battles','vehicles','maps'):
                sorted_scope = self.sort(scope,group,chronology='oldest')
                self.assertEqual(sorted_scope['ordering'][group]['chronology'],'oldest')
                self.window._model.onAction(self.command(scope,group))
                self.assertEqual(self.payload()['scopes'][scope]['pagination'][group]['page'],1)
                self.assertEqual(self.sort(scope,group,chronology='newest')['pagination'][group]['page'],0)

    def test_invalid_and_stale_sort_commands_do_not_mutate_service(self):
        service = self.mod.active_service
        for updates in ({'metric':'bad'}, {'statistic':'sum'}, {'direction':'bad'}, {'chronology':'bad'},
                        {'account_key':'EU:8'}, {'period_id':'expired'}, {'group':'invalid'}):
            self.sort(**updates)
        self.assertEqual(service._orders,{})
        self.assertEqual(service._pages,{})


if __name__ == '__main__':
    import unittest
    unittest.main()
