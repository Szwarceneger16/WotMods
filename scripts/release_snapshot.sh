#!/usr/bin/env bash
# Assemble a complete immutable Release snapshot, replacing only the rebuilt mod.
# Usage: release_snapshot.sh DIST PRIMARY_FILE PRIMARY_GLOB [OTHER_OWNED_GLOBS...]
#  - PRIMARY_FILE is exactly one newly built versioned .wotmod or installer ZIP.
#  - PRIMARY_GLOB matches this mod's older/newer versioned primary artifact.
#  - Remaining globs are assets owned by this mod (installer/config/etc).
#  - Exit 75 means an already-published primary version is >= this build:
#    skip this stale publication; do not create/move a tag or change Latest.
# The caller MUST hold the SAME job-level GitHub Actions concurrency group with
# queue:max across every mod publisher, from this snapshot through publication.
set -euo pipefail

fail() { printf 'Release snapshot blocked: %s\n' "$*" >&2; exit 1; }
[[ $# -ge 3 ]] || fail 'Expected DIST, PRIMARY_FILE and at least one owned-asset glob'
dest="$(realpath -- "$1")"; primary="$2"; primary_glob="$3"; shift 3
[[ -d "$dest" && -f "$dest/SHA256SUMS.txt" ]] || fail 'Missing locally verified build/manifest'
: "${GITHUB_REPOSITORY:?GITHUB_REPOSITORY is required}"
[[ "$primary" =~ ^[A-Za-z0-9][A-Za-z0-9._-]*\.(wotmod|zip)$ && -f "$dest/$primary" ]] || fail 'Missing or unsafe primary .wotmod/ZIP'
[[ "$primary_glob" =~ ^[A-Za-z0-9._-]+\*[A-Za-z0-9._-]+$ ]] || fail 'Primary glob must contain exactly one asterisk'
[[ "$primary" == $primary_glob ]] || fail 'Primary asset does not match its versioned glob'
# The primary glob must contain a single *, and all versions use strict SemVer.
prefix="${primary_glob%%\**}"
suffix="${primary_glob#*\*}"
semver='^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$'
version_of() {
  local name="$1" stem
  [[ "$name" == $primary_glob ]] || fail "Unknown primary asset name: $name"
  stem="${name#"$prefix"}"
  stem="${stem%"$suffix"}"
  [[ "$stem" =~ $semver ]] || fail "Invalid semantic version in primary asset: $name"
  printf '%s' "$stem"
}
new_version="$(version_of "$primary")"
(cd "$dest" && sha256sum --check --strict SHA256SUMS.txt) || fail 'Local build checksum failed'

# Read repository-wide Latest as late as possible, AFTER the publication lock.
# Never use an earlier build's snapshot or a cached GH Actions artifact.
releases="$(gh release list --repo "$GITHUB_REPOSITORY" --limit 200 \
  --json tagName,isDraft,isPrerelease,isLatest,isImmutable)" || fail 'Cannot list published Releases'
published_count="$(jq -r '[.[] | select(.isDraft == false and .isPrerelease == false)] | length' <<< "$releases")"
latest="$(jq -r '[.[] | select(.isLatest == true and .isDraft == false and .isPrerelease == false)] |
  if length == 0 then "" elif length == 1 then .[0].tagName else "DUPLICATE" end' <<< "$releases")"
[[ "$latest" != DUPLICATE ]] || fail 'More than one Latest release'
if [[ -z "$latest" ]]; then
  [[ "$published_count" == 0 ]] || fail 'Published Releases exist, but none is marked Latest'
else
  immutable="$(jq -r --arg tag "$latest" '.[] | select(.tagName == $tag) | .isImmutable' <<< "$releases")"
  [[ "$immutable" == true ]] || fail "Latest Release $latest is not immutable"
  staging="$(mktemp -d)"
  trap 'rm -rf -- "$staging"' EXIT
  gh release download "$latest" --repo "$GITHUB_REPOSITORY" --dir "$staging" || fail 'Cannot download previous Release'
  # Installer releases have internal per-ZIP manifests. Validate these before
  # generating the temporary outer manifest required by the shared snapshot.
  # Legacy loose assets are checksum-verified and converted exactly once.
  if [[ "$primary" == *.zip ]]; then
    client_args=()
    if [[ -n "${WOT_CLIENT_VERSION:-}" ]]; then client_args+=(--client-version "$WOT_CLIENT_VERSION"); fi
    python3 "$(dirname -- "$0")/release_installers.py" normalize "$staging" "${client_args[@]}"
  fi
  [[ -f "$staging/SHA256SUMS.txt" ]] || fail 'Previous Release lacks checksum manifest'
  expected="$(sed -nE 's/^[0-9a-f]{64}  ([A-Za-z0-9][A-Za-z0-9._-]*)$/\1/p' "$staging/SHA256SUMS.txt" | LC_ALL=C sort)"
  actual="$(find "$staging" -mindepth 1 -maxdepth 1 -type f ! -name SHA256SUMS.txt -printf '%f\n' | LC_ALL=C sort)"
  [[ -n "$actual" && "$expected" == "$actual" ]] || fail 'Previous Release has missing, unsafe or unlisted assets'
  (cd "$staging" && sha256sum --check --strict SHA256SUMS.txt) || fail 'Previous Release failed SHA-256 verification'

  # A newer run of THIS SAME MOD might have published first, because GitHub's
  # pending queue is ordered by time of entering it, not by main merge order.
  # Never roll it back. The versioned primary artifact is the monotonic guard.
  old_primary=''
  while IFS= read -r name; do
    if [[ "$name" == $primary_glob ]]; then
      [[ -z "$old_primary" ]] || fail 'Multiple versions of the same primary mod in Latest'
      old_primary="$name"
    fi
  done <<< "$actual"
  if [[ -n "$old_primary" ]]; then
    old_version="$(version_of "$old_primary")"
    if [[ "$old_version" == "$new_version" ]]; then
      cmp -- "$staging/$old_primary" "$dest/$primary" || fail 'Same mod version has different bytes'
      printf '::notice::Release snapshot unchanged: %s is already published. Skipping replay.\n' "$primary"
      exit 75
    fi
    newer="$(printf '%s\n%s\n' "$old_version" "$new_version" | LC_ALL=C sort -V | tail -n 1)"
    if [[ "$newer" != "$new_version" ]]; then
      printf '::notice::Skipping stale %s (Latest contains %s); avoiding a rollback.\n' "$primary" "$old_primary"
      exit 75
    fi
  fi

  while IFS= read -r name; do
    own=false
    for pattern in "$primary_glob" "$@"; do
      # shellcheck disable=SC2053
      if [[ "$name" == $pattern ]]; then own=true; break; fi
    done
    if [[ "$own" == true ]]; then
      printf 'Replace previous owned asset: %s\n' "$name"
      continue
    fi
    [[ ! -e "$dest/$name" ]] || fail "Asset name conflict: $name"
    cp -- "$staging/$name" "$dest/$name"
    printf 'Carry immutable asset from %s: %s\n' "$latest" "$name"
  done <<< "$actual"
fi

# One checksum manifest for the entire snapshot, including unchanged mods.
(
  cd "$dest"
  rm -- SHA256SUMS.txt
  find . -mindepth 1 -maxdepth 1 -type f ! -name SHA256SUMS.txt -printf '%f\n' | LC_ALL=C sort |
    while IFS= read -r name; do
      [[ "$name" =~ ^[A-Za-z0-9][A-Za-z0-9._-]*$ ]] || fail 'Unsafe output asset name'
      sha256sum -- "$name"
    done > SHA256SUMS.txt
  sha256sum --check --strict SHA256SUMS.txt
) || fail 'Assembled Release snapshot failed integrity verification'
