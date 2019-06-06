Online mode
===========

**WARNING:** The manual is current several versions out of date. While it may
still be useful for some users, please refer to the tutorial for the most
up-to-date information.

.. _onlinemode:

RAW has an online mode that will watch a folder, and automatically load any
files placed in the folder that RAW can read. This is typically used to
automatically load in data as it is being collected at the beamline. This
is distinct from the :ref:`automatic update feature <secautoupdate>` of the
SEC Control panel, and both features can be active at once.


Turning on/off online mode
--------------------------

In order to turn on online mode, go to the Options->Online Mode menu and
click the “Online” option. When you go online, a file browser will open
and you will pick a folder. This folder (and only this folder, online mode
does not recurse into subfolders) will be monitored by RAW. Every time a
file is added (or updated) in the folder, RAW checks to see whether it can
load the file. If it can, it will be loaded into RAW (for example, detector
images will be integrated and loaded into the Manipulation panel and Main plot).

To disable online mode, go to the Options->Online Mode menu and click the “Offline” option.

**Note:** The online status of RAW is indicated in the status bar at the bottom of the
main RAW window. On the right side, it says “Mode: <status>” where <status> is OFFLINE
or ONLINE. This is only toggled by this online mode, not the automatic update feature of
the SEC panel.


Changing directories in online mode
-----------------------------------

If you wish to change the directory that RAW is monitoring in online mode, go
to the Options->Online Mode menu and click the “Change Directory” option. A file
browser will appear, and you will use that to select the new folder for the Online mode.


Online mode filter
------------------

In some cases, you may not want every file that enters the directory (that can be read
by RAW) to be loaded into RAW. In this case, it is possible to set a filter so that
only certainly files can be loaded into RAW. The filter can consist of any number of
individual items, which are set as follows. First, chose whether an item is include (open
only if) or exclude (don’t open if). Then provide a string for RAW to match in the file name.
Then specify where in the filename RAW should match the string (start, end, anywhere). This
filter can be set in the :ref:`options window <onlinefilter>`.

