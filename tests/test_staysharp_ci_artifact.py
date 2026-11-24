"""The PR download must preserve the reviewed medkit, not the version probe."""
import importlib.util
import io
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
CI = (ROOT / '.github/workflows/ci.yml').read_text(encoding='utf-8')


def step(name):
    return CI.split('      - name: ' + name + '\n', 1)[1].split('\n      - ', 1)[0]


def commands(name):
    body = step(name).split('        run: |\n', 1)[1]
    return '\n'.join(line[10:] for line in body.splitlines()) + '\n'


class StaySharpArtifactTests(unittest.TestCase):
    def test_only_installable_medkit_is_uploaded_after_all_validation(self):
        package = CI.index('      - name: Package reviewed Stay Sharp installer\n')
        probe = CI.index('      - name: Test automatic next-release version')
        upload = CI.index('      - name: Upload installable Stay Sharp Medkit ZIP')
        self.assertLess(package, probe)
        self.assertLess(probe, upload)
        body = step('Upload installable Stay Sharp Medkit ZIP without repackaging')
        self.assertIn('path: pr-artifact/StaySharp-Medkit-v*.zip', body)
        self.assertIn('archive: false', body)
        self.assertIn('if-no-files-found: error', body)
        self.assertNotIn('sessionstats', body)
        self.assertNotIn('if: always()', body)
        self.assertRegex(body, r'uses: actions/upload-artifact@[0-9a-f]{40}')
        self.assertIn('contents: read', CI)
        self.assertNotIn('contents: write', CI)

    def test_exact_packaging_commands_preserve_baseline_through_next_version_probe(self):
        module = ROOT / 'mods/staysharp'
        if module.is_dir():
            inputs = ('mods/staysharp', 'scripts')
        else:
            module = ROOT
            inputs = ('source', 'assets', 'scripts', 'docs')
        baseline = (module / 'VERSION').read_text(encoding='ascii').strip()
        major, minor, patch = baseline.split('.')
        next_version = '%s.%s.%s' % (major, minor, int(patch) + 1)
        env = dict(os.environ)
        env.pop('WOTMOD_VERSION', None)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for directory in inputs:
                shutil.copytree(ROOT / directory, root / directory,
                                ignore=shutil.ignore_patterns('__pycache__', 'dist'))
            if module == ROOT:
                shutil.copy2(ROOT / 'VERSION', root / 'VERSION')
                sample = ROOT / 'staysharp.medkit.example.json'
                if sample.is_file():
                    shutil.copy2(sample, root / sample.name)

            def run(script, process_env=env):
                result = subprocess.run(['bash', '-c', script], cwd=root, env=process_env,
                                        capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

            github_env = root / 'github-env'
            run(commands('Python and base version'), dict(env, GITHUB_ENV=str(github_env)))
            env.update(line.split('=', 1) for line in github_env.read_text().splitlines())
            self.assertEqual(root / env['STAYSHARP_ROOT'], root / module.relative_to(ROOT))
            build = 'python3 "$STAYSHARP_BUILDER"'
            run(build)
            primary = 'com.staysharp.medkitreminder_' + baseline + '.wotmod'
            reviewed = (root / env['STAYSHARP_ROOT'] / 'dist' / primary).read_bytes()
            run(commands('Package reviewed Stay Sharp installer'))
            installer = root / 'pr-artifact' / ('StaySharp-Medkit-v' + baseline + '.zip')
            original = installer.read_bytes()
            run(build, dict(env, WOTMOD_VERSION=next_version))
            self.assertEqual(installer.read_bytes(), original)
            self.assertEqual([p.name for p in installer.parent.glob('*.zip')],
                             [installer.name])

            spec = importlib.util.spec_from_file_location(
                'artifact_installer', root / 'scripts/release_installers.py')
            packager = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(packager)
            kind, version, client, files, mod_path = packager.verify(installer)
            self.assertEqual((kind, version), ('staysharp', baseline))
            self.assertEqual(files[mod_path], reviewed)
            expected_packages={mod_path}
            with zipfile.ZipFile(installer) as outer:
                with zipfile.ZipFile(io.BytesIO(outer.read(mod_path))) as inner:
                    if packager.MEDKIT_GARAGE_RESOURCE in inner.namelist():
                        vendor='mods/'+client+'/net.openwg/'+packager.OPENWG_PACKAGE
                        expected_packages.add(vendor)
                        self.assertEqual(packager.digest(files[vendor]),packager.OPENWG_SHA256)
                        self.assertIn('docs/staysharp/OPENWG_LICENSE',files)
            self.assertEqual({n for n in files if n.endswith('.wotmod')}, expected_packages)
            self.assertIn('mods/configs/staysharp.medkit.json.example', files)
            self.assertFalse(any('sessionstats' in n for n in files))
            self.assertFalse(any(n.endswith('.json') and n.startswith('mods/configs/')
                                 for n in files))
            with zipfile.ZipFile(installer) as archive:
                self.assertIsNone(archive.testzip())


if __name__ == '__main__':
    unittest.main()
