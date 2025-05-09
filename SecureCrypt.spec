# -*- mode: python ; coding: utf-8 -*-

import sys
from PyInstaller.utils.hooks import collect_all

# collect everything PyQt6 needs
datas, binaries, hiddenimports = collect_all('PyQt6')

# also bundle your assets folder
datas += [
    ('assets/logo.png', 'assets'),
]

block_cipher = None

a = Analysis(
    ['main-v4.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    exclude_binaries=True,
    name='VideoPlayer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,                # GUI app: no console window
    icon='assets/icon.ico',             # your multi‑res icon file
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    name='VideoPlayer'
)
