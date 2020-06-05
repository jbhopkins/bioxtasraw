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
import traceback

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


def save_settings(settings, fname, datadir='.'):
    """
    Saves the settings to a file.

    Parameters
    ----------
    settings: :class:`bioxtasraw.RAWSettings.RAWSettings`
        The settings to be saved.
    fname: str
        The save filename (without path). Should be a .cfg file.
    datadir: str, optional
        The directory to save the settings. Defaults to the current directory.

    Returns
    -------
    success: bool
        Whether the save was successful.
    """
    savepath = os.path.abspath(os.path.expanduser(datadir))
    savename = os.path.join(savepath, fname)

    success = RAWSettings.saveSettings(settings, savename, False)

    return success


def average(profiles, forced=False):
    """
    Averages the input profiles into a single averaged profile. Note that
    unlike in the RAW GUI there is no automatic testing for similarity in
    this average function.

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

def weighted_average(profiles, weight_by_error=True, weight_counter='',
    forced=False, settings=None):
    """
    Averages the input profiles into a single averaged profile, using a
    weighted average. Note that unlike in the RAW GUI there is no automatic
    testing for similarity in this average function.

    Parameters
    ----------
    profiles: list
        A list of profiles (:class:`bioxtasraw.SASM.SASM`) to average.
    weight_by_error: bool, optional
        If true, weight in the average is determined by the profiles'
        uncertainties. If False, then the weighting is done by a
        counter value (such as incident intensity) specified by the
        weight_counter parameter. Defaults to True.
    weight_counter: str, optional
        If weight_by_error is False, this is the counter used to do the
        weighting, for example this might be incident intensity. This
        counter must be present in the header of all of the profiles
        (i.e. either in the 'counters' or 'imageHeader' dictionaries
        of the profiles).
    forced: bool, optional
        If True, RAW will attempt to average profiles even if the q vectors
        do not agree. Defaults to False.
    settings: :class:`bioxtasraw.RAWSettings.RAWSettings`, optional
        RAW settings containing relevant parameters. If provided, the
        weight_by_error and weight_counter parameters will be overridden
        with the values in the settings. Default is None.

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

    if settings is not None:
        weight_by_error = settings.get('weightByError')
        weight_counter = settings.get('weightCounter')

    avg_profile = SASProc.weightedAverage(profiles, weight_by_error,
        weight_counter, forced = False)

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
        A list of profiles (:class:`bioxtasraw.SASM.SASM`) to be rebinned.
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

def interpolate(profiles, ref_profile):
    """
    Interpolates the input profiles onto the reference profile's q vector.

    Parameters
    ----------
    profiles: list
        A list of profiles (:class:`bioxtasraw.SASM.SASM`) to be interpolated.
    ref_profile: :class:`bioxtasraw.SASM.SASM`
        The reference profile the profiles are interpolated onto.

    Returns
    -------
    interpolated_profiles: list
        A list of interpolated profiles. Each entry in the list corresponds to
        the same entry in the input profiles list interpolated to the reference
        profile.
    """

    interpolated_profiles = [SASProc.interpolateToFit(ref_profile, profile)
        for profile in profiles]

    return interpolated_profiles

def merge(profiles):
    """
    Merges the input profiles onto a single profile. Overlapping regions
    are averaged. Merging is done by sorting profiles by q range, then merging
    adjacent profiles. Typically this might be two profiles, for example a
    SAXS and a WAXS detector, but the function can merge an arbitrary number
    of profiles. You must input at least two profiles to merge.

    Parameters
    ----------
    profiles: list
        A list of profiles (:class:`bioxtasraw.SASM.SASM`) to be merged.

    Returns
    -------
    merged_profile: :class:`bioxtasraw.SASM.SASM`
        A single merged profile.
    """

    merged_profile = SASProc.interpolateToFit(profiles[0], profiles[1:])

    return merged_profile

def superimpose(profiles, ref_profile, scale=True, offset=False):
    """
    Superimposes the profiles onto the reference profile using either a scale,
    offset, or both.

    Parameters
    ----------
    profiles: list
        A list of profiles (:class:`bioxtasraw.SASM.SASM`) to be superimposed.
    ref_profile: :class:`bioxtasraw.SASM.SASM`
        The reference profile the profiles are superimposed onto.
    scale: bool, optional
        Whether a scale is used when superimposing. Default is True.
    offset: bool, optional
        Whether an offset is used when superimposing. Default is False.

    Returns
    -------
    sup_profiles: list
        A list of superimposed profiles. Each entry in the list corresponds to
        the same entry in the input profiles list superimposed on the reference
        profile.
    """

    sup_profiles = [copy.deepcopy(profile) for profile in profiles]

    if scale and not offset:
        choice='Scale'
    elif offset and not scale:
        choice='Offset'
    elif offset and scale:
        choice = 'Scale and Offset'
    else:
        choice = None

    if choice is not None:
        SASProc.superimpose(ref_profile, sup_profiles, choice)

    return sup_profiles

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

        datadir = os.path.abspath(os.path.expanduser(tempfile.gettempdir()))
        filename = tempfile.NamedTemporaryFile(dir=datadir).name

        filename = os.path.split(filename)[-1] + '.dat'

        SASFileIO.writeRadFile(profile, os.path.join(datadir, filename), False)

    else:
        datadir = os.path.abspath(os.path.expanduser(datadir))


    res = SASCalc.runDatmw(rg, i0, first, 'bayes', atsas_dir, datadir, filename)


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

        datadir = os.path.abspath(os.path.expanduser(tempfile.gettempdir()))
        filename = tempfile.NamedTemporaryFile(dir=datadir).name

        filename = os.path.split(filename)[-1] + '.dat'

        SASFileIO.writeRadFile(profile, os.path.join(datadir, filename), False)

    else:
        datadir = os.path.abspath(os.path.expanduser(datadir))


    res = SASCalc.runDatclass(rg, i0, atsas_dir, datadir, filename)


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


