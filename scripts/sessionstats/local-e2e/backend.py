"""Offline command bridge for the shipped Session Stats view."""

import argparse
import json
import os
from pathlib import Path
import random
import re
import struct
import sys
from tempfile import TemporaryDirectory
from datetime import datetime, time as midnight, timedelta
from zoneinfo import ZoneInfo
import zlib

from history_profile import load_profile


ROOT = Path(__file__).resolve().parent.parent
GROUPS = ('vehicles', 'maps', 'tiers', 'battles')
METRICS = ('xp_base', 'xp_received', 'credits_income_base', 'credits_income_received',
           'credits_net_base', 'credits_net_received', 'credits_costs', 'battle_wn8',
           'win_rate', 'battles')
ORDER_FIELDS = ('metric', 'statistic', 'direction', 'chronology')
TIMEZONE = 'Europe/Warsaw'
PAGE = re.compile(r'[0-9]{1,8}\Z')
DAY = 86400
REFERENCE_TIME = datetime(2026, 11, 20, 12, tzinfo=ZoneInfo(TIMEZONE)).timestamp()
VEHICLE_CLASSES = ('lightTank', 'mediumTank', 'heavyTank', 'AT_SPG', 'SPG')
PROFILE_SETTINGS = {
    'completion': {'low': .70, 'middle': .83, 'high': .96},
    'wins': {'low': .35, 'middle': .50, 'high': .65},
    'base_credits': {'low': .08, 'middle': .50, 'high': .80},
    'base_xp': {'low': .65, 'middle': 1, 'high': 1.35},
    'credits_income': {'low': .60, 'middle': 1, 'high': 1.55},
    'credits_costs': {'low': .50, 'middle': 1, 'high': 1.55},
}


def example_details(i):
    return {'pass_points': {'battle': 6 + i % 3, 'missions': 8, 'credited': 14 + i % 3}, 'missions': {
        'local:daily': {'kind': 'daily', 'status': 'completed', 'name': 'Daily practice'},
        'local:unnamed': {'kind': 'personal', 'status': 'completed'},
        'local:weekly': {'kind': 'weekly', 'status': 'progress', 'name': 'Weekly practice',
                         'objectives': [{'key': 'battlesCount', 'unit': 'battles',
                                         'before': i % 4, 'after': 1 + i % 4, 'target': 8, 'delta': 1}]}},
            'bonuses': {'eventCredits': 15000, 'eventXP': 320}}


def example_battles(sunday, launch, previous, manual, manual_previous, profile=None):
    # The generator knows only broad bands. Its calendar, identifiers, names,
    # row count and pseudorandom stream are independent of the input history.
    settings = {metric: PROFILE_SETTINGS[metric][level] for metric, level in profile.items()} if profile else None
    generator = random.Random(20261120)
    for i in range(344):
        recent = i >= 291
        if not recent:
            started = sunday - 14 * DAY + i * 3600
        elif i < 318:
            started = sunday + (i - 291) * 1200
        elif i < 335:
            started = sunday + DAY + (i - 318) * 1550
        else:
            started = sunday + 4 * DAY + 14 * 3600 + (i - 335) * 400
        # Dense histories for expansion, with enough distinct maps and tanks
        # elsewhere to verify native forward/backward pagination.
        vehicle = 1 if i % 4 == 0 else 2 + i % 57
        map_number = 1 if i % 3 == 0 else 2 + i % 45
        pending = i >= 341 or (not recent and i > 0 and i % 29 == 0)
        outcome = 'draw' if i % 13 == 0 else 'win' if i % 2 == 0 else 'loss'
        costs = 41000 + i % 21 * 975
        income = 84000 + i % 17 * 6310
        known_base = recent or i % 15 == 1
        xp = 71 + i * 223 % 1603
        if settings:
            completion_roll, win_roll, credit_roll = (generator.random() for _ in range(3))
            if not recent and i != 2:
                pending = completion_roll >= settings['completion']
            if outcome != 'draw':
                outcome = 'win' if win_roll < settings['wins'] else 'loss'
            known_base = recent or credit_roll < settings['base_credits']
            costs = round(costs * settings['credits_costs'])
            income = round(income * settings['credits_income'])
            xp = round(xp * settings['base_xp'])
        base = (0 if i % 19 == 0 else 44000 + i % 20 * 8500) if known_base else None
        vehicle_name = ('Training vehicle ' if vehicle % 5 else 'Long experimental training vehicle ') + str(vehicle)
        row = {'arena_id': f'local-battle-{i:03}', 'started_at': started, 'mode': 'random',
               'vehicle_id': vehicle, 'vehicle_name': vehicle_name, 'vehicle_tier': 1 + vehicle % 11,
               'vehicle_type': VEHICLE_CLASSES[vehicle % len(VEHICLE_CLASSES)],
               'map_id': f'local_map_{map_number:02}', 'map_name': f'Training grounds {map_number:02}',
               '_manual_id': manual if recent else manual_previous, '_launch_id': launch if recent else previous,
               '_updated_at': started + 411, 'revision': 1, '_result_seen': not pending, 'complete': not pending}
        if not pending:
            row.update(ended_at=started + 400, outcome=outcome, damage=140 + i * 287 % 7920, frags=i % 5,
                       spots=i % 7, defense=i % 4, xp_base=xp,
                       xp_received=(20000 if settings else 13590) if i == 2 else xp * (1 + i % 7),
                       free_xp=6 + i * 37 % 810,
                       currencies={'credits': {'income': income, 'costs': costs, 'net': income - costs,
                                               'income_base': base, 'net_base': base - costs if base is not None else None},
                                   'bonds': {'income': i % 35, 'costs': 0, 'net': i % 35}},
                       details=example_details(i))
        yield row


