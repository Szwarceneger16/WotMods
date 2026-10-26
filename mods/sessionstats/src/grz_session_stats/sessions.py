# -*- coding: utf-8 -*-
"""Durable installation scope using the same transactional ledger as accounts."""
from __future__ import unicode_literals

import hashlib
import os
import sys

from .localization import message
from .core import StatsService
from .normalize import text_type


def installation_key(root):
    if isinstance(root, bytes) and not isinstance(root, text_type):
        root = root.decode(sys.getfilesystemencoding() or 'utf-8')
    if not isinstance(root, text_type) or not os.path.isabs(root):
        raise ValueError('An absolute installation root is required.')
    canonical = os.path.normcase(os.path.realpath(root))
    return 'installation:' + hashlib.sha256(canonical.encode('utf-8')).hexdigest()


class InstallationSession(object):
    def __init__(self, data_dir, root, launch_id, expected_table, now, started_at=None, deferred=False):
        self.service = StatsService(os.path.join(data_dir, 'installations'),
                                    installation_key(root), launch_id, expected_table,
                                    now=now, deferred=deferred, started_at=started_at)

    @staticmethod
    def battle_key(account_key, arena_id):
        # Neither raw account IDs nor the physical installation path enter
        # the shared ledger. Account-aware keys prevent cross-account aliases.
        identity = text_type(account_key) + '\x00' + text_type(arena_id)
        return 'installation-' + hashlib.sha256(identity.encode('utf-8')).hexdigest()

    def begin(self, account_key, context):
        fields = ('started_at', 'vehicle_id', 'map_id', 'vehicle_name',
                  'vehicle_tier', 'vehicle_type', 'map_name')
        return self.service.begin_battle(self.battle_key(account_key, context['arena_id']),
                                         mode='random', **dict((key, context.get(key)) for key in fields))

    def result(self, account_key, record, allow_new=False):
        identifier = self.battle_key(account_key, record['arena_id'])
        # An old result first delivered here may belong to another installation.
        # Accept known beginnings or a battle observed by this runtime only.
        if not allow_new and not self.service.loading and identifier not in self.service._state['battles']:
            return False
        record = dict(record, arena_id=identifier)
        if record.get('_deferred_candidates'):
            record['_deferred_candidates'] = [dict(candidate, arena_id=identifier) for candidate in record['_deferred_candidates']]
        if self.service.loading and not allow_new:
            record['_require_known'] = True
        return self.service.record_result(record)

    def snapshot(self):
        snapshot = self.service.snapshot()
        scope = snapshot['scopes']['manual']
        scope['label'] = message('scope.instance')
        scope['loading'] = snapshot.get('loading', False)
        scope['load_error'] = snapshot.get('load_error')
        records = dict((row['id'], self.service.result_context(row['id'])) for row in scope['battles'])
        return scope, records, snapshot['warnings']

    def reset(self):
        return self.service.reset_manual()
