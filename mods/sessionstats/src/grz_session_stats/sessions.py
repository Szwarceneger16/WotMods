# -*- coding: utf-8 -*-
"""Durable installation scope using the same transactional ledger as accounts."""
from __future__ import unicode_literals

import hashlib
import os
import sys

from .localization import message
from .combat_intake import installation_battle_id
from .installation_migration import InstallationHistory
from .normalize import text_type
from .storage import logical_data_path, native_data_path


def _physical_installation_path(path):
    if sys.platform != 'win32':
        return os.path.realpath(path)
    try:
        import ctypes
        from ctypes import wintypes
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        open_directory = kernel.CreateFileW
        final_path = kernel.GetFinalPathNameByHandleW
        close = kernel.CloseHandle
    except (ImportError, AttributeError):
        return os.path.realpath(path)
    open_directory.argtypes = (wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                               wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE)
    open_directory.restype = wintypes.HANDLE
    final_path.argtypes = (wintypes.HANDLE, wintypes.LPWSTR, wintypes.DWORD, wintypes.DWORD)
    final_path.restype = wintypes.DWORD
    close.argtypes = (wintypes.HANDLE,)
    close.restype = wintypes.BOOL
    # Metadata access only, all share modes, OPEN_EXISTING, BACKUP_SEMANTICS.
    handle = open_directory(path, 0, 7, None, 3, 0x02000000, None)
    if handle in (None, ctypes.c_void_p(-1).value):
        return os.path.realpath(path)
    try:
        buffer = ctypes.create_unicode_buffer(260)
        length = final_path(handle, buffer, len(buffer), 0)  # Normalized DOS or UNC path.
        if len(buffer) <= length <= 32768:
            buffer = ctypes.create_unicode_buffer(length)
            length = final_path(handle, buffer, len(buffer), 0)
        return buffer.value if 0 < length < len(buffer) else os.path.realpath(path)
    finally:
        close(handle)


def _installation_keys(root):
    if isinstance(root, bytes) and not isinstance(root, text_type):
        root = root.decode(sys.getfilesystemencoding() or 'utf-8')
    if not isinstance(root, text_type) or not os.path.isabs(root):
        raise ValueError('An absolute installation root is required.')
    path = native_data_path(root)
    canonical = logical_data_path(_physical_installation_path(path))
    # Python 2.7 resolved Windows junctions lexically. POSIX already used the
    # physical directory so there is no separate legacy spelling to migrate.
    observed = logical_data_path(os.path.abspath(path)) if sys.platform == 'win32' else canonical
    return (_installation_digest(canonical), _installation_digest(observed))


def _installation_digest(path):
    canonical = os.path.normcase(path)
    return 'installation:' + hashlib.sha256(canonical.encode('utf-8')).hexdigest()


def installation_key(root):
    return _installation_keys(root)[0]


class InstallationSession(object):
    def __init__(self, data_dir, root, launch_id, expected_table, now, started_at=None, deferred=False):
        key, alias = _installation_keys(root)
        directory = os.path.join(data_dir, 'installations')
        self.service = InstallationHistory(directory, key, alias, launch_id, expected_table,
                                           now=now, deferred=deferred, started_at=started_at)

    def accepts_installation(self, key):
        return (key == self.service.account_key or
                isinstance(key, text_type) and key in self.service._state.get('_installation_aliases', {}))

    battle_key = staticmethod(installation_battle_id)

    def knows_battle(self, identifier):
        return identifier in self.service._state['battles']

    def begin(self, account_key, context):
        fields = ('started_at', 'vehicle_id', 'map_id', 'vehicle_name',
                  'vehicle_tier', 'vehicle_type', 'map_name')
        metadata = dict((key, context.get(key)) for key in fields)
        if context.get('details'):
            metadata['details'] = context['details']
        arena_id = self.battle_key(account_key, context['arena_id'])
        return self.service.begin_battle(arena_id, mode='random', **metadata)

    def result(self, account_key, record, allow_new=False, before_commit=None):
        identifier = self.battle_key(account_key, record['arena_id'])
        record = self._installation_result(identifier, record, allow_new)
        return record is not None and self.service.record_result(record, before_commit=before_commit)

    def replay_capture(self, identifier, kind, capture, receipt):
        is_result = kind == 'result'
        record = capture['record']
        if is_result:
            record = self._installation_result(identifier, record, capture['observed'])
            if record is None:
                return False
        else:
            record = dict(record, arena_id=identifier)
        return self.service.replay_combat_capture(
            record, capture['at'], capture['launch_id'], is_result=is_result, receipt=receipt)

    def _installation_result(self, identifier, record, allow_new):
        # An old result first delivered here may belong to another installation.
        # Accept known beginnings or a battle observed by this runtime only.
        if not allow_new and not self.service.loading and not self.knows_battle(identifier):
            return None
        record = dict(record, arena_id=identifier)
        if record.get('_deferred_candidates'):
            record['_deferred_candidates'] = [dict(candidate, arena_id=identifier) for candidate in record['_deferred_candidates']]
        if self.service.loading and not allow_new:
            record['_require_known'] = True
        return record

    def snapshot(self):
        snapshot = self.service.snapshot()
        scope = snapshot['scopes']['manual']
        scope['label'] = message('scope.instance')
        scope['loading'] = snapshot.get('loading', False) or scope.get('loading', False)
        scope['load_error'] = snapshot.get('load_error')
        records = dict((row['id'], self.service.result_context(row['id'])) for row in scope['battles'])
        return scope, records, snapshot['warnings']

    def reset(self):
        return self.service.reset_manual()
