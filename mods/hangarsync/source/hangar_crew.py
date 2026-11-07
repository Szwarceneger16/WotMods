# -*- coding: utf-8 -*-
"""Bounded copies of native crew skill data and the game's own tooltip text.

No skill-effect formulas, player identifiers, native tooltip objects or image
bytes cross this boundary. Unsupported client details remain absent.
"""
from __future__ import absolute_import, unicode_literals

import itertools
import copy
import hashlib
import json
import math
import re
try:
    from HTMLParser import HTMLParser as _HTMLParser
    _unescape = _HTMLParser().unescape
except ImportError:
    from html.parser import HTMLParser as _HTMLParser
    from html import unescape as _unescape

try:
    _TEXT = unicode
    _INTS = (int, long)
except NameError:
    _TEXT = str
    _INTS = (int,)
_NUMBERS = _INTS + (float,)
_ID = re.compile(r'\A[A-Za-z][A-Za-z0-9_-]{0,79}\Z')
MAX_SKILLS = 24
MAX_CATALOG = 128


def _source_text(value):
    if isinstance(value, bytes) and not isinstance(value, _TEXT):
        value = value.decode('utf-8', 'replace')
    if not isinstance(value, _TEXT):
        return ''
    return value[:16384]


def _decoded(value):
    value = _source_text(value).replace('&zwnbsp;', '')
    value = _unescape(value)
    return value.replace('\ufeff', '').replace('\u200b', '').replace('\u2060', '')


def _tone(value):
    value = _source_text(value).lower()
    if 'green' in value:
        return 'positive'
    if 'red' in value:
        return 'negative'
    if value in ('yellow', 'orange', 'gold', 'cream'):
        return 'highlight'
    if value in ('par', 'parsecondary', 'partertiary', 'brown', 'gray', 'grey'):
        return 'muted'
    return 'normal'


class _RichText(_HTMLParser):
    """Recognize a tiny native formatting subset and emit text-only spans."""
    def __init__(self, max_paragraphs):
        _HTMLParser.__init__(self)
        self.paragraphs = []
        self.spans = []
        self.tones = ['normal']
        self.suppressed = 0
        self.remaining = 8192
        self.max_paragraphs = max_paragraphs

    def paragraph(self):
        if self.spans and len(self.paragraphs) < self.max_paragraphs:
            self.spans[0]['text'] = self.spans[0]['text'].lstrip()
            self.spans[-1]['text'] = self.spans[-1]['text'].rstrip()
            spans = [span for span in self.spans if span['text']]
            if spans:
                self.paragraphs.append({'spans': spans})
        self.spans = []

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style', 'iframe', 'object'):
            self.suppressed += 1
        if self.suppressed:
            return
        if tag in ('br', 'p', 'div', 'li'):
            self.paragraph()
        elif tag in ('b', 'strong'):
            self.tones.append('highlight')
        elif tag == 'native-tone':
            tone = dict(attrs).get('value', 'normal')
            self.tones.append(tone if tone in ('normal', 'highlight', 'positive', 'negative', 'muted') else 'normal')
        elif tag == 'font':
            self.tones.append(_tone(dict(attrs).get('color', '')))

    def handle_endtag(self, tag):
        if tag in ('script', 'style', 'iframe', 'object') and self.suppressed:
            self.suppressed -= 1
            return
        if self.suppressed:
            return
        if tag in ('p', 'div', 'li'):
            self.paragraph()
        elif tag in ('b', 'strong', 'native-tone', 'font') and len(self.tones) > 1:
            self.tones.pop()

    def handle_data(self, data):
        if self.suppressed or self.remaining <= 0 or len(self.paragraphs) >= self.max_paragraphs:
            return
        for index, part in enumerate(re.split(r'\r?\n', data)):
            if index:
                self.paragraph()
            if len(self.paragraphs) >= self.max_paragraphs:
                return
            part = re.sub(r'[\x00-\x09\x0b-\x1f\x7f-\x9f]', ' ', part)
            part = re.sub(r'[ \t\r\f\v]+', ' ', part)[:self.remaining]
            self.remaining -= len(part)
            while part and len(self.spans) < 24:
                tone = self.tones[-1]
                if self.spans and self.spans[-1]['tone'] == tone and len(self.spans[-1]['text']) < 600:
                    take = min(len(part), 600 - len(self.spans[-1]['text']))
                    self.spans[-1]['text'] += part[:take]
                else:
                    take = min(600, len(part))
                    self.spans.append({'text': part[:take], 'tone': tone})
                part = part[take:]


