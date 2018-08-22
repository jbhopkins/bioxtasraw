BioXTAS RAW
===========

What is BioXTAS RAW?
--------------------

BioXTAS RAW is a GUI based, free, open-source Python program for reduction and analysis
of small-angle X-ray solution scattering (SAXS) data. The software is designed for biological
SAXS data. It is available on windows, macOS (and OS X), and linux. It provides an
alternative to closed source programs such as Primus and Scatter for primary data analysis.
Because it can calibrate, mask, and integrate images it also provides an alternative to
synchrotron beamline pipelines that scientists can install on their own computers and use
both at home and at the beamline.

:ref:`Find out how to get it! <install>`

Features
--------

*   Analysis of radius of gyration (|Rg|) and I(0) via Guinier fit.
*   Analysis of molecular weight via I(0) comparison to standards, absolute
    calibration, correlation volume (V\ :sub:`c`) and corrected Porod volume (V\ :sub:`p`) methods.
*   Calculation of inverse Fourier transforms (IFTs) via GNOM and a Bayesian
    indirect Fourier transform (BIFT).
*   Calculation of envelopes (dummy atom models) using DAMMIF, DAMMIN, DAMAVER, and DAMCLUST.
*   Calculation of electron density using the DENSS algorithm
*   Easy processing of in-line chromatography coupled SAXS data, including size-exclusions
    coupled SAXS (SEC-SAXS) data.
*   Deconvolution of SEC-SAXS data using singular value decomposition (SVD) and
    evolving factor analysis (EFA).
*   Standard data operations such as averaging, subtraction, merging, and rebinning.
*   Creation and plotting of 1D scattering profiles from 2D detector images, including
    Pilatus, CBF, Eiger, and more than 20 other types of images.


History and Usage
-----------------
RAW was first developed in 2008 by Soren Skou as part of the biological x-ray total analysis
system (BioXTAS) project. Since then it has been extensively developed, with recent
work being done by Jesse Hopkins.

RAW is actively used as the primary analysis software at the
`MacCHESS G1 BioSAXS Beamline. <http://www.macchess.cornell.edu/MacCHESS/biosaxs.html>`_
It is also used at various other beamlines, including:

*   `BioCAT <http://www.bio.aps.anl.gov/>`_  (18-ID) beamline at the APS
*   BL19U2 (SSRF)
*   `I911-4 <https://www.maxlab.lu.se/node/35>`_ (aka I911-SAXS) beamline at MAX-LAB

`SAXSLAB <http://saxslab.com/>`_ distributes RAW with some of its homesources, and RAW is used at various
other homesources around the world.

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
   videos
   cite_raw
   manual
   changes


.. |Rg| replace:: R\ :sub:`g`
