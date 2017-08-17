Introduction
------------
Overview
^^^^^^^^^^^^^^^^^^
This tutorial covers SAXS data processing with RAW. You will learn how to:

*   Process images into scattering profiles
*   Average, subtract and save scattering profiles
*   Find |Rg| and I(0) by Guinier analysis
*   Find molecular weight by four different methods
*   Do Kratky analysis and normalized Kratky analysis
*   Test the similarity of scattering profiles
*   Load and process SEC-SAXS data
*   Carry out singular value decomposition (SVD) and evolving factor analysis (EFA) to evaluate and analyze SEC-SAXS data
*   Merge SAXS/WAXS data from two detectors
*   Carry out Pair-distance distribution analysis – BIFT and GNOM
*   Evaluate ambiguity of 3D shape reconstructions - AMBIMETER
*   Do 3D reconstructions of bead models - DAMMIF and DAMAVER
*   Calibrate RAW for integrating images
*   Mask images for integration
*   Set up normalization and save processing settings
*   Set absolute scaling in RAW using water and glassy carbon
*   Set a molecular weight standard in RAW

:ref:`Section 1 <section1>` covers basic processing with RAW, and
:ref:`Section 2 <section2>` covers advanced processing with RAW.
:ref:`Section 3 <section3>` covers how to set up RAW for integrating images for those who do not already have a configuration file.


Requirements
^^^^^^^^^^^^
*  BioXTAS RAW >= v1.3.0 (most recent is best).

    *   Install instructions are available from:
        `https://sourceforge.net/projects/bioxtasraw/ <https://sourceforge.net/projects/bioxtasraw/>`_

.. _tutorialdata:

*   Tutorial data.

    *   Available from:
        `https://sourceforge.net/projects/bioxtasraw/files/?source=navbar <https://sourceforge.net/projects/bioxtasraw/files/?source=navbar>`_

*   ATSAS programs, >= v2.8.0 (for :ref:`Section 2 <section2>` of the tutorial only).

    *   Download and installation instructions are available from:
        `http://www.embl-hamburg.de/biosaxs/download.html <http://www.embl-hamburg.de/biosaxs/download.html>`_

    *   Requires a free registration for academic users. Industrial users must pay to use.


Other useful materials
^^^^^^^^^^^^^^^^^^^^^^^
#.  An overview and tutorial of RAW produced by Jesse Hopkins for SBGrid, which can be viewed here:
    `https://youtu.be/XGnJDs3N2MI <https://youtu.be/XGnJDs3N2MI>`_

#.  There are RAW tutorial videos produced by Richard Gillilan, which can be viewed here:
    `http://bit.ly/bioxtast <http://bit.ly/bioxtast>`_. Data for these tutorial videos is available here:
    `http://bit.ly/bioxtasd <http://bit.ly/bioxtasd>`_.

#.  On data collection, molecular weight estimation, and data analysis: Skou, Gillilan, and Ando (2014) Nature Protocols, 9,1727–1739.

#.  On publication guidelines: Jacques, Guss, Svergun, & Trewhella (2012). Acta Cryst D, 68(Pt 6), 620–626.

#.  Uniqueness of ab initio shape determination in small-angle scattering. V. V. Volkov and D. I. Svergun. Journal of Applied Crystallography (2003) 36, 860-864.

#.  Small Angle X-ray Scattering as a Complementary Tool for High-Throughput Structural Studies. Thomas Grant et al. Biopolymers (2011) 95, 517-530.

#.  Ambiguity assessment of small-angle scattering curves from monodisperse systems. M. V. Petoukhov and D. I. Svergun. Acta Crystallographica D (2015) 71, 1051-1058.

#.  ATSAS resources:

    *   Manuals: `http://www.embl-hamburg.de/biosaxs/manuals/ <http://www.embl-hamburg.de/biosaxs/manuals/>`_
    *   User forum: `http://www.saxier.org/forum/ <http://www.saxier.org/forum/>`_

Notes
^^^^^^
If you are only interested in using RAW to process data, and are not interested in how to set up RAW to calibrate your data, you do not need to look at :ref:`Section 3 <section3>`.


RAW depends on user feedback to get better. If you have questions, find bugs, or think a part of this tutorial is unclear, please let the developers know. The best way to do this is via the RAW google group:
`http://bit.ly/rawhelp <http://bit.ly/rawhelp>`_


You can find additional developer contact information on the RAW website:
`https://sourceforge.net/projects/bioxtasraw/ <https://sourceforge.net/projects/bioxtasraw/>`_


.. |Rg| replace:: R\ :sub:`g`
