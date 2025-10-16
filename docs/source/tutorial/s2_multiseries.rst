Multi-series analysis
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Sometimes SAXS data is collected in a way where multiple separate datasets
need to be processed together, either averaged or subtracted. A simple
example is if an IEC-SAXS experiment is done and background subtraction is
done by measuring a blank injection in the same gradient and doing a point
by point subtraction of the series with sample and the series without sample.
A more complicated example would be how time-resolved SAXS data is collected
at the BioCAT beamline, where multiple sequential scans along a microfluidic
mixer are collected for a single injection and some of the scans are used
for buffer subtraction while others contain scattering from the sample.

The multi-series analysis tool in RAW provides a robust mechanism for loading
in multiple series at once, carrying out point-by-point averaging and
subtraction across series. Once a subtracted series is created, you can
then carry out further data refinement including truncating and binning q ranges,
averaging together multiple points in a series to improve signal to noise,
removing particular profiles from the series, and calibrating the series.

The written version of the tutorial follows.

Time-resolved SAXS analysis
*****************************

Time resolved SAXS data from the BioCAT beamline is used for this tutorial.
The experiment is a refolding experiment on Cytochrome C. The protein starts
out chemically denatured in a 4.5 M guanidine buffer. It is then diluted 10x
into a refolding buffer using a very fast microfluidic mixer, initiating the
refolding reaction. Timepoints after mixing are obtained by measuring the
scattering some distance along the mixing channel, and are determined by
how long the solution takes to flow from the mixing point to the measurement point.

The basic data collection procedure is as follows: First, flow of mixing and
sample buffers is started. Then, simultaneously, the X-ray exposure and a
continuous scan of the mixer is started. The X-ray beam is scanned along the
observation region, and images are measured while the mixer is moving (a
continuous/fly scan rather than step scan), which is important for minimizing
radiation damage and maximizing throughput. Each exposure along the observation
region corresponds to a different timepoint after mixing. Repeated scans along
the mixer add additional data at the same timepoints, which improves the
signal to noise of the measurement at the timepoint. After sufficient buffer
scans, the sample is injected into the mixer via an injection valve.
Measurements are carried out while all the sample flows through the mixer,
yielding multiple scans with mixed sample measured at every timepoint. Once
all the sample has passed through the mixer, additional scans of just buffer
are measured, yielding pre- and post-sample buffer and sample measurements
at every timepoint as part of the same experiment. If necessary, the
measurement is repeated multiple times to provide good data at each timepoint.
Typically, at least 3 such measurements are made.


This tutorial will take you through loading and carrying out buffer subtraction
on a single measurement, and then averaging multiple such measurements together
to get a final time series.

#.  Clear all of the data in RAW. From the Tools menu select "Multi-Series Analysis"
    to open the multi-series analysis window.

    |ms_panel_png|

#.  There are three ways that you can load multi-series data in RAW. The primary
    way is to use the Select from disk sub-panel, which allows you to pick a directory
    and then define a filename with variables in it that allows RAW to find the
    series of interest. You can also select series that are loaded in the Series
    control panel in RAW with the "Add from series panel" button and for data
    collected at the BioCAT beamline (or with a compatible file naming convention)
    you can load the data in automatically with the "Auto Select" button.


#.  Click the Browse button and select the **Tutorial_Data/multiseres_data/cytc_01**
    folder. This sets the directory where RAW will look for .dat files corresponding
    to your series.

#.  The filename field expects two variables, one corresponding to the series
    number, <s>, and one corresponding to the file number <f>. As with any
    series in RAW, a single series consists of some set of scattering profiles.
    The file number variable lets you define which profiles (.dat files on disk)
    are in a given series, while the series number defines which series to load.
    Take a look at the data in the **cytc_01** folder. You will see filenames
    such as **cytc_01_005_0001_data_000001_00001.dat** and
    **cytc_01_005_0001_data_000002_00002.dat**. If you scroll down a bit you'll
    see filenames such as **cytc_01_005_0010_data_000001_00001.dat**
    The series number is given by the cytc_01_05\ **_0001** and cytc_01_05\ **_0010**
    values, in this case the first file is in series 1 (0001) and the second file
    is in series 10 (0010). The last value in the filename is the file number,
    so **_00001.dat** is the first file in the series, **_00002.dat** the second, and
    so on.

        *   Note: For this time resolved data set, each series represents a single
            scan of the beam down the mixing channel and each file represents a
            single timepoint in that scan. So across all the series the _00001.dat
            files are all measuring the first timepoint, the _00002.dat files the next
            timepoint, and so on.

        *   Tip: File naming convention will vary from facility to facility, so
            make sure you understand the convention for your data.

#.  In the filename field enter *cytc_01_005_<s>_data_0<f>_<f>.dat*. This is a
    filename constructed to make use of the series number, <s>, and file number,
    <f> variables that allow RAW to find all the series and files of interest.
    We'll go through this construction piece by piece.

    #.  If you scroll through all the .dat files in the selected folder, you
        will see that there is an unvarying file prefix: *cytc_01_005_*
        We include this in our filename to match that part of the filename.

    #.  The *<s>* is put in the series number position. This will let RAW
        match the series numbers, we'll define the exact format of this
        next.

    #.  The *_data_0* is again fixed across all files in the folder, so
        similar to the prefix we include that to match the filename.

    #.  The *<f>_<f>.dat* piece makes use of the file number variable
        twice. Looking at the files in the folder you'll see that every
        time the last number in the filename increments the number right
        before it does as well, e.g. _000001_00001.dat, _000002_00002.dat,
        and so on. The last number is the file number,  but in order to
        match the filename we need to increment both, so we use the <f>
        variable twice.

    |ms_filename_png|

