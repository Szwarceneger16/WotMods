# -*- coding: utf-8 -*-
"""Bounded, local diagnostics for this mod only (Python 2.7 and 3).

The normal game logger remains connected. A short nonblocking OS lock covers
reopen, rotation and writing so two clients never keep an old log generation
open across rotation. Embedded runtimes without a locking extension use a
private process filename instead. No account identifiers or raw results are
added here; exception messages/source lines are omitted from this local log.
"""
from __future__ import absolute_import, unicode_literals

from .localization import message

from collections import deque
import copy
import errno
import logging
from logging.handlers import RotatingFileHandler
import os
import sys
import time
import traceback

from . import VERSION

MAX_LOG_BYTES = 1024 * 1024
BACKUP_COUNT = 3
MAX_PENDING = 32
MAX_RECORD_CHARS = 4096
LOGGER_NAME = 'grz.sessionstats'
_active = {}
_previous_level = None

try:
    text_type = unicode
except NameError:
    text_type = str


class _LocalFormatter(logging.Formatter):
    converter = time.gmtime

    def formatException(self, info):
        # A changed client API can include a full result, nickname or account
        # ID in its exception text. Keep useful locations and class, not values.
        frames = traceback.extract_tb(info[2])[-8:]
        locations = ' > '.join('%s:%s:%s' % (os.path.basename(path), line, name)
                               for path, line, name, unused_source in frames)
        return 'exception=%s frames=%s' % (info[0].__name__, locations)

    def format(self, record):
        local = copy.copy(record)
        def decoded(value):
            if isinstance(value, bytes) and not isinstance(value, text_type):
                return value.decode('utf-8', 'replace')
            return value
        local.msg = decoded(local.msg)
        if isinstance(local.args, tuple):
            local.args = tuple(decoded(value) for value in local.args)
        elif isinstance(local.args, dict):
            local.args = dict((key, decoded(value)) for key, value in local.args.items())
        local.exc_text = None
        local.stack_info = None
        local.mod_version = VERSION
        message = super(_LocalFormatter, self).format(local)
        if len(message) > MAX_RECORD_CHARS:
            message = message[:MAX_RECORD_CHARS] + ' [truncated]'
        return message


class _Lock(object):
    def __init__(self, path, module, windows):
        self.path, self.module, self.windows = path, module, windows
        self.handle = None
        self.acquired = False

    def __enter__(self):
        self.handle = open(self.path, 'a+b')
        try:
            if self.windows:
                if not os.fstat(self.handle.fileno()).st_size:
                    self.handle.write(b'0')
                    self.handle.flush()
                self.handle.seek(0)
                self.module.locking(self.handle.fileno(), self.module.LK_NBLCK, 1)
            else:
                self.module.flock(self.handle.fileno(), self.module.LOCK_EX | self.module.LOCK_NB)
            self.acquired = True
        except (IOError, OSError) as error:
            if error.errno not in (errno.EACCES, errno.EAGAIN, errno.EDEADLK):
                self.handle.close()
                self.handle = None
                raise
        except Exception:
            self.handle.close()
            self.handle = None
            raise
        return self

    def __exit__(self, *unused):
        if self.handle is not None:
            try:
                if self.acquired:
                    if self.windows:
                        self.handle.seek(0)
                        self.module.locking(self.handle.fileno(), self.module.LK_UNLCK, 1)
                    else:
                        self.module.flock(self.handle.fileno(), self.module.LOCK_UN)
            finally:
                self.handle.close()


