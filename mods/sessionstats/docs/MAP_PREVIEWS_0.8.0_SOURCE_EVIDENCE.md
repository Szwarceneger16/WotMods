# Map hover artwork 0.8.0 — native resources

Reviewed on 2026-11-11 against the same pinned client and asset catalogues as
[the thumbnail adapter](VISUALS_0.2.2_SOURCE_EVIDENCE.md). No client artwork is
copied into this repository or fetched by the running mod.

## Available images

| Native map resource | Example dimensions | Use in Session Stats |
| --- | --- | --- |
| `map/small/<geometry>.png` | 100×60 | Existing card thumbnail, unchanged |
| `map/screen/<geometry>.dds` | 2560×1600 | Default landscape hover picture |
| `map/<geometry>.png` | 300×300 | Optional square minimap hover |

Dimensions were read from the PNG/DDS headers for `01_karelia` at asset commit
`3605bd36c53d10c16be5d93f5414aa5fd129e84e`; other geometries can differ or lack a
variant. The catalogue has additional `battleLoading`, `entry`, `respawn`,
`stats` and mode-specific map folders. The resolver uses the two variants with
the verified purposes below, rather than guessing which other art fits a map.

## Primary client evidence

- [getArenaImage](https://github.com/izeberg/wot-src/blob/5e721e36891c80d8d51a431164960c863641ee63/sources/res/scripts/client/gui/shared/utils/functions.py#L185-L192)
  selects `R.images.gui.maps.icons.map`, an optional `dyn(subdir)` and
  `num(geometryName)`. The large picture follows this exact lookup with
  `subdir='screen'`; the small thumbnail keeps `subdir='small'`.
- [MinimapLobby](https://github.com/izeberg/wot-src/blob/5e721e36891c80d8d51a431164960c863641ee63/sources/res/scripts/client/gui/Scaleform/daapi/view/lobby/MinimapLobby.py)
  selects the same map-root geometry resource for the lobby's tactical minimap
  and passes it as the minimap texture. This is separate from landscape art.
- The [screen DDS](https://github.com/Kurzdor/wot.assets/blob/3605bd36c53d10c16be5d93f5414aa5fd129e84e/gui/maps/icons/map/screen/01_karelia.dds)
  and [default minimap PNG](https://github.com/Kurzdor/wot.assets/blob/3605bd36c53d10c16be5d93f5414aa5fd129e84e/gui/maps/icons/map/01_karelia.png)
  are present at the pinned asset revision.
- Native [Gameface maps-training result](https://github.com/Kurzdor/wot.assets/blob/3605bd36c53d10c16be5d93f5414aa5fd129e84e/gui/gameface/_dist/production/mono/maps_training/maps_training_result/bundle.js)
  uses `img://gui/maps/icons/map/screen/…dds` as `backgroundImage`. The mod keeps
  this native texture loader and existing `background-size:contain` rendering.

## Runtime contract and limits

`maps.preview_mode` accepts exactly `image` (default) or `minimap`. Runtime passes
the validated choice to the presentation-only resolver. Map rows can receive
`visual.preview_src` and `visual.preview_mode`; `visual.src` remains the small
card image. Battle and vehicle artwork is unaffected.

Every selected resource must exist in R and pass `ResMgr.isFile` for the returned
local PNG or its same-name DDS backing. A missing preferred variant falls back
to the existing thumbnail for that same geometry, with retries in later
snapshots. Successful preferred lookups are cached separately by geometry and
mode. The frontend independently accepts only local map/vehicle texture paths;
unsafe preview paths fall back to the thumbnail.

Landscape hover retains the fourfold thumbnail proportions. A resolved minimap
uses a square whose side is four times the thumbnail width, reduced when needed
to fit the panel. Leaving the thumbnail still closes the hover immediately.

The local client ultimately controls artwork availability. Tests cover registry
selection, PNG/DDS checks, delayed availability, fallback, config validation,
snapshot isolation and the actual shipped JavaScript's safe source selection
and bounded square preview. They do not replace an in-game texture-render test.
