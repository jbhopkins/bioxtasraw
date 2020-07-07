import os
import copy

import pytest
import numpy as np
import scipy.interpolate as interp

raw_path = os.path.abspath(os.path.join('.', __file__, '..', '..'))
if raw_path not in os.sys.path:
    os.sys.path.append(raw_path)

import bioxtasraw.RAWAPI as raw


@pytest.fixture(scope='package')
def lys_saxs():
    filenames = [os.path.join('.', 'data', 'lys_saxs.dat')]

    profiles = raw.load_profiles(filenames)

    return profiles[0]

@pytest.fixture(scope='package')
def lys_waxs():
    filenames = [os.path.join('.', 'data', 'lys_saxs.dat')]

    profiles = raw.load_profiles(filenames)

    return profiles[0]


@pytest.fixture(scope='package', params=[-1, 0, 1.1, 2, 5, 10, 100, 1000, 10000])
def rebin_factor(request):
    return request.param

@pytest.fixture(scope='package', params=[-1, 0, 1, 1.1, 2, 5, 10, 100, 1000, 10000])
def npts(request):
    return request.param

@pytest.fixture(scope='package', params=[-1, 0, 1, 1.1, 2])
def scale_factor(request):
    return request.param

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

def test_subtract(bsa_series_profiles):
    profiles = bsa_series_profiles

    bkg_profile = profiles.pop(0)

    sub_profiles = raw.subtract(profiles, bkg_profile)

    test_sub_i = [sasm.getI() - bkg_profile.getI() for sasm in profiles]
    test_sub_err = [np.sqrt(sasm.getErr()**2+bkg_profile.getErr()**2) for sasm in profiles]

    for j, sasm in enumerate(sub_profiles):
        assert all(sasm.getQ() == profiles[j].getQ())
        assert all(sasm.getI() == test_sub_i[j])
        assert all(sasm.getErr() == test_sub_err[j])

def test_linear_rebin_factor(gi_sub_profile, rebin_factor):
    rebinned = raw.rebin([gi_sub_profile], rebin_factor=rebin_factor)[0]

    rebin_factor = int(rebin_factor)

    if rebin_factor < 1:
        rebin_factor = 1

    intensity = gi_sub_profile.getI()
    q = gi_sub_profile.getQ()
    err = gi_sub_profile.getErr()

    no_of_bins = int(np.floor(len(intensity) / rebin_factor))

    if no_of_bins < 1:
        no_of_bins = 1

    new_i = np.zeros(no_of_bins)
    new_q = np.zeros(no_of_bins)
    new_err = np.zeros(no_of_bins)

    for eachbin in range(0, no_of_bins):
        first_idx = eachbin * rebin_factor
        last_idx = (eachbin * rebin_factor) + rebin_factor

        new_i[eachbin] = np.sum(intensity[first_idx:last_idx]) / rebin_factor
        new_q[eachbin] = np.sum(q[first_idx:last_idx]) / rebin_factor
        new_err[eachbin] = np.sqrt(np.sum(np.power(err[first_idx:last_idx],2))) / np.sqrt(rebin_factor)

    assert all(rebinned.getQ() == new_q)
    assert all(rebinned.getI() == new_i)
    assert all(rebinned.getErr() == new_err)

def test_linear_rebin_npts(gi_sub_profile, npts):
    rebinned = raw.rebin([gi_sub_profile], npts=npts)[0]

    if npts >= 1:
        rebin_factor = int(np.floor(len(gi_sub_profile.getQ())/float(npts)))
    else:
        rebin_factor = 1

    rebin_factor = int(rebin_factor)

    if rebin_factor < 1:
        rebin_factor = 1

    intensity = gi_sub_profile.getI()
    q = gi_sub_profile.getQ()
    err = gi_sub_profile.getErr()
    err_sqr = err**2
    err_norm = np.sqrt(rebin_factor)

    no_of_bins = int(np.floor(len(intensity) / rebin_factor))

    new_i = np.zeros(no_of_bins)
    new_q = np.zeros(no_of_bins)
    new_err = np.zeros(no_of_bins)

    for eachbin in range(0, no_of_bins):
        first_idx = eachbin * rebin_factor
        last_idx = (eachbin * rebin_factor) + rebin_factor

        new_i[eachbin] = np.sum(intensity[first_idx:last_idx]) / rebin_factor
        new_q[eachbin] = np.sum(q[first_idx:last_idx]) / rebin_factor
        new_err[eachbin] = np.sqrt(np.sum(err_sqr[first_idx:last_idx])) / err_norm

    assert all(rebinned.getQ() == new_q)
    assert all(rebinned.getI() == new_i)
    assert all(rebinned.getErr() == new_err)

