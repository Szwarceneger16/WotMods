# -*- coding: utf-8 -*-
"""An editor-only, isolated instance of the client's original crosshair movie.

The client owns all artwork and reads it through its resource manager.  This
module never attaches a gun controller/provider or alters the live crosshair.
Only the short, bounded initialization wait uses a Python callback.
"""
from __future__ import absolute_import, division, unicode_literals

import math
import re
import time

from .scene_catalog import DEFAULT_FOCUS, FOCUS_FACTORS, resolve as resolve_scene, resolve_focus

SWF = b'battleCrosshairsApp.swf'
RESOURCE = b'gui/flash/battleCrosshairsApp.swf'
ALIAS = b'grzAimTimerOriginalPreview'
ROOT = b'root.main'
MARKER_NAME = b'grzAimTimerPreviewMarker'
DECOR_SWF = b'grzAimTimerReticleDecorPreview_v0_1_7.swf'
DECOR_RESOURCE = b'gui/flash/' + DECOR_SWF
PANEL_SWF = b'grzAimTimerBattleMechanicsPreview_v0_1_7.swf'
PANEL_RESOURCE = b'gui/flash/' + PANEL_SWF
DECOR_LINKAGES = {
    'autoreloaderSurge': b'AutoreloaderSurgeWidgetUI',
    'accuracy': b'AccuracyCrosshairUI',
    'fury': b'FuryCrosshairUI',
    'concentration': b'ConcentrationCrosshairUI',
    'overheat': b'OverheatCrosshairUI',
    'pillboxSiege': b'PillboxSiegeDecorativeCrosshairUI',
    'temperatureGunOverheat': b'TemperatureGunOverheatDecorativeCrosshairUI',
}
DECOR_LINKAGE_NAMES = frozenset(name.decode('ascii') for name in DECOR_LINKAGES.values())
PREVIEW_DEPTH = 0.04
WAIT_DELAY = 0.05
MAX_WAIT_SAMPLES = 240
MAX_DIMENSION = 32768
FOCUS_DURATION = 2.0
FOCUS_FRAME_DELAY = 1.0 / 30
SURGE_READY_CHARGES = 3
SURGE_TOP_SHELL_RELOAD = 10.0
ACCURACY_MAX_STACKS = 4
GUN_MARKER_VISIBLE = 3  # Stock DUAL_GUN_MARKER_STATE.VISIBLE.

# The ActionScript host may include a resource URL or exception text in its
# error. Classify known strings here and expose only these finite values.
DECORATION_ERRORS = (
    (('cannot load ', 'ioerror', 'securityerror'), 'library-load'),
    (('original client symbol is missing',), 'symbol-missing'),
    (('original symbol is not a movieclip', 'verifyerror', 'referenceerror'), 'symbol-incompatible'),
    (('original child is missing', 'original child is not a movieclip'), 'timeline-member'),
    (('original frame label is missing', 'original frame is missing'), 'timeline-frame'),
    (('original surge sector is empty', 'original component is empty'), 'empty-drawing'),
    (('original component draws no visible pixels',), 'pixel-probe'),
    (('unsupported original decorative linkage',), 'host-linkage-unsupported'),
    (('invalid decorative preview geometry',), 'host-geometry-invalid'),
    (('original client symbol failed',), 'stock-symbol-error'),
)
DECORATION_AS_ERROR_IDS = frozenset((1006, 1009, 1010, 1014, 1034, 1056, 1065, 1069,
                                   1074, 1120, 2007, 2008, 2015, 2025, 2032, 2035,
                                   2044, 2123))
_AS_ERROR = re.compile(r'\berror\s+#([0-9]{4})\b')
# Public stock classes from the verified decoration host ancestry. A runtime
# message may name a binding, but it can never extend this local allowlist.
_DECOR_PACKAGE = 'net.wg.gui.battle.views.decorativeCrosshair'
_META_PACKAGE = 'net.wg.infrastructure.base.meta.impl'
_DECOR_ADAPTERS = (
    'AccuracyStackDecorativeCrosshair', 'ConcentrationDecorativeCrosshair',
    'FuryDecorativeCrosshair', 'OverheatDecorativeCrosshair',
    'PillboxSiegeDecorativeCrosshair', 'TemperatureGunOverheatDecorativeCrosshair',
)
DECORATION_MISSING_QNAMES = frozenset(
    package + '::' + name
    for package, names in (
        ('net.wg.gui.battle.components', ('BattleUIComponent', 'BattleDisplayable')),
        ('net.wg.infrastructure.base', ('BaseBattleDAAPIComponent',)),
        (_META_PACKAGE, ('BaseBattleDAAPIComponentMeta', 'BaseDecorativeCrosshairMeta',
                         'DecorativeCrosshairPanelMeta', 'BaseVehicleMechanicsWidgetMeta',
                         'AutoreloaderSurgeWidgetMeta') + tuple(name + 'Meta' for name in _DECOR_ADAPTERS)),
        (_DECOR_PACKAGE, ('BaseDecorativeCrosshair', 'DecorativeCrosshairPanel') + _DECOR_ADAPTERS),
        (_DECOR_PACKAGE + '.shared', ('TextWrapper',)),
        ('net.wg.gui.battle.views.widgetsPanel', ('BaseVehicleMechanicsWidget', 'AutoreloaderSurgeWidget')),
    )
    for name in names
)
_MISSING_QNAME = re.compile(
    r'\b(?:Variable|Class) ([A-Za-z_][A-Za-z0-9_.]*(?:::|\.)[A-Za-z_][A-Za-z0-9_]*) '
    r'(?:is not defined|could not be found)\b')


def _missing_stock_qname(message, error_id):
    if error_id not in (1014, 1065, 1120):
        return None
    match = _MISSING_QNAME.search(message)
    if match is None:
        return None
    name = match.group(1)
    if '::' not in name:
        name = '::'.join(name.rsplit('.', 1))
    return name if name in DECORATION_MISSING_QNAMES else None


def _decoration_error_details(root):
    """Extract bounded codes and a recognized missing stock class, when named."""
    try:
        error = root.as_getError()
    except Exception:
        return 'bridge-error-detail', None, None
    if error is None:
        return 'host-error-empty', None, None
    if not isinstance(error, (str, type(u''))):
        return 'host-error-type', None, None
    if len(error) > 512:
        return 'host-error-too-long', None, None
    if isinstance(error, bytes):
        error = error.decode('ascii', 'replace')
    message = error.strip().lower()
    if not message:
        return 'host-error-empty', None, None
    error_id = None
    match = _AS_ERROR.search(message)
    if match:
        candidate = int(match.group(1))
        if candidate in DECORATION_AS_ERROR_IDS:
            error_id = candidate
    missing_qname = _missing_stock_qname(error, error_id)
    if missing_qname is not None:
        return 'stock-binding-missing', error_id, missing_qname
    for prefixes, code in DECORATION_ERRORS:
        if any(prefix in message for prefix in prefixes):
            return code, error_id, missing_qname
    if error_id in (2032, 2035, 2123):
        return 'library-load', error_id, None
    if error_id is not None:
        return 'flash-error', error_id, missing_qname
    return 'host-rejected', None, None


def _number(value, maximum):
    if isinstance(value, bool):
        return None
    try:
        value = float(value)
        if 0 < value <= maximum and not math.isnan(value) and not math.isinf(value):
            return value
    except (TypeError, ValueError, OverflowError):
        pass
    return None


def _viewport(value):
    if not isinstance(value, dict):
        return None
    width = _number(value.get('width'), MAX_DIMENSION)
    height = _number(value.get('height'), MAX_DIMENSION)
    scale = _number(value.get('scale', 1.0), 16)
    if width is None or height is None or scale is None:
        return None
    return (int(math.ceil(width)), int(math.ceil(height)), scale)


