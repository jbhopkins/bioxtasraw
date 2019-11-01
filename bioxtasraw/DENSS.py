"""
Created on May 17, 2018

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

The purpose of this module is to contain the DENSS algorithm.

Much of the code is from the DENSS source code, released here:
    https://github.com/tdgrant1/denss
That code was released under GPL V3. The original author is Thomas Grant.

This code matches that as of 5/21/19, commit 1967ae6, version 1.4.9
"""

from __future__ import absolute_import, division, print_function, unicode_literals
from builtins import object, range, map, zip
from io import open

import os
import time
import ast
import logging
from functools import partial
import multiprocessing
import struct
import datetime
import traceback
import sys
from functools import reduce

import numpy as np
from scipy import optimize, ndimage
import scipy.interpolate as interpolate

import RAWCustomCtrl

def chi2(exp, calc, sig):
    """Return the chi2 discrepancy between experimental and calculated data"""
    return np.sum(np.square(exp - calc) / np.square(sig))

def center_rho(rho, centering="com", return_shift=False):
    """Move electron density map so its center of mass aligns with the center of the grid

    centering - which part of the density to center on. By default, center on the
                center of mass ("com"). Can also center on maximum density value ("max").
    """
    ne_rho= np.sum((rho))
    if centering == "max":
        rhocom = np.unravel_index(rho.argmax(), rho.shape)
    else:
        rhocom = np.array(ndimage.measurements.center_of_mass(rho))
    gridcenter = np.array(rho.shape)/2.
    shift = gridcenter-rhocom
    rho = ndimage.interpolation.shift(rho,shift,order=3,mode='wrap')
    rho = rho*ne_rho/np.sum(rho)
    if return_shift:
        return rho, shift
    else:
        return rho

def rho2rg(rho, r, support, dx):
    """Calculate radius of gyration from an electron density map."""

    rhocom = (np.array(ndimage.measurements.center_of_mass(rho))-np.array(rho.shape)/2.)*dx
    rg2 = np.sum(r[support]**2*rho[support])/np.sum(rho[support])
    rg2 = rg2 - np.linalg.norm(rhocom)**2
    rg = np.sign(rg2)*np.abs(rg2)**0.5

    return rg

