# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import contextlib
import json
import os
import sys
import types
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'source'))
import hangar_crew as crew


class Obj(object):
    def __init__(self, **values):
        self.__dict__.update(values)


def skill(name='repair', level=37, **values):
    attributes = dict(name=name, userName='Native ' + name, level=level,
                      skillRole='commander', roleType='common', isZero=False,
                      isSkillActive=1, isRelevant=True, isEnable=True,
                      extensionLessIconName=name, description='Native purpose.',
                      maxLvlDescription='Maximum effect %(effect)s.',
                      currentLvlDescription='Current effect %(effect)s.')
    attributes.update(values)
    return Obj(**attributes)


def tankman(skills=None, bonus=None):
    skills = [skill()] if skills is None else skills
    return Obj(skills=skills, skillsCount=len(skills), role='commander',
               roles=lambda: ('commander', 'gunner'), bonusSkills=bonus or {},
               newSkillsCount=(1, 55), newFreeSkillsCount=1,
               bonusSlotsLevels=[100, 45, None], newBonusSkillsCountByRole={'gunner': 1},
               getPossibleSkillsByRole=lambda: {'common': [skill(), skill('unlearned', 0)]},
               invID='PRIVATE_CREW_ID', vehicleInvID='PRIVATE_VEHICLE_ID')


@contextlib.contextmanager
def native_modules(broken=False):
    calls = []

    def params(tman, vehicle, booster, current_skill, name, level, fake, *args):
        calls.append((tman, name, level))
        if broken:
            raise RuntimeError('PRIVATE_NATIVE_ERROR')
        return {'keyArgs': {'effect': {'value': '20%' if tman is None else '12.5%', 'color': 'bonus'}},
                'kpiArgs': [('Native value', 'Native condition', 'positive')]}

    def description(value, arguments):
        return value.replace('%(effect)s', '{bonus_Start}' + arguments['effect']['value'] + '{bonus_End}')

    values = {
        'constants': Obj(NEW_PERK_SYSTEM=Obj(MAX_MAJOR_PERKS=6, MAX_BONUS_SKILLS_PER_ROLE=3)),
        'gui.shared.gui_items.tankman_skill': Obj(getTankmanSkill=lambda name, role: skill(name, 0)),
        'gui.shared.gui_items.Tankman': Obj(getBattleBooster=lambda *args: Obj(private='PRIVATE_BOOSTER'),
                                            crewMemberRealSkillLevel=lambda *args, **kwargs: 137),
        'gui.impl.lobby.crew.crew_helpers.skill_helpers': Obj(
            getSkillParams=params, getSkillDescription=lambda t, s, *args: s.currentLvlDescription,
            formatDescription=description),
    }
    for name in list(values):
        value = values[name]
        module = types.ModuleType(str(name))
        module.__dict__.update(value.__dict__)
        values[name] = module
        parts = name.split('.')
        for size in range(1, len(parts)):
            parent = '.'.join(parts[:size])
            if parent not in values and parent not in sys.modules:
                package = types.ModuleType(str(parent))
                package.__path__ = []
                values[parent] = package
    missing = object()
    old = {name: sys.modules.get(name, missing) for name in values}
    try:
        sys.modules.update(values)
        yield calls
    finally:
        for name, value in old.items():
            if value is missing:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = value


