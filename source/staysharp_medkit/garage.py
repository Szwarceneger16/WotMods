# -*- coding: utf-8 -*-
"""Optional settings child of the native LobbyFooter Gameface document.

Uses the same OpenWG child-model contract as the session statistics footer.
No keyboard hooks or independent GUI.Simple roots are installed here. The
runtime handles primitive hotkey capture and persists accepted settings.
"""
from __future__ import absolute_import, unicode_literals

import json
import logging
import math
import weakref

try:
    text_types = (basestring,)
    number_types = (int, long, float)
except NameError:
    text_types = (str,)
    number_types = (int, float)

LOG = logging.getLogger('staysharp.medkit')
POSITION_ID = 0x47525A4D
INJECT_NAME = 'grz_staysharp_medkit_footer'
DATA_PROPERTY = 'grzMedkitFooter'
MODULE_URL = 'coui://gui/gameface/mods/staysharp_medkit/footer.js'
STYLE_URL = 'coui://gui/gameface/mods/staysharp_medkit/footer.css'
MAX_PAYLOAD_CHARS = 16384
ACTIONS = frozenset(('open', 'close', 'begin_capture', 'cancel_capture', 'clear_binding'))
BINDINGS = frozenset(('toggle_mod', 'toggle_voice'))
PAYLOAD_KEYS = frozenset(('version', 'hotkeys', 'display', 'capturing', 'preview', 'status',
                          'error', 'labels', 'enabled', 'voice_enabled'))
_installed = None


def _payload_json(payload):
    if not isinstance(payload, dict):
        return None
    try:
        selected = dict((key, value) for key, value in payload.items() if key in PAYLOAD_KEYS)
        serialized = json.dumps(selected, ensure_ascii=True, allow_nan=False,
                                sort_keys=True, separators=(',', ':'))
        return serialized if len(serialized) <= MAX_PAYLOAD_CHARS else None
    except (TypeError, ValueError, OverflowError, RuntimeError):
        return None


def _command(arg):
    # Wulf passes a mapping-like command argument. Read only named primitive
    # fields; never retain the native argument or a game input-event object.
    getter = getattr(arg, 'get', None)
    if not callable(getter):
        return None
    try:
        action = getter('action')
        if not isinstance(action, text_types) or action not in ACTIONS:
            return None
        binding = getter('binding')
        if action in ('begin_capture', 'clear_binding'):
            if not isinstance(binding, text_types) or binding not in BINDINGS:
                return None
        elif binding is not None:
            if not isinstance(binding, text_types) or binding not in BINDINGS:
                return None
        result = {'action': action}
        if binding is not None:
            result['binding'] = binding
        if action == 'open':
            for name in ('anchorX', 'anchorY'):
                anchor = getter(name)
                if anchor is not None:
                    if (isinstance(anchor, bool) or not isinstance(anchor, number_types) or
                            math.isnan(anchor) or math.isinf(anchor) or not 0 <= anchor <= 1):
                        return None
                    result[name] = float(anchor)
        return result
    except Exception:
        return None


def build_child_class(gf_mod_inject, on_action, on_unload):
    from frameworks.wulf import ViewModel
    from gui.impl.pub.view_component import ViewComponent

    class FooterCommands(ViewModel):
        def __init__(self):
            self._state = '{}'
            self._active = True
            super(FooterCommands, self).__init__(properties=1, commands=1)

        def _initialize(self):
            super(FooterCommands, self)._initialize()
            self._addStringProperty(str('state'), self._state)
            self.onAction = self._addCommand(str('onAction'))
            self.onAction += self._dispatch

        def setState(self, payload):
            if not self._active or payload == self._state:
                return False
            with self.transaction():
                self._setString(0, payload)
            self._state = payload
            return True

        def _dispatch(self, *args):
            if self._active:
                on_action(args[0] if args else None)

        def deactivate(self):
            self._active = False

    class FooterHostModel(ViewModel):
        def __init__(self):
            super(FooterHostModel, self).__init__(properties=2, commands=0)

        def _initialize(self):
            super(FooterHostModel, self)._initialize()
            gf_mod_inject(self, str(INJECT_NAME), styles=[str(STYLE_URL)],
                          modules=[str(MODULE_URL)])
            self._commands_model = FooterCommands()
            self._addViewModelProperty(str(DATA_PROPERTY), self._commands_model)

        def setState(self, payload):
            return self._commands_model.setState(payload)

        def deactivate(self):
            self._commands_model.deactivate()

    class FooterChild(ViewComponent):
        def __init__(self):
            self._closed = False
            super(FooterChild, self).__init__(model=FooterHostModel)

        def set_state(self, payload):
            return self.getViewModel().setState(payload)

        def _closing(self):
            if self._closed:
                return
            self._closed = True
            try:
                self.getViewModel().deactivate()
            except Exception:
                LOG.warning('Medkit footer command cleanup unavailable.')
            try:
                on_unload()
            except Exception:
                LOG.warning('Medkit footer capture cancellation unavailable.')

        def _onUnloading(self, *args, **kwargs):
            self._closing()
            original = getattr(super(FooterChild, self), '_onUnloading', None)
            if callable(original):
                return original(*args, **kwargs)

        def _finalize(self, *args, **kwargs):
            self._closing()
            original = getattr(super(FooterChild, self), '_finalize', None)
            if callable(original):
                return original(*args, **kwargs)

    return FooterChild


