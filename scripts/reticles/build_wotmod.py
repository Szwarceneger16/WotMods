# -*- coding: utf-8 -*-
"""Build one versioned, deterministic WoT package with CPython 2.7."""
from __future__ import print_function

import argparse
import hashlib
import io
import json
import marshal
import os
import re
import struct
import sys
import zipfile

ROOT = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(ROOT, '..', '..'))
ASSETS = os.path.join(ROOT, 'assets')
SOURCES = {'aimtimer': ('0.1.7', 'AimTimer'), 'rangefinder': ('0.1.13', 'Rangefinder')}
SEMVER = r'(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\Z'
HOSTS = {
    'reticle_decor.swf': '353d25b9d980d578d3c5ae6311b7c3e056e935a6dff1a1c421dd630e5119ece7',
    'battle_mechanics.swf': '8976a8201debbf9b7173b93e108591aaebad1e71be5e7e051fb43960d5eeafdb',
}
HUD_TEXTURES_SHA256 = '46800e1469bb4f1cc36f434a831eb3082d6ded97e14123b59892f3c4082389ea'
SCENES = ('arcade', 'sniper', 'arty_top', 'arty_trajectory')
UI_LOCALES = ('de', 'en', 'es', 'fr', 'pl', 'ru', 'uk')
PNG_HEADER = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR'


def read(path):
    with open(path, 'rb') as stream:
        return stream.read()


def put(archive, name, data):
    info = zipfile.ZipInfo(name.replace('\\', '/'), (2020, 1, 1, 0, 0, 0))
    info.compress_type = zipfile.ZIP_STORED
    archive.writestr(info, data)


def scene_size(path):
    with open(path, 'rb') as stream:
        header = stream.read(24)
    if len(header) != 24 or not header.startswith(PNG_HEADER):
        raise ValueError('Preview scenes must use lossless PNG')
    return struct.unpack('>II', header[16:24])


def scene_resource(scene, step):
    return 'scenes/%s_%d.png' % (scene, step)


def compile27(source, name):
    if sys.version_info[:2] != (2, 7):
        raise RuntimeError('Build packages using CPython 2.7, matching the WoT client')
    import imp
    return imp.get_magic() + struct.pack('<I', 0) + marshal.dumps(compile(source, name, 'exec'))


def catalog():
    result = {'version': 1, 'scenes': {}}
    labels = {'arcade': u'Trzecia osoba', 'sniper': u'Snajperski',
              'arty_top': u'Artyleria z góry', 'arty_trajectory': u'Trajektoria'}
    defaults = {'arcade': 1, 'sniper': 3, 'arty_top': 2, 'arty_trajectory': 2}
    for scene in SCENES:
        frames = []
        for step in range(5):
            zoom = (2, 4, 8, 16, 25)[step] if scene == 'sniper' else None
            frames.append({'step': step, 'zoom': zoom, 'label': (u'×%d' % zoom) if zoom else '%d / 5' % (step + 1),
                           'src': None, 'marker_scale': 1.0, 'ellipse': [95, 52], 'calibrated': False})
        result['scenes'][scene] = {'label': labels[scene], 'default_step': defaults[scene],
                                   'frames': frames}
    assets = {}
    for name in ('trajectory-catalog.json', 'catalog.json'):
        asset_path = os.path.join(ASSETS, name)
        if not os.path.isfile(asset_path):
            continue
        data = json.loads(read(asset_path).decode('utf-8'))
        if data.get('version') != 1:
            raise ValueError('Unsupported scene catalog version')
        assets.update((scene, entry) for scene, entry in data.get('scenes', {}).items()
                      if entry.get('frames'))
    for scene in SCENES:
        seen = set()
        for frame in assets.get(scene, {}).get('frames', []):
            step = frame.get('step')
            if type(step) is not int or step not in range(5) or step in seen:
                raise ValueError('Invalid or duplicate scene step')
            expected = scene_resource(scene, step)
            if frame.get('src') != expected:
                raise ValueError('Unexpected asset resource name')
            path = os.path.join(ASSETS, expected)
            width, height = scene_size(path)
            if (tuple(frame.get('frame_size', ())) != (width, height) or
                    width < 1920 or width * 9 != height * 16):
                raise ValueError('Scene must match its full 16:9 frame: ' + expected)
            if 'markers' in frame:
                raise ValueError('Unexpected legacy scene markers')
            if 'vehicle' in frame:
                vehicle = frame['vehicle']
                anchor = vehicle['anchor']
                if (scene != 'arty_trajectory' or not re.match(r'^[A-Z0-9 -]{1,20}\Z', vehicle['name']) or
                        len(anchor) != 2 or any(type(value) is not int for value in anchor) or
                        not (0 <= anchor[0] < width and 0 <= anchor[1] < height)):
                    raise ValueError('Invalid trajectory vehicle label: ' + expected)
            result['scenes'][scene]['frames'][step].update(frame)
            seen.add(step)
        if scene == 'arty_trajectory' and seen:
            entry = result['scenes'][scene]
            entry['frames'] = [frame for frame in entry['frames'] if frame['step'] in seen]
            for index, frame in enumerate(entry['frames']):
                frame['label'] = '%d / %d' % (index + 1, len(entry['frames']))
            if entry['default_step'] not in seen:
                entry['default_step'] = entry['frames'][0]['step']
    return result


