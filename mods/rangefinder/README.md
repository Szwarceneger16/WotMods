# GRZ Rangefinder

Rangefinder displays the estimated distance for the aim point or visible target. Its position editor offers third-person, sniper and artillery previews with stock crosshairs, zoom, dispersion examples and vehicle mechanics. Third-person, sniper and artillery each have a saved position. Both artillery cameras share one position.

Dalmierz pokazuje odległość do punktu celowania lub widocznego pojazdu. W ustawieniach można ukryć fabryczny odczyt odległości.

## Install

1. Close World of Tanks.
2. Extract `GRZ_Rangefinder-v<version>.zip` into the folder containing `WorldOfTanks.exe`. Keep the nested `mods/<client>/` paths. The fixed installed filename is `GRZ_Rangefinder.wotmod`.
3. If you used a preview build, remove the old `GRZ_Rangefinder_v*.wotmod` file for this mod from the active game version folder before starting the client.

To configure it, open **Rangefinder** in the garage footer. In battle hold Ctrl and use the controls next to the readout. **Hide the stock distance readout** is off by default. It hides the duplicate from the client while the mod displays its reading.

The ZIP includes the same OpenWG Gameface package used by compatible WotMods for the garage button. GRZ Rangefinder works without the other reticle mod. When both are present, the position editor shows the other readout at its saved position and highlights overlap between active readouts. Moving one readout saves its own position.

Settings and limited diagnostics are stored locally under `%APPDATA%/GRZ_Rangefinder` when available. The mod has no network telemetry and does not change aiming or gun controls. The preview was checked with WoT EU 2.4.1.1. Retargeting an installer for a new game directory does not guarantee runtime compatibility.

## Build

From the repository root, with CPython 2.7.18:

```sh
python2.7 mods/rangefinder/tools/build_wotmod.py
python3 scripts/release_installers.py package pr-artifact --source mods/rangefinder/dist --mod rangefinder --client-version 2.4.1.1
```

The [shared preview build](../../scripts/reticles) documents the approved scene assets, optional local-client check and PR tests.
