import os
import copy
import shutil

import pytest
import numpy as np

raw_path = os.path.abspath(os.path.join('.', __file__, '..', '..'))
if raw_path not in os.sys.path:
    os.sys.path.append(raw_path)

import bioxtasraw.RAWAPI as raw

def test_auto_guinier(clean_gi_sub_profile):
    profile = copy.deepcopy(clean_gi_sub_profile)

    (rg, i0, rg_err, i0_err, qmin, qmax, qRg_min, qRg_max, idx_min,
        idx_max, r_sqr) = raw.auto_guinier(profile)

    assert rg == 33.893575007646085
    assert i0 == 0.06158163170868536
    assert rg_err == 0.2411253445992467
    assert i0_err == 0.0003091474210816724
    assert qmin == 0.0147123743
    assert qmax == 0.0389445202
    assert qRg_min == 0.4986549618776146
    assert qRg_max == 1.319969016535488
    assert idx_min == 8
    assert idx_max == 50
    assert r_sqr == 00.9942014318763518

def test_guinier_fit(clean_gi_sub_profile):
    profile = copy.deepcopy(clean_gi_sub_profile)

    (rg, i0, rg_err, i0_err, qmin, qmax, qRg_min, qRg_max,
        r_sqr) = raw.guinier_fit(profile, 0, 42)

    assert rg == 33.29883190131079
    assert i0 == 0.060992517149806996
    assert rg_err == 0.32254864105150266
    assert i0_err == 0.00031800660131762646
    assert qmin == 0.0100967275
    assert qmax == 0.0343288734
    assert qRg_min == 0.33620923177584194
    assert qRg_max == 1.1431113847079795
    assert r_sqr == 0.9905176599909035

def test_mw_ref(clean_gi_sub_profile, old_settings):
    profile = copy.deepcopy(clean_gi_sub_profile)

    mw = raw.mw_ref(profile, settings=old_settings)

    assert mw == 173.86062629638118

def test_mw_abs(clean_gi_sub_profile, old_settings):
    profile = copy.deepcopy(clean_gi_sub_profile)

    mw = raw.mw_abs(profile, settings=old_settings)

    assert np.allclose(mw, 180.38733730964776)

def test_mw_vp(clean_gi_sub_profile, old_settings):
    profile = copy.deepcopy(clean_gi_sub_profile)

    mw, pvol_cor, pvol, qmax = raw.mw_vp(profile, settings=old_settings)

    assert mw == 169.12661474280392
    assert pvol_cor == 203767.0057142216
    assert pvol == 327960.1065457371
    assert qmax == 0.23799429

def test_mw_vc(clean_gi_sub_profile, old_settings):
    profile = copy.deepcopy(clean_gi_sub_profile)

    mw, vcor, mw_err, qmax = raw.mw_vc(profile, settings=old_settings)

    assert mw == 157.024044893903
    assert vcor == 805.9942596873724
    assert mw_err == 12.530923545130383
    assert qmax == 0.282996847

@pytest.mark.atsas
def test_mw_bayes(clean_gi_sub_profile):
    profile = copy.deepcopy(clean_gi_sub_profile)

    mw, mw_prob, ci_lower, ci_upper, ci_prob = raw.mw_bayes(profile)

    assert mw == 169.625
    assert mw_prob == 55.423500000000004
    assert ci_lower == 151.45
    assert ci_upper == 176.6
    assert ci_prob == 98.1173

@pytest.mark.atsas
def test_mw_bayes_i0_from_gnom(clean_gi_sub_profile):
    profile = copy.deepcopy(clean_gi_sub_profile)

    mw, mw_prob, ci_lower, ci_upper, ci_prob = raw.mw_bayes(profile,
        use_i0_from='gnom')

    assert mw == 169.625
    assert mw_prob == 77.6367
    assert ci_lower == 151.45
    assert ci_upper == 176.6
    assert ci_prob == 99.195

@pytest.mark.atsas
def test_mw_bayes_i0_from_bift(clean_gi_sub_profile):
    profile = copy.deepcopy(clean_gi_sub_profile)

    mw, mw_prob, ci_lower, ci_upper, ci_prob = raw.mw_bayes(profile,
        use_i0_from='bift')

    assert mw == 169.625
    assert mw_prob == 77.6367
    assert ci_lower == 151.45
    assert ci_upper == 176.6
    assert ci_prob == 99.195

@pytest.mark.atsas
def test_mw_bayes_first_point(clean_gi_sub_profile):
    profile = copy.deepcopy(clean_gi_sub_profile)

    mw, mw_prob, ci_lower, ci_upper, ci_prob = raw.mw_bayes(profile,
        first=200)

    assert mw == 146.8
    assert mw_prob == 85.2995
    assert ci_lower == 134.3
    assert ci_upper == 151.45
    assert ci_prob == 94.30239999999999

