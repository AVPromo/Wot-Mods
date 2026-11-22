# -*- coding: utf-8 -*-
"""Late installation discovery must retain live provenance during startup."""
from __future__ import unicode_literals

import errno
import shutil
import tempfile
import unittest
import uuid

from test_core import Clock, EXPECTED
from test_config_path import changed
from test_normalize import raw_result, START, ARENA_ID
from test_runtime import FakeAPI, FakeWindow, wait_for_combat_capture
from grz_session_stats import config_path, runtime
from grz_session_stats.sessions import InstallationSession


class LateInstallationLoadingTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.mkdtemp(prefix='grz-late-installation-')
        self.clock = Clock(START - 10)
        self.api = FakeAPI()
        self.resolver = changed(config_path, 'find_installation_root', lambda: None)
        self.resolver.__enter__()
        self.mod = self.open()

    def tearDown(self):
        wait_for_combat_capture(self.mod)
        self.mod.stop()
        self.resolver.__exit__(None, None, None)
        shutil.rmtree(self.directory)

    def open(self, root=None):
        mod = runtime.Runtime(api=self.api, data_dir=self.directory, expected_table=EXPECTED,
                              now=self.clock, window=FakeWindow(), footer_installer=lambda unused: None,
                              installation_dir=root)
        mod.start()
        return mod

    def begin(self):
        self.clock.value = START + 10
        self.api.battle = True
        self.api.context = {'arena_id': str(ARENA_ID), 'started_at': START,
                            'vehicle_id': 1, 'map_id': 'map'}
        self.mod._on_avatar()
        self.assertIsNone(self.mod._instance_session)
        self.assertTrue(self.mod.active_service.loading)
        wait_for_combat_capture(self.mod)

    def discover(self):
        self.mod._installation_dir = self.directory
        self.api.battle = False
        self.api.events.onAccountShowGUI()
        self.assertIsNotNone(self.mod._instance_session)

    def finish(self):
        self.api.battle = False
        self.api.events.onAccountShowGUI()
        self.load_history()
        self.api.fire(self.mod._tick_id)

    def load_history(self):
        for unused in range(10000):
            if self.mod._load_id is None:
                break
            self.api.fire(self.mod._load_id)
        self.assertFalse(self.mod._loading_services())
        self.assertTrue(self.mod.active_service.ready, self.mod.active_service.last_error)
        if self.mod._instance_session is not None:
            self.assertTrue(self.mod._instance_session.service.ready)

    def discover_after_failed_binding(self):
        self.begin()
        self.clock.value = START + 400
        self.api.events.onBattleResultsReceived(True, raw_result())
        wait_for_combat_capture(self.mod)
        intake = self.mod._combat_intake
        publish = intake._publish
        attempts = []

        def fail_first_marker(path, encoded):
            if path.endswith('.installation'):
                attempts.append(path)
                if len(attempts) == 1:
                    raise OSError(errno.EACCES, 'Synthetic temporary file lock')
            return publish(path, encoded)

        intake._publish = fail_first_marker
        self.mod._installation_dir = self.directory
        self.api.battle = False
        self.assertIsNotNone(self.mod._ensure_installation_session())
        self.mod._schedule_loading()
        self.load_history()
        account, service = self.mod.active_key, self.mod.active_service
        self.mod._drain_account_captures(intake, account, service)
        self.assertEqual(len(attempts), 1)
        self.assertIsNone(intake.bound_installation(runtime.LAUNCH_ID))
        self.assertEqual(service.snapshot()['scopes']['manual']['summary']['battles'], 1)
        self.assertEqual(self.mod._instance_session.snapshot()[0]['summary']['battles'], 0)
        self.assertEqual([row[1] for row in intake.pending(account, limit=2)], ['begin', 'result'])
        return intake, attempts

    def test_transient_marker_failure_retries_in_garage_before_acknowledging(self):
        intake, attempts = self.discover_after_failed_binding()
        account = self.mod.active_key
        self.mod._drain_installation_captures(intake, account, self.mod.active_service)
        self.assertEqual(self.mod._instance_session.snapshot()[0]['summary']['battles'], 0)
        self.assertEqual([row[1] for row in intake.pending(account, limit=2)], ['begin', 'result'])
        self.api.fire(self.mod._tick_id)
        self.assertEqual(len(attempts), 2)
        session = self.mod._instance_session
        self.assertEqual(intake.bound_installation(runtime.LAUNCH_ID), session.service.account_key)
        self.assertEqual(session.snapshot()[0]['summary']['battles'], 1)
        self.assertEqual(intake.pending(self.mod.active_key), [])

    def test_transient_marker_failure_retries_at_shutdown_and_recovers_after_restart(self):
        intake, attempts = self.discover_after_failed_binding()
        self.mod.stop()
        self.clock.value = START + 86400
        with changed(runtime, 'LAUNCH_ID', uuid.uuid4().hex):
            self.mod = self.open(self.directory)
            self.finish()
            self.assertEqual(self.mod.active_service.snapshot()['scopes']['manual']['summary']['battles'], 1)
            session = self.mod._instance_session
            self.assertEqual(self.mod._combat_intake.pending(self.mod.active_key), [])
            self.assertEqual(session.snapshot()[0]['summary']['battles'], 1)
        self.assertEqual(len(attempts), 2)
        self.assertIsNotNone(intake.bound_installation(runtime.LAUNCH_ID))

    def test_garage_revision_survives_late_binding_and_restart_between_replay_batches(self):
        self.begin()
        self.clock.value = START + 410
        self.api.events.onBattleResultsReceived(True, raw_result())
        wait_for_combat_capture(self.mod)
        self.finish()
        self.assertIsNone(self.mod._instance_session)
        account = self.mod.active_key
        self.assertEqual(self.mod.active_service._state['battles'][ARENA_ID]['damage'], 2100)

        self.clock.value = START + 490
        revised = raw_result()
        revised['personal'][1]['damageDealt'] = 2700
        self.api.events.onBattleResultsReceived(True, revised)
        wait_for_combat_capture(self.mod)
        self.api.fire(self.mod._tick_id)
        self.assertEqual(self.mod.active_service._state['battles'][ARENA_ID]['damage'], 2700)

        self.discover()
        self.load_history()
        self.api.fire(self.mod._tick_id)
        # Installation replay consumes at most two captures per tick. The
        # correction must still exist after the earlier beginning and result.
        pending = self.mod._combat_intake.pending(account, limit=3)
        self.mod.stop()
        self.clock.value = START + 86400
        with changed(runtime, 'LAUNCH_ID', uuid.uuid4().hex):
            self.mod = self.open(self.directory)
            self.finish()
            installation = self.mod._instance_session
            battle_key = installation.battle_key(account, ARENA_ID)
            self.assertEqual(installation.service._state['battles'][battle_key]['damage'], 2700)
            self.assertEqual(self.mod.active_service._state['battles'][ARENA_ID]['damage'], 2700)
            self.assertEqual(self.mod._combat_intake.pending(account), [])
        self.assertEqual([(kind, capture['record']['damage']) for receipt, kind, capture in pending],
                         [('result', 2700)])

    def restart(self):
        wait_for_combat_capture(self.mod)
        self.mod.stop()
        self.api.battle = False
        self.clock.value = START + 86400
        with changed(runtime, 'LAUNCH_ID', runtime.LAUNCH_ID + '-restart'):
            self.mod = self.open(self.directory)
        self.finish()

    def assert_recovered_once(self):
        self.mod._on_results(True, raw_result())
        session = self.mod._instance_session
        self.assertEqual(session.snapshot()[0]['summary']['battles'], 1)
        sequence = session.service.store.sequence
        self.mod._on_results(True, raw_result())
        self.assertEqual(session.service.store.sequence, sequence)
        self.assertEqual(session.snapshot()[0]['summary']['battles'], 1)

    def test_shutdown_before_loading_finishes_retains_beginning_for_recovered_result(self):
        self.begin()
        self.discover()
        self.assertTrue(self.mod.active_service.loading)
        self.restart()
        self.assert_recovered_once()

    def test_shutdown_after_loading_finishes_retains_beginning_for_recovered_result(self):
        self.begin()
        self.discover()
        self.finish()
        self.restart()
        self.assert_recovered_once()

    def test_ready_backfill_keeps_result_with_original_account_after_switch(self):
        self.begin()
        first = self.mod.active_service
        self.clock.value = START + 400
        self.mod._on_results(True, raw_result())
        wait_for_combat_capture(self.mod)
        self.discover()
        self.api.battle = False
        self.api.dbid = 8
        self.mod._on_account()
        self.finish()
        self.assertTrue(first.ready, first.last_error)
        session = self.mod._instance_session
        records = session.service._state['battles']
        self.assertIn(InstallationSession.battle_key('EU:7', ARENA_ID), records)
        self.assertNotIn(InstallationSession.battle_key('EU:8', ARENA_ID), records)
        self.assertEqual(session.snapshot()[0]['summary']['battles'], 1)
