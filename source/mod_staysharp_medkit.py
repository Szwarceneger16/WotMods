# -*- coding: utf-8 -*-
"""Stay Sharp Medkit Reminder v1.8.4 (WoT EU, CPython 2.7).

One optional HUD-parented GUI.Simple overlay, 21 ARGB DDS animation frames.
This mod does not change battle SWF or WoT's own equipment logic. It keeps
native ComponentEvent battle lifecycle; optional owned garage footer adapter.
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
VERSION = '1.8.4'
MEDKIT_TAG = 'medkit'
TEXTURE_TEMPLATE = 'gui/maps/staysharp/medkit_pulse_%02d.dds'
FRAME_LEVELS = 20              # frames 0..20, each step is 5% optical intensity
HALF_PULSE = 2.0               # 0%->100% in 2 s, then 100%->0% in 2 s
PULSE_TICK = 0.10              # 10 texture switches/s, never allocate new GUI roots
STATE_TICK = 0.25
DORMANT_TICK = 1.0
STABLE_READY_DELAY = 0.90
READY_VOICE_DELAY = 1.0
READY_VOICE_LEAD = 0.5
READY_VOICE_REPEAT = 10.0
READY_VOICE_EVENT = 'staysharp_medkit_ready'
VOICE_LANGUAGES = ('en', 'pl', 'ru', 'fr', 'de', 'es', 'uk')
CONFIG_FILENAME = 'staysharp.medkit.json'
CONFIG_MAX_BYTES = 16384
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
_audio_due = None
_battle_voice_due = None
_cooldown_deadlines = {}
_equipment_controller = None
_audio_announced = False
_audio_next_reminder = None
_voice_player = None
_voice_disabled = False
_reminder_enabled = True
_voice_enabled = True
_default_reminder_enabled = True
_default_voice_enabled = True
_voice_volume = 70
_key_handler = None
_audio_suspended = True
_language = 'en'
_voice_attempts = 0
_voice_failures = 0
_controls = []
_controls_disabled = False
_perk_state = 'unknown'
_settings_store = None
_shortcut_tracker = None
_capture_target = None
_garage_open = False
_garage_handle = None
_settings_status = ''
_settings_error = ''


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
    """Read bounded local settings; preserve legacy values and unknown fields."""
    global _language, _default_reminder_enabled, _default_voice_enabled, _voice_volume
    global _reminder_enabled, _voice_enabled, _settings_store, _shortcut_tracker
    from staysharp_medkit.settings import SettingsStore
    from staysharp_medkit.hotkeys import ChordTracker
    _settings_store = SettingsStore(_config_path(), log=_log, on_change=_settings_changed)
    config = _settings_store.load()
    selected = config.get('language', 'auto')
    _default_reminder_enabled = config['enabled']
    _default_voice_enabled = config['voice_enabled']
    _voice_volume = config['voice_volume']
    _reminder_enabled = _default_reminder_enabled
    _voice_enabled = _default_voice_enabled
    _shortcut_tracker = ChordTracker(_configured_chords(config))
    if selected == 'auto':
        try:
            from helpers import getClientLanguage
            selected = _language_code(getClientLanguage())
        except Exception:
            selected = None
    _language = selected if selected in VOICE_LANGUAGES else 'en'
    _log('ready voice language=' + _language)
    _log('settings enabled=%s voice_enabled=%s voice_volume=%s' % (
        _reminder_enabled, _voice_enabled, _voice_volume))


def _configured_chords(config):
    # Unknown future configuration fields stay on disk, outside input/UI state.
    source = config.get('hotkeys', {})
    return dict((key, source.get(key, [])) for key in ('toggle_mod', 'toggle_voice'))


def _settings_changed(config):
    global _default_reminder_enabled, _default_voice_enabled, _voice_volume
    _default_reminder_enabled = config['enabled']
    _default_voice_enabled = config['voice_enabled']
    _voice_volume = config['voice_volume']
    # Persisted shortcuts become active only after the complete atomic write.
    if _shortcut_tracker is not None:
        _shortcut_tracker.set_chords(_configured_chords(config))
    _publish_garage_settings()


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
    global _audio_key, _audio_since, _audio_due, _audio_announced
    _suspend_audio()
    _audio_key = None
    _audio_since = None
    _audio_due = None
    _audio_announced = False


def _track_battle_start(panel):
    """Translate the client's server-time battle start to the local audio clock."""
    global _battle_voice_due
    if _battle_voice_due is not None:
        return
    arena = getattr(BigWorld.player(), 'arena', None)
    if getattr(arena, 'period', None) != ARENA_PERIOD.BATTLE:
        return
    elapsed = 0.0
    try:
        end = float(arena.periodEndTime)
        length = float(arena.periodLength)
        value = float(BigWorld.serverTime()) - (end - length)
        if end > 0 and length > 0 and 0 <= value <= length:
            elapsed = value
    except (AttributeError, TypeError, ValueError, OverflowError):
        pass
    _battle_voice_due = _time() + max(0.0, READY_VOICE_DELAY - elapsed)
    _log('audio schedule initial_delay=%.2fs lead=%.2fs repeat=%.2fs' % (
        max(0.0, _battle_voice_due - _time()), READY_VOICE_LEAD, READY_VOICE_REPEAT))


