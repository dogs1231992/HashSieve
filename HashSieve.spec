# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

block_cipher = None
project_dir = Path.cwd()

added_datas = [
    (str(project_dir / 'locales'), 'locales'),
    (str(project_dir / 'assets'), 'assets'),
    (str(project_dir / 'VERSION.json'), '.'),
    (str(project_dir / 'LICENSE'), '.'),
]

icon_path = project_dir / 'assets' / 'hashsieve.ico'

a = Analysis(
    ['main.py'],
    pathex=[str(project_dir)],
    binaries=[],
    datas=added_datas,
    hiddenimports=['tkinterdnd2', 'send2trash'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
    name='HashSieve',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(icon_path) if icon_path.exists() else None,
    version=str(project_dir / 'version_info.txt') if (project_dir / 'version_info.txt').exists() else None,
)
