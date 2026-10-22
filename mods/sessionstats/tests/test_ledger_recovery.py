# -*- coding: utf-8 -*-
"""Generation selection must include account/installation ledger validation."""
from __future__ import unicode_literals

import copy
import hashlib
import os
import shutil
import tempfile
import unittest

from test_core import Clock, EXPECTED, result
from grz_session_stats.core import StatsService
from grz_session_stats.sessions import InstallationSession
from grz_session_stats.storage import canonical_bytes


class LedgerRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.mkdtemp(prefix='grz-ledger-recovery-')
        self.clock = Clock(100)
        self.service = StatsService(self.directory, 'EU:1', 'run-a', EXPECTED, self.clock)
        self.clock.value = 120
        self.assertTrue(self.service.record_result(result('1', started_at=110)))
        self.clock.value = 140
        self.assertIsNotNone(self.service.reset_manual())
        self.clock.value = 160
        self.assertTrue(self.service.record_result(result('2', started_at=150, ended_at=160)))
        self.good = copy.deepcopy(self.service._state)

    def tearDown(self):
        shutil.rmtree(self.directory)

    def files(self, store=None):
        files = {}
        for unused, path in (store or self.service.store)._files():
            with open(path, 'rb') as stream:
                files[path] = stream.read()
        return files

    def write_envelope(self, generation, payload, storage_version=1):
        envelope = {'storage_version': storage_version, 'generation': generation,
                    'payload': payload, 'payload_checksum': hashlib.sha256(canonical_bytes(payload)).hexdigest()}
        path = os.path.join(self.service.store.directory, 'state-%020d.json' % generation)
        with open(path, 'wb') as stream:
            stream.write(canonical_bytes(envelope))

    def assert_recovery(self, damaged):
        bad_generation = self.service.store.save(damaged)
        before = self.files()
        self.clock.value = 200
        restored = StatsService(self.directory, 'EU:1', 'run-b', EXPECTED, self.clock)
        self.assertIsNone(restored.last_error)
        self.assertFalse(restored.store.read_only)
        self.assertIsNotNone(restored.store.warning)
        self.assertEqual(restored._state['battles'], self.good['battles'])
        self.assertEqual(restored._state['current_manual_id'], self.good['current_manual_id'])
        snapshot = restored.snapshot()
        self.assertEqual(snapshot['scopes']['manual']['summary']['battles'], 1)
        self.assertEqual(snapshot['scopes']['launch']['summary']['battles'], 0)
        self.assertIn(restored.store.warning, snapshot['warnings'])
        self.assertEqual(restored.store.sequence, bad_generation + 1)
        # Recovery commits a fresh generation without rewriting the failed
        # candidate or the valid backup it selected (normal retention applies).
        after = self.files(restored.store)
        for path, content in after.items():
            if path in before:
                self.assertEqual(content, before[path])
        self.clock.value = 220
        self.assertTrue(restored.record_result(result('3', started_at=210, ended_at=220)))
        self.clock.value = 300
        reopened = StatsService(self.directory, 'EU:1', 'run-c', EXPECTED, self.clock)
        self.assertIsNone(reopened.last_error)
        self.assertEqual(set(reopened._state['battles']), {'1', '2', '3'})
        self.assertEqual(reopened._state['current_manual_id'], self.good['current_manual_id'])
        self.assertEqual(reopened.snapshot()['scopes']['manual']['summary']['battles'], 2)

    def test_empty_manual_periods_recover_history_and_reset_epoch(self):
        damaged = copy.deepcopy(self.good)
        damaged['manual_sessions'] = []
        self.assert_recovery(damaged)

    def test_malformed_battle_recovers_history(self):
        damaged = copy.deepcopy(self.good)
        damaged['battles']['2'] = []
        self.assert_recovery(damaged)

    def test_malformed_launch_period_recovers_history(self):
        damaged = copy.deepcopy(self.good)
        damaged['launch_sessions'][0] = None
        self.assert_recovery(damaged)

    def test_missing_current_manual_period_recovers_history(self):
        damaged = copy.deepcopy(self.good)
        damaged['current_manual_id'] = 'missing-epoch'
        self.assert_recovery(damaged)

    def test_wrong_account_ledger_recovers_only_the_matching_accounts_backup(self):
        damaged = copy.deepcopy(self.good)
        damaged['account_key'] = 'EU:2'
        self.assert_recovery(damaged)

    def test_multiple_invalid_generations_continue_to_the_last_valid_ledger(self):
        damaged = copy.deepcopy(self.good)
        damaged['manual_sessions'] = []
        self.service.store.save(damaged)
        damaged['battles'] = []
        self.assert_recovery(damaged)

    def test_all_invalid_ledgers_remain_read_only_and_are_not_reinitialized(self):
        damaged = copy.deepcopy(self.good)
        damaged['manual_sessions'] = []
        for unused in range(self.service.store.keep_generations):
            self.service.store.save(damaged)
        before = self.files()
        restored = StatsService(self.directory, 'EU:1', 'run-b', EXPECTED, self.clock)
        self.assertTrue(restored.store.read_only)
        self.assertIsNotNone(restored.last_error)
        self.assertFalse(restored.record_result(result('3')))
        self.assertIsNone(restored.reset_manual())
        self.assertEqual(self.files(), before)

    def test_invalid_newest_ledger_cannot_bypass_an_unsupported_older_generation(self):
        latest = self.service.store.sequence
        damaged = copy.deepcopy(self.good)
        damaged['manual_sessions'] = []
        for storage_version, schema in ((1, 999), (999, 1)):
            unsupported = dict(damaged, schema_version=schema)
            self.write_envelope(latest + 1, unsupported, storage_version)
            self.write_envelope(latest + 2, damaged)
            before = self.files()
            restored = StatsService(self.directory, 'EU:1', 'run-b', EXPECTED, self.clock)
            self.assertTrue(restored.store.read_only)
            self.assertIsNotNone(restored.last_error)
            self.assertIsNone(restored.store.warning)
            self.assertFalse(restored.record_result(result('3')))
            self.assertEqual(self.files(), before)

    def test_valid_newest_ledger_is_not_replaced_by_an_older_snapshot(self):
        self.clock.value = 180
        self.assertTrue(self.service.record_result(result('3', started_at=170, ended_at=180)))
        restored = StatsService(self.directory, 'EU:1', 'run-b', EXPECTED, self.clock)
        self.assertIsNone(restored.last_error)
        self.assertIsNone(restored.store.warning)
        self.assertEqual(set(restored._state['battles']), {'1', '2', '3'})
        self.assertEqual(restored.snapshot()['scopes']['manual']['summary']['battles'], 2)

    def test_valid_closed_launch_is_not_treated_as_damage_to_reopen_older_history(self):
        closed = copy.deepcopy(self.good)
        closed['launch_sessions'][0]['ended_at'] = 180
        self.service.store.save(closed)
        self.clock.value = 200
        before = self.files()
        restored = StatsService(self.directory, 'EU:1', 'run-a', EXPECTED, self.clock)
        self.assertTrue(restored.store.read_only)
        self.assertIsNotNone(restored.last_error)
        self.assertIsNone(restored.store.warning)
        self.assertEqual(self.files(), before)

    def test_installation_scope_recovers_history_and_its_independent_reset(self):
        game = os.path.join(self.directory, 'game')
        self.clock.value = 100
        shared = InstallationSession(self.directory, game, 'run-a', EXPECTED, self.clock)
        self.clock.value = 120
        shared.begin('EU:1', result())
        shared.result('EU:1', result())
        self.clock.value = 140
        self.assertIsNotNone(shared.reset())
        self.clock.value = 160
        shared.begin('EU:2', result('2', started_at=150, ended_at=160))
        shared.result('EU:2', result('2', started_at=150, ended_at=160))
        good = copy.deepcopy(shared.service._state)
        damaged = copy.deepcopy(good)
        damaged['battles'] = []
        latest = shared.service.store.save(damaged)
        self.clock.value = 200
        restored = InstallationSession(self.directory, game, 'run-b', EXPECTED, self.clock)
        self.assertFalse(restored.service.store.read_only)
        self.assertIsNone(restored.service.last_error)
        self.assertIsNotNone(restored.service.store.warning)
        self.assertEqual(restored.service._state['battles'], good['battles'])
        self.assertEqual(restored.service._state['current_manual_id'], good['current_manual_id'])
        self.assertEqual(restored.snapshot()[0]['summary']['battles'], 1)
        self.assertEqual(restored.service.store.sequence, latest + 1)


if __name__ == '__main__':
    unittest.main()