def test_log_rebin_factor(gi_sub_profile, rebin_factor):
    rebinned = raw.rebin([gi_sub_profile], rebin_factor=rebin_factor,
        log_rebin=True)[0]

    if rebin_factor == 0:
        rebin_factor = 1

    no_points = int(np.floor(len(gi_sub_profile.getQ())/rebin_factor))

    q = gi_sub_profile.getQ()
    i = gi_sub_profile.getI()
    err = gi_sub_profile.getErr()
    err_sqr = err**2

    total_pts = len(q)

    if no_points <=1:
        no_points = total_pts

    if no_points >= total_pts:
        binned_q = q
        binned_i = i
        binned_err = err
        bins = np.empty_like(q)

    else:
        bins_calc = False
        min_pt = 1

        while not bins_calc:
            bins = np.geomspace(min_pt, total_pts, no_points+1-min_pt)

            pos_min_diff = np.argwhere(np.ediff1d(bins)>1)[0][0]

            if pos_min_diff == 0:
                bins_calc = True

            else:
                pos_min_diff = pos_min_diff + 1
                min_pt = int(np.floor(bins[pos_min_diff]))

        bins = bins.astype(int)
        bins[0] = min_pt

        log_bins = np.concatenate((np.arange(min_pt, dtype=int), bins))

        binned_q = np.empty(log_bins.shape[0]-1)
        binned_i = np.empty(log_bins.shape[0]-1)
        binned_err = np.empty(log_bins.shape[0]-1)

        for j in range(log_bins.shape[0]-1):
            start_idx = log_bins[j]
            end_idx = log_bins[j+1]

            binned_q[j] = np.mean(q[start_idx:end_idx])
            binned_i[j] = np.mean(i[start_idx:end_idx])
            binned_err[j] = np.sqrt(np.sum(err_sqr[start_idx:end_idx])/(end_idx-start_idx))

    assert all(rebinned.getQ() == binned_q)
    assert all(rebinned.getI() == binned_i)
    assert all(rebinned.getErr() == binned_err)

def test_log_rebin_npts(gi_sub_profile, npts):
    rebinned = raw.rebin([gi_sub_profile], npts=npts, log_rebin=True)[0]

    no_points = npts

    no_points = int(no_points)

    q = gi_sub_profile.getQ()
    i = gi_sub_profile.getI()
    err = gi_sub_profile.getErr()
    err_sqr = err**2

    total_pts = len(q)

    if no_points <=1:
        no_points = total_pts

    if no_points >= total_pts:
        binned_q = q
        binned_i = i
        binned_err = err
        bins = np.empty_like(q)

    else:
        bins_calc = False
        min_pt = 1

        while not bins_calc:
            bins = np.geomspace(min_pt, total_pts, no_points+1-min_pt)

            pos_min_diff = np.argwhere(np.ediff1d(bins)>1)[0][0]

            if pos_min_diff == 0:
                bins_calc = True

            else:
                pos_min_diff = pos_min_diff + 1
                min_pt = int(np.floor(bins[pos_min_diff]))

        bins = bins.astype(int)
        bins[0] = min_pt

        log_bins = np.concatenate((np.arange(min_pt, dtype=int), bins))

        binned_q = np.empty(log_bins.shape[0]-1)
        binned_i = np.empty(log_bins.shape[0]-1)
        binned_err = np.empty(log_bins.shape[0]-1)

        for j in range(log_bins.shape[0]-1):
            start_idx = log_bins[j]
            end_idx = log_bins[j+1]

            binned_q[j] = np.mean(q[start_idx:end_idx])
            binned_i[j] = np.mean(i[start_idx:end_idx])
            binned_err[j] = np.sqrt(np.sum(err_sqr[start_idx:end_idx])/(end_idx-start_idx))

    assert all(rebinned.getQ() == binned_q)
    assert all(rebinned.getI() == binned_i)
    assert all(rebinned.getErr() == binned_err)

