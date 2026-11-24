# -*- coding: ascii -*-
"""Finite metadata for the original client crosshair renderer families.

The marker factory, clip-reloading constants, crosshair mechanic plugins and
decorative panel define these native combinations. Artillery has its own stock
marker; the special arcade/sniper marker and decoration layouts are not
invented for it. Selection affects editor previews, never live gun mechanics.
"""
from __future__ import absolute_import

try:
    from . import preview_translations as translations
except ImportError:
    # The build embeds this shared source in each mod's namespace.
    import preview_translations as translations

try:
    _TEXT = (str, unicode)
except NameError:
    _TEXT = (str,)

_ALL = ('arcade', 'sniper', 'arty')
_DIRECT = ('arcade', 'sniper')

# id, English label, Polish label, native camera modes, marker family,
# CLIP_RELOADING_TYPES value, DECORATIVE_CROSSHAIR_CONSTS value.
_ROWS = (
    ('standard', 'Standard gun', u'Zwyk\u0142e dzia\u0142o', _ALL, 'standard', 0, None),
    ('cassette', 'Autoloader magazine', u'Magazynek automatyczny', _ALL, 'standard', 0, None),
    ('forced_reload', 'Forced magazine reload', u'Wymuszone prze\u0142adowanie magazynka', _ALL, 'standard', 0, None),
    ('autoreloader', 'Autoreloader', u'Automatyczne do\u0142adowanie', _ALL, 'standard', 1, None),
    ('extra_shot', 'Reserve-shell autoreloader', u'Do\u0142adowanie z pociskiem rezerwowym', _ALL, 'standard', 2, None),
    ('controllable_reload', 'Controlled reload', u'Kontrolowane prze\u0142adowanie', _ALL, 'standard', 3, None),
    ('unlimited', 'Unlimited magazine', u'Nieograniczony magazynek', _ALL, 'standard', 4, None),
    ('shell_calibration', 'Shell calibration', u'Kalibracja pocisku', _ALL, 'standard', 5, None),
    ('dualgun', 'Double-barrel gun', u'Podw\u00f3jna lufa', _DIRECT, 'dualgun', 0, None),
    ('twingun', 'Twin guns / salvo', u'Podw\u00f3jne dzia\u0142a / salwa', _DIRECT, 'twingun', 0, None),
    ('dual_accuracy', 'Dual accuracy', u'Dwa poziomy celno\u015bci', _DIRECT, 'dual_accuracy', 0, None),
    ('accuracy_stacks', 'Accuracy stacks', u'Poziomy celno\u015bci', _DIRECT, 'accuracy_stacks', 0, 'accuracy'),
    ('charge_shot', 'Charged shot', u'\u0141adowany strza\u0142', _DIRECT, 'charge_shot', 0, None),
    ('low_charge_shot', 'Partial-reload shot', u'Strza\u0142 przy cz\u0119\u015bciowym prze\u0142adowaniu', _DIRECT, 'low_charge_shot', 0, None),
    ('auxiliary_rocket_launcher', 'Auxiliary rocket launcher', u'Dodatkowa wyrzutnia rakiet', _DIRECT, 'auxiliary_rocket_launcher', 0, None),
    ('autoreloader_surge', 'Autoreloader surge', u'Przyspieszone do\u0142adowanie', _DIRECT, 'standard', 1, 'autoreloaderSurge'),
    ('battle_fury', 'Battle fury', u'Bojowa furia', _DIRECT, 'standard', 0, 'fury'),
    ('chargeable_burst', 'Chargeable burst', u'\u0141adowana seria', _DIRECT, 'standard', 0, None),
    ('heating_zones_gun', 'Gun heating zones', u'Strefy nagrzania dzia\u0142a', _DIRECT, 'standard', 0, None),
    ('overheat_stacks', 'Overheat stacks', u'Poziomy przegrzania', _DIRECT, 'standard', 0, 'overheat'),
    ('pillbox_siege', 'Pillbox siege mode', u'Tryb obl\u0119\u017cniczy bunkra', _DIRECT, 'standard', 0, 'pillboxSiege'),
    ('propellant_gun', 'Propellant gun', u'Dzia\u0142o z dodatkowym \u0142adunkiem', _DIRECT, 'standard', 0, None),
    ('stance_dance', 'Combat stance / reload boost', u'Tryb bojowy / szybsze prze\u0142adowanie', _DIRECT, 'standard', 0, None),
    ('stationary_reload', 'Stationary reload', u'Prze\u0142adowanie na postoju', _DIRECT, 'standard', 3, None),
    ('concentration', 'Concentration', u'Koncentracja', _DIRECT, 'standard', 0, 'concentration'),
    ('overheat', 'Gun overheat', u'Przegrzanie dzia\u0142a', _DIRECT, 'standard', 0, 'temperatureGunOverheat'),
    ('temperature_autocannon', 'Overheating autocannon',
     u'Automatyczne dzia\u0142o z przegrzewaniem', _DIRECT, 'standard', 0, 'temperatureGunOverheat'),
    ('bustle_feed', 'Bustle feed reload',
     u'Prze\u0142adowanie po strzale z zewn\u0119trznego podajnika', _DIRECT, 'standard', 0, None),
)
_FIELDS = ('id', 'label_en', 'label_pl', 'modes', 'marker', 'reload_type', 'decoration')
PROFILES = tuple(dict(zip(_FIELDS, row)) for row in _ROWS)
# Detached from the public presentation records so callers cannot modify the
# validation whitelist by editing a returned record or PROFILES entry.
_INDEX = dict((row[0], dict(zip(_FIELDS, row))) for row in _ROWS)

