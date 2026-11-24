# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os
import unittest

from test_config_path import changed
from grz_session_stats import capture_order


class CaptureOrderTests(unittest.TestCase):
    @unittest.skipUnless(os.name == 'nt', 'Windows boot source')
    def test_native_boot_guid_is_stable_and_independent_of_prefetch(self):
        first = capture_order.CaptureClock()
        if first.domain is None:
            self.skipTest('Native Windows boot information is unavailable')
        earlier = first.stamp()
        second = capture_order.CaptureClock()
        self.assertEqual(first.domain, second.domain)
        self.assertEqual(earlier[1], first.domain)
        self.assertGreater(second.stamp()[2], earlier[2])

    def test_missing_boot_id_uses_a_valid_wall_stamp_and_local_sequence(self):
        class WallClock(object):
            wall = 1000

            def time(self):
                return self.wall

        wall = WallClock()
        with changed(capture_order, '_boot_clock', lambda: (None, None)), changed(capture_order, 'time', wall):
            clock = capture_order.CaptureClock()
            older = clock.stamp()
            wall.wall -= 3600
            newer = clock.stamp()
        self.assertIsNone(clock.domain)
        self.assertEqual(older[0], newer[0])
        self.assertTrue(capture_order.valid_capture_order(older))
        self.assertTrue(capture_order.valid_capture_order(newer))
        self.assertEqual(capture_order.compare_capture_order(older, newer, None), -1)
        self.assertEqual(capture_order.compare_capture_order(newer, older, None), 1)

    def test_only_comparable_boot_observations_order_conflicting_facts(self):
        active, old, foreign = 'a' * 32, 'b' * 32, 'c' * 32
        live = [10, active, 100, '1' * 32, 2]
        same_boot = [7000, active, 80, '2' * 32, 2]
        earlier_boot = [9000, old, 100000, '3' * 32, 1]
        other_history = [9999, foreign, 200000, '4' * 32, 1]
        missing = [99999, None, 0, '5' * 32, 1]
        self.assertEqual(capture_order.compare_capture_order(live, same_boot, active), 1)
        self.assertEqual(capture_order.compare_capture_order(earlier_boot, live, active), -1)
        self.assertEqual(capture_order.compare_capture_order(live, earlier_boot, active), 1)
        self.assertIsNone(capture_order.compare_capture_order(earlier_boot, other_history, active))
        self.assertIsNone(capture_order.compare_capture_order(missing, live, active))
        self.assertIsNone(capture_order.compare_capture_order(live, missing, active))
