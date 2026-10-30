# Stay Sharp audio

The mod uses **WoT's Wwise engine for both sounds**, via
`SoundGroups.g_instance.getSound2D(...).play()`. No Windows playback, OS
speech, external process, background thread or runtime download is used.

## Behavior

- Once the existing Stay Sharp eligibility probe reports a usable medkit,
  wait one second, then say **"Medkit is ready" once**. Readiness is sampled
  by the existing 250 ms state tick, so the delay from the game's transition
  can be up to 250 ms longer. The visual stable-ready check also applies.
- Starting four seconds after the announcement, play the equipped medkit's
  **native activation effect** every four seconds, matching the full pulse
  period. The descriptor-to-event mapping comes from WoT's `EquipmentSound`
  class; it is not a cooldown-complete sound or a simulated keypress.
- Pause/stop while the reminder is suppressed. Use/cooldown, losing the
  perk's permission, injury/stun warnings, replay/spectator mode, destruction
  and battle end suppress audio together with the existing outline.
- Hiding/showing the HUD pauses/resumes repetition without another voice
  announcement for the same readiness interval. Readiness is still polled
  while hidden, so using the medkit during that time rearms the next voice.
  Changing arcade/sniper/SPG views does not rearm it.
- A frame stall emits at most one due reminder. There is no catch-up burst.
- If the sound API raises or returns a failure, disable that audio path for
  the battle. Voice failure falls back to the native effect. The outline
  continues. Wwise errors that only appear in the game's own log cannot be
  detected reliably by Python.

## Language configuration

The same seven language codes as Session Stats are supported, with actual
spoken recordings in each language:

| Code | Language | Spoken announcement |
| --- | --- | --- |
| `en` | English | Medkit is ready. |
| `pl` | Polish | Apteczka gotowa. |
| `ru` | Russian | Аптечка готова. |
| `fr` | French | Trousse de soins prête. |
| `de` | German | Das Medikit ist bereit. |
| `es` | Spanish | Botiquín listo. |
| `uk` | Ukrainian | Аптечка готова. |

The optional configuration is `<World_of_Tanks_EU>/mods/configs/staysharp.medkit.json`.
The `configs` folder is beside version folders such as `2.4.1.0`, so the
setting survives game-version folder changes. On first startup the mod
creates the default file there when the installation is identifiable and
writable. Without a readable file it uses the automatic default:

```json
{
  "language": "auto"
}
```

`auto` follows WoT's language using `helpers.getClientLanguage()`. Regional
codes such as `pl-PL` and `fr_FR` are normalized. Unsupported or unavailable
game languages use English. To force Polish, change the value to `"pl"`;
the other codes in the table work the same way. A copyable sample is provided
inside the installer as `mods/configs/staysharp.medkit.json.example` (remove
only `.example` to activate it), and as `staysharp.medkit.example.json` in the repository; copy it to
`mods/configs/staysharp.medkit.json` if you want to prepare the setting before
the first game launch.

**Restart WoT after editing this file.** Configuration is read once at mod
startup, never on animation/state ticks. A missing file is created with
`auto`; an existing file is never replaced. Malformed JSON, non-object
roots, invalid values, read errors and files over 4 KiB use automatic
selection and log a short local diagnostic without echoing file contents.
The installation is identified through WoT's resource resolver and physical
`paths.xml`/`mods` paths, with a bounded application-directory/CWD fallback.
If the installation cannot be identified uniquely, the mod uses automatic
language without writing configuration elsewhere. Existing AppData config
files are not read or migrated. The diagnostic log location is unchanged.
The repeated medkit activation effect remains the native game sound.

## Bank and volume

The package contains `res/audioww/staysharp_medkit.bnk`, with seven events: the existing English `staysharp_medkit_ready` and
`staysharp_medkit_ready_<code>` for the other six languages. Each embedded
mono PCM voice is under two seconds long; only the selected one is played.
The sound routes to the game's existing **VOICE_GUI** bus, inheriting WoT's
master/voice notification volume and mute controls. The native effect keeps
its original game routing. No existing game event, bus or voiceover bank is
replaced. Sound settings and the final loudness must be checked in-game.

