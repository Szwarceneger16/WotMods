# -*- coding: utf-8 -*-
"""Optional, local child of the real LobbyFooter document.

OpenWG Gameface 1.2.2 gf_mod_inject supplies one model property. Our host
reserves that property plus the command model; no native footer model,
resource, HTML or SWF is replaced. The standalone window does not import
OpenWG and remains accessible through the configured keyboard shortcut.

Pattern adapted from przemyslaw-zan/zanju-wot-mods (GPL-3.0),
mods/directives-helper/src/zanju_dh/gameface/bar_probe_inject.py,
_ProbeHostModel/_probe_view_class/_patch. Native 2.4.1 class:
gui.impl.lobby.page.lobby_footer.LobbyFooter.
"""
from __future__ import absolute_import, unicode_literals

import json
import logging
import weakref

try:
    integer_types = (int, long)
    text_types = (basestring,)
except NameError:
    integer_types = (int,)
    text_types = (str,)

LOG = logging.getLogger('grz.sessionstats')
POSITION_ID = 0x47525A53
INJECT_NAME = 'grz_session_stats_footer'
DATA_PROPERTY = 'grzSessionFooter'
MODULE_URL = 'coui://gui/gameface/mods/grz_session_stats/footer.js'
STYLE_URL = 'coui://gui/gameface/mods/grz_session_stats/footer.css'
_installed = None
IDLE_ACTIVITY = '{"pending":0,"processing":false}'
MAX_APPEARANCE_CHARS = 65536


def _activity_json(pending_count, processing, labels=None):
    # The activity bridge carries counts/state only, never result/account data.
    if (isinstance(pending_count, bool) or
            not isinstance(pending_count, integer_types) or pending_count < 0):
        pending_count = 0
    payload = {'pending': pending_count, 'processing': processing is True}
    if labels:
        payload['labels'] = labels
    return json.dumps(payload,
                      sort_keys=True, separators=(',', ':'))


def build_child_class(gf_mod_inject, on_open):
    from frameworks.wulf import ViewModel
    from gui.impl.pub.view_component import ViewComponent

    class FooterCommands(ViewModel):
        def __init__(self):
            self._activity = IDLE_ACTIVITY
            self._appearance = ''
            super(FooterCommands, self).__init__(properties=2, commands=1)

        def _initialize(self):
            super(FooterCommands, self)._initialize()
            self._addStringProperty(str('activity'), self._activity)
            self._addStringProperty(str('appearance'), self._appearance)
            self.onAction = self._addCommand(str('onAction'))
            self.onAction += self._dispatch

        def setActivity(self, payload):
            if payload == self._activity:
                return False
            # The nested model owns the change notification. Commit its cache
            # only after the native transaction succeeds, allowing a retry.
            with self.transaction():
                self._setString(0, payload)
            self._activity = payload
            return True

        def setAppearance(self, payload):
            if payload == self._appearance:
                return False
            with self.transaction():
                self._setString(1, payload)
            self._appearance = payload
            return True

        def _dispatch(self, *args):
            try:
                arg = args[0] if args else None
                getter = getattr(arg, 'get', None)
                if callable(getter) and getter('action') == 'open':
                    on_open()
            except Exception:
                LOG.exception('Garage statistics button command failed.')

    class FooterHostModel(ViewModel):
        def __init__(self):
            super(FooterHostModel, self).__init__(properties=2, commands=0)

        def _initialize(self):
            super(FooterHostModel, self)._initialize()
            gf_mod_inject(self, str(INJECT_NAME), styles=[str(STYLE_URL)], modules=[str(MODULE_URL)])
            self._commands_model = FooterCommands()
            self._addViewModelProperty(str(DATA_PROPERTY), self._commands_model)

        def setActivity(self, payload):
            return self._commands_model.setActivity(payload)

        def setAppearance(self, payload):
            return self._commands_model.setAppearance(payload)

    class FooterChild(ViewComponent):
        def __init__(self):
            super(FooterChild, self).__init__(model=FooterHostModel)

        def set_activity(self, payload):
            return self.getViewModel().setActivity(payload)

        def set_appearance(self, payload):
            return self.getViewModel().setAppearance(payload)

    return FooterChild


