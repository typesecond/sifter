# Run from the repository root: pyinstaller packaging/sifter.spec
from pathlib import Path
import platform
from PyInstaller.utils.hooks import collect_data_files

root = Path(SPECPATH).parent
arch = platform.machine()
engine_dir = root / "src/sifter/engines" / f"macos-{arch}"
analysis = Analysis(
    [str(root / "src/main.py")],
    pathex=[str(root / "src")],
    datas=collect_data_files("customtkinter") + collect_data_files("sifter", excludes=["**/profanity2-*", "**/cache*"]) + [(str(root / "LICENSE"), "."), (str(root / "THIRD_PARTY.md"), ".")],
    hiddenimports=["sifter.gui", "eth_hash.backends.pycryptodome"],
)
# Preserve the inherited helper exactly. Its legacy Mach-O layout cannot be
# re-signed by modern codesign. This is a local, ad-hoc bundle; distribution
# with signing/notarization requires a reproducible rebuild of that helper.
analysis.datas.append((f"sifter/engines/macos-{arch}/profanity2-macos-{arch}", str(engine_dir / f"profanity2-macos-{arch}"), "DATA"))
archive = PYZ(analysis.pure)
exe = EXE(archive, analysis.scripts, [], exclude_binaries=True, name="Sifter", console=False)
collection = COLLECT(exe, analysis.binaries, analysis.datas, name="Sifter")
app = BUNDLE(collection, name="Sifter.app", bundle_identifier="local.sifter.vanity")
