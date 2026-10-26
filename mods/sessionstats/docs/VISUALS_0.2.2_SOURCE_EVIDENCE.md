# Thumbnails 0.2.2 — identifiers and client resources

Reviewed on 2026-10-20. `visuals.py` runs only when constructing UI snapshots. It
changes neither storage nor calculations, and reads existing vehicle/map-geometry
identifiers, including old records. Display names describe images only.

## Versions and verified API

Client mirror: `izeberg/wot-src`, commit
`5e721e36891c80d8d51a431164960c863641ee63`; `.version_name`: `2.4.1.5493`.
This is not a stable mod API declaration.

| Element | Verified behavior and source |
| --- | --- |
| Stored numeric `typeCompDescr` | [getVehicleType](https://github.com/izeberg/wot-src/blob/5e721e36891c80d8d51a431164960c863641ee63/sources/res/scripts/common/items/vehicles.py#L3165-L3171) resolves an integer type descriptor from cache. [VehicleType](https://github.com/izeberg/wot-src/blob/5e721e36891c80d8d51a431164960c863641ee63/sources/res/scripts/common/items/vehicles.py#L1971-L1974) retains `name`/`compactDescr`. The resolver converts decimal text to an integer and requires descriptor agreement so malformed ID bits cannot select another vehicle. |
| Vehicle icon | [getIconPath](https://github.com/izeberg/wot-src/blob/5e721e36891c80d8d51a431164960c863641ee63/sources/res/scripts/client/gui/shared/gui_items/Vehicle.py#L2244-L2249) uses `R.images.gui.maps.icons.vehicle.dyn(...)`, `exists()` and `backport.image`. [getIconResourceName](https://github.com/izeberg/wot-src/blob/5e721e36891c80d8d51a431164960c863641ee63/sources/res/scripts/client/gui/shared/gui_items/Vehicle.py#L2280-L2281) supplies a key from the technical vehicle name. `vehicle.small` is an alternative image of the same vehicle; `noImage` is unused. |
| Map thumbnail | [getArenaImage](https://github.com/izeberg/wot-src/blob/5e721e36891c80d8d51a431164960c863641ee63/sources/res/scripts/client/gui/shared/utils/functions.py#L185-L192) selects `R.images.gui.maps.icons.map`, optional `dyn(subdir)`, then `num(geometryName)`. The [native training list](https://github.com/izeberg/wot-src/blob/5e721e36891c80d8d51a431164960c863641ee63/sources/res/scripts/client/gui/Scaleform/daapi/view/lobby/trainings/trainings_list_base.py) uses `small`. The resolver follows this, falling back to the same geometry's default image. |
| Registry and path | [R](https://github.com/izeberg/wot-src/blob/5e721e36891c80d8d51a431164960c863641ee63/sources/res/scripts/client/gui/impl/gen/resources/__init__.py) comes from `GuiApplication`'s resource manager. [backport.image](https://github.com/izeberg/wot-src/blob/5e721e36891c80d8d51a431164960c863641ee63/sources/res/scripts/client/gui/impl/backport/backport_r.py#L52-L53) delegates to `wulf.getImagePath`; [getAbsoluteUrl](https://github.com/izeberg/wot-src/blob/5e721e36891c80d8d51a431164960c863641ee63/sources/res/scripts/client/gui/shared/utils/functions.py#L232-L233) replaces relative `../` with `img://gui/`. |
| Local-file check | The [native loading screen](https://github.com/izeberg/wot-src/blob/5e721e36891c80d8d51a431164960c863641ee63/sources/res/scripts/client/gui/game_loading/state_machine/states/slide.py#L36-L37) uses `ResMgr.isFile`. The resolver checks the registry path and, when the logical PNG is absent, a same-name DDS. URLs are emitted only after a positive existence check. |

## Actual images and loader

Resource mirror: `Kurzdor/wot.assets`, commit
`3605bd36c53d10c16be5d93f5414aa5fd129e84e`;
[.metadata_version](https://github.com/Kurzdor/wot.assets/blob/3605bd36c53d10c16be5d93f5414aa5fd129e84e/.metadata_version):
`2.4.1.0 #977`.

- [map/small/01_karelia.png](https://github.com/Kurzdor/wot.assets/blob/3605bd36c53d10c16be5d93f5414aa5fd129e84e/gui/maps/icons/map/small/01_karelia.png)
  has a 100×60 PNG header; default [map/01_karelia.png](https://github.com/Kurzdor/wot.assets/blob/3605bd36c53d10c16be5d93f5414aa5fd129e84e/gui/maps/icons/map/01_karelia.png)
  is 300×300. Prefer the small variant.
- Exact [vehicle/uk-GB31_Conqueror_Gun.png](https://github.com/Kurzdor/wot.assets/blob/3605bd36c53d10c16be5d93f5414aa5fd129e84e/gui/maps/icons/vehicle/uk-GB31_Conqueror_Gun.png)
  and [vehicle/small/uk-GB31_Conqueror_Gun.png](https://github.com/Kurzdor/wot.assets/blob/3605bd36c53d10c16be5d93f5414aa5fd129e84e/gui/maps/icons/vehicle/small/uk-GB31_Conqueror_Gun.png)
  exist. Paths come from `R`/backport rather than manual construction.
- Native [Gameface maps_training_result/bundle.js](https://github.com/Kurzdor/wot.assets/blob/3605bd36c53d10c16be5d93f5414aa5fd129e84e/gui/gameface/_dist/production/mono/maps_training/maps_training_result/bundle.js)
  assigns `backgroundImage` from `img://gui/maps/icons/map/screen/…dds`, confirming
  the native scheme and DDS support. It is not replaced with a `coui://` loader.

Images were inspected as references only. No client artwork is bundled; runtime
performs no image-network requests.

## Contract and resilience

`row.visual` has `kind`, `src` and `alt`. Allowed families are exclusively
`img://gui/maps/icons/vehicle/` and `img://gui/maps/icons/map/`. Missing/invalid
resources omit `visual` while preserving names/statistics. A battle prefers its
stored vehicle, then its own map. Images are neither matched by display name nor
borrowed from another record. One image failure does not interrupt adjacent rows.
Failed reads can retry in later snapshots after resources become ready.

## Verification

`tests/test_visuals.py`: 21 tests on Python 3 and 2.7.18 cover numeric descriptors,
invalid ID aliasing, small maps, missing nodes/files, PNG/DDS, rejected URLs, late
resource readiness, old records and Runtime snapshots without history/stat changes.

Resource doubles match the reviewed API without running the native C++ loader or
current WoT client. Every thumbnail's display and actual resource mapping still
required an in-game 0.2.2 check at this historical checkpoint.