def _make_settings_vo(get_setting):
    """The stock _makeSettingsVO mapping, without importing battle plugins."""
    from account_helpers.settings_core.settings_constants import AIM, GRAPHICS, SPGAim
    fields = ((b'centerAlphaValue', b'centralTag'),
              (b'netAlphaValue', b'net'),
              (b'reloaderAlphaValue', b'reloader'),
              (b'conditionAlphaValue', b'condition'),
              (b'cassetteAlphaValue', b'cassette'),
              (b'reloaderTimerAlphaValue', b'reloaderTimer'),
              (b'zoomIndicatorAlphaValue', b'zoomIndicator'),
              (b'gunTagAlpha', b'gunTag'), (b'mixingAlpha', b'mixing'))
    types = ((b'centerType', b'centralTagType'), (b'netType', b'netType'),
             (b'gunTagType', b'gunTagType'), (b'mixingType', b'mixingType'))
    result = {}
    for view_id, key in ((1, AIM.ARCADE), (2, AIM.SNIPER)):
        raw, settings = get_setting(key), {}
        if raw is not None:
            for output, source in fields:
                settings[output] = raw[source] / 100.0
            for output, source in types:
                settings[output] = raw[source]
        settings[b'spgScaleWidgetEnabled'] = get_setting(SPGAim.SPG_SCALE_WIDGET)
        settings[b'isColorBlind'] = get_setting(GRAPHICS.COLOR_BLIND)
        result[view_id] = settings
    return result


def _player_settings():
    from account_helpers.settings_core.settings_constants import SPGAim
    from helpers import dependency
    from skeletons.account_helpers.settings_core import ISettingsCore
    get_setting = dependency.instance(ISettingsCore).getSetting
    return _make_settings_vo(get_setting), bool(get_setting(SPGAim.SHOTS_RESULT_INDICATOR))


def _build_flash_class():
    from gui.Scaleform.daapi.view.external_components import ExternalFlashComponent
    from gui.Scaleform.daapi.view.external_components import ExternalFlashSettings
    from gui.Scaleform.daapi.view.meta.CrosshairPanelContainerMeta import CrosshairPanelContainerMeta
    from gui.Scaleform.genConsts.ROOT_SWF_CONSTANTS import ROOT_SWF_CONSTANTS

    class OriginalPreview(ExternalFlashComponent, CrosshairPanelContainerMeta):
        def __init__(self, on_ready):
            self._preview_ready = on_ready
            self.preview_markers = []
            super(OriginalPreview, self).__init__(ExternalFlashSettings(
                ALIAS, SWF, ROOT,
                ROOT_SWF_CONSTANTS.BATTLE_CROSSHAIRS_REGISTER_CALLBACK))

        def _populate(self):
            # Base DAAPI population only: no battle plugins or global layout.
            super(OriginalPreview, self)._populate()

        def afterCreate(self):
            super(OriginalPreview, self).afterCreate()
            if self._preview_ready is not None:
                self._preview_ready(self)

        def as_playSound(self, unused):
            pass

        def detach_preview(self):
            self._preview_ready = None

    return OriginalPreview


def _configure(flash):
    import GUI
    import SCALEFORM
    from gui.Scaleform.flash_wrapper import InputKeyMode
    component = flash.component
    component.wg_inputKeyMode = InputKeyMode.NO_HANDLE
    component.focus = False
    component.moveFocus = False
    component.heightMode = GUI.Simple.eSizeMode.PIXEL
    component.widthMode = GUI.Simple.eSizeMode.PIXEL
    component.position.z = PREVIEW_DEPTH
    flash.movie.backgroundAlpha = 0
    flash.movie.scaleMode = SCALEFORM.eMovieScaleMode.NO_SCALE


def _build_decoration_class():
    from gui.Scaleform.flash_wrapper import FlashComponentWrapper

    class OriginalDecoration(FlashComponentWrapper):
        def detach_preview(self):
            pass

        def close(self):
            try:
                root = self.getMember(b'root')
                if root is not None:
                    root.as_dispose()
            finally:
                super(OriginalDecoration, self).close()

    return OriginalDecoration


def _release(flash):
    """Release only this editor's objects, even after partial initialization."""
    try:
        flash.detach_preview()
    except Exception:
        pass
    try:
        if getattr(flash, '_isDAAPIInited', lambda: False)():
            for name in flash.preview_markers:
                try:
                    flash.as_destroyGunMarkerS(name)
                except Exception:
                    pass
    except Exception:
        pass
    finally:
        flash.preview_markers = []
    try:
        flash.close()
    except Exception:
        # A native destructor can fail during shutdown; still remove our root.
        try:
            flash.active(False)
        except Exception:
            pass


def _defer_release(flash):
    try:
        flash.detach_preview()
        flash.setVisible(False)
    except Exception:
        pass
    try:
        import BigWorld
        BigWorld.callback(0, lambda: _release(flash))
    except Exception:
        _release(flash)


def _required_methods(selected, mode):
    methods = ['as_setSettings', 'as_setView', 'as_setSize', 'as_setScale',
               'as_recreateDevice', 'as_createGunMarker', 'as_setClipParams',
               'as_setAmmoStock', 'as_setReloadingAsPercent', 'as_setHealth', 'as_setDistance']
    if mode == 'sniper':
        methods.append('as_setZoom')
    elif mode == 'arty':
        methods.append('as_updateScaleWidget')
    reload_type = selected.get('reload_type', 0)
    if reload_type in (1, 3, 5) or selected['id'] == 'chargeable_burst':
        methods.append('as_setNetSeparatorType')
    if reload_type in (1, 3):
        methods.append('as_setAutoloaderPercent')
    if reload_type == 1:
        methods.append('as_setAutoloaderReloadasPercent')
    if selected.get('decoration') == 'autoreloaderSurge':
        methods.append('as_setAutoreloaderSurgeState')
    if reload_type == 3:
        methods.append('as_setIsInControllableReload')
    names = {
        'dualgun': ('as_updateDualGunMarkerState',),
        'twingun': ('as_setTwinGunMarkerActive', 'as_setTwinGunMarkerState'),
        'dual_accuracy': ('as_setSecondaryGunMarkerActive', 'as_setDispersionCircleThickness'),
        'accuracy_stacks': ('as_setAccuracyStacksProgress',),
        'charge_shot': ('as_setChargeGunActive', 'as_setChargeGunState'),
        'low_charge_shot': ('as_setLowChargeInitialTime', 'as_setLowChargeTimeLeft',
                            'as_setReloadingCounterShown'),
        'auxiliary_rocket_launcher': ('as_setAuxiliaryRocketLauncherActive', 'as_setNetType',
                                      'as_setReloadingCounterShown'),
        'chargeable_burst': ('as_setChargeableBurstMode',),
        'heating_zones_gun': ('as_setDispersionCircleThickness',),
        'propellant_gun': ('as_setAlternateZoomPosition',),
        'stance_dance': ('as_setReloadBoost',),
        'battle_fury': ('as_setReloadBoost', 'as_setReloadBoostBorder'),
        'pillbox_siege': ('as_setNetType', 'as_setNetSeparatorVisible'),
        'overheat_stacks': ('as_setAlternateZoomPosition',),
        'shell_calibration': ('as_setShellCalibrationState',),
    }
    return methods + list(names.get(selected['id'], ()))


