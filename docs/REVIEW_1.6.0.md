# Stay Sharp Medkit Reminder 1.6.0 — code review / hardening

## Baseline

The user confirmed version 1.5.0 in the game, including aiming views. This release changes only panel lifecycle attachment and compatibility checks. The pulse algorithm and DDS resources remain unchanged.

## 1. Event subscriptions

**Version 1.5:** replaced `ConsumablesPanel._populate` and `ConsumablesPanel._dispose` on the WoT class.

**Version 1.6:** two read-only listeners on the global `g_eventBus`:

- `ComponentEvent.COMPONENT_REGISTERED` (`event.alias == BATTLE_VIEW_ALIASES.CONSUMABLES_PANEL`) → `_activate`.
- `ComponentEvent.COMPONENT_UNREGISTERED` (`event.componentPy is _panel`) → `_deactivate`.

The WoT client uses this event pattern itself, for example in `markers_gui_provider.py`. Registration follows `componentPy.create()`; unregistration is emitted before `viewPy.destroy()`.

Supporting sources are community client-code mirrors, not an officially stable public API:

- https://github.com/izeberg/wot-src/blob/EU/sources/res/scripts/client/gui/Scaleform/framework/entities/BaseDAAPIComponent.py
- https://github.com/izeberg/wot-src/blob/EU/sources/res/scripts/client/gui/Scaleform/framework/entities/DisposableEntity.py
- https://github.com/izeberg/wot-src/blob/EU/sources/res/scripts/client/gui/Scaleform/daapi/view/battle/shared/component_marker/markers_gui_provider.py
- https://github.com/izeberg/wot-src/blob/EU/sources/res/scripts/client/gui/Scaleform/genConsts/BATTLE_VIEW_ALIASES.py

This avoids overwriting WoT method implementations, collisions with mods patching the same methods and invocation-order problems. Future clients may change or remove these events; the mod then disables itself rather than automatically falling back to monkeypatching.

## 2. Compatibility adapter

Before activation, `_panel_contract(panel)` checks:

- Panel identifiers/ranges and 12 slots.
- `_getPanelSettings()` and the standard layout (`0`).
- Availability of `as_isVisibleS()`.
- Presence/type of `_cds` and a valid 12-bit `_mask`.
- The `_equipmentsGlowCallbacks` dictionary, preserving native WoT warning priority.

`_slot_contract(panel, slot, compact)` verifies that the ready medkit occupies an actual slot in 3..5, that the mask includes the slot and that its compact equipment identifier matches the HUD. Repeated checks during battle cover panel/configuration changes.

`_graphics_contract()` checks `GUI.Simple`, required enums, `ResMgr.isFile`, callback support and BigWorld functions before touching the native renderer. Existing `_preflight_frames` also validates every DDS resource.

**Fail-closed behavior:** unknown layouts disable the overlay and log a specific reason. The mod does not guess layouts or move equipment slots.

## 3. Unchanged behavior

- All 21 128x128 DDS ARGB8888 frames match the 1.5.0 package byte for byte.
- `TEXTURE_TEMPLATE`, `FRAME_LEVELS=20`, `HALF_PULSE=2.0`, `PULSE_TICK=0.1`.
- The 1.5.0 `GUI.Simple` and `hud.addChild` logic.
- Checks of `playerVehicleID`, `perkEffects['equipment']`, `item.canActivate(avatar=player)` and native warning priority.
- No sounds, shaders, DLLs, `battle.swf` replacement or extra installation folders.

## 4. Validation

- 137/137 offline tests: 82 logic regressions, 35 compatibility/event checks and 20 packaging checks.
- The entire `.wotmod` uses ZIP_STORED, has 23 entries and valid metadata.
- The bytecode loader retains the CPython 2.7 format verified in 1.5.0, with an ASCII script embedded in `.pyc`.
- Tests simulate missing/incompatible APIs, unknown layouts, invalid masks/glow dictionaries, missing enums and listener-registration failures.
- **No live WoT client test was performed.** The 137/137 result describes offline checks, not an engine-stability guarantee.

## 5. Limitations

- The mod still depends on private `_cds`, `_mask`, `perkEffects`, `as_isVisibleS` and the Flash bridge. A HUD redesign may break it.
- If a future layout changes, disabling the pulse is the correct response; placing a frame over the wrong consumable is not.
- A different WoT Python interpreter will invalidate the current `.pyc` and require a new build.
- No safe universal technique guarantees full compatibility with unknown future game updates.
