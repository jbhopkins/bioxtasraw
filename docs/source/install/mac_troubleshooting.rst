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

*   If you fail to build the extensions before running RAW, RAW will crash at some point.
    Be sure to run the ``python setup.py build_ext --inplace`` before starting RAW.

*   Using the RAW autorg function requires a relatively recent version of numba.
    If you get an error running this function update your numba version to the
    most recent.
