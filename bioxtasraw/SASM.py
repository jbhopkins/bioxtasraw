'''
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
'''
from __future__ import absolute_import, division, print_function, unicode_literals
from builtins import object, range, map, zip
from io import open

import copy

import numpy as np
from scipy import integrate as integrate

try:
    import SASExceptions
except Exception:
    from . import SASExceptions


class SASM(object):
    '''
        Small Angle Scattering Measurement (SASM) Object.
        Contains all information extracted from a SAS data file.
    '''

    def __init__(self, i, q, err, parameters):
        ''' Constructor

            parameters contains at least {'filename': filename_with_no_path}
            other reserved keys are:

            'counters' : [(countername, value),...] Info from counterfiles
            'fileHeader' : [(label, value),...] Info from the header in the loaded file
        '''

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

        #Modified intensity variables
        self.i = self._i_raw.copy()
        self.q = self._q_raw.copy()
        self.err = self._err_raw.copy()

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

        newsasm.scale(copy.deepcopy(self.getScale(), memo))
        newsasm.offset(copy.deepcopy(self.getOffset(), memo))
        newsasm._q_scale_factor = copy.deepcopy(self._q_scale_factor, memo)

        newsasm._update()

        return newsasm

    def _update(self):
        ''' updates modified intensity after scale, normalization and offset changes '''

        self.i = (self._i_raw * self._scale_factor) + self._offset_value
        self.err = self._err_raw * abs(self._scale_factor)
        self.q = self._q_raw * self._q_scale_factor

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
        return self._scale_factor

    def getOffset(self):
        return self._offset_value

    def getLine(self):
        return self.line

    def scaleRelative(self, relscale):
        self._scale_factor = abs(self._scale_factor * relscale)
        self._update()

    def scale(self, scale_factor):
        ''' Scale intensity by a factor from the raw intensity, also scales errorbars appropiately '''

        self._scale_factor = abs(scale_factor)
        self._update()

    def offset(self, offset_value):
        ''' Offset raw intensity by a constant. Only modified intensity is affected '''

        self._offset_value = offset_value
        self._update()

    def scaleRawQ(self, scale_factor):
        self._q_raw = self._q_raw * scale_factor
        self._update()

    def scaleQ(self, q_scale_factor):
        ''' scale Q values by a factor (calibrate) '''

        self._q_scale_factor = q_scale_factor
        self._update()

    def reset(self):
        ''' Reset q, i and err to their original values '''

        self.i = self._i_raw.copy()
        self.q = self._q_raw.copy()
        self.err = self._err_raw.copy()

        self._scale_factor = 1
        self._offset_value = 0
        self._q_scale_factor = 1

    def setQrange(self, qrange):
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
        return self._selected_q_range

    def setAllParameters(self, new_parameters):
        self._parameters = new_parameters

    def getAllParameters(self):
        return self._parameters

    def getParameter(self, key):
        ''' Get parameter from parameters dict '''

        if key in self._parameters:
            return self._parameters[key]
        else:
            return None

    def setParameter(self, key, value):
        ''' insert key,value pair into parameters dict '''
        self._parameters[key] = value

    def removeZingers(self, start_idx = 0, window_length = 10, stds = 4.0):
        ''' Removes spikes from the radial averaged data
            Threshold is currently 4 times the standard deviation (stds)

            window_length :     The number of points before the spike
                                that are averaged and used to replace the spike.

            start_idx :         Index in the intensityArray to start the search for spikes

        '''

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
        return self._q_raw

    def getRawI(self):
        return self._i_raw

    def getRawErr(self):
        return self._err_raw

    def setRawI(self, new_raw_i):
        self._i_raw = new_raw_i

    def setRawQ(self, new_raw_q):
        self._q_raw = new_raw_q

    def setRawErr(self, new_raw_err):
        self._err_raw = new_raw_err

    def setScaleValues(self, scale_factor, offset_value, q_scale_factor):

        self._scale_factor = scale_factor
        self._offset_value = offset_value
        self._q_scale_factor = q_scale_factor
        self._update()

    def scaleRawIntensity(self, scale):
        self._i_raw = self._i_raw * scale
        self._err_raw = self._err_raw * scale
        self._update()

    def offsetRawIntensity(self, offset):
        self._i_raw = self._i_raw + offset
        self._err_raw = self._err_raw
        self._update()

    def extractAll(self):
        ''' extracts all data from the object and delivers it as a dict '''

        all_data = {}

        all_data['i_raw'] = self._i_raw
        all_data['q_raw'] = self._q_raw
        all_data['err_raw'] = self._err_raw

        all_data['i'] = self.getI()
        all_data['q'] = self.getQ()
        all_data['err'] = self.getErr()

        all_data['scale_factor'] = self._scale_factor
        all_data['offset_value'] = self._offset_value
        all_data['q_scale_factor'] = self._q_scale_factor

        all_data['selected_qrange'] = self._selected_q_range

        all_data['parameters'] = self._parameters

        return all_data

    def copy(self):
        ''' return a copy of the object '''

        return SASM(copy.copy(self.i), copy.copy(self.q), copy.copy(self.err), copy.copy(self._parameters))

    def getMeanI(self):
        return self.mean_intensity

    def getTotalI(self):
        return self.total_intensity

    def getIofQ(self, qref):
        q = self.getQ()
        index = self.closest(q, qref)
        i = self.getI()
        intensity = i[index]

        return intensity

    def getIofQRange(self, q1, q2):
        q = self.getQ()
        index1 = self.closest(q, q1)
        index2 = self.closest(q, q2)
        i = self.getI()

        return integrate.trapz(i[index1:index2+1], q[index1:index2+1])

    def closest(self, qlist, q):
        return np.argmin(np.absolute(qlist-q))

    def getQ(self):
        return self.q[self._selected_q_range[0]:self._selected_q_range[1]]

    def getI(self):
        return self.i[self._selected_q_range[0]:self._selected_q_range[1]]

    def getErr(self):
        return self.err[self._selected_q_range[0]:self._selected_q_range[1]]


