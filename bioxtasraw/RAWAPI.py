"""
Created on June 11, 2019

@author: Jesse B. Hopkins

******************************************************************************
 This file is part of RAW.

RAW is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

RAW is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with RAW.  If not, see <http://www.gnu.org/licenses/>.

******************************************************************************

The purpose of this module is to provide an API for calling RAW functions from
other python programs. This is to provide easy access to RAW's functionality
in any data processing program you want to write in python
"""

from __future__ import absolute_import, division, print_function, unicode_literals
from builtins import object, range, map, zip
from io import open

import os
import copy
import tempfile

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

__default_settings = RAWSettings.RawGuiSettings()

def load_settings(file, settings=None):
    """
    Loads RAW settings from a file.

    Parameters
    ----------
    file: str
        The full path to a RAW settings (.cfg) file.
    settings: :class:`bioxtasraw.RAWSettings.RAWSettings`, optional
        A settings object containing already existing settings. Any
        settings duplicated between the settings loaded in and the settings
        provided will be overwritten by the settings from file. This parameter
        is generally not used.

    Returns
    -------
    settings: :class:`bioxtasraw.RAWSettings.RAWSettings`
        The RAW settings stored in the .cfg file.
    """

    if settings is None:
        settings = __default_settings

    success, msg, post_msg = RAWSettings.loadSettings(settings, file)

    if msg != '':
        print(msg)

    if post_msg != '':
        print(post_msg)

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
    """
    Loads all types of files that RAW knows how to load. If images are
    included in the list, then the images are radially averaged as part
    of being loaded in.

    Parameters
    ----------
    filename_list: list
        A list of strings containing the full path to each file to be
        loaded in.
    settings: :class:`bioxtasraw.RAWSettings.RAWSettings`
        The RAW settings to be used when loading in the files, such as the
        calibration values used when radially averaging images.

    Returns
    -------
    profile_list: list
        A list of individual scattering profile (:class:`bioxtasraw.SASM.SASM`)
        items loaded in, including those obtained from radially averaging any
        images.
    ift_list: list
        A list of individual IFT (:class:`bioxtasraw.SASM.IFTM`) items loaded in.
    series_list: list
        A list of individual series (:class:`bioxtasraw.SECM.SECM`) items
        loaded in.
    img_list: list
        A list of individual images (:class:`numpy.array`) loaded in.
    """

    if not isinstance(filename_list, list):
        filename_list = [filename_list]

    profile_list = []
    ift_list = []
    series_list = []
    img_list = []

    for filename in filename_list:
        file_ext = os.path.splitext(filename)[1]

        if file_ext == '.sec':
            secm = SASFileIO.loadSeriesFile(filename, settings)
            series_list.append(secm)

        elif file_ext == '.ift' or file_ext == '.out':
            iftm, img = SASFileIO.loadFile(filename, settings)

            if isinstance(iftm, list):
                ift_list.append(iftm[0])

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
                profile_list.extend(sasm)
            else:
                profile_list.append(sasm)

    return profile_list, ift_list, series_list, img_list

def load_profiles(filename_list, settings=None):
    """
    Loads individual scattering profiles from text files. This could be
    .dat files, but other file types such as .fit, .fir, .int, or .csv
    can also be loaded. This is a convenience wrapper for
    :py:func:`load_files` that only returns profiles. It should not be used
    for images, instead use :py:func:`load_and_integrate_images`.

    Parameters
    ----------
    filename_list: list
        A list of strings containing the full path to each profile to be loaded
        in.
    settings: :class:`bioxtasraw.RAWSettings.RAWSettings`, optional
        The RAW settings to be used when loading in the files,
        such as the calibration values used when radially averaging images.
        Default is none, this is commonly not used.

    Returns
    -------
    profile_list: list
        A list of individual scattering profile (:class:`bioxtasraw.SASM.SASM`)
        items loaded in, including those obtained from radially averaging any
        images.
    """
    if settings is None:
        settings = __default_settings

    profile_list, iftm_list, secm_list, img_list = load_files(filename_list, settings)

    return profile_list

def load_ifts(filename_list):
    """
    Loads IFT files: .out GNOM files and .ift BIFT files. This is a
    convenience wrapper for :py:func:`load_files` that only returns IFTs.

    Parameters
    ----------
    filename_list: list
        A list of strings containing the full path to each IFT file to be
        loaded in.

    Returns
    -------
    ift_list: list
        A list of individual IFT (:class:`bioxtasraw.SASM.IFTM`) items loaded in.
    """
    settings = __default_settings

    sasm_list, iftm_list, secm_list, img_list = load_files(filename_list, settings)

    return iftm_list

def load_series(filename_list, settings=None):
    """
    Loads in series data. If all filenames provided at individual scattering
    profiles (e.g. .dat files or images that can be radially averaged into
    a scattering profile) they are loaded in as a single series. If
    all files provided are series files (e.g. .sec or .hdf5 files),
    each file is loaded in as a separate series. If a mixture of profiles
    and series are provided then an error is raised.

    Parameters
    ----------
    filename_list: list
        A list of strings containing the full path to each file to be
        loaded in.
    settings: :class:`bioxtasraw.RAWSettings.RAWSettings`, optional
        The RAW settings to be used when loading in the files, such as the
        calibration values used when radially averaging images. Default is
        None. This is required if you are loading images into a series or if
        you wish to set the header style of the series loaded in, which is
        necessary for calculating the timepoint of each frame in the series.

    Returns
    -------
    series_list: list
        A list of individual series (:class:`bioxtasraw.SECM.SECM`) items
        loaded in.

    Raises
    ------
    SASExceptions.UnrecognizedDataFormat
        If you attempt to load in both scattering profiles and series files
        (.sec or .hdf5) at the same time.
    """
    if settings is None:
        settings = __default_settings

    all_secm = True
    for name in filename_list:
        if os.path.splitext(name)[1] != '.sec' or os.path.splitext(name)[1]!='.hdf5':
            all_secm = False
            break

    sasm_list, iftm_list, series_list, img_list = load_files(filename_list, settings)

    if not all_secm:
        if len(sasm_list) != 0 and len(series_list) != 0:
            msg = ('Some or all of the selected files were not scattering '
                'profiles or images, so a series dataset could not be generated.')
            raise SASExceptions.UnrecognizedDataFormat(msg)
        else:
            secm = SECM.SECM(filename_list, sasm_list, range(sasm_list), {},
                settings)

            series_list = [secm]

    return series_list

def load_images(filename_list, settings):
    """
    Loads in image files.

    Parameters
    ----------
    filename_list: list
        A list of strings containing the full path to each file to be
        loaded in.
    settings: :class:`bioxtasraw.RAWSettings.RAWSettings`
        The RAW settings to be used when loading in the files, such as the
        calibration values used when radially averaging images.

    Returns
    -------
    img_list: list
        A list of individual images (:class:`numpy.array`) loaded in.
    imghdr_list: list
        A list of the image header values associated with each image as
        dictionaries.

    Raises
    ------
    SASExceptions.WrongImageFromat
        If you load in an image that RAW can't read. This could be an error
        with your settings, or it could fundamentally be an unreadable image
        type, either due to it being an unknown format or the image being
        corrupted.
    """
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
    """
    Loads in image files and radially averages them into 1D scattering
    profiles. This is a convenience wrapper for :py:func:`load_files` that
    only returns profiles and images.

    Parameters
    ----------
    filename_list: list
        A list of strings containing the full path to each file to be
        loaded in.
    settings: :class:`bioxtasraw.RAWSettings.RAWSettings`
        The RAW settings to be used when loading in the files, such as the
        calibration values used when radially averaging images.

    Returns
    -------
    profile_list: list
        A list of individual scattering profile (:class:`bioxtasraw.SASM.SASM`)
        items loaded in, including those obtained from radially averaging any
        images.
    img_list: list
        A list of individual images (:class:`numpy.array`) loaded in.
    """
    profile_list, iftm_list, secm_list, img_list = load_files(filename_list, settings)

    return profile_list, img_list

