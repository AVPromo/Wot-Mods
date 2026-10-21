# -*- coding: utf-8 -*-
"""Configuration reloads exercise the real runtime, collector and owned log."""
from __future__ import unicode_literals

import io
import json
import logging
import os
import shutil
import tempfile
import unittest

from test_runtime import FakeAPI, FakeWindow, Clock, EXPECTED
from test_normalize import raw_result
from grz_session_stats import appearance, config_path, runtime


class StyledFooter(object):
    def __init__(self):
        self.styles = []
        self.activity = []
        self.fail = False

    def set_appearance(self, value):
        if self.fail:
            raise RuntimeError('fixture model transaction failure')
        self.styles.append(value)

    def set_activity(self, pending, processing):
        self.activity.append((pending, processing))

    def uninstall(self):
        pass


class RuntimeAppearanceTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.mkdtemp(prefix='grz-runtime-appearance-')
        self.path = os.path.join(self.directory, 'grz.sessionstats.json')
        self.api = FakeAPI()
        self.clock = Clock()
        self.window = FakeWindow()
        self.footer = StyledFooter()
        self.old_disable = logging.root.manager.disable
        self.old_propagate = runtime.LOG.propagate
        logging.disable(logging.NOTSET)
        runtime.LOG.propagate = False
        self.mod = None

    def tearDown(self):
        if self.mod is not None:
            self.mod.stop()
        runtime.LOG.propagate = self.old_propagate
        logging.disable(self.old_disable)
        shutil.rmtree(self.directory)

    def write(self, content):
        if isinstance(content, dict):
            content = json.dumps(content, ensure_ascii=False)
        with io.open(self.path, 'w', encoding='utf-8') as handle:
            handle.write(content)

    def start(self, located=False):
        self.mod = runtime.Runtime(api=self.api, data_dir=self.directory,
                                   expected_table=EXPECTED, now=self.clock,
                                   window=self.window,
                                   footer_installer=lambda callback: self.footer,
                                   appearance_path=None if located else self.path)
        self.mod.start()

    def refresh(self):
        self.mod.on_action({'action': 'refresh'})

    def result(self):
        self.clock.value += 500
        self.api.events.onBattleResultsReceived(True, raw_result())

    def log(self):
        self.mod._log_handle.flush()
        with io.open(self.mod.log_path, 'r', encoding='utf-8') as handle:
            return handle.read()

    def defaults(self):
        return appearance.build_presentation(appearance.default_config())

    def test_start_publishes_validated_settings_to_panel_and_native_footer(self):
        self.write({'colors': {'window_background': '#123456',
                               'garage_spinner_border': '#abcdef'},
                    'scroll': {'speed_multiplier': 2}})
        self.start()
        value = self.mod.snapshot()['appearance']
        self.assertEqual(value['scroll_speed'], 2)
        self.assertIn('#123456', value['panel_css'])
        self.assertIn('#abcdef', self.footer.styles[-1])
        self.assertEqual(self.mod.appearance_path, self.path)

    def test_refresh_reloads_file_and_does_not_reset_recorded_statistics(self):
        self.write({'scroll': {'speed_multiplier': 2}})
        self.start()
        self.result()
        before = self.mod.active_service.snapshot()['scopes']['manual']['summary']
        self.assertEqual(before['battles'], 1)
        self.write({'scroll': {'speed_multiplier': 0.5},
                    'colors': {'table_row_background': '#102030'}})
        self.refresh()
        self.assertEqual(self.mod.snapshot()['appearance']['scroll_speed'], 0.5)
        self.assertIn('#102030', self.mod.snapshot()['appearance']['panel_css'])
        self.assertEqual(self.mod.active_service.snapshot()['scopes']['manual']['summary'], before)
        self.assertGreater(self.window.refreshes, 0)

    def test_open_reloads_without_restarting_the_game(self):
        self.start()
        self.write({'scroll': {'speed_multiplier': 3}})
        self.assertTrue(self.mod.open_window())
        self.assertEqual(self.mod.snapshot()['appearance']['scroll_speed'], 3)

    def test_malformed_edit_reverts_entire_presentation_and_logs_after_start(self):
        self.write({'scroll': {'speed_multiplier': 4}})
        self.start()
        self.write('{"scroll": {')
        self.refresh()
        self.assertEqual(self.mod.snapshot()['appearance'], self.defaults())
        self.assertEqual(self.footer.styles[-1], self.defaults()['footer_css'])
        self.assertIn('CONFIG parse failed', self.log())

    def test_invalid_field_keeps_other_valid_settings_and_logs_its_name(self):
        self.write({'scroll': {'speed_multiplier': True},
                    'colors': {'window_background': '#334455'}})
        self.start()
        value = self.mod.snapshot()['appearance']
        self.assertEqual(value['scroll_speed'], 1.0)
        self.assertIn('#334455', value['panel_css'])
        self.assertIn('scroll.speed_multiplier', self.log())

    def test_missing_file_reverts_previous_override_on_refresh(self):
        self.write({'opacity': {'window': 0.6}})
        self.start()
        self.assertNotEqual(self.mod.snapshot()['appearance'], self.defaults())
        os.remove(self.path)
        self.refresh()
        self.assertEqual(self.mod.snapshot()['appearance'], self.defaults())

    def test_log_is_ready_before_an_invalid_startup_configuration_is_read(self):
        self.write('{"colors": INVALID}')
        self.start()
        self.assertIn('CONFIG parse failed', self.log())
        self.assertEqual(self.mod.snapshot()['appearance'], self.defaults())

    def test_ticks_publish_without_reading_configuration_files(self):
        original = appearance.load_config
        calls = []
        def counted(path):
            calls.append(path)
            return original(path)
        appearance.load_config = counted
        try:
            self.start()
            self.mod._tick()
            self.mod._tick()
            self.assertEqual(calls, [self.path])
            self.mod.open_window()
            self.refresh()
            self.assertEqual(calls, [self.path, self.path, self.path])
        finally:
            appearance.load_config = original

    def test_native_style_failure_does_not_block_activity_or_result_collection(self):
        self.start()
        self.footer.fail = True
        self.result()
        self.assertEqual(self.mod.active_service.snapshot()['scopes']['manual']['summary']['battles'], 1)
        self.assertEqual(self.footer.activity[-1], (0, False))
        self.footer.fail = False
        count = len(self.footer.styles)
        self.mod._tick()
        self.assertGreater(len(self.footer.styles), count)
        self.assertEqual(self.footer.styles[-1], self.defaults()['footer_css'])

    def test_unexpected_optional_loader_failure_keeps_static_ui_and_collector(self):
        self.start()
        original = appearance.load_config
        def broken(unused):
            raise RuntimeError('fixture optional loader failure')
        appearance.load_config = broken
        try:
            self.refresh()
        finally:
            appearance.load_config = original
        self.assertEqual(self.mod.snapshot()['appearance'],
                         {'panel_css': '', 'footer_css': '', 'scroll_speed': 1.0})
        self.result()
        self.assertEqual(self.mod.active_service.snapshot()['scopes']['manual']['summary']['battles'], 1)
        self.assertIn('CONFIG appearance unavailable', self.log())

    def test_runtime_uses_resolved_adjacent_path_when_no_test_override_is_given(self):
        self.write({'scroll': {'speed_multiplier': 1.5}})
        original = config_path.find_config_path
        config_path.find_config_path = lambda: self.path
        try:
            self.start(located=True)
        finally:
            config_path.find_config_path = original
        self.assertEqual(self.mod.appearance_path, self.path)
        self.assertEqual(self.mod.snapshot()['appearance']['scroll_speed'], 1.5)


if __name__ == '__main__':
    unittest.main()
