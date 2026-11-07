"""Native settings-window lifecycle and placement contract tests."""
import importlib.util
import json
import math
import os
import sys
import types
import unittest
from contextlib import contextmanager
from unittest.mock import patch

PATH = os.path.join(os.path.dirname(__file__), '..', 'source',
                    'staysharp_medkit', 'views.py')
SPEC = importlib.util.spec_from_file_location('medkit_window_tests', PATH)
views = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(views)


class Event(object):
    def __init__(self):
        self.listeners = []

    def __iadd__(self, callback):
        self.listeners.append(callback)
        return self

    def __isub__(self, callback):
        self.listeners.remove(callback)
        return self

    def __call__(self, *args):
        for callback in list(self.listeners):
            callback(*args)


class Model(object):
    def __init__(self, properties, commands):
        self.counts = (properties, commands)
        self.props = []
        self._initialize()

    def _initialize(self):
        pass

    def _addStringProperty(self, name, value):
        self.props.append((name, value))

    def _addCommand(self, name):
        return Event()

    def _setString(self, index, value):
        self.props[index] = (self.props[index][0], value)

    @contextmanager
    def transaction(self):
        yield self


class View(object):
    def __init__(self, settings):
        self.settings = settings


class NativeWindow(object):
    instances = []

    def __init__(self, flags, **kwargs):
        self.flags, self.options = flags, kwargs
        self.proxy = object()
        self.windowStatus = 0
        self.isFocused = False
        self.hidden = True
        self.size = (1, 1)
        self.position = None
        self.moves = []
        self.show_calls = 0
        self.destroy_calls = 0
        self.finalize_calls = 0
        self.fail_destroy = False
        self.onSizeChanged = Event()
        self.onFocusChanged = Event()
        self.onStatusChanged = Event()
        self.instances.append(self)

    def load(self):
        self.windowStatus = 2
        self._onReady()

    def move(self, x, y):
        if (isinstance(x, bool) or isinstance(y, bool) or
                not isinstance(x, int) or not isinstance(y, int)):
            raise TypeError('WindowImpl.move expects separate pixel coordinates')
        self.position = (x, y)
        self.moves.append(self.position)
        return True

    def show(self, focus=True):
        self.show_calls += 1
        self.hidden = False
        self.isFocused = focus
        self.onFocusChanged(focus)

    def isHidden(self):
        return self.hidden

    def _finalize(self):
        self.finalize_calls += 1

    def destroy(self):
        self.destroy_calls += 1
        if self.fail_destroy:
            raise RuntimeError('native destroy unavailable')
        self.windowStatus = 3
        self.onStatusChanged(3)
        self._finalize()
        self.windowStatus = 4
        self.proxy = None
        self.onStatusChanged(4)


