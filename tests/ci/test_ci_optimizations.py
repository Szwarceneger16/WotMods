"""Keep CI optimizations fail-closed and inside their existing trust boundary."""
from pathlib import Path
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tests'))
from test_unified_release_workflow import condition_matches


STATS = (ROOT / '.github/workflows/sessionstats-ci.yml').read_text()
MEDKIT = (ROOT / '.github/workflows/ci.yml').read_text()
AIMTIMER = (ROOT / '.github/workflows/aimtimer-ci.yml').read_text()
RANGEFINDER = (ROOT / '.github/workflows/rangefinder-ci.yml').read_text()
RELEASE = (ROOT / '.github/workflows/wotmods-release.yml').read_text()
COMPILER = (ROOT / '.github/actions/python27/action.yml').read_text()
VALIDATE = (ROOT / 'scripts/sessionstats/validate.sh').read_text()
CACHE_PIN = 'caa296126883cff596d87d8935842f9db880ef25'
PACKAGE_PHASES = ['preview', 'build', 'integration', 'privacy']


def job(text, name):
    match = re.search(r'(?ms)^  ' + re.escape(name) +
                      r':\n(.*?)(?=^  [a-z0-9_-]+:\n|\Z)', text)
    if not match:
        raise AssertionError('Missing job ' + name)
    return match.group(1)


