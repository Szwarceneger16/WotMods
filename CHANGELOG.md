# Changelog

## 1.7.0

- Add a single bundled ready voice after one second of eligible readiness, using WoT/Wwise only.
- Replace the seven synthetic announcements with offline-generated neural speech: the selected English HFC female voice and five other Piper voices, plus Polish Chatterbox Multilingual V2. Include model provenance, waveform hashes, attribution and the English audio's CC BY-NC-SA 4.0 notice. The mod ships only finished audio.
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
