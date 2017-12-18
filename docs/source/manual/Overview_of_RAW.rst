Overview of RAW
===============

The main screen of RAW shows three distinct panels: The Information Panel (top left),
the Control Panel (bottom left), and the Plot Panel (right). Additional windows that
can be shown are the Options window, and various Analysis windows. In addition, there
is a menu bar at the top of RAW (either in the RAW window or in the system menu bar,
depending on your operating system).


Any of the three panels docked in the main RAW window can be moved relative to the
other panels. To do this, click on the title bar of the panel, and drag the panel
to the desired location (you should see a blue rectangle indicating where the panel
will be put). Additionally, panels can be undocked from the main window by clicking
on the pin icon on the right side of the title bar of the panel. Undocked panels can
be re-docked with the main window using the same method as rearranging the panels,
drag the title bar until you see a blue rectangle appear indicating where the panel
will go.


The portion of the total area available for the left (information and control) and
right (plot) sides of RAW is controlled by the separator bar. You can click and drag
on this bar to change this ratio.


The main RAW window can be resized by clicking and dragging on a corner or edge.

The Control panel
-----------------

The control panel is where you manipulate files and items loaded into RAW. It has
four tabs: Files, Manipulation, IFT, and SEC. The Files tab is for viewing files
on the system disk, and loading the files into RAW. The Manipulation tab is for
working with individual scattering profiles, the IFT tab is for working with inverse
Fourier transforms, and the SEC tab is for working with SEC-SAXS data. You change
tabs just by clicking on them. The order of the tabs in the control panel can be
rearranged by clicking and dragging the tabs.

The Plot panel
--------------

.. _genplotpanel:

The plot panel contains four tabs: the Main Plot, IFT Plot, Image plot, and SEC
plot tabs. The Main Plot tab is for viewing individual scattering profiles. The
IFT Plot tab is for viewing inverse Fourier transforms, the Image plot tab is for
viewing detector images, and the SEC plot tab is for viewing SEC-SAXS data. The
order of the tabs can be changed by clicking and dragging.


Multiple different plot tabs can be displayed at the same time. Click and drag the
tab to any edge of the Plot Panel (up, down, left, or right) and you should see a
blue box appear indicating where the tab will go. Additional splits after the
first can be accomplished by dragging other tabs, and tabs can be moved between
different tab bars (in this case, you should see the bar light up blue, rather
than a full blue box for the panel). The amount of screen occupied by the different
plots can be set by clicking and dragging the separator bars. To recombine, drag all
of the plot tabs into a single bar.


*Navigation/control bar*

.. _navbar:

Each Plot tab has a navigation/control bar on the bottom. Most navigation bars have
some unique buttons, but they all share the following buttons:

|10000000000000210000002267AFAB5BBBEB8688_png|

Home. Zoom the to fit all the displayed data.

Move back and fourth in the zoom history.

|1000000000000023000000229179FE499099E336_png|

|1000000000000023000000229179FE499099E336_png|


Pan/Zoom. Click and drag the left mouse button to pan and the right mouse button to zoom.

|1000000000000023000000229BAB0E7642366178_png|


|10000000000000230000002174F1BA52DF6B9C53_png|

Area Zoom. Click and drag to zoom to the selected area.

|100000000000001F0000001F9C07D19476FF080E_png|

White-space settings. Ability to adjust the white-space around the plots.


|100000000000001C0000001F02670C0CCE6242ED_png|

Image save. Ability to save the displayed plot(s) in formats such as .png, .svg, .eps,
.pdf and more.


*Cursor readout*

Every plot has a cursor readout. If the mouse is hovering over a position on the plot,
the coordinates (x-axis and y-axis values) will read out in the bottom bar of RAW. For
the image plot, the intensity at those coordinates is also displayed. For the SEC plot,
the value of the secondary y-axis is also displayed.


*Plot settings*

For each of the Main Plot, IFT Plot, and SEC plot, one of the options in the right-click
menu is “Plot Options”. Selecting this will open a window that allows you to set:

*   Plot title, x-axis label, and y-axis label text, font size, and bold/italicization

*   Legend title, font size, and bold/italication

*   Whether the legend is visible (default: no)

*   Legend font size, transparency, border, and shadow

*   Turn auto limits on/off for the Axes and manually set the axes limits if desired

*   Turn off the left/right/top/bottom plot borders

*   Turn on a line at y = 0 (the Zero Line)

*   Adjust the axes tick label font sizes


The axis labels and title will accept some LaTeX commands if they are placed between
$ symbols, for example: $\\int I(q)$ will display as :math:`\int I(q)`. The bold and
italic options will not change LaTeX text.

The settings will be changed for the plot/subplot that was clicked on.

The Information panel
---------------------

The information panel displays information about a selected data item in the Manipulation
panel. It will show, if available, the Rg, I(0), and MW. It provides a place to enter the
sample concentration, description/notes about the sample, and quickly look at the different
header values of the data item.

If the current Control panel is changed from the Manipulation panel to the IFT or SEC panel,
the Information panel is cleared. If the panel is changed back to the Manipulation panel,
the data in the Information panel are restored.

The Options window
------------------

The options panel is opened by clicking on the Options->Advanced Options menu item. This
opens a separate window where many of the RAW settings can be viewed/changed. The panel
has two pieces. On the left is the set/category of options, and on the right the actual
options panel. For example, if you click on the General Settings section in the left panel,
the general settings will be displayed on the right.

Note that in the options tree on the left, the triangles can be used to expand/collapse more
options for many of the categories.

Once you have changed the settings, you simply need to click “OK” and they will be saved
in memory. In some cases you may want to set the options without exciting the panel. To
do this, click “Apply”. To exit without saving any changes click “Cancel”.

Analysis windows
----------------

Various analysis windows can be opened in RAW. These will be discussed in detail
:ref:`later <analysiswindows>`.

Menus
-----

The top menu bar of RAW contains the File, Options, View, Tools, and Help menu. The View
and Tools menu are simply another way to access options found elsewhere, while the File,
Options, and Help menu have items that cannot otherwise be accessed. These will be discussed
:ref:`later <menus>`.


.. |10000000000000230000002174F1BA52DF6B9C53_png| image:: images/10000000000000230000002174F1BA52DF6B9C53.png


.. |100000000000001F0000001F9C07D19476FF080E_png| image:: images/100000000000001F0000001F9C07D19476FF080E.png


.. |100000000000001C0000001F02670C0CCE6242ED_png| image:: images/100000000000001C0000001F02670C0CCE6242ED.png


.. |1000000000000023000000229BAB0E7642366178_png| image:: images/1000000000000023000000229BAB0E7642366178.png


.. |1000000000000023000000229179FE499099E336_png| image:: images/1000000000000023000000229179FE499099E336.png


.. |10000000000000210000002267AFAB5BBBEB8688_png| image:: images/10000000000000210000002267AFAB5BBBEB8688.png

