# -*- coding: utf-8 -*-
"""Physical configuration discovery; no installed game or package mutation."""
from __future__ import unicode_literals

import contextlib
import io
import logging
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src'))
from grz_session_stats import config_path as cp, VERSION

try:
    import builtins
except ImportError:
    import __builtin__ as builtins


class Capture(logging.Handler):
    def __init__(self):
        logging.Handler.__init__(self)
        self.records = []

    def emit(self, record):
        self.records.append(record)


class Resources(object):
    def __init__(self, xml=None, app=None, fail=False):
        self.xml, self.app, self.fail = xml, app, fail
        self.calls = []

    def resolveToAbsolutePath(self, path):
        self.calls.append(path)
        if self.fail:
            raise IOError('private resolver detail')
        return self.xml

    def appDirectory(self):
        return self.app


@contextlib.contextmanager
def changed(owner, name, value):
    before = getattr(owner, name)
    setattr(owner, name, value)
    try:
        yield
    finally:
        setattr(owner, name, before)


class ConfigPathTests(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix='grz-config-path-')
        self.package = 'grz.sessionstats_' + VERSION + '.wotmod'
        self.capture = Capture()
        self.old_disabled = cp.LOG.disabled
        self.old_level = cp.LOG.level
        self.old_propagate = cp.LOG.propagate
        self.old_global_disabled = logging.root.manager.disable
        logging.disable(logging.NOTSET)
        cp.LOG.disabled = False
        cp.LOG.setLevel(logging.INFO)
        cp.LOG.propagate = False
        cp.LOG.addHandler(self.capture)

    def tearDown(self):
        cp.LOG.removeHandler(self.capture)
        cp.LOG.disabled = self.old_disabled
        cp.LOG.setLevel(self.old_level)
        cp.LOG.propagate = self.old_propagate
        logging.disable(self.old_global_disabled)
        shutil.rmtree(self.root)

    def write(self, path, data=b''):
        parent = os.path.dirname(path)
        if not os.path.isdir(parent):
            os.makedirs(parent)
        with io.open(path, 'wb') as handle:
            handle.write(data)
        return path

    def game(self, name='game', entries=None):
        base = os.path.join(self.root, name)
        if entries is None:
            entries = [('./mods/2.4.1.0', 'recursive')]
        parts = ['<root><Paths><Path>./res_mods/2.4.1.0</Path>']
        for directory, mode in entries:
            text = directory.replace('&', '&amp;').replace('<', '&lt;')
            parts.append('<Path mask="*.wotmod" mode="{0}" root="res">{1}</Path>'.format(mode, text))
        parts.append('</Paths></root>')
        self.write(os.path.join(base, 'paths.xml'), ''.join(parts).encode('utf-8'))
        return base

    def test_installation_root_is_stable_across_client_version_directories(self):
        base = self.game()
        resources = Resources(xml=os.path.join(base, 'paths.xml'))
        self.assertEqual(cp.find_installation_root(resources), os.path.realpath(base))
        self.game(entries=[('./mods/2.5.0.0', 'recursive')])
        self.assertEqual(cp.find_installation_root(resources), os.path.realpath(base))

    def test_installation_root_does_not_merge_ambiguous_fallback_locations(self):
        first = self.game('game-a')
        second = self.game('game-b')
        self.assertIsNone(cp.find_installation_root(Resources(app=first), cwd=second))

    def test_ambiguous_authoritative_bytes_do_not_select_a_third_installation(self):
        first = self.game('\u00e9')
        self.game('\u00c3\u00a9')
        fallback = self.game('fallback')
        resources = Resources(xml=os.path.join(first, 'paths.xml').encode('utf-8'), app=fallback)
        with changed(sys, 'getfilesystemencoding', lambda: 'cp1252'):
            with self.assertRaises(cp._LocationError):
                cp._physical_xml(resources.xml)
            self.assertIsNone(cp.find_installation_root(resources, cwd=fallback))

    def test_installation_root_falls_back_when_resolver_has_no_physical_path(self):
        fallback = self.game('fallback')
        for resources in (Resources(app=fallback), Resources(app=fallback, fail=True)):
            self.assertEqual(cp.find_installation_root(resources, cwd=fallback),
                             os.path.realpath(fallback))

    def test_invalid_authoritative_installation_xml_does_not_select_another_game(self):
        first = self.game('game-a')
        second = self.game('game-b')
        path = self.write(os.path.join(first, 'paths.xml'), b'<invalid>')
        self.assertIsNone(cp.find_installation_root(Resources(xml=path, app=second), cwd=second))

    def install(self, base, subdir='mods/2.4.1.0', name=None):
        return self.write(os.path.join(base, subdir, name or self.package), b'package fixture')

    def expected(self, base):
        return os.path.join(base, 'mods', 'configs', cp.CONFIG_FILENAME)

    def locate(self, base, **kwargs):
        kwargs.setdefault('resmgr', Resources(os.path.join(base, 'paths.xml')))
        kwargs.setdefault('cwd', self.root)
        return cp.find_config_path(**kwargs)

    def failed(self, result, code):
        self.assertIsNone(result)
        self.assertEqual(len(self.capture.records), 1)
        record = self.capture.records[0]
        self.assertEqual(record.levelno, logging.WARNING)
        self.assertIn('code=' + code, record.getMessage())
        self.assertIsNone(record.exc_info)
        self.assertNotIn(self.root, record.getMessage())

    def test_default_filename_returns_central_absent_json_without_writing_it(self):
        base = self.game()
        package = self.install(base)
        resource = Resources(os.path.join(base, 'paths.xml'))
        result = self.locate(base, resmgr=resource)
        self.assertEqual(result, self.expected(base))
        self.assertTrue(os.path.isabs(result))
        self.assertFalse(os.path.exists(result))
        self.assertEqual(resource.calls, ['../paths.xml'])
        self.assertEqual(self.capture.records, [])

    def test_active_xml_wins_over_old_and_higher_version_directories(self):
        base = self.game()
        package = self.install(base)
        self.install(base, 'mods/0.9.1.0')
        self.install(base, 'mods/99.9.9.9')
        self.assertEqual(self.locate(base), self.expected(base))

    def test_configuration_path_survives_client_version_change(self):
        base = self.game()
        self.install(base)
        before = self.locate(base)
        self.game(entries=[('./mods/2.5.0.0', 'recursive')])
        self.install(base, 'mods/2.5.0.0')
        self.assertEqual(self.locate(base), before)

    def test_prepare_migrates_only_from_the_active_physical_package(self):
        base = self.game()
        package = self.install(base, 'mods/2.4.1.0/custom/stats')
        legacy = self.write(os.path.join(os.path.dirname(package), cp.CONFIG_FILENAME), b'{"language":"pl"}')
        self.write(os.path.join(base, 'mods', '99.9.9.9', cp.CONFIG_FILENAME), b'{"language":"fr"}')
        path = cp.prepare_config_path(resmgr=Resources(os.path.join(base, 'paths.xml')), cwd=self.root)
        self.assertEqual(path, self.expected(base))
        with io.open(path, 'rb') as handle:
            self.assertEqual(handle.read(), b'{"language":"pl"}')
        self.assertTrue(os.path.isfile(legacy))

    def test_prepare_does_not_write_to_either_ambiguous_installation(self):
        first, second = self.game('one'), self.game('two')
        self.install(first)
        self.install(second)
        self.assertIsNone(cp.prepare_config_path(resmgr=Resources(app=first), cwd=second))
        self.assertFalse(os.path.exists(os.path.dirname(self.expected(first))))
        self.assertFalse(os.path.exists(os.path.dirname(self.expected(second))))

    @unittest.skipUnless(hasattr(os, 'symlink'), 'No symlink support')
    def test_shared_configs_target_does_not_disambiguate_two_installations(self):
        first, second = self.game('one'), self.game('two')
        self.install(first)
        self.install(second)
        shared = os.path.join(self.root, 'shared-configs')
        os.makedirs(shared)
        try:
            for base in (first, second):
                os.symlink(shared, os.path.dirname(self.expected(base)))
        except (OSError, NotImplementedError):
            self.skipTest('Creating symlinks is unavailable')
        self.assertIsNone(cp.prepare_config_path(resmgr=Resources(app=first), cwd=second))
        self.assertEqual(os.listdir(shared), [])

    def test_old_inactive_version_config_is_not_migrated(self):
        base = self.game()
        self.install(base)
        self.write(os.path.join(base, 'mods', '0.9.1.0', cp.CONFIG_FILENAME), b'{"language":"fr"}')
        path = cp.prepare_config_path(resmgr=Resources(os.path.join(base, 'paths.xml')), cwd=self.root)
        from grz_session_stats.appearance import load_config
        self.assertEqual(load_config(path)['language'], 'auto')

    def test_recursive_package_still_uses_installation_configs_directory(self):
        base = self.game()
        package = self.install(base, 'mods/2.4.1.0/custom/stats')
        self.assertEqual(self.locate(base), self.expected(base))

    def test_nonrecursive_root_ignores_nested_copy(self):
        base = self.game(entries=[('./mods/2.4.1.0', '')])
        package = self.install(base)
        self.install(base, 'mods/2.4.1.0/subfolder')
        self.assertEqual(self.locate(base), self.expected(base))
        os.remove(package)
        self.failed(self.locate(base), 'active_package_missing')

    def test_duplicate_active_packages_fail_without_guessing(self):
        base = self.game()
        self.install(base)
        self.install(base, 'mods/2.4.1.0/copy')
        self.failed(self.locate(base), 'multiple_active_packages')

    def test_repeated_and_overlapping_roots_do_not_create_false_copies(self):
        base = self.game(entries=[('./mods/2.4.1.0', 'recursive'),
                                 ('./mods/2.4.1.0/.', ''),
                                 ('./mods/2.4.1.0/sub', 'recursive')])
        package = self.install(base, 'mods/2.4.1.0/sub')
        self.assertEqual(self.locate(base), self.expected(base))

    def test_renamed_package_and_json_alone_do_not_identify_this_mod(self):
        base = self.game()
        renamed = self.install(base, name='renamed.wotmod')
        self.write(self.expected(base), b'{}')
        self.failed(self.locate(base), 'active_package_missing')

    def test_explicit_package_name_can_identify_a_known_alternative(self):
        base = self.game()
        package = self.install(base, name='test.stats_4.wotmod')
        self.assertEqual(self.locate(base, package_name='test.stats_4.wotmod'), self.expected(base))

    def test_authoritative_malformed_xml_never_uses_another_installation(self):
        active, other = self.game('active'), self.game('other')
        self.install(other)
        self.write(os.path.join(active, 'paths.xml'), b'<private broken value')
        self.failed(self.locate(active, cwd=other, resmgr=Resources(os.path.join(active, 'paths.xml'), app=other)),
                    'xml_parse_failed')

    def test_authoritative_missing_package_never_uses_old_cwd_installation(self):
        active, other = self.game('active'), self.game('other')
        self.install(other)
        self.failed(self.locate(active, cwd=other), 'active_package_missing')

    def test_failed_resolver_uses_validated_app_directory_parent(self):
        base = self.game()
        package = self.install(base)
        self.assertEqual(self.locate(base, resmgr=Resources(app=os.path.join(base, 'win64'), fail=True)),
                         self.expected(base))

    def test_fallback_cwd_parent_and_duplicate_candidates_are_unambiguous(self):
        base = self.game()
        package = self.install(base)
        self.assertEqual(cp.find_config_path(resmgr=Resources(app=base), cwd=os.path.join(base, 'win64')),
                         self.expected(base))

    def test_fallback_two_installations_with_packages_fail(self):
        first, second = self.game('one'), self.game('two')
        self.install(first)
        self.install(second)
        self.failed(cp.find_config_path(resmgr=Resources(app=first), cwd=second), 'fallback_ambiguous')

    def test_no_game_and_relative_resolver_path_do_not_guess(self):
        self.failed(cp.find_config_path(resmgr=Resources('paths.xml'), cwd=self.root),
                    'config_location_unavailable')

    def test_unicode_paths_xml_bom_and_escaped_ampersand(self):
        base = self.game('Żółć', entries=[('./mods/Ścieżka & gracz', 'recursive')])
        package = self.install(base, 'mods/Ścieżka & gracz/czołgi')
        xml = os.path.join(base, 'paths.xml')
        with io.open(xml, 'rb') as handle:
            content = handle.read()
        self.write(xml, b'\xef\xbb\xbf' + content)
        self.assertEqual(self.locate(base), self.expected(base))

    def test_windows_filesystem_bytes_and_native_utf8_bytes(self):
        base = self.game('Żółć')
        package = self.install(base)
        xml = os.path.join(base, 'paths.xml')
        with changed(sys, 'getfilesystemencoding', lambda: 'cp1250'):
            for encoding in ('utf-8', 'cp1250'):
                self.assertEqual(self.locate(base, resmgr=Resources(xml.encode(encoding))), self.expected(base))
                self.assertEqual(cp.find_config_path(resmgr=Resources(), cwd=base.encode(encoding)), self.expected(base))
        self.assertEqual(self.capture.records, [])

    def test_dtd_and_entities_rejected_before_xml_parser(self):
        base = self.game()
        self.install(base)
        self.write(os.path.join(base, 'paths.xml'),
                   b'<!DOCTYPE root [<!ENTITY secret "private-value">]><root><Paths>&secret;</Paths></root>')
        self.failed(self.locate(base), 'xml_forbidden_declaration')
        self.assertNotIn('private-value', self.capture.records[0].getMessage())

    def test_xml_size_limit(self):
        base = self.game()
        self.write(os.path.join(base, 'paths.xml'), b' ' * (cp.MAX_XML_BYTES + 1))
        self.failed(self.locate(base), 'xml_size_limit')

    def test_xml_node_limit(self):
        base = self.game()
        self.install(base)
        with changed(cp, 'MAX_XML_NODES', 2):
            self.failed(self.locate(base), 'xml_node_limit')

    def test_scan_limit_does_not_accept_an_incompletely_checked_tree(self):
        base = self.game()
        self.install(base)
        for number in range(4):
            self.install(base, name='other%d.wotmod' % number)
        with changed(cp, 'MAX_SCAN_ENTRIES', 3):
            self.failed(self.locate(base), 'package_scan_limit')

    def test_depth_limit_does_not_accept_an_incompletely_checked_tree(self):
        base = self.game()
        self.install(base)
        self.install(base, 'mods/2.4.1.0/one/two')
        with changed(cp, 'MAX_SCAN_DEPTH', 1):
            self.failed(self.locate(base), 'package_depth_limit')

    def test_root_limit(self):
        base = self.game(entries=[('./mods/one', ''), ('./mods/two', '')])
        self.install(base, 'mods/one')
        with changed(cp, 'MAX_PACKAGE_ROOTS', 1):
            self.failed(self.locate(base), 'package_root_limit')

    @unittest.skipUnless(hasattr(os, 'symlink'), 'No symlink support')
    def test_linked_xml_in_two_locations_keeps_distinct_relative_roots(self):
        first, second = self.game('one'), self.game('two')
        self.install(first)
        self.install(second)
        second_xml = os.path.join(second, 'paths.xml')
        os.remove(second_xml)
        try:
            os.symlink(os.path.join(first, 'paths.xml'), second_xml)
        except (OSError, NotImplementedError):
            self.skipTest('Creating symlinks is unavailable')
        self.failed(cp.find_config_path(resmgr=Resources(app=first), cwd=second), 'fallback_ambiguous')

    @unittest.skipUnless(hasattr(os, 'symlink'), 'No symlink support')
    def test_symlink_directories_are_not_followed(self):
        base = self.game()
        package = self.install(base)
        external = os.path.join(self.root, 'external')
        self.write(os.path.join(external, self.package), b'other package')
        try:
            os.symlink(external, os.path.join(os.path.dirname(package), 'linked'))
        except (OSError, NotImplementedError):
            self.skipTest('Creating symlinks is unavailable')
        self.assertEqual(self.locate(base), self.expected(base))

    def test_missing_optional_parser_uses_defaults_and_one_warning(self):
        base = self.game()
        self.install(base)
        original = builtins.__import__

        def unavailable(name, *args, **kwargs):
            if name == 'xml.etree.ElementTree':
                raise ImportError('private parser detail')
            return original(name, *args, **kwargs)

        with changed(builtins, '__import__', unavailable):
            self.failed(self.locate(base), 'xml_parser_unavailable')

    def test_unreadable_active_directory_is_not_silently_skipped(self):
        base = self.game()
        self.install(base)
        original = os.listdir

        def denied(path):
            if path == os.path.join(base, 'mods/2.4.1.0'):
                raise OSError('private directory detail')
            return original(path)

        with changed(os, 'listdir', denied):
            self.failed(self.locate(base), 'package_directory_unreadable')

    def test_changed_xml_structure_and_mode_are_not_guessed(self):
        base = self.game(entries=[('./mods/2.4.1.0', 'unknown')])
        self.install(base)
        self.failed(self.locate(base), 'unsupported_scan_mode')
        self.capture.records[:] = []
        self.write(os.path.join(base, 'paths.xml'), b'<root><Unknown/></root>')
        self.failed(self.locate(base), 'xml_paths_structure')

    def test_package_name_cannot_escape_the_active_directory(self):
        for value in ('../grz.wotmod', 'sub/grz.wotmod', 'sub\\grz.wotmod', '', 12):
            self.capture.records[:] = []
            self.failed(cp.find_config_path(package_name=value, resmgr=Resources(), cwd=self.root),
                        'invalid_package_name')


if __name__ == '__main__':
    unittest.main()
