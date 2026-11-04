# -*- coding: utf-8 -*-
"""Extract bounded, player-only details from WoT's per-arena result."""
from __future__ import unicode_literals

import re

from .normalize import _number, _text, integer_types, text_type

MISSION_LIMIT = 32
MISSION_ID = re.compile(r'\A[A-Za-z0-9_:.\-]{1,96}\Z')
CRUCIBLE_ID = re.compile(r'\Achallenge:[0-9]{1,20}:([0-9]{1,6})(:fail)?\Z')
MARKUP = re.compile(r'<[^>]*>')
MISSION_KINDS = ('crucible', 'daily', 'daily_bonus', 'weekly', 'premium', 'personal', 'other')
MISSION_STATES = ('observed', 'progress', 'failed', 'completed')
POINT_FIELDS = {'battle': 'bpTopPoints', 'missions': 'eventBattlePassPoints',
                'vehicle': 'bpBonusPoints'}
BONUS_FIELDS = {
    'eventCredits': 'credits', 'eventXP': 'xp', 'eventFreeXP': 'free_xp',
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
    keys = sorted(key for key in incoming if isinstance(key, text_type) and MISSION_ID.match(key))
    if active in keys:
        keys.remove(active)
        keys.insert(0, active)
    for key in keys[:MISSION_LIMIT]:
        row = _mapping(incoming[key])
        mission = {}
        for field, size in (('name', 160), ('description', 420)):
            label = _label(row.get(field), size)
            if label:
                mission[field] = label
        for field, options in (('kind', MISSION_KINDS), ('status', MISSION_STATES)):
            if row.get(field) in options:
                mission[field] = row[field]
        for field in ('stage', 'before', 'after'):
            amount = _bounded_number(row.get(field))
            if amount is not None:
                mission[field] = amount
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
                    row = dict(combined.get(key, {}))
                    for name, entry in item.items():
                        previous = row.get(name)
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


def result_details(avatar, vehicle, active=None):
    details = {'pass_points': _pass_points(avatar), 'bonuses': {}, 'missions': {}}
    if active:
        details['active_crucible'] = active
    for field in BONUS_FIELDS:
        amount = _bounded_number(vehicle.get(field))
        base = BONUS_FIELDS[field] if isinstance(BONUS_FIELDS[field], int) else 0
        if amount is not None and amount > base:
            details['bonuses'][field] = amount
        # Account-level event amounts and vehicle-level amounts are separate.
        if field in ('eventCredits', 'eventXP', 'eventFreeXP'):
            account_amount = _bounded_number(avatar.get(field))
            if account_amount:
                details['bonuses'][field] = (details['bonuses'].get(field) or 0) + account_amount
    # Native FairplayViolationsInfo stores warnings, penalties and violations
    # separately. Only the violation/penalty mask is evidence of suicide.
    fairplay = avatar.get('fairplayViolations')
    if isinstance(fairplay, (list, tuple)) and len(fairplay) >= 3:
        details['suicide'] = any(isinstance(mask, integer_types) and mask >= 0 and mask & 2
                                 for mask in fairplay[1:3])

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
                row = details['missions'].setdefault(quest_id[:-5], {})
                if row.get('status') != 'completed':
                    row.update(kind='crucible', stage=int(challenge.group(1)), status='failed')
            continue
        before = _bounded_number(previous.get('battlesCount', 0))
        after = _bounded_number(current.get('battlesCount'))
        if not complete and previous == current and quest_id != active:
            continue
        row = details['missions'].setdefault(quest_id, {})
        status = 'completed' if complete else 'progress' if previous != current else 'observed'
        if status == 'completed' or row.get('status') != 'failed':
            row['status'] = status
        if challenge:
            row.update(kind='crucible', stage=int(challenge.group(1)))
        if before is not None and after is not None and before != after:
            row.update(before=before, after=after)

    personal = dict(_mapping(avatar.get('PM2Progress')))
    personal.update(_mapping(vehicle.get('PM2Progress')))
    for mission_id, progress in personal.items():
        mission_id = _text(mission_id)
        if mission_id.isdigit() and isinstance(progress, dict) and progress:
            details['missions']['pm2:' + mission_id] = {
                'kind': 'personal', 'status': 'completed' if any(value is True for value in progress.values()) else 'progress'}
    return clean_details(details)


def game_mission_metadata(missions):
    """Resolve names using the same local cache as the native results view."""
    from gui.server_events.events_helpers import isDailyQuest, isPremium, isWeeklyQuest
    from helpers import dependency
    from skeletons.gui.server_events import IEventsCache

    cache = dependency.instance(IEventsCache)
    public = cache.getQuests(lambda quest: quest.getID() in missions)
    hidden = cache.getHiddenQuests(lambda quest: quest.getID() in missions, makeRelations=False)
    personal = cache.getPersonalMissions().getAllQuests() if any(key.startswith('pm2:') for key in missions) else {}
    for key, row in missions.items():
        if key.startswith('pm2:'):
            quest = personal.get(int(key[4:]))
        else:
            quest = public.get(key) or hidden.get(key)
            if row.get('kind') != 'crucible':
                for kind, matches in (('premium', isPremium), ('daily', isDailyQuest), ('weekly', isWeeklyQuest)):
                    if matches(key):
                        row['kind'] = kind
                        break
        if quest is None:
            continue
        name = _label(quest.getUserName(), 160)
        if name:
            row['name'] = name
        is_bonus = getattr(quest, 'isBonus', None)
        if row.get('kind') == 'daily' and callable(is_bonus) and is_bonus():
            row['kind'] = 'daily_bonus'
        for getter in ('getConditionsDescription', 'getUserDescription', 'getDescription'):
            read = getattr(quest, getter, None)
            description = _label(read(), 420) if callable(read) else ''
            if description:
                row['description'] = description
                break


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
