# PR #3 review fixes

## Review 5631576981: deferred provenance, clock skew and installation paths

When the installation root becomes available during account startup, backfill
copies durable beginnings captured by the current process immediately. It does
not inspect partially replayed history or adopt previous-process intake/cache
results as proof of installation identity. Each account also retries backfill
once loading succeeds, using its own account key even after an account switch,
so results received before discovery are included. Copies cannot mutate the
account ledger. Normal installation write failures remain contained and visible.

A live beginning with a valid server timestamp ahead of the local clock now
captures the current launch and manual period. Existing durable memberships
still win; historical/manual-reset ownership, invalid timestamps and unobserved
future results keep their existing rules. Deferred replay uses the original
observation time and launch, including after restart.

Ambiguous byte encodings in the authoritative paths.xml location now stop
installation discovery instead of falling back to a different game root. A
resolver that genuinely supplies no physical path still permits the existing
bounded fallback discovery.

Ten new regression/control tests cover all three findings, shutdown before and
after loading, duplicate recovered results, account switching, detached intake,
clock skew with restart/reset, and missing versus ambiguous resolver paths.
Before the fixes, seven regressions failed and both control cases passed. An
additional rollback/reset test protects historical ownership for newly observed
battles whose server timestamp is still ahead of the local clock.


## Review 5625868921: launch overlap after clock rollback

New launch boundaries are clamped to the greatest prior launch end after crash
closure, including a known closed end later than its last observed activity.
The new launch's initial last-seen value uses that same boundary. Ordinary
forward-clock starts retain their real start and unobserved gap. Existing battle
timestamps, durable memberships and manual reset identity remain unchanged.

Generation selection also checks the ordering between consecutive periods for
both launch/manual lists: a historical period must be closed, and the next start
cannot precede its end. A damaged overlap therefore recovers a valid older
generation instead of being accepted and amplified on restart. Equal touching
boundaries remain valid. Launch lookup gives prior observed activity first claim
on such a boundary for an unseen delayed result; explicit live observations
still select the current launch, including while its clamped boundary is ahead
of the rolled-back wall clock.

Regressions cover real rollback/restart and delayed results, equality, repeated
rollback, closed ends, normal forward gaps, live observations, manual-reset
ownership, account/installation ledgers, damaged overlap recovery, all-invalid
read-only behavior and failed launch commit/retry.


## Review 5624888833: record manual activity through normal writes

Every committed beginning, result/enrichment and reset now updates the active
manual period alongside the active launch. Each period retains the maximum of
its previous activity and the observation/commit timestamp, so a clock rollback
cannot lower the reset boundary. The initial manual period records its start as
last-seen activity. A delayed result still belongs to its original historical
period; only the currently active manual period's activity is touched.

Before permitting reset after startup, older ledgers restore their active manual
activity from validated persisted launch and battle-update timestamps. This
upgrade is committed through the same transactional generation path and does not
rewrite existing files. A second open does not repeat the upgrade. Normal
account and installation services share this behavior, while retaining their
independent reset identities and storage.

Regressions use real beginning/result calls rather than injecting a manual
boundary: they cover rollback/reset rejection, correct delayed membership,
restart, legacy upgrade without a new battle, partial activity during rollback,
failed writes/retry, account/region isolation and shared installation activity.
Duplicate results continue to avoid redundant writes. Failed commits do not
publish candidate activity or change existing periods/files.


## Review 5621032549: chronological period boundaries

Application validation now checks the ordering within each launch/manual period,
not just the type of its timestamps: `started_at <= last_seen_at`,
`started_at <= ended_at`, and `last_seen_at <= ended_at` when the optional fields
are present. Missing/null last-seen values retain the start-time fallback.
Equal boundaries, including timestamp zero, remain valid. A reversed known-schema
candidate is rejected during generation selection, allowing the valid backup to
restore history, reset identity and delayed-result memberships before any crash
closure or subsequent write.

The write-path audit covers launch closure, activity updates and manual resets.
Crash closure uses the validated last-seen boundary; activity updates retain its
maximum value during clock rollback. Manual reset refuses a time before the
active period's accepted last-seen boundary, preserving the committed state and
files rather than creating an interval the next startup would reject.

