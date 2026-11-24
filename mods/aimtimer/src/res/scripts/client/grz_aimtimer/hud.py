# -*- coding: ascii -*-
"""Visual-only native aimtimer overlay; no SimpleGUI input callbacks.

The primitive cursor polling contract follows StaySharpMedkit's crash fix.
GUI.Text usage follows the client's ValueTracker/DebugDrawEntity examples.
"""
from __future__ import absolute_import

import math
import time

from .core import format_reading, mode_position

TEXTURE_ROOT = 'gui/maps/grz_aimtimer/v0_1_7/'
REFERENCE_TEXT = '~15.55 s'
_retired = []
_MISSING = object()
try:
    _READING_NUMBERS = (int, long, float)
except NameError:
    _READING_NUMBERS = (int, float)
_POSITION_KEYS = ('schema_version', 'hud_offset_y',
                  'hud_offset_arcade_x', 'hud_offset_arcade_y',
                  'hud_offset_sniper_x', 'hud_offset_sniper_y',
                  'hud_offset_arty_x', 'hud_offset_arty_y')


def finite(value):
    try:
        return not isinstance(value, bool) and not math.isnan(value) and not math.isinf(value)
    except (TypeError, ValueError, OverflowError):
        return False


def clip_position(x, y, viewport, depth=0.1):
    width, height = viewport
    return (2.0 * x / width - 1.0, 1.0 - 2.0 * y / height, depth)


class ClickTracker(object):
    """First sample establishes a baseline; press and release must match."""
    def __init__(self):
        self.reset()

    def reset(self):
        self.previous = None
        self.was_active = False
        self.pressed = None

    def update(self, down, active, hovered):
        clicked = None
        if not active:
            self.pressed = None
        elif self.was_active and self.previous is not None and down != self.previous:
            if down:
                self.pressed = hovered
            else:
                if self.pressed is not None and hovered == self.pressed:
                    clicked = self.pressed
                self.pressed = None
        self.previous = bool(down)
        self.was_active = bool(active)
        return clicked


