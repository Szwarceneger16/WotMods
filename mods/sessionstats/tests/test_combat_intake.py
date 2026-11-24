# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import errno
import os
import shutil
import tempfile
import threading
import unittest

from grz_session_stats.combat_intake import CombatIntake


class CombatIntakeTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.mkdtemp(prefix='ss-combat-intake-')
        self.intake = CombatIntake(self.directory)

    def tearDown(self):
        self.intake.close(wait=True)
        shutil.rmtree(self.directory)

    def test_submit_returns_while_the_disk_write_is_blocked(self):
        entered, resume = threading.Event(), threading.Event()
        write = self.intake._write
        writer = []

        def blocked(*args):
            writer.append(threading.current_thread().ident)
            entered.set()
            if not resume.wait(5):
                raise OSError('Test write did not resume.')
            write(*args)

        self.intake._write = blocked
        try:
            self.assertTrue(self.intake.submit('EU:100', 'result', {'arena_id': '42'}))
            self.assertTrue(entered.wait(5))
            self.assertNotEqual(writer[0], threading.current_thread().ident)
            self.assertEqual(self.intake.waiting('EU:100'), 1)
            self.assertEqual(self.intake.pending('EU:100'), [])
        finally:
            resume.set()
            self.intake.close(wait=True)
        self.assertEqual(self.intake.waiting('EU:100'), 0)
        self.assertEqual(self.intake.pending('EU:100')[0][2], {'arena_id': '42'})

    def test_restart_replays_in_order_and_acknowledgement_is_account_scoped(self):
        self.intake.submit('EU:100', 'begin', {'arena_id': '42'})
        self.intake.submit('EU:200', 'result', {'arena_id': 'different'})
        self.intake.submit('EU:100', 'result', {'arena_id': '42', 'xp': 840})
        self.intake.close(wait=True)
        self.intake = CombatIntake(self.directory)
        begin, = self.intake.pending('EU:100')
        self.assertEqual(begin[1:], ('begin', {'arena_id': '42'}))
        self.assertTrue(self.intake.ack(begin[0]))
        self.assertTrue(self.intake.ack(begin[0]))
        self.assertEqual(self.intake.pending('EU:100')[0][1:],
                         ('result', {'arena_id': '42', 'xp': 840}))
        self.assertEqual(self.intake.pending('EU:200')[0][2]['arena_id'], 'different')
        self.assertEqual(self.intake.pending('EU:300'), [])

    def test_first_combat_write_after_restart_follows_published_receipts_after_clock_rollback(self):
        from grz_session_stats import combat_intake
        from test_config_path import changed
        from test_runtime import Obj

        account = 'EU:100'
        with changed(combat_intake, 'time', Obj(time=lambda: 2000)):
            self.assertTrue(self.intake.submit(account, 'result', {'arena_id': '42', 'credits': 75000}))
            self.intake.close(wait=True)
        restarted = CombatIntake(self.directory)
        list_files = os.listdir
        reading_threads = []

        def track_listing(folder):
            reading_threads.append(threading.current_thread().ident)
            return list_files(folder)

        with changed(os, 'listdir', track_listing):
            try:
                with changed(combat_intake, 'time', Obj(time=lambda: 1000)):
                    self.assertTrue(restarted.submit(account, 'result', {'arena_id': '42', 'credits': 90000}))
                    self.assertTrue(restarted.submit(account, 'result', {'arena_id': '42', 'credits': 95000}))
            finally:
                restarted.close(wait=True)
        pending = self.intake.pending(account, limit=3)
        self.assertEqual([capture['credits'] for receipt, kind, capture in pending], [75000, 90000, 95000])
        self.assertEqual(len(reading_threads), 2)
        self.assertNotIn(threading.current_thread().ident, reading_threads)

    def test_interleaved_live_writers_keep_publication_order_after_clock_rollback(self):
        from grz_session_stats import combat_intake
        from test_config_path import changed
        from test_runtime import Obj

        account = 'EU:100'
        other = CombatIntake(self.directory)

        def publish(writer, timestamp, revision):
            write = writer._write
            published = threading.Event()

            def tracked(*args):
                write(*args)
                published.set()

            with changed(writer, '_write', tracked):
                with changed(combat_intake, 'time', Obj(time=lambda: timestamp)):
                    self.assertTrue(writer.submit(account, 'result', {'arena_id': '42', 'revision': revision}))
                self.assertTrue(published.wait(5))

        try:
            publish(self.intake, 10, 1)
            publish(other, 12, 2)
            publish(self.intake, 8, 3)
        finally:
            self.intake.close(wait=True)
            other.close(wait=True)
        receipts = self.intake.pending(account, limit=3)
        self.assertEqual([capture['revision'] for receipt, kind, capture in receipts], [1, 2, 3])

    def test_overlapping_publications_at_the_same_timestamp_serialize_through_shutdown(self):
        from grz_session_stats import combat_intake
        from test_config_path import changed
        from test_runtime import Obj

        account = 'EU:100'
        other = CombatIntake(self.directory)
        entered, resume, other_entered = threading.Event(), threading.Event(), threading.Event()
        first_write, other_write = self.intake._write, other._write

        def held(*args):
            entered.set()
            if not resume.wait(5):
                raise IOError(errno.EIO, 'Synthetic publication did not resume')
            first_write(*args)

        def tracked(*args):
            other_entered.set()
            other_write(*args)

        self.intake._write = held
        other._write = tracked
        try:
            with changed(combat_intake, 'time', Obj(time=lambda: 10)):
                self.assertTrue(self.intake.submit(account, 'result', {'arena_id': '42', 'revision': 1}))
                self.assertTrue(entered.wait(5))
                self.assertTrue(other.submit(account, 'result', {'arena_id': '42', 'revision': 2}))
                other.close()
                self.assertFalse(other_entered.wait(0.15))
        finally:
            resume.set()
            self.intake.close(wait=True)
            other.close(wait=True)
        self.assertFalse(other.failed)
        first, second = self.intake.pending(account, limit=2)
        self.assertEqual([first[2]['revision'], second[2]['revision']], [1, 2])
        self.assertLess(self.intake.identity(first[0])[1], self.intake.identity(second[0])[1])

    @unittest.skipUnless(os.name == 'nt', 'Windows MAX_PATH fixture')
    def test_long_unicode_profile_preserves_paths_bindings_and_fifo(self):
        for length in (123, 235):
            profile = os.path.join(self.directory, 'Ż' + 'x' * max(1, length - len(self.directory) - 2))
            self.intake = CombatIntake(profile)
            launch = 'a' * 32
            installation = 'installation:' + 'b' * 64
            try:
                self.assertTrue(self.intake.bind_installation(launch, installation))
                if length == 123 and len(profile) == length:
                    # The old spelling still reaches the same marker.
                    with open(os.path.join(profile, 'combat-intake', launch + '.installation'), 'rb') as handle:
                        self.assertEqual(handle.read(), installation.encode('ascii'))
                for kind, arena_id in (('begin', '42'), ('result', '42'), ('result', '43')):
                    self.assertTrue(self.intake.submit('EU:100', kind, {'arena_id': arena_id}))
                self.intake.close(wait=True)
                self.assertFalse(self.intake.failed)
                self.assertEqual(self.intake.waiting('EU:100'), 0)
                self.intake = CombatIntake(profile)
                self.assertEqual(self.intake.bound_installation(launch), installation)
                pending = self.intake.pending('EU:100', limit=3)
                self.assertEqual([row[1:] for row in pending], [
                    ('begin', {'arena_id': '42'}), ('result', {'arena_id': '42'}),
                    ('result', {'arena_id': '43'})])
                for receipt, unused_kind, unused_payload in pending:
                    self.assertGreater(len(os.path.join(profile, 'combat-intake', receipt.account,
                                                        receipt.filename)), 260)
                    self.assertTrue(self.intake.ack(receipt))
                self.assertEqual(self.intake.pending('EU:100'), [])
            finally:
                self.intake.close(wait=True)
                extended_profile = '\\\\?\\' + profile
                if os.path.isdir(extended_profile):
                    shutil.rmtree(extended_profile)

    def test_transient_disk_failure_retries_without_dropping_the_record(self):
        retried = threading.Event()
        write = self.intake._write
        attempts = []

        def fail_once(*args):
            attempts.append(None)
            if len(attempts) == 1:
                raise OSError('Temporary failure.')
            write(*args)
            retried.set()

        self.intake._write = fail_once
        self.intake.submit('EU:100', 'result', {'arena_id': '42'})
        self.assertTrue(retried.wait(5))
        self.intake.close(wait=True)
        self.assertTrue(self.intake.failed)
        self.assertEqual(self.intake.pending('EU:100')[0][2]['arena_id'], '42')

    def test_shutdown_retries_an_accepted_capture_after_a_temporary_write_error(self):
        write = self.intake._write
        attempts = []

        def fail_once(*args):
            attempts.append(None)
            if len(attempts) == 1:
                raise OSError(errno.EACCES, 'Synthetic temporary file lock')
            write(*args)

        self.intake._write = fail_once
        with self.intake._condition:
            self.assertTrue(self.intake.submit('EU:100', 'result', {'arena_id': '42'}))
            self.intake.close()
        self.intake.close(wait=True)
        self.assertEqual(len(attempts), 2)
        self.assertEqual(self.intake.pending('EU:100')[0][2]['arena_id'], '42')

    def test_corrupt_committed_file_is_preserved_and_good_receipts_still_replay(self):
        self.intake.submit('EU:100', 'begin', {'arena_id': '42'})
        self.intake.submit('EU:100', 'result', {'arena_id': '42', 'xp': 840})
        self.intake.close(wait=True)
        first, = self.intake.pending('EU:100')
        path = os.path.join(self.directory, 'combat-intake', first[0].account, first[0].filename)
        with open(path, 'wb') as handle:
            handle.write(b'invalid')
        self.assertEqual(self.intake.pending('EU:100')[0][1], 'result')
        self.assertTrue(self.intake.failed)
        self.assertTrue(os.path.isfile(path))

    def test_retryable_read_does_not_advance_ledger_past_missing_receipt(self):
        from grz_session_stats import combat_intake
        from grz_session_stats.core import StatsService
        from grz_session_stats.runtime import Runtime
        from test_core import Clock, EXPECTED, result

        account = 'EU:100'
        clock = Clock(1000)
        service = StatsService(self.directory, account, 'synthetic-current', EXPECTED, now=clock)
        runtime = Runtime(data_dir=self.directory, now=clock)

        def capture(writer, identifier, timestamp):
            writer.submit(account, 'result', {
                'at': timestamp + 1, 'launch_id': 'a' * 32, 'installation': None, 'observed': True,
                'record': result(identifier, timestamp),
            })

        capture(self.intake, 'synthetic-first', 1010)
        capture(self.intake, 'synthetic-second', 1020)
        self.intake.close(wait=True)
        first, second = self.intake.pending(account, limit=2)
        other = CombatIntake(self.directory)
        capture(other, 'synthetic-independent', 1030)
        self.assertTrue(other.submit('EU:200', 'begin', {'arena_id': 'unrelated-account'}))
        other.close(wait=True)
        read_errors = iter((errno.EACCES, errno.ENOENT))

        def temporarily_locked(path, *args, **kwargs):
            if os.path.basename(path) == first[0].filename:
                raise IOError(next(read_errors), 'Synthetic temporary read failure')
            return open(path, *args, **kwargs)

        combat_intake.open = temporarily_locked
        try:
            runtime._drain_account_captures(self.intake, account, service)
            self.assertTrue(self.intake.has_backlog(account, lambda *unused: False))
            self.assertEqual(self.intake.pending('EU:200')[0][2]['arena_id'], 'unrelated-account')
        finally:
            del combat_intake.open

        self.assertFalse(service.has_combat_receipt(self.intake.identity(first[0])))
        self.assertFalse(service.has_combat_receipt(self.intake.identity(second[0])))
        self.assertEqual(service._state['battles'], {})
        self.assertEqual(self.intake.pending(account, limit=3)[:2], [first, second])

        runtime._drain_account_captures(self.intake, account, service)
        runtime._drain_installation_captures(self.intake, account, service)
        runtime._drain_account_captures(self.intake, account, service)
        runtime._drain_installation_captures(self.intake, account, service)
        self.assertEqual(set(service._state['battles']),
                         {'synthetic-first', 'synthetic-second', 'synthetic-independent'})
        self.assertEqual(self.intake.pending(account), [])

    def test_receipt_watermarks_are_ordered_and_scoped_to_producer_and_account(self):
        self.intake.submit('EU:100', 'begin', {'arena_id': '42'})
        self.intake.submit('EU:100', 'result', {'arena_id': '42', 'xp': 840})
        self.intake.submit('EU:200', 'begin', {'arena_id': '42'})
        self.intake.close(wait=True)
        first, second = self.intake.pending('EU:100', limit=2)
        producer, offset = self.intake.identity(first[0])
        other_producer, next_offset = self.intake.identity(second[0])
        self.assertEqual(producer, other_producer)
        self.assertGreater(next_offset, offset)
        foreign, = self.intake.pending('EU:200')
        self.assertNotEqual(self.intake.identity(foreign[0])[0], producer)

        restored = CombatIntake(self.directory)
        skipped = lambda receipt: restored.identity(receipt)[1] <= offset
        self.assertEqual(restored.pending('EU:100', skip=skipped), [second])
        self.assertEqual(restored.pending('EU:100', accept=lambda unused, kind, payload: kind == 'result'),
                         [second])
        restored.submit('EU:100', 'result', {'arena_id': '43'})
        restored.close(wait=True)
        latest = next(capture for capture in restored.pending('EU:100', limit=3)
                      if capture[2]['arena_id'] == '43')
        self.assertNotEqual(restored.identity(latest[0])[0], producer)

    def test_locked_installation_binding_preserves_producer_order_and_account_progress(self):
        from grz_session_stats import combat_intake
        from grz_session_stats.core import StatsService
        from grz_session_stats.runtime import Runtime
        from grz_session_stats.sessions import InstallationSession
        from test_core import Clock, EXPECTED, result

        account = 'EU:100'
        launch = 'a' * 32
        clock = Clock(1000)
        service = StatsService(self.directory, account, 'synthetic-current', EXPECTED, now=clock)
        runtime = Runtime(data_dir=self.directory, now=clock)
        session = InstallationSession(self.directory, self.directory, 'synthetic-current', EXPECTED, clock)
        runtime._instance_session = session
        runtime._combat_installation = session.service.account_key
        self.assertTrue(self.intake.bind_installation(launch, runtime._combat_installation))

        def capture(writer, identifier, timestamp, origin):
            self.assertTrue(writer.submit(account, 'result', {
                'at': timestamp + 1, 'launch_id': launch, 'installation': origin, 'observed': True,
                'record': result(identifier, timestamp),
            }))

        capture(self.intake, 'synthetic-first', 1010, None)
        capture(self.intake, 'synthetic-second', 1020, runtime._combat_installation)
        self.intake.close(wait=True)
        first, second = self.intake.pending(account, limit=2)
        independent = CombatIntake(self.directory)
        capture(independent, 'synthetic-independent', 1030, runtime._combat_installation)
        independent.close(wait=True)
        binding_reads = []

        def temporarily_locked(path, *args, **kwargs):
            if os.path.basename(path) == launch + '.installation':
                binding_reads.append(path)
                if len(binding_reads) == 1:
                    raise IOError(errno.EACCES, 'Synthetic temporary file lock')
            return open(path, *args, **kwargs)

        combat_intake.open = temporarily_locked
        try:
            runtime._drain_account_captures(self.intake, account, service)
            runtime._drain_account_captures(self.intake, account, service)
            self.assertEqual(set(service._state['battles']),
                             {'synthetic-first', 'synthetic-second', 'synthetic-independent'})
            self.assertEqual(binding_reads, [])

            runtime._drain_installation_captures(self.intake, account, service)
            self.assertEqual(len(binding_reads), 1)
            self.assertEqual(self.intake.pending(account, limit=3)[:2], [first, second])
            self.assertEqual(set(session.service._state['battles']),
                             {session.battle_key(account, 'synthetic-independent')})

            runtime._drain_installation_captures(self.intake, account, service)
            self.assertEqual(len(binding_reads), 2)
            runtime._drain_installation_captures(self.intake, account, service)
            self.assertEqual(self.intake.pending(account), [])
            self.assertEqual(set(session.service._state['battles']), {
                session.battle_key(account, identifier)
                for identifier in ('synthetic-first', 'synthetic-second', 'synthetic-independent')})
        finally:
            del combat_intake.open

    def test_shared_installation_tracks_one_writer_per_account_even_when_drained_in_reverse(self):
        from grz_session_stats.core import StatsService
        from grz_session_stats.runtime import Runtime
        from grz_session_stats.sessions import InstallationSession
        from test_core import Clock, EXPECTED, result

        clock = Clock(1000)
        launch = 'e' * 32
        runtime = Runtime(data_dir=self.directory, now=clock)
        session = InstallationSession(self.directory, self.directory, launch, EXPECTED, clock)
        runtime._instance_session = session
        runtime._combat_installation = session.service.account_key
        accounts = ('EU:100', 'EU:200')
        services = {account: StatsService(self.directory, account, launch, EXPECTED, now=clock)
                    for account in accounts}
        for account in accounts:
            # These legacy receipts intentionally carry no observation order.
            self.assertTrue(self.intake.submit(account, 'result', {
                'at': 1100, 'launch_id': launch, 'observed': True,
                'installation': session.service.account_key,
                'record': result('same-arena', 1010),
            }))
        self.intake.close(wait=True)
        older, newer = [self.intake.identity(self.intake.pending(account)[0][0]) for account in accounts]
        self.assertLess(older[1], newer[1])
        self.assertNotEqual(older[0], newer[0])
        for account in reversed(accounts):
            runtime._drain_account_captures(self.intake, account, services[account])
            runtime._drain_installation_captures(self.intake, account, services[account])
            self.assertEqual(self.intake.pending(account), [])
        self.assertEqual(set(session.service._state['battles']),
                         set(session.battle_key(account, 'same-arena') for account in accounts))

    def test_late_installation_binding_is_durable_and_cannot_be_reassigned(self):
        launch = 'a' * 32
        first = 'installation:' + 'b' * 64
        other = 'installation:' + 'c' * 64
        self.assertIsNone(self.intake.bound_installation(launch))
        self.assertTrue(self.intake.bind_installation(launch, first))
        self.assertTrue(self.intake.bind_installation(launch, first))
        restored = CombatIntake(self.directory)
        self.assertEqual(restored.bound_installation(launch.encode('ascii')), first)
        self.assertFalse(restored.bind_installation(launch, other))
        self.assertEqual(self.intake.bound_installation(launch), first)
        self.assertFalse(restored.bind_installation('../outside', first))
        self.assertFalse(restored.bind_installation('d' * 32, 'unsanitized path'))


if __name__ == '__main__':
    unittest.main()
