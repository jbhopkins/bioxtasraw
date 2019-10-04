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
import os
import copy
import threading
from math import pi, sin
import itertools

import numpy as np
from scipy import integrate as integrate

import SASCalib
import SASExceptions
import SASCalc
import SASProc


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

        #Binned intensity variables
        self._i_binned = self._i_raw.copy()
        self._q_binned = self._q_raw.copy()
        self._err_binned = self._err_raw.copy()

        #Modified intensity variables
        self.i = self._i_raw.copy()
        self.q = self._q_raw.copy()
        self.err = self._err_raw.copy()

        self._scale_factor = 1
        self._offset_value = 0
        self._norm_factor = 1
        self._q_scale_factor = 1
        self._bin_size = 1

        #variables used for plot management
        self.item_panel = None
        self.plot_panel = None
        self.line = None
        self.err_line = None
        self.axes = None
        self.is_plotted = False
        self._selected_q_range = (0, len(self._q_binned))


        #Calculated values
        try:
            if len(self.q)>0:
                self.total_intensity = integrate.trapz(self.getI(), self.getQ())
                self.mean_intensity = self.getI().mean()
            else:
                self.total_intensity = -1
                self.mean_intensity = -1

        except Exception as e:
            print e
            self.total_intensity = -1
            self.mean_intensity = -1

    def __deepcopy__(self, memo):
        #Raw intensity variables
        i_raw = copy.deepcopy(self._i_raw, memo)
        q_raw = copy.deepcopy(self._q_raw, memo)
        err_raw = copy.deepcopy(self._err_raw, memo)
        parameters = copy.deepcopy(self._parameters, memo)

        newsasm = SASM(i_raw, q_raw, err_raw, parameters)

        #Binned intensity variables
        newsasm.setQrange(copy.deepcopy(self.getQrange(), memo))

        newsasm.scale(copy.deepcopy(self.getScale(), memo))
        newsasm.normalize(copy.deepcopy(self._norm_factor, memo))
        newsasm.offset(copy.deepcopy(self.getOffset(), memo))
        newsasm._q_scale_factor = copy.deepcopy(self._q_scale_factor, memo)
        newsasm._bin_size = copy.deepcopy(self.getBinning(), memo)

        newsasm.setBinnedI(copy.deepcopy(self.getBinnedI(), memo))
        newsasm.setBinnedQ(copy.deepcopy(self.getBinnedQ(), memo))
        newsasm.setBinnedErr(copy.deepcopy(self.getBinnedErr(), memo))

        newsasm._update()

        return newsasm

    def _update(self):
        ''' updates modified intensity after scale, normalization and offset changes '''

        #self.i = ((self._i_binned / self._norm_factor) + self._offset_value) * self._scale_factor
        self.i = ((self._i_binned / self._norm_factor) * self._scale_factor) + self._offset_value

        #self.err = ((self._err_binned / self._norm_factor) + self._offset_value) * abs(self._scale_factor)
        self.err = ((self._err_binned / self._norm_factor)) * abs(self._scale_factor)

        self.q = self._q_binned * self._q_scale_factor

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
            barlinecols[0].set_segments(zip(zip(x,y-yerr), zip(x,y+yerr)))

        #Calculated values
        try:
            if len(self.q)>0:
                self.total_intensity = integrate.trapz(self.getI(), self.getQ())
                self.mean_intensity = self.getI().mean()
            else:
                self.total_intensity = -1
                self.mean_intensity = -1

        except Exception as e:
            print e
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

    def normalize(self, norm_value):
        ''' Normalize (divide) raw intensity by a value, errorbars follow '''

        self._norm_factor = norm_value
        self._update()

    def offset(self, offset_value):
        ''' Offset raw intensity by a constant. Only modified intensity is affected '''

        self._offset_value = offset_value
        self._update()

    def scaleBinnedQ(self, scale_factor):
        self._q_binned = self._q_binned * scale_factor
        self._update()

    def scaleQ(self, q_scale_factor):
        ''' scale Q values by a factor (calibrate) '''

        self._q_scale_factor = q_scale_factor
        self._update()

    def calibrateQ(self, sd_distance, delta_q_length, wavelength):
        ''' calibrates the q_vector from the sample-detector
        distance sd_distance. Going from a q-vector in pixels
        to inverse angstroms via delta_q_length (ex. detector pixel size)'''

        for q_idx in range(0,len(self._q_binned)):
            q_vector = self._q_binned[q_idx]
            theta = SASCalib.calcTheta(sd_distance, delta_q_length, q_vector)

            self._q_binned[q_idx] = ((4 * pi * sin(theta)) / wavelength)

        self._update()

    def reset(self):
        ''' Reset q, i and err to their original values '''

        self.i = self._i_raw.copy()
        self.q = self._q_raw.copy()
        self.err = self._err_raw.copy()

        self._i_binned = self._i_raw.copy()
        self._q_binned = self._q_raw.copy()
        self._err_binned = self._err_raw.copy()

        self._scale_factor = 1
        self._offset_value = 0
        self._norm_factor = 1
        self._q_scale_factor = 1

    def setQrange(self, qrange):
        if qrange[0] < 0 or qrange[1] > (len(self._q_binned)):
            raise SASExceptions.InvalidQrange('Qrange: ' + str(qrange) + ' is not a valid q-range for a q-vector of length ' + str(len(self._q_binned)-1))
        else:
            self._selected_q_range = map(int, qrange)

            try:
                if len(self.q)>0:
                    self.total_intensity = integrate.trapz(self.getI(), self.getQ())
                    self.mean_intensity = self.getI().mean()
                else:
                    self.total_intensity = -1
                    self.mean_intensity = -1

            except Exception as e:
                print e
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

        if self._parameters.has_key(key):
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

        intensity = self._i_binned

        for i in range(window_length + start_idx, len(intensity)):

            averaging_window = intensity[i - window_length : i]
            averaging_window_std = np.std(averaging_window)
            averging_window_mean = np.mean(averaging_window)

            threshold = averging_window_mean + (stds * averaging_window_std)

            if intensity[i] > threshold:
                intensity[i] = averging_window_mean

        self._update()

