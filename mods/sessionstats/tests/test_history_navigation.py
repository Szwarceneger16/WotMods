# -*- coding: utf-8 -*-
"""Ephemeral date filters, indexed map pages and exact battle navigation."""
from __future__ import unicode_literals

import copy
import shutil
import tempfile
import unittest

from test_core import Clock, EXPECTED, result
import test_native_pagination as native
from grz_session_stats.core import StatsService
from grz_session_stats.projection import DEFAULT_ORDER, ScopeIndex


class HistoryNavigationTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.mkdtemp(prefix='grz-history-navigation-')
        self.clock = Clock(100)
        self.service = StatsService(self.directory, 'EU:7', 'first', EXPECTED,
                                    now=self.clock, timeline_enabled=True)
        self.clock.value = 2000
        self.seed(125)

    def tearDown(self):
        shutil.rmtree(self.directory)

    def seed(self, count):
        rows = {}
        for index in range(count):
            row = result('row-{0:05d}'.format(index), 110 + index, xp_base=index % 43,
                         map_id='map-a' if index % 2 == 0 else 'map-b')
            row.update(_manual_id=self.service._state['current_manual_id'], _launch_id=self.service.launch_id,
                       _updated_at=1000, _result_seen=True, revision=1)
            rows[row['arena_id']] = row
        self.service._state['battles'] = rows
        self.service._rebuild_indexes()

    def finish(self):
        while self.service.timeline_loading:
            self.service.advance_timeline(budget=1, max_steps=512)
        return self.service.timeline_snapshot()

    def test_custom_bounds_are_cooperative_inclusive_from_exclusive_to_without_storage_writes(self):
        state, sequence = copy.deepcopy(self.service._state), self.service.store.sequence
        original = ScopeIndex.build
        def reject(*unused):
            raise AssertionError('Custom selection cannot build synchronously')
        ScopeIndex.build = reject
        try:
            self.assertTrue(self.service.set_timeline_range('__custom__', '__custom__', 120, 130))
            self.assertTrue(self.service.ready)
            self.assertTrue(self.service.timeline_loading)
            placeholder = self.service.timeline_snapshot()
            self.assertEqual((placeholder['from_date'], placeholder['to_date']), (120, 130))
            self.assertEqual(placeholder['battles'], [])
            self.assertTrue(self.service.advance_timeline(budget=1, max_steps=1))
            scope = self.finish()
        finally:
            ScopeIndex.build = original
        self.assertEqual(scope['summary']['battles'], 10)
        self.assertEqual([row['started_at'] for row in scope['battles']], list(range(129, 119, -1)))
        self.assertEqual(scope['started_at'], 120)
        self.assertEqual(self.service._state, state)
        self.assertEqual(self.service.store.sequence, sequence)

    def test_invalid_dates_and_unused_values_leave_the_selected_job_intact(self):
        self.assertTrue(self.service.set_timeline_range('__custom__', '__custom__', 120, 130))
        job = self.service._timeline_job
        invalid = [('__custom__', '', None, None), ('', '__custom__', None, None),
                   ('__custom__', '', -1, None), ('__custom__', '', True, None),
                   ('__custom__', '', float('nan'), None), ('__custom__', '', float('inf'), None),
                   ('__custom__', '__custom__', 130, 120), ('__custom__', '__custom__', 120, 120),
                   ('', '', 120, None), ('', '', None, 130), ('missing', '', None, None)]
        for start, end, lower, upper in invalid:
            self.assertFalse(self.service.set_timeline_range(start, end, lower, upper))
            self.assertIs(self.service._timeline_job, job)

    def test_future_custom_bounds_are_rejected_without_replacing_selected_work(self):
        self.assertTrue(self.service.set_timeline_range('__custom__', '__custom__', 120, 130))
        job = self.service._timeline_job
        selected = self.service._timeline_range, self.service._timeline_dates
        for start, end, lower, upper in (
                ('__custom__', '', 2001, None),
                ('', '__custom__', None, 2001),
                ('__custom__', '__custom__', 120, 2001)):
            self.assertFalse(self.service.set_timeline_range(start, end, lower, upper))
            self.assertIs(self.service._timeline_job, job)
            self.assertEqual((self.service._timeline_range, self.service._timeline_dates), selected)
        self.assertTrue(self.service.set_timeline_range('__custom__', '__custom__', 1999, 2000))
        self.assertEqual(self.service._timeline_bounds, (1999, 2000))

    def test_custom_period_identity_changes_and_saved_points_mix_without_fake_points(self):
        self.clock.value = 150
        self.assertTrue(self.service.create_time_point('Fixture point'))
        point = next(iter(self.service._state['time_points']))
        points = dict(self.service._state['time_points'])
        self.assertTrue(self.service.set_timeline_range('__custom__', point, 120))
        first = self.finish()
        self.assertEqual(first['summary']['battles'], 30)
        self.assertIsNone(first['to_date'])
        self.assertTrue(self.service.set_timeline_range('__custom__', point, 130))
        second = self.finish()
        self.assertNotEqual(first['period_id'], second['period_id'])
        self.assertEqual(second['summary']['battles'], 20)
        self.assertFalse(self.service.set_page('timeline', 'battles', 0, first['period_id']))
        self.assertEqual(self.service._state['time_points'], points)

    def test_zero_timestamp_is_known_but_unknown_start_is_excluded_from_bounded_range(self):
        for identifier, start in (('zero', 0), ('unknown', None)):
            row = result(identifier, start)
            row.update(_manual_id=None, _launch_id=None, _updated_at=1000, _result_seen=True, revision=1)
            self.service._state['battles'][identifier] = row
        self.service._rebuild_indexes()
        self.assertTrue(self.service.set_timeline_range('__custom__', '__custom__', 0, 1))
        self.assertEqual([row['id'] for row in self.finish()['battles']], ['zero'])
        self.assertTrue(self.service.set_timeline_range('', ''))
        scope = self.service.timeline_snapshot()
        self.assertEqual(scope['summary']['battles'], 127)
        self.assertIsNone(scope['from_date'])
        self.assertIsNone(scope['to_date'])

    def test_map_expansion_is_paged_indexed_and_scoped_without_ledger_changes(self):
        before, sequence = copy.deepcopy(self.service._state), self.service.store.sequence
        scope = self.service.snapshot()['scopes']['manual']
        self.assertNotIn('battle_list', scope['maps'][0])
        period = scope['period_id']
        self.assertTrue(self.service.set_map_battles('manual', 'map-a', 1, period))
        scope = self.service.snapshot()['scopes']['manual']
        row = next(row for row in scope['maps'] if row['id'] == 'map-a')
        page = row['battle_list']
        self.assertEqual((page['page'], page['pages'], page['total'], page['page_size']), (1, 7, 63, 10))
        self.assertEqual([item['started_at'] for item in page['items']], list(range(214, 195, -2)))
        self.assertTrue(all(set(item) == {'id', 'name', 'map', 'map_id', 'started_at', 'outcome', 'wn8'} for item in page['items']))
        self.assertTrue(all(item['map_id'] == row['id'] for item in page['items']))
        self.assertTrue(all(item['wn8'] is not None for item in page['items']))
        self.assertNotIn('battle_list', self.service.snapshot()['scopes']['launch']['maps'][0])
        self.assertEqual(self.service._state, before)
        self.assertEqual(self.service.store.sequence, sequence)

    def test_more_direction_changes_reset_pages_and_reject_retained_old_order_requests(self):
        period = self.service.snapshot()['scopes']['manual']['period_id']
        for kind, identifier, setter in [('maps', 'map-a', self.service.set_map_battles),
                                         ('vehicles', '1', self.service.set_vehicle_battles)]:
            self.assertTrue(setter('manual', identifier, 2, period, 'newest'))
            self.assertTrue(self.service.set_order('manual', kind,
                dict(DEFAULT_ORDER, chronology='oldest'), period))
            scope = self.service.snapshot()['scopes']['manual']
            row = next(row for row in scope[kind] if row['id'] == identifier)
            self.assertEqual(row['battle_list']['page'], 0)
            values = [item['started_at'] for item in row['battle_list']['items']]
            self.assertEqual(values, sorted(values))
            self.assertFalse(setter('manual', identifier, 2, period, 'newest'))
            self.assertTrue(setter('manual', identifier, 1, period, 'oldest'))
            patch = self.service.snapshot()['scopes']['manual']['battle_history']
            self.assertEqual(patch['battle_list']['chronology'], 'oldest')
            values = [item['started_at'] for item in patch['battle_list']['items']]
            self.assertEqual(values, sorted(values))
            self.assertTrue(self.service.set_order('manual', kind,
                dict(DEFAULT_ORDER, chronology='first_desc'), period))
            scope = self.service.snapshot()['scopes']['manual']
            row = next(row for row in scope[kind] if row['id'] == identifier)
            self.assertEqual(row['battle_list']['page'], 0)
            values = [item['started_at'] for item in row['battle_list']['items']]
            self.assertEqual(values, sorted(values, reverse=True))

    def test_map_pages_clamp_and_reject_nonmembers_stale_periods_and_bad_pages(self):
        period = self.service.snapshot()['scopes']['manual']['period_id']
        for identifier, page, token in [('missing', 0, period), ('map-a', 0, 'expired'),
                                       ('map-a', -1, period), ('map-a', True, period), ('map-a', 1.5, period)]:
            self.assertFalse(self.service.set_map_battles('manual', identifier, page, token))
        self.assertTrue(self.service.set_map_battles('manual', 'map-a', 999, period))
        page = self.service.snapshot()['scopes']['manual']['maps'][0]['battle_list']
        self.assertEqual((page['page'], len(page['items'])), (6, 3))

    def test_map_order_is_updated_incrementally_when_a_result_moves_map_and_time(self):
        index = self.service._indexes['manual']
        order = index.groups['maps']['map-a'].battle_order
        self.assertTrue(self.service.record_result(result('row-00000', 999, map_id='map-b', reconcile=True)))
        self.assertIs(index.groups['maps']['map-a'].battle_order, order)
        self.assertEqual(len(order), 62)
        page = index.map_battles('map-b', 0)
        self.assertEqual(page['items'][0]['id'], 'row-00000')
        self.assertEqual(len(set(key[1] for key in index.groups['maps']['map-b'].battle_order)), 63)

    def test_map_snapshots_never_scan_all_records(self):
        self.seed(10000)
        index = self.service._indexes['manual']
        class NoScan(dict):
            def __iter__(self):
                raise AssertionError('Snapshot scanned history')
            def values(self):
                raise AssertionError('Snapshot scanned history')
            def items(self):
                raise AssertionError('Snapshot scanned history')
            itervalues = values
            iteritems = items
        index.records = NoScan(index.records)
        for group in index.groups['maps'].values():
            group.records = NoScan(group.records)
        self.assertTrue(self.service.set_map_battles('manual', 'map-a', 100, index.identifier))
        for unused in range(3):
            scope = self.service._scope_snapshot('manual', index, 'Fixture', 100)
            row = next(row for row in scope['maps'] if row['id'] == 'map-a')
            self.assertEqual(len(row['battle_list']['items']), 10)

    def test_select_battle_finds_exact_page_under_full_chronology_and_metric_sort(self):
        scope = self.service.snapshot()['scopes']['manual']
        period = scope['period_id']
        sequence, state = self.service.store.sequence, copy.deepcopy(self.service._state)
        for metric in ('off', 'xp_base', 'xp_received', 'credits_net', 'battle_wn8'):
            for direction in ('asc', 'desc'):
                for chronology in ('oldest', 'newest'):
                    options = dict(DEFAULT_ORDER, metric=metric, direction=direction, chronology=chronology)
                    self.assertTrue(self.service.set_order('manual', 'battles', options, period))
                    for target in ('row-00000', 'row-00060', 'row-00124'):
                        self.assertTrue(self.service.select_battle('manual', target, period, 'fixture-select'))
                        updated = self.service.snapshot()['scopes']['manual']
                        self.assertIn(target, [row['id'] for row in updated['battles']])
                        self.assertEqual(updated['battle_focus'], {'id': target, 'request_id': 'fixture-select'})
        self.assertEqual(self.service.store.sequence, sequence)
        self.assertEqual(self.service._state, state)

    def test_selection_rejects_stale_and_nonmember_ids_and_clear_focus_on_manual_navigation(self):
        period = self.service.snapshot()['scopes']['manual']['period_id']
        for scope, identifier, token, request in [('manual', 'missing', period, 'request'),
                ('manual', 'row-00000', 'expired', 'request'), ('invalid', 'row-00000', period, 'request'),
                ('manual', 'row-00000', period, ''), ('manual', 'row-00000', period, 'bad request')]:
            self.assertFalse(self.service.select_battle(scope, identifier, token, request))
        self.assertTrue(self.service.select_battle('manual', 'row-00000', period, 'request'))
        self.assertTrue(self.service.set_page('manual', 'battles', 0, period))
        self.assertNotIn('battle_focus', self.service.snapshot()['scopes']['manual'])
        self.assertTrue(self.service.select_battle('manual', 'row-00000', period, 'request'))
        self.assertTrue(self.service.set_order('manual', 'battles', DEFAULT_ORDER, period))
        self.assertNotIn('battle_focus', self.service.snapshot()['scopes']['manual'])

    def test_pending_timeline_cannot_open_maps_or_select_battles_and_reset_retires_pages(self):
        self.assertTrue(self.service.set_timeline_range('__custom__', '__custom__', 120, 130))
        period = self.service.timeline_snapshot()['period_id']
        self.assertFalse(self.service.set_map_battles('timeline', 'map-a', 0, period))
        self.assertFalse(self.service.select_battle('timeline', 'row-00010', period, 'request'))
        self.finish()
        self.assertTrue(self.service.set_map_battles('timeline', 'map-a', 0, period))
        self.assertTrue(self.service.select_battle('timeline', 'row-00010', period, 'request'))
        self.assertTrue(self.service.set_timeline_range('__custom__', '__custom__', 130, 140))
        self.assertNotIn('timeline', self.service._map_pages)
        self.assertNotIn('timeline', self.service._battle_focus)
        self.assertFalse(self.service.select_battle('timeline', 'row-00010', period, 'request'))