def example_service(service_class, clean_record, directory, *, installation=False, profile=None):
    sunday = datetime(2026, 11, 15, tzinfo=ZoneInfo(TIMEZONE)).timestamp()
    first, split = sunday - 14 * DAY, sunday - 1800
    expected = {'header': {'version': 'example', 'source': 'synthetic'}, 'data': [
        {'IDNum': vehicle, 'expDamage': 1100 + vehicle * 13, 'expFrag': 1.0, 'expSpot': 1.5,
         'expDef': 0.8, 'expWinRate': 51} for vehicle in range(1, 59)]}
    launch, previous = 'synthetic-current', 'synthetic-previous'
    account = 'SYNTHETIC:installation' if installation else 'SYNTHETIC:local-e2e'
    service = service_class(str(directory), account, launch, expected,
                            now=lambda: REFERENCE_TIME, started_at=split, timeline_enabled=not installation)
    if not service.ready:
        raise RuntimeError('Could not initialize an isolated statistics service.')
    state = service._state
    manual, manual_previous = state['current_manual_id'], 'a' * 32
    state['launch_sessions'].insert(0, {'id': previous, 'started_at': first, 'ended_at': split})
    state['manual_sessions'].insert(0, {'id': manual_previous, 'started_at': first, 'ended_at': split})
    state['time_points'] = {'b' * 32: sunday, 'c' * 32: sunday + DAY, 'd' * 32: sunday + 3 * DAY}
    state['time_point_names'] = {'b' * 32: 'Practice week', 'c' * 32: 'Monday review', 'd' * 32: 'Later review'}
    state['battles'] = {}
    for row in example_battles(sunday, launch, previous, manual, manual_previous, profile):
        metadata = {key: row[key] for key in ('_manual_id', '_launch_id', '_updated_at', '_result_seen', 'revision')}
        state['battles'][row['arena_id']] = {**clean_record(row), **metadata}
    # Match the in-memory fixture pattern used by the existing core-backed
    # navigation test. All subsequent action handling uses the real service.
    service._validate_state(state)
    service.store.save(state)
    service._rebuild_indexes()
    return service


def swatch(path, palette):
    width, height = 120, 70
    rows = []
    for y in range(height):
        row = bytearray([0])
        for x in range(width):
            if y in (0, height - 1) or x in (0, width - 1):
                color = palette[2]
            elif (x + y * 2) % 45 < 13:
                color = palette[1]
            else:
                color = palette[0]
            row.extend(color)
        rows.append(row)

    def chunk(kind, data):
        return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data))

    path.write_bytes(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0)) +
                     chunk(b'IDAT', zlib.compress(b''.join(rows))) + chunk(b'IEND', b''))


