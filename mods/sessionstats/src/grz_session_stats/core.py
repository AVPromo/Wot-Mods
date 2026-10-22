# -*- coding: utf-8 -*-
"""Statistics and sessions; no dependency on the World of Tanks runtime."""
from __future__ import unicode_literals

from .localization import message

import copy
import hashlib
import math
import os
import time
import uuid

from . import VERSION
from .storage import GenerationStore, SCHEMA_VERSION, StorageError

try:
    text_type = unicode
    number_types = (int, long, float)
except NameError:
    text_type = str
    number_types = (int, float)

_OUTCOMES = ('win', 'loss', 'draw')
_CURRENCIES = ('credits', 'bonds', 'gold')
_BREAKDOWN = ('repair', 'ammo', 'consumables', 'directives')
_NUMBERS = ('damage', 'frags', 'spots', 'defense', 'xp_base', 'xp_received', 'free_xp')
_UNKNOWN_MEMBERSHIP = message('core.membership')


def _text(value):
    if isinstance(value, bytes) and not isinstance(value, text_type):
        return value.decode('utf-8', 'replace')
    return text_type(value)


def _number(value, nonnegative=False):
    if isinstance(value, bool) or not isinstance(value, number_types):
        return None
    try:
        if math.isnan(value) or math.isinf(value):
            return None
    except (ValueError, OverflowError):
        return None
    if nonnegative and value < 0:
        return None
    return value


def _series(values):
    known = [value for value in values if value is not None]
    if not known:
        return {'min': None, 'avg': None, 'max': None, 'sum': None, 'count': 0}
    total = sum(known)
    return {'min': min(known), 'avg': total / float(len(known)),
            'max': max(known), 'sum': total, 'count': len(known)}


def wn8_from_totals(actual, expected):
    """Exact aggregate formula. Wins and expected wins are counts, not percents."""
    ratios = {}
    for key in ('damage', 'frags', 'spots', 'defense', 'wins'):
        got = _number(actual.get(key), True)
        reference = _number(expected.get(key), True)
        if got is None or reference is None or reference <= 0:
            return None
        ratios[key] = got / float(reference)
    damage = max(0.0, (ratios['damage'] - 0.22) / 0.78)
    wins = max(0.0, (ratios['wins'] - 0.71) / 0.29)
    frags = max(0.0, min(damage + 0.2, (ratios['frags'] - 0.12) / 0.88))
    spots = max(0.0, min(damage + 0.1, (ratios['spots'] - 0.38) / 0.62))
    defense = max(0.0, min(damage + 0.1, (ratios['defense'] - 0.10) / 0.90))
    return (980.0 * damage + 210.0 * damage * frags + 155.0 * frags * spots +
            75.0 * defense * frags + 145.0 * min(1.8, wins))


class ExpectedTable(object):
    def __init__(self, document):
        document = document if isinstance(document, dict) else {}
        header = document.get('header', {})
        header = header if isinstance(header, dict) else {}
        self.metadata = {'version': _text(header.get('version', document.get('version', message('unknown')))),
                         'source': 'XVM Wargaming', 'count': 0}
        raw = document.get('data', document)
        if isinstance(raw, list):
            entries = [(item.get('IDNum', item.get('id', item.get('vehicle_id'))), item)
                       for item in raw if isinstance(item, dict)]
        elif isinstance(raw, dict):
            entries = list(raw.items())
        else:
            entries = []
        self.values = {}
        for identifier, item in entries:
            if identifier is None or not isinstance(item, dict):
                continue
            fields = {}
            for key, official in (('damage', 'expDamage'), ('frags', 'expFrag'),
                                  ('spots', 'expSpot'), ('defense', 'expDef'), ('wins', 'expWinRate')):
                value = _number(item.get(official, item.get(key)), True)
                if value is None or value <= 0:
                    fields = None
                    break
                fields[key] = value / 100.0 if key == 'wins' and official in item else value
            # Expected values are rating coefficients. The WG table can contain
            # an extrapolated expWinRate above 100; preserve it, do not clamp it.
            if fields is not None:
                self.values[_text(identifier)] = fields
        self.metadata['count'] = len(self.values)

    def for_record(self, record):
        if record.get('vehicle_id') is None or record.get('outcome') not in _OUTCOMES:
            return None
        expected = self.values.get(_text(record['vehicle_id']))
        if expected is None or any(record.get(key) is None for key in ('damage', 'frags', 'spots', 'defense')):
            return None
        return expected