class NativeHistoryNavigationTests(unittest.TestCase):
    setUp = native.NativePaginationTests.__dict__['setUp']
    tearDown = native.NativePaginationTests.__dict__['tearDown']
    inject_module = native.NativePaginationTests.__dict__['inject_module']
    payload = native.NativePaginationTests.__dict__['payload']

    def test_map_to_battle_navigation_crosses_native_bridge_for_every_scope(self):
        for scope in ('launch', 'manual', 'instance'):
            before = self.payload()['scopes'][scope]
            command = {'scope': scope, 'period_id': before['period_id'], 'account_key': 'EU:7',
                       'action': 'map_battles', 'map_id': '0', 'page': '0'}
            self.window._model.onAction(command)
            opened = next(row for row in self.payload()['scopes'][scope]['maps'] if row['id'] == '0')
            target = opened['battle_list']['items'][0]['id']
            command.update(action='battle_select', id=target, request_id='fixture-jump')
            self.window._model.onAction(command)
            after = self.payload()['scopes'][scope]
            self.assertEqual(after['battle_focus'], {'id': target, 'request_id': 'fixture-jump'})
            self.assertIn(target, [row['id'] for row in after['battles']])
            self.assertEqual(after['summary'], before['summary'])

    def test_stale_account_period_and_closed_model_cannot_change_navigation(self):
        period = self.payload()['scopes']['manual']['period_id']
        base = {'scope': 'manual', 'period_id': period, 'account_key': 'EU:7',
                'action': 'map_battles', 'map_id': '0', 'page': '0'}
        for changes in ({'account_key': 'EU:other'}, {'period_id': 'expired'}, {'page': '-1'},
                        {'page': b'\xff'}, {'map_id': 'missing'}):
            self.window._model.onAction(dict(base, **changes))
        self.assertEqual(self.mod.active_service._map_pages, {})
        old = self.window._model
        self.window.close()
        self.assertTrue(self.window.open())
        old.onAction(base)
        self.assertEqual(self.mod.active_service._map_pages, {})
        self.window._model.onAction(base)
        self.assertIn('manual', self.mod.active_service._map_pages)

    def test_custom_date_commands_accept_numeric_bytes_and_reject_invalid_payloads(self):
        service = self.mod.active_service
        service._timeline_enabled = True
        service._rebuild_indexes()
        command = {'action': 'timeline_range', 'account_key': 'EU:7', 'from_point': '__custom__',
                   'to_point': '__custom__', 'from_date': b'100', 'to_date': b'120'}
        self.window._model.onAction(command)
        self.assertEqual(service._timeline_bounds, (100, 120))
        period = service._timeline_period_id()
        for changes in ({'from_date': 'nan'}, {'to_date': 'inf'}, {'from_date': '-1'},
                        {'from_date': b'\xff'}, {'to_date': '90'}, {'from_point': ''}, {'account_key': 'EU:other'}):
            self.window._model.onAction(dict(command, **changes))
            self.assertEqual(service._timeline_period_id(), period)

    def test_vehicle_to_battle_navigation_crosses_native_bridge_for_every_scope(self):
        for scope in ('launch', 'manual', 'instance'):
            before = self.payload()['scopes'][scope]
            command = {'scope': scope, 'period_id': before['period_id'], 'account_key': 'EU:7',
                       'action': 'vehicle_battles', 'vehicle_id': '1', 'page': '0'}
            self.window._model.onAction(command)
            opened = next(row for row in self.payload()['scopes'][scope]['vehicles'] if row['id'] == '1')
            target = opened['battle_list']['items'][0]['id']
            command.update(action='battle_select', id=target, request_id='fixture-vehicle-jump')
            self.window._model.onAction(command)
            after = self.payload()['scopes'][scope]
            self.assertEqual(after['battle_focus'], {'id': target, 'request_id': 'fixture-vehicle-jump'})
            self.assertIn(target, [row['id'] for row in after['battles']])
            self.assertEqual(after['summary'], before['summary'])

    def test_vehicle_list_bridge_rejects_stale_account_period_and_malformed_page(self):
        period = self.payload()['scopes']['manual']['period_id']
        base = {'scope': 'manual', 'period_id': period, 'account_key': 'EU:7',
                'action': 'vehicle_battles', 'vehicle_id': '1', 'page': '0'}
        for changes in ({'account_key': 'EU:other'}, {'period_id': 'expired'}, {'page': '-1'},
                        {'page': b'\xff'}, {'vehicle_id': 'missing'}):
            self.window._model.onAction(dict(base, **changes))
        self.assertEqual(self.mod.active_service._vehicle_pages, {})
        old = self.window._model
        self.window.close()
        self.assertTrue(self.window.open())
        old.onAction(base)
        self.assertEqual(self.mod.active_service._vehicle_pages, {})
        self.window._model.onAction(base)
        self.assertIn('manual', self.mod.active_service._vehicle_pages)


