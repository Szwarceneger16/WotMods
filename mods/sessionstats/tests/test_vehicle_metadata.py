# -*- coding: utf-8 -*-
"""Native class/role presentation resolves descriptors, not saved display names."""
from __future__ import unicode_literals

import copy
import unittest

from test_visuals import Obj, Node, Branch, ResolverFixture, VEHICLE_ID, snapshot, ledger
from grz_session_stats.visuals import canonical_vehicle_class, _native_role_text, enrich_snapshot


CLASS_PATH = 'gui/maps/icons/vehicleTypes/44x44/AT-SPG.png'
ROLE_KEY = 'role_ATSPG_sniper'
ROLE_PATH = 'gui/maps/icons/roleExp/roles/24x24/' + ROLE_KEY + '.png'


def fixture():
    value = ResolverFixture()
    descriptor = value.vehicles[VEHICLE_ID]
    descriptor.classTag = 'AT-SPG'
    descriptor.tags = frozenset(['AT-SPG', 'synthetic'])
    descriptor.level = 10
    descriptor.role = 17  # Synthetic number; the adapter uses the live mapping.
    icons = value.resources.images.gui.maps.icons
    icons.vehicleTypes = Obj(c_44x44=Branch({'AT_SPG': Node(31)}), big=Branch())
    icons.roleExp = Obj(roles=Obj(c_24x24=Branch({ROLE_KEY: Node(32)})))
    value.paths.update({31: 'img://' + CLASS_PATH, 32: 'img://' + ROLE_PATH})
    value.files.update([CLASS_PATH, ROLE_PATH])
    value.resources.strings = Obj(menu=Obj(roleExp=Obj(
        roleGroupName=Branch({ROLE_KEY: Node(41)}), roleDescr=Branch({ROLE_KEY: Node(42)}))))
    value.role_calls = []
    def label(descriptor):
        value.role_calls.append(descriptor.role)
        return {17: ROLE_KEY}.get(descriptor.role)
    value.resolver._role_label_getter = label
    value.resolver._role_name_getter = lambda key: 'Native client role'
    value.resolver._text_getter = lambda identifier: {41: 'Native client group',
        42: '<font color="#fff">Native definition.</font><br/>Second paragraph.'}[identifier]
    return value


