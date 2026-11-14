# Stable filters, chronology and group WN8 in 0.9.2

The filter row has one deterministic logical width threshold. Its budget includes
metadata, pagination, every advanced control (including Statistic even when
hidden), spacing and loading activity. Selecting another group or metric cannot
move the breakpoint. Layout never temporarily changes visible classes to measure
a candidate row. Wrapped rows remain centered. Narrow panels show a selectable,
diagonally hatched Off option; it is distinct from a disabled control.

Shrinking applies the wrapped layout immediately. Promotion waits for 120 ms of
quiet width or eight animation frames, and finishes once the resize gesture ends.
One owned animation-frame ticket reads the newest width; stale/retired tickets
cannot mutate the view. The measured panel content width is independent of the
current filter layout. Mode changes update control presentation without rebuilding
result cards or changing the feed scroll position.

Aggregate chronology has four choices: First battle ascending/descending and
Last battle ascending/descending. Existing oldest/newest preferences retain their
original meanings (first ascending / last descending). Individual Battles use
only their own timestamp; Tiers also retains both tier orders. Metric ordering
dims the ordinary selector and uses its own direction. Metric ties do not depend
on the inactive date preference. Expanded map/vehicle histories follow the saved
date direction, including additional pages and while metric sorting is active.
The exact chronology participates in history request/cache identity, so delayed
replies from an earlier selection cannot replace the current list.

**Combined WN8** is recalculated from summed actual battle values and summed
expected vehicle values. WN8 is nonlinear; this group rating generally differs
from the arithmetic average of individual-battle ratings. The table below shows
those individual ratings' minimum, arithmetic average and maximum. The existing
card information button explains the distinction. Active WN8 sorting replaces
the large headline with the exact selected distribution value and highlights it.

Compact battle headers place the outcome and map captions below their respective
images. The visible map caption shares the existing local hover preview; very
wide actual cards use inline captions. Asset selection/compositing and safe local
resource validation are unchanged.

For automatic client date/time sources and explicit configuration, see
[Client date and clock formatting](CLIENT_DATE_TIME.md).

Tests use synthetic data and the shipped sources: actual-source layout ownership,
real-frame resize bursts at both interface scales, unchanged card nodes/scroll,
selectable Off hatching, four chronology modes and stale history replies,
localized combined-rating labels, native date-resource stubs and explicit overrides.
Native WoT Gameface behavior still needs in-game confirmation.
