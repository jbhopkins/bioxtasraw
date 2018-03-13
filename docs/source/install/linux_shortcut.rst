Instructions for setting up a RAW desktop shortcut
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.. _lnxsrt:

All files referred to are initially located in the RAW **LinuxLib** folder.

#.  Add the **start_raw** file to your path:

    *   *sudo cp ~/raw/LinuxLib/start_raw /usr/local/bin*

#.  Make the start_raw file executable:

    *   *sudo chmod +x /usr/local/bin/start_raw*

#.  Copy the **RAW.desktop** file to the desktop:

    *   *cp ~/raw/LinuxLib/RAW.desktop ~/Desktop/*

#.   Right click on the **RAW** file on the desktop, and select Properties

#.  Click on the Permissions tab, and make sure “Allow executing file as program” is checked.

#.  Note: depending your distribution/shell, you have to edit the **start_raw**
    file to use a different shell. By default it uses bash.
