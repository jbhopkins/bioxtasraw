Linux install from source instructions
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Tested on: Ubuntu 16.04, Linux Mint 18.3, Debian 9.4, Scientific Linux 6.8 7.4
\(which should be equivalent to Redhat and CentOS), and OpenSUSE Leap 42.3.

#.  Open a new terminal window (in many distros you can right click on the desktop
    and select :menuselection:`New Terminal` or :menuselection:`Open in terminal`).

#.  Download Miniconda Python (Python 2.7) distribution and install.

    *   `http://conda.pydata.org/miniconda.html <http://conda.pydata.org/miniconda.html>`_

    *   Make sure you chose the python 2.7 installer.

    *   Save to the downloads folder

    *   Open a terminal and run the following commands:

        *   ``cd ~/Downloads``

        *   :samp:`bash ./Miniconda2{-version}.sh` (where :samp:`{-version}`
            which will depend on the version you download)

    *   Accept the default installation location.

    *   At the end, say “yes” to have the conda python install put in your system path.

    *   Close the terminal window.

#.  Install python packages. Open a new terminal window and run the following commands
    (in many distros you can right click on the desktop and select :menuselection:`New Terminal`
    or :menuselection:`Open in terminal`).

    *   ``conda upgrade conda pip wheel setuptools``

    *   ``conda install numpy scipy matplotlib pillow wxpython numba h5py lxml cython numexpr``

    *   ``pip install fabio pyFAI hdf5plugin weave``

#.  Download RAW from sourceforge

    *   `http://sourceforge.net/projects/bioxtasraw/ <http://sourceforge.net/projects/bioxtasraw/>`_

    .. raw:: html

        <a href="https://sourceforge.net/projects/bioxtasraw/files/latest/download"><img alt="Download BioXTAS RAW" src="https://a.fsdn.com/con/app/sf-download-button" width=276 height=48 srcset="https://a.fsdn.com/con/app/sf-download-button?button_size=2x 2x"></a>

    *   The download button on the main page should default to the right download for your OS.

#.  Expand the RAW download to your location of choice.

    *   We suggest :file:`~/raw`

    *   Make sure there are no spaces in the file path (you can check by navigating
        to the raw directory in a terminal window and using ``pwd``).

    *   In the terminal or in the graphical file manager, confirm that the file named :file:`RAW.py`
        is in your raw directory. If it isn’t, it’s likely that when you expanded the
        RAW download, you ended up with unnecessary layers of directories. Find the
        directory with :file:`RAW.py` in it, and make that the top level folder.

#.  In a terminal, change directory into the top level RAW folder

    *   If you used the suggested path of :file:`~/raw` type: ``cd ~/raw``

#.  Run RAW

    *   ``python RAW,py``

#.  RAW is now installed. Enjoy!

    *   If you want, see the section on :ref:`making a desktop shortcut for RAW <lnxsrt>`.

    *   If RAW doesn’t work, check out the :ref:`solutions to common problems <lnxtrb>`.
