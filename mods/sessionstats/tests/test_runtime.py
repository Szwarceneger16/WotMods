# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import collections
import copy
import json
import logging
import os
import shutil
import sys
import tempfile
import types
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src'))
from grz_session_stats import VERSION, runtime, views, footer
from grz_session_stats.core import StatsService
from test_normalize import raw_result, ARENA_ID, START


EXPECTED = {'header': {'version': 'fixture'}, 'data': [
    {'IDNum': 1, 'expDamage': 1000, 'expFrag': 1, 'expSpot': 1, 'expDef': 1, 'expWinRate': 50}]}


class Obj(object):
    def __init__(self, **attributes):
        self.__dict__.update(attributes)


class FakeEvent(object):
    def __init__(self):
        self.handlers = []

    def __iadd__(self, handler):
        self.handlers.append(handler)
        return self

    def __isub__(self, handler):
        self.handlers.remove(handler)
        return self

    def __call__(self, *args):
        for handler in list(self.handlers):
            handler(*args)


class Clock(object):
    def __init__(self, value=START - 10):
        self.value = value

    def __call__(self):
        return self.value


class FakeBus(object):
    def __init__(self):
        self.handlers = []

    def addListener(self, name, callback):
        self.handlers.append((name, callback))

    def removeListener(self, name, callback):
        self.handlers.remove((name, callback))

    def emit(self):
        for unused_name, callback in list(self.handlers):
            callback(Obj(ctx={}))


class FakeWindow(object):
    def __init__(self):
        self.opened = False
        self.refreshes = 0
        self.sizes = []

    def open(self):
        self.opened = True
        return True

    def close(self):
        self.opened = False

    def is_open(self):
        return self.opened

    def refresh(self):
        self.refreshes += 1

    def resize(self, width, height):
        self.sizes.append((width, height))


