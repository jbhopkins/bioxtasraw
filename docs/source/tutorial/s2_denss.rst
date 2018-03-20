3D reconstruction with electron density – DENSS and EMAN2 in RAW
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
A new, exciting method for doing 3D shape reconstructions in SAXS yields actual
electron density, rather than bead models. There are many potential advantages to this,
but one significant one is easy handling of systems like RNA-Protein complexes or
membrane proteins surrounded by lipids or detergents, which have more than one electron
density. Bead models typically only have two (molecule and solvent) or three bead densities,
and so typically fail to reconstruct these complex objects. `DENSS <http://denss.org>`_ has
been fully implemented in RAW and will be used to recontruct these electron densities.
In order to align and average these densities, EMAN2 will be used. Note that you need
:ref:`EMAN2 installed <eman2>` to do this part of the tutorial.

**IMPORTANT NOTE:** Unfortunately, the EMAN2 package doesn't work properly on Windows.
Windows users can still use RAW to generate electron densities, but they cannot
create a consensus average or filter out enantiomers. Mac OS (or OS X) and Linux
users can do everything described in this tutorial.


#.  Clear all of the data in RAW. Load the **lysozyme.out** file that you saved in the
    **atsas_data** folder in a previous part of the tutorial.

    *   *Note:* If you haven’t done the previous part of the tutorial, or forgot to save
        the results, you can find the **lysozyme.out** file in the
        **atsas_data/lysozyme_complete** folder.

#.  Right click on the **lysozyme.out** item in the IFT list. Select the “Electron Density (DENSS)” option.

#.  Running DENSS generates a lot of files. Click the “Select/Change Directory” button,
    make a new folder in the **atsas_data** directory called **lysozyme_denss** and select
    that folder.

#.  Change the number of reconstructions to 5 and the mode to Fast.

    *   *Note:* It is generally recommended that you do at least 20 reconstructions. However,
        for the purposes of this tutorial, 5 are enough.

    *   *Note:* For final reconstructions for a paper, DENSS should be run in Slow mode.
        For this tutorial, or for obtaining an initial quick look at results, Fast mode is fine.

#. Uncheck the "Filter enantiomers (EMAN2)" checkbox.

    *   *Note:* For final reconstructions for a paper, you should filter enantiomers.  However, it
        is quite slow, so for the purposes of this tutorial we won't do it.

    *   *Note:* SAXS data can't determine between enantiomers, so all this does is ensure that
        the reconstructions and averaging are done on the most similar enantiomers. There
        is no guarantee that this matches the enantiomer in solution.

    |denss_run_tab_png|

#.  Click the “Start” button.

    *   *Note:* The status panel will show you the overall status of the reconstructions.
        You can look at the detailed status of each run by clicking the appropriate tab in
        the log panel.

#.  Note that by default the envelopes are aligned and averaged using EMAN2.

    *   Some settings are accessible in the panel, and all settings can be changed in the
        advanced settings panel.

#.  Wait for all of the DENSS runs and EMAN2 averaging to finish. Depending
    on the speed of your computer this could take a bit.

#.  Once the reconstructions are finished, the window should automatically switch to the
    results tab. If it doesn’t, click on the results tab.

    |denss_results_png|

#.  The results panel summarizes the results of the reconstruction runs. At the top of the
    panel there is the ambimeter evaluation of how ambiguous the reconstructions might be
    (see previous tutorial section). If EMAN2 averaging was run there is an estimate of the
    reconstruction resolution based on the Fourier shell correlation.

#.  For each individual model there are plots of: the original data and the model data (scattering from density);
    the residual between the original data and the model data; and chi squared, |Rg| and support volume
    vs. refinement step.

    *   Verify that the residual between the actual data and the model data is small.

    *   Check that the chi squared, |Rg|, and support volume have all plateaued (converged)
        by the final steps.

#.  If the plots were averaged, the average tab will display the Fourier shell correlation
    vs. resolution.

    *   *Note:* The reconstruction resolution is taken as the resolution in angstrom where the
        correlation first crosses 0.5.

    |denss_fsc_png|

#.  Click the “Save Results Summary” button to save the results summary as a **.csv** file and
    save the summary plots as a multi-page pdf file.

#.  Click the “Close” button when you are finished looking at the results and reconstructions.

#.  The results from the individual DENSS runs are saved in the selected output folder as
    **<prefix>_xx.mrc** where *xx* corresponds to the run number: 01, 02, etc. For this
    tutorial that would be **lysozyme_01.mrc**, **lysozyme_02.mrc**, etc.

#.  If averaging was done, final average density is saved in the selected output
    folder as **<prefix>_aver.mrc**. For this turotial, that would be **lysozyme_aver.mrc**

    *   *Note:* **.mrc** files can be opened in Chimera and pyMOL. For tips about how to
        visualize the density and align it with known structures see the appropriate
        sections here: `http://www.tdgrant.com/denss/tips/ <http://www.tdgrant.com/denss/tips/>`_.
        When looking at this page, please note that RAW does the conversion from hdf5 to mrc
        for you, so there's no need to do this, i.e. you can skip the first paragraph of the
        evaluating the results section.



.. |denss_run_tab_png| image:: images/denss_run_tab.png

.. |denss_results_png| image:: images/denss_results_tab.png

.. |denss_fsc_png| image:: images/denss_fsc.png

.. |Rg| replace:: R\ :sub:`g`
