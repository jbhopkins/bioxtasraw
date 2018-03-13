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