def _money(records, currency):
    money = {}
    for key in ('income', 'costs', 'net'):
        values = [record.get('currencies', {}).get(currency, {}).get(key) for record in records]
        known = [value for value in values if value is not None]
        money[key] = sum(known) if known else None
        money[key + '_count'] = len(known)
    money['breakdown'] = {}
    money['breakdown_counts'] = {}
    for key in _BREAKDOWN:
        values = [record.get('currencies', {}).get(currency, {}).get('breakdown', {}).get(key)
                  for record in records]
        known = [value for value in values if value is not None]
        money['breakdown'][key] = sum(known) if known else None
        money['breakdown_counts'][key] = len(known)
    return money


def aggregate_stats(records, expected_table):
    observed = [record for record in records if record.get('mode') in (None, 'random')]
    records = [record for record in observed if record.get('mode') == 'random' and record.get('outcome') in _OUTCOMES]
    table = expected_table if isinstance(expected_table, ExpectedTable) else ExpectedTable(expected_table)
    count = len(records)
    stats = {'battles': count, 'observed_battles': len(observed),
             'missing_results': len(observed) - count,
             'partial_results': sum(1 for record in records if not record.get('complete')),
             'wins': sum(1 for record in records if record['outcome'] == 'win'),
             'losses': sum(1 for record in records if record['outcome'] == 'loss'),
             'draws': sum(1 for record in records if record['outcome'] == 'draw')}
    stats['win_rate'] = stats['wins'] * 100.0 / count if count else None
    for key in ('xp_base', 'xp_received', 'free_xp'):
        stats[key] = _series([record.get(key) for record in records])
    actual = dict((key, 0.0) for key in ('damage', 'frags', 'spots', 'defense', 'wins'))
    reference = dict((key, 0.0) for key in actual)
    per_battle = []
    for record in records:
        expected = table.for_record(record)
        if expected is None:
            continue
        values = dict((key, record.get(key)) for key in ('damage', 'frags', 'spots', 'defense'))
        values['wins'] = 1 if record['outcome'] == 'win' else 0
        for key in actual:
            actual[key] += values[key]
            reference[key] += expected[key]
        per_battle.append(wn8_from_totals(values, expected))
    stats['wn8_count'] = len(per_battle)
    stats['wn8'] = wn8_from_totals(actual, reference) if per_battle else None
    stats['battle_wn8'] = _series(per_battle)
    stats['currencies'] = dict((currency, _money(records, currency)) for currency in _CURRENCIES)
    return stats


def _clean_record(record):
    if not isinstance(record, dict) or record.get('arena_id') is None:
        raise ValueError(message('core.missing_id'))
    clean = {'arena_id': _text(record['arena_id'])}
    if not clean['arena_id'] or len(clean['arena_id']) > 128:
        raise ValueError(message('core.invalid_id'))
    for key in ('started_at', 'ended_at') + _NUMBERS:
        if key in record:
            clean[key] = _number(record[key], True)
    for key in ('vehicle_id', 'vehicle_tier'):
        if key in record:
            value = _number(record[key], True)
            clean[key] = int(value) if value is not None and int(value) == value else None
    for key in ('vehicle_name', 'vehicle_type', 'map_id', 'map_name', 'mode'):
        if key in record:
            clean[key] = _text(record[key]) if record[key] is not None else None
    if 'outcome' in record:
        clean['outcome'] = record['outcome'] if record['outcome'] in _OUTCOMES else None
    if 'complete' in record:
        clean['complete'] = record['complete'] is True
    if 'reconcile' in record:
        clean['reconcile'] = record['reconcile'] is True
    if 'xp_bonus_applied' in record:
        clean['xp_bonus_applied'] = record['xp_bonus_applied'] is True
    if 'warnings' in record:
        warnings = record['warnings'] if isinstance(record['warnings'], (list, tuple)) else []
        clean['warnings'] = [_text(warning)[:240] for warning in warnings[:40]]
    if isinstance(record.get('currencies'), dict):
        clean['currencies'] = {}
        for currency in _CURRENCIES:
            incoming = record['currencies'].get(currency)
            if not isinstance(incoming, dict):
                continue
            values = {}
            for key in ('income', 'costs', 'net'):
                if key in incoming:
                    # The client's after-penalty income can be negative.
                    # Costs alone must be nonnegative; do not erase a fine.
                    values[key] = _number(incoming[key], key == 'costs')
            if isinstance(incoming.get('breakdown'), dict):
                values['breakdown'] = dict((key, _number(incoming['breakdown'][key], True))
                                           for key in _BREAKDOWN if key in incoming['breakdown'])
            clean['currencies'][currency] = values
    return clean


