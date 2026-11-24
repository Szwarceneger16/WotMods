# -*- coding: utf-8 -*-
"""Write detached battle receipts without waiting on the client thread."""
from __future__ import unicode_literals

from collections import Counter, deque, namedtuple
from contextlib import contextmanager
import errno
import hashlib
import json
import os
import re
import threading
import time
import uuid

from .normalize import text_type
from .capture_order import CaptureClock
from .storage import (GenerationStore, MAX_TRANSACTION_BYTES, _create_file,
                      _ensure_directory, canonical_bytes, check_json_depth)


_KINDS = ('begin', 'result')
_ACCOUNT = re.compile(r'^[a-f0-9]{64}\Z')
_FILENAME = re.compile(r'^([0-9]{20})-([a-f0-9]{32})\.json\Z')
_LAUNCH = re.compile(r'^[a-f0-9]{32}\Z')
_INSTALLATION = re.compile(r'^installation:[a-f0-9]{64}\Z')
_INSTALLATION_BATTLE = re.compile(r'^installation-[a-f0-9]{64}\Z')
_Receipt = namedtuple('_Receipt', ('account', 'filename'))
_RETRY_SECONDS = 1
_SHUTDOWN_RETRY_SECONDS = 0.1
_LOCK_RETRY_SECONDS = 0.02
_SHUTDOWN_LOCK_RETRIES = 50


class _PublicationBusy(Exception):
    pass


@contextmanager
def _publication_lock(directory, filename='.receipt-write.lock'):
    """An exclusive process-owned lock released by the OS on exit."""
    path = os.path.join(directory, filename)
    if os.name == 'nt':
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_TEMPORARY | os.O_NOINHERIT
        try:
            descriptor = os.open(path, flags, 0o600)
        except OSError as error:
            if error.errno == errno.EEXIST:
                raise _PublicationBusy()
            raise
    else:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | getattr(os, 'O_CLOEXEC', 0), 0o600)
    try:
        if os.name != 'nt':
            import fcntl
            # Separate open descriptors contend even within one process. Keep
            # the inode in place so it continues to coordinate all writers.
            try:
                fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except (IOError, OSError) as error:
                if error.errno in (errno.EACCES, errno.EAGAIN, errno.EWOULDBLOCK):
                    raise _PublicationBusy()
                raise
        yield
    finally:
        # Windows deletes the temporary lock and POSIX releases flock.
        os.close(descriptor)


def _account_folder(account_key):
    if not isinstance(account_key, text_type):
        account_key = account_key.decode('utf-8')
    return hashlib.sha256(account_key.encode('utf-8')).hexdigest()


def installation_battle_id(account_key, arena_id):
    identity = text_type(account_key) + '\x00' + text_type(arena_id)
    return 'installation-' + hashlib.sha256(identity.encode('utf-8')).hexdigest()


def _validated_text(value, pattern):
    try:
        if isinstance(value, bytes) and not isinstance(value, text_type):
            value = value.decode('ascii')
    except UnicodeError:
        return None
    return value if isinstance(value, text_type) and pattern.match(value) else None


def captured_installation_battle(value):
    return _validated_text(value, _INSTALLATION_BATTLE)


