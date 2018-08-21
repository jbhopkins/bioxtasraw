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

import numpy as np
import scipy.interpolate as interp
from scipy import integrate as integrate
import wx

import SASCalib, SASExceptions


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
                self.total_intensity = integrate.trapz(self.i, self.q)
                self.mean_intensity = self.i.mean()
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
                self.total_intensity = integrate.trapz(self.i, self.q)
                self.mean_intensity = self.i.mean()
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

    def __init__(self, file_list, sasm_list, frame_list, parameters):
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

        # Make an entry for analysis parameters i.e. Rg, I(0) etc:
        if 'analysis' not in self._parameters:
            self._parameters['analysis'] = {}
        if 'history' not in self._parameters:
            self._parameters['history'] = {}
        if 'filename' not in self._parameters:
            self._parameters['filename'] = os.path.splitext(os.path.basename(self._file_list[0]))[0]

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
        self.I_of_q=[]

        self.time=[]
        main_frame = wx.FindWindowByName('MainFrame')
        hdr_format = main_frame.raw_settings.get('ImageHdrFormat')

        if hdr_format == 'G1, CHESS' or hdr_format == 'G1 WAXS, CHESS':
            for sasm in self._sasm_list:
                if sasm.getAllParameters().has_key('counters'):
                    file_hdr = sasm.getParameter('counters')

                    if '#C' not in file_hdr.values():
                        if file_hdr.has_key('Time'):
                            sasm_time = file_hdr['Time']
                            self.time.append(sasm_time)

                        elif file_hdr.has_key('Seconds'):
                            sasm_time = file_hdr['Seconds']
                            if len(self.time) == 0:
                                self.time.append(0)
                            else:
                                self.time.append(sasm_time+self.time[-1])

                        elif file_hdr.has_key('Exposure_time'):
                            sasm_time = file_hdr['Exposure_time']
                            if len(self.time) == 0:
                                self.time.append(0)
                            else:
                                self.time.append(sasm_time+self.time[-1])

        self.time=np.array(self.time,dtype=float)


        ####### Parameters for autocalculating rg, MW for SEC plot
        self.initial_buffer_frame = -1
        self.final_buffer_frame = -1
        self.window_size = -1
        self.threshold = -1
        self.mol_type = ''
        self.average_buffer_sasm = None
        self.subtracted_sasm_list = []
        self.use_subtracted_sasm = []
        self.rg_list = []
        self.rger_list = []
        self.i0_list = []
        self.i0er_list = []
        self.mw_list = []
        self.mwer_list = []

        self.calc_line = None
        self.calc_err_line = None
        self.calc_axes = None
        self.calc_is_plotted = False
        self.calc_has_data = False
        self.is_visible = True

        self.my_semaphore = threading.Semaphore()


    def _update(self):
        ''' updates modified intensity after scale, normalization and offset changes '''

        #self.i = ((self._i_binned / self._norm_factor) + self._offset_value) * self._scale_factor
        self.mean_i = ((self.mean_i) * self._scale_factor) + self._offset_value
        self.total_i = ((self.total_i) * self._scale_factor) + self._offset_value

        self.frame_list = self.frame_list * self._frame_scale_factor


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

        time=list(self.time)
        main_frame = wx.FindWindowByName('MainFrame')
        hdr_format = main_frame.raw_settings.get('ImageHdrFormat')

        if hdr_format == 'G1, CHESS' or hdr_format == 'G1 WAXS, CHESS':
            for sasm in sasm_list:
                if sasm.getAllParameters().has_key('counters'):
                    file_hdr = sasm.getParameter('counters')

                    if '#C' not in file_hdr.values():
                        if file_hdr.has_key('Time'):
                            sasm_time = file_hdr['Time']
                            time.append(sasm_time)

                        elif file_hdr.has_key('Seconds'):
                            sasm_time = file_hdr['Seconds']
                            if len(time) == 0:
                                time.append(0)
                            else:
                                time.append(sasm_time+time[-1])

                        elif file_hdr.has_key('Exposure_time'):
                            sasm_time = file_hdr['Exposure_time']
                            if len(time) == 0:
                                time.append(0)
                            else:
                                time.append(sasm_time+self.time[-1])

        self.time=np.array(time,dtype=float)

        if self.qref>0:

            I_of_q = []

            closest = lambda qlist: np.argmin(np.absolute(qlist-self.qref))

            for sasm in sasm_list:
                # print 'in sasm_list loop'
                qmin, qmax = sasm.getQrange()
                q = sasm.q[qmin:qmax]
                index = closest(q)
                # print index
                intensity = sasm.i[index]
                # print intensity
                I_of_q.append(intensity)

            self.I_of_q.extend(I_of_q)

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

    def getSASMList(self, initial_frame, final_frame):
        sasms = []

        try:
            initial_frame = int(initial_frame)
        except:
            msg = "Invalid value for initial frame."
            wx.CallAfter(wx.MessageBox, msg, "Invalid frame range", style = wx.ICON_ERROR | wx.OK)
            return sasms
        try:
            final_frame = int(final_frame)
        except:
            msg = "Invalid value for final frame."
            wx.CallAfter(wx.MessageBox, msg, "Invalid frame range", style = wx.ICON_ERROR | wx.OK)
            return sasms


        if initial_frame > final_frame:
            msg = "To send data to the main plot, enter a valid frame range (initial frame larger than final frame)."
            wx.CallAfter(wx.MessageBox, msg, "Invalid frame range", style = wx.ICON_ERROR | wx.OK)
            return sasms

        elif len(np.where(self.plot_frame_list == initial_frame)[0]) == 0:
            print np.where(self.plot_frame_list == initial_frame)
            msg = "To send data to the main plot, enter a valid frame range (initial frame not in data set)."
            wx.CallAfter(wx.MessageBox, msg, "Invalid frame range", style = wx.ICON_ERROR | wx.OK)
            return sasms

        else:
            sasms = self._sasm_list[initial_frame : final_frame+1]
            return sasms

    def getTime(self):
        if len(self.time)==0:
            return np.zeros_like(self.frame_list) - 1
        else:
            return self.time
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

        all_data['scale_factor'] = self._scale_factor
        all_data['offset_value'] = self._offset_value
        all_data['frame_scale_factor'] = self._frame_scale_factor

        all_data['parameters'] = self._parameters

        all_data['intial_buffer_frame'] = self.initial_buffer_frame
        all_data['final_buffer_frame'] = self.final_buffer_frame
        all_data['window_size'] = self.window_size
        all_data['mol_type'] = self.mol_type
        all_data['threshold'] = self.threshold
        all_data['rg'] = self.rg_list
        all_data['rger'] = self.rger_list
        all_data['i0'] = self.i0_list
        all_data['i0er'] = self.i0er_list
        all_data['mw'] = self.mw_list
        all_data['mwer'] = self.mwer_list
        all_data['calc_has_data'] = self.calc_has_data
        all_data['is_visible'] = self.is_visible

        all_data['use_subtracted_sasm'] = self.use_subtracted_sasm


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


        return all_data

    def copy(self):
        ''' return a copy of the object '''

        return SECM(copy.copy(self.mean_i), copy.copy(self.total_i), copy.copy(self.frame_list), copy.copy(self._parameters))

    def getSASM(self, index=0):
        return self._sasm_list[index]

    def I(self, qref):
        # print 'in I(q)'
        self.qref=float(qref)
        self.I_of_q = []

        closest = lambda qlist: np.argmin(np.absolute(qlist-self.qref))

        for sasm in self._sasm_list:
            # print 'in sasm_list loop'
            q = sasm.q
            index = closest(q)
            # print index
            intensity = sasm.i[index]
            # print intensity
            self.I_of_q.append(intensity)

        return self.I_of_q

    def setCalcParams(self, initial, final, window, mol_type, threshold):
        new = False

        if initial != self.initial_buffer_frame or final != self.final_buffer_frame or window != self.window_size or self.mol_type != mol_type or threshold != self.threshold:
            new = True

            self.initial_buffer_frame = initial
            self.final_buffer_frame = final
            self.window_size = window
            self.mol_type = mol_type
            self.threshold = threshold

        return new

    def getCalcParams(self):
        return self.initial_buffer_frame, self.final_buffer_frame, self.window_size

    def setAverageBufferSASM(self, sasm):
        self.average_buffer_sasm = sasm

    def getAverageBufferSASM(self):
        return self.average_buffer_sasm

    def getAllSASMs(self):
        return self._sasm_list

    def setSubtractedSASMList(self, sasm_list, use_sasm_list):
        self.subtracted_sasm_list = sasm_list
        self.use_subtracted_sasm = use_sasm_list

    def appendSubtractedSASMList(self, sasm_list, use_sasm_list, window_size):
        self.subtracted_sasm_list = self.subtracted_sasm_list[:-window_size] + sasm_list
        self.use_subtracted_sasm = self.use_subtracted_sasm[:-window_size] + use_sasm_list

    def setRgAndI0(self, rg, rger, i0, i0er):
        self.rg_list = rg
        self.rger_list = rger
        self.i0_list = i0
        self.i0er_list = i0er

    def setMW(self, mw, mwer):
        self.mw_list = mw
        self.mwer_list = mwer

    def getRg(self):
        return self.rg_list, self.rger_list

    def getMW(self):
        return self.mw_list, self.mwer_list

    def getI0(self):
        return self.i0_list, self.i0er_list

    def appendRgAndI0(self, rg, rger, i0, i0er, first_frame, window_size):
        index1 = first_frame+(window_size-1)/2
        index2 = (window_size-1)/2

        self.rg_list = np.concatenate((self.rg_list[:index1],rg[index2:]))
        self.rger_list = np.concatenate((self.rger_list[:index1],rger[index2:]))
        self.i0_list = np.concatenate((self.i0_list[:index1],i0[index2:]))
        self.i0er_list = np.concatenate((self.i0er_list[:index1],i0er[index2:]))


    def appendMW(self, mw, mwer, first_frame, window_size):
        index1 = first_frame+(window_size-1)/2
        index2 = (window_size-1)/2

        self.mw_list = np.concatenate((self.mw_list[:index1], mw[index2:]))
        self.mwer_list = np.concatenate((self.mwer_list[:index1], mwer[index2:]))

    def acquireSemaphore(self):
        self.my_semaphore.acquire()

    def releaseSemaphore(self):
        self.my_semaphore.release()

