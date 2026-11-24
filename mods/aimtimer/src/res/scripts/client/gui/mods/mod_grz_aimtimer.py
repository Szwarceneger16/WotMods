# -*- coding: ascii -*-
"""GRZ AimTimer private build 0.1.7; isolated from all other mods."""
from __future__ import absolute_import

_runtime = None


def get_editor_readout_v1(mode):
    """Offer a passive snapshot of saved HUD settings to the other GRZ editor."""
    current = _runtime
    if current is None or not current.running or mode not in ('arcade', 'sniper', 'arty'):
        return None
    from grz_aimtimer.core import mode_position
    config = current.store.data
    x, y = mode_position(config, mode)
    return {'x': x, 'y': y, 'enabled': config['enabled'],
            'hud_font_px': config['hud_font_px'],
            'hud_background_opacity': config['hud_background_opacity'],
            'hud_frame_scale_pct': config['hud_frame_scale_pct']}


def init():
    global _runtime
    if _runtime is not None:
        return
    try:
        from grz_aimtimer.runtime import create_runtime
        _runtime = create_runtime()
        _runtime.start()
    except Exception:
        print('[GRZ AimTimer] Startup unavailable; game initialization continues.')
        fini()


def fini():
    global _runtime
    current, _runtime = _runtime, None
    if current is not None:
        try:
            current.stop()
        except Exception:
            print('[GRZ AimTimer] Cleanup incomplete; no game methods were patched.')
        finally:
            close_log = getattr(current.log, 'close', None)
            if callable(close_log):
                close_log()
