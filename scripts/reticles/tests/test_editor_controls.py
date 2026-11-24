# -*- coding: ascii -*-
from __future__ import absolute_import

import json
import sys
import unittest

from test_native_scene import FocusClock, MODULES


class EditorControlsTest(unittest.TestCase):
    def setUp(self):
        self.clock = FocusClock()
        previous = sys.modules.get('BigWorld')
        if previous is None:
            self.addCleanup(sys.modules.pop, 'BigWorld', None)
        else:
            self.addCleanup(sys.modules.__setitem__, 'BigWorld', previous)
        sys.modules['BigWorld'] = self.clock

    @staticmethod
    def _window(views):
        window = views.SettingsWindow(lambda arg: None, lambda: '{}')
        window._window = object()
        window.is_open = lambda: True
        window._place = lambda: None
        window._refresh_preview = lambda changed: None
        window.update = lambda state: None
        return window

    def test_failed_reticle_does_not_block_trajectory_or_zoom(self):
        for _, _, views in MODULES:
            window = self._window(views)
            self.assertTrue(window.set_editor(True, 'arty', 'standard', 'arty_top', 2))
            window._preview_status = 'unavailable'
            window._preview_availability = {'arty': {'standard': False, 'cassette': False}}
            request = dict(mode='arty', variant='standard', scene_id='arty_trajectory',
                           zoom_step=4, request_id=1)
            self.assertTrue(window._dispatch_editor_request('preview', request.get))
            self.clock.tick(0.0)
            state = json.loads(window._payload())
            self.assertIs(state['editor_request_accepted'], True)
            self.assertEqual((state['editor_scene_id'], state['editor_zoom_step']), ('arty_trajectory', 4))
            self.assertEqual(state['editor_preview_status'], 'unavailable')
            self.assertIs(state['editor_focus_supported'], False)
            other = dict(request, variant='cassette', request_id=2)
            self.assertFalse(window._dispatch_editor_request('preview', other.get))

    def test_direct_mode_accepts_focus_and_demo_callbacks(self):
        class Preview(object):
            supports_focus = True

            def play_focus_demo(self, finished):
                self.finished = finished
                return True

        for _, _, views in MODULES:
            for mode, zoom in (('arcade', 0), ('sniper', 4)):
                window = self._window(views)
                changes = []
                window._refresh_preview = changes.append
                self.assertTrue(window.set_editor(True, mode, 'standard', mode, zoom))
                request = dict(mode=mode, variant='standard', scene_id=mode, zoom_step=zoom,
                               focus=0, focus_changed=True, request_id=1)
                self.assertTrue(window._dispatch_editor_request('preview', request.get))
                self.clock.tick(0.0)
                self.assertEqual(changes, [False, True])
                self.assertEqual(json.loads(window._payload())['editor_focus'], 0)
                window._preview_status = 'ready'
                window._preview = Preview()
                self.assertIs(json.loads(window._payload())['editor_focus_supported'], True)
                self.assertTrue(window._play_focus_demo())
                self.assertIs(json.loads(window._payload())['editor_focus_demo'], True)
                window._preview.finished(True)
                state = json.loads(window._payload())
                self.assertEqual(state['editor_focus'], 2)
                self.assertIs(state['editor_focus_demo'], False)