#	def logRebin(self, no_points, start_idx = 0, end_idx = -1):
#		pass

	def setLogBinning(self, no_points, start_idx = 0, end_idx = -1):

		if end_idx == -1:
			end_idx = len(self._i_raw)

		i = self._i_raw[start_idx:end_idx]
		q = self._q_raw[start_idx:end_idx]
		err = self._err_raw[start_idx:end_idx]

		bins = np.logspace(1, np.log10(len(q)), no_points)

		binned_q = []
		binned_i = []
		binned_err = []

		idx = 0
		for i in range(0, len(bins)):
			no_of_bins = np.floor(bins[i] - bins[i-1])

			if no_of_bins > 1:
				mean_q = np.mean( q[ idx : idx + no_of_bins ] )
				mean_i = np.mean( i[ idx : idx + no_of_bins ] )

				mean_err = np.sqrt( sum( np.power( err[ idx : idx + no_of_bins ], 2) ) ) / np.sqrt( no_of_bins )

				binned_q.append(mean_q)
				binned_i.append(mean_i)
				binned_err.append(mean_err)

				idx = idx + no_of_bins
			else:
				binned_q.append(q[idx])
				binned_i.append(i[idx])
				binned_err.append(err[idx])
				idx = idx + 1

		self._i_binned = np.array(binned_i)
		self._q_binned = np.array(binned_q)
		self._err_binned = np.array(binned_err)

		self._update()
        self._selected_q_range = (0, len(self._i_binned))


    def setBinning(self, bin_size, start_idx = 0, end_idx = -1):
        ''' Sets the bin size of the I_q plot

            end_idx will be lowered to fit the bin_size
            if needed.
        '''

        self._bin_size = bin_size

        if end_idx == -1:
            end_idx = len(self._i_raw)

        len_iq = len(self._i_raw[start_idx:end_idx])

        no_of_bins = int(np.floor(len_iq / bin_size))
        end_idx = start_idx + no_of_bins*bin_size

        i_roi = self._i_raw[start_idx:end_idx]
        q_roi = self._q_raw[start_idx:end_idx]
        err_roi = self._err_raw[start_idx:]

        new_i = np.zeros(no_of_bins)
        new_q = np.zeros(no_of_bins)
        new_err = np.zeros(no_of_bins)

        for eachbin in range(0, no_of_bins):
            first_idx = eachbin * bin_size
            last_idx = (eachbin * bin_size) + bin_size

            new_i[eachbin] = sum(i_roi[first_idx:last_idx]) / bin_size
            new_q[eachbin] = sum(q_roi[first_idx:last_idx]) / bin_size
            new_err[eachbin] = np.sqrt(sum(np.power(err_roi[first_idx:last_idx],2))) / np.sqrt(bin_size)

        if end_idx == -1 or end_idx == len(self._i_raw):
            self._i_binned = np.append(self._i_raw[0:start_idx], new_i)
            self._q_binned = np.append(self._q_raw[0:start_idx], new_q)
            self._err_binned = np.append(self._err_raw[0:start_idx], new_err)
        else:
            self._i_binned = np.append(np.append(self._i_raw[0:start_idx], new_i), self._i_raw[end_idx:])
            self._q_binned = np.append(np.append(self._q_raw[0:start_idx], new_q), self._q_raw[end_idx:])
            self._err_binned = np.append(np.append(self._err_raw[0:start_idx], new_err), self._err_raw[end_idx:])

        self._update()
        self._selected_q_range = (0, len(self._i_binned))

    def getBinning(self):
        return self._bin_size

    def getBinnedQ(self):
        return self._q_binned

    def getBinnedI(self):
        return self._i_binned

    def getBinnedErr(self):
        return self._err_binned

    def setBinnedI(self, new_binned_i):
        self._i_binned = new_binned_i

    def setBinnedQ(self, new_binned_q):
        self._q_binned = new_binned_q

    def setBinnedErr(self, new_binned_err):
        self._err_binned = new_binned_err

    def setScaleValues(self, scale_factor, offset_value, norm_factor, q_scale_factor, bin_size):

        self._scale_factor = scale_factor
        self._offset_value = offset_value
        self._norm_factor = norm_factor
        self._q_scale_factor = q_scale_factor
        self._bin_size = bin_size

    def scaleRawIntensity(self, scale):
        self._i_raw = self._i_raw * scale
        self._err_raw = self._err_raw * scale

    def scaleBinnedIntensity(self, scale):
        self._i_binned = self._i_binned * scale
        self._err_binned = self._err_binned * scale
        self._update()

    def offsetBinnedIntensity(self, offset):
        self._i_binned = self._i_binned + offset
        self._err_binned = self._err_binned
        self._update()

    def extractAll(self):
        ''' extracts all data from the object and delivers it as a dict '''

        all_data = {}

        all_data['i_raw'] = self._i_raw
        all_data['q_raw'] = self._q_raw
        all_data['err_raw'] = self._err_raw
        all_data['i_binned'] = self._i_binned
        all_data['q_binned'] = self._q_binned
        all_data['err_binned'] = self._err_binned

        all_data['scale_factor'] = self._scale_factor
        all_data['offset_value'] = self._offset_value
        all_data['norm_factor'] = self._norm_factor
        all_data['q_scale_factor'] = self._q_scale_factor
        all_data['bin_size'] = self._bin_size

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