def profiles_to_series(profiles, settings=None):
    """
    Converts a set of individual scattering profiles
    (:class:`bioxtasraw.SASM.SASM`) into a single series object
    (:class:`bioxtasraw.SECM.SECM`).

    Parameters
    ----------
    profiles: list
        A list of profiles (:class:`bioxtasraw.SASM.SASM`) to be converted
        into a series.
    settings: :class:`bioxtasraw.RAWSettings.RAWSettings`, optional
        The RAW settings to be used when converting profiles to a series.
        Default is None. This is required if you wish to set the header style
        of the series loaded in, which is necessary for calculating the
        timepoint of each frame in the series.

    Returns
    -------
    series: :class:`bioxtasraw.SECM.SECM`
        A series made from the individual input profiles.
    """

    if settings is None:
        settings = __default_settings

    filename_list = [sasm.getParameter('filename') for sasm in profiles]
    series = SECM.SECM(filename_list, profiles, range(profiles), {},
                settings)

    return series

def make_profile(q, i, err, name):
    """
    Makes a profile (:class:`bioxtasraw.SASM.SASM`) from q, I, and uncertainty
    vectors. All three input vectors must be the same length.

    Parameters
    ----------
    q: iterable
        The q vector for the scattering profile. Should be an iterable that can
        be cast to a :class:`numpy.array`, such as a list or :class:`numpy.array`.
    i: iterable
        The intensity vector for the scattering profile. Should be an iterable
        that can be cast to a :class:`numpy.array`, such as a list or
        :class:`numpy.array`.
    err: iterable
        The uncertainty vector for the scattering profile. Should be an iterable
        that can be cast to a :class:`numpy.array`, such as a list or
        :class:`numpy.array`.
    name: str
        The name of the profile. When loading a profile from a file, this is
        by default set as the filename (without the full path).

    Returns
    -------
    profile: :class:`bioxtasraw.SASM.SASM`
        A scattering profile object that can be used with the other functions in
        the API.
    """

    profile = SASM.SASM(i, q, err, {'filename': name})

    return profile

def save_profile(profile, fname=None, datadir='.', settings=None):
    """
    Saves an individual profile as a .dat file.

    Parameters
    ----------
    profile: :class:`bioxtasraw.SASM.SASM`
        The profile to be saved.
    fname: str, optional
        The output filename, without the directory path. If no filename
        is provided, the filename associated with the profile (e.g. obtained
        by using ``ift.getParameter('filename')``) is used.
    datadir: str, optional
        The directory to save the profile in. If no directory is provided,
        the current directory is used.
    settings: :class:`bioxtasraw.RAWSettings.RAWSettings`, optional
        The RAW settings to be used when saving, which contain settings for
        how to write the output .dat file.
    """
    if settings is None:
        settings = __default_settings

    if fname is not None:
        profile = copy.deepcopy(profile)
        profile.setParameter('filename', fname)

    savepath = os.path.abspath(os.path.expanduser(datadir))
    SASFileIO.saveMeasurement(profile, savepath, settings)

def save_ift(ift, fname=None, datadir='.'):
    """
    Saves an individual ift as a .out (GNOM) or .ift (BIFT) file.

    Parameters
    ----------
    profile: :class:`bioxtasraw.SASM.IFTM`
        The ift to be saved.
    fname: str, optional
        The output filename, without the directory path. If no filename
        is provided, the filename associated with the profile (e.g. obtained
        by using ``profile.getParameter('filename')``) is used.
    datadir: str, optional
        The directory to save the profile in. If no directory is provided,
        the current directory is used.
    """
    settings = __default_settings

    if ift.getParameter('algorithm') == 'GNOM':
        newext = '.out'
    else:
        newext = '.ift'

    if fname is not None:
        ift = copy.deepcopy(ift)
        ift.setParameter('filename', fname)

    savepath = os.path.abspath(os.path.expanduser(datadir))
    SASFileIO.saveMeasurement(ift, savepath, settings, filetype=newext)


def average(profiles, forced=False):
    """
    Averages the input profiles into a single averaged profile.

    Parameters
    ----------
    profiles: list
        A list of profiles (:class:`bioxtasraw.SASM.SASM`) to average.
    forced: bool, optional
        If True, RAW will attempt to average profiles even if the q vectors
        do not agree. Defaults to False.

    Returns
    -------
    avg_profile: :class:`bioxtasraw.SASM.SASM`
        The average profile.

    Raises
    ------
    SASExceptions.DataNotCompatible
        If the average list contains data sets with different q vectors and
        not forced (or if it fails to find a solution even if forced).
    """

    avg_profile = SASProc.average(profiles, forced)

    return avg_profile

def subtract(profiles, bkg_profile, forced=False, full=False):
    """
    Subtracts a background profile from the other input profiles.

    Parameters
    ----------
    profiles: list
        A list of profiles (:class:`bioxtasraw.SASM.SASM`) to be subtracted.
    bkg_profile: :class:`bioxtasraw.SASM.SASM`
        The background profile to subtract from the profiles.
    forced: bool, optional
        If True, RAW will attempt to subtract profiles even if the q vectors
        do not agree. Defaults to False.
    full: bool, optional
        If False, RAW will only use the portion of the profile between the
        defined q start and q end indices. If True, RAW will use the full q
        range of the profile, regardless of the defined q start and end indices.
        Defaults to False.

    Returns
    -------
    sub_profiles: list
        A list of subtracted profiles. Each entry in the list corresponds to
        the same entry in the input profiles list with the bkg_profile
        subtracted from it.
    """

    if not isinstance(profiles, list):
        profiles = [profiles]

    sub_profiles = [SASProc.subtract(profile, bkg_profile, forced, full)
        for profile in profiles]

    return sub_profiles

def rebin(profiles, npts=100, rebin_factor=1, log_rebin=False):
    """
    Rebins the input profiles to either the given number of points or
    by the specified factor.

    Parameters
    ----------
    profiles: list
        A list of profiles (:class:`bioxtasraw.SASM.SASM`) to be subtracted.
    npts: int, optional
        The number of points in each rebinned profile. Only used if rebin_factor
        is left to the default value of 1. Default is 100.
    rebin_factor: int, optional
        The factor by which to rebin each profile, e.g. a rebin_factor of 2
        will result in half as many q points in the rebinned profile. If
        set to a value other than the default of 1, it overrides the npts
        parameter.
    log_rebin: bool, option.
        Specifies whether the rebinning should be done in linear (False) or
        logarithmic (True) space. Defaults to linear (False).

    Returns
    -------
    rebinned_profiles: list
        A list of rebinned profiles. Each entry in the list corresponds to
        the same entry in the input profiles list rebinned.
    """
    if not isinstance(profiles, list):
        profiles = [profiles]

    rebinned_profiles = []

    for profile in profiles:

        if rebin_factor != 1:
            npts = np.floor(len(profile.q)/rebin_factor)
        else:
            rebin_factor = np.floor(len(profile.q)/npts)


        if log_rebin:
            rebin_profile = SASProc.logBinning(profile, npts)
        else:
            rebin_profile = SASProc.rebin(profile, rebin_factor)

        rebinned_profiles.append(rebin_profile)

    return rebinned_profiles


