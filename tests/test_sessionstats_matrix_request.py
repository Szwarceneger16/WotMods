import copy
import json
import unittest
from unittest.mock import Mock

from scripts.sessionstats.matrix_request import HARNESS, MatrixRequestError, plan


REPOSITORY = 'Example/WotMods'
ROOT = '/repos/' + REPOSITORY
PR_SHA = 'b' * 40
CONTENT = ROOT + '/contents/' + HARNESS
PERMISSION = ROOT + '/collaborators/reviewer/permission'
PULL = ROOT + '/pulls/17'


class MatrixRequestTests(unittest.TestCase):
    def setUp(self):
        self.repository = {
            'id': 11,
            'full_name': REPOSITORY,
            'owner': {'id': 20, 'login': 'Example', 'type': 'User'},
        }
        self.event = {
            'action': 'created',
            'repository': self.repository,
            'issue': {'number': 17, 'pull_request': {'url': 'ignored'}},
            'comment': {
                'body': '/sessionstats-matrix',
                'author_association': 'COLLABORATOR',
                'user': {'id': 23, 'login': 'reviewer', 'type': 'User'},
            },
        }
        self.responses = {
            PERMISSION: {'permission': 'write', 'user': {'id': 23}},
            PULL: {
                'number': 17, 'state': 'open',
                'base': {'repo': copy.deepcopy(self.repository)},
                'head': {'repo': copy.deepcopy(self.repository), 'sha': PR_SHA},
            },
            CONTENT + '?ref=' + PR_SHA: {'path': HARNESS, 'type': 'file'},
        }
        self.get = Mock(side_effect=lambda route: self.responses.get(route, {}))

    def resolve(self, event_name='issue_comment'):
        return plan(event_name, self.event, REPOSITORY, self.get)

    def test_comments_choose_coverage_and_resolve_the_open_pull_request_sha(self):
        for suffix, coverage, count in (('', 'exhaustive', 64), (' full', 'full', 16), (' smoke', 'smoke', 1)):
            with self.subTest(coverage=coverage):
                self.get.reset_mock()
                self.event['comment']['body'] = '/sessionstats-matrix' + suffix
                result = self.resolve()
                self.assertEqual(result, {
                    'coverage': coverage, 'target_sha': PR_SHA, 'pr_number': '17',
                    'shard_count': str(count), 'shards': json.dumps(list(range(1, count + 1)), separators=(',', ':')),
                })
                self.assertEqual([c.args[0] for c in self.get.call_args_list],
                                 [PERMISSION, PULL, CONTENT + '?ref=' + PR_SHA])

    def test_owner_is_verified_using_repository_owner_id_and_login(self):
        self.event['comment']['author_association'] = 'OWNER'
        self.event['comment']['user'] = {'id': 20, 'login': 'example', 'type': 'User'}
        self.assertEqual(self.resolve()['target_sha'], PR_SHA)
        self.assertEqual([c.args[0] for c in self.get.call_args_list], [PULL, CONTENT + '?ref=' + PR_SHA])

    def test_claiming_owner_association_alone_does_not_bypass_authorization(self):
        self.event['comment']['author_association'] = 'OWNER'
        self.responses.pop(PERMISSION)
        with self.assertRaisesRegex(MatrixRequestError, 'require repository write access'):
            self.resolve()
        self.get.assert_called_once_with(PERMISSION)

    def test_read_or_triage_permissions_and_other_identity_are_denied(self):
        for permission, user_id in (('read', 23), ('triage', 23), ('none', 23), ('write', 20)):
            with self.subTest(permission=permission, user_id=user_id):
                self.get.reset_mock()
                self.responses[PERMISSION] = {'permission': permission, 'user': {'id': user_id}}
                with self.assertRaisesRegex(MatrixRequestError, 'require repository write access'):
                    self.resolve()
                self.get.assert_called_once_with(PERMISSION)

    def test_only_an_exact_created_command_on_a_pull_request_is_considered(self):
        original = self.event
        for path, key, value in (
            ('comment', 'body', '/sessionstats-matrix\nrun something'),
            ('comment', 'body', '/sessionstats-matrix; unwanted'),
            ('comment', 'body', 'Use /sessionstats-matrix'),
            ('comment', 'author_association', 'CONTRIBUTOR'),
            ('issue', 'pull_request', None),
        ):
            with self.subTest(key=key, value=value):
                self.event = copy.deepcopy(original)
                self.event[path][key] = value
                self.assertEqual(self.resolve(), {})
        self.event = copy.deepcopy(original)
        self.event['comment']['user']['type'] = 'Bot'
        self.assertEqual(self.resolve(), {})
        self.event = copy.deepcopy(original)
        self.event['action'] = 'edited'
        self.assertEqual(self.resolve(), {})
        self.get.assert_not_called()

    def test_fork_and_deleted_head_are_denied_without_loading_the_harness(self):
        for repo in ({'id': 99, 'full_name': REPOSITORY}, None):
            with self.subTest(repo=repo):
                self.get.reset_mock()
                self.responses[PULL]['head']['repo'] = repo
                with self.assertRaisesRegex(MatrixRequestError, 'branch in this repository'):
                    self.resolve()
                self.assertEqual([c.args[0] for c in self.get.call_args_list], [PERMISSION, PULL])

    def test_closed_pull_request_is_denied(self):
        self.responses[PULL]['state'] = 'closed'
        with self.assertRaisesRegex(MatrixRequestError, 'requires an open pull request'):
            self.resolve()
        self.assertEqual([c.args[0] for c in self.get.call_args_list], [PERMISSION, PULL])

    def test_invalid_target_sha_does_not_reach_the_contents_api(self):
        self.responses[PULL]['head']['sha'] = PR_SHA + '\nother=value'
        with self.assertRaisesRegex(MatrixRequestError, 'valid commit SHA'):
            self.resolve()
        self.assertEqual([c.args[0] for c in self.get.call_args_list], [PERMISSION, PULL])

    def test_missing_matrix_harness_has_a_clear_error(self):
        self.responses.pop(CONTENT + '?ref=' + PR_SHA)
        with self.assertRaisesRegex(MatrixRequestError, 'no Chromium matrix harness'):
            self.resolve()

    def test_dispatch_or_labels_do_not_request_a_matrix(self):
        self.assertEqual(self.resolve('workflow_dispatch'), {})
        self.assertEqual(self.resolve('pull_request'), {})
        self.get.assert_not_called()

    def test_wrong_repository_makes_no_api_requests(self):
        self.repository['full_name'] = 'Another/WotMods'
        with self.assertRaisesRegex(MatrixRequestError, 'event repository could not be verified'):
            self.resolve()
        self.get.assert_not_called()


if __name__ == '__main__':
    unittest.main()
