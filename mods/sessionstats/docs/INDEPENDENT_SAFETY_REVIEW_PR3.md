# Independent stability and coexistence review of PR #3

Review date: 2026-10-23. Baseline: `33337c1c8778577a2ef0ac5a7be4d9a57881da62`.

The baseline's 485 Python tests passed. Independent failure injection still
identified the failures below. This review does not certify the absence of all
bugs, native crashes, or conflicts with arbitrary third-party modifications.
No live WoT client, XVM installation, Windows filesystem, or production account
was used. All generated battle data is synthetic.

## Findings and corrections

| Priority | Finding and trigger | Consequence | Status |
| --- | --- | --- | --- |
| P1 | `CacheObserver` replaced native `get(arenaUniqueID, callback)` with a different, fixed argument signature. Keyword calls and earlier mods' additional parameters failed, including calls on unrelated cache instances. | A valid result read could raise before reaching the native cache or another mod. | Fixed: preserve positional/keyword/extension arguments and native returns/errors; only replace the callback slot. Unrecognized shapes bypass observation. |
| P2 | Observer teardown assigned an inherited `get` method directly onto the subclass. | Later changes to the base cache class were shadowed after Session Stats stopped. | Fixed: remove the owned override when the original method was inherited; preserve later wrappers. |
| P2 | Callback objects that reject optional attribute lookup could throw while checking the mod's marker. | The optional observer prevented an otherwise valid callback from reaching the native cache. | Fixed: marker/capture failures bypass observation; the original request executes once. |
| P1 | Footer attachment did not protect its outer wrapper from exceptions in ownership/rollback adapters. | A failure in optional integration could escape through native `_onLoading` and interrupt a later wrapper. | Fixed: contain attachment failures after the original native loading call, preserving its return value and exceptions. |
| P2 | Footer construction/registration could synchronously uninstall the integration before returning. | A newly registered child remained after teardown, even though the integration was disabled. | Fixed: recheck ownership after construction/registration; remove late children or retain failed cleanup for retry. |
| P1 | A directory-listing or lock-release error after successful generation rename was reported as a failed save. | The durable ledger advanced while `StatsService` retained its previous state; the next successful write could erase the accepted battle/reset. | Fixed: publish the committed generation at rename; post-commit cleanup errors do not roll back accepted memory. Prune from the already observed file list. Always release the process lock even if handle close fails. |
| P2 | Finite positive WN8 overrides, or finite values whose sums/products overflow, could produce infinity. Example: `expDamage = 1e-308`. | Strict native JSON serialization failed, preventing the statistics panel from opening/updating. | Fixed: unrepresentable derived values become unknown; invalid ratings are excluded from WN8 coverage. Valid XP/finance information remains available. |
| P1 | Full history is copied, serialized, checksummed, reread and rewritten synchronously; the panel serializes every battle in both active scopes. | History growth can cause long stalls on battle entry/result delivery and when opening the garage panel. | **Per-battle writes and panel projection fixed in the performance follow-up. Startup now uses staged loading with durable intake; frame-time limits remain. See [HISTORY_PERFORMANCE.md](HISTORY_PERFORMANCE.md).** |

