"""Installation, migration and concurrent publication contracts for the two ZIPs."""
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('release_installers', ROOT/'scripts/release_installers.py')
r = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r)


def archive(files):
    target = io.BytesIO()
    with zipfile.ZipFile(target, 'w') as z:
        for name, data in files.items():
            z.writestr(name, data)
    return target.getvalue()


def mod(identifier, version, payload=b'payload'):
    return archive({'meta.xml': '<root><id>'+identifier+'</id><version>'+version+'</version></root>',
                    'res/'+identifier+'/module.pyc': payload})


def build(directory, kind, version, internal=False, stable=False, installed_name=None):
    directory.mkdir(parents=True, exist_ok=True)
    prefix = r.KINDS[kind][1]
    primary = prefix+version+'.wotmod'
    (directory/primary).write_bytes(mod(prefix[:-1], version))
    if kind == 'sessionstats':
        config, language = b'{"language":"auto"}', b'{"languages":{"en":{}}}'
        dependency = mod('net.openwg.gameface', '1.2.2')
        report_data={'version':version, 'client_target':r.CLIENT, 'languages_config_sha256':r.digest(language)}
        if stable:
            report_data['installed_package']=installed_name or r.SESSIONSTATS_PACKAGE
        if internal:
            language=json.dumps({'schema_version':1,'languages':{code:{'title':'Fixture'} for code in ('en','pl','ru','fr','de','es','uk')}}).encode()
            resources=r.read_zip(io.BytesIO((directory/primary).read_bytes()))
            resources['res/grz_session_stats/languages.json']=language
            (directory/primary).write_bytes(archive(resources))
            del report_data['languages_config_sha256']
            report_data.update(languages_resource='res/grz_session_stats/languages.json',languages_resource_sha256=r.digest(language))
        report=json.dumps(report_data).encode()
        (directory/'grz.sessionstats.json').write_bytes(config)
        (directory/'net.openwg.gameface_1.2.2.wotmod').write_bytes(dependency)
        (directory/'BUILD.json').write_bytes(report)
        bundled = {
            'mods/'+r.CLIENT+'/'+((installed_name or r.SESSIONSTATS_PACKAGE) if stable else primary):(directory/primary).read_bytes(),
            'mods/'+r.CLIENT+'/net.openwg/net.openwg.gameface_1.2.2.wotmod':dependency,
            'mods/configs/grz.sessionstats.json'+('.example' if stable else ''):config,
            'mods/configs/grz.sessionstats.languages.json':language,
            'BUILD.json':report, 'README_PL.txt':b'Legacy instructions',
            'LICENSE.txt':b'GPL', 'source/src/main.py':b'# corresponding source',
            'source/third_party/openwg/net.openwg.gameface_1.2.2.wotmod':dependency,
            'SHA256SUMS.txt':b'legacy installer manifest',
        }
        if internal:
            del bundled['mods/configs/grz.sessionstats.languages.json']
            bundled['source/data/languages.json']=language
        (directory/('wot-statystyki-sesji-v'+version+'.zip')).write_bytes(archive(bundled))
    r.manifest(directory)


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root/'build'
        self.source.mkdir()
        self.out = self.root/'out'
        self.out.mkdir()

    def both(self):
        for kind, version in [('staysharp','1.6.5'),('sessionstats','0.2.12')]:
            src=self.root/kind
            build(src,kind,version)
            r.package(src,self.out,kind)

    def test_two_zips_install_together_without_active_configs_or_doc_collisions(self):
        self.both()
        reports=r.verify_directory(self.out)
        self.assertEqual(len(reports),2)
        paths=[set(report[3]) for report in reports]
        self.assertFalse(paths[0]&paths[1])
        for _,_,_,files,_ in reports:
            configs=[n for n in files if n.startswith('mods/configs/')]
            self.assertTrue(configs)
            self.assertTrue(all(n.endswith('.json.example') for n in configs))
            self.assertFalse(any(n.endswith('.zip') for n in files))
        stats=next(x for x in reports if x[0]=='sessionstats')
        self.assertIn('docs/sessionstats/source/src/main.py',stats[3])
        self.assertIn('docs/sessionstats/LICENSE.txt',stats[3])

    def test_packaging_is_deterministic(self):
        build(self.source,'sessionstats','0.2.12')
        path=r.package(self.source,self.out,'sessionstats')
        first=path.read_bytes()
        path=r.package(self.source,self.out,'sessionstats')
        self.assertEqual(first,path.read_bytes())

    def test_internal_catalog_stays_inside_mod_and_only_main_config_is_installed(self):
        build(self.source,'sessionstats','0.3.0',internal=True)
        target=r.package(self.source,self.out,'sessionstats')
        kind,version,client,files,primary=r.verify(target)
        self.assertEqual((kind,version),('sessionstats','0.3.0'))
        self.assertIn('res/grz_session_stats/languages.json',r.read_zip(io.BytesIO(files[primary])))
        self.assertEqual({n for n in files if n.startswith('mods/configs/')},
                         {'mods/configs/grz.sessionstats.json.example'})
        self.assertIn('docs/sessionstats/source/data/languages.json',files)

    def test_internal_catalog_hash_is_checked_before_installation(self):
        build(self.source,'sessionstats','0.3.0',internal=True)
        report=json.loads((self.source/'BUILD.json').read_bytes())
        report['languages_resource_sha256']='0'*64
        (self.source/'BUILD.json').write_text(json.dumps(report))
        r.manifest(self.source)
        with self.assertRaises(ValueError): r.package(self.source,self.out,'sessionstats')

    def test_versioned_zip_contains_only_the_stable_sessionstats_filename(self):
        build(self.source,'sessionstats','0.3.3',internal=True,stable=True)
        target=r.package(self.source,self.out,'sessionstats')
        _,version,client,files,primary=r.verify(target)
        self.assertEqual(target.name,'Session-Stats-v0.3.3.zip')
        self.assertEqual(version,'0.3.3')
        self.assertEqual(primary,'mods/'+client+'/grz_sessions_stats.wotmod')
        self.assertEqual({n for n in files if n.startswith('mods/'+client+'/') and '/net.openwg/' not in n}, {primary})
        self.assertEqual(files[primary],(self.source/'grz.sessionstats_0.3.3.wotmod').read_bytes())

    def test_extracting_two_releases_overwrites_the_mod_and_preserves_user_config(self):
        game=self.root/'game'
        config=game/'mods/configs/grz.sessionstats.json'
        config.parent.mkdir(parents=True)
        config.write_bytes(b'{"language":"pl","custom":7}')
        paths=[]
        for version in ('0.3.3','0.3.4'):
            source=self.root/('build-'+version)
            build(source,'sessionstats',version,internal=True,stable=True)
            target=r.package(source,self.out,'sessionstats')
            paths.append(target.name)
            with zipfile.ZipFile(target) as installer: installer.extractall(game)
        self.assertEqual(paths,['Session-Stats-v0.3.3.zip','Session-Stats-v0.3.4.zip'])
        packages=list((game/'mods'/r.CLIENT).glob('*.wotmod'))
        self.assertEqual([p.name for p in packages],['grz_sessions_stats.wotmod'])
        import xml.etree.ElementTree as ET
        contents=r.read_zip(packages[0])
        self.assertEqual(ET.fromstring(contents['meta.xml']).findtext('version'),'0.3.4')
        self.assertEqual(config.read_bytes(),b'{"language":"pl","custom":7}')

    def test_unknown_installed_filename_in_build_metadata_is_rejected(self):
        build(self.source,'sessionstats','0.3.3',internal=True,stable=True)
        report=json.loads((self.source/'BUILD.json').read_bytes())
        for name in ['../outside.wotmod','GRZ Session Stats.wotmod','GRZ_Session_Stats_0.3.3.wotmod',None]:
            report['installed_package']=name
            (self.source/'BUILD.json').write_text(json.dumps(report))
            r.manifest(self.source)
            with self.assertRaisesRegex(ValueError,'installed package filename'):
                r.package(self.source,self.out,'sessionstats')

    def test_previous_stable_stats_installer_carries_forward_unchanged(self):
        build(self.source,'sessionstats','0.3.3',internal=True,stable=True,
              installed_name='GRZ_Session_Stats.wotmod')
        path=r.package(self.source,self.out,'sessionstats')
        before=path.read_bytes()
        self.assertEqual(r.verify(path)[4],'mods/'+r.CLIENT+'/GRZ_Session_Stats.wotmod')
        r.normalize(self.out)
        self.assertEqual(path.read_bytes(),before)

    def test_stable_medkit_and_lowercase_stats_installers_coexist_and_carry_unchanged(self):
        medkit=self.root/'medkit'
        build(medkit,'staysharp','1.7.0')
        path=r.package(medkit,self.out,'staysharp')
        _,_,_,files,old_primary=r.verify(path)
        files['mods/'+r.CLIENT+'/GRZ_Medkit_Reminder.wotmod']=files.pop(old_primary)
        del files['docs/staysharp/SHA256SUMS.txt']
        r.write_installer(self.out,'staysharp','1.7.0',r.CLIENT,files)
        build(self.source,'sessionstats','0.3.4',internal=True,stable=True)
        r.package(self.source,self.out,'sessionstats')
        reports=r.verify_directory(self.out)
        self.assertEqual({x[4] for x in reports},{'mods/'+r.CLIENT+'/GRZ_Medkit_Reminder.wotmod',
                                               'mods/'+r.CLIENT+'/grz_sessions_stats.wotmod'})
        before={p.name:p.read_bytes() for p in self.out.glob('*.zip')}
        r.normalize(self.out)
        self.assertEqual({p.name:p.read_bytes() for p in self.out.glob('*.zip')},before)

    def test_legacy_installers_remain_byte_identical_when_carried_forward(self):
        build(self.source,'sessionstats','0.2.12')
        path=r.package(self.source,self.out,'sessionstats')
        before=path.read_bytes()
        self.assertTrue(r.verify(path)[4].endswith('/grz.sessionstats_0.2.12.wotmod'))
        r.normalize(self.out)
        self.assertEqual(path.read_bytes(),before)

    def test_legacy_snapshot_migration_retains_exact_production_bytes(self):
        build(self.source,'staysharp','1.6.4')
        build(self.source,'sessionstats','0.2.11')
        original={p.name:p.read_bytes() for p in self.source.glob('*.wotmod')}
        r.normalize(self.source)
        (self.source/'SHA256SUMS.txt').unlink()
        reports=r.verify_directory(self.source)
        for report in reports:
            for name,data in report[3].items():
                if name.startswith('mods/') and name.endswith('.wotmod'):
                    self.assertEqual(data,original[Path(name).name])

    def test_modern_snapshot_carries_bytes_unchanged(self):
        self.both()
        original={p.name:p.read_bytes() for p in self.out.iterdir()}
        r.normalize(self.out)
        self.assertEqual(original,{p.name:p.read_bytes() for p in self.out.glob('*.zip')})
        r.check_manifest(r.directory_files(self.out))

    def test_notes_contain_two_direct_downloads_installation_and_folded_hashes(self):
        self.both()
        output=self.root/'notes.md'
        r.notes(self.out,output,'example/WotMods','staysharp-v1.6.5')
        text=output.read_text()
        self.assertEqual(text.count('/releases/download/'),2)
        for heading in ('## Downloads','## Installation','## Changes','<details>','.json.example'):
            self.assertIn(heading,text)
        for path in self.out.iterdir():
            self.assertIn(r.digest(path.read_bytes()),text)

    def test_corrupt_legacy_snapshot_is_rejected_without_deletion(self):
        build(self.source,'staysharp','1.6.4')
        (self.source/'com.staysharp.medkitreminder_1.6.4.wotmod').write_bytes(b'tampered')
        before=r.directory_files(self.source)
        with self.assertRaises(ValueError):r.normalize(self.source)
        self.assertEqual(before,r.directory_files(self.source))

    def test_unknown_legacy_asset_is_rejected(self):
        build(self.source,'staysharp','1.6.4')
        (self.source/'unknown.txt').write_text('unknown')
        r.manifest(self.source)
        with self.assertRaises(ValueError):r.normalize(self.source)
        self.assertTrue((self.source/'unknown.txt').exists())

    def test_unverified_source_build_is_rejected(self):
        build(self.source,'sessionstats','0.2.12')
        (self.source/'grz.sessionstats.json').write_bytes(b'{}')
        with self.assertRaises(ValueError):r.package(self.source,self.out,'sessionstats')

    def test_stale_inner_installer_is_rejected_even_with_valid_outer_manifest(self):
        build(self.source,'sessionstats','0.2.12')
        (self.source/'grz.sessionstats.json').write_bytes(b'{}')
        r.manifest(self.source)
        with self.assertRaisesRegex(ValueError,'disagree'):
            r.package(self.source,self.out,'sessionstats')

    def test_wrong_language_hash_is_rejected(self):
        build(self.source,'sessionstats','0.2.12')
        report=json.loads((self.source/'BUILD.json').read_bytes())
        report['languages_config_sha256']='0'*64
        (self.source/'BUILD.json').write_text(json.dumps(report))
        r.manifest(self.source)
        with self.assertRaisesRegex(ValueError,'Language'):
            r.package(self.source,self.out,'sessionstats')

    def test_traversal_duplicate_symlink_and_encrypted_members_are_rejected(self):
        for name in ('../outside','/absolute','mods/../outside','C:/outside','mods\\outside'):
            with self.subTest(name=name),self.assertRaises(ValueError):
                r.read_zip(io.BytesIO(archive({name:b'x'})))
        target=io.BytesIO()
        with zipfile.ZipFile(target,'w') as z:
            info=zipfile.ZipInfo('mods/link')
            info.external_attr=0o120777<<16
            z.writestr(info,b'/tmp')
        with self.assertRaises(ValueError):r.read_zip(io.BytesIO(target.getvalue()))

    def test_missing_duplicate_mod_or_extra_loose_asset_fails_release_verification(self):
        self.both()
        (self.out/'BUILD.json').write_text('{}')
        with self.assertRaises(ValueError):r.verify_directory(self.out)
        (self.out/'BUILD.json').unlink()
        (self.out/'Session-Stats-v0.2.12.zip').unlink()
        with self.assertRaises(ValueError):r.verify_directory(self.out)

    def test_tampered_installer_manifest_is_rejected(self):
        self.both()
        path=self.out/'StaySharp-Medkit-v1.6.5.zip'
        files=r.read_zip(path)
        files['mods/configs/staysharp.medkit.json.example']=b'{}'
        path.write_bytes(archive(files))
        with self.assertRaisesRegex(ValueError,'Checksum'):r.verify(path)

    def test_active_config_is_rejected_even_when_checksummed(self):
        build(self.source,'staysharp','1.6.5')
        path=r.package(self.source,self.out,'staysharp')
        files=r.read_zip(path)
        del files['docs/staysharp/SHA256SUMS.txt']
        files['mods/configs/staysharp.medkit.json']=b'{}'
        with self.assertRaisesRegex(ValueError,'Active configuration'):
            r.write_installer(self.out,'staysharp','1.6.5',r.CLIENT,files)


