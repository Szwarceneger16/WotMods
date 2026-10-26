# Source import and publication checks

Baseline: the Session Stats 0.2.7 source package. The initial import retained its
runtime/UI code. Review fixes are recorded in `REVIEW_FIXES_PR3.md`; the storage
schema and default JSON remained unchanged at import. The builder gained release
numbering, a complete asset manifest and generated-test-report filtering. Visual
checks retain exact style/geometry comparison; raster comparison permits at most
16 edge pixels differing by up to 6/255 per channel for Chromium renderer rounding.

Initial local import validation, before review fixes:

- 284 Session Stats tests on Python 3 and 284 on CPython 2.7.18.
- 175 tests for the existing mod and shared release infrastructure.
- 78 panel checks, 22 wheel checks, 22 spinner-activity checks, 12 footer
  compatibility checks, 30 appearance checks and the baseline-icon suite.
- The original 0.2.7 `.wotmod` matched the input package byte for byte:
  SHA-256 `76e5cffa54d79b6cbee37858725d063664082fe8cf0da41eb9406b10bff394bd`.
  This is a historical baseline; corrected code has a different digest.
- All six release assets matched across two builds.
- A trial 0.2.8 build carried the correct version inside bytecode too.
- No package-identifier/resource-path collisions with Medkit Reminder.
- Source, nested-archive and bytecode constant/path privacy scans: PASS.

These results describe the locally combined PRs. The new workflow must be
accepted on `main` before its CI result can validate the source import. The
repository version has not been run in a real WoT client. Limitations:
`UPDATE_COMPATIBILITY_SOURCES.md`, `RESULT_HEALTH_CONTRACT.md` and
`PUBLICATION_PRIVACY.md`.
