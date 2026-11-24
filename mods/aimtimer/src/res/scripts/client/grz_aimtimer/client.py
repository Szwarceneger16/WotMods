# -*- coding: ascii -*-
"""Read-only own-vehicle aim estimate using a fresh native client snapshot.

Only primitive presentation data leaves the adapter. It never calls the
mutating dispersion calculator, reads targets or constructs scene queries.
"""
from __future__ import absolute_import

import math

from .core import estimate_remaining

try:
    _INTEGER_TYPES = (int, long)
    _TEXT_TYPES = (str, unicode)
except NameError:
    _INTEGER_TYPES = (int,)
    _TEXT_TYPES = (str, bytes)

_NUMBER_TYPES = _INTEGER_TYPES + (float,)
SUPPORTED_MODES = ('arcade', 'sniper', 'strategic', 'arty', 'dualgun', 'twinGun')
_OTHER_MODES = ('postmortem', 'debug', 'video', 'mapcase', 'arcadeMapcase',
                'epicMapcase', 'respawn', 'deathfreecam', 'killcam',
                'vehiclesSelection', 'lookAtKiller', 'smStrategic',
                'smEntityView', 'prebattleHighlights',
                'arcadeEpicMinefieldMapcase')
MAX_SNAPSHOT_AGE = 0.5
_DISPERSION_PLACEHOLDER = (5, 6, 6, 6, 6, 5)


def _number(value):
    if type(value) not in _NUMBER_TYPES:
        return None
    try:
        result = float(value)
    except (ValueError, TypeError, OverflowError):
        return None
    return None if math.isnan(result) or math.isinf(result) else result


def _flag(value):
    if type(value) is bool:
        return value
    if type(value) in _INTEGER_TYPES and value in (0, 1):
        return bool(value)
    return None


def _entity_id(value):
    if type(value) in _INTEGER_TYPES and 0 < value < 2 ** 63:
        return value
    return None


def _mode(value):
    if type(value) not in _TEXT_TYPES:
        return 'unknown'
    try:
        if not isinstance(value, str):
            value = value.decode('ascii') if isinstance(value, bytes) else str(value)
    except (UnicodeError, ValueError, TypeError):
        return 'unknown'
    return value if value in SUPPORTED_MODES + _OTHER_MODES else 'unknown'


def _pair(value):
    if type(value) not in (tuple, list) or len(value) < 2:
        return None
    first, second = _number(value[0]), _number(value[1])
    return None if first is None or second is None else (first, second)


def _load_module(name):
    try:
        return __import__(name, fromlist=['__name__'])
    except Exception:
        return None


