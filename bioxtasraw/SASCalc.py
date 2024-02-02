"""
Created on December 12, 2015

@author: Jesse B. Hopkins

#******************************************************************************
# This file is part of RAW.
#
#    RAW is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    RAW is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with RAW.  If not, see <http://www.gnu.org/licenses/>.
#
#******************************************************************************

The purpose of this module is to contain functions for calculating
values from SAXS profiles. These are intended to be automated
functions, including calculation of rg and molecular weight.

It also contains functions for calling outside packages for use in RAW, like DAMMIF.
"""
from __future__ import absolute_import, division, print_function, unicode_literals
from builtins import object, range, map, zip
from io import open

try:
    import queue
except Exception:
    import Queue as queue

import os
import time
import subprocess
import threading
import platform
import re
import math
import traceback
import copy
import tempfile

import numpy as np
from scipy import integrate as integrate
import scipy.interpolate
import scipy.signal
import scipy.stats as stats
from scipy.constants import Avogadro
from numba import jit

raw_path = os.path.abspath(os.path.join('.', __file__, '..', '..'))
if raw_path not in os.sys.path:
    os.sys.path.append(raw_path)

import bioxtasraw.SASFileIO as SASFileIO
import bioxtasraw.SASExceptions as SASExceptions
import bioxtasraw.RAWSettings as RAWSettings
import bioxtasraw.SASProc as SASProc
import bioxtasraw.SASM as SASM
import bioxtasraw.REGALS as REGALS
import bioxtasraw.SECM as SECM
import bioxtasraw.SASUtils as SASUtils


#Define the rg fit function
@jit(nopython=True, cache=True, parallel=False)
def linear_func(x, a, b):
    return a+b*x

@jit(nopython=True, cache=True, parallel=False)
def weighted_lin_reg(x, y, err):
    err_idx = err == 0

    if not np.all(err_idx) :
        if np.any(err_idx):
            err[err_idx] = np.mean(err[np.nonzero(err_idx)])
    else:
        err[err_idx] = 1.

    weights = 1./(err)**2.

    w_sum = weights.sum()
    wy_sum = (weights*y).sum()
    wx_sum = (weights*x).sum()
    wxsq_sum = (weights*x**2.).sum()
    wxy_sum = (weights*x*y).sum()

    delta = weights.sum()*wxsq_sum-(wx_sum)**2.

    if delta != 0:
        a = (wxsq_sum*wy_sum - wx_sum*wxy_sum)/delta
        b = (w_sum*wxy_sum - wx_sum*wy_sum)/delta

        cov_a = wxsq_sum/delta
        cov_b = w_sum/delta
    else:
        a = -1
        b = -1
        cov_a = -1
        cov_b = -1

    return a, b, cov_a, cov_b

@jit(nopython=True, cache=True, parallel=False)
def lin_reg(x, y):
    x_sum = x.sum()
    xsq_sum = (x**2).sum()
    y_sum = y.sum()
    xy_sum = (x*y).sum()
    n = len(x)

    delta = n*xsq_sum - x_sum**2.

    if delta !=0:
        a = (xsq_sum*y_sum - x_sum*xy_sum)/delta
        b = (n*xy_sum-x_sum*y_sum)/delta

        cov_y = (1./(n-2.))*((y-a-b*x)**2.).sum()
        cov_a = cov_y*(xsq_sum/delta)
        cov_b = cov_y*(n/delta)
    else:
        a = -1
        b = -1
        cov_a = -1
        cov_b = -1

    return a, b, cov_a, cov_b

@jit(nopython=True, cache=True, parallel=False)
def calcRg(q, i, err, transform=True, error_weight=True):
    if transform:
        #Start out by transforming as usual.
        x = np.square(q)
        y = np.log(i)
        yerr = np.absolute(err/i) #I know it looks odd, but it's correct for a natural log
        x = x[np.where(np.isfinite(y))]
        yerr = yerr[np.where(np.isfinite(y))]
        y = y[np.where(np.isfinite(y))]
    else:
        x = q
        y = i
        yerr = err

    if error_weight:
        if np.any(yerr == 0):
            error_weight = False

    if error_weight:
        a, b, cov_a, cov_b = weighted_lin_reg(x, y, yerr)
    else:
        a, b, cov_a, cov_b = lin_reg(x, y)

    if b < 0:
        RG=np.sqrt(-3.*b)
        I0=np.exp(a)

        #error in rg and i0 is calculated by noting that q(x)+/-Dq has Dq=abs(dq/dx)Dx, where q(x) is your function you're using
        #on the quantity x+/-Dx, with Dq and Dx as the uncertainties and dq/dx the derviative of q with respect to x.
        RGer=np.absolute(0.5*(np.sqrt(-3./b)))*np.sqrt(np.absolute(cov_b))
        I0er=I0*np.sqrt(np.absolute(cov_a))

    else:
        RG = -1
        I0 = -1
        RGer = -1
        I0er = -1

    return RG, I0, RGer, I0er, a, b

def estimate_guinier_error(q, i, err, transform=True, error_weight=True):
    if transform:
        #Start out by transforming as usual.
        x = np.square(q)
        y = np.log(i)
        yerr = np.absolute(err/i) #I know it looks odd, but it's correct for a natural log
    else:
        x = q
        y = i
        yerr = err

    win_size = len(x)

    if win_size < 10:
        est_rg_err = None
        est_i0_err = None
    else:
        var = win_size//10
        if var > 12:
            step = int(np.ceil(var/12.))
        else:
            step = 1
        rg_list = []
        i0_list = []

        for li in range(0, var+1, step):
            for ri in range(0,var+1, step):
                if ri == 0:
                    Rg, I0, Rger, I0er, a, b = calcRg(x[li:], y[li:], yerr[li:],
                        transform=transform, error_weight=error_weight)
                else:
                    Rg, I0, Rger, I0er, a, b = calcRg(x[li:-ri], y[li:-ri],
                        yerr[li:-ri], transform=transform,
                        error_weight=error_weight)

                rg_list.append(Rg)
                i0_list.append(I0)

        est_rg_err = np.array(rg_list).std()
        est_i0_err = np.array(i0_list).std()

    return est_rg_err, est_i0_err

def calcRefMW(i0, conc, ref_i0, ref_conc, ref_mw):
    if ref_mw > 0 and ref_i0 > 0 and ref_conc > 0 and conc > 0 and i0 > 0:
            mw = (i0 * (ref_mw/(ref_i0/ref_conc))) / conc
    else:
        mw = -1

    return mw

def vpA(q_max):
    A = -2.114*10**6*q_max**4 + 2.920*10**6*q_max**3 - 1.472*10**6*q_max**2+3.349*10**5*q_max - 3.577*10**4
    return A

def vpB(q_max):
    B = 12.09*q_max**3 - 9.39*q_max**2 + 3.03*q_max+0.29
    return B

def calcVqmax(q, i, rg, i0, choice='8/Rg', qmax=None, unit=''):
    vpqmax = None

    if unit == '1/nm':
        temp_q = q/10
        temp_rg = rg*10

        if qmax is not None:
            temp_qmax = qmax/10
        else:
            temp_qmax = qmax

    else:
        temp_q = q
        temp_rg = rg
        temp_qmax = qmax

    if choice == 'Default':
        if temp_rg != 0:
            vpqmax = 8./temp_rg

            if vpqmax > 0.5 or vpqmax < 0.1:
                iratio = np.abs(np.log10(i0/i) - 2.25)
                idx = np.argmin(iratio)

                vpqmax = temp_q[idx]

            if vpqmax > 0.5:
                vpqmax = 0.5
            elif vpqmax < 0.1:
                vpqmax = 0.1

    elif choice == '8/Rg':
        if temp_rg != 0:
            vpqmax = 8./temp_rg

            if vpqmax > 0.5:
                vpqmax = 0.5
            elif vpqmax < 0.1:
                vpqmax = 0.1

    elif choice == 'log(I0/I(q))':

        if i0 != 0:

            iratio = np.abs(np.log10(i0/i) - 2.25)
            idx = np.argmin(iratio)

            vpqmax = temp_q[idx]

            if vpqmax > 0.5:
                vpqmax = 0.5
            elif vpqmax < 0.1:
                vpqmax = 0.1

    elif choice == 'Manual':
        vpqmax = temp_qmax

    if vpqmax is None:
        vpqmax = min(temp_q[-1], 0.5)

    else:
        if vpqmax > q[-1]:
            vpqmax = q[-1]
        elif vpqmax < q[0]:
            vpqmax = q[0]
        else:
            idx = np.argmin(np.abs(temp_q-vpqmax))
            vpqmax = temp_q[idx]

            if choice != 'Manual':
                if vpqmax < 0.1:
                    vpqmax = temp_q[idx+1]
                elif vpqmax > 0.5:
                    vpqmax = temp_q[idx-1]

    if unit == '1/nm':
        vpqmax *= 10

    return vpqmax


def calcVpMW(q, i, err, rg, i0, rg_qmin, vp_density, qmax, unit=''):
    #These functions are used to correct the porod volume for the length of the q vector
    if unit == '1/nm':
        temp_q = q/10
        temp_rg = rg*10
        temp_qmax = qmax/10

    else:
        temp_q = q
        temp_rg = rg
        temp_qmax = qmax

    if temp_qmax not in temp_q:
        idx = np.argmin(np.abs(temp_q-temp_qmax))
    else:
        idx = np.argwhere(temp_q == temp_qmax)[0][0]

    temp_q = temp_q[:idx+1]
    i = i[:idx+1]
    err = err[:idx+1]

    if temp_q[-1] <= 0.5 and temp_q[-1] >= 0.1:
        A = vpA(temp_q[-1])
        B = vpB(temp_q[-1])
    else:
        A = 0
        B = 1

    if i0 > 0:
        #Calculate the Porod Volume
        pVolume = porodVolume(temp_q, i, err, temp_rg, i0, interp = True, rg_qmin=rg_qmin)

        if pVolume == -1:
            mw = -1
            pv_cor = -1

        else:
            #Correct for the length of the q vector
            pv_cor=(A+B*pVolume)

            mw = pv_cor*vp_density

    else:
        mw = -1
        pVolume = -1
        pv_cor = -1

    return mw, pVolume, pv_cor

def calcAbsMW(i0, conc, rho_Mprot, rho_solv, nu_bar, r0):
    d_rho = (rho_Mprot-(rho_solv*nu_bar))*r0
    mw = (Avogadro*i0/conc)/np.square(d_rho)
    return mw

def volumeOfCorrelation(q, i, i0):
    """Calculates the volume of correlation as the ratio of i0 to $\int q*I dq$
    """
    tot=integrate.trapz(q*i,q)
    vc=i0/tot
    return vc

def porodInvariant(q, i,start=0,stop=-1):
    return integrate.trapz(i[start:stop]*np.square(q[start:stop]),q[start:stop])

def porodVolume(q, i, err, rg, i0, start = 0, stop = -1, interp = True, rg_qmin=0):

    if interp and q[0] != 0:
        def f(x):
            return i0*np.exp((-1./3.)*np.square(rg)*np.square(x))

        if rg_qmin>0:

            findClosest = lambda a,l:min(l,key=lambda x:abs(x-a))
            closest_qmin = findClosest(rg_qmin, q)

            idx_min = np.where(q == closest_qmin)[0][0]

            q = q[idx_min:]
            i = i[idx_min:]
            err = err[idx_min:]

        if len(q) != 1:

            q_interp = np.arange(0,q[0],q[1]-q[0])
            i_interp = f(q_interp)
            err_interp = np.sqrt(i_interp)

            q = np.concatenate((q_interp, q))
            i = np.concatenate((i_interp, i))
            err = np.concatenate((err_interp, err))

    if len(q) != 1:
        pInvar = porodInvariant(q, i, start, stop)

        pVolume = 2*np.pi**2*i0/pInvar

    else:
        pVolume = -1

    return pVolume

def autoRg(sasm, single_fit=False, error_weight=True):
    #This function automatically calculates the radius of gyration and scattering intensity at zero angle
    #from a given scattering profile. It roughly follows the method used by the autorg function in the atsas package

    q = sasm.getQ()
    i = sasm.getI()
    err = sasm.getErr()

    qmin = 0

    try:
        rg, rger, i0, i0er, idx_min, idx_max = autoRg_inner(q, i, err, qmin,
            single_fit, error_weight, min_window=10, min_qrg=1.0, max_qrg=1.35,
            quality_thresh=0.6, data_range_scale=0, corr_coefht=2.,
            win_length_weight=1.0)
    except Exception: #Catches unexpected numba errors, I hope
        traceback.print_exc()
        rg = -1
        rger = -1
        i0 = -1
        i0er = -1
        idx_min = -1
        idx_max = -1

    if rg == -1:
        #If we don't find a fit, relax the criteria
        try:
            rg, rger, i0, i0er, idx_min, idx_max = autoRg_inner(q, i, err, qmin,
                single_fit, error_weight, min_window=5, min_qrg=1.0, max_qrg=1.35,
                quality_thresh=0.5, data_range_scale=0, corr_coefht=2.,
                win_length_weight=1.0)
        except Exception: #Catches unexpected numba errors, I hope
            traceback.print_exc()
            rg = -1
            rger = -1
            i0 = -1
            i0er = -1
            idx_min = -1
            idx_max = -1

    if rg == -1:
        #If we don't find a fit, relax the criteria
        try:
            rg, rger, i0, i0er, idx_min, idx_max = autoRg_inner(q, i, err, qmin,
                single_fit, error_weight, min_window=10, min_qrg=1.0, max_qrg=1.35,
                quality_thresh=0.6, data_range_scale=100, corr_coefht=2.,
                win_length_weight=1.0)
        except Exception: #Catches unexpected numba errors, I hope
            traceback.print_exc()
            rg = -1
            rger = -1
            i0 = -1
            i0er = -1
            idx_min = -1
            idx_max = -1

    if rg == -1:
        #If we don't find a fit, relax the criteria
        try:
            rg, rger, i0, i0er, idx_min, idx_max = autoRg_inner(q, i, err, qmin,
                single_fit, error_weight, min_window=10, min_qrg=1.2, max_qrg=1.5,
                quality_thresh=0.3, data_range_scale=100, corr_coefht=2.,
                win_length_weight=1.0)
        except Exception: #Catches unexpected numba errors, I hope
            traceback.print_exc()
            rg = -1
            rger = -1
            i0 = -1
            i0er = -1
            idx_min = -1
            idx_max = -1

    if rg == -1:
        #If we don't find a fit, relax the criteria
        try:
            rg, rger, i0, i0er, idx_min, idx_max = autoRg_inner(q, i, err, qmin,
                single_fit, error_weight, min_window=5, min_qrg=1.2, max_qrg=1.5,
                quality_thresh=0.3, data_range_scale=100, corr_coefht=2.,
                win_length_weight=1.0)
        except Exception: #Catches unexpected numba errors, I hope
            traceback.print_exc()
            rg = -1
            rger = -1
            i0 = -1
            i0er = -1
            idx_min = -1
            idx_max = -1

    return rg, rger, i0, i0er, idx_min, idx_max

