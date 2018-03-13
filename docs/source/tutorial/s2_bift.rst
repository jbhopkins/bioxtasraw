Pair-distance distribution analysis – BIFT in RAW
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
RAW also has a built in method for determining the P(r) function using a Bayesian IFT method.
This has the advantage of only have one possible solution. More information on this method can
be found in the RAW paper and manual and references therein.

#.  Right click on the lysozyme profile in the Manipulation list you loaded in Part 1 and
    select “BIFT”.

    |100002010000031E00000257E806280132469D47_png|

#.  The BIFT panel has plots on the right. These show the P(r) function (top panel),
    the data (bottom panel, blue points) and the fit line (bottom panel, red line).

#.  On the left of the BIFT panel are the controls and the resulting parameters. Note that
    in this case you do not control the |Dmax| value, the BIFT method finds that for you
    automatically.

#.  Click OK to exit the BIFT window. This saves the results into the RAW IFT panel.

#.  Click on the IFT Control and Plot tabs. This will display the BIFT output you just generated.
    Save the **lysozyme.ift** item in the **standards_data** folder.

*Note:* As of now, BIFT output from RAW is not compatible with DAMMIF or other ATSAS programs.
However, it is compatible with electron density determination via DENSS.



.. |100002010000031E00000257E806280132469D47_png| image:: images/100002010000031E00000257E806280132469D47.png

.. |Dmax| replace:: D\ :sub:`max`
