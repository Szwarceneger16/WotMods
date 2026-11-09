# Independent mod builds, one immutable WotMods Release

WotMods uses independent per-mod PR checks and production builds, but one
repository-wide published snapshot. The current Release contains one
installable ZIP per supported mod; unchanged ZIPs are carried **byte-for-byte**
unless the game's installation directory changed. Each mod has its own SemVer
and source-specific build trigger. The overall Release has a separate global
`wotmods-v1.0.<release-sequence>` tag. The first release seeds the sequence
from the migration commit count; each later publication increments it, even
when only the target World of Tanks client changes without a Git commit.

## Responsibilities

- **Pull requests:** `.github/workflows/ci.yml` validates Stay Sharp;
  `.github/workflows/sessionstats-ci.yml` validates Session Statistics. They
  have separate native path filters, `contents: read`, directly downloadable
  ZIP artifacts (14-day retention) and no public Releases. Future mods get a
  new independent PR workflow.
- **Module selection:** `scripts/release_modules.json` enumerates exactly
  which sources belong to each module and which shared paths affect them all.
  Changes to only one mod do not invoke the other builder.
- **Builds:** `.github/workflows/wotmods-release.yml` generates a dynamic
  matrix; `scripts/build_release_module.sh` runs a builder for one module in
  a read-only job. Both builders run concurrently when both are needed.
- **Adding a module:** the coordinator reads the previous Release's historical
  registry, so a legitimate older two-installer snapshot can be migrated to
  a newer three-installer snapshot. The final new Release must still contain
  exactly one verified ZIP for every currently registered mod.
- **Publishing:** the sole write-enabled `publish` job assembles a complete
  immutable snapshot, creates exactly one protected Release, and verifies the
  full remote file set and checksum contents before reporting success.

## Sequencing and race safety

The **entire** production workflow shares the previous release mutex
`wotmod-release-${{ github.repository }}` (`queue: max`,
`cancel-in-progress: false`). This deliberately serializes production release
runs, while keeping the matrix builds of different modules parallel inside
each run and leaving PR jobs independent. Holding the mutex only during the
publish step would permit a later commit to produce a stale build plan before
an earlier commit finishes; the new coordinator avoids that.

Planning starts from the last verified immutable Latest tag and the **exact
accepted push SHA**, not the moving branch head. It diffs their entire Git
range. If the newer B merge is scheduled before A, it also contains A's yet
unreleased changes, so the chosen matrix builds both. The older A run later
detects that its SHA is already an ancestor of Latest and does nothing. If A
publishes first, B carries A's verified ZIP and builds only its own change.
The latest per-module versions can never decrease.

If a build fails, nothing is published. A rerun of that commit retries all
missing modules; a later merge also covers any unreleased changes since the
last successful snapshot. Distinct mod builds must all succeed before the
publisher starts. A client-only change can repack the verified installers
without recompiling mod binaries; this does **not** prove in-game compatibility.

An interrupted draft is a manual recovery incident. No workflow deletes
published releases, moves tags, overwrites published ZIPs or guesses how to
fix an incomplete upload. All tags are protected during GitHub CLI's
multi-request draft/upload/publish sequence.

See [the full maintainer/agent contract](RELEASE_AGENT_GUIDE.md) for the
decision table, extending the registry, trust boundaries, owner tag protection
and test checklist. See [build and installation details](BUILD_RELEASE.md).