def _on_equipment_updated(compact, item):
    """Native remaining time is a snapshot, timestamp it once per server update."""
    if _perk_state != 'present':
        return
    previous = _cooldown_deadlines.pop(compact, None)
    try:
        if item is None or not item.isInCooldown() or item.getQuantity() <= 0:
            return
        remaining = item.getTimeRemaining()
        if isinstance(remaining, bool) or not isinstance(remaining, (int, long, float)):
            return
        if not 0 < remaining < 86400:
            return
        deadline = _time() + remaining
        if (_audio_key is not None and _audio_key[1] == compact and
                (previous is None or previous[0] is not item or deadline > previous[1] + STATE_TICK)):
            _reset_audio()
        _cooldown_deadlines[compact] = (item, deadline)
    except (AttributeError, TypeError, ValueError, OverflowError):
        return


def _subscribe_equipment(panel):
    global _equipment_controller
    session = getattr(panel, 'sessionProvider', None)
    controller = getattr(getattr(session, 'shared', None), 'equipments', None)
    if controller is None:
        return
    try:
        controller.onEquipmentUpdated += _on_equipment_updated
        _equipment_controller = controller
        _log('audio cooldown updates subscribed=yes')
    except Exception:
        # Without a timestamp, announce at actual readiness instead of guessing.
        _exception('audio cooldown updates unavailable; ready-state fallback')


def _unsubscribe_equipment():
    global _equipment_controller
    controller = _equipment_controller
    _equipment_controller = None
    if controller is not None:
        try:
            controller.onEquipmentUpdated -= _on_equipment_updated
        except Exception:
            _exception('audio cooldown unsubscription failed')
    _cooldown_deadlines.clear()


def _cooldown_soon(compact, item):
    record = _cooldown_deadlines.get(compact)
    if record is None or record[0] is not item:
        return False
    try:
        if not item.isInCooldown() or item.getQuantity() <= 0:
            return False
    except (AttributeError, TypeError):
        return False
    remaining = record[1] - _time()
    # Preserve the in-flight announcement across the server's READY update.
    grace = 2.0 if _audio_announced and _audio_key is not None and _audio_key[1] == compact else 0.0
    return -grace <= remaining <= READY_VOICE_LEAD


def _track_audio_ready(panel, slot, reason='ready'):
    """Keep the same announcement latch from anticipation through actual READY."""
    global _audio_key, _audio_since, _audio_due
    key = (slot, panel._cds[slot]) if slot is not None else None
    if key != _audio_key:
        _reset_audio()
        _audio_key = key
        if key is not None:
            _audio_since = _time()
            _audio_due = (_audio_since if reason == 'cooldown_soon' else
                          max(_audio_since, _battle_voice_due or _audio_since))
            _log('audio readiness=%s slot=%d voice_delay=%.2fs' % (
                reason, slot, _audio_due - _audio_since))
        else:
            _log('audio readiness=not_ready')


def _play_ready_voice():
    global _voice_player, _voice_disabled, _voice_attempts, _voice_failures
    if (_voice_disabled or not _voice_enabled or not _reminder_enabled
            or _panel is None or _crew_perk_status(_panel) != 'present'):
        return
    _voice_attempts += 1
    report = _voice_attempts <= 3 or _voice_attempts % 10 == 0
    try:
        if _voice_player is None:
            import SoundGroups
            _log('audio create event=' + _ready_voice_event())
            _voice_player = SoundGroups.g_instance.getSound2D(_ready_voice_event())
            _log('audio handle present=%s' % (_voice_player is not None))
            _voice_player.volume = _voice_volume / 100.0
            _log('audio voice volume=%s' % _voice_volume)
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
            result_type = type(result).__name__
            _log('audio play attempt=%d result=%s result_type=%s isPlaying=%s audible=unknown' % (
                _voice_attempts, result_label, result_type, playing))
        # WoT's own callers do not interpret play()'s return value as a
        # success flag. A falsey result can coexist with isPlaying=True.
    except Exception:
        _voice_failures += 1
        _voice_disabled = True
        _exception('ready voice unavailable; audio disabled for battle')


def _update_audio(eligible=False, anticipating=False):
    """Run on the existing state tick; no extra callbacks or catch-up bursts."""
    global _audio_announced, _audio_next_reminder, _audio_suspended
    if (not _voice_enabled or not _reminder_enabled or _graphics_disabled
            or not (_overlay_active or eligible) or _audio_key is None):
        _suspend_audio()
        return
    now = _time()
    if _audio_due is None or now < _audio_due:
        return
    _audio_suspended = False
    if not _audio_announced:
        _audio_announced = True
        _play_ready_voice()
        _audio_next_reminder = now + READY_VOICE_REPEAT
    elif anticipating:
        return
    elif _audio_next_reminder is None:
        # Resume after a full voice interval without replaying on HUD visibility.
        _audio_next_reminder = now + READY_VOICE_REPEAT
    elif now >= _audio_next_reminder:
        _audio_next_reminder = now + READY_VOICE_REPEAT
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
        interval = STATE_TICK if _perk_state == 'present' else DORMANT_TICK
        _state_callback = BigWorld.callback(interval, _check_state)


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


# The skill configuration maps commander_staySharp to VSE perk 108.
# Vehicle.crewCompactDescrs is the server's own-vehicle crew snapshot.
STAY_SHARP_SKILL = 'commander_staySharp'
_crew_perk_cache_key = None
_crew_perk_cache_status = 'unknown'


def _clear_crew_perk_cache():
    global _crew_perk_cache_key, _crew_perk_cache_status
    _crew_perk_cache_key = None
    _crew_perk_cache_status = 'unknown'