class FakeAPI(object):
    EVENT_NAMES = ('onAccountBecomePlayer', 'onAccountShowGUI', 'onClientSynchronize',
                   'onAvatarReady', 'onAvatarBecomePlayer', 'onAccountBecomeNonPlayer',
                   'onBattleResultsReceived')

    def __init__(self):
        self.events = Obj(**dict((name, FakeEvent()) for name in self.EVENT_NAMES))
        self.input = Obj(onKeyDown=FakeEvent(), onKeyUp=FakeEvent())
        names = ['F{0}'.format(i) for i in range(1, 13)] + [
            'LCONTROL', 'RCONTROL', 'LSHIFT', 'RSHIFT', 'LALT', 'RALT']
        self.keys = Obj(**dict(('KEY_' + name, index + 1) for index, name in enumerate(names)))
        self.pressed = set()
        self.dbid = 7
        self.region = 'EU'
        self.random_bonus_type = 1
        self.replay = False
        self.battle = False
        self.context = None
        self.pending_callbacks = []
        self.callbacks = {}
        self.next_callback = 1
        self.posts = {}
        self.notices = []
        self.results_service = Obj(onResultPosted=FakeEvent())
        self.event_bus = FakeBus()
        self.bonus_event = 'premium-xp-bonus-changed'

    def is_replay(self):
        return self.replay

    def in_battle(self):
        return self.battle

    def account_dbid(self):
        return self.dbid

    def battle_context(self):
        return self.context

    def vehicle_info(self, compact):
        return {'name': 'Test vehicle', 'tier': 8, 'type': 'mediumTank'}

    def map_info(self, arena_type_id):
        return {'id': '17_map', 'name': 'Test map'}

    def key_down(self, key):
        return key in self.pressed

    def schedule(self, seconds, callback):
        callback_id = self.next_callback
        self.next_callback += 1
        self.callbacks[callback_id] = (seconds, callback)
        return callback_id

    def cancel(self, callback_id):
        self.callbacks.pop(callback_id, None)

    def request_result(self, arena_id, callback):
        self.pending_callbacks.append((arena_id, callback))
        return True

    def posted_bundle(self, arena_id):
        return self.posts.get(str(arena_id))

    def load_expected(self, directory):
        return copy.deepcopy(EXPECTED)

    def notify(self, message):
        self.notices.append(message)

    def fire(self, callback_id):
        unused_seconds, callback = self.callbacks.pop(callback_id)
        callback()


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.mkdtemp(prefix='grz-runtime-test-')
        self.clock = Clock()
        self.api = FakeAPI()
        self.window = FakeWindow()
        self.footer_calls = []
        self.log_level = logging.root.manager.disable
        logging.disable(logging.CRITICAL)
        self.mod = runtime.Runtime(deferred_loading=False, api=self.api, data_dir=self.directory,
                                   expected_table=EXPECTED, now=self.clock,
                                   window=self.window, footer_installer=self.no_footer)
        self.mod.start()

    def no_footer(self, callback):
        self.footer_calls.append(callback)
        return None

    def tearDown(self):
        self.mod.stop()
        logging.disable(self.log_level)
        shutil.rmtree(self.directory)

    def summary(self, scope='launch', service=None):
        service = service or self.mod.active_service
        return service.snapshot()['scopes'][scope]['summary']

    def test_missing_account_snapshot_uses_current_package_version(self):
        self.mod.active_service = None
        snapshot = self.mod.snapshot()
        self.assertEqual(snapshot['version'], VERSION)
        self.assertEqual(snapshot['scopes'], {})
        self.assertTrue(snapshot['warnings'])

    def begin(self, arena_id=ARENA_ID):
        self.clock.value = runtime.arena_start(arena_id)
        self.api.context = {'arena_id': arena_id, 'started_at': self.clock.value,
                            'vehicle_id': 1, 'map_id': '17_map', 'account_dbid': self.api.dbid,
                            'mode': 'random'}
        self.api.battle = True
        self.api.events.onAvatarReady()

    def garage(self):
        self.api.battle = False
        self.api.events.onAccountShowGUI()

    def tick(self, seconds=5):
        self.clock.value += seconds
        self.api.fire(self.mod._tick_id)

    def test_initialization_is_account_scoped_and_footer_failure_is_optional(self):
        self.assertTrue(self.mod.running)
        self.assertEqual(self.mod.active_key, 'EU:7')
        self.assertEqual(len(self.footer_calls), 1)
        self.assertIsNone(self.mod.footer_handle)
        self.assertTrue(self.mod.open_window())
        self.assertTrue(self.window.opened)
        self.assertEqual(len(self.api.events.onBattleResultsReceived.handlers), 1)

    def test_keyboard_toggle_ignores_repeat_and_battle(self):
        self.api.pressed.add(self.api.keys.KEY_LCONTROL)
        event = Obj(key=self.api.keys.KEY_F10)
        self.api.input.onKeyDown(event)
        self.assertTrue(self.window.opened)
        self.api.input.onKeyDown(event)
        self.assertTrue(self.window.opened)
        self.api.input.onKeyUp(event)
        self.api.input.onKeyDown(event)
        self.assertFalse(self.window.opened)
        self.api.input.onKeyUp(event)
        self.begin()
        self.api.input.onKeyDown(event)
        self.assertFalse(self.window.opened)

    def test_wrong_modifiers_and_bad_config_do_not_trigger_shortcut(self):
        event = Obj(key=self.api.keys.KEY_F10)
        self.api.input.onKeyDown(event)
        self.assertFalse(self.window.opened)
        self.api.input.onKeyUp(event)
        self.api.pressed.update((self.api.keys.KEY_LCONTROL, self.api.keys.KEY_LSHIFT))
        self.api.input.onKeyDown(event)
        self.assertFalse(self.window.opened)
        self.assertEqual(self.mod._parse_hotkey('bad-key'), (self.api.keys.KEY_F10, {'CTRL'}))
        self.assertEqual(self.mod._parse_hotkey('SHIFT+F12'), (self.api.keys.KEY_F12, {'SHIFT'}))

    def test_replay_nonplayer_and_other_account_results_are_excluded(self):
        self.api.events.onBattleResultsReceived(False, raw_result())
        self.api.events.onBattleResultsReceived(True, raw_result(dbid=8))
        self.api.replay = True
        self.api.events.onBattleResultsReceived(True, raw_result())
        self.begin()
        self.assertEqual(self.summary()['battles'], 0)
        self.assertEqual(self.mod.active_service.pending_arena_ids(), [])
        self.assertFalse(self.mod.open_window())

    def test_begin_is_saved_and_late_result_keeps_pre_reset_membership(self):
        self.begin()
        self.assertEqual(self.mod.active_service.pending_arena_ids(), [ARENA_ID])
        self.garage()
        self.clock.value += 200
        self.mod.on_action({'action': 'reset'})
        self.api.events.onBattleResultsReceived(True, raw_result())
        self.assertEqual(self.summary()['battles'], 1)
        self.assertEqual(self.summary('manual')['battles'], 0)
        self.assertEqual(self.mod.active_service.pending_arena_ids(), [])

    def test_pending_cache_retries_until_end_and_counts_result_once(self):
        self.begin()
        self.garage()
        self.tick()
        arena_id, receive = self.api.pending_callbacks.pop()
        self.assertEqual(arena_id, ARENA_ID)
        receive(-1, None)
        self.assertEqual(self.summary()['battles'], 0)
        self.tick()
        unused_id, receive = self.api.pending_callbacks.pop()
        receive(1, raw_result())
        self.api.events.onBattleResultsReceived(True, raw_result())
        self.assertEqual(self.summary()['battles'], 1)
        self.assertEqual(self.summary()['xp_base']['sum'], 650)
        self.assertEqual(self.summary()['currencies']['bonds']['net'], 28)
        self.assertEqual(self.mod.active_service.pending_arena_ids(), [])

    def test_two_out_of_order_results_keep_independent_identifiers(self):
        second = str((12346 << 32) | (START + 20))
        self.begin()
        self.begin(second)
        self.garage()
        self.api.events.onBattleResultsReceived(True, raw_result(second))
        self.api.events.onBattleResultsReceived(True, raw_result())
        self.api.events.onBattleResultsReceived(True, raw_result(second))
        self.assertEqual(self.summary()['battles'], 2)
        self.assertEqual(self.summary()['currencies']['credits']['net'], 64000)

    def test_expired_request_callback_cannot_consume_a_newer_retry(self):
        self.begin()
        self.garage()
        self.tick()
        unused_id, original_callback = self.api.pending_callbacks.pop()
        self.tick(seconds=31)
        unused_id, retry_callback = self.api.pending_callbacks.pop()
        key = ('EU:7', ARENA_ID)
        current = self.mod.inflight[key]
        retries = dict(self.mod.retries)
        self.clock.value += 11  # Retry backoff has elapsed, timeout has not.
        for args in ((-1, None), (1, []), ()):
            original_callback(*args)
            self.assertIs(self.mod.inflight[key], current)
            self.mod._poll_one(self.mod.active_service, 'EU:7')
            self.assertEqual(self.api.pending_callbacks, [])
            self.assertEqual(self.mod.retries, retries)
            self.assertEqual(self.summary()['battles'], 0)
        # A valid late stream may be the only copy before the native ACK.
        # Accept its unknown values without consuming the newer request token.
        original_callback(1, raw_result())
        self.assertIs(self.mod.inflight[key], current)
        self.assertEqual(self.mod.retries, retries)
        self.assertEqual(self.summary()['battles'], 1)
        retry_callback(1, raw_result())
        self.assertEqual(self.mod.inflight, {})
        self.assertEqual(self.summary()['battles'], 1)
        original_callback(1, raw_result())
        self.assertEqual(self.summary()['battles'], 1)

    def test_cache_mismatched_arena_and_callback_after_stop_are_ignored(self):
        self.begin()
        self.garage()
        self.tick()
        unused_id, receive = self.api.pending_callbacks.pop()
        wrong = raw_result(str((12346 << 32) | (START + 20)))
        receive(1, wrong)
        self.assertEqual(self.summary()['battles'], 0)
        self.tick()
        unused_id, receive = self.api.pending_callbacks.pop()
        self.mod.stop()
        receive(1, raw_result())
        self.assertEqual(self.summary()['battles'], 0)

    def test_reconnect_reuses_service_and_callback_retains_original_account(self):
        original = self.mod.active_service
        self.api.events.onAccountBecomeNonPlayer()
        self.api.events.onAccountBecomePlayer()
        self.assertIs(self.mod.active_service, original)
        self.begin()
        self.garage()
        self.tick()
        unused_id, receive = self.api.pending_callbacks.pop()
        self.api.dbid = 8
        self.api.events.onAccountBecomePlayer()
        current = self.mod.active_service
        self.assertIsNot(current, original)
        self.assertEqual(self.mod.active_key, 'EU:8')
        receive(1, raw_result())
        self.assertEqual(self.summary(service=original)['battles'], 1)
        self.assertEqual(self.summary(service=current)['battles'], 0)
        self.api.dbid = 7
        self.api.events.onAccountBecomePlayer()
        self.assertIs(self.mod.active_service, original)

    def test_applied_bonus_reconciles_partial_result_and_old_cache_cannot_revert(self):
        self.begin()
        self.garage()
        raw = raw_result()
        del raw['personal'][1]['gold']
        self.api.events.onBattleResultsReceived(True, raw)
        self.assertEqual(self.summary()['xp_received']['sum'], 1950)
        reusable = Obj(personal=Obj(xpProgress={1: {'xp': 3900}}, isAddXPBonusApplied=True))
        bundle = Obj(results=raw, reusable=reusable)
        controller = Obj(getResults=lambda: bundle)
        self.api.posts[ARENA_ID] = bundle
        self.api.results_service.onResultPosted(reusable, controller, None)
        self.assertEqual(self.summary()['xp_received']['sum'], 3900)
        self.assertEqual(self.summary()['xp_base']['sum'], 650)
        self.assertEqual(self.summary()['currencies']['gold']['income_count'], 0)
        self.api.events.onBattleResultsReceived(True, raw)
        self.assertEqual(self.summary()['xp_received']['sum'], 3900)
        # If the native cache is cleared, the ledger's provenance still guards XP.
        self.api.posts.clear()
        self.api.events.onBattleResultsReceived(True, raw)
        self.assertEqual(self.summary()['xp_received']['sum'], 3900)

    def test_bonus_event_refreshes_current_native_controller(self):
        self.begin()
        self.garage()
        self.api.events.onBattleResultsReceived(True, raw_result())
        reusable = Obj(personal=Obj(xpProgress={1: {'xp': 4550}}, isAddXPBonusApplied=True))
        self.api.posts[ARENA_ID] = Obj(results=raw_result(), reusable=reusable)
        self.api.event_bus.emit()
        self.assertIsNotNone(self.mod._bonus_callback_id)
        self.api.fire(self.mod._bonus_callback_id)
        self.assertEqual(self.summary()['xp_received']['sum'], 4550)
        self.assertIsNone(self.mod._bonus_callback_id)

    def test_missing_expected_table_keeps_other_statistics_and_reports_wn8_gap(self):
        self.mod.stop()
        def unavailable(directory):
            raise IOError('fixture absent')
        self.api.load_expected = unavailable
        self.mod.expected_table = None
        self.mod.services = {}
        self.mod.active_key = self.mod.active_service = None
        self.mod.start()
        self.begin()
        self.garage()
        self.api.events.onBattleResultsReceived(True, raw_result())
        stats = self.summary()
        self.assertEqual(stats['battles'], 1)
        self.assertIsNone(stats['wn8'])
        self.assertEqual(stats['currencies']['bonds']['net'], 28)
        self.assertTrue(any('WN8 table' in warning for warning in self.mod.snapshot()['warnings']))

    def test_refresh_uses_pending_cache_and_model_actions_are_limited(self):
        self.begin()
        self.garage()
        self.mod.on_action({'action': 'refresh'})
        self.assertEqual(len(self.api.pending_callbacks), 1)
        self.mod.on_action({'action': 'resize', 'width': '700', 'height': '620'})
        self.assertEqual(self.window.sizes, [('700', '620')])
        self.mod.open_window()
        self.mod.on_action({'action': 'close'})
        self.assertFalse(self.window.opened)
        self.mod.on_action(None)
        self.mod.on_action({'action': '__import__'})
        self.assertEqual(self.summary()['battles'], 0)

    def test_stop_removes_every_subscription_callback_and_footer_handle(self):
        removed = []
        self.mod.footer_handle = Obj(uninstall=lambda: removed.append(True))
        self.mod.stop()
        self.assertEqual(removed, [True])
        for name in self.api.EVENT_NAMES:
            self.assertEqual(getattr(self.api.events, name).handlers, [])
        self.assertEqual(self.api.input.onKeyDown.handlers, [])
        self.assertEqual(self.api.input.onKeyUp.handlers, [])
        self.assertEqual(self.api.results_service.onResultPosted.handlers, [])
        self.assertEqual(self.api.event_bus.handlers, [])
        self.assertEqual(self.api.callbacks, {})
        self.assertFalse(self.window.opened)


