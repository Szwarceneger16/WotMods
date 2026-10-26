# -*- coding: utf-8 -*-
"""Bounded, read-only checks of the result contract consumed by this mod.

The allowed field names are frozen from client 2.4.1.5493, commit
5e721e36891c80d8d51a431164960c863641ee63: battle_results_common.py (including
BATTLE_PASS_RESULTS), random.py, and the cache's convertToFullForm envelope.
This is not a learned baseline, an emulator, or proof of unchanged semantics.
No payload values, account IDs, player names or arbitrary repr() enter issues.
"""
from __future__ import absolute_import, unicode_literals

from .normalize import _COST_WIDTHS, _integer, _number, _personal_vehicle, integer_types, text_type

MAX_ISSUES = 32
MAX_FIELDS = 1024
MAX_RECORDS = 64
COST_WIDTHS = _COST_WIDTHS
_ENVELOPE_FIELDS = frozenset(('arenaUniqueID', 'common', 'personal', 'players', 'vehicles', 'avatars'))
_COMMON_FIELDS = frozenset("""
accountCompDescr arenaCreateTime arenaTypeID battleModifiersDescr bonusCapsOverrides bonusType
bots commonNumCaptured commonNumDefended commonNumDestroyed commonNumStarted division duration
finishAllPlayersLeft finishReason gasAttackWinnerTeam guiType teamHealth vehLockMode winnerTeam
""".split())
_AVATAR_FIELDS = frozenset("""
PM2Progress accountDBID activeRents availablePoints avatarAmmo avatarDamageDealt
avatarDamageEventList avatarDamaged avatarKills avatarPlayerSatisfactionRating badges
battlePassComplete battlePassPoints battlePassPointsReplay bpBonusPoints bpChaptersInfo
bpNonChapterPointsDiff bpTopExternalPoints bpTopPoints clanDBID commendationsReceived
commendationsSent credits crystal dogTags eligibleForCrystalRewards eventBattlePassPoints
eventBattlePassPointsList eventBpcoin eventCredits eventCrystal eventEquipCoin eventEventCoin
eventFreeXP eventGold eventTMenXP eventXP fairplayViolations fareTeamXPPosition fortClanDBIDs
freeXP goldBankGain hasBattlePass isPrematureLeave originalBattlePassPoints playerRank
progressiveReward questTokensConvertion questTokensCount questsProgress rankChange recruiterID
recruitsIDs referralBonusVehicles replayURL squadBonusInfo team totalDamaged vseBattleResults
watchedBattleToTheEnd winnerIfDraw xp
""".split())
_VEHICLE_FIELDS = frozenset("""
accountDBID achievementCredits achievementFreeXP achievementXP achievements additionalXPFactor10
aogasFactor10 appliedPremiumCreditsFactor100 appliedPremiumTmenXPFactor100
appliedPremiumXPFactor100 artilleryFortEquipDamageDealt autoEquipBoostersCost autoEquipCost
autoLoadCost autoRepairCost battleNum boosterCredits boosterCreditsFactor100 boosterFreeXP
boosterFreeXPFactor100 boosterTMenXP boosterTMenXPFactor100 boosterXP boosterXPFactor100 bpcoin
bpcoinReplay c11nProgress capturePoints capturingBase committedSuicide credits
creditsContributionIn creditsContributionOut creditsPenalty creditsReplay creditsToDraw crystal
crystalReplay currencies dailyXPFactor10 damageAssistedInspire damageAssistedRadio
damageAssistedSmoke damageAssistedStun damageAssistedTrack damageBeforeTeamWasDamaged
damageBlockedByArmor damageDealt damageRating damageReceived damageReceivedFromInvisibles damaged
damagedHp damagedWhileEnemyMoving damagedWhileMoving deathCount deathReason destructibleDeaths
destructiblesDamageDealt destructiblesHits destructiblesNumDestroyed details directEnemyHits
directHits directHitsReceived directTeamHits dossierLogRecords dossierPopUps droppedCapturePoints
entityCaptured equipCoin equipCoinReplay equipmentDamageDealt eventBpcoin eventBpcoinList
eventCoin eventCoinReplay eventCredits eventCreditsFactor100List eventCreditsList eventCrystal
eventCrystalList eventEquipCoin eventEquipCoinList eventEventCoin eventEventCoinList eventFreeXP
eventFreeXPFactor100List eventFreeXPList eventGold eventGoldFactor100List eventGoldList
eventTMenXP eventTMenXPFactor100List eventTMenXPList eventXP eventXPFactor100List eventXPList
explosionHits explosionHitsReceived factualCredits factualFreeXP factualXP fairplayFactor10
flagActions flagCapture freeXP freeXPReplay gold goldReplay health igrXPFactor10
inBattleAchievements index isFirstBlood isPremium isTeamKiller isWoTPlus
killedAndDamagedByAllSquadmates killerID kills killsBeforeTeamWasDamaged lifeTime markOfMastery
marksOnGun maxHealth mileage movingAvgDamage noDamageDirectHitsReceived numDefended numRecovered
orderCredits orderCreditsFactor100 orderFreeXP orderFreeXPFactor100 orderTMenXP
orderTMenXPFactor100 orderXP orderXPFactor100 originalBpcoin originalCredits
originalCreditsContributionIn originalCreditsContributionInSquad originalCreditsContributionOut
originalCreditsContributionOutSquad originalCreditsPenalty originalCreditsPenaltySquad
originalCreditsToDraw originalCreditsToDrawSquad originalCrystal originalEquipCoin
originalEventCoin originalFreeXP originalGold originalPremSquadCredits originalTMenXP originalXP
originalXPPenalty outfit percentFromSecondBestDamage percentFromTotalTeamDamage petSystemCredits
petSystemCreditsFactor100 piercingEnemyHits piercings piercingsReceived piggyBank playerRankXP
playerRankXPFactor100 poiCapturedByOwnTeam potentialDamageReceived premMask premSquadCredits
premSquadCreditsFactor100 premiumCreditsFactor100 premiumPlusCreditsFactor100
premiumPlusTmenXPFactor100 premiumPlusXPFactor100 premiumTmenXPFactor100 premiumVehicleXP
premiumVehicleXPFactor100 premiumXPFactor100 prestigeResults prevMarkOfMastery questsProgress
refSystemXPFactor10 referral20Credits referral20CreditsFactor100 referral20XP
referral20XPFactor100 repair resourceAbsorbed rolloutsCount serviceProviderID setupsIndexes shots
sniperDamageDealt soloFlagCapture spotted squadXP squadXPFactor100 stopRespawn stunDuration
stunNum stunned subtotalBpcoin subtotalCredits subtotalCrystal subtotalEquipCoin subtotalEventCoin
subtotalFreeXP subtotalGold subtotalTMenXP subtotalXP tdamageDealt tdestroyedModules team tkills
tmenXP tmenXPReplay typeCompDescr vehTypeLockTime vehicleNumCaptured winAloneAgainstVehicleCount
winPoints wotPlusCredits wotPlusCreditsFactor100 wotPlusCrewXP wotPlusCrewXPFactor100
wotPlusFreeXP wotPlusFreeXPFactor100 wotPlusProBoostCredits wotPlusProBoostCreditsFactor100
wotPlusProBoostCrewXP wotPlusProBoostCrewXPFactor100 wotPlusProBoostFreeXP
wotPlusProBoostFreeXPFactor100 wotPlusProBoostXP wotPlusProBoostXPFactor100 wotPlusTier wotPlusXP
wotPlusXPFactor100 xp xp/assist xp/attack xp/other xpByTmen xpPenalty xpReplay
""".split())
_PLAYER_FIELDS = frozenset("""
clanAbbrev clanDBID igrType name prebattleID realName team
""".split())
_STRING_TYPES = (text_type, bytes)
_MISSING = object()