class IFTM(SASM):
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

        #Binned intensity variables
        self._i_orig_binned = self._i_orig_raw.copy()
        self._q_orig_binned = self._q_orig_raw.copy()
        self._err_orig_binned = self._err_orig_raw.copy()
        self._i_fit_binned = self._i_fit_raw.copy()
        self._i_extrap_binned = self._i_extrap_raw.copy()
        self._q_extrap_binned = self._q_extrap_raw.copy()

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
        # self._norm_factor = 1
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
        self._selected_q_range = (0, len(self._q_orig_binned))


    def _update(self):
        ''' updates modified intensity after scale, normalization and offset changes '''

        #self.i = ((self._i_binned / self._norm_factor) + self._offset_value) * self._scale_factor
        self.i = ((self._i_binned / self._norm_factor) * self._scale_factor) + self._offset_value

        #self.err = ((self._err_binned / self._norm_factor) + self._offset_value) * abs(self._scale_factor)
        self.err = ((self._err_binned / self._norm_factor)) * abs(self._scale_factor)

        self.q = self._q_binned * self._q_scale_factor

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

    def normalize(self, norm_value):
        ''' Normalize (divide) raw intensity by a value, errorbars follow '''

        self._norm_factor = norm_value
        self._update()

    def offset(self, offset_value):
        ''' Offset raw intensity by a constant. Only modified intensity is affected '''

        self._offset_value = offset_value
        self._update()

    def reset(self):
        # ''' Reset q, i and err to their original values '''

        # self.i = self._i_raw.copy()
        # self.q = self._q_raw.copy()
        # self.err = self._err_raw.copy()

        # self._i_binned = self._i_raw.copy()
        # self._q_binned = self._q_raw.copy()
        # self._err_binned = self._err_raw.copy()

        # self._scale_factor = 1
        # self._offset_value = 0
        # self._norm_factor = 1
        # self._q_scale_factor = 1

        pass

    def setQrange(self, qrange):

        if qrange[0] < 0 or qrange[1] > (len(self._q_orig_binned)):
            raise SASExceptions.InvalidQrange('Qrange: ' + str(qrange) + ' is not a valid q-range for a q-vector of length ' + str(len(self._q_orig_binned)-1))
        else:
            self._selected_q_range = map(int, qrange)
            print self._selected_q_range

    def getQrange(self):
        return self._selected_q_range

    def setAllParameters(self, new_parameters):
        self._parameters = new_parameters

    def getAllParameters(self):
        return self._parameters

    def getParameter(self, key):
        ''' Get parameter from parameters dict '''

        if self._parameters.has_key(key):
            return self._parameters[key]
        else:
            return None

    def setParameter(self, key, value):
        ''' insert key,value pair into parameters dict '''
        self._parameters[key] = value


    def setScaleValues(self, scale_factor, offset_value, norm_factor, q_scale_factor, bin_size):

        self._scale_factor = scale_factor
        self._offset_value = offset_value
        self._norm_factor = norm_factor
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

        # all_data['i_binned'] = self._i_binned
        # all_data['q_binned'] = self._q_binned
        # all_data['err_binned'] = self._err_binned

        # all_data['scale_factor'] = self._scale_factor
        # all_data['offset_value'] = self._offset_value
        # all_data['norm_factor'] = self._norm_factor
        # all_data['q_scale_factor'] = self._q_scale_factor
        # all_data['bin_size'] = self._bin_size

        all_data['selected_qrange'] = self._selected_q_range

        all_data['parameters'] = self._parameters

        return all_data

        pass

    def copy(self):
        ''' return a copy of the object '''

        return SASM(copy.copy(self.i), copy.copy(self.q), copy.copy(self.err), copy.copy(self._parameters))


