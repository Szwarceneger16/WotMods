# -*- coding: utf-8 -*-
"""Selected UI language resolves stable map IDs without rewriting native saves."""
from __future__ import unicode_literals

import copy
import json
import os
import shutil
import sys
import tempfile
import types
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from grz_session_stats.map_names import MapNames, bundled_names, decode, LANGUAGES, MAX_BYTES
from grz_session_stats.localization import Localizer
from grz_session_stats.core import StatsService
from test_core import result, EXPECTED, Clock


class MapNameTests(unittest.TestCase):
    def test_native_names_cover_every_selected_language_and_keep_verified_spellings(self):
        names = bundled_names()
        self.assertEqual(len(names), 68)
        self.assertTrue(all(set(value) == set(LANGUAGES) for value in names.values()))
        self.assertEqual([names['59_asia_great_wall'][language] for language in LANGUAGES],
                         ["Empire's Border", 'Granica imperium', 'Граница империи', "Frontière de l'Empire",
                          'Chinesische Mauer', 'Frontera del Imperio', 'Кордон імперії'])
        self.assertEqual(names['120_graf_zeppelin']['en'], 'Nordskar')
        self.assertEqual(names['14_siegfried_line_nom']['en'], 'Westwall')

    def test_full_ids_and_only_unambiguous_stripped_aliases_are_resolved(self):
        names = MapNames('en')
        self.assertEqual(names.name('59_asia_great_wall', 'Saved'), "Empire's Border")
        self.assertEqual(names.name(b'asia_great_wall', 'Saved'), "Empire's Border")
        self.assertEqual(names.name('north_america', 'Ambiguous native name'), 'Ambiguous native name')
        self.assertEqual(names.name('44_north_america', 'Saved'), 'Live Oaks')
        self.assertEqual(names.name('45_north_america', 'Saved'), 'Highway')
        for identifier in (None, 59, '../59_asia_great_wall', 'future_map', b'\xff'):
            self.assertEqual(names.name(identifier, 'Original unknown map'), 'Original unknown map')

    def test_a_known_map_uses_verified_english_when_the_requested_translation_is_missing(self):
        names = MapNames('uk', {'59_asia_great_wall': {'en': "Empire's Border"}})
        self.assertEqual(names.name('59_asia_great_wall', 'Saved'), "Empire's Border")

    def test_missing_unknown_labels_stay_absent_but_known_ids_supply_a_name(self):
        listing = {'items': [{'id': 'unknown'}, {'id': 'known', 'map_id': '59_asia_great_wall'}]}
        payload = {'warnings': [], 'scopes': {'launch': {
            'maps': [{'id': 'unknown'}, {'id': '59_asia_great_wall'}],
            'battles': [{'id': 'unknown'}, {'id': 'known', 'map_id': '59_asia_great_wall'}],
            'vehicles': [{'id': 'synthetic', 'battle_list': copy.deepcopy(listing)}],
            'battle_history': {'kind': 'vehicles', 'id': 'synthetic', 'battle_list': copy.deepcopy(listing)}}}}
        shown = Localizer('en').snapshot(payload)['scopes']['launch']
        self.assertEqual(shown['maps'][0], {'id': 'unknown'})
        self.assertEqual(shown['maps'][1], {'id': '59_asia_great_wall', 'name': "Empire's Border"})
        for rows in (shown['battles'], shown['vehicles'][0]['battle_list']['items'],
                     shown['battle_history']['battle_list']['items']):
            self.assertEqual(rows[0], {'id': 'unknown'})
            self.assertEqual(rows[1], {'id': 'known', 'map_id': '59_asia_great_wall', 'map': "Empire's Border"})

    def test_native_resource_is_used_without_a_source_checkout(self):
        raw = json.dumps({'schema_version': 1, 'maps': {'59_asia_great_wall': {'en': 'Native resource fixture'}}}).encode('utf-8')
        module = types.ModuleType(str('ResMgr'))
        calls = []
        module.openSection = lambda path: calls.append(path) or type(str('Section'), (), {'asBinary': raw})()
        previous = sys.modules.get('ResMgr')
        sys.modules['ResMgr'] = module
        try:
            self.assertEqual(bundled_names()['59_asia_great_wall']['en'], 'Native resource fixture')
            self.assertEqual(calls, ['grz_session_stats/map_names.json'])
        finally:
            if previous is None:
                del sys.modules['ResMgr']
            else:
                sys.modules['ResMgr'] = previous

    def test_malformed_oversized_and_non_name_entries_cannot_become_labels(self):
        for raw in (b'[]', b'{', b'{"schema_version":true,"maps":{}}', b' ' * (MAX_BYTES + 1)):
            self.assertRaises((ValueError, TypeError), decode, raw)
        self.assertEqual(decode(json.dumps({'schema_version': 1, 'maps': {
            '../map': {'en': 'Unsafe ID'}, '59_asia_great_wall': {'en': '<b>Unsafe name</b>'},
            '07_lakeville': {'en': 'Lakeville', 'pl': 'Line\nbreak'}}})),
            {'07_lakeville': {'en': 'Lakeville'}})

    def test_projection_and_every_history_keep_map_identity_while_language_changes(self):
        directory = tempfile.mkdtemp(prefix='synthetic-map-language-')
        try:
            service = StatsService(directory, 'EU:synthetic', 'launch', EXPECTED, Clock())
            record = result(map_id='59_asia_great_wall', map_name='Granica imperium')
            service.begin_battle('1', 110, 1, record['map_id'], 'random')
            service.record_result(record)
            first = service.snapshot()['scopes']['launch']
            service.set_map_battles('launch', record['map_id'], 0, first['period_id'])
            service.set_vehicle_battles('launch', '1', 0, first['period_id'])
            saved = copy.deepcopy(service._state)
            snapshot = service.snapshot()
            scope = snapshot['scopes']['launch']
            self.assertEqual(scope['battles'][0]['map_id'], record['map_id'])
            for group in ('maps', 'vehicles'):
                self.assertEqual(scope[group][0]['battle_list']['items'][0]['map_id'], record['map_id'])
            scope['maps'][0]['visual'] = {'kind': 'map', 'alt': 'Granica imperium'}
            scope['battles'][0]['map_visual'] = {'kind': 'map', 'alt': 'Granica imperium'}
            scope['battle_history'] = {'kind': 'vehicles', 'id': '1', 'battle_list': copy.deepcopy(scope['vehicles'][0]['battle_list'])}
            names = bundled_names()['59_asia_great_wall']
            for language in ('pl', 'en', 'de', 'uk', 'en'):
                shown = Localizer(language).snapshot(copy.deepcopy(snapshot))['scopes']['launch']
                self.assertEqual(shown['maps'][0]['name'], names[language])
                self.assertEqual(shown['maps'][0]['visual']['alt'], names[language])
                self.assertEqual(shown['battles'][0]['map'], names[language])
                self.assertEqual(shown['battles'][0]['map_visual']['alt'], names[language])
                for listing in (shown['maps'][0]['battle_list'], shown['vehicles'][0]['battle_list'], shown['battle_history']['battle_list']):
                    self.assertEqual(listing['items'][0]['map'], names[language])
                    self.assertEqual(listing['items'][0]['map_id'], record['map_id'])
            self.assertEqual(service._state, saved)
            self.assertEqual(service.project_scope([record], 'Fixture', 0)['battles'][0]['map_id'], record['map_id'])
        finally:
            shutil.rmtree(directory)


if __name__ == '__main__':
    unittest.main()
