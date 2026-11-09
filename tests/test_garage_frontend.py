"""Run the dependency-free DOM contracts with the CI runner's Node runtime."""
import os
from pathlib import Path
import shutil
import subprocess
import unittest


class GarageFrontendTests(unittest.TestCase):
    def test_footer_and_native_settings_dom_contracts(self):
        node = shutil.which('node')
        if node is None:
            self.skipTest('Node is unavailable; run ui-medkit-footer.cjs separately')
        root = Path(__file__).resolve().parents[1]
        environment = dict(os.environ, GRZ_MEDKIT_BROWSER_TEST='0')
        result = subprocess.run([node, str(root / 'tests/ui-medkit-footer.cjs')],
                                cwd=root, env=environment, capture_output=True,
                                text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
