# Changelog

## 1.8.10

- Show the native clickable-hand cursor over eligible battle reminder buttons and restore the arrow when leaving or hiding the controls.
- Allow shortcuts while other ordinary keys are held, including movement keys; retain exact modifier requirements, one-shot latches and complete multi-key recording.
- Show Cancel only during shortcut recording while reserving its layout space, keeping the panel and description stationary.

## 1.8.9

- Place Cancel beside the description in a permanently reserved footer row, enabling it only while recording a shortcut.
- Keep the 360×232 panel height stable during capture, cancellation, saves and errors; feedback uses the existing description area.

## 1.8.8

- Center the close cross using symmetric CSS strokes instead of a font glyph.
- Remove the empty idle feedback area and shorten the panel to 232 logical pixels; expand only when capture or feedback needs room.
- Raise the panel above the garage footer with a 24-logical-pixel gap, retaining responsive edge gutters.
- Reduce the garage medkit glyph to 20×19 logical pixels while preserving its existing click area.

## 1.8.7

- Restyle garage shortcut settings with the same bundled camouflage as Session Stats, rounded corners, an inset beveled frame, raised buttons and recessed shortcut fields.
- Place labels above each shortcut and widen clear buttons, retaining explicit native button captions and capture/error feedback.
- Keep a scaled 16-pixel inset on every client edge and uniformly fit the complete panel on smaller windows or larger UI scales, including portrait and ultrawide layouts.

## 1.8.6

- Place the garage medkit icon immediately before the native settings gear and keep the popup above that button.
- Verify and retry native texture sizing after loading so the entire shortcut panel remains visible instead of being clipped by the initial surface.
- Close settings on another icon click or garage focus loss, cancelling unfinished key capture and preserving saved shortcuts.


## 1.8.5

- Remove the settings writer's dependency on ctypes: the embedded WoT client does not provide its native _ctypes module, and importing it during 1.8.4 startup aborted the game loader.
- Use dependency-free, recoverable configuration replacement on embedded Windows Python 2.7, preserving existing settings and recovering an interrupted backup before loading defaults.
- Contain initialization errors inside this mod and make cleanup safe after an incomplete startup. Keep the 1.8.4 smaller icons, garage settings and configurable shortcuts.

## 1.8.4

- Reduce battle power/voice controls from 24 to 16 logical pixels and bake 40 percent transparency into all four icon textures.
- Add a matching medkit button at the far left of the native garage footer, before WG session statistics. Open a small native settings window above that button.
- Record separate mod and voice shortcuts, including three/four-key and larger simultaneous combinations, side-specific modifiers and ordinary keyboard keys. Save on release; Escape cancels recording.
- Persist validated shortcuts atomically in the existing configuration, preserve unrelated settings, reject overlapping bindings and retain active shortcuts if saving fails.
- Keep the working 1.8.3 battle rendering/input path. The new garage interface uses the same pinned OpenWG Gameface dependency already used by Session Stats, without a runtime download.

## 1.8.3

- Remove native GUI input scripts and focus from both status icons after client logs showed `Unregistered type : BW::KeyEvent` immediately before access violations. Read cursor/button state on a bounded timer and defer actions and root detachment outside input dispatch.
- Activate battle graphics, sound and input only for an own vehicle with a learned Stay Sharp skill in an active crew role. Without the skill or a readable crew snapshot, stay dormant with one cached state check per second and release existing mod resources.

## 1.8.2

- Let the game cursor click both status icons with or without Ctrl. Check the actual visible, active cursor instead of requiring a modifier-key state, while retaining HUD, camera and modal-window guards.

## 1.8.1

- Separate the voice reminder interval from the visual pulse: repeat every ten seconds while the pulse continues at its original rate.
- Announce about half a second before a tracked medkit cooldown ends, or one second after battle start when already ready. Preserve the announcement across the READY transition without a duplicate.
- Timestamp native cooldown updates and use server battle time for initial readiness; fall back to actual readiness if no trustworthy cooldown timestamp exists.
- Route clickable status icons through independent native GUI roots with cursor hit testing, ahead of the full-screen Flash battle interface.