class IFTM(object):
    '''
        Inverse fourier tranform measurement (IFTM) Object.
        Contains all information extracted from a IFT.
    '''

    def __init__(self, p, r, err, i_orig, q_orig, err_orig, i_fit, parameters, i_extrap = [], q_extrap = []):
        ''' Constructor

            parameters contains at least {'filename': filename_with_no_path}
            other reserved keys are:

            'counters' : [(countername, value),...] Info from counterfiles
            'fileHeader' : [(label, value),...] Info from the header in the loaded file
        '''

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


        # self._scale_factor = 1
        # self._offset_value = 0
        # self._q_scale_factor = 1
        # self._bin_size = 1

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
        self._selected_q_range = (0, len(self._q_orig_raw))


    def _update(self):
        ''' updates modified intensity after scale, normalization and offset changes '''

        self.i = (self._i_raw * self._scale_factor) + self._offset_value
        self.err = self._err_raw * abs(self._scale_factor)
        self.q = self._q_raw * self._q_scale_factor

    def getScale(self):
        return self._scale_factor

    def getOffset(self):
        return self._offset_value

    def getLine(self):
        return self.line

    def scaleRelative(self, relscale):
        self._scale_factor = abs(self._scale_factor * relscale)
        self._update()

    def scale(self, scale_factor):
        ''' Scale intensity by a factor from the raw intensity, also scales errorbars appropiately '''

        self._scale_factor = abs(scale_factor)
        self._update()

    def offset(self, offset_value):
        ''' Offset raw intensity by a constant. Only modified intensity is affected '''

        self._offset_value = offset_value
        self._update()

    def reset(self):
        # ''' Reset q, i and err to their original values '''
        pass

    def setQrange(self, qrange):

        if qrange[0] < 0 or qrange[1] > (len(self._q_orig_raw)):
            raise SASExceptions.InvalidQrange('Qrange: ' + str(qrange) + ' is not a valid q-range for a q-vector of length ' + str(len(self._q_orig_raw)-1))
        else:
            self._selected_q_range = list(map(int, qrange))

    def getQrange(self):
        return self._selected_q_range

    def setAllParameters(self, new_parameters):
        self._parameters = new_parameters

    def getAllParameters(self):
        return self._parameters

    def getParameter(self, key):
        ''' Get parameter from parameters dict '''

        if key in self._parameters:
            return self._parameters[key]
        else:
            return None

    def setParameter(self, key, value):
        ''' insert key,value pair into parameters dict '''
        self._parameters[key] = value


    def setScaleValues(self, scale_factor, offset_value, q_scale_factor, bin_size):

        self._scale_factor = scale_factor
        self._offset_value = offset_value
        self._q_scale_factor = q_scale_factor
        self._bin_size = bin_size

    def extractAll(self):
        ''' extracts all data from the object and delivers it as a dict '''

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

        all_data['selected_qrange'] = self._selected_q_range

        all_data['parameters'] = self._parameters

        return all_data

        pass

    def copy(self):
        ''' return a copy of the object '''

        iftm_copy = IFTM(copy.copy(self._p_raw), copy.copy(self._r_raw),
            copy(self._err_raw), copy.copy(self._i_orig_raw),
            copy.copy(self._q_orig_raw), copy.copy(self._err_orig_raw),
            copy.copy(self._i_fit_raw), copy.deepcopy(self._parameters),
            copy.copy(self._i_extrap_raw), copy.copy(self._q_extrap_raw))

        return iftm_copy


def postProcessSasm(sasm, raw_settings):

    if raw_settings.get('ZingerRemoval'):
        std = raw_settings.get('ZingerRemoveSTD')
        winlen = raw_settings.get('ZingerRemoveWinLen')
        start_idx = raw_settings.get('ZingerRemoveIdx')

        sasm.removeZingers(start_idx, winlen, std)