def subtract(sasm1, sasm2, forced = False, full = False):
    ''' Subtract one SASM object from another and propagate errors '''
    if not full:
        q1_min, q1_max = sasm1.getQrange()
        q2_min, q2_max = sasm2.getQrange()
    else:
        q1_min = 0
        q1_max = len(sasm1.q)+1
        q2_min = 0
        q2_max = len(sasm2.q)+1

    if not np.all(np.round(sasm1.q[q1_min:q1_max],5) == np.round(sasm2.q[q2_min:q2_max],5)) and not forced:
        raise SASExceptions.DataNotCompatible('The curves does not have the same q vectors.')

    elif not np.all(np.round(sasm1.q[q1_min:q1_max],5) == np.round(sasm2.q[q2_min:q2_max],5)) and forced:
        q1 = np.round(sasm1.q[q1_min:q1_max],5)
        q2 = np.round(sasm2.q[q2_min:q2_max],5)
        i1 = sasm1.i[q1_min:q1_max]
        i2 = sasm2.i[q2_min:q2_max]
        err1 = sasm1.err[q1_min:q1_max]
        err2 = sasm2.err[q2_min:q2_max]

        if q1[0]>q2[0]:
            start=np.round(q1[0],5)
        else:
            start=np.round(q2[0],5)

        if q1[-1]>q2[-1]:
            end=np.round(q2[-1],5)
        else:
            end=np.round(q1[-1],5)

        if start>end:
            raise SASExceptions.DataNotCompatible('Subtraction failed: the curves have no overlapping q region.')

        shifted = False
        if len(np.argwhere(q1==start))>0 and len(np.argwhere(q1==end))>0 and len(np.argwhere(q2==start))>0 and len(np.argwhere(q2==end))>0:
            q1_idx1 = np.argwhere(q1==start)[0][0]
            q1_idx2 = np.argwhere(q1==end)[0][0]+1
            q2_idx1 = np.argwhere(q2==start)[0][0]
            q2_idx2 = np.argwhere(q2==end)[0][0] +1

            if np.all(q1[q1_idx1:q1_idx2]==q2[q2_idx1:q2_idx2]):
                shifted = True

        if shifted:
            i = i1[q1_idx1:q1_idx2] - i2[q2_idx1:q2_idx2]
            err = np.sqrt( np.power(err1[q1_idx1:q1_idx2], 2) + np.power(err2[q2_idx1:q2_idx2],2))

            q = copy.deepcopy(sasm1.q[q1_idx1:q1_idx2])

        else:
            q1space=q1[1]-q1[0]
            q2space=q2[1]-q2[0]

            if q1space>q2space:
                npts=(end-start)/q1space+1
            else:
                npts=(end-start)/q2space+1

            refq=np.linspace(start,end,npts,endpoint=True)

            q1_idx1 = np.argmin(np.absolute(q1-start))
            q1_idx2 = np.argmin(np.absolute(q1-end))+1
            q2_idx1 = np.argmin(np.absolute(q2-start))
            q2_idx2 = np.argmin(np.absolute(q2-end))+1

            q1b, i1b, err1b=binfixed(sasm1.q[q1_idx1:q1_idx2], i1[q1_idx1:q1_idx2], err1[q1_idx1:q1_idx2], refq=refq)
            q2b, i2b, err2b=binfixed(sasm2.q[q2_idx1:q2_idx2], i2[q2_idx1:q2_idx2], err2[q2_idx1:q2_idx2], refq=refq)

            i = i1b - i2b
            err=np.sqrt(np.square(err1b)+np.square(err2b))

            q = refq

    else:
        i = sasm1.i[q1_min:q1_max] - sasm2.i[q2_min:q2_max]

        q = copy.deepcopy(sasm1.q)[q1_min:q1_max]
        err = np.sqrt( np.power(sasm1.err[q1_min:q1_max], 2) + np.power(sasm2.err[q2_min:q2_max],2))

    parameters = copy.deepcopy(sasm1.getAllParameters())
    newSASM = SASM(i, q, err, {})
    newSASM.setParameter('filename', parameters['filename'])

    history = newSASM.getParameter('history')

    history = {}

    history1 = []
    history1.append(copy.deepcopy(sasm1.getParameter('filename')))
    for key in sasm1.getParameter('history'):
        history1.append({ key : copy.deepcopy(sasm1.getParameter('history')[key])})

    history2 = []
    history2.append(copy.deepcopy(sasm2.getParameter('filename')))
    for key in sasm2.getParameter('history'):
        history2.append({key : copy.deepcopy(sasm2.getParameter('history')[key])})

    history['subtraction'] = {'initial_file':history1, 'subtracted_file':history2}

    newSASM.setParameter('history', history)

    return newSASM

