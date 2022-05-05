Linux install from source instructions
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.. _lnxsource:

#.  Open a new terminal window (in many distros you can right click on the desktop
    and select :menuselection:`New Terminal` or :menuselection:`Open in terminal`).

#.  Download Miniconda Python (Python 3.x, e.g. 3.8) distribution and install.

    *   `https://docs.conda.io/en/latest/miniconda.html <https://docs.conda.io/en/latest/miniconda.html>`_

    *   Make sure you chose the python 3.x installer.

    *   Save to the downloads folder

    *   Open a terminal and run the following commands:

        *   ``cd ~/Downloads``

        *   :samp:`bash ./Miniconda3{-version}.sh` (where :samp:`{-version}`
            which will depend on the version you download)

    *   Accept the default installation location.

    *   At the end, say “yes” to have the conda python install put in your system path.

    *   Close the terminal window.

#.  Install python packages. Open a new terminal window and run the following commands
    (in many distros you can right click on the desktop and select :menuselection:`New Terminal`
    or :menuselection:`Open in terminal`).

    *   ``conda upgrade conda pip wheel setuptools``

    *   ``conda install numpy scipy matplotlib pillow numba h5py cython numexpr reportlab``

    *  ``conda install -c conda-forge wxpython dbus-python fabio pyfai hdf5plugin mmcif_pdbx``

#.  Download RAW source code from sourceforge

    *   `https://sourceforge.net/projects/bioxtasraw/files <https://sourceforge.net/projects/bioxtasraw/files>`_

    *   Go to the linked website and download the :file:`RAW-x.y.z-Source.zip`
        file, where :file:`x.y.z` is the version number (for example, 1.0.0).

#.  Expand the RAW download to your location of choice.

    *   We suggest :file:`~/raw`

    *   Make sure there are no spaces in the file path (you can check by navigating
        to the raw directory in a terminal window and using ``pwd``).

    *   In the terminal or in the graphical file manager, confirm that the file named :file:`setup.py`
        is in your raw directory. If it isn’t, it’s likely that when you expanded the
        RAW download, you ended up with unnecessary layers of directories. Find the
        directory with :file:`setup.py` in it, and make that the top level folder.

#.  In a terminal, change directory into the top level RAW folder

    *   If you used the suggested path of :file:`~/raw` type: ``cd ~/raw``

#.  Build the extensions.

    *   ``python setup.py build_ext --inplace``

#.  Navigate to the :file:`bioxtasraw` subfolder

    *   From the top level RAW folder it should be ``cd ./bioxtasraw``

#.  Run RAW

    *   ``python RAW.py``

#.  RAW is now installed. Enjoy!

    *   If you want, see the section on :ref:`making a desktop shortcut for RAW <lnxsrt>`.

    *   If RAW doesn’t work, check out the :ref:`solutions to common problems <lnxtrb>`.