@pytest.mark.atsas
def test_mw_bayes_i0_from_gnom_first_point(clean_gi_sub_profile):
    profile = copy.deepcopy(clean_gi_sub_profile)

    mw, mw_prob, ci_lower, ci_upper, ci_prob = raw.mw_bayes(profile,
        first=200, use_i0_from='gnom')

    assert mw == 146.8
    assert mw_prob == 61.05199999999999
    assert ci_lower == 134.3
    assert ci_upper == 151.45
    assert ci_prob == 94.8295

@pytest.mark.atsas
def test_mw_bayes_i0_from_bift_first_point(clean_gi_sub_profile):
    profile = copy.deepcopy(clean_gi_sub_profile)

    mw, mw_prob, ci_lower, ci_upper, ci_prob = raw.mw_bayes(profile,
        first=200, use_i0_from='bift')

    assert mw == 138.225
    assert mw_prob == 50.6872
    assert ci_lower == 127.45
    assert ci_upper == 151.45
    assert ci_prob == 99.6004

@pytest.mark.atsas
def test_mw_bayes_rg_i0(clean_gi_sub_profile):
    profile = copy.deepcopy(clean_gi_sub_profile)

    mw, mw_prob, ci_lower, ci_upper, ci_prob = raw.mw_bayes(profile,
        rg=32, i0=0.06)

    assert mw == 157.05
    assert mw_prob == 64.0507
    assert ci_lower == 142.15
    assert ci_upper == 176.6
    assert ci_prob == 99.3356

@pytest.mark.atsas
def test_mw_bayes_rg_i0_first(clean_gi_sub_profile):
    profile = copy.deepcopy(clean_gi_sub_profile)

    mw, mw_prob, ci_lower, ci_upper, ci_prob = raw.mw_bayes(profile,
        rg=32, i0=0.06, first=200)

    assert mw == 124.45
    assert mw_prob == 48.2237
    assert ci_lower == 111.25
    assert ci_upper == 127.45
    assert ci_prob == 96.27550000000001

@pytest.mark.atsas
def test_mw_bayes_file(clean_gi_sub_profile):
    profile = copy.deepcopy(clean_gi_sub_profile)

    mw, mw_prob, ci_lower, ci_upper, ci_prob = raw.mw_bayes(profile,
        rg=32, i0=0.06, write_profile=False, datadir=os.path.join('.', 'data'),
        filename='glucose_isomerase.dat')

    assert mw == 157.05
    assert mw_prob == 64.0507
    assert ci_lower == 142.15
    assert ci_upper == 176.6
    assert ci_prob == 99.3356

@pytest.mark.atsas
def test_mw_bayes_file2():
    mw, mw_prob, ci_lower, ci_upper, ci_prob = raw.mw_bayes(None,
        rg=32, i0=0.06, write_profile=False, datadir=os.path.join('.', 'data'),
        filename='glucose_isomerase.dat')

    assert mw == 157.05
    assert mw_prob == 64.0507
    assert ci_lower == 142.15
    assert ci_upper == 176.6
    assert ci_prob == 99.3356

@pytest.mark.atsas
def test_mw_bayes_file3(clean_gi_sub_profile):
    profile = copy.deepcopy(clean_gi_sub_profile)

    mw, mw_prob, ci_lower, ci_upper, ci_prob = raw.mw_bayes(profile,
        rg=32, i0=0.06, first=200, write_profile=False,
        datadir=os.path.join('.', 'data'), filename='glucose_isomerase.dat')

    assert mw == 124.45
    assert mw_prob == 48.2237
    assert ci_lower == 111.25
    assert ci_upper == 127.45
    assert ci_prob == 96.27550000000001

@pytest.mark.atsas
def test_mw_datclass(clean_gi_sub_profile):
    profile = copy.deepcopy(clean_gi_sub_profile)

    mw, shape, dmax = raw.mw_datclass(profile)

    assert mw == 155.236
    assert shape == 'compact'
    assert dmax == 105.85

@pytest.mark.atsas
def test_mw_datclass_rg_from_gnom(clean_gi_sub_profile):
    profile = copy.deepcopy(clean_gi_sub_profile)

    mw, shape, dmax = raw.mw_datclass(profile, use_i0_from='gnom')

    assert mw == 168.006
    assert shape == 'compact'
    assert dmax == 107.56

@pytest.mark.atsas
def test_mw_datclass_rg_from_bift(clean_gi_sub_profile):
    profile = copy.deepcopy(clean_gi_sub_profile)

    mw, shape, dmax = raw.mw_datclass(profile, use_i0_from='bift')

    assert mw == 173.898
    assert shape == 'compact'
    assert dmax == 103.32

@pytest.mark.atsas
def test_mw_datclass_rg_i0(clean_gi_sub_profile):
    profile = copy.deepcopy(clean_gi_sub_profile)

    mw, shape, dmax = raw.mw_datclass(profile, rg=32, i0=0.06)

    assert mw == 164.57
    assert shape == 'compact'
    assert dmax == 94.73

@pytest.mark.atsas
def test_mw_datclass_first_point(clean_gi_sub_profile):
    profile = copy.deepcopy(clean_gi_sub_profile)

    mw, shape, dmax = raw.mw_datclass(profile, first=200)

    assert mw == 145.822
    assert shape == 'compact-hollow'
    assert dmax == 114.89

