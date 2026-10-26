# Building and publishing WotMods

## Source and local build

- `source/mod_staysharp_medkit.py` is the WoT client runtime (Python 2.7-compatible).
- `source/build_wotmod.py` creates the single, self-contained `.wotmod` archive using Python 3 standard-library tools.
- `assets/medkit_pulse_master.dds.b85` and `.sha256` are the checked animation master; 21 DDS frames are generated without external downloads.
- `source/build_audio_bank.py` creates the bundled Wwise v150 PCM bank from checksum-verified `assets/medkit_ready.wav.b85`; no authoring tool or synthesizer is required for packaging. See [audio details](AUDIO.md).
- `VERSION` is the reviewed release base. The `Release WotMod` workflow uses its own `github.run_number` to select a unique patch number. A *rerun* keeps the same number; a new dispatch/merge gets a new number.

Run:

```sh
python3 scripts/privacy_audit.py
python3 -m unittest discover -s tests -v
python3 source/build_wotmod.py
(cd dist && sha256sum -- *.wotmod > SHA256SUMS.txt && sha256sum --check SHA256SUMS.txt)
```

Local tests do not prove rendering correctness inside the game; test each new build in a real WoT client before recommending it as confirmed stable.

## GitHub Actions: deliberately simple and GitHub-native

- **PR CI:** `.github/workflows/ci.yml` checks source, privacy and builds. It has `contents: read` and **cannot publish** a release.
- **Automatic Release:** `.github/workflows/release.yml` runs only when **Stay Sharp-owned** source/assets/version/build files change on `main` (or manual dispatch). Changes confined to `mods/sessionstats/**` do **not** build or release Stay Sharp. No third-party release platform, custom REST/HTTP client or Java.
- **Build job:** read-only checkout, unit tests, source/privacy scan, deterministic `.wotmod` + `SHA256SUMS.txt` validation. GitHub's first-party `actions/upload-artifact` preserves the verified output between jobs.
- **Publish job:** only after a green build, and only on `main`, grants `contents: write`, downloads **that same** build with `actions/download-artifact`, verifies SHA-256 again, creates the Git tag pointing to the exact merge commit (if absent), and checks it.
- **Installer:** the publish job passes the verified `.wotmod` and checksum manifest to `scripts/release_installers.py package release --source dist --mod staysharp`. It creates `StaySharp-Medkit-v<version>.zip` with the exact package under `mods/<client_version>/`, the inactive `mods/configs/staysharp.medkit.json.example`, and documentation/voice attribution under `docs/staysharp/`. The soundbank remains inside the original `.wotmod`.
- **Carry-forward:** while holding the shared publication mutex, `scripts/release_snapshot.sh` downloads the previous **Latest immutable Release**, validates the installers and carries Session Stats forward byte-for-byte. Legacy release assets are checksum-verified before migration. The temporary outer manifest is removed before publication; each installer retains its complete internal manifest. It **never runs Session Stats' builder**.
- **Release:** a single official `gh release create --verify-tag --latest` uploads the entire verified snapshot. The workflow then downloads all published assets and checks their bytes, filename set and SHA-256. Existing published assets are verified but never overwritten.
- First-party GitHub Actions are pinned to their exact full commit hashes. The only credential is the ephemeral, repository-scoped `GITHUB_TOKEN`; the build job never receives a write-capable token. The publish job's checkout uses this token only to push the Git tag.
- A **publish-job-only** shared `concurrency` group with `queue: max` serializes all mod publications (up to 100 pending) without blocking independent builds or replacing pending merge events. Older same-mod builds are skipped if Latest already contains a newer primary package; no automation deletes, moves, modifies or retargets existing Releases.

GitHub's `gh release create` internally creates a draft, uploads assets and publishes the Release as separate requests. **No implementation can guarantee these three steps are atomic.** If a draft is interrupted, the workflow fails visibly; it does not delete the draft or falsely report success. There is intentionally **no custom recovery script or workflow**.

## Required GitHub tag protection (before merging)

The publication workflow **fails closed** unless an active native GitHub
**tag ruleset** named `staysharp-release-tags` prevents moving/deleting version
tags. This addresses a race in which `gh release create --verify-tag` only
checks the existence of the tag; GitHub's Immutable Releases protects tags
**after publishing**, not during the draft upload.

