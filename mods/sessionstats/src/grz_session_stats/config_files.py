# -*- coding: utf-8 -*-
"""Create optional configuration without overwriting existing user files."""
from __future__ import absolute_import, unicode_literals

import errno
import io
import json
import logging
import os
import tempfile

from .appearance import MAX_CONFIG_BYTES, default_config

LOG = logging.getLogger('grz.sessionstats')


def _publish_new(path, raw):
    """Publish a complete file atomically, refusing a concurrent destination."""
    directory = os.path.dirname(path)
    try:
        os.makedirs(directory)
    except OSError as error:
        if error.errno != errno.EEXIST or not os.path.isdir(directory):
            raise
    descriptor, temporary = tempfile.mkstemp(prefix='.grz-sessionstats-', suffix='.tmp', dir=directory)
    try:
        with os.fdopen(descriptor, 'wb') as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            if os.name == 'nt':
                # Windows rename refuses to replace an existing destination.
                os.rename(temporary, path)
            else:
                # POSIX rename would overwrite; a hard link is create-only.
                os.link(temporary, path)
        except OSError:
            if os.path.lexists(path):
                return False
            raise
        return True
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _prepare_file(path, legacy, limit, defaults=None):
    if os.path.lexists(path):
        return
    try:
        with io.open(legacy, 'rb') as handle:
            raw = handle.read(limit + 1)
    except (IOError, OSError) as error:
        if error.errno != errno.ENOENT:
            raise
        if defaults is None:
            return
        raw = (json.dumps(defaults(), ensure_ascii=True, indent=2, sort_keys=True) + '\n').encode('utf-8')
        action = 'created_defaults'
    else:
        if len(raw) > limit:
            raise ValueError('legacy_size_limit')
        # Preserve even a malformed user's file verbatim. The ordinary bounded
        # loader validates it and reports errors without rewriting its contents.
        action = 'copied_legacy'
    if _publish_new(path, raw):
        LOG.info('CONFIG_SETUP file=%s action=%s.', os.path.basename(path), action)


def prepare_config(path, legacy):
    """Best-effort migration/defaults; old files and existing targets stay intact."""
    try:
        _prepare_file(path, legacy, MAX_CONFIG_BYTES, default_config)
    except Exception as error:
        LOG.warning('CONFIG_SETUP file=%s failed (%s); existing files are unchanged.',
                    os.path.basename(path), type(error).__name__)


def _replace_file(source, destination):
    if os.name != 'nt':
        os.rename(source, destination)
        return
    # CPython 2.7 has no os.replace; Windows rename cannot replace a file.
    import ctypes
    import sys
    from ctypes import wintypes
    from .localization import text_type
    def wide(value):
        return value if isinstance(value, text_type) else value.decode(sys.getfilesystemencoding() or 'utf-8')
    move = ctypes.WinDLL('kernel32', use_last_error=True).MoveFileExW
    move.argtypes = (wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD)
    move.restype = wintypes.BOOL
    if not move(wide(source), wide(destination), 0x1 | 0x8):
        raise ctypes.WinError(ctypes.get_last_error())


def save_language(path, language):
    """Change only language, atomically; reject invalid or concurrently edited JSON."""
    from .localization import SUPPORTED, text_type
    from .appearance import _object_pairs, _reject_constant, SCHEMA_VERSION, integer_types
    from .storage import check_json_depth
    if not isinstance(language, text_type) or language not in ('auto',) + SUPPORTED or not path:
        return False
    temporary = None
    try:
        def current():
            try:
                with io.open(path, 'rb') as handle:
                    return handle.read(MAX_CONFIG_BYTES + 1)
            except (IOError, OSError) as error:
                if error.errno == errno.ENOENT:
                    return None
                raise
        original = current()
        if original is None:
            return _publish_new(path, (json.dumps({'language': language}) + '\n').encode('utf-8'))
        if len(original) > MAX_CONFIG_BYTES:
            raise ValueError('config_size_limit')
        document = json.loads(original.decode('utf-8-sig'), object_pairs_hook=_object_pairs,
                              parse_constant=_reject_constant)
        if not isinstance(document, dict):
            raise ValueError('config_object_required')
        version = document.get('schema_version', SCHEMA_VERSION)
        if isinstance(version, bool) or not isinstance(version, integer_types) or version != SCHEMA_VERSION:
            raise ValueError('unsupported_schema')
        check_json_depth(document)
        document['language'] = language
        raw = (json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False) + '\n').encode('utf-8')
        if len(raw) > MAX_CONFIG_BYTES:
            raise ValueError('config_size_limit')
        descriptor, temporary = tempfile.mkstemp(prefix='.grz-language-', suffix='.tmp', dir=os.path.dirname(path))
        with os.fdopen(descriptor, 'wb') as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        if current() != original:
            raise ValueError('config_changed')
        _replace_file(temporary, path)
        return True
    except Exception as error:
        LOG.warning('CONFIG language save failed (%s); previous configuration preserved.', type(error).__name__)
        return False
    finally:
        if temporary is not None and os.path.exists(temporary):
            try:
                os.unlink(temporary)
            except OSError:
                LOG.warning('CONFIG language temporary-file cleanup failed.')
