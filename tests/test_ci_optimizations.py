"""Keep CI optimizations fail-closed and inside their existing trust boundary."""
from pathlib import Path
import re
import unittest

from test_unified_release_workflow import condition_matches


ROOT = Path(__file__).resolve().parents[1]
STATS = (ROOT / '.github/workflows/sessionstats-ci.yml').read_text()
MEDKIT = (ROOT / '.github/workflows/ci.yml').read_text()
RELEASE = (ROOT / '.github/workflows/wotmods-release.yml').read_text()
COMPILER = (ROOT / '.github/actions/python27/action.yml').read_text()
VALIDATE = (ROOT / 'scripts/sessionstats/validate.sh').read_text()
CACHE_PIN = 'caa296126883cff596d87d8935842f9db880ef25'
PHASES = ['python3', 'python27', 'preview', 'browser', 'build', 'integration', 'privacy']


def job(text, name):
    match = re.search(r'(?ms)^  ' + re.escape(name) +
                      r':\n(.*?)(?=^  [a-z0-9_-]+:\n|\Z)', text)
    if not match:
        raise AssertionError('Missing job ' + name)
    return match.group(1)


class CiOptimizationContracts(unittest.TestCase):
    def test_only_new_commits_on_the_same_pr_supersede_validation(self):
        group = ('${{ github.workflow }}-${{ github.event_name }}-'
                 '${{ github.event.pull_request.number || github.run_id }}')
        for text in (STATS, MEDKIT):
            with self.subTest(workflow=text.splitlines()[0]):
                concurrency = text.split('\nconcurrency:\n', 1)[1].split('\njobs:', 1)[0]
                self.assertIn('  group: ' + group, concurrency)
                expression = re.search(r'^  cancel-in-progress: \$\{\{ (.+) \}\}$',
                                       concurrency, re.MULTILINE).group(1)
                for event in ('pull_request', 'workflow_dispatch', 'push',
                              'pull_request_target', 'workflow_run'):
                    self.assertEqual(condition_matches(expression, {
                        'github.event_name': event,
                        'github.ref': 'refs/heads/main',
                        'github.repository': 'Szwarceneger16/WotMods',
                    }), event == 'pull_request')
                self.assertIn('contents: read', text)
                self.assertNotIn('contents: write', text)

    def test_release_serialization_and_accepted_main_gate_remain_intact(self):
        queue = RELEASE.split('\nconcurrency:\n', 1)[1].split('\njobs:', 1)[0]
        self.assertIn('group: wotmod-release-${{ github.repository }}', queue)
        self.assertIn('queue: max', queue)
        self.assertIn('cancel-in-progress: false', queue)
        self.assertNotIn('pull_request:', RELEASE)
        self.assertIn('needs: updates', job(RELEASE, 'plan'))
        self.assertIn('needs: [plan, updates]', job(RELEASE, 'build'))
        self.assertIn('needs: [plan, updates, build]', job(RELEASE, 'publish'))

    def test_native_parallelism_waits_for_both_full_python_phases(self):
        parallel = STATS.split('      - parallel:\n', 1)[1].split('\n      - name:', 1)[0]
        names = re.findall(r'^          - name: (.+)$', parallel, re.MULTILINE)
        self.assertEqual(len(names), 2)
        self.assertEqual(len(set(names)), 2)
        self.assertEqual(re.findall(r'run: bash scripts/sessionstats/validate\.sh (\w+)', parallel),
                         ['python3', 'python27'])
        self.assertEqual(parallel.count("if: steps.source.outputs.enabled == 'true'"), 2)
        self.assertNotIn('continue-on-error', parallel)
        self.assertNotIn('parallel:', COMPILER)
        self.assertNotIn('strategy:', job(STATS, 'sessionstats'))

    def test_all_named_phases_gate_packaging_without_repeating_browser_setup(self):
        commands = re.findall(r'run: bash scripts/sessionstats/validate\.sh (\w+)', STATS)
        self.assertEqual(commands, PHASES)
        self.assertNotIn('--prepare', STATS)
        self.assertEqual(VALIDATE.count('python3 -I scripts/sessionstats/browser_qa.py'), 1)
        self.assertNotIn('continue-on-error', job(STATS, 'sessionstats'))
        self.assertNotIn('always()', job(STATS, 'sessionstats'))
        for phase in PHASES:
            command = 'run: bash scripts/sessionstats/validate.sh ' + phase
            position = STATS.index(command)
            step = STATS[STATS.rfind('- name:', 0, position):position]
            self.assertIn("if: steps.source.outputs.enabled == 'true'", step)
        self.assertLess(STATS.index('uses: ./.github/actions/python27'),
                        STATS.index('      - parallel:'))
        self.assertLess(STATS.index('validate.sh privacy'),
                        STATS.index('scripts/release_installers.py package pr-artifact-sessionstats'))
        self.assertLess(STATS.index('scripts/release_installers.py package pr-artifact-sessionstats'),
                        STATS.index('uses: actions/upload-artifact@'))

    def test_exact_cache_identity_covers_platform_and_bootstrap_recipe(self):
        self.assertIn('actions/cache/restore@' + CACHE_PIN, COMPILER)
        self.assertIn('actions/cache/save@' + CACHE_PIN, COMPILER)
        self.assertNotIn('restore-keys:', COMPILER)
        self.assertNotIn('enableCrossOsArchive:', COMPILER)
        key = re.search(r'^        key: (cpython27-.+)$', COMPILER, re.MULTILINE).group(1)
        for field in ('ubuntu-24.04', '${{ runner.os }}', '${{ runner.arch }}',
                      "${{ hashFiles('scripts/sessionstats/python27.sh') }}"):
            self.assertIn(field, key)
        self.assertEqual(COMPILER.count(
            'path: ${{ runner.temp }}/sessionstats-cpython27/Python-2.7.18'), 2)
        self.assertIn('key: ${{ steps.restore.outputs.cache-primary-key }}', COMPILER)
        # A changed checksum, version or compiler flag changes this exact recipe hash.
        bootstrap = (ROOT / 'scripts/sessionstats/python27.sh').read_text()
        self.assertIn('Python-2.7.18.tgz', bootstrap)
        self.assertIn('da3080e3b488f648a3d7a4560ddee895284c3380b11d6de75edb986526b9a814', bootstrap)
        self.assertIn('--without-ensurepip', bootstrap)

    def test_a_cache_hit_never_skips_runtime_validation(self):
        validation = COMPILER.split('    - name: Build on a miss', 1)[1].split('    - name: Save', 1)[0]
        self.assertIn('run: bash scripts/sessionstats/python27.sh', validation)
        self.assertNotIn('if:', validation)
        self.assertNotIn('continue-on-error', COMPILER)
        self.assertIn('cache-mode: read', job(STATS, 'sessionstats'))

    def test_only_accepted_main_events_can_save_the_compiler_cache(self):
        save = COMPILER.split('    - name: Save validated build', 1)[1]
        condition = re.search(r'^      if: (.+)$', save, re.MULTILINE).group(1)
        prefix = "steps.restore.outputs.cache-hit != 'true' && "
        self.assertTrue(condition.startswith(prefix))
        trust = condition[len(prefix):]
        for event in ('push', 'workflow_dispatch', 'pull_request',
                      'pull_request_target', 'workflow_run'):
            for ref in ('refs/heads/main', 'refs/heads/feature', 'refs/pull/29/merge', 'refs/tags/main'):
                with self.subTest(event=event, ref=ref):
                    self.assertEqual(condition_matches(trust, {
                        'github.event_name': event, 'github.ref': ref,
                        'github.repository': 'Szwarceneger16/WotMods',
                    }), event in ('push', 'workflow_dispatch') and ref == 'refs/heads/main')

    def test_release_reuses_the_compiler_only_for_sessionstats(self):
        build = job(RELEASE, 'build')
        self.assertIn('cache-mode: write', build)
        position = build.index('uses: ./.github/actions/python27')
        compiler = build[build.rfind('- name:', 0, position):position]
        self.assertIn("if: matrix.mod == 'sessionstats'", compiler)
        self.assertLess(position, build.index('run: bash scripts/build_release_module.sh'))
        self.assertIn('runs-on: ubuntu-24.04', build)
        self.assertIn('runs-on: ubuntu-24.04', job(STATS, 'sessionstats'))

    def test_shared_contract_and_compiler_action_changes_trigger_validation(self):
        self.assertIn("      - '.github/actions/python27/**'", STATS)
        for workflow in (STATS, MEDKIT):
            self.assertIn("      - 'tests/test_ci_optimizations.py'", workflow)
        self.assertIn("-p 'test_ci_optimizations.py' -v", STATS)


if __name__ == '__main__':
    unittest.main()
