# -*- coding: ascii -*-
"""Read-only client adapter for the private rangefinder.

Artillery uses the client's cached gun marker and its distance convention.
Other cameras measure the first scene intersection along the view ray.
Distances originate at the own vehicle reference point. Only plain HUD data
leaves this adapter. No entity or world position is cached.
"""
from __future__ import absolute_import

import math

try:
    _INTEGER_TYPES = (int, long)
    _TEXT_TYPES = (str, unicode)
except NameError:
    _INTEGER_TYPES = (int,)
    _TEXT_TYPES = (str, bytes)

_NUMBER_TYPES = _INTEGER_TYPES + (float,)
ARTILLERY_MODES = ('strategic', 'arty')
SUPPORTED_MODES = ('arcade', 'sniper', 'strategic', 'arty', 'dualgun', 'twinGun')
_OTHER_MODES = ('postmortem', 'debug', 'video', 'mapcase', 'arcadeMapcase',
                'epicMapcase', 'respawn', 'deathfreecam', 'killcam',
                'vehiclesSelection', 'lookAtKiller', 'smStrategic',
                'smEntityView', 'prebattleHighlights',
                'arcadeEpicMinefieldMapcase')
MAX_RAY_DISTANCE = 10000.0
_MAX_COORDINATE = 10000000.0


def _number(value):
    if type(value) not in _NUMBER_TYPES:
        return None
    try:
        result = float(value)
    except (ValueError, TypeError, OverflowError):
        return None
    if math.isnan(result) or math.isinf(result):
        return None
    return result


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
    if first is None or second is None:
        return None
    return (first, second)


def _coords(value):
    try:
        if type(value) in (tuple, list):
            if len(value) != 3:
                return None
            values = value
        else:
            values = (value.x, value.y, value.z)
        result = tuple(_number(component) for component in values)
        if any(component is None or abs(component) > _MAX_COORDINATE
               for component in result):
            return None
        return result
    except Exception:
        return None


def _distance(first, second):
    try:
        result = math.sqrt(sum((first[i] - second[i]) ** 2 for i in range(3)))
    except (ValueError, OverflowError, TypeError):
        return None
    return _number(result)


def _load_module(name):
    try:
        return __import__(name, fromlist=['__name__'])
    except Exception:
        return None


