# -*- coding: utf-8 -*-
"""Recognizable durable beginnings, even when no result ever arrives."""
from __future__ import unicode_literals

import copy
import json
import unittest

import test_runtime as fixtures
from grz_session_stats import runtime
from grz_session_stats.core import StatsService
from test_normalize import ARENA_ID, START, raw_result


METADATA = {'vehicle_name': 'Entry vehicle', 'vehicle_tier': 8,
            'vehicle_type': 'mediumTank', 'map_name': 'Entry map'}


class NativeEntryContextTests(unittest.TestCase):
    def setUp(self):
        self.vehicle_type = fixtures.Obj(compactDescr=1, shortUserString='Entry vehicle',
                                         userString='Full name', level=8, classTag='mediumTank')
        self.vehicle = {'vehicleType': fixtures.Obj(type=self.vehicle_type),
                        'name': 'PRIVATE_PLAYER_SENTINEL', 'accountDBID': 7}
        self.arena = fixtures.Obj(bonusType=1, vehicles={10: self.vehicle},
                                  arenaType=fixtures.Obj(geometryName='17_map', name='Entry map'))
        player = fixtures.Obj(arena=self.arena, arenaUniqueID=int(ARENA_ID), playerVehicleID=10)
        self.api = runtime.GameAPI.__new__(runtime.GameAPI)
        self.api.player = lambda: player
        self.api.account_dbid = lambda: 7
        self.api.random_bonus_type = 1

    def test_native_descriptor_captures_only_own_vehicle_display_metadata(self):
        context = self.api.battle_context()
        for key, value in METADATA.items():
            self.assertEqual(context[key], value)
        self.assertEqual(context['started_at'], START)
        self.assertEqual(context['vehicle_id'], 1)
        self.assertEqual(context['map_id'], '17_map')
        self.assertNotIn('PRIVATE_PLAYER_SENTINEL', json.dumps(context))
        self.assertNotIn('vehicles', context)

    def test_loading_arena_can_later_supply_vehicle_metadata(self):
        self.vehicle.pop('vehicleType')
        context = self.api.battle_context()
        self.assertIsNone(context['vehicle_id'])
        self.assertIsNone(context['vehicle_name'])
        self.assertEqual(context['map_name'], METADATA['map_name'])
        self.vehicle['vehicleType'] = fixtures.Obj(type=self.vehicle_type)
        self.assertEqual(self.api.battle_context()['vehicle_name'], METADATA['vehicle_name'])

    def test_optional_display_failure_keeps_the_beginning_and_map(self):
        class NotReadyType(object):
            compactDescr = 1

            @property
            def shortUserString(self):
                raise RuntimeError('PRIVATE_EXCEPTION_SENTINEL')

        self.vehicle['vehicleType'] = fixtures.Obj(type=NotReadyType())
        context = self.api.battle_context()
        self.assertEqual(context['arena_id'], ARENA_ID)
        self.assertEqual(context['vehicle_id'], 1)
        self.assertEqual(context['map_name'], METADATA['map_name'])
        self.assertNotIn('PRIVATE_EXCEPTION_SENTINEL', json.dumps(context))

    def test_optional_map_name_failure_keeps_beginning_vehicle_and_map_identity(self):
        class NotReadyMap(object):
            geometryName = '17_map'

            @property
            def name(self):
                raise RuntimeError('PRIVATE_EXCEPTION_SENTINEL')

        self.arena.arenaType = NotReadyMap()
        context = self.api.battle_context()
        self.assertEqual(context['arena_id'], ARENA_ID)
        self.assertEqual(context['vehicle_id'], 1)
        self.assertEqual(context['map_id'], '17_map')
        self.assertIsNone(context['map_name'])

    def test_optional_vehicle_identity_failure_keeps_beginning_display_and_map(self):
        class NotReadyType(object):
            shortUserString, level, classTag = 'Entry vehicle', 8, 'mediumTank'

            @property
            def compactDescr(self):
                raise RuntimeError('PRIVATE_EXCEPTION_SENTINEL')

        self.vehicle['vehicleType'] = fixtures.Obj(type=NotReadyType())
        context = self.api.battle_context()
        self.assertEqual(context['arena_id'], ARENA_ID)
        self.assertIsNone(context['vehicle_id'])
        for key, value in METADATA.items():
            self.assertEqual(context[key], value)

    def test_unavailable_roster_does_not_hide_verified_random_battle(self):
        self.arena.vehicles = None
        context = self.api.battle_context()
        self.assertEqual(context['arena_id'], ARENA_ID)
        self.assertEqual(context['started_at'], START)
        self.assertEqual(context['mode'], 'random')
        self.assertIsNone(context['vehicle_id'])
        self.assertEqual(context['map_name'], METADATA['map_name'])
        self.arena.bonusType = 2
        self.assertIsNone(self.api.battle_context())


