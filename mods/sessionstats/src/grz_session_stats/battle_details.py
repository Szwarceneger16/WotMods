# -*- coding: utf-8 -*-
"""Extract bounded, player-only details from WoT's per-arena result."""
from __future__ import unicode_literals

import re
from copy import deepcopy

from .normalize import _integer, _number, _text, integer_types, text_type

MISSION_LIMIT = 64
MISSION_ID = re.compile(r'\A[A-Za-z0-9_:.\-]{1,96}\Z')
CRUCIBLE_ID = re.compile(r'\Achallenge:[0-9]{1,20}:([0-9]{1,6})(:fail)?\Z')
MARKUP = re.compile(r'<[^>]*>')
MISSION_KINDS = ('crucible', 'daily', 'daily_bonus', 'daily_epic', 'weekly',
                 'premium', 'personal', 'battle_matters', 'other')
MISSION_STATES = ('observed', 'progress', 'reset', 'failed', 'completed', 'honors')
PROGRESS_STATES = ('changed', 'unchanged', 'unavailable')
PROGRESS_UNITS = ('battles', 'vehicles', 'damage', 'kills', 'xp', 'seconds', 'counter')
OBJECTIVE_LIMIT = 12
POINT_FIELDS = {'battle': 'bpTopPoints', 'missions': 'eventBattlePassPoints',
                'vehicle': 'bpBonusPoints'}
BONUS_FIELDS = {
    'eventCredits': 'credits', 'eventXP': 'xp', 'eventFreeXP': 'free_xp', 'eventCrystal': 'bonds',
    'boosterCredits': 'credits', 'boosterXP': 'xp', 'boosterFreeXP': 'free_xp',
    'boosterTMenXP': 'crew_xp', 'orderCredits': 'credits', 'orderXP': 'xp',
    'orderFreeXP': 'free_xp', 'orderTMenXP': 'crew_xp',
    'wotPlusCredits': 'credits', 'wotPlusXP': 'xp', 'wotPlusFreeXP': 'free_xp',
    'wotPlusCrewXP': 'crew_xp', 'premiumVehicleXP': 'xp', 'squadXP': 'xp',
    'dailyXPFactor10': 10, 'additionalXPFactor10': 10,
    'appliedPremiumCreditsFactor100': 100, 'appliedPremiumXPFactor100': 100,
}


def _mapping(value):
    return value if isinstance(value, dict) else {}


def _label(value, length):
    if not isinstance(value, (text_type, bytes)):
        return ''
    return ' '.join(MARKUP.sub('', _text(value)[:4096]).split())[:length]


def _bounded_number(value):
    number = _number(value)
    return number if number is not None and number <= 10 ** 12 else None


def _bounded_delta(value):
    number = _number(value, nonnegative=False)
    return number if number is not None and abs(number) <= 10 ** 12 else None


def _clean_objectives(value):
    if not isinstance(value, (list, tuple)):
        return []
    result = []
    for incoming in value[:OBJECTIVE_LIMIT]:
        incoming = _mapping(incoming)
        key = _text(incoming.get('key'))
        if not MISSION_ID.match(key) or incoming.get('unit') not in PROGRESS_UNITS:
            continue
        objective = {'key': key, 'unit': incoming['unit']}
        label = _label(incoming.get('label'), 160)
        if label:
            objective['label'] = label
        for field in ('before', 'after', 'target', 'delta'):
            amount = (_bounded_delta if field == 'delta' else _bounded_number)(incoming.get(field))
            if amount is not None:
                objective[field] = amount
        if 'after' in objective or 'delta' in objective:
            result.append(objective)
    return result


