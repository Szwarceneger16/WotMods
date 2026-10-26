# Window fix 0.2.1 — source evidence

Reviewed on 2026-10-20. Package target: WoT PC Wargaming EU 2.4.1.0. This records
implementation evidence and local validation, not a stable Wargaming mod API guarantee.

## User-test observations

The supplied 0.2.0 screenshot showed the window near the upper-left corner. Model
data and status text were visible, but `button` labels were missing. The working
footer button used explicit flex layout and a `span` label. The image alone cannot
distinguish a missing Python `resize` callback from a later positioning failure;
no diagnostic log was available.

Previously, `views.py` positioned the window only after the document's `resize`
message. It lacked native centering in `_onReady` and reaction to actual surface
`onSizeChanged`. Parent sizing assumed `Window.parent` always exposed wrapper
`Window.size`; code also ignored native `move` returning `False`.

## Pinned client sources

`izeberg/wot-src`, EU branch, commit `5e721e36891c80d8d51a431164960c863641ee63`
from 2026-10-16. This is a public client-script mirror rather than an officially
supported Wargaming compatibility contract.

| Verified fact | Exact source |
| --- | --- |
| `WindowImpl.center()` calls `self.area.center(self)`; `move(x,y,...)` uses the same area. Both return `False` when the window has no area. | [window_impl.py, lines 35–57](https://github.com/izeberg/wot-src/blob/5e721e36891c80d8d51a431164960c863641ee63/sources/res/scripts/client/gui/impl/pub/window_impl.py#L35-L57) |
| `WindowsArea.center(window)` delegates to `centerPyWindow(window.uniqueID)`; `move` delegates to `movePyWindow`. These scripts do not describe the native positioning algorithm. | [windows_area.py, lines 40–44](https://github.com/izeberg/wot-src/blob/5e721e36891c80d8d51a431164960c863641ee63/sources/res/scripts/client/frameworks/wulf/windows_system/windows_area.py#L40-L44) |
| `Window.parent` returns `self.proxy.parent` without `getObject`, while `WindowSettings.parent` explicitly calls `getObject`. Their return interfaces must not be assumed identical. | [window.py, lines 83–91](https://github.com/izeberg/wot-src/blob/5e721e36891c80d8d51a431164960c863641ee63/sources/res/scripts/client/frameworks/wulf/windows_system/window.py#L83-L91) and [lines 153–159](https://github.com/izeberg/wot-src/blob/5e721e36891c80d8d51a431164960c863641ee63/sources/res/scripts/client/frameworks/wulf/windows_system/window.py#L153-L159) |
| Wrapper `Window.size` reads `proxy.windowSize`. The `PyObjectWindow` stub exposes `windowSize` without a `.size` alias. This supports retaining the main-window wrapper but does not establish the user's exact exception. | [window.py, lines 223–230](https://github.com/izeberg/wot-src/blob/5e721e36891c80d8d51a431164960c863641ee63/sources/res/scripts/client/frameworks/wulf/windows_system/window.py#L223-L230) and [_wulf.py: PyObjectWindow](https://github.com/izeberg/wot-src/blob/5e721e36891c80d8d51a431164960c863641ee63/_stubs/_wulf.py#L1293-L1338) |
| Base `Window._onReady()` only calls `self.show()`. `WindowImpl` does not override it. Our centering followed by `show(True)` preserves showing; another `super()._onReady()` would show twice. | [window.py, lines 285–287](https://github.com/izeberg/wot-src/blob/5e721e36891c80d8d51a431164960c863641ee63/sources/res/scripts/client/frameworks/wulf/windows_system/window.py#L285-L287), [lines 315–316](https://github.com/izeberg/wot-src/blob/5e721e36891c80d8d51a431164960c863641ee63/sources/res/scripts/client/frameworks/wulf/windows_system/window.py#L315-L316) and [window_impl.py](https://github.com/izeberg/wot-src/blob/5e721e36891c80d8d51a431164960c863641ee63/sources/res/scripts/client/gui/impl/pub/window_impl.py) |
| `_cWindowStatusChanged(_,newStatus)` emits one argument: `onStatusChanged(newStatus)`. `_cResized(width,height)` emits three: `onSizeChanged(uniqueID,width,height)`. `_cReady` invokes `_onReady` at `LOADED`. | [window.py, lines 359–383](https://github.com/izeberg/wot-src/blob/5e721e36891c80d8d51a431164960c863641ee63/sources/res/scripts/client/frameworks/wulf/windows_system/window.py#L359-L383) |
| `IGuiLoader.scale` is an interface property; `GuiApplication.scale` reads `self.__impl.scale`. This supplies `payload.viewport.scale` without parsing automatic-scale settings or using `devicePixelRatio`. | [skeletons/gui/impl.py, lines 46–48](https://github.com/izeberg/wot-src/blob/5e721e36891c80d8d51a431164960c863641ee63/sources/res/scripts/client/skeletons/gui/impl.py#L46-L48) and [gui_application.py, lines 69–71](https://github.com/izeberg/wot-src/blob/5e721e36891c80d8d51a431164960c863641ee63/sources/res/scripts/client/frameworks/wulf/gui_application.py#L69-L71) |

No documented texture-size setter was found in the inspected Python window/view
wrappers. The mod neither invents a C++ `resize` method nor assigns read-only `Window.size`.

## Mod-author reference: Gameface sizing and window readiness

`przemyslaw-zan/zanju-wot-mods`, commit
`809ad2740a33154de22c828a5dd3007e7167a282`, 2026-10-14, GPL-3.0:

- [card_window.py, lines 163–171](https://github.com/przemyslaw-zan/zanju-wot-mods/blob/809ad2740a33154de22c828a5dd3007e7167a282/mods/campaign-tracker/src/zanju_ct/gameface/card_window.py#L163-L171)
  calls `show(False)` directly in `_onReady`. Our interactive window uses
  `show(True)` to receive focus.
- [card_panel.js, lines 128–181](https://github.com/przemyslaw-zan/zanju-wot-mods/blob/809ad2740a33154de22c828a5dd3007e7167a282/mods/campaign-tracker/res/gui/gameface/mods/zanju_campaigns/card_panel.js#L128-L181)
  measures after rendering frames, publishes physical size with
  `viewEnv.resizeViewPx(width,height)` and separately sends a model command. This
  source does not establish `viewEnv.remToPx(1)`; our use is a guarded fallback.
  Native `IGuiLoader.scale` is preferred.
- [Choosing a UI approach](https://github.com/przemyslaw-zan/zanju-wot-mods/blob/809ad2740a33154de22c828a5dd3007e7167a282/docs/reference/choosing-a-ui-approach.md)
  explains correct native-surface sizing because it controls input capture.
  Browser tests do not replace that in-game check.

## Integration changes in 0.2.1

1. Native `_onReady` calls `WindowImpl.center()` before `show(True)`. Initial
   positioning no longer depends on a JavaScript message.
2. Each confirmed new surface `onSizeChanged` recenters. The document still owns
   `resizeViewPx`.
3. The retained main-window wrapper supplies model dimensions and fallback `move`
   when the native area rejects `center`. `False` is recognized and not cached as
   successful positioning.
4. Main-window resize updates document bounds/scale. UI scale events send `viewport`
   to reread native scale.
5. The window owner handles `close` directly. Closing removes subscriptions/timer;
   generation numbers reject late commands/readiness from an old window.
6. Bounded diagnostics record `dom_ready`, `model_bound`, `layout_ready`, the first
   message of each type and at most four resizes per opening. One five-second timer
   reports missing stages. Logs exclude account IDs, nicknames, session data and
   full payloads. `layout_ready` means DOM measurement finished, not that every
   label is visible in the native renderer.

## Local validation and limits

`tests/test_runtime.py`: **31 tests pass on CPython 3 and CPython 2.7.18**. Wulf
doubles cover center-before-show, actual event signatures, recentering without HTML
commands, a native parent lacking `.size`, scale changes, invalid dimensions,
rejected positioning, closing, late commands and subscription/timer cleanup.

These check our code against reviewed contracts without running WoT or Coherent
Gameface. At this historical checkpoint, 0.2.1 had not been retested in the game.
Native text drawing, hit tests and C++ centering therefore were not confirmed.
Full UI/package checks are reported separately in the release report.