class ClientProbe(object):
    """Small injectable bridge; poll performs at most one scene ray query.

    ``battle_eligible`` identifies a valid own-vehicle targeting context.
    ``available`` identifies a valid numeric distance, and is false when
    measurement is disabled, no intersection exists, or a read fails.
    ``measure=False`` is the UI-wake path: it does not resolve scene bindings,
    get an origin, construct a ray, collide, inspect targets or compute range.
    ``artillery_measure=False`` leaves both artillery modes to the client HUD.
    """

    def __init__(self, bigworld=None, gui=None, ray_getter=None, collide=None,
                 vector_factory=None, interface_scale_getter=None):
        self._bigworld = bigworld
        self._gui = gui
        self._ray_getter = ray_getter
        self._collide = collide
        self._prefer_native = collide is None
        self._native_collide = None
        self._vector_factory = vector_factory
        self._interface_scale_getter = interface_scale_getter or self._interface_scale
        self._last_interface_scale = 1.0

    @staticmethod
    def _interface_scale():
        from helpers import dependency
        from skeletons.gui.impl import IGuiLoader
        return dependency.instance(IGuiLoader).scale

    def _base(self):
        return {'context': 'unavailable', 'battle_eligible': False,
                'available': False, 'reason': 'player_unavailable',
                'mode': 'unknown', 'distance_m': None, 'kind': 'none',
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

    def _measurement_bindings(self):
        if self._ray_getter is None:
            cameras = _load_module('AvatarInputHandler.cameras')
            self._ray_getter = getattr(cameras, 'getWorldRayAndPoint', None)
        if self._prefer_native and self._native_collide is None:
            native = getattr(self._bigworld, 'wg_collideDynamicStatic', None)
            if callable(native) and callable(getattr(self._bigworld, 'entity', None)):
                self._native_collide = native
            else:
                self._prefer_native = False
        if self._native_collide is None and self._collide is None:
            projectile = _load_module('ProjectileMover')
            self._collide = getattr(projectile, 'collideDynamicAndStatic', None)
        if self._vector_factory is None:
            math_module = _load_module('Math')
            self._vector_factory = getattr(math_module, 'Vector3', None)
        return all(callable(item) for item in (self._ray_getter,
                   self._native_collide or self._collide, self._vector_factory))

    @staticmethod
    def _is_account(player):
        # Account is the known garage player class, not any non-avatar object.
        cls = type(player)
        return (getattr(cls, '__module__', None) == 'Account' and
                getattr(cls, '__name__', None) == 'PlayerAccount')

    @staticmethod
    def _visual_state(entity):
        """Return explicit status; absence of visibility evidence is not visible."""
        try:
            in_world = _flag(getattr(entity, 'inWorld', None))
            started = _flag(getattr(entity, 'isStarted', None))
            hidden = _flag(getattr(entity, 'isHidden', None))
        except Exception:
            return 'unknown'
        if in_world is None or started is None or hidden is None:
            return 'unknown'
        if hidden or not in_world or not started:
            return 'hidden'
        return 'visible'

    @staticmethod
    def _ui_context(crosshair, result, need_ray=False):
        if crosshair is None:
            return
        try:
            position = _pair(crosshair.getPosition())
            if position and all(abs(item) <= 65536 for item in position):
                result['aim_position'] = position
                # Pixel anchoring is sufficient for UI-only wake/drag polls.
                # Numeric distance sampling still needs the exact native clip
                # offset for getWorldRayAndPoint; never reconstruct that ray
                # from potentially delayed display coordinates.
                if not need_ray:
                    return
        except Exception:
            pass
        try:
            offset = _pair(crosshair.getOffset())
            if offset and all(-1.0 <= item <= 1.0 for item in offset):
                result['aim_offset'] = offset
        except Exception:
            pass

    def _stock_marker_distance(self, player, result):
        try:
            # Same cached inputs and integer meter convention as
            # AimDistancePlugin's getDistanceToGunMarker call. During
            # transitions the marker can be absent. Avoid the stock helper's
            # warning path in that case and leave the distance unavailable.
            origin = _coords(player.getOwnVehiclePosition())
            marker_info = player.gunRotator.markerInfo
            marker = _coords(marker_info[0])
            initial = (marker == (0.0, 0.0, 0.0) and len(marker_info) >= 3 and
                       _coords(marker_info[1]) == (0.0, 1.0, 0.0) and marker_info[2] == 1.0)
            distance = None if initial else _distance(origin, marker)
            if distance is not None and distance >= 1.0:
                return int(distance), 'surface'
        except (AttributeError, IndexError, KeyError, TypeError):
            pass
        result['reason'] = 'stock_marker_unavailable'
        return None

    def _disable_native_collision(self):
        # Use the stock compatibility adapter from the next sample onward.
        # Falling back within this sample would issue a second scene query.
        self._native_collide = None
        self._prefer_native = False

    def _distance_from_hit(self, result, hit, direct, start, direction, origin, own_id):
        if hit is None:
            result['reason'] = 'no_intersection'
            return None
        if direct:
            is_vehicle = _flag(hit[1]) if type(hit) in (tuple, list) and len(hit) >= 2 else None
            if is_vehicle is None or (is_vehicle and len(hit) < 3):
                self._disable_native_collision()
                result['reason'] = 'collision_data_unavailable'
                return None
            target = None
            if is_vehicle:
                target_id = _entity_id(hit[2])
                if target_id is None:
                    self._disable_native_collision()
                    result['reason'] = 'collision_data_unavailable'
                    return None
                target = self._bigworld.entity(target_id)
        else:
            if type(hit) not in (tuple, list) or len(hit) != 2:
                result['reason'] = 'intersection_unavailable'
                return None
            collision_data = hit[1]
            is_vehicle = False if collision_data is None else _flag(collision_data.isVehicle())
            if is_vehicle is None:
                result['reason'] = 'collision_data_unavailable'
                return None
            target = collision_data.entity if is_vehicle else None
        hit_position = _coords(hit[0])
        if hit_position is None:
            result['reason'] = 'intersection_unavailable'
            return None
        delta = tuple(hit_position[i] - start[i] for i in range(3))
        along = sum(delta[i] * direction[i] for i in range(3))
        perpendicular = _distance(delta, tuple(along * item for item in direction))
        tolerance = max(0.05, abs(along) * 1e-5)
        if (along < -tolerance or along > MAX_RAY_DISTANCE + tolerance or
                perpendicular is None or perpendicular > tolerance):
            result['reason'] = 'intersection_outside_ray'
            return None
        kind = 'surface'
        measure_position = hit_position
        if is_vehicle:
            target_id = _entity_id(getattr(target, 'id', None))
            if target_id is None or (direct and target_id != hit[2]):
                result['reason'] = 'target_unavailable'
                return None
            if target_id == own_id:
                result['reason'] = 'own_vehicle_intersection'
                return None
            if self._visual_state(target) != 'visible':
                result['reason'] = 'target_visibility_unavailable'
                return None
            alive = _flag(target.isAlive())
            if alive is None:
                result['reason'] = 'target_state_unavailable'
                return None
            if alive:
                measure_position = _coords(target.position)
                if measure_position is None:
                    result['reason'] = 'target_position_unavailable'
                    return None
                kind = 'vehicle'
        distance = _distance(origin, measure_position)
        if distance is None:
            result['reason'] = 'distance_unavailable'
            return None
        return distance, kind

    def _ray_distance(self, player, result, own_id):
        if result['aim_offset'] is None:
            result['reason'] = 'aim_unavailable'
            return None
        if not self._measurement_bindings():
            result['reason'] = 'measurement_api_unavailable'
            return None
        origin = _coords(player.getOwnVehiclePosition())
        if origin is None:
            result['reason'] = 'origin_unavailable'
            return None
        ray_value, start_value = self._ray_getter(*result['aim_offset'])
        ray, start = _coords(ray_value), _coords(start_value)
        if ray is None or start is None:
            result['reason'] = 'ray_unavailable'
            return None
        ray_length = _distance(ray, (0.0, 0.0, 0.0))
        if ray_length is None or ray_length <= 1e-12:
            result['reason'] = 'ray_unavailable'
            return None
        direction = tuple(item / ray_length for item in ray)
        end = tuple(start[i] + direction[i] * MAX_RAY_DISTANCE for i in range(3))
        start_vector, end_vector = self._vector_factory(*start), self._vector_factory(*end)
        direct = self._native_collide is not None
        space_id = getattr(player, 'spaceID', None) if direct else None
        if direct and (type(space_id) not in _INTEGER_TYPES or space_id < 0):
            result['reason'] = 'measurement_api_unavailable'
            return None
        try:
            if direct:
                # Match the stock ProjectileMover flags and excluded own ID.
                # The native result supplies the hit point, vehicle flag and
                # optional entity ID. Armor/material fields are irrelevant.
                hit = self._native_collide(space_id, start_vector, end_vector, 128, own_id, -1, 0)
            else:
                hit = self._collide(start_vector, end_vector, (own_id,), 128)
        except TypeError:
            if direct:
                self._disable_native_collision()
            raise
        return self._distance_from_hit(result, hit, direct, start, direction, origin, own_id)

    def poll(self, measure=True, artillery_measure=True):
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
            self._ui_context(crosshair, result,
                             need_ray=measure and result['mode'] not in ARTILLERY_MODES)
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
        if result['mode'] in ARTILLERY_MODES and not artillery_measure:
            result['reason'] = 'artillery_native_display'
            return result
        try:
            reading = (self._stock_marker_distance(player, result)
                       if result['mode'] in ARTILLERY_MODES else
                       self._ray_distance(player, result, own_id))
            if reading is None:
                return result
            # An arena/player switch during a native read must not display old
            # geometry. The timer's broader generation guard belongs to runtime.
            if (self._bigworld.player() is not player or
                    getattr(player, 'arena', None) is not arena or
                    player.inputHandler is not handler or
                    _mode(handler.ctrlModeName) != result['mode'] or
                    _flag(player.isVehicleAlive) is not True):
                result['battle_eligible'] = False
                result['reason'] = 'context_changed'
                return result
            result.update(available=True, reason='ok', distance_m=reading[0], kind=reading[1])
            return result
        except Exception:
            result['reason'] = 'measurement_failed'
            return result
