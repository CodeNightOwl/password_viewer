# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['password_viewer.py'],
    pathex=[],
    binaries=[],
    datas=[('hook_reader.dll', '.'), ('hook_reader32.dll', '.'), ('load_hook32.exe', '.'), ('load_hook64.exe', '.'), ('星号.png', '.')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='星号探测器-Owl',
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
    icon=['icon.ico'],
)
