# -*- coding: utf-8 -*-
"""Builder contracts; Python 2.7 runs only the game-runtime tests."""
from __future__ import unicode_literals
import os
import shutil
import subprocess
import sys
import tempfile
import unittest


@unittest.skipUnless(sys.version_info[0] >= 3, 'Packaging uses Python 3')
class BuildContracts(unittest.TestCase):
    def setUp(self):
        import importlib.util
        from pathlib import Path
        root = Path(__file__).resolve().parents[1]
        spec = importlib.util.spec_from_file_location('sessionstats_builder', root/'tools/build.py')
        self.build = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.build)
        self.directory = Path(tempfile.mkdtemp(prefix='sessionstats-builder-test-'))

    def tearDown(self):
        shutil.rmtree(str(self.directory))

    def test_active_guides_use_requested_package_and_client_versions(self):
        for name in self.build.RELEASE_GUIDES:
            original = (self.build.ROOT/name).read_bytes()
            rendered = self.build.render_guide(name, original, '0.2.8', '2.5.0.0')
            self.assertNotIn(b'grz.sessionstats_0.2.7.wotmod', rendered)
            if b'grz.sessionstats_0.2.7.wotmod' in original:
                self.assertIn(b'grz.sessionstats_0.2.8.wotmod', rendered)
            self.assertNotIn(b'mods/2.4.1.0/', rendered)
        readme = self.build.render_guide('README_PL.txt', (self.build.ROOT/'README_PL.txt').read_bytes(), '0.2.8','2.5.0.0')
        self.assertIn(b'Wersja 0.2.8', readme)

    def test_historical_changelog_is_not_rewritten(self):
        content = (self.build.ROOT/'ZMIANY.txt').read_bytes()
        self.assertEqual(self.build.render_guide('ZMIANY.txt', content, '0.2.8', '2.5.0.0'), content)

    def test_default_guides_are_byte_identical(self):
        for name in self.build.RELEASE_GUIDES:
            content = (self.build.ROOT/name).read_bytes()
            self.assertEqual(self.build.render_guide(name, content, self.build.VERSION, '2.4.1.0'), content)

    def test_installer_manifest_verifies_from_extracted_archive_root(self):
        files=[]
        for name, relative in [('grz.sessionstats_0.2.8.wotmod','mods/2.5.0.0/'),
                               ('net.openwg.gameface_1.2.2.wotmod','mods/2.5.0.0/net.openwg/'),
                               ('grz.sessionstats.json','mods/2.5.0.0/'),
                               ('grz.sessionstats.languages.json','mods/2.5.0.0/')]:
            path = self.directory/relative/name
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_bytes(name.encode('ascii')); files.append(path)
        manifest = self.build.installer_checksums(files[0], files[1], files[2], '2.5.0.0', files[3])
        (self.directory/'SHA256SUMS.txt').write_bytes(manifest)
        self.assertEqual(len(manifest.splitlines()),4)
        subprocess.check_output(['sha256sum','-c','SHA256SUMS.txt'],cwd=str(self.directory))


if __name__ == '__main__': unittest.main()
