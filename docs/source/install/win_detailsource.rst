Windows 7, 8.1, and 10 install from source instructions
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.. _winsource:

#.  RAW on windows can be installed using 64 bit (x64) or 32 bit (x86) python. Unless you know
    you need a 32 bit build, you should install the 64 bit version. Some libraries,
    such as pyFAI, maybe hard to install on 32 bit windows.

#.  Download and install the Microsoft Visual C++ 14.2 Standalone: Build Tools for Visual Studio 2019.

    *   `https://wiki.python.org/moin/WindowsCompilers#Microsoft_Visual_C.2B-.2B-_14.2_standalone:_Build_Tools_for_Visual_Studio_2019_.28x86.2C_x64.2C_ARM.2C_ARM64.29 <https://wiki.python.org/moin/WindowsCompilers#Microsoft_Visual_C.2B-.2B-_14.2_standalone:_Build_Tools_for_Visual_Studio_2019_.28x86.2C_x64.2C_ARM.2C_ARM64.29>`_

    *   Download from here: https://visualstudio.microsoft.com/downloads/#build-tools-for-visual-studio-2019

    *   Run the installer and install the C++ build tools with the default options.

#.  Install Miniconda python distribution

    *   Download the free miniconda python 3.x, e.g. 3.8, installer from:
        `https://docs.conda.io/en/latest/miniconda.html <https://docs.conda.io/en/latest/miniconda.html>`_

        *   Make sure you get the python 3.x version!

        *   Pick the appropriate 64 bit/32 bit version (64 bit recommended!).

    *   Run the installer with the default options.

    *   More detailed install instructions are available here:
        `https://conda.io/docs/user-guide/install/windows.html <https://conda.io/docs/user-guide/install/windows.html>`_

#.  Install the necessary python packages

    *   Open an anaconda prompt by clicking on the start menu -> All Programs -> Anaconda3 -> Anaconda Prompt

    *   Run the following commands in the anaconda prompt:

    *   ``conda upgrade conda pip wheel setuptools``

    *   ``conda install numpy scipy "matplotlib<3.2" pillow numba h5py cython numexpr``

    *  ``conda install -c conda-forge "wxpython<4.1"``

    *   ``pip install hdf5plugin silx fabio pyfai``

#.  Download RAW from sourceforge (
    `https://sourceforge.net/projects/bioxtasraw <https://sourceforge.net/projects/bioxtasraw>`_)

    *   Go to the Files tab on the linked website and download the :file:`RAW-x.y.z-Source.zip`
        file, where :file:`x.y.z` is the version number (for example, 1.0.0).

#.  Expand the downloaded zip file into the downloads folder

    *   Right click on the download and select :menuselection:`Extract All`

    *   Accept the default location for files to be extracted.

    |1000020100000274000001CAC03003E6F7E944B5_png|

#.  In Windows Explorer, confirm that the file named :file:`setup.py`
    is in your top level expanded raw directory. If it isn’t, it’s likely that
    when you expanded the RAW download, you ended up with unnecessary layers of
    directories. Find the directory with :file:`setup.py` in it, and make that
    the top level folder.

#.  Build the extensions

    *   Open an anaconda prompt as in Step 4 of these instructions.

    *   Type ``cd C:\raw``

    *   Hit enter

    *   Type ``python setup.py build_ext --inplace``

    *   Hit enter

#.  Run :file:`RAW.py` from the command line

    *   Open an anaconda prompt as in Step 4 of these instructions.

    *   Type ``cd C:\raw\bioxtasraw``

    *   Hit enter

    *   Type ``python RAW.py``

    *   Hit enter

#.  Enjoy!

    *   If you have trouble with the installation, please see the
        :ref:`solutions to common problems <wintrb>` section below.


.. |1000020100000274000001CAC03003E6F7E944B5_png| image:: images/win_install/1000020100000274000001CAC03003E6F7E944B5.png
