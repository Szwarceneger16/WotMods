# -*- coding: utf-8 -*-
"""GUI language writes use the existing config and preserve statistics and user settings."""
from __future__ import unicode_literals
import copy
import io
import json
import os
import shutil
import tempfile
import unittest
import test_native_pagination as paging
from grz_session_stats import config_files
from grz_session_stats.appearance import MAX_CONFIG_BYTES
from grz_session_stats.runtime import Runtime


class LanguageFileTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.mkdtemp(prefix='grz-language-save-')
        self.path = os.path.join(self.directory, 'settings.json')
    def tearDown(self):
        shutil.rmtree(self.directory)
    def write(self, raw):
        with io.open(self.path,'wb') as handle: handle.write(raw)
    def read(self):
        with io.open(self.path,'rb') as handle: return handle.read()
    def test_only_language_changes_and_unicode_and_unknown_fields_survive(self):
        original={'language':'en','colors':{'window_border':'#123456'},'custom':'Zażółć','scroll':{'speed_multiplier':2}}
        self.write(json.dumps(original,ensure_ascii=False).encode('utf-8'))
        self.assertTrue(config_files.save_language(self.path,'pl'))
        original['language']='pl'
        self.assertEqual(json.loads(self.read().decode('utf-8')),original)
        self.assertEqual(os.listdir(self.directory),['settings.json'])
    def test_missing_config_is_created_with_only_a_supported_choice(self):
        self.assertTrue(config_files.save_language(self.path,'auto'))
        self.assertEqual(json.loads(self.read().decode()),{'language':'auto'})
    def test_malformed_oversized_duplicate_and_future_config_are_not_overwritten(self):
        for raw in [b'{',b'[]',b'{"language":"en","language":"pl"}',b'{"schema_version":2}',b'{"schema_version":true}',b'{"schema_version":1.0}',b'{"x":NaN}',b' '*(MAX_CONFIG_BYTES+1)]:
            self.write(raw)
            self.assertFalse(config_files.save_language(self.path,'de'))
            self.assertEqual(self.read(),raw)
    def test_invalid_choices_do_not_write(self):
        self.write(b'{"language":"en"}')
        for code in ['pt-BR','../pl','PL','pl\n',None,True,{},[]]:
            self.assertFalse(config_files.save_language(self.path,code))
            self.assertEqual(self.read(),b'{"language":"en"}')
    def test_failed_atomic_replace_preserves_previous_config_and_removes_temp(self):
        original=config_files._replace_file
        self.write(b'{"language":"en"}')
        def fail(*unused): raise OSError('simulated replace failure')
        config_files._replace_file=fail
        try: self.assertFalse(config_files.save_language(self.path,'fr'))
        finally: config_files._replace_file=original
        self.assertEqual(self.read(),b'{"language":"en"}')
        self.assertEqual(os.listdir(self.directory),['settings.json'])


class NativeLanguageTests(unittest.TestCase):
    inject_module=paging.NativePaginationTests.inject_module
    payload=paging.NativePaginationTests.payload
    def setUp(self):
        paging.NativePaginationTests.setUp(self)
        self.path=os.path.join(self.directory,'grz.sessionstats.json')
        self.document={'language':'en','colors':{'window_border':'#123456'},'scroll':{'speed_multiplier':2},'sessions':{'instance_tab':True}}
        with io.open(self.path,'w',encoding='utf-8') as handle: handle.write(json.dumps(self.document))
        self.mod.data_dir=self.directory
        self.mod._appearance_override_path=self.path
        self.mod._load_appearance();self.window.refresh()
    def tearDown(self): paging.NativePaginationTests.tearDown(self)
    def command(self,code,account='EU:7'):
        self.window._model.onAction({'action':'language','language':code,'account_key':account})
    def test_gui_choice_persists_and_updates_immediately_without_changing_history(self):
        service=self.mod.active_service;saved=copy.deepcopy(service._state)
        for code in ['pl','fr','de','es','uk','ru','en','auto']:
            self.mod.api.client_language=lambda:'pl'
            self.command(code)
            payload=self.payload()['localization']
            self.assertEqual(payload['selected'],code)
            self.assertEqual(payload['language'],'pl' if code=='auto' else code)
            with io.open(self.path,'r',encoding='utf-8') as handle: written=json.load(handle)
            expected=dict(self.document,language=code)
            self.assertEqual(written,expected)
            self.assertIs(self.mod.active_service,service)
            self.assertEqual(service._state,saved)
            reloaded=Runtime(api=self.mod.api,appearance_path=self.path)
            reloaded._load_appearance()
            self.assertEqual(reloaded._localizer.selected,code)
    def test_invalid_or_stale_requests_preserve_config_and_selected_language(self):
        self.command('fr',account='EU:other')
        self.command('pt-BR')
        self.assertEqual(self.payload()['localization']['selected'],'en')
        with io.open(self.path,'r',encoding='utf-8') as handle: self.assertEqual(json.load(handle),self.document)
    def test_manual_config_edit_is_read_on_refresh(self):
        self.command('fr')
        with io.open(self.path,'w',encoding='utf-8') as handle: handle.write(json.dumps(dict(self.document,language='uk')))
        self.mod.on_action({'action':'refresh'})
        self.assertEqual(self.payload()['localization']['selected'],'uk')


if __name__=='__main__': unittest.main()