def test_interpolate(gi_sub_profile):
    rebinned = raw.rebin([gi_sub_profile])[0]

    interp_profile = raw.interpolate([gi_sub_profile], rebinned)[0]

    #find overlapping s2 points
    min_q1, max_q1 = rebinned.getQrange()
    min_q2, max_q2 = gi_sub_profile.getQrange()

    lowest_q1, highest_q1 = rebinned.q[rebinned.getQrange()[0]], rebinned.q[rebinned.getQrange()[1]-1]

    overlapping_q2_top = gi_sub_profile.q[min_q2:max_q2][np.where( (gi_sub_profile.q[min_q2:max_q2] <= highest_q1))]
    overlapping_q2 = overlapping_q2_top[np.where(overlapping_q2_top >= lowest_q1)]

    if overlapping_q2[0] != gi_sub_profile.q[0]:
        idx = np.where(gi_sub_profile.q == overlapping_q2[0])
        overlapping_q2 = np.insert(overlapping_q2, 0, gi_sub_profile.q[idx[0]-1])

    if overlapping_q2[-1] != gi_sub_profile.q[-1]:
        idx = np.where(gi_sub_profile.q == overlapping_q2[-1])
        overlapping_q2 = np.append(overlapping_q2, gi_sub_profile.q[idx[0]+1])

    overlapping_q1_top = rebinned.q[min_q1:max_q1][np.where( (rebinned.q[min_q1:max_q1] <= overlapping_q2[-1]))]
    overlapping_q1 = overlapping_q1_top[np.where(overlapping_q1_top >= overlapping_q2[0])]

    q2_indexs = []
    q1_indexs = []
    for each in overlapping_q2:
        idx, = np.where(gi_sub_profile.q == each)
        q2_indexs.append(idx[0])

    for each in overlapping_q1:
        idx, = np.where(rebinned.q == each)
        q1_indexs.append(idx[0])

    #interpolate find the I's that fits the q vector of rebinned:
    f = interp.interp1d(gi_sub_profile.q[q2_indexs], gi_sub_profile.i[q2_indexs])
    f_err = interp.interp1d(gi_sub_profile.q[q2_indexs], gi_sub_profile.err[q2_indexs])

    intp_i = f(rebinned.q[q1_indexs])
    intp_q = rebinned.q[q1_indexs].copy()
    intp_err = f_err(rebinned.q[q1_indexs])

    assert all(interp_profile.getQ() == intp_q)
    assert all(interp_profile.getI() == intp_i)
    assert all(interp_profile.getErr() == intp_err)

def test_merge(lys_saxs, lys_waxs):
    merged_profile = raw.merge([lys_saxs, lys_waxs])

    #find overlapping s2 points
    highest_q = lys_saxs.q[lys_saxs.getQrange()[1]-1]
    qmin, qmax = lys_waxs.getQrange()
    overlapping_q2 = lys_waxs.q[qmin:qmax][np.where(lys_waxs.q[qmin:qmax] <= highest_q)]

    #find overlapping s1 points
    lowest_s2_q = lys_waxs.q[lys_waxs.getQrange()[0]]
    qmin, qmax = lys_saxs.getQrange()
    overlapping_q1 = lys_saxs.q[qmin:qmax][np.where(lys_saxs.q[qmin:qmax] >= lowest_s2_q)]

    tmp_s2i = lys_waxs.i.copy()
    tmp_s2q = lys_waxs.q.copy()
    tmp_s2err = lys_waxs.err.copy()

    if len(overlapping_q1) == 1 and len(overlapping_q2) == 1: #One point overlap
        q1idx = lys_saxs.getQrange()[1]
        q2idx = lys_waxs.getQrange()[0]

        avg_i = (lys_saxs.i[q1idx] + lys_waxs.i[q2idx])/2.0

        tmp_s2i[q2idx] = avg_i

        minq, maxq = lys_saxs.getQrange()
        q1_indexs = [maxq-1, minq]

    elif len(overlapping_q1) == 0 and len(overlapping_q2) == 0: #No overlap
        minq, maxq = lys_saxs.getQrange()
        q1_indexs = [maxq, minq]

    else:   #More than 1 point overlap

        added_index = False
        if overlapping_q2[0] < overlapping_q1[0]:
            #add the point before overlapping_q1[0] to overlapping_q1
            idx, = np.where(lys_saxs.q == overlapping_q1[0])
            overlapping_q1 = np.insert(overlapping_q1, 0, lys_saxs.q[idx-1][0])
            added_index = True

        #get indexes for overlapping_q2 and q1
        q2_indexs = []
        q1_indexs = []

        for each in overlapping_q2:
            idx, = np.where(lys_waxs.q == each)
            q2_indexs.append(idx[0])

        for each in overlapping_q1:
            idx, = np.where(lys_saxs.q == each)
            q1_indexs.append(idx[0])

        #interpolate overlapping s2 onto s1
        f = interp.interp1d(lys_saxs.q[q1_indexs], lys_saxs.i[q1_indexs])
        intp_I = f(lys_waxs.q[q2_indexs])
        averaged_I = (intp_I + lys_waxs.i[q2_indexs])/2.0

        if added_index:
            q1_indexs = np.delete(q1_indexs, 0)

        tmp_s2i[q2_indexs] = averaged_I


    #Merge the two parts
    #cut away the overlapping part on s1 and append s2 to it
    qmin, qmax = lys_saxs.getQrange()
    newi = lys_saxs.i[qmin:q1_indexs[0]]
    newq = lys_saxs.q[qmin:q1_indexs[0]]
    newerr = lys_saxs.err[qmin:q1_indexs[0]]

    qmin, qmax = lys_waxs.getQrange()
    newi = np.append(newi, tmp_s2i[qmin:qmax])
    newq = np.append(newq, tmp_s2q[qmin:qmax])
    newerr = np.append(newerr, tmp_s2err[qmin:qmax])

    assert all(merged_profile.getQ() == newq)
    assert all(merged_profile.getI() == newi)
    assert all(merged_profile.getErr() == newerr)

