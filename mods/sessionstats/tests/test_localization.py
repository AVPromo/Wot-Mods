# -*- coding: utf-8 -*-
"""Catalog safety, durable-history compatibility and native language reloads."""
from __future__ import unicode_literals

import copy
import io
import json
import logging
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from grz_session_stats import localization as loc
from grz_session_stats.appearance import validate_config
from grz_session_stats.runtime import Runtime, GameAPI
from test_runtime import FakeAPI, FakeWindow, Clock, EXPECTED


class LocalizationTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.mkdtemp(prefix='grz-languages-')
        self.path = os.path.join(self.directory, loc.FILENAME)
        self.catalog = loc.bundled_catalog()
        self.disabled = logging.root.manager.disable
        logging.disable(logging.CRITICAL)

    def tearDown(self):
        logging.disable(self.disabled)
        shutil.rmtree(self.directory)

    def write(self, languages):
        value = json.dumps({'schema_version': 1, 'languages': languages}, ensure_ascii=False)
        if not isinstance(value, loc.text_type):
            value = value.decode('utf-8')
        with io.open(self.path, 'w', encoding='utf-8') as stream:
            stream.write(value)

    def test_all_seven_languages_have_every_key_and_exact_placeholder_contract(self):
        self.assertEqual(set(self.catalog), set(('en','pl','ru','fr','de','es','uk')))
        for code, entries in self.catalog.items():
            self.assertEqual(set(entries), set(loc.ENGLISH), code)
            for key, value in entries.items():
                self.assertTrue(loc.valid_text(key, value), code + ':' + key)
        self.assertEqual(self.catalog['en'], loc.ENGLISH)
        self.assertEqual(self.catalog['pl'], loc.LEGACY_POLISH)

    def test_default_and_unknown_language_use_english(self):
        self.assertEqual(loc.Localizer().text('title'), 'Session statistics')
        self.assertEqual(loc.Localizer('zz').language, 'en')
        self.assertEqual(validate_config({})['language'], 'en')
        for value in (True, 12, {}, None, 'EN', '../pl', 'pl\n'):
            self.assertEqual(validate_config({'language': value})['language'], 'en')
        self.assertEqual(validate_config({'language': 'uk'})['language'], 'uk')
        self.assertEqual(validate_config({'language': 'pt-BR'})['language'], 'pt-BR')

    def test_overrides_are_partial_and_new_languages_are_supported(self):
        self.write({'pl': {'title': 'Własny tytuł'}, 'pt-BR': {'title': 'Estatísticas'}})
        translator = loc.Localizer('pl', self.path)
        self.assertEqual(translator.text('title'), 'Własny tytuł')
        self.assertEqual(translator.text('refresh'), self.catalog['pl']['refresh'])
        added = loc.Localizer('pt-BR', self.path)
        self.assertEqual(added.language, 'pt-BR')
        self.assertEqual(added.text('refresh'), 'Refresh')

    def test_invalid_values_and_unsafe_placeholders_fall_back_per_message(self):
        for invalid in ('Missing count', '{1}', '{{0}}', '{0.__class__}', '{0[secret]}', '{0!r}', '{0:>10}', '{',
                        'control\x00{0}', 'x' * (loc.MAX_TEXT + 1), None, 42, []):
            self.write({'en': {'status.pending': invalid, 'refresh': 'Reload'}})
            translator = loc.Localizer('en', self.path)
            self.assertEqual(translator.text('status.pending', 3), 'Pending: 3')
            self.assertEqual(translator.text('refresh'), 'Reload')

    def test_malformed_duplicate_nonfinite_oversized_catalogs_restore_bundled_language(self):
        for raw in (b'{', b'[]', b'{"schema_version":true,"languages":{}}',
                    b'{"schema_version":1,"languages":{"en":{"title":"a","title":"b"}}}',
                    b'{"schema_version":1,"languages":{"en":{"title":NaN}}}',
                    b'\xff', b' ' * (loc.MAX_BYTES + 1)):
            with io.open(self.path, 'wb') as stream:
                stream.write(raw)
            translator = loc.Localizer('uk', self.path)
            self.assertEqual(translator.text('title'), self.catalog['uk']['title'])

    def test_bom_and_missing_file_are_safe(self):
        self.write({'fr': {'refresh': 'Recharger'}})
        with io.open(self.path, 'rb') as stream:
            raw = stream.read()
        with io.open(self.path, 'wb') as stream:
            stream.write(b'\xef\xbb\xbf' + raw)
        self.assertEqual(loc.Localizer('fr', self.path).text('refresh'), 'Recharger')
        os.unlink(self.path)
        self.assertEqual(loc.Localizer('fr', self.path).text('refresh'), 'Actualiser')

    def test_legacy_polish_and_canonical_warnings_translate_without_rewriting_history(self):
        old = loc.LEGACY_POLISH['runtime.backlog'].format(13)
        snapshot = {'warnings': [old, loc.ENGLISH['normalize.finance']], 'scopes': {
            'manual': {'label':'Od resetu', 'battles':[
                {'name':'Leopard 1', 'map':'Malinówka', 'id':'unchanged'},
                {'name':'Nieznany pojazd', 'map':'Mapa 42'}]}}}
        original = copy.deepcopy(snapshot)
        rendered = loc.Localizer('de').snapshot(copy.deepcopy(snapshot))
        self.assertEqual(snapshot, original)
        self.assertEqual(rendered['warnings'][0], self.catalog['de']['runtime.backlog'].format(13))
        rows = rendered['scopes']['manual']['battles']
        self.assertEqual(rows[0], original['scopes']['manual']['battles'][0])
        self.assertEqual(rows[1]['name'], self.catalog['de']['unknown.vehicle'])
        self.assertEqual(rows[1]['map'], 'Karte 42')

    def test_all_backend_warnings_round_trip_to_each_language(self):
        prefixes = ('storage.', 'core.', 'normalize.', 'health.', 'log.', 'runtime.', 'installation.')
        for code in self.catalog:
            translator = loc.Localizer(code)
            for key in loc.ENGLISH:
                if not key.startswith(prefixes):
                    continue
                english = loc.ENGLISH[key].format('1', 'game.log')
                polish = loc.LEGACY_POLISH[key].format('1', 'game.log')
                expected = self.catalog[code][key].format('1', 'game.log')
                self.assertEqual(translator.translate(english), expected, code + ':' + key)
                self.assertEqual(translator.translate(polish), expected, code + ':' + key)

    def test_native_notifications_escape_user_catalog_markup_at_final_boundary(self):
        import types
        pushed = []
        gui = types.ModuleType(str('gui'))
        gui.SystemMessages = type(str('Messages'), (), {
            'SM_TYPE': type(str('Types'), (), {'Warning': 1}),
            'pushMessage': staticmethod(lambda value, **unused: pushed.append(value))})
        previous = sys.modules.get('gui')
        sys.modules['gui'] = gui
        try:
            self.write({'en': {'runtime.garage': '<img src="private"> & test'}})
            message = loc.Localizer('en', self.path).text('runtime.garage')
            self.assertTrue(GameAPI.__new__(GameAPI).notify(message))
            self.assertEqual(pushed, ['&lt;img src="private"&gt; &amp; test'])
        finally:
            if previous is None:
                del sys.modules['gui']
            else:
                sys.modules['gui'] = previous

    def test_runtime_refresh_changes_language_without_resetting_any_statistics(self):
        config_path = os.path.join(self.directory, 'grz.sessionstats.json')
        def configure(code):
            with io.open(config_path, 'w', encoding='utf-8') as stream:
                stream.write(loc.text_type(json.dumps({'language': code})))
        configure('fr')
        api = FakeAPI()
        mod = Runtime(api=api, data_dir=self.directory, expected_table=EXPECTED,
                      now=Clock(), window=FakeWindow(), footer_installer=lambda unused: None,
                      appearance_path=config_path, installation_dir=self.directory)
        try:
            mod.start()
            service = mod.active_service
            service.begin_battle('fixture-pending', vehicle_name='Leopard 1', map_name='Malinówka')
            self.assertEqual(mod.snapshot()['localization']['language'], 'fr')
            saved = copy.deepcopy(service._state)
            self.write({'uk': {'refresh':'Оновити зараз'}})
            configure('uk')
            mod.on_action({'action':'refresh'})
            payload = mod.snapshot()
            self.assertEqual(payload['localization']['language'], 'uk')
            self.assertEqual(payload['localization']['messages']['refresh'], 'Оновити зараз')
            self.assertEqual(service._state, saved)
            self.assertEqual(payload['scopes']['launch']['summary']['observed_battles'], 1)
            mod._notify(loc.message('runtime.garage'))
            self.assertEqual(api.notices[-1], self.catalog['uk']['runtime.garage'])
        finally:
            mod.stop()

if __name__ == '__main__':
    unittest.main()
