# -*- coding: ascii -*-
"""Manage the original mechanics widgets for one editor selection."""
from __future__ import absolute_import

_SLOT_OFFSETS = {'center': (0, 0), 'info': (47, 47)}
_SIDE_OFFSETS = {'arcade': (150, 100), 'sniper': (190, 190)}
_MODE = {'arcade': 1, 'sniper': 2, 'arty': 3}


class _Widget(object):
    def __init__(self, key, recipe):
        self.key = key
        self.recipe = recipe
        self.host = None
        self.requested_viewport = None
        self.polls = 0
        self.state = 'loading'


class BattlePanelPreview(object):
    def __init__(self, recipes, mode, appearance, viewport, open_host, release_host,
                 trace, error_details, max_polls):
        self._mode = _MODE[mode]
        self._side_offset = _SIDE_OFFSETS.get(mode, _SIDE_OFFSETS['arcade'])
        self._appearance = appearance
        self._viewport = viewport
        self._release_host = release_host
        self._trace = trace
        self._error_details = error_details
        self._max_polls = max_polls
        self._widgets = []
        for key, recipe in recipes:
            widget = _Widget(key, recipe)
            self._widgets.append(widget)
            if recipe['sample_status'] == 'pending':
                widget.state = 'incomplete'
                self._report(widget, 'panel-sample-incomplete')
                continue
            resource = recipe['stock_library'].encode('ascii')
            self._report(widget, 'requested')
            try:
                widget.host = open_host(resource)
            except Exception:
                self._fail(widget, 'panel-component')
                continue
            if widget.host is None:
                self._fail(widget, 'panel-resource')

    @property
    def pending(self):
        return any(widget.state == 'loading' for widget in self._widgets)

    @property
    def failed(self):
        return any(widget.state == 'unavailable' for widget in self._widgets)

    @property
    def incomplete(self):
        return any(widget.recipe['sample_status'] != 'complete' for widget in self._widgets)

    def resize(self, viewport):
        if self._viewport == viewport:
            return
        self._viewport = viewport
        for widget in self._widgets:
            if widget.state == 'ready':
                widget.polls = 0
                widget.state = 'loading'

    def poll(self):
        for widget in self._widgets:
            if widget.state == 'loading':
                self._poll(widget)

    def _poll(self, widget):
        try:
            root = widget.host.getMember(b'root')
            if root is not None:
                if widget.requested_viewport != self._viewport:
                    self._request(widget, root)
                state = root.as_getState()
                if state == 1:
                    widget.state = 'ready'
                    self._report(widget, 'mounted' if widget.recipe['sample_status'] == 'complete'
                                 else 'panel-sample-incomplete')
                    return
                if state == -1:
                    diagnostic, error_id, missing_qname = self._error_details(root)
                    self._fail(widget, 'panel-rejected', diagnostic, error_id, missing_qname)
                    return
        except Exception:
            self._fail(widget, 'panel-bridge')
            return
        widget.polls += 1
        if widget.polls >= self._max_polls:
            self._fail(widget, 'panel-timeout')

    def _request(self, widget, root):
        width, height, scale = self._viewport
        slot = widget.recipe['layout']
        if slot in _SLOT_OFFSETS:
            x, y = _SLOT_OFFSETS[slot]
        else:
            x, y = self._side_offset
            if slot == 'left':
                x = -x
        dx, dy = widget.recipe.get('offset', (0, 0))
        x, y = x + dx, y + dy
        widget.host.component.size = (width, height)
        root.as_setPreview(widget.recipe['linkage'].encode('ascii'), width * 0.5 + x * scale,
                           height * 0.5 + y * scale, scale * widget.recipe['scale'],
                           self._mode, self._appearance)
        widget.requested_viewport = self._viewport
        widget.polls = 0

    def _fail(self, widget, code, diagnostic=None, error_id=None, missing_qname=None):
        widget.state = 'unavailable'
        self._report(widget, code, diagnostic, error_id, missing_qname)
        self._remove(widget)

    def _report(self, widget, stage, diagnostic=None, error_id=None, missing_qname=None):
        self._trace('native_battle_panel', panel=widget.key, panel_stage=stage, panel_polls=widget.polls,
                    panel_linkage=widget.recipe['linkage'], panel_library=widget.recipe['stock_library'],
                    diagnostic=diagnostic, as_error_id=error_id, missing_qname=missing_qname)

    def _remove(self, widget):
        host, widget.host = widget.host, None
        if host is not None:
            self._release_host(host)

    def close(self):
        for widget in self._widgets:
            self._remove(widget)
        self._widgets = []