`source/build_audio_bank.py` serializes the small Wwise 2023.1 / bank-version
150 subset directly. Rebuilding requires only Python's standard library;
it verifies the original WAV checksum before building Wwise PCM media and
all seven Sound -> Play Action -> Event graphs. IDs use Wwise's lowercase FNV-1.
All seven recordings are **AI-generated neural speech**, created offline
with **Boson AI's Higgs TTS 3 4B**. The Polish and English takes follow the
owner-auditioned delivery; the other five use the same determination and
projected-voice controls. No real-person voice-cloning reference is used.
The generated Ukrainian sentence includes explicit Ukrainian context to
disambiguate the identical Russian/Ukrainian spelling of the target phrase;
only the complete announcement is extracted for packaging.

The source model produces 24 kHz float audio. Post-processing uses
**FFmpeg `atempo=1.07`** for the selected 7% faster tempo while retaining
pitch, followed by constant gain to approximately **-20 LUFS**, subject to
a **-1.5 dBTP** ceiling, and mono 16-bit PCM export at 16 kHz. There is no
intercom filter, ambience, reverb or pitch shift. The earlier time-stretch
method was rejected after a measured change to the selected Polish
recording's low-mid balance. The Wwise builder embeds the finished PCM
samples without another audio encode.

Exact text, model/codec/port revisions, generation parameters, raw waveform
hashes, Ukrainian crop bounds and final WAV/PCM hashes are recorded in
`assets/voices/manifest.json`. The generated-audio credit is prominent in
the README and retained in `assets/VOICE_NOTICE.txt`, which is included in
the soundbank package and installer. The original model's terms are the
[Boson Higgs TTS 3 Research and Non-Commercial License, including its
Creator Use Grant](https://huggingface.co/bosonai/higgs-tts-3-4b/blob/239f63fb7b02b1aa085f98d9efae5e35cc5523e8/LICENSE).
The model license is not an open-source license, and this audio notice does
not relicense the mod's code. No model weights or inference runtime are
shipped by the mod.

Inference ran from pinned local files in a rootless container with networking
disabled. Neither the game nor the package builder requires the generator
or its libraries. Local speech recognition checked each announcement's
wording; it cannot certify native pronunciation or acting. The final
language quality and loudness still require an in-game listening check.

Format and routing references:

- [Wwise bank format parser](https://github.com/bnnm/wwiser/blob/master/wwiser/parser/wparser.py)
- [Wwise PCM format reader](https://github.com/vgmstream/vgmstream/blob/master/src/meta/wwise.c)
- [WoT equipment activation mapping](https://github.com/izeberg/wot-src/blob/EU/sources/res/scripts/client/gui/battle_control/controllers/consumables/equipment_ctrl.py)
- [WoT SoundGroups API](https://github.com/izeberg/wot-src/blob/EU/sources/res/scripts/client/SoundGroups.py)
- [WoT Wwise mixer reference](https://github.com/Supergrefu/9.13-Wot-gun-sounds-for-wot/tree/main/Master-Mixer%20Hierarchy)

## Loading and coexistence with other sound mods

For a normal installation, the bundled `res/audioww/audio_mods.xml` asks
WoT to load the custom bank. It contains only a `loadBanks` entry and no
event remapping. A namespaced `staysharp_medkit.xml` descriptor is also
provided for existing **BanksLoader** installations to discover/merge.
BanksLoader is not required on an otherwise unmodified client.

**`audio_mods.xml` is a shared WoT resource.** If another sound mod or a
loose file already supplies it, the game's resource precedence may select
that file instead of this package's descriptor, or vice versa. Merely
placing several versions of that XML in separate packages does not merge
them. With an existing sound configuration, preserve all its entries and
add this bank under its `loadBanks` element:

```xml
<bank><name>staysharp_medkit.bnk</name></bank>
```

Alternatively use your existing BanksLoader to merge the namespaced bank
descriptor. The mod does not rewrite your global audio configuration,
install another loader, request a restart or delete another mod's entries.
After changing audio loading configuration, fully restart WoT.

## Verification and limits

Offline tests cover announcement timing, repetition, cancellation, camera
and HUD transitions, failed audio calls, package resources, PCM content,
IDs and bank references. The existing bank layout was previously parsed
independently with **wwiser v20260808**, with all 21 HIRC objects consumed
and no parse errors. This recording refresh keeps the same bank builder;
current packaging tests compare every embedded PCM payload to its source
and provenance checksums. These checks do not prove native engine loading
or audible output.
There is no WoT client in the build environment: perform the in-game checks
in [the installation guide](INSTALACJA.md) before calling this version
confirmed stable. A future Wwise upgrade may require updating the bank
format; Python/API and visual compatibility are separate concerns.