def _painted(component, depth=0, budget=None):
    """Inspect the owned display tree after validation, including child alpha.

    This is a bounded structural check, not a pixel-rendering guarantee. It
    rejects empty timeline frames and transparent/hidden subtrees; the owned
    decoration host additionally performs its original-art pixel probes.
    """
    if component is None or depth > 8:
        return False
    budget = [96] if budget is None else budget
    budget[0] -= 1
    if budget[0] < 0:
        return False
    if not bool(getattr(component, 'visible', False)):
        return False
    try:
        if float(getattr(component, 'alpha', 0)) <= 0:
            return False
        children = int(getattr(component, 'numChildren', 0))
        if children:
            return any(_painted(component.getChildAt(index), depth + 1, budget)
                       for index in range(min(children, 96)))
        return float(getattr(component, 'width', 0)) > 0 and float(getattr(component, 'height', 0)) > 0
    except (TypeError, ValueError, AttributeError, OverflowError):
        return False


class PreviewRenderer(object):
    """Original static artwork, allocated only while the position editor is open."""
    def __init__(self, on_status=None, on_availability=None, on_diagnostic=None):
        self.status = 'unavailable'
        self.reason = None
        self.decoration_diagnostic = None
        self._published_decoration_diagnostic = None
        self._on_status = on_status
        self._on_availability = on_availability
        self._on_diagnostic = on_diagnostic
        self._diagnostic_since = None
        self._core_diagnostic_stage = 'selection'
        self._layer_states = {}
        self._availability = dict((mode, {}) for mode in ('arcade', 'sniper', 'arty'))
        self._capabilities_probed = False
        self._settings = None
        self._show_arty_indicators = False
        self._flash = None
        self._hide_stock_distance = False
        self._decoration = None
        self._battle_panels = None
        self._battle_panel_start_failed = False
        self._spec = None
        self._callback = None
        self._samples = 0
        self._generation = 0
        self._applied = False
        self._prepared = False
        self._finalized = False
        self._decor_pending = False
        self._decor_error = None
        self._decor_structure_ready = False
        self._decor_samples = 0
        self._decor_requested = None
        self._visual_samples = 0
        self._sample_error = None
        self._artillery_nodes = ()
        self._direct_focus_markers = ()
        self._focus = DEFAULT_FOCUS
        self._focus_progress = float(DEFAULT_FOCUS)
        self._focus_callback = None
        self._focus_finished = None

    def get_availability(self):
        return dict((mode, dict(values)) for mode, values in self._availability.items())

    def _trace(self, event, **fields):
        if self._on_diagnostic is None:
            return
        try:
            fields['generation'] = self._generation
            if self._diagnostic_since is not None:
                elapsed = int((time.time() - self._diagnostic_since) * 1000)
                fields['elapsed_ms'] = max(0, min(120000, elapsed))
            if self._spec is not None:
                mode, variant, selected, unused_viewport, scene = self._spec
                fields.update(mode=mode, variant=variant, profile=selected['id'],
                              scene=scene['scene_id'], step=scene['step'])
                if selected.get('decoration'):
                    family = selected['decoration']
                    fields['decoration'] = family
                    linkage = DECOR_LINKAGES.get(family)
                    if linkage is not None:
                        fields['linkage'] = linkage.decode('ascii')
                    fields['stock_library'] = ('autoreloader-surge' if family == 'autoreloaderSurge'
                                               else 'decorative-crosshair')
            self._on_diagnostic(event, fields)
        except Exception:
            # This callback is optional; output must never affect the preview.
            pass

    def _core_step(self, stage, **fields):
        self._core_diagnostic_stage = stage
        self._trace('native_core_stage', stage=stage, **fields)

    def _layer(self, layer, state):
        if self._on_diagnostic is not None and self._layer_states.get(layer) != state:
            self._layer_states[layer] = state
            self._trace('native_layer', layer=layer, layer_state=state)

    def _available(self, mode, identifier, value):
        values = self._availability[mode]
        value = bool(value)
        if values.get(identifier) is value:
            return
        values[identifier] = value
        if self._on_availability is not None:
            try:
                self._on_availability(self.get_availability())
            except Exception:
                pass

    def _status(self, value, reason=None):
        changed = ((self.status, self.reason, self._published_decoration_diagnostic) !=
                   (value, reason, self.decoration_diagnostic))
        self.status, self.reason = value, reason
        self._published_decoration_diagnostic = self.decoration_diagnostic
        if changed:
            self._trace('native_status', status=value, reason=reason,
                        diagnostic=self.decoration_diagnostic, crosshair_polls=self._samples,
                        visual_polls=self._visual_samples, decoration_polls=self._decor_samples)
        if changed and self._on_status is not None:
            try:
                self._on_status(value)
            except Exception:
                pass

    def _cancel_wait(self):
        callback, self._callback = self._callback, None
        if callback is not None:
            try:
                import BigWorld
                BigWorld.cancelCallback(callback)
            except Exception:
                pass

    def _discard(self, keep_decoration=False):
        self._generation += 1
        self._layer_states.clear()
        self._cancel_wait()
        self._artillery_nodes = ()
        self._direct_focus_markers = ()
        self._stop_focus_demo()
        flash, self._flash = self._flash, None
        panels, self._battle_panels = self._battle_panels, None
        if panels is not None:
            panels.close()
        self._battle_panel_start_failed = False
        decoration = None
        if not keep_decoration:
            decoration, self._decoration = self._decoration, None
        self._decor_pending = False
        self._decor_error = None
        self._decor_structure_ready = False
        self.decoration_diagnostic = None
        self._decor_samples = 0
        self._decor_requested = None
        self._applied = False
        self._prepared = self._finalized = False
        self._visual_samples = 0
        self._sample_error = None
        if flash is not None:
            _defer_release(flash)
        if decoration is not None:
            _defer_release(decoration)

    def _fail(self, reason):
        self._layer('crosshair', 'unavailable')
        self._trace('native_core_failure', reason=reason, stage=self._core_diagnostic_stage,
                    crosshair_polls=self._samples, visual_polls=self._visual_samples)
        if self._spec is not None and reason != 'invalid':
            self._available(self._spec[0], self._spec[1], False)
        self._discard()
        self._status('unavailable', reason)

    def open(self, mode, variant, viewport_dict, scene_id=None, zoom_step=None,
             focus=DEFAULT_FOCUS, focus_changed=False, hide_stock_distance=False):
        return self.update(mode, variant, viewport_dict, scene_id, zoom_step,
                           focus, focus_changed, hide_stock_distance)

    def update(self, mode, variant, viewport_dict, scene_id=None, zoom_step=None,
               focus=DEFAULT_FOCUS, focus_changed=False, hide_stock_distance=False):
        try:
            self._core_diagnostic_stage = 'selection'
            from .preview_catalog import profile
            selected = profile(variant, mode)
            viewport = _viewport(viewport_dict)
            scene = resolve_scene(mode, scene_id, zoom_step)
            focus = resolve_focus(focus)
            if selected is None or viewport is None or scene is None or focus is None:
                self._fail('invalid')
                return False
            if self._availability[mode].get(variant) is False:
                self._spec = (mode, variant, selected, viewport, scene)
                self._fail('unsupported')
                return False
            spec = (mode, variant, selected, viewport, scene)
            replace = self._flash is None or self._spec is None or self._spec[:2] != spec[:2]
            distance_changed = hide_stock_distance != self._hide_stock_distance
            self._hide_stock_distance = hide_stock_distance
            if distance_changed and not replace and (self._prepared or self._applied):
                _sample_distance(self._flash, hide_stock_distance)
            if focus_changed or focus != self._focus:
                self._focus = focus
                self._stop_focus_demo()
            if not replace and self._spec == spec:
                return self.status != 'unavailable'
            self._spec = spec
            if replace:
                self._discard(keep_decoration=True)
            self._diagnostic_since = time.time() if self._on_diagnostic is not None else None
            self._trace('native_selection', focus=focus)
            if replace:
                self._layer('crosshair', 'waiting')
                self._samples = 0
                if self._settings is None:
                    # One read-only appearance snapshot per editor session.
                    # Both camera styles remain independent and no defaults
                    # replace elements deliberately hidden by the player.
                    self._core_step('stock-settings')
                    self._settings, self._show_arty_indicators = _player_settings()
                self._core_step('crosshair-resource')
                import ResMgr
                if not ResMgr.isFile(RESOURCE):
                    self._fail('missing')
                    return False
                self._start_decoration()
                self._start_battle_panels()
                self._core_step('crosshair-construction')
                flash = _build_flash_class()(self._on_ready)
                self._flash = flash
                self._core_step('crosshair-component')
                flash.createExternalComponent()
                self._core_step('crosshair-configuration')
                _configure(flash)
                # active() resets the surface to (2,2); apply size afterwards.
                self._core_step('crosshair-activation')
                flash.active(True)
                flash.component.size = viewport[:2]
                self._core_step('await-daapi')
                self._queue_wait()
                self._status('loading')
            elif self._prepared or self._applied:
                self._core_step('geometry-update')
                self._scene_zoom()
                self._geometry()
            return self.status != 'unavailable'
        except Exception:
            self._fail('native')
            return False

    def _on_ready(self, flash):
        if flash is self._flash:
            self._trace('native_core_stage', stage='daapi-callback')
            try:
                self._queue_wait()
            except Exception:
                self._fail('native')

    def _native_overlays_pending(self):
        return (self._decor_pending or
                (self._battle_panels is not None and self._battle_panels.pending))

    def _queue_wait(self):
        if self._callback is not None or self._flash is None or (self._applied and not self._native_overlays_pending()):
            return
        import BigWorld
        generation = self._generation
        pending = [None]

        def ready():
            if self._callback != pending[0] or generation != self._generation:
                return
            self._callback = None
            self._wait()

        pending[0] = BigWorld.callback(WAIT_DELAY, ready)
        self._callback = pending[0]

    def _wait(self):
        if self._flash is None:
            return
        try:
            self._poll_decoration()
            if self._battle_panels is not None:
                self._battle_panels.poll()
            if self._applied:
                self._publish_readiness()
                if self._native_overlays_pending():
                    self._queue_wait()
                return
            if self._flash._isDAAPIInited():
                if not self._prepared:
                    self._layer('crosshair', 'initialized')
                    self._core_step('daapi-capabilities', crosshair_polls=self._samples)
                    self._probe_capabilities()
                    supported = self._availability[self._spec[0]]
                    if supported.get(self._spec[1]) is False:
                        self._fail('unsupported')
                        return
                    self._apply()
                    self._prepared = True
                    self._queue_wait()
                    return
                if not self._finalized:
                    self._core_step('cassette-snapshot', reload_type=self._spec[2]['reload_type'],
                                    clip_capacity=_sample_clip_capacity(self._spec[2]))
                    _finish_sample_state(self._flash, self._spec[2])
                    self._layer('cassette', 'sample-applied')
                    self._finalized = True
                    self._queue_wait()
                    return
                self._core_diagnostic_stage = 'visual-probe'
                reticle_visible = self._visible_sample()
                try:
                    cassette_visible = reticle_visible and self._visible_cassette()
                except Exception:
                    # A later client can name its optional clips differently.
                    cassette_visible = False
                try:
                    marker_verified = reticle_visible and self._visible_marker_variant()
                except Exception:
                    marker_verified = False
                self._trace('native_visual_probe', reticle_visible=reticle_visible,
                            cassette_verified=cassette_visible, marker_verified=marker_verified,
                            visual_polls=self._visual_samples)
                if not cassette_visible or not marker_verified:
                    self._visual_samples += 1
                    if (reticle_visible and self._visual_samples == 1 and
                            self._spec[2].get('decoration') == 'autoreloaderSurge'):
                        # A native invalidation may have staged the fourth
                        # round after the first call. Refresh its sample once.
                        try:
                            self._trace('native_core_stage', stage='refresh-surge-sample')
                            _finish_sample_state(self._flash, self._spec[2], surge_remaining_fraction=0.94)
                        except Exception:
                            pass
                    if self._visual_samples < 8:
                        self._queue_wait()
                        return
                    if not reticle_visible:
                        self._fail('hidden')
                        return
                    self._sample_error = ('cassette-unverified' if not cassette_visible
                                          else 'marker-unverified')
                # A pass includes stock controls intentionally hidden in settings.
                self._layer('crosshair', 'check-passed')
                self._layer('gun-marker', 'check-passed' if marker_verified else 'unverified')
                self._layer('cassette', 'check-passed' if cassette_visible else 'unverified')
                self._available(self._spec[0], self._spec[1], True)
                self._applied = True
                self._publish_readiness()
                if self._native_overlays_pending():
                    self._queue_wait()
                return
            self._samples += 1
            if self._samples in (1, 10, 40, 120):
                self._trace('native_core_stage', stage='await-daapi', crosshair_polls=self._samples)
            if self._samples >= MAX_WAIT_SAMPLES:
                self._fail('timeout')
            else:
                self._queue_wait()
        except Exception:
            self._fail('native')

    def _publish_readiness(self):
        if self._native_overlays_pending():
            self._status('loading')
            return
        panels = self._battle_panels
        panel_failure = self._battle_panel_start_failed or (panels is not None and panels.failed)
        error = self._sample_error or self._decor_error
        if panel_failure:
            error = 'battle-panel-unavailable'
        elif error is None and panels is not None and panels.incomplete:
            error = 'battle-panel-sample-incomplete'
        if error is not None:
            self._status('partial', error)
        elif panels is not None:
            self._status('ready', 'battle-panels-mounted')
        elif self._decor_structure_ready:
            self._status('ready', 'decoration-mounted')
        else:
            self._status('ready')

    def _probe_capabilities(self):
        from .preview_catalog import PROFILES, choices, profile
        root = self._flash.flashObject
        if not self._capabilities_probed:
            try:
                domain = root.loaderInfo.applicationDomain
            except Exception:
                domain = None
            aliases = {}
            for choice in choices():
                if choice.get('tier') == 11:
                    selection = profile(choice['id'], choice['modes'][0])
                    aliases.setdefault(selection['id'], []).append(choice['id'])
            for selected in PROFILES:
                for mode in selected['modes']:
                    try:
                        linkage = _marker_linkage(selected, mode)
                        supported = ((domain is None or domain.hasDefinition(linkage)) and
                                     all(callable(getattr(root, method, None))
                                         for method in _required_methods(selected, mode)))
                    except Exception:
                        supported = False
                    if not supported:
                        self._available(mode, selected['id'], False)
                        # A vehicle alias uses the same linkage and methods.
                        # Runtime render errors remain specific to one variant.
                        for alias in aliases.get(selected['id'], ()):
                            self._available(mode, alias, False)
            self._capabilities_probed = True

    @staticmethod
    def _open_battle_panel(stock_resource):
        import ResMgr
        if not ResMgr.isFile(PANEL_RESOURCE) or not ResMgr.isFile(stock_resource):
            return None
        host = _build_decoration_class()()
        try:
            host.createComponent(swf=PANEL_SWF)
            _configure(host)
            host.component.position.z = PREVIEW_DEPTH - 0.002
            host.active(True)
            return host
        except Exception:
            _defer_release(host)
            raise

    def _start_battle_panels(self):
        mode, unused_variant, selected, viewport, unused_scene = self._spec
        recipes = selected.get('battle_panels')
        if not recipes:
            return
        try:
            from .battle_panel_preview import BattlePanelPreview
            self._battle_panels = BattlePanelPreview(
                recipes, mode, self._settings[2 if mode == 'sniper' else 1], viewport,
                self._open_battle_panel, _defer_release, self._trace,
                _decoration_error_details, MAX_WAIT_SAMPLES)
        except Exception:
            self._battle_panel_start_failed = True
            self._trace('native_battle_panel', panel_stage='panel-component')

    def _start_decoration(self):
        family = self._spec[2].get('decoration')
        stage = 'hide-previous'
        try:
            if self._decoration is not None:
                self._hide_decoration()
            if family is None:
                self._layer('stock-decoration', 'not-requested')
                return
            self._trace('native_decor_stage', stage='prepare-host')
            if family not in DECOR_LINKAGES:
                self._decoration_unavailable('decoration-missing', 'unsupported-family')
                return
            if self._decoration is None:
                stage = 'resource-query'
                self._trace('native_decor_stage', stage=stage)
                import ResMgr
                resources = ((DECOR_RESOURCE, 'missing-host'),
                             (b'gui/flash/decorativeCrosshairPanel.swf', 'missing-stock-layer'))
                if family == 'autoreloaderSurge':
                    resources += ((b'gui/flash/autoreloaderSurge.swf', 'missing-stock-surge'),)
                for resource, missing in resources:
                    if not ResMgr.isFile(resource):
                        self._decoration_unavailable('decoration-missing', missing)
                        return
                stage = 'host-construction'
                self._trace('native_decor_stage', stage=stage)
                decoration = _build_decoration_class()()
                self._decoration = decoration
                stage = 'host-component'
                self._trace('native_decor_stage', stage=stage)
                decoration.createComponent(swf=DECOR_SWF)
                stage = 'host-configuration'
                self._trace('native_decor_stage', stage=stage)
                _configure(decoration)
                decoration.component.position.z = PREVIEW_DEPTH - 0.001
                stage = 'host-activation'
                self._trace('native_decor_stage', stage=stage)
                decoration.active(True)
            self._layer('decoration-host', 'waiting')
            stage = 'host-geometry'
            self._trace('native_decor_stage', stage=stage)
            self._decor_samples = 0
            self._decor_pending = True
            self._decoration.component.size = self._spec[3][:2]
            self._decoration.setVisible(True)
        except Exception:
            self._decoration_unavailable('decoration-failed' if family else None,
                                         stage if family else None)

    def _poll_decoration(self):
        if not self._decor_pending:
            return
        try:
            root = self._decoration.getMember(b'root')
        except Exception:
            self._decoration_unavailable('decoration-failed', 'bridge-root')
            return
        if root is not None:
            self._layer('decoration-host', 'responsive')
            try:
                self._request_decoration(root)
            except Exception:
                self._decoration_unavailable('decoration-failed', 'bridge-request')
                return
            try:
                state = root.as_getState()
            except Exception:
                self._decoration_unavailable('decoration-failed', 'bridge-state')
                return
            if state == 1:
                self._decor_structure_ready = True
                self._layer('stock-decoration', 'mounted-unverified')
                self._trace('native_decor_poll', stage='host-structure-ready',
                            decoration_polls=self._decor_samples)
                self._decor_pending = False
                return
            if state == -1:
                diagnostic, error_id, missing_qname = _decoration_error_details(root)
                self._decoration_unavailable('decoration-failed', diagnostic, error_id, missing_qname)
                return
        self._decor_samples += 1
        if self._decor_samples in (1, 10, 40, 120):
            self._trace('native_decor_poll', stage='await-root' if root is None else 'await-symbol',
                        decoration_polls=self._decor_samples)
        if self._decor_samples >= MAX_WAIT_SAMPLES:
            self._decoration_unavailable('decoration-timeout',
                                         'root-timeout' if root is None else 'library-timeout')

    def _request_decoration(self, root):
        mode, selected, viewport = self._spec[0], self._spec[2], self._spec[3]
        request = (mode, selected['decoration'], viewport)
        if self._decor_requested == request:
            return
        # The host configures mouseEnabled and mouseChildren in its own
        # constructor. The bridge only sends the supported preview method.
        self._trace('native_decor_stage', stage='bridge-request')
        self._decor_structure_ready = False
        self._decoration.setVisible(True)
        width, height, scale = viewport
        root.as_setPreview(DECOR_LINKAGES[selected['decoration']], width / 2.0,
                           height / 2.0, scale, {'arcade': 1, 'sniper': 2, 'arty': 3}[mode],
                           self._settings[2 if mode == 'sniper' else 1])
        self._decor_requested = request
        self._decor_samples = 0
        self._layer('stock-decoration', 'requested')

    def _hide_decoration(self):
        # Scaleform does not advance an invisible whole movie. Keep the owned
        # host active while its bounded frame probes finish, hiding only its
        # selected graphic; stop the empty movie once it has become idle.
        self._decor_requested = None
        self._decoration.setVisible(True)
        root = self._decoration.getMember(b'root')
        if root is not None:
            root.as_hidePreview()
            if root.as_getState() != 0:
                self._decoration.setVisible(False)

    def _decoration_unavailable(self, reason, diagnostic, as_error_id=None, missing_qname=None):
        # Optional stock decorations must never remove the base reticle or cassette on failure.
        decoration, self._decoration = self._decoration, None
        self._decor_error = reason
        self.decoration_diagnostic = diagnostic
        self._decor_pending = False
        self._decor_structure_ready = False
        if reason is not None:
            if diagnostic in ('missing-host', 'host-construction', 'host-component',
                              'host-configuration', 'host-activation', 'host-geometry',
                              'bridge-root', 'bridge-request', 'bridge-state', 'root-timeout'):
                self._layer('decoration-host', 'unavailable')
            self._layer('stock-decoration', 'unavailable')
            self._trace('native_decor_failure', reason=reason, diagnostic=diagnostic, as_error_id=as_error_id,
                        missing_qname=missing_qname, decoration_polls=self._decor_samples)
        if decoration is not None:
            _defer_release(decoration)

    def _visible_sample(self):
        mode = self._spec[0]
        root = self._flash.flashObject
        base = root.getChildAt({'arcade': 0, 'sniper': 1, 'arty': 2}[mode])
        style = self._settings[2 if mode == 'sniper' else 1]
        base_alphas = (b'centerAlphaValue', b'netAlphaValue', b'reloaderAlphaValue',
                       b'conditionAlphaValue', b'cassetteAlphaValue',
                       b'reloaderTimerAlphaValue', b'zoomIndicatorAlphaValue')
        if any(style.get(key, 0) > 0 for key in base_alphas):
            return _painted(base)
        # A player may hide every control in the base while retaining a gun
        # marker. Its active visual state is validated separately.
        return base is not None

    def _visible_marker_variant(self):
        mode, selected = self._spec[0], self._spec[2]
        root = self._flash.flashObject
        style = self._settings[2 if mode == 'sniper' else 1]
        has_tag = style.get(b'gunTagAlpha', 0) > 0
        has_mixing = style.get(b'mixingAlpha', 0) > 0
        family = selected.get('marker')
        for index, name in enumerate(self._flash.preview_markers):
            if family == 'auxiliary_rocket_launcher' and mode != 'arty':
                # The stock rocket tag has its own settings and animation.
                # The ordinary gun tag opacity does not govern its circle.
                marker = root.getChildByName(name)
                rocket = getattr(marker, 'gunTagRocket', None)
                tag = getattr(rocket, 'tag', None)
                circle = getattr(tag, 'circle', None)
                if not all(_painted(part) for part in (marker, rocket, tag, circle)):
                    self._trace('native_visual_probe', stage='rocket-glyph', marker_family=family,
                                marker_verified=False)
                    return False
                continue
            # Stock dual-accuracy secondary marker has no own tag or damage
            # hint. It may be fully hidden when mixing opacity is zero.
            if not has_mixing and (index or not has_tag):
                continue
            marker = root.getChildByName(name)
            if mode == 'arty' and self._spec[4].get('focus_unmeasured'):
                # No photograph of the dispersion is available for this frame.
                # Geometry already checked the required native marker and dots.
                return marker is not None
            if not _painted(marker):
                self._trace('native_visual_probe', stage='marker-root', marker_family=family,
                            marker_verified=False)
                return False
            if mode != 'arty' and has_mixing:
                radius = getattr(marker, 'radiusMC', None)
                if family == 'dualgun' and _painted(getattr(marker, 'chargeMixing', None)):
                    continue
                symbol = 'currMixingMC'
                if family == 'charge_shot':
                    symbol = 'chargeGunMixing'
                elif family == 'accuracy_stacks':
                    symbol = 'accuracyGunMixing'
                elif family == 'twingun':
                    symbol = 'twinGunMixing'
                elif family == 'low_charge_shot':
                    symbol = 'lowChargeShotMixingMC'
                elif selected['id'] == 'chargeable_burst':
                    symbol = 'chargeableBurst'
                if not _painted(radius) or not _painted(getattr(radius, symbol, None)):
                    self._trace('native_visual_probe', stage='marker-' + symbol.lower(),
                                marker_family=family, marker_verified=False)
                    return False
        return True

    def _visible_cassette(self):
        mode, selected = self._spec[0], self._spec[2]
        style = self._settings[2 if mode == 'sniper' else 1]
        if style.get(b'cassetteAlphaValue', 0) <= 0:
            return True
        names = {1: 'autoloaderComponent', 2: 'extraShotClipPanel',
                 3: 'controllableReloadCassette', 4: 'reloadSwitchIcon',
                 5: 'shellCalibrationClipPanel'}
        name = names.get(selected['reload_type'])
        if name is None and _sample_clip_capacity(selected) > 1:
            name = 'cassetteMC'
        if name is None:
            return True
        base = self._flash.flashObject.getChildAt({'arcade': 0, 'sniper': 1, 'arty': 2}[mode])
        if not _painted(getattr(base, name, None)):
            self._trace('native_visual_probe', stage='cassette-' + name.lower(),
                        reload_type=selected['reload_type'], cassette_verified=False)
            return False
        if name == 'autoloaderComponent':
            cassette = getattr(base.autoloaderComponent, 'cassette', None)
            # The named clips are populated by the stock timeline. The status
            # badge may be absent, and exact frame labels differ by state/skin.
            capacity = _sample_clip_capacity(selected)
            loaded = [getattr(cassette, 'shell_%d' % index, None)
                      for index in range(1, _sample_rounds_loaded(selected, capacity) + 1)]
            if not all(_painted(shell) for shell in loaded):
                self._trace('native_visual_probe', stage='autoloader-loaded-shells',
                            clip_capacity=capacity, cassette_verified=False)
                return False
            if selected.get('decoration') == 'autoreloaderSurge':
                loading = getattr(cassette, 'shell_%d' % capacity, None)
                verified = (all(getattr(shell, 'currentLabel', None) in ('ready', 'onReady')
                                for shell in loaded)
                            and _painted(loading) and getattr(loading, 'currentLabel', None) == 'reloading')
                if not verified:
                    self._trace('native_visual_probe', stage='autoloader-surge-shell',
                                clip_capacity=capacity, cassette_verified=False)
                return verified
        return True

    def _scene_zoom(self):
        if self._spec[0] == 'sniper':
            zoom = self._spec[4]['zoom']
            self._flash.as_setZoomS(_zoom_text(zoom), zoom)
        elif self._spec[0] == 'arty':
            # A separate indicator in the original view represents how far
            # the camera is zoomed. Manual frames provide ordered samples.
            self._flash.as_updateScaleWidgetS(self._spec[4]['step'] / 4.0)

    def _draw_focus(self, progress):
        self._focus_progress = progress
        stage = min(int(progress), 1)
        amount = progress - stage
        if self._direct_focus_markers:
            factors = FOCUS_FACTORS[self._spec[0]]
            scale = factors[stage] + (factors[stage + 1] - factors[stage]) * amount
            for marker, baseline in self._direct_focus_markers:
                marker.setMixingScale(baseline * scale)
        for dot, samples in self._artillery_nodes:
            start, end = samples[stage:stage + 2]
            dot.x, dot.y, dot.alpha = tuple(a + (b - a) * amount for a, b in zip(start, end))

    @property
    def supports_focus(self):
        return bool(self._artillery_nodes or self._direct_focus_markers)

    def _stop_focus_demo(self, completed=False):
        callback, self._focus_callback = self._focus_callback, None
        finished, self._focus_finished = self._focus_finished, None
        if callback is not None:
            try:
                import BigWorld
                BigWorld.cancelCallback(callback)
            except Exception:
                pass
        if completed:
            self._focus = 2
        try:
            self._draw_focus(self._focus)
        finally:
            if finished is not None:
                finished(completed)

    def play_focus_demo(self, finished):
        """Animate dispersion on the currently mounted preview markers."""
        if (self.status not in ('ready', 'partial') or not self.supports_focus or
                self._focus_finished is not None):
            return False
        try:
            import BigWorld
            started = BigWorld.time()
            generation = self._generation

            def tick():
                if self._focus_finished is not finished or self._generation != generation:
                    return
                self._focus_callback = None
                try:
                    progress = max(0.0, min(1.0, (BigWorld.time() - started) / FOCUS_DURATION))
                    if progress == 1.0:
                        self._stop_focus_demo(completed=True)
                        return
                    amount = progress * progress * (3.0 - 2.0 * progress)
                    self._draw_focus(2.0 * amount)
                    self._focus_callback = BigWorld.callback(FOCUS_FRAME_DELAY, tick)
                except Exception:
                    self._stop_focus_demo()

            self._draw_focus(0.0)
            self._focus_finished = finished
            self._focus_callback = BigWorld.callback(FOCUS_FRAME_DELAY, tick)
            return True
        except Exception:
            self._stop_focus_demo()
            return False

    def _geometry(self, include_decoration=True):
        flash, viewport, scene = self._flash, self._spec[3], self._spec[4]
        width, height, scale = viewport
        # Calibrated geometry is measured in the source frame's pixel space.
        # Background images use a centered cover transform; labels retain UI scale.
        frame_width, frame_height = scene['frame_size']
        focus_points = scene.get('focus_points')
        focus_unmeasured = scene.get('focus_unmeasured', False)
        scene_scale = (max(width / frame_width, height / frame_height)
                       if scene['calibrated'] or focus_points is not None else scale)
        flash.component.size = (width, height)
        flash.as_setSizeS(width, height)
        flash.as_setScaleS(scale)
        flash.as_recreateDeviceS(width / 2.0, height / 2.0)
        artillery_nodes = []
        direct_focus_markers = []
        for name in flash.preview_markers:
            marker = flash.flashObject.getChildByName(name)
            if marker is None:
                raise ValueError('Original preview marker unavailable')
            marker.x, marker.y = width / 2.0, height / 2.0
            marker.visible = True
            baseline = scene_scale * scene['marker_scale'] * (1.3 if name != MARKER_NAME else 1)
            if self._spec[0] == 'arty':
                marker.setMixingScale(baseline)
                # Captured reference points belong only to this isolated sample.
                # They never become world points or modify the live gun marker.
                points = scene['points']
                radius_x, radius_y = scene['ellipse']
                for index in range(37):
                    child = marker.getChildByName(b'elem_%d' % (index + 1))
                    if child is None:
                        raise ValueError('Original strategic node unavailable')
                    child.visible = not focus_unmeasured
                    if focus_unmeasured:
                        continue
                    if focus_points is not None:
                        samples = tuple(stage[index] for stage in focus_points)
                    else:
                        if points is None:
                            angle = index * 2 * math.pi / 37
                            x, y = math.cos(angle) * radius_x, math.sin(angle) * radius_y
                        else:
                            x, y = points[index]
                        samples = tuple((x * factor, y * factor, 1.0) for factor in FOCUS_FACTORS['arty'])
                    artillery_nodes.append((child, tuple((x * scene_scale, y * scene_scale, opacity)
                                                         for x, y, opacity in samples)))
            elif self._spec[2].get('marker') == 'auxiliary_rocket_launcher':
                # The stock active rocket sight hides its dispersion circle.
                marker.setMixingScale(baseline)
            else:
                # Stock setMixingScale addresses the dispersion and, for
                # double barrels, the charge rings. It leaves the aim glyph fixed.
                direct_focus_markers.append((marker, baseline))
        self._artillery_nodes = tuple(artillery_nodes)
        self._direct_focus_markers = tuple(direct_focus_markers)
        if focus_unmeasured and self._focus_finished is not None:
            self._stop_focus_demo()
        else:
            self._draw_focus(self._focus_progress)
        if include_decoration and self._battle_panels is not None:
            self._battle_panels.resize(viewport)
            if self._battle_panels.pending:
                self._queue_wait()
        family = self._spec[2].get('decoration')
        if (include_decoration and family and self._decoration is not None and
                self._decor_requested != (self._spec[0], family, viewport)):
            try:
                self._decoration.component.size = (width, height)
                self._decor_pending = True
                self._poll_decoration()
                if self._applied:
                    self._publish_readiness()
                if self._decor_pending:
                    self._queue_wait()
            except Exception:
                self._decoration_unavailable('decoration-failed', 'host-geometry')
                if self._applied:
                    self._publish_readiness()

    def _apply(self):
        flash, mode, selected = self._flash, self._spec[0], self._spec[2]
        view_id = {'arcade': 1, 'sniper': 2, 'arty': 3}[mode]
        self._core_step('apply-stock-settings')
        flash.flashObject.mouseEnabled = False
        flash.flashObject.mouseChildren = False
        flash.as_setSettingsS(self._settings)
        flash.as_setViewS(view_id, 2 if mode == 'sniper' else 1)
        self._scene_zoom()
        self._geometry(False)
        self._core_step('create-marker', marker_family=selected['marker'])
        linkage = _marker_linkage(selected, mode)
        if not flash.as_createGunMarkerS(view_id, linkage, MARKER_NAME):
            raise ValueError('Original preview marker could not be created')
        flash.preview_markers.append(MARKER_NAME)
        if selected.get('marker') == 'dual_accuracy' and mode != 'arty':
            self._core_step('create-secondary-marker', marker_family=selected['marker'])
            from gui.Scaleform.genConsts.GUN_MARKER_VIEW_CONSTANTS import GUN_MARKER_VIEW_CONSTANTS as C
            name = (C.SNIPER_DUAL_ACC_GUN_MARKER_NAME if mode == 'sniper'
                    else C.ARCADE_DUAL_ACC_GUN_MARKER_NAME)
            if not flash.as_createGunMarkerS(view_id, linkage, name):
                raise ValueError('Original secondary marker could not be created')
            flash.preview_markers.append(name)
        self._layer('gun-marker', 'attached')
        self._core_step('apply-marker-geometry', marker_count=len(flash.preview_markers))
        self._geometry()
        capacity = _sample_clip_capacity(selected)
        sample = {'clip_capacity': capacity, 'rounds_loaded': _sample_rounds_loaded(selected, capacity),
                  'reload_type': selected['reload_type']}
        if selected.get('decoration') == 'autoreloaderSurge':
            sample['available_charges'] = SURGE_READY_CHARGES
        if selected.get('marker') == 'accuracy_stacks':
            sample['accuracy_stacks'] = ACCURACY_MAX_STACKS
        self._core_step('initial-stock-sample', **sample)
        _sample_state(flash, selected, self._hide_stock_distance)
        if mode == 'arty' and self._show_arty_indicators:
            self._core_step('artillery-indicators')
            try:
                _sample_arty_indicators(flash)
            except Exception:
                self._sample_error = 'artillery-indicators-unavailable'
                self._core_step('artillery-indicators', reason=self._sample_error)

    def close(self):
        self._trace('native_close', status=self.status)
        self._spec = None
        self._discard()
        self._capabilities_probed = False
        self._settings = None
        self._show_arty_indicators = False
        self._availability = dict((mode, {}) for mode in ('arcade', 'sniper', 'arty'))
        self._status('unavailable')


