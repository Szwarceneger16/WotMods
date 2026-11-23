# -*- coding: ascii -*-
"""Owned lifecycle, input polling and configuration for the rangefinder."""
from __future__ import absolute_import

import json
import logging
import os
import time

from . import VERSION, battle_activity, preview_catalog
from .core import SettingsStore, validate_config, with_mode_position
from .hud import ClickTracker, Overlay, finite
from .preview_catalog import translations
from .stock_rangefinder import StockRangefinder

try:
    text_types = (basestring,)
except NameError:
    text_types = (str,)

TICK_SECONDS = 0.10
INTERACTION_SECONDS = 0.05
DISABLED_IDLE_SECONDS = 0.25
MEASUREMENT_SECONDS = 0.10
POSITION_SECONDS = 0.033
SETTINGS_PUBLISH_SECONDS = 0.50
MAX_COMMAND_CHARS = 4096
PROBE_DIAGNOSTICS = frozenset((
    'measurement_failed', 'measurement_api_unavailable',
    'controllers_unavailable', 'vehicle_context_unavailable',
    'aim_unavailable', 'origin_unavailable', 'ray_unavailable',
    'intersection_unavailable', 'intersection_outside_ray',
    'collision_data_unavailable', 'target_unavailable',
    'target_visibility_unavailable', 'target_state_unavailable',
    'target_position_unavailable', 'distance_unavailable',
))


def config_directory():
    base = os.environ.get('APPDATA') or os.environ.get('LOCALAPPDATA')
    if base:
        return os.path.join(base, 'GRZ_Rangefinder')
    return os.path.abspath(os.path.join('mods', 'configs', 'grz_rangefinder'))


class Diagnostics(object):
    """Small category-only log; no coordinates, player names or game payloads."""
    def __init__(self, directory):
        self.logger = logging.getLogger('grz.rangefinder.private')
        self.logger.setLevel(logging.INFO)
        self.logger.propagate = False
        self.handler = None
        self.counts = {}
        self.in_battle = False
        self.queued = []
        try:
            if not os.path.isdir(directory):
                os.makedirs(directory)
            from logging.handlers import RotatingFileHandler
            path = os.path.join(directory, 'rangefinder.log')
            if not os.path.islink(path) and not os.path.islink(directory):
                self.handler = RotatingFileHandler(path, maxBytes=262144, backupCount=1)
                self.handler.setFormatter(logging.Formatter('%(asctime)s %(message)s'))
                self.logger.addHandler(self.handler)
        except Exception:
            self.handler = None

    def __call__(self, code):
        if not isinstance(code, text_types) or len(code) > 96:
            code = 'invalid_log_category'
        count = self.counts.get(code, 0)
        self.counts[code] = count + 1
        if count < 4:
            if self.in_battle:
                if len(self.queued) < 64:
                    self.queued.append(code)
            else:
                self._write(code)

    def _write(self, code):
        try:
            self.logger.info('v%s %s', VERSION, code)
        except Exception:
            pass

    def set_battle(self, active):
        self.in_battle = active
        if not active and self.queued:
            queued, self.queued = self.queued, []
            for code in queued:
                self._write(code)

    def close(self):
        self.set_battle(False)
        if self.handler is not None:
            self.logger.removeHandler(self.handler)
            try:
                self.handler.close()
            except Exception:
                pass
            self.handler = None


