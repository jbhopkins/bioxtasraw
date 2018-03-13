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

    *   wxpython < 4.0

    *   fabio

    *   h5py

    *   lxml

    *   pyFAI

    *   hdf5plugin

    *   weave < 0.16

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
