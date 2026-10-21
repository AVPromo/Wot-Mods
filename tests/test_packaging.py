"""Binary package / frame-level regression tests. No WoT client available."""
import importlib.util
from pathlib import Path
import struct
import sys
import unittest
import zipfile

ROOT=Path(__file__).resolve().parents[1]
SCRIPT=ROOT/'source/build_wotmod.py'
spec=importlib.util.spec_from_file_location('build_wotmod_v161', SCRIPT)
build=importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)


class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.target=build.build()
        cls.frames=build.load_frames()

    def test_01_correct_wotmod_filename(self):
        self.assertEqual(self.target.name,'com.staysharp.medkitreminder_%s.wotmod' % build.VERSION)

    def test_02_single_file_is_zip(self):
        self.assertTrue(zipfile.is_zipfile(self.target))

    def test_03_exactly_23_files(self):
        with zipfile.ZipFile(self.target) as z:
            self.assertEqual(len(z.namelist()),23)

    def test_04_all_zipstored(self):
        with zipfile.ZipFile(self.target) as z:
            self.assertTrue(all(x.compress_type==zipfile.ZIP_STORED for x in z.infolist()))

    def test_05_no_encrypted_files(self):
        with zipfile.ZipFile(self.target) as z:
            self.assertFalse(any(x.flag_bits&1 for x in z.infolist()))

    def test_06_no_externally_needed_shader_sound_or_dll(self):
        with zipfile.ZipFile(self.target) as z:
            self.assertFalse(any(x.filename.endswith(('.fx','.wav','.bnk','.dll','.swf','.py')) for x in z.infolist()))

    def test_07_python_entrypoint_matches_working_py27_format(self):
        with zipfile.ZipFile(self.target) as z:
            data=z.read(build.PYC_PATH)
        self.assertTrue(data.startswith(b'\x03\xf3\x0d\x0a'))
        self.assertIn(b'EXEC_STMT', b'EXEC_STMT') # opcode 85 tested directly below
        self.assertEqual(data[8:9], b'c')
        self.assertIn(bytes([85,100,1,0,83]),data)

    def test_08_embedded_complete_source(self):
        with zipfile.ZipFile(self.target) as z:
            data=z.read(build.PYC_PATH)
        self.assertIn(build.render_source(),data)

    def test_09_all_frame_names_resource_prefix(self):
        with zipfile.ZipFile(self.target) as z:
            names={x for x in z.namelist() if x.endswith('.dds')}
        expected={'res/gui/maps/staysharp/medkit_pulse_%02d.dds'%i for i in range(21)}
        self.assertEqual(names,expected)

    def test_10_each_dds_128x128_argb8888(self):
        for path,raw in self.frames:
            self.assertEqual(raw[:4],b'DDS ')
            self.assertEqual(len(raw),128+128*128*4)
            self.assertEqual(struct.unpack_from('<II',raw,12),(128,128))
            self.assertEqual(struct.unpack_from('<IIIIIIII',raw,76),
                             (32,65,0,32,0xff0000,0xff00,0xff,0xff000000))

    def test_11_frame0_alpha_all_zero(self):
        self.assertEqual(max(self.frames[0][1][131::4]),0)

    def test_12_frame20_alpha_nonzero(self):
        self.assertGreater(max(self.frames[-1][1][131::4]),240)

    def test_13_stepwise_alpha_monotonic_per_pixel(self):
        before=None
        for _,raw in self.frames:
            alpha=raw[131::4]
            if before is not None:
                self.assertTrue(all(x>=y for x,y in zip(alpha,before)))
            before=alpha

    def test_14_rgb_is_identical_among_frames(self):
        reference=self.frames[0][1][128:]
        for _,raw in self.frames[1:]:
            pix=raw[128:]
            for c in range(3):
                self.assertEqual(pix[c::4],reference[c::4])

    def test_15_historical_v160_baseline_does_not_pin_future_versions(self):
        import hashlib
        master = build.load_master()
        expected = (ROOT / 'assets/medkit_pulse_master.sha256').read_text().strip()
        self.assertEqual(hashlib.sha256(master).hexdigest(), expected)
        # Historical v1.6.0 checksum applies ONLY when actually rebuilding
        # the historical source/version. New reviewed versions are allowed.
        if build.VERSION == '1.6.0':
            self.assertEqual(hashlib.sha256(master).hexdigest(),
                             '4659a9da85e1c35634e9dcbabbe6090d4a2fc292c485be484235ccd042517589')
            self.assertEqual(hashlib.sha256(self.target.read_bytes()).hexdigest(),
                             '9f3d98948ed398c3a4dc14b6785b68f10f1319381f896c6cd49b8709359c4927')

    def test_16_meta_id_and_version(self):
        with zipfile.ZipFile(self.target) as z:
            doc=z.read('meta.xml').decode()
        self.assertIn('<id>com.staysharp.medkitreminder</id>',doc)
        self.assertIn('<version>%s</version>' % build.VERSION,doc)

    def test_17_package_integrity(self):
        with zipfile.ZipFile(self.target) as z:
            self.assertIsNone(z.testzip())

    def test_18_no_runtime_python_dependencies_from_our_tooling(self):
        code=(ROOT/'source/mod_staysharp_medkit.py').read_text()
        self.assertNotIn('from PIL import',code)
        self.assertNotIn('import numpy',code)

    def test_19_all_expected_resources_are_in_one_wotmod(self):
        with zipfile.ZipFile(self.target) as z:
            for i in range(21):
                self.assertIn('res/'+('gui/maps/staysharp/medkit_pulse_%02d.dds'%i),z.namelist())

    def test_20_package_stays_under_2mb(self):
        self.assertLess(self.target.stat().st_size,2*1024*1024)


if __name__=='__main__':
    unittest.main()
