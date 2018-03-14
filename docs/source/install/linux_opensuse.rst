OpenSUSE install from source instructions
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.. _lnxopensuse:

Tested on OpenSUSE Leap 42.3.

First install the g++ compiler:

#.  Open a terminal (:menuselection:`Application Menu --> System --> Konsole`)
    and run the following commands (hit enter/return to execute each command):

    *   ``su`` (if necessary)
    *   ``sudo zypper update``
    *   ``sudo zypper install gcc-c++``


Then install python and RAW:

.. include:: linux_miniconda.rst