class CiOptimizationContracts(unittest.TestCase):
    def test_only_new_commits_on_the_same_pr_supersede_validation(self):
        group = ('${{ github.workflow }}-${{ github.event_name }}-'
                 '${{ github.event.pull_request.number || github.run_id }}')
        for text in (STATS, MEDKIT, AIMTIMER, RANGEFINDER):
            with self.subTest(workflow=text.splitlines()[0]):
                concurrency = text.split('\nconcurrency:\n', 1)[1].split('\njobs:', 1)[0]
                self.assertIn('  group: ' + group, concurrency)
                expression = re.search(r'^  cancel-in-progress: \$\{\{ (.+) \}\}$',
                                       concurrency, re.MULTILINE).group(1)
                for event in ('pull_request', 'workflow_dispatch', 'push',
                              'pull_request_target', 'workflow_run'):
                    self.assertEqual(condition_matches(expression, {
                        'github.event_name': event,
                        'github.ref': 'refs/heads/main',
                        'github.repository': 'Szwarceneger16/WotMods',
                    }), event == 'pull_request')
                self.assertIn('contents: read', text)
                self.assertNotIn('contents: write', text)

    def test_release_serialization_and_accepted_main_gate_remain_intact(self):
        queue = RELEASE.split('\nconcurrency:\n', 1)[1].split('\njobs:', 1)[0]
        self.assertIn('group: wotmod-release-${{ github.repository }}', queue)
        self.assertIn('queue: max', queue)
        self.assertIn('cancel-in-progress: false', queue)
        self.assertNotIn('pull_request:', RELEASE)
        self.assertIn('needs: updates', job(RELEASE, 'plan'))
        self.assertIn('needs: [plan, updates]', job(RELEASE, 'build'))
        self.assertIn('needs: [plan, updates, build]', job(RELEASE, 'publish'))

    def test_windows_runs_both_native_python_suites_and_browser_once(self):
        windows = job(STATS, 'sessionstats_windows')
        self.assertIn('runs-on: windows-2025', windows)
        self.assertIn('shell: pwsh', windows)
        self.assertIn('needs: source', windows)
        self.assertIn("if: needs.source.outputs.enabled == 'true'", windows)
        self.assertIn('GIT_CONFIG_KEY_0: core.autocrlf', windows)
        self.assertIn("GIT_CONFIG_VALUE_0: 'false'", windows)
        parallel = windows.split('      - parallel:\n', 1)[1]
        for command in ('python -B -m unittest discover -s mods/sessionstats/tests -v',
                        '& $env:PYTHON27 -E -s -B -m unittest discover -s mods/sessionstats/tests -v',
                        'python -I scripts/sessionstats/browser_qa.py --e2e build'):
            self.assertEqual(parallel.count(command), 1)
            self.assertEqual(STATS.count(command), 1)
        self.assertEqual(len(re.findall(r'^          - name: (.+)$', parallel, re.MULTILINE)), 3)
        self.assertNotIn('continue-on-error', parallel)
        self.assertNotIn('bash ', windows)
        self.assertLess(windows.index('uses: ./.github/actions/python27-windows'), windows.index('      - parallel:'))
        self.assertNotIn('parallel:', COMPILER)

    def test_packaging_requires_windows_success_except_before_source_import(self):
        source = job(STATS, 'source')
        self.assertIn('fetch-depth: 0', source)
        self.assertIn('enabled: ${{ steps.source.outputs.enabled }}', source)
        self.assertIn('run: python3 scripts/sessionstats/source_state.py', source)
        packaging = job(STATS, 'sessionstats')
        self.assertIn('needs: [updates, source, sessionstats_windows]', packaging)
        self.assertIn('if: ${{ !cancelled() }}', packaging)
        gate = packaging.split('      - name: Require the Session Stats checks before packaging\n', 1)[1]
        gate = gate.split('      - uses: actions/checkout@', 1)[0]
        for variable, dependency in (('UPDATES_RESULT', 'updates.result'), ('SOURCE_RESULT', 'source.result'),
                                     ('SOURCE_ENABLED', 'source.outputs.enabled'), ('WINDOWS_RESULT', 'sessionstats_windows.result')):
            self.assertIn(variable + ': ${{ needs.' + dependency + ' }}', gate)
        self.assertIn('if [[ "$UPDATES_RESULT" != success || "$SOURCE_RESULT" != success ]]; then', gate)
        self.assertIn('case "$SOURCE_ENABLED:$WINDOWS_RESULT" in\n            true:success|false:skipped) ;;', gate)
        self.assertEqual(gate.count('exit 1'), 2)
        self.assertNotIn('continue-on-error', gate)
        infrastructure = packaging.split('      - name: Test release infrastructure\n', 1)[1].split('\n      - name:', 1)[0]
        self.assertNotIn('if:', infrastructure)

    def test_all_named_phases_gate_packaging_without_repeating_browser_setup(self):
        commands = re.findall(r'run: bash scripts/sessionstats/validate\.sh (\w+)', STATS)
        self.assertEqual(commands, PACKAGE_PHASES)
        self.assertNotIn('--prepare', STATS)
        self.assertEqual(VALIDATE.count('python3 -I scripts/sessionstats/browser_qa.py'), 1)
        packaging = job(STATS, 'sessionstats')
        self.assertNotIn('continue-on-error', packaging)
        self.assertNotIn('always()', packaging)
        for phase in PACKAGE_PHASES:
            command = 'run: bash scripts/sessionstats/validate.sh ' + phase
            position = packaging.index(command)
            step = packaging[packaging.rfind('- name:', 0, position):position]
            self.assertIn("if: needs.source.outputs.enabled == 'true'", step)
        self.assertLess(packaging.index('uses: ./.github/actions/python27\n'),
                        packaging.index('validate.sh build'))
        self.assertLess(packaging.index('validate.sh privacy'),
                        packaging.index('scripts/release_installers.py package pr-artifact-sessionstats'))
        self.assertLess(packaging.index('scripts/release_installers.py package pr-artifact-sessionstats'),
                        packaging.index('uses: actions/upload-artifact@'))

    def test_exact_cache_identity_covers_platform_and_bootstrap_recipe(self):
        self.assertIn('actions/cache/restore@' + CACHE_PIN, COMPILER)
        self.assertIn('actions/cache/save@' + CACHE_PIN, COMPILER)
        self.assertNotIn('restore-keys:', COMPILER)
        self.assertNotIn('enableCrossOsArchive:', COMPILER)
        key = re.search(r'^        key: (cpython27-.+)$', COMPILER, re.MULTILINE).group(1)
        for field in ('ubuntu-24.04', '${{ runner.os }}', '${{ runner.arch }}',
                      "${{ hashFiles('scripts/sessionstats/python27.sh') }}"):
            self.assertIn(field, key)
        self.assertEqual(COMPILER.count(
            'path: ${{ runner.temp }}/sessionstats-cpython27/Python-2.7.18'), 2)
        self.assertIn('key: ${{ steps.restore.outputs.cache-primary-key }}', COMPILER)
        # A changed checksum, version or compiler flag changes this exact recipe hash.
        bootstrap = (ROOT / 'scripts/sessionstats/python27.sh').read_text()
        self.assertIn('Python-2.7.18.tgz', bootstrap)
        self.assertIn('da3080e3b488f648a3d7a4560ddee895284c3380b11d6de75edb986526b9a814', bootstrap)
        self.assertIn('--without-ensurepip', bootstrap)

    def test_a_cache_hit_never_skips_runtime_validation(self):
        validation = COMPILER.split('    - name: Build on a miss', 1)[1].split('    - name: Save', 1)[0]
        self.assertIn('run: bash scripts/sessionstats/python27.sh', validation)
        self.assertNotIn('if:', validation)
        self.assertNotIn('continue-on-error', COMPILER)
        self.assertIn('cache-mode: read', job(STATS, 'sessionstats'))

    def test_only_accepted_main_events_can_save_the_compiler_cache(self):
        save = COMPILER.split('    - name: Save validated build', 1)[1]
        condition = re.search(r'^      if: (.+)$', save, re.MULTILINE).group(1)
        prefix = "steps.restore.outputs.cache-hit != 'true' && "
        self.assertTrue(condition.startswith(prefix))
        trust = condition[len(prefix):]
        for event in ('push', 'workflow_dispatch', 'pull_request',
                      'pull_request_target', 'workflow_run'):
            for ref in ('refs/heads/main', 'refs/heads/feature', 'refs/pull/29/merge', 'refs/tags/main'):
                with self.subTest(event=event, ref=ref):
                    self.assertEqual(condition_matches(trust, {
                        'github.event_name': event, 'github.ref': ref,
                        'github.repository': 'Szwarceneger16/WotMods',
                    }), event in ('push', 'workflow_dispatch') and ref == 'refs/heads/main')

    def test_release_reuses_the_compiler_only_for_sessionstats(self):
        build = job(RELEASE, 'build')
        self.assertIn('cache-mode: write', build)
        position = build.index('uses: ./.github/actions/python27')
        compiler = build[build.rfind('- name:', 0, position):position]
        self.assertIn("if: matrix.mod == 'sessionstats'", compiler)
        self.assertLess(position, build.index('run: bash scripts/build_release_module.sh'))
        self.assertIn('runs-on: ubuntu-24.04', build)
        self.assertIn('runs-on: ubuntu-24.04', job(STATS, 'sessionstats'))

    def test_compiler_action_changes_trigger_sessionstats_validation(self):
        self.assertIn("      - '.github/actions/python27/**'", STATS)
        self.assertIn("      - '.github/actions/python27-windows/**'", STATS)


if __name__ == '__main__':
    unittest.main()