def average(sasm_list, forced = False):
    ''' Average the intensity of a list of sasm objects '''

    if len(sasm_list) == 1:
        #Useful for where all but the first profile are rejected due to similarity
        #testing. Otherwise we should never have less than one profile to average
        sasm = sasm_list[0]
        q_min, q_max = sasm.getQrange()

        avg_q = copy.deepcopy(sasm.q[q_min:q_max])
        avg_i = copy.deepcopy(sasm.i[q_min:q_max])
        avg_err = copy.deepcopy(sasm.err[q_min:q_max])
        avg_parameters = copy.deepcopy(sasm.getAllParameters())

        avgSASM = SASM(avg_i, avg_q, avg_err, avg_parameters)

        history = {}
        history_list = []
        for eachsasm in sasm_list:
            each_history = []
            each_history.append(copy.deepcopy(eachsasm.getParameter('filename')))

            for key in eachsasm.getParameter('history'):
                each_history.append({key : copy.deepcopy(eachsasm.getParameter('history')[key])})

            history_list.append(each_history)


        history['averaged_files'] = history_list
        avgSASM.setParameter('history', history)

    else:
        #Check average is possible with provided curves:
        first_sasm = sasm_list[0]
        first_q_min, first_q_max = first_sasm.getQrange()

        for each in sasm_list:
            each_q_min, each_q_max = each.getQrange()
            if not np.all(np.round(each.q[each_q_min:each_q_max], 5) == np.round(first_sasm.q[first_q_min:first_q_max], 5)) and not forced:
                raise SASExceptions.DataNotCompatible('Average list contains data sets with different q vectors.')

        all_i = first_sasm.i[first_q_min : first_q_max]

        all_err = first_sasm.err[first_q_min : first_q_max]

        avg_filelist = []
        avg_filelist.append(first_sasm.getParameter('filename'))

        for idx in range(1, len(sasm_list)):
            each_q_min, each_q_max = sasm_list[idx].getQrange()
            all_i = np.vstack((all_i, sasm_list[idx].i[each_q_min:each_q_max]))
            all_err = np.vstack((all_err, sasm_list[idx].err[each_q_min:each_q_max]))
            avg_filelist.append(sasm_list[idx].getParameter('filename'))

        avg_i = np.mean(all_i, 0)

        avg_err = np.sqrt( np.sum( np.power(all_err,2), 0 ) ) / len(all_err)  #np.sqrt(len(all_err))

        avg_i = copy.deepcopy(avg_i)
        avg_err = copy.deepcopy(avg_err)

        avg_q = copy.deepcopy(first_sasm.q)[first_q_min:first_q_max]
        avg_parameters = copy.deepcopy(sasm_list[0].getAllParameters())

        avgSASM = SASM(avg_i, avg_q, avg_err, {})
        avgSASM.setParameter('filename', avg_parameters['filename'])

        history = {}

        history_list = []

        for eachsasm in sasm_list:
            each_history = []
            each_history.append(copy.deepcopy(eachsasm.getParameter('filename')))

            for key in eachsasm.getParameter('history'):
                each_history.append({key : copy.deepcopy(eachsasm.getParameter('history')[key])})

            history_list.append(each_history)

        history['averaged_files'] = history_list
        avgSASM.setParameter('history', history)

    return avgSASM