#.  Look at the data in the selected folder and make a note of the first and
    last series numbers (should be 0001 and 0090). In the Series # line enter
    1 in the first field and 90 in the second field. In the zero pad field
    enter 4. This tells RAW that wherever you put <s> in the filename it
    should substitute numbers in the range from 1 to 90 (so 1, 2, 3, etc up to 90).
    The zero pad value tells RAW what the string format for these numbers is. In
    this case, it will make the numbers in the filename 4 characters long, and
    any extra characters will be zeros. So series 1 is represented as 0001,
    series 10 as 0010.

    *   Note: If you changed the zero padding to 3, for example, then you
        would get series strings 001 and 010 for series 1 and 10.

#.  Look at the data in the selected folder and make a note of the first and
    last file numbers for a single series (should be 00001 and 00040). In the
    Profiles # line enter 1 in the first field and 40 in the second field.
    In the zero pad field enter 5. This tells RAW that wherever you put <f>
    in the filename it should substitute numbers in the range from 1 to 40,
    with the format of those in the filename defined by the zero padding
    as described above. For example, file number 1 is represented as 00001
    and file number 10 as 00010.

    *   Note: For both series and file number, you don't have to list
        everything in your target folder. You could, for example, load
        just series 5 to 35 instead of 1 to 90, if you used that as the
        series number range.

    |ms_series_file_numbers_png|

#.  An important note is that you can use linux \* and ? wildcards in the filename.
    So in this case we could have defined the filename as *cytc_01_005_<s>_*\ \*\ *<f>.dat*.
    This can be useful if your filename can't be matched strictly with the <s>
    and <f> variables. However, searching for files with wildcards in it
    is significantly slower than getting a defined filename, so you should only
    do this if needed.

#.  Now that the directory, filename, and series and file numbers are all
    defined, click the 'Select files' button. This will search for files
    matching the values you provided in the selected folder. Series that it
    successfully finds will be displayed in the left panel. Note that in the left
    panel you will first see a number, this series ID increments sequentially and will be
    used to identify the series in the next part of the analysis. After that you
    will see the series name, in this case it should be something like *cytc_01_005_0001*.

    *   Tip: Scroll down in the left panel to see all 90 loaded series.

    |ms_series_load_png|

#.  Click on the first series in the left panel. This will display the series
    location and contents Series Info subpanel. Verify that the files contained
    in the series are what you expect. In this case, make sure that each file
    corresponds to series 1 (has _0001 for the series number) and that the file
    number is sequentially incrementing from 1 to 40 (ends with _00001.dat
    to _00040.dat). Also verify that the data directory is correct.

    *   Note: The files are not yet loaded into RAW. Because that can take some
        time, due to the large number of files involved, you have a chance to
        check and make sure you're loading what you want first.

    *   Tip: In the left panel, you can rearrange the series order by selecting
        one or more series (clicking, shift clicking, or control clicking as in
        the RAW control panels) and then clicking the Move up or Move down buttons.
        You can also remove series you don't want to include in the analysis
        using the Remove button.

    *   Tip: The number of profiles is provided in the info panel, and is a good
        way to quickly spot check that you loaded what you expected.

    *   Try: Click on a few other series in the left list and make sure they
        contain the right files.

#.  Click the "Next" button to load in the series data (may take a little bit)
    and advance to the next part of the analysis.

    |ms_series_info_png|

#.  The next portion of the analysis allows you to define buffer and sample
    series in a manner similar to how you define buffer and sample profiles
    for a LC Series dataset. The window shows a plot of total scattering
    intensity for each series. Here, each point corresponds to the sum of
    the total intensity of every profile in the series (for this example data
    set, each point in the sum of intensity from 40 profiles). The series number
    corresponds to the series ID given in the list of series in the loading
    panel.

    *   Note that series IDs are simply sequential for the series loaded, so they
        do not necessarily correspond to the series number as defined by <s>.
        For example, if you'd rearranged the list so that the series with number
        0002 was first in the list and 0001 was second, then the first point in
        this intensity plot would have series ID 1 and correspond to the series
        with number 0002. Or if you'd loaded series 5 to 35, the first point
        in the plot would be series 5 but have series ID 1.

    |ms_intensity_plot_png|

.. |ms_panel_png| image:: images/ms_panel.png
    :target: ../_images/ms_panel.png

.. |ms_filename_png| image:: images/ms_filename.png
    :width: 500 px
    :target: ../_images/ms_filename.png

.. |ms_series_file_numbers_png| image:: images/ms_series_file_numbers.png
    :width: 500 px
    :target: ../_images/ms_series_file_numbers.png

.. |ms_series_load_png| image:: images/ms_series_load.png
    :target: ../_images/ms_series_load.png

.. |ms_series_info_png| image:: images/ms_series_info.png
    :target: ../_images/ms_series_info.png

.. |ms_intensity_plot_png| image:: images/ms_intensity_plot.png
    :target: ../_images/ms_intensity_plot.png
