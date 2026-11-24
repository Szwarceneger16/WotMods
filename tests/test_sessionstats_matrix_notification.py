import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts/sessionstats"))
from matrix_notification import publish


REPO = "example/WotMods"
RUN_API = f"repos/{REPO}/actions/runs/123"
COMMENTS_API = f"repos/{REPO}/issues/17/comments"
COMMENT_API = f"repos/{REPO}/issues/comments/900"
ARTIFACT_API = f"repos/{REPO}/actions/artifacts/567"
MARKER = "<!-- sessionstats-matrix-run:123:456:1 -->"
WORKFLOW = Path(__file__).resolve().parents[1] / ".github/workflows/sessionstats-matrix-command.yml"


class MatrixNotificationTests(unittest.TestCase):
    def setUp(self):
        self.env = {
            "GITHUB_REPOSITORY": REPO,
            "GITHUB_SERVER_URL": "https://github.com",
            "GITHUB_RUN_ID": "123",
            "GITHUB_RUN_ATTEMPT": "1",
            "PR_NUMBER": "17",
            "COMMAND_ID": "456",
            "COVERAGE": "full",
            "TARGET_SHA": "a" * 40,
            "REPORT_RESULT": "success",
            "ARTIFACT_ID": "567",
        }
        self.requests = []
        self.posted = []
        self.comments = {}

    def api(self, path, *args):
        self.requests.append((path, args))
        if args[:1] == ("--method",):
            method, body = args[1], args[3].removeprefix("body=")
            self.posted.append((method, path, body))
            if method == "POST":
                comment_id = 900 + len(self.comments)
            else:
                comment_id = int(path.rsplit("/", 1)[1])
                self.assertIn(comment_id, self.comments)
            comment = {"id": comment_id, "user": {"login": "github-actions[bot]"}, "body": body}
            self.comments[comment_id] = comment
            return comment
        if path == ARTIFACT_API:
            return {"id": 567, "name": "sessionstats-matrix-html-attempt-1", "expired": False,
                    "workflow_run": {"id": 123}}
        if path == f"{RUN_API}/attempts/{self.env['GITHUB_RUN_ATTEMPT']}/jobs?per_page=100":
            return {"jobs": [{"id": 789, "name": "Downloadable HTML matrix"}]}
        if path == f"{COMMENTS_API}?per_page=100":
            self.assertEqual(args, ("--paginate", "--slurp"))
            return [
                [{"id": 100, "user": {"login": "a-user"}, "body": MARKER},
                 {"id": 600, "user": {"login": "github-actions[bot]"}, "body": "<!-- sessionstats-matrix-run:111:456:1 -->"}],
                list(self.comments.values()),
            ]
        self.fail(f"Unexpected API request {path} {args}")

    def test_workflow_posts_once_and_updates_same_comment_through_pass(self):
        self.assertEqual(publish("started", self.env, self.api), 900)
        self.assertEqual(self.requests, [(COMMENTS_API, ("--method", "POST", "-f", f"body={self.posted[0][2]}"))])
        self.env["STATUS_COMMENT_ID"] = "900"
        self.assertEqual(publish("running", self.env, self.api), 900)
        self.assertEqual(publish("complete", self.env, self.api), 900)
        self.assertEqual([item[:2] for item in self.posted], [
            ("POST", COMMENTS_API), ("PATCH", COMMENT_API), ("PATCH", COMMENT_API)])
        for (_, _, body), status in zip(self.posted, ("Started", "Running", "Passed")):
            self.assertIn(f"— {status}.", body)
            self.assertIn(MARKER, body)
            self.assertIn("/actions/runs/123/attempts/1)", body)
        self.assertIn("/job/789)", self.posted[-1][2])
        self.assertIn("/artifacts/567)", self.posted[-1][2])

    def test_failure_keeps_actions_and_links_partial_html_if_available(self):
        self.env.update(REPORT_RESULT="failure", STATUS_COMMENT_ID="900")
        publish("complete", self.env, self.api)
        self.assertIn("— Failed.", self.posted[-1][2])
        self.assertIn("/artifacts/567)", self.posted[-1][2])
        self.env["ARTIFACT_ID"] = ""
        publish("complete", self.env, self.api)
        self.assertIn("— Failed.", self.posted[-1][2])
        self.assertIn("/actions/runs/123/attempts/1)", self.posted[-1][2])
        self.assertNotIn("/artifacts/", self.posted[-1][2])

    def test_failed_only_retry_posts_a_separate_result_and_preserves_the_failed_comment(self):
        self.env["REPORT_RESULT"] = "failure"
        first = publish("complete", self.env, self.api)
        failed = self.comments[first]["body"]
        self.env.update(GITHUB_RUN_ATTEMPT="2", REPORT_RESULT="success", STATUS_COMMENT_ID=str(first))

        retry = publish("complete", self.env, self.api)
        self.assertEqual(self.posted[-1][:2], ("POST", COMMENTS_API))
        self.assertNotEqual(retry, first)
        self.assertIn("— Failed.", failed)
        self.assertEqual(self.comments[first]["body"], failed)
        self.assertIn("— Passed.", self.comments[retry]["body"])
        self.assertIn("/actions/runs/123/attempts/2)", self.comments[retry]["body"])
        self.assertNotIn("/artifacts/", self.comments[retry]["body"])
        self.assertEqual(publish("complete", self.env, self.api), retry)
        self.assertEqual(self.posted[-1][:2], ("PATCH", f"repos/{REPO}/issues/comments/{retry}"))

    def test_retry_and_new_command_get_separate_started_comments(self):
        first = publish("started", self.env, self.api)
        self.env["GITHUB_RUN_ATTEMPT"] = "2"
        retry = publish("started", self.env, self.api)
        self.assertEqual(self.posted[-1][:2], ("POST", COMMENTS_API))
        self.assertEqual(publish("running", self.env, self.api), retry)
        self.env.update(GITHUB_RUN_ATTEMPT="1", GITHUB_RUN_ID="321", COMMAND_ID="1000")
        new = publish("started", self.env, self.api)
        self.assertEqual(len({first, retry, new}), 3)
        self.assertEqual(self.posted[-1][:2], ("POST", COMMENTS_API))
        self.assertIn("<!-- sessionstats-matrix-run:321:1000:1 -->", self.posted[-1][2])

    def test_completion_posts_result_if_announce_could_not_post(self):
        def no_announced_comment(path, *args):
            if path == f"{COMMENTS_API}?per_page=100":
                return [[]]
            return self.api(path, *args)

        publish("complete", self.env, no_announced_comment)
        self.assertEqual(self.posted[-1][:2], ("POST", COMMENTS_API))
        self.assertIn("— Passed.", self.posted[-1][2])

    def test_missing_job_metadata_does_not_hide_failure_or_the_actions_link(self):
        self.env.update(REPORT_RESULT="failure", STATUS_COMMENT_ID="900")
        def unavailable(path, *args):
            if "/actions/" in path:
                raise subprocess.CalledProcessError(1, "gh api")
            return self.api(path, *args)

        publish("complete", self.env, unavailable)
        self.assertIn("— Failed.", self.posted[-1][2])
        self.assertIn("/actions/runs/123/attempts/1)", self.posted[-1][2])
        self.assertNotIn("/job/", self.posted[-1][2])

    def test_artifact_belongs_to_this_run_and_is_downloadable(self):
        self.env["STATUS_COMMENT_ID"] = "900"
        for patch in ({"expired": True}, {"workflow_run": {"id": 999}}, {"id": 555}):
            def mismatch(path, *args):
                data = self.api(path, *args)
                return dict(data, **patch) if path == ARTIFACT_API else data

            publish("complete", self.env, mismatch)
            self.assertNotIn("/artifacts/", self.posted[-1][2])

    def test_invalid_ids_are_rejected_before_a_comment_is_sent(self):
        with self.assertRaises(ValueError):
            publish("started", dict(self.env, PR_NUMBER="17/extra"), self.api)
        with self.assertRaises(ValueError):
            publish("running", dict(self.env, STATUS_COMMENT_ID="URL"), self.api)
        self.assertEqual(self.requests, [])

    def test_workflow_tracks_the_early_comment_with_trusted_checkouts(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        announce = text.split("\n  announce:\n", 1)[1].split("\n  render:\n", 1)[0]
        notify = text.split("\n  notify:\n", 1)[1]
        for job in (announce, notify):
            self.assertIn("ref: ${{ github.sha }}", job)
            self.assertIn("persist-credentials: false", job)
        self.assertEqual(text.count("needs: [configuration, announce]"), 2)
        self.assertIn("STATUS_COMMENT_ID: ${{ steps.started.outputs.comment_id }}", announce)
        self.assertNotIn("STATUS_COMMENT_ID:", notify)


if __name__ == "__main__":
    unittest.main()
