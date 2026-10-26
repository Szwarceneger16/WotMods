# -*- coding: utf-8 -*-
"""Local, bounded translation catalogs; no game or network dependency."""
from __future__ import absolute_import, unicode_literals

import copy
import io
import json
import logging
import os
import re
import string

from .language_defaults import ENGLISH, LEGACY_POLISH

LOG = logging.getLogger('grz.sessionstats')
FILENAME = 'grz.sessionstats.languages.json'
MAX_BYTES = 2 * 1024 * 1024
MAX_TEXT = 4096
LANGUAGE = re.compile(r'\A[a-z]{2,3}(?:-[A-Z]{2})?\Z')
CLIENT_LANGUAGE = re.compile(r'\A([a-zA-Z]{2,3})(?:[-_]([a-zA-Z]{2}))?\Z')
try:
    text_type = unicode
except NameError:
    text_type = str


def message(key):
    """Canonical English for durable warnings and runtime-independent services."""
    return ENGLISH[key]


def _fields(value):
    fields = []
    literal = re.sub(r'\{[0-9]\}', '', value)
    if '{' in literal or '}' in literal:
        raise ValueError('invalid_placeholder')
    for unused, field, spec, conversion in string.Formatter().parse(value):
        if field is not None:
            if not re.match(r'\A[0-9]\Z', field) or spec or conversion:
                raise ValueError('invalid_placeholder')
            fields.append(field)
    return sorted(fields)


def valid_text(key, value):
    if (not isinstance(value, text_type) or not value or len(value) > MAX_TEXT or
            any(ord(c) < 32 for c in value)):
        return False
    try:
        return _fields(value) == _fields(ENGLISH[key])
    except (ValueError, KeyError):
        return False


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate_key')
        result[key] = value
    return result


def _constant(unused):
    raise ValueError('non_finite_constant')


def decode(raw):
    if len(raw) > MAX_BYTES:
        raise ValueError('catalog_too_large')
    if isinstance(raw, bytes):
        raw = raw.decode('utf-8-sig')
    document = json.loads(raw, object_pairs_hook=_pairs, parse_constant=_constant)
    if (not isinstance(document, dict) or type(document.get('schema_version')) is not int or
            document['schema_version'] != 1 or not isinstance(document.get('languages'), dict)):
        raise ValueError('catalog_schema')
    result = {}
    invalid = False
    for language, entries in document['languages'].items():
        if not LANGUAGE.match(language) or not isinstance(entries, dict):
            invalid = True
            continue
        result[language] = {}
        for key, value in entries.items():
            if key in ENGLISH and valid_text(key, value):
                result[language][key] = value
            else:
                invalid = True
    if invalid:
        LOG.warning('I18N invalid catalog entries ignored; using per-message fallback.')
    return result


def _read(path):
    with io.open(path, 'rb') as stream:
        return decode(stream.read(MAX_BYTES + 1))


def bundled_catalog():
    try:
        import ResMgr
        section = ResMgr.openSection('grz_session_stats/languages.json')
        if section is not None:
            return decode(section.asBinary)
    except ImportError:
        pass
    except Exception:
        LOG.warning('I18N bundled resource unavailable; trying source defaults.')
    # Source checkout and source-bundle tools use the same canonical JSON.
    path = os.path.join(os.path.dirname(__file__), '..', '..', FILENAME)
    try:
        return _read(path)
    except (IOError, OSError, ValueError, TypeError, UnicodeError, RuntimeError):
        return {'en': dict(ENGLISH)}


def client_language_code(client_language):
    """Normalize only real locale codes, never silently alias an unknown locale."""
    if isinstance(client_language, bytes) and not isinstance(client_language, text_type):
        try:
            client_language = client_language.decode('ascii')
        except UnicodeError:
            return None
    if not isinstance(client_language, text_type):
        return None
    match = CLIENT_LANGUAGE.match(client_language)
    if match is None:
        return None
    base, region = match.groups()
    base = base.lower()
    return base + '-' + region.upper() if region else base


def select_language(configured, client_language, catalogs):
    """Explicit configuration wins; auto follows supported client locales."""
    if configured != 'auto':
        return configured if isinstance(configured, text_type) and configured in catalogs else 'en'
    code = client_language_code(client_language)
    if code is None:
        return 'en'
    base = code.split('-')[0]
    return code if code in catalogs else base if base in catalogs else 'en'


