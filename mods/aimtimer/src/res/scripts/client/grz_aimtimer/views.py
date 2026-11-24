# -*- coding: utf-8 -*-
"""Small registered Gameface settings window with its own native input surface.

Adapted from the user's StaySharpMedkit owned-window implementation.
No footer injection, native GUI input script, or other mod dependency is used.
"""
from __future__ import absolute_import, unicode_literals

import json
import logging
import math
import sys
import time

from .scene_catalog import DEFAULT_FOCUS, resolve as resolve_scene, resolve_focus

LOG = logging.getLogger('grz.aimtimer')
LAYOUT_PATH = ('mods', 'grz', 'aimtimer', 'v0_1_7', 'views', 'Settings')
LOGICAL_SIZE = (520, 320)
EDGE_GUTTER = 16
POPUP_GAP = 24
MAX_DIMENSION = 32768
# Cyrillic catalog strings use JSON Unicode escapes on this bridge.
MAX_STATE_CHARS = 32768
MAX_EDITOR_REQUEST_ID = 2147483647
DECORATION_DIAGNOSTICS = frozenset((
    'stock-binding-missing',
    'library-load', 'symbol-missing', 'symbol-incompatible', 'timeline-member',
    'timeline-frame', 'empty-drawing', 'pixel-probe', 'bridge-error-detail',
    'host-rejected', 'host-linkage-unsupported', 'host-geometry-invalid', 'stock-symbol-error',
    'host-error-empty', 'host-error-type', 'host-error-too-long', 'flash-error',
    'hide-previous', 'unsupported-family', 'resource-query',
    'missing-host', 'missing-stock-layer', 'missing-stock-surge', 'host-construction',
    'host-component', 'host-configuration', 'host-activation', 'host-geometry',
    'bridge-root', 'bridge-request', 'bridge-state', 'root-timeout', 'library-timeout',
))
BLUR_POLL_DELAY = 0.02
BLUR_MAX_SAMPLES = 150
try:
    text_types = (basestring,)
    request_number_types = (int, long, float)
except NameError:
    text_types = (str,)
    request_number_types = (int, float)


def _editor_request_id(value):
    if type(value) not in request_number_types or not 1 <= value <= MAX_EDITOR_REQUEST_ID:
        return None
    return int(value) if int(value) == value else None


def _peer_editor_readout(mode):
    # The game owns peer loading and shutdown. Never load it from this view.
    module = sys.modules.get('gui.mods.mod_grz_rangefinder')
    getter = getattr(module, 'get_editor_readout_v1', None)
    if not callable(getter):
        return None
    try:
        snapshot = getter(mode)
        if not isinstance(snapshot, dict) or type(snapshot.get('enabled')) is not bool:
            return None
        result = {'enabled': snapshot['enabled'],
                  'hide_stock_rangefinder': snapshot.get('hide_stock_rangefinder') is True}
        for key, low, high in (('x', -32768, 32768), ('y', -32768, 32768),
                               ('hud_font_px', 12, 40), ('hud_frame_scale_pct', 100, 300),
                               ('hud_background_opacity', 0, 1)):
            value = snapshot.get(key)
            if type(value) not in request_number_types or not low <= value <= high:
                return None
            if key != 'hud_background_opacity' and int(value) != value:
                return None
            result[key] = value
        return result
    except Exception:
        return None


def _valid_state(state):
    if not isinstance(state, text_types) or len(state) > MAX_STATE_CHARS:
        return False
    try:
        payload = json.loads(state)
        if not isinstance(payload, dict):
            return False
        json.dumps(payload, allow_nan=False)
        return True
    except (TypeError, ValueError, RuntimeError):
        return False


def _positive(value, maximum=MAX_DIMENSION):
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
        return number if 0 < number <= maximum and not math.isnan(number) else None
    except (TypeError, ValueError, OverflowError):
        return None


def _dimensions(value):
    try:
        width, height = value
        width, height = _positive(width), _positive(height)
        if width is not None and height is not None:
            return (int(math.ceil(width)), int(math.ceil(height)))
    except (TypeError, ValueError):
        pass
    return None


