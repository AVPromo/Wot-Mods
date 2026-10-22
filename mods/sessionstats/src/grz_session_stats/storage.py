# -*- coding: utf-8 -*-
"""Crash-safe, game-independent JSON generations (Python 2.7 and Python 3).

The final filename is a commit marker.  It is never overwritten: a flushed,
validated temporary file is renamed to a fresh name on the same filesystem.
Readers validate checksums and can recover a previous complete generation.
"""
from __future__ import unicode_literals

from .localization import message

import errno
import hashlib
import json
import os
import re
import threading
import uuid


SCHEMA_VERSION = 1
STORAGE_VERSION = 1
MAX_JSON_DEPTH = 64
_GENERATION_RE = re.compile(r'^state-([0-9]{20})\.json$')
_PROCESS_LOCK = threading.RLock()


class StorageError(Exception):
    pass


class UnsupportedSchemaError(StorageError):
    pass


def canonical_bytes(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False).encode('utf-8')


def check_json_depth(value):
    """Bound external nesting before later encoders, copies or text conversion.

    Ledger/config structures are shallow; history length is not limited here.
    An iterative check also works when a newer decoder accepts deeper JSON.
    """
    pending = [(value, 0)]
    while pending:
        current, depth = pending.pop()
        if not isinstance(current, (dict, list)):
            continue
        if depth > MAX_JSON_DEPTH:
            raise ValueError('JSON nesting exceeds the supported data shape')
        children = current.values() if isinstance(current, dict) else current
        pending.extend((item, depth + 1) for item in children if isinstance(item, (dict, list)))


def _ensure_directory(directory):
    if not os.path.isdir(directory):
        try:
            os.makedirs(directory, 0o700)
        except OSError as error:
            if error.errno != errno.EEXIST or not os.path.isdir(directory):
                raise


