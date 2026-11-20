# -*- coding: utf-8 -*-
from __future__ import unicode_literals

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
