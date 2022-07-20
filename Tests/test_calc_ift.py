import os
import shutil

import pytest
import numpy as np

raw_path = os.path.abspath(os.path.join('.', __file__, '..', '..'))
if raw_path not in os.sys.path:
    os.sys.path.append(raw_path)

import bioxtasraw.RAWAPI as raw
import bioxtasraw.SASCalc as SASCalc

@pytest.mark.atsas
def test_ambimeter(gi_gnom_ift):
    score, categories, evaluation = raw.ambimeter(gi_gnom_ift)

    assert score == 0
    assert categories == 1

@pytest.mark.atsas
@pytest.mark.slow
def test_dammif(gi_gnom_ift, temp_directory):

    chi_sq, rg, dmax, mw, excluded_volume = raw.dammif(gi_gnom_ift, 'dammif',
        temp_directory, 'Fast')

    atsas_dir = raw.__default_settings.get('ATSASDir')
    version = SASCalc.getATSASVersion(atsas_dir).split('.')

    if (int(version[0]) == 3 and int(version[1]) < 1) or int(version[0]) < 3:
        assert os.path.exists(os.path.join(temp_directory, 'dammif-1.pdb'))
    else:
        assert os.path.exists(os.path.join(temp_directory, 'dammif-1.cif'))

    assert os.path.exists(os.path.join(temp_directory, 'dammif.fit'))
    assert os.path.exists(os.path.join(temp_directory, 'dammif.fir'))
    assert os.path.exists(os.path.join(temp_directory, 'dammif.in'))


@pytest.mark.atsas
@pytest.mark.slow
def test_dammif_interactive(gi_gnom_ift, temp_directory):
    chi_sq, rg, dmax, mw, excluded_volume = raw.dammif(gi_gnom_ift, 'dammif_inter',
        temp_directory, 'Custom', dam_radius=3.1, harmonics=15, max_steps=200,
        max_iters=20000, max_success=2000, min_success=20, T_factor=0.9,
        rg_penalty=0.1e-2, center_penalty=0.1e-4, loose_penalty=0.1e-1)

    atsas_dir = raw.__default_settings.get('ATSASDir')
    version = SASCalc.getATSASVersion(atsas_dir).split('.')

    if (int(version[0]) == 3 and int(version[1]) < 1) or int(version[0]) < 3:
        assert os.path.exists(os.path.join(temp_directory, 'dammif_inter-1.pdb'))
    else:
        assert os.path.exists(os.path.join(temp_directory, 'dammif_inter-1.cif'))

    assert os.path.exists(os.path.join(temp_directory, 'dammif_inter.fit'))
    assert os.path.exists(os.path.join(temp_directory, 'dammif_inter.fir'))
    assert os.path.exists(os.path.join(temp_directory, 'dammif_inter.in'))

@pytest.mark.atsas
@pytest.mark.very_slow
def test_dammin(gi_gnom_ift, temp_directory):

    chi_sq, rg, dmax, mw, excluded_volume = raw.dammin(gi_gnom_ift, 'dammin',
        temp_directory, 'Fast')

    atsas_dir = raw.__default_settings.get('ATSASDir')
    version = SASCalc.getATSASVersion(atsas_dir).split('.')

    if (int(version[0]) == 3 and int(version[1]) < 1) or int(version[0]) < 3:
        assert os.path.exists(os.path.join(temp_directory, 'dammin-0.pdb'))
        assert os.path.exists(os.path.join(temp_directory, 'dammin-1.pdb'))
    else:
        assert os.path.exists(os.path.join(temp_directory, 'dammin-1.cif'))

    assert os.path.exists(os.path.join(temp_directory, 'dammin.fit'))
    assert os.path.exists(os.path.join(temp_directory, 'dammin.fir'))

@pytest.mark.atsas
@pytest.mark.very_slow
def test_dammin_refine(gi_gnom_ift, temp_directory):
    shutil.copy2(os.path.join('./data/dammif_data', 'glucose_isomerase_damstart.pdb'),
            os.path.join(temp_directory, 'glucose_isomerase_damstart.pdb'))

    chi_sq, rg, dmax, mw, excluded_volume = raw.dammin(gi_gnom_ift, 'dammin_refine',
        temp_directory, 'Fast', initial_dam='glucose_isomerase_damstart.pdb')

    atsas_dir = raw.__default_settings.get('ATSASDir')
    version = SASCalc.getATSASVersion(atsas_dir).split('.')

    if (int(version[0]) == 3 and int(version[1]) < 1) or int(version[0]) < 3:
        assert os.path.exists(os.path.join(temp_directory, 'dammin_refine-0.pdb'))
        assert os.path.exists(os.path.join(temp_directory, 'dammin_refine-1.pdb'))
    else:
        assert os.path.exists(os.path.join(temp_directory, 'dammin_refine-1.cif'))

    assert os.path.exists(os.path.join(temp_directory, 'dammin_refine.fit'))
    assert os.path.exists(os.path.join(temp_directory, 'dammin_refine.fir'))

