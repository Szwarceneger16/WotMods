#!/usr/bin/env bash
set -euo pipefail
test -n "${PYTHON27:?Set PYTHON27 to CPython 2.7.18}"
python3 -m unittest discover -s mods/sessionstats/tests -v
"$PYTHON27" -B -m unittest discover -s mods/sessionstats/tests -v
client_args=()
if [[ -n "${WOT_CLIENT_VERSION:-}" ]]; then client_args+=(--client-version "$WOT_CLIENT_VERSION"); fi
python3 mods/sessionstats/tools/make_preview.py
python3 -I scripts/sessionstats/browser_qa.py
python3 mods/sessionstats/tools/build.py --python27 "$PYTHON27" "${client_args[@]}"
manifest="$(mktemp "${RUNNER_TEMP:-${TMPDIR:-/tmp}}/sessionstats-reproducibility.XXXXXX")"
python3 scripts/sessionstats/artifacts.py snapshot "$manifest"
python3 mods/sessionstats/tools/build.py --python27 "$PYTHON27" "${client_args[@]}"
python3 scripts/sessionstats/artifacts.py verify "$manifest"
python3 scripts/sessionstats/integration.py
python3 scripts/sessionstats/privacy.py --python27 "$PYTHON27" --scan-dist
