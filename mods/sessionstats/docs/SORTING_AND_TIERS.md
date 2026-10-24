# Result sorting and tier breakdown

## Delivery stages

1. Add global result ordering before native pagination, including metric/statistic/direction and chronological ordering.
2. Add the Tiers breakdown to every session scope and apply the same ordering contract.
3. Add compact localized select controls, verify their layout and interactions, and run the package checks.

Each stage is committed to the same pull request so work can resume from a published checkpoint.

## Requested behavior

- Place the chronological select between Previous and Next.
- Place three selects on the following row: statistic (Min/Average/Max), metric (Off/Base XP/Received XP/Credits/WN8), and direction (Ascending/Descending).
- With metric sorting off, order chronologically, newest or oldest first.
- Sort the whole selected scope before pagination; changing ordering returns to page one.
- Provide the same controls for Vehicles, Maps, Battles and Tiers.
- Keep the sorting row within the panel width in all supported languages.

## Implementation notes

- Tiers uses the existing incremental totals and expected-value WN8 calculations. Tier XI is displayed as XI; missing tier metadata has a separate unknown group.
- Credits sorting uses net earnings per battle. It compares the selected minimum, average or maximum, rather than the sum across a group.
- WN8 sorting uses the per-battle WN8 series, not the period WN8 rating.
- Group date ordering compares the earliest battle for oldest first and the latest battle for newest first. Equal metric values use that chronology, then the stable group ID.
- Sorting choices are independent per account, scope and grouping for the running process. They do not alter saved battle records or the persistent data schema.
- Native requests require the current account and period ID. A successful sort returns to page one; corrected results invalidate cached ordering.
- Gameface does not support the native HTML select element. The local dropdowns use supported button/div elements, listbox semantics, arrow/Home/End navigation, Enter/Space selection and Escape dismissal. No runtime UI dependency is added.
- The source appearance template controls all colors and corner radii, including the new dropdowns.

Renderer evidence: https://coherentlabs.github.io/GameUIComponents/en/components/form-control/#select
