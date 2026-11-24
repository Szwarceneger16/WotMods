# -*- coding: ascii -*-
"""Bounded local diagnostics for the isolated settings preview."""
from __future__ import absolute_import, unicode_literals

import datetime
import json
import logging
import os

from . import VERSION
from .native_preview import DECORATION_AS_ERROR_IDS, DECORATION_MISSING_QNAMES, DECOR_LINKAGE_NAMES
from .preview_catalog import PANELS, choices
from .views import DECORATION_DIAGNOSTICS

try:
    _TEXT = (basestring,)
    _INTEGER = (int, long)
except NameError:
    _TEXT = (str,)
    _INTEGER = (int,)

FILENAME = 'preview-diagnostics.jsonl'
MAX_BYTES = 512 * 1024
BACKUPS = 2
_EVENTS = frozenset((
    'diagnostics-open', 'diagnostics-close',
    'editor-request', 'editor-result', 'editor-open', 'editor-close', 'preview-status',
    'native_selection', 'native_core_stage', 'native_core_failure', 'native_visual_probe',
    'native_decor_stage', 'native_decor_poll', 'native_decor_failure', 'native_status',
    'native_close', 'native_layer', 'native_battle_panel',
))
_ENUMS = {
    'mode': frozenset(('arcade', 'sniper', 'arty')),
    'scene': frozenset(('arcade', 'sniper', 'arty_top', 'arty_trajectory')),
    'action': frozenset(('open', 'update', 'close')),
    'result': frozenset(('accepted', 'rejected', 'superseded')),
    'status': frozenset(('loading', 'ready', 'partial', 'unavailable')),
    'reason': frozenset((
        'invalid', 'unsupported', 'missing', 'native', 'hidden', 'timeout',
        'cassette-unverified', 'marker-unverified', 'decoration-missing',
        'decoration-failed', 'decoration-timeout', 'decoration-unverified',
        'decoration-mounted', 'battle-panels-mounted', 'battle-panel-unavailable',
        'battle-panel-sample-incomplete', 'artillery-indicators-unavailable',
    )),
    'stage': frozenset((
        'selection', 'stock-settings', 'crosshair-resource', 'crosshair-construction',
        'crosshair-component', 'crosshair-configuration', 'crosshair-activation',
        'await-daapi', 'geometry-update', 'daapi-callback', 'daapi-capabilities',
        'cassette-snapshot', 'visual-probe', 'refresh-surge-sample', 'apply-stock-settings',
        'create-marker', 'create-secondary-marker', 'apply-marker-geometry', 'initial-stock-sample',
        'artillery-indicators',
        'prepare-host', 'resource-query', 'host-construction', 'host-component',
        'host-configuration', 'host-activation', 'host-geometry', 'bridge-request',
        'host-structure-ready', 'await-root', 'await-symbol', 'rocket-glyph', 'marker-root',
        'marker-currmixingmc', 'marker-chargegunmixing', 'marker-twingunmixing',
        'marker-lowchargeshotmixingmc', 'marker-chargeableburst', 'marker-accuracygunmixing',
        'cassette-autoloadercomponent', 'cassette-extrashotclippanel',
        'cassette-controllablereloadcassette', 'cassette-reloadswitchicon',
        'cassette-shellcalibrationclippanel', 'cassette-cassettemc',
        'autoloader-loaded-shells', 'autoloader-surge-shell',
    )),
    'diagnostic': DECORATION_DIAGNOSTICS,
    'missing_qname': DECORATION_MISSING_QNAMES,
    'linkage': DECOR_LINKAGE_NAMES,
    'stock_library': frozenset(('autoreloader-surge', 'decorative-crosshair')),
    'panel': frozenset(PANELS),
    'panel_linkage': frozenset(recipe['linkage'] for recipe in PANELS.values()),
    'panel_library': frozenset(recipe['stock_library'] for recipe in PANELS.values()),
    'panel_stage': frozenset((
        'requested', 'mounted', 'panel-resource', 'panel-component', 'panel-bridge',
        'panel-rejected', 'panel-timeout', 'panel-sample-incomplete',
    )),
    'layer': frozenset(('crosshair', 'gun-marker', 'cassette', 'decoration-host', 'stock-decoration')),
    'layer_state': frozenset((
        'waiting', 'initialized', 'attached', 'sample-applied', 'check-passed', 'unverified',
        'not-requested', 'responsive', 'requested', 'mounted-unverified', 'unavailable',
    )),
    'decoration': frozenset((
        'autoreloaderSurge', 'accuracy', 'fury', 'concentration', 'overheat',
        'pillboxSiege', 'temperatureGunOverheat',
    )),
    'marker_family': frozenset((
        'standard', 'dualgun', 'twingun', 'dual_accuracy', 'accuracy_stacks',
        'charge_shot', 'low_charge_shot', 'auxiliary_rocket_launcher',
    )),
}
_NUMBERS = {
    'request_id': (1, 2147483647), 'generation': (0, 2147483647),
    'elapsed_ms': (0, 3600000), 'step': (0, 4), 'focus': (0, 2),
    'crosshair_polls': (0, 240), 'visual_polls': (0, 240), 'decoration_polls': (0, 240),
    'panel_polls': (0, 240),
    'marker_count': (0, 4), 'clip_capacity': (0, 250), 'reload_type': (0, 5),
    'rounds_loaded': (0, 250), 'available_charges': (0, 3), 'accuracy_stacks': (0, 4),
}
_BOOLEANS = ('cassette_verified', 'reticle_visible', 'marker_verified')


