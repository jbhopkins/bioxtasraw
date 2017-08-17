The IFT Control Panel and IFT Plot Panel
========================================

.. _iftpanel:

When inverse Fourier transforms (P(r) functions) are loaded into RAW or generated
by BIFT or GNOM in RAW, they are placed in the IFT tab of the Control Panel, and
displayed in the IFT Plot window. This section will cover the features of the IFT
control panel and IFT plot panel.


The IFT control panel
---------------------

The IFT control panel refers to the panel that is shown in the Control panel
when the IFT tab is selected.

The panel consists of two parts. The top part is where individual IFT items loaded
into RAW are shown. The bottom part consists of buttons that allow you to save or
remove those IFT items. Further manipulation of the IFT items can be done from the
right click (context) menu and from the Tools menu.

An individual item in the IFT list is called an IFT data item. It is associated
with a P(r) function, the scattering profile used to generate that P(r) function,
and the scattering profile generated from the P(r) function.

All items loaded into the IFT panel have a P(r) function displayed in the top plot
of the IFT Plot window, and an experimental scattering profile and a scattering profile
from the P(r) function displayed in the bottom plot of the IFT Plot window.


IFT Data Items
~~~~~~~~~~~~~~

When a new item is plotted, a data item is added to the IFT list in the IFT tab.
This allows you to control the properties of the data item, and perform analysis on it.

The name of the data item is displayed for each item. If an item is given a different
name for the plot legend, this legend name is displayed in [square brackets] next to the
item name. On the same line as the item name, on the right side of the data item, there
are several buttons that can be used for :ref:`further manipulation <iftitembuttons>`
of the data item.

**Note:** If there is a \* to the left of the item name (between the checkbox and the
item name), it indicates there are unsaved changes to the item. This can occur if the
item is newly created IFT data (such as from the BIFT or GNOM panels), or if item properties
such as the name have been changed.


Showing/Hiding data items on the IFT plot
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To show/hide all of the curves (P(r), experimental data, scattering profile from P(r) curve)
associated with a data item on the plot, click the checkbox next to the filename. If the checkbox
is checked, the item is currently shown on the IFT plot, if the checkbox is unchecked, the item
is currently hidden on the IFT plot.


Data item buttons
~~~~~~~~~~~~~~~~~

.. _iftitembuttons:

On the right of the data are a series of buttons for controlling the data item. In order of
left to right, these buttons have the following properties.

*Locate Line*

The target button is used to highlight the scattering profile on the graph that is associated
with the data item. When the target is pressed, it ‘bolds’ the line each plotted curve associated
with the data item (increases the line width by several points). When the target is pressed again,
the line width is set back to normal. You can tell if a line is currently bolded, as the target
will be orange instead of grey.

*Line Properties*

The colored line button has two purposes. First, the color matches the current color of the
P(r) function in the IFT Plot. Second, when pressed it opens a
:ref:`line properties dialog <lineproperties>` which allows you to set the legend label;
the line style, width, and color; the data point marker style, size, line color, and fill
color; and the error bar line style, width, and color for each line associated with the IFT data item.


Selecting data items
~~~~~~~~~~~~~~~~~~~~

A single data item can be selected by clicking on the item name in the IFT list (similar to
how you would select files in your system file browser). When an item is selected, the color
of the item background changes from white to gray. If the item is currently selected, clicking
on it will cause it to be unselected. Note that for a regular click, all other selected items
will be unselected when a new item is selected.

Multiple items may be selected in two ways. If the Control key (Command key on Macs) is held
down while clicking on items, each item that is clicked on will be added to the set of selected
items. If a single item is first selected and then the Shift key is held down and another item
is selected, all of the items in the list between the two items will be selected (including the
second item that is clicked on).

All of the items in the list can be selected in two ways. The first is using the
:ref:`select all <iftselectall>` button, the second is pressing Ctrl-A (Cmd-A),
the Control (Command) key and the A key at the same time when you are in the IFT panel.
All items can be unselected by clicking in an empty spot of the IFT list (but not above
or below the list), or by clicking on an already selected item.

**Note:** If you have a set of selected items and wish to remove some, holding down the Control
(Command) key and clicking on selected items will deselect them without affecting the other selected
items.


The top buttons of the IFT Panel
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The IFT Panel has a set of three buttons at the top of the panel. These buttons have the following
effects, listed from left to right.

*Show All*

