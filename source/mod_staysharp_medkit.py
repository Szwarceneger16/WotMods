# -*- coding: utf-8 -*-
"""Stay Sharp Medkit Reminder v1.7.1 (WoT EU, CPython 2.7).

One optional HUD-parented GUI.Simple overlay, 21 ARGB DDS animation frames.
This mod does not change battle SWF or WoT's own equipment logic. It keeps
no lifecycle monkeypatches; subscribes to native ComponentEvent lifecycle.
It preserves the working v1.5.0 rendering and detects incompatible HUD
shapes before attempting to paint. Bundled ready voice;
no SWF replacement or downloads.
"""
from __future__ import absolute_import

import errno
import json
import os
import sys
import time
import traceback

import BigWorld
import GUI
import ResMgr
from constants import ARENA_PERIOD

try:
    long
except NameError:
    long = int

TAG = '[StaySharpMedkit]'
VERSION = '1.7.1'
MEDKIT_TAG = 'medkit'
TEXTURE_TEMPLATE = 'gui/maps/staysharp/medkit_pulse_%02d.dds'
FRAME_LEVELS = 20              # frames 0..20, each step is 5% optical intensity
HALF_PULSE = 2.0               # 0%->100% in 2 s, then 100%->0% in 2 s
PULSE_TICK = 0.10              # 10 texture switches/s, never allocate new GUI roots
STATE_TICK = 0.25
STABLE_READY_DELAY = 0.90
READY_VOICE_DELAY = 1.0
READY_VOICE_EVENT = 'staysharp_medkit_ready'
VOICE_LANGUAGES = ('en', 'pl', 'ru', 'fr', 'de', 'es', 'uk')
CONFIG_FILENAME = 'staysharp.medkit.json'
CONFIG_MAX_BYTES = 4096
BORDER_SIZE = 54.0
OFFSET_X = 0.0
OFFSET_Y = 0.0
GUI_DEPTH = 0.005              # position.z used for sorting within root/parent

_panel = None
_overlay = None
_root_registered = False
_overlay_owner = None
_overlay_mount = None
_overlay_active = False
_overlay_geometry = None
_overlay_slot = None
_frame = None
_pulse_start = 0.0
_last_pulse_report = None
_frame_switches = 0
_state_callback = None
_pulse_callback = None
_ready_slot = None
_ready_since = None
_graphics_disabled = False
_error_count = 0
_last_reason = None
_last_panel_active = None
_last_hud_status = None
_last_geometry_source = None
_last_geometry_camera = None
_last_camera_view = None
_last_vehicle_source = None
_event_listeners = []
_event_bus = None
_event_scope = None
_consumables_alias = None
_log_file = None
_audio_key = None
_audio_since = None
_audio_announced = False
_audio_next_reminder = None
_voice_player = None
_voice_disabled = False
_reminder_enabled = True
_key_handler = None
_audio_suspended = True
_language = 'en'
_voice_attempts = 0
_voice_failures = 0


def _language_code(value):
    try:
        string_type = basestring
    except NameError:
        string_type = str
    if not isinstance(value, string_type):
        return None
    return value.strip().lower().replace('_', '-').split('-')[0]


def _game_roots(value, xml=False):
    """Confirm physical installation roots, including native UTF-8 paths."""
    try:
        text_type = unicode
    except NameError:
        text_type = str
    variants = []
    if isinstance(value, text_type):
        variants.append(value)
    elif isinstance(value, bytes):
        for encoding in ('utf-8', sys.getfilesystemencoding() or 'utf-8'):
            try:
                decoded = value.decode(encoding)
                if decoded not in variants:
                    variants.append(decoded)
            except (UnicodeError, LookupError):
                pass
    roots = set()
    for path in variants:
        if not path or '\x00' in path or not os.path.isabs(path):
            continue
        if xml:
            if os.path.basename(path).lower() != 'paths.xml' or not os.path.isfile(path):
                continue
            directories = (os.path.dirname(path),)
        else:
            directories = (path, os.path.dirname(path))
        for root in directories:
            if os.path.isfile(os.path.join(root, 'paths.xml')) and os.path.isdir(os.path.join(root, 'mods')):
                roots.add(os.path.normcase(os.path.realpath(root)))
    return roots


def _config_path():
    """Use mods/configs outside version folders; never guess a game version."""
    try:
        getter = getattr(ResMgr, 'resolveToAbsolutePath', None)
        roots = _game_roots(getter('../paths.xml'), xml=True) if callable(getter) else set()
        if roots:
            return (os.path.join(next(iter(roots)), 'mods', 'configs', CONFIG_FILENAME)
                    if len(roots) == 1 else None)
    except Exception:
        pass
    roots = set()
    try:
        getter = getattr(ResMgr, 'appDirectory', None)
        if callable(getter):
            roots.update(_game_roots(getter()))
    except Exception:
        pass
    try:
        roots.update(_game_roots(getattr(os, 'getcwdu', os.getcwd)()))
    except Exception:
        pass
    return (os.path.join(next(iter(roots)), 'mods', 'configs', CONFIG_FILENAME)
            if len(roots) == 1 else None)


