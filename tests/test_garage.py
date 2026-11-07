"""Native footer ownership, command boundaries and optional failure isolation."""
import contextlib
import gc
import importlib.util
import json
from pathlib import Path
import sys
import types
import unittest
import weakref
from unittest.mock import patch


SPEC = importlib.util.spec_from_file_location(
    'medkit_garage_tests', Path(__file__).resolve().parents[1] /
    'source' / 'staysharp_medkit' / 'garage.py')
garage = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(garage)


class Event(object):
    def __init__(self):
        self.handlers = []

    def __iadd__(self, callback):
        self.handlers.append(callback)
        return self

    def __call__(self, *args):
        for callback in self.handlers[:]:
            callback(*args)


class Model(object):
    def __init__(self, properties, commands):
        self.counts = (properties, commands)
        self.props = []
        self._initialize()

    def _initialize(self):
        pass

    def _addStringProperty(self, name, value):
        self.props.append([name, value])

    def _addViewModelProperty(self, name, value):
        self.props.append([name, value])

    def _addCommand(self, name):
        return Event()

    def _setString(self, index, value):
        self.props[index][1] = value

    @contextlib.contextmanager
    def transaction(self):
        yield


class Component(object):
    serial = 0

    def __init__(self, model=None):
        Component.serial += 1
        self.uniqueID = Component.serial
        self.children = {}
        self.original_calls = 0
        self.unloading_calls = 0
        self.finalize_calls = 0
        self.model = model() if model else None

    def getViewModel(self):
        return self.model

    def _onLoading(self, *args, **kwargs):
        self.original_calls += 1
        return 'native-result'

    def _onUnloading(self):
        self.unloading_calls += 1

    def _finalize(self):
        self.finalize_calls += 1

    def getChildView(self, position):
        return self.children.get(position)

    def _registerChild(self, position, child):
        self.children[position] = child

    def _unregisterChild(self, uid, destroy):
        for position, child in list(self.children.items()):
            if child.uniqueID == uid:
                child._onUnloading()
                child._finalize()
                del self.children[position]


