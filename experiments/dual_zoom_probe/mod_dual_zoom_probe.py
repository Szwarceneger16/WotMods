# -*- coding: ascii -*-
"""Dual Zoom Engine Probe 0.1.0, experimental World of Tanks client mod.

The renderer is opt-in and replay-only by default. No scene is magnified from
the back buffer: a supported native scene-to-texture API is required.
All diagnostics are local and contain API names, not account/game state.
Compatible with the game's Python 2.7 runtime.
"""
from __future__ import absolute_import

import json
import math
import os
import sys

import BigWorld
import GUI
import Keys

TAG = '[DualZoomProbe]'
VERSION = '0.1.0'
FOLDER = 'DualZoomProbe'
SOLID = 'gui/maps/dual_zoom_probe/solid.dds'
MAX_LOG_BYTES = 262144
MAX_CONFIG_BYTES = 8192
ZOOMS = (2.0, 4.0, 8.0, 16.0, 25.0, 32.0)
API_TERMS = ('camera', 'render', 'scene', 'texture', 'projection', 'fov',
             'binocular', 'screen', 'gobo', 'view', 'postprocess')
_CONFIG = None
_SESSION = None
_ORIGINAL = {}
_WRAPPERS = {}
_CONTROL_CLASS = None
_REPORT = {'mod_version': VERSION, 'availability': {}, 'api_names': {},
           'runtime': {}}
_LIVE = False


def _local_dir():
    root = os.environ.get('LOCALAPPDATA')
    if not root or not os.path.isabs(root):
        return None
    return os.path.join(root, FOLDER)


def _log(message):
    line = TAG + ' ' + str(message)[:350]
    try:
        print(line)
    except Exception:
        pass
    directory = _local_dir()
    if directory is None:
        return
    try:
        if not os.path.isdir(directory):
            os.makedirs(directory)
        path = os.path.join(directory, 'diagnostics.log')
        if os.path.exists(path) and os.path.getsize(path) >= MAX_LOG_BYTES:
            return
        with open(path, 'ab') as stream:
            stream.write((line + '\n').encode('ascii', 'replace'))
    except Exception:
        pass


def _save_report():
    directory = _local_dir()
    if directory is None:
        return
    try:
        if not os.path.isdir(directory):
            os.makedirs(directory)
        payload = json.dumps(_REPORT, sort_keys=True, indent=2)
        if len(payload) > 32768:
            raise ValueError('Capability report exceeds size limit')
        with open(os.path.join(directory, 'capabilities.json'), 'wb') as stream:
            stream.write(payload.encode('ascii'))
    except Exception:
        _log('Capability report could not be saved')


def _int_config(value, default, low, high):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return default
    if value != int(value):
        return default
    return max(low, min(high, int(value)))


def _load_config():
    defaults = {'enable_native_renderer': False, 'replay_only': True,
                'width': 400, 'height': 240, 'start_zoom': 2,
                'max_zoom': 25, 'skip_frames': 0, 'staggered': False}
    directory = _local_dir()
    if directory is None:
        return defaults
    path = os.path.join(directory, 'config.json')
    try:
        with open(path, 'rb') as stream:
            raw = stream.read(MAX_CONFIG_BYTES + 1)
        if len(raw) > MAX_CONFIG_BYTES:
            raise ValueError('Configuration file too large')
        supplied = json.loads(raw.decode('utf-8'))
        if not isinstance(supplied, dict):
            raise ValueError('Configuration must be an object')
        for key in ('enable_native_renderer', 'replay_only', 'staggered'):
            if type(supplied.get(key)) is bool:
                defaults[key] = supplied[key]
        defaults['width'] = _int_config(supplied.get('width'), 400, 160, 768)
        defaults['height'] = _int_config(supplied.get('height'), 240, 120, 512)
        defaults['skip_frames'] = _int_config(supplied.get('skip_frames'), 0, 0, 3)
        maximum = supplied.get('max_zoom')
        if maximum in (25, 32) and not isinstance(maximum, bool):
            defaults['max_zoom'] = maximum
        initial = supplied.get('start_zoom')
        if initial in ZOOMS and not isinstance(initial, bool):
            defaults['start_zoom'] = float(initial)
        if defaults['start_zoom'] > defaults['max_zoom']:
            defaults['start_zoom'] = 2.0
        # A tiny render target limits the extra GPU work and memory usage.
        if defaults['width'] * defaults['height'] > 300000:
            defaults['width'], defaults['height'] = 400, 240
    except IOError:
        pass
    except Exception:
        _log('Invalid configuration; safe defaults are used')
    return defaults


