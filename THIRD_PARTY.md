# Attribution and bundled engines

## Application source

The application's inherited MIT notice is retained in the root `LICENSE`.
Required notices are kept in license files, separate from the product interface.

## profanity2 and OpenCL kernels

Project: https://github.com/1inch/profanity2

profanity2 is the 1inch Network fork of profanity by Johan Gustafsson.
The macOS executables and kernel files in `src/sifter/engines/` are inherited
unchanged from the original source distribution, apart from generated caches (which are ignored).
Their precise build revision and independent reproducibility are not established.
The current upstream source is a reference, not a claim that these binaries
were reproduced from its latest commit.

The upstream MIT notice is included at `docs/profanity2-LICENSE` and
`src/sifter/engines/LICENSE`. The kernel files retain their own attribution comments. The Keccak kernel
credits Markku-Juhani O. Saarinen's tiny_sha3 and the xptMiner-gpu implementation.
The native executable's original name and help attribution are preserved.

## Python dependencies

Account creation, derivation, and encrypted V3 keystores use eth-account:
https://eth-account.readthedocs.io/en/stable/eth_account.html

The interface uses CustomTkinter. Their packages include their respective
license notices. Dependencies are listed in pyproject.toml and requirements.lock.

## Silkscreen

The interface bundles the unmodified Silkscreen Regular typeface under the SIL
Open Font License 1.1. Its copyright and complete license are included at
`src/sifter/assets/Silkscreen-OFL.txt`.
