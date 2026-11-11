"""Release orchestration: path scoping, merge races and immutable carry-forward."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))

import release_coordinator as coordinator
import release_installers as installers
from test_release_installers import build
from test_hangar_release_installers import build_hangar


SHA = 'a' * 40
PREVIOUS = {'staysharp': '1.8.22', 'sessionstats': '0.3.15'}


def two_module_registry():
    """Keep historical fixtures explicit after the production set grows."""
    configured = json.loads(json.dumps(coordinator.registry()))
    configured['modules'] = [entry for entry in configured['modules']
                             if entry['id'] in PREVIOUS]
    return configured


class PlanTests(unittest.TestCase):
    def setUp(self):
        self.registry = two_module_registry()

    def make(self, paths, previous=PREVIOUS, tag='sessionstats-v0.3.15',
             client=installers.CLIENT, previous_client=installers.CLIENT):
        return coordinator.make_plan(self.registry, paths, previous, tag,
                                     SHA, 312, client, previous_client)

    def test_mod_specific_changes_build_only_the_selected_mod(self):
        medkit = self.make(['source/mod_staysharp_medkit.py'])
        self.assertEqual(medkit['changed'], ['staysharp'])
        self.assertEqual(medkit['versions'], {'staysharp': '1.8.23',
                                              'sessionstats': '0.3.15'})
        stats = self.make(['mods/sessionstats/src/main.py'])
        self.assertEqual(stats['changed'], ['sessionstats'])
        self.assertEqual(stats['versions'], {'staysharp': '1.8.22',
                                              'sessionstats': '0.3.16'})

    def test_both_mods_changed_get_one_global_release_tag(self):
        result = self.make(['source/mod_staysharp_medkit.py',
                            'mods/sessionstats/src/main.py'])
        self.assertEqual(result['changed'], ['staysharp', 'sessionstats'])
        self.assertEqual(result['release_tag'], 'wotmods-v1.0.312')
        self.assertEqual(len(result['matrix']), 2)

    def test_shared_build_inputs_select_all_without_pairwise_conditions(self):
        self.assertEqual(self.make(['scripts/release_installers.py'])['changed'],
                         ['staysharp', 'sessionstats'])
        self.assertEqual(self.make(['scripts/build_release_module.sh'])['changed'],
                         ['staysharp', 'sessionstats'])

    def test_medkit_installer_docs_change_only_medkit(self):
        self.assertEqual(self.make(['docs/INSTALACJA.md'])['changed'], ['staysharp'])

    def test_unchanged_state_does_not_create_a_new_release(self):
        result = self.make([], tag='wotmods-v1.0.300')
        self.assertFalse(result['publish'])
        self.assertEqual(result['release_tag'], 'wotmods-v1.0.301')
        self.assertEqual(result['changed'], [])
        self.assertEqual(result['matrix'], [{'mod': 'noop', 'version': '0.0.0'}])

    def test_legacy_migration_and_client_retarget_need_no_rebuild(self):
        migration = self.make([])
        self.assertTrue(migration['publish'])
        self.assertEqual(migration['changed'], [])
        updated = self.make([], tag='wotmods-v1.0.300', client='2.5.0.0')
        self.assertTrue(updated['publish'])
        self.assertEqual(updated['changed'], [])
        self.assertEqual(updated['release_tag'], 'wotmods-v1.0.301')

    def test_multiple_client_updates_on_one_source_sha_get_distinct_tags(self):
        first = self.make([], tag='wotmods-v1.0.300', client='2.5.0.0')
        second = self.make([], tag=first['release_tag'], client='2.6.0.0',
                           previous_client='2.5.0.0')
        self.assertTrue(first['publish'] and second['publish'])
        self.assertEqual((first['release_tag'], second['release_tag']),
                         ('wotmods-v1.0.301', 'wotmods-v1.0.302'))
        self.assertEqual((first['source_sha'], second['source_sha']), (SHA, SHA))
        self.assertEqual(first['changed'], second['changed'])

    def test_global_release_number_is_independent_of_commit_count(self):
        result = coordinator.make_plan(self.registry, ['source/mod_staysharp_medkit.py'],
                                       PREVIOUS, 'wotmods-v1.0.300', SHA, 900,
                                       installers.CLIENT, installers.CLIENT)
        self.assertEqual(result['release_tag'], 'wotmods-v1.0.301')

    def test_unknown_latest_tag_fails_instead_of_silent_migration(self):
        with self.assertRaisesRegex(ValueError, 'Unrecognized'):
            self.make([], tag='some-other-v9.0.0')

    def test_cross_module_rename_rebuilds_both_source_and_destination(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)

            def git(*args):
                return subprocess.check_output(['git', '-C', str(root), *args]).decode().strip()

            git('init', '-q')
            git('config', 'user.name', 'Synthetic fixture')
            git('config', 'user.email', 'fixture.invalid')
            original = root / 'assets/VOICE_NOTICE.txt'
            original.parent.mkdir()
            original.write_text('A packaged Medkit asset\n')
            git('add', '.')
            git('commit', '-qm', 'Base')
            moved = root / 'mods/sessionstats/docs/VOICE_NOTICE.txt'
            moved.parent.mkdir(parents=True)
            git('mv', 'assets/VOICE_NOTICE.txt', 'mods/sessionstats/docs/VOICE_NOTICE.txt')
            git('commit', '-qm', 'Cross-module rename')
            changes = git('diff', '--no-renames', '--name-only', 'HEAD~1', 'HEAD').splitlines()
            self.assertEqual(set(changes), {'assets/VOICE_NOTICE.txt',
                                            'mods/sessionstats/docs/VOICE_NOTICE.txt'})
            self.assertEqual(coordinator.selected_modules(changes, self.registry),
                             ['staysharp', 'sessionstats'])

    def test_rapid_merges_preserve_both_updates_in_either_order(self):
        first = self.make(['source/mod_staysharp_medkit.py'])
        second = self.make(['mods/sessionstats/src/main.py'], previous=first['versions'],
                           tag=first['release_tag'])
        self.assertEqual(second['versions'], {'staysharp': '1.8.23',
                                               'sessionstats': '0.3.16'})
        first = self.make(['mods/sessionstats/src/main.py'])
        second = self.make(['source/mod_staysharp_medkit.py'], previous=first['versions'],
                           tag=first['release_tag'])
        self.assertEqual(second['versions'], {'staysharp': '1.8.23',
                                               'sessionstats': '0.3.16'})

    def test_coalesced_merges_build_both_before_publication(self):
        result = self.make(['source/voice.py', 'mods/sessionstats/ui/panel.js'])
        self.assertEqual({m['mod'] for m in result['matrix']},
                         {'staysharp', 'sessionstats'})

    def test_unregistered_module_changes_fail_closed(self):
        with self.assertRaisesRegex(ValueError, 'Unregistered mod'):
            self.make(['mods/thirdmod/source.py'])

    def test_version_rollback_is_blocked_and_explicit_version_jump_allowed(self):
        self.assertEqual(coordinator.next_version('1.8.12', '1.8.22'), '1.8.23')
        self.assertEqual(coordinator.next_version('0.5.0', '0.3.15'), '0.5.0')
        self.assertEqual(coordinator.next_version('0.3.4', None), '0.3.4')
        with self.assertRaises(ValueError):
            coordinator.next_version('1.8.x', '1.8.22')

    def test_new_module_requires_registered_safe_verifier(self):
        rogue = json.loads(json.dumps(self.registry))
        rogue['modules'].append({'id': 'thirdmod', 'display_name': 'Third',
                                'base_version_file': 'VERSION',
                                'installer_prefix': 'Third-v',
                                'source_paths': ['mods/thirdmod/**']})
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'modules.json'
            path.write_text(json.dumps(rogue))
            with self.assertRaisesRegex(ValueError, 'not registered'):
                coordinator.registry(path)

    def test_supported_hangar_format_does_not_register_or_build_absent_source(self):
        self.assertIn('hangarsync', installers.KINDS)
        self.assertEqual({entry['id'] for entry in self.registry['modules']}, set(PREVIOUS))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'modules.json'
            path.write_text(json.dumps(self.registry))
            self.assertEqual(coordinator.registry(path), self.registry)
        with self.assertRaisesRegex(ValueError, 'Unregistered mod'):
            self.make(['mods/hangarsync/source/mod_grz_hangar_sync.py'])

    def test_new_third_module_is_built_while_two_prior_zips_are_carried(self):
        extended = json.loads(json.dumps(self.registry))
        extended['modules'].append({'id': 'thirdmod', 'display_name': 'Third',
                                    'base_version_file': 'VERSION',
                                    'installer_prefix': 'Third-v',
                                    'source_paths': ['mods/thirdmod/**']})
        result = coordinator.make_plan(extended, ['mods/thirdmod/src/main.py'],
                                       PREVIOUS, 'wotmods-v1.0.300', SHA, 312,
                                       installers.CLIENT, installers.CLIENT)
        self.assertEqual(result['previous_modules'], ['sessionstats', 'staysharp'])
        self.assertEqual(result['changed'], ['thirdmod'])
        self.assertEqual([entry['mod'] for entry in result['matrix']], ['thirdmod'])
        self.assertEqual(result['versions']['staysharp'], PREVIOUS['staysharp'])
        self.assertEqual(result['versions']['sessionstats'], PREVIOUS['sessionstats'])

    def test_previous_registry_is_resolved_from_the_tagged_revision(self):
        self.assertEqual(coordinator.previous_module_ids('sessionstats-v0.3.15'),
                         {'staysharp', 'sessionstats'})
        payload = json.dumps({'schema_version': 1,
                              'modules': [{'id': 'staysharp'}]}).encode()
        with patch.object(coordinator.subprocess, 'check_output', return_value=payload) as git:
            self.assertEqual(coordinator.previous_module_ids('wotmods-v1.0.300'),
                             {'staysharp'})
        self.assertIn('wotmods-v1.0.300:scripts/release_modules.json', git.call_args.args[0])

    def test_late_older_merge_skips_when_a_descendant_is_latest(self):
        with tempfile.TemporaryDirectory() as directory:
            prior = Path(directory)
            target = prior / 'plan.json'
            mock_reports = [(kind, version, installers.CLIENT, {}, '')
                            for kind, version in PREVIOUS.items()]
            args = SimpleNamespace(previous_tag='wotmods-v1.0.313', previous_dir=prior,
                                   head='HEAD', client_version=installers.CLIENT, output=target)
            with patch.object(coordinator, 'run_git', side_effect=[SHA, '312', 'b' * 40]), \
                 patch.object(coordinator, 'previous_module_ids', return_value=set(PREVIOUS)), \
                 patch.object(coordinator, 'verify_directory', return_value=mock_reports), \
                 patch.object(coordinator.subprocess, 'run',
                              return_value=SimpleNamespace(returncode=0)), \
                 patch.object(coordinator.subprocess, 'check_call') as guard:
                coordinator.plan(args)
            result = json.loads(target.read_text())
            self.assertFalse(result['publish'])
            self.assertEqual(result['changed'], [])
            guard.assert_not_called()

    def test_diverged_history_fails_instead_of_publishing_stale_assets(self):
        with tempfile.TemporaryDirectory() as directory:
            prior = Path(directory)
            mock_reports = [(kind, version, installers.CLIENT, {}, '')
                            for kind, version in PREVIOUS.items()]
            args = SimpleNamespace(previous_tag='wotmods-v1.0.313', previous_dir=prior,
                                   head='HEAD', client_version=installers.CLIENT,
                                   output=prior/'plan.json')
            with patch.object(coordinator, 'run_git', side_effect=[SHA, '312', 'b' * 40]), \
                 patch.object(coordinator, 'previous_module_ids', return_value=set(PREVIOUS)), \
                 patch.object(coordinator, 'verify_directory', return_value=mock_reports), \
                 patch.object(coordinator.subprocess, 'run',
                              return_value=SimpleNamespace(returncode=1)), \
                 patch.object(coordinator.subprocess, 'check_call',
                              side_effect=ValueError('Not an ancestor')):
                with self.assertRaisesRegex(ValueError, 'Not an ancestor'):
                    coordinator.plan(args)
            self.assertFalse(args.output.exists())


class AssemblyTests(unittest.TestCase):
    def setUp(self):
        configured = two_module_registry()
        for scoped_patch in (
            patch.object(coordinator, 'registry', return_value=configured),
            patch.object(installers, 'registered_kinds', return_value=set(PREVIOUS)),
        ):
            scoped_patch.start()
            self.addCleanup(scoped_patch.stop)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.previous = self.root / 'previous'
        self.previous.mkdir()
        for kind, version in PREVIOUS.items():
            src = self.root / ('src-' + kind)
            build(src, kind, version)
            installers.package(src, self.previous, kind)
        installers.verify_directory(self.previous)
        self.built = self.root / 'built'
        self.built.mkdir()
        self.out = self.root / 'release'
        self.notes = self.root / 'notes.md'
        self.planned = self.root / 'plan.json'

    def assemble(self, paths, tag='sessionstats-v0.3.15', client=installers.CLIENT):
        result = coordinator.make_plan(coordinator.registry(), paths, PREVIOUS,
                                       tag, SHA, 312, client, installers.CLIENT)
        self.planned.write_text(json.dumps(result))
        args = SimpleNamespace(plan=self.planned, previous_dir=self.previous,
                               built_dir=self.built, output=self.out, notes=self.notes,
                               repository='Szwarceneger16/WotMods')
        coordinator.assemble(args)
        return result

    def test_single_mod_build_preserves_other_zip_byte_for_byte(self):
        src = self.root / 'newstats'
        build(src, 'sessionstats', '0.3.16')
        installers.package(src, self.built, 'sessionstats')
        original = (self.previous / 'StaySharp-Medkit-v1.8.22.zip').read_bytes()
        self.assemble(['mods/sessionstats/src/main.py'])
        self.assertEqual((self.out / 'StaySharp-Medkit-v1.8.22.zip').read_bytes(), original)
        self.assertEqual({x[1] for x in installers.verify_directory(self.out)},
                         {'0.3.16', '1.8.22'})

    def test_migration_preserves_both_zips_without_new_builds(self):
        before = {x.name: x.read_bytes() for x in self.previous.iterdir()}
        self.assemble([])
        self.assertEqual({x.name: x.read_bytes() for x in self.out.iterdir()}, before)
        self.assertIn('## Downloads', self.notes.read_text())

    def test_no_build_artifact_directory_is_valid_for_carry_forward(self):
        self.built.rmdir()
        self.assemble([])
        self.assertTrue((self.out / 'StaySharp-Medkit-v1.8.22.zip').exists())
        self.assertTrue((self.out / 'Session-Stats-v0.3.15.zip').exists())
        self.assertIn('## Downloads', self.notes.read_text())

    def test_new_client_retargets_binaries_without_recompiling(self):
        prior = {kind: {name.split('/', 2)[2]: data for name, data in files.items()
                        if name.startswith('mods/' + client + '/')}
                 for kind, _, client, files, _ in installers.verify_directory(self.previous)}
        self.assemble([], tag='wotmods-v1.0.300', client='2.5.0.0')
        for kind, _, client, files, _ in installers.verify_directory(self.out):
            current = {name.split('/', 2)[2]: data for name, data in files.items()
                       if name.startswith('mods/' + client + '/')}
            self.assertEqual(current, prior[kind])

    def test_corrupt_or_extra_artifacts_fail_closed(self):
        (self.built / 'unexpected.zip').write_bytes(b'bad')
        with self.assertRaisesRegex(ValueError, 'mismatch'):
            self.assemble(['source/mod_staysharp_medkit.py'])

    def test_modified_previous_zip_is_never_carried_without_verification(self):
        (self.previous / 'Session-Stats-v0.3.15.zip').write_bytes(b'corrupted')
        with self.assertRaises(Exception):
            self.assemble([])
        self.assertFalse(self.notes.exists())

    def test_history_subset_is_verifiable_without_weakening_final_snapshots(self):
        with tempfile.TemporaryDirectory() as directory:
            only_old = Path(directory)
            shutil.copy2(self.previous / 'StaySharp-Medkit-v1.8.22.zip', only_old)
            reports = installers.verify_directory(only_old, expected_kinds={'staysharp'})
            self.assertEqual([report[0] for report in reports], ['staysharp'])
            with self.assertRaises(ValueError):
                installers.verify_directory(only_old)


class HangarMigrationTests(unittest.TestCase):
    """Exercise a real third installer while old Releases retain their own set."""
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.config = two_module_registry()
        self.config['modules'].append({
            'id': 'hangarsync', 'display_name': 'Hangar Sync',
            'base_version_file': 'mods/hangarsync/VERSION',
            'installer_prefix': 'GRZ_Hangar_Sync-v',
            'source_paths': ['mods/hangarsync/**', 'scripts/hangarsync/**',
                             'scripts/sessionstats/python27.sh'],
        })
        self.current = dict(PREVIOUS, hangarsync='0.14.0')
        for entry in self.config['modules']:
            path = self.root / entry['base_version_file']
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(self.current[entry['id']] + '\n')
        registry_path = self.root / 'scripts/release_modules.json'
        registry_path.parent.mkdir(parents=True, exist_ok=True)
        registry_path.write_text(json.dumps(self.config))
        self.previous = self.root / 'previous'
        self.previous.mkdir()
        for kind, version in PREVIOUS.items():
            source = self.root / ('source-' + kind)
            build(source, kind, version)
            installers.package(source, self.previous, kind)
        installers.verify_directory(self.previous, expected_kinds=set(PREVIOUS))
        self.built = self.root / 'built'
        self.built.mkdir()
        self.output_count = 0
        for scoped_patch in (
            patch.object(coordinator, 'ROOT', self.root),
            patch.object(coordinator, 'registry', return_value=self.config),
            patch.object(installers, 'registered_kinds', return_value=set(self.current)),
        ):
            scoped_patch.start()
            self.addCleanup(scoped_patch.stop)

    def plan(self, paths, previous=None, client=installers.CLIENT):
        return coordinator.make_plan(
            self.config, paths, PREVIOUS if previous is None else previous,
            'wotmods-v1.0.300', SHA, 312, client, installers.CLIENT)

    def hangar(self, directory, version='0.14.0', client=installers.CLIENT):
        source = self.root / ('native-hangar-' + str(self.output_count) + '-' + version)
        candidate = build_hangar(source, version=version, client=client)
        target = directory / candidate.name
        shutil.copy2(candidate, target)
        return target

    def assemble(self, result, previous=None, built=None):
        self.output_count += 1
        output = self.root / ('release-' + str(self.output_count))
        planned = self.root / ('plan-' + str(self.output_count) + '.json')
        notes = self.root / ('notes-' + str(self.output_count) + '.md')
        planned.write_text(json.dumps(result))
        coordinator.assemble(SimpleNamespace(
            plan=planned, previous_dir=self.previous if previous is None else previous,
            built_dir=self.built if built is None else built, output=output,
            notes=notes, repository='example/fixture'))
        return output, notes

    def introduction(self):
        self.hangar(self.built)
        return self.assemble(self.plan([]))[0]

    def test_first_introduction_builds_only_hangar_and_preserves_previous_zips(self):
        before = {path.name: path.read_bytes() for path in self.previous.iterdir()}
        candidate = self.hangar(self.built)
        native_bytes = candidate.read_bytes()
        result = self.plan(['mods/hangarsync/source/mod_grz_hangar_sync.py'])
        self.assertEqual(result['changed'], ['hangarsync'])
        self.assertEqual(result['previous_modules'], sorted(PREVIOUS))
        self.assertEqual(result['versions'], self.current)
        output, notes = self.assemble(result)
        for name, data in before.items():
            self.assertEqual((output / name).read_bytes(), data)
        self.assertEqual((output / candidate.name).read_bytes(), native_bytes)
        self.assertEqual({report[0] for report in installers.verify_directory(output)}, set(self.current))
        self.assertIn('Hangar Sync', notes.read_text())
        self.assertIn('requires a validated local configuration', notes.read_text())
        self.assertIn(installers.digest(native_bytes), notes.read_text())

    def test_newly_registered_hangar_is_required_even_without_matching_diff(self):
        result = self.plan([])
        self.assertTrue(result['publish'])
        self.assertEqual(result['changed'], ['hangarsync'])
        self.assertEqual(result['matrix'], [{'mod': 'hangarsync', 'version': '0.14.0'}])
        with self.assertRaisesRegex(ValueError, 'Build artifacts mismatch'):
            self.assemble(result)

    def test_hangar_only_update_carries_both_other_installers(self):
        previous = self.introduction()
        before = {path.name: path.read_bytes() for path in previous.iterdir()
                  if not path.name.startswith('GRZ_Hangar_Sync-v')}
        for path in self.built.iterdir():
            path.unlink()
        self.hangar(self.built, version='0.14.1')
        result = self.plan(['scripts/hangarsync/privacy.py'], previous=self.current)
        self.assertEqual(result['changed'], ['hangarsync'])
        self.assertEqual(result['versions'], dict(self.current, hangarsync='0.14.1'))
        output, _ = self.assemble(result, previous=previous)
        for name, data in before.items():
            self.assertEqual((output / name).read_bytes(), data)

    def test_stats_only_update_carries_the_hangar_native_zip_unchanged(self):
        previous = self.introduction()
        original = (previous / 'GRZ_Hangar_Sync-v0.14.0.zip').read_bytes()
        for path in self.built.iterdir():
            path.unlink()
        source = self.root / 'updated-stats'
        build(source, 'sessionstats', '0.3.16')
        installers.package(source, self.built, 'sessionstats')
        result = self.plan(['mods/sessionstats/src/main.py'], previous=self.current)
        self.assertEqual(result['changed'], ['sessionstats'])
        output, _ = self.assemble(result, previous=previous)
        self.assertEqual((output / 'GRZ_Hangar_Sync-v0.14.0.zip').read_bytes(), original)

    def test_client_retarget_moves_all_three_installers_without_rebuilding_binaries(self):
        previous = self.introduction()
        binaries = {kind: {name.split('/', 2)[2]: data for name, data in files.items()
                          if name.startswith('mods/' + client + '/')}
                    for kind, _, client, files, _ in installers.verify_directory(previous)}
        for path in self.built.iterdir():
            path.unlink()
        self.built.rmdir()
        result = self.plan([], previous=self.current, client='2.5.0.0')
        self.assertEqual(result['changed'], [])
        self.assertTrue(result['publish'])
        output, _ = self.assemble(result, previous=previous)
        for kind, _, client, files, _ in installers.verify_directory(output):
            self.assertEqual(client, '2.5.0.0')
            self.assertEqual({name.split('/', 2)[2]: data for name, data in files.items()
                              if name.startswith('mods/' + client + '/')}, binaries[kind])

    def test_missing_old_installer_cannot_be_excused_as_a_new_module_migration(self):
        self.hangar(self.built)
        (self.previous / 'Session-Stats-v0.3.15.zip').unlink()
        with self.assertRaisesRegex(ValueError, 'exactly'):
            self.assemble(self.plan([]))

    def test_extra_built_installer_cannot_be_published_with_hangar_only_update(self):
        previous = self.introduction()
        for path in self.built.iterdir():
            path.unlink()
        self.hangar(self.built, version='0.14.1')
        shutil.copy2(previous / 'Session-Stats-v0.3.15.zip', self.built)
        with self.assertRaisesRegex(ValueError, 'Build artifacts mismatch'):
            self.assemble(self.plan(['mods/hangarsync/source/feature.py'], previous=self.current),
                          previous=previous)

    def test_hangar_and_stats_rapid_merges_preserve_independent_versions(self):
        first = self.plan(['mods/hangarsync/source/feature.py'], previous=self.current)
        second = self.plan(['mods/sessionstats/src/feature.py'], previous=first['versions'])
        reverse_first = self.plan(['mods/sessionstats/src/feature.py'], previous=self.current)
        reverse_second = self.plan(['mods/hangarsync/source/feature.py'], previous=reverse_first['versions'])
        expected = dict(self.current, hangarsync='0.14.1', sessionstats='0.3.16')
        self.assertEqual(second['versions'], expected)
        self.assertEqual(reverse_second['versions'], expected)
        compiler = self.plan(['scripts/sessionstats/python27.sh'], previous=self.current)
        self.assertEqual(compiler['changed'], ['sessionstats', 'hangarsync'])

    def test_removed_registered_hangar_is_rejected_after_it_has_been_published(self):
        old_registry = dict(self.config, modules=self.config['modules'][:2])
        with self.assertRaisesRegex(ValueError, 'removed or unknown'):
            coordinator.make_plan(old_registry, [], self.current, 'wotmods-v1.0.300',
                                  SHA, 312, installers.CLIENT, installers.CLIENT)


if __name__ == '__main__':
    unittest.main()
