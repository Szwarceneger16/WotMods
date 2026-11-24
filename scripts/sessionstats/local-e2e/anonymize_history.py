"""Export a private local QA profile from Session Stats history without copying it."""

import argparse
import json
import os
from pathlib import Path
import re
import sys

from history_profile import profile_from_rows


SOURCE = Path(__file__).resolve().parents[3] / 'mods' / 'sessionstats'
ACCOUNT_DIRECTORY = re.compile('[0-9a-f]{64}\\Z')


def latest_eu_rows(ledger, store):
    candidates = []
    for directory in ledger.iterdir():
        if not directory.is_dir() or not ACCOUNT_DIRECTORY.fullmatch(directory.name):
            continue
        modified = max((file.stat().st_mtime_ns for file in directory.glob('state-*.json')), default=0)
        if modified:
            candidates.append((modified, directory))
    for _, directory in sorted(candidates, reverse=True):
        state = store(str(directory)).load()
        if state and str(state.get('account_key', '')).upper().startswith('EU:'):
            return state['battles'].values()
    raise ValueError('No EU account history found. An exact ledger directory can be supplied explicitly.')


def export_profile(source, output, ledger_dir=None):
    if os.environ.get('GITHUB_ACTIONS') == 'true':
        raise ValueError('Private QA profiles must be generated locally.')
    output = output.resolve()
    if any((parent / '.git').exists() for parent in output.parents):
        raise ValueError('Save the private QA profile outside any Git checkout.')
    ledger_root = Path(os.environ.get('APPDATA', '')) / 'grz_wot_session_stats'
    if ledger_dir is None and not os.environ.get('APPDATA'):
        raise ValueError('Supply an exact Session Stats account ledger directory.')
    protected = [ledger_root.resolve()]
    if ledger_dir is not None:
        protected.append(ledger_dir.resolve())
    if any(output.is_relative_to(root) for root in protected):
        raise ValueError('Save the QA profile outside Session Stats history directories.')
    sys.path.insert(0, str(source.resolve() / 'src'))
    from grz_session_stats.storage import GenerationStore, StorageError

    # Load the checksum-validated state and journal. Neither path saves, copies,
    # or repairs storage. The only exported object is the closed-band schema.
    try:
        if ledger_dir is not None:
            state = GenerationStore(str(ledger_dir.resolve())).load()
            if not state or not isinstance(state.get('battles'), dict):
                raise ValueError('No validated history found in the selected ledger.')
            rows = state['battles'].values()
        else:
            rows = latest_eu_rows(ledger_root, GenerationStore)
    except StorageError:
        raise ValueError('Could not load a validated Session Stats ledger.') from None
    profile = profile_from_rows(rows)
    with output.open('x', encoding='utf-8', newline='\n') as handle:
        json.dump(profile, handle, ensure_ascii=True, sort_keys=True, indent=2)
        handle.write('\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=SOURCE)
    parser.add_argument('--ledger-dir', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    options = parser.parse_args()
    try:
        export_profile(options.source, options.output, options.ledger_dir)
    except (ValueError, OSError, RuntimeError, KeyError, TypeError, ImportError, AttributeError):
        # A malformed account file, path or account label must never be echoed.
        parser.exit(1, 'Could not export the local QA profile. Check the ledger, the source checkout '
                       'and a new writable output path outside Git.\n')
    print('Wrote a local aggregate QA profile. Keep it outside Git.')


if __name__ == '__main__':
    main()
