# -*- coding: utf-8 -*-
"""Premium rows report original-account deltas, never a second total multiplier."""
from __future__ import unicode_literals

import copy
import shutil
import tempfile
import unittest

from test_core import EXPECTED
from test_normalize import raw_result
from grz_session_stats.battle_details import clean_details, merge_details, result_details
from grz_session_stats.core import StatsService
from grz_session_stats.normalize import normalize_result


class PremiumBonusTests(unittest.TestCase):
    def vehicle(self):
        return dict(originalCredits=13228, credits=22818,
                    originalXP=225, xp=389, originalFreeXP=11, freeXP=20,
                    originalTMenXP=225, tmenXP=389,
                    appliedPremiumCreditsFactor100=150, appliedPremiumXPFactor100=150,
                    appliedPremiumTmenXPFactor100=150,
                    wotPlusCredits=2976, wotPlusXP=51, wotPlusFreeXP=3, wotPlusCrewXP=51)

    def bonuses(self, vehicle):
        return result_details({}, vehicle).get('bonuses', {})

    def test_premium_and_plus_stay_separate_with_native_half_up_rounding(self):
        amounts = self.bonuses(self.vehicle())
        for key, expected in (('premiumCredits', 6614), ('premiumXP', 113),
                              ('premiumFreeXP', 6), ('premiumCrewXP', 113),
                              ('wotPlusCredits', 2976), ('wotPlusXP', 51),
                              ('wotPlusFreeXP', 3), ('wotPlusCrewXP', 51)):
            self.assertEqual(amounts[key], expected, key)

    def test_received_totals_reserves_and_events_cannot_inflate_the_premium_delta(self):
        vehicle = self.vehicle()
        expected = self.bonuses(vehicle)
        vehicle.update(credits=999999999, xp=999999, freeXP=99999, tmenXP=999999,
                       boosterCredits=12345678, boosterXP=99999, eventCredits=987654321,
                       dailyXPFactor10=50, additionalXPFactor10=30)
        actual = self.bonuses(vehicle)
        for key in ('premiumCredits', 'premiumXP', 'premiumFreeXP', 'premiumCrewXP'):
            self.assertEqual(actual[key], expected[key])

    def test_originals_and_matching_factors_are_required_independently(self):
        vehicle = self.vehicle()
        del vehicle['originalCredits']
        del vehicle['originalFreeXP']
        del vehicle['appliedPremiumTmenXPFactor100']
        amounts = self.bonuses(vehicle)
        self.assertEqual(amounts['premiumXP'], 113)
        for key in ('premiumCredits', 'premiumFreeXP', 'premiumCrewXP'):
            self.assertNotIn(key, amounts)
        # A factor-only report or an unrelated premium-sounding field is not
        # evidence of a resource amount.
        self.assertNotIn('premiumXP', self.bonuses(dict(appliedPremiumXPFactor100=150,
                                                       xp=99999, premiumXP=12345)))

    def test_zero_original_is_known_and_fractional_invalid_or_disabled_factors_are_unknown(self):
        vehicle = self.vehicle()
        for key in ('originalCredits', 'originalXP', 'originalFreeXP', 'originalTMenXP'):
            vehicle[key] = 0
        amounts = self.bonuses(vehicle)
        for key in ('premiumCredits', 'premiumXP', 'premiumFreeXP', 'premiumCrewXP'):
            self.assertEqual(amounts[key], 0)
        for invalid in (None, True, -1, 1.5, float('nan'), float('inf'), 10 ** 13):
            vehicle = self.vehicle()
            vehicle['originalXP'] = invalid
            self.assertNotIn('premiumXP', self.bonuses(vehicle))
        for invalid in (None, True, -1, 0, 100, 150.5, float('nan'), float('inf'), 10001):
            vehicle = self.vehicle()
            vehicle['appliedPremiumXPFactor100'] = invalid
            self.assertNotIn('premiumXP', self.bonuses(vehicle))

    def test_integer_rounding_is_exact_for_odd_originals_and_large_bounded_amounts(self):
        for original, factor, delta in ((1, 150, 1), (11, 150, 6), (225, 150, 113),
                                        (999999999999, 150, 500000000000), (101, 125, 25)):
            self.assertEqual(self.bonuses(dict(originalXP=original, appliedPremiumXPFactor100=factor))['premiumXP'], delta)

    def test_new_absolute_fields_survive_whitelist_and_partial_reconciliation(self):
        details = result_details({}, self.vehicle())
        before = copy.deepcopy(details)
        self.assertEqual(clean_details(details), details)
        partial = result_details({}, dict(appliedPremiumXPFactor100=150, xp=9999))
        updated = merge_details(details, partial, True)
        for key in ('premiumCredits', 'premiumXP', 'premiumFreeXP', 'premiumCrewXP'):
            self.assertEqual(updated['bonuses'][key], details['bonuses'][key])
        self.assertEqual(details, before)
        revised = result_details({}, dict(originalXP=227, appliedPremiumXPFactor100=150))
        self.assertEqual(merge_details(details, revised, True)['bonuses']['premiumXP'], 114)

    def test_full_normalization_enriches_saved_factor_only_history_without_changing_received_values(self):
        directory = tempfile.mkdtemp(prefix='grz-premium-amounts-')
        try:
            raw = raw_result()
            raw['personal'][1].update(self.vehicle())
            current = normalize_result(raw, {'account_dbid': 7})
            legacy = copy.deepcopy(current)
            for key in ('premiumCredits', 'premiumXP', 'premiumFreeXP', 'premiumCrewXP'):
                del legacy['details']['bonuses'][key]
            service = StatsService(directory, 'EU:7', 'premium-fixture', EXPECTED,
                                   now=lambda: current['started_at'])
            service.record_result(legacy)
            service.record_result(current)
            saved = copy.deepcopy(service._state['battles'][current['arena_id']])
            self.assertEqual(saved['details']['bonuses']['premiumXP'], 113)
            self.assertEqual(saved['details']['bonuses']['premiumFreeXP'], 6)
            restored = StatsService(directory, 'EU:7', 'premium-fixture-restored', EXPECTED,
                                    now=lambda: current['started_at'] + 600)
            row = restored._state['battles'][current['arena_id']]
            for key in ('xp_received', 'free_xp', 'currencies', 'details'):
                self.assertEqual(row[key], saved[key])
            self.assertEqual(row['xp_received'], 389)
            self.assertEqual(row['free_xp'], 20)
            self.assertEqual(row['currencies']['credits']['income'], 22818)
        finally:
            shutil.rmtree(directory)


if __name__ == '__main__':
    unittest.main()
