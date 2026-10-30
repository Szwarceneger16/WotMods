# One WotMods repository: independently built mods, consistent shared Releases

## Scope

Stay Sharp's workflow only builds on changes to its own sources, assets, version,
packaging or workflow. A change in `mods/sessionstats/**` (including languages),
README, or another mod does **not** rebuild Stay Sharp. Each mod has its own
version series, build job, tests and workflow. GitHub has one Releases page and
one repository-wide `/releases/latest` pointer. Each *published* Release is a
complete immutable snapshot containing exactly two user-facing installer ZIPs: `StaySharp-Medkit-v<version>.zip` and `Session-Stats-v<version>.zip`. GitHub supplies source archives and attestations separately.

### Pull-request builds and downloads

Each mod's PR workflow owns its native `pull_request.paths` filter. There is no
central list of mod pairs or special "both mods changed" condition. Every
workflow independently matches the complete PR branch diff against its merge
base, rather than just the latest commit or the presence of a source directory:

| Changes in the PR | Stay Sharp Medkit build | Session Stats build |
| --- | --- | --- |
| Stay Sharp sources, audio, version or installer inputs | Yes | No |
| Session Stats sources, UI, languages, config or build tools | No | Yes |
| Changes in both mods | Yes | Yes |
| Shared packaging, versioning, snapshot or privacy infrastructure | Yes | Yes |

A mod-specific workflow or test change also selects that mod; the shared
`tests/test_pr_ci_scoping.py` regression selects its dependent workflows. Shared
infrastructure selects each workflow that declares it as an input, using the
same independent matching rule. Documentation-only changes
outside installer inputs do not select either build. Each selected workflow
uploads only its own installer ZIP. A PR download does not carry an unchanged
mod from Releases. The two-ZIP carry-forward described below applies only to
published Releases.

Merging main into a medkit-only branch does not make already accepted Session
Stats changes part of that PR's own diff. If a later commit changes Session
Stats on that branch, its workflow starts as well. Session Stats checks run its
own and shared release-infrastructure suites, excluding the medkit builder
tests. `workflow_dispatch` remains an explicit per-workflow manual override.

Use **Validate Stay Sharp Medkit PR** for the medkit download and **Validate
Session Stats PR** for the statistics download. Existing Actions runs remain
in history; changing filters does not delete old artifacts. After merging a CI
filter fix, refresh existing PR branches from main and trigger a new PR check.

To add another mod, create its own PR workflow with an identifying name, its own
source/build/test paths, any shared inputs it actually uses, and its own artifact
path. Existing mod filters do not need a new pairwise condition or a reference
to the new mod. Keep the source trees and artifact paths disjoint, retain
read-only PR permissions and an explicit `workflow_dispatch` override, and add
the new workflow to the scoping regression fixtures.

## Publishing without cross-mod rebuilds

1. Build and test the changed mod **in its own read-only job**. Upload its
   freshly built files with GitHub's first-party `actions/upload-artifact`.
2. The publish job waits for the common mutex used by **every** mod publisher.
   Jobs that are only building do not hold this mutex.
3. **Inside that mutex**, fetch the repository-wide Latest published immutable
   Release, download its two ZIPs and validate each complete internal checksum manifest. For the first migration only, verify the old outer `SHA256SUMS.txt` and convert the legacy assets without recompiling either mod.
4. Compare the *versioned installer* of the updated mod with the one in
   the current Latest. If Latest already contains a **newer** version, skip
   the older job (exit status `75` is explicitly converted into a successful
   no-op). If versions are equal, verify the package bytes match; equal
   versions with different bytes fail closed.
5. Replace only the current mod's old files; copy every other mod's published
   installer **byte-for-byte**, without invoking its builder.
   Use a temporary global manifest for assembly, remove it before uploading, publish a new GitHub Release and
   verify all uploaded bytes while **still holding the mutex**.

### Required mutex across ALL release workflows

