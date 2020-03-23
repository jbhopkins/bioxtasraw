# -*- mode: python -*-

import sys
import platform
import os.path

sys.path.append(os.path.join('..', 'bioxtasraw'))
import RAWGlobals

opsys = platform.system()

add_files = [
    (os.path.join('..', 'bioxtasraw', 'resources'), 'resources'),
    (os.path.join('..', 'bioxtasraw', 'definitions'), 'definitions'),
    (os.path.join('..', 'gpl-3.0.txt'), '.'),
    ]

if opsys == 'Darwin':
    raw_icon = os.path.join('..', 'bioxtasraw', 'resources', 'raw.icns')
elif opsys == 'Windows':
    raw_icon = os.path.join('..', 'bioxtasraw', 'resources', 'raw.ico')

a = Analysis(
    [os.path.join('..', 'bioxtasraw', 'RAW.py')],
    pathex=['.'],
    binaries=[],
    datas=add_files,
    hiddenimports=[],
    hookspath=['.'],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
    )

pyz = PYZ(
    a.pure,
    a.zipped_data,
    cipher=None,
    )

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='RAW',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon=raw_icon
    )

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    name='RAW',
    )

if opsys == 'Darwin':
    app = BUNDLE(
        coll,
        name='RAW.app',
        icon=raw_icon,
        bundle_identifier='edu.bioxtas.raw',
        info_plist=
            {
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
        os.mkdir(os.path.join('.', 'dist', 'RAW', 'pyFAI', 'utils'))
    except Exception as e:
        print(e)

    try:
        os.mkdir(os.path.join('.', 'dist', 'RAW.app', 'Contents', 'Resources', 'pyFAI', 'utils'))
        os.mkdir(os.path.join('.', 'dist', 'RAW.app', 'Contents', 'MacOS', 'pyFAI', 'utils'))
    except Exception as e:
        print(e)
