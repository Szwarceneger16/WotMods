"""Contract, privacy and lifecycle tests without a live WoT installation."""
import base64
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import sys
import tempfile
import threading
import time
import types
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / 'source' / 'mod_grz_hangar_sync.py'
spec = importlib.util.spec_from_file_location('mod_grz_hangar_sync', MODULE)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
for name, filename in (('grz_hangar_battle_pass', 'hangar_battle_pass.py'),
                       ('grz_hangar_stats', 'hangar_stats.py'),
                       ('grz_hangar_crew', 'hangar_crew.py'),
                       ('grz_hangar_mission_metadata', 'hangar_mission_metadata.py')):
    helper_spec = importlib.util.spec_from_file_location('gui.mods.' + name, ROOT / 'source' / filename)
    helper = importlib.util.module_from_spec(helper_spec)
    helper_spec.loader.exec_module(helper)
    sys.modules['gui.mods.' + name] = helper

PIXEL_PNG = base64.b64decode(
    'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aKdYAAAAASUVORK5CYII='
)


class Item:
    def __init__(self, name, cd=21, count=None, kind='standard', level=0):
        self.userName = name
        self.intCD = cd
        self.count = count
        self.isModernized = kind == 'experimental'
        self.isDeluxe = kind == 'bond'
        self.isTrophy = kind == 'bounty'
        self.level = level


class Collection:
    def __init__(self, items):
        self.installed = items


class Modification:
    def __init__(self, name, active_id=1, choice=False, purchased=None):
        self._name = name
        self._active_id = active_id
        self._choice = choice
        self._purchased = purchased

    def getActiveID(self):
        return self._active_id

    def getTechName(self):
        return self._name

    def isMultiAction(self):
        return self._choice

    def getPurchasedModification(self):
        return self._purchased


class Step:
    def __init__(self, action, received=True, level=1):
        self.action = action
        self._received = received
        self._level = level

    def isReceived(self):
        return self._received

    def getLevel(self):
        return self._level


class Progression:
    def __init__(self, steps=None, exists=True):
        self.steps = steps or []
        self.exists = exists

    def isExists(self):
        return self.exists

    def iterUnorderedSteps(self):
        return iter(self.steps)


class Vehicle:
    intCD = 62513
    shortUserName = 'Strv 103B'
    nationName = 'sweden'
    type = 'AT-SPG'
    level = 10
    isPremium = False
    isElite = True

    def __init__(self):
        self.optDevices = Collection([Item('Turbocharger', kind='bounty'), None,
                                      Item('Gun Rammer', kind='experimental', level=3)])
        self.consumables = Collection([Item('Repair Kit'), Item('First Aid Kit')])
        self.shells = Collection([Item('APCR', count=45), None, Item('HE', count=0)])
        self.battleBoosters = Collection([Item('Vent Purge')])
        self.postProgression = Progression([
            Step(Modification('Unlocked feature'), received=True, level=1),
            Step(Modification('Not received'), received=False),
            Step(Modification('Pair container', choice=True,
                              purchased=Modification('Chosen pair')), level=4),
            Step(Modification('No selection', active_id=None)),
        ])
        person = types.SimpleNamespace(fullUserName='Test Commander', roleUserName='Commander',
                                       roleLevel=100, skills=[types.SimpleNamespace(
                                           userName='Repairs', name='repair')])
        self.crew = [(0, person)]


def valid_config():
    return dict(enabled=True, endpoint_url='https://private-example.chatgpt.site/api/sync',
                region='EU', display_name='My Garage', allowed_players=['Commander'],
                include_crew=True,
                interval_seconds=60, device_token='wgs_' + 'a' * 64,
                sites_access_token='opaque-site-private-token',
                include_missions=False, mission_diagnostics=True)


