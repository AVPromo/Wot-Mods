"""Integration-level offline tests of immutable asset carry-forward.

Only the updated mod is rebuilt; unchanged asset bytes are imported from a
verified published GitHub Release. GitHub CLI is faked, never the GitHub API.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

HELPER = Path(__file__).resolve().parents[1] / "scripts/release_snapshot.sh"

FAKE_GH = '''#!/usr/bin/env python3
import json, os, pathlib, shutil, sys
args = sys.argv[1:]
if args[:2] == ['release','list']:
    print(pathlib.Path(os.environ['FAKE_RELEASE_LIST']).read_text())
elif args[:2] == ['release','download']:
    dest = pathlib.Path(args[args.index('--dir') + 1])
    for item in pathlib.Path(os.environ['FAKE_RELEASE_DIR']).iterdir():
        shutil.copy2(item, dest / item.name)
else:
    sys.exit('Unexpected command: ' + repr(args))
'''


def manifest(directory):
    files = sorted(p for p in directory.iterdir() if p.is_file() and p.name != "SHA256SUMS.txt")
    (directory / "SHA256SUMS.txt").write_text(
        "".join(hashlib.sha256(p.read_bytes()).hexdigest() + "  " + p.name + "\n" for p in files)
    )


class SnapshotTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.dist = root / "dist"
        self.dist.mkdir()
        self.old = root / "previous"
        self.old.mkdir()
        self.bin = root / "bin"
        self.bin.mkdir()
        exe = self.bin / "gh"
        exe.write_text(FAKE_GH)
        exe.chmod(0o755)
        self.list_path = root / "list.json"
        self.own_name = "com.staysharp.medkitreminder_1.6.3.wotmod"
        (self.dist / self.own_name).write_bytes(b"new-medkit-build")
        manifest(self.dist)
        self.releases = []
        self.env = dict(os.environ,
                        PATH=str(self.bin) + os.pathsep + os.environ["PATH"],
                        GITHUB_REPOSITORY="example/WotMods",
                        FAKE_RELEASE_LIST=str(self.list_path),
                        FAKE_RELEASE_DIR=str(self.old))
        self.set_previous(immutable=True)

    def set_previous(self, immutable=True):
        self.releases = [{"tagName": "sessionstats-v0.2.4", "isLatest": True,
                          "isDraft": False, "isPrerelease": False,
                          "isImmutable": immutable}]
        self.list_path.write_text(json.dumps(self.releases))
        (self.old / "com.staysharp.medkitreminder_1.6.2.wotmod").write_bytes(b"old-medkit")
        (self.old / "grz.sessionstats_0.2.4.wotmod").write_bytes(b"unchanged-stats")
        (self.old / "grz.sessionstats.json").write_bytes(b'{"language":"pl"}')
        (self.old / "wot-statystyki-sesji-v0.2.4.zip").write_bytes(b"unchanged-installer")
        manifest(self.old)

    def call_helper(self, own_pattern="com.staysharp.medkitreminder_*.wotmod"):
        return subprocess.run(["bash", str(HELPER), str(self.dist), self.own_name, own_pattern],
                              capture_output=True, text=True, env=self.env)

    def test_carries_nonowned_assets_without_rebuilding(self):
        r = self.call_helper()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual((self.dist / self.own_name).read_bytes(), b"new-medkit-build")
        self.assertFalse((self.dist / "com.staysharp.medkitreminder_1.6.2.wotmod").exists())
        self.assertEqual((self.dist / "grz.sessionstats_0.2.4.wotmod").read_bytes(), b"unchanged-stats")
        self.assertEqual((self.dist / "grz.sessionstats.json").read_bytes(), b'{"language":"pl"}')
        self.assertEqual((self.dist / "wot-statystyki-sesji-v0.2.4.zip").read_bytes(), b"unchanged-installer")
        self.assertIn("grz.sessionstats_0.2.4.wotmod", (self.dist / "SHA256SUMS.txt").read_text())
        subprocess.run(["sha256sum", "-c", "SHA256SUMS.txt"], cwd=self.dist, check=True,
                       stdout=subprocess.DEVNULL)

    def test_new_tag_namespace_accepts_legacy_latest_without_rebuilding(self):
        self.releases[0]['tagName'] = 'v1.6.2'
        self.list_path.write_text(json.dumps(self.releases))
        result = self.call_helper()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.dist / self.own_name).read_bytes(), b'new-medkit-build')
        self.assertEqual((self.dist / 'grz.sessionstats_0.2.4.wotmod').read_bytes(),
                         b'unchanged-stats')

    def test_first_release_has_no_snapshot_to_carry(self):
        self.list_path.write_text("[]")
        r = self.call_helper()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(sorted(p.name for p in self.dist.iterdir()),
                         ["SHA256SUMS.txt", self.own_name])

    def test_previous_release_must_be_immutable(self):
        self.set_previous(immutable=False)
        r = self.call_helper()
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("not immutable", r.stderr)

    def test_previous_release_corruption_aborts(self):
        (self.old / "grz.sessionstats_0.2.4.wotmod").write_bytes(b"tampered")
        r = self.call_helper()
        self.assertNotEqual(r.returncode, 0)
        self.assertNotIn("grz.sessionstats_0.2.4.wotmod", [p.name for p in self.dist.iterdir()])

    def test_unlisted_asset_aborts(self):
        (self.old / "malicious.json").write_bytes(b"not in checksum")
        r = self.call_helper()
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("unlisted", r.stderr)

    def test_latest_absent_with_other_published_releases_fails(self):
        self.releases[0]["isLatest"] = False
        self.list_path.write_text(json.dumps(self.releases))
        r = self.call_helper()
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("none is marked Latest", r.stderr)

    def test_existing_output_collision_is_rejected(self):
        (self.dist / "grz.sessionstats.json").write_bytes(b"different")
        manifest(self.dist)
        r = self.call_helper()
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("Asset name conflict", r.stderr)

    def test_draft_and_prerelease_do_not_count_as_latest(self):
        self.list_path.write_text(json.dumps([
            {"tagName":"unreleased", "isLatest":False, "isDraft":True,
             "isPrerelease":False,"isImmutable":False},
            {"tagName":"preview", "isLatest":False, "isDraft":False,
             "isPrerelease":True,"isImmutable":False}]))
        r=self.call_helper()
        self.assertEqual(r.returncode,0,r.stderr)
        self.assertEqual(sorted(p.name for p in self.dist.iterdir()),
                         ["SHA256SUMS.txt",self.own_name])

    def test_pattern_parameter_supports_another_mod(self):
        old=self.own_name
        (self.dist / old).unlink()
        self.own_name="grz.sessionstats_0.2.5.wotmod"
        (self.dist / self.own_name).write_bytes(b"new-stats")
        manifest(self.dist)
        r=self.call_helper("grz.sessionstats_*.wotmod")
        self.assertEqual(r.returncode,0,r.stderr)
        self.assertEqual((self.dist / "com.staysharp.medkitreminder_1.6.2.wotmod").read_bytes(),b"old-medkit")
        self.assertFalse((self.dist / "grz.sessionstats_0.2.4.wotmod").exists())


    def test_stale_same_mod_run_is_skipped_without_reverting_latest(self):
        """A2 publishes before A1: A1 must not replace the newer A2."""
        (self.old / "com.staysharp.medkitreminder_1.6.2.wotmod").unlink()
        (self.old / "com.staysharp.medkitreminder_1.6.10.wotmod").write_bytes(b"newer-medkit")
        manifest(self.old)
        previous = {p.name:p.read_bytes() for p in self.dist.iterdir()}
        r = self.call_helper()
        self.assertEqual(r.returncode, 75, r.stderr)
        self.assertIn('Skipping stale', r.stdout)
        self.assertEqual(previous, {p.name:p.read_bytes() for p in self.dist.iterdir()})

    def test_equal_version_with_same_bytes_is_idempotently_skipped(self):
        (self.old / "com.staysharp.medkitreminder_1.6.2.wotmod").unlink()
        (self.old / self.own_name).write_bytes((self.dist / self.own_name).read_bytes())
        manifest(self.old)
        r = self.call_helper()
        self.assertEqual(r.returncode, 75, r.stderr)
        self.assertIn('already published', r.stdout)

    def test_equal_version_different_bytes_fails_closed(self):
        (self.old / "com.staysharp.medkitreminder_1.6.2.wotmod").unlink()
        (self.old / self.own_name).write_bytes(b"malicious-different-build")
        manifest(self.old)
        r = self.call_helper()
        self.assertEqual(r.returncode, 1)
        self.assertIn('Same mod version has different bytes', r.stderr)

    def test_latest_cannot_contain_multiple_versions_of_same_mod(self):
        (self.old / "com.staysharp.medkitreminder_1.6.1.wotmod").write_bytes(b"extra-old-medkit")
        manifest(self.old)
        r = self.call_helper()
        self.assertEqual(r.returncode, 1)
        self.assertIn('Multiple versions', r.stderr)

    def test_missing_primary_asset_fails_closed(self):
        (self.dist / self.own_name).unlink()
        manifest(self.dist)
        r = self.call_helper()
        self.assertEqual(r.returncode, 1)
        self.assertIn('Missing or unsafe primary', r.stderr)

    def test_invalid_primary_glob_fails_closed(self):
        r = self.call_helper('*.wotmod')
        self.assertEqual(r.returncode, 1)
        self.assertIn('Primary glob', r.stderr)

    def test_A_and_B_fast_merges_keep_both_updates_in_either_publish_order(self):
        """Simulate a current-Latest lookup under a common publish mutex.

        Build A1 and B1 independently BEFORE either release exists. One writer
        publishes, then the next writer assembles against the *new* Latest.
        """
        for order in [('A', 'B'), ('B', 'A')]:
            with self.subTest(order=order):
                root = self.dist.parent / ('sequence-' + ''.join(order))
                root.mkdir()
                base = root / 'release-initial'
                base.mkdir()
                for name, contents in {
                    'com.staysharp.medkitreminder_1.6.2.wotmod':b'A0',
                    'grz.sessionstats_0.2.4.wotmod':b'B0',
                    'grz.sessionstats.json':b'{"language":"en"}',
                    'wot-statystyki-sesji-v0.2.4.zip':b'B0-install',
                }.items():
                    (base / name).write_bytes(contents)
                manifest(base)
                latest = base
                # A and B are already compiled. No building happens in this test.
                jobs = {}
                for kind, name, pattern, data in [
                    ('A','com.staysharp.medkitreminder_1.6.3.wotmod','com.staysharp.medkitreminder_*.wotmod',b'A1'),
                    ('B','grz.sessionstats_0.2.5.wotmod','grz.sessionstats_*.wotmod',b'B1'),
                ]:
                    dist = root / ('build-' + kind)
                    dist.mkdir()
                    (dist / name).write_bytes(data)
                    if kind == 'B':
                        (dist / 'grz.sessionstats.json').write_bytes(b'{"language":"pl"}')
                        (dist / 'wot-statystyki-sesji-v0.2.5.zip').write_bytes(b'B1-install')
                    manifest(dist)
                    jobs[kind] = (dist,name,pattern)
                for kind in order:
                    dist,name,pattern = jobs[kind]
                    self.list_path.write_text(json.dumps([{
                        'tagName':'latest-' + kind, 'isLatest': True,
                        'isDraft':False,'isPrerelease':False,'isImmutable':True}]))
                    env=dict(self.env, FAKE_RELEASE_DIR=str(latest))
                    args=['bash',str(HELPER),str(dist),name,pattern]
                    if kind=='B':
                        args += ['grz.sessionstats.json','wot-statystyki-sesji-v*.zip']
                    r=subprocess.run(args,env=env,capture_output=True,text=True)
                    self.assertEqual(r.returncode,0,r.stdout+r.stderr)
                    latest=dist
                actual={p.name:p.read_bytes() for p in latest.iterdir()}
                self.assertEqual(actual['com.staysharp.medkitreminder_1.6.3.wotmod'],b'A1')
                self.assertEqual(actual['grz.sessionstats_0.2.5.wotmod'],b'B1')
                self.assertEqual(actual['grz.sessionstats.json'],b'{"language":"pl"}')
                self.assertFalse(any(n.endswith(('1.6.2.wotmod','0.2.4.wotmod')) for n in actual))
                subprocess.run(['sha256sum','--check','--strict','SHA256SUMS.txt'], cwd=latest,
                               check=True,stdout=subprocess.DEVNULL)


if __name__ == "__main__":
    unittest.main()
