# -*- coding: utf-8 -*-
"""Find configuration in mods/configs of the active physical installation.

The virtual module filename cannot identify its .wotmod. The verified client
paths.xml declares package roots; only those roots are searched. No version
directory guessing or XML parser import at module load. Discovery is read-only;
preparation separately creates missing configuration without replacing files.
"""
from __future__ import absolute_import, unicode_literals

import io
import logging
import os
import re
import sys

from . import VERSION

LOG = logging.getLogger('grz.sessionstats')
CONFIG_FILENAME = 'grz.sessionstats.json'
PACKAGE_FILENAME = 'grz_sessions_stats.wotmod'
PREVIOUS_PACKAGE_FILENAME = 'GRZ_Session_Stats.wotmod'
MAX_XML_BYTES = 256 * 1024
MAX_XML_NODES = 4096
MAX_PACKAGE_ROOTS = 32
MAX_SCAN_ENTRIES = 8192
MAX_SCAN_DEPTH = 8
MAX_PATH_CHARS = 4096

try:
    text_type = unicode
except NameError:
    text_type = str


class _LocationError(Exception):
    pass


def _path_variants(value):
    """Native APIs and Python 2 Windows can use UTF-8 or filesystem bytes."""
    if isinstance(value, text_type):
        values = [value]
    elif isinstance(value, bytes):
        values = []
        for encoding in ('utf-8', sys.getfilesystemencoding() or 'utf-8'):
            try:
                decoded = value.decode(encoding)
                if decoded not in values:
                    values.append(decoded)
            except (UnicodeError, LookupError):
                pass
    else:
        return []
    return [value for value in values if value and len(value) <= MAX_PATH_CHARS
            and '\x00' not in value]


def _physical_xml(value):
    found = {}
    for path in _path_variants(value):
        if (os.path.isabs(path) and os.path.basename(path).lower() == 'paths.xml'
                and os.path.isfile(path)):
            path = os.path.abspath(path)
            # Distinct XML locations can resolve the same relative root
            # differently, even when the XML files themselves are links.
            found[os.path.normcase(path)] = path
    if len(found) > 1:
        raise _LocationError('ambiguous_path_encoding')
    return next(iter(found.values())) if found else None


def _package_roots(xml_path):
    try:
        with io.open(xml_path, 'rb') as handle:
            raw = handle.read(MAX_XML_BYTES + 1)
    except (IOError, OSError):
        raise _LocationError('xml_read_failed')
    if len(raw) > MAX_XML_BYTES:
        raise _LocationError('xml_size_limit')
    try:
        text = raw.decode('utf-8-sig')
    except UnicodeError:
        raise _LocationError('xml_encoding')
    if re.search(r'<!\s*(?:DOCTYPE|ENTITY)\b', text, re.I):
        raise _LocationError('xml_forbidden_declaration')
    encoding = re.search(r'<\?xml[^?]*\bencoding\s*=\s*[\'"]([^\'"]+)', text, re.I)
    if encoding and encoding.group(1).lower() not in ('utf-8', 'utf8', 'ascii', 'us-ascii'):
        raise _LocationError('xml_encoding')
    try:
        # Some embedded clients may lack this optional stdlib component.
        import xml.etree.ElementTree as ET
    except Exception:
        raise _LocationError('xml_parser_unavailable')
    try:
        root = ET.fromstring(text.encode('utf-8'))
    except Exception:
        raise _LocationError('xml_parse_failed')
    for index, unused_node in enumerate(root.iter()):
        if index >= MAX_XML_NODES:
            raise _LocationError('xml_node_limit')
    sections = root.findall('Paths')
    if root.tag != 'root' or len(sections) != 1:
        raise _LocationError('xml_paths_structure')
    roots = {}
    declared = 0
    base = os.path.dirname(xml_path)
    for section in sections[0]:
        if section.tag != 'Path' or section.get('mask', '').strip().lower() != '*.wotmod':
            continue
        declared += 1
        if declared > MAX_PACKAGE_ROOTS:
            raise _LocationError('package_root_limit')
        mode = section.get('mode', '').strip().lower()
        if mode not in ('', 'recursive'):
            raise _LocationError('unsupported_scan_mode')
        value = (section.text or '').strip()
        if len(section) or not value or len(value) > MAX_PATH_CHARS or '\x00' in value:
            raise _LocationError('invalid_package_root')
        # XML paths are relative to the XML's directory, not Python's cwd.
        directory = os.path.abspath(os.path.join(base, value))
        key = os.path.normcase(directory)
        previous = roots.get(key)
        roots[key] = (directory, mode == 'recursive' or bool(previous and previous[1]))
    if not roots:
        raise _LocationError('package_roots_missing')
    return list(roots.values())


def _find_package(xml_path, package_names, budget):
    packages = {}
    wanted = set(os.path.normcase(name) for name in package_names)
    for root, recursive in _package_roots(xml_path):
        if os.path.islink(root):
            continue
        if not os.path.isdir(root):
            continue
        stack = [(root, 0)]
        while stack:
            directory, depth = stack.pop()
            try:
                names = os.listdir(directory)
            except (IOError, OSError):
                raise _LocationError('package_directory_unreadable')
            budget[0] += len(names)
            if budget[0] > MAX_SCAN_ENTRIES:
                raise _LocationError('package_scan_limit')
            for name in names:
                path = os.path.join(directory, name)
                # Neither a directory link nor a package link establishes a
                # unique neighbouring config, so do not follow either one.
                if os.path.islink(path):
                    continue
                if os.path.normcase(name) in wanted and os.path.isfile(path):
                    packages[os.path.normcase(os.path.abspath(path))] = path
                    if len(packages) > 1:
                        raise _LocationError('multiple_active_packages')
                if recursive and os.path.isdir(path):
                    if depth >= MAX_SCAN_DEPTH:
                        raise _LocationError('package_depth_limit')
                    stack.append((path, depth + 1))
    if packages:
        package = next(iter(packages.values()))
        return os.path.join(os.path.dirname(package), CONFIG_FILENAME)
    return None