def denss(q, I, sigq, dmax, ne=None, voxel=5., oversampling=3., limit_dmax=False,
    limit_dmax_steps=[500], recenter=True, recenter_steps=None,
    recenter_mode="com", positivity=True, extrapolate=True, output="map",
    steps=None, seed=None,  minimum_density=None,  maximum_density=None,
    flatten_low_density=True, rho_start=None, shrinkwrap=True,
    shrinkwrap_sigma_start=3, shrinkwrap_sigma_end=1.5,
    shrinkwrap_sigma_decay=0.99, shrinkwrap_threshold_fraction=0.2,
    shrinkwrap_iter=20, shrinkwrap_minstep=100, chi_end_fraction=0.01,
    write_xplor_format=False, write_freq=100, enforce_connectivity=True,
    enforce_connectivity_steps=[500], cutout=True, quiet=False, ncs=0,
    ncs_steps=[500],ncs_axis=1, abort_event=None, my_logger=logging.getLogger(),
    path='.', gui=False):
    """Calculate electron density from scattering data."""
    if abort_event is not None:
        if abort_event.is_set():
            my_logger.info('Aborted!')
            return []

    fprefix = os.path.join(path, output)

    D = dmax

    my_logger.info('q range of input data: %3.3f < q < %3.3f', q.min(), q.max())
    my_logger.info('Maximum dimension: %3.3f', D)
    my_logger.info('Sampling ratio: %3.3f', oversampling)
    my_logger.info('Requested real space voxel size: %3.3f', voxel)
    my_logger.info('Number of electrons: %3.3f', ne)
    my_logger.info('Limit Dmax: %s', limit_dmax)
    my_logger.info('Limit Dmax Steps: %s', limit_dmax_steps)
    my_logger.info('Recenter: %s', recenter)
    my_logger.info('Recenter Steps: %s', recenter_steps)
    my_logger.info('Recenter Mode: %s', recenter_mode)
    my_logger.info('NCS: %s', ncs)
    my_logger.info('NCS Steps: %s', ncs_steps)
    my_logger.info('NCS Axis: %s', ncs_axis)
    my_logger.info('Positivity: %s', positivity)
    my_logger.info('Minimum Density: %s', minimum_density)
    my_logger.info('Maximum Density: %s', maximum_density)
    my_logger.info('Extrapolate high q: %s', extrapolate)
    my_logger.info('Shrinkwrap: %s', shrinkwrap)
    my_logger.info('Shrinkwrap sigma start: %s', shrinkwrap_sigma_start)
    my_logger.info('Shrinkwrap sigma end: %s', shrinkwrap_sigma_end)
    my_logger.info('Shrinkwrap sigma decay: %s', shrinkwrap_sigma_decay)
    my_logger.info('Shrinkwrap threshold fraction: %s', shrinkwrap_threshold_fraction)
    my_logger.info('Shrinkwrap iterations: %s', shrinkwrap_iter)
    my_logger.info('Shrinkwrap starting step: %s', shrinkwrap_minstep)
    my_logger.info('Enforce connectivity: %s', enforce_connectivity)
    my_logger.info('Enforce connectivity steps: %s', enforce_connectivity_steps)
    my_logger.info('Chi2 end fraction: %3.3e', chi_end_fraction)

    #Initialize variables

    side = oversampling*D
    halfside = side//2

    n = int(side/voxel)
    #want n to be even for speed/memory optimization with the FFT, ideally a power of 2, but wont enforce that
    if n%2==1:
        n += 1
    #store n for later use if needed
    nbox = n

    dx = side/n
    dV = dx**3
    V = side**3
    x_ = np.linspace(-halfside,halfside,n)
    x,y,z = np.meshgrid(x_,x_,x_,indexing='ij')
    r = np.sqrt(x**2 + y**2 + z**2)

    df = 1./side
    qx_ = np.fft.fftfreq(x_.size)*n*df*2*np.pi
    qx, qy, qz = np.meshgrid(qx_,qx_,qx_,indexing='ij')
    qr = np.sqrt(qx**2+qy**2+qz**2)
    qmax = np.max(qr)
    qstep = np.min(qr[qr>0])
    nbins = int(qmax/qstep)
    qbins = np.linspace(0,nbins*qstep,nbins+1)

    #create modified qbins and put qbins in center of bin rather than at left edge of bin.
    qbinsc = np.copy(qbins)
    qbinsc[1:] += qstep/2.

    #create an array labeling each voxel according to which qbin it belongs
    qbin_labels = np.searchsorted(qbins,qr,"right")
    qbin_labels -= 1

    #allow for any range of q data
    qdata = qbinsc[np.where( (qbinsc>=q.min()) & (qbinsc<=q.max()) )]
    Idata = np.interp(qdata,q,I)
    if extrapolate:
        qextend = qbinsc[qbinsc>=qdata.max()]
        Iextend = qextend**-4
        Iextend = Iextend/Iextend[0] * Idata[-1]
        qdata = np.concatenate((qdata,qextend[1:]))
        Idata = np.concatenate((Idata,Iextend[1:]))

    #create list of qbin indices just in region of data for later F scaling
    qbin_args = np.in1d(qbinsc,qdata,assume_unique=True)
    sigqdata = np.interp(qdata,q,sigq)

    scale_factor = ne**2 / Idata[0]
    Idata *= scale_factor
    sigqdata *= scale_factor
    I *= scale_factor
    sigq *= scale_factor

    if steps == 'None' or steps is None or steps < 1:
        stepsarr = np.concatenate((enforce_connectivity_steps,[shrinkwrap_minstep]))
        maxec = np.max(stepsarr)
        steps = int(shrinkwrap_iter * (np.log(shrinkwrap_sigma_end/shrinkwrap_sigma_start)/np.log(shrinkwrap_sigma_decay)) + maxec)
        #add enough steps for convergence after shrinkwrap is finished
        #something like 7000 seems reasonable, likely will finish before that on its own
        #then just make a round number when using defaults
        steps += 7621
    else:
        steps = np.int(steps)

    Imean = np.zeros((steps+1,len(qbins)))
    chi = np.zeros((steps+1))
    rg = np.zeros((steps+1))
    supportV = np.zeros((steps+1))
    support = np.ones(x.shape,dtype=bool)

    if seed is None:
        #Have to reset the random seed to get a random in different from other processes
        prng = np.random.RandomState()
        seed = prng.randint(2**31-1)
    else:
        seed = int(seed)

    prng = np.random.RandomState(seed)

    if rho_start is not None:
        rho = rho_start
    else:
        rho = prng.random_sample(size=x.shape) #- 0.5

    sigma = shrinkwrap_sigma_start
    #convert density values to absolute number of electrons
    #since FFT and rho given in electrons, not density, until converted at the end
    rho_min = minimum_density
    rho_max = maximum_density
    if rho_min is not None:
        rho_min *= dV
        #print rho_min
    if rho_max is not None:
        rho_max *= dV
        #print rho_max

    my_logger.info('Maximum number of steps: %i', steps)
    my_logger.info('Grid size (voxels): %i x %i x %i', n, n, n)
    my_logger.info('Real space box width (angstroms): %3.3f', side)
    my_logger.info('Real space box range (angstroms): %3.3f < x < %3.3f', x_.min(), x_.max())
    my_logger.info('Real space box volume (angstroms^3): %3.3f', V)
    my_logger.info('Real space voxel size (angstroms): %3.3f', dx)
    my_logger.info('Real space voxel volume (angstroms^3): %3.3f', dV)
    my_logger.info('Reciprocal space box width (angstroms^(-1)): %3.3f', qx_.max()-qx_.min())
    my_logger.info('Reciprocal space box range (angstroms^(-1)): %3.3f < qx < %3.3f', qx_.min(), qx_.max())
    my_logger.info('Maximum q vector (diagonal) (angstroms^(-1)): %3.3f', qr.max())
    my_logger.info('Number of q shells: %i', nbins)
    my_logger.info('Width of q shells (angstroms^(-1)): %3.3f', qstep)
    my_logger.info('Random seed: %i', seed)
    if not quiet:
        if gui:
            my_logger.info("\n Step     Chi2     Rg    Support Volume")
            my_logger.info(" ----- --------- ------- --------------")
        else:
            print("\n Step     Chi2     Rg    Support Volume")
            print(" ----- --------- ------- --------------")

    for j in range(steps):
        if abort_event is not None:
            if abort_event.is_set():
                my_logger.info('Aborted!')
                return []

        F = np.fft.fftn(rho)

        #APPLY RECIPROCAL SPACE RESTRAINTS
        #calculate spherical average of intensities from 3D Fs
        I3D = np.abs(F)**2
        Imean[j] = ndimage.mean(I3D, labels=qbin_labels, index=np.arange(0,qbin_labels.max()+1))
        """
        if j==0:
            np.savetxt(fprefix+'_step0_saxs.dat',np.vstack((qbinsc,Imean[j],Imean[j]*.05)).T,delimiter=" ",fmt="%.5e")
            write_mrc(rho,side,fprefix+"_step"+str(j)+".mrc")
        """

        #scale Fs to match data
        factors = np.ones((len(qbins)))
        factors[qbin_args] = np.sqrt(Idata/Imean[j,qbin_args])
        F *= factors[qbin_labels]
        chi[j] = np.sum(((Imean[j,qbin_args]-Idata)/sigqdata)**2)/qbin_args.size
        interp = interpolate.interp1d(qbinsc, Imean[j], kind='cubic',fill_value="extrapolate")
        I4chi = interp(q)
        chi[j] = np.sum(((I4chi-I)/sigq)**2)/len(q)

        #APPLY REAL SPACE RESTRAINTS
        rhoprime = np.fft.ifftn(F,rho.shape)
        rhoprime = rhoprime.real
        if j%write_freq == 0:
            if write_xplor_format:
                write_xplor(rhoprime/dV, side, fprefix+"_current.xplor")
            write_mrc(rhoprime/dV, side, fprefix+"_current.mrc")
        rg[j] = rho2rg(rhoprime,r=r,support=support,dx=dx)
        newrho = np.zeros_like(rho)

        #Error Reduction
        newrho[support] = rhoprime[support]
        newrho[~support] = 0.0

        #enforce positivity by making all negative density points zero.
        if positivity:
            netmp = np.sum(newrho)
            newrho[newrho<0] = 0.0
            if np.sum(newrho) != 0:
                newrho *= netmp / np.sum(newrho)

        if flatten_low_density:
            newrho[np.abs(newrho)<0.01*dV] = 0

        #allow further bounds on density, rather than just positivity
        if rho_min is not None:
            netmp = np.sum(newrho)
            newrho[newrho<rho_min] = rho_min
            if np.sum(newrho) != 0:
                newrho *= netmp / np.sum(newrho)

        if rho_max is not None:
            netmp = np.sum(newrho)
            newrho[newrho>rho_max] = rho_max
            if np.sum(newrho) != 0:
                newrho *= netmp / np.sum(newrho)

        #apply non-crystallographic symmetry averaging
        if ncs != 0 and j in ncs_steps:
            newrho = align2xyz(newrho)

        if ncs != 0 and j in [stepi+1 for stepi in ncs_steps]:
            degrees = 360./ncs
            if ncs_axis == 1: axes=(1,2)
            if ncs_axis == 2: axes=(0,2)
            if ncs_axis == 3: axes=(0,1)
            newrhosym = np.zeros_like(newrho)
            for nrot in range(0,ncs+1):
                newrhosym += ndimage.rotate(newrho,degrees*nrot,axes=axes,reshape=False)
            newrho = newrhosym/ncs

        #update support using shrinkwrap method
        if recenter and j in recenter_steps:
            if recenter_mode == "max":
                rhocom = np.unravel_index(newrho.argmax(), newrho.shape)
            else:
                rhocom = np.array(ndimage.measurements.center_of_mass(newrho))
            gridcenter = np.array(rho.shape)/2.
            shift = gridcenter-rhocom
            shift = shift.astype(int)
            newrho = np.roll(np.roll(np.roll(newrho, shift[0], axis=0), shift[1], axis=1), shift[2], axis=2)
            support = np.roll(np.roll(np.roll(support, shift[0], axis=0), shift[1], axis=1), shift[2], axis=2)

        if shrinkwrap and j >= shrinkwrap_minstep and j%shrinkwrap_iter==1:
            if recenter_mode == "max":
                rhocom = np.unravel_index(newrho.argmax(), newrho.shape)
            else:
                rhocom = np.array(ndimage.measurements.center_of_mass(newrho))

            gridcenter = np.array(rho.shape)/2.
            shift = gridcenter-rhocom
            shift = shift.astype(int)
            newrho = np.roll(np.roll(np.roll(newrho, shift[0], axis=0), shift[1], axis=1), shift[2], axis=2)

            if j>500:
                tmp = np.abs(newrho)
            else:
                tmp = newrho

            rho_blurred = ndimage.filters.gaussian_filter(tmp,sigma=sigma,mode='wrap')
            support = np.zeros(rho.shape,dtype=bool)
            support[rho_blurred >= shrinkwrap_threshold_fraction*rho_blurred.max()] = True

            if sigma > shrinkwrap_sigma_end:
                sigma = shrinkwrap_sigma_decay*sigma

        if enforce_connectivity and j in enforce_connectivity_steps:
            if recenter_mode == "max":
                rhocom = np.unravel_index(newrho.argmax(), newrho.shape)
            else:
                rhocom = np.array(ndimage.measurements.center_of_mass(newrho))

            gridcenter = np.array(rho.shape)/2.
            shift = gridcenter-rhocom
            shift = shift.astype(int)
            newrho = np.roll(np.roll(np.roll(newrho, shift[0], axis=0), shift[1], axis=1), shift[2], axis=2)

            #first run shrinkwrap to define the features
            tmp = np.abs(newrho)
            rho_blurred = ndimage.filters.gaussian_filter(tmp,sigma=sigma,mode='wrap')
            support = np.zeros(rho.shape,dtype=bool)
            support[rho_blurred >= shrinkwrap_threshold_fraction*rho_blurred.max()] = True

            #label the support into separate segments based on a 3x3x3 grid
            struct = ndimage.generate_binary_structure(3, 3)
            labeled_support, num_features = ndimage.label(support, structure=struct)
            sums = np.zeros((num_features))
            if not quiet:
                if not gui:
                    print(num_features)

            #find the feature with the greatest number of electrons
            for feature in range(num_features):
                sums[feature-1] = np.sum(newrho[labeled_support==feature])
            big_feature = np.argmax(sums)+1

            #remove features from the support that are not the primary feature
            support[labeled_support != big_feature] = False
            newrho[~support] = 0

            #reset the support to be the entire grid again
            support = np.ones(rho.shape,dtype=bool)

        if limit_dmax and j in limit_dmax_steps:
            #support[r>0.6*D] = False
            #if np.sum(support) <= 0:
            #    support = np.ones(rho.shape,dtype=bool)
            #gradually (smooth like a gaussian maybe) decrease density from center
            #set width of gradual decrease window to be +20 percent of dmax
            #the equation of that line works out to be (where rho goes from 1 down to 0):
            #rho = -1/(0.2*D)*r + 6
            newrho[(r>D)&(r<1.2*D)] *= (-1.0/(0.2*D)*r[(r>D)&(r<1.2*D)] + 6)
            newrho[r>=1.2*D] = 0

        supportV[j] = np.sum(support)*dV

        if not quiet:
            if gui:
                my_logger.info("% 5i % 4.2e % 3.2f       % 5i          ", j, chi[j], rg[j], supportV[j])
            else:
                sys.stdout.write("\r% 5i % 4.2e % 3.2f       % 5i          " % (j, chi[j], rg[j], supportV[j]))
                sys.stdout.flush()

        if j > 101 + shrinkwrap_minstep and np.std(chi[j-100:j]) < chi_end_fraction * np.median(chi[j-100:j]):
            break

        rho = newrho

    F = np.fft.fftn(rho)
    #calculate spherical average intensity from 3D Fs
    Imean[j+1] = ndimage.mean(np.abs(F)**2, labels=qbin_labels, index=np.arange(0,qbin_labels.max()+1))
    #chi[j+1] = np.sum(((Imean[j+1,qbin_args]-Idata)/sigqdata)**2)/qbin_args.size

    #scale Fs to match data
    factors = np.ones((len(qbins)))
    factors[qbin_args] = np.sqrt(Idata/Imean[j+1,qbin_args])
    F *= factors[qbin_labels]
    rho = np.fft.ifftn(F,rho.shape)
    rho = rho.real

    #negative images yield the same scattering, so flip the image
    #to have more positive than negative values if necessary
    #to make sure averaging is done properly
    #whether theres actually more positive than negative values
    #is ambiguous, but this ensures all maps are at least likely
    #the same designation when averaging
    if np.sum(np.abs(rho[rho<0])) > np.sum(rho[rho>0]):
        rho *= -1

    #scale total number of electrons
    if ne is not None:
        rho *= ne / np.sum(rho)

    rg[j+1] = rho2rg(rho=rho,r=r,support=support,dx=dx)
    supportV[j+1] = supportV[j]

    #change rho to be the electron density in e-/angstroms^3, rather than number of electrons,
    #which is what the FFT assumes
    rho /= dV

    if cutout:
        #here were going to cut rho out of the large real space box
        #to the voxels that contain the particle
        #use D to estimate particle size
        #assume the particle is in the center of the box
        #calculate how many voxels needed to contain particle of size D
        #use bigger than D to make sure we don't crop actual particle in case its larger than expected
        #lets clip it to a maximum of 2*D to be safe
        nD = int(2*D/dx)+1
        #make sure final box will still have even samples
        if nD%2==1:
            nD += 1

        nmin = nbox//2 - nD//2
        nmax = nbox//2 + nD//2 + 2
        #create new rho array containing only the particle
        newrho = rho[nmin:nmax,nmin:nmax,nmin:nmax]
        rho = newrho
        #do the same for the support
        newsupport = support[nmin:nmax,nmin:nmax,nmin:nmax]
        support = newsupport
        #update side to new size of box
        side = dx * (nmax-nmin)

    if write_xplor_format:
        write_xplor(rho,side,fprefix+".xplor")
        write_xplor(np.ones_like(rho)*support, side, fprefix+"_support.xplor")

    write_mrc(rho,side,fprefix+".mrc")
    write_mrc(np.ones_like(rho)*support,side, fprefix+"_support.mrc")

    #Write some more output files
    fit = np.zeros(( len(qbinsc),5 ))
    fit[:len(qdata),0] = qdata
    fit[:len(Idata),1] = Idata
    fit[:len(sigqdata),2] = sigqdata
    fit[:len(qbinsc),3] = qbinsc
    fit[:len(Imean[j+1]),4] = Imean[j+1]
    np.savetxt(fprefix+'_map.fit', fit, delimiter=' ', fmt='%.5e'.encode('ascii'),
        header='q(data),I(data),error(data),q(density),I(density)')

    np.savetxt(fprefix+'_stats_by_step.dat',np.vstack((chi, rg, supportV)).T,
        delimiter=" ", fmt="%.5e".encode('ascii'), header='Chi2 Rg SupportVolume')

    my_logger.info('FINISHED DENSITY REFINEMENT')
    my_logger.info('Number of steps: %i', j)
    my_logger.info('Final Chi2: %.3e', chi[j])
    my_logger.info('Final Rg: %3.3f', rg[j+1])
    my_logger.info('Final Support Volume: %3.3f', supportV[j+1])
    # my_logger.info('END')

    #return original unscaled values of Idata (and therefore Imean) for comparison with real data
    Idata /= scale_factor
    sigqdata /= scale_factor
    Imean /= scale_factor
    I /= scale_factor
    sigq /= scale_factor

    return qdata, Idata, sigqdata, qbinsc, Imean[j], chi, rg, supportV, rho, side

