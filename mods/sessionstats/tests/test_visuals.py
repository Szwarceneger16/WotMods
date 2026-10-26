# -*- coding: utf-8 -*-
"""Native resource-adapter contracts, not a claim of a live WoT render test."""
from __future__ import unicode_literals

import copy
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src'))
from grz_session_stats import visuals
from grz_session_stats.visuals import NativeVisualResolver, enrich_snapshot, verified_image_url


VEHICLE_PATH = 'gui/maps/icons/vehicle/uk-GB31_Conqueror_Gun.png'
SMALL_PATH = 'gui/maps/icons/vehicle/small/uk-GB31_Conqueror_Gun.png'
MAP_PATH = 'gui/maps/icons/map/small/01_karelia.png'
MAP_DEFAULT_PATH = 'gui/maps/icons/map/01_karelia.png'
# Descriptor numbers below are test IDs. Only the resource filenames are from
# the inspected client asset catalogue; this fixture is not a server result.
VEHICLE_ID = 257
ARENA_ID = '1000000000000000001'


class Obj(object):
    def __init__(self, **fields):
        self.__dict__.update(fields)


class Node(object):
    def __init__(self, resource_id=0, exists=True):
        self.resource_id = resource_id
        self.available = exists

    def exists(self):
        return self.available

    def __call__(self):
        return self.resource_id


class Branch(object):
    def __init__(self, nodes=None):
        self.nodes = nodes or {}
        self.calls = []

    def dyn(self, name):
        self.calls.append(('dyn', name))
        return self.nodes.get(name, Node(exists=False))

    def num(self, name):
        self.calls.append(('num', name))
        return self.nodes.get(name, Node(exists=False))


class ResolverFixture(object):
    def __init__(self):
        self.vehicles = {VEHICLE_ID: Obj(compactDescr=VEHICLE_ID, name='uk:GB31_Conqueror_Gun')}
        self.types_read = []
        self.paths_checked = []
        self.vehicle_branch = Branch({'uk_GB31_Conqueror_Gun': Node(11)})
        self.vehicle_branch.small = Branch({'uk_GB31_Conqueror_Gun': Node(12)})
        self.map_small_branch = Branch({'01_karelia': Node(22)})
        self.map_branch = Branch({'01_karelia': Node(21), 'small': self.map_small_branch})
        self.resources = Obj(images=Obj(gui=Obj(maps=Obj(icons=Obj(
            vehicle=self.vehicle_branch, map=self.map_branch)))))
        self.paths = {11: '../maps/icons/vehicle/uk-GB31_Conqueror_Gun.png',
                      12: 'img://' + SMALL_PATH, 21: 'img://' + MAP_DEFAULT_PATH,
                      22: 'img://' + MAP_PATH}
        self.files = {VEHICLE_PATH, SMALL_PATH, MAP_PATH, MAP_DEFAULT_PATH}
        self.resolver = NativeVisualResolver(
            resources=self.resources, vehicle_getter=self.vehicle_type,
            image_getter=lambda identifier: self.paths[identifier],
            icon_name_getter=lambda name: name.replace(':', '_').replace('-', '_'),
            absolute_url_getter=lambda path: path.replace('../', 'img://gui/'),
            file_exists=self.exists)

    def vehicle_type(self, compact):
        self.types_read.append(compact)
        return self.vehicles[compact]

    def exists(self, path):
        self.paths_checked.append(path)
        return path in self.files


def snapshot():
    scope = {'summary': {'battles': 1, 'wn8': 1438, 'currencies': {'bonds': {'net': 3}}},
             'vehicles': [{'id': str(VEHICLE_ID), 'name': 'Conqueror GC', 'stats': {'battles': 1}}],
             'maps': [{'id': '01_karelia', 'name': 'Karelia', 'stats': {'battles': 1}}],
             'battles': [{'id': ARENA_ID, 'name': 'Conqueror GC', 'map': 'Karelia', 'stats': {'battles': 1}}]}
    return {'version': 'test', 'warnings': [], 'scopes': {'launch': copy.deepcopy(scope), 'manual': copy.deepcopy(scope)}}


def ledger():
    return {ARENA_ID: {'arena_id': ARENA_ID, 'vehicle_id': VEHICLE_ID,
                       'map_id': '01_karelia', 'map_name': 'Karelia', 'xp_received': 4500}}


