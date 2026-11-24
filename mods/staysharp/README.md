# Stay Sharp — Medkit Reminder for World of Tanks

A small **client-side visual and audio reminder** for the Commander's *Stay Sharp* perk.
When the perk allows using a ready medkit, an orange frame around its original HUD slot smoothly brightens for two seconds and fades for two seconds. The bundled **"Medkit is ready"** voice starts about half a second before a tracked medkit cooldown ends. If the medkit is already ready at battle start, it plays one second after the battle starts. It then repeats every ten seconds while the medkit remains eligible, independently of the continuous outline pulse. Configure separate mod/voice shortcuts from the medkit button immediately to the left of the garage settings gear. Defaults are **Ctrl+Alt+M** and **Ctrl+Alt+V**; recorded three/four-key combinations are saved in the existing configuration. Battle shortcuts also work while movement keys are held, with configured modifiers still required. Press the configured mod shortcut during a battle to turn the entire reminder off or on; it starts enabled in the next battle. Seven spoken languages (`en`, `pl`, `ru`, `fr`, `de`, `es`, `uk`) are selected from WoT or in the [language configuration](docs/AUDIO.md#language-configuration). No automatic consumable use, game-stat changes or injected network traffic.

**Voice credit:** This audio was created with Boson AI's Higgs Audio — https://www.boson.ai/higgs-audio. All seven announcements are AI-generated prerecorded audio; [generation provenance and terms](docs/AUDIO.md#bank-and-volume) are included with the package.

The mod uses the regular consumables HUD and works independently of arcade, sniper and SPG/strategic camera modes. It is packaged as **one `.wotmod`** containing the Python 2.7 game entrypoint, all required DDS frames, its voice soundbank and garage settings UI. The installer also includes the same pinned OpenWG Gameface library used by Session Stats for its native footer button.

The reminder and voice default to enabled, at **70% voice volume**. Use the
game cursor to left-click the power or speaker icon above the medkit and toggle
the reminder or voice for the current battle. Ctrl can show the cursor, but
clicking does not require Ctrl or any other modifier. Icons are visible in arcade and artillery
views and hide in the ordinary sniper view. Configuration defaults are
restored in the next battle.

The mod reads the own vehicle's learned, active-role crew skills before creating
any battle graphics, mouse monitoring or sound. Without Stay Sharp, or while crew
data is unavailable, it remains dormant: no icons, pulse, voice or hotkey/equipment
subscriptions. A cached crew check once per second detects vehicle/crew changes.
The icons use cursor/button polling and never register native GUI input callbacks.

## Downloads

Choose `StaySharp-Medkit-v<version>.zip` in the latest WotMods release. [Latest release](https://github.com/Szwarceneger16/WotMods/releases/latest).

## Installation

1. Close World of Tanks EU.
2. When switching from versioned filenames, remove every older `com.staysharp.medkitreminder_*.wotmod` from the active version folder once.
3. Extract `StaySharp-Medkit-v<version>.zip` into the folder containing `WorldOfTanks.exe`. It installs `mods/<game_version>/GRZ_Medkit_Reminder.wotmod` and the config example. Later updates overwrite that same `.wotmod`; the ZIP name and internal mod metadata retain the version. Check that the target game version matches your client.
4. Start WoT. To uninstall Stay Sharp, remove its `.wotmod` file.

Configurations are optional `mods/configs/*.json.example` files and are not loaded. To customize a supported setting, copy its example and remove only the final `.example`. Keep existing `.json` files when updating. Stay Sharp 1.7.0 uses the language example for its spoken reminder; `auto` follows the client language. Instructions and metadata are under `docs/<mod>/` inside each ZIP.

Optional language configuration: `mods/configs/staysharp.medkit.json`, beside the game-version folders. The mod creates an `auto` default there when possible; see [language selection](docs/AUDIO.md#language-configuration).

The version folder must match your currently installed WoT version. This modification is community-maintained and relies on internal WoT interfaces; **an update to WoT can break it**. The v1.5.0 rendering has been confirmed in a real client; the soundbank, routing/volume, hotkey and audio timing still require an in-game regression test. Back up the last working version before testing an update.

Diagnostic log (created on the player's computer, **never included in releases**): `%LOCALAPPDATA%\StaySharpMedkit\staysharp.log`.

## From source

Packaging and tests use the **Python 3.9+ standard library**. The mod's
entrypoint uses the verified **Python 2.7** bytecode bootstrap.
Run these commands from the repository root.

```sh
python3 -m unittest discover -s mods/staysharp/tests -v
python3 scripts/privacy_audit.py
python3 mods/staysharp/tools/build_wotmod.py
sha256sum mods/staysharp/dist/*.wotmod
```

The `mods/staysharp/assets/medkit_pulse_master.dds.b85` file is a compressed, ASCII-encoded source DDS. The builder recreates **all 21 original DDS animation frames byte-for-byte** using an exact, tested alpha-scaling formula. The **historical v1.6.0** artifact has SHA-256 `9f3d98948ed398c3a4dc14b6785b68f10f1319381f896c6cd49b8709359c4927`. This legacy check applies only when building v1.6.0. Version **1.7.0** added Wwise voice reminders. The builder validates the voice checksum and embeds it as PCM in a deterministic Wwise v150 bank. [Audio packaging and compatibility with other sound mods](docs/AUDIO.md).

See [build and release documentation](../../docs/BUILD_RELEASE.md), [technical notes](../../docs/REVIEW_1.6.0.md), and [installation guide](docs/INSTALACJA.md).
