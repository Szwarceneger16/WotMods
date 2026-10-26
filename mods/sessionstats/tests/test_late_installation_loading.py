# -*- coding: utf-8 -*-
"""Late installation discovery must retain live provenance during startup."""
from __future__ import unicode_literals

import shutil
import tempfile
import unittest

from test_core import Clock, EXPECTED
from test_config_path import changed
from test_normalize import raw_result, START, ARENA_ID
from test_runtime import FakeAPI, FakeWindow
from grz_session_stats import config_path, runtime
from grz_session_stats.sessions import InstallationSession


class LateInstallationLoadingTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.mkdtemp(prefix='grz-late-installation-')
        self.clock = Clock(START - 10)
        self.api = FakeAPI()
        self.resolver = changed(config_path, 'find_installation_root', lambda: None)
        self.resolver.__enter__()
        self.mod = self.open()

    def tearDown(self):
        self.mod.stop()
        self.resolver.__exit__(None, None, None)
        shutil.rmtree(self.directory)

    def open(self, root=None):
        mod = runtime.Runtime(api=self.api, data_dir=self.directory, expected_table=EXPECTED,
                              now=self.clock, window=FakeWindow(), footer_installer=lambda unused: None,
                              installation_dir=root)
        mod.start()
        return mod

    def begin(self):
        self.clock.value = START + 10
        self.api.battle = True
        self.api.context = {'arena_id': str(ARENA_ID), 'started_at': START,
                            'vehicle_id': 1, 'map_id': 'map'}
        self.mod._on_avatar()
        self.assertIsNone(self.mod._instance_session)
        self.assertTrue(self.mod.active_service.loading)

    def discover(self):
        self.mod._installation_dir = self.directory
        self.mod._ensure_service()
        self.assertIsNotNone(self.mod._instance_session)

    def finish(self):
        self.api.battle = False
        for unused in range(10000):
            if self.mod._load_id is None:
                break
            self.api.fire(self.mod._load_id)
        self.assertFalse(self.mod._loading_services())
        self.assertTrue(self.mod.active_service.ready, self.mod.active_service.last_error)
        self.assertTrue(self.mod._instance_session.service.ready)

    def restart(self):
        self.mod.stop()
        self.api.battle = False
        self.clock.value = START + 86400
        with changed(runtime, 'LAUNCH_ID', runtime.LAUNCH_ID + '-restart'):
            self.mod = self.open(self.directory)
        self.finish()

    def assert_recovered_once(self):
        self.mod._on_results(True, raw_result())
        session = self.mod._instance_session
        self.assertEqual(session.snapshot()[0]['summary']['battles'], 1)
        sequence = session.service.store.sequence
        self.mod._on_results(True, raw_result())
        self.assertEqual(session.service.store.sequence, sequence)
        self.assertEqual(session.snapshot()[0]['summary']['battles'], 1)

    def test_shutdown_before_loading_finishes_retains_beginning_for_recovered_result(self):
        self.begin()
        self.discover()
        self.assertTrue(self.mod.active_service.loading)
        self.restart()
        self.assert_recovered_once()

    def test_shutdown_after_loading_finishes_retains_beginning_for_recovered_result(self):
        self.begin()
        self.discover()
        self.finish()
        self.restart()
        self.assert_recovered_once()

    def test_ready_backfill_keeps_result_with_original_account_after_switch(self):
        self.begin()
        first = self.mod.active_service
        self.clock.value = START + 400
        self.mod._on_results(True, raw_result())
        self.discover()
        self.api.battle = False
        self.api.dbid = 8
        self.mod._on_account()
        self.finish()
        self.assertTrue(first.ready, first.last_error)
        session = self.mod._instance_session
        records = session.service._state['battles']
        self.assertIn(InstallationSession.battle_key('EU:7', ARENA_ID), records)
        self.assertNotIn(InstallationSession.battle_key('EU:8', ARENA_ID), records)
        self.assertEqual(session.snapshot()[0]['summary']['battles'], 1)
