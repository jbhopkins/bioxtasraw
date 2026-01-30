# BioXTAS RAW

BioXTAS RAW is a program for analysis of solution Small-Angle Scattering (SAS) data.
The software enables: creation of 1D scattering profiles from 2D detector images,
standard data operations such as averaging and subtraction, analysis of radius of
gyration (Rg) and molecular weight, and advanced analysis using GNOM and DAMMIF as
well as electron density reconstructions using DENSS. It also allows easy processing
of inline SEC-SAXS data and data deconvolution using the evolving factor analysis (EFA)
or the regularized alternating least squares (REGALS) methods.

Install instructions: http://bioxtas-raw.readthedocs.io/en/latest/install.html

User guides:
http://bioxtas-raw.readthedocs.io/

To contact:
https://bioxtas-raw.readthedocs.io/en/latest/help.html

Features
* Calibrate, mask, radially integrate, and normalize 2D images to make 1D scattering profiles
* Average, subtract, merge, rebin, and interpolate scattering profiles
* Easily process in-line SEC-SAXS data
* Calculate radius of gyration (Rg) and I(0) via Guinier fit
* Calculate the molecular weight via I(0) comparison to standards, absolute calibration, correlation volume, and corrected Porod volume
* Run GNOM, DAMMIF, DAMAVER, DAMCLUST, and AMBIMETER (requires ATSAS installation)
* Electron density reconstructions using DENSS
* Deconvolve SEC-SAXS data using singular value decomposition (SVD) and evolving factor analysis (EFA)
* Deconvolve SAXS data using regularized alternating least squares (REGALS)
* Can read >25 image formats including: Pilatus, CBF, HDF5, Eiger, Quantum, Mar345, ESRF EDF, SAXSLab300,16 bit TIF, 32 bit TIF, Bruker, Rigaku SAXS
* And more . . .!
