"""Native battle-switch regressions using the normal component lifecycle."""
import types
import unittest

import test_mod as runtime


class HudControlTests(unittest.TestCase):
    def setUp(self):
        self.game = runtime.Tests()
        self.game.TEST_CONTROLS = True
        self.game.setUp()
        self.mod = self.game.mod
        self.panel = self.game.panel
        self.ctrl = False
        self.game.world.isKeyDown = lambda key: self.ctrl
        import Keys
        Keys.KEY_LEFTMOUSE = 1
        Keys.KEY_LCONTROL = 29
        Keys.KEY_RCONTROL = 157

    def tearDown(self):
        self.game.tearDown()

    def sync(self):
        self.mod._sync_controls(self.panel)

    def click(self, index, down):
        event = types.SimpleNamespace(key=1, isKeyDown=lambda: down)
        component, unused_owner, unused_mount, handler = self.mod._controls[index]
        return handler.handleMouseButtonEvent(component, event)

    def test_normal_state_tick_shows_both_icons_above_medkit(self):
        self.game.state()
        self.assertEqual(len(self.mod._controls), 2)
        geometry, unused_origin = self.mod._geometry(self.panel, 3)
        for component, unused_owner, unused_mount, unused_handler in self.mod._controls:
            self.assertTrue(component.visible)
            self.assertFalse(component.focus)
            self.assertTrue(component.mouseButtonFocus)
            self.assertGreater(component.position[1], geometry[1])
            self.assertEqual(component.size, (24.0, 24.0))

    def test_switches_remain_available_without_readiness_or_with_mod_disabled(self):
        self.game.item.isAvailableToUse = False
        self.game.world.avatar.vehicle.perkEffects = {'equipment': []}
        self.mod._reminder_enabled = False
        self.game.state()
        self.assertTrue(all(entry[0].visible for entry in self.mod._controls))
        self.assertTrue(self.mod._controls[0][0].textureName.endswith('power_off.dds'))

    def test_ctrl_click_toggles_each_setting_once_and_consumes_mouse(self):
        self.sync()
        self.assertFalse(self.click(0, True))
        self.assertTrue(self.mod._reminder_enabled)
        self.ctrl = True
        self.assertTrue(self.click(0, True))
        self.assertTrue(self.click(0, False))
        self.assertFalse(self.mod._reminder_enabled)
        self.assertTrue(self.mod._controls[0][3].handleMouseClickEvent(self.mod._controls[0][0]))
        self.assertFalse(self.mod._reminder_enabled)
        self.assertTrue(self.click(1, True))
        self.assertTrue(self.click(1, False))
        self.assertFalse(self.mod._voice_enabled)
        self.assertTrue(self.mod._controls[1][0].textureName.endswith('voice_off.dds'))

    def test_regular_sniper_hides_controls_and_artillery_keeps_them(self):
        self.sync()
        self.panel.camera_mode = 'sniper'
        self.sync()
        self.assertFalse(any(entry[0].visible for entry in self.mod._controls))
        self.assertFalse(any(entry[0].mouseButtonFocus for entry in self.mod._controls))
        self.panel.camera_mode = 'strategic'
        self.sync()
        self.assertTrue(all(entry[0].visible for entry in self.mod._controls))
        self.panel.camera_mode = 'sniper'
        self.game.world.avatar.vehicle.typeDescriptor = types.SimpleNamespace(
            type=types.SimpleNamespace(tags={'SPG'}))
        self.sync()
        self.assertTrue(all(entry[0].visible for entry in self.mod._controls))

    def test_hidden_hud_and_destroyed_vehicle_cannot_accept_clicks(self):
        self.sync()
        self.ctrl = True
        self.assertTrue(self.click(0, True))
        self.panel.native_visible = False
        self.sync()
        self.assertFalse(self.click(0, False))
        self.assertTrue(self.mod._reminder_enabled)
        self.panel.native_visible = True
        self.game.world.avatar.vehicle.health = 0
        self.sync()
        self.assertFalse(any(entry[0].visible for entry in self.mod._controls))

    def test_disposal_deletes_native_components_and_rejects_stale_callbacks(self):
        self.sync()
        component, unused_owner, unused_mount, handler = self.mod._controls[0]
        self.ctrl = True
        handler.pressed = True
        self.game.emit_unregister()
        self.assertEqual(self.mod._controls, [])
        self.assertEqual(self.game.gui.roots, [])
        self.assertIsNone(component.script)
        self.assertFalse(handler.handleMouseButtonEvent(component,
            types.SimpleNamespace(key=1, isKeyDown=lambda: False)))

    def test_partial_attachment_failure_cleans_up_controls(self):
        self.game.gui.fail_add = True
        self.sync()
        self.assertTrue(self.mod._controls_disabled)
        self.assertEqual(self.mod._controls, [])
        self.assertEqual(self.game.gui.roots, [])

    def test_native_battle_parent_owns_and_disposes_both_buttons(self):
        class HUD:
            def __init__(self): self.children = {}
            def addChild(self, child, name): self.children[name] = child
            def delChild(self, child):
                for name, component in list(self.children.items()):
                    if component is child:
                        del self.children[name]
                        return
                raise AssertionError('not attached')
        hud = HUD()
        self.panel.app = types.SimpleNamespace(component=hud)
        self.game.state()
        self.assertEqual(set(hud.children), {'staysharp_control_power', 'staysharp_control_voice'})
        self.assertEqual(self.game.gui.roots, [])
        self.game.emit_unregister()
        self.assertEqual(hud.children, {})


if __name__ == '__main__':
    unittest.main()