def euler_grid_search(refrho, movrho, topn=1, abort_event=None):
    """Simple grid search on uniformly sampled sphere to optimize alignment.
        Return the topn candidate maps (default=1, i.e. the best candidate)."""
    #taken from https://stackoverflow.com/a/44164075/2836338

    num_pts = 18 #~20 degrees between points
    indices = np.arange(0, num_pts, dtype=float) + 0.5
    phi = np.arccos(1 - 2*indices/num_pts)
    theta = np.pi * (1 + 5**0.5) * indices
    scores = np.zeros((len(phi),len(theta)))
    for p in range(len(phi)):
        for t in range(len(theta)):
            scores[p,t] = 1./minimize_rho_score(T=[phi[p],theta[t],0,0,0,0],refrho=np.abs(refrho),movrho=np.abs(movrho))

            if abort_event is not None:
                if abort_event.is_set():
                    return None, None

    #best_pt = np.unravel_index(scores.argmin(), scores.shape)
    best_pt = largest_indices(scores, topn)
    best_scores = scores[best_pt]
    movrhos = np.zeros((topn,movrho.shape[0],movrho.shape[1],movrho.shape[2]))

    for i in range(topn):
        movrhos[i] = transform_rho(movrho, T=[phi[best_pt[0][i]],theta[best_pt[1][i]],0,0,0,0])

        if abort_event is not None:
            if abort_event.is_set():
                return movrhos, best_scores

    return movrhos, best_scores

