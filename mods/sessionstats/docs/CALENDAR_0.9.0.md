# Calendar and clock in 0.9.0

From and To each use one camouflage popover. The calendar stays above the
hour/minute controls and graphical clock; there is no return-to-calendar toggle.
Clicking a month or year heading opens the corresponding selection grid while
keeping the clock below it. The clock face has an explicit 180rem width and is
centered with `left:50%` and a half-width offset, avoiding native Gameface's
inconsistent automatic margins. The hand is centered on its pivot as well.

Click the hour or minute to choose which clock component to edit. Click a number,
click or drag the hand, or use the arrow keys for single steps. Selecting an hour
advances to minutes. The small information button opens the existing localized
help tooltip. Regional date order, separators, week start, names and 12/24-hour
formatting still follow the native/system preferences described in
[the source evidence](CALENDAR_0.8.0_SOURCE_EVIDENCE.md).

## Allowed choices

The graphical range begins in 2010 and ends at the current minute. A From value
must be strictly earlier than the selected To value, and a To value must be
strictly later than the selected From value. Live custom drafts, saved custom
epochs and saved time points all constrain the other picker. Unavailable years,
months, days, hours, minutes and day periods are disabled before selection;
retained callbacks enforce the same restrictions. If the opposite draft leaves
no possible interval, Apply is disabled. Selecting a date/month that contains a
valid interval chooses its nearest available time.

The inline parser retains the existing 1970–9999 format compatibility, but
submitting a future typed value fails with a localized error. Equal or inverted
From/To values remain invalid. The backend independently rejects future or
inverted bounds before replacing the current projection job, so a stale or
hand-crafted request cannot change the selected range. Today remains selectable
up to the present minute; nonexistent local DST times remain unavailable.

## Verification

`ui-custom-date-source.cjs` exercises exact parsing, localized masks, future
submission guards and strict minute bounds derived from the other draft or
saved point. `test_history_navigation.py` checks authoritative future rejection
without changing existing work. Browser checks cover the simultaneous layout,
centering at 100%/200% scale, help tooltip, disabled future/opposite choices,
exact epoch application, keyboard operation, locale changes and teardown.
`GRZ_CALENDAR_QA_V2` contains one synthetic calendar-and-clock capture for visual
inspection; private game data and screenshots are not release inputs.
