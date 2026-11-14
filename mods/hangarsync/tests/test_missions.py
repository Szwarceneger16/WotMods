"""Mission adapters and the shareable diagnostic log."""
import json
import logging
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest import mock

from test_hangar_sync import ROOT, mod


SECRET = 'sentinel-secret that must never be logged'


class AndGroup:
    def __init__(self, *items):
        self.items = items
        self.isNegative = False


class OrGroup(AndGroup):
    pass


class Counter:
    def getCustomDescription(self):
        return '<b>Damage dealt</b>'

    def getProgressPerGroup(self):
        return {None: (3, 5, 0, False), SECRET: (4, 5, 0, False)}


class Quest:
    def __init__(self, identifier, bonus=False):
        self.identifier = identifier
        self.bonus = bonus
        self.bonusCond = types.SimpleNamespace(
            getConditions=lambda: OrGroup(Counter(), Counter()))

    def getID(self):
        return self.identifier

    def getUserName(self):
        return 'Daily goal'

    def getDescription(self):
        return 'Complete the objective'

    def getConditionsDescription(self):
        return 'Deal damage'

    def isBonus(self):
        return self.bonus

    def isHidden(self):
        return False

    def isAvailable(self):
        return types.SimpleNamespace(isValid=True)

    def isCompleted(self):
        return False

    def getBonuses(self):
        return [types.SimpleNamespace(formattedList=lambda: ['<b>500 credits</b>'])]


class PersonalQuest(Quest):
    def getUserDescription(self):
        return 'Complete a personal objective'

    def isInProgress(self):
        return True

    def isFullCompleted(self):
        return False

    def isDisabled(self):
        return False

    def getMainQuestID(self):
        return 'primary'

    def getAddQuestID(self):
        return 'secondary'

    def getCampaignID(self):
        return 3

    def getOperationID(self):
        return 9

    def getChainID(self):
        return 1

    def getVehMinLevel(self):
        return 8

    def getVehMaxLevel(self):
        return 11


