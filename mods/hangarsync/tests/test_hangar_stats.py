"""Strict data-only boundary for the optional, already loaded Stats mod."""
import copy
import importlib.util
from pathlib import Path
import types
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('hangar_stats', ROOT / 'source' / 'hangar_stats.py')
bridge = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bridge)
MODULE = 'gui.mods.grz_session_stats.runtime'


def fixture():
    return {'schemaVersion': 1, 'provider': 'grz-session-stats', 'providerVersion': '0.4.1',
            'scope': 'recordedRandomBattles', 'status': 'available',
            'dayRange': {'from': '2025-11-05', 'through': '2026-11-05', 'basis': 'gameLocalTime'},
            'vehicles': [{'vehicleId': 62513, 'battles': 3, 'wn8': 1654.5, 'creditsNet': -45,
                          'lastPlayedAt': 1793880000, 'battlesToday': 2,
                          'battlesByDay': {'2026-11-04': 1, '2026-11-05': 2}, 'ownedSince': None}]}


class StatsBridgeTests(unittest.TestCase):
    def collect(self, value, ids=(62513,)):
        provider = types.SimpleNamespace(read_hangar_stats=lambda _: value)
        return bridge.collect_session_stats(ids, {MODULE: provider})

    def test_absent_or_old_mod_is_not_loaded_by_bridge(self):
        self.assertEqual(bridge.collect_session_stats([62513], {})['status'], 'not_loaded')
        self.assertEqual(bridge.collect_session_stats([62513], {MODULE: object()})['status'], 'unsupported')

    def test_only_requested_vehicle_and_contract_fields_cross_boundary(self):
        raw = fixture()
        raw['account_key'] = 'private-account'
        raw['path'] = 'private-file-path'
        raw['vehicles'][0]['secret'] = 'private-field'
        other = copy.deepcopy(raw['vehicles'][0])
        other['vehicleId'] = 7
        raw['vehicles'].append(other)
        result = self.collect(raw)
        self.assertEqual(result, fixture())
        self.assertEqual(self.collect(raw, ())['vehicles'], [])

    def test_unavailable_status_clears_previous_data(self):
        raw = fixture()
        raw['status'] = 'pending'
        result = self.collect(raw)
        self.assertEqual(result['vehicles'], [])
        self.assertNotIn('dayRange', result)

    def test_python27_byte_version_and_calendar_strings_are_normalized(self):
        raw = fixture()
        raw['providerVersion'] = b'0.4.1'
        raw['dayRange']['from'] = b'2025-11-05'
        raw['dayRange']['through'] = b'2026-11-05'
        raw['vehicles'][0]['battlesByDay'] = {b'2026-11-05': 2}
        result = self.collect(raw)
        self.assertEqual(result['status'], 'available')
        self.assertEqual(result['providerVersion'], '0.4.1')
        self.assertEqual(result['vehicles'][0]['battlesByDay'], {'2026-11-05': 2})
        raw['providerVersion'] = '0.4.1-beta+build'
        self.assertEqual(self.collect(raw)['providerVersion'], '0.4.1-beta+build')

    def test_invalid_numbers_duplicate_ids_and_calendar_dates_fail_closed(self):
        cases = []
        for key, value in [('wn8', float('nan')), ('battles', True), ('creditsNet', float('inf'))]:
            raw = fixture()
            raw['vehicles'][0][key] = value
            cases.append(raw)
        raw = fixture()
        raw['vehicles'].append(copy.deepcopy(raw['vehicles'][0]))
        cases.append(raw)
        for day in ('2026-02-30', '2026-11-06', '2025-11-04'):
            raw = fixture()
            raw['vehicles'][0]['battlesByDay'] = {day: 1}
            cases.append(raw)
        for raw in cases:
            self.assertEqual(self.collect(raw)['status'], 'unavailable')

    def test_provider_failure_never_escapes_or_returns_exception_text(self):
        def fail(_):
            raise RuntimeError('private-token-and-path')
        result = bridge.collect_session_stats([62513], {MODULE: types.SimpleNamespace(read_hangar_stats=fail)})
        self.assertEqual(result['status'], 'unavailable')
        self.assertNotIn('private', repr(result))


if __name__ == '__main__':
    unittest.main()