def clean_details(value):
    """Use the same whitelist for intake, storage and display."""
    value = _mapping(value)
    clean = {}
    active = _text(value.get('active_crucible'))
    if CRUCIBLE_ID.match(active) and not active.endswith(':fail'):
        clean['active_crucible'] = active
    if value.get('suicide') is True:
        clean['suicide'] = True
    for section, keys in (('pass_points', tuple(POINT_FIELDS) + ('credited',)),
                          ('bonuses', BONUS_FIELDS)):
        amounts = _mapping(value.get(section))
        selected = dict((key, _bounded_number(amounts.get(key))) for key in keys)
        selected = dict((key, amount) for key, amount in selected.items() if amount is not None)
        if selected:
            clean[section] = selected
    missions = {}
    incoming = _mapping(value.get('missions'))
    # Reserve a place for the observed Crucible even when many quests report results.
    keys = [key for key in incoming if isinstance(key, text_type) and MISSION_ID.match(key)]

    def display_priority(key):
        state = _mapping(incoming[key]).get('status')
        return (-MISSION_STATES.index(state) if state in MISSION_STATES else 0, key)

    keys.sort(key=display_priority)
    if active in keys:
        keys.remove(active)
        keys.insert(0, active)
    for key in keys[:MISSION_LIMIT]:
        row = _mapping(incoming[key])
        mission = {}
        for field, size in (('name', 160), ('operation', 160), ('description', 420)):
            label = _label(row.get(field), size)
            if label:
                mission[field] = label
        for field, options in (('kind', MISSION_KINDS), ('status', MISSION_STATES),
                               ('progress_kind', ('battles', 'vehicles')),
                               ('progress_state', PROGRESS_STATES)):
            if row.get(field) in options:
                mission[field] = row[field]
        for field in ('stage', 'before', 'after'):
            amount = _bounded_number(row.get(field))
            if amount is not None:
                mission[field] = amount
        objectives = _clean_objectives(row.get('objectives'))
        if objectives:
            mission['objectives'] = objectives
        if mission:
            missions[key] = mission
    if missions:
        clean['missions'] = missions
    return clean


def merge_details(existing, incoming, revise):
    merged = dict(existing)
    for field, value in incoming.items():
        if field in ('missions', 'pass_points', 'bonuses'):
            combined = dict(existing.get(field, {}))
            for key, item in value.items():
                if field == 'missions':
                    legacy = combined.pop('pm2:' + key[len('personal:'):], {}) if key.startswith('personal:') else {}
                    legacy = dict((name, value) for name, value in legacy.items() if name != 'status')
                    row = dict(combined.get(key, legacy))
                    if item.get('objectives'):
                        objectives = dict((objective['key'], objective) for objective in row.get('objectives', ()))
                        for objective in item['objectives']:
                            known = dict(objectives.get(objective['key'], {}))
                            for name, entry in objective.items():
                                if name not in known or revise:
                                    known[name] = entry
                            objectives[objective['key']] = known
                        _set_progress(row, [objectives[name] for name in sorted(objectives)],
                                      item.get('progress_state') == 'unchanged')
                    for name, entry in item.items():
                        previous = row.get(name)
                        if name in ('objectives', 'progress_state') and row.get('objectives'):
                            continue
                        if name == 'status' and previous is not None:
                            if MISSION_STATES.index(entry) > MISSION_STATES.index(previous):
                                row[name] = entry
                        elif previous is None or revise:
                            row[name] = entry
                    combined[key] = row
                elif key not in combined or revise:
                    combined[key] = item
            merged[field] = combined
        elif field not in merged:
            merged[field] = value
    return clean_details(merged)


def _pass_points(avatar):
    points = dict((name, _bounded_number(avatar.get(field))) for name, field in POINT_FIELDS.items())
    if all(amount is not None for amount in points.values()):
        # These are the three native earning categories. Chapter and unallocated
        # deltas describe where the same points went, and must not be added here.
        points['credited'] = sum(points.values())
    else:
        unallocated = _bounded_number(avatar.get('bpNonChapterPointsDiff'))
        chapters = _mapping(avatar.get('bpChaptersInfo'))
        deltas = []
        for pair in chapters.values():
            if isinstance(pair, (list, tuple)) and len(pair) == 2:
                before, after = [_bounded_number(amount) for amount in pair]
                if before is not None and after is not None and after > before:
                    deltas.append(after - before)
        if unallocated or deltas:
            points['credited'] = (unallocated or 0) + sum(deltas)
    return points


def _set_progress(row, objectives, comparable=False):
    objectives = _clean_objectives(objectives)
    if objectives:
        row['objectives'] = objectives
    deltas = [objective.get('delta') for objective in objectives]
    if any(delta is not None and delta != 0 for delta in deltas):
        row['progress_state'] = 'changed'
        if row.get('status', 'observed') == 'observed':
            row['status'] = 'progress'
    elif comparable and deltas and all(delta == 0 for delta in deltas):
        row['progress_state'] = 'unchanged'
    else:
        row['progress_state'] = 'unavailable'


