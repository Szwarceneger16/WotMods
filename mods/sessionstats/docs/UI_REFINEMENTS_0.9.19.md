# Native finance column allocation in 0.9.19

Version 0.9.18 measured the financial table immediately after changing its flex
allocation. The reported in-game overflow is reproduced when that measurement
still describes the previous table width: the currency caption consumes the
space intended for Income, Costs and Net. The compact aggregate arrangement
therefore needs an explicit shared width budget for its financial table and
every column inside it.

The finance budget now comes from the assigned logical card interior minus the
performance table's allocation. The financial table receives that complete
fixed flex width. Its caption, Income, shared Costs and Net columns receive
explicit widths and flex bases from the same budget. The financial headings
and Bonds row receive the matching allocation; compact captions use the same
three numeric lanes. Column assignment walks the direct child rows rather than
using a comma-separated selector containing `:not()`.

The regression fault model retains the obsolete table measurement after a flex
resize. Under the previous calculation, it reproduces a 357-pixel caption
inside a 302-pixel financial table, collapsing numeric columns to zero and
pushing figures outside the table. The corrected allocation avoids that stale
measurement: the sum of the assigned columns stays within the financial
content width. This model is separate from a live Gameface verification.

The adjacent aggregate layout, full credit figures, both base and received rows,
shared settled costs and Min/Max source actions are retained. Very narrow cards
and unusually wide figures continue to use the readable fallback arrangement.
No live-client verification is claimed for this version in these notes.
