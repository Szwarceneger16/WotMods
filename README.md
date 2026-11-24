# World of Tanks — mods

| Mod | Source and instructions | Releases |
|---|---|---|
| GRZ AimTimer — estimated aiming time | [mods/aimtimer](mods/aimtimer) | `GRZ_AimTimer-v<version>.zip` |
| Session Stats — WN8, XP, finances, session history | [mods/sessionstats](mods/sessionstats) | `Session-Stats-v<version>.zip`, including OpenWG and configuration examples |
| Stay Sharp — Medkit Reminder | [mods/staysharp](mods/staysharp) | `StaySharp-Medkit-v<version>.zip`, including installation paths and a configuration example |
| GRZ Rangefinder — distance readout | [mods/rangefinder](mods/rangefinder) | `GRZ_Rangefinder-v<version>.zip` |

The mods can be installed independently. [Latest shared release snapshot](../../releases/latest). Each mod builds independently; unchanged installers are carried forward byte-for-byte unless the target game directory changes. See [release flow](docs/MULTIMOD_RELEASES.md).
Sources, tests and licenses are separate; the Session Stats license does not cover the medkit mod.
Integration rules: [mods/sessionstats/README.md](mods/sessionstats/README.md).

Each mod directory contains its source, version, build tools and tests. The root
`scripts/` and `tests/` directories contain shared tooling and checks.

## Changes, reviews and releases

1. Submit a PR to `main`. Each mod has its own **read-only, path-filtered PR workflow** and a downloadable, directly installable ZIP artifact. A PR for Stay Sharp does not build Session Stats and vice versa, except when truly shared build infrastructure changes.
2. After review and merge, `wotmods-release.yml` serializes the release transaction. It compares the exact merged source commit with the last immutable Latest Release and builds only changed modules in independent matrix jobs. Unchanged installers are copied byte-for-byte unless the WoT client directory must be retargeted.
3. A single write-scoped publisher assembles and verifies the entire snapshot, creates **one protected `wotmods-v1.0.<release-sequence>` Release**, and independently downloads and checks every published ZIP. Module versions remain separate and increment only when their own module is rebuilt. A client-only update can advance the shared release sequence even without a source commit.

Rapid merges and retries are safe: a later commit includes earlier unshipped changes, obsolete queued runs are skipped, failed builds never publish, and tags/assets are never overwritten. Only the official GitHub CLI and short-lived `GITHUB_TOKEN` are used; PRs cannot publish. Interrupted drafts require manual inspection, not automatic deletion.

See [release architecture and race conditions](docs/MULTIMOD_RELEASES.md), [operator/agent guide](docs/RELEASE_AGENT_GUIDE.md), and [build instructions](docs/BUILD_RELEASE.md).

### Session Stats visual matrix

On an open pull request from this repository that includes the matrix test harness, a maintainer can post a new comment containing only `/sessionstats-matrix` for the full run across all date ranges. Use `/sessionstats-matrix smoke` for a quick report check or `/sessionstats-matrix full` for all sort variants in the primary date ranges. Each command starts a new run with its own status comment and Actions link. The workflow updates that comment during the attempt and adds the report job and HTML download when available. A retry in GitHub Actions publishes a separate status comment and preserves the previous result. Extract the downloaded archive and open `index.html`. The report uses synthetic data and test artwork.

[Release protection and owner re-attestation](docs/BUILD_RELEASE.md#existing-release-protection-and-owner-re-attestation).

## Privacy and safety

No player ID, nickname, account token, email, API key, machine identifier, private path, telemetry collector or crash dump is shipped in source or releases. The build process scans for common secret/PII patterns. This does **not** anonymize commit author/committer names or prior PR/Actions activity. Runtime logging is local-only and is never uploaded by the mod.

As the repository is **public**, the **GitHub account that owns it, commits, PRs, Release authorship, Actions history and logs** will be publicly attributable; this repository cannot conceal its GitHub owner's identity. Do not commit private test logs or screenshots. See [publication checklist](docs/PUBLICATION_PRIVACY.md).

This project is not affiliated with Wargaming. World of Tanks and related marks are the property of their respective owners. No license for redistribution/modification of the source beyond GitHub's platform terms has been chosen yet; the owner can add a `LICENSE` file in a separate reviewed PR.

The former `staysharp-v*` and `sessionstats-v*` release tags remain in the immutable historical archive. New shared releases use the global `wotmods-v*` namespace; filenames and independent mod versions remain unchanged.
