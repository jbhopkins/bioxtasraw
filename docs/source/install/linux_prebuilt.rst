Using a prebuilt .deb package
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.. _linuxprebuilt:

The recommended way to install RAW on Linux is using a prebuilt .deb package. To install
from a prebuilt app package for Ubuntu 22.04/Debian 12 or newer:

#.  Download the :file:`RAW-x.y.z_linux_x86_64.deb`
    (where :file:`x.y.z` is the version number) file from sourceforge:

    *   `Download Ubuntu/Debian installer
        <https://sourceforge.net/projects/bioxtasraw/files/RAW-2.4.1_linux_x86_64.deb/download>`_

#.  Open a terminal and navigate to where you saved the downloads (usually: ``cd ~/Downloads``)

#.  Run the following command to install, replacing the version number with the correct version:

    *   ``sudo dpkg --install RAW-x.y.z_linux_x86_64.deb``

#.  You may now run RAW either by:

    #.  Using the command ``bioxtas-raw`` from the command line

    #.  Opening the 'BioXTAS RAW' program from your Activities menu or similar.


Note: if you wish to uninstall a version of RAW installed this way, simply use
the following command: ``sudo apt-get remove bioxtas-raw``

Alternatively, RAW is available as a standard debian package:
`https://tracker.debian.org/pkg/bioxtasraw <https://tracker.debian.org/pkg/bioxtasraw>`_.
So you can use that. However, the RAW developers do not maintain this version
and cannot guarantee functionality or how up to date it is.
