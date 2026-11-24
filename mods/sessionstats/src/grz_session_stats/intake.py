# -*- coding: utf-8 -*-
"""Durable startup receipts; committed ledger watermarks make replay idempotent."""
from __future__ import unicode_literals

import os
import re
import uuid

from .localization import message
from .storage import GenerationStore, StorageError, canonical_bytes

MAX_INTAKE_BYTES = 1024 * 1024
_TOKEN = re.compile(r'^[a-f0-9]{32}$')


class Intake(object):
    def __init__(self, directory, account_key):
        self.account_key = account_key
        self.store = GenerationStore(os.path.join(directory, 'startup-intake'))
        self.store.snapshot_limit = MAX_INTAKE_BYTES
        self.state = self.store.load(self.validate) or {
            'schema_version': 1, 'account_key': account_key, 'events': []}
        self.producer, self.sequence = uuid.uuid4().hex, 0

    def validate(self, state):
        if state.get('account_key') != self.account_key or not isinstance(state.get('events'), list):
            raise StorageError('Invalid startup intake; pending data is preserved.')
        previous = {}
        for event in state['events']:
            if (not isinstance(event, dict) or event.get('kind') not in ('open', 'begin', 'result') or
                    not isinstance(event.get('producer'), type(u'')) or not _TOKEN.match(event['producer']) or
                    isinstance(event.get('sequence'), bool) or not isinstance(event.get('sequence'), int) or
                    event['sequence'] <= previous.get(event['producer'], 0) or
                    not isinstance(event.get('launch_id'), type(u'')) or not event['launch_id']):
                raise StorageError('Invalid startup receipt; pending data is preserved.')
            previous[event['producer']] = event['sequence']

    @property
    def events(self):
        return self.state['events']

    def refresh(self):
        if self.store.changed_on_disk():
            state = self.store.load(self.validate)
            if state is None:
                raise StorageError(message('storage.changed'))
            self.state = state

    def _save(self, events):
        candidate = dict(self.state, events=events)
        # Include room for the storage envelope; never create a file that this
        # bounded intake reader would refuse to reopen.
        if len(canonical_bytes(candidate)) > MAX_INTAKE_BYTES - 1024:
            raise StorageError('Startup intake is full; this event was not accepted. Retry after loading.')
        self.store.save(candidate)
        self.state = candidate

    def _update(self, event, remove):
        for attempt in range(4):
            self.refresh()
            if remove:
                if event not in self.events:
                    return  # A peer already removed this acknowledged event.
                events = [saved for saved in self.events if saved != event]
            else:
                events = self.events + [event]
            try:
                self._save(events)
                return
            except StorageError:
                if attempt == 3 or not self.store.changed_on_disk():
                    raise

    def append(self, kind, launch_id, timestamp, record=None, context=None):
        event = {'producer': self.producer, 'sequence': self.sequence + 1,
                 'kind': kind, 'launch_id': launch_id, 'at': timestamp}
        if record is not None:
            event['record'] = record
        if context:
            event['context'] = context
        self._update(event, remove=False)
        self.sequence += 1
        return event

    def remove(self, event):
        self._update(event, remove=True)
