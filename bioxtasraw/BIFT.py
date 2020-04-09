#******************************************************************************
# This file is part of BioXTAS RAW.
#
#    BioXTAS RAW is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    BioXTAS RAW is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with BioXTAS RAW.  If not, see <http://www.gnu.org/licenses/>.
#
#******************************************************************************

from __future__ import absolute_import, division, print_function, unicode_literals
from builtins import object, range, map, zip
from io import open
import six

import multiprocessing
import functools
import threading
import os
import platform

import scipy.optimize
import scipy.interpolate
import numpy as np
from numba import jit

raw_path = os.path.abspath(os.path.join('.', __file__, '..', '..'))
if raw_path not in os.sys.path:
    os.sys.path.append(raw_path)

import bioxtasraw.SASM as SASM

def createTransMatrix(q, r):
    """
    Matrix such that when you take T dot P(r) you get I(q),
    The A_ij matrix in equation (2) of Hansen 2000.
    """
    T = np.outer(q, r)
    T = 4*np.pi*(r[1]-r[0])*np.where(T==0, 1, np.sin(T)/T)

    return T

def distDistribution_Sphere(i0_meas, N, dmax):
    """Creates the initial P(r) function for the prior as a sphere.

    Formula from Svergun & Koch 2003:

    p(r) = 4*pi*D**3/24*r**2*(1-1.5*r/D+0.5*(r/D)**3)

    Normalized so that the area is equal to the measured I(0). Integrate p(r):

    I(0) = integral of p(r) from 0 to Dmax
         = (4*pi*D^3/24)**2

    So the normalized p(r) is:

    p(r) = r**2*(1-1.5*r/D+0.5*(r/D)**3) * I(0)_meas/(4*pi*D**3/24)

    To match convention with old RAW BIFT, we also carry around an extra factor
    of 4*pi*Delta r, so the normalization becomes:

    p(r) = r**2*(1-1.5*r/D+0.5*(r/D)**3) * I(0)_meas/(D**3/(24*Delta_r))
    """

    r = np.linspace(0, dmax, N+1)

    p = r**2 * (1 - 1.5*(r/dmax) + 0.5*(r/dmax)**3)
    p = p * i0_meas/(4*np.pi*dmax**3/24.)
    # p = p * i0_meas/(dmax**3/(24.*(r[1]-r[0])))   #Which normalization should I use? I'm not sure either agrees with what Hansen does.

    return p, r

def makePriorDistribution(i0, N, dmax, dist_type='sphere'):
    if dist_type == 'sphere':
        p, r = distDistribution_Sphere(i0, N, dmax)

    return p, r

@jit(nopython=True, cache=True)
def bift_inner_loop(f, p, B, alpha, N, sum_dia):
    #Define starting conditions and loop variables
    ite = 0
    maxit = 2000
    minit = 100
    xprec = 0.999
    dotsp = 0
    omega = 0.5

    sigma = np.zeros_like(p)

    #Start loop
    while ite < maxit and not (ite > minit and dotsp > xprec):
        ite = ite + 1

        #some kind of renormalization of the p vector
        sigma[1:-1] = np.abs(p[1:-1]+1e-10)
        p[1:-1][p[1:-1]<=0] = p[1:-1][p[1:-1]<=0]*-1+1e-10
        f[1:-1][f[1:-1]<=0] = f[1:-1][f[1:-1]<=0]*-1+1e-10

        #Apply smoothness constraint
        for k in range(2, N-1):
            p[k] = (f[k-1] + f[k+1])/2.

        p[1] = f[2]/2.
        p[-2] = p[-3]/2.

        p[0] = f[0]
        p[-1] = f[-1]

        sigma[0] = 10

        #Calculate the next correction
        for k in range(1, N):
            fsumi = 0

            for j in range(1, N):
                fsumi = fsumi + B[k, j]*f[j]

            fsumi = fsumi - B[k, k]*f[k]

            fx = (2*alpha*p[k]/sigma[k]+sum_dia[k]-fsumi)/(2*alpha/sigma[k]+B[k,k])

            f[k] = (1-omega)*f[k]+omega*fx

        # Calculate convergence
        gradsi = -2*(f[1:-1]-p[1:-1])/sigma[1:-1]
        gradci = 2*(np.sum(B[1:-1,1:-1]*f[1:-1], axis=1)-sum_dia[1:-1])

        wgrads = np.sqrt(np.abs(np.sum(gradsi**2)))
        wgradc = np.sqrt(np.abs(np.sum(gradci**2)))

        if wgrads*wgradc == 0:
            dotsp = 1
        else:
            dotsp = np.sum(gradsi*gradci)/(wgrads*wgradc)

    return f, p, sigma, dotsp, xprec

