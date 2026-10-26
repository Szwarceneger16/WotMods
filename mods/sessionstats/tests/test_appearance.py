# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

import io
import json
import logging
import os
import re
import shutil
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'src'))
from grz_session_stats import appearance as style


class AppearanceTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.mkdtemp(prefix='grz-appearance-')
        self.path = os.path.join(self.directory, style.CONFIG_FILENAME)
        self.output = io.StringIO()
        self.handler = logging.StreamHandler(self.output)
        self.logger = logging.getLogger('grz.sessionstats')
        self.old_level, self.old_propagate = self.logger.level, self.logger.propagate
        self.logger.setLevel(logging.INFO)
        self.logger.propagate = False
        self.logger.addHandler(self.handler)

    def tearDown(self):
        self.logger.removeHandler(self.handler)
        self.logger.setLevel(self.old_level)
        self.logger.propagate = self.old_propagate
        self.handler.close()
        shutil.rmtree(self.directory)

    def write(self, raw):
        if isinstance(raw, dict):
            raw = json.dumps(raw)
        if not isinstance(raw, bytes):
            raw = raw.encode('utf-8')
        with io.open(self.path, 'wb') as target:
            target.write(raw)
        return style.load_config(self.path)

    def test_bundled_json_has_every_default_with_no_extra_fields(self):
        with io.open(os.path.join(ROOT, style.CONFIG_FILENAME), 'r', encoding='utf-8') as source:
            self.assertEqual(json.load(source), style.default_config())
        self.assertEqual(style.load_config(os.path.join(ROOT, style.CONFIG_FILENAME)),
                         style.default_config())
        self.assertEqual(self.output.getvalue(), '')

    def test_default_render_is_exact_original_css_plus_neutral_opacity(self):
        result = style.build_presentation(style.default_config())
        for name, key, extra in (
                ('session_stats.css', 'panel_css', '\n.ss-window { opacity:1; }\n'),
                ('footer.css', 'footer_css', '\n.grz-session-footer-button { opacity:1; }\n')):
            with io.open(os.path.join(ROOT, 'ui', name), 'r', encoding='utf-8') as source:
                self.assertEqual(result[key], source.read() + extra)
        self.assertEqual(result['scroll_speed'], 1.0)

    def test_every_real_color_radius_opacity_is_tokenized(self):
        templates = style.PANEL_TEMPLATE + style.FOOTER_TEMPLATE
        # Exclude comments, where renderer notes can legitimately mention a color.
        stripped = re.sub(r'/\*.*?\*/', '', templates, flags=re.S)
        stripped = style._TOKEN.sub('TOKEN', stripped)
        self.assertIsNone(re.search(r'#[0-9a-fA-F]{3,8}\b|\brgba?\(|\btransparent\b', stripped))
        for match in re.finditer(r'border-radius\s*:\s*([^;]+)', stripped):
            self.assertIn('TOKEN', match.group(1))
            self.assertIsNone(re.search(r'\d+(?:\.\d+)?rem', match.group(1)))
        for match in re.finditer(r'opacity\s*:\s*([^;]+)', stripped):
            self.assertEqual(match.group(1), 'TOKEN')
        tokens = set(style._TOKEN.findall(templates + style.PANEL_OPACITY_RULE + style.FOOTER_OPACITY_RULE))
        for group in ('colors', 'radii', 'opacity'):
            self.assertEqual(set(style.DEFAULT_CONFIG[group]), set(key for section, key in tokens if section == group))

    def test_defaults_and_results_do_not_share_mutable_state(self):
        a = style.default_config()
        a['colors']['window_background'] = '#abcdef'
        self.assertEqual(style.default_config()['colors']['window_background'], '#111309')
        raw = {'colors': {'window_background': '#abc'}}
        validated = style.validate_config(raw)
        raw['colors']['window_background'] = '#fff'
        self.assertEqual(validated['colors']['window_background'], '#abc')

    def test_partial_config_keeps_every_other_default(self):
        actual = self.write({'colors': {'window_background': '#123456'},
                             'scroll': {'speed_multiplier': 2}})
        expected = style.default_config()
        expected['colors']['window_background'] = '#123456'
        expected['scroll']['speed_multiplier'] = 2.0
        self.assertEqual(actual, expected)
        self.assertEqual(self.output.getvalue(), '')

    def test_invalid_leaf_keeps_valid_siblings_and_logs_only_field_reason(self):
        actual = self.write({'colors': {'window_background': 'SECRET-user-value',
                                       'window_border': '#246'},
                             'radii': {'window': 6, 'group_card': -1},
                             'scroll': {'speed_multiplier': 2}})
        self.assertEqual(actual['colors']['window_background'], '#111309')
        self.assertEqual(actual['colors']['window_border'], '#246')
        self.assertEqual(actual['radii']['window'], 6)
        self.assertEqual(actual['radii']['group_card'], 5)
        self.assertEqual(actual['scroll']['speed_multiplier'], 2)
        log = self.output.getvalue()
        self.assertIn('CONFIG field=colors.window_background', log)
        self.assertIn('CONFIG field=radii.group_card', log)
        self.assertNotIn('SECRET-user-value', log)

    def test_malformed_file_restores_all_defaults_not_the_previous_override(self):
        first = self.write({'colors': {'window_border': '#123456'}})
        self.assertEqual(first['colors']['window_border'], '#123456')
        self.assertEqual(self.write('{"colors":{"window_border":"#123456"},'), style.default_config())
        self.assertIn('CONFIG parse failed', self.output.getvalue())

    def test_duplicate_keys_at_any_depth_reject_the_whole_file(self):
        for raw in ('{"colors":{},"colors":{},"scroll":{"speed_multiplier":3}}',
                    '{"colors":{"window_border":"#123","window_border":"#456"},"scroll":{"speed_multiplier":3}}'):
            self.assertEqual(self.write(raw), style.default_config())
        self.assertIn('duplicate_key', self.output.getvalue())

    def test_syntax_error_location_is_available_on_python27_without_echoing_values(self):
        raw = '{\n  "colors": {"window_background": "PRIVATE-value"},\n}'
        self.assertEqual(self.write(raw), style.default_config())
        self.assertIsNotNone(re.search(r'line=[1-9][0-9]* column=[1-9][0-9]*', self.output.getvalue()))
        self.assertNotIn('PRIVATE-value', self.output.getvalue())

    def test_nonstandard_nan_and_infinity_reject_whole_file(self):
        for value in ('NaN', 'Infinity', '-Infinity'):
            self.assertEqual(self.write('{"scroll":{"speed_multiplier":'+value+'},"radii":{"window":7}}'),
                             style.default_config())
        self.assertIn('non_finite_constant', self.output.getvalue())

    def test_nonfinite_exponent_is_invalid_numeric_field(self):
        actual = self.write('{"scroll":{"speed_multiplier":1e999},"radii":{"window":7}}')
        self.assertEqual(actual['scroll']['speed_multiplier'], 1)
        self.assertEqual(actual['radii']['window'], 7)

    def test_wrong_top_level_and_unsupported_schema_restore_all_defaults(self):
        for raw in ('null', '[]', 'true', '12', '"text"',
                    '{"schema_version":2,"radii":{"window":7}}',
                    '{"schema_version":true,"radii":{"window":7}}',
                    '{"schema_version":1.0,"radii":{"window":7}}'):
            self.assertEqual(self.write(raw), style.default_config())

    def test_wrong_section_type_does_not_disable_valid_sections(self):
        actual = self.write({'colors': [], 'radii': {'window': 7}})
        self.assertEqual(actual['colors'], style.default_config()['colors'])
        self.assertEqual(actual['radii']['window'], 7)
        self.assertIn('field=colors reason=expected_object', self.output.getvalue())

    def test_numeric_boundaries_and_zero_are_accepted(self):
        actual = self.write({'radii': {'window': 0, 'group_card': 24},
                             'opacity': {'window': 0, 'garage_button': 1},
                             'scroll': {'speed_multiplier': 0.1}})
        self.assertEqual(actual['radii']['window'], 0)
        self.assertEqual(actual['radii']['group_card'], 24)
        self.assertEqual(actual['opacity']['window'], 0)
        self.assertEqual(actual['scroll']['speed_multiplier'], 0.1)
        self.assertEqual(self.write({'scroll': {'speed_multiplier': 8}})['scroll']['speed_multiplier'], 8)

    def test_booleans_numeric_strings_nonfinite_and_out_of_range_are_rejected(self):
        cases = [('radii', 'window', [True, False, '6', None, -0.01, 24.01, float('nan'), float('inf'), 10 ** 500]),
                 ('opacity', 'window', [True, '0.5', -0.01, 1.01]),
                 ('scroll', 'speed_multiplier', [True, '2', 0, 0.099, 8.01])]
        for section, key, values in cases:
            for value in values:
                result = style.validate_config({section: {key: value}})
                self.assertEqual(result[section][key], style.DEFAULT_CONFIG[section][key])

    def test_supported_colors_have_safe_normalized_css_spellings(self):
        cases = [('#AbC', '#abc'), (' #123ABC ', '#123abc'),
                 ('#12345600', 'rgba(18,52,86,0)'), ('#123456ff', 'rgba(18,52,86,1)'),
                 ('#12345680', 'rgba(18,52,86,0.50196078)'),
                 ('RGB(1, 2, 255)', 'rgb(1,2,255)'), ('rgba(1,2,3,.5)', 'rgba(1,2,3,0.5)'),
                 ('TRANSPARENT', 'transparent')]
        for incoming, expected in cases:
            result = style.validate_config({'colors': {'window_background': incoming}})
            self.assertEqual(result['colors']['window_background'], expected)

    def test_css_injection_unsupported_colors_and_out_of_range_channels_are_rejected(self):
        cases = ['red', 'currentColor', 'var(--color)', 'url(https://example.test/a)',
                 '#abcd', '#12', '#zzzzzz', 'rgb(256,0,0)', 'rgb(-1,0,0)',
                 'rgba(1,2,3,1.1)', 'rgba(1,2,3,-0.1)', 'rgb(1,2,3,1)', 'rgba(1,2,3)',
                 'rgba(1,2,3,NaN)', 'rgba(1,2,3,1e2)', 'rgba(1,2,3,50%)',
                 '#fff; color:#000', '#fff}</style><script>SECRET</script>', '#fff\n',
                 ['#fff'], True, None]
        for value in cases:
            result = style.validate_config({'colors': {'window_background': value}})
            self.assertEqual(result['colors']['window_background'], '#111309')
        self.assertNotIn('SECRET', self.output.getvalue())

    def test_unknown_keys_are_logged_and_ignored_with_bounded_sanitized_names(self):
        actual = self.write({'unexpected\nfield': {'SECRET': 1},
                             'colors': {'unknown_border': '#fff'},
                             'scroll': {'speed_multiplier': 2}})
        self.assertEqual(actual['scroll']['speed_multiplier'], 2)
        self.assertNotIn('unknown_border', actual['colors'])
        log = self.output.getvalue()
        self.assertIn('field=unexpected?field', log)
        self.assertIn('field=colors.unknown_border', log)
        self.assertNotIn('SECRET', log)

    def test_unknown_field_flood_has_bounded_log_output(self):
        style.validate_config({'colors': dict(('extra_%s' % i, '#fff') for i in range(500))})
        self.assertEqual(len(self.output.getvalue().splitlines()), style.MAX_DIAGNOSTICS + 1)
        self.assertIn('additional invalid fields omitted', self.output.getvalue())

    def test_utf8_bom_and_unicode_path_are_supported(self):
        self.path = os.path.join(self.directory, 'zażółć.json')
        actual = self.write(b'\xef\xbb\xbf{"scroll":{"speed_multiplier":2}}')
        self.assertEqual(actual['scroll']['speed_multiplier'], 2)
        self.assertEqual(self.output.getvalue(), '')

    def test_invalid_encoding_and_oversized_files_restore_defaults(self):
        self.assertEqual(self.write(b'{"x":"\xff"}'), style.default_config())
        self.assertIn('invalid_utf8', self.output.getvalue())
        self.assertEqual(self.write(b' ' * (style.MAX_CONFIG_BYTES + 1)), style.default_config())
        self.assertIn('exceeds', self.output.getvalue())

    def test_missing_file_is_normal_fallback_and_io_error_is_logged(self):
        self.assertEqual(style.load_config(None), style.default_config())
        self.assertEqual(style.load_config(self.path), style.default_config())
        self.assertIn('file missing', self.output.getvalue())
        self.assertNotIn('CONFIG field', self.output.getvalue())
        self.assertEqual(style.load_config(self.directory), style.default_config())
        self.assertIn('file read failed', self.output.getvalue())

    def test_build_presentation_changes_only_token_values_and_never_executes_css(self):
        custom = style.default_config()
        custom['colors']['window_background'] = 'rgba(17,19,9,0.8)'
        custom['colors']['table_row_following_border_top'] = '#abcdef'
        custom['colors']['garage_spinner_border_top_color'] = '#123456'
        custom['radii']['window'] = 8
        custom['opacity']['window'] = 0.9
        custom['scroll']['speed_multiplier'] = 1.5
        result = style.build_presentation(custom)
        self.assertIn('background:rgba(17,19,9,0.8)', result['panel_css'])
        self.assertIn('border-top:1rem solid #abcdef', result['panel_css'])
        self.assertIn('border-radius:8rem', result['panel_css'])
        self.assertIn('.ss-window { opacity:0.9; }', result['panel_css'])
        self.assertIn('border-top-color:#123456', result['footer_css'])
        self.assertEqual(result['scroll_speed'], 1.5)
        self.assertNotIn('{{', result['panel_css'] + result['footer_css'])
        invalid = style.build_presentation({'colors': {'window_background': 'red;display:none'}})
        self.assertEqual(invalid, style.build_presentation(style.default_config()))


if __name__ == '__main__':
    unittest.main()
