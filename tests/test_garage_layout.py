"""Exercise delayed native texture creation independently of DOM-only sizing."""
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
        result = subprocess.run([node, str(root / 'tests/ui-medkit-settings-resize.cjs')],
                                cwd=root, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
