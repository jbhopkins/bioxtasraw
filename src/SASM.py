'''
Created on Jul 5, 2010

@author: Soren S. Nielsen
'''

import numpy as np
import scipy.interpolate as interp
from scipy import integrate as integrate
import os, copy
import SASCalib, SASExceptions
from math import pi, sin
import wx

class SASM:
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
        self.origline = None
        self.fitline = None
        self.err_line = None
        self.axes = None
        self.is_plotted = False
        self._selected_q_range = (0, len(self._q_binned))

        #Calculated values
        try:
            if len(self.q)>0:
                self.total_intensity = integrate.simps(self.i, self.q)
                self.mean_intensity = self.i.mean()
        except:
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

        #Calculated values
        try:
            if len(self.q)>0:
                self.total_intensity = integrate.simps(self.i, self.q)
                self.mean_intensity = self.i.mean()
        except:
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
            self._selected_q_range = qrange    
    
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

        # self.fitline = None
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
            self._selected_q_range = qrange    
    
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


class SECM:
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
            self._parameters['filename'] = os.path.basename(self._file_list[0])
        
        #Extract initial mean and total intensity variables
        self._mean_i_raw = np.array([sasm.getMeanI() for sasm in self._sasm_list])
        self._total_i_raw = np.array([sasm.getTotalI() for sasm in self._sasm_list])

        #Set up the modified mean and total intensity variables
        self.mean_i = self._mean_i_raw.copy()
        self.total_i = self._total_i_raw.copy()

        #Make sure we have as many frame numbers as sasm objects
        if len(self._sasm_list) != len(self._frame_list_raw):
            self._frame_list_raw=np.arange(len(self._sasm_list))
            print 'Warning: Incorrect frame number input to SECM object. Using default frame numbers.'

        self.frame_list = self._frame_list_raw.copy()

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
        self.average_buffer_sasm = None
        self.subtracted_sasm_list = []
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
                q = sasm.q
                index = closest(q)
                # print index
                intensity = sasm.i[index]
                # print intensity
                I_of_q.append(intensity)

            self.I_of_q.extend(I_of_q)

        # print self.time

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

        elif len(np.where(self.frame_list == initial_frame)[0]) == 0:
            msg = "To send data to the main plot, enter a valid frame range (initial frame not in data set)."
            wx.CallAfter(wx.MessageBox, msg, "Invalid frame range", style = wx.ICON_ERROR | wx.OK)
            return sasms

        else:
            index1 = np.where(self.frame_list == initial_frame)[0][0]

            if len(np.where(self.frame_list == final_frame)[0]) == 0:
                index2 = len(self.frame_list)
                print 'Warning: Final frame not in data set'
            else:
                index2 = np.where(self.frame_list == final_frame)[0][0]

            sasms = self._sasm_list[index1 : index2+1]

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
        self._frame_scale_factor = q_scale_factor
        
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
        all_data['rg'] = self.rg_list
        all_data['rger'] = self.rger_list
        all_data['i0'] = self.i0_list
        all_data['i0er'] = self.i0er_list
        all_data['mw'] = self.mw_list
        all_data['mwer'] = self.mwer_list
        all_data['calc_has_data'] = self.calc_has_data
        all_data['is_visible'] = self.is_visible


        all_data['sasm_list'] = []
        for idx in range(len(self._sasm_list)):
            all_data['sasm_list'].append(self._sasm_list[idx].extractAll())

        if self.average_buffer_sasm == None:
            all_data['average_buffer_sasm'] = self.average_buffer_sasm
        else:
            all_data['average_buffer_sasm'] = self.average_buffer_sasm.extractAll()


        all_data['subtracted_sasm_list'] = []
        for idx in range(len(self.subtracted_sasm_list)):
            all_data['subtracted_sasm_list'].append(self.subtracted_sasm_list[idx].extractAll())

        
        return all_data
    
    def copy(self):
        ''' return a copy of the object ''' 
        
        return SECM(copy.copy(self.mean_i), copy.copy(self.total_i), copy.copy(self.frame_list), copy.copy(self._parameters))

    def getFilename(self):
        return os.path.basename(self._file_list[0])

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

    def setCalcParams(self, initial, final, window):
        new = False

        if initial != self.initial_buffer_frame or final != self.final_buffer_frame or window != self.window_size:
            new = True

            self.initial_buffer_frame = initial
            self.final_buffer_frame = final
            self.window_size = window

        # print self.initial_buffer_frame
        # print self.final_buffer_frame
        # print self.window_size
        # print new

        return new

    def getCalcParams(self):
        return self.initial_buffer_frame, self.final_buffer_frame, self.window_size

    def setAverageBufferSASM(self, sasm):

        self.average_buffer_sasm = sasm
        
    def getAllSASMs(self):
        return self._sasm_list

    def setSubtractedSASMList(self, sasm_list):
        self.subtracted_sasm_list = sasm_list

    def appendSubtractedSASMList(self, sasm_list):
        self.subtracted_sasm_list = self.subtracted_sasm_list + sasm_list

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
                
