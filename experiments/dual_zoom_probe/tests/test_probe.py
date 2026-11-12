"""Offline tests with native-module stubs; no WoT client or GPU needed."""
import importlib.util
import math
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]


class FakeRenderer(object):
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.dynamic = 0
        self.skipFrames = 0
        self.cameras = []
        self.fov = 0
        self.texture = object()


class FakeSimple(object):
    eSizeMode = types.SimpleNamespace(PIXEL=1)
    ePositionMode = types.SimpleNamespace(CLIP=1)
    eHAnchor = types.SimpleNamespace(CENTER=1)
    eVAnchor = types.SimpleNamespace(CENTER=1)
    eMaterialFX = types.SimpleNamespace(BLEND=1)
    eFilterType = types.SimpleNamespace(LINEAR=1)

    def __init__(self, source):
        self.source = source
        self.texture = None
        self.size = None
        self.position = None
        self.colour = None
        self.visible = None


class FakeCamera(object):
    def __init__(self):
        self._cfg = {'zooms': [2.0, 4.0, 8.0, 16.0, 25.0], 'zoom': 4.0}
        self._SniperCamera__zoom = 4.0
        self.zoom_calls = []
        self.matrix = object()

    def _SniperCamera__applyZoom(self, zoom):
        self.zoom_calls.append(zoom)


class FakeBigWorld(types.ModuleType):
    def __init__(self):
        super(FakeBigWorld, self).__init__('BigWorld')
        self.current_camera = FakeCamera()
        self.current_projection = types.SimpleNamespace(fov=0.6)
        self.callbacks = {}
        self.next_callback = 1
        self.renderers = []
        self.pressed = set()

    def PySceneRenderer(self, width, height):
        result = FakeRenderer(width, height)
        self.renderers.append(result)
        return result

    def callback(self, delay, method):
        handle = self.next_callback
        self.next_callback += 1
        self.callbacks[handle] = (delay, method)
        return handle

    def cancelCallback(self, handle):
        self.callbacks.pop(handle, None)

    def run_zero_callbacks(self):
        for handle, (delay, func) in list(self.callbacks.items()):
            if delay == 0.0:
                self.callbacks.pop(handle, None)
                func()

    def camera(self):
        return self.current_camera

    def projection(self):
        return self.current_projection

    def isKeyDown(self, key):
        return key in self.pressed


class FakeGUI(types.ModuleType):
    def __init__(self):
        super(FakeGUI, self).__init__('GUI')
        self.Simple = FakeSimple
        self.roots = []
        self.resolution = (1920, 1080)

    def addRoot(self, component):
        self.roots.append(component)

    def delRoot(self, component):
        self.roots.remove(component)

    def screenResolution(self):
        return self.resolution


