SESSION STATS — WORLD OF TANKS PC MOD
Version 0.3.1 • 2026-10-26 • target: Wargaming EU 2.4.1.0

RELEASE STATUS
This installable .wotmod contains CPython 2.7.18 bytecode, a dedicated Gameface
window, a battle-result adapter and persistent session storage. Since 0.2.7, it
supports grz.sessionstats.json for colors, corner radii, opacity
and scrolling speed. Configuration now lives in mods/configs, independently of the
active client-version folder. Bundled defaults preserve the panel, icon and wheel behavior.
Each field is validated on load; errors go to the mod's own log. Result health
checks, WoT warnings, the activity spinner and the integration safeguards from
0.2.5/0.2.6 remain available. Automated checks cover the logic, package and simulated
API failures. This release has not been run in a live WoT client here; mocked
interfaces cannot guarantee compatibility with future clients.
This is not an official Wargaming product.

UPDATING AN EXISTING INSTALLATION
Close the game, remove the previous grz.sessionstats_*.wotmod from the active
mods directory and replace it with grz.sessionstats_0.3.1.wotmod
from this package. Place grz.sessionstats.json in mods/configs. Keep only one active
version of grz.sessionstats. Bundled OpenWG 1.2.2 is unchanged; keep one copy.
The Windows journal-header defect is recovered only after the original checksum
verifies. Updating does not require a data reset. Back up the complete AppData
history first; see docs/WINDOWS_JOURNAL_RECOVERY.md for scope and limits.

The configuration filename has no release number. Preserve your own
grz.sessionstats.json instead of overwriting it with the new package's defaults.
Existing central files are never overwritten or filled with missing fields.
If the central main file is absent, the mod copies the legacy JSON beside the
active package, or creates the full defaults when no legacy file exists. Optional
legacy language overrides are also copied only if their central file is absent.
Legacy files stay intact. Copy your custom JSON into mods/configs before extracting
new package defaults, or install just the .wotmod to let this migration run.
The configs directory stays in place when the client's version folder changes.

QUICK INSTALLATION
1. Close World of Tanks.
2. Extract the ZIP anywhere.
3. Copy the included mods directory into the World of Tanks root containing
   WorldOfTanks.exe. For client 2.4.1.0, the installed files should include:
   mods/2.4.1.0/grz.sessionstats_0.3.1.wotmod
   mods/configs/grz.sessionstats.json
   mods/2.4.1.0/net.openwg/net.openwg.gameface_1.2.2.wotmod
   Preserve your existing configuration and language overrides when copying.
4. If another mod pack already provides OpenWG Gameface 1.2.2 or newer, retain
   one copy of that library. Install the grz.sessionstats package and any desired
   JSON overrides. Replace an older OpenWG file with the included newer version.
5. Start the game and enter the garage. Click the three-bar icon with a small
   WN8 label in the upper-right garage footer, or press Ctrl+F10. The shortcut
   toggles the window; Esc and the close button also close it. Drag the title
   bar with the left mouse button to move the window.

Nothing belongs in res_mods. The source directory, PODGLAD.html, README and
license files do not need to be in the game directory. Python is not required
on the player's computer.

If the active mods directory is not 2.4.1.0, use your client's version directory
for the .wotmod files. Both configuration JSON files stay in mods/configs. Moving files alone does not establish compatibility
with a new client. This adapter uses interfaces from the 2.4.1 branch.

LANGUAGES AND OPTIONAL FILES
The default "language": "auto" follows the game language; unsupported languages
fall back to English. English, Russian, French, Polish, German, Spanish and
Ukrainian catalogs are included inside the .wotmod. An explicit language code
in grz.sessionstats.json takes priority over the game, for example:
{"language": "pl"}
Existing "language": "en" remains an explicit English override. Change it to
"auto" or remove the property to follow the game after upgrading.
Use the panel Language dropdown to change the same setting without editing JSON.
It saves language to grz.sessionstats.json and applies the choice immediately.
Other settings and all battle history are preserved. Manual config edits continue
working after Refresh or reopening the panel. The translation catalog is inside
the .wotmod only; old external language files are ignored and never migrated.
Map and vehicle names supplied by the game retain the client's own localization.
See source/docs/LANGUAGES.md for supported choices and fallback behavior.

