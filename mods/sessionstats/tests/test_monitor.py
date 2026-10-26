# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging
import unittest

from test_runtime import Clock
from grz_session_stats.monitor import ResultMonitor, MAX_SIGNATURES


class MonitorTests(unittest.TestCase):
    def setUp(self):
        self.clock = Clock(100)
        self.monitor = ResultMonitor(self.clock, '/fixture/logs/session-stats.log')
        self.old_disable = logging.root.manager.disable
        logging.disable(logging.CRITICAL)

    def tearDown(self):
        logging.disable(self.old_disable)

    def fault(self, path='personal.vehicle.xp'):
        self.monitor.fault('invalid_type', path, 'integer', 'text')

    def test_new_findings_are_batched_and_rate_limited_but_not_lost(self):
        notices = []
        self.fault('personal.vehicle.xp')
        self.assertTrue(self.monitor.flush_notice(notices.append))
        self.fault('personal.vehicle.crystal')
        self.fault('personal.vehicle.gold')
        self.assertFalse(self.monitor.flush_notice(notices.append))
        self.clock.value += 60
        self.assertTrue(self.monitor.flush_notice(notices.append))
        self.assertEqual(len(notices), 2)
        self.assertIn('crystal', notices[1])
        self.assertIn('gold', notices[1])

    def test_identical_findings_from_different_sources_are_reported_once(self):
        notices = []
        for source in ('event', 'posted', 'cache'):
            self.monitor.fault('invalid_type', 'personal.vehicle.xp', 'integer', 'text', source)
            self.monitor.flush_notice(notices.append)
            self.clock.value += 60
        self.assertEqual(len(notices), 1)

    def test_field_labels_are_bounded_and_notification_markup_is_escaped(self):
        self.monitor.fault('type\nnew-line', 'personal.<record>.xp', 'integer', 'text\rnew-line')
        notices = []
        self.monitor.flush_notice(notices.append)
        self.assertIn('&lt;record&gt;', notices[0])
        self.assertNotIn('<record>', notices[0])
        self.assertTrue(all('\n' not in part and '\r' not in part
                            for signature in self.monitor._seen for part in signature))

    def test_flood_of_changed_names_has_bounded_state_and_notice_size(self):
        for i in range(MAX_SIGNATURES + 100):
            self.fault('common.field%d' % i)
        self.assertEqual(len(self.monitor._seen), MAX_SIGNATURES)
        self.assertLessEqual(len(self.monitor._queued), 9)
        notices = []
        self.monitor.flush_notice(notices.append)
        self.assertEqual(len(notices), 1)
        self.assertLess(len(notices[0]), 1000)

    def test_failed_native_push_does_not_discard_queued_findings(self):
        def unavailable(message):
            raise RuntimeError('host not ready')
        self.fault()
        self.assertFalse(self.monitor.flush_notice(unavailable))
        self.clock.value += 61
        notices = []
        self.assertTrue(self.monitor.flush_notice(notices.append))
        self.assertEqual(len(notices), 1)
        self.assertFalse(self.monitor.flush_notice(notices.append))


if __name__ == '__main__':
    unittest.main()
