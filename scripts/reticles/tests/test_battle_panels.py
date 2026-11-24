# -*- coding: ascii -*-
from __future__ import absolute_import

import imp
import os
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BattlePanelPreview = imp.load_source(
    'tested_battle_panel_preview', os.path.join(ROOT, 'battle_panel_preview.py')).BattlePanelPreview


class Root(object):
    def __init__(self, state):
        self.state = state
        self.requests = []

    def as_setPreview(self, *args):
        self.requests.append(args)

    def as_getState(self):
        return self.state


class Host(object):
    def __init__(self, root):
        self.component = type('Component', (object,), {})()
        self.root = root

    def getMember(self, name):
        return self.root if name == b'root' else None


def _recipe(layout, sample_status='complete', offset=(0, 0), scale=1.0):
    return dict(stock_library='gui/flash/sample.swf', linkage='StockWidget', layout=layout,
                sample_status=sample_status, offset=offset, scale=scale)


class BattlePanelsTest(unittest.TestCase):
    def setUp(self):
        self.events = []
        self.closed = []

    def _preview(self, recipes, hosts):
        return BattlePanelPreview(
            recipes, 'sniper', {}, (1920, 1080, 1.0), lambda resource: next(hosts),
            self.closed.append, lambda event, **fields: self.events.append((event, fields)),
            lambda root: ('timeline-member', 1009, None), 2)

    def test_native_slots_and_resizing(self):
        left = Host(Root(1))
        right = Host(Root(1))
        preview = self._preview([('fight', _recipe('left')), ('turbo', _recipe('right', offset=(0, 2)))],
                                iter([left, right]))
        self.assertTrue(preview.pending)
        preview.poll()
        self.assertFalse(preview.pending)
        self.assertEqual((770, 730, 1.0, 2), left.root.requests[-1][1:5])
        self.assertEqual((1150, 732, 1.0, 2), right.root.requests[-1][1:5])
        preview.resize((2560, 1440, 1.25))
        preview.poll()
        self.assertEqual((2560, 1440), right.component.size)
        self.assertEqual((1517.5, 960, 1.25, 2), right.root.requests[-1][1:5])
        preview.close()
        self.assertEqual([left, right], self.closed)

    def test_reports_widget_failures_without_releasing_other_widgets(self):
        working, rejected, timed_out = Host(Root(1)), Host(Root(-1)), Host(None)
        preview = self._preview([
            ('visible', _recipe('center', 'partial')), ('rejected', _recipe('info')),
            ('timed_out', _recipe('right')), ('missing', _recipe('left')),
            ('pending_sample', _recipe('info', 'pending')),
        ], iter([working, rejected, timed_out, None]))
        preview.poll()
        self.assertTrue(preview.pending)
        self.assertTrue(preview.incomplete)
        self.assertTrue(preview.failed)
        preview.poll()
        self.assertFalse(preview.pending)
        self.assertEqual([rejected, timed_out], self.closed)
        phases = dict((payload['panel'], payload['panel_stage']) for _, payload in self.events)
        self.assertEqual({'visible': 'panel-sample-incomplete', 'rejected': 'panel-rejected',
                          'timed_out': 'panel-timeout', 'missing': 'panel-resource',
                          'pending_sample': 'panel-sample-incomplete'}, phases)
        preview.close()
        self.assertEqual([rejected, timed_out, working], self.closed)
