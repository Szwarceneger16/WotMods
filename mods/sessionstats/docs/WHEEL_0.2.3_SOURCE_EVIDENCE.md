# Wheel scrolling 0.2.3 — sources and verification scope

Reviewed on 2026-10-20. This changes only `ui/session_stats.js` panel scrolling.
The user reported reversed direction in the real WoT client; the previous panel
relied solely on `overflow-y: auto`.

## 1. Direction in the current WoT interface

Client resources **2.4.1.0 #977**, `Kurzdor/wot.assets` commit
**`3605bd36c53d10c16be5d93f5414aa5fd129e84e`**, 2026-10-16. This public mirror
is not an official Wargaming mod-compatibility contract.

Source: [InfoView.js, pinned commit](https://github.com/Kurzdor/wot.assets/blob/3605bd36c53d10c16be5d93f5414aa5fd129e84e/gui/gameface/_dist/production/lobby/InfoView/InfoView.js).

| Location | Operation | Meaning |
| --- | --- | --- |
| Lines 2615–2618 | `Next = -1`, `Prev = 1` | Direction is numeric. |
| Lines 2763–2769 | Current position + direction × step | Negative direction decreases position. |
| Lines 2787–2808 | `deltaY` selects direction and triggers movement | Active wheel path. |
| Lines 3150–3157 | `getDirection: e => e.deltaY > 1 ? p.Next : p.Prev`, assigning `scrollTop` | Positive delta above 1 moves up; negative moves down. |
| Lines 3305–3309 | Upper button also uses `Next` | Independently confirms negative-direction meaning. |

Inference: the native WoT component interprets the sign oppositely to standard
browser overflow scrolling, matching the user's observation. Our inversion applies
only after successful Gameface model binding (`state.bound`); standalone HTML keeps
normal browser behavior.

The `> 1` threshold was not copied because it does not give small positive deltas
a consistent direction. The mod uses the sign. Version 0.2.3 retained device-delta
magnitude instead of copying the native animated component's speed.

## 2. Raw DOM versus React

React `onWheel` alone would not establish the same sign for direct `addEventListener`.
In [InfoView.html at the same commit](https://github.com/Kurzdor/wot.assets/blob/3605bd36c53d10c16be5d93f5414aa5fd129e84e/gui/gameface/_dist/production/lobby/InfoView/InfoView.html),
lines 6120–6133, bundled React **copies an existing `deltaY` without changing its
sign**. Only absent `deltaY` falls back to negated `wheelDeltaY`/`wheelDelta`.

Gameface documents `wheel` as a supported DOM L3 `WheelEvent` in its
[JS-event table](https://docs.coherent-labs.com/cpp-gameface/content_development/supported_features_tables/jsevents/).
The official [SVG UI Tricks — `mouse-map-controls.js`](https://guide.coherent-labs.com/layout-assets-and-styling/graphics--shapes/svg-ui-tricks/),
updated 2026-07-02, directly uses `map.addEventListener("wheel", ...)`,
`event.deltaY` and `event.preventDefault()` without React. This supports raw DOM
`deltaY`; no unverified legacy `mousewheel` path was added.

## 3. Canceling default movement — evidence and limits

[Gameface C++ input documentation](https://docs.coherent-labs.com/cpp-gameface/integration/optional_features/inputhandlingcpp_native/)
describes script handling/propagation before default operations including scrolling.
The [Event API](https://docs.coherent-labs.com/cpp-gameface/api_reference/classes/interface_event/)
exposes `preventDefault`, `stopPropagation`, `cancelable` and `defaultPrevented`.
The official example above cancels inside an ordinary wheel listener.

The adapter owns one panel listener, cancels before changing `scrollTop` and stops
propagation. There is no global `document` listener. Cleanup removes the exact
listener. Handled events stay canceled at both endpoints to prevent another element
from scrolling simultaneously.

**Actual `event.cancelable` was not measured in a running WoT client.** Public docs
establish supported interfaces and cancellation usage, not flags for every native
input in a specific client build. `InfoView.js` does not prove this: its handler
does not call `preventDefault()` and uses a custom component. [InfoView.css](https://github.com/Kurzdor/wot.assets/blob/3605bd36c53d10c16be5d93f5414aa5fd129e84e/gui/gameface/_dist/production/lobby/InfoView/InfoView.css),
lines 190–193, uses `overflow-y: hidden`, a separate scrollbar and manual positioning.

If the host explicitly supplies `cancelable === false`, the adapter adds no manual
movement, avoiding overlap with an uncancelable default. Direction correction will
not apply under that unusual contract; client observation and a separate adjustment
would be required. Chromium tests do not establish C++ Gameface behavior.

## 4. Behavior selected for this panel

- In 0.2.3, pixel mode retained absolute delta, including small trackpad input;
  only the sign changed in bound Gameface.
- Line mode multiplied by 24 logical units with client scale; page mode used the
  current viewport height. This was a mod speed choice, not identical InfoView speed.
- Position clamps to content bounds. Manual movement immediately triggers existing
  history batching without waiting for another wheel or engine `scroll` event.
- Predominantly horizontal gestures and Shift + wheel do not become vertical
  movement. Wheeling over the title does not control the list.
- An open reset dialog consumes panel wheels without moving background statistics.
  Events already canceled by another consumer receive no additional movement.

## 5. Regression verification

`tests/ui-wheel.cjs`: **19/19** at preparation, without JavaScript errors. Main cases
use **actual Chromium CDP input** (`page.mouse.wheel`) with `isTrusted === true`.
The model double reproduces WoT's sign contract, allowing browser defaults to run
if cancellation fails. Synthetic `WheelEvent` alone would not reveal that risk.

Checks cover both directions and exactly one movement, small deltas, repeated input,
horizontal gestures, Shift, title, reset dialog, endpoints and batching 95 entries.
A separate unbound page verifies unchanged browser scrolling. After `destroy()`,
the original reversed WoT-sign behavior returns, serving as a negative control and
listener-removal check. Only line/page-unit cases use synthetic events.

Scope: shipped JS/HTML/CSS in Chromium with a model-bridge double. No WoT/Gameface
engine, battles or account-statistic changes were involved.