def weightedAverage(sasm_list, weightByError, weightCounter, forced = False):
    ''' Weighted average of the intensity of a list of sasm objects '''
    if len(sasm_list) == 1:
        #Useful for where all but the first profile are rejected due to similarity
        #testing. Otherwise we should never have less than one profile to average
        sasm = sasm_list[0]
        q_min, q_max = sasm.getQrange()

        avg_q = copy.deepcopy(sasm.q[q_min:q_max])
        avg_i = copy.deepcopy(sasm.i[q_min:q_max])
        avg_err = copy.deepcopy(sasm.err[q_min:q_max])
        avg_parameters = copy.deepcopy(sasm.getAllParameters())

        avgSASM = SASM(avg_i, avg_q, avg_err, avg_parameters)

        history = {}
        history_list = []
        for eachsasm in sasm_list:
            each_history = []
            each_history.append(copy.deepcopy(eachsasm.getParameter('filename')))

            for key in eachsasm.getParameter('history'):
                each_history.append({key : copy.deepcopy(eachsasm.getParameter('history')[key])})

            history_list.append(each_history)


        history['averaged_files'] = history_list
        avgSASM.setParameter('history', history)

    else:
        #Check average is possible with provided curves:
        first_sasm = sasm_list[0]
        first_q_min, first_q_max = first_sasm.getQrange()

        for each in sasm_list:
            each_q_min, each_q_max = each.getQrange()
            if not np.all(np.round(each.q[each_q_min:each_q_max], 5) == np.round(first_sasm.q[first_q_min:first_q_max], 5)) and not forced:
                raise SASExceptions.DataNotCompatible('Average list contains data sets with different q vectors.')

        all_i = first_sasm.i[first_q_min : first_q_max]
        all_err = first_sasm.err[first_q_min : first_q_max]

        if not weightByError:
            if first_sasm.getAllParameters().has_key('counters'):
                file_hdr = first_sasm.getParameter('counters')
            if first_sasm.getAllParameters().has_key('imageHeader'):
                img_hdr = first_sasm.getParameter('imageHeader')

            if weightCounter in file_hdr:
                all_weight = float(file_hdr[weightCounter])
            else:
                all_weight = float(img_hdr[weightCounter])

        avg_filelist = []
        if not weightByError:
            avg_filelist.append([first_sasm.getParameter('filename'), all_weight])
        else:
            avg_filelist.append([first_sasm.getParameter('filename'), 'error'])

        for idx in range(1, len(sasm_list)):
            each_q_min, each_q_max = sasm_list[idx].getQrange()
            all_i = np.vstack((all_i, sasm_list[idx].i[each_q_min:each_q_max]))
            all_err = np.vstack((all_err, sasm_list[idx].err[each_q_min:each_q_max]))

            if not weightByError:
                if sasm_list[idx].getAllParameters().has_key('counters'):
                    file_hdr = sasm_list[idx].getParameter('counters')
                if sasm_list[idx].getAllParameters().has_key('imageHeader'):
                    img_hdr = sasm_list[idx].getParameter('imageHeader')

                if weightCounter in file_hdr:
                    try:
                        all_weight = np.vstack((all_weight, float(file_hdr[weightCounter])))
                    except ValueError:
                        raise SASExceptions.DataNotCompatible('Not all weight counter values were numbers.')

                else:
                    try:
                        all_weight = np.vstack((all_weight, float(img_hdr[weightCounter])))
                    except ValueError:
                        raise SASExceptions.DataNotCompatible('Not all weight counter values were numbers.')

            if not weightByError:
                avg_filelist.append([sasm_list[idx].getParameter('filename'), all_weight])
            else:
                avg_filelist.append([sasm_list[idx].getParameter('filename'), 'error'])

        if not weightByError:
            weight = all_weight.flatten()
            avg_i = np.average(all_i, axis=0, weights=weight)
            avg_err = np.sqrt(np.average(np.square(all_err), axis=0, weights=np.square(weight)))
        else:
            all_err = 1/(np.square(all_err))
            avg_i = np.average(all_i, axis=0, weights = all_err)
            avg_err = np.sqrt(1/np.sum(all_err,0))

        avg_i = copy.deepcopy(avg_i)
        avg_err = copy.deepcopy(avg_err)

        avg_q = copy.deepcopy(first_sasm.q)[first_q_min:first_q_max]
        avg_parameters = copy.deepcopy(sasm_list[0].getAllParameters())

        avgSASM = SASM(avg_i, avg_q, avg_err, {})
        avgSASM.setParameter('filename', avg_parameters['filename'])
        history = avgSASM.getParameter('history')

        history = {}

        history_list = []

        for eachsasm in sasm_list:
            each_history = []
            each_history.append(copy.deepcopy(eachsasm.getParameter('filename')))

            for key in eachsasm.getParameter('history'):
                each_history.append({key : copy.deepcopy(eachsasm.getParameter('history')[key])})

            history_list.append(each_history)


        history['weighted_averaged_files'] = history_list
        avgSASM.setParameter('history', history)

    return avgSASM

