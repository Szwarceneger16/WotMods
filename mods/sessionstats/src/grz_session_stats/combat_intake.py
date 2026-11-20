# -*- coding: utf-8 -*-
"""Write detached battle receipts without waiting on the client thread."""
from __future__ import unicode_literals

from collections import Counter, deque, namedtuple
import errno
import hashlib
import json
import os
import re
import threading
import time
import uuid

from .normalize import text_type
from .storage import (GenerationStore, MAX_TRANSACTION_BYTES, _create_file,
                      _ensure_directory, canonical_bytes, check_json_depth)


_KINDS = ('begin', 'result')
_ACCOUNT = re.compile(r'^[a-f0-9]{64}\Z')
_FILENAME = re.compile(r'^([0-9]{20})-([a-f0-9]{32})\.json\Z')
_LAUNCH = re.compile(r'^[a-f0-9]{32}\Z')
_INSTALLATION = re.compile(r'^installation:[a-f0-9]{64}\Z')
_Receipt = namedtuple('_Receipt', ('account', 'filename'))
_RETRY_SECONDS = 1


def _account_folder(account_key):
    if not isinstance(account_key, text_type):
        account_key = account_key.decode('utf-8')
    return hashlib.sha256(account_key.encode('utf-8')).hexdigest()


def _validated_text(value, pattern):
    try:
        if isinstance(value, bytes) and not isinstance(value, text_type):
            value = value.decode('ascii')
    except UnicodeError:
        return None
    return value if isinstance(value, text_type) and pattern.match(value) else None


class CombatIntake(object):
    """FIFO writer and garage-only reader for normalized, account-local data.

    A submitted payload must be detached and belongs to this writer after
    submission. It is buffered immediately and recoverable after publication
    of its flushed file. Readers keep receipts until the ledger accepts them.
    """

    def __init__(self, data_dir):
        self._directory = os.path.join(data_dir, 'combat-intake')
        self._storage = GenerationStore(self._directory)
        self._condition = threading.Condition()
        self._queue = deque()
        self._waiting = Counter()
        self._thread = None
        self._closed = False
        self._failed = False
        self._last_id = 0
        self._producer = uuid.uuid4().hex

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
            self._last_id = max(self._last_id + 1, int(time.time() * 1000000))
            receipt = _Receipt(account, '%020d-%s.json' % (self._last_id, self._producer))
            self._queue.append((receipt, kind, payload))
            self._waiting[account] += 1
            self._condition.notify()
            return True

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
        while True:
            with self._condition:
                while not self._queue and not self._closed:
                    self._condition.wait()
                if not self._queue:
                    return
                receipt, kind, payload = self._queue[0]
            try:
                self._write(receipt, kind, payload)
            except (IOError, OSError):
                with self._condition:
                    self._failed = True
                    if not self._closed:
                        self._condition.wait(_RETRY_SECONDS)
                        continue
            except (ValueError, TypeError, UnicodeError, OverflowError, RuntimeError):
                self._mark_failed()
            with self._condition:
                self._queue.popleft()
                self._waiting[receipt.account] -= 1
                if not self._waiting[receipt.account]:
                    del self._waiting[receipt.account]

    def _write(self, receipt, kind, payload):
        envelope = {'version': 1, 'account': receipt.account, 'kind': kind, 'payload': payload}
        check_json_depth(envelope)
        encoded = canonical_bytes(envelope)
        if len(encoded) > MAX_TRANSACTION_BYTES - 65:
            raise ValueError('Combat receipt is too large.')
        checksum = hashlib.sha256(encoded).hexdigest().encode('ascii')
        directory = os.path.join(self._directory, receipt.account)
        _ensure_directory(directory)
        path = os.path.join(directory, receipt.filename)
        self._publish(path, checksum + b'\n' + encoded)

    def _publish(self, path, encoded):
        temporary = path + '.' + uuid.uuid4().hex + '.tmp'
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
        self._storage._sync_directory(os.path.dirname(path))

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
        account = _account_folder(account_key)
        directory = os.path.join(self._directory, account)
        try:
            filenames = sorted(name for name in os.listdir(directory) if _FILENAME.match(name))
        except OSError as error:
            if error.errno != errno.ENOENT:
                self._mark_failed()
            return []
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
            except (IOError, OSError) as error:
                if error.errno != errno.ENOENT:
                    self._mark_failed()
            except (ValueError, TypeError, UnicodeError, RuntimeError):
                self._mark_failed()
            else:
                if accept is None or accept(receipt, kind, payload):
                    result.append((receipt, kind, payload))
        return result

    def bind_installation(self, launch_id, installation_key):
        """Record the installation later identified for this launch in the garage."""
        launch_id = _validated_text(launch_id, _LAUNCH)
        installation_key = _validated_text(installation_key, _INSTALLATION)
        if launch_id is None or installation_key is None:
            return False
        path = os.path.join(self._directory, launch_id + '.installation')
        current = self.bound_installation(launch_id)
        if current is not None:
            return current == installation_key
        try:
            _ensure_directory(self._directory)
            self._publish(path, installation_key.encode('ascii'))
        except (IOError, OSError):
            if self.bound_installation(launch_id) != installation_key:
                self._mark_failed()
                return False
        return True

    def bound_installation(self, launch_id):
        launch_id = _validated_text(launch_id, _LAUNCH)
        if launch_id is None:
            return None
        path = os.path.join(self._directory, launch_id + '.installation')
        try:
            with open(path, 'rb') as handle:
                installation = _validated_text(handle.read(78), _INSTALLATION)
        except (IOError, OSError) as error:
            if error.errno != errno.ENOENT:
                self._mark_failed()
            return None
        if installation is None:
            self._mark_failed()
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