The main grz.sessionstats.json is also optional. It may contain only the fields
you want to change, including partial nested sections. Missing fields use defaults;
{} is valid. For example, {"language": "fr", "scroll": {"speed_multiplier": 1.5}}
changes the language and wheel speed while preserving all other defaults.

HOW THE PANEL WORKS
• The header shows completed battles, win rate and the full WN8 number.
• Two default period tabs: "Since launch" and "Since reset". Both belong to the
  active account. The optional installation tab has its own persistent manual
  reset and is hidden by default.
• "Base XP" is selected initially. "Received XP" switches all visible experience
  statistics to the values including bonuses awarded by the game.
• Summary and details are visible immediately. Vehicles / Maps / Battles appear
  below, with Vehicles selected on opening. Scroll the whole panel vertically;
  there are no accordions. Wheel down moves toward later results; wheel up moves
  back. At multiplier 1.0, a regular in-game wheel step moves one quarter of the
  visible list height, including small native input values. JSON changes speed
  without changing direction. Tables use larger text, soft edges and subtle rows.
• Vehicle and map names have thumbnails from local game resources. No additional
  image pack is required. Missing images leave the correct name and statistics
  visible without substituting unrelated artwork.
• Each period, vehicle and map shows minimum/average/maximum XP and individual
  battle WN8.
• Battles show one XP value, one WN8 value and victory, defeat or draw. A single
  result is not repeated across three columns; individual battles have no win rate.
• Every grouping includes free XP and credit/bond income, costs and net amounts.
  Gold appears when the result confirms a battle-related transaction.
• Headline WN8 uses summed results and the expected values of each vehicle.
  Average individual-battle WN8 is a separate detail metric.
• WN8 is written as 1574, not 1.6k. Values such as 805 and 10420 remain unabbreviated.
• Unknown values use a dash. Partial data shows coverage, for example 15/16.
  Partial financial totals contain only confirmed amounts.
• On battle entry, available time, map, vehicle name, tier and class are saved.
  The entry survives restarts even without a result: known names remain visible,
  while missing statistics use dashes. Later metadata fills the same entry.
  Older entries may lack names that earlier versions did not save.
• This release counts standard random battles. Replays and special modes are
  excluded from WN8 for this scope.

APPEARANCE AND SCROLLING — grz.sessionstats.json
The file sits in the installation-wide configs directory:
mods/configs/grz.sessionstats.json
The full supplied file contains 140 color settings, 12 corner radii, 3 opacity
settings and a scrolling multiplier. Defaults preserve layout, spacing, tables,
icons, the spinner and wheel speed.

Configuration sections:
• language: "auto" by default (game language, English fallback), or an explicit code.
• sessions.instance_tab: true displays the durable installation tab;
  false (default) keeps it hidden. Only JSON booleans are accepted.
  Visibility does not interrupt collection.
• colors: text, backgrounds, lines, shadows, gradients and control states.
  Accepted formats: #RGB, #RRGGBB, #RRGGBBAA, rgb(...), rgba(...) and transparent.
  RGB channels range from 0 to 255; rgba alpha ranges from 0 to 1.
• radii: unitless values from 0 to 24. They follow the game's UI scale; one unit
  equals one pixel at the base scale.
• opacity: window, garage_button and disabled_controls, each from 0 to 1.
  1 means fully visible. opacity.window also affects text and controls. To change
  only the window background, use rgba in colors.window_background.
• scroll.speed_multiplier: number from 0.1 to 8, default 1.0. Values 1.5, 2.0
  and 0.5 increase the wheel step by half, double it and halve it respectively.
  This affects in-game scrolling; HTML previews use the browser's native wheel.

