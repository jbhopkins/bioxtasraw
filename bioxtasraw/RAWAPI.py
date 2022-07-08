""""""

from __future__ import absolute_import, division, print_function, unicode_literals

"""
Created on June 11, 2019

@author: Jesse B. Hopkins

##############################################################################
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

##############################################################################

The purpose of this module is to provide an API for calling RAW functions from
other python programs. This is to provide easy access to RAW's functionality
in any data processing program you want to write in python
"""

from builtins import object, range, map, zip
from io import open

import os
import copy
import tempfile
import traceback
import copy
import threading
import queue
import logging

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
import bioxtasraw.DENSS as DENSS
import bioxtasraw.SASUtils as SASUtils
import bioxtasraw.RAWReport as RAWReport

__version__ = RAWGlobals.version

__default_settings = RAWSettings.RawGuiSettings()
atsas_dir = SASUtils.findATSASDirectory()
__default_settings.set('ATSASDir', atsas_dir)

RAWGlobals.RAWResourcesDir = os.path.join(raw_path, 'bioxtasraw', 'resources')
RAWGlobals.RAWDefinitionsDir = os.path.join(raw_path, 'bioxtasraw', 'definitions')
RAWGlobals.RAWDocsDir = os.path.join(raw_path, 'docs', 'build', 'html')

if __name__ != '__main__':
    logger = logging.getLogger('raw')

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
        settings = copy.deepcopy(__default_settings)

    file = os.path.abspath(os.path.expanduser(file))

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
                mask_param[2] = np.logical_not(mask_img)
    else:
        print('Failed to load settings')

    return settings

def load_files(filename_list, settings, return_all_images=False):
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
    return_all_images: bool
        If True, all loaded images are returned. If false, only the first loaded
        image of the last file is returned. Useful for minimizing memory use
        if loading and processing a large number of images. False by default.

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
        filename = os.path.abspath(os.path.expanduser(filename))

        file_ext = os.path.splitext(filename)[1]

        is_profile = False

        if file_ext == '.sec':
            secm = SASFileIO.loadSeriesFile(filename, settings)
            series_list.append(secm)

        elif file_ext == '.ift' or file_ext == '.out':
            iftm, img = SASFileIO.loadFile(filename, settings, return_all_images=False)

            if isinstance(iftm, list):
                ift_list.append(iftm[0])

        elif file_ext == '.hdf5':
            try:
                secm = SASFileIO.loadSeriesFile(filename, settings)
                series_list.append(secm)
            except Exception:
                is_profile = True

        else:
            is_profile = True

        if is_profile:
            sasm, img = SASFileIO.loadFile(filename, settings,
                return_all_images=return_all_images)

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
                    if not return_all_images and len(img_list) == 0:
                        img_list.append(img[0])
                    elif not return_all_images:
                        img_list[0] = img[0]
                    else:
                        img_list.extend(img)
                else:
                    if not return_all_images and len(img_list) == 0:
                        img_list.append(img)
                    elif not return_all_images:
                        img_list[0] = img
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
        necessary for calculating the time point of each frame in the series.

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
        if os.path.splitext(name)[1] != '.sec' and os.path.splitext(name)[1]!='.hdf5':
            all_secm = False
            break

    sasm_list, iftm_list, series_list, img_list = load_files(filename_list, settings)

    if not all_secm:
        if len(sasm_list) != 0 and len(series_list) != 0:
            msg = ('Some or all of the selected files were not scattering '
                'profiles or images, so a series dataset could not be generated.')
            raise SASExceptions.UnrecognizedDataFormat(msg)
        else:
            secm = SECM.SECM(filename_list, sasm_list, range(len(sasm_list)), {},
                settings)

            series_list = [secm]

    return series_list

def load_images(filename_list, settings, frame_num=None):
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
    frame_num: int
        If a frame number is passed, only that specific frame is returned from
        a multi-image file. If no frame number is passed, all frames are returned
        from a multi-image file. Should be either None (the default) or 0 for
        single image files.

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
        filename = os.path.abspath(os.path.expanduser(filename))

        if frame_num is None:
            img, imghdr, _ = SASFileIO.loadImage(filename, settings)
        else:
            img, imghdr, _ = SASFileIO.loadImage(filename, settings,
                next_image=frame_num)

        if img is None:
            raise SASExceptions.WrongImageFormat('not a valid file!')

        img_list.extend(img)
        imghdr_list.extend(imghdr)

    return img_list, imghdr_list

def load_and_integrate_images(filename_list, settings, return_all_images=False):
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
    return_all_images: bool
        If True, all loaded images are returned. If false, only the first loaded
        image of the last file is returned. Useful for minimizing memory use
        if loading and processing a large number of images. False by default.

    Returns
    -------
    profile_list: list
        A list of individual scattering profile (:class:`bioxtasraw.SASM.SASM`)
        items loaded in, including those obtained from radially averaging any
        images.
    img_list: list
        A list of individual images (:class:`numpy.array`) loaded in.
    """
    profile_list, iftm_list, secm_list, img_list = load_files(filename_list,
        settings, return_all_images)

    return profile_list, img_list

def load_counter_values(filename_list, settings, new_filename_list=[]):
    """
    Loads in the counter values from a separate header file associated with
    a given image.

    Parameters
    ----------
    filename_list: list
        A list of strings containing the full path to each image filename to
        load the counter values for.
    settings: :class:`bioxtasraw.RAWSettings.RAWSettings`
        The RAW settings to be used when loading in the header, which defines
        what type of header to look for.
    new_filename_list: list, optional
        A list of strings containing optional filenames for the images.
        If an image file contains multiple images such as some hdf5 files),
        this filename is used to determine what image inside the image file
        the header should be loaded for. RAW expects this to be in the form
        <image_name>_00001.<ext>, where 00001 would be first image in a file,
        00002 the second image, and so on.

    Returns
    -------
    counter_list: list
        A list of dictionaries where each key is a counter name (such as I0)
        and each value is the value of that counter for the input image name.
    """
    hdr_fmt = settings.get('ImageHdrFormat')

    counter_list = []

    if len(new_filename_list) == 0:
        new_filename_list = ['' for j in range(len(filename_list))]

    for j, filename in enumerate(filename_list):
        filename = os.path.abspath(os.path.expanduser(filename))

        if new_filename_list[j] == '':
            new_filename = os.path.split(filename)[1]
        else:
            new_filename = os.path.split(new_filename_list[j])[1]

        counters = SASFileIO.loadHeader(filename, new_filename, hdr_fmt)

        counter_list.append(counters)

    return counter_list

def load_mrc(filename_list):
    """
    Loads DENSS .mrc files.

    Parameters
    ----------
    filename_list: list
        A list of strings containing the full path to each mrc file to be
        loaded in.

    Returns
    -------
    rho: list
        A list of :class:`numpy.array` of the calculated electron density of
        the models.
    side: list
        A list of floats of the real space box width in Angstroms of the
        models.
    """
    rhos = []
    sides = []

    for fname in filename_list:
        fname = os.path.abspath(os.path.expanduser(fname))
        rho, side = DENSS.read_mrc(fname)

        rhos.append(rho)
        sides.append(side)

    return rhos, sides

def integrate_image(img, settings, name, img_hdr={}, counters={}, load_path=''):
    """
    Processes a loaded image into a 1D scattering profile.

    Parameters
    ----------
    img: :class:`numpy.array`
        The image as a numpy array.
    settings: :class:`bioxtasraw.RAWSettings.RAWSettings`
        The RAW settings to be used when integrating the image.
    name: str
        The name to be used for the scattering profile.
    img_hdr: dict, optional
        The image header associated with the given image. May be required for
        normalization.
    counters: dict, optional
        The counters associated with a given image. May be required for
        normalization.
    load_path: str, optional
        The load path of the image. Only used for metadata purposes.

    Returns
    -------
    profile: :class:`bioxtasraw.SASM.SASM`
        The integrated 1D scattering profile.
    """
    if load_path != '':
        load_path = os.path.abspath(os.path.expanduser(load_path))

    parameters = {
        'imageHeader'   : img_hdr,
        'counters'      : counters,
        'filename'      : name,
        'load_path'     : load_path
        }

    profile = SASFileIO.processImage(img, parameters, settings)

    SASFileIO.postProcessProfile(profile, settings, False)

    start_point = settings.get('StartPoint')
    end_point = settings.get('EndPoint')

    if not isinstance(profile, list):
        qrange = (start_point, len(profile.getRawQ())-end_point)
        profile.setQrange(qrange)
    else:
        qrange = (start_point, len(profile[0].getRawQ())-end_point)
        for each_profile in profile:
            each_profile.setQrange(qrange)

    return profile

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
        time point of each frame in the series.

    Returns
    -------
    series: :class:`bioxtasraw.SECM.SECM`
        A series made from the individual input profiles.
    """

    if settings is None:
        settings = __default_settings

    filename_list = [sasm.getParameter('filename') for sasm in profiles]
    series = SECM.SECM(filename_list, profiles, range(len(profiles)), {},
                settings)

    return series

