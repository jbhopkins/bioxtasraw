Instructions for setting up a RAW desktop shortcut from source
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.. _lnxsrt:

All files referred to are initially located in the RAW :file:`LinuxLib` folder.

#.  Add the :file:`start_raw` file to your path:

    *   ``sudo cp ~/raw/LinuxLib/start_raw /usr/local/bin``

#.  Make the :file:`start_raw` file executable:

    *   ``sudo chmod +x /usr/local/bin/start_raw``

#.  Copy the :file:`RAW.desktop` file to the desktop:

    *   ``cp ~/raw/LinuxLib/RAW.desktop ~/Desktop/``

#.   Right click on the :file:`RAW` file on the desktop, and select :menuselection:`Properties`

#.  Click on the Permissions tab, and make sure :guilabel:`Allow executing file as program` is checked.

#.  Note: depending your distribution/shell, you have to edit the :file:`start_raw`
    file to use a different shell. By default it uses bash.