def rich_text(value, max_paragraphs=24):
    value = _decoded(value)
    if not value or value.startswith('#') or re.search(r'%\([^)]+\)[A-Za-z]', value):
        return []
    value = re.sub(r'\{([A-Za-z0-9_]+)_Start\}',
                   lambda match: '<native-tone value="' + _tone(match.group(1)) + '">', value)
    value = re.sub(r'\{[A-Za-z0-9_]+_End\}', '</native-tone>', value)
    value = re.sub(r'\{[^{}]{0,120}\}', '', value)
    parser = _RichText(max_paragraphs)
    try:
        parser.feed(value)
        parser.close()
        parser.paragraph()
        return parser.paragraphs
    except Exception:
        return []


def _localized(key):
    try:
        from helpers import i18n
        value = i18n.makeString(key)
        return value if value != key else ''
    except Exception:
        return ''


def _shared_tooltip(skill):
    result = {'mode': 'maximum'}
    category = _key(_attr(skill, 'typeName'))
    if category:
        result['categoryKey'] = category
        label = _text(_localized('#tooltips:perkType/name/' + category), 100)
        if label:
            result['category'] = label
    details_source = _source_text(_attr(skill, 'altDescription')) + '\n\n' + _source_text(_attr(skill, 'altInfo'))
    if category == 'situational':
        details_source += '\n\n' + _source_text(_localized('#tooltips:perkType/info/situational'))
    details = rich_text(details_source)
    if details:
        result['details'] = details[:24]
    try:
        from gui.shared.tooltips.advanced import SKILL_MOVIES
        identifier = _key(_attr(skill, 'name'))
        if identifier and SKILL_MOVIES.get(identifier):
            result['mediaKey'] = 'skill:' + identifier
    except Exception:
        pass
    return result


class _XpCollector(object):
    """The native setter writes primitives here without creating a UI view."""
    def __init__(self):
        self.values = {}

    def setCurrentXpValue(self, value):
        self.values['current'] = value

    def setTotalXpValue(self, value):
        self.values['fullRequired'] = value

    def setDiscountValue(self, value):
        self.values['required'] = value

    def setSkillProgress(self, value):
        self.values['progress'] = value

    def setZeroSkillsCount(self, value):
        self.values['zeroSkillsCount'] = value

    def setIsLocked(self, value):
        self.values['isLocked'] = value

    def setIsMaxSkillLevel(self, value):
        self.values['isMaxSkillLevel'] = value


def _training_tooltip(skill, tankman, is_bonus, level):
    result = {'mode': 'current'}
    if _attr(skill, 'isZero') is True:
        note = rich_text(_localized('#crew:matrix/skillTooltip/zero/text'), 8)
        if note:
            result['zeroNote'] = note
        return result
    if is_bonus or level >= 100:
        return result
    try:
        names = tankman.descriptor.skills
        if not isinstance(names, (tuple, list)) or len(names) > 24:
            return result
        identifier = _attr(skill, 'name')
        index = names.index(identifier)
        from gui.impl.lobby.crew.crew_helpers.model_setters import setSkillProgressionModel
        collector = _XpCollector()
        setSkillProgressionModel(collector, tankman, index, False)
        values = collector.values
        for key in ('current', 'required', 'fullRequired'):
            if type(values.get(key)) not in _INTS or not 0 <= values[key] <= 10 ** 12:
                return result
        if not 0 <= values['current'] <= values['required'] <= values['fullRequired'] or not values['required']:
            return result
        if (_level(values.get('progress')) is None or
                _count(values.get('zeroSkillsCount')) is None or
                type(values.get('isLocked')) is not bool or type(values.get('isMaxSkillLevel')) is not bool):
            return result
        result['xp'] = values
        count = values['zeroSkillsCount']
        if count in (1, 2):
            note = rich_text(_localized('#crew:matrix/skillTooltip/main/available/discountLabel/' + _TEXT(count)), 8)
            if note:
                result['zeroNote'] = note
    except Exception:
        pass
    return result