def largest_indices(a, n):
    """Returns the n largest indices from a numpy array."""
    flat = a.flatten()
    indices = np.argpartition(flat, -n)[-n:]
    indices = indices[np.argsort(-flat[indices])]
    return np.unravel_index(indices, a.shape)

def coarse_then_fine_alignment(refrho, movrho, topn=1,
    abort_event=None):
    """Course alignment followed by fine alignment.
        Select the topn candidates from the grid search
        and minimize each, selecting the best fine alignment.
        """
    movrhos, scores = euler_grid_search(refrho, movrho, topn=topn,
        abort_event=abort_event)

    if abort_event is not None:
        if abort_event.is_set():
            return None, None

    for i in range(movrhos.shape[0]):
        movrhos[i], scores[i] = minimize_rho(refrho, movrhos[i])

        if abort_event is not None:
            if abort_event.is_set():
                return None, None

    best_i = np.argmax(scores)
    movrho = movrhos[best_i]
    score = scores[best_i]
    return movrho, score

def minimize_rho(refrho, movrho, T = np.zeros(6)):
    """Optimize superposition of electron density maps. Move movrho to refrho."""
    bounds = np.zeros(12).reshape(6,2)
    bounds[:3,0] = -20*np.pi
    bounds[:3,1] = 20*np.pi
    bounds[3:,0] = -5
    bounds[3:,1] = 5
    save_movrho = np.copy(movrho)
    save_refrho = np.copy(refrho)
    result = optimize.fmin_l_bfgs_b(minimize_rho_score, T, factr= 0.1,
        maxiter=100, maxfun=200, epsilon=0.05,
        args=(np.abs(refrho),np.abs(movrho)), approx_grad=True)
    Topt = result[0]
    newrho = transform_rho(save_movrho, Topt)
    finalscore = 1./rho_overlap_score(save_refrho,newrho)
    return newrho, finalscore

