"""Startup isolation and embedded-client dependencies without native ctypes."""
import ast
import builtins
from contextlib import contextmanager
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

import test_mod as runtime

ROOT = Path(__file__).resolve().parents[1]


@contextmanager
def blocked_imports(*prefixes):
    original = builtins.__import__
    attempted = []
    def guarded(name, globals=None, locals=None, fromlist=(), level=0):
        requested = [name]
        requested.extend(name + '.' + item for item in (fromlist or ()) if isinstance(item, str))
        blocked = [candidate for candidate in requested
                   if any(candidate == prefix or candidate.startswith(prefix + '.') for prefix in prefixes)]
        if blocked:
            attempted.extend(blocked)
            raise ImportError('simulated unavailable embedded module')
        return original(name, globals, locals, fromlist, level)
    with patch.object(builtins, '__import__', guarded):
        yield attempted


class StartupSourceTests(unittest.TestCase):
    def test_owned_runtime_has_no_ctypes_import_dependency(self):
        paths = [ROOT / 'source/mod_staysharp_medkit.py']
        paths.extend((ROOT / 'source/staysharp_medkit').glob('*.py'))
        self.assertGreater(len(paths), 1)
        for path in paths:
            with self.subTest(source=path.name):
                tree = ast.parse(path.read_text(encoding='utf-8'))
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        self.assertFalse(any(alias.name.split('.')[0] in ('ctypes', '_ctypes') for alias in node.names))
                    elif isinstance(node, ast.ImportFrom):
                        self.assertNotIn((node.module or '').split('.')[0], ('ctypes', '_ctypes'))

    def test_cold_settings_load_create_and_windows_save_never_import_ctypes(self):
        script = r'''
import builtins, errno, json, os, sys, tempfile
sys.path.insert(0, sys.argv[1])
original_import = builtins.__import__
attempted = []
def guarded(name, globals=None, locals=None, fromlist=(), level=0):
    if name.split('.')[0] in ('ctypes', '_ctypes'):
        attempted.append(name)
        raise ImportError('embedded client has no native ctypes')
    return original_import(name, globals, locals, fromlist, level)
builtins.__import__ = guarded
from staysharp_medkit.settings import SettingsStore
with tempfile.TemporaryDirectory() as folder:
    existing = os.path.join(folder, 'existing.json')
    original = b'{"language":"pl","voice_volume":35,"unknown":{"keep":true}}'
    with open(existing, 'wb') as handle:
        handle.write(original)
    old_name, old_rename = os.name, os.rename
    old_replace = getattr(os, 'replace', None)
    def create_only_rename(source, target):
        if os.path.lexists(target):
            raise OSError(errno.EEXIST, 'Windows create-only rename')
        return old_rename(source, target)
    try:
        os.name = 'nt'
        os.rename = create_only_rename
        os.replace = None  # Python 2.7 does not expose os.replace.
        store = SettingsStore(existing)
        loaded = store.load()
        assert loaded['language'] == 'pl' and loaded['voice_volume'] == 35
        with open(existing, 'rb') as handle:
            assert handle.read() == original
        assert store.update_hotkeys({'toggle_mod': ['A', 'B', 'C']})
        with open(existing, 'rb') as handle:
            saved = json.loads(handle.read().decode('utf-8'))
        assert saved['unknown'] == {'keep': True}
        assert saved['hotkeys']['toggle_mod'] == ['A', 'B', 'C']
        fresh = SettingsStore(os.path.join(folder, 'new.json'))
        assert fresh.load()['voice_volume'] == 70 and fresh.last_error is None
        assert fresh.update_hotkeys({'toggle_voice': ['M', 'V', 'X']})
        assert not attempted, attempted
    finally:
        os.name, os.rename, os.replace = old_name, old_rename, old_replace
print('cold embedded dependency check passed')
'''
        result = subprocess.run([sys.executable, '-I', '-c', script, str(ROOT / 'source')],
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('cold embedded dependency check passed', result.stdout)


class StartupLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.game = runtime.Tests()
        self.game.setUp()
        self.mod = self.game.mod
        self.mod.fini()

    def tearDown(self):
        self.game.tearDown()

    def assert_no_handlers(self):
        self.assertEqual(self.mod._event_listeners, [])
        self.assertFalse(any(self.game.bus.listeners.values()))
        self.assertEqual(self.game.key_event.handlers, [])
        self.assertEqual(self.game.key_up_event.handlers, [])

    def test_unavailable_settings_import_never_escapes_mod_loader(self):
        with blocked_imports('staysharp_medkit.settings') as attempted:
            self.mod.init()
            self.mod.fini()
        self.assertTrue(attempted)
        self.assert_no_handlers()

    def test_fini_never_imports_a_missing_garage_module(self):
        with patch.dict(sys.modules, {'staysharp_medkit.garage': None}):
            with blocked_imports('staysharp_medkit.garage') as attempted:
                self.mod.fini()
                self.mod.fini()
        self.assertEqual(attempted, [])
        self.assert_no_handlers()

    def test_partial_event_subscription_failure_is_cleaned_up(self):
        self.game.bus.fail_on = 'onComponentUnRegistered'
        self.mod.init()
        self.mod.fini()
        self.assert_no_handlers()

    def test_optional_garage_import_error_keeps_battle_and_audio_active(self):
        from staysharp_medkit import garage
        with patch.object(garage, 'install', side_effect=ImportError('optional garage API unavailable')):
            self.mod.init()
        self.assertEqual(len(self.mod._event_listeners), 2)
        self.game.emit_register()
        self.game.state(7)
        self.assertTrue(self.mod._overlay_active)
        self.assertTrue(self.game.audio_plays)
        self.assertEqual(len(self.game.key_event.handlers), 1)
        self.assertEqual(len(self.game.key_up_event.handlers), 1)

    def test_full_init_with_ctypes_blocked_and_repeated_lifecycle_has_no_leaks(self):
        with blocked_imports('ctypes', '_ctypes') as attempted:
            for unused_cycle in range(3):
                self.mod.init()
                self.mod.init()
                self.assertEqual(len(self.mod._event_listeners), 2)
                self.game.emit_register()
                self.assertEqual(len(self.game.key_event.handlers), 1)
                self.assertEqual(len(self.game.key_up_event.handlers), 1)
                self.mod.fini()
                self.mod.fini()
                self.assert_no_handlers()
        self.assertEqual(attempted, [])


if __name__ == '__main__':
    unittest.main()