class GarageTests(unittest.TestCase):
    def setUp(self):
        self.actions = []
        self.payload = {'hotkeys': {'toggle_mod': ['CTRL', 'M']},
                        'capturing': None, 'preview': '', 'status': ''}

        class LobbyFooter(Component):
            pass

        self.footer_class = LobbyFooter

        def inject(model, name, styles=None, modules=None):
            self.assertEqual(name, garage.INJECT_NAME)
            self.assertEqual(styles, [garage.STYLE_URL])
            self.assertEqual(modules, [garage.MODULE_URL])
            model._addStringProperty('ModInjectModel', '{}')

        modules = {}
        for name, values in (
                ('frameworks.wulf', {'ViewModel': Model}),
                ('gui.impl.pub.view_component', {'ViewComponent': Component}),
                ('gui.impl.lobby.page.lobby_footer', {'LobbyFooter': LobbyFooter}),
                ('openwg_gameface', {'gf_mod_inject': inject})):
            module = types.ModuleType(name)
            module.__dict__.update(values)
            modules[name] = module
        self.modules = patch.dict(sys.modules, modules)
        self.modules.start()
        self.addCleanup(self.modules.stop)
        self.addCleanup(self.cleanup)
        self.handle = garage.install(self.actions.append, lambda: self.payload)
        self.assertIsNotNone(self.handle)

    def cleanup(self):
        if garage._installed is not None:
            garage._installed.uninstall()
            garage._installed = None

    def attach(self):
        view = self.footer_class()
        self.assertEqual(view._onLoading(), 'native-result')
        child = view.getChildView(garage.POSITION_ID)
        commands = child.model.props[1][1]
        return view, child, commands

    def test_native_model_contract_and_primitive_command_allowlist(self):
        view, child, commands = self.attach()
        self.assertEqual(child.model.counts, (2, 0))
        self.assertEqual(commands.counts, (1, 1))
        self.assertEqual(child.model.props[1][0], 'grzMedkitFooter')
        self.assertEqual(json.loads(commands.props[0][1]), self.payload)
        commands.onAction({'action': 'begin_capture', 'binding': 'toggle_voice',
                           'event': object()})
        self.assertEqual(self.actions, [{'action': 'begin_capture', 'binding': 'toggle_voice'}])
        for arg in ({'action': 'launch'}, {'action': []},
                    {'action': 'begin_capture', 'binding': 'other'},
                    {'action': 'clear_binding'}, {'action': 'open', 'binding': object()},
                    'open', None):
            commands.onAction(arg)
        self.assertEqual(len(self.actions), 1)
        self.assertEqual(view.original_calls, 1)

    def test_bounded_state_dedup_and_failed_native_write_retry(self):
        view, child, commands = self.attach()
        original = commands._setString
        writes = []

        def rejected(*args):
            raise RuntimeError('native failure')

        commands._setString = rejected
        self.payload['status'] = 'saved'
        self.assertTrue(self.handle.update(self.payload))
        self.assertEqual(json.loads(commands.props[0][1])['status'], '')
        commands._setString = lambda index, value: (writes.append(value), original(index, value))
        self.assertFalse(self.handle.update(self.payload))
        self.assertEqual(json.loads(commands.props[0][1])['status'], 'saved')
        self.assertFalse(self.handle.update(self.payload))
        self.assertEqual(len(writes), 1)
        before = commands.props[0][1]
        for value in ({'status': 'x' * (garage.MAX_PAYLOAD_CHARS + 1)},
                      {'status': float('nan')}, {'status': object()}, []):
            self.assertFalse(self.handle.update(value))
        self.assertEqual(commands.props[0][1], before)

    def test_native_unload_cancels_once_and_retained_command_is_inert(self):
        view, child, commands = self.attach()
        child._onUnloading()
        child._finalize()
        self.assertEqual(self.actions, [{'action': 'cancel_capture'}])
        self.assertEqual((child.unloading_calls, child.finalize_calls), (1, 1))
        commands.onAction({'action': 'open'})
        self.assertEqual(len(self.actions), 1)

    def test_open_loads_current_payload_before_window_and_validates_anchor(self):
        order = []
        settings = types.SimpleNamespace(
            open=lambda anchor: order.append(('open', anchor, self.handle._state)) or True,
            update=lambda state: order.append(('update', state)),
            close=lambda notify=True: True,
            is_capture_allowed=lambda: True)
        self.handle._settings = settings

        def action(command):
            self.actions.append(command)
            if command['action'] == 'open':
                self.payload['status'] = 'loaded'

        self.handle._on_action = action
        self.assertTrue(self.handle.dispatch({'action': 'open', 'anchorX': 0.25,
                                              'nativeEvent': object()}))
        self.assertEqual(self.actions, [{'action': 'open', 'anchorX': 0.25}])
        self.assertEqual(order[-1][:2], ('open', 0.25))
        self.assertEqual(json.loads(order[-1][2])['status'], 'loaded')
        self.assertTrue(self.handle.is_capture_allowed())
        for anchor in (True, '0.5', -1, 2, float('nan'), float('inf')):
            self.assertFalse(self.handle.dispatch({'action': 'open', 'anchorX': anchor}))
        self.assertEqual(len(self.actions), 1)
        self.handle._on_action = lambda command: False
        count = len(order)
        self.assertFalse(self.handle.dispatch({'action': 'open', 'anchorX': 0.5}))
        self.assertEqual(len(order), count)

    def test_weak_child_tracking_does_not_keep_native_views_alive(self):
        view, child, commands = self.attach()
        vr, cr = weakref.ref(view), weakref.ref(child)
        del view, child, commands
        gc.collect()
        self.assertIsNone(vr())
        self.assertIsNone(cr())
        self.handle.update(self.payload)
        self.assertEqual(self.handle._children, [])

    def test_occupied_position_is_never_replaced(self):
        view = self.footer_class()
        foreign = Component()
        view.children[garage.POSITION_ID] = foreign
        view._onLoading()
        self.assertIs(view.getChildView(garage.POSITION_ID), foreign)
        self.handle.uninstall()
        self.assertIs(view.getChildView(garage.POSITION_ID), foreign)

    def test_other_mod_wrapper_is_preserved_and_ours_becomes_inert(self):
        previous = self.footer_class._onLoading
        observed = []

        def later(view, *args, **kwargs):
            observed.append(True)
            return previous(view, *args, **kwargs)

        self.footer_class._onLoading = later
        self.assertTrue(self.handle.uninstall())
        self.assertIs(self.footer_class._onLoading, later)
        view = self.footer_class()
        view._onLoading()
        self.assertEqual(observed, [True])
        self.assertEqual(view.children, {})
        self.assertEqual(view.original_calls, 1)

    def test_partial_registration_retains_failed_cleanup_for_retry(self):
        view = self.footer_class()
        original_register = view._registerChild
        original_remove = view._unregisterChild

        def partial(position, child):
            original_register(position, child)
            raise RuntimeError('attached before failing')

        view._registerChild = partial
        view._unregisterChild = lambda *args: None
        view._onLoading()
        self.assertIsNotNone(view.getChildView(garage.POSITION_ID))
        self.assertFalse(self.handle.uninstall())
        self.assertIs(garage._installed, self.handle)
        self.assertIsNone(garage.install(self.actions.append, lambda: self.payload))
        view._unregisterChild = original_remove
        self.assertTrue(self.handle.uninstall())
        self.assertIsNone(garage._installed)
        self.assertEqual(view.children, {})

    def test_failed_cleanup_does_not_remove_a_foreign_replacement(self):
        view, child, commands = self.attach()
        original_remove = view._unregisterChild
        view._unregisterChild = lambda *args: None
        self.assertFalse(self.handle.uninstall())
        foreign = Component()
        view.children[garage.POSITION_ID] = foreign
        attempts = []
        view._unregisterChild = lambda *args: attempts.append(args)
        self.assertTrue(self.handle.uninstall())
        self.assertEqual(attempts, [])
        self.assertIs(view.getChildView(garage.POSITION_ID), foreign)
        view._unregisterChild = original_remove

    def test_missing_optional_openwg_does_not_escape(self):
        self.handle.uninstall()
        with patch.dict(sys.modules, {'openwg_gameface': None}):
            self.assertIsNone(garage.install(self.actions.append, lambda: self.payload))


if __name__ == '__main__':
    unittest.main()
