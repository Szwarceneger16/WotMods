# Session Stats local end-to-end tests

Chromium loads the mod's HTML, CSS, and JavaScript. The Python backend computes statistics, filters date ranges, and responds to panel commands. The test harness simulates WoT data and window services. You can run the tests without launching the game or signing in.

## Windows x64 setup

1. Install Node.js 22 or later. The Node.js 24 LTS x64 installer is one option. [Download Node.js](https://nodejs.org/en/download)
2. Install Python 3 x64 and add it to `PATH`. The test harness was verified with Python 3.12.14. [Download Python for Windows](https://www.python.org/downloads/windows/)
3. Open PowerShell in the directory containing this file and run the following commands. The `tzdata` package supplies the `Europe/Warsaw` time zone on Windows.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:SESSIONSTATS_PYTHON = (Resolve-Path .\.venv\Scripts\python.exe).Path
npm.cmd install
```

The PowerShell script detects Edge in its standard installation directory. You can also install Playwright's Chromium build or pass a browser executable to `run.cjs` with `--chrome`. [Install Playwright browsers](https://playwright.dev/docs/browsers)

```powershell
npx.cmd playwright install chromium
```

## Local WoT assets and anonymous profile

Installing `requirements-local-assets.txt` adds Pillow for map image conversion. The local runner opens WoT packages in read-only mode and uses them to load both Warhelios fonts and stock images for synthetic maps and vehicles. It stores the fonts and images in a temporary renderer directory and removes them when the run finishes.

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-local-assets.txt
```

The optional exporter reads verified local history and writes broad statistical ranges after dropping rare values. The backend samples those ranges to generate fictitious battles. Keep the profile outside the repository. The generated dates, identifiers, names, and amounts are fictitious. The runner selects artwork by the test vehicle or map number.

```powershell
$profilePath = Join-Path $env:LOCALAPPDATA 'SessionStatsQA/local-profile.json'
New-Item -ItemType Directory -Path (Split-Path -Parent $profilePath) -Force
.\.venv\Scripts\python.exe -B anonymize_history.py --output $profilePath
.\run-local.ps1 -Suite smoke -Profile $profilePath
.\run-local.ps1 -Suite full -Profile $profilePath
```

Use `-GameClient` to select a different WoT installation. Reports that use a local profile or assets default to `%LOCALAPPDATA%/SessionStatsQA/runs/`. The runner blocks writing these reports inside a Git checkout.

## Running the suites on demand

Inspect the case count and coverage without launching the renderer.

```powershell
node run.cjs --suite full --plan
```

Chromium is the default engine. `build` checks eight cases and basic interactions. `smoke` covers multiple widths and both main date ranges.

```powershell
node run.cjs --engine chromium --suite smoke
node run.cjs --engine chromium --suite full --chrome 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'
```

PowerShell's `-Suite full` covers every sorting option across all configured date ranges, equivalent to `--suite full --all-ranges` when running Node directly. `--suite full` alone covers chronological sorting for less common date ranges. The standard view heights are 730 and 900 px, with up to three scroll steps. Separate scenarios cover the menu, calendar, expanded details, and returning from a selected battle.

The full matrix takes substantial time and disk space. `-FinalOnly` still checks each scroll position and records each case result. It saves a final JPEG or a failure screenshot.

```powershell
.\run-local.ps1 -Suite full -Plan -Profile $profilePath
node run.cjs --engine chromium --suite full --widths 365,780 --heights 730,900 --ranges history,since-sunday --languages en,pl --limit 40
node run.cjs --engine chromium --suite smoke --source '../WotMods-pr17-next/mods/sessionstats' --python 'C:/Python312/python.exe'
```

Use `--source` to point to `mods/sessionstats` in the selected checkout. The runner detects it automatically from within the repository and also looks for a neighboring `WotMods-pr17-next` checkout when run from a separate directory. `--python` overrides `SESSIONSTATS_PYTHON` or the default `python` command. If you use `.venv`, set `$env:SESSIONSTATS_PYTHON` again in each new PowerShell session. Run `node run.cjs --help` for all options.

## GitHub Actions

The regular build runs the short Chromium suite on a native Windows runner. It installs the pinned Playwright browser and Python time zone data in a temporary directory. To start **Session Stats Chromium matrix**, post a new command comment on an open pull request from a branch in this repository. `/sessionstats-matrix` runs every sorting option in every configured date range. `/sessionstats-matrix smoke` checks reporting with a small sample. `/sessionstats-matrix full` checks every sorting option in the primary date ranges. The on-demand matrix uses the pinned Linux browser container and appears in Actions as **Session Stats matrix · PR #…**.

Every CI run uses synthetic data and test artwork. The merge job publishes `index.html`, `catalog.js`, and the corresponding screenshots, including any available results from incomplete runs. Extract the artifact and open `index.html` to see the tested commit, case results, and CI job outcomes supplied by the workflow. A failed detailed Chromium check fails the run even when all rendering cases pass. The full CI matrix saves the final phase of each case. Local runs save all four phases by default.

## Reports and visual comparisons

The command prints the path to the new output directory. Open `index.html` to review cases and screenshots. `run.json` contains the version and summary. `results.ndjson` contains results and measurements for each case. Use `-OutputDirectory` or `--out` to select a different directory.

After reviewing a run, you can use it as a baseline. Run the next comparison with the same renderer, version, data and artwork sources, dimensions, and date range. The default `--threshold 0.002` allows up to 0.2% of pixels to differ. Comparisons exclude the inside of the current-time field in the header. When a difference exceeds the threshold, the report saves the screenshot, baseline, and difference image.

```powershell
node run.cjs --engine chromium --suite smoke --out 'runs/baseline'
node run.cjs --engine chromium --suite smoke --baseline 'runs/baseline' --out 'runs/comparison'
```

Gameface Player tests verify panel rendering and command handling in a simulated window. Exact timing and window dragging behavior inside WoT also depend on the game's integration.

## Building the mod package

The builder requires **CPython 2.7.18** to compile the mod. From this directory, generate the browser preview and build the source bundle with the path to that interpreter. The builder writes its output and checksums to the mod's `dist/` directory. The last command produces the same `Session-Stats-v*.zip` installer layout as GitHub Actions. [Download CPython 2.7.18](https://www.python.org/downloads/release/python-2718/)

```powershell
$sessionStatsModule = '../../../mods/sessionstats'
python "$sessionStatsModule/tools/make_preview.py"
python "$sessionStatsModule/tools/build.py" --python27 'C:/Python27/python.exe' --client-version 2.4.1.1
python ../../../scripts/release_installers.py package runs/installer --source "$sessionStatsModule/dist" --mod sessionstats
```