class FooterInstallation(object):
    def __init__(self, footer_class, child_class, on_action, get_payload):
        for name in ('_onLoading', 'getChildView', '_registerChild', '_unregisterChild'):
            if not callable(getattr(footer_class, name, None)):
                raise TypeError('Native footer child contract unavailable: ' + name)
        self.footer_class = footer_class
        self.child_class = child_class
        self._on_action = on_action
        self._get_payload = get_payload
        self._enabled = True
        self._children = []
        self._state = '{}'
        self._settings = None
        self._warned = False
        self._defined_here = '_onLoading' in footer_class.__dict__
        self._original = footer_class._onLoading
        original = self._original
        installation = self

        def on_loading(view, *args, **kwargs):
            result = original(view, *args, **kwargs)
            if installation._enabled:
                try:
                    installation._attach(view)
                except Exception:
                    installation._warn()
            return result

        self._wrapper = on_loading
        footer_class._onLoading = on_loading

    def _warn(self):
        if not self._warned:
            self._warned = True
            LOG.warning('Medkit garage settings unavailable; battle reminder remains active.')

    def _refresh(self):
        if self._enabled and callable(self._get_payload):
            try:
                return self.update(self._get_payload())
            except Exception:
                self._warn()
        return False

    def dispatch(self, arg):
        if not self._enabled or not callable(self._on_action):
            return False
        command = _command(arg)
        if command is None:
            return False
        try:
            if (command['action'] == 'open' and self._settings is not None and
                    self._settings.is_open()):
                command = {'action': 'close'}
            # Close itself is a capture-cancellation action in the runtime.
            if self._on_action(command) is False:
                return False
            self._refresh()
            if command['action'] == 'open':
                if self._settings is None:
                    from .views import SettingsWindow
                    self._settings = SettingsWindow(self.dispatch, lambda: self._state)
                if not self._settings.open(command.get('anchorX', 0.5), command.get('anchorY')):
                    self._on_action({'action': 'close'})
                    self._refresh()
                    return False
            elif command['action'] == 'close' and self._settings is not None:
                self._settings.close(notify=False)
            return True
        except Exception:
            self._warn()
            if command['action'] == 'open':
                try:
                    self._on_action({'action': 'close'})
                    self._refresh()
                except Exception:
                    pass
            return False

    def cancel_capture(self):
        return self.dispatch({'action': 'cancel_capture'})

    def close_window(self):
        return self._settings.close() if self._settings is not None else True

    def is_capture_allowed(self):
        return bool(self._enabled and self._settings is not None and
                    self._settings.is_capture_allowed())

    def _push(self, child):
        try:
            child.set_state(self._state)
        except Exception:
            self._warn()

    def update(self, payload):
        if not self._enabled:
            return False
        serialized = _payload_json(payload)
        if serialized is None:
            self._warn()
            return False
        changed = serialized != self._state
        self._state = serialized
        retained = []
        for view_ref, child_ref in self._children:
            view, child = view_ref(), child_ref()
            if view is None or child is None:
                continue
            try:
                if view.getChildView(POSITION_ID) is not child:
                    continue
                retained.append((view_ref, child_ref))
                self._push(child)
            except Exception:
                retained.append((view_ref, child_ref))
                self._warn()
        self._children = retained
        if self._settings is not None:
            self._settings.update(serialized)
        return changed

    def _attach(self, view):
        child = None
        try:
            if view.getChildView(POSITION_ID) is not None:
                return
            self._refresh()
            child = self.child_class()
            if not self._enabled:
                return
            view._registerChild(POSITION_ID, child)
            if self._enabled and view.getChildView(POSITION_ID) is child:
                self._children.append((weakref.ref(view), weakref.ref(child)))
                self._push(child)
                return
        except Exception:
            self._warn()
        if child is not None and not self._remove_child(view, child):
            self._children.append((weakref.ref(view), weakref.ref(child)))

    def _remove_child(self, view, child):
        try:
            if view.getChildView(POSITION_ID) is not child:
                return True
            view._unregisterChild(child.uniqueID, True)
            return view.getChildView(POSITION_ID) is not child
        except Exception:
            self._warn()
            return False

    def uninstall(self):
        global _installed
        if self._enabled:
            self.cancel_capture()
        window_released = self.close_window()
        self._enabled = False
        self._on_action = None
        self._get_payload = None
        retained = []
        for view_ref, child_ref in self._children:
            view, child = view_ref(), child_ref()
            if view is not None and child is not None and not self._remove_child(view, child):
                retained.append((view_ref, child_ref))
        self._children = retained
        if self.footer_class.__dict__.get('_onLoading') is self._wrapper:
            if self._defined_here:
                self.footer_class._onLoading = self._original
            else:
                del self.footer_class._onLoading
        if _installed is self and not retained and window_released:
            _installed = None
        return not retained and window_released


def install(on_action, get_payload):
    global _installed
    if _installed is not None:
        if _installed._enabled:
            return _installed
        _installed.uninstall()
        if _installed is not None:
            return None
    try:
        from openwg_gameface import gf_mod_inject
        from gui.impl.lobby.page.lobby_footer import LobbyFooter
        holder = {}

        def dispatch(arg):
            current = holder.get('installation')
            return current.dispatch(arg) if current is not None else False

        def closing():
            current = holder.get('installation')
            if current is not None:
                current.cancel_capture()
                return current.close_window()
            return False

        child_class = build_child_class(gf_mod_inject, dispatch, closing)
        handle = FooterInstallation(LobbyFooter, child_class, on_action, get_payload)
        holder['installation'] = handle
        _installed = handle
        handle._refresh()
        return handle
    except Exception:
        LOG.warning('Medkit garage integration unavailable; battle reminder remains active.')
        return None


def update(payload):
    return _installed.update(payload) if _installed is not None else False


def uninstall():
    return _installed.uninstall() if _installed is not None else True


def close_window():
    return _installed.close_window() if _installed is not None else True


def is_capture_allowed():
    return _installed.is_capture_allowed() if _installed is not None else False
