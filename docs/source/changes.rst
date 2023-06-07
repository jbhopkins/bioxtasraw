Changes
============



2.2.0
-----------

Release date:

Overview
^^^^^^^^^^^

The RAW team is pleased to announce the release of RAW version 2.2.0. Significant
changes include:

    *   New CRYSOL GUI
    *   New profile comparison window
    *   Faster calculation of forward and backward EFA plots
    *   Improved PDF report with text wrapping in columns and vector graphics

The new release also includes numerous small bug fixes and improvements. Note
that this version of RAW introduces a new dependency on svglib.

In order to improve the prebuilt MacOS and Linux installers the oldest version
of OSes they will work in is now MacOS 10.14 and Ubuntu 18.04 LTS (note that
RAW can still be run from source on older versions).


All changes:
^^^^^^^^^^^^^

*   Fixed a bug where ATSAS fit files might load in missing the first or last datapoint.
*   Improved robustness of loading text files.
*   Improved speed of averaging, subtraction, merging, and interpolation up to 10x.
*   SVD, EFA, and REGALS can now used binned profiles for calculating the SVD,
    resulting in a significant speed up.
*   EFA now has a toggle for using previous result, which is off by
    default (changes default behavior).
*   Buffer region in the LC Series Analysis panel is now selected/validated with
    an intensity test on the median frame rather than the max frame.
*   Fixed a bug where Custom mode didn't work for DENSS.
*   Fixed a bug where min/max q for adjusted porod volume could end up outside
    of the interpolation range when using automated q selection.
*   The RAW main window now remembers position and size when you reopen it.
*   Fixed a bug where the q range in the BIFT and GNOM windows wasn't restricted by the
    q range set for the profile.
*   Removed spurious angstrom labels from the Rg label in the BIFT and GNOM window.
*   Fixed some issues that could arise when opening the GNOM window if a IFT
    wasn't successfully calculated.
*   Fixed a bug where BIFT wasn't using the q range previously used if the window
    was reopened.
*   Added ability to use non-integer Dmax values in the GNOM window.
*   Added ability to set profile units as 1/A or 1/nm for unit-aware calculations in RAW.
*   Made GNOM and MW panels unit-aware for automatically determining some values.
*   Fixed issues relating to using wxpython 4.2.0
*   Fixed issues relating to using matplotlib 3.7
*   Fixed a bug where the REGALS P(r) function wouldn't have the correct color.
*   Updated error messages to have system and version information.
*   Added zero lines to some REGALS and EFA plots.
*   Changed how plot margins are set to fix visual glitches.
*   Fixed an issue where tables in the report could extend off the edge of the document.
*   Added ability to add DENSS data to the report from the API.
*   Fixed a bug where DENSS data wasn't properly parsed for the report.
*   Fixed a bug where DAMMIF data wasn't properly parsed for the report.
*   Fixed a bug where extra EFA or REGALS information could be saved in the report
    if you saved more than one dataset where the technique was used.
*   Figures in the report are now vector (svg), so they should be higher quality.
*   Added a dependency on svglib.
*   Added a new comparison window that has residuals, ratios and a heat map as
    well as the old similarity test list.
*   Fixed an issue where FoXS fit files could take a long time to load.
*   Added a GUI for CRYSOL.
*   PDB and CIF files can now be loaded into RAW and the theoretical profile from
    CRYSOL is calculated when that happens.
*   Made subtraction of profiles with mismatched q vectors more robust.
*   Added ability to average profiles with mismatched q vectors.
*   Added ability to export data from the main IFT plot.
*   Fixed a bug where loading series data that doesn't have time data when the
    series x axis is in time would cause an error.
*   Fixed a bug where showing an image that was a different size than the beamstop
    mask array would cause an error.
*   DENSS resolution now rounds instead of displaying to arbitrary precision.
*   Added ability to rebin profiles in the dimensionless Kratky plot directly
    from the panel.
*   Fixed a bug where GNOM could raise an error if it failed due to having a
    fixed number of points in the P(r) function.
*   Added a tutorial on customizing and saving plots, exporting plot data, and
    opening data saved from RAW externally.
*   Updated DENSS to the latest version.
*   Added the ability to add DAMMIF and DENSS results from the saved results.csv
    files to the pdf reports from the GUI.
*   Fixed a bug where setting certain TeX values for plot labels could cause an
    error.
*   Fixed a bug where loading in a series when the intensity display was set
    to q value or q range and profiles in the series didn't contain either
    the q value or start/end of the q range could crash RAW.
*   Fixed a bug where denss and dammif results plots could end up the wrong size.
*   The Linux .deb installer now provides a version of RAW that works properly
    on Ubuntu 22.04 LTS (previously no GUI widgets had borders and ATSAS didn't
    work).
*   MacOS .app is now codesigned and notarized, so it should work on any system
    without requiring a workaround.


2.1.4
-----------

Release date: 2022-07-20

Overview
^^^^^^^^^^^

The RAW team is pleased to announce the release of RAW version 2.1.4. Significant
changes include:

*   Compatibility with ATSAS 3.1.0

Due to some changes in ATSAS, you may notice some differences in the associated
RAW tools:

*   SUPCOMB has been replaced with CIFSUP.
*   DAMCLUST is now included in DAMAVER, and so is no longer an option in the
    DAMMIF/N GUI.
*   SASRES is  not included in DAMAVER 3.1.0 output, but is in 3.1.1.
*   Output formats for DAMMIF/N are now .cif files.
*   DAMAVER is now multi-core. This greatly improves the speed, but as of now
    we don't see any way to restrict the number of cores it uses, so the number
    of processors specification in the DAMMIF/N window only applies to the
    reconstructions, not the averaging.
*   Clustering results from DAMAVER no longer include average cluster deviation
    or distance between clusters, so that is not reported. Eventually the GUI
    may be updated to remove those values, but since we suspect many people will
    keep using the older version of DAMCLUST for a while we will leave those
    fields in the GUI for now.
*   Note that the tutorials have been updated for ATSAS 3.1, but if you have
    an older version of ATSAS installed you will see the options appropriate
    for that version.

All changes:
^^^^^^^^^^^^^

*   Support for now .cif output format for DAMMIF/N.
*   Support for CIFSUP for alignment, including standalone GUI.
*   Auto detection of availability of CIFSUP/SUPCOMB.
*   Support for the new DAMAVER.
*   Extended support for SUPCOMB and DAMAVER to include all possible options.
*   Removed standalone call to DAMCLUST when using ATSAS 3.1.0.
*   DAMMIN refinement is now run in the same mode as the rest of the
    reconstructions (Fast/Slow).
*   Updated the sigma_clip integrator to use the pyFAI ng integrator
    (requires pyFAI>=0.21)
*   Added a feature to go to a particular image in a multi image file displayed
    in the Image plot panel.
*   Fixed a bug where certain values were set incorrectly when running DAMMIN in
    expert mode.
*   Added new ATSAS functions to the API, and updated API for changes to
    existing ATSAS functions.
*   Added ability to set DAMMIN random seed in the API.
*   Fixed a bug in the API rebinning that could result in the wrong number of
    points if multiple profiles were input at once.




2.1.3
-----------

Release date: 2022-06-06

Overview
^^^^^^^^^^^

The RAW team is pleased to announce the release of RAW version 2.1.3. This
version contains a single bug fix:

*   Fixed a bug that could prevent data from loading into RAW after the RAW
    window was dragged between two monitors.

It's not clear how prevalent this bug was, but given the potential severity
it warranted a quick fix/release.

NOTE: As of now, RAW is not compatible with ATSAS 3.1.0, which is currently
available for download as a pre-release. This is because ATSAS 3.1.0 is currently
missing several important programs, such as some of the DAMAVER set of tools,
so we can't test against that. Once ATSAS 3.1.0 is officially released we will update
RAW to support it. The same may apply to the 3.2.0 pre-release, we haven't been
able to test that yet.

All changes:
^^^^^^^^^^^^^

*   Fixed a bug that could prevent data from loading into RAW after the RAW
    window was dragged between two monitors.


2.1.2
-----------

Release date: 2022-05-23

Overview
^^^^^^^^^^^

The RAW team is pleased to announce the release of RAW version 2.1.2. This
version contains mostly minor bug fixes. Significant changes include:

*   Added a prebuilt version for arm64 chips on MacOS (Apple Silicon).
*   Removed Windows 7 and 8 support form the prebuilt version for Windows.
*   Added support for Eiger2 images from BioCAT.
*   Improved handling of multi-image files.
*   Adds a new dependency on mmcif_pdbx to read mmcif files.

There are also numerous other small bug fixes and new features.

NOTE: As of now, RAW is not compatible with ATSAS 3.1.0, which is currently
available for download as a pre-release. This is because ATSAS 3.1.0 is currently
missing several important programs, such as some of the DAMAVER set of tools,
so we can't test against that. Once ATSAS 3.1.0 is officially released we will update
RAW to support it.

All changes:
^^^^^^^^^^^^^

*   Fixed a bug that prevented normalization by a BioCAT header counter if
    it was the last counter in a line.
*   Improved buffer region finding in the series analysis.
*   Fixed a bug where the GNOM window raised an error if Dmax wasn't found
    automatically.
*   Fixed a bug where a series buffer region wasn't found if there were no peaks
    present in the data set.
*   Fixed a bug where REGALS results would show two lines for the same concentration
    curve when it wasn't supposed to.
*   Fixed a bug where validation of the REGALS settings could cause an error.
*   Fixed a bug where changing the range for REGALS in the SVD plot when there
    were previous REGALS results could cause an error.
*   Fixed a bug where using the qmin or qmax boxes in the series adjustment
    panel could cause an error.
*   Fixed a validation issue in REGALS.
*   Added ability to read in Eiger2 images from BioCAT and associated headers.
*   Added log binning for azimuthal integration.
*   Fixed a bug in error propagation on binning.
*   Fixed a bug where auto centering in the calibration panel didn't work on Eiger
    images.
*   Fixed a bug were SASRES resolution couldn't be read out of the damsel.log
    file in newer versions of ATSAS (>=3.0.4).
*   Improved azimuthal integration speed.
*   Image display for Eiger2 and Pilatus images now ignores bad pixels and
    detector gaps when automatically setting min and max values.
*   Fixed a bug where series buffer and sample ranges wouldn't print in the report
    if there wasn't also EFA or REGALS data.
*   Fixed a bug where moving a polygon or square mask wouldn't regenerate the mask
    in RAW unless you saved and reloaded the settings.
*   Fixed a bug where if a profile had a non-zero starting q index, autorg
    would return the wrong start index, which could cause it to fail in the GUI.
*   Fixed some off by one errors in the start and end points for some of the
    ATSAS functions in the API.
*   Improved speed of GNOM calculation in the GNOM window.
*   Fixed a bug with the initial start point not getting set correctly for some
    IFTs in GNOM.
*   Added an option (on by default) where masked pixels are excluded from
    automatic scaling in the image viewer.
*   Improved file handling for multi-image files to significantly reduce
    memory usage.
*   Removed GNOM options not available in gnom5.
*   Fixed a bug where if alpha wasn't the default value the GNOM window didn't
    initialize with the correct alpha.
*   Fixed a bug where the show plot buttons (1&2, 1, or 2) weren't working
    correctly with matplotlib >=3.4.
*   Dropped support for Windows 7 and 8 in the prebuilt version.
*   Added a prebuilt version for arm64 chips on MacOS (Apple Silicon chips).
*   Updated DENSS to the current version.
*   Made RAW mostly dark mode compatible on MacOS (requires wxpython>=4.1.1).
    May not work in the pre-built version for Intel macs.
*   Fixed a bug where DENSS symmetry settings other than 0 would cause an error
    when the DENSS window was opened.
*   Added some initial compatibility with ATSAS 3.1.0, but this is not finished
    because the pre-release version of ATSAS doesn't have several of the necessary
    programs for testing. Main change is mmcif compatibility for dammif outputs.
*   Added a new dependency on mmcif_pdbx for reading mmcif files.
*   Fixed an issue with spin controller display sizes in GTK3 (some linux installs).


2.1.1
-----------

Release date: 2021-05-05

Overview
^^^^^^^^^^^

The RAW team is pleased to announce the release of RAW version 2.1.1. The
major change in this version is:

*   Fixed a serious bug that would cause RAW to crash on Ubuntu.

There are also several other small bug fixes and new features.

All changes:
^^^^^^^^^^^^^

*   Fixed a serious bug that would cause RAW to crash on Ubuntu (and possibly other
    OSes).
*   Fixed a bug where closing the Guinier window before autorg finished would
    result in an error.
*   Fixed a bug that could cause an error if the auto_dmax function failed to
    return a result.
*   Fixed a bug where using simple concentration regularizers would fail.
*   Fixed a bug where caching of certain compiled functions wasn't working,
    leading to them having to be compiled every time RAW was opened.
*   Tweaked when functions are compiled to try to speed up the user experience,
    particularly when opening the Guinier window, and either IFT window.
*   Improved the speed of BIFT on Linux and Windows.
*   Fixed an issue where RAW wouldn't work with matplotlib>=3.4.1.
*   Fixed an issue where available fonts weren't properly displayed in the
    prebuilt versions.
*   In the RAW API, BIFT now defaults to single processor (should be faster),
    and you can specify the number of processors to use if you use it in
    multiprocessor mode.



2.1.0
-----------

Release date: 2021-04-20

Overview
^^^^^^^^^^^