Regressions cover both period types, all three ordering relationships, same/new
launch recovery, delayed results, installation history, equality/zero boundaries,
clock rollback, reset rejection/retry, all-invalid read-only behavior, unsupported
schema protection and subsequent writes/restarts.


## Review 5620722118: period timestamps and mid-battle initialization

Generation selection now validates non-null optional `ended_at` and `last_seen_at`
values for launch and manual periods as finite nonnegative numbers, rejecting
booleans, strings and containers. Missing/null last-seen values consistently use
the period start during crash closure, membership lookup and activity updates.
Valid closed launches still cannot be reopened by selecting an older generation.

The related-field audit also validates unique text period identities, current/manual reset consistency, battle
membership references, normalized optional metadata/statistics/finances/warnings,
strict flags and revision/update numbers before accepting a ledger. A malformed
known-schema candidate recovers through the existing generation-selection path;
no rejected file is rewritten. Account and installation ledgers share this path.

`begin_battle` provides explicit live-observation evidence for the current launch,
including a battle whose server start precedes service initialization. The first
manual period can include such a live beginning; an explicit manual reset still
uses the battle's real start and cannot pull a pre-reset battle into the new
period. Existing durable memberships take precedence, and delayed result-only
reads still use historical timestamp-based membership. Server timestamps remain
unchanged in the record. The same behavior applies to the installation ledger.

Regressions cover fresh runtime startup and first account creation mid-battle,
missing/future/invalid beginnings, repeated events, restart/deduplication, manual
resets, installation collection, both period types and subsequent recovery writes.


## Review 5620473401: application validation during generation selection

`GenerationStore.load` accepts an optional application validator. StatsService
supplies its ledger validator before a generation is selected, so a checksum-valid
known-schema payload with invalid periods, battle records or account ownership
can fall back to an older valid generation. Account and installation ledgers use
the same path. Recovery preserves the existing manual-reset epoch and history;
the next commit advances past the newest observed generation.

Unsupported storage/payload/application schemas still stop selection and prohibit
writes. Exhausting the known-schema candidates leaves the store read-only without
reinitializing files. A valid newest ledger and a valid but already closed launch
are not rolled back. Concurrent/stale writer checks continue to compare against
the highest observed generation, including rejected candidates.

Regressions cover invalid manual/launch periods, malformed battles, mismatched
account ownership, multiple rejected candidates, installation resets, subsequent
restart/writes, unsupported schemas, all-invalid stores and stale writers.

## Review 5620062915 and related-pattern audit

The correction includes the three reported findings and a search for analogous
failures in the mod's JSON, packaging and native-resource boundaries:

| Boundary | Correction or verified existing protection |
| --- | --- |
| AppData preferences and WN8 override | One bounded reader converts decoder RuntimeError/RecursionError into the invalid-file fallback. Each start restores preference defaults; hotkeys have bounded text shape and the footer flag is a strict boolean. Bundled WN8 remains available after a rejected override. |
| Accepted deeply nested JSON | An iterative depth limit of 64 protects later conversion, copying and encoding even on interpreters that accept deeper input. It limits structural nesting, not history length. Applies to external runtime JSON and persisted generations. |
| State recovery and writes | Known-schema generations with excessive depth recover older valid state. Unsupported schemas are protected before depth/checksum processing. Failed nested/encoder writes leave the committed generation intact. |
| Appearance and language JSON | Existing bounded reads, strict shape validation and decoder-failure fallback were checked alongside their regression suites. No raw decoder text is added to fallback diagnostics. |
| Source-bundle rebuild | Numeric client directories and active installation target/command fields are restamped from any previous client. Release fields continue to follow source/VERSION. Historical source evidence and dependency versions remain unchanged. Client-version arguments require a full match. |
| Native window subscriptions and watchdog | A registration returning after close is rolled back. An old watchdog return cannot replace the timer owned by a newer window. Interrupted construction stops before loading a released surface. |
| Python footer ownership | Failed child removal and partial-registration rollback remain owned for retry. Reinstallation waits for release and cannot reactivate stale commands or remove another mod's replacement. Runtime retains failed uninstall handles across stop/start. |
| Loader ownership | fini retains a stopped runtime while native cleanup is unconfirmed. init reuses that owner, including after partial initialization failure, so old pending handles are not abandoned for a fresh runtime. |
| Footer JavaScript ownership | Each model callback belongs to its original resource ID and bridge. Late returns after destruction or model/bridge replacement are removed through that original API. Engine subscriptions returning after destroy are rolled back. |
| Panel JavaScript cleanup | Retained DOM controls cannot dispatch commands after destroy, including through a replacement/preview fallback. The exact key handler is removed so a destroyed panel no longer consumes Escape. Existing connection attempt, retry and model ownership checks remain in place. |
| Result/account ownership | Existing revision-authority, delayed-account refresh, stale result-token and late-cache regressions were included in validation. No new collector behavior or dependency on another mod is introduced. |

