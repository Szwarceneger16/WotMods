# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import contextlib
import copy
import datetime
import json
import os
import sys
import types
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'source'))
import mod_grz_hangar_sync as mod
import hangar_crew

for package_name in ('gui', 'gui.mods'):
    if package_name not in sys.modules:
        module = types.ModuleType(str(package_name))
        module.__path__ = []
        sys.modules[package_name] = module
sys.modules['gui.mods.grz_hangar_crew'] = hangar_crew


class Obj(object):
    def __init__(self, **values):
        self.__dict__.update(values)


def member(identifier, assigned=-1, **changes):
    values = dict(invID=identifier, fullUserName='Game crew member', roleUserName='Loader',
                  roleLevel=100, skills=[], isDismissed=False, vehicleInvID=assigned,
                  isInTank=assigned > 0, icon='game_crew.png', skin=None)
    values.update(changes)
    return Obj(**values)


@contextlib.contextmanager
def barracks_constant():
    original = sys.modules.get('constants')
    constants = types.ModuleType(str('constants'))
    constants.VEHICLE_NO_INV_ID = -1
    sys.modules['constants'] = constants
    try:
        yield
    finally:
        if original is None:
            sys.modules.pop('constants', None)
        else:
            sys.modules['constants'] = original


def fixture(remembered, persons=None, assignments=None, current=None, synced=True):
    persons, assignments = persons or {}, assignments or {}
    vehicle = Obj(intCD=23329, invID=700000001, lastCrew=remembered, crew=current or [])
    other = Obj(intCD=62513, invID=700000002)
    rows = [{'id': 23329, 'name': 'Gorilla', 'crew': []},
            {'id': 62513, 'name': 'Another tank', 'crew': []}]
    snapshot = {'capturedAt': '2026-11-06T00:00:00Z', 'vehicles': rows}
    reads = {'tankman': [], 'raw': [], 'vehicle': []}

    def read_raw(identifier):
        reads['raw'].append(identifier)
        return Obj(vehicle=assignments.get(identifier, -1)) if identifier in persons else None

    def read_member(identifier):
        reads['tankman'].append(identifier)
        return persons.get(identifier)

    def read_vehicle(identifier):
        reads['vehicle'].append(identifier)
        return {vehicle.invID: vehicle, other.invID: other}.get(identifier)

    items = Obj(inventory=Obj(isSynced=lambda: synced, getTankmanData=read_raw),
                getTankman=read_member, getVehicle=read_vehicle)
    return snapshot, vehicle, items, reads


