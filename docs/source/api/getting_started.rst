Getting Started
-------------------

This will guide you through several basic tasks using the API, including how
to import the API, load settings, and load and save data. Specific file names
refer to the RAW Tutorial Data, which you can download. File paths are given
from the top level directory of that data.


Importing the API
^^^^^^^^^^^^^^^^^

Once installed, the RAW API is imported just like any other python package.
We recommend that you import just the RAWAPI package, as in the following example.

.. code-block:: python

    import bioxtasraw.RAWAPI as raw


Loading settings
^^^^^^^^^^^^^^^^^

Many functions in the API use RAW settings to provide certain parameters for
the function (e.g. the calibration parameters and mask used to radially average
images). So it is a good idea to load a settings file at the start of your
program.

.. code-block:: python

    my_settings = raw.load_settings('./standards_data/SAXS.cfg')

While settings can be created and saved using the API, we recommend using the
RAW GUI to create and save your settings, then importing them into the API.


Loading data
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Usually you'll need to start by loading data into your program. Here we
show how to load images, profiles, IFTs, and series.


Loading images as scattering profiles
***************************************

One of the most common tasks is loading images and radially averaging them
into 1D scattering profiles. This is easily accomplished with the API.

.. code-block:: python

    ##Define a list of image filenames to load.
    buffer_images = ['./standards_data/GIbuf2_A9_18_001_0000.tiff',
        './standards_data/GIbuf2_A9_18_001_0001.tiff']

    #Load and radially average images
    profiles, imgs = raw.load_and_integrate_images(buffer_images, my_settings)

Loading scattering profiles
***************************************

Another common task is loading data that is already saved as a 1D scattering
profile, usually a .dat file.

.. code-block:: python

    #Define a list of profile filenames to load
    profile_names = ['./reconstruction_data/glucose_isomerase.dat']

    #Load the profiles
    profiles = raw.load_profiles(profile_names)

Loading inverse Fourier transforms (IFTs)
******************************************

You can use the API to load IFT files containing P(r) functions, either GNOM
.out files or .ift files from RAW's BIFT algorithm.

.. code-block:: python

    #Define a list of IFT filenames to load
    ift_names = ['./reconstruction_data/gi_complete/glucose_isomerase.out',
        './reconstruction_data/gi_complete/glucose_isomerase.ift']

    #Load the IFTs
    ifts = raw.load_ifts(ift_names)

Loading series
******************

There are two ways you can load a series. The first is loading a .hdf5 or .sec
series file saved by RAW.

.. code-block:: python

    #Define a list of series filenames to load
    series_names = ['./sec_data/phehc_sec.hdf5', './sec_data/xylanase.hdf5']

    #Load the series
    series = raw.load_series(series_names)

Alternatively, you can load in all of the individual profiles in the series,
then use the API to convert those set of profiles into a series.

.. code-block:: python

    import glob

    #Define a list of profile filenames to load
    profile_names = sorted(glob.glob('./sec_data/sec_sample_2/BSA_001_*.dat'))

    #Load the profiles
    profiles = raw.load_profiles(profile_names)

    #Convert the profiles to a series
    series = raw.profiles_to_series(profiles)

Note that the input profiles should be in the order they appear in the series.


Working with profiles
^^^^^^^^^^^^^^^^^^^^^^^^

RAW uses a custom defined class called a SASM (SAS measurement) to contain
information about scattering profiles, including the q, I, and uncertainty data
as well as metadata data about analysis results.

Accessing q, I, and uncertainty data
************************************

RAW SASMs contain several different versions of the q, I, and uncertainty data.
Most commonly, you'll want to access the data using the ``getQ()``, ``getI()``
and ``getErr()`` functions

.. code-block:: python

    profile_names = ['./reconstruction_data/glucose_isomerase.dat']
    profiles = raw.load_profiles(profile_names)

    gi_profile = profiles[0]

    q = gi_profile.getQ()
    intensity = gi_profile.getI()
    error = gi_profile.getErr()

This contains data that has been truncated, scaled and offset according to the
profile settings. If you want to access the scaled, offset, and un-truncated
data (e.g. without zeros at the beginning skipped for loaded images) you can
access ``profile.q``, ``profile.i`` and ``profile.err`` attributes. If there is
any truncation, you can get that using ``profile.getQrange()``. So, for example

.. code-block:: python

    q_range = gi_profile.getQrange()

    gi_profile.getQ() == gi_profile.q[q_range[0]:q_range[1]]
    gi_profile.getI() == gi_profile.i[q_range[0]:q_range[1]]
    gi_profile.getErr() == gi_profile.err[q_range[0]:q_range[1]]

are all true.

If you want the raw profile data, without any truncation, scaling, or offset,
you can use the ``getRawQ()`` ``getRawI()`` and ``getRawErr()`` functions.

Analyzing the profile
**********************

Many of the RAW analysis functions act on a single scattering profile. For
example, to automatically find the best range for the Guinier fit and
calculate the Rg and I(0), you can do:

.. code-block:: python

    guinier_results = raw.auto_guinier(gi_profile)

Accessing profile metadata
****************************