class ConfigurationTests(unittest.TestCase):
    def test_default_example_is_opt_out_and_has_no_secrets(self):
        text = (ROOT / 'GRZ_Hangar_Sync.json.example').read_bytes()
        parsed = mod.parse_config(text)
        self.assertFalse(parsed['enabled'])
        self.assertFalse(parsed['endpoint_url'])
        self.assertFalse(parsed['device_token'])
        self.assertFalse(parsed['sites_access_token'])
        self.assertEqual(parsed['allowed_players'], [])

    def test_accept_explicit_valid_pairing(self):
        self.assertTrue(mod.parse_config(json.dumps(valid_config()))['enabled'])

    def test_missing_value_can_never_enable_network(self):
        for key in ('endpoint_url', 'device_token', 'sites_access_token', 'display_name'):
            config = valid_config()
            config[key] = ''
            with self.subTest(key=key), self.assertRaises(ValueError):
                mod.parse_config(json.dumps(config))

    def test_all_fields_must_be_explicit(self):
        for key in valid_config():
            config = valid_config()
            del config[key]
            with self.subTest(key=key), self.assertRaisesRegex(mod.ConfigError, '^missing_fields$'):
                mod.parse_config(json.dumps(config))

    def test_allowlist_must_be_explicit_and_nonempty_for_sync(self):
        config = dict(valid_config(), allowed_players=[])
        with self.assertRaisesRegex(mod.ConfigError, '^players_list_empty$'):
            mod.parse_config(json.dumps(config))
        for players in ('Commander', None, [False], [''], [' Commander'],
                        ['Commander\n'], ['Commander', 'commander']):
            with self.subTest(players=players), \
                 self.assertRaisesRegex(mod.ConfigError, '^players_list_invalid$'):
                mod.parse_config(json.dumps(dict(config, allowed_players=players)))
        self.assertEqual(mod.parse_config(json.dumps(dict(config, enabled=False)))['allowed_players'],
                         [])

    def test_token_newline_is_not_accepted_as_header_value(self):
        for key in ('device_token', 'sites_access_token'):
            value = dict(valid_config())
            value[key] += '\n'
            with self.subTest(key=key), self.assertRaises(mod.ConfigError):
                mod.parse_config(json.dumps(value))

    def test_endpoint_accepts_only_exact_sites_https_route(self):
        rejected = (
            'http://private-example.chatgpt.site/api/sync',
            'https://localhost/api/sync',
            'https://chatgpt.site.evil.example/api/sync',
            'https://user:password' + chr(64) + 'private-example.chatgpt.site/api/sync',
            'https://private-example.chatgpt.site:443/api/sync',
            'https://private-example.chatgpt.site/api/sync?debug=1',
            'https://private-example.chatgpt.site/api/sync?',
            'https://private-example.chatgpt.site/api/sync#anything',
            'https://private-example.chatgpt.site/api/sync#',
            'https://private-example.chatgpt.site/other',
            'https://private-example.chatgpt.site/api/sync\n',
            'https://private-example..chatgpt.site/api/sync',
            'https://-private.chatgpt.site/api/sync',
        )
        for url in rejected:
            value = dict(valid_config(), endpoint_url=url)
            with self.subTest(url=url), self.assertRaises(mod.ConfigError) as raised:
                mod.parse_config(json.dumps(value))
            self.assertEqual(str(raised.exception), 'endpoint_url_invalid')

    def test_ambiguous_or_unexpected_configuration_is_rejected(self):
        invalid = [
            dict(enabled=1), dict(interval_seconds=True), dict(region='RU'),
            dict(enabled=False, sites_access_token=9),
            dict(enabled=False, sites_access_token='bad\n'),
            dict(enabled=False, endpoint_url='wrong'),
            dict(mission_diagnostics='false'), dict(display_name='bad\nlabel'),
            dict(expected_player='Commander'), dict(unknown=True),
        ]
        raw_configs = [json.dumps(dict(valid_config(), **fields)).encode() for fields in invalid]
        raw_configs += [b'{"enabled":false,"enabled":true}', b'x' * (mod.MAX_CONFIG_BYTES + 1)]
        for raw in raw_configs:
            with self.subTest(raw=raw[:45]), self.assertRaises((ValueError, TypeError)):
                mod.parse_config(raw)

    def test_config_path_rejects_ambiguous_or_unproven_roots(self):
        no_resmgr = types.SimpleNamespace(resolveToAbsolutePath=lambda x: None,
                                          appDirectory=lambda: None)
        self.assertIsNone(mod.config_path(no_resmgr, '/random/executable'))


class VehicleRoleTests(unittest.TestCase):
    def localization(self, name, group):
        gui = types.ModuleType('gui')
        gui.__path__ = []
        shared = types.ModuleType('gui.shared')
        shared.__path__ = []
        formatters = types.ModuleType('gui.shared.formatters')
        formatters.getRoleText = mock.Mock(return_value=name)
        impl = types.ModuleType('gui.impl')
        impl.__path__ = []
        impl.backport = types.SimpleNamespace(text=mock.Mock(return_value=group))
        gen = types.ModuleType('gui.impl.gen')
        dyn = mock.Mock(side_effect=lambda key: lambda: 'native-role-group:' + key)
        gen.R = types.SimpleNamespace(strings=types.SimpleNamespace(menu=types.SimpleNamespace(
            roleExp=types.SimpleNamespace(roleGroupName=types.SimpleNamespace(dyn=dyn)))))
        return mock.patch.dict(sys.modules, {
            'gui': gui, 'gui.shared': shared, 'gui.shared.formatters': formatters,
            'gui.impl': impl, 'gui.impl.gen': gen,
        }), formatters.getRoleText, impl.backport.text, dyn

    def test_native_breakthrough_label_uses_native_localization(self):
        vehicle = Vehicle()
        vehicle.roleLabel = 'role_HT_break'
        vehicle.type = 'heavyTank'
        localization, name, group, dyn = self.localization(
            'Breakthrough Heavy Tank', 'Breakthrough Heavy Tank')
        with localization:
            row = mod.normalize_vehicle(vehicle, include_crew=False)
        self.assertEqual(row['role'], {
            'key': 'role_HT_break', 'name': 'Breakthrough Heavy Tank',
            'groupName': 'Breakthrough Heavy Tank',
        })
        name.assert_called_once_with('role_HT_break')
        dyn.assert_called_once_with('role_HT_break')
        group.assert_called_once_with('native-role-group:role_HT_break')

    def test_missing_role_api_or_localization_keeps_the_garage_available(self):
        self.assertNotIn('role', mod.normalize_vehicle(Vehicle(), include_crew=False))
        vehicle = Vehicle()
        vehicle.roleLabel = 'role_SPG'
        with mock.patch.dict(sys.modules, {'gui.shared.formatters': None,
                                          'gui.impl': None, 'gui.impl.gen': None}):
            row = mod.normalize_vehicle(vehicle, include_crew=False)
        self.assertEqual(row['role'], {'key': 'role_SPG', 'name': None, 'groupName': None})

    def test_unknown_future_native_role_keeps_key_without_guessing_a_name(self):
        vehicle = Vehicle()
        vehicle.roleLabel = 'role_HT_future'
        localization, _, _, _ = self.localization(
            '#menu:roleExp/roleName/role_HT_future', '%(groupName)s')
        with localization:
            row = mod.normalize_vehicle(vehicle, include_crew=False)
        self.assertEqual(row['role'], {
            'key': 'role_HT_future', 'name': None, 'groupName': None,
        })

    def test_invalid_native_role_keys_are_not_stringified_or_inferred(self):
        class Unprintable:
            def __str__(self):
                raise AssertionError('Native objects must not be stringified')

        for key in (None, 3, {'role': 'role_HT_break'}, Unprintable(), 'NotDefined',
                    'role_HT_break\n', 'role_' + 'x' * 65, 'role_HT-break'):
            vehicle = Vehicle()
            vehicle.roleLabel = key
            with self.subTest(key_type=type(key).__name__):
                self.assertNotIn('role', mod.normalize_vehicle(vehicle, include_crew=False))

        class UnavailableRole(Vehicle):
            @property
            def roleLabel(self):
                raise RuntimeError('Native role metadata is unavailable')

        self.assertNotIn('role', mod.normalize_vehicle(UnavailableRole(), include_crew=False))

    def test_native_markup_entities_and_bounds_become_plain_display_text(self):
        vehicle = Vehicle()
        vehicle.roleLabel = b'role_HT_break'
        localization, _, _, _ = self.localization(
            '<font color="#ffd700">Prze\u0142amanie&nbsp;&amp; wsparcie</font>\x00',
            '&lt;b&gt;Ci\u0119\u017cki&lt;/b&gt;&zwnbsp;\ufeff' + 'x' * 300)
        with localization:
            row = mod.normalize_vehicle(vehicle, include_crew=False)
        self.assertEqual(row['role']['name'], 'Prze\u0142amanie & wsparcie')
        self.assertEqual(len(row['role']['groupName']), 240)
        self.assertTrue(row['role']['groupName'].startswith('Ci\u0119\u017cki '))
        self.assertNotIn('<', row['role']['groupName'])

    def test_role_export_reads_only_the_public_role_label_and_localized_text(self):
        class RoleOnlyVehicle(Vehicle):
            roleLabel = 'role_HT_break'

            @property
            def role(self):
                raise AssertionError('No numeric role or descriptor lookup is needed')

            @property
            def _descriptor(self):
                raise AssertionError('Private native objects must not be copied')

        vehicle = RoleOnlyVehicle()
        vehicle.accountDBID = 987654321
        vehicle.private_token = 'fixture-private-marker'
        localization, _, _, _ = self.localization('Breakthrough Heavy Tank', None)
        with localization:
            row = mod.normalize_vehicle(vehicle, include_crew=False)
        self.assertEqual(set(row['role']), {'key', 'name', 'groupName'})
        self.assertNotIn('accountDBID', json.dumps(row))
        self.assertNotIn('fixture-private-marker', json.dumps(row))


