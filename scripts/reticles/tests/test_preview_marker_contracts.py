# -*- coding: ascii -*-
"""Check structural visibility against stock marker layouts without a game client."""
from __future__ import absolute_import

import unittest

from test_native_scene import MODULES


class Display(object):
    def __init__(self, visible=True, **symbols):
        self.visible = visible
        self.alpha = 1
        self.width = self.height = 20
        self.__dict__.update(symbols)


class Root(object):
    def __init__(self, markers):
        self.markers = markers

    def getChildAt(self, index):
        return Display()

    def getChildByName(self, name):
        return self.markers[name]


class Flash(object):
    def __init__(self, markers):
        self.flashObject = Root(markers)
        self.preview_markers = sorted(markers)

    def _isDAAPIInited(self):
        return True


class MarkerContracts(unittest.TestCase):
    def renderer(self, native, family, identifier, primary, mixing=1, secondary=None):
        renderer = native.PreviewRenderer()
        renderer._spec = ('arcade', identifier, {'marker': family, 'id': identifier, 'reload_type': 0},
                          (1920, 1080, 1), {})
        markers = {'main': primary}
        if secondary is not None:
            markers['secondary'] = secondary
        renderer._flash = Flash(markers)
        renderer._settings = {1: {b'centerAlphaValue': 1, b'gunTagAlpha': 1, b'mixingAlpha': mixing}}
        return renderer

    def test_alternate_native_shapes_do_not_depend_on_default_symbol(self):
        variants = (('twingun', 'twingun', 'twinGunMixing'),
                    ('accuracy_stacks', 'accuracy_stacks', 'accuracyGunMixing'),
                    ('low_charge_shot', 'low_charge_shot', 'lowChargeShotMixingMC'),
                    ('charge_shot', 'charge_shot', 'chargeGunMixing'),
                    ('standard', 'chargeable_burst', 'chargeableBurst'))
        for _, native, _ in MODULES:
            for family, identifier, symbol in variants:
                radius = Display(currMixingMC=Display(False))
                setattr(radius, symbol, Display())
                renderer = self.renderer(native, family, identifier, Display(radiusMC=radius))
                self.assertTrue(renderer._visible_marker_variant(), symbol)
                getattr(radius, symbol).visible = False
                radius.currMixingMC.visible = True
                self.assertFalse(renderer._visible_marker_variant(), symbol)

    def test_rocket_replaces_circle_and_secondary_has_no_tag(self):
        for _, native, _ in MODULES:
            circle = Display()
            rocket = Display(gunTagRocket=Display(tag=Display(circle=circle)), radiusMC=Display(False))
            renderer = self.renderer(native, 'auxiliary_rocket_launcher', 'auxiliary_rocket_launcher', rocket)
            self.assertTrue(renderer._visible_marker_variant())
            # The launcher has its own tag visibility even with ordinary art disabled.
            renderer._settings[1].update({b'gunTagAlpha': 0, b'mixingAlpha': 0})
            self.assertTrue(renderer._visible_marker_variant())
            circle.visible = False
            self.assertFalse(renderer._visible_marker_variant())
            circle.visible = True
            rocket.visible = False
            self.assertFalse(renderer._visible_marker_variant())
            renderer = self.renderer(native, 'dual_accuracy', 'dual_accuracy', Display(),
                                     mixing=0, secondary=Display(False))
            self.assertTrue(renderer._visible_marker_variant())

    def test_rocket_aiming_is_applied_after_stock_marker_configuration(self):
        for _, native, _ in MODULES:
            tag = Display(False, circle=Display())
            rocket = Display(gunTagRocket=Display(tag=tag), radiusMC=Display())
            renderer = self.renderer(native, 'auxiliary_rocket_launcher', 'auxiliary_rocket_launcher', rocket)
            flash = renderer._flash
            calls = []

            def set_active(active):
                calls.append(('aiming', active))
                tag.visible = active

            flash.as_setAuxiliaryRocketLauncherActiveS = set_active
            flash.as_setNetTypeS = lambda value: calls.append(('net-type', value))
            flash.as_setReloadingCounterShownS = lambda value: calls.append(('reload-counter', value))
            renderer._prepared = True
            renderer._queue_wait = lambda: None
            self.assertFalse(renderer._visible_marker_variant())
            renderer._wait()
            self.assertEqual([('aiming', True), ('net-type', 6), ('reload-counter', False)], calls)
            self.assertTrue(renderer._visible_marker_variant())

    def test_unverified_alternate_art_does_not_release_working_base(self):
        for _, native, _ in MODULES:
            renderer = self.renderer(native, 'twingun', 'twingun', Display())
            flash = renderer._flash
            renderer._prepared = renderer._finalized = True
            renderer._visible_cassette = lambda: True
            renderer._visual_samples = 7
            renderer._wait()
            self.assertEqual(('partial', 'marker-unverified'), (renderer.status, renderer.reason))
            self.assertIs(renderer._flash, flash)


if __name__ == '__main__':
    unittest.main()