def artillery_focus_catalog(scenes):
    path = os.path.join(ASSETS, 'artillery-focus.json')
    if not os.path.isfile(path):
        return {}
    data = json.loads(read(path).decode('utf-8'))
    if data.get('version') != 1 or set(data['scenes']) - {'arty_top', 'arty_trajectory'}:
        raise ValueError('Unexpected artillery focus catalogue')
    layouts = {}
    for scene, steps in data['scenes'].items():
        frames = dict((frame['step'], frame['src']) for frame in scenes['scenes'][scene]['frames'])
        for step, stages in steps.items():
            if (step not in ('0', '1', '2', '3', '4') or
                    not frames.get(int(step)) or
                    len(stages) != 3 or any(len(stage) != 37 for stage in stages)):
                raise ValueError('Missing or invalid artillery focus geometry')
            asset = os.path.join(ASSETS, frames[int(step)])
            evidence = data.get('evidence', {}).get(scene, {}).get(step, {})
            if hashlib.sha256(read(asset)).hexdigest() != evidence.get('image_sha256'):
                continue
            for stage in stages:
                for point in stage:
                    if (len(point) != 3 or any(type(value) not in (int, float) for value in point) or
                            not (-32768 <= point[0] <= 32768 and -32768 <= point[1] <= 32768 and
                                 0 <= point[2] <= 1)):
                        raise ValueError('Invalid artillery focus point')
            layouts[(scene, int(step))] = stages
    return layouts


def ui_strings():
    messages = json.loads(read(os.path.join(ROOT, 'ui_strings.json')).decode('utf-8'))
    groups = ('common', 'aimtimer', 'rangefinder')
    if set(messages) != set(UI_LOCALES) or set(messages['en']) != set(groups):
        raise ValueError('UI locales must match Session Stats')
    for locale in UI_LOCALES:
        if (set(messages[locale]) != set(groups) or any(
                set(messages[locale][group]) != set(messages['en'][group]) or
                not all(isinstance(value, unicode) and value.strip()
                        for value in messages[locale][group].values())
                for group in groups)):
            raise ValueError('Incomplete UI translation: ' + locale)
    return messages