class WindowTests(unittest.TestCase):
    def setUp(self):
        NativeWindow.instances = []
        self.mouse_down = False
        self.jobs = {}
        self.serial = 0

        def callback(delay, fn):
            self.serial += 1
            self.jobs[self.serial] = (delay, fn)
            return self.serial

        world = types.ModuleType('BigWorld')
        world.callback = callback
        world.cancelCallback = lambda key: self.jobs.pop(key, None)
        world.isKeyDown = lambda key: self.mouse_down if key == 1 else False
        keys = types.ModuleType('Keys')
        keys.KEY_LEFTMOUSE = 1
        self.screen_size = (1920, 1080)
        gui = types.ModuleType('GUI')
        gui.screenResolution = lambda: self.screen_size
        self.parent = types.SimpleNamespace(proxy=object(), windowStatus=2,
                                            size=(1920, 1080), onSizeChanged=Event())
        loader = types.SimpleNamespace(scale=1.5, windowsManager=types.SimpleNamespace(
            getMainWindow=lambda: self.parent))
        self.loader = loader
        wulf = types.ModuleType('frameworks.wulf')
        wulf.ViewModel = Model
        wulf.ViewFlags = types.SimpleNamespace(VIEW=17)
        wulf.ViewSettings = lambda **kwargs: types.SimpleNamespace(**kwargs)
        wulf.WindowFlags = types.SimpleNamespace(WINDOW=29)
        wulf.WindowLayer = types.SimpleNamespace(WINDOW=31)
        wulf.WindowStatus = types.SimpleNamespace(LOADED=2, DESTROYING=3, DESTROYED=4)
        pub = types.ModuleType('gui.impl.pub')
        pub.ViewImpl, pub.WindowImpl = View, NativeWindow
        resource = types.SimpleNamespace(Settings=lambda: 4567)
        gen = types.ModuleType('gui.impl.gen')
        gen.R = types.SimpleNamespace(mods=types.SimpleNamespace(grz=types.SimpleNamespace(
            staysharp_medkit=types.SimpleNamespace(views=resource))))
        helpers = types.ModuleType('helpers')
        helpers.dependency = types.SimpleNamespace(instance=lambda cls: loader)
        skeleton = types.ModuleType('skeletons.gui.impl')
        skeleton.IGuiLoader = object
        modules = {'frameworks.wulf': wulf, 'gui.impl.pub': pub,
                   'gui.impl.gen': gen, 'helpers': helpers, 'skeletons.gui.impl': skeleton,
                   'BigWorld': world, 'Keys': keys, 'GUI': gui}
        self.patch = patch.dict(sys.modules, modules)
        self.patch.start()
        self.addCleanup(self.patch.stop)
        self.actions = []
        self.state = json.dumps({'capturing': None, 'status': ''})
        self.controller = views.SettingsWindow(self.actions.append, lambda: self.state)
        self.addCleanup(lambda: self.controller.close(notify=False))

    def open(self, anchor=0.25):
        self.assertTrue(self.controller.open(anchor))
        return self.controller._window, self.controller._model

    def tick(self):
        self.assertTrue(self.jobs)
        key = min(self.jobs)
        delay, fn = self.jobs.pop(key)
        fn()
        return delay

    def test_registered_resource_model_and_scaled_bottom_placement(self):
        native, model = self.open()
        self.assertEqual(native.flags, 29)
        self.assertEqual(native.options['layer'], 31)
        self.assertEqual(native.options['content'].settings.layoutID, 4567)
        self.assertIs(native.options['parent'], self.parent)
        self.assertEqual(model.counts, (1, 1))
        self.assertEqual(model.props[0][0], 'state')
        self.assertEqual(json.loads(model.props[0][1])['viewport'],
                         {'width': 1920, 'height': 1080, 'scale': 1.5})
        self.assertEqual(native.position, (210, 552))
        self.assertEqual(native.show_calls, 1)

    def test_parent_resize_refits_layout_without_using_stale_native_bounds(self):
        native, model = self.open()
        native.onSizeChanged(7, 600, 360)
        self.assertEqual(native.position, (210, 552))
        self.parent.size = (500, 300)
        self.screen_size = (500, 300)
        self.parent.onSizeChanged(1, 500, 300)
        self.assertEqual(native.position, (24, 24))
        self.assertEqual(json.loads(model.props[0][1])['viewport']['width'], 500)

    def test_client_surface_wins_over_default_parent_texture(self):
        self.parent.size = (256, 256)
        native, model = self.open(anchor=0.8)
        self.assertEqual(json.loads(model.props[0][1])['viewport'],
                         {'width': 1920, 'height': 1080, 'scale': 1.5})
        self.assertEqual(native.position, (1266, 552))

    def test_native_global_footer_anchor_positions_popup_above_the_icon(self):
        self.assertTrue(self.controller.open(0.8, 0.94))
        native = self.controller._window
        self.assertEqual(native.position, (1266, 583))
        for anchor_y in (True, -1, 2, float('nan'), float('inf'), object()):
            self.assertFalse(self.controller.open(0.8, anchor_y))

    def test_layout_command_is_bounded_and_stays_inside_window_controller(self):
        native, model = self.open()
        model.onAction({'action': 'layout', 'width': 480, 'height': 320})
        self.assertEqual(self.controller._reported_size, (480, 320))
        self.assertEqual(native.position, (240, 652))
        self.assertEqual(self.actions, [])
        for width, height in ((True, 320), (0, 320), (-1, 320),
                              (float('nan'), 320), (480, float('inf')),
                              (views.MAX_DIMENSION + 1, 320)):
            model.onAction({'action': 'layout', 'width': width, 'height': height})
        self.assertEqual(self.controller._reported_size, (480, 320))
        native.onSizeChanged(7, 540, 345)
        self.assertEqual(native.position, (240, 652))

    def test_all_edges_keep_scaled_gutter_across_aspects_and_interface_scales(self):
        screens = ((1920, 1080), (1920, 1200), (2560, 1080), (3440, 1440),
                   (1280, 720), (800, 600), (640, 360), (600, 900),
                   (320, 480), (320, 200), (200, 160))
        for width, height in screens:
            for scale in (1, 1.25, 1.5, 2, 3):
                for anchor_x, anchor_y in ((0, 0), (1, 0), (0, 1), (1, 1)):
                    with self.subTest(screen=(width, height), scale=scale,
                                      anchor=(anchor_x, anchor_y)):
                        self.controller.close(notify=False)
                        self.screen_size = (width, height)
                        self.loader.scale = scale
                        self.assertTrue(self.controller.open(anchor_x, anchor_y))
                        native = self.controller._window
                        viewport = self.controller._viewport()
                        size, gutter, unused_available = views._fit_geometry(viewport)
                        expected_gutter = min(int(math.ceil(16 * scale)), max(1, min(width, height) // 4))
                        self.assertEqual(gutter, expected_gutter)
                        self.assertTrue(self.controller.report_layout(*size))
                        left, top = native.position
                        self.assertGreaterEqual(left, gutter)
                        self.assertGreaterEqual(top, gutter)
                        self.assertLessEqual(left + size[0], width - gutter)
                        self.assertLessEqual(top + size[1], height - gutter)
                        self.assertGreater(size[0], 0)
                        self.assertGreater(size[1], 0)
                        # One uniformly scaled 360x280 design, with only the
                        # requested physical-pixel rounding allowed to differ.
                        self.assertLess(abs(size[0] / 360.0 - size[1] / 280.0), 1.0 / 280)

    def test_native_default_and_fullscreen_observations_never_override_document_size(self):
        native, unused_model = self.open(anchor=1)
        self.assertTrue(self.controller.report_layout(540, 420))
        expected = native.position
        self.assertEqual(expected, (1356, 552))
        for native_size in ((256, 256), (1920, 1080), (540, 420)):
            native.onSizeChanged(7, *native_size)
            self.assertEqual(native.position, expected)
            self.assertEqual(self.controller._reported_size, (540, 420))

    def test_resize_and_scale_changes_reject_old_document_geometry(self):
        native, model = self.open(anchor=1)
        self.assertTrue(self.controller.report_layout(540, 420))
        self.screen_size = self.parent.size = (320, 200)
        self.loader.scale = 2
        self.parent.onSizeChanged(1, 320, 200)
        self.assertEqual(json.loads(model.props[0][1])['viewport'],
                         {'width': 320, 'height': 200, 'scale': 2})
        size, gutter, unused_available = views._fit_geometry(self.controller._viewport())
        self.assertFalse(self.controller.report_layout(540, 420))
        self.assertEqual(native.position, (320 - gutter - size[0], gutter))
        self.assertTrue(self.controller.report_layout(*size))
        native.onSizeChanged(7, 1920, 1080)
        self.assertEqual(native.position, (320 - gutter - size[0], gutter))
        self.screen_size = self.parent.size = (2560, 1080)
        self.loader.scale = 1.25
        self.parent.onSizeChanged(1, 2560, 1080)
        self.assertEqual(native.position, (2090, 640))

    def test_one_pixel_client_degrades_gutter_instead_of_overflowing(self):
        self.screen_size = (1, 1)
        native, unused_model = self.open(anchor=1)
        self.assertEqual(views._fit_geometry(self.controller._viewport()), ((1, 1), 0, (1, 1)))
        self.assertEqual(native.position, (0, 0))
        self.assertTrue(self.controller.report_layout(1, 1))

    def test_repeated_open_does_not_steal_focus_or_show_again(self):
        native, unused_model = self.open()
        self.assertTrue(self.controller.open(0.75))
        self.assertEqual(len(NativeWindow.instances), 1)
        self.assertEqual(native.show_calls, 1)

    def test_capture_requires_loaded_focused_visible_window(self):
        native, model = self.open()
        self.assertTrue(self.controller.is_capture_allowed())
        native.isFocused = False
        native.onFocusChanged(False)
        self.assertEqual(self.actions, [{'action': 'cancel_capture'}])
        self.assertFalse(self.controller.is_capture_allowed())
        native.isFocused = True
        native.hidden = True
        self.assertFalse(self.controller.is_capture_allowed())
        native.hidden = False
        native.windowStatus = 0
        self.assertFalse(self.controller.is_capture_allowed())

    def test_focus_loss_cancels_capture_then_closes_outside_native_dispatch(self):
        native, unused_model = self.open()
        native.isFocused = False
        native.onFocusChanged(False)
        self.assertTrue(self.controller.is_open())
        self.assertEqual(native.destroy_calls, 0)
        self.assertEqual(self.actions, [{'action': 'cancel_capture'}])
        self.tick()
        self.assertTrue(self.controller.is_open())
        self.tick()
        self.assertFalse(self.controller.is_open())
        self.assertEqual(native.destroy_calls, 1)
        self.assertEqual(self.actions[-1], {'action': 'close'})

    def test_long_mouse_press_keeps_window_for_release_toggle_without_reopening(self):
        native, unused_model = self.open()
        self.mouse_down = True
        native.isFocused = False
        native.onFocusChanged(False)
        for unused in range(40):
            self.tick()
        self.assertTrue(self.controller.is_open())
        self.assertEqual(native.destroy_calls, 0)
        self.mouse_down = False
        self.tick()
        # The footer's release command closes the existing window before the
        # deferred focus cleanup, even after a press longer than one frame.
        self.assertTrue(self.controller.is_open())
        self.controller.close()
        self.assertEqual(native.destroy_calls, 1)
        self.assertEqual(self.jobs, {})
        self.assertEqual(len(NativeWindow.instances), 1)

    def test_blur_cleanup_is_bounded_and_focus_regain_cancels_it(self):
        native, unused_model = self.open()
        self.mouse_down = True
        native.isFocused = False
        native.onFocusChanged(False)
        self.tick()
        native.isFocused = True
        native.onFocusChanged(True)
        self.assertEqual(self.jobs, {})
        self.assertTrue(self.controller.is_open())
        native.isFocused = False
        native.onFocusChanged(False)
        for unused in range(views.BLUR_MAX_SAMPLES + 2):
            if self.jobs:
                self.tick()
        self.assertFalse(self.controller.is_open())
        self.assertEqual(self.jobs, {})

    def test_retained_blur_callback_is_inert_after_close_and_new_window(self):
        native, unused_model = self.open()
        native.isFocused = False
        native.onFocusChanged(False)
        callback = next(iter(self.jobs.values()))[1]
        self.controller.close()
        new, unused_model = self.open()
        callback()
        self.assertTrue(self.controller.is_open())
        self.assertIs(self.controller._window, new)
        self.assertEqual(new.destroy_calls, 0)

    def test_native_external_destroy_notifies_close_once_without_reentrant_destroy(self):
        native, model = self.open()

        def callback(action):
            self.actions.append(action)
            if action['action'] == 'close':
                self.controller.close(notify=False)

        self.controller._on_action = callback
        native.destroy()
        self.assertEqual(native.destroy_calls, 1)
        self.assertEqual(native.finalize_calls, 1)
        self.assertEqual(self.actions, [{'action': 'close'}])
        self.assertFalse(self.controller.is_capture_allowed())
        model.onAction({'action': 'begin_capture', 'binding': 'toggle_mod'})
        self.assertEqual(len(self.actions), 1)

    def test_failed_destroy_retains_ownership_until_retry(self):
        native, model = self.open()
        native.fail_destroy = True
        self.assertFalse(self.controller.close())
        self.assertIs(self.controller._window, native)
        self.assertFalse(self.controller.open())
        self.assertEqual(len(NativeWindow.instances), 1)
        native.fail_destroy = False
        self.assertTrue(self.controller.close())
        self.assertIsNone(self.controller._window)
        self.assertTrue(self.controller.open())
        self.assertEqual(len(NativeWindow.instances), 2)

    def test_model_update_retries_after_failed_native_transaction(self):
        native, model = self.open()
        original = model._setString
        model._setString = lambda *args: (_ for _ in ()).throw(RuntimeError('transient'))
        state = json.dumps({'status': 'saved'})
        self.assertFalse(self.controller.update(state))
        model._setString = original
        self.assertTrue(self.controller.update(state))
        self.assertEqual(json.loads(model.props[0][1])['status'], 'saved')

    def test_late_ready_and_retained_native_listener_are_inert_after_close(self):
        native, model = self.open()
        listeners = list(native.onFocusChanged.listeners)
        self.assertTrue(self.controller.close())
        native._onReady()
        for callback in listeners:
            callback(False)
        self.assertEqual(native.show_calls, 1)
        self.assertEqual(self.actions, [{'action': 'close'}])

    def test_invalid_bounds_and_unbounded_state_are_rejected(self):
        for anchor in (True, -1, 2, float('nan'), float('inf'), object()):
            self.assertFalse(self.controller.open(anchor))
        self.assertEqual(NativeWindow.instances, [])
        before = self.controller._state
        for state in ('[]', '{', '{"status":NaN}',
                      'x' * (views.MAX_STATE_CHARS + 1), object()):
            self.assertFalse(self.controller.update(state))
        self.assertEqual(self.controller._state, before)


if __name__ == '__main__':
    unittest.main()