def test_superimpose(bsa_series_profiles):
    input_profiles = [copy.deepcopy(profile) for profile in bsa_series_profiles]
    ref_profile = input_profiles[0]

    sup_profiles = raw.superimpose(input_profiles, ref_profile)

    q_star = ref_profile.q
    i_star = ref_profile.i
    # err_star = ref_profile.err

    q_star_qrange_min, q_star_qrange_max = ref_profile.getQrange()

    q_star = q_star[q_star_qrange_min:q_star_qrange_max]
    i_star = i_star[q_star_qrange_min:q_star_qrange_max]

    choice = 'Scale'

    for each_sasm in input_profiles:

        each_q = each_sasm.getRawQ()
        each_i = each_sasm.getRawI()

        each_q_qrange_min, each_q_qrange_max = each_sasm.getQrange()

        # resample standard curve on the data q vector
        min_q_each = each_q[each_q_qrange_min]
        max_q_each = each_q[each_q_qrange_max-1]

        min_q_idx = np.where(q_star >= min_q_each)[0][0]
        max_q_idx = np.where(q_star <= max_q_each)[0][-1]

        if np.all(q_star[min_q_idx:max_q_idx+1] != each_q[each_q_qrange_min:each_q_qrange_max]):
            I_resamp = np.interp(q_star[min_q_idx:max_q_idx+1],
                                 each_q[each_q_qrange_min:each_q_qrange_max],
                                 each_i[each_q_qrange_min:each_q_qrange_max])
        else:
            I_resamp = each_i[each_q_qrange_min:each_q_qrange_max]

        if not np.all(I_resamp ==i_star):
            if choice == 'Scale and Offset':
                A = np.column_stack([I_resamp, np.ones_like(I_resamp)])
                scale, offset = np.linalg.lstsq(A, i_star[min_q_idx:max_q_idx+1])[0]
            elif choice == 'Scale':
                A = np.column_stack([I_resamp, np.zeros_like(I_resamp)])
                scale, offset= np.linalg.lstsq(A, i_star[min_q_idx:max_q_idx+1])[0]
                offset = 0
            elif choice == 'Offset':
                A = np.column_stack([np.zeros_like(I_resamp), np.ones_like(I_resamp)])
                scale, offset= np.linalg.lstsq(A, i_star[min_q_idx:max_q_idx+1]-I_resamp)[0]
                scale = 1

            each_sasm.scale(scale)
            each_sasm.offset(offset)


    assert sup_profiles[0].getScale() == 1

    for j in range(len(sup_profiles)):
        assert all(sup_profiles[j].getQ() == input_profiles[j].getQ())
        assert all(sup_profiles[j].getI() == input_profiles[j].getI())
        assert all(sup_profiles[j].getErr() == input_profiles[j].getErr())

def test_scale_profile(gi_sub_profile, scale_factor):
    test_profile = copy.deepcopy(gi_sub_profile)

    i = copy.deepcopy(test_profile.getI())
    err = copy.deepcopy(test_profile.getErr())

    test_profile.scale(scale_factor)

    assert all(test_profile.getI() == i*abs(scale_factor))
    assert all(test_profile.getErr() == err*abs(scale_factor))

def test_offest_profile(gi_sub_profile, scale_factor):
    test_profile = copy.deepcopy(gi_sub_profile)

    i = copy.deepcopy(test_profile.getI())
    err = copy.deepcopy(test_profile.getErr())

    test_profile.offset(scale_factor)

    assert all(test_profile.getI() == i + scale_factor)
    assert all(test_profile.getErr() == err)

def test_scaleq_profile(gi_sub_profile, scale_factor):
    test_profile = copy.deepcopy(gi_sub_profile)

    q = copy.deepcopy(test_profile.getQ())

    test_profile.scaleQ(scale_factor)

    assert all(test_profile.getQ() == q*scale_factor)