class DurableEntryMetadataTests(unittest.TestCase):
    setUp = fixtures.RuntimeTests.__dict__['setUp']
    tearDown = fixtures.RuntimeTests.__dict__['tearDown']
    no_footer = fixtures.RuntimeTests.__dict__['no_footer']
    begin = fixtures.RuntimeTests.__dict__['begin']

    def enter_with_metadata(self):
        self.begin()
        self.api.context.update(METADATA)
        self.api.events.onAvatarReady()

    def test_entry_is_on_disk_before_exit_and_recognizable_after_restart(self):
        self.enter_with_metadata()
        service = self.mod.active_service
        persisted = service.store.load()['battles'][ARENA_ID]
        for key, value in METADATA.items():
            self.assertEqual(persisted[key], value)
        self.assertEqual(persisted['started_at'], START)
        self.assertFalse(persisted['_result_seen'])
        self.mod.stop()
        self.clock.value += 86400
        restored = StatsService(self.directory, 'EU:7', 'new-client', fixtures.EXPECTED, now=self.clock)
        scope = restored.snapshot()['scopes']['manual']
        row = scope['battles'][0]
        self.assertEqual((row['name'], row['map'], row['tier'], row['started_at']),
                         (METADATA['vehicle_name'], METADATA['map_name'], 8, START))
        self.assertEqual(scope['vehicles'][0]['type'], 'mediumTank')
        self.assertEqual(scope['maps'][0]['name'], METADATA['map_name'])
        self.assertIsNone(row['outcome'])
        self.assertIsNone(row['stats']['xp_base']['avg'])
        self.assertIsNone(row['stats']['currencies']['credits']['net'])
        stats = scope['summary']
        self.assertEqual((stats['battles'], stats['observed_battles'], stats['missing_results']), (0, 1, 1))

    def test_repeated_entry_only_enriches_missing_fields_without_duplicate_writes(self):
        self.begin()
        service = self.mod.active_service
        self.api.context.update(METADATA)
        self.api.events.onAvatarReady()
        enriched = copy.deepcopy(service._state)
        for unused in range(3):
            self.clock.value += 5
            self.api.events.onAvatarReady()
        self.assertEqual(service._state, enriched)
        self.api.context.update(dict((key, None) for key in METADATA))
        self.api.events.onAvatarReady()
        self.assertEqual(service._state, enriched)
        self.assertEqual(service.result_context(ARENA_ID)['map_name'], METADATA['map_name'])

    def test_context_allowlist_does_not_persist_roster_tokens_or_player_names(self):
        self.enter_with_metadata()
        self.api.context.update({'player_name': 'PRIVATE_PLAYER_SENTINEL',
                                 'vehicles': {'roster': 'PRIVATE_ROSTER_SENTINEL'},
                                 'token': 'PRIVATE_TOKEN_SENTINEL', 'account_dbid': 999999997})
        self.api.events.onAvatarReady()
        serialized = json.dumps(self.mod.active_service.store.load())
        for private in ('PRIVATE_PLAYER_SENTINEL', 'PRIVATE_ROSTER_SENTINEL',
                        'PRIVATE_TOKEN_SENTINEL', '999999997'):
            self.assertNotIn(private, serialized)

    def test_late_result_without_metadata_helpers_preserves_entry_labels(self):
        self.enter_with_metadata()
        self.mod.stop()
        self.clock.value += 86400
        self.api.battle = False
        def unavailable(unused):
            raise RuntimeError('optional helper not available')
        self.api.vehicle_info = unavailable
        self.api.map_info = unavailable
        self.mod.start()
        self.api.events.onBattleResultsReceived(True, raw_result())
        scope = self.mod.active_service.snapshot()['scopes']['manual']
        row = scope['battles'][0]
        self.assertEqual((row['name'], row['map']), (METADATA['vehicle_name'], METADATA['map_name']))
        self.assertEqual((scope['summary']['battles'], scope['summary']['observed_battles']), (1, 1))

    def test_reentering_after_result_keeps_confirmed_stats_and_membership(self):
        self.enter_with_metadata()
        self.api.events.onBattleResultsReceived(True, raw_result())
        service = self.mod.active_service
        before = copy.deepcopy(service._state['battles'][ARENA_ID])
        self.api.context.update(dict((key, None) for key in METADATA))
        self.api.events.onAvatarReady()
        self.assertEqual(service._state['battles'][ARENA_ID], before)


if __name__ == '__main__':
    unittest.main()
