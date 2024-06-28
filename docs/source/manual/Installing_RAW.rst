Installing RAW
==============

**WARNING:** The manual is current several versions out of date. While it may
still be useful for some users, please refer to the tutorial for the most
up-to-date information.

This chapter provides an overview of how to install RAW on Windows, Linux and Macintosh. Detailed installation guides for each system are available separately. It covers:

*   Licensing

*   System requirements

*   Installing from source code.

*   Installing from pre-compiled binaries.

*   Obtaining the newest version of RAW


Licensing
---------

RAW is open source software, which means the source code is freely available and
can be modified/extended as the experienced users sees fit. RAW is available under
the GPL V3 license which means that if a modified version of RAW, or any software
that uses any of the code available in RAW, is made available to users, then the
full source code must also be made available. For a full description of the GPL
licensing terms, see the file gpl-3.0.txt included with the RAW source code, or visit
`https://www.gnu.org/licenses/gpl-3.0.html <https://www.gnu.org/licenses/gpl-3.0.html>`_


System requirements
-------------------

The faster the machine the better the experience.

*Minimum Requirements*

1.6 GHz 32 bit (x86) Computer

1 GB of memory

1024x768 resolution display

Windows 7 or newer, Mac OSX 10.9 or newer, Linux

Note: The newest version of RAW may run on Windows XP or Vista and OS X 10.4+,
but it has not been tested by the developers on these older systems.


*Optimal Requirements*

2.5+ GHz 32/64 bit (x86) Dual/Quad Core Computer

2+ GB of memory

1280x1024+ resolution display

Windows 7 or newer, Mac OSX 10.9 or newer, Linux


Installing RAW from pre-compiled binaries
-----------------------------------------

A prebuilt installer is available for RAW for Windows and Mac. We recommend that most
users install the prebuilt versions. The windows installer has  been tested on Windows 7,
8.1, and 10. It may also work for older versions. The Mac installer has been tested on
macOS/OS X 10.9 - 10.12. It may also work for older versions.


Instructions for prebuilt installers are available here:

* :ref:`Windows <winprebuilt>`

* :ref:`Mac <macprebuilt>`


Installing RAW from source code
-------------------------------

Installing RAW from source code takes more work but has the advantage that
the newest version can always be downloaded and quickly installed once the
necessary tools have been installed. Installing a pre-compiled version of
RAW is easier, but compiled versions are not updated as often as the source
code due to the time consuming process of making a compiled executable.
Compiled versions may also only be available for certain platforms.


Instructions for install RAW from source are available for

* :ref:`Windows <winsource>`

* :ref:`Mac <macsource>`

* :ref:`Linux <lnxsource>`


**NOTE:** As of writing, the RAW is **only** compatible with Python version 2.7
and not the newer 3.x versions.


Obtaining the newest version of RAW
-----------------------------------

The newest version of RAW can always be found on Sourceforge. The released source code and compiled binaries can be downloaded at:

`https://sourceforge.net/projects/bioxtasraw/files/ <https://sourceforge.net/projects/bioxtasraw/files/>`_


To obtain the very latest unreleased version (that might or might not be stable) go to:
`https://sourceforge.net/p/bioxtasraw/code/HEAD/tree/trunk/src/ <https://sourceforge.net/p/bioxtasraw/code/HEAD/tree/trunk/src/>`_

And click “Download Snapshot" near the top of the screen. Unpack the content into a folder
and run RAW.py as usual.


**NOTE:** When installing new source code on top of old it is important to delete the old source code, including the compiled C libraries with the extensions .so, .pyc, and .pyd, otherwise RAW could be loading old code and become unstable.


Integrating ATSAS with RAW
---------------------------

.. _atsas:

RAW allows you to do analysis with some of the programs from the ATSAS
package directly from RAW. Currently, you can use GNOM, DAMMIF, and AMBIMETER
in RAW. This requires a separate ATSAS installation, as the RAW developers
are not allowed to distribute the ATSAS package with RAW.


Installing the ATSAS package
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The ATSAS package is available from EMBL, and can be downloaded here:

`https://github.com/biosaxs-com/atsas-community <https://github.com/biosaxs-com/atsas-community>`_

Installation instructions are available here:

`https://biosaxs-com.github.io/atsas/4.0.0/install/ <https://biosaxs-com.github.io/atsas/4.0.0/install/>`_

We recommend installing the packages in the default installation location.

To use all of the programs through RAW, you need ATSAS version 2.7.1 or greater.
GNOM and DAMMIF may work for earlier versions of the ATSAS package, but the RAW
developers have not tested this.


Locating the ATSAS package for RAW
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

RAW will attempt to automatically locate the ATSAS package when you start up RAW
(and when you load a configuration file). It may fail to do this, in which case
you will need to set the location of the ATSAS programs manually. To do this:

*   Open the “ATSAS” section of the Options window.

*   Uncheck the “Automatically find the ATSAS bin location”

*   Either by typing the path or using the “Select Directory” button,
    select the “bin” folder inside the main ATSAS folder. This folder should
    have a dammif executable inside of it.


Running without compiled extensions
------------------------------------

RAW compiles certain extensions that are written in C++ in order to maximize
the speed of the program. These extensions are involved in the following tasks:
Making polygon masks, integrating images into scattering profiles, and carrying
out the BIFT analysis. All of these extensions are also available in native
python code, but run much more slowly. If RAW is unable to compile these extensions,
a warning message will display when the program is started.

While RAW is able to run without the extensions compiled, it will significantly
impact performance of the listed tasks. We recommend troubleshooting the RAW
installation, or reinstalling RAW to get these to compile. The RAW installation
guides contain detailed install instructions and some solutions to common problems
with the installation. Please refer to those for more details.