Edit the complete file or retain only changed fields. Example overrides, with
all other fields taking their defaults:
{
  "schema_version": 1,
  "colors": {
    "window_background": "rgba(17,19,9,0.9)",
    "table_row_following_border_top": "#465336"
  },
  "radii": {
    "window": 6,
    "group_card": 7
  },
  "opacity": {
    "window": 1.0
  },
  "scroll": {
    "speed_multiplier": 1.5
  }
}
Save as UTF-8; a BOM is supported. JSON requires double quotes and decimal points.
Do not add comments or a trailing comma. Full field descriptions and examples:
source/docs/APPEARANCE_CONFIG.md.

Configuration is read at mod startup, when opening the panel and after clicking
"Refresh". Save the JSON, then refresh or reopen the panel. The mod does not
inspect the file every frame or on every timer tick.

If configuration cannot be created or read, the mod uses defaults. Invalid JSON
syntax/encoding, duplicate keys,
NaN/Infinity, files larger than 128 KiB, an invalid root type or an unsupported
schema_version also restore all defaults. An invalid field restores only its own
default; other valid changes remain active. An incorrectly typed section restores
that section's defaults. Unknown fields are ignored and logged. Omitted fields
and {} are valid. Boolean values cannot substitute for numeric settings.

Read/validation errors use the CONFIG prefix in session-stats.log. Syntax errors
include line and column when available; invalid fields include their names and
reasons. Raw JSON and user values are not logged. An ambiguous package location
produces CONFIG_PATH diagnostics and defaults. The mod does not choose the highest
mods version or JSON beside an old copy from another client version. Renaming
the .wotmod or keeping several active copies can prevent file discovery; retain
the supplied filename and one copy. If the configuration module itself is
unavailable, the bundled static styles and default wheel behavior remain usable.

TWO INDEPENDENT ACCOUNT PERIODS
Both periods and the manual reset are separate for every account and region.
Switching accounts displays that account's history; returning restores the earlier
account's scope. Resetting account B does not reset account A. Their histories
are not combined.
"Since launch" starts a new period in a new game process. Returning from battle
to the garage or reconnecting within the same process does not reset it.
"Since reset" persists across game launches until manually reset. Its "Reset period"
button asks for confirmation. It does not reset "Since launch"; midnight does
not reset either period.

OPTIONAL INSTALLATION SESSION
To display the third tab, add this section to grz.sessionstats.json:
{"sessions": {"instance_tab": true}}
Keep other existing sections. Refresh or reopen the panel after saving.
The tab is hidden by default; the existing account scopes remain separate.

Installation history combines accounts observed in this installation and
survives game restarts, along with its own manual reset boundary. Only its
explicit reset starts a new period. Neither reset changes the other histories.
Late results retain their original installation period after restarting.
The shared ledger uses atomic, checksummed local storage and a hashed game-root
identity independent of the client version directory. Separate installations
remain separate. Hiding the tab neither clears nor stops the saved period.
The footer spinner still follows only the active account.
No account-history migration or reset is required. Older account archives
without installation provenance are not automatically imported.
Details: source/docs/ACCOUNT_SESSIONS.md.

A battle's period membership is saved on entry. A late result fills the correct
period. A repeated result updates the existing record instead of adding another
battle. A later XP bonus does not increment the battle count. Missing results
are retried through the client's available result cache. The client may no longer
provide an old result after a restart; the mod does not invent a defeat. It does
not import Tomonik history or battles played before installation.

When a local result is missing, recovery also uses WoT's native server request.
The game may be closed when the battle ends: its saved entry remains queued and
is reconciled after the next login if the server supplies the result. The mod
also captures valid results read by the client's own interface before the client
acknowledges receipt. Shared-cache failures and accounts that are not ready have
separate retries; old gaps do not block new battles.

An incomplete period shows, for example, "Battles with results: 20 / 21". The
missing battle remains in the list with an unknown outcome. WN8, XP and financial
coverage use all recorded battles as the denominator. Percentages, averages and
sums describe received data. A recovered result fills the original battle and
period without duplication. If the server no longer supplies it, recovery cannot
be promised; the gap stays explicit. See source/docs/OFFLINE_RESULT_RECOVERY.md.

Resetting starts a new visible period and preserves the old journal on disk.
A battle started before the reset does not enter the new manual period.

