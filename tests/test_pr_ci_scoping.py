"""PR branch changes select only the affected mod's build and download."""
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = {
    'medkit': ROOT / '.github/workflows/ci.yml',
    'sessionstats': ROOT / '.github/workflows/sessionstats-ci.yml',
}


def path_filters(workflow):
    block = workflow.read_text().split('  pull_request:\n', 1)[1]
    block = block.split('    paths:\n', 1)[1]
    result = []
    for line in block.splitlines():
        if not line.startswith('      - '):
            break
        result.append(line.strip()[2:].strip().strip("'\""))
    if not result:
        raise ValueError('PR workflow needs explicit path filters')
    return result


def selected(paths, workflows=WORKFLOWS):
    # These workflows use only positive literal patterns, * and **. Unlike
    # fnmatch, GitHub's single * cannot cross a path separator.
    def matches(path, pattern):
        regex = re.escape(pattern).replace(r'\*\*', '.*').replace(r'\*', '[^/]*')
        return re.fullmatch(regex, path) is not None

    return {name for name, workflow in workflows.items()
            if any(matches(path, pattern) for path in paths
                   for pattern in path_filters(workflow))}


class PrBuildScopingTests(unittest.TestCase):
    def test_medkit_changes_do_not_build_sessionstats(self):
        for path in ('source/mod_staysharp_medkit.py', 'source/build_audio_bank.py',
                     'assets/voices/pl.wav.b85', 'assets/voices/manifest.json',
                     'VERSION', 'staysharp.medkit.example.json', 'CHANGELOG.md',
                     'docs/AUDIO.md', 'tests/test_packaging.py',
                     'tests/test_staysharp_ci_artifact.py', '.github/workflows/ci.yml',
                     '.github/workflows/release.yml'):
            with self.subTest(path=path):
                self.assertEqual(selected([path]), {'medkit'})

    def test_sessionstats_changes_do_not_build_medkit(self):
        for path in ('mods/sessionstats/src/grz_session_stats/storage.py',
                     'mods/sessionstats/ui/app.js', 'mods/sessionstats/VERSION',
                     'mods/sessionstats/config/grz.sessionstats.json',
                     'mods/sessionstats/languages/pl.json',
                     'mods/sessionstats/tools/build.py', 'scripts/sessionstats/python27.sh',
                     'scripts/sessionstats/source_state.py',
                     'tests/test_sessionstats_release_scoping.py',
                     '.github/workflows/sessionstats-ci.yml',
                     '.github/workflows/sessionstats-release.yml'):
            with self.subTest(path=path):
                self.assertEqual(selected([path]), {'sessionstats'})

    def test_mixed_changes_build_both_mods(self):
        self.assertEqual(selected(['assets/voices/pl.wav.b85',
                                   'mods/sessionstats/ui/app.js']), set(WORKFLOWS))

    def test_third_mod_selects_itself_without_changing_existing_filters(self):
        original = {name: path.read_bytes() for name, path in WORKFLOWS.items()}
        with tempfile.TemporaryDirectory() as temporary:
            third = Path(temporary) / 'third-mod-ci.yml'
            third.write_text("on:\n  pull_request:\n    paths:\n"
                             "      - 'mods/example/**'\n"
                             "      - 'scripts/example/**'\n"
                             "      - 'scripts/release_installers.py'\n"
                             "  workflow_dispatch:\n")
            workflows = dict(WORKFLOWS, example=third)
            for changes, expected in (
                (['mods/example/src/main.py'], {'example'}),
                (['source/mod_staysharp_medkit.py'], {'medkit'}),
                (['mods/sessionstats/src/storage.py'], {'sessionstats'}),
                (['mods/example/src/main.py', 'source/build_wotmod.py'],
                 {'example', 'medkit'}),
                (['mods/example/src/main.py', 'mods/sessionstats/src/storage.py'],
                 {'example', 'sessionstats'}),
                (['scripts/release_installers.py'], set(workflows)),
                (['README.md'], set()),
            ):
                with self.subTest(changes=changes):
                    self.assertEqual(selected(changes, workflows), expected)
        self.assertEqual({name: path.read_bytes() for name, path in WORKFLOWS.items()},
                         original)

    def test_shared_inputs_validate_both_mods(self):
        for path in ('scripts/release_installers.py', 'scripts/release_snapshot.sh',
                     'scripts/release_version.py', 'scripts/privacy_audit.py',
                     'tests/test_release_installers.py', 'tests/test_release_pipeline.py',
                     'tests/test_release_snapshot.py', 'tests/test_pr_ci_scoping.py'):
            with self.subTest(path=path):
                self.assertEqual(selected([path]), set(WORKFLOWS))

    def test_unrelated_docs_and_empty_diff_start_no_build(self):
        self.assertEqual(selected([]), set())
        for path in ('README.md', 'docs/MULTIMOD_RELEASES.md', 'docs/BUILD_RELEASE.md',
                     'other-mod/source.py', 'notes/sessionstats-example.md'):
            with self.subTest(path=path):
                self.assertEqual(selected([path]), set())

    def test_sessionstats_infrastructure_checks_do_not_run_medkit_builder_tests(self):
        text = WORKFLOWS['sessionstats'].read_text()
        step = text.split('      - name: Test release infrastructure\n', 1)[1]
        step = step.split('\n      - ', 1)[0]
        for pattern in ('test_sessionstats_*.py', 'test_release_*.py', 'test_pr_ci_scoping.py'):
            self.assertIn("-p '" + pattern + "'", step)
        self.assertNotIn('discover -s tests -v', step)
        self.assertNotIn('build_wotmod.py', text)
        self.assertNotIn('test_packaging.py', step)
        self.assertNotIn('test_staysharp_ci_artifact.py', step)

    def test_manual_runs_and_separate_artifact_paths_remain_available(self):
        for path in WORKFLOWS.values():
            text = path.read_text()
            self.assertIn('  workflow_dispatch:', text)
            self.assertIn('contents: read', text)
            self.assertNotIn('contents: write', text)
        medkit = WORKFLOWS['medkit'].read_text().split('uses: actions/upload-artifact@', 1)[1]
        stats = WORKFLOWS['sessionstats'].read_text().split('uses: actions/upload-artifact@', 1)[1]
        self.assertIn('path: pr-artifact/StaySharp-Medkit-v*.zip', medkit)
        self.assertIn('path: mods/sessionstats/dist/wot-statystyki-sesji-v*.zip', stats)
        self.assertNotIn('sessionstats', medkit)
        self.assertNotIn('StaySharp-Medkit', stats)