class MissionTests(unittest.TestCase):
    def test_packed_native_progress_preserves_zero_and_icon(self):
        model = types.SimpleNamespace(getDescrData=lambda: 'Damage', getTitleData=lambda: '',
            getCurrent=lambda: 0, getTotal=lambda: 3500, getIconKey=lambda: 'damage')
        self.assertEqual(mod._packed_condition(model, [48]), {
            'text': 'Damage', 'progress': {'current': 0, 'target': 3500},
            'iconKey': 'condition:damage'})

    def test_packed_native_default_does_not_invent_a_progress_target(self):
        model = types.SimpleNamespace(getDescrData=lambda: 'Objective', getTitleData=lambda: '',
            getCurrent=lambda: 0, getTotal=lambda: 0, getIconKey=lambda: '')
        self.assertEqual(mod._packed_condition(model, [48]), {'text': 'Objective'})

    def game_modules(self):
        challenge_iface, cache_iface = object(), object()
        conditions = types.SimpleNamespace(AndGroup=AndGroup, OrGroup=OrGroup,
                                           Cumulativable=Counter)
        self.quests = {key: Quest(key) for key in ('primary', 'secondary', 'stage-1')}
        self.quests['stage-1'].bonusCond = None
        self.quests['stage-1'].getConditionsDescription = lambda: ''
        operation = types.SimpleNamespace(getUserName=lambda: 'Fossa',
                                          getChainName=lambda _id: 'Vanguard')
        personal = types.SimpleNamespace(
            isQuestsProgressSynced=lambda: True,
            getAllQuests=lambda branches: {101: PersonalQuest(101)} if 'third' in branches else {},
            getAllCampaigns=lambda _: {3: types.SimpleNamespace(getUserName=lambda: 'Sector 3')},
            getAllOperations=lambda _: {9: operation})
        self.cache = types.SimpleNamespace(
            isStarted=True, waitForSync=False,
            getDailyQuests=lambda: {'a': Quest('a'), 'b': Quest('b', bonus=True)},
            getDailyEpicQuest=lambda: Quest('epic'),
            getWeeklyQuests=lambda: {'weekly': Quest('weekly')},
            getPremiumQuests=lambda: {'premium': Quest('premium')},
            getPersonalMissions=lambda: personal,
            getQuestByID=self.quests.get,
            getHiddenQuests=lambda predicate, makeRelations: {
                key: quest for key, quest in self.quests.items() if predicate(quest)})
        chain = types.SimpleNamespace(challengeID=4, attempts=3, finishTime=1794000000,
                                      questsIDs=['stage-1', 'stage-2'],
                                      difficulty=types.SimpleNamespace(value=2))
        self.controller = types.SimpleNamespace(
            isEnabled=True, activeChallengeID=4, getSortedChallenges=lambda: [chain],
            isChallengeCompleted=lambda _: False, getChallengeProgress=lambda _: {'quests': 1})
        helper = types.SimpleNamespace(
            dependency=types.SimpleNamespace(
                instance=lambda iface: self.cache if iface is cache_iface else self.controller))
        class ConditionGroupModel:
            def __init__(self):
                self.items = []
                self.kind = 'and'

            def getItems(self):
                return self.items

            def getConditionType(self):
                return self.kind

        class ChallengePacker:
            def pack(self, quest, model):
                alternatives = ConditionGroupModel()
                alternatives.kind = 'or'
                alternatives.items.append(types.SimpleNamespace(
                    getDescrData=lambda: '<b>Place first by damage</b>'))
                model.items.append(alternatives)

        return mock.patch.dict(sys.modules, {
            'helpers': helper,
            'gui.server_events': types.SimpleNamespace(conditions=conditions),
            'skeletons.gui.server_events': types.SimpleNamespace(IEventsCache=cache_iface),
            'skeletons.gui.challenges': types.SimpleNamespace(IChallengesController=challenge_iface),
            'personal_missions': types.SimpleNamespace(
                PM_BRANCH=types.SimpleNamespace(ALL_NAMES=('first', 'second', 'third'))),
            'gui.impl.gen.view_models.common.missions.conditions.condition_group_model':
                types.SimpleNamespace(ConditionGroupModel=ConditionGroupModel),
            'gui.shared.missions.packers.conditions':
                types.SimpleNamespace(ChallengePostBattleConditionPacker=ChallengePacker),
            'BattleReplay': types.SimpleNamespace(isPlaying=lambda: False),
        })

    def test_known_sources_and_crucible_missing_stage(self):
        with self.game_modules():
            buckets = mod.collect_missions()['categories']
        self.assertEqual(set(buckets), set(mod.MISSION_CATEGORIES))
        for key in ('daily', 'daily_bonus', 'daily_epic', 'premium', 'weekly', 'personal'):
            self.assertEqual(buckets[key]['status'], 'ok')
            self.assertEqual(len(buckets[key]['items']), 1)
        self.assertEqual(buckets['daily']['items'][0]['id'], 'a')
        self.assertEqual(buckets['daily_bonus']['items'][0]['id'], 'b')
        mission = buckets['personal']['items'][0]
        self.assertEqual(mission['operation'], 'Fossa')
        self.assertEqual(mission['series'], 'Vanguard')
        self.assertEqual(mission['rewards'], ['500 credits'])
        self.assertEqual([x['scope'] for x in mission['requirements']], ['primary', 'secondary'])
        condition = mission['requirements'][0]['groups'][0]['requirement']
        self.assertEqual(condition['operator'], 'any')
        self.assertEqual(condition['conditions'][0], {
            'text': 'Damage dealt', 'progress': {'current': 3, 'target': 5}})
        self.assertNotIn(SECRET, json.dumps(buckets))
        crucible = buckets['crucible']
        self.assertEqual(crucible['status'], 'partial')
        self.assertEqual(crucible['items'][0]['completedStages'], 0)
        stage = crucible['items'][0]['stages'][0]
        self.assertEqual(stage['stage'], 1)
        self.assertEqual(stage['missing'], [])
        self.assertEqual(stage['requirements'][0]['scope'], 'postBattleCond')
        post_battle = stage['requirements'][-1]['requirement']
        self.assertEqual(post_battle['conditions'][0], {
            'operator': 'any', 'negated': False, 'conditions': [{'text': 'Place first by damage'}]})
        self.assertIn('stage_unavailable', crucible['items'][0]['missing'])

    def test_ui_conditions_when_personal_linked_quests_have_no_details(self):
        formatter = mock.Mock()
        formatter.bodyFormat.side_effect = lambda is_main: [{
            'initData': {'description': 'Deal damage' if is_main else 'Win the battle',
                         'isInOrGroup': not is_main},
            'progressData': {'current': 2, 'goal': 5, 'details': SECRET},
        }]
        parser = mock.Mock(return_value=formatter)
        path = 'gui.server_events.personal_progress.formatters'
        with self.game_modules(), mock.patch.dict(sys.modules, {
                path: types.SimpleNamespace(PMCardConditionsFormatter=parser)}), \
             mock.patch.object(PersonalQuest, 'getConditionsConfig', return_value={'tasks': {}},
                               create=True):
            self.cache.getQuestByID = mock.Mock(return_value=None)
            mission = mod.collect_missions()['categories']['personal']['items'][0]
        self.cache.getQuestByID.assert_not_called()
        self.assertEqual(mission['missing'], [])
        primary, secondary = mission['requirements']
        self.assertEqual(primary['scope'], 'primary')
        self.assertEqual(primary['groups'][0]['requirement'],
                         {'text': 'Deal damage', 'progress': {'current': 2, 'target': 5}})
        self.assertEqual(secondary['scope'], 'secondary')
        self.assertTrue(secondary['groups'][0]['requirement']['alternative'])
        self.assertNotIn(SECRET, json.dumps(mission))

    def test_epic_description_is_the_visible_objective(self):
        with self.game_modules():
            epic = Quest('epic')
            epic.bonusCond = None
            epic.getConditionsDescription = lambda: ''
            self.cache.getDailyEpicQuest = lambda: epic
            bucket = mod.collect_missions()['categories']['daily_epic']
        self.assertEqual(bucket['status'], 'ok')
        self.assertEqual(bucket['items'][0]['conditionText'], 'Complete the objective')

    def test_mission_log_contains_counts_and_safe_errors_only(self):
        def reject():
            raise ValueError(SECRET)

        with tempfile.TemporaryDirectory() as base, self.game_modules():
            self.cache.getWeeklyQuests = reject
            self.quests['stage-1'].getDescription = lambda: SECRET
            game = types.SimpleNamespace(
                callback=mock.Mock(return_value=11), cancelCallback=mock.Mock(),
                player=lambda: types.SimpleNamespace(name=SECRET, arena=None))
            logger = logging.Logger('test.mission.diagnostics')
            self.assertTrue(mod.start_diagnostics({'APPDATA': base}, logger, mod.MISSION_LOG_FILE))
            try:
                with mock.patch.object(mod, 'MISSION_LOG', logger):
                    probe = mod.MissionDiagnostics(game)
                    probe.start()
                    probe.tick()
                    probe.stop()
            finally:
                for handler in logger.handlers:
                    handler.close()
            game.cancelCallback.assert_called_once_with(11)
            data = (Path(base) / mod.LOG_DIR / mod.MISSION_LOG_FILE).read_text()
        self.assertIn('category=weekly status=unavailable error_type=ValueError rows=0', data)
        self.assertIn('category=daily status=ok error_type=none rows=1', data)
        self.assertIn('missing_stages=1', data)
        self.assertIn('primary_conditions=1 secondary_conditions=1', data)
        self.assertNotIn(SECRET, data)
        self.assertNotIn('stage-1', data)
        self.assertNotIn('500 credits', data)
        self.assertNotIn('Fossa', data)
        self.assertNotIn('Traceback', data)

    def test_missing_and_invalid_config_start_local_probe_only(self):
        example = (ROOT / 'GRZ_Hangar_Sync.json.example').read_bytes()
        enabled = json.dumps(dict(json.loads(example), enabled=True, display_name='My Garage')).encode()
        for raw in (None, example, enabled, b'{}',
                    b'{"enabled":true,"mission_diagnostics":false}', b'broken'):
            with self.subTest(raw=raw), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / mod.CONFIG_FILE
                if raw is not None:
                    path.write_bytes(raw)
                game = types.SimpleNamespace(callback=mock.Mock(return_value=7),
                                             cancelCallback=mock.Mock())
                with mock.patch.dict(sys.modules, {'BigWorld': game}), \
                     mock.patch.object(mod, 'start_diagnostics', return_value=True), \
                     mock.patch.object(mod, 'config_path', return_value=path), \
                     mock.patch.object(mod, 'collect_game_snapshot') as capture, \
                     mock.patch.object(mod.SyncRuntime, 'start') as send:
                    try:
                        mod.init()
                        game.callback.assert_called_once()
                        capture.assert_not_called()
                        send.assert_not_called()
                        self.assertIsNone(mod._state)
                    finally:
                        mod.fini()
                game.cancelCallback.assert_called_once_with(7)

    def test_cache_warms_and_one_missing_controller_keeps_other_data(self):
        with self.game_modules():
            self.cache.waitForSync = True
            self.assertIsNone(mod.collect_missions())
            self.cache.waitForSync = False
            self.controller = None
            buckets = mod.collect_missions()['categories']
        self.assertEqual(buckets['crucible']['status'], 'pending')
        self.assertEqual(buckets['weekly']['status'], 'ok')

    def test_mission_changes_are_hashed_and_overflow_preserves_garage(self):
        baseline = {'capturedAt': '2026-11-03T00:00:00Z', 'vehicles': []}
        with_missions = dict(baseline, missions={'data': 'x' * 200})
        garage_payload, garage_digest = mod.encode_snapshot(baseline)
        payload, digest = mod.encode_snapshot(with_missions)
        self.assertNotEqual(garage_digest, digest)
        self.assertIn('missions', json.loads(payload))
        with mock.patch.object(mod, 'MAX_PAYLOAD_BYTES', 100), self.assertLogs(mod.LOG):
            self.assertEqual(mod.encode_snapshot(with_missions), (garage_payload, garage_digest))

    def test_template_requires_opt_in_for_mission_upload(self):
        config = mod.parse_config((ROOT / 'GRZ_Hangar_Sync.json.example').read_bytes())
        self.assertFalse(config['include_missions'])
        self.assertTrue(config['mission_diagnostics'])
        with self.assertRaises(mod.ConfigError):
            mod.parse_config(json.dumps(dict(config, mission_diagnostics='false')))


if __name__ == '__main__':
    unittest.main()
