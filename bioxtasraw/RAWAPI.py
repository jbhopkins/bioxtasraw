"""
Created on June 11, 2019

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

The purpose of this module is to provide an API for calling RAW functions from
other python programs. This is to provide easy access to RAW's functionality
in any data processing program you want to write in python
"""
from __future__ import absolute_import, division, print_function, unicode_literals
from builtins import object, range, map, zip
from io import open

import os
import copy

import numpy as np

raw_path = os.path.abspath(os.path.join('.', __file__, '..', '..'))
if raw_path not in os.sys.path:
    os.sys.path.append(raw_path)

import bioxtasraw.SASCalc as SASCalc
import bioxtasraw.SASExceptions as SASExceptions
import bioxtasraw.SASFileIO as SASFileIO
import bioxtasraw.SASMask as SASMask
import bioxtasraw.SASM as SASM
import bioxtasraw.SASProc as SASProc
import bioxtasraw.RAWSettings as RAWSettings
import bioxtasraw.RAWGlobals as RAWGlobals
import bioxtasraw.SECM as SECM
import bioxtasraw.BIFT as BIFT

__version__ = RAWGlobals.version

def load_settings(file, settings=None):
    if settings is None:
        settings = RAWSettings.RawGuiSettings()

    success, msg = RAWSettings.loadSettings(settings, file)

    if msg != '':
        print(msg)

    if success:
        mask_dict = settings.get('Masks')
        img_dim = settings.get('MaskDimension')

        for each_key in mask_dict:
            masks = mask_dict[each_key][1]

            if masks is not None:
                mask_img = SASMask.createMaskMatrix(img_dim, masks)
                mask_param = mask_dict[each_key]
                mask_param[0] = mask_img
                mask_param[1] = masks
    else:
        print('Failed to load settings')

    return settings

def load_files(filename_list, settings):
    if not isinstance(filename_list, list):
        filename_list = [filename_list]

    sasm_list = []
    iftm_list = []
    secm_list = []
    img_list = []

    for filename in filename_list:
        file_ext = os.path.splitext(filename)[1]

        if file_ext == '.sec':
            secm = SASFileIO.loadSeriesFile(filename, settings)
            secm_list.append(secm)

        elif file_ext == '.ift' or file_ext == '.out':
            iftm, img = SASFileIO.loadFile(filename, settings)

            if isinstance(iftm, list):
                iftm_list.append(iftm[0])

        else:
            sasm, img = SASFileIO.loadFile(filename, settings)

            if img is not None:
                start_point = settings.get('StartPoint')
                end_point = settings.get('EndPoint')

                if not isinstance(sasm, list):
                    qrange = (start_point, len(sasm.getRawQ())-end_point)
                    sasm.setQrange(qrange)
                else:
                    qrange = (start_point, len(sasm[0].getRawQ())-end_point)
                    for each_sasm in sasm:
                        each_sasm.setQrange(qrange)

                if isinstance(img, list):
                    img_list.extend(img)
                else:
                    img_list.append(img)

            if isinstance(sasm, list):
                sasm_list.extend(sasm)
            else:
                sasm_list.append(sasm)

    return sasm_list, iftm_list, secm_list, img_list

def load_dats(filename_list, settings):
    sasm_list, iftm_list, secm_list, img_list = load_files(filename_list, settings)

    return sasm_list

def load_ifts(filename_list, settings):
    sasm_list, iftm_list, secm_list, img_list = load_files(filename_list, settings)

    return iftm_list

def load_series(filename_list, settings):
    sasm_list, iftm_list, secm_list, img_list = load_files(filename_list, settings)

    return secm_list

def load_images(filename_list, settings):
    img_list = []
    imghdr_list = []

    for filename in filename_list:
        img, imghdr = SASFileIO.loadImage(filename, settings)

        if img is None:
            raise SASExceptions.WrongImageFormat('not a valid file!')

        img_list.append(img)
        imghdr_list.append(imghdr)

    return img_list, imghdr_list

def load_and_integrate_images(filename_list, settings):
    sasm_list, iftm_list, secm_list, img_list = load_files(filename_list, settings)

    return sasm_list, img_list

def save_dat(sasm, settings, fname=None, datadir='.'):
    if fname is not None:
        sasm = copy.deepcopy(sasm)
        sasm.setParameter('filename', fname)

    savepath = os.path.abspath(os.path.expanduser(datadir))
    SASFileIO.saveMeasurement(sasm, savepath, settings)