class LocalURLTests(unittest.TestCase):
    def test_exact_native_png_is_retained(self):
        result = verified_image_url('img://' + VEHICLE_PATH, 'vehicle', lambda path: path == VEHICLE_PATH)
        self.assertEqual(result, 'img://' + VEHICLE_PATH)

    def test_png_logical_name_can_use_confirmed_dds_backing(self):
        dds_path = VEHICLE_PATH[:-4] + '.dds'
        calls = []
        def exists(path):
            calls.append(path)
            return path == dds_path
        self.assertEqual(verified_image_url('img://' + VEHICLE_PATH, 'vehicle', exists), 'img://' + dds_path)
        self.assertEqual(calls, [VEHICLE_PATH, dds_path])
        self.assertEqual(verified_image_url('img://' + dds_path, 'vehicle', exists), 'img://' + dds_path)

    def test_missing_both_backings_does_not_invent_an_image(self):
        self.assertIsNone(verified_image_url('img://' + MAP_PATH, 'map', lambda path: False))

    def test_only_confirmed_family_and_native_scheme_are_accepted(self):
        invalid = ['https://example.test/picture.png', 'data:image/png;base64,AA==',
                   'coui://' + VEHICLE_PATH, 'img://' + MAP_PATH,
                   'img://gui/maps/icons/vehicle/../map/01_karelia.png',
                   'img://gui/maps/icons/vehicle//x.png',
                   'img://gui/maps/icons/vehicle/%2e%2e/x.png',
                   'img://' + VEHICLE_PATH + '?x=1', 'img://' + VEHICLE_PATH + '#x',
                   'img://' + VEHICLE_PATH + '\n', 'img://gui\\maps\\icons\\vehicle\\x.png']
        checked = []
        for url in invalid:
            self.assertIsNone(verified_image_url(url, 'vehicle', lambda path: checked.append(path) or True))
        self.assertEqual(checked, [])

    def test_file_checker_error_is_optional(self):
        def unavailable(path):
            raise RuntimeError('resource system unavailable')
        self.assertIsNone(verified_image_url('img://' + MAP_PATH, 'map', unavailable))


