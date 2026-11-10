"""Native campaign activation is distinct from remembered quest selection."""
import json
import os
import sys
import types
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'source'))
import mod_grz_hangar_sync as mod


class Namespace(object):
    def __init__(self, **values):
        self.__dict__.update(values)


class OperationQuest:
    def __init__(self, identifier, operation, chain=1, selected=False, completed=False):
        self.identifier = identifier
        self.operation = operation
        self.chain = chain
        self.selected = selected
        self.completed = completed
        self.isOnPause = False
        self.disabled = False

    def getID(self):
        return self.identifier

    def getCampaignID(self):
        return self.operation.campaign

    def getOperationID(self):
        return self.operation.identifier

    def getChainID(self):
        return self.chain

    def getQuestBranchName(self):
        return self.operation.branch

    def isInProgress(self):
        return self.selected

    def isCompleted(self):
        return self.completed

    def isFullCompleted(self):
        return self.completed

    def isDisabled(self):
        return self.disabled

    def isAvailableToPerform(self):
        return not self.completed and not self.disabled


class Operation:
    def __init__(self, identifier, campaign, branch, branch_id):
        self.identifier = identifier
        self.campaign = campaign
        self.branch = branch
        self.branch_id = branch_id
        self.quests = {}
        self.actual = []
        self.paused = False
        self.disabled = False
        self.unlocked = True

    def getCampaignID(self):
        return self.campaign

    def getBranchName(self):
        return self.branch

    def getBranch(self):
        return self.branch_id

    def getUserName(self):
        return 'Synthetic operation %d' % self.identifier

    def getIconID(self):
        return 'tile_%d_1' % self.identifier

    def getChainName(self, chain_id):
        return 'Synthetic chain %d' % chain_id

    def getChainClassifier(self, _):
        return Namespace(classificationAttr='Assault')

    def getQuests(self):
        return self.quests

    def isActive(self):
        return any(quest.selected for chain in self.quests.values() for quest in chain.values())

    def isPaused(self):
        return self.paused

    def isDisabled(self):
        return self.disabled

    def isUnlocked(self):
        return self.unlocked

    def isAvailable(self):
        return Namespace(isValid=self.unlocked and not self.disabled)

    def isCompleted(self):
        return False

    def isFullCompleted(self):
        return False

    def isWithoutAwardListBranch(self):
        return self.branch == 'pm3'

    def getTotalPmPointsCount(self):
        return 0

    def getMaxPmPointsCount(self):
        return 125


