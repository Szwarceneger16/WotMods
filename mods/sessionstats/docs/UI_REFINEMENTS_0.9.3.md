# Clock, battle headers, page navigation and XP totals in 0.9.3

The 24-hour clock places midnight (00) at the top of the outer ring and noon
(12) at the top of the inner ring. Hours 1–11 remain outside and 13–23 inside.
Labels, pointer hit testing, hand length, keyboard adjustment and unavailable
choices use the same mapping. The 12-hour clock retains its original layout.

Battle headers reserve stable logical slots for outcome artwork/caption, map
artwork/caption and More/Less. Caption length, outcome kind and a missing image
cannot move neighboring columns. Compact captions reserve two lines; inline
captions have fixed bounds. The same source appearance template and fallback CSS
apply these rules. The panel bridge accepts compiled CSS up to 128 KiB, including
the current template above 64 KiB, and rejects oversized or malformed input. Synthetic checks cover all seven languages and both interface
scales, including long map names and changing More/Less captions.

Aggregate chronology shows both its boundary (first/last battle) and direction
(oldest/newest first) in words. Native font support for arrow glyphs is no longer
required. The selected caption can use two small lines inside its unchanged
control height; the expanded menu shows the full choice. The deterministic
filter-width threshold and pagination budget remain unchanged.

Explicit Previous/Next navigation retains ownership of the requested page divider
until its scroll position and layout settle below the pinned filter panel. Native
geometry and scroll setters can acknowledge in either order. Missing page
geometry and later layout changes are retried within a bounded lifetime; cached
and asynchronously loaded pages share this behavior. User scrolling, context
replacement, Back to top and teardown retire obsolete navigation. Automatic
infinite-scroll prepend anchors remain independent of explicit navigation.

The summary adds a centered total for the selected Base XP or Received XP series.
It uses the supplied sum, never the average multiplied by a guessed battle count.
The row keeps the same footprint when switching XP types, shows known zero as
zero and unavailable results as a dash, and carries its own partial-data coverage.
Min/Average/Max WN8 remains a three-column distribution without a sum.

Combined WN8 is like an account's overall WN8 restricted to this group of battles.
It returns to the combined damage, kills, spotting, defence and wins and compares
these with the expected results for the vehicles used. The distribution's average
instead averages each battle's separately calculated WN8. These operations need
not return the same rating; WN8 points themselves are never added to form an
overall score. Existing rating formulas and coverage rules remain unchanged.

Validation uses synthetic data and shipped code. Real WoT Gameface rendering and
input still require in-game confirmation.