def getEvidence(params, q, i, err, N):

    alpha, dmax = params
    alpha = np.exp(alpha)

    err = err**2

    p, r = makePriorDistribution(i[0], N, dmax) #Note, here I use p for what Hansen calls m
    T = createTransMatrix(q, r)

    p[0] = 0
    f = np.zeros_like(p)

    norm_T = T/err[:,None]  #Slightly faster to create this first

    sum_dia = np.sum(norm_T*i[:,None], axis=0)   #Creates YSUM in BayesApp code, some kind of calculation intermediate
    sum_dia[0] = 0

    B = np.dot(T.T, norm_T)     #Creates B(i, j) in BayesApp code
    B[0,:] = 0
    B[:,0] = 0

    #Do some kind of rescaling of the input
    c1 = np.sum(np.sum(T[1:4,1:-1]*p[1:-1], axis=1)/err[1:4])
    c2 = np.sum(i[1:4]/err[1:4])
    p[1:-1] = p[1:-1]*(c2/c1)
    f[1:-1] = p[1:-1]*1.001     #Note: f is called P in the original RAW BIFT code

    # Do the optimization
    f, p, sigma, dotsp, xprec = bift_inner_loop(f, p, B, alpha, N, sum_dia)

    # Calculate the evidence
    s = np.sum(-(f[1:-1]-p[1:-1])**2/sigma[1:-1])
    c = np.sum((i[1:-1]-np.sum(T[1:-1,1:-1]*f[1:-1], axis=1))**2/err[1:-1])/i.size

    u = np.sqrt(np.abs(np.outer(f[1:-1], f[1:-1])))*B[1:-1, 1:-1]/alpha
    u[np.diag_indices(u.shape[0])] = u[np.diag_indices(u.shape[0])]+1
    w = np.linalg.svd(u, compute_uv = False)
    rlogdet = np.sum(np.log(np.abs(w)))

    evidence = -np.log(abs(dmax))+(alpha*s-0.5*c*i.size)-0.5*rlogdet-np.log(abs(alpha))

    # Some kind of after the fact adjustment

    if evidence <= 0 and dotsp < xprec:
        evidence=evidence*30
    elif dotsp < xprec:
        evidence = evidence/30.

    return evidence, c, f, r

def getEvidenceOptimize(params, q, i, err, N):
    evidence, c, f, r = getEvidence(params, q, i, err, N)
    #Negative so you can minimize on it
    return -evidence

