Advanced SEC-SAXS processing – Baseline correction
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Sometimes SEC data shows a baseline drift. This can be due either to instrumental
changes (such as beam drift), or changes in the measured system, such as capillary
fouling. RAW provides the ability to correct for these forms of baseline drift
using either a linear or integral baseline method. The linear baseline method
is best for instrumental drifts, while the integral baseline method is best
for capillary fouling.

#.  Clear all of the data in RAW. Load the **baseline.sec** SEC data in the
    **sec_data** folder. Note that this is the same as what :ref:`previously
    saved <s1p7>` in an earlier part of the tutorial.

#.  Open the LC Series analysis panel.

#.  Use the triangle to expand the Baseline Correction section.

    |lc_analysis_baseline_expand_png|

#.  Right click on the **phehc_sec.sec** item in the Series list. Select the “SVD” option.

#.  The SVD window will be displayed. On the left are controls, on the right are plots of
    the value of the singular values and the first autocorrelation of the left and right
    singular vectors.

    *   *Note:* Large singular values indicate significant components. What matters is the relative
        magnitude, that is, whether the value is large relative to the mostly flat/unchanging
        value of high index singular values.

    *   *Note:* A large autocorrelation indicates that the singular vector is varying smoothly,
        while a low autocorrelation indicates the vector is very noisy. Vectors corresponding to
        significant components will tend to have autocorrelations near 1 (roughly, >0.6-0.7) and
        vectors corresponding to insignificant components will tend to have autocorrelations near 0.



.. |lc_analysis_baseline_expand_png| image:: images/lc_analysis_baseline_expand.png