class RememberedCrewTests(unittest.TestCase):
    def test_removed_crew_is_separate_and_has_actual_current_locations(self):
        ids = [900000000001, 900000000002, 900000000003]
        people = {ids[0]: member(ids[0]), ids[1]: member(ids[1], 700000002),
                  ids[2]: member(ids[2], 700000099, isInTank=False, vehicleInvID=-1)}
        snapshot, vehicle, items, _ = fixture(ids, people, {ids[1]: 700000002, ids[2]: 700000099})
        before = copy.deepcopy(snapshot['vehicles'][0]['crew'])
        with barracks_constant():
            mod._add_remembered_crew(snapshot, [vehicle], items)
        row = snapshot['vehicles'][0]
        self.assertEqual(row['crew'], before)
        self.assertEqual(row['lastCrewStatus'], 'available')
        self.assertEqual(row['lastCrewSource'], 'previous_battle')
        self.assertEqual(row['lastCrewExpectedCount'], 3)
        self.assertEqual(row['lastCrewMissingCount'], 0)
        self.assertEqual([person['slot'] for person in row['lastCrew']], [0, 1, 2])
        self.assertEqual([person['location'] for person in row['lastCrew']], [
            {'kind': 'barracks'}, {'kind': 'vehicle', 'vehicleId': 62513, 'vehicleName': 'Another tank'},
            {'kind': 'unknown'}])
        payload, _ = mod.encode_snapshot(snapshot)
        for identifier in ids + [700000001, 700000002, 700000099]:
            self.assertNotIn(str(identifier).encode('ascii'), payload)
        self.assertNotIn(b'invID', payload)

    def test_same_ids_must_match_slots_and_no_duplicate_roster_is_sent(self):
        first, second = member(900000000001), member(900000000002)
        ids = [first.invID, second.invID]
        people = {first.invID: first, second.invID: second}
        snapshot, vehicle, items, reads = fixture(ids, people, current=[(0, first), (1, second)])
        mod._add_remembered_crew(snapshot, [vehicle], items)
        self.assertEqual(snapshot['vehicles'][0]['lastCrewStatus'], 'same_as_current')
        self.assertNotIn('lastCrew', snapshot['vehicles'][0])
        self.assertEqual(reads['tankman'], [])
        snapshot, vehicle, items, _ = fixture(ids, people, current=[(0, second), (1, first)])
        mod._add_remembered_crew(snapshot, [vehicle], items)
        self.assertEqual(snapshot['vehicles'][0]['lastCrewStatus'], 'available')

    def test_missing_dismissed_and_unreadable_members_remain_partial(self):
        ids = [900000000001, 900000000002, 900000000003, 900000000004]
        people = {ids[0]: member(ids[0]), ids[2]: member(ids[2], isDismissed=True),
                  ids[3]: member(ids[3], fullUserName=None)}
        snapshot, vehicle, items, reads = fixture(ids, people)
        mod._add_remembered_crew(snapshot, [vehicle], items)
        row = snapshot['vehicles'][0]
        self.assertEqual(row['lastCrewStatus'], 'partial')
        self.assertEqual(row['lastCrewMissingCount'], 3)
        self.assertEqual(len(row['lastCrew']), 1)
        self.assertNotIn(ids[1], reads['tankman'])
        snapshot, vehicle, items, _ = fixture([ids[1]], {})
        mod._add_remembered_crew(snapshot, [vehicle], items)
        self.assertEqual(snapshot['vehicles'][0]['lastCrew'], [])
        self.assertEqual(snapshot['vehicles'][0]['lastCrewStatus'], 'partial')

    def test_no_native_history_differs_from_unsupported_or_unsynced(self):
        for remembered in (None, [], [None, None]):
            snapshot, vehicle, items, _ = fixture(remembered)
            mod._add_remembered_crew(snapshot, [vehicle], items)
            self.assertEqual(snapshot['vehicles'][0]['lastCrewStatus'], 'none')
            self.assertEqual(snapshot['vehicles'][0]['lastCrewExpectedCount'], 0)
        snapshot, vehicle, items, reads = fixture([900000000001], synced=False)
        mod._add_remembered_crew(snapshot, [vehicle], items)
        self.assertEqual(snapshot['vehicles'][0]['lastCrewStatus'], 'unavailable')
        self.assertEqual(reads['raw'], [])
        snapshot, vehicle, items, _ = fixture(None)
        del vehicle.lastCrew
        mod._add_remembered_crew(snapshot, [vehicle], items)
        self.assertEqual(snapshot['vehicles'][0]['lastCrewStatus'], 'unavailable')

    def test_invalid_records_or_mismatched_gui_identity_do_not_escape(self):
        for invalid in ('private-id', [True], [0], [-1], [1] * 11):
            snapshot, vehicle, items, _ = fixture(invalid)
            mod._add_remembered_crew(snapshot, [vehicle], items)
            self.assertEqual(snapshot['vehicles'][0]['lastCrewStatus'], 'unavailable')
        snapshot, vehicle, items, _ = fixture([900000000001], {900000000001: member(900000000099)})
        mod._add_remembered_crew(snapshot, [vehicle], items)
        self.assertEqual(snapshot['vehicles'][0]['lastCrewMissingCount'], 1)

    def test_no_location_inference_from_training_or_unresolved_gui_vehicle(self):
        identifier = 900000000001
        person = member(identifier, -1, vehicleNativeDescr=Obj(type=Obj(compactDescr=999)))
        for assigned in (0, None, 700000099):
            snapshot, vehicle, items, _ = fixture([identifier], {identifier: person}, {identifier: assigned})
            with barracks_constant():
                mod._add_remembered_crew(snapshot, [vehicle], items)
            self.assertEqual(snapshot['vehicles'][0]['lastCrew'][0]['location'], {'kind': 'unknown'})

    def test_historical_profile_keeps_training_without_origin_vehicle_effects(self):
        from test_hangar_crew import native_modules, tankman
        identifier = 900000000001
        person = tankman()
        person.__dict__.update(member(identifier).__dict__)
        from test_hangar_crew import skill
        person.skills = [skill(level=37)]
        person.skillsCount = 1
        snapshot, vehicle, items, _ = fixture([identifier], {identifier: person})
        with native_modules() as calls:
            mod._add_remembered_crew(snapshot, [vehicle], items)
        learned = snapshot['vehicles'][0]['lastCrew'][0]['skills'][0]
        self.assertEqual(learned['level'], 37)
        self.assertNotIn('description', learned)
        self.assertNotIn('effects', learned)
        self.assertTrue(all(tman is None for tman, _, _ in calls))
        self.assertTrue(snapshot['crewSkillCatalog'])

    @unittest.skipUnless(sys.version_info[0] >= 3, 'Main game harness uses Python 3')
    def test_history_reading_requires_allowed_account_and_include_crew(self):
        from unittest import mock
        from test_hangar_sync import valid_config
        player = Obj(name='Commander', arena=None)
        cache = Obj(items=Obj())
        marker = object()
        modules = {
            'BigWorld': Obj(player=lambda: player), 'BattleReplay': Obj(isPlaying=lambda: False),
            'helpers': Obj(dependency=Obj(instance=lambda _: cache)),
            'skeletons.gui.shared': Obj(IItemsCache=marker),
        }
        snapshot = {'vehicles': [{'id': 23329, 'name': 'Gorilla', 'crew': []}]}
        with mock.patch.dict(sys.modules, modules), \
             mock.patch.object(mod, '_inventory_vehicles', return_value=[Obj()]) as inventory, \
             mock.patch.object(mod, 'make_snapshot', return_value=snapshot), \
             mock.patch.object(mod, '_add_remembered_crew') as history, \
             mock.patch.object(mod, '_add_stats_creation_dates'), \
             mock.patch.object(mod, '_collect_playlists', return_value=None):
            config = valid_config()
            mod.collect_game_snapshot(dict(config, include_crew=False))
            history.assert_not_called()
            mod.collect_game_snapshot(config)
            history.assert_called_once()
            history.reset_mock()
            inventory.reset_mock()
            self.assertIsNone(mod.collect_game_snapshot(dict(config, allowed_players=['OtherCommander'])))
            history.assert_not_called()
            inventory.assert_not_called()

    @unittest.skipUnless(sys.version_info[0] >= 3, 'Large main fixture uses Python 3 harness')
    def test_47_full_changed_rosters_with_optional_stats_and_missions_fit_bounded_payload(self):
        from test_hangar_crew import native_modules, tankman, skill
        from test_hangar_sync import Vehicle
        from test_missions import MissionTests
        vehicles, people = [], {}
        for number in range(1, 48):
            vehicle = Vehicle()
            vehicle.intCD = number
            vehicle.invID = 700000000 + number
            vehicle.crew, vehicle.lastCrew = [], []
            for slot in range(6):
                person = tankman([skill('skill' + str(index), 100 if index < 5 else 37)
                                  for index in range(6)])
                person.__dict__.update(member(900000000000 + number * 10 + slot,
                                              vehicle.invID).__dict__)
                person.skills = [skill('skill' + str(index), 100 if index < 5 else 37)
                                 for index in range(6)]
                person.skillsCount = 6
                vehicle.crew.append((slot, person))
                previous = copy.copy(person)
                previous.invID = 950000000000 + number * 10 + slot
                previous.vehicleInvID, previous.isInTank = -1, False
                people[previous.invID] = previous
                vehicle.lastCrew.append(previous.invID)
            vehicles.append(vehicle)
        items = Obj(inventory=Obj(isSynced=lambda: True,
                                 getTankmanData=lambda identifier: Obj(vehicle=-1) if identifier in people else None),
                    getTankman=people.get, getVehicle=lambda _: None)
        with native_modules():
            sys.modules['constants'].VEHICLE_NO_INV_ID = -1
            snapshot = mod.make_snapshot('Fixture garage', vehicles, 'EU', True)
            mod._add_remembered_crew(snapshot, vehicles, items)
        mission_fixture = MissionTests('test_known_sources_and_crucible_missing_stage')
        with mission_fixture.game_modules():
            snapshot['missions'] = mod.collect_missions()
        first = datetime.date(2025, 11, 6)
        days = {(first + datetime.timedelta(days=index)).isoformat(): 1 for index in range(366)}
        snapshot['sessionStats'] = {
            'schemaVersion': 1, 'provider': 'grz-session-stats', 'providerVersion': '0.4.1',
            'status': 'available', 'scope': 'recordedRandomBattles',
            'dayRange': {'from': '2025-11-06', 'through': '2026-11-06', 'basis': 'gameLocalTime'},
            'vehicles': [{'vehicleId': vehicle.intCD, 'battles': 366, 'wn8': 1500,
                          'creditsNet': 12345, 'lastPlayedAt': 1793923200, 'battlesToday': 1,
                          'battlesByDay': days, 'ownedSince': None} for vehicle in vehicles],
        }
        payload, _ = mod.encode_snapshot(snapshot)
        decoded = json.loads(payload)
        self.assertGreater(len(payload), 850000)
        self.assertLessEqual(len(payload), mod.MAX_PAYLOAD_BYTES)
        self.assertEqual(sum(len(person['skills']) for row in decoded['vehicles']
                             for person in row['crew']), 1692)
        self.assertEqual(sum(len(row['lastCrew']) for row in decoded['vehicles']), 282)
        self.assertTrue(all(row['lastCrewStatus'] == 'available' for row in decoded['vehicles']))
        self.assertEqual(len(decoded['sessionStats']['vehicles'][0]['battlesByDay']), 366)
        self.assertIn('missions', decoded)
        oversized = dict(snapshot, vehicles=copy.deepcopy(snapshot['vehicles']))
        oversized['vehicles'][0]['name'] = 'x' * mod.MAX_PAYLOAD_BYTES
        with self.assertRaises(ValueError):
            mod.encode_snapshot(oversized)


if __name__ == '__main__':
    unittest.main()
