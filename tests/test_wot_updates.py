import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import wot_updates as w
from wot_dispatch import needs_rebuild


class CacheTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'cache.json'
        self.calls = 0

    def collect(self):
        self.calls += 1
        return {'client_version': '2.4.1.1', 'items': []}

    def update(self, now, **kwargs):
        return w.update_cache(self.path, now=now, collect_fn=self.collect, **kwargs)

    def test_rolling_24_hours_not_calendar_day(self):
        self.update(100000)
        self.assertEqual(self.update(100000 + 86399)[1:], (False, True))
        self.assertEqual(self.calls, 1)
        self.assertEqual(self.update(100000 + 86400)[1:], (True, True))
        self.assertEqual(self.calls, 2)

    def test_schedule_force_refreshes_before_ttl(self):
        self.update(100000)
        self.assertEqual(self.update(100001, force=True)[1:], (True, True))
        self.assertEqual(self.calls, 2)

    def test_failed_refresh_preserves_good_timestamp_and_data(self):
        good = self.update(100000)[0]
        def fail():
            raise ValueError('HTTP 403')
        bad, changed, fresh = w.update_cache(self.path, now=200000, collect_fn=fail)
        self.assertFalse(fresh)
        self.assertTrue(changed)
        self.assertEqual(bad['fetched_at'], good['fetched_at'])
        self.assertEqual(bad['data'], good['data'])
        self.assertEqual(self.update(200899)[1:], (False, False))
        self.assertEqual(self.update(200900)[1:], (True, True))

    def test_forced_failure_cannot_authorize_release_from_fresh_old_cache(self):
        self.update(100000)
        def fail():
            raise OSError('offline')
        w.update_cache(self.path, now=100001, force=True, collect_fn=fail)
        self.assertEqual(self.update(100002)[1:], (False, False))

    def test_corrupt_or_unknown_schema_is_refetched(self):
        for content in ('not json', '{"schema":2}'):
            self.path.write_text(content)
            self.assertEqual(self.update(100000)[1:], (True, True))

    def test_future_clock_and_injected_version_are_rejected(self):
        self.update(200000)
        self.assertEqual(self.update(100000)[1:], (True, True))
        state = json.loads(self.path.read_text())
        state['data']['client_version'] = '2.4.1.1\nfresh=true'
        self.path.write_text(json.dumps(state))
        self.assertEqual(self.update(100001)[1:], (True, True))

    def test_invalid_remote_version_does_not_enter_good_cache(self):
        result = w.update_cache(self.path, now=100000, collect_fn=lambda: {'client_version':'2.4.1_3'})
        self.assertFalse(result[2])
        self.assertNotIn('fetched_at', result[0])


class EvidenceTests(unittest.TestCase):
    def test_exact_four_component_archive_path(self):
        self.assertEqual(w.directory_from_listing('Path = mods/2.4.1.1/readme.txt\n'), '2.4.1.1')
        self.assertIsNone(w.directory_from_listing('Path = wot_2.4.1.5504_client.wgpkg\n'))
        self.assertIsNone(w.directory_from_listing('Path = mods/2.4.1_3/readme.txt\n'))
        with self.assertRaises(ValueError):
            w.directory_from_listing('Path = mods/2.4.1.1\nPath = mods/2.5.0.0\n')

    def test_rss_validation_and_future_item_retained_as_news_only(self):
        body = b'<rss><channel><item><title>Common Test 9.9</title><link>https://worldoftanks.eu/pl/news/updates/test/</link><pubDate>Mon, 26 Oct 2099 16:00:00 GMT</pubDate></item></channel></rss>'
        item = w.rss_items(body)[0]
        self.assertNotIn('client_version', item)
        with self.assertRaises(ValueError):
            w.rss_items(body.replace(b'worldoftanks.eu', b'example.com'))
        for bad in (b'<html>challenge</html>', b'<rss><channel/></rss>', b'<!DOCTYPE x><rss/>'):
            with self.assertRaises(ValueError):
                w.rss_items(bad)

    def test_chain_requires_eu_production_install(self):
        meta = w.xml(b'<protocol><predefined_section><app_id>WOT.EU.PRODUCTION</app_id></predefined_section></protocol>')
        def chain(kind='install', old='0'):
            return w.xml(('<protocol><patches_chain type="'+kind+'"><patch><part>client</part><version_from>'+old+'</version_from><version_to>2.4.1.24108</version_to><files><file><name>wot_2.4.1.5504_eu_test/wot_2.4.1_client.wgpkg</name><size>12000</size></file></files></patch></patches_chain><web_seeds><url>http://dl-wot-gc.wargaming.net/eu/patches/</url></web_seeds></protocol>').encode())
        result = w.client_chain(meta, chain())
        self.assertEqual(result[0]['to'], '2.4.1.24108')
        self.assertTrue(result[0]['files'][0]['url'].startswith('https://'))
        for wrong in (chain('preload'), chain(old='2.4.1.24091')):
            with self.assertRaises(ValueError): w.client_chain(meta, wrong)
        meta.find('./predefined_section/app_id').text = 'WOT.CT.PRODUCTION'
        with self.assertRaises(ValueError): w.client_chain(meta, chain())

    def test_same_directory_and_downgrade_do_not_dispatch(self):
        self.assertFalse(needs_rebuild('2.4.1.1', ['2.4.1.1'] * 2))
        self.assertTrue(needs_rebuild('2.4.1.1', ['2.4.1.0'] * 2))
        with self.assertRaises(ValueError): needs_rebuild('2.4.1.0', ['2.4.1.1'] * 2)
        with self.assertRaises(ValueError): needs_rebuild('2.4.1_3', ['2.4.1.0'] * 2)
        with self.assertRaises(ValueError): needs_rebuild('2.4.1.1', ['2.4.1.0'])