## 1.8.0

- Write the Wargaming-compatible Wwise bank header so WoT can read the bundled voice bank.
- Enable the reminder and voice by default, with a configurable voice volume of 70 percent.
- Add separate clickable reminder and voice status icons above the medkit. Keep them in arcade and artillery views and hide them in the regular sniper view.
- Apply HUD and shortcut toggles for the current battle, then restore configured defaults in the next battle.

## 1.7.1

- Repeat the bundled ready voice instead of the native medkit activation sound; do not fall back to that sound on audio errors.
- Add Ctrl+Alt+M to toggle the reminder for the current battle.
- Record bounded diagnostics for audio resource visibility, resolved bank configuration, voice attempts, API results and battle controls.
- Do not treat falsey `play()` returns as errors: the WoT client was observed reporting a falsey result with `isPlaying=True`.
- In-game verification of the voice bank and hotkey is still required.

## 1.7.0

- Install the mod as `GRZ_Medkit_Reminder.wotmod` so updates replace one file; keep the release version in the installer ZIP name and internal mod metadata. Preserve existing immutable installers with the older versioned filenames.
- Add a single bundled ready voice after one second of eligible readiness, using WoT/Wwise only.
- Replace all seven ready announcements with offline-generated Higgs TTS 3 speech, following the owner-auditioned Polish and English delivery. Apply pitch-preserving tempo +7% with FFmpeg atempo, match loudness near -20 LUFS, and package 16 kHz mono PCM under two seconds. Include model/codec revisions, full WAV and PCM hashes, Ukrainian language-context provenance and Boson creator attribution. The mod ships only finished audio.
- Bundle the same seven spoken languages as Session Stats (`en`, `pl`, `ru`, `fr`, `de`, `es`, `uk`) and a small optional `mods/configs/staysharp.medkit.json` language selector, defaulting to the game language. Validate configuration with safe automatic/English fallback.
- Repeat the equipped medkit's native activation effect once per four-second pulse while the reminder remains active.
- Stop audio on use/cooldown, perk loss, native injury/stun warning, HUD suppression, vehicle destruction and battle disposal.
- Keep the announcement latch across temporary HUD hiding and camera changes; skip missed repetitions after a frame stall.
- Add a deterministic PCM Wwise bank builder, verified voice source, native loading descriptor and audio regression tests; document sound-mod coexistence.

## 1.6.1 (first GitHub publication candidate, PR #1 fixes)

- Fix Windows log rotation when the `.old` backup already exists; also rotate logs during long sessions.
- Fail closed on existing mismatched release tags and wrong SHA-256 assets.
- Add checks ensuring a published GitHub Release has complete, correct assets.
- Stop forcing future builds to reproduce the original v1.6.0 checksum.
- Verify the master DDS against its own reviewed SHA-256 file so artwork can be updated in later PRs.
- Add offline regression tests for failed/draft/published release states and Windows log rotation.

## 1.6.0 (historical baseline, not published by this PR)

- Event-based registration/unregistration of the battle consumables panel, without monkeypatching WoT methods.
- Explicit state checks for player vehicle ID and medkit readiness in arcade/sniper/arty views.
- HUD compatibility validation and safe disabling on unknown layout.
- Identical 21 DDS frames with 2-second ramp-up + 2-second fade, no sound.
- Existing offline tests and release-packaging pipeline.

Later releases are generated for **each push to `main`** after a reviewed merge; GitHub Releases contains the corresponding commit-based change notes.

### GitHub Actions release workflow simplification (PR #4)
- Separate read-only build/tests from the write-scoped publishing job with first-party GitHub artifact actions.
- Replace bespoke release REST/HTTP and recovery scripts with Git tags and a single `gh release create --verify-tag`.
- Verify published asset bytes and checksums; never overwrite or automatically delete releases.
- Use native GitHub Immutable Releases protection for future published versions (repository setting).
- Retain the historical empty `v1.6.1` draft for manual inspection; allow next version to publish independently.
