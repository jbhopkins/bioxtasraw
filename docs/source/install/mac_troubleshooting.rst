Common problems/troubleshooting
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.. _mactrb:

**Installing the prebuilt app package:**

*   Because the RAW team is an unidentified developer, you may get a warning message the
    first time you run the program. If that happens, right click on RAW and select :menuselection:`Open`
    from the right click menu, and then click the :guilabel:`Open` button in the window that appears.

    *   This requires administrator privileges

*   If the above doesn’t work, you can run the RAW app from the command line. Navigate to
    :file:`RAW.app/Contents/MacOS` and run the RAW unix executable file (:file:`./RAW`) in that directory.


**Installing from source:**

*   The compiler can fail if there are any spaces in the directory paths. Make sure that the
    :file:`RAW.py` file is installed in a directory path without any spaces.

*   If the extensions won’t compile properly (you’ll get a popup message when you start
    RAW warning you of this), try copying the appropriate precompiled extensions (:file:`.so`
    files) from the :file:`MacLib` folder into the main :file:`raw` folder.

*   The shortcut can fail if you didn’t install raw in the recommended location. If that’s
    the case, go through the process of creating a new shortcut, and make sure you change
    the line in the script mentioned in that section.

*   Because of some weirdness with the anaconda/miniconda framework pythonw, it can't run
    EMAN2. Every other variant I've tried (enthought and homebrew) have been fine.