class PrBranchDiffTests(unittest.TestCase):
    def test_main_merge_is_ignored_but_earlier_branch_changes_are_retained(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)

            def git(*args):
                return subprocess.check_output(['git', '-C', str(root), *args],
                                               text=True, stderr=subprocess.STDOUT).strip()

            def commit(path, text):
                target = root / path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(text)
                git('add', '.')
                git('commit', '-qm', 'Synthetic change')

            def changes():
                return git('diff', '--name-only', '--no-renames', 'main...HEAD').splitlines()

            git('init', '-q', '-b', 'main')
            git('config', 'user.name', 'Synthetic fixture')
            git('config', 'user.email', 'fixture.invalid')
            commit('README.md', 'Synthetic base\n')
            git('switch', '-qc', 'medkit')
            commit('source/mod_staysharp_medkit.py', '# medkit change\n')
            git('switch', '-q', 'main')
            commit('mods/sessionstats/src/storage.py', '# accepted on main\n')
            git('switch', '-q', 'medkit')
            git('merge', '--no-ff', '-qm', 'Sync main', 'main')
            self.assertEqual(selected(changes()), {'medkit'})

            commit('mods/sessionstats/ui/app.js', '// new change on the PR branch\n')
            self.assertEqual(selected(changes()), set(WORKFLOWS))
            commit('README.md', 'Latest commit changes docs only\n')
            self.assertEqual(selected(changes()), set(WORKFLOWS))

            git('rm', '-q', 'mods/sessionstats/src/storage.py')
            git('commit', '-qm', 'Remove a Session Stats source')
            self.assertIn('mods/sessionstats/src/storage.py', changes())
            self.assertEqual(selected(changes()), set(WORKFLOWS))


if __name__ == '__main__':
    unittest.main()
