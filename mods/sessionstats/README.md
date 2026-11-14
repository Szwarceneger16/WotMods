# Session Stats for World of Tanks

Version 0.9.9 source: independent sessions, WN8, XP, finances including bonds,
vehicle/map/battle grouping, result health checks, local logging and configurable
appearance. Full guide: [README_PL.txt](README_PL.txt); history: [ZMIANY.txt](ZMIANY.txt).
These legacy filenames are retained for existing package and documentation links;
their contents are English.
The account tabs are **Since launch** and **Timeline**. Timeline opens on the full
history. Use **Create time point** in the title bar, then pick **From** and **To**
to filter by battle start time. Either selector also accepts **Custom date**:
edit the date and time inside that same control, using the displayed WoT client
format (for example `dd.mm.yyyy HH:mm`, or `mm/dd/yyyy hh:mm AM`). Press Enter to
apply a typed value, or open the adjacent calendar button to choose a day and time.
Click the month or year heading for a selection grid. The graphical clock stays
below the calendar; its hour/minute controls and short hints explain selection.
Future dates/times and choices outside the other range boundary are disabled;
From must be earlier than To. Typed dates follow the same range restrictions.
Calendar words follow the selected interface language; the client supplies numeric
date/time preferences and week start.
Explicit `date_time` configuration overrides each automatic setting independently;
see [client date and clock formatting](docs/CLIENT_DATE_TIME.md).
The separate dropdown button still offers saved time points.
Ranges are half-open: **From** is included and **To** is excluded. The start must
be earlier than the end. **Beginning of history** and **Now** leave the
corresponding end open.
Earlier manual resets appear as time points and saved battles remain available.
The account and region determine which history and time points are shown.

Advanced sorting marks the existing card value in orange when that value is
already present. Additional credit or XP-total figures use a stable header slot.
Min/Max offers a compact link to the battle that produced the result, across
Maps, Vehicles and Tiers. For WN8, the large figure shows the selected Min/Average/Max while
that sort is active; otherwise the **Combined WN8** headline recalculates a rating
from all group results and expected vehicle values. It differs from the arithmetic
mean of individual-battle WN8 in the table. The card information button explains
this distinction. **All** sorts aggregate XP, credit income or credit costs by the sum of
known values. Credit income and net sorting separately offer Base (before bonuses)
and Received (settled income); historical missing Base values remain unknown.
Both net variants subtract actual battle costs. All is not offered for
WN8, win rate or individual battles. Credit sums mark the existing finance total;
XP sums show an explicit total in the header, with missing-value coverage.
A compact summary table shows total base XP, total received XP and Free XP in three
horizontal columns, with metric availability in the existing overview help.
The repeated visible x/y captions are removed. Performance tables and battle
cards always show both Base XP and Received XP; the display selector is removed.
Win-rate sorting is available in Vehicles, Maps and Tiers;
unknown outcomes stay last. More: [sorting](docs/SORTING_AND_TIERS.md),
[calendar](docs/CALENDAR_0.9.0.md), [0.9.1 UI refinements](docs/UI_POLISH_0.9.1.md),
[native scrollbar checks](docs/SCROLLBAR_NATIVE_SAFETY.md), and
[stable filtering and chronology](docs/FILTERING_0.9.2.md), and
[0.9.3 UI refinements](docs/UI_REFINEMENTS_0.9.3.md), and
[0.9.4 display corrections](docs/UI_REFINEMENTS_0.9.4.md), and
[0.9.5 layout refinements](docs/UI_REFINEMENTS_0.9.5.md), and
[0.9.6 readability and loading refinements](docs/UI_REFINEMENTS_0.9.6.md), and
[0.9.7 XP presentation and credit sorting](docs/UI_REFINEMENTS_0.9.7.md), and
[0.9.8 battle references and compact headers](docs/UI_REFINEMENTS_0.9.8.md), and
[0.9.9 permanent links and base/received credits](docs/UI_REFINEMENTS_0.9.9.md).

An expanded **Maps** card lists battles on that map within the selected period.
**Show battle** opens the chosen result in **Battles**. **Less** collapses an
expanded card. Hover over its small map picture to see larger local artwork;
`"maps": {"preview_mode": "minimap"}` selects the tactical map instead. The default
`"image"` uses native high-resolution landscape artwork when available and falls
back to the small picture. See [map preview sources](docs/MAP_PREVIEWS_0.8.0_SOURCE_EVIDENCE.md).

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

