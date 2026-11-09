# WotMods release architecture — maintainer and agent instructions

This is the operational contract for future release changes. Follow it when
working on CI, adding a mod, responding to a review, or recovering a failed
publication. **Do not publish from a pull request or bypass tag protection.**

## 1. Separation of responsibilities

| Phase | Entry point | Permissions | Output |
| --- | --- | --- | --- |
| Stay Sharp PR validation | `.github/workflows/ci.yml` | `contents: read` | Its own installable ZIP as a PR artifact |
| Session Stats PR validation | `.github/workflows/sessionstats-ci.yml` | `contents: read` | Its own installable ZIP as a PR artifact |
| Release planning | `wotmods-release.yml` / `release_coordinator.py` | `contents: read` | A versioned plan and selected module matrix |
| Module release builds | `wotmods-release.yml` / `build_release_module.sh` | `contents: read` | One verified installer ZIP per changed module |
| Release publishing | `wotmods-release.yml` / `release_coordinator.py assemble` | `contents: write`, protected Environment | **One** complete immutable GitHub Release |

The PR workflows are intentionally independent. A source-only PR for one mod
must never run the other mod's build. Tests and changes to shared packaging,
privacy checks, or release infrastructure can legitimately select both. PR ZIPs
are retained for 14 days and are never GitHub Releases; `archive: false` avoids
double-wrapping the installer.

The production registry is `scripts/release_modules.json`. Its module source
paths decide which builders run. The corresponding safe packagers and verifiers
are in `scripts/release_installers.py`; the per-module build entry point is
`scripts/build_release_module.sh`. No module is silently discovered from an
unverified or unspecified directory.

## 2. One locked transaction per accepted merge

`Publish WotMods snapshot` runs on relevant `main` pushes or an explicit manual
dispatch. Its **workflow-level** concurrency group is the unchanged
`wotmod-release-${{ github.repository }}` with `queue: max` and
`cancel-in-progress: false`. The lock starts **before** reading Latest and is
held throughout planning, independent matrix builds, upload and remote asset
verification. Builds for selected modules within a single run can execute
concurrently; builds from different release runs wait in the queue. This is a
deliberate throughput trade-off for a straightforward, serializable transaction.

The `main` push filter covers only the registered module build inputs and
shared sources that can affect distribution packages. Workflow-only maintenance,
release coordinator/ruleset logic, update-dispatch logic and unrelated docs do
not start a no-op production workflow. Their changes are tested by the relevant
PR CI jobs; a maintainer can explicitly use `workflow_dispatch` for a live
planning check (publication still requires unreleased changes). When adding
build inputs or a new module, update **both** `scripts/release_modules.json`
and the production `push.paths` filter. The registry coverage test ensures
none of the registered sources can silently miss a production run.

The source commit is the immutable `github.sha` associated with the accepted
workflow invocation. Do **not** check out a moving `main` after selecting a
workflow version: it could run a different CI harness against newer source.

1. Read the current repository-wide Latest published full Release and verify
   `isImmutable`; fail if Releases exist but none is marked Latest.
2. Download its assets and verify every current installer and cross-mod package
   ID/resource collision. Resolve the tag to its exact Git commit. For a
   newly added mod, verify the previous snapshot against the module registry
   stored **at that older tag**, so a valid two-mod snapshot is not mistaken
   for a broken three-mod snapshot.
3. Compare the tag commit to the source commit. Require ancestry, or skip if
   Latest already contains a strictly newer descendant commit. Divergence or
   history rewrites fail closed.
4. Diff **all** source changes since the last published tag, not just the last
   push's changed-file list or individual PR. Disable Git rename detection so
   a cross-mod move selects both the removed source and new destination.
   Select each affected mod using
   the registry. A previously failed build is therefore retried automatically
   by a later accepted merge affecting the same source lineage.
5. Allocate independent SemVer for each changed mod: maximum of its reviewed
   `VERSION` baseline and the last published mod's patch + 1. Never increment
   the version of a carried-forward binary. A requested minor/major jump is
   respected if that baseline is higher.
