Using a prebuilt .deb package
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.. _linuxprebuilt:

The recommended way to install RAW on Linux is using a prebuilt .deb package. To install
from a prebuilt app package:

#.  Download the :file:`RAW-x.y.z-linux-amd64.deb`
    (where :file:`x.y.z` is the version number) file from sourceforge:

    *   `https://sourceforge.net/projects/bioxtasraw <https://sourceforge.net/projects/bioxtasraw>`_

    .. raw:: html

        <a href="https://sourceforge.net/projects/bioxtasraw/files/latest/download"><img alt="Download BioXTAS RAW" src="https://a.fsdn.com/con/app/sf-download-button" width=276 height=48 srcset="https://a.fsdn.com/con/app/sf-download-button?button_size=2x 2x"></a>

    *   Be sure to save the file, rather than opening it with a program.

#.  Open a terminal and navigate to where you saved the downloads (usually: ``cd ~/Downloads``)

#.  Run the following command to install, replacing the version number with the correct version:

    *   ``sudo dpkg --install RAW-x.y.z-linux-amd64.deb``

#.  You may now run RAW either by:

    #.  Using the command ``bioxtas-raw`` from the command line

    #.  Opening the 'BioXTAS RAW' program from your Activities menu or similar.


Note: if you wish to uninstall a version of RAW installed this way, simply use
the following command: ``sudo apt-get remove bioxtas-raw``
