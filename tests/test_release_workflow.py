"""Offline guardrails for the simple, GitHub-native release workflow.

These checks prevent accidental re-introduction of custom release APIs,
destructive recovery scripts or unsafe token use. Actual publication is
integration-tested only after a reviewed merge to the main branch.
"""
from pathlib import Path
import json
import re
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = (ROOT / '.github/workflows/release.yml').read_text(encoding='utf-8')


class GitHubNativeReleaseTests(unittest.TestCase):
    def test_no_custom_publisher_or_deletion_workflow(self):
        self.assertFalse((ROOT / 'scripts/publish_release.py').exists())
        self.assertFalse((ROOT / 'scripts/publish_release.sh').exists())
        self.assertFalse((ROOT / '.github/workflows/recover.yml').exists())
        self.assertFalse((ROOT / 'tests/test_release_publication.py').exists())

    def test_readonly_build_separate_from_write_enabled_publisher(self):
        self.assertIn('contents: read', WORKFLOW)
        self.assertIn('contents: write', WORKFLOW)
        self.assertLess(WORKFLOW.index('contents: read'), WORKFLOW.index('contents: write'))
        self.assertIn('needs: [build, updates]', WORKFLOW)
        self.assertIn("if: github.ref == 'refs/heads/main'", WORKFLOW)

    def test_first_party_actions_pinned_to_full_commit_sha(self):
        action_lines = re.findall(r'^\s*uses:\s*(actions/[^\s]+)', WORKFLOW, re.MULTILINE)
        self.assertGreaterEqual(len(action_lines), 3)
        for action in action_lines:
            self.assertRegex(action, r'^actions/(?:checkout|upload-artifact|download-artifact)@[0-9a-f]{40}$')

    def test_staysharp_namespace_keeps_repository_wide_publication_lock(self):
        self.assertIn('tag=staysharp-v%s', WORKFLOW)
        self.assertNotIn('tag=v%s', WORKFLOW)
        self.assertIn('name: Release Stay Sharp', WORKFLOW)
        self.assertNotIn('wotmod-release-tags', WORKFLOW)
        self.assertNotIn('WOTMOD_REVIEWED_RULESET', WORKFLOW)
        self.assertIn('group: wotmod-release-${{ github.repository }}', WORKFLOW)
        self.assertIn('queue: max', WORKFLOW)
        self.assertIn('cancel-in-progress: false', WORKFLOW)

    def test_remote_tag_bound_to_exact_workflow_commit_before_release(self):
        self.assertLess(WORKFLOW.index('git push origin'), WORKFLOW.index('gh release create'))
        self.assertIn('test "$resolved" = "$GITHUB_SHA"', WORKFLOW)
        self.assertIn('--verify-tag', WORKFLOW)
        self.assertIn('git rev-parse', WORKFLOW)

    def test_no_http_api_or_destructive_release_mutation(self):
        # Official gh api is used *read-only* to validate native tag rules.
        # No custom HTTP client or GitHub API writes are permitted.
        self.assertIn('gh api -X GET', WORKFLOW)
        self.assertNotIn('gh api --method', WORKFLOW)
        self.assertNotIn('gh api -X POST', WORKFLOW)
        self.assertNotIn('gh api -X PATCH', WORKFLOW)
        self.assertNotIn('gh api -X DELETE', WORKFLOW)
        self.assertNotIn('gh release delete', WORKFLOW)
        self.assertNotIn('gh release upload', WORKFLOW)
        self.assertNotIn('--clobber', WORKFLOW)
        self.assertNotIn('--latest=false', WORKFLOW)
        self.assertIn('gh release create', WORKFLOW)

    def test_protection_rules_checked_before_tag_or_release_creation(self):
        self.assertIn('staysharp-release-tags', WORKFLOW)
        self.assertIn('refs/tags/staysharp-v*', WORKFLOW)
        self.assertIn('environment: staysharp-release', WORKFLOW)
        self.assertIn('STAYSHARP_REVIEWED_RULESET_ID: ${{ vars.STAYSHARP_REVIEWED_RULESET_ID }}', WORKFLOW)
        self.assertIn('STAYSHARP_REVIEWED_RULESET_UPDATED_AT: ${{ vars.STAYSHARP_REVIEWED_RULESET_UPDATED_AT }}', WORKFLOW)
        self.assertLess(WORKFLOW.index('policy_ids='), WORKFLOW.index('git push origin'))
        self.assertLess(WORKFLOW.index('policy_ids='), WORKFLOW.index('gh release create'))
        self.assertIn('if has("bypass_actors") then', WORKFLOW)
        self.assertNotIn('(.bypass_actors // []) == []', WORKFLOW)
        self.assertIn('.updated_at == $approved_at', WORKFLOW)
        self.assertIn('index("update")', WORKFLOW)
        self.assertIn('index("deletion")', WORKFLOW)

    def test_ruleset_discovery_uses_server_tag_filter_not_hidden_summary_target(self):
        start = WORKFLOW.index('policy_ids="$(gh api')
        end = WORKFLOW.index('          if [[ ! "$policy_ids"', start)
        listing = WORKFLOW[start:end]
        self.assertIn('targets=tag', listing)
        self.assertIn('includes_parents=true', listing)
        self.assertIn('gh api --paginate -X GET', listing)
        self.assertNotIn('.target == "tag"', listing)
        expr = listing.split("--jq '", 1)[1].split("'", 1)[0]
        summary = [
            {'id': 42, 'name': 'staysharp-release-tags', 'enforcement': 'active'},
            {'id': 91, 'name': 'another-tag-ruleset', 'enforcement': 'active'},
            {'id': 33, 'name': 'staysharp-release-tags', 'enforcement': 'disabled'},
        ]  # The GitHub list-rulesets endpoint does not provide .target.
        result = subprocess.run(['jq', '-r', expr], input=json.dumps(summary),
                                text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), '42')

    def test_ruleset_policy_requires_visible_empty_bypass_or_owner_reviewed_revision(self):
        # Execute the exact jq predicate deployed by GitHub Actions.
        marker = '--arg approved_at "${STAYSHARP_REVIEWED_RULESET_UPDATED_AT:-}" ' + "'\n"
        self.assertIn(marker, WORKFLOW)
        predicate = WORKFLOW.split(marker, 1)[1].split("\n          ' >/dev/null", 1)[0]
        baseline = {
            'id': 42, 'updated_at': '2026-10-22T09:15:00Z',
            'name': 'staysharp-release-tags', 'target': 'tag', 'enforcement': 'active',
            'conditions': {'ref_name': {'include': ['refs/tags/staysharp-v*'], 'exclude': []}},
            'bypass_actors': [], 'rules': [{'type': 'update'}, {'type': 'deletion'}]
        }

        def accepted(value, approved_id='', approved_at=''):
            proc = subprocess.run(['jq', '-e', '--arg', 'id', '42',
                                   '--arg', 'approved_id', approved_id,
                                   '--arg', 'approved_at', approved_at, predicate],
                                  input=json.dumps(value), text=True, capture_output=True)
            self.assertIn(proc.returncode, (0, 1), proc.stderr)
            return proc.returncode == 0

        self.assertTrue(accepted(baseline))
        for changes in (
            {'id': 43}, {'target': 'branch'}, {'enforcement': 'disabled'},
            {'conditions': {'ref_name': {'include': ['refs/tags/v*'], 'exclude': []}}},
            {'conditions': {'ref_name': {'include': ['refs/tags/staysharp-v2*'], 'exclude': []}}},
            {'conditions': {'ref_name': {'include': ['refs/tags/staysharp-v*'], 'exclude': ['refs/tags/staysharp-v1*']}}},
            {'bypass_actors': [{'actor_type': 'RepositoryRole', 'actor_id': 5, 'bypass_mode': 'always'}]},
            {'bypass_actors': None},
            {'rules': [{'type': 'deletion'}]}, {'rules': [{'type': 'update'}]},
            {'rules': [{'type': 'creation'}, {'type': 'update'}, {'type': 'deletion'}]},
        ):
            with self.subTest(changes=changes):
                self.assertFalse(accepted({**baseline, **changes}, '42', baseline['updated_at']))

        hidden = dict(baseline)
        del hidden['bypass_actors']
        self.assertFalse(accepted(hidden), 'Redacted actors must not be assumed empty')
        self.assertFalse(accepted(hidden, '42'), 'Missing approval timestamp must fail')
        self.assertFalse(accepted(hidden, '', baseline['updated_at']), 'Missing approval ID must fail')
        self.assertFalse(accepted(hidden, '43', baseline['updated_at']), 'Incorrect approval ID must fail')
        self.assertFalse(accepted(hidden, '42', '2026-10-22T09:00:00Z'), 'Stale admin review must fail')
        self.assertTrue(accepted(hidden, '42', baseline['updated_at']),
                        'Exact owner-approved ruleset revision can pass without a PAT')
        missing_timestamp = dict(hidden)
        del missing_timestamp['updated_at']
        self.assertFalse(accepted(missing_timestamp, '42', baseline['updated_at']))

    def test_live_remote_tag_checked_after_publication_and_final_verification(self):
        first = WORKFLOW.index('          check_remote_tag\n')
        publish = WORKFLOW.index('            gh release create')
        after = WORKFLOW.index('          check_remote_tag\n', publish)
        manifest = WORKFLOW.index('          python3 scripts/release_installers.py verify "$remote"')
        final = WORKFLOW.index('          check_remote_tag\n', manifest)
        self.assertLess(first, publish)
        self.assertLess(publish, after)
        self.assertLess(after, manifest)
        self.assertLess(manifest, final)
        self.assertIn('git ls-remote --tags origin "refs/tags/$tag^{}"', WORKFLOW)
        self.assertIn('git ls-remote --tags origin "refs/tags/$tag"', WORKFLOW)

    def test_asset_integrity_and_fail_closed_drafts(self):
        self.assertIn('sha256sum --check SHA256SUMS.txt', WORKFLOW)
        self.assertIn('gh release download', WORKFLOW)
        self.assertIn('cmp -- "release/$name" "$remote/$name"', WORKFLOW)
        self.assertIn('isDraft', WORKFLOW)
        self.assertIn('draft)', WORKFLOW)
        self.assertIn('exit 1', WORKFLOW)

    def test_bash_syntax_in_release_step(self):
        fragment = WORKFLOW.split('      - name: Create and verify GitHub Release\n', 1)[1]
        script = fragment.split('        run: |\n', 1)[1]
        lines = []
        for line in script.splitlines():
            if line and not line.startswith('          '):
                break
            lines.append(line[10:] if line else '')
        result = subprocess.run(['bash', '-n'], input='\n'.join(lines) + '\n',
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_write_token_not_exposed_to_build_job(self):
        build, publish = WORKFLOW.split('\n  publish:', 1)
        self.assertNotIn('GH_TOKEN:', build)
        self.assertNotIn('persist-credentials: true', build)
        self.assertIn('GH_TOKEN: ${{ github.token }}', publish)


if __name__ == '__main__':
    unittest.main()
