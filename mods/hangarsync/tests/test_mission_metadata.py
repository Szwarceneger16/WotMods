"""Native mission metadata keeps localized labels and rejects image locations."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    'hangar_mission_metadata_test', ROOT / 'source' / 'hangar_mission_metadata.py')
metadata = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(metadata)


def model(name='credits', icon=None, label='Credits', value='500'):
    return types.SimpleNamespace(getName=lambda: name, getIcon=lambda: icon,
                                 getLabel=lambda: label, getValue=lambda: value)


def bonus(name='credits', visible=True, labels=None):
    return types.SimpleNamespace(getName=lambda: name, isShowInGUI=lambda: visible,
                                 formattedList=lambda: ['500 credits'] if labels is None else labels)


class MetadataTests(unittest.TestCase):
    def native(self, models):
        packer = types.SimpleNamespace(
            getPackers=lambda: {'credits': object()}, pack=mock.Mock(return_value=models))
        factories = {key: mock.Mock(return_value=packer) for key in (
            'getDefaultBonusPacker', 'getDailyMissionsBonusPacker',
            'getWeeklyMissionsBonusPacker', 'getPersonalMissionsBonusPacker')}
        native = types.SimpleNamespace(**factories, getLocalizedBonusName=lambda _: '')
        return mock.patch.dict(sys.modules, {
            'gui.shared.missions.packers': types.SimpleNamespace(bonus=native),
        }), packer, factories

    def test_native_quantity_label_and_icon_are_independent(self):
        patch, _, _ = self.native([model(label='<b>Kredyty</b>')])
        with patch:
            rows = metadata.reward_items(types.SimpleNamespace(
                getBonuses=lambda: [bonus(labels=['<b>500 Kredyty</b>'])]))
        self.assertEqual(rows, [{'label': '500 Kredyty', 'iconKey': 'reward:credits'}])

    def test_single_model_preserves_exact_legacy_display_text(self):
        patch, _, _ = self.native([model(label='Credits', value='500')])
        with patch:
            rows = metadata.reward_items(types.SimpleNamespace(
                getBonuses=lambda: [bonus(labels=['Credits: 500'])]))
        self.assertEqual(rows, [{'label': 'Credits: 500', 'iconKey': 'reward:credits'}])

    def test_ordinary_conditions_use_native_packers_with_post_battle_context(self):
        native_model = object()
        bonus_packer, post_packer = mock.Mock(), mock.Mock()
        quest = types.SimpleNamespace(postBattleCond=types.SimpleNamespace(
            getConditions=lambda: types.SimpleNamespace(items=[object()])))
        modules = {
            'gui.impl.gen.view_models.common.missions.conditions.condition_group_model':
                types.SimpleNamespace(ConditionGroupModel=lambda: native_model),
            'gui.shared.missions.packers.conditions': types.SimpleNamespace(
                getDefaultBonusCondPacker=lambda: bonus_packer,
                PostBattleConditionPacker=lambda: post_packer),
        }
        with mock.patch.dict(sys.modules, modules):
            self.assertIs(metadata.quest_conditions(quest, 'bonusCond'), native_model)
            self.assertIs(metadata.quest_conditions(quest, 'postBattleCond'), native_model)
            self.assertIsNone(metadata.quest_conditions(quest, 'vehicleReqs'))
        bonus_packer.packWithPostBattleCondCheck.assert_called_once_with(quest, native_model, True)
        post_packer.pack.assert_called_once_with(quest, native_model)

    def test_unavailable_native_condition_packer_returns_no_enrichment(self):
        with mock.patch.dict(sys.modules, {
                'gui.shared.missions.packers.conditions': types.SimpleNamespace()}):
            self.assertIsNone(metadata.quest_conditions(object(), 'bonusCond'))

    def test_native_icon_does_not_depend_on_localized_reward_words(self):
        patch, _, _ = self.native([model(name='blueprints', icon='poland',
                                         label='Blueprint fragments', value='3')])
        with patch:
            rows = metadata.reward_items(types.SimpleNamespace(getBonuses=lambda: [bonus()]))
        self.assertEqual(rows[0]['iconKey'], 'reward:poland')

    def test_paths_and_unknown_objects_are_never_serialized(self):
        for invalid in ('https://private.invalid/secret', '../secret.png', object()):
            patch, _, _ = self.native([model(icon=invalid)])
            with patch:
                rows = metadata.reward_items(types.SimpleNamespace(getBonuses=lambda: [bonus()]))
            self.assertEqual(rows[0]['iconKey'], 'reward:credits')
            self.assertIsNone(metadata.condition_icon({'iconID': invalid}))

    def test_hidden_and_unknown_bonuses_are_not_packed(self):
        patch, packer, _ = self.native([model()])
        with patch:
            self.assertEqual(metadata.reward_items(types.SimpleNamespace(
                getBonuses=lambda: [bonus(visible=False), bonus(name='private-token')])), [])
        packer.pack.assert_not_called()

    def test_native_factory_selection_and_condition_model(self):
        for category, personal, factory in (
                ('daily', False, 'getDailyMissionsBonusPacker'),
                ('weekly', False, 'getWeeklyMissionsBonusPacker'),
                (None, True, 'getPersonalMissionsBonusPacker'),
                ('crucible', False, 'getDefaultBonusPacker')):
            patch, _, factories = self.native([model()])
            with patch:
                metadata.reward_items(types.SimpleNamespace(getBonuses=lambda: []), category, personal)
            factories[factory].assert_called_once_with()
        self.assertEqual(metadata.condition_icon(types.SimpleNamespace(
            getIconKey=lambda: 'killVehicles')), 'condition:killVehicles')

    def test_rewards_are_bounded_and_premium_uses_native_day_count(self):
        patch, _, _ = self.native([model(name='premium_plus', label='Premium', value='3')] * 16)
        with patch:
            rows = metadata.reward_items(types.SimpleNamespace(getBonuses=lambda: [bonus()] * 32))
        self.assertEqual(len(rows), 48)
        self.assertEqual(rows[0], {'label': '3 Premium', 'iconKey': 'reward:premium_plus_3'})


if __name__ == '__main__':
    unittest.main()