def _result_counters(previous, current):
    objectives = []
    before = _bounded_number(previous.get('battlesCount'))
    after = _bounded_number(current.get('battlesCount'))
    if before is not None and after is not None:
        objectives.append(dict(key='battlesCount', unit='battles', before=before,
                               after=after, delta=after - before))
    containers = (dict, list, tuple, set, frozenset)
    before_vehicles = previous.get('battlesUniqueVehicles')
    after_vehicles = current.get('battlesUniqueVehicles')
    if isinstance(before_vehicles, containers) and isinstance(after_vehicles, containers):
        before, after = len(before_vehicles), len(after_vehicles)
        objectives.append(dict(key='battlesUniqueVehicles', unit='vehicles',
                               before=before, after=after, delta=after - before))
    return objectives


def result_details(avatar, vehicle, active=None, mission_resolver=None):
    details = {'pass_points': _pass_points(avatar), 'bonuses': {}, 'missions': {}}
    if active:
        details['active_crucible'] = active
    for field in BONUS_FIELDS:
        amount = _bounded_number(vehicle.get(field))
        base = BONUS_FIELDS[field] if isinstance(BONUS_FIELDS[field], int) else 0
        if amount is not None and amount > base:
            details['bonuses'][field] = amount
        # Account-level event amounts and vehicle-level amounts are separate.
        if field in ('eventCredits', 'eventXP', 'eventFreeXP', 'eventCrystal'):
            account_amount = _bounded_number(avatar.get(field))
            if account_amount:
                details['bonuses'][field] = (details['bonuses'].get(field) or 0) + account_amount
    # Native FairplayViolationsInfo stores warnings, penalties and violations
    # separately. Only the violation/penalty mask is evidence of suicide.
    fairplay = avatar.get('fairplayViolations')
    if isinstance(fairplay, (list, tuple)) and len(fairplay) >= 3:
        details['suicide'] = any(isinstance(mask, integer_types) and mask >= 0 and mask & 2
                                 for mask in fairplay[1:3])

    missions = details['missions']
    progress = dict(_mapping(avatar.get('questsProgress')))
    progress.update(_mapping(vehicle.get('questsProgress')))
    for raw_id, entry in progress.items():
        quest_id = _text(raw_id)
        if not MISSION_ID.match(quest_id) or not isinstance(entry, (list, tuple)) or len(entry) != 3:
            continue
        previous, current = entry[1:]
        if not isinstance(previous, dict) or not isinstance(current, dict):
            continue
        challenge = CRUCIBLE_ID.match(quest_id)
        bonus_before = _bounded_number(previous.get('bonusCount', 0))
        bonus_after = _bounded_number(current.get('bonusCount', 0))
        complete = bonus_before is not None and bonus_after is not None and bonus_after > bonus_before
        if challenge and challenge.group(2):
            # The client reports a separate fail quest when a shield is used.
            # A merely active Crucible or an unchanged counter is not a loss.
            if complete:
                row = missions.setdefault(quest_id[:-5], {})
                if row.get('status') != 'completed':
                    row.update(kind='crucible', stage=int(challenge.group(1)), status='failed')
            continue
        row = missions.setdefault(quest_id, {})
        status = 'completed' if complete else 'observed'
        if status == 'completed' or row.get('status') != 'failed':
            row['status'] = status
        row['_result_progress'] = (entry[0], previous, current)
        # An award can reset or rebase counters for the next repetition. Only
        # the native condition knows its target and the progress earned here.
        _set_progress(row, [] if complete else _result_counters(previous, current), previous == current)
        if challenge:
            row.update(kind='crucible', stage=int(challenge.group(1)))
        if not complete:
            before = _bounded_number(previous.get('battlesCount'))
            after = _bounded_number(current.get('battlesCount'))
            if before is not None and after is not None and before != after:
                row.update(before=before, after=after)
            unique_vehicles = current.get('battlesUniqueVehicles')
            if isinstance(unique_vehicles, (dict, list, tuple, set, frozenset)):
                previous_vehicles = previous.get('battlesUniqueVehicles')
                if isinstance(previous_vehicles, (dict, list, tuple, set, frozenset)):
                    if len(previous_vehicles) != len(unique_vehicles):
                        row.update(before=len(previous_vehicles), after=len(unique_vehicles), progress_kind='vehicles')

    for owner in (avatar, vehicle):
        for mission_id, subquests in _mapping(owner.get('PM2Progress')).items():
            mission_id = _integer(mission_id)
            if mission_id is None or mission_id > 10 ** 6 or not _mapping(subquests):
                continue
            row = missions.setdefault('personal:{0}'.format(mission_id), {'kind': 'personal', 'status': 'observed',
                                                                       'progress_state': 'unavailable'})
            row['_pm_progress'] = subquests
            completed = row.setdefault('_completed_conditions', set())
            completed.update(_text(key) for key, value in subquests.items()
                             if value is True and MISSION_ID.match(_text(key)))

    if mission_resolver is not None and missions:
        mission_resolver(missions)
    return clean_details(details)


