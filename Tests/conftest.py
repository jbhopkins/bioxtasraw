import os

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
def series_dats():
    series = raw.load_series([os.path.join('.', 'data',
            'series_new_dats.hdf5')])[0]
    return series

@pytest.fixture(scope="package")
def series_images():
    series = raw.load_series([os.path.join('.', 'data',
            'series_new_images.hdf5')])[0]
    return series
