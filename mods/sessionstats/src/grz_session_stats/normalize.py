# -*- coding: utf-8 -*-
"""Normalize the *player's* server result; no UI strings and no game imports.

Client source checked at izeberg/wot-src, version 2.4.1.5493:
  sources/res/scripts/common/battle_results/battle_results_common.py
  sources/res/scripts/client/gui/battle_results/reusable/personal.py
  sources/res/scripts/client/gui/battle_results/components/details.py
  sources/res/scripts/client/gui/battle_results/reusable/economics_records.py
  sources/res/scripts/common/constants.py:getArenaStartTime
The personal mapping uses vehicle compact descriptors, not arena vehicle IDs.
credits/crystal/gold/xp are awarded values; original* are before bonuses.
Credit totals follow MoneyDetailsBlock.__intermediateTotalRecords; equipment
costs already include directives, so autoEquipBoostersCost is only a breakdown.
"""
from __future__ import absolute_import, division, unicode_literals

from .localization import message

import math

try:
    text_type = unicode
    integer_types = (int, long)
except NameError:
    text_type = str
    integer_types = (int,)


def _number(value, nonnegative=True):
    if isinstance(value, bool) or not isinstance(value, integer_types + (float,)):
        return None
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    if nonnegative and value < 0:
        return None
    return value


def _integer(value):
    if isinstance(value, bool):
        return None
    try:
        answer = int(value)
    except (ValueError, TypeError, OverflowError):
        return None
    if answer <= 0 or (isinstance(value, float) and answer != value):
        return None
    return answer


def _text(value, fallback=''):
    if value is None:
        return fallback
    try:
        if isinstance(value, bytes) and not isinstance(value, text_type):
            return value.decode('utf-8', 'replace')
        return text_type(value)
    except (ValueError, TypeError, UnicodeError):
        return fallback


_COST_WIDTHS = {'autoLoadCost': 2, 'autoEquipCost': 3, 'autoEquipBoostersCost': 3}


def _tuple_cost(data, name, index):
    value = data.get(name)
    # Positions are a verified client contract, not a guess for a new tuple.
    # Reject an extended/truncated container instead of silently assigning
    # changed currency positions. Unknown individual amounts stay independent.
    width = _COST_WIDTHS.get(name)
    if not isinstance(value, (tuple, list)) or len(value) != width or index >= len(value):
        return None
    return _number(value[index])


def _sum_known(values):
    return sum(values) if all(value is not None for value in values) else None


def _money(income, costs, breakdown=None):
    result = {'income': income, 'costs': costs,
              'net': income - costs if income is not None and costs is not None else None}
    if breakdown is not None:
        result['breakdown'] = breakdown
    return result


def _credit_income(data, warnings):
    # credits is the actual premium/booster-adjusted result, not originalCredits.
    # The game's money panel subtracts the two squad-sharing deductions before
    # subtracting repair/ammo/equipment. Never apply premium to credits again.
    credits = _number(data.get('credits'), nonnegative=False)
    if credits is None:
        return None
    deductions = []
    for field, factor in (('originalCreditsToDraw', 'appliedPremiumCreditsFactor100'),
                          ('originalCreditsToDrawSquad', 'premSquadCreditsFactor100')):
        value = _number(data.get(field))
        if value is None:
            warnings.append(message('normalize.platoon'))
            return None
        if not value:
            deductions.append(0)
            continue
        multiplier = _number(data.get(factor))
        if multiplier is None:
            warnings.append(message('normalize.factor'))
            return None
        scaled = value * multiplier / 100.0
        # The first subtraction is a rounded replay value. The squad sharing
        # record is SUBCOEFF: the client's _diff is deliberately not rounded.
        deductions.append(int(math.floor(scaled + 0.5)) if field == 'originalCreditsToDraw' else scaled)
    return credits - sum(deductions)


def normalize_currencies(data, warnings=None):
    warnings = warnings if warnings is not None else []
    repair = _number(data.get('autoRepairCost'))
    ammo = _tuple_cost(data, 'autoLoadCost', 0)
    equipment = _tuple_cost(data, 'autoEquipCost', 0)
    directives = _tuple_cost(data, 'autoEquipBoostersCost', 0)
    consumables = None
    if equipment is not None and directives is not None:
        if directives <= equipment:
            consumables = equipment - directives
        else:
            directives = None
            warnings.append(message('normalize.costs'))
    credit_costs = _sum_known([repair, ammo, equipment])
    bond_costs = _tuple_cost(data, 'autoEquipCost', 2)
    gold_costs = _sum_known([_tuple_cost(data, 'autoLoadCost', 1),
                             _tuple_cost(data, 'autoEquipCost', 1)])
    result = {
        'credits': _money(_credit_income(data, warnings), credit_costs,
                          {'repair': repair, 'ammo': ammo,
                           'consumables': consumables, 'directives': directives}),
        # crystal includes mission bonds. originalCrystal alone does not.
        'bonds': _money(_number(data.get('crystal')), bond_costs),
        'gold': _money(_number(data.get('gold')), gold_costs),
    }
    if _number(data.get('piggyBank')):
        warnings.append(message('normalize.reserve'))
    if any(value['net'] is None for value in result.values()):
        warnings.append(message('normalize.finance'))
    return result


def _personal_vehicle(personal, context):
    if not isinstance(personal, dict):
        return None, None
    choices = []
    for key, value in personal.items():
        if key == 'avatar' or not isinstance(value, dict):
            continue
        compact = _integer(value.get('typeCompDescr')) or _integer(key)
        if compact is not None:
            choices.append((compact, value))
    if len(choices) == 1:
        return choices[0]
    wanted = _integer(context.get('vehicle_id'))
    matching = [item for item in choices if item[0] == wanted]
    return matching[0] if len(matching) == 1 else (None, None)