@jit(nopython=True, cache=True, parallel=False)
def autoRg_inner(q, i, err, qmin, single_fit, error_weight, min_window=10,
    min_qrg=1.0, max_qrg=1.35, quality_thresh=0.6, data_range_scale=0,
    corr_coefht=2., win_length_weight=1.0):
    #Pick the start of the RG fitting range. Note that in autorg, this is done
    #by looking for strong deviations at low q from aggregation or structure factor
    #or instrumental scattering, and ignoring those. This function isn't that advanced
    #so we start at 0.

    # Note, in order to speed this up using numba, I had to do some unpythonic things
    # with declaring lists ahead of time, and making sure lists didn't have multiple
    # object types in them. It makes the code a bit more messy than the original
    # version, but numba provides a significant speedup.

    # Have to pick the right Starting range to avoid various weirdnesses in the data
    data_start = (i>0).argmax()

    if len(i) > 20:
        while i[data_start] < np.mean(i[-1*int(len(i)/20):]) and data_start<len(i):
            data_start = (i[data_start+1:]>0).argmax() + data_start+1

        while i[data_start] > np.mean(i[data_start:data_start+20])*10:
            data_start = (i[data_start+1:]>0).argmax()+data_start+1

    # Turns out to be pretty important to pick a good initial q range for the search
    # This is just kind of determined by what looks reasonable
    if data_range_scale == 0:
        total_int_range = np.abs(np.mean(i[data_start:data_start+20])/np.mean(i[-20:]))
        if total_int_range < 20:
            data_range_scale = 2.5

        elif total_int_range < 100:
            data_range_scale = 5

        elif total_int_range < 1000:
            data_range_scale = 10

        else:
            data_range_scale = 100

    #Following the atsas package, the end point of our search space is the q value
    #where the intensity has droped by an order of magnitude from the initial value.
    data_end = np.abs(i[i>0]-i[data_start]/data_range_scale).argmin()

    i_val = i[i>0][data_end]
    data_end = np.argwhere(i==i_val)[0][0]


    #This makes sure we're not getting some weird fluke at the end of the scattering profile.
    if data_end > len(i)/2.:
        found = False
        if len(i) > data_start+20 and data_start+20<len(i)/2.:
            idx = data_start+20
        else:
            idx = data_start
        while not found:
            idx = idx +1
            if i[idx]<i[data_start]/data_range_scale:
                found = True
            elif idx == len(q) -1:
                found = True
        data_end = idx

    #Start out by transforming as usual.
    qs = np.square(q)
    il = np.log(i)
    iler = np.absolute(err/i)

    #Pick a minimum fitting window size. 10 is consistent with atsas autorg.
    min_window = min_window

    max_window = data_end-data_start

    if max_window<min_window:
        max_window = min_window

    #It is very time consuming to search every possible window size and every possible starting point.
    #Here we define a subset to search.
    tot_points = max_window
    window_step = min(tot_points//10, 20)
    data_step = tot_points//50

    if window_step == 0:
        window_step =1
    if data_step ==0:
        data_step =1

    window_list = [0 for k in range(int(math.ceil((max_window-min_window)/float(window_step)))+1)]

    for k in range(int(math.ceil((max_window-min_window)/float(window_step)))):
        window_list[k] = min_window+k*window_step

    window_list[-1] = max_window

    num_fits = 0

    for w in window_list:
        num_fits = num_fits + int(math.ceil((data_end-w-data_start)/float(data_step)))

    if num_fits < 0:
        num_fits = 1

    start_list = [0 for k in range(num_fits)]
    w_list = [0 for k in range(num_fits)]
    q_start_list = [0. for k in range(num_fits)]
    q_end_list = [0. for k in range(num_fits)]
    rg_list = [0. for k in range(num_fits)]
    rger_list = [0. for k in range(num_fits)]
    i0_list = [0. for k in range(num_fits)]
    i0er_list = [0. for k in range(num_fits)]
    qrg_start_list = [0. for k in range(num_fits)]
    qrg_end_list = [0. for k in range(num_fits)]
    rsqr_list = [0. for k in range(num_fits)]
    chi_sqr_list = [0. for k in range(num_fits)]
    reduced_chi_sqr_list = [0. for k in range(num_fits)]
    corr_coef_list = [0. for k in range(num_fits)]

    success = np.zeros(num_fits)

    current_fit = 0
    #This function takes every window size in the window list, stepts it through the data range, and
    #fits it to get the RG and I0. If basic conditions are met, qmin*RG<1 and qmax*RG<1.35, and RG>0.1,
    #We keep the fit.
    for w in window_list:
        for start in range(data_start,data_end-w, data_step):
            x = qs[start:start+w]
            y = il[start:start+w]
            yerr = iler[start:start+w]

            #Remove NaN and Inf values:
            x = x[np.where(np.isfinite(y))]
            yerr = yerr[np.where(np.isfinite(y))]
            y = y[np.where(np.isfinite(y))]


            RG, I0, RGer, I0er, a, b = calcRg(x, y, yerr, transform=False, error_weight=error_weight)

            if RG>0.1 and q[start]*RG<min_qrg and q[start+w-1]*RG<max_qrg and RGer/RG <= 1:
                residual = il[start:start+w]-linear_func(qs[start:start+w], a, b)

                r_sqr = 1 - np.square(residual).sum()/np.square(il[start:start+w]-il[start:start+w].mean()).sum()

                if r_sqr > .15:
                    chi_sqr = np.square((residual)/iler[start:start+w]).sum()

                    #All of my reduced chi_squared values are too small, so I suspect something isn't right with that.
                    #Values less than one tend to indicate either a wrong degree of freedom, or a serious overestimate
                    #of the error bars for the system.
                    dof = w - 2.
                    reduced_chi_sqr = chi_sqr/dof

                    #Ideally this would be a pvalue, but I'd have to invest in a lot of intrastructure to actually calculate that in a jitted function
                    corr_coef = 1- spearmanr(residual, qs[start:start+w])

                    start_list[current_fit] = start
                    w_list[current_fit] = w
                    q_start_list[current_fit] = q[start]
                    q_end_list[current_fit] = q[start+w-1]
                    rg_list[current_fit] = RG
                    rger_list[current_fit] = RGer
                    i0_list[current_fit] = I0
                    i0er_list[current_fit] = I0er
                    qrg_start_list[current_fit] = q[start]*RG
                    qrg_end_list[current_fit] = q[start+w-1]*RG
                    rsqr_list[current_fit] = r_sqr
                    chi_sqr_list[current_fit] = chi_sqr
                    reduced_chi_sqr_list[current_fit] = reduced_chi_sqr
                    corr_coef_list[current_fit] = corr_coef

                    success[current_fit] = 1

            current_fit = current_fit + 1

    if np.sum(success) > 0:

        fit_array = np.array([[start_list[k], w_list[k], q_start_list[k],
            q_end_list[k], rg_list[k], rger_list[k], i0_list[k], i0er_list[k],
            qrg_start_list[k], qrg_end_list[k], rsqr_list[k], chi_sqr_list[k],
            reduced_chi_sqr_list[k], corr_coef_list[k]] for k in range(num_fits) if success[k]==1])

        #Now we evaluate the quality of the fits based both on fitting data and on other criteria.

        # Choice of weights is pretty arbitrary, but has been tested against
        # all the data in the SASBDB (as of 11/2020)
        qmaxrg_weight = 1
        qminrg_weight = 1
        rg_frac_err_weight = 1
        i0_frac_err_weight = 1
        r_sqr_weight = 4
        reduced_chi_sqr_weight = 0
        window_size_weight = win_length_weight
        corr_coef_weight = corr_coefht

        weights = np.array([qmaxrg_weight, qminrg_weight, rg_frac_err_weight,
            i0_frac_err_weight, r_sqr_weight, reduced_chi_sqr_weight,
            window_size_weight, corr_coef_weight])

        quality = np.zeros(len(fit_array))

        max_window_real = float(max(w_list))


        #This iterates through all the fits, and calculates a score. The score is out of 1, 1 being the best, 0 being the worst.
        indices =list(range(len(fit_array)))
        for a in indices:
            k=int(a) #This is stupid and should not be necessary. Numba bug?

            #Scores all should be 1 based. Reduced chi_square score is not, hence it not being weighted.
            qmaxrg_score = 1-abs((fit_array[k,9]-1.3)/1.3)
            qminrg_score = 1-fit_array[k,8]
            rg_frac_err_score = 1-fit_array[k,5]/fit_array[k,4]
            i0_frac_err_score = 1 - fit_array[k,7]/fit_array[k,6]
            r_sqr_score = fit_array[k,10]
            reduced_chi_sqr_score = 1/fit_array[k,12] #Not right
            window_size_score = fit_array[k,1]/max_window_real
            corr_coef_score = fit_array[k,13]

            scores = np.array([qmaxrg_score, qminrg_score, rg_frac_err_score,
                i0_frac_err_score, r_sqr_score, reduced_chi_sqr_score,
                window_size_score, corr_coef_score])

            total_score = (weights*scores).sum()/weights.sum()

            quality[k] = total_score

            # all_scores[k] = scores

        #I have picked an aribtrary threshold here. Not sure if 0.6 is a good quality cutoff or not.
        if quality.max() > quality_thresh:
            if not single_fit:
                idx = quality.argmax()
                rger = fit_array[:,5][quality>quality[idx]-.1].std()
                i0er = fit_array[:,7][quality>quality[idx]-.1].std()
                idx_min = int(fit_array[idx,0])
                idx_max = int(fit_array[idx,0]+fit_array[idx,1]-1)
            else:
                idx = quality.argmax()
                idx_min = int(fit_array[idx,0])
                idx_max = int(fit_array[idx,0]+fit_array[idx,1]-1)


            # Now refine the range a bit
            max_quality = quality.max()
            qual = max_quality

            idx_max_ref = idx_max

            if max_qrg == 1.35:
                max_qrg_ref = 1.3
            else:
                max_qrg_ref = max_qrg

            if q[idx_max]*RG<1.0:
                quality_scale = 0.9
                r_thresh = 0.1
            else:
                quality_scale = 0.97
                r_thresh = 0.15

            # Refine upper end of range
            while qual > quality_scale*max_quality and idx_max_ref < len(q):

                idx_max_ref = idx_max_ref +1
                x = qs[idx_min:idx_max_ref+1]
                y = il[idx_min:idx_max_ref+1]
                yerr = iler[idx_min:idx_max_ref+1]

                #Remove NaN and Inf values:
                x = x[np.where(np.isfinite(y))]
                yerr = yerr[np.where(np.isfinite(y))]
                y = y[np.where(np.isfinite(y))]


                RG, I0, RGer, I0er, a, b = calcRg(x, y, yerr, transform=False,
                    error_weight=error_weight)

                if RG>0.1 and q[idx_min]*RG<min_qrg and q[idx_max_ref]*RG<max_qrg_ref and RGer/RG <= 1:
                    residual = il[idx_min:idx_max_ref+1]- linear_func(qs[idx_min:idx_max_ref+1], a, b)

                    r_sqr = (1 - np.square(residual).sum()/np.square(il[idx_min:idx_max_ref+1]-il[idx_min:idx_max_ref+1].mean()).sum())

                    if r_sqr > r_thresh:
                        chi_sqr = np.square(residual/iler[idx_min:idx_max_ref+1]).sum()

                        #All of my reduced chi_squared values are too small, so I suspect something isn't right with that.
                        #Values less than one tend to indicate either a wrong degree of freedom, or a serious overestimate
                        #of the error bars for the system.
                        dof = w - 2.
                        reduced_chi_sqr = chi_sqr/dof

                        corr_coef = 1- spearmanr(residual, qs[idx_min:idx_max_ref+1])

                        qmaxrg_score = 1-abs((q[idx_max_ref]*RG-1.3)/1.3)
                        qminrg_score = 1-q[idx_min]*RG
                        rg_frac_err_score = 1-RGer/RG
                        i0_frac_err_score = 1 - I0er/I0
                        r_sqr_score = r_sqr
                        reduced_chi_sqr_score = 1/reduced_chi_sqr #Not right
                        window_size_score = fit_array[k,1]/max_window_real
                        corr_coef_score = corr_coef

                        scores = np.array([qmaxrg_score, qminrg_score,
                            rg_frac_err_score, i0_frac_err_score, r_sqr_score,
                            reduced_chi_sqr_score, window_size_score,
                            corr_coef_score])


                        qual = (weights*scores).sum()/weights.sum()

                        if q[idx_max]*RG<1.0:
                            quality_scale = 0.9
                            r_thresh = 0.1
                        else:
                            quality_scale = 0.97
                            r_thresh = 0.15

                    else:
                        qual = -1

                else:
                    qual = -1

                max_quality = max(max_quality, qual)

            idx_max = idx_max_ref -1

            # Refine lower end of range
            idx_min_ref = idx_min
            qual = max_quality

            while qual > 0.97*max_quality and idx_min_ref > 0:

                idx_min_ref = idx_min_ref -1
                x = qs[idx_min_ref:idx_max+1]
                y = il[idx_min_ref:idx_max+1]
                yerr = iler[idx_min_ref:idx_max+1]

                #Remove NaN and Inf values:
                x = x[np.where(np.isfinite(y))]
                yerr = yerr[np.where(np.isfinite(y))]
                y = y[np.where(np.isfinite(y))]


                RG, I0, RGer, I0er, a, b = calcRg(x, y, yerr, transform=False,
                    error_weight=error_weight)

                if RG>0.1 and q[idx_min_ref]*RG<min_qrg and q[idx_max]*RG<max_qrg_ref and RGer/RG <= 1:

                    residual = il[idx_min_ref:idx_max+1]- linear_func(qs[idx_min_ref:idx_max+1], a, b)

                    r_sqr = (1 - np.square(residual).sum()/np.square(il[idx_min_ref:idx_max+1]-il[idx_min_ref:idx_max+1].mean()).sum())

                    if r_sqr > .15:
                        chi_sqr = (np.square((residual)/iler[idx_min_ref:idx_max+1]).sum())

                        #All of my reduced chi_squared values are too small, so I suspect something isn't right with that.
                        #Values less than one tend to indicate either a wrong degree of freedom, or a serious overestimate
                        #of the error bars for the system.
                        dof = w - 2.
                        reduced_chi_sqr = chi_sqr/dof

                        corr_coef = 1- spearmanr(residual, qs[idx_min_ref:idx_max+1])

                        qmaxrg_score = 1-abs((q[idx_max]*RG-1.3)/1.3)
                        qminrg_score = 1-q[idx_min_ref]*RG
                        rg_frac_err_score = 1-RGer/RG
                        i0_frac_err_score = 1 - I0er/I0
                        r_sqr_score = r_sqr
                        reduced_chi_sqr_score = 1/reduced_chi_sqr #Not right
                        window_size_score = fit_array[k,1]/max_window_real
                        corr_coef_score = corr_coef

                        scores = np.array([qmaxrg_score, qminrg_score,
                            rg_frac_err_score, i0_frac_err_score, r_sqr_score,
                            reduced_chi_sqr_score, window_size_score,
                            corr_coef_score])

                        qual = (weights*scores).sum()/weights.sum()
                    else:
                        qual = -1

                else:
                    qual = -1

                max_quality = max(max_quality, qual)

            if idx_min_ref == 0 and qual != -1:
                idx_min = idx_min_ref
            else:
                idx_min = idx_min_ref +1

            # Recalculate Guinier values with the new min and max idx
            x = qs[idx_min:idx_max+1]
            y = il[idx_min:idx_max+1]
            yerr = iler[idx_min:idx_max+1]

            #Remove NaN and Inf values:
            x = x[np.where(np.isfinite(y))]
            yerr = yerr[np.where(np.isfinite(y))]
            y = y[np.where(np.isfinite(y))]

            rg, i0, Rger, I0er, a, b = calcRg(x, y, yerr, transform=False,
                error_weight=error_weight)

            if single_fit:
                rger = Rger
                i0er = I0er

        else:
            rg = -1
            rger = -1
            i0 = -1
            i0er = -1
            idx_min = -1
            idx_max = -1

    else:
        rg = -1
        rger = -1
        i0 = -1
        i0er = -1
        idx_min = -1
        idx_max = -1

    idx_min = idx_min + qmin
    idx_max = idx_max + qmin

    #returns Rg, Rg error, I0, I0 error, the index of the first q point of the fit and the index of the last q point of the fit
    return rg, rger, i0, i0er, idx_min, idx_max

@jit(nopython=True, cache=True)
def rankdata(array):
    temp = array.argsort()
    ranks = np.empty_like(temp)
    ranks[temp] = np.arange(len(array))

    return ranks

@jit(nopython=True, cache=True)
def spearmanr(array1, array2):
    rank1 = rankdata(array1)
    rank2 = rankdata(array2)

    n = rank1.size

    dsq = (rank1-rank2)**2

    rho = 1. - (6*dsq.sum())/(n*(n**2-1))

    # t = rho*np.sqrt((n-2)/(1-rho**2)) #Calcuates t value for student t test

    return rho


def calcVcMW(sasm, temp_rg, i0, temp_qmax, a_prot, b_prot, a_rna, b_rna,
    protein=True, interp=True, unit=''):
    #using the rambo tainer 2013 method for molecular mass.

    temp_q = sasm.getQ()
    i = sasm.getI()
    err = sasm.getErr()

    if unit == '1/nm':
        q = temp_q/10
        rg = temp_rg*10
        qmax = temp_qmax/10
    else:
        q = temp_q
        rg = temp_rg
        qmax = temp_qmax

    if qmax not in q:
        idx = np.argmin(np.abs(q-qmax))
        qmax = q[idx]
    else:
        idx = np.argwhere(q == qmax)[0][0]

    q = q[:idx+1]
    i = i[:idx+1]
    err = err[:idx+1]

    analysis = sasm.getParameter('analysis')

    if interp and q[0] != 0:
        def f(x):
            return i0*np.exp((-1./3.)*np.square(rg)*np.square(x))

        if 'guinier' in analysis:
            guinier_analysis = analysis['guinier']
            qmin = float(guinier_analysis['qStart'])

            findClosest = lambda a,l:min(l,key=lambda x:abs(x-a))
            closest_qmin = findClosest(qmin, q)

            idx_min = np.where(q == closest_qmin)[0][0]

            q = q[idx_min:]
            i = i[idx_min:]
            err = err[idx_min:]

        q_interp = np.arange(0,q[0],q[1]-q[0])
        i_interp = f(q_interp)
        err_interp = np.sqrt(i_interp)

        q = np.concatenate((q_interp, q))
        i = np.concatenate((i_interp, i))
        err = np.concatenate((err_interp, err))

    vc = volumeOfCorrelation(q, i, i0)

    #We then take a ratio of the square of vc to rg
    qr=np.square(vc)/rg

    #The molecular weight is then determined in a power law relationship. Note, the 1000 puts it in kDa

    if protein:
        A = a_prot
        B = b_prot
        #For proteins:
        # mw=qr/0.1231/1000
    else:
        A = a_rna
        B = b_rna
        #For RNA
        # mw = np.power(qr/0.00934, 0.808)/1000

    mw = (qr/B)**A/1000.

    return mw, np.sqrt(np.absolute(mw)), vc, qr


def getATSASVersion(atsasDir):
    #Checks if we have gnom4 or gnom5
    opsys = platform.system()

    if opsys == 'Windows':
        dammifDir = os.path.join(atsasDir, 'dammif.exe')
    else:
        dammifDir = os.path.join(atsasDir, 'dammif')

    if os.path.exists(dammifDir):
        my_env = setATSASEnv(atsasDir)

        process=subprocess.Popen('"%s" -v' %(dammifDir), stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, shell=True, env=my_env) #gnom4 doesn't do a proper -v!!! So use something else
        output, error = process.communicate()

        if not isinstance(output, str):
            output = str(output, encoding='UTF-8')

        if not isinstance(error, str):
            error = str(error, encoding='UTF-8')

        output = output.strip()
        error = error.strip()

        dammif_re = 'ATSAS\s*\d+[.]\d+[.]\d*'
        version_match = re.search(dammif_re, output)
        version = version_match.group().split()[-1]

    return version

def setATSASEnv(atsasDir):
    my_env = os.environ.copy()
    my_env["PATH"] = my_env["PATH"] + '{}{}'.format(os.pathsep, atsasDir) #Not ideal, what if there's another ATSAS path?
    my_env["ATSAS"] = os.path.split(atsasDir.rstrip(os.sep))[0] #Can only have one thing in ATSAS env variable!

    return my_env

def runGnom(fname, save_ift, dmax, args, path, atsasDir, outname=None,
    new_gnom=False):
    #This function runs GNOM from the atsas package. It can do so without writing a GNOM cfg file.
    #It takes as input the filename to run GNOM on, the output name from the GNOM file, the dmax to evaluate
    #at, and a dictionary of arguments, which can be used to set the optional GNOM arguments.
    #Using the GNOM cfg file is significantly faster than catching the interactive input and pass arguments there.

    #Solution for non-blocking reads adapted from stack overflow
    #http://stackoverflow.com/questions/375427/non-blocking-read-on-a-subprocess-pipe-in-python
    def enqueue_output(out, queue):
        line = 'test'
        line2=''
        while line != '':
            line = out.read(1)

            if not isinstance(line, str):
                line = str(line, encoding='UTF-8')

            line2+=line
            if line == ':':
                queue.put_nowait([line2])
                line2=''

        out.close()

    if new_gnom:
        cfg = False
    else:
        cfg = True

    if args['first'] is not None:
        args['first'] += 1
    if args['last'] is not None:
        args['last'] += 1

    if new_gnom:
        #Check whether everything can be set at the command line:
        fresh_settings = RAWSettings.RawGuiSettings().getAllParams()

        key_ref = {
                    'gnomForceRminZero' : 'rmin_zero',
                    'gnomForceRmaxZero' : 'rmax_zero',
                    'gnomNPoints'       : 'npts',
                    'gnomInitialAlpha'  : 'alpha',
                    'gnomSystem'        : 'system',
                    'gnomRadius56'      : 'radius56',
                    'gnomRmin'          : 'rmin',
                    }

        cmd_line_keys = {'rmin_zero', 'rmax_zero', 'system', 'rmin',
            'radiu56', 'npts', 'alpha'}

        changed = []

        for key in fresh_settings:
            if key in key_ref:
                if fresh_settings[key][0] != args[key_ref[key]]:
                    changed.append((key_ref[key]))

        if set(changed) <= cmd_line_keys:
            use_cmd_line = True
        else:
            use_cmd_line = False

    opsys = platform.system()
    if opsys == 'Windows':
        gnomDir = os.path.join(atsasDir, 'gnom.exe')
        shell=False
    else:
        gnomDir = os.path.join(atsasDir, 'gnom')
        shell=True

    if os.path.exists(gnomDir):

        my_env = setATSASEnv(atsasDir)

        if cfg:
            writeGnomCFG(fname, outname, dmax, args)

            proc = subprocess.Popen('"%s"' %(gnomDir), shell=shell,
                stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, cwd=path, env=my_env)
            proc.communicate('\r\n')

        else:
            if os.path.isfile(os.path.join(path, 'gnom.cfg')):
                os.remove(os.path.join(path, 'gnom.cfg'))

            if new_gnom and use_cmd_line:
                cmd = ('"%s" --rmax=%s' %(gnomDir, str(dmax)))

                if args['first'] is not None:
                    cmd = cmd + (' --first=%s' %(str(args['first'])))

                if args['last'] is not None:
                    cmd = cmd + (' --last=%s' %(str(args['last'])))

                if save_ift and outname is not None:
                    cmd = cmd + ' --output="{}"'.format(outname)

                if args['npts'] > 0:
                    cmd = cmd + ' --nr=%s'%(str(args['npts']))

                if 'system' in changed:
                    cmd = cmd+' --system=%s' %(str(args['system']))

                if 'rmin' in changed:
                    cmd = cmd+' --rmin=%s' %(str(args['rmin']))

                if 'radius56' in changed:
                    cmd = cmd + ' --rad56=%s' %(str(args['radius56']))

                if 'rmin_zero' in changed:
                    cmd = cmd + ' --force-zero-rmin=%s' %(args['rmin_zero'])

                if 'rmax_zero' in changed:
                    cmd = cmd + ' --force-zero-rmax=%s' %(args['rmax_zero'])

                if 'alpha' in changed:
                    cmd = cmd + ' --alpha=%s' %(str(args['alpha']))

                cmd = cmd + ' "%s"' %(fname)

                process=subprocess.Popen(cmd, stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE, shell=shell, cwd=path, env=my_env)

                output, error = process.communicate()

                if not isinstance(output, str):
                    output = str(output, encoding='UTF-8')

                if not isinstance(error, str):
                    error = str(error, encoding='UTF-8')

                output = output.strip()
                error = error.strip()

                if error != '':
                    raise SASExceptions.GNOMError(('GNOM failed to run with the '
                        'following error:\n{}'.format(error)))
            else:

                save_ift = True

                gnom_q = queue.Queue()

                proc = subprocess.Popen('"%s"' %(gnomDir), shell=shell,
                    stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT, cwd=path, universal_newlines=True,
                    bufsize=1, env=my_env)
                gnom_t = threading.Thread(target=enqueue_output, args=(proc.stdout, gnom_q))
                gnom_t.daemon = True
                gnom_t.start()

                previous_line = ''
                previous_line2 = ''

                while proc.poll() is None:
                    data = None
                    try:
                        data = gnom_q.get_nowait()
                        data = data[0]
                        gnom_q.task_done()
                    except queue.Empty:
                        pass

                    if data is not None:
                        current_line = data

                        if data.find('[ postscr     ] :') > -1:
                            proc.stdin.write('\r\n') #Printer type, default is postscr

                        elif data.find('Input data') > -1:
                            proc.stdin.write('%s\r\n' %(fname)) #Input data, first file. No default.

                        elif data.find('Output file') > -1 and data.find('. :') > -1:
                            proc.stdin.write('%s\r\n' %(outname)) #Output file, default is gnom.out

                        elif data.find('No of start points to skip') > -1:
                            if 's_skip' in args and args['s_skip'] != '':
                                proc.stdin.write('%s\r\n' %(args['s_skip']))
                            else:
                                proc.stdin.write('\r\n') #Number of start points to skip, default is 0

                        elif data.find('Input data, second file') > -1:
                            proc.stdin.write('\r\n') #Input data, second file, default is none

                        elif data.find('No of end points to omit') > -1:
                            if 'e_skip' in args and args['e_skip'] != '':
                                proc.stdin.write('%s\r\n' %(args['e_skip']))
                            else:
                                proc.stdin.write('\r\n') #Number of end poitns to omit, default is 0

                        elif data.find('Default input errors level') > -1:
                            proc.stdin.write('\r\n') #Default input errors level, default 0.0

                        elif data.find('Angular scale') > -1:
                            if 'angular' in args and args['angular'] != '':
                                proc.stdin.write('%s\r\n' %(args['angular']))
                            else:
                                proc.stdin.write('\r\n') #Angular scale, default 1

                        elif data.find('Plot input data') > -1:
                            proc.stdin.write('n\r\n') #Plot input data, default yes

                        elif data.find('File containing expert parameters') > -1:
                            if 'expert' in args and args['expert'] != '':
                                proc.stdin.write('%s\r\n' %(args['expert']))
                            else:
                                proc.stdin.write('\r\n') #File containing expert parameters, default none

                        elif data.find('Kernel already calculated') > -1:
                            proc.stdin.write('\r\n') #Kernel already calculated, default no

                        elif data.find('Type of system') > -1 or data.find('arbitrary monodisperse)') > -1:
                            if 'system' in args and args['system'] != '':
                                proc.stdin.write('%s\r\n' %(args['system']))
                            else:
                                proc.stdin.write('\r\n') #Type of system, default 0 (P(r) function)

                        elif (data.find('Zero condition at r=rmin') > -1 and data.find('[') > -1) or (previous_line.find('Zero condition at r=rmin') > -1 and previous_line.find('(') > -1):
                            if 'rmin_zero' in args and args['rmin_zero'] != '':
                                proc.stdin.write('%s\r\n' %(args['rmin_zero']))
                            else:
                                proc.stdin.write('\r\n') #Zero condition at r=rmin, default is yes

                        elif (data.find('Zero condition at r=rmax') > -1 and data.find('[') > -1) or (previous_line.find('Zero condition at r=rmax') > -1 and previous_line.find('(') > -1):
                            if 'rmax_zero' in args and args['rmax_zero'] != '':
                                proc.stdin.write('%s\r\n' %(args['rmax_zero']))
                            else:
                                proc.stdin.write('\r\n') #Zero condition at r=rmax, default is yes

                        elif data.find('Rmax for evaluating p(r)') > -1 or data.find('Maximum particle diameter') > -1 or data.find('Maximum characteristic size') > -1 or data.find('Maximum particle thickness') > -1 or data.find('Maximum diameter of particle') > -1 or data.find('Maximum height of cylinder') > -1 or data.find('Maximum outer shell radius') > -1:
                            proc.stdin.write('%s\r\n' %(str(dmax))) #Rmax for evaluating p(r), no default (DMAX!)

                        elif (data.find('Number of points in real space') > -1 and data.find('[') > -1) or previous_line.find('Number of points in real space?') > -1:
                            if 'npts' in args and args['npts'] != -1:
                                proc.stdin.write('%s\r\n' %(str(args['npts'])))
                            else:
                                proc.stdin.write('\r\n') #Number of points in real space, default is 171

                        elif data.find('Kernel-storage file name') > -1:
                            proc.stdin.write('\r\n') #Kernal-storage file name, default is kern.bin

                        elif (data.find('Experimental setup') > -1 and data.find('[') > -1) or data.find('point collimation)') > -1:
                            if 'gnomExp' in args:
                                proc.stdin.write('%s\r\n' %(str(args['gnomExp'])))
                            else:
                                proc.stdin.write('\r\n') #Experimental setup, default is 0 (no smearing)

                        elif data.find('Initial ALPHA') > -1 or previous_line.find('Initial alpha') > -1:
                            if 'alpha' in args and args['alpha'] != 0.0:
                                proc.stdin.write('%s\r\n' %(str(args['alpha'])))
                            else:
                                proc.stdin.write('\r\n') #Initial ALPHA, default is 0.0

                        elif data.find('Plot alpha distribution') > -1:
                            proc.stdin.write('n\r\n') #Plot alpha distribution, default is yes

                        elif data.find('Plot results') > -1:
                            proc.stdin.write('n\r\n') #Plot results, default is no

                        elif data.find('Your choice') > -1:
                            proc.stdin.write('\r\n') #Choice when selecting one of the following options, CR for EXIT

                        elif data.find('Evaluate errors') > -1:
                            proc.stdin.write('\r\n') #Evaluate errors, default yes

                        elif data.find('Plot p(r) with errors') > -1:
                            proc.stdin.write('n\r\n') #Plot p(r) with errors, default yes

                        elif data.find('Next data set') > -1:
                            proc.stdin.write('\r\n') #Next data set, default no

                        elif data.find('Rmin for evaluating p(r)') > -1 or data.find('Minimum characteristic size') > -1 or previous_line.find('Minimum height of cylinder') > -1 or previous_line.find('Minimum outer shell radius') > -1:
                            if 'rmin' in args and args['rmin'] != -1 and args['rmin'] >= 0:
                                proc.stdin.write('%s\r\n' %(str(args['rmin']))) #Rmin, required for some job types
                            else:
                                proc.stdin.write('\r\n' %(str(args['rmin']))) #Default is 0

                        elif data.find('Form factor file for JOB=2') > -1 or data.find('Form Factor file') > -1:
                            proc.stdin.write('%s\r\n' %(str(args['form'])))

                        elif data.find('Cylinder radius') > -1 or data.find('Relative shell thickness') > -1:
                            if 'radius56' in args and args['radius56'] != -1:
                                proc.stdin.write('%s\r\n') %(str(args['radius56'])) #Cylinder radius / relative thickness
                            else:
                                proc.stdin.write('\r\n') #Default is 0

                        elif data.find('FWHM for the first run') > 1:
                            #Need something here
                            if 'fwhm' in args and args['fwhm'] != -1:
                                proc.stdin.write('%s\r\n') %(str(args['fwhm'])) #Beam FWHM
                            else:
                                proc.stdin.write('\r\n') #Default is 0

                        elif data.find('Slit-height parameter AH') > -1 or previous_line.find('Slit height parameter A') > -1:
                            if 'ah' in args and args['ah'] != -1:
                                proc.stdin.write('%s\r\n') %(str(args['ah'])) #Beam height in the detector plane
                            else:
                                proc.stdin.write('\r\n') #Default is 0

                        elif data.find('Slit-height parameter LH') > -1 or previous_line.find('Slit height parameter L') > -1:
                            if 'lh' in args and args['lh'] != -1:
                                proc.stdin.write('%s\r\n') %(str(args['lh'])) #Half the height  difference between top and bottom edge of beam in detector plane
                            else:
                                proc.stdin.write('\r\n') #Default is 0

                        elif data.find('parameter AW') > -1 or previous_line.find('Slit width parameter A') > -1:
                            if 'aw' in args and args['aw'] != -1:
                                proc.stdin.write('%s\r\n') %(str(args['aw'])) #Projection of beam width in detectgor plane
                            else:
                                proc.stdin.write('\r\n') #Default is 0

                        elif data.find('parameter LW') > -1 or previous_line.find('Slit width parameter L') > -1:
                            if 'lw' in args and args['lw'] != -1:
                                proc.stdin.write('%s\r\n') %(str(args['lw'])) #Half of the width difference bewteen top and bottom edge of beam projection in detector plane
                            else:
                                proc.stdin.write('\r\n') #Default is 0

                        elif data.find('Beam profile file') > -1:
                            if 'spot' in args and args['spot'] != -1:
                                proc.stdin.write('%s\r\n') %(str(args['spot'])) #Beam profile file
                            else:
                                proc.stdin.write('\r\n') #Default is none, doesn't use a profile

                        #Prompts from GNOM5
                        elif previous_line.find('(e) expert') > -1:
                            proc.stdin.write('e\r\n') #Default is user, good for now. Looks like setting weights is now done in expert mode rather than with a file, so eventually incorporate that.

                        elif previous_line.find('First point to use') > -1:
                            if 'first' in args and args['first'] != '':
                                proc.stdin.write('%i\r\n' %(int(args['first'])))
                            else:
                                proc.stdin.write('\r\n') #Number of start points to skip, plus one, default is 1

                        elif previous_line.find('Last point to use') > -1:
                            tot_pts = int(current_line.split()[0].strip().rstrip(')'))
                            if 'last' in args and args['last'] != '':
                                proc.stdin.write('%i\r\n' %(int(args['last'])))
                            else:
                                proc.stdin.write('\r\n') #Number of start points to skip, plus one, default is 1

                        elif previous_line.find('Output file') > -1:
                            proc.stdin.write('%s\r\n' %(outname)) #Output file, default is gnom.out

                        elif previous_line.find('Number of input files') > -1:
                            proc.stdin.write('\r\n')

                        #Not implimented yet in RAW.
                        elif previous_line2.find('Slit height setup') > -1:
                            pass

                        elif previous_line2.find('Slight width setup') > -1:
                            pass

                        elif previous_line2.find('Wavelength distribution setup') > -1:
                            pass

                        elif previous_line.find('FWHM of wavelength') > -1:
                            pass

                        elif data.find('Slit height experimental profile file') > -1:
                            pass

                        previous_line2 = previous_line
                        previous_line = current_line


                gnom_t.join()
        try:
            if save_ift:
                iftm=SASFileIO.loadOutFile(os.path.join(path, outname))[0]

            else:
                iftm = SASFileIO.parse_out_file(output.split('\n'))

        except IOError:
            raise SASExceptions.GNOMError('No GNOM output file present. GNOM failed to run correctly')

        if cfg:
            try:
                os.remove(os.path.join(path, 'gnom.cfg'))
            except Exception as e:
                print(e)
                print('GNOM cleanup failed to delete gnom.cfg!')

        if not new_gnom:
            try:
                os.remove(os.path.join(path, 'kern.bin'))
            except Exception as e:
                print(e)
                print('GNOM cleanup failed to delete kern.bin!')

        return iftm

    else:
        print('Cannot find ATSAS')
        raise SASExceptions.NoATSASError('Cannot find gnom.')
        return None


def runDatgnom(rg, atsasDir, path, datname, outname, first_pt, last_pt):
    #This runs the ATSAS package DATGNOM program, to automatically find the Dmax and P(r) function
    #of a scattering profile.

    opsys = platform.system()

    if opsys == 'Windows':
        datgnomDir = os.path.join(atsasDir, 'datgnom.exe')
        shell=False
    else:
        datgnomDir = os.path.join(atsasDir, 'datgnom')
        shell=True

    if os.path.exists(datgnomDir):

        my_env = setATSASEnv(atsasDir)

        cmd = '"{}" -o "{}" -r {} '.format(datgnomDir, outname, rg)

        if first_pt is not None:
            cmd = cmd + '--first={} '.format(first_pt+1)

        if last_pt is not None:
            cmd = cmd + ' --last={} '.format(last_pt+1)

        cmd = cmd + '"{}"'.format(datname)

        process=subprocess.Popen(cmd, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, shell=shell, cwd=path, env=my_env)

        output, error = process.communicate()

        if not isinstance(output, str):
            output = str(output, encoding='UTF-8')

        if not isinstance(error, str):
            error = str(error, encoding='UTF-8')

        error = error.strip()

        if (error == 'Cannot define Dmax' or error=='Could not find Rg'
            or error=='No intensity values (positive) found'
            or error == 'LOADATF --E- No data lines recognized.'
            or error == 'error: rg not specified'
            or 'error' in error):
            datgnom_success = False
        else:
            datgnom_success = True

        if datgnom_success:
            try:
                iftm=SASFileIO.loadOutFile(os.path.join(path, outname))[0]
            except Exception:
                iftm = None
        else:
            iftm = None

        return iftm

    else:
        print('Cannot find ATSAS')
        raise SASExceptions.NoATSASError('Cannot find datgnom.')


def writeGnomCFG(fname, outname, dmax, args):
    #This writes the GNOM CFG file, using the arguments passed into the function.
    datadir = os.path.dirname(fname)

    f = open(os.path.join(datadir, 'gnom.cfg'),'w')

    f.write('This line intentionally left blank\n')
    f.write('PRINTER C [      postscr     ]  Printer type\n')
    if 'form' in args and args['form'] != '':
        f.write('FORFAC  C [         %s         ]  Form factor file (valid for JOB=2)\n' %(args['form']))
    else:
        f.write('FORFAC  C [                  ]  Form factor file (valid for JOB=2)\n')
    if 'expert' in args and args['expert'] != '':
        f.write('EXPERT  C [     %s         ]  File containing expert parameters\n' %(args['expert']))
    else:
        f.write('EXPERT  C [     none         ]  File containing expert parameters\n')
    f.write('INPUT1  C [        %s        ]  Input file name (first file)\n' %(fname))
    f.write('INPUT2  C [       none       ]  Input file name (second file)\n')
    f.write('NSKIP1  I [       0         ]  Number of initial points to skip\n')
    f.write('NSKIP2  I [        0         ]  Number of final points to skip\n')
    f.write('OUTPUT  C [       %s         ]  Output file\n' %(outname))
    if 'angular' in args and args['angular'] != 1:
        f.write('ISCALE  I [       %s         ]  Angular scale of input data\n' %(args['angular']))
    else:
        f.write('ISCALE  I [        1         ]  Angular scale of input data\n')
    f.write('PLOINP  C [       n          ]  Plotting flag: input data (Y/N)\n')
    f.write('PLORES  C [       n          ]  Plotting flag: results    (Y/N)\n')
    f.write('EVAERR  C [       y          ]  Error flags: calculate errors   (Y/N)\n')
    f.write('PLOERR  C [       n          ]  Plotting flag: p(r) with errors (Y/N)\n')
    f.write('PLOALPH C [       n          ]  Plotting flag: alpha distribution (Y/N)\n')
    f.write('LKERN   C [       n          ]  Kernel file status (Y/N)\n')
    if 'system' in args and args['system'] != 0:
        f.write('JOBTYP  I [       %s         ]  Type of system (0/1/2/3/4/5/6)\n' %(args['system']))
    else:
        f.write('JOBTYP  I [       0          ]  Type of system (0/1/2/3/4/5/6)\n')
    if 'rmin' in args and args['rmin'] != -1:
        f.write('RMIN    R [        %s         ]  Rmin for evaluating p(r)\n' %(args['rmin']))
    else:
        f.write('RMIN    R [                 ]  Rmin for evaluating p(r)\n')
    f.write('RMAX    R [        %s        ]  Rmax for evaluating p(r)\n' %(str(dmax)))
    if 'rmin_zero' in args and args['rmin_zero'] != '':
        f.write('LZRMIN  C [      %s          ]  Zero condition at r=RMIN (Y/N)\n' %(args['rmin_zero']))
    else:
        f.write('LZRMIN  C [       Y          ]  Zero condition at r=RMIN (Y/N)\n')
    if 'rmax_zero' in args and args['rmax_zero'] != '':
        f.write('LZRMAX  C [      %s          ]  Zero condition at r=RMAX (Y/N)\n' %(args['rmax_zero']))
    else:
        f.write('LZRMAX  C [       Y          ]  Zero condition at r=RMAX (Y/N)\n')
    f.write('KERNEL  C [       kern.bin   ]  Kernel-storage file\n')
    f.write('DEVIAT  R [      0.0         ]  Default input errors level\n')
    f.write('IDET    I [       0          ]  Experimental set up (0/1/2)\n')
    f.write('FWHM1   R [       0.0        ]  FWHM for 1st run\n')
    f.write('FWHM2   R [                  ]  FWHM for 2nd run\n')
    f.write('AH1     R [                  ]  Slit-height parameter AH (first  run)\n')
    f.write('LH1     R [                  ]  Slit-height parameter LH (first  run)\n')
    f.write('AW1     R [                  ]  Slit-width  parameter AW (first  run)\n')
    f.write('LW1     R [                  ]  Slit-width  parameter LW (first  run)\n')
    f.write('AH2     R [                  ]  Slit-height parameter AH (second run)\n')
    f.write('LH2     R [                  ]  Slit-height parameter LH (second run)\n')
    f.write('AW2     R [                  ]  Slit-width  parameter AW (second run)\n')
    f.write('LW2     R [                  ]  Slit-width  parameter LW (second run)\n')
    f.write('SPOT1   C [                  ]  Beam profile file (first run)\n')
    f.write('SPOT2   C [                  ]  Beam profile file (second run)\n')
    if 'alpha' in args and args['alpha'] !=0.0:
        f.write('ALPHA   R [      %s         ]  Initial ALPHA\n' %(str(args['alpha'])))
    else:
        f.write('ALPHA   R [      0.0         ]  Initial ALPHA\n')
    if 'npts' in args and args['npts'] !=101:
        f.write('NREAL   R [       %s        ]  Number of points in real space\n' %(str(args['npts'])))
    else:
        f.write('NREAL   R [       101        ]  Number of points in real space\n')
    f.write('COEF    R [                  ]\n')
    if 'radius56' in args and args['radius56'] != -1:
        f.write('RAD56   R [         %s         ]  Radius/thickness (valid for JOB=5,6)\n' %(args['radius56']))
    else:
        f.write('RAD56   R [                  ]  Radius/thickness (valid for JOB=5,6)\n')
    f.write('NEXTJOB C [        n         ]\n')


    f.close()


def runDatmw(rg, i0, first, method, atsasDir, path, datname):
    #This runs the ATSAS package DATMW program, to automatically find the M.W.
    #using one of the defined methods.

    opsys = platform.system()

    if opsys == 'Windows':
        datmwDir = os.path.join(atsasDir, 'datmw.exe')
    else:
        datmwDir = os.path.join(atsasDir, 'datmw')

    if os.path.exists(datmwDir):

        my_env = setATSASEnv(atsasDir)

        cmd = '"{}" --method={} --rg={} --i0={} --first={} {}'.format( datmwDir,
            method, rg, i0, first+1, datname)

        process=subprocess.Popen(cmd, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, shell=True, cwd=path, env=my_env)

        output, error = process.communicate()

        if not isinstance(output, str):
            output = str(output, encoding='UTF-8')

        if not isinstance(error, str):
            error = str(error, encoding='UTF-8')

        error = error.strip()

        if error != '':
            raise SASExceptions.NoATSASError('Error running datmw.')

        ret_values = ()

        if output != '':
            if method == 'bayes':
                mw, mw_score, ci_lower, ci_upper, ci_score, _ = output.split()

                mw = float(mw.strip())/1000.
                mw_score = float(mw_score.strip())
                ci_lower = float(ci_lower.strip())/1000.
                ci_upper = float(ci_upper.strip())/1000.
                ci_score = float(ci_score.strip())

                ret_values = (mw, mw_score, ci_lower, ci_upper, ci_score)

            elif method == 'shapesize':
                mw, _ = output.split()

                mw = float(mw.strip())/1000.

                ret_values = (mw)

        return ret_values

    else:
        raise SASExceptions.NoATSASError('Cannot find datmw.')

def runDatclass(rg, i0, first, atsasDir, path, datname):
    #This runs the ATSAS package DATCLASS program, to find the M.W. using
    #the shape and size method.

    opsys = platform.system()

    if opsys == 'Windows':
        datclassDir = os.path.join(atsasDir, 'datclass.exe')
    else:
        datclassDir = os.path.join(atsasDir, 'datclass')

    if os.path.exists(datclassDir):

        my_env = setATSASEnv(atsasDir)

        cmd = '"{}" --rg={} --i0={} --first={} {}'.format(datclassDir, rg, i0,
            first+1, datname)

        process=subprocess.Popen(cmd, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, shell=True, cwd=path, env=my_env)

        output, error = process.communicate()

        if not isinstance(output, str):
            output = str(output, encoding='UTF-8')

        if not isinstance(error, str):
            error = str(error, encoding='UTF-8')

        error = error.strip()

        if error != '':
            raise SASExceptions.NoATSASError('Error running datclass.')

        ret_values = ()

        if output != '':
            shape, mw, dmax, _ = output.split()

            shape=shape.strip()
            try:
                mw = float(mw.strip())/1000.
            except ValueError:
                mw = -1
            try:
                dmax = float(dmax.strip())
            except ValueError:
                dmax = -1

            ret_values = (shape, mw, dmax)

        return ret_values

    else:
        raise SASExceptions.NoATSASError('Cannot find datclass.')

def runDammif(fname, prefix, args, path, atsasDir):
    #Note: This run dammif command must be run with the current working directory as the directory
    #where the file is located. Otherwise, there are issues if the filepath contains a space.

    fname = os.path.split(fname)[1]

    opsys = platform.system()

    if opsys == 'Windows':
        dammifDir = os.path.join(atsasDir, 'dammif.exe')
    else:
        dammifDir = os.path.join(atsasDir, 'dammif')

    version = getATSASVersion(atsasDir).split('.')

    if os.path.exists(dammifDir):
        my_env = setATSASEnv(atsasDir)

        if args['mode'].lower() == 'fast' or args['mode'].lower() == 'slow':

            command = '"%s" --mode=%s --prefix="%s" --unit=%s --symmetry=%s --anisometry=%s' %(dammifDir, args['mode'], prefix, args['unit'], args['sym'], args['anisometry'])

            if (int(version[0]) == 3 and int(version[1]) < 1) or int(version[0]) < 3:
                if args['omitSolvent']:
                    command = command + ' --omit-solvent'

            if args['chained']:
                command = command + ' --chained'
            if args['constant'] != '':
                command = command + ' --constant=%s' %(args['constant'])

            command = command + ' "%s"' %(fname)

            if opsys == 'Windows':
                proc = subprocess.Popen(command, cwd=path, env=my_env,
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            else:
                proc = subprocess.Popen(command, shell=True, cwd=path,
                    env=my_env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

        else:
            #Solution for non-blocking reads adapted from stack overflow
            #http://stackoverflow.com/questions/375427/non-blocking-read-on-a-subprocess-pipe-in-python
            def enqueue_output(out, queue):
                dammifRunning = False
                line = 'test'
                line2=''
                while line != '' and not dammifRunning:
                    line = out.read(1)

                    if not isinstance(line, str):
                        line = str(line, encoding='UTF-8')

                    line2+=line
                    if line == ':':
                        if line2.find('Log opened') > -1:
                            dammifRunning = True
                        queue.put_nowait([line2])
                        line2=''

            dammif_q = queue.Queue()

            dammifStarted = False

            if opsys == 'Windows':
                proc = subprocess.Popen('"%s"' %(dammifDir), stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, cwd=path,
                    universal_newlines=True, bufsize=1, env=my_env)
            else:
                proc = subprocess.Popen('"%s"' %(dammifDir), shell=True,
                    stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT, cwd=path, universal_newlines=True,
                    bufsize=1, env=my_env)
            dammif_t = threading.Thread(target=enqueue_output, args=(proc.stdout, dammif_q))
            dammif_t.daemon = True
            dammif_t.start()
            previous_line = ''

            previous_data = []

            while proc.poll() is None and not dammifStarted:
                data = None
                try:
                    data = dammif_q.get_nowait()
                    data = data[0]
                    dammif_q.task_done()
                except queue.Empty:
                    pass

                if data is not None:
                    current_line = data
                    if data.find('GNOM output file to read?') > -1:
                        proc.stdin.write('%s\r\n' %(fname)) #Dammif input file, no default

                    elif previous_line.find('nanometer') > -1:
                        proc.stdin.write('%s\r\n' %(args['unit'])) #Dammif input file units, default unknown

                    elif previous_line.find('Output file prefix?') > -1:
                        proc.stdin.write('%s\r\n' %(prefix)) #Dammif output file prefix, default dammif

                    elif previous_line.find('Omit output of solvent') > -1:
                        if args['omitSolvent']:
                            proc.stdin.write('%s\r\n' %('no')) #Omit solvent bead output file, default yes
                        else:
                            proc.stdin.write('\r\n')

                    elif previous_line.find('Create pseudo chains') > -1:
                        if args['chained']:
                            proc.stdin.write('%s\r\n' %('yes')) #Make pseudo chains, default no
                        else:
                            proc.stdin.write('\r\n')

                    elif data.find('p1)') > -1:
                        proc.stdin.write('%s\r\n' %(args['sym'])) #Particle symmetry, default P1

                    elif previous_line.find('prolate, (o) oblate') > -1:
                        proc.stdin.write('%s\r\n' %(args['anisometry'])) #Particle anisometry, default Unknown

                    elif data.find('for automatic (default)') > -1:
                        if args['constant'] != '':
                            proc.stdin.write('%s\r\n' %(args['constant'])) #Subtract constant offset, default automatic
                        else:
                            proc.stdin.write('\r\n')

                    elif previous_line.find('(s) slow') > -1:
                        proc.stdin.write('i\r\n') #Annealing setup, default slow

                    elif previous_line.find('Maximum bead count') > -1:
                        if args['maxBead'] > -1:
                            proc.stdin.write('%i\r\n' %(args['maxBead'])) #Maximum beads to be used, default unlimited
                        else:
                            proc.stdin.write('\r\n')

                    elif previous_line.find('(rc) random-chain (default:') > -1:
                        proc.stdin.write('%s\r\n' %(args['shape'])) #Particle expected shape, default Unknown

                    elif previous_line.find('Dummy atom radius?') > -1:
                        if args['radius'] > -1:
                            proc.stdin.write('%f\r\n' %(args['radius'])) #Dummy atom radius, default 1.0
                        else:
                            proc.stdin.write('\r\n')

                    elif previous_line.find('Maximum number of spherical harmonics') > -1:
                        if args['harmonics'] > -1:
                            proc.stdin.write('%i\r\n' %(args['harmonics'])) #Maximum number of spherical harmonics to use (1-50), default 20
                        else:
                            proc.stdin.write('\r\n')

                    elif previous_line.find('Proportion of the curve to be fitted') > -1:
                        if args['propFit'] > -1:
                            proc.stdin.write('%f\r\n' %(args['propFit'])) #Proportion of curve to be fitted, default 1.00
                        else:
                            proc.stdin.write('\r\n')

                    elif data.find('emphasised porod)') > -1:
                        if args['curveWeight'] != '':
                            proc.stdin.write('%s\r\n' %(args['curveWeight'])) #Curve weighting function, default emphasised porod
                        else:
                            proc.stdin.write('\r\n')

                    elif previous_line.find('Initial random seed?') > -1:
                        if args['seed'] != '':
                            proc.stdin.write('%s\r\n' %(args['seed'])) #Initial random seed, default current time
                        else:
                            proc.stdin.write('\r\n')

                    elif previous_line.find('Maximum number of temperature steps') > -1:
                        if args['maxSteps'] > -1:
                            proc.stdin.write('%i\r\n' %(args['maxSteps'])) #Maximum number of temperature steps, default 200
                        else:
                            proc.stdin.write('\r\n')

                    elif previous_line.find('Minimum number of successes') > -1:
                        if args['minSuccess'] > -1:
                            proc.stdin.write('%i\r\n' %(args['minSuccess'])) #Minimum number of success per temperature step to continue, default 200
                        else:
                            proc.stdin.write('\r\n')

                    elif previous_line.find('Maximum number of iterations within a single temperature step?') > -1:
                        if args['maxIters'] > -1:
                            proc.stdin.write('%i\r\n' %(args['maxIters'])) #Maximum number of iterations per temperature step, default 200000
                        else:
                            proc.stdin.write('\r\n')

                    elif previous_line.find('is decreased?') > -1:
                        if args['maxSuccess'] > -1:
                            proc.stdin.write('%i\r\n' %(args['maxSuccess'])) #Maximum number of successes per T step, before T is decrease, defaul 20000
                        else:
                            proc.stdin.write('\r\n')

                    elif previous_line.find('Temperature schedule factor?') > -1:
                        if args['TFactor'] > -1:
                            proc.stdin.write('%f\r\n' %(args['TFactor'])) #Maximum number of successes per T step, before T is decrease, defaul 20000
                        else:
                            proc.stdin.write('\r\n')

                    elif previous_line.find('Rg penalty weight?') > -1:
                        if args['RgWeight'] > -1:
                            proc.stdin.write('%f\r\n' %(args['RgWeight'])) #Maximum number of successes per T step, before T is decrease, defaul 20000
                        else:
                            proc.stdin.write('\r\n')

                    elif previous_line.find('Center penalty weight?') > -1:
                        if args['cenWeight'] > -1:
                            proc.stdin.write('%f\r\n' %(args['cenWeight'])) #Maximum number of successes per T step, before T is decrease, defaul 20000
                        else:
                            proc.stdin.write('\r\n')

                    elif previous_line.find('Looseness penalty weight?') > -1:
                        if args['looseWeight'] > -1:
                            proc.stdin.write('%f\r\n' %(args['looseWeight'])) #Maximum number of successes per T step, before T is decrease, defaul 20000
                        else:
                            proc.stdin.write('\r\n')
                    elif data.find('Log opened') > -1:
                        dammifStarted = True

                    previous_line = current_line

                    if previous_data.count(data) > 20:
                        raise SASExceptions.ATSASError('Interactive mode not running correctly')

                    previous_data.append(data)

            # proc.stdout.close()
            # proc.stdin.close()

        return proc
    else:
        print('Cannot find ATSAS')
        raise SASExceptions.NoATSASError('Cannot find dammif.')
        return None


def runDamaver(flist, path, atsasDir, prefix, symmetry='P1', enantiomorphs='YES',
   nbeads=5000, method='NSD', lm=5, ns=51, smax=0.5):

    opsys = platform.system()

    if opsys == 'Windows':
        damaverDir = os.path.join(atsasDir, 'damaver.exe')
    else:
        damaverDir = os.path.join(atsasDir, 'damaver')

    version = getATSASVersion(atsasDir).split('.')

    if os.path.exists(damaverDir):
        my_env = setATSASEnv(atsasDir)

        command = '"{}" --nbeads={} --enantiomorphs={}'.format(damaverDir, nbeads,
            enantiomorphs)

        if (int(version[0]) == 3 and int(version[1]) < 1) or int(version[0]) < 3:
            command += ' --symmetry=%s --automatic' %(symmetry)

        if (int(version[0]) == 3 and int(version[1]) >= 1) or int(version[0]) > 3:
            command += ' --method={} --prefix={} --lm={} --ns={} --smax={}'.format(method,
                prefix, lm, ns, smax)

        for item in flist:
            command = command + ' "%s"' %(item)

        if opsys == 'Windows':
            process=subprocess.Popen(command, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, cwd=path, env=my_env)
        else:
            process=subprocess.Popen(command, shell=True, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, cwd=path, env=my_env)

        return process

def runSupcomb(file1, file2, path, atsasDir, symmetry='P1', mode='slow',
    superposition='ALL', enantiomorphs='YES', proximity='NSD',
    fraction=1.0):

    opsys = platform.system()

    if opsys == 'Windows':
        supcombDir = os.path.join(atsasDir, 'supcomb.exe')
    else:
        supcombDir = os.path.join(atsasDir, 'supcomb')

    name, ext = os.path.splitext(file2)
    outname = '{}_aligned{}'.format(name, ext)

    if os.path.exists(supcombDir):
        my_env = setATSASEnv(atsasDir)

        command = ('"{}" --symmetry={} --mode={} --superposition={} '
            '--enantiomorphs={} --proximity={} --fraction={} "{}" "{}" '
            '-o "{}"'.format(supcombDir, symmetry, mode, superposition,
                enantiomorphs, proximity, fraction, file1, file2, outname))

        if opsys == 'Windows':
            process=subprocess.Popen(command, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, cwd=path, env=my_env)
        else:
            process=subprocess.Popen(command, shell=True, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, cwd=path, env=my_env)

    else:
        process = None

    return process

def runCifsup(file1, file2, path, atsasDir, method='NSD', selection='ALL',
    enantiomorphs='YES', target_model_id=1, ref_model_id=1, lm=5, ns=51,
    smax=0.5, beads=2000):

    opsys = platform.system()

    if opsys == 'Windows':
        cifsupDir = os.path.join(atsasDir, 'cifsup.exe')
    else:
        cifsupDir = os.path.join(atsasDir, 'cifsup')

    name, ext = os.path.splitext(file2)
    outname = '{}_aligned{}'.format(name, ext)

    if os.path.exists(cifsupDir):
        my_env = setATSASEnv(atsasDir)

        command = ('"{}" --method={} --selection={} -e={} -lm={} -ns={} '
            '-smax="{}" --beads={} --template-model={} --movable-model={} '
            '-o "{}" "{}" "{}"'.format(cifsupDir, method, selection, enantiomorphs,
                lm, ns, smax, beads, target_model_id, ref_model_id, outname,
                file1, file2))

        if opsys == 'Windows':
            process=subprocess.Popen(command, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, cwd=path, env=my_env)
        else:
            process=subprocess.Popen(command, shell=True, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, cwd=path, env=my_env)

    else:
        process = None

    return process

def runAmbimeter(fname, prefix, args, path, atsasDir):

    opsys = platform.system()

    if opsys == 'Windows':
        ambimeterDir = os.path.join(atsasDir, 'ambimeter.exe')
    else:
        ambimeterDir = os.path.join(atsasDir, 'ambimeter')

    if os.path.exists(ambimeterDir):
        command = '"%s" --srg=%s --prefix="%s" --files=%s "%s"' %(ambimeterDir, args['sRg'], prefix, args['files'], fname)

        my_env = setATSASEnv(atsasDir)

        process=subprocess.Popen(command, shell=True, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, cwd=path, env=my_env, universal_newlines=True)

        start = time.time()
        while process.poll() is None:
            if time.time()-start > 120:
                raise SASExceptions.NoATSASError('Ambimeter timed out. Try running it from the command line to diagnose this problem.')
                return None

        output, error = process.communicate()

        if not isinstance(output, str):
            output = str(output, encoding='UTF-8')

        if not isinstance(error, str):
            error = str(error, encoding='UTF-8')

        lines = output.split('\n')
        ambiCats = lines[0].split(':')[-1].strip()
        ambiScore = lines[1].split(':')[-1].strip()
        ambiEval = lines[2]

        return ambiCats, ambiScore, ambiEval

    else:
        print('Cannot find ATSAS')
        raise SASExceptions.NoATSASError('Cannot find ambimeter.')
        return None

def runDamclust(flist, path, atsasDir, symmetry='P1'):

    opsys = platform.system()

    if opsys == 'Windows':
        damclustDir = os.path.join(atsasDir, 'damclust.exe')
    else:
        damclustDir = os.path.join(atsasDir, 'damclust')


    if os.path.exists(damclustDir):
        my_env = setATSASEnv(atsasDir)

        command = '"%s" --symmetry=%s' %(damclustDir, symmetry)

        for item in flist:
            command = command + ' "%s"' %(item)

        if opsys == 'Windows':
            process=subprocess.Popen(command, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, cwd=path, env=my_env)
        else:
            process=subprocess.Popen(command, shell=True, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, cwd=path, env=my_env)

        return process


def runDammin(fname, prefix, args, path, atsasDir):
    #Note: This run dammin command must be run with the current working directory as the directory
    #where the file is located. Otherwise, there are issues if the filepath contains a space.

    fname = os.path.split(fname)[1]

    opsys = platform.system()

    if opsys == 'Windows':
        dammifDir = os.path.join(atsasDir, 'dammin.exe')
    else:
        dammifDir = os.path.join(atsasDir, 'dammin')

    if os.path.exists(dammifDir):
        my_env = setATSASEnv(atsasDir)

        if args['mode'].lower() == 'fast' or args['mode'].lower() == 'slow':
            if args['unit'] == 'Angstrom':
                unit = '1'
            elif args['unit'] == 'Nanometer':
                unit = '2'
            else:
                unit = '1'

            command = '"%s" --mo=%s --lo="%s" --un=%s --sy=%s' %(dammifDir, args['mode'], prefix, unit, args['sym'])

            if args['anisometry'] != 'Unknown':
                command += command + ' --an=%s' %(args['anisometry'])

            if args['initialDAM'].lower() in ['s', 'e', 'c', 'p']:
                command += ' --sv={}'.format(args['initialDAM'].lower())
            else:
                command += ' --svfile={}'.format(args['initialDAM'])

            if args['seed'] != '':
                command = command + ' --seed={}'.format(args['seed'])

            command = command + ' "%s"' %(fname)

            if opsys == 'Windows':
                proc = subprocess.Popen(command, cwd=path, env=my_env,
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            else:
                proc = subprocess.Popen(command, shell=True, cwd=path,
                    env=my_env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

        else:
            #Solution for non-blocking reads adapted from stack overflow
            #http://stackoverflow.com/questions/375427/non-blocking-read-on-a-subprocess-pipe-in-python
            def enqueue_output(out, queue):
                dammifRunning = False
                line = 'test'
                line2=''
                while line != '' and not dammifRunning:
                    line = out.read(1)

                    if not isinstance(line, str):
                        line = str(line, encoding='UTF-8')

                    line2+=line
                    if line == ':':
                        queue.put_nowait([line2])
                        line2=''
                    elif line == '=':
                        if line2.find('procedure started') > -1:
                            dammifRunning = True
                            queue.put_nowait([line2])
                            line2=''


            dammif_q = queue.Queue()

            dammifStarted = False

            if opsys == 'Windows':
                proc = subprocess.Popen('%s' %(dammifDir),
                    stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT, cwd=path, universal_newlines=True,
                    bufsize=1, env=my_env)
            else:
                proc = subprocess.Popen('%s' %(dammifDir), shell=True,
                    stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT, cwd=path, universal_newlines=True,
                    bufsize=1, env=my_env)
            dammif_t = threading.Thread(target=enqueue_output, args=(proc.stdout, dammif_q))
            dammif_t.daemon = True
            dammif_t.start()

            previous_data = []

            while proc.poll() is None and not dammifStarted:
                data = None

                try:
                    data = dammif_q.get_nowait()
                    data = data[0]
                    dammif_q.task_done()
                except queue.Empty:
                    pass

                if data is not None:
                    if data.find('[E]xpert') > -1:
                        if args['mode'] == 'Refine':
                            proc.stdin.write('S\r\n') #Dammif run mode
                        else:
                            proc.stdin.write('E\r\n') #Dammif run mode

                    elif data.find('Log file name') > -1:
                        proc.stdin.write('%s\r\n' %(prefix)) #Dammif input file, no default

                    elif data.find('GNOM output file') > -1:
                        proc.stdin.write('%s\r\n' %(fname)) #Dammif input file, no default

                    elif data.find('project description') > -1:
                        proc.stdin.write('\r\n') #Extra information, default is none

                    elif data.find('1/nm') > -1:
                        if args['unit'] == 'Angstrom':
                            proc.stdin.write('1\r\n') #Dammif input file units, default 1/angstrom
                        elif args['unit'] == 'Nanometer':
                            proc.stdin.write('2\r\n') #Dammif input file units, default 1/angstrom
                        else:
                            proc.stdin.write('\r\n') #Dammif input file units, default 1/angstrom

                    elif data.find('Portion of the curve') > -1:
                        if args['propFit'] > -1:
                            proc.stdin.write('%f\r\n' %(args['propFit'])) #Proportion of curve to be fitted, default 1.00
                        else:
                            proc.stdin.write('\r\n')

                    elif data.find('parallelepiped') > -1:
                        if 'initialDAM' in args:
                            proc.stdin.write('%s\r\n' %(args['initialDAM'])) #Initial dammin shape, default sphere (S)
                        else:
                            proc.stdin.write('\r\n')

                    elif data.find('PICO') > -1:
                        proc.stdin.write('%s\r\n' %(args['sym'])) #Particle symmetry, default P1

                    elif data.find('<P>rolate') > -1:
                        proc.stdin.write('%s\r\n' %(args['anisometry'])) #Particle anisometry, default Unknown

                    elif data.find('knots') > -1 and args['mode'] != 'Refine':
                        if 'knots' in args:
                            proc.stdin.write('%s\r\n' %(str(args['knots']))) #Number of knots in the curve to be fit, default 20
                        else:
                            proc.stdin.write('\r\n')

                    elif data.find('automatic subtraction') > -1:
                        if 'damminConstant' in args:
                            proc.stdin.write('%f\r\n' %(args['damminConstant'])) #Subtract constant offset, default automatic
                        else:
                            proc.stdin.write('\r\n')

                    elif data.find('Maximum order of harmonics') > -1 and args['mode'] != 'Refine':
                        if args['harmonics'] > -1:
                            proc.stdin.write('%i\r\n' %(args['harmonics'])) #Maximum number of spherical harmonics to use (1-50), default 20
                        else:
                            proc.stdin.write('\r\n')

                    elif data.find('Sphere  diameter [Angstrom]') > -1:
                        if args['diameter'] > -1:
                            proc.stdin.write('%f\r\n' %(args['diameter'])) #Dummy atom diameter, default 1.0
                        else:
                            proc.stdin.write('\r\n')

                    elif data.find('Packing radius') > -1 and args['mode'] != 'Refine':
                        if args['packing'] > -1:
                            proc.stdin.write('%f\r\n' %(args['packing']))
                        else:
                            proc.stdin.write('\r\n')

                    elif data.find('coordination sphere') > -1 and args['mode'] != 'Refine':
                        if args['coordination'] > -1:
                            proc.stdin.write('%f\r\n' %(args['coordination']))
                        else:
                            proc.stdin.write('\r\n')

                    elif data.find('Looseness penalty weight') > -1 and args['mode'] != 'Refine':
                        if args['looseWeight'] > -1:
                            proc.stdin.write('%f\r\n' %(args['looseWeight']))
                        else:
                            proc.stdin.write('\r\n')

                    elif data.find('Disconnectivity penalty') > -1 and args['mode'] != 'Refine':
                        if args['disconWeight'] > -1:
                            proc.stdin.write('%f\r\n' %(args['disconWeight']))
                        else:
                            proc.stdin.write('\r\n')

                    elif data.find('Peripheral penalty weight') > -1 and args['mode'] != 'Refine':
                        if args['periphWeight'] > -1:
                            proc.stdin.write('%f\r\n' %(args['periphWeight']))
                        else:
                            proc.stdin.write('\r\n')

                    elif data.find('Fixing thresholds') > -1 and args['mode'] != 'Refine':
                        proc.stdin.write('\r\n')

                    elif data.find('Randomize the structure') > -1 and args['mode'] != 'Refine':
                        proc.stdin.write('\r\n')

                    elif data.find('0=s^2') > -1 and args['mode'] != 'Refine' and args['mode'] != 'Refine':
                        proc.stdin.write('%s\r\n' %(args['damminCurveWeight'])) #Curve weighting function, default emphasised porod

                    elif data.find('scale factor') > -1 and args['mode'] != 'Refine':
                        proc.stdin.write('\r\n')

                    elif data.find('Initial annealing temperature') > -1 and args['mode'] != 'Refine':
                        proc.stdin.write('\r\n')

                    elif data.find('Annealing schedule factor') > -1 and args['mode'] != 'Refine':
                        if args['annealSched'] > -1:
                            proc.stdin.write('%f\r\n' %(args['annealSched']))
                        else:
                            proc.stdin.write('\r\n')

                    elif data.find('# of independent') > -1 and args['mode'] != 'Refine':
                        proc.stdin.write('\r\n')

                    elif data.find('Max # of iterations') > -1 and args['mode'] != 'Refine':
                        if args['maxIters'] > -1:
                            proc.stdin.write('%i\r\n' %(args['maxIters'])) #Maximum number of iterations per temperature step
                        else:
                            proc.stdin.write('\r\n')

                    elif data.find('Max # of successes') > -1 and args['mode'] != 'Refine':
                        if args['maxSuccess'] > -1:
                            proc.stdin.write('%i\r\n' %(args['maxSuccess']))
                        else:
                            proc.stdin.write('\r\n')

                    elif data.find('Min # of successes') > -1 and args['mode'] != 'Refine':
                        if args['minSuccess'] > -1:
                            proc.stdin.write('%i\r\n' %(args['minSuccess'])) #Minimum number of success per temperature step to continue, default 200
                        else:
                            proc.stdin.write('\r\n')

                    elif data.find('Max # of annealing steps') > -1 and args['mode'] != 'Refine':
                        if args['maxSteps'] > -1:
                            proc.stdin.write('%i\r\n' %(args['maxSteps'])) #Maximum number of temperature steps, default 200
                        else:
                            proc.stdin.write('\r\n')

                    elif data.find('Reset core') > -1:
                        proc.stdin.write('\r\n')

                    elif data.find('annealing procedure started') > -1:
                        dammifStarted = True


                    if previous_data.count(data) > 20:
                        raise SASExceptions.ATSASError('Interactive mode not running correctly')

                    previous_data.append(data)

            # proc.stdout.close()
            # proc.stdin.close()
            # proc.wait()

        return proc
    else:
        raise SASExceptions.NoATSASError('Cannot find dammif.')
        return None


def run_ambimeter_from_ift(ift, atsas_dir, qRg_max=4, save_models='none',
        save_prefix=None, datadir=None, write_ift=True, filename=None):
    """
    Evaluates ambiguity of a potential 3D reconstruction from a GNOM IFT (.out
    file) by running Ambimeter from the ATSAS package. Requires separate
    installation of the ATSAS package. Doesn't work on BIFT IFTs. Returns
    -1 and '' if it fails to run.

    Parameters
    ----------
    ift: :class:`bioxtasraw.SASM.IFTM`
        The GNOM IFT to be evaluated. If write_ift is False, an IFT already
        on disk is used and this parameter can be ``None``.
    qRg_max: float, optional
        The maximum qRg to be used when evaluating the ambiguity. Allowed
        range is 3-7, default is 4.
    save_models: {'all', 'best', 'none'} str, optional
        Whether to save all, the single best, or none of the models that
        ambimeter finds to be similar to the input ift. Default is 'none'.
        If set to 'all' or 'best', save_prefix and datadir parameters must
        be provided.
    save_prefix: str, optional
        The prefix to use for the saved modes, if any are saved.
    datadir: str, optional
        The datadir to use for reading a IFT already on disk and saving
        models from ambimeter.
    write_profile: bool, optional
        If True, the input ift is written to file. If False, then the
        input ift is ignored, and the ift specified by datadir and
        filename is used. This is convenient if you are trying to process
        a lot of files that are already on disk, as it saves having to read
        in each file and then save them again. Defaults to True. If False,
        you must provide a value for the datadir and filename parameters.
    filename: str, optional
        The filename of an ift on disk. Used if write_profile is False.
    atsas_dir: str, optional
        The directory of the atsas programs (the bin directory). If not provided,
        the API uses the auto-detected directory.

    Returns
    -------
    score: float
        The ambiguity score (A score), which is log base 10 of the number of
        compatible shape categories.
    categories: int
        The number of compatible shape categories.
    evaluation: str
        The Ambimeter evaluation of ift based on the ambiguity score.

    Raises
    ------
    SASEXceptions.NoATSASError
        If the Ambimeter program cannot be found in the ATSAS directory or
        running Ambimeter times out (>120 s).
    """


    # Set input and output filenames and directory
    if write_ift and save_models=='none':
        datadir = os.path.abspath(os.path.expanduser(tempfile.gettempdir()))

        filename = tempfile.NamedTemporaryFile(dir=datadir).name
        filename = os.path.split(filename)[-1] + '.out'

    elif write_ift:
        datadir = os.path.abspath(os.path.expanduser(datadir))
        filename = tempfile.NamedTemporaryFile(dir=datadir).name
        filename = os.path.split(filename)[-1] + '.out'

    else:
        datadir = os.path.abspath(os.path.expanduser(datadir))

    # Save profile if necessary, truncating q range as appropriate
    if write_ift:
        SASFileIO.writeOutFile(ift, os.path.join(datadir, filename))

    # Run ambimeter
    ambimeter_settings = {
        'sRg'   : qRg_max,
        'files' : save_models,
        }

    ret = runAmbimeter(filename, save_prefix, ambimeter_settings, datadir,
        atsas_dir)

    # Clean up
    if write_ift and os.path.isfile(os.path.join(datadir, filename)):
        try:
            os.remove(os.path.join(datadir, filename))
        except Exception:
            pass

    if ret is not None:
        categories = int(ret[0])
        score = float(ret[1])
        evaluation = ret[2]

    else:
        categories = -1
        score = -1
        evaluation = ''

    return score, categories, evaluation

def run_crysol(fnames, path, atsasDir, exp_fnames=None, prefix=None, lm=20,
    fb=17, ns=101, smax=0.5, units=None, dns=0.334, dro=0.03, constant=False,
    fit_solvent=True, energy=None, shell='directional', explicit_hydrogen=False,
    implicit_hydrogen=None, sub_element=None, model=None, chain=None,
    alternative_names=False):
    #This runs the ATSAS package CRYSOL program,

    opsys = platform.system()

    if opsys == 'Windows':
        crysolDir = os.path.join(atsasDir, 'crysol.exe')
    else:
        crysolDir = os.path.join(atsasDir, 'crysol')

    if os.path.exists(crysolDir):

        my_env = setATSASEnv(atsasDir)

        cmd = ('"{}" --lm={} --fb={} --ns={} --smax={} --dns={} --dro={} '
                '--shell={}'.format(crysolDir, lm, fb, ns, smax, dns, dro, shell))

        if constant:
            cmd += ' --constant'

        if units is not None:
            cmd += ' --units={}'.format(units)

        if not fit_solvent:
            cmd += ' --skip-minimization'

        if explicit_hydrogen:
            cmd += ' --explicit-hydrogens'

        if energy is not None:
            cmd += ' --energy={}'.format(energy)

        if implicit_hydrogen is not None:
            cmd += ' --implicit-hydrogen={}'.format(implicit_hydrogen)

        if sub_element is not None:
            cmd += ' --sub-element={}'.format(sub_element)

        if model is not None:
            cmd += ' --model={}'.format(model)

        if model is not None:
            cmd += ' --chain={}'.format(chain)

        if alternative_names:
            cmd += ' --alternative-names'

        if prefix is not None:
            cmd += ' -p "{}"'.format(prefix)

        cmd += ' "' + '" "'.join(fnames) + '"'

        if exp_fnames is not None:
            cmd += ' "' + '" "'.join(exp_fnames) + '"'

        process = subprocess.Popen(cmd, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, shell=True, cwd=path, env=my_env)

        return process

    else:
        raise SASExceptions.NoATSASError('Cannot find crysol.')


def run_secm_calcs(subtracted_sasm_list, use_subtracted_sasm, window_size,
    is_protein, error_weight, vp_density, vp_cutoff, vp_qmax, vc_cutoff,
    vc_qmax, vc_a_prot, vc_b_prot, vc_a_rna, vc_b_rna):

    #Now calculate the RG, I0, and MW for each SASM
    rg = np.zeros(len(subtracted_sasm_list),dtype=float)
    rger = np.zeros(len(subtracted_sasm_list),dtype=float)
    i0 = np.zeros(len(subtracted_sasm_list),dtype=float)
    i0er = np.zeros(len(subtracted_sasm_list),dtype=float)
    vcmw = np.zeros(len(subtracted_sasm_list),dtype=float)
    vcmwer = np.zeros(len(subtracted_sasm_list),dtype=float)
    vpmw = np.zeros(len(subtracted_sasm_list),dtype=float)
    vp = np.zeros(len(subtracted_sasm_list),dtype=float)
    vpcor = np.zeros(len(subtracted_sasm_list),dtype=float)

    if window_size == 1:
        for a in range(len(subtracted_sasm_list)):
            current_sasm = subtracted_sasm_list[a]
            use_current_sasm = use_subtracted_sasm[a]

            if use_current_sasm:
                #use autorg to find the Rg and I0
                rg[a], rger[a], i0[a], i0er[a], idx_min, idx_max = autoRg(current_sasm,
                    error_weight=error_weight)

                #Now use the rambo tainer 2013 method to calculate molecular weight
                if rg[a] > 0:
                    vcqmax = calcVqmax(current_sasm.getQ(),
                        current_sasm.getI(), rg[a], i0[a], vc_cutoff, vc_qmax)

                    vcmw[a], vcmwer[a], junk1, junk2 = calcVcMW(current_sasm, rg[a],
                        i0[a], vcqmax, vc_a_prot, vc_b_prot, vc_a_rna, vc_b_rna,
                        is_protein)

                    vpqmax = calcVqmax(current_sasm.getQ(),
                        current_sasm.getI(), rg[a], i0[a], vp_cutoff, vp_qmax)

                    vpmw[a], vp[a], vpcor[a] = calcVpMW(current_sasm.getQ(),
                        current_sasm.getI(), current_sasm.getErr(), rg[a], i0[a],
                        current_sasm.getQ()[idx_min], vp_density, vpqmax)
                else:
                    vcmw[a], vcmwer[a] = -1, -1
                    vpmw[a], vp[a], vpcor[a] = -1, -1, -1

            else:
                rg[a], rger[a], i0[a], i0er[a] = -1, -1, -1, -1
                vcmw[a], vcmwer[a] = -1, -1,
                vpmw[a], vp[a], vpcor[a] = -1, -1, -1

    else:
        for a in range(len(subtracted_sasm_list)-(window_size-1)):

            current_sasm_list = subtracted_sasm_list[a:a+window_size]

            truth_test = use_subtracted_sasm[a:a+window_size]

            index = a+(window_size-1)//2

            if np.all(truth_test):
                try:
                    current_sasm = SASProc.average(current_sasm_list, copy_params=False)
                except SASExceptions.DataNotCompatible:
                    return False, {}

                #use autorg to find the Rg and I0
                (rg[index], rger[index], i0[index], i0er[index], idx_min,
                    idx_max) = autoRg(current_sasm, error_weight=error_weight)

                #Now use the rambo tainer 2013 method to calculate molecular weight
                if rg[index] > 0:
                    vcqmax = calcVqmax(current_sasm.getQ(),
                        current_sasm.getI(), rg[a], i0[a], vc_cutoff, vc_qmax)

                    vcmw[index], vcmwer[index], junk1, junk2 = calcVcMW(current_sasm,
                        rg[index], i0[index], vcqmax, vc_a_prot, vc_b_prot,
                        vc_a_rna, vc_b_rna, is_protein)

                    vpqmax = calcVqmax(current_sasm.getQ(),
                        current_sasm.getI(), rg[index], i0[index], vp_cutoff, vp_qmax)

                    vpmw[index], vp[index], vpcor[index] = calcVpMW(current_sasm.getQ(),
                        current_sasm.getI(), current_sasm.getErr(), rg[index], i0[index],
                        current_sasm.getQ()[idx_min], vp_density, vpqmax)
                else:
                    vcmw[index], vcmwer[index] = -1, -1
                    vpmw[index], vp[index], vpcor[index] = -1, -1, -1
            else:
                rg[index], rger[index], i0[index], i0er[index] = -1, -1, -1, -1
                vcmw[index], vcmwer[index] = -1, -1,
                vpmw[index], vp[index], vpcor[index] = -1, -1, -1

    #Set everything that's nonsense to -1
    rg[rg<=0] = -1
    rger[rg==-1] = -1
    i0[i0<=0] = -1
    i0er[i0==-1] = -1

    vcmw[vcmw<=0] = -1
    vcmw[rg<=0] = -1
    vcmw[i0<=0] = -1
    vcmwer[vcmw==-1] = -1

    vpmw[vpmw<=0] = -1
    vpmw[vcmw==-1] = -1
    vp[vp<=0] = -1
    vp[vcmw==-1] = -1
    vpcor[vpcor<=0] = -1
    vpcor[vcmw==-1] = -1

    results = {'rg':    rg,
        'rger':         rger,
        'i0':           i0,
        'i0er':         i0er,
        'vcmw':         vcmw,
        'vcmwer':       vcmwer,
        'vpmw':         vpmw,
        'window_size':  window_size,
        'is_protein':   is_protein,
        'vp_density':   vp_density,
        }

    return True, results

def smooth_data(data, window_length=51, order=5):
    smoothed_data = scipy.signal.savgol_filter(data, window_length, order)
    return smoothed_data

def find_peaks(data, height=0.4, width=10, rel_height=0.5):
    """Finds peaks, expects normalized to max=1 smoothed data as input."""
    peaks = scipy.signal.find_peaks(data, height=height, width=width,
        rel_height=rel_height)
    return peaks

def integral_baseline(sasms, start_range, end_range, max_iter, min_iter):
    end_frames = list(range(end_range[0], end_range[1]+1))
    end_sasms = [sasms[j] for j in end_frames]

    sasm_bl = SASProc.average(end_sasms, forced=True, copy_params=False)
    i_bl = sasm_bl.getI()

    win_len = len(sasms)//2
    if win_len % 2 == 0:
        win_len = win_len+1
    win_len = min(51, win_len)

    order = min(5, win_len-1)

    intensity = np.array([sasm.getI() for sasm in sasms[start_range[-1]:end_range[0]+1]])
    intensity = np.apply_along_axis(smooth_data, 0, intensity, win_len, order)

    b = np.zeros_like(intensity)

    j = 0
    tols = []
    converged = False

    while j<max_iter and not converged:
        i_diff = intensity - b
        i_tot = i_diff.sum(axis=0)

        gamma = i_bl/i_tot

        d = gamma*i_diff

        b[1:] = d[1:].cumsum(axis=0)
        b[0, :] = 0

        old_b = copy.copy(b)

        if j > 0:
            tol = np.sum(np.abs(b-old_b))
            tols.append(tol)

        if j > min_iter:
            if tol <= min(tols[-100:]):
                converged=True

        j = j+1

    idx = np.where(b[-1,:] < 0)
    b[:,idx]=0

    return  b


def linear_baseline(sasms, start_range, end_range):
    start_frames = list(range(start_range[0], start_range[1]+1))
    start_sasms = [sasms[j] for j in start_frames]

    end_frames = list(range(end_range[0], end_range[1]+1))
    end_sasms = [sasms[j] for j in end_frames]

    frames = np.array(start_frames + end_frames)
    fit_sasms = start_sasms + end_sasms

    intensity = np.array([sasm.getI() for sasm in fit_sasms])
    err = np.array([sasm.getErr() for sasm in fit_sasms])

    fit_results = []

    for j in range(intensity.shape[1]):
        a, b, cov_a, cov_b = weighted_lin_reg(frames, intensity[:, j], err[:, j])
        fit_results.append((a, b, cov_a, cov_b))

    return fit_results


###############################################################################
#EFA below here
def runEFA(A, forward=True):
    """Runs the forward or backward evolving factor calculations."""
    slist = np.zeros_like(A)

    jmax = A.shape[1]

    if not forward:
        A = A[:,::-1]

    for j in range(jmax):
        s = np.linalg.svd(A[:, :j+1], full_matrices = False, compute_uv = False)
        slist[:s.size, j] = s

        if j > 0:
            slist[s.size-1:, j-1] = s[-1]

    return slist

def runRotation(D, intensity, err, ranges, force_positive, svd_v, previous_results=None,
    method='Hybrid', niter=1000, tol=1e-12):
    """
    Runs the full EFA rotation.

    :param numpy.array intensity: An array of scattering intensities with intensities
        corresponding to a single experiment in each column and intensities
        corresponding to a single q in each row.

    :param numpy.array err: An array of scattering intensity errors with each
        column being the errors associated with the corresponding column in the
        intensity matrix.

    :param numpy.array ranges: An array of the EFA ranges, which each row is
        the range of a given component, and contains two integers, the first is
        start of that component the second the end of the component.

    :param list force_positive: A list with as many entries as there are EFA
        components (i.e. rows in the ranges array). Each entry is either True or False,
        corresponding to whether the intensity is forced to remain positive or not.

    :param np.array svd_v: The right singular matrix obtained from SVD of the
        appropriate intensity matrix (either error normalized or otherwise). Note that
        for numpy.svd results, it initial returns V transpose. So if you had
        U, S, Vt = np.linalg.svd(...), this V = Vt.T.

    :param list previous_results: This list contains the previous results of
        EFA, if any. This is used to improve the starting guess. The first
        entry in the list is a boolean corresponding to whether the previous
        results converged, and the second is a dictionary of the previous results,
        corresponding to the rotation_data dictionary returned by this function.
        Defaults to None, which should be used if no previous results are available.

    :param str method: The method of EFA to be used. Options are 'Hybrid', 'Iterative',
        and 'Explicit'. Defaults to 'Hybrid'.

    :param int niter: Number of iterations to run in the iterative and hybrid methods.
        Defaults to 1000.

    :param float tol: Tolerance for convergence of the iterative and hybrid methods.
        Defaults to 1e-12.
    """

    init_dict = {'Hybrid'       : initHybridEFA,
                'Iterative'     : initIterativeEFA,
                'Explicit'      : initExplicitEFA}

    run_dict = {'Hybrid'        : runIterativeEFARotation,
                'Iterative'     : runIterativeEFARotation,
                'Explicit'      : runExplicitEFARotation}

    #Calculate the initial matrices
    num_sv = ranges.shape[0]

    M = np.zeros_like(svd_v[:,:num_sv])

    if previous_results is not None:
        converged, rotation_data = previous_results
    else:
        converged = False
        rotation_data = {}

    for j in range(num_sv):
        M[ranges[j][0]:ranges[j][1]+1, j] = 1

    if converged and M.shape[0] != rotation_data['C'].shape[0]:
        converged = False
        rotation_data = {}

    if converged:
        C_init = rotation_data['C']
    else:
        C_init = svd_v[:,:num_sv]

    V_bar = svd_v[:,:num_sv]

    failed, C, T = init_dict[method](M, num_sv, D, C_init, converged, V_bar) #Init takes M, num_sv, and D, C_init, and converged and returns failed, C, and T in that order. If a method doesn't use a particular variable, then it should return None for that result
    C, failed, converged, dc, k = run_dict[method](M, D, failed, C, V_bar, T, niter, tol, force_positive) #Takes M, D, failed, C, V_bar, T in that order. If a method doesn't use a particular variable, then it should be passed None for that variable.

    if not failed:
        if method != 'Explicit':
            conv_data = {'steps'   : dc,
                'iterations': k,
                'final_step': dc[-1],
                'options'   : {'niter': niter, 'tol': tol, 'method': method},
                'failed'    : False,
                }
        else:
            conv_data = {'steps'   : None,
                'iterations': None,
                'final_step': None,
                'options'   : {'niter': niter, 'tol': tol, 'method': method},
                'failed'    : False,
                }

    else:
        conv_data = {'steps'   : None,
                'iterations': None,
                'final_step': None,
                'options'   : {'niter': niter, 'tol': tol, 'method': method},
                'failed'    : True,
                }

    #Check whether the calculation converged

    if method != 'Explicit':
        if k == niter and dc[-1] > tol:
            converged = False
        elif failed:
            converged = False
        else:
            converged = True

    else:
        if failed:
            converged = False
        else:
            converged = True

    if converged:
        #Calculate SAXS basis vectors
        mult = np.linalg.pinv(np.transpose(M*C))
        intensity = np.dot(intensity, mult)
        err = np.sqrt(np.dot(np.square(err), np.square(mult)))

        int_norm = np.dot(D, mult)
        resid = D - np.dot(int_norm, np.transpose(M*C))

        chisq = np.mean(np.square(resid),0)

        #Save the results
        rotation_data = {'M'   : M,
            'C'     : C,
            'int'   : intensity,
            'err'   : err,
            'chisq' : chisq}

    return converged, conv_data, rotation_data

def runExplicitEFARotation(M, D, failed, C, V_bar, T, niter, tol, force_pos):
    num_sv = M.shape[1]

    for i in range(num_sv):
        V_i_0 = V_bar[np.logical_not(M[:,i]),:]

        T[i,1:num_sv] = -np.dot(V_i_0[:,0].T, np.linalg.pinv(V_i_0[:,1:num_sv].T))

    C = np.dot(T, V_bar.T)

    C = C.T

    if -1*C.min() > C.max():
        C = C*-1

    converged = True

    csum = np.sum(M*C, axis = 0)
    if (int(np.__version__.split('.')[0]) > 1 or int(np.__version__.split('.')[0]) == 1
        and int(np.__version__.split('.')[1])>=10):
        C = C/np.broadcast_to(csum, C.shape) #normalizes by the sum of each column
    else:
        norm = np.array([csum for i in range(C.shape[0])])

        C = C/norm #normalizes by the sum of each column

    return C, failed, converged, None, None

def runIterativeEFARotation(M, D, failed, C, V_bar, T, niter, tol, force_pos):
    #Carry out the calculation to convergence
    k = 0
    converged = False

    dc = []

    while k < niter and not converged and not failed:
        k = k+1
        try:
            Cnew = EFAUpdateRotation(M, C, D, force_pos)
        except np.linalg.linalg.LinAlgError:
           failed = True

        dck = np.sum(np.abs(Cnew - C))

        dc.append(dck)

        C = Cnew

        if dck < tol:
            converged = True

    return C, failed, converged, dc, k

def EFAUpdateRotation(M,C,D, force_pos):
    S = np.dot(D, np.linalg.pinv(np.transpose(M*C)))

    Cnew = np.transpose(np.dot(np.linalg.pinv(S), D))

    for i, fp in enumerate(force_pos):
        if fp:
            Cnew[Cnew[:,i] < 0,i] = 0

    csum = np.sum(M*Cnew, axis = 0)

    if (int(np.__version__.split('.')[0]) > 1 or int(np.__version__.split('.')[0]) == 1
        and int(np.__version__.split('.')[1])>=10):
        Cnew = Cnew/np.broadcast_to(csum, Cnew.shape) #normalizes by the sum of each column
    else:
        norm = np.array([csum for i in range(Cnew.shape[0])])

        Cnew = Cnew/norm #normalizes by the sum of each column

    return Cnew

def EFAFirstRotation(M,C,D):
    #Have to run an initial rotation without forcing C>=0 or things typically fail to converge (usually the SVD fails)
    S = np.dot(D, np.linalg.pinv(np.transpose(M*C)))

    Cnew = np.transpose(np.dot(np.linalg.pinv(S), D))

    csum = np.sum(M*Cnew, axis = 0)
    if (int(np.__version__.split('.')[0]) > 1 or int(np.__version__.split('.')[0]) == 1
        and int(np.__version__.split('.')[1])>=10):
        Cnew = Cnew/np.broadcast_to(csum, Cnew.shape) #normalizes by the sum of each column
    else:
        norm = np.array([csum for i in range(Cnew.shape[0])])

        Cnew = Cnew/norm #normalizes by the sum of each column

    return Cnew

def initIterativeEFA(M, num_sv, D, C, converged, V_bar):

    #Set a variable to test whether the rotation fails for a numerical reason
    failed = False

    #Do an initial rotation
    try:
        C = EFAFirstRotation(M, C, D)
    except np.linalg.linalg.LinAlgError:
        failed = True

    return failed, C, None

def initExplicitEFA(M, num_sv, D, C, converged, V_bar):

    T = np.ones((num_sv, num_sv))

    failed = False

    return failed, None, T

def initHybridEFA(M, num_sv, D, C, converged, V_bar):
    failed = False

    if not converged:
        failed, temp, T = initExplicitEFA(M, num_sv, D, C, converged, V_bar)
        C, failed, temp1, temp2, temp3 = runExplicitEFARotation(M, None, None, None, V_bar, T, None, None, None)

    return failed, C, None

def run_full_efa(series, ranges, profile_type='sub', framei=None, framef=None,
    method='Hybrid', niter=1000, tol=1e-12, norm=True, force_positive=None,
    previous_results=None):
    """
    Runs evolving factor analysis (EFA) on the input series to deconvolve
    overlapping elution peaks in the data.

    Parameters
    ----------
    series: list or :class:`bioxtasraw.SECM.SECM`
        The input series to be deconvolved. It should either be a list
        of individual scattering profiles (:class:`bioxtasraw.SASM.SASM`) or
        a single series object (:class:`bioxtasraw.SECM.SECM`).
    ranges: iterable
        A list, :class:`numpy.array`, or other iterable of the EFA ranges,
        which each item is the range of a given component, and contains two
        integers, the first is start of that component range the second the
        end of the component range. Must be a type that can be cast as a
        numpy array. Should be relative to the full range of the series,
        even if framei and framef are provided.
    profile_type: {'unsub', 'sub', 'baseline'} str, optional
        Only used if a :class:`bioxtasraw.SECM.SECM` is provided for the series
        argument. Determines which type of profile to use from the series
        for the EFA. Unsubtracted profiles - 'unsub', subtracted profiles -
        'sub', baseline corrected profiles - 'baseline'.
    framei: int, optional
        The initial frame in the series to use for EFA. If not provided,
        it defaults to the first frame in the series.
    framef: int, optional
        The final frame in the series to use for EFA. If not provided, it
        defaults to the last frame in the series.
    method: {'Hybrid', 'Iterative', 'Explicit'} str, optional
        Sets the method used for the EFA rotation step as either 'Hybrid',
        'Iterative', or 'Explicit'.
    niter: int, optional
        The maximum number of iterations to use for the rotation in either
        hybrid or iterative mode. Defaults to 1000. Can be increased if
        EFA fails to converge.
    tol: float, optional
        The tolerance used as the convergence criteria for the EFA rotation
        in hybrid or iterative mode. Defaults to 1e-12. Can be decreased
        if EFA fails to converge.
    norm: bool, optional
        Whether error normalized intensity should be used for EFA. Defaults
        to True. Recommended to not change this.
    force_positive: list, optional
        Whether EFA ranges should be constrained to force positive. By default
        all ranges are forced positive. If provided, it should be a list of
        bool values with a length equal to the number of EFA ranges. Each
        list item determines whether to force positive the range defined by the
        same index in the ranges parameter.
    previous_results: list, optional
        This list contains the previous results of EFA, if any. This is used
        to improve the starting guess. The first entry in the list is a boolean
        corresponding to whether the previous results converged, and the second
        is a dictionary of the previous results, corresponding to the
        rotation_data dictionary returned by this function. Defaults to None,
        which should be used if no previous results are available.

    Returns
    -------
    efa_profiles: list
        A list of profiles (:class:`bioxtasraw.SASM.SASM`) determined by EFA.
        If EFA converged, the profile at each list index was determined for the
        corresponding range in the ranges input parameter. If EFA failed to
        converge an empty list is returned.
    converged: bool
        True if EFA converged, otherwise False.
    conv_data: dict
        A dictionary containing information about the convergence. Keys are
        'steps' - A list containing the value of the convergence criteria at
        each iteration, if available; 'iterations' - The number of iterations
        carried out during the rotation, if available; 'final_step' - The
        value of the convergence criteria in the final iteration step, if
        available; 'options' - A dictionary containing the input convergence
        options; 'failed' - A bool indicating if convergence failed.
    rotation_data: dict
        A dictionary containing the rotation results, if available. If the
        rotation failed to converge, the dictionary is empty. Keys are:
        'C' - Concentration data. A numpy array where the first axis is
        concentration as a function of frame and the second axis is component
        number. 'chisq' - Mean error weighted chi squared data. A numpy array
        of chi squared vs. frame number. 'int' - Scattering intensity. A numpy
        array where the first axis is intensity and the second axis is component
        number. ' err' - Scattering intensity uncertainty. A numpy array where
        the first axis is intensity and the second axis is component number.
        'M' - The EFA M rotation matrix.

    Raises
    ------
    SASExceptions.EFAError
        If initial SVD cannot be carried out.
    """

    if force_positive is None:
        force_positive = [True for i in range(len(ranges))]

    if framei is None:
            framei = 0
    if framef is None:
        if isinstance(series, SECM.SECM):
            framef = len(series.getAllSASMs())-1
        else:
            framef = len(series)-1

    ranges = copy.deepcopy(ranges)
    for efa_range in ranges:
        efa_range[0] = efa_range[0] - framei
        efa_range[1] = efa_range[1] - framei

    if isinstance(series, SECM.SECM):
        sasm_list = series.getSASMList(framei, framef, profile_type)
        filename = os.path.splitext(series.getParameter('filename'))[0]
    else:
        sasm_list = series[framei:framef+1]
        names = [os.path.basename(sasm.getParameter('filename')) for sasm in series]
        filename = os.path.commonprefix(names).rstrip('_')
        if filename == '':
            filename =  os.path.splitext(os.path.basename(series[0].getParameter('filename')))[0]

    if not isinstance(ranges, np.ndarray):
        ranges = np.array(ranges)

    (svd_U, svd_s, svd_V, svd_U_autocor, svd_V_autocor, intensity, err, svd_a,
        success) = SVDonSASMs(sasm_list, do_binning=False, do_autocorr=False)

    converged, conv_data, rotation_data = runRotation(svd_a, intensity,
        err, ranges, force_positive, svd_V, previous_results=previous_results,
        method=method, niter=niter, tol=tol)

    efa_profiles = []

    q = copy.deepcopy(sasm_list[0].getQ())

    if converged:
        for i in range(len(ranges)):
            intensity = rotation_data['int'][:,i]

            err = rotation_data['err'][:,i]

            sasm = SASM.SASM(intensity, q, err, {},
                copy.deepcopy(sasm_list[0].getQErr()))

            sasm.setParameter('filename', filename+'_%i' %(i))

            history_dict = {}

            history_dict['input_filename'] = filename
            history_dict['start_index'] = str(framei)
            history_dict['end_index'] = str(framef)
            history_dict['component_number'] = str(i)

            points = ranges[i]
            history_dict['component_range'] = '[%i, %i]' %(points[0], points[1])

            history = sasm.getParameter('history')
            history['EFA'] = history_dict

            efa_profiles.append(sasm)

        if isinstance(series, SECM.SECM):
            analysis_dict = series.getParameter('analysis')

            efa_dict = {}

            if profile_type == 'unsub':
                profile_data = 'Unsubtracted'
            elif profile_type == 'sub':
                profile_data = 'Subtracted'
            elif profile_type == 'baseline':
                profile_data = 'Baseline Corrected'

            efa_dict['fstart'] = str(framei)
            efa_dict['fend'] = str(framef)
            efa_dict['profile'] = profile_data
            efa_dict['nsvs'] = str(len(ranges))
            efa_dict['ranges'] = ranges
            efa_dict['iter_limit'] = str(niter)
            efa_dict['tolerance'] = str(tol)
            efa_dict['method'] = method

            analysis_dict['efa'] = efa_dict

            series.setParameter('analysis', analysis_dict)

    return efa_profiles, converged, conv_data, rotation_data

def validateBuffer(sasms, frame_idx, intensity, sim_test, sim_cor, sim_thresh,
    fast):
    median = np.median(intensity)
    median_i_idx = (np.absolute(intensity-median)).argmin()

    ref_sasm = sasms[median_i_idx].copy_no_metadata()
    buffer_sasms = [sasm.copy_no_metadata() for sasm in sasms]
    qi, qf = ref_sasm.getQrange()

    #Test for frame correlation
    if len(sasms) > 1:
        intI_test = stats.spearmanr(intensity, frame_idx)
    else:
        intI_test = [1,1]

    intI_valid = intI_test[1]>0.05

    if fast and not intI_valid:
        return False, {}, {}, {}

    win_len = len(intensity)//2
    if win_len % 2 == 0:
        win_len = win_len+1
    win_len = min(51, win_len)

    order = min(5, win_len-1)

    if len(sasms) > 1:
        smoothed_intI = smooth_data(intensity, window_length=win_len,
            order=order)
        smoothed_intI_test = stats.spearmanr(smoothed_intI, frame_idx)
    else:
        smoothed_intI_test = [1,1]

    smoothed_intI_valid = smoothed_intI_test[1]>0.01

    intI_results = {'intI_r'    : intI_test[0],
        'intI_pval'             : intI_test[1],
        'intI_valid'            : intI_valid,
        'smoothed_intI_r'       : smoothed_intI_test[0],
        'smoothed_intI_pval'    : smoothed_intI_test[1],
        'smoothed_intI_valid'   : smoothed_intI_valid,
        }

    if fast and not smoothed_intI_valid:
        return False, {}, {}, intI_results


    #Test for regional frame similarity
    if len(sasms) > 1:
        if qf-qi>200:
            ref_sasm.setQrange((qi, qi+100))
            for sasm in buffer_sasms:
                sasm.setQrange((qi, qi+100))
            low_q_similar, low_q_outliers = run_similarity_test(ref_sasm,
                buffer_sasms, sim_test, sim_cor, sim_thresh)

            if fast and not low_q_similar:
                ref_sasm.setQrange((qi, qf))
                for sasm in buffer_sasms:
                    sasm.setQrange((qi, qf))
                return False, {}, {}, intI_results

            ref_sasm.setQrange((qf-100, qf))
            for sasm in buffer_sasms:
                sasm.setQrange((qf-100, qf))
            high_q_similar, high_q_outliers = run_similarity_test(ref_sasm,
                buffer_sasms, sim_test, sim_cor, sim_thresh)

            ref_sasm.setQrange((qi, qf))
            for sasm in buffer_sasms:
                sasm.setQrange((qi, qf))

            if fast and not high_q_similar:
                return False, {}, {}, intI_results

        else:
            low_q_similar = True
            high_q_similar = True
            low_q_outliers = []
            high_q_outliers = []
    else:
        low_q_similar = True
        high_q_similar = True
        low_q_outliers = []
        high_q_outliers = []


    #Test for more than one significant singular value
    if len(sasms) > 1:
        svd_results = significantSingularValues(sasms)

        if fast and not svd_results['svals']==1:
            return False, {}, svd_results, intI_results
    else:
        svd_results = {'svals': 1}


    #Test for all frame similarity
    if len(sasms) > 1:
        all_similar, all_outliers = run_similarity_test(ref_sasm,
            buffer_sasms, sim_test, sim_cor, sim_thresh)
    else:
        all_similar = True
        all_outliers = []

    similarity_results = {'all_similar'     : all_similar,
        'low_q_similar'     : low_q_similar,
        'high_q_similar'    : high_q_similar,
        'median_idx'        : median_i_idx,
        'all_outliers'      : all_outliers,
        'low_q_outliers'    : low_q_outliers,
        'high_q_outliers'   : high_q_outliers,
        }

    similar_valid = (all_similar and low_q_similar and high_q_similar)

    valid = similar_valid and svd_results['svals']==1 and intI_valid and smoothed_intI_valid

    return valid, similarity_results, svd_results, intI_results

def run_similarity_test(ref_sasm, sasm_list, sim_test, sim_cor, sim_thresh):
    if sim_test == 'CorMap':
        pvals, corrected_pvals, failed_comparisons = SASProc.run_cormap_ref(sasm_list,
            ref_sasm, sim_cor)

    if np.any(pvals<sim_thresh):
        similar = False
    else:
        similar = True

    return similar, np.argwhere(pvals<sim_thresh).flatten()

def significantSingularValues(sasms):
    """
    Calculates number of significant singular values.

    Returns both SVD results and number of significant singular values.
    """

    (svd_U, svd_s, svd_V, svd_U_autocor, svd_V_autocor, i, err, svd_a,
        continue_svd_analysis) = SVDonSASMs(sasms, do_binning=False)

    if continue_svd_analysis:
        svals = findSignificantSingularValues(svd_s, svd_U_autocor, svd_V_autocor)

        if svals <= 0:
            svals = 1 #Assume algorithm failure and set to 1 to continue other validation steps

        svd_results = {'svals'  : svals,
            'U'             : svd_U,
            'V'             : svd_V,
            'u_autocor'     : svd_U_autocor,
            'v_autocor'     : svd_V_autocor,
            }

    else:
        svd_results = {'svals': 1} #Default to let other analysis continue in validation steps

    return svd_results

def prepareSASMsforSVD(sasms, err_norm=True, do_binning=True, bin_to=100):
    if do_binning:
        rebinned_sasms = []
        for sasm in sasms:
            rb_fac = int(np.floor(len(sasm.getQ())/float(bin_to)))

            if rb_fac > 1:
                rb_sasm = SASProc.rebin(sasm, rb_fac, copy_params=False)
            else:
                rb_sasm = sasm

            rebinned_sasms.append(rb_sasm)

    else:
        rebinned_sasms = sasms

    i = np.array([sasm.getI() for sasm in rebinned_sasms])
    err = np.array([sasm.getErr() for sasm in rebinned_sasms])

    i = i.T #Because of how numpy does the SVD, to get U to be the scattering vectors and V to be the other, we have to transpose
    err = err.T

    err_mean = np.mean(err, axis = 1)
    if int(np.__version__.split('.')[0]) >= 1 and int(np.__version__.split('.')[1])>=10:
        err_avg = np.broadcast_to(err_mean.reshape(err_mean.size,1), err.shape)
    else:
        err_avg = np.array([err_mean for k in range(i.shape[1])]).T

    if err_norm:
        svd_a = i/err_avg
    else:
        svd_a = i

    q = rebinned_sasms[0].getQ()

    return svd_a, i, err, q

def doSVDonSASMs(svd_a, do_autocorr=True):
    if np.all(np.isfinite(svd_a)):
        try:
            svd_U, svd_s, svd_Vt = np.linalg.svd(svd_a, full_matrices = True)
            success = True
        except Exception:
            success = False

        if success and do_autocorr:
            svd_V = svd_Vt.T
            svd_U_autocor = np.abs(np.array([np.correlate(svd_U[:,k],
                svd_U[:,k], mode = 'full')[-svd_U.shape[0]+1] for k in range(svd_U.shape[1])]))
            svd_V_autocor = np.abs(np.array([np.correlate(svd_V[:,k],
                svd_V[:,k], mode = 'full')[-svd_V.shape[0]+1] for k in range(svd_V.shape[1])]))

        elif success:
            svd_V = svd_Vt.T
            svd_U_autocor = []
            svd_V_autocor = []
        else:
            svd_U = []
            svd_s = []
            svd_V = []
            svd_U_autocor = []
            svd_V_autocor = []
    else:
        svd_U = []
        svd_s = []
        svd_V = []
        svd_U_autocor = []
        svd_V_autocor = []
        success = False

    return svd_U, svd_s, svd_V, svd_U_autocor, svd_V_autocor, success


def SVDonSASMs(sasms, err_norm=True, do_binning=True, bin_to=100, do_autocorr=True):
    svd_a, i, err, q = prepareSASMsforSVD(sasms, err_norm, do_binning, bin_to)

    svd_U, svd_s, svd_V, svd_U_autocor, svd_V_autocor, success = doSVDonSASMs(svd_a,
        do_autocorr)

    return svd_U, svd_s, svd_V, svd_U_autocor, svd_V_autocor, i, err, svd_a, success

def findSignificantSingularValues(svd_s, svd_U_autocor, svd_V_autocor):
     #Attempts to figure out the significant number of singular values
        point1 = 0
        point2 = 0
        point3 = 0

        i = 0
        ratio_found = False

        while i < svd_s.shape[0]-1 and not ratio_found:
            ratio = svd_s/svd_s[i]

            if ratio[i+1] > 0.75:
                point1 = i
                ratio_found = True

            i = i +1

        if not ratio_found:
            point1 = svd_s.shape[0]

        u_points = np.where(svd_U_autocor > 0.6)[0]
        index_list = []

        if len(u_points) > 0:

            for i in range(1,len(u_points)):
                if u_points[i-1] +1 == u_points[i]:
                    index_list.append(i)

            point2 = len(index_list)

            if point2 == 0:
                if u_points[0] == 0:
                    point2 =1
            else:
                point2 = point2 + 1

        v_points = np.where(svd_V_autocor > 0.6)[0]
        index_list = []

        if len(v_points) > 0:

            for i in range(1,len(v_points)):
                if v_points[i-1] +1 == v_points[i]:
                    index_list.append(i)

            point3 = len(index_list)

            if point3 == 0:
                if v_points[0] == 0:
                    point3 =1
            else:
                point3 = point3 + 1

        plist = [point1, point2, point3]

        mode, count = stats.mode(plist)

        try:
            mode = mode[0]
            count = count[0]
        except IndexError:
            pass

        if count > 1:
            svals = mode

        elif np.mean(plist) > np.std(plist):
            svals = int(round(np.mean(plist)))

        else:
            svals = 0

        return svals


def findBufferRange(buffer_sasms, intensity, avg_window, sim_test, sim_cor,
    sim_thresh):
    region_start = None
    region_end = None

    win_len = len(intensity)//2
    if win_len % 2 == 0:
        win_len = win_len+1
    win_len = min(51, win_len)

    order = min(5, win_len-1)

    smoothed_data = smooth_data(intensity, window_length=win_len,
        order=order)

    norm_sdata = smoothed_data/np.max(smoothed_data)
    peaks, peak_params = find_peaks(norm_sdata, height=0.4)

    avg_window = avg_window
    min_window_width = min(max(10, int(round(avg_window/2.))), len(intensity)//2)
    if min_window_width < 2:
        min_window_width = 2

    if len(peaks) == 0:
        # Searches entire series

        start_window_size =  min_window_width
        start_point = 0
        end_point = len(intensity) - 1 - start_window_size

        use_peak_search = False
        search_full_length = True

        peak_pos = []

    else:
        use_peak_search = True

        max_peak_idx = np.argmax(peak_params['peak_heights'])
        main_peak_width = int(round(peak_params['widths'][max_peak_idx]))

        max_peak_prom = peak_params['prominences'][max_peak_idx]
        prom_thres = 0.05

        peak_idx = []
        peak_pos = []

        for j in range(len(peak_params['peak_heights'])):
            if peak_params['prominences'][j] > max_peak_prom*prom_thres:
                peak_idx.append(j)
                peak_pos.append(peaks[j])
                peak_pos.append(peak_params['right_ips'][j])
                peak_pos.append(peak_params['left_ips'][j])

        start_window_size = max(main_peak_width*2, min_window_width)
        start_window_size = min(start_window_size, len(intensity)//2)

        start_point = 0

        if start_window_size == min_window_width:
            end_point = len(intensity) - 1 - start_window_size
            search_full_length = True

        else:
            #Start search to the left from edge of leftmost peak and go to start
            end_point = int(round(peak_params['left_ips'][peak_idx[0]]))

            if end_point + start_window_size > len(intensity) - 1 - start_window_size:
                end_point = len(intensity) - 1 - start_window_size

            search_full_length = False

    #Initial search
    failed, region_start, region_end = inner_find_buffer_range(intensity,
        buffer_sasms, start_point, end_point, start_window_size,
        min_window_width, peak_pos, sim_test, sim_cor, sim_thresh, True)

    if use_peak_search and not search_full_length and failed:
        #Start search to the right from edge of rightmost peak and go to end
        start_point = int(round(peak_params['right_ips'][peak_idx[-1]]))
        end_point = len(intensity) - 1 - start_window_size

        if start_point + start_window_size > len(intensity) - 1 - start_window_size:
            failed = True

        else:
            failed, region_start, region_end = inner_find_buffer_range(intensity,
                buffer_sasms, start_point, end_point, start_window_size,
                min_window_width, peak_pos, sim_test, sim_cor, sim_thresh, False)

    if use_peak_search and not search_full_length and failed:
        #Start search to the left from edge of main peak and go to the left edge of the first peak
        start_point = int(round(peak_params['left_ips'][peak_idx[0]]))
        end_point = int(round(peak_params['left_ips'][max_peak_idx]))

        if start_point + start_window_size > len(intensity) - 1 - start_window_size:
            failed = True

        else:
            if end_point + start_window_size > len(intensity) - 1 - start_window_size:
                end_point = len(intensity) - 1 - start_window_size

            if end_point != start_point:
                failed, region_start, region_end = inner_find_buffer_range(intensity,
                    buffer_sasms, start_point, end_point, start_window_size,
                    min_window_width, peak_pos, sim_test, sim_cor, sim_thresh, True)

            else:
                failed = True

    if use_peak_search and not search_full_length and failed:
        #Start search to the right from edge of main peak and go to the rightmost edge of the rightmost peak
        start_point = int(round(peak_params['right_ips'][max_peak_idx]))
        end_point = int(round(peak_params['right_ips'][peak_idx[-1]]))

        if start_point + start_window_size > len(intensity) - 1 - start_window_size:
            failed = True

        else:
            if end_point + start_window_size > len(intensity) - 1 - start_window_size:
                end_point = len(intensity) - 1 - start_window_size

            if end_point != start_point:
                failed, region_start, region_end = inner_find_buffer_range(intensity,
                    buffer_sasms, start_point, end_point, start_window_size,
                    min_window_width, peak_pos, sim_test, sim_cor, sim_thresh, False)
            else:
                failed = True

    success = not failed

    return success, region_start, region_end

def inner_find_buffer_range(intensity, buffer_sasms, start_point, end_point,
    start_window_size, min_window_width, peaks, sim_test, sim_cor, sim_thresh,
    flip_regions):

    found_region = False
    failed = False

    window_size = start_window_size

    region_start = None
    region_end = None

    while not found_region and not failed:
        step_size = max(1, int(round(window_size/4.)))
        region_starts = list(range(start_point, end_point, step_size))

        if flip_regions:
            region_starts = region_starts[::-1]

        for idx in region_starts:
            region_sasms = buffer_sasms[idx:idx+window_size+1]
            frame_idx = list(range(idx, idx+window_size+1))
            region_intensity = intensity[idx:idx+window_size+1]

            if len(peaks) == 0 or np.all([peak not in frame_idx for peak in peaks]):
                found_region, similarity_results, svd_results, intI_results = validateBuffer(region_sasms,
                    frame_idx, region_intensity, sim_test, sim_cor, sim_thresh, True)

            else:
                found_region = False

            if found_region:
                region_start = idx
                region_end = idx+window_size
                break

        window_size = int(round(window_size/2.))

        if window_size < min_window_width and not found_region:
            failed = True

    return failed, region_start, region_end

def validateSample(sub_sasms, frame_idx, intensity, rg, vcmw, vpmw,
    sim_test, sim_cor, sim_thresh, fast):
    max_i_idx = np.argmax(intensity)

    ref_sasm = sub_sasms[max_i_idx].copy_no_metadata()
    superimpose_sub_sasms = [sasm.copy_no_metadata() for sasm in sub_sasms]
    SASProc.superimpose(ref_sasm, superimpose_sub_sasms, 'Scale')
    qi, qf = ref_sasm.getQrange()

    if np.any(rg==-1):
        param_range_valid = False
        param_bad_frames = np.argwhere(rg==-1).flatten()
    else:
        param_range_valid = True
        param_bad_frames = []

    if fast and not param_range_valid:
        return False, {}, {}, {}, {}

    if len(sub_sasms) > 1:
        rg_test = stats.spearmanr(rg, frame_idx)
    else:
        rg_test = [1,1]

    if not np.isnan(rg_test[1]):
        rg_valid = rg_test[1]>0.05
    else:
        rg_valid = False

    if fast and not rg_valid:
        return False, {}, {}, {}, {}

    if len(sub_sasms) > 1:
        vcmw_test = stats.spearmanr(vcmw, frame_idx)
    else:
        vcmw_test = [1,1]

    if not np.isnan(vcmw_test[1]):
        vcmw_valid = vcmw_test[1]>0.05
    else:
        vcmw_valid = False

    if fast and not vcmw_valid:
        return False, {}, {}, {}, {}

    if len(sub_sasms) > 1:
        vpmw_test = stats.spearmanr(vpmw, frame_idx)
    else:
        vpmw_test = [1,1]

    if not np.isnan(vpmw_test[1]):
        vpmw_valid = vpmw_test[1]>0.05
    else:
        vpmw_valid = False

    param_valid = (param_range_valid and rg_valid and vcmw_valid and vpmw_valid)

    param_results = {'rg_r' : rg_test[0],
        'rg_pval'           : rg_test[1],
        'rg_valid'          : rg_valid,
        'vcmw_r'            : vcmw_test[0],
        'vcmw_pval'         : vcmw_test[1],
        'vcmw_valid'        : vcmw_valid,
        'vpmw_r'            : vpmw_test[0],
        'vpmw_pval'         : vpmw_test[1],
        'vpmw_valid'        : vpmw_valid,
        'param_range_valid' : param_range_valid,
        'param_bad_frames'  : param_bad_frames,
        'param_valid'       : param_valid,
        }

    if fast and not param_valid:
        return False, {}, param_results, {}, {}


    #Test for regional frame similarity
    if len(sub_sasms) > 1:
        if qf-qi>200:
            ref_sasm.setQrange((qi, qi+100))
            for sasm in superimpose_sub_sasms:
                sasm.setQrange((qi, qi+100))
            low_q_similar, low_q_outliers = run_similarity_test(ref_sasm,
                superimpose_sub_sasms, sim_test, sim_cor, sim_thresh)

            if fast and not low_q_similar:
                ref_sasm.setQrange((qi, qf))
                for sasm in superimpose_sub_sasms:
                    sasm.setQrange((qi, qf))
                return False, {}, param_results, {}, {}

            ref_sasm.setQrange((qf-100, qf))
            for sasm in superimpose_sub_sasms:
                sasm.setQrange((qf-100, qf))

            high_q_similar, high_q_outliers = run_similarity_test(ref_sasm,
                superimpose_sub_sasms, sim_test, sim_cor, sim_thresh)

            ref_sasm.setQrange((qi, qf))
            for sasm in superimpose_sub_sasms:
                sasm.setQrange((qi, qf))

            if fast and not high_q_similar:
                return False, {}, param_results, {}, {}

        else:
            low_q_similar = True
            high_q_similar = True
            low_q_outliers = []
            high_q_outliers = []
    else:
        low_q_similar = True
        high_q_similar = True
        low_q_outliers = []
        high_q_outliers = []


    #Test for more than one significant singular value
    if len(sub_sasms) > 1:
        svd_results = significantSingularValues(sub_sasms)
    else:
        svd_results = {'svals': 1}

    if fast and not svd_results['svals']==1:
        return False, {}, param_results, svd_results, {}


    # Test whether averaging all selected frames is helping signal to noise,
    # or if inclusion of some are hurting because they're too noisy

    if len(sub_sasms) > 1:
        sort_idx = np.argsort(intensity)[::-1]
        old_s_to_n = 0
        sn_valid = True
        i = 0

        while sn_valid and i < len(sort_idx):
            idxs = sort_idx[:i+1]
            avg_list = [sub_sasms[idx] for idx in idxs]

            average_sasm = SASProc.average(avg_list, forced=True,
                copy_params=False)
            avg_i = average_sasm.getI()
            avg_err = average_sasm.getErr()

            s_to_n = np.abs(avg_i/avg_err).mean()

            if s_to_n >= old_s_to_n:
                old_s_to_n = s_to_n
                i = i+1
            else:
                sn_valid = False
    else:
        sort_idx = []
        i = 0
        sn_valid = True

    sn_results = {'low_sn'  : np.sort(sort_idx[i:]),
        'sn_valid'  : sn_valid,
        }

    if fast and not sn_valid:
        return False, {}, param_results, svd_results, sn_results


    #Test for all frame similarity
    if len(sub_sasms) > 1:
        all_similar, all_outliers = run_similarity_test(ref_sasm,
            superimpose_sub_sasms, sim_test, sim_cor, sim_thresh)
    else:
        all_similar = True
        all_outliers = []

    similarity_results = {'all_similar'     : all_similar,
        'low_q_similar'     : low_q_similar,
        'high_q_similar'    : high_q_similar,
        'max_idx'           : max_i_idx,
        'all_outliers'      : all_outliers,
        'low_q_outliers'    : low_q_outliers,
        'high_q_outliers'   : high_q_outliers,
        }

    similar_valid = (all_similar and low_q_similar and high_q_similar)

    valid = (similar_valid and param_valid and svd_results['svals']==1 and sn_valid)

    return valid, similarity_results, param_results, svd_results, sn_results

def findSampleRange(sub_sasms, intensity, rg, vcmw, vpmw, avg_window, sim_test,
    sim_cor, sim_thresh):
    win_len = len(intensity)//2
    if win_len % 2 == 0:
        win_len = win_len+1
    win_len = min(51, win_len)

    order = min(5, win_len-1)

    smoothed_data = smooth_data(intensity, window_length=win_len,
        order=order)

    norm_sdata = smoothed_data/np.max(smoothed_data)
    peaks, peak_params = find_peaks(norm_sdata)

    if len(peaks) == 0:
        return False, None, None

    max_peak_idx = np.argmax(peak_params['peak_heights'])

    main_peak_pos = peaks[max_peak_idx]
    main_peak_width = int(round(peak_params['widths'][max_peak_idx]))

    avg_window = avg_window
    min_window_width = max(3, int(round(avg_window/2.)))
    search_region = main_peak_width*2

    window_size = main_peak_width
    start_point = main_peak_pos - int(round(search_region/2.))

    found_region = False
    failed = False

    while not found_region and not failed:
        step_size = max(1, int(round(window_size/8.)))

        end_point = main_peak_pos + int(round(search_region/2.)) - window_size
        num_pts_gen = int(round((end_point-start_point)/step_size/2.))

        mid_point = main_peak_pos-int(round(window_size/2.))

        region_starts = []

        for i in range(num_pts_gen+1):
            if i == 0:
                if mid_point > 0:
                    region_starts.append(mid_point)
            else:
                if (mid_point+ i*step_size + window_size < len(intensity)
                    and mid_point+ i*step_size> 0):
                    region_starts.append(mid_point+i*step_size)
                if mid_point - i*step_size > 0:
                    region_starts.append(mid_point-i*step_size)

        for idx in region_starts:
            region_sasms = sub_sasms[idx:idx+window_size+1]
            region_intensity = intensity[idx:idx+window_size+1]
            frame_idx = list(range(idx, idx+window_size+1))
            rg_region = rg[idx:idx+window_size+1]
            vcmw_region = vcmw[idx:idx+window_size+1]
            vpmw_region = vpmw[idx:idx+window_size+1]
            # valid, similarity_results, param_results, svd_results, sn_results = self._validateSample(region_sasms,
            #     , True)
            (valid, similarity_results, param_results, svd_results,
                sn_results) = validateSample(region_sasms, frame_idx,
                region_intensity, rg_region, vcmw_region, vpmw_region,
                sim_test, sim_cor, sim_thresh, True)
            found_region = valid

            if found_region:
                region_start = idx
                region_end = idx+window_size
                break

        window_size = int(round(window_size/2.))

        if window_size < min_window_width and not found_region:
            failed = True

    success = not failed

    if not success:
        region_start = -1
        region_end = -1

    return success, region_start, region_end

def validateBaseline(sasms, frame_idx, intensity, bl_type, ref_sasms, start,
    sim_test, sim_cor, sim_thresh, fast):
    other_results = {}

    if bl_type == 'Integral':
        valid, similarity_results, svd_results, intI_results = validateBuffer(sasms,
            frame_idx, intensity, sim_test, sim_cor, sim_thresh,
    fast)

        if fast and not valid:
            return valid, similarity_results, svd_results, intI_results, other_results
    else:
        valid = True
        similarity_results = {}
        svd_results = {}
        intI_results = {}


    if bl_type == 'Integral':
        # if start and frames[0] != 0:
        #     full_frames = range(0, frames[-1]+1)
        #     full_sasms = [all_sasms[i] for i in full_frames]

        #     f_valid, f_similarity_results, f_svd_results, f_intI_results = self._validateBuffer(full_sasms,
        #     full_frames, True)

        #     valid = valid and f_valid

        #     other_results['range_valid'] = f_valid

        # elif not start and frames[-1] != len(all_sasms)-1:
        #     full_frames = range(frames[0], len(all_sasms))
        #     full_sasms = [all_sasms[i] for i in full_frames]

        #     f_valid, f_similarity_results, f_svd_results, f_intI_results = self._validateBuffer(full_sasms,
        #     full_frames, True)

        #     valid = valid and f_valid

        #     other_results['range_valid'] = f_valid

        # else:
        #     other_results['range_valid'] = True

        # if fast and not valid:
        #     return valid, similarity_results, svd_results, intI_results, other_results

        if not start:
            start_avg_sasm = SASProc.average(ref_sasms, forced=True, copy_params=False)
            end_avg_sasm = SASProc.average(sasms, forced=True, copy_params=False)

            diff_sasm = SASProc.subtract(end_avg_sasm, start_avg_sasm, forced=True,
                copy_params=False)

            diff_i = diff_sasm.getI()
            end_err = end_avg_sasm.getErr()

            neg_idx = diff_i<0

            outlier_idx = np.abs(diff_i[neg_idx]) > 4*np.abs(end_err[neg_idx])

            if np.any(outlier_idx):
                other_results['zero_valid'] = False

            else:
                other_results['zero_valid'] = True

            other_results['zero_outliers'] = outlier_idx
            other_results['zero_q'] = diff_sasm.getQ()

            valid = valid and other_results['zero_valid']

        if fast and not valid:
            return valid, similarity_results, svd_results, intI_results, other_results

    elif bl_type == 'Linear':
        if not start:
            start_ints = np.array([sasm.getI() for sasm in ref_sasms])
            end_ints = np.array([sasm.getI() for sasm in sasms])

            start_ints_err = np.array([sasm.getErr() for sasm in ref_sasms])
            end_ints_err = np.array([sasm.getErr() for sasm in sasms])

            start_fit_results = []
            end_fit_results = []

            j = 0
            fit_valid = True

            while fit_valid and j < end_ints.shape[1]-1:

                s_a, s_b, s_cov_a, s_cov_b = weighted_lin_reg(np.arange(start_ints.shape[0]),
                    start_ints[:, j], start_ints_err[:, j])
                start_fit_results.append((s_a, s_b, s_cov_a, s_cov_b))

                e_a, e_b, e_cov_a, e_cov_b = weighted_lin_reg(np.arange(end_ints.shape[0]),
                    end_ints[:, j], end_ints_err[:, j])
                end_fit_results.append((e_a, e_b, e_cov_a, e_cov_b))


                if s_a != -1 and e_a != -1:
                    a_diff = abs(s_a - e_a)
                    b_diff = abs(s_b - e_b)

                    a_delta = 2*s_cov_a + 2*e_cov_a
                    b_delta = 2*s_cov_b + 2*e_cov_b

                    if a_diff > a_delta or b_diff > b_delta:
                        fit_valid = False

                j = j + 1

            other_results['fit_valid'] = fit_valid
            # other_results['start_fits'] = start_fit_results
            # other_results['end_fits'] = end_fit_results

            valid = valid and other_results['fit_valid']

        if fast and not valid:
            return valid, similarity_results, svd_results, intI_results, other_results

    return valid, similarity_results, svd_results, intI_results, other_results

def findBaselineRange(sub_sasms, intensity, bl_type, avg_window, start_region,
    sim_test, sim_cor, sim_thresh):
    region1_start = -1
    region1_end = -1
    region2_start = -1
    region2_end = -1

    win_len = len(intensity)//2
    if win_len % 2 == 0:
        win_len = win_len+1
    win_len = min(51, win_len)

    order = min(5, win_len-1)

    smoothed_data = smooth_data(intensity, window_length=win_len,
        order=order)

    norm_sdata = smoothed_data/np.max(smoothed_data)
    peaks, peak_params = find_peaks(norm_sdata, height=0.4)

    min_window_width = max(10, int(round(avg_window/2.)))

    # Start region
    if len(peaks) == 0:
        window_size =  min_window_width
        start_point = 0
        end_point = len(intensity) - 1 - window_size
    else:
        max_peak_idx = np.argmax(peak_params['peak_heights'])
        main_peak_width = int(round(peak_params['widths'][max_peak_idx]))

        window_size = max(main_peak_width, min_window_width)
        start_point = 0

        end_point = int(round(peak_params['left_ips'][max_peak_idx]))
        if end_point + window_size > len(intensity) - 1 - window_size:
            end_point = len(intensity) - 1 - window_size

    found_region = False
    start_failed = False

    if start_region is not None:
        region_sasms = sub_sasms[start_region[0]:start_region[1]+1]
        frame_idx = np.arange(start_region[0], start_region[1]+1)
        region_intensity = intensity[start_region[0]:start_region[1]+1]

        (valid, similarity_results, svd_results, intI_results,
            other_results) = validateBaseline(region_sasms, frame_idx,
            region_intensity, bl_type, None, True, sim_test, sim_cor,
            sim_thresh, True)

        if np.all([peak not in frame_idx for peak in peaks]) and valid:
            found_region = True
            region1_start = start_region[0]
            region1_end = start_region[1]
        else:
            found_region = False


    while not found_region and not start_failed:
        step_size = max(1, int(round(window_size/4.)))

        region_starts = list(range(start_point, end_point, step_size))

        region_starts = region_starts[::-1]

        for idx in region_starts:
            region_sasms = sub_sasms[idx:idx+window_size+1]
            frame_idx = np.arange(idx, idx+window_size+1)
            region_intensity = intensity[idx:idx+window_size+1]

            (valid, similarity_results, svd_results, intI_results,
                other_results) = validateBaseline(region_sasms, frame_idx,
                region_intensity, bl_type, None, True, sim_test, sim_cor,
                sim_thresh, True)

            if np.all([peak not in frame_idx for peak in peaks]) and valid:
                found_region = True
            else:
                found_region = False

            if found_region:
                region1_start = idx
                region1_end = idx+window_size
                break

        window_size = int(round(window_size/2.))

        if window_size < min_window_width and not found_region:
            start_failed = True

    if not start_failed:
        start_sasms = sub_sasms[region1_start:region1_end+1]


    # End region
    if len(peaks) == 0:
        window_size =  min_window_width
        start_point = 0
        end_point = len(intensity) - 1 - window_size
    else:
        max_peak_idx = np.argmax(peak_params['peak_heights'])
        main_peak_width = int(round(peak_params['widths'][max_peak_idx]))

        window_size = max(main_peak_width, min_window_width)

        start_point = int(round(peak_params['left_ips'][max_peak_idx]))
        if start_point + window_size > len(intensity) - 1 - window_size:
            start_point = len(intensity) - 1 - window_size

        end_point = len(intensity) - 1 - window_size

    found_region = False
    end_failed = False

    while not found_region and not end_failed:
        step_size = max(1, int(round(window_size/4.)))

        region_starts = list(range(start_point, end_point, step_size))

        for idx in region_starts:
            region_sasms = sub_sasms[idx:idx+window_size+1]
            frame_idx = np.arange(idx, idx+window_size+1)
            region_intensity = intensity[idx:idx+window_size+1]

            if not start_failed:
                (valid, similarity_results, svd_results, intI_results,
                    other_results) = validateBaseline(region_sasms, frame_idx,
                    region_intensity, bl_type, start_sasms, False, sim_test,
                    sim_cor, sim_thresh, True)
            else:
                (valid, similarity_results, svd_results, intI_results,
                    other_results) = validateBaseline(region_sasms, frame_idx,
                    region_intensity, bl_type, None, True, sim_test, sim_cor,
                    sim_thresh, True)

            if np.all([peak not in frame_idx for peak in peaks]) and valid:
                found_region = True
            else:
                found_region = False

            if found_region:
                region2_start = idx
                region2_end = idx+window_size
                break

        window_size = int(round(window_size/2.))

        if window_size < min_window_width and not found_region:
            end_failed = True

    return (start_failed, end_failed, region1_start, region1_end, region2_start,
        region2_end)

def processBaseline(unsub_sasms, sub_sasms, r1, r2, bl_type, min_iter, max_iter,
    bl_extrap, int_type, qref, qrange, calc_threshold):
    if bl_type == 'Integral':
        fit_results = [] #Need to declare here for integral baselines which don't return fit_results

        baselines = integral_baseline(sub_sasms, r1, r2, max_iter,
            min_iter)

        bl_sasms = []

        bl_corr = []
        bl_q = copy.deepcopy(sub_sasms[0].getQ())
        bl_err = np.zeros_like(baselines[0])

        for j, sasm in enumerate(sub_sasms):
            q = copy.deepcopy(sasm.getQ())

            if j < r1[1]:
                baseline = baselines[0]
                i = copy.deepcopy(sasm.getI())
                err = copy.deepcopy(sasm.getErr())
            elif j >= r1[1] and j <= r2[0]:
                baseline = baselines[j-r1[1]]
                i = sasm.getI() - baseline
                err = sasm.getErr() * i/sasm.getI()

                newSASM = SASM.SASM(baseline, bl_q, bl_err, {})
                bl_corr.append(newSASM)
            else:
                baseline = baselines[-1]
                i = sasm.getI() - baseline
                err = sasm.getErr() * i/sasm.getI()


            parameters = copy.deepcopy(sasm.getAllParameters())

            old_history = parameters['history']

            history1 = []
            history1.append(copy.deepcopy(sasm.getParameter('filename')))

            for key in old_history:
                history1.append({key:old_history[key]})

            history = {}
            history['baseline_correction'] = {'initial_file':history1,
                'type':bl_type}

            parameters['history'] = history

            newSASM = SASM.SASM(i, q, err, parameters, copy.deepcopy(sasm.getQErr()))

            bl_sasms.append(newSASM)

    elif bl_type == 'Linear':
        fit_results = linear_baseline(sub_sasms, r1, r2)
        bl_sasms = []
        bl_corr = []

        bl_q = copy.deepcopy(sub_sasms[0].getQ())
        bl_err = np.zeros_like(sub_sasms[0].getQ())

        for j, sasm in enumerate(sub_sasms):
            q = copy.deepcopy(sasm.getQ())

            if bl_extrap:
                baseline = np.array([linear_func(j, fit[0], fit[1]) for fit in fit_results])
                i = sasm.getI() - baseline
                err = sasm.getErr() * i/sasm.getI()

                bl_newSASM = SASM.SASM(baseline, bl_q, bl_err, {})
                bl_corr.append(bl_newSASM)

            else:
                if j >= r1[0] and j <= r2[1]:
                    baseline = np.array([linear_func(j, fit[0], fit[1]) for fit in fit_results])
                    i = sasm.getI() - baseline
                    err = sasm.getErr() * i/sasm.getI()

                    bl_newSASM = SASM.SASM(baseline, bl_q, bl_err, {})
                    bl_corr.append(bl_newSASM)
                else:
                    i = copy.deepcopy(sasm.getI())
                    err = copy.deepcopy(sasm.getErr())
                    baseline = np.zeros_like(i)


            parameters = copy.deepcopy(sasm.getAllParameters())

            old_history = parameters['history']

            history1 = []
            history1.append(copy.deepcopy(sasm.getParameter('filename')))

            for key in old_history:
                history1.append({key:old_history[key]})

            history = {}
            history['baseline_correction'] = {'initial_file':history1,
                'type':bl_type}

            parameters['history'] = history

            newSASM = SASM.SASM(i, q, err, parameters, copy.deepcopy(sasm.getQErr()))

            bl_sasms.append(newSASM)


    sub_mean_i = np.array([sasm.getMeanI() for sasm in bl_sasms])
    sub_total_i = np.array([sasm.getTotalI() for sasm in bl_sasms])

    use_subtracted_sasms = []
    zeroSASM = SASM.SASM(np.zeros_like(sub_sasms[0].getQ()), sub_sasms[0].getQ(),
        sub_sasms[0].getErr(), {})
    bl_unsub_sasms = []

    for j in range(len(unsub_sasms)):
        if bl_type == 'Integral':
            if j < r1[1]:
                bkg_sasm = zeroSASM
            elif j >= r1[1] and j <= r2[0]:
                bkg_sasm = bl_corr[j-r1[1]]
            else:
                bkg_sasm = bl_corr[-1]

        elif bl_type == 'Linear':
            if bl_extrap:
                bkg_sasm = bl_corr[j]
            else:
                if j >= r1[0] and j <= r2[1]:
                    bkg_sasm = bl_corr[j-r1[0]]
                else:
                    bkg_sasm = zeroSASM

        bl_unsub_sasms.append(SASProc.subtract(unsub_sasms[j], bkg_sasm,
            forced=True, copy_params=False))

    start_frames = list(range(r1[0], r1[1]+1))
    bl_unsub_ref_sasm = SASProc.average([bl_unsub_sasms[j] for j in start_frames],
        forced=True, copy_params=False)

    if  int_type == 'total':
        ref_intensity = bl_unsub_ref_sasm.getTotalI()
    elif int_type == 'mean':
        ref_intensity = bl_unsub_ref_sasm.getMeanI()
    elif int_type == 'q_val':
        ref_intensity = bl_unsub_ref_sasm.getIofQ(qref)
    elif int_type == 'q_range':
        q1 = qrange[0]
        q2 = qrange[1]
        ref_intensity = bl_unsub_ref_sasm.getIofQRange(q1, q2)

    for sasm in bl_unsub_sasms:
        if int_type == 'total':
            sasm_intensity = sasm.getTotalI()
        elif int_type == 'mean':
            sasm_intensity = sasm.getMeanI()
        elif int_type == 'q_val':
            sasm_intensity = sasm.getIofQ(qref)
        elif int_type == 'q_range':
            sasm_intensity = sasm.getIofQRange(q1, q2)

        if abs(sasm_intensity/ref_intensity) > calc_threshold:
            use_subtracted_sasms.append(True)
        else:
            use_subtracted_sasms.append(False)

    bl_sub_mean_i = np.array([sasm.getMeanI() for sasm in bl_corr])
    bl_sub_total_i = np.array([sasm.getTotalI() for sasm in bl_corr])

    return (bl_sasms, use_subtracted_sasms, bl_corr, fit_results, sub_mean_i,
        sub_total_i, bl_sub_mean_i, bl_sub_total_i)


###############################################################################
# REGALS stuff

def run_regals(M, intensity, sigma, min_iter=20, max_iter=1000, tol=0.001,
    conv_type='Chi^2', callback=None, abort_event=None):
    R = REGALS.regals(intensity, sigma)

    chis = np.empty(max_iter)
    niter = 0

    while True:

        if abort_event is not None:
            if abort_event.is_set():
                break

        M, params, resid = R.step(M)
        chis[niter] = params['x2']

        # if (niter +1) % 1 == 0 or niter == 0:
        #     print('Iteration: {}, chi^2: {}'.format(niter+1, params['x2']))

        if niter >= min_iter and conv_type=='Chi^2':
            if np.std(chis[niter-min_iter:niter+1]) < tol*np.median(chis[niter-min_iter:niter+1]):
                break

        if niter == max_iter-1:
            break

        niter += 1

    params['total_iter'] = niter+1

    if callback is not None:
        if abort_event is not None:
            if not abort_event.is_set():
                callback(M, params, resid)
        else:
            callback(M, params, resid)

    return M, params, resid

def create_regals_mixture(component_settings, q, x, intensity, sigma,
    seed_previous=False, prev_mixture=None):
    """
    Creates regals components, puts them into a mixture, and estimates/assigns
    lambda values as appropriate.
    """
    components = []

    prev_u_profile = None
    prev_u_conc = None

    if seed_previous and prev_mixture is not None:
        if len(prev_mixture.u_profile) == len(component_settings):
            if all(map(np.all, map(np.isfinite, prev_mixture.u_profile))):
                prev_u_profile = prev_mixture.u_profile

            if all(map(np.all, map(np.isfinite, prev_mixture.u_concentration))):
                prev_u_conc = prev_mixture.u_concentration

    for j, settings in enumerate(component_settings):
        prof_settings = settings[0]
        conc_settings = settings[1]

        conc = REGALS.concentration_class(conc_settings['type'], x,
            **conc_settings['kwargs'])
        prof = REGALS.profile_class(prof_settings['type'], q,
            **prof_settings['kwargs'])

        component = REGALS.component(conc, prof)

        components.append(component)

        if prev_u_profile is not None and prev_u_conc is not None:
            fixed_prev_u = match_regals_component_u(prof,
                prev_mixture.components[j].profile, prev_u_profile[j])
            prev_u_profile[j] = fixed_prev_u

            fixed_prev_u = match_regals_component_u(conc,
                prev_mixture.components[j].concentration, prev_u_conc[j])
            prev_u_conc[j] = fixed_prev_u

    if prev_u_profile is not None and prev_u_conc is not None:
        mixture = REGALS.mixture(components, u_concentration=prev_u_conc,
            u_profile=prev_u_profile)
    else:
        mixture = REGALS.mixture(components)

    if any([settings[0]['auto_lambda'] for settings in component_settings]):
        prof_lambda_est = mixture.estimate_profile_lambda(sigma)
        auto_prof = True
    else:
        prof_lambda_est = [settings[0]['lambda'] for settings in component_settings]
        auto_prof = False

    if any([settings[1]['auto_lambda'] for settings in component_settings]):
        conc_lambda_est = mixture.estimate_concentration_lambda(sigma)
        auto_conc = True
    else:
        conc_lambda_est = [settings[1]['lambda'] for settings in component_settings]
        auto_conc = False

    if auto_prof or auto_conc:
        for j, settings in enumerate(component_settings):
            prof_settings = settings[0]
            conc_settings = settings[1]

            if auto_prof and not prof_settings['auto_lambda']:
                prof_lambda_est[j] = prof_settings['lambda']

            if auto_conc and not conc_settings['auto_lambda']:
                conc_lambda_est[j] = conc_settings['lambda']

        mix_temp = copy.deepcopy(mixture)

        mix_temp.lambda_profile = prof_lambda_est
        mix_temp.lambda_concentration = conc_lambda_est

        R = REGALS.regals(intensity, sigma)

        mix_temp = R.step(mix_temp)[0]

        prof_lambda_est = mix_temp.estimate_profile_lambda(sigma)
        conc_lambda_est = mix_temp.estimate_concentration_lambda(sigma)

        for j, settings in enumerate(component_settings):
            prof_settings = settings[0]
            conc_settings = settings[1]

            if prof_settings['auto_lambda']:
                p_lambda = float(np.format_float_scientific(prof_lambda_est[j], 0))
            else:
                p_lambda = prof_settings['lambda']

            prof_lambda_est[j] = p_lambda

            if conc_settings['auto_lambda']:
                c_lambda = float(np.format_float_scientific(conc_lambda_est[j], 0))
            else:
                c_lambda = conc_settings['lambda']

            conc_lambda_est[j] = c_lambda

    mixture.lambda_profile = prof_lambda_est
    mixture.lambda_concentration = conc_lambda_est

    return mixture, components

def match_regals_component_u(new_comp, old_comp, old_u):
    new_u0 = new_comp.u0
    fixed_u = np.empty_like(new_u0)

    if isinstance(new_comp, REGALS.concentration_class):

        if ((new_comp.reg_type == 'smooth' and old_comp.reg_type == 'smooth')
            and (old_comp._regularizer.Nw == new_comp._regularizer.Nw)):

            if ((new_comp._regularizer.is_zero_at_xmin == old_comp._regularizer.is_zero_at_xmin)
                and (new_comp._regularizer.is_zero_at_xmax == old_comp._regularizer.is_zero_at_xmax)):
                # Both end points are the same
                fixed_u = old_u

            elif new_comp._regularizer.is_zero_at_xmin == old_comp._regularizer.is_zero_at_xmin:
                # Only the max endpoint is different
                if new_comp._regularizer.is_zero_at_xmax and not old_comp._regularizer.is_zero_at_xmax:
                    fixed_u = old_u[:-1]

                elif not new_comp._regularizer.is_zero_at_xmax and old_comp._regularizer.is_zero_at_xmax:
                    fixed_u[:-1] = old_u
                    fixed_u[-1] = new_u0[-1]

            elif new_comp._regularizer.is_zero_at_xmax == old_comp._regularizer.is_zero_at_xmax:
                # Only the min endpoint is different
                if new_comp._regularizer.is_zero_at_xmin and not old_comp._regularizer.is_zero_at_xmin:
                    fixed_u = old_u[1:]

                elif not new_comp._regularizer.is_zero_at_xmin and old_comp._regularizer.is_zero_at_xmin:
                    fixed_u[1:] = old_u
                    fixed_u[0] = new_u0[0]

            else:
                # Both end points are different
                if new_comp._regularizer.is_zero_at_xmax and not old_comp._regularizer.is_zero_at_xmax:
                    if new_comp._regularizer.is_zero_at_xmin and not old_comp._regularizer.is_zero_at_xmin:
                        fixed_u = old_u[1:-1]

                    elif not new_comp._regularizer.is_zero_at_xmin and old_comp._regularizer.is_zero_at_xmin:
                        fixed_u[1:] = old_u[:-1]
                        fixed_u[0] = new_u0[0]

                elif not new_comp._regularizer.is_zero_at_xmax and old_comp._regularizer.is_zero_at_xmax:
                    if new_comp._regularizer.is_zero_at_xmin and not old_comp._regularizer.is_zero_at_xmin:
                        fixed_u[:-1] = old_u[1:]
                        fixed_u[-1] = new_u0[-1]

                    elif not new_comp._regularizer.is_zero_at_xmin and old_comp._regularizer.is_zero_at_xmin:
                        fixed_u[1:-1] = old_u
                        fixed_u[-1] = new_u0[-1]
                        fixed_u[0] = new_u0[0]

        elif ((new_comp.reg_type == 'simple' and old_comp.reg_type == 'simple')
            and len(new_u0) == len(old_u)):
            fixed_u = old_u

        else:
            fixed_u = new_u0

    else:
        if ((new_comp.reg_type == 'realspace' and old_comp.reg_type == 'realspace')
            and (old_comp._regularizer.Nw == new_comp._regularizer.Nw)):
            if ((new_comp._regularizer.is_zero_at_r0 == old_comp._regularizer.is_zero_at_r0)
                and (new_comp._regularizer.is_zero_at_dmax == old_comp._regularizer.is_zero_at_dmax)):
                # Both end points are the same
                fixed_u = old_u

            elif new_comp._regularizer.is_zero_at_r0 == old_comp._regularizer.is_zero_at_r0:
                # Only the max endpoint is different
                if new_comp._regularizer.is_zero_at_dmax and not old_comp._regularizer.is_zero_at_dmax:
                    fixed_u = old_u[:-1]

                elif not new_comp._regularizer.is_zero_at_dmax and old_comp._regularizer.is_zero_at_dmax:
                    fixed_u[:-1] = old_u
                    fixed_u[-1] = new_u0[-1]

            elif new_comp._regularizer.is_zero_at_dmax == old_comp._regularizer.is_zero_at_dmax:
                # Only the min endpoint is different
                if new_comp._regularizer.is_zero_at_r0 and not old_comp._regularizer.is_zero_at_r0:
                    fixed_u = old_u[1:]

                elif not new_comp._regularizer.is_zero_at_r0 and old_comp._regularizer.is_zero_at_r0:
                    fixed_u[1:] = old_u
                    fixed_u[0] = new_u0[0]

            else:
                # Both end points are different
                if new_comp._regularizer.is_zero_at_dmax and not old_comp._regularizer.is_zero_at_dmax:
                    if new_comp._regularizer.is_zero_at_r0 and not old_comp._regularizer.is_zero_at_r0:
                        fixed_u = old_u[1:-1]

                    elif not new_comp._regularizer.is_zero_at_r0 and old_comp._regularizer.is_zero_at_r0:
                        fixed_u[1:] = old_u[:-1]
                        fixed_u[0] = new_u0[0]

                elif not new_comp._regularizer.is_zero_at_dmax and old_comp._regularizer.is_zero_at_dmax:
                    if new_comp._regularizer.is_zero_at_r0 and not old_comp._regularizer.is_zero_at_r0:
                        fixed_u[:-1] = old_u[1:]
                        fixed_u[-1] = new_u0[-1]

                    elif not new_comp._regularizer.is_zero_at_r0 and old_comp._regularizer.is_zero_at_r0:
                        fixed_u[1:-1] = old_u
                        fixed_u[-1] = new_u0[-1]
                        fixed_u[0] = new_u0[0]

        elif ((new_comp.reg_type == 'simple' or new_comp.reg_type == 'smooth')
            and (old_comp.reg_type == 'simple' or old_comp.reg_type == 'smooth')
            and len(new_u0) == len(old_u)):
            fixed_u = old_u

        else:
            fixed_u = new_u0

    return fixed_u


def make_regals_sasms(mixture, q, intensity, sigma, secm, start, end, q_err=None):

    old_filename = secm.getParameter('filename').split('.')

    new_sasms = []

    if len(old_filename) > 1:
        old_filename = '.'.join(old_filename[:-1])
    else:
        old_filename = old_filename[0]

    for j in range(mixture.Nc):
        calc_intensity, calc_err = mixture.extract_profile(intensity, sigma, j)

        sasm = SASM.SASM(calc_intensity, q, calc_err, {}, q_err)

        sasm.setParameter('filename', '{}_{}'.format(old_filename, j))

        history_dict = {}

        history_dict['input_filename'] = secm.getParameter('filename')
        history_dict['start_index'] = str(start)
        history_dict['end_index'] = str(end)
        history_dict['component_number'] = str(j)

        prof_comp = mixture.components[j].profile
        conc_comp = mixture.components[j].concentration

        history_dict['profile'] = {}
        history_dict['profile']['regularizer'] = prof_comp.reg_type

        if prof_comp.reg_type != 'simple':
            history_dict['profile']['nw'] = prof_comp._regularizer.Nw

        if prof_comp.reg_type == 'realspace':
            history_dict['profile']['dmax'] = prof_comp._regularizer.dmax
            history_dict['profile']['is_zero_at_r0'] = prof_comp._regularizer.is_zero_at_r0
            history_dict['profile']['is_zero_at_dmax'] = prof_comp._regularizer.is_zero_at_dmax

        history_dict['concentration'] = {}
        history_dict['concentration']['regularizer'] = conc_comp.reg_type

        if conc_comp.reg_type != 'simple':
            history_dict['concentration']['nw'] = conc_comp._regularizer.Nw
            history_dict['concentration']['component_range'] = ('[{}, '
                '{}]'.format(conc_comp._regularizer.xmin, conc_comp._regularizer.xmax))
            history_dict['concentration']['is_zero_at_xmin'] = conc_comp._regularizer.is_zero_at_xmin
            history_dict['concentration']['is_zero_at_xmax'] = conc_comp._regularizer.is_zero_at_xmax

        history = sasm.getParameter('history')
        history['REGALS'] = history_dict

        new_sasms.append(sasm)

    return new_sasms

def make_regals_ifts(mixture, q, intensity, sigma, secm, start, end):
    old_filename = secm.getParameter('filename').split('.')

    new_ifts = []

    if len(old_filename) > 1:
        old_filename = '.'.join(old_filename[:-1])
    else:
        old_filename = old_filename[0]

    for j in range(mixture.Nc):

        prof_comp = mixture.components[j].profile
        conc_comp = mixture.components[j].concentration

        if prof_comp.reg_type == 'realspace':
            r = prof_comp.w
            pr = mixture.u_profile[j]

            if prof_comp._regularizer.is_zero_at_r0:
                pr = np.concatenate(([0], pr))

            if prof_comp._regularizer.is_zero_at_dmax:
                pr = np.concatenate((pr, [0]))

            area = np.trapz(pr, r)
            area2 = np.trapz(np.array(pr)*np.array(r)**2, r)

            rg = np.sqrt(abs(area2/(2.*area)))
            i0 = area*4*np.pi

            calc_intensity, calc_err = mixture.extract_profile(intensity, sigma, j)


            history_dict = {}

            history_dict['input_filename'] = secm.getParameter('filename')
            history_dict['start_index'] = str(start)
            history_dict['end_index'] = str(end)
            history_dict['component_number'] = str(j)

            prof_comp = mixture.components[j].profile
            conc_comp = mixture.components[j].concentration

            history_dict['profile'] = {}
            history_dict['profile']['regularizer'] = prof_comp.reg_type

            if prof_comp.reg_type != 'simple':
                history_dict['profile']['nw'] = prof_comp._regularizer.Nw

            if prof_comp.reg_type == 'realspace':
                history_dict['profile']['dmax'] = prof_comp._regularizer.dmax
                history_dict['profile']['is_zero_at_r0'] = prof_comp._regularizer.is_zero_at_r0
                history_dict['profile']['is_zero_at_dmax'] = prof_comp._regularizer.is_zero_at_dmax

            history_dict['concentration'] = {}
            history_dict['concentration']['regularizer'] = conc_comp.reg_type

            if conc_comp.reg_type != 'simple':
                history_dict['concentration']['nw'] = conc_comp._regularizer.Nw
                history_dict['concentration']['component_range'] = ('[{}, '
                    '{}]'.format(conc_comp._regularizer.xmin, conc_comp._regularizer.xmax))
                history_dict['concentration']['is_zero_at_xmin'] = conc_comp._regularizer.is_zero_at_xmin
                history_dict['concentration']['is_zero_at_xmax'] = conc_comp._regularizer.is_zero_at_xmax


            results = {
                'dmax'      : prof_comp._regularizer.dmax,
                'rg'        : rg,
                'i0'        : i0,
                'qmin'      : q[0],
                'qmax'      : q[-1],
                'algorithm' : 'REGALS',
                'filename'  : old_filename,
                'REGALS'    : history_dict,
                }

            ift = SASM.IFTM(pr, r, -1*np.ones_like(pr), calc_intensity, q,
                calc_err, calc_intensity, results, calc_intensity, q)

            new_ifts.append(ift)

        else:
            new_ifts.append(None)

    return new_ifts

def make_regals_concs(mixture, intensity, sigma):
    concs = []

    for j in range(mixture.Nc):
        x = mixture.components[j].concentration._regularizer.x
        c = mixture.extract_concentration(intensity, sigma, j)

        concs.append((x, c[0], c[1]))

    return concs

def make_regals_regularized_concs(mixture):
    reg_concs = []

    for j in range(mixture.Nc):
        x = mixture.components[j].concentration.w
        c = mixture.u_concentration[j]

        if mixture.components[j].concentration.reg_type == 'smooth':
            if mixture.components[j].concentration._regularizer.is_zero_at_xmin:
                c = np.concatenate(([0], c))
            if mixture.components[j].concentration._regularizer.is_zero_at_xmax:
                c = np.concatenate((c, [0]))

        reg_concs.append((x, c))

    return reg_concs

def run_full_regals(series, comp_settings, profile_type='sub', framei=None,
    framef=None, x_vals=None, min_iter=25, max_iter=1000, tol=0.0001,
    conv_type='Chi^2', use_previous_results=False,
    previous_results=None):
    """
    Runs regularized alternating least squares (REGALS) on the input series to
    deconvolve overlapping components in the data.

    Parameters
    ----------
    series: list or :class:`bioxtasraw.SECM.SECM`
        The input series to be deconvolved. It should either be a list
        of individual scattering profiles (:class:`bioxtasraw.SASM.SASM`) or
        a single series object (:class:`bioxtasraw.SECM.SECM`).
    comp_settings: list
        A list where each entry is the settings for a REGALS component. REGALS
        component settings are themselves lists with two entries, one for the
        profile settings and one for the concentration settings. Each of these
        is a dictionary. Profile and settings are::

            prof_settings = {
                'type'          : 'simple', #simple, smooth, or realspace
                'lambda'        : 1.0, #float of the regularizer
                'auto_lambda'   : True, #Whether to automatically determine lambda
                'kwargs'        : {
                    'Nw'    : 50, #Number of control points (smooth/realspace)
                    'dmax'  : 100, #Maximum dimension (realspace)
                    'is_zero_at_r0' : True, #realspace
                    'is_zero_at_damx': True, #realspace
                },
            }

            conc_settings = {
                'type'  : 'simple', #simple or smooth
                'lambda'        : 1.0, #float of the regularizer
                'auto_lambda'   : True, #Whether to automatically determine lambda
                'kwargs'        : {
                    'xmin'  : 0, #Minimum x value for the component
                    'xmax'  : 1, #Maximum x value for the component
                    'Nw'    : 50, #Number of control points (smooth)
                    'is_zero_at_xmin'   : True, #Smooth
                    'is_zero_at_xmax'   : True, #Smooth

                },
            }

    profile_type: {'unsub', 'sub', 'baseline'} str, optional
        Only used if a :class:`bioxtasraw.SECM.SECM` is provided for the series
        argument. Determines which type of profile to use from the series
        for the REGALS. Unsubtracted profiles - 'unsub', subtracted profiles -
        'sub', baseline corrected profiles - 'baseline'.
    framei: int, optional
        The initial frame in the series to use for REGALS. If not provided,
        it defaults to the first frame in the series.
    framef: int, optional
        The final frame in the series to use for REGALS. If not provided, it
        defaults to the last frame in the series.
    min_iter: int, optional
        The minimum number of iterations of the REGALS algorithm to run. Defaults
        to 25.
    max_iter: int, optional
        The maximum number of iterations of the REGALS algorithm to run. Defaults
        to 1000. If convergence method is set to 'Iterations' then this value is
        used as the number of iterations to run.
    tol: float, optional
        The relative tolerance to use for the 'Chi^2' convergence criteria.
        Defaults to 0.001.
    conv_type: str, optional
        The convergence type to use. Can be either 'Iterations' or 'Chi^2'.
        Iterations runs a number of iterations equal to max_iter. The chi^2
        criteria runs iterations until the average of the past min_iter
        iterations is stable within the tolerance defined by tol, up to the
        max_iter number of iterations.
    use_previous_results: bool, optional
        Whether to use previous results as the initial profile and concentration
        vectors. Requires previous_results input. Defaults to False.
    previous_results: :class:`bioxtasraw.REGALS.mixture`, optional
        The mixture output from a previous REGALS run, which will be used as
        the initial profile and concentration vectors for this REGALS run. Only
        used of use_previous_results is True.

    Returns
    -------
    regals_profiles: list
        A list of profiles (:class:`bioxtasraw.SASM.SASM`) determined by REGALS.
    regals_ifts: list
        A list of IFTS (:class:`bioxtasraw.SASM.IFTM`) determined by REGALS.
        Only contains results for components using the 'realspace' constraint.
    concs: list
        The concentrations sampled at the input experimental points. Returns
        a list where each list item is a tuple of (x, conc, conc_sigma).
    reg_concs: list
        The regularized concentrations sampled at the grid/control points.
        Returns a list where each list item is a list of (x, conc).
    mixture: REGALS.mixture
        The final mixture result from REGALS. Can be used as input to REGALS to
        start with the previously determined values for each component.
    params: dict
        Contains the final convergence parameters for REGALS. Each parameter
        is for the final iteration of the algorithm. 'x2': chi^2,
        'delta_concentration': the difference between the final and final-1
        iterations concentrations. 'delta_profile': the difference between
        the final and final-1 iterations profiles. 'delta_u_concentration':
        the difference between the final and final-1 iterations u concentration
        matrix. 'delta_u_profile': the difference between the final and final-1
        iterations U profiles matrix. 'total_iter': the total number of iterations.
    residual: :class:`numpy.array`
        The residual between the initial input intensities and the deconvolved
        intensities. This is a matrix where each column corresponds to an
        input intensity.
    """
    if framei is None:
            framei = 0
    if framef is None:
        if isinstance(series, SECM.SECM):
            framef = len(series.getAllSASMs())-1
        else:
            framef = len(series)-1

    ref_q = series.getSASMList(framei, framef)[0].getQ()
    ref_q_err = series.getSASMList(framei, framef)[0].getQErr()

    if x_vals is None:
        x_vals = np.arange(framei, framef+1)

    if isinstance(series, SECM.SECM):
        sasm_list = series.getSASMList(framei, framef, profile_type)
        filename = os.path.splitext(series.getParameter('filename'))[0]
    else:
        sasm_list = series[framei:framef+1]
        names = [os.path.basename(sasm.getParameter('filename')) for sasm in series]
        filename = os.path.commonprefix(names).rstrip('_')
        if filename == '':
            filename =  os.path.splitext(os.path.basename(series[0].getParameter('filename')))[0]

    i = np.array([sasm.getI() for sasm in sasm_list])
    err = np.array([sasm.getErr() for sasm in sasm_list])

    intensity = i.T #Because of how numpy does the SVD, to get U to be the scattering vectors and V to be the other, we have to transpose
    sigma = err.T

    if (use_previous_results and previous_results is not None and
        len(previous_results.u_profile) == len(comp_settings)):
        mixture, components = create_regals_mixture(comp_settings,
            ref_q, x_vals, intensity, sigma, use_previous_results,
            previous_results)

    else:
        mixture, components = create_regals_mixture(comp_settings,
            ref_q, x_vals, intensity, sigma)

    mixture, params, residual = run_regals(mixture, intensity, sigma,
        min_iter=min_iter, max_iter=max_iter, tol=tol, conv_type=conv_type)

    regals_profiles = make_regals_sasms(mixture, ref_q, intensity, sigma,
        series, framei, framef, ref_q_err)

    regals_ifts = make_regals_ifts(mixture, ref_q, intensity, sigma,
        series, framei, framef)

    concs = make_regals_concs(mixture, intensity, sigma)
    reg_concs = make_regals_regularized_concs(mixture)

    # Make results into a format that matches the GUI
    comp_ranges = np.array([[comp[1]['kwargs']['xmin'], comp[1]['kwargs']['xmin']] for comp in comp_settings])

    if x_vals is not None:
        comp_frame_ranges = []

        for cr in comp_ranges:
            min_val, min_arg = SASUtils.find_closest(cr[0], x_vals)
            max_val, max_arg = SASUtils.find_closest(cr[1], x_vals)

            start = min_arg + framei
            end = max_arg + framei

            comp_frame_ranges.append([start, end])

    ctrl_settings = {
        'seed_previous' : use_previous_results,
        'conv_type'     : conv_type,
        'max_iter'      : max_iter,
        'min_iter'      : min_iter,
        'tol'           : tol,
        }

    for j, comp in enumerate(comp_settings):
        prof = comp[0]
        conc = comp[1]

        prof['lambda'] = mixture.lambda_profile[j]
        conc['lambda'] = mixture.lambda_concentration[j]

    analysis_dict = series.getParameter('analysis')

    regals_dict = {}

    if profile_type == 'unsub':
        profile_data = 'Unsubtracted'
    elif profile_type == 'sub':
        profile_data = 'Subtracted'
    elif profile_type == 'baseline':
        profile_data = 'Baseline Corrected'

    regals_dict['fstart'] = str(framei)
    regals_dict['fend'] = str(framef)
    regals_dict['profile'] = profile_data
    regals_dict['nsvs'] = str(len(regals_profiles))
    regals_dict['ranges'] = comp_ranges
    regals_dict['frame_ranges'] = comp_frame_ranges
    regals_dict['component_settings'] = comp_settings
    regals_dict['run_settings'] = ctrl_settings
    regals_dict['background_components'] = 0
    regals_dict['exp_type'] = 'IEC/SEC-SAXS'
    regals_dict['use_efa'] = True

    if not np.array_equal(x_vals, np.arange(framei, framef+1)):
        regals_dict['x_calibration'] = x_vals

    analysis_dict['regals'] = regals_dict

    return regals_profiles, regals_ifts, concs, reg_concs, mixture, params, residual