def _merge_known(existing, incoming, revise=False):
    """Unknown updates never erase facts; authoritative readings may revise."""
    merged = copy.deepcopy(existing)
    for key, value in incoming.items():
        if key in ('complete', 'xp_bonus_applied'):
            merged[key] = bool(merged.get(key)) or bool(value)
        elif key == 'warnings':
            merged[key] = list(value) if revise else sorted(set(merged.get(key, []) + value))
        elif isinstance(value, dict):
            merged[key] = _merge_known(merged.get(key, {}) or {}, value, revise)
        elif value is not None and (revise or merged.get(key) is None):
            merged[key] = value
        elif key not in merged:
            merged[key] = value
    return merged


class StatsService(object):
    def __init__(self, data_dir, account_key, launch_id, expected_table, now=None):
        self.account_key = _text(account_key)
        self.launch_id = _text(launch_id)
        self._now = now or time.time
        self.expected_table = ExpectedTable(expected_table)
        account_dir = hashlib.sha256(self.account_key.encode('utf-8')).hexdigest()
        self.store = GenerationStore(os.path.join(data_dir, account_dir))
        self.last_error = None
        self._warnings = []
        current_time = self._time()
        self._state = self._empty_state(current_time)
        try:
            existing = self.store.load(validate=self._validate_state)
            if existing is not None:
                self._state = existing
            if self.store.warning:
                self._warnings.append(self.store.warning)
            candidate = copy.deepcopy(self._state)
            found = self._launch(candidate, self.launch_id)
            if found is None:
                for previous in candidate['launch_sessions']:
                    if previous.get('ended_at') is None:
                        # A crash has no known exit timestamp. Do not invent activity
                        # during the unobserved gap up to this process's start.
                        previous['ended_at'] = previous.get('last_seen_at', previous['started_at'])
                candidate['launch_sessions'].append({'id': self.launch_id, 'started_at': current_time,
                                                     'last_seen_at': current_time, 'ended_at': None})
            elif found.get('ended_at') is not None:
                raise StorageError(message('core.closed'))
            if existing is None or candidate != self._state:
                if not self._commit(candidate):
                    raise StorageError(self.last_error or message('core.create'))
        except (StorageError, IOError, OSError, ValueError, TypeError, KeyError) as error:
            self.store.read_only = True
            self.last_error = message('core.load')
            if isinstance(error, StorageError):
                self.last_error = _text(error)

    def _time(self):
        value = _number(self._now(), True)
        if value is None:
            raise ValueError(message('core.time'))
        return value

    def _empty_state(self, timestamp):
        manual_id = uuid.uuid4().hex
        return {'schema_version': SCHEMA_VERSION, 'account_key': self.account_key,
                'launch_sessions': [],
                'manual_sessions': [{'id': manual_id, 'started_at': timestamp, 'ended_at': None}],
                'current_manual_id': manual_id, 'battles': {}}

    def _validate_state(self, state):
        if state.get('account_key') != self.account_key:
            raise StorageError(message('core.account'))
        if not isinstance(state.get('battles'), dict) or not isinstance(state.get('launch_sessions'), list):
            raise StorageError(message('core.ledger'))
        if not isinstance(state.get('manual_sessions'), list) or not state['manual_sessions']:
            raise StorageError(message('core.periods'))
        for epoch in state['launch_sessions'] + state['manual_sessions']:
            if not isinstance(epoch, dict) or not epoch.get('id') or _number(epoch.get('started_at'), True) is None:
                raise StorageError(message('core.boundaries'))
        manual_ids = [epoch.get('id') for epoch in state['manual_sessions']]
        if state.get('current_manual_id') not in manual_ids:
            raise StorageError(message('core.current'))
        for arena_id, battle in state['battles'].items():
            if not isinstance(battle, dict) or battle.get('arena_id') != arena_id:
                raise StorageError(message('core.battle'))

    @staticmethod
    def _launch(state, identifier):
        for epoch in state['launch_sessions']:
            if epoch['id'] == identifier:
                return epoch
        return None

    def _commit(self, candidate):
        try:
            self.store.save(candidate)
        except StorageError as error:
            self.last_error = _text(error)
            return False
        self._state = candidate
        self.last_error = None
        return True

    def _touch(self, candidate, timestamp):
        epoch = self._launch(candidate, self.launch_id)
        if epoch is not None:
            epoch['last_seen_at'] = max(epoch.get('last_seen_at', epoch['started_at']), timestamp)

    def _memberships(self, timestamp, current_time):
        if timestamp is None or timestamp > current_time:
            return None, None
        manual_id = None
        launch_id = None
        for epoch in reversed(self._state['manual_sessions']):
            if timestamp >= epoch['started_at'] and (epoch.get('ended_at') is None or timestamp < epoch['ended_at']):
                manual_id = epoch['id']
                break
        for epoch in reversed(self._state['launch_sessions']):
            if timestamp < epoch['started_at']:
                continue
            if epoch['id'] == self.launch_id and epoch.get('ended_at') is None:
                launch_id = epoch['id']
                break
            if timestamp <= epoch.get('last_seen_at', epoch['started_at']):
                launch_id = epoch['id']
                break
        return launch_id, manual_id

    def begin_battle(self, arena_id, started_at=None, vehicle_id=None, map_id=None, mode=None,
                     vehicle_name=None, vehicle_tier=None, vehicle_type=None, map_name=None):
        if mode not in (None, 'random'):
            return False
        timestamp = self._time()
        record = {'arena_id': arena_id, 'started_at': timestamp if started_at is None else started_at,
                  'vehicle_id': vehicle_id, 'map_id': map_id, 'mode': mode, 'complete': False,
                  'vehicle_name': vehicle_name, 'vehicle_tier': vehicle_tier,
                  'vehicle_type': vehicle_type, 'map_name': map_name}
        return self._apply(record, timestamp, is_result=False)

    def record_result(self, record):
        if not isinstance(record, dict):
            self.last_error = message('core.result')
            return False
        if record.get('mode') not in (None, 'random') or record.get('is_replay') or record.get('isReplay'):
            return False
        return self._apply(record, self._time(), is_result=True)

    def result_context(self, arena_id):
        """Known metadata for one result, including after a client restart.

        Presentation fallbacks must not replace previously resolved names or
        map identities when a later client no longer supplies that metadata.
        Return only contextual fields, never a mutable reference to the ledger.
        """
        record = self._state['battles'].get(_text(arena_id), {})
        fields = ('started_at', 'vehicle_id', 'vehicle_name', 'vehicle_tier',
                  'vehicle_type', 'map_id', 'map_name')
        return dict((key, record[key]) for key in fields if record.get(key) is not None)

    def _apply(self, record, timestamp, is_result):
        try:
            incoming = _clean_record(record)
        except (ValueError, TypeError, OverflowError) as error:
            self.last_error = _text(error)
            return False
        arena_id = incoming['arena_id']
        old = self._state['battles'].get(arena_id, {})
        # Authority and completeness are separate: a new XP bonus can arrive
        # while a currency is unavailable. This control flag is not ledger data.
        revise = incoming.pop('reconcile', False)
        # The raw server-result cache may predate an already applied premium XP
        # bonus even after restart. Only another bonus-aware reading can revise it.
        if old.get('xp_bonus_applied') and not incoming.get('xp_bonus_applied'):
            incoming.pop('xp_received', None)
        merged = _merge_known(old, incoming, revise)
        if merged.get('mode') not in (None, 'random'):
            return False
        if old:
            # A known beginning is authoritative even if a result arrives later.
            if old.get('_launch_id') is not None:
                merged['_launch_id'] = old['_launch_id']
            if old.get('_manual_id') is not None:
                merged['_manual_id'] = old['_manual_id']
        launch_id, manual_id = self._memberships(merged.get('started_at'), timestamp)
        if merged.get('_launch_id') is None:
            merged['_launch_id'] = launch_id
        if merged.get('_manual_id') is None:
            merged['_manual_id'] = manual_id
        merged['_result_seen'] = bool(old.get('_result_seen')) or is_result
        merged.setdefault('complete', False)
        merged.setdefault('warnings', [])
        # Infer a net value only when both components are confirmed. Reconcile it
        # when an authoritative update revises a component but does not supply net.
        for currency, values in merged.get('currencies', {}).items():
            update = incoming.get('currencies', {}).get(currency, {})
            has_components = values.get('income') is not None and values.get('costs') is not None
            if has_components and (values.get('net') is None or
                                   (revise and update.get('net') is None and
                                    (update.get('income') is not None or update.get('costs') is not None))):
                values['net'] = values['income'] - values['costs']
        if merged == old:
            return False
        merged['revision'] = old.get('revision', 0) + 1
        merged['_updated_at'] = timestamp
        candidate = copy.deepcopy(self._state)
        candidate['battles'][arena_id] = merged
        self._touch(candidate, timestamp)
        return self._commit(candidate)

    def reset_manual(self, now=None):
        timestamp = self._time() if now is None else _number(now, True)
        active = self._state['manual_sessions'][-1]
        if timestamp is None or timestamp < active['started_at']:
            self.last_error = message('core.reset_time')
            return None
        new_id = uuid.uuid4().hex
        candidate = copy.deepcopy(self._state)
        candidate['manual_sessions'][-1]['ended_at'] = timestamp
        candidate['manual_sessions'].append({'id': new_id, 'started_at': timestamp, 'ended_at': None})
        candidate['current_manual_id'] = new_id
        self._touch(candidate, timestamp)
        return new_id if self._commit(candidate) else None

    def pending_arena_ids(self):
        return sorted(arena_id for arena_id, record in self._state['battles'].items()
                      if record.get('mode') in (None, 'random') and self._pending(record))

    @staticmethod
    def _pending(record):
        return not record.get('complete') or record.get('outcome') not in _OUTCOMES

    def _scope(self, key, identifier, label, started_at):
        records = [record for record in self._state['battles'].values()
                   if record.get(key) == identifier and record.get('mode') in (None, 'random')]
        return self.project_scope(records, label, started_at)

    def launch_records(self):
        """Independent records from this account and game process only."""
        return [copy.deepcopy(record) for record in self._state['battles'].values()
                if record.get('_launch_id') == self.launch_id and record.get('mode') in (None, 'random')]

    def project_scope(self, records, label, started_at):
        """Project known records without changing their account/session ledger."""
        scope = {'label': label, 'started_at': started_at,
                 'pending': sum(1 for record in records if self._pending(record)),
                 'summary': aggregate_stats(records, self.expected_table), 'vehicles': [], 'maps': [], 'battles': []}
        for group_type, field, name_field in (('vehicles', 'vehicle_id', 'vehicle_name'), ('maps', 'map_id', 'map_name')):
            groups = {}
            for record in records:
                identifier = _text(record[field]) if record.get(field) is not None else '__unknown__'
                groups.setdefault(identifier, []).append(record)
            for identifier, group_records in groups.items():
                named = [row for row in group_records if row.get(name_field)]
                latest = max(named or group_records, key=lambda row: row.get('_updated_at', 0))
                fallback = message('unknown.vehicle') if group_type == 'vehicles' else message('unknown.map')
                group = {'id': identifier, 'name': latest.get(name_field) or fallback,
                         'tier': latest.get('vehicle_tier') if group_type == 'vehicles' else None,
                         'type': latest.get('vehicle_type') if group_type == 'vehicles' else None,
                         'stats': aggregate_stats(group_records, self.expected_table)}
                scope[group_type].append(group)
            scope[group_type].sort(key=lambda group: (-group['stats']['battles'], group['name'].lower(), group['id']))
        for record in sorted(records, key=lambda row: (row.get('started_at') or 0, row['arena_id']), reverse=True):
            scope['battles'].append({'id': record['arena_id'], 'name': record.get('vehicle_name') or message('unknown.vehicle'),
                                     'map': record.get('map_name') or message('unknown.map'), 'started_at': record.get('started_at'),
                                     'outcome': record.get('outcome'), 'tier': record.get('vehicle_tier'),
                                     'stats': aggregate_stats([record], self.expected_table)})
        return scope

    def snapshot(self):
        timestamp = self._time()
        launch = self._launch(self._state, self.launch_id)
        manual = next(epoch for epoch in self._state['manual_sessions']
                      if epoch['id'] == self._state['current_manual_id'])
        warnings = list(self._warnings)
        if self.store.warning:
            warnings.append(self.store.warning)
        if self.last_error:
            warnings.append(self.last_error)
        if not self.expected_table.values:
            warnings.append(message('core.wn8'))
        if any(record.get('_manual_id') is None or record.get('_launch_id') is None
               for record in self._state['battles'].values()):
            warnings.append(_UNKNOWN_MEMBERSHIP)
        for record in self._state['battles'].values():
            if record.get('_manual_id') == manual['id'] or record.get('_launch_id') == self.launch_id:
                warnings.extend(record.get('warnings', []))
        return {'version': VERSION, 'account_key': self.account_key, 'generated_at': timestamp,
                'expected': copy.deepcopy(self.expected_table.metadata), 'warnings': sorted(set(warnings)),
                'scopes': {'launch': self._scope('_launch_id', self.launch_id, message('scope.launch'),
                                                 launch['started_at'] if launch else timestamp),
                           'manual': self._scope('_manual_id', manual['id'], message('scope.manual'), manual['started_at'])}}
