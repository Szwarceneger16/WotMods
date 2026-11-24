"""Windows-compatible bounded log rotation; tests only the runtime helpers."""
import ast
import os
from pathlib import Path
import tempfile
import time
from unittest import TestCase, mock

ROOT = Path(__file__).resolve().parents[1]


def load_logger():
    # Extract original implementation, avoiding imports of unavailable WoT DLLs.
    original = ast.parse((ROOT / 'src/mod_staysharp_medkit.py').read_text())
    function = next(n for n in original.body
                    if isinstance(n, ast.FunctionDef) and n.name == '_log')
    ast.fix_missing_locations(function)
    env = dict(os=os, time=time, TAG='[StaySharpMedkit]', _log_file=None)
    exec(compile(ast.Module(body=[function], type_ignores=[]), '<runtime-log>', 'exec'), env)
    return env


class LogRotationTests(TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.folder = Path(self.tmp.name) / 'StaySharpMedkit'
        self.folder.mkdir()
        self.log_path = self.folder / 'staysharp.log'
        self.backup = self.folder / 'staysharp.log.old'
        self.env = load_logger()
        self.patcher = mock.patch.dict(os.environ, {'LOCALAPPDATA': self.tmp.name})
        self.patcher.start()
        self.addCleanup(self.patcher.stop)

    def log(self, message):
        with mock.patch('builtins.print'):
            self.env['_log'](message)

    def test_existing_backup_is_removed_before_windows_rename(self):
        self.log_path.write_bytes(b'a' * 524289)
        self.backup.write_bytes(b'older backup')
        real_rename = os.rename

        def windows_rename(source, target):
            if os.path.exists(target):
                raise OSError('Windows refuses overwriting rename')
            return real_rename(source, target)

        with mock.patch.object(os, 'rename', side_effect=windows_rename):
            self.log('after first rotation')
            self.assertEqual(self.backup.stat().st_size, 524289)
            self.assertLess(self.log_path.stat().st_size, 512)
            self.log_path.write_bytes(b'b' * 524289)
            self.log('after second rotation')
            self.assertEqual(self.backup.read_bytes()[:1], b'b')
            self.assertLess(self.log_path.stat().st_size, 512)

    def test_rotation_works_after_first_write_during_one_session(self):
        self.log('first')
        self.log_path.write_bytes(b'a' * 524289)
        self.log('in the same running session')
        self.assertTrue(self.backup.exists())
        self.assertLess(self.log_path.stat().st_size, 512)

    def test_unrecoverable_rename_truncates_to_prevent_growth(self):
        self.log_path.write_bytes(b'a' * 524289)
        with mock.patch.object(os, 'rename', side_effect=OSError('locked')):
            self.log('rotation fallback')
        self.assertLess(self.log_path.stat().st_size, 512)
        self.assertIn(b'rotation fallback', self.log_path.read_bytes())

    def test_bounded_after_repeated_oversize_log_messages(self):
        for i in range(5):
            self.log('x' * 530000 + str(i))
            self.log('marker after long message')
            self.assertLess(self.log_path.stat().st_size, 524289)
            self.assertLessEqual(self.backup.stat().st_size, 530200)


if __name__ == '__main__':
    import unittest
    unittest.main()
