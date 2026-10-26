# History persistence and panel performance

This follow-up to the independent PR #3 audit removes full-history rewriting
from battle updates and full-history projection from normal panel refreshes.
The startup follow-up also splits initial loading into scheduled garage steps
and durably captures events arriving before completion. It does **not** certify
live-game frame times. All measurements below use synthetic records on a Linux host.

## Changes

- Battle updates persist the changed normalized record and changed period
  boundaries. They no longer deep-copy, encode, hash or reread all battles.
  Accepted state and indexes advance only after the commit marker is durable.
- Storage format 2 retains three small, atomic generation descriptors. A
  descriptor authenticates an immutable base and a committed journal prefix.
  Journal files are owned by one writer and have an independently flushed mirror.
  Transactions are chained by SHA-256, flushed before descriptor rename, and
  replayed iteratively. A failed append/rename leaves the prior prefix committed;
  a retry truncates only that writer's uncommitted tail. A restarted writer uses
  a new segment. Existing lock, stale-generation and post-commit protections apply.
- Base/segment creation uses exclusive file creation. Names are restricted to
  local UUID filenames. A corrupted primary can recover from its mirror;
  damaged newest prefixes can recover an earlier valid descriptor. Unknown
  formats remain read-only. A missing/corrupt base and mirror are not reinitialized.
- Legacy v1 histories load with their existing checksum and application validator.
  Base copies and new segment headers are prepared during service initialization,
  before live writes. Subsequent loads authenticate the immutable base bytes,
  avoiding repeated full-history JSON encoding. Old mod versions see storage
  version 2 and refuse writes instead of overwriting the new history.
- A snapshot read is capped at 64 MiB; larger files fail closed without falling
  back to an older, potentially incomplete history. Individual journal headers
  and transactions are bounded at 1 MiB and JSON nesting remains bounded.
- Active-period totals, group totals, extrema, warning counts and pending IDs are
  indexed. Corrections remove the old contribution and add the new one. WN8
  remains calculated from aggregate actual/expected totals. Floating-point
  cancellation and overflow can recover after a correction. Startup builds
  indexes in batches; battle updates modify only affected groups.
- Each scope supplies at most 40 rows per grouping (battles, vehicles, maps).
  Previous/Next controls request further pages. Totals and coverage always refer
  to the entire period. Commands carry account and period identity, so stale
  account/reset requests are ignored. Native thumbnail enrichment only copies
  displayed battle contexts. Display names are capped at 256 characters and
  notices at 200 plus an explicit additional-notices message; stored data remains
  intact. The installation scope uses the same paging and storage machinery.

No database extension, network service, new mod dependency, game thread,
worker-thread game API call, or new shared-client hook was introduced.

## Reproducible benchmark

Run `tools/benchmark_history.py` under Python 2.7 and Python 3. The revised fixture
first writes a real legacy ledger, then reopens it normally, so index construction
and migration are not bypassed by direct in-memory test seeding. It measures
initial load separately from a new beginning, a result correction, the first
snapshot plus compact strict JSON, and a subsequent journal-backed restart.

Baseline: `77331eb581f00bd3b3fe5947a43f4fd2c90b875e`, as measured in the independent
audit. Follow-up timings below are one observed run, not latency guarantees.

| Interpreter | Records | Beginning before | Beginning after | Correction after | Snapshot before | Snapshot after | Payload before → after |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| CPython 2.7.18 | 1,000 | 1.107 s | 0.003913 s | 0.004628 s | 0.859 s | 0.009833 s | 2,505,356 → 113,128 bytes |
| CPython 2.7.18 | 10,000 | 7.154 s | 0.004354 s | 0.004231 s | 7.287 s | 0.016238 s | 24,933,550 → 113,410 bytes |
| CPython 3.12.14 | 1,000 | 0.094 s | 0.002956 s | 0.002880 s | 0.177 s | 0.004456 s | 2,505,356 → 113,128 bytes |
| CPython 3.12.14 | 10,000 | 0.930 s | 0.005399 s | 0.004424 s | 2.151 s | 0.014177 s | 24,933,550 → 113,410 bytes |

These measurements exclude localization, thumbnails, native transfer, DOM layout
and the optional installation write. Actual disk/antivirus latency remains a
factor because successful receipt still requires synchronous flushing.

## Staged startup and results arriving during loading

Before this follow-up, the same 10,000-record Python 2.7 benchmark blocked in
initialization for 25.025 s on one legacy import (4.658 s in an earlier run) and
3.687 s on a journal-backed restart. Those are historical measurements, not the
new startup path. Host variability is substantial.

The game runtime now constructs a loading service and schedules one small portion
of work at a time. The target is 2 ms per callback, with another callback requested
after 10 ms in the garage. Account and installation loaders share that scheduler;
the budget is not multiplied by the number of loaders. While in battle the
scheduler checks once per second without advancing history work. Direct result
and battle-beginning capture remains active; backlog polling waits until ready.
No worker thread calls game APIs, and no interpreter/garbage-collector settings
are changed globally.

The steps cover file reading, incremental UTF-8 decoding, outer JSON containers,
legacy canonical checksums, journal verification/replay, record validation,
immutable base copying and index construction. Individual records still use the
standard JSON decoder. Existing v1 snapshots and v2 journals keep their formats,
checksum, mirror, size, recovery and stale-writer checks. Locks are not held across
callbacks: staged preparation creates exclusively owned uncommitted files, and
each commit rechecks the generation under the existing write lock.

