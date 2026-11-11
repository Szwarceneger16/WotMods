# Calendar and regional formatting in 0.8.0

The From and To controls share the same inline editor and compact camouflage
popover. Click the month heading for a twelve-month grid or the year heading
for descending years from the current year to 2010. Month arrows and calendar
keyboard navigation stay inside that range. Existing manually entered or saved
1970–9999 dates remain valid; opening the graphical picker clamps its initial
year to the graphical range without submitting a change.

The time buttons open an analog hour or minute clock in the same popover.
The 24-hour face has inner and outer rings; a 12-hour clock offers AM/PM buttons.
Clicking an hour advances to minutes. Clicking or dragging the minute hand can
choose any minute, and arrow keys adjust the focused clock by one hour/minute.
Hour arrows cross AM/PM boundaries correctly. The calendar icon returns to days.
Apply validates the complete local date, including nonexistent DST times, before
sending the account-owned range. Cancel, Escape, outside clicks and account
changes retire the popover and its temporary drag listeners.

## Regional preferences

`GameAPI.date_settings()` probes WoT's native short-date and short-time formatters
with a fixed local sample. This preserves numeric DMY, MDY or YMD ordering,
separators and 12/24-hour preferences independently of the chosen mod language.
The implementation was checked against the pinned public client source:

- [Backport exports](https://github.com/izeberg/wot-src/blob/5e721e36891c80d8d51a431164960c863641ee63/sources/res/scripts/client/gui/impl/backport/__init__.py)
- [Native Wulf date/time wrappers](https://github.com/izeberg/wot-src/blob/5e721e36891c80d8d51a431164960c863641ee63/sources/res/scripts/client/gui/impl/backport/backport_system_locale.py)

Windows `GetLocaleInfoEx` (or `GetLocaleInfoW` on older systems) supplies the
current user's date override, first weekday, abbreviated weekday names, month
names and AM/PM labels. It does not change Python's process locale. On other
platforms, available non-C `locale.nl_langinfo` settings are used. Unsupported
or unavailable metadata falls back to the bundled language catalog and the
existing Monday-first, 24-hour editor. Python's C locale is not treated as a
user preference. The frontend does not require browser `Intl` support.

The backend bounds each field before exposing it. The same metadata governs
the inline mask, parser, placeholder, calendar labels and compact battle dates.
A complete draft is converted through its original format when regional settings
change, preserving its timestamp; partial drafts retain their typed digits.
Invalid-date messages do not prescribe a conflicting hardcoded date format.

## Verification

`test_date_locale.py` covers Windows user overrides, native formatter precedence,
DMY/MDY/YMD patterns, C-locale fallback and metadata bounds. Runtime configuration
checks verify that native preferences reload without changing the UI language.
`ui-custom-date-source.cjs` exercises actual shipped parser/mask/range functions,
all seven catalogs, native ordering, 12-hour noon/midnight and DST validation
without Chromium or Intl. `ui-custom-dates.cjs` exercises graphical month/year
navigation, picker bounds, clock selection and keyboard wrapping, native weekday
labels, exact epochs, account teardown and viewport-constrained positioning.
