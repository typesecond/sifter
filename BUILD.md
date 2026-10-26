# Building Sifter

The desktop app is developed and tested on macOS Apple Silicon with Python
3.13 and Tk. Install the project as described in README.md, then:

```sh
python -m pip install pyinstaller
pyinstaller --noconfirm packaging/sifter.spec
```

The output is `dist/Sifter.app`. The spec bundles the current Mac architecture's
native engine, OpenCL kernels, CustomTkinter assets, and the Python runtime.
Build separately on Intel macOS for Intel distribution. The app is ad-hoc signed and
not notarized; this build recipe is for local use, not an App Store release.
The inherited native helper is preserved without modification. A distribution
build with a Developer ID requires rebuilding that helper from known source.

To build a Python wheel (including both inherited macOS engines):

```sh
python -m pip wheel --no-deps --no-build-isolation . -w dist
```

Windows/Linux CPU operation uses the Python package. GPU operation there needs
an external compatible engine; native desktop bundles for those platforms are
not provided by this project yet.
