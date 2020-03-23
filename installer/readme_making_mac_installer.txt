Making the mac installer users pyinstaller (tested on 3.4.0). This must be done with
miniconda to properly package the LLVMLite package for numba. In order to set up the
proper build environment, simply install from source as in the RAW documentation, then
additionally install pyinstaller through pip: pip install pyinstaller.

Note: currently requires setuptools<0.45 to work.

Steps:
1) Make a fresh git-free folder for RAW: git archive master | tar -x -C /somewhere/else
2)  Build the extensions and run RAW in that new folder.
3)  Set the appropriate python path, if needed: export PATH=~/miniconda2/bin:$PATH
4)  Copy the RAW_mac.spec file into the main RAW directory.
5)  Run “pyinstaller -y RAW_mac.spec”
6)  The app file is located at ./dist/RAW.app #NOTE: The dist/RAW/RAW executable will not open because the resources path is wrong if it's not in the .app package!
7)  Open disk utility
8)  Create a new disk image (File->New Image>Blank Image) that is ~12% larger than the
    .app package. Name it RAW, but save it as untitled.
9)  Open the mounted disk image. Copy the .app file and a shortcut of the applications
    folder to the disk image. Size and arrange as desired.
9)  In Disk Utility, Image->Convert, select the prepared disk image, and name it RAW-x.y.z-mac
    (note, the disk image must be ejected for this to work

Note: if pyopencl is installed, the build will fail.

Note 2: Without numba, I've now gotten this to work with stock enthought canopy, with the extra
raw packages installed through pip (Fabio, pyfai, hdf5plugin) and uninstalling pyside.

Note 3: It looks like when the intel mkl library is linked to numpy, the Mac build
gets really big (~750 MB). Can unlink it by install conda package nomkl if desired.

Note 4: In order to refresh the size of the RAW.app package you need to first delete the .DS_store file
that is in the folder it is in, then relaunch Finder from the force quit menu.

More info on disk images here:
https://el-tramo.be/blog/fancy-dmg/

Pyinstaller command used to generate initial .spec file:

pyinstaller --add-data ./resources:resources --hidden-import _sysconfigdata --additional-hooks-dir ../MacLib/installer/ --exclude-module PyQt5 --exclude-module tk --exclude-module ipython --exclude-module tcl -d all -i resources/raw.icns --osx-bundle-identifier edu.bioxtas.raw --windowed RAW.py

