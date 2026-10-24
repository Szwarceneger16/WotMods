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