def _api_names(obj):
    try:
        return sorted(name for name in dir(obj)
                      if not name.startswith('_')
                      and any(term in name.lower() for term in API_TERMS))[:160]
    except Exception:
        return []


def _inspect_api():
    """Reflect once; do not instantiate renderers or read player state."""
    for name, obj in (('BigWorld', BigWorld), ('GUI', GUI)):
        _REPORT['api_names'][name] = _api_names(obj)
    candidates = {
        'BigWorld.PySceneRenderer': (BigWorld, 'PySceneRenderer'),
        'BigWorld.RenderTarget': (BigWorld, 'RenderTarget'),
        'BigWorld.PyModelRenderer': (BigWorld, 'PyModelRenderer'),
        'BigWorld.FreeCamera': (BigWorld, 'FreeCamera'),
        'BigWorld.camera': (BigWorld, 'camera'),
        'BigWorld.projection': (BigWorld, 'projection'),
        'BigWorld.wg_binoculars': (BigWorld, 'wg_binoculars'),
        'GUI.Simple': (GUI, 'Simple'),
        'GUI.Gobo': (GUI, 'Gobo'),
        'GUI.addRoot': (GUI, 'addRoot'),
        'GUI.delRoot': (GUI, 'delRoot'),
        'GUI.screenResolution': (GUI, 'screenResolution')}
    for label, target in sorted(candidates.items()):
        _REPORT['availability'][label] = callable(getattr(target[0], target[1], None))
    _REPORT['runtime']['python'] = '%d.%d' % sys.version_info[:2]
    _save_report()
    _log('API probe complete; PySceneRenderer=%s, RenderTarget=%s' % (
        _REPORT['availability']['BigWorld.PySceneRenderer'],
        _REPORT['availability']['BigWorld.RenderTarget']))


def _inspect_camera():
    try:
        projection = BigWorld.projection()
        camera = BigWorld.camera()
        _REPORT['api_names']['active_camera'] = _api_names(camera)
        _REPORT['api_names']['projection'] = _api_names(projection)
        _REPORT['runtime']['projection_fov_readable'] = isinstance(
            projection.fov, (int, float))
        _REPORT['runtime']['camera_matrix_readable'] = hasattr(camera, 'matrix')
        # These are the native sniper-camera surfaces found in current EU
        # decompiled control_modes.py / DynamicCameras/SniperCamera.py.
        _REPORT['availability']['SniperCamera.apply_zoom'] = callable(
            getattr(getattr(_SESSION.mode, 'camera', None),
                    '_SniperCamera__applyZoom', None)) if _SESSION is not None else False
        try:
            zooms = getattr(_SESSION.mode.camera, '_cfg', {}).get('zooms', ())
            _REPORT['runtime']['native_sniper_zoom_levels'] = [
                float(value) for value in zooms[:8]]
        except Exception:
            pass
    except Exception as error:
        _REPORT['runtime']['camera_probe_error'] = type(error).__name__
    _save_report()


def _is_replay():
    try:
        import BattleReplay
        return bool(BattleReplay.g_replayCtrl.isPlaying)
    except Exception:
        return False


def _screen_size():
    width, height = GUI.screenResolution()[:2]
    width, height = float(width), float(height)
    if width < 320 or height < 240:
        raise ValueError('Invalid current screen dimensions')
    return width, height


def _inset_fov(main_fov, screen_height, inset_height, zoom):
    """Match the underlying image pixel-for-pixel when inner zoom is x2.

    FOV is assumed vertical. The physical inset is smaller than the viewport,
    so merely setting the renderer to the native full-screen x2 FOV is wrong.
    """
    if not 0.01 < main_fov < 2.8 or screen_height <= 0 or inset_height <= 0:
        raise ValueError('Invalid projection geometry')
    if zoom < 2 or zoom > 32:
        raise ValueError('Unsupported inset zoom')
    extent = math.tan(main_fov * 0.5) * (inset_height / screen_height)
    extent *= 2.0 / float(zoom)
    return 2.0 * math.atan(extent)


def _modifier_down(names):
    for name in names:
        code = getattr(Keys, name, None)
        if code is not None:
            try:
                if BigWorld.isKeyDown(code):
                    return True
            except Exception:
                pass
    return False


def _ctrl_alt():
    return (_modifier_down(('KEY_LCONTROL', 'KEY_RCONTROL'))
            and _modifier_down(('KEY_LALT', 'KEY_RALT')))