def subtract(sasm1, sasm2, forced = False):
    ''' Subtract one SASM object from another and propagate errors '''
    
    q1_min, q1_max = sasm1.getQrange()
    q2_min, q2_max = sasm2.getQrange()
    
    if not np.all(np.round(sasm1.q[q1_min:q1_max],5) == np.round(sasm2.q[q2_min:q2_max],5)) and not forced:
        raise SASExceptions.DataNotCompatible('The curves does not have the same q vectors.')

    elif not np.all(np.round(sasm1.q[q1_min:q1_max],5) == np.round(sasm2.q[q2_min:q2_max],5)) and forced:
        q1 = np.round(sasm1.q[q1_min:q1_max],5)
        q2 = np.round(sasm2.q[q2_min:q2_max],5)
        i1 = np.round(sasm1.i[q1_min:q1_max],5)
        i2 = np.round(sasm2.i[q2_min:q2_max],5)
        err1 = np.round(sasm1.err[q1_min:q1_max],5)
        err2 = np.round(sasm2.err[q2_min:q2_max],5)

        if q1[0]>q2[0]:
            start=np.round(q1[0],5)
            q1start=True
        else:
            start=np.round(q2[0],5)
            q1start=False

        if q1[-1]>q2[-1]:
            end=np.round(q2[-1],5)
            q1end=False
        else:
            end=np.round(q1[-1],5)
            q1end=True

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

            q = copy.deepcopy(q1[q1_idx1:q1_idx2])

            # print i
            # print q
        
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

            q1b, i1b, err1b=binfixed(q1[q1_idx1:q1_idx2], i1[q1_idx1:q1_idx2], err1[q1_idx1:q1_idx2], refq=refq)
            q2b, i2b, err2b=binfixed(q2[q2_idx1:q2_idx2], i2[q2_idx1:q2_idx2], err2[q2_idx1:q2_idx2], refq=refq)
            
            i = i1b - i2b
            err=np.sqrt(np.square(err1b)+np.square(err2b))

            q = refq 

    else:
        i = sasm1.i[q1_min:q1_max] - sasm2.i[q2_min:q2_max]

        q = copy.deepcopy(sasm1.q)[q1_min:q1_max]
        err = np.sqrt( np.power(sasm1.err[q1_min:q1_max], 2) + np.power(sasm2.err[q2_min:q2_max],2))
    
    parameters = copy.deepcopy(sasm1.getAllParameters())
    newSASM = SASM(i, q, err, parameters)

    history = newSASM.getParameter('history')
    if 'averaged_files' in history:
        del history['averaged_files']

    history1 = []
    history1.append(copy.deepcopy(sasm1.getParameter('filename')))
    if 'averaged_files' in sasm1.getParameter('history'):
        history1.append({'averaged_files' : copy.deepcopy(sasm1.getParameter('history')['averaged_files'])})
    if 'subtraction' in sasm1.getParameter('history'):
        history1.append({'subtraction' : copy.deepcopy(sasm1.getParameter('history')['subtraction'])})

    history2 = []
    history2.append(copy.deepcopy(sasm2.getParameter('filename')))
    if 'averaged_files' in sasm2.getParameter('history'):
        history2.append({'averaged_files' : copy.deepcopy(sasm2.getParameter('history')['averaged_files'])})
    if 'subtraction' in sasm2.getParameter('history'):
        history2.append({'subtraction' : copy.deepcopy(sasm2.getParameter('history')['subtraction'])})

    history['subtraction'] = {'initial_file':history1, 'subtracted_file':history2}
     
    return newSASM 