class _WriteLock(object):
    """An OS-released lock: process crashes never leave a permanent lock."""

    def __init__(self, directory):
        self.path = os.path.join(directory, '.write.lock')
        self.handle = None
        self.platform = None
        self.fallback = False

    def __enter__(self):
        _PROCESS_LOCK.acquire()
        try:
            self.handle = open(self.path, 'a+b')
            if os.name == 'nt':
                try:
                    import msvcrt
                except ImportError:
                    # Some embedded runtimes omit the stdlib extension. Windows
                    # rename refuses to replace the fresh final filename, so a
                    # concurrent commit still fails instead of overwriting data.
                    self.fallback = True
                    return self
                self.platform = msvcrt
                self.handle.seek(0, os.SEEK_END)
                if self.handle.tell() == 0:
                    self.handle.write(b'0')
                    self.handle.flush()
                self.handle.seek(0)
                msvcrt.locking(self.handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                self.platform = fcntl
                fcntl.flock(self.handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except (IOError, OSError, ImportError):
            if self.handle is not None:
                self.handle.close()
            self.handle = None
            _PROCESS_LOCK.release()
            raise StorageError(message('storage.busy'))
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        try:
            if self.handle is not None:
                if os.name == 'nt' and self.platform is not None:
                    self.handle.seek(0)
                    self.platform.locking(self.handle.fileno(), self.platform.LK_UNLCK, 1)
                elif self.platform is not None:
                    self.platform.flock(self.handle.fileno(), self.platform.LOCK_UN)
        finally:
            if self.handle is not None:
                self.handle.close()
            _PROCESS_LOCK.release()


class GenerationStore(object):
    def __init__(self, directory, schema_version=SCHEMA_VERSION, keep_generations=3):
        self.directory = directory
        self.schema_version = schema_version
        self.keep_generations = max(2, int(keep_generations))
        self.sequence = 0
        self._observed_generation = 0
        self.read_only = False
        self.warning = None

    def _files(self):
        if not os.path.isdir(self.directory):
            return []
        found = []
        for name in os.listdir(self.directory):
            match = _GENERATION_RE.match(name)
            if match:
                found.append((int(match.group(1)), os.path.join(self.directory, name)))
        return sorted(found, reverse=True)

    def _decode(self, path, generation):
        with open(path, 'rb') as handle:
            envelope = json.loads(handle.read().decode('utf-8'))
        if not isinstance(envelope, dict):
            raise ValueError('invalid envelope')
        if envelope.get('storage_version') != STORAGE_VERSION:
            raise UnsupportedSchemaError(message('storage.format'))
        if envelope.get('generation') != generation:
            raise ValueError('generation mismatch')
        payload = envelope.get('payload')
        if not isinstance(payload, dict):
            raise ValueError('invalid payload')
        if payload.get('schema_version') != self.schema_version:
            raise UnsupportedSchemaError(message('storage.schema'))
        check_json_depth(payload)
        actual = hashlib.sha256(canonical_bytes(payload)).hexdigest()
        if actual != envelope.get('payload_checksum'):
            raise ValueError('checksum mismatch')
        return payload

    def load(self, validate=None):
        """Select the newest generation accepted by storage and the caller.

        An optional application validator raises StorageError/ValueError for
        invalid known-schema payloads. UnsupportedSchemaError always stops
        selection, including when raised by the validator.
        """
        self.warning = None
        files = self._files()
        self._observed_generation = files[0][0] if files else 0
        damaged = 0
        for generation, path in files:
            try:
                payload = self._decode(path, generation)
                if validate is not None:
                    validate(payload)
            except UnsupportedSchemaError:
                self.read_only = True
                raise
            except (StorageError, ValueError, TypeError, UnicodeError, IOError, OSError, RuntimeError):
                # Python 2.7 reports decoder/encoder recursion as RuntimeError;
                # Python 3 RecursionError is its subclass. Try an older backup.
                damaged += 1
                continue
            self.sequence = generation
            if damaged:
                self.warning = (message('storage.recovered'))
            return payload
        if files:
            self.read_only = True
            raise StorageError(message('storage.corrupt'))
        self.sequence = 0
        return None

    def save(self, payload):
        if self.read_only:
            raise StorageError(message('storage.readonly'))
        if payload.get('schema_version') != self.schema_version:
            raise UnsupportedSchemaError(message('storage.unsupported_write'))
        try:
            check_json_depth(payload)
            _ensure_directory(self.directory)
            with _WriteLock(self.directory) as lock:
                if lock.fallback:
                    self.warning = (message('storage.no_lock'))
                files = self._files()
                on_disk = files[0][0] if files else 0
                if on_disk != self._observed_generation:
                    raise StorageError(message('storage.changed'))
                generation = on_disk + 1
                final_name = 'state-%020d.json' % generation
                final_path = os.path.join(self.directory, final_name)
                temporary = os.path.join(self.directory, '.%s-%s.tmp' % (final_name, uuid.uuid4().hex))
                envelope = {'storage_version': STORAGE_VERSION,
                            'generation': generation,
                            'payload_checksum': hashlib.sha256(canonical_bytes(payload)).hexdigest(),
                            'payload': payload}
                encoded = canonical_bytes(envelope)
                try:
                    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                    with os.fdopen(descriptor, 'wb') as handle:
                        handle.write(encoded)
                        handle.flush()
                        os.fsync(handle.fileno())
                    self._decode(temporary, generation)
                    if os.path.exists(final_path):
                        raise StorageError(message('storage.collision'))
                    os.rename(temporary, final_path)
                    self._sync_directory()
                finally:
                    if os.path.exists(temporary):
                        try:
                            os.unlink(temporary)
                        except OSError:
                            pass
                self.sequence = generation
                self._observed_generation = generation
                for unused_generation, path in self._files()[self.keep_generations:]:
                    try:
                        os.unlink(path)
                    except OSError:
                        # A failed old-backup cleanup does not undo a committed save.
                        pass
                return generation
        except StorageError:
            raise
        except (IOError, OSError, ValueError, TypeError, UnicodeError, RuntimeError):
            raise StorageError(message('storage.failed'))

    def _sync_directory(self):
        if os.name == 'nt' or not hasattr(os, 'O_DIRECTORY'):
            return
        directory_fd = None
        try:
            directory_fd = os.open(self.directory, os.O_RDONLY | os.O_DIRECTORY)
            os.fsync(directory_fd)
        except OSError:
            # Some filesystems do not support directory fsync. File fsync is required above.
            pass
        finally:
            if directory_fd is not None:
                os.close(directory_fd)
