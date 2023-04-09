""""""

from __future__ import absolute_import, division, print_function, unicode_literals

"""
Created on Jul 5, 2010

@author: Soren S. Nielsen

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

from builtins import object, range, map, zip
from io import open

import copy
import os

import numpy as np
from scipy import integrate as integrate

raw_path = os.path.abspath(os.path.join('.', __file__, '..', '..'))
if raw_path not in os.sys.path:
    os.sys.path.append(raw_path)

import bioxtasraw.SASExceptions as SASExceptions


class SASM(object):
    """
    Small Angle Scattering Measurement (SASM) Object. Essentially a
    scattering profile with q, i, and uncertainty, plus a lot of metadata.

    Attributes
    ----------
    q: numpy.array
        The scaled q vector, without the trimming specified by
        :func:`setQrange`.
    i: numpy.array
        The scaled intensity vector, without the trimming specified by
        :func:`setQrange`.
    err: numpy.array
        The scaled error vector, without the trimming specified by
        :func:`setQrange`.
    q_err: numpy.array
        The scaled q error vector, without the trimming specified by
        :func:`setQrange`. Typically only used with SANS data.
    """

    def __init__(self, i, q, err, parameters, q_err=None):
        """
        Constructor

        Parameters
        ----------
        i: numpy.array
            The intensity vector.
        q: numpy.array
            The q vector.
        err: numpy.array
            The error vector.
        parameters: dict
            A dictionary of metadata for the object. This should contain at
            least {'filename': filename_with_no_path}. Other reserved keys are:
            'counters' : [(countername, value),...] Info from counter files
            'fileHeader' : [(label, value),...] Info from the header in the
            loaded file
        """

        #Raw intensity variables
        self._i_raw = np.array(i)
        self._q_raw = np.array(q)
        self._err_raw = np.array(err)
        self._parameters = parameters



        # Make an entry for analysis parameters i.e. Rg, I(0) etc:
        if 'analysis' not in self._parameters:
            self._parameters['analysis'] = {}
        if 'history' not in self._parameters:
            self._parameters['history'] = {}
        if 'unit' not in self._parameters:
            self._parameters['unit'] = ''

        #Modified intensity variables
        self.i = self._i_raw.copy()
        self.q = self._q_raw.copy()
        self.err = self._err_raw.copy()

        #For SANS data with a qerr column
        try:
            if q_err is not None:
                self._q_err_raw = np.array(q_err)
                self.q_err = self._q_err_raw.copy()
            else:
                self._q_err_raw = None
                self.q_err = None
        except Exception:
            self._q_err_raw = None
            self.q_err = None

        self._scale_factor = 1
        self._offset_value = 0
        self._q_scale_factor = 1

        #variables used for plot management
        self.item_panel = None
        self.plot_panel = None
        self.line = None
        self.err_line = None
        self.axes = None
        self.is_plotted = False
        self._selected_q_range = (0, len(self._q_raw))

        #Calculated values
        try:
            if len(self.q)>0:
                self.total_intensity = integrate.trapz(self.getI(), self.getQ())
                self.mean_intensity = self.getI().mean()
            else:
                self.total_intensity = -1
                self.mean_intensity = -1

        except Exception as e:
            print(e)
            self.total_intensity = -1
            self.mean_intensity = -1

    def __deepcopy__(self, memo):
        #Raw intensity variables
        i_raw = copy.deepcopy(self._i_raw, memo)
        q_raw = copy.deepcopy(self._q_raw, memo)
        err_raw = copy.deepcopy(self._err_raw, memo)
        parameters = copy.deepcopy(self._parameters, memo)

        newsasm = SASM(i_raw, q_raw, err_raw, parameters)

        newsasm.setQrange(copy.deepcopy(self.getQrange(), memo))
        newsasm.setRawQErr(copy.deepcopy(self._q_err_raw, memo))

        newsasm.scale(copy.deepcopy(self.getScale(), memo))
        newsasm.offset(copy.deepcopy(self.getOffset(), memo))
        newsasm._q_scale_factor = copy.deepcopy(self._q_scale_factor, memo)

        newsasm._update()

        return newsasm

    def copy_no_metadata(self):
        """
        Creates a deep copy of the SAMS without the metadata, which will usually
        be faster.
        """
        i_raw = copy.deepcopy(self._i_raw)
        q_raw = copy.deepcopy(self._q_raw)
        err_raw = copy.deepcopy(self._err_raw)
        parameters = {}

        newsasm = SASM(i_raw, q_raw, err_raw, parameters)

        newsasm.setQrange(copy.deepcopy(self.getQrange()))
        newsasm.setRawQErr(copy.deepcopy(self._q_err_raw))

        newsasm.scale(copy.deepcopy(self.getScale()))
        newsasm.offset(copy.deepcopy(self.getOffset()))
        newsasm._q_scale_factor = copy.deepcopy(self._q_scale_factor)

        newsasm._update()

        return newsasm

    def _update(self):
        ''' updates modified intensity after scale, normalization and offset changes '''

        self.i = (self._i_raw * self._scale_factor) + self._offset_value
        self.err = self._err_raw * abs(self._scale_factor)
        self.q = self._q_raw * self._q_scale_factor

        if self._q_err_raw is not None:
            self.q_err = self._q_err_raw*self._q_scale_factor

        # print self.err_line

        if self.err_line is not None:
            #Update errorbar positions
            caplines = self.err_line[0]
            barlinecols = self.err_line[1]

            yerr = self.err
            x = self.q
            y = self.i

            # Find the ending points of the errorbars
            error_positions = (x, y-yerr), (x, y+yerr)

            # Update the caplines
            for i,pos in enumerate(error_positions):
                caplines[i].set_data(pos)

            # Update the error bars
            barlinecols[0].set_segments(list(zip(list(zip(x,y-yerr)), list(zip(x,y+yerr)))))

        #Calculated values
        try:
            if len(self.q)>0:
                self.total_intensity = integrate.trapz(self.getI(), self.getQ())
                self.mean_intensity = self.getI().mean()
            else:
                self.total_intensity = -1
                self.mean_intensity = -1

        except Exception as e:
            print(e)
            self.total_intensity = -1
            self.mean_intensity = -1

    def getScale(self):
        """
        Returns the scale factor for the profile.

        Returns
        -------
        scale: float
            The scale factor.
        """
        return self._scale_factor

    def getOffset(self):
        """
        Returns the offset for the profile.

        Returns
        -------
        offset: float
            The offset.
        """
        return self._offset_value

    def getLine(self):
        """
        Returns the plotted line for the profile. Only used in the RAW GUI.

        Returns
        -------
        line: matplotlib.lines.Line2D
            The plotted line.
        """
        return self.line

    def scaleRelative(self, relscale):
        """
        Applies a relative scale to the profile intensity. If the scale factor
        is currently 1, then this is the same as :func:`scale`. Otherwise,
        this scales relative to the current scale factor. For example, suppose
        the scale factor is currently 2. If a relative scale of 2 is provided,
        the resulting scale factor if 4. Scale factors are always positive.

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
        Applies an absolute scale to the profile intensity. The scale factor
        supersedes the existing scale factor. For example, suppose the scale
        factor is currently 2. If a scale of 4 is provided, the resulting
        scale factor is 4 (not 8). Scale factors are always positive.

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

        Parameters
        ----------
        offset_value: float
            The offset to be applied to the profile intensity.
        """

        self._offset_value = offset_value
        self._update()

    def scaleRawQ(self, scale_factor):
        """
        Scales the raw q values. These are the q values without any scale
        applied. The raw q scale factor is not tracked, so this cannot easily
        be undone, unlike the :func:scaleQ function.

        Parameters
        ----------
        scale_factor: float
            The scale factor to be applied to the raw profile q values.
        """
        self._q_raw = self._q_raw * scale_factor
        self._update()

    def scaleQ(self, q_scale_factor):
        """
        Scales the profile q values by a factor. The scale factor
        supersedes the existing scale factor. For example, suppose the scale
        factor is currently 2. If a scale of 4 is provided, the resulting
        scale factor if 4 (not 8). Useful for converting between 1/A and 1/nm,
        for example.

        Parameters
        ----------
        q_scale_factor: float
            The scale factor to be applied to the profile q values.
        """

        self._q_scale_factor = q_scale_factor
        self._update()

    def scaleRelativeQ(self, relscale):
        """
        Applies a relative scale to the profile q. If the scale factor
        is currently 1, then this is the same as :func:`scale`. Otherwise,
        this scales relative to the current scale factor. For example, suppose
        the scale factor is currently 2. If a relative scale of 2 is provided,
        the resulting scale factor if 4.

        Parameters
        ----------
        relscale: float
            The relative scale factor to be applied to the the profile
            intensity and uncertainty.
        """
        self._q_scale_factor = self._q_scale_factor * relscale
        self._update()

    def reset(self):
        """
        Removes scale and offset values from the intensity, uncertainty, and q.
        """

        self.i = self._i_raw.copy()
        self.q = self._q_raw.copy()
        self.err = self._err_raw.copy()

        self._scale_factor = 1
        self._offset_value = 0
        self._q_scale_factor = 1

    def setQrange(self, qrange):
        """
        Sets the q range used for the profile. Useful for trimming leading or
        trailing values of the q profile that are not useful data.

        Parameters
        ----------
        qrange: tuple or list
            A tuple or list with two items. The first item is the starting
            index of the q vector to be used, the second item is the ending
            index of the q vector to be used, such that q[start:end] returns
            the desired q range.
        """
        if qrange[0] < 0 or qrange[1] > (len(self._q_raw)):
            msg = ('Qrange: ' + str(qrange) + ' is not a valid q-range for a '
                'q-vector of length ' + str(len(self._q_raw)-1))
            raise SASExceptions.InvalidQrange(msg)
        else:
            self._selected_q_range = list(map(int, qrange))

            try:
                if len(self.q)>0:
                    self.total_intensity = integrate.trapz(self.getI(), self.getQ())
                    self.mean_intensity = self.getI().mean()
                else:
                    self.total_intensity = -1
                    self.mean_intensity = -1

            except Exception as e:
                print(e)
                self.total_intensity = -1
                self.mean_intensity = -1


    def getQrange(self):
        """
        Returns the currently selected q range as described in
        :func:`setQrange`.

        Returns
        -------
        q_range: tuple
            A tuple with 2 indices, the start and end of the selected
            q range, such that q[start:end] returns the desired q range.
        """
        return self._selected_q_range

    def setAllParameters(self, new_parameters):
        """
        Sets the parameters dictionary, which contains the profile metadata,
        to the new input value.

        Parameters
        ----------
        new_parameters: dict
            A dictionary containing the new parameters.
        """
        self._parameters = new_parameters

    def getAllParameters(self):
        """
        Returns all of the metadata parameters associated with the profile as
        a dictionary.

        Returns
        -------
        parameters: dict
            The metadata associated with the profile.
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

    def removeParameter(self, key):
        """
        Removes a particular metadata parameter based on the provided key.

        Parameters
        ----------
        key: str
            A string that is a key in the parameters metadata dictionary.
        """
        del self._parameters[key]

    def removeZingers(self, start_idx = 0, window_length = 10, stds = 4.0):
        """
        Removes spikes (zingers) from radially averaged data based on smoothing
        of the intensity profile.

        Parameters
        ----------
        start_idx: int
            The initial index in the intensity to start the dezingering process.
        window_length: int
            The size of the window used to search for an replace spikes, as the
            number of intensity points.
        stds: The standard deviation threshold used to detect spikes.
        """

        intensity = self._i_raw

        for i in range(window_length + start_idx, len(intensity)):

            averaging_window = intensity[i - window_length : i]
            averaging_window_std = np.std(averaging_window)
            averging_window_mean = np.mean(averaging_window)

            threshold = averging_window_mean + (stds * averaging_window_std)

            if intensity[i] > threshold:
                intensity[i] = averging_window_mean

        self._update()

    def getRawQ(self):
        """
        Gets the raw q vector, without scaling based on the :func:`scaleQ` and
        without trimming based on :func:`setQrange`.

        Returns
        -------
        q_raw: numpy.array
            The raw q vector.
        """
        return self._q_raw

    def getRawI(self):
        """
        Gets the raw intensity vector, without scaling or offset from
        :func:`scale` and :func:`offset` and without trimming based on
        :func:`setQrange`.

        Returns
        -------
        i_raw: numpy.array
            The raw intensity vector.
        """
        return self._i_raw

    def getRawErr(self):
        """
        Gets the raw error vector, without scaling or offset from
        :func:`scale` and :func:`offset` and without trimming based on
        :func:`setQrange`.

        Returns
        -------
        err_raw: numpy.array
            The raw error vector.
        """
        return self._err_raw

    def getRawQErr(self):
        """
        Gets the raw q error vector, without scaling or offset from
        :func:`scale` and :func:`offset` and without trimming based on
        :func:`setQrange`.

        Returns
        -------
        q_err_raw: numpy.array
            The raw error vector.
        """
        return self._q_err_raw

    def setRawI(self, new_raw_i):
        """
        Sets the raw q vector. Will overwrite whatever q vector is already
        in the object! Typically only used during calibration.

        Parameters
        ----------
        new_raw_i: numpy.array
            The new intensity vector.
        """
        self._i_raw = new_raw_i

    def setRawQ(self, new_raw_q):
        """
        Sets the raw intensity vector. Will overwrite whatever intensity vector
        is already in the object! Typically only used during calibration.

        Parameters
        ----------
        new_raw_q: numpy.array
            The new q vector.
        """
        self._q_raw = new_raw_q

    def setRawErr(self, new_raw_err):
        """
        Sets the raw error vector. Will overwrite whatever error vector
        is already in the object! Typically only used during calibration.

        Parameters
        ----------
        new_raw_err: numpy.array
            The new error vector.
        """
        self._err_raw = new_raw_err

    def setRawQErr(self, new_raw_q_err):
        """
        Sets the raw q error vector. Will overwrite whatever error vector
        is already in the object! Typically only used during calibration.
        Q errors are typically only found in SANS data, and currently are
        only carried and written out with the data set, they are not used
        in any processing.

        Parameters
        ----------
        new_raw_err: numpy.array
            The new error vector.
        """
        self._q_err_raw = new_raw_q_err

    def setScaleValues(self, scale_factor, offset_value, q_scale_factor):
        """
        A convenience method that lets you set the scale offset, and q scale
        values all at once.

        Parameters
        ----------
        scale_factor: float
            The scale factor to be applied to the the profile intensity and
            uncertainty.
        offset_value: float
            The offset to be applied to the profile intensity.
        q_scale_factor: float
            The scale factor to be applied to the profile q values.
        """
        self._scale_factor = scale_factor
        self._offset_value = offset_value
        self._q_scale_factor = q_scale_factor
        self._update()

    def scaleRawIntensity(self, scale):
        """
        Scales the raw intensity and error values. These are the intensity and
        error values without any scale applied. The raw scale factor is not
        tracked, so this cannot easily be undone, unlike the :func:scaleQ function.

        Parameters
        ----------
        scale: float
            The scale factor to be applied to the raw profile intensity and
            error values.
        """
        self._i_raw = self._i_raw * scale
        self._err_raw = self._err_raw * scale
        self._update()

    def offsetRawIntensity(self, offset):
        """
        Offsets the raw intensity and error values. These are the intensity and
        error values without any offset applied. The raw offset factor is not
        tracked, so this cannot easily be undone, unlike the :func:scaleQ function.

        Parameters
        ----------
        offset: float
            The offset to be applied to the raw profile intensity and error
            values.
        """
        self._i_raw = self._i_raw + offset
        self._err_raw = self._err_raw
        self._update()

    def extractAll(self):
        """
        Extracts the raw and scaled q, intensity, and error, the scale and
        offset values, the selected q range, and the parameters in a single
        dictionary.

        Returns
        -------
        all_data: dict
            A dictionary with keys q_raw, i_raw, err_raw, q, i, err, scale_factor,
            offset_value, q_scale_factor, selected_qrange, and parameters, which
            correspond to those values from the SASM.
        """

        all_data = {}

        all_data['i_raw'] = self._i_raw
        all_data['q_raw'] = self._q_raw
        all_data['err_raw'] = self._err_raw
        all_data['q_err_raw'] = self._q_err_raw

        all_data['i'] = self.getI()
        all_data['q'] = self.getQ()
        all_data['err'] = self.getErr()
        all_data['q_err'] = self.getQErr()

        all_data['scale_factor'] = self._scale_factor
        all_data['offset_value'] = self._offset_value
        all_data['q_scale_factor'] = self._q_scale_factor

        all_data['selected_qrange'] = self._selected_q_range

        all_data['parameters'] = self._parameters

        return all_data

    def copy(self):
        """
        Creates a copy of the SASM, without scale information, using, for
        example, the scaled, trimmed intensity as the raw intensity for
        the new SASM.

        The preferred method of copying a profile is to use copy.deepcopy on
        the profile.

        Returns
        -------
        profile: bioxtasraw.SASM.SASM
            The copied profile
        """

        sasm = SASM(copy.deepcopy(self.i), copy.deepcopy(self.q),
            copy.deepcopy(self.err), copy.deepcopy(self._parameters))
        sasm.setRawQErr(self._q_err_raw)

        return sasm

    def getMeanI(self):
        """
        Gets the mean intensity of the intensity vector.

        Returns
        -------
        mean_intensity: float
            The mean intensity.
        """
        return self.mean_intensity

    def getTotalI(self):
        """
        Gets the total integrated intensity of the intensity vector.

        Returns
        -------
        total_intensity: float
            The total intensity.
        """
        return self.total_intensity

    def getIofQ(self, qref):
        """
        Gets the intensity at a specific q value (or the closest such value in
        the q vector).

        Parameters
        ----------
        qref: float
            The reference q to get the intensity at.

        Returns
        -------
        intensity: float
            The intensity at the q point nearest the provided qref.
        """
        q = self.getQ()
        index = self.closest(q, qref)
        i = self.getI()
        intensity = i[index]

        return intensity

    def getIofQRange(self, q1, q2):
        """
        Gets the total integrated intensity in the q range from q1 to q2 (or
        the closest such values in the q vector).

        Parameters
        ----------
        q1: float
            The starting q value in the q range
        q2: float
            The ending q value in the q range.

        Returns
        -------
        total_intensity: float
            The total intensity.
        """
        q = self.getQ()
        index1 = self.closest(q, q1)
        index2 = self.closest(q, q2)
        i = self.getI()

        return integrate.trapz(i[index1:index2+1], q[index1:index2+1])

    @staticmethod
    def closest(qlist, q):
        """
        A convenience function which returns the index of the nearest
        q point in qlist to the input q value.

        Parameters
        ----------
        qlist: np.array
            The q list to search in.
        q: float
            The q value to search for in the qlist.

        Returns
        -------
        index: int
            The index of the q value in qlist closest to the input q.
        """
        return np.argmin(np.absolute(qlist-q))

    def getQ(self):
        """
        Gets the scaled, offset, trimmed q vector. Usually this is what you
        want to use to the get the q vector.
        """
        return self.q[self._selected_q_range[0]:self._selected_q_range[1]]

    def getI(self):
        """
        Gets the scaled, offset, trimmed intensity vector. Usually this is what
        you want to use to the get the intensity vector.
        """
        return self.i[self._selected_q_range[0]:self._selected_q_range[1]]

    def getErr(self):
        """
        Gets the scaled, offset, trimmed error vector. Usually this is what you
        want to use to the get the error vector.
        """
        return self.err[self._selected_q_range[0]:self._selected_q_range[1]]

    def getQErr(self):
        """
        Gets the scaled, offset, trimmed q error vector. Usually this is what you
        want to use to the get the q error vector. Q errors are usually only
        available with SANS data. Returns None if no q error has been defined.
        """

        if self.q_err is not None:
            q_err = self.q_err[self._selected_q_range[0]:self._selected_q_range[1]]
        else:
            q_err = None

        return q_err


