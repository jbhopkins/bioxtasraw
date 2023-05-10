General instructions for installing from source (advanced users)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.. _lnxgen:

#.  Install python 3.X (if it isn’t already installed), RAW is tested on 3.7 and 3.8.

#.  Install python3 development tools and gcc (if they are not already installed).

#.  Install the following python packages (version indicated if less than most recent):

    *   numpy

    *   scipy

    *   matplotlib

    *   pillow

    *   wxpython

    *   h5py

    *   cython

    *   fabio

    *   pyFAI

    *   hdf5plugin

    *   numba

    *   dbus-python

    *   reportlab

    *   mmcif_pdbx

    *   svglib

#.  Download RAW source code from sourceforge (
    `https://sourceforge.net/projects/bioxtasraw/files <https://sourceforge.net/projects/bioxtasraw/files>`_)

#.  Extract RAW to a directory of your choice.

#.  In the top level RAW directory run ``python setup.py build_ext --inplace``
    to build the extensions.

#.  In the :file:`bioxtasraw` subdirectory run :file:`RAW.py` using python.

#.  Enjoy!

    *   If you have problems, please consult the detailed installation guides and check
        out the :ref:`solutions to common problems <lnxtrb>`.

    *   If you want, see the section on :ref:`making a desktop shortcut for RAW <lnxsrt>`.


Notes for python 2 installation
*********************************

As of version 2.0.0, RAW is Python 3 compatible. The last guaranteed Python 2
compatible version of RAW is 2.0.0. However, it may still be possible to install
RAW for Python 2. A few additional notes for that:

#.  Additional dependencies:

    *   future

#.  Required version of pyFAI is 0.17
