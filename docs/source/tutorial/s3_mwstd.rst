Setting a molecular weight standard
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
One method for determining molecular weight from a scattering profile is comparison to a known
scattering profile with known molecular weight. This part will teach you how to set that known
standard in RAW.

#.  Load/use the settings from :ref:`Parts 4 <s3p4>`\ , :ref:`5 <s3p5>`\ , or :ref:`6 <s3p6>`\ .

#.  Plot all of the **lysbuf2_52_001_000x.tiff** files, where x is 0-9, on the main plot.

    *   *Tip:* :ref:`Section 1 Part 1 <s1p1>` of this tutorial document teaches you how to do this.

#.  Average the **lysbuf2** files you just loaded. Save the average in the
    **calibration_data** folder.

#.  Repeat steps 2-3 for the **lys2_52_001_000x.tiff** files.

#.  Subtract the averaged buffer profile (**lysbuf2**\ ) from the averaged sample profile
    (**lys2**\ ).

    *   *Tip:* :ref:`Section 1 Part 1 <s1p1>` of this tutorial document teaches you how to do this.

#.  Select the subtracted profile by clicking on it. In the information panel, set the concentration
    in the Conc box to 4.14 (this is concentration in mg/ml).

    |config_mwstd1_png|

#.  Perform a Guinier fit on the subtracted profile.

    *   *Tip:* :ref:`Section 1 Part 2 <s1p2>` of this tutorial document teaches you how to do this.

#.  Right click on the subtracted profile and select the “Other Operations->Use as MW Standard” option.

#.  Enter the molecular weight of the standard in kDa in the box that appears. For this lysozyme
    sample, the molecular weight is 14.3 kDa.

    |config_mwstd2_png|

#.  Click “OK” to save the molecular weight standard.

#.  Save the settings for future use.


.. |config_mwstd1_png| image:: images/config_mwstd1.png

.. |config_mwstd2_png| image:: images/config_mwstd2.png
    :width: 450 px
