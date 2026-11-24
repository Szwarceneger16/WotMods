# -*- coding: utf-8 -*-
"""Bounded page acknowledgements and coherent incremental page caches."""
from __future__ import unicode_literals

import copy
import unittest

import test_history_navigation as history
from test_native_pagination import NativePaginationFixture
from test_core import EXPECTED, result
from grz_session_stats.core import StatsService
from grz_session_stats.projection import DEFAULT_ORDER


class PageCacheProtocolTests(unittest.TestCase):
    setUp = history.HistoryNavigationTests.__dict__['setUp']
    tearDown = history.HistoryNavigationTests.__dict__['tearDown']
    seed = history.HistoryNavigationTests.__dict__['seed']
    finish = history.HistoryNavigationTests.__dict__['finish']

    def scope(self):
        return self.service.snapshot()['scopes']['manual']

    def test_page_request_resolves_a_battle_that_moved_across_the_boundary(self):
        before = self.scope()
        period = before['period_id']
        anchor = before['battles'][-1]['id']
        self.assertTrue(self.service.record_result(result('newest', 1000)))
        self.assertNotIn(anchor, [row['id'] for row in self.scope()['battles']])

        self.assertTrue(self.service.set_page('manual', 'battles', 0, period, 'refresh', anchor, before['order_epoch']))
        scope = self.scope()
        self.assertEqual(scope['pagination']['battles']['page'], 1)
        self.assertEqual(scope['pagination']['battles']['request_id'], 'refresh')
        self.assertEqual(scope['battles'][0]['id'], anchor)
        self.assertNotIn('battle_focus', scope)

        self.assertTrue(self.service.set_page('manual', 'battles', 0, period, 'fallback', 'missing'))
        self.assertEqual(self.scope()['pagination']['battles']['page'], 0)

    def test_loading_a_new_timeline_projection_preserves_the_selected_battle(self):
        service = StatsService(self.directory, 'EU:8', 'first', EXPECTED, self.clock,
                               started_at=100, timeline_enabled=True)
        for index in range(40):
            self.assertTrue(service.record_result(result('battle-%02d' % index, 110 + index)))
        self.assertTrue(service.set_timeline_range('__custom__', '', 105))
        while service.timeline_loading:
            service.advance_timeline()
        period = service.timeline_snapshot()['period_id']
        self.assertTrue(service.select_battle('timeline', 'battle-00', period, 'selected'))

        peer = StatsService(self.directory, 'EU:8', 'second', EXPECTED, self.clock)
        self.assertTrue(peer.record_result(result('newest', 1000)))
        self.assertTrue(service.refresh_capture_history())
        self.assertTrue(service.timeline_snapshot()['loading'])
        while service.timeline_loading:
            service.advance_timeline()

        scope = service.timeline_snapshot()
        self.assertEqual(scope['battle_focus'], {'id': 'battle-00', 'request_id': 'selected'})
        self.assertEqual(scope['pagination']['battles']['page'], 1)

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
        first_history = self.scope()['history_navigation_revision']
        self.assertGreater(first_history, before['history_navigation_revision'])
        self.assertTrue(self.service.set_vehicle_battles('manual', '1', 0, period))
        second_history = self.scope()['history_navigation_revision']
        self.assertGreater(second_history, first_history)
        self.assertTrue(self.service.select_battle('manual', 'row-00000', period, 'jump-1'))
        self.assertEqual(self.scope()['history_navigation_revision'], second_history)
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

    def test_sort_echo_identifies_the_command_even_when_options_match_the_previous_order(self):
        initial = self.scope()
        period = initial['period_id']
        first = dict(DEFAULT_ORDER)
        self.assertTrue(self.service.set_order('manual', 'battles', first, period, 'sort-first'))
        second = dict(DEFAULT_ORDER, metric='xp_base')
        self.assertTrue(self.service.set_order('manual', 'battles', second, period, 'sort-second'))
        self.assertTrue(self.service.set_order('manual', 'battles', first, period, b'sort-third'))
        self.assertTrue(self.service.set_page('manual', 'battles', 1, period, 'page-new'))
        snapshot = self.scope()
        meta = snapshot['pagination']['battles']
        self.assertEqual(snapshot['ordering']['battles'], first)
        self.assertEqual(meta['order_request_id'], 'sort-third')
        self.assertEqual(meta['request_id'], 'page-new')
        self.assertNotIn('order_request_id', snapshot['pagination']['maps'])
        self.assertNotIn('order_request_id', initial['pagination']['battles'])
        self.assertEqual(snapshot['order_epoch'], initial['order_epoch'])
        self.assertFalse(self.service.set_order('manual', 'battles', second, period, 'invalid request'))
        self.assertEqual(self.scope()['ordering']['battles'], first)
        self.assertTrue(self.service.set_order('manual', 'battles', second, period))
        without_request = self.scope()
        self.assertNotEqual(without_request['order_epoch'], snapshot['order_epoch'])
        self.assertNotIn('order_request_id', without_request['pagination']['battles'])
        self.assertTrue(self.service.set_order('manual', 'battles', second, period, 'before-reset'))
        self.assertTrue(self.service.reset_manual())
        self.assertNotIn('order_request_id', self.scope()['pagination']['battles'])

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

    def test_returning_to_a_timeline_range_rejects_all_previous_navigation_owners(self):
        self.assertTrue(self.service.set_timeline_range('__custom__', '__custom__', 120, 130))
        initial = self.finish()
        period, epoch = initial['period_id'], initial['order_epoch']
        self.assertTrue(self.service.set_order('timeline', 'battles', DEFAULT_ORDER, period, 'first', epoch))
        self.assertTrue(self.service.set_timeline_range('', ''))
        intervening = self.service.timeline_snapshot()
        self.assertTrue(self.service.set_timeline_range('__custom__', '__custom__', 120, 130))
        loading = self.service.timeline_snapshot()
        self.assertTrue(loading['loading'])
        self.assertEqual(loading['period_id'], period)
        prefix, counter = epoch.rsplit(':', 1)
        self.assertEqual(intervening['order_epoch'], '{0}:{1}'.format(prefix, int(counter) + 1))
        self.assertEqual(loading['order_epoch'], '{0}:{1}'.format(prefix, int(counter) + 2))
        returned = self.finish()
        self.assertEqual(returned['order_epoch'], loading['order_epoch'])
        self.assertNotIn('order_request_id', returned['pagination']['battles'])
        self.assertFalse(self.service.set_order('timeline', 'battles', DEFAULT_ORDER, period, 'stale', epoch))
        self.assertFalse(self.service.set_page('timeline', 'battles', 3, period, 'stale', order_epoch=epoch))
        self.assertFalse(self.service.set_map_battles('timeline', 'map-a', 2, period, order_epoch=epoch))
        self.assertFalse(self.service.set_vehicle_battles('timeline', '1', 2, period, order_epoch=epoch))
        self.assertFalse(self.service.select_battle('timeline', 'row-00010', period, 'stale', epoch))
        self.assertNotIn('battle_history', self.service.timeline_snapshot())
        self.assertNotIn('battle_focus', self.service.timeline_snapshot())
        self.assertTrue(self.service.set_order('timeline', 'battles', DEFAULT_ORDER, period, 'latest', returned['order_epoch']))
        self.assertEqual(self.service.timeline_snapshot()['pagination']['battles']['order_request_id'], 'latest')
        current = returned['order_epoch']
        self.assertTrue(self.service.set_page('timeline', 'battles', 0, period, 'latest-page', order_epoch=current))
        self.assertTrue(self.service.set_map_battles('timeline', 'map-a', 0, period, order_epoch=current))
        self.assertTrue(self.service.set_vehicle_battles('timeline', '1', 0, period, order_epoch=current))
        self.assertTrue(self.service.select_battle('timeline', 'row-00010', period, 'latest-battle', current))

    def test_anchored_page_finds_a_battle_that_moved_inside_map_and_vehicle_history(self):
        self.seed(10)
        for row in self.service._state['battles'].values():
            row['map_id'] = 'map-a'
        self.service._rebuild_indexes()
        initial = self.scope()
        period, epoch = initial['period_id'], initial['order_epoch']
        kinds = (('maps', 'map-a', self.service.set_map_battles),
                 ('vehicles', '1', self.service.set_vehicle_battles))
        for kind, identifier, open_history in kinds:
            self.assertTrue(open_history('manual', identifier, 0, period, order_epoch=epoch))
        self.assertTrue(self.service.record_result(result('fixture-recent', 500, map_id='map-a')))
        for kind, identifier, unused in kinds:
            for chronology, expected in (('newest', 1), ('oldest', 0)):
                options = dict(DEFAULT_ORDER, chronology=chronology)
                self.assertTrue(self.service.set_order('manual', kind, options, period))
                prior_navigation = self.scope()['history_navigation_revision']
                self.assertTrue(self.service.set_page('manual', kind, 0, period, 'return-test', identifier,
                                                      epoch, 'row-00000'))
                scope = self.scope()
                self.assertGreater(scope['history_navigation_revision'], prior_navigation)
                detail = next(row['battle_list'] for row in scope[kind] if row['id'] == identifier)
                self.assertEqual(scope['pagination'][kind]['request_id'], 'return-test')
                self.assertEqual(detail['page'], expected)
                self.assertIn('row-00000', [row['id'] for row in detail['items']])
                self.assertEqual(scope['battle_history']['battle_list'], detail)
                self.assertTrue(self.service.set_page('manual', kind, 0, period, 'missing-battle', identifier,
                                                      epoch, 'absent-fixture'))
                unchanged = self.scope()
                self.assertEqual(next(row['battle_list'] for row in unchanged[kind] if row['id'] == identifier), detail)
                self.assertEqual(unchanged['history_navigation_revision'], scope['history_navigation_revision'])
        self.assertFalse(self.service.set_page('manual', 'tiers', 0, period, 'wrong-group', '1', epoch, 'row-00000'))
        self.assertFalse(self.service.set_page('manual', 'maps', 0, period, 'missing-group', order_epoch=epoch,
                                               history_anchor_id='row-00000'))

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


class NativePageCacheProtocolTests(NativePaginationFixture, unittest.TestCase):
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
                        {'account_key': 'EU:other'}, {'order_epoch': 'expired:1'}):
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
                command.update(action='page', anchor_id=history['id'], history_anchor_id=identifier,
                               request_id='return-history', order_epoch=before['order_epoch'])
                self.window._model.onAction(command)
                restored = self.payload()['scopes'][scope]
                card = next(row for row in restored[kind] if row['id'] == history['id'])
                self.assertEqual(card['battle_list']['items'][0]['id'], identifier)
                self.assertEqual(restored['pagination'][kind]['request_id'], 'return-history')


if __name__ == '__main__':
    unittest.main()