class ExampleArt:
    """Original diagnostic images at resource URL shapes recognized by the UI."""

    def __init__(self, directory):
        directory.mkdir()
        self.images = {}
        palettes = {'vehicle': ((42, 72, 61), (75, 104, 80), (154, 171, 142)),
                    'map': ((28, 73, 103), (49, 99, 106), (167, 191, 167)),
                    'win': ((38, 79, 45), (66, 103, 56), (161, 192, 136)),
                    'loss': ((86, 41, 33), (132, 75, 51), (212, 166, 133)),
                    'draw': ((82, 72, 38), (124, 106, 52), (193, 178, 132)),
                    'badge': ((62, 79, 77), (92, 110, 97), (163, 193, 169))}
        for kind, palette in palettes.items():
            swatch(directory / (kind + '.png'), palette)
        for kind in ('win', 'loss', 'draw'):
            self.outcome_src(kind)
        self._source('library/alertIcon', 'badge')

    def _source(self, stem, kind):
        key = 'img://gui/maps/icons/' + stem + '.png'
        self.images[key] = 'assets/' + kind + '.png'
        return key

    def vehicle_src(self, identifier):
        return self._source('vehicle/local-' + str(identifier), 'vehicle')

    def vehicle_metadata(self, identifier):
        kind = VEHICLE_CLASSES[int(identifier) % len(VEHICLE_CLASSES)]
        asset = 'AT-SPG' if kind == 'AT_SPG' else kind
        return {'class': kind, 'tier': 1 + int(identifier) % 11,
                'class_icon': {'kind': 'vehicle_class',
                               'src': self._source('vehicleTypes/24x24_metal/' + asset, 'badge')}}

    def map_src(self, identifier):
        return self._source('map/small/' + identifier, 'map')

    def map_preview(self, identifier, mode='image'):
        directory = 'screen/' if mode == 'image' else ''
        return {'src': self._source('map/' + directory + identifier, 'map'), 'mode': mode}

    def outcome_src(self, outcome):
        name = {'win': 'Victory', 'loss': 'Defeat', 'draw': 'Draw'}[outcome]
        return self._source('library/BgBattleResultIcon' + name + '-1', outcome)


def sort_orders(group, default, valid_order):
    chronologies = ['newest', 'oldest']
    if group != 'battles':
        chronologies.extend(('first_desc', 'last_asc'))
    if group == 'tiers':
        chronologies.extend(('tier_asc', 'tier_desc'))
    for chronology in chronologies:
        yield dict(default, chronology=chronology)
    for metric in METRICS:
        single = group == 'battles' or metric in ('win_rate', 'battles')
        statistics = ('avg',) if single else ('min', 'avg', 'max', 'sum')
        for statistic in statistics:
            for direction in ('desc', 'asc'):
                order = dict(default, metric=metric, statistic=statistic, direction=direction)
                if valid_order(order, group):
                    yield order


def test_ranges(now, points, has_installation):
    timezone = ZoneInfo(TIMEZONE)
    today = datetime.fromtimestamp(now, timezone).date()
    sunday = today - timedelta(days=(today.weekday() + 1) % 7)

    def date_from_sunday(days):
        return datetime.combine(sunday + timedelta(days=days), midnight.min, timezone).timestamp()

    def timeline(identifier, lower=None, upper=None, saved=None, exhaustive=False):
        start, end = saved or ('__custom__' if lower is not None else '',
                               '__custom__' if upper is not None else '')
        return {'id': identifier, 'scope': 'timeline', 'exhaustive': exhaustive,
                'from_point': start, 'to_point': end, 'from_date': lower, 'to_date': upper}

    ranges = [timeline('history', exhaustive=True),
              timeline('since-sunday', date_from_sunday(0), exhaustive=True),
              timeline('before-sunday', upper=date_from_sunday(0)),
              timeline('recent-24h', now - 86400),
              timeline('empty-date', date_from_sunday(-3650), date_from_sunday(-3649)),
              {'id': 'launch', 'scope': 'launch', 'exhaustive': False},
              {'id': 'manual-legacy', 'scope': 'manual', 'exhaustive': False}]
    if date_from_sunday(1) <= now:
        ranges.append(timeline('sunday', date_from_sunday(0), date_from_sunday(1)))
    if date_from_sunday(2) <= now:
        ranges.append(timeline('monday', date_from_sunday(1), date_from_sunday(2)))
    if has_installation:
        ranges.append({'id': 'installation', 'scope': 'instance', 'exhaustive': False})
    # The first placeholder is “beginning / now”. Each remaining value is a
    # saved point in chronological order. Exclude zero-length date pairs.
    point_keys = [''] + [identifier for identifier, timestamp in points if timestamp <= now]
    timestamps = dict(points)
    for i, start in enumerate(point_keys):
        for j, end in enumerate(point_keys):
            if not (i or j) or (j and (i >= j or (start and timestamps[start] >= timestamps[end]))):
                continue
            ranges.append(timeline(f'point-{i:02}-{j:02}', saved=(start, end)))
    return {item['id']: item for item in ranges}


