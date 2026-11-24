#!/usr/bin/env python3
"""Run CI browser checks with pinned Chromium and isolated dependencies."""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import sysconfig
import tempfile
import uuid

ROOT = Path(__file__).resolve().parents[2]
PLAYWRIGHT_VERSION = '1.62.1'
# Official MCR OCI index; amd64 is selected explicitly on every pull and run.
IMAGE = ('mcr.microsoft.com/playwright:v1.62.1-noble@sha256:'
         'dcc5531e97840b9b5e794f2814476b21571c5124a3fca2267d73041f56e7580e')
UI_TESTS = ('ui_contract', 'ui-wheel', 'ui-footer', 'ui-footer-activity',
            'ui-footer-compat', 'ui-appearance')
E2E_MODES = {'build': ('build', 'failures'), 'smoke': ('build', 'all'),
             'full': ('full', 'final'), 'exhaustive': ('full', 'final')}
PULL_TIMEOUT = 600
PREPARE_TIMEOUT = 300
TEST_TIMEOUT = 900
MATRIX_TIMEOUT = 150 * 60
HOST_CA = Path('/etc/ssl/certs/ca-certificates.crt')


def python_runtime():
    """Map only this isolated host interpreter's runtime into the Noble image."""
    executable = Path(sys.executable).resolve(strict=True)
    version = '{}.{}'.format(*sys.version_info[:2])
    stdlib = Path(sysconfig.get_path('stdlib')).resolve(strict=True)
    platstdlib = Path(sysconfig.get_path('platstdlib')).resolve(strict=True)
    mounts = [(executable, '/host-python/bin/python3'),
              (stdlib, '/host-python/lib/python' + version)]
    prefix = '/host-python'
    if platstdlib != stdlib:
        mounts.append((platstdlib, '/host-python/plat/lib/python' + version))
        prefix += ':/host-python/plat'
    # ldd resolves the actual runtime SONAME, including interpreters whose
    # development libpython symlink is absent. Static libpython needs no mount.
    linked = subprocess.run(['ldd', str(executable)], check=True,
                            capture_output=True, text=True, timeout=30).stdout
    for soname, source in re.findall(r'^\s*(libpython\S+)\s+=>\s+(\S+)\s+\(',
                                      linked, re.MULTILINE):
        mounts.append((Path(source).resolve(strict=True), '/host-python/lib/' + soname))
    if re.search(r'libpython\S+\s+=>\s+not found', linked):
        raise RuntimeError('The host interpreter has an unresolved libpython dependency')
    return {'mounts': mounts,
            'environment': {'PYTHONHOME': prefix,
                            'LD_LIBRARY_PATH': '/host-python/lib'},
            'version': sys.version}


def docker_command(command, *, runtime, workspace, temporary, name, offline=False):
    """Build a container command without forwarding host credentials or sockets."""
    args = ['docker', 'run', '--rm', '--init', '--platform', 'linux/amd64',
            '--shm-size=1g', '--name', name, '--user', '{}:{}'.format(os.getuid(), os.getgid()),
            '--workdir', str(workspace)]
    if offline:
        args += ['--network', 'none']
    mounts = [(workspace, str(workspace), False),
              (temporary, str(temporary), False)]
    mounts += [(source, target, True) for source, target in runtime['mounts']]
    if HOST_CA.is_file():
        mounts.append((HOST_CA, '/host-ca-certificates.crt', True))
    for source, target, readonly in mounts:
        if any(c in str(source) + str(target) for c in ',\n\r'):
            raise RuntimeError('Docker bind paths cannot contain commas or newlines')
        spec = 'type=bind,src={},dst={}'.format(source, target)
        args += ['--mount', spec + (',readonly' if readonly else '')]
    environment = {
        'HOME': str(temporary / 'home'), 'CI': '1',
        'NODE_PATH': str(temporary / 'tools/node_modules'),
        'PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD': '1',
        'PLAYWRIGHT_BROWSERS_PATH': '/ms-playwright',
        'npm_config_strict_ssl': 'true',
        'GRZ_PYTHON3': '/host-python/bin/python3',
        'PYTHONNOUSERSITE': '1', 'PYTHONDONTWRITEBYTECODE': '1',
        'PATH': '/host-python/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin',
        **runtime['environment'],
    }
    if offline:
        environment['GITHUB_ACTIONS'] = 'true'
    if HOST_CA.is_file():
        environment['NODE_EXTRA_CA_CERTS'] = '/host-ca-certificates.crt'
    for key, value in sorted(environment.items()):
        args += ['--env', key + '=' + value]
    return args + [IMAGE] + list(command)