def auto_guinier(profile, error_weight=True, single_fit=True, settings=None):
    """
    Automatically calculates the Rg and I(0) values from the Guinier fit by
    determining the best range for the Guinier fit.

    Parameters
    ----------
    profile: :class:`bioxtasraw.SASM.SASM`
        The profile to perform the Guineir fit on.
    error_weight: bool, optional
        If True (default), then the Guinier fit is calculated in an error
        weighted fashion. If not, the Guinier fit is calculated without
        error weight. This is overriden by the value in the settings if
        a settings object is provided.
    single_fit: bool, optional
        If True (default), then after the correct range for the Guinier fit
        is found a traditional Guinier fit is performed using that range. If
        False, currently the same is true. In the future, if False then the Rg
        and I(0) values may be averages over some range of best Guinier fit
        intervals.
    settings: :class:`bioxtasraw.RAWSettings.RAWSettings`, optional
        RAW settings containing relevant parameters. If provided, the
        error_weight parameter will be overridden with the value in the
        settings. Default is None.

    Returns
    -------
    rg: float
        The Rg value of the fit.
    i0: float
        The I(0) value of the fit.
    rg_err: float
        The uncertainty in Rg. This is calculated as the largest
        of the uncertainty returned from autorg and the uncertatiny as
        calculated from the covariance of the Guinier fit with the autorg
        determined ranges.
    i0_err: float
        The uncertainty in I(0). This is calculated as the largest
        of the uncertainty returned from autorg and the uncertatiny as
        calculated from the covariance of the Guinier fit with the autorg
        determined ranges.
    qmin: float
        The minimum q value of the Guinier fit.
    qmax: float
        The maximum q value of the Guinier fit.
    qRg_min: float
        The q*Rg value at the minimmum q value of the Guinier fit.
    qRg_max: float
        The q*Rg value at the maximum q value of the Guinier fit.
    idx_min: int
        The minimum index of the q vector used for Guinier fit.
    idx_max: int
        The maximum index of the q vector used for the GUinier fit.
    """

    if settings is not None:
        error_weight = settings.get('errorWeight')

    rg_auto, rger_auto, i0_auto, i0er_auto, idx_min, idx_max = SASCalc.autoRg(profile,
        single_fit, error_weight)

    q = profile.getQ()
    i = profile.getI()
    err = profile.getErr()

    rg_fit, i0_fit, rger_fit, i0er_fit, a, b = SASCalc.calcRg(q[idx_min:idx_max+1],
        i[idx_min:idx_max+1], err[idx_min:idx_max+1], transform=True,
        error_weight=error_weight)

    if single_fit:
        rg = float(rg_fit)
        i0 = float(i0_fit)
    else:
        rg = float(rg_auto)
        i0 = float(i0_auto)

    rg_err = max(float(rger_fit), float(rger_auto))
    i0_err = max(float(i0er_fit), float(i0er_auto))

    qmin = q[idx_min]
    qmax = q[idx_max]
    qRg_min = qmin*rg
    qRg_max = qmax*rg

    #Get fit r squared:
    x = np.square(q[idx_min:idx_max+1])
    y = np.log(i[idx_min:idx_max+1])
    y_fit = SASCalc.linear_func(x, a, b)
    error = y - y_fit
    r_sqr = 1 - np.square(error).sum()/np.square(y-y.mean()).sum()

    info_dict = {}
    info_dict['Rg'] = rg
    info_dict['I0'] = i0
    info_dict['nStart'] = idx_min
    info_dict['nEnd'] = idx_max
    info_dict['qStart'] = qmin
    info_dict['qEnd'] = qmax
    info_dict['qRg_min'] = qRg_min
    info_dict['qRg_max'] = qRg_max
    info_dict['Rg_fit_err'] = rger_fit
    info_dict['I0_fit_err'] = i0er_fit
    info_dict['Rg_est_err'] = -1
    info_dict['I0_est_err'] = -1
    info_dict['Rg_autorg_err'] = rger_auto
    info_dict['I0_autorg_err'] = i0er_auto
    info_dict['Rg_err'] = rg_err
    info_dict['I0_err'] = i0_err
    info_dict['rsq'] = r_sqr

    analysis_dict = profile.getParameter('analysis')
    analysis_dict['guinier'] = info_dict
    profile.setParameter('analysis', analysis_dict)

    return rg, i0, rg_err, i0_err, qmin, qmax, qRg_min, qRg_max, idx_min, idx_max

def guinier_fit(profile, idx_min, idx_max, error_weight=True, settings=None):
    """
    Calculates the Rg and I(0) values from the Guinier fit defined by the
    input idx_min and idx_max parameters.

    Parameters
    ----------
    profile: :class:`bioxtasraw.SASM.SASM`
        The profile to perform the Guineir fit on.
    idx_min: int
        The index of the q vector that corresponds to the minimum q point
        to be used in the Guinier fit.
    idx_max: int
        The index of the q vector that corresponds to the maximum q point
        to be used in the Guinier fit.
    error_weight: bool, optional
        If True (default), then the Guinier fit is calculated in an error
        weighted fashion. If not, the Guinier fit is calculated without
        error weight. This is overriden by the value in the settings if
        a settings object is provided.
    single_fit: bool, optional
        If True (default), then after the correct range for the Guinier fit
        is found a traditional Guinier fit is performed using that range. If
        False, currently the same is true. In the future, if False then the Rg
        and I(0) values may be averages over some range of best Guinier fit
        intervals.
    settings: :class:`bioxtasraw.RAWSettings.RAWSettings`, optional
        RAW settings containing relevant parameters. If provided, the
        error_weight parameter will be overridden with the value in the
        settings. Default is None.

    Returns
    -------
    rg: float
        The Rg value of the fit.
    i0: float
        The I(0) value of the fit.
    rg_err: float
        The uncertainty in Rg. This is calculated as the largest
        of the uncertainty returned from autorg and the uncertatiny as
        calculated from the covariance of the Guinier fit with the autorg
        determined ranges.
    i0_err: float
        The uncertainty in I(0). This is calculated as the largest
        of the uncertainty returned from autorg and the uncertatiny as
        calculated from the covariance of the Guinier fit with the autorg
        determined ranges.
    qmin: float
        The minimum q value of the Guinier fit.
    qmax: float
        The maximum q value of the Guinier fit.
    qRg_min: float
        The q*Rg value at the minimmum q value of the Guinier fit.
    qRg_max: float
        The q*Rg value at the maximum q value of the Guinier fit.
    idx_min: int
        The minimum index of the q vector used for Guinier fit.
    idx_max: int
        The maximum index of the q vector used for the GUinier fit.
    """

    if settings is not None:
        error_weight = settings.get('errorWeight')

    x = profile.getQ()[idx_min:idx_max+1]
    y = profile.getI()[idx_min:idx_max+1]
    yerr = profile.getErr()[idx_min:idx_max+1]

    #Remove NaN and Inf values:
    x = x[np.where(np.isfinite(y))]
    yerr = yerr[np.where(np.isfinite(y))]
    y = y[np.where(np.isfinite(y))]

    rg, i0, rger_fit, i0er_fit, a, b = SASCalc.calcRg(x, y, yerr, transform=False,
        error_weight=error_weight)

    rger_est, i0er_est = SASCalc.estimate_guinier_error(x, y, yerr,
        transform=False, error_weight=error_weight)

    rg_err = max(float(rger_fit), float(rger_est))
    i0_err = max(float(i0er_fit), float(i0er_est))

    #Get fit statistics:
    y_fit = SASCalc.linear_func(x, a, b)
    error = y - y_fit
    r_sqr = 1 - np.square(error).sum()/np.square(y-y.mean()).sum()

    qmin = profile.getQ()[idx_min]
    qmax = profile.getQ()[idx_max]
    qRg_min = qmin*rg
    qRg_max = qmax*rg

    info_dict = {}
    info_dict['Rg'] = rg
    info_dict['I0'] = i0
    info_dict['nStart'] = idx_min
    info_dict['nEnd'] = idx_max
    info_dict['qStart'] = qmin
    info_dict['qEnd'] = qmax
    info_dict['qRg_min'] = qRg_min
    info_dict['qRg_max'] = qRg_max
    info_dict['Rg_fit_err'] = rger_fit
    info_dict['I0_fit_err'] = i0er_fit
    info_dict['Rg_est_err'] = rger_est
    info_dict['I0_est_err'] = i0er_est
    info_dict['Rg_autorg_err'] = -1
    info_dict['I0_autorg_err'] = -1
    info_dict['Rg_err'] = rg_err
    info_dict['I0_err'] = i0_err
    info_dict['rsq'] = r_sqr

    analysis_dict = profile.getParameter('analysis')
    analysis_dict['guinier'] = info_dict
    profile.setParameter('analysis', analysis_dict)

    return rg, i0, rg_err, i0_err, qmin, qmax, qRg_min, qRg_max, idx_min, idx_max