def _marker_linkage(selected, mode):
    """Resolve only source-confirmed original marker linkages."""
    from gui.Scaleform.genConsts.GUN_MARKER_VIEW_CONSTANTS import GUN_MARKER_VIEW_CONSTANTS as C
    if mode == 'arty':
        return C.GUN_MARKER_SPG_LINKAGE
    kind = selected.get('marker', 'standard')
    names = {
        'standard': 'GUN_MARKER_LINKAGE',
        'dual_accuracy': 'GUN_MARKER_LINKAGE',
        'dualgun': 'DUAL_GUN_SNIPER_MARKER_LINKAGE' if mode == 'sniper' else 'DUAL_GUN_ARCADE_MARKER_LINKAGE',
        'twingun': 'TWIN_GUN_MARKER_LINKAGE',
        'accuracy_stacks': 'ACCURACY_GUN_MARKER_LINKAGE',
        'charge_shot': 'CHARGE_GUN_MARKER_LINKAGE',
        'low_charge_shot': 'LOW_CHARGE_SHOT_GUN_MARKER_LINKAGE',
        'auxiliary_rocket_launcher': 'AUXILIARY_ROCKET_LAUNCHER_GUN_MARKER_SNIPER_LINKAGE' if mode == 'sniper' else 'AUXILIARY_ROCKET_LAUNCHER_GUN_MARKER_ARCADE_LINKAGE',
    }
    return getattr(C, names[kind])