def _load_language():
    """Read a bounded local JSON once at startup; never overwrite user data."""
    global _language
    selected = 'auto'
    path = _config_path()
    if path is not None:
        folder = os.path.dirname(path)
        try:
            try:
                with open(path, 'rb') as handle:
                    raw = handle.read(CONFIG_MAX_BYTES + 1)
            except IOError as error:
                if error.errno != errno.ENOENT:
                    raise
                if not os.path.isdir(folder):
                    try:
                        os.makedirs(folder)
                    except OSError:
                        if not os.path.isdir(folder):
                            raise
                # Exclusive creation protects an existing config in a race.
                try:
                    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                except OSError as error:
                    if error.errno != errno.EEXIST:
                        raise
                else:
                    with os.fdopen(fd, 'wb') as handle:
                        handle.write(b'{\n  "language": "auto"\n}\n')
                with open(path, 'rb') as handle:
                    raw = handle.read(CONFIG_MAX_BYTES + 1)
            if len(raw) > CONFIG_MAX_BYTES:
                raise ValueError('configuration exceeds size limit')
            config = json.loads(raw.decode('utf-8-sig'))
            if not isinstance(config, dict):
                raise ValueError('configuration must be a JSON object')
            value = _language_code(config.get('language', 'auto'))
            if value not in VOICE_LANGUAGES + ('auto',):
                raise ValueError('unsupported voice language')
            selected = value
        except Exception:
            # Do not echo file contents or a private filesystem path.
            _log('invalid or unreadable configuration; using automatic language')
    if selected == 'auto':
        try:
            from helpers import getClientLanguage
            selected = _language_code(getClientLanguage())
        except Exception:
            selected = None
    _language = selected if selected in VOICE_LANGUAGES else 'en'
    _log('ready voice language=' + _language)


def _ready_voice_event():
    return READY_VOICE_EVENT if _language == 'en' else READY_VOICE_EVENT + '_' + _language


def _audio_diagnostics():
    """Inspect resolved resources, without claiming a bank is loaded or audible."""
    try:
        present = bool(ResMgr.isFile('audioww/staysharp_medkit.bnk'))
        _log('audio resource bank_visible=%s' % present)
    except Exception:
        _exception('audio resource bank_visibility=unknown')
    try:
        root = ResMgr.openSection('audioww/audio_mods.xml')
        if root is None:
            _log('audio config resolved=missing bank_entry=unknown')
            return
        banks = root['loadBanks']
        if banks is None:
            _log('audio config resolved=yes loadBanks=missing bank_entry=no')
            return
        # Do not log other mods' names or dump the shared XML.
        found = False
        count = 0
        truncated = False
        for section in banks.values():
            if count >= 128:
                truncated = True
                break
            count += 1
            name = section.asString
            if not name or not name.strip():
                child = section['name']
                name = child.asString if child is not None else ''
            if name.strip().lower() == 'staysharp_medkit.bnk':
                found = True
                break
        state = 'yes' if found else ('unknown' if truncated else 'no')
        _log('audio config resolved=yes bank_entry=%s scan_limited=%s' % (state, truncated))
    except Exception:
        _exception('audio config resolved=unknown bank_entry=unknown')


def _suspend_audio():
    """Stop current audio, retaining the one-announcement-per-ready latch."""
    global _audio_next_reminder, _audio_suspended
    _audio_next_reminder = None
    if _audio_suspended:
        return
    _audio_suspended = True
    if _voice_player is not None:
        try:
            _voice_player.stop()
            _log('audio voice stop requested')
        except Exception:
            _exception('voice stop failed')


def _reset_audio():
    global _audio_key, _audio_since, _audio_announced
    _suspend_audio()
    _audio_key = None
    _audio_since = None
    _audio_announced = False


def _track_audio_ready(panel, slot):
    """Track actual readiness even while the player temporarily hides HUD."""
    global _audio_key, _audio_since
    key = (slot, panel._cds[slot]) if slot is not None else None
    if key != _audio_key:
        _reset_audio()
        _audio_key = key
        if key is not None:
            _audio_since = _time()
            _log('audio readiness=ready slot=%d voice_delay=%.2fs' % (slot, READY_VOICE_DELAY))
        else:
            _log('audio readiness=not_ready')


def _play_ready_voice():
    global _voice_player, _voice_disabled, _voice_attempts, _voice_failures
    if _voice_disabled:
        return
    _voice_attempts += 1
    report = _voice_attempts <= 3 or _voice_attempts % 10 == 0
    try:
        if _voice_player is None:
            import SoundGroups
            _log('audio create event=' + _ready_voice_event())
            _voice_player = SoundGroups.g_instance.getSound2D(_ready_voice_event())
            _log('audio handle present=%s' % (_voice_player is not None))
        result = _voice_player.play()
        result_label = 'none' if result is None else ('truthy' if result else 'false')
        if report:
            playing = 'unknown'
            try:
                state = getattr(_voice_player, 'isPlaying', None)
                if isinstance(state, bool):
                    playing = str(state)
            except Exception:
                pass
            _log('audio play attempt=%d result=%s isPlaying=%s audible=unknown' % (
                _voice_attempts, result_label, playing))
        if result is not None and not result:
            raise RuntimeError('ready voice playback failed')
    except Exception:
        _voice_failures += 1
        _voice_disabled = True
        _exception('ready voice unavailable; audio disabled for battle')


def _update_audio():
    """Run on the existing state tick; no extra callbacks or catch-up bursts."""
    global _audio_announced, _audio_next_reminder, _audio_suspended
    if not _overlay_active or _audio_key is None:
        _suspend_audio()
        return
    now = _time()
    if now - _audio_since < READY_VOICE_DELAY:
        return
    _audio_suspended = False
    if not _audio_announced:
        _audio_announced = True
        _play_ready_voice()
        _audio_next_reminder = now + 2.0 * HALF_PULSE
    elif _audio_next_reminder is None:
        # Resume at the next complete pulse without repeating the voice.
        _audio_next_reminder = now + 2.0 * HALF_PULSE
    elif now >= _audio_next_reminder:
        _audio_next_reminder = now + 2.0 * HALF_PULSE
        _play_ready_voice()