The profile saves various bits of metadata to a dictionary. If the profile
was created by RAW this includes information on how the profile was created and
various metadata parameters from the data collection. It also includes analysis
information. To get all of the metadata you can do:

.. code-block:: python

    metadata = gi_profile.getAllParameters()

To get a specific category of metadata,

.. code-block:: python

    analysis = gi_profile.getParameter('analysis')

    guinier_rg = analysis['guinier']['Rg']


Working with IFTs
^^^^^^^^^^^^^^^^^^

RAW uses a custom defined class called a IFTM (IFT measurement) to contain
information about IFTs, including the P(r) function, the fit of the P(r)
function to the data, and metadata about the P(r) function.

Access the P(r) function and fit
**********************************

All of the P(r) data and fit is accessible as attributes of the class.

.. code-block:: python

    ift_names = ['./reconstruction_data/gi_complete/glucose_isomerase.out']
    ifts = raw.load_ifts(ift_names)

    gi_ift = ifts[0]

    #Get the P(r) function itself
    p = gi_ift.p #P(r)
    r = gi_ift.r
    err = gi_ift.err #Uncertainty in P(r)

    #Get the original data and the P(r) fit to the original data
    q = gi_ift.q_orig
    i = gi_ift.i_orig
    err = gi_ift.err_orig
    fit = gi_ift.i_fit

    #Get the fit extrapolated to q=0.
    q_extrap = gi_ift.q_extrap
    fit_extrap = gi_ift.i_extrap

Analyzing the IFT
******************

There are several functions that take the IFTM as input for analysis, including
ambimeter and the various 3D reconstruction methods. Note that analysis methods
from the ATSAS package require a GNOM IFT, whereas those natively implemented
in RAW (DENSS) work on either GNOM or BIFT IFTs.

.. code-block:: python

    score, categories, evaluation = raw.ambimeter(gi_ift)

Accessing IFT metadata
************************

IFT metadata can be accessed in the same way as for profiles:

.. code-block:: python

    metadata = gi_ift.getAllParameters()

    dmax = gi_ift.getParameter('dmax')


Working with series
^^^^^^^^^^^^^^^^^^^

RAW uses a custom defined class called a SECM (SEC measurement, a slightly
outdated name) to contain information about series, including the individual
scattering profiles, total and mean intensity as a function of frame number,
and calculated parameters such as R\ :sub:`g` as a function of frame number.

Accessing the series data
**************************

In order to visualize the series data it is common to plot total or mean
intensity as a function of frame number. You can get that data as:

.. code-block:: python

    series_names = ['./sec_data/baseline.hdf5']
    series = raw.load_series(series_names)

    my_series = series[0]

    frames = my_series.getFrames()
    total_i = my_series.getIntI()
    mean_i = my_series.getMeanI()

The calculated parameter data is similarly accessed:

.. code-block:: python

    rg = my_series.getRg()
    i0 = my_series.getI0()
    mw_vc = my_series.getVcMW()[0]
    mw_vp = my_series.getVpMW()[0]

The intensity for subtracted of baseline corrected data is accessed by specifying
the data type

.. code-block:: python

    subtracted_total_i = my_series.getIntI('sub')
    subtracted_mean_i = my_series.getMeanI('sub')

Note that for data with baseline corrected profiles you would use 'baseline'

If you want to access the underlying profiles, it is done similarly.

.. code-block:: python

    #Gets all profiles in the series
    profiles = my_series.getAllSASMs()
    sub_profiles = my_series.getAllSASMs('sub')

    #Gets a single profile in the series, zero indexed
    profile_5 = my_series.getSASM(5)
    sub_profile_5 = my_series.getSASM(5, 'sub')

    #Get profiles from the series in a given range, zero indexed
    profiles_roi = my_series.getSASMList(10, 20)
    sub_profiles_roi = my_series.getSASMList(10, 20, 'sub')

Analyzing the series
*********************

Any analysis you can do on series in the GUI can be done with the API. For
example, to automatically find a good buffer region:

.. code-block:: python

    success, region_start, region_end = raw.find_buffer_range(my_series)

Accessing series metadata
***************************

Series in RAW have a lot of associated metadata, such as the buffer range
used for subtraction, the start and end of the baseline correction ranges,
or the sample range. Most of these are accessible as attributes of the SECM.

.. code-block:: python

    buffer_range = my_series.buffer_range
    sample_range = my_series.sample_range


Saving data
^^^^^^^^^^^^^^^

After you process your data you will want to save it. Here we show how to save
profiles, IFTs, and series.

Saving scattering profiles
***************************

Suppose you have the scattering profile ``my_profile``. You would save the
profile as:

.. code-block:: python

    raw.save_profile(my_profile, 'my_profile.dat', './my_profile_dir')

Saving inverse Fourier transforms (IFTs)
********************************************

Suppose you have the IFT ``my_ift``. You would save the IFT as:

.. code-block:: python

    raw.save_ift(my_ift, 'my_ift.out', './my_ift_dir')

Note that you use the ``.out`` extension for GNOM IFTs, and the ``.ift``
extension for BIFT IFTs.

Saving series
**************

Suppose you have the series ``my_series``. You would save the series as:

.. code-block:: python

    raw.save_series(my_series, 'my_series.hdf5', './my_series_dir')