def _sample_clip_capacity(selected):
    identifier = selected['id']
    if identifier == 'temperature_autocannon':
        # Ares 90 C: the stock ammo plugin passes its 250-shell clip through
        # CASSETTE_CLIP. It does not mark this gun as UNLIMITED_CLIP.
        return 250
    declared = selected.get('capacity')
    if declared in (2, 3, 4, 5):
        return declared
    return 4 if selected['reload_type'] != 0 or identifier in ('cassette', 'forced_reload') else 1


def _sample_rounds_loaded(selected, capacity):
    identifier = selected['id']
    if identifier in ('forced_reload', 'bustle_feed', 'low_charge_shot'):
        return 0
    if identifier == 'temperature_autocannon':
        # Keep the stock indicator for an autocannon with under 20% ammo.
        return 49
    if selected['reload_type'] == 2:
        # The reserve-shell shot is available with one round during extra reload.
        return 1
    if selected['reload_type'] in (1, 3):
        return capacity - 1
    return capacity


def _sample_distance(flash, hidden):
    if hidden:
        flash.as_clearDistanceS(True)
    else:
        flash.as_setDistanceS(_distance_text(250))


def _sample_state(flash, selected, hide_stock_distance=False):
    """Finite example states; duration APIs would start Flash timer loops."""
    reload_type = selected.get('reload_type', 0)
    identifier = selected['id']
    manual_reload = identifier == 'forced_reload'
    bustle_reload = identifier == 'bustle_feed'
    partial_shot = identifier == 'low_charge_shot'
    capacity = _sample_clip_capacity(selected)
    quantity = 30
    in_clip = _sample_rounds_loaded(selected, capacity)
    ammo_state = b'normal'
    if identifier == 'temperature_autocannon':
        # Below the 20% threshold from the stock automatic-fire cassette logic.
        quantity = in_clip
        ammo_state = b'critical'
    if bustle_reload:
        quantity = 40
    flash.as_setHealthS(0.82)
    _sample_distance(flash, hide_stock_distance)
    flash.as_setClipParamsS(capacity, 1, reload_type)
    flash.as_setAmmoStockS(quantity, in_clip, ammo_state, False)
    if bustle_reload:
        # The stock gun's base reload is 9.2 s and the feed's reload factor is
        # 1.5. Show the ordinary stock timer halfway through that reload.
        flash.as_setReloadingAsPercentS(6.9, 50, True, False)
    elif partial_shot:
        flash.as_setReloadingAsPercentS(6.0, 70.73, True, True)
    elif reload_type == 2:
        # The reserve-shell interval is 4.5 s for AMX 67 Imbattable.
        flash.as_setReloadingAsPercentS(2.25, 50, True, True)
    elif manual_reload or reload_type == 3:
        flash.as_setReloadingAsPercentS(3.5, 65, True, False)
    else:
        flash.as_setReloadingAsPercentS(0, 100, False, True)
    kind = selected.get('marker', 'standard')
    if kind == 'dualgun':
        flash.as_updateDualGunMarkerStateS(GUN_MARKER_VISIBLE)
    elif kind == 'twingun':
        flash.as_setTwinGunMarkerActiveS(True)
        flash.as_setTwinGunMarkerStateS(GUN_MARKER_VISIBLE)
    elif kind == 'dual_accuracy':
        # The secondary is recognized by the stock marker name and must
        # also be activated explicitly by the same pair of methods as in battle.
        flash.as_setSecondaryGunMarkerActiveS(True)
        flash.as_setDispersionCircleThicknessS(True)
    elif kind == 'accuracy_stacks':
        flash.as_setAccuracyStacksProgressS(ACCURACY_MAX_STACKS)
    elif kind == 'charge_shot':
        flash.as_setChargeGunActiveS(True)
        # Object 432U is at its maximum charge level, after the shot block.
        flash.as_setChargeGunStateS(0.99, 3, False)
    elif kind == 'low_charge_shot':
        from gui.Scaleform.genConsts.LOW_CHARGE_SHOT_CONSTS import LOW_CHARGE_SHOT_CONSTS
        # Gorilla can fire at half reload; keep the partial shot marker active.
        flash.as_setLowChargeInitialTimeS(20.5, 10.25, 2.0, 0.5)
        # Replay's one-shot setter updates the real display without a timer.
        flash.as_setLowChargeTimeLeftS(6.0, LOW_CHARGE_SHOT_CONSTS.LOW_CHARGE, True)
        flash.as_setReloadingCounterShownS(False)
    if identifier == 'chargeable_burst' or reload_type in (3, 5):
        flash.as_setNetSeparatorTypeS(b'short')
    elif reload_type == 1:
        flash.as_setNetSeparatorTypeS(b'empty')
    if selected.get('decoration') == 'autoreloaderSurge':
        # All three charges are available in the other widget, none is in use.
        flash.as_setAutoreloaderSurgeStateS(False)
    elif identifier == 'chargeable_burst':
        flash.as_setChargeableBurstModeS(True)
    elif identifier == 'heating_zones_gun':
        # The heat-zones panel shows the upper zone, outside stock comfort.
        flash.as_setDispersionCircleThicknessS(False)
    elif identifier == 'propellant_gun':
        flash.as_setAlternateZoomPositionS(True)
    elif identifier == 'stance_dance':
        flash.as_setReloadBoostS(True)
    elif identifier in ('stationary_reload', 'controllable_reload'):
        flash.as_setIsInControllableReloadS(True)
    elif identifier == 'battle_fury':
        flash.as_setReloadBoostBorderS(True, True)
        flash.as_setReloadBoostS(True)
    elif identifier == 'pillbox_siege':
        flash.as_setNetTypeS(5)
        flash.as_setNetSeparatorVisibleS(False)
    elif identifier == 'overheat_stacks':
        flash.as_setAlternateZoomPositionS(True)


