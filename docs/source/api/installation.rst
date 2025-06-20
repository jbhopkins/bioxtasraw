Installing the API
-------------------

Installation
^^^^^^^^^^^^

Users should proceed as if :ref:`installing RAW from source on their OS of
choice.<install>` If you are not going to use the RAW GUI from source,
then you do not need to install the wx package. Once you've installed all
required packages and downloaded and unpacked the source code, you then
proceed differently:

#.  Open a terminal window and cd into the top level source directory.

#.  Install the RAW API using pip with the command ``pip install .``

The RAW API is now installed and ready to use.


Using the RAW GUI from the installed package
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If you don't want to have RAW hanging around in several places, it is possible
to run the RAW GUI directly from the installed API package on most systems.
When you install the RAW package, it creates a bioxtas_raw script that
should be in the system path. You can simply run bioxtas_raw from the
command line and the RAW GUI should start.

Note: Does not work for older versions of conda on MacOS due to the need
to use the pythonw command to run GUI programs. Works on modern versions
of conda.