class AdapterUtilityTests(unittest.TestCase):
    def test_data_directory_is_outside_versioned_mods_and_never_opens_preferences(self):
        result = runtime.resolve_data_dir(environ={'APPDATA': '/user/roaming'})
        self.assertEqual(result, '/user/roaming/grz_wot_session_stats')
        bw = Obj(wg_getPreferencesFilePath=lambda: '/user/wargaming/preferences.xml')
        self.assertEqual(runtime.resolve_data_dir(bw, {}), '/user/wargaming/grz_session_stats')
        with self.assertRaises(RuntimeError):
            runtime.resolve_data_dir(environ={})

    def test_non_ascii_profile_bytes_are_decoded_before_unicode_path_join(self):
        profile = '/user/Łukasz/roaming'
        encoded = profile.encode(sys.getfilesystemencoding() or 'utf-8')
        self.assertEqual(runtime.resolve_data_dir(environ={'APPDATA': encoded}),
                         profile + '/grz_wot_session_stats')

    def test_expected_table_validation_rejects_nonfinite_and_missing_coefficients(self):
        self.assertTrue(runtime._looks_like_expected(EXPECTED))
        for invalid in (float('nan'), float('inf'), -1, 0, True, None):
            table = copy.deepcopy(EXPECTED)
            table['data'][0]['expDamage'] = invalid
            self.assertFalse(runtime._looks_like_expected(table))
        self.assertFalse(runtime._looks_like_expected({'data': []}))

    def test_cache_adapter_uses_decimal_uint64_id(self):
        called = []
        cache = Obj(get=lambda arena_id, callback: called.append((arena_id, callback)))
        api = runtime.GameAPI.__new__(runtime.GameAPI)
        api.bw = Obj(player=lambda: Obj(battleResultsCache=cache))
        callback = lambda code, raw: None
        self.assertTrue(api.request_result(ARENA_ID, callback))
        self.assertEqual(called, [(int(ARENA_ID), callback)])


