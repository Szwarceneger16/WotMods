#!/usr/bin/env python3
"""Cache official EU update evidence; never infer a mods directory from patch labels."""
import argparse
import email.utils
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

RSS = 'https://worldoftanks.eu/pl/rss/news/updates/'
HOST = 'https://wgus-woteu.wargaming.net'
GUID = 'WOT.EU.PRODUCTION'
TTL = 24 * 60 * 60
BACKOFF = 15 * 60
HEADERS = {
    'User-Agent': 'WotMods update checker (+https://github.com/Szwarceneger16/WotMods)',
    'Accept': 'application/rss+xml, application/xml;q=0.9, text/xml;q=0.8',
}
VERSION = r'(?:0|[1-9][0-9]*)(?:\.(?:0|[1-9][0-9]*)){3}'


def xml(data):
    if b'<!DOCTYPE' in data.upper() or b'<!ENTITY' in data.upper():
        raise ValueError('Unexpected XML DTD/entity or HTML response: ' + repr(data[:100]))
    return ET.fromstring(data)


def fetch(url, maximum=4 * 1024 * 1024, start=None, length=None):
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != 'https' or parsed.username or parsed.password:
        raise ValueError('Only public HTTPS update sources are allowed')
    if parsed.hostname not in ('worldoftanks.eu', 'wgus-woteu.wargaming.net', 'dl-wot-gc.wargaming.net'):
        raise ValueError('Unexpected update source host')
    headers = dict(HEADERS)
    if start is not None:
        headers['Range'] = 'bytes=%d-%d' % (start, start + length - 1)
        maximum = length
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=30) as response:
        if urllib.parse.urlsplit(response.url).hostname != parsed.hostname:
            raise ValueError('Unexpected cross-host redirect')
        if start is not None and (response.status != 206 or not response.headers.get('Content-Range', '').startswith('bytes %d-%d/' % (start, start + length - 1))):
            raise ValueError('CDN did not honor the exact byte range')
        data = response.read(maximum + 1)
        print('Fetched %s: HTTP %s, %s, %d bytes' % (url, response.status, response.headers.get('Content-Type', ''), len(data)))
        if len(data) > maximum or (start is not None and len(data) != length):
            raise ValueError('Unexpected response size')
        return data


def rss_items(data):
    root = xml(data)
    if root.tag != 'rss' or root.find('channel') is None:
        raise ValueError('Expected an RSS channel, not an HTML challenge')
    items = []
    for item in root.findall('./channel/item')[:30]:
        link = item.findtext('link', '').strip()
        u = urllib.parse.urlsplit(link)
        if u.scheme != 'https' or u.netloc != 'worldoftanks.eu' or not u.path.startswith('/pl/news/updates/'):
            raise ValueError('Unexpected RSS article URL')
        published = email.utils.parsedate_to_datetime(item.findtext('pubDate', '')).timestamp()
        items.append({'title': item.findtext('title', '').strip(), 'url': link,
                      'published_at': published, 'description': item.findtext('description', '')})
    if not items:
        raise ValueError('Empty update feed')
    return items


def client_chain(meta, chain):
    if meta.findtext('./predefined_section/app_id') != GUID:
        raise ValueError('Not the EU production application')
    install = chain.find("./patches_chain[@type='install']")
    if install is None:
        raise ValueError('Expected the live install chain; preload/test chains are not accepted')
    seed = chain.findtext('.//web_seeds/url', '').strip()
    # Upgrade the publisher's HTTP seed to HTTPS; retain its exact path.
    seed = seed.replace('http://dl-wot-gc.wargaming.net/', 'https://dl-wot-gc.wargaming.net/', 1)
    if not seed.startswith('https://dl-wot-gc.wargaming.net/eu/patches/'):
        raise ValueError('Unexpected EU production CDN')
    patches = [p for p in install.findall('patch') if p.findtext('part') == 'client']
    by_from = {}
    for patch in patches:
        old, new = patch.findtext('version_from'), patch.findtext('version_to')
        if not re.fullmatch(VERSION, new or '') or (old != '0' and not re.fullmatch(VERSION, old or '')) or old in by_from:
            raise ValueError('Ambiguous or invalid client patch chain')
        files = []
        for f in patch.findall('./files/file'):
            name, size = f.findtext('name', ''), int(f.findtext('size', '0'))
            if not re.fullmatch(r'wot_[0-9.]+_eu_[a-z0-9]+/wot_[A-Za-z0-9._-]+', name) or not 0 < size <= 8 * 1024**3:
                raise ValueError('Unsafe archive name or size')
            files.append({'url': seed + name, 'size': size})
        if not files or len(files) > 16:
            raise ValueError('Invalid client volume list')
        by_from[old] = {'from': old, 'to': new, 'files': files}
    ordered, cursor, seen = [], '0', set()
    while cursor in by_from:
        if cursor in seen:
            raise ValueError('Cyclic client chain')
        seen.add(cursor)
        patch = by_from[cursor]
        ordered.append(patch)
        cursor = patch['to']
    if not ordered or len(ordered) != len(patches):
        raise ValueError('Disconnected or missing client install chain')
    return ordered


def directory_from_listing(listing):
    # Read actual archive paths, including the readme when 7z omits directories.
    versions = set(re.findall(r'^Path = mods/(' + VERSION + r')(?:/readme\.txt)?\r?$', listing, re.M))
    if len(versions) > 1:
        raise ValueError('Multiple mods directories in one client patch')
    return next(iter(versions), None)