SPINNER AND PENDING RESULTS
A small spinner appears above the garage icon's bars while waiting for a result
from a battle observed during the current launch, or while processing a result
or XP bonus. It concerns only the active account. The button still opens the
panel and retains the small WN8 label. Its tooltip distinguishes waiting from
processing and reports the pending count.

Being in a current battle is not itself a pending result. If you return to the
garage before it ends, the observed battle remains pending until WoT supplies
the result. Partial results can remain pending for completion. The spinner stops
when the queue is empty and processing is complete, without an artificial timeout.
Brief processing can be barely noticeable.

Activity follows the account's queue regardless of the selected period tab.
Manual reset does not discard pending settlements. Account changes switch queues;
a late callback from the old account cannot activate the new account's spinner.
After restarting without entering a new or ongoing battle, an old incomplete
entry does not keep the spinner active. The panel retains the missing count and
explanation while background recovery continues. "Refresh" retries reads. History
is neither deleted nor marked complete merely to stop the spinner. Processing a
recovered result can briefly display real activity. Stopping the mod invalidates
old callbacks and removes the indicator with its button.

RESULT FORMAT HEALTH CHECK
The health check compares received results against a verified client contract:
field names, types, container shapes, required data, relevant numeric ranges and
the known credit/bond/gold expense layout. It also checks selected identifier
relationships and directive settlements. New field names are compared against a
fixed catalog; the first result after an update does not become a new baseline.

Incompatibilities produce a WoT system warning identifying problematic fields
and the log location. Messages are delivered in the garage without interrupting
battle. Each combination of code, path, expected and actual type/shape is logged
and reported once per mod launch. New problems are grouped; result-warning
attempts are at least 60 seconds apart. If notifications are temporarily unavailable,
the message waits for another attempt. The panel retains the detected issue
for the current launch.

A warning does not mean every statistic is wrong. Known valid data can still be
stored despite an unused new field or partial settlement. Unknown expense-tuple
layouts are not guessed using old indexes. With a known layout, one missing
amount does not discard other confirmed currencies. Normal waiting and a
"not ready yet" response do not trigger a format warning; changed damage or XP
values alone do not trigger one either.

The check has limits: changed meanings with unchanged names, types and valid
ranges cannot be detected from the result alone. Unused extension internals are
not fully validated; missing unused optional fields are not an alarm. Major
client changes still require comparison with a native battle report. Details:
source/docs/RESULT_HEALTH_CONTRACT.md.

MOD LOG
Standard Windows location:
%APPDATA%/grz_wot_session_stats/logs/session-stats.log

The UTF-8 log records UTC timestamps, severity, mod version and diagnostics such
as pending-count changes or health-check codes/paths/types. CONFIG entries describe
configuration reads and validation; CONFIG_PATH describes discovery of mods/configs
in the active installation. CONFIG_SETUP records creation/migration or a failure. Health diagnostics contain schema metadata without
raw results, nicknames, account identifiers or statistic values. Exception logging
keeps exception types and code locations, omitting messages that could contain
result data.

Rotation: approximately 1 MiB per file, plus session-stats.log.1, .2 and .3,
approximately 4 MiB for that log family. Concurrent clients use a short nonblocking
file lock; contention does not stall the game. Without a supported locking module,
the mod uses session-stats-<PID>.log, where PID is the game process ID, with the
same rotation limit per PID family. It does not remove other processes' logs.
Result warnings show the actual log path.

Failure to write the dedicated log does not disable statistics. The panel and
WoT notifications report the problem; existing game.log diagnostics remain.
Logs are local and are not automatically uploaded.

FINANCES AND XP
Base XP comes from originalXP; received XP comes from the game result. Additional
post-battle bonuses are reconciled with the native result controller and saved.
Base XP is not reconstructed by dividing final XP by a multiplier.

Credits include awarded amounts with applicable deductions, repair costs and
automatic ammunition, consumable and directive resupply. Directive costs are not
subtracted twice when already included in automatic resupply. Bonds include
battle-reported income and expenses, including bond-funded directives. Gold is
a separate currency.

