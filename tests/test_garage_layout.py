"""Exercise delayed native texture creation independently of DOM-only sizing."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import unittest


class GarageLayoutTests(unittest.TestCase):
    def test_delayed_native_texture_resize_and_cleanup(self):
        node = shutil.which('node')
        if node is None:
            self.skipTest('Node is unavailable')
        root = Path(__file__).resolve().parents[1]
        spec = importlib.util.spec_from_file_location('medkit_layout_contract', root / 'source/staysharp_medkit/views.py')
        views = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(views)
        cases = []
        for width, height in ((1, 1), (2, 100), (320, 200), (435, 337), (640, 360),
                              (800, 600), (1280, 720), (1920, 1080), (1920, 1200),
                              (2560, 1080), (3440, 1440), (600, 900), (3840, 2160)):
            for scale in (0.1, 0.5, 1, 1.025, 1.1, 1.25, 1.5, 2, 3, 4, 8, 16):
                viewport = dict(width=width, height=height, scale=scale)
                size, unused_gutter, unused_available = views._fit_geometry(viewport)
                cases.append(dict(viewport=viewport, size=size))
        environment = dict(os.environ, MEDKIT_LAYOUT_CASES=json.dumps(cases))
        result = subprocess.run([node, str(root / 'tests/ui-medkit-settings-resize.cjs')],
                                cwd=root, env=environment, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
