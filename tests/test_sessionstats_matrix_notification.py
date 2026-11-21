import json
import os
from pathlib import Path
import subprocess
import textwrap
import unittest
from unittest.mock import patch


WORKFLOW = Path(__file__).resolve().parents[1] / ".github/workflows/sessionstats-matrix-command.yml"
REPO = "example/WotMods"
RUN_API = f"repos/{REPO}/actions/runs/123"
COMMENTS_API = f"repos/{REPO}/issues/17/comments"


class MatrixNotificationTests(unittest.TestCase):
    def publish(self, *, result="success", artifact_id="567", jobs=None, artifacts=None, attempt="1"):
        text = WORKFLOW.read_text(encoding="utf-8")
        code = text.split("          python3 - <<'PY'\n", 1)[1].split("\n          PY", 1)[0]
        responses = {
            f"{RUN_API}/attempts/{attempt}/jobs?per_page=100": {
                "jobs": jobs if jobs is not None else [{"id": 789, "name": "Downloadable HTML matrix"}]
            },
            f"{RUN_API}/artifacts?name=sessionstats-matrix-html": {
                "artifacts": artifacts if artifacts is not None else [
                    {"id": 567, "name": "sessionstats-matrix-html", "expired": False}
                ]
            },
        }
        messages = []

        def gh(command, *, text):
            self.assertEqual(command[:2], ["gh", "api"])
            path, *arguments = command[2:]
            if path == COMMENTS_API:
                method_flag, method, field_flag, body, silent_flag = arguments
                self.assertEqual((method_flag, method, field_flag, silent_flag),
                                 ("--method", "POST", "-f", "--silent"))
                self.assertTrue(body.startswith("body="))
                messages.append(body.removeprefix("body="))
                return ""
            return json.dumps(responses[path])

        with patch.dict(os.environ, {
            "GITHUB_REPOSITORY": REPO, "GITHUB_SERVER_URL": "https://github.com",
            "PR_NUMBER": "17", "COMMAND_ID": "99", "GITHUB_RUN_ID": "123",
            "GITHUB_RUN_ATTEMPT": attempt, "COVERAGE": "smoke", "TARGET_SHA": "a" * 40,
            "REPORT_RESULT": result, "ARTIFACT_ID": artifact_id,
        }), patch.object(subprocess, "check_output", side_effect=gh):
            exec(compile(textwrap.dedent(code), str(WORKFLOW), "exec"), {})
        self.assertEqual(len(messages), 1)
        return messages[0]

    def test_success_posts_links_to_the_report_and_command(self):
        message = self.publish()
        self.assertIn("`smoke` — passed", message)
        self.assertIn("/actions/runs/123/artifacts/567", message)
        self.assertIn("/actions/runs/123/job/789", message)
        self.assertIn("/pull/17#issuecomment-99", message)

    def test_failure_still_links_to_a_partial_report(self):
        message = self.publish(result="failure")
        self.assertIn("— failed", message)
        self.assertIn("/actions/runs/123/artifacts/567", message)

    def test_missing_report_falls_back_to_the_run(self):
        message = self.publish(result="failure", artifact_id="", jobs=[])
        self.assertIn("— failed", message)
        self.assertIn(f"[Actions run](https://github.com/{REPO}/actions/runs/123)", message)
        self.assertNotIn("Download HTML report", message)

    def test_unverified_artifact_id_is_ignored(self):
        message = self.publish(artifact_id="111")
        self.assertNotIn("/artifacts/", message)

    def test_rerun_posts_a_new_comment_for_each_attempt(self):
        first = self.publish(result="failure", attempt="1")
        retry = self.publish(attempt="2")
        self.assertIn("in attempt 1", first)
        self.assertIn("— failed", first)
        self.assertIn("in attempt 2", retry)
        self.assertIn("— passed", retry)


if __name__ == "__main__":
    unittest.main()
