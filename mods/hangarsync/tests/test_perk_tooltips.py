# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import contextlib
import copy
import json
import os
import sys
import types
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'source'))
import hangar_crew as crew
from test_hangar_crew import Obj, native_modules, skill, tankman


# Native ACTIVE_SKILLS identifiers, pinned to client 2.4.1.1.
ACTIVE = ('brotherhood repair camouflage commander_eagleEye commander_emergency commander_tutor '
          'commander_coordination commander_enemyShotPredictor commander_practical commander_sixthSense '
          'commander_holdLine commander_staySharp gunner_smoothTurret gunner_sniper gunner_rancorous '
          'gunner_focus gunner_quickAiming gunner_armorer gunner_pointBlast gunner_loneWolf driver_virtuoso '
          'driver_smoothDriving driver_badRoadsKing driver_reliablePlacement driver_rammingMaster '
          'driver_motorExpert driver_suspensionRepair driver_bulletproof radioman_finder radioman_sideBySide '
          'radioman_interference radioman_signalInterception radioman_expert fireFighting '
          'radioman_battleTempered radioman_threatSearch loader_desperado loader_pedant loader_intuition '
          'loader_perfectCharge loader_melee loader_ammunitionImprove loader_secondChance loader_magMastery').split()


@contextlib.contextmanager
def tooltip_native(unavailable_xp=False):
    with native_modules() as calls:
        names = ('helpers', 'gui.shared.tooltips.advanced', 'items.components.skills_constants',
                 'gui.impl.lobby.crew.crew_helpers.model_setters',
                 'gui.impl.lobby.crew.tooltips.crew_perks_tooltip')
        missing = object()
        xp_calls = []

        def localize(key):
            if key.startswith('#tooltips:perkType/name/'):
                return 'Native category ' + key.rsplit('/', 1)[-1]
            if '/discountLabel/' in key:
                return 'Native reduced XP note for ' + key.rsplit('/', 1)[-1] + ' zero perk.'
            if key == '#crew:matrix/skillTooltip/zero/text':
                return 'Native zero perks require no Crew XP.'
            return key

        def progression(vm, tman, index, is_zero):
            xp_calls.append((index, is_zero))
            if unavailable_xp:
                raise RuntimeError('PRIVATE_NATIVE_XP_FAILURE')
            vm.setCurrentXpValue(1007206)
            vm.setDiscountValue(1680480)
            vm.setTotalXpValue(3360960)
            vm.setSkillProgress(89)
            vm.setZeroSkillsCount(1)
            vm.setIsLocked(False)
            vm.setIsMaxSkillLevel(False)

        def canonical(name, role):
            category = 'commanderSpecial' if name == 'commander_sixthSense' else 'common' if name in ACTIVE[:3] else 'main'
            return skill(name, 0, typeName=category,
                         altDescription='Native mechanic.\n\nNative highlighted <b>condition</b>.',
                         altInfo='Native help &amp; details.\nSecond paragraph.')

        class NativeContext(object):
            @staticmethod
            def _isGroupSkill(context):
                return True

            @staticmethod
            def _isGroupSkillHasLowEff(context):
                return False

            @staticmethod
            def _isGroupSkillHasUntrained(context):
                return False

            @staticmethod
            def _getBoosterType(context):
                return 'extra'

        modules = {
            'helpers': Obj(i18n=Obj(makeString=localize)),
            'gui.shared.tooltips.advanced': Obj(SKILL_MOVIES={name: 'nativeMovie' for name in ACTIVE}),
            'items.components.skills_constants': Obj(ACTIVE_SKILLS=frozenset(ACTIVE)),
            'gui.impl.lobby.crew.crew_helpers.model_setters': Obj(setSkillProgressionModel=progression),
            'gui.impl.lobby.crew.tooltips.crew_perks_tooltip': Obj(CrewPerksTooltip=NativeContext),
        }
        for name, values in list(modules.items()):
            module = types.ModuleType(str(name))
            module.__dict__.update(values.__dict__)
            modules[name] = module
            parts = name.split('.')
            for size in range(1, len(parts)):
                parent = '.'.join(parts[:size])
                if parent not in modules and parent not in sys.modules:
                    package = types.ModuleType(str(parent))
                    package.__path__ = []
                    modules[parent] = package
        old = {name: sys.modules.get(name, missing) for name in modules}
        sys.modules.update(modules)
        native_skill_module = sys.modules['gui.shared.gui_items.tankman_skill']
        native_skill_module.getTankmanSkill = canonical
        formatters = sys.modules['gui.impl.lobby.crew.crew_helpers.skill_helpers']
        previous_params = formatters.getSkillParams

        def colored_params(*args, **kwargs):
            params = previous_params(*args, **kwargs)
            params['keyArgs']['effect']['color'] = 'greenBright'
            return params

        def native_description(value, arguments):
            for name, data in arguments.items():
                value = value.replace('%(' + name + ')s', '{' + data['color'] + '_Start}'
                                      + data['value'] + '{' + data['color'] + '_End}')
            return value

        formatters.getSkillParams = colored_params
        formatters.formatDescription = native_description
        try:
            yield calls, xp_calls
        finally:
            for name, value in old.items():
                if value is missing:
                    sys.modules.pop(name, None)
                else:
                    sys.modules[name] = value


