import os

import pytest
import numpy as np

raw_path = os.path.abspath(os.path.join('.', __file__, '..', '..'))
if raw_path not in os.sys.path:
    os.sys.path.append(raw_path)

import bioxtasraw.RAWAPI as raw


@pytest.fixture(scope="package")
def temp_directory(tmp_path_factory):
    return tmp_path_factory.mktemp('raw')

@pytest.fixture()
def new_settings():
    settings = raw.load_settings(os.path.join('.', 'data', 'settings_new.cfg'))
    return settings

def test_api_save_settings(new_settings, temp_directory):
    raw.save_settings(new_settings, 'test_settings.cfg', temp_directory)

    with open(os.path.join(temp_directory, 'test_settings.cfg'), 'r') as f:
        test_settings = f.read()

    with open(os.path.join('.', 'data', 'settings_new.cfg'), 'r') as f:
        exp_settings = f.read()

    exclude_keys = ['ATSASDir']

    test_settings = test_settings.split('\n')
    for line in test_settings:
        for key in exclude_keys:
            if key in line:
                test_settings.remove(line)

    test_settings='\n'.join(test_settings)

    exp_settings = exp_settings.split('\n')
    for line in exp_settings:
        for key in exclude_keys:
            if key in line:
                exp_settings.remove(line)

    exp_settings='\n'.join(exp_settings)


    assert test_settings == exp_settings

def test_api_save_profile(gi_sub_profile, temp_directory):
    raw.save_profile(gi_sub_profile, 'test_profile.dat', temp_directory)

    with open(os.path.join(temp_directory, 'test_profile.dat'), 'r') as f:
        test_profile = f.read()

    with open(os.path.join('.', 'data', 'glucose_isomerase.dat'), 'r') as f:
        exp_profile = f.read()

    exclude_keys = ['filename']

    test_profile = test_profile.split('\n')
    for line in test_profile:
        for key in exclude_keys:
            if key in line:
                test_profile.remove(line)

    test_profile='\n'.join(test_profile)

    exp_profile = exp_profile.split('\n')
    for line in exp_profile:
        for key in exclude_keys:
            if key in line:
                exp_profile.remove(line)

    exp_profile='\n'.join(exp_profile)

    assert test_profile == exp_profile

def test_api_save_gnom_ift(gi_gnom_ift, temp_directory):
    raw.save_ift(gi_gnom_ift, 'test_gnom_ift.out', temp_directory)

    with open(os.path.join(temp_directory, 'test_gnom_ift.out'), 'r') as f:
        test_ift = f.read()

    with open(os.path.join('.', 'data', 'glucose_isomerase.out'), 'r') as f:
        exp_ift = f.read()

    assert test_ift == exp_ift

def test_api_save_bift_ift(gi_bift_ift, temp_directory):
    raw.save_ift(gi_bift_ift, 'test_bift_ift.ift', temp_directory)

    with open(os.path.join(temp_directory, 'test_bift_ift.ift'), 'r') as f:
        test_ift = f.read()

    with open(os.path.join('.', 'data', 'glucose_isomerase.ift'), 'r') as f:
        exp_ift = f.read()

    exclude_keys = ['filename']

    test_ift = test_ift.split('\n')
    for line in test_ift:
        for key in exclude_keys:
            if key in line:
                test_ift.remove(line)

    test_ift='\n'.join(test_ift)

    exp_ift = exp_ift.split('\n')
    for line in exp_ift:
        for key in exclude_keys:
            if key in line:
                exp_ift.remove(line)

    exp_ift='\n'.join(exp_ift)

    assert test_ift == exp_ift

