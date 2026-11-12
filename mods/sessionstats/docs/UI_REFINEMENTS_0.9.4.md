# Display and language corrections in 0.9.4

Active sorting uses a neutral dark fill (`colors.sort_active_background`) with
the existing accent edge. WN8 figures retain rating colors and numeric outlines;
WN8 captions have no numeric halo, and black/unavailable captions use the normal
configured label color. Shared distribution labels remain neutral. Mixed nested
history text separates the caption from its numeric value.

Filter rows center their actual visible fields, including the combined pager and
sorting strip on wide windows. The deterministic full row budget and resize
debounce remain unchanged. Pinned filter placement uses
normal-flow offsets rather than its translated rectangle; delayed native scroll
samples cannot move the panel's origin. Coalesced pin-only work is bounded and
does not rebuild result cards, load pages or resize the native surface.
Retained callbacks recheck frame-scheduler availability and retire their owned
work if it disappears, so a restored scheduler can accept fresh scroll work.
Pending filter promotions complete their guarded fallback; retained resize and
card-flow callbacks keep their existing measurement/timer fallbacks and lifecycle
ownership checks when the scheduler disappears between frames.

Map names and calendar month/weekday text follow the selected interface language.
Map labels resolve by stable IDs during presentation, preserving saved native
names and history. Numeric date order, separators, first weekday and 12/24-hour
preferences retain their client/config precedence. Packaged map-name provenance
is recorded with the catalog; no runtime network translation is used.

The summary shows both Base XP and Received XP totals in equal columns, each
with its own coverage. Switching the experience selector changes the detailed
series while both totals stay visible. Unknown values remain distinct from zero;
WN8 retains its three-column distribution.

Stacked More sections keep their explicit readable widths but use automatic
flex bases. A native column-flow interpretation can no longer reserve the width
as vertical height. Paired sections retain fixed horizontal bases. Regressions
measure spacing from actual table content through narrow/wide resize transitions.

Transparency pointer/drag and keyboard input land on five-percent ticks within
0–100. Home/End remain endpoints; Shift/Page keys retain larger steps. Legacy
arbitrary percentages remain readable without an automatic configuration rewrite;
the next user input lands on the new grid. Existing save/acknowledgement and
account-context protections remain active.

Validation uses synthetic fixtures across all seven languages and both interface
scales. Real WoT Gameface rendering/input still needs in-game confirmation.