class SECM(object):
    '''
        SEC-SAS Measurement (SECM) Object.
    '''

    def __init__(self, file_list, sasm_list, frame_list, parameters, settings):
        ''' Constructor

            parameters contains at least {'filename': filename_with_no_path}
            other reserved keys are:

            'counters' : [(countername, value),...] Info from counterfiles
            'fileHeader' : [(label, value),...] Info from the header in the loaded file
        '''

        #Raw inputs variables
        self._file_list = file_list
        self._sasm_list = sasm_list
        self._frame_list_raw = np.array(frame_list, dtype=int)
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
        self._mean_i_raw = np.array([sasm.getMeanI() for sasm in self._sasm_list])
        self._total_i_raw = np.array([sasm.getTotalI() for sasm in self._sasm_list])

        #Set up the modified mean and total intensity variables
        self.mean_i = self._mean_i_raw.copy()
        self.total_i = self._total_i_raw.copy()

        #Make sure we have as many frame numbers as sasm objects

        if len(self._sasm_list) != len(self._frame_list_raw):
            self._frame_list_raw=np.arange(len(self._sasm_list))
            self._file_list=[sasm.getParameter('filename') for sasm in self._sasm_list]

        self.frame_list = self._frame_list_raw.copy()
        self.plot_frame_list = np.arange(len(self.frame_list))

        self._scale_factor = 1
        self._offset_value = 0
        self._frame_scale_factor = 1

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

        self.calcTime(self._sasm_list)

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

        self.mean_i = ((self.mean_i) * self._scale_factor) + self._offset_value
        self.total_i = ((self.total_i) * self._scale_factor) + self._offset_value
        self.I_of_q = ((self.I_of_q) * self._scale_factor) + self._offset_value
        self.qrange_I = ((self.qrange_I) * self._scale_factor) + self._offset_value

        self.mean_i_sub = ((self.mean_i_sub) * self._scale_factor) + self._offset_value
        self.total_i_sub = ((self.total_i_sub) * self._scale_factor) + self._offset_value
        self.I_of_q_sub = ((self.I_of_q_sub) * self._scale_factor) + self._offset_value
        self.qrange_I_sub = ((self.qrange_I_sub) * self._scale_factor) + self._offset_value

        self.mean_i_bcsub = ((self.mean_i_bcsub) * self._scale_factor) + self._offset_value
        self.total_i_bcsub = ((self.total_i_bcsub) * self._scale_factor) + self._offset_value
        self.I_of_q_bcsub = ((self.I_of_q_bcsub) * self._scale_factor) + self._offset_value
        self.qrange_I_sub = ((self.qrange_I_sub) * self._scale_factor) + self._offset_value

        self.plot_frame_list = self.plot_frame_list * self._frame_scale_factor


    def append(self, filename_list, sasm_list, frame_list):

        self._file_list.extend(filename_list)
        self._sasm_list.extend(sasm_list)
        self._frame_list_raw = np.concatenate((self._frame_list_raw, np.array(frame_list, dtype=int)))

        self._mean_i_raw = np.concatenate((self._mean_i_raw, np.array([sasm.getMeanI() for sasm in sasm_list])))
        self._total_i_raw = np.concatenate((self._total_i_raw, np.array([sasm.getTotalI() for sasm in sasm_list])))

        self.mean_i = self._mean_i_raw.copy()
        self.total_i = self._total_i_raw.copy()

        if len(self._sasm_list) != len(self._frame_list_raw):
            self._frame_list_raw=np.arange(len(self._sasm_list))
            print 'Warning: Incorrect frame number input to SECM object. Using default frame numbers.'

        self.frame_list = self._frame_list_raw.copy()

        self.calcTime(sasm_list)

        if self.qref>0:
            I_of_q = np.array([sasm.getIofQ(self.qref) for sasm in sasm_list])
            self.I_of_q = np.concatenate((self.I_of_q, I_of_q))

        if self.qrange != (0,0):
            qrange_I = np.array([sasm.getIofQRange(self.qrange[0], self.qrange[1]) for sasm in sasm_list])
            self.qrange_I = np.concatenate((self.qrange_I, qrange_I))

        # print self.time

        self.plot_frame_list = np.arange(len(self.frame_list))

        self._update()


    def getScale(self):
        return self._scale_factor

    def getOffset(self):
        return self._offset_value

    def getLine(self):
        return self.line

    def getCalcLine(self):
        return self.calc_line

    def getSASMList(self, initial_frame, final_frame, int_type='unsub'):
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
        if len(self.time)==0:
            return np.zeros_like(self.frame_list) - 1
        else:
            return self.time

    def calcTime(self, sasm_list):
        time=list(self.time)

        if self.hdr_format == 'G1, CHESS' or self.hdr_format == 'G1 WAXS, CHESS':
            for sasm in sasm_list:
                if sasm.getAllParameters().has_key('counters'):
                    file_hdr = sasm.getParameter('counters')

                    if '#C' not in file_hdr.values():
                        if file_hdr.has_key('Time'):
                            sasm_time = float(file_hdr['Time'])
                            time.append(sasm_time)

                        elif file_hdr.has_key('Seconds'):
                            sasm_time = float(file_hdr['Seconds'])
                            if len(time) == 0:
                                time.append(0)
                            else:
                                time.append(sasm_time+time[-1])

                        elif file_hdr.has_key('Exposure_time'):
                            sasm_time = float(file_hdr['Exposure_time'])
                            if len(time) == 0:
                                time.append(0)
                            else:
                                time.append(sasm_time+self.time[-1])

        elif self.hdr_format == 'BioCAT, APS':
            for sasm in sasm_list:
                if sasm.getAllParameters().has_key('counters'):
                    file_hdr = sasm.getParameter('counters')

                    if 'start_time' in file_hdr:
                        time.append(float(file_hdr['start_time']))

        self.time = np.array(time, dtype=float)

    def scaleRelative(self, relscale):
        self._scale_factor = abs(self._scale_factor * relscale)
        self._update()

    def scale(self, scale_factor):
        ''' Scale intensity by a factor from the raw intensity, also scales errorbars appropiately '''

        self._scale_factor = abs(scale_factor)
        self._update()

    def normalize(self, norm_value):
        ''' Normalize (divide) raw intensity by a value, errorbars follow '''

        self._norm_factor = norm_value
        self._update()

    def offset(self, offset_value):
        ''' Offset raw intensity by a constant. Only modified intensity is affected '''

        self._offset_value = offset_value
        self._update()

    def reset(self):
        ''' Reset q, i and err to their original values '''

        self.mean_i = self._mean_i_raw.copy()
        self.total_i = self._total_i_raw.copy()
        self.frame_list = self._frame_list_raw.copy()

        self._scale_factor = 1
        self._offset_value = 0
        self._frame_scale_factor = 1

    def setAllParameters(self, new_parameters):
        self._parameters = new_parameters

    def getAllParameters(self):
        return self._parameters

    def getParameter(self, key):
        ''' Get parameter from parameters dict '''

        if self._parameters.has_key(key):
            return self._parameters[key]
        else:
            return None

    def setParameter(self, key, value):
        ''' insert key,value pair into parameters dict '''

        self._parameters[key] = value

    def setScaleValues(self, scale_factor, offset_value, frame_scale_factor):

        self._scale_factor = scale_factor
        self._offset_value = offset_value
        self._frame_scale_factor = frame_scale_factor

    def extractAll(self):
        ''' extracts all data from the object and delivers it as a dict '''

        all_data = {}

        all_data['file_list'] = self._file_list
        all_data['mean_i_raw'] = self._mean_i_raw
        all_data['total_i_raw'] = self._total_i_raw
        all_data['frame_list_raw'] = self._frame_list_raw
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

        return all_data

    def __deepcopy__(self, memo):
        ''' return a copy of the object '''

        copy_secm = SECM(copy.deepcopy(self._file_list), copy.deepcopy(self._sasm_list),
            copy.deepcopy(self._frame_list_raw), copy.deepcopy(self._parameters), self._settings)

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

        return copy_secm

    def getSASM(self, index=0):
        return self._sasm_list[index]

    def I(self, qref):
        self.qref=float(qref)
        self.I_of_q = np.array([sasm.getIofQ(qref) for sasm in self.getAllSASMs()])

        if self.subtracted_sasm_list:
            self.I_of_q_sub = np.array([sasm.getIofQ(qref) for sasm in self.subtracted_sasm_list])

        if self.baseline_subtracted_sasm_list:
            self.I_of_q_bcsub = np.array([sasm.getIofQ(qref) for sasm in self.baseline_subtracted_sasm_list])

        return self.I_of_q

    def calc_qrange_I(self, qrange):
        self.qrange = qrange
        self.qrange_I = np.array([sasm.getIofQRange(qrange[0], qrange[1]) for sasm in self.getAllSASMs()])

        if self.subtracted_sasm_list:
            self.qrange_I_sub = np.array([sasm.getIofQRange(qrange[0], qrange[1]) for sasm in self.subtracted_sasm_list])

        if self.baseline_subtracted_sasm_list:
            self.qrange_I_bcsub = np.array([sasm.getIofQRange(qrange[0], qrange[1]) for sasm in self.baseline_subtracted_sasm_list])

        return self.qrange_I

    def getAllSASMs(self):
        return self._sasm_list

    def setRgAndI0(self, rg, rger, i0, i0er):
        self.rg_list = rg
        self.rger_list = rger
        self.i0_list = i0
        self.i0er_list = i0er

    def setMW(self, mw, mwer):
        self.mw_list = mw
        self.mwer_list = mwer

    def setCalcValues(self, rg, rger, i0, i0er, vcmw, vcmwer, vpmw):
        self.rg_list = rg
        self.rger_list = rger
        self.i0_list = i0
        self.i0er_list = i0er
        self.vpmw_list = vpmw
        self.vcmw_list = vcmw
        self.vcmwer_list = vcmwer

    def getRg(self):
        return self.rg_list, self.rger_list

    def getVcMW(self):
        return self.vcmw_list, self.vcmwer_list

    def getVpMW(self):
        return self.vpmw_list, np.zeros_like(self.vpmw_list)

    def getI0(self):
        return self.i0_list, self.i0er_list

    def getIntI(self):
        return self.total_i

    def getMeanI(self):
        return self.mean_i

    def getIofQ(self):
        return self.I_of_q

    def getIofQRange(self):
        return self.qrange_I

    def getFrames(self):
        return self.plot_frame_list

    def getIntISub(self):
        return self.total_i_sub

    def getMeanISub(self):
        return self.mean_i_sub

    def getIofQSub(self):
        return self.I_of_q_sub

    def getIofQRangeSub(self):
        return self.qrange_I_sub

    def getIntIBCSub(self):
        return self.total_i_bcsub

    def getMeanIBCSub(self):
        return self.mean_i_bcsub

    def getIofQRangeBCSub(self):
        return self.qrange_I_bcsub

    def appendCalcValues(self, rg, rger, i0, i0er, vcmw, vcmwer, vpmw,
        first_frame, window_size):
        index1 = first_frame+(window_size-1)/2
        index2 = (window_size-1)/2

        self.rg_list = np.concatenate((self.rg_list[:index1],rg[index2:]))
        self.rger_list = np.concatenate((self.rger_list[:index1],rger[index2:]))
        self.i0_list = np.concatenate((self.i0_list[:index1],i0[index2:]))
        self.i0er_list = np.concatenate((self.i0er_list[:index1],i0er[index2:]))
        self.vcmw_list = np.concatenate((self.vcmw_list[:index1], vcmw[index2:]))
        self.vcmwer_list = np.concatenate((self.vcmwer_list[:index1], vcmwer[index2:]))
        self.vpmw_list = np.concatenate((self.vpmw_list[:index1], vpmw[index2:]))

    def acquireSemaphore(self):
        self.my_semaphore.acquire()

    def releaseSemaphore(self):
        self.my_semaphore.release()

    def averageFrames(self, range_list, series_type, sim_test, sim_thresh, sim_cor, forced=False):
        frame_idx = []
        for item in range_list:
            frame_idx = frame_idx + range(item[0], item[1]+1)

        frame_idx = list(set(frame_idx))
        frame_idx.sort()

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
                    n, c, pval = SASCalc.cormap_pval(ref_sasm.i[qi_ref:qf_ref], sasm.i[qi:qf])
                pvals[index] = pval

            if sim_cor == 'Bonferroni':
                pvals = pvals*len(sasm_list[1:])
                pvals[pvals>1] = 1

            if np.any(pvals<sim_thresh):
                dif_idx = itertools.compress(frame_idx[1:], pvals<sim_thresh)
                dif_idx = map(str, dif_idx)
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

        average_sasm = SASProc.average(sasm_list, forced=True)
        average_sasm.setParameter('filename', 'A_{}'.format(average_sasm.getParameter('filename')))

        return average_sasm, True, ''

    def subtractAllSASMs(self, buffer_sasm, int_type, threshold, qref=None, qrange=None):
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

        self.subtracted_sasm_list = list(sub_sasm_list)
        self.use_subtracted_sasm = list(use_sub_sasm)

        self.mean_i_sub = np.array([sasm.getMeanI() for sasm in sub_sasm_list])
        self.total_i_sub = np.array([sasm.getTotalI() for sasm in sub_sasm_list])

        if self.qref>0:
            self.I_of_q_sub = np.array([sasm.getIofQ(self.qref) for sasm in sub_sasm_list])

        if self.qrange != (0,0):
            self.qrange_I_sub = np.array([sasm.getIofQRange(self.qrange[0], self.qrange[1]) for sasm in sub_sasm_list])

    def appendSubtractedSASMs(self, sub_sasm_list, use_sasm_list, window_size):
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

        self.baseline_subtracted_sasm_list = list(sub_sasm_list)
        self.use_baseline_subtracted_sasm = list(use_sub_sasm)

        self.mean_i_bcsub = np.array([sasm.getMeanI() for sasm in sub_sasm_list])
        self.total_i_bcsub = np.array([sasm.getTotalI() for sasm in sub_sasm_list])

        if self.qref>0:
            self.I_of_q_bcsub = np.array([sasm.getIofQ(self.qref) for sasm in sub_sasm_list])

        if self.qrange != (0,0):
            self.qrange_I_bcsub = np.array([sasm.getIofQRange(self.qrange[0], self.qrange[1]) for sasm in sub_sasm_list])

    def appendBCSubtractedSASMs(self, sub_sasm_list, use_sasm_list, window_size):
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