def minimize_rho_score(T, refrho, movrho):
    """Scoring function for superposition of electron density maps.

        refrho - fixed, reference rho
        movrho - moving rho
        T - 6-element list containing alpha, beta, gamma, Tx, Ty, Tz in that order
        to move movrho by.
        """
    newrho = transform_rho(movrho, T)
    score = rho_overlap_score(refrho,newrho)
    return score

def rho_overlap_score(rho1,rho2):
    """Scoring function for superposition of electron density maps."""
    n=2*np.sum(np.abs(rho1*rho2))
    d=(2*np.sum(rho1**2)**0.5*np.sum(rho2**2)**0.5)
    score = n/d
    #1/score for least squares minimization, i.e. want to minimize, not maximize score
    return 1./score

def transform_rho(rho, T, order=1):
    """ Rotate and translate electron density map by T vector.

        T = [alpha, beta, gamma, x, y, z], angles in radians
        order = interpolation order (0-5)
    """
    ne_rho= np.sum((rho))
    R = euler2matrix(T[0],T[1],T[2])
    c_in = np.array(ndimage.measurements.center_of_mass(rho))
    c_out = np.array(rho.shape)/2.
    offset = c_in-c_out.dot(R)
    rho = ndimage.interpolation.affine_transform(rho,R.T, order=order,
        offset=offset, output=np.float64, mode='wrap')
    rho = ndimage.interpolation.shift(rho,T[3:], order=order, mode='wrap',
        output=np.float64)
    rho *= ne_rho/np.sum(rho)
    return rho

def euler2matrix(alpha=0.0,beta=0.0,gamma=0.0):
    """Convert Euler angles alpha, beta, gamma to a standard rotation matrix.

        alpha - yaw, counterclockwise rotation about z-axis, upper-left quadrant
        beta - pitch, counterclockwise rotation about y-axis, four-corners
        gamma - roll, counterclockwise rotation about x-axis, lower-right quadrant
        all angles given in radians

        """
    R = []
    cosa = np.cos(alpha)
    sina = np.sin(alpha)
    cosb = np.cos(beta)
    sinb = np.sin(beta)
    cosg = np.cos(gamma)
    sing = np.sin(gamma)
    R.append(np.array(
        [[cosa, -sina, 0],
        [sina, cosa, 0],
        [0, 0, 1]]))
    R.append(np.array(
        [[cosb, 0, sinb],
        [0, 1, 0],
        [-sinb, 0, cosb]]))
    R.append(np.array(
        [[1, 0, 0],
        [0, cosg, -sing],
        [0, sing, cosg]]))
    return reduce(np.dot,R[::-1])

def inertia_tensor(rho,side):
    """Calculate the moment of inertia tensor for the given electron density map."""
    halfside = side/2.
    n = rho.shape[0]
    x_ = np.linspace(-halfside,halfside,n)
    x,y,z = np.meshgrid(x_,x_,x_,indexing='ij')
    Ixx = np.sum((y**2 + z**2)*rho)
    Iyy = np.sum((x**2 + z**2)*rho)
    Izz = np.sum((x**2 + y**2)*rho)
    Ixy = -np.sum(x*y*rho)
    Iyz = -np.sum(y*z*rho)
    Ixz = -np.sum(x*z*rho)
    I = np.array([[Ixx, Ixy, Ixz],
                  [Ixy, Iyy, Iyz],
                  [Ixz, Iyz, Izz]])
    return I

def principal_axes(I):
    """Calculate the principal inertia axes and order them Ia < Ib < Ic."""
    w,v = np.linalg.eigh(I)
    return w,v

def align2xyz(rho, return_transform=False):
    """ Align rho such that principal axes align with XYZ axes."""
    side = 1.0
    ne_rho = np.sum(rho)
    #shift refrho to the center
    rhocom = np.array(ndimage.measurements.center_of_mass(rho))
    gridcenter = np.array(rho.shape)/2.
    shift = gridcenter-rhocom
    rho = ndimage.interpolation.shift(rho,shift,order=3,mode='wrap')
    #calculate, save and perform rotation of refrho to xyz for later
    I = inertia_tensor(rho, side)
    w,v = principal_axes(I)
    R = v.T
    refR = np.copy(R)
    refshift = np.copy(shift)
    #apparently need to run this a few times to get good alignment
    #maybe due to interpolation artifacts?
    for i in range(3):
        I = inertia_tensor(rho, side)
        w,v = np.linalg.eigh(I) #principal axes
        R = v.T #rotation matrix
        c_in = np.array(ndimage.measurements.center_of_mass(rho))
        c_out = np.array(rho.shape)/2.
        offset=c_in-c_out.dot(R)
        rho = ndimage.interpolation.affine_transform(rho, R.T, order=3,
            offset=offset, mode='wrap')
    rho *= ne_rho/np.sum(rho)
    if return_transform:
        return rho, refR, refshift
    else:
        return rho

def generate_enantiomers(rho):
    """ Generate all enantiomers of given density map.
        Output maps are flipped over x,y,z,xy,yz,zx, and xyz, respectively.
        Assumes rho is prealigned to xyz.
        """
    rho_xflip = rho[::-1,:,:]
    """
    rho_yflip = rho[:,::-1,:]
    rho_zflip = rho[:,:,::-1]
    rho_xyflip = rho_xflip[:,::-1,:]
    rho_yzflip = rho_yflip[:,:,::-1]
    rho_zxflip = rho_zflip[::-1,:,:]
    rho_xyzflip = rho_xyflip[:,:,::-1]
    enans = np.array([rho,rho_xflip,rho_yflip,rho_zflip,
                      rho_xyflip,rho_yzflip,rho_zxflip,
                      rho_xyzflip])
    """
    enans = np.array([rho,rho_xflip])
    return enans


