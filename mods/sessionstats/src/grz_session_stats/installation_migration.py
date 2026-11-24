# -*- coding: utf-8 -*-
"""Adopt known legacy Windows installation aliases without changing their saves."""
from __future__ import unicode_literals

from bisect import bisect_right
from collections import deque
import copy
import hashlib
import os
import re

from .capture_order import compare_capture_order, valid_capture_order
from .core import (StatsService, _finalize_result, _merge_known, _metadata_gaps, _repair_result_metadata,
                   _restrict_unverified_facts, _text)
from .intake import Intake
from .loading import items
from .localization import message
from .normalize import text_type
from .storage import GenerationStore, StorageError


_ALIASES = '_installation_aliases'
_KEY = re.compile(r'^installation:[a-f0-9]{64}\Z')
_GENERATION_TYPES = (int, type(2 ** 64))


def _manual_periods(primary, legacy):
    first = min((primary[0], legacy[0]), key=lambda period: period['started_at'])
    resets = {}
    for period in legacy[1:] + primary[1:]:
        resets[period['started_at']] = period
    periods = [first] + [resets[stamp] for stamp in sorted(resets)]
    # Legacy files are untouched. The common history observes resets from
    # both views of the installation and assigns battles by their dates.
    return _ordered_periods(periods, next_boundary=True)


def _launch_periods(primary, legacy):
    by_id = dict((period['id'], period) for period in legacy + primary)
    periods = sorted(by_id.values(), key=lambda period: (period['started_at'], period['id']))
    return _ordered_periods(periods, next_boundary=False)


def _ordered_periods(periods, next_boundary):
    result = [dict(period) for period in periods]
    for previous, current in zip(result, result[1:]):
        boundary = current['started_at']
        last = min(StatsService._last_seen(previous), boundary)
        previous['last_seen_at'] = last
        previous['ended_at'] = boundary if next_boundary else min(previous.get('ended_at') or last, boundary)
    return result


def _merged_battle(primary, legacy):
    primary_order, legacy_order = primary.get('_capture_order'), legacy.get('_capture_order')
    primary_ordered, legacy_ordered = valid_capture_order(primary_order), valid_capture_order(legacy_order)
    if primary_ordered and legacy_ordered:
        use_legacy = compare_capture_order(primary_order, legacy_order, None) == -1
    else:
        # Local revision counters and wall clocks do not order results across
        # installations. An actual result can replace a recorded beginning.
        use_legacy = not primary.get('_result_seen') and legacy.get('_result_seen')
    newer, older = (legacy, primary) if use_legacy else (primary, legacy)
    other = dict(older)
    for field in ('_capture_order', '_launch_id', '_manual_id', 'revision', '_updated_at', 'warnings'):
        other.pop(field, None)
    _, _, arena_type_id = _metadata_gaps(newer)
    _restrict_unverified_facts(newer, other, arena_type_id)
    merged = _merge_known(newer, other)
    _repair_result_metadata(newer, other, merged, arena_type_id)
    # Observation of a beginning can prove its membership even when another
    # ledger holds the more authoritative result facts.
    for field in ('_launch_id', '_manual_id'):
        merged[field] = primary.get(field) or legacy.get(field)
    # An older bonus-aware reading stays authoritative for the applied XP.
    if other.get('xp_bonus_applied') and not newer.get('xp_bonus_applied') and other.get('xp_received') is not None:
        merged['xp_received'] = other['xp_received']
    merged['_result_seen'] = bool(primary.get('_result_seen') or legacy.get('_result_seen'))
    merged['_updated_at'] = max(primary.get('_updated_at', 0), legacy.get('_updated_at', 0))
    merged['revision'] = max(primary.get('revision', 0), legacy.get('revision', 0))
    if merged['_result_seen']:
        _finalize_result(merged)
    return merged


def _merge_history(primary, legacy, output):
    periods = _manual_periods(primary['manual_sessions'], legacy['manual_sessions'])
    starts = [period['started_at'] for period in periods]
    launches = _launch_periods(primary['launch_sessions'], legacy['launch_sessions'])
    battles = dict(primary['battles'])
    for arena, record in items(legacy['battles']):
        battles[arena] = _merged_battle(battles[arena], record) if arena in battles else record
        yield None
    for arena, record in items(battles):
        started = record.get('started_at')
        if started is None:
            manual = None
        else:
            index = bisect_right(starts, started) - 1
            # A live beginning is allowed to precede the first open period.
            manual = periods[max(0, index)]['id'] if index >= 0 or record.get('_manual_id') else None
        if manual != record.get('_manual_id'):
            battles[arena] = dict(record, _manual_id=manual)
        yield None
    receipts = dict(primary.get('_startup_receipts', {}))
    for producer, sequence in legacy.get('_startup_receipts', {}).items():
        receipts[producer] = max(sequence, receipts.get(producer, 0))
    output[0] = dict(primary, battles=battles, launch_sessions=launches, manual_sessions=periods,
                     current_manual_id=periods[-1]['id'], _startup_receipts=receipts)