@pytest.mark.atsas
@pytest.mark.very_slow
def test_dammin_interative(gi_gnom_ift, temp_directory):
    chi_sq, rg, dmax, mw, excluded_volume = raw.dammin(gi_gnom_ift, 'dammin_inter',
        temp_directory, 'Custom', dam_radius=3.7, harmonics=10, max_steps=200,
        max_iters=134820, max_success=13482, min_success=44, T_factor=0.9,
        loose_penalty=6.000E-03, knots=20, sphere_diam=102, coord_sphere=10.43,
        disconnect_penalty=6.000E-03, periph_penalty=0.3000)

    atsas_dir = raw.__default_settings.get('ATSASDir')
    version = SASCalc.getATSASVersion(atsas_dir).split('.')

    if (int(version[0]) == 3 and int(version[1]) < 1) or int(version[0]) < 3:
        assert os.path.exists(os.path.join(temp_directory, 'dammin_inter-0.pdb'))
        assert os.path.exists(os.path.join(temp_directory, 'dammin_inter-1.pdb'))
    else:
        assert os.path.exists(os.path.join(temp_directory, 'dammin_inter-1.cif'))

    assert os.path.exists(os.path.join(temp_directory, 'dammin_inter.fit'))
    assert os.path.exists(os.path.join(temp_directory, 'dammin_inter.fir'))

@pytest.mark.atsas
@pytest.mark.slow
def test_damaver(temp_directory):
    fnames = ['glucose_isomerase_{:02d}-1.pdb'.format(i) for i in range(1, 4)]

    for fname in fnames:
        shutil.copy2(os.path.join('./data/dammif_data', fname),
            os.path.join(temp_directory, fname))

    (mean_nsd, stdev_nsd, rep_model, result_dict, res, res_err,
        res_unit, cluster_list) = raw.damaver(fnames, 'damaver', temp_directory)

    assert np.allclose(mean_nsd, 0.443, rtol=1e-2)

    atsas_dir = raw.__default_settings.get('ATSASDir')
    version = SASCalc.getATSASVersion(atsas_dir).split('.')

    if (int(version[0]) == 3 and int(version[1]) < 1) or int(version[0]) < 3:
        assert stdev_nsd == 0.014
        assert res == 20
        assert res_err == 0
    else:
        assert stdev_nsd == 0.03
        assert res == 18.5339
        assert res_err == -1
        assert len(cluster_list) == 2

@pytest.mark.atsas
@pytest.mark.very_slow
def test_damclust(temp_directory):
    atsas_dir = raw.__default_settings.get('ATSASDir')
    version = SASCalc.getATSASVersion(atsas_dir).split('.')

    if (int(version[0]) == 3 and int(version[1]) < 1) or int(version[0]) < 3:
        fnames = ['glucose_isomerase_{:02d}-1.pdb'.format(i) for i in range(1, 4)]

        for fname in fnames:
            shutil.copy2(os.path.join('./data/dammif_data', fname),
                os.path.join(temp_directory, fname))

        cluster_list, distance_list = raw.damclust(fnames, 'damaver', temp_directory)

        assert len(cluster_list) == 1
        assert len(distance_list) == 0
        assert np.isclose(float(cluster_list[0].dev), 0.43326809411161260, rtol=1e-2)
    else:
        pass
        #DAMCLUST was removed in ATSAS 3.1.0

@pytest.mark.atsas
@pytest.mark.slow
def test_supcomb(temp_directory):
    atsas_dir = raw.__default_settings.get('ATSASDir')
    version = SASCalc.getATSASVersion(atsas_dir).split('.')

    if (int(version[0]) == 3 and int(version[1]) < 1) or int(version[0]) < 3:
        shutil.copy2(os.path.join('./data/dammif_data', 'glucose_isomerase_01-1.pdb'),
            os.path.join(temp_directory, 'glucose_isomerase_01-1.pdb'))

        shutil.copy2(os.path.join('./data/dammif_data', '1XIB_4mer.pdb'),
            os.path.join(temp_directory, '1XIB_4mer.pdb'))

        raw.supcomb('glucose_isomerase_01-1.pdb', '1XIB_4mer.pdb', temp_directory)

        assert os.path.exists(os.path.join(temp_directory,
            'glucose_isomerase_01-1_aligned.pdb'))

    else:
        pass
        #SUPCOMB was removed in ATSAS 3.1.0

