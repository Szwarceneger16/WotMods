"""Synthetic season changes and fail-closed client API boundary tests."""
from __future__ import absolute_import, unicode_literals

import os
import types
import unittest

MODULE = os.path.join(os.path.dirname(__file__), '..', 'source', 'hangar_battle_pass.py')
bridge = types.ModuleType(str('hangar_battle_pass_test'))
with open(MODULE, 'rb') as source:
    eval(compile(source.read(), 'hangar_battle_pass.py', 'exec'), bridge.__dict__)


class Config(object):
    seasonID = 54

    def __init__(self, ids=(541, 542, 549, 540)):
        self.ids = list(ids)

    def getChapterIDs(self):
        return self.ids

    def getChapterExpireTimestamp(self, chapter_id):
        return 1800000300 if chapter_id == 549 else 0


class Controller(object):
    season = 54
    selected = 541
    levels = {541: [25, 70, 145], 542: [11, 35], 549: [17], 540: [31, 80]}
    counts = {541: 1, 542: 2, 549: 0, 540: 5}
    points = {541: 33, 542: 35, 549: 4, 540: 209}

    def getSeasonID(self):
        return self.season

    def getSeasonNum(self):
        return self.season

    def getSeasonStartTime(self):
        return 1800000000

    def getSeasonFinishTime(self):
        return 1800100000

    def isEnabled(self):
        return True

    def isActive(self):
        return True

    def getCurrentChapterID(self):
        return self.selected

    def getPostProgressionChapterID(self):
        return 540

    def getChapterIDs(self):
        return [541, 542, 540]

    def isExtraChapter(self, chapter_id):
        return chapter_id == 549

    def getLevelInChapter(self, chapter_id):
        return self.counts[chapter_id]

    def getMaxLevelInChapter(self, chapter_id):
        return 2147483647 if chapter_id == 540 else len(self.levels[chapter_id])

    def getPointsInChapter(self, chapter_id):
        return self.points[chapter_id]

    def getLevelsConfig(self, chapter_id):
        return self.levels[chapter_id]

    def isChapterCompleted(self, chapter_id):
        return chapter_id == 542

    def isBought(self, chapter_id):
        return chapter_id == 542


def collect(controller=None, config=None, localize=None):
    return bridge.collect_battle_pass(controller or Controller(), config or Config(),
                                      localize or (lambda key: 'Localized ' + key.rsplit('/', 1)[-1]))


def by_id(result, chapter_id):
    return next(row for row in result['chapters'] if row['id'] == str(chapter_id))


