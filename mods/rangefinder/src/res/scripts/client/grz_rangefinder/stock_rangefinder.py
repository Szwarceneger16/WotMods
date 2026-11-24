# -*- coding: ascii -*-
"""Temporarily hide the live Scaleform CrosshairBase distance subclips."""
from __future__ import absolute_import


def _stock_crosshair(app):
    from frameworks.wulf import WindowLayer
    from gui.Scaleform.daapi.view.battle.shared.crosshair.container import CrosshairPanelContainer

    battle_view = app.containerManager.getContainer(WindowLayer.VIEW).getView()
    for component in battle_view._external:
        if isinstance(component, CrosshairPanelContainer) and component._isDAAPIInited():
            return component
    return None


def _fields(owner):
    root = owner.flashObject
    count = int(root.numChildren)
    if not 0 < count <= 64:
        return ()
    fields = []
    # Stock initCrosshairs attaches the native mode views directly under this
    # panel. Distance updates use the distance clip's timeline, not its
    # DisplayObject visibility, in all supported camera modes.
    for index in range(count):
        try:
            field = root.getChildAt(index).distance
            if field is not None and field.visible in (False, True):
                fields.append(field)
        except (AttributeError, TypeError, RuntimeError):
            continue
    return fields


class StockRangefinder(object):
    def __init__(self):
        self._owner = None
        self._changed = []

    def suppress(self, app):
        if app is None:
            self.restore()
            return False
        try:
            owner = _stock_crosshair(app)
            if owner is not None and owner is self._owner:
                return True
            self.restore()
            if owner is None:
                return False
            fields = _fields(owner)
            if not fields:
                return False
            for field in fields:
                if field.visible:
                    self._changed.append(field)
                    field.visible = False
            self._owner = owner
            return True
        except Exception:
            self.restore()
            return False

    def restore(self):
        changed, self._changed = self._changed, []
        self._owner = None
        for field in changed:
            try:
                if field.visible in (False, 0):
                    field.visible = True
            except Exception:
                # Disposed Flash values cannot change the replacement panel.
                pass
