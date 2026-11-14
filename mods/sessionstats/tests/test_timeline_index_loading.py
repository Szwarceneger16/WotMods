# -*- coding: utf-8 -*-
"""Selected history is projected in bounded slices, independently of account loading."""
from __future__ import unicode_literals

import shutil
import tempfile
import unittest

from test_core import Clock, EXPECTED, result
from test_runtime import START
import test_runtime as runtime_fixtures
from grz_session_stats.core import StatsService, aggregate_stats
from grz_session_stats.projection import DEFAULT_ORDER, ScopeIndex


class TimelineLoadingHelpers(object):
    def assert_statistics_equal(self, actual, expected):
        if isinstance(expected, dict):
            self.assertEqual(set(actual), set(expected))
            for key in expected:
                self.assert_statistics_equal(actual[key], expected[key])
        elif isinstance(expected, float):
            self.assertAlmostEqual(actual, expected, delta=max(0.0000001, abs(expected) * 0.0000000001))
        else:
            self.assertEqual(actual, expected)

    def point(self, timestamp, service=None):
        service = service or self.service
        self.clock.value = timestamp
        previous = set(service._time_points())
        self.assertTrue(service.create_time_point())
        return (set(service._time_points()) - previous).pop()

    def finish_timeline(self, service=None):
        service = service or self.service
        slices = 0
        while service.timeline_loading:
            pending = service.advance_timeline(budget=1.0, max_steps=512)
            self.assertEqual(pending, service.timeline_loading)
            slices += 1
            self.assertLess(slices, 1000)
        return service.timeline_snapshot()

    def selected_rows(self, service, lower, upper):
        return [row for row in service._state['battles'].values()
                if row.get('started_at') is not None and lower <= row['started_at'] < upper]


