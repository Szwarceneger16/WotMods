# Layout refinements in 0.9.5

The summary gives the Base XP and Received XP totals explicit caption/value
rows. Their coverage stays with each value, and Free XP/WN8 coverage follows
in a separate normal-flow row. Native flex intrinsic-height differences cannot
place the footer across the totals.

Expanded battle details use two mission columns when the mission block can fit
two readable cards. Narrower blocks retain one column. The bonus resource table
keeps its numeric columns, and mission source order is preserved across resize.
This uses explicit flex rows instead of requiring CSS grid support.

Map hover frames use the reviewed proportions of recognized local artwork
categories. Previously, the popup copied the thumbnail shape while `contain`
fitted a differently shaped loading picture, producing dark side bands. Loading
photos use the reviewed 8:5 default frame and fill it without distortion; unusual
photo proportions may crop at the edges. Tactical/default-map previews remain
square and show the complete image. Small-image and unknown-branch fallbacks
retain containment. Existing local-path validation remains in force.

Black WN8 numbers keep their light, zero-blur edge at a finer width. WN8 captions
retain normal interface text rendering, and other rating colors are unchanged.

Sorting controls and aggregate headline values use stable logical slots. A
highlight changes decoration, not padding or alignment. Inapplicable statistic
choices retain their layout slot while remaining unavailable to pointer and
keyboard interaction. The existing filter width budget, debounce and owned
rendering callbacks remain unchanged.

Regression checks use synthetic records, translated labels and both interface
scales, including native-style intrinsic-size failures and metric changes at a
fixed window width. Native WoT Gameface appearance still needs in-game checking.
