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
        self.assertIn(b'Version 0.2.8', readme)

    def test_historical_changelog_is_not_rewritten(self):
        content = (self.build.ROOT/'ZMIANY.txt').read_bytes()
        self.assertEqual(self.build.render_guide('ZMIANY.txt', content, '0.2.8', '2.5.0.0'), content)

    def test_every_release_field_advances_again_from_a_stamped_source_bundle(self):
        fields = {
            'README_PL.txt': ('Version {version} ',),
            'README.md': ('Version {version} source:',),
            'CONTRACT.txt': ('IMPLEMENTATION CONTRACT v{version} ', " version: '{version}',"),
            'docs/APPEARANCE_CONFIG.md': ('# Appearance and scrolling configuration — {version}\n',),
        }
        source_version = self.build.VERSION
        guides = {name: (self.build.ROOT/name).read_bytes() for name in fields}
        major, minor, patch = map(int, source_version.split('.'))
        versions = ('%d.%d.%d' % (major, minor, patch + 1), '%d.0.0' % (major + 1))
        try:
            for version in versions:
                guides = {name: self.build.render_guide(name, content, version, '2.5.0.0')
                          for name, content in guides.items()}
                for name, markers in fields.items():
                    for marker in markers:
                        self.assertIn(marker.format(version=version).encode('utf-8'), guides[name], name)
                        self.assertNotIn(marker.format(version=self.build.VERSION).encode('utf-8'), guides[name], name)
                # The extracted builder reads the new source/VERSION on rebuild.
                self.build.VERSION = version
        finally:
            self.build.VERSION = source_version

    def test_active_guides_keep_explicit_historical_version_evidence(self):
        historical = {
            'README.md': b'The user tested 0.2.4',
            'README_PL.txt': b'Since 0.2.7,',
            'CONTRACT.txt': b'Historical compatibility: upgrading from 0.2.6 to 0.2.7',
        }
        for name, marker in historical.items():
            original = (self.build.ROOT/name).read_bytes()
            self.assertIn(marker, original)
            self.assertIn(marker, self.build.render_guide(name, original, '1.0.0', '2.5.0.0'))

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
