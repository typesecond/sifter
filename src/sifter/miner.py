"""CPU search and a cancellable adapter for the bundled profanity2 engine.

MIT licensed. See the retained notices in LICENSE.
"""
import os
from pathlib import Path
import platform
import queue
import re
import subprocess
import shutil
import tempfile
import threading
import time

from eth_keys import keys

from .core import Event, Result, combine_keys, new_key


def engine_path():
    override = os.environ.get("SIFTER_ENGINE")
    if override:
        path = Path(override).expanduser().resolve()
    else:
        arch = platform.machine()
        if platform.system() != "Darwin" or arch not in ("arm64", "x86_64"):
            raise RuntimeError("No bundled GPU engine for this platform. Select CPU or set SIFTER_ENGINE.")
        path = Path(__file__).parent / "engines" / f"macos-{arch}" / f"profanity2-macos-{arch}"
    if not path.is_file():
        raise RuntimeError("GPU engine was not found. Select CPU or set SIFTER_ENGINE.")
    if not os.access(path, os.X_OK):
        raise RuntimeError(f"GPU engine is not executable: {path}")
    return path


def cpu_search(pattern, cancel, limit=None):
    started = last_update = time.monotonic()
    attempts = 0
    yield Event("status", "CPU search running")
    while not cancel.is_set():
        account = Result.from_key(new_key())
        attempts += 1
        elapsed = time.monotonic() - started
        if pattern.matches(account.address):
            yield Event("found", "Match verified", attempts / max(elapsed, 1e-9), attempts, elapsed, account)
            return
        if limit is not None and elapsed >= limit:
            yield Event("timeout", "Search time limit reached", attempts / max(elapsed, 1e-9), attempts, elapsed)
            return
        if time.monotonic() - last_update >= .25:
            yield Event("progress", rate=attempts / max(elapsed, 1e-9), attempts=attempts, elapsed=elapsed)
            last_update = time.monotonic()
    yield Event("cancelled", "Search stopped", attempts=attempts, elapsed=time.monotonic() - started)


def read_output(stream, messages):
    """The native engine uses both CR and LF for progress updates."""
    pending = bytearray()
    try:
        while chunk := stream.read(1):
            if chunk in (b"\r", b"\n"):
                if pending:
                    messages.put(pending.decode(errors="replace"))
                    pending.clear()
            elif len(pending) < 16384:
                pending.extend(chunk)
        if pending:
            messages.put(pending.decode(errors="replace"))
    finally:
        messages.put(None)


def gpu_search(pattern, cancel, limit=None):
    binary = engine_path()
    # profanity2's short matching behavior is unreliable; the auto mode uses CPU.
    if pattern.digits < 3:
        raise ValueError("GPU search requires at least 3 matching characters. Select Auto or CPU.")
    seed = new_key()
    public = keys.PrivateKey(seed).public_key.to_bytes().hex()
    # The native engine writes kernel caches in its working directory. Keep
    # those outside installed packages and sealed app resources, and discard
    # them when the search ends.
    with tempfile.TemporaryDirectory(prefix="sifter-opencl-") as working_dir:
        for name in ("profanity.cl", "keccak.cl"):
            shutil.copyfile(binary.parent / name, Path(working_dir) / name)
        messages = queue.Queue()
        started = time.monotonic()
        process = subprocess.Popen(
            [str(binary), "--matching", pattern.mask, "-z", public],
            cwd=working_dir, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            bufsize=0,
        )
        reader = threading.Thread(target=read_output, args=(process.stdout, messages), daemon=True)
        reader.start()
        rate = 0
        try:
            yield Event("status", "Initializing OpenCL GPU engine")
            while True:
                elapsed = time.monotonic() - started
                if cancel.is_set():
                    yield Event("cancelled", "Search stopped", elapsed=elapsed)
                    return
                if limit is not None and elapsed >= limit:
                    yield Event("timeout", "Search time limit reached", elapsed=elapsed)
                    return
                try:
                    line = messages.get(timeout=.1)
                except queue.Empty:
                    continue
                if line is None:
                    code = process.wait(timeout=2)
                    yield Event("error", f"GPU engine exited before finding a verified match (exit {code}). Try CPU mode.")
                    return
                if "GPU" in line and "Private:" not in line:
                    yield Event("device", line[:240])
                match = re.search(r"Private:\s*(0x[0-9a-fA-F]+)\s+Address:\s*(0x[0-9a-fA-F]{40})", line)
                if match:
                    # Native output contains intermediate scores, not just full matches.
                    try:
                        result = Result.from_key(combine_keys(seed, match[1]))
                    except ValueError:
                        continue
                    if result.address.lower() == match[2].lower() and pattern.matches(result.address):
                        yield Event("found", "Match verified", rate=rate, elapsed=elapsed, result=result)
                        return
                speed = re.search(r"Total:\s*([\d.]+)\s*([kKmMgGtT]?)H", line)
                if speed:
                    rate = float(speed[1]) * 1000 ** ("kmgt".find(speed[2].lower()) + 1 if speed[2] else 0)
                    yield Event("progress", rate=rate, elapsed=elapsed)
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=2)
            reader.join(timeout=2)
            process.stdout.close()


def search(pattern, cancel, engine="auto", limit=None):
    if engine not in ("auto", "cpu", "gpu"):
        raise ValueError("Unknown engine.")
    if limit is not None and limit <= 0:
        raise ValueError("Time limit must be positive.")
    selected = engine
    if selected == "auto":
        selected = "cpu"
        if pattern.digits >= 3:
            try:
                engine_path()
                selected = "gpu"
            except RuntimeError:
                pass
    try:
        yield from (gpu_search if selected == "gpu" else cpu_search)(pattern, cancel, limit)
    except (OSError, RuntimeError, ValueError) as error:
        yield Event("error", str(error))
