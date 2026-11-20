# Permanent battle links and native display corrections in 0.9.9

Minimum and maximum values are permanent source-battle actions in the overview
and aggregate Vehicles, Maps and Tiers cards. XP and WN8 use the numeric value
itself as a readable, keyboard-focusable button. Compact credit cells provide
explicit Min/Max actions; their tooltips include the exact extreme value and
battle. References cover the selected period before pagination and do not depend
on the sorting metric. Average and All never invent a responsible battle.
Account, scope, period, revision and live DOM ownership still protect navigation.
The former Source battle date and header arrow are removed. A reserved result
slot can still show a selected credit Min/Avg/Max value when the finance table
shows its All total, preserving a stable card footprint.

Credit sorting now offers base income, received income, base net, received net
and actual costs. Each has Min/Avg/Max/All where meaningful and independent
known-value coverage. Raw `originalCredits` supplies base income before bonuses,
analogous to the existing raw `originalXP` base metric. Received income retains
the verified settled-credit calculation. Both net metrics subtract the same
actual repair/ammunition/equipment costs. Base is not the native counterfactual
account-without-premium subtotal, which requires replaying all bonus records.
Older saves do not contain base credit earnings and cannot recover them by
premium-factor division. They retain received statistics and show base as
unavailable until an actual result supplies it; zero remains a valid amount.
Legacy `credits_gross`/`credits_net` preferences remain received aliases.

The compact finance table compares Base and Received credit totals and preserves
bond/gold totals. Actual costs apply to both credit variants. Its permanent
source actions have metric-specific owners, so a total cannot masquerade as an
average or be linked to a winner selected for a different metric.

Class artwork uses the original client `24x24_metal` family at its full 24 px
canvas. Elite laurels follow the live inventory item's actual `isElite` state,
including state changes, rather than vehicle name or class guesses. Role icons
remain separate and keep their original descriptions. Native textures are
referenced locally and are not copied into the distribution.

The footer chart uses the native 22 px ink height and shares its vertical center
with WN8. Busy processing replaces the chart bars with a 16 px circular spinner
in the same position; its 44 by 36 px control footprint does not change. The old
default spinner radius 5 migrates to 8; other customized radii remain unchanged.
Headline value boxes center their content vertically, including two-line known
and observed battle counts. Regression coverage includes grouped three-, four-,
five- and six-digit counts in all seven interface languages and both scales.

Checks use synthetic records and generated artwork. Native class textures were
inspected separately; live WoT Gameface visual verification remains necessary.

Credit semantics were checked against the pinned 2.4.1.1 client sources:
[replay economics](https://github.com/izeberg/wot-src/blob/447437a25a2222a0d10dde96f65a20254d3a7d0d/sources/res/scripts/client/gui/battle_results/reusable/economics_records.py)
and [money details](https://github.com/izeberg/wot-src/blob/447437a25a2222a0d10dde96f65a20254d3a7d0d/sources/res/scripts/client/gui/battle_results/components/details.py).
