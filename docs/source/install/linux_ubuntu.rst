Ubuntu/Linux Mint install from source instructions
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.. _lnxubuntu:

Tested on Ubuntu 16.04, Linux Mint 18.1.

#.  Open a terminal (right click on the desktop -> new terminal) and run the following
    commands (hit enter/return to execute each command):

    *   *su* (may not be necessary on some machines)

    *   *sudo apt-get update*

    *   *sudo apt-get upgrade*

    *   *sudo apt-get install build-essential*

    *   *sudo apt-get install python-dev*

    *   *sudo apt-get install python-numpy python-scipy python-matplotlib python-wxgtk3.0
        python-pillow python-fabio python-pip cython python-pyfai*

    *   *sudo pip install --upgrade pip*

    *   *sudo pip install --upgrade wheel setuptools*

    *   *sudo pip install --upgrade --no-deps fabio pyfai*

    *   *sudo pip install hdf5plugin weave*

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
