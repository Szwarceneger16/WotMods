"""Keep the runner mirror workaround narrow and preserve signed validation."""
import importlib.util
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / '.github/scripts/prepare_ubuntu_mirrors.py'
spec = importlib.util.spec_from_file_location('sessionstats_apt_mirrors', HELPER)
mirrors = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mirrors)

AZURE = b'http://azure.archive.ubuntu.com/ubuntu/\tpriority:1\n'
ARCHIVE = b'https://archive.ubuntu.com/ubuntu/\tpriority:2\n'
SECURITY = b'https://security.ubuntu.com/ubuntu/\tpriority:3\n'


class UbuntuMirrorPreparationTests(unittest.TestCase):
    def test_removes_only_the_exact_azure_entry_and_keeps_both_official_fallbacks(self):
        original = AZURE + ARCHIVE + SECURITY
        self.assertEqual(mirrors.transform_mirrors(original), ARCHIVE + SECURITY)
        self.assertEqual(mirrors.DEFAULT_MIRROR_PATH, Path('/etc/apt/apt-mirrors.txt'))

    def test_preserves_unrelated_urls_comments_order_whitespace_and_line_endings(self):
        retained = (b'# http://azure.archive.ubuntu.com/ubuntu/ priority:1\r\n'
                    b'  # an ordinary comment\n'
                    b'https://azure.archive.ubuntu.com/ubuntu/ priority:1\n'
                    b'http://azure.archive.ubuntu.com/ubuntu/extra/ priority:1\r\n'
                    b'http://azure.archive.ubuntu.com/ubuntu.evil/ priority:1\n'
                    b'http://azure.archive.ubuntu.com.evil/ubuntu/ priority:1\n'
                    b'https://example.invalid/ubuntu/ arbitrary:unchanged\n'
                    b'\r\n')
        fallbacks = (b'  https://security.ubuntu.com/ubuntu/ priority:3 # security\r\n'
                     b'https://archive.ubuntu.com/ubuntu/ priority:2')
        original = retained + b'  ' + AZURE.replace(b'\n', b'\r\n') + fallbacks
        self.assertEqual(mirrors.transform_mirrors(original), retained + fallbacks)

    def test_without_azure_does_not_validate_or_rewrite_existing_configuration(self):
        for original in (b'', b'# only comments\n', b'unknown custom mirror data\r\n',
                         ARCHIVE, b'https://azure.archive.ubuntu.com/ubuntu/ priority:1\n'):
            with self.subTest(original=original):
                self.assertEqual(mirrors.transform_mirrors(original), original)

    def test_azure_requires_both_real_and_well_formed_https_fallback_entries(self):
        invalid = (
            b'', ARCHIVE, SECURITY,
            ARCHIVE + b'# ' + SECURITY,
            ARCHIVE + SECURITY.replace(b'https:', b'http:'),
            ARCHIVE + SECURITY.replace(b'security.ubuntu.com', b'security.ubuntu.com.evil'),
            ARCHIVE + SECURITY.replace(b'/ubuntu/', b'/ubuntu/extra/'),
            ARCHIVE + b'https://security.ubuntu.com/ubuntu/ priority:bad\n',
            ARCHIVE + b'https://security.ubuntu.com/ubuntu/ priority:-1\n',
            ARCHIVE + b'https://security.ubuntu.com/ubuntu/ unexpected:field\n',
        )
        for retained in invalid:
            with self.subTest(retained=retained):
                with self.assertRaises(ValueError):
                    mirrors.transform_mirrors(AZURE + retained)

    def test_file_preparation_validates_before_writing_and_is_idempotent(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'mirrors.txt'
            original = AZURE + ARCHIVE + SECURITY
            path.write_bytes(original)
            self.assertTrue(mirrors.prepare_mirrors(path))
            self.assertEqual(path.read_bytes(), ARCHIVE + SECURITY)
            stat = path.stat()
            self.assertFalse(mirrors.prepare_mirrors(path))
            self.assertEqual(path.stat().st_mtime_ns, stat.st_mtime_ns)
            invalid = AZURE + ARCHIVE
            path.write_bytes(invalid)
            stat = path.stat()
            with self.assertRaises(ValueError):
                mirrors.prepare_mirrors(path)
            self.assertEqual(path.read_bytes(), invalid)
            self.assertEqual(path.stat().st_mtime_ns, stat.st_mtime_ns)

    def test_missing_file_is_a_no_op_without_creating_it(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'missing.txt'
            self.assertFalse(mirrors.prepare_mirrors(path))
            self.assertFalse(path.exists())


class UbuntuMirrorWorkflowTests(unittest.TestCase):
    def test_preparation_is_source_gated_and_does_not_replace_any_validation(self):
        workflow = (ROOT / '.github/workflows/sessionstats-ci.yml').read_text()
        self.assertIn("      - '.github/scripts/prepare_ubuntu_mirrors.py'", workflow)
        self.assertIn('contents: read', workflow)
        self.assertNotIn('contents: write', workflow)
        command = 'sudo python3 .github/scripts/prepare_ubuntu_mirrors.py'
        self.assertIn(command, workflow)
        start = workflow.rfind('      - name:', 0, workflow.index(command))
        stop = workflow.find('\n      - ', workflow.index(command))
        step = workflow[start:stop]
        self.assertIn("if: steps.source.outputs.enabled == 'true'", step)
        self.assertLess(workflow.index('id: source'), start)
        self.assertLess(start, workflow.index('run: bash scripts/sessionstats/validate.sh'))
        self.assertRegex(step, r'Acquire::Retries\s+"[1-3]";')
        for transport in ('http', 'https'):
            self.assertRegex(step, r'Acquire::' + transport + r'::Timeout\s+"(?:[1-9]|[1-5][0-9]|60)";')
        self.assertIn('APT::Update::Error-Mode "any";', step)
        self.assertIn('sudo apt-get update', step)
        self.assertNotIn('APT::Acquire::Retries', step)
        self.assertNotRegex(step, r'\|\|\s*(?:true|:)')
        self.assertNotRegex(step.lower(), r'allowinsecure|allow-unauthenticated|verify-peer|trusted=yes')
        for marker in ('run: bash scripts/sessionstats/python27.sh',
                       'run: bash scripts/sessionstats/validate.sh',
                       'scripts/release_installers.py package pr-artifact-sessionstats',
                       'uses: actions/upload-artifact@', 'archive: false',
                       'if-no-files-found: error'):
            self.assertIn(marker, workflow)
        validate = (ROOT / 'scripts/sessionstats/validate.sh').read_text()
        self.assertIn('install --with-deps chromium', validate)
        self.assertIn('ui_contract ui-wheel ui-footer ui-footer-activity ui-footer-compat ui-appearance', validate)
        self.assertIn('scripts/sessionstats/artifacts.py verify', validate)
        self.assertIn('scripts/sessionstats/privacy.py', validate)
        release = (ROOT / '.github/workflows/wotmods-release.yml').read_text()
        push = release.split('  push:\n', 1)[1].split('  workflow_dispatch:', 1)[0]
        self.assertNotIn('.github/scripts/prepare_ubuntu_mirrors.py', push)
        self.assertNotIn('tests/test_sessionstats_apt_mirrors.py', push)


if __name__ == '__main__':
    unittest.main()
