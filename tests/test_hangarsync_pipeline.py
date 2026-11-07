"""Hangar PR builds stay scoped, read-only and directly installable."""
from pathlib import Path
import re
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / '.github/workflows/hangarsync-ci.yml'
VALIDATE = ROOT / 'scripts/hangarsync/validate.sh'


def filters(text):
    block = text.split('  pull_request:\n', 1)[1].split('    paths:\n', 1)[1]
    paths = []
    for line in block.splitlines():
        if not line.startswith('      - '):
            break
        paths.append(line.strip()[2:].strip("'\""))
    return paths


def matches(path, patterns):
    for pattern in patterns:
        regex = re.escape(pattern).replace(r'\*\*', '.*').replace(r'\*', '[^/]*')
        if re.fullmatch(regex, path):
            return True
    return False


class HangarPipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workflow = WORKFLOW.read_text(encoding='utf-8')
        cls.validate = VALIDATE.read_text(encoding='utf-8')
        cls.paths = filters(cls.workflow)

    def test_pr19_base_and_main_both_receive_builds(self):
        branch_line = self.workflow.split('  pull_request:\n', 1)[1].split('    paths:', 1)[0]
        branches = re.search(r'branches: \[([^\]]+)\]', branch_line).group(1)
        self.assertEqual({value.strip() for value in branches.split(',')},
                         {'main', 'feature/sessionstats-battle-details-timeline'})
        self.assertIn('  workflow_dispatch:', self.workflow)
        self.assertNotIn('pull_request_target', self.workflow)
        self.assertNotIn('\n  push:', self.workflow)

    def test_hangar_changes_and_its_dependencies_trigger_build(self):
        for path in ('mods/hangarsync/source/hangar_crew.py', 'mods/hangarsync/VERSION',
                     'mods/hangarsync/GRZ_Hangar_Sync.json.example',
                     'scripts/hangarsync/privacy.py', 'scripts/hangarsync/bootstrap_smoke.py',
                     'tests/test_hangarsync_pipeline.py', 'tests/test_hangarsync_privacy.py',
                     '.github/workflows/hangarsync-ci.yml', 'scripts/sessionstats/python27.sh',
                     'scripts/privacy_audit.py', 'scripts/wot_updates.py'):
            with self.subTest(path=path):
                self.assertTrue(matches(path, self.paths))

    def test_other_mods_and_unrelated_docs_do_not_trigger_hangar(self):
        for path in ('source/mod_staysharp_medkit.py', 'assets/voices/pl.wav.b85', 'VERSION',
                     'mods/sessionstats/src/grz_session_stats/runtime.py',
                     'mods/sessionstats/ui/session_stats.js', 'scripts/sessionstats/validate.sh',
                     '.github/workflows/sessionstats-ci.yml', '.github/workflows/ci.yml',
                     'README.md', 'docs/MULTIMOD_RELEASES.md'):
            with self.subTest(path=path):
                self.assertFalse(matches(path, self.paths))

    def test_existing_mod_filters_do_not_pick_hangar_sources(self):
        for workflow in ('ci.yml', 'sessionstats-ci.yml'):
            patterns = filters((ROOT / '.github/workflows' / workflow).read_text())
            for path in ('mods/hangarsync/source/mod_grz_hangar_sync.py',
                         'scripts/hangarsync/validate.sh', 'tests/test_hangarsync_pipeline.py',
                         '.github/workflows/hangarsync-ci.yml'):
                with self.subTest(workflow=workflow, path=path):
                    self.assertFalse(matches(path, patterns))

    def test_candidate_build_has_no_publication_credentials(self):
        self.assertIn('permissions:\n  contents: read', self.workflow)
        self.assertIn('persist-credentials: false', self.workflow)
        self.assertNotIn('contents: write', self.workflow)
        self.assertNotIn('secrets.', self.workflow)
        self.assertNotIn('environment:', self.workflow)
        self.assertNotIn('gh release', self.validate)
        self.assertNotIn('release_snapshot', self.validate)
        self.assertNotIn('WOT_CLIENT_VERSION', self.workflow)

    def test_verified_compiler_and_pinned_actions_are_reused(self):
        self.assertIn('bash scripts/sessionstats/python27.sh', self.workflow)
        references = re.findall(r'uses: (actions/[^\s]+)', self.workflow)
        self.assertEqual(references, [
            'actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1',
            'actions/upload-artifact@cf430e030ddbb5b0abf93d22962f4752f3646cd9',
        ])
        self.assertIn('strict: false', self.workflow)

    def test_installer_is_uploaded_as_existing_zip(self):
        upload = self.workflow.split('      - name: Upload installable Hangar Sync ZIP', 1)[1]
        self.assertIn('path: mods/hangarsync/dist/GRZ_Hangar_Sync-v*.zip', upload)
        self.assertIn('archive: false', upload)
        self.assertIn('if-no-files-found: error', upload)
        self.assertIn('retention-days: 14', upload)
        self.assertNotIn('path: mods/hangarsync/dist/*', upload)

    def test_validator_includes_real_python27_bootstrap_and_recursive_audit(self):
        self.assertIn('discover -s mods/hangarsync/tests -v', self.validate)
        self.assertIn('"$PYTHON27" -B -m unittest -v', self.validate)
        self.assertIn('test_hangar_crew test_perk_tooltips test_remembered_crew', self.validate)
        self.assertIn('"$PYTHON27" -B scripts/hangarsync/bootstrap_smoke.py', self.validate)
        self.assertIn('privacy.py --python27 "$PYTHON27" --scan-dist', self.validate)
        self.assertEqual(self.validate.count('python3 mods/hangarsync/tools/build.py'), 2)
        self.assertIn('if actual != expected:', self.validate)
        self.assertNotIn('mods/sessionstats/tools/build.py', self.validate)
        self.assertNotIn('source/build_wotmod.py', self.validate)

    def test_shell_validator_is_syntactically_valid(self):
        subprocess.check_call(['bash', '-n', str(VALIDATE)])


if __name__ == '__main__':
    unittest.main()
