# Session Stats for World of Tanks

Version 0.3.0 source: independent sessions, WN8, XP, finances including bonds,
vehicle/map/battle grouping, result health checks, local logging and configurable
appearance. Full guide: [README_PL.txt](README_PL.txt); history: [ZMIANY.txt](ZMIANY.txt).
These legacy filenames are retained for existing package and documentation links;
their contents are English.
Both default scopes and manual resets are isolated per account and region.
`"sessions": {"instance_tab": true}` displays the optional installation tab.
Its shared history and independent manual reset persist across game restarts;
the tab is hidden by default. See [ACCOUNT_SESSIONS.md](docs/ACCOUNT_SESSIONS.md).
Import review fixes: [REVIEW_FIXES_PR3.md](docs/REVIEW_FIXES_PR3.md).
Independent stability/coexistence review and corrections: [INDEPENDENT_SAFETY_REVIEW_PR3.md](docs/INDEPENDENT_SAFETY_REVIEW_PR3.md).
Incremental saves, paged history, staged startup with durable pending results,
benchmarks and remaining limits: [HISTORY_PERFORMANCE.md](docs/HISTORY_PERFORMANCE.md).
Windows journal creation and checksum-verified recovery of affected saves:
[WINDOWS_JOURNAL_RECOVERY.md](docs/WINDOWS_JOURNAL_RECOVERY.md).

## Installation and integration with other mods

Download the **Session Stats** installation ZIP from [Releases](https://github.com/Szwarceneger16/WotMods/releases).
Place the `.wotmod` in the active `mods/<game_version>/` directory and configuration
in **`mods/configs/grz.sessionstats.json`**. This path survives client-version changes.
Preserve your custom JSON when updating. OpenWG
Gameface 1.2.2 is included under MIT; install only one copy even if another mod
uses it. Remove the old Session Stats package without deleting AppData history.
The Session Stats `.wotmod` itself works without OpenWG: collection and the native
panel opened with **Ctrl+F10** remain available; only the garage footer button needs
OpenWG. Its shared Gameface resource still needs compatibility testing with the
other UI frameworks in a mod pack.

Session Stats uses its own `mod_grz_session_stats` entrypoint, `grz_session_stats`
package, `grz.sessionstats` resources and data/log directory. Medkit Reminder has
a separate entrypoint and is not a dependency. Built packages have disjoint
resource paths; coexistence in the actual client still requires an in-game test.

## Local build

Packaging requires Python 3.9+ and CPython 2.7.18 for game bytecode. Python 2.7 is
used only for compatibility tests and compilation, without network access.
Run from this directory:

```sh
python3 -m unittest discover -s tests -v
/path/to/python2.7 -m unittest discover -s tests -v
python3 tools/make_preview.py
python3 tools/build.py --python27 /path/to/python2.7
```

`dist/` contains six assets: the mod `.wotmod`, complete installation ZIP with
sources, configuration JSON, OpenWG, `BUILD.json` and `SHA256SUMS.txt`. The builder
downloads no dependencies and verifies OpenWG's SHA-256. Compiled bytecode uses
virtual paths without exposing the build computer's filesystem paths.

Previews and browser tests use only synthetic data from `tools/make_preview.py`.
Playwright is the test dependency; optional `GRZ_CHROME` selects a Chromium
executable. These tests do not run the real WoT client.

## Privacy and compatibility

See [PUBLICATION_PRIVACY.md](docs/PUBLICATION_PRIVACY.md). Do not publish local
logs, player history, personal configuration or screenshots. Runtime account
identifiers used to separate histories remain local; they are neither repository
data nor telemetry.
Mod license: [GPL-3.0](LICENSE.txt); dependencies: [THIRD_PARTY.txt](THIRD_PARTY.txt).
This license does not alter the terms of other mods in the repository.

WoT interfaces may change. Health checks cannot guarantee detection of changed
field meanings when types and structures remain the same. The user tested 0.2.4
and has also confirmed a preceding build works in game. The 0.2.9 UI/language
changes and 0.2.12 Windows storage correction still require a current-client test
after automated validation.

## Interface languages and optional configuration

The default `"language": "auto"` follows the game language, with English as the
fallback. Explicit `en`, `ru`, `fr`, `pl`, `de`, `es` or `uk` in the root `language`
property take priority. Existing `"language": "en"` files stay English; change
that value to `"auto"` to follow the game.
Use the Language dropdown in the panel to change this same configuration value.
The choice is saved to `mods/configs/grz.sessionstats.json` and applied immediately;
all other config values and battle history are preserved. Manual edits still work
when the panel is reopened or Refresh is selected.
All seven translation catalogs are bundled inside the `.wotmod`. External language
catalogs are not read, copied or installed. See [language configuration](docs/LANGUAGES.md).

The main configuration is optional too. Include only fields you want to override;
omitted fields and nested settings use defaults. For example:

```json
{"language": "pl", "scroll": {"speed_multiplier": 1.5}}
```

Save in `mods/configs/grz.sessionstats.json`, then reopen the panel or click Refresh.
The mod creates a missing main file using defaults, or copies the legacy JSON beside
the active package if present. Existing central files always win during initialization; only an explicit GUI language selection updates their language property.
The packaged language catalog is fixed to the seven supported choices; old external language files are ignored.
Appearance fields and validation: [APPEARANCE_CONFIG.md](docs/APPEARANCE_CONFIG.md).

Battle outcomes use unchanged local WG notification artwork with separate captions.
No game artwork is edited, bundled or downloaded at runtime. Missing resources
retain text outcomes. See [0.2.9 UI and language evidence](docs/UI_0.2.9_SOURCE_EVIDENCE.md).

### Result ordering and Tiers

Use the date dropdown between Previous and Next for newest/oldest ordering. The following row contains Statistic (Min/Avg/Max), Sort by (Off/Base XP/Received XP/Credits net/WN8), and Order (Ascending/Descending). With Sort by set to Off, date ordering applies; the other two controls are disabled. Equal metric values use the selected date order, with stable ID ties. Missing metric values sort last.

Sorting covers the complete selected period before pages of 40 rows are sent to the UI, and changes return to page one. Vehicles, Maps, Battles and the new Tiers tab have independent choices in each session scope, including Installation. Tiers includes XI and preserves an unknown-tier group for incomplete metadata. WN8 Min/Avg/Max uses individual battle WN8, and credits use per-battle net earnings, including losses.

The selectors use local Gameface-compatible dropdowns with keyboard navigation. See [sorting and tier behavior](docs/SORTING_AND_TIERS.md).
