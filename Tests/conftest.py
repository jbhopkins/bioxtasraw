import os
import copy

import pytest

raw_path = os.path.abspath(os.path.join('.', __file__, '..', '..'))
if raw_path not in os.sys.path:
    os.sys.path.append(raw_path)

import bioxtasraw.RAWAPI as raw

@pytest.fixture(scope="package")
def old_settings():
    settings = raw.load_settings(os.path.join('.', 'data', 'settings_old.cfg'))
    return settings

@pytest.fixture(scope="package")
def gi_sub_profile():
    profile = raw.load_profiles([os.path.join('.', 'data',
            'glucose_isomerase.dat')])[0]
    return profile

@pytest.fixture(scope="package")
def gi_sub_profile_dupe_data():
    profile = raw.load_profiles([os.path.join('.', 'data',
            'glucose_isomerase_dupe_data.dat')])[0]
    return profile

@pytest.fixture(scope="package")
def sans_profile():
    profile = raw.load_profiles([os.path.join('.', 'data',
            'sans_data.dat')])[0]
    return profile

@pytest.fixture(scope="package")
def gi_gnom_ift():
    ift = raw.load_ifts([os.path.join('.', 'data',
            'glucose_isomerase.out')])[0]
    return ift

@pytest.fixture(scope="package")
def gi_bift_ift():
    ift = raw.load_ifts([os.path.join('.', 'data',
            'glucose_isomerase.ift')])[0]
    return ift

@pytest.fixture(scope="package")
def gi_dift_ift():
    ift = raw.load_ifts([os.path.join('.', 'data',
            'glucose_isomerase_dift.ift')])[0]
    return ift

@pytest.fixture(scope="package")
def gi_pdb2sas_modelonly_ift():
    ift = raw.load_ifts([os.path.join('.', 'data',
            'gi_pdb2mrc_modelonly.ift')])[0]
    return ift

@pytest.fixture(scope="package")
def gi_pdb2sas_fit_ift():
    ift = raw.load_ifts([os.path.join('.', 'data',
            'gi_pdb2mrc_fit.ift')])[0]
    return ift

@pytest.fixture(scope="package")
def series_dats():
    series = raw.load_series([os.path.join('.', 'data',
            'series_new_dats.hdf5')])[0]
    return series

@pytest.fixture(scope="package")
def series_images():
    series = raw.load_series([os.path.join('.', 'data',
            'series_new_images.hdf5')])[0]
    return series

@pytest.fixture(scope="function")
def clean_gi_sub_profile(gi_sub_profile):
    return copy.deepcopy(gi_sub_profile)

@pytest.fixture(scope='package')
def bsa_series_profiles():
    filenames = [os.path.join('.', 'data', 'series_dats',
        'BSA_001_{:04d}.dat'.format(i)) for i in range(10)]

    profiles = raw.load_profiles(filenames)

    return profiles

@pytest.fixture(scope="package")
def temp_directory(tmp_path_factory):
    return tmp_path_factory.mktemp('raw')

@pytest.fixture(scope="package")
def bsa_series():
    series = raw.load_series([os.path.join('.', 'data',
            'BSA_001.hdf5')])[0]
    return series

@pytest.fixture(scope="package")
def series_sasbdb_keywords():
    series = raw.load_series([os.path.join('.', 'data',
            'series_with_sasbdb_keywords.hdf5')])[0]
    return series