def execute(command, timeout, **options):
    subprocess.run(command, check=True, timeout=timeout, **options)


def container(command, *, runtime, workspace, temporary, timeout, offline=False):
    name = 'sessionstats-browser-' + uuid.uuid4().hex
    try:
        execute(docker_command(command, runtime=runtime, workspace=workspace,
                               temporary=temporary, name=name, offline=offline), timeout)
    finally:
        # Killing a timed-out Docker CLI does not stop its container. Remove
        # this invocation's unique name only; never prune unrelated containers.
        subprocess.run(['docker', 'rm', '--force', name], check=False, timeout=30,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def smoke_script(runtime):
    python_code = (
        'import json,sys; '
        'from grz_session_stats.appearance import default_config,build_presentation; '
        'assert sys.version == ' + repr(runtime['version']) + '; '
        'assert isinstance(build_presentation(default_config()),dict); '
        'print("Mounted host Python configuration smoke OK: " + sys.version)')
    return """
const fs = require('fs');
const path = require('path');
const {spawnSync} = require('child_process');
const {chromium} = require('playwright');
if (require('playwright/package.json').version !== %s) throw Error('Playwright version mismatch');
const executable = chromium.executablePath();
if (!executable.startsWith('/ms-playwright/')) throw Error('Unexpected Chromium installation');
fs.accessSync(executable, fs.constants.X_OK);
const python = spawnSync(process.env.GRZ_PYTHON3, ['-c', %s], {
  stdio:'inherit', env:{...process.env, PYTHONPATH:path.join(process.cwd(),'mods/sessionstats/src')}
});
if (python.error) throw python.error;
if (python.status !== 0) process.exit(python.status || 1);
(async () => {
  const browser = await chromium.launch({headless:true, executablePath:executable, args:['--no-sandbox']});
  try {
    const page = await browser.newPage();
    await page.setContent('<p>Session Stats Chromium smoke</p>');
    if (await page.locator('p').textContent() !== 'Session Stats Chromium smoke') throw Error('Chromium smoke failed');
    console.log('Pinned Chromium smoke OK: ' + browser.version());
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
""" % (json.dumps(PLAYWRIGHT_VERSION), json.dumps(python_code))


def test_script():
    return """
const {spawnSync} = require('child_process');
const {chromium} = require('playwright');
for (const name of %s) {
  console.log('Running browser suite: ' + name);
  const result = spawnSync(process.execPath, ['mods/sessionstats/tests/' + name + '.cjs'], {
    stdio:'inherit', env:{...process.env, GRZ_CHROME:chromium.executablePath()}
  });
  if (result.error) throw result.error;
  if (result.status !== 0) process.exit(result.status || 1);
}
""" % json.dumps(UI_TESTS)


def e2e_command(profile, report_dir, shard, target_sha=None, *, python='/host-python/bin/python3'):
    suite, capture = E2E_MODES[profile]
    command = ['node', 'scripts/sessionstats/local-e2e/run.cjs', '--suite', suite,
               '--engine', 'chromium', '--python', python,
               '--capture', capture, '--out', str(report_dir)]
    if suite == 'full':
        command += ['--image-format', 'jpeg', '--jpeg-quality', '48']
    if profile == 'exhaustive':
        command += ['--all-ranges']
    if shard or profile == 'smoke':
        command += ['--shard', shard or '1/1']
    if target_sha:
        command += ['--commit', target_sha]
    return command


def merge_report_command(profile, report_dir, expected_shards, parts, target_sha=None, upstream=None):
    suite, capture = E2E_MODES[profile]
    version = (ROOT / 'mods/sessionstats/VERSION').read_text(encoding='ascii').strip()
    command = ['node', 'scripts/sessionstats/local-e2e/merge-report.cjs', '--out', str(report_dir),
               '--expected-shards', str(expected_shards), '--expected-version', version,
               '--expected-suite', suite, '--expected-capture', capture, '--coverage', profile]
    if target_sha:
        command += ['--expected-commit', target_sha]
    for name, result in (upstream or {}).items():
        command += ['--' + name + '-result', result]
    return command + ['--', *parts]


def checkout_commit():
    sha = subprocess.check_output(['git', 'rev-parse', '--verify', 'HEAD'], cwd=ROOT, text=True, timeout=10).strip()
    if not re.fullmatch(r'[0-9a-f]{40}', sha):
        raise RuntimeError('The matrix checkout does not have a valid commit SHA')
    return sha


def verify_target_checkout(sha):
    if checkout_commit() != sha:
        raise RuntimeError('The checked-out commit does not match the planned matrix commit')


def target_commit(explicit, *, render_matrix):
    if explicit:
        verify_target_checkout(explicit)
        return explicit
    # Before the default workflow passed --target-sha, its checkout was already
    # pinned to the planned PR head. GITHUB_SHA names the default branch instead.
    if (render_matrix and os.environ.get('GITHUB_ACTIONS') == 'true'
            and os.environ.get('GITHUB_EVENT_NAME') == 'issue_comment'):
        return checkout_commit()
    return None


def windows_smoke(report_dir, target_sha):
    """Run the normal build check using Windows CPython and Chromium directly."""
    npm = shutil.which('npm.cmd')
    if npm is None or shutil.which('node.exe') is None:
        raise RuntimeError('Windows browser smoke requires Node.js 22 or later with npm')
    # Forward OS process and network settings. The synthetic test does not
    # need the runner's GitHub credentials, workflow commands or user modules.
    inherited = {'path', 'pathext', 'systemroot', 'windir', 'comspec', 'temp', 'tmp',
                 'programfiles', 'programfiles(x86)', 'programdata', 'userprofile',
                 'localappdata', 'appdata', 'homedrive', 'homepath', 'http_proxy',
                 'https_proxy', 'no_proxy'}
    environment = {key: value for key, value in os.environ.items() if key.lower() in inherited}
    directory = os.environ.get('RUNNER_TEMP') or None
    with tempfile.TemporaryDirectory(prefix='sessionstats-browser-', dir=directory) as directory:
        temporary = Path(directory).resolve()
        tools = temporary / 'tools'
        tools.mkdir()
        modules = tools / 'node_modules'
        dependencies = temporary / 'python'
        environment.update({'CI': '1', 'GITHUB_ACTIONS': 'true', 'NODE_PATH': str(modules),
                            'PLAYWRIGHT_BROWSERS_PATH': str(temporary / 'browsers'),
                            'PYTHONPATH': str(dependencies), 'PYTHONNOUSERSITE': '1',
                            'PYTHONDONTWRITEBYTECODE': '1', 'npm_config_strict_ssl': 'true',
                            'npm_config_userconfig': str(temporary / 'npmrc'),
                            'npm_config_cache': str(temporary / 'npm-cache')})
        options = {'cwd': ROOT, 'env': environment}
        execute([sys.executable, '-I', '-m', 'pip', '--isolated', 'install', '--disable-pip-version-check', '--no-cache-dir',
                 '--target', str(dependencies), '-r', str(ROOT / 'scripts/sessionstats/local-e2e/requirements.txt')],
                PREPARE_TIMEOUT, **options)
        execute([npm, 'install', '--prefix', str(tools), '--no-audit', '--no-fund', '--ignore-scripts',
                 '--save-exact', 'playwright@' + PLAYWRIGHT_VERSION], PREPARE_TIMEOUT, **options)
        execute(['node', str(modules / 'playwright/cli.js'), 'install', '--only-shell', 'chromium'],
                PULL_TIMEOUT, **options)
        execute(e2e_command('build', report_dir or temporary / 'report', None, target_sha, python=sys.executable),
                TEST_TIMEOUT, **options)


def run(prepare=False, *, e2e=None, report_dir=None, shard=None, target_sha=None):
    if report_dir is not None:
        report_dir = report_dir.resolve()
        if ROOT not in report_dir.parents:
            raise RuntimeError('The CI report directory must be inside the workspace')
    if sys.platform == 'win32' and e2e == 'build':
        windows_smoke(report_dir, target_sha)
        return
    if not shutil.which('docker'):
        raise RuntimeError('Docker is required for the pinned browser QA runtime')
    runtime = python_runtime()
    execute(['docker', 'pull', '--platform', 'linux/amd64', IMAGE], PULL_TIMEOUT)
    directory = os.environ.get('RUNNER_TEMP') or None
    with tempfile.TemporaryDirectory(prefix='sessionstats-browser-', dir=directory) as directory:
        temporary = Path(directory).resolve()
        (temporary / 'home').mkdir()
        (temporary / 'tools').mkdir()
        options = {'runtime': runtime, 'workspace': ROOT, 'temporary': temporary}
        container(['npm', 'install', '--prefix', str(temporary / 'tools'), '--no-audit',
                   '--no-fund', '--save-exact', 'playwright@' + PLAYWRIGHT_VERSION],
                  timeout=PREPARE_TIMEOUT, **options)
        container(['node', '-e', smoke_script(runtime)], timeout=PREPARE_TIMEOUT, **options)
        if e2e:
            timeout = MATRIX_TIMEOUT if e2e in ('full', 'exhaustive') else TEST_TIMEOUT
            container(e2e_command(e2e, report_dir or temporary / 'report', shard, target_sha),
                      timeout=timeout, offline=True, **options)
        elif not prepare:
            container(['node', '-e', test_script()], timeout=TEST_TIMEOUT, **options)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument('--prepare', action='store_true', help='Install and smoke-test the runtime only')
    modes.add_argument('--e2e', choices=E2E_MODES,
                       help='Render a short CI check or an on-demand matrix')
    modes.add_argument('--merge-report', choices=E2E_MODES, help='Assemble the downloaded matrix parts')
    parser.add_argument('--report-dir', type=Path, help='Keep the report under this workspace path')
    parser.add_argument('--shard', help='Render the given full-matrix shard (N/M)')
    parser.add_argument('--expected-shards', type=int, help='Number of shards from the CI plan')
    parser.add_argument('--target-sha', help='Commit from the CI plan')
    jobs = ('render', 'contracts', 'download')
    for name in jobs:
        parser.add_argument('--' + name + '-result', choices=('success', 'failure', 'cancelled', 'skipped'),
                            help='Outcome from the workflow')
    parser.add_argument('parts', nargs='*', help='Shard directories to merge')
    args = parser.parse_args()
    if args.report_dir is not None and not (args.e2e or args.merge_report):
        parser.error('--report-dir requires --e2e or --merge-report')
    if args.shard and args.e2e not in ('full', 'exhaustive'):
        parser.error('--shard requires --e2e full or --e2e exhaustive')
    if args.target_sha is not None and (not (args.e2e or args.merge_report) or
                                        not re.fullmatch(r'[0-9a-f]{40}', args.target_sha)):
        parser.error('--target-sha requires a 40-character commit SHA with --e2e or --merge-report')
    if args.merge_report:
        if not args.report_dir or not args.expected_shards or args.expected_shards < 1:
            parser.error('--merge-report requires --report-dir and a positive --expected-shards')
    elif args.expected_shards is not None or args.parts:
        parser.error('--expected-shards and shard directories require --merge-report')
    upstream = {name: getattr(args, name + '_result') for name in jobs}
    if any(upstream.values()) and (not args.merge_report or not all(upstream.values())):
        parser.error('Provide all three job results with --merge-report')
    try:
        sha = target_commit(args.target_sha, render_matrix=args.e2e or args.merge_report)
        if args.merge_report:
            command = merge_report_command(args.merge_report, args.report_dir, args.expected_shards, args.parts,
                                           target_sha=sha, upstream=upstream if all(upstream.values()) else None)
            return subprocess.run(command, cwd=ROOT, check=False).returncode
        run(prepare=args.prepare, e2e=args.e2e, report_dir=args.report_dir, shard=args.shard, target_sha=sha)
    except (OSError, RuntimeError, subprocess.SubprocessError) as error:
        print('Browser QA failed: ' + str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