def archive_directory(volumes, get=fetch):
    tool = shutil.which('7z') or shutil.which('7zz')
    if not tool:
        raise ValueError('7z is required to inspect official client archive headers')
    with tempfile.TemporaryDirectory() as tmp:
        paths = []
        for index, volume in enumerate(volumes):
            path = Path(tmp) / ('client.7z.%03d' % (index + 1))
            with path.open('wb') as stream:
                stream.truncate(volume['size'])
            paths.append(path)
        # Sparse files occupy only downloaded header bytes, not the client's GBs.
        for index, start, length in [(0, 0, min(65536, volumes[0]['size'])),
                                      (len(volumes)-1, max(0, volumes[-1]['size']-2097152), min(2097152, volumes[-1]['size']))]:
            data = get(volumes[index]['url'], start=start, length=length)
            with paths[index].open('r+b') as stream:
                stream.seek(start)
                stream.write(data)
        result = subprocess.run([tool, 'l', '-slt', str(paths[0])], check=True,
                                capture_output=True, text=True, timeout=60)
        return directory_from_listing(result.stdout)


def collect(get=fetch, inspect=archive_directory):
    feed = get(RSS)
    items = rss_items(feed)
    # Retain actual patch-note pages as evidence; RSS descriptions are summaries.
    for item in items[:3]:
        item['article_html'] = get(item['url'], maximum=1024 * 1024).decode('utf-8')
    meta_url = HOST + '/api/v1/metadata/?' + urllib.parse.urlencode(dict(guid=GUID, chain_id='unknown', protocol_version='7.2'))
    meta = xml(get(meta_url))
    query = dict(game_id=GUID, protocol_version='7.2', metadata_protocol_version='7.2', installation_id='WotMods',
                 client_type='sd', lang='PL', metadata_version=meta.findtext('version'),
                 client_current_version='0', locale_current_version='0', sdcontent_current_version='0')
    chain_url = HOST + '/api/v1/patches_chain/?' + urllib.parse.urlencode(query)
    chain = client_chain(meta, xml(get(chain_url)))
    for patch in reversed(chain):
        directory = inspect(patch['files'])
        if directory:
            # This is the *actual mods path*, never the client build or patch suffix.
            return {'client_version': directory, 'client_build': chain[-1]['to'], 'directory_patch': patch['to'],
                    'source': chain_url, 'archive_urls': [v['url'] for v in patch['files']],
                    'rss_url': RSS, 'rss_sha256': hashlib.sha256(feed).hexdigest(), 'items': items}
    raise ValueError('No exact mods directory found in the production install chain')


def update_cache(path, now=None, force=False, collect_fn=collect):
    now = time.time() if now is None else now
    path = Path(path)
    try:
        previous = json.loads(path.read_text())
        if (not isinstance(previous, dict) or previous.get('schema') != 1
                or not isinstance(previous.get('fetched_at', 0), (int, float))
                or not isinstance(previous.get('attempted_at', 0), (int, float))):
            previous = {}
    except (OSError, ValueError):
        previous = {}
    age = now - previous.get('fetched_at', 0)
    if (not force and not previous.get('error') and isinstance(previous.get('data'), dict)
            and re.fullmatch(VERSION, previous['data'].get('client_version', '')) and 0 <= age < TTL):
        return previous, False, True
    if not force and 0 <= now - previous.get('attempted_at', 0) < BACKOFF and previous.get('error'):
        return previous, False, False
    current = dict(previous, schema=1, attempted_at=now)
    try:
        data = collect_fn()
        if not re.fullmatch(VERSION, data.get('client_version', '')):
            raise ValueError('Invalid collected client directory')
        current.update(data=data, fetched_at=now, error=None)
        good = True
    except Exception as exc:
        # Keep last-good data and timestamp unchanged; stale data cannot authorize a release.
        current['error'] = type(exc).__name__ + ': ' + str(exc)
        good = False
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(current, ensure_ascii=False, indent=2))
    temp.replace(path)
    return current, True, good


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache', type=Path, default=Path('.wot-update-cache/state.json'))
    parser.add_argument('--force', action='store_true')
    args = parser.parse_args()
    state, refreshed, fresh = update_cache(args.cache, force=args.force)
    version = state.get('data', {}).get('client_version', '') if fresh else ''
    outputs = {'refreshed': str(refreshed).lower(), 'fresh': str(fresh).lower(), 'client_version': version}
    if os.environ.get('GITHUB_OUTPUT'):
        with open(os.environ['GITHUB_OUTPUT'], 'a') as stream:
            stream.writelines('%s=%s\n' % pair for pair in outputs.items())
    summary = ['### World of Tanks EU update check', '', 'Source: ' + RSS,
               'Fresh evidence: ' + str(fresh), 'Live mods directory: ' + (version or 'unavailable'),
               'Last successful fetch (UTC epoch): ' + str(state.get('fetched_at', 'never')),
               'Cache refreshed: ' + str(refreshed)]
    if state.get('error'):
        summary += ['', 'Refresh error (last-good data retained): ' + state['error']]
    for item in state.get('data', {}).get('items', [])[:5]:
        summary.append('- ' + item['title'].replace('\n', ' ') + ': ' + item['url'])
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'], 'a') as stream:
            stream.write('\n'.join(summary) + '\n')
    print(json.dumps(outputs))
    if not fresh:
        print('::warning::Official EU evidence could not be refreshed; publication must remain blocked. ' + state.get('error', '').replace('\n', ' '))


if __name__ == '__main__':
    main()