def _distance_text(meters):
    from gui.Scaleform.locale.INGAME_GUI import INGAME_GUI
    from helpers import i18n
    return i18n.makeString(INGAME_GUI.DISTANCE_METERS, meters=meters)


def _zoom_text(zoom):
    from gui.Scaleform.locale.INGAME_GUI import INGAME_GUI
    from helpers import i18n
    return i18n.makeString(INGAME_GUI.AIM_ZOOM, zoom=zoom)


def _sample_arty_indicators(flash):
    # These IDs are local to the preview panel. The stock panel pairs its
    # shell indicator records with the flight times by shellIntCD.
    labels = (b'HE', b'AP')
    try:
        from gui.impl import backport
        from gui.impl.gen import R
        abbreviations = R.strings.item_types.shell.kindsAbbreviation
        resources = (abbreviations.dyn('HIGH_EXPLOSIVE'), abbreviations.dyn('ARMOR_PIERCING'))
        # The stock R lookup returns a callable resource; the text bridge
        # requires the numeric resource ID returned by calling it.
        localized = tuple(backport.text(resource()) if resource else None for resource in resources)
        labels = tuple(name or fallback for name, fallback in zip(localized, labels))
    except (ImportError, AttributeError, LookupError, RuntimeError, TypeError, ValueError):
        pass
    flash.as_setGunMarkersIndicatorsS([
        {b'shellIntCD': 1, b'shellTypeName': labels[0], b'shotResult': 1, b'state': 1},
        {b'shellIntCD': 2, b'shellTypeName': labels[1], b'shotResult': 0, b'state': 0},
    ])
    flash.as_setShotFlyTimesS([
        {b'shellIntCD': 1, b'flyTime': 1.85},
        {b'shellIntCD': 2, b'flyTime': -1.0},
    ])


