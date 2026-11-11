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
- Offer recorded battle count sorting only for Vehicles and Maps. Hide Min/Average/Max for counts and individual Battles.
- Keep the sorting row within the panel width in all supported languages.

## Implementation notes

- Tiers uses the existing incremental totals and expected-value WN8 calculations. Tier XI is displayed as XI; numeric tier sorting places XI above IX, and missing tier metadata remains last in both tier directions.
- Credits sorting uses net earnings per battle. It compares the selected minimum, average or maximum, rather than the sum across a group.
- WN8 sorting uses the per-battle WN8 series, not the period WN8 rating. The card shows the selected per-battle sort value explicitly beside its metadata, so it can be compared with the unchanged whole-period rating.
- Count sorting uses all recorded battles, including pending results. For a card showing 12/14 received results, the count sort value is 14. Counts have no minimum, average or maximum statistic, and no duplicate count caption is added to the card.
- Group date ordering compares the earliest battle for oldest first and the latest battle for newest first. Active metric ties always use the latest battle first, then the stable group ID; changing a saved date preference cannot reorder an active metric.
- Sorting choices are independent per account, scope and grouping for the running process. They do not alter saved battle records or the persistent data schema.
- Native requests require the current account and period ID. A successful sort returns to page one; corrected results invalidate cached ordering.
- Gameface does not support the native HTML select element. The local dropdowns use supported button/div elements, listbox semantics, arrow/Home/End navigation, Enter/Space selection and Escape dismissal. No runtime UI dependency is added.
- The source appearance template controls all colors and corner radii, including the new dropdowns.
- Wide sorting uses a compact inset switch in a rounded button frame. Narrow panels retain Off in the metric dropdown.

Renderer evidence: https://coherentlabs.github.io/GameUIComponents/en/components/form-control/#select

List totals use `groups.*.total` messages without a fixed ordering caption. Translation catalogs are now internal; old external templates are ignored.
