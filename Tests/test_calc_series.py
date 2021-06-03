import os
import copy

import pytest
import numpy as np

raw_path = os.path.abspath(os.path.join('.', __file__, '..', '..'))
if raw_path not in os.sys.path:
    os.sys.path.append(raw_path)

import bioxtasraw.RAWAPI as raw


@pytest.fixture(scope="function")
def clean_bsa_series(bsa_series):
    series = raw.load_series([os.path.join('.', 'data',
            'clean_BSA_001.hdf5')])[0]
    return series

@pytest.fixture(scope="package")
def int_baseline_series():
    series = raw.load_series([os.path.join('.', 'data',
            'short_profile_001.hdf5')])[0]
    return series

@pytest.fixture(scope="function")
def clean_baseline_series(int_baseline_series):
    series = copy.deepcopy(int_baseline_series)
    return series

def test_svd(bsa_series):
    svd_s, svd_U, svd_V = raw.svd(bsa_series)
    assert np.allclose(svd_s[0], 7474.750264659797)

def test_svd_list(bsa_series):
    sasms = bsa_series.subtracted_sasm_list

    svd_s, svd_U, svd_V = raw.svd(sasms)
    assert np.allclose(svd_s[0], 7474.750264659797)

def test_efa(bsa_series):
    efa_profiles, converged, conv_data, rotation_data = raw.efa(bsa_series,
        [[130, 187], [149, 230]], framei=130, framef=230)

    assert converged
    assert np.allclose(conv_data['final_step'], 9.254595973975021e-13,
        atol=1e-15, rtol=1e-2)
    assert len(efa_profiles) == 2
    assert np.allclose(efa_profiles[0].getI().sum(), 75885.43573919893)

def test_efa_list(bsa_series):
    sasms = bsa_series.subtracted_sasm_list

    efa_profiles, converged, conv_data, rotation_data = raw.efa(sasms,
        [[130, 187], [149, 230]], framei=130, framef=230)

    assert converged
    assert np.allclose(conv_data['final_step'], 9.254595973975021e-13,
        atol=1e-15, rtol=1e-2)
    assert len(efa_profiles) == 2
    assert np.allclose(efa_profiles[0].getI().sum(), 75885.43573919893)

def test_regals(bsa_series):
    prof1_settings = {
        'type'          : 'simple',
        'lambda'        : 0.0,
        'auto_lambda'   : False,
        'kwargs'        : {},
        }

    conc1_settings = {
        'type'          : 'smooth',
        'lambda'        : 6.0e3,
        'auto_lambda'   : False,
        'kwargs'                : {
            'xmin'              : 130,
            'xmax'              : 187,
            'Nw'                : 50,
            'is_zero_at_xmin'   : False,
            'is_zero_at_xmax'   : True,
            }
        }

    prof2_settings = {
        'type'          : 'simple',
        'lambda'        : 0.0,
        'auto_lambda'   : False,
        'kwargs'        : {},
        }

    conc2_settings = {
        'type'          : 'smooth',
        'lambda'        : 8.0e3,
        'auto_lambda'   : False,
        'kwargs'                : {
            'xmin'              : 149,
            'xmax'              : 230,
            'Nw'                : 50,
            'is_zero_at_xmin'   : True,
            'is_zero_at_xmax'   : False,
            }
        }

    comp_settings = [(prof1_settings, conc1_settings),
        (prof2_settings, conc2_settings)]

    regals_profiles, regals_ifts, concs, reg_concs, mixture, params, residual = raw.regals(bsa_series,
        comp_settings, framei=130, framef=230)

    assert len(regals_profiles) == 2
    assert len(regals_ifts) == 0
    assert np.allclose(regals_profiles[0].getI().sum(), 194.77363667059115)
    assert np.allclose(params['x2'], 1.0332748476863391)
    assert params['total_iter'] == 43

