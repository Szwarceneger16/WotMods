# Stay Sharp Medkit Reminder 1.7.1 - installation and test

## Install

1. Close World of Tanks EU completely.
2. Keep a backup of your last working build outside the active mods folder.
3. When switching from versioned filenames, remove older
   `com.staysharp.medkitreminder_*.wotmod` files from the active
   `mods/<current_game_version>/` folder once; install only one version.
4. Download `StaySharp-Medkit-v<version>.zip` from GitHub Releases and extract it
   into the folder containing `WorldOfTanks.exe`, preserving the nested paths.
   The installer puts `GRZ_Medkit_Reminder.wotmod` in `mods/<game_version>/`;
   future updates overwrite that same filename. The ZIP and internal mod
   metadata keep the release version. Check that the target game version
   matches your client. All frames, code and the voice bank are
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
- With the perk permitting use and the medkit ready, expect the orange pulse
  and the selected voice after one second, repeated every four seconds.
  There must be no native medkit activation effect from this mod.
- Press Ctrl+Alt+M to turn the outline and voice off, then press it again to
  restore them. The reminder starts enabled in the next battle. Verify the
  shortcut does not react while battle chat is focused.
- Check arcade, sniper and artillery cameras, cooldown, HUD visibility,
  warnings, destruction and battle end. The reminder must stop when ineligible.
- Test automatic and manually selected languages and WoT voice volume.
- If other sound mods are installed, verify that their effects still work.

Offline checks cannot confirm native bank loading, final voice loudness or
client rendering. If there is no voice, inspect the game's sound errors and
verify the `staysharp_medkit.bnk` loading entry. Keep the previous working
build until the new one has passed an actual battle test.

## Diagnostics and removal

Local log: `%LOCALAPPDATA%\StaySharpMedkit\staysharp.log`.

The log records the mod version, selected voice event, readiness transitions,
whether the game resource manager can see the bank, whether the resolved
`audio_mods.xml` mentions it, playback attempts and their API results, and the
battle hotkey. It does not list other mods from the audio configuration.
Playback attempts are sampled after the first three; counts are also recorded
at battle end. Logs are local, rotate at roughly 512 KiB, and are not uploaded.
If rotation occurs, include `staysharp.log.old` as well.

`bank_visible=True` and `bank_entry=yes` do not prove that Wwise loaded the
bank. `result=none` or `result=truthy` means only that no failure was reported
by the Python call; `audible=unknown` is intentional. `ready voice unavailable`
means the API reported an error and audio was disabled for that battle.
Wwise may report additional failures only in the game's `python.log`.
`overlay suspended` explains why the reminder paused. The game's `python.log`
may contain information from WoT and other mods; review it before sharing.

To uninstall, remove this mod's `.wotmod`. If you manually merged a bank
entry into a separate audio configuration, remove only the
`staysharp_medkit.bnk` entry, preserving all other sound mods.