class SnapshotTests(unittest.TestCase):
    def test_all_schema_categories_and_active_slots(self):
        row = mod.normalize_vehicle(Vehicle(), include_crew=True)
        self.assertEqual((row['id'], row['tier'], row['nation'], row['type']),
                         (62513, 10, 'Sweden', 'TD'))
        self.assertEqual([(x['name'], x['slot']) for x in row['equipment']],
                         [('Turbocharger', 1), ('Gun Rammer', 3)])
        self.assertEqual(row['equipment'][0]['detail'], 'Bounty equipment')
        self.assertEqual(row['equipment'][1]['detail'], 'Experimental equipment')
        self.assertEqual(row['equipment'][1]['tier'], 3)
        self.assertEqual([x['quantity'] for x in row['ammunition']], [45, 0])
        self.assertEqual(row['directives'][0]['name'], 'Vent Purge')
        self.assertEqual([x['name'] for x in row['fieldMods']],
                         ['Unlocked feature', 'Chosen pair'])
        self.assertEqual(row['crew'][0]['perks'], ['Repairs'])

    def test_excluding_crew_never_exposes_names(self):
        row = mod.normalize_vehicle(Vehicle(), include_crew=False)
        self.assertEqual(row['crew'], [])

    def test_bad_inventory_fails_closed(self):
        vehicle = Vehicle()
        vehicle.optDevices = None
        with self.assertRaises(ValueError):
            mod.make_snapshot('Commander', [vehicle], 'EU', True)

    def test_duplicates_fail_closed(self):
        with self.assertRaises(ValueError):
            mod.make_snapshot('Commander', [Vehicle(), Vehicle()], 'EU', True)

    def test_payload_has_site_schema_and_is_bounded(self):
        snapshot = mod.make_snapshot('Commander', [Vehicle()], 'EU', True)
        body, checksum = mod.encode_snapshot(snapshot)
        value = json.loads(body)
        self.assertEqual(value['schemaVersion'], 1)
        self.assertEqual(value['player'], {'name': 'Commander', 'region': 'EU'})
        self.assertTrue(value['capturedAt'].endswith('Z'))
        self.assertEqual(len(checksum), 64)
        self.assertLessEqual(len(body), mod.MAX_PAYLOAD_BYTES)

    def test_native_vehicle_key_uses_static_site_catalog(self):
        vehicle = Vehicle()
        vehicle.name = 'sweden:S16_Strv_103B'
        artwork = mock.Mock()
        row = mod.normalize_vehicle(vehicle, include_crew=False, artwork=artwork)
        self.assertEqual(row['iconKey'], 'S16_Strv_103B')
        self.assertFalse(any(call.args[1] == 'vehicle' for call in artwork.add.call_args_list))

    def test_daily_stats_compact_before_missions_and_without_mutating_source(self):
        snapshot = mod.make_snapshot('Commander', [Vehicle()], 'EU', False)
        snapshot['missions'] = {'schemaVersion': 1, 'categories': {}}
        snapshot['sessionStats'] = {'schemaVersion': 1, 'provider': 'grz-session-stats',
            'status': 'available', 'scope': 'recordedRandomBattles',
            'vehicles': [{'vehicleId': 62513, 'battles': 2, 'battlesByDay': {'2026-11-05': 2}}]}
        complete, _ = mod.encode_snapshot(snapshot)
        with mock.patch.object(mod, 'MAX_PAYLOAD_BYTES', len(complete) - 1):
            payload, _ = mod.encode_snapshot(snapshot)
        value = json.loads(payload)
        self.assertIn('missions', value)
        self.assertEqual(value['sessionStats']['vehicles'][0]['battles'], 2)
        self.assertNotIn('battlesByDay', value['sessionStats']['vehicles'][0])
        self.assertIn('battlesByDay', snapshot['sessionStats']['vehicles'][0])

    def test_digest_ignores_timestamp_only(self):
        snapshot = mod.make_snapshot('Commander', [Vehicle()], 'EU', True)
        _, first = mod.encode_snapshot(snapshot)
        snapshot['capturedAt'] = '2030-01-01T00:00:00Z'
        _, second = mod.encode_snapshot(snapshot)
        self.assertEqual(first, second)
        snapshot['vehicles'][0]['equipment'][0]['name'] = 'Other equipment'
        _, third = mod.encode_snapshot(snapshot)
        self.assertNotEqual(first, third)

    def test_large_snapshot_is_never_truncated(self):
        value = {'capturedAt': '2026-11-02T00:00:00Z', 'player': {'name': 'Commander', 'region': 'EU'},
                 'vehicles': [{'name': 'x' * (mod.MAX_PAYLOAD_BYTES + 1)}]}
        with self.assertRaises(ValueError):
            mod.encode_snapshot(value)

    def test_overlarge_playlists_do_not_suppress_the_garage_snapshot(self):
        snapshot = mod.make_snapshot('Commander', [Vehicle()], 'EU', False)
        expected = mod.encode_snapshot(snapshot)
        snapshot['playlists'] = [{'id': 'large', 'name': 'All', 'vehicleIds': list(range(1, 200))}]
        with mock.patch.object(mod, 'MAX_PAYLOAD_BYTES', len(expected[0]) + 20):
            self.assertEqual(mod.encode_snapshot(snapshot), expected)

    def test_inventory_does_not_publish_before_cache_sync_or_after_a_missing_vehicle(self):
        get_vehicle = mock.Mock(side_effect=[Vehicle(), None])
        inventory = types.SimpleNamespace(isSynced=lambda: False,
                                          getInvIDsIterator=lambda: iter([5, 10]))
        items = types.SimpleNamespace(inventory=inventory, getVehicle=get_vehicle)
        self.assertEqual(mod._inventory_vehicles(items), [])
        get_vehicle.assert_not_called()
        inventory.isSynced = lambda: True
        with self.assertRaisesRegex(ValueError, 'Owned vehicle details'):
            mod._inventory_vehicles(items)
        self.assertEqual(get_vehicle.call_args_list, [mock.call(5), mock.call(10)])

    def test_game_adapter_only_reads_authenticated_garage_inventory(self):
        player = types.SimpleNamespace(name='Commander', arena=None)
        bigworld = types.ModuleType('BigWorld')
        bigworld.player = lambda: player
        replay = types.ModuleType('BattleReplay')
        replay.isPlaying = lambda: False
        helpers = types.ModuleType('helpers')
        skeletons = types.ModuleType('skeletons')
        gui_pkg = types.ModuleType('skeletons.gui')
        shared = types.ModuleType('skeletons.gui.shared')
        shared.IItemsCache = object()
        game_control = types.ModuleType('skeletons.gui.game_control')
        game_control.IVehiclePlaylistsController = object()
        visible_vehicle = Vehicle()
        hidden_vehicle = Vehicle()
        hidden_vehicle.intCD = 897
        hidden_vehicle.shortUserName = 'Cromwell'
        hidden_vehicle.level = 6
        read_inventory = mock.Mock(side_effect=lambda: iter([5, 10]))
        read_vehicle = mock.Mock(side_effect={5: visible_vehicle, 10: hidden_vehicle}.__getitem__)
        read_filtered = mock.Mock(return_value={visible_vehicle.intCD: visible_vehicle})
        inventory = types.SimpleNamespace(isSynced=lambda: True, getInvIDsIterator=read_inventory)
        read_raw_dossier = mock.Mock(side_effect=lambda cd: b'native-dossier' if cd == 62513 else b'')
        read_dossier = mock.Mock(return_value=types.SimpleNamespace(
            isCurrentUser=lambda: True, getCompactDescriptor=lambda: 62513,
            getGlobalStats=lambda: types.SimpleNamespace(
                getCreationTime=lambda: 1600000000, getLastBattleTime=lambda: 1700000000)))
        cache = types.SimpleNamespace(items=types.SimpleNamespace(
            inventory=inventory, getVehicle=read_vehicle, getVehicles=read_filtered,
            dossiers=types.SimpleNamespace(isSynced=lambda: True, getVehicleDossier=read_raw_dossier),
            getVehicleDossier=read_dossier))
        playlist_data = json.dumps({'title': 'Rotacja dzienna', 'createdAt': 123,
                                    'modifiedAt': 124, 'list': [897, 62513, 777, 897]})
        read_playlists = mock.Mock(side_effect=lambda: iter([
            ('daily', playlist_data),
            ('empty', json.dumps({'title': 'Pusta lista', 'list': []})),
            ('invalid', '{"title":"Private test field","list":[true]}'),
        ]))
        playlists = types.SimpleNamespace(isEnabled=True, iterPlaylists=read_playlists)
        services = {shared.IItemsCache: cache, game_control.IVehiclePlaylistsController: playlists}
        helpers.dependency = types.SimpleNamespace(instance=services.__getitem__)
        modules = {'BigWorld': bigworld, 'BattleReplay': replay, 'helpers': helpers,
                   'skeletons': skeletons, 'skeletons.gui': gui_pkg,
                   'skeletons.gui.shared': shared, 'skeletons.gui.game_control': game_control}
        with mock.patch.dict(sys.modules, modules), \
             mock.patch.object(mod, 'collect_missions', return_value={}) as read_missions, \
             mock.patch.object(mod, 'collect_battle_pass', return_value={'status': 'pending'}) as read_pass:
            config = dict(valid_config(), allowed_players=['OtherCommander', player.name.lower()],
                          include_crew=False, include_missions=True)
            snapshot = mod.collect_game_snapshot(config)
            self.assertEqual([v['name'] for v in snapshot['vehicles']], ['Strv 103B', 'Cromwell'])
            read_inventory.assert_called_once_with()
            self.assertEqual(read_vehicle.call_args_list, [mock.call(5), mock.call(10)])
            read_filtered.assert_not_called()
            read_missions.assert_called_once_with()
            read_pass.assert_called_once_with()
            self.assertEqual(snapshot['battlePass'], {'status': 'pending'})
            read_playlists.assert_called_once_with()
            self.assertEqual(snapshot['vehicles'][0]['crew'], [])
            self.assertEqual(snapshot['vehicles'][0]['statsCreatedAt'], 1600000000)
            self.assertNotIn('statsCreatedAt', snapshot['vehicles'][1])
            read_dossier.assert_called_once_with(62513)
            self.assertEqual(snapshot['player'], {'name': config['display_name'], 'region': 'EU'})
            self.assertEqual(snapshot['playlists'], [
                {'id': 'empty', 'name': 'Pusta lista', 'vehicleIds': []},
                {'id': 'daily', 'name': 'Rotacja dzienna', 'vehicleIds': [897, 62513, 777]},
            ])
            payload, _ = mod.encode_snapshot(snapshot)
            self.assertNotIn(b'Private test field', payload)
            for value in ([player.name] + config['allowed_players'] +
                          [config['endpoint_url'], config['device_token'],
                           config['sites_access_token']]):
                self.assertNotIn(value.encode(), payload)
            read_pass.reset_mock()
            without_missions = mod.collect_game_snapshot(dict(config, include_missions=False))
            self.assertNotIn('battlePass', without_missions)
            read_pass.assert_not_called()
            read_inventory.reset_mock()
            read_missions.reset_mock()
            read_playlists.reset_mock()
            read_raw_dossier.reset_mock()
            read_dossier.reset_mock()
            for players in ([], ['OtherCommander'], ['Command']):
                self.assertIsNone(mod.collect_game_snapshot(dict(config, allowed_players=players)))
            player.arena = object()
            self.assertIsNone(mod.collect_game_snapshot(valid_config()))
            read_inventory.assert_not_called()
            read_missions.assert_not_called()
            read_playlists.assert_not_called()
            read_raw_dossier.assert_not_called()
            read_dossier.assert_not_called()


