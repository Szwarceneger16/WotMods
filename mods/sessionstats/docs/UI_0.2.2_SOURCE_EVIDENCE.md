# Window 0.2.2 — dragging, geometry and source evidence

Reviewed on 2026-10-20. Target: WoT PC Wargaming EU 2.4.1.0. Public client-resource
mirrors and a mod author's repository provide implementation evidence, not an
official stable Wargaming mod API.

## Observation and scope

The user's full screenshot showed a roughly 700×620 px panel near the upper-left
corner with battle results rendered correctly. Version 0.2.1 lacked native header
dragging. Without `game.log`, initial surface dimensions, window area and operation
ordering cannot be distinguished as causes of the (0,0) position. None is presented
as the established cause of that user test.

Version 0.2.2 adds the verified client move event, explicit `WindowImpl.move(x,y)`
positioning and separate requested/observed `Window.position`. Data refresh no
longer recenters a player-moved window. A smaller game area only clamps it within
available bounds.

## Native dragging: complete JS/Python path

JS source: `Kurzdor/wot.assets`, commit
`3605bd36c53d10c16be5d93f5414aa5fd129e84e`, 2026-10-16, **2.4.1.0 #977**.

| Verified element | Exact source |
| --- | --- |
| Client helper `sendEvent.move(on)` sends event type 16 with `isMouseEvent: true` and `on`; proxy type is `GFViewEventProxy`. | [tutorial.js, lines 197–244](https://github.com/Kurzdor/wot.assets/blob/3605bd36c53d10c16be5d93f5414aa5fd129e84e/gui/gameface/js/tutorial.js#L197-L244) |
| The native platoon window begins moving only with the left mouse button, ends on document `mouseup` and removes that listener. | [MembersWindow.js, lines 1257–1268](https://github.com/Kurzdor/wot.assets/blob/3605bd36c53d10c16be5d93f5414aa5fd129e84e/gui/gameface/_dist/production/lobby/platoon/MembersWindow/MembersWindow.js#L1257-L1268) |
| Python `MembersWindow` uses `WindowFlags.WINDOW` without an additional draggable flag. Its `ViewSettings` defaults to `ViewFlags.VIEW`, as in this mod. | [platoon_members_view.py, lines 87–92](https://github.com/izeberg/wot-src/blob/5e721e36891c80d8d51a431164960c863641ee63/sources/res/scripts/client/gui/impl/lobby/platoon/view/platoon_members_view.py#L87-L92) and [lines 724–739](https://github.com/izeberg/wot-src/blob/5e721e36891c80d8d51a431164960c863641ee63/sources/res/scripts/client/gui/impl/lobby/platoon/view/platoon_members_view.py#L724-L739) |
| `PreloadableWindow` passes flags/content to `WindowImpl`; its extra behavior hides preloaded views. It adds no drag mechanism or flag. | [platoon_helpers.py, lines 19–36](https://github.com/izeberg/wot-src/blob/5e721e36891c80d8d51a431164960c863641ee63/sources/res/scripts/client/gui/impl/lobby/platoon/platoon_helpers.py#L19-L36) |

The header uses:

```javascript
viewEnv.handleViewEvent({__Type:'GFViewEventProxy', type:16, isMouseEvent:true, on:true});
```

Ending sends the same event with `on:false`. Model command
`{action:'drag', active:true/false}` tells the owner to preserve the chosen position;
it does not transmit mouse-movement coordinates. The mod does not use an unverified
`startWindowDrag`, DOM-only moving or cursor simulation. Close controls and an open
reset dialog do not start dragging. Blur and document cleanup also end it.

## Size and positioning

- [tutorial.js, lines 262–282](https://github.com/Kurzdor/wot.assets/blob/3605bd36c53d10c16be5d93f5414aa5fd129e84e/gui/gameface/js/tutorial.js#L262-L282)
  confirms `getViewSizePx()`, `resizeViewPx(width,height)`, `getScale()` and
  `remToPx(value)`. These are binding calls, not C++ implementations. Generic
  `engine.call` does not justify inventing additional resize-command names.
- [WindowImpl.move, lines 42–48](https://github.com/izeberg/wot-src/blob/5e721e36891c80d8d51a431164960c863641ee63/sources/res/scripts/client/gui/impl/pub/window_impl.py#L42-L48)
  delegates to the native area. [Window.position and Window.size](https://github.com/izeberg/wot-src/blob/5e721e36891c80d8d51a431164960c863641ee63/sources/res/scripts/client/frameworks/wulf/windows_system/window.py#L207-L230)
  read proxy `windowPosition`/`windowSize`. [Events](https://github.com/izeberg/wot-src/blob/5e721e36891c80d8d51a431164960c863641ee63/sources/res/scripts/client/frameworks/wulf/windows_system/window.py#L381-L386)
  use `onSizeChanged(uniqueID,width,height)` and `onPositionChanged(uniqueID,x,y)`.
- [Mod-author card_window.py, lines 417–438](https://github.com/przemyslaw-zan/zanju-wot-mods/blob/809ad2740a33154de22c828a5dd3007e7167a282/mods/campaign-tracker/src/zanju_ct/gameface/card_window.py#L417-L438)
  derives position from document/parent dimensions and calls `WindowImpl.move`,
  the pattern adopted in 0.2.2.
- [Mod-author card.css](https://github.com/przemyslaw-zan/zanju-wot-mods/blob/809ad2740a33154de22c828a5dd3007e7167a282/mods/campaign-tracker/res/gui/gameface/mods/zanju_campaigns/card.css#L14-L21)
  avoids 100% `html`/`body` dimensions, keeping an explicitly sized panel in normal
  flow. Our native document likewise separates body height from the initial surface;
  browser previews have their own context.

DOM measurement does not confirm texture dimensions. One five-second timer can
separately report missing renderer stages, requested/observed-position differences
or document/native-surface differences. It stops early only after matching stages
and measurements. Logs are bounded and exclude account/statistic contents. Closing
removes all listeners and the timer.

## Local verification

`tests/test_runtime.py`: **34/34 on Python 3 and 34/34 on Python 2.7.18**. Regressions
cover accepted movement clamped to (0,0) on an initial fullscreen surface, successful
positioning after native resize, position retention across data/size/scale updates,
uninterrupted active dragging, smaller-screen clamping, listener removal and old
window commands.

Wulf doubles validate our code against reviewed contracts without running client
C++. These results do not mean 0.2.2 had already been retested in a running WoT client.
