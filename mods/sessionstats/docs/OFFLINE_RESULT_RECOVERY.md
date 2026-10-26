# Battle results after client shutdown

## What counts

Battle entry is persisted with battle/account/region identity and period membership.
An entry alone is neither a victory, a defeat nor a numeric result. Received data
is required for settlement. A recognized outcome can contribute confirmed statistics
even while other fields remain incomplete. Missing fields do not become zero.

Entry immediately saves available identifying metadata: time, map identifier/name,
and the player's vehicle identifier/name/tier/class. Names come from the vehicle
descriptor and client arena type. Saving waits for neither battle end nor shutdown.
If the arena is not ready, later avatar events and five-second polls fill missing
fields in the same entry. Identical reads do not produce further disk writes.
An optional vehicle-name failure does not block saving the battle entry.

After restart, known map/vehicle names remain visible with an unknown outcome and
dashes for missing statistics. Player lists, nicknames and raw arena context are
not saved. This cannot reconstruct names an older version never preserved; later
client metadata or results may fill them.

Summary/group coverage shows received results against all recorded battles, for
example `20 / 21`. The missing battle remains in the list with an unknown outcome.
WN8, XP and financial coverage use every recorded battle as the denominator. Win
rate and averages use confirmed data; the panel explicitly marks incomplete scopes.
A result received the next day fills the original battle and period without creating
a duplicate or assigning it to the new launch.

## Client and server reads

Verified client 2.4.1.5493, commit `5e721e36891c80d8d51a431164960c863641ee63`:

- [BattleResultsCache.get](https://github.com/izeberg/wot-src/blob/5e721e36891c80d8d51a431164960c863641ee63/sources/res/scripts/client_common/shared_utils/account_helpers/BattleResultsCache.py)
  first checks a local file, then uses native `CMD_REQ_BATTLE_RESULTS` if absent.
  This is the client's own path, without custom HTTP/API, tokens, an external
  service or a process running after game shutdown.
- The same cache constructor clears the standard result directory. A client cache
  file alone is not a durable mod archive.
- On receiving a stream, the client writes its cache, invokes the callback and then
  sends `CMD_BATTLE_RESULTS_RECEIVED`. An additional observer stores normalized
  mod data before the original callback and acknowledgment. It also covers requests
  made by the game interface or another mod when our normal result event is missing.
- [BattleResultsGetter](https://github.com/izeberg/wot-src/blob/5e721e36891c80d8d51a431164960c863641ee63/sources/res/scripts/client/gui/shared/gui_items/processors/common.py)
  uses the same `battleResultsCache.get` method for the WoT interface.

The observer preserves arguments, return values and the original consumer. Observer
failure does not block that consumer. Mod-owned requests are not processed twice.
Responses retain the account/lifecycle captured on dispatch; old-runtime callbacks
cannot modify a new runtime. Removing the observer does not overwrite a wrapper
installed later by another mod.

## Recovery queue

Login loads every preserved incomplete entry. Requests remain serial, prioritizing
current battles and the earliest due attempts. An old error should not continually
precede untried results. Shared-cache cooldown, an unready account and disconnection
do not increase a battle's exponential backoff; request limits receive a longer
pause. Ordinary read errors retain the entry and bounded retries.

A valid stream arriving after our request expires can still fill unknown data,
but cannot change newer confirmed values or remove a newer request's token. This
fill uses `reconcile=False`. Diagnostics contain states and known client codes,
without account/battle numbers, raw responses or arbitrary unknown numeric values.

## Limits and verification

The mod does not run after client shutdown. Unsettled battles wait for the next
login and then use the native server-read path above. Client code does not guarantee
server retention time. If WoT no longer supplies a result, complete recovery cannot
be promised. The entry stays an explicit gap; it is not replaced by a guessed defeat
or a credit-balance difference affected by unrelated transactions.

Synthetic transport tests cover shutdown before battle end, recovery after login
into a new launch, original-period membership, deduplication, native reads without
events, writes before consumers, failures/other-mod wrappers, account changes,
cooldown, retry order and valid late streams. They do not emulate server retention
or replace a live WoT test. Separate battle-entry tests cover saving before shutdown,
recognizable entries without results after restart, late metadata, no duplicate
writes and exclusion of private context fields.
