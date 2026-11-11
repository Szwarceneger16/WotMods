# -*- coding: utf-8 -*-
"""Map hover choices use verified native assets and never alter saved records."""
from __future__ import unicode_literals

import copy
import unittest

from test_visuals import Branch, Node, ResolverFixture, MAP_PATH, MAP_DEFAULT_PATH, ledger, snapshot
from grz_session_stats import appearance, visuals


SCREEN_PATH = 'gui/maps/icons/map/screen/01_karelia.dds'


def add_screen(fixture):
    fixture.map_branch.nodes['screen'] = Branch({'01_karelia': Node(23)})
    fixture.paths[23] = 'img://' + SCREEN_PATH[:-4] + '.png'
    fixture.files.add(SCREEN_PATH)


class MapPreviewTests(unittest.TestCase):
    def test_landscape_preview_uses_registered_screen_dds_while_thumb_stays_small(self):
        fixture = ResolverFixture()
        add_screen(fixture)
        self.assertEqual(fixture.resolver.map_preview('01_karelia'),
                         {'src': 'img://' + SCREEN_PATH, 'mode': 'image'})
        self.assertEqual(fixture.resolver.map_src('01_karelia'), 'img://' + MAP_PATH)
        self.assertIn(SCREEN_PATH, fixture.paths_checked)

    def test_minimap_is_separate_from_landscape_cache_and_cannot_mutate_it(self):
        fixture = ResolverFixture()
        add_screen(fixture)
        fixture.resolver.map_preview('01_karelia', 'image')
        answer = fixture.resolver.map_preview('01_karelia', 'minimap')
        self.assertEqual(answer, {'src': 'img://' + MAP_DEFAULT_PATH, 'mode': 'minimap'})
        answer['src'] = 'changed by caller'
        count = len(fixture.paths_checked)
        self.assertEqual(fixture.resolver.map_preview('01_karelia', 'minimap')['src'], 'img://' + MAP_DEFAULT_PATH)
        self.assertEqual(fixture.resolver.map_preview('01_karelia', 'image')['src'], 'img://' + SCREEN_PATH)
        self.assertEqual(len(fixture.paths_checked), count)

    def test_missing_screen_falls_back_then_retries_when_registry_or_texture_is_ready(self):
        fixture = ResolverFixture()
        self.assertEqual(fixture.resolver.map_preview('01_karelia'),
                         {'src': 'img://' + MAP_PATH, 'mode': 'image'})
        add_screen(fixture)
        fixture.files.remove(SCREEN_PATH)
        self.assertEqual(fixture.resolver.map_preview('01_karelia')['src'], 'img://' + MAP_PATH)
        fixture.files.add(SCREEN_PATH)
        self.assertEqual(fixture.resolver.map_preview('01_karelia')['src'], 'img://' + SCREEN_PATH)

    def test_missing_minimap_uses_existing_thumbnail_and_recovers_later(self):
        fixture = ResolverFixture()
        fixture.files.remove(MAP_DEFAULT_PATH)
        self.assertEqual(fixture.resolver.map_preview('01_karelia', 'minimap'),
                         {'src': 'img://' + MAP_PATH, 'mode': 'image'})
        fixture.files.add(MAP_DEFAULT_PATH)
        self.assertEqual(fixture.resolver.map_preview('01_karelia', 'minimap')['mode'], 'minimap')

    def test_other_resource_family_and_remote_screen_urls_are_rejected(self):
        for path in ('img://gui/maps/icons/vehicle/test.png', 'https://example.test/test.png',
                     'img://gui/maps/icons/map/../vehicle/test.png',
                     'img://gui/maps/icons/map/screen/01_karelia.png?size=large'):
            fixture = ResolverFixture()
            add_screen(fixture)
            fixture.paths[23] = path
            self.assertEqual(fixture.resolver.map_preview('01_karelia')['src'], 'img://' + MAP_PATH)

    def test_invalid_geometry_or_mode_does_not_touch_registry(self):
        fixture = ResolverFixture()
        for geometry in (None, True, 1, '../01_karelia', '01_karelia\n', 'Karelia (translated)'):
            self.assertIsNone(fixture.resolver.map_preview(geometry))
        for mode in (None, True, {}, 'https://example.test/image.png', 'screen'):
            self.assertIsNone(fixture.resolver.map_preview('01_karelia', mode))
        self.assertEqual(fixture.map_branch.calls, [])
        self.assertEqual(fixture.paths_checked, [])

    def test_absent_map_preserves_missing_image_contract(self):
        fixture = ResolverFixture()
        fixture.files.clear()
        self.assertIsNone(fixture.resolver.map_preview('01_karelia'))

    def test_snapshot_attaches_large_preview_to_maps_and_battle_maps_without_persistence_changes(self):
        fixture = ResolverFixture()
        add_screen(fixture)
        payload, records = snapshot(), ledger()
        original, saved = copy.deepcopy(payload), copy.deepcopy(records)
        visuals.enrich_snapshot(payload, records, fixture.resolver)
        for scope in payload['scopes'].values():
            self.assertEqual(scope['maps'][0]['visual']['preview_src'], 'img://' + SCREEN_PATH)
            self.assertEqual(scope['maps'][0]['visual']['preview_mode'], 'image')
            self.assertEqual(scope['battles'][0]['map_visual'], scope['maps'][0]['visual'])
            scope['battles'][0].pop('map_visual')
            for grouping in ('vehicles', 'battles'):
                self.assertNotIn('preview_src', scope[grouping][0]['visual'])
            for grouping in ('vehicles', 'maps', 'battles'):
                scope[grouping][0].pop('visual')
        self.assertEqual(payload, original)
        self.assertEqual(records, saved)

    def test_battle_map_preview_obeys_the_same_minimap_configuration(self):
        fixture = ResolverFixture()
        add_screen(fixture)
        payload, records = snapshot(), ledger()
        visuals.enrich_snapshot(payload, records, fixture.resolver, map_preview_mode='minimap')
        for scope in payload['scopes'].values():
            image = scope['battles'][0]['map_visual']
            self.assertEqual(image['src'], 'img://' + MAP_PATH)
            self.assertEqual(image['preview_src'], 'img://' + MAP_DEFAULT_PATH)
            self.assertEqual(image['preview_mode'], 'minimap')

    def test_snapshot_fallback_omits_extra_metadata_and_invalid_mode_uses_default(self):
        fixture = ResolverFixture()
        payload = snapshot()
        visuals.enrich_snapshot(payload, ledger(), fixture.resolver, map_preview_mode='bad')
        self.assertEqual(payload['scopes']['launch']['maps'][0]['visual'],
                         {'kind': 'map', 'src': 'img://' + MAP_PATH, 'alt': 'Karelia'})
        add_screen(fixture)
        visuals.enrich_snapshot(payload, ledger(), fixture.resolver, map_preview_mode='bad')
        self.assertEqual(payload['scopes']['launch']['maps'][0]['visual']['preview_src'], 'img://' + SCREEN_PATH)

    def test_runtime_presentation_mode_reaches_visual_enrichment(self):
        from grz_session_stats.runtime import Runtime
        from test_visuals import Obj
        fixture, original_resolver = ResolverFixture(), visuals._get_native_resolver
        visuals._get_native_resolver = lambda: fixture.resolver
        try:
            raw, saved = snapshot(), ledger()
            runtime = Runtime()
            runtime.active_service = Obj(snapshot=lambda: copy.deepcopy(raw), _state={'battles': saved}, last_error=None)
            runtime._presentation = appearance.build_presentation({'maps': {'preview_mode': 'minimap'}})
            result = runtime.snapshot()
            self.assertEqual(result['scopes']['launch']['maps'][0]['visual']['preview_mode'], 'minimap')
            self.assertNotIn('visual', raw['scopes']['launch']['maps'][0])
            self.assertEqual(saved, ledger())
        finally:
            visuals._get_native_resolver = original_resolver


class MapPreviewConfigTests(unittest.TestCase):
    def test_old_partial_configs_keep_landscape_and_valid_choice_reaches_presentation(self):
        self.assertEqual(appearance.validate_config({'scroll': {'speed_multiplier': 2}})['maps'], {'preview_mode': 'image'})
        for mode in ('image', 'minimap'):
            self.assertEqual(appearance.validate_config({'maps': {'preview_mode': mode}})['maps']['preview_mode'], mode)
            self.assertEqual(appearance.build_presentation({'maps': {'preview_mode': mode}})['map_preview_mode'], mode)

    def test_only_the_two_literal_modes_are_accepted(self):
        for value in (None, True, 1, [], {}, 'MINIMAP', 'screen', 'https://example.test/picture.png'):
            config = appearance.validate_config({'maps': {'preview_mode': value}, 'scroll': {'speed_multiplier': 2}})
            self.assertEqual(config['maps'], {'preview_mode': 'image'})
            self.assertEqual(config['scroll']['speed_multiplier'], 2)
        self.assertEqual(appearance.validate_config({'maps': []})['maps'], {'preview_mode': 'image'})


if __name__ == '__main__':
    unittest.main()