Configure once in **Settings → Rules → Rulesets → New ruleset → New tag ruleset**:

- **Name:** `staysharp-release-tags`; **Enforcement:** Active.
- **Target tags:** `staysharp-v*`, stored by GitHub as `refs/tags/staysharp-v*`; no exclusions.
- **Rules:** Restrict updates and Restrict deletions.
- **Bypass actors:** none. Leave **Restrict creations** unchecked, because
  GitHub Actions needs to create new version tags.

The publishing job discovers candidate Rulesets with GitHub's native
`GET /rulesets?targets=tag` filter (the listing omits `target`), then checks
the full Ruleset using a **read-only** `gh api -X GET` call.

**Bypass-list visibility:** GitHub deliberately omits `bypass_actors` unless
the caller can modify that Ruleset. The scoped `GITHUB_TOKEN` has
`contents: write`, but not Ruleset administration. Therefore **missing
`bypass_actors` is NOT an empty list**. The publisher accepts either an
explicitly returned `bypass_actors: []` or a *human-reviewed, pinned
Ruleset revision*. There is no extra PAT, GitHub App or custom HTTP client.

To approve a Ruleset without granting administrative credentials to Actions:

1. As the repository owner, inspect **Settings → Rules → Rulesets →
   `staysharp-release-tags`**. Confirm it is Active, targets `staysharp-v*`, blocks
   updates/deletion and contains **no bypass actors**. The owner is the
   trusted authority for this initial verification.
2. Find its numeric ID and last-updated timestamp using the owner's own
   `gh` CLI login (on a trusted local computer):

   ```sh
   gh api 'repos/Szwarceneger16/WotMods/rulesets?targets=tag' \
     --jq '.[] | select(.name == "staysharp-release-tags") | .id'
   gh api 'repos/Szwarceneger16/WotMods/rulesets/REPLACE_ID' \
     --jq '{id, updated_at, bypass_actors}'
   ```

   Only continue if the owner's response shows `bypass_actors: []`.
3. Open **Settings → Environments**, create `staysharp-release`, restrict
   deployments to `main`, and set these two *non-secret environment variables*:

   - `STAYSHARP_REVIEWED_RULESET_ID` = the numeric Ruleset ID.
   - `STAYSHARP_REVIEWED_RULESET_UPDATED_AT` = the exact `updated_at` string
     returned by the owner-authorized API request.

   Environment variables in a personally owned repository can only be
   configured by the owner. The automatic release job references this
   environment but requires **no manual approval for every release**.
4. Any subsequent Ruleset change (including adding bypass actors) invalidates
   this approval because GitHub updates `updated_at`; the publisher refuses
   to proceed until the owner rechecks the full Ruleset and refreshes the
   two environment variables. If GitHub omits the Ruleset timestamp, it
   also refuses to publish.

This is a human-admin trust anchor, not a way to infer hidden API fields.
No program can verify the complete bypass list with an unprivileged token
when GitHub deliberately redacts it. Administrators who can change Rulesets
remain trusted and must not bypass their own controls during publication.

The script also resolves the tag from the **remote Git server** immediately
before and after publication and after downloading/verifying release files.
Unlike a local `git rev-parse`, this detects an unexpected move of the remote
tag, but the native tag ruleset is the mechanism that *prevents* changes by
ordinary writers during `gh release create`'s multi-request draft phase.
A repository administrator capable of disabling the ruleset remains part of
the trusted computing base.

## One-time GitHub setting: Immutable Releases

Before the first successful public release, enable **Settings → Releases → Enable release immutability** in this repository. GitHub then protects new published release assets and their associated tags from modification, and generates release attestations. This setting applies to **future** published releases and cannot be enabled by this source-code PR alone. **It does not replace the required version-tag ruleset above.**

Check published assets using `gh release verify <tag>` and `gh release verify-asset <tag> <filename>` after enabling immutability. The workflow also always verifies actual downloaded bytes independently of this setting.

## The interrupted `v1.6.1` release

