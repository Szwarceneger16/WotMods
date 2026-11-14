# Client date and clock formatting

Automatic date/time formatting comes from the WoT client, independently of the
Windows regional settings and the browser locale. There is no XVM dependency.

The native adapter samples `gui.shared.formatters.date_time.getRegionalDateTime`
with `DateTimeFormatsEnum.SHORTDATE` and `SHORTTIME`. Those formatters use the
client's translated `R.strings.datetime_formats` resources and `CURRENT_REALM`.
Month and weekday labels use `getFormattedDateTime` with its resource-backed
`%B` and `%a` handlers. The system-locale `backport.getShortDateFormat` and
`getShortTimeFormat` wrappers are deliberately excluded.

If the optional client formatters are unavailable, the bundled client-language
defaults supply DMY ordering, a dot separator (slash for French/Spanish), a
Monday-first calendar and a 24-hour clock. Twelve-hour mode is enabled only by
an actual native formatted sample or by explicit configuration. The inline
editor, date placeholders, calendar, clock, saved time-point labels and compact
battle dates all receive the same effective metadata.

## Configuration takes priority

Add only the fields you want to force to `mods/configs/grz.sessionstats.json`:

```json
{
  "date_time": {
    "order": "DMY",
    "separator": ".",
    "hour_format": "24h",
    "first_weekday": 1
  }
}
```

Every field defaults to `"auto"`, which keeps the corresponding client value.
`order` also accepts `"MDY"` and `"YMD"`; `separator` accepts `"."`, `"/"` and
`"-"`; `hour_format` accepts `"12h"` and `"24h"`. Weekdays use `0` for Sunday
through `6` for Saturday. Invalid leaves fall back independently. Refresh or
reopen the panel to apply changes. Existing configs are never rewritten merely
to insert the new defaults, and explicit overrides survive native/UI language
changes and subsequent refreshes.

## Verified client sources

Pinned reference: `izeberg/wot-src` at
`5e721e36891c80d8d51a431164960c863641ee63`:

- [Resource-backed date/time formatters](https://github.com/izeberg/wot-src/blob/5e721e36891c80d8d51a431164960c863641ee63/sources/res/scripts/client/gui/shared/formatters/date_time.py)
- [Native format enum](https://github.com/izeberg/wot-src/blob/5e721e36891c80d8d51a431164960c863641ee63/sources/res/scripts/client/gui/impl/gen/view_models/constants/date_time_formats.py)
- [System-locale wrappers excluded from this flow](https://github.com/izeberg/wot-src/blob/5e721e36891c80d8d51a431164960c863641ee63/sources/res/scripts/client/gui/impl/backport/backport_system_locale.py)

Python tests exercise the actual adapter imports, resource-formatter calls,
fallbacks, per-field override priority and config reload without rewrites.
Actual-source and browser regressions pass the real Python-produced metadata to
the shipped editor/clock and verify both 24-hour client defaults and forced
12-hour/YMD formats. Existing strict future, opposite-bound, DST and epoch
validation remains in force.