def absorbance(sasm1, sasm2):
    ''' compute the absorbance of one SASM object from another  '''
    
    q1_min, q1_max = sasm1.getQrange()
    q2_min, q2_max = sasm2.getQrange()
    
    if len(sasm1.i[q1_min:q1_max]) != len(sasm2.i[q2_min:q2_max]):
        raise SASExceptions.DataNotCompatible('The curves does not have the same number of points.')
    
    i = np.log(sasm2.i[q2_min:q2_max] / sasm1.i[q1_min:q1_max])

    q = sasm1.q.copy()[q1_min:q1_max]
    
    err = i*0

    parameters = sasm1.getAllParameters().copy()    
    absSASM = SASM(i, q, err, parameters)
     
    return absSASM 

def average(sasm_list, forced = False):
    ''' Average the intensity of a list of sasm objects '''
    
    #Check average is possible with provided curves:
    first_sasm = sasm_list[0]
    first_q_min, first_q_max = first_sasm.getQrange()
    
    number_of_points = len(first_sasm.i[first_q_min:first_q_max])

    # print number_of_points
    
    for each in sasm_list:
        each_q_min, each_q_max = each.getQrange()
        # print each_q_min
        # print each_q_max
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
    
    avgSASM = SASM(avg_i, avg_q, avg_err, avg_parameters)
    history = avgSASM.getParameter('history')

    if 'subtraction' in history:
        del history['subtraction']

    history_list = []

    for eachsasm in sasm_list:
        each_history = []
        each_history.append(copy.deepcopy(eachsasm.getParameter('filename')))
        if 'averaged_files' in eachsasm.getParameter('history'):
            each_history.append({'averaged_files' : copy.deepcopy(eachsasm.getParameter('history')['averaged_files'])})
        if 'subtraction' in eachsasm.getParameter('history'):
            each_history.append({'subtraction' : copy.deepcopy(eachsasm.getParameter('history')['subtraction'])})
        history_list.append(each_history)


    history['averaged_files'] = history_list
    avgSASM.setParameter('history', history)
    
    return avgSASM

def addFilenamePrefix(sasm, prefix):
    ''' add prefix to the filename variable in the SASM parameters '''
    
    filename = sasm.getParameter('filename')
    sasm.setParameter('filename', prefix + filename)
    
    return sasm

def addFilenameSuffix(sasm, suffix):
    ''' add suffix to the filename variable in the SASM parameters '''
    
    filename, ext = os.path.splitext(sasm.getParameter('filename'))
    sasm.setParameter('filename', filename + suffix + ext)
    
    return sasm

def determineOutlierMinMax(data, sensitivity):
    ''' Determines the max and min borders for outliers using 
        interquantile range-based fences '''
            
    N = len(data)
    data_sorted = np.sort(data)
        
    P25_idx = round((25.0/100) * N)
    P75_idx = round((75.0/100) * (N-1))
        
    P25 = data_sorted[P25_idx]
    P75 = data_sorted[P75_idx]
        
    IQR = P75-P25
        
    min = P25 - (sensitivity * IQR)
    max = P75 + (sensitivity * IQR)
        
    return (min, max)

def removeZingersAndAverage(sasmList):
    pass


def calcAbsoluteScaleWaterConst(water_sasm, emptycell_sasm, I0_water, raw_settings):
    
    if emptycell_sasm == None or emptycell_sasm == 'None' or water_sasm == 'None' or water_sasm == None:
        raise SASExceptions.AbsScaleNormFailed('Empty cell file or water file was not found. Open options to set these files.')
    
    water_bgsub_sasm = subtract(water_sasm, emptycell_sasm) 
    
    water_avg_end_idx = int( len(water_bgsub_sasm.i) * 0.666 ) 
    water_avg_start_idx = int( len(water_bgsub_sasm.i) * 0.333 )

    avg_water = np.mean(water_bgsub_sasm.i[water_avg_start_idx : water_avg_end_idx]) 
    
    abs_scale_constant = I0_water / avg_water
    
    return abs_scale_constant