The original first run left **an unpublished, empty draft** named `v1.6.1`. The tag still points to the exact original commit. This draft is **not** a public downloadable Release; it does not block a newer `v1.6.2` (automatic run #2).

To tidy it, inspect `v1.6.1` in GitHub's Releases UI. Only if it is **still a draft**, optionally delete **the draft only**, keeping its Git tag. Do not delete published releases or move tags. There is no need to re-create `v1.6.1`: the first successful automatic publication will use the new, unique release number. For a historical rebuild, check out the original tag and run the local build procedure, without publishing over an existing tag.

If a new run leaves a draft, leave it for manual investigation, and fix the underlying fault in a reviewed PR. A fresh run can publish a new version; **rerunning the same run** will fail safely until the draft is manually reconciled.

## Release numbering and scope

The first merged workflow on `main` had run number 1, producing `v1.6.1`, but publication failed. New runs now use `staysharp-v<version>`; the numeric version still comes from the same workflow run counter and baseline. This is **workflow-run numbering**, not the number of commits and not a tag-triggered workflow. Tags created with `GITHUB_TOKEN` don't trigger another GitHub Actions workflow.

For now, this pipeline builds **Stay Sharp only**. The repo can contain other mods, but `/releases/latest` is a repository-wide pointer. A future multi-mod release workflow must be explicitly designed and reviewed before combining artifacts.

WoT upgrades may change the Python interpreter, HUD, or private methods used by the mod; this pipeline cannot guarantee runtime compatibility with untested game updates.

See [independent builds and shared immutable Release snapshots](MULTIMOD_RELEASES.md) for cross-mod concurrency and migration requirements. PR-only path-filter-skipped checks should not be configured as mandatory branch protection checks without an always-running gate.

### Fast successive merges across multiple mods

The publish step acquires the same `wotmod-release-${{ github.repository }}`
**job-level** mutex for every mod; `queue: max` keeps up to 100 waiting
publications rather than discarding an earlier pending workflow. The shared
mutex covers **reading current Latest**, copying unchanged files, creating
and verifying the new Release. Build jobs remain independent and parallel.

If A and B merge back-to-back, either publication order yields a complete
Latest containing A-new and B-new, because the second publisher reads the
first publisher's finished snapshot. If two versions of A publish in reverse
order, the older run exits as a successful no-op, never reverting A to an old
binary. Every mod's release workflow must use the same lock and the same
`release_snapshot.sh DIST PRIMARY_FILE PRIMARY_GLOB ...` contract; otherwise
this guarantee does not hold. See [MULTIMOD_RELEASES.md](MULTIMOD_RELEASES.md).

## Migration from the historical Stay Sharp namespace

New runs use `staysharp-v<version>`, Ruleset `staysharp-release-tags`,
Environment `staysharp-release`, and `STAYSHARP_REVIEWED_RULESET_*` variables.
The package filename and version algorithm are unchanged. Snapshot comparison reads the primary package version rather than a
Release tag prefix. There is no legacy publisher, alias or configuration fallback.

Before merging this workflow migration:

1. Create a NEW active tag Ruleset `staysharp-release-tags` targeting exactly
   `staysharp-v*`, with no exclusions or bypass actors. Enable Restrict updates
   and Restrict deletions; leave Restrict creations off.
2. Create `staysharp-release` under Settings → Environments. Select **Selected
   branches and tags**, add a **Branch** rule for exactly `main`, and leave
   required reviewers/wait timers off for automatic publication.
3. Inspect the new Ruleset and set its exact numeric ID and `updated_at` in
   Environment variables `STAYSHARP_REVIEWED_RULESET_ID` and
   `STAYSHARP_REVIEWED_RULESET_UPDATED_AT`. Do not copy the old ruleset's values.
4. Finish or cancel old running publications, then review and merge the
   migration. Once no old publisher is running, retire the old
   `wotmod-release-tags` Ruleset targeting `v*` and delete the unused
   `wotmod-release` Environment and its approval variables. Legacy settings
   are not required by the new publisher.
5. Synchronize open CI/source branches onto accepted main so they cannot
   restore the old publisher configuration. Historical tags/releases need
   no migration, aliases, renaming or republication.

The repository-wide lock deliberately retains its generic name
`wotmod-release-${{ github.repository }}`. Giving each mod a different lock
would permit simultaneous writes to the shared Latest pointer.