class CrewSkillTests(unittest.TestCase):
    def test_native_training_level_and_resolved_effect_use_separate_sources(self):
        catalog = {}
        with native_modules() as calls:
            result = crew.collect_crew_skills(tankman(), Obj(), catalog)
        row = result['skills'][0]
        self.assertEqual(row['level'], 37)
        self.assertEqual(row['description'], 'Current effect 12.5%.')
        self.assertTrue(any(tman is not None and level == 137 for tman, name, level in calls))
        self.assertEqual(catalog['repair']['maxDescription'], 'Maximum effect 20%.')
        self.assertNotIn('maxDescription', row)
        self.assertNotIn('PRIVATE_', json.dumps({'crew': result, 'catalog': catalog}))

    def test_zero_bonus_special_icon_and_exact_native_slot_counts(self):
        tman = tankman([skill('brotherhood', 100, isZero=True, extensionLessIconName='sabaton_brotherhood')],
                       {'gunner': [skill('gunner_skill', 84, isZero=0, isSkillActive=2), None]})
        with native_modules():
            result = crew.collect_crew_skills(tman, Obj(), {})
        major, bonus = result['skills']
        self.assertEqual(major['iconKey'], 'skill:sabaton_brotherhood')
        self.assertTrue(major['isZero'])
        self.assertTrue(major['isActive'])
        self.assertFalse(major['isBonus'])
        self.assertTrue(bonus['isBonus'])
        self.assertEqual(bonus['level'], 84)
        self.assertFalse(bonus['isZero'])
        self.assertEqual(result['skillSlots'], 6)
        self.assertEqual(result['remainingSkillSlots'], 5)
        self.assertEqual(result['freeSkillSlots'], 2)
        self.assertEqual(result['roles'], ['commander', 'gunner'])
        self.assertEqual(result['bonusSkillSlots'], [{'role': 'gunner', 'capacity': 3,
                          'levels': [100, 45, None], 'available': 1, 'remaining': 2}])

    def test_shared_catalog_is_deduplicated_and_unlearned_rows_stay_out_of_crew(self):
        catalog = {}
        with native_modules() as calls:
            first = crew.collect_crew_skills(tankman(), Obj(), catalog)
            before = len([call for call in calls if call[0] is None])
            second = crew.collect_crew_skills(tankman(), Obj(), catalog)
        self.assertEqual(set(catalog), {'repair', 'unlearned'})
        self.assertEqual([row['id'] for row in first['skills']], ['repair'])
        self.assertEqual(first, second)
        self.assertEqual(len([call for call in calls if call[0] is None]), before)

    def test_invalid_or_missing_percent_does_not_become_zero_or_hundred(self):
        for level in (None, True, -1, 101, float('nan'), '100'):
            with native_modules():
                result = crew.collect_crew_skills(tankman([skill(level=level)]), Obj(), {})
            self.assertNotIn('skills', result)
        with native_modules():
            result = crew.collect_crew_skills(tankman([skill(level=0)]), Obj(), {})
        self.assertEqual(result['skills'][0]['level'], 0)

    def test_unavailable_formatter_keeps_native_identity_and_level(self):
        with native_modules(broken=True):
            catalog = {}
            result = crew.collect_crew_skills(tankman(), Obj(), catalog)
        self.assertEqual(result['skills'][0]['level'], 37)
        self.assertNotIn('description', result['skills'][0])
        self.assertNotIn('maxDescription', catalog['repair'])
        self.assertNotIn('PRIVATE_', json.dumps(result))

    @unittest.skipUnless(sys.version_info[0] >= 3, 'Main harness uses Python 3')
    def test_47_vehicles_full_crews_keep_current_levels_and_fit_sync_limit(self):
        from test_hangar_sync import mod, Vehicle
        vehicles = []
        for identifier in range(1, 48):
            vehicle = Vehicle()
            vehicle.intCD = identifier
            vehicle.crew = [(index, tankman([skill('skill' + str(i), 100 if i < 5 else 37)
                                            for i in range(6)])) for index in range(6)]
            for slot, member in vehicle.crew:
                member.fullUserName = 'Native crew member'
                member.roleUserName = 'Commander'
                member.roleLevel = 100
                member.invID = 900000000000 + identifier * 10 + slot
            vehicle.lastCrew = [member.invID for _, member in vehicle.crew]
            vehicles.append(vehicle)
        with native_modules():
            snapshot = mod.make_snapshot('Fixture garage', vehicles, 'EU', True)
            mod._add_remembered_crew(snapshot, vehicles, Obj(inventory=Obj(isSynced=lambda: True)))
            payload, _ = mod.encode_snapshot(snapshot)
        decoded = json.loads(payload)
        self.assertEqual(len(decoded['vehicles']), 47)
        self.assertEqual(sum(len(member['skills']) for vehicle in decoded['vehicles']
                             for member in vehicle['crew']), 47 * 6 * 6)
        self.assertLess(len(payload), mod.MAX_PAYLOAD_BYTES)
        self.assertEqual(len(decoded['crewSkillCatalog']), 8)
        self.assertTrue(all(vehicle['lastCrewStatus'] == 'same_as_current' and
                            'lastCrew' not in vehicle for vehicle in decoded['vehicles']))
        self.assertNotIn('PRIVATE_', payload.decode())


if __name__ == '__main__':
    unittest.main()
