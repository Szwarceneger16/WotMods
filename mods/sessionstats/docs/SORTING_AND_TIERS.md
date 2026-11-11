# Result sorting and tier breakdown

## Delivery stages

1. Add global result ordering before native pagination, including metric/statistic/direction and chronological ordering.
2. Add the Tiers breakdown to every session scope and apply the same ordering contract.
3. Add compact localized select controls, verify their layout and interactions, and run the package checks.

Each stage is committed to the same pull request so work can resume from a published checkpoint.

## Requested behavior

- Place the ordinary date/tier select between Previous and Next.
- Place direction, metric and statistic controls beside pagination when they fit, or on the following row in a narrow panel.
- With metric sorting off, order chronologically, newest or oldest first. Tiers also offers highest/lowest tier first in this same selector and defaults to highest first.
- With metric sorting on, disable and visibly dim the ordinary ordering selector, including its label and arrow; use Ascending/Descending for the selected metric. The saved ordinary preference returns when metric sorting is off.
- Sort the whole selected scope before pagination; changing ordering returns to page one.
- Offer recorded battle count sorting only for Vehicles and Maps. Offer win-rate sorting in every grouping. Hide Min/Average/Max for counts, win rate and individual Battles.
- Keep the sorting row within the panel width in all supported languages.

## Implementation notes

- Tiers uses the existing incremental totals and expected-value WN8 calculations. Tier XI is displayed as XI; numeric tier sorting places XI above IX, and missing tier metadata remains last in both tier directions.
- Credits sorting uses net earnings per battle. It compares the selected minimum, average or maximum, rather than the sum across a group.
- WN8 sorting uses the per-battle WN8 series. During active WN8 ordering, the existing large WN8 figure and label show the selected Min/Average/Max, with an orange mark; its text and card border follow that displayed rating. With metric sorting off or another metric selected, the headline returns to whole-period WN8. No duplicate WN8 caption is added below the name.
- Advanced sorting marks an existing value wherever its meaning matches the exact sort key: the selected XP distribution cell, a battle net-credit amount, or the existing battle-count/win-rate headline. A compact caption remains only when the exact per-battle aggregate is absent, such as aggregate net-credit Min/Average/Max; the finance table continues to show totals.
- Win rate is wins divided by known Random Battle outcomes, matching the displayed percentage. Losses and draws count in the denominator; unresolved outcomes do not become losses. Individual Battles sort wins as 100%, losses/draws as 0%, and unknown outcomes last in both directions. A compact percentage is shown only while this otherwise absent individual-battle metric is selected. Win rate has no Min/Average/Max statistic.
- Count sorting uses all recorded battles, including pending results. For a card showing 12/14 received results, the count sort value is 14. Counts have no minimum, average or maximum statistic, and no duplicate count caption is added to the card.
- Group date ordering compares the earliest battle for oldest first and the latest battle for newest first. Active metric ties always use the latest battle first, then the stable group ID; changing a saved date preference cannot reorder an active metric.
- Sorting choices are independent per account, scope and grouping for the running process. They do not alter saved battle records or the persistent data schema.
- Native requests require the current account and period ID. A successful sort returns to page one; corrected results invalidate cached ordering.
- Gameface does not support the native HTML select element. The local dropdowns use supported button/div elements, listbox semantics, arrow/Home/End navigation, Enter/Space selection and Escape dismissal. No runtime UI dependency is added.
- The source appearance template controls all colors and corner radii, including the new dropdowns.
- Wide sorting uses a compact inset switch in a rounded button frame. Narrow panels retain Off in the metric dropdown.

Renderer evidence: https://coherentlabs.github.io/GameUIComponents/en/components/form-control/#select

List totals use `groups.*.total` messages without a fixed ordering caption. Translation catalogs are now internal; old external templates are ignored.
