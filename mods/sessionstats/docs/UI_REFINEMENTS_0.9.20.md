# Single-line captions and balanced wide tables in 0.9.20

Table captions stay on one line at every supported card width. A caption that
exceeds its available lane ends with an ellipsis instead of adding another
line to the row. Custom hover help displays the full localized caption after
500 ms, using the panel's existing tooltip surface. The ellipsis applies to
captions; XP, WN8 and financial figures retain their full values.

Wide aggregate cards, including the 720-logical-pixel preset, distribute spare
space to the performance table and numeric columns. The currency-caption lane
no longer absorbs the remaining card width while performance remains packed
against the left edge. Narrower cards retain their compact arrangement and the
readable fallback for figures that genuinely need more space.

The logical-width allocation from 0.9.19 remains the source of the finance
budget. Credit rows, shared Costs, financial headings and Bonds continue to
receive matching explicit column widths. Width redistribution does not depend
on remeasuring a resized native flex table during the same layout pass.

Both base and received credit rows, complete financial amounts, source arrows,
Min/Max actions and the shared settled cost remain available. These notes do
not claim live-client verification or a completed validation result.
