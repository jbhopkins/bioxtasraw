General instructions for installing from source (advanced users)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.. _macgen:

#.  Install a standalone version of python 3.7 (recommended, not required).

#.  Install the following python packages (most recent version of each recommended):

    *   numpy

    *   scipy

    *   matplotlib < 3.2

    *   pillow

    *   wxpython < 4.1

    *   h5py

    *   cython

    *   fabio

    *   pyFAI

    *   hdf5plugin

    *   numba

#.  Download the latest RAW sourcecode from sourceforge (
    `https://sourceforge.net/projects/bioxtasraw <https://sourceforge.net/projects/bioxtasraw>`_)

#.  Extract RAW to a directory of your choice.

#.  In the top level RAW directory run ``python setup.py build_ext --inplace``
    to build the extensions.

#.  In the :file:`bioxtasraw` subdirectory run :file:`RAW.py` using python.

#.  Enjoy!

    *   If you have problems, please consult the detailed installation guide and the
        :ref:`solutions to common problems <mactrb>` below. If that doesn’t help,
        please contact the developers.


Notes for python 2 installation
*********************************

As of version 2.0.0, RAW is Python 3 compatible. The last guaranteed Python 2
compatible version of RAW is 2.0.0. However, it may still be possible to install
RAW for Python 2. A few additional notes for that:

#.  Additional dependencies:

    *   future

#.  Required version of pyFAI is 0.17