def arena_start(arena_id):
    """Same uint64 layout as constants.getArenaStartTime, with plausibility gate."""
    value = _integer(arena_id)
    if value is None:
        return None
    stamp = value & 0xffffffff
    return stamp if 946684800 <= stamp <= 4102444800 else None


def normalize_result(results, context=None, random_bonus_type=1,
                     vehicle_resolver=None, map_resolver=None):
    """Return a normalized random-battle record, or None if it is not ours.

    context may contain account_dbid, started_at, vehicle_id and map metadata
    captured at battle entry. A missing source value stays None. A server result
    with an unknown outcome can be retained for reconciliation but is not a win.
    """
    context = context or {}
    if not isinstance(results, dict) or context.get('replay'):
        return None
    common = results.get('common')
    if not isinstance(common, dict):
        return None
    bonus = _integer(common.get('bonusType'))
    if bonus != random_bonus_type:
        return None
    arena_id = _integer(results.get('arenaUniqueID'))
    if arena_id is None:
        return None
    personal = results.get('personal')
    if not isinstance(personal, dict):
        return None
    avatar = personal.get('avatar') or {}
    if not isinstance(avatar, dict):
        return None
    expected_dbid = _integer(context.get('account_dbid'))
    actual_dbid = _integer(avatar.get('accountDBID'))
    if expected_dbid is not None and actual_dbid != expected_dbid:
        return None
    vehicle_id, data = _personal_vehicle(personal, context)
    if data is None:
        if context.get('_loading') and not context.get('_candidate'):
            candidates = []
            for key, value in personal.items():
                if key == 'avatar' or not isinstance(value, dict):
                    continue
                compact = _integer(value.get('typeCompDescr')) or _integer(key)
                if compact is None:
                    continue
                candidate_context = dict(context, vehicle_id=compact, _candidate=True)
                candidate = normalize_result(results, candidate_context, random_bonus_type,
                                             vehicle_resolver, map_resolver)
                if candidate is not None:
                    candidates.append(candidate)
            if candidates:
                # Preserve only normalized player data, never the raw server
                # payload. Select the correct vehicle after stored context loads.
                return {'arena_id': text_type(arena_id), 'mode': 'random', 'complete': False,
                        'started_at': arena_start(arena_id) or _number(context.get('started_at')),
                        'vehicle_id': None, 'xp_received': None,
                        '_deferred_candidates': candidates}
        return None
    warnings = []
    team = _integer(avatar.get('team')) or _integer(data.get('team'))
    winner = _number(common.get('winnerTeam'))
    outcome = None
    if winner == 0:
        outcome = 'draw'
    elif winner in (1, 2) and team in (1, 2):
        outcome = 'win' if winner == team else 'loss'
    info = {}
    if vehicle_resolver is not None:
        try:
            info = vehicle_resolver(vehicle_id) or {}
        except Exception:
            warnings.append(message('normalize.vehicle'))
    map_info = {}
    arena_type_id = _integer(common.get('arenaTypeID'))
    if map_resolver is not None and arena_type_id is not None:
        try:
            map_info = map_resolver(arena_type_id) or {}
        except Exception:
            warnings.append(message('normalize.map'))
    map_id = map_info.get('id') or context.get('map_id')
    if not map_id:
        map_id = 'arena:{0}'.format(arena_type_id) if arena_type_id else 'unknown'
    started_at = arena_start(arena_id) or _number(context.get('started_at'))
    duration = _number(common.get('duration'))
    result = {
        'arena_id': text_type(arena_id),
        'started_at': started_at,
        'ended_at': started_at + duration if started_at is not None and duration is not None else None,
        'vehicle_id': vehicle_id,
        'vehicle_name': _text(info.get('name') or context.get('vehicle_name'),
                              message('unknown.vehicle_id').format(vehicle_id) if vehicle_id is not None else message('unknown.vehicle')),
        'vehicle_tier': _integer(info.get('tier') or context.get('vehicle_tier')),
        'vehicle_type': _text(info.get('type') or context.get('vehicle_type')) or None,
        'map_id': _text(map_id),
        'map_name': _text(map_info.get('name') or context.get('map_name'),
                          message('unknown.map_id').format(arena_type_id) if arena_type_id else message('unknown.map')),
        'mode': 'random', 'outcome': outcome,
        'damage': _number(data.get('damageDealt')),
        'frags': _number(data.get('kills')),
        'spots': _number(data.get('spotted')),
        'defense': _number(data.get('droppedCapturePoints')),
        'xp_base': _number(data.get('originalXP')),
        'xp_received': _number(data.get('xp')),
        'free_xp': _number(data.get('freeXP')),
        'currencies': normalize_currencies(data, warnings),
        'warnings': warnings, 'complete': False, 'reconcile': True,
        'xp_bonus_applied': False,
    }
    if context.get('_loading'):
        fields = []
        for field, source in (('vehicle_name', 'name'), ('vehicle_tier', 'tier'), ('vehicle_type', 'type')):
            if not info.get(source):
                fields.append(field)
        for field, source in (('map_id', 'id'), ('map_name', 'name')):
            if not map_info.get(source):
                fields.append(field)
        if arena_start(arena_id) is None:
            fields.append('started_at')
        result['_deferred_context'] = {'fields': fields, 'duration': duration}
    required = ('damage', 'frags', 'spots', 'defense', 'xp_base', 'xp_received', 'free_xp')
    result['complete'] = bool(outcome and all(result[key] is not None for key in required)
                              and all(value['net'] is not None for value in result['currencies'].values()))
    return result
