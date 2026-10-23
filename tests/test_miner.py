import io
from pathlib import Path
import threading
import unittest
from unittest.mock import patch
from sifter.core import Pattern, Result
from sifter.miner import gpu_search, search


class Process:
    def __init__(self, output):
        self.stdout = io.BytesIO(output.encode())
        self.terminated = False

    def poll(self):
        return 0 if self.terminated else None

    def terminate(self):
        self.terminated = True

    def wait(self, timeout=None):
        return 0


class GpuTests(unittest.TestCase):
    def run_engine(self, output, pattern, cancel=None):
        process = Process(output)
        with patch("sifter.miner.engine_path", return_value=Path("/tmp/test-engine")), \
             patch("sifter.miner.new_key", return_value=(1).to_bytes(32, "big")), \
             patch("sifter.miner.shutil.copyfile"), \
             patch("sifter.miner.subprocess.Popen", return_value=process) as spawn:
            events = list(gpu_search(pattern, cancel or threading.Event()))
        self.assertFalse(Path(spawn.call_args.kwargs["cwd"]).exists())
        self.assertTrue(process.terminated)
        self.assertTrue(process.stdout.closed)
        return events

    def test_verified_result_and_cr_rate(self):
        result = Result.from_key((3).to_bytes(32, "big"))
        events = self.run_engine(f"Total: 2.5 MH/s\rPrivate: 0x2 Address: {result.address}\n", Pattern(result.address[2:5]))
        self.assertEqual(events[-1].kind, "found")
        self.assertEqual(events[-1].result, result)
        self.assertEqual(events[-1].rate, 2500000)

    def test_wrong_address_and_early_exit(self):
        events = self.run_engine("Private: 0x2 Address: 0x" + "0" * 40 + "\n", Pattern("000"))
        self.assertFalse(any(event.kind == "found" for event in events))
        self.assertEqual(events[-1].kind, "error")

    def test_cancel_terminates_native_process(self):
        cancel = threading.Event()
        cancel.set()
        self.assertEqual(self.run_engine("", Pattern("abc"), cancel)[-1].kind, "cancelled")

    def test_auto_uses_cpu_for_short_patterns(self):
        with patch("sifter.miner.cpu_search", return_value=iter([])) as cpu:
            list(search(Pattern("a"), threading.Event()))
        cpu.assert_called_once()

    def test_missing_gpu_reported(self):
        with patch("sifter.miner.engine_path", side_effect=RuntimeError("missing engine")):
            events = list(search(Pattern("abc"), threading.Event(), "gpu"))
        self.assertEqual(events[-1].kind, "error")

    def test_auto_falls_back_without_engine(self):
        with patch("sifter.miner.engine_path", side_effect=RuntimeError("missing engine")), \
             patch("sifter.miner.cpu_search", return_value=iter([])) as cpu:
            list(search(Pattern("abc"), threading.Event()))
        cpu.assert_called_once()
