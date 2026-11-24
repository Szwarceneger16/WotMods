"""Release numbering and conservative privacy-audit regression tests."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


version = load('release_version', ROOT / 'scripts/release_version.py')
audit = load('privacy_audit', ROOT / 'scripts/privacy_audit.py')


class ReleaseAndPrivacyTests(unittest.TestCase):
    def test_first_workflow_run_is_base_release(self):
        self.assertEqual(version.release_version('1.6.0', 1), '1.6.0')

    def test_subsequent_workflow_runs_increase_patch(self):
        self.assertEqual(version.release_version('1.6.0', 2), '1.6.1')
        self.assertEqual(version.release_version('1.6.0', 11), '1.6.10')

    def test_malformed_version_and_run_numbers_fail(self):
        for baseline, number in [('1.6.0', 0), ('abc', 2), ('1.6.00', 2), ('1.6.0', -1)]:
            with self.subTest(baseline=baseline, number=number), self.assertRaises(ValueError):
                version.release_version(baseline, number)

    def test_email_and_windows_user_directory_are_detected(self):
        self.assertIn('email_address', audit.match_private_data('user' + chr(64) + 'example.org'))
        self.assertIn('windows_user_profile', audit.match_private_data('C:' + chr(92) + 'Users' + chr(92) + 'privateperson' + chr(92) + 'Downloads'))

    def test_sample_github_access_token_is_detected(self):
        self.assertIn('github_classic_token', audit.match_private_data('ghp_' + 'A'*40))

    def test_audit_own_source_does_not_trip_on_regex_definitions(self):
        self.assertEqual(audit.scan_root(), [])

    def test_audit_checks_archives_in_staysharp_dist(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(audit, 'ROOT', Path(directory)):
            dist = Path(directory) / 'mods/staysharp/dist'
            dist.mkdir(parents=True)
            with ZipFile(dist / 'test.wotmod', 'w') as archive:
                archive.writestr('debug.log', 'test fixture')
            self.assertEqual(audit.scan_dist(), [
                ('test.wotmod:debug.log', ['forbidden_release_resource']),
            ])


if __name__ == '__main__':
    unittest.main()
