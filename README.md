# Sifter

Local Ethereum vanity address search with a pixel-art desktop UI and CLI.
Match a hexadecimal prefix, suffix, or both using Python CPU search or a native
OpenCL engine. Results are checked against their private keys before display
or export.

## Search

- Case-insensitive hexadecimal matching, with optional `0x` input.
- Live search rate, elapsed time, and probability estimates.
- Hidden private keys with explicit reveal and encrypted wallet export.
- Cancellation and time limits, including native process cleanup.

Each additional matching hex character multiplies expected search work by 16.
For `n` characters, the expected number of attempts is `16^n`.

Auto mode uses CPU for patterns shorter than three characters. Longer patterns
use a native engine when its executable is available; otherwise they use CPU.
Apple Silicon and Intel macOS engines are bundled. Other platforms can use CPU
or set `SIFTER_ENGINE` to a compatible executable with `profanity.cl` and
`keccak.cl` beside it.

## Install

Requires Python 3.10+. The desktop UI also requires Tk. On macOS:

```sh
brew install python-tk@3.13
python3.13 -m venv .venv-sifter
source .venv-sifter/bin/activate
python -m pip install -r requirements.txt
sifter
```

Enter a pattern and select **Find address**. Copy the address, reveal the
private key, or save an encrypted keystore. The interface uses CustomTkinter,
a code-drawn sieve, and the bundled Silkscreen font.

## CLI

```sh
sifter mine --prefix c0f --suffix ee --keystore wallet.keystore.json
sifter mine --suffix beef --engine cpu --timeout 30 --keystore wallet.keystore.json
sifter estimate --prefix c0ffee --rate 100000000
sifter benchmark --seconds 3
```

Keystore export prompts for a password and confirmation. `--show-key` prints
the private key instead of exporting a keystore. Ctrl+C stops the search.

## Implementation

CPU search generates private scalars with Python's `secrets` module. The GPU
engine receives a seed public key and returns an offset; Sifter combines it
with the private seed modulo the secp256k1 group order, then derives and checks
the final address. Searches use no RPC provider or remote service.

Exports use Ethereum V3 keystores with scrypt. Files are created exclusively,
with POSIX permissions `0600`; existing files are never overwritten. Native
engine caches are written to temporary directories outside the installed app.

`core.py` handles matching, scalar math, and export. `miner.py` runs the search
engines. `gui.py` and `cli.py` share that implementation under `src/sifter/`.

## Development

```sh
python -m unittest discover -s tests -v
python -m pip check
```

The 19 tests cover scalar boundaries, address verification, encrypted export,
input validation, cancellation, and native engine errors. CI runs on Python
3.11 and 3.13. See [BUILD.md](BUILD.md) for macOS app packaging.

The bundled GPU binaries have no documented source revision. See
[SECURITY.md](SECURITY.md) and [THIRD_PARTY.md](THIRD_PARTY.md) for details.
[Local checks](docs/VALIDATION.md) document the tested platforms and builds.

MIT. See [LICENSE](LICENSE) and [component notices](THIRD_PARTY.md).
