import contextlib
import io
import math
import os
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
from eth_account import Account
from eth_keys.constants import SECPK1_N
from sifter.core import Pattern, Result, combine_keys, export_keystore
from sifter.miner import cpu_search


class PatternTests(unittest.TestCase):
    def test_normalization_and_both_ends(self):
        pattern = Pattern(" 0xAb ", "CD")
        self.assertEqual(pattern.mask, "ab" + "X" * 36 + "cd")
        self.assertTrue(pattern.matches("0x" + "ab" + "0" * 36 + "Cd"))
        self.assertFalse(pattern.matches("0x" + "ab" + "0" * 38))
        self.assertFalse(pattern.matches("0xabcd"))

    def test_invalid_patterns(self):
        for prefix, suffix in [("", ""), ("hello", ""), ("a" * 41, ""), ("a" * 22, "b" * 19)]:
            with self.subTest(prefix=prefix, suffix=suffix), self.assertRaises(ValueError):
                Pattern(prefix, suffix)

    def test_long_pattern_estimate(self):
        pattern = Pattern("a" * 40)
        self.assertTrue(math.isfinite(pattern.seconds_for(.95, 1e9)))
        self.assertEqual(Pattern("ab").expected_attempts, 256)
        self.assertGreater(pattern.seconds_for(.95, 1e9), pattern.seconds_for(.5, 1e9))


class KeyTests(unittest.TestCase):
    def test_curve_order_and_fixed_width(self):
        key = combine_keys((SECPK1_N - 1).to_bytes(32, "big"), "0x2")
        self.assertEqual(key, (1).to_bytes(32, "big"))
        self.assertEqual(len(key), 32)

    def test_zero_scalar_rejected(self):
        with self.assertRaises(ValueError):
            combine_keys((SECPK1_N - 1).to_bytes(32, "big"), "0x1")

    def test_secret_is_not_in_repr(self):
        result = Result.from_key((1).to_bytes(32, "big"))
        self.assertNotIn(result.private_key.hex(), repr(result))

    def test_encrypted_keystore_roundtrip(self):
        result = Result.from_key((1).to_bytes(32, "big"))
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "test.keystore.json"
            export_keystore(result, "test password", path)
            document = path.read_text()
            self.assertNotIn(result.private_key.hex(), document)
            self.assertEqual(bytes(Account.decrypt(document, "test password")), result.private_key)
            if os.name == "posix":
                self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            with patch("sifter.core.Account.encrypt", return_value={}):
                with self.assertRaises(FileExistsError):
                    export_keystore(result, "new password", path)
            self.assertEqual(path.read_text(), document)
            with self.assertRaises(ValueError):
                Account.decrypt(document, "wrong password")

    def test_bad_address_cannot_be_exported(self):
        result = Result("0x" + "0" * 40, (1).to_bytes(32, "big"))
        with self.assertRaises(ValueError):
            export_keystore(result, "password", "unused.json")


class CpuTests(unittest.TestCase):
    def test_verified_search_and_no_secret_output(self):
        result = Result.from_key((1).to_bytes(32, "big"))
        pattern = Pattern(result.address[2:5], result.address[-3:])
        log = io.StringIO()
        with patch("sifter.miner.new_key", return_value=result.private_key), contextlib.redirect_stdout(log):
            events = list(cpu_search(pattern, threading.Event()))
        self.assertEqual(events[-1].kind, "found")
        self.assertEqual(events[-1].result, result)
        self.assertEqual(events[-1].attempts, 1)
        self.assertEqual(log.getvalue(), "")

    def test_cancel_and_timeout(self):
        cancel = threading.Event()
        cancel.set()
        self.assertEqual(list(cpu_search(Pattern("a"), cancel))[-1].kind, "cancelled")
        with patch("sifter.miner.new_key", return_value=(1).to_bytes(32, "big")):
            self.assertEqual(list(cpu_search(Pattern("ffff"), threading.Event(), 1e-9))[-1].kind, "timeout")
