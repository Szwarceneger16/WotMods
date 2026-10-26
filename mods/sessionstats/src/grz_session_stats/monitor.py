# -*- coding: utf-8 -*-
"""Bounded result diagnostics and notification batching, independent of WoT UI."""
from __future__ import absolute_import, unicode_literals

from .localization import message

import logging
import re

LOG = logging.getLogger('grz.sessionstats')
NOTICE_INTERVAL = 60.0
MAX_SIGNATURES = 256

try:
    text_type = unicode
except NameError:
    text_type = str


def _safe(value, limit=160):
    # Only schema labels reach this boundary, never a result value or repr.
    if isinstance(value, bytes) and not isinstance(value, text_type):
        value = value.decode('utf-8', 'replace')
    if not isinstance(value, text_type):
        value = type(value).__name__
    return re.sub(r'[^a-zA-Z0-9_.*<>\[\](): /,+=-]', '?', value)[:limit]


def _escape(value):
    # Only text nodes enter the native rich-text message; avoid importing an
    # XML parser and its optional dependencies into the embedded client.
    return value.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


class ResultMonitor(object):
    def __init__(self, now, log_path=None):
        self.now = now
        self.log_path = log_path
        self._seen = set()
        self._queued = []
        self._last_notice = None
        self._notice_failed = False
        self._overflow = False

    @property
    def has_problems(self):
        return bool(self._seen)

    def check(self, results, context, random_bonus_type, source):
        try:
            from .health import inspect_result
            issues = inspect_result(results, context, random_bonus_type)
        except Exception:
            # A monitor must not disable otherwise usable statistics.
            issues = [{'code': 'validator_unavailable', 'path': 'healthcheck',
                       'expected': 'working result validator', 'actual': 'exception'}]
            LOG.exception('Result healthcheck could not inspect the client response.')
        self.report(issues, source)
        return issues

    def fault(self, code, path, expected, actual, source='client'):
        return self.report([{'code': code, 'path': path, 'expected': expected,
                             'actual': actual}], source)

    def report(self, issues, source):
        for issue in issues:
            signature = tuple(_safe(issue.get(key, 'unknown'))
                              for key in ('code', 'path', 'expected', 'actual'))
            if signature in self._seen:
                continue
            if len(self._seen) >= MAX_SIGNATURES:
                if not self._overflow:
                    self._overflow = True
                    LOG.warning('HEALTHCHECK additional distinct changes omitted after %s signatures.', MAX_SIGNATURES)
                    if 'additional_changes' not in self._queued:
                        self._queued.append('additional_changes')
                break
            self._seen.add(signature)
            code, path, expected, actual = signature
            LOG.warning('HEALTHCHECK source=%s code=%s path=%s expected=%s actual=%s',
                        _safe(source, 32), code, path, expected, actual)
            if path not in self._queued and len(self._queued) < 8:
                self._queued.append(path)

    def flush_notice(self, notify, escape=True):
        if not self._queued:
            return False
        now = self.now()
        if self._last_notice is not None and now - self._last_notice < NOTICE_INTERVAL:
            return False
        self._last_notice = now
        fields = ', '.join(self._queued[:3])
        if len(self._queued) > 3:
            fields += ', ...'
        location = self.log_path or message('health.log')
        notice = message('health.notice').format(_escape(fields) if escape else fields,
                                                _escape(location) if escape else location)
        try:
            # Existing integrations may return None after a successful push.
            if notify(notice) is False:
                raise RuntimeError('Native notification unavailable')
        except Exception:
            if not self._notice_failed:
                LOG.warning('Could not show the result healthcheck warning in native notifications.')
                self._notice_failed = True
            return False
        self._queued = []
        self._notice_failed = False
        return True

    def warning(self):
        if not self.has_problems:
            return None
        return (message('health.warning'))
