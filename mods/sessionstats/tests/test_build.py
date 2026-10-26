# -*- coding: utf-8 -*-
"""Builder contracts; Python 2.7 runs only the game-runtime tests."""
from __future__ import unicode_literals
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest


@unittest.skipUnless(sys.version_info[0] >= 3, 'Packaging uses Python 3')
class BuildContracts(unittest.TestCase):
    def setUp(self):
        import importlib.util
        from pathlib import Path
        root = Path(__file__).resolve().parents[1]
        spec = importlib.util.spec_from_file_location('sessionstats_builder', root/'tools/build.py')
        self.build = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.build)
        self.directory = Path(tempfile.mkdtemp(prefix='sessionstats-builder-test-'))

    def tearDown(self):
        shutil.rmtree(str(self.directory))

    def test_active_guides_use_requested_package_and_client_versions(self):
        major, minor, patch = map(int, self.build.VERSION.split('.'))
        version = '%d.%d.%d' % (major, minor, patch + 1)
        source_package = ('grz.sessionstats_' + self.build.VERSION + '.wotmod').encode('ascii')
        target_package = ('grz.sessionstats_' + version + '.wotmod').encode('ascii')
        for name in self.build.RELEASE_GUIDES:
            original = (self.build.ROOT/name).read_bytes()
            rendered = self.build.render_guide(name, original, version, '2.5.0.0')
            self.assertNotIn(source_package, rendered)
            if source_package in original:
                self.assertIn(target_package, rendered)
            self.assertNotIn(b'mods/2.4.1.0/', rendered)
        readme = self.build.render_guide('README_PL.txt', (self.build.ROOT/'README_PL.txt').read_bytes(), version, '2.5.0.0')
        self.assertIn(('Version ' + version).encode('ascii'), readme)

    def test_historical_changelog_is_not_rewritten(self):
        content = (self.build.ROOT/'ZMIANY.txt').read_bytes()
        self.assertEqual(self.build.render_guide('ZMIANY.txt', content, '0.2.8', '2.5.0.0'), content)

    def test_every_release_field_advances_again_from_a_stamped_source_bundle(self):
        fields = {
            'README_PL.txt': ('Version {version} ',),
            'README.md': ('Version {version} source:',),
            'CONTRACT.txt': ('IMPLEMENTATION CONTRACT v{version} ', " version: '{version}',"),
            'docs/APPEARANCE_CONFIG.md': ('# Appearance and scrolling configuration — {version}\n',),
        }
        source_version = self.build.VERSION
        guides = {name: (self.build.ROOT/name).read_bytes() for name in fields}
        major, minor, patch = map(int, source_version.split('.'))
        versions = ('%d.%d.%d' % (major, minor, patch + 1), '%d.0.0' % (major + 1))
        try:
            for version in versions:
                guides = {name: self.build.render_guide(name, content, version, '2.5.0.0')
                          for name, content in guides.items()}
                for name, markers in fields.items():
                    for marker in markers:
                        self.assertIn(marker.format(version=version).encode('utf-8'), guides[name], name)
                        self.assertNotIn(marker.format(version=self.build.VERSION).encode('utf-8'), guides[name], name)
                # The extracted builder reads the new source/VERSION on rebuild.
                self.build.VERSION = version
        finally:
            self.build.VERSION = source_version

    def test_active_guides_keep_explicit_historical_version_evidence(self):
        historical = {
            'README.md': b'The user tested 0.2.4',
            'README_PL.txt': b'Since 0.2.7,',
            'CONTRACT.txt': b'Historical compatibility: upgrading from 0.2.6 to 0.2.7',
        }
        for name, marker in historical.items():
            original = (self.build.ROOT/name).read_bytes()
            self.assertIn(marker, original)
            self.assertIn(marker, self.build.render_guide(name, original, '1.0.0', '2.5.0.0'))

    def test_guides_are_byte_identical_when_version_and_client_are_unchanged(self):
        for name in self.build.RELEASE_GUIDES:
            content = (self.build.ROOT/name).read_bytes()
            current = re.search(br'(?:mods/|Wargaming EU )([0-9]+(?:\.[0-9]+){3})', content)
            client = current.group(1).decode('ascii') if current else '2.4.1.0'
            self.assertEqual(self.build.render_guide(name, content, self.build.VERSION, client), content)

    def test_rebuilt_guides_restamp_every_client_installation_and_target_field(self):
        for name in self.build.RELEASE_GUIDES:
            content = (self.build.ROOT/name).read_bytes()
            for client in ('2.5.0.0', '2.6.0.0', '2.4.1.0'):
                content = self.build.render_guide(name, content, self.build.VERSION, client)
                for other in {'2.4.1.0', '2.5.0.0', '2.6.0.0'} - {client}:
                    self.assertNotIn(other.encode('ascii'), content, name)
                if name == 'README_PL.txt':
                    for marker in ('target: Wargaming EU ', 'For client ',
                                   'active mods directory is not ', '--client-version ', 'mods/'):
                        self.assertIn((marker+client).encode('ascii'), content)
                if name == 'CONTRACT.txt':
                    self.assertIn(('Target: World of Tanks PC Wargaming EU '+client).encode('ascii'), content)
                if name != 'README.md':
                    self.assertIn(('mods/'+client+'/').encode('ascii'), content)

    def test_client_restamping_preserves_historical_evidence_and_unrelated_versions(self):
        content = b'Historical WoT 2.4.1 source; Python 2.7.18; OpenWG 1.2.2.\n'
        self.assertEqual(self.build.render_guide('README.md', content, '0.2.8', '2.6.0.0'), content)
        for name in ('ZMIANY.txt', 'docs/UI_0.2.2_SOURCE_EVIDENCE.md'):
            content = (self.build.ROOT/name).read_bytes()
            self.assertEqual(self.build.render_guide(name, content, '0.2.8', '2.6.0.0'), content)

    def test_client_version_rejects_a_trailing_newline_before_invoking_the_compiler(self):
        result = subprocess.run([sys.executable, str(self.build.ROOT/'tools/build.py'),
                                 '--python27', 'unused-compiler', '--client-version', '2.5.0.0\n'],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.assertEqual(result.returncode, 2)
        self.assertIn(b'Client version must have four numeric parts', result.stderr)

    def test_installer_manifest_verifies_from_extracted_archive_root(self):
        files=[]
        for name, relative in [('grz.sessionstats_0.2.8.wotmod','mods/2.5.0.0/'),
                               ('net.openwg.gameface_1.2.2.wotmod','mods/2.5.0.0/net.openwg/'),
                               ('grz.sessionstats.json','mods/configs/'),
                               ('grz.sessionstats.languages.json','mods/configs/')]:
            path = self.directory/relative/name
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_bytes(name.encode('ascii')); files.append(path)
        manifest = self.build.installer_checksums(files[0], files[1], files[2], '2.5.0.0', files[3])
        (self.directory/'SHA256SUMS.txt').write_bytes(manifest)
        self.assertEqual(len(manifest.splitlines()),4)
        subprocess.check_output(['sha256sum','-c','SHA256SUMS.txt'],cwd=str(self.directory))


if __name__ == '__main__': unittest.main()
