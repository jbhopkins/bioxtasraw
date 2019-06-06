The SEC Control Panel and SEC Plot Panel
========================================

**WARNING:** The manual is current several versions out of date. While it may
still be useful for some users, please refer to the tutorial for the most
up-to-date information.

.. _secplot:

When SEC-SAXS data is loaded into RAW, it is placed in the SEC tab of the Control
Panel, and displayed in the SEC Plot window. This section will cover the features
of the SEC control panel and the SEC plot panel.

SEC-SAXS data is assumed to come from continuous collection of images while sample is
being eluted from an FPLC column. Depending on the frame rate of the detector and the
total elution time, this can generate thousands of images. The basic approach RAW uses
to deal with this data is to load every scattering profile (or integrate every image
into a scattering profile), and associate it with a single SEC data item. For each SEC
item, the total (or average) intensity in each scattering profile is plotted vs. frame
number, where frame number is simply what position the item was loaded in (so if 10 items
are loaded, the frame number for the first item loaded would be 0, for the next item loaded
1, etc). For standard SEC-SAXS data, this intensity vs. frame number should look similar to
the UV chromatograph of the sample after it passes through the column. Some analysis can be
carried out directly on this SEC data item, and the scattering profiles of interest can be
extracted for further analysis.


The SEC control panel
---------------------

The SEC control panel refers to the panel that is shown in the Control panel when the SEC
tab is selected.

The panel consists of three parts. The top part is a set of controls for loading SEC items,
controlling the SEC online mode, and analyzing SEC items. The middle part is where individual
SEC items loaded into RAW are shown. The bottom part consists of buttons that allow you to
save or remove the SEC items. Further manipulation of the SEC items can be done from the right
click (context) menu.

An individual item in the SEC list is the called a SEC data item. It is associated with two
curves on the SEC plot, one plotted on the right y axis and one on the left y axis.


SEC Data Items
~~~~~~~~~~~~~~

When a new item is plotted, a data item is added to the SEC list in the SEC control panel. This
allows you to control the properties of the data item, and perform analysis on it.

The name of the data item is displayed for each item. If an item is given a different name for the
plot legend, this legend name is displayed in [square brackets] next to the item name. On the same
line as the item name, on the right side of the data item, there are several buttons that can be
used for further manipulation of the data item.

SEC data items are different from Manipulation and IFT data items as they have many (often hundreds
or thousands) of scattering profiles associated with a single data item, and they can have new
profiles appended to them after they are loaded.

**Note:** If there is a \* to the left of the item name (between the checkbox and the item name),
it indicates there are unsaved changes to the item. This can occur if the item is newly created IFT
data (such as from the BIFT or GNOM panels), or if item properties such as the name have been changed.


Showing/Hiding data items on the SEC plot
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To show/hide the curves on the plot associated with a data item, click the checkbox next to the
filename. If the checkbox is checked, the item is currently shown on the SEC plot, if the checkbox
is unchecked, the item is currently hidden on the SEC plot.


Data item buttons
~~~~~~~~~~~~~~~~~

On the right of the data item are several buttons for controlling the data item. In order of left
to right, these buttons have the following properties.

*Extended Info*

By hovering the mouse over the i in the blue circle button, a tooltip will appear which shows more
information about the item. It shows the buffer range and window size used (if any) to calculate the
structural parameters of the SEC data item as a function of frame number.

*Locate Line*

The target button is used to highlight the scattering profile on the graph that is associated
with the data item. When the target is pressed, it ‘bolds’ the line each plotted curve associated
with the data item (increases the line width by several points). When the target is pressed again,
the line width is set back to normal. You can tell if a line is currently bolded, as the target will
be orange instead of grey.

*Line Properties*

The colored line button has two purposes. First, the color matches the current color of the Intensity
curve in the SEC Plot. Second, when pressed it opens a :ref:`line properties dialog <lineproperties>`
which allows you to set the legend label; the line style, width, and color; the data point
marker style, size, line color, and fill color; and the error bar line style, width, and
color for each line associated with the SEC data item.

*Mark*

The star button marks an item. This is used when doing operations such as sending data frames to plot
or calculating structural parameters. In those cases, the marked (also referred to as starred) item
has a special significance.