def localize_ui(source, filename, folder, messages):
    if filename == 'settings.js':
        marker = b'/* GRZ_UI_STRINGS */ {}'
        labels = dict((locale, dict(messages[locale]['common'].items() + messages[locale][folder].items()))
                      for locale in UI_LOCALES)
    else:
        marker = b'/* GRZ_FOOTER_TITLES */ {}'
        labels = dict((locale, messages[locale][folder]['footer-title']) for locale in UI_LOCALES)
    if source.count(marker) != 1:
        raise ValueError('Expected one UI translation token in ' + filename)
    return source.replace(marker, json.dumps(labels, ensure_ascii=True, sort_keys=True))


def tier_catalog():
    vehicles = json.loads(read(os.path.join(ROOT, 'tier_xi_profiles.json')).decode('utf-8'))
    known_ids = set()
    for vehicle in vehicles:
        identifier = vehicle['id']
        if (identifier in known_ids or not re.match(r'xi_[a-z0-9_]+\Z', identifier) or
                vehicle['coverage'] not in ('native', 'partial', 'separate', 'standard') or
                not all(vehicle[key] for key in ('label', 'profile', 'detail_pl', 'detail_en'))):
            raise ValueError('Invalid Tier XI profile: ' + identifier)
        known_ids.add(identifier)
    return sorted(vehicles, key=lambda vehicle: vehicle['label'].lower())


def build_decoration_host():
    sys.path.insert(0, os.path.join(ROOT, 'native'))
    try:
        import patch_decoration_host as legacy_host
        from patch_decoration_ancestry import patch_ancestry
        from patch_decoration_samples import patch_samples
    finally:
        del sys.path[0]
    return patch_samples(patch_ancestry(legacy_host.patch(read(legacy_host.REFERENCE))))


def battle_panel_catalog(vehicles):
    path = os.path.join(ROOT, 'native', 'battle_panel_profiles.json')
    catalog = json.loads(read(path).decode('utf-8'))
    if catalog.get('version') != 1 or set(catalog['vehicles']) != set(v['id'] for v in vehicles):
        raise ValueError('Battle-panel catalogue does not cover the Tier XI choices')
    panels = {}
    for key, recipe in sorted(catalog['panels'].items()):
        if not re.match(r'[a-z][a-z0-9_]*\Z', key) or recipe['layout'] not in ('center', 'left', 'right', 'info'):
            raise ValueError('Invalid battle-panel identifier or layout: ' + key)
        metadata = dict((field, recipe[field]) for field in ('stock_library', 'linkage', 'layout'))
        for geometry_field in ('offset', 'offset_by_mode', 'scale_by_mode'):
            if geometry_field in recipe:
                metadata[geometry_field] = recipe[geometry_field]
        state = recipe.get('snapshot_status', 'complete' if recipe.get('snapshot') else 'pending')
        if state not in ('complete', 'partial', 'pending'):
            raise ValueError('Unexpected battle-panel sample status: ' + key)
        metadata['sample_status'] = state
        panels[key] = metadata
    for index in (catalog['vehicles'], catalog['profiles']):
        for identifier, entries in index.items():
            if (not isinstance(entries, list) or len(set(entries)) != len(entries) or
                    not all(key in panels for key in entries)):
                raise ValueError('Invalid battle-panel assignment: ' + identifier)
    return panels, catalog['vehicles'], catalog['profiles']


def build_battle_panel_host(decoration_host, game_root):
    sys.path.insert(0, os.path.join(ROOT, 'native'))
    try:
        from generate_widget_host import build_widget_host
        return build_widget_host(decoration_host, game_root)
    finally:
        del sys.path[0]


def stable_repr(value):
    if isinstance(value, dict):
        return '{' + ', '.join('%s: %s' % (repr(key), stable_repr(value[key]))
                               for key in sorted(value)) + '}'
    if isinstance(value, list):
        return '[' + ', '.join(stable_repr(item) for item in value) + ']'
    if isinstance(value, tuple):
        suffix = ',' if len(value) == 1 else ''
        return '(' + ', '.join(stable_repr(item) for item in value) + suffix + ')'
    return repr(value)


