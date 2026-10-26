# Final independent review of PR #3

Review date: 2026-10-24. Baseline: `3aedc4a1a58f66e7a9c5b24799f6c80064267ac6`.

This follow-up checked the native UI/runtime boundary, delayed result ownership,
optional battle-entry metadata, staged intake and replay, journal recovery,
incremental summaries, configuration discovery/creation, and shared cache hooks.
The three confirmed findings below are corrected. This is not an assertion that
every state or possible conflict has been tested.

## Confirmed findings

| Priority | Trigger and impact | Correction and evidence |
| --- | --- | --- |
| P2 | The renderer emitted `page`, but `StatsWindow._handle_action` did not allow that command. Runtime-only and browser-only paging tests passed independently. In the native window, users could never leave the first 40 battles, vehicles or maps. | Permit `page` through the existing guarded bridge. The real runtime still validates the account, scope, group, page and period. New native-model-to-runtime tests traverse both directions for all nine scope/group combinations, verify disjoint rows and unchanged totals, and exercise stale windows, invalid requests and reset boundaries. |
| P2 | A cache request captured account A, then returned after login switched to B. Result normalization verified A, but the supplemental XP lookup consulted the current posted controller without checking the bundle's owner or battle. A foreign bonus could be saved to A with `xp_bonus_applied=True`, preventing ordinary raw readings from repairing it. A stale/mismatched bundle could cause the same issue on the active account. | Supplemental posted XP is consulted only for the active account and accepted only when the bundle's raw result matches both account DBID and arena ID. The original delayed result remains accepted by its own ledger. Regression tests reproduce the callback/login sequence, reject wrong/missing bundle identities, and retain valid bonus reconciliation for the current account. |
| P2 | `GameAPI.battle_context` protected vehicle display names but read the roster, compact descriptor and map metadata outside that boundary. A failing map-name/descriptor getter or temporarily unavailable roster aborted a verified random-battle beginning. Without a durable beginning, a later restart could lose the only pending-result recovery key. The runtime contained the exception, but skipped recording the observation. | Keep arena identity and mode checks authoritative; read optional vehicle/map attributes independently. Missing/failing optional values stay unknown and later observations can enrich them. Failure-injection tests cover all three previously unprotected paths and retain the unsupported-mode rejection. |

## Validation

Nine regression/control tests were added. Seven failed against the pre-fix source
(four assertion failures at the UI/XP boundaries and three entry-adapter errors);
the remaining two verify rejected/stale commands. All nine pass after correction.

- Local Python 3: all **584 mod tests** and **213 repository tests** pass.
- Hosted Python 2.7, browser, package and audit results are tracked on the PR for
  the exact published commit; they are not inferred from the local Python 3 run.
- No workflows, trusted validation scripts, storage format, config paths, package
  version, dependencies or release-asset layout changed in this follow-up.
- The full ledger, result revisions, totals and paging remain available. The
  correction restores native access to history pages; it does not trim history.

## Remaining validation limits

No live WoT client, Windows filesystem, XVM installation or large third-party mod
pack was exercised. Native doubles and failure injection verify Python behavior,
not the absence of native crashes. Complete branch/state coverage was not measured.

The existing performance limits in [HISTORY_PERFORMANCE.md](HISTORY_PERFORMANCE.md)
remain: the startup scheduler has a soft budget; individual filesystem flushes,
records, sorting and garbage collection can exceed it. Journal/intake maintenance
and long-term compaction need a separate design. Optional OpenWG footer resource
sharing and non-chaining third-party hooks retain the integration limits described
in [INDEPENDENT_SAFETY_REVIEW_PR3.md](INDEPENDENT_SAFETY_REVIEW_PR3.md).

Before treating the package as game-validated, check native paging with more than
40 rows, a battle/garage transition with delayed results, an account switch with
pending results, restart recovery, and startup with the intended mod pack.