Loading data items
~~~~~~~~~~~~~~~~~~

SEC data items can be loaded from the :ref:`files tab <filepanel>`. There is an additional way
to load files available in the SEC control panel, this method is intended to be used in
conjunction with the SEC online mode. This method is described in the rest of this section.

At the top of the SEC control panel, there is a section for loading files. It has a button
“Select file in SEC run”, and then descriptive information about the file: the image prefix,
the run number, and the frame numbers of the file. Note that none of these descriptive fields
can be edited. Below the descriptive fields is an “Update” button and an “Automatically Update”
checkbox.

To load a SEC curve using this method, click the “Select file in SEC run” button. In the file
browser that pops up, select any file in the SEC data set. The data set will automatically be
loaded into RAW as a SEC item, and the descriptive information will be displayed in the appropriate
boxes. This loaded file can then be used with the SEC automatic update mode described
:ref:`below <secautoupdate>`.

**Note:** Due to how files are loaded from the SEC control panel, it only works for certain header
file types. RAW must be able to automatically determine what files are associated with the SEC run,
from any file in the run. At the moment, this can only be done with the G1 and G1 WAXS header file
formats. If you want to have a particular beamline’s file format added to this loading (and thus able
to use the online mode) please contact the RAW developers.


Updating a SEC data item
~~~~~~~~~~~~~~~~~~~~~~~~

If a SEC data item is loaded via the SEC control panel, it can be updated if additional files are
added to the folder that are part of the data collection. This can only be done for the most recent
file loaded via the SEC control panel, for which the descriptive information is shown at the top of
the SEC control panel.

To do this update, hit the “Update” button on the SEC control panel. RAW will automatically determine
all of the files associated with the SEC run, based on the file you selected with the “Select file
in SEC run” button, determine if any of those files have not yet been loaded, and if so,
load the files and add them to the SEC item as appropriate.

This is useful when working at the beamline while data is being collected, as you may want
to start analysis of the SEC curve before all of the images are taken.


SEC automatic update (online mode)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. _secautoupdate:

The SEC control panel can be used in an online mode, where a SEC curve is automatically
updated as data comes in. All of the conditions for manually updating a curve, described above,
must be met. Instead of using the “Update” button as in that section, check the “Automatically
Update” box in the SEC control panel.

**Note:** The automatic update will stay on even if you load a new file into the
SEC panel using the “Select file in SEC run” button. It will switch to updating
this newly loaded file. As with the “Update” button described above, the automatic
update only applies to the SEC data item most recently loaded in the SEC panel.


Selecting data items
~~~~~~~~~~~~~~~~~~~~

A single data item can be selected by clicking on the item name in the SEC list
(similar to how you would select files in your system file browser). When an item
is selected, the color of the item background changes from white to gray. If the
item is currently selected, clicking on it will cause it to be unselected. Note
that for a regular click, all other selected items will be unselected when a new
item is selected.

Multiple items may be selected in two ways. If the Control key (Command key on Macs)
is held down while clicking on items, each item that is clicked on will be added to the
set of selected items. If a single item is first selected and then the Shift key is held
down and another item is selected, all of the items in the list between the two items will
be selected (including the second item that is clicked on).

All of the items in the list can be selected in two ways. The first is using the
:ref:`select all <iftselectall>` button, the second is pressing Ctrl-A (Cmd-A), the Control
(Command) key and the A key at the same time when you are in the SEC panel. All items
can be unselected by clicking in an empty spot of the SEC list (but not above or below
the list), or by clicking on an already selected item.

**Note:** If you have a set of selected items and wish to remove some, holding down the
Control (Command) key and clicking on selected items will deselect them without affecting
the other selected items.


The top buttons of the SEC item list
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The SEC item list has a set of three buttons at the top of the panel. These buttons have
the following effects, listed from left to right.

*Show All*

Clicking on the button that looks like an eye will show all SEC items. This is the same as
if you manually set all of the show/hide checkboxes in the data items to on.

*Hide All*

Clicking on the button that looks like an eye with a red x through it will hide all SEC
items. This is the same as if you manually set all of the show/hide checkboxes in the data
items to off.

*Select All*

Clicking on the button that looks like a spreadsheet with selected cells will select all
of the SEC data items.