class DossierMetadataTests(unittest.TestCase):
    def fixture(self, created=100, last_battle=200, raw=b'existing', synced=True,
                current_user=True, compact=62513):
        snapshot = {'vehicles': [{'id': 62513}]}
        raw_reader = mock.Mock(return_value=raw)
        dossier = types.SimpleNamespace(
            isCurrentUser=lambda: current_user, getCompactDescriptor=lambda: compact,
            getGlobalStats=lambda: types.SimpleNamespace(
                getCreationTime=lambda: created, getLastBattleTime=lambda: last_battle))
        gui_reader = mock.Mock(return_value=dossier)
        items = types.SimpleNamespace(
            dossiers=types.SimpleNamespace(isSynced=lambda: synced, getVehicleDossier=raw_reader),
            getVehicleDossier=gui_reader)
        return snapshot, items, raw_reader, gui_reader

    def test_existing_native_date_is_independent_of_session_stats(self):
        snapshot, items, raw_reader, gui_reader = self.fixture()
        mod._add_stats_creation_dates(snapshot, items, now=1000)
        self.assertEqual(snapshot['vehicles'], [{'id': 62513, 'statsCreatedAt': 100}])
        raw_reader.assert_called_once_with(62513)
        gui_reader.assert_called_once_with(62513)
        self.assertNotIn('sessionStats', snapshot)

    def test_absent_or_unsynced_cache_never_constructs_synthetic_dossier(self):
        for values in ({'raw': b''}, {'raw': None}, {'synced': False}):
            snapshot, items, raw_reader, gui_reader = self.fixture(**values)
            mod._add_stats_creation_dates(snapshot, items, now=1000)
            self.assertNotIn('statsCreatedAt', snapshot['vehicles'][0])
            gui_reader.assert_not_called()
            if values.get('synced') is False:
                raw_reader.assert_not_called()

    def test_unproven_invalid_or_foreign_dates_are_omitted(self):
        cases = [dict(created=value) for value in (None, 0, -1, True, 1.5, '100', 1301)]
        cases += [dict(last_battle=value) for value in (None, 0, -1, True, 1301)]
        cases += [{'current_user': False}, {'compact': 897}]
        for values in cases:
            with self.subTest(values=values):
                snapshot, items, _, _ = self.fixture(**values)
                mod._add_stats_creation_dates(snapshot, items, now=1000)
                self.assertNotIn('statsCreatedAt', snapshot['vehicles'][0])

    def test_one_dossier_failure_cannot_block_other_vehicles(self):
        snapshot, items, _, gui_reader = self.fixture()
        snapshot['vehicles'].insert(0, {'id': 897})
        valid = gui_reader.return_value
        gui_reader.side_effect = [RuntimeError('private-error-account-path'), valid]
        mod._add_stats_creation_dates(snapshot, items, now=1000)
        self.assertEqual(snapshot['vehicles'], [{'id': 897}, {'id': 62513, 'statsCreatedAt': 100}])
        self.assertNotIn('private', json.dumps(snapshot))