def test_regals_auto_lambda(bsa_series):
    prof1_settings = {
        'type'          : 'simple',
        'lambda'        : 0.0,
        'auto_lambda'   : True,
        'kwargs'        : {},
        }

    conc1_settings = {
        'type'          : 'smooth',
        'lambda'        : 6.0e3,
        'auto_lambda'   : True,
        'kwargs'                : {
            'xmin'              : 130,
            'xmax'              : 187,
            'Nw'                : 50,
            'is_zero_at_xmin'   : False,
            'is_zero_at_xmax'   : True,
            }
        }

    prof2_settings = {
        'type'          : 'simple',
        'lambda'        : 0.0,
        'auto_lambda'   : True,
        'kwargs'        : {},
        }

    conc2_settings = {
        'type'          : 'smooth',
        'lambda'        : 8.0e3,
        'auto_lambda'   : True,
        'kwargs'                : {
            'xmin'              : 149,
            'xmax'              : 230,
            'Nw'                : 50,
            'is_zero_at_xmin'   : True,
            'is_zero_at_xmax'   : False,
            }
        }

    comp_settings = [(prof1_settings, conc1_settings),
        (prof2_settings, conc2_settings)]

    regals_profiles, regals_ifts, concs, reg_concs, mixture, params, residual = raw.regals(bsa_series,
        comp_settings, framei=130, framef=230)

    assert len(regals_profiles) == 2
    assert len(regals_ifts) == 0
    assert np.allclose(regals_profiles[0].getI().sum(), 200.45514174941226)
    assert np.allclose(params['x2'], 0.9949186551912603)
    assert params['total_iter'] == 33

def test_regals_realspace(bsa_series):
    prof1_settings = {
        'type'          : 'realspace',
        'lambda'        : 1e10,
        'auto_lambda'   : False,
        'kwargs'        : {
            'Nw'                : 50,
            'dmax'              : 185,
            'is_zero_at_r0'     : True,
            'is_zero_at_dmax'   : True,
            },
        }

    conc1_settings = {
        'type'          : 'smooth',
        'lambda'        : 6.0e3,
        'auto_lambda'   : False,
        'kwargs'                : {
            'xmin'              : 130,
            'xmax'              : 187,
            'Nw'                : 50,
            'is_zero_at_xmin'   : False,
            'is_zero_at_xmax'   : True,
            }
        }

    prof2_settings = {
        'type'          : 'realspace',
        'lambda'        : 1e11,
        'auto_lambda'   : False,
        'kwargs'        : {
            'Nw'                : 50,
            'dmax'              : 85,
            'is_zero_at_r0'     : True,
            'is_zero_at_dmax'   : True,
            },
        }

    conc2_settings = {
        'type'          : 'smooth',
        'lambda'        : 8.0e3,
        'auto_lambda'   : False,
        'kwargs'                : {
            'xmin'              : 149,
            'xmax'              : 230,
            'Nw'                : 50,
            'is_zero_at_xmin'   : True,
            'is_zero_at_xmax'   : False,
            }
        }

    comp_settings = [(prof1_settings, conc1_settings),
        (prof2_settings, conc2_settings)]

    regals_profiles, regals_ifts, concs, reg_concs, mixture, params, residual = raw.regals(bsa_series,
        comp_settings, framei=130, framef=230)

    assert len(regals_profiles) == 2
    assert len(regals_ifts) == 2
    assert np.allclose(regals_profiles[0].getI().sum(), 40.58942509086738)
    assert np.allclose(params['x2'], 1.5230463212831427)
    assert params['total_iter'] == 33
    assert np.allclose(regals_ifts[0].p.sum(), 0.021077276247305057)

def test_find_buffer_range(bsa_series):
    success, region_start, region_end = raw.find_buffer_range(bsa_series)

    assert success
    assert region_start == 45
    assert region_end == 80

def test_find_buffer_range_list(bsa_series):
    sasms = bsa_series.getAllSASMs()

    success, region_start, region_end = raw.find_buffer_range(sasms)

    assert success
    assert region_start == 45
    assert region_end == 80

def test_validate_buffer_range_good(bsa_series):
    (valid, similarity_results, svd_results,
        intI_results) = raw.validate_buffer_range(bsa_series, [[18, 53]])

    assert valid
    assert similarity_results['all_similar']
    assert similarity_results['low_q_similar']
    assert similarity_results['high_q_similar']
    assert svd_results['svals'] == 1
    assert intI_results['intI_valid']
    assert intI_results['smoothed_intI_valid']
    assert intI_results['intI_pval'] == 0.33394404805178013
    assert intI_results['smoothed_intI_pval'] == 0.02474248231802627

