#!/usr/bin/env bash
# Build exactly one independently versioned module in a read-only Actions job.
# The publisher consumes only the verified ZIP; no build tools run with write access.
set -euo pipefail

[[ $# == 3 ]] || { echo 'Usage: build_release_module.sh MODULE VERSION CLIENT' >&2; exit 2; }
module="$1"
version="$2"
client="$3"
[[ "$version" =~ ^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$ ]] || exit 2
[[ "$client" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]] || exit 2
export WOT_CLIENT_VERSION="$client"

case "$module" in
  staysharp)
    export WOTMOD_VERSION="$version"
    python3 scripts/privacy_audit.py
    python3 -m unittest discover -s tests -v
    python3 source/build_wotmod.py
    python3 scripts/privacy_audit.py --scan-dist
    (cd dist && sha256sum -- *.wotmod > SHA256SUMS.txt && sha256sum --check --strict SHA256SUMS.txt)
    source_dir=dist
    ;;
  sessionstats)
    export SESSIONSTATS_VERSION="$version"
    bash scripts/sessionstats/python27.sh
    bash scripts/sessionstats/validate.sh
    python3 scripts/sessionstats/release.py --verify-directory mods/sessionstats/dist --version "$version"
    source_dir=mods/sessionstats/dist
    ;;
  *)
    echo "Unknown module builder: $module" >&2
    exit 2
    ;;
esac

mkdir -p release-module
python3 scripts/release_installers.py package release-module \
  --source "$source_dir" --mod "$module" --client-version "$client"
rm -- release-module/SHA256SUMS.txt

python3 - "$module" "$version" "$client" <<'PY'
import sys
sys.path.insert(0, 'scripts')
from pathlib import Path
from release_installers import installer_name, verify
module, version, client = sys.argv[1:]
files = list(Path('release-module').iterdir())
assert len(files) == 1 and files[0].name == installer_name(module, version)
assert verify(files[0])[:3] == (module, version, client)
print('Verified isolated installer:', files[0])
PY