class ArtworkTests(unittest.TestCase):
    def test_only_native_icon_paths_and_supported_image_formats(self):
        self.assertEqual(mod._artwork_path('../maps/icons/artefact/gun.png', 'item'),
                         'gui/maps/icons/artefact/gun.png')
        self.assertEqual(mod._artwork_path('img://gui/maps/icons/vehicle/tank.png', 'vehicle'),
                         'gui/maps/icons/vehicle/tank.png')
        for value in ('../maps/icons/artefact/../secret.png',
                      'https://example.invalid/gui/maps/icons/artefact/gun.png',
                      'gui/maps/icons/artefact/gun.dds',
                      'gui/maps/icons/artefact/%2egun.png',
                      'gui/maps/icons/tankmen/icons/big/crew.png'):
            self.assertIsNone(mod._artwork_path(value, 'item'))
        self.assertTrue(mod._valid_artwork_bytes(PIXEL_PNG))
        self.assertFalse(mod._valid_artwork_bytes(PIXEL_PNG[:-1]))
        huge_png = PIXEL_PNG[:16] + struct.pack('!I', 4097) + PIXEL_PNG[20:]
        self.assertFalse(mod._valid_artwork_bytes(huge_png))
        jpeg = (b'\xff\xd8\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00'
                b'\xff\xda\x00\x08\x01\x01\x00\x00\x3f\x00\x00\xff\xd9')
        self.assertTrue(mod._valid_artwork_bytes(jpeg))
        self.assertFalse(mod._valid_artwork_bytes(jpeg.replace(b'\xff\xc0', b'\xff\xe0')))
        self.assertFalse(mod._valid_artwork_bytes(b'<svg></svg>'))

    def test_references_dedupe_archive_reads_and_never_publish_paths(self):
        reader = mock.Mock(return_value=PIXEL_PNG)
        store = mod.ArtworkStore(reader)
        artwork = mod.ArtworkCapture(store)
        path = 'gui/maps/icons/vehicle/tank.png'
        rows = [{}, {}]
        for row in rows:
            artwork.add(row, 'vehicle', (path,))
        self.assertTrue(artwork.step())
        reader.assert_called_once_with(path)
        image_id = hashlib.sha256(PIXEL_PNG).hexdigest()
        self.assertEqual(rows, [{'imageId': image_id}] * 2)
        self.assertEqual(store.pending(artwork.image_ids), [(image_id, PIXEL_PNG)])
        store.uploaded([image_id])
        self.assertFalse(store.has_pending(artwork.image_ids))
        self.assertEqual(store.resolve([path]), image_id)
        reader.assert_called_once_with(path)

    def test_payload_limit_drops_images_before_playlists(self):
        snapshot = {'capturedAt': '2026-11-02T00:00:00Z', 'playlists': [],
                    'vehicles': [{'name': 'Tank'}]}
        base_payload, _ = mod.encode_snapshot(snapshot)
        store = mod.ArtworkStore(lambda path: PIXEL_PNG)
        artwork = mod.ArtworkCapture(store)
        artwork.add(snapshot['vehicles'][0], 'vehicle', ('gui/maps/icons/vehicle/tank.png',))
        self.assertTrue(artwork.step())
        with mock.patch.object(mod, 'MAX_PAYLOAD_BYTES', len(base_payload)):
            payload, _ = mod.encode_snapshot(snapshot, artwork)
        self.assertEqual(json.loads(payload)['playlists'], [])
        self.assertNotIn(b'imageId', payload)
        self.assertFalse(artwork.image_ids)

    def test_bounded_asset_batches_keep_every_encoded_record(self):
        cases = ((25, PIXEL_PNG), (9, b'x' * mod.MAX_ARTWORK_BYTES))
        for count, data in cases:
            images = [('%064x' % index, data) for index in range(count)]
            actual = []
            for ids, payload in mod.artwork_batches(images):
                self.assertLessEqual(len(payload), mod.MAX_ARTWORK_BATCH_BYTES)
                self.assertLessEqual(len(ids), mod.MAX_ARTWORK_BATCH_COUNT)
                records = json.loads(payload)['images']
                self.assertEqual(ids, [record['id'] for record in records])
                actual.extend((record['id'], base64.b64decode(record['data']))
                              for record in records)
            self.assertEqual(actual, images)


