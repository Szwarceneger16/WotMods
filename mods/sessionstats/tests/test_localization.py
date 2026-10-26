# -*- coding: utf-8 -*-
"""Catalog safety, durable-history compatibility and native language reloads."""
from __future__ import unicode_literals

import copy
from contextlib import contextmanager
import io
import json
import logging
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from grz_session_stats import localization as loc
from grz_session_stats.appearance import validate_config
from grz_session_stats.runtime import Runtime, GameAPI
from test_runtime import FakeAPI, FakeWindow, Clock, EXPECTED

DECODER_ERRORS = [RuntimeError]
try:
    DECODER_ERRORS.append(RecursionError)
except NameError:
    pass  # Python 2.7 reports decoder recursion as RuntimeError.


class LocalizationTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.mkdtemp(prefix='grz-languages-')
        self.path = os.path.join(self.directory, loc.FILENAME)
        self.catalog = loc.bundled_catalog()
        self.disabled = logging.root.manager.disable
        logging.disable(logging.CRITICAL)

    def tearDown(self):
        logging.disable(self.disabled)
        shutil.rmtree(self.directory)

    def write(self, languages):
        value = json.dumps({'schema_version': 1, 'languages': languages}, ensure_ascii=False)
        if not isinstance(value, loc.text_type):
            value = value.decode('utf-8')
        with io.open(self.path, 'w', encoding='utf-8') as stream:
            stream.write(value)

    def test_all_seven_languages_have_every_key_and_exact_placeholder_contract(self):
        self.assertEqual(set(self.catalog), set(('en','pl','ru','fr','de','es','uk')))
        for code, entries in self.catalog.items():
            self.assertEqual(set(entries), set(loc.ENGLISH), code)
            for key, value in entries.items():
                self.assertTrue(loc.valid_text(key, value), code + ':' + key)
        self.assertEqual(self.catalog['en'], loc.ENGLISH)
        self.assertEqual(self.catalog['pl'], loc.LEGACY_POLISH)

    def test_default_and_unknown_language_use_english(self):
        self.assertEqual(loc.Localizer().text('title'), 'Session statistics')
        self.assertEqual(loc.Localizer('zz').language, 'en')
        self.assertEqual(validate_config({})['language'], 'auto')
        for value in (True, 12, {}, None, 'EN', '../pl', 'pl\n'):
            self.assertEqual(validate_config({'language': value})['language'], 'auto')
        self.assertEqual(validate_config({'language': 'auto'})['language'], 'auto')
        self.assertEqual(validate_config({'language': 'uk'})['language'], 'uk')
        self.assertEqual(validate_config({'language': 'pt-BR'})['language'], 'pt-BR')

    def test_auto_normalizes_game_locales_and_unsupported_games_use_english(self):
        for game, expected in (('pl', 'pl'), ('PL_pl', 'pl'), (b'pl', 'pl'),
                               ('uk-UA', 'uk'), ('en_GB', 'en'), ('ja', 'en'),
                               (None, 'en'), (True, 'en'), ({}, 'en'),
                               (b'\xff', 'en'), ('pl\n', 'en'), ('../pl', 'en')):
            translator = loc.Localizer('auto', client_language=game)
            self.assertEqual(translator.language, expected, repr(game))
            self.assertEqual(translator.text('title'), self.catalog[expected]['title'])

    def test_explicit_language_wins_over_game_and_unknown_override_uses_english(self):
        for configured, expected in (('en', 'en'), ('fr', 'fr'), ('zz', 'en')):
            self.assertEqual(loc.Localizer(configured, client_language='pl').language, expected)

    def test_external_regions_cannot_add_supported_languages(self):
        self.write({'pt': {'title': 'Base'}, 'pt-BR': {'title': 'Regional'}})
        self.assertEqual(loc.Localizer('auto', self.path, client_language='pt_br').text('title'), self.catalog['en']['title'])
        self.assertEqual(loc.Localizer('auto', self.path, client_language='pt_PT').text('title'), self.catalog['en']['title'])

    def test_native_outcomes_follow_only_the_selected_game_language(self):
        native = {'outcome.win': 'WG victory fixture', 'outcome.loss': 'WG loss fixture',
                  'outcome.draw': 'WG draw fixture'}
        for configured in ('auto', 'pl'):
            translator = loc.Localizer(configured, client_language='pl_PL', native_messages=native)
            for key in native:
                self.assertEqual(translator.text(key), native[key])
        for configured, game in (('en', 'pl'), ('fr', 'pl'), ('auto', 'ja'), ('zz', 'pl')):
            translator = loc.Localizer(configured, client_language=game, native_messages=native)
            self.assertEqual(translator.text('outcome.win'), self.catalog[translator.language]['outcome.win'])

    def test_external_catalog_cannot_override_native_labels(self):
        self.write(self.catalog)
        native = {'outcome.win': 'WG fixture'}
        self.assertEqual(loc.Localizer('auto', self.path, client_language='pl', native_messages=native)
                         .text('outcome.win'), 'WG fixture')
        self.write({'pl': {'outcome.win': 'Custom victory'}})
        self.assertEqual(loc.Localizer('auto', self.path, client_language='pl', native_messages=native)
                         .text('outcome.win'), 'WG fixture')

    def test_missing_or_malformed_native_text_retains_per_outcome_fallback(self):
        for invalid in (None, 23, '#battle_results:status/win', '', '<b>Win</b>',
                        'x' * 129, b'\xff', 'Win\n', '{0}'):
            translator = loc.Localizer('auto', client_language='pl', native_messages={
                'outcome.win': invalid, 'outcome.draw': 'WG draw fixture'})
            self.assertEqual(translator.text('outcome.win'), self.catalog['pl']['outcome.win'])
            self.assertEqual(translator.text('outcome.draw'), 'WG draw fixture')
        self.assertEqual(loc.Localizer('auto', client_language='pl', native_messages={
            'outcome.win': 'Zwycięstwo'.encode('utf-8')}).text('outcome.win'), 'Zwycięstwo')

    def test_native_adapter_reads_client_language_and_exact_wg_result_keys(self):
        import types
        helpers = types.ModuleType(str('helpers'))
        helpers.getClientLanguage = lambda: 'pl'
        calls = []
        helpers.i18n = type(str('I18n'), (), {'makeString': staticmethod(
            lambda key: calls.append(key) or 'WG fixture')})
        previous = sys.modules.get('helpers')
        sys.modules['helpers'] = helpers
        try:
            api = GameAPI.__new__(GameAPI)
            self.assertEqual(api.client_language(), 'pl')
            self.assertEqual(set(api.outcome_messages()), {'outcome.win', 'outcome.loss', 'outcome.draw'})
            self.assertEqual(calls, ['#battle_results:status/win', '#battle_results:status/lose',
                                     '#battle_results:status/tie'])
        finally:
            if previous is None:
                del sys.modules['helpers']
            else:
                sys.modules['helpers'] = previous

    def test_external_overrides_and_new_languages_are_ignored(self):
        self.write({'pl': {'title': 'Własny tytuł'}, 'pt-BR': {'title': 'Estatísticas'}})
        translator = loc.Localizer('pl', self.path)
        self.assertEqual(translator.text('title'), self.catalog['pl']['title'])
        self.assertEqual(translator.text('refresh'), self.catalog['pl']['refresh'])
        added = loc.Localizer('pt-BR', self.path)
        self.assertEqual(added.language, 'en')
        self.assertEqual(added.text('refresh'), 'Refresh')

    def test_invalid_values_and_unsafe_placeholders_fall_back_per_message(self):
        for invalid in ('Missing count', '{1}', '{{0}}', '{0.__class__}', '{0[secret]}', '{0!r}', '{0:>10}', '{',
                        'control\x00{0}', 'x' * (loc.MAX_TEXT + 1), None, 42, []):
            self.write({'en': {'status.pending': invalid, 'refresh': 'Reload'}})
            translator = loc.Localizer('en', self.path)
            self.assertEqual(translator.text('status.pending', 3), 'Pending: 3')
            self.assertEqual(translator.text('refresh'), self.catalog['en']['refresh'])

    def test_malformed_duplicate_nonfinite_oversized_catalogs_restore_bundled_language(self):
        for raw in (b'{', b'[]', b'{"schema_version":true,"languages":{}}',
                    b'{"schema_version":1,"languages":{"en":{"title":"a","title":"b"}}}',
                    b'{"schema_version":1,"languages":{"en":{"title":NaN}}}',
                    b'\xff', b' ' * (loc.MAX_BYTES + 1)):
            with io.open(self.path, 'wb') as stream:
                stream.write(raw)
            translator = loc.Localizer('uk', self.path)
            self.assertEqual(translator.text('title'), self.catalog['uk']['title'])

    def test_bom_and_missing_file_are_safe(self):
        self.write({'fr': {'refresh': 'Recharger'}})
        with io.open(self.path, 'rb') as stream:
            raw = stream.read()
        with io.open(self.path, 'wb') as stream:
            stream.write(b'\xef\xbb\xbf' + raw)
        self.assertEqual(loc.Localizer('fr', self.path).text('refresh'), self.catalog['fr']['refresh'])
        os.unlink(self.path)
        self.assertEqual(loc.Localizer('fr', self.path).text('refresh'), 'Actualiser')

    @contextmanager
    def failing_decoder(self, raw, error_type):
        """Fail only this document at the real JSON decoder boundary."""
        document = raw.decode('utf-8-sig')
        previous = loc.json.loads
        calls = []
        def loads(value, *args, **kwargs):
            if value == document:
                calls.append(error_type)
                raise error_type('synthetic decoder recursion')
            return previous(value, *args, **kwargs)
        loc.json.loads = loads
        try:
            yield calls
        finally:
            loc.json.loads = previous

    def test_deep_catalog_uses_fallback_whether_decoder_accepts_or_rejects_nesting(self):
        # Decoder limits differ: Python 3.14 accepts this depth. Either a decoder
        # error or a parsed non-string translation must retain bundled messages.
        depth = 16384
        raw = (b'{"schema_version":1,"languages":{"uk":{"title":' +
               b'[' * depth + b'"CATALOG_NESTED_SENTINEL"' + b']' * depth + b'}}}')
        self.assertLess(len(raw), loc.MAX_BYTES)
        with io.open(self.path, 'wb') as stream:
            stream.write(raw)
        translator = loc.Localizer('uk', self.path)
        self.assertEqual(translator.language, 'uk')
        self.assertEqual(translator.messages, self.catalog['uk'])

    def test_external_decoder_recursion_retains_the_selected_bundled_language(self):
        self.write({'uk': {'title': 'CATALOG_DECODER_SENTINEL'}})
        with io.open(self.path, 'rb') as stream:
            raw = stream.read()
        for error_type in DECODER_ERRORS:
            with self.failing_decoder(raw, error_type) as calls:
                translator = loc.Localizer('uk', self.path, catalog=self.catalog)
            self.assertEqual(calls, [])
            self.assertEqual(translator.language, 'uk')
            self.assertEqual(translator.messages, self.catalog['uk'])

    def test_source_catalog_recursion_uses_the_embedded_english_fallback(self):
        import types
        source_path = os.path.join(os.path.dirname(loc.__file__), '..', '..', 'data', 'languages.json')
        with io.open(source_path, 'rb') as stream:
            raw = stream.read()
        resource_manager = types.ModuleType(str('ResMgr'))
        resource_manager.openSection = lambda unused: None
        previous_module = sys.modules.get('ResMgr')
        sys.modules['ResMgr'] = resource_manager
        try:
            for error_type in DECODER_ERRORS:
                with self.failing_decoder(raw, error_type) as calls:
                    self.assertEqual(loc.bundled_catalog(), {'en': loc.ENGLISH})
                self.assertEqual(calls, [error_type])
        finally:
            if previous_module is None:
                del sys.modules['ResMgr']
            else:
                sys.modules['ResMgr'] = previous_module

    def test_decoder_failure_does_not_discard_valid_runtime_appearance_or_sessions(self):
        config_path = os.path.join(self.directory, 'grz.sessionstats.json')
        config = {'language': 'uk', 'colors': {'window_border': '#123456'},
                  'scroll': {'speed_multiplier': 2}, 'sessions': {'instance_tab': True}}
        with io.open(config_path, 'w', encoding='utf-8') as stream:
            stream.write(loc.text_type(json.dumps(config)))
        self.write({})
        mod = Runtime(deferred_loading=False, api=FakeAPI(), data_dir=self.directory, expected_table=EXPECTED,
                      now=Clock(), window=FakeWindow(), footer_installer=lambda unused: None,
                      appearance_path=config_path, installation_dir=self.directory)
        try:
            mod.start()
            service = mod.active_service
            service.begin_battle('fixture-pending', vehicle_name='Leopard 1', map_name='Malinovka')
            saved = copy.deepcopy(service._state)
            presentation = copy.deepcopy(mod.snapshot()['appearance'])
            installation = mod._instance_session
            self.assertIn('#123456', presentation['panel_css'])
            self.assertEqual(presentation['scroll_speed'], 2)
            self.write({'uk': {'title': 'CATALOG_DECODER_SENTINEL'}})
            with io.open(self.path, 'rb') as stream:
                raw = stream.read()
            for error_type in DECODER_ERRORS:
                with self.failing_decoder(raw, error_type) as calls:
                    mod.on_action({'action': 'refresh'})
                    payload = mod.snapshot()
                self.assertEqual(calls, [])
                self.assertEqual(payload['appearance'], presentation)
                self.assertEqual(payload['localization']['language'], 'uk')
                self.assertEqual(payload['localization']['messages'], self.catalog['uk'])
                self.assertIn('instance', payload['scopes'])
                self.assertTrue(mod._instance_tab_enabled)
                self.assertIs(mod._instance_session, installation)
                self.assertIs(mod.active_service, service)
                self.assertEqual(service._state, saved)
        finally:
            mod.stop()

    def test_legacy_polish_and_canonical_warnings_translate_without_rewriting_history(self):
        old = loc.LEGACY_POLISH['runtime.backlog'].format(13)
        snapshot = {'warnings': [old, loc.ENGLISH['normalize.finance']], 'scopes': {
            'manual': {'label':'Od resetu', 'battles':[
                {'name':'Leopard 1', 'map':'Malinówka', 'id':'unchanged'},
                {'name':'Nieznany pojazd', 'map':'Mapa 42'}]}}}
        original = copy.deepcopy(snapshot)
        rendered = loc.Localizer('de').snapshot(copy.deepcopy(snapshot))
        self.assertEqual(snapshot, original)
        self.assertEqual(rendered['warnings'][0], self.catalog['de']['runtime.backlog'].format(13))
        rows = rendered['scopes']['manual']['battles']
        self.assertEqual(rows[0], original['scopes']['manual']['battles'][0])
        self.assertEqual(rows[1]['name'], self.catalog['de']['unknown.vehicle'])
        self.assertEqual(rows[1]['map'], 'Karte 42')

    def test_all_backend_warnings_round_trip_to_each_language(self):
        prefixes = ('storage.', 'core.', 'normalize.', 'health.', 'log.', 'runtime.', 'installation.')
        for code in self.catalog:
            translator = loc.Localizer(code)
            for key in loc.ENGLISH:
                if not key.startswith(prefixes):
                    continue
                english = loc.ENGLISH[key].format('1', 'game.log')
                polish = loc.LEGACY_POLISH[key].format('1', 'game.log')
                expected = self.catalog[code][key].format('1', 'game.log')
                self.assertEqual(translator.translate(english), expected, code + ':' + key)
                self.assertEqual(translator.translate(polish), expected, code + ':' + key)

    def test_native_notifications_escape_user_catalog_markup_at_final_boundary(self):
        import types
        pushed = []
        gui = types.ModuleType(str('gui'))
        gui.SystemMessages = type(str('Messages'), (), {
            'SM_TYPE': type(str('Types'), (), {'Warning': 1}),
            'pushMessage': staticmethod(lambda value, **unused: pushed.append(value))})
        previous = sys.modules.get('gui')
        sys.modules['gui'] = gui
        try:
            self.write({'en': {'runtime.garage': '<img src="private"> & test'}})
            message = '<img src="private"> & test'
            self.assertTrue(GameAPI.__new__(GameAPI).notify(message))
            self.assertEqual(pushed, ['&lt;img src="private"&gt; &amp; test'])
        finally:
            if previous is None:
                del sys.modules['gui']
            else:
                sys.modules['gui'] = previous

    def test_runtime_refresh_changes_language_without_resetting_any_statistics(self):
        config_path = os.path.join(self.directory, 'grz.sessionstats.json')
        def configure(code):
            with io.open(config_path, 'w', encoding='utf-8') as stream:
                stream.write(loc.text_type(json.dumps({'language': code})))
        configure('fr')
        api = FakeAPI()
        mod = Runtime(deferred_loading=False, api=api, data_dir=self.directory, expected_table=EXPECTED,
                      now=Clock(), window=FakeWindow(), footer_installer=lambda unused: None,
                      appearance_path=config_path, installation_dir=self.directory)
        try:
            mod.start()
            service = mod.active_service
            service.begin_battle('fixture-pending', vehicle_name='Leopard 1', map_name='Malinówka')
            self.assertEqual(mod.snapshot()['localization']['language'], 'fr')
            saved = copy.deepcopy(service._state)
            self.write({'uk': {'refresh':'Оновити зараз'}})
            configure('uk')
            mod.on_action({'action':'refresh'})
            payload = mod.snapshot()
            self.assertEqual(payload['localization']['language'], 'uk')
            self.assertEqual(payload['localization']['messages']['refresh'], self.catalog['uk']['refresh'])
            self.assertEqual(service._state, saved)
            self.assertEqual(payload['scopes']['launch']['summary']['observed_battles'], 1)
            mod._notify(loc.message('runtime.garage'))
            self.assertEqual(api.notices[-1], self.catalog['uk']['runtime.garage'])
        finally:
            mod.stop()

if __name__ == '__main__':
    unittest.main()