def test_validate_buffer_region_bad(bsa_series):
    (valid, similarity_results, svd_results,
        intI_results) = raw.validate_buffer_range(bsa_series, [[50, 100]])

    assert not valid
    assert not similarity_results['all_similar']
    assert similarity_results['low_q_similar']
    assert not similarity_results['high_q_similar']
    assert similarity_results['all_outliers'][0] == 34
    assert similarity_results['high_q_outliers'][0] == 46
    assert svd_results['svals'] == 1
    assert not intI_results['intI_valid']
    assert not intI_results['smoothed_intI_valid']
    assert intI_results['intI_pval'] == 0.0007815284021663028
    assert intI_results['smoothed_intI_pval'] == 2.8531443061690295e-19

def test_validate_buffer_range_list(bsa_series):
    sasms = bsa_series.getAllSASMs()

    (valid, similarity_results, svd_results,
        intI_results) = raw.validate_buffer_range(sasms, [[18, 53]])

    assert valid
    assert similarity_results['all_similar']
    assert similarity_results['low_q_similar']
    assert similarity_results['high_q_similar']
    assert svd_results['svals'] == 1
    assert intI_results['intI_valid']
    assert intI_results['smoothed_intI_valid']
    assert intI_results['intI_pval'] == 0.33394404805178013
    assert intI_results['smoothed_intI_pval'] == 0.02474248231802627

def test_set_buffer_range(clean_bsa_series):
    (sub_profiles, rg, rger, i0, i0er, vcmw, vcmwer,
        vpmw) = raw.set_buffer_range(clean_bsa_series, [[18, 53]])

    assert len(sub_profiles) == len(clean_bsa_series.getAllSASMs())
    assert rg[200] == 28.359975022504145
    assert rger[200] == 0.27691242689048307
    assert i0[200] == 139.3524947924968
    assert vcmw[200] == 65.39761365015703
    assert vpmw[200] == 69.44895475238502
    assert all(clean_bsa_series.getRg()[0] == rg)
    assert clean_bsa_series.getIntI(int_type='sub').sum() == 331.3353154360302

def test_series_calc(bsa_series):
    sasms = bsa_series.subtracted_sasm_list

    rg, rger, i0, i0er, vcmw, vcmwer, vpmw = raw.series_calc(sasms)

    assert rg[200] == 28.359975022504145
    assert rger[200] == 0.27691242689048307
    assert i0[200] == 139.3524947924968
    assert vcmw[200] == 65.39761365015703
    assert vpmw[200] == 69.44895475238502

def test_find_sample_range(bsa_series):
    success, region_start, region_end = raw.find_sample_range(bsa_series)

    assert success
    assert region_start == 188
    assert region_end == 206

def test_find_sample_range_list(bsa_series):
    sasms = bsa_series.subtracted_sasm_list
    rg = bsa_series.getRg()[0]
    vcmw = bsa_series.getVcMW()[0]
    vpmw = bsa_series.getVpMW()[0]

    success, region_start, region_end = raw.find_sample_range(sasms, rg=rg,
        vcmw=vcmw, vpmw=vpmw)

    assert success
    assert region_start == 188
    assert region_end == 206

def test_validate_sample_range_good(bsa_series):
    (valid, similarity_results, param_results, svd_results,
        sn_results) = raw.validate_sample_range(bsa_series, [[188, 206]])

    assert valid
    assert similarity_results['all_similar']
    assert similarity_results['low_q_similar']
    assert similarity_results['high_q_similar']
    assert svd_results['svals'] == 1
    assert param_results['param_valid']
    assert param_results['rg_valid']
    assert param_results['vcmw_valid']
    assert param_results['vpmw_valid']
    assert param_results['rg_pval'] == 0.9488461264555137
    assert param_results['vcmw_pval'] == 0.3438801731989136
    assert param_results['vpmw_pval'] == 0.6472068934597522
    assert sn_results['sn_valid']