def _log(message):
    global _log_file
    message = str(message)
    try:
        print(TAG + ' ' + message)
    except Exception:
        pass
    try:
        if _log_file is None:
            base = os.environ.get('LOCALAPPDATA') or os.environ.get('APPDATA')
            if not base:
                return
            folder = os.path.join(base, 'StaySharpMedkit')
            if not os.path.isdir(folder):
                os.makedirs(folder)
            _log_file = os.path.join(folder, 'staysharp.log')
        # Windows os.rename() cannot overwrite an existing backup. Check the
        # size on every write, not only at startup: a long battle can generate
        # enough pulse diagnostics to exceed the configured log budget.
        if os.path.isfile(_log_file) and os.path.getsize(_log_file) > 524288:
            backup = _log_file + '.old'
            try:
                if os.path.exists(backup):
                    os.remove(backup)
                os.rename(_log_file, backup)
            except OSError:
                # Preserve the size bound if an external process has locked
                # the backup or an antivirus interfered with rotation. Losing
                # older diagnostics is preferable to unbounded disk growth.
                try:
                    with open(_log_file, 'wb'):
                        pass
                except OSError:
                    return
        with open(_log_file, 'ab') as output:
            output.write(('%s %s %s\n' % (time.strftime('%Y-%m-%d %H:%M:%S'), TAG, message)).encode('ascii', 'replace'))
            output.flush()
    except Exception:
        pass


def _exception(message):
    _log(message)
    exc_type, unused_value, tb = sys.exc_info()
    frames = traceback.extract_tb(tb)[-8:] if tb is not None else []
    locations = ' > '.join('%s:%s:%s' % (os.path.basename(path), line, name)
                           for path, line, name, unused_source in frames)
    _log('exception=%s frames=%s' % (getattr(exc_type, '__name__', 'unknown'), locations))


def _time():
    return float(BigWorld.time())


def _texture(level):
    return TEXTURE_TEMPLATE % level


def _cancel_state():
    global _state_callback
    if _state_callback is not None:
        job = _state_callback
        _state_callback = None
        try:
            BigWorld.cancelCallback(job)
        except Exception:
            _exception('state cancellation failed')


def _cancel_pulse():
    global _pulse_callback
    if _pulse_callback is not None:
        job = _pulse_callback
        _pulse_callback = None
        try:
            BigWorld.cancelCallback(job)
        except Exception:
            _exception('pulse cancellation failed')


def _schedule_state():
    global _state_callback
    if _panel is not None and _state_callback is None and not _graphics_disabled:
        _state_callback = BigWorld.callback(STATE_TICK, _check_state)


def _schedule_pulse():
    global _pulse_callback
    if _panel is not None and _overlay_active and _pulse_callback is None:
        _pulse_callback = BigWorld.callback(PULSE_TICK, _animate)


def _panel_contract(panel):
    """Validate only the HUD layout relied on by the v1.5 renderer.

    Refuse to draw on unknown client layouts rather than approximating a
    rectangle that could land elsewhere or indicate the wrong consumable.
    The check is intentionally inexpensive and repeatable after HUD changes.
    """
    if panel is None:
        return (False, 'no_panel')
    required = (
        ('_PANEL_MAX_LENGTH', 12),
        ('_AMMO_START_IDX', 0), ('_AMMO_END_IDX', 2),
        ('_EQUIPMENT_START_IDX', 3), ('_EQUIPMENT_END_IDX', 5),
        ('_ORDERS_START_IDX', 6), ('_ORDERS_END_IDX', 8),
        ('_OPT_DEVICE_START_IDX', 9), ('_OPT_DEVICE_END_IDX', 11))
    try:
        for name, wanted in required:
            if getattr(panel, name, None) != wanted:
                return (False, 'changed_panel_layout_' + name)
        settings_getter = getattr(panel, '_getPanelSettings', None)
        if not callable(settings_getter):
            return (False, 'missing_panel_settings_api')
        # This fallback's spacing is correct only for default battle HUD.
        if settings_getter() != 0:
            return (False, 'unsupported_panel_settings')
        if not callable(getattr(panel, 'as_isVisibleS', None)):
            return (False, 'missing_panel_visibility_api')
        cds = getattr(panel, '_cds', None)
        if not isinstance(cds, (list, tuple)) or len(cds) != 12:
            return (False, 'unexpected_panel_cds')
        mask = getattr(panel, '_mask', None)
        if not isinstance(mask, (int, long)):
            return (False, 'invalid_panel_mask_type')
        if mask < 0 or mask >= (1 << 12):
            return (False, 'invalid_panel_mask_bits')
        glow_callbacks = getattr(panel, '_equipmentsGlowCallbacks', None)
        if not isinstance(glow_callbacks, dict):
            return (False, 'missing_native_glow_tracking')
    except Exception:
        return (False, 'panel_contract_check_failed')
    return (True, 'compatible_default_battle_panel')


def _slot_contract(panel, slot, compact=None):
    """Stop if a client update changes the meaning or placement of slots."""
    valid, reason = _panel_contract(panel)
    if not valid:
        return (False, reason)
    try:
        if slot not in (3, 4, 5):
            return (False, 'medkit_outside_equipment_slots')
        cds, mask = panel._cds, panel._mask
        if not mask & (1 << slot) or cds[slot] is None:
            return (False, 'medkit_slot_not_rendered')
        if compact is not None and cds[slot] != compact:
            return (False, 'medkit_slot_compact_changed')
        # The known Flash drawLayout iterates exactly these bitmasked indices.
        indices = [i for i in range(12)
                   if mask & (1 << i) and cds[i] is not None]
        if not (4 <= len(indices) <= 12):
            return (False, 'panel_layout_not_ready')
    except Exception:
        return (False, 'slot_contract_check_failed')
    return (True, 'known_slot_layout')


