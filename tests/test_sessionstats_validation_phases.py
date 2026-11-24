"""Exercise the shared validation entry point without a browser or network."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts/sessionstats/validate.sh'
TRANSACTION = ['python3', 'python27', 'preview', 'browser', 'build1',
               'snapshot', 'build2', 'verify', 'integration', 'privacy']
PHASES = {
    'python3': ['python3'], 'python27': ['python27'],
    'preview': ['preview'], 'browser': ['browser'],
    'build': ['build1', 'snapshot', 'build2', 'verify'],
    'integration': ['integration'], 'privacy': ['privacy'],
}

# This executable records actual argv boundaries rather than parsing shell text.
FAKE_PYTHON = r'''
import json, os
from pathlib import Path
import sys

log = Path(os.environ['VALIDATION_TEST_LOG'])
previous = [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []
arguments = sys.argv[1:]
if Path(sys.argv[0]).name == 'python27':
    stage = 'python27'
elif arguments[:2] == ['-m', 'unittest']:
    stage = 'python3'
elif arguments[:2] == ['-I', 'scripts/sessionstats/browser_qa.py']:
    stage = 'browser'
elif arguments[0] == 'mods/sessionstats/tools/make_preview.py':
    stage = 'preview'
elif arguments[0] == 'mods/sessionstats/tools/build.py':
    stage = 'build' + str(1 + sum(item['stage'].startswith('build') for item in previous))
elif arguments[0] == 'scripts/sessionstats/artifacts.py':
    stage = arguments[1]
elif arguments[0] == 'scripts/sessionstats/integration.py':
    stage = 'integration'
elif arguments[0] == 'scripts/sessionstats/privacy.py':
    stage = 'privacy'
else:
    raise SystemExit('Unexpected validation command: ' + repr(arguments))
entry = {'stage': stage, 'arguments': arguments,
         'session_version': os.environ.get('SESSIONSTATS_VERSION'),
         'python27': os.environ.get('PYTHON27')}
with log.open('a') as stream:
    stream.write(json.dumps(entry) + '\n')
if os.environ.get('VALIDATION_TEST_FAIL') == stage:
    raise SystemExit(7)
if stage == 'snapshot':
    Path(arguments[2]).write_text('synthetic six-asset snapshot\n')
elif stage == 'verify':
    if Path(arguments[2]).read_text() != 'synthetic six-asset snapshot\n':
        raise SystemExit('Reproducibility must verify the same snapshot')
'''


@unittest.skipUnless(shutil.which('bash'), 'Bash is required by the release entry point')
class ValidationPhaseTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='synthetic-validation-')
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        self.binary_directory = self.directory / 'executables with spaces'
        self.binary_directory.mkdir()
        for name in ('python3', 'python27'):
            executable = self.binary_directory / name
            executable.write_text('#!' + sys.executable + '\n' + FAKE_PYTHON)
            executable.chmod(0o755)
        self.manifests = self.directory / 'manifest files'
        self.manifests.mkdir()
        self.unrelated = self.manifests / 'unrelated.txt'
        self.unrelated.write_text('preserve this file')
        self.log = self.directory / 'commands.jsonl'
        self.environment = dict(os.environ, PATH=str(self.binary_directory) + os.pathsep + os.defpath,
                                PYTHON27=str(self.binary_directory / 'python27'),
                                RUNNER_TEMP=str(self.manifests),
                                VALIDATION_TEST_LOG=str(self.log),
                                SESSIONSTATS_VERSION='0.3.9')
        self.environment.pop('VALIDATION_TEST_FAIL', None)
        self.environment.pop('WOT_CLIENT_VERSION', None)

    def invoke(self, *arguments, fail=None, missing_runtime=False, temporary=None):
        self.log.unlink(missing_ok=True)
        environment = dict(self.environment)
        if fail is not None:
            environment['VALIDATION_TEST_FAIL'] = fail
        if missing_runtime:
            environment.pop('PYTHON27')
        if temporary is not None:
            environment['RUNNER_TEMP'] = str(temporary)
        result = subprocess.run([shutil.which('bash'), str(SCRIPT), *arguments],
                                cwd=self.directory, env=environment,
                                capture_output=True, text=True)
        entries = [json.loads(line) for line in self.log.read_text().splitlines()] if self.log.exists() else []
        return result, entries

    def assert_manifest_cleanup(self):
        self.assertEqual(list(self.manifests.glob('sessionstats-reproducibility.*')), [])
        self.assertEqual(self.unrelated.read_text(), 'preserve this file')

    def test_default_and_explicit_all_run_the_complete_release_transaction_once(self):
        for arguments in ((), ('all',)):
            with self.subTest(arguments=arguments):
                result, entries = self.invoke(*arguments)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual([entry['stage'] for entry in entries], TRANSACTION)
                self.assertTrue(all(entry['session_version'] == '0.3.9' for entry in entries))
                self.assert_manifest_cleanup()

    def test_named_phases_run_only_their_full_command_group(self):
        for phase, expected in PHASES.items():
            with self.subTest(phase=phase):
                result, entries = self.invoke(phase)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual([entry['stage'] for entry in entries], expected)
                self.assert_manifest_cleanup()

    def test_each_failure_blocks_every_later_release_stage(self):
        for index, stage in enumerate(TRANSACTION):
            with self.subTest(stage=stage):
                result, entries = self.invoke(fail=stage)
                self.assertEqual(result.returncode, 7, result.stderr)
                self.assertEqual([entry['stage'] for entry in entries], TRANSACTION[:index + 1])
                self.assert_manifest_cleanup()

    def test_named_phase_failures_are_not_swallowed(self):
        for phase, stages in PHASES.items():
            for index, stage in enumerate(stages):
                with self.subTest(phase=phase, stage=stage):
                    result, entries = self.invoke(phase, fail=stage)
                    self.assertEqual(result.returncode, 7, result.stderr)
                    self.assertEqual([entry['stage'] for entry in entries], stages[:index + 1])
                    self.assert_manifest_cleanup()

    def test_both_builds_keep_the_runtime_and_requested_client_arguments(self):
        self.environment['WOT_CLIENT_VERSION'] = '2.4.1.1'
        result, entries = self.invoke('build')
        self.assertEqual(result.returncode, 0, result.stderr)
        expected = ['mods/sessionstats/tools/build.py', '--python27', self.environment['PYTHON27'],
                    '--client-version', '2.4.1.1']
        self.assertEqual([entry['arguments'] for entry in entries if entry['stage'].startswith('build')],
                         [expected, expected])
        snapshot, verify = [entry['arguments'] for entry in entries if entry['stage'] in ('snapshot', 'verify')]
        self.assertEqual(snapshot[2], verify[2])
        self.assert_manifest_cleanup()

    def test_full_runtime_and_audit_commands_keep_their_guards(self):
        result, entries = self.invoke()
        self.assertEqual(result.returncode, 0, result.stderr)
        commands = {entry['stage']: entry['arguments'] for entry in entries}
        self.assertEqual(commands['python3'], ['-m', 'unittest', 'discover', '-s', 'mods/sessionstats/tests', '-v'])
        self.assertEqual(commands['python27'], ['-B', '-m', 'unittest', 'discover', '-s', 'mods/sessionstats/tests', '-v'])
        self.assertEqual(commands['browser'], ['-I', 'scripts/sessionstats/browser_qa.py', '--e2e', 'build'])
        self.assertEqual(commands['privacy'], ['scripts/sessionstats/privacy.py', '--python27',
                                              self.environment['PYTHON27'], '--scan-dist'])
        self.assertEqual(commands['integration'], ['scripts/sessionstats/integration.py'])

    def test_runtime_is_required_for_all_runtime_dependent_phases(self):
        for arguments in ((), ('all',), ('python27',), ('build',), ('integration',), ('privacy',)):
            with self.subTest(arguments=arguments):
                result, entries = self.invoke(*arguments, missing_runtime=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('Set PYTHON27', result.stderr)
                self.assertEqual(entries, [])
        for phase in ('python3', 'preview', 'browser'):
            with self.subTest(phase=phase):
                result, entries = self.invoke(phase, missing_runtime=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual([entry['stage'] for entry in entries], PHASES[phase])

    def test_invalid_phase_or_extra_arguments_fail_before_any_commands(self):
        for arguments in (('unknown',), ('python3', 'python27'), ('all', 'extra')):
            with self.subTest(arguments=arguments):
                result, entries = self.invoke(*arguments)
                self.assertEqual(result.returncode, 2)
                self.assertIn('Usage: validate.sh', result.stderr)
                self.assertEqual(entries, [])

    def test_failure_to_allocate_a_manifest_blocks_both_builds(self):
        invalid_parent = self.directory / 'not a directory'
        invalid_parent.write_text('keep')
        result, entries = self.invoke('build', temporary=invalid_parent)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(entries, [])
        self.assertEqual(invalid_parent.read_text(), 'keep')
        self.assert_manifest_cleanup()


if __name__ == '__main__':
    unittest.main()
