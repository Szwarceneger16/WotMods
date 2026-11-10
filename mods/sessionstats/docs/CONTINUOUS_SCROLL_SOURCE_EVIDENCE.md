# Continuous scrolling and native top action

The top action draws two upward chevrons with the same configurable orange
accent as its frame/glow. Borders, absolute positions and 2D transforms are
already used by the panel's native resize grips; no browser-only image tint,
mask or filter is required. No game artwork is edited or distributed.

The Close symbol uses explicit configured stroke backgrounds in its normal,
hover and keyboard-focus states. Gameface rejects `currentColor` backgrounds
(also covered by the footer compatibility tests), so titlebar regression tests
remove those declarations before checking the painted symbols and alignment.

The matching native selection reply owns the highlight before any layout runs;
card construction paints its frame before native geometry is ready. A delayed
first layout or an expired scroll retry cannot prevent that selection paint.
Focus/scroll retries retire after two seconds or 40 attempts; later geometry,
snapshots or resize events cannot revive that destination. Expiry preserves the
existing outline. Native focus/blur events do not own selection: Gameface can
publish them during mounting or reparenting. An explicit outside click or changed
view/context dismisses the frame. Its ordinary card border carries the solid
orange baseline without changing dimensions; the animated overlay is cosmetic.
The map drill-down regressions cover both retry limits and delayed geometry.

The previous 16×16 client bitmap
`coui://gui/maps/icons/buttons/icon_arrow_formation_right_double.png` was verified in
[Kurzdor/wot.assets at 3605bd36](https://github.com/Kurzdor/wot.assets/tree/3605bd36c53d10c16be5d93f5414aa5fd129e84e).
Its gray pixels do not inherit the button's CSS color, so it is no longer used
for the orange top action.
The Flash-only `GlowArrowAsset` linkage is not a browser texture URL and is
therefore not used as an invented PNG resource.

The panel uses existing block/flex, transforms and animation support. It does
not depend on CSS sticky positioning or IntersectionObserver. Filter pinning
translates the original controls inside their existing scroll viewport while
retaining their normal-flow space. Each loaded result page has its own pair
of chronological card lanes and a horizontal numbered separator.

The feed loads adjacent pages at both edges. Inserting an earlier boundary or
page restores an owned visible-card anchor after native layout settles. The Top
action targets page zero directly, preserving ordering and cached data while
retiring an older pending navigation destination. Delayed replies cannot move
the viewport away from this newer destination. Empty-feed messages have their
own marker and are reconciled once per render rather than repeatedly appended.

Request identities and an opaque index revision prevent joining pages from
different native result snapshots. Map/vehicle paging returns one additional
indexed ten-row list independently of the current global page; this allows
earlier appended cards to update their own body without rebuilding the panel.