class _Session(object):
    def __init__(self, config):
        self.config = config
        self.mode = None
        self.renderer = None
        self.pip = None
        self.borders = []
        self.zoom = float(config['start_zoom'])
        self.started = False
        self.requested = bool(config['enable_native_renderer'])
        self.generation = 0
        self.sync_handle = None
        self.update_handle = None
        self.screen_size = None
        self.previous_native = None

    def _valid_mode(self, generation):
        return (self.mode is not None and self.generation == generation
                and bool(getattr(self.mode, 'isEnabled', False)))

    def enter(self, mode):
        self.leave()
        self.mode = mode
        self.zoom = float(self.config['start_zoom'])
        _inspect_camera()
        _log('Sniper view entered; renderer opt-in=%s replay-only=%s' % (
            self.requested, self.config['replay_only']))
        if self.requested:
            self._schedule_start()

    def _schedule_start(self):
        generation = self.generation
        try:
            BigWorld.callback(0.0, lambda: self._start(generation))
        except Exception as error:
            _REPORT['runtime']['schedule_error'] = type(error).__name__
            _save_report()

    def _set_native_zoom_two(self):
        camera = self.mode.camera
        settings = getattr(camera, '_cfg', None)
        setter = getattr(camera, '_SniperCamera__applyZoom', None)
        if not isinstance(settings, dict) or not callable(setter):
            raise RuntimeError('Native sniper camera zoom interface unavailable')
        available = settings.get('zooms', ())
        if not available or abs(float(available[0]) - 2.0) > 0.001:
            raise RuntimeError('Native sniper x2 base is unavailable')
        previous = (camera, getattr(camera, '_SniperCamera__zoom'), settings['zoom'])
        setattr(camera, '_SniperCamera__zoom', 2.0)
        settings['zoom'] = 2.0
        try:
            setter(2.0)
        except Exception:
            setattr(camera, '_SniperCamera__zoom', previous[1])
            settings['zoom'] = previous[2]
            raise
        return previous

    @staticmethod
    def _restore_native_zoom(previous):
        if previous is None:
            return
        camera, value, setting = previous
        try:
            setattr(camera, '_SniperCamera__zoom', value)
            camera._cfg['zoom'] = setting
            camera._SniperCamera__applyZoom(value)
        except Exception:
            _log('Could not restore zoom after rejected renderer start')

    def _new_gui(self, width, height, x, y, z, colour, texture=None):
        component = GUI.Simple(SOLID)
        component.script = None
        component.focus = False
        component.moveFocus = False
        component.mouseButtonFocus = False
        component.widthMode = GUI.Simple.eSizeMode.PIXEL
        component.heightMode = GUI.Simple.eSizeMode.PIXEL
        component.horizontalPositionMode = GUI.Simple.ePositionMode.CLIP
        component.verticalPositionMode = GUI.Simple.ePositionMode.CLIP
        component.horizontalAnchor = GUI.Simple.eHAnchor.CENTER
        component.verticalAnchor = GUI.Simple.eVAnchor.CENTER
        component.materialFX = GUI.Simple.eMaterialFX.BLEND
        component.filterType = GUI.Simple.eFilterType.LINEAR
        component.size = (float(width), float(height))
        component.position = (float(x), float(y), float(z))
        component.colour = colour
        component.visible = False
        if texture is not None:
            # Only a new world render may be assigned, never a screen crop.
            component.texture = texture
        GUI.addRoot(component)
        return component

    def _layout(self):
        screen_width, screen_height = _screen_size()
        width, height = self.config['width'], self.config['height']
        if self.pip is not None:
            self.pip.size = (width, height)
            self.pip.position = (0.0, 0.0, 0.02)
        if self.borders:
            thick = 2.0
            top = height / screen_height
            side = width / screen_width
            items = ((width, thick, 0.0, top),
                     (width, thick, 0.0, -top),
                     (thick, height, -side, 0.0),
                     (thick, height, side, 0.0))
            for part, shape in zip(self.borders, items):
                part.size = shape[:2]
                part.position = (shape[2], shape[3], 0.01)
        self.screen_size = (screen_width, screen_height)
        if self.renderer is not None:
            self.renderer.fov = _inset_fov(float(BigWorld.projection().fov),
                                            screen_height, height, self.zoom)

    def _start(self, generation):
        if not self._valid_mode(generation) or not self.requested or self.started:
            return
        if self.config['replay_only'] and not _is_replay():
            _log('Native rendering skipped: replay-only safety gate')
            _REPORT['runtime']['native_render'] = 'replay_only'
            _save_report()
            return
        if not (_REPORT['availability'].get('BigWorld.PySceneRenderer')
                and _REPORT['availability'].get('GUI.Simple')
                and _REPORT['availability'].get('GUI.addRoot')):
            _log('Native rendering unavailable; ordinary sniper controls unchanged')
            _REPORT['runtime']['native_render'] = 'missing_api'
            _save_report()
            return
        previous = None
        stage = 'native_camera_x2'
        try:
            previous = self._set_native_zoom_two()
            _screen_size()
            width, height = self.config['width'], self.config['height']
            stage = 'scene_renderer_creation'
            renderer = BigWorld.PySceneRenderer(width, height)
            self.renderer = renderer
            stage = 'scene_camera_attachment'
            renderer.dynamic = 0
            renderer.cameras = [BigWorld.camera()]
            if self.config['skip_frames']:
                renderer.skipFrames = self.config['skip_frames']
            if self.config['staggered']:
                renderer.staggered = 1
            stage = 'independent_scene_projection'
            self._layout()
            if not hasattr(renderer, 'texture'):
                raise RuntimeError('Native scene renderer has no texture output')
            stage = 'gui_texture_attachment'
            self.pip = self._new_gui(width, height, 0, 0, 0.02,
                                     (255, 255, 255, 255), renderer.texture)
            colour = (235, 182, 94, 220)
            stage = 'gui_outline'
            for unused in range(4):
                self.borders.append(self._new_gui(2, 2, 0, 0, 0.01, colour))
            self._layout()
            stage = 'native_dynamic_refresh'
            # Native engine updates its own texture; there is no Python frame loop.
            renderer.dynamic = 1
            self.started = True
            self.previous_native = previous
            self.pip.visible = True
            for component in self.borders:
                component.visible = True
            _REPORT['runtime']['native_render'] = 'started'
            _REPORT['runtime']['native_render_stage'] = stage
            _REPORT['runtime']['render_target_pixels'] = width * height
            _REPORT['runtime']['renderer_properties'] = _api_names(renderer)
            _log('Native scene renderer started at %dx%d, inner zoom x%s' % (
                width, height, self.zoom))
            self._schedule_sync()
        except Exception as error:
            _REPORT['runtime']['native_render'] = 'failed'
            _REPORT['runtime']['native_render_stage'] = stage
            _REPORT['runtime']['native_render_error'] = type(error).__name__
            _log('Native renderer failed at %s: %s' % (stage, type(error).__name__))
            self._release()
            self._restore_native_zoom(previous)
        _save_report()

    def _schedule_sync(self):
        if self.started and self.sync_handle is None:
            generation = self.generation
            self.sync_handle = BigWorld.callback(
                1.0, lambda: self._sync(generation))

    def _sync(self, generation):
        self.sync_handle = None
        if not self.started or not self._valid_mode(generation):
            return
        try:
            if abs(float(getattr(self.mode.camera, '_SniperCamera__zoom')) - 2.0) > 0.001:
                self._set_native_zoom_two()
            if _screen_size() != self.screen_size:
                self._layout()
            self._schedule_sync()
        except Exception as error:
            _log('Renderer synchronization failed: ' + type(error).__name__)
            self._release()

    def _apply_zoom(self, generation):
        self.update_handle = None
        if not self.started or not self._valid_mode(generation):
            return
        try:
            self._layout()
        except Exception as error:
            _log('Zoom update failed; releasing renderer: ' + type(error).__name__)
            self._release()

    def scroll(self, dz):
        if not self.started or dz == 0:
            return False
        steps = [zoom for zoom in ZOOMS if zoom <= self.config['max_zoom']]
        current = min(range(len(steps)), key=lambda index: abs(steps[index] - self.zoom))
        index = min(len(steps) - 1, current + 1) if dz > 0 else max(0, current - 1)
        self.zoom = steps[index]
        if self.update_handle is None:
            generation = self.generation
            self.update_handle = BigWorld.callback(
                0.0, lambda: self._apply_zoom(generation))
        return True

    def _release(self):
        self.started = False
        for name in ('sync_handle', 'update_handle'):
            handle = getattr(self, name)
            setattr(self, name, None)
            if handle is not None:
                try:
                    BigWorld.cancelCallback(handle)
                except Exception:
                    pass
        renderer = self.renderer
        self.renderer = None
        if renderer is not None:
            try:
                renderer.dynamic = 0
            except Exception:
                pass
        previous = self.previous_native
        self.previous_native = None
        self._restore_native_zoom(previous)
        components = ([self.pip] if self.pip is not None else []) + self.borders
        self.pip = None
        self.borders = []
        self.screen_size = None
        for component in components:
            try:
                component.visible = False
            except Exception:
                pass
        if components:
            # GUI root deletion inside an input/lifecycle callback can crash WoT.
            # Detach hidden components on a later engine tick instead.
            def deferred_detach():
                for component in components:
                    try:
                        GUI.delRoot(component)
                    except Exception:
                        pass
            try:
                BigWorld.callback(0.0, deferred_detach)
            except Exception:
                _log('GUI detach deferred callback unavailable; roots hidden')

    def leave(self):
        self.generation += 1
        self.mode = None
        self._release()

    def toggle(self):
        if not self.config['enable_native_renderer']:
            _log('Opt in using config.json before enabling native rendering')
            return
        self.requested = not self.requested
        if self.requested:
            self._schedule_start()
        else:
            self._release()
        _log('Renderer requested=%s' % self.requested)

    def recreate(self):
        if self.started:
            self._release()
            self._schedule_start()


