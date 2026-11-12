# -*- coding: utf-8 -*-
"""Resolve client-localized date preferences without reading the OS locale."""
from __future__ import absolute_import, unicode_literals

import re
import time

try:
    text_type = unicode
except NameError:
    text_type = str


def date_pattern(value):
    """Accept only numeric date formats that the inline editor can reproduce."""
    if isinstance(value, bytes) and not isinstance(value, text_type):
        try:
            value = value.decode('utf-8')
        except UnicodeError:
            return {}
    if not isinstance(value, text_type):
        return {}
    value = re.sub(r"'([./-])'", r'\1', value).replace('%O', '%').replace('%E', '%')
    tokens = re.findall(r'%[EO]?[demyY]|d{1,2}|M{1,2}|y{2,4}', value)
    names = []
    for token in tokens:
        names.append('D' if token in ('%d', '%e') or token.startswith('d') else
                     'M' if token == '%m' or token.startswith('M') else 'Y')
    if len(names) != 3 or set(names) != set('DMY'):
        return {}
    remainder = re.sub(r'%[EO]?[demyY]|d{1,2}|M{1,2}|y{2,4}', '', value)
    separators = re.findall(r'[./-]', remainder)
    if len(separators) != 2 or separators[0] != separators[1] or re.sub(r'[./\-\s]', '', remainder):
        return {}
    return {'order': ''.join(names), 'separator': separators[0]}


def language_date_settings(client_language=None):
    """Use bundled-language date defaults with a conservative 24-hour clock."""
    if isinstance(client_language, bytes) and not isinstance(client_language, text_type):
        try:
            client_language = client_language.decode('ascii')
        except UnicodeError:
            client_language = None
    code = client_language.lower().replace('_', '-').split('-')[0] if isinstance(client_language, text_type) else ''
    # Only an actual native formatted sample or an explicit override enables
    # 12h mode. Neither Windows preferences nor a browser locale is evidence.
    return {'order': 'DMY', 'separator': '/' if code in ('fr', 'es') else '.',
            'hour12': False, 'first_weekday': 1}


def regional_date_settings(date_formatter=None, time_formatter=None, client_language=None,
                           weekday_formatter=None, month_formatter=None):
    """Read only the game's resource-backed formatters, never OS preferences."""
    result = language_date_settings(client_language)
    sample = time.mktime((2006, 11, 23, 17, 45, 0, 0, 0, -1))
    if callable(date_formatter):
        try:
            value = date_formatter(sample)
            match = re.match(r'^\s*(\d{1,4})([./-])(\d{1,4})\2(\d{1,4})\s*$', value)
            if match:
                mapping = {23: 'D', 11: 'M', 2006: 'Y', 6: 'Y'}
                order = ''.join(mapping.get(int(match.group(index)), '?') for index in (1, 3, 4))
                if len(order) == 3 and set(order) == set('DMY'):
                    result.update(order=order, separator=match.group(2))
        except (ValueError, TypeError, AttributeError, RuntimeError):
            pass
    if callable(time_formatter):
        try:
            match = re.search(r'\d{1,2}', time_formatter(sample))
            if match and int(match.group()) in (5, 17):
                result['hour12'] = int(match.group()) == 5
        except (ValueError, TypeError, AttributeError, RuntimeError):
            pass
    # These callbacks use R.strings.menu.dateTime, not strftime's process locale.
    for key, count, formatter in (('weekdays', 7, weekday_formatter), ('months', 12, month_formatter)):
        if not callable(formatter):
            continue
        try:
            stamps = [time.mktime((2006, index + 1, 23, 12, 0, 0, 0, 0, -1)) for index in range(12)] if key == 'months' else [
                time.mktime((2026, 11, 1 + index, 12, 0, 0, 0, 0, -1)) for index in range(7)]
            labels = [formatter(stamp) for stamp in stamps]
            labels = [label.decode('utf-8') if isinstance(label, bytes) and not isinstance(label, text_type) else label for label in labels]
            if all(isinstance(label, text_type) and 0 < len(label) <= 64 and
                   not any(ord(char) < 32 for char in label) for label in labels):
                result[key] = labels
        except (ValueError, TypeError, AttributeError, RuntimeError):
            pass
    return result


def resolve_date_settings(client_language=None, native=None, overrides=None):
    """Explicit config fields override the game, then language supplies gaps."""
    from .localization import calendar_settings
    result = language_date_settings(client_language)
    result.update(calendar_settings(native))
    if not isinstance(overrides, dict):
        return result
    if overrides.get('order') in ('DMY', 'MDY', 'YMD'):
        result['order'] = overrides['order']
    if overrides.get('separator') in ('.', '/', '-'):
        result['separator'] = overrides['separator']
    if overrides.get('hour_format') in ('12h', '24h'):
        result['hour12'] = overrides['hour_format'] == '12h'
    first = overrides.get('first_weekday')
    if isinstance(first, int) and not isinstance(first, bool) and 0 <= first <= 6:
        result['first_weekday'] = first
    return result