Tests inject both decoder runtime failures and successful decoding of invalid
nested values. They do not assume one fixed recursion threshold across Python
versions. Native lifecycle tests use strict doubles; browser tests use synthetic
bridges. Neither establishes compatibility with a live WoT client.

## English repository documentation

Repository guides, historical notes, changelogs, attribution descriptions and
package metadata are now English. Legacy guide/archive filenames remain stable
for existing packaging and links. The builder stamps the English `Version` line;
synthetic preview names and generic test messages are English too. Translated
catalogs, legacy Polish warning lookups and deliberate Unicode/localization test
fixtures retain their language-specific content.

Installation and language guides explicitly document the bundled seven-language
catalog, embedded English fallback, optional neighboring JSON files and partial
nested configuration overrides.

## Earlier review fixes

- Sources are stacked on dedicated PR #2, which supplies builds, both Python
  versions, Chromium tests and automatic Session Stats Releases. Workflow review
  remains in PR #2; PR #3 shows source changes. The pipeline must be accepted on
  `main` before the final source merge.
- Malformed-JSON tests require a numeric error location and omission of private
  values from logs without depending on the decoder's chosen error position.
- Each cache request owns a token. Late responses from expired requests cannot
  remove newer requests or bypass backoff.
- Only `reconcile=True` authorizes changing known results. `complete=True` marks
  completeness; without revision authority it may fill unknown fields only.
- Optional Gameface registration failure does not block the initial model read
  or sizing. A later model event retries registration without duplicate engine
  listeners; cleanup removes only an acquired registration.
- The builder stamps active guide filenames, including the source copy, with the
  release version. Historical changelogs and compatibility evidence stay historical.
- The ZIP's internal manifest uses paths relative to the extracted package root.
  At this review stage, `sha256sum -c SHA256SUMS.txt` verified all three installed
  files; the later language-catalog addition extends this to four.
- Old incomplete entries remain queued and stored, but do not keep the spinner
  active after restarting without a new battle. The panel explains the gap.
  Details: [RESTORED_RESULTS_ACTIVITY.md](RESTORED_RESULTS_ACTIVITY.md).

Validation: 364 Python 3 tests; the same Python 2.7 suite with 4 Python-3-only
builder tests skipped. The 114 panel checks cover rejected callback registration,
synchronous delivery during registration and retained callbacks after teardown.
A 0.2.8 build, actual extracted-ZIP checksum verification and an identical ZIP
rebuilt from its included sources were checked. Mocked-client tests do not replace
running WoT.

Offline recovery additionally observes the native cache before its consumer and
stream acknowledgment, uses a fair queue, separates cooldown/login delays and
fills unknown fields from late streams. Incomplete periods and missing battles
remain explicit. Recovery limits and pinned client code:
[OFFLINE_RESULT_RECOVERY.md](OFFLINE_RESULT_RECOVERY.md). Battle entry also saves
available map/vehicle names, tier and class, making missing results recognizable
after restart. Eight tests cover native descriptors, late metadata readiness,
persistence, write deduplication, confirmed-result protection and context privacy.