class BattlePassTests(unittest.TestCase):
    def test_variable_costs_and_completed_stage_semantics(self):
        result = collect()
        self.assertEqual(result['status'], 'ok')
        self.assertEqual(result['season']['id'], '54')
        row = by_id(result, 541)
        self.assertEqual((row['completedStages'], row['totalStages']), (1, 3))
        self.assertEqual((row['pointsInStage'], row['pointsToStage']), (8, 45))
        self.assertEqual((row['totalPoints'], row['maxPoints']), (33, 145))
        self.assertEqual(row['name'], 'Localized 541')
        self.assertTrue(row['active'])

    def test_expired_extra_is_not_lost_by_controller_navigation_filter(self):
        row = by_id(collect(), 549)
        self.assertEqual(row['kind'], 'extra')
        self.assertEqual(row['endsAt'], 1800000300)
        self.assertFalse(row['active'])
        self.assertEqual(row['totalStages'], 1)

    def test_complete_chapter_has_full_final_stage_and_improved_flag(self):
        row = by_id(collect(), 542)
        self.assertEqual((row['pointsInStage'], row['pointsToStage']), (24, 24))
        self.assertTrue(row['completed'])
        self.assertTrue(row['improved'])

    def test_repeatable_post_progression_has_no_fake_completion_target(self):
        row = by_id(collect(), 540)
        self.assertEqual(row['kind'], 'post_progression')
        self.assertEqual(row['completedStages'], 5)
        self.assertEqual((row['pointsInStage'], row['pointsToStage']), (18, 49))
        self.assertIsNone(row['totalStages'])
        self.assertIsNone(row['maxPoints'])
        self.assertIsNone(row['completed'])

    def test_next_season_replaces_identifiers_costs_and_names_without_retained_state(self):
        collect()
        controller, config = Controller(), Config([903])
        config.seasonID = controller.season = 90
        controller.selected = 903
        controller.levels = {903: [13, 22, 99, 120]}
        controller.counts, controller.points = {903: 2}, {903: 30}
        result = collect(controller, config)
        self.assertEqual(result['season']['id'], '90')
        self.assertEqual([x['id'] for x in result['chapters']], ['903'])
        row = result['chapters'][0]
        self.assertEqual((row['pointsInStage'], row['pointsToStage']), (8, 77))
        self.assertEqual(row['totalStages'], 4)

    def test_missing_apis_are_null_and_partial_not_zero(self):
        controller = Controller()
        controller.getPointsInChapter = lambda _: None
        result = collect(controller)
        self.assertEqual(result['status'], 'partial')
        self.assertIsNone(by_id(result, 541)['totalPoints'])
        self.assertIsNone(by_id(result, 541)['pointsInStage'])

    def test_no_season_and_absent_controller_are_explicit(self):
        self.assertEqual(bridge.collect_battle_pass(None)['status'], 'unavailable')
        controller = Controller()
        controller.season = 0
        self.assertEqual(collect(controller)['status'], 'pending')
        controller.isEnabled = lambda: False
        self.assertEqual(collect(controller)['status'], 'inactive')

    def test_rollover_cannot_mix_old_account_and_new_config(self):
        controller = Controller()
        controller.season = 99
        result = collect(controller)
        self.assertEqual(result, bridge._empty('pending'))

    def test_selected_chapter_must_belong_to_this_season(self):
        controller = Controller()
        controller.selected = 111
        self.assertEqual(collect(controller)['status'], 'pending')

    def test_missing_localization_is_null_not_raw_resource_key(self):
        result = collect(localize=lambda key: key)
        self.assertIsNone(result['chapters'][0]['name'])
        result = collect(localize=lambda key: '<b>Chapter</b>\x00')
        self.assertEqual(result['chapters'][0]['name'], 'Chapter')

    def test_unknown_selection_is_not_reported_as_inactive(self):
        controller = Controller()
        controller.selected = None
        result = collect(controller)
        self.assertIsNone(result['activeChapterId'])
        self.assertIsNone(result['chapters'][0]['active'])
        self.assertEqual(result['status'], 'partial')

    def test_lazy_adapter_reports_pending_until_account_cache_is_ready(self):
        original = bridge._game_sources
        try:
            bridge._game_sources = lambda: (None, None, None)
            self.assertEqual(bridge.collect_battle_pass()['status'], 'pending')

            def unavailable():
                raise ImportError('synthetic_missing_client')

            bridge._game_sources = unavailable
            self.assertEqual(bridge.collect_battle_pass()['status'], 'unavailable')
        finally:
            bridge._game_sources = original

    def test_broken_configuration_property_is_pending(self):
        class BrokenConfig(object):
            @property
            def seasonID(self):
                raise RuntimeError('synthetic_unready_config')
        self.assertEqual(bridge.collect_battle_pass(Controller(), BrokenConfig())['status'], 'pending')

    def test_explicit_no_selection_is_false_for_each_chapter(self):
        controller = Controller()
        controller.selected = 0
        result = collect(controller)
        self.assertIsNone(result['activeChapterId'])
        self.assertTrue(all(x['active'] is False for x in result['chapters']))

    def test_config_fallback_is_partial_and_bounded(self):
        self.assertEqual(bridge.collect_battle_pass(Controller())['status'], 'partial')
        result = collect(config=Config(range(1, bridge.MAX_CHAPTERS + 2)))
        self.assertEqual(result['status'], 'partial')
        self.assertLessEqual(len(result['chapters']), bridge.MAX_CHAPTERS)

    def test_malformed_costs_and_values_never_escape(self):
        controller = Controller()
        controller.getLevelProgression = lambda _: (999, 1)
        controller.getLevelsConfig = lambda _: [50, 20]
        result = collect(controller)
        self.assertEqual(result['status'], 'partial')
        self.assertIsNone(by_id(result, 541)['pointsInStage'])
        self.assertIsNone(by_id(result, 541)['maxPoints'])
        controller.getPointsInChapter = lambda _: True
        self.assertIsNone(by_id(collect(controller), 541)['totalPoints'])

    def test_snapshot_contains_only_allowlisted_fields_and_no_private_attributes(self):
        controller = Controller()
        controller.accountKey = 'synthetic-private-field'
        controller.token = 'synthetic-private-field'
        result = collect(controller)
        self.assertNotIn('synthetic-private-field', repr(result))
        self.assertEqual(set(result), {'schemaVersion', 'status', 'season', 'activeChapterId', 'chapters'})

    def test_disabled_feature_retains_observed_values_but_marks_inactive(self):
        controller = Controller()
        controller.isActive = lambda: False
        result = collect(controller)
        self.assertEqual(result['status'], 'inactive')
        self.assertEqual(by_id(result, 541)['totalPoints'], 33)


if __name__ == '__main__':
    unittest.main()
