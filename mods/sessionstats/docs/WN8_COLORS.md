# WN8 text colors

Session Stats uses the thresholds in the [WoT-Life color scheme](https://pl.wot-life.com/)
and the swatches in its [published stylesheet](https://wot-life.com/css/main.min.css).
These colors apply to text, without adding a rating background.

| Displayed WN8 | Text color |
| --- | --- |
| 0–299 | `#000000` |
| 300–599 | `#cd3333` |
| 600–899 | `#d77900` |
| 900–1249 | `#d7b600` |
| 1250–1599 | `#6d9521` |
| 1600–1899 | `#4c762e` |
| 1900–2349 | `#4a92b7` |
| 2350–2899 | `#83579d` |
| 2900 and above | `#5a3175` |

Colors follow the rounded integer actually displayed. The WN8 label and its
value share a color; each Min/Avg/Max value has its own color, while that row's
WN8 label follows Avg. Coverage markers follow the associated period WN8, not
their count. Unknown or pending ratings keep the configured neutral color.
Colored labels and values have one subtle, translucent neutral text halo.
Black ratings instead have a fine, light outline made of four zero-blur text
shadows at 0.75 logical pixels in the cardinal directions. This gives small black
labels and digits a visible edge against dark camouflage without a fuzzy glow.
It scales with the native interface and preserves the exact black ink, cell
background and dimensions. Both the panel and native battle-results cell use
this treatment; changing rating bands or becoming unknown clears the old effect.

Cards have a faint border in their headline WN8 color, drawn at 22% opacity as an
absolute overlay. It does not change card dimensions or add a rating background.
The orange selected-battle frame takes priority; clearing the selection restores
the rating border. Unknown ratings retain the normal configured card border.

The palette covers the period summary, group headlines, distributions,
individual battles, expanded map/vehicle histories, WN8 sorting captions and
the native battle-results cell. The garage launcher has no numerical rating;
its static WN8 caption retains its configured color.

`ui-wn8-colors.cjs` exercises both shipped implementations at every boundary,
including missing values and rounding. Browser checks verify label/value
coloring across grouping modes and nested histories; `ui-postbattle.cjs`
checks the same nine bands in the native result-widget fixture.
