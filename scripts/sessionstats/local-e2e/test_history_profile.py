"""Privacy boundaries of the local-only data profile."""

from io import BytesIO
import json
import unittest

from backend import example_battles
from history_profile import FIELDS, LEVELS, load_profile, profile_from_rows


class Input:
    def __init__(self, raw):
        self.raw = raw

    def open(self, mode):
        return BytesIO(self.raw)


def mock_rows(prefix, *, xp=650, income=95000):
    for i in range(80):
        yield {'mode': 'random', '_result_seen': True, 'outcome': 'win' if i % 2 else 'loss',
               'arena_id': f'{prefix}-example-{i}', 'vehicle_id': f'{prefix}-{i}', 'map_id': prefix,
               'player': prefix, 'started_at': 1_000_000 + i, 'xp_base': xp + i,
               'currencies': {'credits': {'income': income + i, 'income_base': 40000, 'costs': 42000}}}


class HistoryProfileTest(unittest.TestCase):
    def test_identifier_order_and_nearby_values_do_not_affect_profile(self):
        first = profile_from_rows(mock_rows('different-account-A'))
        second = profile_from_rows(reversed(list(mock_rows('different-account-B', xp=660, income=98000))))
        self.assertEqual(first, second)
        self.assertEqual(set(first), {'schema', 'bands'})
        self.assertEqual(set(first['bands']), FIELDS)
        self.assertLessEqual(set(first['bands'].values()), LEVELS)
        self.assertEqual(load_profile(Input(json.dumps(first).encode())), first['bands'])

    def test_small_history_fails_and_rare_metric_values_are_suppressed(self):
        rows = list(mock_rows('fixture'))
        with self.assertRaises(ValueError):
            profile_from_rows(rows[:1])
        for i, row in enumerate(rows):
            row['xp_base'] = 50000 if i < 3 else None
        profile = profile_from_rows(rows)
        self.assertEqual(profile['bands']['base_xp'], 'middle')
        rows[2]['xp_base'] = 1
        self.assertEqual(profile_from_rows(rows), profile)

    def test_profile_loader_rejects_a_raw_ledger_and_extra_or_repeated_fields(self):
        profile = profile_from_rows(mock_rows('fixture'))
        valid = json.dumps(profile).encode()
        various = [b'x' * 2000, b'{"account_key":"example","battles":{}}',
                   valid[:-1] + b',"account_key":"example"}', valid[:-1] + b',"schema":1}']
        for raw in various:
            with self.subTest(length=len(raw)), self.assertRaisesRegex(ValueError, '^Invalid local QA profile'):
                load_profile(Input(raw))

    def test_synthetic_battles_are_generated_from_fixed_categories_only(self):
        date = 1_750_000_000
        low = dict.fromkeys(FIELDS, 'low')
        high = dict.fromkeys(FIELDS, 'high')
        first = list(example_battles(date, 'launch', 'previous', 'manual', 'older', low))
        second = list(example_battles(date, 'launch', 'previous', 'manual', 'older', high))
        fields = ('arena_id', 'started_at', 'vehicle_name', 'map_name')
        self.assertEqual(len(first), 344)
        self.assertEqual([[row[key] for key in fields] for row in first],
                         [[row[key] for key in fields] for row in second])
        self.assertGreater(sum(row.get('xp_base', 0) for row in second),
                           sum(row.get('xp_base', 0) for row in first))


if __name__ == '__main__':
    unittest.main()