def _allowed_text(value, options):
    return isinstance(value, _TEXT) and value in options


def _safe_fields(fields, profiles):
    if not isinstance(fields, dict):
        return {}
    safe = {}
    for key, options in _ENUMS.items():
        value = fields.get(key)
        if _allowed_text(value, options):
            safe[key] = value
    for key in ('variant', 'profile'):
        value = fields.get(key)
        if _allowed_text(value, profiles):
            safe[key] = value
    for key, bounds in _NUMBERS.items():
        value = fields.get(key)
        if type(value) in _INTEGER and bounds[0] <= value <= bounds[1]:
            safe[key] = value
    for key in _BOOLEANS:
        value = fields.get(key)
        if type(value) is bool:
            safe[key] = value
    error_id = fields.get('as_error_id')
    if type(error_id) in _INTEGER and error_id in DECORATION_AS_ERROR_IDS:
        safe['as_error_id'] = error_id
    return safe


class PreviewDiagnostics(object):
    """Append one JSON record per transition in an owned rotating log."""

    def __init__(self, directory):
        self._handler = None
        self._sequence = 0
        self._session = datetime.datetime.utcnow().isoformat() + 'Z'
        self._profiles = frozenset(choice['id'] for choice in choices())
        try:
            from logging.handlers import RotatingFileHandler

            class QuietHandler(RotatingFileHandler):
                def handleError(self, record):
                    pass

            if os.path.islink(directory):
                return
            if not os.path.isdir(directory):
                os.makedirs(directory)
            path = os.path.join(directory, FILENAME)
            files = [path] + [path + '.%d' % number for number in range(1, BACKUPS + 1)]
            if any(os.path.islink(name) or (os.path.exists(name) and not os.path.isfile(name))
                   for name in files):
                return
            self._handler = QuietHandler(path, maxBytes=MAX_BYTES, backupCount=BACKUPS,
                                         encoding='utf-8', delay=True)
            self._handler.setFormatter(logging.Formatter('%(message)s'))
            self('diagnostics-open', {})
        except Exception:
            self._handler = None

    def __call__(self, event, fields):
        handler = self._handler
        if handler is None or not _allowed_text(event, _EVENTS):
            return
        try:
            self._sequence += 1
            record = {'schema': 1, 'version': VERSION, 'session': self._session,
                      'time': datetime.datetime.utcnow().isoformat() + 'Z',
                      'seq': self._sequence, 'event': event}
            record.update(_safe_fields(fields, self._profiles))
            message = json.dumps(record, ensure_ascii=True, sort_keys=True, separators=(',', ':'))
            handler.handle(logging.LogRecord(__name__, logging.INFO, '', 0, message, (), None))
        except Exception:
            # Logs may be unwritable without affecting settings or preview.
            pass

    def close(self):
        handler = self._handler
        if handler is not None:
            self('diagnostics-close', {})
            self._handler = None
            try:
                handler.close()
            except Exception:
                pass
