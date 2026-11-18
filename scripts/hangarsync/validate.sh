#!/usr/bin/env bash
set -euo pipefail
test -n "${PYTHON27:?Set PYTHON27 to CPython 2.7.18}"
repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$repo_root"

python3 -m unittest discover -s mods/hangarsync/tests -v
(
  cd mods/hangarsync
  PYTHONPATH=source:tests "$PYTHON27" -B -m unittest -v \
    test_hangar_crew test_perk_tooltips test_remembered_crew test_battle_pass
)

python3 mods/hangarsync/tools/build.py
manifest="$(mktemp "${RUNNER_TEMP:-${TMPDIR:-/tmp}}/hangarsync-reproducibility.XXXXXX")"
trap 'rm -f "$manifest"' EXIT
python3 - "$manifest" <<'PY'
import hashlib
import json
from pathlib import Path
import sys

directory = Path('mods/hangarsync/dist')
version = Path('mods/hangarsync/VERSION').read_text(encoding='ascii').strip()
expected = {'GRZ_Hangar_Sync.wotmod', 'GRZ_Hangar_Sync-v' + version + '.zip'}
entries = list(directory.iterdir())
if {path.name for path in entries} != expected or any(not path.is_file() or path.is_symlink() for path in entries):
    raise SystemExit('Unexpected Hangar Sync build assets')
digests = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in entries}
Path(sys.argv[1]).write_text(json.dumps(digests, sort_keys=True) + '\n', encoding='ascii')
PY

python3 mods/hangarsync/tools/build.py
python3 - "$manifest" <<'PY'
import hashlib
import json
from pathlib import Path
import sys

directory = Path('mods/hangarsync/dist')
expected = json.loads(Path(sys.argv[1]).read_text(encoding='ascii'))
entries = list(directory.iterdir())
if any(not path.is_file() or path.is_symlink() for path in entries):
    raise SystemExit('Unexpected Hangar Sync build assets')
actual = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in entries}
if actual != expected:
    raise SystemExit('Hangar Sync build is not reproducible')
print('Reproducibility OK: Hangar Sync mod and installable ZIP')
PY

"$PYTHON27" -B scripts/hangarsync/bootstrap_smoke.py mods/hangarsync/dist/GRZ_Hangar_Sync.wotmod
python3 scripts/hangarsync/privacy.py --python27 "$PYTHON27" --scan-dist
