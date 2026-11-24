# -*- coding: utf-8 -*-
"""Window preferences share atomic configuration saves and native placement."""
from __future__ import unicode_literals

import copy
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unittest

import test_native_pagination as paging
import test_runtime as native
from grz_session_stats import appearance, config_files


class WindowConfigTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.mkdtemp(prefix='grz-window-settings-')
        self.path = os.path.join(self.directory, 'settings.json')

    def tearDown(self):
        shutil.rmtree(self.directory)

    def write(self, document):
        with io.open(self.path, 'wb') as handle:
            handle.write(json.dumps(document, ensure_ascii=False).encode('utf-8'))

    def read(self):
        with io.open(self.path, 'r', encoding='utf-8') as handle:
            return json.load(handle)

    def test_partial_window_save_preserves_language_and_unknown_root_and_window_fields(self):
        document = {'language': 'pl', 'custom': 'Zażółć', 'colors': {'window_border': '#abc'},
                    'window': {'restored_width': 900, 'custom': {'keep': True}}}
        self.write(document)
        self.assertTrue(config_files.save_window_settings(self.path, {
            'background_transparency': 75, 'maximized': True, 'restored_height': 650}))
        document['window'].update(background_transparency=75, maximized=True, restored_height=650)
        self.assertEqual(self.read(), document)
        self.assertTrue(config_files.save_language(self.path, 'fr'))
        document['language'] = 'fr'
        self.assertEqual(self.read(), document)
        expected = ['settings.json'] if os.name == 'nt' else ['.settings.json.lock', 'settings.json']
        self.assertEqual(sorted(os.listdir(self.directory)), expected)

    def test_invalid_updates_and_malformed_window_section_leave_original_bytes(self):
        document = {'language': 'en', 'window': {'maximized': False}}
        self.write(document)
        for values in ({}, {'maximized': 1}, {'background_transparency': True},
                       {'background_transparency': 101}, {'background_transparency': float('nan')},
                       {'restored_width': 0}, {'restored_height': 32769}, {'unknown': 4}):
            self.assertFalse(config_files.save_window_settings(self.path, values))
            self.assertEqual(self.read(), document)
        self.write({'language': 'en', 'window': []})
        self.assertFalse(config_files.save_window_settings(self.path, {'maximized': True}))
        self.assertEqual(self.read(), {'language': 'en', 'window': []})

    def test_missing_file_is_created_with_only_the_validated_update(self):
        self.assertTrue(config_files.save_window_settings(self.path, {'maximized': True}))
        self.assertEqual(self.read(), {'window': {'maximized': True}})

    def test_concurrent_edit_and_failed_publication_preserve_the_actual_file(self):
        self.write({'language': 'en'})
        original = config_files.tempfile.mkstemp

        def edited(*args, **kwargs):
            self.write({'language': 'uk', 'custom': 42})
            return original(*args, **kwargs)

        config_files.tempfile.mkstemp = edited
        try:
            self.assertFalse(config_files.save_window_settings(self.path, {'maximized': True}))
        finally:
            config_files.tempfile.mkstemp = original
        self.assertEqual(self.read(), {'language': 'uk', 'custom': 42})
        replace = config_files._replace_file

        def failed(*args):
            raise OSError('fixture publication failure')

        config_files._replace_file = failed
        try:
            self.assertFalse(config_files.save_window_settings(self.path, {'maximized': True}))
        finally:
            config_files._replace_file = replace
        self.assertEqual(self.read(), {'language': 'uk', 'custom': 42})

    def test_simultaneous_language_and_window_writes_preserve_both_changes(self):
        self.write({'language': 'en', 'window': {'background_transparency': 0}})
        first_ready = threading.Event()
        allow_first = threading.Event()
        second_started = threading.Event()
        second_done = threading.Event()
        results = {}
        replace = config_files._replace_file

        def delay_language_replace(source, destination):
            with io.open(source, 'r', encoding='utf-8') as handle:
                if json.load(handle)['language'] == 'pl' and not first_ready.is_set():
                    first_ready.set()
                    if not allow_first.wait(5):
                        raise IOError('Timed out before publishing the first update.')
            replace(source, destination)

        def change_language():
            results['language'] = config_files.save_language(self.path, 'pl')

        def change_window():
            second_started.set()
            try:
                results['window'] = config_files.save_window_settings(
                    self.path, {'background_transparency': 25})
            finally:
                second_done.set()

        first = threading.Thread(target=change_language)
        second = threading.Thread(target=change_window)
        config_files._replace_file = delay_language_replace
        first.start()
        try:
            self.assertTrue(first_ready.wait(5))
            second.start()
            self.assertTrue(second_started.wait(5))
            self.assertFalse(second_done.wait(0.25))
        finally:
            allow_first.set()
            first.join(5)
            if second.ident is not None:
                second.join(5)
            config_files._replace_file = replace
        self.assertEqual(results, {'language': True, 'window': True})
        self.assertEqual(self.read(), {'language': 'pl', 'window': {'background_transparency': 25}})

    def test_another_process_cannot_save_while_the_configuration_is_locked(self):
        self.write({'language': 'en'})
        source = os.path.dirname(os.path.dirname(config_files.__file__))
        command = (
            'import sys; sys.path.insert(0, sys.argv[1]); '
            'from grz_session_stats.config_files import save_window_settings; '
            'print(int(save_window_settings(sys.argv[2], {"maximized": True})))'
        )
        with config_files._settings_lock(self.path):
            child = subprocess.Popen(
                [sys.executable, '-B', '-c', command, source, self.path], stdout=subprocess.PIPE)
            deadline = time.time() + 5
            while child.poll() is None and time.time() < deadline:
                time.sleep(0.01)
            if child.poll() is None:
                child.kill()
                child.communicate()
                self.fail('The second process did not report lock contention.')
            result, unused = child.communicate()
            self.assertEqual(child.returncode, 0)
            self.assertEqual(result.strip(), b'0')
            self.assertEqual(self.read(), {'language': 'en'})
        self.assertTrue(config_files.save_window_settings(self.path, {'maximized': True}))
        self.assertEqual(self.read(), {'language': 'en', 'window': {'maximized': True}})

    @unittest.skipUnless(os.name == 'nt', 'Requires Windows delete-on-close locking')
    def test_terminated_settings_writer_does_not_leave_a_stale_lock(self):
        self.write({'language': 'en'})
        source = os.path.dirname(os.path.dirname(config_files.__file__))
        ready = os.path.join(self.directory, 'owner.ready')
        command = (
            'import sys, time\n'
            'sys.path.insert(0, sys.argv[1])\n'
            'from grz_session_stats.config_files import _settings_lock\n'
            'with _settings_lock(sys.argv[2]):\n'
            '    open(sys.argv[3], "w").close()\n'
            '    time.sleep(30)\n'
        )
        child = subprocess.Popen([sys.executable, '-B', '-c', command, source, self.path, ready])
        try:
            deadline = time.time() + 5
            while not os.path.isfile(ready) and child.poll() is None and time.time() < deadline:
                time.sleep(0.01)
            self.assertTrue(os.path.isfile(ready))
            self.assertFalse(config_files.save_language(self.path, 'pl'))
        finally:
            if child.poll() is None:
                child.kill()
            child.wait()
        self.assertTrue(config_files.save_language(self.path, 'pl'))
        self.assertEqual(self.read(), {'language': 'pl'})

    def test_window_and_wide_card_validation_is_bounded_and_does_not_share_defaults(self):
        value = appearance.validate_config({'window': {'background_transparency': 100, 'maximized': True,
            'restored_width': 860, 'restored_height': False}, 'wide_cards': {'battles': 1200, 'maps': 479}})
        self.assertEqual(value['window'], {'background_transparency': 100, 'maximized': True,
            'restored_width': 860, 'restored_height': 620})
        self.assertEqual(value['wide_cards']['battles'], 1200)
        self.assertEqual(value['wide_cards']['maps'], 720)
        result = appearance.build_presentation(value)
        result['window_settings']['maximized'] = False
        result['wide_card_widths']['maps'] = 999
        self.assertTrue(value['window']['maximized'])
        self.assertEqual(value['wide_cards']['maps'], 720)
        self.assertEqual(appearance.window_settings_patch({'maximized': b'true', 'restored_width': b'900'}, True),
                         {'maximized': True, 'restored_width': 900})
        self.assertIsNone(appearance.window_settings_patch({'maximized': '1'}, True))

    def test_fractional_window_values_are_rejected_in_config_and_commands(self):
        values = {'background_transparency': 35.5, 'restored_width': 900.5, 'restored_height': 650.5}
        normalized = appearance.validate_config({'window': dict(values, maximized=True)})['window']
        self.assertEqual(normalized, {'background_transparency': 0, 'maximized': True,
                                     'restored_width': 700, 'restored_height': 620})
        self.write({'language': 'pl'})
        for key, value in values.items():
            self.assertIsNone(appearance.window_settings_patch({key: str(value)}, command=True))
            self.assertFalse(config_files.save_window_settings(self.path, {key: value}))
        self.assertEqual(self.read(), {'language': 'pl'})


