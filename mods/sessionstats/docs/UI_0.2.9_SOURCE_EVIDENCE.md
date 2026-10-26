# UI and game-language selection 0.2.9

Reviewed on 2026-10-24. These changes affect presentation only: battle records,
history format, period calculations and account ownership are unchanged.

## Existing WG artwork and localized text

The inspected native result screen does not use a complete localized bitmap
with the result word baked into it. Its text comes from
`battle_results.status.{win,lose,tie}`, rendered separately from the artwork.
See the pinned client assets' [random result bundle](https://github.com/Kurzdor/wot.assets/blob/3605bd36c53d10c16be5d93f5414aa5fd129e84e/gui/gameface/_dist/production/mono/post_battle/random/bundle.js)
and [styles](https://github.com/Kurzdor/wot.assets/blob/3605bd36c53d10c16be5d93f5414aa5fd129e84e/gui/gameface/_dist/production/mono/post_battle/random/random.css).
This is evidence about that screen, not a claim that every client resource has
been searched or that its full native component is embedded in this mod.

The mod references three existing WG notification graphics, unchanged, from
the local game resources. The [pinned 2.4.1.0 asset directory](https://github.com/Kurzdor/wot.assets/tree/3605bd36c53d10c16be5d93f5414aa5fd129e84e/gui/maps/icons/library)
contains these 288 by 167 images:

| Result | Exact resource under `gui/maps/icons/library/` | Source blob SHA-1 |
| --- | --- | --- |
| Victory | `BgBattleResultIconVictory-1.png` | `9a6fdf9c6a758b5858c6d81a05304069a6c6821c` |
| Defeat | `BgBattleResultIconDefeat-1.png` | `b68a1654afba8d4433cbed75c301819114550a85` |
| Draw | `BgBattleResultIconDraw-1.png` | `cf4b969b9d565c938578a4bcbabeb6694b7af69d` |

These are language-neutral graphics, not newly drawn or translated banners.
They are displayed proportionally without recoloring, cropping or text overlays.
The localized caption is a separate element below each image. Nothing is copied
into the package, and runtime performs no image downloads. Existing
`ResMgr.isFile` checks verify PNG or same-name DDS before exposing an `img://` URL.
Python and JavaScript accept only the three exact result paths; JavaScript also
requires the image to match the row's outcome. Missing art leaves readable text.
Unknown results never borrow a Victory, Defeat or Draw graphic.

## Native language boundary

The [client helpers](https://github.com/izeberg/wot-src/blob/c7d909ac3a5e0b4564b202eb200f8ed58c0c11b6/sources/res/scripts/client/helpers/__init__.py)
provide `getClientLanguage()`. The game adapter reads it only when reloading
configuration, not per frame or result poll. Pure localization code normalizes
regional codes, chooses a supported catalog and falls back to English. An
explicit configured language wins. Existing configuration is not overwritten.

[BATTLE_RESULTS](https://github.com/izeberg/wot-src/blob/c7d909ac3a5e0b4564b202eb200f8ed58c0c11b6/sources/res/scripts/client/gui/Scaleform/locale/BATTLE_RESULTS.py)
declares the original keys `#battle_results:status/win`, `status/lose` and
`status/tie`. `helpers.i18n.makeString` supplies these native captions when the
selected mod language matches the game. A different configured language uses
its bundled catalog. An unchanged external template does not mask native text;
customized outcome entries retain priority. Rejected or unavailable native text
falls back per message, independently of collecting results and applying styles.

## Controls and validation

Previous/Next now share `.ss-button` with the existing panel actions. They use
the same configurable colors, borders, typography and disabled opacity, plus
rem-based pagination spacing. Both static and generated CSS agree.

Regression coverage includes automatic, explicit, regional and unsupported
languages; missing/failing native APIs; original translation keys; UTF-8 native
text; external overrides; unchanged history across reloads; exact image paths;
PNG/DDS availability; resource retries; text fallback and unchanged summaries.
Browser contracts exercise matching button styles, pagination ownership and
disabled states, separate localized captions, narrow layouts and rejection of
remote/mismatched graphics. Browsers cannot load WoT's native `img://` textures;
these checks validate DOM/layout/URL behavior, not the actual game renderer.

The user confirmed the preceding mod build works in game. The new 0.2.9 changes
still need an in-game visual check in the intended client language. No claim of
an in-game test of this revision is made here.