class BattleProbe(object):
    """No native-state writes or target reads.

    ``battle_eligible`` describes an active own-vehicle battle context.
    ``available`` describes a fresh supported aim estimate. ``measure=False``
    keeps the off/Ctrl UI wake path free of aim, descriptor and replay reads.
    """

    def __init__(self, bigworld=None, gui=None, interface_scale_getter=None,
                 replay_getter=None):
        self._bigworld = bigworld
        self._gui = gui
        self._interface_scale_getter = interface_scale_getter or self._interface_scale
        self._replay_getter = replay_getter or self._is_replay
        self._last_interface_scale = 1.0

    @staticmethod
    def _interface_scale():
        from helpers import dependency
        from skeletons.gui.impl import IGuiLoader
        return dependency.instance(IGuiLoader).scale

    @staticmethod
    def _is_replay():
        replay = _load_module('BattleReplay')
        # A missing game module is normal in offline adapter tests.
        if replay is None:
            return False
        return _flag(getattr(getattr(replay, 'g_replayCtrl', None), 'isPlaying', None))

    def _base(self):
        return {'context': 'unavailable', 'battle_eligible': False,
                'available': False, 'reason': 'player_unavailable',
                'mode': 'unknown', 'remaining_s': None, 'kind': 'none',
                'aim_position': None, 'aim_offset': None,
                'viewport': (0, 0), 'scale': self._last_interface_scale}

    def _common(self, result):
        if self._bigworld is None:
            self._bigworld = _load_module('BigWorld')
        if self._gui is None:
            self._gui = _load_module('GUI')
        try:
            resolution = _pair(self._gui.screenResolution())
            if resolution and all(0 < item <= 65536 for item in resolution):
                result['viewport'] = tuple(int(item) for item in resolution)
        except Exception:
            pass
        try:
            scale = _number(self._interface_scale_getter())
            if scale is not None and 0.1 <= scale <= 16.0:
                result['scale'] = scale
                self._last_interface_scale = scale
        except Exception:
            pass

    @staticmethod
    def _is_account(player):
        cls = type(player)
        return (getattr(cls, '__module__', None) == 'Account' and
                getattr(cls, '__name__', None) == 'PlayerAccount')

    @staticmethod
    def _visual_state(entity):
        try:
            in_world = _flag(getattr(entity, 'inWorld', None))
            started = _flag(getattr(entity, 'isStarted', None))
            hidden = _flag(getattr(entity, 'isHidden', None))
        except Exception:
            return 'unknown'
        if in_world is None or started is None or hidden is None:
            return 'unknown'
        return 'visible' if in_world and started and not hidden else 'hidden'

    @staticmethod
    def _ui_context(crosshair, result):
        if crosshair is None:
            return
        try:
            position = _pair(crosshair.getPosition())
            if position and all(abs(item) <= 65536 for item in position):
                result['aim_position'] = position
                # Pixel coordinates are the HUD's primary anchor. The clip
                # offset is only a fallback, so do not query it as well.
                return
        except Exception:
            pass
        try:
            offset = _pair(crosshair.getOffset())
            if offset and all(-1.0 <= item <= 1.0 for item in offset):
                result['aim_offset'] = offset
        except Exception:
            pass

    def _same_context(self, player, arena, handler, attached, own_id, mode):
        return (self._bigworld.player() is player and
                getattr(player, 'arena', None) is arena and
                player.inputHandler is handler and
                _mode(handler.ctrlModeName) == mode and
                _flag(handler.isStarted) is True and
                _flag(player.isVehicleAlive) is True and
                _flag(player.isObserver()) is False and
                _entity_id(player.playerVehicleID) == own_id and
                player.getVehicleAttached() is attached and
                _entity_id(getattr(attached, 'id', None)) == own_id and
                self._visual_state(attached) == 'visible')

    def poll(self, measure=True):
        result = self._base()
        self._common(result)
        try:
            player = self._bigworld.player()
        except Exception:
            return result
        if player is None:
            return result
        if self._is_account(player):
            result.update(context='garage', reason='garage')
            return result
        try:
            arena = getattr(player, 'arena', None)
        except Exception:
            result['reason'] = 'context_unavailable'
            return result
        if arena is None:
            result['reason'] = 'context_unavailable'
            return result
        result['context'] = 'battle'
        try:
            handler = player.inputHandler
            result['mode'] = _mode(handler.ctrlModeName)
            crosshair = player.guiSessionProvider.shared.crosshair
            self._ui_context(crosshair, result)
        except Exception:
            result['reason'] = 'controllers_unavailable'
            return result
        if result['mode'] not in SUPPORTED_MODES:
            result['reason'] = 'unsupported_mode'
            return result
        try:
            if _flag(handler.isStarted) is not True:
                result['reason'] = 'input_not_ready'
                return result
            if _flag(player.isVehicleAlive) is not True:
                result['reason'] = 'own_vehicle_not_alive'
                return result
            if _flag(player.isObserver()) is not False:
                result['reason'] = 'spectator'
                return result
            own_id = _entity_id(player.playerVehicleID)
            attached = player.getVehicleAttached()
            if (own_id is None or attached is None or
                    _entity_id(getattr(attached, 'id', None)) != own_id):
                result['reason'] = 'not_own_vehicle'
                return result
            if self._visual_state(attached) != 'visible':
                result['reason'] = 'own_vehicle_not_ready'
                return result
        except Exception:
            result['reason'] = 'vehicle_context_unavailable'
            return result
        result['battle_eligible'] = True
        if not measure:
            result['reason'] = 'measurement_disabled'
            return result
        try:
            replay = _flag(self._replay_getter())
            if replay is not False:
                result['reason'] = 'replay_unsupported'
                return result
            descriptor = getattr(attached, 'typeDescriptor', None)
            dual_accuracy = _flag(getattr(descriptor, 'hasDualAccuracy', None))
            if dual_accuracy is not False:
                result['reason'] = ('dual_accuracy_unsupported' if dual_accuracy else
                                    'aim_state_unavailable')
                return result

            # The native gun update already clamped F against its movement floor.
            # Never call getOwnVehicleShotDispersionAngle or extrapolate F down:
            # either could incorrectly bypass that current movement floor.
            latest = getattr(player, '_PlayerAvatar__latestAimingInfo', None)
            dispersion = getattr(player, '_PlayerAvatar__dispersionInfo', None)
            if (type(latest) not in (tuple, list) or len(latest) != 4 or
                    type(dispersion) not in (tuple, list) or len(dispersion) != 6):
                result['reason'] = 'aim_state_unavailable'
                return result
            latest = tuple(_number(value) for value in latest)
            dispersion = tuple(_number(value) for value in dispersion)
            if (any(value is None for value in latest + dispersion) or
                    any(value < 0 for value in latest + dispersion)):
                result['reason'] = 'aim_state_invalid'
                return result
            if (dispersion == _DISPERSION_PLACEHOLDER or
                    latest[0] <= 0 or latest[1] <= 0):
                result['reason'] = 'aim_state_uninitialized'
                return result
            now = _number(self._bigworld.time())
            if now is None or not 0 <= now - latest[0] <= MAX_SNAPSHOT_AGE:
                result['reason'] = 'aim_state_stale'
                return result
            remaining = estimate_remaining(latest[1], dispersion[0], dispersion[5])
            if remaining is None:
                result['reason'] = 'aim_state_invalid'
                return result
            if (not self._same_context(player, arena, handler, attached, own_id,
                                       result['mode']) or
                    getattr(attached, 'typeDescriptor', None) is not descriptor):
                result['battle_eligible'] = False
                result['reason'] = 'context_changed'
                return result
            result.update(available=True, reason='ok', remaining_s=remaining,
                          kind='aim')
            return result
        except Exception:
            result['reason'] = 'measurement_failed'
            return result


ClientProbe = BattleProbe
