# Interface languages

The mod defaults to **the game client language** (`"language": "auto"`).
An explicit supported code in the configuration takes priority. An unavailable
game language or explicit unsupported code falls back to English.
The supported codes are `en` (English), `ru` (Russian), `fr` (French), `pl`
(Polish), `de` (German), `es` (Spanish), and `uk` (Ukrainian).

Set the root `language` property in `mods/configs/grz.sessionstats.json`, for example:

```json
{"schema_version": 1, "language": "uk"}
```

Existing appearance and session settings can stay in the same object. Open the
panel or select Refresh to reload both configuration files. Language changes
do not reset statistics, change account ownership or modify saved battle facts.
The main configuration is optional and supports partial nested overrides. For
example, `{"language":"fr"}` changes only the language; every omitted setting
keeps its built-in default. A missing main file is created with automatic language selection,
or copied from the legacy file beside the active package. An existing central file
always wins; failure to create/read the optional file retains defaults.

Existing files containing `"language": "en"` remain an explicit English override.
To follow the game after upgrading, change that value to `"auto"` or remove the
`language` property. Regional client codes such as `pl_PL` select their bundled
base language; an exact external regional catalog takes priority when available.
No files are polled per frame: selection reloads on startup, panel opening and Refresh.

Victory, Defeat and Draw use the client's original `battle_results:status` text
when the selected mod language matches the game. If configuration selects another
language, bundled translations in that language are used. Missing game APIs,
resource keys returned instead of translations and malformed text retain safe
per-message fallbacks. An unchanged shipped catalog does not mask the native
outcome text; a customized outcome entry takes priority. No history is rewritten.

## Custom translations

`grz.sessionstats.languages.json` is the editable UTF-8 catalog. The installation
ZIP places it in `mods/configs`, next to `grz.sessionstats.json`. The `.wotmod` also includes all
seven languages, so installing the `.wotmod` alone still provides translations.
The six top-level release assets are unchanged; the editable catalog is inside
the installation ZIP and its source bundle.

Keep your edited catalog when updating the mod. New messages missing from an
older override file use the current bundled defaults.
The external catalog is optional: deleting or omitting it keeps the selected
bundled language available. If the bundled resource itself cannot be read, an
English dictionary embedded in Python code remains available. Language files
are never required as separate downloads for the mod to start.

The catalog uses stable message keys, including panel headings, buttons,
accessibility labels, tooltips, reset confirmations, outcomes, vehicle classes,
coverage explanations, native notifications, storage/recovery warnings, footer
activity messages, and number/date formats. Names supplied by the game remain
as supplied by the client. WN8 identifiers and technical diagnostic field paths
remain recognizable across languages.

External catalogs can contain just the overrides you need:

```json
{
  "schema_version": 1,
  "languages": {
    "en": {"title": "My battle statistics"},
    "pl": {"refresh": "Wczytaj ponownie"},
    "pt-BR": {"title": "Estatísticas da sessão"}
  }
}
```

Select `pt-BR` in the main configuration to use that added language. Language
codes follow `xx`, `xxx`, or those forms followed by an uppercase region such
as `pt-BR`. An unavailable code selects English. Missing overrides use the
bundled selected language; entries absent from that language use English.

Preserve every numbered placeholder, such as `{0}` and `{1}`, including its
number of occurrences. They may be reordered in a translation. Attribute/index
access, conversion flags and format specifications are rejected. Values must
be nonempty plain strings of at most 4,096 characters without control
characters. JSON files are bounded to 2 MiB; duplicate keys, invalid UTF-8,
non-finite numbers and unsupported schemas reject the external file. Invalid
individual translations use their fallback while valid entries still apply.
Decoder recursion failures also reject only the catalog: the selected bundled
language, appearance settings and session-tab configuration remain active.

Translations are rendered as text. Native notifications escape rich-text
markup. No catalog content is evaluated as HTML, JavaScript, Python or CSS;
no online translation service is used. Diagnostics never include catalog
values, JSON excerpts or private paths. Long button captions are shortened
visually with ellipsis and retain the full caption or scope explanation in a
tooltip.

Older stored Polish warnings and synthetic map/vehicle fallback names are
translated when displayed. Their saved records are not rewritten or reset.

## Updating the shipped catalog

Edit the JSON and run:

```sh
python3 mods/sessionstats/tools/sync_languages.py
```

This generates the Python canonical English/legacy Polish lookup and the
panel's offline English fallback. The builder runs `--check` and rejects stale
generated fallbacks. Both runtime interpreters test complete key coverage and
placeholder parity for all seven shipped languages. Browser tests exercise
translated controls, outcomes, both reset scopes, errors, narrow/full-width
panels, footer activity, partial catalogs and text escaping. Native Gameface
rendering and translation terminology still benefit from in-game review.
