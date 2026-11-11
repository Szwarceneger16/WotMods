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
    # $GITHUB_ENV is read by later Actions steps only, not the current shell.
    export PYTHON27="${RUNNER_TEMP:-${TMPDIR:-/tmp}}/sessionstats-cpython27/Python-2.7.18/python"
    [[ -x "$PYTHON27" ]] || { echo 'Verified Python 2.7 interpreter missing' >&2; exit 1; }
    bash scripts/sessionstats/validate.sh
    python3 scripts/sessionstats/release.py --verify-directory mods/sessionstats/dist --version "$version"
    source_dir=mods/sessionstats/dist
    ;;
  hangarsync)
    bash scripts/sessionstats/python27.sh
    export PYTHON27="${RUNNER_TEMP:-${TMPDIR:-/tmp}}/sessionstats-cpython27/Python-2.7.18/python"
    [[ -x "$PYTHON27" ]] || { echo 'Verified Python 2.7 interpreter missing' >&2; exit 1; }
    bash scripts/hangarsync/validate.sh
    # The native harness first tests its reviewed baseline. The release planner
    # can allocate a later independent version or a newer WoT target directory.
    python3 - "$version" "$client" "$PYTHON27" <<'PY'
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

version, client, python27 = sys.argv[1:]
directory = Path('mods/hangarsync/dist')
baseline = Path('mods/hangarsync/VERSION').read_text(encoding='ascii').strip()
baseline_zip = directory / ('GRZ_Hangar_Sync-v' + baseline + '.zip')
baseline_zip.unlink()
expected = {'GRZ_Hangar_Sync.wotmod', 'GRZ_Hangar_Sync-v' + version + '.zip'}
command = [sys.executable, 'mods/hangarsync/tools/build.py',
           '--version', version, '--client-version', client]
digests = None
for _ in range(2):
    built = subprocess.run(command, check=True, capture_output=True, text=True)
    report = json.loads(built.stdout)
    entries = list(directory.iterdir())
    if ({entry.name for entry in entries} != expected or
            any(not entry.is_file() or entry.is_symlink() for entry in entries) or
            report['client_version'] != client):
        raise SystemExit('Unexpected planned Hangar build output')
    actual = {entry.name: hashlib.sha256(entry.read_bytes()).hexdigest() for entry in entries}
    if digests is not None and actual != digests:
        raise SystemExit('Planned Hangar build is not reproducible')
    digests = actual

subprocess.run([python27, '-B', 'scripts/hangarsync/bootstrap_smoke.py',
                str(directory / 'GRZ_Hangar_Sync.wotmod')], check=True)
spec = importlib.util.spec_from_file_location('hangar_release_privacy',
                                            'scripts/hangarsync/privacy.py')
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)
problems = []
for entry in sorted(directory.iterdir()):
    problems.extend(audit.scan_bytes(entry.name, entry.read_bytes(), python27))
if problems:
    labels = sorted({label for _, found in problems for label in found})
    raise SystemExit('Planned Hangar privacy audit blocked: ' + ','.join(labels))
print('Planned Hangar version/client build is reproducible and privacy-audited')
PY
    source_dir=mods/hangarsync/dist
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