class Runtime(object):
    def __init__(self, world, gui, keys, probe, store, resource_exists,
                 window_factory=None, app_getter=None, chat_focused=None,
                 log=None, clock=None, language_getter=None, hotkey_unbound=None, preview_diagnostics=None):
        self.world, self.gui, self.keys = world, gui, keys
        self.probe, self.store = probe, store
        self.log = log or (lambda code: None)
        self.preview_diagnostics = preview_diagnostics
        self.clock = clock or time.time
        self.window_factory = window_factory
        self.app_getter = app_getter or self._native_application
        self.chat_focused = chat_focused or self._native_chat_focused
        self.language_getter = language_getter or self._native_language
        self.hotkey_unbound = hotkey_unbound or self._native_hotkey_unbound
        self.overlay = Overlay(gui, world, resource_exists, self.log, clock=self.clock)
        self._stock_rangefinder = StockRangefinder()
        self._stock_requested = False
        self._stock_syncing = False
        self._stock_rangefinder.start(self._application, self._stock_status_changed)
        self.window = None
        self.footer = None
        self.running = False
        self.generation = 0
        self.context_epoch = 0
        self.callback = None
        self._timer_token = 0
        self._wake_queued = False
        self._rebind_requested = False
        self._position_callback = None
        self._position_tracking = False
        self._pending_position = None
        self.battle_events = []
        self.pending = []
        self.events = []
        self.panel = None
        self._avatar = None
        self._arena = None
        self._sample = {'context': 'unavailable', 'battle_eligible': False,
                        'available': False, 'distance_m': None, 'kind': 'none',
                        'viewport': (0, 0), 'reason': 'not_started'}
        self._sample_time = None
        self._sample_measured = False
        self._language_cache = None
        self._language_cache_getter = None
        self._language_cache_epoch = None
        self._last_context = 'unavailable'
        self._clicks = ClickTracker()
        self._drag = None
        self._drag_owner_token = object()
        self._hotkey_down = None
        self._status = ''
        self._error = ''
        self._error_streak = 0
        self._settings_session = 0
        self._settings_publish_at = None
        self._load_issue = False
        self._idle_suspended = False

    @staticmethod
    def _native_application(context):
        from helpers import dependency
        from skeletons.gui.app_loader import IAppLoader
        loader = dependency.instance(IAppLoader)
        return loader.getDefBattleApp() if context == 'battle' else loader.getDefLobbyApp()

    @staticmethod
    def _native_chat_focused():
        try:
            from messenger import MessengerEntry
            return bool(MessengerEntry.g_instance.gui.isFocused())
        except Exception:
            return True

    @staticmethod
    def _native_language():
        try:
            from helpers import getClientLanguage
            return getClientLanguage()
        except Exception:
            return 'en'

    def _native_hotkey_unbound(self):
        """Read the verified complete map; never override a user's game key."""
        try:
            import CommandMapping
            mapping = getattr(CommandMapping.g_instance, '_CommandMapping__mapping', None)
            if type(mapping) is not dict:
                return False
            key = self.keys.KEY_F10
            if key not in mapping:
                return True
            commands = mapping[key]
            return type(commands) in (tuple, list) and not commands
        except Exception:
            return False

    def language(self):
        # Client language normally lasts for the process lifetime. Refresh on
        # context changes, or if an injected getter is deliberately replaced.
        if (self._language_cache_getter is self.language_getter and
                self._language_cache_epoch == self.context_epoch):
            return self._language_cache
        try:
            value = translations.language_code(self.language_getter())
        except Exception:
            value = 'en'
        self._language_cache = value
        self._language_cache_getter = self.language_getter
        self._language_cache_epoch = self.context_epoch
        return value

    def _application(self):
        try:
            app = self.app_getter(self._sample.get('context'))
            if app is None or getattr(app, 'initialized', True) is False:
                return None
            return app
        except Exception:
            return None

    def _modal(self):
        app = self._application()
        if app is None:
            return True
        try:
            query = getattr(app, 'isModalViewShown', None)
            return bool(query()) if callable(query) else True
        except Exception:
            return True

    def _window_open(self):
        try:
            return bool(self.window is not None and self.window.is_open())
        except Exception:
            return False

    def _hud_visible(self):
        context = self._sample.get('context')
        if context == 'garage':
            return not self._modal()
        if context != 'battle' or self.panel is None:
            return False
        try:
            from constants import ARENA_PERIOD
            avatar = self.world.player()
            if avatar is not self._avatar or getattr(avatar.arena, 'period', None) != ARENA_PERIOD.BATTLE:
                return False
            visible = self.panel.as_isVisibleS()
            return visible in (True, 1) and not self._modal()
        except Exception:
            return False

    def _ctrl_held(self):
        try:
            return bool(self.world.isKeyDown(self.keys.KEY_LCONTROL) or
                        self.world.isKeyDown(self.keys.KEY_RCONTROL))
        except Exception:
            return False

    def _interaction_allowed(self, require_cursor=True, cursor=None,
                             ctrl=None, visible=None):
        context = self._sample.get('context')
        if not self.running or context not in ('battle', 'garage'):
            return False
        if require_cursor and context == 'battle':
            held = self._ctrl_held() if ctrl is None else bool(ctrl)
            if not held:
                return False
        if self._window_open():
            return False
        # _hud_visible already includes app/modal checks. Deferred controls use
        # a fresh query; the polling tick can reuse its one visibility result.
        if not (self._hud_visible() if visible is None else visible):
            return False
        if self.chat_focused():
            return False
        if require_cursor:
            cursor = self.gui.mcursor() if cursor is None else cursor
            return bool(cursor.active and cursor.visible)
        return True

    def payload(self):
        language = self.language()
        return json.dumps({'version': VERSION, 'config': dict(self.store.data),
                           'language': language, 'context': self._sample.get('context'),
                           'preview_choices': preview_catalog.choices(language),
                           'status': self._status, 'error': self._error},
                          ensure_ascii=True, allow_nan=False, sort_keys=True,
                          separators=(',', ':'))

    def _publish(self):
        window = self.window if self._window_open() else None
        if self.footer is None and window is None:
            return
        # Serialize once for both owned consumers, never for a closed form.
        payload = self.payload()
        if self.footer is not None:
            try:
                self.footer.update(payload)
            except Exception:
                self.log('garage_update_failed')
        if window is not None:
            try:
                window.update(payload)
            except Exception:
                self.log('settings_update_failed')
        self._settings_publish_at = self.clock()

    def _defer(self, function, fence_context=True):
        generation, epoch = self.generation, self.context_epoch
        try:
            player = self.world.player()
            arena = getattr(player, 'arena', None)
        except Exception:
            self.log('deferred_context_unavailable')
            return False
        pending = {'id': None}
        self.pending.append(pending)

        def apply():
            if pending not in self.pending:
                return
            self.pending.remove(pending)
            if (not self.running or generation != self.generation or
                    (fence_context and epoch != self.context_epoch)):
                return
            try:
                if fence_context:
                    current = self.world.player()
                    if current is not player or getattr(current, 'arena', None) is not arena:
                        return
                function()
            except Exception:
                self.log('deferred_action_failed')
        try:
            pending['id'] = self.world.callback(0.0, apply)
            return True
        except Exception:
            self.pending.remove(pending)
            self.log('deferred_action_unavailable')
            return False

    def _save(self, config):
        self._cancel_drag()
        was_enabled = bool(self.store.data['enabled'])
        if self.store.save(config):
            self._load_issue = False
            self._status = translations.message('saved', self.language())
            self._error = ''
            self.log('settings_saved')
            if not (self.store.data['enabled'] and self.store.data['hide_stock_rangefinder']):
                self._sync_stock(False)
                if self._sample.get('mode') in ('strategic', 'arty'):
                    self.overlay.hide()
                    self._position_tracking = False
            if self._arena is not None:
                self._battle_wakeup()
            if not was_enabled or not self.store.data['enabled']:
                self._sample_time = None
                self._sample_measured = False
            if not self.store.data['enabled']:
                # Stop the native overlay immediately, including a disable
                # accepted between timer ticks. Old readings cannot survive
                # until the next lightweight context refresh.
                self.overlay.suspend()
                self._idle_suspended = True
                self._sample = dict(self._sample, available=False,
                                    distance_m=None, kind='none')
            self._publish()
            return True
        self._status = ''
        self._error = translations.message('save_failed', self.language())
        self.log('settings_save_failed')
        self._publish()
        return False

    def dispatch(self, argument):
        """Copy only bounded command fields; native dispatch never destroys GUI."""
        if not self.running or not self._window_open():
            return False
        try:
            getter = getattr(argument, 'get', None)
            if not callable(getter):
                return False
            action = getter('action')
            if action == 'close':
                session, window = self._settings_session, self.window
                def close():
                    if self._settings_session == session and self.window is window:
                        self._close_window()
                return self._defer(close)
            if action != 'apply':
                return False
            serialized = getter('settings')
            if not isinstance(serialized, text_types) or len(serialized) > MAX_COMMAND_CHARS:
                return False
            raw = json.loads(serialized)
            config = validate_config(raw, strict=True)
            window = self.window
            session = self._settings_session

            def save():
                if (self.window is window and session == self._settings_session and
                        self._window_open()):
                    self._save(config)
            return self._defer(save)
        except Exception:
            self.log('settings_command_rejected')
            self._error = translations.message('invalid_settings', self.language())
            self._publish()
            return False

    def _close_window(self):
        self._cancel_drag()
        self._settings_session += 1
        self._settings_publish_at = None
        if self.window is not None:
            self.window.close(notify=False)
        self._clicks.reset()

    def _footer_action(self, command):
        if not self.running or self._sample.get('context') != 'garage':
            return False
        return self._defer(lambda: self._open_window(
            command.get('anchorX', 0.96), command.get('anchorY')))

    def _open_window(self, anchor=None, anchor_y=None):
        if self._window_open():
            self._close_window()
            return
        if not self._interaction_allowed(require_cursor=False):
            return
        if self.window is None:
            if self.window_factory is None:
                from .views import SettingsWindow
                self.window = SettingsWindow(self.dispatch, self.payload,
                                             on_diagnostic=self.preview_diagnostics)
            else:
                self.window = self.window_factory(self.dispatch, self.payload)
        self._settings_session += 1
        self._settings_publish_at = None
        self._status = ''
        self._error = (translations.message('load_failed', self.language()) % 'rangefinder.log'
                       if self._load_issue else '')
        if anchor is None:
            anchor = 0.96 if self._sample.get('context') == 'garage' else 0.5
            anchor_y = None if self._sample.get('context') == 'garage' else 0.78
        if not self.window.open(anchor, anchor_y):
            self.log('settings_window_unavailable')
            self._error = translations.message('window_unavailable', self.language())
        else:
            self._cancel_position()
            self.overlay.hide()
            self._sync_stock(False)
            self.log('settings_window_opened')
        self._clicks.reset()

    def _control(self, action):
        if not self._interaction_allowed():
            return
        cursor = self.gui.mcursor()
        if self.overlay.hit_test(cursor.position) != action:
            return
        if action == 'settings':
            self._open_window()
        elif action == 'toggle':
            config = dict(self.store.data)
            config['enabled'] = not config['enabled']
            self._save(config)

    def _cancel_drag(self):
        self._drag = None
        self._clicks.reset()
        try:
            if getattr(self.world, '_grz_hud_drag_owner', None) is self._drag_owner_token:
                self.world._grz_hud_drag_owner = None
        except Exception:
            self.log('drag_owner_release_unavailable')

    def _claim_drag(self):
        # A shared, namespaced Python token prevents both independent mods
        # dragging at once when their grips happen to overlap.
        try:
            owner = getattr(self.world, '_grz_hud_drag_owner', None)
            if owner is not None and owner is not self._drag_owner_token:
                return False
            self.world._grz_hud_drag_owner = self._drag_owner_token
            return self.world._grz_hud_drag_owner is self._drag_owner_token
        except Exception:
            self.log('drag_owner_unavailable')
            return False

    def _display_config(self):
        drag = self._drag
        if drag is not None:
            return with_mode_position(self.store.data, drag['mode'], *drag['offset'])
        return self.store.data

    @staticmethod
    def _cursor_pixels(cursor, viewport):
        try:
            x, y = cursor.position
            width, height = viewport
            if (not all(finite(value) for value in (x, y, width, height)) or
                    width <= 0 or height <= 0 or abs(x) > 2 or abs(y) > 2):
                return None
            return ((x + 1) * width / 2.0, (1 - y) * height / 2.0)
        except Exception:
            return None

    def _placement_input(self, cursor, down, active, hovered):
        """Poll a Ctrl-only drag; persist one owned position on mouse release."""
        drag = self._drag
        pressed = (active and down and self._clicks.was_active and
                   self._clicks.previous is False)
        if drag is None and not (pressed and hovered == 'move' and
                                 self.store.data['enabled']):
            return False
        # Copy placement geometry only when starting or continuing a drag.
        geometry = self.overlay.placement() if active else None
        if drag is not None:
            valid = (active and self.store.data['enabled'] and geometry is not None and
                     geometry['mode'] == drag['mode'] and
                     tuple(geometry['viewport']) == drag['viewport'] and
                     geometry['scale'] == drag['scale'] and
                     self.context_epoch == drag['epoch'])
            if not valid:
                self._cancel_drag()
                return True
            if drag['released']:
                # The zero-delay commit owns the accepted drop. Do not queue
                # another save or turn the release into a normal button click.
                return True
            point = self._cursor_pixels(cursor, drag['viewport'])
            if point is None:
                self._cancel_drag()
                return True
            left, top, right, bottom = geometry['bounds']
            center = (max(left, min(right, point[0] - drag['grab'][0])),
                      max(top, min(bottom, point[1] - drag['grab'][1])))
            anchor, scale = geometry['anchor'], geometry['scale']
            drag['offset'] = tuple(max(-32768, min(32768, int(round(
                (center[index] - anchor[index]) / scale)))) for index in (0, 1))
            self.overlay.hover('move')
            if not down:
                drag['released'] = True

                def commit():
                    if self._drag is not drag:
                        return
                    if (self.context_epoch != drag['epoch'] or
                            self._sample.get('mode', 'unknown') != drag['mode']):
                        self._cancel_drag()
                        return
                    # Merge only this mode into the latest settings. A queued
                    # drop must not restore older values for another camera.
                    config = with_mode_position(self.store.data, drag['mode'],
                                                *drag['offset'])
                    if self._save(config):
                        self.log('position_saved')
                if not self._defer(commit):
                    self._cancel_drag()
            return True
        if (pressed and hovered == 'move' and self.store.data['enabled'] and
                geometry is not None):
            point = self._cursor_pixels(cursor, geometry['viewport'])
            if point is None:
                return False
            if not self._claim_drag():
                self._clicks.reset()
                return True
            self._drag = {'mode': geometry['mode'],
                          'viewport': tuple(geometry['viewport']),
                          'scale': geometry['scale'], 'epoch': self.context_epoch,
                          'offset': tuple(max(-32768, min(32768, int(round(value))))
                                          for value in geometry['offset']),
                          'released': False,
                          'grab': tuple(point[index] - geometry['center'][index]
                                        for index in (0, 1))}
            self._clicks.reset()
            self.overlay.hover('move')
            return True
        return False

    def _poll_input(self, ctrl=None, cursor=None, active=None):
        try:
            ctrl = self._ctrl_held() if ctrl is None else bool(ctrl)
            if not ctrl:
                # Native settings own their input surface. With Ctrl up there
                # is no HUD interaction to poll, even while the feature runs.
                self._cancel_drag()
                self._hotkey_down = False
                return
            cursor = self.gui.mcursor() if cursor is None else cursor
            active = (self._interaction_allowed(cursor=cursor, ctrl=ctrl)
                      if active is None else bool(active))
            hovered = self.overlay.hit_test(cursor.position) if active else None
            down = bool(self.world.isKeyDown(self.keys.KEY_LEFTMOUSE))
            if self._placement_input(cursor, down, active, hovered):
                return
            action = self._clicks.update(down, active, hovered)
            self.overlay.hover(hovered)
            if action is not None:
                self._defer(lambda: self._control(action))
            # F10 is unused in the checked stock command map. Recheck the
            # current map before using it; do not suppress game input or use
            # Ctrl+Alt+Fn (virtual-console switching on some Linux desktops).
            extra_modifier = any(self.world.isKeyDown(key) for key in (
                self.keys.KEY_LALT, self.keys.KEY_RALT,
                self.keys.KEY_LSHIFT, self.keys.KEY_RSHIFT))
            chord = bool(ctrl and not extra_modifier and
                         self.world.isKeyDown(self.keys.KEY_F10))
            previous, self._hotkey_down = self._hotkey_down, chord
            if chord and previous is False:
                own_window = self._window_open()
                if own_window or self._interaction_allowed(require_cursor=False):
                    if self.hotkey_unbound():
                        self._defer(self._open_window)
                    else:
                        self.log('hotkey_conflict_or_unavailable')
        except Exception:
            self._clicks.reset()
            self._hotkey_down = None
            self._cancel_drag()
            self.log('input_poll_failed')

    def _context_changed(self):
        self._cancel_position()
        self._cancel_drag()
        self._sync_stock(False)
        self.context_epoch += 1
        self._clicks.reset()
        self._hotkey_down = None
        self.overlay.hide()
        if not self.store.data['enabled']:
            self.overlay.suspend()
            self._idle_suspended = True
        self._sample_time = None
        self._sample_measured = False
        self._defer(self._close_window)

    def _sync_stock(self, requested):
        if requested == self._stock_requested:
            return
        self._stock_requested = requested
        if requested:
            self._stock_syncing = True
            try:
                self._stock_rangefinder.suppress(self._application())
            finally:
                self._stock_syncing = False
        else:
            self._stock_rangefinder.restore()

    def _stock_status_changed(self):
        if self._stock_requested and not self._stock_syncing:
            self._battle_wakeup()

    def _measurement_interval(self):
        if self._sample.get('mode') in ('strategic', 'arty'):
            return MEASUREMENT_SECONDS
        value = self._sample.get('distance_m')
        threshold = self.store.data['threshold_m']
        if value is None or abs(value - threshold) <= max(10.0, 0.04 * threshold):
            return MEASUREMENT_SECONDS
        return 0.20

    def _battle_wakeup(self, *unused):
        if not self.running or self._arena is None:
            return
        self._sample_time = None
        self._sample_measured = False
        self._position_tracking = False
        self._pending_position = None
        if self._wake_queued:
            return
        self._wake_queued = True
        callback, self.callback = self.callback, None
        if callback is not None:
            try:
                self.world.cancelCallback(callback)
            except Exception:
                # The replaced timer's token prevents a stray callback.
                pass
        self._schedule(0.0)

    def _ready_wakeup(self, *unused):
        self._rebind_requested = True
        self._battle_wakeup()

    def _vehicle_destroyed(self, vehicle_id=None, *unused):
        if vehicle_id is not None and vehicle_id == getattr(self._avatar, 'playerVehicleID', None):
            self._battle_wakeup()

    def _own_vehicle_visibility_changed(self, vehicle=None, *unused):
        if vehicle is not None and getattr(vehicle, 'id', None) == getattr(self._avatar, 'playerVehicleID', None):
            self._battle_wakeup()

    def _position_changed(self, x, y):
        if not self._position_tracking:
            return
        self._pending_position = (x, y)
        if self._position_callback is not None:
            return
        generation = self.generation
        scheduled = [None]

        def apply():
            if self._position_callback != scheduled[0]:
                return
            self._position_callback = None
            position, self._pending_position = self._pending_position, None
            if not (self.running and generation == self.generation and self._position_tracking and
                    position is not None):
                return
            mode = self._sample.get('mode')
            if self.overlay.reposition(position, mode):
                self._sample['aim_position'] = position

        try:
            scheduled[0] = self._position_callback = self.world.callback(POSITION_SECONDS, apply)
        except Exception:
            self._pending_position = None

    def _cancel_position(self):
        self._position_tracking = False
        self._pending_position = None
        callback, self._position_callback = self._position_callback, None
        if callback is not None:
            try:
                self.world.cancelCallback(callback)
            except Exception:
                pass

    def _tick(self, generation, token=None):
        if (not self.running or generation != self.generation or
                (token is not None and token != self._timer_token)):
            return
        self.callback = None
        self._wake_queued = False
        ctrl = False
        try:
            player = self.world.player()
            arena = getattr(player, 'arena', None)
            if player is not self._avatar or arena is not self._arena:
                self._avatar, self._arena = player, arena
                set_battle = getattr(self.log, 'set_battle', None)
                if arena is not None and set_battle is not None:
                    set_battle(True)
                self._rebind_requested = True
                self._context_changed()
                if arena is None and self._last_context == 'battle':
                    self._last_context = 'unavailable'
            if self._rebind_requested:
                self._rebind_requested = False
                battle_activity.bind(self)
            now = self.clock()
            enabled = bool(self.store.data['enabled'])
            ctrl = self._ctrl_held()
            settings_open = self._window_open()
            awake = self._sample.get('reason') != 'own_vehicle_not_alive' or self._sample_time is None
            ui_requested = (enabled and awake) or ctrl or settings_open
            visible = bool(ui_requested and not settings_open and self._hud_visible())
            measure = enabled and visible and arena is not None
            context_changed = False
            interval = self._measurement_interval()
            if not (measure or ctrl):
                interval = DISABLED_IDLE_SECONDS
            sample_due = (self._sample_time is None or
                          ((arena is not None or ctrl or self._last_context == 'unavailable') and
                           (now < self._sample_time or now + 1e-6 >= self._sample_time + interval)))
            if sample_due or (measure and not self._sample_measured):
                self._sample = self.probe.poll(
                    measure=measure, artillery_measure=self.store.data['hide_stock_rangefinder'])
                self._sample_time = now
                self._sample_measured = bool(measure)
                context = self._sample.get('context', 'unavailable')
                if context != self._last_context:
                    self._last_context = context
                    self._context_changed()
                    self._sample_time = now
                    self._sample_measured = bool(measure)
                    context_changed = True
                    visible = bool(ui_requested and not settings_open and self._hud_visible())
                    if context == 'garage' and arena is None:
                        set_battle = getattr(self.log, 'set_battle', None)
                        if set_battle is not None:
                            set_battle(False)
                    self.log('context_' + context if context in ('battle', 'garage') else 'context_unavailable')
                reason = self._sample.get('reason', '')
                if reason in PROBE_DIAGNOSTICS:
                    self.log(reason)
            cursor, active = None, False
            if ctrl and visible:
                cursor = self.gui.mcursor()
                active = self._interaction_allowed(cursor=cursor, ctrl=ctrl, visible=visible)
            mode = self._sample.get('mode')
            eligible = visible and self._sample.get('context') == 'battle' and self._sample.get('battle_eligible')
            arty = mode in ('strategic', 'arty')
            distance_available = self._sample.get('available') is True
            replace_reading = self.store.data['hide_stock_rangefinder']
            self._sync_stock(bool(eligible and enabled and replace_reading and
                                  distance_available and not self.overlay.failed))
            stock_hidden = self._stock_rangefinder.status == 'hidden'
            show_reading = ((stock_hidden and distance_available) if replace_reading
                            else not arty)
            if eligible and (active or (enabled and show_reading)):
                self.overlay.update(self._sample, self._display_config(), self.language(), True,
                                    settings_open, controls_visible=active, reading_visible=show_reading)
                self._idle_suspended = False
            elif not self._idle_suspended:
                # Hide on transient loss of visibility without dropping warmed
                # font and texture resources during a camera/modal transition.
                if enabled:
                    self.overlay.hide()
                else:
                    self.overlay.suspend()
                self._idle_suspended = True
            self._position_tracking = bool(eligible and enabled and show_reading and not ctrl and
                                           self.overlay.has_readout())
            if stock_hidden and not self.overlay.has_readout():
                self._sync_stock(False)
            if ((context_changed and self.footer is not None) or
                    (settings_open and (self._settings_publish_at is None or
                     now < self._settings_publish_at or
                     now + 1e-6 >= self._settings_publish_at + SETTINGS_PUBLISH_SECONDS))):
                self._publish()
            self._poll_input(ctrl=ctrl, cursor=cursor, active=active)
            self._error_streak = 0
        except Exception:
            self._error_streak += 1
            self._sync_stock(False)
            self.overlay.hide()
            self._position_tracking = False
            self._sample_time = None
            self._sample_measured = False
            self._clicks.reset()
            self._cancel_drag()
            self.log('runtime_tick_failed')
        if self.running and generation == self.generation:
            delay = (1.0 if self._error_streak else
                     INTERACTION_SECONDS if ctrl or self._drag is not None else
                     DISABLED_IDLE_SECONDS if self._idle_suspended else TICK_SECONDS)
            self._schedule(delay)

    def _schedule(self, delay):
        if not self.running or self.callback is not None:
            return
        generation = self.generation
        self._timer_token += 1
        token = self._timer_token
        try:
            self.callback = self.world.callback(delay, lambda: self._tick(generation, token))
        except Exception:
            self.log('runtime_scheduler_failed')
            self._cancel_drag()
            self._sync_stock(False)
            self.running = False
            self.overlay.hide()

    def _component_registered(self, event):
        if not self.running:
            return
        try:
            if getattr(event, 'alias', None) != self._consumables_alias:
                return
            self.panel = getattr(event, 'componentPy', None)
            self._context_changed()
            battle_activity.bind(self)
            self._battle_wakeup()
        except Exception:
            self.log('panel_registration_failed')

    def _component_unregistered(self, event):
        if not self.running:
            return
        try:
            if (getattr(event, 'alias', None) == self._consumables_alias and
                    getattr(event, 'componentPy', None) is self.panel):
                self.panel = None
                self._context_changed()
        except Exception:
            self.log('panel_unregistration_failed')

    def install_events(self):
        from gui.shared import g_eventBus, EVENT_BUS_SCOPE
        from gui.shared.events import ComponentEvent
        from gui.Scaleform.genConsts.BATTLE_VIEW_ALIASES import BATTLE_VIEW_ALIASES
        self._consumables_alias = BATTLE_VIEW_ALIASES.CONSUMABLES_PANEL
        for event, callback in ((ComponentEvent.COMPONENT_REGISTERED, self._component_registered),
                                (ComponentEvent.COMPONENT_UNREGISTERED, self._component_unregistered)):
            try:
                g_eventBus.addListener(event, callback, scope=EVENT_BUS_SCOPE.GLOBAL)
            except Exception:
                try:
                    g_eventBus.removeListener(event, callback, scope=EVENT_BUS_SCOPE.GLOBAL)
                except Exception:
                    pass
                raise
            self.events.append((g_eventBus, event, callback, EVENT_BUS_SCOPE.GLOBAL))

    def start(self, subscribe=True):
        if self.running:
            return
        self.store.load()
        self._load_issue = bool(getattr(self.store, 'last_error', None))
        if self._load_issue:
            self.log('settings_load_failed')
        self.running = True
        self.generation += 1
        if subscribe:
            try:
                from . import garage
                self.footer = garage.install(self._footer_action, self.payload,
                                             lambda: self._defer(self._close_window))
                if self.footer is None:
                    self.log('garage_footer_unavailable')
            except Exception:
                self.log('garage_footer_unavailable')
            try:
                self.install_events()
            except Exception:
                # Garage configuration remains usable; no fake battle HUD visibility.
                self.log('battle_events_unavailable')
        self.log('started')
        self._schedule(0.5)

    def stop(self):
        self._cancel_position()
        battle_activity.unbind(self)
        self._cancel_drag()
        self._sync_stock(False)
        self.running = False
        self.generation += 1
        self.context_epoch += 1
        callbacks = [self.callback] + [item['id'] for item in self.pending]
        self.callback, self.pending = None, []
        for callback in callbacks:
            if callback is not None:
                try:
                    self.world.cancelCallback(callback)
                except Exception:
                    pass
        while self.events:
            bus, event, callback, scope = self.events.pop()
            try:
                bus.removeListener(event, callback, scope=scope)
            except Exception:
                self.log('event_detach_failed')
        self.panel = self._avatar = self._arena = None
        if self.footer is not None:
            try:
                self.footer.uninstall()
            except Exception:
                self.log('garage_detach_failed')
            self.footer = None
        try:
            self._close_window()
        except Exception:
            self.log('settings_close_failed')
        try:
            self.overlay.close()
        finally:
            if self.preview_diagnostics is not None:
                try:
                    self.preview_diagnostics.close()
                except Exception:
                    pass
        self._clicks.reset()
        self.log('stopped')


def create_runtime():
    import BigWorld
    import GUI
    import Keys
    import ResMgr
    from .client import ClientProbe
    from .preview_diagnostics import PreviewDiagnostics
    directory = config_directory()
    log = Diagnostics(directory)
    store = SettingsStore(os.path.join(directory, 'settings.json'))
    return Runtime(BigWorld, GUI, Keys, ClientProbe(), store, ResMgr.isFile, log=log,
                   preview_diagnostics=PreviewDiagnostics(directory))
