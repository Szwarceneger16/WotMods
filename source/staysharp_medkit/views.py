# -*- coding: utf-8 -*-
"""Small registered Gameface settings window with its own native input surface.

Uses the proven sessionstats WindowImpl/ViewImpl resource pattern. No native
footer sizing, hit paddings, HTML or other mod state is changed.
"""
from __future__ import absolute_import, unicode_literals

import json
import logging
import math

LOG = logging.getLogger('staysharp.medkit')
LAYOUT_PATH = ('mods', 'grz', 'staysharp_medkit', 'views', 'Settings')
LOGICAL_SIZE = (360, 232)
EDGE_GUTTER = 16
POPUP_GAP = 24
MAX_DIMENSION = 32768
MAX_STATE_CHARS = 16384
BLUR_POLL_DELAY = 0.02
BLUR_MAX_SAMPLES = 150
try:
    text_types = (basestring,)
except NameError:
    text_types = (str,)


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
        raise ValueError('Invalid registered Medkit resource')
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
                    LOG.warning('Medkit settings command unavailable.')

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
        def __init__(self, content, parent, on_ready, on_released):
            self._medkit_ready = on_ready
            self._medkit_released = on_released
            super(SettingsNativeWindow, self).__init__(
                WindowFlags.WINDOW, content=content, layer=WindowLayer.WINDOW,
                name=str('GrzStaySharpSettings'), parent=parent)

        def _onReady(self):
            try:
                if self._medkit_ready(self) is not False:
                    self.show(True)
            except Exception:
                LOG.warning('Medkit settings readiness unavailable.')

        def _finalize(self):
            try:
                try:
                    self._medkit_released(self)
                except Exception:
                    LOG.warning('Medkit settings close notification unavailable.')
            finally:
                super(SettingsNativeWindow, self)._finalize()

    return SettingsNativeWindow


class SettingsWindow(object):
    def __init__(self, on_action, get_state):
        self._on_action = on_action
        self._get_state = get_state
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

    def _warn(self):
        if not self._warned:
            self._warned = True
            LOG.warning('Medkit settings window unavailable; battle reminder remains active.')

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
        return json.dumps(payload, ensure_ascii=True, allow_nan=False,
                          separators=(',', ':'), sort_keys=True)

    def _released(self, window):
        try:
            from frameworks.wulf import WindowStatus
            return window.proxy is None or window.windowStatus == WindowStatus.DESTROYED
        except Exception:
            return False

    def is_open(self):
        return self._window is not None and not self._closing and not self._released(self._window)

    def is_capture_allowed(self):
        if not self.is_open():
            return False
        try:
            from frameworks.wulf import WindowStatus
            return (self._window.windowStatus == WindowStatus.LOADED and
                    self._window.isFocused is True and not self._window.isHidden())
        except Exception:
            return False

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
                # Let the footer's mouse-release command toggle this window
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
            LOG.info('Medkit settings layout stage=%s client=%s parent=%s native=%s '
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
        if fit is None or any(actual > limit for actual, limit in zip(size, fit[2])):
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
        if focused is False and self.is_open():
            self._notify('cancel_capture')
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
            self._cancel_blur()
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
            if self._window is not None and not self.is_open():
                if not self.close(notify=False):
                    return False
            if self.is_open():
                self.update(self._get_state())
                self._place()
                return True
            self._generation += 1
            self._parent = _main_window()
            if self._parent is None:
                return False
            state = self._get_state()
            if not _valid_state(state):
                return False
            self._state = state
            generation = self._generation
            self._closing = False
            self._notified = False
            self._layout_logs = 0
            self._reported_size = None
            self._reported_viewport = None

            def dispatch(arg):
                if generation == self._generation and self.is_open():
                    getter = getattr(arg, 'get', None)
                    if callable(getter) and getter('action') == 'layout':
                        self.report_layout(getter('width'), getter('height'))
                    else:
                        self._on_action(arg)

            model = build_model_class()(self._payload(), dispatch)
            content = build_view_class()(_layout_id(), model)
            native = build_window_class()(content, self._parent,
                                          self._on_ready, self._native_released)
            self._model, self._window, self._size = model, native, None
            for event, callback in (
                    (getattr(native, 'onSizeChanged', None), self._on_size),
                    (getattr(native, 'onFocusChanged', None), self._on_focus),
                    (getattr(native, 'onStatusChanged', None),
                     lambda status: self._on_status(native, status)),
                    (getattr(self._parent, 'onSizeChanged', None), self._on_parent_size)):
                self._attach(event, callback)
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
            self._cancel_blur()
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
