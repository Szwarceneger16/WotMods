# Source publication audit — 0.2.7

The import contains code, UI resources, the public WN8 expected-values table,
tests, synthetic previews, documentation and the unchanged OpenWG dependency.
No private game installation, account state, battle history, logs, screenshots,
dumps, authentication files or personal configuration were imported. The included
configuration JSON contains built-in defaults.

Fixture identifiers are synthetic: for example `DEMO:100`, small account numbers
in tests and sequential battle numbers from the generator. Public vehicle-type
descriptors in the WN8 table do not identify player accounts. Third-party author
names and links provide required attribution/licensing, not private details of
the repository owner.

Checks cover source and documentation, expanded archives, Python 2.7 bytecode
strings and virtual compilation paths. Diagnostic tests verify that health-check
messages omit nicknames, account numbers and raw reports. Pattern scans provide
an additional check, not proof of anonymization for every unknown data format.

The mod stores account-separated statistics locally. Such history must not be
included in PRs or Releases. Local logs rotate and are not uploaded by the mod.

This repository is public. Its owner, public GitHub identity, commit authors and
PR/Actions history remain visible under GitHub's platform behavior. Publishing
code does not hide this account metadata.
