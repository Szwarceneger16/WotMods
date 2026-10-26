# Windows journal recovery — 0.2.12

## Failure and cause

On Windows, a history written by the incremental storage implementation could
fail to reopen with `No valid save was found. Corrupted files were not overwritten.`
The optional installation history uses the same storage implementation.

The writer created an OS descriptor with `os.open` and then wrapped it using
`os.fdopen(..., 'wb')`. It omitted `os.O_BINARY`. Under the Windows CRT behavior
used by CPython 2.7, a text-mode descriptor expands the journal header's final LF
to CRLF. The writer nevertheless records the intended binary length and hash.
The first transaction seeks to that intended offset, truncates the expanded LF
and replaces it with the first JSON byte. The result is:

```
intended: header JSON + LF + transaction JSON + LF
on disk:  header JSON + CR + transaction JSON + LF
```

The remaining offsets are correct, but a line-based reader sees the header and
first transaction as one invalid JSON document. The mirrored journal has the
same defect. Older full snapshots can initially hide the failure by providing
a fallback, until all retained commit descriptors depend on journals.

The incremental writer was introduced in 0.2.8. Linux-only runs, including Linux
CPython 2.7 tests, do not exercise Windows descriptor newline translation.

## Correction and compatibility

All exclusive storage-file creation now sets `getattr(os, 'O_BINARY', 0)` in the
`os.open` flags. Platforms without that flag retain their previous behavior.
Journal appends already use `open(..., 'r+b')` and remain binary.

For existing journals, the reader recognizes only a canonical version-1 header
whose closing brace is immediately followed by CR and the first transaction's
opening brace. It replaces that one delimiter with LF **in memory** and seeks to
the unchanged byte offset. It still verifies the original committed hash chain,
base-file checksum, schema and application-level state before accepting data.
It does not recalculate a stored checksum to make damaged data pass.

Loading leaves the original bytes intact. New commits use a new binary segment;
mixed legacy and corrected segments remain readable. Normal mirror and previous
generation recovery still apply. Unrelated corruption remains rejected, and a
history with no valid generation stays read-only. Reads remain bounded and staged;
there is no full-history rewrite on the per-battle path.

This correction cannot recreate results absent from every retained save, or
automatically merge a result lost by an earlier fallback into a newer history.
Such an earlier generation may contain useful recovery evidence, but merging
requires checking the record's identity and session membership separately.

## Upgrading and checking

1. Close World of Tanks and back up the entire `%APPDATA%\grz_wot_session_stats`
   directory, including `journal` and `startup-intake` subdirectories.
2. Remove older active `grz.sessionstats_*.wotmod` packages and install the fixed
   package. Preserve `mods/configs` and the existing AppData data.
3. Start the game, allow loading to finish in the garage and check the history.
   Restart once more after a result has been saved to check persistence.
4. If the failure remains, preserve the backup and current files for diagnosis;
   do not reset or delete history to suppress the message.

Check the version reported in the mod's own `logs/session-stats.log`. A downloaded
package's filename alone does not establish which copy the client actually loaded.

## Validation scope

`tests/test_windows_journal.py` models Windows descriptor translation independently
of the host platform. Its negative control confirms that `fdopen(..., 'wb')` alone
does not prevent the modeled expansion. Tests cover new binary writes, recovery
without mutation, deferred startup with incoming results, mixed journal chains,
verified mirrors, truncated commits, tampering, uncommitted tails and a maximum-size
first transaction. All fixtures are synthetic; no player history or logs are
included in the repository or CI.

This simulation and the regular Python 2.7/3 suites do not execute the Windows CRT
or a live WoT client. A Windows in-game save/restart check remains necessary.
