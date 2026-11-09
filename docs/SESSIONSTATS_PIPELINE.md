# Session Statistics: independent PR builds and unified releases

Session Statistics lives in `mods/sessionstats/`. Its PR workflow is
`.github/workflows/sessionstats-ci.yml`, separate from Stay Sharp's
`.github/workflows/ci.yml`. It runs for Session Stats or shared infrastructure
changes only; a Medkit-only PR does **not** compile Session Statistics.

## Downloading a PR installer

Open the successful **Validate Session Stats PR** run in GitHub Actions and
download `Session-Stats-v<version>.zip` from **Artifacts**. The validated
installer ZIP is uploaded with `archive: false`, so it is directly installable
without extracting an extra Actions wrapper. PR artifacts expire after 14
days and do not become public GitHub Releases.

The PR job runs CPython 3 and CPython 2.7 logic tests, Chromium UI tests,
reproducibility checks and a full six-asset checksum verification before
uploading only the installer ZIP. Compiler source is CPython 2.7.18 from
python.org, verified against SHA-256
`da3080e3b488f648a3d7a4560ddee895284c3380b11d6de75edb986526b9a814`.
The compilation uses no third-party Python 2.7 packages.

## Production versioning and handoff

Production uses `.github/workflows/wotmods-release.yml`. The read-only
coordinator selects Session Stats for a build only when its own source paths
or shared build inputs changed since the previous published immutable snapshot.
`scripts/release_modules.json` owns the path mapping. The last published Stats
SemVer patch increments by one when changed; a higher reviewed baseline in
`mods/sessionstats/VERSION` can intentionally advance the minor or major number.
An unchanged Stats ZIP is copied byte-for-byte into the next shared Release.

The Stats builder still validates all source artifacts, their checksums and
OpenWG before packaging `Session-Stats-v<version>.zip`. Its production job has
`contents: read`. Only the separate global publisher has `contents: write`,
and it publishes one complete WotMods snapshot (both mods' ZIPs) after all
selected builds pass. No direct Stats publisher, independent tag namespace or
API credential is required for new releases.

See [multi-mod architecture](MULTIMOD_RELEASES.md) and
[maintainer/agent instructions](RELEASE_AGENT_GUIDE.md) for the queue, race
conditions, protected new tag namespace and owner setup.