def _graphics_contract():
    """Probe enum and resource *interfaces* before calling native GUI.Simple."""
    try:
        if not callable(getattr(GUI, 'screenResolution', None)):
            return (False, 'missing_GUI_screenResolution')
        cls = getattr(GUI, 'Simple', None)
        if not callable(cls):
            return (False, 'missing_GUI_Simple')
        for enum_class, field in (
            ('eSizeMode', 'PIXEL'), ('ePositionMode', 'CLIP'),
            ('eHAnchor', 'CENTER'), ('eVAnchor', 'CENTER'),
            ('eMaterialFX', 'BLEND'), ('eFilterType', 'LINEAR')):
            enum = getattr(cls, enum_class, None)
            if enum is None or getattr(enum, field, None) is None:
                return (False, 'unsupported_GUI_enum_' + enum_class)
        if not callable(getattr(ResMgr, 'isFile', None)):
            return (False, 'missing_ResMgr_isFile')
        for name in ('player', 'entity', 'time', 'callback', 'cancelCallback'):
            if not callable(getattr(BigWorld, name, None)):
                return (False, 'missing_BigWorld_' + name)
    except Exception:
        return (False, 'graphics_contract_check_failed')
    return (True, 'supported_GUI_interfaces')


def _resolve_player_vehicle(panel, avatar):
    """Use game entity by stable playerVehicleID, NOT avatar.vehicle.

    WoT may clear/change avatar.vehicle while the camera is in strategic/arty
    mode. The equipment controller continues to operate on the same tank.
    Avoid using the camera mode as a proxy for whether that tank exists.
    """
    session = getattr(panel, 'sessionProvider', None)
    shared = getattr(session, 'shared', None)
    vehicle_state = getattr(shared, 'vehicleState', None)
    vehicle_id = getattr(avatar, 'playerVehicleID', None)
    if vehicle_id:
        getter_id = getattr(vehicle_state, 'getControllingVehicleID', None)
        if callable(getter_id):
            try:
                controlling = getter_id()
            except Exception:
                controlling = None
            if controlling and controlling != vehicle_id:
                return (None, 'controlling_vehicle_not_player')

        # BigWorld.entity(id) is the mechanism used by the native equipment
        # controller when an explicit player avatar is passed.
        get_entity = getattr(BigWorld, 'entity', None)
        if callable(get_entity):
            try:
                vehicle = get_entity(vehicle_id)
            except Exception:
                vehicle = None
            if vehicle is not None:
                return (vehicle, 'playerVehicleID_entity')

        get_controlling = getattr(vehicle_state, 'getControllingVehicle', None)
        if callable(get_controlling):
            try:
                vehicle = get_controlling()
            except Exception:
                vehicle = None
            if vehicle is not None and getattr(vehicle, 'id', vehicle_id) == vehicle_id:
                return (vehicle, 'vehicle_state_controller')

    # Last resort for older clients and during normal arcade camera modes.
    # Never treat avatar.vehicle=None as proof of destruction.
    vehicle = getattr(avatar, 'vehicle', None)
    if vehicle is not None and (not vehicle_id or getattr(vehicle, 'id', vehicle_id) == vehicle_id):
        return (vehicle, 'avatar_vehicle_fallback')
    return (None, 'vehicle_entity_unavailable')


def _probe_medkit(panel):
    """Return ready slot and reason. Check the *real* player tank, not camera.

    The equipment is ready only if the game reports it usable and explicitly
    permits activation via the server-provided perkEffects['equipment'].
    """
    global _last_vehicle_source
    session = getattr(panel, 'sessionProvider', None)
    if session is None:
        return (None, 'no_session')
    if session.isReplayPlaying:
        return (None, 'replay')
    player = BigWorld.player()
    if player is None or player.isObserver():
        return (None, 'observer_or_no_player')

    # isVehicleAlive is maintained by WoT separately from the camera entity.
    # If unavailable in old clients, vehicle.health remains the safeguard.
    if not bool(getattr(player, 'isVehicleAlive', True)):
        return (None, 'own_vehicle_destroyed')

    vehicle, origin = _resolve_player_vehicle(panel, player)
    if origin != _last_vehicle_source:
        _last_vehicle_source = origin
        _log('own vehicle source=' + origin)
    if vehicle is None:
        return (None, origin)
    if getattr(vehicle, 'health', 0) <= 0:
        return (None, 'own_vehicle_destroyed')
    effects = getattr(vehicle, 'perkEffects', None)
    if not effects:
        return (None, 'no_perk_effects')
    try:
        enabled = effects['equipment']
    except (KeyError, IndexError, TypeError):
        return (None, 'no_equipment_perk')
    if not enabled:
        return (None, 'equipment_perk_inactive')

    shared = getattr(session, 'shared', None)
    controller = getattr(shared, 'equipments', None)
    valid, panel_reason = _panel_contract(panel)
    if not valid:
        return (None, 'incompatible_hud_' + panel_reason)
    slots = panel._cds
    if controller is None:
        return (None, 'equipment_panel_initialising')
    if not callable(getattr(controller, 'iterEquipmentsByTag', None)):
        return (None, 'missing_equipment_iterator')

    had_medkit = False
    for compact, item in controller.iterEquipmentsByTag(MEDKIT_TAG):
        if item is None:
            continue
        had_medkit = True
        if not item.isAvailableToUse:
            continue
        descriptor = item.getDescriptor()
        if descriptor is None or descriptor.name not in enabled:
            continue
        # Native _MedKitItem._canActivate uses avatar.vehicle when avatar
        # is omitted. Explicit avatar selects BigWorld.entity(playerVehicleID)
        # in sniper/strategic/arty modes and prevents the camera-only bug.
        if not item.canActivate(avatar=player)[0]:
            continue
        try:
            slot = slots.index(compact)
        except ValueError:
            continue
        valid, slot_reason = _slot_contract(panel, slot, compact)
        if not valid:
            return (None, 'incompatible_hud_' + slot_reason)
        # The game's injury/stun warning must always have priority.
        if slot in getattr(panel, '_equipmentsGlowCallbacks', {}):
            return (None, 'vanilla_equipment_glow_priority')
        return (slot, 'ready')
    return (None, 'medkit_unavailable' if had_medkit else 'medkit_not_equipped')