def test_api_save_series_dats(series_dats, temp_directory):
    raw.save_series(series_dats, 'test_series_dats.hdf5', temp_directory)

    test_series = raw.load_series([os.path.join(temp_directory,
        'test_series_dats.hdf5')])[0]

    assert test_series._file_list == series_dats._file_list
    assert all(test_series.total_i == series_dats.total_i)
    assert test_series.window_size == series_dats.window_size
    assert test_series.buffer_range == series_dats.buffer_range
    assert test_series.buffer_range == series_dats.buffer_range
    assert test_series.sample_range == series_dats.sample_range
    assert test_series.sample_range == series_dats.sample_range
    assert test_series.baseline_start_range == series_dats.baseline_start_range
    assert test_series.baseline_end_range == series_dats.baseline_end_range
    assert all(test_series.rg_list == series_dats.rg_list)
    assert all(test_series.rger_list == series_dats.rger_list)
    assert all(test_series.i0_list == series_dats.i0_list)
    assert all(test_series.i0er_list == series_dats.i0er_list)
    assert all(test_series.vpmw_list == series_dats.vpmw_list)
    assert all(test_series.vcmw_list == series_dats.vcmw_list)
    assert all(test_series.vcmwer_list == series_dats.vcmwer_list)

    assert test_series.series_type == series_dats.series_type
    assert test_series._scale_factor == series_dats._scale_factor
    assert test_series._offset_value == series_dats._offset_value
    assert test_series._frame_scale_factor == series_dats._frame_scale_factor
    assert test_series.mol_type == series_dats.mol_type
    assert test_series.mol_density == series_dats.mol_density
    assert test_series.already_subtracted == series_dats.already_subtracted
    assert len(test_series.subtracted_sasm_list) == len(series_dats.subtracted_sasm_list)
    assert len(test_series.use_subtracted_sasm) == len(series_dats.use_subtracted_sasm)
    assert all(test_series.total_i_sub == series_dats.total_i_sub)
    assert test_series.baseline_type == series_dats.baseline_type
    assert len(test_series.baseline_subtracted_sasm_list) == len(series_dats.baseline_subtracted_sasm_list)
    assert len(test_series.use_baseline_subtracted_sasm) == len(series_dats.use_baseline_subtracted_sasm)
    assert all(test_series.total_i_bcsub == series_dats.total_i_bcsub)

def test_api_save_series_images(series_images, temp_directory):
    raw.save_series(series_images, 'test_series_images.hdf5', temp_directory)

    test_series = raw.load_series([os.path.join(temp_directory,
        'test_series_images.hdf5')])[0]

    assert test_series._file_list == series_images._file_list
    assert all(test_series.total_i == series_images.total_i)
    assert test_series.window_size == series_images.window_size
    assert test_series.buffer_range == series_images.buffer_range
    assert test_series.buffer_range == series_images.buffer_range
    assert test_series.sample_range == series_images.sample_range
    assert test_series.sample_range == series_images.sample_range
    assert test_series.baseline_start_range == series_images.baseline_start_range
    assert test_series.baseline_end_range == series_images.baseline_end_range
    assert all(test_series.rg_list == series_images.rg_list)
    assert all(test_series.rger_list == series_images.rger_list)
    assert all(test_series.i0_list == series_images.i0_list)
    assert all(test_series.i0er_list == series_images.i0er_list)
    assert all(test_series.vpmw_list == series_images.vpmw_list)
    assert all(test_series.vcmw_list == series_images.vcmw_list)
    assert all(test_series.vcmwer_list == series_images.vcmwer_list)

    assert test_series.series_type == series_images.series_type
    assert test_series._scale_factor == series_images._scale_factor
    assert test_series._offset_value == series_images._offset_value
    assert test_series._frame_scale_factor == series_images._frame_scale_factor
    assert test_series.mol_type == series_images.mol_type
    assert test_series.mol_density == series_images.mol_density
    assert test_series.already_subtracted == series_images.already_subtracted
    assert len(test_series.subtracted_sasm_list) == len(series_images.subtracted_sasm_list)
    assert len(test_series.use_subtracted_sasm) == len(series_images.use_subtracted_sasm)
    assert all(test_series.total_i_sub == series_images.total_i_sub)
    assert test_series.baseline_type == series_images.baseline_type
    assert len(test_series.baseline_subtracted_sasm_list) == len(series_images.baseline_subtracted_sasm_list)
    assert len(test_series.use_baseline_subtracted_sasm) == len(series_images.use_baseline_subtracted_sasm)
    assert all(test_series.total_i_bcsub == series_images.total_i_bcsub)
