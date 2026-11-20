# Bonus amounts, selected-language hints and summary navigation in 0.9.12

The premium account bonus row shows added amounts rather than account
multipliers. Each known contribution is derived from its reported original
amount and the corresponding premium factor, with native-style integer rounding.
For example, 13,228 credits at 150% add 6,614 credits; 225 XP at 150% add 113 XP;
11 Free XP at 150% add 6 Free XP. Recorded crew XP originals use their own premium
factor. Existing known originals can reconstruct a historical contribution;
missing originals remain unavailable. Already received totals, which can include
other bonuses, are never used as a substitute original amount.

Vehicle role names and explanations follow the mod's selected language, across
English, Polish, German, French, Spanish, Russian and Ukrainian. Missing catalog
translations fall back to English. A cached description from the game's client
language cannot override an explicit mod language selection. Unknown future roles
retain a localized vehicle-class label rather than an unrelated cached
paragraph in another language.

The filter section displays an orange-red warning when received results in the
selected period lack the chosen metric. Its coverage check applies to fields
such as Base XP, received XP, WN8 and the independent credit income, cost and net
series. Missing pending battle reports alone do not trigger this field-coverage
warning. The active sorting caption and number remain centered within the
existing gold-marked slot.

Black WN8 figures retain bold black text and their muted translucent backing.
The light text outline and the backing's shadow ring are removed; other WN8
palette bands keep their existing paint. Performance rows distribute spare card
height evenly, while financial cells no longer reserve an empty source-action
row when no source action exists.

Summary extrema arrows can select and reveal a source battle on a later page
even when **Battles** is already the current tab. An accepted native selection
starts the feed at the target page instead of reusing the previous visible page.
Account, period, request and DOM ownership checks continue to reject stale work.
This also covers full-history Timeline ranges and exact Min/Max source results.

Regression fixtures use synthetic records. Browser checks exercise the shipped
UI, while the original Gameface renderer still needs an in-game visual check.
