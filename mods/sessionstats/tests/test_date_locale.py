# -*- coding: utf-8 -*-
"""Regional calendar metadata is bounded and does not mutate locale state."""
from __future__ import unicode_literals

from contextlib import contextmanager
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from grz_session_stats import date_locale as dates
from grz_session_stats.localization import Localizer, calendar_settings


@contextmanager
def replace(owner, name, value):
    original = getattr(owner, name)
    setattr(owner, name, value)
    try:
        yield
    finally:
        setattr(owner, name, original)


class RegionalCalendarTests(unittest.TestCase):
    def test_numeric_windows_and_posix_patterns_preserve_regional_order(self):
        for pattern, order, separator in (("dd'.'MM'.'yyyy", 'DMY', '.'),
                                          ('M/d/yyyy', 'MDY', '/'),
                                          ('yyyy-MM-dd', 'YMD', '-'),
                                          ('%m/%d/%y', 'MDY', '/'),
                                          ('%Y-%Om-%Od', 'YMD', '-')):
            self.assertEqual(dates.date_pattern(pattern), {'order': order, 'separator': separator})
        for pattern in ('ddd, dd MMM yyyy', '%x', '%m/%d-%Y', 'arbitrary', None):
            self.assertEqual(dates.date_pattern(pattern), {})

    def test_native_game_format_overrides_process_locale_and_keeps_calendar_metadata(self):
        native = {'order': 'DMY', 'separator': '.', 'first_weekday': 0,
                  'weekdays': ['Su', 'Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa'], 'hour12': False}
        with replace(dates, '_windows_settings', lambda: dict(native)):
            answer = dates.regional_date_settings(lambda stamp: '11/23/2006', lambda stamp: '5:45 PM')
        self.assertEqual(answer['order'], 'MDY')
        self.assertEqual(answer['separator'], '/')
        self.assertTrue(answer['hour12'])
        self.assertEqual(answer['first_weekday'], 0)
        self.assertEqual(answer['weekdays'], native['weekdays'])
        with replace(dates, '_windows_settings', lambda: dict(native)):
            answer = dates.regional_date_settings(lambda stamp: '2006-11-23', lambda stamp: '17:45')
        self.assertEqual(answer['order'], 'YMD')
        self.assertFalse(answer['hour12'])

    def test_unavailable_native_formatters_keep_valid_system_preferences(self):
        def broken(stamp):
            raise RuntimeError('fixture unavailable')
        with replace(dates, '_windows_settings', lambda: {'order': 'DMY', 'separator': '-', 'hour12': False}):
            answer = dates.regional_date_settings(broken, broken)
        self.assertEqual(answer, {'order': 'DMY', 'separator': '-', 'hour12': False})

    def test_c_process_locale_does_not_invent_regional_preferences(self):
        with replace(dates.locale, 'getlocale', lambda unused: (None, None)):
            self.assertEqual(dates._posix_settings(), {})

    def test_native_metadata_is_bounded_and_snapshot_does_not_share_mutable_labels(self):
        source = {'order': 'MDY', 'separator': '/', 'hour12': True, 'first_weekday': 0,
                  'periods': ['AM', 'PM'], 'months': ['Month'] * 12, 'weekdays': ['Day'] * 7}
        translator = Localizer('pl', date_settings=source)
        source['months'][0] = 'Changed'
        snapshot = translator.snapshot({'warnings': [], 'scopes': {}})
        self.assertEqual(snapshot['localization']['date_settings']['months'][0], 'Month')
        snapshot['localization']['date_settings']['months'][0] = 'Changed again'
        self.assertEqual(translator.date_settings['months'][0], 'Month')
        self.assertEqual(calendar_settings({'order': 'DYM', 'separator': '<', 'hour12': 1,
                                            'first_weekday': True, 'months': ['x'] * 13,
                                            'weekdays': ['x\n'] * 7, 'periods': ['', 'x']}), {})

    def test_platform_metadata_uses_windows_user_overrides_and_weekday_order(self):
        class Kernel(object):
            def GetLocaleInfoEx(self, name, field, buffer, size):
                values = {0x1f: 'M/d/yyyy', 0x100c: '6', 0x23: '0', 0x28: 'AM', 0x29: 'PM'}
                buffer.value = values.get(field, 'label-' + str(field))
                return len(buffer.value) + 1
        class Windows(object):
            kernel32 = Kernel()
        import ctypes
        original = getattr(ctypes, 'windll', None)
        ctypes.windll = Windows()
        try:
            answer = dates._windows_settings()
        finally:
            if original is None:
                del ctypes.windll
            else:
                ctypes.windll = original
        self.assertEqual((answer['order'], answer['separator'], answer['first_weekday'], answer['hour12']), ('MDY', '/', 0, True))
        self.assertEqual(answer['weekdays'][0], 'label-55')
        self.assertEqual(answer['weekdays'][1], 'label-49')