Balances describe settled battles in the selected period. Vehicle purchases,
equipment sales and unrelated garage transactions are not assigned to the last
map. Deferred credit reserves are not treated as immediate payouts. Rewards count
when included in that battle's result. Missing amounts remain unknown; they are
not replaced by zero or catalog equipment prices.

DATA, SHORTCUT AND BUTTON
Standard Windows data location:
%APPDATA%/grz_wot_session_stats/

Paste this path into Explorer. Each account/region has a subdirectory derived
from its identifier, not its nickname. Data is outside mods/2.4.1.0, so moving
the mod to a new client version does not erase the manual period. Saves append
checksummed changes to mirrored journals and retain three atomic commit descriptors.
Back up the entire account/installation directory while the game is closed,
including journal/, its .bak files and startup-intake/; state-*.json alone is not
a complete backup.
Unknown newer formats block writes instead of damaging files. Older releases
cannot write the new journal format. History lists use pages of 40 rows; totals
still cover the whole period. History loads in scheduled steps in the garage;
history work pauses during battles. New results are saved to a temporary durable
queue until the history and indexes are ready. The panel shows a loading notice
and disables reset/pagination during this time; it does not show partial totals.
Allow loading to finish before downgrading: an older mod ignores the pending
startup queue. Keep the entire data directory if loading reports an error.
See docs/HISTORY_PERFORMANCE.md for measurements and remaining limits. Scheduled
steps improve responsiveness but do not guarantee frame times or faster completion.

Existing shortcut and garage-button settings remain separate from appearance.
Optionally create %APPDATA%/grz_wot_session_stats/config.json:
{
  "hotkey": "CTRL+F10",
  "footer_button": true
}
F1–F12 support CTRL, SHIFT or ALT combinations, for example CTRL+SHIFT+F10.
Shortcut/footer_button changes take effect after restarting the game. An invalid
shortcut restores Ctrl+F10. Edit appearance, language and scrolling in
mods/configs/grz.sessionstats.json.

WN8 AND GAME UPDATES
The bundled offline XVM Wargaming table is dated 2026-10-19 and covers 999 vehicles.
Missing expected values for a new vehicle do not disable XP, counts or finances;
WN8 displays missing or partial coverage.

To update only WN8 data, download:
https://static.modxvm.com/wn8-data-exp/json/wg/wn8exp.json
and save it as %APPDATA%/grz_wot_session_stats/wn8exp.json, then restart the game.
Do not use the lesta directory's file. Invalid local data falls back to the bundled
table. Updating the table may change WN8 for earlier results; counts, XP and
currency settlements still use stored results.

Window resources are registered through gui/gen_resources and R.mods.grz… names,
without fixed resource IDs or replacing core result-panel files. The garage
button uses a dedicated footer component and OpenWG Gameface. If a client update
changes the footer, the independent keyboard shortcut remains available provided
the keyboard and window interfaces still work.
Client changes usually concern runtime.py, normalize.py, views.py, footer.py and
the small visuals.py adapter. Calculations and storage are separate. Confirmed
schema changes also require updating health.py's contract; a warning does not
modify the adapter automatically. Package discovery is isolated in config_path.py;
appearance.py validation does not depend on the client. Discovery sources and
safe loading rules: source/docs/CONFIG_PATH_SOURCES.md. No mod using internal
client interfaces can guarantee operation after arbitrary future updates; this
architecture limits the scope of fixes.

SAFEGUARDS RETAINED FROM 0.2.5
• Missing window imports, keyboard handling or an optional subscription do not
  by themselves block receipt and storage from other available result sources.
• Mod callbacks are guarded so failures do not interrupt the native dispatcher.
  Closing/stopping detaches components independently. Retained old callbacks
  are invalidated and cannot control a new window or runtime.
• Missing vehicle-thumbnail helpers do not disable map thumbnails. Missing
  graphics do not block text statistics.
• Re-reading saved results retains known vehicle names and map identity when
  the current client cannot resolve them, preserving historical grouping.
• The panel warns about unavailable result or additional-XP sources. Repeated
  failures do not flood logs. Missing data remains missing; changed financial
  meanings and bonus values are not guessed.

