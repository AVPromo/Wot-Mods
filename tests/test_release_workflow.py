"""Offline guardrails for the simple, GitHub-native release workflow.

These checks prevent accidental re-introduction of custom release APIs,
destructive recovery scripts or unsafe token use. Actual publication is
integration-tested only after a reviewed merge to the main branch.
"""
from pathlib import Path
import re
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = (ROOT / '.github/workflows/release.yml').read_text(encoding='utf-8')


class GitHubNativeReleaseTests(unittest.TestCase):
    def test_no_custom_publisher_or_deletion_workflow(self):
        self.assertFalse((ROOT / 'scripts/publish_release.py').exists())
        self.assertFalse((ROOT / 'scripts/publish_release.sh').exists())
        self.assertFalse((ROOT / '.github/workflows/recover.yml').exists())
        self.assertFalse((ROOT / 'tests/test_release_publication.py').exists())

    def test_readonly_build_separate_from_write_enabled_publisher(self):
        self.assertIn('contents: read', WORKFLOW)
        self.assertIn('contents: write', WORKFLOW)
        self.assertLess(WORKFLOW.index('contents: read'), WORKFLOW.index('contents: write'))
        self.assertIn('needs: build', WORKFLOW)
        self.assertIn("if: github.ref == 'refs/heads/main'", WORKFLOW)

    def test_first_party_actions_pinned_to_full_commit_sha(self):
        action_lines = re.findall(r'^\s*uses:\s*(actions/[^\s]+)', WORKFLOW, re.MULTILINE)
        self.assertGreaterEqual(len(action_lines), 3)
        for action in action_lines:
            self.assertRegex(action, r'^actions/(?:checkout|upload-artifact|download-artifact)@[0-9a-f]{40}$')

    def test_remote_tag_bound_to_exact_workflow_commit_before_release(self):
        self.assertLess(WORKFLOW.index('git push origin'), WORKFLOW.index('gh release create'))
        self.assertIn('test "$resolved" = "$GITHUB_SHA"', WORKFLOW)
        self.assertIn('--verify-tag', WORKFLOW)
        self.assertIn('git rev-parse', WORKFLOW)

    def test_no_http_api_or_destructive_release_mutation(self):
        self.assertNotIn('gh api', WORKFLOW)
        self.assertNotIn('gh release delete', WORKFLOW)
        self.assertNotIn('gh release upload', WORKFLOW)
        self.assertNotIn('--clobber', WORKFLOW)
        self.assertNotIn('--latest=false', WORKFLOW)
        self.assertIn('gh release create', WORKFLOW)

    def test_asset_integrity_and_fail_closed_drafts(self):
        self.assertIn('sha256sum --check SHA256SUMS.txt', WORKFLOW)
        self.assertIn('gh release download', WORKFLOW)
        self.assertIn('cmp -- "dist/$mod" "$remote/$mod"', WORKFLOW)
        self.assertIn('isDraft', WORKFLOW)
        self.assertIn('draft)', WORKFLOW)
        self.assertIn('exit 1', WORKFLOW)

    def test_bash_syntax_in_release_step(self):
        fragment = WORKFLOW.split('      - name: Create and verify GitHub Release\n', 1)[1]
        script = fragment.split('        run: |\n', 1)[1]
        lines = []
        for line in script.splitlines():
            if line and not line.startswith('          '):
                break
            lines.append(line[10:] if line else '')
        result = subprocess.run(['bash', '-n'], input='\n'.join(lines) + '\n',
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_write_token_not_exposed_to_build_job(self):
        build, publish = WORKFLOW.split('\n  publish:', 1)
        self.assertNotIn('GH_TOKEN:', build)
        self.assertNotIn('persist-credentials: true', build)
        self.assertIn('GH_TOKEN: ${{ github.token }}', publish)


if __name__ == '__main__':
    unittest.main()