def _context_flags(skill, tankman, vehicle, booster, irrelevant):
    result = {}
    try:
        from gui.impl.lobby.crew.tooltips.crew_perks_tooltip import CrewPerksTooltip
        context = type(str('NativeTooltipContext'), (object,), {})()
        context._skill, context._tankman, context._tankmanVehicle = skill, tankman, vehicle
        context._skillBooster, context._skillName, context._isIrrelevant = booster, skill.name, irrelevant
        for native, exported in (('_isGroupSkill', 'isGroupSkill'),
                                 ('_isGroupSkillHasLowEff', 'hasLowEfficiencyMember'),
                                 ('_isGroupSkillHasUntrained', 'hasUntrainedMember')):
            method = getattr(CrewPerksTooltip, native)
            function = getattr(method, 'im_func', getattr(method, '__func__', method))
            result[exported] = bool(function(context))
        method = CrewPerksTooltip._getBoosterType
        function = getattr(method, 'im_func', getattr(method, '__func__', method))
        native_type = function(context)
        booster_type = _key(_attr(native_type, 'value', native_type))
        if booster_type:
            result['boosterType'] = booster_type
    except Exception:
        pass
    return result


def _skill_rows(snapshot):
    for vehicle in snapshot.get('vehicles', []):
        for field in ('crew', 'lastCrew'):
            for member in vehicle.get(field, []):
                for skill in member.get('skills', []):
                    yield skill


def compact_tooltip_shorts(snapshot):
    """Losslessly share repeated current text, preserving explicit context.

    Only rendered text/tones determine a reference. No member IDs, training
    indices or vehicle assignments enter hashes. Collisions and full variant
    tables retain inline text. Input snapshots are never mutated.
    """
    counts = {}
    for skill in _skill_rows(snapshot):
        tooltip = skill.get('tooltip') or {}
        short = tooltip.get('short')
        if tooltip.get('mode') != 'current' or not isinstance(short, list) or not short:
            continue
        canonical = json.dumps(short, ensure_ascii=True, sort_keys=True, separators=(',', ':'), allow_nan=False)
        key = (skill.get('id'), canonical)
        counts[key] = counts.get(key, 0) + 1
    repeated = {key for key, count in counts.items() if count > 1}
    if not repeated:
        return snapshot
    result = copy.deepcopy(snapshot)
    catalog = {row['id']: row for row in result.get('crewSkillCatalog', [])}
    references = {}
    for identifier, canonical in sorted(repeated):
        definition = catalog.get(identifier)
        if definition is None:
            continue
        tooltip = definition.setdefault('tooltip', {'mode': 'maximum'})
        variants = tooltip.setdefault('shortVariants', {})
        digest = hashlib.sha256(canonical.encode('utf-8')).hexdigest()[:16]
        short = json.loads(canonical)
        if digest in variants:
            if variants[digest] != short:
                continue
        elif len(variants) < 64:
            variants[digest] = short
        else:
            continue
        references[(identifier, canonical)] = digest
    if not references:
        return snapshot
    for skill in _skill_rows(result):
        tooltip = skill.get('tooltip') or {}
        short = tooltip.get('short')
        if tooltip.get('mode') != 'current' or not isinstance(short, list) or not short:
            continue
        canonical = json.dumps(short, ensure_ascii=True, sort_keys=True, separators=(',', ':'), allow_nan=False)
        digest = references.get((skill.get('id'), canonical))
        if digest:
            del tooltip['short']
            tooltip['shortKey'] = digest
    return result


def _attr(value, key, default=None):
    try:
        return getattr(value, key, default)
    except Exception:
        return default


def _text(value, limit=650):
    value = _decoded(value)
    value = re.sub(r'<[^<>]*>', ' ', value[:8192])
    value = re.sub(r'\{[A-Za-z0-9_]+_(?:Start|End)\}', '', value)
    value = ' '.join(re.sub(r'[\x00-\x1f\x7f-\x9f]', ' ', value).split())
    # Unresolved localization/template text is not a description of an effect.
    if re.search(r'%\([^)]+\)[A-Za-z]|\{[^{}]+\}', value) or value.startswith('#'):
        return ''
    return value[:limit]


def _key(value):
    value = _text(value, 81)
    return value if _ID.match(value) else None


def _count(value, maximum=24):
    return value if type(value) in _INTS and 0 <= value <= maximum else None


def _level(value):
    if (type(value) in _NUMBERS and 0 <= value <= 100 and
            not (isinstance(value, float) and (math.isnan(value) or math.isinf(value)))):
        return value
    return None


