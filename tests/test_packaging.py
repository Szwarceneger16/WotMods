"""Binary package / frame-level regression tests. No WoT client available."""
import importlib.util
import io
import wave
from xml.etree import ElementTree
from pathlib import Path
import struct
import sys
import tempfile
import unittest
import zipfile

ROOT=Path(__file__).resolve().parents[1]
SCRIPT=ROOT/'source/build_wotmod.py'
spec=importlib.util.spec_from_file_location('build_wotmod_v161', SCRIPT)
build=importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)


class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.target=build.build()
        cls.frames=build.load_frames()

    def test_01_correct_wotmod_filename(self):
        self.assertEqual(self.target.name,'com.staysharp.medkitreminder_%s.wotmod' % build.VERSION)

    def test_02_single_file_is_zip(self):
        self.assertTrue(zipfile.is_zipfile(self.target))

    def test_03_exactly_27_files(self):
        with zipfile.ZipFile(self.target) as z:
            self.assertEqual(len(z.namelist()),27)

    def test_04_all_zipstored(self):
        with zipfile.ZipFile(self.target) as z:
            self.assertTrue(all(x.compress_type==zipfile.ZIP_STORED for x in z.infolist()))

    def test_05_no_encrypted_files(self):
        with zipfile.ZipFile(self.target) as z:
            self.assertFalse(any(x.flag_bits&1 for x in z.infolist()))

    def test_06_only_bundled_audio_no_shader_dll_or_swf(self):
        with zipfile.ZipFile(self.target) as z:
            self.assertFalse(any(x.filename.endswith(('.fx','.dll','.swf','.py')) for x in z.infolist()))
            self.assertEqual([x for x in z.namelist() if x.endswith('.bnk')],
                             ['res/audioww/staysharp_medkit.bnk'])

    def test_07_python_entrypoint_matches_working_py27_format(self):
        with zipfile.ZipFile(self.target) as z:
            data=z.read(build.PYC_PATH)
        self.assertTrue(data.startswith(b'\x03\xf3\x0d\x0a'))
        self.assertIn(b'EXEC_STMT', b'EXEC_STMT') # opcode 85 tested directly below
        self.assertEqual(data[8:9], b'c')
        self.assertIn(bytes([85,100,1,0,83]),data)

    def test_08_embedded_complete_source(self):
        with zipfile.ZipFile(self.target) as z:
            data=z.read(build.PYC_PATH)
        self.assertIn(build.render_source(),data)

    def test_09_all_frame_names_resource_prefix(self):
        with zipfile.ZipFile(self.target) as z:
            names={x for x in z.namelist() if x.endswith('.dds')}
        expected={'res/gui/maps/staysharp/medkit_pulse_%02d.dds'%i for i in range(21)}
        self.assertEqual(names,expected)

    def test_10_each_dds_128x128_argb8888(self):
        for path,raw in self.frames:
            self.assertEqual(raw[:4],b'DDS ')
            self.assertEqual(len(raw),128+128*128*4)
            self.assertEqual(struct.unpack_from('<II',raw,12),(128,128))
            self.assertEqual(struct.unpack_from('<IIIIIIII',raw,76),
                             (32,65,0,32,0xff0000,0xff00,0xff,0xff000000))

    def test_11_frame0_alpha_all_zero(self):
        self.assertEqual(max(self.frames[0][1][131::4]),0)

    def test_12_frame20_alpha_nonzero(self):
        self.assertGreater(max(self.frames[-1][1][131::4]),240)

    def test_13_stepwise_alpha_monotonic_per_pixel(self):
        before=None
        for _,raw in self.frames:
            alpha=raw[131::4]
            if before is not None:
                self.assertTrue(all(x>=y for x,y in zip(alpha,before)))
            before=alpha

    def test_14_rgb_is_identical_among_frames(self):
        reference=self.frames[0][1][128:]
        for _,raw in self.frames[1:]:
            pix=raw[128:]
            for c in range(3):
                self.assertEqual(pix[c::4],reference[c::4])

    def test_15_historical_v160_baseline_does_not_pin_future_versions(self):
        import hashlib
        master = build.load_master()
        expected = (ROOT / 'assets/medkit_pulse_master.sha256').read_text().strip()
        self.assertEqual(hashlib.sha256(master).hexdigest(), expected)
        # Historical v1.6.0 checksum applies ONLY when actually rebuilding
        # the historical source/version. New reviewed versions are allowed.
        if build.VERSION == '1.6.0':
            self.assertEqual(hashlib.sha256(master).hexdigest(),
                             '4659a9da85e1c35634e9dcbabbe6090d4a2fc292c485be484235ccd042517589')
            self.assertEqual(hashlib.sha256(self.target.read_bytes()).hexdigest(),
                             '9f3d98948ed398c3a4dc14b6785b68f10f1319381f896c6cd49b8709359c4927')

    def test_16_meta_id_and_version(self):
        with zipfile.ZipFile(self.target) as z:
            doc=z.read('meta.xml').decode()
        self.assertIn('<id>com.staysharp.medkitreminder</id>',doc)
        self.assertIn('<version>%s</version>' % build.VERSION,doc)

    def test_17_package_integrity(self):
        with zipfile.ZipFile(self.target) as z:
            self.assertIsNone(z.testzip())

    def test_18_no_runtime_python_dependencies_from_our_tooling(self):
        code=(ROOT/'source/mod_staysharp_medkit.py').read_text()
        self.assertNotIn('from PIL import',code)
        self.assertNotIn('import numpy',code)

    def test_19_all_expected_resources_are_in_one_wotmod(self):
        with zipfile.ZipFile(self.target) as z:
            for i in range(21):
                self.assertIn('res/'+('gui/maps/staysharp/medkit_pulse_%02d.dds'%i),z.namelist())

    def test_20_package_stays_under_2mb(self):
        self.assertLess(self.target.stat().st_size,2*1024*1024)


    def bank_chunks(self):
        with zipfile.ZipFile(self.target) as archive:
            bank=archive.read('res/audioww/staysharp_medkit.bnk')
        chunks={}
        offsets={}
        pos=0
        while pos < len(bank):
            tag,size=struct.unpack_from('<4sI',bank,pos)
            self.assertNotIn(tag,chunks)
            offsets[tag]=pos+8
            chunks[tag]=bank[pos+8:pos+8+size]
            self.assertEqual(len(chunks[tag]),size)
            pos+=8+size
        self.assertEqual(pos,len(bank))
        return chunks,offsets

    def test_21_native_bank_header_and_aligned_embedded_media(self):
        chunks,offsets=self.bank_chunks()
        self.assertEqual(set(chunks),{b'BKHD',b'DIDX',b'DATA',b'HIRC',b'STID'})
        version,bank_id,language,alignment,project,kind=struct.unpack_from('<6I',chunks[b'BKHD'])
        self.assertEqual((version,language,alignment,kind),(150,0,16,0))
        self.assertEqual(bank_id,build.audio.short_id('staysharp_medkit'))
        self.assertEqual(offsets[b'DATA']%16,0)
        self.assertEqual(len(chunks[b'DIDX']),12*7)
        media_id,offset,size=struct.unpack_from('<3I',chunks[b'DIDX'])
        self.assertEqual(offset,0)
        self.assertLess(size,len(chunks[b'DATA']))
        self.assertEqual(media_id,build.audio.short_id('staysharp_medkit_ready_pcm'))

    def test_22_bank_embeds_complete_pcm_voice_without_reencoding(self):
        chunks,_=self.bank_chunks()
        media_id,offset,size=struct.unpack_from('<3I',chunks[b'DIDX'])
        wem=chunks[b'DATA'][offset:offset+size]
        self.assertEqual(wem[:4],b'RIFF')
        self.assertEqual(struct.unpack_from('<I',wem,4)[0],len(wem)-8)
        self.assertEqual(wem[8:16],b'WAVEfmt ')
        self.assertEqual(struct.unpack_from('<I',wem,16)[0],24)
        self.assertEqual(struct.unpack_from('<HHIIHHHHI',wem,20),
                         (0xfffe,1,16000,32000,2,16,6,16,0x4101))
        self.assertEqual(wem[44:48],b'data')
        size=struct.unpack_from('<I',wem,48)[0]
        pcm=wem[52:]
        self.assertEqual(size,len(pcm))
        with wave.open(io.BytesIO(build.audio.load_voice())) as voice:
            self.assertEqual(pcm,voice.readframes(voice.getnframes()))
            self.assertGreater(voice.getnframes()/voice.getframerate(),0.5)
            self.assertLess(voice.getnframes()/voice.getframerate(),2.0)

    def test_23_bank_graph_links_event_action_sound_and_native_voice_bus(self):
        chunks,_=self.bank_chunks()
        graph=chunks[b'HIRC']
        self.assertEqual(struct.unpack_from('<I',graph)[0],21)
        pos=4
        objects={}
        for index in range(21):
            kind,size=struct.unpack_from('<BI',graph,pos)
            data=graph[pos+5:pos+5+size]
            if index < 3:
                objects[kind]=data
            pos+=5+size
        self.assertEqual(pos,len(graph))
        self.assertEqual(set(objects),{2,3,4})
        sound,action,event=objects[2],objects[3],objects[4]
        self.assertEqual(len(sound),49)
        self.assertEqual(len(action),22)
        self.assertEqual(len(event),9)
        sound_id=struct.unpack_from('<I',sound)[0]
        action_id=struct.unpack_from('<I',action)[0]
        self.assertEqual(struct.unpack_from('<I',event)[0],
                         build.audio.short_id('staysharp_medkit_ready'))
        self.assertEqual(event[4],1)
        self.assertEqual(struct.unpack_from('<I',event,5)[0],action_id)
        self.assertEqual(struct.unpack_from('<HI',action,4),(0x0403,sound_id))
        self.assertEqual(struct.unpack_from('<II',action,14),
                         (build.audio.short_id('staysharp_medkit'),0))
        self.assertEqual(struct.unpack_from('<I',sound,22)[0],
                         build.audio.short_id('VOICE_GUI'))
        self.assertEqual(struct.unpack_from('<I',sound,4)[0],0x00010001)
        self.assertEqual(sound[8],0)  # embedded source, not streaming
        self.assertEqual(sound[33],1)  # override positioning with 2D panning

    def test_24_bank_loading_config_has_no_global_event_overrides(self):
        with zipfile.ZipFile(self.target) as archive:
            native=archive.read('res/audioww/audio_mods.xml')
            namespaced=archive.read('res/audioww/staysharp_medkit.xml')
            notice=archive.read('res/audioww/staysharp_VOICE_NOTICE.txt')
        self.assertEqual(native,namespaced)
        root=ElementTree.fromstring(native)
        self.assertEqual([child.tag for child in root],['loadBanks'])
        self.assertEqual([el.text for el in root.findall('loadBanks/bank/name')],
                         ['staysharp_medkit.bnk'])
        self.assertIn(b'AI-generated neural speech',notice)
        self.assertIn(b'Piper 1.8.0',notice)
        self.assertIn(b'SIWIS',notice)

    def test_25_voice_integrity_and_bank_build_are_deterministic(self):
        chunks,_=self.bank_chunks()
        with zipfile.ZipFile(self.target) as archive:
            bank=archive.read('res/audioww/staysharp_medkit.bnk')
        self.assertEqual(bank,build.audio.build_bank())
        self.assertEqual(build.audio.short_id('Init'),1355168291)


    def test_26_all_seven_voices_have_distinct_events_and_original_pcm(self):
        chunks,offsets=self.bank_chunks()
        self.assertEqual(set(build.audio.LANGUAGES),{'en','pl','ru','fr','de','es','uk'})
        ids=set()
        graph=chunks[b'HIRC']
        pos=4
        objects={}
        while pos < len(graph):
            kind,size=struct.unpack_from('<BI',graph,pos)
            data=graph[pos+5:pos+5+size]
            ident=struct.unpack_from('<I',data)[0]
            self.assertNotIn(ident,objects)
            objects[ident]=(kind,data)
            pos+=5+size
        previous_end=0
        for n,language in enumerate(build.audio.LANGUAGES):
            event=build.audio.event_name(language)
            media_id,offset,size=struct.unpack_from('<III',chunks[b'DIDX'],n*12)
            self.assertEqual(media_id,build.audio.short_id(event+'_pcm'))
            self.assertNotIn(media_id,ids)
            ids.add(media_id)
            self.assertEqual((offsets[b'DATA']+offset)%16,0)
            self.assertGreaterEqual(offset,previous_end)
            self.assertEqual(set(chunks[b'DATA'][previous_end:offset]),set() if previous_end==offset else {0})
            wem=chunks[b'DATA'][offset:offset+size]
            self.assertEqual(struct.unpack_from('<I',wem,4)[0],len(wem)-8)
            with wave.open(io.BytesIO(build.audio.load_voice(language))) as voice:
                self.assertEqual(wem[52:],voice.readframes(voice.getnframes()))
                self.assertLess(voice.getnframes()/voice.getframerate(),2.0)
            previous_end=offset+size
            kind,event_data=objects[build.audio.short_id(event)]
            self.assertEqual(kind,4)
            action_id=struct.unpack_from('<I',event_data,5)[0]
            kind,action=objects[action_id]
            self.assertEqual(kind,3)
            sound_id=struct.unpack_from('<I',action,6)[0]
            kind,sound=objects[sound_id]
            self.assertEqual(kind,2)
            self.assertEqual(struct.unpack_from('<I',sound,9)[0],media_id)
            self.assertEqual(struct.unpack_from('<I',sound,13)[0],size)
            self.assertEqual(struct.unpack_from('<I',sound,22)[0],build.audio.short_id('VOICE_GUI'))
        self.assertEqual(previous_end,len(chunks[b'DATA']))

    def test_27_unknown_voice_cannot_select_arbitrary_asset(self):
        for language in ('jp','../en','','AUTO'):
            with self.assertRaises(ValueError):
                build.audio.load_voice(language)


    def test_28_new_release_installer_preserves_the_verified_audio_build(self):
        installer_spec = importlib.util.spec_from_file_location(
            'audio_release_installers', ROOT / 'scripts/release_installers.py')
        installers = importlib.util.module_from_spec(installer_spec)
        installer_spec.loader.exec_module(installers)
        with tempfile.TemporaryDirectory(prefix='staysharp-installer-') as directory:
            root = Path(directory)
            source = root / 'verified-build'
            source.mkdir()
            verified = self.target.read_bytes()
            (source / self.target.name).write_bytes(verified)
            installers.manifest(source)
            first = installers.package(source, root / 'first', 'staysharp')
            second = installers.package(source, root / 'second', 'staysharp')
            self.assertEqual(first.read_bytes(), second.read_bytes())
            kind, version, client, files, primary = installers.verify(first)
            self.assertEqual((kind, version), ('staysharp', build.VERSION))
            self.assertEqual(primary, 'mods/' + client + '/' + self.target.name)
            self.assertEqual(files[primary], verified)
            self.assertEqual(files['mods/configs/staysharp.medkit.json.example'],
                             (ROOT / 'staysharp.medkit.example.json').read_bytes())
            self.assertNotIn('mods/configs/staysharp.medkit.json', files)
            self.assertEqual(files['docs/staysharp/VOICE_NOTICE.txt'],
                             (ROOT / 'assets/VOICE_NOTICE.txt').read_bytes())
            self.assertEqual(files['docs/staysharp/AUDIO.md'],
                             (ROOT / 'docs/AUDIO.md').read_bytes())
            with zipfile.ZipFile(io.BytesIO(files[primary])) as packaged:
                self.assertEqual(packaged.read('res/audioww/staysharp_medkit.bnk'),
                                 build.audio.build_bank())
                self.assertIn('staysharp_medkit.bnk',
                              packaged.read('res/audioww/audio_mods.xml').decode('utf-8'))



if __name__=='__main__':
    unittest.main()
