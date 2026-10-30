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
    def test_native_byte_string_locale_is_normalized_and_non_ascii_is_rejected(self):
        self.write(b'{"language":"en","custom":7}')
        self.assertTrue(config_files.save_language(self.path,b'pl'))
        self.assertEqual(json.loads(self.read().decode('utf-8')),{'language':'pl','custom':7})
        for code in [b'\xff', b'PL', b'pl\n', b'../pl']:
            self.assertFalse(config_files.save_language(self.path,code))
        self.assertEqual(json.loads(self.read().decode('utf-8'))['language'],'pl')

    def test_embedded_windows_without_ctypes_saves_and_cleans_backup(self):
        import sys
        import types
        previous_module=sys.modules.get('ctypes');previous_name=config_files.os.name
        sys.modules['ctypes']=types.ModuleType(str('ctypes'));config_files.os.name='nt'
        self.write(b'{"language":"en","custom":7}')
        try: self.assertTrue(config_files.save_language(self.path,b'fr'))
        finally:
            config_files.os.name=previous_name
            if previous_module is None: del sys.modules['ctypes']
            else: sys.modules['ctypes']=previous_module
        self.assertEqual(json.loads(self.read().decode('utf-8')),{'language':'fr','custom':7})
        self.assertEqual(os.listdir(self.directory),['settings.json'])

    def test_embedded_windows_failed_publication_restores_previous_config(self):
        self.write(b'{"language":"en"}')
        source=os.path.join(self.directory,'new.tmp')
        with io.open(source,'wb') as handle: handle.write(b'{"language":"fr"}')
        rename=config_files.os.rename
        def fail_source(src,dst):
            if src==source: raise OSError('simulated publication failure')
            rename(src,dst)
        config_files.os.rename=fail_source
        try:
            with self.assertRaises(OSError): config_files._replace_without_ctypes(source,self.path)
        finally: config_files.os.rename=rename
        self.assertEqual(self.read(),b'{"language":"en"}')
        self.assertFalse(os.path.exists(self.path+'.language-backup'))

    def test_interrupted_windows_replacement_recovers_before_creating_defaults(self):
        self.write(b'{"language":"uk","custom":7}')
        os.rename(self.path,self.path+'.language-backup')
        config_files.prepare_config(self.path,os.path.join(self.directory,'missing.json'))
        self.assertEqual(self.read(),b'{"language":"uk","custom":7}')
        self.assertEqual(os.listdir(self.directory),['settings.json'])
    def test_windows_atomic_replacement_uses_unicode_and_replace_existing_flags(self):
        import sys
        import types
        calls=[]
        class Move(object):
            def __call__(self,*args): calls.append(args);return 1
        move=Move()
        fake=types.ModuleType(str('ctypes'))
        fake.wintypes=type(str('Types'),(),{'LPCWSTR':str,'DWORD':int,'BOOL':bool})
        fake.WinDLL=lambda name,**kwargs:type(str('Kernel'),(),{'MoveFileExW':move})()
        previous_module=sys.modules.get('ctypes');previous_name=config_files.os.name
        sys.modules['ctypes']=fake;config_files.os.name='nt'
        try: config_files._replace_file('źródło.tmp','ustawienia.json')
        finally:
            config_files.os.name=previous_name
            if previous_module is None: del sys.modules['ctypes']
            else: sys.modules['ctypes']=previous_module
        self.assertEqual(calls,[('źródło.tmp','ustawienia.json',0x1|0x8)])

    def test_concurrent_manual_edit_is_preserved(self):
        self.write(b'{"language":"en"}')
        original=config_files.tempfile.mkstemp
        def changed(*args,**kwargs):
            self.write(b'{"language":"uk","custom":7}')
            return original(*args,**kwargs)
        config_files.tempfile.mkstemp=changed
        try: self.assertFalse(config_files.save_language(self.path,'fr'))
        finally: config_files.tempfile.mkstemp=original
        self.assertEqual(self.read(),b'{"language":"uk","custom":7}')

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
    inject_module=paging.NativePaginationTests.__dict__['inject_module']
    payload=paging.NativePaginationTests.__dict__['payload']
    def setUp(self):
        paging.NativePaginationTests.__dict__['setUp'](self)
        self.path=os.path.join(self.directory,'grz.sessionstats.json')
        self.document={'language':'en','colors':{'window_border':'#123456'},'scroll':{'speed_multiplier':2},'sessions':{'instance_tab':True}}
        with io.open(self.path,'wb') as handle: handle.write(json.dumps(self.document).encode('utf-8'))
        self.mod.data_dir=self.directory
        self.mod._appearance_override_path=self.path
        self.mod._load_appearance();self.window.refresh()
    def tearDown(self): paging.NativePaginationTests.__dict__['tearDown'](self)
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
        with io.open(self.path,'wb') as handle: handle.write(json.dumps(dict(self.document,language='uk')).encode('utf-8'))
        self.mod.on_action({'action':'refresh'})
        self.assertEqual(self.payload()['localization']['selected'],'uk')

    def test_actual_python2_byte_command_changes_language_and_survives_reload(self):
        self.command(b'pl')
        self.assertEqual(self.payload()['localization']['selected'],'pl')
        self.assertEqual(self.payload()['localization']['messages']['refresh'],'Odśwież')
        reloaded=Runtime(api=self.mod.api,appearance_path=self.path)
        reloaded._load_appearance()
        self.assertEqual(reloaded._localizer.selected,'pl')


if __name__=='__main__': unittest.main()