def _kind(value):
    if value is _MISSING:
        return 'missing'
    if value is None:
        return 'null'
    if isinstance(value, bool):
        return 'boolean'
    if isinstance(value, integer_types):
        return 'integer'
    if isinstance(value, float):
        return 'number' if _number(value, nonnegative=False) is not None else 'non-finite number'
    if isinstance(value, _STRING_TYPES):
        return 'text'
    if isinstance(value, dict):
        return 'mapping'
    if isinstance(value, (tuple, list)):
        return 'sequence(length={0})'.format(len(value))
    if isinstance(value, (set, frozenset)):
        return 'set'
    return 'unsupported object'


def _field_name(value):
    # Dynamic record keys never pass through here. A schema extension may
    # still carry an arbitrary key: do not copy its content into diagnostics.
    if not isinstance(value, _STRING_TYPES):
        return '<unknown-field>'
    try:
        if isinstance(value, bytes) and not isinstance(value, text_type):
            value = value.decode('ascii')
        if (0 < len(value) <= 48 and value[0].isalpha() and
                all(ord(char) < 128 and (char.isalnum() or char in '_/') for char in value)):
            return value
    except (UnicodeError, TypeError, ValueError):
        pass
    return '<unknown-field>'


class _Inspection(object):
    def __init__(self):
        self.issues = []
        self._seen = set()

    def add(self, code, path, expected, actual):
        item = {'code': code, 'path': path[:160], 'expected': expected[:160], 'actual': actual[:100]}
        token = (item['code'], item['path'], item['expected'], item['actual'])
        if token in self._seen:
            return
        if len(self.issues) < MAX_ISSUES:
            self._seen.add(token)
            self.issues.append(item)
        elif self.issues[-1]['code'] != 'inspection_limit':
            self.issues[-1] = {'code': 'inspection_limit', 'path': 'result',
                              'expected': 'bounded diagnostic output',
                              'actual': 'additional issues omitted'}

    def names(self, mapping, known, path):
        if len(mapping) > MAX_FIELDS:
            self.add('inspection_limit', path, 'at most {0} fields'.format(MAX_FIELDS), 'oversized mapping')
            return
        for name in mapping:
            if name not in known:
                self.add('unknown_field', path + '.' + _field_name(name),
                         'field in the pinned client contract', _kind(mapping[name]))

    def number(self, mapping, name, path, required=True, signed=False, integer=False, positive=False):
        value = mapping.get(name, _MISSING)
        field = path + '.' + name
        if value is _MISSING and not required:
            return None
        expected = ('positive integer' if positive else
                    'integer' if integer else 'finite number')
        if not signed and not positive:
            expected += ' >= 0'
        if value is _MISSING:
            self.add('missing_field', field, expected, 'missing')
            return None
        if _number(value, nonnegative=False) is None:
            self.add('invalid_type', field, expected, _kind(value))
            return None
        if integer and (isinstance(value, float) or not isinstance(value, integer_types)):
            self.add('invalid_type', field, expected, _kind(value))
            return None
        if (positive and value <= 0) or (not signed and value < 0):
            self.add('invalid_range', field, expected, 'number outside supported range')
            return None
        return value

    def mapping(self, mapping, name, path, required=True):
        value = mapping.get(name, _MISSING)
        field = path + '.' + name
        if value is _MISSING and not required:
            return None
        if not isinstance(value, dict):
            self.add('missing_field' if value is _MISSING else 'invalid_type',
                     field, 'mapping', _kind(value))
            return None
        return value

    def cost(self, mapping, name):
        path = 'personal.vehicle.' + name
        value = mapping.get(name, _MISSING)
        width = COST_WIDTHS[name]
        expected = 'sequence of {0} nonnegative integer amounts'.format(width)
        if not isinstance(value, (tuple, list)):
            self.add('missing_field' if value is _MISSING else 'invalid_type',
                     path, expected, _kind(value))
            return None
        if len(value) != width:
            self.add('unsupported_shape', path, expected, _kind(value))
            return None
        valid = True
        for index, amount in enumerate(value):
            if _number(amount) is None or not isinstance(amount, integer_types):
                self.add('invalid_amount', path + '[{0}]'.format(index),
                         'nonnegative integer amount', _kind(amount) if _number(amount, False) is None
                         or not isinstance(amount, integer_types)
                         else 'number outside supported range')
                valid = False
        return value if valid else None

    def record_map(self, value, section, known, sequence=False):
        if len(value) > MAX_RECORDS:
            self.add('inspection_limit', section, 'at most {0} records'.format(MAX_RECORDS), 'oversized mapping')
            return
        for key, record in value.items():
            # Account and arena-vehicle identifiers are dynamic, not fields.
            # convertToFullForm copies these unused-map keys without a sign
            # constraint. Do not infer that bot/auxiliary records must be > 0.
            valid_key = isinstance(key, integer_types) and not isinstance(key, bool)
            if isinstance(key, _STRING_TYPES):
                try:
                    int(key)
                    valid_key = True
                except (ValueError, TypeError, OverflowError):
                    pass
            if not valid_key:
                self.add('invalid_key', section + '.<record>', 'integer record identifier', _kind(key))
            records = record
            if sequence:
                if not isinstance(record, (list, tuple)):
                    self.add('invalid_type', section + '.<record>', 'sequence of mappings', _kind(record))
                    continue
                if len(record) > MAX_RECORDS:
                    self.add('inspection_limit', section + '.<record>', 'bounded sequence', 'oversized sequence')
                    continue
            else:
                records = (record,)
            for item in records:
                if not isinstance(item, dict):
                    self.add('invalid_type', section + '.<record>', 'mapping', _kind(item))
                else:
                    self.names(item, known, section + '.<record>')


