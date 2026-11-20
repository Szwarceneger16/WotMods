"""Reduce private history to a fixed set of broad, independent QA bands."""

import json
from statistics import median


FIELDS = frozenset(('completion', 'wins', 'base_credits', 'base_xp', 'credits_income', 'credits_costs'))
LEVELS = frozenset(('low', 'middle', 'high'))
MIN_HISTORY = 40
MIN_METRIC_SAMPLE = 20


def nonnegative(value):
    return type(value) in (int, float) and value >= 0 and value <= 1_000_000_000


def band(value, lower, upper):
    if value < lower:
        return 'low'
    return 'high' if value >= upper else 'middle'


def rate_band(total, count, lower, upper):
    return band(count / total, lower, upper) if total >= MIN_METRIC_SAMPLE else 'middle'


def median_band(values, lower, upper):
    usable = [value for value in values if nonnegative(value)]
    return band(median(usable), lower, upper) if len(usable) >= MIN_METRIC_SAMPLE else 'middle'


def credit_values(row):
    currencies = row.get('currencies')
    if isinstance(currencies, dict) and isinstance(currencies.get('credits'), dict):
        return currencies['credits']
    return {}


def profile_from_rows(rows):
    """Return bands only, with no identifiers, timestamps, rows or exact counts."""
    eligible = [row for row in rows if isinstance(row, dict) and row.get('mode') == 'random']
    if len(eligible) < MIN_HISTORY:
        raise ValueError('Too few random battles for a private QA profile.')
    results = [row for row in eligible if row.get('_result_seen') and row.get('outcome') in ('win', 'loss', 'draw')]
    credits = [credit_values(row) for row in results]
    return {'schema': 1, 'bands': {
        'completion': rate_band(len(eligible), len(results), .75, .90),
        'wins': rate_band(len(results), sum(row.get('outcome') == 'win' for row in results), .40, .60),
        'base_credits': rate_band(len(results), sum(nonnegative(row.get('income_base')) for row in credits), .30, .70),
        'base_xp': median_band((row.get('xp_base') for row in results), 400, 900),
        'credits_income': median_band((row.get('income') for row in credits), 60000, 150000),
        'credits_costs': median_band((row.get('costs') for row in credits), 30000, 70000),
    }}


def _unique_object(pairs):
    data = dict(pairs)
    if len(data) != len(pairs):
        raise ValueError('Repeated profile field.')
    return data


def load_profile(path):
    """Accept only the exporter schema. An account ledger cannot enter the renderer."""
    try:
        with path.open('rb') as handle:
            raw = handle.read(1025)
        if len(raw) > 1024:
            raise ValueError('Profile is too large.')
        data = json.loads(raw, object_pairs_hook=_unique_object)
        levels = data.get('bands') if isinstance(data, dict) else None
        if (not isinstance(levels, dict) or set(data) != {'schema', 'bands'} or
                type(data['schema']) is not int or data['schema'] != 1 or set(levels) != FIELDS or
                not all(isinstance(level, str) and level in LEVELS for level in levels.values())):
            raise ValueError('Unexpected profile schema.')
        return levels
    except (OSError, UnicodeError, ValueError, RecursionError):
        raise ValueError('Invalid local QA profile. Use the aggregate exporter, never an account file.') from None