The native cache signature was verified against the existing pinned
[client source](https://github.com/izeberg/wot-src/blob/5e721e36891c80d8d51a431164960c863641ee63/sources/res/scripts/client_common/shared_utils/account_helpers/BattleResultsCache.py).
Its actual implementation is evidence for argument compatibility; synthetic
tests do not claim that a particular installed mod currently makes those calls.

## Original history scaling measurements

These measurements describe the audited baseline. The implemented follow-up and
current limits are documented in [HISTORY_PERFORMANCE.md](HISTORY_PERFORMANCE.md).

`tools/benchmark_history.py` uses real `StatsService`/`GenerationStore` code with
synthetic records. Run it outside the game:

```sh
python3 mods/sessionstats/tools/benchmark_history.py
/path/to/python2.7 -B mods/sessionstats/tools/benchmark_history.py
```

Measurements on this review's Linux execution host, without live WoT:

| Interpreter | Existing records | One new beginning/write | Snapshot and compact JSON | Payload size |
| --- | ---: | ---: | ---: | ---: |
| CPython 2.7.18 | 1,000 | 1.107 s | 0.859 s | 2,505,356 bytes |
| CPython 2.7.18 | 10,000 | 7.154 s | 7.287 s | 24,933,550 bytes |
| CPython 3.12.14 | 1,000 | 0.094 s | 0.177 s | 2,505,356 bytes |
| CPython 3.12.14 | 10,000 | 0.930 s | 2.151 s | 24,933,550 bytes |

These are observations, not predictions for another CPU, disk, embedded Python
build, or game client. They exclude localization, image enrichment, native
transfer and DOM rendering. The optional installation ledger adds another write.
In the baseline, the account ledger kept historical records after manual reset,
so resetting the visible period did not bound persistence work. Its
`GenerationStore._decode` also read an entire generation without a byte limit. An oversized/corrupt local
file can therefore create additional memory pressure before validation.

The performance follow-up adds incremental mirrored persistence, bounded reads,
incremental active-period totals and paginated history without deleting records
or weakening the accepted-write boundary. Initial loading still needs further
work, and a live-client frame-time test remains necessary.

## Independence and coexistence

- The statistics engine and native window do not import XVM, Aslain, Medkit
  Reminder or OpenWG. WN8 uses bundled coefficients; it does not call an XVM
  service or require XVM to be installed.
- The optional garage footer **does depend on OpenWG Gameface**. The supplied
  dependency includes `res/gui/gameface/js/index.js` and a shared
  `openwg_gameface` module. Therefore the complete installation ZIP cannot be
  described as having no shared-resource dependency. Multiple incompatible
  OpenWG versions or another replacement of that resource remain an integration
  risk, not a demonstrated XVM-specific conflict.
- The Session Stats `.wotmod` alone supports collection and the default
  **Ctrl+F10** native window. OpenWG is required only for the footer button.
  If another mod already supplies OpenWG, avoid installing a second copy;
  exact version compatibility still needs a client test. Disabling the footer
  does not unload a separately installed OpenWG package.
- Shared cache/footer hooks preserve existing native behavior and later mod
  wrappers; footer child position collisions are detected rather than replacing
  the other child. CSS selectors, resource names, package IDs and module names
  are scoped to Session Stats. A noncooperative mod can still overwrite a hook
  without chaining it; no local wrapper can guarantee compatibility with that.
- Configuration uses validated scalars and fixed CSS templates. Catalog text is
  rendered as text, notifications are escaped, and thumbnail paths are restricted
  to verified local game resources. No custom networking, executable download,
  automatic gameplay input or native preference mutation was added.

## Test coverage and its limits

`tests/test_independent_safety.py` adds 18 tests, including 81 malformed-result
variants across nine input positions. Every variant verifies that later native
listeners still run, the source object is unchanged, processing ownership clears,
and a later valid result is collected correctly. Fourteen tests fail against the
baseline production source; all 18 pass with this correction.

| State/failure family | Automated evidence | Remaining limitation |
| --- | --- | --- |
| Login, account/region switch, restart, replay, late results, reset boundaries | Existing runtime, account/installation, chronology and recovery suites | Native event order and server retention are simulated. |
| Battle entry and missing/partial metadata | Existing entry/runtime suites; malformed-result matrix | No real battle, reconnect or replay client was launched. |
| Other-mod cache wrapper order, keywords, extensions, inheritance, callback failure | Existing observer suite plus new compatibility regressions | Arbitrary non-chaining wrappers cannot be certified. |
| Footer/window teardown and retained callbacks | Native doubles, new reentrant registration cases, browser lifecycle suites | Chromium and Wulf doubles are not the real Gameface/Wulf runtime. |
| Write failure, stale writer, corruption, unsupported schema, commit cleanup | Existing storage/recovery suites plus post-commit regressions | Windows locking/antivirus, power loss and actual disk exhaustion need platform testing. |
| Bad config/catalogs, numeric extremes, unavailable optional APIs | Existing boundary suites plus finite-overflow regressions | Finite tests cannot exhaust every value or future client API. |
| Large persistent histories and panel payloads | Reproducible benchmark above | Write/panel paths and staged startup improved; native frame times remain unverified. See the follow-up benchmark. |

Validation of this correction: 503 Python tests on CPython 3.12; the same 503 on
CPython 2.7.18 with nine expected Python-3-only packaging skips; 211 repository
tests also pass. Browser validation passes 209 panel, 22 wheel, 29 footer activity,
40 footer compatibility and 31 appearance checks, plus the base footer icon suite.
The package builds successfully, all six assets reproduce exactly, and integration
and recursive source/archive/bytecode privacy checks pass locally. Hosted CI is
separate and was not used as evidence for these local results.
No claim of complete branch/state coverage or compatibility with
500 installed mods is made. Remaining indivisible operations and untested native frame times prevent an
unconditional recommendation that this version cannot stall gameplay.
