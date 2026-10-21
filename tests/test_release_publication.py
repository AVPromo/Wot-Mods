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