6. Run only selected builders and verify their ZIP content/checksums with
   read-only tokens. A failure in **any** selected builder blocks publication.
7. The publisher re-reads Latest, checks that it has not changed outside the
   transaction, downloads and validates the previous immutable snapshot,
   replaces only rebuilt modules, retargets installation paths only if the WoT
   client version changed, and verifies the whole final set.
8. Verify exact tag Ruleset revision **before** creating a tag. Use
   `wotmods-v1.0.<release-sequence>` pointing to the pinned source commit. Seed
   the first global number from the migration commit count and then increment
   per published Release, even when a WoT client update uses the same SHA. Reject
   any existing conflicting tag or draft. Use native `gh release create
   --verify-tag --latest` and explicitly start generated notes at the previous
   shared Release tag, never at an arbitrary other-mod tag.
9. Re-resolve the remote tag, download the just-published Release, compare the
   entire asset name set and every byte against the validated local ZIPs, and
   run the cross-mod verifier again. Do not declare success before this check.

The release tag identifies the repository snapshot. Individual ZIP filenames
and internal metadata continue to use each mod's own SemVer. A current Release
contains one ZIP per registered mod, even when only one mod changed.

## 3. Race and failure matrix

| Event | Required behavior |
| --- | --- |
| Merge A, then merge B 5 minutes later | A can publish A1+B0, followed by B producing A1+B1. No unchanged mod is rebuilt in the second run. |
| B's event starts before older A's event | B diffs from the last published commit and builds all not-yet-published A and B changes. A later skips as superseded. |
| One commit edits A+B | Two independent matrix builds; exactly one complete Release. |
| File moves from A's bundled assets into B | Treat both removal and addition as build changes; rebuild both affected mods. |
| A1 and A2 arrive rapidly | Serial planning makes A2 increment after A1 or includes both in one build. An older SHA never makes Latest roll backward. |
| A's build fails, then a B merge arrives | No partial Release for A; B's cumulative diff selects both modules and either publishes both or fails. |
| One changed mod fails in a two-mod run | Publish job does not start; successful artifact cannot be published alone. |
| Unrelated docs or CI-only change | No new Release unless this is the one-time migration from old tag namespace. |
| No module binaries changed but WoT client folder changes | Repack verified installers for the new target, preserving binary bytes; explicitly warn that compatibility is untested. |
| Migration or retarget requires no build artifacts | Allow an absent internal `built/` directory, but still require an exact empty build set and verify all carried ZIPs. |
| Two WoT client updates without an intervening merge | Produce two distinct global release tags, both on the same source commit, and never mutate the first immutable Release. |
| Re-run of a published source commit | Plan is a no-op; immutable Releases and tags are not overwritten. |
| Release draft interrupted after upload | Fail closed. Inspect manually; do not delete or finish it automatically. A rerun cannot mutate an immutable published Release. |
| Tag was pushed, but release creation failed before a draft appeared | Re-running the same accepted commit may reuse the already correctly pinned tag. A later commit can supersede it, leaving a protected orphan tag for owner inspection; never retarget it. |
| Tag exists at a different SHA, Ruleset changed, or approval missing | Fail before Release publication; no bypass/rewrite. |
| `main` force-pushed or diverged from Latest | Fail closed until an owner reviews history and decides a safe recovery. |
| New module path is not registered | Fail rather than silently omit a mod from an otherwise complete snapshot. |
| First merge introducing mod C after a complete A+B Release | Verify A+B against the tagged historical registry; build C (and any affected shared inputs), then require A+B+C in the new full snapshot. Never accept an unexplained missing older mod. |
| An administrator publishes outside the coordinator | Revalidate Latest immediately before publication; fail if it changed. The job-level mutex cannot constrain external administrators. |
| WoT update evidence is stale | Do not publish; explicit fresh evidence is required before any tag creation or Release upload. |

The top-level queue preserves up to GitHub's supported pending-run limit; it
is not an infinite backlog. Monitor cancelled, skipped or failed workflow runs.
The queue and verification do not certify compatibility inside World of Tanks.