def _crew_perk_status(panel):
    """Read learned active-role skills, independently of temporary perkEffects.

    Unknown or incomplete crew data must never enable native GUI/input/audio.
    Decode a changed snapshot once; never log the compact descriptions or IDs.
    """
    global _crew_perk_cache_key, _crew_perk_cache_status
    try:
        player = BigWorld.player()
        if player is None:
            return 'unknown'
        vehicle, unused_origin = _resolve_player_vehicle(panel, player)
        if vehicle is None:
            return 'unknown'
        crew_data = getattr(vehicle, 'crewCompactDescrs', None)
        descriptor = getattr(vehicle, 'typeDescriptor', None)
        roles_data = getattr(getattr(descriptor, 'type', None), 'crewRoles', None)
        if crew_data is None or roles_data is None:
            return 'unknown'
        crew = tuple(crew_data)
        roles = tuple(tuple(slot_roles) for slot_roles in roles_data)
        if not crew or len(crew) > 16 or len(roles) != len(crew):
            return 'unknown'
        key = (id(vehicle), getattr(vehicle, 'id', None), crew, roles)
        if key == _crew_perk_cache_key:
            return _crew_perk_cache_status
        from items.tankmen import TankmanDescr
        try:
            string_types = (basestring,)
        except NameError:
            string_types = (str, bytes)
        status = 'absent'
        for compact, active_roles in zip(crew, roles):
            if (not compact or not isinstance(compact, string_types)
                    or len(compact) > 65536 or not active_roles):
                status = 'unknown'
                continue
            tankman = TankmanDescr(compact, battleOnly=True)
            for skill_name, skill_level in tankman.skillLevels(active_roles):
                if skill_name == STAY_SHARP_SKILL and skill_level > 0:
                    _crew_perk_cache_key, _crew_perk_cache_status = key, 'present'
                    return 'present'
        # Do not cache incomplete snapshots; the server can populate them later.
        if status != 'unknown':
            _crew_perk_cache_key, _crew_perk_cache_status = key, status
        return status
    except Exception:
        # Client versions without this read-only contract stay dormant.
        return 'unknown'


def _probe_medkit(panel, for_audio=False):
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
        anticipating = for_audio and _cooldown_soon(compact, item)
        if not item.isAvailableToUse and not anticipating:
            continue
        descriptor = item.getDescriptor()
        if descriptor is None or descriptor.name not in enabled:
            continue
        # Native _MedKitItem._canActivate uses avatar.vehicle when avatar
        # is omitted. Explicit avatar selects BigWorld.entity(playerVehicleID)
        # in sniper/strategic/arty modes and prevents the camera-only bug.
        if not anticipating and not item.canActivate(avatar=player)[0]:
            continue
        try:
            slot = slots.index(compact)
        except ValueError:
            continue
        valid, slot_reason = _slot_contract(panel, slot, compact)
        if not valid:
            return (None, 'incompatible_hud_' + slot_reason)
        # Keep native visual warnings on top. The same callback map also
        # contains the ordinary green READY flash: it must not cut the voice
        # that started just before zero, or delay an actual-ready announcement.
        ready_flash = False
        if for_audio and bool(getattr(item, 'becomeReady', False)):
            try:
                warning = getattr(panel, '_canApplyingGlowEquipment', None)
                ready_flash = callable(warning) and not warning(item)
            except Exception:
                pass
        if slot in getattr(panel, '_equipmentsGlowCallbacks', {}) and not ready_flash:
            return (None, 'vanilla_equipment_glow_priority')
        return (slot, 'cooldown_soon' if anticipating else 'ready')
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

# GUI.Simple native key/mouse callbacks are unsafe in the current client:
# its callback bridge raises "Unregistered type : BW::KeyEvent" in native code.
# These components stay visual-only; one timer reads primitive cursor/button
# state for both icons and applies completed clicks on a separate callback.
_controls_poll_callback = None
_controls_mouse_down = None
_controls_cursor_was_active = False
_controls_pending_actions = []
_controls_pending_detaches = []


class _ControlState(object):
    def __init__(self, action, component):
        self.action = action
        self.component = component
        self.pressed = False

    def contains(self, point):
        width, height = GUI.screenResolution()[:2]
        x, y = point
        center, size = self.component.position, self.component.size
        return (abs(x - center[0]) < float(size[0]) / width and
                abs(y - center[1]) < float(size[1]) / height)


def _controls_cursor_active():
    if _panel is None or not any(entry[0].visible for entry in _controls):
        return False
    try:
        cursor = GUI.mcursor()
        if not cursor.active or not cursor.visible:
            return False
        app = getattr(_panel, 'app', None)
        modal = getattr(app, 'isModalViewShown', None)
        if callable(modal) and modal():
            return False
        # Ctrl only exposes the game's cursor. Modifiers are not click inputs.
        return _control_slot(_panel) is not None
    except Exception:
        return False


def _control_slot(panel):
    if _crew_perk_status(panel) != 'present':
        return None
    shown, unused_reason = _hud_visibility(panel)
    if not shown:
        return None
    session = getattr(panel, 'sessionProvider', None)
    if session is None or session.isReplayPlaying:
        return None
    player = BigWorld.player()
    if player is None or player.isObserver() or not getattr(player, 'isVehicleAlive', True):
        return None
    vehicle, unused_reason = _resolve_player_vehicle(panel, player)
    if vehicle is None or getattr(vehicle, 'health', 0) <= 0:
        return None
    if _camera_view(panel) == 2:
        descriptor = getattr(vehicle, 'typeDescriptor', None)
        tags = getattr(getattr(descriptor, 'type', None), 'tags', ())
        if 'SPG' not in tags:
            return None
    valid, unused_reason = _panel_contract(panel)
    if not valid:
        return None
    controller = getattr(getattr(session, 'shared', None), 'equipments', None)
    iterator = getattr(controller, 'iterEquipmentsByTag', None)
    if not callable(iterator):
        return None
    for compact, item in iterator(MEDKIT_TAG):
        if item is None or compact not in panel._cds:
            continue
        slot = panel._cds.index(compact)
        valid, unused_reason = _slot_contract(panel, slot, compact)
        if valid:
            return slot
    return None