Clicking on the button that looks like an eye will show all IFT items. This is the same as if you
manually set all of the show/hide checkboxes in the data items to on.

*Hide All*

Clicking on the button that looks like an eye with a red x through it will hide all IFT items.
This is the same as if you manually set all of the show/hide checkboxes in the data items to off.

*Select All*

.. _iftselectall:

Clicking on the button that looks like a spreadsheet with selected cells will select all of the
IFT data items.


Renaming a data item
~~~~~~~~~~~~~~~~~~~~

.. _renameiftitem:

Data items can be renamed by selecting the data item of interest and selecting “Rename” in the right
click popup menu.

**Note:** While no characters are expressly forbidden in the filename, RAW does not sanitize file names
before saving, and thus special characters such as ‘/’ and ‘\\’ are likely to cause problems when the
file is saved.


Saving data items
~~~~~~~~~~~~~~~~~

.. _savingiftdata:

IFT items are saved in two different formats, depending on whether the item was generated by BIFT
(“.ift”) or GNOM (“.out”). The procedure to save either is the same. To save:

#.  Select the item(s) to be saved.

#.  Click the “Save” button or select “Save selected file(s)” from the right click menu.

#.  In the window that pops up, navigate to the directory in which you want to save the files.

#.  If you are saving a single item, the window will give you an opportunity to rename your file
    if desired. Click “Save” when ready.

#.  If you are saving multiple items, you simply need to select the folder for the items to be saved
    in, and click “Open”. The items will be saved with the same names displayed in the IFT Panel, in
    the folder that you chose.

BIFT items are saved as “.ift” files, which is a text file with RAW specific formatting of the text.
The first two lines are “BIFT” and the “Filename: <filename>”. After that, the P(r) function is saved
as 3 column data. The first column is “R”, the second column is “P(R)” and the third column is “Error”,
these headers are included as the third line of the file. After the P(R) function there are two blank
lines, followed by the scattering data. This is saved in four columns, the first three are “Q”, “I(q)”
and “Error” which correspond to the experimental data, while the fourth column is “Fit” which is the
scattering profile from the P(r) function. After this data is written there is a “header” written, which
consists of the Chisquared, algorithm used, I(0) value, log base 10 of the alpha value, Dmax, Rg, and the
filename, all saved in JSON format. The files are simply text files, and can be opened and viewed in any
standard text editor.

GNOM items are saved in the standard “.out” format. This is described in the ATSAS manual for GNOM.
These files can be directly input into any ATSAS (or other) program that requires a GNOM .out file as input.


Removing data items from the IFT list
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. _removeift:

To remove one or more data items, select them and do one of the following:

#.  Press the “Delete” key on the keyboard

#.  Click the “Remove” button

#.  Select “Remove” from the right click menu


Sending data to the main plot
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. _ifttomainplot:

If you wish to examine the experimental scattering profile and fit to this profile from
the P(r) function more closely, the data can be sent to the main plot. To do this, right
click on the IFT data item and select “To Main Plot”. This will plot items on the Main plot
and add them to the Manipulation list.

For a “.ift” file generated by BIFT, the following items will be added to the Manipulation list
and Main plot. In all cases, <filename> corresponds to the filename of the IFT data item without
the extension (so “my_ift”.ift would have a filename of “my_ift”).

<filename>_data – This is the experimental data that was used to generate the P(r) curve.

<filename>_fit – This is the scattering profile generated from the P(r) curve.

For a “.out” file generated by GNOM, the same two curves as for a BIFT item (above) are sent to the
main plot, there is also one additional file.

<filename>_extrap – This is the scattering profile generated from the P(r) curve, extrapolated to q=0.


Running DAMMIF on the P(r) function
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

RAW allows you to run DAMMIF on a P(r) function from within RAW. Currently, this can only be
done on P(r) items generated by GNOM (these can be generated in RAW, or loaded in after being
generated outside of RAW). To run DAMMIF, select an appropriate IFT data item (a “.out” item),
and either right click and select the “Run DAMMIF” option or from the Tools->ATSAS menu select
“DAMMIF”. This opens the :ref:`DAMMIF window <dammifwindow>`.


Running AMBIMETER on the P(r) function
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

