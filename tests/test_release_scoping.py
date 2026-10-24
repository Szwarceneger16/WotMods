"""Architecture regression: Stay Sharp is isolated from other WoT mods."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
RELEASE = (ROOT / '.github/workflows/release.yml').read_text(encoding='utf-8')
CI = (ROOT / '.github/workflows/ci.yml').read_text(encoding='utf-8')


def yaml_paths(document, event):
    """Read literal top-level on.<event>.paths (keeps tests dependency-free)."""
    event_header = '  ' + event + ':\n'
    if event_header not in document:
        return []
    block = document.split(event_header, 1)[1]
    paths = block.split('    paths:\n', 1)[1]
    result = []
    for line in paths.splitlines():
        if not line.startswith('      - '):
            break
        result.append(line.strip()[2:].strip().strip("\"'"))
    return result


class ScopedStaySharpReleaseTests(unittest.TestCase):
    def test_release_trigger_scoped_to_staysharp_and_build_inputs(self):
        paths = yaml_paths(RELEASE, 'push')
        self.assertTrue({'source/**', 'assets/**', 'VERSION'}.issubset(paths))
        self.assertIn('scripts/release_snapshot.sh', paths)
        self.assertFalse(any('sessionstats' in p or p == 'mods/**' or p == 'tests/**' for p in paths))
        self.assertNotIn('README.md', paths)
        self.assertNotIn('docs/**', paths)
        self.assertTrue('workflow_dispatch:' in RELEASE)

    def test_pr_ci_skips_other_mods_but_tests_own_builder(self):
        paths = yaml_paths(CI, 'pull_request')
        self.assertIn('source/**', paths)
        self.assertIn('tests/test_packaging.py', paths)
        self.assertIn('.github/workflows/ci.yml', paths)
        self.assertFalse(any('mods/**' in p or 'sessionstats' in p for p in paths))

    def test_carried_assets_never_rebuilt_in_own_release(self):
        self.assertIn('bash scripts/release_snapshot.sh release', RELEASE)
        self.assertIn('com.staysharp.medkitreminder_${RELEASE_VERSION}.wotmod', RELEASE)
        self.assertIn('StaySharp-Medkit-v*.zip', RELEASE)
        self.assertNotIn('mods/sessionstats/tools/build.py', RELEASE)
        self.assertNotIn('scripts/sessionstats/validate.sh', RELEASE)
        self.assertLess(RELEASE.index('bash scripts/release_snapshot.sh release'),
                        RELEASE.index('gh release create'))

    def test_all_current_snapshot_assets_are_uploaded(self):
        self.assertIn('gh release create "$tag" release/*.zip', RELEASE)
        self.assertIn('--latest', RELEASE)
        self.assertIn('gh release download "$tag" --repo "$GITHUB_REPOSITORY" --dir "$remote"', RELEASE)
        self.assertIn('cmp -- "release/$name" "$remote/$name"', RELEASE)

    def test_shared_lock_serializes_only_publish_jobs_and_queues_every_merge(self):
        # Builds for different mods are independent and can run in parallel.
        before_publish, publish = RELEASE.split('\n  publish:', 1)
        self.assertNotIn('group: wotmod-release-', before_publish)
        self.assertIn('    concurrency:', publish)
        self.assertIn('group: wotmod-release-${{ github.repository }}', publish)
        self.assertIn('queue: max', publish)
        self.assertIn('cancel-in-progress: false', publish)
        self.assertLess(publish.index('concurrency:'), publish.index('bash scripts/release_snapshot.sh'))
        self.assertLess(publish.index('bash scripts/release_snapshot.sh'), publish.index('gh release create'))

    def test_stale_build_is_skipped_before_any_tag_or_release_creation(self):
        _, publish = RELEASE.split('\n  publish:', 1)
        self.assertIn('id: snapshot', publish)
        self.assertIn("if: steps.snapshot.outputs.publish == 'true'", publish)
        self.assertIn('if [[ "$status" == 75 ]]', publish)
        self.assertIn('publish=false', publish)
        self.assertLess(publish.index('if [[ "$status" == 75 ]]'), publish.index('gh release create'))



if __name__ == '__main__':
    unittest.main()