class IFTM(object):
    """
    Inverse Fourier transform measurement (IFTM) object. Contains the P(r), r
    and error vectors, as well as the original data, the fit of the P(r) to
    the data, and all associated metadata.

    Attributes
    ----------
    r: numpy.array
        The r vector of the P(r) function.
    p: numpy.array
        The values of the P(r) function.
    err: numpy.array
        The errors of the P(r) function.
    q_orig: numpy.array
        The q vector of the input data.
    i_orig: numpy.array
        The intensity vector of the input data.
    err_orig: numpy.array
        The error vector of the input data.
    i_fit: numpy.array
        The intensity vector of the fit to the input data.
    q_extrap: numpy.array
        The q vector of the input data extrapolated to q=0.
    i_extrap: numpy.array
        The intensity vector of the fit to the input data extrapolated to q=0.
    """

    def __init__(self, p, r, err, i_orig, q_orig, err_orig, i_fit, parameters, i_extrap = [], q_extrap = []):
        """
        Constructor

        Parameters
        ----------
        p: numpy.array
            The input P(r) values.
        r:  numpy.array
            The input r values for the P(r) function.
        err: numpy.array
            The input error values for the P(r) function.
        i_orig: numpy.array
            The intensity values of the data used to do the IFT.
        q_orig: numpy.array
            The q values of the data used to do the IFT.
        err_orig: numpy.array
            The error values of the data used to do the IFT.
        i_fit: numpy.array
            The intensity values of the fit of the P(r) function to the data.
        parameters: dict
            A dictionary of the metadata. Should ontain at least {'filename':
            filename_with_no_path}
        i_extrap: numpy.array, optional
            The intensity values of the fit of the P(r) function to the data
            extrapolated to q=0. If not provided, an empty array is used.
        q_extrap: numpy.array, optional
            The q values of the input data extrapolated to q=0. If not
            provided, an empty array is used.
        """

        #Raw intensity variables
        self._r_raw = np.array(r)
        self._p_raw = np.array(p)
        self._err_raw = np.array(err)
        self._i_orig_raw = np.array(i_orig)
        self._q_orig_raw = np.array(q_orig)
        self._err_orig_raw = np.array(err_orig)
        self._i_fit_raw = np.array(i_fit)
        self._i_extrap_raw = np.array(i_extrap)
        self._q_extrap_raw = np.array(q_extrap)
        self._parameters = parameters

        # Make an entry for analysis parameters i.e. Rg, I(0) etc:
        # if 'analysis' not in self._parameters:
        #     self._parameters['analysis'] = {}
        # if 'history' not in self._parameters:
        #     self._parameters['history'] = {}

        #Modified intensity variables
        self.r = self._r_raw.copy()
        self.p = self._p_raw.copy()
        self.err = self._err_raw.copy()

        self.i_orig = self._i_orig_raw.copy()
        self.q_orig = self._q_orig_raw.copy()
        self.err_orig = self._err_orig_raw.copy()

        self.i_fit = self._i_fit_raw.copy()

        self.i_extrap = self._i_extrap_raw.copy()
        self.q_extrap = self._q_extrap_raw.copy()

        #variables used for plot management
        self.item_panel = None

        self.plot_panel = None

        self.r_line = None
        self.qo_line = None
        self.qf_line = None

        self.r_origline = None
        self.qo_origline = None
        self.qf_origline = None

        self.r_err_line = None
        self.qo_err_line = None

        self.r_axes = None
        self.qo_axes = None
        self.qf_axes = None

        self.canvas = None

        self.is_plotted = False

    def __deepcopy__(self, memo):
        p = copy.deepcopy(self._p_raw, memo)
        r = copy.deepcopy(self._r_raw, memo)
        err = copy.deepcopy(self._err_raw, memo)

        i_orig = copy.deepcopy(self._i_orig_raw, memo)
        q_orig = copy.deepcopy(self._q_orig_raw, memo)
        err_orig = copy.deepcopy(self._err_orig_raw, memo)

        i_fit = copy.deepcopy(self._i_fit_raw, memo)

        i_extrap = copy.deepcopy(self._i_extrap_raw, memo)
        q_extrap = copy.deepcopy(self._q_extrap_raw, memo)

        parameters = copy.deepcopy(self._parameters, memo)

        new_iftm = IFTM(p, r, err, i_orig, q_orig, err_orig, i_fit, parameters,
            i_extrap, q_extrap)

        return new_iftm

    def getScale(self):
        """
        Returns the scale factor for the P(r) function.

        Returns
        -------
        scale: float
            The scale factor.
        """
        return self._scale_factor

    def getOffset(self):
        """
        Returns the offset for the P(r) function.

        Returns
        -------
        offset: float
            The offset.
        """
        return self._offset_value

    def getLine(self):
        """
        Returns the plotted line for the P(r) function. Only used in the RAW GUI.

        Returns
        -------
        line: matplotlib.lines.Line2D
            The plotted line.
        """
        return self.line

    def setAllParameters(self, new_parameters):
        """
        Sets the parameters dictionary, which contains the IFT metadata,
        to the new input value.

        Parameters
        ----------
        new_parameters: dict
            A dictionary containing the new parameters.
        """
        self._parameters = new_parameters

    def getAllParameters(self):
        """
        Returns all of the metadata parameters associated with the IFT as
        a dictionary.

        Returns
        -------
        parameters: dict
            The metadata associated with the IFT.
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

    def extractAll(self):
        """
        Extracts the raw and scaled q, intensity, and error, the scale and
        offset values, the selected q range, and the parameters in a single
        dictionary.

        Returns
        -------
        all_data: dict
            A dictionary with keys r_raw, p_raw, err_raw, i_orig_raw, q_orig_raw,
            err_orig_raw, i_fit_raw, i_extrap_raw, q_extrap_raw, and parameters,
            which correspond to those values from the IFTM.
        """

        all_data = {}

        all_data['r_raw'] = self._r_raw
        all_data['p_raw'] = self._p_raw
        all_data['err_raw'] = self._err_raw

        all_data['i_orig_raw'] = self._i_orig_raw
        all_data['q_orig_raw'] = self._q_orig_raw
        all_data['err_orig_raw'] = self._err_orig_raw

        all_data['i_fit_raw'] = self._i_fit_raw
        all_data['i_extrap_raw'] = self._i_extrap_raw
        all_data['q_extrap_raw'] = self._q_extrap_raw

        all_data['parameters'] = self._parameters

        return all_data

        pass

    def copy(self):
        """
        Creates a copy of the IFT.

        Returns
        -------
        ift: bioxtasraw.SASM.IFTM
            The copied IFTM
        """

        iftm_copy = IFTM(copy.deepcopy(self._p_raw), copy.deepcopy(self._r_raw),
            copy.deepcopy(self._err_raw), copy.deepcopy(self._i_orig_raw),
            copy.deepcopy(self._q_orig_raw), copy.deepcopy(self._err_orig_raw),
            copy.deepcopy(self._i_fit_raw), copy.deepcopy(self._parameters),
            copy.deepcopy(self._i_extrap_raw), copy.deepcopy(self._q_extrap_raw))

        return iftm_copy


def postProcessSasm(sasm, raw_settings):

    if raw_settings.get('ZingerRemoval'):
        std = raw_settings.get('ZingerRemoveSTD')
        winlen = raw_settings.get('ZingerRemoveWinLen')
        start_idx = raw_settings.get('ZingerRemoveIdx')

        sasm.removeZingers(start_idx, winlen, std)
