# -*- mode: python -*-

import sys
import platform
import os.path

sys.path.append(os.path.join('..', 'bioxtasraw'))
import RAWGlobals

opsys = platform.system()

if opsys != 'Linux':
    add_files = [
        (os.path.join('..', 'bioxtasraw', 'resources'), 'resources'),
        (os.path.join('..', 'bioxtasraw', 'definitions'), 'definitions'),
        (os.path.join('..', 'bioxtasraw', 'denss_resources'),
            os.path.join('bioxtasraw', 'denss_resources')),
        (os.path.join('..', 'gpl-3.0.txt'), '.'),
        (os.path.join('..', 'docs', 'build', 'html'), 'docs'),
        ]
else:
    add_files = [
        (os.path.join('..', 'bioxtasraw', 'resources'), os.path.join('share', 'bioxtas-raw', 'resources')),
        (os.path.join('..', 'bioxtasraw', 'definitions'), os.path.join('share', 'bioxtas-raw', 'definitions')),
        (os.path.join('..', 'bioxtasraw', 'denss_resources'), os.path.join('bioxtasraw', 'denss_resources')),
        (os.path.join('..', 'gpl-3.0.txt'), '.'),
        (os.path.join('..', 'docs', 'build', 'html'), os.path.join('share', 'bioxtas-raw', 'docs')),
        ]

if opsys == 'Darwin':
    raw_icon = os.path.join('..', 'bioxtasraw', 'resources', 'raw.icns')
    console = False
elif opsys == 'Windows':
    raw_icon = os.path.join('..', 'bioxtasraw', 'resources', 'raw.ico')
    console = False
elif opsys == 'Linux':
    raw_icon = os.path.join('..', 'bioxtasraw', 'resources', 'raw.png')
    console = False

options=[('W ignore', None, 'OPTION')]

a = Analysis(
    [os.path.join('..', 'bioxtasraw', 'RAW.py')],
    pathex=['.'],
    binaries=[],
    datas=add_files,
    hiddenimports=[],
    hookspath=['.'],
    runtime_hooks=[],
    excludes=['PyQt5', 'PyQt6', 'PySide6', 'tkinter', 'sphinx', 'pyopengl',
        'opengl', 'pyopencl', 'opencl', 'pytest', 'IPython', 'OpenGL'],
    hooksconfig={
        'matplotlib': {
            'backends': ['AGG', 'PDF', 'PS', 'SVG', 'PGF', 'Cairo', 'wxAgg'],
        }
    },
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

if opsys == 'Darwin':
    exe = EXE(
        pyz,
        a.scripts,
        options,
        exclude_binaries=True,
        name='RAW',
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        console=console,
        icon=raw_icon,
        disable_windowed_traceback=False,
#        target_arch='arm64',
        codesign_identity=None,
        entitlements_file=None,
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
elif opsys != 'Linux':
    exe = EXE(
        pyz,
        a.scripts,
        options,
        exclude_binaries=True,
        name='RAW',
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        console=console,
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
else:
    exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          options,
          name='bioxtas-raw',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          upx_exclude=[],
          runtime_tmpdir=None,
          console=True )


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
                        'int', 'dat', 'csv', 'sub', 'txt', 'ift'],
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

if opsys == 'Linux':
    try:
        os.mkdir(os.path.join('.', 'dist', 'RAW', 'pyFAI', 'utils'))
    except Exception:
        pass
