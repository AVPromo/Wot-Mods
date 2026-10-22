# -*- coding: utf-8 -*-
"""Optional process-wide view; account ledgers and their resets stay independent."""
from __future__ import unicode_literals


class InstanceSession(object):
    def __init__(self, started_at):
        self.started_at = started_at
        self.reset_at = None
        self.excluded = set()
        self.aliases = {}

    def records(self, services):
        records = {}
        for account_key, service in sorted(services.items()):
            for record in service.launch_records():
                key = (account_key, record['arena_id'])
                started_at = record.get('started_at')
                if key in self.excluded or (self.reset_at is not None and
                        (started_at is None or started_at < self.reset_at)):
                    continue
                if key not in self.aliases:
                    self.aliases[key] = 'instance-{0}'.format(len(self.aliases) + 1)
                record['arena_id'] = self.aliases[key]
                records[record['arena_id']] = record
        return records

    def reset(self, services, timestamp):
        # Include unresolved beginnings and equal-second records in the old
        # epoch. Late results cannot reintroduce these after a separate reset.
        for account_key, service in services.items():
            self.excluded.update((account_key, record['arena_id']) for record in service.launch_records())
        self.started_at = self.reset_at = timestamp
