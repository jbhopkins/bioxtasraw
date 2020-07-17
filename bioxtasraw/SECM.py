""""""

from __future__ import absolute_import, division, print_function, unicode_literals

"""
Created on March 26, 2020

@author: Jesse Hopkins

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
"""

from builtins import object, range, map, open, zip
from io import open
import six

import os
import copy
import threading
import itertools

import numpy as np

raw_path = os.path.abspath(os.path.join('.', __file__, '..', '..'))
if raw_path not in os.sys.path:
    os.sys.path.append(raw_path)

import bioxtasraw.SASExceptions as SASExceptions
import bioxtasraw.SASProc as SASProc

class SECM(object):
    """
    Series measurement object. Was originally a SEC-SAXS measurement (SECM)
    object. Contains all the information about a series, including the
    individual scattering profiles, subtracted scattering profiles, baseline
    corrected scattering profiles, calculated parameter values such as Rg,
    total and mean intensity for each profile, information about selected
    buffer ranges and baseline correction ranges, etc.

    Attributes
        ----------
        qref: float
            The reference q value specified by :func:`I`.
        qrange: tuple
            The q range specified by :func:`calc_qrange_I`.
        buffer_range: list
            A list defining the set buffer range. The list is made up of a set
            of sub-ranges, each defined by an entry in the list. Each sub-range
            item should be a list or tuple where the first entry is the
            starting index of the range and the second entry is the ending index
            of the range. So a list like ``[[0, 10], [100, 110]]`` would define
            a buffer range consisting of two sub-ranges, the first from profiles
            0-10 in the series and the second from profiles 100-110 in the
            series.
        window_size: int
            The size of the average window used when calculating parameters
            such as Rg.
        mol_type: str
            The macromolecule type used when calculating the Vc M.W.
        mol_density: float
            The macromolecular density used when calculating the Vp M.W.
        already_subtracted: bool
            Whether the initial input profiles represent an already subtracted
            series or not.
        average_buffer_sasm: bioxtasraw.SASM.SASM
            The average buffer profile from the buffer_range.
        baseline_start_range: tuple
            A tuple where the first item is the start of the baseline start
            range and the second item is the end of the baseline start range.
        baseline_end_range: tuple
            A tuple where the first item is the start of the baseline end range
            and the second item is the end of the baseline end range.
        baseline_corr: list
            A list of the baseline correction applied. Each item is a
            :class:`bioxtasraw.SASM.SASM`, and there is one for every baseline
            corrected profile. The intensity is the value subtracted from the
            starting intensity of the corresponding profile to achieve the
            baseline corrected intensity.
        baseline_type: str
            The baseline type.
        baseline_extrap: bool
            Whether the baseline was extrapolated to all profiles.
        baseline_fit_results: list
            Only contains items if a linear baseline correction is done. In
            that case, each item is the linear fit results a, b, and
            corresponding covariances for a given q value. There is one item
            per q value of the input profiles.
        sample_range: list
            A list defining the set sample range. The list is made up of a set
            of sub-ranges, each defined by an entry in the list. Each sub-range
            item should be a list or tuple where the first entry is the
            starting index of the range and the second entry is the ending
            index of the range. So a list like ``[[0, 10], [100, 110]]`` would
            define a sample range consisting of two sub-ranges, the first from
            profiles 0-10 in the series and the second from profiles 100-110
            in the series.
    """

    def __init__(self, file_list, sasm_list, frame_list, parameters, settings):
        """
        Constructor

        Parameters
        ----------
        file_list: list
            A list of strings corresponding to the filenames of each input
            sasm.
        sasm_list: list
            A list of bioxtasraw.SASM.SASM objects, which are the individual
            scattering profiles that make up the series.
        frame_list: list
            A list of the frame numbers of each item in the sasm_list. Usually
            just range(len(sasm_list))
        parameters: dict
            A dictionary of metadata for the object. This should contain at
            least {'filename': filename_with_no_path}.
        settings: bioxtasraw.RAWSettings.RawGuiSettings
            RAW settings. Used to try compute the time associated with each
            input profile.
        """

        #Raw inputs variables
        self._file_list = file_list
        self._sasm_list = sasm_list
        self.frame_list = np.array(frame_list, dtype=int)
        self._parameters = parameters
        self._settings = settings

        # Make an entry for analysis parameters i.e. Rg, I(0) etc:
        if 'analysis' not in self._parameters:
            self._parameters['analysis'] = {}
        if 'history' not in self._parameters:
            self._parameters['history'] = {}
        if 'filename' not in self._parameters:
            files = [os.path.basename(f) for f in self._file_list]
            files = ['_'.join(f.split('_')[:-1]) for f in files]
            filename = os.path.commonprefix(files)
            if filename == '':
                filename =  os.path.splitext(os.path.basename(self._file_list[0]))[0]
            self._parameters['filename'] = filename

        #Extract initial mean and total intensity variables
        self.mean_i = np.array([sasm.getMeanI() for sasm in self._sasm_list])
        self.total_i = np.array([sasm.getTotalI() for sasm in self._sasm_list])

        #Make sure we have as many frame numbers as sasm objects

        if len(self._sasm_list) != len(self.frame_list):
            self.frame_list = np.arange(len(self._sasm_list))
            self._file_list=[sasm.getParameter('filename') for sasm in self._sasm_list]

        self.plot_frame_list = np.arange(len(self.frame_list))

        self.series_type = ''

        self._scale_factor = 1.0
        self._offset_value = 0.0
        self._frame_scale_factor = 1.0
        self._q_range = None
        self._sub_q_range = None
        self._bc_sub_q_range = None

        #variables used for plot management
        self.item_panel = None
        self.plot_panel = None
        self.line = None
        self.origline = None
        self.err_line = None
        self.axes = None
        self.is_plotted = False

        self.qref=0
        self.I_of_q = np.zeros_like(self.mean_i)
        self.qrange = (0,0)
        self.qrange_I = np.zeros_like(self.mean_i)

        self.time=[]
        self.hdr_format = settings.get('ImageHdrFormat')

        self._calcTime(self._sasm_list)

        ####### Parameters for autocalculating rg, MW for SEC plot
        self.buffer_range = []
        self.window_size = -1
        self.mol_type = ''
        self.mol_density = -1
        self.already_subtracted = False

        # Use this to signal if the intensity on plots changes, and so things
        # like use_subtracted_sasm need to be recalculated
        self.intensity_change = False

        self.average_buffer_sasm = None
        self.subtracted_sasm_list = []
        self.use_subtracted_sasm = []
        self.mean_i_sub = np.zeros_like(self.mean_i)
        self.total_i_sub = np.zeros_like(self.total_i)
        self.I_of_q_sub = np.zeros_like(self.I_of_q)
        self.qrange_I_sub = np.zeros_like(self.qrange_I)

        self.baseline_start_range = (-1, -1)
        self.baseline_end_range = (-1, -1)
        self.baseline_corr = []
        self.baseline_type = ''
        self.baseline_extrap = True
        self.baseline_fit_results = []

        self.baseline_subtracted_sasm_list = []
        self.use_baseline_subtracted_sasm = []
        self.mean_i_bcsub = np.zeros_like(self.mean_i)
        self.total_i_bcsub = np.zeros_like(self.total_i)
        self.I_of_q_bcsub = np.zeros_like(self.I_of_q)
        self.qrange_I_bcsub = np.zeros_like(self.qrange_I)

        self.sample_range = []

        self.rg_list = []
        self.rger_list = []
        self.i0_list = []
        self.i0er_list = []
        self.vpmw_list = []
        self.vcmw_list = []
        self.vcmwer_list = []

        self.calc_line = None
        self.calc_err_line = None
        self.calc_axes = None
        self.calc_is_plotted = False
        self.calc_has_data = False
        self.is_visible = True

        self.my_semaphore = threading.Semaphore()


    def _update(self):
        ''' updates modified intensity after scale, normalization and offset changes '''

        for i, sasm in enumerate(self._sasm_list):
            sasm.scale(self._scale_factor)
            sasm.offset(self._offset_value)

            if self._q_range is not None:
                sasm.setQrange((self._q_range[0], self._q_range[1]+1))

            self.mean_i[i] = sasm.getMeanI()
            self.total_i[i] = sasm.getTotalI()

            if self.qref > 0:
                self.I_of_q[i] = sasm.getIofQ(self.qref)

            if self.qrange[0] != 0 and self.qrange[1] != 0:
                self.qrange_I[i] = sasm.getIofQRange(self.qrange[0], self.qrange[1])

        for i, sasm in enumerate(self.subtracted_sasm_list):
            sasm.scale(self._scale_factor)
            sasm.offset(self._offset_value)

            if self._sub_q_range is not None:
                sasm.setQrange((self._sub_q_range[0], self._sub_q_range[1]+1))

            self.mean_i_sub[i] = sasm.getMeanI()
            self.total_i_sub[i] = sasm.getTotalI()

            if self.qref > 0:
                self.I_of_q_sub[i] = sasm.getIofQ(self.qref)

            if self.qrange[0] != 0 and self.qrange[1] != 0:
                self.qrange_I_sub[i] = sasm.getIofQRange(self.qrange[0], self.qrange[1])

        for i, sasm in enumerate(self.baseline_subtracted_sasm_list):
            sasm.scale(self._scale_factor)
            sasm.offset(self._offset_value)

            if self._bc_sub_q_range is not None:
                sasm.setQrange((self._bc_sub_q_range[0], self._bc_sub_q_range[1]+1))

            self.mean_i_bcsub[i] = sasm.getMeanI()
            self.total_i_bcsub[i] = sasm.getTotalI()

            if self.qref > 0:
                self.I_of_q_bcsub[i] = sasm.getIofQ(self.qref)

            if self.qrange[0] != 0 and self.qrange[1] != 0:
                self.qrange_I_bcsub[i] = sasm.getIofQRange(self.qrange[0], self.qrange[1])

        for i, sasm in enumerate(self.baseline_corr):
            sasm.scale(self._scale_factor)
            sasm.offset(self._offset_value)

            if self._sub_q_range is not None:
                sasm.setQrange((self._sub_q_range[0], self._sub_q_range[1]+1))

        if self.average_buffer_sasm is not None:
            self.average_buffer_sasm.scale(self._scale_factor)
            self.average_buffer_sasm.offset(self._offset_value)

            if self._sub_q_range is not None:
                self.average_buffer_sasm.setQrange((self._sub_q_range[0], self._sub_q_range[1]+1))


    def append(self, filename_list, sasm_list, frame_list):
        """
        Appends new data to the series. Used when operating in an 'online' mode
        during active data collection.

        Parameters
        ----------
        filename_list: list
            A list of strings corresponding to the filenames of each input
            sasm.
        sasm_list: list
            A list of bioxtasraw.SASM.SASM objects, which are the individual
            scattering profiles that make up the series.
        frame_list: list
            A list of the frame numbers of each item in the sasm_list. Usually
            just range(len(sasm_list))
        """
        for i, sasm in enumerate(sasm_list):
            sasm.scale(self._scale_factor)
            sasm.offset(self._offset_value)

            if self._q_range is not None:
                sasm.setQrange((self._q_range[0], self._q_range[1]+1))

        self._file_list.extend(filename_list)
        self._sasm_list.extend(sasm_list)
        self.frame_list = np.concatenate((self.frame_list, np.array(frame_list, dtype=int)))

        self.mean_i = np.concatenate((self.mean_i, np.array([sasm.getMeanI() for sasm in sasm_list])))
        self.total_i = np.concatenate((self.total_i, np.array([sasm.getTotalI() for sasm in sasm_list])))

        if len(self._sasm_list) != len(self.frame_list):
            self.frame_list = np.arange(len(self._sasm_list))
            print('Warning: Incorrect frame number input to SECM object. Using default frame numbers.')

        self._calcTime(sasm_list)

        if self.qref>0:
            I_of_q = np.array([sasm.getIofQ(self.qref) for sasm in sasm_list])
            self.I_of_q = np.concatenate((self.I_of_q, I_of_q))

        if self.qrange != (0,0):
            qrange_I = np.array([sasm.getIofQRange(self.qrange[0], self.qrange[1]) for sasm in sasm_list])
            self.qrange_I = np.concatenate((self.qrange_I, qrange_I))

        self.plot_frame_list = np.arange(len(self.frame_list))


    def getScale(self):
        """
        Returns the scale factor for the series.

        Returns
        -------
        scale: float
            The scale factor.
        """
        return self._scale_factor

    def getOffset(self):
        """
        Returns the offset for the series.

        Returns
        -------
        offset: float
            The offset.
        """
        return self._offset_value

    def getLine(self):
        """
        Returns the plotted line for the series. Only used in the RAW GUI.

        Returns
        -------
        line: matplotlib.lines.Line2D
            The plotted line.
        """
        return self.line

    def getCalcLine(self):
        """
        Returns the plotted line for the calculated values of the series, such
        as Rg. Only used in the RAW GUI.

        Returns
        -------
        line: matplotlib.lines.Line2D
            The plotted line.
        """
        return self.calc_line

    def getSASMList(self, initial_frame, final_frame, int_type='unsub'):
        """
        Gets the specified profiles of the series in a given frame range.

        Parameters
        ----------
        initial_frame: int
            The starting frame of profiles in the series to get.
        final_frame: int
            The final frame of profiles in the series to get.
        int_type: {'unsub', 'sub', 'baseline'} str, optional
            The type of profile to get. Either 'unsub' - unsubtracted,
            'sub' - subtracted, or 'baseline' - baseline corrected.

        Returns
        -------
        profiles: list
            A list of bioxtasraw.SASM.SASM profiles corresponding to the
            selected type and frame range.

        Raises
        ------
        SASExceptions.DataNotCompatible
            If the frame range is invalid or requesting a profile type not
            available in the series (such as asking for baseline corrected
            profiles when no baseline correction has been done).
        """
        sasms = []

        try:
            initial_frame = int(initial_frame)
        except:

            return sasms
        try:
            final_frame = int(final_frame)
        except Exception:
            raise SASExceptions.DataNotCompatible("Invalid value for final frame.")

        if initial_frame > final_frame:
            raise SASExceptions.DataNotCompatible("Initial frame larger than final frame.")

        elif initial_frame >= len(self.plot_frame_list):
            raise SASExceptions.DataNotCompatible("Initial frame not in data set.")

        if int_type == 'sub' and not self.subtracted_sasm_list:
            return sasms
        elif int_type == 'baseline' and not self.baseline_subtracted_sasm_list:
            return sasms

        if int_type == 'unsub':
            sasms = self._sasm_list[initial_frame : final_frame+1]
        elif int_type == 'sub':
            sasms = self.subtracted_sasm_list[initial_frame : final_frame+1]
        elif int_type == 'baseline':
            sasms = self.baseline_subtracted_sasm_list[initial_frame : final_frame+1]

        return sasms

    def getTime(self):
        """
        Gets the time associated with each scattering profile, if available.
        Returns an arary of -1 if not available.

        Returns
        -------
        time: numpy.array
            A array of the collection time of each profile, relative to the
            first.
        """
        if len(self.time)==0:
            return np.zeros_like(self.frame_list) - 1
        else:
            return self.time

    def _calcTime(self, sasm_list):
        time=list(self.time)

        if self.hdr_format == 'G1, CHESS' or self.hdr_format == 'G1 WAXS, CHESS':
            for sasm in sasm_list:
                if 'counters' in sasm.getAllParameters():
                    file_hdr = sasm.getParameter('counters')

                    if '#C' not in list(file_hdr.values()):
                        if 'Time' in file_hdr:
                            sasm_time = float(file_hdr['Time'])
                            time.append(sasm_time)

                        elif 'Seconds' in file_hdr:
                            sasm_time = float(file_hdr['Seconds'])
                            if len(time) == 0:
                                time.append(0)
                            else:
                                time.append(sasm_time+time[-1])

                        elif 'Exposure_time' in file_hdr:
                            sasm_time = float(file_hdr['Exposure_time'])
                            if len(time) == 0:
                                time.append(0)
                            else:
                                time.append(sasm_time+self.time[-1])

        elif self.hdr_format == 'BioCAT, APS':
            for sasm in sasm_list:
                if 'counters' in sasm.getAllParameters():
                    file_hdr = sasm.getParameter('counters')

                    if 'start_time' in file_hdr:
                        time.append(float(file_hdr['start_time']))

        self.time = np.array(time, dtype=float)

    def scaleRelative(self, relscale):
        """
        Applies a relative scale to the series intensity. If the scale factor
        is currently 1, then this is the same as :func:`scale`. Otherwise,
        this scales relative to the current scale factor. For example, suppose
        the scale factor is currently 2. If a relative scale of 2 is provided,
        the resulting scale factor if 4. Scale factors are always positive.

        Scale factors are applied to the individual profiles with the series,
        not to the overall intensity, so if the profiles are then retrieved
        from the series they will have the same scale factor as was applied
        to the series.

        Parameters
        ----------
        relscale: float
            The relative scale factor to be applied to the the profile
            intensity and uncertainty.
        """
        self._scale_factor = abs(self._scale_factor * relscale)
        self._update()

    def scale(self, scale_factor):
        """
        Applies an absolute scale to the series intensity. The scale factor
        supersedes the existing scale factor. For example, suppose the scale
        factor is currently 2. If a scale of 4 is provided, the resulting
        scale factor is 4 (not 8). Scale factors are always positive.

        Scale factors are applied to the individual profiles with the series,
        not to the overall intensity, so if the profiles are then retrieved
        from the series they will have the same scale factor as was applied
        to the series.

        Parameters
        ----------
        scale_factor: float
            The scale factor to be applied to the the profile intensity and
            uncertainty.
        """

        self._scale_factor = abs(scale_factor)
        self._update()

    def offset(self, offset_value):
        """
        Applies an absolute offset to the profile intensity. For example, if
        the offset is 1, then all the the intensities in the profile are
        increased by 1. Offset supersedes the existing offset, so if the
        current offset is 1, and an offset_value of 2 is provided, the
        resulting offset is 2 (not 3).

        Scale factors are applied to the individual profiles with the series,
        not to the overall intensity, so if the profiles are then retrieved
        from the series they will have the same scale factor as was applied
        to the series.

        Parameters
        ----------
        offset_value: float
            The offset to be applied to the profile intensity.
        """

        self._offset_value = offset_value
        self._update()

    def reset(self):
        """
        Removes scale and offset values from the series.
        """

        self._scale_factor = 1
        self._offset_value = 0
        self._frame_scale_factor = 1
        self._q_range = None

        self._update()

    def setQrange(self, n_min, n_max):
        """
        Sets the q range used for each profile in the series. Useful for
        trimming leading or trailing values of the q profile that are not
        useful data.

        Parameters
        ----------
        n_min: int
            The starting index of the q vector to be used.

        n_max: int
            The ending index of the q vector to be used, such that q[start:end]
            returns the desired q range.
        """
        self._q_range = (n_min, n_max)

        self._update()

    def setSubQrange(self, n_min, n_max):
        """
        Sets the q range used for each subtracted profile in the series. Useful
        for trimming leading or trailing values of the q profile that are not
        useful data.

        Parameters
        ----------
        n_min: int
            The starting index of the q vector to be used.

        n_max: int
            The ending index of the q vector to be used, such that q[start:end]
            returns the desired q range.
        """
        self._sub_q_range = (n_min, n_max)

        self._update()

    def setBCSubQrange(self, n_min, n_max):
        """
        Sets the q range used for each baseline corrected profile in the series.
        Useful for trimming leading or trailing values of the q profile that
        are not useful data.

        Parameters
        ----------
        n_min: int
            The starting index of the q vector to be used.

        n_max: int
            The ending index of the q vector to be used, such that q[start:end]
            returns the desired q range.
        """
        self._bc_sub_q_range = (n_min, n_max)

        self._update()

    def getQrange(self):
        """
        Returns the currently selected q range for each profile in the series
        as described in :func:`setQrange`.

        Returns
        -------
        q_range: tuple
            A tuple with 2 indices, the start and end of the selected
            q range, such that q[start:end] returns the desired q range.
        """
        return self._q_range

    def getSubQrange(self):
        """
        Returns the currently selected q range for each subtracted profile in
        the series as described in :func:`setSubQrange`.

        Returns
        -------
        q_range: tuple
            A tuple with 2 indices, the start and end of the selected
            q range, such that q[start:end] returns the desired q range.
        """
        return self._sub_q_range

    def getBCSubQrange(self):
        """
        Returns the currently selected q range for each baseline corrected
        profile in the series as described in :func:`setBCSubQrange`.

        Returns
        -------
        q_range: tuple
            A tuple with 2 indices, the start and end of the selected
            q range, such that q[start:end] returns the desired q range.
        """
        return self._bc_sub_q_range

    def setAllParameters(self, new_parameters):
        """
        Sets the parameters dictionary, which contains the series metadata,
        to the new input value.

        Parameters
        ----------
        new_parameters: dict
            A dictionary containing the new parameters.
        """
        self._parameters = new_parameters

    def getAllParameters(self):
        """
        Returns all of the metadata parameters associated with the series as
        a dictionary.

        Returns
        -------
        parameters: dict
            The metadata associated with the series.
        """
        return self._parameters

    def getParameter(self, key):
        """
        Gets a particular metadata parameter based on the provided key.

        Parameters
        ----------
        key: str
            A string that is a key in the parameters metadata dictionary.

        Returns
        -------
        parameter
            The parameter associated with the specified key. If the key is not
            in the parameter dictionary, None is returned.
        """

        if key in self._parameters:
            return self._parameters[key]
        else:
            return None

    def setParameter(self, key, value):
        """
        Sets a particular metadata parameter based on the provided key and value.

        Parameters
        ----------
        key: str
            The name of the new bit of metadata.
        value: object
            The value of the new bit of metadata. Could be anything that is
            an acceptable value for a dictionary.
        """

        self._parameters[key] = value

    def setScaleValues(self, scale_factor, offset_value, frame_scale_factor):
        """
        A convenience method that lets you set the scale offset, and frame scale
        values all at once.

        Note: Frame scale factor is currently not used.

        Parameters
        ----------
        scale_factor: float
            The scale factor to be applied to the series intensity.
        offset_value: float
            The offset to be applied to the series intensity.
        frame_scale_factor: float
            The scale factor to be applied to the series frame values.
        """

        self._scale_factor = scale_factor
        self._offset_value = offset_value
        self._frame_scale_factor = frame_scale_factor

    def extractAll(self):
        """
        Extracts all of the series data and returns it as a dict. Useful
        for pickling the series.

        Returns
        -------
        all_data: dict
            A dictionary with all the series data.
        """

        all_data = {}

        all_data['series_type'] = self.series_type
        all_data['file_list'] = self._file_list
        all_data['mean_i'] = self.mean_i
        all_data['total_i'] = self.total_i
        all_data['frame_list'] = self.frame_list
        all_data['i_of_q'] = self.I_of_q
        all_data['time'] = self.time
        all_data['qref'] = self.qref
        all_data['qrange'] = self.qrange
        all_data['qrange_I'] = self.qrange_I

        all_data['scale_factor'] = self._scale_factor
        all_data['offset_value'] = self._offset_value
        all_data['frame_scale_factor'] = self._frame_scale_factor

        all_data['parameters'] = self._parameters

        all_data['buffer_range'] = self.buffer_range
        all_data['window_size'] = self.window_size
        all_data['mol_type'] = self.mol_type
        all_data['mol_density'] = self.mol_density
        all_data['already_subtracted'] = self.already_subtracted

        all_data['mean_i_sub'] = self.mean_i_sub
        all_data['total_i_sub'] = self.total_i_sub
        all_data['I_of_q_sub'] = self.I_of_q_sub
        all_data['qrange_I_sub'] = self.qrange_I_sub

        all_data['baseline_start_range'] = self.baseline_start_range
        all_data['baseline_end_range'] = self.baseline_end_range
        all_data['baseline_type'] = self.baseline_type
        all_data['baseline_extrap'] = self.baseline_extrap
        all_data['baseline_fit_results'] = self.baseline_fit_results

        all_data['mean_i_bcsub'] = self.mean_i_bcsub
        all_data['total_i_bcsub'] = self.total_i_bcsub
        all_data['I_of_q_bcsub'] = self.I_of_q_bcsub
        all_data['qrange_I_bcsub'] = self.qrange_I_bcsub

        all_data['rg'] = self.rg_list
        all_data['rger'] = self.rger_list
        all_data['i0'] = self.i0_list
        all_data['i0er'] = self.i0er_list
        all_data['vcmw'] = self.vcmw_list
        all_data['vcmwer'] = self.vcmwer_list
        all_data['vpmw'] = self.vpmw_list

        all_data['sample_range'] = self.sample_range

        all_data['calc_has_data'] = self.calc_has_data
        all_data['is_visible'] = self.is_visible

        all_data['use_subtracted_sasm'] = self.use_subtracted_sasm
        all_data['use_baseline_subtracted_sasm'] = self.use_baseline_subtracted_sasm


        all_data['sasm_list'] = []
        for idx in range(len(self._sasm_list)):
            all_data['sasm_list'].append(self._sasm_list[idx].extractAll())

        if self.average_buffer_sasm is None or self.average_buffer_sasm == -1:
            all_data['average_buffer_sasm'] = self.average_buffer_sasm
        else:
            all_data['average_buffer_sasm'] = self.average_buffer_sasm.extractAll()


        all_data['subtracted_sasm_list'] = []
        for idx in range(len(self.subtracted_sasm_list)):
            if self.subtracted_sasm_list[idx] != -1:
                all_data['subtracted_sasm_list'].append(self.subtracted_sasm_list[idx].extractAll())
            else:
                all_data['subtracted_sasm_list'].append(-1)

        all_data['baseline_subtracted_sasm_list'] = []
        for idx in range(len(self.baseline_subtracted_sasm_list)):
            if self.baseline_subtracted_sasm_list[idx] != -1:
                all_data['baseline_subtracted_sasm_list'].append(self.baseline_subtracted_sasm_list[idx].extractAll())
            else:
                all_data['baseline_subtracted_sasm_list'].append(-1)

        all_data['baseline_corr'] = []
        for idx in range(len(self.baseline_corr)):
            if self.baseline_corr[idx] != -1:
                all_data['baseline_corr'].append(self.baseline_corr[idx].extractAll())
            else:
                all_data['baseline_corr'].append(-1)


        # Here's some stupid python 2 compatibility stuff
        if not six.PY3:
            str_key_list = ['series_type', 'mol_type', 'baseline_type']

            for key in str_key_list:
                all_data[key] = np.string_(all_data[key])

        return all_data

    def __deepcopy__(self, memo):
        ''' return a copy of the object '''

        copy_secm = SECM(copy.deepcopy(self._file_list), copy.deepcopy(self._sasm_list),
            copy.deepcopy(self.frame_list), copy.deepcopy(self._parameters), self._settings)

        copy_secm.qref = copy.deepcopy(self.qref)
        copy_secm.I_of_q = copy.deepcopy(self.I_of_q)
        copy_secm.qrange = copy.deepcopy(self.qrange)
        copy_secm.qrange_I = copy.deepcopy(self.qrange_I)

        copy_secm.time = copy.deepcopy(self.time)

        ####### Parameters for autocalculating rg, MW for SEC plot
        copy_secm.buffer_range = copy.deepcopy(self.buffer_range)
        copy_secm.window_size = copy.deepcopy(self.window_size)
        copy_secm.mol_type = copy.deepcopy(self.mol_type)
        copy_secm.mol_density = copy.deepcopy(self.mol_density)
        copy_secm.already_subtracted = copy.deepcopy(self.already_subtracted)
        copy_secm.calc_has_data = copy.deepcopy(self.calc_has_data)

        copy_secm.intensity_change = copy.deepcopy(self.intensity_change)

        copy_secm.average_buffer_sasm = copy.deepcopy(self.average_buffer_sasm)
        copy_secm.subtracted_sasm_list = copy.deepcopy(self.subtracted_sasm_list)
        copy_secm.use_subtracted_sasm = copy.deepcopy(self.use_subtracted_sasm)
        copy_secm.mean_i_sub = copy.deepcopy(self.mean_i_sub)
        copy_secm.total_i_sub = copy.deepcopy(self.total_i_sub)
        copy_secm.I_of_q_sub = copy.deepcopy(self.I_of_q_sub)
        copy_secm.qrange_I_sub = copy.deepcopy(self.qrange_I_sub)

        copy_secm.baseline_start_range = copy.deepcopy(self.baseline_start_range)
        copy_secm.baseline_end_range = copy.deepcopy(self.baseline_end_range)
        copy_secm.baseline_corr = copy.deepcopy(self.baseline_corr)
        copy_secm.baseline_type = copy.deepcopy(self.baseline_type)
        copy_secm.baseline_extrap = copy.deepcopy(self.baseline_extrap)
        copy_secm.baseline_fit_results = copy.deepcopy(self.baseline_fit_results)

        copy_secm.baseline_subtracted_sasm_list = copy.deepcopy(self.baseline_subtracted_sasm_list)
        copy_secm.use_baseline_subtracted_sasm = copy.deepcopy(self.use_baseline_subtracted_sasm)
        copy_secm.mean_i_bcsub = copy.deepcopy(self.mean_i_bcsub)
        copy_secm.total_i_bcsub = copy.deepcopy(self.total_i_bcsub)
        copy_secm.I_of_q_bcsub = copy.deepcopy(self.I_of_q_bcsub)
        copy_secm.qrange_I_bcsub = copy.deepcopy(self.qrange_I_bcsub)

        copy_secm.sample_range = copy.deepcopy(self.sample_range)

        copy_secm.rg_list = copy.deepcopy(self.rg_list)
        copy_secm.rger_list = copy.deepcopy(self.rger_list)
        copy_secm.i0_list = copy.deepcopy(self.i0_list)
        copy_secm.i0er_list = copy.deepcopy(self.i0er_list)
        copy_secm.vpmw_list = copy.deepcopy(self.vpmw_list)
        copy_secm.vcmw_list = copy.deepcopy(self.vcmw_list)
        copy_secm.vcmwer_list = copy.deepcopy(self.vcmwer_list)

        copy_secm._scale_factor = copy.deepcopy(self._scale_factor)
        copy_secm._offset_value = copy.deepcopy(self._offset_value)
        copy_secm._q_range = copy.deepcopy(self._q_range)
        copy_secm._sub_q_range = copy.deepcopy(self._sub_q_range)
        copy_secm._bc_sub_q_range = copy.deepcopy(self._bc_sub_q_range)

        copy_secm.series_type = copy.deepcopy(self.series_type)

        return copy_secm

    def getSASM(self, index=0, int_type='unsub'):
        """
        Gets the profile at a given frame number.

        Parameters
        ----------
        index: int, optional.
            The index of the profile to return. Defaults to the first profile.
        int_type: {'unsub', 'sub', 'baseline'} str, optional
            The type of profile to get. Either 'unsub' - unsubtracted,
            'sub' - subtracted, or 'baseline' - baseline corrected.

        Returns
        -------
        profile: bioxtasraw.SASM.SASM
            A scattering profile.
        """

        if int_type == 'sub' and not self.subtracted_sasm_list:
            sasm = self._sasm_list[index]
        elif int_type == 'baseline' and not self.baseline_subtracted_sasm_list:
            sasm = self._sasm_list[index]
        elif int_type == 'unsub':
            sasm = self._sasm_list[index]
        elif int_type == 'sub':
            sasm = self.subtracted_sasm_list[index]
        elif int_type == 'baseline':
            sasm = self.baseline_subtracted_sasm_list[index]

        return sasm

    def I(self, qref):
        """
        Sets the reference q value and returns the intensity of each profile
        at the specified q value (or the closest such value in each profile).

        Parameters
        ----------
        qref: float
            The reference q to get the intensity at.

        Returns
        -------
        intensity: numpy.array
            The intensity of each profile at the given q value.
        """
        self.qref=float(qref)
        self.I_of_q = np.array([sasm.getIofQ(qref) for sasm in self.getAllSASMs()])

        if self.subtracted_sasm_list:
            self.I_of_q_sub = np.array([sasm.getIofQ(qref) for sasm in self.subtracted_sasm_list])

        if self.baseline_subtracted_sasm_list:
            self.I_of_q_bcsub = np.array([sasm.getIofQ(qref) for sasm in self.baseline_subtracted_sasm_list])

        return self.I_of_q

    def calc_qrange_I(self, qrange):
        """
        Sets the reference q range and returns the intensity of each profile
        in the specified q range (or the closest such q values in each profile).

        Parameters
        ----------
        qrange: tuple or list
            A tuple or list with two items. The first item is the starting
            index of the q vector to be used, the second item is the ending
            index of the q vector to be used, such that q[start:end] returns
            the desired q range.

        Returns
        -------
        intensity: numpy.array
            The total intensity of each profile in the given q range.
        """
        self.qrange = qrange
        self.qrange_I = np.array([sasm.getIofQRange(qrange[0], qrange[1]) for sasm in self.getAllSASMs()])

        if self.subtracted_sasm_list:
            self.qrange_I_sub = np.array([sasm.getIofQRange(qrange[0], qrange[1]) for sasm in self.subtracted_sasm_list])

        if self.baseline_subtracted_sasm_list:
            self.qrange_I_bcsub = np.array([sasm.getIofQRange(qrange[0], qrange[1]) for sasm in self.baseline_subtracted_sasm_list])

        return self.qrange_I

    def getAllSASMs(self, int_type='unsub'):
        """
        Gets the all profiles in the series.

        Parameters
        ----------
        int_type: {'unsub', 'sub', 'baseline'} str, optional
            The type of profile to get. Either 'unsub' - unsubtracted,
            'sub' - subtracted, or 'baseline' - baseline corrected.

        Returns
        -------
        profiles: list
            A list of bioxtasraw.SASM.SASM profiles corresponding to the
            selected type.
        """
        if int_type == 'unsub':
            sasms = self._sasm_list
        elif int_type == 'sub':
            sasms = self.subtracted_sasm_list
        elif int_type == 'baseline':
            sasms = self.baseline_subtracted_sasm_list

        return sasms

    def setCalcValues(self, rg, rger, i0, i0er, vcmw, vcmwer, vpmw):
        """
        Sets the value of the calculated values for the series. If a value
        is not available for a given profile than a -1 value should be provided.

        Parameters
        ----------
        rg: np.array
            An array of the Rg values for each profile in the series.
        rger: np.array
            An array of the uncertainty in the Rg values for each profile
            in the series.
        i0: np.array
            An array of the I(0) values for each profile in the series.
        i0er: np.array
            An array of the uncertainty in the I(0) values for each profile
            in the series.
        vcmw: np.array
            An array of the volume of correlation M.W. values for each profile
            in the series.
        vcmwer: np.array
            An array of the uncertainty in the volume of correlation M.W.
            values for each profile in the series.
        vpmw: np.array
            An array of the corrected Porod volume M.W. values for each profile
            in the series.
        """
        self.rg_list = rg
        self.rger_list = rger
        self.i0_list = i0
        self.i0er_list = i0er
        self.vpmw_list = vpmw
        self.vcmw_list = vcmw
        self.vcmwer_list = vcmwer

    def getRg(self):
        """
        Returns the Rg and uncertainty in Rg values for each profile in the
        series. If the Rg value is not available for a given profile, then a
        -1 is returned.

        Returns
        -------
        rg: numpy.array
            The Rg values for each profile in the series.
        rger: numpy.array
            The uncertainty in the Rg values for each profile in the series.
        """
        return self.rg_list, self.rger_list

    def getVcMW(self):
        """
        Returns the volume of correlation M.W. and uncertainty values for each
        profile in the  series. If the M.W. value is not available for a given
        profile, then a -1 is returned.

        Returns
        -------
        vcmw: numpy.array
            The Vc M.W. values for each profile in the series.
        vcmwer: numpy.array
            The uncertainty in the Vc M.W. values for each profile in the series.
        """
        return self.vcmw_list, self.vcmwer_list

    def getVpMW(self):
        """
        Returns the corrected Porod volume M.W. and uncertainty values for each
        profile in the  series. If the M.W. value is not available for a given
        profile, then a -1 is returned. Currently uncertainty is not available,
        so an array of all -1 is returned.

        Returns
        -------
        vcmw: numpy.array
            The Vp M.W. values for each profile in the series.
        vcmwer: numpy.array
            The uncertainty in the Vp M.W. values for each profile in the series.
            Currently all -1, as this value is not calculated.
        """
        return self.vpmw_list, np.zeros_like(self.vpmw_list)-1

    def getI0(self):
        """
        Returns the I(0) and uncertainty in I(0) values for each profile in the
        series. If the I(0) value is not available for a given profile, then a
        -1 is returned.

        Returns
        -------
        i0: numpy.array
            The I(0) values for each profile in the series.
        i0er: numpy.array
            The uncertainty in the I(0) values for each profile in the series.
        """
        return self.i0_list, self.i0er_list

    def getIntI(self, int_type='unsub'):
        """
        Returns the total integrated intensity of each profile in the series.

        Parameters
        ----------
        int_type: {'unsub', 'sub', 'baseline'} str, optional
            The type of profile to get. Either 'unsub' - unsubtracted,
            'sub' - subtracted, or 'baseline' - baseline corrected.

        Returns
        -------
        intensity: numpy.array
            The total integrated intensity of each profile for the selected
            profile type.
        """
        if int_type == 'unsub':
            total_i = self.total_i
        elif int_type == 'sub':
            total_i = self.total_i_sub
        elif int_type == 'baseline':
            total_i = self.total_i_bcsub

        return total_i

    def getMeanI(self, int_type='unsub'):
        """
        Returns the mean intensity of each profile in the series.

        Parameters
        ----------
        int_type: {'unsub', 'sub', 'baseline'} str, optional
            The type of profile to get. Either 'unsub' - unsubtracted,
            'sub' - subtracted, or 'baseline' - baseline corrected.

        Returns
        -------
        intensity: numpy.array
            The mean intensity of each profile for the selected profile type.
        """
        if int_type == 'unsub':
            mean_i = self.mean_i
        elif int_type == 'sub':
            mean_i = self.mean_i_sub
        elif int_type == 'baseline':
            mean_i = self.mean_i_bcsub

        return mean_i

    def getIofQ(self, int_type='unsub'):
        """
        Returns the intensity of each profile at the  specified q value (or the
        closest such value in each profile). Use this instead of :func:`I` if
        you don't want to recalculate the intensity at the given reference q
        value.

        Parameters
        ----------
        int_type: {'unsub', 'sub', 'baseline'} str, optional
            The type of profile to get. Either 'unsub' - unsubtracted,
            'sub' - subtracted, or 'baseline' - baseline corrected.

        Returns
        -------
        intensity: numpy.array
            The intensity of each profile at the given q value for the selected
            profile type.
        """

        if int_type == 'unsub':
            i_of_q = self.I_of_q
        elif int_type == 'sub':
            i_of_q = self.I_of_q_sub
        elif int_type == 'baseline':
            i_of_q = self.I_of_q_bcsub

        return i_of_q

    def getIofQRange(self, int_type='unsub'):
        """
        Returns the intensity of each profile  in the specified q range (or
        the closest such q values in each profile). Use this instead of
        :func:`calc_qrange_I` if you don't want to recalculate the intensity
        for the given reference q range.

        Parameters
        ----------
        int_type: {'unsub', 'sub', 'baseline'} str, optional
            The type of profile to get. Either 'unsub' - unsubtracted,
            'sub' - subtracted, or 'baseline' - baseline corrected.

        Returns
        -------
        intensity: numpy.array
            The total intensity of each profile in the given q range for the
            selected profile type.
        """
        if int_type == 'unsub':
            qrange_I = self.qrange_I
        elif int_type == 'sub':
            qrange_I = self.qrange_I_sub
        elif int_type == 'baseline':
            qrange_I = self.qrange_I_bcsub

        return qrange_I

    def getFrames(self):
        """
        Returns the list of frames suitable for plotting the series intensity.
        Note that this may be different from the input frame list.

        Returns
        -------
        frame_list: numpy.array
            An array that starts from 0 and runs to the length of the series.
        """
        return self.plot_frame_list

    def appendCalcValues(self, rg, rger, i0, i0er, vcmw, vcmwer, vpmw,
        first_frame, window_size):
        """
        Appends new calculated parameter data to the series. Used when
        operating in an 'online' mode during active data collection.

        Parameters
        ----------
        rg: np.array
            An array of the new Rg values.
        rger: np.array
            An array of the new uncertainty in the Rg values.
        i0: np.array
            An array of the new I(0) values.
        i0er: np.array
            An array of the new uncertainty in the I(0) values.
        vcmw: np.array
            An array of the new volume of correlation M.W. values.
        vcmwer: np.array
            An array of the new uncertainty in the Vc M.W. values.
        vpmw: np.array
            An array of the new corrected Porod volume M.W. values.
        first_frame: int
            The first frame index of the new data.
        window_size: int
            The averaging window size used to calculate the parameters.
        """
        index1 = first_frame+(window_size-1)//2
        index2 = (window_size-1)//2

        self.rg_list = np.concatenate((self.rg_list[:index1],rg[index2:]))
        self.rger_list = np.concatenate((self.rger_list[:index1],rger[index2:]))
        self.i0_list = np.concatenate((self.i0_list[:index1],i0[index2:]))
        self.i0er_list = np.concatenate((self.i0er_list[:index1],i0er[index2:]))
        self.vcmw_list = np.concatenate((self.vcmw_list[:index1], vcmw[index2:]))
        self.vcmwer_list = np.concatenate((self.vcmwer_list[:index1], vcmwer[index2:]))
        self.vpmw_list = np.concatenate((self.vpmw_list[:index1], vpmw[index2:]))

    def acquireSemaphore(self):
        """
        Acquires a processing semaphore. Useful for multi-threading operations
        on the series.
        """
        self.my_semaphore.acquire()

    def releaseSemaphore(self):
        """
        Releases a processing semaphore. Useful for multi-threading operations
        on the series.
        """
        self.my_semaphore.release()

    def averageFrames(self, range_list, series_type, sim_test, sim_thresh,
        sim_cor, forced=False):
        """
        Creates an average profile from the frame ranges defined in the range_list.

        Parameters
        ----------
        range_list: list
            A list defining the input range to be averaged. The list  is made
            up of a set of sub-ranges, each defined by an entry in the  list.
            Each sub-range item should be a list or tuple where the first entry
            is the starting index of the range and the second entry is the
            ending index of the range. So a list like ``[[0, 10], [100, 110]]``
            would define a buffer range consisting of  two sub-ranges, the
            first from profiles 0-10 in the series and the second from profiles
            100-110 in the series.
        series_type: {'unsub', 'sub', 'baseline'} str, optional
            Determines which type of profile to average. Unsubtracted profiles
            - 'unsub', subtracted profiles - 'sub', baseline corrected profiles
            - 'baseline'
        sim_test: {'CorMap'} str, optional
            Sets the type of similarity test to be used. Currently only CorMap
            is supported as an option.
        sim_thresh: float, optional
            Sets the p value threshold for the similarity test. A higher value
            is a more strict test (range from 0-1).
        sim_cor: {'Bonferroni', 'None'} str, optional
            Sets the multiple testing correction to be used as part of the
            similarity test. Default is Bonferroni.
        forced: bool, optional
            If True, RAW will attempt to average profiles even if the q vectors
            do not agree or the profiles are not similar. Defaults to False.

        Returns
        -------
        average_profile: bioxtasraw.SASM.SASM
            The average profile. If averaging fails, returns None.
        success: bool
            Whether the average succeeded.
        error: tuple
            A tuple of strings. Both are empty if success. If the average failed,
            it contains either 'sim' or 'q_vector' to indicate the issue is
            either the profiles are not all similar or the q vectors do not
            all match. The second string is the names of the profiles where
            the check failed.
        """
        frame_idx = []
        for item in range_list:
            frame_idx = frame_idx + list(range(item[0], item[1]+1))

        frame_idx = sorted(set(frame_idx))

        if series_type == 'unsub':
            sasm_list = [self._sasm_list[idx] for idx in frame_idx]

        if not forced:
            ref_sasm = sasm_list[0]
            qi_ref, qf_ref = ref_sasm.getQrange()
            pvals = np.ones(len(sasm_list[1:]), dtype=float)

            for index, sasm in enumerate(sasm_list[1:]):
                qi, qf = sasm.getQrange()
                if not np.all(np.round(sasm.q[qi:qf], 5) == np.round(ref_sasm.q[qi_ref:qf_ref], 5)):
                    return None, False, ('q_vector', '')

                if sim_test == 'CorMap':
                    n, c, pval = SASProc.cormap_pval(ref_sasm.i[qi_ref:qf_ref], sasm.i[qi:qf])
                pvals[index] = pval

            if sim_cor == 'Bonferroni':
                pvals = pvals*len(sasm_list[1:])
                pvals[pvals>1] = 1

            if np.any(pvals<sim_thresh):
                dif_idx = itertools.compress(frame_idx[1:], pvals<sim_thresh)
                dif_idx = list(map(str, dif_idx))
                profile_str = ", ".join(dif_idx)
                find = profile_str.find(', ')
                i=1
                while find !=-1:
                    if i == 20:
                        profile_str = profile_str[:find]+',\n'+profile_str[find+len(', '):]
                        i=0
                    find = profile_str.find(', ', find+len(', ')+1)
                    i +=1

                return None, False, ('sim', profile_str)

        if self._scale_factor != 1 or self._offset_value != 0:
            avg_list = []
            for sasm in sasm_list:
                sasm.scale(1.0)
                sasm.offset(0)
                avg_list.append(sasm)
        else:
            avg_list = sasm_list

        average_sasm = SASProc.average(avg_list, forced=True)
        average_sasm.setParameter('filename', 'A_{}'.format(average_sasm.getParameter('filename')))

        if self._scale_factor != 1 or self._offset_value != 0:
            for sasm in sasm_list:
                sasm.scale(self._scale_factor)
                sasm.offset(self._offset_value)

            average_sasm.scale(self._scale_factor)
            average_sasm.offset(self._offset_value)

        return average_sasm, True, ('', '')

    def subtractAllSASMs(self, buffer_sasm, int_type, threshold, qref=None,
        qrange=None):
        """
        Subtracts the input buffer profile from all of the profiles in the
        series to generate subtracted profiles. Does not save the subtracted
        profiles to the series.

        Parameters
        ----------
        buffer_sasm: bioxtasraw.SASM.SASM
            The buffer profile to be subtracted.
        int_type: {'total', 'mean', 'q_val', 'q_range'} str, optional
            The intensity type to use when setting the buffer range. Total
            integrated intensity - 'total', mean intensity - 'mean', intensity
            at a particular q value - 'q_val', intensity in a given q range -
            'q_range'. Use of q_val or q_range requires the corresponding
            parameter to be provided.
        threshold: float
            If the ratio of the scattering profile intensity to the average buffer
            intensity is greater than this threshold, the use_subtracted_sasm
            flag for that profile will be set to true. This flag can later be
            used for calculating Rg, M.W., etc, to determine which profiles to
            attempt the calculation for.
        q_val: float, optional
            If int_type is 'q_val', the q value used for the intensity is set
            by this parameter.
        q_range: list, optional
            This should have two entries, both floats. The first is the minimum
            q value of the range, the second the maximum q value of the range.
            If int_type is 'q_range', the q range used for the intensity is set
            by this parameter.

        Returns
        -------
        subtracted_sasms: list
            A list of the subtracted profiles (bioxtasraw.SASM.SASM).
        use_subtracted_sasms: list
            A list of bool values corresponding to the subtracted profile. If
            True, the corresponding profile has a intensity ratio above the
            buffer greater than the threshold, and so should be used when
            calculating Rg, M.W., and other parameters.
        """
        subtracted_sasms = []
        use_subtracted_sasms = []

        if int_type == 'total':
            ref_intensity = buffer_sasm.getTotalI()

        elif int_type == 'mean':
            ref_intensity = buffer_sasm.getMeanI()

        elif int_type == 'q_val':
            ref_intensity = buffer_sasm.getIofQ(qref)
        elif int_type == 'q_range':
            ref_intensity = buffer_sasm.getIofQRange(qrange[0], qrange[1])

        for sasm in self.getAllSASMs():
            subtracted_sasm = SASProc.subtract(sasm, buffer_sasm, forced = True)
            subtracted_sasm.setParameter('filename', 'S_{}'.format(subtracted_sasm.getParameter('filename')))

            subtracted_sasms.append(subtracted_sasm)

            #check to see whether we actually need to subtract this curve
            if int_type == 'total':
                sasm_intensity = sasm.getTotalI()

            elif int_type == 'mean':
                sasm_intensity = sasm.getMeanI()

            elif int_type == 'q_val':
                sasm_intensity = sasm.getIofQ(qref)
            elif int_type == 'q_range':
                sasm_intensity = sasm.getIofQRange(qrange[0], qrange[1])

            if abs(sasm_intensity/ref_intensity) > threshold:
                use_subtracted_sasms.append(True)
            else:
                use_subtracted_sasms.append(False)

        return subtracted_sasms, use_subtracted_sasms

    @staticmethod
    def subtractSASMs(buffer_sasm, sasms, int_type, threshold, qref=None,
        qrange=None):
        """
        Subtracts the input buffer profile from the input profiles to generate
        subtracted profiles.

        Parameters
        ----------
        buffer_sasm: bioxtasraw.SASM.SASM
            The buffer profile to be subtracted.
        sasms: list
            A list of profiles to subtract the buffer from.
        int_type: {'total', 'mean', 'q_val', 'q_range'} str, optional
            The intensity type to use when setting the buffer range. Total
            integrated intensity - 'total', mean intensity - 'mean', intensity
            at a particular q value - 'q_val', intensity in a given q range -
            'q_range'. Use of q_val or q_range requires the corresponding
            parameter to be provided.
        threshold: float
            If the ratio of the scattering profile intensity to the average buffer
            intensity is greater than this threshold, the use_subtracted_sasm
            flag for that profile will be set to true. This flag can later be
            used for calculating Rg, M.W., etc, to determine which profiles to
            attempt the calculation for.
        q_val: float, optional
            If int_type is 'q_val', the q value used for the intensity is set
            by this parameter.
        q_range: list, optional
            This should have two entries, both floats. The first is the minimum
            q value of the range, the second the maximum q value of the range.
            If int_type is 'q_range', the q range used for the intensity is set
            by this parameter.

        Returns
        -------
        subtracted_sasms: list
            A list of the subtracted profiles (bioxtasraw.SASM.SASM).
        use_subtracted_sasms: list
            A list of bool values corresponding to the subtracted profile. If
            True, the corresponding profile has a intensity ratio above the
            buffer greater than the threshold, and so should be used when
            calculating Rg, M.W., and other parameters.
        """
        subtracted_sasms = []
        use_subtracted_sasms = []

        if int_type == 'total':
            ref_intensity = buffer_sasm.getTotalI()

        elif int_type == 'mean':
            ref_intensity = buffer_sasm.getMeanI()

        elif int_type == 'q_val':
           ref_intensity = buffer_sasm.getIofQ(qref)
        elif int_type == 'q_range':
            ref_intensity = buffer_sasm.getIofQRange(qrange[0], qrange[1])

        for sasm in sasms:
            subtracted_sasm = SASProc.subtract(sasm, buffer_sasm, forced = True)
            subtracted_sasm.setParameter('filename', 'S_{}'.format(subtracted_sasm.getParameter('filename')))

            subtracted_sasms.append(subtracted_sasm)

            #check to see whether we actually need to subtract this curve
            if int_type == 'total':
                sasm_intensity = sasm.getTotalI()

            elif int_type == 'mean':
                sasm_intensity = sasm.getMeanI()

            elif int_type == 'q_val':
                sasm_intensity = sasm.getIofQ(qref)
            elif int_type == 'q_range':
                sasm_intensity = sasm.getIofQRange(qrange[0], qrange[1])

            if abs(sasm_intensity/ref_intensity) > threshold:
                use_subtracted_sasms.append(True)
            else:
                use_subtracted_sasms.append(False)

        return subtracted_sasms, use_subtracted_sasms

    def setSubtractedSASMs(self, sub_sasm_list, use_sub_sasm):
        """
        Sets the subtracted profiles for the series.

        Parameters
        ----------
        sub_sasm_list: list
            A list of the subtracted profiles.
        use_sub_sasm: list
            A list of bools indicating whether or not the subtracted profiles
            should be used when calculating parameters such as Rg.
        """
        for i, sasm in enumerate(sub_sasm_list):
            sasm.scale(self._scale_factor)
            sasm.offset(self._offset_value)

            if self._sub_q_range is not None:
                sasm.setQrange((self._sub_q_range[0], self._sub_q_range[1]+1))

        self.subtracted_sasm_list = list(sub_sasm_list)
        self.use_subtracted_sasm = list(use_sub_sasm)

        self.mean_i_sub = np.array([sasm.getMeanI() for sasm in sub_sasm_list])
        self.total_i_sub = np.array([sasm.getTotalI() for sasm in sub_sasm_list])

        if self.qref>0:
            self.I_of_q_sub = np.array([sasm.getIofQ(self.qref) for sasm in sub_sasm_list])

        if self.qrange != (0,0):
            self.qrange_I_sub = np.array([sasm.getIofQRange(self.qrange[0], self.qrange[1]) for sasm in sub_sasm_list])

    def appendSubtractedSASMs(self, sub_sasm_list, use_sasm_list, window_size):
        """
        Appends new subtracted data to the series. Used when operating in an
        'online' mode during active data collection.

        Parameters
        ----------
        sub_sasm_list: list
            A list of the subtracted profiles.
        use_sasm_list: list
            A list of bools indicating whether or not the subtracted profiles
            should be used when calculating parameters such as Rg.
        window_size: int
            The averaging window size used to calculate the parameters.
        """
        for i, sasm in enumerate(sub_sasm_list):
            sasm.scale(self._scale_factor)
            sasm.offset(self._offset_value)

            if self._sub_q_range is not None:
                sasm.setQrange((self._sub_q_range[0], self._sub_q_range[1]+1))

        self.subtracted_sasm_list = self.subtracted_sasm_list[:-window_size] + sub_sasm_list
        self.use_subtracted_sasm = self.use_subtracted_sasm[:-window_size] + use_sasm_list

        self.mean_i_sub = np.concatenate((self.mean_i_sub[:-window_size],
            np.array([sasm.getMeanI() for sasm in sub_sasm_list])))
        self.total_i_sub = np.concatenate((self.total_i_sub[:-window_size],
            np.array([sasm.getTotalI() for sasm in sub_sasm_list])))

        if self.qref>0:
            I_of_q_sub = np.array([sasm.getIofQ(self.qref) for sasm in sub_sasm_list])
            self.I_of_q_sub = np.concatenate((self.I_of_q_sub[:-window_size],
                I_of_q_sub))

        if self.qrange != (0,0):
            qrange_I_sub = np.array([sasm.getIofQRange(self.qrange[0], self.qrange[1]) for sasm in sub_sasm_list])
            self.qrange_I_sub = np.concatenate((self.qrange_I_sub[:-window_size],
                qrange_I_sub))

    def setBCSubtractedSASMs(self, sub_sasm_list, use_sub_sasm):
        """
        Sets the baseline corrected subtracted profiles for the series.

        Parameters
        ----------
        sub_sasm_list: list
            A list of the baseline corrected subtracted profiles.
        use_sub_sasm: list
            A list of bools indicating whether or not the profiles should be
            used when calculating parameters such as Rg.
        """
        for i, sasm in enumerate(sub_sasm_list):
            sasm.scale(self._scale_factor)
            sasm.offset(self._offset_value)

            if self._bc_sub_q_range is not None:
                sasm.setQrange((self._bc_sub_q_range[0], self._bc_sub_q_range[1]+1))

        self.baseline_subtracted_sasm_list = list(sub_sasm_list)
        self.use_baseline_subtracted_sasm = list(use_sub_sasm)

        self.mean_i_bcsub = np.array([sasm.getMeanI() for sasm in sub_sasm_list])
        self.total_i_bcsub = np.array([sasm.getTotalI() for sasm in sub_sasm_list])

        if self.qref>0:
            self.I_of_q_bcsub = np.array([sasm.getIofQ(self.qref) for sasm in sub_sasm_list])

        if self.qrange != (0,0):
            self.qrange_I_bcsub = np.array([sasm.getIofQRange(self.qrange[0], self.qrange[1]) for sasm in sub_sasm_list])

    def appendBCSubtractedSASMs(self, sub_sasm_list, use_sasm_list, window_size):
        """
        Appends new baseline corrected subtracted data to the series. Used
        when operating in an 'online' mode during active data collection.

        Parameters
        ----------
        sub_sasm_list: list
            A list of the baseline corrected subtracted profiles.
        use_sasm_list: list
            A list of bools indicating whether or not the baseline corrected
            subtracted profiles should be used when calculating parameters
            such as Rg.
        window_size: int
            The averaging window size used to calculate the parameters.
        """
        for i, sasm in enumerate(sub_sasm_list):
            sasm.scale(self._scale_factor)
            sasm.offset(self._offset_value)

            if self._bc_sub_q_range is not None:
                sasm.setQrange((self._bc_sub_q_range[0], self._bc_sub_q_range[1]+1))

        self.baseline_subtracted_sasm_list = self.baseline_subtracted_sasm_list[:-window_size] + sub_sasm_list
        self.use_baseline_subtracted_sasm = self.use_baseline_subtracted_sasm[:-window_size] + use_sasm_list

        self.mean_i_bcsub = np.concatenate((self.mean_i_bcsub[:-window_size],
            np.array([sasm.getMeanI() for sasm in sub_sasm_list])))
        self.total_i_bcsub = np.concatenate((self.total_i_bcsub[:-window_size],
            np.array([sasm.getTotalI() for sasm in sub_sasm_list])))

        if self.qref>0:
            I_of_q_bcsub = np.array([sasm.getIofQ(self.qref) for sasm in sub_sasm_list])
            self.I_of_q_bcsub = np.concatenate((self.I_of_q_bcsub[:-window_size],
                I_of_q_bcsub))

        if self.qrange != (0,0):
            qrange_I_bcsub = np.array([sasm.getIofQRange(self.qrange[0], self.qrange[1]) for sasm in sub_sasm_list])
            self.qrange_I_bcsub = np.concatenate((self.qrange_I_bcsub[:-window_size],
                qrange_I_bcsub))
