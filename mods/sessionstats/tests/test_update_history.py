# -*- coding: utf-8 -*-
"""Keep existing session data and identities when optional client metadata changes."""
from __future__ import unicode_literals

import copy
import logging
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src'))
from grz_session_stats import runtime
from grz_session_stats.core import StatsService
from grz_session_stats.normalize import normalize_result
from test_normalize import raw_result, ARENA_ID, START
from test_runtime import Clock, FakeAPI, FakeWindow, EXPECTED


class MissingMetadataAPI(FakeAPI):
    def vehicle_info(self, compact):
        raise AttributeError('Client vehicle metadata helper changed')

    def map_info(self, arena_type_id):
        raise AttributeError('Client map metadata helper changed')


class UpdateHistoryTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.mkdtemp(prefix='grz-update-history-')
        self.clock = Clock(START - 10)
        self.log_level = logging.root.manager.disable
        logging.disable(logging.CRITICAL)
        self.previous = StatsService(self.directory, 'EU:7', 'before-update', EXPECTED, now=self.clock)
        self.clock.value = START + 450
        api = FakeAPI()
        record = normalize_result(raw_result(), {'account_dbid': 7},
                                  vehicle_resolver=api.vehicle_info, map_resolver=api.map_info)
        self.assertTrue(self.previous.record_result(record))
        self.mod = None

    def tearDown(self):
        if self.mod is not None:
            self.mod.stop()
        logging.disable(self.log_level)
        shutil.rmtree(self.directory)

    def restart(self, api):
        self.clock.value = START + 900
        self.mod = runtime.Runtime(deferred_loading=False, api=api, data_dir=self.directory,
                                   expected_table=EXPECTED, now=self.clock,
                                   window=FakeWindow(), footer_installer=lambda callback: None)
        self.mod.start()
        self.assertEqual(self.mod.contexts, {})
        return self.mod.active_service

    def test_context_lookup_is_read_only_and_contains_no_stats_or_membership(self):
        before = copy.deepcopy(self.previous._state)
        sequence = self.previous.store.sequence
        context = self.previous.result_context(ARENA_ID)
        self.assertEqual(context['map_id'], '17_map')
        self.assertEqual(context['vehicle_name'], 'Test vehicle')
        self.assertNotIn('currencies', context)
        self.assertNotIn('_manual_id', context)
        context['map_id'] = 'changed-locally'
        self.assertEqual(self.previous._state, before)
        self.assertEqual(self.previous.store.sequence, sequence)
        self.assertEqual(self.previous.result_context('unknown-arena'), {})

    def test_metadata_failure_after_restart_keeps_names_groups_and_session_membership(self):
        before = self.previous.snapshot()['scopes']['manual']
        service = self.restart(MissingMetadataAPI())
        raw = raw_result()
        raw['personal'][1]['xp'] = 2600
        self.assertTrue(self.mod._process(raw, 'EU:7', service))
        snapshot = service.snapshot()
        manual = snapshot['scopes']['manual']
        self.assertEqual(snapshot['scopes']['launch']['summary']['battles'], 0)
        self.assertEqual(manual['started_at'], before['started_at'])
        self.assertEqual(manual['summary']['battles'], 1)
        self.assertEqual(manual['summary']['xp_received']['sum'], 2600)
        self.assertEqual(manual['vehicles'][0]['id'], before['vehicles'][0]['id'])
        self.assertEqual(manual['vehicles'][0]['name'], 'Test vehicle')
        self.assertEqual(manual['maps'][0]['id'], '17_map')
        self.assertEqual(manual['maps'][0]['name'], 'Test map')
        self.assertEqual(manual['summary']['currencies'], before['summary']['currencies'])
        self.assertTrue(any('Map name' in item for item in snapshot['warnings']))

    def test_current_verified_metadata_can_still_correct_an_older_label(self):
        api = FakeAPI()
        api.map_info = lambda arena_type_id: {'id': '17_map', 'name': 'Aktualna nazwa mapy'}
        api.vehicle_info = lambda compact: {'name': 'Aktualna nazwa pojazdu', 'tier': 8, 'type': 'mediumTank'}
        service = self.restart(api)
        self.assertTrue(self.mod._process(raw_result(), 'EU:7', service))
        manual = service.snapshot()['scopes']['manual']
        self.assertEqual(manual['vehicles'][0]['name'], 'Aktualna nazwa pojazdu')
        self.assertEqual(manual['maps'][0]['name'], 'Aktualna nazwa mapy')
        self.assertEqual(manual['summary']['battles'], 1)

    def test_changed_currency_container_keeps_performance_without_guessing_costs(self):
        raw = raw_result()
        # A named object is deliberately not reinterpreted as the known tuple.
        raw['personal'][1]['autoEquipCost'] = {'credits': 15000, 'gold': 5, 'crystal': 12}
        record = normalize_result(raw, {'account_dbid': 7})
        self.assertEqual(record['xp_base'], 650)
        self.assertEqual(record['damage'], 2100)
        self.assertEqual(record['currencies']['bonds']['income'], 40)
        for currency in ('credits', 'bonds', 'gold'):
            self.assertIsNone(record['currencies'][currency]['costs'])
            self.assertIsNone(record['currencies'][currency]['net'])
        self.assertFalse(record['complete'])


if __name__ == '__main__':
    unittest.main()
