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
        cls.build = (ROOT / '.github/workflows/wotmods-release.yml').read_text(encoding='utf-8')
        cls.validate = VALIDATE.read_text(encoding='utf-8')
        cls.paths = filters(cls.workflow)

    def test_feature_and_main_targets_receive_candidate_validation(self):
        branch_line = self.workflow.split('  pull_request:\n', 1)[1].split('    paths:', 1)[0]
        branches = re.search(r'branches: \[([^\]]+)\]', branch_line).group(1)
        self.assertEqual({value.strip() for value in branches.split(',')},
                         {'main', 'feature/sessionstats-battle-details-timeline',
                          'feature/sessionstats-hangar-api'})
        self.assertIn('  workflow_dispatch:', self.workflow)
        self.assertNotIn('pull_request_target', self.workflow)
        self.assertNotIn('\n  push:', self.workflow)

    def test_hangar_sources_and_shared_release_inputs_trigger_validation(self):
        for path in ('mods/hangarsync/source/hangar_crew.py', 'mods/hangarsync/VERSION',
                     'mods/hangarsync/GRZ_Hangar_Sync.json.example',
                     'scripts/hangarsync/privacy.py', 'scripts/hangarsync/bootstrap_smoke.py',
                     'tests/test_hangarsync_pipeline.py', 'tests/test_hangarsync_privacy.py',
                     'tests/test_hangar_release_installers.py',
                     '.github/workflows/hangarsync-ci.yml', '.github/workflows/wotmods-release.yml',
                     'scripts/sessionstats/python27.sh', 'scripts/privacy_audit.py',
                     'scripts/release_installers.py', 'scripts/release_coordinator.py',
                     'scripts/release_modules.json', 'scripts/build_release_module.sh',
                     'tests/test_release_coordinator.py', 'tests/test_unified_release_workflow.py'):
            with self.subTest(path=path):
                self.assertTrue(matches(path, self.paths))

    def test_other_mod_sources_and_unused_news_preflight_do_not_start_hangar(self):
        for path in ('source/mod_staysharp_medkit.py', 'assets/voices/pl.wav.b85', 'VERSION',
                     'mods/sessionstats/src/grz_session_stats/runtime.py',
                     'mods/sessionstats/ui/session_stats.js', 'scripts/sessionstats/validate.sh',
                     '.github/workflows/sessionstats-ci.yml', '.github/workflows/ci.yml',
                     '.github/workflows/wot-updates.yml', 'scripts/wot_updates.py',
                     'scripts/wot_dispatch.py', 'tests/test_wot_updates.py',
                     'README.md', 'docs/MULTIMOD_RELEASES.md'):
            with self.subTest(path=path):
                self.assertFalse(matches(path, self.paths))
        self.assertEqual(set(jobs(self.workflow)), {'hangarsync'})
        self.assertNotIn('uses: ./.github/workflows/wot-updates.yml', self.workflow)

    def test_existing_mod_filters_do_not_cross_build_hangar_source_changes(self):
        for workflow in ('ci.yml', 'sessionstats-ci.yml'):
            patterns = filters((ROOT / '.github/workflows' / workflow).read_text())
            for path in ('mods/hangarsync/source/mod_grz_hangar_sync.py',
                         'scripts/hangarsync/validate.sh', 'tests/test_hangarsync_pipeline.py',
                         '.github/workflows/hangarsync-ci.yml'):
                with self.subTest(workflow=workflow, path=path):
                    self.assertFalse(matches(path, patterns))

    def test_candidate_build_keeps_readonly_permissions_and_no_installer_upload(self):
        self.assertIn('permissions:\n  contents: read', self.workflow)
        self.assertIn('persist-credentials: false', self.workflow)
        self.assertIn('ref: ${{ github.sha }}', self.workflow)
        for forbidden in ('contents: write', 'secrets.', 'environment:', 'gh release',
                          'workflow_run', 'actions/upload-artifact@', 'actions/download-artifact@'):
            self.assertNotIn(forbidden, self.workflow)
        self.assertIn('bash scripts/hangarsync/validate.sh', self.workflow)
        self.assertIn('GITHUB_STEP_SUMMARY', self.workflow)
        self.assertIn('Trusted release downloads', self.workflow)

    def test_verified_compiler_and_pinned_checkout_are_reused(self):
        self.assertIn('bash scripts/sessionstats/python27.sh', self.workflow)
        references = re.findall(r'uses: (actions/[^\s]+)', self.workflow)
        self.assertEqual(references, ['actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1'])

    def test_standalone_hangar_publisher_is_retired(self):
        self.assertFalse(BUILD.exists())
        self.assertIn('name: Publish WotMods snapshot', self.build)
        self.assertIn('  push:\n    branches: [main]', self.build)
        self.assertNotIn('  pull_request:', self.build)
        publishers = [path.name for path in (ROOT / '.github/workflows').glob('*.yml')
                      if re.search(r'^\s+gh release create ', path.read_text(), re.MULTILINE)]
        self.assertEqual(publishers, ['wotmods-release.yml'])

    def test_unified_installer_gate_rejects_untrusted_contexts_before_all_jobs(self):
        blocks = jobs(self.build)
        expression = job_condition(blocks['updates'])
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
        for event, ref, repository, expected in cases:
            with self.subTest(event=event, ref=ref, repository=repository):
                self.assertEqual(condition_matches(expression, {
                    'github.event_name': event, 'github.ref': ref,
                    'github.repository': repository}), expected)
        self.assertIn('needs: updates', blocks['plan'])
        self.assertIn('needs: [plan, updates]', blocks['build'])
        self.assertIn('needs: [plan, updates, build]', blocks['publish'])
        for name in ('plan', 'build', 'publish'):
            self.assertNotIn('always()', blocks[name])
            self.assertNotIn('!cancelled()', blocks[name])

    def test_registered_hangar_build_uses_common_planner_and_native_zip(self):
        import json
        registry = json.loads((ROOT / 'scripts/release_modules.json').read_text())
        entry = next(item for item in registry['modules'] if item['id'] == 'hangarsync')
        self.assertEqual(entry['installer_prefix'], 'GRZ_Hangar_Sync-v')
        self.assertEqual(entry['base_version_file'], 'mods/hangarsync/VERSION')
        self.assertEqual(entry['source_paths'], [
            'mods/hangarsync/**', 'scripts/hangarsync/**', 'scripts/sessionstats/python27.sh'])
        builder = (ROOT / 'scripts/build_release_module.sh').read_text()
        hangar = builder.split('  hangarsync)', 1)[1].split('  *)', 1)[0]
        self.assertIn('bash scripts/hangarsync/validate.sh', hangar)
        self.assertIn("'--version', version, '--client-version', client", hangar)
        self.assertIn('audit.scan_bytes', hangar)
        self.assertNotIn('scripts/sessionstats/validate.sh', hangar)
        self.assertNotIn('source/build_wotmod.py', hangar)
        self.assertIn('fromJSON(needs.plan.outputs.matrix)', self.build)
        self.assertIn('pattern: wotmods-installer-*', self.build)

    def test_production_downloads_follow_verified_remote_bytes(self):
        self.assertIn('ref: ${{ github.sha }}', self.build)
        self.assertIn('ref: ${{ needs.plan.outputs.source_sha }}', self.build)
        self.assertIn('environment: wotmods-release', self.build)
        self.assertIn('queue: max', self.build)
        self.assertIn('cancel-in-progress: false', self.build)
        self.assertLess(self.build.index('python3 scripts/release_installers.py verify "$remote"'),
                        self.build.index('cat release-notes.md >> "$GITHUB_STEP_SUMMARY"'))

    def test_installation_docs_point_to_shared_trusted_releases(self):
        readme = (ROOT / 'README.md').read_text(encoding='utf-8')
        self.assertIn('GRZ_Hangar_Sync-v<version>.zip', readme)
        self.assertIn('../../releases/latest', readme)
        self.assertNotIn('Build Hangar Sync installer', readme)
        self.assertNotIn('PR build artifact:', readme)

    def test_validator_keeps_native_python27_and_recursive_privacy_audits(self):
        self.assertIn('discover -s mods/hangarsync/tests -v', self.validate)
        self.assertIn('test_personal_operations', self.validate)
        self.assertIn('"$PYTHON27" -B scripts/hangarsync/bootstrap_smoke.py', self.validate)
        self.assertIn('privacy.py --python27 "$PYTHON27" --scan-dist', self.validate)
        self.assertEqual(self.validate.count('python3 mods/hangarsync/tools/build.py'), 2)
        self.assertIn('if actual != expected:', self.validate)
        self.assertNotIn('mods/sessionstats/tools/build.py', self.validate)
        self.assertNotIn('source/build_wotmod.py', self.validate)

    def test_shell_blocks_parse(self):
        subprocess.check_call(['bash', '-n', str(VALIDATE)])
        for body in re.findall(r'(?m)^        run: \|\n((?:          .*\n|\n)+)', self.workflow):
            code = '\n'.join(line[10:] if line.startswith('          ') else ''
                             for line in body.splitlines()) + '\n'
            subprocess.run(['bash', '-n'], input=code, text=True, check=True)


if __name__ == '__main__':
    unittest.main()