def _hud_visibility(panel):
    """Fail closed: show the overlay only if the real battle bar is visible.

    The pre-battle equipment selection is a DIFFERENT Flash component.  WoT
    hides the real consumablesPanel while that selection is displayed.
    panel.isActive is only a notification cache, not an authoritative test.
    """
    player = BigWorld.player()
    arena = getattr(player, 'arena', None)
    period = getattr(arena, 'period', None)
    if period is None:
        visitor = getattr(getattr(panel, 'sessionProvider', None), 'arenaVisitor', None)
        getter = getattr(visitor, 'getArenaPeriod', None)
        if callable(getter):
            try:
                period = getter()
            except Exception:
                return (False, 'arena_period_unavailable')
    if period != ARENA_PERIOD.BATTLE:
        return (False, 'not_in_battle_period_%s' % str(period))

    # Native read-only Flash bridge, as_isVisibleS -> as_isVisible() -> visible.
    # This reflects the actual consumables panel, not the prebattle selector.
    getter = getattr(panel, 'as_isVisibleS', None)
    if not callable(getter):
        return (False, 'no_native_panel_visibility_api')
    try:
        actual_visible = getter()
    except Exception:
        return (False, 'native_panel_visibility_query_failed')
    if actual_visible not in (True, 1):
        return (False, 'native_panel_hidden')
    return (True, 'hud_visible')


def _camera_view(panel):
    try:
        crosshair = panel.sessionProvider.shared.crosshair
        return crosshair.getViewID() if crosshair is not None else None
    except Exception:
        return None


def _interface_scale(panel):
    try:
        option = panel.app.settingsCore.interfaceScale
        scale = float(option.getScaleByIndex(option.get()))
        if 0.5 <= scale <= 3.0:
            return scale
    except Exception:
        pass
    return 1.0


def _native_geometry(panel, slot, width, height, scale):
    """Try one *stage-space* Flash rectangle; never add local coordinates.

    The previous version used panel.x + renderer.x. Both coordinates can be
    relative to different Flash parents, so that calculation was invalid.
    In ordinary WoT clients Python often cannot invoke the renderer getter:
    fallback is then modeled using the confirmed WoT drawLayout algorithm.
    """
    try:
        flash = panel.flashObject
        if flash is None:
            return (None, 'flash_not_created')
        accessor = getattr(flash, 'getRendererBySlotIdx', None)
        if not callable(accessor):
            return (None, 'renderer_accessor_unavailable')
        renderer = accessor(slot)
        if renderer is None:
            return (None, 'renderer_unavailable')
        if getattr(renderer, 'visible', True) is False:
            return (None, 'renderer_hidden')
        bounds_fn = getattr(renderer, 'getBounds', None)
        stage = getattr(renderer, 'stage', None)
        if not callable(bounds_fn) or stage is None:
            return (None, 'renderer_stage_bounds_unavailable')
        bounds = bounds_fn(stage)
        if bounds is None:
            return (None, 'renderer_bounds_unavailable')
        x, y = float(bounds.x), float(bounds.y)
        w, h = float(bounds.width), float(bounds.height)
        stage_width, stage_height = width / scale, height / scale
        if not (15.0 <= w <= 160.0 and 15.0 <= h <= 160.0):
            return (None, 'renderer_bounds_size_invalid')
        if not (0.0 <= x < stage_width and 0.0 <= y < stage_height):
            return (None, 'renderer_bounds_outside_stage')
        center_x = (x + 0.5 * w) * scale
        center_y = (y + 0.5 * h) * scale
        if not (0.0 <= center_x <= width and 0.0 <= center_y <= height):
            return (None, 'renderer_center_outside_screen')
        size = BORDER_SIZE * scale * min(w / 54.0, h / 54.0)
        if not (20.0 <= size <= 240.0):
            return (None, 'renderer_border_size_invalid')
        return ((2.0 * center_x / width - 1.0,
                 1.0 - 2.0 * center_y / height, size), 'flash_stage_bounds')
    except Exception:
        return (None, 'renderer_stage_read_failed')

def _geometry(panel, slot):
    """Position native GUI in screen clip-space above actual WoT HUD.

    Full Flash stage-space geometry is preferred. Native Python Flash bridge
    exposes as_* functions but often NOT getRendererBySlotIdx. In that case
    calculate using the original WoT ConsumablesPanel.drawLayout rules:
      - one renderer per occupied panel index (including empty equipment slots),
      - 49/57 pixels of item padding based on Flash-stage width,
      - the whole bar centered horizontally,
      - positioned 58 px from bottom.

    Do not use flashObject.x/y as absolute coordinates: they are local Flash
    coordinates and caused the misplaced overlay in 1.4.0.
    """
    valid, reason = _slot_contract(panel, slot)
    if not valid:
        return (None, 'incompatible_hud_' + reason)
    width, height = GUI.screenResolution()[:2]
    width, height = float(width), float(height)
    if width < 600.0 or height < 400.0:
        return (None, 'invalid_resolution')
    scale = _interface_scale(panel)
    native, native_origin = _native_geometry(panel, slot, width, height, scale)
    if native is not None:
        return (native, native_origin)
    if native_origin == 'renderer_hidden':
        return (None, 'renderer_hidden')

    slots = getattr(panel, '_cds', ())
    mask = getattr(panel, '_mask', 0)
    indices = [i for i in range(min(12, len(slots)))
               if mask & (1 << i) and slots[i] is not None]
    if slot not in indices or len(indices) < 4 or len(indices) > 12:
        return (None, 'panel_layout_not_ready')
    stage_width = width / scale
    stage_height = height / scale
    spacing = 49.0 if stage_width < 1280.0 else 57.0
    # ConsumablesPanel._getPanelSettings() for the regular battle uses
    # DEFAULT_SETTINGS_ID, where customIndexGap is empty and groupGap=0.
    total_width = len(indices) * spacing
    left = 0.5 * (stage_width - total_width)
    top = stage_height - 58.0
    position = indices.index(slot)
    center_x = (left + position * spacing + BORDER_SIZE * 0.5 + OFFSET_X) * scale
    center_y = (top + BORDER_SIZE * 0.5 + OFFSET_Y) * scale
    if not (0 <= center_x <= width and 0 <= center_y <= height):
        return (None, 'modeled_outside_screen')
    return ((2.0 * center_x / width - 1.0,
             1.0 - 2.0 * center_y / height,
             BORDER_SIZE * scale), 'centered_layout_' + native_origin)

