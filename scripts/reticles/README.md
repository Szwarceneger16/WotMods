# Shared reticle preview build

AimTimer and Rangefinder use separate client namespaces, Gameface resources, local settings and installers. Both build from the same preview inputs. The companion mod is optional and is only queried when the game has already started it.

The art directory contains the reviewed preview backgrounds used by both packages. These are composed Full HD scene assets without player names, battle HUD records or personal metadata. Labels that remain refer to vehicle models. The checksums cover the 16 scene images and CI verifies their PNG structure inside each generated package. One checked asset archive contains the 105 identical HUD textures used by both mods. The stock HUD, crosshair widgets and original mechanics are loaded from the installed client at runtime.

The two pinned Flash files are the mod's preview adapters. The generator in `native/` uses installed WoT EU resources to verify names, dependencies and supported timelines. It preserves the adapters' owned non-code resources. To check the adapters against a supported installed client, add `--game-root <game-directory>` to a build. A normal build reproduces the reviewed packages without a WoT installation.

Each mod has a separate version file and PR workflow. The workflow builds twice with the verified CPython 2.7.18 environment, compares the results, tests the settings editor, and verifies one installable ZIP. The release coordinator publishes registered mods through the existing shared process.
