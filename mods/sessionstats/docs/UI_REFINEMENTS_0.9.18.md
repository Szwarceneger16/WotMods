# Adjacent aggregate tables and compact headers in 0.9.18

Ordinary vehicle and map cards are 560 logical pixels wide. Their previous
performance and finance flex bases required at least 300 + 296 pixels before
insets, so finance wrapped below performance. The single-battle adjustment in
0.9.17 did not address these aggregate cards.

Aggregate tables now measure explicit text boxes for Min, Average and Max,
including their source arrows and spacing. Average does not reserve an arrow
lane. The performance table receives the width needed by its figures and
caption lane; finance receives the remaining space. Ordinary vehicle, map and
tier cards keep both tables on one row without reducing their figure fonts.
Adjacent performance rows retain their natural height instead of stretching
to the height of the finance table.

The aggregate finance layout can retain a dedicated currency-caption column at
ordinary widths. Narrower financial tables still use their compact caption
layout. Very narrow cards and unusually wide figures retain the stacked,
full-number fallback. Both base and received credit rows and the single shared
cost value remain available.

An aggregate header without an additional sorting-result block no longer forces
its statistics onto a separate row at ordinary card widths. Headers with a
sorting result retain the existing wrapped layout when needed.

Regression coverage includes both timeline lanes, default vehicle/map/tier
widths, full signed six-digit credit totals, Min/Max source actions, missing base
credit values, large figures and both interface scales. An explicit legacy-flex
control reproduces the old vertical-table layout so the adjacency and height
checks can reject it. Native Gameface rendering still requires an in-game check.
