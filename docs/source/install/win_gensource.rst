General instructions for installing from source (advanced users)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.. _wingen:

#.  Install Microsoft Visual C++ 14.2 Standalone: Build Tools for Visual Studio 2019

#.  Install Python 3.X (if it isn’t already installed) and add it to your system
    path (tested on 3.7 and 3.8).

#.  Install the following Python packages (version indicated if less than most recent):

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

    *   reportlab

#.  Download the RAW source file (:file:`RAW-{x}.{y}.{z}-Source` where :file:`{x}.{y}.{z}` is the version number)
    from sourceforge (
    `https://sourceforge.net/projects/bioxtasraw <https://sourceforge.net/projects/bioxtasraw>`_)

#.  Extract RAW to a directory of your choice.

#.  In the top level RAW directory run ``python setup.py build_ext --inplace``
    to build the extensions.

#.  In the :file:`bioxtasraw` subdirectory run :file:`RAW.py` using python.

#.  Enjoy!

    *   If you have problems, please consult the detailed installation guides and the
        :ref:`solutions to common problems <wintrb>` below. If that doesn’t help,
        please contact the developers.


Notes for python 2 installation
*********************************

As of version 2.0.0, RAW is Python 3 compatible. The last guaranteed Python 2
compatible version of RAW is 2.0.0. However, it may still be possible to install
RAW for Python 2. A few additional notes for that:


#.  Install Microsoft Visual C++ 2008 Redistributable and Visual C++ Compiler for
    Python.

#.  Install Python 2.7

#.  Additional dependencies:

    *   future

#.  Required version of pyFAI is 0.17
