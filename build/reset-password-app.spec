# -*- mode: python ; coding: utf-8 -*-
import platform
from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules

project_root = Path(SPECPATH).resolve().parent
frontend_dist = project_root / 'frontend' / 'dist'
backend_dir = project_root / 'backend'
is_macos = platform.system() == 'Darwin'

hiddenimports = collect_submodules('ldap3')

app = Analysis(
    [str(project_root / 'run.py')],
    pathex=[str(project_root), str(backend_dir)],
    binaries=[],
    datas=[
        (str(frontend_dist), 'frontend/dist'),
        (str(project_root / 'backend'), 'backend'),
    ],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(app.pure)

exe = EXE(
    pyz,
    app.scripts,
    [],
    exclude_binaries=True,
    name='AD_Password_Reset',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=not is_macos,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    app.binaries,
    app.datas,
    strip=False,
    upx=not is_macos,
    upx_exclude=[],
    name='AD_Password_Reset',
)

if is_macos:
    app_bundle = BUNDLE(
        coll,
        name='AD_Password_Reset.app',
        icon=None,
        bundle_identifier='com.local.ad-password-reset',
    )
