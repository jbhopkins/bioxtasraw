Assessing ambiguity of 3D shape information - AMBIMETER in RAW
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
It is impossible to determine a provably unique three-dimensional shape from a scattering
profile. This makes it important to determine what degree of ambiguity might be expected
in our reconstructions. The program AMBIMETER from the ATSAS package does this by comparing
the measured scattering profile to a library of scattering profiles from relatively simple
shapes. The more possible shapes that could have generated the scattering profile, the greater
ambiguity there will be in the reconstruction. We will use RAW to run AMBIMETER. Note that you need
:ref:`ATSAS installed <atsas>` to do this part of the tutorial.

#.  Clear all of the data in RAW. Load the **lysozyme.out** file that you saved in the
    **atsas_data** folder in a previous part of the tutorial.

    *   *Note:* If you haven’t done the previous part of the tutorial, or forgot to save
        the results, you can find the **lysozyme.out** file in the **atsas_data/lysozyme_complete**
        folder.

    |ift_panel_png|

#.  Right click on the **lysozyme.out** item in the IFT list. Select the “AMBIMETER” option.

#.  The new window will show the results of AMBIMETER. It includes the number of shape categories
    that are compatible with the scattering profile, the ambiguity score (a-score) (log base 10 of the
    number of shape categories), and the AMBIMETER interpretation of whether or not you can
    obtain a unique 3D reconstruction.

    *   According to the `original paper <https://doi.org/10.1107/S1399004715002576>`_,
        "an a-score below 1.5 practically guarantees a unique ab initio shape determination,
        whereas when the a-score is in the range 1.5–2.5 care should be taken, perhaps involving
        cluster analysis, and for a-scores exceeding 2.5 unambiguous reconstruction without
        restrictions (for example, on symmetry and/or anisometry) is highly unlikely."

    *   *Note:* AMBIMETER can also save the compatible shapes (either all or just the best
        fit). You can do that by selecting the output shapes to save, giving it a save
        directory, and clicking run. We won’t be using those shapes in this tutorial.

    |10000201000001C00000020ABF9AC84A21364E29_png|

#.  Click “OK” to exit the AMBIMETER window.



.. |10000201000001C00000020ABF9AC84A21364E29_png| image:: images/10000201000001C00000020ABF9AC84A21364E29.png

.. |ift_panel_png| image:: images/ift_panel.png
