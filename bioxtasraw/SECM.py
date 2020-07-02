'''
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
'''
from __future__ import absolute_import, division, print_function, unicode_literals
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

        self.calcTime(sasm_list)

        if self.qref>0:
            I_of_q = np.array([sasm.getIofQ(self.qref) for sasm in sasm_list])
            self.I_of_q = np.concatenate((self.I_of_q, I_of_q))

        if self.qrange != (0,0):
            qrange_I = np.array([sasm.getIofQRange(self.qrange[0], self.qrange[1]) for sasm in sasm_list])
            self.qrange_I = np.concatenate((self.qrange_I, qrange_I))

        self.plot_frame_list = np.arange(len(self.frame_list))


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
        ''' Reset q, i and err to their original values '''

        self._scale_factor = 1
        self._offset_value = 0
        self._frame_scale_factor = 1
        self._q_range = None

        self._update()

    def setQrange(self, n_min, n_max):
        self._q_range = (n_min, n_max)

        self._update()

    def setSubQrange(self, n_min, n_max):
        self._sub_q_range = (n_min, n_max)

        self._update()

    def setBCSubQrange(self, n_min, n_max):
        self._bc_sub_q_range = (n_min, n_max)

        self._update()

    def getQrange(self):
        return self._q_range

    def getSubQrange(self):
        return self._sub_q_range

    def getBCSubQrange(self):
        return self._bc_sub_q_range

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

    def setScaleValues(self, scale_factor, offset_value, frame_scale_factor):

        self._scale_factor = scale_factor
        self._offset_value = offset_value
        self._frame_scale_factor = frame_scale_factor

    def extractAll(self):
        ''' extracts all data from the object and delivers it as a dict '''

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
        self.my_semaphore.acquire()

    def releaseSemaphore(self):
        self.my_semaphore.release()

    def averageFrames(self, range_list, series_type, sim_test, sim_thresh, sim_cor, forced=False):
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