def _effects(params):
    result = []
    for row in itertools.islice(params.get('kpiArgs') or [], 4):
        if not isinstance(row, (list, tuple)) or len(row) != 3:
            continue
        value, text = _text(row[0], 80), _text(row[1], 160)
        label = (text + ': ' + value).strip(': ') if text and value else text or value
        if label:
            result.append(label[:200])
    return result


def _definition(skill):
    identifier = _key(_attr(skill, 'name'))
    name = _text(_attr(skill, 'userName'), 100)
    if not identifier or not name:
        return None
    result = {'id': identifier, 'name': name, 'iconKey': 'skill:' + identifier}
    tooltip = _shared_tooltip(skill)
    role = _key(_attr(skill, 'roleType'))
    if role:
        result['role'] = role
    try:
        from gui.impl.lobby.crew.crew_helpers.skill_helpers import getSkillParams, formatDescription
        params = getSkillParams(None, None, None, skill, identifier, 100, False)
        maximum_source = formatDescription(_attr(skill, 'maxLvlDescription', ''), params.get('keyArgs', {}))
        maximum = _text(maximum_source, 900)
        short = rich_text(maximum_source, 8)
        if short:
            tooltip['short'] = short
        general = _text(formatDescription(_attr(skill, 'description', ''), params.get('keyArgs', {})), 900)
        if general:
            result['description'] = general
        if maximum:
            result['maxDescription'] = maximum
        effects = _effects(params)
        if effects:
            result['effects'] = effects
    except Exception:
        # Static text is useful only if the game left no unexpanded arguments.
        general = _text(_attr(skill, 'description'), 900)
        if general:
            result['description'] = general
    if len(tooltip) > 1:
        result['tooltip'] = tooltip
    return result


def _remember(skill, catalog):
    identifier = _key(_attr(skill, 'name'))
    if not identifier or identifier in catalog or len(catalog) >= MAX_CATALOG:
        return catalog.get(identifier)
    canonical = skill
    try:
        from gui.shared.gui_items.tankman_skill import getTankmanSkill
        canonical = getTankmanSkill(identifier, _attr(skill, 'skillRole') or 'commander')
    except Exception:
        pass
    definition = _definition(canonical)
    if definition:
        catalog[identifier] = definition
    return definition


def prime_crew_catalog(catalog):
    """Read every native active perk, including the innate commander feature."""
    try:
        from items.components.skills_constants import ACTIVE_SKILLS
        from gui.shared.gui_items.tankman_skill import getTankmanSkill
        for identifier in sorted(ACTIVE_SKILLS)[:MAX_CATALOG]:
            if _key(identifier) and identifier not in catalog:
                _remember(getTankmanSkill(identifier, 'commander'), catalog)
    except Exception:
        pass


def _learned(skill, tankman, vehicle, is_bonus, role, catalog):
    definition = _remember(skill, catalog)
    level = _level(_attr(skill, 'level'))
    if definition is None or level is None:
        return None
    result = {'id': definition['id'], 'name': _text(_attr(skill, 'userName'), 100) or definition['name'],
              'iconKey': definition['iconKey'], 'level': level, 'isBonus': bool(is_bonus)}
    icon = _key(_attr(skill, 'extensionLessIconName'))
    if icon:
        result['iconKey'] = 'skill:' + icon
    for source, target in (('isZero', 'isZero'), ('isSkillActive', 'isActive')):
        value = _attr(skill, source)
        if type(value) is bool or type(value) in _INTS and 0 <= value <= 3:
            result[target] = bool(value)
    role = _key(role or _attr(skill, 'skillRole'))
    if role:
        result['role'] = role
    tooltip = _training_tooltip(skill, tankman, is_bonus, level)
    if len(tooltip) > 1:
        result['tooltip'] = tooltip
    if vehicle is None:
        return result
    # Use exactly the game's learned-perk tooltip path for current effects.
    # The stored training percentage above is independent of effective bonuses.
    if result.get('isActive') is False:
        return result
    try:
        from gui.shared.gui_items.Tankman import getBattleBooster, crewMemberRealSkillLevel
        from gui.impl.lobby.crew.crew_helpers.skill_helpers import getSkillParams, getSkillDescription, formatDescription
        identifier = definition['id']
        booster = getBattleBooster(vehicle, identifier)
        effective = crewMemberRealSkillLevel(vehicle, identifier, commonWithIncrease=True)
        if type(effective) not in _NUMBERS or not 0 < effective <= 1000:
            return result
        irrelevant = _attr(skill, 'isRelevant') is False or _attr(skill, 'isEnable') is False
        if irrelevant:
            return result
        params = getSkillParams(tankman, vehicle, booster, skill, identifier, effective, False, irrelevant, is_bonus)
        source = formatDescription(getSkillDescription(
            tankman, skill, effective, booster, False, False, irrelevant), params.get('keyArgs', {}))
        description = _text(source)
        short = rich_text(source, 8)
        if short:
            tooltip['short'] = short
        context = _context_flags(skill, tankman, vehicle, booster, irrelevant)
        if context:
            tooltip['context'] = context
        if len(tooltip) > 1:
            result['tooltip'] = tooltip
        if description and description not in (definition.get('description'), definition.get('maxDescription')):
            result['description'] = description
        effects = _effects(params)
        if effects:
            result['effects'] = effects
    except Exception:
        pass
    return result