Renaming a data item
~~~~~~~~~~~~~~~~~~~~

Data items can be renamed by selecting the data item of interest and selecting “Rename” in
the right click popup menu.

**Note:** While no characters are expressly forbidden in the filename, RAW does not sanitize
file names before saving, and thus special characters such as ‘/’ and ‘\\’ are likely to cause
problems when the file is saved.


Saving data items
~~~~~~~~~~~~~~~~~

.. _savingsecdata:

SEC items are saved as “.sec” files, and is the only data that RAW does not save in a human
readable format. To save:

#.  Select the item(s) to be saved.

#.  Click the “Save” button or select “Save selected file(s)” from the right click menu.

#.  In the window that pops up, navigate to the directory in which you want to save the files.

#.  If you are saving a single item, the window will give you an opportunity to rename your
    file if desired. Click “Save” when ready.

#.  If you are saving multiple items, you simply need to select the folder for the items to
    be saved in, and click “Open”. The items will be saved with the same names displayed in
    the SEC Panel, in the folder that you chose.

SEC items often contain hundreds or thousands of scattering profiles, so they are not saved in a
human readable format. The “.sec” files that RAW saves can only be read by RAW.


Removing data items from the SEC list
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To remove one or more data items, select them and do one of the following:

#.  Press the “Delete” key on the keyboard

#.  Click the “Remove” button

#.  Select “Remove” from the right click menu


Exporting SEC data
~~~~~~~~~~~~~~~~~~

The following data can be exported in a spreadsheet ready format: frame number,
integrated intensity, mean intensity, Rg, Rg error, I(0), I(0) error, MW, filename,
and, if available intensity a q=<#> where <#> is a user selected value, for each individual
point.

To do so:

#.  Select the item(s) to be saved.

#.  Select “Export data” from the right click menu.

#.  In the window that pops up, navigate to the directory in which you want to save the file(s).

#.  If you are saving a single item, the window will give you an opportunity to rename your
    file if desired. Click “Save” when ready.

#.  If you are saving multiple items, you simply need to select the folder for the items to be
    saved in, and click “Open”. The items will be saved with the same names displayed in the SEC
    Panel, in the folder that you chose.

The data is saved as a comma separated value (“.csv”) file. This can be opened directly into most
spreadsheet programs, such as Excel.


Saving all SEC scattering profiles
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you want to save every individual scattering profile loaded into a SEC data item, you can do so by:

#.  Select the item(s) to be saved.

#.  Select “Save all profiles as .dats” from the right click menu.

#.  In the window that pops up, navigate to the directory in which you want to save the file(s).

#.  Select the folder for the items to be saved in, and click “Open”. The items will be saved with
    the same filenames displayed in the :ref:`data browser <secdatadialog>`.


Sending data to the main plot
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Individual scattering profiles can be sent to the main plot for further analysis. This utilizes the
middle section of the controls at the top of the SEC Control panel.

To do so:

#.  Star the SEC data item containing the scattering profiles of interest (note: if only
    one SEC data item is loaded, it does not have to be starred).

#.  Enter the data frames of interest in the “Select Data Frames:” boxes. The box on the
    left is the first frame of interest, the box on the right is the last frame of interest.
    All of the frames between those two endpoints (inclusively) are selected.

#.  Either click the “Frames To Main Plot” button, which will send each individual frame selected
    in part 2 to the Main plot, or click “Average To Main Plot” which will send the average of the
    selected frames to the Main plot.

#.  Click on the Manipulation panel and Main plot panel to view the scattering profiles.


Calculate structural parameters
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. _secparams:

You can calculate the Rg, MW, and I(0) as a function of frame number for a SEC
profile. This is done using the “Calculate/Plot Structural Parameters” section
of the SEC control panel (the bottom section of the controls at the top of the panel).

It is important to have a big picture for what is happening when this is done. First
you set a buffer range. All of the scattering profiles in that range will be averaged,
and then subtracted from every loaded scattering profile. Next you set a window size.
This window will be slid across the curve and all of the frames within it averaged
(note: this average is of the buffer subtracted scattering profiles). This Rg, MW, and
I(0) for this averaged profile is then calculated. Those values are assigned to the center
frame of the window. The window is then slid down the curve one frame, and the process is
repeated until the window reaches the end of the SEC data. For example, if the window size
is 5, the first 5 frames, frames 0, 1, 2, 3, and 4, are averaged, and have the Rg, MW, and
I(0) calculated. Then window is moved over by one, and frames 1, 2, 3, 4, and 5 are averaged
and have the Rg, MW, and I(0) calculated, and so on.

