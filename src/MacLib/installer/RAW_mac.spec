# -*- mode: python -*-

block_cipher = None

add_files = []

a = Analysis(['RAW.py'],
             pathex=['.'],
             binaries=[],
             datas=add_files,
             hiddenimports=['_sysconfigdata'],
             hookspath=['./MacLib/installer'],
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
          console=True )
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               name='RAW')


#Have to hack pyFAI a little bit to make it work right in frozen mode
import os

try:
  os.mkdir('./dist/RAW/pyFAI/utils')
except:
  pass
