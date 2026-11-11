# World of Tanks — mods

| Mod | Source and instructions | Releases |
|---|---|---|
| Session Stats — WN8, XP, finances, session history | [mods/sessionstats](mods/sessionstats) | `Session-Stats-v<version>.zip`, including OpenWG and configuration examples |
| Stay Sharp — Medkit Reminder | [source](source), description below | `StaySharp-Medkit-v<version>.zip`, including installation paths and a configuration example |
| Hangar Sync — opt-in garage, crew and mission snapshots | [mods/hangarsync](mods/hangarsync) | Shared Release: `GRZ_Hangar_Sync-v<version>.zip`, including installation paths and a disabled configuration example |

Each mod can be installed independently. All three use the [latest shared release snapshot](../../releases/latest), carrying unchanged installers forward byte-for-byte unless the target game directory changes. See [release flow](docs/MULTIMOD_RELEASES.md). Hangar Sync validates PR candidates without uploading executable packages. After reviewed changes reach `main`, the single **Publish WotMods snapshot** transaction tests, builds, audits and publishes its installer with the other registered mods. Its final Actions summary contains verified Release download links. Green PR checks do not establish trust in an installer; older installer-named PR artifacts are review evidence, not installation downloads.
Sources and tests are separate; the Session Stats license applies only to its module.
Integration rules: [mods/sessionstats/README.md](mods/sessionstats/README.md).

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

**[Latest release](../../releases/latest)** — choose `StaySharp-Medkit-v<version>.zip`, `Session-Stats-v<version>.zip`, or `GRZ_Hangar_Sync-v<version>.zip`. Each release offers all registered installers; GitHub also adds source archives and release attestations. The Downloads section links directly to the installer ZIPs.

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

Requirements: **Python 3.9+** for packaging/tests, no third-party Python libraries. The mod's embedded runtime remains **Python 2.7**, generated by the existing, verified bytecode bootstrap.

```sh
python3 -m unittest discover -s tests -v
python3 scripts/privacy_audit.py
python3 source/build_wotmod.py
sha256sum dist/*.wotmod
```

The `assets/medkit_pulse_master.dds.b85` file is a compressed, ASCII-encoded source DDS. The builder recreates **all 21 original DDS animation frames byte-for-byte** using an exact, tested alpha-scaling formula; the full assets do not need to be separately committed. The **historical v1.6.0** artifact has SHA-256 `9f3d98948ed398c3a4dc14b6785b68f10f1319381f896c6cd49b8709359c4927`. This legacy check applies only when building v1.6.0. Current code starts at **v1.7.0**, which adds Wwise voice reminders. The builder validates the voice checksum and embeds it as PCM in a deterministic Wwise v150 bank. See [audio packaging and compatibility](docs/AUDIO.md), including coexistence with other sound mods.

See [build and release documentation](docs/BUILD_RELEASE.md), [technical notes](docs/REVIEW_1.6.0.md), and [installation guide](docs/INSTALACJA.md).

## Changes, reviews and releases

1. Submit a PR to `main`. Each mod has its own **read-only, path-filtered PR workflow**. Stay Sharp and Session Stats provide candidate ZIP artifacts; Hangar candidates are tested and audited without uploading an installer. Mod-specific source changes do not cross-build other mods; shared infrastructure changes validate the affected modules.
2. After review and merge, `wotmods-release.yml` serializes the release transaction. It compares the exact merged source commit with the last immutable Latest Release and builds only changed modules in independent matrix jobs. Unchanged installers are copied byte-for-byte unless the WoT client directory must be retargeted.
3. A single write-scoped publisher assembles and verifies the entire snapshot, creates **one protected `wotmods-v1.0.<release-sequence>` Release**, and independently downloads and checks every published ZIP. Module versions remain separate and increment only when their own module is rebuilt. A client-only update can advance the shared release sequence even without a source commit.

Rapid merges and retries are safe: a later commit includes earlier unshipped changes, obsolete queued runs are skipped, failed builds never publish, and tags/assets are never overwritten. Only the official GitHub CLI and short-lived `GITHUB_TOKEN` are used; PRs cannot publish. Interrupted drafts require manual inspection, not automatic deletion.

See [release architecture and race conditions](docs/MULTIMOD_RELEASES.md), [operator/agent guide](docs/RELEASE_AGENT_GUIDE.md), and [build instructions](docs/BUILD_RELEASE.md).

The existing `wotmods-release-tags` Ruleset and reviewed `wotmods-release` Environment remain unchanged. Missing or stale protection evidence blocks publication. Historical releases and their tag protections remain untouched.

## Privacy and safety

No player ID, nickname, account token, email, API key, machine identifier, private path, telemetry collector or crash dump is shipped in source or releases. The build process scans for common secret/PII patterns. This does **not** anonymize commit author/committer names or prior PR/Actions activity. Runtime logging is local-only and is never uploaded by the mod.

As the repository is **public**, the **GitHub account that owns it, commits, PRs, Release authorship, Actions history and logs** will be publicly attributable; this repository cannot conceal its GitHub owner's identity. Do not commit private test logs or screenshots. See [publication checklist](docs/PUBLICATION_PRIVACY.md).

This project is not affiliated with Wargaming. World of Tanks and related marks are the property of their respective owners. No license for redistribution/modification of the source beyond GitHub's platform terms has been chosen yet; the owner can add a `LICENSE` file in a separate reviewed PR.

The former `staysharp-v*` and `sessionstats-v*` release tags remain in the immutable historical archive. New shared releases use the global `wotmods-v*` namespace; filenames and independent mod versions remain unchanged.