def mw_ref(profile, conc=0, i0=None, ref_i0=0, ref_conc=0, ref_mw=0, settings=None,
    use_i0_from='guinier'):
    """
    Calculates the M.W. of the input profile using the reference to known
    standard method. The input profile needs to have a calculated I(0) value,
    either from a Guinier fit or from a IFT P(r) function, so the I(0)
    value is known. You must supply either ref_i0, ref_conc, and ref_mw,
    or settings.

    Parameters
    ----------
    profile: :class:`bioxtasraw.SASM.SASM`
        The profile to calculate the M.W. for.
    conc: float, optional
        The concentration of the measured profile. If not provided, then
        the value from profile.getParameter('Conc') is used.
    i0: float, optional
        The I(0) to be used in calculating the M.W. If not provided, then the
        I(0) is taken from the analysis dictionary of the profile, in conjunction
        with the use_i0_from setting.
    ref_i0: float, optional
        The I(0) value for the reference standard. If settings are provided,
        this is overridden by the value in the settings.
    ref_conc: float, optional
        The concentration of the reference standard. If settings are provided,
        this is overridden by the value in the settings.
    ref_mw: float, optional
        The M.W. of the reference standard. If settings are provided,
        this is overridden by the value in the settings.
    settings: :class:`bioxtasraw.RAWSettings.RAWSettings`, optional
        RAW settings containing relevant parameters. If provided, the
        ref_i0, ref_conc, and ref_mw parameters will be overridden with the
        values in the settings. Default is None.
    use_i0_from: {'guinier', 'gnom', 'bift'} str, optional
        Determines whether the I(0) value used for the M.W. calculation is
        from the Guinier fit, or the GNOM or BIFT P(r) function. Ignored if
        the i0 parameter is provided.

    Returns
    -------
    mw: float
        The M.W.
    """

    if settings is not None:
        ref_mw = settings.get('MWStandardMW')
        ref_i0 = settings.get('MWStandardI0')
        ref_conc = settings.get('MWStandardConc')

    if conc == 0:
        conc = float(profile.getParameter('Conc'))
    else:
        profile.setParameter('Conc', conc)

    analysis_dict = profile.getParameter('analysis')

    if i0 is None:
        if use_i0_from == 'guinier':
            guinier_dict = analysis_dict['guinier']
            i0 = float(guinier_dict['I0'])

        elif use_i0_from == 'gnom':
            gnom_dict = analysis_dict['GNOM']
            i0 = float(gnom_dict['Real_Space_I0'])

        elif use_i0_from == 'bift':
            bift_dict = analysis_dict['BIFT']
            i0 = float(bift_dict['Real_Space_I0'])


    mw = SASCalc.calcRefMW(i0, conc, ref_i0, ref_conc, ref_mw)

    if 'molecularWeight' in analysis_dict:
        mw_dict = analysis_dict['molecularWeight']
    else:
        mw_dict = {}

    if mw != -1:
        mw_dict['I(0)Concentration'] = {}
        mw_dict['I(0)Concentration']['MW'] = str(mw)

        analysis_dict['molecularWeight'] = mw_dict
        profile.setParameter('analysis', analysis_dict)

    return mw

def mw_abs(profile, conc=0, i0=None, rho_Mprot=3.22*10**23, rho_solv=3.34*10**23,
    psv=0.7425, settings=None, use_i0_from='guinier',
    use_previous_settings=True, r0=2.8179*10**-13):
    """
    Calculates the M.W. of the input profile using the reference to known
    standard method. The input profile needs to have a calculated I(0) value,
    either from a Guinier fit or from a IFT P(r) function, so the I(0)
    value is known. You must supply either ref_i0, ref_conc, and ref_mw,
    or settings.

    Parameters
    ----------
    profile: :class:`bioxtasraw.SASM.SASM`
        The profile to calculate the M.W. for.
    conc: float, optional
        The concentration of the measured profile. If not provided, then
        the value from profile.getParameter('Conc') is used.
    i0: float, optional
        The I(0) to be used in calculating the M.W. If not provided, then the
        I(0) is taken from the analysis dictionary of the profile, in conjunction
        with the use_i0_from setting.
    rho_Mprot: float, optional
        Number of electrons per dry mass of protein, in e-/g
    rho_solv: float, optional
        Number of electrons per volume of aqueous solvent, in e-/cm^-3
    psv: float, optional
        The protein partial specific volume.
    settings: :class:`bioxtasraw.RAWSettings.RAWSettings`, optional
        RAW settings containing relevant parameters. If provided, the
        ref_i0, ref_conc, and ref_mw parameters will be overridden with the
        values in the settings. Default is None.
    use_i0_from: {'guinier', 'gnom', 'bift'} str, optional
        Determines whether the I(0) value used for the M.W. calculation is
        from the Guinier fit, or the GNOM or BIFT P(r) function. Ignored if
        the i0 parameter is provided.
    use_previous_settings: bool, optional
        If True, if M.W. has previously been calculated for this profile using
        this method, then the values of rho_Mprot, rho_solv, and psv are taken
        from the previously used values, if available. This overrides the
        values from either settings or the input parameters. If this is set to
        True, but the profile doesn't have those values available, then
        the next default is to look for them in settings. If that fails,
        the parameters values are used as directly input.
    r0: float, optional
        The scattering length of an electron, in cm. Not recommended to change.

    Returns
    -------
    mw: float
        The M.W.
    """
    analysis_dict = profile.getParameter('analysis')
    if 'molecularWeight' in analysis_dict:
        mw_dict = analysis_dict['molecularWeight']
    else:
        mw_dict = {}

    if (use_previous_settings and 'Absolute' in mw_dict
        and 'Density_dry_protein' in mw_dict['Absolute']
        and 'Density_buffer' in mw_dict['Absolute']
        and 'Partial_specific_volume' in mw_dict['Absolute']):

        rho_Mprot = float(mw_dict['Absolute']['Density_dry_protein'])
        rho_solv = float(mw_dict['Absolute']['Density_buffer'])
        psv =float(mw_dict['Absolute']['Partial_specific_volume'])

    elif settings is not None:
        rho_Mprot = settings.get('MWAbsRhoMprot')
        rho_solv = settings.get('MWAbsRhoSolv')
        psv = settings.get('MWAbsNuBar')
        r0 = settings.get('MWAbsR0')

    if conc == 0:
        conc = float(profile.getParameter('Conc'))
    else:
        profile.setParameter('Conc', conc)


    if i0 is None:
        if use_i0_from == 'guinier':
            guinier_dict = analysis_dict['guinier']
            i0 = float(guinier_dict['I0'])

        elif use_i0_from == 'gnom':
            gnom_dict = analysis_dict['GNOM']
            i0 = float(gnom_dict['Real_Space_I0'])

        elif use_i0_from == 'bift':
            bift_dict = analysis_dict['BIFT']
            i0 = float(bift_dict['Real_Space_I0'])


    mw = SASCalc.calcAbsMW(i0, conc, rho_Mprot, rho_solv, psv, r0)

    mw_dict['Absolute'] = {}
    mw_dict['Absolute']['MW'] = str(mw)
    mw_dict['Absolute']['Density_dry_protein'] = str(rho_Mprot)
    mw_dict['Absolute']['Density_buffer'] = str(rho_solv)
    mw_dict['Absolute']['Partial_specific_volume'] = psv

    analysis_dict['molecularWeight'] = mw_dict
    profile.setParameter('analysis', analysis_dict)

    return mw

