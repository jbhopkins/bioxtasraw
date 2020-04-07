Making the .deb installer uses pyinstaller (tested on 3.6.0). This must be done with
miniconda to properly package the LLVMLite package for numba. In order to set up the
proper build environment, simply install from source as in the RAW documentation, then
additionally install pyinstaller through pip or conda: pip install pyinstaller.

Note: currently requires setuptools<0.45 to work.

Steps:
1)  Install fakeroot, lintian: sudo apt-get install fakeroot lintian
2)  Install conda nomkl: conda install nomkl
3)  Fix pyFAI utils error (should be fixed in 0.20 release) by editing line 166 of utils/__init__.py
    in site packages to use os.path.abspath.
4)  Make a fresh git-free folder for RAW: git archive master | tar -x -C /somewhere/else
5)  Build the extensions and run RAW in that new folder.
6)  Build the html documentation
7)  In the installer directory, run “pyinstaller -y RAW.spec”
8)  In the installer/linux directory run "python make_deb_installer.py"
9)  Rename the package appropriate (e.g. RAW-2.0.0-linux-amd64.deb)
