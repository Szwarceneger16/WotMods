# Per-battle mission progress

The adapter follows the Python client reference at
[`izeberg/wot-src`, commit `ed377b7bc5e8c232cf41bd0887bcfa0d75005fcb`](https://github.com/izeberg/wot-src/tree/ed377b7bc5e8c232cf41bd0887bcfa0d75005fcb).
All paths below are relative to `sources/res/scripts` in that reference.

## Common quests and Crucible stages

- `client/gui/battle_results/components/progress.py`, `QuestsProgressBlock.setRecord`,
  unpacks a result entry as `(groupBy, previous, current)`. The result dictionaries
  belong to the player's account or player's vehicle; teammate results are not read.
- `client/gui/battle_results/progress/progress_helpers.py`,
  `isQuestCompleted` and `packQuestProgressData`, establish the `bonusCount`
  completion comparison and wrap the two states using their recorded group key.
- `client/gui/server_events/conditions.py`, `Cumulativable.getProgressPerGroup`,
  returns `(current, target, earned, completed)` and handles capped counters and
  counters that reset after an award. `isCurrentProgress=True` is the native
  per-battle interpretation; subtracting the two raw counter values would be wrong
  for a completed repeating quest.
- `client/gui/impl/lobby/battle_results/missions_progress/common_battle_quests_progress.py`,
  `CommonBattleQuestsProgressPresenter`, uses the same helper with that flag to
  fill its `earned`, `current` and `total` model fields.
- The cumulative condition supplies its exact key and localized description.
  Verified implementations include `BattlesCount`, `CumulativeResult`,
  `VehicleKillsCumulative`, `VehicleDamageCumulative`, `VehicleStunCumulative`
  and `CumulativeSum`. Damage/stun event counts retain a generic counter unit;
  they are not presented as hit points or seconds.

The adapter checks that both result states actually contain a numeric counter
before calling the native helper. The helper itself supplies zero defaults for
missing values, which are inappropriate evidence for an unknown historical
result. An explicit unchanged pair can confirm no progress; an absent pair cannot.
An unrelated dictionary change or the presence of a mission in the catalog does
not establish objective progress.

The result's recorded group key is retained for grouped/per-vehicle conditions.
The adapter does not test old results against the vehicle currently selected in
the garage.

## Personal missions

- `client/gui/battle_results/components/progress.py` combines `PM2Progress`
  booleans with the mission's main/additional quest IDs to establish completion
  and honors. Unrelated technical booleans are not objective completion.
- `client/gui/server_events/personal_progress/formatters.py`,
  `PostBattleConditionsFormatter`, passes `PM2Progress[missionID]['current']`
  to `PostBattleProgressStorage` with `getConditionsConfig()`.
- `common/quest_progress.py`, `ValueProgress` and `CounterProgress`, establish
  explicit `value/state/goal` and `counter/state` payloads. The client storage and
  progress wrappers resolve the configured target and localized objective text.

No previous PM2 snapshot is established by this contract. Personal mission
current/target values therefore remain current/target values, without an invented
per-battle increment. Only progress IDs with explicitly supplied numeric values
or counters are included; storage-created default zero objects are ignored.
An absent dynamic goal remains absent. A copy of the mission configuration is
passed to native storage because storage augments its config dictionaries.

## Stored representation and validation

Mission rows optionally contain `progress_state` (`changed`, `unchanged`, or
`unavailable`) and at most 12 `objectives`. Each objective contains a bounded key,
unit, optional plain localized label, and the known subset of `before`, `after`,
`delta`, and `target`. Deltas may be negative for confirmed streak resets.
Unknown fields stay absent. Existing stored rows without these fields remain
valid and do not acquire fabricated zero progress. Result retries merge known
objectives without erasing earlier confirmed completion or honors.

Synthetic regression tests run on Python 3 and Python 2.7. Live client validation
is still required for mission-specific server payloads not represented in the
reference; unsupported or partial payloads remain explicitly unavailable.
