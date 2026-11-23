# -*- coding: ascii -*-
from __future__ import absolute_import

import unittest

from test_native_scene import MODULES, Value


HAS_RANGEFINDER = any(native.__package__ == 'grz_rangefinder' for _, native, _ in MODULES)
if HAS_RANGEFINDER:
    from grz_rangefinder import client


def value(**attributes):
    result = Value()
    result.__dict__.update(attributes)
    return result


def vehicle(entity_id, position, alive=True, hidden=False):
    return value(id=entity_id, position=position, inWorld=True, isStarted=True,
                 isHidden=hidden, isAlive=lambda: alive)


@unittest.skipUnless(HAS_RANGEFINDER, 'The distance adapter belongs to Rangefinder')
class DistanceMeasurementTest(unittest.TestCase):
    def setUp(self):
        self.casts = []
        self.rays = []
        self.lookups = []
        self.position = (100, 200)
        self.native_hit = ((8, 0, 0), False)
        self.target = vehicle(2, (12, 0, 0))
        self.own = vehicle(1, (0, 0, 0))
        self.handler = value(ctrlModeName='arcade', isStarted=True)
        self.crosshair = value(getPosition=lambda: self.position, getOffset=lambda: (0, 0))
        self.player = value(
            arena=Value(), inputHandler=self.handler, playerVehicleID=1, spaceID=9,
            isVehicleAlive=True, isObserver=lambda: False,
            getVehicleAttached=lambda: self.own, getOwnVehiclePosition=lambda: self.own.position,
            gunRotator=value(markerInfo=((123, 0, 9),)),
            guiSessionProvider=value(shared=value(crosshair=self.crosshair)))
        self.world = value(player=lambda: self.player, wg_collideDynamicStatic=self._cast,
                           entity=self._lookup)
        self.probe = client.ClientProbe(self.world, value(screenResolution=lambda: (1920, 1080)),
                                        self._ray, vector_factory=lambda *coords: coords,
                                        interface_scale_getter=lambda: 1.0)

    def _ray(self, *args):
        self.rays.append(args)
        return (1, 0, 0), (0, 0, 0)

    def _cast(self, *args):
        self.casts.append(args)
        return self.native_hit

    def _lookup(self, entity_id):
        self.lookups.append(entity_id)
        return self.target if self.target is not None and self.target.id == entity_id else None

    def test_both_artillery_modes_use_native_meter_truncation_without_a_ray(self):
        for mode in ('strategic', 'arty'):
            self.handler.ctrlModeName = mode
            result = self.probe.poll()
            self.assertEqual((123, 'surface'),
                             (result['distance_m'], result['kind']))
        self.assertEqual([], self.rays)
        self.assertEqual([], self.casts)

    def test_factory_artillery_display_skips_measurement_entirely(self):
        self.handler.ctrlModeName = 'arty'
        self.player.getOwnVehiclePosition = self._ray
        result = self.probe.poll(artillery_measure=False)
        self.assertTrue(result['battle_eligible'])
        self.assertFalse(result['available'])
        self.assertEqual('artillery_native_display', result['reason'])
        self.assertEqual([], self.rays)
        self.assertEqual([], self.casts)

    def test_unavailable_or_initial_artillery_marker_does_not_cast(self):
        self.handler.ctrlModeName = 'strategic'
        self.own.position = (123, 0, 0)
        for marker_info in ((), ((0.0, 0.0, 0.0), (0.0, 1.0, 0.0), 1.0)):
            self.player.gunRotator.markerInfo = marker_info
            result = self.probe.poll()
            self.assertFalse(result['available'])
            self.assertEqual('stock_marker_unavailable', result['reason'])
        self.assertEqual([], self.casts)
        self.assertEqual([], self.rays)

    def test_native_ray_preserves_hit_and_skips_material_lookup(self):
        self.native_hit = ((8, 0, 0), True, 2, 4, 48, None)
        result = self.probe.poll()
        self.assertEqual([(9, (0.0, 0.0, 0.0), (10000.0, 0.0, 0.0), 128, 1, -1, 0)],
                         self.casts)
        self.assertEqual([2], self.lookups)
        self.assertEqual((12.0, 'vehicle'),
                         (result['distance_m'], result['kind']))
        self.target = vehicle(2, (12, 0, 0), alive=False)
        result = self.probe.poll()
        self.assertEqual((8.0, 'surface'), (result['distance_m'], result['kind']))
        self.target = vehicle(2, (12, 0, 0), hidden=True)
        result = self.probe.poll()
        self.assertFalse(result['available'])
        self.assertEqual('target_visibility_unavailable', result['reason'])

    def test_incompatible_native_tuple_falls_back_on_next_sample(self):
        self.native_hit = ((8, 0, 0), True)
        fallback_calls = []

        def fallback(*args):
            fallback_calls.append(args)
            return (8, 0, 0), None

        original = client._load_module
        client._load_module = lambda name: value(collideDynamicAndStatic=fallback)
        self.addCleanup(setattr, client, '_load_module', original)
        result = self.probe.poll()
        self.assertEqual('collision_data_unavailable', result['reason'])
        self.assertEqual(1, len(self.casts))
        self.assertEqual([], fallback_calls)
        result = self.probe.poll()
        self.assertEqual(1, len(self.casts))
        self.assertEqual(1, len(fallback_calls))
        self.assertEqual((8.0, 'surface'),
                         (result['distance_m'], result['kind']))


if __name__ == '__main__':
    unittest.main()
