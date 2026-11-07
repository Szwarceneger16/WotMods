# World of Tanks EU update monitoring

`Check World of Tanks EU updates` is a shared preflight of both PR builds and both production publishers. It reads `.wot-update-cache/state.json` through GitHub Actions cache. A successful fetch remains fresh for **24 elapsed hours**, irrespective of calendar date. Cache keys are immutable per run; restore selects the newest entry with the schema and parser-revision prefix. Only the small preflight is serialized. Branch/PR caches remain isolated from the default branch's production cache by GitHub's cache scoping rules.

`Refresh World of Tanks EU at 06:00` runs daily at **06:00 Europe/Warsaw**, including DST changes. That scheduled run forces a refresh so an incidental build shortly before 06:00 does not hide the morning update. Therefore a scheduled refresh can occur less than 24 hours after an earlier build fetch. GitHub may delay scheduled jobs. Manual runs use the normal TTL. Workflows become active after merging to main.

## Sources and HTTP 403

- Official update RSS: https://worldoftanks.eu/pl/rss/news/updates/
- Official fallback feeds: https://worldoftanks.eu/en/rss/news/updates/ and https://worldoftanks.eu/pl/rss/news/ (filtered to update articles).
- Example patch notes: https://worldoftanks.eu/pl/news/updates/micro-patch-2-4-1-3/
- Official client updater: `https://wgus-woteu.wargaming.net`, application **WOT.EU.PRODUCTION**.

The client identifies itself with an explicit WotMods User-Agent and requests XML. These headers were checked against the RSS and patch-note page on a GitHub-hosted runner (HTTP 200). No browser cookies, credentials, proxy bypass or anti-bot challenge solver is used. HTTP errors and HTML challenge pages (including HTTP 200 challenges) are rejected. The checker tries the official English update feed and general Polish RSS before marking patch notes unavailable. SteamDB is not a runtime dependency.

The updater follows only the production **install** chain and walks its connected client patches. It reads actual `mods/<four-component-version>/readme.txt` entries from the latest applicable archive headers. It does not use RSS titles, micropatch suffixes, launcher build numbers, common tests or preload chains to construct a directory. Sparse temporary files hold only the first 64 KiB and last 2 MiB of selected archive volumes. `7z l` reads their directory metadata; no client files or remote code are extracted/executed. Once this evidence is verified, the checker attempts to retain the RSS and up to three matching article pages alongside the exact client build, archive URLs and last successful fetch timestamp.

An article response whose title does not match RSS is marked unavailable, rather than treating an HTML challenge as patch notes. RSS and article failures are listed separately in the summary. Freshness and the release gate depend on the verified EU production install chain and the actual archive directory.

RSS articles can announce a future release or common test. They are news evidence only. The live production install chain supplies the directory.

## Failure behavior

A failed Game Center refresh retains the last-good data and its successful timestamp; it does not extend the TTL. A 15-minute failed-attempt backoff prevents repeated build requests from hammering an unavailable source. Failed evidence blocks production, including a forced refresh failure while an older cache entry is still under 24 hours old. PR builds report source failure as a warning and can still validate code. Every job summary reports Game Center freshness and links any available recent official announcements.

## Rebuild and publication

The morning watcher downloads **both** installers from the latest immutable production Release, checks their GitHub SHA-256 digests and internal/cross-mod manifests, and compares their directories with the checked EU directory. If both match, it does nothing. It refuses to downgrade newer installers. For a new directory it dispatches the two existing publishers on accepted main, skipping a publisher already queued/running/waiting. A dispatch is not a publication claim.

Each publisher receives a fresh checked directory, builds using it, and passes the same directory to its protected snapshot/publish job. Session Stats passes it through both reproducibility builds; Stay Sharp passes it to installer packaging. The publisher carries the counterpart installer forward under the checked directory using the retargeting changes from **PR #14**, included in this branch. After queue and approval delays, the protected job rechecks the original evidence timestamp before any tag write and again before creating the Release. If it has expired, start a new release run to check the target and rebuild. Publication retains the shared lock, immutable releases, monotonic mod versions, protected tag checks, exact ruleset revision approvals and post-publication byte verification. A normal merged source change also checks the cache before building.

Mod runtime compatibility is limited to automated repository/packaging tests; this workflow does not run World of Tanks or claim in-game testing. Patch notes are retained for diagnosis. A test failure blocks publication and requires a source fix/review.
