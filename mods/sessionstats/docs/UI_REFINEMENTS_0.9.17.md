# Compact battle cards and source arrows in 0.9.17

Single-battle performance tables use 148 logical pixels instead of 176. The
recovered 28 pixels give the finance table more room for currency captions.
Its ordinary caption column uses 35% of the table; numeric figures keep their
regular 13-pixel reading size. Larger figures and narrow layouts retain their
full-number fallback rather than compressing or clipping the text.

A synthetic Polish battle with six-digit income, costs and net values fits
both credit captions on one line in a default 500-pixel card. Its height falls
from 223 to 183 logical pixels at both 1× and 2× scale. Both credit rows remain
visible, with one shared actual cost value. Aggregate distribution columns
keep their existing layout.

Outcome and map slots keep their horizontal footprint. Natural caption
heights center the visible artwork and text together with the More action,
including one-line labels. The existing wide inline mode is retained.

Source arrows use a 14×14 square with a 5-pixel gap from the figure. Their
combined 19-pixel lane is unchanged, preserving the full number's available
space. Explicit flex items, original numeric nodes, focus/source ownership,
colors, configured corner radii and the orange return marker are retained.

Regression checks cover real text ink, six-digit signed values, large-value
fallback, visible header-content centers, translated labels, narrow layouts,
source-arrow geometry and native paint fault models. Fixtures and captures
are synthetic; the actual renderer remains an in-game verification step.

The appearance-only browser uses full rasterization for both the static and
compiled-default frames. Partial repaint tiles produced tiny rounded-edge
differences despite identical geometry and computed paint. Independent raw
PNG comparisons reproduce that drift and confirm zero changed pixels through
three default/fallback cycles with full rasterization. Actual configured
theme changes remain detectable. The 37 assertions and existing 16-pixel /
6-channel-level limits are retained.

The Chromium rendering option is documented in
[Chrome's tooling flags](https://github.com/GoogleChrome/chrome-launcher/blob/main/docs/chrome-flags-for-tools.md#rendering--gpu).
