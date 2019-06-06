Introduction to RAW and this documentation
==========================================

**WARNING:** The manual is current several versions out of date. While it may
still be useful for some users, please refer to the tutorial for the most
up-to-date information.

RAW
---

BioXTAS RAW is a program for analysis of Small-Angle X-ray Scattering (SAXS) data.
The software enables: creation of 1D scattering profiles from 2D detector images,
standard data operations such as averaging and subtraction, analysis of radius of
gyration (Rg) and molecular weight, and advanced processing using GNOM, DAMMIF,
and AMBIMETER (requires ATSAS installation). It also allows easy processing of
inline SEC-SAXS data.

RAW is written in python (mostly) and C++ (a few small bits for speed). It is open
source and free for anyone to use. If you do use RAW, we ask that you cite the
following paper if you publish or present your results:

BioXTAS RAW, a software program for high-throughput automated small-angle X-ray
scattering data reduction and preliminary analysis, J. Appl. Cryst. (2009). 42, 959-964.

Some of the features of RAW include:

*   Calibrate, mask, radially integrate, and normalize 2D images to make 1D scattering profiles

*   Average, subtract, merge, rebin, and interpolate scattering profiles

*   Easily process in-line SEC-SAXS data

*   Calculate radius of gyration (Rg) and I(0) via Guinier fit

*   Calculate the molecular weight via I(0) comparison to standards, absolute calibration,
    correlation volume, and corrected Porod volume

*   Run GNOM, DAMMIF, and AMBIMETER (requires ATSAS installation)

*   Run singular value decomposition (SVD) and evolving factor analysis (EFA) on datasets

*   Calculate P(r) functions using a Bayesian indirect Fourier transform (BIFT)

*   Can read the following image formats:

    *   Pilatus Tiff

    *   CBF

    *   SAXSLab300

    *   ADSC Quantum

    *   Bruker

    *   Gatan Digital Micrograph

    *   EDNA-XML

    *   Eiger

    *   ESRF EDF

    *   FReLoN

    *   Nonius KappaCCD

    *   Fit2D spreadsheet

    *   FLICAM

    *   General Electric

    *   Hamamatsu CCD

    *   HDF5

    *   ILL SANS D11

    *   MarCCD 165

    *   Mar345

    *   Medoptics

    *   MPA (multiwire)

    *   Numpy 2D Array

    *   Oxford Diffraction

    *   Pixi

    *   Portable aNy Map

    *   Rigaku SAXS format

    *   16 bit TIF

    *   32 bit TIF

RAW is currently being developed by Jesse Hopkins and Soren Nielsen.

More information on RAW is available from the RAW website:

`https://sourceforge.net/projects/bioxtasraw/ <https://sourceforge.net/projects/bioxtasraw/>`_

RAW needs your help! If you find bugs in the program, or errors in the documentation
or tutorial, please let us know. Your input is the way we get better!

This documentation
------------------

The purpose of this documentation is to clearly and completely document the functions of RAW.
This document is not intended to act as a tutorial to RAW, for a tutorial please refer to the
tutorial document and videos available from the RAW website. Instead, the goal is to document
what features are available in each section of RAW, how to use them, and what they do.

This document is laid out in chapters discussing each general area of RAW (for example, the
Files tab in the Control Panel is a single chapter). When appropriate, a chapter will cover
two related areas, such as the Manipulation tab of the Control Panel and the Main Plot Panel.
Some areas will be physical panels or windows of RAW, as the previous examples, while some
will be features, such as the Online Mode chapter. The exceptions to this are the second chapter,
which covers how to install RAW, and the third chapter, which provides a brief introduction
to the different windows of RAW and how they relate.

Typically, the algorithms used will not be fully documented here, as they are available in
the source code or appropriate citations (and are subject to change as we improve and expand RAW).