class NativeResolverTests(unittest.TestCase):
    def setUp(self):
        self.fixture = ResolverFixture()

    def test_outcomes_use_only_their_original_wg_art_and_cache_successes(self):
        for outcome, name in (('win', 'Victory'), ('loss', 'Defeat'), ('draw', 'Draw')):
            path = 'gui/maps/icons/library/BgBattleResultIcon' + name + '-1.png'
            self.fixture.files.add(path)
            self.assertEqual(self.fixture.resolver.outcome_src(outcome), 'img://' + path)
            count = len(self.fixture.paths_checked)
            self.assertEqual(self.fixture.resolver.outcome_src(outcome), 'img://' + path)
            self.assertEqual(len(self.fixture.paths_checked), count)
        for unknown in (None, 'unknown', 'Victory', '../win', {}, 1):
            self.assertIsNone(self.fixture.resolver.outcome_src(unknown))

    def test_missing_outcome_retries_and_accepts_only_confirmed_dds_backing(self):
        self.assertIsNone(self.fixture.resolver.outcome_src('win'))
        path = 'gui/maps/icons/library/BgBattleResultIconVictory-1.dds'
        self.fixture.files.add(path)
        self.assertEqual(self.fixture.resolver.outcome_src('win'), 'img://' + path)
        checked = []
        for suffix in ('Other.png', '../map/01_karelia.png', 'BgBattleResultIconVictory-1.png?x'):
            self.assertIsNone(verified_image_url('img://gui/maps/icons/library/' + suffix,
                                                 'outcome', lambda path: checked.append(path) or True))
        self.assertEqual(checked, [])

    def test_outcome_art_is_snapshot_only_and_missing_art_preserves_result_and_totals(self):
        payload, records = snapshot(), ledger()
        payload['scopes']['launch']['battles'][0]['outcome'] = 'win'
        original, original_records = copy.deepcopy(payload), copy.deepcopy(records)
        path = 'gui/maps/icons/library/BgBattleResultIconVictory-1.png'
        enriched = enrich_snapshot(copy.deepcopy(payload), records, self.fixture.resolver)
        row = enriched['scopes']['launch']['battles'][0]
        self.assertNotIn('outcome_visual', row)
        self.assertEqual(row['outcome'], 'win')
        self.fixture.files.add(path)
        enriched = enrich_snapshot(copy.deepcopy(payload), records, self.fixture.resolver)
        row = enriched['scopes']['launch']['battles'][0]
        self.assertEqual(row['outcome_visual']['src'], 'img://' + path)
        self.assertEqual(enriched['scopes']['launch']['summary'], original['scopes']['launch']['summary'])
        self.assertEqual(payload, original)
        self.assertEqual(records, original_records)

    def test_vehicle_uses_type_compact_and_registered_resource_name(self):
        fixture = self.fixture
        self.assertEqual(fixture.resolver.vehicle_src(str(VEHICLE_ID)), 'img://' + VEHICLE_PATH)
        self.assertEqual(fixture.types_read, [VEHICLE_ID])
        self.assertEqual(fixture.vehicle_branch.calls, [('dyn', 'uk_GB31_Conqueror_Gun')])
        self.assertEqual(fixture.vehicle_branch.small.calls, [])
        self.assertEqual(fixture.paths_checked, [VEHICLE_PATH])

    def test_vehicle_fallback_is_smaller_icon_of_the_same_vehicle(self):
        fixture = self.fixture
        fixture.files.remove(VEHICLE_PATH)
        self.assertEqual(fixture.resolver.vehicle_src(VEHICLE_ID), 'img://' + SMALL_PATH)
        self.assertEqual(fixture.vehicle_branch.small.calls, [('dyn', 'uk_GB31_Conqueror_Gun')])

    def test_map_uses_geometry_not_a_translated_label(self):
        fixture = self.fixture
        self.assertEqual(fixture.resolver.map_src('01_karelia'), 'img://' + MAP_PATH)
        self.assertEqual(fixture.map_branch.calls, [('dyn', 'small')])
        self.assertEqual(fixture.map_small_branch.calls, [('num', '01_karelia')])
        self.assertIsNone(fixture.resolver.map_src('arena:42'))
        self.assertIsNone(fixture.resolver.map_src('../01_karelia'))
        self.assertIsNone(fixture.resolver.map_src('01_karelia\n'))

    def test_missing_small_map_uses_only_confirmed_default_of_same_geometry(self):
        fixture = self.fixture
        fixture.files.remove(MAP_PATH)
        self.assertEqual(fixture.resolver.map_src('01_karelia'), 'img://' + MAP_DEFAULT_PATH)
        self.assertEqual(fixture.map_branch.calls, [('dyn', 'small'), ('num', '01_karelia')])
        self.assertEqual(fixture.paths_checked, [MAP_PATH, MAP_PATH[:-4] + '.dds', MAP_DEFAULT_PATH])

    def test_missing_small_branch_can_use_registered_default_map(self):
        fixture = self.fixture
        del fixture.map_branch.nodes['small']
        self.assertEqual(fixture.resolver.map_src('01_karelia'), 'img://' + MAP_DEFAULT_PATH)

    def test_bad_compact_cannot_alias_another_vehicle(self):
        fixture = self.fixture
        fixture.vehicles[513] = fixture.vehicles[VEHICLE_ID]
        self.assertIsNone(fixture.resolver.vehicle_src(513))
        for value in (True, 0, -1, 257.0, '257x', '257\n', None):
            self.assertIsNone(fixture.resolver.vehicle_src(value))
        self.assertEqual(fixture.vehicle_branch.calls, [])

    def test_missing_nodes_ids_or_path_never_fall_back_to_wrong_picture(self):
        fixture = self.fixture
        fixture.vehicle_branch.nodes.clear()
        fixture.vehicle_branch.small.nodes.clear()
        self.assertIsNone(fixture.resolver.vehicle_src(VEHICLE_ID))
        fixture.map_small_branch.nodes.clear()
        fixture.map_branch.nodes['01_karelia'] = Node(-1)
        self.assertIsNone(fixture.resolver.map_src('01_karelia'))
        self.assertIsNone(fixture.resolver.vehicle_src(99999))
        self.assertEqual(fixture.paths_checked, [])

    def test_wrong_resource_family_is_rejected(self):
        fixture = self.fixture
        fixture.paths[11] = 'img://' + MAP_PATH
        fixture.paths[12] = 'img://' + MAP_PATH
        self.assertIsNone(fixture.resolver.vehicle_src(VEHICLE_ID))

    def test_positive_cache_avoids_repeated_resource_work(self):
        fixture = self.fixture
        for unused in range(5):
            fixture.resolver.vehicle_src(VEHICLE_ID)
            fixture.resolver.map_src('01_karelia')
        self.assertEqual(fixture.types_read, [VEHICLE_ID])
        self.assertEqual(fixture.paths_checked, [VEHICLE_PATH, MAP_PATH])

    def test_unavailable_image_can_recover_later_in_the_same_process(self):
        fixture = self.fixture
        fixture.files.clear()
        self.assertIsNone(fixture.resolver.map_src('01_karelia'))
        fixture.files.add(MAP_PATH)
        self.assertEqual(fixture.resolver.map_src('01_karelia'), 'img://' + MAP_PATH)


