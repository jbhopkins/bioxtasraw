General instructions for installing from source (advanced users)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.. _wingen:

#.  Install the Microsoft Visual C++ compiler for Python 2.7

#.  Install Python 2.7 (if it isn’t already installed) and add it to your system path.

#.  Install a C compiler (such as the gcc c++ compiler) and add it to your system path.

#.  Install the following Python packages (version indicated if less than most recent):

    *   numpy

    *   matplotlib

    *   scipy

    *   pillow

    *   wxpython < 4.0

    *   fabio

    *   lxml

    *   h5py

    *   hdf5plugin

    *   pyFAI

    *   weave

#.  Download the RAW source file (:file:`RAW-{x}.{y}.{z}-Source` where :file:`{x}.{y}.{z}` is the version number)
    from sourceforge (
    `http://sourceforge.net/projects/bioxtasraw <http://sourceforge.net/projects/bioxtasraw>`_)

#. Extract RAW to a directory of your choice and run :file:`RAW.py` using python.

    *   Note: the first time you run :file:`RAW.py` it may need to be run from the command line
        in order to successfully compile various extensions. It may take some time to compile
        the extensions, be patient.

    *   After you run RAW for the first time, you can run it by double clicking the
        :file:`RAW.py` file, assuming :file:`.py` files are associated with your python executable.

#.  Enjoy!

    *   If you have problems, please consult the detailed installation guides and the
        :ref:`solutions to common problems <wintrb>` below. If that doesn’t help,
        please contact the developers.
