# Sifter

**An address with your signature.** A local Ethereum vanity address studio
with a compact pixel-art desktop interface, terminal commands, and CPU/OpenCL search engines.

**Status:** experimental. See [SECURITY.md](SECURITY.md) for the publication review,
key handling, and known release limitations.

## What it does

- Find a hexadecimal prefix, suffix, or both at once; accept mixed case and `0x`.
- Run CPU searches everywhere supported by Python; use bundled GPU engines on
  Apple Silicon and Intel macOS. Auto uses CPU for fewer than three characters.
- Show live throughput, elapsed time, and a probability-based search estimate.
- Verify each result by deriving its address from the final private key.
- Keep keys hidden until explicitly revealed; export password-encrypted
  Ethereum V3 keystores with scrypt. Never overwrite an existing export.
- Cancel native GPU work when a search stops, completes, or the window closes.
- Keep GPU caches in disposable work directories, outside the installed app.
- Use a CLI for mining, difficulty estimates, and CPU benchmarks.

Vanity matching is case-insensitive, before the address checksum's capitalization.
Every additional matching hex character multiplies the expected work by 16.
Estimates describe probability, not a completion deadline.

## Desktop

Enter a prefix, a suffix, or both, then click **Find address**. **Auto** selects
an engine. When a verified match appears, use **Copy address**, **Show key**, or
**Save wallet** (a password-encrypted keystore). Enter starts or stops a search.

The UI uses a code-drawn 8-bit sieve, a pixel wordmark, and the bundled Silkscreen
font. The previous studio interface is preserved; see [docs/ROLLBACK.md](docs/ROLLBACK.md).

## Install

Python 3.10+ is required. Python 3.13 is the locally verified runtime.
For the desktop interface, the Python installation also needs Tk:

```sh
# macOS, if Python with Tk is not already installed
brew install python-tk@3.13
python3.13 -m venv .venv-sifter
source .venv-sifter/bin/activate
python -m pip install -r requirements.txt
sifter
```

On this checkout, double-click **Start Sifter.command** after installation.
`python src/main.py` is retained as a compatibility launcher.

## Terminal

```sh
sifter estimate --prefix c0ffee --suffix 00 --rate 100000000
sifter benchmark --seconds 3
sifter mine --prefix abc --engine auto --keystore ./my-wallet.keystore.json
sifter mine --suffix beef --engine cpu --timeout 30 --keystore ./my-wallet.keystore.json
```

Keystore passwords are entered through a hidden prompt and confirmed. Normal
terminal results contain the address and export path. `--show-key` explicitly
prints the secret instead of exporting; use it only when terminal output is an
appropriate destination. The GUI provides an explicit reveal/hide action.

`--timeout` includes GPU initialization. Ctrl+C stops the native process.
Exit codes: 0 success, 1 error, 2 time limit/cancellation, 130 keyboard interrupt.

CPU search has no engine binary dependency. On other platforms, an externally
built profanity2 engine can be selected with `SIFTER_ENGINE=/absolute/path/to/profanity2`.
Put its `profanity.cl` and `keccak.cl` files beside that executable.
The bundled macOS binaries are inherited native engines; their exact source
build revision is not documented upstream. See [THIRD_PARTY.md](THIRD_PARTY.md).

## Development

```sh
python -m unittest discover -s tests -v
python -m pip check
python -m pip wheel --no-deps --no-build-isolation . -w dist
```

`src/sifter/core.py` contains patterns, scalar math, and keystore export.
`miner.py` owns CPU/GPU execution and process cleanup. `gui.py` consumes events
on Tk's main thread. `cli.py` uses the same search and export functions.

The regression suite covers scalar wraparound, result verification, prefix and
suffix validation, estimates for long patterns, cancellation, engine failures,
CR-delimited progress, secret redaction, and encrypted export/decryption.
See [docs/VALIDATION.md](docs/VALIDATION.md) for actual local checks and limits.
[BUILD.md](BUILD.md) describes desktop packaging.

## Key handling

Searches do not connect to an RPC provider or send keys to a remote service.
The GPU engine receives only a fresh seed public key; Sifter combines its
returned offset with the secret scalar locally modulo the secp256k1 group order.
A result is accepted only if its derived address matches both the engine output
and the requested pattern. This is a software implementation with tests, not
an independent cryptographic audit.

Secrets remain in process memory until exit and may be copied by the Python
runtime; Sifter does not promise secure memory erasure. Keystore files are
created exclusively with owner-only permissions on POSIX systems. Keep the
password: Sifter has no recovery service.

## License

MIT. See [LICENSE](LICENSE) and [THIRD_PARTY.md](THIRD_PARTY.md) for the retained
software and bundled-component notices.