@pytest.mark.atsas
def test_mw_datclass_rg_from_gnom_first_point(clean_gi_sub_profile):
    profile = copy.deepcopy(clean_gi_sub_profile)

    mw, shape, dmax = raw.mw_datclass(profile, use_i0_from='gnom', first=200)

    assert mw == 145.829
    assert shape == 'compact-hollow'
    assert dmax == 115.04

@pytest.mark.atsas
def test_mw_datclass_rg_from_bift_first_point(clean_gi_sub_profile):
    profile = copy.deepcopy(clean_gi_sub_profile)

    mw, shape, dmax = raw.mw_datclass(profile, use_i0_from='bift', first=200)

    assert mw == 144.814
    assert shape == 'compact-hollow'
    assert dmax == 115.17

@pytest.mark.atsas
def test_mw_datclass_rg_i0_first(clean_gi_sub_profile):
    profile = copy.deepcopy(clean_gi_sub_profile)

    mw, shape, dmax = raw.mw_datclass(profile, rg=32, i0=0.06, first=200)

    assert mw == 121.929
    assert shape == 'compact-hollow'
    assert dmax == 111.84

@pytest.mark.atsas
def test_mw_datclass_file(clean_gi_sub_profile):
    profile = copy.deepcopy(clean_gi_sub_profile)

    mw, shape, dmax = raw.mw_datclass(profile, rg=32, i0=0.06,
        write_profile=False, datadir=os.path.join('.', 'data'),
        filename='glucose_isomerase.dat')

    assert mw == 164.57
    assert shape == 'compact'
    assert dmax == 94.73

@pytest.mark.atsas
def test_mw_datclass_file2():

    mw, shape, dmax = raw.mw_datclass(None, rg=32, i0=0.06,
        write_profile=False, datadir=os.path.join('.', 'data'),
        filename='glucose_isomerase.dat')

    assert mw == 164.57
    assert shape == 'compact'
    assert dmax == 94.73

@pytest.mark.atsas
def test_mw_datclass_file3():

    mw, shape, dmax = raw.mw_datclass(None, rg=32, i0=0.06, first=200,
        write_profile=False, datadir=os.path.join('.', 'data'),
        filename='glucose_isomerase.dat')

    assert mw == 121.929
    assert shape == 'compact-hollow'
    assert dmax == 111.84

@pytest.mark.slow
def test_bift(clean_gi_sub_profile, old_settings, gi_bift_ift):
    (ift, dmax, rg, i0, dmax_err, rg_err, i0_err, chi_sq, log_alpha,
        log_alpha_err, evidence, evidence_err) = raw.bift(clean_gi_sub_profile,
        settings=old_settings, single_proc=False)

    assert np.allclose(dmax, gi_bift_ift.getParameter('dmax'))
    assert np.allclose(rg, gi_bift_ift.getParameter('rg'))
    assert np.allclose(ift.r, gi_bift_ift.r)
    assert np.allclose(ift.p, gi_bift_ift.p)

@pytest.mark.slow
def test_bift_limited_proc(clean_gi_sub_profile, old_settings, gi_bift_ift):
    profile = copy.deepcopy(clean_gi_sub_profile)

    (ift, dmax, rg, i0, dmax_err, rg_err, i0_err, chi_sq, log_alpha,
        log_alpha_err, evidence, evidence_err) = raw.bift(profile,
        settings=old_settings, single_proc=False, nprocs=2)

    assert np.allclose(dmax, gi_bift_ift.getParameter('dmax'))
    assert np.allclose(rg, gi_bift_ift.getParameter('rg'))
    assert np.allclose(ift.r, gi_bift_ift.r)
    assert np.allclose(ift.p, gi_bift_ift.p)

@pytest.mark.slow
def test_bift_single_proc(clean_gi_sub_profile, old_settings, gi_bift_ift):
    profile = copy.deepcopy(clean_gi_sub_profile)

    (ift, dmax, rg, i0, dmax_err, rg_err, i0_err, chi_sq, log_alpha,
        log_alpha_err, evidence, evidence_err) = raw.bift(profile,
        settings=old_settings, single_proc=True)

    assert np.allclose(dmax, gi_bift_ift.getParameter('dmax'))
    assert np.allclose(rg, gi_bift_ift.getParameter('rg'))
    assert np.allclose(ift.r, gi_bift_ift.r)
    assert np.allclose(ift.p, gi_bift_ift.p)

@pytest.mark.atsas
def test_datgnom(clean_gi_sub_profile):
    profile = copy.deepcopy(clean_gi_sub_profile)

    (ift, dmax, rg, i0, rg_err, i0_err, total_est, chi_sq, alpha,
        quality) = raw.datgnom(profile)

    assert dmax == 100.8
    assert rg == 33.35
    assert i0 == 0.06118
    assert round(total_est, 3) == 0.971

