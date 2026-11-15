# -*- coding: utf-8 -*-
"""Bounded account-local recovery hints, independent of the battle ledger.

These hints never establish a result or change statistics. GenerationStore gives
them the same checksum, backup and concurrent-writer protections as history.
"""
from __future__ import unicode_literals

import hashlib
import os

from .normalize import _number, text_type
from .storage import GenerationStore, StateDelta, StorageError

MAX_ENTRIES = 4096
MAX_ATTEMPTS = 1000000
MAX_DELAY = 86400.0
STATUSES = frozenset(('queued', 'in_flight', 'cooldown', 'rate_limited',
                      'not_ready', 'disconnected', 'unavailable', 'rejected',
                      'not_returned', 'partial_report', 'outcome_missing', 'complete'))
SOURCES = frozenset(('event', 'posted', 'refresh', 'cache', 'late_cache', 'native_cache', 'postbattle'))
CODES = frozenset((-14, -13, -10, -7, -6, -5, -4, -3, -2, -1, 0))
REASONS = frozenset(('invalid_container', 'invalid_common', 'unsupported_mode',
                    'missing_arena_id', 'invalid_personal', 'invalid_avatar',
                    'account_missing', 'wrong_account', 'missing_vehicle',
                    'vehicle_mismatch', 'malformed_structure', 'replay',
                    'winner_missing', 'team_missing', 'outcome_missing',
                    'missing_combat', 'missing_xp', 'missing_finance',
                    'never_received', 'complete', 'deferred_vehicle',
                    'timeout', 'request_failed', 'identity_mismatch', 'invalid_status'))


def valid_id(value):
    if isinstance(value, bytes) and not isinstance(value, text_type):
        try:
            value = value.decode('ascii')
        except UnicodeError:
            return False
    return (isinstance(value, text_type) and 1 <= len(value) <= 32 and
            all(char in '0123456789' for char in value) and int(value) > 0)


def clean_entry(entry):
    if not isinstance(entry, dict):
        raise ValueError('Invalid recovery entry')
    clean = {}
    for key in ('attempts', 'failures', 'unavailable_count'):
        number = _number(entry.get(key, 0))
        if number is None or not 0 <= number <= MAX_ATTEMPTS or int(number) != number:
            raise ValueError('Invalid recovery counter')
        clean[key] = int(number)
    for key in ('last_attempt', 'next_attempt'):
        number = _number(entry.get(key, 0))
        if number is None:
            raise ValueError('Invalid recovery time')
        clean[key] = number
    clean['status'] = entry.get('status') if entry.get('status') in STATUSES else 'queued'
    clean['code'] = entry.get('code') if entry.get('code') in CODES else None
    clean['source'] = entry.get('source') if entry.get('source') in SOURCES else None
    clean['reason'] = entry.get('reason') if entry.get('reason') in REASONS else None
    return clean


class RecoveryStore(object):
    def __init__(self, data_dir, account_key):
        self.account_key = account_key
        identity = hashlib.sha256(account_key.encode('utf-8')).hexdigest()
        self.store = GenerationStore(os.path.join(data_dir, identity, 'recovery')) if data_dir else None
        if self.store is not None:
            self.store.snapshot_limit = 2 * 1024 * 1024
        self.entries = {}
        self.pause_until = 0
        self.warning = False
        self._updates = 0
        self.evicted = ()
        if self.store is None:
            return
        try:
            payload = self.store.load(self._validate)
            if payload:
                self.entries = dict((key, clean_entry(value)) for key, value in
                                    payload['battles'].items() if value is not None)
                self.pause_until = payload.get('pause_until', 0)
        except (StorageError, ValueError, TypeError, IOError, OSError):
            # Corrupt hints must never damage or make battle history read-only.
            self.warning = True

    def _validate(self, payload):
        if payload.get('account_key') != self.account_key:
            raise ValueError('Recovery owner mismatch')
        entries = payload.get('battles')
        if not isinstance(entries, dict) or len(entries) > MAX_ENTRIES + 128:
            raise ValueError('Recovery limit exceeded')
        if _number(payload.get('pause_until', 0)) is None:
            raise ValueError('Invalid recovery pause')
        for key, value in entries.items():
            if not valid_id(key):
                raise ValueError('Invalid recovery identity')
            if value is not None:
                clean_entry(value)

    def put(self, arena_id, entry, pause_until=None):
        self.evicted = ()
        if not valid_id(arena_id):
            return False
        if isinstance(arena_id, bytes) and not isinstance(arena_id, text_type):
            arena_id = arena_id.decode('ascii')
        entry = clean_entry(entry)
        pause = self.pause_until if pause_until is None else pause_until
        if self.entries.get(arena_id) == entry and pause == self.pause_until:
            return False
        self.entries[arena_id] = entry
        self.pause_until = pause
        changes = {arena_id: entry}
        while len(self.entries) > MAX_ENTRIES:
            oldest = min(self.entries, key=lambda key: (
                self.entries[key]['status'] != 'complete',
                self.entries[key]['last_attempt'], key))
            self.entries.pop(oldest)
            changes[oldest] = None
            self.evicted += (oldest,)
        if self.store is None:
            return True
        try:
            if not self.store.sequence or self._updates >= 127:
                self.store.save({'schema_version': 1, 'account_key': self.account_key,
                                 'battles': self.entries, 'pause_until': pause})
                self._updates = 0
            else:
                self.store.save(StateDelta({'pause_until': pause}, changes))
                self._updates += 1
            self.warning = False
        except (StorageError, ValueError, TypeError, IOError, OSError):
            self.warning = True
        return True
