"""Settings preserve data without optional embedded native extensions."""
import builtins
import errno
import importlib.util
import os
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
        self.backup = self.path.with_name(self.path.name + settings.BACKUP_SUFFIX)
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

    def windows_rename(self, source, destination):
        # Model Windows Python 2.7: rename may create, never overwrite.
        if os.path.lexists(destination):
            raise OSError(errno.EEXIST, 'destination exists')
        self.real_rename(source, destination)

    def windows_fallback(self, rename=None):
        self.real_rename = settings.os.rename
        return (patch.object(settings.os, 'name', 'nt'),
                patch.object(settings.os, 'replace', None, create=True),
                patch.object(settings.os, 'rename', rename or self.windows_rename))

    def test_import_and_windows_save_do_not_attempt_optional_native_modules(self):
        original_import = builtins.__import__
        def guarded_import(name, *args, **kwargs):
            if name in ('ctypes', '_ctypes'):
                raise AssertionError('optional native dependency was imported')
            return original_import(name, *args, **kwargs)
        spec = importlib.util.spec_from_file_location(PACKAGE + '.without_native', SOURCE / 'settings.py')
        module = importlib.util.module_from_spec(spec)
        with patch.object(builtins, '__import__', guarded_import):
            spec.loader.exec_module(module)
            store = module.SettingsStore(str(self.path))
            store.load()
            self.real_rename = os.rename
            with patch.object(module.os, 'name', 'nt'), \
                    patch.object(module.os, 'replace', None, create=True), \
                    patch.object(module.os, 'rename', self.windows_rename):
                self.assertTrue(store.update_hotkeys({'toggle_mod': ['F5']}))
        self.assertEqual(self.disk()['hotkeys']['toggle_mod'], ['F5'])
        self.assertFalse(self.backup.exists())

    def test_windows_fallback_replaces_without_deleting_primary_first(self):
        self.write({'language': 'pl', 'voice_volume': 35, 'unknown': {'keep': True}})
        self.store.load()
        calls = []
        def renamed(source, destination):
            calls.append((source, destination))
            if source == str(self.path):
                self.assertFalse(self.backup.exists())
            else:
                self.assertFalse(self.path.exists())
                self.assertEqual(json.loads(self.backup.read_text())['unknown'], {'keep': True})
            self.windows_rename(source, destination)
        first, second, third = self.windows_fallback(renamed)
        with first, second, third:
            self.assertTrue(self.store.update_hotkeys({'toggle_mod': ['F5']}))
        self.assertEqual(calls[0], (str(self.path), str(self.backup)))
        self.assertEqual(len(calls), 2)
        self.assertEqual(self.disk()['language'], 'pl')
        self.assertEqual(self.disk()['voice_volume'], 35)
        self.assertEqual(self.disk()['unknown'], {'keep': True})
        self.assertEqual(self.disk()['hotkeys']['toggle_mod'], ['F5'])
        self.assertEqual(self.store.get_payload()['hotkeys']['toggle_mod'], ['F5'])
        self.assertEqual(len(self.changes), 1)
        self.assertFalse(self.backup.exists())
        self.assert_no_temporary_files()

    def test_windows_existing_os_replace_is_used_without_backup(self):
        self.store.load()
        replace = Mock(wraps=os.replace)
        with patch.object(settings.os, 'name', 'nt'), patch.object(settings.os, 'replace', replace):
            self.assertTrue(self.store.update_hotkeys({'toggle_mod': ['F5']}))
        self.assertEqual(replace.call_count, 1)
        self.assertFalse(self.backup.exists())
        self.assertEqual(self.disk()['hotkeys']['toggle_mod'], ['F5'])

    def test_windows_first_move_failure_leaves_original_and_memory_intact(self):
        initial = self.store.load()
        original = self.path.read_bytes()
        first, second, third = self.windows_fallback(Mock(side_effect=OSError('move denied')))
        with first, second, third:
            self.assertFalse(self.store.update_hotkeys({'toggle_mod': ['F5']}))
        self.assertEqual(self.path.read_bytes(), original)
        self.assertEqual(self.store.get_payload(), initial)
        self.assertFalse(self.backup.exists())
        self.assertEqual(self.changes, [])
        self.assert_no_temporary_files()

    def test_windows_second_move_failure_rolls_back_complete_original(self):
        initial = self.store.load()
        original = self.path.read_bytes()
        calls = []
        def failed_move(source, destination):
            calls.append((source, destination))
            if len(calls) == 2:
                raise OSError('install denied')
            self.windows_rename(source, destination)
        first, second, third = self.windows_fallback(failed_move)
        with first, second, third:
            self.assertFalse(self.store.update_hotkeys({'toggle_mod': ['F5']}))
        self.assertEqual(len(calls), 3)
        self.assertEqual(self.path.read_bytes(), original)
        self.assertEqual(self.store.get_payload(), initial)
        self.assertFalse(self.backup.exists())
        self.assertEqual(self.changes, [])
        self.assert_no_temporary_files()

    def test_windows_failed_rollback_recovers_original_on_next_load(self):
        initial = self.store.load()
        original = self.path.read_bytes()
        calls = []
        def failed_moves(source, destination):
            calls.append((source, destination))
            if len(calls) in (2, 3):
                raise OSError('install or rollback denied')
            self.windows_rename(source, destination)
        first, second, third = self.windows_fallback(failed_moves)
        with first, second, third:
            self.assertFalse(self.store.update_hotkeys({'toggle_mod': ['F5']}))
        self.assertFalse(self.path.exists())
        self.assertEqual(self.backup.read_bytes(), original)
        self.assertEqual(self.store.get_payload(), initial)
        self.assertEqual(self.changes, [])
        first, second, third = self.windows_fallback()
        with first, second, third:
            recovered = settings.SettingsStore(str(self.path)).load()
        self.assertEqual(self.path.read_bytes(), original)
        self.assertEqual(recovered, initial)
        self.assertFalse(self.backup.exists())
        self.assert_no_temporary_files()

    def test_stopped_process_between_moves_restores_previous_choices(self):
        class StoppedProcess(BaseException):
            pass
        initial = self.store.load()
        original = self.path.read_bytes()
        def stopped(source, destination):
            self.windows_rename(source, destination)
            if source == str(self.path):
                raise StoppedProcess()
        first, second, third = self.windows_fallback(stopped)
        with first, second, third, self.assertRaises(StoppedProcess):
            self.store.update_hotkeys({'toggle_mod': ['F5']})
        self.assertFalse(self.path.exists())
        self.assertEqual(self.backup.read_bytes(), original)
        self.assertEqual(self.changes, [])
        first, second, third = self.windows_fallback()
        with first, second, third:
            loaded = settings.SettingsStore(str(self.path)).load()
        self.assertEqual(loaded, initial)
        self.assertEqual(self.path.read_bytes(), original)
        self.assertFalse(self.backup.exists())

    def test_stopped_process_after_publication_keeps_new_complete_choices(self):
        class StoppedProcess(BaseException):
            pass
        self.store.load()
        original = self.path.read_bytes()
        def stopped(source, destination):
            self.windows_rename(source, destination)
            if source != str(self.path):
                raise StoppedProcess()
        first, second, third = self.windows_fallback(stopped)
        with first, second, third, self.assertRaises(StoppedProcess):
            self.store.update_hotkeys({'toggle_mod': ['F5']})
        self.assertEqual(self.disk()['hotkeys']['toggle_mod'], ['F5'])
        self.assertEqual(self.backup.read_bytes(), original)
        self.assertEqual(self.changes, [])
        loaded = settings.SettingsStore(str(self.path)).load()
        self.assertEqual(loaded['hotkeys']['toggle_mod'], ['F5'])
        self.assertFalse(self.backup.exists())

    def test_missing_primary_recovers_backup_before_creating_defaults(self):
        source = {'language': 'uk', 'enabled': False, 'voice_volume': 17,
                  'hotkeys': {'toggle_mod': ['F9'], 'toggle_voice': ['F10']},
                  'future': ['preserved']}
        self.write(source)
        original = self.path.read_bytes()
        self.path.rename(self.backup)
        first, second, third = self.windows_fallback()
        with first, second, third:
            loaded = self.store.load()
        self.assertEqual(loaded['language'], 'uk')
        self.assertEqual(loaded['hotkeys'], source['hotkeys'])
        self.assertEqual(self.path.read_bytes(), original)
        self.assertFalse(self.backup.exists())
        self.assertEqual(self.changes, [])

    def test_complete_new_primary_wins_after_interrupted_backup_cleanup(self):
        self.write({'language': 'pl', 'hotkeys': {'toggle_mod': ['F5']}})
        new_bytes = self.path.read_bytes()
        self.backup.write_text(json.dumps({'language': 'en', 'hotkeys': {'toggle_mod': ['F6']}}))
        loaded = self.store.load()
        self.assertEqual(loaded['hotkeys']['toggle_mod'], ['F5'])
        self.assertEqual(self.path.read_bytes(), new_bytes)
        self.assertFalse(self.backup.exists())

    def test_malformed_primary_keeps_recovery_backup_and_is_never_rewritten(self):
        self.store.load()
        backup_bytes = self.path.read_bytes()
        self.backup.write_bytes(backup_bytes)
        malformed = b'{invalid private configuration'
        self.path.write_bytes(malformed)
        self.store.load()
        self.assertFalse(self.store.update_hotkeys({'toggle_mod': ['F5']}))
        self.assertEqual(self.path.read_bytes(), malformed)
        self.assertEqual(self.backup.read_bytes(), backup_bytes)
        self.assertEqual(self.changes, [])

    def test_invalid_or_oversized_backup_does_not_create_defaults(self):
        self.path.parent.mkdir(parents=True)
        for invalid in (b'{invalid backup', b'[]', b'x' * (settings.CONFIG_MAX_BYTES + 1)):
            with self.subTest(invalid_prefix=invalid[:8]):
                self.backup.write_bytes(invalid)
                self.assertEqual(self.store.load(), settings.DEFAULTS)
                self.assertFalse(self.store.update_hotkeys({'toggle_mod': ['F5']}))
                self.assertFalse(self.path.exists())
                self.assertEqual(self.backup.read_bytes(), invalid)
                self.assertEqual(self.changes, [])

    def test_existing_invalid_backup_is_never_overwritten_by_fallback_write(self):
        initial = self.store.load()
        original = self.path.read_bytes()
        unexpected = b'unexpected recovery artifact'
        self.backup.write_bytes(unexpected)
        first, second, third = self.windows_fallback()
        with first, second, third:
            self.assertEqual(self.store.load(), initial)
            self.assertFalse(self.store.update_hotkeys({'toggle_mod': ['F5']}))
        self.assertEqual(self.path.read_bytes(), original)
        self.assertEqual(self.backup.read_bytes(), unexpected)
        self.assertEqual(self.store.get_payload(), initial)
        self.assertEqual(self.changes, [])
        self.assert_no_temporary_files()

    def test_windows_backup_cleanup_failure_is_still_a_successful_commit(self):
        self.store.load()
        original = self.path.read_bytes()
        unlink = os.unlink
        def cleanup(path):
            if path == str(self.backup):
                raise OSError('backup cleanup denied')
            return unlink(path)
        first, second, third = self.windows_fallback()
        with first, second, third, patch.object(settings.os, 'unlink', cleanup):
            self.assertTrue(self.store.update_hotkeys({'toggle_mod': ['F5']}))
        self.assertEqual(self.disk()['hotkeys']['toggle_mod'], ['F5'])
        self.assertEqual(self.store.get_payload()['hotkeys']['toggle_mod'], ['F5'])
        self.assertEqual(self.backup.read_bytes(), original)
        self.assertEqual(len(self.changes), 1)
        self.assertIsNone(self.store.last_error)
        self.store.load()
        self.assertFalse(self.backup.exists())

    def test_concurrent_edit_just_before_old_file_move_is_restored_not_clobbered(self):
        initial = self.store.load()
        external = {'language': 'de', 'changed_before_move': True}
        def changed(source, destination):
            if source == str(self.path):
                self.write(external)
            self.windows_rename(source, destination)
        first, second, third = self.windows_fallback(changed)
        with first, second, third:
            self.assertFalse(self.store.update_hotkeys({'toggle_mod': ['F5']}))
        self.assertEqual(self.disk(), external)
        self.assertEqual(self.store.get_payload(), initial)
        self.assertEqual(self.changes, [])
        self.assertFalse(self.backup.exists())

    def test_concurrent_primary_created_during_gap_is_not_overwritten_by_rollback(self):
        initial = self.store.load()
        original = self.path.read_bytes()
        external = {'language': 'fr', 'created_during_gap': True}
        def created(source, destination):
            if source != str(self.path) and source != str(self.backup):
                self.write(external)
            self.windows_rename(source, destination)
        first, second, third = self.windows_fallback(created)
        with first, second, third:
            self.assertFalse(self.store.update_hotkeys({'toggle_mod': ['F5']}))
        self.assertEqual(self.disk(), external)
        self.assertEqual(self.backup.read_bytes(), original)
        self.assertEqual(self.store.get_payload(), initial)
        self.assertEqual(self.changes, [])
        self.store.load()
        self.assertEqual(self.disk(), external)
        self.assertFalse(self.backup.exists())

    def test_windows_first_creation_refuses_concurrent_primary(self):
        external = {'language': 'pl', 'concurrently_created': True}
        def created(source, destination):
            self.write(external)
            self.windows_rename(source, destination)
        first, second, third = self.windows_fallback(created)
        with first, second, third:
            self.assertFalse(self.store.update_hotkeys({'toggle_mod': ['F5']}))
        self.assertEqual(self.disk(), external)
        self.assertEqual(self.changes, [])
        self.assert_no_temporary_files()


if __name__ == '__main__':
    unittest.main()
