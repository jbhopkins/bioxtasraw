import os

import pytest
import numpy as np

raw_path = os.path.abspath(os.path.join('.', __file__, '..', '..'))
if raw_path not in os.sys.path:
    os.sys.path.append(raw_path)

import bioxtasraw.RAWAPI as raw

@pytest.fixture(scope='package')
def bsa_series_profiles():
    filenames = [os.path.join('.', 'data', 'series_dats',
        'BSA_001_{:04d}.dat'.format(i)) for i in range(10)]

    profiles = raw.load_profiles(filenames)

    return profiles

def test_average(bsa_series_profiles):
    profiles = bsa_series_profiles

    avg_profile = raw.average(profiles)

    all_i = np.array([sasm.getI() for sasm in profiles])
    avg_i = np.mean(all_i, axis=0)
    all_err = np.array([sasm.getErr() for sasm in profiles])
    avg_err = np.sqrt(np.sum(np.power(all_err, 2),axis=0))/len(all_err)

    assert all(avg_profile.getQ() == profiles[0].getQ())
    assert all(avg_profile.getI() == avg_i)
    assert all(avg_profile.getErr() == avg_err)

@pytest.mark.new
def test_weighted_average(bsa_series_profiles):
    profiles = bsa_series_profiles

    avg_profile = raw.weighted_average(profiles)

    all_i = np.array([sasm.getI() for sasm in profiles])
    all_err = np.array([sasm.getErr() for sasm in profiles])
    all_err = 1/(np.square(all_err))
    avg_i = np.average(all_i, axis=0, weights = all_err)
    avg_err = np.sqrt(1/np.sum(all_err,0))

    assert all(avg_profile.getQ() == profiles[0].getQ())
    assert all(avg_profile.getI() == avg_i)
    assert all(avg_profile.getErr() == avg_err)