def calc_bift_errors(opt_params, q, i, err, N, mc_runs=300, abort_check=False,
    single_proc=False):
    #First, randomly generate a set of parameters similar but not quite the same as the best parameters (monte carlo)
    #Then, calculate the evidence, pr, and other results for each set of parameters
    alpha_opt, dmax_opt = opt_params
    mult = 3.0

    if not single_proc:
        n_proc = multiprocessing.cpu_count()
        mp_pool = multiprocessing.Pool(processes=n_proc)
        mp_get_evidence = functools.partial(getEvidence, q=q, i=i, err=err, N=N)

    ev_array = np.zeros(mc_runs)
    c_array = np.zeros(mc_runs)
    f_array = np.zeros((mc_runs, N+1))
    r_array = np.zeros((mc_runs, N+1))

    max_dmax = dmax_opt+0.1*dmax_opt*0.5*mult

    _, ref_r = makePriorDistribution(i[0], N, max_dmax)

    run_mc = True

    while run_mc:

        alpha_array = alpha_opt+0.1*alpha_opt*(np.random.random(mc_runs)-0.5)*mult
        dmax_array = dmax_opt+0.1*dmax_opt*(np.random.random(mc_runs)-0.5)*mult
        alpha_array[0] = alpha_opt
        dmax_array[0] = dmax_opt

        pts = list(zip(alpha_array, dmax_array))

        if not single_proc:
            results = mp_pool.map(mp_get_evidence, pts)
        else:
            results = [getEvidence(params, q, i, err, N) for params in pts]

        for res_idx, res in enumerate(results):
            dmax = dmax_array[res_idx]

            evidence, c, f, r = res

            interp = scipy.interpolate.interp1d(r, f, copy=False)

            f_interp = np.zeros_like(ref_r)
            f_interp[ref_r<dmax] = interp(ref_r[ref_r<dmax])

            ev_array[res_idx] = evidence
            c_array[res_idx] = c
            f_array[res_idx,:] = f_interp
            r_array[res_idx,:] = ref_r

        if np.abs(ev_array).max() >= 9e8:
            mult = mult/2.

            if mult < 0.001:
                run_mc = False

            if abort_check.is_set():
                run_mc = False

        else:
            run_mc = False

    if not single_proc:
        mp_pool.close()
        mp_pool.join()

    #Then, calculate the probability of each result as exp(evidence - evidence_max)**(1/minimum_chisq), normalized by the sum of all result probabilities

    ev_max = ev_array.max()
    prob = np.exp(ev_array - ev_max)**(1./c_array.min())
    prob = prob/prob.sum()

    #Then, calculate the average P(r) function as the weighted sum of the P(r) functions
    #Then, calculate the error in P(r) as the square root of the weighted sum of squares of the difference between the average result and the individual estimate
    p_avg = np.sum(f_array*prob[:,None], axis=0)
    err = np.sqrt(np.abs(np.sum((f_array-p_avg)**2*prob[:,None], axis=0)))

    #Then, calculate structural results as weighted sum of each result
    alpha = np.sum(alpha_array*prob)
    dmax = np.sum(dmax_array*prob)
    c = np.sum(c_array*prob)
    evidence = np.sum(ev_array*prob)

    area = np.trapz(f_array, r_array, axis=1)
    area2 = np.trapz(f_array*r_array**2, r_array, axis=1)
    rg_array = np.sqrt(abs(area2/(2.*area)))
    i0_array = area*4*np.pi
    rg = np.sum(rg_array*prob)
    i0 = np.sum(i0_array*prob)

    sd_alpha = np.sqrt(np.sum((alpha_array - alpha)**2*prob))
    sd_dmax = np.sqrt(np.sum((dmax_array - dmax)**2*prob))
    sd_c = np.sqrt(np.sum((c_array - c)**2*prob))
    sd_ev = np.sqrt(np.sum((ev_array - evidence)**2*prob))
    sd_rg = np.sqrt(np.sum((rg_array - rg)**2*prob))
    sd_i0 = np.sqrt(np.sum((i0_array - i0)**2*prob))

    #Should I also extrapolate to q=0? Might be good, though maybe not in this function
    #Should I report number of good parameters (ftot(nmax-12 in Hansen code, line 2247))
    #Should I report number of Shannon Channels? That's easy to calculate: q_range*dmax/pi

    return ref_r, p_avg, err, (alpha, sd_alpha), (dmax, sd_dmax), (c, sd_c), (evidence, sd_ev), (rg, sd_rg), (i0, sd_i0)

def make_fit(q, r, pr):
    qr = np.outer(q, r)
    sinc_qr = np.where(qr==0, 1, np.sin(qr)/qr)
    i = 4*np.pi*np.trapz(pr*sinc_qr, r, axis=1)

    return i