## 4. Adding the third and later mods

1. Introduce the module's source tree, deterministic versioned package,
   independent test suite, privacy checks and direct installer ZIP.
2. Add its unique ID, installer prefix, base version and source globs to
   `scripts/release_modules.json`. Do not broaden another mod's source globs.
3. Add its exact safe packager/verification contract to `KINDS` and the
   corresponding handlers in `scripts/release_installers.py`, and add an
   isolated build case in `scripts/build_release_module.sh`. A new module
   cannot be released until the complete set can be verified together. Keep
   `verify_directory` default verification strict for the **current** full
   module set. Only historical snapshots may specify their tagged older set.
4. Add a **separate** read-only PR workflow with native `pull_request.paths`,
   its own tests and `archive: false` installable ZIP artifact. Do not add
   `contents: write` or public release commands to any PR workflow.
5. Extend the registry/scoping tests and complete ZIP collision, privacy,
   checksum and A→B/B→A race tests. Shared infrastructure changes should
   select each module that genuinely depends on that infrastructure.
6. Change the code in a dedicated CI PR, obtain normal review and owner merge
   authorization. The publisher does not need any per-pair compatibility rule:
   its matrix and file selection derive from the registry.

## 5. Existing owner protection and re-attestation

The one-time setup was completed on 2026-11-09 and the first unified immutable
Release, `wotmods-v1.0.158`, was published successfully. Keep the following
owner-reviewed settings; repeat the inspection and update the attestation
variables after any Ruleset change:

- **Settings → Rules → Rulesets → New tag ruleset**: name
  `wotmods-release-tags`, enforcement **Active**, one target
  `refs/tags/wotmods-v*`, no exclusions; restrict **updates** and **deletions**,
  permit creations, and allow **no bypass actors**.
- **Settings → Environments**: new environment `wotmods-release` with a
  deployment branch restriction for exactly `main`. Do not configure reviewers
  or delays unless intentionally switching to manual publication approval.
- With owner-level visibility, inspect the exact Ruleset and its `bypass_actors`
  (must be `[]`). Set two **non-secret** Environment variables to attest that
  exact reviewed revision when GitHub hides bypass actors from `GITHUB_TOKEN`:
  `WOTMODS_REVIEWED_RULESET_ID` and
  `WOTMODS_REVIEWED_RULESET_UPDATED_AT`.

Example owner inspection on a trusted CLI session:

```sh
gh api 'repos/Szwarceneger16/WotMods/rulesets?targets=tag' \
  --jq '.[] | select(.name == "wotmods-release-tags") | .id'
gh api 'repos/Szwarceneger16/WotMods/rulesets/REPLACE_ID' \
  --jq '{id, updated_at, bypass_actors}'
```

If `bypass_actors` is redacted to the publisher, it requires both matching
non-secret environment variables; absence is **not** treated as an empty list.
Any Ruleset edit invalidates the timestamp approval and publication stops.

Keep the existing `staysharp-release-tags` and `sessionstats-release-tags`
Rulesets: their historical immutable Release tags remain preserved. Never
delete, rewrite, retarget or modify existing published Releases to "clean" the
list. Historical cleanup requires a separate explicit owner decision.

**Merge order:** owner-reviewed new tag protection and Environment first;
then the dedicated CI/workflow PR; finally later feature PRs should be updated
onto accepted `main` and revalidated. Tests running on an unmerged proposed
workflow do not prove that it is the accepted default-branch harness.

## 6. Validation checklist before asking for review

```sh
python3 -m unittest discover -s tests -v
python3 -m unittest discover -s mods/sessionstats/tests -v
python3 scripts/privacy_audit.py
bash -n scripts/build_release_module.sh
```

Confirm PR path filtering with `tests/test_pr_ci_scoping.py`, race and assembly
behavior with `tests/test_release_coordinator.py`, and security of the global
workflow with `tests/test_unified_release_workflow.py`. Check the complete diff,
not only test names. No scripted review can replace the game's own runtime QA.
