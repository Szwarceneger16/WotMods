# -*- coding: utf-8 -*-
"""Bounded page acknowledgements and coherent incremental page caches."""
from __future__ import unicode_literals

import copy
import unittest

import test_history_navigation as history
from test_core import result
from grz_session_stats.projection import DEFAULT_ORDER


class PageCacheProtocolTests(unittest.TestCase):
    setUp = history.HistoryNavigationTests.__dict__['setUp']
    tearDown = history.HistoryNavigationTests.__dict__['tearDown']
    seed = history.HistoryNavigationTests.__dict__['seed']
    finish = history.HistoryNavigationTests.__dict__['finish']

    def scope(self):
        return self.service.snapshot()['scopes']['manual']

    def test_revision_is_stable_across_navigation_sort_and_drilldown_without_history_writes(self):
        before = self.scope()
        state, sequence = copy.deepcopy(self.service._state), self.service.store.sequence
        period, revision = before['period_id'], before['data_revision']
        self.assertTrue(revision)
        self.assertTrue(self.service.set_page('manual', 'battles', 1, period, 'cache-1'))
        page = self.scope()
        self.assertEqual(page['pagination']['battles']['request_id'], 'cache-1')
        self.assertEqual(page['data_revision'], revision)
        self.assertTrue(self.service.set_order('manual', 'battles', dict(DEFAULT_ORDER, metric='xp_base'), period))
        self.assertNotIn('request_id', self.scope()['pagination']['battles'])
        self.assertTrue(self.service.set_map_battles('manual', 'map-a', 0, period))
        self.assertTrue(self.service.set_vehicle_battles('manual', '1', 0, period))
        self.assertTrue(self.service.select_battle('manual', 'row-00000', period, 'jump-1'))
        self.assertEqual(self.scope()['data_revision'], revision)
        self.assertEqual(self.service._state, state)
        self.assertEqual(self.service.store.sequence, sequence)

    def test_pending_new_result_late_correction_and_name_updates_change_the_revision(self):
        previous = self.scope()['data_revision']
        self.assertTrue(self.service.begin_battle('fixture-new', 1000, vehicle_id=1, map_id='map-a', mode='random'))
        pending = self.scope()['data_revision']
        self.assertNotEqual(pending, previous)
        self.assertTrue(self.service.record_result(result('fixture-new', 1000)))
        complete = self.scope()['data_revision']
        self.assertNotEqual(complete, pending)
        self.assertTrue(self.service.record_result(result('fixture-new', 1000, reconcile=True,
                                                          vehicle_name='Corrected fixture name', xp_base=777)))
        corrected = self.scope()['data_revision']
        self.assertNotEqual(corrected, complete)
        self.assertEqual(self.scope()['data_revision'], corrected)

    def test_newest_insert_invalidates_old_cached_page_boundaries(self):
        first = self.scope()
        period = first['period_id']
        self.assertTrue(self.service.set_page('manual', 'battles', 1, period, 'page-1'))
        self.assertTrue(self.service.record_result(result('fixture-new', 1000)))
        second = self.scope()
        self.assertNotEqual(second['data_revision'], first['data_revision'])
        old_ids = set(row['id'] for row in first['battles'])
        second_ids = set(row['id'] for row in second['battles'])
        self.assertTrue(old_ids.intersection(second_ids))
        self.assertTrue(self.service.set_page('manual', 'battles', 0, period, 'refresh-0'))
        refreshed = self.scope()
        self.assertEqual(refreshed['data_revision'], second['data_revision'])
        self.assertFalse(set(row['id'] for row in refreshed['battles']).intersection(second_ids))
        self.assertEqual(second['pagination']['battles']['request_id'], 'page-1')

    def test_filtered_revision_changes_only_when_that_selected_scope_changes(self):
        self.assertTrue(self.service.set_timeline_range('__custom__', '__custom__', 120, 130))
        pending = self.service.timeline_snapshot()['data_revision']
        self.assertEqual(self.service.timeline_snapshot()['data_revision'], pending)
        selected = self.finish()
        self.assertNotEqual(selected['data_revision'], pending)
        self.assertTrue(self.service.record_result(result('row-00000', 110, reconcile=True, xp_base=777)))
        self.assertEqual(self.service.timeline_snapshot()['data_revision'], selected['data_revision'])
        self.assertTrue(self.service.record_result(result('row-00010', 120, reconcile=True, xp_base=888)))
        self.assertNotEqual(self.service.timeline_snapshot()['data_revision'], selected['data_revision'])

    def test_rebuilding_same_period_retires_its_previous_revision(self):
        before = self.scope()
        self.service._rebuild_indexes()
        after = self.scope()
        self.assertEqual(after['period_id'], before['period_id'])
        self.assertEqual(after['summary'], before['summary'])
        self.assertNotEqual(after['data_revision'], before['data_revision'])

    def test_page_echo_is_per_group_and_retired_by_sort_selection_and_period_reset(self):
        period = self.scope()['period_id']
        self.assertTrue(self.service.set_page('manual', 'vehicles', 0, period, 'vehicles-0'))
        self.assertTrue(self.service.set_page('manual', 'battles', 1, period, 'battles-1'))
        current = self.scope()['pagination']
        self.assertEqual(current['vehicles']['request_id'], 'vehicles-0')
        self.assertEqual(current['battles']['request_id'], 'battles-1')
        self.assertTrue(self.service.select_battle('manual', 'row-00000', period, 'battle-jump'))
        self.assertNotIn('request_id', self.scope()['pagination']['battles'])
        self.assertTrue(self.service.set_page('manual', 'vehicles', 0, period))
        self.assertNotIn('request_id', self.scope()['pagination']['vehicles'])
        self.assertTrue(self.service.set_page('manual', 'battles', 0, period, 'old-period'))
        self.assertTrue(self.service.reset_manual())
        self.assertNotIn('manual', self.service._page_requests)
        self.assertFalse(self.service.set_page('manual', 'battles', 0, period, 'stale-period'))

    def test_supplemental_history_is_bounded_and_independent_of_visible_aggregate_page(self):
        rows = {}
        for group in range(45):
            for battle in range(12):
                identifier = 'fixture-{0:02d}-{1:02d}'.format(group, battle)
                row = result(identifier, 110 + group * 12 + battle, vehicle_id=group + 1,
                             vehicle_name='Fixture vehicle {0}'.format(group),
                             map_id='map-{0:02d}'.format(group), map_name='Fixture map {0}'.format(group))
                row.update(_manual_id=self.service._state['current_manual_id'], _launch_id=self.service.launch_id,
                           _updated_at=1000, _result_seen=True, revision=1)
                rows[identifier] = row
        self.service._state['battles'] = rows
        self.service._rebuild_indexes()
        before, sequence = copy.deepcopy(self.service._state), self.service.store.sequence
        initial = self.scope()
        period = initial['period_id']
        self.assertTrue(self.service.set_page('manual', 'maps', 1, period, 'maps-1'))
        self.assertTrue(self.service.set_page('manual', 'vehicles', 1, period, 'vehicles-1'))
        self.assertNotIn('map-44', [row['id'] for row in self.scope()['maps']])
        self.assertNotIn('45', [row['id'] for row in self.scope()['vehicles']])
        self.assertTrue(self.service.set_map_battles('manual', 'map-44', 1, period))
        scope = self.scope()
        history = scope['battle_history']
        self.assertEqual(set(history), {'kind', 'id', 'battle_list'})
        self.assertEqual((history['kind'], history['id']), ('maps', 'map-44'))
        self.assertEqual((history['battle_list']['page'], history['battle_list']['total'],
                          len(history['battle_list']['items'])), (1, 12, 2))
        self.assertEqual(scope['pagination']['maps']['page'], 1)
        self.assertTrue(self.service.set_vehicle_battles('manual', '45', 0, period))
        scope = self.scope()
        history = scope['battle_history']
        self.assertEqual((history['kind'], history['id']), ('vehicles', '45'))
        self.assertEqual(len(history['battle_list']['items']), 10)
        self.assertEqual(scope['pagination']['vehicles']['page'], 1)
        self.assertEqual(scope['data_revision'], initial['data_revision'])
        self.assertFalse(self.service.set_vehicle_battles('manual', '45', 1, 'expired'))
        self.assertEqual(self.scope()['battle_history'], history)
        self.assertEqual(self.service._state, before)
        self.assertEqual(self.service.store.sequence, sequence)

    def test_supplemental_history_retires_on_reset_range_or_missing_group(self):
        period = self.scope()['period_id']
        self.assertTrue(self.service.set_vehicle_battles('manual', '1', 0, period))
        self.assertTrue(self.service.reset_manual())
        self.assertNotIn('manual', self.service._history_request)
        self.assertNotIn('battle_history', self.scope())
        self.assertTrue(self.service.set_timeline_range('__custom__', '__custom__', 120, 130))
        timeline = self.finish()
        self.assertTrue(self.service.set_vehicle_battles('timeline', '1', 0, timeline['period_id']))
        self.assertIn('battle_history', self.service.timeline_snapshot())
        index = self.service._filtered_timeline
        for identifier in list(index.records):
            index.discard(identifier)
        self.assertNotIn('battle_history', self.service.timeline_snapshot())
        self.assertTrue(self.service.set_timeline_range('__custom__', '__custom__', 130, 140))
        self.assertNotIn('timeline', self.service._history_request)
        self.assertNotIn('battle_history', self.service.timeline_snapshot())
        loading = self.service.timeline_snapshot()['data_revision']
        self.assertEqual(self.service.timeline_snapshot()['data_revision'], loading)
        self.service.loading = True
        try:
            first, second = self.service.snapshot(), self.service.snapshot()
            for name in ('launch', 'manual'):
                self.assertEqual(first['scopes'][name]['data_revision'], second['scopes'][name]['data_revision'])
                self.assertNotIn('battle_history', first['scopes'][name])
        finally:
            self.service.loading = False