def mw_vp(profile, rg=None, i0=None, density=0.83*10**(-3), cutoff='Default',
    qmax=0.5, settings=None, use_i0_from='guinier', use_previous_settings=True):
    """
    Calculates the M.W. of the input profile using the corrected Porod volume
    method. The input profile needs to have calculated Rg and I(0) values,
    either from a Guinier fit or from a IFT P(r) function, so the Rg and I(0)
    values are known. You must supply either density, cutoff, and qmax,
    settings, or if use_previous_settings is True then the profile needs
    to have a previously calculated M.W. using this method.

    Parameters
    ----------
    profile: :class:`bioxtasraw.SASM.SASM`
        The profile to calculate the M.W. for.
    rg: float, optional
        The Rg to be used in calculating the M.W. If not provided, then the
        Rg is taken from the analysis dictionary of the profile, in conjunction
        with the use_i0_from setting.
    i0: float, optional
        The I(0) to be used in calculating the M.W. If not provided, then the
        I(0) is taken from the analysis dictionary of the profile, in conjunction
        with the use_i0_from setting.
    density: float, optional
        The density used to the calculate the M.W. in kDa/A^3. Defaults
        to 0.83*10**(-3).
    cutoff: {''Default', '8/Rg', 'log(I0/I(q))', 'Manual''} str, optional
        The method to use to calculate the maximum q value used for the
        M.W. calculation. Defaults to 'Default'
    qmax: float, optional
        The maximum q value to be used if the 'Manual' cutoff method is
        selected. Defaults to 0.5.
    settings: :class:`bioxtasraw.RAWSettings.RAWSettings`, optional
        RAW settings containing relevant parameters. If provided, the
        density, cutoff, and qmax parameters will be overridden with the
        values in the settings. Can be overridden by the use_previous_settings
        parameter. Default is None.
    use_i0_from: {'guinier', 'gnom', 'bift'} str, optional
        Determines whether the Rg and I(0) value used for the M.W. calculation
        is from the Guinier fit, or the GNOM or BIFT P(r) function. Ignored if
        both rg and i0 parameters are provided.
    use_previous_settings: bool, optional
        If True, if M.W. has previously been calculated for this profile using
        this method, then the values of density, cutoff, and qmax are taken
        from the previously used values, if available. This overrides the
        values from either settings or the input parameters. If this is set to
        True, but the profile doesn't have those values available, then
        the next default is to look for them in settings. If that fails,
        the parameters values are used as directly input.

    Returns
    -------
    mw: float
        The M.W.
    pvol_cor: float
        The corrected Porod volume.
    pvol: float
        The uncorrected Porod volume.
    qmax: float
        The maximum q used to calculate the Porod volume.
    """

    analysis_dict = profile.getParameter('analysis')
    if 'molecularWeight' in analysis_dict:
        mw_dict = analysis_dict['molecularWeight']
    else:
        mw_dict = {}

    if (use_previous_settings and 'PorodVolume' in mw_dict
        and 'Cutoff' in mw_dict['PorodVolume']
        and 'Density' in mw_dict['PorodVolume']
        and 'Q_max' in mw_dict['PorodVolume']):

        cutoff = mw_dict['PorodVolume']['Cutoff']
        density = float(mw_dict['PorodVolume']['Density'])
        qmax =float(mw_dict['PorodVolume']['Q_max'])

    elif settings is not None:
        cutoff = settings.get('MWVpCutoff')
        density = settings.get('MWVpRho')
        qmax = settings.get('MWVpQmax')

    q = profile.getQ()
    i = profile.getI()
    err = profile.getErr()

    if rg is None or i0 is None:
        if use_i0_from == 'guinier':
            guinier_dict = analysis_dict['guinier']
            rg = float(guinier_dict['Rg'])
            i0 = float(guinier_dict['I0'])
            qmin = float(guinier_dict['qStart'])

        elif use_i0_from == 'gnom':
            gnom_dict = analysis_dict['GNOM']
            rg = float(gnom_dict['Real_Space_Rg'])
            i0 = float(gnom_dict['Real_Space_I0'])

            if 'guinier' in analysis_dict:
                guinier_dict = analysis_dict['guinier']
                qmin = float(guinier_dict['qStart'])
            else:
                qmin = q[0]

        elif use_i0_from == 'bift':
            bift_dict = analysis_dict['BIFT']
            rg = float(bift_dict['Real_Space_Rg'])
            i0 = float(bift_dict['Real_Space_I0'])

            if 'guinier' in analysis_dict:
                guinier_dict = analysis_dict['guinier']
                qmin = float(guinier_dict['qStart'])
            else:
                qmin = q[0]

    if cutoff != 'Manual':
        qmax = SASCalc.calcVqmax(q, i, rg, i0, cutoff, qmax)

    if qmax > q[-1]:
        qmax = q[-1]
    elif qmax < q[0]:
        qmax = q[0]

    mw, pvol, pvol_cor = SASCalc.calcVpMW(q, i, err, rg, i0, qmin, density,
        qmax)

    mw_dict['PorodVolume'] = {}
    mw_dict['PorodVolume']['MW'] = str(mw)
    mw_dict['PorodVolume']['VPorod'] = str(pvol)
    mw_dict['PorodVolume']['VPorod_Corrected'] = str(pvol_cor)
    mw_dict['PorodVolume']['Density'] = str(density)
    mw_dict['PorodVolume']['Cutoff'] = cutoff
    mw_dict['PorodVolume']['Q_max'] = str(qmax)
    analysis_dict['molecularWeight'] = mw_dict
    profile.setParameter('analysis', analysis_dict)

    return mw, pvol_cor, pvol, qmax

def mw_vc(profile, rg=None, i0=None, protein=True, cutoff='Manual', qmax=0.3,
    settings=None, use_i0_from='guinier', use_previous_settings=True, A_prot=1.0,
    B_prot=0.1231, A_rna=0.808, B_rna=0.00934):
    """
    Calculates the M.W. of the input profile using the volume of correlation
    method. The input profile needs to have calculated Rg and I(0) values,
    either from a Guinier fit or from a IFT P(r) function, so the Rg and I(0)
    values are known. You must supply either protein, cutoff, and qmax,
    or settings, or if use_previous_settings is True then the profile needs
    to have a previously calculated M.W. using this method.

    Parameters
    ----------
    profile: :class:`bioxtasraw.SASM.SASM`
        The profile to calculate the M.W. for.
    rg: float, optional
        The Rg to be used in calculating the M.W. If not provided, then the
        Rg is taken from the analysis dictionary of the profile, in conjunction
        with the use_i0_from setting.
    i0: float, optional
        The I(0) to be used in calculating the M.W. If not provided, then the
        I(0) is taken from the analysis dictionary of the profile, in conjunction
        with the use_i0_from setting.
    protein: bool
        True if the sample is protein, False if the sample is RNA. Determines
        which set of coefficients to use for calculating M.W.
    cutoff: {''Default', '8/Rg', 'log(I0/I(q))', 'Manual''} str, optional
        The method to use to calculate the maximum q value used for the
        M.W. calculation. Defaults to 'Manual'
    qmax: float, optional
        The maximum q value to be used if the 'Manual' cutoff method is
        selected. Defaults to 0.3.
    settings: :class:`bioxtasraw.RAWSettings.RAWSettings`, optional
        RAW settings containing relevant parameters. If provided, the
        density, cutoff, and qmax parameters will be overridden with the
        values in the settings. Can be overridden by the use_previous_settings
        parameter. Default is None.
    use_i0_from: {'guinier', 'gnom', 'bift'} str, optional
        Determines whether the Rg and I(0) value used for the M.W. calculation
        is from the Guinier fit, or the GNOM or BIFT P(r) function. Ignored if
        both rg and i0 parameters are provided.
    use_previous_settings: bool, optional
        If True, if M.W. has previously been calculated for this profile using
        this method, then the values of density, cutoff, and qmax are taken
        from the previously used values, if available. This overrides the
        values from either settings or the input parameters. If this is set to
        True, but the profile doesn't have those values available, then
        the next default is to look for them in settings. If that fails,
        the parameters values are used as directly input.
    A_prot: float
        The A coefficient for protein. Not recommended to be changed.
    B_prot: float
        The B coefficient for protein. Not recommended to be changed.
        Note that here B is defined as 1/B from the original paper.
    A_rna: float
        The A coefficient for RNA. Not recommended to be changed.
    B_rna: float
        The B coefficient for RNA. Not recommended to be changed.
        Note that here B is defined as 1/B from the original paper.

    Returns
    -------
    mw: float
        The M.W.
    vcor: float
        The volume of correlation.
    mw_err: float
        The estimated uncertainty in the M.W.
    qmax: float
        The maximum q used to calculate the Porod volume.
    """
    analysis_dict = profile.getParameter('analysis')
    if 'molecularWeight' in analysis_dict:
        mw_dict = analysis_dict['molecularWeight']
    else:
        mw_dict = {}


    if (use_previous_settings and 'VolumeOfCorrelation' in mw_dict
        and 'Cutoff' in mw_dict['VolumeOfCorrelation']
        and 'Type' in mw_dict['VolumeOfCorrelation']
        and 'Q_max' in mw_dict['VolumeOfCorrelation']):

        cutoff = mw_dict['VolumeOfCorrelation']['Cutoff']
        vc_type = mw_dict['VolumeOfCorrelation']['Type']
        qmax =float(mw_dict['VolumeOfCorrelation']['Q_max'])

        if vc_type == 'Protein':
            protein = True
        else:
            protein = False

    elif settings is not None:
        cutoff = settings.get('MWVcCutoff')
        vc_type = settings.get('MWVcType')
        qmax = settings.get('MWVcQmax')

        if vc_type == 'Protein':
            protein = True
        else:
            protein = False


    if rg is None or i0 is None:
        if use_i0_from == 'guinier':
            guinier_dict = analysis_dict['guinier']
            rg = float(guinier_dict['Rg'])
            i0 = float(guinier_dict['I0'])

        elif use_i0_from == 'gnom':
            gnom_dict = analysis_dict['GNOM']
            rg = float(gnom_dict['Real_Space_Rg'])
            i0 = float(gnom_dict['Real_Space_I0'])

        elif use_i0_from == 'bift':
            bift_dict = analysis_dict['BIFT']
            rg = float(bift_dict['Real_Space_Rg'])
            i0 = float(bift_dict['Real_Space_I0'])


    q = profile.getQ()
    i = profile.getI()

    if cutoff != 'Manual':
        qmax = SASCalc.calcVqmax(q, i, rg, i0, cutoff, qmax)

    if qmax > q[-1]:
        qmax = q[-1]
    elif qmax < q[0]:
        qmax = q[0]


    mw, mw_err, vcor, qr = SASCalc.calcVcMW(profile, rg, i0, qmax,
        A_prot, B_prot, A_rna, B_rna, protein)

    if protein:
        vc_type = 'Protein'
    else:
        vc_type = 'RNA'

    mw_dict['VolumeOfCorrelation'] = {}
    mw_dict['VolumeOfCorrelation']['MW'] = str(mw)
    mw_dict['VolumeOfCorrelation']['Type'] = vc_type
    mw_dict['VolumeOfCorrelation']['Vcor'] = str(vcor)
    mw_dict['VolumeOfCorrelation']['Cutoff'] = cutoff
    mw_dict['VolumeOfCorrelation']['Q_max'] = str(qmax)
    analysis_dict['molecularWeight'] = mw_dict
    profile.setParameter('analysis', analysis_dict)

    return mw, vcor, mw_err, qmax

