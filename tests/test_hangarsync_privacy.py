"""Publication-boundary regression tests use synthetic data and temporary files."""
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('hangar_ci_privacy', ROOT / 'scripts/hangarsync/privacy.py')
privacy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(privacy)
PYTHON27 = os.environ.get('PYTHON27')


def archive(contents):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, 'w') as result:
        for name, data in contents.items():
            result.writestr(name, data)
    return stream.getvalue()


class HangarPrivacyTests(unittest.TestCase):
    def test_empty_example_is_strict_and_cannot_hide_a_new_private_field(self):
        self.assertTrue(privacy.clean_example(json.dumps(privacy.EXAMPLE).encode()))
        for change in ({'enabled': True}, {'allowed_players': ['SYNTHETIC_PLAYER']},
                       {'device_token': 'SYNTHETIC_SECRET'}, {'region': 'NA'},
                       {'expected_player': 'SYNTHETIC_PLAYER'}, {'password': 'SYNTHETIC_SECRET'}):
            with self.subTest(change=change):
                self.assertFalse(privacy.clean_example(json.dumps(dict(privacy.EXAMPLE, **change)).encode()))

    def test_duplicate_example_fields_cannot_hide_personal_values(self):
        clean = json.dumps(privacy.EXAMPLE)
        duplicate = '{"allowed_players":["SYNTHETIC_PLAYER"],' + clean[1:]
        self.assertFalse(privacy.clean_example(duplicate.encode()))
        problems = privacy.scan_bytes('GRZ_Hangar_Sync.json.example', duplicate.encode(), None)
        self.assertIn('personalized_example', problems[0][1])

    def test_tokens_private_endpoints_and_local_paths_are_classified(self):
        token = 'wgs_' + 'b' * 64
        site = 'https://' + 'synthetic-private.chatgpt.site/api/sync'
        account = 'databaseID = ' + str(123456789)
        for value, expected in ((token, 'wot_device_token'), (site, 'private_site_endpoint'),
                                (account, 'literal_game_account_id'),
                                ('/' + 'home/SYNTHETIC_USER/data', 'unix_home_directory')):
            with self.subTest(label=expected):
                labels = privacy.text_labels(value)
                self.assertIn(expected, labels)
                self.assertNotIn(value, json.dumps(labels))

    def test_fixture_and_documentation_exemptions_are_exact_and_scoped(self):
        fixture = 'https://' + 'private-example.chatgpt.site/api/sync'
        self.assertNotIn('private_site_endpoint', privacy.text_labels(fixture, fixture=True))
        self.assertIn('private_site_endpoint', privacy.text_labels(fixture))
        other = 'https://' + 'other-private.chatgpt.site/api/sync'
        self.assertIn('private_site_endpoint', privacy.text_labels(other, fixture=True))
        docs = 'https://' + 'YOUR-SITE.chatgpt.site/api/sync'
        self.assertNotIn('private_site_endpoint', privacy.text_labels(docs, documentation=True))
        self.assertIn('private_site_endpoint', privacy.text_labels(docs))

    def test_nested_archive_cannot_hide_a_secret_or_personal_configuration(self):
        token = 'wgs_' + 'c' * 64
        inner = archive({'module.py': token, 'mods/configs/GRZ_Hangar_Sync.json': '{}'})
        problems = privacy.scan_bytes('synthetic-installer.zip', archive({'inner.wotmod': inner}), None)
        labels = {label for _, values in problems for label in values}
        self.assertIn('wot_device_token', labels)
        self.assertIn('forbidden_resource', labels)
        self.assertNotIn(token, json.dumps(problems))

    def test_archive_traversal_duplicates_and_excessive_recursion_fail_closed(self):
        for data in (archive({'../escape.py': 'safe'}), archive({'/absolute.py': 'safe'})):
            self.assertIn('unsafe_archive_member', privacy.scan_bytes('synthetic.zip', data, None)[0][1])
        self.assertEqual(privacy.scan_bytes('synthetic.py', b'x', None, depth=5)[0][1], ['archive_budget'])

    def test_personalized_example_and_missing_python27_are_rejected(self):
        self.assertIn('personalized_example', privacy.scan_bytes(
            'GRZ_Hangar_Sync.json.example', b'{"enabled":true}', None)[0][1])
        self.assertEqual(privacy.bytecode_labels(b'not-code', None), ['python27_required'])

    @unittest.skipUnless(PYTHON27, 'Set PYTHON27 for the isolated bytecode decoder test')
    def test_python27_constant_and_filename_scan_never_executes_candidate(self):
        # Create only synthetic bytecode in a temporary directory, never a mod build.
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'synthetic.pyc'
            token = 'wgs_' + 'd' * 64
            marker = Path(temporary) / 'MUST_NOT_EXIST'
            source = 'secret = %r\nopen(%r, "w").write("not allowed")\n' % (token, str(marker))
            script = ('import marshal, struct, sys\n'
                      'code=compile(sys.argv[1], "res/scripts/client/gui/mods/synthetic.py", "exec")\n'
                      'open(sys.argv[2],"wb").write("\\x03\\xf3\\r\\n"+struct.pack("<I",0)+marshal.dumps(code))\n')
            subprocess.check_call([PYTHON27, '-B', '-c', script, source, str(path)])
            labels = privacy.bytecode_labels(path.read_bytes(), PYTHON27)
            self.assertIn('wot_device_token', labels)
            self.assertFalse(marker.exists())
            self.assertNotIn(token, json.dumps(labels))


if __name__ == '__main__':
    unittest.main()