def calcAbsoluteScaleWaterConst(water_sasm, emptycell_sasm, I0_water, raw_settings):

    if emptycell_sasm == None or emptycell_sasm == 'None' or water_sasm == 'None' or water_sasm == None:
        raise SASExceptions.AbsScaleNormFailed('Empty cell file or water file was not found. Open options to set these files.')

    water_bgsub_sasm = SASProc.subtract(water_sasm, emptycell_sasm)

    water_avg_end_idx = int( len(water_bgsub_sasm.i) * 0.666 )
    water_avg_start_idx = int( len(water_bgsub_sasm.i) * 0.333 )

    avg_water = np.mean(water_bgsub_sasm.i[water_avg_start_idx : water_avg_end_idx])

    abs_scale_constant = I0_water / avg_water

    return abs_scale_constant

def calcAbsoluteScaleCarbonConst(carbon_sasm, carbon_thickness,
                        _raw_settings, cal_q, cal_i, cal_err, ignore_bkg, bkg_sasm,
                        carbon_ctr_ups_val, carbon_ctr_dns_val, bkg_ctr_ups_val,
                        bkg_ctr_dns_val):

    def closest(qlist, qref):
        return np.argmin(np.absolute(qlist-qref))

    if ignore_bkg:
        qmin, qmax = carbon_sasm.getQrange()
        exp_q = carbon_sasm.q[qmin:qmax]
        exp_i = carbon_sasm.i[qmin:qmax]

    else:
        carbon_trans = (carbon_ctr_dns_val/carbon_ctr_ups_val)/(bkg_ctr_dns_val/bkg_ctr_ups_val)
        carbon_sasm.scale(1./carbon_ctr_ups_val)
        bkg_sasm.scale((1./bkg_ctr_ups_val)*carbon_trans)

        exp_sasm = SASProc.subtract(carbon_sasm, bkg_sasm)

        exp_sasm.scale(1./(carbon_trans)/carbon_thickness)

        qmin, qmax = exp_sasm.getQrange()
        exp_q = exp_sasm.q[qmin:qmax]
        exp_i = exp_sasm.i[qmin:qmax]


    min_qval = max(cal_q[0], exp_q[0])
    max_qval = min(cal_q[-1], exp_q[-1])

    cal_min_idx = closest(cal_q, min_qval)
    cal_max_idx = closest(cal_q, max_qval)

    I_resamp = np.interp(cal_q[cal_min_idx:cal_max_idx+1], exp_q, exp_i)
    A = np.column_stack([I_resamp, np.zeros_like(I_resamp)])
    abs_scale_const, offset= np.linalg.lstsq(A, cal_i[cal_min_idx:cal_max_idx+1])[0]

    return abs_scale_const