def bift(profile, idx_min=None, idx_max=None, pr_pts=100, alpha_min=150,
    alpha_max=1e10, alpha_pts=16, dmax_min=10, dmax_max=400, dmax_pts=10,
    mc_runs=300, use_guinier_start=True, settings=None):
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
        to be used in the IFT. Default is to use the first point of the q
        vector, unless use_guinier_start is set.
    idx_max: int, optional
        The index of the q vector that corresponds to the maximum q point
        to be used in the IFT. Default is to use the last point of the
        q vector.
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
    use_guiner_start: bool, optional
        If set to True, and no idx_min idx_min is provided, if a Guinier fit has
        been done for the input profile, the start point of the Guinier fit is
        used as the start point for the IFT.
    settings: :class:`bioxtasraw.RAWSettings.RAWSettings`, optional
        RAW settings containing relevant parameters. If provided, the
        pr_Pts, alpha_min, alpha_max, alpha_pts, dmax_min, dmax_max, dmax_pts,
        and mc_runs parameters will be overridden with the values in the
        settings. Default is None.

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

    if idx_min is None and use_guinier_start:
        analysis_dict = profile.getParameter('analysis')
        if 'guinier' in analysis_dict:
            guinier_dict = analysis_dict['guinier']
            idx_min = int(guinier_dict['nStart']) - profile.getQrange()[0]
        else:
            idx_min = 0

    elif idx_min is None:
        idx_min = 0

    if idx_max is not None:
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

def datgnom(profile, rg=None, idx_min=None, idx_max=None, atsas_dir=None,
    use_rg_from='guinier', use_guinier_start=True, cut_8rg=False,
    write_profile=True, datadir=None, filename=None, save_ift=False,
    savename=None):
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
        to be used in the IFT. Defaults to the first point in the q vector.
        Overrides use_guinier_start.
    idx_max: int, optional
        The index of the q vector that corresponds to the maximum q point
        to be used in the IFT. Defaults to the last point in the q vector.
        If write_profile is false and no profile is provided then this cannot
        be set, and datgnom will truncate to 8/Rg automatically. Overrides
        cut_8rg.
    atsas_dir: str, optional
        The directory of the atsas programs (the bin directory). If not provided,
        the API uses the auto-detected directory.
    use_rg_from: {'guinier', 'gnom', 'bift'} str, optional
        Determines whether the Rg value used for the IFT calculation
        is from the Guinier fit, or the GNOM or BIFT P(r) function. Ignored if
        the rg parameter is provided.
    use_guiner_start: bool, optional
        If set to True, and no idx_min is provided, if a Guinier fit has
        been done for the input profile, the start point of the Guinier fit is
        used as the start point for the IFT. Ignored if there is no input profile.
    cut_8rg: bool, optional
        If set to True and no idx_max is provided, then the profile is
        automatically truncated at q=8/Rg.
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
        datadir = os.path.abspath(os.path.expanduser(tempfile.gettempdir()))

        filename = tempfile.NamedTemporaryFile(dir=datadir).name
        filename = os.path.split(filename)[-1] + '.dat'

    elif save_ift and write_profile:
        filename = profile.getParameter('filename')

    datadir = os.path.abspath(os.path.expanduser(datadir))

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

        if idx_min is None and use_guinier_start:
            analysis_dict = profile.getParameter('analysis')
            if 'guinier' in analysis_dict:
                guinier_dict = analysis_dict['guinier']
                idx_min = int(guinier_dict['nStart']) - profile.getQrange()[0]
            else:
                idx_min = 0

        elif idx_min is None:
            idx_min = 0

        if idx_max is not None:
            save_profile.setQrange((idx_min, idx_max+1))
        else:
            if cut_8rg:
                q = save_profile.getQ()
                idx_max = np.argmin(np.abs(q-(8/rg)))
            else:
                _, idx_max = save_profile.getQrange()

            save_profile.setQrange((idx_min, idx_max))

        SASFileIO.writeRadFile(save_profile, os.path.join(datadir, filename),
            False)

    else:
        if idx_min is None and use_guinier_start and profile is not None:
            analysis_dict = profile.getParameter('analysis')
            if 'guinier' in analysis_dict:
                guinier_dict = analysis_dict['guinier']
                idx_min = int(guinier_dict['nStart']) - profile.getQrange()[0]
            else:
                idx_min = 0

        elif idx_min is None:
            idx_min=0

        if idx_max is None and profile is not None:
            _, idx_max = save_profile.getQrange()


    if not save_ift:
        savename = tempfile.NamedTemporaryFile(dir=datadir).name
        while os.path.isfile(savename):
            savename = tempfile.NamedTemporaryFile(dir=datadir).name

        savename = os.path.split(savename)[1]
        savename = savename+'.out'


    ift = SASCalc.runDatgnom(rg, atsas_dir, datadir, filename, savename,
        idx_min, idx_max)


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

        if write_profile:
            ift_name = profile.getParameter('filename')
        else:
            ift_name = filename

        ift_name = os.path.splitext(ift_name)[0] + '.out'
        ift.setParameter('filename', ift_name)

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

