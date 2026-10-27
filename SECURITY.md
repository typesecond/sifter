# Security status

Sifter is an experimental vanity address generator, not an independently audited
wallet product. Publishing its source does not publish freshly generated keys:
those come from the operating system's cryptographic random generator at runtime.

## Implemented protections

- Fresh private scalars sampled with Python secrets within the secp256k1 group.
- The GPU receives the seed public key, not the private seed.
- Every accepted result is checked by independently deriving its address.
- Keys are omitted from object representations and normal diagnostic output.
- Explicit reveal or --show-key is required for plaintext key display.
- Keystore exports use scrypt, exclusive file creation, and POSIX mode 0600.
- Virtual environments, local app/source backups, builds, and common wallet
  exports are ignored by Git. Arbitrary export filenames still require care.

## Known release limitations

- This standalone repository starts with clean Sifter history. Historical
  placeholder key material from the original application is not included. The
  original local development checkout and its rollback backups remain separate.
- The bundled GPU executables were inherited as binaries. Their exact source
  revision and reproducible build provenance have not been established. Rebuild
  the engine from a reviewed, pinned source revision before making production
  security claims or recommending it for valuable wallets.
- Python does not guarantee erasure of secret values from process memory.
- The app bundle is a local ad-hoc build, not a notarized distribution.
- Only Apple Silicon was tested live. CI covers the native Python regression
  tests; it does not validate GPU operation on other platforms.

## Checks performed

19 regression tests, live CPU/GPU result verification, native cancellation,
encrypted keystore round-trip, desktop smoke tests, and package checks passed.
A pattern-based scan found no GitHub tokens, AWS access keys, or PEM private keys
in the current candidate text files. No generated wallet exports or environments
are tracked. This scan is not an exhaustive secret detector or security audit.

See docs/VALIDATION.md and THIRD_PARTY.md for scope and engine provenance.