class PersonalOperationTests(unittest.TestCase):
    def setUp(self):
        self.operations = {1: Operation(1, 1, 'regular', 0),
                           8: Operation(8, 3, 'pm3', 4),
                           11: Operation(11, 4, 'pm4', 8)}
        self.quests = {}
        self.active_branches = {'pm3'}
        self.personal = Namespace(
            isQuestsProgressSynced=lambda: True,
            getAllOperations=lambda _: self.operations,
            getAllCampaigns=lambda _: {
                key: Namespace(getUserName=lambda key=key: 'Synthetic campaign %d' % key)
                for key in (1, 3, 4)},
            getAllQuests=lambda _: self.quests,
            isCampaignActive=lambda branch: branch in self.active_branches,
            getActualQuests=lambda branch, operation: self.operations[operation].actual)
        self.cache = Namespace(getPersonalMissions=lambda: self.personal)
        previous_module = sys.modules.get('personal_missions')
        native_module = types.ModuleType('personal_missions')
        native_module.PM_BRANCH = Namespace(ALL_NAMES=('regular', 'pm3', 'pm4'))
        sys.modules['personal_missions'] = native_module
        self.addCleanup(self.restore_module, previous_module)
        previous_row = mod._quest_row
        mod._quest_row = lambda quest, **_: {
            'id': str(quest.getID()), 'title': 'Synthetic objective', 'description': '',
            'completed': quest.isCompleted(), 'requirements': [], 'rewards': [], 'missing': []}
        self.addCleanup(setattr, mod, '_quest_row', previous_row)

    @staticmethod
    def restore_module(previous):
        if previous is None:
            sys.modules.pop('personal_missions', None)
        else:
            sys.modules['personal_missions'] = previous

    def quest(self, identifier, operation_id, **kwargs):
        operation = self.operations[operation_id]
        quest = OperationQuest(identifier, operation, **kwargs)
        self.quests[identifier] = quest
        operation.quests.setdefault(quest.chain, {})[identifier] = quest
        return quest

    def test_paused_legacy_selection_does_not_become_currently_active(self):
        legacy = self.quest(101, 1, selected=True)
        current = self.quest(801, 8, selected=True)
        self.operations[1].paused = True
        self.operations[1].actual = [legacy]
        self.operations[8].actual = [current]
        bucket = mod._personal_mission_bucket(self.cache)
        quests = {row['id']: row for row in bucket['items']}
        operations = {row['id']: row for row in bucket['operations']}
        self.assertTrue(quests['101']['selected'])
        self.assertFalse(quests['101']['campaignActive'])
        self.assertTrue(quests['101']['paused'])
        self.assertFalse(quests['101']['active'])
        self.assertFalse(operations['1']['active'])
        self.assertTrue(quests['801']['active'])
        self.assertTrue(operations['8']['active'])
        self.assertEqual(quests['801']['operationId'], '8')
        self.assertEqual(quests['801']['campaignId'], '3')
        self.assertEqual(quests['801']['branch'], 'pm3')
        self.assertEqual(quests['801']['iconKey'], 'operation:8')

    def test_unknown_campaign_or_pause_state_never_asserts_active(self):
        self.quest(801, 8, selected=True)
        self.personal.isCampaignActive = lambda _: None
        bucket = mod._personal_mission_bucket(self.cache)
        self.assertIsNone(bucket['items'][0]['campaignActive'])
        self.assertFalse(bucket['items'][0]['active'])
        self.personal.isCampaignActive = lambda _: True
        self.operations[8].isPaused = lambda: None
        bucket = mod._personal_mission_bucket(self.cache)
        self.assertIsNone(bucket['items'][0]['paused'])
        self.assertFalse(bucket['items'][0]['active'])
        self.assertFalse(next(row for row in bucket['operations'] if row['id'] == '8')['active'])

    def test_locked_and_unselected_operations_are_in_catalog_without_quests(self):
        self.operations[11].unlocked = False
        bucket = mod._personal_mission_bucket(self.cache)
        self.assertEqual(bucket['items'], [])
        self.assertEqual(len(bucket['operations']), 3)
        locked = next(row for row in bucket['operations'] if row['id'] == '11')
        self.assertFalse(locked['unlocked'])
        self.assertFalse(locked['available'])
        self.assertFalse(locked['selected'])
        self.assertFalse(locked['active'])
        modern = next(row for row in bucket['operations'] if row['id'] == '8')
        self.assertEqual(modern['points'], {'current': 0, 'total': 125})
        self.assertEqual(modern['iconKey'], 'operation:8')
        self.assertEqual(bucket['operationsStatus'], 'ok')

    def test_native_actual_quests_come_before_flat_list_truncation(self):
        for identifier in range(100, 270):
            self.quest(identifier, 1, selected=True)
        self.operations[1].actual = [self.quests[100]]
        actual = self.quest(801, 8, selected=True)
        actual.isAvailableToPerform = lambda: False
        self.operations[8].actual = [actual]
        bucket = mod._personal_mission_bucket(self.cache)
        self.assertTrue(bucket['truncated'])
        self.assertEqual(len(bucket['items']), mod.MAX_MISSIONS)
        self.assertEqual(bucket['items'][0]['id'], '801')
        modern = next(row for row in bucket['operations'] if row['id'] == '8')
        self.assertEqual(modern['actualQuestIds'], ['801'])
        self.assertEqual(modern['chains'][0]['currentQuestId'], '801')

    def test_native_chain_progress_counts_and_current_id_are_not_inferred(self):
        first = self.quest(801, 8, completed=True)
        second = self.quest(802, 8, selected=True)
        self.quest(803, 8)
        self.operations[8].actual = [second]
        row = next(row for row in mod._personal_mission_bucket(self.cache)['operations'] if row['id'] == '8')
        self.assertEqual(row['chains'], [{
            'id': '1', 'name': 'Synthetic chain 1', 'category': 'Assault',
            'completed': 1, 'total': 3, 'currentQuestId': '802'}])
        first.isCompleted = lambda: None
        row = next(row for row in mod._personal_mission_bucket(self.cache)['operations'] if row['id'] == '8')
        self.assertIsNone(row['chains'][0]['completed'])
        self.assertEqual(row['chains'][0]['currentQuestId'], '802')

    def test_missing_actual_api_is_unknown_and_does_not_guess_current_quest(self):
        self.quest(801, 8, selected=True)
        del self.personal.getActualQuests
        row = next(row for row in mod._personal_mission_bucket(self.cache)['operations'] if row['id'] == '8')
        self.assertIsNone(row['actualQuestIds'])
        self.assertIsNone(row['chains'][0]['currentQuestId'])

    def test_native_failures_and_private_attributes_are_isolated(self):
        self.quest(801, 8, selected=True)
        self.operations[8].accountDBID = 999999999
        self.operations[8].private_token = 'synthetic-private-attribute'
        def rejected_classifier(_):
            raise RuntimeError('synthetic-private-error')
        self.operations[8].getChainClassifier = rejected_classifier
        bucket = mod._personal_mission_bucket(self.cache)
        text = json.dumps(bucket)
        self.assertNotIn('accountDBID', text)
        self.assertNotIn('private_token', text)
        self.assertNotIn('synthetic-private', text)
        row = next(row for row in bucket['operations'] if row['id'] == '8')
        self.assertIsNone(row['chains'][0]['category'])

    def test_operation_and_quest_pause_or_disable_always_prevent_active(self):
        quest = self.quest(801, 8, selected=True)
        quest.isOnPause = True
        self.assertFalse(mod._personal_mission_bucket(self.cache)['items'][0]['active'])
        quest.isOnPause = False
        self.operations[8].disabled = True
        row = mod._personal_mission_bucket(self.cache)['items'][0]
        self.assertTrue(row['disabled'])
        self.assertFalse(row['active'])

    def test_unsynced_catalog_is_pending_and_not_known_empty(self):
        self.personal.isQuestsProgressSynced = lambda: False
        row = mod._personal_mission_bucket(self.cache)
        self.assertEqual(row['status'], 'pending')
        self.assertEqual(row['operationsStatus'], 'pending')
        self.assertEqual(row['operations'], [])


if __name__ == '__main__':
    unittest.main()
