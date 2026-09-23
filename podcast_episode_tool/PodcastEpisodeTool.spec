import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_submodules, copy_metadata


datas = [("app.py", "."), ("pipeline", "pipeline")]
binaries = []
hiddenimports = collect_submodules("streamlit")

conda_bin = Path(sys.base_prefix) / "Library" / "bin"
for dll_name in ("ffi.dll", "libbz2.dll", "libexpat.dll", "liblzma.dll", "sqlite3.dll"):
    dll_path = conda_bin / dll_name
    if dll_path.exists():
        binaries.append((str(dll_path), "."))

for package in ("streamlit", "openai", "pydantic", "dotenv"):
    package_datas, package_binaries, package_hiddenimports = collect_all(package)
    datas += package_datas
    binaries += package_binaries
    hiddenimports += package_hiddenimports

for distribution in ("streamlit", "openai", "pydantic", "python-dotenv"):
    datas += copy_metadata(distribution)

a = Analysis(
    ["launcher.py"],
    pathex=["."],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="PodcastEpisodeTool",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="PodcastEpisodeTool",
)