### Read-only Hangar integration

Version 0.5.0 exposes `gui.mods.grz_session_stats.runtime.read_hangar_stats(vehicle_ids)`
on the already loaded module. Consumers must not import or start Session Stats
when it is absent. API schema 1 returns only requested vehicle summaries from
the current account's full recorded Random Battle history, independent of UI
pages, reset periods and selected timeline bounds. WN8, battles and net credits
reuse the existing timeline group totals. Sparse daily counts cover the last
366 calendar days in the game computer's local time. Missing results are not
invented, and the first recorded battle is never treated as a purchase date.
The API returns no account identifier, local path or individual battle ledger.

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
The window has a minimum of 550 × 730 logical pixels when the game viewport can fit it.
A smaller viewport temporarily caps the displayed surface without discarding
saved restored-size preferences. A visible right-hand scrollbar shows position
and supports dragging, track clicks and keyboard navigation.

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
Mission cards use two columns when their available block fits two readable
cards; smaller blocks retain a single column.
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

Use the date dropdown between Previous and Next for chronology. Advanced sorting offers Statistic (Min/Avg/Max, plus All for additive aggregate metrics), Sort by (Off/Base XP/Received XP/Credits income net/Credits income gross/Credits costs/WN8), and Order (Ascending/Descending). With sorting off, chronology applies. Equal metric values use the selected chronology, with stable ID ties. Missing metric values sort last.

Sorting covers the complete selected period before pages of 40 rows are sent to the UI, and changes return to page one. Vehicles, Maps, Battles and Tiers have independent choices in each session scope, including Installation. Tiers includes XI and preserves an unknown-tier group for incomplete metadata. WN8 Min/Avg/Max uses individual battle WN8. Credits income gross uses recorded income, while credits income net includes costs and losses. Credits costs sorts nonnegative expense magnitudes, with the largest expense first when descending; the finance table still displays costs with a minus sign. All sums confirmed XP, credit income or credit costs for the group and selected period; it is unavailable for WN8, win rate and individual battles.

The selectors use local Gameface-compatible dropdowns with keyboard navigation.
Battles hides the aggregate Min/Avg/Max selector. When the complete control row
fits, a separate sorting toggle replaces the Off entry and groups the active
sorting controls; narrow layouts retain Off in the dropdown. A loading indicator
remains visible while a projection or result page is being rebuilt.
See [sorting and tier behavior](docs/SORTING_AND_TIERS.md).

Vehicle cards provide the same paginated battle history and Show battle links as
map cards. The selected battle keeps a visible orange frame across snapshot
refreshes in the same period. Active net-credit sorting displays the exact
per-battle Min/Average/Max value beside the vehicle metadata; the finance table
still reports period totals.

### Continuous result pages

Scrolling near either loaded edge fetches the adjacent 40-result page with a
dashed, localized page-number separator. Battles also shows the first result's
date and time beneath that boundary. Earlier pages are inserted above the
current cards while preserving their visible position. A spinner marks its
loading boundary; failed requests offer Retry. Previous/Next scroll to an already
loaded page or fetch the adjacent page. The native double-chevron button returns
to the full summary and page one of the selected result order, fetching it when
navigation initially opened a later page.
The grouping and sorting bar pins inside the scroll viewport. Filter changes
retain the current pixel offset, rebuilding the loaded window atomically for
a new ordering or index revision. New account histories start at the top.

Map/vehicle history pagers update a capped ten-row viewport in place, including
cards on an earlier loaded global page. Short single-page lists use their actual
height; multiple pages retain a stable body height. Battle navigation waits for
the exact card's geometry to settle, including results below a later page's
divider; scrolling input immediately cancels that automatic correction. Its
localized selected-battle badge is an absolute overlay that cannot resize cards
or move neighboring rows. Navigation pulses its
overlay for five seconds, then leaves it 30% transparent. The card's solid orange
border remains visible through native focus/blur events and any background
transparency setting. An explicit outside click or a changed view/period clears
the selection. Bonus source labels sit beside aligned resource values. Ordinary
matrices retain their compact width; additional resource columns or long amounts
can expand the matrix from 308 to 486 logical pixels. Remaining card width goes
to mission details.