def _quest_labels(quest, row):
    name = _label(quest.getUserName(), 160)
    if name:
        row['name'] = name
    for getter in ('getConditionsDescription', 'getUserDescription', 'getDescription'):
        read = getattr(quest, getter, None)
        description = _label(read(), 420) if callable(read) else ''
        if description:
            row['description'] = description
            break


def _objective_unit(key, condition=None):
    key = key[5:] if key.startswith('unit_') else key
    if key == 'battlesCount':
        return 'battles'
    if key in ('vehicleKills', 'kills'):
        return 'kills'
    if key in ('xp', 'originalXP'):
        return 'xp'
    if key in ('vehicleDamage', 'vehicleStun'):
        event_count = getattr(condition, 'isEventCount', None)
        if not callable(event_count) or event_count():
            return 'counter'
        return 'damage' if key == 'vehicleDamage' else 'seconds'
    if key in ('damageDealt', 'damageAssistedRadio', 'damageAssistedTrack',
               'damageAssistedStun', 'damageBlockedByArmor'):
        return 'damage'
    return 'counter'


def _cumulative_conditions(group, depth=0):
    if depth > 8:
        return
    for condition in getattr(group, 'items', ())[:128]:
        if callable(getattr(condition, 'getProgressPerGroup', None)):
            yield condition
        elif hasattr(condition, 'items'):
            for nested in _cumulative_conditions(condition, depth + 1):
                yield nested


def _common_objectives(quest, row):
    data = row.get('_result_progress')
    bonus = getattr(quest, 'bonusCond', None)
    get_conditions = getattr(bonus, 'getConditions', None)
    if not data or not callable(get_conditions):
        return
    group, previous, current = data
    objectives, comparable = [], True
    for condition in _cumulative_conditions(get_conditions()):
        if len(objectives) >= OBJECTIVE_LIMIT:
            comparable = False
            break
        key = _text(condition.getKey())
        before = _bounded_number(previous.get(key))
        after = _bounded_number(current.get(key))
        if before is None or after is None:
            comparable = False
            continue
        # The native helper handles capped and repeating quests. Its missing
        # counter defaults must not turn an absent result value into zero.
        packed = condition.getProgressPerGroup({group: current}, {group: previous}, True).get(group)
        if not isinstance(packed, (list, tuple)) or len(packed) != 4:
            comparable = False
            continue
        after, target, delta = _bounded_number(packed[0]), _bounded_number(packed[1]), _bounded_delta(packed[2])
        if after is None or delta is None:
            comparable = False
            continue
        objective = dict(key=key, unit=_objective_unit(key, condition), after=after, delta=delta)
        before = _bounded_number(after - delta)
        if before is not None:
            objective['before'] = before
        if target is not None:
            objective['target'] = target
        label = ''
        for getter in ('getCustomTitle', 'getUserString', 'getCustomDescription'):
            get_label = getattr(condition, getter, None)
            label = _label(get_label(), 160) if callable(get_label) else ''
            if label:
                break
        if label:
            objective['label'] = label
        objectives.append(objective)
    if objectives:
        # PM3's unique-vehicle counter is independent of cumulative fields.
        objectives.extend(item for item in row.get('objectives', ()) if item['key'] == 'battlesUniqueVehicles')
        _set_progress(row, objectives, comparable)
        in_row = getattr(bonus, 'isInRow', None)
        if (row.get('status') == 'progress' and callable(in_row) and in_row() and
                any(item.get('delta', 0) < 0 and item.get('after') == 0 for item in objectives)):
            row['status'] = 'reset'


