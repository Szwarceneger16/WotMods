# -*- coding: utf-8 -*-
"""Finite editor scene metadata. Never reads or changes the active camera.

Geometry marked uncalibrated is only the existing isolated reticle sample.
The capture importer replaces these records with measured frame geometry;
these values must not be presented as a ballistic simulation.
"""
from __future__ import absolute_import, division, unicode_literals

import math

try:
    _TEXT = (str, unicode)
    _INTEGER = (int, long)
except NameError:
    _TEXT = (str,)
    _INTEGER = (int,)

SCENE_MODES = {'arcade': 'arcade', 'sniper': 'sniper',
               'arty_top': 'arty', 'arty_trajectory': 'arty'}
DEFAULT_SCENES = {'arcade': 'arcade', 'sniper': 'sniper', 'arty': 'arty_top'}
DEFAULT_STEPS = {'arcade': 1, 'sniper': 3, 'arty_top': 2, 'arty_trajectory': 2}
DEFAULT_FOCUS = 1
FOCUS_FACTORS = {'arcade': (1.62, 1.0, 0.48), 'sniper': (1.62, 1.0, 0.18),
                 'arty': (2.25, 1.0, 0.48)}


def _sample(zoom=None):
    return {'zoom': zoom, 'marker_scale': 1.0, 'ellipse': (95.0, 52.0),
            'points': None, 'frame_size': (1920, 1080), 'calibrated': False}


# The build/import step replaces only these owned records after real captures.
SCENE_FRAMES = {
    'arcade': tuple(_sample() for unused in range(5)),
    'sniper': tuple(_sample(zoom) for zoom in (2, 4, 8, 16, 25)),
    'arty_top': tuple(_sample() for unused in range(5)),
    'arty_trajectory': tuple(_sample() for unused in range(5)),
}

try:
    # Generated from this project's own capture set by the build/import step.
    # Never imports a path supplied by the settings document or game account.
    from .scene_frames_data import SCENE_FRAMES as _CAPTURED_FRAMES
except ImportError:
    _CAPTURED_FRAMES = None
if isinstance(_CAPTURED_FRAMES, dict):
    SCENE_FRAMES.update(dict((key, value) for key, value in _CAPTURED_FRAMES.items()
                            if key in SCENE_MODES))


def _finite(value, minimum, maximum):
    if type(value) not in _INTEGER + (float,):
        return None
    if minimum <= value <= maximum and not math.isnan(value) and not math.isinf(value):
        return float(value)
    return None


def resolve_focus(value):
    """Validate a preview-only focus preset."""
    number = _finite(value, 0, 2)
    return int(number) if number is not None and number == int(number) else None


def _points(value, dimensions):
    if not isinstance(value, (tuple, list)) or len(value) != 37:
        return None
    checked = []
    bounds = ((-32768, 32768), (-32768, 32768), (0, 1))
    for point in value:
        if not isinstance(point, (tuple, list)) or len(point) != dimensions:
            return None
        values = tuple(_finite(number, *limits) for number, limits in zip(point, bounds))
        if None in values:
            return None
        checked.append(values)
    return tuple(checked)


def resolve(mode, scene_id=None, step=None):
    """Return detached, finite geometry for an allowed scene and level."""
    if type(mode) not in _TEXT or mode not in DEFAULT_SCENES:
        return None
    if scene_id is None:
        scene_id = DEFAULT_SCENES[mode]
    if type(scene_id) not in _TEXT or SCENE_MODES.get(scene_id) != mode:
        return None
    use_default = step is None
    if use_default:
        step = DEFAULT_STEPS[scene_id]
    checked_step = _finite(step, 0, 4)
    if checked_step is None or checked_step != int(checked_step):
        return None
    step = int(checked_step)
    frames = SCENE_FRAMES.get(scene_id)
    if not isinstance(frames, (tuple, list)) or not 1 <= len(frames) <= 5:
        return None
    by_step = dict((frame.get('step', index), frame) for index, frame in enumerate(frames)
                   if isinstance(frame, dict))
    if not by_step:
        return None
    if step not in by_step and use_default:
        step = min(by_step)
    raw = by_step.get(step)
    if raw is None:
        return None
    marker_scale = _finite(raw.get('marker_scale'), 0.001, 128)
    ellipse, size = raw.get('ellipse'), raw.get('frame_size')
    if (marker_scale is None or not isinstance(ellipse, (tuple, list)) or
            len(ellipse) != 2 or not isinstance(size, (tuple, list)) or len(size) != 2):
        return None
    ellipse = tuple(_finite(number, 0.001, 32768) for number in ellipse)
    size = tuple(_finite(number, 1, 32768) for number in size)
    if None in ellipse or None in size:
        return None
    points = _points(raw['points'], 2) if raw.get('points') is not None else None
    if raw.get('points') is not None and points is None:
        return None
    focus_points = raw.get('focus_points')
    if focus_points is not None:
        if mode != 'arty' or not isinstance(focus_points, (tuple, list)) or len(focus_points) != 3:
            return None
        focus_points = tuple(_points(stage, 3) for stage in focus_points)
        if None in focus_points:
            return None
    if mode == 'arty' and raw.get('calibrated') is not True and points is None:
        # Show an illustrative, larger dispersion area in the position editor.
        factor = 1.60
        if scene_id == 'arty_trajectory':
            # Keep the focus preset while scaling the sample with this view.
            factor *= (0.86, 0.93, 1.0, 1.07, 1.14)[step]
        ellipse = tuple(radius * factor for radius in ellipse)
    zoom = (2, 4, 8, 16, 25)[step] if scene_id == 'sniper' else None
    return {'scene_id': scene_id, 'step': step, 'zoom': zoom,
            'marker_scale': marker_scale, 'ellipse': ellipse, 'points': points,
            'focus_points': focus_points, 'focus_unmeasured': raw.get('focus_unmeasured') is True,
            'frame_size': size, 'calibrated': raw.get('calibrated') is True}
