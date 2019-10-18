# -*- mode: python -*-

import sys
sys.path.append('.')
import RAWGlobals

block_cipher = None


a = Analysis(['RAW.py'],
             pathex=['.'],
             binaries=[],
             datas=[('./resources', 'resources'), ('./definitions', 'definitions'), ('../gpl-3.0.txt', '.')],
             hiddenimports=['_sysconfigdata'],
             hookspath=['../MacLib/installer/'],
             runtime_hooks=[],
             excludes=['PyQt5', 'tk', 'ipython', 'tcl'],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          [],
          exclude_binaries=True,
          name='RAW',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          console=False , icon='resources/raw.icns')
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               name='RAW')
app = BUNDLE(coll,
             name='RAW.app',
             icon='resources/raw.icns',
             bundle_identifier='edu.bioxtas.raw',
             info_plist={
                'CFBundleVersion' : RAWGlobals.version,
                'CFBundleShortVersionString' : RAWGlobals.version,
                'LSBackgroundOnly' : '0',
                'NSHighResolutionCapable' : True,
                'NSPrincipleClass' : 'NSApplication',
                'CFBundleDevelopmentRegion' : 'en_US',
                'LSHasLocalizedDisplayName' : False,
                'CFBundleDocumentTypes' : [
                    {
                        'CFBundleTypeName' : 'SAXS data file',
                        'LSHandlerRank' : 'Default',
                        'CFBundleTypeExtensions': ['out', 'fit', 'fir', 'rad',
                            'int', 'dat', 'csv', 'sub', 'txt'],
                        'CFBundleTypeRole' : 'Viewer'
                    },
                    {
                        'CFBundleTypeName' : 'Image file',
                        'LSHandlerRank' : 'Default',
                        'CFBundleTypeExtensions': ['tif', 'tiff', 'nxs', 'edf',
                            'ccdraw', 'img', 'imx_0', 'dkx_0', 'dxk_1', 'png',
                            'mpa', 'mar1200', 'mar2400', 'mar3200', 'mar3600',
                            'sfrm', 'dm3', 'xml', 'cbf', 'kccd', 'msk',
                            'spr', 'h5', 'mccd', 'mar3450', 'npy', 'No'],
                        'CFBundleTypeRole' : 'Viewer'
                    },
                    {
                        'CFBundleTypeName' : 'LC data file',
                        'LSHandlerRank' : 'Default',
                        'CFBundleTypeExtensions': ['sec',],
                        'CFBundleTypeRole' : 'Viewer'
                    },
                ],
             },
             )

try:
    os.mkdir('./dist/RAW/pyFAI/utils')
except Exception as e:
    print(e)

try:
    os.mkdir('./dist/RAW.app/Contents/Resources/pyFAI/utils')
except Exception as e:
    print(e)