def _set_frame(level):
    """Update a single component's texture; no shader/colour writes per tick.

    At zero the native component is really invisible, not just tinted black.
    Hence even a client ignoring alpha tint cannot show a permanent outline.
    """
    global _frame, _frame_switches
    if _overlay is None:
        return
    level = max(0, min(FRAME_LEVELS, int(level)))
    if level == _frame:
        return
    if level == 0:
        _overlay.visible = False
    else:
        _overlay.textureName = _texture(level)
        _overlay.visible = True
        _frame_switches += 1
    _frame = level


def _hide_overlay(reason='not_ready'):
    global _overlay_active, _frame
    _suspend_audio()
    _cancel_pulse()
    if not _overlay_active:
        return
    _overlay_active = False
    if _overlay is not None:
        _overlay.visible = False
    _frame = None
    _log('overlay suspended: ' + reason + '; GUI root kept')


def _delete_overlay():
    global _overlay, _root_registered, _overlay_owner, _overlay_mount
    global _overlay_geometry, _overlay_slot, _overlay_active, _frame
    _cancel_pulse()
    component, owner, mount = _overlay, _overlay_owner, _overlay_mount
    _overlay = None
    _root_registered = False
    _overlay_owner = None
    _overlay_mount = None
    _overlay_geometry = None
    _overlay_slot = None
    _overlay_active = False
    _frame = None
    if component is None or not mount:
        return
    try:
        # Do not leave a visible native child if detachment itself fails.
        component.visible = False
    except Exception:
        pass
    try:
        if mount == 'hud_child':
            _log('GFX BEFORE HUD.delChild')
            owner.delChild(component)
            _log('GFX AFTER HUD.delChild')
        elif mount == 'gui_root':
            _log('GFX BEFORE GUI.delRoot')
            GUI.delRoot(component)
            _log('GFX AFTER GUI.delRoot')
    except Exception:
        _exception('GFX cleanup failed for ' + str(mount))

def _preflight_frames():
    for i in range(FRAME_LEVELS + 1):
        if not ResMgr.isFile(_texture(i)):
            _log('GFX disabled: missing texture ' + _texture(i))
            return False
    return True


def _allocate_overlay(panel, geometry, slot):
    global _overlay, _root_registered, _overlay_owner, _overlay_mount
    global _overlay_geometry, _overlay_slot, _graphics_disabled
    if _graphics_disabled:
        return False
    compatible, reason = _graphics_contract()
    if not compatible:
        _log('GFX disabled by compatibility preflight: ' + reason)
        _graphics_disabled = True
        return False
    try:
        if not _preflight_frames():
            _graphics_disabled = True
            return False
    except Exception:
        _graphics_disabled = True
        _exception('GFX resource preflight error')
        return False

    component, owner, mount = None, None, None
    phase = 'GUI.Simple'
    try:
        _log('GFX BEFORE GUI.Simple(' + _texture(0) + ')')
        component = GUI.Simple(_texture(0))
        _log('GFX AFTER GUI.Simple')
        phase = 'GUI properties'
        component.widthMode = GUI.Simple.eSizeMode.PIXEL
        component.heightMode = GUI.Simple.eSizeMode.PIXEL
        component.horizontalPositionMode = GUI.Simple.ePositionMode.CLIP
        component.verticalPositionMode = GUI.Simple.ePositionMode.CLIP
        component.horizontalAnchor = GUI.Simple.eHAnchor.CENTER
        component.verticalAnchor = GUI.Simple.eVAnchor.CENTER
        component.materialFX = GUI.Simple.eMaterialFX.BLEND
        component.filterType = GUI.Simple.eFilterType.LINEAR
        component.focus = False
        component.mouseButtonFocus = False
        component.moveFocus = False
        component.visible = False
        component.colour = (255, 255, 255, 255)
        component.size = (geometry[2], geometry[2])
        component.position = (geometry[0], geometry[1], GUI_DEPTH)

        # Prefer the native Flash GUI app (which owns the actual battle HUD)
        # rather than an unrelated root. This is parent-child *rendering*,
        # NOT an unsupported ActionScript MovieClip mutation.
        app = getattr(panel, 'app', None)
        hud = getattr(app, 'component', None)
        if hud is not None and callable(getattr(hud, 'addChild', None)) and \
                callable(getattr(hud, 'delChild', None)):
            phase = 'HUD.addChild'
            _log('GFX BEFORE HUD.addChild')
            # Record owner/mount before calling native code, so an exception
            # after partial attachment can still be cleaned up safely.
            owner = hud
            mount = 'hud_child'
            hud.addChild(component, 'staysharp_medkit_overlay')
            _log('GFX AFTER HUD.addChild')
        else:
            # Legacy clients / test environments without a Flash GUI
            # component retain the previously verified GUI.addRoot route.
            phase = 'GUI.addRoot'
            _log('GFX BEFORE GUI.addRoot (no HUD parent available)')
            GUI.addRoot(component)
            mount = 'gui_root'
            _log('GFX AFTER GUI.addRoot')
        _overlay = component
        _root_registered = (mount == 'gui_root')
        _overlay_owner = owner
        _overlay_mount = mount
        _overlay_geometry = geometry
        _overlay_slot = slot
        _log('overlay mounted: %s' % mount)
        return True
    except Exception:
        _graphics_disabled = True
        _exception('GFX disabled during ' + phase)
        # If addChild raised AFTER partially inserting the component, never
        # attach that same component to a different GUI root.
        if mount == 'hud_child' and owner is not None:
            try:
                owner.delChild(component)
            except Exception:
                pass
        elif mount == 'gui_root':
            try:
                GUI.delRoot(component)
            except Exception:
                pass
        return False

