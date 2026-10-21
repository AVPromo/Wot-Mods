"""Separate namespaces, complete checksums and immutable/resumable publications."""
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
import publish_release as shared
from test_release_publication import FakeGitHub


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT/'scripts/sessionstats'/filename)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


release = load('sessionstats_release', 'release.py')
privacy = load('sessionstats_privacy', 'privacy.py')


class SessionStatsPipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.version = '0.2.9'
        for name in ('grz.sessionstats_0.2.9.wotmod', 'wot-statystyki-sesji-v0.2.9.zip',
                     'net.openwg.gameface_1.2.2.wotmod', 'grz.sessionstats.json'):
            (self.folder/name).write_bytes(b'synthetic-artifact')
        (self.folder/'BUILD.json').write_text(json.dumps({'version':self.version,'python_bytecode':'2.7'}))
        self.checksums()
        self.api = FakeGitHub()

    def checksums(self):
        (self.folder/'SHA256SUMS.txt').write_text(''.join(shared.sha256(p)+'  '+p.name+'\n'
            for p in sorted(self.folder.iterdir()) if p.name != 'SHA256SUMS.txt'))

    def publish(self, tag='sessionstats-v0.2.9'):
        return shared.publish(self.api, 'example/mods', tag, 'a'*40, self.version, self.folder,
            tag_prefix='sessionstats-v', title='Session Stats', artifact_loader=release.inputs)

    def test_all_six_assets_publish_and_rerun_verifies_without_overwrite(self):
        self.assertEqual(self.publish(), 'published')
        self.assertEqual(len(self.api.release['assets']), 6)
        self.api.actions.clear()
        self.assertEqual(self.publish(), 'verified_existing')
        self.assertNotIn('upload_draft', self.api.actions)

    def test_medkit_tag_cannot_be_used_by_sessionstats(self):
        with self.assertRaises(shared.PublicationError): self.publish('v0.2.9')
        self.assertEqual(self.api.actions, [])

    def test_wrong_source_commit_is_not_retargeted(self):
        self.api.commit = 'b'*40
        with self.assertRaises(shared.PublicationError): self.publish()
        self.assertNotIn('upload_draft', self.api.actions)

    def test_interrupted_upload_resumes_same_draft(self):
        self.api.fail_upload_once = True
        with self.assertRaisesRegex(RuntimeError, 'Simulated interruption'): self.publish()
        self.assertEqual(self.publish(), 'published')
        self.assertEqual(self.api.actions.count('create_tag'), 1)

    def test_changed_asset_hash_blocks_before_remote_operations(self):
        (self.folder/'grz.sessionstats.json').write_text('changed')
        with self.assertRaises(shared.PublicationError): self.publish()
        self.assertEqual(self.api.actions, [])

    def test_additional_stale_build_blocks_publication(self):
        (self.folder/'grz.sessionstats_0.2.8.wotmod').write_bytes(b'stale')
        self.checksums()
        with self.assertRaises(shared.PublicationError): self.publish()

    def test_incorrect_runtime_version_blocks_publication(self):
        (self.folder/'BUILD.json').write_text(json.dumps({'version':'0.2.8','python_bytecode':'2.7'}))
        self.checksums()
        with self.assertRaises(shared.PublicationError): self.publish()

    def test_nested_archives_do_not_hide_credentials(self):
        inner = io.BytesIO()
        with zipfile.ZipFile(inner, 'w') as z:
            z.writestr('ui/script.js', 'const token = "ghp_' + 'A'*40 + '";')
        outer = io.BytesIO()
        with zipfile.ZipFile(outer, 'w') as z: z.writestr('dependency.wotmod', inner.getvalue())
        issues = privacy.scan_bytes('release.zip', outer.getvalue(), None)
        self.assertIn('github_classic_token', issues[0][1])

    def test_private_history_and_logs_are_rejected(self):
        for filename in ('player.db', 'session-stats.log', 'crash.dmp'):
            self.assertEqual(privacy.scan_bytes(filename,b'',None)[0][1], ['forbidden_resource'])


if __name__ == '__main__': unittest.main()
