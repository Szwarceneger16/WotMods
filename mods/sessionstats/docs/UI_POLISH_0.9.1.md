# Battle cards, sorting and date choices in 0.9.1

Battle cards retain the verified World of Tanks Victory, Defeat and Draw artwork.
These source images contain a baked-in fade. The UI composites the same local
texture in a fixed-size opaque outcome frame to strengthen it without altering
the game files or relying on unsupported native CSS filters. The outcome text
remains visible, including when an optional game texture is unavailable.

A separate map thumbnail appears beside the result. It is resolved from the
battle's saved map identifier and uses the same local-artwork validation and
hover/focus preview as Maps. The `maps.preview_mode` configuration also applies
here. Leaving the miniature closes its preview.

Win-rate ordering is available for Vehicles, Maps and Tiers. Battles no longer
offers that metric; stale callbacks cannot request it, the backend rejects it,
and legacy selections fall back to ordinary chronology. A selected card figure
and its caption are centered within the orange frame. Shared WN8 distribution
captions remain neutral, while each Min/Average/Max value keeps its own rating
color. WN8 captions for a single value keep that value's color.

When filters need multiple rows, each row is centered in the actual panel rather
than the full game viewport. The loading indicator retains its reserved space.
The fitting single-row layout retains the adjacent sorting switch.

Unavailable calendar dates, months, years and clock choices use explicit gray
text, fill and borders, with semantic disabled states and callback guards.
They do not depend on low opacity to communicate availability. Selecting today
with a later clock time inherited from a past date clamps to the current valid
minute, including the strict opposite From/To bound. Valid past-date times are
preserved; a day with no valid interval cannot be selected. Future clock choices
remain visibly unavailable, and Apply and the backend validate the exact epoch.

Browser regressions use synthetic histories and frozen times at 100% and 200%
interface scale. Source-level checks exercise unavailable ranges and stale sort
callbacks without depending on Chromium. Native game-resource loading and input
still require a live Gameface check; the browser bridge uses controlled doubles.