def mw_bayes(profile, rg=None, i0=None, first=None, atsas_dir=None,
    use_i0_from='guinier', write_file=True, datadir=None, filename=None):
    """
    Calculates the M.W. of the input profile using the Bayesian inference
    method implemented in datmw in the ATSAS package. This requires a separate
    installation of the ATSAS package to use. The input profile needs to have
    calculated Rg and I(0) values, either from a Guinier fit or from a IFT P(r)
    function, so the Rg and I(0) values are known. All return values are -1 if
    datmw fails.

    Parameters
    ----------
    profile: :class:`bioxtasraw.SASM.SASM`
        The profile to calculate the M.W. for. If using write_file false, you
        can pass None here. In that case you must pass values for rg, i0, and
        first.
    rg: float, optional
        The Rg to be used in calculating the M.W. If not provided, then the
        Rg is taken from the analysis dictionary of the profile, in conjunction
        with the use_i0_from setting.
    i0: float, optional
        The I(0) to be used in calculating the M.W. If not provided, then the
        I(0) is taken from the analysis dictionary of the profile, in conjunction
        with the use_i0_from setting.
    first: int, optional
        The first point in the q vector to be used in calculating the M.W.
        If not provided, then the first point is taken from the guinier analysis
        of the profile if available. If not available, then the first point
        of the profile is used. Note that this must be 1 indexed, rather than
        0 indexed, so the first point of the q vector is point 1.
    atsas_dir: str, optional
        The directory of the atsas programs (the bin directory). If not provided,
        the API uses the auto-detected directory.
    use_i0_from: {'guinier', 'gnom', 'bift'} str, optional
        Determines whether the Rg and I(0) value used for the M.W. calculation
        is from the Guinier fit, or the GNOM or BIFT P(r) function. Ignored if
        both rg and i0 parameters are provided.
    write_file: bool, optional
        If True, the input profile is written to file. If False, then the
        input profile is ignored, and the profile specified by datadir and
        filename is used. This is convenient if you are trying to process
        a lot of files that are already on disk, as it saves having to read
        in each file and then save them again. Defaults to True.
    datadir: str, optional
        If write_file is False, this is used as the path to the scattering
        profile on disk.
    filename: str, optional.
        If write_file is False, this is used as the filename of the scattering
        profile on disk.

    Returns
    -------
    mw: float
        The M.W.
    mw_prob: float
        The Bayesian estimated probability that the given M.W. is correct.
    ci_lower: float
        The lower bound of the Bayesian confidence interval for the M.W. value.
    ci_upper: float
        The upper bound for the Bayesian confidence interval for the M.W. value.
    ci_prob: float
        The Bayesian estimated probability that the M.W. for the scattering
        profile is within the confidence interval.
    """
    settings = __default_settings

    if atsas_dir is None:
        atsas_dir = settings.get('ATSASDir')

    if write_file:
        analysis_dict = profile.getParameter('analysis')
        if 'molecularWeight' in analysis_dict:
            mw_dict = analysis_dict['molecularWeight']
        else:
            mw_dict = {}

        if rg is None or i0 is None:
            if use_i0_from == 'guinier':
                guinier_dict = analysis_dict['guinier']
                rg = float(guinier_dict['Rg'])
                i0 = float(guinier_dict['I0'])
                first = int(guinier_dict['nStart']) - profile.getQrange()[0] + 1

            elif use_i0_from == 'gnom':
                gnom_dict = analysis_dict['GNOM']
                rg = float(gnom_dict['Real_Space_Rg'])
                i0 = float(gnom_dict['Real_Space_I0'])

                if 'guinier' in analysis_dict:
                    guinier_dict = analysis_dict['guinier']
                    first = int(guinier_dict['nStart']) - profile.getQrange()[0] + 1
                else:
                    first = 1

            elif use_i0_from == 'bift':
                bift_dict = analysis_dict['BIFT']
                rg = float(bift_dict['Real_Space_Rg'])
                i0 = float(bift_dict['Real_Space_I0'])

                if 'guinier' in analysis_dict:
                    guinier_dict = analysis_dict['guinier']
                    first = int(guinier_dict['nStart']) - profile.getQrange()[0] + 1
                else:
                    first = 1

        if first is None:
            first = 1

        datadir = tempfile.gettempdir()
        filename = tempfile.NamedTemporaryFile(dir=os.path.abspath(datadir)).name

        filename = os.path.split(filename)[-1] + '.dat'

        SASFileIO.writeRadFile(profile, os.path.abspath(os.path.join(datadir, filename)),
            False)

    try:
        res = SASCalc.runDatmw(rg, i0, first, 'bayes', atsas_dir, datadir, filename)
    except Exception:
        res = ()

    if write_file and os.path.isfile(os.path.join(datadir, filename)):
            try:
                os.remove(os.path.join(datadir, filename))
            except Exception:
                pass

    if len(res) > 0:
        mw, mw_score, ci_lower, ci_upper, ci_score = res

        mw_prob = mw_score*100
        ci_prob = ci_score*100

        if profile is not None:
            mw_dict['DatmwBayes'] = {}
            mw_dict['DatmwBayes']['MW'] = str(mw)
            mw_dict['DatmwBayes']['ConfidenceIntervalLower'] = str(ci_lower)
            mw_dict['DatmwBayes']['ConfidenceIntervalUpper'] = str(ci_upper)
            mw_dict['DatmwBayes']['MWProbability'] = str(mw_prob)
            mw_dict['DatmwBayes']['ConfidenceIntervalProbability'] = str(ci_prob)
            analysis_dict['molecularWeight'] = mw_dict
            profile.setParameter('analysis', analysis_dict)

    else:
        mw = -1
        mw_score = -1
        ci_lower = -1
        ci_upper = -1
        ci_score = -1

    return mw, mw_prob, ci_lower, ci_upper, ci_prob