@pytest.mark.atsas
def test_datgnom_rg_from_gnom(clean_gi_sub_profile):
    profile = copy.deepcopy(clean_gi_sub_profile)

    (ift, dmax, rg, i0, rg_err, i0_err, total_est, chi_sq, alpha,
        quality) = raw.datgnom(profile, use_rg_from='gnom')

    assert dmax == 101.4
    assert rg == 33.36
    assert i0 == 0.06118
    assert round(total_est, 3) == 0.971

@pytest.mark.atsas
def test_datgnom_rg_from_bift(clean_gi_sub_profile):
    profile = copy.deepcopy(clean_gi_sub_profile)

    (ift, dmax, rg, i0, rg_err, i0_err, total_est, chi_sq, alpha,
        quality) = raw.datgnom(profile, use_rg_from='bift')

    assert dmax == 100.5
    assert rg == 33.35
    assert i0 == 0.06117
    assert round(total_est, 3) == 0.971

@pytest.mark.atsas
def test_datgnom_idx_min(clean_gi_sub_profile):
    profile = copy.deepcopy(clean_gi_sub_profile)

    (ift, dmax, rg, i0, rg_err, i0_err, total_est, chi_sq, alpha,
        quality) = raw.datgnom(profile, idx_min=30)

    assert dmax == 100.8
    assert rg == 33.43
    assert i0 == 0.0614
    assert round(total_est, 3) == 0.963
    assert round(ift.q_orig[0], 6) == round(clean_gi_sub_profile.getQ()[30], 6)

@pytest.mark.atsas
def test_datgnom_idx_max(clean_gi_sub_profile):
    profile = copy.deepcopy(clean_gi_sub_profile)

    (ift, dmax, rg, i0, rg_err, i0_err, total_est, chi_sq, alpha,
        quality) = raw.datgnom(profile, idx_max=300)

    assert dmax == 102.0
    assert rg == 33.16
    assert i0 == 0.061
    assert round(total_est, 3) == 0.96
    assert round(ift.q_orig[-1], 6) == round(clean_gi_sub_profile.getQ()[300], 6)

@pytest.mark.atsas
def test_datgnom_idx_min_max(clean_gi_sub_profile):
    profile = copy.deepcopy(clean_gi_sub_profile)

    (ift, dmax, rg, i0, rg_err, i0_err, total_est, chi_sq, alpha,
        quality) = raw.datgnom(profile, idx_min=30, idx_max=300)

    assert dmax == 97.54
    assert rg == 33.12
    assert i0 == 0.06099
    assert round(total_est, 3) == 0.937
    assert round(ift.q_orig[0], 6) == round(clean_gi_sub_profile.getQ()[30], 6)
    assert round(ift.q_orig[-1], 6) == round(clean_gi_sub_profile.getQ()[300], 6)

@pytest.mark.atsas
def test_datgnom_file(clean_gi_sub_profile):
    profile = copy.deepcopy(clean_gi_sub_profile)

    (ift, dmax, rg, i0, rg_err, i0_err, total_est, chi_sq, alpha,
        quality) = raw.datgnom(profile, rg=33.607769, write_profile=False,
            datadir=os.path.join('.', 'data'), filename='glucose_isomerase.dat')

    assert dmax == 100.8
    assert rg == 33.37
    assert i0 == 0.06119
    assert round(total_est, 3) == 0.971

@pytest.mark.atsas
def test_datgnom_file2():
    (ift, dmax, rg, i0, rg_err, i0_err, total_est, chi_sq, alpha,
        quality) = raw.datgnom(None, rg=33.607769, write_profile=False,
            datadir=os.path.join('.', 'data'), filename='glucose_isomerase.dat')

    assert dmax == 100.8
    assert rg == 33.37
    assert i0 == 0.06119
    assert round(total_est, 3) == 0.971

@pytest.mark.atsas
def test_datgnom_file_idx_min(clean_gi_sub_profile):
    (ift, dmax, rg, i0, rg_err, i0_err, total_est, chi_sq, alpha,
        quality) = raw.datgnom(None, rg=33.607769, idx_min=30, write_profile=False,
            datadir=os.path.join('.', 'data'), filename='glucose_isomerase.dat')

    assert dmax == 100.0
    assert rg == 33.36
    assert i0 == 0.06131
    assert round(total_est, 3) == 0.964
    assert round(ift.q_orig[0], 6) == round(clean_gi_sub_profile.getQ()[30], 6)

@pytest.mark.atsas
def test_datgnom_file_idx_max(clean_gi_sub_profile):
    (ift, dmax, rg, i0, rg_err, i0_err, total_est, chi_sq, alpha,
        quality) = raw.datgnom(None, rg=33.607769, idx_max=300, write_profile=False,
            datadir=os.path.join('.', 'data'), filename='glucose_isomerase.dat')

    assert dmax == 102.0
    assert rg == 33.16
    assert i0 == 0.061
    assert round(total_est, 3) == 0.96
    assert round(ift.q_orig[-1], 6) == round(clean_gi_sub_profile.getQ()[300], 6)

