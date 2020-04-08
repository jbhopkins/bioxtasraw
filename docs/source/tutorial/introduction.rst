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
*   Carry out singular value decomposition (SVD) and evolving factor analysis (EFA)
    to evaluate and analyze SEC-SAXS data
*   Do baseline correction on SEC-SAXS data
*   Merge SAXS/WAXS data from two detectors
*   Carry out Pair-distance distribution analysis (BIFT and GNOM)
*   Evaluate ambiguity of 3D shape reconstructions (AMBIMETER)
*   3D reconstructions with bead models (DAMMIF/N and DAMAVER)
*   3D reconstructions with electron density (DENSS)
*   Calibrate RAW for integrating images
*   Mask images for integration
*   Set up normalization and save processing settings
*   Set absolute scaling in RAW using water and glassy carbon
*   Set a molecular weight standard in RAW

:ref:`Section 1 <section1>` covers basic processing with RAW, and
:ref:`Section 2 <section2>` covers advanced processing with RAW.
:ref:`Section 3 <section3>` covers how to set up RAW for integrating images for
those who do not already have a configuration file.


This tutorial is focused on how to use RAW, it is not necessarily a tutorial
on best practices for SAXS data processing.

Requirements
^^^^^^^^^^^^
*  BioXTAS RAW >= v2.0.0 (most recent is best).

    *   :ref:`Install instructions <install>`

.. _tutorialdata:

*   Tutorial data.

    *   Available from:
        `https://sourceforge.net/projects/bioxtasraw/files/?source=navbar <https://sourceforge.net/projects/bioxtasraw/files/?source=navbar>`_

.. _atsas:

*   ATSAS programs, >= v2.8.0 (for parts of :ref:`Section 2 <section2>` of the tutorial only).

    *   Download and installation instructions are available from:
        `https://www.embl-hamburg.de/biosaxs/download.html <https://www.embl-hamburg.de/biosaxs/download.html>`_

    *   Requires a free registration for academic users. Industrial users must pay to use.

Other useful materials
^^^^^^^^^^^^^^^^^^^^^^^
#.  `Video lectures from the BioCAT Everything BioSAXS 5 workshop, <https://www.youtube.com/playlist?list=PLbPNI520xTsEYbJk8V0BNQ461xnG6tpRW>`_
    which can help you learn more about best practices for SAXS data processing.

#.  An overview and tutorial of RAW produced by Jesse Hopkins for SBGrid, which can be viewed here:
    `https://youtu.be/XGnJDs3N2MI <https://youtu.be/XGnJDs3N2MI>`_

#.  There are RAW tutorial videos produced by Richard Gillilan, which can be viewed here:
    `https://bit.ly/bioxtast <https://bit.ly/bioxtast>`_. Data for these tutorial videos is available here:
    `https://bit.ly/bioxtasd <https://bit.ly/bioxtasd>`_.

#.  ATSAS resources:

    *   Manuals: `https://www.embl-hamburg.de/biosaxs/manuals/ <https://www.embl-hamburg.de/biosaxs/manuals/>`_
    *   User forum: `https://www.saxier.org/forum/ <https://www.saxier.org/forum/>`_

#.  Electron density (DENSS) resources available at `DENSS.org <denss.org>`_

    *   Particularly useful is the section on `visualizing the results and aligning with known structures <https://www.tdgrant.com/denss/tips/>`_.

Notes
^^^^^^
If you are only interested in using RAW to process data, and are not interested
in how to set up RAW to calibrate your data, you do not need to look at
:ref:`Section 3 <section3>`.


RAW depends on user feedback to get better. If you have questions, find bugs,
or think a part of this tutorial is unclear, :ref:`please let the developers know.
<contactus>`


You can find additional developer contact information on the RAW website:
`https://sourceforge.net/projects/bioxtasraw/ <https://sourceforge.net/projects/bioxtasraw/>`_


.. |Rg| replace:: R\ :sub:`g`
