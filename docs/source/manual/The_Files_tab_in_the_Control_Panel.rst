The Files tab in the Control Panel
===================================

**WARNING:** The manual is current several versions out of date. While it may
still be useful for some users, please refer to the tutorial for the most
up-to-date information.

.. _filepanel:

Changing file directories
-------------------------

There are three ways to change the directory whose contents are displayed in the Files tab:

*   Click on the folder icon next to the bar to open a directory window. This allows you to
    select the directory you want to display.

*   Type a path into the bar at the top of the Files tab and hit enter to go to a directory.

*   Double click the up arrow in the File list (blue arrow with a filename of ‘..’) to navigate
    up a directory level. Double click on any displayed directory to open it and show the contents
    in the Files tab.

**Note:** The Files tab simply displays the files in your system. None of these files are loaded into
RAW until you take some action on them (for example, :ref:`plotting them <plotfiles>`)


Updating the file list
----------------------

The file list in the Files tab does not automatically update when new files are placed in the folder.
In order to update the file list to show new files, you must click the Refresh button (two green arrows
in a circle) to the right of the Folder button near the top right of the Files tab.


Plotting files
--------------

.. _plotfiles:

Plotting is done from the Files tab in the Control Panel. It can be done in two ways:

#.  Simply double-click an image, compatible ASCII file, or RAW sec file to plot it.

#.  Select one or more files to be plotted at the same time and click the “Plot” button

The Calibration, Normalization, Masking, and other Advanced Options will be used to convert
images into one dimensional scattering profiles when an image is selected and plotted. The
Normalization settings, including absolute scale factor, counter norms, and solid angle
correction status, the configuration file used, and the image load path are saved as part
of the manipulation history for a scattering profile in RAW created from an image.

**Note 1:** Selecting files is as simple as left clicking on them. Multiple files can be
selected by shift or ctrl (command on OS X) left clicking on the files.

**Note 2:** Some image files can only be loaded if the image type in the Advanced Options
is set appropriately.


Filtering and searching the file list
-------------------------------------

Below the file list is a filter/search bar. You can either select filters
from a list or create your own using wildcard characters. The filter bar accepts ‘\*’ as a wildcard
matching any number of characters and ‘?’ as a wildcard matching a single character.

Examples:

*   If you were looking for all files with ‘BSA’ anywhere in the filename you would write: \*BSA\*
    in the filter/search bar. The two \* wildcard matches any characters before and after the ‘BSA’.

*   If you wanted all files with ‘BSA’ at the start of the filename you would write BSA\*
    in the filter/search bar. The single \* wildcard will match any characters after the ‘BSA’.

*   If you wanted all of the files with ‘BSA’ at the start of the filename and ‘.tiff’ at the end of
    the filename you would write **BSA\*.tiff**. The single \* wildcard will match any characters
    between BSA and .tiff in the filename.

*   If you wanted all of the files with ‘BSA_000x.tiff’ where x is a single character, you would write
    **BSA_000?.tiff**. The ? wildcard will match any single alphanumeric character in that position.


Sorting the file list
---------------------

The columns at the top of the file list, Name, Ext, Modified and Size, show the file name, the
file extension, the file modified time, and the file size respectively. By clicking on the column
heading, you can sort the file list by those attributes. By default, the file list is sorted by
name, ascending (low to high, A to Z). This is indicated by the upward pointing green arrow in the
Name column heading. Clicking on the Name column heading will switch the order of the sort to
descending (high to low, Z to A) sort. Clicking again will return it to the ascending sort. Clicking
on another column heading will sort the file list by that column, and again can be switched between
ascending and descending.


Files tab buttons
-----------------

Quick reduce
~~~~~~~~~~~~

Processes selected images and save them to ASCII files without plotting the scattering profiles using
the integration parameters (calibration, masking, etc) current set in RAW.


System Viewer
~~~~~~~~~~~~~

Attempts to open/run the selected file using whatever software is set up in the operating system to
handle the file format. You can use the 'E' keyboard key as a shortcut.


Plot
~~~~

This plots the selected files in RAW, assuming the formats can be read by RAW. If the files are
images, they will be integrated into one dimensional scattering profiles using the integration
parameters (calibration, masking, etc) set in RAW. Files are shown in the following locations:

*   Images (which RAW integrates) and 1D scattering profiles (typically “.dat” files) opened by
    RAW display in the Main Plot tab of the Plot panel. The Manipulation panel shows the items
    in the Main Plot and lets change and process the curves individually.

*   IFT files (.out and .ift extensions) are loaded into the IFT Plot Panel of RAW. The IFT panel
    in the Control Panel shows the items in the IFT Plot and lets you change and process the curves
    individually.

*   SEC files (.sec extensions) are loaded into the SEC Plot Panel of RAW. The SEC panel in the Control
    Panel shows the items in the SEC plot and lets you change and process the curves individually.

**Note:** If a file has previously been saved from RAW, all of the saved information (see later sections)
will be loaded when the file is reloaded. For example, if a subtracted scattering profile had a Guinier
analysis performed on it and was saved as a “.dat” file, when that saved file is loaded back into RAW,
the Rg and I(0) values will be loaded as well.


Show image
~~~~~~~~~~

.. _showimage:

Shows the image selected in the file list in RAW’s image plot. You can use the 'S' keyboard key as a
shortcut.

**Note:** If multiple files are selected, the image shown is from the first file in the list.


Clear all
~~~~~~~~~

Resets and clears all plots and also clears the item lists in the Manipulation, IFT, and SEC tab.


Plot SEC
~~~~~~~~

The “Plot SEC” button plots the selected images and/or 1D scattering profiles as a
:ref:`SEC curve <secplot>`. The images are integrated into 1D scattering profiles.

**Note:** This button can also be used to plot files with the .sec extension that have previously been
saved by RAW.


Manipulating files and folders
------------------------------

Files and folders can be manipulated in the Files tab by right clicking on a filename in the file list.
The pop-up menu has the options to create a new folder, rename a file, copy/cut/paste file(s) or delete
file(s).

**Note:** These options change the files on disk, not just in RAW! So if you delete a file here, it
will be deleted from your disk. If you want to work with the files you have loaded into RAW, see the
sections on the :ref:`Manipulation <manippanel>`, :ref:`IFT <iftpanel>`, and
:ref:`SEC Control Panels <secplot>`.

