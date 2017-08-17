RAW Install Guide for Linux
---------------------------
.. _lnxsource:

Introduction
^^^^^^^^^^^^

This guide contains instructions for:

*   :ref:`General instructions to install from source for advanced users <lnxgen>`

*   Detailed instructions to install from source for:

    *   :ref:`Ubuntu/Linux Mint <lnxubuntu>`
    *   :ref:`Debian <lnxdebian>`
    *   :ref:`OpenSUSE <lnxopensuse>`
    *   :ref:`Scientific Linux/Red Hat <lnxsl>`

*   :ref:`How to make a clickable shortcut to start RAW <lnxsrt>`

It also provides :ref:`solutions to common problems <lnxtrb>` with the
installation from source.


Conventions: things to type are in *italics* , file paths and file names are in
**bold**.

If you have questions or feedback, please contact us.


General instructions for installing from source (advanced users)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.. _lnxgen:

#.  Install python 2.7 (if it isn’t already installed).

#.  Install the python development tools.

#.  Install the gcc c++ compiler.

#.  Install the following python packages (version indicated if less than most recent):

    *   numpy

    *   scipy

    *   matplotlib

    *   pillow

    *   wxpython

    *   fabio

    *   h5py

    *   lxml

    *   pyFAI

    *   hdf5plugin

    *   weave

#.  Download RAW from sourceforge (
    `http://sourceforge.net/projects/bioxtasraw <http://sourceforge.net/projects/bioxtasraw>`_)

#.  Extract RAW to a directory of your choice, and run **RAW.py** using python.

    *   Note: the first time you run RAW.py it may need to be run from the command line
        in order to successfully compile various extensions. It may take some time to
        compile the extensions, be patient.

#.  Enjoy!

    *   If you have problems, please consult the detailed installation guides below and check
        out the :ref:`solutions to common problems <lnxtrb>`.

    *   If you want, see the section on :ref:`making a desktop shortcut for RAW <lnxsrt>`.


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


Debian install from source instructions
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.. _lnxdebian:

Tested on Debian 8.7.

#.  Installation is the same as for Ubuntu/Linux Mint, but instead of 1, do:

    *   *su* (may not be necessary on some machines)

    *   *sudo apt-get update*

    *   *sudo apt-get upgrade*

    *   *sudo apt-get install build-essential*

    *   *sudo apt-get install python-dev*

    *   *sudo apt-get install python-numpy python-scipy python-matplotlib python wxgtk3.0
        python-pip cython python-h5py python-lxml*

    *   *sudo pip install –U pip wheel setuptools*

    *   *sudo pip install pillow fabio weave hdf5plugin*

    *   *sudo pip install pyFAI*

#.  Continue with step 2 and beyond from the :ref:`Ubuntu/Linux Mint instructions <lnxubuntu>`


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


Scientific Linux/Red Hat install from source instructions
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.. _lnxsl:

Tested on SL 6.8 and SL 7.3.

#.  Open a terminal and run the following commands:

    *   *su* (if necessary)

    *   *sudo yum update*

    *   *sudo yum install gcc-c++ python-devel*

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


Instructions for setting up a RAW desktop shortcut
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.. _lnxsrt:

All files referred to are initially located in the RAW **LinuxLib** folder.

#.  Add the **start_raw** file to your path:

    *   *sudo cp ~/raw/LinuxLib/start_raw /usr/local/bin*

#.  Make the start_raw file executable:

    *   *sudo chmod +x /usr/local/bin/start_raw*

#.  Copy the **RAW.desktop** file to the desktop:

    *   *cp ~/raw/LinuxLib/RAW.desktop ~/Desktop/*

#.   Right click on the **RAW** file on the desktop, and select Properties

#.  Click on the Permissions tab, and make sure “Allow executing file as program” is checked.

#.  Note: depending your distribution/shell, you have to edit the **start_raw**
    file to use a different shell. By default it uses bash.


Common problems/troubleshooting
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.. _lnxtrb:

*   On Scientific Linux 6, and thus probably on Red Hat 6 (untested), RAW completely fails
    to work with wxpython 3.0 and certain python distributions (namely the Enthought python).

    *   If RAW completely doesn’t start, check and make sure you have wxpython 2.8
        installed. This requires that you have matplotlib<=1.4.

    *   In general, RAW should work with wxpython 3.0.

*   Sometimes, compilers can have trouble if there are spaces in the filepath. Try
    installing RAW so that there are no spaces in the file path (navigate the folder
    in the terminal, type *pwd* and see what the result is).

*   The Enthought Canopy python package DOESN’T WORK on Ubuntu or Linux Mint with wxpython.

    *   We haven’t tested the Anaconda python package. It might work. If you use it
        successfully, let us know!

*   If you have installed a standalone python distribution (such as Enthought Canopy or
    miniconda/anaconda), it is possible that it isn’t set to default, so when you run
    *python RAW.py*, you are using the wrong python.

    *   You can verify which python you are using the command *which python* in the terminal.

    *   You can set the correct python to default by modifying your appropriate profile
        file (such as the .bash_profile), or setting the $PATH environmental variable.

    *   You can also specify the full path to the version of python you want to use in
        the command, such as *~/miniconda2/bin/python*

*   In some cases it is necessary to run RAW as an administrator, in order to compile
    (we’ve observed this on Scientific Linux 6). If RAW runs but doesn’t compile, and
    you’re sure you’ve got the gcc c++ compiler installed, try running it using *sudo*.

    *   Warning: the python used for *sudo* may not be the python for the regular user
        (particularly if you *su* and then *sudo*).

*   Note that when you change environmental variables in one terminal window, you need to
    restart other windows for this to take effect. If you aren’t using the right python
    (or compiler, etc), trying closing all of your terminal windows and opening a new one.
