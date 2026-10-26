#!/usr/bin/env python
"""Measure synthetic ledger/panel scaling outside WoT, on Python 2.7 or 3.

No player data or client APIs are used. Times are observations, not CI limits.
"""
from __future__ import print_function

import argparse
import copy
import json
import os
import shutil
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [os.path.join(ROOT, 'src'), os.path.join(ROOT, 'tests')]
from grz_session_stats.core import StatsService
from test_core import Clock, EXPECTED, result


def measure(count):
    directory = tempfile.mkdtemp(prefix='grz-history-benchmark-')
    timer = getattr(time, 'perf_counter', time.time)
    try:
        clock = Clock(100)
        service = StatsService(directory, 'synthetic:7', 'synthetic-launch', EXPECTED, clock)
        clock.value = 200
        service.record_result(result('0'))
        sample = service._state['battles']['0']
        service._state['battles'] = dict((str(index), dict(copy.deepcopy(sample), arena_id=str(index)))
                                        for index in range(count))
        # Seed a real durable legacy ledger, then build indexes through normal load.
        # Direct in-memory seeding would bypass both migration and cache construction.
        service.store.save(service._state)
        started = timer()
        service = StatsService(directory, 'synthetic:7', 'synthetic-launch', EXPECTED, clock)
        load_seconds = timer() - started
        assert not service.last_error, service.last_error
        started = timer()
        assert service.begin_battle(str(count)), 'Synthetic save failed'
        write_seconds = timer() - started
        started = timer()
        assert service.record_result(result('1', reconcile=True, xp_received=2100))
        revision_seconds = timer() - started
        started = timer()
        payload = json.dumps(service.snapshot(), ensure_ascii=True, separators=(',', ':'), allow_nan=False)
        snapshot_seconds = timer() - started
        started = timer()
        restored = StatsService(directory, 'synthetic:7', 'synthetic-launch', EXPECTED, clock)
        restart_seconds = timer() - started
        assert restored._state == service._state, 'Journal restart changed history'
        return {'records': count, 'write_seconds': round(write_seconds, 6),
                'revision_seconds': round(revision_seconds, 6), 'load_seconds': round(load_seconds, 3),
                'snapshot_seconds': round(snapshot_seconds, 6), 'journal_restart_seconds': round(restart_seconds, 3), 'snapshot_bytes': len(payload),
                'python': sys.version.split()[0], 'live_client': False}
    finally:
        shutil.rmtree(directory)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--records', type=int, nargs='+', default=[1000, 10000])
    args = parser.parse_args()
    if any(count < 1 or count > 100000 for count in args.records):
        parser.error('Use 1 to 100000 synthetic records per measurement')
    for count in args.records:
        print(json.dumps(measure(count), sort_keys=True))
        sys.stdout.flush()