def _cancel_control_actions():
    actions = list(_controls_pending_actions)
    _controls_pending_actions[:] = []
    for action in actions:
        try:
            BigWorld.cancelCallback(action['callback'])
        except Exception:
            _exception('HUD control action cancellation failed')


def _queue_control_action(state):
    action = {'callback': None, 'panel': _panel, 'state': state}
    def apply_control_action():
        if action not in _controls_pending_actions:
            return
        _controls_pending_actions.remove(action)
        panel = action['panel']
        current = any(entry[3] is state and entry[0].visible for entry in _controls)
        if panel is not _panel or not current or not _controls_cursor_active():
            return
        _log('HUD control click: ' + state.action)
        if state.action == 'power':
            _toggle_reminder()
        else:
            _toggle_voice()
        # The regular state tick refreshes textures. Never mutate GUI roots
        # or call Flash layout functions synchronously from input dispatch.
    _controls_pending_actions.append(action)
    try:
        action['callback'] = BigWorld.callback(0.0, apply_control_action)
    except Exception:
        _controls_pending_actions.remove(action)
        raise


def _schedule_control_poll(delay):
    global _controls_poll_callback
    if _controls_poll_callback is None and _controls and _panel is not None:
        _controls_poll_callback = BigWorld.callback(delay, _poll_controls)


def _poll_controls():
    global _controls_poll_callback, _controls_mouse_down, _controls_disabled, _controls_cursor_was_active
    _controls_poll_callback = None
    if not _controls or _panel is None:
        return
    try:
        import Keys
        cursor = GUI.mcursor()
        down = bool(BigWorld.isKeyDown(Keys.KEY_LEFTMOUSE))
        active = bool(cursor.active and cursor.visible and any(entry[0].visible for entry in _controls))
        previous = _controls_mouse_down
        was_active = _controls_cursor_was_active
        _controls_mouse_down = down
        _controls_cursor_was_active = active
        if not active:
            for entry in _controls:
                entry[3].pressed = False
        elif was_active and previous is not None and down != previous:
            eligible = _controls_cursor_active()
            for component, unused_owner, unused_mount, state in _controls:
                inside = eligible and component.visible and state.contains(cursor.position)
                if down:
                    state.pressed = inside
                else:
                    clicked = state.pressed and inside
                    state.pressed = False
                    if clicked:
                        _queue_control_action(state)
        # The first sample is only a baseline: a button held before these
        # icons appeared must not turn its eventual release into a click.
        _schedule_control_poll(0.02 if active else 0.10)
    except Exception:
        _controls_disabled = True
        _exception('HUD controls disabled after input polling failure')
        _delete_controls()


def _hide_controls():
    global _controls_mouse_down, _controls_cursor_was_active
    _controls_mouse_down = None
    _controls_cursor_was_active = False
    _cancel_control_actions()
    for component, unused_owner, unused_mount, state in _controls:
        component.visible = False
        state.pressed = False


def _dispose_control_roots(entries):
    for component, owner, mount, unused_state in entries:
        try:
            if mount == 'hud_child':
                owner.delChild(component)
            elif mount == 'gui_root':
                GUI.delRoot(component)
        except Exception:
            _exception('HUD control cleanup failed')


def _delete_controls():
    global _controls_poll_callback, _controls_mouse_down, _controls_cursor_was_active
    callback = _controls_poll_callback
    _controls_poll_callback = None
    _controls_mouse_down = None
    _controls_cursor_was_active = False
    if callback is not None:
        try:
            BigWorld.cancelCallback(callback)
        except Exception:
            _exception('HUD control polling cancellation failed')
    _cancel_control_actions()
    entries = list(_controls)
    _controls[:] = []
    for component, unused_owner, unused_mount, state in entries:
        component.visible = False
        state.pressed = False
    if not entries:
        return
    # Component disposal can run inside another native GUI handler. Removing
    # roots there invalidates SimpleGUI's vector while it is still iterating.
    # Keep the components alive and detach on the next engine callback instead.
    pending = {'callback': None, 'entries': entries}
    def detach_control_roots():
        if pending not in _controls_pending_detaches:
            return
        _controls_pending_detaches.remove(pending)
        _dispose_control_roots(entries)
    _controls_pending_detaches.append(pending)
    try:
        pending['callback'] = BigWorld.callback(0.0, detach_control_roots)
    except Exception:
        # Hidden visual-only roots are safer than modifying an active native
        # input traversal synchronously. Retain them if scheduling is unavailable.
        _exception('HUD control deferred cleanup unavailable; hidden roots retained')


