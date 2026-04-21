# -*- mode: python ; coding: utf-8 -*-
import os

block_cipher = None

# 获取当前目录
current_dir = os.path.dirname(os.path.abspath(SPEC))

a = Analysis(
    ['main.py'],
    pathex=[current_dir],
    binaries=[],
    datas=[
        # 包含本地 Python 模块文件
        (os.path.join(current_dir, 'task_manager_v2.py'), '.'),
        (os.path.join(current_dir, 'executor.py'), '.'),
        (os.path.join(current_dir, 'message_queue_client.py'), '.'),
        (os.path.join(current_dir, 'config.py'), '.'),
        (os.path.join(current_dir, 'gui'), 'gui'),
        (os.path.join(current_dir, 'utils'), 'utils'),
    ],
    hiddenimports=[
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
        'PyQt6.sip',
        'loguru',
        'requests',
        'urllib3',
        'pika',
        'pika.adapters.blocking_connection',
        'pika.connection',
        'pika.channel',
        'pika.credentials',
        'selenium',
        'selenium.webdriver',
        'selenium.webdriver.common',
        'selenium.webdriver.common.by',
        'selenium.webdriver.common.keys',
        'selenium.webdriver.chrome',
        'selenium.webdriver.chrome.service',
        'webdriver_manager',
        'webdriver_manager.chrome',
        'psutil',
        'qasync',
        'config',
        'task_manager_v2',
        'executor',
        'message_queue_client',
        'utils',
        'utils.system',
        'gui',
        'gui.main_window',
        'gui.config_wizard',
        'gui.log_window',
    ],
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
    [],
    exclude_binaries=True,
    name='AutoTestExecutor',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
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
    upx=True,
    upx_exclude=[],
    name='AutoTestExecutor',
)