def _fit_geometry(viewport):
    """Fit the complete logical design inside a scaled client-edge gutter."""
    width, height, scale = viewport['width'], viewport['height'], viewport['scale']
    if width <= 0 or height <= 0:
        return None
    gutter = min(max(1, int(math.ceil(EDGE_GUTTER * scale))),
                 max(1, int(min(width, height) // 4)))
    # A one-pixel client cannot contain two one-pixel gutters. Degrade the
    # inset only for that degenerate surface, keeping all coordinates valid.
    gutter = min(gutter, max(0, (min(width, height) - 1) // 2))
    available = (width - 2 * gutter, height - 2 * gutter)
    if min(available) < 1:
        return None
    fitted_scale = min(scale, float(available[0]) / LOGICAL_SIZE[0],
                       float(available[1]) / LOGICAL_SIZE[1])
    size = tuple(max(1, int(math.floor(value * fitted_scale))) for value in LOGICAL_SIZE)
    return size, gutter, available


def _layout_id():
    from gui.impl.gen import R
    node = R
    for name in LAYOUT_PATH:
        node = getattr(node, name)
    resource = int(node())
    if resource < 0:
        raise ValueError('Invalid registered AimTimer resource')
    return resource


def _main_window():
    from frameworks.wulf import WindowStatus
    from helpers import dependency
    from skeletons.gui.impl import IGuiLoader
    parent = dependency.instance(IGuiLoader).windowsManager.getMainWindow()
    if parent is None or parent.proxy is None or parent.windowStatus != WindowStatus.LOADED:
        return None
    return parent


def _interface_scale():
    try:
        from helpers import dependency
        from skeletons.gui.impl import IGuiLoader
        return _positive(dependency.instance(IGuiLoader).scale, 16) or 1.0
    except Exception:
        return 1.0


def _battle_application():
    from helpers import dependency
    from skeletons.gui.app_loader import IAppLoader
    return dependency.instance(IAppLoader).getDefBattleApp()


def _preview_profile(mode, variant):
    from .preview_catalog import profile
    return profile(variant, mode)


def _build_preview(on_status, on_availability=None, on_diagnostic=None):
    from .native_preview import PreviewRenderer
    return PreviewRenderer(on_status=on_status, on_availability=on_availability,
                           on_diagnostic=on_diagnostic)


def _safe_preview_availability(value):
    """Accept a finite detached capability map, never arbitrary native data."""
    result = {}
    if not isinstance(value, dict):
        return result
    for mode in ('arcade', 'sniper', 'arty'):
        entries = value.get(mode)
        if not isinstance(entries, dict) or len(entries) > 64:
            continue
        safe = {}
        for variant, available in entries.items():
            if (type(available) is bool and isinstance(variant, text_types) and
                    len(variant) <= 64 and _preview_profile(mode, variant) is not None):
                safe[variant] = available
        if safe:
            result[mode] = safe
    return result


def _battle_escape_handler(on_escape):
    from gui.Scaleform.managers.battle_input import BattleGUIKeyHandler
    pressed = [False]

    class SettingsEscapeHandler(BattleGUIKeyHandler):
        def handleEscKey(self, is_down):
            previous, pressed[0] = pressed[0], bool(is_down)
            # One physical Escape exits one layer. Native key-repeat must not
            # also close the settings form after the editor was dismissed.
            if is_down and not previous:
                on_escape()
            return True

    return SettingsEscapeHandler()


def build_model_class():
    from frameworks.wulf import ViewModel

    class SettingsModel(ViewModel):
        def __init__(self, state, on_action):
            self._state = state
            self._on_action = on_action
            super(SettingsModel, self).__init__(properties=1, commands=1)

        def _initialize(self):
            super(SettingsModel, self)._initialize()
            self._addStringProperty(str('state'), self._state)
            self.onAction = self._addCommand(str('onAction'))
            self.onAction += self._dispatch

        def _dispatch(self, *args):
            if self._on_action is not None:
                try:
                    self._on_action(args[0] if args else None)
                except Exception:
                    LOG.warning('AimTimer settings command unavailable.')

        def setState(self, state):
            if self._on_action is None or state == self._state:
                return False
            with self.transaction():
                self._setString(0, state)
            self._state = state
            return True

        def deactivate(self):
            self._on_action = None

    return SettingsModel


def build_view_class():
    from frameworks.wulf import ViewFlags, ViewSettings
    from gui.impl.pub import ViewImpl

    class SettingsView(ViewImpl):
        def __init__(self, layout, model):
            super(SettingsView, self).__init__(ViewSettings(
                layoutID=layout, flags=ViewFlags.VIEW, model=model))

    return SettingsView


def build_window_class():
    from frameworks.wulf import WindowFlags, WindowLayer
    from gui.impl.pub import WindowImpl

    class SettingsNativeWindow(WindowImpl):
        def __init__(self, content, parent, on_ready, on_released, is_battle=False):
            self._aimtimer_ready = on_ready
            self._aimtimer_released = on_released
            super(SettingsNativeWindow, self).__init__(
                WindowFlags.WINDOW | (WindowFlags.WINDOW_MODAL if is_battle else 0),
                content=content, layer=WindowLayer.WINDOW,
                name=str('GrzAimTimerSettings'), parent=parent)

        def _onReady(self):
            try:
                if self._aimtimer_ready(self) is not False:
                    self.show(True)
            except Exception:
                LOG.warning('AimTimer settings readiness unavailable.')

        def _finalize(self):
            try:
                try:
                    self._aimtimer_released(self)
                except Exception:
                    LOG.warning('AimTimer settings close notification unavailable.')
            finally:
                super(SettingsNativeWindow, self)._finalize()

    return SettingsNativeWindow


class SettingsWindow(object):
    def __init__(self, on_action, get_state, battle_app_getter=None, on_diagnostic=None):
        self._on_action = on_action
        self._get_state = get_state
        self._on_diagnostic = on_diagnostic
        self._diagnostic_pending = None
        self._diagnostic_active_request = None
        self._window = self._model = self._parent = None
        self._events = []
        self._state = '{}'
        self._anchor = 0.5
        self._anchor_y = None
        self._size = None
        self._reported_size = None
        self._reported_viewport = None
        self._blur_callback = None
        self._blur_pending = None
        self._layout_logs = 0
        self._generation = 0
        self._closing = False
        self._destroying = False
        self._notified = True
        self._warned = False
        self._battle_app_getter = battle_app_getter or _battle_application
        self._battle_app = self._battle_key_handler = None
        self._battle_consumer = str('grz.aimtimer.settings.%s' % id(self))
        self._battle_mode = False
        self._editor_active = False
        self._editor_target = False
        self._editor_callback = None
        self._editor_request_seen = 0
        self._editor_request_ack = 0
        self._editor_request_accepted = True
        self._preview = None
        self._preview_mode = 'arcade'
        self._preview_variant = 'standard'
        self._preview_scene_id = 'arcade'
        self._preview_zoom_step = 1
        self._preview_focus = DEFAULT_FOCUS
        self._preview_focus_demo = False
        self._preview_status = 'unavailable'
        self._preview_reason = None
        self._preview_decoration_diagnostic = None
        self._preview_signature = None
        self._preview_availability = {}

    def _acquire_battle_input(self):
        if not self._battle_mode or self._battle_app is not None:
            return True
        app = self._battle_app_getter()
        if app is None or getattr(app, 'initialized', True) is False:
            return False
        for method in ('enterGuiControlMode', 'leaveGuiControlMode',
                       'hasGuiControlModeConsumers', 'registerGuiKeyHandler',
                       'unregisterGuiKeyHandler'):
            if not callable(getattr(app, method, None)):
                return False
        # Retain ownership before native calls, including partially successful
        # calls which throw after adding a consumer/handler.
        self._battle_app = app
        generation = self._generation

        def escape():
            if generation == self._generation and self.is_open():
                if self._editor_active or self._editor_target:
                    self._queue_editor(False)
                else:
                    self._notify('close')

        self._battle_key_handler = _battle_escape_handler(escape)
        app.registerGuiKeyHandler(self._battle_key_handler)
        app.enterGuiControlMode(self._battle_consumer, cursorVisible=True,
                                enableAiming=False, stopVehicle=False)
        # The native method returns None on success. Its own consumer query is
        # the acknowledgement; never use the method's falsey return value.
        return bool(app.hasGuiControlModeConsumers(self._battle_consumer))

    def _release_battle_input(self):
        app, handler = self._battle_app, self._battle_key_handler
        self._battle_app = self._battle_key_handler = None
        if app is None:
            return
        try:
            if handler is not None:
                app.unregisterGuiKeyHandler(handler)
        except Exception:
            self._warn()
        try:
            app.leaveGuiControlMode(self._battle_consumer)
        except Exception:
            self._warn()

    def _warn(self):
        if not self._warned:
            self._warned = True
            LOG.warning('AimTimer settings window unavailable; the aimtimer can remain active.')

    def _viewport(self):
        size = None
        # A loading main Window can still expose its default 256px texture.
        # Placement and responsive CSS need the client surface, not that texture.
        try:
            import GUI
            size = _dimensions(GUI.screenResolution())
        except Exception:
            pass
        if size is None and self._parent is not None:
            try:
                size = _dimensions(self._parent.size)
            except Exception:
                pass
        return {'width': size[0] if size else 0, 'height': size[1] if size else 0,
                'scale': _interface_scale()}

    def _payload(self):
        payload = json.loads(self._state)
        payload['viewport'] = self._viewport()
        payload['native_gameface'] = True
        payload['editor_active'] = self._editor_active
        payload['editor_request_id'] = self._editor_request_ack
        payload['editor_request_accepted'] = self._editor_request_accepted
        payload['editor_preview_mode'] = self._preview_mode
        payload['editor_peer_readout'] = (_peer_editor_readout(self._preview_mode)
                                          if self._editor_active else None)
        payload['editor_preview_variant'] = self._preview_variant
        payload['editor_preview_status'] = self._preview_status
        payload['editor_preview_reason'] = self._preview_reason
        payload['editor_preview_decoration_diagnostic'] = self._preview_decoration_diagnostic
        payload['editor_preview_availability'] = self._preview_availability
        payload['editor_scene_id'] = self._preview_scene_id
        payload['editor_zoom_step'] = self._preview_zoom_step
        payload['editor_focus'] = self._preview_focus
        payload['editor_focus_demo'] = self._preview_focus_demo
        payload['editor_focus_supported'] = (self._preview_status in ('ready', 'partial') and
                                             bool(getattr(self._preview, 'supports_focus', False)))
        return json.dumps(payload, ensure_ascii=True, allow_nan=False,
                          separators=(',', ':'), sort_keys=True)

    def _cancel_editor(self):
        callback, self._editor_callback = self._editor_callback, None
        self._editor_target = self._editor_active
        if callback is not None:
            try:
                import BigWorld
                BigWorld.cancelCallback(callback)
            except Exception:
                self._warn()

    def _scene_selection(self, mode, scene_id=None, zoom_step=None):
        if scene_id is None and mode == self._preview_mode:
            scene_id = self._preview_scene_id
        if (zoom_step is None and mode == self._preview_mode and
                scene_id == self._preview_scene_id):
            zoom_step = self._preview_zoom_step
        return resolve_scene(mode, scene_id, zoom_step)

    def _queue_editor(self, active, mode=None, variant=None, scene_id=None, zoom_step=None,
                      focus=None, focus_changed=False, request_id=None):
        """Resize only after the owned native input dispatcher has returned."""
        if type(active) is not bool or not self.is_open():
            return False
        mode = self._preview_mode if mode is None else mode
        variant = self._preview_variant if variant is None else variant
        scene = self._scene_selection(mode, scene_id, zoom_step) if active else None
        if active and (scene is None or self._focus_selection(focus) is None or
                       not self._preview_supported(mode, variant)):
            return False
        self._cancel_editor()
        generation, native = self._generation, self._window
        self._editor_target = active
        pending = [None]

        def apply():
            if self._editor_callback != pending[0]:
                return
            self._editor_callback = None
            if (generation == self._generation and self._window is native and
                    self.is_open()):
                if not self.set_editor(active, mode, variant,
                                       scene['scene_id'] if scene else None,
                                       scene['step'] if scene else None, focus, focus_changed, request_id):
                    self._editor_target = self._editor_active
                    self._record_editor_request(request_id, False)
                    self.update(self._state)

        try:
            import BigWorld
            pending[0] = BigWorld.callback(0.0, apply)
            self._editor_callback = pending[0]
            return True
        except Exception:
            self._editor_target = self._editor_active
            self._warn()
            return False

    def _queue_preview(self, mode, variant, scene_id=None, zoom_step=None,
                       focus=None, focus_changed=False, request_id=None):
        if not (self._editor_active or self._editor_target):
            return False
        # Zoom requests can be queued during a running demo. Only an explicit
        # preset click may replace the latest focus when the request runs.
        focus = focus if focus_changed else None
        return self._queue_editor(True, mode, variant, scene_id, zoom_step, focus, focus_changed, request_id)

    def _record_editor_request(self, request_id, accepted):
        if request_id is not None:
            self._editor_request_ack, self._editor_request_accepted = request_id, accepted
            pending = self._diagnostic_pending
            if pending is not None and request_id == pending[0]['request_id']:
                if accepted and self._editor_active:
                    self._diagnostic_active_request = (request_id, pending[1])
                self._finish_diagnostic_request('accepted' if accepted else 'rejected')

    @staticmethod
    def _diagnostic_context(mode, variant, scene):
        fields = {}
        if mode in ('arcade', 'sniper', 'arty'):
            fields['mode'] = mode
            selected = _preview_profile(mode, variant)
            if selected is not None:
                fields.update(variant=variant, profile=selected['id'])
        if scene is not None:
            fields.update(scene=scene['scene_id'], step=scene['step'])
        return fields

    def _diagnose(self, event, fields):
        if self._on_diagnostic is not None:
            try:
                self._on_diagnostic(event, fields)
            except Exception:
                pass

    def _active_diagnostic_fields(self):
        mode, variant = self._preview_mode, self._preview_variant
        fields = self._diagnostic_context(mode, variant, self._scene_selection(mode))
        if self._diagnostic_active_request is not None:
            request_id, started = self._diagnostic_active_request
            fields.update(request_id=request_id, elapsed_ms=self._elapsed_ms(started))
        return fields

    @staticmethod
    def _elapsed_ms(started):
        return max(0, min(120000, int((time.time() - started) * 1000)))

    def _finish_diagnostic_request(self, result):
        pending, self._diagnostic_pending = self._diagnostic_pending, None
        if pending is not None:
            fields, started = pending
            self._diagnose('editor-result', dict(fields, result=result, elapsed_ms=self._elapsed_ms(started)))

    def _diagnose_close(self, request_id=None, was_active=None):
        if was_active is None:
            was_active = self._editor_active
        if self._on_diagnostic is not None and was_active:
            fields = self._active_diagnostic_fields()
            fields.pop('elapsed_ms', None)
            if request_id is not None:
                fields['request_id'] = request_id
            self._diagnose('editor-close', fields)
        self._diagnostic_active_request = None

    def _dispatch_editor_request(self, action, getter):
        request_id = _editor_request_id(getter('request_id'))
        if request_id is None or request_id <= self._editor_request_seen:
            return False
        self._editor_request_seen = request_id
        mode, variant = getter('mode'), getter('variant')
        scene_id, zoom_step, focus = getter('scene_id'), getter('zoom_step'), getter('focus')
        if self._on_diagnostic is not None:
            active = getter('active') if action == 'editor' else True
            if active is False:
                fields = self._active_diagnostic_fields()
                fields.pop('elapsed_ms', None)
                fields['action'] = 'close'
            else:
                scene = self._scene_selection(mode, scene_id, zoom_step)
                fields = self._diagnostic_context(mode, variant, scene)
                if active is True:
                    fields['action'] = 'open' if action == 'editor' else 'update'
            fields['request_id'] = request_id
            self._finish_diagnostic_request('superseded')
            self._diagnostic_pending = (fields, time.time())
            self._diagnose('editor-request', dict(fields))
        if action == 'editor':
            queued = self._queue_editor(getter('active'), mode, variant, scene_id, zoom_step,
                                        focus, request_id=request_id)
        else:
            queued = self._queue_preview(mode, variant, scene_id, zoom_step,
                                         focus, getter('focus_changed') is True, request_id)
        if not queued:
            self._cancel_editor()
            self._record_editor_request(request_id, False)
            self.update(self._state)
        return queued

    def _focus_selection(self, focus):
        return self._preview_focus if focus is None else resolve_focus(focus)

    def _play_focus_demo(self):
        preview = self._preview
        if (preview is None or not self._editor_active or not self._editor_target or
                not self.is_open() or self._preview_focus_demo):
            return False

        def finished(completed):
            if self._preview is preview and self._editor_active and self.is_open():
                self._preview_focus_demo = False
                if completed:
                    self._preview_focus = 2
                self.update(self._state)

        if not preview.play_focus_demo(finished):
            return False
        self._preview_focus_demo = True
        self.update(self._state)
        return True

    def _preview_supported(self, mode, variant):
        if _preview_profile(mode, variant) is None:
            return False
        # Keep the scene controls available for the current editor selection
        # even if its native reticle could not start.
        if self._editor_active and (mode, variant) == (self._preview_mode, self._preview_variant):
            return True
        return self._preview_availability.get(mode, {}).get(variant) is not False

    def _close_preview(self):
        preview, self._preview = self._preview, None
        self._preview_signature = None
        self._preview_status = 'unavailable'
        self._preview_reason = None
        self._preview_decoration_diagnostic = None
        self._preview_availability = {}
        self._preview_focus_demo = False
        if preview is not None:
            try:
                preview.close()
            except Exception:
                self._warn()

    def _refresh_preview(self, focus_changed=False):
        if not self._editor_active or not self.is_open():
            return
        viewport = self._viewport()
        distance_config = _peer_editor_readout(self._preview_mode) or {}
        hide_stock_distance = (distance_config.get('enabled') is True and
                               distance_config.get('hide_stock_rangefinder') is True)
        signature = (self._preview_mode, self._preview_variant,
                     self._preview_scene_id, self._preview_zoom_step, self._preview_focus,
                     viewport['width'], viewport['height'], viewport['scale'], hide_stock_distance)
        if self._preview_signature == signature and not focus_changed:
            return
        self._preview_signature = signature
        try:
            opening = self._preview is None
            if opening:
                generation = self._generation
                owner = [None]

                def status(value):
                    renderer = owner[0]
                    if (self._preview is renderer and renderer is not None and
                            generation == self._generation and self._editor_active and
                            self.is_open() and value in ('loading', 'ready', 'partial', 'unavailable')):
                        reason = renderer.reason
                        diagnostic = getattr(renderer, 'decoration_diagnostic', None)
                        if not isinstance(diagnostic, text_types) or diagnostic not in DECORATION_DIAGNOSTICS:
                            diagnostic = None
                        if (self._preview_status, self._preview_reason,
                                self._preview_decoration_diagnostic) != (value, reason, diagnostic):
                            self._preview_status, self._preview_reason = value, reason
                            self._preview_decoration_diagnostic = diagnostic
                            if self._on_diagnostic is not None:
                                fields = self._active_diagnostic_fields()
                                fields.update(status=value, reason=reason, diagnostic=diagnostic)
                                self._diagnose('preview-status', fields)
                            self.update(self._state)

                def availability(value):
                    if (self._preview is owner[0] and owner[0] is not None and
                            generation == self._generation and self._editor_active and
                            self.is_open()):
                        value = _safe_preview_availability(value)
                        if value != self._preview_availability:
                            self._preview_availability = value
                            self.update(self._state)

                def diagnostic_event(event, fields):
                    if (generation == self._generation and self._preview is owner[0] and
                            owner[0] is not None and self._editor_active and self.is_open()):
                        entry = dict(fields)
                        if self._diagnostic_active_request is not None:
                            entry['request_id'] = self._diagnostic_active_request[0]
                        self._diagnose(event, entry)

                owner[0] = self._preview = _build_preview(status, availability,
                    diagnostic_event if self._on_diagnostic is not None else None)
            if opening:
                self._preview_status = 'loading'
                self._preview_reason = None
                self._preview_decoration_diagnostic = None
            preview = self._preview
            method = preview.open if opening else preview.update
            method(self._preview_mode, self._preview_variant, viewport,
                   self._preview_scene_id, self._preview_zoom_step,
                   self._preview_focus, focus_changed, hide_stock_distance)
            if self._preview is not preview or not self._editor_active or not self.is_open():
                return
            availability = _safe_preview_availability(preview.get_availability())
            if availability != self._preview_availability:
                self._preview_availability = availability
                self.update(self._state)
        except Exception:
            self._close_preview()
            # Keep the owned form and drag editor usable after a resource or
            # native-movie failure. Do not substitute approximate artwork.
            self._preview_signature = signature
            if self._on_diagnostic is not None:
                self._diagnose('preview-status', dict(self._active_diagnostic_fields(),
                                                     status='unavailable', reason='native'))
            self._warn()

    def set_editor(self, active, mode=None, variant=None, scene_id=None, zoom_step=None,
                   focus=None, focus_changed=False, request_id=None):
        """Acknowledge fullscreen preview; the document resizes its own view."""
        if type(active) is not bool or not self.is_open():
            return False
        mode = self._preview_mode if mode is None else mode
        variant = self._preview_variant if variant is None else variant
        scene = self._scene_selection(mode, scene_id, zoom_step) if active else None
        focus = self._focus_selection(focus)
        if active and (scene is None or focus is None or not self._preview_supported(mode, variant)):
            return False
        self._cancel_editor()
        was_active = self._editor_active
        if request_id is None:
            self._finish_diagnostic_request('superseded')
        self._editor_active = self._editor_target = active
        self._record_editor_request(request_id, True)
        if active:
            if (mode, variant) != (self._preview_mode, self._preview_variant):
                self._preview_status = 'loading'
                self._preview_reason = None
                self._preview_decoration_diagnostic = None
            self._preview_mode, self._preview_variant = mode, variant
            self._preview_scene_id, self._preview_zoom_step = scene['scene_id'], scene['step']
            self._preview_focus = focus
            if not was_active and self._on_diagnostic is not None:
                self._diagnose('editor-open', self._active_diagnostic_fields())
            self._refresh_preview(focus_changed is True)
        else:
            self._diagnose_close(request_id, was_active)
            self._close_preview()
        self._reported_size = self._reported_viewport = None
        self._cancel_blur()
        # Native payload is authoritative. The UI waits for this acknowledgment
        # before requesting a fullscreen or restored compact texture.
        self.update(self._state)
        self._place()
        return True

    def _released(self, window):
        try:
            from frameworks.wulf import WindowStatus
            return window.proxy is None or window.windowStatus == WindowStatus.DESTROYED
        except Exception:
            return False

    def is_open(self):
        return self._window is not None and not self._closing and not self._released(self._window)

    def _notify(self, action):
        try:
            self._on_action({'action': action})
        except Exception:
            self._warn()

    def _notify_close(self):
        if not self._notified:
            self._notified = True
            self._notify('close')

    def _attach(self, event, callback):
        if event is None:
            return
        generation = self._generation
        active = [True]

        def guarded(*args):
            if active[0] and generation == self._generation:
                try:
                    callback(*args)
                except Exception:
                    self._warn()

        try:
            event += guarded
            self._events.append((event, guarded, active))
        except Exception:
            active[0] = False
            try:
                event -= guarded
            except Exception:
                pass
            self._warn()

    def _detach(self):
        while self._events:
            event, callback, active = self._events.pop()
            active[0] = False
            try:
                event -= callback
            except Exception:
                self._warn()

    def _cancel_blur(self):
        callback = self._blur_callback
        self._blur_callback = self._blur_pending = None
        if callback is not None:
            try:
                import BigWorld
                BigWorld.cancelCallback(callback)
            except Exception:
                self._warn()

    def _schedule_blur(self):
        self._cancel_blur()
        generation = self._generation
        pending = {'samples': 0, 'released': False}
        self._blur_pending = pending

        def dismiss():
            if self._blur_pending is not pending or generation != self._generation:
                return
            self._blur_callback = None
            if not self.is_open():
                self._blur_pending = None
                return
            if getattr(self._window, 'isFocused', False):
                self._blur_pending = None
                return
            held = False
            if not pending['released'] and pending['samples'] < BLUR_MAX_SAMPLES:
                try:
                    import BigWorld
                    import Keys
                    held = bool(BigWorld.isKeyDown(Keys.KEY_LEFTMOUSE))
                except Exception:
                    pass
            pending['samples'] += 1
            if held:
                schedule()
            elif not pending['released']:
                # Let the opening button's mouse-release command toggle this window
                # before blur cleanup. A long press must not close/reopen it.
                pending['released'] = True
                schedule()
            else:
                self._blur_pending = None
                self.close()

        def schedule():
            try:
                import BigWorld
                self._blur_callback = BigWorld.callback(BLUR_POLL_DELAY, dismiss)
            except Exception:
                # Never destroy a native window inside its focus dispatcher.
                # Capture is already cancelled; another close can retry cleanup.
                self._blur_pending = None
                self._warn()

        schedule()

    def _diagnose_layout(self, stage, target=None, accepted=None):
        if self._layout_logs >= 6:
            return
        self._layout_logs += 1
        try:
            native = self._window
            LOG.info('AimTimer settings layout stage=%s client=%s parent=%s native=%s '
                     'document=%s anchor=%s target=%s position=%s accepted=%s',
                     stage, self._viewport(),
                     _dimensions(self._parent.size) if self._parent is not None else None,
                     _dimensions(native.size) if native is not None else None,
                     self._reported_size, (self._anchor, self._anchor_y), target,
                     native.position if native is not None else None, accepted)
        except Exception:
            self._warn()

    def report_layout(self, width, height):
        size = _dimensions((width, height))
        if size is None or not self.is_open():
            return False
        viewport = self._viewport()
        fit = _fit_geometry(viewport)
        limits = ((viewport['width'], viewport['height']) if self._editor_active
                  else fit[2] if fit is not None else (0, 0))
        if min(limits) < 1 or any(actual > limit for actual, limit in zip(size, limits)):
            return False
        changed = size != self._reported_size
        self._reported_size = size
        self._reported_viewport = (viewport['width'], viewport['height'], viewport['scale'])
        if changed:
            self._diagnose_layout('document')
        self._place()
        return True

    def _place(self):
        if not self.is_open():
            return False
        from frameworks.wulf import WindowStatus
        if self._window.windowStatus != WindowStatus.LOADED:
            return False
        viewport = self._viewport()
        width, height = viewport['width'], viewport['height']
        if self._editor_active:
            if width <= 0 or height <= 0:
                return False
            # Gameface viewEnv.resizeViewPx owns texture sizing; the native
            # window only needs the matching fullscreen origin.
            accepted = self._window.move(0, 0) is not False
            self._refresh_preview()
            self._diagnose_layout('editor', (0, 0), accepted)
            return accepted
        fit = _fit_geometry(viewport)
        if fit is None:
            return False
        scale = viewport['scale']
        size, gutter, available = fit
        signature = (width, height, scale)
        if (self._reported_size is not None and self._reported_viewport == signature and
                all(actual <= limit for actual, limit in zip(self._reported_size, available))):
            size = self._reported_size
        # Native defaults (256px or fullscreen) are observations, not the
        # intended document bounds. They must not override the fitted layout.
        left = int(round(self._anchor * width - size[0] / 2.0))
        bottom = (self._anchor_y * height - POPUP_GAP * scale if self._anchor_y is not None
                  else height - (64 + POPUP_GAP) * scale)
        top = int(round(bottom - size[1]))
        target = (max(gutter, min(width - gutter - size[0], left)),
                  max(gutter, min(height - gutter - size[1], top)))
        # Verified WindowImpl.move(x, y, xAnchor=LEFT, yAnchor=TOP).
        accepted = self._window.move(target[0], target[1]) is not False
        self._diagnose_layout('place', target, accepted)
        return accepted

    def _on_ready(self, native):
        if native is not self._window or not self.is_open():
            return False
        self._place()
        return True

    def _on_size(self, unique_id, width, height):
        size = _dimensions((width, height))
        if size is not None:
            self._size = size
            self._diagnose_layout('native_size')
            self._place()

    def _on_parent_size(self, *args):
        if self.is_open():
            self.update(self._state)
            self._place()

    def _on_focus(self, focused):
        if self._battle_mode:
            # Ctrl transitions and temporary native focus changes must not
            # discard the form or its unsaved input. Native GUI-control
            # ownership keeps the cursor usable without holding Ctrl.
            self._cancel_blur()
            return
        if focused is False and self.is_open():
            self._schedule_blur()
        elif focused is True:
            self._cancel_blur()

    def _on_status(self, native, status):
        from frameworks.wulf import WindowStatus
        if native is self._window and status in (WindowStatus.DESTROYING, WindowStatus.DESTROYED):
            self._native_released(native)

    def _native_released(self, native):
        if native is not self._window:
            return
        # A native DESTROYING notification is already tearing down this
        # surface. A reentrant root close must not call native destroy again.
        destroying = self._destroying
        self._destroying = True
        try:
            self._closing = True
            self._cancel_editor()
            self._finish_diagnostic_request('superseded')
            self._diagnose_close()
            self._editor_active = self._editor_target = False
            self._close_preview()
            self._cancel_blur()
            self._release_battle_input()
            self._notify_close()
            self._detach()
            if self._model is not None:
                self._model.deactivate()
            self._model = self._parent = None
            if self._released(native):
                self._window = None
        finally:
            self._destroying = destroying

    def update(self, state):
        if not _valid_state(state):
            self._warn()
            return False
        self._state = state
        if self._model is not None and self.is_open():
            try:
                return self._model.setState(self._payload())
            except Exception:
                self._warn()
        return False

    def open(self, anchor=0.5, anchor_y=None):
        if self._destroying:
            return False
        try:
            if isinstance(anchor, bool):
                return False
            anchor = float(anchor)
            if math.isnan(anchor) or math.isinf(anchor) or not 0 <= anchor <= 1:
                return False
            if anchor_y is not None:
                if isinstance(anchor_y, bool):
                    return False
                anchor_y = float(anchor_y)
                if math.isnan(anchor_y) or math.isinf(anchor_y) or not 0 <= anchor_y <= 1:
                    return False
            self._anchor = anchor
            self._anchor_y = anchor_y
            current_parent = _main_window()
            if current_parent is None:
                if self.is_open():
                    self.close(notify=False)
                return False
            if self.is_open() and self._parent is not current_parent:
                if not self.close(notify=False):
                    return False
            if self._window is not None and not self.is_open():
                if not self.close(notify=False):
                    return False
            if self.is_open():
                self.update(self._get_state())
                self._place()
                return True
            self._generation += 1
            self._parent = current_parent
            if self._parent is None:
                return False
            state = self._get_state()
            if not _valid_state(state):
                return False
            self._state = state
            self._battle_mode = json.loads(state).get('context') == 'battle'
            generation = self._generation
            self._closing = False
            self._notified = False
            self._layout_logs = 0
            self._reported_size = None
            self._reported_viewport = None
            self._editor_active = self._editor_target = False
            self._editor_request_seen = self._editor_request_ack = 0
            self._editor_request_accepted = True
            self._preview_mode, self._preview_variant = 'arcade', 'standard'
            self._preview_scene_id, self._preview_zoom_step = 'arcade', 1
            self._preview_focus = DEFAULT_FOCUS

            def dispatch(arg):
                if generation == self._generation and self.is_open():
                    getter = getattr(arg, 'get', None)
                    if callable(getter) and getter('action') == 'layout':
                        self.report_layout(getter('width'), getter('height'))
                    elif callable(getter) and getter('action') in ('editor', 'preview'):
                        self._dispatch_editor_request(getter('action'), getter)
                    elif callable(getter) and getter('action') == 'focus_demo':
                        self._play_focus_demo()
                    else:
                        self._on_action(arg)

            model = build_model_class()(self._payload(), dispatch)
            content = build_view_class()(_layout_id(), model)
            native = build_window_class()(content, self._parent,
                                          self._on_ready, self._native_released,
                                          is_battle=self._battle_mode)
            self._model, self._window, self._size = model, native, None
            for event, callback in (
                    (getattr(native, 'onSizeChanged', None), self._on_size),
                    (getattr(native, 'onFocusChanged', None), self._on_focus),
                    (getattr(native, 'onStatusChanged', None),
                     lambda status: self._on_status(native, status)),
                    (getattr(self._parent, 'onSizeChanged', None), self._on_parent_size)):
                self._attach(event, callback)
            if not self._acquire_battle_input():
                self.close()
                return False
            native.load()
            return self.is_open()
        except Exception:
            self._warn()
            self.close()
            return False

    def close(self, notify=True):
        if self._destroying:
            return False
        self._destroying = True
        native = self._window
        self._closing = native is not None
        try:
            if notify:
                self._notify_close()
            else:
                self._notified = True
            self._generation += 1
            self._cancel_editor()
            self._finish_diagnostic_request('superseded')
            self._diagnose_close()
            self._editor_active = self._editor_target = False
            self._close_preview()
            self._cancel_blur()
            self._release_battle_input()
            self._detach()
            if self._model is not None:
                self._model.deactivate()
            self._model = self._parent = None
            if native is not None and not self._released(native):
                try:
                    native.destroy()
                except Exception:
                    self._warn()
            if native is None or self._released(native):
                self._window = None
                self._closing = False
                return True
            return False
        finally:
            self._destroying = False
