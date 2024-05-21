Making the mac installer uses pyinstaller. This must be done with
miniconda to properly package the LLVMLite package for numba. In order to set up the
proper build environment, simply install from source as in the RAW documentation, then
additionally install pyinstaller through pip: pip install pyinstaller.

Steps:
1)  Make a fresh git-free folder for RAW: git archive master | tar -x -C /somewhere/else
2)  Set the appropriate python path, if needed: export PATH=~/miniconda2/bin:$PATH
3)  Build the extensions and run RAW in that new folder.
4)  Build the html documentation
5)  In the installer directory, run “pyinstaller -y RAW.spec”
6)  The app file is located at ./dist/RAW.app #NOTE: The dist/RAW/RAW executable will not open because the resources path is wrong if it's not in the .app package!
7)  In the app file, remove and simlink wxpython dylibs as necesscary (see wxpython note below)
8)  Get your developer certificate hash: security find-identity -p basic -v
    The has is the long string of numbers and letters at the start
9)  Codesign the resources folder, from the top level installer folder:
    codesign --deep --force --options=runtime --entitlements ./entitlements.plist
        --sign "<hash>" --timestamp ./dist/RAW.app/Contents/Resources/*.dylib
10) Codesign the overall app:
    codesign --deep --force --options=runtime --entitlements ./entitlements.plist
    --sign "<hash>" --timestamp ./dist/RAW.app
11) Verify the codesigning:
    codesign --verify --verbose ./dist/RAW.app/Contents/Resources/*.dylib
    codesign --verify --verbose ./dist/RAW.app
12) Open disk utility
13) Create a new disk image (File->New Image>Blank Image) that is ~12% larger than the
    .app package. Name it RAW, but save it as untitled.
14) Open the mounted disk image. Copy the .app file and a shortcut of the applications
    folder to the disk image. Size and arrange as desired.
15) In Disk Utility, Image->Convert, select the prepared disk image, and name it RAW-x.y.z-mac-<sys>
    (note, the disk image must be ejected for this to work)
16) Notarize the disk image (will take some time to process):
    xcrun notarytool submit --apple-id "<apple_id>" --password "<notarytool_pwd>"
    --team-id "<team_id>" --wait RAW-x.y.z-mac-<sys>.dmg
17) After succesful notarzation (see troubleshooting below if needed), staple
    the notarization to the dmg:
    xcrun stapler staple -v RAW-x.y.z-mac-<sys>.dmg



Codesigning/notarization notes:
- Requires an apple developer account
- Must create a Developer ID Application certificate
- Add your developer account to XCode on the machine you're using
- Get your team_id from your developer account
- In your apple account create an app specific password for notarytool
- Using notarytool requires Xcode >=13, which requires MacOS 11
- If needed, can use this command to get more info on a failed notarization:
    xcrun notarytool log "<notarization_id>" --apple-id "<apple_id>"
    --password "<notarytool_pwd>" --team-id "<team_id>"

    Where the first argument is the request UUID, which can be found in
    the submission or using “xcrun notartyool history”

Useful resources:
https://lessons.livecode.com/m/4071/l/1653720-code-signing-and-notarizing-your-lc-standalone-for-distribution-outside-the-mac-appstore-with-xcode-13-and-up
https://developer.apple.com/forums/thread/128166
https://gist.github.com/txoof/0636835d3cc65245c6288b2374799c43


wxpython notes:
Currenty wxpython versions >=4.1 require some manual modification to package
with pyinstaller, as described here:
https://github.com/pyinstaller/pyinstaller/issues/5710

First:
cd dist/program.app/Contents/MacOS/
Then:
Commands for wxpython 4.1:
rm -f libwx_osx_cocoau_core-3.1.5.0.0.dylib libwx_baseu-3.1.5.0.0.dylib
ln -s libwx_osx_cocoau_core-3.1.dylib libwx_osx_cocoau_core-3.1.5.0.0.dylib
ln -s libwx_baseu-3.1.dylib libwx_baseu-3.1.5.0.0.dylib

Commands for wxpython 4.2 on x86_64:
rm -f libwx_osx_cocoau_core-3.2.0.0.0.dylib libwx_baseu-3.2.0.0.0.dylib
ln -s libwx_osx_cocoau_core-3.2.dylib libwx_osx_cocoau_core-3.2.0.0.0.dylib
ln -s libwx_baseu-3.2.dylib libwx_baseu-3.2.0.0.0.dylib

Commands for wxpython 4.2 on arm64:
rm -f libwx_osx_cocoau_core-3.2.0.0.0.dylib libwx_baseu-3.2.0.0.0.dylib
ln -s libwx_osx_cocoau_core-3.2.0.dylib libwx_osx_cocoau_core-3.2.0.0.0.dylib
ln -s libwx_baseu-3.2.0.dylib libwx_baseu-3.2.0.0.0.dylib



Other current notes:
-   Successful codesigning seems to require the latest version of pyinstaller (5.11).
    Note that this version isn't on conda for python 3.11, so if using 3.11 you need
    to install from pip.
- Currently building on MacOS 11, in the raw_build environment.



Older notes, might still be relevant:
Need to use wxpython >=4.1 to eliminate some weird GUI glitches on MacOS 11.

For RAW to work on macbooks older than 2011 need to install all packages
through conda forge. The new ones through conda have some weird error. See:
https://github.com/conda/conda/issues/9678

For RAW to build on 10.9, using python 3, install miniconda from the
4.5.12 installer (not latest!)

It looks like when the intel mkl library is linked to numpy, the Mac build
gets really big (~750 MB). Can unlink it by install conda package nomkl if desired.

In order to refresh the size of the RAW.app package you need to first delete the .DS_store file
that is in the folder it is in, then relaunch Finder from the force quit menu.

More info on disk images here:
https://el-tramo.be/blog/fancy-dmg/

Pyinstaller command used to generate initial .spec file:

pyinstaller --add-data ./resources:resources --hidden-import _sysconfigdata --additional-hooks-dir ../MacLib/installer/ --exclude-module PyQt5 --exclude-module tk --exclude-module ipython --exclude-module tcl -d all -i resources/raw.icns --osx-bundle-identifier edu.bioxtas.raw --windowed RAW.py

