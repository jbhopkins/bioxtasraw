Guinier analysis
^^^^^^^^^^^^^^^^^^^^^^^^
.. _s1p2:

Recall Guinier’s approximation at low-*q*\ : :math:`I(q)\approx I(0) \exp(-R_g^2 q^2 /3)`.

|Rg| and I(0) can be determined by performing a linear fit in the Guinier plot (a plot of
:math:`\ln(I)` vs. :math:`q^2`). The fitting region should normally have :math:`q_{max}R_g<1.3`
for globular proteins or :math:`q_{max}R_g<1.0` for rod-like proteins. This
fitting region is called the "Guinier region."


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
        then |Rg| is in Å), while the two :math:`qR_g` boxes give, left to right,
        :math:`q_{min}R_g` and :math:`q_{max}R_g` respectively.

    |guinier_gi_png|

#.  In the "Control" panel, you’ll see that n_min is 0. This means RAW has
    used all of the low q for the Guinier fit. You can see a little dip in the
    residual at the lowest q values, use the arrow buttons next to
    the n_min box to adjust it up several points to remove that dip and check whether
    the |Rg| changes. Once you're done return n_min to 0.

#.  In the "Parameters" panel, note that :math:`q_{max}R_g` is only ~1.14. Recall that for globular
    proteins like GI, it is typical to have :math:`q_{max}R_g` ~1.3. Adjust n_max until that is
    the case, watching what happens to the |Rg| and the residual.

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

**Aside: Criteria for a good Guinier region**

For a globular protein, you are looking for three essential components in your Guinier fit:

*   :math:`q_{min}R_g<1.0`. This states that the minimum q of your fit, q\ :sub:`min`, times
    the |Rg|  of your fit should be less than 1.0. This criteria ensures you
    have enough q range to properly estimate the |Rg| and I(0) values.

*   :math:`q_{max}R_g<1.3`. This states that the maximum q of your fit, q\ :sub:`max`,
    times the |Rg| of your fit should be less than 1.3. This criteria
    ensures you remain in the linear range of the Guinier approximation
    for the fit.

*   Residuals should be flat and randomly distributed about zero. If
    your residuals have a ‘smile’ (above zero near start and end of fit,
    below in the middle), or a ‘frown’ (below zero near start and end
    of fit, above in the middle), it indicates you have non-ideal data.
    The ‘smile’ is characteristic of aggregation, the ‘frown’ characteristic
    of interparticle repulsion.

Additionally, you shouldn’t have to excluded very many points at the start of the
fit. A few is generally fine, as the points nearest the beamstop can be noisy
(depending on the exact details of the measurement). If you have a small amount
of aggregation or repulsion it may manifest as a small upturn or downturn at low
q that, once excluded, doesn’t seem to affect the fit residual (i.e. no ‘smile’
or ‘frown’). In these cases, you may proceed, but exercise caution as your data
may be subtly affected. Also, be sure whoever you present the data to understands
you observed these effects and decided to proceed with analysis despite the
non-ideality.

Note that for non-globular systems, such as rod-like shapes, the fitting range
shifts as the linear region of the Guinier approximation shifts.

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
