# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import shutil
import tempfile
import unittest

from test_core import EXPECTED, result
from test_normalize import raw_result
from test_runtime import Clock
from grz_session_stats.core import StatsService
from grz_session_stats.normalize import normalize_result


class TimelineAndBattleDetailsTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.mkdtemp()
        self.clock = Clock(100)
        self.service = self.open_service('first')

    def tearDown(self):
        shutil.rmtree(self.directory)

    def open_service(self, launch, account='EU:7'):
        return StatsService(self.directory, account, launch, EXPECTED, now=self.clock, timeline_enabled=True)

    def test_timeline_keeps_legacy_boundaries_and_filters_all_groups_by_battle_start(self):
        self.clock.value = 130
        self.assertTrue(self.service.record_result(result('old', 110)))
        legacy = self.service.reset_manual()
        self.clock.value = 140
        self.assertTrue(self.service.create_time_point())
        self.assertEqual(self.service.timeline_snapshot()['summary']['battles'], 1)
        points = self.service.timeline_snapshot()['time_points']
        self.assertEqual(points[0], (legacy, 130))
        cutoff = points[1][0]
        self.clock.value = 190
        self.assertTrue(self.service.record_result(result('first', 130)))
        self.assertTrue(self.service.record_result(result('last', 140)))
        self.assertTrue(self.service.record_result(result('unknown', None)))
        self.assertTrue(self.service.set_timeline_range(legacy, cutoff))
        scope = self.service.timeline_snapshot()
        self.assertEqual([row['id'] for row in scope['battles']], ['first'])
        self.assertEqual(scope['summary']['battles'], 1)
        self.assertEqual(scope['vehicles'][0]['stats']['battles'], 1)
        self.assertTrue(self.service.set_page('timeline', 'battles', 0, scope['period_id']))
        self.assertFalse(self.service.set_timeline_range(cutoff, legacy))
        self.assertFalse(self.service.set_timeline_range('another-account', ''))
        self.assertEqual(self.service.timeline_snapshot(), scope)
        self.clock.value = 200
        self.assertTrue(self.service.record_result(result('late', 135)))
        self.assertEqual(self.service.timeline_snapshot()['summary']['battles'], 2)
        self.assertTrue(self.service.set_timeline_range('', ''))
        self.assertEqual(self.service.timeline_snapshot()['summary']['battles'], 5)
        restored = self.open_service('second')
        self.assertEqual(restored.timeline_snapshot()['time_points'], points)
        self.assertEqual(restored.timeline_snapshot()['summary']['battles'], 5)
        self.assertEqual(self.open_service('other', 'EU:8').timeline_snapshot()['time_points'], [])

    def test_normalize_confirmed_crucible_and_points_without_counting_allocations_twice(self):
        raw = raw_result()
        active = 'challenge:8:2'
        avatar = raw['personal']['avatar']
        avatar.update(bpTopPoints=8, eventBattlePassPoints=10, bpBonusPoints=15,
                      bpNonChapterPointsDiff=33, bpChaptersInfo={5: (10, 43)},
                      fairplayViolations=(0, 2, 0),
                      questsProgress={active + ':fail': ('group', {}, {'bonusCount': 1})})
        raw['personal'][1].update(boosterCredits=1000, dailyXPFactor10=20,
                                  questsProgress={'daily:test': ('group', {}, {'bonusCount': 1})})
        details = normalize_result(raw, {'active_crucible': active})['details']
        self.assertEqual(details['pass_points'], {'battle': 8, 'missions': 10, 'vehicle': 15, 'credited': 33})
        self.assertEqual(details['bonuses']['boosterCredits'], 1000)
        self.assertEqual(details['bonuses']['dailyXPFactor10'], 20)
        self.assertTrue(details['suicide'])
        self.assertEqual(details['missions'][active]['status'], 'failed')
        self.assertEqual(details['missions']['daily:test']['status'], 'completed')
        avatar['questsProgress'][active] = ('group', {}, {'bonusCount': 1})
        self.assertEqual(normalize_result(raw)['details']['missions'][active]['status'], 'completed')

    def test_active_crucible_and_confirmed_result_survive_reopen_and_partial_retry(self):
        active = 'challenge:8:2'
        self.clock.value = 110
        self.assertTrue(self.service.begin_battle('1', 110, mode='random', details={
            'active_crucible': active, 'missions': {active: {'name': '<b>Fixture mission</b>', 'kind': 'crucible', 'stage': 2}},
        }))
        self.assertNotIn('status', self.service.timeline_snapshot()['battles'][0]['details']['missions'][active])
        self.assertTrue(self.service.record_result(result(details={'missions': {active: {'status': 'completed'}}})))
        self.service.record_result(result(details={'missions': {active: {'status': 'observed'}}}, reconcile=True))
        self.clock.value = 120
        restored = self.open_service('second')
        self.assertEqual(restored.result_context('1')['active_crucible'], active)
        mission = restored.timeline_snapshot()['battles'][0]['details']['missions'][active]
        self.assertEqual(mission, {'kind': 'crucible', 'stage': 2, 'name': 'Fixture mission', 'status': 'completed'})
