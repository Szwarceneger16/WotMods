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
        self.cursor = types.SimpleNamespace(active=True, visible=True)
        self.game.gui.mcursor = lambda: self.cursor
        import Keys
        Keys.KEY_LEFTMOUSE = 1
        Keys.KEY_LCONTROL = 29
        Keys.KEY_RCONTROL = 157

    def tearDown(self):
        self.game.tearDown()

    def sync(self):
        self.mod._sync_controls(self.panel)

    def click(self, index, down):
        component, unused_owner, unused_mount, handler = self.mod._controls[index]
        event = types.SimpleNamespace(key=1, isKeyDown=lambda: down,
            cursorPosition=component.position[:2])
        return handler.handleMouseButtonEvent(component, event)

    def test_normal_state_tick_shows_both_icons_above_medkit(self):
        self.game.state()
        self.assertEqual(len(self.mod._controls), 2)
        geometry, unused_origin = self.mod._geometry(self.panel, 3)
        for component, unused_owner, unused_mount, unused_handler in self.mod._controls:
            self.assertTrue(component.visible)
            self.assertTrue(component.focus)
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

    def test_plain_click_toggles_each_setting_once_and_consumes_mouse(self):
        self.sync()
        self.cursor.active = False
        self.assertFalse(self.click(0, True))
        self.assertTrue(self.mod._reminder_enabled)
        self.cursor.active = True
        self.assertTrue(self.click(0, True))
        self.assertTrue(self.click(0, False))
        self.assertFalse(self.mod._reminder_enabled)
        self.assertFalse(self.mod._controls[0][3].handleMouseClickEvent(self.mod._controls[0][0]))
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
            types.SimpleNamespace(key=1, isKeyDown=lambda: False,
                cursorPosition=component.position[:2])))

    def test_partial_attachment_failure_cleans_up_controls(self):
        self.game.gui.fail_add = True
        self.sync()
        self.assertTrue(self.mod._controls_disabled)
        self.assertEqual(self.mod._controls, [])
        self.assertEqual(self.game.gui.roots, [])

    def test_input_roots_are_independent_of_native_battle_parent(self):
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
        self.assertEqual(hud.children, {})
        self.assertEqual(self.game.gui.roots,
            [entry[0] for entry in self.mod._controls])
        self.game.emit_unregister()
        self.assertEqual(hud.children, {})
        self.assertEqual(self.game.gui.roots, [])

    def install_native_router(self, native_hit=True):
        """Mirror BigWorld: native hit first, then sorted focused GUI roots.

        The real full-screen Flash component consumes remaining mouse buttons.
        Its wrapper enables focus, not mouseButtonFocus. A disabled native_hit
        models the client regression where the rendered quad never receives its
        mouseButtonFocus callback; the root key path must still work.
        """
        self.flash_events = []
        flash = types.SimpleNamespace(position=(0, 0, 0.5), visible=True,
            focus=True, mouseButtonFocus=False,
            script=types.SimpleNamespace(handleKeyEvent=lambda event:
                self.flash_events.append(event) or True))
        self.game.gui.roots.append(flash)
        add_root = self.game.gui.addRoot
        def sorted_add(component):
            add_root(component)
            # addRoot sorts immediately; later position writes do not re-sort.
            self.game.gui.roots.sort(key=lambda node: node.position[2], reverse=True)
        self.game.gui.addRoot = sorted_add
        self.native_clicked = None
        def route(event):
            handled = False
            if event.key == 1 and self.cursor.active and native_hit:
                for component in reversed(self.game.gui.roots):
                    if component.visible and component.mouseButtonFocus:
                        width, height = self.game.gui.screenResolution()[:2]
                        x, y = event.cursorPosition
                        if (abs(x-component.position[0]) < component.size[0]/width and
                                abs(y-component.position[1]) < component.size[1]/height):
                            handled = component.script.handleMouseButtonEvent(component, event)
                            if event.isKeyDown():
                                self.native_clicked = component
                            break
                if not event.isKeyDown() and self.native_clicked is not None:
                    handled = self.native_clicked.script.handleMouseClickEvent(self.native_clicked) or handled
                    self.native_clicked = None
            if not handled:
                for component in reversed(self.game.gui.roots):
                    if component.visible and component.focus:
                        if component.script.handleKeyEvent(event):
                            return True
            return handled
        return route, flash

    def routed_event(self, index, down, key=1, position=None):
        component = self.mod._controls[index][0]
        return types.SimpleNamespace(key=key, isKeyDown=lambda: down,
            cursorPosition=component.position[:2] if position is None else position)

    def test_root_key_route_handles_click_when_native_hit_callback_is_missing(self):
        route, flash = self.install_native_router(native_hit=False)
        self.game.state()
        for ctrl in (False, True):
            self.ctrl = ctrl
            for index, setting in ((0, '_reminder_enabled'), (1, '_voice_enabled')):
                with self.subTest(ctrl=ctrl, setting=setting):
                    before = getattr(self.mod, setting)
                    self.assertTrue(route(self.routed_event(index, True)))
                    self.assertTrue(route(self.routed_event(index, False)))
                    self.assertEqual(getattr(self.mod, setting), not before)
        self.assertEqual(self.flash_events, [])
        self.assertEqual(self.game.gui.roots[0], flash)

    def test_native_mouse_route_and_duplicate_click_toggle_once(self):
        route, unused_flash = self.install_native_router()
        self.sync()
        for ctrl in (False, True):
            self.ctrl = ctrl
            for index, setting in ((0, '_reminder_enabled'), (1, '_voice_enabled')):
                with self.subTest(ctrl=ctrl, setting=setting):
                    before = getattr(self.mod, setting)
                    self.assertTrue(route(self.routed_event(index, True)))
                    self.assertTrue(route(self.routed_event(index, False)))
                    self.assertEqual(getattr(self.mod, setting), not before)
        self.assertEqual(self.flash_events, [])

    def test_mouse_and_root_click_paths_do_not_require_key_state_api(self):
        self.sync()
        def unavailable_key_state(key):
            raise AssertionError('click handling must not query modifier keys')
        for state_api in ('absent', 'raises'):
            if state_api == 'absent':
                del self.game.world.isKeyDown
            else:
                self.game.world.isKeyDown = unavailable_key_state
            for path in ('mouse', 'root'):
                with self.subTest(state_api=state_api, path=path):
                    component, unused_owner, unused_mount, handler = self.mod._controls[0]
                    before = self.mod._reminder_enabled
                    def send(down):
                        event = self.routed_event(0, down)
                        return (handler.handleMouseButtonEvent(component, event)
                            if path == 'mouse' else handler.handleKeyEvent(event))
                    self.assertTrue(send(True))
                    self.assertTrue(send(False))
                    self.assertEqual(self.mod._reminder_enabled, not before)

    def test_releasing_ctrl_before_mouse_up_keeps_click_when_cursor_stays_visible(self):
        self.sync()
        for path in ('mouse', 'root'):
            with self.subTest(path=path):
                component, unused_owner, unused_mount, handler = self.mod._controls[0]
                before = self.mod._reminder_enabled
                def send(down):
                    event = self.routed_event(0, down)
                    return (handler.handleMouseButtonEvent(component, event)
                        if path == 'mouse' else handler.handleKeyEvent(event))
                self.ctrl = True
                self.assertTrue(send(True))
                self.ctrl = False
                self.assertTrue(send(False))
                self.assertFalse(send(False))
                self.assertFalse(handler.handleMouseClickEvent(component))
                self.assertEqual(self.mod._reminder_enabled, not before)

    def test_same_mouse_event_delivered_to_both_paths_never_toggles_twice(self):
        self.sync()
        self.ctrl = True
        component, unused_owner, unused_mount, handler = self.mod._controls[0]
        down = self.routed_event(0, True)
        up = self.routed_event(0, False)
        self.assertTrue(handler.handleMouseButtonEvent(component, down))
        self.assertTrue(handler.handleKeyEvent(down))
        self.assertTrue(handler.handleMouseButtonEvent(component, up))
        self.assertFalse(handler.handleKeyEvent(up))
        self.assertFalse(handler.handleMouseClickEvent(component))
        self.assertFalse(self.mod._reminder_enabled)

    def test_root_route_passes_unrelated_keys_and_clicks_to_battle(self):
        route, unused_flash = self.install_native_router(native_hit=False)
        self.sync()
        self.ctrl = True
        route(self.routed_event(0, True, key=50))
        route(self.routed_event(0, True, position=(-0.9, 0.9)))
        self.cursor.active = False
        route(self.routed_event(0, True))
        route(self.routed_event(0, False))
        self.assertEqual(len(self.flash_events), 4)
        self.assertTrue(self.mod._reminder_enabled)

    def test_root_route_cancels_release_outside_and_consumes_captured_click(self):
        route, unused_flash = self.install_native_router(native_hit=False)
        self.sync()
        self.ctrl = True
        self.assertTrue(route(self.routed_event(0, True)))
        self.assertTrue(route(self.routed_event(0, False, position=(-0.9, 0.9))))
        self.assertTrue(self.mod._reminder_enabled)
        self.assertEqual(self.flash_events, [])
        # Returning to the button cannot complete the cancelled press.
        route(self.routed_event(0, False))
        self.assertTrue(self.mod._reminder_enabled)
        self.assertEqual(len(self.flash_events), 1)

    def test_inactive_or_hidden_cursor_and_modal_hud_cannot_toggle(self):
        self.sync()
        self.cursor.active = False
        self.assertFalse(self.click(0, True))
        self.cursor.active = True
        self.cursor.visible = False
        self.assertFalse(self.click(0, True))
        self.cursor.visible = True
        self.panel.app.isModalViewShown = lambda: True
        self.assertFalse(self.click(0, True))
        self.panel.app.isModalViewShown = lambda: False
        self.assertTrue(self.click(0, True))
        self.assertTrue(self.click(0, False))
        self.assertFalse(self.mod._reminder_enabled)

    def test_camera_and_hud_changes_are_rechecked_before_next_state_tick(self):
        self.sync()
        self.ctrl = True
        self.panel.camera_mode = 'sniper'
        self.assertFalse(self.click(0, True))
        self.panel.camera_mode = 'arcade'
        self.panel.native_visible = False
        self.assertFalse(self.click(0, True))
        self.panel.native_visible = True
        self.assertTrue(self.click(0, True))
        self.assertTrue(self.click(0, False))
        self.assertFalse(self.mod._reminder_enabled)


if __name__ == '__main__':
    unittest.main()
