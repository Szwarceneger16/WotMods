# Spinner after restarting the game

Persistent waiting without a new battle was caused by treating unsettled journal
entries as current client activity. A battle-entry record can remain incomplete
after shutdown. If the client cache cannot supply its result, that entry does
not disappear on the next launch.

The garage button now indicates waiting for battles observed during the current
launch and actual result/XP-bonus processing. Older incomplete entries remain in
history and the recovery queue. The panel explains their count; Refresh retries
reads. Successful recovery follows normal settlement and deduplication. No schema
migration, history deletion or replacement of unknown values with zero is involved.

[OFFLINE_RESULT_RECOVERY.md](OFFLINE_RESULT_RECOVERY.md) describes recovery and
explicit statistical coverage. Activity is separate from completeness, which is
shown as received results divided by all recorded battles.

Tests cover restart without a new battle, unavailable cache, old-result recovery,
a new battle alongside backlog, manual refresh/reset, restarting the same runtime,
reconnection to an ongoing battle and old/current results without avatar-ready.

The issue was reproduced with synthetic fixtures. No private logs, screenshots,
account identifiers or player history were added to the repository.