class Localizer(object):
    def __init__(self, language='en', path=None, catalog=None, client_language=None, native_messages=None):
        defaults = bundled_catalog() if catalog is None else catalog
        catalogs = copy.deepcopy(defaults)
        overrides = {}
        if path is not None:
            try:
                overrides = _read(path)
                for code, entries in overrides.items():
                    catalogs.setdefault(code, {}).update(entries)
            except (IOError, OSError, ValueError, TypeError, UnicodeError, RuntimeError):
                # Decoder recursion uses RuntimeError on Python 2.7 and its
                # RecursionError subclass on Python 3. Keep config independent.
                # Neither private file paths, JSON fragments nor values enter logs.
                LOG.warning('I18N external catalog unavailable; using bundled translations.')
        self.language = select_language(language, client_language, catalogs)
        if language != 'auto' and self.language != language:
            LOG.warning('I18N selected language unavailable; using English.')
        self.messages = dict(ENGLISH)
        self.messages.update(catalogs.get(self.language, {}))
        native_code = client_language_code(client_language)
        if native_code and self.language in (native_code, native_code.split('-')[0]):
            selected_overrides = overrides.get(self.language, {})
            for key in ('outcome.win', 'outcome.loss', 'outcome.draw'):
                # The installation ZIP includes a full editable catalog. Its
                # unchanged template entries must not mask the client's labels.
                if (key in selected_overrides and selected_overrides[key] !=
                        defaults.get(self.language, {}).get(key)):
                    continue
                value = native_messages.get(key) if isinstance(native_messages, dict) else None
                if isinstance(value, bytes) and not isinstance(value, text_type):
                    try:
                        value = value.decode('utf-8')
                    except UnicodeError:
                        continue
                if (valid_text(key, value) and len(value) <= 128 and
                        not value.startswith('#') and '<' not in value and '>' not in value):
                    self.messages[key] = value
        self._known = {}
        self._patterns = []
        # English strings remain canonical in saves. The original Polish strings
        # are recognized without rewriting or resetting any account history.
        for source in (ENGLISH, LEGACY_POLISH):
            for key, template in source.items():
                if not _fields(template):
                    self._known[template] = key
                    continue
                pattern, fields = [], []
                for literal, field, unused, unused_conversion in string.Formatter().parse(template):
                    pattern.append(re.escape(literal))
                    if field is not None:
                        fields.append(int(field))
                        pattern.append('(.*?)')
                self._patterns.append((re.compile('\\A' + ''.join(pattern) + '\\Z', re.S), key, fields))

    def text(self, key, *args):
        return self.messages[key].format(*args)

    def translate(self, value):
        if not isinstance(value, text_type):
            return value
        key = self._known.get(value)
        if key is not None:
            return self.messages[key]
        for pattern, key, fields in self._patterns:
            match = pattern.match(value)
            if match:
                args = [''] * (max(fields) + 1)
                for index, captured in zip(fields, match.groups()):
                    args[index] = self.translate(captured)
                return self.text(key, *args)
        return value

    def snapshot(self, snapshot):
        """Translate presentation fields only; never IDs or game-supplied names."""
        snapshot['localization'] = {'language': self.language, 'messages': dict(self.messages)}
        snapshot['warnings'] = [self.translate(value) for value in snapshot.get('warnings', [])]
        fallbacks = set(ENGLISH[key] for key in ('unknown.vehicle', 'unknown.map'))
        fallbacks.update(LEGACY_POLISH[key] for key in ('unknown.vehicle', 'unknown.map'))
        def is_fallback(value):
            return isinstance(value, text_type) and (value in fallbacks or any(
                pattern.match(value) for pattern, key, unused in self._patterns
                if key in ('unknown.vehicle_id', 'unknown.map_id')))
        for name, scope in snapshot.get('scopes', {}).items():
            scope['label'] = self.text('scope.' + name)
            for grouping in ('vehicles', 'maps', 'battles'):
                for row in scope.get(grouping, []):
                    for field in ('name', 'map'):
                        value = row.get(field)
                        if is_fallback(value):
                            row[field] = self.translate(row[field])
                    visual = row.get('visual')
                    outcome_visual = row.get('outcome_visual')
                    if isinstance(outcome_visual, dict) and row.get('outcome') in ('win', 'loss', 'draw'):
                        outcome_visual['alt'] = self.text('outcome.' + row['outcome'])
                    visual_names = (ENGLISH['visual.vehicle'], ENGLISH['visual.map'],
                                    LEGACY_POLISH['visual.vehicle'], LEGACY_POLISH['visual.map'])
                    if visual and (is_fallback(visual.get('alt')) or visual.get('alt') in visual_names):
                        visual['alt'] = self.translate(visual['alt'])
        return snapshot

    def footer_labels(self):
        return dict((key, self.messages[key]) for key in
                    ('footer.idle', 'footer.processing', 'footer.waiting', 'status.pending', 'metric.wn8'))