@pytest.mark.atsas
def test_datgnom_file_idx_min_max(clean_gi_sub_profile):
    (ift, dmax, rg, i0, rg_err, i0_err, total_est, chi_sq, alpha,
        quality) = raw.datgnom(None, rg=33.607769, idx_min=30, idx_max=300,
            write_profile=False, datadir=os.path.join('.', 'data'),
            filename='glucose_isomerase.dat')

    assert dmax == 97.54
    assert rg == 33.12
    assert i0 == 0.06099
    assert round(total_est, 3) == 0.937
    assert round(ift.q_orig[0], 6) == round(clean_gi_sub_profile.getQ()[30], 6)
    assert round(ift.q_orig[-1], 6) == round(clean_gi_sub_profile.getQ()[300], 6)

@pytest.mark.atsas
def test_gnom(clean_gi_sub_profile, gi_gnom_ift):
    profile = copy.deepcopy(clean_gi_sub_profile)

    analysis_dict = profile.getParameter('analysis')
    guinier_dict = analysis_dict['guinier']
    idx_min = max(0, int(guinier_dict['nStart']) - profile.getQrange()[0])

    (ift, dmax, rg, i0, rg_err, i0_err, total_est, chi_sq, alpha,
        quality) = raw.gnom(profile, 101)

    assert dmax == gi_gnom_ift.getParameter('dmax')
    assert rg == gi_gnom_ift.getParameter('rg')
    assert np.allclose(ift.r, gi_gnom_ift.r)
    assert np.allclose(ift.p, gi_gnom_ift.p)
    assert round(ift.q_orig[0], 7) == round(clean_gi_sub_profile.getQ()[idx_min], 7)

@pytest.mark.atsas
def test_gnom_idx_min(clean_gi_sub_profile):
    profile = copy.deepcopy(clean_gi_sub_profile)

    (ift, dmax, rg, i0, rg_err, i0_err, total_est, chi_sq, alpha,
        quality) = raw.gnom(profile, 101, idx_min=30)

    assert dmax == 101
    assert rg == 33.44
    assert i0 == 0.06141
    assert np.sum(ift.p) == 0.0080805399
    assert round(ift.q_orig[0], 7) == round(clean_gi_sub_profile.getQ()[30], 7)

@pytest.mark.atsas
def test_gnom_idx_max(clean_gi_sub_profile):
    profile = copy.deepcopy(clean_gi_sub_profile)

    (ift, dmax, rg, i0, rg_err, i0_err, total_est, chi_sq, alpha,
        quality) = raw.gnom(profile, 101, idx_max=300)

    assert dmax == 101
    assert rg == 33.15
    assert i0 == 0.06099
    assert np.sum(ift.p) == 0.0065834595
    assert round(ift.q_orig[-1], 6) == round(clean_gi_sub_profile.getQ()[300], 6)

@pytest.mark.atsas
def test_gnom_idx_min_max(clean_gi_sub_profile):
    profile = copy.deepcopy(clean_gi_sub_profile)

    (ift, dmax, rg, i0, rg_err, i0_err, total_est, chi_sq, alpha,
        quality) = raw.gnom(profile, 101, idx_min=30, idx_max=300)

    assert dmax == 101
    assert rg == 33.21
    assert i0 == 0.06112
    assert np.sum(ift.p) == 0.0062605377
    assert round(ift.q_orig[0], 7) == round(clean_gi_sub_profile.getQ()[30], 7)
    assert round(ift.q_orig[-1], 6) == round(clean_gi_sub_profile.getQ()[300], 6)

@pytest.mark.atsas
def test_gnom_cut_dam(clean_gi_sub_profile):
    profile = copy.deepcopy(clean_gi_sub_profile)

    analysis_dict = profile.getParameter('analysis')
    guinier_dict = analysis_dict['guinier']
    rg = float(guinier_dict['Rg'])
    q = profile.getQ()
    max_q = min(8/rg, 0.3)
    idx_max = np.argmin(np.abs(q-max_q)) -profile.getQrange()[0]

    (ift, dmax, rg, i0, rg_err, i0_err, total_est, chi_sq, alpha,
        quality) = raw.gnom(profile, 101, cut_dam=True)

    assert dmax == 101
    assert rg == 33.37
    assert i0 == 0.06119
    assert np.sum(ift.p) == 0.00761771669
    assert round(ift.q_orig[-1], 6) == round(clean_gi_sub_profile.getQ()[idx_max], 6)

@pytest.mark.atsas
def test_gnom_cut_dam_idx_max(clean_gi_sub_profile):
    profile = copy.deepcopy(clean_gi_sub_profile)

    (ift, dmax, rg, i0, rg_err, i0_err, total_est, chi_sq, alpha,
        quality) = raw.gnom(profile, 101, idx_max=300, cut_dam=True)

    assert dmax == 101
    assert rg == 33.15
    assert i0 == 0.06099
    assert np.sum(ift.p) == 0.0065834595
    assert round(ift.q_orig[-1], 6) == round(clean_gi_sub_profile.getQ()[300], 6)

