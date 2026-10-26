# -*- coding: utf-8 -*-
"""Bounded local log, OS-lock boundaries and safe client failure handling."""
from __future__ import unicode_literals

import errno
import io
import logging
import os
import shutil
import sys
import tempfile
import types
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src'))
from grz_session_stats import diagnostics, VERSION

try:
    import builtins
except ImportError:
    import __builtin__ as builtins


class Capture(logging.Handler):
    def __init__(self):
        logging.Handler.__init__(self)
        self.records = []

    def emit(self, record):
        self.records.append(record)


class DiagnosticsTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.mkdtemp(prefix='grz-log-test-')
        self.states = []
        self.logger = logging.getLogger(diagnostics.LOGGER_NAME)
        self.old_level = self.logger.level
        self.old_disable = logging.root.manager.disable
        self.old_raise = logging.raiseExceptions
        logging.disable(logging.NOTSET)
        logging.raiseExceptions = True

    def tearDown(self):
        for state in self.states:
            state.close()
        self.logger.setLevel(self.old_level)
        logging.disable(self.old_disable)
        logging.raiseExceptions = self.old_raise
        shutil.rmtree(self.directory)

    def start(self, directory=None):
        state = diagnostics.start_logging(directory or self.directory)
        self.states.append(state)
        return state

    def read(self, state):
        with io.open(state.path, 'r', encoding='utf-8') as handle:
            return handle.read()

    def test_unicode_path_text_version_timestamp_and_native_propagation(self):
        capture = Capture()
        logging.root.addHandler(capture)
        original_root_level = logging.root.level
        original_propagation = self.logger.propagate
        try:
            state = self.start(os.path.join(self.directory, 'Żółć'))
            self.assertTrue(state.ok)
            self.logger.warning('Missing field: %s', 'received XP — żółć')
            content = self.read(state)
            self.assertIn('Missing field: received XP — żółć', content)
            self.assertIn('[v%s]' % VERSION, content)
            self.assertIn('Z WARNING', content)
            self.assertEqual(len(capture.records), 1)
            self.assertEqual(logging.root.level, original_root_level)
            self.assertEqual(self.logger.propagate, original_propagation)
        finally:
            logging.root.removeHandler(capture)

    def test_utf8_byte_message_is_decoded_without_modifying_other_handlers_record(self):
        capture = Capture()
        self.logger.addHandler(capture)
        try:
            state = self.start()
            message = 'Zażółć %s'.encode('utf-8')
            value = 'gęślą'.encode('utf-8')
            self.logger.warning(message, value)
            self.assertIn('Zażółć gęślą', self.read(state))
            self.assertEqual(capture.records[-1].msg, message)
            self.assertEqual(capture.records[-1].args, (value,))
        finally:
            self.logger.removeHandler(capture)

    def test_info_reaches_own_file_when_host_root_level_is_warning(self):
        previous_root_level = logging.root.level
        self.logger.setLevel(logging.NOTSET)
        logging.root.setLevel(logging.WARNING)
        try:
            state = self.start()
            self.logger.info('result complete pending=0')
            self.assertIn('INFO [v%s] result complete pending=0' % VERSION, self.read(state))
            self.assertEqual(logging.root.level, logging.WARNING)
            state.close()
            self.assertEqual(self.logger.level, logging.NOTSET)
            self.assertEqual(logging.root.level, logging.WARNING)
        finally:
            logging.root.setLevel(previous_root_level)

    def test_repeated_start_and_close_have_one_owned_handler_and_keep_others(self):
        unrelated = logging.getLogger('another.mod')
        capture = Capture()
        self.logger.addHandler(capture)
        root_handlers = list(logging.root.handlers)
        other_handlers = list(unrelated.handlers)
        before = self.logger.level
        try:
            state = self.start()
            again = self.start()
            self.assertIs(state, again)
            owned = [handler for handler in self.logger.handlers
                     if isinstance(handler, diagnostics._ModLogHandler)]
            self.assertEqual(len(owned), 1)
            self.logger.warning('One record')
            self.assertEqual(self.read(state).count('One record'), 1)
            state.close()
            state.close()
            self.assertIn(capture, self.logger.handlers)
            self.assertNotIn(state._handler, self.logger.handlers)
            self.assertEqual(logging.root.handlers, root_handlers)
            self.assertEqual(unrelated.handlers, other_handlers)
            self.assertEqual(self.logger.level, before)
            self.assertFalse(state.ok)
        finally:
            self.logger.removeHandler(capture)

    def test_rotation_is_bounded_and_utf8_content_remains_readable(self):
        state = self.start()
        state._handler.maxBytes = 220
        for index in range(30):
            self.logger.warning('row=%02d %s', index, 'żółć' * 5)
        names = [name for name in os.listdir(os.path.dirname(state.path))
                 if name.startswith('session-stats.log') and not name.endswith('.lock')]
        self.assertEqual(sorted(names), ['session-stats.log', 'session-stats.log.1',
                                         'session-stats.log.2', 'session-stats.log.3'])
        for name in names:
            path = os.path.join(os.path.dirname(state.path), name)
            self.assertLessEqual(os.path.getsize(path), 220)
            with io.open(path, encoding='utf-8') as handle:
                self.assertIn('żółć', handle.read())
        self.assertIn('row=29', self.read(state))

    def test_creation_failure_returns_status_without_adding_a_handler(self):
        blocker = os.path.join(self.directory, 'logs')
        with open(blocker, 'wb') as handle:
            handle.write(b'occupied')
        handlers = list(self.logger.handlers)
        state = self.start()
        self.assertFalse(state.ok)
        self.assertTrue(state.error)
        self.assertEqual(self.logger.handlers, handlers)
        state.flush()
        state.close()

    def test_failed_open_during_start_cannot_later_claim_an_unattached_log_works(self):
        original = diagnostics._ModLogHandler._open
        def fail(unused):
            raise IOError(errno.EACCES, 'private path must not be logged')
        try:
            diagnostics._ModLogHandler._open = fail
            state = self.start()
        finally:
            diagnostics._ModLogHandler._open = original
        self.assertFalse(state.ok)
        self.assertIsNone(state._handler)
        self.assertNotIn('private path', state.error)
        state.flush()
        self.assertFalse(state.ok)

    def test_write_failure_is_contained_and_queued_record_recovers_on_flush(self):
        state = self.start()
        original = state._handler._open
        def fail():
            raise IOError(errno.ENOSPC, 'raw account data must not leak')
        state._handler._open = fail
        self.logger.warning('health missing personal.vehicle.xp')
        self.assertFalse(state.ok)
        self.assertNotIn('raw account', state.error)
        self.assertEqual(len(state._handler.queue), 1)
        state._handler._open = original
        state.flush()
        self.assertTrue(state.ok)
        self.assertEqual(len(state._handler.queue), 0)
        self.assertEqual(self.read(state).count('health missing'), 1)

    def test_rotation_failure_does_not_escape_or_drop_the_pending_record(self):
        state = self.start()
        state._handler.maxBytes = 100
        self.logger.warning('initial')
        original = state._handler.doRollover
        def fail():
            raise OSError(errno.EACCES, 'another program locked the destination')
        state._handler.doRollover = fail
        self.logger.warning('new result warning after rollover threshold')
        self.assertFalse(state.ok)
        self.assertTrue(state._handler.queue)
        state._handler.doRollover = original
        state.flush()
        self.assertTrue(state.ok)
        self.assertIn('new result warning', self.read(state))

    def test_exception_values_are_omitted_locally_but_original_record_is_intact(self):
        capture = Capture()
        self.logger.addHandler(capture)
        try:
            state = self.start()
            try:
                raise ValueError('accountDBID=123456 nickname=PrivatePlayer token=secret')
            except ValueError:
                self.logger.exception('Bonus helper unavailable')
            text = self.read(state)
            self.assertIn('Bonus helper unavailable', text)
            self.assertIn('exception=ValueError', text)
            self.assertIn('test_diagnostics.py:', text)
            self.assertNotIn('123456', text)
            self.assertNotIn('PrivatePlayer', text)
            self.assertNotIn('token=secret', text)
            self.assertIn('PrivatePlayer', str(capture.records[-1].exc_info[1]))
            self.assertIsNone(capture.records[-1].exc_text)
        finally:
            self.logger.removeHandler(capture)

    @unittest.skipIf(os.name == 'nt', 'POSIX lock exercised here; Windows contract is separate')
    def test_other_process_lock_buffers_without_waiting_and_flush_reopens_current_log(self):
        import fcntl
        state = self.start()
        lock = open(state.path + '.lock', 'a+b')
        try:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.logger.warning('waiting for shared log')
            self.assertTrue(state.ok)
            self.assertEqual(len(state._handler.queue), 1)
            self.assertNotIn('waiting for shared log', self.read(state))
        finally:
            lock.close()
        os.rename(state.path, state.path + '.1')
        state.flush()
        self.assertTrue(state.ok)
        self.assertIn('waiting for shared log', self.read(state))
        with io.open(state.path + '.1', encoding='utf-8') as old:
            self.assertNotIn('waiting for shared log', old.read())

    @unittest.skipIf(os.name == 'nt', 'POSIX contention fixture')
    def test_contention_queue_is_bounded_and_overflow_is_reported_when_available(self):
        import fcntl
        state = self.start()
        lock = open(state.path + '.lock', 'a+b')
        try:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            for index in range(diagnostics.MAX_PENDING + 5):
                self.logger.warning('queued=%d', index)
            self.assertEqual(len(state._handler.queue), diagnostics.MAX_PENDING)
            self.assertTrue(state.ok)
        finally:
            lock.close()
        state.flush()
        self.assertIn('diagnostics.queue_overflow discarded=5', self.read(state))
        self.assertIn('queued=%d' % (diagnostics.MAX_PENDING + 4), self.read(state))

    def test_windows_lock_uses_nonblocking_one_byte_and_current_position_zero(self):
        original_name = diagnostics.os.name
        original = sys.modules.get('msvcrt')
        module = types.ModuleType(str('msvcrt'))
        module.LK_NBLCK, module.LK_UNLCK = 2, 0
        calls = []
        def locking(descriptor, mode, length):
            calls.append((mode, length, os.lseek(descriptor, 0, os.SEEK_CUR)))
        module.locking = locking
        try:
            diagnostics.os.name = 'nt'
            sys.modules['msvcrt'] = module
            state = self.start()
            self.logger.warning('Windows locking contract')
            self.assertTrue(state.ok)
            self.assertTrue(calls)
            self.assertTrue(all(mode in (2, 0) and length == 1 and position == 0
                                for mode, length, position in calls))
            self.assertIn('Windows locking contract', self.read(state))
        finally:
            diagnostics.os.name = original_name
            if original is None:
                sys.modules.pop('msvcrt', None)
            else:
                sys.modules['msvcrt'] = original

    def test_missing_windows_lock_extension_uses_process_private_rotating_log(self):
        original_name = diagnostics.os.name
        original_import = builtins.__import__
        def imports(name, *args, **kwargs):
            if name == 'msvcrt':
                raise ImportError('not shipped in embedded runtime')
            return original_import(name, *args, **kwargs)
        try:
            diagnostics.os.name = 'nt'
            builtins.__import__ = imports
            state = self.start()
            self.logger.warning('process-private fallback')
            self.assertTrue(state.ok)
            self.assertTrue(state.path.endswith('session-stats-%d.log' % os.getpid()))
            self.assertEqual(state._handler.backupCount, 3)
            self.assertIn('process-private fallback', self.read(state))
        finally:
            diagnostics.os.name = original_name
            builtins.__import__ = original_import


if __name__ == '__main__':
    unittest.main()
