#!/usr/bin/env python
"""Inspect or smoke-test packaged Hangar bootstraps with CPython 2.7 only."""
from __future__ import print_function

import argparse
import json
import marshal
import re
import sys
import types
import zipfile

MAGIC = b'\x03\xf3\r\n'
PREFIX = 'res/scripts/client/gui/mods/'
MODULES = ('grz_hangar_battle_pass', 'grz_hangar_crew', 'grz_hangar_stats',
           'grz_hangar_mission_metadata', 'mod_grz_hangar_sync')
BOOTSTRAP_CODE = b'd\x00\x00d\x01\x00d\x01\x00Ud\x01\x00S'


def require_python27():
    if sys.version_info[:2] != (2, 7):
        raise ValueError('CPython 2.7 is required')


def decode(data):
    require_python27()
    if data[:4] != MAGIC or len(data) < 9:
        raise ValueError('Invalid Python 2.7 bytecode header')
    code = marshal.loads(data[8:])
    if not isinstance(code, types.CodeType):
        raise ValueError('A packaged module must contain a code object')
    return code


def audit_pyc(data, patterns):
    """Read constants and compile embedded source without executing candidate code."""
    code = decode(data)
    expressions = [(name, re.compile(pattern, re.I)) for name, pattern in patterns]
    found = set()

    def walk(value):
        if isinstance(value, types.CodeType):
            filename = value.co_filename.replace('\\', '/')
            if (filename != 'mod_grz_hangar_sync.py' and
                    not re.match(r'\Ares/scripts/client/gui/mods/[A-Za-z0-9_]+\.py\Z', filename)):
                found.add('non_virtual_code_filename')
            walk(value.co_filename)
            for item in value.co_consts:
                walk(item)
        elif isinstance(value, (list, tuple)):
            for item in value:
                walk(item)
        elif isinstance(value, basestring):
            text = value if isinstance(value, unicode) else value.decode('utf-8', 'replace')
            for name, pattern in expressions:
                if pattern.search(text):
                    found.add(name)

    walk(code)
    # The published builder uses a small EXEC_STMT wrapper containing ASCII source.
    if code.co_code == BOOTSTRAP_CODE:
        if len(code.co_consts) != 2 or not isinstance(code.co_consts[0], str):
            raise ValueError('Unexpected embedded-source bootstrap')
        embedded = compile(code.co_consts[0], PREFIX + 'embedded.py', 'exec')
        walk(embedded)
    return sorted(found)


