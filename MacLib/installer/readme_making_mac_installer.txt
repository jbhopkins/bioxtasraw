Making the mac installer users pyinstaller (tested on 3.4.0). This must be done with
miniconda to properly package the LLVMLite package for numba. In order to set up the
proper build environment, simply install from source as in the RAW documentation, then
additionally install pyinstaller through pip: pip install pyinstaller.

Steps:
0) Make a fresh git-free folder for RAW: git archive master | tar -x -C /somewhere/else
1) Run RAW in that new folder to compile the extensions.
2)  Set the appropriate python path, if needed: export PATH=~/miniconda2/bin:$PATH
3)  Copy the RAW_mac.spec file into the main RAW directory.
4)  Run “pyinstaller -y RAW_mac.spec”
5)  Copy the RAW.app file from the MacLib/installer folder to the main RAW folder.
    Show the contents in finder, and copy the contents of the dist/RAW directory to the
    Contents/MacOS folder in the .app file.
6)  Update the version number in the info.plist file in the top level of the .app folder.
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
