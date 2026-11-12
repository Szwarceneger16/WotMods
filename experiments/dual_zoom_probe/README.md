# Dual Zoom Engine Probe (experimental, v0.1.0)

An independent **research build** for World of Tanks EU. It does not join the
WotMods shared Releases, change GitHub Actions, install native code, or affect
the existing mods. It is not a validated gameplay mod.

## What is implemented

- One-time, bounded, read-only introspection of relevant native engine APIs:
  `BigWorld` scene renderers, render targets, cameras and projection;
  `GUI` textures, `Simple`, `Gobo`, and display interfaces.
- A second **native 3D scene render** via `BigWorld.PySceneRenderer`, but **only
  if this API still exists and works** in the installed client. The same native
  sniper camera is reused for both passes; a second per-frame Python camera
  controller is unnecessary.
- The normal sniper view stays at **x2 when the second render is active**.
  Mouse wheel and native zoom-key commands change the inset only:
  x2, x4, x8, x16, x25, optionally x32. A 2 px decorative frame marks the inset.
- Independent scene-to-texture FOV, corrected for the inset's pixel size. At
  inner x2 the projected pixel scale matches the outer x2 screen. No cropping,
  pixel enlargement, capture of the screen, or third-party rendering DLL.
- Engine-managed texture refresh (no high-frequency Python `callback` loop).
  One inexpensive once-per-second check runs while the renderer is active to
  respond to screen resizing and native zoom interference. The optional
  `skip_frames` knob may reduce GPU work at the cost of reticle latency.
- Complete cleanup of this mod's own GUI roots, callbacks and renderer on
  sniper-mode exit or toggle-off. Failures restore ordinary sniper controls.
- Local-only, capped diagnostics with no player names, account data, network
  traffic, raw screenshots, memory dumping, telemetry, or secrets.

## Current compatibility warning

The *current EU client Python source* exposes `SniperControlMode` with
`handleMouseEvent(dx, dy, dz)` and the native `SniperCamera` FOV/zoom methods.
However, `PySceneRenderer` is documented by the historical **BigWorld Engine**
API, not guaranteed to be exported by the **current WoT retail client**.
The mod explicitly tests whether this function is available and whether an
instance can be created. If absent or broken, it logs that result; it does not
substitute a fake digital zoom or attempt DLL injection.

In a successful experiment the inset may initially cover the stock aiming
reticle. The actual weapon reticle, dispersion circle, synchronized shot point,
shaders, UI depth ordering, and any game-specific visual effects have **not**
been verified. **Do not use this experimental view to aim in live battles.**

Official Fair Play rules do not explicitly certify this dual-view capability.
Do not use it in multiplayer matches without Wargaming's approval. The default
configuration limits the renderer to replay mode, and requires explicit opt-in.

## Build, install, probe

From the repository root:

```bash
python3 -m unittest discover -s experiments/dual_zoom_probe/tests -v
python3 experiments/dual_zoom_probe/build.py
```

1. Close WoT. Copy the produced `com.grz.dualzoomprobe_0.1.0.wotmod` into the
   `mods/<your-current-game-version>/` directory, next to the existing mods.
2. Launch WoT. Even with the renderer disabled, the first probe writes names
   of relevant exported APIs to `%LOCALAPPDATA%\DualZoomProbe\capabilities.json`
   and logs to `%LOCALAPPDATA%\DualZoomProbe\diagnostics.log`.
3. To test the real renderer, copy `config.example.json` to
   `%LOCALAPPDATA%\DualZoomProbe\config.json`, change
   `enable_native_renderer` to `true`, **keep `replay_only` set to `true`**,
   and restart WoT.
4. Load a replay and switch to sniper view. If supported, a 400 x 240 px
   live-rendered rectangular inset appears at the center of the screen.
   Scroll to change only its zoom.
5. Press **Ctrl+Alt+D** in sniper view to refresh the capability report, or
   **Ctrl+Alt+P** to toggle native inset rendering for that session.
6. After exiting the replay, inspect `capabilities.json` (`native_render` is
   `started`, `missing_api`, `replay_only`, or `failed`) and `diagnostics.log`.
   Only share these two small, local diagnostics files, not the full game log.

Do not run the test if the game is unstable. Remove this `.wotmod` to uninstall.
The mod makes no changes to original game files. It restores the native camera
zoom preferences it temporarily overrides when the inset is turned off.

## Options and trade-offs

| Setting | Default | Meaning |
|---|---:|---|
| `enable_native_renderer` | `false` | Explicit GPU renderer opt-in |
| `replay_only` | `true` | Prevent experimental rendering in normal matches |
| `width`, `height` | `400`, `240` | Inset pixel dimensions; bounded to 300,000 pixels |
| `start_zoom` | `2` | Initial inset zoom multiplier |
| `max_zoom` | `25` | `32` exists for controlled experimentation only |
| `skip_frames` | `0` | 0 = update every engine frame; 1-3 skips frames |
| `staggered` | `false` | Ask the historical engine API to spread render updates |

**Why reusing the same camera helps:** the engine computes the world camera
transform once. `PySceneRenderer` reuses that camera with a separate field of
view and render target, so Python does not poll/duplicate its matrix every
frame. A second GPU scene pass is still required and can be expensive even
at small texture sizes; benchmark frame time before promising performance.

### References inspected (12 November 2026)

- Current decomposed WoT EU camera/control implementation:
  [SniperCamera.py](https://github.com/izeberg/wot-src/blob/EU/sources/res/scripts/client/AvatarInputHandler/DynamicCameras/SniperCamera.py),
  [control_modes.py](https://github.com/izeberg/wot-src/blob/EU/sources/res/scripts/client/AvatarInputHandler/control_modes.py).
- Recent community documentation on WoT 2.0 Gameface/Flash/Python layers:
  [Python, Flash, and Gameface](https://wgmods.dev/docs/wot/getting-started/python-flash-gameface).
- Historical BigWorld engine reference:
  [PySceneRenderer](https://howarduong.github.io/github.io/doc/api_python/client_python_api/doc/PySceneRenderer.html).
- [Wargaming Fair Play policy](https://worldoftanks.eu/en/content/guide/fair-play/prohibited-mods/).

This experimental module intentionally has **no CI or production Release
integration** until runtime compatibility and game-policy acceptance are known.