class NativePageCacheProtocolTests(unittest.TestCase):
    setUp = history.NativeHistoryNavigationTests.__dict__['setUp']
    tearDown = history.NativeHistoryNavigationTests.__dict__['tearDown']
    inject_module = history.NativeHistoryNavigationTests.__dict__['inject_module']
    payload = history.NativeHistoryNavigationTests.__dict__['payload']

    def test_native_page_echo_and_revision_work_for_account_and_instance_scopes(self):
        for scope in ('launch', 'manual', 'instance'):
            before = self.payload()['scopes'][scope]
            command = {'action': 'page', 'scope': scope, 'group': 'battles', 'page': '1',
                       'period_id': before['period_id'], 'account_key': 'EU:7', 'request_id': b'cache-1'}
            self.window._model.onAction(command)
            after = self.payload()['scopes'][scope]
            self.assertEqual(after['pagination']['battles']['request_id'], 'cache-1')
            self.assertEqual(after['data_revision'], before['data_revision'])
            self.assertEqual(len(after['battles']), 5)
            command.update(page='0', request_id='cache-0')
            self.window._model.onAction(command)
            self.assertEqual(self.payload()['scopes'][scope]['pagination']['battles']['request_id'], 'cache-0')

    def test_invalid_request_account_and_period_cannot_change_or_acknowledge_a_page(self):
        scope = self.payload()['scopes']['manual']
        command = {'action': 'page', 'scope': 'manual', 'group': 'battles', 'page': '1',
                   'period_id': scope['period_id'], 'account_key': 'EU:7', 'request_id': 'accepted'}
        self.window._model.onAction(command)
        for changes in ({'request_id': ''}, {'request_id': 'bad\nrequest'}, {'request_id': b'\xff'},
                        {'request_id': True}, {'request_id': 'x' * 65}, {'period_id': 'expired'},
                        {'account_key': 'EU:other'}):
            self.window._model.onAction(dict(command, page='0', **changes))
            after = self.payload()['scopes']['manual']
            self.assertEqual(after['pagination']['battles']['page'], 1)
            self.assertEqual(after['pagination']['battles']['request_id'], 'accepted')

    def test_offscreen_history_response_and_installation_ids_cross_native_bridge(self):
        for scope in ('launch', 'manual', 'instance'):
            before = self.payload()['scopes'][scope]
            for kind, action, field, identifier in [('maps', 'map_battles', 'map_id', '0'),
                                                     ('vehicles', 'vehicle_battles', 'vehicle_id', '1')]:
                command = {'action': 'page', 'scope': scope, 'group': kind, 'page': '1',
                           'period_id': before['period_id'], 'account_key': 'EU:7'}
                self.window._model.onAction(command)
                self.assertNotIn(identifier, [row['id'] for row in self.payload()['scopes'][scope][kind]])
                command.update(action=action, page='0')
                command[field] = identifier
                self.window._model.onAction(command)
                after = self.payload()['scopes'][scope]
                history = after['battle_history']
                self.assertEqual((history['kind'], history['id']), (kind, identifier))
                self.assertEqual(after['pagination'][kind]['page'], 1)
                self.assertEqual(after['data_revision'], before['data_revision'])
                self.assertEqual(history['battle_list']['total'], 1)
                identifier = history['battle_list']['items'][0]['id']
                if scope == 'instance':
                    self.assertEqual(identifier, self.mod._instance_session.battle_key('EU:7', '0'))


if __name__ == '__main__':
    unittest.main()
