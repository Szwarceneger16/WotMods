# -*- coding: utf-8 -*-
"""External JSON fallback behavior, including interpreters with deeper decoders."""
from __future__ import unicode_literals

import contextlib
import io
import json
import logging
import os
import shutil
import sys
import tempfile
import types
import unittest

from test_runtime import FakeAPI, FakeWindow, Clock, Obj, EXPECTED
from test_normalize import ARENA_ID, raw_result
from grz_session_stats import runtime

DECODER_ERRORS = [RuntimeError]
if sys.version_info[0] >= 3:
    DECODER_ERRORS.append(RecursionError)


class ExternalJSONTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.mkdtemp(prefix='grz-json-boundaries-')
        self.modules = []
        self.log_level = logging.root.manager.disable
        logging.disable(logging.CRITICAL)
        self.api, self.clock = FakeAPI(), Clock()
        self.saved_resmgr = sys.modules.get('ResMgr')
        module = types.ModuleType(str('ResMgr'))
        module.openSection = lambda name: Obj(asBinary=json.dumps(EXPECTED))
        sys.modules['ResMgr'] = module

    def tearDown(self):
        for mod in self.modules:
            mod.stop()
        if self.saved_resmgr is None:
            sys.modules.pop('ResMgr', None)
        else:
            sys.modules['ResMgr'] = self.saved_resmgr
        logging.disable(self.log_level)
        shutil.rmtree(self.directory)

    def write(self, filename, raw):
        path = os.path.join(self.directory, filename)
        with io.open(path, 'w', encoding='utf-8') as stream:
            stream.write(raw)
        return path

    def mod(self, load_expected=False, footer_installer=None):
        api = FakeAPI()
        if load_expected:
            api.load_expected = runtime.GameAPI.__new__(runtime.GameAPI).load_expected
        mod = runtime.Runtime(deferred_loading=False, api=api, data_dir=self.directory, now=self.clock,
                              expected_table=None if load_expected else EXPECTED,
                              window=FakeWindow(), footer_installer=footer_installer or (lambda callback: None),
                              installation_dir=self.directory)
        self.modules.append(mod)
        return mod

    @contextlib.contextmanager
    def failing_decoder(self, raw, error_type):
        original = runtime.json.loads
        calls = []

        def fail(value, *args, **kwargs):
            if value == raw:
                calls.append(error_type)
                raise error_type('PRIVATE_JSON_SENTINEL')
            return original(value, *args, **kwargs)

        runtime.json.loads = fail
        try:
            yield calls
        finally:
            runtime.json.loads = original

    def collect(self, mod):
        api = mod.api
        api.battle = True
        self.clock.value = runtime.arena_start(ARENA_ID)
        api.context = {'arena_id': ARENA_ID, 'started_at': self.clock.value,
                       'vehicle_id': 1, 'map_id': '17_map', 'mode': 'random'}
        api.events.onAvatarReady()
        api.battle = False
        api.events.onBattleResultsReceived(True, raw_result())
        summary = mod.active_service.snapshot()['scopes']['launch']['summary']
        self.assertEqual(summary['battles'], 1)
        self.assertIsNotNone(summary['wn8'])

    def test_recursive_local_preferences_do_not_disable_startup_or_result_collection(self):
        raw = '{"hotkey":"PRIVATE_JSON_SENTINEL","footer_button":false}'
        self.write('config.json', raw)
        for error in DECODER_ERRORS:
            mod = self.mod()
            with self.failing_decoder(raw, error) as calls:
                mod.start()
            self.assertEqual(calls, [error])
            self.assertTrue(mod.running)
            self.assertEqual(mod.config, runtime.DEFAULT_LOCAL_CONFIG)
            self.assertEqual(len(mod.api.events.onBattleResultsReceived.handlers), 1)
            self.collect(mod)
            mod.stop()

    def test_recursive_wn8_override_loads_bundled_table_and_keeps_wn8(self):
        raw = '{"data":"PRIVATE_JSON_SENTINEL"}'
        self.write('wn8exp.json', raw)
        for error in DECODER_ERRORS:
            mod = self.mod(load_expected=True)
            with self.failing_decoder(raw, error) as calls:
                mod.start()
            self.assertEqual(calls, [error])
            self.assertEqual(mod.expected_table, EXPECTED)
            self.assertIsNone(mod.last_error)
            self.collect(mod)
            mod.stop()

    def test_real_deep_json_uses_valid_defaults_or_bundled_data_without_a_fixed_depth_assumption(self):
        nested = '[' * 16384 + '0' + ']' * 16384
        self.write('config.json', '{"hotkey":'+nested+',"footer_button":{}}')
        self.write('wn8exp.json', '{"data":'+nested+'}')
        mod = self.mod(load_expected=True)
        mod.start()
        self.assertTrue(mod.running)
        self.assertEqual(mod.config, runtime.DEFAULT_LOCAL_CONFIG)
        self.assertEqual(mod.expected_table, EXPECTED)
        self.collect(mod)

    def test_accepted_but_nested_hotkey_and_nonboolean_footer_are_validated_before_use(self):
        nested = []
        for unused in range(3000):
            nested = [nested]
        original = runtime._load_json_file
        runtime._load_json_file = lambda unused: {'hotkey': nested, 'footer_button': 'false'}
        self.write('config.json', '{}')
        try:
            mod = self.mod()
            mod.start()
        finally:
            runtime._load_json_file = original
        self.assertEqual(mod.config, runtime.DEFAULT_LOCAL_CONFIG)
        self.assertTrue(mod.running)
        self.collect(mod)

    def test_accepted_nested_wn8_metadata_cannot_break_account_initialization(self):
        raw = '{"header":"PRIVATE_JSON_SENTINEL"}'
        self.write('wn8exp.json', raw)
        nested = []
        for unused in range(3000):
            nested = [nested]
        document = dict(EXPECTED, header={'version': nested})
        original = runtime.json.loads

        def accepted(value, *args, **kwargs):
            return document if value == raw else original(value, *args, **kwargs)

        runtime.json.loads = accepted
        try:
            mod = self.mod(load_expected=True)
            mod.start()
        finally:
            runtime.json.loads = original
        self.assertEqual(mod.expected_table, EXPECTED)
        self.assertIsNotNone(mod.active_service)
        self.collect(mod)

    def test_invalid_replacement_preferences_restore_defaults_after_stop_and_start(self):
        self.write('config.json', '{"hotkey":"CTRL+F6","footer_button":false}')
        installed = []
        mod = self.mod(footer_installer=lambda callback: installed.append(callback))
        mod.start()
        self.assertEqual(mod._hotkey[0], mod.api.keys.KEY_F6)
        self.assertFalse(mod.config['footer_button'])
        self.assertEqual(installed, [])
        mod.stop()
        raw = '{"hotkey":"PRIVATE_JSON_SENTINEL"}'
        self.write('config.json', raw)
        with self.failing_decoder(raw, RuntimeError):
            mod.start()
        self.assertEqual(mod.config, runtime.DEFAULT_LOCAL_CONFIG)
        self.assertEqual(mod._hotkey[0], mod.api.keys.KEY_F10)
        self.assertEqual(len(installed), 1)

    def test_local_reader_handles_bom_and_enforces_actual_read_size(self):
        path = self.write('config.json', '\ufeff{"hotkey":"CTRL+F6"}')
        self.assertEqual(runtime._load_json_file(path), {'hotkey': 'CTRL+F6'})
        original_limit = runtime.MAX_EXPECTED_BYTES
        runtime.MAX_EXPECTED_BYTES = 64
        try:
            self.write('config.json', ' ' * 65)
            self.assertRaises(ValueError, runtime._load_json_file, path)
        finally:
            runtime.MAX_EXPECTED_BYTES = original_limit

    def test_rejected_json_diagnostics_do_not_echo_decoder_payloads(self):
        raw = '{"hotkey":"PRIVATE_JSON_SENTINEL"}'
        self.write('config.json', raw)
        self.write('wn8exp.json', raw)
        original = runtime.LOG.warning
        warnings = []
        runtime.LOG.warning = lambda value, *args, **kwargs: warnings.append(value % args)
        try:
            with self.failing_decoder(raw, RuntimeError):
                self.mod(load_expected=True).start()
        finally:
            runtime.LOG.warning = original
        fallbacks = [value for value in warnings if value.startswith(('Invalid local configuration;',
                      'Invalid local WN8 expected table;'))]
        self.assertEqual(len(fallbacks), 2)
        self.assertNotIn('PRIVATE_JSON_SENTINEL', '\n'.join(warnings))


if __name__ == '__main__':
    unittest.main()
