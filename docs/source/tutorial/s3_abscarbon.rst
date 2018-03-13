Setting absolute scale with glassy carbon
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.. _s3p6:

This section teaches you how to set up absolute scale using glassy carbon (NIST SRM 3600)
as a reference. It assumes you have completed :ref:`Parts 1 <s3p1>` (or :ref:`2 <s3p2>`\ ),
:ref:`3 <s3p3>` and :ref:`4 <s3p4>`\ . Note that you can use water (:ref:`Part 5 <s3p5>`) or
glassy carbon for absolute scale calibration in RAW.

There are two ways to use glassy carbon as a standard in RAW. One way follows the NIST
protocol, and will deliver the most accurate results. However, this method depends on
all measurements having reliable flux measurements upstream and downstream of the sample.
It also requires accurate measurements of the background of the glassy carbon measurement
and the sample measurements. The second way is more similar to that used by water, in that
it essentially ignores the background (assumes it to be small). This approach only requires
regular normalization and a single measurement of the background for the glassy carbon sample.


**The simple approach, “ignoring” background:**

#.  Load/use the settings from part 4 (without absolute scale set from water, part 5).

#.  Plot all of the **glassy_carbon_41_001_000x.tiff** files, where x is 0-9, on the main plot.

    *   *Tip:* :ref:`Section 1 Part 1 <s1p1>` of this tutorial document teaches you how to do this.

#.  Average the **glassy_carbon** files you just loaded. Save the average in
    the **calibration_data** folder.

#.  Open the Options window by selecting “Advanced Options” in the Options menu.

#.  Click on the Absolute Scale section in the options list on the left.

    |100002010000032000000255A94EE51014E73548_png|

#.  Click on the Glassy carbon “Set” button and select the **A_glassy_carbon_41_001_0000.dat** file.

#.  Set the Sample thickness to 1.5 mm.

    |100002010000024A0000010255684CF81FEA93EF_png|

#.  Click “Calculate” button. You should get something near 0.0014.

    *   *Note:* It is important that you not change your normalization settings once
        you have set the absolute scaling constant. If you do, you will have to recalculate
        the absolute scaling constant. Also, make sure absolute scale is turned off before
        you calculate the scale constant, otherwise you will get a bad scaling constant
        (see the manual for details).

#.  Check the “Normalize processed data to absolute scale using glassy carbon” checkbox.

#.  Click “OK” to exit the advanced options panel, saving the changes.

    |100002010000031E000002533D65082AC93CE448_png|

#.  Save the settings for future use.

**The NIST approach:**

*Important note:* All of the normalization (including flux, transmission, etc) happens
through the absolute scale panel. You shouldn’t have anything set in the Normalization
panel (unless you are doing something like subtracting off a constant pedestal from the
image).

#.  Load/use the settings from part 4 (without absolute scale set from water, part 5).

#.  Open the Options window by selecting “Advanced Options” in the Options menu.

#.  Click on the Normalization section in the options list on the left.

#.  Remove any/all items in the Normalization List by highlighting them in the list
    and clicking the “Delete” button.

    |100002010000031F0000025307BE652194AFBF84_png|

#.  Turn off any absolute scaling already in place.

#.  Click on the Calibration section in the options list on the left.

#.  Change the “Start plots at q-point number” to 0.

    |1000020100000319000000E3F41DC6D4D282F31B_png|

#.  Click “OK” to exit the advanced options window and save the changes.

#.  Plot the **glassy_carbon_41_001_0000.tiff** file.

    *   *Tip:* :ref:`Section 1 Part 1 <s1p1>` of this tutorial document teaches you how
        to do this.

#.  Save the **glassy_carbon** profile in the **calibration_data** folder.

#.  Plot, average, and save the **vac_37_001_000x.tiff** and ** MT2_48_001_000x.tiff **
    files, where x is 0-9.

    *   *Tip:* Because you aren’t normalizing by beam intensity, these averages may have
        profiles that are not similar (see :ref:`Section 1 Part 6 <s1p6>`). In that case,
        average just the similar profiles.

#.  Open the Options window and select the Absolute Scale section.

#.  Uncheck the Ignore background checkbox.

    |100002010000031E000002572EF4280A9EB5D279_png|

#.  Click the Glassy carbon “Set” button and select the **glassy_carbon_41_001_0000.dat** file.

#.  Click the Glassy carbon background “Set” button and select the **A_vac_37_001_0000.dat** file.

#.  Click the Sample background “Set” button and select the **A_MT2_48_001_0000.tiff** file.

#.  Set the Sample thickness to 1.5 mm.

#.  Set the Upstream counter to I1.

#.  Set the Downstream counter to I3.

#.  Click the “Calculate” button. You should get an absolute scaling constant near 198.

    *   *Note:* This approach will only work if the .dat files you select for the glassy
        carbon, glassy carbon background, and sample background contain the upstream and
        downstream counter values. This happens automatically with RAW. Otherwise, you should
        use images, which will have more noise, but should allow RAW to find all of the
        appropriate counter values.

    *   *Note:* It is important that you not change your normalization settings once you
        have set the absolute scaling constant. If you do, you will have to recalculate the
        absolute scaling constant. Also, make sure absolute scale is turned off before you
        calculate the scale constant, otherwise you will get a bad scaling constant (see the
        manual for details).

    |100002010000031F00000254EC8C0C5D987D9510_png|

#.  Check the “Normalize processed data to absolute scale using glassy carbon” checkbox.

#.  Click on the Calibration section in the options list on the left.

#.  Change the “Start plots at q-point number” to 13.

#.  Click “OK” to exit the advanced options panel, saving the changes.

#.  Save the settings for future use.


**Comparison note:**

We find that for the example data given here, the two methods of glassy carbon calibration
agree within ~1.5%. The best approach depends on how strong your background scattering is
relative to the rest of the scattering in the system.



.. |100002010000032000000255A94EE51014E73548_png| image:: images/100002010000032000000255A94EE51014E73548.png

.. |100002010000024A0000010255684CF81FEA93EF_png| image:: images/100002010000024A0000010255684CF81FEA93EF.png

.. |100002010000031E000002533D65082AC93CE448_png| image:: images/100002010000031E000002533D65082AC93CE448.png

.. |100002010000031F0000025307BE652194AFBF84_png| image:: images/100002010000031F0000025307BE652194AFBF84.png

.. |1000020100000319000000E3F41DC6D4D282F31B_png| image:: images/1000020100000319000000E3F41DC6D4D282F31B.png

.. |100002010000031E000002572EF4280A9EB5D279_png| image:: images/100002010000031E000002572EF4280A9EB5D279.png

.. |100002010000031F00000254EC8C0C5D987D9510_png| image:: images/100002010000031F00000254EC8C0C5D987D9510.png
