# Missing and partial result recovery in 0.9.16

Recovery uses the native `BigWorld.player().battleResultsCache.get` path. No
credentials, HTTP result service, replay estimates or independent background
process are introduced. A recorded beginning is not a received report. Missing
outcomes and numeric fields remain unknown; unavailable reports stay in history.

## Report coverage and transport are separate

Each visible account battle receives an optional `recovery` presentation object.
Its `report_state` is `never_received`, `outcome_missing`, `partial_report` or
`complete`. Its transport `status` explains queuing, an active request, shared
cooldown, rate limiting, unavailable reports, rejected data or failed reads.
Fixed reason codes distinguish malformed envelopes, missing identity, missing
own-vehicle data, missing outcome/combat/XP/finance and request failures. Reports
from replays, unsupported modes and other accounts are ignored without accusing
the current battle of a parser error. Raw responses are never saved in diagnostics.

The Battles card shows a short recovery label for missing or partial reports.
Its existing hover help provides attempts, last/next attempt, last data source,
known native status and the report limitation. **Retry result** addresses exactly
one pending battle from the active account's ledger. The native window bridge
preserves its lifecycle guard; runtime revalidates account, identifier, pending
membership, player readiness and garage state. Manual retry and **Refresh** use
the same serialized queue and do not bypass shared-cache cooldown.

The overview retains its single confirmed/recorded counter. Additional recovery
counts distinguish complete reports, partial reports, unknown outcomes and current
requests. Fetching is an activity count, not an additional disjoint report class.
Known outcomes with missing XP/finance remain partial. A usable WN8 alone does not
mean the report is complete. No per-metric visible x/y counters are added.

## Completeness repair

Normalization and merging share one coverage predicate. It requires an actual
received result, a recognized win/loss/draw, the seven required combat/XP values
and confirmed net values for credits, bonds and gold. Coverage is recomputed
after merging and deriving net only from known income and costs. Two complementary
partial reports can therefore complete one record. Optional historical Base
credits and mission details are not newly required.

An incremental startup pass repairs stale coverage flags from stored facts before
building indexes. It commits changed flags through the existing transaction store;
original values, battle identity and launch/manual membership remain intact.
The pass is idempotent and needs no native request to recognize already saved data.
Late callbacks retain fill-only authority, and old raw-cache responses cannot
replace already applied XP bonuses.

## Persistent bounded scheduling

Small retry hints live in an account-hashed `recovery` child directory beside the
existing account history. This separate GenerationStore has checksums, backup
selection and stale-writer protection. It does not alter the battle-ledger schema.
Entries contain bounded counters, fixed status/code/source/reason enums and attempt
timestamps. Hints cannot establish statistics. Unchanged ticks do not save them.
History remains usable when hint storage fails.

Requests remain serial with a 30-second timeout. Current battles take priority;
due historical work receives a turn after at most three current requests.
Transient native cooldown, rate limit, unready-player and disconnected responses
do not inflate per-battle failure backoff. Repeated unavailable responses receive
longer bounded delays, up to 24 hours, with manual retry available later. Native
cooldown remains authoritative. Restart restores delays and diagnostics rather
than treating every old failure as a first attempt.

The hints are bounded to 4096 records, preferring eviction of completed/old hints.
Evicting a hint never removes its battle. Payload enrichment is limited to visible
battle rows; no entire diagnostic ledger is sent to the frontend. Account and
region isolation, original sessions, duplicate handling, cache-consumer callbacks
and other mods' wrappers retain the existing boundaries.

## Client source verification

Compared on 2026-11-15 against EU mirror commit
[`447437a25a2222a0d10dde96f65a20254d3a7d0d`](https://github.com/izeberg/wot-src/commit/447437a25a2222a0d10dde96f65a20254d3a7d0d)
(`v.2.4.1.1 #993`, 2026-11-05). These client implementation sources are not a
stable mod SDK or a server-retention guarantee.

| Source | Verified behavior |
| --- | --- |
| [BattleResultsCache.py](https://github.com/izeberg/wot-src/blob/447437a25a2222a0d10dde96f65a20254d3a7d0d/sources/res/scripts/client_common/shared_utils/account_helpers/BattleResultsCache.py) | Native local-file/server fallback, `(code, fullForm)` callback, `convertToFullForm`; blob `f2f88011e792c06d332f73ac3aa237c567d8567f` is unchanged from the earlier audit. |
| [AccountCommands.py](https://github.com/izeberg/wot-src/blob/447437a25a2222a0d10dde96f65a20254d3a7d0d/sources/res/scripts/common/AccountCommands.py) | Native result constants, including unavailable `-10`, cooldown `-5`, rate-limit cooldown `-14`. |
| [battle_results_common.py](https://github.com/izeberg/wot-src/blob/447437a25a2222a0d10dde96f65a20254d3a7d0d/sources/res/scripts/common/battle_results/battle_results_common.py) and [random.py](https://github.com/izeberg/wot-src/blob/447437a25a2222a0d10dde96f65a20254d3a7d0d/sources/res/scripts/common/battle_results/random.py) | Required report field definitions retain the earlier audited blobs. |
| [Avatar.py](https://github.com/izeberg/wot-src/blob/447437a25a2222a0d10dde96f65a20254d3a7d0d/sources/res/scripts/client/Avatar.py) | Save and emit `onBattleResultsReceived(True, fullForm)` before acknowledgment. |
| [BattleResultsService](https://github.com/izeberg/wot-src/blob/447437a25a2222a0d10dde96f65a20254d3a7d0d/sources/res/scripts/client/gui/battle_results/service.py) | Posted-result callback retains reusable info, stats controller and result window. |

## Verification and live acceptance

Automated regressions use synthetic reports and controlled clocks. They cover
complementary merges, unknown outcomes, normalization rejection, restart,
account/region separation, corrupt hints, cooldown, unavailable backoff, queue
fairness, stale callbacks and the owned native/UI command bridge. Existing ledger,
financial, WN8, bonus, observer and session suites remain applicable.

For the real client acceptance check:

1. Install one active Session Stats package and record its version.
2. Record complete, partial and unknown counts before recovery. Open Battles and
   inspect one missing report's help, then try its **Retry result** in the garage.
3. Play a short Random Battle, leave before its result, restart, and let native
   recovery finish. Check the same battle and original timeline/session ownership.
4. Reconnect during recovery and check cooldown, late responses and a known native
   report opened by the stock UI. Confirm that other report consumers still work.
5. Record actual before/after unknown counts and remaining fixed reasons. If native
   WoT does not return a report, retain the gap and its diagnosis. Do not infer
   financial values or claim historical recovery from synthetic tests.

No real account ledger or running WoT client was available for this implementation.
Actual recovered battle count and server retention remain unmeasured.
