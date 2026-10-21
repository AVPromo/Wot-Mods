"""Offline release-transaction regression tests; no real GitHub write operations."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest import mock

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/publish_release.py'
spec = importlib.util.spec_from_file_location('staysharp_release_publisher', SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
PublicationError = module.PublicationError
publish = module.publish
sha256 = module.sha256
GitHubCLI = module.GitHubCLI

SHA = 'a' * 40
DIFFERENT_SHA = 'b' * 40
VERSION = '1.6.7'
TAG = 'v' + VERSION


class FakeGitHub:
    def __init__(self):
        self.commit = None
        self.release = None
        self.actions = []
        self.fail_upload_once = False

    def tag_commit(self, tag):
        self.actions.append('get_tag')
        return self.commit

    def create_tag(self, tag, commit):
        self.actions.append('create_tag')
        self.commit = commit

    def get_release(self, tag):
        self.actions.append('get_release')
        return self.release

    def create_draft(self, tag, commit, title):
        self.actions.append('create_draft')
        self.release = {'tag_name': tag, 'draft': True, 'prerelease': False,
                        'html_url': 'https://github.com/example/releases/v1.6.7',
                        'assets': []}

    def upload_draft(self, tag, paths):
        self.actions.append('upload_draft')
        self.release['assets'] = []
        for index, path in enumerate(paths):
            self.release['assets'].append({
                'name': path.name,
                'size': path.stat().st_size,
                'state': 'uploaded',
                'digest': 'sha256:' + sha256(path),
            })
            if index == 0 and self.fail_upload_once:
                self.fail_upload_once = False
                raise PublicationError('Simulated interruption halfway through upload')

    def publish_draft(self, tag):
        self.actions.append('publish_draft')
        self.release['draft'] = False

    def asset_hash(self, tag, asset, name):
        self.actions.append('asset_hash')
        return asset['digest'].split(':')[1]


class ReleasePublicationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.folder = Path(self.tmp.name)
        self.mod = self.folder / ('com.staysharp.medkitreminder_%s.wotmod' % VERSION)
        self.mod.write_bytes(b'example-mod-for-local-test')
        self.manifest = self.folder / 'SHA256SUMS.txt'
        self.manifest.write_text('%s  %s\n' % (sha256(self.mod), self.mod.name), encoding='ascii')
        self.api = FakeGitHub()

    def run_release(self):
        return publish(self.api, 'example/WotMods', TAG, SHA, VERSION, self.folder)

    def test_new_release_creates_tag_then_draft_uploads_verifies_and_publishes(self):
        self.assertEqual(self.run_release(), 'published')
        self.assertEqual(self.api.commit, SHA)
        self.assertFalse(self.api.release['draft'])
        self.assertEqual(len(self.api.release['assets']), 2)
        for name in ('create_tag', 'create_draft', 'upload_draft', 'publish_draft'):
            self.assertEqual(self.api.actions.count(name), 1)

    def test_existing_wrong_tag_is_never_retargeted(self):
        self.api.commit = DIFFERENT_SHA
        with self.assertRaisesRegex(PublicationError, 'points to'):
            self.run_release()
        self.assertNotIn('create_draft', self.api.actions)
        self.assertNotIn('upload_draft', self.api.actions)

    def test_existing_correct_tag_without_release_can_be_published(self):
        self.api.commit = SHA
        self.assertEqual(self.run_release(), 'published')
        self.assertNotIn('create_tag', self.api.actions)

    def test_existing_draft_without_assets_is_repaired_and_published(self):
        self.api.commit = SHA
        self.api.create_draft(TAG, SHA, 'draft')
        self.api.actions.clear()
        self.assertEqual(self.run_release(), 'published')
        self.assertIn('upload_draft', self.api.actions)
        self.assertFalse(self.api.release['draft'])

    def test_rerun_repairs_failed_upload_in_existing_draft(self):
        self.api.fail_upload_once = True
        with self.assertRaisesRegex(PublicationError, 'Simulated interruption'):
            self.run_release()
        self.assertTrue(self.api.release['draft'])
        self.assertEqual(len(self.api.release['assets']), 1)
        self.assertEqual(self.run_release(), 'published')
        self.assertEqual(len(self.api.release['assets']), 2)

    def test_completed_release_rerun_verifies_and_does_not_mutate(self):
        self.run_release()
        self.api.actions.clear()
        self.assertEqual(self.run_release(), 'verified_existing')
        self.assertFalse(any(a in self.api.actions for a in
                             ('create_tag', 'create_draft', 'upload_draft', 'publish_draft')))

    def test_published_incomplete_release_fails_instead_of_false_success(self):
        self.run_release()
        self.api.release['assets'].pop()
        self.api.actions.clear()
        with self.assertRaisesRegex(PublicationError, 'asset set'):
            self.run_release()
        self.assertNotIn('upload_draft', self.api.actions)

    def test_published_corrupt_asset_fails_instead_of_overwriting(self):
        self.run_release()
        self.api.release['assets'][0]['digest'] = 'sha256:' + 'f'*64
        self.api.actions.clear()
        with self.assertRaisesRegex(PublicationError, 'SHA-256 mismatch'):
            self.run_release()
        self.assertNotIn('upload_draft', self.api.actions)

    def test_draft_with_wrong_tag_sha_does_not_upload(self):
        self.api.commit = DIFFERENT_SHA
        self.api.create_draft(TAG, DIFFERENT_SHA, 'draft')
        self.api.actions.clear()
        with self.assertRaisesRegex(PublicationError, 'points to'):
            self.run_release()
        self.assertNotIn('upload_draft', self.api.actions)

    def test_release_without_tag_is_refused(self):
        self.api.create_draft(TAG, SHA, 'draft')
        self.api.actions.clear()
        with self.assertRaisesRegex(PublicationError, 'tag is missing'):
            self.run_release()
        self.assertNotIn('create_tag', self.api.actions)

    def test_wrong_manifest_is_rejected_before_any_remote_operation(self):
        self.manifest.write_text('deadbeef  ' + self.mod.name, encoding='ascii')
        with self.assertRaisesRegex(PublicationError, 'Checksum manifest'):
            self.run_release()
        self.assertFalse(self.api.actions)

    def test_unexpected_second_mod_is_rejected(self):
        (self.folder / 'another.wotmod').write_bytes(b'foo')
        with self.assertRaisesRegex(PublicationError, 'multiple'):
            self.run_release()
        self.assertFalse(self.api.actions)

    def test_tag_version_mismatch_rejected(self):
        with self.assertRaisesRegex(PublicationError, 'do not match'):
            publish(self.api, 'example/WotMods', 'v1.6.8', SHA, VERSION, self.folder)

    def test_uploaded_asset_content_hash_is_also_checked(self):
        self.run_release()
        self.api.release['assets'][0]['digest'] = 'sha256:' + '0'*64
        with self.assertRaisesRegex(PublicationError, 'SHA-256 mismatch'):
            self.run_release()

    def test_wrong_prerelease_flag_fails_closed(self):
        self.run_release()
        self.api.release['prerelease'] = True
        with self.assertRaisesRegex(PublicationError, 'prerelease'):
            self.run_release()


class CLIContractTests(unittest.TestCase):
    def test_only_404_counts_as_missing(self):
        client = GitHubCLI('some/repository')
        for code in (401, 403, 500):
            fake = mock.Mock(returncode=1, stderr='gh: Forbidden (HTTP %d)' % code, stdout='')
            with mock.patch.object(module.subprocess, 'run', return_value=fake):
                with self.assertRaises(PublicationError):
                    client.api('releases/tags/v1.6.1', missing_ok=True)
        fake = mock.Mock(returncode=1, stderr='gh: Not Found (HTTP 404)', stdout='')
        with mock.patch.object(module.subprocess, 'run', return_value=fake):
            self.assertIsNone(client.api('releases/tags/v1.6.1', missing_ok=True))

    def test_annotated_tag_resolves_to_commit(self):
        client = GitHubCLI('some/repository')
        with mock.patch.object(client, 'api', side_effect=[
            {'object': {'type': 'tag', 'sha': 'b' * 40}},
            {'object': {'type': 'commit', 'sha': SHA}},
        ]) as called:
            self.assertEqual(client.tag_commit(TAG), SHA)
            self.assertEqual(called.call_count, 2)

    def test_ambiguous_reference_is_rejected(self):
        client = GitHubCLI('some/repository')
        with mock.patch.object(client, 'api', return_value=[]):
            with self.assertRaises(PublicationError):
                client.tag_commit(TAG)

    def test_explicit_tag_creation_uses_expected_commit(self):
        client = GitHubCLI('some/repository')
        with mock.patch.object(client, 'command', return_value='') as gh:
            client.create_tag(TAG, SHA)
            self.assertIn('sha='+SHA, gh.call_args.args)
            self.assertIn('ref=refs/tags/'+TAG, gh.call_args.args)


if __name__ == '__main__':
    unittest.main()


class RealGitHubDraftRegressionTests(unittest.TestCase):
    """Recreate the exact GitHub API contract behind run #39677307005."""

    def test_draft_is_listed_but_tag_endpoint_is_404(self):
        client = GitHubCLI('owner/repo')
        draft = {'id': 420063804, 'tag_name': 'v1.6.1', 'draft': True,
                 'prerelease': False, 'assets': []}
        called = []

        def actual_api(resource, **kwargs):
            called.append(resource)
            if resource.startswith('releases?'):
                return [draft]
            if resource == 'releases/420063804':
                return draft
            if resource == 'releases/tags/v1.6.1':
                return None  # Verified real GitHub HTTP 404 for a draft.
            raise AssertionError('Unexpected endpoint ' + resource)

        with mock.patch.object(client, 'api', side_effect=actual_api):
            self.assertEqual(client.get_release('v1.6.1'), draft)
        self.assertEqual(called,
                         ['releases?per_page=100&page=1', 'releases/420063804'])

    def test_paginate_when_draft_not_on_first_page(self):
        client = GitHubCLI('owner/repo')
        page1 = [{'id': k+1, 'tag_name': 'v0.0.%d' % k} for k in range(100)]
        item = {'id': 555, 'tag_name': 'v1.6.1', 'draft': True, 'assets': []}

        def actual_api(resource, **kwargs):
            if resource.endswith('page=1'):
                return page1
            if resource.endswith('page=2'):
                return [item]
            if resource == 'releases/555':
                return item
            raise AssertionError(resource)

        with mock.patch.object(client, 'api', side_effect=actual_api):
            self.assertEqual(client.get_release('v1.6.1'), item)
            self.assertIsNone(client.get_release('v1.6.2'))

    def test_unknown_release_returns_none_without_creating_draft(self):
        client = GitHubCLI('owner/repo')
        with mock.patch.object(client, 'api', return_value=[]):
            self.assertIsNone(client.get_release('v1.6.2'))

    def test_malformed_release_listing_fails_closed(self):
        client = GitHubCLI('owner/repo')
        with mock.patch.object(client, 'api', return_value={'draft': True}):
            with self.assertRaisesRegex(PublicationError, 'listing'):
                client.get_release('v1.6.1')

    def test_duplicate_tag_listings_are_rejected(self):
        client = GitHubCLI('owner/repo')
        item = {'id': 15, 'tag_name': 'v1.6.1'}
        with mock.patch.object(client, 'api', return_value=[item, item]):
            with self.assertRaisesRegex(PublicationError, 'Ambiguous'):
                client.get_release('v1.6.1')

    def test_uploads_draft_by_numeric_id_not_by_tag(self):
        client = GitHubCLI('owner/repo')
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory) / 'com.staysharp.medkitreminder_1.6.1.wotmod'
            p.write_bytes(b'mod-1.6.1')
            draft = {'id': 420063804, 'tag_name': 'v1.6.1',
                     'draft': True, 'assets': []}
            created = {'name': p.name, 'size': p.stat().st_size,
                       'state': 'uploaded', 'digest': 'sha256:' + sha256(p)}
            with mock.patch.object(client, 'get_release', return_value=draft), \
                 mock.patch.object(client, '_request_bytes',
                                   return_value=module.json.dumps(created).encode()) as transfer, \
                 mock.patch.object(client, 'command') as command:
                client.upload_draft('v1.6.1', [p])
                command.assert_not_called()
                transfer.assert_called_once()
                url = transfer.call_args.args[0]
                self.assertEqual(url, 'https://uploads.github.com/repos/owner/repo/'
                                      'releases/420063804/assets?name=' + p.name)
                self.assertEqual(transfer.call_args.kwargs['method'], 'POST')
                self.assertEqual(transfer.call_args.kwargs['payload'], b'mod-1.6.1')

    def test_corrupted_draft_asset_is_removed_before_reupload(self):
        client = GitHubCLI('owner/repo')
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory) / 'SHA256SUMS.txt'
            p.write_bytes(b'new manifest')
            draft = {'id': 22, 'tag_name': 'v1.6.1', 'draft': True,
                     'assets': [{'id': 53, 'name': p.name, 'size': 3,
                                 'state': 'uploaded', 'digest': 'sha256:bad'}]}
            created = {'name': p.name, 'size': p.stat().st_size,
                       'state': 'uploaded', 'digest': 'sha256:' + sha256(p)}
            with mock.patch.object(client, 'get_release', return_value=draft), \
                 mock.patch.object(client, '_request_bytes',
                                   return_value=module.json.dumps(created).encode()), \
                 mock.patch.object(client, 'command') as command:
                client.upload_draft('v1.6.1', [p])
                self.assertEqual(command.call_args.args[-1],
                                 'repos/owner/repo/releases/assets/53')

    def test_matching_draft_asset_not_clobbered(self):
        client = GitHubCLI('owner/repo')
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory) / 'SHA256SUMS.txt'
            p.write_bytes(b'already uploaded')
            draft = {'id': 22, 'tag_name': 'v1.6.1', 'draft': True,
                     'assets': [{'id': 54, 'name': p.name,
                                 'size': p.stat().st_size, 'state': 'uploaded',
                                 'digest': 'sha256:' + sha256(p)}]}
            with mock.patch.object(client, 'get_release', return_value=draft), \
                 mock.patch.object(client, '_request_bytes') as transfer, \
                 mock.patch.object(client, 'command') as command:
                client.upload_draft('v1.6.1', [p])
                transfer.assert_not_called()
                command.assert_not_called()

    def test_publish_draft_uses_release_numeric_id(self):
        client = GitHubCLI('owner/repo')
        draft = {'id': 420063804, 'tag_name': 'v1.6.1', 'draft': True}
        with mock.patch.object(client, 'get_release', return_value=draft), \
             mock.patch.object(client, 'command') as command:
            client.publish_draft('v1.6.1')
            self.assertEqual(command.call_args.args,
                             ('api', '--method', 'PATCH',
                              'repos/owner/repo/releases/420063804',
                              '-F', 'draft=false'))

    def test_missing_digest_fail_closed_without_draft_download(self):
        client = GitHubCLI('owner/repo')
        with mock.patch.object(client, 'command') as command:
            with self.assertRaisesRegex(PublicationError, 'valid GitHub SHA-256'):
                client.asset_hash('v1.6.1', {'id': 33}, 'example.wotmod')
            command.assert_not_called()

    def test_creating_draft_waits_for_listing_visibility(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            version = '1.6.7'
            p = folder / ('com.staysharp.medkitreminder_%s.wotmod' % version)
            p.write_bytes(b'example')
            (folder / 'SHA256SUMS.txt').write_text(
                '%s  %s\n' % (sha256(p), p.name), encoding='ascii')
            api = FakeGitHub()
            original_get = api.get_release
            waited = [0]

            def lagged_get(tag):
                if api.release is not None and waited[0] < 2:
                    waited[0] += 1
                    return None
                return original_get(tag)

            with mock.patch.object(api, 'get_release', side_effect=lagged_get), \
                 mock.patch.object(module.time, 'sleep') as sleep:
                self.assertEqual(publish(api, 'owner/repo', 'v1.6.7', SHA,
                                         version, folder), 'published')
                self.assertEqual(sleep.call_count, 2)


class WorkflowRegressionTests(unittest.TestCase):
    """Check recovery is opt-in and cannot publish from PR event."""

    def test_recovery_workflow_requires_manual_dispatch(self):
        root = Path(__file__).resolve().parents[1]
        source = (root / '.github/workflows/recover.yml').read_text(encoding='utf-8')
        self.assertIn('workflow_dispatch:', source)
        self.assertIn('required: true', source)
        self.assertIn("if: github.ref == 'refs/heads/main'", source)
        self.assertIn('RELEASE_COMMIT: ${{ steps.tagged.outputs.commit }}', source)
        self.assertIn('STAYSHARP_DIST_DIR: ${{ github.workspace }}/tagged_source/dist', source)
        self.assertIn('persist-credentials: false', source)
        self.assertNotIn('pull_request:', source)
        self.assertNotIn('curl -H', source)

    def test_release_workflow_still_auto_publishes_new_main_commits(self):
        root = Path(__file__).resolve().parents[1]
        source = (root / '.github/workflows/release.yml').read_text(encoding='utf-8')
        self.assertIn('push:', source)
        self.assertIn('branches: [main]', source)
        self.assertIn('python3 scripts/publish_release.py', source)
        self.assertIn('wotmod-release-${{ github.repository }}', source)


class RecoveryLatestRegressionTests(unittest.TestCase):
    def test_repairing_old_draft_never_marks_it_latest(self):
        client = GitHubCLI('owner/repo')
        with mock.patch.dict(module.os.environ, {'STAYSHARP_RECOVERY_MODE': '1'}), \
             mock.patch.object(client, 'get_release',
                               return_value={'id': 420063804, 'draft': True}), \
             mock.patch.object(client, 'command') as command:
            client.publish_draft('v1.6.1')
            self.assertEqual(command.call_args.args[-2:], ('-f', 'make_latest=false'))

    def test_regular_release_can_be_automatically_latest(self):
        client = GitHubCLI('owner/repo')
        with mock.patch.dict(module.os.environ,
                             {'STAYSHARP_RECOVERY_MODE': ''}), \
             mock.patch.object(client, 'get_release',
                               return_value={'id': 420063804, 'draft': True}), \
             mock.patch.object(client, 'command') as command:
            client.publish_draft('v1.6.2')
            self.assertNotIn('make_latest=false', command.call_args.args)