@pytest.mark.atsas
def test_gnom_not_guinier_start(clean_gi_sub_profile):
    profile = copy.deepcopy(clean_gi_sub_profile)

    (ift, dmax, rg, i0, rg_err, i0_err, total_est, chi_sq, alpha,
        quality) = raw.gnom(profile, 101, use_guinier_start=False)

    assert dmax == 101
    assert rg == 33.36
    assert i0 == 0.06118
    assert np.sum(ift.p) == 0.00833920043
    assert round(ift.q_orig[0], 7) == round(clean_gi_sub_profile.getQ()[0], 7)

@pytest.mark.atsas
def test_gnom_file(clean_gi_sub_profile, gi_gnom_ift):
    profile = copy.deepcopy(clean_gi_sub_profile)

    analysis_dict = profile.getParameter('analysis')
    guinier_dict = analysis_dict['guinier']
    idx_min = max(0, int(guinier_dict['nStart']) - profile.getQrange()[0])

    (ift, dmax, rg, i0, rg_err, i0_err, total_est, chi_sq, alpha,
        quality) = raw.gnom(profile, 101, write_profile=False,
        datadir=os.path.join('.', 'data'), filename='glucose_isomerase.dat')

    assert dmax == gi_gnom_ift.getParameter('dmax')
    assert rg == gi_gnom_ift.getParameter('rg')
    assert np.allclose(ift.r, gi_gnom_ift.r)
    assert np.allclose(ift.p, gi_gnom_ift.p)
    assert round(ift.q_orig[0], 7) == round(clean_gi_sub_profile.getQ()[idx_min], 7)

@pytest.mark.atsas
def test_gnom_file2(clean_gi_sub_profile, gi_gnom_ift):
    (ift, dmax, rg, i0, rg_err, i0_err, total_est, chi_sq, alpha,
        quality) = raw.gnom(None, 101, write_profile=False,
        datadir=os.path.join('.', 'data'), filename='glucose_isomerase.dat')

    assert dmax == gi_gnom_ift.getParameter('dmax')
    assert rg == gi_gnom_ift.getParameter('rg')
    assert np.allclose(ift.r, gi_gnom_ift.r)
    assert np.allclose(ift.p, gi_gnom_ift.p)
    assert round(ift.q_orig[0], 7) == round(clean_gi_sub_profile.getQ()[0], 7)

@pytest.mark.atsas
def test_gnom_file_idx_min(clean_gi_sub_profile):
    profile = copy.deepcopy(clean_gi_sub_profile)

    (ift, dmax, rg, i0, rg_err, i0_err, total_est, chi_sq, alpha,
        quality) = raw.gnom(profile, 101, idx_min=30, write_profile=False,
        datadir=os.path.join('.', 'data'), filename='glucose_isomerase.dat')

    assert dmax == 101
    assert rg == 33.44
    assert i0 == 0.06141
    assert np.sum(ift.p) == 0.0080805399
    assert round(ift.q_orig[0], 7) == round(clean_gi_sub_profile.getQ()[30], 7)

@pytest.mark.atsas
def test_gnom_file_idx_max(clean_gi_sub_profile):
    profile = copy.deepcopy(clean_gi_sub_profile)

    (ift, dmax, rg, i0, rg_err, i0_err, total_est, chi_sq, alpha,
        quality) = raw.gnom(profile, 101, idx_max=300, write_profile=False,
        datadir=os.path.join('.', 'data'), filename='glucose_isomerase.dat')

    assert dmax == 101
    assert rg == 33.15
    assert i0 == 0.06099
    assert np.sum(ift.p) == 0.0065834595
    assert round(ift.q_orig[-1], 6) == round(clean_gi_sub_profile.getQ()[300], 6)

@pytest.mark.atsas
def test_gnom_file_idx_min_max(clean_gi_sub_profile):
    profile = copy.deepcopy(clean_gi_sub_profile)

    (ift, dmax, rg, i0, rg_err, i0_err, total_est, chi_sq, alpha,
        quality) = raw.gnom(profile, 101, idx_min=30, idx_max=300,
        write_profile=False, datadir=os.path.join('.', 'data'),
        filename='glucose_isomerase.dat')

    assert dmax == 101
    assert rg == 33.21
    assert i0 == 0.06112
    assert np.sum(ift.p) == 0.0062605377
    assert round(ift.q_orig[0], 7) == round(clean_gi_sub_profile.getQ()[30], 7)
    assert round(ift.q_orig[-1], 6) == round(clean_gi_sub_profile.getQ()[300], 6)

# Currently not used
# @pytest.mark.atsas
# def test_gnom_interactive(clean_gi_sub_profile):
#     profile = copy.deepcopy(clean_gi_sub_profile)

#     (ift, dmax, rg, i0, rg_err, i0_err, total_est, chi_sq, alpha,
#         quality) = raw.gnom(profile, 101, ah=1)

#     assert dmax == 101
#     assert rg == 33.21
#     assert i0 == 0.06112
#     assert np.sum(ift.p) == 0.0062605377
#     assert round(ift.q_orig[0], 7) == round(clean_gi_sub_profile.getQ()[0], 7)
#     assert round(ift.q_orig[-1], 6) == round(clean_gi_sub_profile.getQ()[-1], 6)

