# -*- coding: utf-8 -*-
"""Delayed bonus work belongs to its scheduling account, not the next login."""
from __future__ import unicode_literals

import copy
import unittest

import test_runtime as fixtures
from test_normalize import ARENA_ID, raw_result


class BonusAccountOwnershipTests(unittest.TestCase):
    setUp = fixtures.RuntimeTests.__dict__['setUp']
    tearDown = fixtures.RuntimeTests.__dict__['tearDown']
    no_footer = fixtures.RuntimeTests.__dict__['no_footer']
    begin = fixtures.RuntimeTests.__dict__['begin']
    garage = fixtures.RuntimeTests.__dict__['garage']
    summary = fixtures.RuntimeTests.__dict__['summary']

    def schedule_then_switch(self):
        self.begin()
        self.garage()
        self.api.events.onBattleResultsReceived(True, raw_result())
        original = self.mod.active_service
        self.api.event_bus.emit()
        timer = self.mod._bonus_callback_id
        self.api.dbid = 8
        self.api.events.onAccountBecomePlayer()
        current = self.mod.active_service
        self.api.events.onBattleResultsReceived(True, raw_result(dbid=8))
        reusable = fixtures.Obj(personal=fixtures.Obj(xpProgress={1: {'xp': 4550}},
                                                      isAddXPBonusApplied=True))
        self.api.posts[ARENA_ID] = fixtures.Obj(results=raw_result(dbid=8), reusable=reusable)
        return timer, original, current

    def test_previous_account_timer_cannot_read_or_revise_new_account(self):
        timer, original, current = self.schedule_then_switch()
        before = [copy.deepcopy(service._state) for service in (original, current)]
        reads, processing = [], []
        posted_bundle = self.api.posted_bundle
        process = self.mod._process

        def observe_read(arena_id):
            reads.append(arena_id)
            return posted_bundle(arena_id)

        def observe_process(*args, **kwargs):
            processing.append(args[1])
            return process(*args, **kwargs)

        self.api.posted_bundle = observe_read
        self.mod._process = observe_process
        self.api.fire(timer)
        self.assertEqual(reads, [])
        self.assertEqual(processing, [])
        self.assertEqual([original._state, current._state], before)
        self.assertIsNone(self.mod._bonus_callback_id)
        self.assertIsNone(self.mod._bonus_account_key)
        # The new account can still schedule and reconcile its own bonus.
        self.api.event_bus.emit()
        self.api.fire(self.mod._bonus_callback_id)
        self.assertEqual(processing, ['EU:8'])
        self.assertEqual(self.summary()['xp_received']['sum'], 4550)

    def test_manual_refresh_on_new_account_does_not_consume_previous_timer(self):
        timer, original, current = self.schedule_then_switch()
        self.mod._refresh_posted()
        self.assertEqual(self.summary()['xp_received']['sum'], 4550)
        self.assertEqual(self.mod._bonus_callback_id, timer)
        self.assertEqual(self.mod._bonus_account_key, 'EU:7')
        after_manual = [copy.deepcopy(service._state) for service in (original, current)]
        self.api.fire(timer)
        self.assertEqual([original._state, current._state], after_manual)
        self.assertIsNone(self.mod._bonus_callback_id)
        self.assertIsNone(self.mod._bonus_account_key)


if __name__ == '__main__':
    unittest.main()
