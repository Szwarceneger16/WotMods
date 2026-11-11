"""Exercise the isolated browser bootstrap without Docker or network access."""
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    'sessionstats_browser_container', ROOT/'scripts/sessionstats/browser_qa.py')
qa = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = qa
SPEC.loader.exec_module(qa)

EXPECTED_IMAGE = ('mcr.microsoft.com/playwright:v1.62.1-noble@sha256:'
                  'dcc5531e97840b9b5e794f2814476b21571c5124a3fca2267d73041f56e7580e')
EXPECTED_SUITES = ('ui_contract', 'ui-wheel', 'ui-footer', 'ui-footer-activity',
                   'ui-footer-compat', 'ui-appearance')


def docker_mounts(command):
    mounts = []
    for index, argument in enumerate(command):
        if argument == '--mount':
            fields = dict(part.split('=', 1) if '=' in part else (part, True)
                          for part in command[index + 1].split(','))
            mounts.append((fields.get('source', fields.get('src')),
                           fields.get('target', fields.get('dst', fields.get('destination'))),
                           'readonly' in fields or fields.get('ro') is True))
        elif argument in ('--volume', '-v'):
            fields = command[index + 1].split(':')
            mounts.append((fields[0], fields[1], len(fields) > 2 and 'ro' in fields[2].split(',')))
    return mounts


class BrowserContainerTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory(prefix='synthetic-browser-')
        self.addCleanup(directory.cleanup)
        self.directory = Path(directory.name)
        self.workspace = self.directory/'source with spaces'
        self.workspace.mkdir()
        self.temporary = self.directory/'tools'
        self.temporary.mkdir()
        binary = self.directory/'python3'
        binary.write_bytes(b'synthetic executable')
        library = self.directory/'libpython3.so'
        library.write_bytes(b'synthetic shared library')
        standard = self.directory/'python-stdlib'
        standard.mkdir()
        self.runtime = {
            'mounts': [(binary, '/host-python/bin/python3'),
                       (standard, '/host-python/lib/python3'),
                       (library, '/host-python/lib/libpython3.so')],
            'environment': {'PYTHONHOME': '/host-python',
                            'LD_LIBRARY_PATH': '/host-python/lib'},
            'version': '3.12.0 synthetic',
        }
        self.certificate = self.directory/'public-ca.crt'
        self.certificate.write_text('Synthetic public CA bundle')
        certificate = patch.object(qa, 'HOST_CA', self.certificate)
        certificate.start()
        self.addCleanup(certificate.stop)

    def test_exact_browser_and_package_versions_remain_paired(self):
        self.assertEqual(qa.IMAGE, EXPECTED_IMAGE)
        self.assertEqual(qa.PLAYWRIGHT_VERSION, '1.62.1')
        self.assertEqual(tuple(qa.UI_TESTS), EXPECTED_SUITES)
        self.assertEqual(len(set(qa.UI_TESTS)), 6)

    def test_only_workspace_and_temporary_tools_are_writable_mounts(self):
        payload = ['node', '-e', 'synthetic command with spaces']
        command = qa.docker_command(payload, runtime=self.runtime,
                                    workspace=self.workspace, temporary=self.temporary,
                                    name='synthetic-ui-container')
        self.assertEqual(command[-len(payload):], payload)
        self.assertIn(EXPECTED_IMAGE, command)
        self.assertIn('--init', command)
        for forbidden in ('--privileged', '--cap-add', '--network=host', '--pid=host', '--ipc=host'):
            self.assertNotIn(forbidden, command)
        self.assertFalse(any('docker.sock' in item for item in command))
        self.assertTrue(any(item == '--user' or item.startswith('--user=') for item in command))
        mounts = docker_mounts(command)
        runtime_sources = {str(source) for source, _ in self.runtime['mounts']}
        readonly_sources = runtime_sources | {str(self.certificate)}
        expected_sources = readonly_sources | {str(self.workspace), str(self.temporary)}
        self.assertEqual({source for source, _, _ in mounts}, expected_sources)
        for source, target, readonly in mounts:
            self.assertTrue(target.startswith('/'))
            self.assertEqual(readonly, source in readonly_sources,
                             'Host Python is read-only; reports and isolated tools remain writable')
            self.assertNotIn(source, ('/', '/usr', '/usr/local', '/var', '/tmp'))
        environment = [command[index + 1] for index, value in enumerate(command)
                       if value in ('--env', '-e')]
        self.assertIn('PYTHONHOME=/host-python', environment)
        self.assertIn('LD_LIBRARY_PATH=/host-python/lib', environment)
        self.assertTrue(any(value.startswith('HOME=') for value in environment))
        self.assertIn('NODE_EXTRA_CA_CERTS=/host-ca-certificates.crt', environment)
        self.assertIn('npm_config_strict_ssl=true', environment)
        self.assertFalse(any(value.startswith(('GITHUB_TOKEN=', 'GH_TOKEN=', 'PYTHONPATH='))
                             for value in environment))

    def invoke(self, *, prepare=False, failure=None):
        calls = []

        def execute(command, **kwargs):
            command = list(command)
            calls.append((command, kwargs))
            failed = failure(command) if failure else False
            if isinstance(failed, Exception):
                raise failed
            if failed:
                raise subprocess.CalledProcessError(17, command)
            return subprocess.CompletedProcess(command, 0, stdout='', stderr='')

        with patch.object(qa.shutil, 'which', return_value='/usr/bin/docker'), \
                patch.object(qa, 'python_runtime', return_value=self.runtime), \
                patch.object(qa.subprocess, 'run', side_effect=execute):
            try:
                qa.run(prepare=prepare)
            except Exception as error:
                return calls, error
        return calls, None

    def test_preparation_pulls_installs_and_smokes_without_running_the_suite(self):
        calls, error = self.invoke(prepare=True)
        self.assertIsNone(error)
        commands = [command for command, _ in calls]
        self.assertEqual(sum(command[:2] == ['docker', 'pull'] for command in commands), 1)
        self.assertTrue(any(command[:2] == ['docker', 'pull'] and EXPECTED_IMAGE in command
                            for command in commands))
        runs = [command for command in commands if command[:2] == ['docker', 'run']]
        self.assertGreaterEqual(len(runs), 2)
        content = '\n'.join(' '.join(command) for command in runs)
        self.assertIn('playwright@1.62.1', content)
        self.assertNotIn('install --with-deps', content)
        self.assertNotIn('apt-get', content)
        self.assertNotIn('ui_contract.cjs', content)
        self.assertIn('chromium', content)
        for command, options in calls:
            self.assertTrue(options.get('timeout', 0) > 0, 'Every Docker stage must have a deadline')
            if command[:2] != ['docker', 'rm']:
                self.assertTrue(options.get('check'), 'Bootstrap errors must propagate')

    def test_failed_image_pull_stops_before_browser_or_ui_commands(self):
        calls, error = self.invoke(failure=lambda command: command[:2] == ['docker', 'pull'])
        self.assertIsInstance(error, (subprocess.CalledProcessError, RuntimeError))
        self.assertFalse(any(command[:2] == ['docker', 'run'] for command, _ in calls))

    def test_every_container_is_removed_by_its_owned_name_even_after_timeout(self):
        calls, error = self.invoke(failure=lambda command:
                                  subprocess.TimeoutExpired(command, 900)
                                  if qa.test_script() in command else False)
        self.assertIsInstance(error, subprocess.TimeoutExpired)
        runs = [command for command, _ in calls if command[:2] == ['docker', 'run']]
        self.assertEqual(len(runs), 3)
        owned = {command[command.index('--name') + 1] for command in runs}
        self.assertEqual(len(owned), 3)
        removed = {command[-1] for command, _ in calls if command[:3] == ['docker', 'rm', '--force']}
        self.assertEqual(removed, owned)
        self.assertFalse(any('prune' in command for command, _ in calls))

    def test_dependency_failure_stops_before_smoke_and_ui(self):
        calls, error = self.invoke(failure=lambda command:
                                  command[:2] == ['docker', 'run'] and 'npm' in command)
        self.assertIsInstance(error, subprocess.CalledProcessError)
        self.assertEqual(sum(command[:2] == ['docker', 'run'] for command, _ in calls), 1)
        self.assertEqual(sum(command[:3] == ['docker', 'rm', '--force'] for command, _ in calls), 1)

    def test_absent_public_ca_does_not_forward_arbitrary_host_certificate_settings(self):
        self.certificate.unlink()
        with patch.dict(qa.os.environ, {'NODE_EXTRA_CA_CERTS': '/private/secret.pem',
                                      'NODE_TLS_REJECT_UNAUTHORIZED': '0'}):
            command = qa.docker_command(['node', '-e', 'synthetic'], runtime=self.runtime,
                                        workspace=self.workspace, temporary=self.temporary,
                                        name='synthetic-no-ca')
        self.assertNotIn('/private/secret.pem', ' '.join(command))
        self.assertFalse(any('NODE_EXTRA_CA_CERTS=' in value for value in command))
        self.assertFalse(any('NODE_TLS_REJECT_UNAUTHORIZED=' in value for value in command))
        self.assertIn('npm_config_strict_ssl=true', command)

    def test_unsafe_bind_path_fails_before_docker_can_interpret_another_mount(self):
        for workspace in (self.directory/'source,readonly', self.directory/'source\nextra'):
            with self.subTest(workspace=workspace):
                with self.assertRaises(RuntimeError):
                    qa.docker_command(['node'], runtime=self.runtime, workspace=workspace,
                                      temporary=self.temporary, name='synthetic-invalid')

    def test_missing_docker_fails_instead_of_skipping_ui_validation(self):
        with patch.object(qa.shutil, 'which', return_value=None), \
                patch.object(qa.subprocess, 'run') as execute:
            with self.assertRaises(RuntimeError):
                qa.run()
        execute.assert_not_called()

    def test_python_probe_mounts_the_resolved_runtime_soname_instead_of_host_directories(self):
        binary, standard, library = (source for source, _ in self.runtime['mounts'])
        soname = 'libpython3.12.so.1.0'
        answer = subprocess.CompletedProcess(['ldd'], 0,
                                             stdout='\t' + soname + ' => ' + str(library) + ' (0x1234)\n')
        with patch.object(qa.sys, 'executable', str(binary)), \
                patch.object(qa.sysconfig, 'get_path', return_value=str(standard)), \
                patch.object(qa.subprocess, 'run', return_value=answer) as execute:
            runtime = qa.python_runtime()
        self.assertEqual(runtime['mounts'][0], (binary, '/host-python/bin/python3'))
        self.assertIn((library, '/host-python/lib/' + soname), runtime['mounts'])
        self.assertEqual(len(runtime['mounts']), 3)
        self.assertEqual(runtime['environment']['PYTHONHOME'], '/host-python')
        self.assertEqual(runtime['version'], sys.version)
        self.assertEqual(execute.call_args.args[0], ['ldd', str(binary)])
        self.assertTrue(execute.call_args.kwargs['check'])
        self.assertGreater(execute.call_args.kwargs['timeout'], 0)

    def test_python_probe_rejects_unresolved_libpython_before_container_execution(self):
        binary, standard = (source for source, _ in self.runtime['mounts'][:2])
        answer = subprocess.CompletedProcess(['ldd'], 0, stdout='\tlibpython3.12.so.1.0 => not found\n')
        with patch.object(qa.sys, 'executable', str(binary)), \
                patch.object(qa.sysconfig, 'get_path', return_value=str(standard)), \
                patch.object(qa.subprocess, 'run', return_value=answer):
            with self.assertRaises(RuntimeError):
                qa.python_runtime()


