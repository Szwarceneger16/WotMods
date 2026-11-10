"""Voice timing against native equipment snapshots and battle progression."""
import unittest

import test_mod as runtime


class AudioTimingTests(unittest.TestCase):
    def setUp(self):
        # Reuse the strict fixture without inheriting its existing test methods.
        self.game = runtime.Tests()
        self.game.setUp()
        self.mod = self.game.mod
        self.panel = self.game.panel
        self.world = self.game.world
        self.item = self.game.item
        self.cooldown = False
        self.remaining = 0.0
        self.quantity = 1
        self.item.isInCooldown = lambda: self.cooldown
        self.item.getTimeRemaining = lambda: self.remaining
        self.item.getQuantity = lambda: self.quantity
        self.item.isLocked = lambda: False

    def tearDown(self):
        self.game.tearDown()

    def refresh_at(self, when):
        self.world.clock = when
        self.mod._refresh(self.panel)

    def equipment_update(self, when, remaining, ready=False):
        self.world.clock = when
        self.cooldown = not ready
        self.remaining = remaining
        self.item.isAvailableToUse = ready
        self.item.can_use = ready
        self.panel.sessionProvider.shared.equipments.onEquipmentUpdated.emit(72, self.item)

    def played_times(self):
        return [when for when, unused_event in self.game.audio_plays]

    def test_advance_voice_does_not_start_pulse_or_repeat_at_zero(self):
        self.equipment_update(10.0, 2.0)
        self.refresh_at(11.49)
        self.assertEqual(self.played_times(), [])
        self.refresh_at(11.5)
        self.assertEqual(self.played_times(), [11.5])
        self.assertFalse(self.mod._overlay_active)
        self.assertEqual(self.game.gui.roots, [])
        stops = list(self.game.audio_stops)
        self.equipment_update(12.0, 0.0, ready=True)
        self.refresh_at(12.0)
        self.refresh_at(12.25)
        self.refresh_at(13.0)
        self.assertEqual(self.played_times(), [11.5])
        self.assertEqual(self.game.audio_stops, stops)
        self.assertTrue(self.mod._overlay_active)

    def test_repeat_interval_is_ten_seconds_and_pulse_keeps_its_phase(self):
        self.equipment_update(10.0, 2.0)
        self.refresh_at(11.5)
        self.equipment_update(12.0, 0.0, ready=True)
        self.refresh_at(12.0)
        self.refresh_at(13.0)
        pulse_start = self.mod._pulse_start
        self.refresh_at(15.5)
        self.refresh_at(19.5)
        self.refresh_at(21.49)
        self.assertEqual(self.played_times(), [11.5])
        self.refresh_at(21.5)
        self.assertEqual(self.played_times(), [11.5, 21.5])
        self.assertEqual(self.mod._pulse_start, pulse_start)
        self.world.clock = pulse_start + 11.0
        self.mod._animate()
        self.assertEqual(self.mod._frame, 10)

    def test_static_native_remaining_snapshot_does_not_slide_deadline(self):
        self.equipment_update(10.0, 3.0)
        for when in (10.25, 10.5, 11.0, 11.5, 12.0, 12.49):
            self.refresh_at(when)
        self.assertEqual(self.remaining, 3.0)
        self.assertEqual(self.played_times(), [])
        self.refresh_at(12.5)
        self.assertEqual(self.played_times(), [12.5])
        self.refresh_at(12.75)
        self.assertEqual(self.played_times(), [12.5])

    def test_new_server_update_can_extend_cooldown_deadline(self):
        self.equipment_update(10.0, 2.0)
        self.refresh_at(11.0)
        self.equipment_update(11.25, 3.0)
        self.refresh_at(11.5)
        self.refresh_at(13.74)
        self.assertEqual(self.played_times(), [])
        self.refresh_at(13.75)
        self.assertEqual(self.played_times(), [13.75])

    def test_invalid_remaining_or_empty_quantity_never_predicts_readiness(self):
        for remaining in (0.0, -1.0, float('inf'), float('nan'), '2', None, True, False):
            with self.subTest(remaining=remaining):
                self.equipment_update(10.0, remaining)
                self.refresh_at(11.5)
                self.assertEqual(self.played_times(), [])
        self.quantity = 0
        self.equipment_update(20.0, 2.0)
        self.refresh_at(21.5)
        self.assertEqual(self.played_times(), [])

    def test_advance_voice_retains_battle_safety_guards(self):
        guards = (
            ('wrong_perk', lambda: self.world.avatar.vehicle.perkEffects.update(equipment=['repairkit'])),
            ('destroyed', lambda: setattr(self.world.avatar.vehicle, 'health', 0)),
            ('hidden_hud', lambda: setattr(self.panel, 'native_visible', False)),
            ('spectator', lambda: setattr(self.world.avatar, 'isObserver', lambda: True)),
            ('prebattle', lambda: setattr(self.world.avatar.arena, 'period', 2)),
            ('native_warning', lambda: self.panel._equipmentsGlowCallbacks.update({3: object()})),
        )
        for name, apply_guard in guards:
            with self.subTest(guard=name):
                self.world.avatar.vehicle.health = 1000
                self.world.avatar.vehicle.perkEffects = {'equipment': ['medkitPremium']}
                self.world.avatar.isObserver = lambda: False
                self.world.avatar.arena.period = 3
                self.panel.native_visible = True
                self.panel._equipmentsGlowCallbacks.clear()
                self.mod._reset_audio()
                self.equipment_update(10.0, 2.0)
                apply_guard()
                self.refresh_at(11.5)
                self.assertEqual(self.played_times(), [])
                self.assertFalse(self.mod._overlay_active)

    def test_ready_at_battle_start_waits_one_second_from_battle_transition(self):
        self.world.avatar.arena.period = 2
        self.refresh_at(0.0)
        self.world.avatar.arena.period = 3
        self.refresh_at(30.0)
        self.refresh_at(30.99)
        self.assertEqual(self.played_times(), [])
        self.refresh_at(31.0)
        self.assertEqual(self.played_times(), [31.0])
        self.refresh_at(31.25)
        self.assertEqual(self.played_times(), [31.0])

    def test_server_battle_start_avoids_extra_delay_after_late_hud_load(self):
        self.world.serverTime = lambda: 1000.0 + self.world.clock
        self.world.avatar.arena.periodEndTime = 1900.0
        self.world.avatar.arena.periodLength = 900.0
        self.refresh_at(0.75)
        self.assertEqual(self.played_times(), [])
        self.refresh_at(1.0)
        self.assertEqual(self.played_times(), [1.0])

    def test_joining_an_existing_battle_announces_ready_without_extra_delay(self):
        self.world.serverTime = lambda: 1000.0 + self.world.clock
        self.world.avatar.arena.periodEndTime = 1900.0
        self.world.avatar.arena.periodLength = 900.0
        self.refresh_at(20.0)
        self.assertEqual(self.played_times(), [20.0])
        self.refresh_at(20.25)
        self.assertEqual(self.played_times(), [20.0])

    def test_anticipation_does_not_repeat_while_native_stage_is_still_cooldown(self):
        self.equipment_update(10.0, 2.0)
        self.refresh_at(11.5)
        self.refresh_at(12.0)
        self.refresh_at(21.5)
        self.assertEqual(self.played_times(), [11.5])
        self.assertFalse(self.mod._overlay_active)

    def test_native_update_subscription_is_removed_on_disposal(self):
        event = self.panel.sessionProvider.shared.equipments.onEquipmentUpdated
        self.assertEqual(event.handlers, [self.mod._on_equipment_updated])
        self.equipment_update(10.0, 2.0)
        self.refresh_at(11.5)
        self.assertEqual(self.played_times(), [11.5])
        self.game.emit_unregister()
        self.assertEqual(event.handlers, [])
        self.assertEqual(self.mod._cooldown_deadlines, {})
        event.emit(72, self.item)
        self.assertEqual(self.mod._cooldown_deadlines, {})

    def test_replacement_item_does_not_use_old_items_cooldown_snapshot(self):
        self.equipment_update(10.0, 2.0)
        replacement = runtime.FakeItem()
        replacement.isAvailableToUse = False
        replacement.can_use = False
        replacement.isInCooldown = lambda: True
        replacement.getQuantity = lambda: 1
        replacement.getTimeRemaining = lambda: 4.0
        controller = self.panel.sessionProvider.shared.equipments
        controller.item = replacement
        self.refresh_at(11.5)
        self.assertEqual(self.played_times(), [])
        self.world.clock = 12.0
        controller.onEquipmentUpdated.emit(72, replacement)
        self.refresh_at(15.49)
        self.assertEqual(self.played_times(), [])
        self.refresh_at(15.5)
        self.assertEqual(self.played_times(), [15.5])

    def test_late_attachment_does_not_guess_age_of_existing_cooldown(self):
        self.world.serverTime = lambda: 1000.0 + self.world.clock
        self.world.avatar.arena.periodEndTime = 1900.0
        self.world.avatar.arena.periodLength = 900.0
        self.cooldown = True
        self.remaining = 2.0
        self.item.isAvailableToUse = False
        self.item.can_use = False
        self.world.clock = 10.0
        self.mod._deactivate(self.panel)
        self.mod._activate(self.panel)
        self.refresh_at(11.5)
        self.refresh_at(12.0)
        self.assertEqual(self.played_times(), [])
        self.equipment_update(12.0, 0.0, ready=True)
        self.refresh_at(12.0)
        self.assertEqual(self.played_times(), [12.0])

    def test_native_ready_warning_holds_audio_until_warning_ends(self):
        self.panel._equipmentsGlowCallbacks[3] = object()
        self.refresh_at(0.0)
        self.refresh_at(1.0)
        self.refresh_at(5.0)
        self.assertEqual(self.played_times(), [])
        self.assertFalse(self.mod._overlay_active)
        self.panel._equipmentsGlowCallbacks.clear()
        self.refresh_at(5.25)
        self.assertEqual(self.played_times(), [5.25])
        self.refresh_at(15.24)
        self.assertEqual(self.played_times(), [5.25])
        self.refresh_at(15.25)
        self.assertEqual(self.played_times(), [5.25, 15.25])

    def test_native_ready_green_glow_preserves_advance_voice_and_repeat(self):
        self.equipment_update(10.0, 2.0)
        self.refresh_at(11.5)
        self.assertEqual(self.played_times(), [11.5])
        stops = list(self.game.audio_stops)
        # Native ConsumablesPanel adds the same callback entry for the green
        # becomeReady animation as it does for an injury/stun warning.
        self.item.becomeReady = True
        self.panel._canApplyingGlowEquipment = lambda item: False
        self.equipment_update(12.0, 0.0, ready=True)
        self.panel._equipmentsGlowCallbacks[3] = object()
        self.refresh_at(12.0)
        self.refresh_at(13.0)
        self.assertEqual(self.played_times(), [11.5])
        self.assertEqual(self.game.audio_stops, stops)
        self.assertFalse(self.mod._overlay_active)
        # Retain the native animation beyond its normal lifetime to prove that
        # it blocks the pulse independently of the ten-second voice interval.
        self.refresh_at(21.5)
        self.assertEqual(self.played_times(), [11.5, 21.5])
        self.assertEqual(self.game.audio_stops, stops)
        self.assertFalse(self.mod._overlay_active)
        self.panel._equipmentsGlowCallbacks.clear()
        self.refresh_at(21.75)
        self.refresh_at(22.75)
        self.assertTrue(self.mod._overlay_active)
        self.assertEqual(self.played_times(), [11.5, 21.5])
        self.assertEqual(self.game.audio_stops, stops)

    def test_native_injury_warning_still_wins_with_sticky_become_ready_flag(self):
        self.equipment_update(10.0, 2.0)
        self.refresh_at(11.5)
        self.item.becomeReady = True
        self.panel._canApplyingGlowEquipment = lambda item: False
        self.equipment_update(12.0, 0.0, ready=True)
        self.panel._equipmentsGlowCallbacks[3] = object()
        self.refresh_at(12.0)
        self.assertEqual(self.game.audio_stops, [])
        # A later native DEVICES/STUN event can show orange without another
        # equipment update, leaving becomeReady true on the same item.
        self.panel._canApplyingGlowEquipment = lambda item: True
        self.panel._equipmentsGlowCallbacks[3] = object()
        self.refresh_at(14.0)
        self.refresh_at(21.5)
        self.assertEqual(self.played_times(), [11.5])
        self.assertEqual(self.game.audio_stops, [self.mod.READY_VOICE_EVENT])
        self.assertFalse(self.mod._overlay_active)

    def test_missing_native_warning_checker_keeps_ready_glow_priority(self):
        self.item.becomeReady = True
        self.panel._equipmentsGlowCallbacks[3] = object()
        self.refresh_at(0.0)
        self.refresh_at(1.0)
        self.assertEqual(self.played_times(), [])
        self.assertFalse(self.mod._overlay_active)


if __name__ == '__main__':
    unittest.main()
