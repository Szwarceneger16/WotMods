# -*- coding: utf-8 -*-
"""Observe the client's own result reads without replacing their consumers."""
from __future__ import unicode_literals

import logging
from functools import wraps

LOG = logging.getLogger('grz.sessionstats')
OWN_CALLBACK = '_grz_session_stats_result_request'


def _function(method):
    return getattr(method, 'im_func', method)


class CacheObserver(object):
    def __init__(self, cache, capture, consume):
        self.cache = cache
        self._capture = capture
        self._consume = consume
        self._active = True
        self._warned = False
        self._cls = type(cache)
        self._defined_here = 'get' in self._cls.__dict__
        self._original = _function(self._cls.get)
        original = self._original

        @wraps(original)
        def observed_get(instance, *args, **kwargs):
            # This is a shared method, including for other cache instances.
            # Keep native keyword names and any earlier mod's extensions.
            # Unknown/ambiguous call shapes bypass optional observation and
            # retain the original method's validation and exception behavior.
            if not self._active or instance is not self.cache:
                return original(instance, *args, **kwargs)
            arena_id = args[0] if args else kwargs.get('arenaUniqueID', kwargs.get('arena_id'))
            positional_callback = len(args) >= 2
            if arena_id is None or (not positional_callback and 'callback' not in kwargs):
                return original(instance, *args, **kwargs)
            if positional_callback and 'callback' in kwargs:
                return original(instance, *args, **kwargs)
            callback = args[1] if positional_callback else kwargs['callback']
            try:
                context = None if getattr(callback, OWN_CALLBACK, False) else self._capture()
            except Exception:
                context = None
                self._warn()
            if context is None:
                return original(instance, *args, **kwargs)

            def received(*args, **kwargs):
                if self._active:
                    try:
                        # Run before the original consumer and the client's
                        # post-callback acknowledgement of the server stream.
                        self._consume(context, arena_id, args)
                    except Exception:
                        self._warn()
                if callback is not None:
                    return callback(*args, **kwargs)

            if positional_callback:
                args = args[:1] + (received,) + args[2:]
            else:
                kwargs = dict(kwargs, callback=received)
            return original(instance, *args, **kwargs)

        self._wrapper = observed_get
        self._cls.get = observed_get

    def _warn(self):
        if not self._warned:
            self._warned = True
            LOG.warning('Optional result-cache observer failed; native consumer remains active.')

    def close(self):
        self._active = False
        if _function(self._cls.get) is self._wrapper:
            if self._defined_here:
                self._cls.get = self._original
            else:
                del self._cls.get
        # A later mod may retain our inert wrapper in its chain. Do not retain
        # the runtime or overwrite that mod's method during cleanup.
        self.cache = self._capture = self._consume = None
