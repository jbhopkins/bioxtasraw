Menus
=====

.. _menus:

RAW has 5 program wide menus: File, Options, View, Tools, and Help.


The File menu
-------------

The File menu has five choices:

*Load Settings*

This loads RAW settings from a .cfg file. This can also be done by double clicking
on the .cfg file in the Files tab of the Control Panel.

*Save Settings*

This saves all of the RAW settings, including image calibration and the image mask,
to a .cfg file so they can be loaded again later.

*Load Workspace*

This loads a RAW :ref:`workspace <workspaces>`.

*Save Workspace*

This saves a RAW :ref:`workspace <workspaces>`.

*Quit*

This quits the RAW program. If you have unsaved data or are running DAMMIF reconstructions
you will be asked to confirm that you wish to quite.


The Options menu
----------------

The options menu has one choice and one submenu. The “Advanced Options” choice opens
the :ref:`Options window <optionswindow>`. The submenu is labeled “Online mode”
and the three options available there are described :ref:`here <onlinemode>`.


The View menu
-------------

The view menu has three top level options and five submenus. The three top level options are:
“Show image”, “Show data”, and “Show header”. All of these require that a single manipulation
item be selected, and otherwise behave as the options of the same name in the Manipulation
data item :ref:`right click menu <maniprightclick>`.

The view menus named “Top Main Plot Axis” and “Bottom Main Plot Axis” change the plot axes/scale
of the top and bottom main plots respective. Each option in the two menus corresponds to the options
in the main plot :ref:`right click menu <manipplottypes>`.

The view menus named “SEC Plot Left Y Axis”, “SEC Plot Right Y Axis”, and “SEC Plot X Axis” change
the data plotted on the SEC Plot axes as the options in the SEC plot
:ref:`right click menu <secplottypes>`.


The Tools menu
--------------

The Tools menu is split into three parts. In all of the items in the top part of the menu apply
to Manipulation data items and all of them require one or more Manipulation data items to be selected.
The first submenu is “Operations”. This contains a set of operations that can be run on Manipulation
data items, and have identical effects to items of the same name in the manipulation
:ref:`right click menu <maniprightclick>`. The second submenu is “Convert q-scale” and
the options in the menu have identical effects to items of the same name in the Manipulation
data items, and have identical effects to items of the same name in the manipulation
:ref:`right click menu <maniprightclick>`. The third item is “Use as MW Standard” and has an
identical effect as the item of the same name in the manipulation :ref:`right click menu <maniprightclick>`.

The middle part of the Tools menu consists of analysis tools. The “Guinier Fit”, “Molecular Weight”
and “BIFT” options, and the “ATSAS” submenu option “GNOM” all require a single Manipulation data item
to be selected. These all open the corresponding :ref:`analysis windows <analysiswindows>`.
The “DAMMIF” and “AMBIMETER” options require a single IFT data item to be selected, and open the
corresponding :ref:`analysis windows <analysiswindows>`. The “SVD” and “EFA” require either
that multiple Manipulation or IFT data items be selected for that a single SEC data item be selected,
and open the corresponding :ref:`analysis windows <analysiswindows>`.

The lower part of the Tools menu consists of two options. The “Centering/Calibration” option requires
that an appropriate image for centering/calibration be loaded in the Image plot panel. It then opens
the :ref:`Centering/Calibration panel <centeringcalibration>`. The “Masking” option requires that an
appropriate image for masking be loaded in the Image plot panel. It then opens the
:ref:`Masking panel <masking>`.


The Help menu
-------------

The Help menu has two options on it. The “Help!” option shows a window describing how to find help for
RAW (including a reference to this document). The “About” provides a very brief description of RAW,
includes the RAW citation, provides the license agreement, and lists the developers.

