# -*- mode: python -*-

block_cipher = None

add_files = [('/raw/resources', 'resources'), ('/raw/gpl-3.0.txt', '.')]

a = Analysis(['RAW.py'],
             pathex=['C:\\Python27\\lib\\site-packages\\scipy\\extra-dll',
             'C:\\raw'],
             binaries=None,
             datas=add_files,
             hiddenimports=['scipy._lib.messagestream'],
             hookspath=['./WinLib/installer'],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          exclude_binaries=True,
          name='RAW',
          debug=False,
          strip=False,
          upx=True,
          console=True , icon='./resources/raw.ico')
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               name='RAW')