def _sync_controls(panel):
    """Keep visual-only switches and their one polling timer in sync with HUD."""
    global _controls_disabled
    if _controls_disabled:
        return
    try:
        slot = _control_slot(panel)
        geometry, unused_reason = _geometry(panel, slot) if slot is not None else (None, None)
        if geometry is None:
            _hide_controls()
            return
        if not _controls:
            for action in ('power', 'voice'):
                for state in ('on', 'off'):
                    if not ResMgr.isFile('gui/maps/staysharp/control_%s_%s.dds' % (action, state)):
                        raise ValueError('HUD control texture unavailable')
            for action in ('power', 'voice'):
                path = 'gui/maps/staysharp/control_%s_on.dds' % action
                component = GUI.Simple(path)
                state = _ControlState(action, component)
                # An unattached allocation needs no native detach if setup fails.
                entry = [component, None, 'unattached', state]
                _controls.append(entry)
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
                component.visible = False
                component.colour = (255, 255, 255, 255)
                component.position = (0.0, 0.0, GUI_DEPTH)
                # Record ownership before attachment for partial-failure cleanup.
                entry[2] = 'gui_root'
                GUI.addRoot(component)
            _log('HUD controls created; visual-only roots; cursor polling; left-click power or voice')
        width, height = GUI.screenResolution()[:2]
        size = geometry[2] * (16.0 / BORDER_SIZE)
        y = geometry[1] + 2.0 * (geometry[2] * 0.5 + size * 0.5 + 4.0 * _interface_scale(panel)) / height
        for index, entry in enumerate(_controls):
            component = entry[0]
            action = 'power' if index == 0 else 'voice'
            enabled = _reminder_enabled if index == 0 else _voice_enabled
            path = 'gui/maps/staysharp/control_%s_%s.dds' % (action, 'on' if enabled else 'off')
            if component.textureName != path:
                component.textureName = path
            component.size = (size, size)
            component.position = (geometry[0] + (index * 2 - 1) * (size + 3.0 * _interface_scale(panel)) / width,
                                  y, GUI_DEPTH)
            component.visible = True
        _schedule_control_poll(0.02)
    except Exception:
        _controls_disabled = True
        _exception('HUD controls disabled after GUI failure')
        _delete_controls()


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


def _hide_overlay(reason='not_ready', suspend_audio=True):
    global _overlay_active, _frame
    if suspend_audio:
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
    global _perk_state, _voice_player
    status = _crew_perk_status(panel)
    if status != _perk_state:
        _log('crew stay_sharp=%s; reminder %s' % (
            status, 'awake' if status == 'present' else 'dormant'))
    _perk_state = status
    if status != 'present':
        _ready_slot, _ready_since = None, None
        _reset_audio()
        _voice_player = None
        _unsubscribe_hotkey()
        _unsubscribe_equipment()
        _delete_controls()
        _delete_overlay()
        return
    if _key_handler is None:
        _subscribe_hotkey()
    if _equipment_controller is None:
        _subscribe_equipment(panel)
    _sync_controls(panel)
    _track_battle_start(panel)
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
            slot, reason = _probe_medkit(panel, for_audio=True)
            _track_audio_ready(panel, slot, reason)
        else:
            _reset_audio()
        _ready_slot, _ready_since = None, None
        _hide_overlay(hud_reason)
        return

    slot, reason = _probe_medkit(panel)
    audio_slot, audio_reason = (slot, reason) if slot is not None else _probe_medkit(panel, for_audio=True)
    _track_audio_ready(panel, audio_slot, audio_reason)
    if reason != _last_reason:
        _last_reason = reason
        _log('equipment state=' + reason + (' slot=%d' % slot if slot is not None else ''))
    if slot is None:
        _ready_slot, _ready_since = None, None
        if audio_slot is not None:
            geometry, _ = _geometry(panel, audio_slot)
            if geometry is not None:
                _hide_overlay(reason, suspend_audio=False)
                _update_audio(eligible=True, anticipating=audio_reason == 'cooldown_soon')
                return
        _hide_overlay(reason)
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
    _update_audio(eligible=True)
    if slot != _ready_slot:
        _ready_slot, _ready_since = slot, _time()
        _hide_overlay('slot_changed', suspend_audio=False)
        return
    if _time() - _ready_since < STABLE_READY_DELAY:
        return
    _show_overlay(slot, geometry)

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


