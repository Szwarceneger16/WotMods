"""Fail-closed tests for protected global release tag Ruleset attestation."""

import copy
import json
from pathlib import Path
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from release_ruleset import parse_timestamp, verify_ruleset  # noqa: E402


RULESET_ID = 26888687
OWNER_TIMESTAMP = '2026-11-09T21:14:31.734+01:00'
ACTION_TIMESTAMP = '2026-11-09T20:14:31.734Z'


def policy(**overrides):
    document = {
        'id': RULESET_ID,
        'name': 'wotmods-release-tags',
        'target': 'tag',
        'enforcement': 'active',
        'conditions': {
            'ref_name': {'include': ['refs/tags/wotmods-v*'], 'exclude': []},
        },
        'rules': [
            {'type': 'deletion'}, {'type': 'non_fast_forward'}, {'type': 'update'},
        ],
        'updated_at': ACTION_TIMESTAMP,
    }
    document.update(overrides)
    return document


class ReleaseRulesetTests(unittest.TestCase):
    def test_rfc3339_timezone_equivalence(self):
        self.assertEqual(parse_timestamp(OWNER_TIMESTAMP), parse_timestamp(ACTION_TIMESTAMP))
        self.assertIsNone(parse_timestamp('2026-11-09T20:14:31'))
        self.assertIsNone(parse_timestamp('not-a-date'))
        self.assertIsNone(parse_timestamp('2026-11-09T20:14:31.734000000Z'))

    def test_unredacted_empty_bypass_requires_no_attestation(self):
        doc = policy(bypass_actors=[])
        self.assertTrue(verify_ruleset(doc, RULESET_ID))

    def test_redacted_bypass_accepts_exact_revision_as_utc_instant(self):
        self.assertTrue(verify_ruleset(policy(), RULESET_ID, str(RULESET_ID), OWNER_TIMESTAMP))
        self.assertTrue(verify_ruleset(policy(bypass_actors=None), RULESET_ID,
                                       str(RULESET_ID), OWNER_TIMESTAMP))

    def test_redacted_bypass_rejects_stale_missing_or_invalid_review(self):
        doc = policy()
        for reviewed_id, reviewed_at in (
            ('', OWNER_TIMESTAMP),
            (str(RULESET_ID), ''),
            ('26888688', OWNER_TIMESTAMP),
            (str(RULESET_ID), '2026-11-09T20:14:31.735Z'),
            (str(RULESET_ID), '2026-11-09T20:14:31'),
        ):
            with self.subTest(reviewed_id=reviewed_id, reviewed_at=reviewed_at):
                self.assertFalse(verify_ruleset(doc, RULESET_ID, reviewed_id, reviewed_at))
        self.assertFalse(verify_ruleset(policy(updated_at='invalid'), RULESET_ID,
                                        str(RULESET_ID), OWNER_TIMESTAMP))

    def test_nonempty_or_invalid_bypass_list_is_never_approved(self):
        for bypass in ([{'actor_id': 1, 'actor_type': 'OrganizationAdmin'}], {}, 'redacted'):
            with self.subTest(bypass=bypass):
                self.assertFalse(verify_ruleset(policy(bypass_actors=bypass), RULESET_ID,
                                                str(RULESET_ID), OWNER_TIMESTAMP))

    def test_required_rules_and_exact_pattern_fail_closed(self):
        original = policy(bypass_actors=[])
        bad = []
        item = copy.deepcopy(original)
        item['rules'].append({'type': 'creation'})
        bad.append(item)
        item = copy.deepcopy(original)
        item['rules'] = [{'type': 'update'}]
        bad.append(item)
        item = copy.deepcopy(original)
        item['conditions']['ref_name']['include'] = ['refs/tags/*']
        bad.append(item)
        item = copy.deepcopy(original)
        item['conditions']['ref_name']['exclude'] = ['refs/tags/wotmods-v2*']
        bad.append(item)
        item = copy.deepcopy(original)
        item['enforcement'] = 'disabled'
        bad.append(item)
        item = copy.deepcopy(original)
        item['name'] = 'other-ruleset'
        bad.append(item)
        item = copy.deepcopy(original)
        item['id'] = RULESET_ID + 1
        bad.append(item)
        item = copy.deepcopy(original)
        item['rules'] = ['update', 'deletion']
        bad.append(item)
        for item in bad:
            with self.subTest(item=item):
                self.assertFalse(verify_ruleset(item, RULESET_ID,
                                                str(RULESET_ID), OWNER_TIMESTAMP))

    def test_cli_accepts_owner_review_and_rejects_unreviewed_policy(self):
        script = str(ROOT / 'scripts/release_ruleset.py')
        result = subprocess.run(
            [sys.executable, script, '--ruleset-id', str(RULESET_ID),
             '--reviewed-id', str(RULESET_ID), '--reviewed-at', OWNER_TIMESTAMP],
            input=json.dumps(policy()), text=True, capture_output=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        result = subprocess.run(
            [sys.executable, script, '--ruleset-id', str(RULESET_ID)],
            input=json.dumps(policy()), text=True, capture_output=True,
        )
        self.assertNotEqual(result.returncode, 0)


if __name__ == '__main__':
    unittest.main()
