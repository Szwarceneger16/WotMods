"""Atomic settings updates preserve unrelated local configuration."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import Mock, patch

SOURCE = Path(__file__).resolve().parents[1] / 'source/staysharp_medkit'
PACKAGE = 'medkit_settings_tests_package'
package = types.ModuleType(PACKAGE)
package.__path__ = [str(SOURCE)]
sys.modules[PACKAGE] = package
spec = importlib.util.spec_from_file_location(PACKAGE + '.settings', SOURCE / 'settings.py')
settings = importlib.util.module_from_spec(spec)
spec.loader.exec_module(settings)


class SettingsTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.path = Path(self.temporary.name) / 'mods' / 'configs' / 'staysharp.medkit.json'
        self.logs = []
        self.changes = []
        self.store = settings.SettingsStore(str(self.path), self.logs.append, self.changes.append)

    def tearDown(self):
        self.temporary.cleanup()

    def write(self, payload):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(payload), encoding='utf-8')

    def disk(self):
        return json.loads(self.path.read_text(encoding='utf-8'))

    def assert_no_temporary_files(self):
        self.assertEqual(list(self.path.parent.glob('.staysharp-medkit-*.tmp')), [])

    def test_missing_config_is_created_and_payloads_are_independent(self):
        payload = self.store.load()
        self.assertEqual(payload, settings.DEFAULTS)
        self.assertEqual(self.disk(), settings.DEFAULTS)
        payload['hotkeys']['toggle_mod'].append('Q')
        self.assertEqual(self.store.get_payload(), settings.DEFAULTS)
        self.assertEqual(self.changes, [])
        self.assert_no_temporary_files()

    def test_legacy_configuration_load_does_not_rewrite_existing_bytes(self):
        self.write({'language': 'PL_pl', 'enabled': False, 'voice_enabled': False,
                    'voice_volume': 35, 'custom': {'keep': [1, 'two']}})
        original = self.path.read_bytes()
        payload = self.store.load()
        self.assertEqual(payload['language'], 'pl')
        self.assertFalse(payload['enabled'])
        self.assertFalse(payload['voice_enabled'])
        self.assertEqual(payload['voice_volume'], 35)
        self.assertEqual(payload['hotkeys'], settings.DEFAULT_HOTKEYS)
        self.assertEqual(payload['custom'], {'keep': [1, 'two']})
        self.assertEqual(self.path.read_bytes(), original)

    def test_save_merges_fresh_disk_settings_and_unknown_nested_hotkeys(self):
        self.store.load()
        self.write({'language': 'de', 'enabled': False, 'voice_enabled': False,
                    'voice_volume': 25, 'future': {'retained': True},
                    'hotkeys': {'future_action': ['Q'], 'toggle_voice': ['F8']}})
        self.assertTrue(self.store.update_hotkeys({'toggle_mod': ['f7']}))
        expected = {'language': 'de', 'enabled': False, 'voice_enabled': False,
                    'voice_volume': 25, 'future': {'retained': True},
                    'hotkeys': {'future_action': ['Q'], 'toggle_voice': ['F8'], 'toggle_mod': ['F7']}}
        self.assertEqual(self.disk(), expected)
        self.assertEqual(self.store.get_payload(), expected)
        self.assertEqual(self.changes, [expected])
        self.changes[0]['hotkeys']['toggle_mod'].append('X')
        self.assertEqual(self.store.get_payload(), expected)
        self.assert_no_temporary_files()

    def test_saved_keys_survive_new_store_and_disabled_actions_are_allowed(self):
        self.store.load()
        self.assertTrue(self.store.update_hotkeys({'toggle_mod': ['RCTRL', 'F6'], 'toggle_voice': []}))
        loaded = settings.SettingsStore(str(self.path)).load()
        self.assertEqual(loaded['hotkeys'], {'toggle_mod': ['RCTRL', 'F6'], 'toggle_voice': []})
        self.assertTrue(self.store.update_hotkeys({'toggle_mod': None}))
        self.assertEqual(self.store.get_payload()['hotkeys'], {'toggle_mod': [], 'toggle_voice': []})

    def test_malformed_or_oversized_configuration_is_never_clobbered(self):
        known = self.store.load()
        for invalid in (b'{broken private content', b'[]', b'{"enabled":true,"enabled":false}',
                        b'{"voice_volume":NaN}', b'\xff', b'x' * (settings.CONFIG_MAX_BYTES + 1)):
            with self.subTest(invalid_prefix=invalid[:8]):
                self.path.write_bytes(invalid)
                self.assertEqual(self.store.load(), known)
                self.assertFalse(self.store.update_hotkeys({'toggle_mod': ['F9']}))
                self.assertEqual(self.path.read_bytes(), invalid)
                self.assertEqual(self.store.get_payload(), known)
                self.assertEqual(self.changes, [])
                self.assert_no_temporary_files()
        self.assertNotIn('private content', '\n'.join(self.logs))
        self.assertNotIn(str(self.path), '\n'.join(self.logs))

    def test_utf8_bom_loads_and_invalid_known_values_use_defaults_without_rewrite(self):
        source = {'language': 'unsupported', 'enabled': 0, 'voice_enabled': 'false',
                  'voice_volume': True, 'hotkeys': {'toggle_mod': ['NOT_A_KEY']}, 'note': 'żółć'}
        self.path.parent.mkdir(parents=True)
        original = b'\xef\xbb\xbf' + json.dumps(source, ensure_ascii=False).encode('utf-8')
        self.path.write_bytes(original)
        payload = self.store.load()
        for key in ('language', 'enabled', 'voice_enabled', 'voice_volume', 'hotkeys'):
            self.assertEqual(payload[key], settings.DEFAULTS[key])
        self.assertEqual(payload['note'], 'żółć')
        self.assertEqual(self.path.read_bytes(), original)

    def test_conflicts_and_invalid_updates_do_not_change_disk_or_memory(self):
        initial = self.store.load()
        original = self.path.read_bytes()
        for invalid in (None, [], {}, {'unknown': ['F1']}, {'toggle_mod': ['NOT_A_KEY']},
                        {'toggle_mod': [True]}, {'toggle_mod': ['CTRL', 'ALT', 'V']},
                        {'toggle_mod': ['LCTRL', 'ALT', 'V']}):
            with self.subTest(invalid=invalid):
                self.assertFalse(self.store.update_hotkeys(invalid))
                self.assertEqual(self.path.read_bytes(), original)
                self.assertEqual(self.store.get_payload(), initial)
                self.assertEqual(self.changes, [])

    def test_conflicting_keys_loaded_from_disk_fall_back_together(self):
        self.write({'hotkeys': {'toggle_mod': ['CTRL', 'M'], 'toggle_voice': ['LCTRL', 'M']}})
        original = self.path.read_bytes()
        self.assertEqual(self.store.load()['hotkeys'], settings.DEFAULT_HOTKEYS)
        self.assertEqual(self.path.read_bytes(), original)

    def test_unavailable_path_never_writes_or_notifies(self):
        for path in (None, '', 'relative.json', 123):
            with self.subTest(path=path):
                store = settings.SettingsStore(path, self.logs.append, self.changes.append)
                self.assertEqual(store.load(), settings.DEFAULTS)
                self.assertFalse(store.update_hotkeys({'toggle_mod': ['F5']}))
                self.assertEqual(store.last_error, 'unavailable_path')
        self.assertEqual(self.changes, [])

    def test_replace_failure_preserves_original_and_memory_and_removes_temporary(self):
        initial = self.store.load()
        original = self.path.read_bytes()
        with patch.object(settings, '_replace_file', side_effect=OSError('private path and content')):
            self.assertFalse(self.store.update_hotkeys({'toggle_mod': ['F5']}))
        self.assertEqual(self.path.read_bytes(), original)
        self.assertEqual(self.store.get_payload(), initial)
        self.assertEqual(self.changes, [])
        self.assertEqual(self.store.last_error, 'save_failed')
        self.assertNotIn('private path', '\n'.join(self.logs))
        self.assert_no_temporary_files()

    def test_fsync_failure_never_replaces_live_file(self):
        initial = self.store.load()
        original = self.path.read_bytes()
        with patch.object(settings.os, 'fsync', side_effect=OSError('write failed')), \
                patch.object(settings, '_replace_file') as replace:
            self.assertFalse(self.store.update_hotkeys({'toggle_mod': ['F5']}))
        replace.assert_not_called()
        self.assertEqual(self.path.read_bytes(), original)
        self.assertEqual(self.store.get_payload(), initial)
        self.assertEqual(self.changes, [])
        self.assert_no_temporary_files()

    def test_serialized_size_limit_preserves_large_valid_original(self):
        self.write({'note': 'x' * (settings.CONFIG_MAX_BYTES - 50)})
        self.assertLess(len(self.path.read_bytes()), settings.CONFIG_MAX_BYTES)
        initial = self.store.load()
        original = self.path.read_bytes()
        self.assertFalse(self.store.update_hotkeys({'toggle_mod': ['F5']}))
        self.assertEqual(self.path.read_bytes(), original)
        self.assertEqual(self.store.get_payload(), initial)
        self.assertEqual(self.changes, [])
        self.assert_no_temporary_files()

    def test_detected_concurrent_edit_survives_without_stale_memory_commit(self):
        initial = self.store.load()
        read = settings._read_document
        calls = []
        external = {'language': 'fr', 'externally_changed': True}
        def changed(path):
            calls.append(path)
            if len(calls) == 2:
                self.write(external)
            return read(path)
        with patch.object(settings, '_read_document', changed):
            self.assertFalse(self.store.update_hotkeys({'toggle_mod': ['F5']}))
        self.assertEqual(self.disk(), external)
        self.assertEqual(self.store.get_payload(), initial)
        self.assertEqual(self.store.last_error, 'changed_configuration')
        self.assertEqual(self.changes, [])
        self.assert_no_temporary_files()

    def test_creation_race_keeps_existing_configuration(self):
        read = settings._read_document
        calls = []
        external = {'language': 'uk', 'created_elsewhere': True}
        def created(path):
            calls.append(path)
            if len(calls) == 2:
                self.write(external)
            return read(path)
        with patch.object(settings, '_read_document', created):
            self.assertEqual(self.store.load(), settings.DEFAULTS)
        self.assertEqual(self.disk(), external)
        self.assertEqual(self.changes, [])
        self.assert_no_temporary_files()

    def test_callback_failure_does_not_undo_committed_settings(self):
        self.store.load()
        self.store.set_on_change(Mock(side_effect=RuntimeError('private callback content')))
        self.assertTrue(self.store.update_hotkeys({'toggle_mod': ['F5']}))
        self.assertEqual(self.disk()['hotkeys']['toggle_mod'], ['F5'])
        self.assertEqual(self.store.get_payload()['hotkeys']['toggle_mod'], ['F5'])
        self.assertIsNone(self.store.last_error)
        self.assertIn('settings callback_failed', self.logs)
        self.assertNotIn('private callback content', '\n'.join(self.logs))

    def test_temporary_cleanup_failure_after_exclusive_creation_is_still_a_commit(self):
        with patch.object(settings.os, 'unlink', side_effect=OSError('cleanup unavailable')):
            self.assertTrue(self.store.update_hotkeys({'toggle_mod': ['F5']}))
        self.assertEqual(self.disk()['hotkeys']['toggle_mod'], ['F5'])
        self.assertEqual(self.store.get_payload()['hotkeys']['toggle_mod'], ['F5'])
        self.assertEqual(len(self.changes), 1)
        self.assertIsNone(self.store.last_error)

    def test_windows_replace_uses_unicode_and_write_through_without_delete(self):
        move = Mock(return_value=1)
        kernel = types.SimpleNamespace(MoveFileExW=move)
        with patch.object(settings.os, 'name', 'nt'), \
                patch.object(settings.ctypes, 'WinDLL', return_value=kernel, create=True), \
                patch.object(settings, '_windows_path', side_effect=lambda value: value):
            settings._replace_file('temporary', 'existing', True)
            self.assertEqual(move.call_args.args, ('temporary', 'existing', 0x9))
            settings._replace_file('temporary', 'new', False)
            self.assertEqual(move.call_args.args, ('temporary', 'new', 0x8))
        self.assertEqual(move.argtypes, (settings.ctypes.c_wchar_p,
                                        settings.ctypes.c_wchar_p, settings.ctypes.c_uint32))

    def test_windows_replace_failure_is_reported(self):
        move = Mock(return_value=0)
        kernel = types.SimpleNamespace(MoveFileExW=move)
        with patch.object(settings.os, 'name', 'nt'), \
                patch.object(settings.ctypes, 'WinDLL', return_value=kernel, create=True), \
                patch.object(settings.ctypes, 'get_last_error', return_value=5, create=True), \
                patch.object(settings, '_windows_path', side_effect=lambda value: value), \
                self.assertRaises(OSError):
            settings._replace_file('temporary', 'existing', True)


if __name__ == '__main__':
    unittest.main()