class _ModLogHandler(RotatingFileHandler):
    def __init__(self, path, lock_module=None, windows=False):
        super(_ModLogHandler, self).__init__(path, maxBytes=MAX_LOG_BYTES,
                                            backupCount=BACKUP_COUNT,
                                            encoding='utf-8', delay=True)
        self.lock_module = lock_module
        self.windows = windows
        self.queue = deque()
        self.error = None
        self.dropped = 0
        self._unreported_drops = 0
        self.stopped = False
        self._probed = False
        self.setLevel(logging.INFO)
        self.setFormatter(_LocalFormatter(
            '%(asctime)sZ %(levelname)s [v%(mod_version)s] %(message)s',
            datefmt='%Y-%m-%dT%H:%M:%S'))

    def _write_pending(self):
        # All processes close before releasing the lock: Windows can rename,
        # and the next writer reopens the current filename after any rotation.
        self.stream = self._open()
        try:
            if self._unreported_drops:
                record = logging.LogRecord(LOGGER_NAME, logging.WARNING, '', 0,
                    'diagnostics.queue_overflow discarded=%d', (self._unreported_drops,), None)
                self.queue.appendleft(self.format(record))
                self._unreported_drops = 0
            while self.queue:
                message = self.queue[0] + '\n'
                size = os.path.getsize(self.baseFilename)
                if size and size + len(message.encode('utf-8')) > self.maxBytes:
                    self.doRollover()
                    self.stream = self._open()
                self.stream.write(message)
                self.stream.flush()
                self.queue.popleft()
            self.error = None
            self._probed = True
        finally:
            stream, self.stream = self.stream, None
            if stream is not None:
                stream.close()

    def flush(self):
        if self.stopped or (self._probed and not self.queue and self.error is None):
            return
        self.acquire()
        try:
            if self.lock_module is None:
                self._write_pending()
            else:
                with _Lock(self.baseFilename + '.lock', self.lock_module, self.windows) as lock:
                    if lock.acquired:
                        self._write_pending()
                    # Contention is temporary; keep the bounded queue and the
                    # last real error status until a later tick can flush it.
        except Exception as error:
            self.error = message('log.write').format(type(error).__name__)
        finally:
            self.release()

    def emit(self, record):
        if self.stopped:
            return
        try:
            if len(self.queue) >= MAX_PENDING:
                self.queue.popleft()
                self.dropped += 1
                self._unreported_drops += 1
            self.queue.append(self.format(record))
            self.flush()
        except Exception as error:
            # Never delegate to handleError(): logging.raiseExceptions in the
            # host must not print a raw record or leak this failure to the UI.
            self.error = message('log.prepare').format(type(error).__name__)

    def close(self):
        self.flush()
        self.stopped = True
        try:
            super(_ModLogHandler, self).close()
        except Exception as error:
            self.error = message('log.close').format(type(error).__name__)


class LogState(object):
    def __init__(self, path=None, error=None):
        self.path = path
        self._error = error
        self._handler = None
        self._key = None
        self._closed = False

    @property
    def ok(self):
        return not self._closed and self._handler is not None and self.error is None

    @property
    def error(self):
        return self._error or (self._handler.error if self._handler is not None else None)

    def flush(self):
        if not self._closed and self._handler is not None:
            self._handler.flush()

    def close(self):
        global _previous_level
        if self._closed:
            return
        self._closed = True
        logger = logging.getLogger(LOGGER_NAME)
        if self._handler is not None:
            logger.removeHandler(self._handler)
            self._handler.close()
        if _active.get(self._key) is self:
            _active.pop(self._key, None)
        if not _active and _previous_level is not None:
            # Preserve a later explicit configuration change by the host.
            if logger.level == logging.INFO:
                logger.setLevel(_previous_level)
            _previous_level = None


def start_logging(data_dir):
    """Return an idempotent local log state; failures never stop statistics.

    flush() is cheap when idle and should also be called by the existing
    runtime tick, so a single health warning queued during contention is saved.
    Only this mod's logger/handler is configured; root handlers and propagation
    are untouched. A missing OS locking extension uses a process-private log.
    """
    global _previous_level
    state = LogState()
    try:
        if isinstance(data_dir, bytes) and not isinstance(data_dir, text_type):
            data_dir = data_dir.decode(sys.getfilesystemencoding() or 'utf-8')
        directory = os.path.join(os.path.abspath(data_dir), 'logs')
        state.path = os.path.join(directory, 'session-stats.log')
        state._key = os.path.normcase(state.path)
        existing = _active.get(state._key)
        if existing is not None and not existing._closed:
            return existing
        if not os.path.isdir(directory):
            try:
                os.makedirs(directory, 0o700)
            except OSError as error:
                if error.errno != errno.EEXIST or not os.path.isdir(directory):
                    raise
        windows = os.name == 'nt'
        try:
            if windows:
                import msvcrt as lock_module
            else:
                import fcntl as lock_module
        except ImportError:
            lock_module = None
            state.path = os.path.join(directory, 'session-stats-%d.log' % os.getpid())
        state._handler = _ModLogHandler(state.path, lock_module, windows)
        state._handler.flush()  # Probe the destination without exposing data.
        if state._handler.error:
            state._error = state._handler.error
            state._handler.close()
            state._handler = None
            return state
        logger = logging.getLogger(LOGGER_NAME)
        if not _active:
            _previous_level = logger.level
        if logger.level == logging.NOTSET or logger.level > logging.INFO:
            logger.setLevel(logging.INFO)
        logger.addHandler(state._handler)
        _active[state._key] = state
        return state
    except Exception as error:
        state._error = message('log.start').format(type(error).__name__)
        return state
