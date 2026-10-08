# -*- mode: python ; coding: utf-8 -*-
import os

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

PROJECT_ROOT = os.path.abspath(os.path.join(SPECPATH, ".."))

datas = []
datas += collect_data_files("rapidocr_onnxruntime")

hiddenimports = []
hiddenimports += collect_submodules("rapidocr_onnxruntime")
hiddenimports += [
    "pymupdf",
    "pdf2docx",
    "pdfplumber",
    "docx",
    "openpyxl",
    "onnxruntime",
]

a = Analysis(
    [os.path.join(PROJECT_ROOT, "app", "main.py")],
    pathex=[PROJECT_ROOT],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter",
        "matplotlib",
        "PySide6.QtWebEngineCore",
        "PySide6.QtWebEngineWidgets",
        "PySide6.QtQml",
        "PySide6.Qt3DCore",
        "PySide6.QtCharts",
        "PySide6.QtMultimedia",
        "PySide6.QtNetworkAuth",
        "PySide6.QtPdf",
        "PySide6.QtQuick",
        "PySide6.QtSensors",
        "PySide6.QtSql",
        "PySide6.QtTest",
        "PySide6.QtWebChannel",
        "PySide6.QtWebSockets",
        "PySide6.QtDesigner",
        "PySide6.QtHelp",
        "PySide6.QtOpenGL",
        "PySide6.QtSvg",
        "PySide6.QtUiTools",
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Pdf2",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="Pdf2",
)
