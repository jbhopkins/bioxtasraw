Guinier analysis
^^^^^^^^^^^^^^^^^^^^^^^^
.. _s1p2:

This tutorial covers how to use RAW for Guinier analysis. This is not a tutorial
on basic principles and best practices for doing a Guinier analysis. For that,
please see the :ref:`SAXS tutorial <saxs_guinier>`.

A video version of this tutorial is available:

.. raw:: html

    <style>.embed-container { position: relative; padding-bottom: 56.25%; height: 0; overflow: hidden; max-width: 100%; } .embed-container iframe, .embed-container object, .embed-container embed { position: absolute; top: 0; left: 0; width: 100%; height: 100%; }</style><div class='embed-container'><iframe src='https://www.youtube.com/embed/B3xJP40Z8Ww' frameborder='0' allowfullscreen></iframe></div>

The written version of the tutorial follows.


#.  In RAW, right click (ctrl click on macs without a right mouse button) on the
    subtracted GI scattering profile in the Profiles list and select "Guinier fit".
    The Guinier fit window will open.

    *   *Note:* You can also click the 'Guinier' button at the bottom of the Profiles
        control panel.

    |guinier_open_png|

#.  In the Guinier window, the top plot shows you the Guinier plot and the fit,
    while the bottom plot shows you the residual of the fit.

    *   *Note:* RAW automatically tries to find the best Guinier region for you
        when the Guinier window is opened for the first time.

    *   *Note:* The |Rg| value is in units of 1/q (e.g. if q is in Å\ :sup:`-1`
        then |Rg| is in Å).

    |guinier_gi_png|

#.  In the "Control" panel, you’ll see that n_min is 8. This means RAW has
    skipped the first few low q points for the Guinier fit. You can see a little
    dip in the lowest q values, which may be why it was skipped. Use the arrow
    buttons next to the n_min box to adjust it down several points to include that
    dip and check whether the |Rg| changes. Once you're done return n_min to 8.

#.  In the "Parameters" panel, note that :math:`q_{max}R_g` is  ~1.32. Recall that for globular
    proteins like GI, it is typical to have :math:`q_{max}R_g` ~1.3. Adjust
    n_max down slightly until that is the case, watching what happens to the |Rg|
    and the residual.

    *   *Question:* The literature radius of gyration for GI is 32.7 Å. How does yours compare?

#.  RAW also provides an estimate of the uncertainty in both the |Rg| and I(0) values for
    the Guinier fit, shown in the Uncertainty section.

    *   *Note:* This is the largest of the uncertainties from the fit (standard deviation
        of fit values calculated from the covariance matrix), and either the standard deviation of
        |Rg| and I(0) across all acceptable intervals found by the autorg function
        or an estimated uncertainty in |Rg| and I(0) based on variation of the selected
        interval start and end points.

#.  Click the "OK" button to keep the results.

    *   *Note:* Clicking the "Cancel" button will discard the results.

#.  If you now select the GI scattering profile, in the information panel above
    the control panel you should see the |Rg| and I(0) that you just found.

    |info_panel_png|

    *   *Tip:* Click on the triangle to expand the Guinier info section and see more details
        on the fit.

    |info_expand_png|

#.  Repeat the Guinier analysis for lysozyme.

    *   *Try:* Increase q\ :sub:`min` and/or decrease q\ :sub:`max` to verify that the |Rg|
        does not change significantly in the Guinier region.

    *   *Tip:* If you hover your mouse cursor over the info icon (just left of the target icon)
        for a given scattering profile it should show you the |Rg| and I(0) of your Guinier analysis.

|lys_guinier_png|


.. |guinier_open_png| image:: images/guinier_open.png
    :width: 400 px
    :target: ../_images/guinier_open.png

.. |guinier_gi_png| image:: images/guinier_gi.png
    :target: ../_images/guinier_gi.png

.. |info_panel_png| image:: images/info_panel.png
    :width: 400 px
    :target: ../_images/info_panel.png

.. |info_expand_png| image:: images/info_expand.png
    :width: 400 px
    :target: ../_images/info_expand.png

.. |lys_guinier_png| image:: images/guinier_lys.png
    :target: ../_images/guinier_lys.png


.. |Rg| replace:: R\ :sub:`g`
