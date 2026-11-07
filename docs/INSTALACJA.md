# Stay Sharp Medkit Reminder 1.8.5 - installation and test

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
   with automatic language, reminder and voice enabled, and 70 percent voice
   volume when the directory is writable. A previous language-only configuration
   uses these same defaults. To force Polish,
   change `auto` to `pl` and restart WoT. See [all seven languages](AUDIO.md#language-configuration).
7. Installer metadata, checksums, audio instructions and voice attribution are
   included under `docs/staysharp/`. Session Stats is the separate second ZIP;
   its existing installer is carried forward without being rebuilt.

## Garage shortcuts

The medkit button is the leftmost button in the garage footer, before the native WG session statistics button. Its muted grey/beige icon matches the surrounding buttons. Click it to open a small settings window above the button. The installer includes the unchanged, checksum-verified OpenWG Gameface dependency used by Session Stats; both mods share the same dependency path.

Select either shortcut row, hold the desired keys together, then release every key to save. The two actions toggle the whole reminder or toggle voice independently. Defaults are Ctrl+Alt+M and Ctrl+Alt+V. Use Clear to disable a shortcut; Escape or Cancel abandons a recording. Left/right modifiers are preserved when recording. The configuration also accepts generic CTRL, ALT and SHIFT names for either side.

Three/four-key combinations and larger simultaneous combinations are supported, including multiple ordinary keys. The client can only record keys delivered by the OS and keyboard hardware: system-reserved shortcuts such as Ctrl+Alt+Delete and keyboard rollover limits cannot be overridden by this mod. Escape is reserved for cancelling the recorder. Overlapping action bindings are rejected to avoid firing a shorter action while entering a longer one.

Settings are saved immediately without requiring native Python extension modules to `mods/configs/staysharp.medkit.json` and are loaded again when the window opens and at the next game startup. Existing language, volume, defaults and unrelated configuration fields are preserved. Failed saves retain the previous active binding and show an error. On embedded Windows Python 2.7, complete temporary and backup files allow recovery after interruption; this fallback is recoverable rather than a single atomic replacement. The previous configuration is recovered before defaults can be created. Recording does not trigger either reminder action and stops when the window closes, loses focus or battle starts. Ordinary battle shortcuts remain inactive on a vehicle without the learned perk, and while chat or a battle modal is active.

Battle power/voice icons are 16 logical pixels (previously 24) with 40 percent transparency. Their existing plain-click/Ctrl-click behavior is retained. Their battle toggles remain temporary; the next battle restores configured enabled/voice defaults.

## In-game verification

- On a vehicle without a learned Stay Sharp perk, expect no mod icons, outline,
  voice or active mouse monitoring. Repeat with missing crew data: it stays dormant.
- On artillery with the perk, repeatedly switch views using the minimap right
  mouse button and the normal view controls, including while the medkit is cooling
  down. Verify both regular and trajectory artillery views and leaving/rejoining
  battle. The icons must accept left clicks without native GUI input callbacks.

- Before battle starts and during equipment selection, expect no outline or
  extra audio.
- With the perk permitting use and the medkit ready, expect the orange pulse
  continuously. With a medkit ready at battle start, expect the selected voice
  one second after the battle starts, then every ten seconds while eligible.
- Use the medkit and check the next cooldown: the voice starts about half a
  second before it ends; the outline resumes only after actual readiness.
  There must be no second announcement when the countdown reaches zero.
  There must be no native medkit activation effect from this mod.
- Press the configured whole-mod shortcut (default Ctrl+Alt+M) to turn the outline and voice off, then press it again to
  restore them. The voice shortcut defaults to Ctrl+Alt+V. Show the game cursor (normally with Ctrl) and left-click the
  power or speaker icon above the medkit to toggle the reminder or voice
  separately. Clicking works both with and without Ctrl when the cursor is
  visible and active; no modifier state needs to reach the mod.
  The next battle restores the configured defaults. Verify the
  shortcut does not react while battle chat is focused.
- Verify both icons appear in arcade and artillery views. The normal tank
  sniper view hides the icons. The speaker switch can mute the voice while
  the medkit outline keeps pulsing.
- Check arcade, sniper and artillery cameras, cooldown, HUD visibility,
  warnings, destruction and battle end. The reminder must stop when ineligible.
- Test automatic and manually selected languages and WoT voice volume.
- Check the local log shows `settings enabled=True voice_enabled=True voice_volume=70`
  for a default configuration and `audio voice volume=70` when the voice is created.
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
bank. The meaning of `play()` return values is not established, so the mod
logs them without treating falsey values as failures. `isPlaying=True` and
`audible=unknown` do not prove that the player can hear the voice.
`ready voice unavailable` means the Python API raised an exception and audio
was disabled for that battle.
Wwise may report additional failures only in the game's `python.log`.
`overlay suspended` explains why the reminder paused. The game's `python.log`
may contain information from WoT and other mods; review it before sharing.

To uninstall, remove this mod's `.wotmod`. If you manually merged a bank
entry into a separate audio configuration, remove only the
`staysharp_medkit.bnk` entry, preserving all other sound mods.
