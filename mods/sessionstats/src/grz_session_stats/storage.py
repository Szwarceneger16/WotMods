# -*- coding: utf-8 -*-
"""Crash-safe, game-independent JSON generations (Python 2.7 and Python 3).

The final filename is a commit marker.  It is never overwritten: a flushed,
validated temporary file is renamed to a fresh name on the same filesystem.
Readers validate checksums and can recover a previous complete generation.
"""
from __future__ import unicode_literals

from .localization import message

import errno
import hashlib
import json
import os
import re
import threading
import uuid

from .loading import complete, read_json_steps, digest_steps, depth_steps


SCHEMA_VERSION = 1
STORAGE_VERSION = 1
MAX_JSON_DEPTH = 64
MAX_SNAPSHOT_BYTES = 64 * 1024 * 1024
MAX_TRANSACTION_BYTES = 1024 * 1024
_JOURNAL_RE = re.compile(r'^[a-f0-9]{32}\.(?:json|log)$')
_GENERATION_RE = re.compile(r'^state-([0-9]{20})\.json$')
_PROCESS_LOCK = threading.RLock()


class StorageError(Exception):
    pass


class UnsupportedSchemaError(StorageError):
    pass


def canonical_bytes(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False).encode('utf-8')


def check_json_depth(value):
    """Bound external nesting before later encoders, copies or text conversion.

    Ledger/config structures are shallow; history length is not limited here.
    An iterative check also works when a newer decoder accepts deeper JSON.
    """
    pending = [(value, 0)]
    while pending:
        current, depth = pending.pop()
        if not isinstance(current, (dict, list)):
            continue
        if depth > MAX_JSON_DEPTH:
            raise ValueError('JSON nesting exceeds the supported data shape')
        children = current.values() if isinstance(current, dict) else current
        pending.extend((item, depth + 1) for item in children if isinstance(item, (dict, list)))


def _ensure_directory(directory):
    if not os.path.isdir(directory):
        try:
            os.makedirs(directory, 0o700)
        except OSError as error:
            if error.errno != errno.EEXIST or not os.path.isdir(directory):
                raise


def _create_file(path):
    return os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'wb')