def average(sasms, forced=False):
    avg_sasm = SASProc.average(sasms, forced)

    return avg_sasm

def subtract(sasms, bkg_sasm, forced=False, full=False):
    if not isinstance(sasms, list):
        sasms = [sasms]

    sub_sasms = [SASProc.subtract(sasm, bkg_sasm, forced, full) for sasm in sasms]

    return sub_sasms

def rebin(sasms, npts, rebin_factor=1, log_rebin=False):
    if not isinstance(sasms, list):
        sasms = [sasms]

    rebinned_sasms = []

    for sasm in sasms:

        if rebin_factor != 1:
            npts = np.floor(len(sasm.q)/rebin_factor)
        else:
            rebin_factor = np.floor(len(sasm.q)/npts)


        if log_rebin:
            rebin_sasm = SASProc.logBinning(sasm, npts)
        else:
            rebin_sasm = SASProc.rebin(sasm, rebin_factor)

        rebinned_sasms.append(rebin_sasm)

    return rebinned_sasms


def autorg(sasm, single_fit=False, error_weight=True, save=True):
    rg, rger, i0, i0er, idx_min, idx_max = SASCalc.autoRg(sasm, single_fit, error_weight)

    if save:
        ####### NOT DONE YET
        q = sasm.getQ()
        i = sasm.getI()
        err = sasm.getErr()

        Rg, I0, Rger, I0er, a, b = SASCalc.calcRg(q[idx_min:idx_max+1],
            i[idx_min:idx_max+1], err[idx_min:idx_max+1], transform=False,
            error_weight=error_weight)

        info_dict = {}

        info_dict['nStart'] = idx_min
        info_dict['nEnd'] = idx_max
        info_dict['qStart'] = q[idx_min]
        info_dict['qEnd'] = q[idx_max]

        info_dict['Rg_fit_err'] = Rger
        info_dict['I0_fit_err'] = I0er

        info_dict['Rg_est_err'] = est_rg_err
        info_dict['I0_est_err'] = est_i0_err
        info_dict['Rg_err'] = max(float(est_rg_err), float(Rger))
        info_dict['I0_err'] = max(float(est_i0_err), float(I0er))

        analysis_dict = sasm.getParameter('analysis')
        analysis_dict['guinier'] = info_dict

    return rg, rger, i0, i0er, idx_min, idx_max

def calc_rg(sasm, nmin, nmax, error_weight=True, save=True):

    x = sasm.getQ()[nmin:nmax+1]
    y = sasm.getI()[nmin:nmax+1]
    yerr = sasm.getErr()[nmin:nmax+1]

    #Remove NaN and Inf values:
    x = x[np.where(np.isfinite(y))]
    yerr = yerr[np.where(np.isfinite(y))]
    y = y[np.where(np.isfinite(y))]

    rg, i0, rger, i0er, a, b = SASCalc.calcRg(x, y, yerr, transform=True,
        error_weight=error_weight)

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
                    Rg, I0, Rger, I0er, a, b = SASCalc.calcRg(x[li:],
                        y[li:], yerr[li:], transform=False, error_weight=error_weight)
                else:
                    Rg, I0, Rger, I0er, a, b = SASCalc.calcRg(x[li:-ri],
                        y[li:-ri], yerr[li:-ri], transform=False, error_weight=error_weight)

                rg_list.append(Rg)
                i0_list.append(I0)

        est_rg_err = np.std(rg_list)
        est_i0_err = np.std(i0_list)

    #Get fit statistics:
    y_fit = SASCalc.linear_func(x, a, b)
    error = y - y_fit
    r_sqr = 1 - np.square(error).sum()/np.square(y-y.mean()).sum()

    error = error/yerr

    if save:
        # THIS ISN"T DONE YET!!!!!!!!!
        info_dict = {}
        info_dict['Rg'] = rg
        info_dict['I0'] = i0
        info_dict['qRg_max'] = rg*x[-1]
        info_dict['qRg_min'] = rg*x[0]
        info_dict['nStart'] = str(nmin)
        info_dict['nEnd'] = str(nmax)
        info_dict['qStart'] = str(x[nmin])
        info_dict['qEnd'] = str(x[nmax])

        info_dict['Rg_fit_err'] = str(Rger)
        info_dict['I0_fit_err'] = str(I0er)

        info_dict['Rg_est_err'] = str(est_rg_err)
        info_dict['I0_est_err'] = str(est_i0_err)
        info_dict['Rg_err'] = max(float(est_rg_err), float(Rger))
        info_dict['I0_err'] = max(float(est_i0_err), float(I0er))

        analysis_dict = sasm.getParameter('analysis')
        analysis_dict['guinier'] = info_dict

    return rg, i0, rger, i0er, est_rg_err, est_i0_err, r_sqr