def learning_tankman():
    person = tankman([skill('repair', 89)])
    # Descriptor positions are native; GUI skills filter the reserved any slot.
    person.descriptor = Obj(skills=['any', 'repair'])
    person.freeSkillsCount = 1
    return person


class PerkTooltipTests(unittest.TestCase):
    def test_rich_text_retains_native_tones_and_decodes_spacing_entities(self):
        value = ('Effect {greenBright_Start}12.5&zwnbsp;&#37;{greenBright_End}&nbsp;now.'
                 '\n\n<b>Mechanic</b><br>More &amp; details.')
        paragraphs = crew.rich_text(value)
        self.assertEqual(len(paragraphs), 3)
        self.assertIn({'text': '12.5%', 'tone': 'positive'}, paragraphs[0]['spans'])
        plain = '\n'.join(''.join(span['text'] for span in row['spans']) for row in paragraphs)
        self.assertEqual(plain, 'Effect 12.5%\xa0now.\nMechanic\nMore & details.')
        self.assertNotIn('&zwnbsp;', crew._text(value))
        self.assertNotIn('\ufeff', plain)

    def test_unsafe_markup_and_unknown_tones_never_escape_the_text_contract(self):
        result = crew.rich_text('<script>PRIVATE_SCRIPT</script><style>PRIVATE_STYLE</style>'
                                '<native-tone value="invalid">Safe</native-tone><img src="secret">'
                                '<a href="secret"> text</a>')
        self.assertEqual(result, [{'spans': [{'text': 'Safe text', 'tone': 'normal'}]}])
        self.assertNotIn('PRIVATE', json.dumps(result))
        self.assertEqual(crew.rich_text('Unresolved %(factor)s'), [])
        bounded = crew.rich_text(('word ' * 500 + '<br>') * 50)
        self.assertLessEqual(len(bounded), 24)
        self.assertLessEqual(sum(len(span['text']) for row in bounded for span in row['spans']), 8192)
        self.assertTrue(all(0 < len(span['text']) <= 600 for row in bounded for span in row['spans']))

    def test_every_native_active_perk_has_shared_metadata_without_member_ids(self):
        with tooltip_native():
            catalog = {}
            crew.prime_crew_catalog(catalog)
        self.assertEqual(len(ACTIVE), 44)
        self.assertEqual(set(catalog), set(ACTIVE))
        for identifier, row in catalog.items():
            self.assertEqual(row['tooltip']['mode'], 'maximum')
            self.assertEqual(row['tooltip']['mediaKey'], 'skill:' + identifier)
            self.assertTrue(row['tooltip']['category'])
            self.assertTrue(row['tooltip']['details'])
            self.assertTrue(row['tooltip']['short'])
        self.assertEqual(catalog['commander_sixthSense']['tooltip']['categoryKey'], 'commanderSpecial')
        self.assertNotIn('PRIVATE', json.dumps(catalog))

    def test_exact_native_xp_is_not_a_percentage_interpolation(self):
        person = learning_tankman()
        with tooltip_native() as (_, xp_calls):
            row = crew.collect_crew_skills(person, Obj(), {})['skills'][0]
        tooltip = row['tooltip']
        self.assertEqual(row['level'], 89)
        self.assertEqual(tooltip['mode'], 'current')
        self.assertEqual(tooltip['xp'], {'current': 1007206, 'required': 1680480,
                         'fullRequired': 3360960, 'progress': 89, 'zeroSkillsCount': 1,
                         'isLocked': False, 'isMaxSkillLevel': False})
        self.assertNotEqual(tooltip['xp']['current'], int(tooltip['xp']['required'] * 0.89))
        self.assertEqual(xp_calls, [(1, False)])
        self.assertTrue(tooltip['zeroNote'])
        self.assertIn({'text': '12.5%', 'tone': 'positive'}, tooltip['short'][0]['spans'])
        self.assertEqual(tooltip['context']['boosterType'], 'extra')

    def test_missing_native_progression_does_not_invent_xp_and_bonus_has_no_paid_xp(self):
        with tooltip_native(unavailable_xp=True):
            row = crew.collect_crew_skills(learning_tankman(), Obj(), {})['skills'][0]
        self.assertNotIn('xp', row.get('tooltip', {}))
        person = learning_tankman()
        person.skills = []
        person.bonusSkills = {'gunner': [skill('repair', 89)]}
        with tooltip_native() as (_, calls):
            row = crew.collect_crew_skills(person, Obj(), {})['skills'][0]
        self.assertTrue(row['isBonus'])
        self.assertNotIn('xp', row.get('tooltip', {}))
        self.assertEqual(calls, [])

    def test_remembered_context_keeps_current_profile_xp_without_origin_effects(self):
        with tooltip_native() as (calls, _):
            row = crew.collect_crew_skills(learning_tankman(), None, {})['skills'][0]
        self.assertEqual(row['tooltip']['xp']['current'], 1007206)
        self.assertNotIn('short', row['tooltip'])
        self.assertNotIn('description', row)
        self.assertTrue(all(tankman is None for tankman, _, _ in calls))

    def test_zero_perk_note_uses_native_text_without_paid_progression(self):
        person = tankman([skill('brotherhood', 100, isZero=True)])
        with tooltip_native() as (_, calls):
            row = crew.collect_crew_skills(person, Obj(), {})['skills'][0]
        self.assertTrue(row['isZero'])
        self.assertTrue(row['tooltip']['zeroNote'])
        self.assertNotIn('xp', row['tooltip'])
        self.assertEqual(calls, [])

    def test_lossless_current_short_references_are_scoped_by_native_skill(self):
        short = [{'spans': [{'text': 'Native actual 12.5%', 'tone': 'positive'}]}]
        snapshot = {'vehicles': [{'crew': [{'skills': [
            {'id': 'repair', 'level': 89, 'description': 'Legacy actual',
             'tooltip': {'mode': 'current', 'short': copy.deepcopy(short)}},
            {'id': 'repair', 'level': 89, 'tooltip': {'mode': 'current', 'short': copy.deepcopy(short)}},
            {'id': 'camouflage', 'level': 89, 'tooltip': {'mode': 'current', 'short': copy.deepcopy(short)}},
        ]}]}], 'crewSkillCatalog': [{'id': 'repair', 'name': 'Repair', 'tooltip': {'mode': 'maximum'}}]}
        original = copy.deepcopy(snapshot)
        compact = crew.compact_tooltip_shorts(snapshot)
        self.assertEqual(snapshot, original)
        rows = compact['vehicles'][0]['crew'][0]['skills']
        self.assertEqual(rows[0]['description'], 'Legacy actual')
        key = rows[0]['tooltip']['shortKey']
        self.assertEqual(len(key), 16)
        self.assertEqual(rows[1]['tooltip']['shortKey'], key)
        self.assertNotIn('short', rows[0]['tooltip'])
        self.assertEqual(compact['crewSkillCatalog'][0]['tooltip']['shortVariants'][key], short)
        self.assertEqual(rows[2]['tooltip']['short'], short)
        self.assertEqual(crew.compact_tooltip_shorts(compact), compact)

    def test_hash_collisions_and_variant_limit_preserve_inline_actual_text(self):
        def build(groups):
            rows = []
            for index in range(groups):
                for _ in range(2):
                    rows.append({'crew': [{'skills': [{'id': 'repair', 'level': 89, 'tooltip': {
                        'mode': 'current', 'short': [{'spans': [{'text': 'Effect ' + str(index), 'tone': 'positive'}]}]}}]}]})
            return {'vehicles': rows, 'crewSkillCatalog': [{'id': 'repair', 'name': 'Repair'}]}

        original_hash = crew.hashlib.sha256
        crew.hashlib.sha256 = lambda _: Obj(hexdigest=lambda: 'a' * 64)
        try:
            source = build(2)
            result = crew.compact_tooltip_shorts(source)
        finally:
            crew.hashlib.sha256 = original_hash
        variants = result['crewSkillCatalog'][0]['tooltip']['shortVariants']
        self.assertEqual(len(variants), 1)
        inline = 0
        for before, after in zip(source['vehicles'], result['vehicles']):
            current = after['crew'][0]['skills'][0]['tooltip']
            expected = before['crew'][0]['skills'][0]['tooltip']['short']
            if 'shortKey' in current:
                self.assertEqual(variants[current['shortKey']], expected)
            else:
                inline += 1
                self.assertEqual(current['short'], expected)
        self.assertEqual(inline, 2)
        limited = crew.compact_tooltip_shorts(build(65))
        self.assertEqual(len(limited['crewSkillCatalog'][0]['tooltip']['shortVariants']), 64)
        self.assertEqual(sum('short' in row['crew'][0]['skills'][0]['tooltip']
                             for row in limited['vehicles']), 2)


if __name__ == '__main__':
    unittest.main()
