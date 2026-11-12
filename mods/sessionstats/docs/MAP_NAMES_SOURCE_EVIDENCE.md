# Map names and selected UI language

The bundled `data/map_names.json` contains only 68 factual arena names in English,
Polish, Russian, French, German, Spanish and Ukrainian. These are the game's own
words, extracted from its gettext `arenas` catalogues; no map descriptions or
machine translations are included.

Source: [client catalogue mirror, pinned commit](https://github.com/unicum-gg/wot.src/tree/7c135eea16a3c9f8be2097cb1a408de4ee9d6f94/text/lc_messages).
Its pinned README identifies EU client **2.4.1.5514**. The mirror's
[`generate-locales.ts`](https://github.com/unicum-gg/wot.build/blob/main/generate-locales.ts)
extracts the original `.mo` files from Wargaming's per-language update packages
and converts them to `.po`. All seven selected languages come from the EU client.
Each exact fetched `.po` was also checked against its Git blob SHA-1. The resource
records the SHA-256 of every complete source catalogue and the immutable commit.

To reproduce, supply the seven pinned files as `en.po`, `pl.po`, `ru.po`, `fr.po`,
`de.po`, `es.po` and `uk.po`, then run:

```sh
python3 mods/sessionstats/tools/import_map_names.py /path/to/catalogues
```

Only native `<geometry>/name` entries are selected. Full geometry IDs resolve
directly. Removing the numeric prefix is supported only when that alias names
exactly one geometry: `north_america` is ambiguous between `44_north_america`
(Live Oaks) and `45_north_america` (Highway), so it deliberately keeps its saved
name. Unknown/new IDs also keep their original game-supplied name. A known ID
without a requested translation uses its verified English name.

The resource is installed inside the wotmod and read through `ResMgr`; source
tools use the same checked-in JSON. Every projection carries stable map IDs for
individual battles and nested histories. Localization changes only fresh
presentation snapshots, including map visual/hover labels. Saved native names,
map IDs and account history remain unchanged. There is no network access at
runtime. Existing frontend feed and card cache identities include UI language.

Calendar month and weekday words also use the selected UI catalogue. Numeric
date order, separator, 12/24-hour convention and first weekday continue to use
client preferences and explicit configuration overrides.