RAW allows you to run AMBIMETER on a P(r) function from within RAW. Currently, this can only
be done on P(r) items generated by GNOM (these can be generated in RAW, or loaded in after
being generated outside of RAW). To run AMBIMETER, select an appropriate IFT data item (a
“.out” item), and either right click and select the “Run AMBIMETER” option or from the
Tools->ATSAS menu select “AMBIMETER”. This opens the :ref:`AMBIMETER window <ambimeterwindow>`.


Data point browsing
~~~~~~~~~~~~~~~~~~~

.. _showiftdata:

Each individual point of the r; P(r); error in P(r); experimental q, I(q), and error;
I(q) from the P(r) function; and, for GNOM generated IFT data items, the q and I(q)
values extrapolated to q=0 vectors; can be inspected using the data browser. To do so:

#.  Right-click on the data item of interest.

#.  Select “Show data” in the popup menu.


The IFT data item right click menu options
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When you right click on a data item, a popup menu is shown. This section describes what each
item on the menu does.

*Remove*

:ref:`Removes the item <removeift>`.

*To Main Plot*

This :ref:`sends the scattering profile data to the main plot <ifttomainplot>`.

*Run DAMMIF*

This item is only available for “.out” files generated by GNOM. It opens the
:ref:`DAMMIF window <dammifwindow>`.

*Run AMBIMETER*

This item is only available for “.out” files generated by GNOM. It opens the
:ref:`AMBIMETER window <ambimeterwindow>`.

*SVD*

Opens the singular value decomposition (SVD) analysis panel for the selected scattering
profiles (must have at least 2 items selected).

*EFA*

Opens the evolving factor analysis (EFA) panel for the selected scattering profiles
(must have at least 2 items selected).

*Show data*

Shows the :ref:`individual data points <showiftdata>`.

*Rename*

:ref:`Renames <renameiftitem>` the data item,

*Save selected file(s)*

:ref:`Saves the selected data item(s) <savingiftdata>`.


The IFT panel bottom buttons
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

There are three buttons at the bottom of the IFT control panel. They are:

*Save*

This button :ref:`saves the selected data item(s) <savingiftdata>`.

*Remove*

This button :ref:`removes the selected data item(s) <removeift>` from the IFT panel.

*Clear IFT Data*

This button clears all loaded IFT data. It works the same as if you had selected all of
the IFT data items and then removed them.


The IFT Plot window
-------------------

The IFT Plot window displays P(r) data (top plot), the scattering profiles generated from
the P(r) data (bottom plot), and the experimental scattering profile used to generate the
P(r) data (bottom plot). Each set of three curves is associated with a single IFT data item
in the IFT control panel. The two subplots are the Pair Distance Distribution Function (top)
and Data/Fit (bottom) plots.

The features that are general between all of the plots are described :ref:`elsewhere <genplotpanel>`.
This section will describe features unique to this plot.


Changing axes and plot types
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Right-click in the Data/Fit (top) plot to view a pop-up menu with different axis settings.

The available plot modes are:

*   Lin-Lin

*   Log-Lin

*   Log-Log

*   Lin-Log

*   Guinier plot (ln(I(q)) vs. q\ :sup:`2`\ )

*   Porod plot (q\ :sup:`4`\ I(q) vs. q)

*   Kratky plot (q\ :sup:`2`\ I(q) vs. q)

The axes cannot be changed for the P(r) (top) plot.


The IFT plot toolbar
~~~~~~~~~~~~~~~~~~~~

In addition to the plot toolbar buttons :ref:`shared by all of the plots <navbar>`, the
IFT plot has the following buttons:

|100000000000002200000021727FD1590D192861_png|

Toggle errorbars. Shows the errorbars on the plotted curves.

|100000000000001F00000021D9FCD008A5DADBD2_png|

Top/Bottom plot. Shows both the top and the bottom plot.

|100000000000001F00000020F81C3AA753AFD388_png|

Top plot. Shows only the top plot.

|1000000000000022000000213F375FFE6DB9D8A9_png|

Bottom plot. Shows only the bottom plot.


.. |100000000000001F00000020F81C3AA753AFD388_png| image:: images/100000000000001F00000020F81C3AA753AFD388.png


.. |100000000000001F00000021D9FCD008A5DADBD2_png| image:: images/100000000000001F00000021D9FCD008A5DADBD2.png


.. |1000000000000022000000213F375FFE6DB9D8A9_png| image:: images/1000000000000022000000213F375FFE6DB9D8A9.png


.. |100000000000002200000021727FD1590D192861_png| image:: images/100000000000002200000021727FD1590D192861.png