def _show_overlay(slot, geometry):
    global _overlay_active, _overlay_slot, _overlay_geometry, _pulse_start
    global _frame, _last_pulse_report, _frame_switches, _graphics_disabled
    if _graphics_disabled:
        return
    if _overlay is None and not _allocate_overlay(_panel, geometry, slot):
        return
    try:
        if geometry != _overlay_geometry:
            _overlay.position = (geometry[0], geometry[1], GUI_DEPTH)
            _overlay.size = (geometry[2], geometry[2])
            _overlay_geometry = geometry
        _overlay_slot = slot
        if not _overlay_active:
            _overlay_active = True
            _pulse_start = _time()
            _frame = None
            _frame_switches = 0
            _last_pulse_report = _time()
            _set_frame(0)
            _log('overlay ACTIVE slot=%d, mount=%s, frames 0..%d; depth=%.3f' % (slot, _overlay_mount, FRAME_LEVELS, GUI_DEPTH))
            _schedule_pulse()
    except Exception:
        _graphics_disabled = True
        _exception('GFX overlay display error')
        try:
            _hide_overlay('graphics_failure')
        except Exception:
            pass


def _animate():
    global _pulse_callback, _last_pulse_report, _graphics_disabled
    _pulse_callback = None
    if _panel is None or _overlay is None or not _overlay_active:
        return
    try:
        t = (_time() - _pulse_start) % (2.0 * HALF_PULSE)
        strength = t / HALF_PULSE if t <= HALF_PULSE else (2.0 * HALF_PULSE - t) / HALF_PULSE
        level = int(strength * FRAME_LEVELS + 0.5)
        _set_frame(level)
        # Low-frequency diagnostic proves that the callback is running.
        if _last_pulse_report is not None and _time() - _last_pulse_report >= 8.0:
            _last_pulse_report = _time()
            _log('PULSE alive frame=%d switches=%d GUI.visible=%s mount=%s parent.visible=%s panel.isActive=%s' % (
                level, _frame_switches, str(_overlay.visible), str(_overlay_mount),
                str(getattr(_overlay_owner, 'visible', None)),
                str(getattr(_panel, 'isActive', None))))
    except Exception:
        _graphics_disabled = True
        _exception('GFX texture animation failed; disabled for battle')
        try:
            _hide_overlay('graphics_failure')
        except Exception:
            pass
        return
    _schedule_pulse()


def _refresh(panel):
    global _ready_slot, _ready_since, _last_reason, _last_panel_active
    global _last_hud_status, _last_geometry_source, _last_geometry_camera, _last_camera_view
    if not _reminder_enabled:
        _hide_overlay('disabled_by_player')
        return
    panel_active = getattr(panel, 'isActive', None)
    camera = _camera_view(panel)
    if camera != _last_camera_view:
        _last_camera_view = camera
        _log('crosshair view=%s (1=arcade 2=sniper 3=strategic)' % str(camera))
    if panel_active != _last_panel_active:
        _last_panel_active = panel_active
        _log('panel.isActive=%s (diagnostic only)' % str(panel_active))

    shown, hud_reason = _hud_visibility(panel)
    if hud_reason != _last_hud_status:
        _last_hud_status = hud_reason
        _log('native HUD visibility=' + hud_reason)
    if not shown:
        if hud_reason == 'native_panel_hidden':
            slot, _ = _probe_medkit(panel)
            _track_audio_ready(panel, slot)
        else:
            _reset_audio()
        _ready_slot, _ready_since = None, None
        _hide_overlay(hud_reason)
        return

    slot, reason = _probe_medkit(panel)
    _track_audio_ready(panel, slot)
    if reason != _last_reason:
        _last_reason = reason
        _log('equipment state=' + reason + (' slot=%d' % slot if slot is not None else ''))
    if slot is None:
        _ready_slot, _ready_since = None, None
        _hide_overlay(reason)
        return
    if slot != _ready_slot:
        _ready_slot, _ready_since = slot, _time()
        _hide_overlay('slot_changed')
        return
    if _time() - _ready_since < STABLE_READY_DELAY:
        return

    geometry, origin = _geometry(panel, slot)
    if origin != _last_geometry_source or camera != _last_geometry_camera:
        _last_geometry_source = origin
        _last_geometry_camera = camera
        _log('HUD geometry=%s camera=%s coordinates=%s' % (
            origin, str(camera), str(geometry)))
    if geometry is None:
        _hide_overlay('panel_geometry_unavailable_' + origin)
        return
    _show_overlay(slot, geometry)
    _update_audio()

def _check_state():
    global _state_callback, _error_count, _graphics_disabled
    _state_callback = None
    if _panel is None:
        return
    try:
        _refresh(_panel)
        _error_count = 0
    except Exception:
        _error_count += 1
        _exception('state exception attempt=%d' % _error_count)
        try:
            _hide_overlay('state_exception')
        except Exception:
            pass
        if _error_count >= 3:
            _graphics_disabled = True
            _log('mod suspended for battle after three exceptions')
            return
    try:
        _schedule_state()
    except Exception:
        _exception('state scheduler failed')


