# -*- coding: ascii -*-
from __future__ import absolute_import

import sys
import types
import unittest

from test_native_scene import MODULES, Value

HAS_RANGEFINDER = any(native.__package__ == 'grz_rangefinder' for _, native, _ in MODULES)
if HAS_RANGEFINDER:
    from grz_rangefinder import runtime, stock_rangefinder


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

    def test_late_panel_retries_are_bounded_and_resume_after_a_new_request(self):
        runner = runtime.Runtime.__new__(runtime.Runtime)
        runner._stock_rangefinder = self.visibility
        runner._stock_requested = runner._stock_syncing = False
        runner._stock_retry_at, runner._stock_retry_index = None, 0
        runner._application = lambda: self.app
        now = [0.0]
        runner.clock = lambda: now[0]
        attempts = []
        suppress = self.visibility.suppress

        def attempt(app):
            attempts.append(now[0])
            return suppress(app)

        self.visibility.suppress = attempt
        for tick in range(30):
            now[0] = tick / 10.0
            runner._sync_stock(True)
        self.assertEqual(1 + len(runtime.STOCK_RETRY_DELAYS), len(attempts))
        self.assertEqual('panel_not_ready', self.visibility.status)

        runner._sync_stock(False)
        runner._sync_stock(True)
        panel = self.app.panel = Panel(610)
        now[0] += .10
        runner._sync_stock(True)
        self.assertEqual([], panel.calls)
        now[0] += .20
        runner._sync_stock(True)
        self.assertEqual('hidden', self.visibility.status)
        self.assertEqual([('clear', True)], panel.calls)
        now[0] += 2
        runner._sync_stock(True)
        self.assertEqual(3 + len(runtime.STOCK_RETRY_DELAYS), len(attempts))
        runner._sync_stock(False)
        self.assertEqual(('show', '610 m'), panel.calls[-1])

    def test_cached_distance_accepts_only_a_current_artillery_value(self):
        for parent in ('gui', 'gui.battle_control'):
            if parent not in sys.modules:
                package = types.ModuleType(parent)
                package.__path__ = []
                sys.modules[parent] = package
                self.addCleanup(sys.modules.pop, parent, None)
        name = 'gui.battle_control.battle_constants'
        previous = sys.modules.get(name)
        if previous is None:
            self.addCleanup(sys.modules.pop, name, None)
        else:
            self.addCleanup(sys.modules.__setitem__, name, previous)
        constants = types.ModuleType(name)
        constants.CROSSHAIR_VIEW_ID = Value()
        constants.CROSSHAIR_VIEW_ID.STRATEGIC = 3
        sys.modules[name] = constants
        panel = self.app.panel = Panel(615)
        panel.getViewID = lambda: 1
        self.assertIsNone(self.visibility.artillery_distance())
        panel.getViewID = lambda: 3
        self.assertEqual(615, self.visibility.artillery_distance())
        panel.distance = 0
        self.assertIsNone(self.visibility.artillery_distance())
        self.assertEqual([], panel.calls)

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