# Written into the game entrypoint; only primitive keys cross this boundary.
_GARAGE_LABELS = json.loads(r'''{"en":{"title":"Medkit hotkeys","toggle_mod":"Toggle mod","toggle_voice":"Toggle voice","cancel":"Cancel","clear":"Clear","close":"Close","capture":"Press keys...","not_assigned":"Not assigned","hint":"Select a shortcut, hold the keys together, then release all keys. Esc cancels.","saved":"Shortcut saved","cancelled":"Recording cancelled","conflict":"These shortcuts overlap. Choose another combination.","failed":"Could not save. Previous shortcuts remain active."},"pl":{"title":"Skr\u00f3ty apteczki","toggle_mod":"W\u0142\u0105cz / wy\u0142\u0105cz mod","toggle_voice":"W\u0142\u0105cz / wy\u0142\u0105cz g\u0142os","cancel":"Anuluj","clear":"Wyczy\u015b\u0107","close":"Zamknij","capture":"Naci\u015bnij klawisze...","not_assigned":"Nieprzypisany","hint":"Wybierz skr\u00f3t, przytrzymaj klawisze razem, potem zwolnij wszystkie. Esc anuluje.","saved":"Skr\u00f3t zapisany","cancelled":"Nagrywanie anulowane","conflict":"Skr\u00f3ty nak\u0142adaj\u0105 si\u0119. Wybierz inn\u0105 kombinacj\u0119.","failed":"Nie uda\u0142o si\u0119 zapisa\u0107. Poprzednie skr\u00f3ty pozostaj\u0105 aktywne."},"de":{"title":"Tastenk\u00fcrzel f\u00fcr Erste Hilfe","toggle_mod":"Mod ein / aus","toggle_voice":"Stimme ein / aus","cancel":"Abbrechen","clear":"L\u00f6schen","close":"Schlie\u00dfen","capture":"Tasten dr\u00fccken...","not_assigned":"Nicht belegt","hint":"Tasten gemeinsam halten, dann alle loslassen. Esc bricht ab.","saved":"Tastenk\u00fcrzel gespeichert","cancelled":"Aufnahme abgebrochen","conflict":"Tastenk\u00fcrzel \u00fcberschneiden sich.","failed":"Speichern fehlgeschlagen. Bisherige Tastenk\u00fcrzel bleiben aktiv."},"fr":{"title":"Raccourcis de la trousse","toggle_mod":"Activer le mod","toggle_voice":"Activer la voix","cancel":"Annuler","clear":"Effacer","close":"Fermer","capture":"Appuyez sur les touches...","not_assigned":"Non attribu\u00e9","hint":"Maintenez les touches ensemble puis rel\u00e2chez-les toutes. \u00c9chap annule.","saved":"Raccourci enregistr\u00e9","cancelled":"Enregistrement annul\u00e9","conflict":"Ces raccourcis se chevauchent.","failed":"\u00c9chec de l\u2019enregistrement. Les anciens raccourcis restent actifs."},"es":{"title":"Atajos del botiqu\u00edn","toggle_mod":"Activar mod","toggle_voice":"Activar voz","cancel":"Cancelar","clear":"Borrar","close":"Cerrar","capture":"Pulsa las teclas...","not_assigned":"Sin asignar","hint":"Mant\u00e9n las teclas juntas y su\u00e9ltalas todas. Esc cancela.","saved":"Atajo guardado","cancelled":"Grabaci\u00f3n cancelada","conflict":"Los atajos se superponen.","failed":"No se pudo guardar. Se conservan los atajos anteriores."},"ru":{"title":"\u041a\u043b\u0430\u0432\u0438\u0448\u0438 \u0430\u043f\u0442\u0435\u0447\u043a\u0438","toggle_mod":"\u0412\u043a\u043b\u044e\u0447\u0438\u0442\u044c \u043c\u043e\u0434","toggle_voice":"\u0412\u043a\u043b\u044e\u0447\u0438\u0442\u044c \u0433\u043e\u043b\u043e\u0441","cancel":"\u041e\u0442\u043c\u0435\u043d\u0430","clear":"\u041e\u0447\u0438\u0441\u0442\u0438\u0442\u044c","close":"\u0417\u0430\u043a\u0440\u044b\u0442\u044c","capture":"\u041d\u0430\u0436\u043c\u0438\u0442\u0435 \u043a\u043b\u0430\u0432\u0438\u0448\u0438...","not_assigned":"\u041d\u0435 \u043d\u0430\u0437\u043d\u0430\u0447\u0435\u043d\u043e","hint":"\u0423\u0434\u0435\u0440\u0436\u0438\u0432\u0430\u0439\u0442\u0435 \u043a\u043b\u0430\u0432\u0438\u0448\u0438 \u0432\u043c\u0435\u0441\u0442\u0435, \u0437\u0430\u0442\u0435\u043c \u043e\u0442\u043f\u0443\u0441\u0442\u0438\u0442\u0435 \u0432\u0441\u0435. Esc \u043e\u0442\u043c\u0435\u043d\u044f\u0435\u0442.","saved":"\u0421\u043e\u0447\u0435\u0442\u0430\u043d\u0438\u0435 \u0441\u043e\u0445\u0440\u0430\u043d\u0435\u043d\u043e","cancelled":"\u0417\u0430\u043f\u0438\u0441\u044c \u043e\u0442\u043c\u0435\u043d\u0435\u043d\u0430","conflict":"\u0421\u043e\u0447\u0435\u0442\u0430\u043d\u0438\u044f \u043f\u0435\u0440\u0435\u0441\u0435\u043a\u0430\u044e\u0442\u0441\u044f.","failed":"\u041d\u0435 \u0443\u0434\u0430\u043b\u043e\u0441\u044c \u0441\u043e\u0445\u0440\u0430\u043d\u0438\u0442\u044c. \u041f\u0440\u0435\u0436\u043d\u0438\u0435 \u0441\u043e\u0447\u0435\u0442\u0430\u043d\u0438\u044f \u043e\u0441\u0442\u0430\u044e\u0442\u0441\u044f \u0430\u043a\u0442\u0438\u0432\u043d\u044b\u043c\u0438."},"uk":{"title":"\u041a\u043b\u0430\u0432\u0456\u0448\u0456 \u0430\u043f\u0442\u0435\u0447\u043a\u0438","toggle_mod":"\u0423\u0432\u0456\u043c\u043a\u043d\u0443\u0442\u0438 \u043c\u043e\u0434","toggle_voice":"\u0423\u0432\u0456\u043c\u043a\u043d\u0443\u0442\u0438 \u0433\u043e\u043b\u043e\u0441","cancel":"\u0421\u043a\u0430\u0441\u0443\u0432\u0430\u0442\u0438","clear":"\u041e\u0447\u0438\u0441\u0442\u0438\u0442\u0438","close":"\u0417\u0430\u043a\u0440\u0438\u0442\u0438","capture":"\u041d\u0430\u0442\u0438\u0441\u043d\u0456\u0442\u044c \u043a\u043b\u0430\u0432\u0456\u0448\u0456...","not_assigned":"\u041d\u0435 \u043f\u0440\u0438\u0437\u043d\u0430\u0447\u0435\u043d\u043e","hint":"\u0423\u0442\u0440\u0438\u043c\u0443\u0439\u0442\u0435 \u043a\u043b\u0430\u0432\u0456\u0448\u0456 \u0440\u0430\u0437\u043e\u043c, \u043f\u043e\u0442\u0456\u043c \u0432\u0456\u0434\u043f\u0443\u0441\u0442\u0456\u0442\u044c \u0443\u0441\u0456. Esc \u0441\u043a\u0430\u0441\u043e\u0432\u0443\u0454.","saved":"\u0421\u043f\u043e\u043b\u0443\u0447\u0435\u043d\u043d\u044f \u0437\u0431\u0435\u0440\u0435\u0436\u0435\u043d\u043e","cancelled":"\u0417\u0430\u043f\u0438\u0441 \u0441\u043a\u0430\u0441\u043e\u0432\u0430\u043d\u043e","conflict":"\u0421\u043f\u043e\u043b\u0443\u0447\u0435\u043d\u043d\u044f \u043f\u0435\u0440\u0435\u0442\u0438\u043d\u0430\u044e\u0442\u044c\u0441\u044f.","failed":"\u041d\u0435 \u0432\u0434\u0430\u043b\u043e\u0441\u044f \u0437\u0431\u0435\u0440\u0435\u0433\u0442\u0438. \u041f\u043e\u043f\u0435\u0440\u0435\u0434\u043d\u0456 \u0441\u043f\u043e\u043b\u0443\u0447\u0435\u043d\u043d\u044f \u0437\u0430\u043b\u0438\u0448\u0430\u044e\u0442\u044c\u0441\u044f \u0430\u043a\u0442\u0438\u0432\u043d\u0438\u043c\u0438."}}''')


