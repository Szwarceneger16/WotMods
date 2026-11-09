#!/usr/bin/env python3
"""Fail-closed validation of the repository's immutable release tag Ruleset.

GitHub may serialize the same Ruleset updated_at timestamp with a local offset
for the owner and with a UTC Z suffix for a limited GitHub Actions token.
"""

import argparse
from datetime import datetime, timezone
import json
import re
import sys


RELEASE_TAG_RULESET = 'wotmods-release-tags'
RELEASE_TAG_PATTERN = 'refs/tags/wotmods-v*'
TIMESTAMP = re.compile(
    r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})$'
)


def parse_timestamp(value):
    """Return a timezone-aware UTC instant, or None for invalid timestamps."""
    if not isinstance(value, str) or not TIMESTAMP.fullmatch(value):
        return None
    try:
        parsed = datetime.fromisoformat(value[:-1] + '+00:00' if value.endswith('Z') else value)
    except ValueError:
        return None
    return parsed.astimezone(timezone.utc)


def verify_ruleset(policy, ruleset_id, reviewed_id='', reviewed_at=''):
    """Require native tag protection and a verified empty bypass list.

    An explicitly returned bypass list is authoritative and must be empty.
    Only absent/null (redacted) lists can use the owner's ID/revision attestation.
    """
    if not isinstance(policy, dict):
        return False
    if (type(policy.get('id')) is not int or policy['id'] != ruleset_id or
            policy.get('name') != RELEASE_TAG_RULESET or
            policy.get('target') != 'tag' or
            policy.get('enforcement') != 'active'):
        return False

    try:
        refs = policy['conditions']['ref_name']
    except (KeyError, TypeError):
        return False
    if (not isinstance(refs, dict) or
            refs.get('include') != [RELEASE_TAG_PATTERN] or
            refs.get('exclude', []) != []):
        return False

    rules = policy.get('rules')
    if not isinstance(rules, list) or not all(
            isinstance(rule, dict) and isinstance(rule.get('type'), str)
            for rule in rules):
        return False
    types = {rule['type'] for rule in rules}
    if 'creation' in types or not {'update', 'deletion'} <= types:
        return False

    bypass = policy.get('bypass_actors')
    if bypass is not None:
        return isinstance(bypass, list) and bypass == []

    # No bypass list was visible to this token: require owner-reviewed evidence.
    observed = parse_timestamp(policy.get('updated_at'))
    approved = parse_timestamp(reviewed_at)
    return (reviewed_id == str(ruleset_id) and
            observed is not None and approved is not None and observed == approved)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ruleset-id', type=int, required=True)
    parser.add_argument('--reviewed-id', default='')
    parser.add_argument('--reviewed-at', default='')
    args = parser.parse_args()
    try:
        policy = json.load(sys.stdin)
    except (ValueError, UnicodeError):
        print('Invalid GitHub Ruleset response', file=sys.stderr)
        return 1
    if not verify_ruleset(policy, args.ruleset_id, args.reviewed_id, args.reviewed_at):
        print('GitHub release tag Ruleset failed the owner-approved protection checks', file=sys.stderr)
        return 1
    print('Release tag Ruleset protection verified')
    return 0


if __name__ == '__main__':
    sys.exit(main())
