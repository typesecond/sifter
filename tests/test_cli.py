import contextlib
import io
import json
import unittest
from unittest.mock import patch
from sifter.cli import main
from sifter.core import Event, Result


def iter_events(result):
    yield Event("found", result=result)


class CliTests(unittest.TestCase):
    def test_estimate_and_invalid_input(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(main(["estimate", "--prefix", "ab", "--suffix", "cd"]), 0)
        self.assertEqual(json.loads(output.getvalue())["expected_attempts"], 65536)
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(main(["estimate", "--prefix", "hello"]), 1)

    def test_explicit_key_output(self):
        result = Result.from_key((1).to_bytes(32, "big"))
        output = io.StringIO()
        with patch("sifter.cli.search", return_value=iter_events(result)), contextlib.redirect_stdout(output):
            self.assertEqual(main(["mine", "--prefix", "a", "--show-key"]), 0)
        self.assertEqual(json.loads(output.getvalue())["private_key"], "0x" + result.private_key.hex())

    def test_keystore_does_not_print_key(self):
        result = Result.from_key((1).to_bytes(32, "big"))
        output = io.StringIO()
        with patch("sifter.cli.search", return_value=iter_events(result)), \
             patch("sifter.cli.getpass.getpass", return_value="test password"), \
             patch("sifter.cli.export_keystore", return_value="test.keystore.json"), \
             contextlib.redirect_stdout(output):
            self.assertEqual(main(["mine", "--prefix", "a", "--keystore", "test.keystore.json"]), 0)
        self.assertNotIn(result.private_key.hex(), output.getvalue())
        self.assertNotIn("private_key", json.loads(output.getvalue()))
