"""Crew-snapshot gating before native GUI, input and sound are activated."""
import sys
import types
import unittest
from unittest.mock import patch

import test_mod as runtime


class PerkGatingTests(unittest.TestCase):
    def setUp(self):
        self.game = runtime.Tests()
        self.game.TEST_CONTROLS = True
        self.game.setUp()
        self.mod = self.game.mod
        self.panel = self.game.panel
        self.vehicle = self.game.world.avatar.vehicle
        self.vehicle.crewCompactDescrs = (b'crew-with-perk',)
        self.vehicle.typeDescriptor = types.SimpleNamespace(type=types.SimpleNamespace(
            crewRoles=(('commander',),)))
        self.records = {b'crew-with-perk': [('commander_staySharp', 100)],
                        b'crew-without-perk': [('commander_tutor', 100)]}
        self.decoded = []
        self.failure = False
        def decode(compact, battleOnly=False):
            self.decoded.append((compact, battleOnly))
            if self.failure:
                raise ValueError('unsupported crew snapshot')
            skills = self.records[compact]
            return types.SimpleNamespace(skills=[], bonusSkills={},
                skillLevels=lambda active_roles: skills if 'commander' in active_roles else [])
        self.decode_patch = patch.object(sys.modules['items.tankmen'], 'TankmanDescr', decode)
        self.decode_patch.start()
        self.mod._clear_crew_perk_cache()

    def tearDown(self):
        self.decode_patch.stop()
        self.game.tearDown()

    def status(self):
        return self.mod._crew_perk_status(self.panel)

    def set_crew(self, compact):
        self.vehicle.crewCompactDescrs = (compact,)

    def restart_panel(self):
        self.game.emit_unregister()
        self.game.emit_register()

    def assert_dormant(self):
        # Native roots become inert immediately, then detach outside GUI input
        # traversal on a zero-delay engine callback. Do not advance state here.
        self.assertFalse(any(component.visible for component in self.game.gui.roots))
        while any(fn.__name__ == 'detach_control_roots' for unused_delay, fn in self.game.world.jobs.values()):
            self.game.world.fire('detach_control_roots')
        self.assertEqual(self.game.gui.roots, [])
        self.assertEqual(self.mod._controls, [])
        self.assertIsNone(self.mod._overlay)
        self.assertIsNone(self.mod._voice_player)
        self.assertIsNone(self.mod._pulse_callback)
        self.assertIsNone(self.mod._controls_poll_callback)
        self.assertEqual([(delay, fn.__name__) for delay, fn in self.game.world.jobs.values()],
                         [(self.mod.DORMANT_TICK, '_check_state')])
        self.assertEqual(self.game.key_event.handlers, [])
        self.assertEqual(self.panel.sessionProvider.shared.equipments.onEquipmentUpdated.handlers, [])

    def test_learned_skill_is_independent_of_temporary_effect_state(self):
        self.vehicle.perkEffects = {'equipment': []}
        self.assertEqual(self.status(), 'present')
        self.vehicle.perkEffects = None
        self.assertEqual(self.status(), 'present')
        self.assertEqual(self.decoded, [(b'crew-with-perk', True)])

    def test_absent_skill_does_not_count_unrelated_commander_skills(self):
        self.set_crew(b'crew-without-perk')
        self.assertEqual(self.status(), 'absent')
        self.assertEqual(self.status(), 'absent')
        self.assertEqual(self.decoded, [(b'crew-without-perk', True)])

    def test_zero_level_is_absent_and_positive_level_is_present(self):
        self.records[b'zero-level'] = [('commander_staySharp', 0)]
        self.records[b'partial-level'] = [('commander_staySharp', 1)]
        self.set_crew(b'zero-level')
        self.assertEqual(self.status(), 'absent')
        self.set_crew(b'partial-level')
        self.assertEqual(self.status(), 'present')

    def test_active_slot_roles_are_passed_to_native_skill_levels(self):
        self.assertEqual(self.status(), 'present')
        self.vehicle.typeDescriptor.type.crewRoles = (('loader',),)
        self.assertEqual(self.status(), 'absent')
        self.assertEqual(len(self.decoded), 2)

    def test_native_bonus_skill_results_are_used(self):
        # Native skillLevels includes relevant bonus-role skills even when the
        # descriptor's major .skills list is empty.
        self.vehicle.typeDescriptor.type.crewRoles = (('loader', 'commander'),)
        self.assertEqual(self.status(), 'present')

    def test_changed_crew_and_replacement_entity_invalidate_cached_presence(self):
        self.assertEqual(self.status(), 'present')
        self.set_crew(b'crew-without-perk')
        self.assertEqual(self.status(), 'absent')
        replacement = types.SimpleNamespace(**vars(self.vehicle))
        self.game.world.avatar.vehicle = replacement
        self.assertEqual(self.status(), 'absent')
        self.assertEqual(len(self.decoded), 3)

    def test_missing_or_incomplete_crew_contract_stays_unknown(self):
        for crew, roles in ((None, (('commander',),)),
                            ((), ()),
                            ((b'crew-with-perk',), None),
                            ((b'crew-with-perk',), ()),
                            ((b'',), (('commander',),))):
            with self.subTest(crew=crew, roles=roles):
                self.vehicle.crewCompactDescrs = crew
                self.vehicle.typeDescriptor.type.crewRoles = roles
                self.assertEqual(self.status(), 'unknown')
        self.assertEqual(self.decoded, [])

    def test_unsupported_snapshot_fails_closed_and_can_retry(self):
        self.failure = True
        self.assertEqual(self.status(), 'unknown')
        self.failure = False
        self.assertEqual(self.status(), 'present')
        self.assertEqual(len(self.decoded), 2)

    def test_without_perk_no_gui_sound_or_input_subscriptions_are_created(self):
        self.set_crew(b'crew-without-perk')
        self.restart_panel()
        self.game.state(12)
        self.assert_dormant()
        self.assertEqual(self.game.audio_plays, [])

    def test_unknown_crew_remains_dormant_until_native_snapshot_arrives(self):
        self.vehicle.crewCompactDescrs = ()
        self.restart_panel()
        self.game.state(4)
        self.assert_dormant()
        self.set_crew(b'crew-with-perk')
        self.game.state(8)
        self.assertEqual(len(self.mod._controls), 2)
        self.assertTrue(self.mod._overlay_active)
        self.assertEqual(self.game.key_event.handlers, [self.mod._on_key_down])
        self.assertEqual(len(self.game.audio_plays), 1)

    def test_crew_without_perk_replaces_active_crew_and_removes_resources(self):
        self.restart_panel()
        self.game.state(8)
        self.assertTrue(self.mod._overlay_active)
        self.assertEqual(len(self.mod._controls), 2)
        before = len(self.game.audio_plays)
        self.set_crew(b'crew-without-perk')
        self.game.state()
        self.assert_dormant()
        self.game.state(48)
        self.assertEqual(len(self.game.audio_plays), before)

    def test_learned_but_temporarily_inactive_perk_keeps_controls_only(self):
        self.vehicle.perkEffects = {'equipment': []}
        self.restart_panel()
        self.game.state(8)
        self.assertEqual(len(self.mod._controls), 2)
        self.assertFalse(self.mod._overlay_active)
        self.assertEqual(self.game.audio_plays, [])
        self.assertEqual(self.game.key_event.handlers, [self.mod._on_key_down])


if __name__ == '__main__':
    unittest.main()