def _garage_payload():
    from staysharp_medkit.hotkeys import format_chord
    config = _settings_store.get_payload() if _settings_store is not None else {}
    hotkeys = _configured_chords(config)
    return {'hotkeys': hotkeys,
            'display': dict((key, format_chord(value).replace('+', ' + ')) for key, value in hotkeys.items()
                            if key in ('toggle_mod', 'toggle_voice')),
            'capturing': _capture_target,
            'preview': list(_shortcut_tracker.held_keys) if _capture_target and _shortcut_tracker else [],
            'status': _settings_status, 'error': _settings_error,
            'labels': _GARAGE_LABELS.get(_language, _GARAGE_LABELS['en']),
            'enabled': _default_reminder_enabled, 'voice_enabled': _default_voice_enabled}


def _publish_garage_settings():
    if _garage_handle is not None:
        from staysharp_medkit import garage
        garage.update(_garage_payload())


def _cancel_capture(publish=True):
    global _capture_target
    _capture_target = None
    if _shortcut_tracker is not None:
        _shortcut_tracker.reset()
    if _panel is None:
        _unsubscribe_hotkey()
    if publish:
        _publish_garage_settings()


def _garage_action(command):
    global _garage_open, _capture_target, _settings_error, _settings_status
    action = command.get('action')
    if action in ('close', 'cancel_capture'):
        if action == 'close':
            _garage_open = False
        _settings_status = ''
        _settings_error = ''
        _cancel_capture()
        return
    # A late garage command must never activate recording during battle.
    player = BigWorld.player()
    if _panel is not None or getattr(player, 'arena', None) is not None:
        return False
    if action == 'open':
        _cancel_capture(publish=False)
        _garage_open = True
        _settings_status = _settings_error = ''
        if _settings_store is not None:
            _settings_changed(_settings_store.load())
        _publish_garage_settings()
        return
    binding = command.get('binding')
    if not _garage_open or binding not in ('toggle_mod', 'toggle_voice'):
        return
    _settings_status = _settings_error = ''
    if action == 'begin_capture':
        _cancel_capture(publish=False)
        _capture_target = binding
        _shortcut_tracker.begin_capture(side_specific=True)
        _subscribe_hotkey()
        if _key_handler is None:
            _capture_target = None
            _shortcut_tracker.reset()
            _settings_error = _GARAGE_LABELS.get(_language, _GARAGE_LABELS['en'])['failed']
    elif action == 'clear_binding':
        _cancel_capture(publish=False)
        _save_binding(binding, [])
    _publish_garage_settings()


def _save_binding(binding, chord):
    global _settings_status, _settings_error
    labels = _GARAGE_LABELS.get(_language, _GARAGE_LABELS['en'])
    if _settings_store is not None and _settings_store.update_hotkeys({binding: chord}):
        _settings_status, _settings_error = labels['saved'], ''
        _log('shortcut configuration saved')
    else:
        code = _settings_store.last_error if _settings_store is not None else None
        _settings_status = ''
        _settings_error = labels['conflict' if code == 'conflicting_hotkeys' else 'failed']
    _publish_garage_settings()


def _garage_capture_allowed():
    from staysharp_medkit import garage
    return garage.is_capture_allowed()


def _input_blocked():
    try:
        from messenger import MessengerEntry
        if MessengerEntry.g_instance.gui.isFocused():
            return True
        app = getattr(_panel, 'app', None)
        modal = getattr(app, 'isModalViewShown', None)
        return bool(callable(modal) and modal())
    except Exception:
        return True


def _on_key_down(event):
    _handle_shortcut_key(event, True)


def _on_key_up(event):
    _handle_shortcut_key(event, False)


