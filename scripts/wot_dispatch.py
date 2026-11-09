#!/usr/bin/env python3
"""Dispatch the one protected snapshot coordinator when installers lag EU."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

import release_installers
from wot_updates import VERSION


def gh(*args):
    return subprocess.check_output(['gh', *args], text=True)


def needs_rebuild(target, installed):
    if not re.fullmatch(VERSION, target):
        raise ValueError('Missing exact EU mods directory')
    wanted = tuple(map(int, target.split('.')))
    versions = [tuple(map(int, value.split('.'))) for value in installed]
    if len(versions) != len(release_installers.KINDS):
        raise ValueError('Expected one installer for every registered mod')
    if any(v > wanted for v in versions):
        raise ValueError('Refusing to downgrade an installer')
    return any(v != wanted for v in versions)


def main():
    if os.environ.get('GITHUB_REF') != 'refs/heads/main':
        raise ValueError('Only accepted main may dispatch the production coordinator')
    repo = os.environ['GITHUB_REPOSITORY']
    target = os.environ['WOT_CLIENT_VERSION']
    release = json.loads(gh('api', 'repos/' + repo + '/releases/latest'))
    if not release.get('immutable') or release.get('draft') or release.get('prerelease'):
        raise ValueError('Latest release is not immutable production evidence')
    with tempfile.TemporaryDirectory() as tmp:
        gh('release', 'download', release['tag_name'], '--repo', repo, '--dir', tmp)
        assets = release['assets']
        if len(assets) != len(release_installers.KINDS):
            raise ValueError('Missing or duplicate installer assets')
        for asset in assets:
            name = asset['name']
            if Path(name).name != name:
                raise ValueError('Unexpected asset name')
            release_installers.identity(name)
            digest = 'sha256:' + hashlib.sha256((Path(tmp) / name).read_bytes()).hexdigest()
            if digest != asset.get('digest'):
                raise ValueError('Downloaded immutable asset digest mismatch')
        reports = release_installers.verify_directory(Path(tmp))
        # verify_directory validates both installers and cross-mod paths/resources.
        versions = [report[2] for report in reports]
        if not needs_rebuild(target, versions):
            print('All verified installers already target ' + target)
            return
    workflow = 'wotmods-release.yml'
    runs = json.loads(gh('run', 'list', '--repo', repo, '--workflow', workflow, '--branch', 'main',
                         '--limit', '100', '--json', 'status,databaseId'))
    if any(r['status'] in ('queued', 'in_progress', 'waiting', 'requested', 'pending') for r in runs):
        print('A unified snapshot run is already pending: ' + workflow)
        return
    gh('workflow', 'run', workflow, '--repo', repo, '--ref', 'main')
    print('Dispatched one snapshot coordinator for ' + target)


if __name__ == '__main__':
    main()
