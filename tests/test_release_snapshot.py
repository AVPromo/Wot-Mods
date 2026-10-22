"""Offline tests: copy unchanged assets from the previous immutable GitHub Release.

Only the modified mod is built. A fake GitHub CLI supplies assets and listing
data; no network/API credentials are used in these tests.
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/release_snapshot.sh'

FAKE_GH = """#!/usr/bin/env python3
import os, pathlib, shutil, sys
args = sys.argv[1:]
if args[:2] == ['release', 'list']:
    print(pathlib.Path(os.environ['FAKE_RELEASE_LIST']).read_text())
elif args[:2] == ['release', 'download']:
    dest = pathlib.Path(args[args.index('--dir') + 1])
    for item in pathlib.Path(os.environ['FAKE_RELEASE_DIR']).iterdir():
        shutil.copy2(item, dest / item.name)
else:
    sys.exit('Unexpected GitHub CLI operation: ' + repr(args))
"""


def manifest(directory):
    files = sorted(p for p in directory.iterdir()
                   if p.is_file() and p.name != 'SHA256SUMS.txt')
    (directory / 'SHA256SUMS.txt').write_text(
        ''.join(hashlib.sha256(p.read_bytes()).hexdigest() + '  ' + p.name + '\n'
                for p in files))


class SnapshotTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        home = Path(tmp.name)
        self.dist, self.previous, self.bin = [home / n for n in ('dist', 'previous', 'bin')]
        for directory in (self.dist, self.previous, self.bin):
            directory.mkdir()
        gh = self.bin / 'gh'
        gh.write_text(FAKE_GH)
        gh.chmod(0o755)
        self.list_path = home / 'releases.json'
        self.own = 'com.staysharp.medkitreminder_1.6.3.wotmod'
        (self.dist / self.own).write_bytes(b'updated-staysharp')
        manifest(self.dist)
        self.env = dict(os.environ, PATH=str(self.bin) + os.pathsep + os.environ['PATH'],
                        GITHUB_REPOSITORY='example/WotMods',
                        FAKE_RELEASE_LIST=str(self.list_path),
                        FAKE_RELEASE_DIR=str(self.previous))
        self.previous_release()

    def previous_release(self, immutable=True):
        self.list_path.write_text(json.dumps([{
            'tagName': 'sessionstats-v0.2.4', 'isLatest': True, 'isDraft': False,
            'isPrerelease': False, 'isImmutable': immutable}]))
        (self.previous / 'com.staysharp.medkitreminder_1.6.2.wotmod').write_bytes(b'old-staysharp')
        (self.previous / 'grz.sessionstats_0.2.4.wotmod').write_bytes(b'unchanged-stats')
        (self.previous / 'wot-statystyki-sesji-v0.2.4.zip').write_bytes(b'unchanged-installer')
        (self.previous / 'grz.sessionstats.json').write_bytes(b'{"language":"en"}')
        manifest(self.previous)

    def run_snapshot(self, *patterns):
        if not patterns:
            patterns = ('com.staysharp.medkitreminder_*.wotmod',)
        return subprocess.run(['bash', str(SCRIPT), str(self.dist), *patterns],
                              capture_output=True, text=True, env=self.env)

    def test_carries_stats_exactly_while_replacing_only_staysharp(self):
        result = self.run_snapshot()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.dist / self.own).read_bytes(), b'updated-staysharp')
        self.assertFalse((self.dist / 'com.staysharp.medkitreminder_1.6.2.wotmod').exists())
        for filename in ('grz.sessionstats_0.2.4.wotmod',
                         'grz.sessionstats.json', 'wot-statystyki-sesji-v0.2.4.zip'):
            self.assertEqual((self.dist / filename).read_bytes(),
                             (self.previous / filename).read_bytes())
        subprocess.run(['sha256sum', '-c', 'SHA256SUMS.txt'], cwd=self.dist,
                       check=True, stdout=subprocess.DEVNULL)

    def test_no_previous_release_is_supported(self):
        self.list_path.write_text('[]')
        result = self.run_snapshot()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(sorted(p.name for p in self.dist.iterdir()),
                         ['SHA256SUMS.txt', self.own])

    def test_mutable_source_is_rejected(self):
        self.previous_release(immutable=False)
        result = self.run_snapshot()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('not immutable', result.stderr)

    def test_corrupted_previous_asset_fails_closed(self):
        (self.previous / 'grz.sessionstats_0.2.4.wotmod').write_bytes(b'tampered')
        result = self.run_snapshot()
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.dist / 'grz.sessionstats_0.2.4.wotmod').exists())

    def test_previous_release_cannot_contain_unlisted_asset(self):
        (self.previous / 'extra.json').write_bytes(b'unverified')
        result = self.run_snapshot()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('unlisted', result.stderr)

    def test_previous_release_requires_checksum_manifest(self):
        (self.previous / 'SHA256SUMS.txt').unlink()
        result = self.run_snapshot()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('lacks checksum', result.stderr)

    def test_published_releases_without_latest_fail_closed(self):
        self.list_path.write_text(json.dumps([{
            'tagName': 'v1.6.2', 'isLatest': False, 'isDraft': False,
            'isPrerelease': False, 'isImmutable': True}]))
        result = self.run_snapshot()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('none is marked Latest', result.stderr)

    def test_output_name_collision_is_not_overwritten(self):
        (self.dist / 'grz.sessionstats.json').write_bytes(b'new-configuration')
        manifest(self.dist)
        result = self.run_snapshot()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Asset name conflict', result.stderr)

    def test_generic_helper_replaces_a_different_mod_instead(self):
        (self.dist / self.own).unlink()
        name = 'grz.sessionstats_0.2.5.wotmod'
        (self.dist / name).write_bytes(b'new-sessionstats')
        manifest(self.dist)
        result = self.run_snapshot('grz.sessionstats_*.wotmod')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.dist / name).read_bytes(), b'new-sessionstats')
        self.assertFalse((self.dist / 'grz.sessionstats_0.2.4.wotmod').exists())
        self.assertEqual((self.dist / 'com.staysharp.medkitreminder_1.6.2.wotmod').read_bytes(),
                         b'old-staysharp')


if __name__ == '__main__':
    unittest.main()