class TestProbe(unittest.TestCase):
    def setUp(self):
        self.world = FakeBigWorld()
        self.gui = FakeGUI()
        self.keys = types.ModuleType('Keys')
        self.keys.KEY_LCONTROL = 11
        self.keys.KEY_RCONTROL = 12
        self.keys.KEY_LALT = 13
        self.keys.KEY_RALT = 14
        self.keys.KEY_P = 15
        self.keys.KEY_D = 16
        camera = self.world.current_camera

        class SniperControlMode(object):
            def __init__(self):
                self.isEnabled = False
                self.camera = camera
                self.mouse_calls = []
                self.key_calls = []

            def enable(self, *unused, **unused_kwargs):
                self.isEnabled = True

            def disable(self, *unused, **unused_kwargs):
                self.isEnabled = False

            def handleMouseEvent(self, dx, dy, dz):
                self.mouse_calls.append((dx, dy, dz))
                return True

            def handleKeyEvent(self, is_down, code, mods, event=None):
                self.key_calls.append((is_down, code, mods, event))
                return False

            def onRecreateDevice(self):
                return True

        self.mode_class = SniperControlMode
        avatar = types.ModuleType('AvatarInputHandler')
        controls = types.ModuleType('AvatarInputHandler.control_modes')
        controls.SniperControlMode = SniperControlMode
        self.modules = patch.dict(sys.modules, {
            'BigWorld': self.world, 'GUI': self.gui, 'Keys': self.keys,
            'AvatarInputHandler': avatar,
            'AvatarInputHandler.control_modes': controls})
        self.modules.start()
        self.temp = tempfile.TemporaryDirectory()
        self.local = patch.dict('os.environ', {'LOCALAPPDATA': self.temp.name})
        self.local.start()
        spec = importlib.util.spec_from_file_location('isolated_probe', ROOT / 'mod_dual_zoom_probe.py')
        self.probe = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.probe)

    def tearDown(self):
        self.probe.fini()
        self.local.stop()
        self.temp.cleanup()
        self.modules.stop()

    def start(self, renderer=True, replay_only=False):
        config = self.probe._load_config()
        config['enable_native_renderer'] = renderer
        config['replay_only'] = replay_only
        self.probe._SESSION = self.probe._Session(config)
        self.probe._LIVE = True
        self.probe._inspect_api()
        self.probe._install_hooks()
        mode = self.mode_class()
        mode.enable()
        self.world.run_zero_callbacks()
        return mode

    def test_probe_without_opt_in_has_zero_gpu_or_gui_work(self):
        mode = self.start(renderer=False)
        self.assertFalse(self.world.renderers)
        self.assertFalse(self.gui.roots)
        self.assertEqual(self.world.current_camera._SniperCamera__zoom, 4)
        mode.handleMouseEvent(7, 8, 1)
        self.assertEqual(mode.mouse_calls[-1], (7, 8, 1))
        self.assertFalse(self.probe._SESSION.started)
        self.assertTrue((Path(self.temp.name) / 'DualZoomProbe' / 'capabilities.json').exists())

    def test_real_renderer_has_shared_camera_and_separate_corrected_fov(self):
        mode = self.start()
        session = self.probe._SESSION
        self.assertTrue(session.started)
        self.assertEqual(len(self.world.renderers), 1)
        native = self.world.current_camera
        self.assertEqual(native._SniperCamera__zoom, 2.0)
        self.assertEqual(native._cfg['zoom'], 2.0)
        renderer = self.world.renderers[0]
        self.assertEqual(renderer.cameras, [native])
        self.assertEqual(renderer.dynamic, 1)
        self.assertIs(self.gui.roots[0].texture, renderer.texture)
        self.assertEqual(len(self.gui.roots), 5)
        expected = 2 * math.atan(math.tan(0.6 / 2) * 240 / 1080)
        self.assertAlmostEqual(renderer.fov, expected, places=8)
        mode.handleMouseEvent(9, -7, 1)
        self.assertEqual(mode.mouse_calls[-1], (9, -7, 0))
        self.assertEqual(session.zoom, 4.0)
        self.assertEqual(native._SniperCamera__zoom, 2.0)
        self.world.run_zero_callbacks()
        self.assertLess(renderer.fov, expected)
        mode.disable()
        self.assertEqual(renderer.dynamic, 0)
        self.assertEqual(native._SniperCamera__zoom, 4.0)
        self.assertEqual(native._cfg['zoom'], 4.0)
        self.world.run_zero_callbacks()
        self.assertFalse(self.gui.roots)

    def test_missing_native_api_fails_open_to_original_controls(self):
        self.world.PySceneRenderer = None
        mode = self.start()
        self.assertFalse(self.probe._SESSION.started)
        self.assertEqual(self.probe._REPORT['runtime']['native_render'], 'missing_api')
        self.assertEqual(self.world.current_camera._SniperCamera__zoom, 4.0)
        mode.handleMouseEvent(1, 2, 3)
        self.assertEqual(mode.mouse_calls[-1], (1, 2, 3))

    def test_runtime_creation_failure_restores_native_zoom(self):
        def failing(*args):
            raise RuntimeError('fake GPU failure')
        self.world.PySceneRenderer = failing
        mode = self.start()
        self.assertFalse(self.probe._SESSION.started)
        self.assertFalse(self.gui.roots)
        self.assertEqual(self.world.current_camera._SniperCamera__zoom, 4.0)
        self.assertEqual(self.world.current_camera._cfg['zoom'], 4.0)
        self.assertEqual(self.probe._REPORT['runtime']['native_render'], 'failed')
        mode.handleMouseEvent(1, 1, -1)
        self.assertEqual(mode.mouse_calls[-1], (1, 1, -1))

    def test_replay_gate_prevents_renderer_or_zoom_mutation(self):
        mode = self.start(replay_only=True)
        self.assertFalse(self.probe._SESSION.started)
        self.assertEqual(self.probe._REPORT['runtime']['native_render'], 'replay_only')
        self.assertFalse(self.world.renderers)
        self.assertEqual(self.world.current_camera._SniperCamera__zoom, 4.0)
        mode.disable()

    def test_ctrl_alt_p_disables_renderer_and_removes_roots(self):
        mode = self.start()
        self.world.pressed = {self.keys.KEY_LCONTROL, self.keys.KEY_LALT}
        self.assertTrue(mode.handleKeyEvent(True, self.keys.KEY_P, 0))
        self.assertFalse(self.probe._SESSION.started)
        self.world.run_zero_callbacks()
        self.assertEqual(self.gui.roots, [])
        self.assertEqual(self.world.renderers[0].dynamic, 0)

    def test_renderer_throttling_is_explicit_and_optional(self):
        cfg = self.probe._load_config()
        cfg.update({'enable_native_renderer': True, 'replay_only': False,
                    'skip_frames': 2, 'staggered': True, 'max_zoom': 32})
        self.probe._SESSION = self.probe._Session(cfg)
        self.probe._LIVE = True
        self.probe._inspect_api()
        self.probe._install_hooks()
        mode = self.mode_class()
        mode.enable()
        self.world.run_zero_callbacks()
        self.assertTrue(self.probe._SESSION.started)
        self.assertEqual(self.world.renderers[0].skipFrames, 2)
        self.assertEqual(self.world.renderers[0].staggered, 1)
        for unused in range(5):
            mode.handleMouseEvent(0, 0, 1)
        self.world.run_zero_callbacks()
        self.assertEqual(self.probe._SESSION.zoom, 32.0)

    def test_hooks_can_be_uninstalled_and_reinstalled(self):
        self.start(renderer=False)
        first = self.mode_class.handleMouseEvent
        self.probe.fini()
        self.assertIsNot(first, self.mode_class.handleMouseEvent)
        self.probe._LIVE = True
        self.probe._SESSION = self.probe._Session(self.probe._load_config())
        self.probe._install_hooks()
        self.assertIsNot(first, self.mode_class.handleMouseEvent)
        self.assertIn('handleMouseEvent', self.probe._ORIGINAL)

    def test_resize_recomputes_fov_and_frame_positions(self):
        mode = self.start()
        initial_fov = self.world.renderers[0].fov
        self.gui.resolution = (1920, 1440)
        self.probe._SESSION._sync(self.probe._SESSION.generation)
        self.assertLess(self.world.renderers[0].fov, initial_fov)
        self.assertAlmostEqual(self.probe._SESSION.borders[0].position[1], 240/1440)
        mode.disable()

    def test_fov_rejects_invalid_geometry_and_x2_matches_pixel_scale(self):
        f = self.probe._inset_fov
        full_fov = 0.6
        inset = f(full_fov, 1080, 240, 2.0)
        self.assertAlmostEqual(math.tan(inset/2) * 1080 / 240,
                               math.tan(full_fov/2))
        self.assertLess(f(full_fov, 1080, 240, 25), inset)
        for arg in ((0, 1080, 240, 2), (full_fov, 0, 240, 2),
                    (full_fov, 1080, 240, 35)):
            with self.assertRaises(ValueError):
                f(*arg)

    def test_large_config_is_rejected_without_large_target(self):
        target = Path(self.temp.name) / 'DualZoomProbe'
        target.mkdir()
        (target / 'config.json').write_text('{"width": 999999, "height": 99999}')
        cfg = self.probe._load_config()
        self.assertEqual((cfg['width'], cfg['height']), (400, 240))


if __name__ == '__main__':
    unittest.main()
