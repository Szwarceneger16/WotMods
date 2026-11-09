"""Release orchestration: path scoping, merge races and immutable carry-forward."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))

import release_coordinator as coordinator
import release_installers as installers
from test_release_installers import build


SHA = 'a' * 40
PREVIOUS = {'staysharp': '1.8.22', 'sessionstats': '0.3.15'}


class PlanTests(unittest.TestCase):
    def setUp(self):
        self.registry = coordinator.registry()

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

    def test_unchanged_state_does_not_create_a_new_release(self):
        result = self.make([], tag='wotmods-v1.0.300')
        self.assertFalse(result['publish'])
        self.assertEqual(result['changed'], [])
        self.assertEqual(result['matrix'], [{'mod': 'noop', 'version': '0.0.0'}])

    def test_legacy_migration_and_client_retarget_need_no_rebuild(self):
        migration = self.make([])
        self.assertTrue(migration['publish'])
        self.assertEqual(migration['changed'], [])
        updated = self.make([], tag='wotmods-v1.0.300', client='2.5.0.0')
        self.assertTrue(updated['publish'])
        self.assertEqual(updated['changed'], [])

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


class AssemblyTests(unittest.TestCase):
    def setUp(self):
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


if __name__ == '__main__':
    unittest.main()