class WindowSettingsRuntimeTests(unittest.TestCase):
    inject_module = paging.NativePaginationFixture.__dict__['inject_module']
    payload = paging.NativePaginationFixture.__dict__['payload']

    def setUp(self):
        paging.NativePaginationFixture.__dict__['setUp'](self)
        self.addCleanup(paging.NativePaginationFixture.__dict__['tearDown'], self)
        self.path = os.path.join(self.directory, 'settings.json')
        self.document = {'language': 'pl', 'custom': 42, 'window': {'custom': 'retain'}}
        with io.open(self.path, 'w', encoding='utf-8') as handle:
            handle.write(json.dumps(self.document, ensure_ascii=False))
        self.mod._appearance_override_path = self.path
        self.mod._load_appearance()
        self.window.refresh()

    def command(self, **values):
        command = {'action': 'window_settings', 'account_key': 'EU:7', 'request_id': 'window-1'}
        command.update(values)
        self.window._model.onAction(command)

    def settings_update(self):
        payload = self.payload()
        return payload.get('window_settings_update') or payload['appearance']

    def test_command_atomically_saves_and_acknowledges_without_mutating_history(self):
        before = copy.deepcopy(self.mod.active_service._state)
        snapshots = []
        original_snapshot = self.window._snapshot

        def snapshot():
            snapshots.append(True)
            return original_snapshot()

        self.window._snapshot = snapshot
        self.command(maximized='true', restored_width='900', restored_height='650', background_transparency='55')
        self.assertEqual(snapshots, [])
        data = self.payload()['window_settings_update']
        self.assertEqual(data['account_key'], 'EU:7')
        self.assertEqual(self.window._preferred_size, (900, 650))
        self.assertTrue(self.window._maximized)
        self.assertEqual(data['window_settings'], {'maximized': True, 'restored_width': 900,
            'restored_height': 650, 'background_transparency': 55})
        self.assertEqual(data['window_settings_result'], {'request_id': 'window-1', 'saved': True})
        with io.open(self.path, 'r', encoding='utf-8') as handle:
            saved = json.load(handle)
        self.assertEqual(saved['language'], 'pl')
        self.assertEqual(saved['custom'], 42)
        self.assertEqual(saved['window']['custom'], 'retain')
        self.assertEqual(self.mod.active_service._state, before)

    def test_failed_save_publishes_rollback_and_false_ack(self):
        replace = config_files._replace_file

        def failed(*args):
            raise OSError('fixture publication failure')

        config_files._replace_file = failed
        try:
            self.command(background_transparency='80')
        finally:
            config_files._replace_file = replace
        data = self.settings_update()
        self.assertEqual(data['window_settings']['background_transparency'], 0)
        self.assertEqual(data['window_settings_result'], {'request_id': 'window-1', 'saved': False})

    def test_rejected_concurrent_write_reloads_the_external_values_before_ack(self):
        original = config_files.tempfile.mkstemp

        def edited(*args, **kwargs):
            changed = copy.deepcopy(self.document)
            changed['language'] = 'en'
            changed['window']['background_transparency'] = 35
            with io.open(self.path, 'w', encoding='utf-8') as handle:
                handle.write(json.dumps(changed, ensure_ascii=False))
            return original(*args, **kwargs)

        config_files.tempfile.mkstemp = edited
        try:
            self.command(background_transparency='80')
        finally:
            config_files.tempfile.mkstemp = original
        data = self.payload()['appearance']
        self.assertEqual(data['window_settings']['background_transparency'], 35)
        self.assertEqual(data['window_settings_result'], {'request_id': 'window-1', 'saved': False})
        self.assertEqual(self.payload()['localization']['selected'], 'en')

    def test_stale_and_invalid_commands_never_write_and_refresh_reloads_external_values(self):
        self.command(account_key='EU:other', maximized='true')
        self.command(maximized='1')
        self.assertFalse(self.settings_update()['window_settings_result']['saved'])
        self.command(maximized='true', unexpected='discard')
        self.assertFalse(self.settings_update()['window_settings_result']['saved'])
        with io.open(self.path, 'r', encoding='utf-8') as handle:
            self.assertEqual(json.load(handle), self.document)
        self.document['window'].update(maximized=True, restored_width=840, background_transparency=35)
        with io.open(self.path, 'w', encoding='utf-8') as handle:
            handle.write(json.dumps(self.document, ensure_ascii=False))
        self.mod.on_action({'action': 'refresh'})
        self.assertTrue(self.payload()['appearance']['window_settings']['maximized'])
        self.assertEqual(self.payload()['appearance']['window_settings']['background_transparency'], 35)


