#!/usr/bin/env python3
"""Run every browser check with pinned Chromium, fonts and OS dependencies."""
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
PULL_TIMEOUT = 600
PREPARE_TIMEOUT = 300
TEST_TIMEOUT = 900
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


def docker_command(command, *, runtime, workspace, temporary, name):
    """Build a container command without forwarding host credentials or sockets."""
    args = ['docker', 'run', '--rm', '--init', '--platform', 'linux/amd64',
            '--shm-size=1g', '--name', name, '--user', '{}:{}'.format(os.getuid(), os.getgid()),
            '--workdir', str(workspace)]
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
    if HOST_CA.is_file():
        environment['NODE_EXTRA_CA_CERTS'] = '/host-ca-certificates.crt'
    for key, value in sorted(environment.items()):
        args += ['--env', key + '=' + value]
    return args + [IMAGE] + list(command)


def execute(command, timeout):
    subprocess.run(command, check=True, timeout=timeout)


def container(command, *, runtime, workspace, temporary, timeout):
    name = 'sessionstats-browser-' + uuid.uuid4().hex
    try:
        execute(docker_command(command, runtime=runtime, workspace=workspace,
                               temporary=temporary, name=name), timeout)
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


def run(prepare=False):
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
        if not prepare:
            container(['node', '-e', test_script()], timeout=TEST_TIMEOUT, **options)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare', action='store_true', help='Install and smoke-test the runtime only')
    args = parser.parse_args()
    try:
        run(prepare=args.prepare)
    except (OSError, RuntimeError, subprocess.SubprocessError) as error:
        print('Browser QA failed: ' + str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
