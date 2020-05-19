WAXS processing and merging
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Several SAXS beamlines use two (or more) detectors to collect different q regions. For example,
the MacCHESS G1 beamline used dual Pilatus detectors to measure SAXS and WAXS from *q* ~0.008 – 0.75
Å\ :sup:`-1`\ . The SAXS detector has *q* ~< 0.25 Å\ :sup:`-1` and the wide-angle scattering
(WAXS) data has *q* >~ 0.25 Å\ :sup:`-1`\ . All of the data that you have been working with
so far has been SAXS data. Some experiments can make use of the WAXS data. In this part of the
tutorial you will learn the basics of processing it.

A video version of this tutorial is available:

.. raw:: html

    <iframe width="560" height="315" src="https://www.youtube.com/embed/UZCGXjQdk7Y" frameborder="0" allow="accelerometer; autoplay; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>

The written version of the tutorial follows.

#.  Clear any data in RAW.

#.  Navigate to the **standards_data** and load the **WAXS.cfg** file.

#.  Plot the **lysbuff2** **PIL3** and **lys2** **PIL3** files. These are the images from the WAXS
    detector. Average these files and create a subtracted WAXS scattering profile.

    *   *Tip:* Filenames should be **lysbuff2_<stuff>_PIL3_<stuff>.tiff**
        and **lys2_<stuff>_PIL3_<stuff>.tiff**\ .

#.  Load the saved subtracted SAXS scattering profile for the lysozyme standards data.

    *   *Note:* You should have saved it in the **standards_data** folder, and it is likely
        named **S_A_lys2_A9_17_001_0000.dat**\ .

#.  Move the SAXS scattering profile you just loaded to the bottom plot by right clicking
    on it in the Profiles list and selecting “Move to bottom plot.”

#.  The WAXS data is not on the same scale as the SAXS data. For this data, the known scale
    factor to apply is 0.000014 to the WAXS data.

    *   *Note:* The scale factor can be calculated as the ratio of solid angles subtended
        by the pixels on the SAXS and WAXS detectors, plus any scale factor for absolute
        calibration and normalization included for one curve but not the other.

#.  Star the WAXS data. Right click on the SAXS data and select Other Operations -> Merge.
    This will create a new merged scattering profile. The new file will have the
    prefix **M_** to indicate it is a merged file.

    *   *Tip:* If you can’t see it, that’s probably because it appeared on the upper plot,
        and is hidden by the very large intensities of the averaged WAXS files. Either try
        hiding those, or move the Merged curve to the lower plot.
