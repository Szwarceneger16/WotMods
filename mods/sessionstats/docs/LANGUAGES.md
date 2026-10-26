# Interface languages

The mod includes English, Polish, Russian, French, German, Spanish and Ukrainian.
All translation text is packaged in `res/grz_session_stats/languages.json` inside
the `.wotmod`. External catalogs cannot override messages or add languages. Old
`grz.sessionstats.languages.json` files are ignored, left untouched and not migrated.

## Selecting a language

Use **Language** in the statistics panel. **Automatic** follows WoT's client language;
unsupported client languages fall back to English. Regional client codes are normalized.
Selecting a fixed language overrides automatic selection.

The dropdown updates the existing `mods/configs/grz.sessionstats.json`:

```json
{"language": "auto"}
```

Supported values are `auto`, `en`, `pl`, `ru`, `fr`, `de`, `es` and `uk`.
Manual JSON editing remains supported: reopen the panel or select Refresh afterward.
GUI changes apply immediately to the panel and footer, persist across game restarts
and client-version folder changes, and preserve appearance, other JSON properties,
sort selections and all battle history. No new settings file is introduced.

A malformed, oversized, unsupported-schema or concurrently changed file is not
replaced. Failed saves preserve the previous configuration and selected language;
a local notification explains that the save failed. Windows Python 2.7 uses an
atomic Unicode file replacement after flushing the complete temporary file.

## Game resources and fallbacks

Vehicle and map names keep the client's own localization. For matching client and
selected languages, valid native WG Victory/Defeat/Draw text is preferred. Otherwise
the packaged translations are used. Outcome artwork is unchanged WG artwork.
Missing translation entries fall back to embedded English; unavailable optional
language/resource APIs must never stop result collection.

The installer contains only the ordinary appearance/language-choice config example
under `mods/configs/`. Source bundles retain `source/data/languages.json` for a full
reproducible source rebuild; it is documentation/source material and is never loaded
from there by an installed mod. Existing older installers remain valid for unchanged
mod carry-forward, while new builds record the embedded resource hash in BUILD.json.

## Development and validation

`data/languages.json` is the canonical source. Generate and check fallbacks with:

```sh
python3 mods/sessionstats/tools/sync_languages.py
python3 mods/sessionstats/tools/sync_languages.py --check
```

Tests cover all seven catalogs and placeholder parity, ignored external files,
config preservation and failure handling, native command ownership, persistence,
manual edits, keyboard navigation, narrow layouts and language switching in place.
