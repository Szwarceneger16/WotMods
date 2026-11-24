# -*- coding: utf-8 -*-
"""Artillery preview's stock resource and shell-indicator boundary."""
from __future__ import absolute_import

from contextlib import contextmanager
import sys
import types
import unittest

from test_native_scene import MODULES, Value


@contextmanager
def localized_shells(dyn, text):
    names = ('gui', 'gui.impl', 'gui.impl.gen')
    previous = dict((name, sys.modules.get(name)) for name in names)
    try:
        gui, impl, gen = (types.ModuleType(name) for name in names)
        sys.modules.update(zip(names, (gui, impl, gen)))
        gui.impl, impl.gen = impl, gen
        impl.backport = Value()
        impl.backport.text = text
        gen.R = Value()
        gen.R.strings = Value()
        gen.R.strings.item_types = Value()
        gen.R.strings.item_types.shell = Value()
        abbreviation = Value()
        abbreviation.dyn = dyn
        gen.R.strings.item_types.shell.kindsAbbreviation = abbreviation
        yield
    finally:
        for name, module in previous.items():
            if module is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = module


class ArtilleryFlash(object):
    def __init__(self):
        self.flashObject = Value()
        self.preview_markers = []
        self.indicators = None
        self.flight_times = None

    def as_setSettingsS(self, settings):
        pass

    def as_setViewS(self, view_id, style_id):
        pass

    def as_createGunMarkerS(self, view_id, linkage, name):
        return True

    def as_setGunMarkersIndicatorsS(self, indicators):
        self.indicators = indicators

    def as_setShotFlyTimesS(self, flight_times):
        self.flight_times = flight_times


class ArtilleryIndicators(unittest.TestCase):
    def test_calls_stock_resource_to_get_numeric_id(self):
        by_kind = {'HIGH_EXPLOSIVE': 10, 'ARMOR_PIERCING': 20}
        translated = {10: u'OB', 20: u'PP'}

        def dyn(kind):
            return lambda: by_kind[kind]

        with localized_shells(dyn, translated.__getitem__):
            for _, native, _ in MODULES:
                flash = ArtilleryFlash()
                native._sample_arty_indicators(flash)
                self.assertEqual([u'OB', u'PP'], [entry[b'shellTypeName'] for entry in flash.indicators])
                self.assertEqual([1, 2], [entry[b'shellIntCD'] for entry in flash.indicators])
                self.assertEqual([1, 2], [entry[b'shellIntCD'] for entry in flash.flight_times])
                self.assertEqual([1.85, -1.0], [entry[b'flyTime'] for entry in flash.flight_times])

    def test_translation_failure_still_submits_indicators(self):
        def invalid_text(resource_id):
            raise TypeError('Cannot translate resource')

        with localized_shells(lambda _: lambda: 10, invalid_text):
            for _, native, _ in MODULES:
                flash = ArtilleryFlash()
                native._sample_arty_indicators(flash)
                self.assertEqual([b'HE', b'AP'], [entry[b'shellTypeName'] for entry in flash.indicators])
                self.assertIsNotNone(flash.flight_times)

    def test_indicator_bridge_failure_keeps_the_artillery_marker(self):
        def bridge_failure(_):
            raise RuntimeError('Optional artillery indicator rejected')

        for _, native, _ in MODULES:
            renderer = native.PreviewRenderer()
            flash = ArtilleryFlash()
            flash.as_setGunMarkersIndicatorsS = bridge_failure
            renderer._flash = flash
            renderer._show_arty_indicators = True
            renderer._spec = ('arty', 'standard', {'id': 'standard', 'marker': 'standard', 'reload_type': 0},
                              (1920, 1080, 1), {'scene_id': 'arty_top', 'step': 2})
            renderer._geometry = lambda unused=True: None
            renderer._scene_zoom = lambda: None
            original_marker, original_sample = native._marker_linkage, native._sample_state
            core_samples = []
            try:
                native._marker_linkage = lambda selected, mode: 'stock'
                native._sample_state = lambda selected_flash, selected, hidden: core_samples.append(selected_flash)
                renderer._apply()
                renderer._publish_readiness()
            finally:
                native._marker_linkage, native._sample_state = original_marker, original_sample
            self.assertEqual([flash], core_samples)
            self.assertIs(renderer._flash, flash)
            self.assertEqual([native.MARKER_NAME], flash.preview_markers)
            self.assertEqual(('partial', 'artillery-indicators-unavailable'), (renderer.status, renderer.reason))


if __name__ == '__main__':
    unittest.main()
