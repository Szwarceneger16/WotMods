# -*- coding: ascii -*-
from __future__ import absolute_import

import json
import os
import sys
import types
import unittest

from test_native_scene import MODULES, MOD_ROOT, Value


class PeerReadoutTest(unittest.TestCase):
    @staticmethod
    def _window(views):
        window = views.SettingsWindow(lambda arg: None, lambda: '{}')
        window._editor_active = True
        return window

    @staticmethod
    def _snapshot(window):
        return json.loads(window._payload())['editor_peer_readout']

    def _registered_peer(self, mod):
        name = 'gui.mods.mod_grz_' + mod
        old = sys.modules.pop(name, None)
        if old is None:
            self.addCleanup(sys.modules.pop, name, None)
        else:
            self.addCleanup(sys.modules.__setitem__, name, old)
        return name

    @staticmethod
    def _load_peer(mod, name):
        source = os.path.join(MOD_ROOT, mod, 'src', 'res', 'scripts', 'client', 'gui', 'mods',
                              'mod_grz_' + mod + '.py')
        module = types.ModuleType(name)
        if os.path.isfile(source):
            with open(source, 'rb') as reader:
                eval(compile(reader.read(), 'peer_entry.py', 'exec'), module.__dict__)
        else:
            # The optional peer can be absent from this branch. Model its public
            # snapshot contract without requiring it as a test dependency.
            def get_editor_readout_v1(mode):
                runtime = module._runtime
                if runtime is None or not runtime.running:
                    return None
                config = runtime.store.data
                fields = ('enabled', 'hud_font_px', 'hud_background_opacity', 'hud_frame_scale_pct')
                snapshot = dict((field, config[field]) for field in fields)
                for axis in ('x', 'y'):
                    snapshot[axis] = config['hud_offset_' + mode + '_' + axis]
                if mod == 'rangefinder':
                    snapshot['hide_stock_rangefinder'] = config['hide_stock_rangefinder']
                return snapshot
            module._runtime = None
            module.get_editor_readout_v1 = get_editor_readout_v1
        sys.modules[name] = module
        return module

    def test_uses_saved_camera_positions_from_loaded_peer_and_never_requires_it(self):
        for _, _, views in MODULES:
            mod = 'aimtimer' if views.__package__ == 'grz_rangefinder' else 'rangefinder'
            name = self._registered_peer(mod)
            window = self._window(views)
            self.assertIsNone(self._snapshot(window))
            self.assertNotIn(name, sys.modules)

            peer = self._load_peer(mod, name)
            self.assertIsNone(self._snapshot(window))
            config = dict(enabled=True, hide_stock_rangefinder=True, hud_font_px=22,
                          hud_background_opacity=0.45, hud_frame_scale_pct=120,
                          hud_offset_arcade_x=-91, hud_offset_arcade_y=72,
                          hud_offset_sniper_x=157, hud_offset_sniper_y=-49,
                          hud_offset_arty_x=37, hud_offset_arty_y=283, extra_private='not transferred')
            peer._runtime = Value()
            peer._runtime.running = True
            peer._runtime.store = Value()
            peer._runtime.store.data = config
            for mode, x, y in (('arcade', -91, 72), ('sniper', 157, -49), ('arty', 37, 283)):
                window._preview_mode = mode
                expected = {
                    'x': x, 'y': y, 'enabled': True, 'hud_font_px': 22,
                    'hud_background_opacity': 0.45, 'hud_frame_scale_pct': 120}
                if mod == 'rangefinder':
                    expected['hide_stock_rangefinder'] = True
                self.assertEqual(self._snapshot(window), expected)

            config['enabled'] = False
            disabled = self._snapshot(window)
            self.assertEqual((disabled['x'], disabled['y'], disabled['enabled']), (37, 283, False))
            peer._runtime.running = False
            self.assertIsNone(self._snapshot(window))
            self.assertEqual(config['extra_private'], 'not transferred')

    def test_inactive_editor_skips_lookup_and_malformed_peer_is_optional(self):
        for _, _, views in MODULES:
            mod = 'aimtimer' if views.__package__ == 'grz_rangefinder' else 'rangefinder'
            name = self._registered_peer(mod)
            window = self._window(views)
            peer = types.ModuleType(name)
            sys.modules[name] = peer
            self.assertIsNone(self._snapshot(window))

            calls = []

            def invalid(mode):
                calls.append(mode)
                return dict(x=0, y=float('nan'), enabled=True, hud_font_px=22,
                            hud_background_opacity=0.5, hud_frame_scale_pct=120)

            peer.get_editor_readout_v1 = invalid
            window._editor_active = False
            self.assertIsNone(self._snapshot(window))
            self.assertEqual(calls, [])
            window._editor_active = True
            self.assertIsNone(self._snapshot(window))
            self.assertEqual(calls, ['arcade'])