The RAW team is pleased to announce the release of RAW version 2.1.0. This
version sees the release of two major new features:

*   Analysis reports on your data can now be :ref:`saved as PDFs <s1p4>`.
*   The release of a GUI for the REGALS technique, a new way to deconvolve
    overlapping LC-SAXS peaks. REGALS can be thought of as an extension and
    enhancement of EFA for other types of SAXS data, such as ion exchange
    chromatography, titration series, and time resolved SAXS.
    You can :ref:`read more about REGALS here <raw_regals>`.

Additionally we've overhauled the auto_guinier function to improve accuracy and
applicability to lower quality data. We've also added a new, more accurate
method for automatically finding Dmax when using GNOM. Finally, there are the usual
numerous small tweaks and bug fixes for the main RAW GUI and the API.

Special thanks to Steve Meisburger and Darren Xu for helping with the
details of their REGALS algorithm and code, and testing the new REGALS GUI.

**Note for MacOS users:** In order to achieve full compatibility with MacOS 11, we
have had to drop support in the prebuilt version for 10.9 and 10.10. The
prebuilt version of RAW will now run only on 10.11 or later. Additionally,
in 10.11-10.13 the main RAW windows will show some odd coloration (black
bars near the top of various windows, for example), but all functionality
seems to work fine. You can still build RAW from source on older versions of MacOS.

Also, we haven't been able to test on the Apple M1 chipset. RAW should work via the
built in Rosetta 2 translation in MacOS 11, but it will not run natively. If
someone wants to send us a Mac with an M1 chip to test on, we're happy to work on
getting it to run natively.

All changes:
^^^^^^^^^^^^^

*   Fixed a bug that was causing pyFAI to recreate the azimuthal integrator each
    time, slowing down radial averaging.
*   Fixed a BioCAT specific bug where concentration would end up in the profile
    info when it wasn't actually known for that profile.
*   Fixed a bug where series files couldn't be loaded or saved in python 3.8.
*   Fixed a bug where if you declined to load a config when you started RAW,
    the ATSAS install location wouldn't be automatically found.
*   Fixed a bug where matplotlib 3.3 would mess up the plot toolbars.
*   Fixed a bug where you would see an error message if RAW failed to find
    a valid sample region in the LC series plot.
*   Fixed a bug where doing EFA on a series that had the q range of the
    subtracted profiles truncated relative to the unsubtracted profiles would
    fail.
*   Added the ability to generate PDF reports of analysis.
*   Fixed a bug where the profile and ift line options dialogs couldn't be
    opened with matplotlib 3.3.
*   Significant improvements to auto_guinier function for both the GUI and API,
    including better accuracy, better handling of low quality data, and better
    handling of poorly formatted data.
*   Fixed a bug where if previous EFA ranges were available they wouldn't be
    properly set when the EFA window was opened.
*   The RAW DENSS results .csv file now indicates if a refinement was run.
*   Fixed a bug where RAW could fail to load a .out file.
*   Fixed a bug where aborting in the middle of a DENSS average could
    cause an error.
*   Fixed a bug where opening the GNOM window if the profile had a non-integer
    Dmax value caused an error.
*   Added the REGALS technique.
*   Added an enhanced way to automatically find Dmax when using GNOM.
*   Fixed a bug where running GNOM when RAW was run with python 3.8 could fail.
*   Added ability to read in a fourth dQ column in .dat files, preserve the dQ
    values through analysis and saving. Note that merging and interpolating
    do not preserve the dQ values at this time.
*   Added ability to read in CRYSOL 3 .int files.
*   Fixed an off by one bug that could affect SVD/EFA/REGALS
*   Fixed a bug where settings could fail to save or load on Windows if they included
    non-ascii characters
*   Fixed a bug where calculating the corrected Porod volume MW could return an error
*   EFA now remembers the force positive settings for concentration.
*   Fixed a bug where if an EFA range was listed high to low it would cause an
    error.
*   Fixed a bug where scaling q by 10x or 0.1x only worked once (i.e. you could
    scale to 0.1x or 10x, but not 100x, and couldn't go back to 1x after
    applying a scale).
*   Fixed a bug where the linear baseline wasn't getting a good start value.
*   GNOM window now 'truncates for dammif/n', which truncates to the smaller
    of 8/Rg or 0.3.
*   Guinier window now opens faster.
*   Updated DENSS to version 1.6.3, which includes the possibility of doing
    DENSS on a GPU (requires RAW to be built from source).
*   Fixed a bug where multiple DENSS windows couldn't be used at the same time.
*   Fixed a bug where subtracted and baseline corrected profiles from the LC
    Series Analysis window would have the prefix of the individual profiles in
    the series, rather than the series itself.
*   Fixed some possible memory leaks related to dialog creation/destruction.
*   Added a number of new tests.
*   Added compatibility with new string handing in h5py version 3.
*   Full compatibility with MacOS 11, which fixes several graphics glitches
    in 10.15 and 11. This required dropping support in the prebuilt version
    for MacOS 10.10 and earlier.
*   Fixed a bug with the API where loading multiple images from a single file
    wasn't working properly.
*   Added the ability to abort DAMMIF/N and related functions and DENSS runs
    in the API.
*   Made SECM and RAWSettings objects picklable, so they can be passed
    through a multiprocessing queue.
*   Fixed an API bug where saving a series would fail if you didn't set a
    filename.
*   Fixed an API bug where saving the GNOM results to a profile was saving
    the wrong qmax value.
*   Fixed a bug in the API where Dmin and Dmax zero conditions weren't getting
    set correctly for GNOM.
*   Added a feature to the API to truncate an IFT for dammif using either 8/rg
    or 0.3, whichever is smaller.
*   Fixed a bug in the API that could cause GNOM to fail to run.
*   The DENSS function in the API now returns chi squared, rg, and support
    volume as a function of iteration so you can check convergence.
*   Fixed a bug in the API where running EFA would change the associated ranges.
*   Fixed a bug in the API that could cause BIFT to fail.
*   Fixed a bug in the API that could cause the auto_guinier function to fail.
*   Fixed a bug in the mw_vp API function.


2.0.3
-----------

Release date: 2020-08-11

Overview
^^^^^^^^^^^

The RAW team is pleased to announce the release of RAW version 2.0.3. While
this is only a point release, we are releasing a major new feature for RAW.
There are only minor modifications to the RAW GUI, but we are releasing an
entirely new RAW API. This means that RAW can now be imported as a python
package and you can call RAW functions in your own scripts. The API is fully
documented, and the :ref:`documentation plus install instructions and some
examples are available on the RAW website. <api>`

A short example of the usage would be:

.. code-block:: python

    import bioxtasraw.RAWAPI as raw

    #Load the settings
    settings = raw.load_settings('./standards_data/SAXS.cfg')

    #Load the profile of interest
    profile_names = ['./reconstruction_data/glucose_isomerase.dat']
    profiles = raw.load_profiles(profile_names)

    gi_prof = profiles[0]

    #Automatically calculate the Guinier range and fit
    (rg, i0, rg_err, i0_err, qmin, qmax, qrg_min, qrg_max, idx_min, idx_max,
        r_sq) = raw.auto_guinier(gi_prof, settings=settings)

The API should be considered in beta right now. It is tested, but based on
further testing and user feedback the API may still change significantly.
If you use the API, please let us know if you encounter any bugs, incomplete
(or inaccurate) documentation or examples, or have suggestions for changes or
additions.

There are also several small bug fixes for the main RAW GUI.

All changes:
^^^^^^^^^^^^^

*   First release of the RAW API
*   Added new unit tests for the API.
*   Improved backwards compatibility of the RAW series .hdf5 files.
*   Fixed some depreciation warnings.
*   Fixed a bug where returning to the first EFA panel from the last and
    changing the number of significant singular values, then returning to the
    third panel would result in an error.
*   Fixed several bugs that could cause multiprocessing calculations to lock
    up.
*   Fixed several bugs in BIFT to make it more robust for poorly formatted
    data.
*   Fixed a Guinier fit bug where the fit could fail if a point in the fit
    had an uncertainty value of 0.
*   Fixed a bug where DATCLASS M.W. calculation could fail with an error.
*   Fixed a bug where if the estimation of the Rg error failed the Rg results
    would fail to save with the profile when the Guinier window was closed.
*   Fixed a bug where axes for the IFT profile plot couldn't be changed.
*   The P(r) fit is now plotted on top of the IFT data.
*   Fixed a bug where workspaces with IFTs couldn't be loaded.
*   Modified the BioCAT header load function to parse a single field spread
    out over multiple lines in the header.


2.0.2
-----------

Release date: 2020-07-09

Overview
^^^^^^^^^^^

The RAW team is pleased to announce the release of RAW version 2.0.2. The
major change in this version is:

*   Fixed a bug where SAXSLAB images couldn't be loaded.

There are also several other small bug fixes and new features.

All changes:
^^^^^^^^^^^^^

*   Can now load .dat files from WAXSiS, .dat files that are comma separated.
*   Fixed a bug where the Vc integrated intensity plot was blank if the
    scattering profile had saved M.W. results.
*   Improved rebinning functions, particularly the log binning function.
*   Fixed a bug where error wasn't interpolated properly when interpolating
    a profile.
*   Fixed a bug where pixel size from header bindings was in the wrong units.
*   Fixed a bug where series type could get lost in certain operations.
*   Fixed a bug where centering and enantiomorph selection options were
    ignored in the DENSS alignment panel.
*   Fixed a bug where series buffer range finding was scaling profiles before
    testing for similarity.
*   Fixed a bug where SAXSLAB images failed to load with pillow version 7.
*   Fixed a bug where SAXSLAB images failed to load.
*   Fixed a bug where images wouldn't load if there was no beamstop mask.
*   Fixed a bug that could result in calculated data not displaying on the
    series plot.
*   Fixed a bug where series saved as .hdf5 with EFA analysis would fail to
    open the EFA window when reloaded.
*   Fixed a bug where datgnom couldn't be run on truncated profiles.
*   Fixed a bug where opening the advanced settings window from the GNOM
    window didn't properly update changed settings in the GNOM window.
*   Fixed a bug where .hdf5 files couldn't be plotted by dragging and dropping
    or using the 'Plot Series' button.
*   Fixed a bug where running a dammin refine with too long a filename would
    fail (previously thought to be fixed in 2.0.0).
*   Fixed a bug that could prevent DENSS from starting on Windows and Linux.
*   Fixed a bug that could prevent auto determination of number of components
    in EFA.


2.0.1
------------

Release date: 2020-06-01

Overview
^^^^^^^^^^^^

The RAW team is pleased to announce the release of RAW version 2.0.1. This
version fixes several serious bugs in the previous version, including:

*   A bug where some of the M.W. calculations failed for profiles with
    a maximum q value greater than 0.5.
*   A bug where the standalone DENSS alignment window failed to run
    on Windows and Linux.
*   A bug where killing the prebuilt version of RAW on Linux would fail to
    delete temporary files, which could lead to the /tmp partition filling up.

There are also several other small bug fixes and new features.


All changes:
^^^^^^^^^^^^^^

*   Fixed a bug where the 'More Info' button didn't work for DATCLASS M.W.
*   Fixed a bug where Bayes and DATCLASS M.W. weren't saved when saving all
    analysis info.
*   Fixed a bug where RAW woud fail to load in .out files if they were missing
    values for any of the perceptual criteria.
*   Fixed a bug where an error message was shown whenever a profile with qmax
    > 0.5 was opened in the M.W. window.
*   Fixed a bug where the Vp M.W. extrapolation range warning could be shown even
    if the qmax selected was inside the extrapolation range.
*   Added zero lines to DAMMIF, DENSS residual plots.
*   Fixed a bug where running DENSS without averaging could result in an error
    message.
*   Fixed a bug where running DENSS without averaging or alignment would result
    in an error message.
*   Fixed a bug where when there was more than one profile in the normalized
    Kratky plot the dashed lines to guide the eye were not removed when
    switching from dimensionless Rg to other plots, which would throw off the
    scale of the plot.
*   Fixed a bug on Windows where the standalone DENSS alignment window didn't
    work.
*   Fixed bugs where the advanced options couldn't be shown in the SUPCOMB or
    DENSS alignement standalone windows on Windows.
*   RAW now catches SIGINT and SIGTERM and tries to exit gracefully. This mostly
    fixes an issue with the prebuilt .deb installer where the temp files
    created when starting RAW don't get deleted.

2.0.0
--------

Release date: 2020-05-07

Overview
^^^^^^^^^^^^

The RAW team is pleased to announce the release of RAW version 2.0.0. This version
brings a number of exciting changes, including:

*   Python 3 compatibility!
*   Conversion to pyFAI for radial integration
*   A .deb prebuilt installer for Debian/Ubuntu
*   A new series save format, .hdf5, that can be easily read by other programs.
    This new format is also ~50-70% smaller than the previous format.
*   New information windows above the control panel to display all your analysis
*   Ability to align DENSS and DAMMIF/N outputs to PDB files
*   Works with ATSAS 3 on all platforms
*   New Series adjustment panel that lets you adjust the scale, offset, and q range
    for all profiles in a series easily.

There are also a number of smaller new features, and a ton of bug fixes and tweaks.

With this release, we recommend that all users running RAW from source start
using Python 3 instead of Python 2.

Important notes:

*   RAW configuration files from 2.0.0 will not necessarily be back compatible with
    previous versions of RAW. You will get a warning if you load a .cfg file from
    RAW 2.0.0 in a previous version. Old configuration files can be loaded in
    RAW 2.0.0.

