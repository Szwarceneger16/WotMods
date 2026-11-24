# -*- coding: ascii -*-
from __future__ import absolute_import

import unittest

from test_native_scene import MODULES, Value


class Crosshair(object):
    def __init__(self, visibility):
        self.distance = Value()
        self.distance.visible = visibility
        self.visible = True


class Panel(object):
    def __init__(self, *children):
        self.flashObject = self
        self.numChildren = len(children)
        self.getChildAt = children.__getitem__


class StockDistanceTest(unittest.TestCase):
    def test_restores_only_the_distance_clips_it_hid(self):
        if not any(native.__package__ == 'grz_rangefinder' for _, native, _ in MODULES):
            self.skipTest('The live stock visibility option belongs to Rangefinder')
        from grz_rangefinder import stock_rangefinder
        arcade, sniper, disabled, new_arty = (Crosshair(True), Crosshair(True),
                                             Crosshair(False), Crosshair(True))
        app = Value()
        app.panel = Panel(arcade, Value(), sniper, disabled)
        previous_lookup = stock_rangefinder._stock_crosshair
        stock_rangefinder._stock_crosshair = lambda app: app.panel
        self.addCleanup(setattr, stock_rangefinder, '_stock_crosshair', previous_lookup)
        visibility = stock_rangefinder.StockRangefinder()
        self.assertTrue(visibility.suppress(app))
        self.assertTrue(visibility.suppress(app))
        self.assertFalse(arcade.distance.visible)
        self.assertFalse(sniper.distance.visible)
        self.assertTrue(arcade.visible)
        self.assertTrue(sniper.visible)

        app.panel = Panel(new_arty)
        self.assertTrue(visibility.suppress(app))
        self.assertTrue(arcade.distance.visible)
        self.assertTrue(sniper.distance.visible)
        self.assertFalse(disabled.distance.visible)
        self.assertFalse(new_arty.distance.visible)
        self.assertFalse(visibility.suppress(None))
        self.assertTrue(new_arty.distance.visible)

    def test_both_native_previews_use_the_stock_hide_and_show_calls(self):
        for _, native, _ in MODULES:
            flash = Value()
            calls = []
            flash.as_clearDistanceS = lambda instant: calls.append(('clear', instant))
            flash.as_setDistanceS = lambda label: calls.append(('set', label))
            original = native._distance_text
            native._distance_text = lambda meters: '%d m' % meters
            try:
                native._sample_distance(flash, True)
                native._sample_distance(flash, False)
                self.assertEqual([('clear', True), ('set', '250 m')], calls)
            finally:
                native._distance_text = original
