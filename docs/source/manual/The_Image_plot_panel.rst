The Image plot panel
====================

**WARNING:** The manual is current several versions out of date. While it may
still be useful for some users, please refer to the tutorial for the most
up-to-date information.

.. _imageplotpanel:

The Image plot panel displays any detector image that RAW is able to read. The image name
is shown at the top of the plot, while the x and y axes are in dimensions of pixels. There
is no right click menu for this plot, but scrolling with a mouse scroll wheel will zoom in
and out. It is possible to display regions where there is no image data, these will show up
as a white background (for example, if you zoom out and show negative pixel ranges.

In addition to the plot toolbar buttons :ref:`shared by all of the plots <navbar>`,
the Image plot has the following buttons:

|100002010000001800000018B603AD208545D77F_png|

Displays the image header. This does not display any information from separate header files,
only what is in the image itself.

|1000020100000018000000187E6D3770EAA7994B_png|

Opens the image display settings dialog described in below.

|10000201000000500000001EACBFAAFAC41D2CC1_png|

Shows the previous/next image in the same directory as the current image (as sorted by filename, A-Z).


The Image Display Settings dialog
---------------------------------

The Image Display Settings dialog lets you change how the image is displayed on the screen.
It has three sections, Image parameters, Image scaling, and Colormaps.

*Image parameters*

There are three slider bars here. The Upper and Lower limit sliders let you set what pixel
values in the image correspond to the most extreme values of the color scale chosen. The
Brightness color bar does not work at the moment. By default, the upper and lower limit
values are automatically set each time an image is loaded into the Image plot panel.
However, checking the Lock values checkbox will prevent the current set values from
changing. This allows you to scroll through images maintaining constant upper and lower limits.

*Image scaling*

Image scaling allows you to use a linear or logarithmic (base 10) color scale. The logarithmic
scale uses the matplotlib.colors.SymLogNorm function (more available here:
`https://matplotlib.org/api/colors_api.html <https://matplotlib.org/api/colors_api.html>`_),
with a linear threshold set at 1. So the image is logarithmic in color display above 1, and
linear in color display below 1 (this is so 0 and negative value pixels can be handled).

*Colormaps*

The colormaps option allows you to change the color scale used to display intensity values
in the Image plot. The color maps are those available through matplotlib (
`https://matplotlib.org/users/colormaps.html <https://matplotlib.org/users/colormaps.html>`_),
a limited selection of which are available in RAW: Gray, Heat, Rainbow, Jet (default), Spectral.

**Note:**
Currently there is also a brightness setting, but it does not work properly.

.. |1000020100000018000000187E6D3770EAA7994B_png| image:: images/1000020100000018000000187E6D3770EAA7994B.png


.. |10000201000000500000001EACBFAAFAC41D2CC1_png| image:: images/10000201000000500000001EACBFAAFAC41D2CC1.png


.. |100002010000001800000018B603AD208545D77F_png| image:: images/100002010000001800000018B603AD208545D77F.png