def mw_datclass(profile, rg=None, i0=None,  atsas_dir=None,
    use_i0_from='guinier', write_file=True, datadir=None, filename=None):
    """
    Calculates the M.W. of the input profile using the Bayesian inference
    method implemented in datmw in the ATSAS package. This requires a separate
    installation of the ATSAS package to use. The input profile needs to have
    calculated Rg and I(0) values, either from a Guinier fit or from a IFT P(r)
    function, so the Rg and I(0) values are known. All return values are -1 or
    None if datclass fails.

    Parameters
    ----------
    profile: :class:`bioxtasraw.SASM.SASM`
        The profile to calculate the M.W. for. If using write_file false, you
        can pass None here. In that case you must pass values for rg, i0, and
        first.
    rg: float, optional
        The Rg to be used in calculating the M.W. If not provided, then the
        Rg is taken from the analysis dictionary of the profile, in conjunction
        with the use_i0_from setting.
    i0: float, optional
        The I(0) to be used in calculating the M.W. If not provided, then the
        I(0) is taken from the analysis dictionary of the profile, in conjunction
        with the use_i0_from setting.
    atsas_dir: str, optional
        The directory of the atsas programs (the bin directory). If not provided,
        the API uses the auto-detected directory.
    use_i0_from: {'guinier', 'gnom', 'bift'} str, optional
        Determines whether the Rg and I(0) value used for the M.W. calculation
        is from the Guinier fit, or the GNOM or BIFT P(r) function. Ignored if
        both rg and i0 parameters are provided.
    write_file: bool, optional
        If True, the input profile is written to file. If False, then the
        input profile is ignored, and the profile specified by datadir and
        filename is used. This is convenient if you are trying to process
        a lot of files that are already on disk, as it saves having to read
        in each file and then save them again. Defaults to True.
    datadir: str, optional
        If write_file is False, this is used as the path to the scattering
        profile on disk.
    filename: str, optional.
        If write_file is False, this is used as the filename of the scattering
        profile on disk.

    Returns
    -------
    mw: float
        The M.W.
    shape: str
        The datclass shape category of the profile.
    dmax: float
        The datclass estimated Dmax of the profile.
    """
    settings = __default_settings

    if atsas_dir is None:
        atsas_dir = settings.get('ATSASDir')

    if write_file:
        analysis_dict = profile.getParameter('analysis')
        if 'molecularWeight' in analysis_dict:
            mw_dict = analysis_dict['molecularWeight']
        else:
            mw_dict = {}

        if rg is None or i0 is None:
            if use_i0_from == 'guinier':
                guinier_dict = analysis_dict['guinier']
                rg = float(guinier_dict['Rg'])
                i0 = float(guinier_dict['I0'])
                first = int(guinier_dict['nStart']) - profile.getQrange()[0] + 1

            elif use_i0_from == 'gnom':
                gnom_dict = analysis_dict['GNOM']
                rg = float(gnom_dict['Real_Space_Rg'])
                i0 = float(gnom_dict['Real_Space_I0'])

                if 'guinier' in analysis_dict:
                    guinier_dict = analysis_dict['guinier']
                    first = int(guinier_dict['nStart']) - profile.getQrange()[0] + 1
                else:
                    first = 1

            elif use_i0_from == 'bift':
                bift_dict = analysis_dict['BIFT']
                rg = float(bift_dict['Real_Space_Rg'])
                i0 = float(bift_dict['Real_Space_I0'])

                if 'guinier' in analysis_dict:
                    guinier_dict = analysis_dict['guinier']
                    first = int(guinier_dict['nStart']) - profile.getQrange()[0] + 1
                else:
                    first = 1

        if first is None:
            first = 1

        datadir = tempfile.gettempdir()
        filename = tempfile.NamedTemporaryFile(dir=os.path.abspath(datadir)).name

        filename = os.path.split(filename)[-1] + '.dat'

        SASFileIO.writeRadFile(profile, os.path.abspath(os.path.join(datadir, filename)),
            False)

    try:
        res = SASCalc.runDatclass(rg, i0, atsas_dir, datadir, filename)
    except Exception:
        res = ()

    if write_file and os.path.isfile(os.path.join(datadir, filename)):
            try:
                os.remove(os.path.join(datadir, filename))
            except Exception:
                pass

    if len(res) > 0:
        shape, mw, dmax = res

        if profile is not None:
            mw_dict['ShapeAndSize'] = {}
            mw_dict['ShapeAndSize']['MW'] = str(mw)
            mw_dict['ShapeAndSize']['Shape'] = shape
            mw_dict['ShapeAndSize']['Dmax'] = str(dmax)
            analysis_dict['molecularWeight'] = mw_dict
            profile.setParameter('analysis', analysis_dict)

    else:
        mw = -1
        shape = None
        dmax = -1

    return mw, shape, dmax


def bift(profile, idx_min=0, idx_max=-1, pr_pts=100, alpha_min=150,
    alpha_max=1e10, alpha_pts=16, dmax_min=10, dmax_max=400, dmax_pts=10,
    mc_runs=300, settings=None):
    """
    Calculates the Bayesian indirect Fourier transform (BIFT) of a scattering
    profile to generate a P(r) function and determine the maximum dimension
    Dmax.

    Parameters
    ----------
    profile: :class:`bioxtasraw.SASM.SASM`
        The profile to calculate the BIFT for.
    idx_min: int, optional
        The index of the q vector that corresponds to the minimum q point
        to be used in the IFT.
    idx_max: int, optional
        The index of the q vector that corresponds to the maximum q point
        to be used in the IFT.
    pr_pts: int, optional
        The number of points in the calculated P(r) function. This should
        be less than the number of points in the scattering profile.
        If settings are provided, this is overridden by the value in the
        settings.
    alpha_min: float, optional
        The minimum value of alpha for the parameter search step. If settings
        are provided, this is overridden by the value in the settings. The
        value of alpha can go beyond this bound in the optimization step,
        so this is not a hard limit on alpha.
    alpha_max: float, optional
        The maximum value of alpha for the parameter search step. If settings
        are provided, this is overridden by the value in the settings. The
        value of alpha can go beyond this bound in the optimization step,
        so this is not a hard limit on alpha.
    alpha_pts: int, optional
        The number of points in the alpha search space, which will be
        logarithmically spaced between alpha_min and alpha_max. If settings
        are provided, this is overridden by the value in the settings.
    dmax_min: float, optional
        The minimum value of Dmax for the parameter search step. If settings
        are provided, this is overridden by the value in the settings. The
        value of Dmax can go beyond this bound in the optimization step,
        so this is not a hard limit on Dmax.
    dmax_max: float, optional
        The maximum value of Dmax for the parameter search step. If settings
        are provided, this is overridden by the value in the settings. The
        value of Dmax can go beyond this bound in the optimization step,
        so this is not a hard limit on Dmax.
    dmax_pts: int, optional
        The number of points in the Dmax search space, which will be linearly
        spaced between dmax_min and dmax_max. If settings are provided, this
        is overridden by the value in the settings.
    mc_runs: int, optional
        The number of monte carlo runs used to generate the uncertainty
        estimates for the P(r) function.

    Returns
    -------
    ift: :class:`bioxtasraw.SASM.IFTM`
        The IFT calculated by BIFT from the input profile.
    dmax: float
        The maximum dimension of the P(r) function found by BIFT.
    rg: float
        The real space radius of gyration (Rg) from the P(r) function.
    i0: float
        The real space scattering at zero angle (I(0)) from the P(r) function.
    dmax_err: float
        The uncertainty in the maximum dimension of the P(r) function found
        by BIFT.
    rg_err: float
        The uncertainty in the real space radius of gyration (Rg) from the P(r)
        function.
    i0_err: float
        The uncertainty in the real space scattering at zero angle (I(0)) from
        the P(r) function.
    chi_sq: float
        The chi squared value of the fit of the scattering profile calculated
        from the P(r) function to the input scattering profile.
    log_alpha: float
        Log base 10 of the alpha value for the IFT.
    log_alpha_err: float
        Log base 10 of the uncertainty in the alpha value for the IFT.
    evidence: float
        The Bayesian evidence of the IFT.
    evidence_err: float
        The uncertainty in the Bayesian evidence of the IFT.
    """

    if settings is not None:
        pr_pts = settings.get('PrPoints')
        alpha_min = settings.get('minAlpha')
        alpha_max = settings.get('maxAlpha')
        alpha_pts = settings.get('AlphaPoints')
        dmax_min = settings.get('maxDmax')
        dmax_max = settings.get('minDmax')
        dmax_pts = settings.get('DmaxPoints')
        mc_runs = settings.get('mcRuns')

    q = profile.getQ()
    i = profile.getI()
    err = profile.getErr()
    filename = profile.getParameter('filename')

    if idx_max != -1:
        q = q[idx_min:idx_max+1]
        i = i[idx_min:idx_max+1]
        err = err[idx_min:idx_max+1]
    else:
        q = q[idx_min:]
        i = i[idx_min:]
        err = err[idx_min:]

    bift_settings = {
            'npts'      : pr_pts,
            'alpha_max' : alpha_max,
            'alpha_min' : alpha_min,
            'alpha_n'   : alpha_pts,
            'dmax_min'  : dmax_min,
            'dmax_max'  : dmax_max,
            'dmax_n'    : dmax_pts,
            'mc_runs'   : mc_runs,
            }

    ift = BIFT.doBift(q, i, err, filename, **bift_settings)

    dmax = float(ift.getParameter('dmax'))
    dmax_err = float(ift.getParameter('dmaxer'))
    rg = float(ift.getParameter('rg'))
    rg_err = float(ift.getParameter('rger'))
    i0 = float(ift.getParameter('i0'))
    i0_err = float(ift.getParameter('i0er'))
    chi_sq = float(ift.getParameter('chisq'))
    log_alpha = float(ift.getParameter('alpha'))
    log_alpha_err = float(ift.getParameter('alpha_er'))
    evidence = float(ift.getParameter('evidence'))
    evidence_err = float(ift.getParameter('evidence_er'))
    qmin = q[0]
    qmax = q[-1]

    results_dict = {}
    results_dict['Dmax'] = str(dmax)
    results_dict['Dmax_Err'] = str(dmax_err)
    results_dict['Real_Space_Rg'] = str(rg)
    results_dict['Real_Space_Rg_Err'] = str(rg_err)
    results_dict['Real_Space_I0'] = str(i0)
    results_dict['Real_Space_I0_Err'] = str(i0_err)
    results_dict['ChiSquared'] = str(chi_sq)
    results_dict['LogAlpha'] = str(log_alpha)
    results_dict['LogAlpha_Err'] = str(log_alpha_err)
    results_dict['Evidence'] = str(evidence)
    results_dict['Evidence_Err'] = str(evidence_err)
    results_dict['qStart'] = str(qmin)
    results_dict['qEnd'] = str(qmax)

    analysis_dict = profile.getParameter('analysis')
    analysis_dict['BIFT'] = results_dict
    profile.setParameter('analysis', analysis_dict)

    return (ift, dmax, rg, i0, dmax_err, rg_err, i0_err, chi_sq, log_alpha,
        log_alpha_err, evidence, evidence_err)