def _fallback_files(resmgr, cwd):
    directories = []
    if resmgr is not None:
        try:
            getter = getattr(resmgr, 'appDirectory', None)
            if callable(getter):
                directories.extend(_path_variants(getter()))
        except Exception:
            pass
    if cwd is None:
        getter = getattr(os, 'getcwdu', os.getcwd)
        cwd = getter()
    directories.extend(_path_variants(cwd))
    files = {}
    for directory in directories:
        directory = os.path.abspath(directory)
        for base in (directory, os.path.dirname(directory)):
            candidate = _physical_xml(os.path.join(base, 'paths.xml'))
            if candidate:
                files[os.path.normcase(candidate)] = candidate
    return list(files.values())


def _config_location(xml_path, legacy_path):
    return (os.path.join(os.path.dirname(xml_path), 'mods', 'configs', CONFIG_FILENAME), legacy_path)


def _find_config_location(package_name=None, resmgr=None, cwd=None):
    """Return central/legacy JSON paths or None; never write installation.

    A physically confirmed resolver result is authoritative, even if malformed
    or ambiguous. Only when it cannot identify a physical paths.xml may the
    bounded app-directory/cwd fallback be used. The JSON itself may be absent.
    """
    try:
        legacy_name = 'grz.sessionstats_' + VERSION + '.wotmod'
        default_name = package_name is None
        variants = _path_variants(PACKAGE_FILENAME if default_name else package_name)
        if (len(variants) != 1 or len(variants[0]) > 255 or
                (variants[0] != PACKAGE_FILENAME and
                 not re.match(r'\A[A-Za-z0-9_.-]+\.wotmod\Z', variants[0]))):
            raise _LocationError('invalid_package_name')
        # The installed name is stable across releases. The exact current
        # versioned developer artifact remains supported for older callers.
        package_names = (variants[0], PREVIOUS_PACKAGE_FILENAME, legacy_name) if default_name else (variants[0],)
        if resmgr is None:
            try:
                import ResMgr as resmgr
            except Exception:
                resmgr = None
        xml_path = None
        if resmgr is not None:
            try:
                resolver = getattr(resmgr, 'resolveToAbsolutePath', None)
                resolved = resolver('../paths.xml') if callable(resolver) else None
            except Exception:
                resolved = None
            xml_path = _physical_xml(resolved)
        budget = [0]
        if xml_path is not None:
            result = _find_package(xml_path, package_names, budget)
            if result is None:
                raise _LocationError('active_package_missing')
            return _config_location(xml_path, result)
        candidates = _fallback_files(resmgr, cwd)
        results = {}
        for candidate in candidates:
            result = _find_package(candidate, package_names, budget)
            if result is not None:
                location = _config_location(candidate, result)
                # A shared/linked configs directory does not make two physical
                # XML locations the same installation or legacy source.
                results[os.path.normcase(candidate)] = location
        if len(results) != 1:
            raise _LocationError('fallback_ambiguous' if results else 'config_location_unavailable')
        return next(iter(results.values()))
    except _LocationError as error:
        code = error.args[0]
    except Exception:
        code = 'unexpected_location_error'
    try:
        LOG.warning('CONFIG_PATH code=%s; mods/configs for the active installation was not resolved; using defaults.', code)
    except Exception:
        pass
    return None


def find_config_path(package_name=None, resmgr=None, cwd=None):
    """Locate mods/configs/grz.sessionstats.json without creating any files."""
    location = _find_config_location(package_name, resmgr, cwd)
    return location[0] if location is not None else None


def prepare_config_path(package_name=None, resmgr=None, cwd=None):
    """Locate configuration and create/migrate only missing optional files."""
    location = _find_config_location(package_name, resmgr, cwd)
    if location is None:
        return None
    from .config_files import prepare_config
    prepare_config(*location)
    return location[0]


def find_installation_root(resmgr=None, cwd=None):
    """Identify the physical game root, independently of mod/client versions."""
    try:
        if resmgr is None:
            try:
                import ResMgr as resmgr
            except Exception:
                resmgr = None
        if resmgr is not None:
            try:
                resolver = getattr(resmgr, 'resolveToAbsolutePath', None)
                resolved = resolver('../paths.xml') if callable(resolver) else None
            except Exception:
                resolved = None
            # An ambiguous authoritative path must not select another game via
            # appDirectory/CWD fallback. Only resolver absence permits fallback.
            path = _physical_xml(resolved)
            if path is not None:
                _package_roots(path)
                return os.path.realpath(os.path.dirname(path))
        candidates = _fallback_files(resmgr, cwd)
        if len(candidates) == 1:
            _package_roots(candidates[0])
            return os.path.realpath(os.path.dirname(candidates[0]))
    except Exception:
        pass
    # Never use one global fallback that could merge distinct installations.
    return None