def align(refrho, movrho, abort_event=None):
    """ Align second electron density map to the first."""
    if abort_event is not None:
        if abort_event.is_set():
            return None, None

    ne_rho = np.sum((movrho))
    #movrho, score = minimize_rho(refrho, movrho)
    movrho, score = coarse_then_fine_alignment(refrho, movrho, topn=5,
        abort_event=abort_event)

    if movrho is not None:
        movrho *= ne_rho/np.sum(movrho)

    return movrho, score

def select_best_enantiomers(rhos, refrho=None, cores=1, avg_queue=None,
    abort_event=None):
    """ Select the best enantiomer from each map in the set (or a single map).
        refrho should not be binary averaged from the original
        denss maps, since that would likely lose handedness.
        By default, refrho will be set to the first map."""
    if rhos.ndim == 3:
        rhos = rhos[np.newaxis,...]
    #can't have nested parallel jobs, so run enantiomer selection
    #in parallel, but run each map in a loop
    if refrho is None:
        refrho = rhos[0]
    xyz_refrho, refR, refshift = align2xyz(refrho, return_transform=True)
    scores = np.zeros(rhos.shape[0])
    for i in range(rhos.shape[0]):
        if abort_event is not None:
            if abort_event.is_set():
                return None, None
        if avg_queue is not None:
            avg_queue.put_nowait('Selecting enantiomer for model {}\n'.format(i+1))
        #align rho to xyz and generate the enantiomers, then shift/rotate each enan
        #by inverse of refrho, then perform minimization around the original refrho location,
        #and select the best enantiomer from that set,
        #rather than doing the minimization around the xyz_refrho location
        #and then shifting the final best enan back.
        #this way the final rotation is defined by the optimized score, not
        #by the inverse refrho xyz alignment, which appears to suffer from
        #interpolation artifacts
        xyz_rho = align2xyz(rhos[i])
        enans = generate_enantiomers(xyz_rho)
        #now rotate rho by the inverse of the refrho rotation for each enantiomer
        R = np.linalg.inv(refR)
        c_in = np.array(ndimage.measurements.center_of_mass(rhos[i]))
        c_out = np.array(rhos[i].shape)/2.
        offset = c_in-c_out.dot(R)
        for j in range(len(enans)):
            enans[j] = ndimage.interpolation.affine_transform(enans[j],R.T,order=3,offset=offset,mode='wrap')
            enans[j] = ndimage.interpolation.shift(enans[j],-refshift,order=3,mode='wrap')
        #now minimize each enan around the original refrho location
        pool = multiprocessing.Pool(cores)
        try:
            mapfunc = partial(align, refrho)
            results = pool.map(mapfunc, enans)
            pool.close()
            pool.join()
        except KeyboardInterrupt:
            pool.terminate()
            pool.close()
            raise

        #now select the best enantiomer and set it as the new rhos[i]
        enans = np.array([results[k][0] for k in range(len(results))])
        enans_scores = np.array([results[k][1] for k in range(len(results))])

        best_i = np.argmax(enans_scores)
        rhos[i], scores[i] = enans[best_i], enans_scores[best_i]
        if avg_queue is not None:
            avg_queue.put_nowait('Best enantiomer for model {} has score {}\n'.format(i+1, round(scores[i],3)))

    return rhos, scores

def align_multiple(refrho, rhos, cores=1, abort_event=None):
    """ Align multiple (or a single) maps to the reference."""
    if rhos.ndim == 3:
        rhos = rhos[np.newaxis,...]
    #first, center all the rhos, then shift them to where refrho is
    cen_refrho, refshift = center_rho(refrho, return_shift=True)
    for i in range(rhos.shape[0]):
        rhos[i] = center_rho(rhos[i])
        ne_rho = np.sum(rhos[i])
        #now shift each rho back to where refrho was originally
        rhos[i] = ndimage.interpolation.shift(rhos[i],-refshift,order=3,mode='wrap')
        rhos[i] *= ne_rho/np.sum(rhos[i])

    if abort_event is not None:
        if abort_event.is_set():
            return None, None

    pool = multiprocessing.Pool(cores)
    try:
        mapfunc = partial(align, refrho)
        results = pool.map(mapfunc, rhos)
        pool.close()
        pool.join()
    except KeyboardInterrupt:
        pool.terminate()
        pool.close()
        raise

    rhos = np.array([results[i][0] for i in range(len(results))])
    scores = np.array([results[i][1] for i in range(len(results))])

    return rhos, scores

def average_two(rho1, rho2, abort_event=None):
    """ Align two electron density maps and return the average."""
    rho2, score = align(rho1, rho2, abort_event=abort_event)
    average_rho = (rho1+rho2)/2.
    return average_rho

def multi_average_two(niter, **kwargs):
    """ Wrapper script for averaging two maps for multiprocessing."""
    kwargs['rho1']=kwargs['rho1'][niter]
    kwargs['rho2']=kwargs['rho2'][niter]
    time.sleep(1)
    return average_two(**kwargs)

