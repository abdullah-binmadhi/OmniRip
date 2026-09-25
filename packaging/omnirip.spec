# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller specification for building standalone OmniRip binaries.
Build with:
    pyinstaller packaging/omnirip.spec
"""

import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None
project_root = Path.cwd()

datas = [
    (str(project_root / "src" / "harvester" / "ui" / "app.tcss"), "harvester/ui"),
]
datas += collect_data_files("harvester", include_py_files=False)

hiddenimports = [
    "harvester",
    "harvester.ui",
    "harvester.ui.app",
    "harvester.ui.help_modal",
    "harvester.ui.setup_modal",
    "harvester.ui.settings_modal",
    "harvester.ui.player",
    "harvester.ui.workbench",
    "harvester.ui.visualizer",
    "harvester.ui.repair",
    "harvester.ui.deck",
    "harvester.ui.eq",
    "harvester.ui.themes",
    "harvester.services",
    "harvester.services.model_manager",
    "harvester.services.slskd",
    "harvester.pipeline",
    "textual",
    "rich",
    "platformdirs",
]
hiddenimports += collect_submodules("harvester")

a = Analysis(
    [str(project_root / "src" / "harvester" / "__main__.py")],
    pathex=[str(project_root / "src")],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="omnirip",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