class RuntimeTests(unittest.TestCase):
    def test_no_schedule_or_network_if_disabled(self):
        with mock.patch.object(mod, 'start_diagnostics', return_value=True), \
             mock.patch.object(mod, 'load_config',
                               return_value=dict(valid_config(), enabled=False,
                                                 mission_diagnostics=False)), \
             mock.patch.object(mod, 'config_path', return_value='/safe/path'), \
             mock.patch.object(mod.SyncRuntime, 'start') as start:
            mod.init()
            start.assert_not_called()

    def test_valid_external_config_starts_sync(self):
        config = dict(valid_config(), mission_diagnostics=False)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / mod.CONFIG_FILE
            path.write_text(json.dumps(config), encoding='utf-8')
            with mock.patch.object(mod, 'config_path', return_value=path), \
                 mock.patch.object(mod, 'start_diagnostics', return_value=True), \
                 mock.patch.object(mod.SyncRuntime, 'start') as start:
                try:
                    mod.init()
                    start.assert_called_once()
                    self.assertEqual(mod._state.config, config)
                finally:
                    mod.fini()

    def test_no_network_when_appdata_log_is_unavailable(self):
        with mock.patch.object(mod, 'start_diagnostics', return_value=False), \
             mock.patch.object(mod, 'load_config') as load:
            mod.init()
            load.assert_not_called()

    def test_one_worker_and_one_pending_snapshot(self):
        sent = []
        completed = threading.Event()
        fake_game = types.SimpleNamespace(callback=lambda delay, func: 10,
                                          cancelCallback=lambda token: None)
        def transport(payload, config):
            sent.append(json.loads(payload))
            completed.set()
        runtime = mod.SyncRuntime(valid_config(), game=fake_game, transport=transport)
        with mock.patch.object(mod, 'collect_game_snapshot',
                               return_value=mod.make_snapshot('A', [Vehicle()], 'EU', True)):
            try:
                runtime.start()
                runtime.tick()
                self.assertTrue(completed.wait(3), 'Worker did not process pending snapshot')
                deadline = time.monotonic() + 3
                while runtime.last_sent is None and time.monotonic() < deadline:
                    time.sleep(0.01)
                runtime.tick()
                self.assertEqual(len(sent), 1)
            finally:
                runtime.stop()
                runtime.worker.join(timeout=2)
        self.assertFalse(runtime.worker.is_alive())

    def test_game_exit_cancels_tick(self):
        cancelled = []
        fake_game = types.SimpleNamespace(callback=lambda delay, func: 47,
                                          cancelCallback=lambda ident: cancelled.append(ident))
        runtime = mod.SyncRuntime(valid_config(), game=fake_game)
        runtime._schedule(5)
        runtime.stop()
        self.assertEqual(cancelled, [47])
        self.assertTrue(runtime.stopped.is_set())

    def test_artwork_only_retries_after_accepted_snapshot(self):
        completed = threading.Event()
        transmissions = []
        game = types.SimpleNamespace(callback=lambda delay, func: 10,
                                     cancelCallback=lambda token: None)

        def send_snapshot(payload, config):
            transmissions.append(('snapshot', json.loads(payload)))

        def send_artwork(payload, config):
            transmissions.append(('artwork', json.loads(payload)))
            completed.set()
            if len(transmissions) == 2:
                raise IOError('asset transport failed')

        def capture(config, artwork):
            vehicle = {'id': 1, 'name': 'Tank'}
            artwork.add(vehicle, 'vehicle', ('gui/maps/icons/vehicle/tank.png',))
            return {'capturedAt': '2026-11-02T00:00:00Z', 'vehicles': [vehicle]}

        runtime = mod.SyncRuntime(valid_config(), game, send_snapshot, send_artwork)
        runtime.artwork_store = mod.ArtworkStore(lambda path: PIXEL_PNG)
        with mock.patch.object(mod, 'collect_game_snapshot', side_effect=capture):
            try:
                runtime.start()
                for _ in range(2):
                    runtime.tick()
                    self.assertTrue(completed.wait(3))
                    deadline = time.monotonic() + 3
                    while runtime.last_attempt is not None and time.monotonic() < deadline:
                        time.sleep(0.01)
                    completed.clear()
            finally:
                runtime.stop()
                runtime.worker.join(timeout=2)
        self.assertEqual([kind for kind, _ in transmissions],
                         ['snapshot', 'artwork', 'artwork'])
        image_id = transmissions[0][1]['vehicles'][0]['imageId']
        self.assertEqual(transmissions[2][1]['images'][0]['id'], image_id)
        self.assertFalse(runtime.artwork_store.has_pending([image_id]))


