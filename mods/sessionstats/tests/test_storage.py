# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import hashlib
import json
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src'))
from grz_session_stats.storage import GenerationStore, StorageError, UnsupportedSchemaError, canonical_bytes
try:
    import builtins
except ImportError:
    import __builtin__ as builtins


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.mkdtemp(prefix='grz-storage-test-')
        self.store = GenerationStore(self.directory)

    def tearDown(self):
        shutil.rmtree(self.directory)

    def payload(self, value):
        return {'schema_version': 1, 'value': value, 'label': 'Za\u017c\u00f3\u0142\u0107 g\u0119\u015bl\u0105 ja\u017a\u0144'}

    def test_roundtrip_and_bounded_backups(self):
        self.assertIsNone(self.store.load())
        for value in range(8):
            self.store.save(self.payload(value))
        loaded = GenerationStore(self.directory)
        self.assertEqual(loaded.load(), self.payload(7))
        self.assertEqual(len(loaded._files()), 3)

    def test_truncated_latest_recovers_previous_and_next_save_advances(self):
        self.store.save(self.payload(1))
        self.store.save(self.payload(2))
        latest = self.store._files()[0][1]
        with open(latest, 'wb') as handle:
            handle.write(b'{"storage_version":')
        recovered = GenerationStore(self.directory)
        self.assertEqual(recovered.load(), self.payload(1))
        self.assertIsNotNone(recovered.warning)
        recovered.save(self.payload(3))
        self.assertEqual(recovered.sequence, 3)
        self.assertEqual(GenerationStore(self.directory).load(), self.payload(3))

    def test_checksum_detects_well_formed_but_tampered_payload(self):
        self.store.save(self.payload(1))
        self.store.save(self.payload(2))
        path = self.store._files()[0][1]
        with open(path, 'rb') as handle:
            envelope = json.loads(handle.read().decode('utf-8'))
        envelope['payload']['value'] = 999
        with open(path, 'wb') as handle:
            handle.write(canonical_bytes(envelope))
        self.assertEqual(GenerationStore(self.directory).load(), self.payload(1))

    def test_uncommitted_tempfile_is_ignored(self):
        self.store.save(self.payload(1))
        with open(os.path.join(self.directory, '.state-999.tmp'), 'wb') as handle:
            handle.write(b'partial uncommitted data')
        self.assertEqual(GenerationStore(self.directory).load(), self.payload(1))

    def test_rename_failure_preserves_committed_state(self):
        self.store.save(self.payload(1))
        original = os.rename
        def fail(unused_source, unused_destination):
            raise OSError('simulated pre-commit crash')
        os.rename = fail
        try:
            self.assertRaises(StorageError, self.store.save, self.payload(2))
        finally:
            os.rename = original
        self.assertEqual(GenerationStore(self.directory).load(), self.payload(1))
        self.assertEqual(self.store.sequence, 1)

    def test_fsync_failure_does_not_create_a_committed_generation(self):
        self.store.save(self.payload(1))
        original = os.fsync
        def fail(unused_descriptor):
            raise OSError('simulated fsync failure')
        os.fsync = fail
        try:
            self.assertRaises(StorageError, self.store.save, self.payload(2))
        finally:
            os.fsync = original
        self.assertEqual(GenerationStore(self.directory).load(), self.payload(1))

    def test_unknown_schema_refuses_fallback_and_all_mutations(self):
        self.store.save(self.payload(1))
        payload = self.payload(2)
        payload['schema_version'] = 2
        envelope = {'storage_version': 1, 'generation': 2, 'payload': payload,
                    'payload_checksum': hashlib.sha256(canonical_bytes(payload)).hexdigest()}
        path = os.path.join(self.directory, 'state-%020d.json' % 2)
        with open(path, 'wb') as handle:
            handle.write(canonical_bytes(envelope))
        newer = GenerationStore(self.directory)
        self.assertRaises(UnsupportedSchemaError, newer.load)
        self.assertTrue(newer.read_only)
        self.assertRaises(StorageError, newer.save, self.payload(3))
        self.assertEqual(len(newer._files()), 2)

    def test_all_corrupt_generations_are_not_silently_reinitialized(self):
        self.store.save(self.payload(1))
        with open(self.store._files()[0][1], 'wb') as handle:
            handle.write(b'broken')
        broken = GenerationStore(self.directory)
        self.assertRaises(StorageError, broken.load)
        self.assertRaises(StorageError, broken.save, self.payload(2))

    def test_stale_writer_cannot_replace_newer_state(self):
        self.store.save(self.payload(1))
        other = GenerationStore(self.directory)
        other.load()
        self.store.save(self.payload(2))
        self.assertRaises(StorageError, other.save, self.payload(999))
        self.assertEqual(GenerationStore(self.directory).load(), self.payload(2))
        self.assertEqual(other.load(), self.payload(2))
        other.save(self.payload(3))
        self.assertEqual(GenerationStore(self.directory).load(), self.payload(3))

    def test_nonfinite_data_cannot_be_saved(self):
        self.assertRaises(StorageError, self.store.save, self.payload(float('nan')))
        self.assertIsNone(GenerationStore(self.directory).load())

    def test_windows_missing_msvcrt_can_save_with_explicit_fallback_warning(self):
        original_name = os.name
        original_import = builtins.__import__
        def missing(name, *args, **kwargs):
            if name == 'msvcrt':
                raise ImportError('not shipped by embedded runtime')
            return original_import(name, *args, **kwargs)
        os.name = 'nt'
        builtins.__import__ = missing
        try:
            self.store.save(self.payload(1))
            self.assertIsNotNone(self.store.warning)
        finally:
            os.name = original_name
            builtins.__import__ = original_import
        self.assertEqual(GenerationStore(self.directory).load(), self.payload(1))


if __name__ == '__main__':
    unittest.main()