class _WriteLock(object):
    """An OS-released lock: process crashes never leave a permanent lock."""

    def __init__(self, directory):
        self.path = os.path.join(directory, '.write.lock')
        self.handle = None
        self.platform = None
        self.fallback = False

    def __enter__(self):
        _PROCESS_LOCK.acquire()
        try:
            self.handle = open(self.path, 'a+b')
            if os.name == 'nt':
                try:
                    import msvcrt
                except ImportError:
                    # Some embedded runtimes omit the stdlib extension. Windows
                    # rename refuses to replace the fresh final filename, so a
                    # concurrent commit still fails instead of overwriting data.
                    self.fallback = True
                    return self
                self.platform = msvcrt
                self.handle.seek(0, os.SEEK_END)
                if self.handle.tell() == 0:
                    self.handle.write(b'0')
                    self.handle.flush()
                self.handle.seek(0)
                msvcrt.locking(self.handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                self.platform = fcntl
                fcntl.flock(self.handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except (IOError, OSError, ImportError):
            if self.handle is not None:
                self.handle.close()
            self.handle = None
            _PROCESS_LOCK.release()
            raise StorageError(message('storage.busy'))
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        try:
            if self.handle is not None:
                if os.name == 'nt' and self.platform is not None:
                    self.handle.seek(0)
                    self.platform.locking(self.handle.fileno(), self.platform.LK_UNLCK, 1)
                elif self.platform is not None:
                    self.platform.flock(self.handle.fileno(), self.platform.LOCK_UN)
        finally:
            try:
                if self.handle is not None:
                    self.handle.close()
            finally:
                _PROCESS_LOCK.release()


class StateDelta(dict):
    """Internal, explicit update; ordinary dictionaries remain full snapshots."""
    def __init__(self, fields, battles, periods=None):
        dict.__init__(self, schema_version=SCHEMA_VERSION, fields=fields, battles=battles, periods=periods or {})


class GenerationStore(object):
    def __init__(self, directory, schema_version=SCHEMA_VERSION, keep_generations=3):
        self.directory = directory
        self.schema_version = schema_version
        self.keep_generations = max(2, int(keep_generations))
        self.sequence = 0
        self._observed_generation = 0
        self.read_only = False
        self.warning = None
        self._journal_ref = None
        self._base_path = None
        self._writer_path = None
        self._writer_offset = 0

    def _files(self):
        if not os.path.isdir(self.directory):
            return []
        found = []
        for name in os.listdir(self.directory):
            match = _GENERATION_RE.match(name)
            if match:
                found.append((int(match.group(1)), os.path.join(self.directory, name)))
        return sorted(found, reverse=True)

    def _decode(self, path, generation, allow_journal=True, file_checksum=None):
        output = [None]
        complete(self._decode_steps(path, generation, output, allow_journal, file_checksum))
        return output[0]

    def _decode_steps(self, path, generation, output, allow_journal=True, file_checksum=None):
        box = [None]
        error = UnsupportedSchemaError('History exceeds the supported snapshot size; data is preserved.')
        for step in read_json_steps(path, getattr(self, 'snapshot_limit', MAX_SNAPSHOT_BYTES), error, box):
            yield step
        envelope, raw_checksum, raw_size = box[0]
        if not isinstance(envelope, dict):
            raise ValueError('invalid envelope')
        if envelope.get('storage_version') not in (STORAGE_VERSION, 2):
            raise UnsupportedSchemaError(message('storage.format'))
        if envelope.get('generation') != generation:
            raise ValueError('generation mismatch')
        payload = envelope.get('payload')
        if not isinstance(payload, dict):
            raise ValueError('invalid payload')
        if payload.get('schema_version') != self.schema_version:
            raise UnsupportedSchemaError(message('storage.schema'))
        for step in depth_steps(payload, MAX_JSON_DEPTH):
            yield step
        if file_checksum is not None:
            if raw_checksum != file_checksum:
                raise ValueError('base file checksum mismatch')
        else:
            if raw_size <= 16384:
                box[0] = hashlib.sha256(canonical_bytes(payload)).hexdigest()
            else:
                for step in digest_steps(payload, box):
                    yield step
            if box[0] != envelope.get('payload_checksum'):
                raise ValueError('checksum mismatch')
        self._candidate_ref = None
        if envelope['storage_version'] == 2:
            if not allow_journal:
                raise UnsupportedSchemaError(message('storage.format'))
            for step in self._replay_steps(payload, output):
                yield step
            self._candidate_ref = payload
        else:
            self._base_checksum = raw_checksum
            output[0] = payload

    def _journal_path(self, name):
        if not isinstance(name, type(u'')) or not _JOURNAL_RE.match(name):
            raise ValueError('invalid journal name')
        return os.path.join(self.directory, 'journal', name)

    def _segment_steps(self, reference, output):
        path = self._journal_path(reference['journal'])
        offset = reference.get('offset')
        if isinstance(offset, bool) or not isinstance(offset, (int, type(2 ** 64))) or offset < 1:
            raise ValueError('invalid journal offset')
        for candidate in (path, path + '.bak'):
            try:
                with open(candidate, 'rb') as handle:
                    header = handle.readline(MAX_TRANSACTION_BYTES + 1)
                    if len(header) > MAX_TRANSACTION_BYTES or not header.endswith(b'\n'):
                        raise ValueError('invalid journal header')
                    digest = hashlib.sha256(header).hexdigest()
                    while handle.tell() < offset:
                        raw = handle.readline(min(MAX_TRANSACTION_BYTES + 1, offset - handle.tell()))
                        if not raw.endswith(b'\n') or len(raw) > MAX_TRANSACTION_BYTES:
                            raise ValueError('incomplete journal transaction')
                        digest = hashlib.sha256(digest.encode('ascii') + raw).hexdigest()
                        yield None
                    if handle.tell() != offset or digest != reference.get('checksum'):
                        raise ValueError('journal checksum mismatch')
                if candidate != path:
                    self.warning = message('storage.recovered')
                output[0] = (candidate, header)
                yield None
                return
            except (ValueError, IOError, OSError):
                continue
        raise StorageError(message('storage.corrupt'))

    def _replay_steps(self, reference, output):
        """Stream bounded transactions; no recursive JSON or dependency traversal."""
        segments, seen = [], set()
        while 'journal' in reference:
            name = reference['journal']
            if name in seen:
                raise ValueError('journal cycle')
            seen.add(name)
            box = [None]
            for step in self._segment_steps(reference, box):
                yield step
            path, raw = box[0]
            header = json.loads(raw.decode('utf-8'))
            check_json_depth(header)
            if header.get('journal_version') != 1:
                raise UnsupportedSchemaError(message('storage.format'))
            segments.append((path, reference, raw))
            reference = header['parent']
        path = self._journal_path(reference['base'])
        state = None
        for candidate in (path, path + '.bak'):
            try:
                # Bases must be v1, not recursive replay entry points.
                box = [None]
                for step in self._decode_steps(candidate, reference['generation'], box,
                                                allow_journal=False, file_checksum=reference.get('file_checksum')):
                    yield step
                state = box[0]
                if candidate != path:
                    self.warning = message('storage.recovered')
                break
            except UnsupportedSchemaError:
                raise
            except (StorageError, ValueError, TypeError, UnicodeError, IOError, OSError, RuntimeError, KeyError, IndexError, AttributeError, OverflowError):
                continue
        if state is None:
            raise StorageError(message('storage.corrupt'))
        for path, pointer, header in reversed(segments):
            digest = hashlib.sha256(header).hexdigest()
            with open(path, 'rb') as handle:
                handle.seek(len(header))
                while handle.tell() < pointer['offset']:
                    raw = handle.readline(min(MAX_TRANSACTION_BYTES + 1, pointer['offset'] - handle.tell()))
                    if not raw.endswith(b'\n') or len(raw) > MAX_TRANSACTION_BYTES:
                        raise ValueError('incomplete journal transaction')
                    patch = json.loads(raw.decode('utf-8'))
                    if patch.get('schema_version') != self.schema_version:
                        raise UnsupportedSchemaError(message('storage.schema'))
                    check_json_depth(patch)
                    fields, battles = patch['fields'], patch['battles']
                    if not isinstance(fields, dict) or not isinstance(battles, dict) or 'battles' in fields:
                        raise ValueError('invalid journal patch')
                    if fields.get('schema_version', self.schema_version) != self.schema_version:
                        raise UnsupportedSchemaError(message('storage.schema'))
                    state.update(fields)
                    for kind, change in patch.get('periods', {}).items():
                        if kind not in ('launch_sessions', 'manual_sessions'):
                            raise ValueError('invalid period update')
                        periods = state[kind]
                        length = change['length']
                        if isinstance(length, bool) or not isinstance(length, int) or not len(periods) <= length <= len(periods) + 1:
                            raise ValueError('invalid period length')
                        if length > len(periods):
                            periods.append(None)
                        for position, period in change['entries'].items():
                            position = int(position)
                            if not 0 <= position < length:
                                raise ValueError('invalid period position')
                            periods[position] = period
                        if periods and periods[-1] is None:
                            raise ValueError('missing period')
                    state['battles'].update(battles)
                    digest = hashlib.sha256(digest.encode('ascii') + raw).hexdigest()
                    yield None
                if handle.tell() != pointer['offset'] or digest != pointer['checksum']:
                    raise ValueError('journal checksum mismatch')
        output[0] = state

    def prepare(self):
        """Prepare immutable base/segment files during load, before live events."""
        if self.read_only or self._writer_path is not None:
            return
        with _WriteLock(self.directory):
            files = self._files()
            if not files or files[0][0] != self._observed_generation:
                raise StorageError(message('storage.changed'))
            self._prepare_journal()

    def _prepare_journal(self):
        complete(self._prepare_journal_steps())

    def prepare_steps(self):
        if self.read_only or self._writer_path is not None:
            return
        files = self._files()
        if not files or files[0][0] != self._observed_generation:
            raise StorageError(message('storage.changed'))
        # Only create exclusively owned, uncommitted files here. No OS lock is
        # held across callbacks. save() rechecks the generation under its lock.
        for step in self._prepare_journal_steps():
            yield step

    def _prepare_journal_steps(self):
        directory = os.path.join(self.directory, 'journal')
        _ensure_directory(directory)
        if self._writer_path is None:
            parent = self._journal_ref
            if parent is None:
                if self._base_path is None:
                    raise StorageError('An incremental update requires a committed snapshot.')
                name = uuid.uuid4().hex + '.json'
                path = self._journal_path(name)
                # Copy the already validated bytes once when upgrading v1. Do not
                # re-encode the complete battle history on the gameplay write path.
                checksum = None
                for candidate in (path, path + '.bak'):
                    digest = hashlib.sha256()
                    with open(self._base_path, 'rb') as source, _create_file(candidate) as target:
                        while True:
                            block = source.read(65536)
                            if not block:
                                break
                            digest.update(block)
                            target.write(block)
                            yield None
                        target.flush()
                        os.fsync(target.fileno())
                    if (getattr(self, '_base_checksum', digest.hexdigest()) != digest.hexdigest() or
                            (checksum is not None and checksum != digest.hexdigest())):
                        raise StorageError(message('storage.changed'))
                    checksum = digest.hexdigest()
                parent = {'base': name, 'generation': self.sequence, 'file_checksum': checksum}
            writer_path = self._journal_path(uuid.uuid4().hex + '.log')
            header = canonical_bytes({'journal_version': 1, 'parent': parent}) + b'\n'
            for candidate in (writer_path, writer_path + '.bak'):
                with _create_file(candidate) as handle:
                    handle.write(header)
                    handle.flush()
                    os.fsync(handle.fileno())
            self._writer_path = writer_path
            self._writer_offset = len(header)
            self._writer_checksum = hashlib.sha256(header).hexdigest()
            self._sync_directory(directory)

    def _append_delta(self, patch):
        encoded = canonical_bytes(patch) + b'\n'
        if len(encoded) > MAX_TRANSACTION_BYTES:
            raise StorageError('History update exceeds the supported transaction size; data is preserved.')
        self._prepare_journal()
        for path in (self._writer_path, self._writer_path + '.bak'):
            with open(path, 'r+b') as handle:
                handle.seek(self._writer_offset)
                handle.truncate()  # Only this writer's uncommitted tail; never shared data.
                handle.write(encoded)
                handle.flush()
                os.fsync(handle.fileno())
        return {'schema_version': self.schema_version,
                'journal': os.path.basename(self._writer_path),
                'offset': self._writer_offset + len(encoded),
                'checksum': hashlib.sha256(self._writer_checksum.encode('ascii') + encoded).hexdigest()}

    def load(self, validate=None):
        def validation(payload):
            if validate is not None:
                validate(payload)
            return iter(())
        output = [None]
        complete(self.load_steps(output, validation))
        return output[0]

    def load_steps(self, output, validate=None):
        """Select the newest generation accepted by storage and the caller.

        An optional application validator raises StorageError/ValueError for
        invalid known-schema payloads. UnsupportedSchemaError always stops
        selection, including when raised by the validator.
        """
        self.warning = None
        self._writer_path = None
        files = self._files()
        self._observed_generation = files[0][0] if files else 0
        damaged = 0
        for generation, path in files:
            try:
                box = [None]
                for step in self._decode_steps(path, generation, box):
                    yield step
                payload = box[0]
                if validate is not None:
                    for step in validate(payload):
                        yield step
            except UnsupportedSchemaError:
                self.read_only = True
                raise
            except (StorageError, ValueError, TypeError, UnicodeError, IOError, OSError, RuntimeError, KeyError, IndexError, AttributeError, OverflowError):
                # Python 2.7 reports decoder/encoder recursion as RuntimeError;
                # Python 3 RecursionError is its subclass. Try an older backup.
                damaged += 1
                continue
            self.sequence = generation
            self._journal_ref = self._candidate_ref
            self._base_path = path if self._journal_ref is None else None
            if damaged:
                self.warning = (message('storage.recovered'))
            output[0] = payload
            return
        if files:
            self.read_only = True
            raise StorageError(message('storage.corrupt'))
        self.sequence = 0
        output[0] = None

    def save(self, payload):
        if self.read_only:
            raise StorageError(message('storage.readonly'))
        if payload.get('schema_version') != self.schema_version:
            raise UnsupportedSchemaError(message('storage.unsupported_write'))
        committed = None
        try:
            check_json_depth(payload)
            _ensure_directory(self.directory)
            with _WriteLock(self.directory) as lock:
                if lock.fallback:
                    self.warning = (message('storage.no_lock'))
                files = self._files()
                on_disk = files[0][0] if files else 0
                if on_disk != self._observed_generation:
                    raise StorageError(message('storage.changed'))
                generation = on_disk + 1
                final_name = 'state-%020d.json' % generation
                final_path = os.path.join(self.directory, final_name)
                temporary = os.path.join(self.directory, '.%s-%s.tmp' % (final_name, uuid.uuid4().hex))
                delta = isinstance(payload, StateDelta)
                stored = self._append_delta(payload) if delta else payload
                envelope = {'storage_version': 2 if delta else STORAGE_VERSION,
                            'generation': generation,
                            'payload_checksum': hashlib.sha256(canonical_bytes(stored)).hexdigest(),
                            'payload': stored}
                encoded = canonical_bytes(envelope)
                try:
                    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                    with os.fdopen(descriptor, 'wb') as handle:
                        handle.write(encoded)
                        handle.flush()
                        os.fsync(handle.fileno())
                    if delta:
                        # Read back only the small commit descriptor. Replay is a
                        # startup/recovery operation, never a per-battle operation.
                        with open(temporary, 'rb') as handle:
                            if handle.read(len(encoded) + 1) != encoded:
                                raise StorageError(message('storage.failed'))
                    else:
                        self._decode(temporary, generation)
                    if os.path.exists(final_path):
                        raise StorageError(message('storage.collision'))
                    os.rename(temporary, final_path)
                    # Rename is the commit marker. A subsequent directory
                    # sync, backup cleanup or lock-release error must not make
                    # StatsService keep its old in-memory ledger and later
                    # overwrite this already accepted battle/reset.
                    committed = generation
                    self.sequence = generation
                    self._observed_generation = generation
                    if delta:
                        self._journal_ref = stored
                        self._writer_offset = stored['offset']
                        self._writer_checksum = stored['checksum']
                    else:
                        self._journal_ref = None
                        self._writer_path = None
                        self._base_path = final_path
                    self._sync_directory()
                finally:
                    if os.path.exists(temporary):
                        try:
                            os.unlink(temporary)
                        except OSError:
                            pass
                for unused_generation, path in files[self.keep_generations - 1:]:
                    try:
                        os.unlink(path)
                    except OSError:
                        # A failed old-backup cleanup does not undo a committed save.
                        pass
                return generation
        except StorageError:
            if committed is not None:
                return committed
            raise
        except (IOError, OSError, ValueError, TypeError, UnicodeError, RuntimeError):
            if committed is not None:
                return committed
            raise StorageError(message('storage.failed'))

    def _sync_directory(self, directory=None):
        if os.name == 'nt' or not hasattr(os, 'O_DIRECTORY'):
            return
        directory_fd = None
        try:
            directory_fd = os.open(directory or self.directory, os.O_RDONLY | os.O_DIRECTORY)
            os.fsync(directory_fd)
        except OSError:
            # Some filesystems do not support directory fsync. File fsync is required above.
            pass
        finally:
            if directory_fd is not None:
                os.close(directory_fd)