```yaml
jobs:
  publish:
    needs: build
    if: github.ref == 'refs/heads/main'
    concurrency:
      group: wotmod-release-${{ github.repository }}
      queue: max
      cancel-in-progress: false
    # ... fetch current Latest, assemble snapshot, publish, verify ...
```

`queue: max` is officially supported in GitHub Actions since May 2026; it
allows up to 100 pending jobs rather than silently replacing an older pending
publication. **Do not** place this shared mutex on the *entire workflow*, or
builds of different mods will be serialized unnecessarily. The group must
cover the entire critical section: latest lookup → carry-forward → upload →
post-upload verification. Every new mod's publisher must use **exactly** the
same group and options. The GitHub queue is FIFO by when each job starts
*waiting*, not necessarily by merge order; the primary-artifact SemVer guard
prevents older builds of the **same** mod from rolling newer ones back.

GitHub queues up to 100 pending jobs, not an unlimited number. Failed jobs
remain visible as failures; successful publication of a different mod cannot
recover a failed build. Do not configure `cancel-in-progress: true`.

### Two fast merges, in either order

Suppose the initial Latest contains A0+B0, merge A builds A1, and merge B
builds B1. The two builds can complete in any order, **but publishing is
serialized**:

- **A publishes first:** A1+B0, then B snapshots that Latest and publishes A1+B1.
- **B publishes first:** A0+B1, then A snapshots that Latest and publishes A1+B1.

The resulting Latest contains both changes without recompiling the unchanged
mod. If an older build A1 reaches publication after a newer A2, it skips
instead of replacing A2 with A1; equal-version mismatches fail safely.

## Adding Session Stats and additional mods

The common helper interface is:

```bash
bash scripts/release_snapshot.sh DIST PRIMARY_FILE PRIMARY_GLOB [OTHER_OWNED_GLOBS...]
```

The read-only build artifacts keep their existing validation layout. The publisher
packages only the changed mod, then invokes the shared helper with an installer
as its versioned primary artifact:

```bash
python3 scripts/release_installers.py package release --source dist --mod staysharp
bash scripts/release_snapshot.sh release \
  "StaySharp-Medkit-v${RELEASE_VERSION}.zip" 'StaySharp-Medkit-v*.zip'
```

For Session Stats use `--source mods/sessionstats/dist --mod sessionstats` and
`"Session-Stats-v${RELEASE_VERSION}.zip" 'Session-Stats-v*.zip'`.
The helper retains support for legacy `.wotmod` callers for offline regression
coverage, but both active publishers use ZIP primaries.

Before publishing, remove the temporary `release/SHA256SUMS.txt` and run
`python3 scripts/release_installers.py verify release`. Exactly one installer
per mod is required. Both must target the same client, include only optional
`.json.example` configs under `mods/configs/`, and have disjoint package IDs and
resource paths. OpenWG is inside Session Stats. Each mod has its own
`docs/<mod>/` directory for instructions, licenses, source where applicable,
build metadata and a full internal checksum manifest. Production `.wotmod`
bytes are preserved. No nested installer ZIP is introduced.

Release notes begin with Downloads and Installation sections, with direct links
to both ZIPs. SHA-256 values appear in a collapsed details block; GitHub's
generated changes follow. The Assets section uploads only `release/*.zip`.
Post-publication checks compare the complete remote asset list and every byte,
validate both installers again, then re-resolve the protected tag.

Existing immutable release assets are left intact. The first successful release
from this workflow introduces the new layout; it does not delete history.

**Merge dependency:** PR #5 is accepted on main. PR #2 integrates that accepted
flow for Session Stats; PR #3 remains stacked on #2. After #2 is accepted,
update #3 onto main and run full source validation with the accepted harness.
The infrastructure-only checkout deliberately skips absent, never-imported
Session Stats sources; it does not establish a passing mod build.

Session Stats requires a separate `sessionstats-release-tags` Ruleset targeting
exactly `refs/tags/sessionstats-v*`, with active update/deletion protection and
no bypass actors or creation block. Its `sessionstats-release` Environment must
supply `SESSIONSTATS_REVIEWED_RULESET_ID` and
`SESSIONSTATS_REVIEWED_RULESET_UPDATED_AT` if GitHub redacts bypass actors.
The publisher checks the exact revision; missing protection blocks publishing.
Creating that owner-managed policy is a deployment prerequisite, not something
this workflow grants to itself.

