# Local validation — October 26, 2026

## Original baseline

Checked out the original application at commit 1c805fd on an Apple
Silicon Mac (Apple M1 Pro).

- The declared legacy dependencies did not install directly with Apple's Python
  3.9.6/Clang: lru-dict 1.1.8 failed a function-pointer type check. An isolated
  legacy environment was built with a compiler compatibility flag.
- urllib3 2.0.2 then rejected Apple's LibreSSL runtime. For the baseline probe
  only, urllib3 was changed to 1.26.20 in that environment.
- CPU prefix and suffix searches returned matching, independently derived addresses.
- The bundled OpenCL engine detected the Apple M1 Pro and returned a verified
  three-character vanity result.
- The original desktop window launched and closed successfully.
- A deterministic scalar wraparound test failed: the original implementation
  added private scalars modulo the field prime instead of the group order.

No generated private keys were forwarded in probe logs or retained as test files.
The legacy test environment is kept only in the original local development
checkout, separate from this standalone project.

## Sifter

Validated on October 26–27, 2026, with Python 3.13.18 and Tk 9.1.0:

- 19 automated regression tests pass; dependency consistency check passes.
- Live CPU prefix/suffix search returned a verified match.
- Live OpenCL GPU search returned a verified three-character match.
- Cancelling a live GPU search stopped and reaped its process within the probe's
  five-second bound.
- The desktop smoke test launched the app, entered a pattern, ran a CPU search,
  verified the result, toggled key reveal/hide, and closed without Tk errors.
- The Python wheel contains both inherited Mac engines and no generated caches.
- The built Mac app ran estimates, a CPU benchmark, and a verified GPU search
  from outside the repository; its desktop window launched without a startup
  error. It does not require an activated Python environment.
- GPU kernel work takes place in a temporary directory, which is removed after
  success, cancellation, and errors. Searches leave installed resources intact.

The local bundle uses an ad-hoc signature, not a Developer ID or notarization.
Only Apple Silicon was tested live. Intel, Linux, and Windows are not claimed
as runtime-verified. CI runs the portable native regression tests.
The original kernel/binary provenance is not independently verified. The tests
and runtime checks do not constitute a cryptographic audit or prove the absence
of all platform-specific issues.

## Pixel interface — October 27, 2026

- Previous app, wheel, and source archive saved under ignored `backups/` in
  the original local development checkout.
- The original checkout retains a Git rollback tag and branch for the pre-pixel
  source. This standalone history also preserves the earlier desktop interface.
- 19 regression tests and the desktop CPU search/reveal/hide smoke test pass.
- Silkscreen resolves as the actual Tk font family. All primary inputs and
  actions fit within the supported 720 × 620 minimum window size.
- The v0.2.0 wheel includes the font and its OFL license.
- The rebuilt standalone v0.2.0 Mac app passes version and GUI startup checks.
- macOS window image capture was unavailable; layout verification used actual
  widget geometry and runtime checks rather than a screenshot.
