# -*- coding: ascii -*-
from __future__ import absolute_import

import unittest

from test_native_scene import MODULES, Value

HAS_RANGEFINDER = any(native.__package__ == 'grz_rangefinder' for _, native, _ in MODULES)
if HAS_RANGEFINDER:
    from grz_rangefinder import stock_rangefinder


class Event(object):
    def __init__(self):
        self.listeners = []

    def __iadd__(self, listener):
        self.listeners.append(listener)
        return self

    def __isub__(self, listener):
        self.listeners.remove(listener)
        return self

    def emit(self, *args):
        for listener in self.listeners[:]:
            listener(*args)


class Panel(object):
    def __init__(self, distance=0):
        self.distance = distance
        self.calls = []

    def _isDAAPIInited(self):
        return True

    def getDistance(self):
        return self.distance

    def setDistance(self, distance):
        if distance != self.distance:
            self.distance = distance
            self.as_setDistanceS('%d m' % distance)

    def as_setDistanceS(self, text):
        self.calls.append(('show', text))

    def as_clearDistanceS(self, immediate):
        self.calls.append(('clear', immediate))


@unittest.skipUnless(HAS_RANGEFINDER, 'The live stock option belongs to Rangefinder')
class StockDistanceTest(unittest.TestCase):
    def setUp(self):
        self.app = Value()
        self.app.panel = None
        self.panel_ready = Event()
        self.proxy = Value()
        self.proxy.onCrosshairViewChanged = Event()
        self.proxy.onStrategicCameraChanged = Event()
        replacements = {
            '_stock_crosshair': lambda app: app.panel if app else None,
            '_panel_signal': lambda: self.panel_ready,
            '_view_proxy': lambda: self.proxy,
            '_distance_label': lambda value: '%d m' % value,
        }
        for name, value in replacements.items():
            self.addCleanup(setattr, stock_rangefinder, name, getattr(stock_rangefinder, name))
            setattr(stock_rangefinder, name, value)
        self.states = []
        visibility = stock_rangefinder.StockRangefinder()
        visibility.start(lambda: self.app, lambda: self.states.append(visibility.status))
        self.addCleanup(visibility.restore)
        self.visibility = visibility

    def test_intercepts_presentation_and_restores_current_stock_value(self):
        panel = self.app.panel = Panel(300)
        self.assertTrue(self.visibility.suppress(self.app))
        self.assertTrue(self.visibility.suppress(self.app))
        panel.setDistance(340)
        self.assertEqual(340, panel.getDistance())
        self.assertEqual([('clear', True)], panel.calls)
        self.visibility.restore()
        self.assertNotIn('as_setDistanceS', panel.__dict__)
        self.assertEqual([('clear', True), ('show', '340 m')], panel.calls)
        panel.setDistance(370)
        self.assertEqual(('show', '370 m'), panel.calls[-1])
        self.assertEqual(['hidden', 'inactive'], self.states)

    def test_binds_on_native_initialization_and_reapplies_on_both_camera_events(self):
        self.assertFalse(self.visibility.suppress(None))
        self.assertEqual('panel_not_ready', self.visibility.status)
        panel = self.app.panel = Panel(500)
        self.panel_ready.emit()
        self.proxy.onCrosshairViewChanged.emit(1)
        self.proxy.onStrategicCameraChanged.emit(2)
        panel.setDistance(505)
        self.assertEqual([('clear', True)] * 3, panel.calls)

        new_panel = self.app.panel = Panel()
        camera_event = self.proxy.onStrategicCameraChanged
        switched = lambda *unused: new_panel.calls.append(('native_view', None))
        camera_event += switched
        self.addCleanup(camera_event.__isub__, switched)
        self.panel_ready.emit()
        new_panel.setDistance(601)
        self.assertEqual(('show', '505 m'), panel.calls[-1])
        camera_event.emit(2)
        self.assertEqual([('clear', True), ('native_view', None), ('clear', True)], new_panel.calls)

        self.visibility.restore()
        self.assertEqual(('show', '601 m'), new_panel.calls[-1])
        self.assertFalse(self.panel_ready.listeners)
        self.assertFalse(self.proxy.onCrosshairViewChanged.listeners)
        self.assertEqual([switched], camera_event.listeners)

    def test_preserves_another_mods_instance_wrapper(self):
        panel = self.app.panel = Panel(700)
        inherited = panel.as_setDistanceS
        previous = lambda text: inherited('older ' + text)
        panel.as_setDistanceS = previous
        self.assertTrue(self.visibility.suppress(self.app))
        self.visibility.restore()
        self.assertIs(previous, panel.as_setDistanceS)
        self.assertEqual(('show', 'older 700 m'), panel.calls[-1])

        self.assertTrue(self.visibility.suppress(self.app))
        ours = panel.as_setDistanceS
        foreign = lambda text: ours('newer ' + text)
        panel.as_setDistanceS = foreign
        self.visibility.restore()
        self.assertIs(foreign, panel.as_setDistanceS)
        self.assertEqual(('show', 'older newer 700 m'), panel.calls[-1])

class PreviewStockDistanceTest(unittest.TestCase):
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