def datgnom(profile, rg=None, idx_min=0, idx_max=-1, atsas_dir=None,
    use_rg_from='guinier', write_profile=True, datadir=None, filename=None,
    save_ift=False, savename=None):
    """
    Calculates the IFT and resulting P(r) function using datgnom from the
    ATSAS package to automatically find the Dmax value. This requires a
    separate installation of the ATSAS package to use. The input profile needs
    to have a calculated Rg value, either from a Guinier fit or from a IFT
    P(r) function, so the Rg value is known. If datgnom fails, values of
    None, -1, or '' are returned.

    Parameters
    ----------
    profile: :class:`bioxtasraw.SASM.SASM`
        The profile to calculate the IFT for. If using write_file false, you
        can pass None here. In that case you must pass a value for rg.
    rg: float, optional
        The Rg to be used in calculating the IFT If not provided, then the
        Rg is taken from the analysis dictionary of the profile, in conjunction
        with the use_rg_from setting.
    idx_min: int, optional
        The index of the q vector that corresponds to the minimum q point
        to be used in the IFT. Ignored if write_file is False.
    idx_max: int, optional
        The index of the q vector that corresponds to the maximum q point
        to be used in the IFT. Ignored if write_file is False.
    atsas_dir: str, optional
        The directory of the atsas programs (the bin directory). If not provided,
        the API uses the auto-detected directory.
    use_rg_from: {'guinier', 'gnom', 'bift'} str, optional
        Determines whether the Rg value used for the IFT calculation
        is from the Guinier fit, or the GNOM or BIFT P(r) function. Ignored if
        the rg parameter is provided.
    write_profile: bool, optional
        If True, the input profile is written to file. If False, then the
        input profile is ignored, and the profile specified by datadir and
        filename is used. This is convenient if you are trying to process
        a lot of files that are already on disk, as it saves having to read
        in each file and then save them again. Defaults to True. If False,
        you must provide a value for the rg parameter.
    datadir: str, optional
        If write_file is False, this is used as the path to the scattering
        profile on disk.
    filename: str, optional.
        If write_file is False, this is used as the filename of the scattering
        profile on disk.
    save_ift: bool, optional
        If True, the IFT from datgnom (.out file) is saved on disk. Requires
        specification of datadir and savename parameters.
    savename: str, optional
        If save_ift is True, this is used as the filename of the .out file on
        disk. This should just be the filename, no path. The datadir parameter
        is used as the parth.

    Returns
    -------
    ift: :class:`bioxtasraw.SASM.IFTM`
        The IFT calculated by BIFT from the input profile.
    dmax: float
        The maximum dimension of the P(r) function found by BIFT.
    rg: float
        The real space radius of gyration (Rg) from the P(r) function.
    i0: float
        The real space scattering at zero angle (I(0)) from the P(r) function.
    rg_err: float
        The uncertainty in the real space radius of gyration (Rg) from the P(r)
        function.
    i0_err: float
        The uncertainty in the real space scattering at zero angle (I(0)) from
        the P(r) function.
    total_est: float
        The GNOM total estimate.
    chi_sq: float
        The chi squared value of the fit of the scattering profile calculated
        from the P(r) function to the input scattering profile.
    alpha: float
        The alpha value determined by datgnom.
    quality: str
        The GNOM qualitative interpretation of the total estimate.
    """
    settings = __default_settings

    if atsas_dir is None:
        atsas_dir = settings.get('ATSASDir')

    if not save_ift and write_profile:
        datadir = tempfile.gettempdir()

        filename = tempfile.NamedTemporaryFile(dir=os.path.abspath(datadir)).name
        filename = os.path.split(filename)[-1] + '.dat'

    elif save_ift and write_profile:
        filename = profile.getParameter('filename')

    if write_profile:
        analysis_dict = profile.getParameter('analysis')

        if rg is None:
            if use_rg_from == 'guinier':
                guinier_dict = analysis_dict['guinier']
                rg = float(guinier_dict['Rg'])

            elif use_rg_from == 'gnom':
                gnom_dict = analysis_dict['GNOM']
                rg = float(gnom_dict['Real_Space_Rg'])

            elif use_rg_from == 'bift':
                bift_dict = analysis_dict['BIFT']
                rg = float(bift_dict['Real_Space_Rg'])

        save_profile = copy.deepcopy(profile)
        if idx_max != -1:
            save_profile.setQrange((idx_min, idx_max+1))
        else:
            _, idx_max = save_profile.getQrange()
            save_profile.setQrange((idx_min, idx_max))

        SASFileIO.writeRadFile(save_profile, os.path.abspath(os.path.join(datadir, filename)),
            False)

    if not save_ift:
        savename = tempfile.NamedTemporaryFile(dir=os.path.abspath(datadir)).name
        while os.path.isfile(savename):
            savename = tempfile.NamedTemporaryFile(dir=os.path.abspath(datadir)).name

        savename = os.path.split(savename)[1]
        savename = savename+'.out'

    try:
        ift = SASCalc.runDatgnom(rg, atsas_dir, datadir, filename, savename)
    except Exception:
        ift = None

    if write_profile and os.path.isfile(os.path.join(datadir, filename)):
            try:
                os.remove(os.path.join(datadir, filename))
            except Exception:
                pass

    if not save_ift and os.path.isfile(os.path.join(datadir, savename)):
            try:
                os.remove(os.path.join(datadir, savename))
            except Exception:
                pass

    if ift is not None:
        dmax = float(ift.getParameter('dmax'))
        rg = float(ift.getParameter('rg'))
        rg_err = float(ift.getParameter('rger'))
        i0 = float(ift.getParameter('i0'))
        i0_err = float(ift.getParameter('i0er'))
        chi_sq = float(ift.getParameter('chisq'))
        alpha = float(ift.getParameter('alpha'))
        total_est = float(ift.getParameter('TE'))
        quality = ift.getParameter('quality')

        if profile is not None:
            results_dict = {}
            results_dict['Dmax'] = str(dmax)
            results_dict['Total_Estimate'] = str(total_est)
            results_dict['Real_Space_Rg'] = str(rg)
            results_dict['Real_Space_Rg_Err'] = str(rg_err)
            results_dict['Real_Space_I0'] = str(i0)
            results_dict['Real_Space_I0_Err'] = str(i0_err)
            results_dict['GNOM_ChiSquared'] = str(chi_sq)
            results_dict['Alpha'] = str(alpha)
            results_dict['qStart'] = save_profile.getQ()[0]
            results_dict['qEnd'] = save_profile.getQ()[0]
            results_dict['GNOM_Quality_Assessment'] = quality
            analysis_dict['GNOM'] = results_dict
            profile.setParameter('analysis', analysis_dict)

    else:
        dmax = -1
        rg = -1
        rg_err = -1
        i0 = -1
        i0_err = -1
        chi_sq = -1
        alpha = -1
        total_est = -1
        quality = ''

    return ift, dmax, rg, i0, rg_err, i0_err, total_est, chi_sq, alpha, quality


def efa(series, ranges, profile_type='sub', framei=None, framef=None,
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
        which each row is the range of a given component, and contains two
        integers, the first is start of that component range the second the
        end of the component range. Must be a type that can be cast as a
        numpy array.
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
        The tolerance used as the convergence critera for the EFA rotation
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
            framef = len(series.getAllSASMs())
        else:
            framef = len(series)

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

    efa_profiles = []

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

            efa_profiles.append(sasm)

    return efa_profiles, converged, conv_data, rotation_data
