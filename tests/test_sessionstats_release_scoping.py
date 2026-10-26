"""Session Stats publication shares the accepted lock, with independent builds."""
from pathlib import Path
import unittest
ROOT = Path(__file__).resolve().parents[1]

class SessionStatsScopingTests(unittest.TestCase):
    def test_common_publish_lock_and_independent_builds(self):
        for name in ('release.yml', 'sessionstats-release.yml'):
            build, publish = (ROOT/'.github/workflows'/name).read_text().split('\n  publish:', 1)
            self.assertNotIn('concurrency:', build)
            for marker in ('group: wotmod-release-${{ github.repository }}', 'queue: max', 'cancel-in-progress: false'):
                self.assertIn(marker, publish)

    def test_snapshot_skip_and_integration_precede_tag_push(self):
        text = (ROOT/'.github/workflows/sessionstats-release.yml').read_text()
        for marker in ('scripts/release_snapshot.sh', '"$status" == 75', 'scripts/release_installers.py verify release'):
            self.assertLess(text.index(marker), text.index('git push origin'))
        for pattern in ('Session-Stats-v*.zip',):
            self.assertIn("'"+pattern+"'", text)

    def test_no_cross_mod_build_or_retired_import(self):
        for name in ('validate.sh', 'integration.py'):
            self.assertNotIn('build_wotmod.py', (ROOT/'scripts/sessionstats'/name).read_text())
        for p in (ROOT/'scripts/sessionstats').glob('*.py'):
            self.assertNotRegex(p.read_text(), r'(?:import|from) publish_release')