def collect_crew_skills(tankman, vehicle, catalog):
    """Copy learned/bonus skills, shared definitions and authoritative counts."""
    result = {}
    role = _key(_attr(tankman, 'role'))
    if role:
        result['roleKey'] = role
    try:
        roles = [_key(value) for value in itertools.islice(tankman.roles(), 5)]
        if roles and all(roles):
            result['roles'] = [value for index, value in enumerate(roles) if value not in roles[:index]]
    except Exception:
        pass
    learned = []
    seen = set()
    major = list(itertools.islice(_attr(tankman, 'skills') or [], MAX_SKILLS))
    bonus = _attr(tankman, 'bonusSkills')
    sources = [(skill, False, _attr(tankman, 'role')) for skill in major]
    if isinstance(bonus, dict):
        for role in sorted(bonus):
            for skill in itertools.islice(bonus[role] or [], 3):
                if skill is not None:
                    sources.append((skill, True, role))
    for skill, is_bonus, role in sources[:MAX_SKILLS]:
        identifier = (_key(_attr(skill, 'name')), bool(is_bonus), _key(role))
        if identifier in seen:
            continue
        seen.add(identifier)
        row = _learned(skill, tankman, vehicle, is_bonus, role, catalog)
        if row:
            learned.append(row)
    if learned:
        result['skills'] = learned
    try:
        possible = tankman.getPossibleSkillsByRole()
        if isinstance(possible, dict):
            for role in sorted(possible):
                for skill in itertools.islice(possible[role] or [], MAX_CATALOG):
                    _remember(skill, catalog)
    except Exception:
        pass
    try:
        from constants import NEW_PERK_SYSTEM
        capacity = _count(NEW_PERK_SYSTEM.MAX_MAJOR_PERKS, 24)
        selected = _count(_attr(tankman, 'skillsCount'), 24)
        if capacity is not None:
            result['skillSlots'] = capacity
            if selected is not None and selected <= capacity:
                result['remainingSkillSlots'] = capacity - selected
        new = _attr(tankman, 'newSkillsCount')
        free = _count(_attr(tankman, 'newFreeSkillsCount'), 24)
        if isinstance(new, (tuple, list)) and len(new) == 2:
            earned = _count(new[0], 24)
            if earned is not None and free is not None and earned + free <= 24:
                result['freeSkillSlots'] = earned + free
        levels = _attr(tankman, 'bonusSlotsLevels')
        available = _attr(tankman, 'newBonusSkillsCountByRole')
        bonus_capacity = _count(NEW_PERK_SYSTEM.MAX_BONUS_SKILLS_PER_ROLE, 12)
        if isinstance(bonus, dict) and isinstance(levels, (list, tuple)) and bonus_capacity is not None:
            if len(levels) <= bonus_capacity and all(value is None or _level(value) is not None for value in levels):
                slots = []
                for role in sorted(bonus)[:5]:
                    key = _key(role)
                    if not key:
                        continue
                    row = {'role': key, 'capacity': bonus_capacity, 'levels': list(levels)}
                    selected_bonus = len([skill for skill in itertools.islice(bonus[role] or [], bonus_capacity)
                                          if skill is not None])
                    if selected_bonus <= bonus_capacity:
                        row['remaining'] = bonus_capacity - selected_bonus
                    count = _count(available.get(role), bonus_capacity) if isinstance(available, dict) else None
                    if count is not None:
                        row['available'] = count
                    slots.append(row)
                if slots:
                    result['bonusSkillSlots'] = slots
    except Exception:
        pass
    return result