def gnom(profile, dmax, rg=None, idx_min=None, idx_max=None, dmax_zero=True, alpha=0,
    atsas_dir=None, use_rg_from='guinier', use_guinier_start=True,
    cut_8rg=False, write_profile=True, datadir=None, filename=None,
    save_ift=False, savename=None, settings=None, dmin_zero=True, npts=0,
    angular_scale=1, system=0, form_factor='', radius56=-1, rmin=-1, fwhm=-1,
    ah=-1, lh=-1, aw=-1, lw=-1, spot=''):
    """
    Calculates the IFT and resulting P(r) function using gnom from the
    ATSAS package. This requires a separate installation of the ATSAS package
    to use. If gnom fails, values of ``None``, -1, or ``''`` are returned.

    Parameters
    ----------
    profile: :class:`bioxtasraw.SASM.SASM`
        The profile to calculate the IFT for. If using write_file false, you
        can pass None here.
    dmax: float
        The Dmax to be used in calculating the IFT.
    rg: float, optional
        The Rg to be used in calculating the 8/rg cutoff, if cut_8/rg is
        True. If not provided, then the Rg is taken from the analysis
        dictionary of the profile, in conjunction with the use_rg_from setting.
    idx_min: int, optional
        The index of the q vector that corresponds to the minimum q point
        to be used in the IFT. Defaults to the first point in the q vector.
        Overrides use_guinier_start.
    idx_max: int, optional
        The index of the q vector that corresponds to the maximum q point
        to be used in the IFT. Defaults to the last point in the q vector.
        If write_profile is false and no profile is provided then this cannot
        be set, and datgnom will truncate to 8/Rg automatically. Overrides
        cut_8rg.
    dmax_zero: bool, optional
        If True, force P(r) function to zero at Dmax.
    alpha: bool, optional
        If not zero, force alpha value to the input value. If zero (default),
        then alpha is automatically determined by GNOM.
    atsas_dir: str, optional
        The directory of the atsas programs (the bin directory). If not provided,
        the API uses the auto-detected directory.
    use_rg_from: {'guinier', 'gnom', 'bift'} str, optional
        Determines whether the Rg value used for the 8/rg cutoff calculation
        is from the Guinier fit, or the GNOM or BIFT P(r) function. Ignored if
        the rg parameter is provided. Only used if cut_8/rg is True.
    use_guiner_start: bool, optional
        If set to True, and no idx_min is provided, if a Guinier fit has
        been done for the input profile, the start point of the Guinier fit is
        used as the start point for the IFT. Ignored if there is no input profile.
    cut_8rg: bool, optional
        If set to True and no idx_max is provided, then the profile is
        automatically truncated at q=8/Rg.
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
    settings: :class:`bioxtasraw.RAWSettings.RAWSettings`, optional
        RAW settings containing relevant parameters. If provided, the
        dmin_zero, npts, angular_scale, system, form_factor, radius56, rmin,
        fwhm, ah, lh, aw, lw, and spot parameters will be overridden with the
        values in the settings. Default is None.
    dmin_zero: bool, optional
        If True, force P(r) function to zero at Dmin.
    npts: int, optional
        If provided, fixes the number of points in the P(r) function. If 0
        (default), number of points in th P(r) function is automatically
        determined.
    angular_scale: int, optional
        Defines the angular scale of the data as given in the GNOM manual.
        Default is 1/Angstrom.
    system: int, optional
        Defines the job type as in the GNOM manual. Default is 0, a
        monodisperse system.
    form_factor: str, optional
        Path to the form factor file for system type 2. Default is not used.
    radius56: float, optional
        The radius/thickness for system type 5/6. Default is not used.
    rmin: float, optional
        Minimum size for system types 1-6. Default is not used.
    fwhm: float, optional
        Beam FWHM. Default is not used.
    ah: float, optional
        Slit height parameter A as defined in the GNOM manual. Default is not
        used.
    lh: float, optional
        Slit height parameter L as defined in the GNOM manual. Default is not
        used.
    aw: float, optional
        Slit width parameter A as defined in the GNOM manual. Default is not
        used.
    lw: float, optional
        Slit width parameter L as defined in the GNOM manual. Default is not
        used.
    spot: str, optional
        Beam profile file. Default is not used.


    Returns
    -------
    ift: :class:`bioxtasraw.SASM.IFTM`
        The IFT calculated by GNOM from the input profile.
    dmax: float
        The maximum dimension of the P(r) function.
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

    if atsas_dir is None:
        atsas_dir = __default_settings.get('ATSASDir')

    # Set input and output filenames and directory
    if not save_ift and write_profile:
        datadir = os.path.abspath(os.path.expanduser(tempfile.gettempdir()))

        filename = tempfile.NamedTemporaryFile(dir=datadir).name
        filename = os.path.split(filename)[-1] + '.dat'

    elif save_ift and write_profile:
        filename = profile.getParameter('filename')

    datadir = os.path.abspath(os.path.expanduser(datadir))

    if not save_ift:
        savename = tempfile.NamedTemporaryFile(dir=datadir).name
        while os.path.isfile(savename):
            savename = tempfile.NamedTemporaryFile(dir=datadir).name

        savename = os.path.split(savename)[1]
        savename = savename+'.out'



    # Save profile if necessary, truncating q range as appropriate
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

        if idx_min is None and use_guinier_start:
            analysis_dict = profile.getParameter('analysis')
            if 'guinier' in analysis_dict:
                guinier_dict = analysis_dict['guinier']
                idx_min = int(guinier_dict['nStart']) - profile.getQrange()[0]
            else:
                idx_min = 0

        elif idx_min is None:
            idx_min = 0

        if idx_max is not None:
            save_profile.setQrange((idx_min, idx_max+1))
        else:
            if cut_8rg:
                q = save_profile.getQ()
                idx_max = np.argmin(np.abs(q-(8/rg)))
            else:
                _, idx_max = save_profile.getQrange()

            save_profile.setQrange((idx_min, idx_max))

        SASFileIO.writeRadFile(save_profile, os.path.join(datadir, filename),
            False)

    else:
        if idx_min is None and use_guinier_start and profile is not None:
            analysis_dict = profile.getParameter('analysis')
            if 'guinier' in analysis_dict:
                guinier_dict = analysis_dict['guinier']
                idx_min = int(guinier_dict['nStart']) - profile.getQrange()[0]
            else:
                idx_min = 0

        elif idx_min is None:
            idx_min=0

        if idx_max is None and profile is not None:
            _, idx_max = save_profile.getQrange()


    #Initialize settings
    if settings is not None:
        gnom_settings = {
            'expert'        : settings.get('gnomExpertFile'),
            'rmin_zero'     : settings.get('gnomForceRminZero'),
            'rmax_zero'     : dmax_zero,
            'npts'          : settings.get('gnomNPoints'),
            'alpha'         : alpha,
            'angular'       : settings.get('gnomAngularScale'),
            'system'        : settings.get('gnomSystem'),
            'form'          : settings.get('gnomFormFactor'),
            'radius56'      : settings.get('gnomRadius56'),
            'rmin'          : settings.get('gnomRmin'),
            'fwhm'          : settings.get('gnomFWHM'),
            'ah'            : settings.get('gnomAH'),
            'lh'            : settings.get('gnomLH'),
            'aw'            : settings.get('gnomAW'),
            'lw'            : settings.get('gnomLW'),
            'spot'          : settings.get('gnomSpot'),
            'expt'          : settings.get('gnomExpt')
            }

    else:
        settings = __default_settings

        gnom_settings = {
            'expert'        : settings.get('gnomExpertFile'),
            'rmin_zero'     : dmin_zero,
            'rmax_zero'     : dmax_zero,
            'npts'          : npts,
            'alpha'         : alpha,
            'angular'       : angular_scale,
            'system'        : system,
            'form'          : form_factor,
            'radius56'      : radius56,
            'rmin'          : rmin,
            'fwhm'          : fwhm,
            'ah'            : ah,
            'lh'            : lh,
            'aw'            : aw,
            'lw'            : lw,
            'spot'          : spot,
            'expt'          : settings.get('gnomExpt')
            }


    # Run the IFT
    ift = SASCalc.runGnom(filename, savename, dmax, gnom_settings, datadir,
        atsas_dir, True)

    # Clean up
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

        if write_profile:
            ift_name = profile.getParameter('filename')
        else:
            ift_name = filename

        ift_name = os.path.splitext(ift_name)[0] + '.out'
        ift.setParameter('filename', ift_name)

    # Save results
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

def cormap(profiles, ref_profile=None, correction='Bonferroni', settings=None):
    """
    Runs the cormap comparison test between the input profiles. If a reference
    profile is provided, then all of the profiles are compared to the reference
    profile. If not reference profile is provided, then all possible pairwise
    comparisons are run between the input profiles.

    Parameters
    ----------
    profiles: list
        The input profiles (:class:`bioxtasraw.SASM.SASM` to be compared.
    ref_profile: :class:`bioxtasraw.SASM.SASM`, optional
        The reference profile to be used. If provided, all profiles are compared
        to this profile. If not provided (default) then all profiles are compared
        pairwise to each other.
    correction: {'None', 'Bonferroni'} str, optional
        What multiple testing correction to apply to the calculated pvalues.
        A value of 'None' applies no correction.
    settings: :class:`bioxtasraw.RAWSettings.RAWSettings`, optional
        RAW settings containing relevant parameters. If provided, the
        correction parameter will be overridden with the value in the settings.
        Default is None.

    Returns
    -------
    pvals: np.array
        The p values from the comparison. If no reference is provided this is
        an NxN array, where N is the number of input profiles, and each index
        corresponds to the profile in profiles. So for example, pvals[0, 5]
        would correspond to a comparison between profiles[0] and profiles[5].

        If a reference is provided, pvals is a 1D array with the same size
        as profiles. There is a direct correspondence between the index
        of pvals and profiles. E.g. pvals[2] would correspond to the comparison
        of profiles[2] and the ref_profile.
    corrected_pvals: np.array
        As pvals, but with the corrected p values based on the input correction.
    failed_comparisons: list
        If any comparisons fail, the list contains the names of the two profiles
        (as determined by profile.getParameter('filename')) for which the
        comparison failed.
    """

    if settings is not None:
        correction = settings.get('similarityCorrection')

    if ref_profile is None:
        (item_data, pvals, corrected_pvals,
            failed_comparisons) = SASProc.run_cormap_all(profiles, correction)

    else:
        pvals, corrected_pvals, failed_comparisons = SASProc.run_cormap_ref(profiles,
            ref_profile, correction)

    if correction == 'None':
        corrected_pvals = pvals

    return pvals, corrected_pvals, failed_comparisons


# Operations on IFTs

def ambimeter(ift, qRg_max=4, save_models='none', save_prefix=None,
    datadir=None, write_ift=True, filename=None, atsas_dir=None):
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

    if atsas_dir is None:
        atsas_dir = __default_settings.get('ATSASDir')

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

    ret = SASCalc.runAmbimeter(filename, save_prefix, ambimeter_settings, datadir,
        atsas_dir)

    # Clean up
    if write_ift and os.path.isfile(os.path.join(datadir, filename)):
        try:
            os.remove(os.path.join(datadir, filename))
        except Exception:
            pass

    if ret is not None:
        categories = ret[0]
        score = ret[1]
        evaluation = ret[2]

    else:
        categories = -1
        score = -1
        evaluation = ''

    return score, categories, evaluation

def dammif(ift, prefix, datadir, mode='Slow', symmetry='P1', anisometry='Unknown',
    write_ift=True, ift_name=None, atsas_dir=None, settings=None, unit='Unknown',
    omit_solvent=True, chained=False, expected_shape='u', random_seed='',
    constant='', max_bead_count=-1, dam_radius=-1, harmonics=-1, prop_to_fit=-1,
    curve_weight='e', max_steps=-1, max_iters=-1, max_success=-1,
    min_success=-1, T_factor=-1, rg_penalty=-1, center_penalty=-1,
    loose_penalty=-1):
    """
    Creates a bead model (dummy atom) reconstruction using DAMMIF from the ATSAS
    package. Requires a separate installation of the ATSAS package. Function
    blocks until DAMMIF finishes.

    Parameters
    ----------
    ift: :class:`bioxtasraw.SASM.IFTM`
        The GNOM IFT to be used as DAMMIF input. If write_ift is False, an IFT already
        on disk is used and this parameter can be ``None``.
    prefix: str
        The output prefix for the DAMMIF model.
    datadir: str
        The output directory for the DAMMIF model. If using an IFT on disk, then
        the IFT must be in this directory.
    mode: {'Fast', 'Slow' 'Custom'} str, optional
        The DAMMIF mode. Note that most of the advanced settings require that
        DAMMIF be in 'Custom' mode to use. Defaults to slow.
    symmetry: str, optional
        The symmetry applied to the reconstruction. Accepts any symmetry
        known to DAMMIF. Defaults to P1.
    anisometry: {'Unknown', 'Prolate', 'Oblate'} str, optional
        The anisometry applied to the reconstruction. Defaults to Unknown.
    write_ift: bool, optional
        If True, the input IFT is written to disk. If False, an IFT already
        on disk used, as defined by ift_name (directory must be datadir).
    ift_name: str, optional
        The IFT name on disk. Used if write_ift is False.
    atsas_dir: str, optional
        The directory of the atsas programs (the bin directory). If not provided,
        the API uses the auto-detected directory.
    settings: :class:`bioxtasraw.RAWSettings.RAWSettings`, optional
        RAW settings containing relevant parameters. If provided, every model
        parameter except mode, symmetry, and anisometry is overridden with
        the value in the settings file. Default is None.
    unit: {'Unknown', 'Angstrom', 'Nanometer'} str, optional
        The unit of the P(r) function. Defaults to 'Unknown'.
    omit_solvent: bool, optional
        Whether the solvent file (-0.pdb) should be omitted. Defaults to True.
    chained: bool, optional
        Whether the beads should be connected in pseudo-chains. Defaults to
        False.
    expected_shape: {'u', 'c', 'e', 'f', 'r', 'h', 'hs', 'rc'} str, optional
        Expected shape of the reconstruction: (u)nknown, (c)ompact, (e)xtended,
        (f)lat, (r)ing, (h) compact-hollow, (hs) hollow-sphere, (rc)
        random-chain. Default is unknown.
    random_seed: str, optional
        Random seed for the reconstruction. Default is to let DAMMIF generate
        the seed.
    constant: str, optional
        Constant offset for reconstruction. Default is to let DAMMIF determine
        the offset.
    max_bead_count: int, optional
        Maximum bead count for the model. Default is to let DAMMIF determine
        the parameter value.
    dam_radius: float, optional
        Dummy atom radius of the reconstruction, in Angstrom (>=1.0). Default
        is to let DAMMIF determine the parameter value.
    harmonics: int, optional
        Number of spherical harmonics to use in the reconstruction. Default is
        the DAMMIF default.
    prop_to_fit: float, optional
        Proportion of the curve to fit for the reconstruction. Default is
        the DAMMIF default.
    curve_weight: {'l', 'p', 'e', 'n'} str, optional
        Curve weighting function, [l]log, [p]orod, [e]mphasized porod, or
        [n]one. Default is 'e'.
    max_steps: int, optional
        Maximum number of steps in the annealing procedure. Default is the
        DAMMIF default.
    max_iters: int, optional
        Maximum number of iterations within a single temperature step. Default
        is the DAMMIF default.
    max_success: int, optional
        Maximum number of successes in a temperature step. Default is the DAMMIF
        default.
    min_success: int, optional
        Minimum number of successes in a temperature step. Default is the DAMMIF
        default.
    T_factor: float, optional
        Temperature schedule factor. Default is the DAMMIF default.
    rg_penalty: float, optional
        Rg penalty weight. Default is the DAMMIF default.
    center_penalty: float, optional
        Center penalty weight. Default is the DAMMIF default.
    loose_penalty: float, optional
        Looseness penalty weight. Default is the DAMMIF default.

    Returns
    -------
    chi_sq: float
        The chi squared of the model's scattering profile to the data.
    rg: float
        The Rg of the model.
    dmax: float
        The Dmax of the model.
    mw: float
        The estimated molecular weight of the model, based on the excluded
        volume.
    excluded_volume: float
        The excluded volume of the model.
    """

    if atsas_dir is None:
        atsas_dir = __default_settings.get('ATSASDir')

    datadir = os.path.abspath(os.path.expanduser(datadir))

    if write_ift:
        ift_name = os.path.join(datadir, ift.getParameter('filename'))
        SASFileIO.writeOutFile(ift, os.path.join(datadir, ift_name))

    if settings is None:
        dam_settings = {
            'mode'              : mode,
            'unit'              : unit,
            'sym'               : symmetry,
            'anisometry'        : anisometry,
            'omitSolvent'       : omit_solvent,
            'chained'           : chained,
            'constant'          : constant,
            'maxBead'           : max_bead_count,
            'radius'            : dam_radius,
            'harmonics'         : harmonics,
            'propFit'           : prop_to_fit,
            'curveWeight'       : curve_weight,
            'seed'              : random_seed,
            'maxSteps'          : max_steps,
            'maxIters'          : max_iters,
            'maxSuccess'        : max_success,
            'minSuccess'        : min_success,
            'TFactor'           : T_factor,
            'RgWeight'          : rg_penalty,
            'cenWeight'         : center_penalty,
            'looseWeight'       : loose_penalty,
            'shape'             : expected_shape,
            }
    else:
        dam_settings = {
            'mode'              : mode,
            'unit'              : settings.get('dammifUnit'),
            'sym'               : symmetry,
            'anisometry'        : anisometry,
            'omitSolvent'       : settings.get('dammifOmitSolvent'),
            'chained'           : settings.get('dammifChained'),
            'constant'          : settings.get('dammifConstant'),
            'maxBead'           : settings.get('dammifMaxBeadCount'),
            'radius'            : settings.get('dammifDummyRadius'),
            'harmonics'         : settings.get('dammifSH'),
            'propFit'           : settings.get('dammifPropToFit'),
            'curveWeight'       : settings.get('dammifCurveWeight'),
            'seed'              : settings.get('dammifRandomSeed'),
            'maxSteps'          : settings.get('dammifMaxSteps'),
            'maxIters'          : settings.get('dammifMaxIters'),
            'maxSuccess'        : settings.get('dammifMaxStepSuccess'),
            'minSuccess'        : settings.get('dammifMinStepSuccess'),
            'TFactor'           : settings.get('dammifTFactor'),
            'RgWeight'          : settings.get('dammifRgPen'),
            'cenWeight'         : settings.get('dammifCenPen'),
            'looseWeight'       : settings.get('dammifLoosePen'),
            'shape'             : settings.get('dammifExpectedShape'),
            }

    proc = SASCalc.runDammif(ift_name, prefix, dam_settings, datadir, atsas_dir)

    if proc is not None:
        while proc.poll() is None:
            if proc.stdout is not None:
                proc.stdout.read(1)

    if write_ift and os.path.isfile(os.path.join(datadir, ift_name)):
        try:
            os.remove(os.path.join(datadir, ift_name))
        except Exception:
            pass

    dam_name = os.path.join(datadir, prefix+'-1.pdb')
    fir_name = os.path.join(datadir, prefix+'.fir')

    _, _, model_data = SASFileIO.loadPDBFile(dam_name)

    sasm, fit_sasm = SASFileIO.loadFitFile(fir_name)
    chi_sq = float(sasm.getParameter('counters')['Chi_squared'])

    rg = float(model_data['rg'])
    dmax = float(model_data['dmax'])
    excluded_volume=float(model_data['excluded_volume'])
    mw = float(model_data['mw'])

    return chi_sq, rg, dmax, mw, excluded_volume


def dammin(ift, prefix, datadir, mode='Slow', symmetry='P1', anisometry='Unknown',
    initial_dam=None, write_ift=True, ift_name=None, atsas_dir=None,
    settings=None, unit='Unknown', constant=0, dam_radius=-1, harmonics=-1,
    prop_to_fit=-1, curve_weight='1', max_steps=-1, max_iters=-1, max_success=-1,
    min_success=-1, T_factor=-1, loose_penalty=-1, knots=20, sphere_diam=-1,
    coord_sphere=-1, disconnect_penalty=-1, periph_penalty=1):
    """
    Creates a bead model (dummy atom) reconstruction using DAMMIN from the ATSAS
    package. Requires a separate installation of the ATSAS package. Function
    blocks until DAMMIN finishes. Can be used to refine damstart.pdb files.

    Parameters
    ----------
    ift: :class:`bioxtasraw.SASM.IFTM`
        The GNOM IFT to be used as DAMMIN input. If write_ift is False, an IFT already
        on disk is used and this parameter can be ``None``.
    prefix: str
        The output prefix for the DAMMIN model.
    datadir: str
        The output directory for the DAMMIN model. If using an IFT on disk, then
        the IFT must be in this directory.
    mode: {'Fast', 'Slow' 'Custom', 'Refine'} str, optional
        The DAMMIN mode. Note that most of the advanced settings require that
        DAMMIN be in 'Custom' mode to use. Defaults to slow. If using 'Refine'
        mode then initial_dam must be specified.
    symmetry: str, optional
        The symmetry applied to the reconstruction. Accepts any symmetry
        known to DAMMIN. Defaults to P1.
    anisometry: {'Unknown', 'Prolate', 'Oblate'} str, optional
        The anisometry applied to the reconstruction. Defaults to Unknown.
    initial_dam: str, optional
        Name of the input model file for refinement. Must be in datadir.
    write_ift: bool, optional
        If True, the input IFT is written to disk. If False, an IFT already
        on disk used, as defined by ift_name (directory must be datadir).
    ift_name: str, optional
        The IFT name on disk. Used if write_ift is False.
    atsas_dir: str, optional
        The directory of the atsas programs (the bin directory). If not provided,
        the API uses the auto-detected directory.
    settings: :class:`bioxtasraw.RAWSettings.RAWSettings`, optional
        RAW settings containing relevant parameters. If provided, every model
        parameter except mode, symmetry, and anisometry is overridden with
        the value in the settings file. Default is None.
    unit: {'Unknown', 'Angstrom', 'Nanometer'} str, optional
        The unit of the P(r) function. Defaults to 'Unknown'.
    constant: str, optional
        Constant offset for reconstruction. Default is to let DAMMIN determine
        the offset.
    dam_radius: float, optional
        Packing radius of the dummy atoms. Default is to let DAMMIN determine
        the parameter value.
    harmonics: int, optional
        Number of spherical harmonics to use in the reconstruction. Default is
        the DAMMIN default.
    prop_to_fit: float, optional
        Proportion of the curve to fit for the reconstruction. Default is
        the DAMMIN default.
    curve_weight: {'0', '1', '2'} str, optional
        Curve weighting function. 0 - Porod weighting. 1 - Porod weighting
        with emphasis of initial points (default), 2 - logarithmic weighting.
    max_steps: int, optional
        Maximum number of steps in the annealing procedure. Default is the
        DAMMIN default.
    max_iters: int, optional
        Maximum number of iterations within a single temperature step. Default
        is the DAMMIN default.
    max_success: int, optional
        Maximum number of successes in a temperature step. Default is the DAMMIN
        default.
    min_success: int, optional
        Minimum number of successes in a temperature step. Default is the DAMMIN
        default.
    T_factor: float, optional
        Temperature schedule factor. Default is the DAMMIN default.
    loose_penalty: float, optional
        Looseness penalty weight. Default is the DAMMIN default.
    knots: int, optional
        Number of knots in curve to fit. Default is the DAMMIN default.
    sphere_diam: float, optional
        Sphere diameter in Angstrom. Default is the DAMMIN default.
    coord_sphere: float, optional
        Radius of the first coordination sphere. Default is the DAMMIN default.
    disconnect_penalty: float, optional
        Disconnectivity penalty weight. Default is DAMMIN default.
    periph_penalty: float, optional
        Peripheral penalty weight. Default is DAMMIN default.

    Returns
    -------
    chi_sq: float
        The chi squared of the model's scattering profile to the data.
    rg: float
        The Rg of the model.
    dmax: float
        The Dmax of the model.
    mw: float
        The estimated molecular weight of the model, based on the excluded
        volume.
    excluded_volume: float
        The excluded volume of the model.
    """

    if atsas_dir is None:
        atsas_dir = __default_settings.get('ATSASDir')

    datadir = os.path.abspath(os.path.expanduser(datadir))

    if write_ift:
        ift_name = os.path.join(datadir, ift.getParameter('filename'))
        SASFileIO.writeOutFile(ift, os.path.join(datadir, ift_name))

    if settings is None:
        dam_settings = {
            'mode'              : mode,
            'unit'              : unit,
            'sym'               : symmetry,
            'anisometry'        : anisometry,
            'harmonics'         : harmonics,
            'propFit'           : prop_to_fit,
            'curveWeight'       : curve_weight,
            'maxSteps'          : max_steps,
            'maxIters'          : max_iters,
            'maxSuccess'        : max_success,
            'minSuccess'        : min_success,
            'looseWeight'       : loose_penalty,
            'initialDAM'        : initial_dam,
            'knots'             : knots,
            'damminConstant'    : constant,
            'diameter'          : dam_radius,
            'packing'           : dam_radius,
            'coordination'      : coord_sphere,
            'disconWeight'      : disconnect_penalty,
            'periphWeight'      : periph_penalty,
            'damminCurveWeight' : curve_weight,
            'annealSched'       : T_factor,
            }
    else:
        dam_settings = {
            'mode'              : mode,
            'unit'              : settings.get('dammifUnit'),
            'sym'               : symmetry,
            'anisometry'        : anisometry,
            'harmonics'         : settings.get('dammifSH'),
            'propFit'           : settings.get('dammifPropToFit'),
            'curveWeight'       : settings.get('dammifCurveWeight'),
            'maxSteps'          : settings.get('dammifMaxSteps'),
            'maxIters'          : settings.get('dammifMaxIters'),
            'maxSuccess'        : settings.get('dammifMaxStepSuccess'),
            'minSuccess'        : settings.get('dammifMinStepSuccess'),
            'looseWeight'       : settings.get('dammifLoosePen'),
            'initialDAM'        : settings.get('damminInitial'),
            'knots'             : settings.get('damminKnots'),
            'damminConstant'    : settings.get('damminConstant'),
            'diameter'          : settings.get('damminDiameter'),
            'packing'           : settings.get('damminPacking'),
            'coordination'      : settings.get('damminCoordination'),
            'disconWeight'      : settings.get('damminDisconPen'),
            'periphWeight'      : settings.get('damminPeriphPen'),
            'damminCurveWeight' : settings.get('damminCurveWeight'),
            'annealSched'       : settings.get('damminAnealSched'),
            }

    proc = SASCalc.runDammin(ift_name, prefix, dam_settings, datadir, atsas_dir)

    if proc is not None:
        while proc.poll() is None:
            if proc.stdout is not None:
                proc.stdout.read(1)

    if write_ift and os.path.isfile(os.path.join(datadir, ift_name)):
        try:
            os.remove(os.path.join(datadir, ift_name))
        except Exception:
            pass

    dam_name = os.path.join(datadir, prefix+'-1.pdb')
    fir_name = os.path.join(datadir, prefix+'.fir')

    _, _, model_data = SASFileIO.loadPDBFile(dam_name)

    sasm, fit_sasm = SASFileIO.loadFitFile(fir_name)
    chi_sq = float(sasm.getParameter('counters')['Chi_squared'])

    rg = float(model_data['rg'])
    dmax = float(model_data['dmax'])
    excluded_volume=float(model_data['excluded_volume'])
    mw = float(model_data['mw'])

    return chi_sq, rg, dmax, mw, excluded_volume

def damaver(files, prefix, datadir, symmetry='P1', atsas_dir=None):
    """
    Runs DAMAVER from the ATSAS package on a set of files. Requires a
    separate installation of the ATSAS package. Function blocks until
    DAMAVER finishes.

    Parameters
    ----------
    files: list
        A list of strings of the filenames on disk that are the DAMAVER inputs.
        Must be just filenames, no paths, and all files must be in the same
        directory.
    prefix: str
        The prefix to be appended to the DAMAVER output files.
    datadir: str
        The data directory in which all of the input files are located.
        Also the location of the DAMAVER output.
    symmetry: str, optional
        The symmetry that DAMAVER will use during alignment. Accepts any
        symmetry that DAMAVEr will accept. Defaults to 'P1'.
    atsas_dir: str, optional
        The directory of the atsas programs (the bin directory). If not provided,
        the API uses the auto-detected directory.

    Returns
    -------
    mean_nsd: float
        The mean NSD of the models.
    stdev_nsd: float
        The standard deviation of the NSD of the models.
    result_dict: dict
        A dictionary of the model specific results. The keys are the input
        filenames. The values are lists of the form ['Include' mean_model_nsd]
        where 'Include' indicates the model was in the average whereas a
        different value indicates the model was excluded from the average.
    rep_model: str
        The name of the representative model determined by DAMAVER.
    res: float
        The resolution of the reconstructions. Only available if more than 3
        models were averaged.
    res_err: float
        The uncertainty in the resolution.
    res_unit: str
        The unit of the resolution.

    """
    if atsas_dir is None:
        atsas_dir = __default_settings.get('ATSASDir')

    datadir = os.path.abspath(os.path.expanduser(datadir))

    proc = SASCalc.runDamaver(files, datadir, atsas_dir, symmetry)

    if proc is not None:
        while proc.poll() is None:
            if proc.stdout is not None:
                proc.stdout.read(1)

    damsel_path = os.path.join(datadir, prefix+'_damsel.log')
    damsup_path = os.path.join(datadir, prefix+'_damsup.log')

    new_files = [
        (os.path.join(datadir, 'damfilt.pdb'),
            os.path.join(datadir, prefix+'_damfilt.pdb')),
        (os.path.join(datadir, 'damsel.log'), damsel_path),
        (os.path.join(datadir, 'damstart.pdb'),
            os.path.join(datadir, prefix+'_damstart.pdb')),
        (os.path.join(datadir, 'damsup.log'), damsup_path),
        (os.path.join(datadir, 'damaver.pdb'),
            os.path.join(datadir, prefix+'_damaver.pdb'))
        ]

    for item in new_files:
        if os.path.isfile(item[0]):
            os.rename(item[0], item[1])

    (mean_nsd, stdev_nsd, include_list, discard_list, result_dict, res, res_err,
        res_unit) = SASFileIO.loadDamselLogFile(damsel_path)

    model_data, rep_model = SASFileIO.loadDamsupLogFile(damsup_path)

    return mean_nsd, stdev_nsd, rep_model, result_dict, res, res_err, res_unit

def damclust(files, prefix, datadir, symmetry='P1', atsas_dir=None):
    """
    Runs DAMCLUST from the ATSAS package on a set of files. Requires a
    separate installation of the ATSAS package. Function blocks until
    DAMCLUST finishes.

    Parameters
    ----------
    files: list
        A list of strings of the filenames on disk that are the DAMAVER inputs.
        Must be just filenames, no paths, and all files must be in the same
        directory.
    prefix: str
        The prefix to be appended to the DAMAVER output files.
    datadir: str
        The data directory in which all of the input files are located.
        Also the location of the DAMAVER output.
    symmetry: str, optional
        The symmetry that DAMAVER will use during alignment. Accepts any
        symmetry that DAMAVEr will accept. Defaults to 'P1'.
    atsas_dir: str, optional
        The directory of the atsas programs (the bin directory). If not provided,
        the API uses the auto-detected directory.

    Returns
    -------
    cluster_list: list
        A list of :class:`collections.namedtuple` items. Each list item has
        entries: 'num', 'rep_model', and 'dev', where num is the number of
        models in the cluster, rep_model is the representative model of the
        cluster, and dev is the deviation within the cluster.
    distance_list: list
        A list of :class:`collections.namedtuple` items. Each list item has
        entries 'cluster1', 'cluster2', and 'cluster_dist', where cluster1 is
        the first cluster, cluster2 is the second cluster, and cluster_dist is
        the distance between cluster1 and cluster2. If there is only one
        cluster the distance list will be empty.

    """
    if atsas_dir is None:
        atsas_dir = __default_settings.get('ATSASDir')

    datadir = os.path.abspath(os.path.expanduser(datadir))

    proc = SASCalc.runDamclust(files, datadir, atsas_dir, symmetry)

    if proc is not None:
        while proc.poll() is None:
            if proc.stdout is not None:
                proc.stdout.read(1)


    damclust_log = os.path.join(datadir, prefix+'_damclust.log')
    new_files = [(os.path.join(datadir, 'damclust.log'), damclust_log)]

    for item in new_files:
        if os.path.isfile(item[0]):
            os.rename(item[0], item[1])

    cluster_list, distance_list = SASFileIO.loadDamclustLogFile(damclust_log)

    return cluster_list, distance_list

def supcomb(target, ref_file, datadir, mode='fast', superposition='ALL',
        enantiomorphs='YES', proximity='NSD', symmetry='P1', fraction='1.0',
        atsas_dir=None):
    """
    Aligns the target to the reference file using SUPCOMB from the ATSAS
    package. Require a separate installation of ATSAS. Both files must be
    in the same folder, and the aligned file is output in the folder. The
    aligned file will have the same name as the target file with _aligned
    appended to the end of the name. This function blocks until SUPCOMB is
    done.

    Parameters
    ----------
    target: str
        The target file name, without path. This file is aligned to the
        reference file, and must be in the same folder as the reference file.
    ref_file: str
        The reference file name, without path.
    datadir: str
        The directory containing both the target and ref_file. It is also the
        directory for the output file.
    mode: {'fast', 'slow'} str, optional
        The alignment mode. Must be 'slow' if symmetry is not P1. Default is
        fast.
    superposition: {'ALL', 'BACKBONE'} str, optional
        Whether to align all atoms or just the backbone. Default is ALL.
    enantiomorphs: {'YES', 'NO'} str, optional
        Whether to generate enantiomorphs during alignment. Default is YES.
    proximity: {'NSD, 'VOL'} str, optional
        What method to use to determine distance between two models. Default
        is NSD.
    symmetry: str, optional
        The symmetry applied to the alignment. If the symmetry is not P1,
        then the mode must be slow. Any symmetry allowed in the SUPCOMB
        manual is an acceptable input.
    fraction: str, optional
        The amount of the structure closer to the surface to use for NSD
        calculations.
    atsas_dir: str, optional
        The directory of the atsas programs (the bin directory). If not provided,
        the API uses the auto-detected directory.
    """

    if atsas_dir is None:
        atsas_dir = __default_settings.get('ATSASDir')

    settings = {
        'mode'          : mode,
        'superposition' : superposition,
        'enantiomorphs' : enantiomorphs,
        'proximity'     : proximity,
        'symmetry'      : symmetry,
        'fraction'      : fraction,
        }

    proc = SASCalc.runSupcomb(ref_file, target, datadir, atsas_dir, **settings)

    if proc is not None:
        while proc.poll() is None:
            if proc.stdout is not None:
                proc.stdout.read(1)

    return

# Operations on series

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
