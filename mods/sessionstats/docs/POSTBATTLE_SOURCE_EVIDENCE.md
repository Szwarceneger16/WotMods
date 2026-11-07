# Post-battle WN8 integration

The optional integration targets the random post-battle Gameface document. It
does not replace a native model, statistic, resource, click handler or window.

## Native result ownership

Reviewed [native view source](https://github.com/izeberg/wot-src/blob/ed377b7bc5e8c232cf41bd0887bcfa0d75005fcb/sources/res/scripts/client/gui/impl/lobby/battle_results/random_battle_results_view.py)
at client-script commit `ed377b7bc5e8c232cf41bd0887bcfa0d75005fcb`:

| Source | Verified contract |
| --- | --- |
| `gui/impl/lobby/battle_results/random_battle_results_view.py` | `RandomBattleResultsView` is a `ViewComponent` using `R.views.mono.post_battle.random()`. Its public `arenaUniqueID` property comes from the view context. |
| Same class, `_onLoading` | Native loading and result packing run before the optional child is attached. |
| Same class, `_finalize` | The native arena identifier is cleared before parent teardown; the adapter therefore captures it when attaching. |
| `gui/impl/lobby/battle_results/submodel_presenters/battle_efficiency.py` | The personal-efficiency model belongs to this result, rather than an account's latest battle. |

The runtime provider binds the account on its first known lookup. Later refreshes
use that same account and captured arena identifier. An account change cannot
rebind an existing result view. Neither identifier enters the Gameface payload.

## DOM and spinner

Reviewed client assets at
[`3605bd36c53d10c16be5d93f5414aa5fd129e84e`](https://github.com/Kurzdor/wot.assets/tree/3605bd36c53d10c16be5d93f5414aa5fd129e84e):

| Asset | Verified contract |
| --- | --- |
| `gui/gameface/_dist/production/mono/post_battle/random/bundle.js` | The bottom native statistics use `PersonalEfficiency_totalEfficiencyTable_*` with a `TableHeader` containing a `TableRow`. |
| `gui/gameface/_dist/production/mono/post_battle/chunks/lib.js` and `lib.css` | These table elements expose their `data-name` attributes and use supported div/flex layout. |
| `random/bundle.js` and `random/random.css` | A result with no efficiency rows renders `PersonalEfficiency_messagesPanel_*` inside `Overview_*` instead; our fallback appends a normal-flow status beneath its existing text. |
| `gui/maps/icons/library/spinner.png` | The native 24 × 24 spinner image is rendered at 18rem in the owned value slot. |

The primary selector is scoped to the personal-efficiency table; another team or
financial table cannot receive the WN8 cell. An optional document observer and
one coalesced placement retry after each model event handle native React
recreation. The retry also works without `MutationObserver` and creates no
recurring polling loop. Only owned nodes and exact owned subscriptions are removed.

## Display states and verification

`WN8` stays visible in every supported state. A pending result has a spinner only
in the value slot; a ready result displays the rounded per-battle value, including
zero. Missing or unsupported data displays a dash. The runtime bounds pending
work to 30 seconds; the UI creates no cache requests or polling timers.

Python lifecycle tests use strict Wulf doubles. Browser tests use the shipped
JavaScript/CSS, synthetic models and the verified DOM structure. Those checks do
not constitute a live-client compatibility test.
