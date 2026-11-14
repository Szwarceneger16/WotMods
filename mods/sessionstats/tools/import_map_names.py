#!/usr/bin/env python3
"""Extract factual names from locally supplied, pinned client arena catalogues."""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
LANGUAGES = ('en', 'pl', 'ru', 'fr', 'de', 'es', 'uk')
COMMIT = '7c135eea16a3c9f8be2097cb1a408de4ee9d6f94'


def names_from_po(raw):
    result, key, value, active = {}, '', '', ''
    def save():
        if re.fullmatch(r'[0-9]+_[a-z0-9_-]+/name', key) and value:
            if key[:-5] in result:
                raise ValueError('duplicate_map_name')
            result[key[:-5]] = value
    for line in raw.decode('utf-8').splitlines():
        if line.startswith('msgid '):
            save(); key, value, active = ast.literal_eval(line[6:]), '', 'id'
        elif line.startswith('msgstr '):
            value, active = ast.literal_eval(line[7:]), 'str'
        elif line.startswith('"'):
            if active == 'id':
                key += ast.literal_eval(line)
            elif active == 'str':
                value += ast.literal_eval(line)
    save()
    return result


def document(directory):
    entries, catalogs = {}, {}
    for language in LANGUAGES:
        raw = (directory / (language + '.po')).read_bytes()
        entries[language] = names_from_po(raw)
        catalogs[language] = {'path': 'text/lc_messages/' + language + '/arenas.po',
                              'sha256': hashlib.sha256(raw).hexdigest()}
    assert all(set(value) == set(entries['en']) for value in entries.values())
    return {'schema_version': 1, 'source': {'repository': 'https://github.com/unicum-gg/wot.src',
            'commit': COMMIT, 'client': '2.4.1.5514', 'catalogs': catalogs},
            'maps': {key: {language: entries[language][key] for language in LANGUAGES}
                     for key in sorted(entries['en'])}}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('catalog_directory', type=Path, help='Directory containing en.po, pl.po, etc.')
    parser.add_argument('--output', type=Path, default=ROOT / 'data/map_names.json')
    args = parser.parse_args()
    args.output.write_text(json.dumps(document(args.catalog_directory), ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
