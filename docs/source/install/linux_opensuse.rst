OpenSUSE install from source instructions
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.. _lnxopensuse:

Tested on OpenSUSE Leap 42.2.

#.  Open a terminal and run the following commands (hit enter/return to execute each command):

    *   *sudo zypper update*

    *   *sudo zypper install python-devel*

    *   *sudo zypper install gcc-c++*


#.  Download Miniconda Python (Python 2.7) distribution and install.

    *   `http://conda.pydata.org/miniconda.html <http://conda.pydata.org/miniconda.html>`_

    *   Make sure you chose the python 2.7 installer.

    *   Save to the downloads folder

    *   Open a terminal and run the following commands:

        *   *cd Downloads*

        *   *bash ./Miniconda2<stuff>.sh* (<stuff> is the appropriate filename,
            which will depend on the version you download)

    *   Accept the default installation location.

    *   At the end, say “yes” to have the conda python install put in your system path.

#.  Install python packages. Open a new terminal window and run the following commands.

    *   *conda install numpy scipy matplotlib pillow wxpython h5py lxml cython*

    *   *pip install -U pip setuptools wheel*

    *   *pip install fabio pyFAI hdf5plugin weave*

#.  Download RAW from sourceforge

    *   `http://sourceforge.net/projects/bioxtasraw/ <http://sourceforge.net/projects/bioxtasraw/>`_

    *   The download button on the main page should default to the right download for your OS.

#.  Expand the RAW download to your location of choice.

    *   We suggest **~/raw**

    *   Make sure there are no spaces in the file path (you can check by navigating
        to the raw directory in a terminal window and using *pwd*).

    *   In the terminal or in the graphical file manager, confirm that the file named **RAW.py**
        is in your raw directory. If it isn’t, it’s likely that when you expanded the
        RAW download, you ended up with unnecessary layers of directories. Find the
        directory with **RAW.py** in it, and make that the top level folder.

#.  In a terminal, change directory into the top level RAW folder

    *   If you used the suggested path of **~/raw** type: *cd ~/raw*

#.  Run RAW

    *   *python RAW,py*

    *   The first time RAW runs, it may take a little while to load, as it has to
        compile various extensions.

#.  RAW is now installed. Enjoy!

    *   If you want, see the section on :ref:`making a desktop shortcut for RAW <lnxsrt>`.

    *   If RAW doesn’t work, check out the :ref:`solutions to common problems <lnxtrb>`.