def normalizeAbsoluteScaleWater(sasm, raw_settings):
    abs_scale_constant = raw_settings.get('NormAbsWaterConst')
    sasm.scaleBinnedIntensity(abs_scale_constant)

    return sasm, abs_scale_constant

def postProcessImageSasm(sasm, raw_settings):
    
    if raw_settings.get('NormAbsWater'):
        try:
            normalizeAbsoluteScaleWater(sasm, raw_settings)
        except SASExceptions.AbsScaleNormFailed, e:
            print e

def postProcessSasm(sasm, raw_settings):
    
    if raw_settings.get('ZingerRemoval'):
        std = raw_settings.get('ZingerRemoveSTD')
        winlen = raw_settings.get('ZingerRemoveWinLen')
        start_idx = raw_settings.get('ZingerRemoveIdx')
        
        sasm.removeZingers(start_idx, winlen, std)
        
def superimpose(sasm_star, sasm_list):
    """
    Find the scale factors for a protein buffer pair that will best match a known standard curve.
    If I = I_prot - alf*I_buf, then find alf and bet such that
    ||(I_prot - alf*I_buf) - bet*I_std ||^2 is a minimum. This is a standard vector norm which gives the least squares minimum.
    The standard curve need not be sampled at the same q-space points.

    """
    
    q_star = sasm_star.q
    i_star = sasm_star.i
    err_star = sasm_star.err
    
    q_star_qrange_min, q_star_qrange_max = sasm_star.getQrange()
    
    for each_sasm in sasm_list:
    
        each_q = each_sasm.getBinnedQ()
        each_i = each_sasm.getBinnedI()
        each_err = each_sasm.getBinnedErr()
        
        each_q_qrange_min, each_q_qrange_max = each_sasm.getQrange()
    
        # resample standard curve on the data q vector
        min_q_star, min_q_each = q_star[q_star_qrange_min], each_q[each_q_qrange_min]
        max_q_star, max_q_each = q_star[q_star_qrange_max-1], each_q[each_q_qrange_max-1]
        
        min_q = min([min_q_star, min_q_each])
        max_q = min([max_q_star, max_q_each])
        
        min_q_idx = np.where(q_star >= min_q_each)[0][0]
        max_q_idx = np.where(q_star <= max_q_each)[0][-1]
        
        print min_q, max_q
        print min_q_idx, max_q_idx
        print each_q_qrange_min, each_q_qrange_max
                                                                                         
        I_resamp = np.interp(q_star[min_q_idx:max_q_idx+1], 
                             each_q[each_q_qrange_min:each_q_qrange_max-1],
                             each_i[each_q_qrange_min:each_q_qrange_max-1])

        #print I_resamp
        
        I_buf = np.ones(max_q_idx - min_q_idx + 1)
        
        g2 = np.dot(I_buf, I_buf)
        s2 = np.dot(i_star[min_q_idx:max_q_idx+1], i_star[min_q_idx:max_q_idx+1])
        
        gs = sg = np.dot(I_buf, i_star[min_q_idx:max_q_idx+1])
        
        fg = np.dot(I_resamp, I_buf)
        fs = np.dot(I_resamp, i_star[min_q_idx:max_q_idx+1])

        determ = g2*s2 - gs*sg
    
        alf = (fg*s2-fs*sg) / determ
        bet = (g2*fs-gs*fg) / determ
        
        offset = -alf
        scale = 1.0/bet
                
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
    parameters = {}
    newSASM = SASM(newi, newq, newerr, parameters)
    
    if len(sasm_list) == 0:
        return newSASM
    else:
        return merge(newSASM, sasm_list)

def interpolateToFit(sasm_star, sasm_list):
    s1 = sasm_star
    s2 = sasm_list[0]
      
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
    
    parameters = {}
    
    newSASM = SASM(intp_i_s2, intp_q_s2, newerr, parameters)
    
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
        no_of_bins = np.floor(bins[i] - bins[i-1])

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
    
    