def _personal_objectives(quest, row):
    current = _mapping(_mapping(row.get('_pm_progress')).get('current'))
    get_config = getattr(quest, 'getConditionsConfig', None)
    if not current or not callable(get_config):
        return
    from gui.server_events.personal_progress.storage import PostBattleProgressStorage

    # Native storage augments config dictionaries with unique-vehicle state.
    # A result read must not mutate the live mission catalog.
    config = deepcopy(get_config())
    storage = PostBattleProgressStorage(quest.getGeneralQuestID(), config, current, quest.isOneBattleQuest())
    objectives = list(row.get('objectives', ()))
    body = storage.getBodyProgresses()
    for progress_id in sorted(body, key=_text):
        progress = body[progress_id]
        if len(objectives) >= OBJECTIVE_LIMIT:
            break
        raw = _mapping(current.get(progress_id))
        settings = _mapping(_mapping(config.get(progress_id)).get('config'))
        # Native storage creates zero-valued objects for omitted progress IDs.
        # Only an explicitly supplied numeric value/container is evidence.
        value = _bounded_number(raw.get('value'))
        counter = raw.get('counter')
        if value is None and not (isinstance(counter, dict) and
                                  all(_bounded_number(amount) is not None for amount in counter.values())):
            continue
        goal_known = ('goal' in raw if settings.get('dynamicGoal') else
                      any(key in settings for key in ('goal', 'totalGoal', 'uniqueGoal')))
        after = _bounded_number(progress.getCurrent() if goal_known else
                                value if value is not None else sum(counter.values()))
        if after is None:
            continue
        objective = dict(key='pm:' + _text(progress_id), unit='counter', after=after)
        # Descriptions interpolate the goal; an omitted dynamic goal would
        # otherwise render the storage object's synthetic zero in the text.
        label = _label(progress.getDescription(), 160) if goal_known else ''
        if label:
            objective['label'] = label
        target = _bounded_number(progress.getGoal()) if goal_known else None
        if target is not None:
            objective['target'] = target
        objectives.append(objective)
    if objectives:
        # PM2 current has no previous snapshot. Its value is not a battle delta.
        _set_progress(row, objectives)


def _personal_mission_rows(missions, ids, quests, operations):
    # PM1–PM4 can report main and additional conditions as separate quest IDs
    # for the same mission. Only the named additional condition grants honors.
    normalized = {}
    source_keys = []
    for key, mission_id in sorted(ids.items()):
        quest = quests.get(mission_id)
        if quest is None:
            missions[key]['kind'] = 'personal'
            continue
        row = missions[key].copy()
        try:
            _personal_objectives(quest, row)
        except Exception:
            # Completion evidence remains usable without optional UI metadata.
            pass
        source_keys.append(key)
        target_id = 'personal:{0}'.format(mission_id)
        if '_completed_conditions' in row:
            conditions = row.pop('_completed_conditions')
        else:
            conditions = {key} if row.get('status') == 'completed' else set()
        if quest.getAddQuestID() in conditions:
            row['status'] = 'honors'
        elif quest.getMainQuestID() in conditions:
            row['status'] = 'completed'
        elif row.get('status') == 'completed':
            # Award-list and technical subquests do not confirm an objective.
            row['status'] = 'progress' if row.get('progress_state') == 'changed' else 'observed'
        row['kind'] = 'personal'
        other = normalized.get(target_id, {})
        if MISSION_STATES.index(row['status']) >= MISSION_STATES.index(other.get('status', 'observed')):
            combined = other.copy()
            combined.update(row)
        else:
            combined = row.copy()
            combined.update(other)
        objectives = {}
        for objective in list(other.get('objectives', ())) + list(row.get('objectives', ())):
            objectives[objective['key']] = objective
        if objectives:
            _set_progress(combined, [objectives[name] for name in sorted(objectives)],
                          row.get('progress_state') == 'unchanged' and
                          other.get('progress_state', 'unchanged') == 'unchanged')
        normalized[target_id] = combined

    for key in source_keys:
        del missions[key]
    missions.update(normalized)
    for mission_id in set(ids.values()):
        quest = quests.get(mission_id)
        if quest is None:
            continue
        row = missions['personal:{0}'.format(mission_id)]
        operation = operations.get(quest.getOperationID())
        if operation is not None:
            row['operation'] = _label(operation.getUserName(), 160)
        _quest_labels(quest, row)
        try:
            _common_objectives(quest, row)
        except Exception:
            # Preserve explicit result counters if the catalog cannot resolve
            # this client's cumulative-condition implementation.
            pass


