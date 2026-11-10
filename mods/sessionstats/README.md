# Session Stats for World of Tanks

Version 0.5.1 source: independent sessions, WN8, XP, finances including bonds,
vehicle/map/battle grouping, result health checks, local logging and configurable
appearance. Full guide: [README_PL.txt](README_PL.txt); history: [ZMIANY.txt](ZMIANY.txt).
These legacy filenames are retained for existing package and documentation links;
their contents are English.
The account tabs are **Since launch** and **Timeline**. Timeline opens on the full
history. Use **Create time point** in the title bar, then pick **From** and **To**
to filter by battle start time. Either selector also accepts **Custom date**:
enter `YYYY-MM-DD HH:mm` in the computer's local time and choose **Apply**.
Ranges are half-open: **From** is included and **To** is excluded. The start must
be earlier than the end. **Beginning of history** and **Now** leave the
corresponding end open.
Earlier manual resets appear as time points and saved battles remain available.
The account and region determine which history and time points are shown.

An expanded **Maps** card lists battles on that map within the selected period.
**Show battle** opens the chosen result in **Battles**. **Less** collapses an
expanded card.

In **Battles → More**, the card lists recorded daily, bonus, weekly, personal
campaign and event missions, along with the active Crucible stage and its
reported result. Personal missions show the operation name and completion with
honors when the additional objective is confirmed. The card also shows Battle
Pass points and the available bonus breakdown. The finance tables include
vehicle and account-level bonds reported for each recorded Random Battle.
Older saved battles may have no mission or bonus details. All four corners and all four edges
resize the window and keep its size across garage openings during the same
game process. The panel follows the resolved WoT interface scale.

The native Random Battle overview also shows **WN8** in its bottom personal
statistics strip. The label stays visible while a spinner occupies the value
slot during processing. It then shows the displayed battle's rating, including
zero, or a dash when the required data is unavailable. The garage button sits
immediately to the right of the built-in session statistics in the existing
control row, preserving the native notification spacing.

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
panel opened with **Ctrl+F10** remain available; the garage footer button and the
post-battle WN8 display need OpenWG. Its shared Gameface resource still needs compatibility testing with the
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

## Data coverage and notices

An `x/y` count means that a value is available for `x` of the `y` recorded battles.
The headline counts received results; XP, WN8 and each financial column have their
own coverage. Missing values do not become zero. Partial summaries include a
localized explanation, and the individual counts carry matching descriptions.
Data notices are deduplicated after translation, including older Polish history;
the footer counts the distinct messages actually displayed. Saved records are
not rewritten by this presentation change.

The downloaded ZIP retains its release version, while the installed mod is always
`grz_sessions_stats.wotmod`. Close the game and remove old `grz.sessionstats_*.wotmod`
files and the earlier `GRZ_Session_Stats.wotmod` test file once when switching to
this name. Later updates overwrite the same file.
Keep your existing `mods/configs/grz.sessionstats.json` when updating.

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

Card widths can be set independently in logical pixels (before the game's UI
scale), from 480 to 900. Omitted values use Battles 500, Vehicles 560, Maps 560,
and Tiers 520. Cards within a tab keep the same width; the layout switches to two
columns only when both cards and the central gap fit. The complete previous
untouched width preset follows these compact defaults on load; customized or
partial card settings remain unchanged. For example:

```json
{"cards": {"battles": 580, "vehicles": 560}}
```

The layout always has at most two columns. When two wider cards fit, it switches
both columns to a second fixed width, rather than adding another column or
stretching cards continuously. Each tab defaults to 720 logical pixels in this
wide preset; `wide_cards` accepts 480–1200 independently per tab. A wide value
smaller than the tab's ordinary card width uses the ordinary width instead.
The untouched previous 800-pixel preset follows the new 720-pixel default on
load; partial and customized presets remain unchanged, and the file is preserved.

```json
{"wide_cards": {"battles": 720, "vehicles": 720, "maps": 720, "tiers": 720}}
```

The title bar includes Maximize/Restore and a background transparency slider.
Transparency ranges from 0 (opaque, the default) to 100 (fully transparent
background); text and controls retain their own opacity. Window controls save
`window.background_transparency`, `window.maximized`, `window.restored_width`
and `window.restored_height` to the same configuration, preserving unrelated
fields. Restored dimensions use logical pixels. A smaller viewport temporarily
clamps the surface without discarding the saved size.

Every two-column tab uses staggered cards connected to a dashed central axis.
Several battle cards can keep More open together. Expanded battles use the
next available column in sorted order, so consecutive battles fill the space
beside a tall card and their axis markers retain chronology. With all details
closed, cards use their usual alternating layout. Refreshing or resizing preserves open cards;
switching accounts clears their open state.
The three main statistics stay horizontal; the compact performance and finance
tables wrap together as one centered group. Summary rows remain centered when
the window cannot fit them together. Changing the period returns to the top;
incoming result updates preserve the current scroll position. Matching finance coverage is shown once in
the table header; differing coverage remains beside its own row or value.

Information icons show explanations after one second over the icon. Moving
across a statistics section does not open a tooltip. Battle bonuses share one
row per source with separate resource columns; premium credit/XP multipliers
share a row too. Battle Pass is a compact strip above the details. A wider bonus
table sits beside the mission cards; each mission has its name, progress and
description inside one outline. These sections wrap when the card cannot fit
them without crowding, including unusually large numerical rewards.
Mission progress shows confirmed per-battle increments and known current/target
counters with their objective labels. Explicit unchanged counters show no
progress; missing historical counters remain unavailable. A current/target
snapshot alone never becomes an invented battle increment. Completion and
honors remain visible. See [mission progress source evidence](docs/MISSION_PROGRESS_SOURCE_EVIDENCE.md).

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

Vehicle cards provide the same paginated battle history and Show battle links as
map cards. The selected battle keeps a visible orange frame across snapshot
refreshes in the same period. Active net-credit sorting displays the exact
per-battle Min/Average/Max value beside the vehicle metadata; the finance table
still reports period totals.

### Continuous result pages

Scrolling near either loaded edge fetches the adjacent 40-result page with a
dashed, localized page-number separator. Earlier pages are inserted above the
current cards while preserving their visible position. A spinner marks its
loading boundary; failed requests offer Retry. Previous/Next scroll to an already
loaded page or fetch the adjacent page. The native double-chevron button returns
to the full summary and page one of the selected result order, fetching it when
navigation initially opened a later page.
The grouping and sorting bar pins inside the scroll viewport. Filter changes
retain the current pixel offset, rebuilding the loaded window atomically for
a new ordering or index revision. New account histories start at the top.

Map/vehicle history pagers update their fixed-height ten-row viewport in place,
including cards on an earlier loaded global page. Battle navigation pulses its
overlay for five seconds, then leaves it 30% transparent. The card's solid orange
border remains visible through native focus/blur events and any background
transparency setting. An explicit outside click or a changed view/period clears
the selection. Wider battle cards keep the bonus matrix
at 308 logical pixels and assign the additional width to mission details.
