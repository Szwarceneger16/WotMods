# -*- coding: ascii -*-
"""Owned lifecycle, input polling and configuration for the aimtimer."""
from __future__ import absolute_import

import json
import logging
import os
import time

from . import VERSION, preview_catalog
from .core import SettingsStore, validate_config, with_mode_position
from .hud import ClickTracker, Overlay, finite
from .preview_catalog import translations

try:
    text_types = (basestring,)
except NameError:
    text_types = (str,)

TICK_SECONDS = 0.10
INTERACTION_SECONDS = 0.05
DISABLED_IDLE_SECONDS = 0.10
MEASUREMENT_SECONDS = 0.10
SETTINGS_PUBLISH_SECONDS = 0.50
MAX_COMMAND_CHARS = 4096
PROBE_DIAGNOSTICS = frozenset((
    'measurement_failed', 'aim_state_unavailable', 'aim_state_stale',
    'aim_state_invalid', 'aim_state_uninitialized',
    'dual_accuracy_unsupported', 'replay_unsupported',
    'controllers_unavailable', 'vehicle_context_unavailable',
))


def config_directory():
    base = os.environ.get('APPDATA') or os.environ.get('LOCALAPPDATA')
    if base:
        return os.path.join(base, 'GRZ_AimTimer')
    return os.path.abspath(os.path.join('mods', 'configs', 'grz_aimtimer'))


class Diagnostics(object):
    """Small category-only log; no coordinates, player names or game payloads."""
    def __init__(self, directory):
        self.logger = logging.getLogger('grz.aimtimer.private')
        self.logger.setLevel(logging.INFO)
        self.logger.propagate = False
        self.handler = None
        self.counts = {}
        try:
            if not os.path.isdir(directory):
                os.makedirs(directory)
            from logging.handlers import RotatingFileHandler
            path = os.path.join(directory, 'aimtimer.log')
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
            try:
                self.logger.info('v%s %s', VERSION, code)
            except Exception:
                pass

    def close(self):
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
                 log=None, clock=None, language_getter=None, preview_diagnostics=None):
        self.world, self.gui, self.keys = world, gui, keys
        self.probe, self.store = probe, store
        self.log = log or (lambda code: None)
        self.preview_diagnostics = preview_diagnostics
        self.clock = clock or time.time
        self.window_factory = window_factory
        self.app_getter = app_getter or self._native_application
        self.chat_focused = chat_focused or self._native_chat_focused
        self.language_getter = language_getter or self._native_language
        self.overlay = Overlay(gui, world, resource_exists, self.log, clock=self.clock)
        self.window = None
        self.footer = None
        self.running = False
        self.generation = 0
        self.context_epoch = 0
        self.callback = None
        self.pending = []
        self.events = []
        self.panel = None
        self._avatar = None
        self._arena = None
        self._sample = {'context': 'unavailable', 'battle_eligible': False,
                        'available': False, 'remaining_s': None, 'kind': 'none',
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
                                    remaining_s=None, kind='none')
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
        self._error = (translations.message('load_failed', self.language()) % 'aimtimer.log'
                       if self._load_issue else '')
        if anchor is None:
            anchor = 0.96 if self._sample.get('context') == 'garage' else 0.5
            anchor_y = None if self._sample.get('context') == 'garage' else 0.78
        if not self.window.open(anchor, anchor_y):
            self.log('settings_window_unavailable')
            self._error = translations.message('window_unavailable', self.language())
        else:
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
        except Exception:
            self._clicks.reset()
            self._cancel_drag()
            self.log('input_poll_failed')

    def _context_changed(self):
        self._cancel_drag()
        self.context_epoch += 1
        self._clicks.reset()
        self.overlay.hide()
        if not self.store.data['enabled']:
            self.overlay.suspend()
            self._idle_suspended = True
        self._sample_time = None
        self._sample_measured = False
        self._defer(self._close_window)

    def _tick(self, generation):
        if not self.running or generation != self.generation:
            return
        self.callback = None
        ctrl = False
        try:
            player = self.world.player()
            arena = getattr(player, 'arena', None)
            if player is not self._avatar or arena is not self._arena:
                self._avatar = player
                self._arena = arena
                self._context_changed()
            now = self.clock()
            enabled = bool(self.store.data['enabled'])
            ctrl = self._ctrl_held()
            settings_open = self._window_open()
            ui_requested = enabled or ctrl or settings_open
            # An owned form or hidden battle HUD needs neither a ray cast nor
            # an aiming-state read. Visibility includes the modal/app gate.
            visible = bool(ui_requested and not settings_open and self._hud_visible())
            measure = enabled and visible and self._sample.get('context') == 'battle'
            context_changed = False
            sample_due = (self._sample_time is None or
                          (ui_requested and (self._idle_suspended or
                           now < self._sample_time or
                           now + 1e-6 >= self._sample_time + MEASUREMENT_SECONDS)))
            # Resume with a fresh value immediately after a hidden interval.
            if sample_due or (measure and not self._sample_measured):
                self._sample = self.probe.poll(measure=measure)
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
                    self.log('context_' + context if context in ('battle', 'garage') else 'context_unavailable')
                reason = self._sample.get('reason', '')
                if reason in PROBE_DIAGNOSTICS:
                    self.log(reason)
            cursor, active = None, False
            if ui_requested:
                # Query cursor/focus only for the Ctrl interaction path, and
                # reuse that snapshot for both control visibility and clicks.
                if ctrl:
                    cursor = self.gui.mcursor()
                    active = self._interaction_allowed(cursor=cursor, ctrl=ctrl,
                                                       visible=visible)
                controls_visible = self._sample.get('context') == 'battle' and active
                self.overlay.update(self._sample, self._display_config(), self.language(), visible,
                                    settings_open, controls_visible=controls_visible)
                self._idle_suspended = False
            elif not self._idle_suspended:
                self.overlay.suspend()
                self._idle_suspended = True
            if context_changed and self.footer is not None:
                self._publish()
            elif (settings_open and (self._settings_publish_at is None or
                    now < self._settings_publish_at or
                    now + 1e-6 >= self._settings_publish_at + SETTINGS_PUBLISH_SECONDS)):
                self._publish()
            self._poll_input(ctrl=ctrl, cursor=cursor, active=active)
            self._error_streak = 0
        except Exception:
            self._error_streak += 1
            self.overlay.hide()
            self._sample_time = None
            self._sample_measured = False
            self._clicks.reset()
            self._cancel_drag()
            self.log('runtime_tick_failed')
        if self.running and generation == self.generation:
            delay = (1.0 if self._error_streak else
                     DISABLED_IDLE_SECONDS if self._idle_suspended else
                     INTERACTION_SECONDS if ctrl or self._drag is not None else TICK_SECONDS)
            self._schedule(delay)

    def _schedule(self, delay):
        if not self.running or self.callback is not None:
            return
        generation = self.generation
        try:
            self.callback = self.world.callback(delay, lambda: self._tick(generation))
        except Exception:
            self.log('runtime_scheduler_failed')
            self._cancel_drag()
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
        self._cancel_drag()
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