class Overlay(object):
    def __init__(self, gui, bigworld, resource_exists, log=None, clock=None):
        self.gui = gui
        self.world = bigworld
        self.resource_exists = resource_exists
        self.log = log or (lambda code: None)
        self.clock = clock or getattr(time, 'monotonic', time.time)
        self.components = {}
        self.roots = []
        self.controls = {}
        self.viewport = (0, 0)
        self.context = None
        self.failed = False
        self.closed = False
        self._signature = None
        self._metric_signature = None
        self._metrics = None
        self._placement = None
        self._applied = {}
        self._visible = set()
        self._frame_visible = None
        self._hovered = None
        self._position_key = None
        self._position_value = None
        self._reading_key = None
        self._reading_value = None
        self._layout_key = None
        self._layout_value = None

    def _assign(self, name, attribute, value):
        # Cache values we own rather than reading native properties merely to
        # compare them. Equal assignments can rebuild native text/geometry.
        key = (name, attribute)
        if self._applied.get(key, _MISSING) != value:
            setattr(self.components[name], attribute, value)
            self._applied[key] = value
            if attribute == 'text':
                # Text can rebuild native bounds. Reapply width0 with the
                # requested height so the new glyphs retain their aspect ratio.
                self._applied.pop((name, 'size'), None)

    def _set_visible(self, name, visible):
        self._assign(name, 'visible', visible)
        if visible:
            self._visible.add(name)
        else:
            self._visible.discard(name)

    def _finish_visibility(self):
        desired, self._frame_visible = self._frame_visible, None
        if desired is not None:
            for name in tuple(self._visible - desired):
                self._set_visible(name, False)

    def _position(self, config, mode):
        key = (mode,) + tuple(config.get(field) for field in _POSITION_KEYS)
        if key != self._position_key:
            self._position_value = mode_position(config, mode)
            self._position_key = key
        return self._position_value

    def _configure(self, component, text=False):
        enum = self.gui.Simple
        component.script = None
        component.focus = False
        component.moveFocus = False
        component.mouseButtonFocus = False
        component.widthMode = enum.eSizeMode.PIXEL
        component.heightMode = enum.eSizeMode.PIXEL
        component.horizontalPositionMode = enum.ePositionMode.CLIP
        component.verticalPositionMode = enum.ePositionMode.CLIP
        component.horizontalAnchor = enum.eHAnchor.CENTER
        component.verticalAnchor = enum.eVAnchor.CENTER
        component.materialFX = enum.eMaterialFX.BLEND
        component.filterType = enum.eFilterType.LINEAR
        component.visible = False
        component.position = (0.0, 0.0, 0.1)
        if text:
            component.multiline = False
            component.explicitSize = True

    def _create(self):
        if self.closed or self.failed:
            return
        if 'main' in self.components:
            return
        if self.components:
            self.suspend()
        try:
            for name in ('panel_000.dds', 'panel_050.dds', 'panel_100.dds',
                         'move.dds', 'gear.dds', 'power_on.dds', 'power_off.dds'):
                if not self.resource_exists(TEXTURE_ROOT + name):
                    raise ValueError('missing_owned_texture')
            specs = (('back', 'panel_050.dds'), ('main_shadow', None), ('main', None),
                     ('move', 'move.dds'), ('gear', 'gear.dds'),
                     ('power', 'power_on.dds'))
            for name, texture in specs:
                component = (self.gui.Simple(TEXTURE_ROOT + texture) if texture
                             else self.gui.Text(''))
                self.components[name] = component
                self._configure(component, texture is None)
                self._applied[(name, 'visible')] = False
                self._applied[(name, 'position')] = (0.0, 0.0, 0.1)
                if texture:
                    self._applied[(name, 'textureName')] = TEXTURE_ROOT + texture
                # Keep ownership before addRoot, including a partly successful call.
                self.roots.append(component)
                self.gui.addRoot(component)
        except Exception:
            self.failed = True
            self.log('hud_allocation_failed')
            self.close()

    def _create_power(self):
        """Disabled controls need one visual root, never fonts or the frame."""
        if self.closed or self.failed:
            return
        if set(self.components) == set(('power',)):
            return
        if self.components:
            self.suspend()
        try:
            if not self.resource_exists(TEXTURE_ROOT + 'power_off.dds'):
                raise ValueError('missing_owned_texture')
            power = self.gui.Simple(TEXTURE_ROOT + 'power_off.dds')
            self.components['power'] = power
            self._configure(power)
            self._applied[('power', 'visible')] = False
            self._applied[('power', 'position')] = (0.0, 0.0, 0.1)
            self._applied[('power', 'textureName')] = TEXTURE_ROOT + 'power_off.dds'
            self.roots.append(power)
            self.gui.addRoot(power)
        except Exception:
            self.failed = True
            self.log('hud_allocation_failed')
            self.close()

    def hide(self, reset_tracking=True):
        for name in tuple(self._visible):
            try:
                self._set_visible(name, False)
            except Exception:
                pass
        self.controls = {}
        self._signature = None
        self._placement = None
        self._frame_visible = None

    def placement(self):
        """Detached visible geometry for the runtime's polled drag gesture."""
        return dict(self._placement) if self._placement is not None else None

    def _place(self, name, x, y, width, height, viewport, colour, depth):
        self._assign(name, 'position', clip_position(x, y, viewport, depth))
        self._assign(name, 'size', (float(width), float(height)))
        if name in ('move', 'gear', 'power') and self._hovered == {
                'move': 'move', 'gear': 'settings', 'power': 'toggle'}[name]:
            colour = (255, 217, 142, colour[3])
        self._assign(name, 'colour', colour)
        self._set_visible(name, True)
        if self._frame_visible is not None:
            self._frame_visible.add(name)

    def _text(self, name, text, x, y, height, viewport, colour):
        # All HUD strings are short, controlled ASCII strings, not markup/data.
        if not isinstance(text, str):
            text = text.encode('ascii', 'replace')
        self._assign(name, 'text', text)
        self._assign(name + '_shadow', 'text', text)
        self._place(name + '_shadow', x + 1, y + 1, 0, height, viewport,
                    (0, 0, 0, colour[3]), 0.09)
        self._place(name, x, y, 0, height, viewport, colour, 0.08)

    def _measure_text(self, text, height):
        """Use the native text's aspect-preserving pixel bounds when available."""
        signature = (text, height)
        if signature == self._metric_signature and self._metrics is not None:
            return self._metrics
        component = self.components['main']
        self._assign('main', 'text', text)
        self._assign('main', 'size', (0.0, float(height)))
        size = None
        try:
            width, actual_height = component.size
            if all(finite(v) and 0 < v <= 65536 for v in (width, actual_height)):
                size = (float(width), float(actual_height))
        except Exception:
            pass
        if size is None:
            try:
                width, native_height = component.stringDimensions(text)
                if all(finite(v) and 0 < v <= 65536 for v in (width, native_height)):
                    size = (float(width) * height / native_height, float(height))
            except Exception:
                pass
        if size is None:
            # Older native builds can lack metrics. Approximate the same
            # bounded reference string rather than changing the digit budget.
            width = sum(.28 if c in ('.', ',') else .30 if c == ' ' else
                        .82 if c == 'm' else .56 for c in text) * height
            size = (max(1.0, width), float(height))
        self._metric_signature, self._metrics = signature, size
        return size

    def _control_metrics(self, height):
        # Reuse the last known reference size or a small primitive estimate.
        # Disabled mode must not create or measure native text components.
        if self._metric_signature == (REFERENCE_TEXT, height) and self._metrics:
            return self._metrics
        width = sum(.28 if c in ('.', ',') else .30 if c == ' ' else
                    .82 if c == 'm' else .56 for c in REFERENCE_TEXT) * height
        return max(1.0, width), float(height)

    def _layout(self, viewport, scale, config):
        key = (tuple(viewport), scale, config['enabled'],
               config['hud_font_px'], config['hud_frame_scale_pct'])
        if (key == self._layout_key and self._layout_value is not None and
                (not config['enabled'] or self._metric_signature is not None)):
            return self._layout_value
        width, height = viewport
        factor = config['hud_frame_scale_pct'] / 100.0
        metrics = self._measure_text if config['enabled'] else self._control_metrics
        if config['enabled']:
            text_width, text_height = metrics(REFERENCE_TEXT, config['hud_font_px'] * scale)
        else:
            text_width, text_height = metrics(config['hud_font_px'] * scale)
        panel_width = (text_width + 2 * scale) * factor
        panel_height = (text_height + 2 * scale) * factor
        fitted = min(1.0, (width - 8.0) / (panel_width + 88 * scale),
                     (height - 8.0) / max(panel_height, 24 * scale))
        if fitted < 1.0:
            scale *= fitted
            if config['enabled']:
                text_width, text_height = metrics(REFERENCE_TEXT, config['hud_font_px'] * scale)
            else:
                text_width, text_height = metrics(config['hud_font_px'] * scale)
            panel_width = (text_width + 2 * scale) * factor
            panel_height = (text_height + 2 * scale) * factor
        self._layout_key = key
        self._layout_value = (scale, panel_width, panel_height,
                              panel_width / 2.0 + 30 * scale,
                              panel_width / 2.0 + 58 * scale,
                              max(panel_height / 2.0, 12 * scale))
        return self._layout_value

    def _reading(self, sample, config, language):
        value = sample.get('remaining_s') if sample.get('available') is True else None
        if type(value) not in _READING_NUMBERS or not finite(value):
            value = None
        key = (value, language)
        if key != self._reading_key:
            self._reading_value = format_reading(value, config, language)
            self._reading_key = key
        return self._reading_value

    def update(self, sample, config, language, visible, settings_open=False,
               controls_visible=False):
        if self.closed or self.failed:
            return
        context = sample.get('context')
        viewport = sample.get('viewport', (0, 0))
        try:
            if not config['enabled'] and (not controls_visible or settings_open):
                self.suspend()
                return
            width, height = viewport
            if not all(finite(x) and 16 <= x <= 32768 for x in (width, height)):
                self.hide()
                return
            if not visible or context not in ('battle', 'garage'):
                self.hide(reset_tracking=context != 'battle')
                return
            if context == 'battle' and not sample.get('battle_eligible'):
                self.hide()
                return
            if context == 'garage':
                self.hide()
                self.context = context
                return
            if config['enabled']:
                self._create()
            else:
                self._create_power()
            if self.closed or self.failed:
                return
            self.context = context
            self.viewport = viewport
            scale = sample.get('scale', 1.0)
            scale = max(0.5, min(3.0, scale)) if finite(scale) else 1.0
            # Follow the reticle's pixel anchor, not zoom or aiming-circle
            # radius. Font and frame sizing use only interface scale.
            aim = sample.get('aim_position')
            if not (isinstance(aim, (tuple, list)) and len(aim) == 2 and
                    all(finite(v) and abs(v) <= 65536 for v in aim)):
                offset = sample.get('aim_offset')
                if (isinstance(offset, (tuple, list)) and len(offset) == 2 and
                        all(finite(v) and -1 <= v <= 1 for v in offset)):
                    aim = ((offset[0] + 1) * width / 2.0,
                           (1 - offset[1]) * height / 2.0)
                elif not config['enabled'] and controls_visible:
                    aim = (width / 2.0, height / 2.0)
                else:
                    self.hide()
                    return
            # Each camera mode uses its current reticle, with no correction
            # carried over from another mode. Keep position scaling independent
            # of any font fitting needed for a tiny viewport.
            mode = sample.get('mode', 'unknown')
            if not isinstance(mode, str):
                mode = 'unknown'
            position = self._position(config, mode)
            reading = None
            if config['enabled']:
                reading = self._reading(sample, config, language)
            signature = (tuple(viewport), tuple(aim), mode, scale, position,
                         config['enabled'], config['hud_font_px'],
                         config['hud_frame_scale_pct'], config['hud_background_opacity'],
                         bool(controls_visible), bool(settings_open),
                         None if reading is None else (reading['text'], reading['colour']))
            if (signature == self._signature and
                    (not config['enabled'] or self._metric_signature is not None)):
                # Nothing changed, including visibility and hit geometry. The
                # native components continue rendering without Python writes.
                self._frame_visible = None
                return
            # Stage visibility only for a changed frame. Static updates need
            # neither native assignments nor another visible-set allocation.
            self._frame_visible = set()
            self.controls = {}
            self._placement = None
            position_scale = scale
            (scale, panel_width, panel_height, left, right, edge) = self._layout(
                viewport, scale, config)
            x = max(left + 4, min(width - right - 4,
                    aim[0] + position[0] * position_scale))
            y = max(edge + 4, min(height - edge - 4,
                    aim[1] + position[1] * position_scale))
            if config['enabled']:
                colour = tuple(reading['colour'][:3]) + (255,)
                opacity = int(math.floor(config['hud_background_opacity'] * 100 + .5))
                if opacity > 0:
                    # Native BLEND reliably uses texture alpha. Keep vertex
                    # alpha fully opaque and select a baked opacity level.
                    texture = TEXTURE_ROOT + ('panel_%03d.dds' % opacity)
                    self._assign('back', 'textureName', texture)
                    self._place('back', x, y, panel_width, panel_height, viewport,
                                (255, 255, 255, 255), 0.12)
                self._text('main', reading['text'], x, y,
                           config['hud_font_px'] * scale, viewport, colour)
            if config['enabled']:
                self._placement = {
                    'mode': mode, 'viewport': tuple(viewport),
                    'scale': position_scale, 'center': (x, y),
                    'anchor': tuple(aim),
                    'bounds': (left + 4, edge + 4,
                               width - right - 4, height - edge - 4),
                    # At a viewport edge start from the visible position,
                    # rather than jumping to a saved off-screen coordinate.
                    'offset': ((x - aim[0]) / position_scale,
                               (y - aim[1]) / position_scale),
                }
            if not controls_visible or settings_open:
                self._finish_visibility()
                self._signature = signature
                return
            mx = x - panel_width / 2.0 - 16 * scale
            gx, px = x + panel_width / 2.0 + 16 * scale, x + panel_width / 2.0 + 44 * scale
            gs = ps = 24 * scale
            if config['enabled']:
                self._place('move', mx, y, gs, gs, viewport,
                            (255, 255, 255, 255), 0.07)
                self.controls['move'] = (mx, y, gs, gs)
                self._place('gear', gx, y, gs, gs, viewport,
                            (255, 255, 255, 255), 0.07)
                self.controls['settings'] = (gx, y, gs, gs)
            self._assign('power', 'textureName', TEXTURE_ROOT + (
                'power_on.dds' if config['enabled'] else 'power_off.dds'))
            self._place('power', px, y, ps, ps, viewport,
                        (255, 255, 255, 255), 0.07)
            self.controls['toggle'] = (px, y, ps, ps)
            self._finish_visibility()
            self._signature = signature
        except Exception:
            self.failed = True
            self.log('hud_update_failed')
            self.close()

    def hit_test(self, clip_point):
        try:
            width, height = self.viewport
            x, y = clip_point
            if not all(finite(v) for v in (x, y)):
                return None
            sx, sy = (x + 1) * width / 2.0, (1 - y) * height / 2.0
            for name in ('move', 'settings', 'toggle'):
                geometry = self.controls.get(name)
                if geometry is not None:
                    cx, cy, w, h = geometry
                    if abs(sx - cx) <= w / 2.0 and abs(sy - cy) <= h / 2.0:
                        return name
        except Exception:
            pass
        return None

    def hover(self, name):
        # Cosmetic colour only; never seize global cursor ownership.
        self._hovered = name
        for action, key in (('move', 'move'), ('settings', 'gear'), ('toggle', 'power')):
            if key in self._visible:
                self._assign(key, 'colour', ((255, 217, 142, 255) if name == action
                                            else (255, 255, 255, 255)))

    def suspend(self):
        """Detach owned roots while leaving the overlay available for re-enable."""
        self.hide(reset_tracking=False)
        if not self.roots:
            return
        entries, self.roots = self.roots, []
        self.components = {}
        self._applied = {}
        self._visible = set()
        self._hovered = None
        self._layout_key = self._layout_value = None
        pending = {'gui': self.gui, 'entries': entries}
        _retired.append(pending)

        def detach():
            if pending not in _retired:
                return
            retained = []
            for component in pending['entries']:
                try:
                    pending['gui'].delRoot(component)
                except Exception:
                    retained.append(component)
            if retained:
                pending['entries'] = retained
                self.log('hud_detach_incomplete')
            else:
                _retired.remove(pending)
        try:
            self.world.callback(0.0, detach)
        except Exception:
            # Hidden visual-only roots are preferable to native re-entrant removal.
            self.log('hud_deferred_detach_unavailable')

    def close(self):
        self.closed = True
        self.suspend()
