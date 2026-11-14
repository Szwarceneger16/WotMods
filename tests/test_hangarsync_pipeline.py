"""PR candidates are validated; only accepted main revisions publish installers."""
from pathlib import Path
import re
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / '.github/workflows/hangarsync-ci.yml'
BUILD = ROOT / '.github/workflows/hangarsync-build.yml'
VALIDATE = ROOT / 'scripts/hangarsync/validate.sh'


def filters(text, event='pull_request'):
    block = text.split('  ' + event + ':\n', 1)[1].split('    paths:\n', 1)[1]
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


def jobs(text):
    body = text.split('\njobs:\n', 1)[1]
    return {match.group(1): match.group(2) for match in re.finditer(
        r'^  ([a-zA-Z0-9_-]+):\n(.*?)(?=^  [a-zA-Z0-9_-]+:\n|\Z)', body,
        re.MULTILINE | re.DOTALL)}


def job_condition(block):
    match = re.search(r'^    if: (.+)$', block, re.MULTILINE)
    if not match:
        raise ValueError('Every trusted build job needs an explicit trust condition')
    expression = match.group(1).strip()
    if expression in ('>', '>-', '|', '|-'):
        tail = block[match.end():]
        expression = ' '.join(line.strip() for line in re.match(r'\n(?:      [^\n]*\n?)+', tail).group(0).splitlines())
    if expression.startswith('${{') and expression.endswith('}}'):
        expression = expression[3:-2].strip()
    return expression


def condition_matches(expression, context):
    """Evaluate the actual job guard with a narrow grammar, never eval code."""
    token = re.compile(r"github\.(?:repository|ref|event_name)|'(?:[^']|'')*'|==|&&|\|\||[()]")
    tokens = []
    end = 0
    for match in token.finditer(expression):
        if expression[end:match.start()].strip():
            raise ValueError('Unsupported trust-condition syntax')
        tokens.append(match.group(0))
        end = match.end()
    if expression[end:].strip():
        raise ValueError('Unsupported trust-condition syntax')
    position = [0]

    def take(expected=None):
        if position[0] >= len(tokens):
            raise ValueError('Incomplete trust condition')
        value = tokens[position[0]]
        if expected is not None and value != expected:
            raise ValueError('Unexpected trust-condition token')
        position[0] += 1
        return value

    def atom():
        if position[0] < len(tokens) and tokens[position[0]] == '(':
            take('(')
            value = either()
            take(')')
            return value
        field = take()
        if field not in ('github.repository', 'github.ref', 'github.event_name'):
            raise ValueError('Only immutable event context may select installer publication')
        take('==')
        value = take()
        if not (value.startswith("'") and value.endswith("'")):
            raise ValueError('Expected a literal trust boundary')
        return context[field] == value[1:-1].replace("''", "'")

    def both():
        value = atom()
        while position[0] < len(tokens) and tokens[position[0]] == '&&':
            take('&&')
            right = atom()
            value = value and right
        return value

    def either():
        value = both()
        while position[0] < len(tokens) and tokens[position[0]] == '||':
            take('||')
            right = both()
            value = value or right
        return value

    value = either()
    if position[0] != len(tokens):
        raise ValueError('Unexpected trailing trust-condition tokens')
    return value


class HangarPipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workflow = WORKFLOW.read_text(encoding='utf-8')
        cls.build = BUILD.read_text(encoding='utf-8')
        cls.validate = VALIDATE.read_text(encoding='utf-8')
        cls.paths = filters(cls.workflow)
        cls.build_paths = filters(cls.build, 'push')

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
                     '.github/workflows/hangarsync-ci.yml', '.github/workflows/hangarsync-build.yml',
                     'scripts/sessionstats/python27.sh',
                     'scripts/privacy_audit.py', 'scripts/wot_updates.py'):
            with self.subTest(path=path):
                self.assertTrue(matches(path, self.paths))
                self.assertTrue(matches(path, self.build_paths))

    def test_other_mods_and_unrelated_docs_do_not_trigger_hangar(self):
        for path in ('source/mod_staysharp_medkit.py', 'assets/voices/pl.wav.b85', 'VERSION',
                     'mods/sessionstats/src/grz_session_stats/runtime.py',
                     'mods/sessionstats/ui/session_stats.js', 'scripts/sessionstats/validate.sh',
                     '.github/workflows/sessionstats-ci.yml', '.github/workflows/ci.yml',
                     'README.md', 'docs/MULTIMOD_RELEASES.md'):
            with self.subTest(path=path):
                self.assertFalse(matches(path, self.paths))
                self.assertFalse(matches(path, self.build_paths))

    def test_existing_mod_filters_do_not_pick_hangar_sources(self):
        for workflow in ('ci.yml', 'sessionstats-ci.yml'):
            patterns = filters((ROOT / '.github/workflows' / workflow).read_text())
            for path in ('mods/hangarsync/source/mod_grz_hangar_sync.py',
                         'scripts/hangarsync/validate.sh', 'tests/test_hangarsync_pipeline.py',
                         '.github/workflows/hangarsync-ci.yml', '.github/workflows/hangarsync-build.yml'):
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
        self.assertEqual(references, ['actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1'])
        self.assertIn('strict: false', self.workflow)

    def test_pr_workflow_never_uploads_or_promotes_executable_artifacts(self):
        self.assertNotRegex(self.workflow, r'actions/(?:upload|download)-artifact@')
        self.assertNotIn('gh release', self.workflow)
        self.assertNotIn('workflow_run', self.workflow)
        self.assertIn('bash scripts/hangarsync/validate.sh', self.workflow)
        self.assertIn('candidate', self.workflow.lower())

    def test_installer_build_only_triggers_on_main_or_explicit_dispatch(self):
        trigger = self.build.split('\npermissions:', 1)[0]
        self.assertIn('name: Build Hangar Sync installer', trigger)
        self.assertRegex(trigger, r'push:\n    branches: \[main\]')
        self.assertIn('  workflow_dispatch:', trigger)
        for forbidden in ('pull_request', 'workflow_run', 'inputs:', 'tags:'):
            self.assertNotIn(forbidden, trigger)
        self.assertEqual(set(self.paths), set(self.build_paths))

    def test_installer_jobs_reject_untrusted_event_ref_and_repository_contexts(self):
        blocks = jobs(self.build)
        self.assertEqual(set(blocks), {'updates', 'hangarsync'})
        official = 'Szwarceneger16/WotMods'
        cases = [
            ('pull_request', 'refs/pull/19/merge', official, False),
            ('pull_request', 'refs/heads/main', official, False),
            ('pull_request_target', 'refs/heads/main', official, False),
            ('workflow_run', 'refs/heads/main', official, False),
            ('push', 'refs/heads/feature/candidate', official, False),
            ('push', 'refs/tags/main', official, False),
            ('workflow_dispatch', 'refs/heads/feature/candidate', official, False),
            ('workflow_dispatch', 'refs/tags/main', official, False),
            ('push', 'refs/heads/main', 'contributor/WotMods', False),
            ('workflow_dispatch', 'refs/heads/main', 'contributor/WotMods', False),
            ('push', 'refs/heads/main', official, True),
            ('workflow_dispatch', 'refs/heads/main', official, True),
        ]
        for name, block in blocks.items():
            expression = job_condition(block)
            for event, ref, repository, expected in cases:
                with self.subTest(job=name, event=event, ref=ref, repository=repository):
                    self.assertEqual(condition_matches(expression, {
                        'github.event_name': event, 'github.ref': ref,
                        'github.repository': repository,
                    }), expected)

    def test_trusted_build_rebuilds_exact_sha_with_read_only_permissions(self):
        self.assertIn('permissions:\n  contents: read', self.build)
        self.assertIn('ref: ${{ github.sha }}', self.build)
        self.assertIn('persist-credentials: false', self.build)
        self.assertIn('bash scripts/sessionstats/python27.sh', self.build)
        self.assertIn('bash scripts/hangarsync/validate.sh', self.build)
        self.assertIn("python3 -m unittest discover -s tests -p 'test_hangarsync_*.py' -v", self.build)
        references = re.findall(r'uses: (actions/[^\s]+)', self.build)
        self.assertEqual(references, [
            'actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1',
            'actions/upload-artifact@cf430e030ddbb5b0abf93d22962f4752f3646cd9',
        ])
        for forbidden in ('contents: write', 'secrets.', 'environment:', 'download-artifact',
                          'pull_request_target', 'workflow_run', 'gh release'):
            self.assertNotIn(forbidden, self.build)
        self.assertNotEqual(re.search(r'group: (.+)', self.workflow).group(1),
                            re.search(r'group: (.+)', self.build).group(1))

    def test_trusted_installer_is_uploaded_only_after_validation_as_existing_zip(self):
        upload = self.build.split('uses: actions/upload-artifact@', 1)[1]
        self.assertLess(self.build.index('bash scripts/hangarsync/validate.sh'),
                        self.build.index('uses: actions/upload-artifact@'))
        self.assertIn('path: mods/hangarsync/dist/GRZ_Hangar_Sync-v*.zip', upload)
        self.assertIn('archive: false', upload)
        self.assertIn('if-no-files-found: error', upload)
        self.assertIn('retention-days: 14', upload)
        self.assertNotIn('path: mods/hangarsync/dist/*', upload)

    def test_installation_docs_point_to_trusted_builds_not_pr_checks(self):
        readme = (ROOT / 'README.md').read_text(encoding='utf-8')
        self.assertNotIn('PR build artifact:', readme)
        self.assertNotIn('successful **Validate Hangar Sync PR** run', readme)
        self.assertIn('Build Hangar Sync installer', readme)

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