class FooterInstallation(object):
    def __init__(self, footer_class, child_class, on_open):
        # Check only the methods this optional integration actually uses.
        # An incompatible footer must remain untouched so the native garage
        # and the independent statistics hotkey keep their own lifecycles.
        for name in ('_onLoading', 'getChildView', '_registerChild', '_unregisterChild'):
            if not callable(getattr(footer_class, name, None)):
                raise TypeError('Native footer child contract unavailable: ' + name)
        self.footer_class = footer_class
        self.child_class = child_class
        self._on_open = on_open
        self._enabled = True
        self._children = []
        self._activity = IDLE_ACTIVITY
        self._labels = None
        self._activity_state = (0, False)
        self._activity_warning = False
        self._appearance = ''
        self._appearance_warning = False
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
                    # Even rollback/ownership adapters are optional. Never
                    # interrupt native loading or a later mod in the chain.
                    LOG.exception('Statistics footer attachment failed; native loading continues.')
            return result

        self._wrapper = on_loading
        footer_class._onLoading = on_loading

    def open(self):
        if self._enabled and self._on_open is not None:
            return self._on_open()
        return False

    def _warn_activity(self):
        if not self._activity_warning:
            self._activity_warning = True
            LOG.warning('Statistics footer activity unavailable; button remains usable.',
                        exc_info=True)

    def _push_activity(self, child):
        try:
            child.set_activity(self._activity)
            return True
        except Exception:
            self._warn_activity()
            return False

    def set_activity(self, pending_count, processing):
        if not self._enabled:
            return False
        self._activity_state = (pending_count, processing)
        payload = _activity_json(pending_count, processing, self._labels)
        changed = payload != self._activity
        self._activity = payload
        retained = []
        for view_ref, child_ref in self._children:
            view, child = view_ref(), child_ref()
            if view is None or child is None:
                continue
            try:
                if view.getChildView(POSITION_ID) is not child:
                    continue
                retained.append((view_ref, child_ref))
                # Model-level deduplication avoids redundant native updates,
                # while this retry can recover an earlier transient failure.
                self._push_activity(child)
            except Exception:
                retained.append((view_ref, child_ref))
                self._warn_activity()
        self._children = retained
        return changed

    def set_language(self, labels):
        if not self._enabled:
            return False
        from .localization import valid_text
        keys = ('footer.idle', 'footer.processing', 'footer.waiting', 'status.pending', 'metric.wn8')
        checked = dict((key, labels[key]) for key in keys
                       if key in labels and valid_text(key, labels[key]))
        if checked == self._labels:
            return False
        self._labels = checked
        self.set_activity(*self._activity_state)
        return True

    def _warn_appearance(self, exception=False):
        if not self._appearance_warning:
            self._appearance_warning = True
            LOG.warning('Statistics footer appearance unavailable; using stylesheet defaults.',
                        exc_info=exception)

    def _push_appearance(self, child):
        try:
            setter = getattr(child, 'set_appearance', None)
            if not callable(setter):
                if self._appearance:
                    self._warn_appearance()
                return False
            setter(self._appearance)
            return True
        except Exception:
            self._warn_appearance(exception=True)
            return False

    def set_appearance(self, css):
        if not self._enabled:
            return False
        # Configuration validation/compilation belongs to appearance.py. This
        # native boundary accepts only bounded CSS text and supports clearing.
        if (not isinstance(css, text_types) or len(css) > MAX_APPEARANCE_CHARS or
                '\x00' in css or '<' in css):
            css = ''
            self._warn_appearance()
        changed = css != self._appearance
        self._appearance = css
        retained = []
        for view_ref, child_ref in self._children:
            view, child = view_ref(), child_ref()
            if view is None or child is None:
                continue
            try:
                if view.getChildView(POSITION_ID) is not child:
                    continue
                retained.append((view_ref, child_ref))
                # Retry unchanged state after a transient native write failure.
                self._push_appearance(child)
            except Exception:
                retained.append((view_ref, child_ref))
                self._warn_appearance(exception=True)
        self._children = retained
        return changed

    def _attach(self, view):
        child = None
        try:
            # Position IDs are scoped to this parent. Do not displace another
            # component if another mod happens to have chosen the same value.
            if view.getChildView(POSITION_ID) is not None:
                LOG.warning('Statistics footer position is occupied; shortcut remains active.')
                return
            child = self.child_class()
            if not self._enabled:
                return
            view._registerChild(POSITION_ID, child)
            if self._enabled and view.getChildView(POSITION_ID) is child:
                self._children.append((weakref.ref(view), weakref.ref(child)))
                self._push_activity(child)
                self._push_appearance(child)
                return
            LOG.warning('Native footer did not attach statistics child; shortcut remains active.')
        except Exception:
            LOG.exception('Could not attach statistics footer child; shortcut remains active.')
        if child is not None and not self._remove_child(view, child):
            # Registration may attach before throwing. Keep failed rollback
            # owned so uninstall/reinstallation can retry the exact child.
            self._children.append((weakref.ref(view), weakref.ref(child)))

    def _remove_child(self, view, child):
        try:
            if view.getChildView(POSITION_ID) is not child:
                return True
            view._unregisterChild(child.uniqueID, True)
            return view.getChildView(POSITION_ID) is not child
        except Exception:
            LOG.warning('Statistics footer child cleanup incomplete; cleanup will be retried.')
            return False

    def uninstall(self):
        global _installed
        self._enabled = False
        self._on_open = None
        retained = []
        for view_ref, child_ref in self._children:
            view, child = view_ref(), child_ref()
            if view is not None and child is not None and not self._remove_child(view, child):
                retained.append((view_ref, child_ref))
        self._children = retained
        # Another mod may have wrapped our wrapper. Leave its method alone;
        # this wrapper is now inert and only calls the original implementation.
        if self.footer_class.__dict__.get('_onLoading') is self._wrapper:
            if self._defined_here:
                self.footer_class._onLoading = self._original
            else:
                del self.footer_class._onLoading
        if _installed is self and not retained:
            _installed = None
        return not retained


def install(on_open):
    global _installed
    if _installed is not None:
        if _installed._enabled:
            return _installed
        try:
            _installed.uninstall()
        except Exception:
            LOG.warning('Previous statistics footer cleanup is still incomplete.')
        if _installed is not None:
            return None
    try:
        from openwg_gameface import gf_mod_inject
        from gui.impl.lobby.page.lobby_footer import LobbyFooter
    except ImportError:
        LOG.warning('OpenWG or native LobbyFooter unavailable; shortcut remains active.')
        return None
    # Bind through the installation so that a retained client command becomes
    # harmless after uninstall, even if a later mod keeps our wrapper alive.
    holder = {}

    def open_current():
        current = holder.get('installation')
        return current.open() if current is not None else False

    try:
        child_class = build_child_class(gf_mod_inject, open_current)
        handle = FooterInstallation(LobbyFooter, child_class, on_open)
        holder['installation'] = handle
        _installed = handle
        return handle
    except Exception:
        LOG.exception('Statistics footer integration unavailable; shortcut remains active.')
        return None
