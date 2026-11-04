#!/usr/bin/env bash
set -euo pipefail
test -n "${PYTHON27:?Set PYTHON27 to CPython 2.7.18}"
python3 -m unittest discover -s mods/sessionstats/tests -v
"$PYTHON27" -B -m unittest discover -s mods/sessionstats/tests -v
client_args=()
if [[ -n "${WOT_CLIENT_VERSION:-}" ]]; then client_args+=(--client-version "$WOT_CLIENT_VERSION"); fi
python3 mods/sessionstats/tools/make_preview.py
ui_tools="${RUNNER_TEMP:-${TMPDIR:-/tmp}}/sessionstats-ui"
npm install --prefix "$ui_tools" --no-audit --no-fund --save-exact playwright@1.62.1
export NODE_PATH="$ui_tools/node_modules"
node "$ui_tools/node_modules/playwright/cli.js" install --with-deps chromium
# Use Playwright's matching browser unless the caller provides an executable.
export GRZ_CHROME="${GRZ_CHROME:-$(node -e 'process.stdout.write(require("playwright").chromium.executablePath())')}"
for test_file in ui_contract ui-wheel ui-footer ui-footer-activity ui-footer-compat ui-appearance; do
  node "mods/sessionstats/tests/$test_file.cjs"
done
python3 mods/sessionstats/tools/build.py --python27 "$PYTHON27" "${client_args[@]}"
manifest="$(mktemp "${RUNNER_TEMP:-${TMPDIR:-/tmp}}/sessionstats-reproducibility.XXXXXX")"
python3 scripts/sessionstats/artifacts.py snapshot "$manifest"
python3 mods/sessionstats/tools/build.py --python27 "$PYTHON27" "${client_args[@]}"
python3 scripts/sessionstats/artifacts.py verify "$manifest"
python3 scripts/sessionstats/integration.py
python3 scripts/sessionstats/privacy.py --python27 "$PYTHON27" --scan-dist
