# -*- coding: utf-8 -*-
"""Native registered Gameface window; no OpenWG dependency on this path.

Integration pattern adapted from przemyslaw-zan/zanju-wot-mods (GPL-3.0),
mods/campaign-tracker/src/zanju_ct/gameface/card_window.py, especially
build_model_class/build_view_class/build_window_class/_main_window/_layout_id.
Client resource: R.mods.grz.sessionstats.views.SessionStats, registered by
this package's gui/gen_resources/grz.sessionstats.json (WoT 2.4.1).

v0.2.2: position the real native surface with WindowImpl.move and retain the
user's placement after a native title-bar drag. HTML initiates the client's
GFViewEventProxy MOVE event; Python never simulates mouse movement.
Exact source references and observed limits: docs/UI_0.2.2_SOURCE_EVIDENCE.md.
"""
from __future__ import absolute_import, unicode_literals

import json
import logging
import math

LOG = logging.getLogger('grz.sessionstats')
LAYOUT_PATH = ('mods', 'grz', 'sessionstats', 'views', 'SessionStats')
LOGICAL_SIZE = (700, 620)
MAX_DIMENSION = 32768
DIAGNOSTIC_STAGES = ('dom_ready', 'model_bound', 'layout_ready')


def _read(arg, key):
    getter = getattr(arg, 'get', None)
    if callable(getter):
        try:
            return getter(key)
        except Exception:
            return None
    return None


def _positive(value, maximum=MAX_DIMENSION):
    if isinstance(value, bool):
        return None
    try:
        value = float(value)
        if math.isnan(value) or math.isinf(value) or value <= 0 or value > maximum:
            return None
        return value
    except (TypeError, ValueError, OverflowError):
        return None


def _dimensions(value):
    try:
        width, height = value
        width, height = _positive(width), _positive(height)
        if width is not None and height is not None:
            return (int(math.ceil(width)), int(math.ceil(height)))
    except (TypeError, ValueError, AttributeError):
        pass
    return None


def _position(value):
    try:
        x, y = value
        x, y = float(x), float(y)
        if (not math.isnan(x) and not math.isnan(y) and
                not math.isinf(x) and not math.isinf(y) and
                abs(x) <= MAX_DIMENSION and abs(y) <= MAX_DIMENSION):
            return (int(round(x)), int(round(y)))
    except (TypeError, ValueError, OverflowError):
        pass
    return None


def build_model_class():
    from frameworks.wulf import ViewModel

    class SessionStatsModel(ViewModel):
        def __init__(self, payload, on_action):
            self._payload = payload
            self._on_action = on_action
            super(SessionStatsModel, self).__init__(properties=1, commands=1)

        def _initialize(self):
            super(SessionStatsModel, self)._initialize()
            self._addStringProperty(str('payload'), self._payload)
            self.onAction = self._addCommand(str('onAction'))
            self.onAction += self._dispatch

        def _dispatch(self, *args):
            # Never interrupt native command dispatch or other listeners.
            try:
                self._on_action(args[0] if args else None)
            except Exception:
                LOG.exception('Statistics command failed.')

        def setPayload(self, payload):
            self._payload = payload
            self._setString(0, payload)

    return SessionStatsModel


def build_view_class():
    from frameworks.wulf import ViewFlags, ViewSettings
    from gui.impl.pub import ViewImpl

    class SessionStatsView(ViewImpl):
        def __init__(self, layout_id, model):
            self._model = model
            super(SessionStatsView, self).__init__(ViewSettings(
                layoutID=layout_id, flags=ViewFlags.VIEW, model=model))

        @property
        def viewModel(self):
            return self._model

    return SessionStatsView


def build_window_class():
    from frameworks.wulf import WindowFlags, WindowLayer
    from gui.impl.pub import WindowImpl

    class SessionStatsNativeWindow(WindowImpl):
        def __init__(self, content, parent, on_ready=None):
            self._grz_on_ready = on_ready
            super(SessionStatsNativeWindow, self).__init__(
                WindowFlags.WINDOW, content=content, layer=WindowLayer.WINDOW,
                name=str('GrzSessionStats'), parent=parent)

        def _onReady(self):
            # Place before first paint, without a JS round trip. The actual
            # texture-size event corrects the initial placement after layout.
            # A close while loading must not allow a late ready event to show
            # the old window over a newly opened one.
            try:
                if self._grz_on_ready is not None and self._grz_on_ready(self) is False:
                    return
            except Exception:
                LOG.exception('GRZ UI: native readiness callback failed.')
            # Shown native windows receive animation frames for later DOM
            # measurement; keeping one hidden while awaiting JS would deadlock.
            self.show(True)

    return SessionStatsNativeWindow


