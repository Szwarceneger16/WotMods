# Scrolling speed 0.2.4 — source and verification

Reviewed on 2026-10-20. After the 0.2.3 direction fix, the user confirmed scrolling
was too slow in WoT. This update changes step size. Direction, clamping and default
cancellation remain documented in `WHEEL_0.2.3_SOURCE_EVIDENCE.md`.

## Why the old speed was unsuitable

Version 0.2.3 interpreted pixel-mode `deltaY` as pixels. A normalized host value such
as `-1` therefore moved one pixel. The report confirms poor speed, not a measurement
of that user's event values; `-1` illustrates the previous algorithm's weakness.

## WoT interface pattern

Rechecked [InfoView.js from client 2.4.1.0 #977](https://github.com/Kurzdor/wot.assets/blob/3605bd36c53d10c16be5d93f5414aa5fd129e84e/gui/gameface/_dist/production/lobby/InfoView/InfoView.js),
commit `3605bd36c53d10c16be5d93f5414aa5fd129e84e`,
file SHA `af8259ddacaef0cf69b638b1ae88e455b2f2057b`.

| Location | Observed operation | Mod usage |
| --- | --- | --- |
| Lines 2619–2622 | Default `step: { type: 'proportional', factor: 4 }` | One-quarter viewport-height steps. |
| Lines 2787–2808 | `getWrapperSize / factor`; nonzero `deltaY` selects direction | Raw delta magnitude does not set ordinary wheel distance. |
| Lines 3150–3157 | `offsetHeight` and `scrollTop` | Step follows current panel height. |

This public client-resource mirror is not an official compatibility promise. The
mod uses the same proportion without copying the animation library; movement is direct.

## Version 0.2.4 behavior

- Ordinary vertical bound-Gameface wheel input moves **one quarter of the visible
  list height**, for `1`, `120` and fractional values alike. Four events cover one
  viewport unless an endpoint is reached.
- This also applies to line mode. Separate page mode retains whole-page units:
  viewport height multiplied by delta.
- Dimensions come from the actual scroll region without multiplying GUI scale
  again, preventing double scaling.
- Direction follows sign: native positive delta moves up, negative moves down.
  Standalone HTML retains normal browser scrolling.
- Endpoint clamping, history batching, reset-modal background blocking and ignoring
  horizontal/Shift gestures remain.
- Title-bar wheels do not scroll content. Cancellation precedes manual movement,
  preventing additional browser-default movement for handled input.

This deliberately gives up pixel precision for tiny native deltas, treating them
as list-movement commands. Device event frequency can still affect perceived speed;
no unverified mouse/trackpad detection was introduced.

## Verification

`tests/ui-wheel.cjs` uses shipped HTML/CSS/JS. Main cases use actual CDP input
(`page.mouse.wheel`, `isTrusted === true`) to detect uncanceled browser defaults.
Only line/page-unit cases are synthetic.

Regressions cover a useful `-1` step, correct `+1` direction, fractional input,
repeated input, shorter panels, both directions, gesture blocking, modal reset,
endpoints and batching 95 entries. A separate unbound page checks normal preview
scrolling. The post-`destroy()` control confirms adapter removal.

Current run results: `tests/wheel-report.json`. Scope is Chromium with a model
contract double, without native WoT/Gameface, battles or account-statistic changes.
