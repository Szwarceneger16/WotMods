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

    def test_client_resource_formatters_override_language_without_os_metadata(self):
        answer = dates.regional_date_settings(lambda stamp: '11/23/2006', lambda stamp: '5:45 PM',
                                              client_language='pl',
                                              weekday_formatter=lambda stamp: 'Day' + str(dates.time.localtime(stamp).tm_wday),
                                              month_formatter=lambda stamp: ('Month' + str(dates.time.localtime(stamp).tm_mon)).encode('utf-8'))
        self.assertEqual((answer['order'], answer['separator'], answer['hour12']), ('MDY', '/', True))
        self.assertEqual(answer['first_weekday'], 1)
        self.assertEqual(answer['weekdays'], ['Day6', 'Day0', 'Day1', 'Day2', 'Day3', 'Day4', 'Day5'])
        self.assertEqual(answer['months'], ['Month' + str(index) for index in range(1, 13)])
        answer = dates.regional_date_settings(lambda stamp: '2006-11-23', lambda stamp: '17:45', client_language='en')
        self.assertEqual((answer['order'], answer['separator'], answer['hour12']), ('YMD', '-', False))

    def test_unavailable_native_formatters_use_client_language_not_windows(self):
        def broken(stamp):
            raise RuntimeError('fixture unavailable')
        answer = dates.regional_date_settings(broken, broken, client_language='pl',
                                              weekday_formatter=broken, month_formatter=broken)
        self.assertEqual(answer, {'order': 'DMY', 'separator': '.', 'hour12': False, 'first_weekday': 1})
        self.assertFalse(dates.regional_date_settings(client_language=b'en')['hour12'])
        self.assertFalse(dates.regional_date_settings(client_language='pl')['hour12'])
        self.assertEqual(dates.regional_date_settings(client_language='fr')['separator'], '/')
        self.assertFalse(dates.regional_date_settings(client_language=None)['hour12'])
        # No Windows/ctypes or process-locale entry point is retained in this module.
        self.assertFalse(hasattr(dates, '_windows_settings'))
        self.assertFalse(hasattr(dates, '_posix_settings'))
        self.assertFalse(hasattr(dates, 'locale'))

    def test_config_fields_override_client_and_auto_preserves_client_values(self):
        native = {'order': 'MDY', 'separator': '/', 'hour12': True, 'first_weekday': 0,
                  'months': ['Native month'] * 12}
        forced = {'order': 'YMD', 'separator': '-', 'hour_format': '24h', 'first_weekday': 1}
        result = dates.resolve_date_settings('en', native, forced)
        self.assertEqual((result['order'], result['separator'], result['hour12'], result['first_weekday']),
                         ('YMD', '-', False, 1))
        self.assertEqual(result['months'], ['Native month'] * 12)
        self.assertEqual(native['order'], 'MDY')
        self.assertEqual(dates.resolve_date_settings('pl', native, dict((key, 'auto') for key in forced)), native)
        self.assertEqual(dates.resolve_date_settings('pl', None, {'hour_format': '12h'})['hour12'], True)

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

    def test_game_api_uses_client_resources_and_never_backport_system_locale(self):
        import types
        from grz_session_stats.runtime import GameAPI
        names = ('gui', 'gui.shared', 'gui.shared.formatters', 'gui.impl', 'gui.impl.gen',
                 'gui.impl.gen.view_models', 'gui.impl.gen.view_models.constants',
                 'gui.impl.gen.view_models.constants.date_time_formats')
        modules = dict((name, types.ModuleType(name)) for name in names)
        for module in modules.values():
            module.__path__ = []
        class Formats(object):
            SHORTDATE = 'shortDate'
            SHORTTIME = 'ShortTime'
        calls = []
        def regional(stamp, form):
            calls.append(form)
            return '23.11.2006' if form == Formats.SHORTDATE else '17:45'
        native = types.ModuleType('date_time')
        native.getRegionalDateTime = regional
        native.getFormattedDateTime = lambda stamp, form: ('Day' + str(dates.time.localtime(stamp).tm_wday)
                                                           if form == '%a' else 'Month' + str(dates.time.localtime(stamp).tm_mon))
        modules['gui.shared.formatters'].date_time = native
        modules['gui.impl.gen.view_models.constants.date_time_formats'].DateTimeFormatsEnum = Formats
        prior = dict((name, sys.modules.get(name)) for name in modules)
        sys.modules.update(modules)
        try:
            api = GameAPI.__new__(GameAPI)
            api.client_language = lambda: 'pl'
            settings = api.date_settings()
        finally:
            for name, old in prior.items():
                if old is None:
                    sys.modules.pop(name, None)
                else:
                    sys.modules[name] = old
        self.assertEqual(calls, [Formats.SHORTDATE, Formats.SHORTTIME])
        self.assertEqual((settings['order'], settings['separator'], settings['hour12']), ('DMY', '.', False))
        self.assertEqual(len(settings['months']), 12)
        self.assertEqual(len(settings['weekdays']), 7)
