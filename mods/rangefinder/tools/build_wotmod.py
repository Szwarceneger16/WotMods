#!/usr/bin/env python2
"""Build the GRZ Rangefinder WoT package."""
from __future__ import absolute_import

import os
import runpy
import sys

repo = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
if __name__ == '__main__':
    sys.argv.insert(1, 'rangefinder')
    runpy.run_path(os.path.join(repo, 'scripts', 'reticles', 'build_wotmod.py'), run_name='__main__')
