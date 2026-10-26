# Stay Sharp Medkit Reminder 1.7.0 - installation and test

## Install

1. Close World of Tanks EU completely.
2. Keep a backup of your last working build outside the active mods folder.
3. Remove older `com.staysharp.medkitreminder_*.wotmod` files from the active
   `mods/<current_game_version>/` folder; install only one version.
4. Download `StaySharp-Medkit-v<version>.zip` from GitHub Releases and extract it
   into the folder containing `WorldOfTanks.exe`, preserving the nested paths.
   The installer puts the `.wotmod` in `mods/<game_version>/`; check that its
   target version matches your client. All frames, code and the voice bank are
   bundled. There are no separate DLLs, speech tools or sound downloads.
5. If you already use sound mods, check [audio loading and coexistence](AUDIO.md#loading-and-coexistence-with-other-sound-mods)
   before starting: a shared `audio_mods.xml` needs all installed banks.
6. The optional template is `mods/configs/staysharp.medkit.json.example`; it is
   not loaded. Preserve any existing `.json` when updating. To configure before
   startup, copy the example and remove only its final `.example`. Otherwise,
   start the game normally: the mod creates `mods/configs/staysharp.medkit.json`
   with `{"language":"auto"}` when the directory is writable. To force Polish,
   change `auto` to `pl` and restart WoT. See [all seven languages](AUDIO.md#language-configuration).
7. Installer metadata, checksums, audio instructions and voice attribution are
   included under `docs/staysharp/`. Session Stats is the separate second ZIP;
   its existing installer is carried forward without being rebuilt.

## In-game verification

- Before battle starts and during equipment selection, expect no outline or
  extra audio.
- With the Stay Sharp perk permitting medkit use and the kit available,
  expect the original four-second orange pulse and one **"Medkit is ready"**
  voice after one second, in the selected language. There should be no additional immediate ping on
  top of the game's cooldown-complete sound.
- If you leave the kit ready, expect its normal **activation effect** four
  seconds after the announcement and every four seconds thereafter.
- Check arcade, sniper, SPG top-down and trajectory cameras. Switching camera
  modes must not repeat the voice or reset the reminder interval.
- Use the medkit; the outline and extra sounds must stop during cooldown.
  The next eligible readiness interval should produce one new voice.
- Hide/show the HUD: silence while hidden, no duplicate voice when restored.
- Check an injury/stun warning, perk permission loss, own vehicle destruction,
  battle end and return to the garage. No reminder should continue there.
- Test `language: auto` with your game language, then force another supported
  code in the configuration and restart. Confirm that the spoken language
  changes while timing and the native repeated effect remain the same.
- Change WoT master/voice notification volume and mute; check the voice
  follows the game settings. The repeated native effect follows its existing
  game audio channel. Restore your preferred volume afterward.
- If other sound mods are installed, verify their effects still work too.

Offline checks cannot confirm native bank loading, final voice loudness or
client rendering. If there is no voice, inspect the game's sound errors and
verify the `staysharp_medkit.bnk` loading entry. Keep the previous working
build until the new one has passed an actual battle test.

## Diagnostics and removal

Local log: `%LOCALAPPDATA%\StaySharpMedkit\staysharp.log`.

`ready voice unavailable` or `native medkit reminder unavailable` means an
API call failed and that path was disabled for the battle. Wwise can also
report failures only in `python.log`. `overlay suspended` explains why the
visual and audio reminder paused. Logs remain local and are not uploaded.

To uninstall, remove this mod's `.wotmod`. If you manually merged a bank
entry into a separate audio configuration, remove only the
`staysharp_medkit.bnk` entry, preserving all other sound mods.