def game_mission_metadata(missions):
    """Resolve missions from the native post-battle catalog, including PM4."""
    from gui.server_events.events_helpers import (
        isBattleMattersQuestID, isDailyEpicReward, isDailyQuest, isPremium, isWeeklyQuest)
    from helpers import dependency
    from personal_missions import PM_BRANCH, g_cache
    from skeletons.gui.server_events import IEventsCache

    cache = dependency.instance(IEventsCache)
    personal_ids = {}
    for key in missions:
        if key.startswith('personal:') and key[len('personal:'):].isdigit():
            personal_ids[key] = int(key[len('personal:'):])
        elif g_cache.isPersonalMission(key):
            personal_ids[key] = g_cache.getPersonalMissionIDByUniqueID(key)

    if personal_ids:
        personal = cache.getPersonalMissions()
        _personal_mission_rows(missions, personal_ids, personal.getAllQuests(PM_BRANCH.ALL_NAMES),
                               personal.getAllOperations(PM_BRANCH.ALL_NAMES))
    ordinary = set(missions) - set('personal:{0}'.format(identifier) for identifier in personal_ids.values())
    if not ordinary:
        return
    public = cache.getQuests(lambda quest: quest.getID() in ordinary)
    hidden = cache.getHiddenQuests(lambda quest: quest.getID() in ordinary, makeRelations=False)
    kinds = (('daily_epic', isDailyEpicReward), ('premium', isPremium), ('daily', isDailyQuest),
             ('weekly', isWeeklyQuest), ('battle_matters', isBattleMattersQuestID))
    for key in ordinary:
        row = missions[key]
        if row.get('kind') == 'personal':
            continue
        if row.get('kind') != 'crucible':
            for kind, matches in kinds:
                if matches(key):
                    row['kind'] = kind
                    break
        quest = public.get(key) or hidden.get(key)
        if quest is None:
            continue
        _quest_labels(quest, row)
        try:
            _common_objectives(quest, row)
        except Exception:
            # Labels and explicit counters survive incomplete catalog support.
            pass
        is_bonus = getattr(quest, 'isBonus', None)
        if row.get('kind') == 'daily' and callable(is_bonus) and is_bonus():
            row['kind'] = 'daily_bonus'
        bonus_conditions = getattr(quest, 'bonusCond', None)
        if (row.get('status') == 'progress' and row.get('before', 0) > 0 and row.get('after') == 0
                and row.get('progress_kind') != 'vehicles' and bonus_conditions is not None
                and bonus_conditions.isInRow()):
            row['status'] = 'reset'


def game_active_crucible():
    """Read the active stage in the lobby before the controller is cleared."""
    from helpers import dependency
    from skeletons.gui.challenges import IChallengesController

    controller = dependency.instance(IChallengesController)
    if controller is None or not controller.isEnabled or not controller.activeChallengeID:
        return {}
    challenge = controller.getChallenge(controller.activeChallengeID)
    if challenge is None:
        return {}
    stage = controller.getChallengeProgress(challenge.challengeID).get('quests')
    if not isinstance(stage, integer_types) or not 0 <= stage < len(challenge.questsIDs):
        return {}
    quest_id = _text(challenge.questsIDs[stage])
    row = {'kind': 'crucible', 'stage': stage + 1}
    missions = {quest_id: row}
    try:
        row['name'] = challenge.name
        game_mission_metadata(missions)
    except Exception:
        # The selected stage remains useful when the quest catalog is unavailable.
        pass
    return clean_details({'active_crucible': quest_id, 'missions': missions})
