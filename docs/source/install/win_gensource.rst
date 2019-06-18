General instructions for installing from source (advanced users)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.. _wingen:

#.  Install Microsoft Visual C++ 2008 Redistributable and Visual C++ Compiler for
    Python.

#.  Install Python 2.7 (if it isn’t already installed) and add it to your system path.

#.  Install the following Python packages (version indicated if less than most recent):

    *   numpy

    *   scipy

    *   matplotlib

    *   pillow

    *   wxpython

    *   lxml

    *   h5py

    *   cython

    *   fabio

    *   pyFAI < 0.16

    *   hdf5plugin

    *   numba < 0.44

#.  Download the RAW source file (:file:`RAW-{x}.{y}.{z}-Source` where :file:`{x}.{y}.{z}` is the version number)
    from sourceforge (
    `http://sourceforge.net/projects/bioxtasraw <http://sourceforge.net/projects/bioxtasraw>`_)

#.  Extract RAW to a directory of your choice.

#.  In the top level RAW directory run ``python setup.py build_ext --inplace``
    to build the extensions.

#.  In the :file:`bioxtasraw` subdirectory run :file:`RAW.py` using python.

#.  Enjoy!

    *   If you have problems, please consult the detailed installation guides and the
        :ref:`solutions to common problems <wintrb>` below. If that doesn’t help,
        please contact the developers.
