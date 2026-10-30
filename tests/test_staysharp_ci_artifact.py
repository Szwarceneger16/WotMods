"""The PR download must preserve the reviewed medkit, not the version probe."""
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
CI = (ROOT / '.github/workflows/ci.yml').read_text(encoding='utf-8')


def step(name):
    return CI.split('      - name: ' + name + '\n', 1)[1].split('\n      - ', 1)[0]


def package_commands():
    body = step('Package reviewed Stay Sharp installer').split('        run: |\n', 1)[1]
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
        baseline = (ROOT / 'VERSION').read_text(encoding='ascii').strip()
        major, minor, patch = baseline.split('.')
        next_version = '%s.%s.%s' % (major, minor, int(patch) + 1)
        env = dict(os.environ)
        env.pop('WOTMOD_VERSION', None)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for directory in ('source', 'assets', 'scripts', 'docs'):
                shutil.copytree(ROOT / directory, root / directory,
                                ignore=shutil.ignore_patterns('__pycache__'))
            shutil.copy2(ROOT / 'VERSION', root / 'VERSION')
            sample = ROOT / 'staysharp.medkit.example.json'
            if sample.is_file():
                shutil.copy2(sample, root / sample.name)

            def run(command, process_env=env):
                result = subprocess.run(command, cwd=root, env=process_env,
                                        capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

            run([sys.executable, 'source/build_wotmod.py'])
            primary = 'com.staysharp.medkitreminder_' + baseline + '.wotmod'
            reviewed = (root / 'dist' / primary).read_bytes()
            run(['bash', '-c', package_commands()])
            installer = root / 'pr-artifact' / ('StaySharp-Medkit-v' + baseline + '.zip')
            original = installer.read_bytes()
            run([sys.executable, 'source/build_wotmod.py'],
                dict(env, WOTMOD_VERSION=next_version))
            self.assertEqual(installer.read_bytes(), original)
            self.assertEqual([p.name for p in installer.parent.glob('*.zip')],
                             [installer.name])

            spec = importlib.util.spec_from_file_location(
                'artifact_installer', root / 'scripts/release_installers.py')
            packager = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(packager)
            kind, version, _, files, mod_path = packager.verify(installer)
            self.assertEqual((kind, version), ('staysharp', baseline))
            self.assertEqual(files[mod_path], reviewed)
            self.assertEqual([n for n in files if n.endswith('.wotmod')], [mod_path])
            self.assertIn('mods/configs/staysharp.medkit.json.example', files)
            self.assertFalse(any('sessionstats' in n for n in files))
            self.assertFalse(any(n.endswith('.json') and n.startswith('mods/configs/')
                                 for n in files))
            with zipfile.ZipFile(installer) as archive:
                self.assertIsNone(archive.testzip())


if __name__ == '__main__':
    unittest.main()