class InstallationHistory(StatsService):
    def __init__(self, directory, key, observed, launch_id, expected_table, **kwargs):
        self._alias_key = observed if observed != key else None
        super(InstallationHistory, self).__init__(directory, key, launch_id, expected_table, **kwargs)

    def _validate_state_steps(self, state):
        aliases = state.get(_ALIASES, {})
        if not isinstance(aliases, dict):
            raise StorageError(message('core.ledger'))
        for key, generations in items(aliases):
            if (not isinstance(key, text_type) or not _KEY.match(key) or key == self.account_key or
                    not isinstance(generations, list) or len(generations) != 2 or
                    any(type(value) not in _GENERATION_TYPES or value < 0 for value in generations)):
                raise StorageError(message('core.ledger'))
        for step in super(InstallationHistory, self)._validate_state_steps(state):
            yield step

    def _validate_alias(self, state):
        if state.get('account_key') != self._alias_key:
            raise StorageError(message('core.account'))
        # Validate the entire application schema before changing identity.
        return super(InstallationHistory, self)._validate_state_steps(dict(state, account_key=self.account_key))

    def _new_migration_state(self, timestamp):
        state = self._empty_state(timestamp)
        # Match the on-disk Unicode form before validating an unpublished
        # Python 2 snapshot. uuid.hex is a byte string on that runtime.
        manual = _text(state['current_manual_id'])
        state['current_manual_id'] = manual
        state['manual_sessions'][0]['id'] = manual
        return state

    def _read_archived_intake(self, directory, archive, output):
        try:
            intake = Intake(directory, self._alias_key)
            if intake.store.warning:
                self._warnings.append(intake.store.warning)
            if not intake.events:
                output[:] = [archive, intake.store.sequence]
                return
            # Replay on the alias' own timeline and watermarks. Copy all battle
            # dictionaries that the usual replay path can revise in place.
            replay = copy.copy(self)
            replay.account_key = self._alias_key
            replay._indexes = None
            replay._intake = _ArchivedReceipts(intake.events)
            replay.store = _UnpublishedGeneration()
            if archive is None:
                replay._state = replay._new_migration_state(intake.events[0].get('at'))
            else:
                replay._state = dict(archive, battles={})
                for arena, battle in items(archive['battles']):
                    replay._state['battles'][arena] = dict(battle)
                    yield None
            for step in replay._drain_intake_steps():
                yield step
            for step in self._validate_alias(replay._state):
                yield step
            output[:] = [replay._state, intake.store.sequence]
        except (StorageError, IOError, OSError, KeyError, TypeError, ValueError, OverflowError):
            if archive is None:
                raise StorageError(message('storage.corrupt'))
            self._warnings.append(message('storage.corrupt'))
            # Keep the invalid source intact and still adopt its valid ledger.
            output[:] = [archive, 0]

    def _adopt_alias(self):
        folder = hashlib.sha256(self._alias_key.encode('ascii')).hexdigest()
        legacy = GenerationStore(os.path.join(os.path.dirname(self.store.directory), folder))
        startup = GenerationStore(os.path.join(legacy.directory, 'startup-intake'))
        for attempt in range(3):
            current = [None]
            for step in self.store.load_steps(current, self._validate_state_steps):
                yield step
            primary = current[0]
            aliases = dict((primary or {}).get(_ALIASES, {}))
            observed = [_latest_generation(legacy), _latest_generation(startup)]
            known = aliases.get(self._alias_key)
            if known is not None and all(next_value <= previous for next_value, previous in zip(observed, known)):
                return
            saved = [None]
            try:
                for step in legacy.load_steps(saved, self._validate_alias):
                    yield step
            except StorageError as error:
                if primary is None:
                    raise
                self._warnings.append(_text(error))
            archive = saved[0]
            if legacy.warning:
                self._warnings.append(legacy.warning)
            recovered = [archive, 0]
            if observed[1]:
                for step in self._read_archived_intake(legacy.directory, archive, recovered):
                    yield step
            archive, startup_generation = recovered
            generations = [legacy.sequence if saved[0] else 0, startup_generation]
            aliases[self._alias_key] = [max(old, new) for old, new in zip(known or [0, 0], generations)]
            if archive is not None and primary is not None:
                for step in _merge_history(primary, archive, current):
                    yield step
            elif archive is not None:
                current[0] = dict(archive, account_key=self.account_key)
            elif primary is None:
                current[0] = self._new_migration_state(self._initial_time)
            candidate = dict(current[0])
            candidate[_ALIASES] = aliases
            for step in self._validate_state_steps(candidate):
                yield step
            try:
                self.store.save(candidate)
                return
            except StorageError:
                if attempt == 2 or not self.store.changed_on_disk():
                    raise
                # Another client wrote a valid generation while we read the
                # alias. Retry from that generation instead of replacing it.
                yield None

    def _initialize_generation_steps(self):
        if self._alias_key is not None:
            for step in self._adopt_alias():
                yield step
        for step in super(InstallationHistory, self)._initialize_generation_steps():
            yield step


def _latest_generation(store):
    files = store._files()
    return files[0][0] if files else 0


class _ArchivedReceipts(object):
    def __init__(self, events):
        self.events = deque(events)

    def remove(self, event):
        self.events.popleft()


class _UnpublishedGeneration(object):
    sequence = 1

    def save(self, payload):
        # StatsService can acknowledge its detached copy. Only the final
        # canonical merge writes a generation to disk.
        pass