To do this:

#.  Star the SEC data item containing the scattering profiles of interest (note:
    if only one SEC data item is loaded, it does not have to be starred).

#.  Enter the buffer range in the “Buffer Range” boxes. The box on the left is the
    starting buffer frame and the box on the right is the final buffer frame.

#.  Enter the window size.

#.  Select the appropriate molecule type (Protein or RNA) for the molecular weight calculation.

#.  Click the “Set/Update Parameters” button.

#.  The structural parameters will be plotted as a function of frame number in the SEC plot.
    If RAW was unable to determine the parameters for a particular window, then all parameters
    in that window are set to -1.

The Rg and I(0) calculations are done using RAW’s :ref:`automatic rg function <guinierwindow>`.
The molecular weight calculation is done using the
:ref:`volume of correlation method <molweightmethods>`.

**Note:** See :ref:`below <secplottypes>` for how to show different structural parameters
on the SEC plot.


Data point browsing
~~~~~~~~~~~~~~~~~~~

.. _secdatadialog:

The Frame number, integrated intensity, mean intensity, Rg, Rg error, I(0), I(0) error,
MW, filename, and, if available intensity a q=<#> where <#> is a user selected value,
for each individual point can be inspected using the data browser. To do so:

#.  Right-click on the data item of interest.

#.  Select “Show data” in the popup menu.


The SEC data item right click menu options
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When you right click on a data item, a popup menu is shown. This section describes what
each item on the menu does.

*Remove*

Removes the item.

*Export data*

Exports the SEC data item to a spreadsheet.

*Save all profiles as .dats*

Saves all of the scattering profiles loaded into the SEC item as individual .dat files.

*Save*

Saves the selected data item(s).

*SVD*

Opens the singular value decomposition (SVD) analysis panel for the selected SEC item.

*EFA*

Opens the evolving factor analysis (EFA) panel for the selected SEC item.

*Show data*

Shows the individual data points.

*Rename*

Renames the data item.


The SEC panel bottom buttons
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

There are three buttons at the bottom of the SEC control panel. They are:

*Save*

This button saves the selected data item(s).

*Remove*

This button removes the selected data item(s) from the SEC panel.

*Clear SEC Data*

This button clears all loaded SEC data. It works the same as if you had selected
all of the SEC data items and then removed them.


The SEC Plot window
-------------------

The SEC plot window has only one plot, however data can be plotted on both the left
and right y axes. The left axis plots intensity from scattering profiles, while the
right axis plots structural parameters (Rg, MW, I(0)). The items associated with the
plotted curves are shown in the SEC control panel list.

The features that are general between all of the plots are described :ref:`elsewhere <genplotpanel>`.
This section will describe features unique to this plot.


Changing axes and plot types
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. _secplottypes:

Right-click in the plot to view a pop-up menu with different axis settings. In this
plot, you can change what data is plotted on each axis.

*Y Data (Left Axis)*

This allows you to change intensity plotted on the left y axis. The methods are:

*   Integrated intensity (default), which is

.. math::
    I_{tot} = \int_{q_{min}}^{q_{max}} I(q) dq

*   Mean intensity, which is the average intensity across the whole scattering profile

*   Intensity at q=…, which allows the user to specify a q value, and displays the
    intensity at the nearest q point to that specified value.

*Y Data (Right Axis)*

This allows you to change which calculated structural parameter is plotted on the right y axis.

#.  RG (default) which plots the Rg

#.  MW which plots the molecular weight

#.  I(0) which plots the I(0)

#.  None, which turns off the right y axis.

*X Data*

This allows you to change what is plotted on the x axis.

*   Frame Number, which plots the intensity and structural parameter as a function of frame number.

*   Time, which puts the x axis in terms of experimental time.

**Note:** The time display on the x axis is only available for certain types of header
files. Currently only G1 and G1 WAXS header files will have associated time values.

