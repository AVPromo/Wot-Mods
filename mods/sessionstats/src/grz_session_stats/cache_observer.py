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
        self._original = _function(self._cls.get)
        original = self._original

        @wraps(original)
        def observed_get(instance, arena_id, callback):
            if (not self._active or instance is not self.cache or
                    getattr(callback, OWN_CALLBACK, False)):
                return original(instance, arena_id, callback)
            try:
                context = self._capture()
            except Exception:
                context = None
                self._warn()
            if context is None:
                return original(instance, arena_id, callback)

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

            return original(instance, arena_id, received)

        self._wrapper = observed_get
        self._cls.get = observed_get

    def _warn(self):
        if not self._warned:
            self._warned = True
            LOG.warning('Optional result-cache observer failed; native consumer remains active.')

    def close(self):
        self._active = False
        if _function(self._cls.get) is self._wrapper:
            self._cls.get = self._original
        # A later mod may retain our inert wrapper in its chain. Do not retain
        # the runtime or overwrite that mod's method during cleanup.
        self.cache = self._capture = self._consume = None