def _handle_shortcut_key(event, down):
    global _capture_target, _settings_status
    from staysharp_medkit.hotkeys import key_name
    if _shortcut_tracker is None:
        return
    try:
        # Ignore all mouse/unsupported input before querying vehicle or crew.
        key = key_name(event.key)
        if key is None:
            return
        repeated = bool(event.isRepeatedEvent()) if down else False
        if repeated:
            return
        blocked = _input_blocked()
        capturing = _capture_target is not None
        if capturing:
            blocked = (blocked or not _garage_open or _panel is not None
                       or getattr(BigWorld.player(), 'arena', None) is not None
                       or not _garage_capture_allowed())
        elif _panel is None or _crew_perk_status(_panel) != 'present':
            _shortcut_tracker.reset()
            return
        reconciled = _shortcut_tracker.reconcile(getattr(BigWorld, 'isKeyDown', None), current_key=event.key)
        if reconciled and capturing:
            _settings_status = _GARAGE_LABELS.get(_language, _GARAGE_LABELS['en'])['cancelled']
            _cancel_capture()
            return
        outcome = _shortcut_tracker.feed(key, down, repeated=repeated, blocked=blocked)
        if capturing:
            if outcome['cancelled']:
                _settings_status = _GARAGE_LABELS.get(_language, _GARAGE_LABELS['en'])['cancelled']
                _cancel_capture()
            elif outcome['captured'] is not None:
                binding = _capture_target
                _capture_target = None
                _save_binding(binding, outcome['captured'])
                if _panel is None:
                    _unsubscribe_hotkey()
            else:
                _publish_garage_settings()
            return
        for action in outcome['actions']:
            if action == 'toggle_mod':
                _toggle_reminder()
            elif action == 'toggle_voice':
                _toggle_voice()
    except Exception:
        _cancel_capture(publish=False)
        _exception('shortcut input unavailable')


def _toggle_reminder():
    global _reminder_enabled
    if _panel is None:
        return
    _reminder_enabled = not _reminder_enabled
    _reset_audio()
    if not _reminder_enabled:
        _hide_overlay('disabled_by_player')
    _log('reminder enabled=%s for current battle' % _reminder_enabled)


def _toggle_voice():
    global _voice_enabled
    if _panel is None:
        return
    _voice_enabled = not _voice_enabled
    _reset_audio()
    _log('voice enabled=%s for current battle' % _voice_enabled)


def _subscribe_hotkey():
    global _key_handler
    if _key_handler is not None:
        return
    handler = None
    try:
        from gui import InputHandler
        handler = InputHandler.g_instance
        handler.onKeyDown += _on_key_down
        handler.onKeyUp += _on_key_up
        _key_handler = handler
        _log('configured keyboard shortcuts subscribed')
    except Exception:
        if handler is not None:
            for name, callback in (('onKeyDown', _on_key_down), ('onKeyUp', _on_key_up)):
                try:
                    event = getattr(handler, name)
                    event -= callback
                except Exception:
                    pass
        _exception('shortcut subscription failed')


def _unsubscribe_hotkey():
    global _key_handler
    handler, _key_handler = _key_handler, None
    if handler is not None:
        for name, callback in (('onKeyDown', _on_key_down), ('onKeyUp', _on_key_up)):
            try:
                event = getattr(handler, name)
                event -= callback
            except Exception:
                _exception('shortcut unsubscription failed')
    if _shortcut_tracker is not None:
        _shortcut_tracker.reset()


def _activate(panel):
    global _panel, _ready_slot, _ready_since, _graphics_disabled, _error_count
    global _last_reason, _last_panel_active, _last_hud_status
    global _last_geometry_source, _last_geometry_camera, _last_camera_view
    global _last_vehicle_source
    global _voice_player, _voice_disabled, _reminder_enabled, _voice_enabled, _voice_attempts, _voice_failures
    global _controls_disabled, _battle_voice_due, _perk_state
    if panel is _panel:
        return
    if _panel is not None:
        _deactivate(_panel)
    _cancel_capture(publish=False)
    from staysharp_medkit import garage
    garage.close_window()
    _reset_audio()
    _battle_voice_due = None
    _cooldown_deadlines.clear()
    _clear_crew_perk_cache()
    _voice_player = None
    _voice_disabled = False
    _voice_attempts = 0
    _voice_failures = 0
    _controls_disabled = False
    _reminder_enabled = _default_reminder_enabled
    _voice_enabled = _default_voice_enabled
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
    _perk_state = _crew_perk_status(panel)
    _log('crew stay_sharp=%s; reminder %s' % (
        _perk_state, 'awake' if _perk_state == 'present' else 'dormant'))
    if _perk_state == 'present':
        _subscribe_hotkey()
        _subscribe_equipment(panel)
    _log('audio battle_start mod_version=%s language=%s event=%s' % (VERSION, _language, _ready_voice_event()))
    if _perk_state == 'present':
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
    _unsubscribe_equipment()
    _panel = None
    _ready_slot = None
    _ready_since = None
    _cancel_state()
    _reset_audio()
    _clear_crew_perk_cache()
    _delete_controls()
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


def _install_garage():
    global _garage_handle
    try:
        from staysharp_medkit import garage
        _garage_handle = garage.install(_garage_action, _garage_payload)
        _log('garage settings available=%s' % (_garage_handle is not None))
    except Exception:
        _exception('garage settings unavailable; battle reminder remains active')


def init():
    """Subscribe once; never modify WoT methods or installed mod hooks."""
    global _event_bus, _event_scope, _consumables_alias
    if _event_listeners:
        return
    _load_language()
    _install_garage()
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
    global _event_bus, _event_scope, _consumables_alias, _garage_handle, _garage_open
    _garage_open = False
    _cancel_capture(publish=False)
    from staysharp_medkit import garage
    try:
        garage.uninstall()
    except Exception:
        _exception('garage settings cleanup failed')
    _garage_handle = None
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
