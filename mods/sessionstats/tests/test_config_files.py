# -*- coding: utf-8 -*-
"""Central configuration creation/migration preserves user edits and failures."""
from __future__ import unicode_literals

import errno
import io
import json
import os
import shutil
import tempfile
import unittest

from test_config_path import changed
from grz_session_stats import config_files as files
from grz_session_stats.appearance import CONFIG_FILENAME, default_config, load_config
from grz_session_stats.localization import FILENAME as LANGUAGES_FILENAME


class ConfigFilesTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.mkdtemp(prefix='grz-config-files-')
        self.path = os.path.join(self.directory, 'mods', 'configs', CONFIG_FILENAME)
        self.legacy = os.path.join(self.directory, 'mods', '2.4.1.0', CONFIG_FILENAME)
        self.languages = os.path.join(os.path.dirname(self.path), LANGUAGES_FILENAME)
        self.old_languages = os.path.join(os.path.dirname(self.legacy), LANGUAGES_FILENAME)

    def tearDown(self):
        shutil.rmtree(self.directory)

    @staticmethod
    def write(path, raw):
        if not os.path.isdir(os.path.dirname(path)):
            os.makedirs(os.path.dirname(path))
        with io.open(path, 'wb') as handle:
            handle.write(raw)

    @staticmethod
    def read(path):
        with io.open(path, 'rb') as handle:
            return handle.read()

    def prepare(self):
        files.prepare_config(self.path, self.legacy)

    def test_missing_directory_gets_complete_defaults_and_no_language_override(self):
        self.prepare()
        self.assertEqual(json.loads(self.read(self.path).decode('utf-8')), default_config())
        self.assertEqual(load_config(self.path), default_config())
        self.assertFalse(os.path.exists(self.languages))
        self.assertFalse(os.path.exists(self.legacy))
        self.assertEqual(os.listdir(os.path.dirname(self.path)), [CONFIG_FILENAME])

    def test_existing_central_files_win_and_are_never_rewritten(self):
        self.write(self.path, b'{"language":"pl","scroll":{"speed_multiplier":2}}')
        self.write(self.languages, b'custom central translations')
        self.write(self.legacy, b'{"language":"fr"}')
        self.write(self.old_languages, b'old translations')
        before = (self.read(self.path), self.read(self.languages))
        writes = []
        def forbidden(*args, **kwargs):
            writes.append(args)
            raise IOError('Existing configuration must not be written')
        with changed(files, '_publish_new', forbidden):
            self.prepare()
            self.prepare()
        self.assertEqual(writes, [])
        self.assertEqual((self.read(self.path), self.read(self.languages)), before)
        self.assertEqual(load_config(self.path)['language'], 'pl')

    def test_legacy_configuration_is_copied_but_external_translations_are_not(self):
        raw = b'\xef\xbb\xbf{ "language": "pl", "custom_unknown": 7 }\n'
        self.write(self.legacy, raw)
        self.write(self.old_languages, b'{"schema_version":1,"languages":{}}')
        self.prepare()
        self.assertEqual(self.read(self.path), raw)
        self.assertEqual(self.read(self.legacy), raw)
        self.assertFalse(os.path.exists(self.languages))
        self.assertEqual(self.read(self.old_languages), b'{"schema_version":1,"languages":{}}')
        self.assertEqual(load_config(self.path)['language'], 'pl')
        self.write(self.path, b'{"language":"de"}')
        self.prepare()
        self.assertEqual(load_config(self.path)['language'], 'de')

    def test_existing_malformed_config_is_preserved_and_loader_uses_defaults(self):
        self.write(self.path, b'{ invalid existing config')
        self.write(self.legacy, b'{"language":"pl"}')
        self.prepare()
        self.assertEqual(self.read(self.path), b'{ invalid existing config')
        self.assertEqual(load_config(self.path), default_config())

    def test_malformed_legacy_bytes_are_preserved_for_user_repair(self):
        self.write(self.legacy, b'{ invalid legacy config')
        self.prepare()
        self.assertEqual(self.read(self.path), self.read(self.legacy))
        self.assertEqual(load_config(self.path), default_config())

    def test_oversize_legacy_config_is_not_copied_or_replaced(self):
        self.write(self.legacy, b'x' * (files.MAX_CONFIG_BYTES + 1))
        self.prepare()
        self.assertFalse(os.path.exists(self.path))
        self.assertEqual(len(self.read(self.legacy)), files.MAX_CONFIG_BYTES + 1)

    def test_unreadable_legacy_does_not_publish_defaults_over_unknown_preferences(self):
        original = files.io.open
        def denied(path, *args, **kwargs):
            if path == self.legacy:
                raise IOError(errno.EACCES, 'private failure details')
            return original(path, *args, **kwargs)
        with changed(files.io, 'open', denied):
            self.prepare()
        self.assertFalse(os.path.exists(self.path))

    def test_readonly_installation_does_not_raise_or_stop_default_loading(self):
        def denied(*args, **kwargs):
            raise OSError(errno.EACCES, 'private installation')
        with changed(files.os, 'makedirs', denied):
            self.prepare()
        self.assertFalse(os.path.exists(self.path))
        self.assertEqual(load_config(self.path), default_config())

    def test_failed_flush_does_not_publish_partial_config_and_retry_succeeds(self):
        def failed(unused):
            raise OSError(errno.ENOSPC, 'disk full')
        with changed(files.os, 'fsync', failed):
            self.prepare()
        self.assertFalse(os.path.exists(self.path))
        self.assertEqual(os.listdir(os.path.dirname(self.path)), [])
        self.prepare()
        self.assertEqual(load_config(self.path), default_config())

    @unittest.skipUnless(hasattr(os, 'link'), 'Requires POSIX hard-link fixture')
    def test_concurrent_creation_wins_without_being_overwritten(self):
        original = files.os.link
        def raced(source, destination):
            self.write(destination, b'{"language":"uk"}')
            return original(source, destination)
        with changed(files.os, 'link', raced):
            self.prepare()
        self.assertEqual(load_config(self.path)['language'], 'uk')
        self.assertEqual(os.listdir(os.path.dirname(self.path)), [CONFIG_FILENAME])

    def test_windows_publication_uses_rename_and_keeps_concurrent_destination(self):
        def raced(source, destination):
            self.write(destination, b'{"language":"es"}')
            raise OSError(errno.EEXIST, 'Windows destination exists')
        with changed(files.os, 'name', 'nt'):
            with changed(files.os, 'rename', raced):
                self.prepare()
        self.assertEqual(load_config(self.path)['language'], 'es')
        self.assertEqual(os.listdir(os.path.dirname(self.path)), [CONFIG_FILENAME])

    def test_unicode_installation_path(self):
        base = os.path.join(self.directory, '\u017b\u00f3\u0142\u0107')
        self.path = os.path.join(base, 'mods', 'configs', CONFIG_FILENAME)
        self.legacy = os.path.join(base, 'mods', '2.4.1.0', CONFIG_FILENAME)
        self.prepare()
        self.assertEqual(load_config(self.path), default_config())