def calcAbsoluteScaleWaterConst(water_sasm, emptycell_sasm, I0_water, raw_settings):

    if emptycell_sasm == None or emptycell_sasm == 'None' or water_sasm == 'None' or water_sasm == None:
        raise SASExceptions.AbsScaleNormFailed('Empty cell file or water file was not found. Open options to set these files.')

    water_bgsub_sasm = subtract(water_sasm, emptycell_sasm)

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

        exp_sasm = subtract(carbon_sasm, bkg_sasm)

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
            sub_sasm = subtract(sasm, bkg_sasm, forced = True, full = True)
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

def superimpose(sasm_star, sasm_list, choice):
    """
    Find the scale and/or offset factor between a reference curve and the
    curves of interest.
    The reference curve need not be sampled at the same q-space points.

    """

    q_star = sasm_star.q
    i_star = sasm_star.i
    # err_star = sasm_star.err

    q_star_qrange_min, q_star_qrange_max = sasm_star.getQrange()

    q_star = q_star[q_star_qrange_min:q_star_qrange_max]
    i_star = i_star[q_star_qrange_min:q_star_qrange_max]

    for each_sasm in sasm_list:

        each_q = each_sasm.getBinnedQ()
        each_i = each_sasm.getBinnedI()
        # each_err = each_sasm.getBinnedErr()

        each_q_qrange_min, each_q_qrange_max = each_sasm.getQrange()

        # resample standard curve on the data q vector
        min_q_each = each_q[each_q_qrange_min]
        max_q_each = each_q[each_q_qrange_max-1]

        min_q_idx = np.where(q_star >= min_q_each)[0][0]
        max_q_idx = np.where(q_star <= max_q_each)[0][-1]

        I_resamp = np.interp(q_star[min_q_idx:max_q_idx+1],
                             each_q[each_q_qrange_min:each_q_qrange_max],
                             each_i[each_q_qrange_min:each_q_qrange_max])


        if choice == 'Scale and Offset':
            A = np.column_stack([I_resamp, np.ones_like(I_resamp)])
            scale, offset = np.linalg.lstsq(A, i_star[min_q_idx:max_q_idx+1])[0]
        elif choice == 'Scale':
            A = np.column_stack([I_resamp, np.zeros_like(I_resamp)])
            scale, offset= np.linalg.lstsq(A, i_star[min_q_idx:max_q_idx+1])[0]
            offset = 0
        elif choice == 'Offset':
            A = np.column_stack([np.zeros_like(I_resamp), np.ones_like(I_resamp)])
            scale, offset= np.linalg.lstsq(A, i_star[min_q_idx:max_q_idx+1]-I_resamp)[0]
            scale = 1

        each_sasm.scale(scale)
        each_sasm.offset(offset)


