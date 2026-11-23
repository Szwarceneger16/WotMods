# -*- coding: ascii -*-
"""Keep the stock numeric cache while suppressing its live HUD text."""
from __future__ import absolute_import

_SET_DISTANCE = 'as_setDistanceS'
_INHERITED = object()


def _stock_crosshair(app):
    if app is None:
        return None
    from frameworks.wulf import WindowLayer
    from gui.Scaleform.daapi.view.battle.shared.crosshair.container import CrosshairPanelContainer

    view = app.containerManager.getContainer(WindowLayer.VIEW).getView()
    panel = getattr(view, 'crosshair', None)
    if isinstance(panel, CrosshairPanelContainer) and panel._isDAAPIInited():
        return panel
    return None


def _panel_signal():
    from PlayerEvents import g_playerEvents
    return g_playerEvents.crosshairPanelInitialized


def _view_proxy():
    import BigWorld
    player = BigWorld.player()
    provider = getattr(player, 'guiSessionProvider', None)
    return getattr(getattr(provider, 'shared', None), 'crosshair', None)


def _distance_label(distance):
    from gui.Scaleform.locale.INGAME_GUI import INGAME_GUI
    from helpers import i18n
    return i18n.makeString(INGAME_GUI.DISTANCE_METERS, meters=distance)


class StockRangefinder(object):
    def __init__(self):
        self.status = 'inactive'
        self._app_getter = None
        self._on_status_changed = None
        self._requested = False
        self._panel_signal = None
        self._proxy = None
        self._view_signals = []
        self._owner = None
        self._hook = None
        self._prior = _INHERITED

    def start(self, app_getter, on_status_changed=None):
        """Set up the callbacks. Watch the game only while suppression is requested."""
        self._app_getter = app_getter
        self._on_status_changed = on_status_changed

    def _set_status(self, status):
        if status == self.status:
            return
        self.status = status
        if self._on_status_changed is not None:
            try:
                self._on_status_changed()
            except Exception:
                pass

    def suppress(self, app):
        self._requested = True
        self._watch()
        return self._refresh(app, clear=False)

    def _watch(self):
        try:
            if self._panel_signal is None:
                signal = _panel_signal()
                signal += self._on_panel
                self._panel_signal = signal
            proxy = _view_proxy()
        except Exception:
            return
        if proxy is self._proxy:
            return
        self._unwatch_view()
        self._proxy = proxy
        for name in ('onCrosshairViewChanged', 'onStrategicCameraChanged'):
            signal = getattr(proxy, name, None)
            if signal is not None:
                try:
                    signal += self._on_view
                    self._view_signals.append(signal)
                except Exception:
                    pass

    def _unwatch_view(self):
        for signal in self._view_signals:
            try:
                signal -= self._on_view
            except Exception:
                pass
        self._view_signals = []
        self._proxy = None

    def _on_panel(self, *unused):
        if self._requested:
            # Rebind after the replacement panel's plugins subscribed, so the
            # view-change clear runs after the stock view received its cache.
            self._unwatch_view()
            self._watch()
            self._on_view()

    def _on_view(self, *unused):
        if self._requested and self._app_getter is not None:
            try:
                app = self._app_getter()
            except Exception:
                app = None
            self._refresh(app, clear=True)

    def _refresh(self, app, clear):
        try:
            owner = _stock_crosshair(app)
            if owner is None:
                self._unbind()
                self._set_status('panel_not_ready')
                return False
            if owner is not self._owner:
                self._unbind()
                self._bind(owner)
                clear = True
            elif vars(owner).get(_SET_DISTANCE, _INHERITED) is not self._hook:
                self._unbind()
                self._set_status('binding_conflict')
                return False
            if clear:
                owner.as_clearDistanceS(True)
            self._set_status('hidden')
            return True
        except Exception:
            self._unbind()
            self._set_status('binding_failed')
            return False

    def _bind(self, owner):
        previous = owner.as_setDistanceS
        prior = vars(owner).get(_SET_DISTANCE, _INHERITED)

        # Stock setDistance still updates the distance field used by getDistance.
        # Keep only the presentation call on this one panel from reaching Flash.
        def hide(*args, **kwargs):
            if self._hook is not hide:
                return previous(*args, **kwargs)
            return None

        setattr(owner, _SET_DISTANCE, hide)
        self._owner, self._hook, self._prior = owner, hide, prior

    def _unbind(self):
        owner, hook, prior = self._owner, self._hook, self._prior
        self._owner, self._hook, self._prior = None, None, _INHERITED
        if owner is None:
            return True
        try:
            # A later instance patch may have wrapped ours. Leave that patch in
            # place. The inactive wrapper now delegates to its original call.
            if vars(owner).get(_SET_DISTANCE, _INHERITED) is hook:
                if prior is _INHERITED:
                    delattr(owner, _SET_DISTANCE)
                else:
                    setattr(owner, _SET_DISTANCE, prior)
            if owner._isDAAPIInited():
                distance = owner.getDistance()
                if distance > 0:
                    owner.as_setDistanceS(_distance_label(distance))
            return True
        except Exception:
            return False

    def restore(self):
        if not self._requested:
            return
        self._requested = False
        signal, self._panel_signal = self._panel_signal, None
        if signal is not None:
            try:
                signal -= self._on_panel
            except Exception:
                pass
        self._unwatch_view()
        self._set_status('inactive' if self._unbind() else 'restore_failed')