def smoke(package_path):
    require_python27()
    with zipfile.ZipFile(package_path) as archive:
        expected = set(['meta.xml'] + [PREFIX + name + '.pyc' for name in MODULES])
        if set(archive.namelist()) != expected or len(archive.namelist()) != len(expected):
            raise ValueError('Unexpected Hangar package members')
        modules = dict((name, decode(archive.read(PREFIX + name + '.pyc'))) for name in MODULES)

    # Preload standard libraries before denying external effects and file access.
    import __builtin__
    import datetime
    import hashlib
    import HTMLParser
    import httplib
    import logging
    import logging.handlers
    import os
    import socket
    import ssl
    import subprocess
    import thread
    import threading
    import urllib2

    effects = []
    patches = []

    def patch(owner, name, value):
        patches.append((owner, name, getattr(owner, name)))
        setattr(owner, name, value)

    def forbidden(label):
        def blocked(*args, **kwargs):
            effects.append(label)
            raise RuntimeError('External effect blocked by Hangar CI')
        return blocked

    for owner, names in ((socket, ('socket', 'create_connection', 'getaddrinfo')),
                         (urllib2, ('urlopen', 'build_opener')),
                         (subprocess, ('Popen',)),
                         (threading.Thread, ('start',)),
                         (thread, ('start_new_thread',)),
                         (__builtin__, ('open', 'file')),
                         (os, ('open', 'mkdir', 'makedirs', 'system'))):
        for name in names:
            patch(owner, name, forbidden(name))

    original_import = __builtin__.__import__

    def guarded_import(name, *args, **kwargs):
        if name.split('.')[0] in ('BigWorld', 'ResMgr', 'PlayerEvents', 'Account', 'Avatar', 'helpers', 'items'):
            raise ImportError('Game APIs are unavailable in CI')
        return original_import(name, *args, **kwargs)

    patch(__builtin__, '__import__', guarded_import)
    namespace = {}
    installed = []
    threads_before = threading.active_count()
    try:
        for package in ('gui', 'gui.mods'):
            module = types.ModuleType(str(package))
            module.__path__ = []
            sys.modules[package] = module
            installed.append(package)
        for name in MODULES:
            qualified = 'gui.mods.' + name
            module = types.ModuleType(str(qualified))
            module.__file__ = PREFIX + name + '.pyc'
            sys.modules[qualified] = module
            installed.append(qualified)
            # eval accepts an exec-mode code object on Python 2.7. This executes
            # the exact archive wrapper, not recompiled or substituted sources.
            eval(modules[name], module.__dict__)
            namespace[name] = module

        main = namespace['mod_grz_hangar_sync']
        if main._state is not None or main._mission_probe is not None:
            raise AssertionError('Module import started a game runtime')
        expected_config = {
            'enabled': False, 'endpoint_url': '', 'device_token': '', 'sites_access_token': '',
            'region': 'EU', 'display_name': '', 'allowed_players': [], 'include_crew': False,
            'interval_seconds': 120, 'include_missions': False, 'mission_diagnostics': True,
        }
        disabled = main.parse_config(json.dumps(expected_config))
        # init's file/log adapters are replaced with controlled public inputs;
        # privacy/disabled-state behavior still executes the packaged function.
        disabled['mission_diagnostics'] = False
        main.start_diagnostics = lambda *args, **kwargs: True
        main.config_path = lambda: 'synthetic-disabled-config'
        main.load_config = lambda path: disabled
        main.LOG.addHandler(logging.NullHandler())
        main.MISSION_LOG.addHandler(logging.NullHandler())
        main.init()
        if main._state is not None or main._mission_probe is not None:
            raise AssertionError('Disabled configuration started a runtime')

        stats = namespace['grz_hangar_stats'].collect_session_stats([1])
        if stats['status'] != 'not_loaded' or stats['vehicles']:
            raise AssertionError('The optional statistics provider was initialized')
        rich = namespace['grz_hangar_crew'].rich_text('{greenBright_Start}+6.35%{greenBright_End}')
        if rich != [{'spans': [{'text': '+6.35%', 'tone': 'positive'}]}]:
            raise AssertionError('The packaged crew helper returned unexpected text')
        snapshot = {'capturedAt': 'synthetic', 'vehicles': [], 'crewSkillCatalog': []}
        payload, digest = main.encode_snapshot(snapshot)
        if json.loads(payload) != snapshot or not re.match(r'\A[0-9a-f]{64}\Z', digest):
            raise AssertionError('Packaged encoder/helper integration failed')
        main.fini()
        if effects or threading.active_count() != threads_before:
            raise AssertionError('An external effect or thread was started')
    finally:
        for owner, name, previous in reversed(patches):
            setattr(owner, name, previous)
        for name in reversed(installed):
            sys.modules.pop(name, None)
    print('Bootstrap smoke OK: five packaged Python 2.7 modules, disabled init and helper integration; no external effects')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('package', nargs='?')
    parser.add_argument('--audit-pyc')
    parser.add_argument('--patterns')
    args = parser.parse_args()
    if args.audit_pyc:
        if args.package or not args.patterns:
            parser.error('--audit-pyc requires --patterns and no package')
        with open(args.audit_pyc, 'rb') as stream:
            data = stream.read()
        with open(args.patterns) as stream:
            patterns = json.load(stream)
        print(json.dumps(audit_pyc(data, patterns)))
    else:
        if not args.package or args.patterns:
            parser.error('Supply one packaged wotmod')
        smoke(args.package)


if __name__ == '__main__':
    try:
        main()
    except Exception:
        # Paths, source values and exception messages can contain private data.
        print('Hangar bootstrap check failed', file=sys.stderr)
        raise SystemExit(1)