def _finish_sample_state(flash, selected, surge_remaining_fraction=0.95):
    """Run only after the original clip/ammo invalidation has drawn once."""
    reload_type = selected.get('reload_type', 0)
    if selected.get('marker') == 'auxiliary_rocket_launcher':
        # The stock marker's deferred configUI starts with the rocket tag
        # hidden. Apply the aiming state after the stock marker has drawn.
        flash.as_setAuxiliaryRocketLauncherActiveS(True)
        flash.as_setNetTypeS(6)
        flash.as_setReloadingCounterShownS(False)
    elif reload_type == 1:
        # 1.0 means the gun is loaded. A value below1 moves the entire cassette
        # into its inter-shot animation and can hide the rectangular shells.
        flash.as_setAutoloaderReloadasPercentS(1.0)
        remaining_fraction, seconds = 0.35, 3.5
        if selected.get('decoration') == 'autoreloaderSurge':
            # Early in the fourth round's normal refill, surge can still cut
            # the remaining time. All charges are ready and none is in use.
            flash.as_setAutoreloaderSurgeStateS(False)
            remaining_fraction = surge_remaining_fraction
            seconds = round(SURGE_TOP_SHELL_RELOAD * remaining_fraction, 2)
        flash.as_setAutoloaderPercentS(remaining_fraction, seconds, False, True, False)
    elif reload_type == 3:
        flash.as_setIsInControllableReloadS(True)
        flash.as_setAutoloaderPercentS(0.35, 3.5, False, True, False)
    elif reload_type == 5:
        flash.as_setShellCalibrationStateS(3)
