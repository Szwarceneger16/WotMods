# Native personal-operation state

The collector follows the EU client APIs in the public decompiled client source
at commit `447437a25a2222a0d10dde96f65a20254d3a7d0d`. These references describe
game semantics, not an account-specific snapshot or an assertion that the mod
has been tested in a live client.

## Remembered selection and campaign activation

- [QuestsProgressRequester.py](https://github.com/izeberg/wot-src/blob/447437a25a2222a0d10dde96f65a20254d3a7d0d/sources/res/scripts/client/gui/shared/utils/requesters/QuestsProgressRequester.py):
  `PersonalMissionsProgressRequester.getPersonalMissionProgress` sets `selected`
  from the stored selected-quest IDs. `getActiveCampaigns` and `isCampaignActive`
  read campaign activation separately. A selected quest can therefore belong to
  a campaign that is currently inactive.
- [event_items.py](https://github.com/izeberg/wot-src/blob/447437a25a2222a0d10dde96f65a20254d3a7d0d/sources/res/scripts/client/gui/server_events/event_items.py):
  `PersonalMission.isInProgress` returns the stored `selected` flag.
  `PMOperation.isActive` tests for selected quests. During `updateProgress`, an
  operation is paused when its campaign is inactive and the operation has been
  started. Neither stored selection nor started progress alone establishes
  current campaign activation.
- [personal_missions_cache.py](https://github.com/izeberg/wot-src/blob/447437a25a2222a0d10dde96f65a20254d3a7d0d/sources/res/scripts/client/gui/server_events/personal_missions_cache.py):
  `isCampaignActive(branchName)` is the public campaign activation check.

The exported `selected`, `campaignActive`, `paused` and `disabled` states remain
separate. `active` is true only when selection and campaign activation are both
explicitly true and the pause/disabled checks explicitly return false. Missing
or failing APIs produce null state, which never becomes a true active flag.
For a mission, operation pause/disable state is also respected.

## Campaign, operation and chain hierarchy

- [potapov_quests.py](https://github.com/izeberg/wot-src/blob/447437a25a2222a0d10dde96f65a20254d3a7d0d/sources/res/scripts/common/potapov_quests.py):
  `PQ_BRANCH` supplies branch names and campaign relationships. The collector
  uses the running client's `PM_BRANCH.ALL_NAMES`; no current campaign, vehicle
  reward, or player progress is hardcoded.
- `PMOperation` in `event_items.py` exposes public campaign/branch IDs, localized
  names, icon IDs, lock/availability state, chain names, classifiers and quests.
  For points-based branches it exposes cumulative operation points and their
  native target. Legacy award-list branches do not acquire a fabricated points
  progression.
- `PersonalMissionsCache.getActualQuests` selects the first quest in each chain
  that is not fully completed, falling back to the final quest when the whole
  chain is completed. This is independent of unlocked/selected quest filtering.
- [main_view.py](https://github.com/izeberg/wot-src/blob/447437a25a2222a0d10dde96f65a20254d3a7d0d/sources/res/scripts/client/gui/impl/lobby/personal_missions_30/main_view.py):
  `__fillActualMissionsModel` uses `getActualQuests` for the operation's summary
  cards. `__updateAllMissions` keeps the complete mission lists in a separate
  view. `__fillAdditionalMissionsModel` handles daily and weekly point sources
  separately.

The optional `categories.personal.operations` catalog includes locked and
unselected operations even when no flat mission passes the previous availability
filter. Operation `iconKey` uses a bounded semantic `operation:<operation ID>`
key. Native `getIconID` returns a tile key, which is mapped to embedded artwork
by the Site rather than assumed to be a numeric identifier. Chain `completed` counts primary-completed
quests; `total` is the native chain length. `currentQuestId` and `actualQuestIds`
come from the native actual-quest result and remain null when that API is
unavailable. The collector does not derive the current mission by adding one to
the completed count.

Actual summary quests are placed before the compatible flat list, with the
currently active operation first, so the existing mission cap cannot be consumed
by the historical selected/available list before the current summary is emitted.
The catalog is bounded to 64 operations and 16 chains per operation; mission
details retain the existing 160-item cap. `operationsStatus` distinguishes a
complete, partial, pending or unavailable catalog.

## Older campaigns and navigation

- [campaign_selector_view.py](https://github.com/izeberg/wot-src/blob/447437a25a2222a0d10dde96f65a20254d3a7d0d/sources/res/scripts/client/gui/impl/lobby/personal_missions_30/campaign_selector_view.py):
  the campaign selector retains the first two campaigns alongside the newer
  operations. Its selection action routes old operations through
  `showPersonalMissionOperationsPage` and newer operations through
  `showPersonalMissionMainWindow`. An old stored selection is not evidence that
  the newer campaign screen is currently displaying that operation.

Only native game identifiers, localized display text, bounded counts and
explicit state fields are exported. Native objects, account identifiers,
arbitrary exception messages and private configuration are not copied.
