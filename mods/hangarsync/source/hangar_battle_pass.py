# -*- coding: utf-8 -*-
"""Bounded, read-only Battle Pass snapshot from the running client's controller.

Season and chapter identifiers, costs and dates come from server configuration.
This module keeps no player history and never activates or purchases anything.
"""
from __future__ import absolute_import, unicode_literals

import itertools
import re

try:
    _INTS = (int, long)
except NameError:
    _INTS = (int,)
try:
    _TEXT = (str, unicode)
except NameError:
    _TEXT = (str,)

_UNSET = object()
MAX_CHAPTERS = 256
MAX_LEVELS = 10000
_MAX_COUNT = 1000000000000


def _empty(status):
    return {'schemaVersion': 1, 'status': status, 'season': None,
            'activeChapterId': None, 'chapters': []}


def _int(value, positive=False, maximum=_MAX_COUNT):
    if type(value) in _INTS and (1 if positive else 0) <= value <= maximum:
        return value
    return None


def _epoch(value):
    return _int(value, positive=True, maximum=253402300799)


def _bool(value):
    return value if type(value) is bool else None


def _read(obj, name, *args):
    try:
        return getattr(obj, name)(*args)
    except Exception:
        return None


def _bounded_ids(value):
    if value is None or isinstance(value, _TEXT):
        return None
    try:
        values = list(itertools.islice(iter(value), MAX_CHAPTERS + 1))
    except Exception:
        return None
    if len(values) > MAX_CHAPTERS:
        return None
    if any(_int(x, positive=True) is None for x in values):
        return None
    return sorted(set(values))


def _levels(value):
    if value is None or isinstance(value, _TEXT):
        return None
    try:
        values = list(itertools.islice(iter(value), MAX_LEVELS + 1))
    except Exception:
        return None
    if not values or len(values) > MAX_LEVELS:
        return None
    if any(_int(x, positive=True) is None for x in values):
        return None
    if any(a >= b for a, b in zip(values, values[1:])):
        return None
    return values


def _localized_name(chapter_id, localize):
    key = '#battle_pass:chapter/fullName/%s' % chapter_id
    try:
        name = localize(key)
        if not isinstance(name, _TEXT + (bytes,)) or len(name) > 960:
            return None
        if isinstance(name, bytes):
            name = name.decode('utf-8')
        if not isinstance(name, _TEXT) or not name.strip() or len(name) > 240:
            return None
        if name == key or 'chapter/fullName/' in name or name.startswith('#'):
            return None
        return re.sub(r'[\x00-\x1f\x7f]', '', re.sub(r'<[^>]*>', '', name)).strip() or None
    except Exception:
        return None


def _game_sources():
    from helpers import dependency, i18n
    from skeletons.gui.game_control import IBattlePassController
    from skeletons.gui.lobby_context import ILobbyContext
    from skeletons.gui.shared import IItemsCache
    items = dependency.instance(IItemsCache)
    if items is None or not items.isSynced():
        return None, None, None
    controller = dependency.instance(IBattlePassController)
    lobby = dependency.instance(ILobbyContext)
    config = lobby.getServerSettings().getBattlePassConfig() if lobby else None
    return controller, config, i18n.makeString