def make_profile(q, i, err, name, q_err=None):
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
    q_err: iterable, optional
        The uncertainty vector in q for the scattering profile. Should be
        either None or an iterable that can be cast to a :class:`numpy.array',
        such as a list or :class:`numpy.array`. Default is None. Typically only
        used for SANS data.

    Returns
    -------
    profile: :class:`bioxtasraw.SASM.SASM`
        A scattering profile object that can be used with the other functions in
        the API.
    """

    profile = SASM.SASM(i, q, err, {'filename': name}, q_err)

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
    logger.debug('In save profile')
    if settings is None:
        settings = __default_settings

    logger.debug('setting filename if necessary')
    if fname is not None:
        profile = copy.deepcopy(profile)
        profile.setParameter('filename', fname)

    logger.debug('setting path')
    savepath = os.path.abspath(os.path.expanduser(datadir))
    logger.debug('saving')
    SASFileIO.saveMeasurement(profile, savepath, settings)
    logger.debug('done saving profile')


def save_ift(ift, fname=None, datadir='.'):
    """
    Saves an individual ift as a .out (GNOM) or .ift (BIFT) file.

    Parameters
    ----------
    ift: :class:`bioxtasraw.SASM.IFTM`
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

def save_series(series, fname=None, datadir='.'):
    """
    Saves an individual series as a .hdf5 file.

    Parameters
    ----------
    series: :class:`bioxtasraw.SASM.IFTM`
        The series to be saved.
    fname: str, optional
        The output filename, without the directory path. If no filename
        is provided, the filename associated with the profile (e.g. obtained
        by using ``series.getParameter('filename')``) is used.
    datadir: str, optional
        The directory to save the profile in. If no directory is provided,
        the current directory is used.
    """
    if fname is not None:
        series = copy.deepcopy(series)
        series.setParameter('filename', fname)
    else:
        fname = series.getParameter('filename')

    fname = '{}.hdf5'.format(os.path.splitext(fname)[0])

    datadir = os.path.abspath(os.path.expanduser(datadir))
    savepath = os.path.join(datadir, fname)

    SASFileIO.save_series(savepath, series)

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

def save_report(fname, datadir='.', profiles=[], ifts=[], series=[],
    dammif_data=[]):
    """
    Saves a .pdf report/summary of the input data.

    Parameters
    ----------
    fname: str
        The output filename without the directory path.
    datadir: str, optional
        The directory to save the report in. If no directory is provided,
        the current directory is used.
    profiles: list
        A list of :class:`bioxtasraw.SASM.SASM` profiles to add to the report.
    ifts: list
        A list of :class:`bioxtasraw.SASM.IFTM` IFTs to add to the report.
    series: list
        A list of :class:`bioxtasraw.SECM.SECM` series to add to the report.
    dammif_data: list
        A list of paths to the summary files of dammif runs from RAW (.csv files)
        to add to the report.
    """
    datadir = os.path.abspath(os.path.expanduser(datadir))

    fname = os.path.splitext(fname)[0] + '.pdf'

    RAWReport.make_report_from_raw(fname, datadir, profiles, ifts, series,
        __default_settings, dammif_data)

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
    avg_profile.setParameter('filename',
        'A_{}'.format(avg_profile.getParameter('filename')))

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

    avg_profile.setParameter('filename',
        'A_{}'.format(avg_profile.getParameter('filename')))

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

    for profile in sub_profiles:
        profile.setParameter('filename',
            'S_{}'.format(profile.getParameter('filename')))

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
            if rebin_factor != 0:
                rb_pts = int(np.floor(len(profile.getQ())/rebin_factor))
            else:
                rb_pts = len(profile.getQ())

            rb_fac = rebin_factor
        else:
            if npts >= 1:
                rb_fac = int(np.floor(len(profile.getQ())/float(npts)))
            else:
                rb_fac = 1

            rb_pts = npts

        if log_rebin:
            rebin_profile = SASProc.logBinning(profile, rb_pts)
        else:
            rebin_profile = SASProc.rebin(profile, rb_fac)

        rebin_profile.setParameter('filename',
            'R_{}'.format(rebin_profile.getParameter('filename')))

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

    for profile in interpolated_profiles:
        profile.setParameter('filename',
            'I_{}'.format(profile.getParameter('filename')))

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

    merged_profile = SASProc.merge(profiles[0], profiles[1:])

    merged_profile.setParameter('filename',
            'M_{}'.format(merged_profile.getParameter('filename')))

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
        error weight. This is overridden by the value in the settings if
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
    r_sqr: float
        The r^2 value of the fit.
    """

    if settings is not None:
        error_weight = settings.get('errorWeight')

    rg_auto, rger_auto, i0_auto, i0er_auto, idx_min, idx_max = SASCalc.autoRg(profile,
        single_fit, error_weight)

    if rg_auto != -1:
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

        nmin_offset, _ = profile.getQrange()

        info_dict = {}
        info_dict['Rg'] = rg
        info_dict['I0'] = i0
        info_dict['nStart'] = idx_min + nmin_offset
        info_dict['nEnd'] = idx_max + nmin_offset
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

    else:
        rg = -1.
        i0 = -1.
        rg_err = -1.
        i0_err = -1.
        qmin = -1.
        qmax = -1.
        qRg_min = -1.
        qRg_max = -1.
        idx_min = -1
        idx_max = -1
        r_sqr = -1.

    return (rg, i0, rg_err, i0_err, qmin, qmax, qRg_min, qRg_max, idx_min, idx_max, r_sqr)

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
        error weight. This is overridden by the value in the settings if
        a settings object is provided.
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
        of the uncertainty returned from autorg and the uncertainty as
        calculated from the covariance of the Guinier fit with the autorg
        determined ranges.
    i0_err: float
        The uncertainty in I(0). This is calculated as the largest
        of the uncertainty returned from autorg and the uncertainty as
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
    r_sqr: float
        The r^2 value of the fit.
    """

    if settings is not None:
        error_weight = settings.get('errorWeight')

    q = profile.getQ()[idx_min:idx_max+1]
    i = profile.getI()[idx_min:idx_max+1]
    ierr = profile.getErr()[idx_min:idx_max+1]

    #Remove NaN and Inf values:
    q = q[np.where(np.isfinite(i))]
    ierr = ierr[np.where(np.isfinite(i))]
    i = i[np.where(np.isfinite(i))]

    x = np.square(q)
    yerr = np.absolute(ierr/i)
    y = np.log(i)

    rg, i0, rger_fit, i0er_fit, a, b = SASCalc.calcRg(x, y, yerr, transform=False,
        error_weight=error_weight)

    rger_est, i0er_est = SASCalc.estimate_guinier_error(x, y, yerr,
        transform=False, error_weight=error_weight)

    if rger_est is None:
        rg_err = float(rger_fit)
    else:
        rg_err = max(float(rger_fit), float(rger_est))

    if i0er_est is None:
        i0_err = float(i0er_fit)
    else:
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

    return rg, i0, rg_err, i0_err, qmin, qmax, qRg_min, qRg_max, r_sqr

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
    psv=0.7425, settings=None, use_i0_from='guinier', r0=2.8179*10**-13):
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

    if settings is not None:
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
    qmin=None, qmax=0.5, settings=None, use_i0_from='guinier'):
    """
    Calculates the M.W. of the input profile using the corrected Porod volume
    method. The input profile needs to have calculated Rg and I(0) values,
    either from a Guinier fit or from a IFT P(r) function, so the Rg and I(0)
    values are known. You must supply either density, cutoff, and qmax,
    settings.

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
    qmin: float, optional
        The minimum q value to be used if rg and I(0) are supplied. Ignored if
        rg and i0 parameters are not provided.
    qmax: float, optional
        The maximum q value to be used if the 'Manual' cutoff method is
        selected. Defaults to 0.5.
    settings: :class:`bioxtasraw.RAWSettings.RAWSettings`, optional
        RAW settings containing relevant parameters. If provided, the
        density, cutoff, and qmax parameters will be overridden with the
        values in the settings.
        parameter. Default is None.
    use_i0_from: {'guinier', 'gnom', 'bift'} str, optional
        Determines whether the Rg and I(0) value used for the M.W. calculation
        is from the Guinier fit, or the GNOM or BIFT P(r) function. Ignored if
        both rg and i0 parameters are provided.

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

    if settings is not None:
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

    else:
        if qmin is None:
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
    settings=None, use_i0_from='guinier', A_prot=1.0, B_prot=0.1231,
    A_rna=0.808, B_rna=0.00934):
    """
    Calculates the M.W. of the input profile using the volume of correlation
    method. The input profile needs to have calculated Rg and I(0) values,
    either from a Guinier fit or from a IFT P(r) function, so the Rg and I(0)
    values are known. You must supply either protein, cutoff, and qmax,
    or settings.

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
        values in the settings.
        parameter. Default is None.
    use_i0_from: {'guinier', 'gnom', 'bift'} str, optional
        Determines whether the Rg and I(0) value used for the M.W. calculation
        is from the Guinier fit, or the GNOM or BIFT P(r) function. Ignored if
        both rg and i0 parameters are provided.
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

    if settings is not None:
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
    use_i0_from='guinier', write_profile=True, datadir=None, filename=None):
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
        The profile to calculate the M.W. for. If using write_profile false, you
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
        of the profile is used.
    atsas_dir: str, optional
        The directory of the atsas programs (the bin directory). If not provided,
        the API uses the auto-detected directory.
    use_i0_from: {'guinier', 'gnom', 'bift'} str, optional
        Determines whether the Rg and I(0) value used for the M.W. calculation
        is from the Guinier fit, or the GNOM or BIFT P(r) function. Ignored if
        both rg and i0 parameters are provided.
    write_profile: bool, optional
        If True, the input profile is written to file. If False, then the
        input profile is ignored, and the profile specified by datadir and
        filename is used. This is convenient if you are trying to process
        a lot of files that are already on disk, as it saves having to read
        in each file and then save them again. Defaults to True. In this case,
        Rg and I(0) must be specified, as they are not read from the file on disk.
    datadir: str, optional
        If write_profile is False, this is used as the path to the scattering
        profile on disk.
    filename: str, optional
        If write_profile is False, this is used as the filename of the scattering
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

    if write_profile:
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

                if first is None:
                    first = max(0, int(guinier_dict['nStart']) - profile.getQrange()[0])

            elif use_i0_from == 'gnom':
                gnom_dict = analysis_dict['GNOM']
                rg = float(gnom_dict['Real_Space_Rg'])
                i0 = float(gnom_dict['Real_Space_I0'])

                if first is None:
                    if 'guinier' in analysis_dict:
                        guinier_dict = analysis_dict['guinier']
                        first = max(0, int(guinier_dict['nStart']) - profile.getQrange()[0])
                    else:
                        first = 0

            elif use_i0_from == 'bift':
                bift_dict = analysis_dict['BIFT']
                rg = float(bift_dict['Real_Space_Rg'])
                i0 = float(bift_dict['Real_Space_I0'])

                if first is None:
                    if 'guinier' in analysis_dict:
                        guinier_dict = analysis_dict['guinier']
                        first = max(0, int(guinier_dict['nStart']) - profile.getQrange()[0])
                    else:
                        first = 0

        datadir = os.path.abspath(os.path.expanduser(tempfile.gettempdir()))
        filename = tempfile.NamedTemporaryFile(dir=datadir).name

        filename = os.path.split(filename)[-1] + '.dat'

        SASFileIO.writeRadFile(profile, os.path.join(datadir, filename), False)

    else:
        datadir = os.path.abspath(os.path.expanduser(datadir))

    if first is None:
        first = 0

    res = SASCalc.runDatmw(rg, i0, first, 'bayes', atsas_dir, datadir, filename)


    if write_profile and os.path.isfile(os.path.join(datadir, filename)):
        try:
            os.remove(os.path.join(datadir, filename))
        except Exception:
            pass

    if len(res) > 0:
        mw, mw_score, ci_lower, ci_upper, ci_score = res

        mw_prob = mw_score*100
        ci_prob = ci_score*100

        if profile is not None and write_profile:
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

def mw_datclass(profile, rg=None, i0=None, first=None, atsas_dir=None,
    use_i0_from='guinier', write_profile=True, datadir=None, filename=None):
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
        The profile to calculate the M.W. for. If using write_profile false, you
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
        of the profile is used.
    atsas_dir: str, optional
        The directory of the atsas programs (the bin directory). If not provided,
        the API uses the auto-detected directory.
    use_i0_from: {'guinier', 'gnom', 'bift'} str, optional
        Determines whether the Rg and I(0) value used for the M.W. calculation
        is from the Guinier fit, or the GNOM or BIFT P(r) function. Ignored if
        both rg and i0 parameters are provided.
    write_profile: bool, optional
        If True, the input profile is written to file. If False, then the
        input profile is ignored, and the profile specified by datadir and
        filename is used. This is convenient if you are trying to process
        a lot of files that are already on disk, as it saves having to read
        in each file and then save them again. Defaults to True.
    datadir: str, optional
        If write_profile is False, this is used as the path to the scattering
        profile on disk.
    filename: str, optional.
        If write_profile is False, this is used as the filename of the scattering
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

    if profile is not None:
        analysis_dict = profile.getParameter('analysis')
        if 'molecularWeight' in analysis_dict:
            mw_dict = analysis_dict['molecularWeight']
        else:
            mw_dict = {}

    if write_profile:
        if rg is None or i0 is None:
            if use_i0_from == 'guinier':
                guinier_dict = analysis_dict['guinier']
                rg = float(guinier_dict['Rg'])
                i0 = float(guinier_dict['I0'])

                if first is None:
                    first = max(0, int(guinier_dict['nStart']) - profile.getQrange()[0])

            elif use_i0_from == 'gnom':
                gnom_dict = analysis_dict['GNOM']
                rg = float(gnom_dict['Real_Space_Rg'])
                i0 = float(gnom_dict['Real_Space_I0'])

                if first is None:
                    if 'guinier' in analysis_dict:
                        guinier_dict = analysis_dict['guinier']
                        first = max(0, int(guinier_dict['nStart']) - profile.getQrange()[0])
                    else:
                        first = 0

            elif use_i0_from == 'bift':
                bift_dict = analysis_dict['BIFT']
                rg = float(bift_dict['Real_Space_Rg'])
                i0 = float(bift_dict['Real_Space_I0'])

                if first is None:
                    if 'guinier' in analysis_dict:
                        guinier_dict = analysis_dict['guinier']
                        first = max(0, int(guinier_dict['nStart']) - profile.getQrange()[0])
                    else:
                        first = 0

        datadir = os.path.abspath(os.path.expanduser(tempfile.gettempdir()))
        filename = tempfile.NamedTemporaryFile(dir=datadir).name

        filename = os.path.split(filename)[-1] + '.dat'

        SASFileIO.writeRadFile(profile, os.path.join(datadir, filename), False)

    else:
        datadir = os.path.abspath(os.path.expanduser(datadir))

    if first is None:
        first = 0

    res = SASCalc.runDatclass(rg, i0, first, atsas_dir, datadir, filename)


    if write_profile and os.path.isfile(os.path.join(datadir, filename)):
            try:
                os.remove(os.path.join(datadir, filename))
            except Exception:
                pass

    if len(res) > 0:
        shape, mw, dmax = res

        if profile is not None and write_profile:
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

def auto_dmax(profile, dmax_thresh=0.01, dmax_low_bound=0.5, dmax_high_bound=1.5,
    settings=None, use_atsas=True, single_proc=True):
    """
    Automatically calculate the maximum dimension (Dmax) value of a profile.
    By default uses BIFT, DATGNOM, and DATCLASS to find a starting value and
    then refines that starting value using GNOM. If use_atsas is False it just
    returns the BIFT value. It requires having an Rg from the Guinier fit.

    Parameters
    ----------
    profile: :class:`bioxtasraw.SASM.SASM`
        The profile to find the Dmax for.
    dmax_thresh: float, optional
        The threshold for refining the Dmax value. If the value of the P(r) at
        Dmax is greater than this threshold times the maximum value of the P(r)
        function Dmax is extended until the value falls below this fractional
        threshold or the Dmax exceeds the initial estimated value times the
        dmax_high_bound value. Defaults is 0.01.
    dmax_low_bound: float, optional
        If the end of the P(r) function contains negative values, Dmax is
        reduced until either no negative values exist or the Dmax becomes
        less than this parameter times the initial estimated value of Dmax.
        Default is 0.5.
    dmax_high_bound: float, optional
        If the value of the P(r) at Dmax is greater than dmax_thres times
        the maximum value of the P(r) function Dmax is extended until the value
        falls below that fractional threshold or the Dmax exceeds the initial
        estimated value times this parameter. Default is 1.5.
    settings: :class:`bioxtasraw.RAWSettings.RAWSettings`, optional
        RAW settings containing relevant parameters. Passed to BIFT. Default
        is None, which uses the default RAW settings.
    use_atsas: bool, optional
        Whether to use ATSAS functions. If False, simply returns the Dmax
        found by BIFT. Default is True.
    single_proc: bool, optional
        Whether to use one or multiple processors. Defaults to True.

    Returns
    -------
    dmax: int
        The maximum dimension found by this algorithm. Returns -1 if not found.
    """

    if settings is None:
        settings = __default_settings

    analysis_dict = profile.getParameter('analysis')
    try:
        rg = float(analysis_dict['guinier']['Rg'])
        i0 = float(analysis_dict['guinier']['I0'])
    except Exception:
        rg = -1
        i0 = -1

    datadir = os.path.abspath(os.path.expanduser(tempfile.gettempdir()))

    filename = tempfile.NamedTemporaryFile(dir=datadir).name
    filename = os.path.split(filename)[-1] + '.dat'

    if rg != -1:

        # Save profile
        save_profile = copy.deepcopy(profile)

        SASFileIO.writeRadFile(save_profile, os.path.join(datadir, filename),
            False)

        # Get Dmax from DATCLASS
        try:
            dc_dmax = float(analysis_dict['molecularWeight']['ShapeAndSize']['Dmax'])
        except Exception:
            dc_dmax = -1

        if dc_dmax == -1 and use_atsas:
            try:
                dc_mw, dc_shape, dc_dmax = mw_datclass(profile, rg, i0,
                    write_profile=False, datadir=datadir, filename=filename)
            except Exception:
                # traceback.print_exc()
                dc_dmax = -1

        if dc_dmax != -1:
            dmax = int(round(dc_dmax))

        else:
            #Calculate the IFT using BIFT
            try:
                bift_dmax = float(analysis_dict['BIFT']['Dmax'])
            except Exception:
                bift_dmax = -1

            if bift_dmax == -1:
                try:
                    (bift_ift, bift_dmax, bift_rg, bift_i0, bift_dmax_err,
                    bift_rg_err, bift_i0_err, bift_chi_sq, bift_log_alpha,
                    bift_log_alpha_err, bift_evidence,
                    bift_evidence_err) = bift(profile, use_guinier_start=False,
                    settings=settings, single_proc=single_proc)
                except Exception:
                    bift_dmax = -1

            #Calculate the IFT using DATGNOM
            if use_atsas:
                try:
                    (datgnom_ift, datgnom_dmax, datgnom_rg, datgnom_i0,
                    datgnom_rg_err, datgnom_i0_err, datgnom_total_est,
                    datgnom_chi_sq, datgnom_alpha, datgnom_quality) = datgnom(profile,
                    use_guinier_start=False, write_profile=False,
                    datadir=datadir, filename=filename)
                except Exception:
                    datgnom_dmax = -1
            else:
                datgnom_dmax = -1

            if bift_dmax != -1 and datgnom_dmax != -1:
                dmax = np.mean([bift_dmax, datgnom_dmax])

            elif bift_dmax != -1:
                dmax = bift_dmax*0.79

            elif datgnom_dmax != -1:
                dmax = datgnom_dmax*1.2

            else:
                dmax = -1

            if dmax != -1:
                dmax = round(dmax)

        if dmax != -1 and use_atsas:
            # Refine if Dmax is too long
            ift_results = gnom(profile, dmax, use_guinier_start=False,
                settings=settings, write_profile=False, datadir=datadir,
                filename=filename)
            ift = ift_results[0]
            dmax_start = dmax

            while dmax > dmax_start*dmax_low_bound and np.any(ift.p[-20:] < 0):
                dmax = dmax -1
                ift_results = gnom(profile, dmax, use_guinier_start=False,
                    settings=settings, write_profile=False, datadir=datadir,
                    filename=filename)
                ift = ift_results[0]

            #Refine if Dmax is too long
            ift_results = gnom(profile, dmax, dmax_zero=False,
                use_guinier_start=False, settings=settings,
                write_profile=False, datadir=datadir, filename=filename)
            ift_unforced = ift_results[0]

            refined_shorter = False

            while (dmax > dmax_start*dmax_low_bound
                and ift_unforced.p[-1]<dmax_thresh*ift_unforced.p.max()):
                dmax = dmax -1
                ift_results = gnom(profile, dmax, dmax_zero=False,
                    use_guinier_start=False, settings=settings,
                    write_profile=False, datadir=datadir, filename=filename)
                ift_unforced = ift_results[0]

                refined_shorter = True

            if refined_shorter:
                dmax = dmax +1

            if dmax_start == dmax:
                #Refine if Dmax is too short
                ift_results = gnom(profile, dmax, dmax_zero=False,
                    use_guinier_start=False, settings=settings,
                    write_profile=False, datadir=datadir, filename=filename)
                ift_unforced = ift_results[0]
                dmax_start = dmax

                while (dmax < dmax_start*dmax_high_bound
                    and ift_unforced.p[-1]>dmax_thresh*ift_unforced.p.max()):
                    dmax = dmax +1
                    ift_results = gnom(profile, dmax, dmax_zero=False,
                        use_guinier_start=False, settings=settings,
                        write_profile=False, datadir=datadir, filename=filename)
                    ift_unforced = ift_results[0]

    else:
        dmax = -1

    if os.path.isfile(os.path.join(datadir, filename)):
        try:
            os.remove(os.path.join(datadir, filename))
        except Exception:
            pass

    dmax = int(round(dmax))

    return dmax

def bift(profile, idx_min=None, idx_max=None, pr_pts=100, alpha_min=150,
    alpha_max=1e10, alpha_pts=16, dmax_min=10, dmax_max=400, dmax_pts=10,
    mc_runs=300, use_guinier_start=True, single_proc=True, nprocs=None,
    settings=None):
    """
    Calculates the Bayesian indirect Fourier transform (BIFT) of a scattering
    profile to generate a P(r) function and determine the maximum dimension
    Dmax. Returns None and -1 values if BIFT fails.

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
    single_proc: bool, optional
        Whether to use one or multiple processors. Defaults to True. In limited
        testing the single processor version has been found to be 2-3x faster
        than the multiprocessor version, but actual results may depend on
        the computer and the number of gird search points.
    nprocs: int, optional
        If specified, and single_proc is False, determines the number of processors
        to use for BIFT. Otherwise defaults to number of processors in the computer
        -1 (minimum 1).
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
            idx_min = max(0, int(guinier_dict['nStart']) - profile.getQrange()[0])
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

    if nprocs is None:
        nprocs = 0

    bift_settings = {
        'npts'      : pr_pts,
        'alpha_max' : alpha_max,
        'alpha_min' : alpha_min,
        'alpha_n'   : alpha_pts,
        'dmax_min'  : dmax_min,
        'dmax_max'  : dmax_max,
        'dmax_n'    : dmax_pts,
        'mc_runs'   : mc_runs,
        'single_proc' : single_proc,
        'nprocs'    : nprocs,
        }

    ift = BIFT.doBift(q, i, err, filename, **bift_settings)

    if ift is not None:

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

    else:
        dmax = -1
        dmax_err = -1
        rg = -1
        rg_err = -1
        i0 = -1
        i0_err = -1
        chi_sq = -1
        log_alpha = -1
        log_alpha_err = -1
        evidence = -1
        evidence_err = -1
        qmin = q[0]
        qmax = q[-1]

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
                idx_min = max(0, int(guinier_dict['nStart']) - profile.getQrange()[0])
            else:
                idx_min = 0

        elif idx_min is None:
            idx_min = 0

        if idx_max is None:
            if cut_8rg:
                q = save_profile.getQ()
                idx_max = np.argmin(np.abs(q-(8/rg)))
            else:
                idx_max = save_profile.getQrange()[1]

        SASFileIO.writeRadFile(save_profile, os.path.join(datadir, filename),
            False)

    if idx_min is None:
        idx_min = 0

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

        if ift is not None:
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

        if profile is not None and write_profile:
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
    cut_dam=False, write_profile=True, datadir=None, filename=None,
    save_ift=False, savename=None, settings=None, dmin_zero=True, npts=0,
    system=0, radius56=-1, rmin=-1):
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
        cut_dam.
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
    cut_dam: bool, optional
        If set to True and no idx_max is provided, then the profile is
        automatically truncated at q=8/Rg or 0.3 1/A, whichever is smaller.
        This is useful for bead models
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
    system: int, optional
        Defines the job type as in the GNOM manual. Default is 0, a
        monodisperse system.
    radius56: float, optional
        The radius/thickness for system type 5/6. Default is not used.
    rmin: float, optional
        Minimum size for system types 1-6. Default is not used.



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


    if profile is not None:
        analysis_dict = profile.getParameter('analysis')

    # Save profile if necessary, truncating q range as appropriate
    if write_profile:
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
            if 'guinier' in analysis_dict:
                guinier_dict = analysis_dict['guinier']
                idx_min = max(0, int(guinier_dict['nStart']) - save_profile.getQrange()[0])
            else:
                idx_min = 0

        elif idx_min is None:
            idx_min = 0

        if idx_max is None:
            if cut_dam:
                q = save_profile.getQ()
                max_q = min(8/rg, 0.3)
                idx_max = np.argmin(np.abs(q-max_q)) -save_profile.getQrange()[0]
            else:
                idx_max = save_profile.getQrange()[1] -save_profile.getQrange()[0]

        SASFileIO.writeRadFile(save_profile, os.path.join(datadir, filename),
            False)

    else:
        if idx_min is None and use_guinier_start and profile is not None:
            if 'guinier' in analysis_dict:
                guinier_dict = analysis_dict['guinier']
                idx_min = max(0, int(guinier_dict['nStart']) - profile.getQrange()[0] )
            else:
                idx_min = 0

        elif idx_min is None:
            idx_min = 0

        if idx_max is None and profile is not None:
            if cut_dam:
                q = profile.getQ()
                max_q = min(8/rg, 0.3)
                idx_max = np.argmin(np.abs(q-max_q)) -profile.getQrange()[0]
            else:
                idx_max = profile.getQrange()[1] -profile.getQrange()[0]


    #Initialize settings
    if settings is not None:
        gnom_settings = {
            'rmin_zero'     : settings.get('gnomForceRminZero'),
            'rmax_zero'     : dmax_zero,
            'npts'          : settings.get('gnomNPoints'),
            'alpha'         : alpha,
            'first'         : idx_min,
            'last'          : idx_max,
            'system'        : settings.get('gnomSystem'),
            'radius56'      : settings.get('gnomRadius56'),
            'rmin'          : settings.get('gnomRmin'),
            }

    else:
        settings = __default_settings

        if dmin_zero:
            dmin_zero = 'Y'
        else:
            dmin_zero = 'N'

        if dmax_zero:
            dmax_zero = 'Y'
        else:
            dmax_zero = 'N'

        gnom_settings = {
            'rmin_zero'     : dmin_zero,
            'rmax_zero'     : dmax_zero,
            'npts'          : npts,
            'alpha'         : alpha,
            'first'         : idx_min,
            'last'          : idx_max,
            'alpha'         : alpha,
            'system'        : system,
            'radius56'      : radius56,
            'rmin'          : rmin,
            }

    # Run the IFT
    ift = SASCalc.runGnom(filename, save_ift, dmax, gnom_settings, datadir,
        atsas_dir, savename, True)

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

    # Save results
    if ift is not None:
        if not save_ift:
            if write_profile:
                ift_name = profile.getParameter('filename')
            else:
                ift_name = filename

            ift_name = os.path.splitext(ift_name)[0] + '.out'
            ift.setParameter('filename', ift_name)


        try:
            dmax = float(ift.getParameter('dmax'))
        except Exception:
            dmax = -1

        try:
            rg = float(ift.getParameter('rg'))
        except Exception:
            rg = -1

        try:
            rg_err = float(ift.getParameter('rger'))
        except Exception:
            rg_err = -1

        try:
            i0 = float(ift.getParameter('i0'))
        except Exception:
            i0 = -1

        try:
            i0_err = float(ift.getParameter('i0er'))
        except Exception:
            i0_err = -1

        try:
            chi_sq = float(ift.getParameter('chisq'))
        except Exception:
            chi_sq = -1

        try:
            alpha = float(ift.getParameter('alpha'))
        except Exception:
            alpha = -1

        try:
            total_est = float(ift.getParameter('TE'))
        except Exception:
            total_est = -1

        quality = ift.getParameter('quality')

        if profile is not None:

            if round(float(dmax)) == dmax:
                dmax = int(dmax)

            results_dict = {}
            results_dict['Dmax'] = str(dmax)
            results_dict['Total_Estimate'] = total_est
            results_dict['Real_Space_Rg'] = rg
            results_dict['Real_Space_Rg_Err'] = rg_err
            results_dict['Real_Space_I0'] = i0
            results_dict['Real_Space_I0_Err'] = i0_err
            results_dict['GNOM_ChiSquared'] = chi_sq
            results_dict['Alpha'] = alpha
            results_dict['qStart'] = profile.getQ()[idx_min-1]
            results_dict['qEnd'] = profile.getQ()[idx_max-1]
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
        The input profiles (:class:`bioxtasraw.SASM.SASM`) to be compared.
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

    if atsas_dir is None:
        atsas_dir = __default_settings.get('ATSASDir')

    score, categories, evaluation = SASCalc.run_ambimeter_from_ift(ift, atsas_dir,
        qRg_max, save_models, save_prefix, datadir, write_ift, filename)

    return score, categories, evaluation

def dammif(ift, prefix, datadir, mode='Slow', symmetry='P1', anisometry='Unknown',
    write_ift=True, ift_name=None, atsas_dir=None, settings=None, unit='Unknown',
    omit_solvent=True, chained=False, expected_shape='u', random_seed='',
    constant='', max_bead_count=-1, dam_radius=-1, harmonics=-1, prop_to_fit=-1,
    curve_weight='e', max_steps=-1, max_iters=-1, max_success=-1,
    min_success=-1, T_factor=-1, rg_penalty=-1, center_penalty=-1,
    loose_penalty=-1, abort_event=None, readback_queue=None):
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
    abort_event: :class:`threading.Event`, optional
        A :class:`threading.Event` or :class:`multiprocessing.Event`. If this
        event is set it will abort the dammin run.
    readback_queue: :class:`queue.Queue`, optional
        If provided, any command line output (STDIN, STDERR) is placed in the
        queue.

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

    if abort_event is None:
        abort_event = threading.Event()
    if readback_queue is None:
        readback_queue = queue.Queue()
    read_semaphore = threading.BoundedSemaphore(1)

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

    readout_t = threading.Thread(target=SASUtils.enqueue_output,
        args=(proc, readback_queue, read_semaphore))
    readout_t.daemon = True
    readout_t.start()

    if proc is not None:
        while proc.poll() is None:
            if abort_event.is_set():
                proc.terminate()
                break

    if write_ift and os.path.isfile(os.path.join(datadir, ift_name)):
        try:
            os.remove(os.path.join(datadir, ift_name))
        except Exception:
            pass

    if not abort_event.is_set():
        dam_name = os.path.join(datadir, prefix+'-1.pdb')
        fir_name = os.path.join(datadir, prefix+'.fir')

        _, _, model_data = SASFileIO.loadPDBFile(dam_name)

        sasm, fit_sasm = SASFileIO.loadFitFile(fir_name)
        chi_sq = float(sasm.getParameter('counters')['Chi_squared'])

        rg = float(model_data['rg'])
        dmax = float(model_data['dmax'])
        excluded_volume=float(model_data['excluded_volume'])
        mw = float(model_data['mw'])
    else:
        chi_sq = -1
        rg = -1
        dmax = -1
        mw = -1
        excluded_volume = -1

    return chi_sq, rg, dmax, mw, excluded_volume


def dammin(ift, prefix, datadir, mode='Slow', symmetry='P1', anisometry='Unknown',
    initial_dam=None, write_ift=True, ift_name=None, atsas_dir=None,
    settings=None, unit='Unknown', constant=0, dam_radius=-1, harmonics=-1,
    prop_to_fit=-1, curve_weight='1', max_steps=-1, max_iters=-1, max_success=-1,
    min_success=-1, T_factor=-1, loose_penalty=-1, knots=20, sphere_diam=-1,
    coord_sphere=-1, disconnect_penalty=-1, periph_penalty=1,
    abort_event=None, readback_queue=None):
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
    abort_event: :class:`threading.Event`, optional
        A :class:`threading.Event` or :class:`multiprocessing.Event`. If this
        event is set it will abort the dammif run.
    readback_queue: :class:`queue.Queue`, optional
        If provided, any command line output (STDIN, STDERR) is placed in the
        queue.

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

    if abort_event is None:
        abort_event = threading.Event()
    if readback_queue is None:
        readback_queue = queue.Queue()
    read_semaphore = threading.BoundedSemaphore(1)

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

    readout_t = threading.Thread(target=SASUtils.enqueue_output,
        args=(proc, readback_queue, read_semaphore))
    readout_t.daemon = True
    readout_t.start()

    if proc is not None:
        while proc.poll() is None:
            if abort_event.is_set():
                proc.terminate()
                break

    if write_ift and os.path.isfile(os.path.join(datadir, ift_name)):
        try:
            os.remove(os.path.join(datadir, ift_name))
        except Exception:
            pass

    dam_name = os.path.join(datadir, prefix+'-1.pdb')
    fir_name = os.path.join(datadir, prefix+'.fir')

    if not abort_event.is_set():
        _, _, model_data = SASFileIO.loadPDBFile(dam_name)

        sasm, fit_sasm = SASFileIO.loadFitFile(fir_name)
        chi_sq = float(sasm.getParameter('counters')['Chi_squared'])

        rg = float(model_data['rg'])
        dmax = float(model_data['dmax'])
        excluded_volume=float(model_data['excluded_volume'])
        mw = float(model_data['mw'])
    else:
        chi_sq = -1
        rg = -1
        dmax = -1
        mw = -1
        excluded_volume = -1

    return chi_sq, rg, dmax, mw, excluded_volume

def damaver(files, prefix, datadir, symmetry='P1', enantiomorphs='YES',
    nbeads=5000, method='NSD', lm=5, ns=51, smax=0.5, atsas_dir=None,
    settings=None, abort_event=None, readback_queue=None):
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
        symmetry that DAMAVER will accept. Defaults to 'P1'. Note, not used
        in ATSAS version >= 3.1.0
    enantiomorphs: str, optional
        Search enantiomorphs. Can be YES or NO. Default YES.
    nbeads: int, optional
        Number of beads within the resulting DAM. Default 5000.
    method: str, optional
        The method used by damaver. May be NSD, NCC, or ICP. Only used in ATSAS
        version >= 3.1.0. Default NSD.
    lm: int, optional
        Number of spherical harmonics used in NCC mode. Only used in ATSAS
        version >=3.1.0. Default 5.
    ns: int, optional
        Number of data points used in NCC mode. Only used in ATSAS version
        >=3.1.0. Default 51.
    smax: float, optional
        Maximum scattering angle in 1/A used in NCC mode. Only used in ATSAS
        version >=3.1.0. Default 0.5.
    atsas_dir: str, optional
        The directory of the atsas programs (the bin directory). If not provided,
        the API uses the auto-detected directory.
    settings: :class:`bioxtasraw.RAWSettings.RAWSettings`, optional
        RAW settings containing relevant parameters. If provided, every
        parameter except symmetry is overridden with the value in the settings
        file. Default is None.
    abort_event: :class:`threading.Event`, optional
        A :class:`threading.Event` or :class:`multiprocessing.Event`. If this
        event is set it will abort the damaver run.
    readback_queue: :class:`queue.Queue`, optional
        If provided, any command line output (STDIN, STDERR) is placed in the
        queue.

    Returns
    -------
    mean_nsd: float
        The mean NSD of the models.
    stdev_nsd: float
        The standard deviation of the NSD of the models.
    rep_model: str
        The name of the representative model determined by DAMAVER.
    result_dict: dict
        A dictionary of the model specific results. The keys are the input
        filenames. The values are lists of the form ['Include', mean_model_nsd]
        where 'Include' indicates the model was in the average whereas a
        different value indicates the model was excluded from the average.
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

    if abort_event is None:
        abort_event = threading.Event()
    if readback_queue is None:
        readback_queue = queue.Queue()
    read_semaphore = threading.BoundedSemaphore(1)

    if settings is None:
        damaver_settings = {
            'symmetry'      : symmetry,
            'enantiomorphs' : enantiomorphs,
            'nbeads'        : nbeads,
            'method'        : method,
            'lm'            : lm,
            'ns'            : ns,
            'smax'          : smax,
            }
    else:
        damaver_settings = {
            'symmetry'      : symmetry,
            'enantiomorphs' : settings.get('damaverEnantiomers'),
            'nbeads'        : settings.get('damaverNbeads'),
            'method'        : settings.get('damaverMethod'),
            'lm'            : settings.get('damaverHarmonics'),
            'ns'            : settings.get('damaverPoints'),
            'smax'          : settings.get('damaverQmax'),
            }

    datadir = os.path.abspath(os.path.expanduser(datadir))

    proc = SASCalc.runDamaver(files, datadir, atsas_dir, prefix, **damaver_settings)

    readout_t = threading.Thread(target=SASUtils.enqueue_output,
        args=(proc, readback_queue, read_semaphore))
    readout_t.daemon = True
    readout_t.start()

    if proc is not None:
        while proc.poll() is None:
            if abort_event.is_set():
                proc.terminate()
                break

    version = SASCalc.getATSASVersion(atsas_dir).split('.')

    if (int(version[0]) == 3 and int(version[1]) < 1) or int(version[0]) < 3:
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

        if not abort_event.is_set():
            (mean_nsd, stdev_nsd, include_list, discard_list, result_dict, res, res_err,
                res_unit) = SASFileIO.loadDamselLogFile(damsel_path)

            mean_nsd = float(mean_nsd)
            stdev_nsd = float(stdev_nsd)
            res = float(res)
            res_err = float(res_err)

            model_data, rep_model = SASFileIO.loadDamsupLogFile(damsup_path)
        else:
            mean_nsd = -1
            stdev_nsd = -1
            rep_model = ''
            result_dict = {}
            res = -1
            res_err = -1
            res_unit = ''

    else:
        if not abort_event.is_set():
            dist_path = os.path.join(datadir, prefix+'-distances.txt')
            summary_path = os.path.join(datadir, prefix+'-global-summary.txt')

            mean_nsd, stdev_nsd, model_nsds = SASFileIO.loadDamaverDistancesFile(dist_path)
            rep_model, model_includes = SASFileIO.loadDamaverGlobalSummaryFile(summary_path)

            mean_nsd = float(mean_nsd)
            stdev_nsd = float(stdev_nsd)
            res = -1
            res_err = -1
            res_unit = ''

            result_dict = {}

            for model_name in model_nsds:
                if model_includes[model_name]:
                    inc = 'Include'
                else:
                    inc = 'Not'
                result_dict[model_name] = [inc, float(model_nsds[model_name])]

        else:
            mean_nsd = -1
            stdev_nsd = -1
            rep_model = ''
            result_dict = {}
            res = -1
            res_err = -1
            res_unit = ''

    return mean_nsd, stdev_nsd, rep_model, result_dict, res, res_err, res_unit

def damclust(files, prefix, datadir, symmetry='P1', atsas_dir=None,
    abort_event=None, readback_queue=None):
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
    abort_event: :class:`threading.Event`, optional
        A :class:`threading.Event` or :class:`multiprocessing.Event`. If this
        event is set it will abort the damclust run.
    readback_queue: :class:`queue.Queue`, optional
        If provided, any command line output (STDIN, STDERR) is placed in the
        queue.

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

    if abort_event is None:
        abort_event = threading.Event()
    if readback_queue is None:
        readback_queue = queue.Queue()
    read_semaphore = threading.BoundedSemaphore(1)

    datadir = os.path.abspath(os.path.expanduser(datadir))

    proc = SASCalc.runDamclust(files, datadir, atsas_dir, symmetry)

    readout_t = threading.Thread(target=SASUtils.enqueue_output,
        args=(proc, readback_queue, read_semaphore))
    readout_t.daemon = True
    readout_t.start()

    if proc is not None:
        while proc.poll() is None:
            if abort_event.is_set():
                proc.terminate()
                break

    damclust_log = os.path.join(datadir, prefix+'_damclust.log')
    new_files = [(os.path.join(datadir, 'damclust.log'), damclust_log)]

    for item in new_files:
        if os.path.isfile(item[0]):
            os.rename(item[0], item[1])

    if not abort_event.is_set():
        cluster_list, distance_list = SASFileIO.loadDamclustLogFile(damclust_log)
    else:
        cluster_list = []
        distance_list = []

    return cluster_list, distance_list

def supcomb(target, ref_file, datadir, mode='fast', superposition='ALL',
        enantiomorphs='YES', proximity='NSD', symmetry='P1', fraction='1.0',
        atsas_dir=None, settings=None, abort_event=None, readback_queue=None):
    """
    Aligns the target to the reference file using SUPCOMB from the ATSAS
    package. Require a separate installation of ATSAS. Both files must be
    in the same folder, and the aligned file is output in the folder. The
    aligned file will have the same name as the target file with _aligned
    appended to the end of the name. This function blocks until SUPCOMB is
    done. SUPCOMB is only available in ATSAS <3.1.0.

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
    settings: :class:`bioxtasraw.RAWSettings.RAWSettings`, optional
        RAW settings containing relevant parameters. If provided, every
        parameter except symmetry is overridden with the value in the settings
        file. Default is None.
    abort_event: :class:`threading.Event`, optional
        A :class:`threading.Event` or :class:`multiprocessing.Event`. If this
        event is set it will abort the supcomb run.
    readback_queue: :class:`queue.Queue`, optional
        If provided, any command line output (STDIN, STDERR) is placed in the
        queue.
    """

    if atsas_dir is None:
        atsas_dir = __default_settings.get('ATSASDir')

    if abort_event is None:
        abort_event = threading.Event()
    if readback_queue is None:
        readback_queue = queue.Queue()
    read_semaphore = threading.BoundedSemaphore(1)

    if settings is None:
        supcomb_settings = {
            'mode'          : mode,
            'superposition' : superposition,
            'enantiomorphs' : enantiomorphs,
            'proximity'     : proximity,
            'symmetry'      : symmetry,
            'fraction'      : fraction,
            }
    else:
        supcomb_settings = {
            'mode'          : settings.get('supcombMode'),
            'superposition' : settings.get('supcombSuperpositon'),
            'enantiomorphs' : settings.get('supEnantiomorphs'),
            'proximity'     : settings.get('supcombMethod'),
            'symmetry'      : symmetry,
            'fraction'      : settings.get('supcombFraction'),
            }


    proc = SASCalc.runSupcomb(ref_file, target, datadir, atsas_dir, **supcomb_settings)

    readout_t = threading.Thread(target=SASUtils.enqueue_output,
        args=(proc, readback_queue, read_semaphore))
    readout_t.daemon = True
    readout_t.start()

    if proc is not None:
        while proc.poll() is None:
            if abort_event.is_set():
                proc.terminate()
                break

            if proc.stdout is not None:
                proc.stdout.read(1)

    return

def cifsup(target, ref_file, datadir, method='ICP', selection='ALL',
        enantiomorphs='YES', target_model_id=1, ref_model_id=1, lm=5, ns=51,
        smax=0.5, beads=2000, atsas_dir=None, settings=None,
        abort_event=None, readback_queue=None):
    """
    Aligns the target to the reference file using CIFSUP from the ATSAS
    package. Require a separate installation of ATSAS. Both files must be
    in the same folder, and the aligned file is output in the folder. The
    aligned file will have the same name as the target file with _aligned
    appended to the end of the name. This function blocks until CIFSUP is
    done. CIFSUP is only available in ATSAS >=3.1.0.

    Parameters
    ----------
    target: str
        The target file name, without path. This file is aligned to the
        reference file, and must be in the same folder as the reference file.
        Called the movable file in the CIFSUP manual.
    ref_file: str
        The reference file name, without path. Called the static or template
        file in the CIFSUP manual.
    datadir: str
        The directory containing both the target and ref_file. It is also the
        directory for the output file.
   method: {'NSD, 'NCC', 'ICP', 'RMSD'} str, optional
        What method to use to determine distance between two models. Default
        is ICP.
    selection: {'ALL', 'BACKBONE', 'REGRID', 'SHELL'} str, optional
        What portion of the molecule to use for alignment. Default is ALL.
    enantiomorphs: {'YES', 'NO'} str, optional
        Whether to generate enantiomorphs during alignment. Default is YES.
    target_model_id: int, optional
        Model ID in the target file. Default is 1.
    ref_model_id: int, optional
        Model ID in the reference file. Default is 1.
    lm: int, optional
        Number of spherical harmonics used in NCC mode. Default 5.
    ns: int, optional
        Number of data points used in NCC mode. Default 51.
    smax: float, optional
        Maximum scattering angle in 1/A used in NCC mode. Default 0.5.
    beads: int, optional
        Number of beads used for the REGRID method. Default 2000.
    atsas_dir: str, optional
        The directory of the atsas programs (the bin directory). If not provided,
        the API uses the auto-detected directory.
    settings: :class:`bioxtasraw.RAWSettings.RAWSettings`, optional
        RAW settings containing relevant parameters. If provided, every
        parameter is overridden with the value in the settings file. Default is None.
    abort_event: :class:`threading.Event`, optional
        A :class:`threading.Event` or :class:`multiprocessing.Event`. If this
        event is set it will abort the CIFSUP run.
    readback_queue: :class:`queue.Queue`, optional
        If provided, any command line output (STDIN, STDERR) is placed in the
        queue.
    """

    if atsas_dir is None:
        atsas_dir = __default_settings.get('ATSASDir')

    if abort_event is None:
        abort_event = threading.Event()
    if readback_queue is None:
        readback_queue = queue.Queue()
    read_semaphore = threading.BoundedSemaphore(1)

    if settings is None:
        cifsup_settings = {
            'method'            : method,
            'selection'         : selection,
            'enantiomorphs'     : enantiomorphs,
            'target_model_id'   : target_model_id,
            'ref_model_id'      : ref_model_id,
            'lm'                : lm,
            'ns'                : ns,
            'smax'              : smax,
            'beads'             : beads,
            }
    else:
        cifsup_settings = {
            'method'            : settings.get('cifsupMethod'),
            'selection'         : settings.get('cifsupSelection'),
            'enantiomorphs'     : settings.get('supEnantiomorphs'),
            'target_model_id'   : settings.get('cifsupTargetID'),
            'ref_model_id'      : settings.get('cifsupRefID'),
            'lm'                : settings.get('cifsupHarmonics'),
            'ns'                : settings.get('cifsupPoints'),
            'smax'              : settings.get('cifsupQmax'),
            'beads'             : settings.get('cifsupBeads'),
            }



    proc = SASCalc.runCifsup(ref_file, target, datadir, atsas_dir, **cifsup_settings)

    readout_t = threading.Thread(target=SASUtils.enqueue_output,
        args=(proc, readback_queue, read_semaphore))
    readout_t.daemon = True
    readout_t.start()

    if proc is not None:
        while proc.poll() is None:
            if abort_event.is_set():
                proc.terminate()
                break

    return

def denss(ift, prefix, datadir, mode='Slow', symmetry=0, sym_axis='X',
    sym_type='Cyclical', initial_model=None, n_electrons=None, settings=None,
    voxel=5, oversampling=3, steps=10000,
    recenter=True, recenter_step=list(range(1001,8002, 500)),
    recenter_mode='com', positivity=True, extrapolate=True, shrinkwrap=True,
    sw_sigma_start=3.0, sw_sigma_end=1.5, sw_sigma_decay=0.99,
    sw_sigma_thresh=0.2, sw_iter=20, sw_min_step=5000, connected=True,
    connectivity_step=[7500], chi_end_frac=0.001, cut_output=False,
    write_xplor=False, sym_step=[3000, 5000, 7000, 9000], seed=None,
    abort_event=None, gpu=False):
    """
    Generates an electron density reconstruction using DENSS. Function blocks
    until DENSS finishes. Can be used to refine an existing model.

    Parameters
    ----------
    ift: :class:`bioxtasraw.SASM.IFTM`
        The IFT to be used as DENSS input.
    prefix: str
        The output prefix for the DENSS model.
    datadir: str
        The output directory for the DENSS model.
    mode: {'Fast', 'Slow' 'Custom'} str, optional
        The DENSS mode. Note that some of the advanced settings require that
        DENSS be in 'Custom' mode to use. Defaults to slow.
    symmetry: int, optional
        Rotational symmetry applied as n-fold symmetry about the sym_axis.
        Default is 0, i.e. no symmetry.
    sym_axis: {'X', 'Y', 'Z'} str, optional
        The symmetry axis used if a symmetry is specified. Correspond to the
        xyz principal axes.
    sym_type: {'Cyclical', 'Dihedral'}
        The symmetry type to use, either cyclical or dihedral.
    initial_model: class:`numpy.array`, optional
        Initial electron density model as a numpy array. If input is provided,
        then the model will be refined.
    n_electrons: int, optional
        Number of electrons in the molecule. If provided, the output density
        will be scaled so that the sum of the density across the occupied volume
        is equal to this value.
    settings: :class:`bioxtasraw.RAWSettings.RAWSettings`, optional
        RAW settings containing relevant parameters. If provided, every model
        parameter except mode, symmetry, and sym_axis, and n_electrons is
        overridden with the value in the settings file. Default is None.
    voxel: float, optional
        The voxel size for the model. Only used in Custom mode.
    oversampling: int, optional
        The sampling ratio.
    steps: int, optional
        Maximum number of iterations of the denss algorithm. Only used
        in Custom mode.
    recenter: bool, optional
        Whether the particle should be recentered at the origin during
        reconstruction. Default is True.
    recenter_step: list, optional
        A list of integers specifying the steps at which recentering
        should be carried out. Only used in custom mode.
    recenter_mode: {'com', 'max'} str, optional
        Recenter based on the center of mass (com) or maximum density (max).
        Default is com.
    positivity: bool, optional
        Enforces positive density. Only used in Custom mode. Default is True.
        Set to False in Membrane mode.
    extrapolate: bool, optional
        Whether to extrapolate the measured scattering profile based on the
        voxel size. Default is True.
    shrinkwrap: bool, optional
        Whether to apply the shrinkwrap algorithm to determine the underlying
        support. Default is True. Not recommended to change.
    sw_sigma_start: float, optional
        The starting value to use for blurring during the shrinkwrap algorithm.
        Default is 3.0.
    sw_sigma_end: float, optional
        The ending value to use for blurring during the shrinkwrap algorithm.
        Default is 1.5.
    sw_sigma_decay: float, optional
        How quickly the sw_sigma value transitions from start to end.
    sw_sigma_thresh: float, optional
        The minimum threshold for inclusion of a voxel in the support during
        the shrinkwrap algorithm. Membrane mode sets this to 0.1.
    sw_iter: int, optional
        How often the shrinkwrap algorithm is applied. Not recommended to
        change.
    sw_min_step: int, optional
        The first step at which the shrinkwrap algorithm is applied. Only used
        in Custom mode.
    connected: bool, optional
        Whether connectivity is enforced for the reconstruction. Default is
        True.
    connectivity_step: list, optional
        A list of integers specifying the steps at which connectivity is
        enforced. Only used in Custom model.
    chi_end_frac: float, optional
        The convergence criteria. Set as the minimum threshold of the chi
        squared standard deviation in the last 100 steps, as a fraction of
        the median chi squared in those steps.
    cut_output: bool, optional
        Whether to remove unused parts of the search space when writing the
        output electron density files. Default is False.
    write_xplor:  bool, optional
        Whether to write the output density as xplor files and mrc files, or
        just mrc files. Default is False.
    sym_step: list, optional
        A list of integers specifying the steps at which the symmetry
        constraint should be applied.
    seed: int, optional
        The random seed to be used for the DENSS reconstruction. If None
        (default) than a new seed is generated.
    abort_event: :class:`threading.Event`, optional
        A :class:`threading.Event` or :class:`multiprocessing.Event`. If this
        event is set it will abort the denss run.
    gpu: bool, optional
        Whether to use GPU computing for DENSS. CuPy must be installed.

    Returns
    -------
    rho: :class:`numpy.array`
        The calculated electron density of the model.
    chi_sq: float
        The chi squared value of the model fit to the data.
    rg: float
        The radius of gyration of the model.
    support_vol: float
        The support volume of the mode.
    side: float
        The real space box width in Angstroms of the reconstruction.
    q_fit: :class:`numpy.array`
        The q values, including any extrapolation, of the model fit to the data.
    I_fit: :class:`numpy.array`
        The I values, including any extrapolation, of the model fit to the data.
    I_extrap: :class:`numpy.array`
        The experimental intensity, including any extrapolation, used in the
        reconstruction.
    err_extrap: :class:`numpy.array`
        The experimental uncertainty, including any extrapolation, used in the
        reconstruction.
    all_chi_sq: :class:`numpy.array`
        The value of chi squared at all iterations of the DENSS algorithm.
        Useful to check convergence.
    all_rg: :class:`numpy.array`
        The value of rg at all iterations of the DENSS algorithm. Useful to
        check convergence.
    all_support_vol: :class:`numpy.array`
        The value of support volume at all iterations of the DENSS algorithm.
        Useful to check convergence.
    """

    datadir = os.path.abspath(os.path.expanduser(datadir))

    if abort_event is None:
        abort_event = threading.Event()

    if settings is not None:
        denss_settings = {
            'voxel'             : settings.get('denssVoxel'),
            'oversample'        : settings.get('denssOversampling'),
            'electrons'         : n_electrons,
            'steps'             : settings.get('denssSteps'),
            # 'limitDmax'         : settings.get('denssLimitDmax'),
            # 'dmaxStep'          : settings.get('denssLimitDmaxStep'),
            'recenter'          : settings.get('denssRecenter'),
            'recenterStep'      : settings.get('denssRecenterStep'),
            'positivity'        : settings.get('denssPositivity'),
            'extrapolate'       : settings.get('denssExtrapolate'),
            'shrinkwrap'        : settings.get('denssShrinkwrap'),
            'swSigmaStart'      : settings.get('denssShrinkwrapSigmaStart'),
            'swSigmaEnd'        : settings.get('denssShrinkwrapSigmaEnd'),
            'swSigmaDecay'      : settings.get('denssShrinkwrapSigmaDecay'),
            'swThresFrac'       : settings.get('denssShrinkwrapThresFrac'),
            'swIter'            : settings.get('denssShrinkwrapIter'),
            'swMinStep'         : settings.get('denssShrinkwrapMinStep'),
            'connected'         : settings.get('denssConnected'),
            'conSteps'          : settings.get('denssConnectivitySteps'),
            'chiEndFrac'        : settings.get('denssChiEndFrac'),
            'cutOutput'         : settings.get('denssCutOut'),
            'writeXplor'        : settings.get('denssWriteXplor'),
            'mode'              : mode,
            'recenterMode'      : settings.get('denssRecenterMode'),
            # 'minDensity'        : settings.get('denssMinDensity'),
            # 'maxDensity'        : settings.get('denssMaxDensity'),
            # 'flattenLowDensity' : settings.get('denssFlattenLowDensity'),
            'ncs'               : symmetry,
            'ncsSteps'          : settings.get('denssNCSSteps'),
            'ncsAxis'           : str(sym_axis),
            'ncsType'           : sym_type,
            'seed'              : seed,
            'denssGPU'          : settings.get('denssGPU')
            }

    else:
        denss_settings = {
            'voxel'             : voxel,
            'oversample'        : oversampling,
            'electrons'         : n_electrons,
            'steps'             : steps,
            # 'limitDmax'         : False,
            # 'dmaxStep'          : '[500]',
            'recenter'          : recenter,
            'recenterStep'      : str(recenter_step),
            'positivity'        : positivity,
            'extrapolate'       : extrapolate,
            'shrinkwrap'        : shrinkwrap,
            'swSigmaStart'      : sw_sigma_start,
            'swSigmaEnd'        : sw_sigma_end,
            'swSigmaDecay'      : sw_sigma_decay,
            'swThresFrac'       : sw_sigma_thresh,
            'swIter'            : sw_iter,
            'swMinStep'         : sw_min_step,
            'connected'         : connected,
            'conSteps'          : str(connectivity_step),
            'chiEndFrac'        : chi_end_frac,
            'cutOutput'         : cut_output,
            'writeXplor'        : write_xplor,
            'mode'              : mode,
            'recenterMode'      : recenter_mode,
            # 'minDensity'        : str(min_density),
            # 'maxDensity'        : str(max_density),
            # 'flattenLowDensity' : flatten_low,
            'ncs'               : symmetry,
            'ncsSteps'          : str(sym_step),
            'ncsType'           : sym_type,
            'ncsAxis'           : sym_axis,
            'seed'              : seed,
            'denssGPU'          : gpu,
            }

    q = ift.q_extrap
    I = ift.i_extrap

    ext_pts = len(I)-len(ift.i_orig)

    if ext_pts > 0:
        sigq =np.empty_like(I)
        sigq[:ext_pts] = I[:ext_pts]*np.mean((ift.err_orig[:10]/ift.i_orig[:10]))
        sigq[ext_pts:] = I[ext_pts:]*(ift.err_orig/ift.i_orig)
    else:
        sigq = I*(ift.err_orig/ift.i_orig)

    D = ift.getParameter('dmax')

    shrinkwrap_sigma_start_in_A = (3.0 * D / 64.0) * 3.0
    shrinkwrap_sigma_end_in_A = (3.0 * D / 64.0) * 1.5

    if denss_settings['mode'] == 'Fast':
        denss_settings['swMinStep'] = 1000
        denss_settings['conSteps'] = '[2000]'
        denss_settings['recenterStep'] = '%s' %(list(range(501,2502,500)))
        denss_settings['steps'] = None
        denss_settings['voxel'] = D*denss_settings['oversample']/32.

    elif denss_settings['mode'] == 'Slow':
        denss_settings['swMinStep'] = 1000
        denss_settings['conSteps'] = '[2000]'
        denss_settings['recenterStep'] = '%s' %(list(range(501,8002,500)))
        denss_settings['steps'] = None
        denss_settings['voxel'] = D*denss_settings['oversample']/64.

    elif denss_settings['mode'] == 'Membrane':
        denss_settings['swMinStep'] = 0
        denss_settings['swThresFrac'] = 0.1
        denss_settings['conSteps'] = '[300, 500, 1000]'
        denss_settings['recenterStep'] = '%s' %(list(range(501,8002,500)))
        denss_settings['steps'] = None
        denss_settings['voxel'] = D*denss_settings['oversample']/64.
        denss_settings['positivity'] = False

        shrinkwrap_sigma_start_in_A *= 2.0
        shrinkwrap_sigma_end_in_A *= 2.0

    if denss_settings['swSigmaStart'] == 'None':
        shrinkwrap_sigma_start_in_vox = shrinkwrap_sigma_start_in_A / denss_settings['voxel']
        denss_settings['swSigmaStart'] = shrinkwrap_sigma_start_in_vox

    if denss_settings['swSigmaEnd'] == 'None':
        shrinkwrap_sigma_end_in_vox = shrinkwrap_sigma_end_in_A / denss_settings['voxel']
        denss_settings['swSigmaEnd'] = shrinkwrap_sigma_end_in_vox

    denss_data = DENSS.runDenss(q, I, sigq, D, prefix, datadir, denss_settings,
        initial_model, gui=False, abort_event=abort_event)

    if len(denss_data) == 0:
        raise Exception('DENSS failed to run properly')

    if not abort_event.is_set():
        (qdata, I_extrap, err_extrap, q_fit, I_fit, chi_sq, rg, support_vol, rho,
            side) = denss_data

        last_index = max(np.where(rg !=0)[0])
        all_rg = rg[:last_index+1]
        all_support_vol = support_vol[:last_index+1]
        #Weird DENSS thing where last index of chi is 1 less than of Rg
        all_chi_sq = chi_sq[:last_index]
    else:
        rho = -1
        all_chi_sq = [-1]
        all_rg = [-1]
        all_support_vol = [-1]
        side = -1
        q_fit = -1
        I_fit = -1
        I_extrap = -1
        err_extrap = -1

    return (rho, all_chi_sq[-1], all_rg[-1], all_support_vol[-1], side, q_fit,
        I_fit, I_extrap, err_extrap, all_chi_sq, all_rg, all_support_vol)

def denss_average(densities, side, prefix, datadir, n_proc=1,
    abort_event=None):
    """
    Averages multiple electron densities to produce a single average density.
    Uses the averaging procedure from the DENSS package. Function blocks until
    the average is complete. There must be at least four densities to average.

    Parameters
    ----------
    densities: :class:`numpy.array`
        A :class:`numpy.array` where the the first axis (e.g. density[0],
        density[1], etc) corresponds to each electron density to be averaged.
    side: float
        The real space box width in Angstroms of the reconstruction.
    prefix: str
        The output prefix for the averaged model.
    datadir: str
        The output directory for the averaged model.
    n_proc: int
        The number of processors to use. This could be up to as many cores
        as your computer has.
    abort_event: :class:`multiprocessing.Manager.Event`, optional
        A :class:`multiprocessing.ManagerEvent` If this event is set it will abort
        the denss average run.

    Returns
    -------
    average_rho: :class:`numpy.array`
        The average electron density. Of the input models, after rejecting the
        outliers.
    mean_cor: float
        The mean correlation score of the models.
    std_cor: float
        The standard deviation of the model correlation scores.
    threshold: float
        The threshold used to reject models from the average.
    res: float
        The estimated model resolution in Angstrom from the Fourier shell
        correlation.
    scores: :class:`numpy.array`
        An array of the correlation scores. Each entry in the array is the
        score for the corresponding entry in the input densities array.
    fsc: :class:`numpy.array`
        The average Fourier shell correlation between each model and a
        average reference model. This is used to estimate the resolution.
    """

    datadir = os.path.abspath(os.path.expanduser(datadir))

    if n_proc == 1:
        single_proc = True
    else:
        single_proc = False

    if isinstance(densities, list):
        densities = np.array(densities)

    allrhos, scores = DENSS.run_enantiomers(densities, n_proc,
        single_proc=single_proc, abort_event=abort_event, gui=False)

    if abort_event is not None and abort_event.is_set():
        return np.array([-1]), -1, -1, -1, -1, np.array([-1]), np.array([-1])

    refrho = DENSS.binary_average(allrhos, n_proc, single_proc=single_proc,
        abort_event=abort_event)

    if abort_event is not None and abort_event.is_set():
        return np.array([-1]), -1, -1, -1, -1, np.array([-1]), np.array([-1])

    aligned, scores = DENSS.align_multiple(refrho, allrhos, n_proc,
        single_proc=single_proc, abort_event=abort_event)

    if abort_event is not None and abort_event.is_set():
        return np.array([-1]), -1, -1, -1, -1, np.array([-1]), np.array([-1])

    #filter rhos with scores below the mean - 2*standard deviation.
    mean_cor = np.mean(scores)
    std_cor = np.std(scores)
    threshold = mean_cor - 2*std_cor

    aligned = aligned[scores>threshold]
    average_rho = np.mean(aligned,axis=0)

    DENSS.write_mrc(average_rho, side, os.path.join(datadir, prefix+'_average.mrc'))

    #rather than compare two halves, average all fsc's to the reference
    fscs = []
    for calc_map in range(len(aligned)):
        fscs.append(DENSS.calc_fsc(aligned[calc_map],refrho,side))
    fscs = np.array(fscs)
    fsc = np.mean(fscs,axis=0)
    x = np.linspace(fsc[0,0],fsc[-1,0],100)
    y = np.interp(x, fsc[:,0], fsc[:,1])
    resi = np.argmin(y>=0.5)
    resx = np.interp(0.5,[y[resi+1],y[resi]],[x[resi+1],x[resi]])
    resn = round(float(1./resx),1)
    np.savetxt(os.path.join(datadir, prefix+'_fsc.dat'),fsc,delimiter=" ",
        fmt="%.5e",header="1/resolution, FSC; Resolution=%.1f A" % resn)

    with open(os.path.join(datadir, '{}_average.log'.format(prefix)), 'w') as f:
        f.write( "Mean of correlation scores: %.3f\n" % mean_cor)
        f.write( "Standard deviation of scores: %.3f\n" % std_cor)
        f.write('Total number of input maps for alignment: %i\n' % allrhos.shape[0])
        f.write('Number of aligned maps accepted: %i\n' % aligned.shape[0])
        f.write(('Correlation score between average and reference: %.3f\n'
            % (1./DENSS.rho_overlap_score(average_rho, refrho))))
        f.write("Resolution: %.1f " % resn + 'Angstrom\n')


    return average_rho, mean_cor, std_cor, threshold, resn, scores, fsc

def denss_align(density, side, ref_file, ref_datadir='.',  prefix='',
    save_datadir='.', save=True, center=True, resolution=15.0, enantiomer=True,
    n_proc=1, abort_event=None):
    """
    Aligns each input electron density against a reference model. The
    reference model can either be a PDB model (.pdb) or electron density (.mrc).
    The aligned model can be saved to disk.

    Parameters
    ----------
    density: :class:`numpy.array`
        A :class:`numpy.array` of the electron density to be aligned to the
        reference model.
    side: float
        The real space box width in Angstroms of the reconstruction.
    ref_file: str
        The name (without path) of the reference model file to align the input
        densities to. Should be either a .pdb or .mrc file.
    ref_datadir: str, optional
        The directory where ref_file is located. Defaults to the current
        directory.
    prefix: str
        The name the aligned model will be saved with (minus extension) if
        save is True.
    save_datadir: str
        The directory to save the aligned model in if save is True.
    save: bool, optional
        Whether or not to save the aligned model to disk.
    center: bool, optional
        Whether the reference file should first be centered on the origin.
        Defaults to True. Only used if the reference file is a .pdb file.
        If used, a _centered.pdb file is written to the same folder as
        the ref_datadir.
    resolution: float, optional
        If a .pdb file is the reference file, this is the resolution used to
        generate an electron density map for comparison with the input
        densities.
    enantiomer: bool, optional
        Check for enantiomers during alignment.
    n_proc: int, optional
        The number of processors to use. This could be up to as many cores
        as your computer has.
    abort_event: :class:`multiprocessing.Manager.Event`, optional
        A :class:`multiprocessing.Manager.Event` If this event is set it will abort
        the denss alignment run.

    Returns
    -------
    aligned_density: :class:`numpy.array`
        The input electron density aligned to the reference model.
    scores: float
        The correlation score of the model to the reference model.
    """

    ref_datadir = os.path.abspath(os.path.expanduser(ref_datadir))
    save_datadir = os.path.abspath(os.path.expanduser(save_datadir))

    ref_name = os.path.join(ref_datadir, ref_file)

    if n_proc == 1:
        single_proc = True
    else:
        single_proc = False

    rho_list = np.array([density])
    side_list = np.array([side])

    aligned_rhos, scores = DENSS.run_align(rho_list, side_list, ref_name,
        center=center, resolution=resolution, enantiomer=enantiomer,
        cores=n_proc, single_proc=single_proc, gui=False,
        abort_event=abort_event)

    if abort_event is not None and abort_event.is_set():
        return np.array([-1]), -1

    aligned_density = aligned_rhos[0]
    score = scores[0]

    outname = '{}.mrc'.format(prefix)

    DENSS.write_mrc(aligned_density, side, os.path.join(save_datadir, outname))

    return aligned_density, score

# Operations on series

def svd(series, profile_type='sub', framei=None, framef=None, norm=True):
    """
    Runs singular value decomposition (SVD) on the input series.

    Parameters
    ----------
    series: list or :class:`bioxtasraw.SECM.SECM`
        The input series to be deconvolved. It should either be a list
        of individual scattering profiles (:class:`bioxtasraw.SASM.SASM`) or
        a single series object (:class:`bioxtasraw.SECM.SECM`).
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
    norm: bool, optional
        Whether error normalized intensity should be used for EFA. Defaults
        to True. Recommended to not change this.

    Returns
    -------
    svd_s: class:`numpy.array`
        The singular values.
    svd_U: class:`numpy.array`
        The left singular vectors
    svd_V: class:`numpy.array`
        The right singular vectors.

    Raises
    ------
    SASExceptions.EFAError
        If SVD cannot be carried out.
    """
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

    return svd_s, svd_U, svd_V

def regals(series, comp_settings, profile_type='sub', framei=None,
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
    (regals_profiles, regals_ifts, concs, reg_concs, mixture, params,
        residual) = SASCalc.run_full_regals(series, comp_settings, profile_type,
        framei, framef, x_vals, min_iter, max_iter, tol, conv_type,
        use_previous_results, previous_results)

    return regals_profiles, regals_ifts, concs, reg_concs, mixture, params, residual

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

    efa_profiles, converged, conv_data, rotation_data = SASCalc.run_full_efa(series,
        ranges, profile_type, framei, framef, method, niter, tol, norm,
        force_positive, previous_results)

    return efa_profiles, converged, conv_data, rotation_data


def find_buffer_range(series, profile_type='unsub', int_type='total', q_val=None,
    q_range=None, window_size=5, settings=None, sim_test='CorMap',
    sim_cor='Bonferroni', sim_thresh=0.01):
    """
    Automatically determine the appropriate buffer range from subtraction from
    the input series. This is designed to work with SEC-SAXS data, but may work
    in other circumstances.

    Parameters
    ----------
    series: list or :class:`bioxtasraw.SECM.SECM`
        The input series to find the buffer range for. It should either be a list
        of individual scattering profiles (:class:`bioxtasraw.SASM.SASM`) or
        a single series object (:class:`bioxtasraw.SECM.SECM`).
    profile_type: {'unsub', 'sub', 'baseline'} str, optional
        Only used if a :class:`bioxtasraw.SECM.SECM` is provided for the series
        argument. Determines which type of profile to use from the series to
        find the buffer range. Unsubtracted profiles - 'unsub', subtracted
        profiles - 'sub', baseline corrected profiles - 'baseline'.
    int_type: {'total', 'mean', 'q_val', 'q_range'} str, optional
        The intensity type to use for the automated determination of buffer
        range. Total integrated intensity - 'total', mean intensity - 'mean',
        intensity at a particular q value - 'q_val', intensity in a given
        q range - 'q_range'. Use of q_val or q_range requires the corresponding
        parameter to be provided.
    q_val: float, optional
        If int_type is 'q_val', the q value used for the intensity is set by
        this parameter.
    q_range: list, optional
        This should have two entries, both floats. The first is the minimum q
        value of the range, the second the maximum q value of the range. If
        int_type is 'q_range', the q range used for the intensity is set by
        this parameter.
    window_size: int, optional
        The size of the average window used for calculating parameters from
        series data. Used to help set the size of the search window for the
        buffer region. Defaults to 5.
    settings: :class:`bioxtasraw.RAWSettings.RAWSettings`, optional
        RAW settings containing relevant parameters. If provided, sim_test,
        sim_cor, and sim_threshold are overridden by the values in the
        settings.
    sim_test: {'CorMap'} str, optional
        Sets the type of similarity test to be used. Currently only CorMap is
        supported as an option. Is overridden if settings are provided.
    sim_cor: {'Bonferroni', 'None'} str, optional
        Sets the multiple testing correction to be used as part of the similarity
        test. Default is Bonferroni. Is overridden if settings are provided.
    sim_thresh: float, optional
        Sets the p value threshold for the similarity test. A higher value is
        a more strict test (range from 0-1). Is overridden if settings are
        provided.

    Returns
    -------
    success: bool
        If a buffer range was successfully found.
    region_start: int
        The starting index of the buffer region found.
    region_end: int
        The ending index of the buffer region found.
    """
    if settings is not None:
        sim_thresh = settings.get('similarityThreshold')
        sim_test = settings.get('similarityTest')
        sim_cor = settings.get('similarityCorrection')

    if isinstance(series, SECM.SECM):
        if profile_type == 'unsub':
            buffer_sasms = series._sasm_list
        elif profile_type == 'sub':
            buffer_sasms = series.subtracted_sasm_list
        elif profile_type == 'baseline':
            buffer_sasms = series.baseline_subtracted_sasm_list
    else:
        buffer_sasms = series

    if int_type == 'total':
        intensity = np.array([sasm.getTotalI() for sasm in buffer_sasms])
    elif int_type == 'mean':
        intensity = np.array([sasm.getMeanI() for sasm in buffer_sasms])
    elif int_type == 'q_val':
        intensity = np.array([sasm.getIofQ(q_val) for sasm in buffer_sasms])
    elif int_type == 'q_range':
        q1 = q_range[0]
        q2 = q_range[1]
        intensity = np.array([sasm.getIofQRange(q1, q2) for sasm in buffer_sasms])

    success, region_start, region_end = SASCalc.findBufferRange(buffer_sasms,
        intensity, window_size, sim_test, sim_cor, sim_thresh)

    return success, region_start, region_end

def validate_buffer_range(series, buf_range, profile_type='unsub',
    int_type='total', q_val=None, q_range=None, fast=False, settings=None,
    sim_test='CorMap', sim_cor='Bonferroni', sim_thresh=0.01):
    """
    Validates whether the input data range is a trustworthy buffer range or not.
    This is designed to work with SEC-SAXS data, but may work in other
    circumstances.

    Parameters
    ----------
    series: list or :class:`bioxtasraw.SECM.SECM`
        The input series to validate the buffer range for. It should either be
        a list of individual scattering profiles (:class:`bioxtasraw.SASM.SASM`)
        or a single series object (:class:`bioxtasraw.SECM.SECM`).
    buf_range: list
        A list defining the input buffer range to be validated. The list is made
        up of a set of sub-ranges, each defined by an entry in the list. Each
        sub-range item should be a list or tuple where the first entry is the
        starting index of the range and the second entry is the ending index
        of the range. So a list like ``[[0, 10], [100, 110]]`` would define
        a buffer range consisting of two sub-ranges, the first from profiles 0-10
        in the series and the second from profiles 100-110 in the series.
    profile_type: {'unsub', 'sub', 'baseline'} str, optional
        Only used if a :class:`bioxtasraw.SECM.SECM` is provided for the series
        argument. Determines which type of profile to use from the series to
        validate the buffer range. Unsubtracted profiles - 'unsub', subtracted
        profiles - 'sub', baseline corrected profiles - 'baseline'.
    int_type: {'total', 'mean', 'q_val', 'q_range'} str, optional
        The intensity type to use for the validation of the buffer range. Total
        integrated intensity - 'total', mean intensity - 'mean', intensity at
        a particular q value - 'q_val', intensity in a given q range -
        'q_range'. Use of q_val or q_range requires the corresponding parameter
        to be provided.
    q_val: float, optional
        If int_type is 'q_val', the q value used for the intensity is set by
        this parameter.
    q_range: list, optional
        This should have two entries, both floats. The first is the minimum q
        value of the range, the second the maximum q value of the range. If
        int_type is 'q_range', the q range used for the intensity is set by
        this parameter.
    fast: bool, optional
        Whether the test should be done in fast mode or not. A fast test stops
        at the first failed check. In a normal test (not fast), all metrics
        are checked. Using a fast test is best when trying to automatically
        determine a buffer range, something which can take many separate
        validation checks. A normal test is best when trying to determine what,
        if anything, about your selected region might be problematic.
    settings: :class:`bioxtasraw.RAWSettings.RAWSettings`, optional
        RAW settings containing relevant parameters. If provided, sim_test,
        sim_cor, and sim_threshold are overridden by the values in the
        settings.
    sim_test: {'CorMap'} str, optional
        Sets the type of similarity test to be used. Currently only CorMap is
        supported as an option. Is overridden if settings are provided.
    sim_cor: {'Bonferroni', 'None'} str, optional
        Sets the multiple testing correction to be used as part of the similarity
        test. Default is Bonferroni. Is overridden if settings are provided.
    sim_thresh: float, optional
        Sets the p value threshold for the similarity test. A higher value is
        a more strict test (range from 0-1). Is overridden if settings are
        provided.

    Returns
    -------
    valid: bool
        If the input buffer range is a valid buffer range.
    similarity_results: dict
        A dictionary with the results of the similarity test. In particular,
        keys are: 'all_similar' - whether all profiles in the selected range
        are similar over the entire profile. 'low_q_similar' - whether all
        profiles in the selected range are similar over the low q region
        of the profile. 'high_q_similar' - whether all profiles in the
        selected range are similar over the high q region. 'max_idx' -
        The index of the profile used as the reference for the similarity test,
        corresponding to the profile with the highest intensity in the region.
        'all_outliers' - Indices of the outlier profiles of the similarity
        test at all q. 'low_q_outliers' - Indices of the outlier profiles of
        the similarity test at low q. 'high_q_outliers' - Indices of the
        outlier profiles of the similarity test at high q.
    svd_results: dict
        A dictionary with the results of the SVD test. In particular, keys are:
        'svals' - the number of significant singular vectors in the region. 'U'
        - the left singular vectors. 'V' - the right singular vectors.
        'u_autocor' - The autocorrelation of the left singular vectors.
        'v_autocor' - The autocorrelation of the right singular vectors.
    intI_results: dict
        A dictionary with the results of the intensity test. In particular, keys
        are: 'intI_r' - the Spearman correlation coefficient of the intensity
        in the region. 'inti_pval' - the p-value from the Spearman correlation
        test on the intensity of the region. 'intI_valid' - Whether the
        range is a valid buffer range based on the intensity correlation.
        The same keys are provided but with smoothed in front, indicating
        the test results on the smoothed intensity.
    """
    if settings is not None:
        sim_thresh = settings.get('similarityThreshold')
        sim_test = settings.get('similarityTest')
        sim_cor = settings.get('similarityCorrection')

    frame_idx = []
    for item in buf_range:
        frame_idx = frame_idx + list(range(item[0], item[1]+1))

    frame_idx = sorted(set(frame_idx))
    frame_idx = np.array(frame_idx)

    if isinstance(series, SECM.SECM):
        buffer_sasms = [series.getSASM(idx, profile_type) for idx in frame_idx]
    else:
        buffer_sasms = [series[idx] for idx in frame_idx]

    if int_type == 'total':
        intensity = np.array([sasm.getTotalI() for sasm in buffer_sasms])
    elif int_type == 'mean':
        intensity = np.array([sasm.getMeanI() for sasm in buffer_sasms])
    elif int_type == 'q_val':
        intensity = np.array([sasm.getIofQ(q_val) for sasm in buffer_sasms])
    elif int_type == 'q_range':
        q1 = q_range[0]
        q2 = q_range[1]
        intensity = np.array([sasm.getIofQRange(q1, q2) for sasm in buffer_sasms])

    (valid, similarity_results, svd_results,
        intI_results) = SASCalc.validateBuffer(buffer_sasms, frame_idx,
        intensity, sim_test, sim_cor, sim_thresh, fast)

    return valid, similarity_results, svd_results, intI_results

def set_buffer_range(series, buffer_range, int_type='total', q_val=None,
    q_range=None, already_subtracted=False, window_size=5, settings=None,
    calc_thresh=1.02, sim_test='CorMap', sim_cor='Bonferroni', sim_thresh=0.01,
    error_weight=True, vp_density=0.83*10**(-3), vp_cutoff='Default',
    vp_qmax=0.5, vc_protein=True, vc_cutoff='Manual', vc_qmax=0.3,
    vc_a_prot=1.0, vc_b_prot=0.1231, vc_a_rna=0.808, vc_b_rna=0.00934):
    """
    Sets the buffer range for a series, carries out the subtraction, and
    calculates Rg and MW vs. frame number.

    Parameters
    ----------
    series: :class:`bioxtasraw.SECM.SECM`
        The input series to set the buffer range for.
    buffer_range: list
        A list defining the input buffer range to be set. The list is made
        up of a set of sub-ranges, each defined by an entry in the list. Each
        sub-range item should be a list or tuple where the first entry is the
        starting index of the range and the second entry is the ending index
        of the range. So a list like ``[[0, 10], [100, 110]]`` would define
        a buffer range consisting of two sub-ranges, the first from profiles 0-10
        in the series and the second from profiles 100-110 in the series.
    int_type: {'total', 'mean', 'q_val', 'q_range'} str, optional
        The intensity type to use when setting the buffer range. Total
        integrated intensity - 'total', mean intensity - 'mean', intensity at
        a particular q value - 'q_val', intensity in a given q range -
        'q_range'. Use of q_val or q_range requires the corresponding parameter
        to be provided.
    q_val: float, optional
        If int_type is 'q_val', the q value used for the intensity is set by
        this parameter.
    q_range: list, optional
        This should have two entries, both floats. The first is the minimum q
        value of the range, the second the maximum q value of the range. If
        int_type is 'q_range', the q range used for the intensity is set by
        this parameter.
    already_subtracted: bool, optional
        Whether the series is already subtracted. If True, any buffer_range
        input is ignored and the series unsubtracted profiles are set as the
        subtracted profiles. Defaults to False
    window_size: int, optional
        The size of the average window used when calculating Rg and MW.
        So if the window is 5, 5 a window is size 5 is slid along the series,
        and profiles in that window are averaged before being used to calculate
        Rg and MW. For example, frames 1-5, 2-6, 3-7, etc would be averaged and
        then have Rg and MW calculated from that average.
    settings: :class:`bioxtasraw.RAWSettings.RAWSettings`, optional
        RAW settings containing relevant parameters. If provided, calc_thresh,
        sim_test, sim_cor, sim_thresh, err_weight, vp_density, vp_cutoff,
        vp_qmax, vc_protein, vc_cutoff, and vc_qmax are overridden by the
        values in the settings.
    calc_thresh: float, optional
        If the ratio of the scattering profile intensity to the average buffer
        intensity is greater than this threshold, the Rg and MW for the profile
        is calculated. Defaults to 1.02.
    sim_test: {'CorMap'} str, optional
        Sets the type of similarity test to be used. Currently only CorMap is
        supported as an option. Is overridden if settings are provided.
    sim_cor: {'Bonferroni', 'None'} str, optional
        Sets the multiple testing correction to be used as part of the similarity
        test. Default is Bonferroni. Is overridden if settings are provided.
    sim_thresh: float, optional
        Sets the p value threshold for the similarity test. A higher value is
        a more strict test (range from 0-1). Is overridden if settings are
        provided.
    error_weight: bool, optional
        Whether to use error weighting when calculating the Rg.
    vp_density: float, optional
        The density used for the Porod volume M.W. calculation in kDa/A^3.
        Defaults to 0.83*10**(-3).
    vp_cutoff: {''Default', '8/Rg', 'log(I0/I(q))', 'Manual''} str, optional
        The method to use to calculate the maximum q value used for the
        Porod volume M.W. calculation. Defaults to 'Default'
    vp_qmax: float, optional
        The maximum q value to be used if the 'Manual' cutoff method is
        selected for the Porod volume M.W. calculation. Defaults to 0.5.
    vc_protein: bool
        True if the sample is protein, False if the sample is RNA. Determines
        which set of coefficients to use for calculating M.W.
    vc_cutoff: {''Default', '8/Rg', 'log(I0/I(q))', 'Manual''} str, optional
        The method to use to calculate the maximum q value used for the
        M.W. calculation. Defaults to 'Manual'
    vc_qmax: float, optional
        The maximum q value to be used if the 'Manual' cutoff method is
        selected. Defaults to 0.3.
    vc_a_prot: float
        The volume of correlation A coefficient for protein. Not recommended
        to be changed.
    vc_b_prot: float
        The volume of correlation B coefficient for protein. Not recommended
        to be changed. Note that here B is defined as 1/B from the original paper.
    vc_a_rna: float
        The volume of correlation A coefficient for RNA. Not recommended to
        be changed.
    vc_b_rna: float
        The volume of correlation B coefficient for RNA. Not recommended to
        be changed. Note that here B is defined as 1/B from the original paper.

    Returns
    -------
    sub_profiles: list
        A list of :class:`SASM.SASM` subtracted profiles. Each profile is created
        by creating an average buffer from the range defined by buffer_range
        and subtracting that from every unsubtracted profile in the series.
    rg: :class:`numpy.array`
        An array of the Rg values calculated for each subtracted profile. If
        no Rg value could be calculated then the value is -1. Each array index
        is the Rg corresponding to the subtracted profile at that index in
        the sub_profiles list.
    rger: :class:`numpy.array`
        An array of the uncertainty in the Rg values calculated for each
        subtracted profile. If no Rg value could be calculated then the
        value is -1. Each array index is the uncertainty corresponding to the
        subtracted profile at that index in  the sub_profiles list.
    i0: :class:`numpy.array`
        An array of the I(0) values calculated for each subtracted profile. If
        no I(0) value could be calculated then the value is -1. Each array index
        is the I(0) corresponding to the subtracted profile at that index in
        the sub_profiles list.
    i0er: :class:`numpy.array`
        An array of the uncertainty in the I(0) values calculated for each
        subtracted profile. If no I(0) value could be calculated then the
        value is -1. Each array index is the uncertainty corresponding to the
        subtracted profile at that index in  the sub_profiles list.
    vcmw: :class:`numpy.array`
        An array of the volume of correlation M.W. values calculated for each
        subtracted profile. If no M.W. value could be calculated then the value
        is -1. Each array index is the M.W. corresponding to the subtracted
        profile at that index in the sub_profiles list.
    vcmwer: :class:`numpy.array`
        An array of the uncertainty in the volume of correlation M.W. values
        calculated for each subtracted profile. If no M.W. value could be
        calculated then the value is -1. Each array index is the uncertainty
        corresponding to the subtracted profile at that index in  the
        sub_profiles list.
    vpmw: :class:`numpy.array`
        An array of the Porod volume M.W. values calculated for each subtracted
        profile. If no M.W. value could be calculated then the value is -1.
        Each array index is the M.W. corresponding to the subtracted profile
        at that index in the sub_profiles list.
    """

    if settings is not None:
        calc_thresh = settings.get('secCalcThreshold')
        sim_thresh = settings.get('similarityThreshold')
        sim_test = settings.get('similarityTest')
        sim_cor = settings.get('similarityCorrection')

        error_weight = settings.get('errorWeight')

        vp_cutoff = settings.get('MWVpCutoff')
        vp_density = settings.get('MWVpRho')
        vp_qmax = settings.get('MWVpQmax')

        vc_cutoff = settings.get('MWVcCutoff')
        vc_type = settings.get('MWVcType')
        vc_qmax = settings.get('MWVcQmax')

        if vc_type == 'Protein':
            vc_protein = True
        else:
            vc_protein = False

    if not already_subtracted:
        avg_sasm, success, err = series.averageFrames(buffer_range, 'unsub',
            sim_test, sim_thresh, sim_cor, True)

        sub_profiles, use_sub_profiles = series.subtractAllSASMs(avg_sasm, int_type,
            calc_thresh, q_val, q_range)
    else:
        avg_sasm = None
        sub_profiles = series.getAllSASMs()
        use_sub_profiles = [True for i in range(len(sub_profiles))]
        buffer_range = []

    success, results = SASCalc.run_secm_calcs(sub_profiles, use_sub_profiles,
        window_size, vc_protein, error_weight, vp_density, vp_cutoff,
        vp_qmax, vc_cutoff, vc_qmax, vc_a_prot, vc_b_prot, vc_a_rna,
        vc_b_rna)

    if vc_protein:
        mol_type = 'Protein'
    else:
        mol_type = 'RNA'

    if success:
        rg = results['rg']
        rger = results['rger']
        i0 = results['i0']
        i0er = results['i0er']
        vcmw = results['vcmw']
        vcmwer = results['vcmwer']
        vpmw = results['vpmw']
    else:
        rg = np.zeros(len(sub_profiles),dtype=float)-1
        rger = np.zeros(len(sub_profiles),dtype=float)-1
        i0 = np.zeros(len(sub_profiles),dtype=float)-1
        i0er = np.zeros(len(sub_profiles),dtype=float)-1
        vcmw = np.zeros(len(sub_profiles),dtype=float)-1
        vcmwer = np.zeros(len(sub_profiles),dtype=float)-1
        vpmw = np.zeros(len(sub_profiles),dtype=float)-1

    series.buffer_range = buffer_range
    series.already_subtracted = already_subtracted
    series.average_buffer_sasm = avg_sasm
    series.setSubtractedSASMs(sub_profiles, use_sub_profiles)

    series.window_size = window_size
    series.mol_type = mol_type
    series.mol_density = vp_density

    if rg.size > 0 and success:
        series.setCalcValues(rg, rger, i0, i0er, vcmw, vcmwer, vpmw)
        series.calc_has_data = True

    return sub_profiles, rg, rger, i0, i0er, vcmw, vcmwer, vpmw

def series_calc(sub_profiles, window_size=5, settings=None, error_weight=True,
    vp_density=0.83*10**(-3), vp_cutoff='Default', vp_qmax=0.5,
    vc_protein=True, vc_cutoff='Manual', vc_qmax=0.3, vc_a_prot=1.0,
    vc_b_prot=0.1231, vc_a_rna=0.808, vc_b_rna=0.00934):
    """
    Calculates Rg and MW for the input subtracted profiles. If you are working
    with a :class:`SECM.SECM` series object then use :func:`set_buffer_range`
    instead of this function.

    Parameters
    ----------
    sub_profiles: list
        A list of subtracted profiles (:class:`SASM.SASM`) to calculate the
        Rg and M.W. values for using the series calculation function.
    window_size: int, optional
        The size of the average window used when calculating Rg and MW.
        So if the window is 5, 5 a window is size 5 is slid along the series,
        and profiles in that window are averaged before being used to calculate
        Rg and MW. For example, frames 1-5, 2-6, 3-7, etc would be averaged and
        then have Rg and MW calculated from that average.
    settings: :class:`bioxtasraw.RAWSettings.RAWSettings`, optional
        RAW settings containing relevant parameters. If provided, err_weight,
        vp_density, vp_cutoff, vp_qmax, vc_protein, vc_cutoff, and vc_qmax are
        overridden by the values in the settings.
    error_weight: bool, optional
        Whether to use error weighting when calculating the Rg.
    vp_density: float, optional
        The density used for the Porod volume M.W. calculation in kDa/A^3.
        Defaults to 0.83*10**(-3).
    vp_cutoff: {''Default', '8/Rg', 'log(I0/I(q))', 'Manual''} str, optional
        The method to use to calculate the maximum q value used for the
        Porod volume M.W. calculation. Defaults to 'Default'
    vp_qmax: float, optional
        The maximum q value to be used if the 'Manual' cutoff method is
        selected for the Porod volume M.W. calculation. Defaults to 0.5.
    vc_protein: bool
        True if the sample is protein, False if the sample is RNA. Determines
        which set of coefficients to use for calculating M.W.
    vc_cutoff: {''Default', '8/Rg', 'log(I0/I(q))', 'Manual''} str, optional
        The method to use to calculate the maximum q value used for the
        M.W. calculation. Defaults to 'Manual'
    vc_qmax: float, optional
        The maximum q value to be used if the 'Manual' cutoff method is
        selected. Defaults to 0.3.
    vc_a_prot: float
        The volume of correlation A coefficient for protein. Not recommended
        to be changed.
    vc_b_prot: float
        The volume of correlation B coefficient for protein. Not recommended
        to be changed. Note that here B is defined as 1/B from the original paper.
    vc_a_rna: float
        The volume of correlation A coefficient for RNA. Not recommended to
        be changed.
    vc_b_rna: float
        The volume of correlation B coefficient for RNA. Not recommended to
        be changed. Note that here B is defined as 1/B from the original paper.

    Returns
    -------
    rg: :class:`numpy.array`
        An array of the Rg values calculated for each subtracted profile. If
        no Rg value could be calculated then the value is -1. Each array index
        is the Rg corresponding to the subtracted profile at that index in
        the sub_profiles list.
    rger: :class:`numpy.array`
        An array of the uncertainty in the Rg values calculated for each
        subtracted profile. If no Rg value could be calculated then the
        value is -1. Each array index is the uncertainty corresponding to the
        subtracted profile at that index in  the sub_profiles list.
    i0: :class:`numpy.array`
        An array of the I(0) values calculated for each subtracted profile. If
        no I(0) value could be calculated then the value is -1. Each array index
        is the I(0) corresponding to the subtracted profile at that index in
        the sub_profiles list.
    i0er: :class:`numpy.array`
        An array of the uncertainty in the I(0) values calculated for each
        subtracted profile. If no I(0) value could be calculated then the
        value is -1. Each array index is the uncertainty corresponding to the
        subtracted profile at that index in  the sub_profiles list.
    vcmw: :class:`numpy.array`
        An array of the volume of correlation M.W. values calculated for each
        subtracted profile. If no M.W. value could be calculated then the value
        is -1. Each array index is the M.W. corresponding to the subtracted
        profile at that index in the sub_profiles list.
    vcmwer: :class:`numpy.array`
        An array of the uncertainty in the volume of correlation M.W. values
        calculated for each subtracted profile. If no M.W. value could be
        calculated then the value is -1. Each array index is the uncertainty
        corresponding to the subtracted profile at that index in  the
        sub_profiles list.
    vpmw: :class:`numpy.array`
        An array of the Porod volume M.W. values calculated for each subtracted
        profile. If no M.W. value could be calculated then the value is -1.
        Each array index is the M.W. corresponding to the subtracted profile
        at that index in the sub_profiles list.
    """
    if settings is not None:
        error_weight = settings.get('errorWeight')

        vp_cutoff = settings.get('MWVpCutoff')
        vp_density = settings.get('MWVpRho')
        vp_qmax = settings.get('MWVpQmax')

        vc_cutoff = settings.get('MWVcCutoff')
        vc_type = settings.get('MWVcType')
        vc_qmax = settings.get('MWVcQmax')

        if vc_type == 'Protein':
            vc_protein = True
        else:
            vc_protein = False

    use_sub_profiles = [True for profile in sub_profiles]

    success, results = SASCalc.run_secm_calcs(sub_profiles, use_sub_profiles,
        window_size, vc_protein, error_weight, vp_density, vp_cutoff,
        vp_qmax, vc_cutoff, vc_qmax, vc_a_prot, vc_b_prot, vc_a_rna,
        vc_b_rna)

    if success:
        rg = results['rg']
        rger = results['rger']
        i0 = results['i0']
        i0er = results['i0er']
        vcmw = results['vcmw']
        vcmwer = results['vcmwer']
        vpmw = results['vpmw']
    else:
        rg = np.zeros(len(sub_profiles),dtype=float)-1
        rger = np.zeros(len(sub_profiles),dtype=float)-1
        i0 = np.zeros(len(sub_profiles),dtype=float)-1
        i0er = np.zeros(len(sub_profiles),dtype=float)-1
        vcmw = np.zeros(len(sub_profiles),dtype=float)-1
        vcmwer = np.zeros(len(sub_profiles),dtype=float)-1
        vpmw = np.zeros(len(sub_profiles),dtype=float)-1

    return rg, rger, i0, i0er, vcmw, vcmwer, vpmw

def find_sample_range(series, profile_type='sub', window_size=5,
    int_type='total', q_val=None, q_range=None, rg=None, vcmw=None, vpmw=None,
    settings=None, sim_test='CorMap', sim_cor='Bonferroni', sim_thresh=0.01):
    """
    Automatically determine the appropriate sample range to average from
    the input series. This is designed to work with SEC-SAXS data, but may
    work in other circumstances.

    Parameters
    ----------
    series: list or :class:`bioxtasraw.SECM.SECM`
        The input series to find the sample range for. It should either be
        a list of individual scattering profiles (:class:`bioxtasraw.SASM.SASM`)
        or a single series object (:class:`bioxtasraw.SECM.SECM`).
    profile_type: {'unsub', 'sub', 'baseline'} str, optional
        Only used if a :class:`bioxtasraw.SECM.SECM` is provided for the series
        argument. Determines which type of profile to use from the series to
        find the sample range. Unsubtracted profiles - 'unsub', subtracted
        profiles - 'sub', baseline corrected profiles - 'baseline'.
    window_size: int
        The size of the average window used when calculating Rg and MW.
    int_type: {'total', 'mean', 'q_val', 'q_range'} str, optional
        The intensity type to used when finding the sample range. Total
        integrated intensity - 'total', mean intensity - 'mean', intensity at
        a particular q value - 'q_val', intensity in a given q range -
        'q_range'. Use of q_val or q_range requires the corresponding parameter
        to be provided.
    q_val: float, optional
        If int_type is 'q_val', the q value used for the intensity is set by
        this parameter.
    q_range: list, optional
        This should have two entries, both floats. The first is the minimum q
        value of the range, the second the maximum q value of the range. If
        int_type is 'q_range', the q range used for the intensity is set by
        this parameter.
    rg: list
        A list of the Rg values corresponding to the input series data. Only
        required if inputing a list of profiles rather than a series object.
    vcmw: list
        A list of the volume of correlation M.W. values corresponding to the
        input series data. Only required if inputing a list of profiles rather
        than a series object.
    vpmw: list
        A list of the Porod volume M.W. values corresponding to the  input
        series data. Only required if inputing a list of profiles rather  than
        a series object.
    settings: :class:`bioxtasraw.RAWSettings.RAWSettings`, optional
        RAW settings containing relevant parameters. If provided, sim_test,
        sim_cor, and sim_threshold are overridden by the values in the
        settings.
    sim_test: {'CorMap'} str, optional
        Sets the type of similarity test to be used. Currently only CorMap is
        supported as an option. Is overridden if settings are provided.
    sim_cor: {'Bonferroni', 'None'} str, optional
        Sets the multiple testing correction to be used as part of the similarity
        test. Default is Bonferroni. Is overridden if settings are provided.
    sim_thresh: float, optional
        Sets the p value threshold for the similarity test. A higher value is
        a more strict test (range from 0-1). Is overridden if settings are
        provided.

    Returns
    -------
    success: bool
        If a buffer range was successfully found.
    region_start: int
        The starting index of the sample region found.
    region_end: int
        The ending index of the sample region found.
    """
    if settings is not None:
        sim_thresh = settings.get('similarityThreshold')
        sim_test = settings.get('similarityTest')
        sim_cor = settings.get('similarityCorrection')

    if isinstance(series, SECM.SECM):
        if profile_type == 'unsub':
            sub_profiles = series._sasm_list
        elif profile_type == 'sub':
            sub_profiles = series.subtracted_sasm_list
        elif profile_type == 'baseline':
            sub_profiles = series.baseline_subtracted_sasm_list

        rg, _ = series.getRg()
        vcmw, _ = series.getVcMW()
        vpmw, _ = series.getVpMW()
    else:
        sub_profiles = series

    if int_type == 'total':
        intensity = np.array([sasm.getTotalI() for sasm in sub_profiles])
    elif int_type == 'mean':
        intensity = np.array([sasm.getMeanI() for sasm in sub_profiles])
    elif int_type == 'q_val':
        intensity = np.array([sasm.getIofQ(q_val) for sasm in sub_profiles])
    elif int_type == 'q_range':
        q1 = q_range[0]
        q2 = q_range[1]
        intensity = np.array([sasm.getIofQRange(q1, q2) for sasm in sub_profiles])

    success, region_start, region_end = SASCalc.findSampleRange(sub_profiles,
        intensity, rg, vcmw, vpmw, window_size, sim_test, sim_cor,
        sim_thresh)

    return success, region_start, region_end

def validate_sample_range(series, sample_range, profile_type='sub',
    int_type='total', q_val=None, q_range=None, rg=None, vcmw=None, vpmw=None,
    fast=False, settings=None, sim_test='CorMap', sim_cor='Bonferroni',
    sim_thresh=0.01):
    """
    Validates whether the input data range is a trustworthy sample range or not.
    This is designed to work with SEC-SAXS data, but may work in other
    circumstances.

    Parameters
    ----------
    series: list or :class:`bioxtasraw.SECM.SECM`
        The input series to validate the sample range for. It should either be
        a list of individual scattering profiles (:class:`bioxtasraw.SASM.SASM`)
        or a single series object (:class:`bioxtasraw.SECM.SECM`).
    sample_range: list
        A list defining the input sample range to be validated. The list is made
        up of a set of sub-ranges, each defined by an entry in the list. Each
        sub-range item should be a list or tuple where the first entry is the
        starting index of the range and the second entry is the ending index
        of the range. So a list like ``[[0, 10], [100, 110]]`` would define
        a sample range consisting of two sub-ranges, the first from profiles 0-10
        in the series and the second from profiles 100-110 in the series.
    profile_type: {'unsub', 'sub', 'baseline'} str, optional
        Only used if a :class:`bioxtasraw.SECM.SECM` is provided for the series
        argument. Determines which type of profile to use from the series to
        validate the sample range. Unsubtracted profiles - 'unsub', subtracted
        profiles - 'sub', baseline corrected profiles - 'baseline'.
    int_type: {'total', 'mean', 'q_val', 'q_range'} str, optional
        The intensity type to use for the validation of the sample range. Total
        integrated intensity - 'total', mean intensity - 'mean', intensity at
        a particular q value - 'q_val', intensity in a given q range -
        'q_range'. Use of q_val or q_range requires the corresponding parameter
        to be provided.
    q_val: float, optional
        If int_type is 'q_val', the q value used for the intensity is set by
        this parameter.
    q_range: list, optional
        This should have two entries, both floats. The first is the minimum q
        value of the range, the second the maximum q value of the range. If
        int_type is 'q_range', the q range used for the intensity is set by
        this parameter.
    rg: list
        A list of the Rg values corresponding to the input series data. Only
        required if inputing a list of profiles rather than a series object.
    vcmw: list
        A list of the volume of correlation M.W. values corresponding to the
        input series data. Only required if inputing a list of profiles rather
        than a series object.
    vpmw: list
        A list of the Porod volume M.W. values corresponding to the  input
        series data. Only required if inputing a list of profiles rather  than
        a series object.
    fast: bool, optional
        Whether the test should be done in fast mode or not. A fast test stops
        at the first failed check. In a normal test (not fast), all metrics
        are checked. Using a fast test is best when trying to automatically
        determine a sample range, something which can take many separate
        validation checks. A normal test is best when trying to determine what,
        if anything, about your selected region might be problematic.
    settings: :class:`bioxtasraw.RAWSettings.RAWSettings`, optional
        RAW settings containing relevant parameters. If provided, sim_test,
        sim_cor, and sim_threshold are overridden by the values in the
        settings.
    sim_test: {'CorMap'} str, optional
        Sets the type of similarity test to be used. Currently only CorMap is
        supported as an option. Is overridden if settings are provided.
    sim_cor: {'Bonferroni', 'None'} str, optional
        Sets the multiple testing correction to be used as part of the similarity
        test. Default is Bonferroni. Is overridden if settings are provided.
    sim_thresh: float, optional
        Sets the p value threshold for the similarity test. A higher value is
        a more strict test (range from 0-1). Is overridden if settings are
        provided.

    Returns
    -------
    valid: bool
        If the input sample range is a valid sample range.
    similarity_results: dict
        A dictionary with the results of the similarity test. In particular,
        keys are: 'all_similar' - whether all profiles in the selected range
        are similar over the entire profile. 'low_q_similar' - whether all
        profiles in the selected range are similar over the low q region
        of the profile. 'high_q_similar' - whether all profiles in the
        selected range are similar over the high q region. 'max_idx' -
        The index of the profile used as the reference for the similarity test,
        corresponding to the profile with the highest intensity in the region.
        'all_outliers' - Indices of the outlier profiles of the similarity
        test at all q. 'low_q_outliers' - Indices of the outlier profiles of
        the similarity test at low q. 'high_q_outliers' - Indices of the
        outlier profiles of the similarity test at high q.
    param_results: dict
        A dictionary with the results of the Rg and M.W. tests. In particular,
        keys are: 'rg_r' - the Spearman correlation coefficient of the Rg
        values in the region. 'rg_pval' - the p-value from the Spearman
        correlation test on the Rg values in the region. 'rg_valid' - Whether
        the range is a valid sample range based on the Rg correlation. The
        same keys are provided for vcmw and vpmw. Additional keys are
        'param_range_valid' - Whether Rg is not calculated anywhere in the
        defined range. 'param_bad_frames' - The frames at which the Rg is
        undefined, if any. 'param_valid' - Whether all evaluation metrics (
        rg_valid, vcmw_valid, vpmw_valid, param_range_valid) are True.
    svd_results: dict
        A dictionary with the results of the SVD test. In particular, keys are:
        'svals' - the number of significant singular vectors in the region. 'U'
        - the left singular vectors. 'V' - the right singular vectors.
        'u_autocor' - The autocorrelation of the left singular vectors.
        'v_autocor' - The autocorrelation of the right singular vectors.
    sn_results: dict:
        A dictionary with the results of the signal to noise test. In particular,
        keys are 'low_sn' - an array of the indices of profiles that, when
        averaged, lower the signal to noise of the resulting averaged profile.
        'sn_valid' - Whether all profiles averaged improve signal to noise.
    """
    if settings is not None:
        sim_thresh = settings.get('similarityThreshold')
        sim_test = settings.get('similarityTest')
        sim_cor = settings.get('similarityCorrection')

    frame_idx = []
    for item in sample_range:
        frame_idx = frame_idx + list(range(item[0], item[1]+1))

    frame_idx = sorted(set(frame_idx))
    frame_idx = np.array(frame_idx)

    if isinstance(series, SECM.SECM):
        rg, _ = series.getRg()
        vcmw, _ = series.getVcMW()
        vpmw, _ = series.getVpMW()

        sub_profiles = [series.getSASM(idx, profile_type) for idx in frame_idx]
        rg = [rg[idx] for idx in frame_idx]
        vcmw = [vcmw[idx] for idx in frame_idx]
        vpmw = [vpmw[idx] for idx in frame_idx]
    else:
        sub_profiles = [series[idx] for idx in frame_idx]
        rg = [rg[idx] for idx in frame_idx]
        vcmw = [vcmw[idx] for idx in frame_idx]
        vpmw = [vpmw[idx] for idx in frame_idx]

    if int_type == 'total':
        intensity = np.array([sasm.getTotalI() for sasm in sub_profiles])
    elif int_type == 'mean':
        intensity = np.array([sasm.getMeanI() for sasm in sub_profiles])
    elif int_type == 'q_val':
        intensity = np.array([sasm.getIofQ(q_val) for sasm in sub_profiles])
    elif int_type == 'q_range':
        q1 = q_range[0]
        q2 = q_range[1]
        intensity = np.array([sasm.getIofQRange(q1, q2) for sasm in sub_profiles])

    (valid, similarity_results, param_results, svd_results,
        sn_results) = SASCalc.validateSample(sub_profiles, frame_idx,
        intensity, rg, vcmw, vpmw, sim_test, sim_cor, sim_thresh, fast)

    return valid, similarity_results, param_results, svd_results, sn_results

def set_sample_range(series, sample_range, profile_type='sub'):
    """
    Sets the sample range for the series and returns the subtracted scattering
    profile corresponding to the specified sample range.

    Parameters
    ----------
    series: :class:`bioxtasraw.SECM.SECM`
        The input series to set the sample range for.
    sample_range: list
        A list defining the input sample range to be set. The list is made
        up of a set of sub-ranges, each defined by an entry in the list. Each
        sub-range item should be a list or tuple where the first entry is the
        starting index of the range and the second entry is the ending index
        of the range. So a list like ``[[0, 10], [100, 110]]`` would define
        a sample range consisting of two sub-ranges, the first from profiles 0-10
        in the series and the second from profiles 100-110 in the series.
    profile_type: {'unsub', 'sub', 'baseline'} str, optional
        Determines which type of profile to use from the series to set the
        sample range. Unsubtracted profiles - 'unsub', subtracted
        profiles - 'sub', baseline corrected profiles - 'baseline'.

    Returns
    -------
    sub_profile: :class:`bioxtasraw.SASM.SASM`
        The subtracted scattering profile calculated from the specified
        sample_range.
    """
    frame_idx = []
    for item in sample_range:
        frame_idx = frame_idx + list(range(item[0], item[1]+1))

    frame_idx = sorted(set(frame_idx))
    frame_idx = np.array(frame_idx)

    if profile_type == 'sub':

        profiles = series.getAllSASMs()
        profiles_list = [profiles[idx] for idx in frame_idx]

        average_profile = SASProc.average(profiles_list, forced=True)
        average_profile.setParameter('filename', ('A_{}'
            .format(average_profile.getParameter('filename'))))

        buffer_profile = series.average_buffer_sasm

        sub_profile = SASProc.subtract(average_profile, buffer_profile,
            forced=True)
        sub_profile.setParameter('filename', ('S_{}'
            .format(sub_profile.getParameter('filename'))))

    else:
        sub_profiles = series.baseline_subtracted_sasm_list

        profiles_list = [sub_profiles[idx] for idx in frame_idx]

        sub_profile = SASProc.average(profiles_list, forced=True)
        sub_profile.setParameter('filename', ('A_{}'
            .format(sub_profile.getParameter('filename'))))

    series.sample_range = sample_range

    return sub_profile

def find_baseline_range(series, baseline_type='Integral', profile_type='sub',
    window_size=5, int_type='total', q_val=None, q_range=None, settings=None,
    sim_test='CorMap', sim_cor='Bonferroni', sim_thresh=0.01):
    """
    Automatically determine an appropriate range for the baseline
    correction. Currently only works for integral baseline corrections.

    Parameters
    ----------
    series: list or :class:`bioxtasraw.SECM.SECM`
        The input series to find the baseline range for. It should either be
        a list of individual scattering profiles (:class:`bioxtasraw.SASM.SASM`)
        or a single series object (:class:`bioxtasraw.SECM.SECM`).
    baseline_type: {'Integral', 'Linear'} str, optional
        Defines the baseline type for validation purposes.
    profile_type: {'unsub', 'sub', 'baseline'} str, optional
        Only used if a :class:`bioxtasraw.SECM.SECM` is provided for the series
        argument. Determines which type of profile to use from the series to
        validate the baseline range. Unsubtracted profiles - 'unsub', subtracted
        profiles - 'sub', baseline corrected profiles - 'baseline'.
    window_size: int, optional
        The size of the average window used for calculating parameters from
        series data. Used to help set the size of the search window for the
        buffer region. Defaults to 5.
    int_type: {'total', 'mean', 'q_val', 'q_range'} str, optional
        The intensity type to use for the validation of the baseline range. Total
        integrated intensity - 'total', mean intensity - 'mean', intensity at
        a particular q value - 'q_val', intensity in a given q range -
        'q_range'. Use of q_val or q_range requires the corresponding parameter
        to be provided.
    q_val: float, optional
        If int_type is 'q_val', the q value used for the intensity is set by
        this parameter.
    q_range: list, optional
        This should have two entries, both floats. The first is the minimum q
        value of the range, the second the maximum q value of the range. If
        int_type is 'q_range', the q range used for the intensity is set by
        this parameter.
    settings: :class:`bioxtasraw.RAWSettings.RAWSettings`, optional
        RAW settings containing relevant parameters. If provided, sim_test,
        sim_cor, and sim_threshold are overridden by the values in the
        settings.
    sim_test: {'CorMap'} str, optional
        Sets the type of similarity test to be used. Currently only CorMap is
        supported as an option. Is overridden if settings are provided.
    sim_cor: {'Bonferroni', 'None'} str, optional
        Sets the multiple testing correction to be used as part of the similarity
        test. Default is Bonferroni. Is overridden if settings are provided.
    sim_thresh: float, optional
        Sets the p value threshold for the similarity test. A higher value is
        a more strict test (range from 0-1). Is overridden if settings are
        provided.

    Returns
    -------
    start_found: bool
        True if a start region was successfully found.
    end_found: bool
        True if an end region was successfully found.
    start_range: tuple
        A tuple where the first entry is the start of the start region and
        the second entry is the end of the start region. Returns -1 for each
        value if not start_found.
    end_range: tuple
        A tuple where the first entry is the start of the end region and
        the second entry is the end of the end region. Returns -1 for each
        value if not end_found.
    """

    if settings is not None:
        sim_thresh = settings.get('similarityThreshold')
        sim_test = settings.get('similarityTest')
        sim_cor = settings.get('similarityCorrection')

    if isinstance(series, SECM.SECM):
        if profile_type == 'unsub':
            sub_profiles = series._sasm_list
        elif profile_type == 'sub':
            sub_profiles = series.subtracted_sasm_list
        elif profile_type == 'baseline':
            sub_profiles = series.baseline_subtracted_sasm_list

        if not series.already_subtracted and len(series.buffer_range) ==1:
            start_region = series.buffer_range[0]
        else:
            start_region = None

    else:
        sub_profiles = series
        start_region = None

    if int_type == 'total':
        intensity = np.array([sasm.getTotalI() for sasm in sub_profiles])
    elif int_type == 'mean':
        intensity = np.array([sasm.getMeanI() for sasm in sub_profiles])
    elif int_type == 'q_val':
        intensity = np.array([sasm.getIofQ(q_val) for sasm in sub_profiles])
    elif int_type == 'q_range':
        q1 = q_range[0]
        q2 = q_range[1]
        intensity = np.array([sasm.getIofQRange(q1, q2) for sasm in sub_profiles])

    (start_failed, end_failed, region1_start, region1_end, region2_start,
        region2_end) = SASCalc.findBaselineRange(sub_profiles, intensity,
        baseline_type, window_size, start_region, sim_test, sim_cor, sim_thresh)

    start_found = not start_failed
    end_found = not end_failed
    start_range = (region1_start, region1_end)
    end_range = (region2_start, region2_end)

    return start_found, end_found, start_range, end_range

def validate_baseline_range(series, start_range, end_range,
    baseline_type='Integral', profile_type='sub', int_type='total',
    q_val=None, q_range=None, fast=False, settings=None, sim_test='CorMap',
    sim_cor='Bonferroni', sim_thresh=0.01):
    """
    Validates whether the input start and end ranges are a trustworthy baseline
    range or not. This is designed to work with SEC-SAXS data, but may work in
    other circumstances. Note that currently the validation for linear baselines
    almost always returns false, and is of little use.

    Parameters
    ----------
    series: list or :class:`bioxtasraw.SECM.SECM`
        The input series to validate the baseline range for. It should either be
        a list of individual scattering profiles (:class:`bioxtasraw.SASM.SASM`)
        or a single series object (:class:`bioxtasraw.SECM.SECM`).
    start_range: list
        A list defining the baseline start range to be validated. The list is two
        integers, the start of the range and the end of the range.
    end_range: list
        A list defining the baseline end range to be validated. The list is two
        integers, the start of the range and the end of the range.
    baseline_type: {'Integral', 'Linear'} str, optional
        Defines the baseline type for validation purposes.
    profile_type: {'unsub', 'sub', 'baseline'} str, optional
        Only used if a :class:`bioxtasraw.SECM.SECM` is provided for the series
        argument. Determines which type of profile to use from the series to
        validate the baseline range. Unsubtracted profiles - 'unsub', subtracted
        profiles - 'sub', baseline corrected profiles - 'baseline'.
    int_type: {'total', 'mean', 'q_val', 'q_range'} str, optional
        The intensity type to use for the validation of the baseline range. Total
        integrated intensity - 'total', mean intensity - 'mean', intensity at
        a particular q value - 'q_val', intensity in a given q range -
        'q_range'. Use of q_val or q_range requires the corresponding parameter
        to be provided.
    q_val: float, optional
        If int_type is 'q_val', the q value used for the intensity is set by
        this parameter.
    q_range: list, optional
        This should have two entries, both floats. The first is the minimum q
        value of the range, the second the maximum q value of the range. If
        int_type is 'q_range', the q range used for the intensity is set by
        this parameter.
    fast: bool, optional
        Whether the test should be done in fast mode or not. A fast test stops
        at the first failed check. In a normal test (not fast), all metrics
        are checked. Using a fast test is best when trying to automatically
        determine a baseline range, something which can take many separate
        validation checks. A normal test is best when trying to determine what,
        if anything, about your selected range might be problematic.
    settings: :class:`bioxtasraw.RAWSettings.RAWSettings`, optional
        RAW settings containing relevant parameters. If provided, sim_test,
        sim_cor, and sim_threshold are overridden by the values in the
        settings.
    sim_test: {'CorMap'} str, optional
        Sets the type of similarity test to be used. Currently only CorMap is
        supported as an option. Is overridden if settings are provided.
    sim_cor: {'Bonferroni', 'None'} str, optional
        Sets the multiple testing correction to be used as part of the similarity
        test. Default is Bonferroni. Is overridden if settings are provided.
    sim_thresh: float, optional
        Sets the p value threshold for the similarity test. A higher value is
        a more strict test (range from 0-1). Is overridden if settings are
        provided.

    Returns
    -------
    valid: bool
        If the baseline start and end ranges are a valid baseline range.
    valid_reuslts: tuple
        A tuple of bools. The first entry is whether the start range is
        valid, the second is whether the end range is valid. The start
        range is always valid for a linear baseline correction.
    similarity_results: tuple
        A tuple of dicts. The first entry is the start range similarity
        results, the second entry is the end range similarity results. A
        similarity test is only done for integral baselines. For linear
        baselines an empty dictionary is returned. For an integral baseline,
        each dictionary has the following keys are: 'all_similar' - whether all
        profiles in the selected range are similar over the entire profile.
        'low_q_similar' - whether all profiles in the selected range are
        similar over the low q region of the profile. 'high_q_similar' -
        whether all profiles in the selected range are similar over the high q
        region. 'max_idx' - The index of the profile used as the reference for
        the similarity test, corresponding to the profile with the highest
        intensity in the region. 'all_outliers' - Indices of the outlier
        profiles of the similarity test at all q. 'low_q_outliers' - Indices of
        the outlier profiles of the similarity test at low q. 'high_q_outliers'
        - Indices of the outlier profiles of the similarity test at high q.
    svd_results: tuple
        A tuple of dicts. The first entry is the start range svd results, the
        second is the end range svd results. A SVD test is only done for
        integral baselines. For linear baselines an empty dictionary is
        returned. For an integral baseline the dictionary keys are:
        'svals' - the number of significant singular vectors in the region. 'U'
        - the left singular vectors. 'V' - the right singular vectors.
        'u_autocor' - The autocorrelation of the left singular vectors.
        'v_autocor' - The autocorrelation of the right singular vectors.
    intI_results: tuple
        A tuple of dicts. The first entry is the start range intensity results,
        the second entry is the end range intensity results. The intensity
        test is only done for integral baselines. For linear baselines an
        empty dictionary is returned. For an integral baseline, each
        dictionary has the following keys: 'intI_r' - the Spearman correlation
        coefficient of the intensity in the region. 'inti_pval' - the p-value
        from the Spearman correlation test on the intensity of the region.
        'intI_valid' - Whether the range is a valid buffer range based on the
        intensity correlation. The same keys are provided but with smoothed in
        front, indicating the test results on the smoothed intensity.
    other_results: tuple
        A tuple of dicts. The first entry is the start range other results, the
        second entry is the end range other results. For either baseline type,
        only the end range has other results, as this is an evaluation based on
        comparing the end range to the start range. For an integral baseline,
        This contains the following keys: 'zero_valid' - whether all q points
        in the end region are higher than the same q points in the start region.
        'zero_outliers' - An array of bools in the shape of the input profile
        q vector. True where q values are more than 4 sigma lower in the
        end region than the start region. 'zero_q' - the q vector. For a
        linear baseline the following keys are available: 'fit_valid' -
        whether the fit is valid. Note that fit_valid almost always returns False,
        and is currently of little use.

    """
    if settings is not None:
        sim_thresh = settings.get('similarityThreshold')
        sim_test = settings.get('similarityTest')
        sim_cor = settings.get('similarityCorrection')

    #First do start range
    start = True
    start_ref_profiles = None

    start_frame_idx = np.arange(start_range[0], start_range[1]+1)

    if isinstance(series, SECM.SECM):
        start_profiles = [series.getSASM(idx, profile_type) for idx
            in start_frame_idx]
    else:
        start_profiles = [series[idx] for idx in start_frame_idx]

    if int_type == 'total':
        start_intensity = np.array([sasm.getTotalI() for sasm in start_profiles])
    elif int_type == 'mean':
        start_intensity = np.array([sasm.getMeanI() for sasm in start_profiles])
    elif int_type == 'q_val':
        start_intensity = np.array([sasm.getIofQ(q_val) for sasm
            in start_profiles])
    elif int_type == 'q_range':
        q1 = q_range[0]
        q2 = q_range[1]
        start_intensity = np.array([sasm.getIofQRange(q1, q2) for sasm
            in start_profiles])

    (start_valid, start_similarity_results, start_svd_results,
        start_intI_results, start_other_results) = SASCalc.validateBaseline(
        start_profiles, start_frame_idx, start_intensity, baseline_type,
        start_ref_profiles,  start, sim_test, sim_cor, sim_thresh, fast)


    #Next do end range
    start = False
    end_ref_profiles = start_profiles

    end_frame_idx = np.arange(end_range[0], end_range[1]+1)

    if isinstance(series, SECM.SECM):
        end_profiles = [series.getSASM(idx, profile_type) for idx
            in end_frame_idx]
    else:
        end_profiles = [series[idx] for idx in end_frame_idx]

    if int_type == 'total':
        end_intensity = np.array([sasm.getTotalI() for sasm in end_profiles])
    elif int_type == 'mean':
        end_intensity = np.array([sasm.getMeanI() for sasm in end_profiles])
    elif int_type == 'q_val':
        end_intensity = np.array([sasm.getIofQ(q_val) for sasm
            in end_profiles])
    elif int_type == 'q_range':
        q1 = q_range[0]
        q2 = q_range[1]
        end_intensity = np.array([sasm.getIofQRange(q1, q2) for sasm
            in end_profiles])

    (end_valid, end_similarity_results, end_svd_results,
        end_intI_results, end_other_results) = SASCalc.validateBaseline(
        end_profiles, end_frame_idx, end_intensity, baseline_type,
        end_ref_profiles,  start, sim_test, sim_cor, sim_thresh, fast)

    valid = start_valid and end_valid
    valid_results = (start_valid, end_valid)
    similarity_results = (start_similarity_results, end_similarity_results)
    svd_results = (start_svd_results, end_svd_results)
    intI_results = (start_intI_results, end_intI_results)
    other_results = (start_other_results, end_other_results)

    return (valid, valid_results, similarity_results, svd_results,
        intI_results, other_results)

def set_baseline_correction(series, start_range, end_range, baseline_type,
    bl_extrap=True, int_type='total', q_val=None, q_range=None, window_size=5,
    settings=None, min_iter=100, max_iter=2000,  calc_thresh=1.02,
    error_weight=True, vp_density=0.83*10**(-3), vp_cutoff='Default',
    vp_qmax=0.5, vc_protein=True, vc_cutoff='Manual', vc_qmax=0.3,
    vc_a_prot=1.0, vc_b_prot=0.1231, vc_a_rna=0.808, vc_b_rna=0.00934):
    """
    Calculates and sets the baseline correction for the input series. Then
    recalculates the series Rg and M.W. values based on the baseline corrected
    profiles. The input profile must have both unsubtracted and subtracted
    profiles.

    Parameters
    ----------
    series: :class:`bioxtasraw.SECM.SECM`
        The input series to calculate the baseline for.
    start_range: list
        A list defining the baseline start range to be validated. The list is two
        integers, the start of the range and the end of the range.
    end_range: list
        A list defining the baseline end range to be validated. The list is two
        integers, the start of the range and the end of the range.
    baseline_type: {'Integral', 'Linear'} str
        Defines the baseline type as either Integral or Linear.
    bl_extrap: bool, optional
        Used for a linear baseline. If True, the linear baseline correction is
        extrapolated to the entire series, if not it is only applied between
        the start_range and end_range.
    int_type: {'total', 'mean', 'q_val', 'q_range'} str, optional
        The intensity type to use the calculation of the baseline range. Total
        integrated intensity - 'total', mean intensity - 'mean', intensity at
        a particular q value - 'q_val', intensity in a given q range -
        'q_range'. Use of q_val or q_range requires the corresponding parameter
        to be provided.
    q_val: float, optional
        If int_type is 'q_val', the q value used for the intensity is set by
        this parameter.
    q_range: list, optional
        This should have two entries, both floats. The first is the minimum q
        value of the range, the second the maximum q value of the range. If
        int_type is 'q_range', the q range used for the intensity is set by
        this parameter.
    window_size: int, optional
        The size of the average window used when calculating Rg and MW.
        So if the window is 5, 5 a window is size 5 is slid along the series,
        and profiles in that window are averaged before being used to calculate
        Rg and MW. For example, frames 1-5, 2-6, 3-7, etc would be averaged and
        then have Rg and MW calculated from that average.
    settings: :class:`bioxtasraw.RAWSettings.RAWSettings`, optional
        RAW settings containing relevant parameters. If provided, sim_test,
        sim_cor, and sim_threshold are overridden by the values in the
        settings.
    min_iter: int, optional
        The minimum number of iterations for calculating the integral baseline
        correction. Overridden if settings are provided.
    max_iter: int, optional
        The maximum number of iterations for calculating the integral baseline
        correction. Overridden if settings are provided.
    calc_thresh: float, optional
        If the ratio of the scattering profile intensity to the average buffer
        intensity is greater than this threshold, the Rg and MW for the profile
        is calculated. Defaults to 1.02.
    error_weight: bool, optional
        Whether to use error weighting when calculating the Rg.
    vp_density: float, optional
        The density used for the Porod volume M.W. calculation in kDa/A^3.
        Defaults to 0.83*10**(-3).
    vp_cutoff: {''Default', '8/Rg', 'log(I0/I(q))', 'Manual''} str, optional
        The method to use to calculate the maximum q value used for the
        Porod volume M.W. calculation. Defaults to 'Default'
    vp_qmax: float, optional
        The maximum q value to be used if the 'Manual' cutoff method is
        selected for the Porod volume M.W. calculation. Defaults to 0.5.
    vc_protein: bool
        True if the sample is protein, False if the sample is RNA. Determines
        which set of coefficients to use for calculating M.W.
    vc_cutoff: {''Default', '8/Rg', 'log(I0/I(q))', 'Manual''} str, optional
        The method to use to calculate the maximum q value used for the
        M.W. calculation. Defaults to 'Manual'
    vc_qmax: float, optional
        The maximum q value to be used if the 'Manual' cutoff method is
        selected. Defaults to 0.3.
    vc_a_prot: float
        The volume of correlation A coefficient for protein. Not recommended
        to be changed.
    vc_b_prot: float
        The volume of correlation B coefficient for protein. Not recommended
        to be changed. Note that here B is defined as 1/B from the original paper.
    vc_a_rna: float
        The volume of correlation A coefficient for RNA. Not recommended to
        be changed.
    vc_b_rna: float
        The volume of correlation B coefficient for RNA. Not recommended to
        be changed. Note that here B is defined as 1/B from the original paper.

    Returns
    -------
    bl_cor_profiles: list
        A list of the baseline corrected profiles.
    rg: :class:`numpy.array`
        An array of the Rg values calculated for each subtracted profile. If
        no Rg value could be calculated then the value is -1. Each array index
        is the Rg corresponding to the subtracted profile at that index in
        the sub_profiles list.
    rger: :class:`numpy.array`
        An array of the uncertainty in the Rg values calculated for each
        subtracted profile. If no Rg value could be calculated then the
        value is -1. Each array index is the uncertainty corresponding to the
        subtracted profile at that index in  the sub_profiles list.
    i0: :class:`numpy.array`
        An array of the I(0) values calculated for each subtracted profile. If
        no I(0) value could be calculated then the value is -1. Each array index
        is the I(0) corresponding to the subtracted profile at that index in
        the sub_profiles list.
    i0er: :class:`numpy.array`
        An array of the uncertainty in the I(0) values calculated for each
        subtracted profile. If no I(0) value could be calculated then the
        value is -1. Each array index is the uncertainty corresponding to the
        subtracted profile at that index in  the sub_profiles list.
    vcmw: :class:`numpy.array`
        An array of the volume of correlation M.W. values calculated for each
        subtracted profile. If no M.W. value could be calculated then the value
        is -1. Each array index is the M.W. corresponding to the subtracted
        profile at that index in the sub_profiles list.
    vcmwer: :class:`numpy.array`
        An array of the uncertainty in the volume of correlation M.W. values
        calculated for each subtracted profile. If no M.W. value could be
        calculated then the value is -1. Each array index is the uncertainty
        corresponding to the subtracted profile at that index in  the
        sub_profiles list.
    vpmw: :class:`numpy.array`
        An array of the Porod volume M.W. values calculated for each subtracted
        profile. If no M.W. value could be calculated then the value is -1.
        Each array index is the M.W. corresponding to the subtracted profile
        at that index in the sub_profiles list.
    bl_corr: list
        A list of the baseline correction applied. Each item is a
        :class:`bioxtasraw.SASM.SASM`, and there is one for every baseline
        corrected profile. The intensity is the value subtracted from the
        starting intensity of the corresponding profile to achieve the
        baseline corrected intensity.
    fit_results: list
        Only contains items if a linear correction is done. In that case,
        each item is the linear fit results a, b, and corresponding covariances
        for a given q value. There is one item per q value of the input profiles.
    """

    # Set input values from settings if applicable

    if settings is not None:
        min_iter = settings.get('IBaselineMinIter')
        max_iter = settings.get('IBaselineMaxIter')
        calc_thresh = settings.get('secCalcThreshold')

        error_weight = settings.get('errorWeight')

        vp_cutoff = settings.get('MWVpCutoff')
        vp_density = settings.get('MWVpRho')
        vp_qmax = settings.get('MWVpQmax')

        vc_cutoff = settings.get('MWVcCutoff')
        vc_type = settings.get('MWVcType')
        vc_qmax = settings.get('MWVcQmax')

        if vc_type == 'Protein':
            vc_protein = True
        else:
            vc_protein = False

    unsub_profiles = series.getAllSASMs()
    sub_profiles = series.subtracted_sasm_list

    (bl_cor_profiles, use_sub_profiles, bl_corr, fit_results, sub_mean_i,
        sub_total_i, bl_sub_mean_i, bl_sub_total_i) = SASCalc.processBaseline(
        unsub_profiles, sub_profiles, start_range, end_range, baseline_type,
        min_iter, max_iter, bl_extrap, int_type, q_val, q_range, calc_thresh)

    success, results = SASCalc.run_secm_calcs(bl_cor_profiles, use_sub_profiles,
        window_size, vc_protein, error_weight, vp_density, vp_cutoff,
        vp_qmax, vc_cutoff, vc_qmax, vc_a_prot, vc_b_prot, vc_a_rna,
        vc_b_rna)

    if vc_protein:
        mol_type = 'Protein'
    else:
        mol_type = 'RNA'

    if success:
        rg = results['rg']
        rger = results['rger']
        i0 = results['i0']
        i0er = results['i0er']
        vcmw = results['vcmw']
        vcmwer = results['vcmwer']
        vpmw = results['vpmw']
    else:
        rg = np.zeros(len(sub_profiles),dtype=float)-1
        rger = np.zeros(len(sub_profiles),dtype=float)-1
        i0 = np.zeros(len(sub_profiles),dtype=float)-1
        i0er = np.zeros(len(sub_profiles),dtype=float)-1
        vcmw = np.zeros(len(sub_profiles),dtype=float)-1
        vcmwer = np.zeros(len(sub_profiles),dtype=float)-1
        vpmw = np.zeros(len(sub_profiles),dtype=float)-1


    series.window_size = window_size
    series.mol_type = mol_type
    series.mol_density = vp_density

    if rg.size > 0 and success:
        series.setCalcValues(rg, rger, i0, i0er, vcmw, vcmwer, vpmw)
        series.calc_has_data = True

    series.setBCSubtractedSASMs(bl_cor_profiles, use_sub_profiles)

    series.baseline_start_range = start_range
    series.baseline_end_range = end_range
    series.baseline_corr = bl_corr
    series.baseline_type = baseline_type
    series.baseline_extrap = bl_extrap
    series.baseline_fit_results = fit_results

    return (bl_cor_profiles, rg, rger, i0, i0er, vcmw, vcmwer, vpmw, bl_corr,
        fit_results)
