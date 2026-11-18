# -*- coding: utf-8 -*-
"""Copy native mission display metadata without reading or sending image bytes."""
from __future__ import absolute_import, unicode_literals

import itertools
import re

try:
    _TEXT = unicode
except NameError:
    _TEXT = str

_MAX_REWARDS = 48
_MAX_BONUSES = 32
_MAX_MODELS_PER_BONUS = 16
_KEY = re.compile(r'\A[A-Za-z0-9][A-Za-z0-9_-]{0,95}\Z')
_QUANTITY = re.compile(r'\A-?[0-9]+(?:\.[0-9]+)?\Z')
_PREMIUM_DAYS = frozenset(('1', '2', '3', '7', '14', '30', '90', '180', '360'))


def _call(value, name, *args):
    method = getattr(value, name, None)
    if callable(method):
        try:
            return method(*args)
        except Exception:
            pass
    return None


def _text(value):
    if isinstance(value, bytes) and not isinstance(value, _TEXT):
        value = value.decode('utf-8', 'replace')
    if not isinstance(value, _TEXT):
        return ''
    value = re.sub(r'<[^<>]*>', ' ', value[:8192])
    value = re.sub(r'[\x00-\x1f\x7f]+', ' ', value)
    value = ' '.join(value.split())
    if value.startswith('#') and not any(char.isspace() for char in value):
        return ''
    return value[:1400]


def _key(value):
    value = _text(value)
    return value if _KEY.match(value) else None


def condition_icon(model):
    """Return only the icon identifier supplied by a native condition formatter."""
    if isinstance(model, dict):
        key = _key(model.get('iconID'))
    else:
        key = _key(_call(model, 'getIconKey'))
    return 'condition:' + key if key else None


def quest_conditions(quest, scope):
    """Use the game's ordinary objective formatters, retaining their native tree."""
    if scope not in ('bonusCond', 'postBattleCond'):
        return None
    try:
        from gui.impl.gen.view_models.common.missions.conditions.condition_group_model import ConditionGroupModel
        from gui.shared.missions.packers.conditions import getDefaultBonusCondPacker, PostBattleConditionPacker
        model = ConditionGroupModel()
        if scope == 'bonusCond':
            post_battle = _call(getattr(quest, 'postBattleCond', None), 'getConditions')
            has_post_battle = bool(getattr(post_battle, 'items', None))
            getDefaultBonusCondPacker().packWithPostBattleCondCheck(quest, model, has_post_battle)
        else:
            PostBattleConditionPacker().pack(quest, model)
        return model
    except Exception:
        return None


def _packer(module, category, personal):
    if personal:
        factory = module.getPersonalMissionsBonusPacker
    elif category == 'weekly':
        factory = module.getWeeklyMissionsBonusPacker
    elif category in ('daily', 'daily_bonus', 'daily_epic'):
        factory = module.getDailyMissionsBonusPacker
    else:
        factory = module.getDefaultBonusPacker
    return factory()


def _model_reward(model, bonus, module, fallback_label):
    name = _key(_call(model, 'getName')) or _key(_call(bonus, 'getName'))
    icon = _key(_call(model, 'getIcon')) or name
    value = _text(_call(model, 'getValue'))
    label = fallback_label or _text(_call(model, 'getLabel')) or _text(_call(model, 'getUserName'))
    if not label and name:
        label = _text(_call(module, 'getLocalizedBonusName', name))
    if not label:
        return None
    if not fallback_label and value and value != label and _QUANTITY.match(value):
        label = (value + ' ' + label)[:1400]
    if name in ('premium', 'premium_plus') and value in _PREMIUM_DAYS and icon == name:
        icon = name + '_' + value
    result = {'label': label}
    if icon:
        result['iconKey'] = 'reward:' + icon
    return result


def reward_items(quest, category=None, personal=False, crucible=False):
    """Read bounded localized reward labels and native semantic icon names.

    The existing text rewards remain the fallback when a native packer is absent
    or cannot describe a reward. No tooltip, raw token, image path or image data
    is included in the result.
    """
    try:
        from gui.shared.missions.packers import bonus as native
        packer = _packer(native, category, personal)
        known_packers = packer.getPackers()
        bonuses = _call(quest, 'getBonuses') or []
        result = []
        for bonus in itertools.islice(bonuses, _MAX_BONUSES):
            if _call(bonus, 'isShowInGUI') is False:
                continue
            native_packer = known_packers.get(_call(bonus, 'getName'))
            if native_packer is None or _call(native_packer, 'isAsync'):
                continue
            try:
                models = list(itertools.islice(packer.pack(bonus) or [], _MAX_MODELS_PER_BONUS))
                try:
                    labels = [_text(item) for item in itertools.islice(
                        _call(bonus, 'formattedList') or [], _MAX_MODELS_PER_BONUS)]
                except Exception:
                    labels = []
                fallback = labels[0] if len(models) == len(labels) == 1 else ''
                for model in models:
                    row = _model_reward(model, bonus, native, fallback)
                    if row is not None:
                        result.append(row)
                        if len(result) == _MAX_REWARDS:
                            return result
            except Exception:
                continue
        return result
    except Exception:
        return []
