#!/usr/bin/env python
"""Measure cooperative startup CPU slices, excluding real client scheduling."""
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
    directory = tempfile.mkdtemp(prefix='grz-loading-benchmark-')
    timer = getattr(time, 'perf_counter', time.time)
    try:
        clock = Clock(100)
        seed = StatsService(directory, 'synthetic:7', 'launch', EXPECTED, clock)
        clock.value = 200
        seed.record_result(result('0'))
        sample = seed._state['battles']['0']
        seed._state['battles'] = dict((str(i), dict(copy.deepcopy(sample), arena_id=str(i))) for i in range(count))
        seed.store.save(seed._state)
        seed = None
        measurements = []
        service = None
        for format_name in ('legacy', 'journal'):
            service = None  # Release a previous test instance outside the timed constructor.
            started = timer()
            service = StatsService(directory, 'synthetic:7', 'launch', EXPECTED, clock, deferred=True)
            constructor = timer() - started
            slices, phases = [], {}
            while service.loading:
                phase = service.loading_phase
                before = timer()
                service.advance_loading()
                elapsed = timer() - before
                slices.append(elapsed)
                phases[phase] = max(phases.get(phase, 0), elapsed)
            assert service.ready, service.last_error
            assert len(service._state['battles']) == count
            assert service.snapshot()['scopes']['manual']['summary']['battles'] == count
            ordered = sorted(slices)
            measurements.append({'format': format_name, 'constructor_ms': round(constructor * 1000, 3),
                                 'steps': len(slices), 'work_seconds': round(sum(slices), 3),
                                 'slice_median_ms': round(ordered[len(ordered)//2] * 1000, 3),
                                 'slice_p99_ms': round(ordered[min(len(ordered)-1, int(len(ordered)*0.99))] * 1000, 3),
                                 'slice_max_ms': round(max(slices) * 1000, 3),
                                 'phase_max_ms': dict((key, round(value*1000, 3)) for key,value in phases.items())})
        return {'records': count, 'python': sys.version.split()[0], 'live_client': False,
                'budget_ms': 2, 'measurements': measurements}
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
