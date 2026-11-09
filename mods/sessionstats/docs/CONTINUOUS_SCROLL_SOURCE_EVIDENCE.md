# Continuous scrolling and native top action

The top action draws two upward chevrons with the same configurable orange
accent as its frame/glow. Borders, absolute positions and 2D transforms are
already used by the panel's native resize grips; no browser-only image tint,
mask or filter is required. No game artwork is edited or distributed.

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

Request identities and an opaque index revision prevent joining pages from
different native result snapshots. Map/vehicle paging returns one additional
indexed ten-row list independently of the current global page; this allows
earlier appended cards to update their own body without rebuilding the panel.
