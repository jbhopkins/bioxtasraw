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