def normalizeAbsoluteScaleWater(sasm, raw_settings):
    abs_scale_constant = raw_settings.get('NormAbsWaterConst')
    sasm.scaleBinnedIntensity(abs_scale_constant)

    norm_parameter = sasm.getParameter('normalizations')

    norm_parameter['Absolute_scale_factor'] = abs_scale_constant

    sasm.setParameter('normalizations', norm_parameter)

    return sasm, abs_scale_constant

def normalizeAbsoluteScaleCarbon(sasm, raw_settings):
    abs_scale_constant = float(raw_settings.get('NormAbsCarbonConst'))
    sam_thick = float(raw_settings.get('NormAbsCarbonSamThick'))
    ignore_bkg = raw_settings.get('NormAbsCarbonIgnoreBkg')

    if ignore_bkg:
        sasm.scaleBinnedIntensity(abs_scale_constant/sam_thick)
    else:
        bkg_sasm = raw_settings.get('NormAbsCarbonSamEmptySASM')

        ctr_ups = raw_settings.get('NormAbsCarbonUpstreamCtr')
        ctr_dns = raw_settings.get('NormAbsCarbonDownstreamCtr')

        sample_ctrs = sasm.getParameter('imageHeader')
        sample_file_hdr = sasm.getParameter('counters')
        sample_ctrs.update(sample_file_hdr)

        bkg_ctrs = bkg_sasm.getParameter('imageHeader')
        bkg_file_hdr = bkg_sasm.getParameter('counters')
        bkg_ctrs.update(bkg_file_hdr)

        sample_ctr_ups_val = float(sample_ctrs[ctr_ups])
        sample_ctr_dns_val = float(sample_ctrs[ctr_dns])
        bkg_ctr_ups_val = float(bkg_ctrs[ctr_ups])
        bkg_ctr_dns_val = float(bkg_ctrs[ctr_dns])

        sample_trans = (sample_ctr_dns_val/sample_ctr_ups_val)/(bkg_ctr_dns_val/bkg_ctr_ups_val)
        sasm.scaleBinnedIntensity(1./sample_ctr_ups_val)
        bkg_sasm.scale((1./bkg_ctr_ups_val)*sample_trans)

        try:
            sub_sasm = SASProc.subtract(sasm, bkg_sasm, forced = True, full = True)
        except SASExceptions.DataNotCompatible:
            sasm.scaleBinnedIntensity(sample_ctr_ups_val)
            raise SASExceptions.AbsScaleNormFailed('Absolute scale failed because empty scattering could not be subtracted')

        sub_sasm.scaleBinnedIntensity(1./(sample_trans)/sam_thick)
        sub_sasm.scaleBinnedIntensity(abs_scale_constant)

        sasm.setBinnedQ(sub_sasm.getBinnedQ())
        sasm.setBinnedI(sub_sasm.getBinnedI())
        sasm.setBinnedErr(sub_sasm.getBinnedErr())
        sasm.scale(1.)
        sasm.setQrange((0,len(sasm.q)))

        bkg_sasm.scale(1.)

    abs_scale_params = {'Absolute_scale_factor': abs_scale_constant,
                        'Sample_thickness_[mm]': sam_thick,
                        'Ignore_background': ignore_bkg,
                        }

    if not ignore_bkg:
        abs_scale_params['Background_file'] = raw_settings.get('NormAbsCarbonSamEmptyFile')
        abs_scale_params['Upstream_counter_name'] = ctr_ups
        abs_scale_params['Downstream_counter_name'] = ctr_dns
        abs_scale_params['Upstream_counter_value_sample'] = sample_ctr_ups_val
        abs_scale_params['Downstream_counter_value_sample'] = sample_ctr_dns_val
        abs_scale_params['Upstream_counter_value_background'] = bkg_ctr_ups_val
        abs_scale_params['Downstream_counter_value_background'] = bkg_ctr_dns_val
        abs_scale_params['Sample_transmission'] = sample_trans

    norm_parameter = sasm.getParameter('normalizations')

    norm_parameter['Absolute_scale'] = abs_scale_params

    sasm.setParameter('normalizations', norm_parameter)

    return sasm, abs_scale_constant

def postProcessImageSasm(sasm, raw_settings):
    if raw_settings.get('NormAbsWater'):
        normalizeAbsoluteScaleWater(sasm, raw_settings)

    elif raw_settings.get('NormAbsCarbon'):
        normalizeAbsoluteScaleCarbon(sasm, raw_settings)

def postProcessSasm(sasm, raw_settings):

    if raw_settings.get('ZingerRemoval'):
        std = raw_settings.get('ZingerRemoveSTD')
        winlen = raw_settings.get('ZingerRemoveWinLen')
        start_idx = raw_settings.get('ZingerRemoveIdx')

        sasm.removeZingers(start_idx, winlen, std)
