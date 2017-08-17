File types
==========

.. _filetypes:

Output file types
-----------------

RAW outputs the following file types:

.cfg – These are files containing all of RAW’s settings (configuration files).
This file type is not human readable.

.dat – These are files containing :ref:`three column scattering profile data <savingdata>`
with a “header” at the start or end of the file for additional information. This file type
is human readable.

.ift – These are files containing :ref:`three column BIFT data <savingiftdata>` followed by four column
scattering profile data, with a “header” at the start or end of the file for additional
information. This file type is human readable.

.msk – These are files containing a RAW mask. This file type is not human readable.

.out – These are files containing GNOM P(r) data and are written in the standard
format described in the ATSAS manual for GNOM. This file is human readable.

.sec – These are files containing :ref:`SEC-SAXS curves <savingsecdata>`, which can be
loaded back into RAW and contain all of the relevant scattering profiles and
structural parameters. This file type is not human readable.

.wsp – These are files for :ref:`saved workspaces <workspaces>`. This file type is not human readable.


Input file types
----------------

In addition to the output file types described above, all of which can be read in by RAW,
RAW can load the following types of input files.

*ASCII files:*

.csv – If data is in a 3 column csv format, it is loaded assuming the columns are q, I, Error.

.dat (2 column) – If a .dat file has exactly 2 columns separated
by whitespace, it is loaded as q I.

.dat (4 column) – Produced by FoXs when fitting a theoretical curve to a scattering profile.
Loads the experimental and simulated (_FIT) scattering profiles.

.fir – Output by various ATSAS programs such as DAMMIF. Loads the experimental and simulated
(_FIT) scattering profiles.

.fit – Output by various ATSAS programs such as DAMMIF. Loads the experimental (often smoothed)
and simulated (_FIT) scattering profiles.

.int – Output by CRYSOL if no fitting is used. Loads the scattering intensity in solution.

.rad – Depreciated file format for RAW saved scattering profiles.

.txt - 2 or 3 column data can be read in as if it was a .dat file.

*Image files:*

Image files are often distinguished not just by their extension, but by their header format.
For example, many detectors produce tif files, but require different methods to read in the
appropriate header data. RAW uses the fabIO python module to load images. The complete list o
f images and extensions supported can be found here:
`http://pythonhosted.org/fabio/getting_started.html#list-of-file-formats-that-fabio-can-read-and-write <http://pythonhosted.org/fabio/getting_started.html#list-of-file-formats-that-fabio-can-read-and-write>`_

We reproduce that here with the detector/format followed by the file extension in parenthesis:
*   ADSC Quantum (.img)

*   Bruker (.sfrm)

*   CIF binary files (.cbf)

*   EDNA-XML (.xml)

*   ESRF EDF (.edf)

*   Eiger (.h5)

*   FReLoN

*   Fit2D spreadsheet (spr)

*   Gatan Digital Micrograph (.dm3)

*   General Electric (.No?)

*   HDF5 (Hierarchical Data Format 5) (.h5)

*   Hamamatsu CCD (.tif)

*   MarCCD/Mar165 (.mccd)

*   Mar345 image plate (.mar3450)

*   Nonius KappaCCD (.kccd)

*   Numpy 2D array (.npy)

*   Oxford Diffraction (.img)

*   Pixi (.?)

*   Pilatus Tiff (.tif or .tiff)

*   Portable aNy Map (.pnm)

*   Rigaku SAXS format (.img)

*   Tagged Image File Format (.tif)

In addition, we have written custom methods to support the following detector/file formats:

*   32 bit TIF (.tif)

*   FLICAM (.tif)

*   ILL SANS D11

*   Medoptics (.tif)

*   Multiwire (.mpa)

*   SAXSLab300