def inspect_result(results, context=None, random_bonus_type=1):
    """Return bounded issues for a delivered result, without modifying it.

    Non-random modes and another identified account return no format alarms.
    Absence of unused optional fields and changing dynamic record IDs is normal.
    The caller must skip unsuccessful/not-ready cache responses before calling.
    """
    context = context or {}
    if context.get('replay'):
        return []
    check = _Inspection()
    if not isinstance(results, dict):
        check.add('invalid_type', 'result', 'mapping', _kind(results))
        return check.issues
    personal = results.get('personal')
    avatar = personal.get('avatar') if isinstance(personal, dict) else None
    expected_dbid = _integer(context.get('account_dbid'))
    actual_dbid = _integer(avatar.get('accountDBID')) if isinstance(avatar, dict) else None
    if expected_dbid is not None and actual_dbid is not None and actual_dbid != expected_dbid:
        return []
    common = results.get('common')
    if not isinstance(common, dict):
        check.mapping(results, 'common', 'result')
        return check.issues
    bonus = _integer(common.get('bonusType'))
    if bonus is not None and bonus != random_bonus_type:
        return []
    check.names(results, _ENVELOPE_FIELDS, 'result')
    arena_id = check.number(results, 'arenaUniqueID', 'result', integer=True, positive=True)
    if arena_id is not None and arena_id > 0xffffffffffffffff:
        check.add('invalid_range', 'result.arenaUniqueID', 'positive uint64', 'integer outside supported range')
    check.names(common, _COMMON_FIELDS, 'common')
    check.number(common, 'bonusType', 'common', integer=True, positive=True)
    check.number(common, 'arenaTypeID', 'common', integer=True, positive=True)
    check.number(common, 'duration', 'common', integer=True)
    winner = check.number(common, 'winnerTeam', 'common', integer=True)
    if winner is not None and winner not in (0, 1, 2):
        check.add('invalid_range', 'common.winnerTeam', 'draw or one of the two standard teams',
                  'integer outside supported team set')
    personal = check.mapping(results, 'personal', 'result')
    if personal is None:
        return check.issues
    avatar = check.mapping(personal, 'avatar', 'personal')
    if avatar is not None:
        check.names(avatar, _AVATAR_FIELDS, 'personal.avatar')
        check.number(avatar, 'accountDBID', 'personal.avatar', integer=True, positive=True)
    if len(personal) > MAX_RECORDS:
        check.add('inspection_limit', 'personal', 'bounded vehicle mapping', 'oversized mapping')
        return check.issues
    for key, value in personal.items():
        if key == 'avatar':
            continue
        if _integer(key) is None:
            check.add('invalid_key', 'personal.vehicle', 'positive vehicle compact descriptor', _kind(key))
        if not isinstance(value, dict):
            check.add('invalid_type', 'personal.vehicle', 'mapping', _kind(value))
        else:
            check.names(value, _VEHICLE_FIELDS, 'personal.vehicle')
            if 'typeCompDescr' in value:
                compact = check.number(value, 'typeCompDescr', 'personal.vehicle', integer=True, positive=True)
                if compact is not None and _integer(key) is not None and compact != _integer(key):
                    check.add('inconsistent_identity', 'personal.vehicle.typeCompDescr',
                              'descriptor matching personal record key', 'mismatched descriptor')
    vehicle_id, vehicle = _personal_vehicle(personal, context)
    if vehicle is None:
        check.add('unresolved_vehicle', 'personal.vehicle',
                  'one personal vehicle or an unambiguous captured descriptor', 'missing or ambiguous vehicle mapping')
    else:
        for name in ('damageDealt', 'kills', 'spotted', 'droppedCapturePoints',
                     'originalXP', 'xp', 'freeXP', 'crystal', 'gold', 'autoRepairCost'):
            check.number(vehicle, name, 'personal.vehicle', integer=True)
        check.number(vehicle, 'credits', 'personal.vehicle', signed=True, integer=True)
        for name, factor in (('originalCreditsToDraw', 'appliedPremiumCreditsFactor100'),
                             ('originalCreditsToDrawSquad', 'premSquadCreditsFactor100')):
            deduction = check.number(vehicle, name, 'personal.vehicle', integer=True)
            check.number(vehicle, factor, 'personal.vehicle', required=deduction is not None and deduction > 0,
                         integer=True)
        check.number(vehicle, 'piggyBank', 'personal.vehicle', required=False, integer=True)
        team_source = avatar if isinstance(avatar, dict) and 'team' in avatar else vehicle
        team_path = 'personal.avatar' if team_source is avatar else 'personal.vehicle'
        team = check.number(team_source, 'team', team_path, required=winner != 0, integer=True, positive=True)
        if team is not None and team not in (1, 2):
            check.add('invalid_range', team_path + '.team', 'one of the two standard teams',
                      'integer outside supported team set')
        costs = dict((name, check.cost(vehicle, name)) for name in sorted(COST_WIDTHS))
        equipment, directives = costs['autoEquipCost'], costs['autoEquipBoostersCost']
        if equipment is not None and directives is not None and any(directives[i] > equipment[i] for i in range(3)):
            check.add('inconsistent_costs', 'personal.vehicle.autoEquipBoostersCost',
                      'directive components included in equipment costs', 'component exceeds total equipment cost')
    for name, fields, sequence in (('players', _PLAYER_FIELDS, False),
                                   ('avatars', _AVATAR_FIELDS, False),
                                   ('vehicles', _VEHICLE_FIELDS, True)):
        value = check.mapping(results, name, 'result', required=False)
        if value is not None:
            check.record_map(value, name, fields, sequence)
    return check.issues