@unittest.skipUnless(shutil.which('node'), 'Node is required for the synthetic suite-runner probe')
class BrowserSuiteRunnerTests(unittest.TestCase):
    def run_script(self, failure=None):
        harness = r'''
const fs = require('fs'), vm = require('vm');
const input = JSON.parse(fs.readFileSync(0, 'utf8'));
const report = {calls:[], exit:0, error:null};
class Exit { constructor(code) { this.code=code; } }
const child = {spawnSync(executable,args,options) {
  const index=report.calls.length;report.calls.push({executable,args,options});
  return input.failure===index ? {status:17} : {status:0};
}};
const processStub = {execPath:'/container/node',env:{CI:'1'},exit(code){throw new Exit(code);}};
try { vm.runInNewContext(input.script,{process:processStub,console:{log(){}},require(name){
  if(name==='child_process')return child;
  if(name==='playwright')return {chromium:{executablePath:()=>'/ms-playwright/chromium/chrome'}};
  throw Error('Unexpected dependency: '+name);
}}); } catch(error) {
  if(error instanceof Exit)report.exit=error.code;else report.error=String(error);
}
process.stdout.write(JSON.stringify(report));
'''
        result = subprocess.run([shutil.which('node'), '-e', harness],
                                input=json.dumps({'script': qa.test_script(), 'failure': failure}),
                                text=True, capture_output=True, check=True, timeout=10)
        return json.loads(result.stdout)

    def test_actual_suite_runner_executes_all_six_once_in_order_with_pinned_chromium(self):
        report = self.run_script()
        self.assertIsNone(report['error'])
        self.assertEqual(report['exit'], 0)
        self.assertEqual([call['args'] for call in report['calls']],
                         [['mods/sessionstats/tests/' + name + '.cjs'] for name in EXPECTED_SUITES])
        for call in report['calls']:
            self.assertEqual(call['executable'], '/container/node')
            self.assertEqual(call['options']['env']['GRZ_CHROME'], '/ms-playwright/chromium/chrome')
            self.assertEqual(call['options']['stdio'], 'inherit')

    def test_actual_suite_runner_propagates_failure_and_does_not_run_remaining_suites(self):
        report = self.run_script(failure=2)
        self.assertIsNone(report['error'])
        self.assertEqual(report['exit'], 17)
        self.assertEqual(len(report['calls']), 3)


if __name__ == '__main__':
    unittest.main()