Raster comparison retains its 16-pixel limit; the 6/255 channel tolerance covers
10 pixels differing by 5/255 observed on Chromium 151. Styles and geometry still
match exactly. A negative control confirms rejection of actual color, radius and
opacity changes.

Review 5610518614:
- Deferred bonus refresh retains the account captured when scheduled. After an
  account switch, the timer releases its state and stops without reading or
  processing the new account's results. Manual Refresh remains independent and
  neither consumes nor cancels the old account's timer.
- Panel cleanup invalidates local binding/callback state before calling the bridge.
  Each of three engine.off calls and model-callback removal is guarded separately.
  One failure neither blocks the others nor escapes beforeunload. A retained scale
  callback stays inert after document destruction.
- Two Python tests cover switching accounts while a timer waits, no reads/revisions
  of the new account and independent manual refresh. Fifteen Chromium checks cover
  each removal failing separately, all failing together, repeated cleanup and late
  callbacks.

Account scopes and the optional durable installation scope:
- Default scopes and manual resets remain isolated per account and region.
  A confirmation from a previous account cannot reset the current account.
- sessions.instance_tab=true displays the installation tab. Its history and
  manual reset persist across game restarts using a separate transactional
  StatsService ledger; account ledgers and reset epochs are never modified.
- Installation identity uses the verified physical game root, independent of
  client-version directories. Unknown roots do not select a global fallback.
- Fifteen additional Python tests cover persistent history and reset boundaries,
  restart recovery, late discovery, separate installations, failed writes,
  corrupted generations and identity discovery. An additional browser check
  verifies that confirmation explains restart persistence.
- Details and migration rules: [ACCOUNT_SESSIONS.md](ACCOUNT_SESSIONS.md).

## English defaults and editable language catalogs

- All mod interface text now uses an English default and a configurable local
  JSON catalog with complete English, Russian, French, Polish, German, Spanish
  and Ukrainian dictionaries (181 message keys per language, including previews).
- Root `language` in `grz.sessionstats.json` selects the language. The neighboring
  `grz.sessionstats.languages.json` can override individual messages or add
  languages. The installation ZIP includes the editable file and verifies its
  checksum; the `.wotmod` includes all bundled translations as an offline fallback.
- Translation validation rejects unsafe placeholders and malformed catalogs;
  valid partial overrides retain per-message fallbacks. Native notifications
  escape markup and panel/footer labels use text nodes. Catalog values and
  private paths are omitted from diagnostics.
- Canonical English and legacy Polish warning templates are translated at
  presentation time. Account histories, session/reset boundaries and game-supplied
  map/vehicle names remain intact. Language reloads require opening the panel or
  Refresh, with no per-tick file reads.
- Local validation: 375 Python tests on both runtime interpreters (four builder
  cases skipped on Python 2.7), 183 infrastructure/Medkit tests, 165 panel checks,
  29 footer activity checks, 22 wheel checks, 12 footer compatibility checks and
  31 appearance checks. Raster checks use grayscale text to avoid RGB subpixel
  repaint artifacts while retaining the original exact style/layout comparison
  and pixel thresholds. All six assets reproduce; recursive privacy and
  cross-mod integration checks pass. Native Gameface still needs in-game review.

## Catalog recursion and pending panel readiness

- Review 5612698603: external and source-catalog loading now handle decoder
  `RuntimeError`, which also covers Python 3 `RecursionError`. A deeply nested
  catalog below the byte limit falls back locally. Valid language, appearance,
  scroll speed and installation-tab settings are preserved; account/session
  records are unchanged. Source-only fallback can still use embedded English.
- Three regressions use real decoder recursion on Python 2.7 and Python 3:
  external-catalog fallback, source-catalog fallback, and runtime Refresh with
  customized appearance, an enabled installation tab and existing history.
- The older pending-DOM review thread is also fixed: cleanup removes the exact
  `self.onDomBuilt` callback even when model binding has not started. Late engine
  readiness and load events cannot create new subscriptions after destruction.
  Five browser checks cover pending subscription ownership/removal, retained
  callbacks, delayed engine readiness and normal deferred rendering.

