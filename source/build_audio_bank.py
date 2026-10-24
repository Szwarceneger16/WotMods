"""Deterministic, seven-language Wwise 2023.1 (bank v150) PCM bank.

No authoring tool is needed to rebuild this small subset: one embedded PCM
source per language, with a 2D Sound, Play action and Event for each. All
voices route to WoT's existing VOICE_GUI bus.
The bank never defines/replaces game buses, RTPCs, switches or game events.
Format reference: https://github.com/bnnm/wwiser (parser/wparser.py).
"""
import base64
import hashlib
import io
from pathlib import Path
import struct
import wave
import zlib

ASSETS = Path(__file__).resolve().parents[1] / 'assets'
BANK_NAME = 'staysharp_medkit'
EVENT_NAME = 'staysharp_medkit_ready'
BUS_NAME = 'VOICE_GUI'
BANK_VERSION = 150
LANGUAGES = ('en', 'pl', 'ru', 'fr', 'de', 'es', 'uk')


def u32(value):
    return struct.pack('<I', value)


def short_id(name):
    """Wwise's lowercase FNV-1 (multiply, then XOR), not FNV-1a."""
    value = 2166136261
    for byte in name.lower().encode('ascii'):
        value = ((value * 16777619) & 0xffffffff) ^ byte
    return value


def chunk(name, data):
    return name.encode('ascii') + u32(len(data)) + data


def hirc(kind, data):
    return bytes([kind]) + u32(len(data)) + data


def event_name(language):
    if language not in LANGUAGES:
        raise ValueError('Unsupported voice language')
    return EVENT_NAME if language == 'en' else EVENT_NAME + '_' + language


def load_voice(language='en'):
    event_name(language)
    stem = ASSETS / 'medkit_ready' if language == 'en' else ASSETS / 'voices' / language
    encoded = Path(str(stem) + '.wav.b85').read_text(encoding='ascii')
    data = zlib.decompress(base64.b85decode(''.join(encoded.split())))
    expected = Path(str(stem) + '.sha256').read_text(encoding='ascii').strip()
    if hashlib.sha256(data).hexdigest() != expected:
        raise ValueError('Ready voice checksum mismatch')
    with wave.open(io.BytesIO(data)) as audio:
        if (audio.getnchannels(), audio.getsampwidth(), audio.getframerate(),
                audio.getcomptype()) != (1, 2, 16000, 'NONE'):
            raise ValueError('Expected mono 16-bit 16 kHz PCM voice')
        if not 0 < audio.getnframes() <= 32000:
            raise ValueError('Ready voice must last at most two seconds')
    return data


def _wem(language):
    with wave.open(io.BytesIO(load_voice(language))) as audio:
        samples = audio.readframes(audio.getnframes())
    # Wwise's 24-byte PCM fmt: cbSize=6, valid bits=16, serialized
    # AkChannelConfig = mono/front-center (mask=4, standard type=1).
    fmt = struct.pack('<HHIIHHHHI', 0xfffe, 1, 16000, 32000, 2, 16, 6, 16, 0x4101)
    body = b'WAVE' + chunk('fmt ', fmt) + chunk('data', samples)
    voice = b'RIFF' + u32(len(body)) + body
    return voice


def _graph(event, size):
    bank_id = short_id(BANK_NAME)
    media_id = short_id(event + '_pcm')
    sound_id = short_id(event + '_sound')
    action_id = short_id(event + '_play')
    # AkBankSourceData: built-in PCM codec, embedded data, one media source.
    source = u32(0x00010001) + b'\0' + u32(media_id) + u32(size) + b'\x80'
    # No FX/metadata or actor parent. Existing VOICE_GUI bus; default
    # priority/properties, 2D panning, no aux/reflections or state/RTPC curves.
    node = (b'\0\0\0\0' + u32(short_id(BUS_NAME)) + u32(0)
            + b'\0' + b'\0\0' + b'\x01' + b'\0' + u32(0)
            + b'\0\0\0\0\0\0' + b'\0\0' + b'\0\0')
    sound = hirc(2, u32(sound_id) + source + node)
    action = hirc(3, u32(action_id) + struct.pack('<H', 0x0403)
                  + u32(sound_id) + b'\0\0\0\x04' + u32(bank_id) + u32(0))
    event = hirc(4, u32(short_id(event)) + b'\x01' + u32(action_id))
    return sound + action + event


def build_bank():
    bank_id = short_id(BANK_NAME)
    media = bytearray()
    index = bytearray()
    graph = bytearray()
    for language in LANGUAGES:
        event = event_name(language)
        voice = _wem(language)
        media.extend(bytes((-len(media)) % 16))
        index.extend(u32(short_id(event + '_pcm')) + u32(len(media)) + u32(len(voice)))
        media.extend(voice)
        graph.extend(_graph(event, len(voice)))
    header = (u32(BANK_VERSION) + u32(bank_id) + u32(0) + u32(16)
              + u32(0) + u32(0) + bytes(16))
    # Align embedded media to the bank's declared 16-byte boundary.
    prefix = chunk('BKHD', header) + chunk('DIDX', bytes(index))
    padding = (-(len(prefix) + 8)) % 16
    if padding:
        header += bytes(padding)
        prefix = chunk('BKHD', header) + chunk('DIDX', bytes(index))
    name = BANK_NAME.encode('ascii')
    strings = u32(1) + u32(1) + u32(bank_id) + bytes([len(name)]) + name
    return (prefix + chunk('DATA', bytes(media)) + chunk('HIRC', u32(3 * len(LANGUAGES)) + bytes(graph))
            + chunk('STID', strings))


def resources():
    # Native WoT reads audio_mods.xml. BanksLoader users can merge the same
    # namespaced bank descriptor without replacing any other mod's config.
    config = (b'<?xml version="1.0" encoding="UTF-8"?>\n'
              b'<audio_mods.xml>\n  <loadBanks><bank><name>'
              + BANK_NAME.encode('ascii') + b'.bnk</name></bank></loadBanks>\n'
              b'</audio_mods.xml>\n')
    return [
        ('res/audioww/' + BANK_NAME + '.bnk', build_bank()),
        ('res/audioww/audio_mods.xml', config),
        ('res/audioww/' + BANK_NAME + '.xml', config),
        ('res/audioww/staysharp_VOICE_NOTICE.txt', (ASSETS / 'VOICE_NOTICE.txt').read_bytes()),
    ]
