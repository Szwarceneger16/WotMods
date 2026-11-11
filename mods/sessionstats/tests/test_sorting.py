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
            for group in ('battles','vehicles','maps','tiers'):
                sorted_scope = self.sort(scope,group,chronology='oldest')
                self.assertEqual(sorted_scope['ordering'][group]['chronology'],'oldest')
                self.window._model.onAction(self.command(scope,group))
                self.assertEqual(self.payload()['scopes'][scope]['pagination'][group]['page'],
                                 0 if group == 'tiers' else 1)
                self.assertEqual(self.sort(scope,group,chronology='newest')['pagination'][group]['page'],0)

    def test_tier_order_is_numeric_defaults_highest_first_and_is_owned_by_each_scope(self):
        for identifier, tier, started in (('tier-xi', 11, 125), ('tier-ix', 9, 145),
                                          ('tier-ii', 2, 165), ('tier-unknown', None, 185)):
            row = result(identifier, vehicle_tier=tier, started_at=started, ended_at=195)
            self.assertTrue(self.mod.active_service.record_result(row))
            self.assertTrue(self.mod._instance_session.result('EU:7', row, allow_new=True))
        self.window.refresh()
        for scope in ('launch', 'manual', 'instance'):
            before = self.payload()['scopes'][scope]
            self.assertEqual(before['ordering']['tiers']['chronology'], 'tier_desc')
            self.assertEqual([row['tier'] for row in before['tiers']], [11, 9, 8, 2, None])
            ascending = self.sort(scope, 'tiers', chronology='tier_asc')
            self.assertEqual([row['tier'] for row in ascending['tiers']], [2, 8, 9, 11, None])
            descending = self.sort(scope, 'tiers', chronology='tier_desc')
            self.assertEqual([row['tier'] for row in descending['tiers']], [11, 9, 8, 2, None])
            # An explicit ordinary date choice remains available when metric
            # sorting is off, even though tier order is this tab's default.
            newest = self.sort(scope, 'tiers', chronology='newest')
            self.assertIsNone(newest['tiers'][0]['tier'])
            self.assertEqual(newest['ordering']['tiers']['chronology'], 'newest')
        # Changing one tab cannot change the ordinary date selector elsewhere.
        for group in ('battles', 'vehicles', 'maps'):
            self.assertEqual(self.payload()['scopes']['manual']['ordering'][group], DEFAULT_ORDER)

    def test_tier_modes_are_rejected_for_other_groups_and_metric_ties_ignore_them(self):
        service = self.mod.active_service
        for group in ('battles', 'vehicles', 'maps'):
            for chronology in ('tier_asc', 'tier_desc'):
                self.sort(group=group, chronology=chronology)
        self.assertEqual(service._orders, {})
        for identifier, tier, started in (('tier-old', 11, 125), ('tier-new', 2, 185)):
            self.assertTrue(service.record_result(result(identifier, vehicle_tier=tier,
                                                         started_at=started, ended_at=195)))
        ascending = self.sort(group='tiers', metric='xp_base', chronology='tier_asc')
        descending = self.sort(group='tiers', metric='xp_base', chronology='tier_desc')
        self.assertEqual([row['tier'] for row in ascending['tiers']], [2, 11, 8])
        self.assertEqual(ascending['tiers'], descending['tiers'])
        restored = self.sort(group='tiers', metric='off', chronology='tier_desc')
        self.assertEqual([row['tier'] for row in restored['tiers']], [11, 8, 2])

    def test_invalid_and_stale_sort_commands_do_not_mutate_service(self):
        service = self.mod.active_service
        for updates in ({'metric':'bad'}, {'statistic':'sum'}, {'direction':'bad'}, {'chronology':'bad'},
                        {'account_key':'EU:8'}, {'period_id':'expired'}, {'group':'invalid'}):
            self.sort(**updates)
        self.assertEqual(service._orders,{})
        self.assertEqual(service._pages,{})

    def test_active_metric_ties_ignore_saved_chronology_in_every_group(self):
        # Each recorded result has equal XP; changing the saved date preference
        # must not silently reorder the active metric's tied groups/battles.
        for identifier, vehicle, tier, started in (('time-old', 1001, 6, 125), ('time-new', 1002, 9, 185)):
            self.assertTrue(self.mod.active_service.record_result(result(identifier, vehicle_id=vehicle,
                vehicle_tier=tier, map_id=identifier, started_at=started, ended_at=195)))
        for group in ('battles', 'vehicles', 'maps', 'tiers'):
            first = self.sort(group=group, metric='xp_base', chronology='newest')
            second = self.sort(group=group, metric='xp_base', chronology='oldest')
            self.assertEqual([item['id'] for item in first[group]],
                             [item['id'] for item in second[group]], group)
        # The preference is retained and remains effective in date-only mode.
        newest = self.sort(metric='off', chronology='newest')['battles'][0]['id']
        oldest = self.sort(metric='off', chronology='oldest')['battles'][0]['id']
        self.assertNotEqual(newest, oldest)

    def test_recorded_battle_count_sorts_vehicle_and_map_totals_without_a_statistic(self):
        service = self.mod.active_service
        for index in range(3):
            self.assertTrue(service.record_result(result('count-' + str(index), vehicle_id=2,
                                                         map_id='recorded-count-map', started_at=150 + index)))
        # The pending result counts as a recorded battle, matching the
        # denominator shown beside the three received results.
        self.assertTrue(service.record_result(result('count-pending', vehicle_id=2,
                                                     map_id='recorded-count-map', outcome=None,
                                                     complete=False, started_at=160)))
        for group, identifier in (('vehicles', '2'), ('maps', 'recorded-count-map')):
            for statistic in ('min', 'avg', 'max'):
                scope = self.sort(group=group, metric='battles', statistic=statistic)
                self.assertEqual(scope[group][0]['id'], identifier)
                row = scope[group][0]
                expected = 5 if group == 'vehicles' else 4
                self.assertEqual(row['sort_value'], expected)
                self.assertEqual(row['stats']['observed_battles'], expected)
                self.assertEqual(row['stats']['battles'], expected - 1)
                ascending = self.sort(group=group, metric='battles', statistic=statistic, direction='asc')
                self.assertEqual(ascending[group][0]['sort_value'], 1)

    def test_battle_count_sort_is_rejected_for_battles_and_tiers(self):
        service = self.mod.active_service
        for group in ('battles', 'tiers'):
            self.sort(group=group, metric='battles')
        self.assertEqual(service._orders, {})

    def test_wn8_average_sort_uses_battle_average_instead_of_period_formula(self):
        service = self.mod.active_service
        for identifier, damage, kills in (('wn8-a', 0, 0), ('wn8-b', 4000, 4)):
            self.assertTrue(service.record_result(result(identifier, vehicle_id=1,
                                                         damage=damage, frags=kills, spots=kills,
                                                         defense=kills, outcome='win' if kills else 'loss')))
        scope = self.sort(group='vehicles', metric='battle_wn8', statistic='avg')
        row = next(item for item in scope['vehicles'] if item['id'] == '1')
        self.assertAlmostEqual(row['sort_value'], row['stats']['battle_wn8']['avg'])
        self.assertNotAlmostEqual(row['sort_value'], row['stats']['wn8'])


if __name__ == '__main__':
    import unittest
    unittest.main()
