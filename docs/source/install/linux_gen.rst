General instructions for installing from source (advanced users)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.. _lnxgen:

#.  Install python 2.7 (if it isn’t already installed).

#.  Install the following python packages (version indicated if less than most recent):

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

    *   numba

#.  Download RAW from sourceforge (
    `http://sourceforge.net/projects/bioxtasraw <http://sourceforge.net/projects/bioxtasraw>`_)

    .. raw:: html

        <a href="https://sourceforge.net/projects/bioxtasraw/files/latest/download"><img alt="Download BioXTAS RAW" src="https://a.fsdn.com/con/app/sf-download-button" width=276 height=48 srcset="https://a.fsdn.com/con/app/sf-download-button?button_size=2x 2x"></a>

#.  Extract RAW to a directory of your choice.

#.  In the top level RAW directory run ``python setup.py build_ext --inplace``
    to build the extensions.

#.  In the :file:`bioxtasraw` subdirectory run :file:`RAW.py` using python.

#.  Enjoy!

    *   If you have problems, please consult the detailed installation guides below and check
        out the :ref:`solutions to common problems <lnxtrb>`.

    *   If you want, see the section on :ref:`making a desktop shortcut for RAW <lnxsrt>`.
