# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller 构建配置。"""

a = Analysis(
    ['src/main.py'],
    pathex=['src'],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    runtime_hooks=[],
    excludes=[
        'tkinter', 'unittest', 'email', 'html', 'http', 'xmlrpc',
        'pydoc', 'doctest', 'difflib', 'asyncio',
        'multiprocessing', 'concurrent', 'xml.etree', 'xml.dom.minidom',
        'xml.sax', 'csv', 'sqlite3', 'logging', 'pdb',
        'lib2to3', 'distutils', 'setuptools', 'pip',
        'encodings.mac_roman', 'encodings.cp437',
    ],
    noarchive=True,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='CopyTree',
    debug=False,
    bootloader_ignore_signals=True,
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
    icon='src/copytree/icon.ico',
)
