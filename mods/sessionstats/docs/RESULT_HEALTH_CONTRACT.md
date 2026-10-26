# Result-format health check — contract 0.2.6

## Checked data

`health.inspect_result(results, context=None, random_bonus_type=1)` performs no I/O
and imports no WoT client code. It returns `{code, path, expected, actual}` entries
without modifying the supplied result. The caller excludes transport errors and
"not ready yet" responses; waiting alone is not evidence of a format change.

Checks include:

- Root result type and `common`, `personal`, `avatar` containers, plus present
  `players`, `vehicles` and `avatars` containers.
- Adapter-required identifiers, outcome, WN8, XP, currencies, costs and deductions;
  types, nonnegative relevant values and supported team numbers.
- New field names in the envelope, common, avatar, vehicle and player records.
  The catalog is pinned to reviewed client definitions; the first post-update
  result does not automatically become a new baseline.
- Two-element `autoLoadCost` and three-element `autoEquipCost` /
  `autoEquipBoostersCost`, including bonds at the verified equipment-cost position.
- Vehicle identity and known directive-cost splits already included in automatic
  equipment resupply.

The catalog contains 20 common names, 62 avatar names, 249 combined vehicle-record
names and seven player names, combined from applicable `BATTLE_RESULTS`,
`BATTLE_PASS_RESULTS` and `random` categories. It does not require every field:
most are unused by the mod or conditional. Scalar-type validation covers fields
read by the adapter; other names serve new-field detection.

Changed damage, XP, outcome, player count, dynamic record identifiers, absent unused
optional fields and a list replacing an equivalent supported expense tuple do not
trigger alarms. Unused player/avatar/vehicle maps validate key types without assuming
positivity: client `convertToFullForm` does not guarantee positive keys for every
record. The player's accountDBID, arenaUniqueID and typeCompDescr must still be
positive. A missing deduction multiplier is an alarm only for a nonzero deduction;
a malformed present multiplier remains an incompatibility. Recognized results from
another account, replays and other supported modes are outside this random-battle
scope and excluded from its checks.

## Partial-result storage

An unused new field does not by itself prevent normalization of known data. Unknown
numeric types remain unknown. Changed-length currency tuples are not read using
old indexes because positional meanings cannot be confirmed. With known length and
positions, one unavailable amount does not erase other confirmed currencies.
Financial failures do not erase valid combat results or XP.

## Diagnostics

At most 32 entries are returned, with fixed text and inspected-field/record limits.
Entries contain schema paths and type/shape or consistency descriptions, without
statistic values, account/player/vehicle numbers, nicknames or full raw results.
Dynamic record keys become `<record>` or `vehicle`. Invalid, oversized and non-field
keys are masked.

The function sends no notifications, writes no files and does not determine pending
counts. Notifications, deduplication/rate limits, dedicated logging and button
activity belong to runtime.

## Limits

Changed numeric meaning with unchanged field names, types and valid ranges cannot
be established from payload alone. Checks do not prove unchanged internals of unused
nested extensions or detect removal of unused optional fields. Major protocol
changes still require comparison with a native battle report. New fields can be
harmless extensions; warnings indicate deviation from the verified contract, not
that all statistics are wrong.

## Sources read on 2026-10-21

Shared public `izeberg/wot-src` mirror commit:
`5e721e36891c80d8d51a431164960c863641ee63` (client 2.4.1.5493).
These verify implementation rather than declare a stable SDK.

- [Field and expense definitions](https://github.com/izeberg/wot-src/blob/5e721e36891c80d8d51a431164960c863641ee63/sources/res/scripts/common/battle_results/battle_results_common.py),
  blob `a8476aed85f0cfce21e6a3c9fb267e6cc533ae21`.
- [Category-based schema assembly](https://github.com/izeberg/wot-src/blob/5e721e36891c80d8d51a431164960c863641ee63/sources/res/scripts/common/battle_results/__init__.py).
- [Random-mode extension assignment](https://github.com/izeberg/wot-src/blob/5e721e36891c80d8d51a431164960c863641ee63/sources/res/scripts/common/battle_results/battle_results_constants.py).
- [Additional random-mode field](https://github.com/izeberg/wot-src/blob/5e721e36891c80d8d51a431164960c863641ee63/sources/res/scripts/common/battle_results/random.py),
  blob `60149af5c3da7728bc294a5a75d9f77aacfea9a4`.
- [Full envelope and dynamic record maps](https://github.com/izeberg/wot-src/blob/5e721e36891c80d8d51a431164960c863641ee63/sources/res/scripts/client_common/shared_utils/account_helpers/BattleResultsCache.py),
  blob `f2f88011e792c06d332f73ac3aa237c567d8567f`, function `convertToFullForm`.
- [Section names used by client UI](https://github.com/izeberg/wot-src/blob/5e721e36891c80d8d51a431164960c863641ee63/sources/res/scripts/client/gui/battle_results/settings.py),
  blob `63e443d35b0f11a7c5fa3caf172b401792949e5f`.