def test_validate_sample_range_bad(bsa_series):
    (valid, similarity_results, param_results, svd_results,
        sn_results) = raw.validate_sample_range(bsa_series, [[190, 210]])

    assert not valid
    assert similarity_results['all_similar']
    assert similarity_results['low_q_similar']
    assert similarity_results['high_q_similar']
    assert svd_results['svals'] == 1
    assert not param_results['param_valid']
    assert not param_results['rg_valid']
    assert param_results['vcmw_valid']
    assert not param_results['vpmw_valid']
    assert param_results['rg_pval'] == 0.0009457098107349513
    assert param_results['vcmw_pval'] == 0.7625997832797398
    assert param_results['vpmw_pval'] == 0.018076642193560675
    assert sn_results['sn_valid']

def test_validate_sample_range_list(bsa_series):
    sasms = bsa_series.subtracted_sasm_list
    rg = bsa_series.getRg()[0]
    vcmw = bsa_series.getVcMW()[0]
    vpmw = bsa_series.getVpMW()[0]

    (valid, similarity_results, param_results, svd_results,
        sn_results) = raw.validate_sample_range(sasms, [[188, 206]], rg=rg,
        vcmw=vcmw, vpmw=vpmw)

    assert valid
    assert similarity_results['all_similar']
    assert similarity_results['low_q_similar']
    assert similarity_results['high_q_similar']
    assert svd_results['svals'] == 1
    assert param_results['param_valid']
    assert param_results['rg_valid']
    assert param_results['vcmw_valid']
    assert param_results['vpmw_valid']
    assert param_results['rg_pval'] == 0.9488461264555137
    assert param_results['vcmw_pval'] == 0.3438801731989136
    assert param_results['vpmw_pval'] == 0.6472068934597522
    assert sn_results['sn_valid']

def test_set_sampe_range(bsa_series):
    sub_profile = raw.set_sample_range(bsa_series, [[188, 206]])

    assert sub_profile.getI().sum() == 11758.431580249562

def test_find_baseline_range_integral(int_baseline_series):
    (start_found, end_found, start_range,
        end_range) = raw.find_baseline_range(int_baseline_series)

    assert start_found
    assert end_found
    assert start_range[0] == 42
    assert start_range[1] == 71
    assert end_range[0] == 318
    assert end_range[1] == 347

def test_find_baseline_range_integral_list(int_baseline_series):
    sasms = int_baseline_series.subtracted_sasm_list

    (start_found, end_found, start_range,
        end_range) = raw.find_baseline_range(sasms)

    assert start_found
    assert not end_found
    assert start_range[0] == 140
    assert start_range[1] == 169

def test_validate_baseline_range_integral_good(int_baseline_series):
    (valid, valid_results, similarity_results, svd_results, intI_results,
        other_results) = raw.validate_baseline_range(int_baseline_series,
        [42, 71], [318, 347])

    assert valid
    assert similarity_results[0]['all_similar']
    assert similarity_results[0]['low_q_similar']
    assert similarity_results[0]['high_q_similar']
    assert svd_results[0]['svals'] == 1
    assert intI_results[0]['intI_valid']
    assert intI_results[0]['smoothed_intI_valid']
    assert intI_results[0]['intI_pval'] == 0.2388039563971044
    assert intI_results[0]['smoothed_intI_pval'] == 0.10656462177179266
    assert similarity_results[1]['all_similar']
    assert similarity_results[1]['low_q_similar']
    assert similarity_results[1]['high_q_similar']
    assert svd_results[1]['svals'] == 1
    assert intI_results[1]['intI_valid']
    assert intI_results[1]['smoothed_intI_valid']
    assert intI_results[1]['intI_pval'] == 0.3572478396366079
    assert intI_results[1]['smoothed_intI_pval'] == 0.06588236359826605

def test_validate_baseline_range_integral_bad(int_baseline_series):
    (valid, valid_results, similarity_results, svd_results, intI_results,
        other_results) = raw.validate_baseline_range(int_baseline_series,
        [50, 80], [320, 350])

    assert not valid
    assert similarity_results[0]['all_similar']
    assert similarity_results[0]['low_q_similar']
    assert similarity_results[0]['high_q_similar']
    assert svd_results[0]['svals'] == 1
    assert intI_results[0]['intI_valid']
    assert intI_results[0]['smoothed_intI_valid']
    assert intI_results[0]['intI_pval'] == 0.07367410936498585
    assert intI_results[0]['smoothed_intI_pval'] == 0.017991315636281355
    assert similarity_results[1]['all_similar']
    assert similarity_results[1]['low_q_similar']
    assert similarity_results[1]['high_q_similar']
    assert svd_results[1]['svals'] == 1
    assert intI_results[1]['intI_valid']
    assert not intI_results[1]['smoothed_intI_valid']
    assert intI_results[1]['intI_pval'] == 0.26995117121922096
    assert intI_results[1]['smoothed_intI_pval'] == 0.006453749007721673

