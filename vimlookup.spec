# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec file for VimLookup backend server

Build with: pyinstaller vimlookup.spec

This creates a single executable that bundles:
- Python interpreter
- All dependencies (FastAPI, uvicorn, OpenAI, etc.)
- Application code (lookup package, web backend)
- Static frontend files
"""

import sys
from pathlib import Path

block_cipher = None

# Project root
ROOT = Path(SPECPATH)

# Collect all data files
datas = [
    # Frontend static files
    (str(ROOT / 'web' / 'frontend'), 'web/frontend'),
    # Config file template (optional, will be created on first run)
]

# Hidden imports that PyInstaller might miss
hiddenimports = [
    'uvicorn.logging',
    'uvicorn.loops',
    'uvicorn.loops.auto',
    'uvicorn.protocols',
    'uvicorn.protocols.http',
    'uvicorn.protocols.http.auto',
    'uvicorn.protocols.websockets',
    'uvicorn.protocols.websockets.auto',
    'uvicorn.lifespan',
    'uvicorn.lifespan.on',
    'uvicorn.lifespan.off',
    'httptools',
    'dotenv',
    'email_validator',
    'multipart',
    'python_multipart',
    # OpenAI and HTTP
    'openai',
    'httpx',
    'httpcore',
    'h11',
    'anyio',
    'sniffio',
    # FastAPI/Starlette
    'fastapi',
    'starlette',
    'starlette.responses',
    'starlette.routing',
    'starlette.middleware',
    'starlette.middleware.cors',
    # Pydantic
    'pydantic',
    'pydantic.deprecated',
    'pydantic.deprecated.decorator',
    # BeautifulSoup
    'bs4',
    'lxml',
    'lxml.etree',
    # Our packages
    'lookup',
    'lookup.config',
    'lookup.domain',
    'lookup.cache',
    'lookup.cache.base',
    'lookup.cache.jsonl',
    'lookup.cache.memory',
    'lookup.cli',
    'lookup.cli.factory',
    'lookup.conversation',
    'lookup.conversation.service',
    'lookup.dictionary',
    'lookup.dictionary.scraper',
    'lookup.dictionary.service',
    'lookup.orchestration',
    'lookup.orchestration.service',
    'lookup.translation',
    'lookup.translation.llm',
    'lookup.translation.llm.base',
    'lookup.translation.llm.openai',
    'lookup.translation.prompts',
    'lookup.translation.service',
    'web',
    'web.backend',
    'web.backend.app',
    'web.backend.routes',
    'web.backend.session',
    'web.backend.models',
    # Platformdirs
    'platformdirs',
    # OCR
    'pytesseract',
    'PIL',
]

a = Analysis(
    ['backend_server.py'],
    pathex=[str(ROOT / 'src'), str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'numpy',
        'pandas',
        'cv2',
    ],
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
    name='vimlookup-server',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # Keep console for logging
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