def _install_hooks():
    global _CONTROL_CLASS
    from AvatarInputHandler.control_modes import SniperControlMode
    if _CONTROL_CLASS is not None:
        return
    _CONTROL_CLASS = SniperControlMode
    for name in ('enable', 'disable', 'handleMouseEvent', 'handleKeyEvent',
                 'onRecreateDevice'):
        _ORIGINAL[name] = getattr(SniperControlMode, name)

    def enable(mode, *args, **kwargs):
        result = _ORIGINAL['enable'](mode, *args, **kwargs)
        if _LIVE:
            _SESSION.enter(mode)
        return result

    def disable(mode, *args, **kwargs):
        if _LIVE and _SESSION.mode is mode:
            _SESSION.leave()
        return _ORIGINAL['disable'](mode, *args, **kwargs)

    def mouse(mode, dx, dy, dz):
        if _LIVE and _SESSION.mode is mode and _SESSION.scroll(dz):
            return _ORIGINAL['handleMouseEvent'](mode, dx, dy, 0)
        return _ORIGINAL['handleMouseEvent'](mode, dx, dy, dz)

    def key(mode, isDown, code, mods, event=None):
        if _LIVE and _SESSION.mode is mode and isDown:
            if _ctrl_alt() and code == getattr(Keys, 'KEY_P', None):
                _SESSION.toggle()
                return True
            if _ctrl_alt() and code == getattr(Keys, 'KEY_D', None):
                _inspect_api()
                _inspect_camera()
                _log('Manual capability scan written')
                return True
            if _SESSION.started:
                try:
                    import CommandMapping
                    mapping = CommandMapping.g_instance
                    if mapping.isFired(CommandMapping.CMD_CM_INCREASE_ZOOM, code):
                        return _SESSION.scroll(1)
                    if mapping.isFired(CommandMapping.CMD_CM_DECREASE_ZOOM, code):
                        return _SESSION.scroll(-1)
                except Exception:
                    pass
        return _ORIGINAL['handleKeyEvent'](mode, isDown, code, mods, event)

    def recreate(mode, *args, **kwargs):
        result = _ORIGINAL['onRecreateDevice'](mode, *args, **kwargs)
        if _LIVE and _SESSION.mode is mode:
            _SESSION.recreate()
        return result

    _WRAPPERS.update({'enable': enable, 'disable': disable,
                      'handleMouseEvent': mouse, 'handleKeyEvent': key,
                      'onRecreateDevice': recreate})
    for name, wrapper in _WRAPPERS.items():
        setattr(SniperControlMode, name, wrapper)
    _log('SniperControlMode event hooks installed; no frame polling')


def init():
    global _CONFIG, _SESSION, _LIVE
    if _LIVE:
        return
    _CONFIG = _load_config()
    _SESSION = _Session(_CONFIG)
    _LIVE = True
    _inspect_api()
    try:
        _install_hooks()
    except Exception as error:
        _LIVE = False
        _log('Could not install sniper hooks: ' + type(error).__name__)


def fini():
    global _LIVE, _CONTROL_CLASS
    _LIVE = False
    if _SESSION is not None:
        _SESSION.leave()
    if _CONTROL_CLASS is not None:
        fully_removed = True
        for name, wrapper in _WRAPPERS.items():
            # Do not undo another mod's later wrapper in a shared class.
            if getattr(_CONTROL_CLASS, name, None) is wrapper:
                setattr(_CONTROL_CLASS, name, _ORIGINAL[name])
            else:
                fully_removed = False
        if fully_removed:
            _CONTROL_CLASS = None
            _ORIGINAL.clear()
            _WRAPPERS.clear()
