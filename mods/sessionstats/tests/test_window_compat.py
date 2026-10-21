# -*- coding: utf-8 -*-
"""Update-boundary regressions with strict native doubles; no live-client claim."""
from __future__ import unicode_literals

import json
import sys
import unittest

import test_runtime as runtime_fixtures
import test_visuals as visual_fixtures
from grz_session_stats import footer, visuals


class RetainedEvent(runtime_fixtures.FakeEvent):
    def __isub__(self, callback):
        raise TypeError('changed unsubscribe contract')


class PartialSubscriptionEvent(RetainedEvent):
    def __iadd__(self, callback):
        self.handlers.append(callback)
        raise TypeError('changed subscribe contract after registration')


class WindowCompatibilityTests(unittest.TestCase):
    # Reuse the verified Wulf setup without inheriting and rerunning its tests.
    setUp = runtime_fixtures.NativeBindingTests.__dict__['setUp']
    tearDown = runtime_fixtures.NativeBindingTests.__dict__['tearDown']
    inject_module = runtime_fixtures.NativeBindingTests.__dict__['inject_module']

    def test_changed_notification_signature_cannot_interrupt_native_listeners(self):
        self.assertTrue(self.window.open())
        native = self.window._window
        later = []
        native.onSizeChanged += lambda *args: later.append(args)
        previous = self.window._native_size
        native.onSizeChanged(native.uniqueID, {'width': 700, 'height': 620})
        self.assertEqual(len(later), 1)
        self.assertEqual(self.window._native_size, previous)
        self.assertTrue(self.window.is_open())
        native.resize_surface(701, 621)
        self.assertEqual(self.window._native_size, (701, 621))
        self.assertEqual(len(later), 2)

    def test_changed_subscription_is_optional_and_partial_listener_is_inert(self):
        changed = PartialSubscriptionEvent()
        self.main.onSizeChanged = changed
        self.assertTrue(self.window.open())
        self.assertEqual(len(changed.handlers), 1)
        self.stats['probe'] = 'must not be published by failed listener'
        changed()
        payload = json.loads(self.window._model._payload)
        self.assertNotIn('probe', payload)
        self.window.refresh()
        self.assertIn('probe', json.loads(self.window._model._payload))

    def test_failed_unsubscribe_does_not_let_old_window_refresh_new_one(self):
        retained = RetainedEvent()
        self.main.onSizeChanged = retained
        self.assertTrue(self.window.open())
        stale = retained.handlers[0]
        self.window.close()
        self.assertTrue(self.window.open())
        self.stats['probe'] = 'belongs to next explicit refresh'
        stale()
        self.assertNotIn('probe', json.loads(self.window._model._payload))
        retained()
        self.assertIn('probe', json.loads(self.window._model._payload))

    def test_changed_timer_cancellation_cannot_prevent_native_destruction(self):
        self.assertTrue(self.window.open())
        native = self.window._window

        def changed_cancel(callback_id):
            raise TypeError('changed callback cancellation contract')

        sys.modules['BigWorld'].cancelCallback = changed_cancel
        self.window.close()
        self.assertIsNone(native.proxy)
        self.assertFalse(self.window.is_open())
        self.assertEqual(self.window._events, [])

    def test_footer_wrapper_preserves_original_arguments_and_return_value(self):
        marker = object()
        received = []

        class LobbyFooter(self.component):
            def _onLoading(self, *args, **kwargs):
                received.append((args, kwargs))
                return marker

        handle = footer.FooterInstallation(LobbyFooter, self.component, lambda: None)
        self.addCleanup(handle.uninstall)
        lobby = LobbyFooter()
        self.assertIs(lobby._onLoading('native', ready=True), marker)
        self.assertEqual(received, [(('native',), {'ready': True})])
        self.assertIsNotNone(lobby.getChildView(footer.POSITION_ID))

    def test_footer_does_not_mask_errors_in_original_game_callback(self):
        class LobbyFooter(self.component):
            def _onLoading(self, *args, **kwargs):
                raise ValueError('native callback error')

        handle = footer.FooterInstallation(LobbyFooter, self.component, lambda: None)
        self.addCleanup(handle.uninstall)
        lobby = LobbyFooter()
        with self.assertRaises(ValueError):
            lobby._onLoading()
        self.assertEqual(lobby.children, {})

    def test_missing_optional_footer_contract_leaves_native_class_untouched(self):
        class LobbyFooter(self.component):
            _registerChild = None

        original = LobbyFooter._onLoading
        with self.assertRaises(TypeError):
            footer.FooterInstallation(LobbyFooter, self.component, lambda: None)
        current = LobbyFooter._onLoading
        self.assertIs(getattr(current, '__func__', current), getattr(original, '__func__', original))
        self.assertNotIn('_onLoading', LobbyFooter.__dict__)

    def test_vehicle_helper_loss_preserves_maps_and_can_recover_later(self):
        fixture = visual_fixtures.ResolverFixture()
        vehicle_module = self.inject_module('items.vehicles')
        icon_module = self.inject_module('gui.shared.gui_items.Vehicle')
        resolver = visuals.NativeVisualResolver(
            resources=fixture.resources,
            image_getter=lambda identifier: fixture.paths[identifier],
            absolute_url_getter=lambda path: path.replace('../', 'img://gui/'),
            file_exists=fixture.exists)
        self.assertEqual(resolver.map_src('01_karelia'), 'img://' + visual_fixtures.MAP_PATH)
        self.assertIsNone(resolver.vehicle_src(visual_fixtures.VEHICLE_ID))
        vehicle_module.getVehicleType = fixture.vehicle_type
        self.assertIsNone(resolver.vehicle_src(visual_fixtures.VEHICLE_ID))
        self.assertEqual(resolver.map_src('01_karelia'), 'img://' + visual_fixtures.MAP_PATH)
        icon_module.getIconResourceName = lambda name: name.replace(':', '_').replace('-', '_')
        self.assertEqual(resolver.vehicle_src(visual_fixtures.VEHICLE_ID),
                         'img://' + visual_fixtures.VEHICLE_PATH)


if __name__ == '__main__':
    unittest.main()
