# Interface 0.2.4 — changes and verification basis

As of 2026-10-20. This update responds to two screenshots of working 0.2.3 and reports
of slow scrolling, repeated averages for individual battles and overly sharp table grids.

## Individual battle results

`ui/session_stats.js` distinguishes aggregates from individual battles. A battle
header shows vehicle, date, map and victory/defeat/draw without repeating the
single-battle count or win rate.

`details(..., battle)` creates two individual `.ss-battle-performance` metrics:
the selected XP type and full WN8. XP comes from a series total containing exactly
one known result. WN8 uses `stats.wn8` with one-result coverage. Neither presents
an average as an individual result. Missing coverage gives a dash even if the
missing series total would be zero; confirmed zero remains zero.

Session, vehicle and map aggregates retain minimum/average/maximum. Shared finances
show income, costs and net values including bonds. Calculations, normalization and
history storage are unchanged.

## Softer layout

`ui/session_stats.css` retains the default 700×620 panel, Warhelios and olive/gold
palette. Sections have small corner radii and calm headers. Subtle horizontal
separators and alternating backgrounds replace vertical cell grids.

Aggregate XP/WN8 numbers remain 16 logical units, finances 14 and individual battle
metrics 18. Rows have five units of top/bottom spacing. Amounts align right with
four trailing units. Numeric columns retain left space for full values after
removing vertical lines. Names/other cells retain side padding. Fonts are not
shrunk to fit large amounts.

The [official Gameface CSS property table](https://docs.coherent-labs.com/cpp-gameface/content_development/supported_features_tables/cssproperties/)
lists `border-radius`, individual corners and `box-shadow`; the shadow restriction
concerns unused `inherit`. Rechecked on 2026-10-20. No CSS grid, `object-fit`,
background `currentColor` or new dependencies were introduced.

## Verification and limits

`tests/ui_contract.cjs` checks the shipped HTML/CSS/JS: individual metrics in both
XP modes, no battle min/average/max, retained aggregates, outcomes/missing data,
bond finances, thumbnails, controls and window contract. DOM Range measurements
detect digits entering cell padding. Checks include ordinary values and full
±12 345 678 amounts, XP 123 456 and WN8 10420 at widths 320, 360, 420, 560, 620
and 744 pixels.

Current report: `tests/ui-report.json`. Final session/battle previews were visually
inspected internally; QA images are not packaged. Tests run Chromium with a mocked
client model, without WoT's native renderer. User screenshots establish the previous
release's behavior, not the new 0.2.4 package in that client.

Wheel-speed changes and separate tests: `WHEEL_0.2.4_SOURCE_EVIDENCE.md`.
