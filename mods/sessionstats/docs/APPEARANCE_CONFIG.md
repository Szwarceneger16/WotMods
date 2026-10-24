# Appearance and scrolling configuration — 0.3.0

## File placement and applying changes

Place **`grz.sessionstats.json`** in the game installation's **`mods/configs`** directory:

```text
mods/2.4.1.0/grz.sessionstats_0.3.0.wotmod
mods/configs/grz.sessionstats.json
```

The JSON path has no release/client version. Preserve your custom file when replacing
the package; the configs directory remains in place across client-version changes.
The mod creates missing directories and the main JSON on startup, panel open or Refresh.
It copies a legacy JSON beside the uniquely identified active package if available;
otherwise it writes the complete defaults. Existing files, even malformed ones, are
never overwritten or filled with missing fields. Legacy originals remain intact.
Do not install packaged defaults over your custom configuration. To migrate an old
installation automatically, leave the central JSON absent when replacing the .wotmod.

Optional translation overrides use `mods/configs/grz.sessionstats.languages.json`.
A legacy override is copied only when its central counterpart is absent; no external
language file is required because the package contains all supported languages.
Creation uses a complete temporary file and create-only publication; concurrent
creation cannot replace another writer's file. Permission, disk and migration errors
are logged as `CONFIG_SETUP` without stopping collection or modifying source files.
Configuration loads at startup, when opening the panel and after **Refresh**.
Save the file, then reopen or refresh the panel. There is no per-frame polling.

The full supplied JSON contains **the current appearance as defaults**: 140 colors,
12 corner radii, three opacity settings and a scrolling multiplier. An unavailable file,
empty object `{}` and omitted fields use the built-in defaults. Partial nested
sections are supported; include only the fields you want to override.

## Optional installation session

Add `"sessions": {"instance_tab": true}` to display the installation tab.
The strict boolean defaults to `false`. Its shared history and independent
manual reset survive game restarts. The setting controls visibility, so hiding
the tab does not stop collection or clear the saved period. The two account
scopes remain independent. [Persistence and identity rules](ACCOUNT_SESSIONS.md).

## Commonly useful fields

| Field | Default | Meaning |
| --- | --- | --- |
| `colors.window_background` | `"#111309"` | Main window background |
| `colors.window_border` | `"#646044"` | Window border |
| `colors.table_header_background_start` | `"#292e1f"` | Table-header gradient start |
| `colors.table_header_background_end` | `"#222719"` | Table-header gradient end |
| `colors.table_row_background` | `"#181d11"` | First table-row background |
| `colors.table_row_following_background` | `"#1a1f13"` | Subsequent table-row background |
| `colors.table_row_following_border_top` | `"#2e3522"` | Subtle row separator |
| `colors.table_row_hover_background` | `"#252d1b"` | Hovered row background |
| `colors.metric_value_text` | `"#ebe7d4"` | Performance-table numbers |
| `colors.positive_text` | `"#c0d889"` | Positive balance |
| `colors.negative_text` | `"#e4ad84"` | Negative balance |
| `colors.garage_bars_background` | `"#969a9d"` | Garage-icon bars |
| `colors.garage_wn8_text` | `"#bdc0c2"` | Small WN8 label |
| `colors.garage_spinner_border` | `"rgba(207,190,140,0.25)"` | Translucent spinner segment |
| `colors.garage_spinner_border_top_color` | `"#dfd3a4"` | Bright spinner segment |
| `radii.window` | `4` | Window corners |
| `radii.table_header` | `3` | Table-header corners |
| `radii.table_row` | `2` | Table-row corners |
| `radii.group_card` | `5` | Vehicle/map/battle card corners |
| `radii.garage_spinner` | `5` | Spinner corners |
| `opacity.window` | `1.0` | Entire panel, including text |
| `opacity.garage_button` | `1.0` | Entire garage button |
| `opacity.disabled_controls` | `0.45` | Disabled controls |
| `scroll.speed_multiplier` | `1.0` | In-game wheel-speed multiplier |

Other full-JSON keys cover document backgrounds, title bars, period tabs, XP
switches, metric headings/values, separators, cards, battle results, messages,
buttons, reset confirmation, scrollbars, shadows and hover states. Suffixes mean:
`text` for text, `background` for backgrounds, `border`/`border_top`/`border_left`
for lines, `shadow` for shadows, `hover` for pointer hover, `active` for selection,
and `start`/`middle`/`end` for successive existing gradient colors.

## Formats and ranges

### Colors and transparent backgrounds

Accepted color formats:

- `"#abc"` — short RGB.
- `"#aabbcc"` — full RGB.
- `"#aabbcc80"` — RGB with a final hexadecimal alpha channel.
- `"rgb(170,187,204)"`.
- `"rgba(170,187,204,0.5)"` — alpha from `0` to `1`.
- `"transparent"`.

