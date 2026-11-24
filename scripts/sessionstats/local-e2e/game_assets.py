"""Read public appearance resources from a local WoT installation."""

from collections import defaultdict
from hashlib import sha256
from io import BytesIO
from pathlib import Path
import re
from zipfile import ZipFile


ICON_ROOT = 'gui/maps/icons/'
FONTS = {'regular': 'gui/gameface/fonts/Warhelios-Regular.ttf',
         'bold': 'gui/gameface/fonts/Warhelios-Bold.ttf'}
VEHICLE = re.compile(r'vehicle/local-([0-9]+)\.png')
MAP = re.compile(r'map/(small/|screen/)?local_map_([0-9]+)\.png')
VEHICLE_ART = re.compile(r'gui/maps/icons/vehicle/(?:small/)?[a-z]+-[a-z0-9_-]+\.png', re.I)
MAP_DIRECTORY = ICON_ROOT + 'map/small/'


def overlay_game_assets(client, scratch, assets):
    """Map fictional fixture IDs to stock artwork independently of history."""
    packages = client / 'res' / 'packages'
    index = {}
    for archive in sorted(packages.glob('gui-part*.pkg')):
        with ZipFile(archive) as package:
            for name in package.namelist():
                if (name.startswith(ICON_ROOT) or name in FONTS.values()) and not name.endswith('/'):
                    index.setdefault(name.lower(), (archive, name))
    if any(name.lower() not in index for name in FONTS.values()):
        raise ValueError('Both Warhelios fonts are required in the local WoT packages')
    vehicles = sorted(name for name in index if VEHICLE_ART.fullmatch(name) and '/small/' not in name)
    if not vehicles:
        vehicles = sorted(name for name in index if VEHICLE_ART.fullmatch(name))
    maps = sorted(name[len(MAP_DIRECTORY):-4] for name in index
                  if name.startswith(MAP_DIRECTORY) and name.endswith('.png'))
    if not vehicles or not maps:
        raise ValueError('No stock vehicle or map art was found in the local WoT packages')

    selected = defaultdict(list)
    for weight, name in FONTS.items():
        selected[name.lower()].append(('fonts', weight))
    for key in assets['images']:
        stem = key.removeprefix('img://' + ICON_ROOT)
        vehicle, map_view = VEHICLE.fullmatch(stem), MAP.fullmatch(stem)
        if vehicle:
            name = vehicles[int(vehicle[1]) % len(vehicles)]
        elif map_view:
            geometry = maps[(int(map_view[2]) - 1) % len(maps)]
            thumbnail = MAP_DIRECTORY + geometry + '.png'
            name = ICON_ROOT + 'map/screen/' + geometry + '.dds' if map_view[1] == 'screen/' else thumbnail
            if name not in index:
                name = thumbnail
        else:
            name = (ICON_ROOT + stem).lower()
        if name in index:
            selected[name].append(('images', key))

    by_archive = defaultdict(list)
    for name, targets in selected.items():
        archive, entry = index[name]
        by_archive[archive].append((entry, targets))
    for archive, files in by_archive.items():
        with ZipFile(archive) as package:
            for entry, targets in files:
                extension = Path(entry).suffix.lower()
                digest = sha256(entry.encode('utf-8')).hexdigest()[:16]
                relative = f'assets/wot-{digest}{".png" if extension == ".dds" else extension}'
                target = scratch / relative
                data = package.read(entry)
                if extension == '.dds':
                    try:
                        from PIL import Image
                    except ImportError as error:
                        raise ValueError('Install Pillow for local WoT map images') from error
                    with Image.open(BytesIO(data)) as image:
                        image.thumbnail((640, 360))
                        image.save(target, 'PNG')
                else:
                    target.write_bytes(data)
                for category, key in targets:
                    assets[category][key] = relative