class NetworkTests(unittest.TestCase):
    def test_configured_https_origin_no_proxy_no_redirect_and_verified_tls(self):
        capture = {}
        ssl_module = types.ModuleType('ssl')
        ssl_module.CERT_REQUIRED = 2
        context = types.SimpleNamespace(verify_mode=None, check_hostname=False)
        ssl_module.create_default_context = lambda: context

        urllib2 = types.ModuleType('urllib2')
        class RedirectHandler:
            pass
        class Response:
            def getcode(self):
                return 200
            def read(self, amount):
                capture['maximum_response_bytes'] = amount
                return b'{"ok":true}'
            def close(self):
                capture['closed'] = True
        class Opener:
            def open(self, request, timeout):
                capture['request'] = request
                capture['timeout'] = timeout
                return Response()
        def build_opener(*handlers):
            capture['handlers'] = handlers
            return Opener()
        class Request:
            def __init__(self, url, data, headers):
                self.url = url
                self.data = data
                self.headers = headers
        urllib2.HTTPRedirectHandler = RedirectHandler
        urllib2.ProxyHandler = lambda proxies: ('proxies', proxies)
        urllib2.HTTPSHandler = lambda context: ('https', context)
        urllib2.build_opener = build_opener
        urllib2.Request = Request
        with mock.patch.dict(sys.modules, {'urllib2': urllib2, 'ssl': ssl_module}):
            mod.send_snapshot(b'{"schemaVersion":1}', valid_config())

        request = capture['request']
        self.assertEqual(request.url, valid_config()['endpoint_url'])
        self.assertTrue(request.url.startswith('https://'))
        self.assertEqual(capture['handlers'][0], ('proxies', {}))
        self.assertEqual(capture['handlers'][1], ('https', context))
        self.assertTrue(capture['handlers'][2].redirect_request(None, None, 302, '', {}, '') is None)
        self.assertEqual(context.verify_mode, 2)
        self.assertTrue(context.check_hostname)
        self.assertEqual(capture['timeout'], 8)
        self.assertEqual(capture['maximum_response_bytes'], 4097)
        self.assertTrue(capture['closed'])
        self.assertTrue(request.headers['OAI-Sites-Authorization'].startswith('Bearer '))
        with mock.patch.dict(sys.modules, {'urllib2': urllib2, 'ssl': ssl_module}):
            mod.send_artwork(b'{"images":[]}', valid_config())
        self.assertEqual(capture['request'].url, valid_config()['endpoint_url'] + '/assets')

    def test_no_insecure_tls_fallback(self):
        fake_ssl = types.ModuleType('ssl')
        with mock.patch.dict(sys.modules, {'ssl': fake_ssl}):
            with self.assertRaises(mod.TLSUnavailable):
                mod.send_snapshot(b'{}', valid_config())
        self.assertEqual(mod._network_error_kind(mod.TLSUnavailable('PRIVATE_MARKER')),
                         ('tls', 0))

    def test_rejects_bad_destination_before_network_setup(self):
        config = dict(valid_config(), endpoint_url='https://other.example/api/sync')
        with self.assertRaises(mod.ConfigError):
            mod.send_snapshot(b'{}', config)

    def test_rejects_disabled_or_invalid_config_before_tls_setup(self):
        for config in (dict(valid_config(), enabled=False), dict(valid_config(), device_token=''),
                       dict(valid_config(), allowed_players=[])):
            with self.subTest(enabled=config['enabled']), \
                 mock.patch.dict(sys.modules, {'ssl': None, 'urllib2': None}), \
                 self.assertRaises(mod.ConfigError):
                mod.send_snapshot(b'{}', config)