def test_validate_baseline_range_list(int_baseline_series):
    sasms = int_baseline_series.subtracted_sasm_list
    (valid, valid_results, similarity_results, svd_results, intI_results,
        other_results) = raw.validate_baseline_range(sasms, [42, 71],
        [318, 347])

    assert valid
    assert similarity_results[0]['all_similar']
    assert similarity_results[0]['low_q_similar']
    assert similarity_results[0]['high_q_similar']
    assert svd_results[0]['svals'] == 1
    assert intI_results[0]['intI_valid']
    assert intI_results[0]['smoothed_intI_valid']
    assert intI_results[0]['intI_pval'] == 0.2388039563971044
    assert intI_results[0]['smoothed_intI_pval'] == 0.10656462177179266
    assert similarity_results[1]['all_similar']
    assert similarity_results[1]['low_q_similar']
    assert similarity_results[1]['high_q_similar']
    assert svd_results[1]['svals'] == 1
    assert intI_results[1]['intI_valid']
    assert intI_results[1]['smoothed_intI_valid']
    assert intI_results[1]['intI_pval'] == 0.3572478396366079
    assert intI_results[1]['smoothed_intI_pval'] == 0.06588236359826605

# def test_validate_baseline_range_linear_good(int_baseline_series):
#     (valid, valid_results, similarity_results, svd_results, intI_results,
#         other_results) = raw.validate_baseline_range(int_baseline_series,
#         [42, 71], [318, 347], 'Linear')

#     assert valid
#     assert similarity_results[0]['all_similar']
#     assert similarity_results[0]['low_q_similar']
#     assert similarity_results[0]['high_q_similar']
#     assert svd_results[0]['svals'] == 1
#     assert intI_results[0]['intI_valid']
#     assert intI_results[0]['smoothed_intI_valid']
#     assert intI_results[0]['intI_pval'] == 0.2388039563971044
#     assert intI_results[0]['smoothed_intI_pval'] == 0.10656462177179266
#     assert similarity_results[1]['all_similar']
#     assert similarity_results[1]['low_q_similar']
#     assert similarity_results[1]['high_q_similar']
#     assert svd_results[1]['svals'] == 1
#     assert intI_results[1]['intI_valid']
#     assert intI_results[1]['smoothed_intI_valid']
#     assert intI_results[1]['intI_pval'] == 0.3572478396366079
#     assert intI_results[1]['smoothed_intI_pval'] == 0.06588236359826605

def test_validate_baseline_range_linear_bad(int_baseline_series):
    (valid, valid_results, similarity_results, svd_results, intI_results,
        other_results) = raw.validate_baseline_range(int_baseline_series,
        [0, 10], [390, 400], 'Linear')

    assert not valid
    assert not other_results[1]['fit_valid']

def test_set_baseline_correction_integral(clean_baseline_series):
    (bl_cor_profiles, rg, rger, i0, i0er, vcmw, vcmwer, vpmw, bl_corr,
        fit_results) = raw.set_baseline_correction(clean_baseline_series,
        [42, 71], [318, 347], 'Integral')

    assert np.allclose(rg[200], 27.753419465473335)
    assert np.allclose(rger[200], 0.12139692269361119)
    assert all(rg == clean_baseline_series.getRg()[0])
    assert np.allclose(clean_baseline_series.getIntI(int_type='baseline').sum(),
        0.1031091826570453)

def test_set_baseline_correction_linear(clean_baseline_series):
    (bl_cor_profiles, rg, rger, i0, i0er, vcmw, vcmwer, vpmw, bl_corr,
        fit_results) = raw.set_baseline_correction(clean_baseline_series,
        [0, 10], [390, 400], 'Linear')

    assert rg[200] == 27.709617891146536
    assert rger[200] == 0.12827521377190731
    assert all(rg == clean_baseline_series.getRg()[0])
    assert clean_baseline_series.getIntI(int_type='baseline').sum() == 0.10684702672323632
