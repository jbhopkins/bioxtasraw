# -*- mode: python -*-

block_cipher = None

add_files = [('./resources', 'resources'), ('../gpl-3.0.txt', '.')]

a = Analysis(['RAW.py'],
             pathex=['.'],
             binaries=None,
             datas=add_files,
             hiddenimports=[],
             hookspath=['../WinLib/installer'],
             runtime_hooks=[],
             excludes=['PyQt5', 'tk', 'ipython', 'tcl'],
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