@pytest.mark.atsas
def test_auto_dmax(clean_gi_sub_profile):
    dmax = raw.auto_dmax(clean_gi_sub_profile, single_proc=False)

    assert dmax == 102

@pytest.mark.atsas
def test_auto_dmax_single_proc(clean_gi_sub_profile):
    dmax = raw.auto_dmax(clean_gi_sub_profile, single_proc=False)

    assert dmax == 102

@pytest.mark.slow
def test_auto_dmax_no_atsas(clean_gi_sub_profile):
    dmax = raw.auto_dmax(clean_gi_sub_profile, use_atsas=False)

    assert dmax == 106

@pytest.mark.slow
def test_auto_dmax_single_proc_no_atsas(clean_gi_sub_profile):
    dmax = raw.auto_dmax(clean_gi_sub_profile, single_proc=True, use_atsas=False)

    assert dmax == 106

def test_cormap_all(bsa_series_profiles):
    pvals, corrected_pvals, failed_comparisons = raw.cormap(bsa_series_profiles)

    assert pvals.shape[0] == len(bsa_series_profiles)
    assert pvals.shape[1] == len(bsa_series_profiles)
    assert corrected_pvals.shape[0] == len(bsa_series_profiles)
    assert corrected_pvals.shape[1] == len(bsa_series_profiles)
    assert pvals[0][0] == 1
    assert pvals[0][1] == 0.202088
    assert pvals[5][0] == 0.054454
    assert corrected_pvals[0][0] == 1
    assert corrected_pvals[0][1] == 1
    assert corrected_pvals[5][0] == 1
    assert len(failed_comparisons) == 0

def test_cormap_ref(bsa_series_profiles):
    ref_profile = bsa_series_profiles[0]
    pvals, corrected_pvals, failed_comparisons = raw.cormap(bsa_series_profiles,
        ref_profile)

    assert pvals.shape[0] == len(bsa_series_profiles)
    assert corrected_pvals.shape[0] == len(bsa_series_profiles)
    assert pvals[0] == 1
    assert pvals[1] == 0.202088
    assert pvals[5] == 0.054454
    assert corrected_pvals[0] == 1
    assert corrected_pvals[1] == 1
    assert corrected_pvals[5] == 0.54454
    assert len(failed_comparisons) == 0

@pytest.mark.atsas
@pytest.mark.slow
def test_crysol_model(temp_directory):
    shutil.copy2(os.path.join('./data/dammif_data', '1XIB_4mer.pdb'),
            os.path.join(temp_directory, '1XIB_4mer.pdb'))

    results = raw.crysol([os.path.join(temp_directory, '1XIB_4mer.pdb')])

    results = results['1XIB_4mer']
    abs_profile = results[0]
    fit_profile = results[1]

    abs_params = abs_profile.getParameter('analysis')['crysol']
    fit_params = fit_profile.getParameter('analysis')['crysol']

    assert len(results) == 2
    assert fit_params['Rg'] == 33.22
    assert abs_params['Rg'] == 33.22
    assert fit_params['Excluded_volume'] == 213838
    assert fit_profile.getI().sum() == 4664787183.0
    assert abs_profile.getI().sum() == 1.2894319715

@pytest.mark.atsas
@pytest.mark.slow
def test_crysol_model_settings(temp_directory, old_settings):
    shutil.copy2(os.path.join('./data/dammif_data', '1XIB_4mer.pdb'),
            os.path.join(temp_directory, '1XIB_4mer.pdb'))

    results = raw.crysol([os.path.join(temp_directory, '1XIB_4mer.pdb')],
        settings=old_settings)

    results = results['1XIB_4mer']
    abs_profile = results[0]
    fit_profile = results[1]

    abs_params = abs_profile.getParameter('analysis')['crysol']
    fit_params = fit_profile.getParameter('analysis')['crysol']

    assert len(results) == 2
    assert fit_params['Rg'] == 33.22
    assert abs_params['Rg'] == 33.22
    assert fit_params['Excluded_volume'] == 213838
    assert fit_profile.getI().sum() == 4664787183.0
    assert abs_profile.getI().sum() == 1.2894319715

@pytest.mark.atsas
@pytest.mark.slow
def test_crysol_model_cif(temp_directory):
    shutil.copy2(os.path.join('./data', '2pol.cif'),
            os.path.join(temp_directory, '2pol.cif'))

    results = raw.crysol([os.path.join(temp_directory, '2pol.cif')])

    results = results['2pol']
    abs_profile = results[0]
    fit_profile = results[1]

    abs_params = abs_profile.getParameter('analysis')['crysol']
    fit_params = fit_profile.getParameter('analysis')['crysol']

    assert len(results) == 2
    assert fit_params['Rg'] == 33.19
    assert abs_params['Rg'] == 33.19
    assert fit_params['Excluded_volume'] == 101381.0
    assert fit_profile.getI().sum() == 1108294088.4
    assert abs_profile.getI().sum() == 0.6531660600000001

