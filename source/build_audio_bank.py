"""Deterministic, single-event Wwise 2023.1 (bank v150) PCM bank.

No authoring tool is needed to rebuild this small subset: one embedded PCM
source, a 2D Sound routed to WoT's VOICE_GUI bus, a Play action and an Event.
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


def load_voice():
    encoded = (ASSETS / 'medkit_ready.wav.b85').read_text(encoding='ascii')
    data = zlib.decompress(base64.b85decode(''.join(encoded.split())))
    expected = (ASSETS / 'medkit_ready.sha256').read_text(encoding='ascii').strip()
    if hashlib.sha256(data).hexdigest() != expected:
        raise ValueError('Ready voice checksum mismatch')
    with wave.open(io.BytesIO(data)) as audio:
        if (audio.getnchannels(), audio.getsampwidth(), audio.getframerate(),
                audio.getcomptype()) != (1, 2, 16000, 'NONE'):
            raise ValueError('Expected mono 16-bit 16 kHz PCM voice')
        if not 0 < audio.getnframes() <= 32000:
            raise ValueError('Ready voice must last at most two seconds')
    return data


def build_bank():
    with wave.open(io.BytesIO(load_voice())) as audio:
        samples = audio.readframes(audio.getnframes())
    # Wwise's 24-byte PCM fmt: cbSize=6, valid bits=16, serialized
    # AkChannelConfig = mono/front-center (mask=4, standard type=1).
    fmt = struct.pack('<HHIIHHHHI', 0xfffe, 1, 16000, 32000, 2, 16, 6, 16, 0x4101)
    body = b'WAVE' + chunk('fmt ', fmt) + chunk('data', samples)
    voice = b'RIFF' + u32(len(body)) + body
    bank_id = short_id(BANK_NAME)
    media_id = short_id(EVENT_NAME + '_pcm')
    sound_id = short_id(EVENT_NAME + '_sound')
    action_id = short_id(EVENT_NAME + '_play')
    # AkBankSourceData: built-in PCM codec, embedded data, one media source.
    source = (u32(0x00010001) + b'\0' + u32(media_id)
              + u32(len(voice)) + b'\x80')
    # NodeBaseParams: no FX/metadata; use existing VOICE_GUI output bus,
    # no actor parent, default priority/properties, 2D speaker panning,
    # no aux/reflections, default virtualization, no states/RTPC curves.
    node = (b'\0\0\0\0' + u32(short_id(BUS_NAME)) + u32(0)
            + b'\0' + b'\0\0' + b'\x01' + b'\0' + u32(0)
            + b'\0\0\0\0\0\0' + b'\0\0' + b'\0\0')
    sound = hirc(2, u32(sound_id) + source + node)
    # Play action (0x0403): target sound, no delay/fade, user bank type 0.
    action = hirc(3, u32(action_id) + struct.pack('<H', 0x0403)
                  + u32(sound_id) + b'\0\0\0\x04' + u32(bank_id) + u32(0))
    event = hirc(4, u32(short_id(EVENT_NAME)) + b'\x01' + u32(action_id))
    header = (u32(BANK_VERSION) + u32(bank_id) + u32(0) + u32(16)
              + u32(0) + u32(0) + bytes(16))
    # Align embedded media to the bank's declared 16-byte boundary.
    prefix = chunk('BKHD', header) + chunk('DIDX', u32(media_id) + u32(0) + u32(len(voice)))
    padding = (-(len(prefix) + 8)) % 16
    if padding:
        header += bytes(padding)
        prefix = chunk('BKHD', header) + chunk('DIDX', u32(media_id) + u32(0) + u32(len(voice)))
    name = BANK_NAME.encode('ascii')
    strings = u32(1) + u32(1) + u32(bank_id) + bytes([len(name)]) + name
    return (prefix + chunk('DATA', voice) + chunk('HIRC', u32(3) + sound + action + event)
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
