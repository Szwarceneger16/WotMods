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
from grz_session_stats import storage
RECURSION_ERRORS = [RuntimeError]
if sys.version_info[0] >= 3:
    RECURSION_ERRORS.append(RecursionError)
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

    def _recover_runtime_failure(self, boundary):
        for error_type in RECURSION_ERRORS:
            directory = os.path.join(self.directory, boundary + error_type.__name__)
            writer = GenerationStore(directory)
            writer.save(self.payload(1))
            writer.save(self.payload(2))
            with open(writer._files()[0][1], 'rb') as stream:
                newest = stream.read().decode('utf-8')
            calls = []
            original = getattr(storage.json, 'loads') if boundary == 'decode' else storage.canonical_bytes

            def fail_newest(value, *args, **kwargs):
                if ((boundary == 'decode' and value == newest) or
                        (boundary == 'checksum' and value == self.payload(2))):
                    calls.append(error_type)
                    raise error_type('simulated recursive generation')
                return original(value, *args, **kwargs)

            if boundary == 'decode':
                storage.json.loads = fail_newest
            else:
                storage.canonical_bytes = fail_newest
            recovered = GenerationStore(directory)
            try:
                self.assertEqual(recovered.load(), self.payload(1))
            finally:
                if boundary == 'decode':
                    storage.json.loads = original
                else:
                    storage.canonical_bytes = original
            self.assertEqual(calls, [error_type])
            self.assertIsNotNone(recovered.warning)
            self.assertFalse(recovered.read_only)
            self.assertEqual(recovered.sequence, 1)
            self.assertEqual(recovered.save(self.payload(3)), 3)
            self.assertEqual(GenerationStore(directory).load(), self.payload(3))

    def test_decoder_runtime_failure_recovers_an_older_generation_and_advances(self):
        self._recover_runtime_failure('decode')

    def test_checksum_runtime_failure_recovers_an_older_generation_and_advances(self):
        self._recover_runtime_failure('checksum')

    def test_real_deeply_nested_generation_recovers_without_assuming_a_decoder_depth_limit(self):
        self.store.save(self.payload(1))
        depth = 16384
        raw = (b'{"storage_version":1,"generation":2,"payload_checksum":"damaged",'
               b'"payload":{"schema_version":1,"value":' + b'[' * depth +
               b'0' + b']' * depth + b'}}')
        with open(os.path.join(self.directory, 'state-%020d.json' % 2), 'wb') as stream:
            stream.write(raw)
        recovered = GenerationStore(self.directory)
        self.assertEqual(recovered.load(), self.payload(1))
        self.assertIsNotNone(recovered.warning)
        self.assertEqual(recovered.save(self.payload(3)), 3)

    def test_only_recursive_generation_remains_read_only(self):
        self.store.save(self.payload(1))
        original = storage.json.loads

        def fail(*args, **kwargs):
            raise RuntimeError('simulated recursive generation')

        storage.json.loads = fail
        try:
            self.assertRaises(StorageError, self.store.load)
        finally:
            storage.json.loads = original
        self.assertTrue(self.store.read_only)
        self.assertRaises(StorageError, self.store.save, self.payload(2))

    def test_recursive_damage_does_not_bypass_an_older_unsupported_schema(self):
        self.store.save(self.payload(1))
        for generation, schema in ((2, 2), (3, 1)):
            payload = self.payload(generation)
            payload['schema_version'] = schema
            envelope = {'storage_version': 1, 'generation': generation, 'payload': payload,
                        'payload_checksum': hashlib.sha256(canonical_bytes(payload)).hexdigest()}
            with open(os.path.join(self.directory, 'state-%020d.json' % generation), 'wb') as stream:
                stream.write(canonical_bytes(envelope))
        original = storage.canonical_bytes

        def fail_newest(payload):
            if payload.get('value') == 3:
                raise RuntimeError('simulated recursive checksum')
            return original(payload)

        storage.canonical_bytes = fail_newest
        try:
            self.assertRaises(UnsupportedSchemaError, self.store.load)
        finally:
            storage.canonical_bytes = original
        self.assertTrue(self.store.read_only)
        self.assertRaises(StorageError, self.store.save, self.payload(4))

    def test_uncommitted_tempfile_is_ignored(self):
        self.store.save(self.payload(1))
        with open(os.path.join(self.directory, '.state-999.tmp'), 'wb') as handle:
            handle.write(b'partial uncommitted data')
        self.assertEqual(GenerationStore(self.directory).load(), self.payload(1))

    def _reject_second_payload(self, payload):
        if payload['value'] == 2:
            raise StorageError('invalid application ledger')

    def test_application_validation_selects_an_older_generation_and_advances_past_damage(self):
        self.store.save(self.payload(1))
        self.store.save(self.payload(2))
        damaged_path = self.store._files()[0][1]
        with open(damaged_path, 'rb') as stream:
            damaged_bytes = stream.read()
        recovered = GenerationStore(self.directory)
        self.assertEqual(recovered.load(validate=self._reject_second_payload), self.payload(1))
        self.assertEqual(recovered.sequence, 1)
        self.assertIsNotNone(recovered.warning)
        self.assertFalse(recovered.read_only)
        self.assertEqual(recovered.save(self.payload(3)), 3)
        with open(damaged_path, 'rb') as stream:
            self.assertEqual(stream.read(), damaged_bytes)
        self.assertEqual(GenerationStore(self.directory).load(), self.payload(3))

    def test_application_schema_rejection_stops_selection_before_older_payloads(self):
        self.store.save(self.payload(1))
        self.store.save(self.payload(2))
        calls = []

        def unsupported(payload):
            calls.append(payload['value'])
            raise UnsupportedSchemaError('application schema unavailable')

        recovered = GenerationStore(self.directory)
        self.assertRaises(UnsupportedSchemaError, recovered.load, validate=unsupported)
        self.assertEqual(calls, [2])
        self.assertTrue(recovered.read_only)
        self.assertRaises(StorageError, recovered.save, self.payload(3))

    def test_application_recovery_keeps_stale_writer_protection(self):
        self.store.save(self.payload(1))
        self.store.save(self.payload(2))
        first, second = GenerationStore(self.directory), GenerationStore(self.directory)
        self.assertEqual(first.load(validate=self._reject_second_payload), self.payload(1))
        self.assertEqual(second.load(validate=self._reject_second_payload), self.payload(1))
        self.assertEqual(second.save(self.payload(3)), 3)
        self.assertRaises(StorageError, first.save, self.payload(4))
        self.assertEqual(GenerationStore(self.directory).load(), self.payload(3))

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

    def _nested_payload(self, schema=1):
        value = []
        for unused in range(80):
            value = [value]
        return {'schema_version': schema, 'value': value}

    def _write_nested_generation(self, payload):
        envelope = {'storage_version': 1, 'generation': 2, 'payload': payload,
                    'payload_checksum': hashlib.sha256(canonical_bytes(payload)).hexdigest()}
        with open(os.path.join(self.directory, 'state-%020d.json' % 2), 'wb') as stream:
            stream.write(canonical_bytes(envelope))

    def test_checksum_valid_but_excessively_nested_generation_recovers_older_state(self):
        self.store.save(self.payload(1))
        self._write_nested_generation(self._nested_payload())
        recovered = GenerationStore(self.directory)
        self.assertEqual(recovered.load(), self.payload(1))
        self.assertIsNotNone(recovered.warning)
        self.assertEqual(recovered.save(self.payload(3)), 3)

    def test_nested_newer_schema_still_refuses_fallback_and_mutations(self):
        self.store.save(self.payload(1))
        self._write_nested_generation(self._nested_payload(schema=2))
        recovered = GenerationStore(self.directory)
        self.assertRaises(UnsupportedSchemaError, recovered.load)
        self.assertTrue(recovered.read_only)
        self.assertRaises(StorageError, recovered.save, self.payload(3))

    def test_nested_write_is_rejected_without_replacing_a_committed_generation(self):
        self.store.save(self.payload(1))
        self.assertRaises(StorageError, self.store.save, self._nested_payload())
        self.assertEqual(self.store.sequence, 1)
        self.assertEqual(GenerationStore(self.directory).load(), self.payload(1))

    def test_encoder_runtime_failure_keeps_previous_committed_state(self):
        self.store.save(self.payload(1))
        original = storage.canonical_bytes

        def fail(*args):
            raise RuntimeError('simulated encoder failure')

        storage.canonical_bytes = fail
        try:
            self.assertRaises(StorageError, self.store.save, self.payload(2))
        finally:
            storage.canonical_bytes = original
        self.assertEqual(self.store.sequence, 1)
        self.assertEqual(GenerationStore(self.directory).load(), self.payload(1))

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
