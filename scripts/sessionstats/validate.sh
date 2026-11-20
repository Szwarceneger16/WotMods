#!/usr/bin/env bash
set -euo pipefail

# PR steps and the complete release transaction share the same commands.
# GitHub Actions owns concurrency; this entry point does not schedule processes.
run_phase() {
  case "$1" in
    python3)
      python3 -m unittest discover -s mods/sessionstats/tests -v
      ;;
    python27)
      test -n "${PYTHON27:?Set PYTHON27 to CPython 2.7.18}"
      "$PYTHON27" -B -m unittest discover -s mods/sessionstats/tests -v
      ;;
    preview)
      python3 mods/sessionstats/tools/make_preview.py
      ;;
    browser)
      python3 -I scripts/sessionstats/browser_qa.py --e2e build
      ;;
    build)
      test -n "${PYTHON27:?Set PYTHON27 to CPython 2.7.18}"
      (
        client_args=()
        if [[ -n "${WOT_CLIENT_VERSION:-}" ]]; then client_args+=(--client-version "$WOT_CLIENT_VERSION"); fi
        manifest="$(mktemp "${RUNNER_TEMP:-${TMPDIR:-/tmp}}/sessionstats-reproducibility.XXXXXX")"
        trap 'rm -f -- "$manifest"' EXIT
        python3 mods/sessionstats/tools/build.py --python27 "$PYTHON27" "${client_args[@]}"
        python3 scripts/sessionstats/artifacts.py snapshot "$manifest"
        python3 mods/sessionstats/tools/build.py --python27 "$PYTHON27" "${client_args[@]}"
        python3 scripts/sessionstats/artifacts.py verify "$manifest"
      )
      ;;
    integration)
      test -n "${PYTHON27:?Set PYTHON27 to CPython 2.7.18}"
      python3 scripts/sessionstats/integration.py
      ;;
    privacy)
      test -n "${PYTHON27:?Set PYTHON27 to CPython 2.7.18}"
      python3 scripts/sessionstats/privacy.py --python27 "$PYTHON27" --scan-dist
      ;;
    *)
      echo "Unknown validation phase: $1" >&2
      return 2
      ;;
  esac
}

if [[ $# -gt 1 ]]; then
  echo 'Usage: validate.sh [all|python3|python27|preview|browser|build|integration|privacy]' >&2
  exit 2
fi
phase="${1:-all}"
case "$phase" in
  all)
    test -n "${PYTHON27:?Set PYTHON27 to CPython 2.7.18}"
    for validation_phase in python3 python27 preview browser build integration privacy; do
      run_phase "$validation_phase"
    done
    ;;
  python3|python27|preview|browser|build|integration|privacy)
    run_phase "$phase"
    ;;
  *)
    echo 'Usage: validate.sh [all|python3|python27|preview|browser|build|integration|privacy]' >&2
    exit 2
    ;;
esac