def _on_key_down(event):
    global _reminder_enabled
    if _panel is None:
        return
    try:
        import Keys
        if (event.key != Keys.KEY_M or not event.isKeyDown()
                or event.isRepeatedEvent() or not event.isCtrlDown()
                or not event.isAltDown() or event.isShiftDown()):
            return
        from messenger import MessengerEntry
        if MessengerEntry.g_instance.gui.isFocused():
            return
        _reminder_enabled = not _reminder_enabled
        if not _reminder_enabled:
            _reset_audio()
            _hide_overlay('disabled_by_player')
        _log('reminder ' + ('enabled' if _reminder_enabled else 'disabled') + ' by hotkey')
    except Exception:
        _exception('reminder hotkey unavailable')


def _subscribe_hotkey():
    global _key_handler
    try:
        from gui import InputHandler
        handler = InputHandler.g_instance
        handler.onKeyDown += _on_key_down
        _key_handler = handler
        _log('hotkey subscribed=Ctrl+Alt+M')
    except Exception:
        _exception('reminder hotkey subscription failed')


def _unsubscribe_hotkey():
    global _key_handler
    if _key_handler is not None:
        try:
            _key_handler.onKeyDown -= _on_key_down
        except Exception:
            _exception('reminder hotkey unsubscription failed')
        _key_handler = None


def _activate(panel):
    global _panel, _ready_slot, _ready_since, _graphics_disabled, _error_count
    global _last_reason, _last_panel_active, _last_hud_status
    global _last_geometry_source, _last_geometry_camera, _last_camera_view
    global _last_vehicle_source
    global _voice_player, _voice_disabled, _reminder_enabled, _voice_attempts, _voice_failures
    if panel is _panel:
        return
    if _panel is not None:
        _deactivate(_panel)
    _reset_audio()
    _voice_player = None
    _voice_disabled = False
    _voice_attempts = 0
    _voice_failures = 0
    _reminder_enabled = True
    _panel = panel
    _ready_slot = None
    _ready_since = None
    _graphics_disabled = False
    _error_count = 0
    _last_reason = None
    _last_panel_active = None
    _last_hud_status = None
    _last_geometry_source = None
    _last_geometry_camera = None
    _last_camera_view = None
    _last_vehicle_source = None
    _subscribe_hotkey()
    _log('audio battle_start mod_version=%s language=%s event=%s' % (VERSION, _language, _ready_voice_event()))
    _audio_diagnostics()
    _log('battle panel populated; renderer deferred; HUD visibility required')
    _schedule_state()


def _deactivate(panel):
    global _panel, _ready_slot, _ready_since
    if panel is None or panel is not _panel:
        return
    _log('audio battle_end attempts=%d failures=%d disabled=%s' % (
        _voice_attempts, _voice_failures, _voice_disabled))
    _unsubscribe_hotkey()
    _panel = None
    _ready_slot = None
    _ready_since = None
    _cancel_state()
    _reset_audio()
    _delete_overlay()
    _log('battle panel disposed')


def _on_component_registered(event):
    """WoT dispatches this event AFTER component.create/populate."""
    if getattr(event, 'alias', None) != _consumables_alias:
        return
    component = getattr(event, 'componentPy', None)
    if component is None:
        _log('HUD registration ignored: missing component')
        return
    compatible, reason = _panel_contract(component)
    if not compatible:
        _log('HUD registration rejected: ' + reason)
        return
    try:
        _activate(component)
    except Exception:
        _exception('HUD registration handler failed')


def _on_component_unregistered(event):
    """WoT emits this event BEFORE destroying the Flash component."""
    if getattr(event, 'alias', None) != _consumables_alias:
        return
    component = getattr(event, 'componentPy', None)
    if component is _panel:
        try:
            _deactivate(component)
        except Exception:
            _exception('HUD unregistration handler failed')


def init():
    """Subscribe once; never modify WoT methods or installed mod hooks."""
    global _event_bus, _event_scope, _consumables_alias
    if _event_listeners:
        return
    _load_language()
    try:
        from gui.shared import g_eventBus, EVENT_BUS_SCOPE
        from gui.shared.events import ComponentEvent
        from gui.Scaleform.genConsts.BATTLE_VIEW_ALIASES import BATTLE_VIEW_ALIASES
        registrar = getattr(g_eventBus, 'addListener', None)
        unregistrar = getattr(g_eventBus, 'removeListener', None)
        if not callable(registrar) or not callable(unregistrar):
            _log('disabled: WoT component event bus is unavailable')
            return
        _event_bus = g_eventBus
        _event_scope = EVENT_BUS_SCOPE.GLOBAL
        _consumables_alias = BATTLE_VIEW_ALIASES.CONSUMABLES_PANEL
        pairs = ((ComponentEvent.COMPONENT_REGISTERED, _on_component_registered),
                 (ComponentEvent.COMPONENT_UNREGISTERED, _on_component_unregistered))
        for event_type, handler in pairs:
            try:
                registrar(event_type, handler, scope=_event_scope)
            except Exception:
                # If a future event bus registers and then raises, attempt
                # to remove that partially installed callback as well.
                try:
                    unregistrar(event_type, handler, scope=_event_scope)
                except Exception:
                    pass
                raise
            _event_listeners.append((event_type, handler))
        _log('v' + VERSION + ' loaded; component events, strict HUD layout adapter, repeating ready voice and battle hotkey')
    except Exception:
        _exception('component event subscription failed; mod disabled')
        fini()


def fini():
    """Unregister handlers and cleanup without touching native WoT methods."""
    global _event_bus, _event_scope, _consumables_alias
    if _panel is not None:
        try:
            _deactivate(_panel)
        except Exception:
            _exception('final cleanup failed')
    for event_type, handler in tuple(_event_listeners):
        try:
            _event_bus.removeListener(event_type, handler, scope=_event_scope)
        except Exception:
            _exception('failed unsubscribing HUD event ' + str(event_type))
    _event_listeners[:] = []
    _event_bus = None
    _event_scope = None
    _consumables_alias = None
    _log('unloaded')
