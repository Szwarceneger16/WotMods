"""Check reproducible, self-contained packaging and privacy constraints."""
import importlib.util
import hashlib
from pathlib import Path
import unittest
import zipfile


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('dual_zoom_build', ROOT / 'build.py')
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)


class TestBuild(unittest.TestCase):
    def test_exact_content_and_python_27_bootstrap(self):
        target = build.build()
        self.assertTrue(build.verify(target))
        with zipfile.ZipFile(target) as archive:
            names = archive.namelist()
            self.assertEqual(set(names), {'meta.xml', build.PYC, build.TEXTURE})
            self.assertTrue(all(name.startswith(('res/', 'meta.xml')) for name in names))
            pyc = archive.read(build.PYC)
            self.assertEqual(pyc[:4], build.MAGIC_PY27)
            self.assertEqual(pyc[8:9], b'c')
            self.assertIn(bytes((85, 100, 1, 0, 83)), pyc)
            self.assertIn(b'PySceneRenderer', pyc)
            self.assertTrue(all(entry.compress_type == zipfile.ZIP_STORED
                                for entry in archive.infolist()))
            self.assertLess(target.stat().st_size, 100000)

    def test_reproducible_build(self):
        path = build.build()
        first = hashlib.sha256(path.read_bytes()).digest()
        build.build()
        self.assertEqual(first, hashlib.sha256(path.read_bytes()).digest())

    def test_dds_has_expected_header_and_no_executables(self):
        payload = build.solid_dds()
        self.assertEqual(payload[:4], b'DDS ')
        self.assertEqual(len(payload), 128 + 16*16*4)
        self.assertNotIn(b'MZ', payload[:4])
        self.assertEqual(len(build.resources()), 3)

    def test_runtime_remains_read_only_probe_except_local_logs(self):
        data = build.SOURCE.read_bytes()
        self.assertTrue(data.isascii())
        for banned in (b'import socket', b'import requests', b'urlopen',
                       b'ctypes', b'DirectX', b'CreateRemoteThread',
                       b'screenshot', b'upload'):
            self.assertNotIn(banned, data)


if __name__ == '__main__':
    unittest.main()
