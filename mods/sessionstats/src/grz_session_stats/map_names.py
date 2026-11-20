# -*- coding: utf-8 -*-
"""Bounded offline names from the client's verified arena catalogues."""
from __future__ import absolute_import, unicode_literals

import io
import json
import os
import re

try:
    text_type = unicode
except NameError:
    text_type = str

LANGUAGES = ('en', 'pl', 'ru', 'fr', 'de', 'es', 'uk')
MAX_BYTES = 128 * 1024
GEOMETRY = re.compile(r'\A[0-9]+_[a-z0-9_-]{1,120}\Z')


def decode(raw):
    if len(raw) > MAX_BYTES:
        raise ValueError('map_catalog_too_large')
    if isinstance(raw, bytes):
        raw = raw.decode('utf-8')
    document = json.loads(raw)
    if (not isinstance(document, dict) or type(document.get('schema_version')) is not int or
            document['schema_version'] != 1 or not isinstance(document.get('maps'), dict) or
            len(document['maps']) > 256):
        raise ValueError('map_catalog_schema')
    result = {}
    for identifier, names in document['maps'].items():
        if not isinstance(identifier, text_type) or not GEOMETRY.match(identifier) or not isinstance(names, dict):
            continue
        values = dict((language, value) for language, value in names.items()
                      if language in LANGUAGES and isinstance(value, text_type) and 0 < len(value) <= 128 and
                      not any(ord(char) < 32 for char in value) and not any(char in value for char in '<>{}'))
        if values.get('en'):
            result[identifier] = values
    return result


def bundled_names():
    try:
        import ResMgr
        section = ResMgr.openSection('grz_session_stats/map_names.json')
        if section is not None:
            return decode(section.asBinary)
    except ImportError:
        pass
    except Exception:
        pass
    path = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'map_names.json')
    try:
        with io.open(path, 'rb') as stream:
            return decode(stream.read(MAX_BYTES + 1))
    except (IOError, OSError, ValueError, TypeError, UnicodeError, RuntimeError):
        return {}


class MapNames(object):
    def __init__(self, language, catalog=None):
        self.language = language
        self.catalog = bundled_names() if catalog is None else catalog
        aliases = {}
        for identifier in self.catalog:
            alias = identifier.split('_', 1)[1]
            aliases[alias] = None if alias in aliases else identifier
        self.aliases = aliases

    def name(self, identifier, fallback):
        if isinstance(identifier, bytes) and not isinstance(identifier, text_type):
            try:
                identifier = identifier.decode('ascii')
            except UnicodeError:
                return fallback
        if not isinstance(identifier, text_type):
            return fallback
        names = self.catalog.get(identifier) or self.catalog.get(self.aliases.get(identifier))
        return (names.get(self.language) or names.get('en') or fallback) if names else fallback
