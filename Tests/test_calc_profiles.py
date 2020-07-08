import os
import copy

import pytest
import numpy as np

raw_path = os.path.abspath(os.path.join('.', __file__, '..', '..'))
if raw_path not in os.sys.path:
    os.sys.path.append(raw_path)

import bioxtasraw.RAWAPI as raw

def test_auto_guinier(clean_gi_sub_profile):
    (rg, i0, rg_err, i0_err, qmin, qmax, qRg_min, qRg_max, idx_min,
        idx_max, r_sqr) = raw.auto_guinier(clean_gi_sub_profile)

    assert rg == 33.29883190131079
    assert i0 == 0.060992517149806996
    assert rg_err == 0.32254864105150266
    assert i0_err == 0.00031800660131762646
    assert qmin == 0.0100967275
    assert qmax == 0.0343288734
    assert qRg_min == 0.33620923177584194
    assert qRg_max == 1.1431113847079795
    assert idx_min == 0
    assert idx_max == 42
    assert r_sqr == 0.9905176599909035

def test_guinier_fit(clean_gi_sub_profile):
    (rg, i0, rg_err, i0_err, qmin, qmax, qRg_min, qRg_max,
        r_sqr) = raw.guinier_fit(clean_gi_sub_profile, 0, 42)

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
    mw = raw.mw_ref(clean_gi_sub_profile, settings=old_settings)

    assert mw == 173.86062629638118

def test_mw_abs(clean_gi_sub_profile, old_settings):
    mw = raw.mw_abs(clean_gi_sub_profile, settings=old_settings)

    assert np.allclose(mw, 180.38733730964776)

def test_mw_vp(clean_gi_sub_profile, old_settings):
    mw, pvol_cor, pvol, qmax = raw.mw_vp(clean_gi_sub_profile,
        settings=old_settings)

    assert mw == 169.12661474280392
    assert pvol_cor == 203767.0057142216
    assert pvol == 327960.1065457371
    assert qmax == 0.23799429

def test_mw_vc(clean_gi_sub_profile, old_settings):
    mw, vcor, mw_err, qmax = raw.mw_vc(clean_gi_sub_profile, settings=old_settings)

    assert mw == 145.09526582282663
    assert vcor == 774.7748056547058
    assert mw_err == 12.045549627261789
    assert qmax == 0.282996847

def test_mw_bayes(clean_gi_sub_profile):
    mw, mw_prob, ci_lower, ci_upper, ci_prob = raw.mw_bayes(clean_gi_sub_profile)

    assert mw == 169.625
    assert mw_prob == 55.423500000000004
    assert ci_lower == 151.45
    assert ci_upper == 176.6
    assert ci_prob == 98.1173

def test_mw_datclass(clean_gi_sub_profile):
    profile = copy.deepcopy(clean_gi_sub_profile)

    mw, shape, dmax = raw.mw_datclass(profile)

    assert mw == 155.236
    assert shape == 'compact'
    assert dmax == 105.85

@pytest.mark.slow
def test_bift(clean_gi_sub_profile, old_settings, gi_bift_ift):
    (ift, dmax, rg, i0, dmax_err, rg_err, i0_err, chi_sq, log_alpha,
        log_alpha_err, evidence, evidence_err) = raw.bift(clean_gi_sub_profile,
        settings=old_settings)

    assert dmax == gi_bift_ift.getParameter('dmax')
    assert rg == gi_bift_ift.getParameter('rg')
    assert np.allclose(ift.r, gi_bift_ift.r)
    assert np.allclose(ift.p, gi_bift_ift.p)

def test_datgnom(clean_gi_sub_profile):
    (ift, dmax, rg, i0, rg_err, i0_err, total_est, chi_sq, alpha,
        quality) = raw.datgnom(clean_gi_sub_profile)

    assert dmax == 100.8
    assert rg == 33.35
    assert i0 == 0.06118
    assert total_est == 0.9708

def test_gnom(clean_gi_sub_profile, gi_gnom_ift):
    (ift, dmax, rg, i0, rg_err, i0_err, total_est, chi_sq, alpha,
        quality) = raw.gnom(clean_gi_sub_profile, 101)

    assert dmax == gi_gnom_ift.getParameter('dmax')
    assert rg == gi_gnom_ift.getParameter('rg')
    assert np.allclose(ift.r, gi_gnom_ift.r)
    assert np.allclose(ift.p, gi_gnom_ift.p)

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
