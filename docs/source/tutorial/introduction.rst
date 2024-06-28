Introduction
------------
.. _raw_tutorial:

Overview
^^^^^^^^^^^^^^^^^^
This tutorial covers SAXS data processing with RAW. You will learn how to:

*   Process images into scattering profiles
*   Average, subtract and save scattering profiles
*   Find |Rg| and I(0) by Guinier analysis
*   Find molecular weight by six different methods
*   Do Kratky analysis and dimensionless Kratky analysis
*   Compare scattering profiles using residuals, ratios, and statistical tests
*   Load and process SEC-SAXS data
*   Carry out singular value decomposition (SVD) and evolving factor analysis (EFA)
    to evaluate and deconvolve SEC-SAXS data
*   Carry out regularized alternating least squares (REGALS) analysis to
    deconvolve SAXS data.
*   Do baseline correction on SEC-SAXS data
*   Merge SAXS/WAXS data from two detectors
*   Carry out Pair-distance distribution analysis (BIFT, DIFT and GNOM)
*   Evaluate ambiguity of 3D shape reconstructions (AMBIMETER)
*   3D reconstructions with bead models (DAMMIF/N and DAMAVER)
*   3D reconstructions with electron density (DENSS)
*   Align 3D reconstructions with high resolution models (DENSS and CIFSUP)
*   Calculate theoretical scattering profiles from models and fit the
    theoretical scattering against experimental data (CRYSOL and PDB2SAS)
*   Save your analysis information and plots
*   Calibrate RAW for integrating images
*   Mask images for integration
*   Set up normalization and save processing settings
*   Set absolute scaling in RAW using water and glassy carbon
*   Set a molecular weight standard in RAW

:ref:`Section 1 <section1>` covers basic processing with RAW, and
:ref:`Section 2 <section2>` covers advanced processing with RAW.
:ref:`Section 3 <section4>` covers saving plots and plot data and opening
data in other programs.
:ref:`Section 4 <section3>` covers how to set up RAW for integrating images for
those who do not already have a configuration file.


This tutorial is focused on how to use RAW, it is not necessarily a tutorial
on best practices for SAXS data processing. The :ref:`SAXS tutorial <saxs_tutorial>`
covers some basic processing and analysis best practices.

Requirements
^^^^^^^^^^^^
*  BioXTAS RAW >= v2.3.0 (most recent is best).

    *   :ref:`Install instructions <install>`

.. _tutorialdata:

*   Tutorial data.

    *   Available from:
        `https://sourceforge.net/projects/bioxtasraw/files/?source=navbar
        <https://sourceforge.net/projects/bioxtasraw/files/?source=navbar>`_

.. _atsas:

*   ATSAS programs, >= v3.1.1 (for parts of :ref:`Section 2 <section2>` of
    the tutorial).

    *   Download and installation instructions are available from:
        `https://github.com/biosaxs-com/atsas-community <https://github.com/biosaxs-com/atsas-community>`_

    *   Requires a free registration for academic users. Proprietary users must pay to use.

Other useful materials
^^^^^^^^^^^^^^^^^^^^^^^
#.  `Video lectures from BioCAT's Everything BioSAXS workshops,
    <https://www.youtube.com/playlist?list=PLbPNI520xTsEYbJk8V0BNQ461xnG6tpRW>`_
    which can help you learn more about best practices for SAXS data processing.

#.  Most tutorial sections have a linked video tutorial. A full playlist of the
    videos is available here:

    .. raw:: html

        <style>.embed-container { position: relative; padding-bottom: 56.25%; height: 0; overflow: hidden; max-width: 100%; } .embed-container iframe, .embed-container object, .embed-container embed { position: absolute; top: 0; left: 0; width: 100%; height: 100%; }</style><div class='embed-container'><iframe src='https://www.youtube.com/embed/videoseries?list=PLm39Taum4df4alFnacOOr1RWgylwiTWED' frameborder='0' allowfullscreen></iframe></div>

#.  ATSAS resources:

    *   Manuals: `https://biosaxs-com.github.io/atsas/4.0.0/manuals/ <https://biosaxs-com.github.io/atsas/4.0.0/manuals/>`_
    *   User forum: `https://github.com/biosaxs-com/atsas-community/discussions <https://github.com/biosaxs-com/atsas-community/discussions>`_

#.  Electron density (DENSS) resources available at `DENSS.org <denss.org>`_

    *   Particularly useful is the section on `visualizing the results and aligning with known structures <https://www.tdgrant.com/denss/tips/>`_.

Notes
^^^^^^
If you are only interested in using RAW to process data, and are not interested
in how to set up RAW to calibrate your data, you do not need to look at
:ref:`Section 4 <section3>`.


RAW depends on user feedback to get better. If you have questions, find bugs,
or think a part of this tutorial is unclear, :ref:`please let the developers know.
<contactus>`


You can find additional developer contact information on the RAW website:
`https://sourceforge.net/projects/bioxtasraw/ <https://sourceforge.net/projects/bioxtasraw/>`_


.. |Rg| replace:: R\ :sub:`g`