class SnapshotTests(unittest.TestCase):
    def setUp(self):
        self.fixture = ResolverFixture()

    def test_existing_rows_and_old_battle_records_are_enriched_without_persistence_changes(self):
        payload = snapshot()
        before = copy.deepcopy(payload)
        records = ledger()
        records_before = copy.deepcopy(records)
        self.assertIs(enrich_snapshot(payload, records, self.fixture.resolver), payload)
        for scope in payload['scopes'].values():
            self.assertEqual(scope['vehicles'][0]['visual'],
                             {'kind': 'vehicle', 'src': 'img://' + VEHICLE_PATH, 'alt': 'Conqueror GC'})
            self.assertEqual(scope['maps'][0]['visual'],
                             {'kind': 'map', 'src': 'img://' + MAP_PATH, 'alt': 'Karelia'})
            self.assertEqual(scope['battles'][0]['visual']['src'], 'img://' + VEHICLE_PATH)
            for group in ('vehicles', 'maps', 'battles'):
                scope[group][0].pop('visual')
        self.assertEqual(payload, before)
        self.assertEqual(records, records_before)

    def test_no_guess_from_a_battle_or_vehicle_display_name(self):
        payload = snapshot()
        payload['scopes']['launch']['vehicles'][0]['id'] = '__unknown__'
        enrich_snapshot(payload, {}, self.fixture.resolver)
        self.assertNotIn('visual', payload['scopes']['launch']['vehicles'][0])
        self.assertNotIn('visual', payload['scopes']['launch']['battles'][0])
        self.assertEqual(payload['scopes']['launch']['vehicles'][0]['name'], 'Conqueror GC')

    def test_missing_battle_vehicle_can_use_its_confirmed_map(self):
        payload = snapshot()
        records = ledger()
        records[ARENA_ID]['vehicle_id'] = None
        enrich_snapshot(payload, records, self.fixture.resolver)
        self.assertEqual(payload['scopes']['launch']['battles'][0]['visual'],
                         {'kind': 'map', 'src': 'img://' + MAP_PATH, 'alt': 'Karelia'})

    def test_one_bad_row_does_not_break_neighboring_rows_or_leave_stale_visuals(self):
        payload = snapshot()
        bad = {'id': 'missing', 'name': 'Unknown', 'stats': {'battles': 1},
               'visual': {'kind': 'vehicle', 'src': 'old'}}
        payload['scopes']['launch']['vehicles'].insert(0, bad)
        enrich_snapshot(payload, ledger(), self.fixture.resolver)
        self.assertNotIn('visual', bad)
        self.assertIn('visual', payload['scopes']['launch']['vehicles'][1])

    def test_missing_native_modules_do_not_break_snapshot(self):
        original = visuals._get_native_resolver
        visuals._get_native_resolver = lambda: None
        try:
            payload = snapshot()
            before = copy.deepcopy(payload)
            self.assertEqual(enrich_snapshot(payload, ledger()), before)
        finally:
            visuals._get_native_resolver = original

    def test_runtime_snapshot_enriches_using_existing_ledger_without_mutating_service(self):
        from grz_session_stats.runtime import Runtime
        original = visuals._get_native_resolver
        visuals._get_native_resolver = lambda: self.fixture.resolver
        try:
            raw = snapshot()
            saved = ledger()
            service = Obj(snapshot=lambda: copy.deepcopy(raw), _state={'battles': saved}, last_error=None)
            runtime = Runtime()
            runtime.active_service = service
            result = runtime.snapshot()
            self.assertEqual(result['scopes']['launch']['battles'][0]['visual']['src'], 'img://' + VEHICLE_PATH)
            self.assertNotIn('visual', raw['scopes']['launch']['battles'][0])
            self.assertEqual(saved, ledger())
        finally:
            visuals._get_native_resolver = original


if __name__ == '__main__':
    unittest.main()