def doBift(q, i, err, filename, npts, alpha_min, alpha_max, alpha_n, dmax_min,
    dmax_max, dmax_n, mc_runs, queue=None, abort_check=threading.Event()):

    # Start by finding the optimal dmax and alpha via minimization of evidence
    if platform.system() == 'Darwin' and six.PY3:
        single_proc = True
    else:
        single_proc = False

    alpha_min = np.log(alpha_min)
    alpha_max = np.log(alpha_max)

    alpha_points = np.linspace(alpha_min, alpha_max, alpha_n)          # alpha points are log(alpha) for better search
    dmax_points = np.linspace(dmax_min, dmax_max, dmax_n)

    all_posteriors = np.zeros((dmax_points.size, alpha_points.size))

    N = npts - 1

    if not single_proc:
        n_proc = multiprocessing.cpu_count()
        mp_pool = multiprocessing.Pool(processes=n_proc)
        mp_get_evidence = functools.partial(getEvidence, q=q, i=i, err=err, N=N)

    # Loop through a range of dmax and alpha to get a starting point for the minimization

    if abort_check.is_set():
        if queue is not None:
            queue.put({'canceled' : True})

        if not single_proc:
            mp_pool.close()
            mp_pool.join()

        return None

    for d_idx, dmax in enumerate(dmax_points):

        pts = [(alpha, dmax) for alpha in alpha_points]

        if not single_proc:
            results = mp_pool.map(mp_get_evidence, pts)
        else:
            results = [getEvidence(params, q, i, err, N) for params in pts]

        for res_idx, res in enumerate(results):
            all_posteriors[d_idx, res_idx] = res[0]

        if queue is not None:
            bift_status = {
                'alpha'     : pts[-1][0],
                'evidence'  : res[0],
                'chi'       : res[1],          #Actually chi squared
                'dmax'      : pts[-1][1],
                'spoint'    : (d_idx+1)*(res_idx+1),
                'tpoint'    : alpha_points.size*dmax_points.size,
                }

            queue.put({'update' : bift_status})

        if abort_check.is_set():
            if queue is not None:
                queue.put({'canceled' : True})

            if not single_proc:
                mp_pool.close()
                mp_pool.join()

            return None

    if not single_proc:
        mp_pool.close()
        mp_pool.join()

    if queue is not None:
        bift_status = {
            'alpha'     : pts[-1][0],
            'evidence'  : res[0],
            'chi'       : res[1],          #Actually chi squared
            'dmax'      : pts[-1][1],
            'spoint'    : alpha_points.size*dmax_points.size,
            'tpoint'    : alpha_points.size*dmax_points.size,
            'status'    : 'Running minimization',
            }

        queue.put({'update' : bift_status})

    min_idx = np.unravel_index(np.argmax(all_posteriors, axis=None), all_posteriors.shape)

    min_dmax = dmax_points[min_idx[0]]
    min_alpha = alpha_points[min_idx[1]]

    # Once a starting point is found, do an actual minimization to find the best alpha/dmax
    opt_res = scipy.optimize.minimize(getEvidenceOptimize, (min_alpha, min_dmax),
        (q, i, err, N), method='Powell')

    if abort_check.is_set():
        if queue is not None:
            queue.put({'canceled' : True})
        return None

    if opt_res.get('success'):
        alpha, dmax = opt_res.get('x')
        evidence, c, f, r = getEvidence((alpha, dmax), q, i, err, N)

        if queue is not None:
            bift_status = {
                'alpha'     : alpha,
                'evidence'  : evidence,
                'chi'       : c,          #Actually chi squared
                'dmax'      : dmax,
                'spoint'    : alpha_points.size*dmax_points.size,
                'tpoint'    : alpha_points.size*dmax_points.size,
                'status'    : 'Calculating Monte Carlo errors',
                }

            queue.put({'update' : bift_status})

        pr = f

        area = np.trapz(pr, r)
        area2 = np.trapz(np.array(pr)*np.array(r)**2, r)

        rg = np.sqrt(abs(area2/(2.*area)))
        i0 = area*4*np.pi

        fit = make_fit(q, r, pr)

        q_extrap = np.arange(0, q[1]-q[0], q[1])
        q_extrap = np.concatenate((q_extrap, q))

        fit_extrap = make_fit(q_extrap, r, pr)

        # Use a monte carlo method to estimate the errors in pr function, values found
        err_calc = calc_bift_errors((alpha, dmax), q, i, err, N, mc_runs,
            abort_check=abort_check, single_proc=single_proc)

        if abort_check.is_set():
            if queue is not None:
                queue.put({'canceled' : True})
            return None

        r_err, _, pr_err, a_res, d_res, c_res, ev_res, rg_res, i0_res = err_calc

        # NOTE: Unlike Hansen, we don't return the average pr function from the montecarlo
        # error estimate, but rather the best pr from the optimal dmax/alpha found above
        # This is consistent with the old RAW behavior. In the future this could change.

        rg_sd = rg_res[1]
        i0_sd = i0_res[1]
        alpha_sd = a_res[1]
        dmax_sd = d_res[1]
        c_sd = c_res[1]
        ev_sd = ev_res[1]

        interp = scipy.interpolate.interp1d(r_err, pr_err, copy=False)
        err_interp = interp(r)

        results = {
            'dmax'          : dmax,         # Dmax
            'dmaxer'        : dmax_sd,      # Uncertainty in Dmax
            'rg'            : rg,           # Real space Rg
            'rger'          : rg_sd,        # Real space rg error
            'i0'            : i0,           # Real space I0
            'i0er'          : i0_sd,        # Real space I0 error
            'chisq'         : c,            # Actual chi squared value
            'chisq_er'      : c_sd,         # Uncertainty in chi squared
            'alpha'         : alpha,        # log(Alpha) used for the IFT
            'alpha_er'      : alpha_sd,     # Uncertainty in log(alpha)
            'evidence'      : evidence,     # Evidence of solution
            'evidence_er'   : ev_sd,        # Uncertainty in evidence of solution
            'qmin'          : q[0],         # Minimum q
            'qmax'          : q[-1],        # Maximum q
            'algorithm'     : 'BIFT',       # Lets us know what algorithm was used to find the IFT
            'filename'      : os.path.splitext(filename)[0]+'.ift'
            }

        iftm = SASM.IFTM(pr, r, err_interp, i, q, err, fit, results, fit_extrap, q_extrap)

    else:
        if queue is not None:
            queue.put({'failed' : True})
        return None

    return iftm
