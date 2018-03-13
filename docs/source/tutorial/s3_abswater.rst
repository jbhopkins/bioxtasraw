Setting absolute scale with water
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.. _s3p5:

This section teaches you how to set up absolute scale using water as a reference. It assumes
you have completed :ref:`Parts 1 <s3p1>` (or :ref:`2 <s3p2>`\ ), :ref:`3 <s3p3>` and
:ref:`4 <s3p4>`. Note that you can use water or glassy carbon (:ref:`Part 6 <s3p6>`)
for absolute scale calibration in RAW.

#.  Using the settings from the previous parts of the tutorial, plot all of the
    **MT2_48_001_000x.tiff** files, where x is 0-9, on the main plot.

    *   *Tip:* :ref:`Section 1 Part 1 <s1p1>` of this tutorial document teaches you
        how to do this.

#.  Average the **MT2** files you just loaded. Save the average in the **calibration_data**
    folder.

    |10000201000003FD000002FDF405DABE73178919_png|

#.  Repeat steps 1 and 2, plotting, averaging and saving, for the **water2_49_001_000x.tiff**
    files.

#.  Open the Options window by selecting “Advanced Options” in the Options menu.

#.  Click on the Absolute Scale section in the options list on the left.

    |100002010000032000000255A94EE51014E73548_png|

#.  Click on the Empty cell “Set” button and select the **A_MT2_48_001_0000.dat**
    file.

#.  Click on the Water sample “Set” button and select the **A_water2_49_001_0000.dat**
    file.

#.  Set the Water temperature to 4 C.

    |100002010000024C000000B45B6C3F21D0977D19_png|

#.  Click the Calculate button to calculate the Absolute Scaling Constant. You should
    get a value near 0.00077.

    *   *Tip:* You can also use images to set the absolute scale. This may give worse
        results, as the signal to noise of the averaged file should be better than for
        a single image.

    *   *Note:* It is important that you not change your normalization settings once you
        have set the absolute scaling constant. If you do, you will have to recalculate
        the absolute scaling constant. Also, make sure absolute scale is turned off before
        you calculate the scale constant, otherwise you will get a bad scaling constant
        (see the manual for details).

    |100002010000017C0000002239FE4A9099163120_png|

#.  Check the “Normalize processed data to absolute scale” checkbox. Click “OK” to
    exit the advanced options window and save the changes.

    |100002010000031B0000025153E03F7B64A2BA9D_png|

#.  Save the settings for later use.



.. |10000201000003FD000002FDF405DABE73178919_png| image:: images/10000201000003FD000002FDF405DABE73178919.png

.. |100002010000032000000255A94EE51014E73548_png| image:: images/100002010000032000000255A94EE51014E73548.png

.. |100002010000024C000000B45B6C3F21D0977D19_png| image:: images/100002010000024C000000B45B6C3F21D0977D19.png

.. |100002010000017C0000002239FE4A9099163120_png| image:: images/100002010000017C0000002239FE4A9099163120.png

.. |100002010000031B0000025153E03F7B64A2BA9D_png| image:: images/100002010000031B0000025153E03F7B64A2BA9D.png
