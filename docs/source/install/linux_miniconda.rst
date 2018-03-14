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

#.  Install python packages. Open a new terminal window and run the following commands.

    *   ``conda update conda setuptools wheel pip``

    *   ``conda install numpy scipy matplotlib pillow h5py lxml cython numexpr``

    *   ``conda install 'wxpython<4'``

    *   ``pip install fabio pyFAI hdf5plugin weave``

#.  Download RAW from sourceforge

    *   `http://sourceforge.net/projects/bioxtasraw/ <http://sourceforge.net/projects/bioxtasraw/>`_

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

    *   The first time RAW runs, it may take a little while to load, as it has to
        compile various extensions.

#.  RAW is now installed. Enjoy!

    *   If you want, see the section on :ref:`making a desktop shortcut for RAW <lnxsrt>`.

    *   If RAW doesn’t work, check out the :ref:`solutions to common problems <lnxtrb>`.