class NativeWindowMaximizeTests(unittest.TestCase):
    setUp = native.NativeBindingTests.__dict__['setUp']
    tearDown = native.NativeBindingTests.__dict__['tearDown']
    inject_module = native.NativeBindingTests.__dict__['inject_module']

    def test_maximize_uses_parent_pixels_at_both_scales_and_restore_uses_saved_size(self):
        for scale in (1, 2):
            self.main.size = (1920 * scale, 1080 * scale)
            self.loader.scale = float(scale)
            self.stats['appearance'] = {'window_settings': {'maximized': True,
                'restored_width': 700, 'restored_height': 620}}
            self.assertTrue(self.window.open())
            self.window.resize(1920 * scale - 20, 1080 * scale - 20)
            self.assertEqual(self.window._window.position, (10, 10))
            self.assertEqual(self.window._fallback_size(self.window._viewport()), (1920 * scale - 20, 1080 * scale - 20))
            self.stats['appearance']['window_settings']['maximized'] = False
            self.window.refresh()
            self.window.resize(700 * scale, 620 * scale)
            self.assertEqual(self.window._window.position, (610 * scale, 230 * scale))
            self.assertEqual(json.loads(self.window._model._payload)['window_size'], [700, 620])
            self.window.close()

    def test_persisting_an_ordinary_resize_does_not_recenter_a_player_moved_window(self):
        settings = {'maximized': False, 'restored_width': 700, 'restored_height': 620}
        self.stats['appearance'] = {'window_settings': settings}
        self.assertTrue(self.window.open())
        self.window._on_drag(True)
        self.window._window.drag_surface(130, 100)
        self.window._on_drag(False)
        settings['restored_width'] = 800
        self.window.refresh()
        self.window.resize(800, 620)
        self.assertTrue(self.window._user_position)
        self.assertEqual(self.window._window.position, (130, 100))


if __name__ == '__main__':
    unittest.main()
