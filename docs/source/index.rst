BioXTAS RAW
===========

What is BioXTAS RAW?
--------------------

BioXTAS RAW is a GUI based, free, open-source Python program for reduction and analysis
of small-angle X-ray solution scattering (SAXS) data. The software is designed for biological
SAXS data. It is available on Windows, macOS (and OS X), and Linux. It provides an
alternative to closed source programs such as Primus and Scatter for primary data analysis.
Because it can calibrate, mask, and integrate images it also provides an alternative to
synchrotron beamline pipelines that scientists can install on their own computers and use
both at home and at the beamline.

:ref:`Find out how to get it! <install>`

Features
--------

*   Analysis of radius of gyration (|Rg|) and I(0) via Guinier fit.
*   Analysis of molecular weight via I(0) comparison to standards, absolute
    calibration, correlation volume (V\ :sub:`c`), corrected Porod volume
    (V\ :sub:`p`), the ATSAS Shape&Size and the ATSAS Bayesian methods.
*   Calculation of inverse Fourier transforms (IFTs) via GNOM, DENSS (DIFT) and a Bayesian
    indirect Fourier transform (BIFT).
*   Calculation of envelopes (dummy atom models) using DAMMIF, DAMMIN, DAMAVER, and DAMCLUST.
*   Calculation of electron density using the DENSS algorithm
*   Calculation and fitting of theoretical profiles to experimental data using CRYSOL.
*   Easy processing of in-line chromatography coupled SAXS data, including size-exclusions
    coupled SAXS (SEC-SAXS) data.
*   Deconvolution of SAXS data using singular value decomposition (SVD) and
    evolving factor analysis (EFA), and regularized alternating least squares
    (REGALS).
*   Standard data operations such as averaging, subtraction, merging, and rebinning.
*   Creation and plotting of 1D scattering profiles from 2D detector images, including
    Pilatus, CBF, Eiger, and more than 20 other types of images.


What is the RAW API?
---------------------

You can also :ref:`install BioXTAS RAW as a python package <api>` without the
GUI. This lets you import RAW directly into your python scripts and use the
API to call any of the functions in RAW. This is great for creating custom
processing scripts, either for unusual datasets that aren't handled in the
GUI, or to ensure reproducibility in your analysis. It can also be used
as the basis for an open-source automated SAXS data processing pipeline at
a beamline or homesource.


History and Usage
-----------------
RAW was first developed in 2008 by Soren Skou as part of the biological x-ray total analysis
system (BioXTAS) project. Since then it has been extensively developed, with recent
work being done by Jesse Hopkins.

RAW is used at various beamlines, including:

*   `BioCAT (18-ID) <https://www.bio.aps.anl.gov/>`_ at the APS
*   `MacCHESS ID7A BioSAXS <https://www.chess.cornell.edu/index.php/macchess/biosaxs>`_
    at CHESS
*   `LiX <https://www.bnl.gov/nsls2/beamlines/beamline.php?r=16-ID>`_ at NSLS II
*   `SIBYLS <https://bl1231.als.lbl.gov/htsaxs>`_ at ALS
*   `BIO-SANS at ORNL <https://neutrons.ornl.gov/biosans>`_
*   BL19U2 at SSRF

Xenocs distributes RAW with some of its homesources, and RAW is used at
various other homesources around the world.

Do you use RAW? :ref:`Let us know! <contactus>`


Licensing
-----------------
RAW source code is released under a GPLv3 license. Both the source code and the
prebuilt versions of RAW are free for anyone to download and use.

.. toctree::
   :hidden:
   :maxdepth: 2

   install
   help
   tutorial
   saxs_tutorial
   videos
   cite_raw
   api
   manual
   changes


.. |Rg| replace:: R\ :sub:`g`