def merge(sasm_star, sasm_list):

    """ Merge one or more sasms by averaging and possibly interpolating
    points if all values are not on the same q scale """

    #Sort sasms according to lowest q value:
    sasm_list.extend([sasm_star])
    sasm_list = sorted(sasm_list, key=lambda each: each.q[each.getQrange()[0]])

    s1 = sasm_list[0]
    s2 = sasm_list[1]

    sasm_list.pop(0)
    sasm_list.pop(0)

    #find overlapping s2 points
    highest_q = s1.q[s1.getQrange()[1]-1]
    min, max = s2.getQrange()
    overlapping_q2 = s2.q[min:max][np.where(s2.q[min:max] <= highest_q)]

    #find overlapping s1 points
    lowest_s2_q = s2.q[s2.getQrange()[0]]
    min, max = s1.getQrange()
    overlapping_q1 = s1.q[min:max][np.where(s1.q[min:max] >= lowest_s2_q)]

    tmp_s2i = s2.i.copy()
    tmp_s2q = s2.q.copy()
    tmp_s2err = s2.err.copy()

    if len(overlapping_q1) == 1 and len(overlapping_q2) == 1: #One point overlap
        q1idx = s1.getQrange()[1]
        q2idx = s2.getQrange()[0]

        avg_i = (s1.i[q1idx] + s2.i[q2idx])/2.0

        tmp_s2i[q2idx] = avg_i

        minq, maxq = s1.getQrange()
        q1_indexs = [maxq-1, minq]

    elif len(overlapping_q1) == 0 and len(overlapping_q2) == 0: #No overlap
        minq, maxq = s1.getQrange()
        q1_indexs = [maxq, minq]

    else:   #More than 1 point overlap

        added_index = False
        if overlapping_q2[0] < overlapping_q1[0]:
            #add the point before overlapping_q1[0] to overlapping_q1
            idx, = np.where(s1.q == overlapping_q1[0])
            overlapping_q1 = np.insert(overlapping_q1, 0, s1.q[idx-1][0])
            added_index = True

        #get indexes for overlapping_q2 and q1
        q2_indexs = []
        q1_indexs = []

        for each in overlapping_q2:
            idx, = np.where(s2.q == each)
            q2_indexs.append(idx[0])

        for each in overlapping_q1:
            idx, = np.where(s1.q == each)
            q1_indexs.append(idx[0])

        #interpolate overlapping s2 onto s1
        f = interp.interp1d(s1.q[q1_indexs], s1.i[q1_indexs])
        intp_I = f(s2.q[q2_indexs])
        averaged_I = (intp_I + s2.i[q2_indexs])/2.0

        if added_index:
            q1_indexs = np.delete(q1_indexs, 0)

        tmp_s2i[q2_indexs] = averaged_I


    #Merge the two parts
    #cut away the overlapping part on s1 and append s2 to it
    min, max = s1.getQrange()
    newi = s1.i[min:q1_indexs[0]]
    newq = s1.q[min:q1_indexs[0]]
    newerr = s1.err[min:q1_indexs[0]]

    min, max = s2.getQrange()
    newi = np.append(newi, tmp_s2i[min:max])
    newq = np.append(newq, tmp_s2q[min:max])
    newerr = np.append(newerr, tmp_s2err[min:max])

    #create a new SASM object with the merged parts.
    parameters = copy.deepcopy(s1.getAllParameters())
    newSASM = SASM(newi, newq, newerr, parameters)

    history = newSASM.getParameter('history')

    history = {}

    history_list = []

    for eachsasm in [s1, s2]:
        each_history = []
        each_history.append(copy.deepcopy(eachsasm.getParameter('filename')))
        for key in eachsasm.getParameter('history'):
            each_history.append({key : copy.deepcopy(eachsasm.getParameter('history')[key])})

        history_list.append(each_history)

    history['merged_files'] = history_list
    newSASM.setParameter('history', history)

    if len(sasm_list) == 0:
        return newSASM
    else:
        return merge(newSASM, sasm_list)