These safeguards address specific failures rather than automatically adapting
to every new WoT client. Changed result formats, Wulf/Gameface bridges or Python
versions may require adapter updates or recompilation. A changed active mods
directory also requires installing the package for the correct client version.
Audit details and pinned sources: source/docs/UPDATE_COMPATIBILITY_SOURCES.md.

FIRST IN-GAME CHECK
1. In the garage, check the small icon, window position, visible tab labels,
   title-bar dragging, upper-right close button, XP mode, Vehicles/Maps/Battles,
   Ctrl+F10 and Esc. Change a color or wheel multiplier in JSON, save and click
   "Refresh". This interface check does not require playing a battle.
2. Verify result receipt separately: after a new completed random battle, compare
   base/received XP and credit/bond net values with that battle's native report.
   After returning early, check the spinner and tooltip; after full settlement,
   it should stop unless another result is pending.
3. Restart the game: "Since launch" has zero battles; "Since reset" retains the
   result. Manual reset clears only the second period. An incomplete old result
   alone should not start the spinner; the panel explains the missing data.
If the panel fails to open, a result is missing or a warning appears, retain the
indicated log and rotated copies plus game.log from that launch (and python.log
if the client creates it). If the dedicated log fails, search game.log for
grz.sessionstats. A statistics discrepancy also requires the native result's
detail screen. Without these, the cause cannot be confirmed.

COMMON TEST
A separate test client does not guarantee separate local account history. The
journal is keyed by account and region. If Common Test returns the same pair and
both clients use the same AppData, they can share the local "Since reset" scope.
A separate Windows user provides separate AppData; changing only the game install
directory does not. This does not affect main-account progress on Wargaming's server.

UNINSTALLING
Close the game and remove grz.sessionstats_0.3.1.wotmod from the active mods directory.
Other mods may require OpenWG. The AppData journal remains; deleting the data
directory deletes saved statistics. Keep grz.sessionstats.json and optional
language overrides for a later installation if desired.

SOURCE AND BUILD
source/src/ — mod code; source/ui/ — native panel and button.
source/tests/ — calculation, storage, adapter and UI tests.
source/tools/build.py — builds ZIP_STORED .wotmod and installation packages.
source/tools/make_preview.py — real UI preview using synthetic data.
source/preview/PODGLAD.html and PODGLAD.html — previews without game data input.

Building requires Python 3 and CPython 2.7 developer tools:
python3 tools/build.py --python27 /path/to/python2.7 --client-version 2.4.1.0
Run Python tests from source:
python2.7 -m unittest discover -s tests -p "test_*.py" -v
python3 -m unittest discover -s tests -p "test_*.py" -v
UI tests require Node and Playwright; set GRZ_CHROME to the Chrome executable.
node tests/ui_contract.cjs — controls, layout and individual battle results.
node tests/ui-wheel.cjs — wheel direction/speed, no duplicate movement and bounds.
node tests/ui-footer.cjs — garage-button appearance, controls and integration.
node tests/ui-footer-compat.cjs — footer API failures and inert old callbacks.
node tests/ui-footer-activity.cjs — spinner, queue state, tooltip and cleanup.
node tests/ui-appearance.cjs — configured styles, fallback and wheel multiplier.
Python tests also cover JSON validation, default/style agreement, package-path
discovery and configuration delivery to the panel and footer.
Source validation after PR #3 corrections: 364 tests on Python 3; the same suite
on CPython 2.7.18 with 4 Python-3-only builder tests skipped.
Tests cover spinner behavior after restart and old-result recovery. Default panel
and icon styles/geometry are compared against the baseline; raster checks allow
bounded antialiasing differences between Chromium versions. Automated validation
is not a live WoT test. The game package contains Python 2.7 bytecode; do not
replace it with Python 3 bytecode. BUILD.json, SHA256SUMS.txt and test reports
describe the actual verification.

Code license: GPL-3.0. OpenWG retains MIT. Details and original sources:
LICENSE.txt, THIRD_PARTY.txt, source/third_party/openwg/LICENSE.
