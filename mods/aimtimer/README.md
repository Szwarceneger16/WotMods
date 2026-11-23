# GRZ AimTimer

AimTimer displays the estimated time for the current aiming circle to settle. Its position editor offers third-person, sniper and artillery previews with stock crosshairs, zoom, dispersion examples and vehicle mechanics. Third-person, sniper and artillery each have a saved position. Both artillery cameras share one position.

AimTimer pokazuje szacowany czas skupienia celownika. Pozycję odczytu można ustawić osobno dla widoku trzeciej osoby, snajperskiego i artyleryjskiego.

## Install

1. Close World of Tanks.
2. Extract `GRZ_AimTimer-v<version>.zip` into the folder containing `WorldOfTanks.exe`. Keep the nested `mods/<client>/` paths. The fixed installed filename is `GRZ_AimTimer.wotmod`.
3. If you used a preview build, remove the old `GRZ_AimTimer_v*.wotmod` file for this mod from the active game version folder before starting the client.

To configure it, open **Aim time** in the garage footer. In battle hold Ctrl and use the controls next to the readout.

The ZIP includes the same OpenWG Gameface package used by compatible WotMods for the garage button. GRZ AimTimer works without the other reticle mod. When both are present, the position editor shows the other readout at its saved position and highlights overlap between active readouts. Moving one readout saves its own position.

AimTimer pauses measurement while the battle HUD is hidden or the player no longer controls a live vehicle. The readout follows the client's crosshair position events between measurements.

Settings and a short support log are stored locally under `%APPDATA%/GRZ_AimTimer` when available. The release package has no detailed battle tracing or network telemetry and does not change aiming or gun controls. The preview was checked with WoT EU 2.4.1.1. Retargeting an installer for a new game directory does not guarantee runtime compatibility.

## Build

From the repository root, with CPython 2.7.18:

```sh
python2.7 mods/aimtimer/tools/build_wotmod.py
python3 scripts/release_installers.py package pr-artifact --source mods/aimtimer/dist --mod aimtimer --client-version 2.4.1.1
```

The [shared preview build](../../scripts/reticles) documents the approved scene assets, optional local-client check and PR tests.