def _chapter(controller, config, chapter_id, active_id, season, localize):
    post_id = _read(controller, 'getPostProgressionChapterID')
    extra = _bool(_read(controller, 'isExtraChapter', chapter_id))
    kind = ('post_progression' if post_id == chapter_id else
            'extra' if extra is True else 'regular' if extra is False else 'unknown')
    count = _int(_read(controller, 'getLevelInChapter', chapter_id))
    total = _int(_read(controller, 'getMaxLevelInChapter', chapter_id), positive=True)
    points = _int(_read(controller, 'getPointsInChapter', chapter_id))
    levels = _levels(_read(controller, 'getLevelsConfig', chapter_id))
    maximum = levels[-1] if levels else None
    completed = _bool(_read(controller, 'isChapterCompleted', chapter_id))
    improved = _bool(_read(controller, 'isBought', chapter_id))
    within, cost = None, None
    progression = _read(controller, 'getLevelProgression', chapter_id)
    if isinstance(progression, (tuple, list)) and len(progression) == 2:
        within, cost = _int(progression[0]), _int(progression[1], positive=True)
    # Derive from actual cumulative thresholds when the convenience API is absent.
    if (within is None or cost is None) and levels and count is not None and points is not None:
        index = count % len(levels) if kind == 'post_progression' else count
        if kind != 'post_progression' and index >= len(levels):
            cost = levels[-1] - (levels[-2] if len(levels) > 1 else 0)
            within = cost
        else:
            base = levels[index - 1] if index else 0
            cost = levels[index] - base
            within = (points % levels[-1] if kind == 'post_progression' else points) - base
            within = _int(within)
    if within is not None and cost is not None and within > cost:
        within = None
    if kind == 'post_progression':
        # The client uses a large sentinel ceiling for repeatable progression.
        # Do not present that implementation limit as a real completion target.
        total, maximum, completed = None, None, None
    elif points is not None and maximum is not None and points > maximum:
        points = None
    if count is not None and total is not None and count > total:
        count = None
    if total is not None and levels is not None and total != len(levels):
        total, maximum = None, None
    expires = _epoch(_read(config, 'getChapterExpireTimestamp', chapter_id))
    if expires is None:
        expires = _epoch(_read(controller, 'getChapterExpiration', chapter_id))
    expires = expires or season['endsAt']
    row = {'id': str(chapter_id), 'name': _localized_name(chapter_id, localize),
           'kind': kind, 'completedStages': count, 'totalStages': total,
           'pointsInStage': within, 'pointsToStage': cost, 'totalPoints': points,
           'maxPoints': maximum, 'startsAt': None, 'endsAt': expires,
           'active': active_id == chapter_id if active_id is not None else None,
           'completed': completed, 'improved': improved}
    required = ('completedStages', 'pointsInStage', 'pointsToStage', 'totalPoints', 'improved')
    if kind != 'post_progression':
        required += ('totalStages', 'maxPoints', 'completed')
    partial = kind == 'unknown' or any(row[key] is None for key in required)
    return row, partial


def collect_battle_pass(controller=_UNSET, config=None, localize=None):
    """Return allowlisted current-season data; previous-season history is not guessed.

    Explicit dependencies allow tests without importing any game modules. Missing
    client APIs produce a partial/unavailable result instead of invented zeros.
    """
    if controller is _UNSET:
        try:
            controller, config, localize = _game_sources()
        except ImportError:
            return _empty('unavailable')
        except Exception:
            return _empty('pending')
        if controller is None:
            return _empty('pending')
    if controller is None:
        return _empty('unavailable')
    localize = localize or (lambda key: key)
    season_id = _int(_read(controller, 'getSeasonID'), positive=True)
    enabled = _bool(_read(controller, 'isEnabled'))
    if season_id is None:
        return _empty('inactive' if enabled is False else 'pending')
    # Configuration can arrive before account data during login/season rollover.
    try:
        configured_id = getattr(config, 'seasonID', None)
    except Exception:
        return _empty('pending')
    if configured_id is not None and configured_id != season_id:
        return _empty('pending')
    season = {'id': str(season_id), 'number': _int(_read(controller, 'getSeasonNum'), positive=True),
              'startsAt': _epoch(_read(controller, 'getSeasonStartTime')),
              'endsAt': _epoch(_read(controller, 'getSeasonFinishTime'))}
    if (season['startsAt'] is not None and season['endsAt'] is not None and
            season['startsAt'] >= season['endsAt']):
        season['startsAt'], season['endsAt'] = None, None
    # Configuration includes expired extra chapters; controller.getChapterIDs()
    # intentionally hides those from navigation and is only the fallback.
    ids = _bounded_ids(_read(config, 'getChapterIDs'))
    used_fallback = ids is None
    if ids is None:
        ids = _bounded_ids(_read(controller, 'getChapterIDs'))
    if ids is None:
        result = _empty('partial')
        result['season'] = season
        return result
    active_id = _int(_read(controller, 'getCurrentChapterID'))
    if active_id is not None and active_id != 0 and active_id not in ids:
        # An inconsistent rollover must not join data from two seasons.
        return _empty('pending')
    active = _bool(_read(controller, 'isActive'))
    result = _empty('ok')
    result['season'] = season
    result['activeChapterId'] = str(active_id) if active_id else None
    partial = (used_fallback or active_id is None or active is None or enabled is None or
               any(value is None for value in season.values()))
    for chapter_id in ids:
        try:
            row, incomplete = _chapter(controller, config, chapter_id, active_id, season, localize)
            result['chapters'].append(row)
            partial = partial or incomplete
        except Exception:
            partial = True
    if enabled is False or active is False:
        result['status'] = 'inactive'
    elif partial:
        result['status'] = 'partial'
    return result