class DispatchTests(unittest.TestCase):
    def setUp(self):
        import hashlib
        from test_release_installers import build, r
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.out = self.root / 'installers'
        self.out.mkdir()
        for kind, version in [('staysharp', '1.7.0'), ('sessionstats', '0.3.4')]:
            source = self.root / kind
            build(source, kind, version)
            r.package(source, self.out, kind)
        self.metadata = {'immutable':True, 'draft':False, 'prerelease':False, 'tag_name':'fixture',
                         'assets':[{'name':p.name, 'digest':'sha256:'+hashlib.sha256(p.read_bytes()).hexdigest()} for p in self.out.iterdir()]}
        self.dispatched = []
        self.pending = False
        self.env = patch.dict('os.environ', {'GITHUB_REF':'refs/heads/main', 'GITHUB_REPOSITORY':'example/repo', 'WOT_CLIENT_VERSION':'2.4.1.1'})
        self.env.start()
        self.addCleanup(self.env.stop)

    def gh(self, *args):
        import shutil
        if args[0] == 'api': return json.dumps(self.metadata)
        if args[:2] == ('release', 'download'):
            destination = Path(args[args.index('--dir') + 1])
            for p in self.out.iterdir():shutil.copyfile(p, destination/p.name)
            return ''
        if args[:2] == ('run', 'list'): return json.dumps([{'status':'queued'}] if self.pending else [])
        if args[:2] == ('workflow', 'run'):
            self.dispatched.append(args[2]);return ''
        raise AssertionError(args)

    def test_dispatches_both_existing_main_publishers(self):
        import wot_dispatch as d
        with patch.object(d, 'gh', side_effect=self.gh): d.main()
        self.assertEqual(self.dispatched, ['release.yml', 'sessionstats-release.yml'])

    def test_pending_publishers_are_not_duplicated(self):
        import wot_dispatch as d
        self.pending=True
        with patch.object(d, 'gh', side_effect=self.gh): d.main()
        self.assertEqual(self.dispatched, [])

    def test_mutable_or_corrupt_release_cannot_dispatch(self):
        import wot_dispatch as d
        self.metadata['immutable']=False
        with patch.object(d, 'gh', side_effect=self.gh), self.assertRaises(ValueError): d.main()
        self.metadata['immutable']=True
        self.metadata['assets'][0]['digest']='sha256:invalid'
        with patch.object(d, 'gh', side_effect=self.gh), self.assertRaises(ValueError): d.main()
        self.assertEqual(self.dispatched, [])

    def test_feature_branch_cannot_dispatch(self):
        import wot_dispatch as d
        with patch.dict('os.environ', {'GITHUB_REF':'refs/heads/feature'}), patch.object(d, 'gh') as gh, self.assertRaises(ValueError): d.main()
        gh.assert_not_called()


if __name__ == '__main__':
    unittest.main()