PR #6 is also accepted on main. Keep its dedicated Stay Sharp tag namespace,
Ruleset, Environment and approval variables when synchronizing either branch.

## Testing and operating limits

`tests/test_release_snapshot.py` checks A→B and B→A snapshot assembly using
two separately prebuilt versions, stale and duplicate version guards, asset
hashes, immutable sources, corrupt/missing manifests and name collisions.
`tests/test_release_scoping.py` checks the shared **publish-job** mutex and
that the stale skip happens before tag/Release creation.

The read/modify/publish process is serialized among cooperating GitHub Actions
jobs, not against a repository administrator manually publishing a release
outside those workflows. Immutable Releases and protected tags limit tampering;
workflow runs should be monitored. A snapshot does not silently repair a
release that failed to build or publish. CI and local tests cannot guarantee
runtime compatibility in the World of Tanks client.

**Required PR check note:** Path-filter-skipped checks may be Pending if
configured as required. Use an always-running required gate rather than
requiring a check that is intentionally skipped for unrelated mods.

## Per-mod namespaces and one shared publication lock

| Mod | New tags | Tag Ruleset | Environment | Revision variables |
|---|---|---|---|---|
| Stay Sharp | `staysharp-v*` | `staysharp-release-tags` | `staysharp-release` | `STAYSHARP_REVIEWED_RULESET_ID`, `STAYSHARP_REVIEWED_RULESET_UPDATED_AT` |
| Session Stats | `sessionstats-v*` | `sessionstats-release-tags` | `sessionstats-release` | `SESSIONSTATS_REVIEWED_RULESET_ID`, `SESSIONSTATS_REVIEWED_RULESET_UPDATED_AT` |

Both Environments allow deployments only from **Branch `main`**. This is
additional to the workflow's own main-ref checks. After the new workflow is
accepted and old publishers are no longer running, retire the old
`wotmod-release-tags` Ruleset and `wotmod-release` Environment. The new
publisher has no fallback to legacy settings and needs no tag aliases.

Separate mod namespaces do not mean separate publication locks. Every publisher
must still use exactly `wotmod-release-${{ github.repository }}`. Concurrency
protection applies to cooperating workflows; manual administrator publication,
queue overflow or failed builds require operator attention and are not repaired
by another mod's successful release.

### Bundled Session Stats translations

Session Stats 0.3.0 and later carry their fixed seven-language catalog inside the
`.wotmod`, with `languages_resource` and `languages_resource_sha256` in BUILD.json.
Their installers include only `grz.sessionstats.json.example` under mods/configs;
the GUI saves the selected language to the corresponding active JSON. The shared
packager verifies the embedded bytes and rejects an external language config in
new-format builds. Previously published installers retain their legacy validation
contract and are carried forward unchanged until that mod is updated.


Session Stats build reports since 0.3.3 record a stable `installed_package` in
BUILD.json. Starting with 0.3.4, its value is `grz_sessions_stats.wotmod`. Both the
raw test ZIP and the production installer use that filename under `mods/<client>/`;
the ZIP filename and internal mod metadata retain the release version. The loose
verified build artifact remains versioned for existing release tooling. Its bytes
are installed unchanged at the stable path, and the inner checksum manifest names
that exact path. Older versioned installers and the preceding 0.3.3
`GRZ_Session_Stats.wotmod` test installer remain supported and carry forward
byte-for-byte. The validator also recognizes the stable `GRZ_Medkit_Reminder.wotmod`
installer from the Medkit branch, so either mod can carry the other forward.

Users must remove old `grz.sessionstats_*.wotmod` and `GRZ_Session_Stats.wotmod`
files once when adopting the final name. Later extractions overwrite
`grz_sessions_stats.wotmod`. Production installers and raw test ZIPs ship only
`.json.example` settings and preserve existing configs.
