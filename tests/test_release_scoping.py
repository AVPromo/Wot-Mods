"""Prevent rebuilding Stay Sharp for unrelated mods' changes."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
RELEASE = (ROOT / '.github/workflows/release.yml').read_text(encoding='utf-8')
CI = (ROOT / '.github/workflows/ci.yml').read_text(encoding='utf-8')


def path_filters(document, event):
    block = document.split('  ' + event + ':\n', 1)[1].split('    paths:\n', 1)[1]
    result = []
    for line in block.splitlines():
        if not line.startswith('      - '):
            break
        result.append(line.strip()[2:].strip().strip('\'"'))
    return result


class IsolatedBuildTests(unittest.TestCase):
    def test_release_responds_only_to_staysharp_and_its_build_machinery(self):
        paths = path_filters(RELEASE, 'push')
        for path in ('source/**', 'assets/**', 'VERSION',
                     'scripts/release_version.py', 'scripts/release_snapshot.sh'):
            self.assertIn(path, paths)
        self.assertFalse(any('sessionstats' in path or path == 'mods/**' for path in paths))
        self.assertNotIn('tests/**', paths)
        self.assertNotIn('README.md', paths)
        self.assertNotIn('docs/**', paths)
        self.assertIn('workflow_dispatch:', RELEASE)

    def test_pr_workflow_does_not_build_stats(self):
        paths = path_filters(CI, 'pull_request')
        for path in ('source/**', 'assets/**', 'tests/test_packaging.py',
                     'tests/test_release_scoping.py', '.github/workflows/ci.yml'):
            self.assertIn(path, paths)
        self.assertFalse(any('sessionstats' in path or path == 'mods/**' for path in paths))

    def test_snapshot_carries_other_mods_without_compilers(self):
        self.assertIn('bash scripts/release_snapshot.sh dist', RELEASE)
        self.assertIn('com.staysharp.medkitreminder_*.wotmod', RELEASE)
        self.assertLess(RELEASE.index('bash scripts/release_snapshot.sh dist'),
                        RELEASE.index('gh release create'))
        self.assertNotIn('mods/sessionstats/tools/build.py', RELEASE)
        self.assertNotIn('scripts/sessionstats/validate.sh', RELEASE)

    def test_publishes_and_verifies_every_snapshot_asset(self):
        self.assertIn('gh release create "$tag" dist/*', RELEASE)
        self.assertIn('--latest', RELEASE)
        self.assertIn('gh release download "$tag" --repo "$GITHUB_REPOSITORY" --dir "$remote"', RELEASE)
        self.assertIn('cmp -- "dist/$name" "$remote/$name"', RELEASE)

    def test_other_mods_must_share_publisher_lock(self):
        self.assertIn('group: wotmod-release-${{ github.repository }}', RELEASE)
        self.assertIn('cancel-in-progress: false', RELEASE)


if __name__ == '__main__':
    unittest.main()