def interpolateToFit(sasm_star, sasm):
    s1 = sasm_star
    s2 = sasm

    #find overlapping s2 points
    min_q1, max_q1 = s1.getQrange()
    min_q2, max_q2 = s2.getQrange()

    lowest_q1, highest_q1 = s1.q[s1.getQrange()[0]], s1.q[s1.getQrange()[1]-1]

    #fuck hvor besvaerligt!
    overlapping_q2_top = s2.q[min_q2:max_q2][np.where( (s2.q[min_q2:max_q2] <= highest_q1))]
    overlapping_q2 = overlapping_q2_top[np.where(overlapping_q2_top >= lowest_q1)]

    if overlapping_q2[0] != s2.q[0]:
        idx = np.where(s2.q == overlapping_q2[0])
        overlapping_q2 = np.insert(overlapping_q2, 0, s2.q[idx[0]-1])

    if overlapping_q2[-1] != s2.q[-1]:
        idx = np.where(s2.q == overlapping_q2[-1])
        overlapping_q2 = np.append(overlapping_q2, s2.q[idx[0]+1])

    overlapping_q1_top = s1.q[min_q1:max_q1][np.where( (s1.q[min_q1:max_q1] <= overlapping_q2[-1]))]
    overlapping_q1 = overlapping_q1_top[np.where(overlapping_q1_top >= overlapping_q2[0])]

    q2_indexs = []
    q1_indexs = []
    for each in overlapping_q2:
        idx, = np.where(s2.q == each)
        q2_indexs.append(idx[0])

    for each in overlapping_q1:
        idx, = np.where(s1.q == each)
        q1_indexs.append(idx[0])

    #interpolate find the I's that fits the q vector of s1:
    f = interp.interp1d(s2.q[q2_indexs], s2.i[q2_indexs])

    intp_i_s2 = f(s1.q[q1_indexs])
    intp_q_s2 = s1.q[q1_indexs].copy()
    newerr = s1.err[q1_indexs].copy()

    parameters = copy.deepcopy(s1.getAllParameters())

    newSASM = SASM(intp_i_s2, intp_q_s2, newerr, parameters)

    history = newSASM.getParameter('history')

    history = {}

    history1 = []
    history1.append(copy.deepcopy(s1.getParameter('filename')))
    for key in s1.getParameter('history'):
        history1.append({key:copy.deepcopy(s1.getParameter('history')[key])})

    history2 = []
    history2.append(copy.deepcopy(s2.getParameter('filename')))
    for key in s2.getParameter('history'):
        history2.append({key:copy.deepcopy(s2.getParameter('history')[key])})

    history['interpolation'] = {'initial_file':history1, 'interpolated_to_q_of':history2}
    newSASM.setParameter('history', history)

    return newSASM

