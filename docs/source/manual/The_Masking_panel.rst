The Masking panel
=================

**WARNING:** The manual is current several versions out of date. While it may
still be useful for some users, please refer to the tutorial for the most
up-to-date information.

.. _masking:

The masking panel allows you to create various types of masks that will be used when the
image is integrated into a one dimensional scattering profiles.


Types of masks
--------------

Beamstop mask
~~~~~~~~~~~~~

Unwanted regions such as the beamstop, bad pixels, or gaps between detector panels need to
be excluded from the detector image before processing the image. Creating a beamstop mask
allows you to do so. For a beamstop mask, when a normal mask is drawn (shown as red on the
image), the area inside the mask is excluded from integration. When an inverted mask is used
(green on the image), only the area within the mask is included during integration. These
types of masks can be combined: normal masked regions will be excluded from integration, even
if some or all of the same region is included in the inverse mask region. This allows you to
create an inverse mask, and mask out undesired features within that inverse mask.


ROI counter mask
~~~~~~~~~~~~~~~~

.. _makeroimask:

RAW allows you to define a region of interest (ROI) mask. If you have an ROI mask defined,
every time an image is integrated to a scattering profile, all of the pixel intensities in
the ROI mask will be summed, and the value will be available as a counter. In this case, the
normal mask (red color) is an include only mask, while the inverted mask (green color) is an
exclusion mask. Thus, any areas with a normal mask will be counted in the ROI, while any areas
with an inverted mask will be ignored by the ROI.

Typically this is used for normalization purposes, for example to normalize by the transmitted
beam through a semi-transparent beamstop. The counter name that this value goes to is *roi_counter*.


SAXSLAB Beamstop mask
~~~~~~~~~~~~~~~~~~~~~

The SAXSLAB home source instruments embed the beamstop mask within the image header. Selecting this
beamstop mask option will allow you to show this mask on the image. This mask cannot be changed within RAW.

*Note:* Both a beamstop mask and a SAXSLAB beamstop mask can be simultaneously defined in RAW. In that
case, they are both used to mask the image.


Readout-dark mask
~~~~~~~~~~~~~~~~~

The area that is selected by a readout-dark mask is averaged for each image, and that average
value is subtracted off of every pixel in the image. The standard deviation in the pixel counts
is added in quadrature with the noise in the scattering profile calculated during integration
(the standard deviation of the counts in each q bin). In this case, the normal mask (red color)
is an include only mask, while the inverted mask (green color) is an exclusion mask. Thus, any
areas with a normal mask will be averaged to get the readout-dark counts, while any areas with
an inverted mask will be ignored by the average.

Setting a readout-dark mask is intended to allow RAW to compensate for dark counts on the detector
(most common with CCD detectors). Typically it is used when a fixed area of the detector is
permanently masked, such as by lead tape applied to the detector face.


Creating a mask
---------------

In order to creating a mask, an appropriate image must first be l:ref:`open <showimage>`
in the :ref:`Image panel <imageplotpanel>`. Mask creation is then done as follows:

#.  Select the appropriate mask type from the drop down masking menu in the Mask Creation panel.

#.  Use the mask drawing tools to draw a mask on the image.

#.  For the circle and rectangle tools, left click once to start drawing, move the mouse until
    you have the desired shape, and click again to stop drawing.

#.  For a polygon, left click once to start drawing, and continue left clicking to add
    vertices. To finish drawing and connect the final point to the initial point, right click.

#.  To invert a mask section, right click on the section and select “Inverted mask”.

#.  To remove a mask section, left click on the section to select it and click the delete key.

#.  You may draw as many mask sections as you want.

#.  Once done, click the “Set” button to save the mask.

**Note:** Clicking “Set” overwrites the existing mask in memory. To add new regions to an existing
mask, see below.


Viewing and modifying a mask
----------------------------

At times you may wish to view an existing mask, and possibly modify it. To do so:

#.  Select the mask type in the Mask Creation panel drop down menu.

#.  Click “Show” to show the existing mask.

#.  Draw new masked regions and/or remove old masked regions as above.

#.  Once you have finished modifying the mask, click “Set” to save your changes.


Removing a mask
---------------

.. _removemask:

To completely remove a mask, select the appropriate type of mask in the drop down menu
in the Mask Creation panel, and click the “Remove” button.


Saving/Loading a mask to/from disk
----------------------------------

A mask may be saved to disk by itself (saving the settings saves the mask as well),
using the “Save” button in the mask drawing panel, and loaded into RAW using the “Load”
button. Once a mask is loaded, select the appropriate mask type from the drop down menu
in the Mask Creation panel and click “Set” to set the loaded mask as that mask type.


**Note:** The “Save” button does not save the mask in program memory! You must use the
“Set” button to set a mask as the current mask for use. Save and load are exclusively for
saving/loading to/from disk.


Clearing a mask
---------------

The “Clear” button clears any mask from the image. However, to save these changes, you must click
“Set” for the mask type of interest. To remove a mask from use in RAW, see :ref:`above <removemask>`.


Mask drawing options
--------------------

The check box “Show Beam Center” puts a red circle of diameter 6 pixels on the image where the
beam center is (as set in the Centering/Calibration panel).