class Backend:
    def __init__(self, source, scratch, *, profile=None, game_client=None):
        sys.path.insert(0, str(source / 'src'))
        from grz_session_stats import VERSION
        from grz_session_stats.appearance import build_presentation, default_config
        from grz_session_stats.core import StatsService, _clean_record
        from grz_session_stats.date_locale import resolve_date_settings
        from grz_session_stats.localization import Localizer, SUPPORTED, message
        from grz_session_stats.projection import DEFAULT_ORDER, TIER_ORDER, valid_order
        from grz_session_stats.visuals import enrich_snapshot

        self.version = VERSION
        self.fixture = 'local-aggregate' if profile else 'synthetic'
        self.instance_label = message('scope.instance')
        self.defaults = {group: TIER_ORDER if group == 'tiers' else DEFAULT_ORDER for group in GROUPS}
        self.orders = {group: list(sort_orders(group, self.defaults[group], valid_order))
                       for group in GROUPS}
        self.enrich = enrich_snapshot
        self.asset_root = scratch
        self.serial = 0
        self.account = None
        self.language = 'en'
        self.timeline_cache = {}
        config = default_config()
        self.presentation = build_presentation(config)
        self.map_preview_mode = self.presentation.get('map_preview_mode', 'image')
        self.localizers = {language: Localizer(language, date_settings=resolve_date_settings(
            language, overrides=config['date_time'])) for language in SUPPORTED}
        self.service = example_service(StatsService, _clean_record, scratch, profile=profile)
        self.installation = example_service(StatsService, _clean_record, scratch, installation=True, profile=profile)
        self.records = dict(self.service._state['battles'])
        self.ranges = test_ranges(REFERENCE_TIME, self.service.timeline_snapshot()['time_points'], True)
        self.resolver = ExampleArt(scratch / 'assets')
        # Enrich a materialized list solely to preload artwork. The real
        # snapshots published below still come from the current Python core.
        self.enrich({'scopes': {'timeline': {'battles': [
            {'id': identifier, 'outcome': row.get('outcome')} for identifier, row in self.records.items()]}}},
            self.records, resolver=self.resolver, map_preview_mode=self.map_preview_mode)
        self.assets = {'images': self.resolver.images, 'fonts': {}}
        if game_client is not None:
            from game_assets import overlay_game_assets
            overlay_game_assets(game_client, scratch, self.assets)

    def inventory(self):
        return {'version': self.version, 'ranges': list(self.ranges.values()), 'groups': GROUPS,
                'orders': self.orders, 'languages': list(self.localizers), 'timezone': TIMEZONE,
                'assets': self.assets, 'asset_root': self.asset_root.as_posix(),
                'fixture': self.fixture, 'reference_time': REFERENCE_TIME}

    def _scope(self, name):
        if name == 'instance' and self.installation:
            return self.installation, 'manual'
        if name in ('timeline', 'launch', 'manual'):
            return self.service, name
        raise ValueError('Unknown or unavailable result scope.')

    def _timeline(self, start, end, lower=None, upper=None):
        selected = (start, end, lower, upper)
        service = self.service
        if not service.set_timeline_range(*selected):
            return False
        if service.timeline_loading and selected in self.timeline_cache:
            service._filtered_timeline = self.timeline_cache[selected]
            service._timeline_job = None
        while service.timeline_loading:
            service.advance_timeline(budget=1.0)
        index = service._view_index('timeline')
        if index is None:
            raise RuntimeError('The statistics core failed to project the selected date range.')
        if start or end:
            self.timeline_cache[selected] = index
        return True

    def setup(self, range_id, group, language):
        if range_id not in self.ranges or group not in GROUPS or language not in self.localizers:
            raise ValueError('Unknown date range, group, or UI language.')
        selected = self.ranges[range_id]
        if selected['scope'] == 'timeline' and not self._timeline(*(
                selected[key] for key in ('from_point', 'to_point', 'from_date', 'to_date'))):
            raise RuntimeError('The statistics core declined a planned date range.')
        service, scope = self._scope(selected['scope'])
        index = service._view_index(scope)
        # Playback is allowed to revisit the exact same range and size. Reset
        # view state without reopening the ledger or sharing previous details.
        for attr in ('_map_pages', '_vehicle_pages', '_history_request'):
            getattr(service, attr).pop(scope, None)
        for tab in GROUPS:
            if not service.set_order(scope, tab, self.defaults[tab], index.identifier):
                raise RuntimeError('Could not reset the sort order for ' + tab)
        self.language = language
        self.serial += 1
        self.account = f'local-e2e-{self.serial}'
        return self.snapshot()

    def snapshot(self):
        data = self.service.snapshot()
        data['account_key'] = self.account
        data['appearance'] = self.presentation
        data['scopes']['timeline'] = self.service.timeline_snapshot()
        if self.installation:
            installation = self.installation.snapshot()
            scope = installation['scopes']['manual']
            scope.update(label=self.instance_label, loading=False, load_error=None)
            data['scopes']['instance'] = scope
            data['warnings'].extend(installation.get('warnings', ()))
        data['recovery'] = {'pending': len(self.service.pending_arena_ids()), 'in_flight': 0, 'states': {}}
        self.enrich(data, self.records, resolver=self.resolver, map_preview_mode=self.map_preview_mode)
        return self.localizers[self.language].snapshot(data)

    def command(self, action):
        kind = action.get('action')
        if action.get('account_key') != self.account:
            return None
        if kind == 'language':
            language = action.get('language')
            if language not in self.localizers:
                return None
            self.language = language
        elif kind == 'timeline_range':
            dates = [float(action[key]) if action.get(key) not in (None, '') else None
                     for key in ('from_date', 'to_date')]
            if not self._timeline(action.get('from_point', ''), action.get('to_point', ''), *dates):
                return None
        elif kind == 'time_point':
            if not self.service.create_time_point(action.get('name')):
                return None
            self.timeline_cache.clear()
        elif kind == 'reset':
            service, scope = self._scope(action.get('scope') or 'manual')
            if scope != 'manual' or not service.reset_manual():
                return None
            self.timeline_cache.clear()
        elif kind in ('sort', 'page', 'map_battles', 'vehicle_battles', 'battle_select'):
            service, scope = self._scope(action.get('scope'))
            group, period = action.get('group'), action.get('period_id')
            if not period or not self._navigation(service, scope, kind, group, period, action):
                return None
        elif kind != 'refresh':
            return None  # Window/cursor events belong to the renderer adapter.
        return self.snapshot()

    @staticmethod
    def _navigation(service, scope, kind, group, period, action):
        if kind == 'sort':
            return service.set_order(scope, group, {key: action.get(key) for key in ORDER_FIELDS}, period)
        if kind == 'battle_select':
            return service.select_battle(scope, action.get('id'), period, action.get('request_id'))
        raw_page = action.get('page')
        if not isinstance(raw_page, str) or not PAGE.fullmatch(raw_page):
            return False
        page = int(raw_page)
        chronology = action.get('chronology')
        if kind == 'map_battles':
            return service.set_map_battles(scope, action.get('map_id'), page, period, chronology)
        if kind == 'vehicle_battles':
            return service.set_vehicle_battles(scope, action.get('vehicle_id'), page, period, chronology)
        return service.set_page(scope, group, page, period, action.get('request_id'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT / 'WotMods-pr17-next/mods/sessionstats')
    parser.add_argument('--profile', type=Path)
    parser.add_argument('--game-client', type=Path)
    options = parser.parse_args()
    if os.environ.get('GITHUB_ACTIONS') == 'true' and (options.profile or options.game_client):
        parser.error('Local QA inputs are not allowed in GitHub Actions.')
    try:
        profile = load_profile(options.profile) if options.profile else None
    except ValueError as error:
        parser.error(str(error))
    with TemporaryDirectory(prefix='ss-test-') as temporary:
        backend = Backend(options.source.resolve(), Path(temporary), profile=profile, game_client=options.game_client)
        for line in sys.stdin:
            identifier = None
            try:
                request = json.loads(line)
                identifier = request.get('id')
                operation = request.get('op')
                if operation == 'inventory':
                    result = backend.inventory()
                elif operation == 'setup':
                    result = backend.setup(request.get('range'), request.get('group'), request.get('language'))
                elif operation == 'command':
                    result = backend.command(request.get('action'))
                else:
                    raise ValueError('Unknown command bridge operation.')
                response = {'id': identifier, 'result': result}
                out = json.dumps(response, ensure_ascii=True, separators=(',', ':'), allow_nan=False)
            except (AttributeError, KeyError, ValueError, RuntimeError, TypeError) as error:
                out = json.dumps({'id': identifier, 'error': str(error)}, ensure_ascii=True)
            print(out, flush=True)


if __name__ == '__main__':
    main()
