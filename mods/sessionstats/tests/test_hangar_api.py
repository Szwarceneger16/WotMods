# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import datetime
import shutil
import tempfile
import time
import unittest

from test_core import EXPECTED, result
from test_runtime import Clock, Obj
from grz_session_stats import runtime as runtime_module
from grz_session_stats.core import StatsService
from grz_session_stats.hangar import read_snapshot


def local_stamp(date, hour=12):
    return time.mktime((date.year, date.month, date.day, hour, 0, 0, 0, 0, -1))


class HangarAPITests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.mkdtemp()
        self.today = datetime.date(2026, 11, 5)
        self.clock = Clock(local_stamp(self.today))
        self.service = StatsService(self.directory, 'EU:7', 'launch', EXPECTED,
                                    now=self.clock, timeline_enabled=True)
        self.api = Obj(is_replay=lambda: False, in_battle=lambda: False,
                       account_dbid=lambda: 7, region='EU')
        self.runtime = Obj(running=True, api=self.api, active_key='EU:7',
                           active_service=self.service, now=self.clock)

    def tearDown(self):
        shutil.rmtree(self.directory)

    def add(self, identifier, date=None, vehicle_id=1, **updates):
        started = local_stamp(date or self.today)
        self.assertTrue(self.service.record_result(result(
            identifier, started_at=started, vehicle_id=vehicle_id,
            ended_at=started + 5, **updates)))

    def test_full_history_groups_ignore_ui_page_reset_and_timeline_range(self):
        yesterday = self.today - datetime.timedelta(days=1)
        self.add('old', yesterday)
        self.assertTrue(self.service.reset_manual())
        for identifier in range(1, 46):
            self.add(str(identifier), vehicle_id=identifier)
        self.assertTrue(self.service.create_time_point('Current point'))
        point = next(iter(self.service._state['time_points']))
        self.assertTrue(self.service.set_timeline_range(point, ''))
        sequence = self.service.store.sequence
        snapshot = read_snapshot(self.runtime, list(range(1, 46)))
        self.assertEqual(snapshot['status'], 'available')
        self.assertEqual(len(snapshot['vehicles']), 45)
        vehicle = snapshot['vehicles'][0]
        existing = self.service._indexes['timeline'].groups['vehicles']['1'].totals.snapshot()
        self.assertEqual(vehicle['battles'], 2)
        self.assertEqual(vehicle['wn8'], existing['wn8'])
        self.assertEqual(vehicle['creditsNet'], existing['credits_net']['sum'])
        self.assertEqual(vehicle['battlesToday'], 1)
        self.assertEqual(vehicle['battlesByDay'], {yesterday.isoformat(): 1, self.today.isoformat(): 1})
        self.assertIsNone(vehicle['ownedSince'])
        self.assertEqual(sequence, self.service.store.sequence)
        self.assertNotIn('account_key', snapshot)

    def test_day_window_is_inclusive_and_unknown_vehicles_are_absent(self):
        first = self.today - datetime.timedelta(days=365)
        self.add('inside', first)
        self.add('outside', first - datetime.timedelta(days=1))
        snapshot = read_snapshot(self.runtime, [1, 2])
        self.assertEqual(snapshot['dayRange'], {
            'from': first.isoformat(), 'through': self.today.isoformat(), 'basis': 'gameLocalTime'})
        self.assertEqual(len(snapshot['vehicles']), 1)
        row = snapshot['vehicles'][0]
        self.assertEqual(row['battles'], 2)
        self.assertEqual(row['battlesByDay'], {first.isoformat(): 1})
        self.assertEqual(row['battlesToday'], 0)

    def test_missing_result_is_not_presented_as_confirmed_daily_count(self):
        self.service.begin_battle('pending', started_at=self.clock(), mode='random', vehicle_id=2)
        self.add('known')
        snapshot = read_snapshot(self.runtime, [1, 2])
        self.assertEqual([row['vehicleId'] for row in snapshot['vehicles']], [1])
        self.assertEqual(snapshot['vehicles'][0]['battlesToday'], 1)

    def test_current_account_replay_battle_and_loading_gates(self):
        self.add('known')
        self.api.account_dbid = lambda: 8
        self.assertEqual(read_snapshot(self.runtime, [1])['status'], 'unavailable')
        self.api.account_dbid = lambda: 7
        self.api.is_replay = lambda: True
        self.assertEqual(read_snapshot(self.runtime, [1])['vehicles'], [])
        self.api.is_replay = lambda: False
        self.api.in_battle = lambda: True
        self.assertEqual(read_snapshot(self.runtime, [1])['status'], 'unavailable')
        self.api.in_battle = lambda: False
        self.service.loading = True
        self.assertEqual(read_snapshot(self.runtime, [1])['status'], 'pending')
        self.service.loading = False
        self.service.ready = False
        self.assertEqual(read_snapshot(self.runtime, [1])['status'], 'unavailable')

    def test_cached_results_are_copies_and_refresh_after_ledger_or_day_change(self):
        self.add('first')
        first = read_snapshot(self.runtime, [1])
        first['vehicles'][0]['battles'] = 999
        self.assertEqual(read_snapshot(self.runtime, [1])['vehicles'][0]['battles'], 1)
        self.add('second')
        self.assertEqual(read_snapshot(self.runtime, [1])['vehicles'][0]['battles'], 2)
        self.clock.value += 86400
        self.assertEqual(read_snapshot(self.runtime, [1])['vehicles'][0]['battlesToday'], 0)

    def test_public_runtime_api_does_not_start_stopped_runtime(self):
        original = runtime_module._runtime
        try:
            runtime_module._runtime = None
            self.assertEqual(runtime_module.read_hangar_stats([1])['status'], 'unavailable')
        finally:
            runtime_module._runtime = original
        for ids in ([True], [0], [-1], [2 ** 32], ['1'], list(range(1, 1202))):
            with self.assertRaises(ValueError):
                read_snapshot(self.runtime, ids)


if __name__ == '__main__':
    unittest.main()
