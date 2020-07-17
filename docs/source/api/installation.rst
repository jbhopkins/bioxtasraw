Installing the API
-------------------

Installation
^^^^^^^^^^^^

Users should proceed as if installing RAW from source on their OS of choice.
If you are not going to use the RAW GUI from source, then you do not need
to install the wx package. Once you've installed all required packages and
downloaded and unpacked the source code, you then proceed differently:

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

The only catch to this is, that on MacOS using the anaconda python distribution,
that doesn't work. This has to do with the fact that using the anaconda python
you have to run GUI programs as pythonw, not python (on a deeper level this
is an issue with Framework builds of python), which can't be done for this
script.