class SnapshotInstallerTests(unittest.TestCase):
    def test_fast_merges_in_both_orders_migrate_then_carry_without_rollback(self):
        from test_release_snapshot import FAKE_GH
        for order in [('staysharp','sessionstats'),('sessionstats','staysharp')]:
            with self.subTest(order=order),tempfile.TemporaryDirectory() as temporary:
                root=Path(temporary)
                latest=root/'legacy'
                latest.mkdir()
                build(latest,'staysharp','1.6.4')
                build(latest,'sessionstats','0.2.11')
                binpath=root/'bin'
                binpath.mkdir()
                (binpath/'gh').write_text(FAKE_GH)
                (binpath/'gh').chmod(0o755)
                listing=root/'list.json'
                listing.write_text(json.dumps([{'tagName':'latest','isLatest':True,
                    'isDraft':False,'isPrerelease':False,'isImmutable':True}]))
                jobs={}
                for kind,version in [('staysharp','1.6.5'),('sessionstats','0.2.12')]:
                    src=root/(kind+'-source')
                    build(src,kind,version)
                    dest=root/kind
                    dest.mkdir()
                    r.package(src,dest,kind)
                    r.manifest(dest)
                    jobs[kind]=(dest,version)
                for kind in order:
                    dest,version=jobs[kind]
                    env=dict(os.environ,PATH=str(binpath)+os.pathsep+os.environ['PATH'],
                        GITHUB_REPOSITORY='example/WotMods',FAKE_RELEASE_LIST=str(listing),
                        FAKE_RELEASE_DIR=str(latest))
                    result=subprocess.run(['bash',str(ROOT/'scripts/release_snapshot.sh'),str(dest),
                        r.installer_name(kind,version),r.KINDS[kind][0]+'*.zip'],
                        env=env,capture_output=True,text=True)
                    self.assertEqual(result.returncode,0,result.stdout+result.stderr)
                    (dest/'SHA256SUMS.txt').unlink()
                    r.verify_directory(dest)
                    if latest.name!='legacy':
                        other=next(p for p in latest.glob('*.zip') if p.name.startswith(r.KINDS[order[0]][0]))
                        self.assertEqual(other.read_bytes(),(dest/other.name).read_bytes())
                    latest=dest
                reports=r.verify_directory(latest)
                self.assertEqual({(x[0],x[1]) for x in reports},
                    {('staysharp','1.6.5'),('sessionstats','0.2.12')})
                # Stale same-mod primary cannot roll back the modern ZIP snapshot.
                stale=root/'stale'
                stale.mkdir()
                r.package(root/'staysharp-source',stale,'staysharp')
                r.manifest(stale)
                env['FAKE_RELEASE_DIR']=str(latest)
                result=subprocess.run(['bash',str(ROOT/'scripts/release_snapshot.sh'),str(stale),
                    'StaySharp-Medkit-v1.6.5.zip','StaySharp-Medkit-v*.zip'],
                    env=env,capture_output=True,text=True)
                self.assertEqual(result.returncode,75,result.stderr)


if __name__=='__main__':unittest.main()
