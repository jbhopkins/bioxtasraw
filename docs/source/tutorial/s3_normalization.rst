Setting normalization and other options
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.. _s3p4:

This section teaches you how to set up normalization by a beamstop counter, and
other options. It assumes you have completed :ref:`Parts 1 <s3p1>` (or :ref:`2 <s3p2>`\ )
and :ref:`3 <s3p3>`.

#.  Open the Options window by selecting “Advanced Options” in the Options menu.

#.  In the window that shows up select the Image/Header Format section on the left.
    In the area on the right click the Load Image button.

    |1000020100000321000002567002F3E445956D31_png|

#.  In the window that pops up, select the **AgBeh_A1_43_001_0000.tiff** file. Click
    the Open button.

    *   *Note:* You can select any image of the appropriate type, not just the behenate.

#.  In the Image/Header Format window you should now see header values loaded into the
    list. Click the Apply button at the bottom of the screen.

    |1000020100000261000000FF99D0DAD279E9E046_png|

#.  Click on the Normalization section in the options list on the left.

#.  In the fields at the bottom of the Normalization panel, make sure “/” is selected
    in the left dropdown menu, and enter I3/200000 in the large field.

    *   *Note:* It is typical in SAXS to normalize by the transmitted intensity. At the
        CHESS G1 beamline, the beamstop counter is name I3, which is why we are using
        that name in the normalization expression.

    |10000201000003200000025782A90D7B63DA90C9_png|

#.  Click the Calc button to evaluate the expression for the counter values loaded
    in the Image/Header Format tab. You should get a value of 0.02404.

#.  Click the Add button to add the expression to the normalization list.

#.  Make sure the “Enable Normalization” checkbox at the top of the page is checked.

#.  Click OK to exit the options window.

#.  In the file list, select the **AgBeh_A1_43_001_0000.tiff** file and click the Plot
    button. You will see a curve get plotted in the top panel of the Main Plot.

#.  Click on the manipulation tab. You will see a data item loaded in the manipulation list.

    |10000201000003FA00000193060E3A3AD503E41B_png|

#.  Adjust the start point for q Min to remove the points with zero value at the start of
    the curve (these are q points entirely in the mask). Set q Min so that the first point
    is the peak of the curve on the main plot. This should be around point 13 (depending
    on your mask).

    |10000201000003DE0000018D073F6458E51E1527_png|

#.  Open the Options window as in Step 1.

#.  Click on the Calibration section in the options list on the left. Set “Start plots
    at q-point number” to the number you just found in Step 13.

    *   *Note:* This makes it so that every curve loaded from now on will by default
        not display the first n points, which are covered by the beamstop.

    |1000020100000311000000E79A17725090A964FF_png|

#.  Click the OK button to exit the options window and save your changes.

#.  You have configured everything necessary, and are now ready to save your settings.
    Go to the File menu and select “Save Settings”.

#.  Save the settings as **SAXS.cfg**\ .

#.  These settings can now be used to process images, and can be reloaded when you
    open RAW by selecting “Load Settings” from the File menu.



.. |1000020100000321000002567002F3E445956D31_png| image:: images/1000020100000321000002567002F3E445956D31.png

.. |1000020100000261000000FF99D0DAD279E9E046_png| image:: images/1000020100000261000000FF99D0DAD279E9E046.png

.. |10000201000003200000025782A90D7B63DA90C9_png| image:: images/10000201000003200000025782A90D7B63DA90C9.png

.. |10000201000003FA00000193060E3A3AD503E41B_png| image:: images/10000201000003FA00000193060E3A3AD503E41B.png

.. |10000201000003DE0000018D073F6458E51E1527_png| image:: images/10000201000003DE0000018D073F6458E51E1527.png

.. |1000020100000311000000E79A17725090A964FF_png| image:: images/1000020100000311000000E79A17725090A964FF.png