*   RAW series .hdf5 files from 2.0.0 cannot be opened by previous versions of RAW.
    The old series .sec files can be opened by 2.0.0.

*   This is the last release that is guaranteed to be Python 2 compatible, since
    Python 2 hit end of life in January 2020. While we will not intentionally
    break compatibility with Python 2, we don't have the resources to test on both
    Python 2 and 3.


Many thanks to the beta testers who helped test this release:

    *   Norm Cyr
    *   Richard Gillilan
    *   Rob Miller


All changes:
^^^^^^^^^^^^^^^

*   All RAW code is now compatible with both Python 2 and 3
*   Conversion to pyFAI for radial integration, including support for using
    detector angles, polarization correction, dark correction, flatfield
    correction, and dezingering.
*   A new .deb prebuilt installer for Debian/Ubuntu
*   A new series save format, .hdf5, which is easily read by any program that
    can load HDF5 data.
*   Modified Control panel button layouts.
*   Added a requirements.txt file for easy pip installation.
*   Added ability to align DENSS results to a PDB or MRC file either from the
    main DENSS window or an auxiliary window.
*   Updated DENSS to version 1.5.0.
*   Added ability to view help documents in program on MacOS and Windows.
*   Changed a number of default windows sizes and tweaked layouts to be better on
    all operating systems.
*   Added all new info panels for Profiles, IFTs, and Series that display all
    relevant analysis information about a selected item.
*   Added ability for users to permanently add new hdf5 file definitions to RAW
    from inside the program.
*   Added a q cutoff to the volume of correlation calculation.
*   Fixed a bug where the q cutoff for the porod volume MW calculation wasn't being
    used for Series files.
*   Fixed a bug where the q cutoff for the porod volume MW calculation wasn't getting
    set properly in default mode when the MW window opened.
*   Changed how imports are done on startup so that RAW can be run from the command line
    in two number of ways, including ``python <path-to>RAW.py``, and as a module as
    ``python -m bioxtasraw.RAW``
*   Added ability to use SUPCOMB to align dammif/n output with a PDB file,
    either directly from the main dammif/n window from from a separate window.
*   Fixed a bug where not all of the program output would get written to the log
    window for damaver, damclust.
*   Added error handling for the main thread, which will reduce amount that RAW
    freezes from unexpected errors.
*   Changes to prevent/reduce flickering on Windows.
*   You no longer see two overwrite prompts when saving multiple items at once.
*   Fixed a couple of options in the view menu that didn't work.
*   Added a feature where if a user tries to load more than 100 profiles individually
    they are asked if they instead want to load them as a series.
*   EFA ranges can now span the whole dataset, allowing better fits for components
    that are still eluting at the end of the EFA range.
*   Added ability to easily apply the 8/Rg cutoff for dammif in the GNOM panel.
*   Fixed a bug where RAW was not checking for unsaved IFTs on exit.
*   Fixed a bug where IFTs would show as having unsaved changes when there were
    no unsaved changes.
*   Changed Manipulation and Main Plot names to Profiles.
*   Added ability for RAW to prevent the computer from going to sleep during long
    calculations, such as DENSS or DAMMIF/N.
*   Fixed a bug where view menu items were not getting properly selected on startup.
*   Added IFT plot axes to the view menu.
*   Added LC Series Analysis to the Tools menu.
*   Fixed a bug where an error message was displayed when quitting RAW.
*   Fixed a bug where running DENSS on a BIFT P(r) function wasn't using the
    correct q & i vectors for the refinement.
*   Changed item highlight color.
*   Made masking, centering, and all options panels scrolling panels.
*   Added busy dialogs for saving files.
*   Fixed a bug where failing to save a file could crash RAW.
*   Added a zero line to the normalized Kratky plot.
*   Fixed a bug that could cause dammif/n, damaver, and damclust to stop running on Windows.
*   Fixed a bug where new versions of ATSAS (>=3.0) wouldn't be found on Windows.
*   Fixed a bug where if filenames got too long and were truncated for dammif
    the refine step failed.
*   Fixed a bug where making lots of masks could result in an 'out of window ids'
    error.
*   Fixed a bug where masks didn't stay inverted upon resizing.
*   Fixed a bug where changing the qmin or qmax while BIFT was running an initial
    search gave an error.
*   BIFT now saves the set q range and reopens the window with that range.
*   BIFT and GNOM windows now default to the min q of the Guinier range if no
    analysis has previously been done.
*   GNOM analysis now saves alpha value, restores it when window is reopened.
*   MW analysis now saves Porod cutoff choice, density, and VC mol type choice
    and restores when the window is reopened.
*   Fixed a bug where if you ran dammif or denss again in the same window the
    results summary wouldn't display properly.
*   Fixed several bugs related to running ATSAS by properly setting the environment
    ATSAS and PATH variables.
*   Fixed a bug where the wrong version of ATSAS could be fond on MacOS.
*   Added ability to display P(r) functions on an I(0) normalized plot (set as default).
*   Fixed a bug where custom toolbar buttons didn't display as toggled properly on MacOS.
*   Added ATSAS MW methods Bayes and DATCLASS (Shape&Size) to the MW panel.
*   Fixed a bug where running datgnom didn't respect the q ranges set in the GNOM window.
*   Changes for compatibility with wxpython 4.1.0.
*   Fixed a bug where moving a profile between plots didn't preserve all of the
    line/marker style settings.
*   Fixed several bugs related to displaying and moving a legend on the plots.
*   New Series adjustment panel that lets you adjust the scale, offset, and q range
    for all profiles in a series easily.
*   Fixed a bug where the end point for profiles used in GNOM and BIFT was one
    data point earlier than specified in the controls.


1.6.4
--------

Release date: 2020-03-10

Overview
^^^^^^^^^^^^

The RAW team is pleased to announce the release of RAW version 1.6.4. This version
adds in a new header type for the MacCHESS SAXS beamline Eiger 4M detector. There
are also a few other minor bug fixes.

All changes:
^^^^^^^^^^^^^^^

*   Fixed a bug where negative values for error would cause points to not be read
    from .dat files.
*   Fixed a bug where the BIFT window wouldn't open if the profile and n min or
    n max for the q vector set to other than 0 and the length of the q vector.
*   Fixed a bug where looking for bind list keywords that don't exist in the
    RAW settings would prevent a file from loading.
*   Fixed a bug where damaver didn't run with symmetry even if dammif did.
*   Added a name to the dock/menu bar icon.
*   Fixed a bug with moving masks.
*   Added CHESS EIGER 4M to counter file reader options.
*   Fixed type-casting issues for max/min in polygonmasking that caused
    errors on some older systems.


1.6.3
--------

Release date: 2019-11-01

Overview
^^^^^^^^^^^^

