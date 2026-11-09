"""Offline security and sequencing contracts for the sole WotMods publisher."""
from pathlib import Path
import re
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = (ROOT / '.github/workflows/wotmods-release.yml').read_text()
BUILDER = (ROOT / 'scripts/build_release_module.sh').read_text()
MEDKIT_CI = (ROOT / '.github/workflows/ci.yml').read_text()
STATS_CI = (ROOT / '.github/workflows/sessionstats-ci.yml').read_text()


def job(name):
    match = re.search(r'(?ms)^  ' + re.escape(name) +
                      r':\n(.*?)(?=^  [a-z0-9_-]+:\n|\Z)', WORKFLOW)
    if not match:
        raise AssertionError('Missing job ' + name)
    return match.group(1)


class SinglePublisherTests(unittest.TestCase):
    def test_previous_per_mod_publishers_are_retired(self):
        self.assertFalse((ROOT / '.github/workflows/release.yml').exists())
        self.assertFalse((ROOT / '.github/workflows/sessionstats-release.yml').exists())
        self.assertEqual(WORKFLOW.count('gh release create "$RELEASE_TAG"'), 2)
        self.assertIn('name: Publish WotMods snapshot', WORKFLOW)

    def test_main_only_and_no_public_release_from_pull_requests(self):
        self.assertIn('  push:\n    branches: [main]', WORKFLOW)
        self.assertNotIn('  pull_request:', WORKFLOW)
        self.assertIn('  workflow_dispatch:', WORKFLOW)
        for pr in (MEDKIT_CI, STATS_CI):
            self.assertIn('  pull_request:', pr)
            self.assertIn('contents: read', pr)
            self.assertNotIn('contents: write', pr)
            self.assertIn('uses: actions/upload-artifact@', pr)
            self.assertNotIn('gh release create', pr)
        self.assertIn('path: pr-artifact/StaySharp-Medkit-v*.zip', MEDKIT_CI)
        self.assertIn('path: pr-artifact-sessionstats/Session-Stats-v*.zip', STATS_CI)

    def test_legacy_publishers_mutex_shared_across_entire_transaction(self):
        before_jobs = WORKFLOW.split('\njobs:', 1)[0]
        self.assertIn('group: wotmod-release-${{ github.repository }}', before_jobs)
        self.assertIn('queue: max', before_jobs)
        self.assertIn('cancel-in-progress: false', before_jobs)
        self.assertNotIn('cancel-in-progress: true', WORKFLOW)
        self.assertNotIn('    concurrency:', job('publish'))

    def test_planning_uses_reviewed_event_commit_and_latest_inside_lock(self):
        planning = job('plan')
        self.assertIn('ref: ${{ github.sha }}', planning)
        self.assertIn('fetch-depth: 0', planning)
        self.assertIn('--previous-tag "$latest" --previous-dir previous', planning)
        self.assertIn('isImmutable', planning)
        self.assertIn('scripts/release_coordinator.py plan', planning)

    def test_matrix_builds_only_plan_selected_modules_with_readonly_token(self):
        build = job('build')
        self.assertIn('fromJSON(needs.plan.outputs.matrix)', build)
        self.assertIn('ref: ${{ needs.plan.outputs.source_sha }}', build)
        self.assertIn('permissions:\n      contents: read', build)
        self.assertIn('bash scripts/build_release_module.sh "$MODULE" "$VERSION"', build)
        self.assertNotIn('contents: write', build)
        self.assertNotIn('gh release create', build)
        # Internal uploads are archived so the explicit artifact name survives;
        # archive:false would ignore name and break the plan-scoped download.
        self.assertNotIn('archive: false', build)
        self.assertIn('if: matrix.mod != \'noop\'', build)

    def test_module_builder_does_not_cross_build_other_module(self):
        medkit, stats = BUILDER.split('  sessionstats)', 1)
        self.assertIn('source/build_wotmod.py', medkit)
        self.assertNotIn('scripts/sessionstats/validate.sh', medkit)
        self.assertIn('scripts/sessionstats/validate.sh', stats)
        self.assertNotIn('source/build_wotmod.py', stats)
        self.assertIn('scripts/privacy_audit.py --scan-dist', medkit)
        self.assertIn('scripts/sessionstats/release.py --verify-directory', stats)

    def test_production_write_token_only_after_green_build(self):
        build = job('build')
        publish = job('publish')
        self.assertIn('needs: [plan, updates, build]', publish)
        self.assertIn('if: needs.plan.outputs.publish == \'true\'', publish)
        self.assertIn('contents: write', publish)
        self.assertIn('environment: wotmods-release', publish)
        self.assertNotIn('GH_TOKEN:', build)
        self.assertIn('pattern: wotmods-installer-*', publish)
        self.assertIn('name: wotmods-plan', publish)
        self.assertIn('overwrite: true', build)

    def test_plan_is_bounded_to_expected_sha_and_latest_is_revalidated(self):
        publish = job('publish')
        self.assertIn('test "$(git rev-parse HEAD)" = "$SOURCE_SHA"', publish)
        self.assertIn('git merge-base --is-ancestor "$SOURCE_SHA" origin/main', publish)
        self.assertIn('[[ "$current" == "$PREVIOUS_TAG" || "$current" == "$RELEASE_TAG" ]]', publish)
        self.assertIn('scripts/release_coordinator.py assemble', publish)
        self.assertLess(publish.index('scripts/release_coordinator.py assemble'),
                        publish.index('gh release create "$RELEASE_TAG"'))

    def test_first_party_actions_pinned_to_full_commit_sha(self):
        for doc in (WORKFLOW, MEDKIT_CI, STATS_CI):
            for value in re.findall(r'uses: (actions/(?:checkout|upload-artifact|download-artifact))@([^\s#]+)', doc):
                self.assertRegex(value[1], r'^[0-9a-f]{40}$')

    def test_verified_native_tag_protection_before_any_write(self):
        publish = job('publish')
        for marker in ('wotmods-release-tags', 'refs/tags/wotmods-v*',
                       'index("creation") == null', 'index("update") != null',
                       'index("deletion") != null', 'bypass_actors',
                       'WOTMODS_REVIEWED_RULESET_UPDATED_AT', 'targets=tag'):
            self.assertIn(marker, publish)
        self.assertLess(publish.index('policy_ids='), publish.index('git push origin'))
        self.assertLess(publish.index('policy_ids='), publish.index('gh release create'))

    def test_no_write_before_checksums_and_tag_pin(self):
        publish = job('publish')
        self.assertLess(publish.index('scripts/release_coordinator.py assemble'),
                        publish.index('git push origin'))
        self.assertIn('git ls-remote --tags origin "refs/tags/$RELEASE_TAG^{}"', publish)
        self.assertIn('check_remote_tag', publish)
        self.assertIn('--verify-tag --latest', publish)
        self.assertIn('--notes-start-tag "$PREVIOUS_TAG"', publish)

    def test_drafts_are_fail_closed_and_existing_published_bytes_verified(self):
        publish = job('publish')
        self.assertIn('draft) echo', publish)
        self.assertIn('published) ;;', publish)
        self.assertIn('gh release download "$RELEASE_TAG"', publish)
        self.assertIn('isImmutable,assets', publish)
        self.assertIn('latest_now=', publish)
        self.assertIn('cmp -- "release/$name" "$remote/$name"', publish)
        self.assertIn('scripts/release_installers.py verify "$remote"', publish)
        self.assertGreaterEqual(publish.count('check_remote_tag'), 3)
        self.assertNotIn('gh release delete', publish)
        self.assertNotIn('gh release upload', publish)
        self.assertNotIn('curl ', publish)
        self.assertNotIn('requests.', publish)

    def test_shell_scripts_and_inline_bash_blocks_parse(self):
        subprocess.check_call(['bash', '-n', str(ROOT/'scripts/build_release_module.sh')])
        # Extract all literal run blocks without adding a YAML runtime dependency.
        for body in re.findall(r'(?m)^        run: \|\n((?:          .*\n|\n)+)', WORKFLOW):
            code = '\n'.join(line[10:] if line.startswith('          ') else ''
                             for line in body.splitlines()) + '\n'
            subprocess.run(['bash', '-n'], input=code, text=True, check=True)


if __name__ == '__main__':
    unittest.main()
