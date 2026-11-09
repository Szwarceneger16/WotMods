# Build, installation and publication instructions

## Local Stay Sharp build

- The game entrypoint is `source/mod_staysharp_medkit.py` (CPython 2.7).
- Python 3 standard-library tools produce the deterministic `.wotmod`.
- The animation master and seven voice files have pinned checksums; the
  Wwise v150 bank is assembled from reviewed source assets. See [Audio](AUDIO.md).

```sh
python3 scripts/privacy_audit.py
python3 -m unittest discover -s tests -v
python3 source/build_wotmod.py
(cd dist && sha256sum -- *.wotmod > SHA256SUMS.txt && sha256sum --check SHA256SUMS.txt)
python3 scripts/release_installers.py package release-local --source dist --mod staysharp
```

`StaySharp-Medkit-v<version>.zip` extracts into the folder containing
`WorldOfTanks.exe` and installs the fixed
`mods/<client_version>/GRZ_Medkit_Reminder.wotmod` file. The version is in
the ZIP name and the internal mod metadata, not the installed filename. The
configuration example remains inactive until the user copies the `.json.example`
file to the corresponding `.json` filename. Existing settings are preserved.

## Session Statistics PR builds

`Validate Session Stats PR` compiles verified CPython 2.7.18, runs Python 3
and 2.7 logic tests, browser/UI suites, privacy tests and reproducibility
checks. It uploads the **existing installer ZIP** with `archive: false`:

`wot-statystyki-sesji-v<version>.zip`

The download is not double-zipped and does not create a public Release. The
production packaging step independently verifies all built source assets,
then produces `Session-Stats-v<version>.zip` with the installed file
`grz_sessions_stats.wotmod`, OpenWG and configuration examples. See
[Session Statistics source](../mods/sessionstats/README.md).

## Production flow

The only publisher is `.github/workflows/wotmods-release.yml`:

1. Accepted `main` push or explicit dispatch; exact `github.sha` pinned.
2. Global queue acquired **before** reading the old Latest.
3. Last immutable Release downloaded and verified, including the internal
   SHA-256 manifests and cross-mod resource conflicts.
4. Paths since that Release select only changed modules; the module baseline
   `VERSION` is a lower bound for the next independent SemVer, while unchanged
   packages retain their existing versions.
5. Separate read-only matrix builds generate only the needed ZIPs. All must
   pass tests and verification before any write-enabled job begins.
6. The publisher carries unchanged ZIPs, verifies the complete new snapshot,
   checks the reviewed native tag Ruleset, creates a single immutable global
   Release, and re-downloads every published ZIP to compare exact bytes.

The Release downloads table is intentionally short. Full installation guidance
is here, and the generated changelog compares the new global tag with the
**previous repository-wide Latest tag** using `--notes-start-tag`. A mod-only
PR must not pull the other module's unrelated commits into its changelog.

The release tag format is `wotmods-v1.0.<commit-count>`. This is separate
from the two installers' own SemVer. Legacy `staysharp-v*`, `sessionstats-v*`,
and older `v*` tags remain preserved in history; published artifacts are not
mutated or deleted.

## Owner prerequisite before merging the workflow migration

The repository already uses Immutable Releases and legacy protected tags.
Before the unified workflow is accepted, the owner must create a **new**
native tag Ruleset:

- Name `wotmods-release-tags`, Active, target exactly
  `refs/tags/wotmods-v*`, no exclusions or bypass actors.
- Restrict tag **updates** and **deletions**; do not restrict creations.
- Create GitHub Environment `wotmods-release`, allow only branch `main`.
- Verify the Ruleset with owner privileges and set its exact ID and `updated_at`
  in the non-secret Environment variables `WOTMODS_REVIEWED_RULESET_ID` and
  `WOTMODS_REVIEWED_RULESET_UPDATED_AT`.

The workflow fails closed if the Ruleset is absent, was modified since
review, allows bypasses, or has the wrong tag pattern. Do not create a PAT,
custom publisher, unaudited third-party action or broad tag exemption.
Keep the old tag Rulesets for legacy release provenance.

See [RELEASE_AGENT_GUIDE.md](RELEASE_AGENT_GUIDE.md) for exact owner CLI
commands, failure-recovery steps and the complete concurrency test matrix.

## Limitations

CI can check bytecode, packages, reproducibility, integrity and privacy but
cannot prove the mod runs correctly inside a particular World of Tanks client.
Do a real in-game test before describing a release as runtime-confirmed.
Immutable Release creation has a non-atomic draft → upload → publish phase;
interrupted drafts must be inspected manually. The pipeline never deletes them.