## Portable decoder regressions (review comment 4348237318)

The original recursion fixture assumed that every decoder would reject an array
nested 16,384 levels deep. CPython 3.14.4 accepts it, causing three tests to fail
before reaching the fallback behavior. This was reproduced on that interpreter.

The three fallback regressions now inject `RuntimeError` and, where available,
`RecursionError` at `json.loads` for the selected catalog document only. They keep
real file reads and decoding/validation boundaries, verify that injection occurred,
and restore the decoder in `finally`. Other configuration and stored data continue
through the original decoder. External fallback retains the selected bundled
language; source fallback retains embedded English; Runtime Refresh preserves
custom appearance, scroll speed, installation-tab state and account history.

A separate real 16,384-level input checks bundled-message fallback whether a
decoder rejects nesting or accepts the invalid non-string translation. The
14-test localization suite passes on CPython 2.7.18, 3.12 and 3.14.4. A negative
control removing the production `RuntimeError` handlers makes all three targeted
fallback regressions fail. Production behavior and workflow files are unchanged.

## Review 5616729809: retry native panel and footer subscriptions

Panel binding is committed only after both engine subscriptions succeed.
A rejected subscription invalidates its attempt before independently removing
both listeners, clears the connection gate and permits a later load/readiness
retry. Attempt-owned wrappers keep partially retained callbacks inert even
when native unsubscription throws. Readiness rejection and synchronous bridge
errors are handled without an unhandled promise. Successful connections still
render the current model, size the window and retain optional model-callback
retry behavior.

Footer model registration is retried whenever its callback ID is missing,
including after a rejection or null return for the same/recreated subview.
The model/button remains usable while registration waits. A reentrancy guard
prevents synchronous delivery from recursively registering another callback.

Browser regressions cover subscription failures before/after registration,
failed rollback removal, recovery and inert old callbacks, readiness rejection
and recovery, initial/recreated footer subviews, activity/appearance updates,
cleanup and synchronous registration. Targeted negative controls run these
regressions against the previous shipped JavaScript and reproduce both bugs.
Real Gameface/client validation remains separate from these Chromium doubles.

The source branch was synchronized with accepted main after infrastructure
PR #2 and Stay Sharp namespace PR #6. No candidate workflow replaces the
accepted validation harness.

## Review 5617307888: complete asynchronous connection lifecycle

The previous recovery tests depended on a second synthetic load event. That
could not recover a real document whose readiness promise settled after its
normal load events. The panel now owns one retry/check timer: failures use
100 ms exponential backoff capped at 2 seconds, and successful connections
are checked every 2 seconds without re-rendering or re-subscribing. Pending
promises are observed once per attempt. This also handles a late/missing or
replaced engine/viewEnv and retries optional model callback registration.

One attempt owns readiness, DOM-ready, data, scale and model subscriptions.
DOM-ready callbacks use the same active/identity guards as data and scale;
registration-time notifications are buffered until registration succeeds.
Rollback invalidates ownership before each independent native removal. Late
resolved/rejected promises and retained callbacks cannot modify replacement
attempts. Callback IDs returned during destruction are removed using their
original viewEnv. Replacement connections send fresh surface dimensions.
Destroy invalidates/cancels the timer and removes document bootstrap handlers;
even an already queued timer or failed native cancellation cannot reconnect.

The existing panel suite imports ui-connection.cjs, with deterministic timer
checks plus a real-timer integration case. The tests no longer synthesize
another load to recover. They cover late transient/permanent failures,
coalescing and capped backoff, stale/synchronous rejected DOM callbacks,
replacement readiness and old promise settlement, missed DOM events, late
bridge appearance, optional callback recovery, stable-connection no-ops,
replacement sizing and destruction during registration or pending retries.
All 207 panel checks pass locally. Two focused negative controls reproduce
both findings with the previous JavaScript and pass with the corrected source.

The review summary also identified an obsolete Stay Sharp release prefix.
The repository README and Session Stats pipeline table now both advertise
`staysharp-v…`, matching the accepted workflow and per-mod release settings.