def calc_refmw(i0, conc, settings):
    mw = SASCalc.calcRefMW(i0, conc, settings)

    return mw

def calc_vpmw(sasm):
    q = sasm.getQ()
    i = sasm.getI()
    err = sasm.getErr()

    SASCalc.calcVpMW(q, i, err, rg, i0, rg_qmin, vp_density)

    ###### NOT FINISHED


def bift(sasm, settings):
    q = sasm.getQ()
    i = sasm.getI()
    err = sasm.getErr()
    filename = sasm.getParameter('filename')

    bift_settings = {
            'npts'      : settings.get('PrPoints'),
            'alpha_max' : settings.get('maxAlpha'),
            'alpha_min' : settings.get('minAlpha'),
            'alpha_n'   : settings.get('AlphaPoints'),
            'dmax_min'  : settings.get('maxDmax'),
            'dmax_max'  : settings.get('minDmax'),
            'dmax_n'    : settings.get('DmaxPoints'),
            'mc_runs'   : settings.get('mcRuns'),
            }

    iftm = BIFT.doBift(q, i, err, filename, **bift_settings)

    return iftm


def run_efa(data, ranges, sasm_type='sub', framei=None, framef=None,
    method='Hybrid', niter=1000, tol=1e-12, norm=True, force_positive=None,
    previous_results=None):

    if force_positive is None:
        force_positive = [True for i in range(len(ranges))]

    if framei is None:
            framei = 0
    if framef is None:
        if isinstance(data, SECM.SECM):
            framef = len(data.getAllSASMs())
        else:
            framef = len(data)

    if isinstance(data, SECM.SECM):
        sasm_list = data.getSASMList(framei, framef)
        filename = os.path.splitext(data.getParameter('filename'))[0]
    else:
        sasm_list = data[framei:framef+1]
        names = [os.path.basename(sasm.getParameter('filename')) for sasm in data]
        filename = os.path.commonprefix(names).rstrip('_')
        if filename == '':
            filename =  os.path.splitext(os.path.basename(data[0].getParameter('filename')))[0]

    if not isinstance(ranges, np.ndarray):
        ranges = np.array(ranges)

    intensity = np.array([sasm.getI() for sasm in sasm_list])
    err = np.array([sasm.getErr() for sasm in sasm_list])

    intensity = intensity.T #Because of how numpy does the SVD, to get U to be the scattering vectors and V to be the other, we have to transpose
    err = err.T

    if norm:
        err_mean = np.mean(err, axis = 1)
        if int(np.__version__.split('.')[0]) >= 1 and int(np.__version__.split('.')[1])>=10:
            err_avg = np.broadcast_to(err_mean.reshape(err_mean.size,1), err.shape)
        else:
            err_avg = np.array([err_mean for k in range(intensity.shape[1])]).T

        D = intensity/err_avg
    else:
        D = intensity

    if not np.all(np.isfinite(D)):
        raise SASExceptions.EFAError(('Initial SVD matrix contained nans or '
            'infinities. SVD could not be carried out'))

    svd_U, svd_s, svd_Vt = np.linalg.svd(D, full_matrices = True)

    svd_V = svd_Vt.T

    converged, conv_data, rotation_data = SASCalc.runRotation(D, intensity,
        err, ranges, force_positive, svd_V, previous_results=previous_results,
        method=method, niter=niter, tol=tol)

    efa_sasm_list = []

    q = sasm_list[0].getQ()

    if converged:
        for i in range(len(ranges)):
            intensity = rotation_data['int'][:,i]

            err = rotation_data['err'][:,i]

            sasm = SASM.SASM(intensity, q, err, {})

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

            efa_sasm_list.append(sasm)

    return efa_sasm_list, converged, conv_data, rotation_data
