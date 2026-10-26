# -*- coding: utf-8 -*-
"""WoT discovers compiled, lower-case mod_*.pyc files in gui/mods."""
from __future__ import absolute_import

import logging

LOG = logging.getLogger('grz.sessionstats')


def init():
    try:
        from gui.mods.grz_session_stats import runtime
        runtime.init()
    except Exception:
        # A future client import/API change must stay inside this mod's loader
        # entry point instead of interrupting initialization of other mods.
        LOG.exception('GRZ Session Stats loader unavailable; client initialization continues.')


def fini():
    try:
        from gui.mods.grz_session_stats import runtime
        runtime.fini()
    except Exception:
        LOG.exception('GRZ Session Stats loader teardown failed; client teardown continues.')