RGB channels are integers from `0` to `255`. Alpha `0` is fully transparent;
`1` is fully opaque. Hexadecimal `80` is approximately 50.2% opacity. Eight-digit
hex values are converted to `rgba(...)` to avoid depending on Gameface hex support.

To change **only background transparency**, use, for example,
`"colors": {"window_background": "rgba(17,19,9,0.8)"}`. Other backgrounds,
gradients and shadows retain their separate values. `opacity.window` affects
**the entire panel, including text and controls**.

Gradient/shadow colors are independently editable. JSON accepts neither entire
CSS declarations nor named colors such as `red`, `url(...)`, `var(...)`,
`currentColor`, selector names or arbitrary gradients. Gradient directions/stops,
shadow positions and layout remain part of the mod's styles.

### Corner radii

Each `radii` field accepts a number from **0 to 24**. Units follow WoT's UI scale;
one unit is one pixel at base scale. Do not append `px` or `rem`. Zero removes
the group's rounding. Styles rounded only at the top/bottom retain those same
corners; configuration does not change panel structure.

### Opacity

Each `opacity` field accepts **0 to 1**. `1` is fully visible, `0.8` is 80% visible,
and `0` is invisible. Do not use percentages or numeric strings: `0.8` is valid,
`"80%"` is not.

### Wheel speed

`scroll.speed_multiplier` accepts **0.1 to 8**:

- `1.0` preserves current speed.
- `1.5` increases each step by half.
- `2.0` doubles each step.
- `0.5` halves each step.

This affects the in-game scrolling adapter, including page-unit input. Direction
and endpoint clamping remain unchanged. Standalone HTML previews retain native
browser wheel handling.

## Example overrides

Keep the complete supplied file or replace it with a partial configuration. Only
the following values change; every omitted setting uses its default:

```json
{
  "schema_version": 1,
  "colors": {
    "window_background": "rgba(17,19,9,0.9)",
    "table_row_background": "#202719",
    "table_row_following_background": "#242c1c",
    "table_row_following_border_top": "#465336"
  },
  "radii": {
    "window": 6,
    "group_card": 7
  },
  "opacity": {
    "window": 1.0
  },
  "scroll": {
    "speed_multiplier": 1.5
  }
}
```

These are **example changes, not the bundled defaults**. Save UTF-8; BOM is
supported. JSON requires quoted keys, decimal points and commas between fields.
Comments and trailing commas are unsupported.

## Errors and logging

| Condition | Behavior |
| --- | --- |
| Missing file or individual field | Built-in defaults |
| Invalid JSON syntax/encoding, duplicate key or size above 128 KiB | All defaults |
| Invalid root type or unsupported `schema_version` | All defaults |
| Invalid individual color/type/range | That field's default; valid other settings remain |
| Invalid section type, such as `"colors": []` | That section's defaults |
| Unknown field | Ignored and logged |

`true` and `false` cannot substitute for numeric settings. Nonstandard `NaN` and
`Infinity` reject the file. Every number must be finite and within its range.
Invalid changes loaded by Refresh restore the appropriate defaults rather than
silently retaining earlier custom values.

Errors use **`CONFIG`**, a field name and rejection reason. Syntax errors include
line/column when supplied, including Python 2.7's text error format. Raw values
and full JSON contents are never logged. One read emits at most 64 field diagnostics
plus an omitted-excess notice.

Standard log:

```text
%APPDATA%\grz_wot_session_stats\logs\session-stats.log
```

## Implementation contract

`appearance.py` contains independent default copies and templates for the existing
complete stylesheets. Only validated scalar values are substituted. It does not
use CSS variables or load styles from external paths. Bundled static styles remain
the fallback.

Tests require default template expansion to match the stylesheets textually,
except for neutral `opacity:1` declarations added to the panel/button. Separate
checks require tokens for all actual colors, radii and opacity declarations, and
exact agreement with the supplied JSON defaults. Future base-style changes must
update this explicit contract.

Public functions: `default_config()`, `load_config(path)`, `validate_config(object)`
and `build_presentation(config)`. The last returns `panel_css`, `footer_css` and
`scroll_speed` for the existing UI models.

## Language selection

The root `"language": "auto"` is the default and follows the game language,
with English as fallback. Explicit `en`, `ru`, `fr`, `pl`, `de`, `es` or `uk`
take priority. Existing `"language": "en"` remains an English override; change
it to `"auto"` to follow the game. All seven catalogs are bundled in the `.wotmod`.
The neighboring `grz.sessionstats.languages.json` is optional and editable.
Removing it preserves bundled translations; embedded English is the final fallback.
See [LANGUAGES.md](LANGUAGES.md) for overrides and added languages.