@pytest.mark.atsas
@pytest.mark.slow
def test_crysol_fit(temp_directory):
    shutil.copy2(os.path.join('./data/dammif_data', '1XIB_4mer.pdb'),
            os.path.join(temp_directory, '1XIB_4mer.pdb'))

    shutil.copy2(os.path.join('./data', 'glucose_isomerase.dat'),
            os.path.join(temp_directory, 'glucose_isomerase.dat'))

    results = raw.crysol([os.path.join(temp_directory, '1XIB_4mer.pdb')],
        [os.path.join(temp_directory, 'glucose_isomerase.dat')])

    results = results['1XIB_4mer_glucose_isomerase']
    fit_profile = results[0]

    fit_params = fit_profile.getParameter('analysis')['crysol']

    assert len(results) == 1
    assert fit_params['Rg'] == 33.22
    assert fit_params['Excluded_volume'] == 213838
    assert fit_params['Chi_squared'] ==  1.089
    assert np.allclose(fit_profile.getI().sum(), 3.72612387712)

@pytest.mark.atsas
@pytest.mark.slow
def test_crysol_fit_settings(temp_directory, old_settings):
    shutil.copy2(os.path.join('./data/dammif_data', '1XIB_4mer.pdb'),
            os.path.join(temp_directory, '1XIB_4mer.pdb'))

    shutil.copy2(os.path.join('./data', 'glucose_isomerase.dat'),
            os.path.join(temp_directory, 'glucose_isomerase.dat'))

    results = raw.crysol([os.path.join(temp_directory, '1XIB_4mer.pdb')],
        [os.path.join(temp_directory, 'glucose_isomerase.dat')],
        settings=old_settings)

    results = results['1XIB_4mer_glucose_isomerase']
    fit_profile = results[0]

    fit_params = fit_profile.getParameter('analysis')['crysol']

    assert len(results) == 1
    assert fit_params['Rg'] == 33.22
    assert fit_params['Excluded_volume'] == 213838
    assert fit_params['Chi_squared'] ==  1.089
    assert np.allclose(fit_profile.getI().sum(), 3.72612387712)

@pytest.mark.new
def test_dift(clean_gi_sub_profile, old_settings, gi_dift_ift):
    (ift, dmax, rg, i0, rg_err, i0_err, chi_sq, alpha) = raw.denss_ift(clean_gi_sub_profile,)

    assert np.allclose(dmax, gi_dift_ift.getParameter('dmax'))
    assert np.allclose(rg, gi_dift_ift.getParameter('rg'))
    assert np.allclose(ift.r, gi_dift_ift.r)
    assert np.allclose(ift.p, gi_dift_ift.p)

@pytest.mark.new
def test_dift_dmax_alpha(clean_gi_sub_profile, old_settings, gi_dift_ift):
    (ift, dmax, rg, i0, rg_err, i0_err, chi_sq, alpha) = raw.denss_ift(clean_gi_sub_profile,
        dmax=114.81772123448121, alpha=8119093695685.446)

    assert np.allclose(dmax, gi_dift_ift.getParameter('dmax'))
    assert np.allclose(rg, gi_dift_ift.getParameter('rg'))
    assert np.allclose(ift.r, gi_dift_ift.r)
    assert np.allclose(ift.p, gi_dift_ift.p)

@pytest.mark.new
def test_pdb2mrc_modelonly(temp_directory, gi_pdb2mrc_modelonly_ift):
    shutil.copy2(os.path.join('./data/dammif_data', '1XIB_4mer.pdb'),
            os.path.join(temp_directory, '1XIB_4mer.pdb'))

    results = raw.pdb2mrc([os.path.join(temp_directory, '1XIB_4mer.pdb')])

    pdb2mrc = results['1XIB_4mer'][0]

    assert np.allclose(pdb2mrc.Rg,gi_pdb2mrc_modelonly_ift.getParameter('rg'))
    assert np.allclose(pdb2mrc.I0,gi_pdb2mrc_modelonly_ift.getParameter('i0'))
    assert np.allclose(pdb2mrc.side,gi_pdb2mrc_modelonly_ift.getParameter('dmax'))

@pytest.mark.new
def test_pdb2mrc_fit(temp_directory, clean_gi_sub_profile, gi_pdb2mrc_fit_ift):
    shutil.copy2(os.path.join('./data/dammif_data', '1XIB_4mer.pdb'),
            os.path.join(temp_directory, '1XIB_4mer.pdb'))

    results = raw.pdb2mrc([os.path.join(temp_directory, '1XIB_4mer.pdb')], profiles=[clean_gi_sub_profile])

    pdb2mrc = results['1XIB_4mer_glucose_isomerase'][0]

    assert np.allclose(pdb2mrc.Rg,gi_pdb2mrc_fit_ift.getParameter('rg'))
    assert np.allclose(pdb2mrc.I0,gi_pdb2mrc_fit_ift.getParameter('i0'))
    assert np.allclose(pdb2mrc.side,gi_pdb2mrc_fit_ift.getParameter('dmax'))
    assert np.allclose(pdb2mrc.chi2,gi_pdb2mrc_fit_ift.getParameter('chisq'))




