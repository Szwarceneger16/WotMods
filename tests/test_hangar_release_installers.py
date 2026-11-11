"""Strict native Hangar ZIP verification and three-module coexistence."""
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import warnings
import zipfile

from test_release_installers import archive, build, r


def build_hangar(directory, version='0.14.0', client=r.CLIENT):
    """Create a synthetic native build without importing candidate mod code."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    package = {'meta.xml': ('<root><id>com.grz.hangarsync</id><version>' + version
                            + '</version></root>').encode('ascii')}
    for name in r.HANGAR_MODULES:
        package['res/scripts/client/gui/mods/' + name + '.pyc'] = b'\x03\xf3\r\n\x00\x00\x00\x00fixture'
    mod = archive(package)
    (directory / r.HANGAR_PACKAGE).write_bytes(mod)
    primary = 'mods/' + client + '/' + r.HANGAR_PACKAGE
    example = (json.dumps(r.HANGAR_EXAMPLE, indent=2) + '\n').encode('utf-8')
    files = {primary: mod, r.HANGAR_CONFIG: example,
             'README.md': b'Synthetic Hangar guide: configure locally before enabling.\n'}
    files['SHA256SUMS.txt'] = ''.join(r.digest(files[name]) + '  ' + name + '\n'
                                     for name in (primary, r.HANGAR_CONFIG)).encode('ascii')
    target = directory / r.installer_name('hangarsync', version)
    target.write_bytes(archive(files))
    return target


def checked_native(directory, files):
    """Refresh only native installable-byte hashes for adversarial fixtures."""
    primaries = [name for name in files if name.endswith('/' + r.HANGAR_PACKAGE)]
    if len(primaries) == 1 and r.HANGAR_CONFIG in files:
        files['SHA256SUMS.txt'] = ''.join(r.digest(files[name]) + '  ' + name + '\n'
                                         for name in (primaries[0], r.HANGAR_CONFIG)).encode('ascii')
    target = Path(directory) / 'GRZ_Hangar_Sync-v0.14.0.zip'
    target.write_bytes(archive(files))
    return target


class HangarInstallerTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.source = self.root / 'build'
        self.output = self.root / 'output'
        self.output.mkdir()
        self.native = build_hangar(self.source)

    def package(self):
        reviewed = self.root / 'reviewed'
        sample = reviewed / 'mods/hangarsync/GRZ_Hangar_Sync.json.example'
        sample.parent.mkdir(parents=True, exist_ok=True)
        sample.write_bytes(r.read_zip(self.native)[r.HANGAR_CONFIG])
        with patch.object(r, 'ROOT', reviewed):
            return r.package(self.source, self.output, 'hangarsync')

    def test_native_build_copies_exact_zip_without_rewrapping(self):
        original = self.native.read_bytes()
        target = self.package()
        self.assertEqual(target.read_bytes(), original)
        report = r.verify(target)
        self.assertEqual(report[:3], ('hangarsync', '0.14.0', r.CLIENT))
        self.assertEqual(report[4], 'mods/' + r.CLIENT + '/' + r.HANGAR_PACKAGE)
        self.assertEqual(set(report[3]), {report[4], r.HANGAR_CONFIG, 'README.md', 'SHA256SUMS.txt'})

    def test_personalized_enabled_extra_and_wrongly_typed_examples_are_rejected(self):
        original = r.read_zip(self.native)
        changes = ({'enabled': True}, {'device_token': 'synthetic-secret'},
                   {'endpoint_url': 'https://example.invalid/api/sync'},
                   {'display_name': 'Synthetic account'}, {'allowed_players': ['Synthetic player']},
                   {'expected_player': 'Synthetic player'}, {'include_crew': 0}, {'interval_seconds': True})
        for change in changes:
            with self.subTest(fields=list(change)):
                files = dict(original)
                config = dict(r.HANGAR_EXAMPLE, **change)
                files[r.HANGAR_CONFIG] = json.dumps(config).encode('utf-8')
                with self.assertRaisesRegex(ValueError, 'credential-free'):
                    r.verify(checked_native(self.output, files))
        files = dict(original)
        files[r.HANGAR_CONFIG] = b'{"enabled":false,"enabled":true}'
        with self.assertRaisesRegex(ValueError, 'Duplicate JSON'):
            r.verify(checked_native(self.output, files))

    def test_active_configuration_extra_resource_and_stale_manifest_are_rejected(self):
        original = r.read_zip(self.native)
        for name, value in ((r.HANGAR_CONFIG[:-8], b'{}'), ('private.log', b'fixture'),
                            ('other.zip', b'fixture')):
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, 'members'):
                r.verify(checked_native(self.output, dict(original, **{name: value})))
        files = dict(original)
        files[r.HANGAR_CONFIG] = b'{}'
        path = self.output / self.native.name
        path.write_bytes(archive(files))
        with self.assertRaisesRegex(ValueError, 'Checksum'):
            r.verify(path)

    def test_duplicate_outer_and_inner_archive_members_are_rejected(self):
        original = r.read_zip(self.native)
        primary = 'mods/' + r.CLIENT + '/' + r.HANGAR_PACKAGE
        for nested in (False, True):
            with self.subTest(nested=nested):
                members = r.read_zip(io.BytesIO(original[primary])) if nested else original
                output = io.BytesIO()
                with warnings.catch_warnings():
                    warnings.simplefilter('ignore', UserWarning)
                    with zipfile.ZipFile(output, 'w') as archive_file:
                        for name, content in members.items():
                            archive_file.writestr(name, content)
                        name = next(iter(members))
                        archive_file.writestr(name, members[name])
                path = self.output / self.native.name
                if nested:
                    files = dict(original)
                    files[primary] = output.getvalue()
                    path = checked_native(self.output, files)
                else:
                    path.write_bytes(output.getvalue())
                with self.assertRaisesRegex(ValueError, 'Duplicate ZIP'):
                    r.verify(path)

    def test_package_resources_and_identity_are_fixed_without_executing_bytecode(self):
        original = r.read_zip(self.native)
        primary = 'mods/' + r.CLIENT + '/' + r.HANGAR_PACKAGE
        for change in ('version', 'identifier', 'extra', 'missing', 'magic'):
            with self.subTest(change=change):
                files = dict(original)
                package = r.read_zip(io.BytesIO(files[primary]))
                if change == 'version':
                    package['meta.xml'] = package['meta.xml'].replace(b'0.14.0', b'0.13.0')
                elif change == 'identifier':
                    package['meta.xml'] = package['meta.xml'].replace(b'com.grz.hangarsync', b'unknown.package')
                elif change == 'extra':
                    package['res/extra.pyc'] = b'fixture'
                else:
                    name = 'res/scripts/client/gui/mods/mod_grz_hangar_sync.pyc'
                    if change == 'missing':
                        del package[name]
                    else:
                        package[name] = b'not-python27'
                files[primary] = archive(package)
                with self.assertRaises(ValueError):
                    r.verify(checked_native(self.output, files))

    def test_stale_binary_wrong_client_extra_build_and_reviewed_example_mismatch_fail(self):
        reviewed = self.root / 'reviewed'
        sample = reviewed / 'mods/hangarsync/GRZ_Hangar_Sync.json.example'
        sample.parent.mkdir(parents=True)
        sample.write_bytes(r.read_zip(self.native)[r.HANGAR_CONFIG])
        with patch.object(r, 'ROOT', reviewed):
            with self.assertRaisesRegex(ValueError, 'disagree'):
                r.package(self.source, self.output, 'hangarsync', '2.5.0.0')
            primary = self.source / r.HANGAR_PACKAGE
            before = primary.read_bytes()
            primary.write_bytes(b'stale')
            with self.assertRaisesRegex(ValueError, 'disagree'):
                r.package(self.source, self.output, 'hangarsync')
            primary.write_bytes(before)
            sample.write_bytes(b'{}')
            with self.assertRaisesRegex(ValueError, 'reviewed example'):
                r.package(self.source, self.output, 'hangarsync')
            extra = self.source / 'private.log'
            extra.write_bytes(b'synthetic')
            with self.assertRaisesRegex(ValueError, 'assets'):
                r.package(self.source, self.output, 'hangarsync')

    def test_current_registry_does_not_activate_every_supported_format(self):
        self.assertIn('hangarsync', r.KINDS)
        configured = json.loads((r.ROOT / 'scripts/release_modules.json').read_text())
        self.assertEqual(r.registered_kinds(), {item['id'] for item in configured['modules']})
        registry = self.root / 'registry.json'
        current = [item for item in configured['modules'] if item['id'] != 'hangarsync']
        registry.write_text(json.dumps({'schema_version': 1, 'modules': current}))
        self.assertEqual(r.registered_kinds(registry), {'staysharp', 'sessionstats'})
        with self.assertRaises(ValueError):
            r.verify_directory(self.source)
        for modules in ([], [{'id': 'unknown', 'installer_prefix': 'Unknown-v'}],
                        [{'id': 'hangarsync', 'installer_prefix': 'Wrong-v'}],
                        [{'id': 'hangarsync', 'installer_prefix': 'GRZ_Hangar_Sync-v'}] * 2):
            registry.write_text(json.dumps({'schema_version': 1, 'modules': modules}))
            with self.assertRaises(ValueError):
                r.registered_kinds(registry)

    def three(self):
        native = self.package()
        for kind, version in (('staysharp', '1.8.13'), ('sessionstats', '0.5.0')):
            source = self.root / kind
            build(source, kind, version)
            r.package(source, self.output, kind)
        return native

    def test_three_formats_coexist_and_unchanged_zips_are_carried_byte_for_byte(self):
        self.three()
        reports = r.verify_directory(self.output, expected_kinds=set(r.KINDS))
        self.assertEqual(len(reports), 3)
        original = {path.name: path.read_bytes() for path in self.output.iterdir()}
        r.normalize(self.output)
        self.assertEqual({path.name: path.read_bytes() for path in self.output.glob('*.zip')}, original)
        r.check_manifest(r.directory_files(self.output))

    def test_default_verification_requires_exact_current_registered_set(self):
        self.three()
        configured = r.registered_kinds()
        for path in list(self.output.iterdir()):
            if r.identity(path.name)[0] not in configured:
                path.unlink()
        self.assertEqual({report[0] for report in r.verify_directory(self.output)}, configured)
        next(self.output.iterdir()).unlink()
        with self.assertRaises(ValueError):
            r.verify_directory(self.output)

    def test_three_installers_retarget_without_changing_payload_bytes(self):
        native = self.three()
        original = r.verify(native)
        r.normalize(self.output, '2.5.0.0')
        (self.output / 'SHA256SUMS.txt').unlink()
        reports = r.verify_directory(self.output, expected_kinds=set(r.KINDS))
        self.assertEqual({report[2] for report in reports}, {'2.5.0.0'})
        current = next(report for report in reports if report[0] == 'hangarsync')
        self.assertEqual(original[3][original[4]], current[3][current[4]])
        self.assertEqual(original[3][r.HANGAR_CONFIG], current[3][r.HANGAR_CONFIG])
        self.assertEqual(original[3]['README.md'], current[3]['README.md'])

    def test_three_way_resource_collision_and_missing_or_extra_installer_fail(self):
        native = self.three()
        with patch.object(r, 'registered_kinds', return_value={'staysharp', 'sessionstats'}), self.assertRaises(ValueError):
            r.verify_directory(self.output)
        reports = r.verify_directory(self.output, expected_kinds=set(r.KINDS))
        stats = next(report for report in reports if report[0] == 'sessionstats')
        files = dict(stats[3])
        package = r.read_zip(io.BytesIO(files[stats[4]]))
        package['res/scripts/client/gui/mods/mod_grz_hangar_sync.pyc'] = b'collision'
        files[stats[4]] = archive(package)
        del files['docs/sessionstats/SHA256SUMS.txt']
        r.write_installer(self.output, 'sessionstats', stats[1], stats[2], files)
        with self.assertRaisesRegex(ValueError, 'Conflicting'):
            r.verify_directory(self.output, expected_kinds=set(r.KINDS))
        native.unlink()
        with self.assertRaises(ValueError):
            r.verify_directory(self.output, expected_kinds=set(r.KINDS))


if __name__ == '__main__':
    unittest.main()
