# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import copy
import hashlib
import json
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src'))
from grz_session_stats.core import StatsService, ExpectedTable, aggregate_stats, wn8_from_totals
from grz_session_stats.storage import StorageError, canonical_bytes


EXPECTED = {'header': {'version': 'test-wg'}, 'data': [
    {'IDNum': 1, 'expDamage': 1000.0, 'expFrag': 1.0, 'expSpot': 1.0, 'expDef': 1.0, 'expWinRate': 55.0},
    {'IDNum': 2, 'expDamage': 2000.0, 'expFrag': 1.5, 'expSpot': 0.5, 'expDef': 0.5, 'expWinRate': 50.0}]}


class Clock(object):
    def __init__(self, value=100):
        self.value = value

    def __call__(self):
        return self.value


def result(arena_id='1', started_at=110, vehicle_id=1, **updates):
    row = {'arena_id': str(arena_id), 'started_at': started_at, 'ended_at': 120,
           'vehicle_id': vehicle_id, 'vehicle_name': 'Czo\u0142g testowy', 'vehicle_tier': 8,
           'vehicle_type': 'mediumTank', 'map_id': 'map-a', 'map_name': 'Mapa A',
           'mode': 'random', 'outcome': 'win', 'damage': 1000, 'frags': 1, 'spots': 1, 'defense': 1,
           'xp_base': 500, 'xp_received': 1500, 'free_xp': 75,
           'currencies': {'credits': {'income': 100, 'costs': 20, 'net': None,
                                       'breakdown': {'repair': 10, 'ammo': 10, 'consumables': 0, 'directives': 0}},
                          'bonds': {'income': 10, 'costs': 0, 'net': None},
                          'gold': {'income': 0, 'costs': 0, 'net': None}},
           'complete': True, 'warnings': []}
    row.update(updates)
    return row


class FormulaTests(unittest.TestCase):
    def test_expected_performance_is_1565_and_all_zero_is_zero(self):
        values = {'damage': 1000, 'frags': 1, 'spots': 1, 'defense': 1, 'wins': 0.55}
        self.assertAlmostEqual(wn8_from_totals(values, values), 1565.0)
        self.assertEqual(wn8_from_totals(dict((key, 0) for key in values), values), 0.0)
        invalid = dict(values, spots=0)
        self.assertIsNone(wn8_from_totals(values, invalid))

    def test_twenty_battles_at_expected_rates_are_1565(self):
        rows = [result(str(index), outcome='win' if index < 11 else 'loss') for index in range(20)]
        stats = aggregate_stats(rows, EXPECTED)
        self.assertEqual(stats['battles'], 20)
        self.assertEqual(stats['win_rate'], 55.0)
        self.assertAlmostEqual(stats['wn8'], 1565.0)

    def test_aggregate_is_not_arithmetic_mean_of_single_battle_wn8(self):
        rows = [result('1', damage=0, frags=0, spots=0, defense=0, outcome='loss'),
                result('2', damage=4000, frags=4, spots=4, defense=4, outcome='win')]
        stats = aggregate_stats(rows, EXPECTED)
        self.assertNotAlmostEqual(stats['wn8'], stats['battle_wn8']['avg'])
        self.assertEqual(stats['battle_wn8']['count'], 2)
        self.assertEqual(stats['battle_wn8']['min'], 0.0)

    def test_mixed_vehicles_sum_their_expected_values(self):
        rows = [result('1', vehicle_id=1, damage=1500, frags=2, spots=2, defense=1, outcome='win'),
                result('2', vehicle_id=2, damage=1500, frags=0, spots=0, defense=0, outcome='draw')]
        actual = {'damage': 3000, 'frags': 2, 'spots': 2, 'defense': 1, 'wins': 1}
        expected = {'damage': 3000, 'frags': 2.5, 'spots': 1.5, 'defense': 1.5, 'wins': 1.05}
        stats = aggregate_stats(rows, EXPECTED)
        self.assertAlmostEqual(stats['wn8'], wn8_from_totals(actual, expected))
        self.assertEqual(stats['win_rate'], 50.0)
        self.assertEqual(stats['draws'], 1)

    def test_missing_expected_is_not_zero_or_full_coverage(self):
        stats = aggregate_stats([result('1'), result('2', vehicle_id=999), result('3', spots=None)], EXPECTED)
        self.assertEqual(stats['battles'], 3)
        self.assertEqual(stats['wn8_count'], 1)
        self.assertEqual(stats['battle_wn8']['count'], 1)
        self.assertAlmostEqual(stats['wn8'], aggregate_stats([result('1')], EXPECTED)['wn8'])
        missing = aggregate_stats([result('2', vehicle_id=999)], EXPECTED)
        self.assertIsNone(missing['wn8'])
        self.assertIsNone(missing['battle_wn8']['min'])

    def test_full_table_and_parsed_mapping_are_supported(self):
        mapping = dict((str(row['IDNum']), row) for row in EXPECTED['data'])
        self.assertEqual(ExpectedTable(EXPECTED).values, ExpectedTable(mapping).values)

    def test_extrapolated_expected_winrate_above_100_is_preserved(self):
        source = copy.deepcopy(EXPECTED)
        source['data'][0]['expWinRate'] = 106.529
        table = ExpectedTable(source)
        self.assertAlmostEqual(table.values['1']['wins'], 1.06529)
        self.assertEqual(aggregate_stats([result()], table)['wn8_count'], 1)

    def test_empty_and_unknown_outcome_do_not_invent_values(self):
        stats = aggregate_stats([result(outcome=None)], EXPECTED)
        self.assertEqual(stats['battles'], 0)
        self.assertIsNone(stats['win_rate'])
        self.assertIsNone(stats['xp_base']['avg'])
        self.assertIsNone(stats['currencies']['bonds']['net'])


class ServiceTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.mkdtemp(prefix='grz-core-test-')
        self.clock = Clock()
        self.service = StatsService(self.directory, 'EU:1', 'launch-one', EXPECTED, self.clock)
        self.assertIsNone(self.service.last_error)
        self.clock.value = 120

    def tearDown(self):
        shutil.rmtree(self.directory)

    def summary(self, service=None, scope='launch'):
        return (service or self.service).snapshot()['scopes'][scope]['summary']

    def test_live_observation_before_initialization_enters_both_scopes_durably(self):
        self.assertTrue(self.service.begin_battle('1', started_at=90, mode='random'))
        manual_id = self.service._state['current_manual_id']
        self.assertEqual(self.summary()['observed_battles'], 1)
        self.assertEqual(self.summary(scope='manual')['observed_battles'], 1)
        restored = StatsService(self.directory, 'EU:1', 'launch-one', EXPECTED, self.clock)
        self.assertTrue(restored.record_result(result(started_at=90)))
        self.assertEqual(self.summary(restored)['battles'], 1)
        self.assertEqual(self.summary(restored, 'manual')['battles'], 1)
        self.assertEqual(restored._state['battles']['1']['_manual_id'], manual_id)
        sequence = restored.store.sequence
        self.assertFalse(restored.begin_battle('1', started_at=90, mode='random'))
        self.assertEqual(restored.store.sequence, sequence)

    def test_live_preinitialization_battle_respects_existing_manual_reset(self):
        self.clock.value = 130
        self.service.reset_manual()
        self.clock.value = 140
        self.assertTrue(self.service.begin_battle('1', started_at=90, mode='random'))
        self.assertEqual(self.summary()['observed_battles'], 1)
        self.assertEqual(self.summary(scope='manual')['observed_battles'], 0)
        self.assertIsNone(self.service._state['battles']['1']['_manual_id'])
        self.assertTrue(self.service.begin_battle('2', started_at=120, mode='random'))
        self.assertEqual(self.service._state['battles']['2']['_manual_id'],
                         self.service._state['manual_sessions'][0]['id'])

    def test_reobserved_old_battle_preserves_both_durable_memberships(self):
        self.service.begin_battle('1', started_at=90, mode='random')
        original = copy.deepcopy(self.service._state['battles']['1'])
        self.clock.value = 200
        restored = StatsService(self.directory, 'EU:1', 'launch-two', EXPECTED, self.clock)
        restored.reset_manual()
        restored.begin_battle('1', started_at=90, mode='random', vehicle_id=1)
        self.assertEqual(restored._state['battles']['1']['_launch_id'], original['_launch_id'])
        self.assertEqual(restored._state['battles']['1']['_manual_id'], original['_manual_id'])
        self.assertEqual(self.summary(restored)['observed_battles'], 0)
        self.assertEqual(self.summary(restored, 'manual')['observed_battles'], 0)

    def test_observed_gap_battle_enters_current_launch_without_reassigning_history(self):
        self.service.record_result(result())
        self.clock.value = 200
        restored = StatsService(self.directory, 'EU:1', 'launch-two', EXPECTED, self.clock)
        restored.begin_battle('2', started_at=170, mode='random')
        self.assertEqual(restored._state['battles']['2']['_launch_id'], 'launch-two')
        self.assertEqual(restored._state['battles']['1']['_launch_id'], 'launch-one')

    def test_unobserved_old_result_does_not_enter_new_initial_scopes(self):
        self.service.record_result(result(started_at=90))
        self.assertEqual(self.summary()['battles'], 0)
        self.assertEqual(self.summary(scope='manual')['battles'], 0)

    def test_invalid_observed_start_does_not_gain_membership(self):
        for index, invalid in enumerate(('invalid', -1, True)):
            self.assertTrue(self.service.begin_battle(str(index), started_at=invalid, mode='random'))
            row = self.service._state['battles'][str(index)]
            self.assertIsNone(row['_launch_id'])
            self.assertIsNone(row['_manual_id'])

    def test_clock_skewed_live_beginning_keeps_memberships_after_complete_result(self):
        manual_id = self.service._state['current_manual_id']
        self.assertTrue(self.service.begin_battle('1', started_at=121, mode='random'))
        self.assertTrue(self.service.record_result(result(started_at=121, ended_at=122)))
        self.assertEqual(self.service.pending_arena_ids(), [])
        for scope in ('launch', 'manual'):
            self.assertEqual(self.summary(scope=scope)['battles'], 1)
        self.clock.value = 200
        restored = StatsService(self.directory, 'EU:1', 'launch-two', EXPECTED, self.clock)
        restored.reset_manual()
        self.clock.value = 119
        restored.begin_battle('1', started_at=121, mode='random')
        row = restored._state['battles']['1']
        self.assertEqual(row['_launch_id'], 'launch-one')
        self.assertEqual(row['_manual_id'], manual_id)
        self.assertEqual(self.summary(restored)['battles'], 0)
        self.assertEqual(self.summary(restored, 'manual')['battles'], 0)

    def test_future_result_without_live_observation_has_no_memberships(self):
        self.service.record_result(result(started_at=121, ended_at=122))
        row = self.service._state['battles']['1']
        self.assertIsNone(row['_launch_id'])
        self.assertIsNone(row['_manual_id'])

    def test_clock_skewed_new_observations_respect_manual_reset_boundary(self):
        old_manual = self.service._state['current_manual_id']
        self.clock.value = 130
        new_manual = self.service.reset_manual()
        self.assertIsNotNone(new_manual)
        self.clock.value = 119
        for arena, started, expected in (('before', 121, old_manual), ('after', 131, new_manual)):
            self.service.begin_battle(arena, started_at=started, mode='random')
            self.service.record_result(result(arena, started_at=started, ended_at=started + 1))
            row = self.service._state['battles'][arena]
            self.assertEqual(row['_launch_id'], 'launch-one')
            self.assertEqual(row['_manual_id'], expected)
        self.assertEqual(self.summary()['battles'], 2)
        self.assertEqual(self.summary(scope='manual')['battles'], 1)

    def test_begin_is_durable_and_duplicate_result_is_idempotent(self):
        self.assertTrue(self.service.begin_battle('1', started_at=110, vehicle_id=1, mode='random'))
        reloaded = StatsService(self.directory, 'EU:1', 'launch-one', EXPECTED, self.clock)
        self.assertEqual(reloaded.pending_arena_ids(), ['1'])
        self.assertTrue(reloaded.record_result(result()))
        sequence = reloaded.store.sequence
        self.assertFalse(reloaded.record_result(result()))
        self.assertEqual(reloaded.store.sequence, sequence)
        self.assertEqual(self.summary(reloaded)['battles'], 1)
        self.assertEqual(reloaded.pending_arena_ids(), [])

    def test_partial_update_preserves_known_values_and_reconciliation_can_revise(self):
        self.service.record_result(result())
        update = {'arena_id': '1', 'damage': None, 'xp_base': None, 'xp_received': 999,
                  'currencies': {'credits': {'income': None, 'costs': None, 'net': None}}, 'complete': False}
        self.service.record_result(update)
        self.assertEqual(self.summary()['xp_received']['sum'], 1500)
        self.assertEqual(self.summary()['currencies']['credits']['income'], 100)
        update.update(complete=True, xp_received=4500, reconcile=True)
        self.assertTrue(self.service.record_result(update))
        self.assertEqual(self.summary()['xp_received']['sum'], 4500)
        self.assertEqual(self.summary()['xp_base']['sum'], 500)
        self.assertEqual(self.summary()['battles'], 1)

    def test_financial_sums_have_per_column_coverage_and_no_zero_imputation(self):
        self.service.record_result(result())
        self.service.record_result(result('2', currencies={'credits': {'income': 200, 'costs': None, 'net': None},
                                                         'bonds': {'income': 0, 'costs': 0, 'net': 0}}))
        stats = self.summary()
        money = stats['currencies']['credits']
        self.assertEqual(money['income'], 300)
        self.assertEqual(money['income_count'], 2)
        self.assertEqual(money['costs'], 20)
        self.assertEqual(money['costs_count'], 1)
        self.assertEqual(money['net'], 80)
        self.assertEqual(money['net_count'], 1)
        self.assertEqual(stats['currencies']['bonds']['net_count'], 2)
        self.assertEqual(stats['currencies']['gold']['income_count'], 1)
        self.assertEqual(money['breakdown']['consumables'], 0)
        self.assertEqual(money['breakdown_counts']['consumables'], 1)

    def test_authoritative_partial_update_revises_xp_without_inventing_money(self):
        self.service.record_result(result(complete=False, currencies={
            'credits': {'income': 100, 'costs': None, 'net': None}}))
        update = {'arena_id': '1', 'complete': False, 'reconcile': True,
                  'xp_base': None, 'xp_received': 4500,
                  'currencies': {'credits': {'income': None, 'costs': None, 'net': None},
                                 'bonds': {'income': None, 'costs': None, 'net': None}}}
        self.assertTrue(self.service.record_result(update))
        stats = self.summary()
        self.assertEqual(stats['xp_received']['sum'], 4500)
        self.assertEqual(stats['xp_base']['sum'], 500)
        self.assertEqual(stats['currencies']['credits']['income'], 100)
        self.assertIsNone(stats['currencies']['credits']['net'])
        self.assertIsNone(stats['currencies']['bonds']['net'])
        self.assertEqual(self.service.pending_arena_ids(), ['1'])
        self.assertEqual(stats['battles'], 1)
        self.assertNotIn('reconcile', self.service._state['battles']['1'])
        sequence = self.service.store.sequence
        self.assertFalse(self.service.record_result(update))
        self.assertEqual(self.service.store.sequence, sequence)

    def test_negative_after_penalty_income_is_preserved(self):
        self.service.record_result(result(currencies={
            'credits': {'income': -900, 'costs': 20, 'net': None}}))
        money = self.summary()['currencies']['credits']
        self.assertEqual(money['income'], -900)
        self.assertEqual(money['net'], -920)
        self.assertEqual(money['income_count'], 1)
        self.assertEqual(money['net_count'], 1)

    def test_restart_raw_cache_cannot_undo_a_confirmed_xp_bonus(self):
        self.service.record_result(result(complete=False, reconcile=True,
                                           xp_received=4500, xp_bonus_applied=True))
        self.clock.value = 200
        next_launch = StatsService(self.directory, 'EU:1', 'launch-two', EXPECTED, self.clock)
        next_launch.record_result(result(reconcile=True, xp_received=1500, xp_bonus_applied=False))
        self.assertEqual(self.summary(next_launch, 'manual')['xp_received']['sum'], 4500)
        self.assertTrue(next_launch._state['battles']['1']['xp_bonus_applied'])
        next_launch.record_result(result(reconcile=True, xp_received=4600, xp_bonus_applied=True))
        self.assertEqual(self.summary(next_launch, 'manual')['xp_received']['sum'], 4600)
        next_launch.record_result(result(reconcile=True, xp_received=1500))
        self.assertEqual(self.summary(next_launch, 'manual')['xp_received']['sum'], 4600)

    def test_authoritative_partial_components_recalculate_derived_net(self):
        self.service.record_result(result(complete=False))
        self.service.record_result({'arena_id': '1', 'complete': False, 'reconcile': True,
                                    'currencies': {'credits': {'income': -50, 'net': None}}})
        self.assertEqual(self.summary()['currencies']['credits']['net'], -70)
        self.assertEqual(self.service.pending_arena_ids(), ['1'])

    def test_updated_components_recalculate_derived_net(self):
        self.service.record_result(result())
        self.service.record_result({'arena_id': '1', 'complete': True, 'reconcile': True,
                                    'currencies': {'credits': {'income': 200, 'net': None}}})
        self.assertEqual(self.summary()['currencies']['credits']['net'], 180)

    def test_complete_stale_duplicate_has_no_authority_over_confirmed_values(self):
        current = result(reconcile=True, damage=2400, xp_received=4500)
        current['currencies']['credits'].update(income=500, costs=80, net=420)
        self.service.record_result(current)
        confirmed = copy.deepcopy(self.service._state['battles']['1'])
        sequence = self.service.store.sequence
        self.assertFalse(self.service.record_result(result(complete=True)))
        self.assertEqual(self.service._state['battles']['1'], confirmed)
        self.assertEqual(self.service.store.sequence, sequence)
        reloaded = StatsService(self.directory, 'EU:1', 'launch-one', EXPECTED, self.clock)
        self.assertFalse(reloaded.record_result(result(complete=True)))
        self.assertEqual(reloaded._state['battles']['1'], confirmed)

    def test_non_authoritative_complete_result_can_fill_unknown_fields(self):
        self.service.record_result(result(complete=False, damage=None, xp_base=None))
        self.assertTrue(self.service.record_result(result(complete=True, damage=2400, xp_base=800)))
        row = self.service._state['battles']['1']
        self.assertEqual(row['damage'], 2400)
        self.assertEqual(row['xp_base'], 800)
        self.assertTrue(row['complete'])

    def test_reset_keeps_launch_and_history_late_known_result_stays_old(self):
        self.service.begin_battle('1', started_at=110, vehicle_id=1, mode='random')
        original_manual = self.service._state['current_manual_id']
        self.clock.value = 130
        manual_id = self.service.reset_manual()
        self.assertNotEqual(original_manual, manual_id)
        self.clock.value = 150
        self.service.record_result(result('1', started_at=110))
        self.assertEqual(self.summary()['battles'], 1)
        self.assertEqual(self.summary(scope='manual')['battles'], 0)
        self.assertEqual(self.service._state['battles']['1']['_manual_id'], original_manual)
        self.assertEqual(len(self.service._state['battles']), 1)

    def test_unseen_late_result_uses_reliable_start_before_reset(self):
        self.clock.value = 130
        self.service.reset_manual()
        self.clock.value = 160
        self.service.record_result(result('1', started_at=120))
        self.service.record_result(result('2', started_at=140))
        self.assertEqual(self.summary()['battles'], 2)
        self.assertEqual(self.summary(scope='manual')['battles'], 1)

    def test_restart_does_not_move_old_pending_battle_to_new_launch(self):
        self.service.begin_battle('1', started_at=110, mode='random')
        self.clock.value = 200
        next_launch = StatsService(self.directory, 'EU:1', 'launch-two', EXPECTED, self.clock)
        self.clock.value = 210
        next_launch.record_result(result())
        self.assertEqual(self.summary(next_launch)['battles'], 0)
        self.assertEqual(self.summary(next_launch, 'manual')['battles'], 1)
        self.assertEqual(next_launch._state['battles']['1']['_launch_id'], 'launch-one')

    def test_unseen_timestamp_during_unobserved_gap_not_assigned_to_old_process(self):
        self.service.begin_battle('1', started_at=110, mode='random')
        self.clock.value = 200
        next_launch = StatsService(self.directory, 'EU:1', 'launch-two', EXPECTED, self.clock)
        next_launch.record_result(result('2', started_at=170))
        self.assertIsNone(next_launch._state['battles']['2']['_launch_id'])
        self.assertEqual(self.summary(next_launch)['battles'], 0)
        self.assertEqual(self.summary(next_launch, 'manual')['battles'], 1)

    def test_missing_start_is_not_assigned_then_reliable_timestamp_can_recover(self):
        self.service.record_result(result(started_at=None))
        self.assertEqual(self.summary()['battles'], 0)
        self.assertTrue(self.service.snapshot()['warnings'])
        self.service.record_result({'arena_id': '1', 'started_at': 110, 'complete': True})
        self.assertEqual(self.summary()['battles'], 1)

    def test_reconnect_preserves_launch_and_other_accounts_are_isolated(self):
        self.service.record_result(result())
        reconnect = StatsService(self.directory, 'EU:1', 'launch-one', EXPECTED, self.clock)
        self.assertEqual(self.summary(reconnect)['battles'], 1)
        for key in ('EU:2', 'NA:1'):
            other = StatsService(self.directory, key, 'launch-one', EXPECTED, self.clock)
            self.assertEqual(self.summary(other)['battles'], 0)
            self.assertNotEqual(other.store.directory, reconnect.store.directory)

    def test_groups_and_battles_derive_from_same_records(self):
        self.service.record_result(result('1'))
        self.service.record_result(result('2', map_id='map-b', map_name='Mapa B', outcome='loss'))
        self.service.record_result(result('3', vehicle_id=2, vehicle_name='Drugi', outcome='draw'))
        scope = self.service.snapshot()['scopes']['launch']
        for grouping in ('vehicles', 'maps', 'battles'):
            self.assertEqual(sum(group['stats']['battles'] for group in scope[grouping]), scope['summary']['battles'])
            self.assertEqual(sum(group['stats']['currencies']['credits']['net'] for group in scope[grouping]), 240)

    def test_no_replays_or_unsupported_modes(self):
        self.assertFalse(self.service.record_result(result(mode='frontline')))
        self.assertFalse(self.service.record_result(result(is_replay=True)))
        self.assertFalse(self.service.begin_battle('2', mode='ranked'))
        self.assertEqual(self.summary()['battles'], 0)

    def test_unknown_outcome_remains_pending(self):
        self.service.record_result(result(outcome=None))
        self.assertEqual(self.summary()['battles'], 0)
        self.assertEqual(self.service.pending_arena_ids(), ['1'])

    def test_failed_save_does_not_publish_or_reset_state(self):
        old_manual = self.service._state['current_manual_id']
        original = self.service.store.save
        def fail(unused):
            raise StorageError('Test: storage unavailable.')
        self.service.store.save = fail
        self.assertFalse(self.service.record_result(result()))
        self.assertEqual(self.summary()['battles'], 0)
        self.assertIsNotNone(self.service.last_error)
        self.assertIsNone(self.service.reset_manual())
        self.assertEqual(self.service._state['current_manual_id'], old_manual)
        self.service.store.save = original
        self.assertTrue(self.service.record_result(result()))
        self.assertIsNone(self.service.last_error)

    def test_newer_schema_makes_service_read_only_without_erasing_files(self):
        generation = self.service.store.sequence + 1
        payload = copy.deepcopy(self.service._state)
        payload['schema_version'] = 999
        envelope = {'storage_version': 1, 'generation': generation, 'payload': payload,
                    'payload_checksum': hashlib.sha256(canonical_bytes(payload)).hexdigest()}
        path = os.path.join(self.service.store.directory, 'state-%020d.json' % generation)
        with open(path, 'wb') as handle:
            handle.write(canonical_bytes(envelope))
        readonly = StatsService(self.directory, 'EU:1', 'launch-next', EXPECTED, self.clock)
        self.assertTrue(readonly.store.read_only)
        self.assertIsNotNone(readonly.last_error)
        self.assertFalse(readonly.record_result(result()))
        self.assertTrue(os.path.exists(path))
        json.dumps(readonly.snapshot(), allow_nan=False)

    def test_snapshot_is_strict_json_even_with_invalid_optional_numbers(self):
        self.service.record_result(result(damage=float('nan'), xp_base=True, xp_received=float('inf')))
        payload = self.service.snapshot()
        self.assertIsNone(payload['scopes']['launch']['summary']['wn8'])
        json.dumps(payload, allow_nan=False)


if __name__ == '__main__':
    unittest.main()