try:
    from .tier_xi_data import TIER_XI
except ImportError:
    TIER_XI = ()
_BY_VEHICLE = dict((vehicle['id'], vehicle) for vehicle in TIER_XI)

try:
    from .battle_panel_data import PANELS, VEHICLE_PANELS, PROFILE_PANELS
except ImportError:
    PANELS, VEHICLE_PANELS, PROFILE_PANELS = {}, {}, {}


def _battle_panel_recipe(key, mode):
    metadata = PANELS[key]
    return {
        'stock_library': metadata['stock_library'], 'linkage': metadata['linkage'],
        'layout': metadata['layout'], 'sample_status': metadata['sample_status'],
        'offset': tuple(metadata.get('offset_by_mode', {}).get(mode, metadata.get('offset', (0, 0)))),
        'scale': metadata.get('scale_by_mode', {}).get(mode, 1.0),
    }


def profile(identifier, mode):
    """Return owned primitive metadata for an exact supported pair, or None."""
    if type(identifier) not in _TEXT or type(mode) not in _TEXT:
        return None
    vehicle = _BY_VEHICLE.get(identifier)
    if vehicle is not None and mode not in _DIRECT:
        return None
    selected = _INDEX.get(vehicle['profile'] if vehicle is not None else identifier)
    if selected is None or mode not in selected['modes']:
        return None
    result = dict(selected)
    if vehicle is not None and vehicle.get('capacity'):
        result['capacity'] = vehicle['capacity']
    recipes = (VEHICLE_PANELS if vehicle is not None else PROFILE_PANELS).get(identifier, ())
    if recipes:
        result['battle_panels'] = tuple((key, _battle_panel_recipe(key, mode)) for key in recipes)
    return result


def choices(language='en'):
    """Return detached localized chooser records, using English by default."""
    locale = translations.language_code(language)
    mechanics = [{'id': row['id'], 'label': translations.mechanic_label(row, locale), 'modes': row['modes'],
                  'battle_panel_count': len(PROFILE_PANELS.get(row['id'], ()))}
                 for row in (_INDEX[entry[0]] for entry in _ROWS)]
    vehicles = [{'id': vehicle['id'], 'label': vehicle['label'], 'modes': _DIRECT,
                 'tier': 11, 'coverage': vehicle['coverage'], 'note': translations.vehicle_note(vehicle, locale),
                 'battle_panel_count': len(VEHICLE_PANELS.get(vehicle['id'], ()))}
                for vehicle in TIER_XI if vehicle['profile'] in _INDEX]
    return mechanics + vehicles