The RAW team is pleased to announce the release of RAW version 1.6.3. This version
fixes a critical bug where when average detected different files, regardless of
user choice it would always average all files (selecting just similar files
didn't work). There are also a few other minor bug fixes.

All changes:
^^^^^^^^^^^^^^^^^^

*   Fixed a bug where if you averaged, subtracted, or merged two items with analysis
    done on them, you could end up with partial analysis info in the resulting file
    that would cause errors opening analysis windows.
*   Fixed a critical bug where when average detected different files, regardless of
    user choice it would always average all files (selecting just similar files
    didn't work).
*   Fixed a bug where the MW window wouldn't open if the Guinier fit hadn't been done.
*   Fixed a (Debian specific?) bug where wx.CallAfter used with wx.MessageBox wasn't
    threadsafe and could cause RAW to crash (use wx.MessageDialog).


1.6.2
--------

Release date: 2019-10-28

Overview
^^^^^^^^^^^^

The RAW team is pleased to announce the release of RAW version 1.6.2. This version
fixes several critical bugs that could prevent DENSS from running. There are no
other changes.


1.6.1
--------

Release date: 2019-10-21

Overview
^^^^^^^^^^^^

The RAW team is pleased to announce the release of RAW version 1.6.1. This version
contains numerous small bug fixes and improvements, particularly for the new
series analysis methods released in version 1.6.0.

We anticipate this will be the last release before RAW version 2.0, which will be our
first python 3 compatible release. We're aiming to release version 2.0 sometime around
the end of the year.

Note: as part of this release we did test with ATSAS 3.0 (pre-release version), and
RAW seems to be compatible with it.

All changes:
^^^^^^^^^^^^^^^^

*   Fixed a bug where opening the Ambimeter panel could fail if ATSAS was installed
    in a directory with a space in the path name.
*   Fixed a bug where if RAW didn't load a settings file when opened it wouldn't
    automatically find the ATSAS directory on startup.
*   Fixed a possible bug where using the LC Series Analysis panel on series data
    being loaded in online mode could fail.
*   Added intensity type selector for the series panel when sending data to the main plot.
*   Fixed a bug where automatic integral baseline start/end region determination
    could set the wrong control limits.
*   Fixed a bug where zero lines on various plots (like the GNOM P(r)) plot weren't
    getting redrawn when necessary.
*   Fixed a bug with autoscaling in the LC Series Analysis plots when changing the
    data type displayed.
*   Fixed a bug where sample and buffer region comparison in the LC Series Analysis
    panel could return the wrong indices for dissimilar profiles.
*   Fixed a bug where profile comparison in LC Series Analysis would skip the first profile.
*   Fixed a bug where a very short series (<22 frames) could cause errors when opening
    the LC Series Analysis panel.
*   Improved automatic buffer search in the absence of major peaks.
*   Improved automatic buffer search to search on the right side of the main peak if
    it doesn't find a good buffer region on the left side.
*   Removed a bias to the left side of the peak in the automated sample region search.
*   Removed actual baseline correction values from being saved in file history, as history
    could get very long (>100000 lines).
*   Added a cutoff for header length, at which point RAW will stop saving file history.
    This avoids saving extremely large text files.
*   Added compatibility for pyFAI 0.18 (note: on linux and python 2 pyFAI 0.18 seems
    to be broken, stick with 0.17).
*   Added a new way of loading HDF5 files with definitions done in external files.
*   Added ability to load HDF5 files from LiX.
*   Fixed a bug where identical selected regions in the LC Series Analysis window didn't
    count as overlapping.
*   Fixed a couple of typos in messages.
*   Fixed a bug where Ambimeter and GNOM couldn't run if the current working
    directory was read only.
*   Improved how ATSAS programs are called, and added use of temporary file names
    and directories.
*   Fixed a bug where when dragging the image plot with the masking showing you
    could sometimes get an unexpected error.
*   Added the name of the series to the LC Series Analysis panel.
*   Fixed a bug where baseline subtracted profiles were improperly being skipped
    when calculating Rg etc in the LC Series Analysis panel.
*   Fixed a bug where if a series was loaded with a baseline already calculated,
    changing buffer range or other parameters wouldn't properly recalculate baseline
    corrected values.
*   Fixed a bug where if you set a baseline, then set it back to none, when exiting
    the LC Series Analysis window the baseline calculated values would be saved
    instead of the regular subtracted values.
*   Fixed a bug where if you loaded in a series curve with baseline correction,
    then turned off baseline correction, it wouldn't have any calculated values.
*   Fixed a bug where the LC Series Analysis panel would resize itself when any of
    the collapsible panes were collapsed or expanded.
*   Fixed a bug in the LC Series Analysis panel where if you had a range that was
    one frame long, when you closed and reopened the analysis window you
    couldn't adjust the range.
*   Fixed a bug in the LC Series Analysis panel where if you had a one frame long range
    you could get a reported correlation in the range.
*   Fixed some issues with window height where windows weren't opening large enough
    for all of their contents.
*   Fixed some issues with window size where windows could open up bigger than
    the screen.
*   Fixed a bug where in certain circumstances opening the SVD and EFA windows could fail.
*   Added compatibility with numba >= 0.44


1.6.0
------

Release date: 2019-06-07

Overview
^^^^^^^^^^^^

The RAW team is pleased to announce the release of RAW version 1.6.0. This version
contains several major changes:

*   Completely new and improved SEC-SAXS processing, including new automated buffer
    and sample region selection and baseline correction. There are also
    significant speed improvements for SEC-SAXS processing, in addition to the
    new features.
*   Completely redone BIFT, which fixes several bugs (both minor and major), and
    adds Monte Carlo error estimation and extrapolation fit of data to I(0).
*   RAW now preserves matching metadata across processes like averaging and
    subtraction. Metadata is now saved with keywords compatible with the SASBDB
    to make uploading there easier for users. Users can now also provide
    arbitrary metadata during data reduction.
*   All new icons which are compatible with retina displays, including changing
    out the check mark for showing/hiding data on plots for an eye, which we
    hope will be more intuitive.
*   RAW now loads the last used config, rather than the last saved config, when
    it starts up.
*   Any analysis window (Guinier, MW, GNOM, etc) can now be opened more than
    once, allowing easy comparison or side-by-side processing of data sets.

You can see the full set of changes below.

We also want to note that we're not anticipating any other major
feature releases this year. With the upcoming end of life for python 2 at the
end of 2019, we need to focus on making RAW work with python 3. Once that is
done we will start doing major feature development again.

All changes:
^^^^^^^^^^^^^^

*   Updated DENSS to have the latest features, including refining averaged
    structures, symmetry constraints, and the 'Membrane' protein mode.
*   Completely redid BIFT code from the ground up. This fixes several bugs, and
    now includes Monte Carlo estimation of errors.
*   Completely redid series analysis for SEC-SAXS data. Now includes automated
    buffer and sample region determination and baseline correction.
*   Added residual plots to GNOM, BIFT, and DAMMIF/N results.
*   Fixed several bugs related to setting error bar line styles.
*   Added ability to add arbitrary metadata to a file header when an image is
    processed by RAW
*   Updated the adjusted Porod volume MW method to match the newly published MoW2
    approach.
*   Fixed a bug where info panel data could get improperly set
*   All appropriate fields in MW panel now editable.
*   You can now open any analysis window more than once (previously only one
    instance of each window was allowed).
*   Fixed a bug where in the GNOM window changing q_min or q_max didn’t update
    the IFT results.
*   RAW now loads the last used config (saved or loaded) by default rather than
    the last saved.
*   RAW now preserves all shared header values when averaging, subtracting, or
    merging datasets.
*   Added visual guidelines to the dimensionless Kratky plot.
*   Added option to display normalized residuals, now on by default.
*   Added Rigaku HiPix to known images (requires Fabio 0.9.0)
*   Guinier panel can now export Guinier fit data so users can make the Guinier
    plots in their plotting software of choice.
*   RAW’s file list no longer displays hidden files.
*   Can now read in time of each data point for BioCAT data.
*   Fixed a bug where closing the BIFT window with BIFT running would crash RAW.
*   Better formatting for numbers displayed in the status bar.
*   Fixed a bug where windows could be too large on low resolution displays.
*   Fixed a bug where series plot calculated data were not highlighted by the
    locater button.
*   Fixed a bug where markers were not highlighted by the locater button for
    any plot.
*   Fixed a bug where when selecting a line by clicking on it the plot markers
    were not highlighted.
*   Fixed a bug where selecting a line on the IFT plot didn’t work.
*   Can now display unsubtracted, subtracted, or baseline corrected intensity
    in the main series plot.
*   Fixed a bug where series data could be truncated when exporting.
*   Fixed a bug where the SVD window wasn’t doing the SVD on non-error-normalized
    curves.
*   Moved cormap to cython for speed, increased by at least 5x.
*   Modified layout of the repository to standardize.
*   Autorg now uses numba for just-in-time compiling. Speed increase of 2 orders
    of magnitude.
*   Fixed bugs that would occur when quick reduce, plot, plot series, or show
    images were used on folders, ‘..’, or with no files selected.
*   Added ability to plot intensity over a q range for series plots.
*   All-new icons that work with retina displays, including a new ‘eye’ for
    show/hide instead of a check box (hopefully more intuitive).
*   Fixed a few bugs in the DAMMIF/N GUI.


1.5.2
------

Release date: 2019-04-04

Overview
^^^^^^^^^^^^

The RAW team is pleased to announce the release of RAW version 1.5.2. The only
change is this version is a modification to how BioCAT header files are read in,
to accommodate a new header file format at that beamline.

1.5.1
------

Release date: 2018-11-01

Overview
^^^^^^^^^^^^

The RAW team is pleased to announce the release of RAW version 1.5.1. This version
contains several small bug fixes. Normally we might wait to release these until
more major changes had happened, but there is a workshop using RAW soon and
we wanted these bugs fixed before then. Significant issues that have been eliminated:

*   An issue where the electron density output from DENSS could fail to load into pymol
    correctly because the default scaling was too small (still loaded into Chimera fine).
    Strictly speaking I think this is a workaround for a bug in pymol . . .
*   Several bugs with running GNOM, including using data with minimal sampling (<100 points).
*   Fixed a bug where the .app package for Mac wasn't displaying natively on retina displays,
    so the text was fuzzy.

You can see the full set of changes below.

All changes:
^^^^^^^^^^^^^^

*   Fixed a bug where automatic loading of BioCAT SEC data wouldn't work if there was
    more than one underscore in the filename.
*   Fixed a bug where automatic loading of BioCAT SEC data wouldn't work if there existed
    another file with the same name but different extension as one of the image files.
*   Added parsing of damsup.log file for bead models, which allows highlighting of
    the representative model in the dammif summary.
*   Dammif results summary now saved by default.
*   DENSS results summary now saved by default.
*   Fixed several bugs in the GNOM interface that could cause it to fail.
*   Fixed a bug that prevented some .fit files from being loaded.
*   Fixed a bug where the Rg for BIFT was being calculated incorrectly.
*   Fixed a bug where temporary files (with a .tmp prefix) would mess up SEC autoupdates.
*   Fixed an issue where you couldn't run DENSS twice without closing the panel
    between each run.
*   Fixed an issue where the default scaling for DENSS was too small, and caused issues loading
    the electron densities into pymol.
*   Fixed a bug text in some items and list controls would display 'fuzzy' on high dpi
    monitors. This is still an issue for the plot labels.
*   Added the ability to run damaver and damclust on the same set of reconstructions.
*   Fixed a bug where the .app package for Mac wasn't displaying natively on retina displays,
    so the text was fuzzy. Note that in order to fix this, even after you install the new
    version you may have to do the following:

    #.  Enter the following commands in your terminal: ::

        /System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister -f /Applications/RAW.app
        /System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister -kill -seed
        /System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister -f /Applications -all local,user

    #.  You may then have to right click on RAW.app, select 'Get Info' and uncheck the box
        'Open in low resolution mode'


1.5.0
------

Release date: 2018-08-23

Overview
^^^^^^^^^^^^

The RAW team is pleased to announce the release of RAW version 1.5.0. This version focused on
several significant updates that will be invisible to most users. Namely:

*   RAW is now compatible with wxpython4
*   RAW no longer uses weave, which has been essentially unsupported for years, to
    compile code. It now uses the numba just-in-time compiler.

This will make it much easier for us to support RAW, and should make it easier for
users to install RAW from source on any platform. It also prepares us for the
inevitable transition to Python 3 that has to happen in the next several years.

In addition to a range of bug fixes and small enhancements detailed below, RAW
also now incorporates the new DENSS alignment code. This is all done in python,
in RAW. This removes the dependency on EMAN2, and means that all parts of density
reconstructions work on Windows!

Finally, RAW is now saving configuration files in JSON format. This is human
readable, and makes the RAW configuration files more open and accessible for other
programs to use. However, this does mean that earlier versions of RAW will not be
able to open configuration files created with version 1.5.0 or later. However,
configuration files created in earlier versions of RAW ARE compatible with version 1.5.0.


All changes:
^^^^^^^^^^^^

*   Fixed a bug where if atsas is in the path but not installed RAW will still find the directory from the path.
*   ATSAS filepaths and filenames should be able to deal with spaces.
*   Fixed various strange threadsafe bugs on debian 8.
*   Weighted average now checks for similarity
*   Fixed a bug where the dammif results window wouldn't work when you did only one dammif run and had damaver checked.
*   Fixed a bug where dammin in normal mode wouldn't work on windows.
*   Fixed a bug where dammif/n wouldn't abort on windows.
*   Added in new expected shape parameter for dammif in custom mode.
*   Fabio, hdf5plugin, and pyfai are now required dependencies, rather than optional dependencies
*   Mode all previously compiled code into using the numba just-in-time compiler.
    This is important because the previous code was compiled with weave, which
    has been unsupported for years.
*   Fixed a bug where users could give dammif/n file prefixes that were too long for damaver.
*   Fixed a bug where canceling out of the color change dialog didn't cancel the color change.
*   Made the plot options box resizable (important for computers with large font size).
*   Fixed a bug where the sec plot right axis framestyle wouldn't properly restore
    if you canceled out of the plot options dialog.
*   Significant code restructuring and cleanup.
*   EFA calculations are now in a thread, so it might not freeze the whole GUI.
*   Circle and rectangle masks are now resizable.
*   Added ability to automatically mask pixels at/above/below a given threshold.
*   Added ability to automatically mask images based on known detector panel gaps.
*   Added ability to create predefined size/location circle and rectangle masks.
*   Added ability to control detector image left-right flip and up-down flip.
*   Fixed a bug where RAW could crash under certain conditions when exporting analysis info.
*   Fixed a bug where the Guinier window would give an error under certain circumstances.
*   GNOM and BIFT windows now show scattering profiles on log-lin axes.
*   RAW is now wxpython4 compatible.
*   Added alpha as an available setting in the GNOM window.
*   Fixed several bugs in the GNOM window that caused RAW to unnecessarily calculate
    the P(r) function, slowing down the program.
*   Added drag and drop file loading for both the plot and control panels.
*   Settings are now saved in JSON format, which is human readable, to increase
    compatibility and ease of use by other programs. This means that settings
    saved from RAW 1.5.0 are not compatible with previous versions of RAW. Settings
    saved from previous version of RAW ARE compatible with RAW 1.5.0.
*   DENSS now uses custom python code for aligning and averaging density. This
    removes the requirement on EMAN2, which means all parts of DENNS will work on Windows.
*   The image plot now maintains the same zoom when you change images. Previously
    it would zoom back out to the full image whenever you showed a new image.
*   Fixed a bug where the SVD would sometimes not open correctly.
*   Fixed a bug where if there was one pixel in the q bin during integration the
    error would be set to 0 instead of the square root of the value
*   Fixed a bug where nans or infinities in the SVD matrix would break SVD/EFA
    without an appropriate error message.

1.4.0
-------

Release date: 2018-03-20

Overview
^^^^^^^^^

The RAW team is pleased to announce the release of RAW version 1.4.0. This is a
major feature release for us! The big new feature is that RAW can now use the
DENSS method to calculate electron density from SAXS scattering! You can read
more about this at http://denss.org/.

To fully use this new feature (for density averaging and enantiomer filtering)
you have to install EMAN2 (http://blake.bcm.edu/emanwiki/EMAN2/Install) which,
sadly, doesn't work on Windows. Windows users can still generate densities, but
they won't be able to average them. A new tutorial on DENSS in RAW is now available
in the documentation (https://bioxtas-raw.readthedocs.io/en/latest/tutorial/s2_denss.html).

The other feature many folks will be interested in is the new error calculation
for Guinier fits, which is a much requested feature. This is now available whenever
you open the Guinier panel, and saves and exports with the rest of the analysis
information as expected.

We've also done the usual set of bug fixes and tweaks. You can find a full list of changes below.

All changes:
^^^^^^^^^^^^

*   Added DENSS method for calculating electron density from SAXS profiles
*   Added support for EMAN2 averaging and enantiomer testing of DENSS results
*   Fixed a bug where the GNOM window could fail to exit and save the .out file to the IFT tab
*   Changed the default DAMMIF mode to slow.
*   Changed when the 'please wait' message appears when loading SEC-SAXS files
    in autoupdate mode. Now it only shows up if more than 5 files are loaded at once.
*   Fixed a bug where advanced options for GNOM and DAMMIF couldn't be set while
    the respective analysis windows were open.
*   Fixed a bug where the spectral color map couldn't be displayed, breaking the
    image control panel.
*   Fixed a bug where ambimeter would try to run in the DAMMIF window even if
    ambimeter wasn't available.
*   Fixed a bug where if files were averaged or subtracted and had analysis history,
    that analysis would get transfered to the new file.
*   Fixed a bug where Guinier fit limits would be improperly displayed on the plot
    when the Guinier window was first opened.
*   Fixed a bug where calls to set up the DAMMIF results window could be non thread safe.
*   Added estimate of the parameter (Rg and I0) errors for a Guinier fit.
*   Reformatted the MW display to make it more compact.
*   Changed how numbers are displayed in all of the analysis windows, to better
    handle very large or very small values.
*   GNOM, Ambimeter, DAMMIF windows now open much faster.
*   Added support for BioCAT header files (new style).
*   Added support for autoloading of BioCAT Series curves.
*   Added GNOM P(r) parameters (Rg, I0) errors to the GNOM window, and the estimated Guinier errors.
*   Guinier parameter errors and GNOM P(r) parameter errors are now saved with
    profiles, and with analysis info spreadsheets.
*   Fixed bugs where spin controls could raises errors if a user entered a blank value.
*   Values from analysis windows are now saved with more precision.
*   Rearranged the manipulation item right click menu to make it more compact,
    put some less-used items on sub-menus.
*   Changed 'SEC' labels to 'Series' labels.
*   Fixed an off by one error in SEC autoupdate that could occur for certain file names.
*   Renamed and rearranged some menu items in the IFT item right click menu.
*   Added universal newline support when loading in scattering data.
*   Fixed a bug where averaging could fail if all the averaged files were different form the first file.
*   Fixed a bug where similarity testing could fail with an overflow error if
    there were too many points in the scattering profile.
*   Minor improvements to plotting speed with large numbers of files.
*   Fixed a bug where having no positive values in a curve displayed on a log-y
    axis would cause an error.
*   Updated the documentation to include a DENSS tutorial. Updated various other
    parts of the documentation, including the images, to reflect other new features.
*   Updated all of the installation documentation.
*   Removed the RAW-Windows-Source-Install-Essentials file from the downloads.


1.3.1
-------

Release date: 2017-11-01

Overview
^^^^^^^^^

The RAW team is pleased to announce the release of RAW version 1.3.1. This is a
very minor release. Several small bugs have been fixed, and we have updated the
citations in the program to reflect the release of the new RAW paper. Most of
the major work in this release went into updating the documentation, which we
have already released on the new website: https://bioxtas-raw.readthedocs.io/

All changes:
^^^^^^^^^^^^

*   Made RAW compatible with pyFAI 0.14 (not back compatible with 0.13)
*   Improved the multiwire loading function
*   Updated some citations and error messages in the program
*   Revamped and updated all of the documentation and tutorials. It is now in
    sphinx format, in the RAW SVN for better tracking.
*   Updated the RAW citation to reflect the newly released RAW paper.
*   Updated the .app build on mac.


1.3.0
-------

Release date: 2017-08-19

Overview
^^^^^^^^^

The RAW team is pleased to announce the release of RAW version 1.3.0. This release
is a major feature release, and we're very excited that you get to use all of the
fun new stuff we’ve added in! The major new features are:

*   Similarity testing for scattering profiles using the CorMap test. This allows
    statistical testing of whether or not profiles are similar. This is done
    automatically when averaging profiles or picking a buffer region of a SEC curve,
    and is also available in the right click menu for profiles, IFTs, and sec
    files. In the automatic check, if it detects files that may be different,
    you’ll see a message asking you how you want to proceed.
*   Normalized Kratky plots can now be made, and are accessible through the right click menu.
*   We’ve added a results summary panel for dammif/n reconstructions that shows the
    NSD, resolution (if SASRES is installed), and statistics about the individual
    reconstructions including chi squared, rg, dmax, excluded volume, and molecular
    weight. There is also a new dammif results viewer panel that lets you get a
    basic look at the reconstructions (this panel is still very simple).
*   Absolute scaling can now be done using the NIST glassy carbon standard SRM 3600.

In addition to all of these major changes, we’ve made the usual range of small
tweaks, bug fixes, and enhancements. See the full list of changes below.

Finally, we’re happy to announce that we’re also releasing a new tutorial, that
has been updated to include tutorials for all of the new features mentioned above!

All changes:
^^^^^^^^^^^^

*   Fixed a bug where switching between linear and log scale in the image display
    could change the overall scaling of the image without changing the displayed
    limits in the dialog.
*   Added a new dammif/n results summary panel.
*   Added a new dammif/n results viewer panel.
*   Added a new normalized kratky plot panel
*   Changed how multiple images in a single file are deal with when loaded as a
    sec curve (now each is loaded as an individual point on the curve).
*   Added a new check for statistical similarity between profiles (or IFTs or SEC curves).
*   Now on average, RAW automatically checks whether the profiles are statistically similar.
*   Fixed a bug where the first image loaded from a file with multiple images in
    t was flipped left-to-right relative to the rest.
*   Fixed a bug where if a configuration file is loaded and doesn’t contain certain
    setting keys (a configuration made with a previous version where those settings
    don’t exist, for example), those settings are now set to default, rather than
    left as whatever is loaded in RAW.
*   Added ability to view all images in a single file if the file contains more than one image.
*   Added ability to use glassy carbon (NIST SRM 3600) to calibrate absolute scale.
*   Fixed a bug in subtraction that could result in the q and i vectors being rounded.
*   Fixed a bug where if the beam center was in the masked region of the image
    it could be assigned a non-zero value.
*   Fixed a bug where a RAW setting for a choice type with default value of None
    could cause an error when trying to set the field in the Advanced Options window.
*   Added a check for syncing items to make sure that an item is starred and an item is selected.
*   Added ability to reset all settings to default values from the advanced options panel.
*   Marker face, marker edge, and error bar colors are now saved when you save a workspace.
*   Error bars now show up correctly for Guinier, Kratky, and Porod axes in the Main Plots.
*   Added ability to use error weighting in fits, and ability for user to toggle
    that on and off in the advanced options panel. Fitting is now by default done
    with error weighting.
*   RAW can now load .txt files.
*   Fixed a bug where on a single core machine there would be no default selection
    for the number of simultaneous runs in the dammif/n window.
*   Font list now includes matplotlib fonts
*   Changed LaTeX symbols to default to regular instead of italics.
*   Fixed a bug where line size on a plot would change when opening/closing the
    line properties window without making any changes to the line size in the window.
*   Added ability to use fractional line sizes.
*   Fixed a typo in the readme
*   Removed a message asking if you’re sure you want to load the workspace.
*   RAW now checks whether or not you’re saving something when it quits. If it is
    saving something, it warns you that you might now want to quit.
*   Legend labels are now saved with a workspace.
*   Fixed a bug where the legend label for IFT items would get changed from the
    default when you opened the line properties window.
*   Fixed a bug where the calculated markers for a SEC item would show when loading
    a workspace even if the item wasn’t supposed to be visible.
*   Added sync and superimpose to the right click menu, tools menu.
*   Added the program version to integrated dat files history.
*   Added integration method and calibration parameters to the integrated dat files history.
*   Fixed a bug where a dammin refine would try to run even if damaver didn’t run.
*   Fixed a bug where superimpose could break for different q vectors.
*   Fixed a bug where the slider and custom color boxes in the color dialogs didn’t change line/marker colors.
*   Fixed a bug where in autoupdate mode the SEC plot could fail to switch between rg, mw, i0 on the right axis.
*   Fixed a bug where you couldn’t resize custom question dialogs.
*   Fixed a bug where SVD/EFA wouldn’t work with some sec data loaded in autoupdate mode.
*   Fixed a bug where when updating the SEC data in autoupdate mode, an improper
    q value could be used when getting the intensity at a given q.
*   Fixed a bug where if improper values were entered in the buffer range or window
    size and the set/update parameter button was pressed, if autoupdate mode was on it would stop.
*   Removed the error printing on startup that backup.ini file could not be found.
*   Fixed a bug where carrying out EFA to panel 3, then going back to panel 1 and
    changing the frame range used, then carrying out EFA again could cause an error in the rotation.
*   Fixed a bug where for unsubtracted profiles from images, EFA would use the full
    profile rather than the appropriately truncated profile.
*   Fixed a bug where the options panel couldn’t be opened twice in windows.
*   Added a check to prevent errors with missing lines when changing plot type in the main plots.
*   Added a check to prevent index errors when setting the q range of a sasm.
*   Fixed a bug where online mode would show an error if the directory being watched was removed.
*   Added a choice in the GNOM panel to force dmax to zero or not.
*   Added ability to use superimpose to find scale, offset, or scale and offset.
*   Fixed a bug where EFA results wouldn’t export due to getting the wrong q values from the scattering profiles.
*   Fixed a bug with new versions of numpy not integrating images correctly. (actually fixed in 1.2.3 rerelease)
*   Changed the generic error message. (actually fixed in 1.2.3 rerelease)
*   Fixed a bug where temporary files that vanish in the online directory could
    raise an error. (actually fixed in 1.2.3 re-release)
*   Fixed a bug that could cause intensity integration to fail in the sec plot.
    (actually fixed in 1.2.3 re-release)
*   Fixed a bug where calculating the scale constant of water could cause the main
    thread to lock up if it had an error.
*   Verified compatibility with ATSAS 2.8.2.
*   Fixed a bug where in the prebuilt windows version any plots not in the main
    window (for example, Guinier plots) couldn’t be saved.
*   Fixed a bug where line colors didn’t reset properly when canceling out of any
    of the line properties dialogs.
*   Fixed a bug where the SVD window could have no default selection for type of
    profile to use.
*   Fixed a bug where the advanced options window didn’t open properly centered on
    the parent window.
*   Minor speed improvements from code streamlining.


1.2.3
-------

Release date: 2017-05-08

Overview
^^^^^^^^^

The RAW team is pleased to announce the release of RAW version 1.2.3. The release
again mostly focuses on bug fixes, speed improvements, and other small improvements
to the user experience. There is one bit of exciting news: we are releasing a
prebuilt version for Mac! Users can now download a .dmg with a RAW.app in it.
This can be installed via drag-and-drop, like other app files, and run just like
any other app. We hope this will make installation much easier for mac users.
If you want to try this, the download is available in the usual area, and the
mac install instructions have been updated.

In addition to the new prebuilt version, we’ve also made errors more obvious,
now if there is an unhandled error in the program, rather than failing silently
it will pop up a dialog box to let you know. We’re hoping this is seen as an improvement!

All changes:
^^^^^^^^^^^^

*   Made numerous changes to fix strange behavior in frozen version on mac
*   Created instructions for building a frozen version on mac
*   RAW icon now shows up in the dock instead of the top bar on mac
*   Fixed how RAWWorkDir is used in the program, and how it gets set. It now gets set appropriately for each type of OS
*   Switched to using an embedded version of the BioXTAS logo, for easier packaging
*   Changed the default directory for RAW if there is no previous directory. It now uses the documents directory
*   Fixed a bug in the Porod volume calculation that in some cases could extrapolate to q<0
*   Added Guinier extrapolation to the volume of correlation molecular weight calculation
*   Changed how Guinier extrapolation is done for the adjusted porod volume method
*   Updated some of the text in the More Info buttons of the MW panel
*   Fixed a bug where changing the q vector of a scattering profile would print an error in the console
*   Updated the A and B coefficients for the adjusted porod volume method to perfectly match those used in the paper
*   Updated GNOM and BIFT windows to both report reduced chi squared values
*   Fixed a bug where having an ROI mask set could prevent loading image
    headers in the calibration section of the advanced settings
*   Tweaked the MW, GNOM, and BIFT GUIs
*   Fixed a bug where GNOM wouldn't run on SL6 with ATSAS 2.7.2
*   Fixed a bug where rescaling profiles wouldn't work on a kratky plot
*   Fixed a bug where IFT data plot could display the wrong scale for Guinier and Porod plots
*   Changed how Guinier plots are displayed from I vs. q2 on a loglin scale to
    log(I) vs. q2 on a linlin scale, to match with labels shown on the plot
*   Fixed a bug that could cause autorg to crash
*   Changed the circle masking tool to draw more quickly/smoothly
*   Improved responsiveness of dragging masks on an image
*   Fixed a bug where the beam center wouldn't turn off if the masking panel was closed
*   Improved responsiveness of updating positions of calibrant rings and beam
    center when working in the centering panel
*   Fixed some bugs that could happen when switching between calibration and
    masking windows without hitting the okay or cancel buttons first
*   Fixed a bug where VC integration was highly unstable in some cases, required
    switching from simpsons method to trapezoid method for numerical integration
*   Attempted to fix a not reproducible bug where clicking the clear all button
    could cause a segfault on linux
*   Fixed a bug so that the info panel is only cleared if the user actually decides
    to clear all items when clicking the clear all button
*   Fixed a bug where loading FoXS files with fits would not load the fit
*   Fixed a bug where PIL.Image couldn't load files (prevented loading of SAXSLAB300 images)
*   Fixed a bug where if an image load returned no header, RAW could crash
*   Did some futureproofing in the code
*   Fixed a possible memory leak when loading certain image types
*   Attempted to fix an irreproducible bug where masking would fail because pixel
    positions were floats instead of ints
*   Error bars, if shown, now move properly with the line on scale and offset
*   Fixed a bug where the Guinier window didn't respect the q limits set on the manipulation panel
*   Set the default plot type to log-lin instead of lin-lin
*   Fixed a bug where using the next/previous image buttons would cause the image
    to flicker if a fixed range were set for the color scale
*   Fixed a bug where scaling q didn't mark the item as modified
*   Fixed a bug where online mode loading more than one image didn't update the image plot
*   Changed the green for the average file name text from green to forest green, which may be easier to read
*   Fixed a bug where the centering panel being displayed without an image loaded could cause an error.
*   Fixed a bug where the ATSAS 2.8.0 GNOM wouldn’t run if an Rg for the profile had not been calculated.
*   Fixed a bug where DAMCLUST wouldn’t run.
*   Added a global error handler to pop up a dialog for unhandled errors.
*   Attempted to fix a bug where the program could run out of control ids on mac, causing a crash.
*   Fixed a bug where damclust and dammin refine could both be selected in the advanced options window.
*   Fixed a bug where dammin refine could be selected without damaver being selected in the advanced options window
*   Fixed a bug where setting a flatfield image could fail if there wasn’t an absolute scale normalization factor set
*   Fixed a bug where GNOM and BIFT autosaving could be turned on without directories selected.
*   Fixed a bug where switching from linear to log scale or vice versa with limits
    locked in the image display would set the slider bar maximum value incorrectly.
*   Removed tifffile.py (no longer used).
*   Fixed a bug where automated centering wouldn’t work with the newest pyFAI
*   Fixed a bug where typing an incomplete LaTeX expression in the plot label could cause an error.
*   Added some error checking to running GNOM/DATGNOM in case it fails for some reason.


1.2.2
-------

Release date: 2017-03-10

Overview
^^^^^^^^^

The RAW team is pleased to announce the release of RAW version 1.2.2. This release
mostly focuses on bug fixes, speed improvements, and other small improvements to
the user experience. However, there are several changes/new features we think
many of our users may want to know about:

#.  RAW now has the ability to do weighted averages of scattering profiles (accessible
    by the right click menu in the main control panel)
#.  RAW is now compatible with ATSAS version 2.8.0.
#.  You can now run DAMMIN from RAW (previously on DAMMIF was available). This
    includes using DAMMIN to refine the damstart.pdb file output from DAMAVER,
    which is now the default option.
#.  RAW can now handle files with multiple images in them, such as Eiger hdf5 files.
    This is an ongoing project, so some features, such as image viewing and SEC
    plotting do not yet handle these types of files perfectly.
#.  We have changed how the show/hide and collapse/expand buttons work. Previously
    they affected all items. Now if no items are selected they affect all items,
    otherwise they affect the selected items. We hope that once users are accustomed
    to this change they will find it useful.
#.  RAW has a new header type available, P12 Eiger header files.

Additionally, RAW users should be aware that we have added an additional dependency,
the weave package (to replace scipy.weave, which was removed in scipy version 0.19),
and that RAW is not yet compatible with matplotlib version 2.0 (released January 2017).
We are working on updated install instructions to reflect these changes, and those will
be available (hopefully) next week.

As always, we appreciate user feedback, as that is how we improve the program.
If you have questions, need help, or want to report a bug, please contact us!

All changes:
^^^^^^^^^^^^

*   Added ability to do a weighted average in RAW, using either error based weighting
    per q point or weighted by a counter value.
*   Many small changes to the code to streamline how plotting works, which should
    results in modest speed improvements, particularly when working with large numbers of plotted files.
*   If autoscaling is on for plots, plots should now autoscale in all appropriate
    instances (previously they didn't autoscale when moving items between plots,
    rescaling the q range, and a few other instances)
*   Trimmed out many dead functions to make the code easier to maintain.
*   Changed how the visibility check box for control panel items works, which
    improved show/hide speed for a single item when lots of files were loaded by a factor of 2.
*   Improved speed for certain actions that resulted in marking lots of items as modified.
*   Fixed a bug in autorg where error for the rg value could fail to be calculated
*   Fixed a bug in running GNOM for ATSAS <2.8 where certain advanced settings couldn't be used.
*   Fixed a bug where flatfielding would fail when using pyFAI to integrate images (not yet publicly available)
*   Fixed a bug where using the roi_counter would fail when using pyFAI to integrate images (not yet publicly available)
*   Fixed a bug where dezingering would fail using python for integration (instead of the compiled c++ modules)
*   Removed the SASIft.py file that was unused.
*   Fixed a bug where having nothing entered for limits in the plot options
    panel (such as when typing a new limit) would print an error message in the console.
*   Fixed a bug where loading a roi_counter header value with no image header would give an error.
*   Fixed a bug where legend position wasn't maintained when all items were removed or hidden on a plot.
*   Fixed a bug where the legend wouldn't go away if all items on the SEC plot
    were hidden and there had previously been a legend.
*   Updated how legend settings are handled in plot options to improve speed and maintainability.
*   Fixed a bug where plot titles and axes labels didn't reset appropriately when using the clear all button.
*   Fixed a bug where the plot options font selector boxes didn't work.
*   Fixed a bug where not all settings were restored to previous values when canceling out of the plot options dialog.
*   Fixed a bug where the Porod volume calculation was not getting properly interpolated to q=0.
*   Fixed a bug where hitting the next/previous image buttons in the RAW Image
    plot would throw an error and crash RAW if the image currently displayed wasn't
    in the current working directory of the Files panel.
*   Fixed a bug where saving items wasn't threadsafe on scientific linux 6.
*   Fixed a bug in how the error bars for log(I) were calculated in the autorg function.
*   Switched the autorg to calculate the Guinier fit without error weighting, to
    match how it is done in the Guinier panel.
*   Fixed a bug where the how to cite button in the dammif frame wasn't getting properly placed in wxpython < 3.0.
*   Addeed the ability to run dammin from the DAMMIF (now DAMMIF/N) window.
*   Added the ability to use dammin to refine damstart files from dammin/f in the DAMMIF window.
*   Fixed a bug where autoMW, autoRG did not respect the limits set for the
    scattering profile in the manipulation controls.
*   Changed how the show/hide and collapse/expand buttons work. Previously they
    affected all items. Now if no items are selected they affect all items, otherwise
    they affect the selected items.
*   Added compatibility for gnom5 from ATSAS 2.8.
*   Counters available for normalization now show up in the combo box in the normalization list panel.
*   Made some progress fixing a windows specific bug having to do with hitting
    enter after clicking a button in another panel.
*   Fixed some bugs on windows where the mouse would get captured and not released by txtctrl boxes.
*   Fixed a bug where the rename option wasn't working in the file overwrite dialog.
*   Moved the version number into the RAWGlobals.py file.
*   Improved speed of saving items from RAW, by a factor of ~160x for a large number of files on my test machine.
*   Fixed a bug in the Guinier panel where the maximum point shown in the plot and
    used for the fit was one less than the maximum point shown in the spin control.
*   Tweaked the autorg function to allow some intervals with qmaxRg > 1.3 (up to 1.35) to improve fitting.
*   Fixed a bug where interpolate did not work on multiple selected scattering profiles.
*   Fixed a bug where interpolate was giving the interpolated file the wrong name.
*   Fixed a bug where writing the header could cause RAW to crash due to improper json serialization.
*   Changed how normalization deals with zero values. Instead of raising an error it prints a warning.
*   Added the GNU disclaimer at the top of all .py files that didn't have it.
*   Added a header type for P12 Eiger, Petra III
*   Updated image loading and all associated functions to handle multiple images
    in a single file, for example eiger files.
*   Added filtering of headers so that () and [] characters are removed, as header
    names with these characters could not be used for normalization.
*   Fixed a bug where image and other headers were getting filtered differently.
*   Added some new file types to the TestData folder.
*   Added error catching for json formatting of file headers upon save. If the
    header can't be serialized properly, the files saves without a header (used to cause a crash).
*   Fixed a bug where ambimeter could fail if there were spaces in the filename.
*   Fixed a bug where with older versions of wxpython and matplotlib, failure to
    find points in the autocentering mode could cause RAW to freeze.
*   Fixed a bug where quick reduce would crash if it couldn't find the header.
*   Replaced the dependency on scipy.weave with the weave package (which is a
    fork of scipy.weave), as scipy.weave is removed in scipy 0.19.


1.2.1
-------

Release date: 2016-12-02

Overview
^^^^^^^^^

The RAW team is happy to announce the release of RAW version 1.2.1. This version
focuses on bug fixes and small improvements to the user experience. There were a
few significant changes:

#.  In addition to numerous bug fixes, the EFA technique can now be used with
    explicit, iterative, or hybrid methods for computing the concentration profiles
    of the components. Previously, only the iterative approach was available.
#.  We added a new automated centering and calibration routine using the pyFAI
    library, for better determination of beam center and sample-detector distance.

In addition to a new version of RAW, we have also released new installation instructions for all platforms.

As always, we appreciate user feedback, as that is how we improve the program.
If you have questions, need help, or want to report a bug, please contact us!

All changes:
^^^^^^^^^^^^

*   Updated online mode so RAW only plots files if there are files to plot. This
    prevents some flickering when files enter the directory but are not plotted
    for any reason (such as not being suitable images).
*   Updated online mode so that the “Processing incoming file…” status doesn’t
    linger forever after an image is processed, but goes away suitably quickly.
*   Fixed a bug that prevented EFA from running on scattering profiles that don’t
    use the full range of their q vector.
*   Fixed a bug where concentration wasn’t saved when the ‘save all analysis info’ option was used.
*   Fixed a bug where changing SEC plot axes while SEC live update is going could cause a crash
*   Fixed a bug where Normalization information got saved in the scattering profile
    processing parameters twice, once with a capital N, once with a lowercase n.
*   Fixed a bug where the wrong upper limit was getting set for the end of range
    controls in the third EFA control panel.
*   Fixed a bug where if no normalizations were set in the normalization list,
    the solid angle correction would not be saved in the normalization history
    list for the scattering profile.
*   Made a change where if EFA has a converged solution, if the ranges are changed
    it uses that solution as a starting point. This leads to faster convergence to the new solution.
*   Added ability to display calibration rings from any calibrant in the pyFAI library.
*   Fixed a bug where plotting certain scattering profiles on a Kratky plot would cause RAW to crash
*   Fixed a bug where having the SEC plot set to display the intensity at a particular
    q value would prevent structural parameters from being calculated, and in
    some cases could prevent new SEC items from being plotted.
*   Fixed a bug where the plot legend wasn’t updated if the plot was turned on,
    then off, and then items were removed from the plot.
*   Added an energy box in the centering and calibration window, so that if energy
    is entered, wavelength is automatically calibrated, and vice versa.
*   Fixed a bug where changing centering values with no centering values selected
    could crash RAW.
*   Added ability to explicit calculation of concentrations for EFA, as opposed to currently iterative method.
*   Added ability to use a hybrid method for calculation EFA, using the explicit
    calculation as a starting point, then refining iteratively.
*   Added ability to chose rotation method for EFA in the third EFA control panel.
*   Fixed a bug where the range plot in the third EFA panel was not refreshing
    properly when the number of significant values was changed.
*   Fixed a bug where the info panel was not updated when a scattering profile
    was selected by clicking on it on the main plot.
*   Updated build commands for making a windows installer, including adding some
    explicit hooks for pyFAI and pyinstaller.
*   Added the optional use of the hdf5plugin to RAW to support eiger images.
*   Fixed a bug in the image display where the dialog box could fail to open
    because the maximum value in the image was greater than 2^31-1 (the maximum
    value a wx slider can handle).
*   Added a feature for automatic centering and fitting of the beam center and
    sample to detector distance. Requires pyFAI to be installed.
*   Added a header reader for g1 eiger files, which have the spec header file
    one level up from the image files.
*   Fixed a bug where the RAW ROI could not consistently be used for normalization.


1.2.0
-------

Release date: 2016-10-25

Overview
^^^^^^^^^

The RAW team is very pleased to announce the release of version 1.2.0. We've added
two major new features, the first of which is the ability to perform SVD on a set
of scattering profiles, IFTs, or a SEC-SAXS curve. We've also implemented the
exciting new evolving factor analysis (EFA)[1] method for deconvolving overlapping
data. This is primarily intended to be applied to SEC-SAXS data, but it is implemented
so that it can be applied to any set of scattering profiles or IFTs. We want to
note that while EFA is an exciting new technique, it is still in ongoing development.
We intend continuing development on the stability and utility of the algorithm.

We will release an updated tutorial document and dataset which includes examples of doing SVD and EFA soon.

As always, we appreciate feedback from users, either positive or negative.

The RAW Team

[1] Steve P. Meisburger, Alexander B. Taylor, Crystal A. Khan, Shengnan Zhang,
Paul F. Fitzpatrick, and Nozomi Ando. Journal of the American Chemical Society 2016 138 (20), 6506-6516.

All changes:
^^^^^^^^^^^^

*   Added the solid angle correction to the normalization parameters in the sasm
    history, so that if it is used, that use is recorded.
*   Fixed a bug where SAXSLAB images could not be loaded when using version 3.0 or newer of the pillow library.
*   Added in the ability to use a RAW defined beamstop mask in addition to a SAXSLAB beamstop mask for SAXSLAB data.
*   Fixed a bug (on OSX, wxpython 3.0) where clicking the OK button in the Masking
    Panel was returning the plot window to the IFT panel instead of the Main Panel.
*   Added in some dialog boxes letting users know they can't modify the SAXSLAB
    header mask in RAW. Previously, the Remove and Set buttons in the masking
    panel appeared to work for the SAXSLAB header beamstop mask, but in reality
    did nothing. Now they still do nothing, but pop up a dialog letting the user
    know that nothing has happened (and no longer appear to do anything).
*   Added a molecule type choice to the SEC calculate parameters panel, so that
    the user no longer has to change the default molecule type in the mol weight options panel.
*   Fixed a bug where the Clear All button was not properly clearing some fields in the SEC control panel.
*   Added SVD capability.
*   Fixed a bug which prevented some .sec curves from being loaded.
*   Added overwrite checking to the .sec saving function.
*   Fixed a bug where the SEC item filename didn't change when the item was saved with a different name.
*   Made how SEC names are deal with consistent with how scattering profile names are dealt with.
*   Added overwrite checking to the Export data option for SEC curves.
*   The parameters on a SEC plot now default to markers, not lines.
*   Fixed a bug where in a 3 column data file with no non-data first line (empty
    or otherwise), the first data point would get cut off.
*   Added evolving factor analysis (EFA) capability
*   Added 'How To Cite' buttons for the RAW functions that incorporate other people's
    work, so that they can correctly cite the methods.
*   Added in backwards compatibility for loading .sec files from previous versions
    of RAW, and workspaces with saved .sec files from previous versions of RAW.
*   Saving/Loading a workspace now preserves the file order in the workspace.
*   Fixed a bug where selecting log axes would crash RAW if you tried to do so before loading any data.
*   Fixed a bug where the legend label for ift and sec items got set when it didn't need to be.


1.1.0
-------

Release date: 2016-08-22

Overview
^^^^^^^^^

The RAW team is happy to announce the release of version 1.1.0. While there are
several significant new features, the major milestone that pushed us into version
1.1 is the integration (after almost a year) of the RAW code that has been available
on this website and the RAW code improvements made by Soren Skou for use with the
SAXSLAB homesource machines. All of RAW is now unified, and we intend to have only
one development trunk for the foreseeable future (though we may have temporary branches
for major feature development).

We have also added in a solid angle correction for integrating images into scattering
profiles. This correction accounts for the change in solid angle of a pixel as you
change q. We have tested it against the solid angle correction implemented in pyFAI,
and found that the results are identical. This effect will get stronger at higher
q, and cause an overall increase in intensity of integrated profiles. On a Pilatus
detector, the solid angle correction has a ~0.5% effect on integrated intensity
at q=0.25 A^-1 and ~4% effect at q=0.75 A^-1.

Major new features include:

*   The solid angle correction mentioned above
*   Improved speed when calculating Rg, MW, and I(0) for SEC-SAXS curves (up to a
    factor of 7 faster in our limited testing)
*   Ability to read in multiwire (.mpa) files
*   Ability to read in headers from SAXS beamline BL19U2 at the Shanghai Synchrotron Radiation Facility
*   Merging, rebinning, and interpolating now all save history information like averaging and subtracting have
*   Scattering profile history (either: averaging, subtracting, merging, rebinning,
    and interpolating, or information about loading in and normalization) can now
    be viewed within RAW by right clicking and selecting 'Show history'
*   RAW is now (mostly) compatible with wxpython 3.0 on Linux

Beyond these changes, there are numerous small improvements, visual tweaks, and bug
fixes. You can find a full list of those below.

Simultaneous with this release we are also releasing updated installation guides
for all platforms. We are happy to say that we are confidant enough in our ability to
produce prebuilt windows installers that we now recommend that windows users install
from the .msi files unless they know that they need to compile from source.

As always, we appreciate any feedback (positive, or, especially, negative), bug
reports, and suggestions for new features!

All changes:
^^^^^^^^^^^^

*   Fixed a bug that prevented BIFT from running in uncomplied mode
*   AutoRG now runs automatically when the Guinier window opens, assuming there is no previous Guinier analysis
*   Fixed a bug where BIFT failing to find a solution caused RAW to crash
*   If autosave is active, and a the folder vanishes, autosave now detects that, and is disabled, instead of crashing RAW
*   When RAW settings are loaded, all folders and files in the settings (autosave directory, online directory, flatfield file) are checked. If they cannot be found, these settings are disabled, and the user is notified.
*   Visual improvements of the BIFT window, DAMMIF window, and some options windows
*   Fixed a bug where analysis windows would show up behind the main window,
    where you could move them by dragging the title bar without losing focus on
    the analysis windows, and where you could bring them to the front without first
    clicking on the main window
*   Changed the layout in the SEC tab to be more descriptive, and to save space
*   Changed welcome dialog info
*   Fixed display problems of the Guinier and GNOM windows under wxpython 2.8 on Ubuntu
*   Added the ability to start online mode at startup with a predefined directory
*   Added the option of automatic saving of BIFT and GNOM results
*   Updated save functions in RAW so that files that RAW saves are not automatically loaded back into RAW
*   Added in option (on by default) to apply a solid angle correction to the
    integrated data to account for change in solid angle of the pixels with q
*   Fixed several small bugs with the online mode: crashing when the online mode
    directory ceased to exist, online mode being able to start without selecting an online directory
*   All counters and image header parameters now automatically have any spaces in
    the file name replaced with underscores, so that they do not crash the normalization
*   DAMCLUST is now available as an alternative to DAMAVER after running DAMMIF
*   Merging, rebinning, and interpolation now add to the file history in the same
    way that subtracting and averaging have
*   Added a new feature to view the file manipulation history or load history within
    RAW (right click on a scattering profile in the manipulation list and select 'Show history')
*   Added a sorting function to the .dat file saving so that file parameters should
    always appear in the same order in the saved file
*   Fixed a bug where a tiff file with the wrong header getting read in as a
    Pilatus tiff file would cause RAW to hang up
*   Added extra error catching to the file header load function
*   Sped up calculation of SEC-SAXS Rg, MW, and I0 by adding a threshold function.
    The threshold checks the ratio of integrated sample intensity (or whatever
    intensity is being used for the SEC plot) of the average buffer to the average
    sample files. If the intensity is not above the set threshold (1.02 by default),
    it does not try to calculate the parameters. This means all of the buffer curves
    are automatically skipped, and calculation is much faster. It depends on the
    threshold and the data, but I saw speed increases of up to ~7x. This can be
    set by the user in the new SEC-SAXS panel in the Advanced Options window.
*   Changed how normalization information is saved when a .dat file is saved.
    Now, normalization information is only saved when it is applied. The absolute
    scale factor applied is also now saved
*   Added more files to the list of files that can be loaded in online mode
*   Updated sync function so that files are only marked as modified when something is changed during the sync
*   Modified how the centering arrows work to catch faster clicks, and to (mostly)
    prevent two moves with one click (noticed on a mac)
*   Masks with zero area are no longer saved as masks
*   Added the ability to load some multiwire detector files (.mpa files)
*   Added the ability to read in the header for files from BL19U2 at the Shanghai Synchrotron Radiation Facility
*   If the image or beamline header contains a concentration key word, that is
    now set as the sample concentration in RAW when the image is loaded
*   Fixed a problem where ambimeter in the ATSAS 2.7.2 package could not be run
*   Fixed numerous small and large visual problems with running RAW on linux with
    wxpython 3.0. I now believe that RAW can be considered compatible with
    wxpython 3.0 on all platforms, but there are still occasional sizing issues
    on Linux that it does not handle perfectly
*   Fixed a bug where damaver and damclust would not run if the directory path contained a space


1.0.3
-------

Release date: 2016-07-20

Overview
^^^^^^^^^

We're releasing the latest version of RAW, 1.0.3 today. This includes several minor
bug fixes. The timing of the release is done so that the version being demoed at the
ACA meeting (http://www.amercrystalassn.org/2016-scientific-program#SAXS) will be
identical to the latest release.

All changes:
^^^^^^^^^^^^

*   Fixed a bug where saving a mask without an image loaded would cause an error.
*   Fixed a bug where attempting to show a SAXSLAB BS Mask without a SAXSLAB image loaded would cause an error.
*   Fixed a bug where autosaving for files (processed image files, averaged files,
    subtracted files) could be turned on without a valid save directory selected.
*   Added a feature so that when an autosave directory is cleared, autosave for
    that file type is turned off.
*   Fixed a bug where the final lines of the damaver output were not being shown in the dammif window.
*   Added some extra information to the two most common error messages we get
    contacted about: inability to load an image type, and inability to load a header file.
*   Fixed an error where if an image header contained non-unicode characters,
    when a scattering profile generated from that image header was saved it would
    crash RAW. Fixed the same error if the header was shown.
*   Removed some unused settings values.
*   Removed the brightness bar in the image settings pop up window, as it was
    currently disabled. This may be re-enabled in the future.
*   Set the image settings pop up window to have the default upper value be the
    max pixel value, rather than 65535.
*   Fixed a bug where starting two dammif runs in the same window (running it
    again after either aborting or letting the current runs finish) did not clear the old log tabs.
*   Fixed a bug where entering a wavelength longer than ~115 A resulted in an
    error. Now a window pops up informing you of the error and you have to re-enter the wavelength value.
*   Fixed a bug where the quick reduce dialog was not displaying, and thus quick reduce could not be used.
*   Profiles reduced using quick reduce will now have a q range corresponding to
    the start/end skip points in RAW, consistent with items loaded into RAW and saved from there.
*   Fixed a bug where certain .fit files and FoXS .dat files with 4 columns would not plot properly.
*   Fixed a bug where the x and y axis values of the Guinier plot were not updating when the data range was changed
*   Relabeled the residual plot in the Guinier window with the correct axis labels.
*   Updated how GNOM, BIFT, an Guinier plots are refreshed for improved speed and to remove certain display glitches.
*   Changed the header display in the image panel to be read only (since changes there were not saved).
*   Removed the automation and SANS options panels, as they had no effect. These may be reenabled in the future.
*   Changed the default bin size in RAW for q spacing from 2 to 1.
*   Removed some extraneous print statements.
*   Cleaned up RAWAnalysis.py code and some code in SASFileIO.py
*   Added ability to load .fir files.
*   Fixed a bug where most of the new image types added in RAW 1.0.2 were not being recognized by RAW.


1.0.2
-------

Release date: 2016-06-22

Overview
^^^^^^^^^

We're happy to announce that we're releasing RAW 1.0.2. This is another version
focusing on small bug fixes and speed improvements, to try to increase the stability
and usability of the software. As always, please report any bugs you find to us, so
we can fix them!

The one major change is the inclusion of the fabIO package (https://pypi.python.org/pypi/fabio)
for opening images. This has allowed us to support a number of new image types. RAW now
supports images in the following formats:

*   Pilatus TIff
*   CBF
*   SAXSLab300
*   ADSC Quantum
*   Bruker
*   Gatan Digital Micrograph
*   EDNA-XML
*   ESRF EDF
*   FReLoN
*   Nonius KappCCD
*   Fit2D spreadsheet
*   FLICAM
*   General Eelctric
*   Hamamatsu CCD
*   HDF5
*   ILL SANS D11
*   MarCCD 165
*   Mar345
*   Medoptics
*   Numpy 2D Array
*   Oxford Diffraction
*   Pixi
*   Portable aNy Map
*   Rigaku SAXS format
*   16 bit TIF
*   32 bit TIF


All changes:
^^^^^^^^^^^^

*   Removed tifffile warnings upon opening RAW
*   Improved the SEC-SAXS online mode based on user feedback to make it easier to work with.
*   Fixed an issue where active masks could be removed from memory when saving config files.
*   Fixed an issue where no warning was being displayed when config files failed to save properly.
*   Improved the speed of selecting large numbers of manipulation, IFT, and SEC items by at least 3 orders of magnitude.
*   Updated how loading and plotting works to improve speed by a factor of ~2.5
    for both loading and subtracting large numbers of items.
*   Updated the Plot Sec button to improve the speed of file loading in certain cases.
*   Fixed a bug where FLICAM images could no longer be loaded due to changes in how tiffs are loaded in pillow >=3.0
*   Removed some possible issues with loading items where files were not getting closed correctly.
*   Fixed an error where rebinning an item under certain conditions could crash RAW.
*   Added a warning if a users tries to update or send frames from a hidden SEC
    curve (assumes that they forgot to change their selection)
*   Fixed a big where sending the same frames twice to the main plot from a SEC
    curve would cause various problems with RAW.
*   IFT items are now marked as modified when they are renamed.
*   Fixed an error caused by clicking on the top item of the advanced options configuration tree
*   Fixed an error in the Image tab where selecting the pan/zoom buttons wouldn't
    always properly toggle the button in the toolbar.
*   Fixed a bug where the popup menu for inverting the mask couldn't show.
*   Fixed a bug where panning or zooming when centering would turn off the silver behenate centering rings
*   Fixed a bug in OS X where holding down the centering arrows didn't continuously move the beam center position
*   Fixed a bug where the centering arrows wouldn't move the beam center in smaller
    than integer steps (when holding them down).
*   Updated the sync function to greatly increase speed when used with lots of items.
*   Updated the superimpose function to greatly increase the speed when used with lots of items.
*   The file panel now automatically refreshes when you switch to the file tab.
*   Added the ability to use the common keyboard shortcut ctrl-A to select all items
    in the manipulation, IFT, and SEC lists.
*   Fixed an issue with the beam center indicator in the masking panel vanishing when it should not.
*   Fixed a bug where error bar color was not maintained when moving a line between different plots.
*   Fixed a bug where the error bar color selector for the manipulation and IFT line
    properties displayed the wrong color in the line properties box.
*   Added the ability to change the calculated line name in the SEC line properties box.
*   Fixed an issue where, if the legend position had been changed, it reset to the
    default position when the legend was updated.
*   Fixed an issue where the legend shadow went away when legend was updated.
*   Added ability to load many more image types using the fabIO library.
*   Fixed a bug where the wrong legend label would sometimes be used for SEC curves in windows.


1.0.1
-------

Release date: 2016-05-23

Overview
^^^^^^^^^

We're very happy to announce that we are releasing RAW 1.0.1. This is a minor release,
concentrating on bug fixes and small changes to the user interface.

There is one very exciting piece of news, which is that this release comes with
a prebuilt windows installer (.msi file)! This should make it much easier for those
on windows to install the program. We're currently working on a similar thing for OS X.

We are also happy to announce that, to the best of our testing, RAW is compatible
with wxpython 3.0 on OS X and Windows (Linux is still a work in progress).


All changes:
^^^^^^^^^^^^

*   Fixed a bug where online mode without an online filter would load files twice.
*   Fixed a bug which caused dammif to crash when run in a directory where the path contained a space.
*   Masking panel now defaults to the beamstop mask, not the ROI mask.
*   Fixed a bug where if OS X preview files became visible on another system, loading them would crash RAW.
*   Fixed an intermittent bug where in scientific linux 6 and wxpython 2.8,
    occasional calls to the File List would crash RAW.
*   Added in error catching, so attempting to load bad .cfg files (either corrupted,
    or non-RAW files with the same extension) doesn't crash RAW.
*   Added in automatic verification of saved .cfg files, to check they can be loaded back into RAW.
*   Scrolling with the third mouse button in the Image plot panel, but outside
    of an image, no longer produces errors in the console.
*   Moving manipulation items between plots now respects visibility of the manipulation items.
*   The plot axes now automatically refresh when the scale or offset of an item
    is changed if the axes are set to autoscale.
*   Tool tips now work in wxpython 3.0 on OS X
*   Selecting the "remove" option in a right click context menu in the Manipulation,
    IFT, or SEC control tabs no longer causes a seg fault in wxpython 3.0 and OS X.
*   Removed MM and conc from Guinier panel, to unify GUi so that MW information is only in the MW panel.
*   Added ability to change online mode directory without going offline and back online.
*   Added a sort to the online mode, so that files should load in order if multiple
    files are detected in a given online mode load sequence.
*   Added a size check to the online mode load, so that if a file fails to load
    because it hadn't finished writing/copying, it should load when it is finished.
*   Removed the Load button in the SEC control panel .SEC items are now loaded automatically once the file is selected.
*   Added an online mode for SEC-SAXS
*   Fixed a bug in how SEC-SAXS data was updated when no parameters were being calculated.
*   Added a feature so that RAW's online mode will not load in files that RAW saves in the online directory.
*   Fixed a bug occasionally preventing the ATSAS directory from being automatically detected.
*   Changing control tabs now automatically clears/loads the info window as appropriate.
*   Fixed a bug with running datgnom from inside RAW that caused it to fail in certain circumstances.


1.0.0
-------

Release date: 2016-05-06

Overview
^^^^^^^^^

Very exciting news, we're moving the project out of beta! That doesn't mean there
aren't still bugs, or that we're done adding features. But it does mean that we're
happy with the current build (and that we ran out of numbers to increment in beta).

The major new features in this release:

*   Added support for running GNOM from RAW
*   Added support for running DAMMIF from RAW
*   Added support for running DAMAVER from RAW
*   Added support for running AMBIMETER from RAW
*   Major overhaul of the IFT panel, so it actually works, which involved changing how BIFT is run.


All other changes:
^^^^^^^^^^^^^^^^^^^

*   Added support for reading in FoXS .dat files that have both experimental and model intensities in them
*   Fixed a bug where after using the Clear SEC data button RAW could still think
    there were unsaved changes in the SEC panel
*   After removing an item from a plot, the plot axes will automatically resize
    \(unless automatic axes size is turned off in plot options)
*   Added a README file in the RAW directory with information on installation and getting help
*   Fixed an issue with the porod volume MW calculator crashing if the scattering
    profile extended to q greater than 0.45 A^-1
*   Fixed a bug where MW for RNA was not properly calculated in the SEC plot
*   Added ability to save all integrated scattering profiles from a SEC curve as dats
*   Fixed an issue where header for save analysis csv files was not using the correct delimiter
*   Fixed an issue where beam center did not initially show up correctly in the centering/calibration panel
*   Fixed a bug where changing font size for the plot title and axis labels had no effect
*   Fixed an issue where the home button in the sec plot didn't work if the calc data existed but was not shown
*   Added complied windows 8 exentions, updated compiled windows 7 extensions.
*   Various other small bug fixes.


1.0.0b
-------

Release date: 2016-03-24

Overview
^^^^^^^^^

We are proud to announce that RAW version 1.0.0b has been released for download!
This version includes a huge number of new features and bug fixes.

Our favorite new features are:

*   Easy processing of in-line SEC-SAXS data
*   New molecular weight panel for calculating mol. weight from the volume of correlation,
    adjusted porod volume, and absolute scaling.
*   AutoRG now available.
*   Uncompiled running, which allows RAW to run as long as the appropriate python
    packages are installed, even if the extension files cannot be compiled.
*   Files saved as .dats now automatically save all analysis information in the
    header, and reload it into RAW when loaded again.

We have also made significant improvements to speed and responsiveness:

*   Sped up loading and plotting for large numbers of files on a test machine by a factor of ~30
*   Sped up subtraction of large numbers of scattering profiles by a factor of ~4
*   Improved responsiveness when large numbers of scattering profiles are plotted.

Also, there are new, up-to-date install guides available for Windows, Mac, and Linux.
Check them out in the files tab.

Finally, we have cleaned up both the code repository and the files area.

If you have questions, or feedback, please contact us!


All changes:
^^^^^^^^^^^^

SEC-SAXS data processing:

Added capability to process SEC-SAXS data. This included adding a new SEC tab in
the control panel, a new SEC plot, and a new SECM data class.

SEC-SAXS data is collected by continuous framing of the detector while sample is
being pumped through a column. The output of that column is connected to the SAXS
cell. The new RAW addition allows users to load all of the detector images collected
during column elution into a new data type, the SECM. The overall frame intensity is
plotted vs. frame number or time, and this should look very similar to the UV-chromatograph
that an FPLC produces. The users can then select a range of frames from this curve, and
send them to the main plot for processing as normal.

Additionally, the users can select a specified buffer range, and an average window
size. The window is then slid across the curve, and the scattering profiles within
the window are averaged. The averaged buffer is subtracted from the curves in the
window, and radius of gyration, molecular weight, and I(0) are automatically calculated.
These are then plotted on the same plot as the 'SAXS chromatograph' (intensity vs.
frame #), allowing users to quickly get a feel for what is in each peak they measured.

Major code additions:

*   There is now a SEC Panel, SEC Item panel, and SEC Control panel class, based
    on the Manipulation panel and Item Panel in RAW.py.
*   There is now a new plot class in RAWPlot.py, the SECPlot, which allows for
    multiple axes on the same plot, and handles the various plotting options.
*   There is a SECM class in SASM.py, which is the data structure for this new thing.
*   There is a new SASCalc.py file, which contains the autorg and automw functions.
    The autorg is pure python, based on the ATSAS package autorg function. It could
    probably use some tuning of the various parameters. The automw is also purely
    python, and based on the Rambo & Tainer correlation volume method for determining molecular weight.
*   There is a new save/load format, extension .sec, for saving SEC objects.
*   The SEC data is saved when the workspace is saved.
*   Various bits and pieces everywhere have been adjusted to accommodate these new panels.

Online mode filtering:

*   Added an online mode section in the advanced option panel. This allows you to
    turn on online filtering, and give a set of strings that allow you to ignore
    certain files when they enter the watched folder. You can either set a list
    of strings in the file name to ignore, or a list of strings that must be in
    the file name, or some combination. You can also set the location where these
    strings must occur: at the start, end, or anywhere.

MW Panel:

*   Added a new analysis panel for finding MW. It has methods for MW by I(0)
    ratio (also in Guinier plot), MW by the Rambo & Tainer method of the volume
    of correlation, MW by the Porod volume (corrected by the method of Fisher),
    and MW by absolute intensity.
*   Users can modify default calculation values for the MW in the advanced options MW panel.

Speed improvements:

*   Changed the loadAndPlot function so that it only updates the curves on the
    plot every 20 curves loaded (and at the end), and only updates the legend
    after all the curves are loaded. On my machine, for ~400 data files (pilatus
    100K tiffs) this sped up loading and plotting by ~30x (~40 s vs. 20 minutes & 15 s).
*   Changed the subtractItems function so that it only updates the curves on the
    plot every 20 curves loaded (and at the end), and only updates the legend after
    all the curves are loaded, as with the _loadAndPlot function. On my machine,
    this sped up subtraction by ~4x (1 min 7 s vs. 4 min 5 s for ~400 manipulation items).
*   Updated online mode to take advantage of the faster plotting, by passing all
    of the files to be plotted to ‘loadAndPlot’ at once, rather than one at a time
    \(will only matter if files are coming in faster than the online mode update timer)
*   Changed the legend to be off by default (since it significantly hinders
    performance). Changed the update legend and the legend plot options dialog
    functions so that this all still works. This seemed to improve load in performance
    for ~400 data files by ~15% (35 s compared to 40 s).

Uncompiled running:

*   Removed all attempts to compile unused extensions.
*   Added in try/except cycles for importing and compiling compiled extensions.
*   Rewrote compiled extensions scipy.weave code (essentially c code) as pure python.
*   Set it so that if RAW is unable to compile extensions, it displays a warning
    message to users on startup, and then runs with the pure python versions.
*   Compilation is particularly an issue on windows, so hopefully this will make
    deploying to windows much easier (even though the program will run slower).
    Particularly for versions where a windows installer is not available.
*   This required the inclusion of a RAWGlobals file, which contains a variable
    that notes whether or not the compiled extensions were successfully imported.

Minor changes:

*   Switched from PIL to pillow. PIL is not longer under active development, pillow
    is a fork of PIL that is still supported. Also, pillow is included in the default
    enthought python installation, while PIL no longer is.
*   Fixed an issue where integrated scattering profiles could end up with different
    numbers of points. This was simply disabling the zero trim command in the integration routine.
*   Added in an option to skip points at the end of a scattering profile (identical
    to the skip at the beginning). This was needed after the removal of the zero
    trim command when you have entire range of high q masked out (such as to
    eliminate shadowing from the beam pipe). This setting is accessible in the
    advanced options calibration dialog.
*   Added in a parse function and header profile for log files from the BioCAT beamline.
*   Removed the requirement that the beam position be an integer.
*   Added in the ability to add a ‘zero line’ to the main plots (a horizontal
    line at y=0), in the plot options dialog.
*   Fixed the plot options dialog so that it can be opened when no items are loaded in the plot.
*   Fixed how the plot options dialog handles legend settings, so it doesn’t break
    if there are no curves already plotted.
*   Fixed plot options so that setting x limits and y limits when auto limits
    is not checked actually affects the graph. Also fixed the limits so that they
    properly acquire the current axis limits when plot options is opened.
*   Made it so that turning auto fitting axes back on forces the plot to autofit
    the axes when the plot option dialog is closed with the okay button.
*   Fixed a bug where the legend would turn on when an item was hid/shown in the
    manipulation panel, even if the legend was previously turned off.
*   Fixed a bug where error bars didn’t turn off when an item was hidden in the
    manipulation panel with error bars turned on.
*   Made it so that the borders check boxes in the plot options window actually
    cause the borders (and tick marks) to turn on and off in the plot.
*   Changed the Guinier plot panel so that it automatically updates the MW when
    the concentration is entered (instead of needing one of the up/down arrows
    to be hit in the spin control)
*   Fixed a bug where the MW of a SASM object wasn’t updated when the SASM object
    was set as a MW standard.
*   Fixed a bug in the menu creation of the file browser pane where the right
    click menu wouldn’t open on a mac (wxpython >=2.9.2.4)
*   Fixed a bug where the concentration of a sasm object was getting improperly
    set when the clearinfo function in the information panel was called.
*   Made the info panel Rg, MW, and I(0) boxes read only, since user modified
    values in those boxes aren’t saved
*   Made the info panel conc box update whenever it gets text, so that if you
    update the concentration and click on another sasm it still saves the concentration.
*   Fixed the options window not opening at the right size.
*   Switched to using json to save/load sasm parameter dictionary contents in .dat files.
    This allows easy saving and loading of dictionaries in human readable format. So
    now all parameters (header, counters, analysis, etc) are loaded. NOTE: THIS
    IS NOT STRICTLY BACKWARD COMPATIBLE. RAW can still load old .dat files (and
    primus .dat files), but it cannot load analysis information out of the old
    files. This doesn’t really affect anything, as for the old files the analysis
    information didn’t load anyways.
*   Modified how saving of averaged files history is done. Added in saving of
    subtracted files history. Now all of the averaging and subtracting manipulation
    history of a file is saved in the history entry of the parameters dictionary.
    This works even when you average or subtract files that are already averaged or
    subtracted. It is mostly human readable in the saved .dat file (though as you
    get more layers deep in averaging or subtracting it gets hard to tell what is what).
*   Fixed a bug where the correct qmin and qmax weren’t loading in the Guinier
    window when a previous Guinier analysis had been done.
*   Changed it so that when guinier or mol. weight analysis is done, if the results
    are different from previous analysis, the scattering profile is marked as modified
    to denote that the results are not saved.
*   Fixed a bug where plot axes didn’t auto resize when curves were moved from the
    top main plot to the bottom main plot and vice versa.
*   Fixed a bug where selecting ‘Help!’ in the help menu crashed RAW. No in-program
    help is yet available, but a message dialog now tells the user to look for help
    on the raw project homepage.
*   Set ‘okay’ button to be selected by default in the welcome window.
*   Fixed a bug where on mac, last saved settings wouldn’t load from the dialog
    on startup (this may have also been affecting other OSes).
*   Enabled normalization by ROI counter using an ‘ROI counter mask’ (formerly
    called a transparent beamstop mask).
*   Fixed a bug where minor tick marks weren’t turning off for log axes that weren’t
    shown (such as top and right) (I believe this was introduced by an updated version
    of matplotlib, I don’t remember seeing it before).
*   Fixed the logarithmic image scale display in the image panel. It works now,
    and is enabled.
*   Disabled nexus support to remove error on starting raw (can be easily re-enabled,
    it is simply commented out in a couple places in SASFileIO).
*   Updated the manipulation and IFT item saves so that it offers the choice to
    rename the file when saving a single file, and so that there are more explicit
    instructions when saving multiple files.
*   Fixed a bug in the rebin function, where it wasn’t setting the qrange according
    to the original sasm.
*   Fixed a bug where comparison of q vectors to test for subtraction was done
    by length rather than elementwise by q.
*   When scattering profiles with different q vectors are subtracted, choosing
    to force the subtraction now actually carries out the subtraction (with appropriate
    matching/rebinning of the q vectors).
*   Fixed a bug so that the average function now tests the q vectors point wise,
    rather than by length, to make sure they actually match.
*   Added a feature to export all analysis information from sasm objects as an
    alternative to selecting which analysis features you want to save.
*   Update the old save analysis feature to be called ‘save item info’ in the menu,
    since it can save things that aren’t analysis. Updated the layout of that window
    a little bit, and added ability to save the new MW analysis info into the item.
*   Added scattering profile manipulation into the tools menu: average, subtract, merge,
    rebin, interpolate, normalize by concentration, change q scale, set as MW standard.
*   Upon quitting, RAW now checks whether there are unsaved changes to manipulation or
    SEC items, and asks for confirmation of quitting if there are.
*   Added show image, show data, show header options to the view menu.
*   File list maintains sort order upon refresh.
*   Doing a Guinier fit on a scattering profile that is all zeros no long crashes RAW.
*   Subtraction can handle mismatched q vectors.
*   Autosave for averaged and subtracted files now available.
*   Features supporting SAXSLab300 image format now available.