class TimelineIndexLoadingTests(TimelineLoadingHelpers, unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.mkdtemp(prefix='grz-timeline-loading-')
        self.clock = Clock(100)
        self.service = self.open_service('EU:7', 'first')

    def tearDown(self):
        shutil.rmtree(self.directory)

    def open_service(self, account, launch):
        return StatsService(self.directory, account, launch, EXPECTED, now=self.clock,
                            timeline_enabled=True)

    def small_history(self):
        lower, upper = self.point(130), self.point(170)
        self.clock.value = 200
        for identifier, timestamp in [('early', 135), ('middle', 145), ('late', 155),
                                      ('outside', 120), ('unknown', None)]:
            self.assertTrue(self.service.record_result(result(identifier, timestamp)))
        return lower, upper

    def test_ten_thousand_records_never_build_during_selection_or_snapshot(self):
        lower, upper = self.point(100), self.point(20000)
        # Seed a synthetic loaded archive and rebuild once. This performance
        # fixture must not perform ten thousand separate durable disk commits.
        rows = {}
        for position in range(10000):
            row = result(str(position), 101 + position, vehicle_id=1 + position % 2,
                         ended_at=102 + position, map_id='map-' + str(position % 3))
            row.update(_launch_id=self.service.launch_id,
                       _manual_id=self.service._state['current_manual_id'],
                       _updated_at=20000, _result_seen=True, revision=1)
            rows[row['arena_id']] = row
        self.service._state['battles'] = rows
        self.service._rebuild_indexes()
        original_build, original_steps, original_replace = (ScopeIndex.build,
                                                            ScopeIndex.build_steps,
                                                            ScopeIndex.replace)
        replacements = []

        def reject_build(*unused, **keywords):
            raise AssertionError('A selected snapshot must not rebuild the archive')

        def count_replace(index, record, item):
            if index.identifier.startswith('timeline:'):
                replacements.append(record['arena_id'])
            return original_replace(index, record, item)

        ScopeIndex.build = ScopeIndex.build_steps = reject_build
        ScopeIndex.replace = count_replace
        try:
            self.assertTrue(self.service.set_timeline_range(lower, upper))
            self.assertTrue(self.service.timeline_loading)
            self.assertFalse(self.service.loading)
            self.assertTrue(self.service.ready)
            for unused in range(3):
                placeholder = self.service.timeline_snapshot()
                self.assertTrue(placeholder['loading'])
                self.assertEqual(placeholder['battles'], [])
            self.assertEqual(replacements, [])
            self.assertEqual(self.service.snapshot()['scopes']['launch']['summary']['battles'], 10000)
            self.assertTrue(self.service.advance_timeline(budget=1.0, max_steps=1))
            self.assertEqual(len(replacements), 1)
            self.assertTrue(self.service.timeline_snapshot()['loading'])
            self.assertEqual(len(replacements), 1)
            scope = self.finish_timeline()
            self.assertFalse(scope['loading'])
            self.assertEqual(len(replacements), 10000)
            self.assertEqual(len(set(replacements)), 10000)
            self.assert_statistics_equal(scope['summary'], aggregate_stats(list(rows.values()), self.service.expected_table))
            self.assertEqual(scope['pagination']['battles']['total'], 10000)
            self.assertEqual(len(scope['battles']), 40)
            self.assertEqual(scope['pagination']['vehicles']['total'], 2)
            self.assertEqual(scope['pagination']['maps']['total'], 3)
        finally:
            ScopeIndex.build, ScopeIndex.build_steps, ScopeIndex.replace = original_build, original_steps, original_replace

    def test_live_revisions_before_and_after_cursor_match_the_authoritative_ledger(self):
        lower, upper = self.small_history()
        self.assertTrue(self.service.set_timeline_range(lower, upper))
        self.assertTrue(self.service.advance_timeline(budget=1.0, max_steps=1))
        candidate = self.service._timeline_job['index']
        self.assertEqual(set(candidate.records), set(['early']))
        updates = [
            result('early', 125, reconcile=True),  # Previously processed, now outside.
            result('late', 132, vehicle_id=2, map_id='map-b', reconcile=True),
            result('new-before-cursor', 133, damage=2300),
            result('new-after-cursor', 165, damage=3400),
            result('unknown', 160, reconcile=True),
            result('outside', 142, damage=1700, reconcile=True),
            result('middle', 180, reconcile=True),  # Future cursor entry leaves range.
        ]
        for update in updates:
            self.assertTrue(self.service.record_result(update))
        original_replace = candidate.replace

        def reject_duplicate(*unused):
            raise AssertionError('Live contributions must not be removed and added again')

        candidate.replace = reject_duplicate
        try:
            scope = self.finish_timeline()
        finally:
            candidate.replace = original_replace
        self.assertNotIn('load_error', scope)
        self.assertIs(self.service._filtered_timeline, candidate)
        expected = self.selected_rows(self.service, 130, 170)
        self.assertEqual(scope['summary'], aggregate_stats(expected, self.service.expected_table))
        self.assertEqual([row['id'] for row in scope['battles']],
                         ['new-after-cursor', 'unknown', 'outside', 'new-before-cursor', 'late'])
        self.assertEqual(scope['summary']['battles'], 5)
        self.assertEqual(scope['pagination']['vehicles']['total'], 2)

    def test_beginning_bound_preserves_known_zero_time_but_excludes_unknown_and_upper_endpoint(self):
        lower, upper = self.point(130), self.point(170)
        self.clock.value = 200
        for identifier, timestamp in [('a-unknown', None), ('b-zero', 0),
                                      ('c-upper', 170), ('d-inside', 169), ('e-lower', 130)]:
            self.assertTrue(self.service.record_result(result(identifier, timestamp)))
        self.assertTrue(self.service.set_timeline_range('', upper))
        scope = self.finish_timeline()
        self.assertEqual([row['id'] for row in scope['battles']], ['d-inside', 'e-lower', 'b-zero'])
        self.assertEqual(scope['battles'][-1]['started_at'], 0)
        self.assertTrue(self.service.set_timeline_range(lower, upper))
        bounded = self.finish_timeline()
        self.assertEqual([row['id'] for row in bounded['battles']], ['d-inside', 'e-lower'])

    def test_unrelated_updates_keep_the_completed_projection_and_its_sort_cache(self):
        lower, upper = self.small_history()
        self.assertTrue(self.service.set_timeline_range(lower, upper))
        before = self.finish_timeline()
        index = self.service._filtered_timeline
        sort_cache = index._sort_cache
        self.assertTrue(self.service.record_result(result('outside', 120, damage=9999, reconcile=True)))
        self.assertIs(self.service._filtered_timeline, index)
        self.assertIs(index._sort_cache, sort_cache)
        self.assertFalse(self.service.timeline_loading)
        self.assertEqual(self.service.timeline_snapshot(), before)
        self.assertTrue(self.service.record_result(result('early', 135, xp_base=1700, reconcile=True)))
        self.assertIs(self.service._filtered_timeline, index)
        self.assertFalse(self.service.timeline_loading)
        after = self.service.timeline_snapshot()
        self.assertEqual(after['summary']['battles'], 3)
        self.assertEqual(after['summary']['xp_base']['sum'], 2700)

    def test_range_changes_cancel_the_previous_candidate_and_stale_page_ownership(self):
        lower, upper = self.small_history()
        self.assertTrue(self.service.set_timeline_range(lower, upper))
        first = self.service.timeline_snapshot()
        self.assertFalse(self.service.set_page('timeline', 'battles', 0, first['period_id']))
        self.assertFalse(self.service.set_order('timeline', 'battles', dict(DEFAULT_ORDER), first['period_id']))
        self.service.advance_timeline(budget=1.0, max_steps=1)
        old_candidate = self.service._timeline_job['index']
        self.assertTrue(self.service.set_timeline_range('', lower))
        second = self.service.timeline_snapshot()
        self.assertNotEqual(first['period_id'], second['period_id'])
        self.assertFalse(self.service.set_page('timeline', 'battles', 0, first['period_id']))
        scope = self.finish_timeline()
        self.assertEqual([row['id'] for row in scope['battles']], ['outside'])
        self.assertIsNot(self.service._filtered_timeline, old_candidate)
        self.assertTrue(self.service.set_page('timeline', 'battles', 0, scope['period_id']))
        self.assertTrue(self.service.set_order('timeline', 'battles', dict(DEFAULT_ORDER), scope['period_id']))
        self.assertEqual(self.service.timeline_snapshot()['summary'], scope['summary'])
        self.assertTrue(self.service.set_timeline_range(lower, upper))
        self.assertTrue(self.service.timeline_loading)
        self.assertTrue(self.service.set_timeline_range('', ''))
        self.assertFalse(self.service.timeline_loading)
        self.assertFalse(self.service.advance_timeline())
        full = self.service.timeline_snapshot()
        self.assertFalse(full['loading'])
        self.assertEqual(full['summary']['battles'], 5)
        self.assertEqual(len(old_candidate.records), 1)

    def test_pending_projections_and_markers_are_isolated_between_accounts(self):
        lower, upper = self.small_history()
        other = self.open_service('EU:8', 'other')
        other_lower, other_upper = self.point(210, other), self.point(250, other)
        self.clock.value = 260
        self.assertTrue(other.record_result(result('early', 220, damage=8000)))
        self.assertFalse(other.set_timeline_range(lower, upper))
        self.assertTrue(self.service.set_timeline_range(lower, upper))
        self.assertTrue(other.set_timeline_range(other_lower, other_upper))
        selected = self.finish_timeline()
        self.assertTrue(other.timeline_loading)
        self.assertTrue(other.timeline_snapshot()['loading'])
        other_scope = self.finish_timeline(other)
        self.assertEqual(selected['summary']['battles'], 3)
        self.assertEqual(other_scope['summary']['battles'], 1)
        self.assertNotEqual(selected['summary']['wn8'], other_scope['summary']['wn8'])
        restored = self.open_service('EU:7', 'restored')
        self.assertFalse(restored.timeline_loading)
        self.assertEqual(restored.timeline_snapshot()['from_point'], '')
        self.assertTrue(restored.set_timeline_range(lower, upper))
        self.assertEqual(self.finish_timeline(restored)['summary'], selected['summary'])

    def test_projection_error_does_not_publish_a_prefix_or_make_account_read_only(self):
        lower, upper = self.small_history()
        self.assertTrue(self.service.set_timeline_range(lower, upper))
        self.service.advance_timeline(budget=1.0, max_steps=1)
        original = self.service._update_timeline_record

        def fail_projection(*unused):
            raise RuntimeError('Synthetic projection failure')

        self.service._update_timeline_record = fail_projection
        try:
            self.assertFalse(self.service.advance_timeline())
        finally:
            self.service._update_timeline_record = original
        scope = self.service.timeline_snapshot()
        self.assertTrue(scope['load_error'])
        self.assertEqual(scope['battles'], [])
        self.assertTrue(self.service.ready)
        self.assertFalse(self.service.loading)
        self.assertFalse(self.service.store.read_only)
        self.assertTrue(self.service.record_result(result('still-durable', 150)))
        self.assertTrue(self.service.set_timeline_range(lower, upper))
        retried = self.finish_timeline()
        self.assertNotIn('load_error', retried)
        self.assertEqual(retried['summary']['battles'], 4)


class TimelineRuntimeLoadingTests(TimelineLoadingHelpers, unittest.TestCase):
    no_footer = runtime_fixtures.RuntimeTests.__dict__['no_footer']

    def setUp(self):
        runtime_fixtures.RuntimeTests.__dict__['setUp'](self)
        self.service = self.mod.active_service

    def tearDown(self):
        runtime_fixtures.RuntimeTests.__dict__['tearDown'](self)

    def select_history(self):
        lower, upper = self.point(START), self.point(START + 20)
        self.clock.value = START + 30
        for position in range(6):
            self.assertTrue(self.service.record_result(result(str(position), START + position)))
        self.mod.on_action({'action': 'timeline_range', 'account_key': self.mod.active_key,
                            'from_point': lower, 'to_point': upper})

    def test_runtime_schedules_ready_account_projection_and_defers_it_during_battle(self):
        self.select_history()
        self.assertTrue(self.service.ready)
        self.assertFalse(self.service.loading)
        self.assertTrue(self.service.timeline_loading)
        callback_id = self.mod._load_id
        self.assertIsNotNone(callback_id)
        self.assertEqual(self.api.callbacks[callback_id][0], 0.01)
        self.api.battle = True
        self.api.fire(callback_id)
        self.assertTrue(self.service.timeline_loading)
        self.assertEqual(self.service._timeline_job['index'].records, {})
        self.assertEqual(self.api.callbacks[self.mod._load_id][0], 1.0)
        self.api.battle = False
        before = self.window.refreshes
        for unused in range(20):
            if not self.service.timeline_loading:
                break
            self.api.fire(self.mod._load_id)
        self.assertFalse(self.service.timeline_loading)
        self.assertEqual(self.service.timeline_snapshot()['summary']['battles'], 6)
        self.assertGreater(self.window.refreshes, before)

    def test_shutdown_cancels_pending_projection_and_its_stale_scheduled_callback(self):
        self.select_history()
        callback_id = self.mod._load_id
        callback = self.api.callbacks[callback_id][1]
        self.mod.stop()
        before = self.window.refreshes
        self.assertFalse(self.service.timeline_loading)
        self.assertNotIn(callback_id, self.api.callbacks)
        callback()
        self.assertFalse(self.service.timeline_loading)
        self.assertEqual(self.window.refreshes, before)


if __name__ == '__main__':
    unittest.main()