@pytest.mark.atsas
def test_cifsup(temp_directory):
    atsas_dir = raw.__default_settings.get('ATSASDir')
    version = SASCalc.getATSASVersion(atsas_dir).split('.')

    if (int(version[0]) == 3 and int(version[1]) >= 1) or int(version[0]) > 3:
        shutil.copy2(os.path.join('./data/dammif_data', 'glucose_isomerase_01-1.pdb'),
            os.path.join(temp_directory, 'glucose_isomerase_01-1.pdb'))

        shutil.copy2(os.path.join('./data/dammif_data', '1XIB_4mer.pdb'),
            os.path.join(temp_directory, '1XIB_4mer.pdb'))

        raw.cifsup('glucose_isomerase_01-1.pdb', '1XIB_4mer.pdb', temp_directory)

        assert os.path.exists(os.path.join(temp_directory,
            'glucose_isomerase_01-1_aligned.pdb'))

    else:
        pass
        #CIFSUP was added in ATSAS 3.1.0

@pytest.mark.slow
def test_denss(gi_gnom_ift, temp_directory):
    (rho, chi_sq, rg, support_vol, side, q_fit, I_fit, I_extrap,
        err_extrap, all_chi_sq, all_rg, all_support_vol) = raw.denss(gi_gnom_ift,
        'denss', temp_directory, 'Fast', seed=1)

    assert os.path.exists(os.path.join(temp_directory, 'denss.mrc'))
    assert os.path.exists(os.path.join(temp_directory, 'denss.log'))
    assert os.path.exists(os.path.join(temp_directory, 'denss_support.mrc'))
    assert os.path.exists(os.path.join(temp_directory, 'denss_map.fit'))
    assert os.path.exists(os.path.join(temp_directory, 'denss_stats_by_step.dat'))
    assert np.allclose(chi_sq, 0.006432532615631702)
    assert np.allclose(rg, 33.39020968091663)
    assert np.allclose(support_vol, 500026.75790405273)
    assert np.allclose(I_fit.sum(), 0.1345053935771273)

@pytest.mark.very_slow
def test_denss_average(temp_directory):
    fnames = ['./data/denss_data/glucose_isomerase_{:02d}.mrc'.format(i)
        for i in range(1, 5)]

    for fname in fnames:
        rhos, sides = raw.load_mrc(fnames)

    (average_rho, mean_cor, std_cor, threshold, res, scores,
        fsc) = raw.denss_average(np.array(rhos), sides[0], 'denss',
        temp_directory, n_proc=2)

    assert np.isclose(average_rho.sum(), 11.779369592666626)
    assert np.isclose(mean_cor, 0.9558480944677593, rtol=1e-3)
    assert np.isclose(std_cor, 0.010040825860950791, rtol=1e-3)
    assert res == 35.1
    assert os.path.exists(os.path.join(temp_directory, 'denss_average.log'))
    assert os.path.exists(os.path.join(temp_directory, 'denss_fsc.dat'))
    assert os.path.exists(os.path.join(temp_directory, 'denss_average.mrc'))

@pytest.mark.very_slow
def test_denss_average_single_proc(temp_directory):
    fnames = ['./data/denss_data/glucose_isomerase_{:02d}.mrc'.format(i)
        for i in range(1, 5)]

    for fname in fnames:
        rhos, sides = raw.load_mrc(fnames)

    (average_rho, mean_cor, std_cor, threshold, res, scores,
        fsc) = raw.denss_average(np.array(rhos), sides[0], 'denss',
        temp_directory, n_proc=1)

    assert np.isclose(average_rho.sum(), 11.779369592666626)
    assert np.isclose(mean_cor, 0.9558480944677593, rtol=1e-3)
    assert np.isclose(std_cor, 0.010040825860950791, rtol=1e-3)
    assert res == 35.1
    assert os.path.exists(os.path.join(temp_directory, 'denss_average.log'))
    assert os.path.exists(os.path.join(temp_directory, 'denss_fsc.dat'))
    assert os.path.exists(os.path.join(temp_directory, 'denss_average.mrc'))

@pytest.mark.very_slow
def test_denss_align(temp_directory):
    rhos, sides = raw.load_mrc(['./data/denss_data/glucose_isomerase_01.mrc'])

    aligned_density, score = raw.denss_align(rhos[0], sides[0], '1XIB_4mer.pdb',
        './data/dammif_data/', save_datadir=temp_directory, n_proc=2)

    assert np.isclose(score, 0.880398898847921)
    assert np.isclose(aligned_density.sum(), 11.779369354248047)

@pytest.mark.very_slow
def test_denss_align_single_proc(temp_directory):
    rhos, sides = raw.load_mrc(['./data/denss_data/glucose_isomerase_01.mrc'])

    aligned_density, score = raw.denss_align(rhos[0], sides[0], '1XIB_4mer.pdb',
        './data/dammif_data/', save_datadir=temp_directory, n_proc=1)

    assert np.isclose(score, 0.880398898847921)
    assert np.isclose(aligned_density.sum(), 11.779369354248047)