class DiagnosticsTests(unittest.TestCase):
    def tearDown(self):
        for handler in list(mod.LOG.handlers):
            mod.LOG.removeHandler(handler)
            handler.close()
        mod.LOG.propagate = True

    def test_appdata_log_has_no_secrets_or_user_identifiers(self):
        with tempfile.TemporaryDirectory() as appdata:
            with mock.patch.object(mod, 'LOG_MAX_BYTES', 2048):
                self.assertTrue(mod.start_diagnostics({'APPDATA': appdata}))
            config = dict(valid_config(), allowed_players=['PRIVATE_NICKNAME_MARKER'])
            poison = 'SECRET_ERROR_MARKER ' + config['endpoint_url'] + ' ' + config['device_token']
            completed = threading.Event()
            def failing_transport(payload, unused_config):
                completed.set()
                raise RuntimeError(poison)
            game = types.SimpleNamespace(callback=lambda delay, callback: 17,
                                         cancelCallback=lambda callback_id: None)
            runtime = mod.SyncRuntime(config, game=game, transport=failing_transport)
            with mock.patch.object(mod, 'collect_game_snapshot',
                                   return_value=mod.make_snapshot('PRIVATE_NICKNAME_MARKER',
                                                                  [Vehicle()], 'EU', True)):
                try:
                    runtime.start()
                    runtime.tick()
                    self.assertTrue(completed.wait(3))
                    deadline = time.monotonic() + 3
                    while runtime.failures == 0 and time.monotonic() < deadline:
                        time.sleep(0.01)
                finally:
                    runtime.stop()
                    runtime.worker.join(timeout=2)
            log_path = Path(appdata) / mod.LOG_DIR / mod.LOG_FILE
            self.assertTrue(log_path.is_file())
            content = log_path.read_text(encoding='utf-8')
            self.assertIn('event=send_attempt', content)
            self.assertIn('event=send_failed kind=protocol http_status=0', content)
            self.assertIn('event=capture_ready vehicle_count=1', content)
            self.assertNotIn('PRIVATE_NICKNAME_MARKER', content)
            self.assertNotIn(config['endpoint_url'], content)
            self.assertNotIn(config['device_token'], content)
            self.assertNotIn(config['sites_access_token'], content)
            self.assertNotIn('SECRET_ERROR_MARKER', content)
            self.assertNotIn('Traceback', content)

            for number in range(100):
                mod.LOG.info('event=diagnostic_test sequence=%d', number)
            for handler in mod.LOG.handlers:
                handler.flush()
            self.assertTrue(log_path.with_name(mod.LOG_FILE + '.1').exists())
            self.assertFalse(log_path.with_name(mod.LOG_FILE + '.3').exists())

    def test_logs_http_status_without_http_error_details(self):
        class HTTPError(Exception):
            code = 403
        kind, status = mod._network_error_kind(HTTPError('PRIVATE_URL_AND_TOKENS'))
        self.assertEqual((kind, status), ('http', 403))

    def test_missing_config_error_has_safe_explanation(self):
        import errno
        missing = IOError(errno.ENOENT, 'PRIVATE_PATH_MARKER')
        self.assertEqual(mod._config_error_code(missing), 'file_not_found')
        self.assertEqual(mod._config_error_code(mod.ConfigError('endpoint_url_invalid')),
                         'endpoint_url_invalid')


if __name__ == '__main__':
    unittest.main()
