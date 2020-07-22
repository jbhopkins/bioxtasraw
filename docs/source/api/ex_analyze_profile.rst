Analyzing a scattering profile
********************************

One of the most common tasks is analyzing a scattering profile. Here's
an example of how that might be done, from Guinier analysis through creating
a 3D reconstruction.

Guinier fit and MW
+++++++++++++++++++++

.. code-block:: python

    import os
    import shutil
    import numpy as np
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


    #Calculate M.W. using 6 different methods
    mw_ref = raw.mw_ref(gi_prof, 0.47, settings=settings)
    mw_abs = raw.mw_abs(gi_prof, 0.47, settings=settings)
    mw_vp, pvol_cor, pvol, vp_qmax = raw.mw_vp(gi_prof, settings=settings)
    mw_vc, vcor, mw_err, vc_qmax = raw.mw_vc(gi_prof, settings=settings)
    mw_bayes, mw_prob, ci_lower, ci_upper, ci_prob = raw.mw_bayes(gi_prof)
    mw_datclass, shape, dmax_datclass = raw.mw_datclass(gi_prof)


Calculate IFTs
+++++++++++++++

.. code-block:: python

    #Calculate the IFT using BIFT
    (gi_bift, gi_bift_dmax, gi_bift_rg, gi_bift_i0, gi_bift_dmax_err,
        gi_bift_rg_err, gi_bift_i0_err, gi_bift_chi_sq, gi_bift_log_alpha,
        gi_bift_log_alpha_err, gi_bift_evidence,
        gi_bift_evidence_err) = raw.bift(gi_prof, settings=settings)


    #Calculate the IFT using GNOM
    (gi_datgnom_ift, gi_datgnom_dmax, gi_datgnom_rg, gi_datgnom_i0,
        gi_datgnom_rg_err, gi_datgnom_i0_err, gi_datgnom_total_est,
        gi_datgnom_chi_sq, gi_datgnom_alpha, gi_datgnom_quality) = raw.datgnom(gi_prof)


Save the profile and IFTs
++++++++++++++++++++++++++++

.. code-block:: python

    #Save the profile and IFTs
    if not os.path.exists('./api_results'):
        os.mkdir('./api_results')

    raw.save_profile(gi_prof, 'gi.dat', './api_results')
    raw.save_ift(gi_datgnom_ift, 'gi.out', './api_results')
    raw.save_ift(gi_bift, 'gi.ift', './api_results')


    #Calculate the ambiguity using AMBIMETER
    a_score, a_cats, a_eval = raw.ambimeter(gi_datgnom_ift)


Create a bead model reconstruction
+++++++++++++++++++++++++++++++++++

.. code-block:: python

    #Create individual bead model reconstructions
    if not os.path.exists('./api_results/gi_dammif'):
        os.mkdir('./api_results/gi_dammif')
    else:
        files = os.listdir('./api_results/gi_dammif')
        for f in files:
            os.remove(os.path.join('./api_results/gi_dammif', f))

    chi_sq_vals = []
    rg_vals = []
    dmax_vals = []
    mw_vals = []
    ev_vals = []

    for i in range(5):
        chi_sq, rg, dmax, mw, ev = raw.dammif(gi_datgnom_ift,
            'gi_{:02d}'.format(i+1), './api_results/gi_dammif', mode='Fast')

        chi_sq_vals.append(chi_sq)
        rg_vals.append(rg)
        dmax_vals.append(dmax)
        mw_vals.append(mw)
        ev_vals.append(ev)


    #Average the bead model reconstructions
    damaver_files = ['gi_{:02d}-1.pdb'.format(i+1) for i in range(5)]

    (mean_nsd, stdev_nsd, rep_model, result_dict, res, res_err,
        res_unit) = raw.damaver(damaver_files, 'gi',
        './api_results/gi_dammif')


    #Cluster the bead model reconstructions
    cluster_list, distance_list = raw.damclust(damaver_files, 'gi',
        './api_results/gi_dammif')


    #Refine the bead model
    chi_sq, rg, dmax, mw, ev = raw.dammin(gi_datgnom_ift, 'refine_gi',
        './api_results/gi_dammif', 'Refine',
        initial_dam='gi_damstart.pdb')


    #Align the refined bead model with a high resolution structure
    shutil.copy('./reconstruction_data/gi_complete/1XIB_4mer.pdb',
        './api_results/gi_dammif')

    raw.supcomb('refine_gi-1.pdb', '1XIB_4mer.pdb', './api_results/gi_dammif')


Create an electron density reconstruction
+++++++++++++++++++++++++++++++++++++++++++

.. code-block:: python

    #Create individual electron density reconstructions
    if not os.path.exists('./api_results/gi_denss'):
        os.mkdir('./api_results/gi_denss')
    else:
        files = os.listdir('./api_results/gi_denss')
        for f in files:
            os.remove(os.path.join('./api_results/gi_denss', f))

    rhos = []
    chi_vals = []
    rg_vals = []
    support_vol_vals = []
    sides = []
    fit_data = []

    for i in range(5):
        (rho, chi_sq, rg, support_vol, side, q_fit, I_fit, I_extrap,
            err_extrap) = raw.denss(gi_datgnom_ift, 'gi',
            './api_results/gi_denss', mode='Fast')

        rhos.append(rho)
        chi_vals.append(chi_sq)
        rg_vals.append(rg)
        support_vol_vals.append(support_vol)
        sides.append(side)
        fit_data.append([q_fit, I_fit, I_extrap, err_extrap])


    #Average the electron reconstructions
    (average_rho, mean_cor, std_cor, threshold, res, scores,
        fsc) = raw.denss_average(np.array(rhos), side, 'gi_average',
        './api_results/gi_denss')


    #Refine the electron density
    (refined_rho, refined_chi_sq, refined_rg, refined_support_vol, refined_side,
        refined_q_fit, refined_I_fit, refined_I_extrap,
        refined_err_extrap) = raw.denss(gi_datgnom_ift, 'gi_refine',
        './api_results/gi_denss', mode='Fast',
        initial_model=average_rho)


    #Align the electron density with a high resolution structure
    shutil.copy('./reconstruction_data/gi_complete/1XIB_4mer.pdb',
        './api_results/gi_denss')

    aligned_density, score = raw.denss_align(refined_rho, refined_side,
         '1XIB_4mer.pdb', './api_results/gi_denss',
         'gi_refined_aligned', './api_results/gi_denss')
