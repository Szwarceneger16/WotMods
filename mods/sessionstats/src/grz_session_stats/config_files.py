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
from .localization import FILENAME as LANGUAGES_FILENAME, MAX_BYTES as MAX_LANGUAGE_BYTES

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
    pairs = ((path, legacy, MAX_CONFIG_BYTES, default_config),
             (os.path.join(os.path.dirname(path), LANGUAGES_FILENAME),
              os.path.join(os.path.dirname(legacy), LANGUAGES_FILENAME), MAX_LANGUAGE_BYTES, None))
    for target, source, limit, defaults in pairs:
        try:
            _prepare_file(target, source, limit, defaults)
        except Exception as error:
            # No raw paths, configuration contents or exception text in logs.
            LOG.warning('CONFIG_SETUP file=%s failed (%s); existing files are unchanged.',
                        os.path.basename(target), type(error).__name__)