class CombatIntake(object):
    """FIFO writer and garage-only reader for normalized, account-local data.

    A submitted payload must be detached and belongs to this writer after
    submission. It is buffered immediately and recoverable after publication
    of its flushed file. Readers keep receipts until the ledger accepts them.
    """

    def __init__(self, data_dir, launch_id=None):
        subdirectory = b'combat-intake' if isinstance(data_dir, bytes) else 'combat-intake'
        self._storage = GenerationStore(os.path.join(data_dir, subdirectory))
        self._directory = self._storage.directory
        self._condition = threading.Condition()
        self._queue = deque()
        self._waiting = Counter()
        self._thread = None
        self._closed = False
        self._failed = False
        self._last_id = 0
        self._producer = uuid.uuid4().hex
        self._launch_id = _validated_text(launch_id, _LAUNCH)
        self._clock = CaptureClock()

    @property
    def clock_domain(self):
        return self._clock.domain

    def capture_order(self):
        return self._clock.stamp()

    def account_transaction(self, account_key, create=False):
        """Share the receipt writer's lock with garage reads and direct commits."""
        return self.folder_transaction(_account_folder(account_key), create)

    @contextmanager
    def folder_transaction(self, account, create=False):
        if not _ACCOUNT.match(account):
            raise ValueError('Invalid combat receipt account.')
        directory = os.path.join(self._directory, account)
        lock = _publication_lock(directory)
        try:
            if create:
                _ensure_directory(directory)
            lock.__enter__()
        except _PublicationBusy:
            yield False
            return
        except (IOError, OSError) as error:
            if create or error.errno != errno.ENOENT:
                self._mark_failed()
            yield False
            return
        try:
            yield True
        finally:
            lock.__exit__(None, None, None)

    def launch_is_alive(self, launch_id):
        """An unbound capture is recoverable while its owner is still active."""
        launch = _validated_text(launch_id, _LAUNCH)
        if launch is None:
            return False
        try:
            with _publication_lock(self._directory, launch + '.live'):
                return False
        except _PublicationBusy:
            return True
        except (IOError, OSError) as error:
            if error.errno == errno.ENOENT:
                return False
            self._mark_failed()
            raise

    @property
    def failed(self):
        with self._condition:
            return self._failed

    def waiting(self, account_key):
        account = _account_folder(account_key)
        with self._condition:
            return self._waiting[account]

    def submit(self, account_key, kind, payload):
        if kind not in _KINDS or not isinstance(payload, dict):
            raise ValueError('Invalid combat receipt.')
        account = _account_folder(account_key)
        with self._condition:
            if self._closed:
                return False
            if self._thread is None:
                worker = threading.Thread(target=self._write_queue, name='SessionStats-combat-intake')
                worker.daemon = True
                try:
                    worker.start()
                except RuntimeError:
                    self._failed = True
                    return False
                self._thread = worker
            submitted_order = int(time.time() * 1000000)
            self._queue.append((account, submitted_order, kind, payload))
            self._waiting[account] += 1
            self._condition.notify()
            return True

    def persist_locked_result(self, account_key, payload):
        """Publish a garage result before the first ledger write, under its account lock."""
        try:
            receipt = self._next_receipt(_account_folder(account_key), int(time.time() * 1000000))
            self._write(receipt, 'result', payload)
            return receipt
        except (IOError, OSError, ValueError, TypeError, OverflowError, RuntimeError):
            self._mark_failed()
            return None

    def close(self, wait=False):
        with self._condition:
            self._closed = True
            self._condition.notify()
            worker = self._thread
        if wait and worker is not None:
            worker.join()

    def _mark_failed(self):
        with self._condition:
            self._failed = True

    def _write_queue(self):
        leases = []
        try:
            self._publish_queue(leases)
        finally:
            for lease in leases:
                lease.__exit__(None, None, None)

    def _publish_queue(self, leases):
        shutdown_retry = True
        shutdown_lock_retries = _SHUTDOWN_LOCK_RETRIES
        while True:
            with self._condition:
                while not self._queue and not self._closed:
                    self._condition.wait()
                if not self._queue:
                    return
                account, submitted_order, kind, payload = self._queue[0]
            try:
                directory = os.path.join(self._directory, account)
                _ensure_directory(directory)
                if self._launch_id is not None and not leases:
                    lease = _publication_lock(self._directory, self._launch_id + '.live')
                    lease.__enter__()
                    leases.append(lease)
                with _publication_lock(directory):
                    receipt = self._next_receipt(account, submitted_order)
                    self._write(receipt, kind, payload)
            except _PublicationBusy:
                with self._condition:
                    if not self._closed or shutdown_lock_retries:
                        if self._closed:
                            shutdown_lock_retries -= 1
                        self._condition.wait(_LOCK_RETRY_SECONDS)
                        continue
                    self._failed = True
            except (IOError, OSError):
                with self._condition:
                    self._failed = True
                    if not self._closed:
                        self._condition.wait(_RETRY_SECONDS)
                        continue
                    if shutdown_retry:
                        # Allow a final retry after a short lock without
                        # waiting repeatedly on an unavailable disk at exit.
                        shutdown_retry = False
                        self._condition.wait(_SHUTDOWN_RETRY_SECONDS)
                        continue
            except (ValueError, TypeError, UnicodeError, OverflowError, RuntimeError):
                self._mark_failed()
            with self._condition:
                self._queue.popleft()
                self._waiting[account] -= 1
                if not self._waiting[account]:
                    del self._waiting[account]

    def _next_receipt(self, account, submitted_order):
        filenames = self._receipt_filenames(account)
        with self._condition:
            if filenames:
                # Allocate after every visible receipt while publication is
                # locked, even when simultaneous or older clocks collide.
                self._last_id = max(self._last_id, int(_FILENAME.match(filenames[-1]).group(1)))
            self._last_id = max(self._last_id + 1, submitted_order)
            return _Receipt(account, '%020d-%s.json' % (self._last_id, self._producer))

    def _receipt_filenames(self, account):
        directory = os.path.join(self._directory, account)
        try:
            return sorted(name for name in os.listdir(directory) if _FILENAME.match(name))
        except OSError as error:
            if error.errno != errno.ENOENT:
                raise
            return []

    def _write(self, receipt, kind, payload):
        envelope = {'version': 1, 'account': receipt.account, 'kind': kind, 'payload': payload}
        check_json_depth(envelope)
        encoded = canonical_bytes(envelope)
        if len(encoded) > MAX_TRANSACTION_BYTES - 65:
            raise ValueError('Combat receipt is too large.')
        checksum = hashlib.sha256(encoded).hexdigest().encode('ascii')
        directory = os.path.join(self._directory, receipt.account)
        path = os.path.join(directory, receipt.filename)
        self._publish(path, checksum + b'\n' + encoded)

    def _publish(self, path, encoded):
        directory = os.path.dirname(path)
        temporary = os.path.join(directory, uuid.uuid4().hex + '.tmp')
        try:
            with _create_file(temporary) as handle:
                handle.write(encoded)
                handle.flush()
                os.fsync(handle.fileno())
            # Publish a new immutable name. Windows rename and POSIX hard
            # links both refuse to replace a marker another writer committed.
            if os.name == 'nt':
                os.rename(temporary, path)
            else:
                os.link(temporary, path)
        finally:
            try:
                os.remove(temporary)
            except OSError:
                pass
        self._storage._sync_directory(directory)

    @staticmethod
    def identity(receipt):
        """Return an account-specific writer id and its ordered sequence."""
        if not isinstance(receipt, _Receipt) or not _ACCOUNT.match(receipt.account):
            raise ValueError('Invalid combat receipt identity.')
        match = _FILENAME.match(receipt.filename)
        if match is None:
            raise ValueError('Invalid combat receipt identity.')
        order, producer = match.groups()
        identity = hashlib.sha256((receipt.account + ':' + producer).encode('ascii')).hexdigest()[:32]
        return text_type(identity), int(order)

    def pending(self, account_key, limit=1, skip=None, accept=None):
        """Read a bounded number of published receipts while in the garage."""
        return self.pending_in_folder(_account_folder(account_key), limit, skip, accept)

    account_folder = staticmethod(_account_folder)

    def published_folders(self):
        try:
            return [name for name in sorted(os.listdir(self._directory))
                    if _ACCOUNT.match(name) and self._receipt_filenames(name)]
        except OSError as error:
            if error.errno != errno.ENOENT:
                self._mark_failed()
            return []

    def pending_in_folder(self, account, limit=1, skip=None, accept=None):
        if not _ACCOUNT.match(account):
            raise ValueError('Invalid combat receipt account.')
        receipts, unused_blocked = self._pending(account, limit, skip, accept)
        return receipts

    def has_published(self, account_key):
        try:
            return bool(self._receipt_filenames(_account_folder(account_key)))
        except OSError:
            self._mark_failed()
            return False

    def has_backlog(self, account_key, accept=None):
        """Defer newer writes while an older receipt may still be replayed."""
        if self.waiting(account_key):
            return True
        receipts, blocked = self._pending(_account_folder(account_key), 1, None, accept)
        return bool(receipts) or blocked

    def _pending(self, account, limit, skip, accept):
        directory = os.path.join(self._directory, account)
        try:
            filenames = self._receipt_filenames(account)
        except OSError:
            self._mark_failed()
            return [], True
        result = []
        for filename in filenames:
            if len(result) >= limit:
                break
            receipt = _Receipt(account, filename)
            if skip is not None and skip(receipt):
                continue
            try:
                with open(os.path.join(directory, filename), 'rb') as handle:
                    raw = handle.read(MAX_TRANSACTION_BYTES + 1)
                checksum, separator, encoded = raw.partition(b'\n')
                if (len(raw) > MAX_TRANSACTION_BYTES or not separator or
                        hashlib.sha256(encoded).hexdigest().encode('ascii') != checksum):
                    raise ValueError('Invalid combat receipt checksum.')
                envelope = json.loads(encoded.decode('utf-8'))
                check_json_depth(envelope)
                if (not isinstance(envelope, dict) or envelope.get('version') != 1 or
                        envelope.get('account') != account or envelope.get('kind') not in _KINDS or
                        not isinstance(envelope.get('payload'), dict)):
                    raise ValueError('Invalid combat receipt.')
                kind, payload = envelope['kind'], envelope['payload']
                accepted = accept is None or accept(receipt, kind, payload)
            except (IOError, OSError) as error:
                if error.errno != errno.ENOENT:
                    self._mark_failed()
                # Another producer may revise the same battle. Recheck a
                # listed name before passing it, even if it disappeared.
                return result, True
            except (ValueError, TypeError, UnicodeError, RuntimeError):
                self._mark_failed()
            else:
                if accepted:
                    result.append((receipt, kind, payload))
        return result, False

    def bind_installation(self, launch_id, installation_key):
        """Record the installation later identified for this launch in the garage."""
        launch_id = _validated_text(launch_id, _LAUNCH)
        installation_key = _validated_text(installation_key, _INSTALLATION)
        if launch_id is None or installation_key is None:
            return False
        path = os.path.join(self._directory, launch_id + '.installation')
        try:
            current = self.bound_installation(launch_id)
            if current is not None:
                return current == installation_key
            _ensure_directory(self._directory)
            self._publish(path, installation_key.encode('ascii'))
        except (IOError, OSError):
            # Another process can publish the same immutable marker first.
            try:
                if self.bound_installation(launch_id) == installation_key:
                    return True
            except (IOError, OSError):
                pass
            self._mark_failed()
            return False
        return True

    def bound_installation(self, launch_id):
        """Return a verified binding or None when there is no marker."""
        launch_id = _validated_text(launch_id, _LAUNCH)
        if launch_id is None:
            return None
        path = os.path.join(self._directory, launch_id + '.installation')
        try:
            with open(path, 'rb') as handle:
                installation = _validated_text(handle.read(78), _INSTALLATION)
        except (IOError, OSError) as error:
            if error.errno == errno.ENOENT:
                return None
            self._mark_failed()
            raise
        if installation is None:
            self._mark_failed()
            raise IOError(errno.EINVAL, 'Invalid combat installation marker.')
        return installation

    def ack(self, receipt):
        """Remove the receipt only after the caller has committed its ledger."""
        if (not isinstance(receipt, _Receipt) or not _ACCOUNT.match(receipt.account) or
                not _FILENAME.match(receipt.filename)):
            return False
        directory = os.path.join(self._directory, receipt.account)
        try:
            os.remove(os.path.join(directory, receipt.filename))
        except OSError as error:
            if error.errno != errno.ENOENT:
                self._mark_failed()
                return False
        return True
