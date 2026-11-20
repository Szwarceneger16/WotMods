# Adjacent source actions and native warnings in 0.9.13

Performance Min/Max arrows sit immediately after their figures, with a 3 px gap,
in both the summary and aggregate cards. The original numeric text and WN8 figure
nodes remain direct children of their native cells. A transparent, cell-sized
button owns navigation; its small rounded arrow cue stays outside the numeric
painting path. Hover, focus and active sorting change the cue background without
adding a frame around the whole value.

Financial Min/Max controls retain their explicit native captions and 18 px
height. They form centered pairs with a 3 px gap. Thin 1 px grey-olive horizontal
and vertical rules separate the performance and finance cells, using
`colors.table_row_following_border_top`, whose default is `#3c4434`.
The tables have no additional outer frame. Six-digit figures, zero values,
long currency amounts and source navigation retain their existing behavior.

The filter warning uses the native alert triangle inside a framed orange
Gameface treatment. The partial sorting-value indicator uses the same asset in
place of the asterisk. Its coverage tooltip and accessible description retain
the available and recorded counts. Unknown values remain unknown, and pending
reports alone do not trigger a warning about fields missing from received
reports. A single partial-results badge remains separate from those field counts.

The **Back** button beside **Selected battle** returns to the exact source
context captured when that result was opened. Existing account, period and
request ownership checks continue to reject stale source actions.

Aggregate headers no longer reserve an empty identity spacer. Their identity,
statistics and controls share the available width, and the gold selected-value
block fits its caption and figure. Compact layouts retain readable controls
without introducing another fixed empty column.

## Native warning sources

The resource and Gameface rules were checked in the client assets at commit
`3605bd36c53d10c16be5d93f5414aa5fd129e84e`:

- [Native alert triangle](https://github.com/Kurzdor/wot.assets/blob/3605bd36c53d10c16be5d93f5414aa5fd129e84e/gui/maps/icons/library/alertIcon.png):
  `gui/maps/icons/library/alertIcon.png`, 16×16 RGBA, 629 bytes;
  SHA-256 `5714241ffc673fa4dd406f9f1acee8127f3824a57b54cd2978427ee2843ed18a`.
- [AlertTooltip.css](https://github.com/Kurzdor/wot.assets/blob/3605bd36c53d10c16be5d93f5414aa5fd129e84e/gui/gameface/_dist/production/lobby/mode_selector/tooltips/AlertTooltip/AlertTooltip.css):
  a 16×16 alert icon and `#ee7000` warning text.
- [WarningText.css](https://github.com/Kurzdor/wot.assets/blob/3605bd36c53d10c16be5d93f5414aa5fd129e84e/gui/gameface/_dist/production/dialogs/widgets/WarningText/WarningText.css)
  and [TextWithWarning.css](https://github.com/Kurzdor/wot.assets/blob/3605bd36c53d10c16be5d93f5414aa5fd129e84e/gui/gameface/_dist/production/dialogs/sub_views/content/TextWithWarning/TextWithWarning.css):
  native icon-and-text warning layout and orange text.
- [HangarView.css](https://github.com/Kurzdor/wot.assets/blob/3605bd36c53d10c16be5d93f5414aa5fd129e84e/gui/gameface/_dist/production/lobby/HangarView/HangarView.css):
  `.InputControl_base__alert_22` uses a `#ee7000` border with black inner shadows
  and a `#8d0d03` glow. The panel adapts those primitives and supplies its own
  configurable 4 px warning radius.

The separate login retry warning is a Scaleform view, selected by
[`LoginView.py`](https://github.com/izeberg/wot-src/blob/c7d909ac3a5e0b4564b202eb200f8ed58c0c11b6/sources/res/scripts/client/gui/Scaleform/daapi/view/login/LoginView.py).
These Gameface components do not claim to reproduce that SWF pixel for pixel.

Regression fixtures and captures use synthetic data. Browser validation exercises
the shipped UI; the live client's renderer still requires an in-game check.