class VehicleHistoryAndSortTests(unittest.TestCase):
    setUp = HistoryNavigationTests.__dict__['setUp']
    tearDown = HistoryNavigationTests.__dict__['tearDown']
    seed = HistoryNavigationTests.__dict__['seed']
    finish = HistoryNavigationTests.__dict__['finish']

    def test_vehicle_history_is_bounded_and_independent_of_map_and_other_scope_pages(self):
        before, sequence = copy.deepcopy(self.service._state), self.service.store.sequence
        scope = self.service.snapshot()['scopes']['manual']
        period = scope['period_id']
        self.assertNotIn('battle_list', scope['vehicles'][0])
        self.assertTrue(self.service.set_vehicle_battles('manual', '1', 1, period))
        self.assertTrue(self.service.set_map_battles('manual', 'map-a', 0, period))
        updated = self.service.snapshot()['scopes']['manual']
        page = updated['vehicles'][0]['battle_list']
        self.assertEqual((page['page'], page['pages'], page['total'], page['page_size']), (1, 13, 125, 10))
        self.assertEqual([item['started_at'] for item in page['items']], list(range(224, 214, -1)))
        self.assertTrue(all(item['map'] == 'Mapa A' for item in page['items']))
        self.assertEqual(updated['maps'][0]['battle_list']['page'], 0)
        self.assertNotIn('battle_list', self.service.snapshot()['scopes']['launch']['vehicles'][0])
        self.assertEqual(self.service._state, before)
        self.assertEqual(self.service.store.sequence, sequence)

    def test_vehicle_pages_reject_nonmembers_and_retire_on_range_or_manual_reset(self):
        period = self.service.snapshot()['scopes']['manual']['period_id']
        for identifier, page, token in [('missing', 0, period), ('1', 0, 'expired'),
                                       ('1', -1, period), ('1', True, period), ('1', 1.5, period)]:
            self.assertFalse(self.service.set_vehicle_battles('manual', identifier, page, token))
        self.assertTrue(self.service.set_vehicle_battles('manual', '1', 999, period))
        page = self.service.snapshot()['scopes']['manual']['vehicles'][0]['battle_list']
        self.assertEqual((page['page'], len(page['items'])), (12, 5))
        self.assertTrue(self.service.set_timeline_range('__custom__', '__custom__', 120, 130))
        selected = self.service.timeline_snapshot()['period_id']
        self.assertFalse(self.service.set_vehicle_battles('timeline', '1', 0, selected))
        self.finish()
        self.assertTrue(self.service.set_vehicle_battles('timeline', '1', 0, selected))
        self.assertTrue(self.service.set_timeline_range('__custom__', '__custom__', 130, 140))
        self.assertNotIn('timeline', self.service._vehicle_pages)
        self.assertTrue(self.service.reset_manual())
        self.assertNotIn('manual', self.service._vehicle_pages)
        self.assertFalse(self.service.set_vehicle_battles('manual', '1', 0, period))

    def test_vehicle_chronology_updates_incrementally_on_vehicle_and_start_corrections(self):
        index = self.service._indexes['manual']
        order = index.groups['vehicles']['1'].battle_order
        self.assertTrue(self.service.record_result(result('row-00000', 999, vehicle_id=2, reconcile=True)))
        self.assertIs(index.groups['vehicles']['1'].battle_order, order)
        self.assertEqual(len(order), 124)
        page = index.vehicle_battles('2', 0)
        self.assertEqual([row['id'] for row in page['items']], ['row-00000'])
        self.assertNotIn('row-00000', [key[1] for key in order])

    def test_ten_thousand_vehicle_records_are_sliced_without_rescanning(self):
        self.seed(10000)
        index = self.service._indexes['manual']
        class NoScan(dict):
            def __iter__(self):
                raise AssertionError('Snapshot scanned vehicle history')
            def values(self):
                raise AssertionError('Snapshot scanned vehicle history')
            def items(self):
                raise AssertionError('Snapshot scanned vehicle history')
            itervalues = values
            iteritems = items
        index.records = NoScan(index.records)
        index.groups['vehicles']['1'].records = NoScan(index.groups['vehicles']['1'].records)
        self.assertTrue(self.service.set_vehicle_battles('manual', '1', 100, index.identifier))
        for unused in range(3):
            scope = self.service._scope_snapshot('manual', index, 'Fixture', 100)
            self.assertEqual(len(scope['vehicles'][0]['battle_list']['items']), 10)

    def test_active_net_credit_sort_value_is_per_battle_statistic_not_visible_period_sum(self):
        rows = {}
        # Vehicle1 has a larger maximum but a smaller total than vehicle2.
        for identifier, vehicle, timestamp, net in [('a', 1, 120, 1000), ('b', 1, 121, -900),
                                                     ('c', 2, 122, 600), ('d', 2, 123, 600)]:
            row = result(identifier, timestamp, vehicle_id=vehicle)
            row['currencies']['credits'] = {'income': net + 1000, 'costs': 1000, 'net': net}
            row.update(_manual_id=self.service._state['current_manual_id'], _launch_id=self.service.launch_id,
                       _updated_at=1000, _result_seen=True, revision=1)
            rows[identifier] = row
        unknown = result('unknown', 124, vehicle_id=3, outcome=None, complete=False)
        unknown.update(_manual_id=self.service._state['current_manual_id'], _launch_id=self.service.launch_id,
                       _updated_at=1000, _result_seen=True, revision=1)
        rows['unknown'] = unknown
        self.service._state['battles'] = rows
        self.service._rebuild_indexes()
        period = self.service.snapshot()['scopes']['manual']['period_id']
        for statistic, expected, values in [('max', ['1', '2', '3'], [1000, 600, None]),
                                             ('avg', ['2', '1', '3'], [600, 50, None]),
                                             ('min', ['2', '1', '3'], [600, -900, None])]:
            self.assertTrue(self.service.set_order('manual', 'vehicles',
                dict(DEFAULT_ORDER, metric='credits_net', statistic=statistic, direction='desc'), period))
            vehicles = self.service.snapshot()['scopes']['manual']['vehicles']
            self.assertEqual([row['id'] for row in vehicles], expected)
            self.assertEqual([row['sort_value'] for row in vehicles], values)
            totals = dict((row['id'], row['stats']['currencies']['credits']['net']) for row in vehicles)
            self.assertEqual(totals, {'1': 100, '2': 1200, '3': None})
        self.assertTrue(self.service.set_order('manual', 'vehicles', DEFAULT_ORDER, period))
        self.assertNotIn('sort_value', self.service.snapshot()['scopes']['manual']['vehicles'][0])


if __name__ == '__main__':
    unittest.main()