class NativeBindingTests(unittest.TestCase):
    """Exercise native construction contracts with strict Wulf doubles, not a browser."""

    def setUp(self):
        self.modules = {}
        self.log_level = logging.root.manager.disable
        logging.disable(logging.CRITICAL)
        self.status = Obj(LOADING=0, LOADED=1, DESTROYING=2, DESTROYED=3)
        status = self.status

        class FakeModel(object):
            def __init__(self, properties=0, commands=0):
                self.props = []
                self.commands = []
                self._initialize()
                if len(self.props) != properties or len(self.commands) != commands:
                    raise AssertionError('Native model allocation mismatch')
            def _initialize(self):
                pass
            def _addStringProperty(self, key, value):
                self.props.append((key, value))
            def _addViewModelProperty(self, key, value):
                self.props.append((key, value))
            def _addCommand(self, key):
                command = FakeEvent()
                self.commands.append((key, command))
                return command
            def _setString(self, index, value):
                self.props[index] = (self.props[index][0], value)
            def transaction(self):
                return self
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return False

        class FakeView(object):
            def __init__(self, settings):
                self.settings = settings

        class FakeWindowNative(object):
            def __init__(self, flags, content, layer, name, parent):
                self.flags, self.content, self.layer, self.name = flags, content, layer, name
                self.native_parent = parent
                # Window.parent returns the binding's object directly. It may
                # have windowSize but not the Python Window.size property.
                self.parent = Obj(windowSize=parent.size)
                self.proxy = object()
                self.uniqueID = id(self)
                self.windowStatus = status.LOADING
                self.shown = False
                self.position = None
                self.size = (700, 620)
                self.onSizeChanged = FakeEvent()
                self.onPositionChanged = FakeEvent()
                self.onStatusChanged = FakeEvent()
                self.calls = []
                self.accept_center = True
                self.accept_move = True
                self.clamp_moves_to_surface = False
            def load(self):
                self.windowStatus = status.LOADED
                self.onStatusChanged(status.LOADED)
                self._onReady()
            def show(self, focus):
                self.shown = focus
                self.calls.append('show')
            def center(self):
                self.calls.append('center')
                # Acceptance is deliberately not proof of an observed target.
                return self.accept_center
            def move(self, x, y):
                self.calls.append('move')
                if self.accept_move:
                    if self.clamp_moves_to_surface:
                        x = min(x, max(0, self.native_parent.size[0] - self.size[0]))
                        y = min(y, max(0, self.native_parent.size[1] - self.size[1]))
                    self.position = (x, y)
                    self.onPositionChanged(self.uniqueID, x, y)
                return self.accept_move
            def drag_surface(self, x, y):
                self.position = (x, y)
                self.onPositionChanged(self.uniqueID, x, y)
            def resize_surface(self, width, height):
                self.size = (width, height)
                self.onSizeChanged(self.uniqueID, width, height)
            def destroy(self):
                self.windowStatus = status.DESTROYING
                # Actual Wulf event has ONE status argument.
                self.onStatusChanged(status.DESTROYING)
                self.proxy = None
                self.windowStatus = status.DESTROYED
                self.onStatusChanged(status.DESTROYED)
                self.onSizeChanged.handlers[:] = []
                self.onPositionChanged.handlers[:] = []
                self.onStatusChanged.handlers[:] = []

        class FakeComponent(object):
            next_id = 100
            def __init__(self, model=None):
                self.model = model() if model is not None else None
                self.children = {}
                self.uniqueID = FakeComponent.next_id
                FakeComponent.next_id += 1
                self.original_calls = 0
            def _onLoading(self, *args, **kwargs):
                self.original_calls += 1
            def getChildView(self, position):
                return self.children.get(position)
            def _registerChild(self, position, child):
                self.children[position] = child
            def _unregisterChild(self, unique_id, destroy):
                for position, child in list(self.children.items()):
                    if child.uniqueID == unique_id:
                        self.children.pop(position)

        self.component = FakeComponent
        self.main = Obj(proxy=object(), windowStatus=status.LOADED, size=(1920, 1080),
                        onSizeChanged=FakeEvent())
        self.loader = Obj(windowsManager=Obj(getMainWindow=lambda: self.main), scale=1.0)
        self.timer = FakeAPI()
        resource = Obj(mods=Obj(grz=Obj(sessionstats=Obj(views=Obj(SessionStats=lambda: 54321)))))
        self.resource = resource
        self.inject_module('frameworks.wulf', ViewModel=FakeModel, ViewFlags=Obj(VIEW=1),
                           ViewSettings=lambda **kwargs: Obj(**kwargs), WindowFlags=Obj(WINDOW=1),
                           WindowLayer=Obj(WINDOW=7), WindowStatus=status)
        self.inject_module('gui.impl.pub', ViewImpl=FakeView, WindowImpl=FakeWindowNative)
        self.inject_module('gui.impl.pub.view_component', ViewComponent=FakeComponent)
        self.inject_module('gui.impl.gen', R=resource)
        self.inject_module('helpers', dependency=Obj(instance=lambda interface: self.loader))
        self.inject_module('skeletons.gui.impl', IGuiLoader=object)
        self.inject_module('BigWorld', callback=self.timer.schedule, cancelCallback=self.timer.cancel)
        self.stats = {'version': VERSION, 'scopes': {}, 'warnings': []}
        self.actions = []
        self.window = views.StatsWindow(lambda: self.stats, self.actions.append)

    def inject_module(self, name, **attributes):
        if '.' in name:
            parent_name, child_name = name.rsplit('.', 1)
            if parent_name not in sys.modules:
                self.inject_module(parent_name)
        if name not in self.modules:
            self.modules[name] = sys.modules.get(name)
        module = types.ModuleType(str(name))
        module.__path__ = []
        module.__dict__.update(attributes)
        sys.modules[name] = module
        if '.' in name:
            setattr(sys.modules[parent_name], child_name, module)
        return module

    def tearDown(self):
        self.window.close()
        if footer._installed is not None:
            footer._installed.uninstall()
        for name, old in self.modules.items():
            if old is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = old
        logging.disable(self.log_level)

    def test_registered_native_window_lifetime_model_updates_and_centering(self):
        self.assertTrue(self.window.open())
        native = self.window._window
        self.assertEqual(native.content.settings.layoutID, 54321)
        self.assertEqual(native.layer, 7)
        self.assertTrue(native.shown)
        # Placement is independent of the renderer sending an action back.
        self.assertEqual(native.calls[:2], ['move', 'show'])
        self.assertEqual(native.position, (610, 230))
        payload = json.loads(self.window._model.props[0][1])
        self.assertEqual(payload['viewport'], {'width': 1920, 'height': 1080, 'scale': 1.0})
        self.window._model.onAction({'action': 'refresh'})
        self.assertEqual(self.actions, [{'action': 'refresh'}])
        self.stats['warnings'] = ['Probe']
        self.window.refresh()
        self.assertEqual(json.loads(self.window._model.props[0][1])['warnings'], ['Probe'])
        self.window.resize('700', '620')
        self.assertEqual(native.position, (610, 230))
        self.window.resize('nan', '620')
        self.assertEqual(native.position, (610, 230))
        self.window.close()
        self.assertIsNone(native.proxy)
        self.assertFalse(self.window.is_open())
        self.assertTrue(self.window.open())
        self.assertIsNot(self.window._window, native)

    def test_native_surface_event_recenters_without_renderer_command(self):
        self.assertTrue(self.window.open())
        native = self.window._window
        native.resize_surface(1000, 700)
        self.assertEqual(native.position, (460, 190))
        self.assertEqual(self.actions, [])
        before = len(native.calls)
        native.resize_surface(1000, 700)
        self.assertEqual(len(native.calls), before)

    def test_explicit_parent_bounds_and_resolved_scale_survive_native_parent_proxy(self):
        self.assertTrue(self.window.open())
        native = self.window._window
        self.assertFalse(hasattr(native.parent, 'size'))
        native.accept_center = False
        self.main.size = (1280, 800)
        self.loader.scale = 1.25
        self.main.onSizeChanged(99, 1280, 800)
        self.assertEqual(native.position, (290, 90))
        payload = json.loads(self.window._model.props[0][1])
        self.assertEqual(payload['viewport'], {'width': 1280, 'height': 800, 'scale': 1.25})
        # Scale can change without a physical parent resize. The HTML event
        # asks Python for its current resolved value rather than echoing one.
        self.loader.scale = 1.5
        self.window._model.onAction({'action': 'viewport'})
        self.assertEqual(json.loads(self.window._model.props[0][1])['viewport']['scale'], 1.5)

    def test_renderer_measurement_positions_pending_texture_and_rejects_invalid_sizes(self):
        self.assertTrue(self.window.open())
        native = self.window._window
        self.window._model.onAction({'action': 'resize', 'width': '1024', 'height': '720'})
        # The author pattern uses the measured DOM size for placement while
        # texture resizing completes independently. No Python size setter.
        self.assertEqual(native.position, (448, 180))
        self.assertEqual(native.size, (700, 620))
        for width in ('nan', 'inf', '-1', '0', '999999999999999', True, None):
            self.window.resize(width, 620)
            self.assertEqual(native.position, (448, 180))
        native.resize_surface(1024, 720)
        self.assertEqual(native.position, (448, 180))

    def test_fullscreen_bootstrap_is_not_mistaken_for_final_panel_geometry(self):
        self.assertTrue(self.window.open())
        native = self.window._window
        native.clamp_moves_to_surface = True
        native.resize_surface(1920, 1080)
        self.window._model.onAction({'action': 'resize', 'width': '700', 'height': '620'})
        # Simulate a native area which accepts requests but clamps a still
        # full-screen texture to (0,0). Renderer ready is not geometry ready.
        self.assertEqual(native.position, (0, 0))
        for stage in views.DIAGNOSTIC_STAGES:
            self.window._model.onAction({'action': 'diagnostic', 'stage': stage})
        self.assertEqual(len(self.timer.callbacks), 1)
        native.resize_surface(700, 620)
        self.assertEqual(native.position, (610, 230))
        self.assertEqual(self.timer.callbacks, {})
        self.assertNotIn('center', native.calls)

    def test_native_drag_preserves_position_through_model_surface_scale_and_reopen(self):
        self.assertTrue(self.window.open())
        native = self.window._window
        model = self.window._model
        model.onAction({'action': 'resize', 'width': '700', 'height': '620'})
        model.onAction({'action': 'drag', 'active': 'true'})
        native.drag_surface(150, 75)
        self.window.refresh()
        model.onAction({'action': 'resize', 'width': '800', 'height': '640'})
        native.resize_surface(800, 640)
        self.assertEqual(native.position, (150, 75))
        model.onAction({'action': 'drag', 'active': 'false'})
        for unused in range(3):
            self.window.refresh()
            self.window.open()
            model.onAction({'action': 'resize', 'width': '800', 'height': '640'})
        self.main.size = (1600, 900)
        self.loader.scale = 1.25
        self.main.onSizeChanged(99, 1600, 900)
        model.onAction({'action': 'viewport'})
        self.assertEqual(native.position, (150, 75))
        self.assertEqual(self.actions, [])

    def test_drag_keeps_title_accessible_after_smaller_parent_without_recentering(self):
        self.assertTrue(self.window.open())
        native = self.window._window
        model = self.window._model
        model.onAction({'action': 'resize', 'width': '700', 'height': '620'})
        model.onAction({'action': 'drag', 'active': True})
        native.drag_surface(900, 600)
        self.main.size = (1024, 768)
        self.main.onSizeChanged(99, 1024, 768)
        # Do not fight the client's active mouse operation.
        self.assertEqual(native.position, (900, 600))
        model.onAction({'action': 'drag', 'active': False})
        self.assertEqual(native.position, (324, 148))
        self.window.refresh()
        self.assertEqual(native.position, (324, 148))
        self.window.close()
        self.assertEqual(native.onPositionChanged.handlers, [])
        self.assertTrue(self.window.open())
        current = self.window._window
        model.onAction({'action': 'drag', 'active': True})
        current.resize_surface(600, 500)
        self.assertEqual(current.position, (212, 134))

    def test_close_command_and_native_teardown_release_subscriptions_and_timers(self):
        self.assertTrue(self.window.open())
        native = self.window._window
        old_model = self.window._model
        self.assertEqual(len(self.main.onSizeChanged.handlers), 1)
        self.assertEqual(len(self.timer.callbacks), 1)
        old_model.onAction({'action': 'close'})
        self.assertFalse(self.window.is_open())
        self.assertIsNone(native.proxy)
        self.assertEqual(self.main.onSizeChanged.handlers, [])
        self.assertEqual(self.timer.callbacks, {})
        self.assertEqual(self.actions, [])
        self.assertTrue(self.window.open())
        new = self.window._window
        old_model.onAction({'action': 'close'})
        self.assertIs(self.window._window, new)
        native.shown = False
        native._onReady()
        self.assertFalse(native.shown)
        # Lobby teardown uses a single-argument native status event, not the
        # close action. The same cleanup must happen there.
        new.destroy()
        self.assertFalse(self.window.is_open())
        self.assertEqual(self.main.onSizeChanged.handlers, [])
        self.assertEqual(self.timer.callbacks, {})

    def test_early_resize_waits_for_ready_and_refused_placement_is_not_cached(self):
        self.assertTrue(self.window.open())
        native = self.window._window
        before = len(native.calls)
        native.windowStatus = self.status.LOADING
        native.resize_surface(900, 680)
        self.assertEqual(len(native.calls), before)
        native.windowStatus = self.status.LOADED
        native._onReady()
        self.assertEqual(native.position, (510, 200))
        native.accept_center = native.accept_move = False
        native.resize_surface(1000, 700)
        self.assertEqual(native.position, (510, 200))
        self.assertFalse(self.window._center('test_refused'))
        native.accept_move = True
        self.assertTrue(self.window._center('test_recovered'))
        self.assertEqual(native.position, (460, 190))

    def test_renderer_handshake_is_bounded_and_cancels_timeout(self):
        records = []
        class Capture(logging.Handler):
            def emit(self, record):
                records.append(record.getMessage())
        handler = Capture()
        old_level = views.LOG.level
        logging.disable(logging.NOTSET)
        views.LOG.setLevel(logging.INFO)
        views.LOG.addHandler(handler)
        try:
            self.assertTrue(self.window.open())
            model = self.window._model
            model.onAction({'action': 'resize', 'width': '700', 'height': '620'})
            for stage in ('dom_ready', 'model_bound', 'layout_ready'):
                for unused in range(5):
                    model.onAction({'action': 'diagnostic', 'stage': stage,
                                    'width': '700', 'height': '620', 'scale': '1'})
            self.assertEqual(self.timer.callbacks, {})
            self.assertEqual(len([line for line in records if 'GRZ UI: renderer ' in line]), 3)
            self.assertEqual(self.actions, [])
            self.window.close()
            self.assertTrue(self.window.open())
            for callback_id in list(self.timer.callbacks):
                self.timer.fire(callback_id)
            self.assertEqual(len([line for line in records if 'handshake incomplete' in line]), 1)
            self.assertEqual(self.timer.callbacks, {})
        finally:
            views.LOG.removeHandler(handler)
            views.LOG.setLevel(old_level)
            logging.disable(logging.CRITICAL)

    def test_missing_native_resource_fails_honestly_without_fallback_demo(self):
        del self.resource.mods.grz.sessionstats.views.SessionStats
        self.assertFalse(self.window.open())
        self.assertFalse(self.window.is_open())
        self.assertIsNone(self.window._model)

    def test_stale_destroyed_window_is_rebuilt_after_lobby_reload(self):
        self.assertTrue(self.window.open())
        old = self.window._window
        old.proxy = None
        old.windowStatus = self.status.DESTROYED
        self.assertFalse(self.window.is_open())
        self.assertTrue(self.window.open())
        self.assertIsNot(self.window._window, old)

    def test_command_exception_does_not_leave_native_dispatch(self):
        def fail(arg):
            raise RuntimeError('fixture handler failure')
        model = views.build_model_class()('{}', fail)
        model.onAction({'action': 'refresh'})

    def fake_inject(self, model, name, styles=None, modules=None):
        self.assertEqual(name, 'grz_session_stats_footer')
        self.assertEqual(modules, ['coui://gui/gameface/mods/grz_session_stats/footer.js'])
        self.assertEqual(styles, ['coui://gui/gameface/mods/grz_session_stats/footer.css'])
        model._addViewModelProperty('ModInjectModel', Obj())

    def test_footer_is_separate_child_model_and_teardown_restores_inherited_method(self):
        class LobbyFooter(self.component):
            pass
        self.inject_module('openwg_gameface', gf_mod_inject=self.fake_inject)
        self.inject_module('gui.impl.lobby.page.lobby_footer', LobbyFooter=LobbyFooter)
        opened = []
        handle = footer.install(lambda: opened.append(True))
        self.assertIsNotNone(handle)
        lobby = LobbyFooter()
        lobby._onLoading()
        self.assertEqual(lobby.original_calls, 1)
        child = lobby.getChildView(footer.POSITION_ID)
        self.assertIsNotNone(child)
        self.assertEqual([item[0] for item in child.model.props], ['ModInjectModel', 'grzSessionFooter'])
        commands = child.model.props[1][1]
        commands.onAction({'action': 'open'})
        self.assertEqual(opened, [True])
        commands.onAction({'action': 'reset'})
        self.assertEqual(opened, [True])
        handle.uninstall()
        self.assertEqual(lobby.children, {})
        self.assertNotIn('_onLoading', LobbyFooter.__dict__)
        commands.onAction({'action': 'open'})
        self.assertEqual(opened, [True])

    def test_footer_does_not_displace_collision_or_clobber_later_mod_wrapper(self):
        class LobbyFooter(self.component):
            pass
        opened = []
        child = footer.build_child_class(self.fake_inject, lambda: opened.append(True))
        handle = footer.FooterInstallation(LobbyFooter, child, lambda: None)
        lobby = LobbyFooter()
        sentinel = self.component()
        lobby.children[footer.POSITION_ID] = sentinel
        lobby._onLoading()
        self.assertIs(lobby.getChildView(footer.POSITION_ID), sentinel)
        ours = LobbyFooter._onLoading
        def another_mod(view, *args, **kwargs):
            ours(view, *args, **kwargs)
        LobbyFooter._onLoading = another_mod
        handle.uninstall()
        self.assertIs(LobbyFooter.__dict__['_onLoading'], another_mod)
        another = LobbyFooter()
        another._onLoading()
        self.assertEqual(another.children, {})


if __name__ == '__main__':
    unittest.main()
