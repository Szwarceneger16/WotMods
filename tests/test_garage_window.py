"""Native settings-window lifecycle and placement contract tests."""
import importlib.util
import json
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
        self.parent = types.SimpleNamespace(proxy=object(), windowStatus=2,
                                            size=(1920, 1080), onSizeChanged=Event())
        loader = types.SimpleNamespace(scale=1.5, windowsManager=types.SimpleNamespace(
            getMainWindow=lambda: self.parent))
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
                   'gui.impl.gen': gen, 'helpers': helpers, 'skeletons.gui.impl': skeleton}
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
        self.assertEqual(native.position, (210, 627))
        self.assertEqual(native.show_calls, 1)

    def test_actual_native_size_and_parent_resize_clamp_to_viewport(self):
        native, model = self.open()
        native.onSizeChanged(7, 600, 360)
        self.assertEqual(native.position, (180, 612))
        self.parent.size = (500, 300)
        self.parent.onSizeChanged(1, 500, 300)
        self.assertEqual(native.position, (0, 0))
        self.assertEqual(json.loads(model.props[0][1])['viewport']['width'], 500)

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
