#!/usr/bin/env bash
# Read-only CI path for either reticle mod. Every archive is built from source.
set -euo pipefail
[[ $# == 2 && ( "$1" == aimtimer || "$1" == rangefinder ) ]] || exit 2
module="$1"
version="$2"
: "${PYTHON27:?The pinned CPython 2.7 build is required}"
export GRZ_RETICLE_MOD="$module"

dist="mods/$module/dist"
scratch="$(mktemp -d)"
trap 'rm -rf -- "$scratch"' EXIT
archive="com.grz.${module}_${version}.wotmod"
python3 scripts/privacy_audit.py
"$PYTHON27" -B "mods/$module/tools/build_wotmod.py" --version "$version"
"$PYTHON27" -B "mods/$module/tools/build_wotmod.py" --version "$version" --output "$scratch"
cmp "$dist/$archive" "$scratch/$archive"
cmp "$dist/SHA256SUMS.txt" "$scratch/SHA256SUMS.txt"
python3 scripts/reticles/verify_assets.py "$module" "$version" "$dist/$archive"
"$PYTHON27" -B -m unittest discover -s scripts/reticles/tests -v
node scripts/reticles/tests/test_preview_ui.mjs "$module" "$version" "$dist"
