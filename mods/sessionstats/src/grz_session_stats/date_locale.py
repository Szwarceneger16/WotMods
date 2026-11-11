# -*- coding: utf-8 -*-
"""Read regional date preferences without changing the process locale."""
from __future__ import absolute_import, unicode_literals

import locale
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


def _windows_settings():
    import ctypes
    kernel = ctypes.windll.kernel32
    def read(field):
        buffer = ctypes.create_unicode_buffer(128)
        getter = getattr(kernel, 'GetLocaleInfoEx', None)
        length = getter(None, field, buffer, len(buffer)) if getter else kernel.GetLocaleInfoW(0x0400, field, buffer, len(buffer))
        return buffer.value if length else ''
    result = date_pattern(read(0x001f))  # LOCALE_SSHORTDATE, including user overrides.
    week = read(0x100c)  # Monday=0 through Sunday=6.
    if week in tuple(str(value) for value in range(7)):
        result['first_weekday'] = (int(week) + 1) % 7
    clock = read(0x0023)
    if clock in ('0', '1'):
        result['hour12'] = clock == '0'
    result['weekdays'] = [read(0x0037)] + [read(0x0031 + index) for index in range(6)]
    result['months'] = [read(0x0038 + index) for index in range(12)]
    result['periods'] = [read(0x0028), read(0x0029)]
    return result


def _posix_settings():
    # A C process locale is not evidence of the user's regional preferences.
    # In particular, the game can keep Python in C while Wulf uses Windows.
    name = locale.getlocale(locale.LC_TIME)[0]
    if not name or name in ('C', 'POSIX') or not hasattr(locale, 'nl_langinfo'):
        return {}
    result = date_pattern(locale.nl_langinfo(locale.D_FMT))
    result['hour12'] = bool(re.search(r'%[IlpPr]', locale.nl_langinfo(locale.T_FMT)))
    result['weekdays'] = [locale.nl_langinfo(getattr(locale, 'ABDAY_' + str(index))) for index in range(1, 8)]
    result['months'] = [locale.nl_langinfo(getattr(locale, 'MON_' + str(index))) for index in range(1, 13)]
    result['periods'] = [locale.nl_langinfo(locale.AM_STR), locale.nl_langinfo(locale.PM_STR)]
    return result


def regional_date_settings(date_formatter=None, time_formatter=None):
    """Prefer the game's formatter; use system settings for calendar metadata."""
    try:
        result = _windows_settings()
    except (ImportError, AttributeError, OSError, ValueError, TypeError):
        try:
            result = _posix_settings()
        except (AttributeError, ValueError, TypeError):
            result = {}
    # All components differ, so a formatted sample unambiguously identifies
    # DMY/MDY/YMD even when the system uses a two-digit display year.
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
    return result