def hud_textures():
    data = read(os.path.join(ASSETS, 'hud-textures.zip'))
    if hashlib.sha256(data).hexdigest() != HUD_TEXTURES_SHA256:
        raise ValueError('HUD textures differ from the reviewed build')
    expected = {'gear.dds', 'move.dds', 'power_off.dds', 'power_on.dds'}
    expected.update('panel_%03d.dds' % index for index in range(101))
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        if sorted(archive.namelist()) != sorted(expected):
            raise ValueError('Unexpected HUD textures')
        return [(name, archive.read(name)) for name in sorted(expected)]


def build_mod(folder, new, output, scenes, focus_layouts, vehicles, hosts, battle_panels, messages):
    old, title = SOURCES[folder]
    namespace = 'grz_' + folder
    source_root = os.path.join(REPO, 'mods', folder, 'src')
    filename = 'com.grz.%s_%s.wotmod' % (folder, new)
    target = os.path.join(output, filename)
    old_resource, new_resource = 'v' + old.replace('.', '_'), 'v' + new.replace('.', '_')
    ui_prefix = 'res/gui/gameface/mods/%s/%s/' % (namespace, new_resource)
    with zipfile.ZipFile(target, 'w') as archive:
        files = []
        for base, dirs, names in os.walk(os.path.join(source_root, 'res')):
            dirs[:] = sorted(d for d in dirs if d != '__pycache__')
            for name in sorted(names):
                if name.endswith(('.pyc', '.pyo')) or name == 'editor_battle.jpg':
                    continue
                files.append(os.path.join(base, name))
        files.append(os.path.join(source_root, 'meta.xml'))
        for path in sorted(files):
            relative = os.path.relpath(path, source_root).replace('\\', '/')
            packaged = relative.replace(old_resource, new_resource)
            data = read(path)
            if path.endswith(('.py', '.html', '.js', '.css', '.json', '.xml')):
                data = data.replace(b'\r\n', b'\n').replace(old_resource, new_resource).replace(old, new)
            if packaged in (ui_prefix + 'settings.js', ui_prefix + 'footer.js'):
                data = localize_ui(data, os.path.basename(packaged), folder, messages)
            if path.endswith('.py'):
                data = compile27(data, packaged)
                packaged += 'c'
            put(archive, packaged, data)
        maps = 'res/gui/maps/' + namespace + '/' + new_resource + '/'
        for name, data in hud_textures():
            put(archive, maps + name, data)
        put(archive, ui_prefix + 'preview_scenes.js',
            'window.GRZPreviewScenes = ' + json.dumps(scenes, ensure_ascii=True, sort_keys=True) + ';\n')
        geometry = {}
        for scene in SCENES:
            geometry[scene] = [dict((key, frame[key]) for key in
                                   ('step', 'zoom', 'marker_scale', 'ellipse', 'frame_size', 'points',
                                    'calibrated', 'focus_unmeasured')
                                   if key in frame) for frame in scenes['scenes'][scene]['frames']]
            for frame in geometry[scene]:
                step = frame['step']
                frame.setdefault('frame_size', [1920, 1080])
                frame.setdefault('points', None)
                if (scene, step) in focus_layouts:
                    frame['focus_points'] = focus_layouts[(scene, step)]
        generated = '# -*- coding: ascii -*-\nSCENE_FRAMES = ' + stable_repr(geometry) + '\n'
        geometry_name = 'res/scripts/client/%s/scene_frames_data.py' % namespace
        put(archive, geometry_name + 'c', compile27(generated, geometry_name))
        vehicle_name = 'res/scripts/client/%s/tier_xi_data.py' % namespace
        vehicle_data = '# -*- coding: ascii -*-\nTIER_XI = ' + stable_repr(vehicles) + '\n'
        put(archive, vehicle_name + 'c', compile27(vehicle_data, vehicle_name))
        panel_data = ('# -*- coding: ascii -*-\nPANELS, VEHICLE_PANELS, PROFILE_PANELS = ' +
                      stable_repr(battle_panels) + '\n')
        panel_data_name = 'res/scripts/client/%s/battle_panel_data.py' % namespace
        put(archive, panel_data_name + 'c', compile27(panel_data, panel_data_name))
        for shared in ('battle_panel_preview.py', 'preview_translations.py'):
            shared_name = 'res/scripts/client/%s/%s' % (namespace, shared)
            put(archive, shared_name + 'c', compile27(read(os.path.join(ROOT, shared)), shared_name))
        flash = 'res/gui/flash/grz' + title
        put(archive, flash + 'ReticleDecorPreview_' + new_resource + '.swf', hosts['reticle_decor.swf'])
        put(archive, flash + 'BattleMechanicsPreview_' + new_resource + '.swf', hosts['battle_mechanics.swf'])
        for scene in SCENES:
            for frame in scenes['scenes'][scene]['frames']:
                if not frame.get('src'):
                    continue
                expected = scene_resource(scene, frame['step'])
                if frame['src'] != expected:
                    raise ValueError('Unexpected asset resource name')
                data = read(os.path.join(ASSETS, expected))
                put(archive, ui_prefix + expected, data)
    return {'file': filename, 'entries': len(archive.namelist()),
            'sha256': hashlib.sha256(read(target)).hexdigest(), 'bytes': os.path.getsize(target)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mod', choices=sorted(SOURCES))
    parser.add_argument('--version')
    parser.add_argument('--output')
    parser.add_argument('--game-root', help='Optional local WoT client for rebuilding and checking the owned Flash hosts')
    args = parser.parse_args()
    module = os.path.join(REPO, 'mods', args.mod)
    baseline = read(os.path.join(module, 'VERSION')).strip()
    version = args.version or baseline
    if not (re.match(SEMVER, baseline) and re.match(SEMVER, version)):
        parser.error('Expected a three-part version')
    parsed_version = tuple(map(int, version.split('.')))
    parsed_baseline = tuple(map(int, baseline.split('.')))
    if parsed_version[:2] != parsed_baseline[:2] or parsed_version < parsed_baseline:
        parser.error('Release must be in the current series and at least the reviewed baseline')
    output = args.output or os.path.join(module, 'dist')
    if not os.path.isdir(output):
        os.makedirs(output)

    scenes = catalog()
    counts = dict((scene, sum(bool(frame['src']) for frame in data['frames']))
                  for scene, data in scenes['scenes'].items())
    if counts != {'arcade': 5, 'sniper': 5, 'arty_top': 5, 'arty_trajectory': 1}:
        raise ValueError('Incomplete set of reviewed preview scenes')
    focus = artillery_focus_catalog(scenes)
    for scene in ('arty_top', 'arty_trajectory'):
        for frame in scenes['scenes'][scene]['frames']:
            if (scene, frame['step']) not in focus:
                raise ValueError('Artillery spread must be attached to the reviewed frame')
            frame['focus_unmeasured'] = False

    hosts = dict((name, read(os.path.join(ASSETS, name))) for name in HOSTS)
    for name, value in hosts.items():
        if hashlib.sha256(value).hexdigest() != HOSTS[name]:
            raise ValueError('Owned Flash host differs from the reviewed build: ' + name)
    if args.game_root:
        decoration = build_decoration_host()
        if decoration != hosts['reticle_decor.swf']:
            raise ValueError('Rebuilt decoration host differs from reviewed asset')
        if build_battle_panel_host(decoration, args.game_root) != hosts['battle_mechanics.swf']:
            raise ValueError('Rebuilt mechanics host differs from reviewed asset')

    vehicles = tier_catalog()
    result = build_mod(args.mod, version, output, scenes, focus, vehicles, hosts,
                       battle_panel_catalog(vehicles), ui_strings())
    with open(os.path.join(output, 'SHA256SUMS.txt'), 'wb') as stream:
        stream.write('%s  %s\n' % (result['sha256'], result['file']))
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    main()
