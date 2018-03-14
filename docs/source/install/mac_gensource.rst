General instructions for installing from source (advanced users)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.. _macgen:

#.  Install a standalone version of python 2.7 (recommended, not required).

#.  Install a gcc c++ compiler (for example the Xcode command line tools) and add it to your system path.

#.  Install the following python packages (most recent version of each recommended):

    *   numpy

    *   scipy

    *   matplotlib

    *   pillow

    *   wxpython < 4.0

    *   fabio

    *   lxml

    *   h5py

    *   cython

    *   pyFAI

    *   hdf5plugin

    *   weave < 0.16

#.  Download the latest RAW sourcecode from sourceforge (
    `http://sourceforge.net/projects/bioxtasraw <http://sourceforge.net/projects/bioxtasraw>`_)

#.  Extract RAW to a directory of your choice and run :file:`RAW.py` using python.

    *   Note: the first time you run :file:`RAW.py` it may need to be run from the command line
        in order to successfully compile various extensions. It may take some time to
        compile the extensions, be patient.

#.  Enjoy!

    *   If you have problems, please consult the detailed installation guide and the
        :ref:`solutions to common problems <mactrb>` below. If that doesn’t help,
        please contact the developers.