Each account/installation has a bounded `startup-intake/` generation store. An
opening boundary, observed beginning or normalized result is accepted only after
its queue snapshot is committed. The receipt includes its original launch, time
and ownership; it never stores the full native server payload. Once the history
loads, the battle change and receipt watermark are committed together. Only then
is the queue entry removed. If cleanup fails or the process exits between these
steps, replay recognizes the watermark and does not apply the result twice.
Results arriving during index construction are drained before readiness. Missing
names/start times and ambiguous vehicle selection can use the loaded historical
context before reconciliation; XP bonus authority is preserved.

Until ready, the UI displays loading or failure rather than partial/zero totals,
and reset/pagination are disabled. Account switching keeps receipts with their
original account. Stop/restart cancels loading and makes retained callbacks inert;
pending receipts survive. Corrupt or unsupported histories are not replaced by an
empty ledger. Queue failures are visible, and a full queue rejects the new event
without truncating accepted entries. The queue is capped at 1 MiB and retains
three generations; recovery from a damaged latest generation can still require
retrieving recent results again, as with the existing history recovery policy.

Run `tools/benchmark_loading.py --records 1000 10000` under Python 2.7 or Python 3
to reproduce constructor, active-work and callback-slice measurements. The fixture
contains all battles in both active scopes and checks the final total. It excludes
real callback delays, native APIs and a second installation loader. This trades
long uninterrupted work for scheduled work; total CPU and time until all totals
are available can increase. Scheduler/frame delays can add tens of seconds for a
large history, and loading intentionally remains paused throughout a battle.

One final synthetic CPython 2.7.18 run with 10,000 records:

| History | Constructor | Median slice | 99th percentile slice | Longest observed slice | Active work, excluding scheduling |
| --- | ---: | ---: | ---: | ---: | ---: |
| Legacy import | 5.667 ms | 2.088 ms | 8.858 ms | 60.820 ms | 6.399 s |
| Journal restart | 3.374 ms | 2.060 ms | 4.935 ms | 62.567 ms | 4.613 s |

The journal restart used 2,024 callbacks. This is a reduction in uninterrupted
work, not a reduction of total startup work to 2 ms. Earlier runs on the same host
observed slices up to about 99 ms. Percentiles describe this fixture/run only;
they are not performance guarantees for the embedded client or arbitrary histories.

The existing live-path benchmark was rerun after these changes: a 10,000-record
Python 2.7 history took 7.486 ms for a beginning, 5.178 ms for a correction and
14.830 ms for snapshot plus JSON (113,410 bytes). These remain bounded live-path
measurements; they exclude native UI and the optional installation write.

## Remaining performance limits

**The 2 ms target is cooperative, not a hard latency bound.** One large individual
JSON value, a bounded journal transaction, key/group sorting, period-list copies,
filesystem calls, `fsync`, Python memory reclamation or host scheduling can exceed
it. The small intake is loaded and rewritten synchronously for durable capture;
a near-full queue and slow disks can still cause a delay. A diagnostic run associated
the longest index slices with Python 2 generation-2 garbage collection; this change
does not disable the shared collector. Live WoT/Windows measurements remain required.

Journal replay, receipt watermarks and index memory grow with history/restarts. Journals, mirrors and orphaned
pre-commit segments are deliberately not deleted or automatically compacted by
this change. Reset preserves historical membership. Very long histories with
many result revisions/restarts require an explicit maintenance/compaction design.
Period-list copying and group sorting still scale with period/group count, and
pending-result recovery scales with the number of incomplete results. This is
not a constant-time or bounded-memory guarantee for every possible input.

Back up the **entire account/installation data directory while the game is
closed**, including `journal/`, its `.bak` files and `startup-intake/`. Copying only
`state-*.json` no longer creates a complete backup. Do not manually delete journal
segments or pending intake. Allow loading to finish before downgrading: earlier
journal-capable releases ignore the new pending queue. Receipt watermarks are
additional ledger metadata; no SQLite extension or external database is needed.

## Regression evidence

`test_history_performance.py` checks bounded encoded writes and copy work,
complete traversal of all pages, full-period totals, incremental/full-recompute
parity through corrections/resets/restarts, overflow recovery, independent
snapshot objects, failed commit/mirror flush and retry, mirrored corruption
recovery, torn-tail fallback, stale writers, malformed/future descriptors,
oversize protection, filename collisions, bounded display fields and stale
pagination commands. Existing chronology/account/installation/recovery suites
also run against journal storage. The generation-recovery fixture now restores
its journal dependencies alongside its head descriptors.

`ui-pagination.cjs`, included in the existing panel suite, exercises shipped
pagination controls, ownership parameters, row replacement, totals/counts,
first/last-page limits, old small payloads and retained handlers after teardown.
It uses explicit button-label elements required by the existing Gameface
compatibility contract. Browser doubles do not replace a real client test.

`test_staged_loading.py` covers staged read/validation/index parity, events before
and during loading, cancellation, restart, commit-before-cleanup interruption,
queue write/size failures, corruption, concurrent writers, deferred metadata and
vehicle selection, historical period ownership, installation provenance, timer
failure/retry, account switching, battle pause and retained callbacks. Streaming
JSON tests compare decoding and canonical hashes across small UTF-8/number/escape
boundaries and reject malformed/truncated input. `ui-loading.cjs` covers loading,
failure, visible queue warnings, blocked reset and restoration of totals/rows.

Local validation: all 546 tests pass on CPython 3.12.14; the same suite passes on
CPython 2.7.18 with nine expected Python-3-only packaging skips. All 211 repository
tests pass. Browser suites pass 230 panel, 22 wheel, 29 footer activity, 40 footer
compatibility and 31 appearance checks, plus the base footer suite. The package
build, all-six-asset reproducibility, integration isolation and recursive
source/archive/bytecode privacy audit pass. Hosted CI is reported separately in
PR #3. No live WoT/Windows/mod-pack validation was performed.