def average_pairs(rhos, cores=1, abort_event=None):
    """ Average pairs of electron density maps, second half to first half."""
    #create even/odd pairs, odds are the references
    rho_args = {'rho1':rhos[::2], 'rho2':rhos[1::2], 'abort_event': abort_event}
    pool = multiprocessing.Pool(cores)
    try:
        mapfunc = partial(multi_average_two, **rho_args)
        average_rhos = pool.map(mapfunc, list(range(rhos.shape[0]//2)))
        pool.close()
        pool.join()
    except KeyboardInterrupt:
        pool.terminate()
        pool.close()
        raise

    return np.array(average_rhos)

def binary_average(rhos, cores=1, abort_event=None):
    """ Generate a reference electron density map using binary averaging."""
    twos = 2**np.arange(20)
    nmaps = np.max(twos[twos<=rhos.shape[0]])
    levels = int(np.log2(nmaps))-1
    rhos = rhos[:nmaps]
    for level in range(levels):
         rhos = average_pairs(rhos, cores, abort_event=abort_event)
    refrho = center_rho(rhos[0])
    return refrho

def calc_fsc(rho1, rho2, side):
    """ Calculate the Fourier Shell Correlation between two electron density maps."""
    df = 1.0/side
    n = rho1.shape[0]
    qx_ = np.fft.fftfreq(n)*n*df
    qx, qy, qz = np.meshgrid(qx_,qx_,qx_,indexing='ij')
    qx_max = qx.max()
    qr = np.sqrt(qx**2+qy**2+qz**2)
    qmax = np.max(qr)
    qstep = np.min(qr[qr>0])
    nbins = int(qmax/qstep)
    qbins = np.linspace(0,nbins*qstep,nbins+1)
    #create an array labeling each voxel according to which qbin it belongs
    qbin_labels = np.searchsorted(qbins, qr, "right")
    qbin_labels -= 1
    F1 = np.fft.fftn(rho1)
    F2 = np.fft.fftn(rho2)
    numerator = ndimage.sum(np.real(F1*np.conj(F2)), labels=qbin_labels,
        index=np.arange(0,qbin_labels.max()+1))
    term1 = ndimage.sum(np.abs(F1)**2, labels=qbin_labels,
        index=np.arange(0,qbin_labels.max()+1))
    term2 = ndimage.sum(np.abs(F2)**2, labels=qbin_labels,
        index=np.arange(0,qbin_labels.max()+1))
    denominator = (term1*term2)**0.5
    FSC = numerator/denominator
    qidx = np.where(qbins<qx_max)
    return  np.vstack((qbins[qidx],FSC[qidx])).T

def write_mrc(rho,side,filename="map.mrc"):
    """Write an MRC formatted electron density map.
       See here: http://www2.mrc-lmb.cam.ac.uk/research/locally-developed-software/image-processing-software/#image
    """
    xs, ys, zs = rho.shape
    nxstart = -xs//2+1
    nystart = -ys//2+1
    nzstart = -zs//2+1
    side = np.atleast_1d(side)
    if len(side) == 1:
        a,b,c = side, side, side
    elif len(side) == 3:
        a,b,c = side
    else:
        print("Error. Argument 'side' must be float or 3-tuple")
    with open(filename, "wb") as fout:
        # NC, NR, NS, MODE = 2 (image : 32-bit reals)
        fout.write(struct.pack('<iiii', xs, ys, zs, 2))
        # NCSTART, NRSTART, NSSTART
        fout.write(struct.pack('<iii', nxstart, nystart, nzstart))
        # MX, MY, MZ
        fout.write(struct.pack('<iii', xs, ys, zs))
        # X length, Y, length, Z length
        fout.write(struct.pack('<fff', a, b, c))
        # Alpha, Beta, Gamma
        fout.write(struct.pack('<fff', 90.0, 90.0, 90.0))
        # MAPC, MAPR, MAPS
        fout.write(struct.pack('<iii', 1, 2, 3))
        # DMIN, DMAX, DMEAN
        fout.write(struct.pack('<fff', np.min(rho), np.max(rho), np.average(rho)))
        # ISPG, NSYMBT, mlLSKFLG
        fout.write(struct.pack('<iii', 1, 0, 0))
        # EXTRA
        fout.write(struct.pack('<'+'f'*12, 1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0))
        for i in range(0, 12):
            fout.write(struct.pack('<f', 0.0))

        # XORIGIN, YORIGIN, ZORIGIN
        fout.write(struct.pack('<fff', nxstart*(a/xs), nystart*(b/ys), nzstart*(c/zs)))
        # MAP
        fout.write('MAP ')
        # MACHST (little endian)
        fout.write(struct.pack('<BBBB', 0x44, 0x41, 0x00, 0x00))
        # RMS (std)
        fout.write(struct.pack('<f', np.std(rho)))
        # NLABL
        fout.write(struct.pack('<i', 0))
        # LABEL(20,10) 10 80-character text labels
        for i in range(0, 800):
            fout.write(struct.pack('<B', 0x00))

        # Write out data
        s = struct.pack('=%sf' % rho.size, *rho.flatten('F'))
        fout.write(s)

def write_xplor(rho,side,filename="map.xplor"):
    """Write an XPLOR formatted electron density map."""
    xs, ys, zs = rho.shape
    title_lines = ['REMARK FILENAME="'+filename+'"','REMARK DATE= '+str(datetime.datetime.today())]
    with open(filename,'wb') as f:
        f.write("\n")
        f.write("%8d !NTITLE\n" % len(title_lines))
        for line in title_lines:
            f.write("%-264s\n" % line)
        #f.write("%8d%8d%8d%8d%8d%8d%8d%8d%8d\n" % (xs,0,xs-1,ys,0,ys-1,zs,0,zs-1))
        f.write("%8d%8d%8d%8d%8d%8d%8d%8d%8d\n" % (xs,-xs/2+1,xs/2,ys,-ys/2+1,ys/2,zs,-zs/2+1,zs/2))
        f.write("% -.5E% -.5E% -.5E% -.5E% -.5E% -.5E\n" % (side,side,side,90,90,90))
        f.write("ZYX\n")
        for k in range(zs):
            f.write("%8s\n" % k)
            for j in range(ys):
                for i in range(xs):
                    if (i+j*ys) % 6 == 5:
                        f.write("% -.5E\n" % rho[i,j,k])
                    else:
                        f.write("% -.5E" % rho[i,j,k])
            f.write("\n")
        f.write("    -9999\n")
        f.write("  %.4E  %.4E" % (np.average(rho), np.std(rho)))


######################
# RAW specific stuff
######################

def runDenss(q, I, sigq, D, prefix, path, comm_list, my_lock, thread_num_q,
    wx_queue, abort_event, denss_settings, avg_model=None):
    my_lock.acquire()
    if avg_model is None:
        my_num = thread_num_q.get()
        den_queue, stop_event = comm_list[int(my_num)-1]
    else:
        my_num = '-1'
        den_queue, stop_event = comm_list[0]
    my_lock.release()

    #Check to see if things have been aborted
    if abort_event.is_set():
        stop_event.set()
        my_lock.acquire()
        if avg_model is None:
            wx_queue.put_nowait(['window %s'%(str(my_num)), 'Aborted!\n'])
            wx_queue.put_nowait(['finished', int(my_num)-1])
        else:
            wx_queue.put_nowait(['refine', 'Aborted!\n'])
        my_lock.release()
        return

    if avg_model is None:
        den_prefix = prefix+'_%s' %(my_num.zfill(2))
    else:
        den_prefix = '{}_refine'.format(prefix)

    #Remove old files, so they don't mess up the program
    log_name = den_prefix+'.log'
    xplor_names = [den_prefix+'_current.xplor', den_prefix+'.xplor',
        den_prefix+'_original.xplor', den_prefix+'_precentered.xplor',
        den_prefix+'_support.xplor']
    fit_name = den_prefix+'_map.fit'
    stats_name = den_prefix+'_stats_by_step.txt'
    saxs_name = den_prefix+'_step0_saxs.dat'
    image_names = [den_prefix+'_chis.png', den_prefix+'_fit.png',
        den_prefix+'_rgs.png', den_prefix+'_supportV.png']
    mrc_name = den_prefix+'.mrc'

    names = [log_name, fit_name, stats_name, saxs_name, mrc_name] + xplor_names + image_names

    old_files = [os.path.join(path, name) for name in names]

    for item in old_files:
        if os.path.exists(item):
            os.remove(item)

    #Run DENSS
    my_lock.acquire()
    if avg_model is None:
        wx_queue.put_nowait(['status', 'Starting DENSS run %s\n' %(my_num)])
    my_lock.release()

    my_logger = logging.getLogger(prefix)
    my_logger.setLevel(logging.DEBUG)
    my_logger.propagate = False
    my_logger.handlers = []

    my_fh = logging.FileHandler(os.path.join(path, den_prefix+'.log'), mode = 'w')
    my_fh.setLevel(logging.INFO)
    my_fh_formatter = logging.Formatter('%(asctime)s %(message)s', '%Y-%m-%d %I:%M:%S %p')
    my_fh.setFormatter(my_fh_formatter)

    my_sh = RAWCustomCtrl.CustomConsoleHandler(den_queue)
    my_sh.setLevel(logging.DEBUG)

    my_logger.addHandler(my_fh)
    my_logger.addHandler(my_sh)

    try:
        # Rename to match denss code
        denss_args = {
            'voxel'             : float(denss_settings['voxel']),
            'oversampling'      : float(denss_settings['oversample']),
            'limit_dmax'        : float(denss_settings['limitDmax']),
            'limit_dmax_steps'  : ast.literal_eval(denss_settings['dmaxStep']),
            'recenter'          : denss_settings['recenter'],
            'recenter_steps'    : ast.literal_eval(denss_settings['recenterStep']),
            'recenter_mode'     : denss_settings['recenterMode'],
            'positivity'        : denss_settings['positivity'],
            'extrapolate'       : denss_settings['extrapolate'],
            'output'            : den_prefix,
            'flatten_low_density': denss_settings['flattenLowDensity'],
            'shrinkwrap'        : denss_settings['shrinkwrap'],
            'shrinkwrap_sigma_start' : float(denss_settings['swSigmaStart']),
            'shrinkwrap_sigma_end' : float(denss_settings['swSigmaEnd']),
            'shrinkwrap_sigma_decay' : float(denss_settings['swSigmaDecay']),
            'shrinkwrap_threshold_fraction' : float(denss_settings['swThresFrac']),
            'shrinkwrap_iter'   : int(denss_settings['swIter']),
            'shrinkwrap_minstep' : int(denss_settings['swMinStep']),
            'chi_end_fraction'  : float(denss_settings['chiEndFrac']),
            'write_xplor_format' : denss_settings['writeXplor'],
            'enforce_connectivity' : denss_settings['connected'],
            'enforce_connectivity_steps' : ast.literal_eval(denss_settings['conSteps']),
            'cutout'            : denss_settings['cutOutput'],
            'ncs'               : int(denss_settings['ncs']),
            'ncs_steps'         : ast.literal_eval(denss_settings['ncsSteps']),
            'abort_event'       : abort_event,
            'my_logger'         : my_logger,
            'path'              : path,
            'gui'               : True,
        }

        if denss_settings['electrons'] != '':
            try:
                ne = int(denss_settings['electrons'])
            except Exception:
                ne = None

        else:
            ne = None

        if ne is None:
            ne = 10000

        denss_args['ne'] = ne

        try:
            denss_args['steps'] = int(denss_settings['steps'])
        except Exception:
            denss_args['steps'] = None

        if denss_settings['minDensity'] == 'None':
            denss_args['minimum_density'] = None
        else:
            denss_args['minimum_density'] = float(denss_settings['minDensity'])

        if denss_settings['maxDensity'] == 'None':
            denss_args['maximum_density'] = None
        else:
            denss_args['maximum_density'] = float(denss_settings['maxDensity'])

        if avg_model is not None:
            denss_args['rho_start'] = avg_model

        if denss_settings['ncsAxis'] == 'X':
            denss_args['ncs_axis'] = 1
        elif denss_settings['ncsAxis'] == 'Y':
            denss_args['ncs_axis'] = 2
        elif denss_settings['ncsAxis'] == 'Z':
            denss_args['ncs_axis'] = 3
        else:
            denss_args['ncs_axis'] = 1

        """
        Settings that are purposefully left as default:
        seed
        write_freq
        """

        data = denss(q, I, sigq, D, **denss_args)
    except Exception:
        error = traceback.format_exc()
        wx_queue.put_nowait(['error', int(my_num)-1, error])
        my_logger.error('An error occured, aborting.')
        my_logger.error(error)
        abort_event.set()

    my_fh.close()

    stop_event.set()

    if not abort_event.is_set():
        my_lock.acquire()
        if avg_model is None:
            wx_queue.put_nowait(['status', 'Finished run %s\n' %(my_num)])
        my_lock.release()

    my_lock.acquire()
    if avg_model is None:
        wx_queue.put_nowait(['finished', int(my_num)-1])
    my_lock.release()

    return data

def run_enantiomers(rhos, cores, num, avg_q, my_lock, wx_queue,
    abort_event):
    #Check to see if things have been aborted
    if abort_event.is_set():
        my_lock.acquire()
        wx_queue.put_nowait(['average', 'Aborted!\n'])
        wx_queue.put_nowait(['finished', num])
        my_lock.release()
        return None, None

    best_enans, scores = select_best_enantiomers(rhos, rhos[0], cores, avg_q,
        abort_event)

    if abort_event.is_set():
        my_lock.acquire()
        wx_queue.put_nowait(['average', 'Aborted!\n'])
        wx_queue.put_nowait(['finished', num])
        my_lock.release()
        return None, None

    return best_enans, scores