def _layout_id():
    from gui.impl.gen import R
    node = R
    for name in LAYOUT_PATH:
        node = getattr(node, name)
    layout_id = int(node())
    if layout_id < 0:
        raise ValueError('Invalid registered statistics resource')
    return layout_id


def _main_window():
    from frameworks.wulf import WindowStatus
    from helpers import dependency
    from skeletons.gui.impl import IGuiLoader
    parent = dependency.instance(IGuiLoader).windowsManager.getMainWindow()
    if parent is None or parent.proxy is None or parent.windowStatus != WindowStatus.LOADED:
        return None
    return parent


def _interface_scale():
    # IGuiLoader.scale is the resolved native scale. Reading the setting itself
    # could return 0 for "automatic" or revalidate/change a graphics setting.
    try:
        from helpers import dependency
        from skeletons.gui.impl import IGuiLoader
        return _positive(dependency.instance(IGuiLoader).scale, 16) or 1.0
    except (ImportError, AttributeError, RuntimeError):
        return 1.0


class StatsWindow(object):
    def __init__(self, snapshot, on_action):
        self._snapshot = snapshot
        self._on_action = on_action
        self._window = None
        self._closing = False
        self._destroying = False
        self._view = None
        self._model = None
        self._parent = None
        self._events = []
        self._generation = 0
        self._watchdog_id = None
        self._reported_size = None
        self._native_size = None
        self._published_viewport = None
        self._center_signature = None
        self._expected_position = None
        self._user_position = False
        self._drag_active = False
        self._diagnostic_once = set()
        self._renderer_stages = set()
        self._size_logs = 0

    def is_open(self):
        window = self._window
        if window is None:
            return False
        if self._closing:
            # A failed/asynchronous destroy still owns a native input surface.
            return not self._released(window)
        try:
            from frameworks.wulf import WindowStatus
            return window.proxy is not None and window.windowStatus not in (
                WindowStatus.DESTROYING, WindowStatus.DESTROYED)
        except (ImportError, AttributeError, RuntimeError):
            return False

    def _log_once(self, key, level, message, *args):
        if key not in self._diagnostic_once:
            self._diagnostic_once.add(key)
            LOG.log(level, message, *args)

    def _viewport(self, parent=None):
        parent = parent if parent is not None else self._parent
        size = None
        if parent is not None:
            try:
                if parent.proxy is not None:
                    size = _dimensions(parent.size)
            except (AttributeError, RuntimeError):
                pass
        if size is None:
            # The game API reports the current client surface, not a desktop
            # monitor's native resolution. Do not infer a size from settings.
            try:
                import GUI
                size = _dimensions(GUI.screenResolution())
            except (ImportError, AttributeError, RuntimeError):
                pass
        return {'width': size[0] if size else 0, 'height': size[1] if size else 0,
                'scale': _interface_scale()}

    def _payload(self, parent=None):
        # Physical parent bounds and the current resolved scale are authoritative
        # for responsive HTML, including the first 1x1 loading frame.
        payload = dict(self._snapshot())
        viewport = self._viewport(parent)
        payload['viewport'] = viewport
        self._published_viewport = viewport
        return json.dumps(payload, ensure_ascii=True, separators=(',', ':'), allow_nan=False)

    def _attach(self, event, callback):
        if event is None:
            return False
        generation = self._generation
        active = [True]
        name = getattr(callback, '__name__', 'listener')

        def guarded(*args, **kwargs):
            # Optional Wulf notifications must not interrupt the native event
            # dispatcher when a later client changes their contract. A failed
            # unsubscribe must not let an old window modify a newly opened one.
            if not active[0] or generation != self._generation:
                return
            try:
                return callback(*args, **kwargs)
            except Exception:
                self._log_once('event_dispatch_' + name, logging.WARNING,
                               'GRZ UI: optional native notification %s unavailable; document controls remain active.', name)

        try:
            event += guarded
        except Exception:
            active[0] = False
            # Some adapters can add a listener before reporting an error.
            try:
                event -= guarded
            except Exception:
                pass
            self._log_once('event_attach_' + name, logging.WARNING,
                           'GRZ UI: optional native notification %s could not be subscribed.', name)
            return False
        if generation != self._generation or self._closing:
            active[0] = False
            try:
                event -= guarded
            except Exception:
                pass
            return False
        self._events.append((event, guarded, active))
        return True

    def _detach(self):
        while self._events:
            event, callback, active = self._events.pop()
            active[0] = False
            try:
                event -= callback
            except Exception:
                self._log_once('event_detach', logging.WARNING,
                               'GRZ UI: native listener could not be removed; retained callback is inactive.')

    def _cancel_watchdog(self):
        callback_id = self._watchdog_id
        self._watchdog_id = None
        self._cancel_callback(callback_id)

    def _cancel_callback(self, callback_id):
        if callback_id is not None:
            try:
                import BigWorld
                BigWorld.cancelCallback(callback_id)
            except (ImportError, AttributeError, RuntimeError, TypeError, ValueError):
                pass

    def _released(self, window):
        try:
            if window.proxy is None:
                return True
            from frameworks.wulf import WindowStatus
            return window.windowStatus == WindowStatus.DESTROYED
        except Exception:
            # An unavailable native property is not confirmation of release.
            return False

    def _discard(self):
        self._invalidate()
        self._window = None
        self._closing = False

    def _invalidate(self):
        # Invalidate before native cancellation/unsubscription can reenter us.
        self._generation += 1
        self._cancel_watchdog()
        self._detach()
        self._view = self._model = self._parent = None
        self._reported_size = self._native_size = None
        self._published_viewport = self._center_signature = None
        self._expected_position = None
        self._user_position = self._drag_active = False

    def _window_size(self):
        if self.is_open():
            try:
                return _dimensions(self._window.size)
            except (AttributeError, RuntimeError):
                pass
        return None

    def _window_position(self):
        if self.is_open():
            try:
                return _position(self._window.position)
            except (AttributeError, RuntimeError):
                pass
        return None

    def _fallback_size(self, viewport):
        scale = viewport['scale']
        requested = self._reported_size or tuple(int(math.ceil(value * scale)) for value in LOGICAL_SIZE)
        # HTML is responsible for sizing its texture. Before its first report,
        # use our known design size instead of the native full-screen default.
        return tuple(min(value, max(1, viewport[key] - 20)) if viewport[key] > 0 else value
                     for value, key in zip(requested, ('width', 'height')))

    def _center(self, reason, force=False):
        if not self.is_open() or self._user_position or self._drag_active:
            return False
        native = self._window
        from frameworks.wulf import WindowStatus
        if native.windowStatus != WindowStatus.LOADED:
            # An early native resize can arrive before the area owns the
            # window. _onReady will place it once loading is complete.
            return False
        viewport = self._viewport()
        actual_size = self._window_size() or self._native_size
        size = self._reported_size or actual_size
        if size is None or size == (viewport['width'], viewport['height']) or min(size) <= 1:
            size = self._fallback_size(viewport)
        signature = (size, viewport['width'], viewport['height'], viewport['scale'], self._reported_size)
        if viewport['width'] > 0 and viewport['height'] > 0:
            width, height = size
            left = max(0, int((viewport['width'] - width) // 2))
            top = max(0, int((viewport['height'] - height) // 2))
            target = (left, top)
            observed = self._window_position()
            if not force and signature == self._center_signature and observed == target:
                return True
            # Same pattern as the author's native card: explicit parent-space
            # coordinates, using measured DOM pixels once available. Native
            # center() returning successfully would not establish those exact
            # bounds; do not infer the observed placement from a return value.
            accepted = self._move(target)
            observed = self._window_position()
            if accepted and observed == target:
                self._center_signature = signature
            self._log_once('placement_' + reason, logging.INFO,
                           'GRZ UI: placement %s requested=%s accepted=%s observed=%s viewport=%sx%s scale=%s native_size=%s document_size=%s.',
                           reason, target, accepted, observed, viewport['width'], viewport['height'],
                           viewport['scale'], actual_size, self._reported_size)
            if not accepted:
                self._log_once('move_failed', logging.WARNING, 'GRZ UI: native area refused explicit placement.')
            return accepted
        else:
            self._log_once('viewport_unknown', logging.WARNING,
                           'GRZ UI: no valid parent bounds for placement.')
            return False

    def _move(self, target):
        self._expected_position = target
        try:
            return self._window.move(target[0], target[1]) is not False
        except (AttributeError, RuntimeError, TypeError, ValueError):
            return False

    def _keep_visible(self):
        if not self.is_open() or self._drag_active:
            return
        position = self._window_position()
        size = self._reported_size or self._window_size()
        viewport = self._viewport()
        if position is None or size is None or viewport['width'] <= 0 or viewport['height'] <= 0:
            return
        target = (max(0, min(max(0, viewport['width'] - size[0]), position[0])),
                  max(0, min(max(0, viewport['height'] - size[1]), position[1])))
        # A smaller client window may put the title bar beyond an edge. Clamp
        # only when needed; ordinary model and surface updates keep the exact
        # position selected by the player, rather than recentering it.
        if target != position:
            self._move(target)

    def _place(self, reason, force=False):
        if self._user_position:
            self._keep_visible()
        else:
            self._center(reason, force)

    def _on_native_position(self, unique_id, x, y):
        if not self.is_open():
            return
        position = _position((x, y))
        if position is not None and position == self._expected_position:
            self._log_once('position_observed', logging.INFO,
                           'GRZ UI: native position confirmed at %s.', position)
        self._finish_watchdog_if_ready()

    def _finish_watchdog_if_ready(self):
        if not all(item in self._renderer_stages for item in DIAGNOSTIC_STAGES):
            return
        if self._reported_size is None or self._window_size() != self._reported_size:
            return
        if self._user_position or self._window_position() == self._expected_position:
            self._cancel_watchdog()

    def _on_drag(self, active):
        if active in (True, 'true', 'True', '1'):
            self._drag_active = True
            self._user_position = True
            self._center_signature = None
            self._log_once('drag_started', logging.INFO, 'GRZ UI: native title-bar drag started.')
            self._finish_watchdog_if_ready()
        elif active in (False, 'false', 'False', '0'):
            was_active = self._drag_active
            self._drag_active = False
            if was_active:
                self._log_once('drag_finished', logging.INFO,
                               'GRZ UI: native title-bar drag finished at %s.', self._window_position())
                self._keep_visible()

    def _on_ready(self, native):
        if native is not self._window or self._closing or not self.is_open():
            return False
        self._log_once('native_ready', logging.INFO, 'GRZ UI: native window ready.')
        self._center('ready', force=True)
        generation = self._generation
        self._cancel_watchdog()
        try:
            import BigWorld
            callback_id = BigWorld.callback(5.0, lambda: self._check_renderer(generation))
            if generation != self._generation or native is not self._window or self._closing:
                self._cancel_callback(callback_id)
                return False
            self._watchdog_id = callback_id
            self._finish_watchdog_if_ready()
        except (ImportError, AttributeError, RuntimeError):
            pass
        return True

    def _check_renderer(self, generation):
        if generation != self._generation or not self.is_open():
            return
        self._watchdog_id = None
        missing = [stage for stage in DIAGNOSTIC_STAGES if stage not in self._renderer_stages]
        if missing:
            self._log_once('renderer_timeout', logging.WARNING,
                           'GRZ UI: renderer handshake incomplete after 5 s; missing=%s native_size=%s reported_size=%s.',
                           ','.join(missing), self._window_size(), self._reported_size)
        if not self._user_position and self._expected_position is not None:
            observed = self._window_position()
            if observed != self._expected_position:
                self._log_once('position_unconfirmed', logging.WARNING,
                               'GRZ UI: native position differs from request; requested=%s observed=%s native_size=%s document_size=%s.',
                               self._expected_position, observed, self._window_size(), self._reported_size)
        if self._reported_size is not None and self._window_size() != self._reported_size:
            self._log_once('surface_unconfirmed', logging.WARNING,
                           'GRZ UI: native surface differs from document; native_size=%s document_size=%s.',
                           self._window_size(), self._reported_size)

    def _on_native_size(self, unique_id, width, height):
        if not self.is_open():
            return
        size = _dimensions((width, height))
        if size is None:
            return
        if size != self._native_size and self._size_logs < 4:
            LOG.info('GRZ UI: native surface resized to %sx%s.', size[0], size[1])
            self._size_logs += 1
        self._native_size = size
        self._place('native_resize')
        self._finish_watchdog_if_ready()

    def _on_parent_size(self, *args):
        if self.is_open():
            # A changed parent includes a game-window resize. Republish bounds
            # and resolved scale so the document can resize to fit that window.
            self.refresh()
            self._place('parent_resize', force=True)

    def _on_native_status(self, native, status):
        if native is not self._window:
            return
        from frameworks.wulf import WindowStatus
        if status == WindowStatus.DESTROYED:
            self._log_once('native_released', logging.INFO, 'GRZ UI: native window released.')
            self._discard()
        elif status == WindowStatus.DESTROYING:
            self._closing = True
            self._invalidate()

    def _handle_action(self, generation, arg):
        if generation != self._generation or not self.is_open():
            return
        action = _read(arg, 'action')
        if action == 'diagnostic':
            stage = _read(arg, 'stage')
            if stage in DIAGNOSTIC_STAGES:
                self._renderer_stages.add(stage)
                self._log_once('renderer_' + stage, logging.INFO,
                               'GRZ UI: renderer %s width=%s height=%s scale=%s.', stage,
                               _positive(_read(arg, 'width')), _positive(_read(arg, 'height')),
                               _positive(_read(arg, 'scale'), 16))
                self._finish_watchdog_if_ready()
            return
        if action not in ('close', 'resize', 'refresh', 'reset', 'page', 'sort', 'language', 'viewport', 'drag'):
            return
        self._log_once('command_' + action, logging.INFO, 'GRZ UI: command %s received.', action)
        if action == 'close':
            self.close()
        elif action == 'resize':
            self.resize(_read(arg, 'width'), _read(arg, 'height'))
        elif action == 'viewport':
            self.refresh()
            self._place('viewport', force=True)
        elif action == 'drag':
            self._on_drag(_read(arg, 'active'))
        else:
            self._on_action(arg)

    def open(self):
        if self._destroying:
            return False
        if self._closing or (self._window is not None and not self.is_open()):
            self.close()
            if self._window is not None:
                return False
        if self.is_open():
            self.refresh()
            from frameworks.wulf import WindowStatus
            if self._window.windowStatus == WindowStatus.LOADED:
                self._place('reopen', force=True)
                self._window.show(True)
            return True
        self._discard()
        self._diagnostic_once.clear()
        self._renderer_stages.clear()
        self._size_logs = 0
        try:
            parent = _main_window()
            if parent is None:
                return False
            self._parent = parent
            layout_id = _layout_id()
            generation = self._generation
            self._model = build_model_class()(self._payload(parent),
                                             lambda arg: self._handle_action(generation, arg))
            self._view = build_view_class()(layout_id, self._model)
            native = build_window_class()(self._view, parent, self._on_ready)
            self._window = native
            if generation != self._generation:
                self.close()
                return False
            for event, callback in (
                    (getattr(native, 'onSizeChanged', None), self._on_native_size),
                    (getattr(native, 'onPositionChanged', None), self._on_native_position),
                    (getattr(parent, 'onSizeChanged', None), self._on_parent_size),
                    (getattr(native, 'onStatusChanged', None),
                     lambda status: self._on_native_status(native, status))):
                self._attach(event, callback)
                if generation != self._generation or self._window is not native or self._closing:
                    return False
            LOG.info('GRZ UI: opening registered layout=%s viewport=%s.', layout_id, self._published_viewport)
            native.load()
            return self.is_open()
        except Exception:
            LOG.exception('Could not create the registered statistics window.')
            self.close()
            return False

    def refresh(self):
        if not self.is_open() or self._model is None:
            return
        try:
            with self._model.transaction() as live:
                live.setPayload(self._payload())
        except Exception:
            LOG.exception('Could not update the statistics view model.')

    def resize(self, width, height):
        if self._closing or not self.is_open():
            return
        size = _dimensions((width, height))
        if size is None:
            self._log_once('invalid_resize', logging.WARNING, 'GRZ UI: invalid renderer dimensions ignored.')
            return
        self._reported_size = size
        # The event from Wulf remains the authoritative actual surface size;
        # this report is useful for fallback placement and bridge diagnostics.
        self._place('renderer_resize')
        if self._viewport() != self._published_viewport:
            self.refresh()

    def close(self):
        # Keep ownership until native release is confirmed. Retrying close (or
        # opening later) must not orphan a visible window after destroy raises.
        if self._destroying:
            return
        window = self._window
        self._closing = window is not None
        self._destroying = True
        try:
            self._invalidate()
            if window is not None and not self._released(window):
                try:
                    window.destroy()
                except Exception:
                    LOG.exception('Could not destroy the statistics window; cleanup will be retried.')
        finally:
            if window is None or self._released(window):
                self._window = None
                self._closing = False
            self._destroying = False