class VehicleMetadataTests(unittest.TestCase):
    def test_native_at_spg_alias_has_the_same_class_without_guessing_names(self):
        for value in ('AT-SPG', 'AT_SPG', b'AT-SPG'):
            self.assertEqual(canonical_vehicle_class(value), 'AT_SPG')
        for value in (None, False, {}, 'Strv 103B', 'TD', 'futureTank'):
            self.assertIsNone(canonical_vehicle_class(value))

    def test_original_class_and_role_images_and_native_paragraphs_are_resolved(self):
        value = fixture()
        data = value.resolver.vehicle_metadata(VEHICLE_ID)
        self.assertEqual(data['class'], 'AT_SPG')
        self.assertEqual(data['tier'], 10)
        self.assertEqual(data['class_icon'], {'kind': 'vehicle_class', 'src': 'img://' + CLASS_PATH})
        self.assertEqual(data['role'], {'key': ROLE_KEY, 'name': 'Native client role',
            'group_name': 'Native client group', 'description': 'Native definition.\nSecond paragraph.',
            'icon': {'kind': 'vehicle_role', 'src': 'img://' + ROLE_PATH}})
        self.assertEqual(value.role_calls, [17])

    def test_success_cache_is_owned_and_returned_metadata_cannot_mutate_it(self):
        value = fixture()
        data = value.resolver.vehicle_metadata(VEHICLE_ID)
        data['role']['description'] = 'mutated'
        for unused in range(3):
            self.assertEqual(value.resolver.vehicle_metadata(VEHICLE_ID)['role']['description'],
                             'Native definition.\nSecond paragraph.')
        self.assertEqual(value.role_calls, [17])

    def test_missing_class_tag_uses_exact_native_tags_and_unknown_role_is_not_guessed(self):
        value = fixture()
        value.vehicles[VEHICLE_ID].classTag = None
        value.vehicles[VEHICLE_ID].role = 999
        data = value.resolver.vehicle_metadata(VEHICLE_ID)
        self.assertEqual(data['class'], 'AT_SPG')
        self.assertNotIn('role', data)
        value.vehicles[VEHICLE_ID].tags = frozenset(['unknown'])
        self.assertNotIn('class', value.resolver.vehicle_metadata(VEHICLE_ID))

    def test_missing_optional_native_apis_can_recover_and_do_not_poison_cache(self):
        value = fixture()
        def unavailable(unused):
            raise RuntimeError('not mounted yet')
        value.resolver._role_label_getter = unavailable
        self.assertEqual(value.resolver.vehicle_metadata(VEHICLE_ID)['class'], 'AT_SPG')
        value.resolver._role_label_getter = lambda descriptor: ROLE_KEY
        self.assertEqual(value.resolver.vehicle_metadata(VEHICLE_ID)['role']['key'], ROLE_KEY)

    def test_wrong_descriptors_and_noncompact_values_never_alias_a_vehicle(self):
        value = fixture()
        value.vehicles[VEHICLE_ID].compactDescr = VEHICLE_ID + 1
        for identifier in (VEHICLE_ID, None, 'Strv 103B', True, '-1', '257\n'):
            self.assertIsNone(value.resolver.vehicle_metadata(identifier))

    def test_spg_has_its_original_class_icon_and_no_fabricated_role_art(self):
        value = fixture()
        value.vehicles[VEHICLE_ID].classTag = 'SPG'
        path = 'gui/maps/icons/vehicleTypes/44x44/SPG.png'
        value.resources.images.gui.maps.icons.vehicleTypes.c_44x44.nodes = {'SPG': Node(33)}
        value.paths[33] = 'img://' + path
        value.files.add(path)
        value.resolver._role_label_getter = lambda descriptor: 'role_SPG'
        data = value.resolver.vehicle_metadata(VEHICLE_ID)
        self.assertEqual(data['class'], 'SPG')
        self.assertEqual(data['role']['key'], 'role_SPG')
        self.assertNotIn('icon', data['role'])
        self.assertTrue(data.get('class_icon'))

    def test_unknown_future_role_is_not_given_a_fabricated_name_or_definition(self):
        value = fixture()
        value.resolver._role_label_getter = lambda descriptor: 'role_ATSPG_future'
        value.resolver._role_name_getter = lambda key: '#menu:roleExp/roleName/' + key
        data = value.resolver.vehicle_metadata(VEHICLE_ID)
        self.assertEqual(data['role'], {'key': 'role_ATSPG_future'})

    def test_wrong_image_family_and_missing_textures_do_not_remove_metadata(self):
        value = fixture()
        value.paths[31] = 'img://gui/maps/icons/map/small/01_karelia.png'
        value.files.discard(ROLE_PATH)
        data = value.resolver.vehicle_metadata(VEHICLE_ID)
        self.assertNotIn('class_icon', data)
        self.assertNotIn('icon', data['role'])
        self.assertEqual(data['class'], 'AT_SPG')
        self.assertEqual(data['role']['description'], 'Native definition.\nSecond paragraph.')

    def test_optional_class_size_and_role_group_api_fail_independently(self):
        value = fixture()
        icons = value.resources.images.gui.maps.icons
        icons.vehicleTypes = Obj(big=Branch({'AT_SPG': Node(33)}))
        path = 'gui/maps/icons/vehicleTypes/big/AT-SPG.png'
        value.paths[33] = 'img://' + path
        value.files.add(path)
        del value.resources.strings.menu.roleExp.roleGroupName
        data = value.resolver.vehicle_metadata(VEHICLE_ID)
        self.assertEqual(data['class_icon']['src'], 'img://' + path)
        self.assertNotIn('group_name', data['role'])
        self.assertEqual(data['role']['description'], 'Native definition.\nSecond paragraph.')

    def test_native_strings_are_plain_bounded_and_unresolved_tokens_are_omitted(self):
        self.assertEqual(_native_role_text('&lt;b&gt;Rola&nbsp;&amp; wsparcie&lt;/b&gt;<br/>Druga\x00 linia'),
                         'Rola & wsparcie\nDruga linia')
        self.assertEqual(len(_native_role_text('a' * 300)), 240)
        for text in ('#menu:roleExp/roleName/role_HT_break', '%(groupName)s', '{role}', None, 2):
            self.assertIsNone(_native_role_text(text))
        value = fixture()
        value.resolver._role_name_getter = lambda key: '#menu:roleExp/roleName/' + key
        value.resolver._text_getter = lambda identifier: '%(groupName)s'
        data = value.resolver.vehicle_metadata(VEHICLE_ID)['role']
        self.assertNotIn('name', data)
        self.assertNotIn('description', data)

    def test_historic_vehicle_and_battle_rows_are_backfilled_without_ledger_rewrite(self):
        value = fixture()
        payload = snapshot()
        records = ledger()
        original_records = copy.deepcopy(records)
        summary = copy.deepcopy(payload['scopes']['launch']['summary'])
        for scope in payload['scopes'].values():
            scope['vehicles'][0]['type'] = None
        enrich_snapshot(payload, records, value.resolver)
        for scope in payload['scopes'].values():
            for grouping in ('vehicles', 'battles'):
                row = scope[grouping][0]
                self.assertEqual(row['type'], 'AT_SPG')
                self.assertEqual(row['vehicle_meta']['role']['key'], ROLE_KEY)
            self.assertNotIn('vehicle_meta', scope['maps'][0])
        payload['scopes']['launch']['vehicles'][0]['vehicle_meta']['role']['name'] = 'changed'
        self.assertEqual(payload['scopes']['manual']['vehicles'][0]['vehicle_meta']['role']['name'], 'Native client role')
        self.assertEqual(records, original_records)
        self.assertEqual(payload['scopes']['launch']['summary'], summary)

    def test_stale_metadata_is_removed_when_the_descriptor_is_unavailable(self):
        value = fixture()
        payload = snapshot()
        payload['scopes']['launch']['vehicles'][0]['vehicle_meta'] = {'class': 'heavyTank'}
        value.vehicles.clear()
        enrich_snapshot(payload, ledger(), value.resolver)
        self.assertNotIn('vehicle_meta', payload['scopes']['launch']['vehicles'][0])


if __name__ == '__main__':
    unittest.main()