def logBinning(sasm, no_points):

    #if end_idx == -1:
#       end_idx = len(self._i_raw)

    i_roi = sasm._i_binned
    q_roi = sasm._q_binned
    err_roi = sasm._err_binned

    bins = np.logspace(1, np.log10(len(q_roi)), no_points)

    binned_q = []
    binned_i = []
    binned_err = []

    idx = 0
    for i in range(0, len(bins)):
        no_of_bins = int(np.floor(bins[i] - bins[i-1]))

        if no_of_bins > 1:
            mean_q = np.mean( q_roi[ idx : idx + no_of_bins ] )
            mean_i = np.mean( i_roi[ idx : idx + no_of_bins ] )

            mean_err = np.sqrt( sum( np.power( err_roi[ idx : idx + no_of_bins ], 2) ) ) / np.sqrt( no_of_bins )

            binned_q.append(mean_q)
            binned_i.append(mean_i)
            binned_err.append(mean_err)

            idx = idx + no_of_bins
        else:
            binned_q.append(q_roi[idx])
            binned_i.append(i_roi[idx])
            binned_err.append(err_roi[idx])
            idx = idx + 1

    parameters = copy.deepcopy(sasm.getAllParameters())

    newSASM = SASM(binned_i, binned_q, binned_err, parameters)

    history = newSASM.getParameter('history')

    history = {}

    history1 = []
    history1.append(copy.deepcopy(sasm.getParameter('filename')))

    for key in sasm.getParameter('history'):
        history1.append({key:copy.deepcopy(sasm.getParameter('history')[key])})

    history['log_binning'] = {'initial_file' : history1, 'initial_points' : len(q_roi), 'final_points': len(bins)}

    newSASM.setParameter('history', history)

    return newSASM

def rebin(sasm, rebin_factor):
    ''' Sets the bin size of the I_q plot
        end_idx will be lowered to fit the bin_size
        if needed.
    '''

    len_iq = len(sasm._i_binned)

    no_of_bins = int(np.floor(len_iq / rebin_factor))

    end_idx = no_of_bins * rebin_factor

    start_idx = 0
    i_roi = sasm._i_binned[start_idx:end_idx]
    q_roi = sasm._q_binned[start_idx:end_idx]
    err_roi = sasm._err_binned[start_idx:end_idx]

    new_i = np.zeros(no_of_bins)
    new_q = np.zeros(no_of_bins)
    new_err = np.zeros(no_of_bins)

    for eachbin in range(0, no_of_bins):
        first_idx = eachbin * rebin_factor
        last_idx = (eachbin * rebin_factor) + rebin_factor

        new_i[eachbin] = sum(i_roi[first_idx:last_idx]) / rebin_factor
        new_q[eachbin] = sum(q_roi[first_idx:last_idx]) / rebin_factor
        new_err[eachbin] = np.sqrt(sum(np.power(err_roi[first_idx:last_idx],2))) / np.sqrt(rebin_factor)


    parameters = copy.deepcopy(sasm.getAllParameters())

    newSASM = SASM(new_i, new_q, new_err, parameters)

    qstart, qend = sasm.getQrange()

    new_qstart = int(qstart/float(rebin_factor)+.5)
    new_qend = int(qend/float(rebin_factor))

    newSASM.setQrange([new_qstart, new_qend])

    history = newSASM.getParameter('history')

    history = {}

    history1 = []
    history1.append(copy.deepcopy(sasm.getParameter('filename')))

    for key in sasm.getParameter('history'):
        history1.append({key:copy.deepcopy(sasm.getParameter('history')[key])})

    history['log_binning'] = {'initial_file' : history1, 'initial_points' : len_iq, 'final_points': no_of_bins}

    newSASM.setParameter('history', history)

    return newSASM


def binfixed(q, I, er, refq):
    """
    This function bins the input q, I, and er into the fixed bins of qref
    """
    dq=refq[1]-refq[0]

    qn=np.linspace(refq[0]-dq/2.,refq[-1]+1.5*dq, np.around((refq[-1]+2*dq-refq[0])/dq,0)+1,endpoint=True )


    dig=np.digitize(q,qn)

    In=np.array([I[dig==i].mean() for i in range(1,len(qn)-1)])


    mI = np.ma.masked_equal(I,0)

    Iern=np.array([np.sqrt(np.sum(np.square(er[dig==i]/mI[dig==i])))/len(I[dig==i]) for i in range(1,len(qn)-1)])

    Iern=Iern*In

    qn=refq

    return qn, In, np.nan_to_num(Iern)


