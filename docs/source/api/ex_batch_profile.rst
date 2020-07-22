Creating a subtracted scattering profile
*****************************************

This example shows how to create a subtracted scattering profile from batch
mode SAXS data. While this particular example uses images as the starting
point, the same process is easily applied to .dat file as well.

.. code-block:: python

    import glob
    import os
    import bioxtasraw.RAWAPI as raw

    #Load settings
    settings = raw.load_settings('./standards_data/SAXS.cfg')

    #Load buffer and sample profiles
    buffer_files = sorted(glob.glob('./standards_data/GIbuf2_A9_18_001_*.tiff'))
    buffers, imgs = raw.load_and_integrate_images(buffer_files, settings)

    sample_files = sorted(glob.glob('./standards_data/GI2_A9_19_001_*.tiff'))
    samples, imgs = raw.load_and_integrate_images(sample_files, settings)

    #Test for similarity between buffer and sample profiles
    buf_pvals, buf_corrected_pvals, buf_failed_comps = raw.cormap(buffers[1:],
        buffers[0])
    sam_pvals, sam_corrected_pvals, sam_failed_comps = raw.cormap(samples[1:],
        samples[0])

    #Average buffer and sample profiles
    buf_avg = raw.average(buffers)
    sam_avg = raw.average(samples)

    #Subtract buffer and sample profiles
    gi_prof = raw.subtract([sam_avg], buf_avg)[0]

    #Save the averaged and subtracted profiles
    if not os.path.exists('./api_results/gi_denss'):
        os.mkdir('./api_results/gi_denss')

    raw.save_profile(buf_avg, datadir='./api_results')
    raw.save_profile(sam_avg, datadir='./api_results')
    raw.save_profile(gi_prof, datadir='./api_results')

