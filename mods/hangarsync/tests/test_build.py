"""Independent installer, reproducibility and credential exclusion."""
import importlib.util
import json
from pathlib import Path
import tempfile
from zipfile import ZIP_STORED, ZipFile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('grz_hangarsync_builder', ROOT / 'tools' / 'build.py')
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class BuildTests(unittest.TestCase):
    def test_fixed_internal_name_and_reproducible_installer(self):
        first = builder.build(client_version='2.4.1.1')
        second = builder.build(client_version='2.4.1.1')
        self.assertEqual(first['sha256'], second['sha256'])
        self.assertTrue(first['installer'].endswith('GRZ_Hangar_Sync-v0.11.0.zip'))
        with ZipFile(first['wotmod']) as package:
            self.assertEqual(set(package.namelist()), {'meta.xml', builder.PYC_PATH} | {
                'res/scripts/client/gui/mods/' + name + '.pyc' for name in builder.HELPERS})
            code = package.read(builder.PYC_PATH)
            self.assertTrue(code.startswith(builder.MAGIC_PY27))
            for private_marker in (b'PRIVATE_USER_SITE_HOST', b'PRIVATE_PLAYER_ID',
                                   b'https://', b'wgs_' + b'a' * 64):
                self.assertNotIn(private_marker, code)
            self.assertTrue(all(i.compress_type == ZIP_STORED for i in package.infolist()))
        with ZipFile(first['installer']) as archive:
            contents = archive.namelist()
            self.assertEqual(sum(p.endswith('.wotmod') for p in contents), 1)
            self.assertIn('mods/2.4.1.1/GRZ_Hangar_Sync.wotmod', contents)
            example = json.loads(archive.read('mods/configs/GRZ_Hangar_Sync.json.example'))
            self.assertIs(example['enabled'], False)
            self.assertEqual(example['device_token'], '')
            self.assertEqual(example['sites_access_token'], '')
            self.assertEqual(example['endpoint_url'], '')
            self.assertEqual(example['display_name'], '')
            self.assertEqual(example['allowed_players'], [])
            self.assertNotIn('expected_player', example)
            self.assertIs(example['include_crew'], False)
            self.assertNotIn('mods/configs/GRZ_Hangar_Sync.json', contents)
            for filename in contents:
                data = archive.read(filename)
                self.assertNotIn(b'PRIVATE_USER_SITE_HOST', data)
                self.assertNotIn(b'PRIVATE_PLAYER_ID', data)

    def test_build_rejects_personalized_example(self):
        clean = json.loads(builder.CONFIG.read_bytes())
        with tempfile.TemporaryDirectory() as directory:
            example = Path(directory) / builder.CONFIG.name
            private = {'endpoint_url': 'private', 'device_token': 'private',
                       'sites_access_token': 'private', 'display_name': 'private',
                       'allowed_players': ['private'], 'expected_player': 'private'}
            for field, value in private.items():
                example.write_text(json.dumps(dict(clean, **{field: value})))
                with self.subTest(field=field), mock.patch.object(builder, 'CONFIG', example), \
                     self.assertRaisesRegex(ValueError, 'credential-free'):
                    builder.build()

    def test_invalid_client_version_does_not_build(self):
        with self.assertRaises(ValueError):
            builder.build(client_version='2.4.1')


if __name__ == '__main__':
    unittest.main()
