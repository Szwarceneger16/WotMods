# Account and installation sessions

The two default tabs are isolated by account and region. Switching A → B → A
restores A's own manual period. Resetting B never changes A. Nicknames are
not used as storage keys.

| Scope | Accounts | Reset | After restarting the game |
| --- | --- | --- | --- |
| Since launch | Current account | New game process | Empty |
| Since reset | Current account | Its own manual reset | Preserved |
| Installation, optional tab | Accounts observed in this installation | Its own manual reset | Preserved |

To display the installation tab, add this section to the existing JSON beside
the mod. The previous `instance_tab` option name is retained for compatibility;
it now selects the durable installation scope, not a process-only scope.

```json
{
  "sessions": {
    "instance_tab": true
  }
}
```

The default is `false`. Missing fields and invalid types keep the tab hidden.
The setting controls visibility; collection continues while hidden, so toggling
or restarting with the tab hidden does not create a gap in the saved period.
Settings reload when opening the panel or choosing Refresh.

The installation ledger and its manual reset boundary use the same checksummed,
atomic generation store as account histories. They are saved under the local
mod data directory in a separate `installations` namespace. Restarting, closing
before a result arrives, switching accounts and updating the client version do
not clear that period. Only its explicit manual reset starts a new one.

Installation identity comes from the verified physical game root containing
`paths.xml`, independently of the version directory under `mods`. Its normalized
path is hashed; the shared ledger contains neither the raw path nor raw account
IDs. Distinct installation roots remain separate even when account data uses
the same AppData directory. Moving the game root selects a different namespace;
the former history is retained. Unknown or ambiguous roots never fall back to
one global shared history. Account collection remains available independently.

Each account/battle pair has a stable hashed key. WN8, averages, coverage and
groups are computed from the shared ledger's individual normalized records.
The installation reset never resets an account; account resets never reset the
installation. Confirmation closes on account changes and stale commands are
rejected. The footer spinner still follows the active account only.

Beginnings are saved before results. A result delivered after a restart fills
its existing shared record exactly once and retains its original reset epoch.
A battle started before an installation reset cannot enter the new period,
including when its result arrives in a later game process. Unknown historical
results without installation provenance are not imported from another client's
account history. Known records from the current process can be adopted if
installation discovery becomes available late.

No account-history migration or reset is required. Earlier account archives
lack installation provenance and are not guessed into the new shared ledger.
Shared collection starts with this implementation's observed battles. Errors
in its storage do not block account results; the panel reports incomplete or
unavailable shared storage instead of silently overwriting existing data.

Tests use synthetic accounts/results and cover restarts, independent durable
resets, separate installations, delayed results, duplicate delivery, corrupted
generations and failed writes. Python and Chromium checks do not replace an
in-game test with the actual WoT client.
