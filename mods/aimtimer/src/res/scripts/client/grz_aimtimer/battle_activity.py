# -*- coding: ascii -*-
"""Subscribe to the live avatar's public battle events for the owned HUD."""
from __future__ import absolute_import


def _watch(runtime, source, name, callback):
    try:
        event = getattr(source, name, None)
        if event is not None:
            event += callback
            runtime.battle_events.append((event, callback))
    except Exception:
        # The regular, low-frequency visibility check remains available.
        pass


def unbind(runtime):
    while runtime.battle_events:
        event, callback = runtime.battle_events.pop()
        try:
            event -= callback
        except Exception:
            pass


def bind(runtime):
    unbind(runtime)
    avatar, arena = runtime._avatar, runtime._arena
    if arena is None:
        return
    _watch(runtime, arena, 'onVehicleKilled', runtime._vehicle_destroyed)
    _watch(runtime, avatar, 'onVehicleEnterWorld', runtime._own_vehicle_visibility_changed)
    _watch(runtime, avatar, 'onVehicleLeaveWorld', runtime._own_vehicle_visibility_changed)
    try:
        from PlayerEvents import g_playerEvents
        _watch(runtime, g_playerEvents, 'onArenaPeriodChange', runtime._battle_wakeup)
        _watch(runtime, g_playerEvents, 'onAvatarReady', runtime._ready_wakeup)
    except ImportError:
        pass
    try:
        handler = avatar.inputHandler
        crosshair = avatar.guiSessionProvider.shared.crosshair
    except (AttributeError, RuntimeError):
        return
    _watch(runtime, handler, 'onControlModeChanged', runtime._battle_wakeup)
    _watch(runtime, crosshair, 'onCrosshairViewChanged', runtime._battle_wakeup)
    _watch(runtime, crosshair, 'onStrategicCameraChanged', runtime._battle_wakeup)
    _watch(runtime, crosshair, 'onCrosshairPositionChanged', runtime._position_changed)
