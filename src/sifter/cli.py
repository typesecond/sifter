"""Sifter's terminal interface; secrets are shown only by explicit request."""
import argparse
import getpass
import json
import math
import sys
import threading
import time

from . import __version__
from .core import Pattern, Result, export_keystore, new_key
from .miner import search


def positive_seconds(value):
    number = float(value)
    if not math.isfinite(number) or number <= 0:
        raise argparse.ArgumentTypeError("Enter a positive, finite number of seconds.")
    return number


def parser():
    root = argparse.ArgumentParser(prog="sifter", description="Local Ethereum vanity address search")
    root.add_argument("--version", action="version", version=f"Sifter {__version__}")
    commands = root.add_subparsers(dest="command")
    commands.add_parser("gui", help="Open the Sifter desktop app")
    mine = commands.add_parser("mine", help="Search for a prefix, suffix, or both")
    mine.add_argument("--prefix", default="")
    mine.add_argument("--suffix", default="")
    mine.add_argument("--engine", choices=("auto", "cpu", "gpu"), default="auto")
    mine.add_argument("--timeout", type=positive_seconds)
    output = mine.add_mutually_exclusive_group(required=True)
    output.add_argument("--keystore", help="Save an encrypted Ethereum V3 keystore; prompts for a password")
    output.add_argument("--show-key", action="store_true", help="Explicitly print the private key to this terminal")
    estimate = commands.add_parser("estimate", help="Estimate search difficulty without mining")
    estimate.add_argument("--prefix", default="")
    estimate.add_argument("--suffix", default="")
    estimate.add_argument("--rate", type=positive_seconds, default=1000, help="Addresses per second")
    benchmark = commands.add_parser("benchmark", help="Measure this machine's CPU address generation rate")
    benchmark.add_argument("--seconds", type=positive_seconds, default=3)
    return root


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        if args.command in (None, "gui"):
            from .gui import run
            run()
            return 0
        if args.command == "benchmark":
            started = time.monotonic()
            attempts = 0
            while time.monotonic() - started < args.seconds:
                Result.from_key(new_key())
                attempts += 1
            elapsed = time.monotonic() - started
            print(json.dumps({"engine": "cpu", "attempts": attempts, "elapsed_seconds": elapsed, "addresses_per_second": attempts / elapsed}))
            return 0
        pattern = Pattern(args.prefix, args.suffix)
        if args.command == "estimate":
            print(json.dumps({"pattern": pattern.mask, "expected_attempts": pattern.expected_attempts,
                              "rate": args.rate, "seconds_50_percent": pattern.seconds_for(.5, args.rate),
                              "seconds_95_percent": pattern.seconds_for(.95, args.rate)}, indent=2))
            return 0
        password = None
        if args.keystore:
            password = getpass.getpass("Keystore password: ")
            if not password or password != getpass.getpass("Confirm password: "):
                raise ValueError("Passwords must be nonempty and match.")
        cancel = threading.Event()
        events = search(pattern, cancel, args.engine, args.timeout)
        try:
            for event in events:
                if event.kind == "found":
                    result = {"address": event.result.address, "elapsed_seconds": event.elapsed}
                    if args.keystore:
                        result["keystore"] = str(export_keystore(event.result, password, args.keystore))
                    if args.show_key:
                        result["private_key"] = "0x" + event.result.private_key.hex()
                    print(json.dumps(result, indent=2))
                    return 0
                if event.kind == "error":
                    raise RuntimeError(event.message)
                if event.kind in ("timeout", "cancelled"):
                    print(event.message, file=sys.stderr)
                    return 2
                if event.kind != "progress":
                    print(event.message, file=sys.stderr)
        finally:
            cancel.set()
            events.close()
    except KeyboardInterrupt:
        print("Search stopped.", file=sys.stderr)
        return 130
    except (ValueError, RuntimeError, OSError) as error:
        print(f"Sifter: {error}", file=sys.stderr)
        return 1
    return 0
