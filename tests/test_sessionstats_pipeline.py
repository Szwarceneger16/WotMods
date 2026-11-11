"""Separate namespaces, complete checksums and immutable/resumable publications."""
import importlib.util
import io
import json
from pathlib import Path
import re
import sys
import shutil
import subprocess
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT/'scripts/sessionstats'/filename)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


release = load('sessionstats_release', 'release.py')
privacy = load('sessionstats_privacy', 'privacy.py')
source_state = load('sessionstats_source_state', 'source_state.py')
sys.path.insert(0, str(ROOT/'scripts/sessionstats'))
artifacts = load('sessionstats_artifacts', 'artifacts.py')


class SessionStatsPipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.version = '0.2.9'
        for name in ('grz.sessionstats_0.2.9.wotmod', 'wot-statystyki-sesji-v0.2.9.zip',
                     'net.openwg.gameface_1.2.2.wotmod', 'grz.sessionstats.json'):
            (self.folder/name).write_bytes(b'synthetic-artifact')
        (self.folder/'BUILD.json').write_text(json.dumps({'version':self.version,'python_bytecode':'2.7'}))
        self.checksums()

    def checksums(self):
        (self.folder/'SHA256SUMS.txt').write_text(''.join(release.sha256(p)+'  '+p.name+'\n'
            for p in sorted(self.folder.iterdir()) if p.name != 'SHA256SUMS.txt'))

    def test_all_six_assets_validate(self):
        self.assertEqual(len(release.inputs(self.folder, self.version)), 6)

    def test_pr_download_selects_only_the_release_installer_without_wrapping_it(self):
        workflow = (ROOT/'.github/workflows/sessionstats-ci.yml').read_text()
        upload = workflow.split('uses: actions/upload-artifact@', 1)[1]
        path = re.search(r'^          path: (.+)$', upload, re.MULTILINE).group(1)
        self.assertEqual(path, 'pr-artifact-sessionstats/Session-Stats-v*.zip')
        self.assertRegex(upload, r'(?m)^          archive: false$')
        self.assertRegex(upload, r'(?m)^          if-no-files-found: error$')
        self.assertLess(workflow.index('run: bash scripts/sessionstats/validate.sh'),
                        workflow.index('scripts/release_installers.py package pr-artifact-sessionstats'))
        self.assertLess(workflow.index('scripts/release_installers.py package pr-artifact-sessionstats'),
                        workflow.index('uses: actions/upload-artifact@'))
        self.assertIn('--source mods/sessionstats/dist --mod sessionstats', workflow)
        # PR and production package the identical installer format, but only
        # production allocates versions and publishes protected Releases.
        builder = (ROOT/'scripts/build_release_module.sh').read_text()
        publisher = (ROOT/'.github/workflows/wotmods-release.yml').read_text()
        self.assertIn('scripts/sessionstats/release.py --verify-directory', builder)
        self.assertIn('scripts/release_installers.py package release-module', builder)
        self.assertIn('path: release-module/*.zip', publisher)
        self.assertNotIn('archive: false', publisher)

    def test_browser_environment_is_prepared_before_compilation_without_skipping_validation(self):
        workflow = (ROOT/'.github/workflows/sessionstats-ci.yml').read_text()
        command = 'python3 -I scripts/sessionstats/browser_qa.py --prepare'
        self.assertIn(command, workflow)
        start = workflow.rfind('      - name:', 0, workflow.index(command))
        stop = workflow.find('\n      - ', workflow.index(command))
        preparation = workflow[start:stop]
        self.assertIn("if: steps.source.outputs.enabled == 'true'", preparation)
        self.assertLess(workflow.index('id: source'), start)
        self.assertLess(start, workflow.index('run: bash scripts/sessionstats/python27.sh'))
        self.assertIn('contents: read', workflow)
        self.assertNotIn('contents: write', workflow)
        self.assertNotRegex(preparation, r'\|\|\s*(?:true|:)')

    def test_both_pr_and_production_keep_the_complete_validation_transaction(self):
        validate = (ROOT/'scripts/sessionstats/validate.sh').read_text()
        markers = (
            'python3 -m unittest discover -s mods/sessionstats/tests -v',
            '"$PYTHON27" -B -m unittest discover -s mods/sessionstats/tests -v',
            'python3 mods/sessionstats/tools/make_preview.py',
            'python3 -I scripts/sessionstats/browser_qa.py',
            'python3 mods/sessionstats/tools/build.py',
            'python3 scripts/sessionstats/artifacts.py snapshot',
            'python3 mods/sessionstats/tools/build.py',
            'python3 scripts/sessionstats/artifacts.py verify',
            'python3 scripts/sessionstats/integration.py',
            'python3 scripts/sessionstats/privacy.py --python27 "$PYTHON27" --scan-dist',
        )
        offset = 0
        for marker in markers:
            with self.subTest(stage=marker):
                position = validate.find(marker, offset)
                self.assertGreaterEqual(position, offset, 'The full validation order must remain intact')
                offset = position + len(marker)
        self.assertIn('set -euo pipefail', validate)
        self.assertEqual(validate.count('python3 mods/sessionstats/tools/build.py'), 2)
        self.assertNotIn('install --with-deps', validate)
        self.assertNotIn('apt-get', validate)
        builder = (ROOT/'scripts/build_release_module.sh').read_text()
        self.assertIn('bash scripts/sessionstats/validate.sh', builder)
        self.assertIn('run: bash scripts/sessionstats/validate.sh',
                      (ROOT/'.github/workflows/sessionstats-ci.yml').read_text())

    def test_second_installer_blocks_validation_even_with_valid_checksums(self):
        (self.folder/'wot-statystyki-sesji-v0.2.8.zip').write_bytes(b'stale')
        self.checksums()
        with self.assertRaises(release.ValidationError):
            release.inputs(self.folder, self.version)

    def test_changed_asset_hash_blocks_before_remote_operations(self):
        (self.folder/'grz.sessionstats.json').write_text('changed')
        with self.assertRaises(release.ValidationError): release.inputs(self.folder, self.version)

    def test_additional_stale_build_blocks_publication(self):
        (self.folder/'grz.sessionstats_0.2.8.wotmod').write_bytes(b'stale')
        self.checksums()
        with self.assertRaises(release.ValidationError): release.inputs(self.folder, self.version)

    def test_incorrect_runtime_version_blocks_publication(self):
        (self.folder/'BUILD.json').write_text(json.dumps({'version':'0.2.8','python_bytecode':'2.7'}))
        self.checksums()
        with self.assertRaises(release.ValidationError): release.inputs(self.folder, self.version)

    def test_nested_archives_do_not_hide_credentials(self):
        inner = io.BytesIO()
        with zipfile.ZipFile(inner, 'w') as z:
            z.writestr('ui/script.js', 'const token = "ghp_' + 'A'*40 + '";')
        outer = io.BytesIO()
        with zipfile.ZipFile(outer, 'w') as z: z.writestr('dependency.wotmod', inner.getvalue())
        issues = privacy.scan_bytes('release.zip', outer.getvalue(), None)
        self.assertIn('github_classic_token', issues[0][1])

    def test_private_history_and_logs_are_rejected(self):
        for filename in ('player.db', 'session-stats.log', 'crash.dmp', 'credential.p12', 'credential.P12'):
            self.assertEqual(privacy.scan_bytes(filename,b'',None)[0][1], ['forbidden_resource'])

    def test_nested_binary_pkcs12_is_rejected_without_textual_secret(self):
        inner = io.BytesIO()
        with zipfile.ZipFile(inner, 'w') as z: z.writestr('certificate.P12', b'\x30\x82\x00\xff\x01')
        outer = io.BytesIO()
        with zipfile.ZipFile(outer, 'w') as z: z.writestr('dependency.wotmod', inner.getvalue())
        self.assertEqual(privacy.scan_bytes('release.zip', outer.getvalue(), None),
                         [('release.zip:dependency.wotmod:certificate.P12', ['forbidden_resource'])])

    def test_reproducibility_snapshot_covers_all_six_published_files(self):
        expected = artifacts.snapshot(self.folder)
        self.assertEqual(set(expected), set(release.inputs(self.folder, self.version)))
        self.assertEqual(len(expected), 6)
        artifacts.verify(self.folder, expected)

    def test_mutating_any_asset_and_regenerating_checksums_still_fails_reproducibility(self):
        original = {p.name:p.read_bytes() for p in self.folder.iterdir()}
        expected = artifacts.snapshot(self.folder)
        for name in sorted(original):
            with self.subTest(asset=name):
                for saved, value in original.items(): (self.folder/saved).write_bytes(value)
                if name == 'BUILD.json':
                    report = json.loads(original[name]); report['extra'] = 'changed by rebuild'
                    (self.folder/name).write_text(json.dumps(report))
                elif name == 'SHA256SUMS.txt':
                    lines = original[name].decode('ascii').splitlines()
                    (self.folder/name).write_text('\n'.join(reversed(lines))+'\n')
                else:
                    (self.folder/name).write_bytes(original[name] + b'changed by rebuild')
                if name != 'SHA256SUMS.txt': self.checksums()
                with self.assertRaises(artifacts.ValidationError): artifacts.verify(self.folder, expected)


class SourceStateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)/'repo'
        self.folder.mkdir()
        self.git('init', '-q', '-b', 'main')
        self.git('config', 'user.name', 'Synthetic fixture')
        self.git('config', 'user.email', 'fixture.invalid')
        self.git('commit', '--allow-empty', '-qm', 'Infrastructure before import')

    def git(self, *args):
        return subprocess.check_output(['git','-C',str(self.folder),*args], text=True, stderr=subprocess.STDOUT)

    def import_source(self):
        entry = self.folder/source_state.ENTRY
        entry.parent.mkdir(parents=True)
        entry.write_text('# synthetic fixture\n')
        self.git('add', '.')
        self.git('commit', '-qm', 'Import source')
        return entry

    def test_absent_source_is_allowed_before_any_import(self):
        self.assertFalse(source_state.source_enabled(self.folder))

    def test_present_entrypoint_enables_source_validation(self):
        self.import_source()
        self.assertTrue(source_state.source_enabled(self.folder))

    def test_misnamed_entrypoint_fails_instead_of_skipping(self):
        entry = self.import_source()
        entry.rename(entry.with_name('misnamed.py'))
        with self.assertRaises(RuntimeError): source_state.source_enabled(self.folder)

    def test_deleting_entire_source_directory_fails_from_history(self):
        self.import_source()
        shutil.rmtree(self.folder/source_state.SOURCE)
        self.git('add', '-u'); self.git('commit', '-qm', 'Remove all source')
        with self.assertRaises(RuntimeError): source_state.source_enabled(self.folder)

    def test_shallow_history_cannot_authorize_skipping(self):
        self.import_source()
        shutil.rmtree(self.folder/source_state.SOURCE)
        self.git('add', '-u'); self.git('commit', '-qm', 'Remove all source')
        clone = self.folder.parent/'shallow'
        subprocess.check_output(['git','clone','-q','--depth','1',self.folder.as_uri(),str(clone)], stderr=subprocess.STDOUT)
        with self.assertRaises(RuntimeError): source_state.source_enabled(clone)


if __name__ == '__main__': unittest.main()
