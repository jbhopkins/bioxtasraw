"""
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

The purpose of this module is to contain the report writer.

Much of the code is from the BioCAT SAXS pipeline source code, released here:
    https://github.com/biocatiit/saxs-pipeline
That code was released under GPL V3. The original author is Jesse Hopkins.

"""

from __future__ import absolute_import, division, print_function, unicode_literals
from builtins import object, range, map, zip
from io import open
import six

import collections
from collections import OrderedDict, defaultdict
import tempfile
import os
import copy

import numpy as np
import scipy.signal
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Table, Image,
    XPreformatted, KeepTogether, TableStyle)
import matplotlib as mpl
import matplotlib.pyplot as plt

import bioxtasraw.RAWAPI as raw
import bioxtasraw.SASCalc as SASCalc

# mpl.rc('font', size = 8.0, family='Arial')
# mpl.rc('legend', frameon=False, fontsize='medium')
# mpl.rc('axes', labelsize='medium', linewidth=1, facecolor='white',
#     axisbelow=False, labelpad=2.5, xmargin = 0.015, ymargin = 0.02)
# mpl.rc('xtick', labelsize='medium', top=True, direction='in')
# mpl.rc('ytick', labelsize='medium', right=True, direction='in')
# mpl.rc('lines', linewidth=1)
# mpl.rc('mathtext', default='regular')

# with mpl.rc_context({'font.size' : 8.0, 'font.family': 'Arial',
#     'legend.frameon': False, 'legend.fontsize': 'medium', 'axes.labelsize': 'medium',
#     'axes.linewidth': 1, 'axes.facecolor': 'white', 'axes.axisbelow': False,
#     'axes.labelpad': 2.5, 'axes.xmargin': 0.015, 'axes.ymargin': 0.02,
#     'xtick.labelsize' : 'medium', 'xtick.top' : True, 'xtick.direction' : 'in',
#     'ytick.labelsize' : 'medium', 'ytick.right' : True, 'ytick.direction' : 'in',
#     'lines.linewidth' : 1, 'mathtext.default': 'regular'}):

temp_files = []

##################### Contents of reports/utils.py #####################
def text_round(value, round_to):
    value = float(value)

    low_bound = 1./(10.**(round_to))

    if round_to > 1:
        high_bound = 1000./(10.**(round_to-1))
    else:
        high_bound = 1000

    if (value < low_bound and value != 0) or value > high_bound:
            value = str(np.format_float_scientific(value, round_to, trim='0',
            exp_digits=1))
    else:
        value = str(round(value, round_to))

    return value

def rotate_list(my_list):
    rot_list = []

    dim1 = len(my_list)
    dim2 = len(my_list[0])

    for j in range(dim2):
        data = []

        for k in range(dim1):
            data.append(my_list[k][j])

        rot_list.append(data)

    return rot_list


##################### Contents of reports/data.py #####################

GuinierData = collections.namedtuple('Guinier', ['Rg', 'I0', 'Rg_err',
    'I0_err', 'n_min', 'n_max', 'q_min', 'q_max', 'qRg_min', 'qRg_max', 'r_sq'],
    defaults=[-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1])

AbsMWData = collections.namedtuple('Abs_MW', ['MW', 'Buffer_density',
    'Protein_density', 'Partial_specific_volume'], defaults=[-1, -1, -1, -1])
I0MWData = collections.namedtuple('I0_MW', ['MW'], defaults=[-1])
VpMWData = collections.namedtuple('PV_MW', ['MW', 'Density', 'q_max',
    'Porod_volume_corrected', 'Porod_volume', 'cutoff'], defaults=[-1, -1, -1,
    -1, -1, ''])
VcMWData = collections.namedtuple('Vc_MW', ['MW', 'Type', 'q_max',
    'Volume_of_correlation', 'cutoff'], defaults=[-1, '', -1, -1, ''])
SSMWData = collections.namedtuple('Shape_and_size_MW', ['MW', 'Dmax', 'Shape'],
    defaults=[-1, -1, ''])
BayesMWData = collections.namedtuple('Bayes_MW', ['MW', 'Probability',
    'Confidence_interval_lower', 'Confidence_interval_upper',
    'Confidence_interval_probability'], defaults=[-1, -1, -1, -1, -1])

BIFTData = collections.namedtuple('BIFT', ['Dmax', 'Rg', 'I0', 'Dmax_err',
    'Rg_err', 'I0_err', 'Chi_sq', 'q_min', 'q_max', 'Evidence', 'log_alpha',
    'Evidence_err', 'log_alpha_err'], defaults=[-1, -1, -1, -1, -1, -1, -1,
    -1, -1, -1, -1, -1, -1])

GNOMData = collections.namedtuple('GNOM', ['Dmax', 'Rg', 'I0', 'Rg_err',
    'I0_err', 'Chi_sq', 'Total_estimate', 'Quality', 'q_min', 'q_max'],
    defaults=[-1, -1, -1, -1, -1, -1, -1, '', -1, -1])

Metadata = collections.namedtuple('Metadata', ['Sample_to_detector_distance',
    'Wavelength', 'Exposure_time', 'Exposure_period', 'Flow_rate', 'Detector',
    'Instrument', 'Absolute_scale', 'File_prefix', 'Date', 'RAW_version',
    'q_range', 'Experiment_type', 'Sample', 'Buffer', 'Temperature',
    'Loaded_volume', 'Concentration', 'Column', 'Mixer', 'Transmission',
    'Notes'], defaults=[-1, -1, -1, -1, -1, '', '', False, '', '', '', '',
    '', '', '', -1, -1, -1, '', '', -1, ''])

class SECData(object):
    """
    The goal of this class is to contain all of the information about a SEC
    experiment in a single python object, with easily accessible info.
    """

    _calib_trans = {
        'Sample-to-detector distance (mm)'  : 'Sample_to_detector_distance',
        'Sample_Detector_Distance'          : 'Sample_to_detector_distance',
        'Wavelength (A)'                    : 'Wavelength',
        'Wavelength'                        : 'Wavelength',
        }

    _counters_trans = {
        'Flow rate (ml/min)'            : 'Flow_rate',
        'LC_flow_rate_mL/min'           : 'Flow_rate',
        'Exposure time/frame (s)'       : 'Exposure_time',
        'Exposure_time/frame_s'         : 'Exposure_time',
        'Exposure_period/frame_s'       : 'Exposure_period',
        'Instrument'                    : 'Instrument',
        'File_prefix'                   : 'File_prefix',
        'Date'                          : 'Date',
        'Experiment_type'               : 'Experiment_type',
        'Sample'                        : 'Sample',
        'Buffer'                        : 'Buffer',
        'Temperature_C'                 : 'Temperature',
        'Loaded_volume_uL'              : 'Loaded_volume',
        'Concentration_mg/ml'           : 'Concentration',
        'Column'                        : 'Column',
        'Mixer'                         : 'Mixer',
        'Nominal_Transmission_12_keV'   : 'Transmission',
        'Notes'                         : 'Notes',
        }

    _metadata_trans = {
        'Detector'  : 'Detector',
        }

    def __init__(self, secm):
        """
        Takes as input a RAW SECM object, and extracts parameters from there.
        """

        self.filename = secm.getParameter('filename')

        self.buffer_range = secm.buffer_range
        self.sample_range = secm.sample_range
        self.baseline_start_range = secm.baseline_start_range
        self.baseline_end_range = secm.baseline_end_range
        self.baseline_type = secm.baseline_type

        self.rg = secm.rg_list
        self.rg_err = secm.rger_list
        self.i0 = secm.i0_list
        self.i0_err = secm.i0er_list
        self.vpmw = secm.vpmw_list
        self.vcmw = secm.vcmw_list
        self.vcmw_err = secm.vcmwer_list

        self.has_calc_data = secm.calc_has_data

        self.time = secm.time
        self.frames = secm.plot_frame_list

        if secm.baseline_subtracted_sasm_list:
            self.total_i = secm.total_i_bcsub
            self.mean_i = secm.mean_i_bcsub

            self.baseline_corrected = True
            self.subtracted = True
        elif secm.subtracted_sasm_list:
            self.total_i = secm.total_i_sub
            self.mean_i = secm.mean_i_sub

            self.baseline_corrected = False
            self.subtracted = True
        else:
            self.total_i = secm.total_i
            self.mean_i = secm.mean_i

            self.baseline_corrected = False
            self.subtracted = False

        self.get_metadata(secm)
        self.get_efa_data(secm)
        self.get_regals_data(secm)

    def get_metadata(self, secm):
        metadata_dict = {}

        first_prof = secm.getSASM(0)

        all_params = first_prof.getAllParameters()

        metadata_dict = {}

        if 'calibration_params' in all_params:
            calibration_params = first_prof.getParameter('calibration_params')

            for key, value in self._calib_trans.items():
                if key in calibration_params:
                    metadata_dict[value] = calibration_params[key]

        if 'counters' in all_params:
            counters = first_prof.getParameter('counters')

            for key, value in self._counters_trans.items():
                if key in counters:
                    metadata_dict[value] = counters[key]

        if 'metadata' in all_params:
            metadata = first_prof.getParameter('metadata')

            for key, value in self._metadata_trans.items():
                if key in metadata:
                    metadata_dict[value] = metadata[key]

        if 'normalizations' in all_params:
            normalizations = first_prof.getParameter('normalizations')

            if 'Absolute_scale' in normalizations:
                metadata_dict['Absolute_scale'] = True

        if 'raw_version' in all_params:
            metadata_dict['RAW_version'] = all_params['raw_version']

        q_i = first_prof.getQ()[0]
        q_f = first_prof.getQ()[-1]
        metadata_dict['q_range'] = '{} to {}'.format(text_round(q_i, 4),
            text_round(q_f, 2))

        self.metadata = Metadata(**metadata_dict)

    def get_efa_data(self, secm):
        analysis_dict = secm.getParameter('analysis')

        if 'efa' in analysis_dict:
            efa_dict = analysis_dict['efa']

            self.efa_done = True
            self.efa_ranges = efa_dict['ranges']
            self.efa_start = efa_dict['fstart']
            self.efa_end = efa_dict['fend']
            self.efa_nsvs = efa_dict['nsvs']
            self.efa_iter_limit = efa_dict['iter_limit']
            self.efa_method = efa_dict['method']
            self.efa_profile_type = efa_dict['profile']
            self.efa_tolerance = efa_dict['tolerance']
            self.efa_frames = list(range(int(self.efa_start), int(self.efa_end)+1))

            if self.efa_profile_type == 'Subtracted':
                prof_type = 'sub'
            elif self.efa_profile_type == 'Unsubtracted':
                prof_type = 'unsub'
            elif self.efa_profile_type == 'Basline Corrected':
                prof_type = 'baseline'

            efa_results = run_efa_for_report(secm, self.efa_ranges, prof_type,
                int(self.efa_start), int(self.efa_end), self.efa_method,
                int(self.efa_iter_limit), float(self.efa_tolerance))

            if efa_results[1]:
                self.efa_extra_data = True
                self.efa_profiles = [SAXSData(prof) for prof in efa_results[0]]
                self.efa_conc = efa_results[3]['C']
                self.efa_chi = efa_results[3]['chisq']
            else:
                self.efa_extra_data = False
                self.efa_profiles = []
                self.efa_conc = []
                self.efa_chi = ''

        else:
            self.efa_done = False
            self.efa_ranges = []
            self.efa_start = ''
            self.efa_end = ''
            self.efa_nsvs = ''
            self.efa_iter_limit = ''
            self.efa_method = ''
            self.efa_profile_type = ''
            self.efa_tolerance = ''
            self.efa_frames = []
            self.efa_extra_data = False
            self.efa_profiles = []
            self.efa_conc = []
            self.efa_chi = ''

    def get_regals_data(self, secm):
        analysis_dict = secm.getParameter('analysis')

        if 'regals' in analysis_dict:
            regals_dict = analysis_dict['regals']

            self.regals_done = True
            self.regals_ranges = regals_dict['ranges']
            self.regals_frame_ranges = regals_dict['frame_ranges']
            self.regals_start = int(regals_dict['fstart'])
            self.regals_end = int(regals_dict['fend'])
            self.regals_nsvs = regals_dict['nsvs']
            self.regals_component_settings = regals_dict['component_settings']
            self.regals_run_settings = regals_dict['run_settings']
            self.regals_exp_type = regals_dict['exp_type']
            self.regals_profile_type = regals_dict['profile']

            if 'background_components' in regals_dict:
                self.regals_background_comps = regals_dict['background_components']
            else:
                self.regals_background_comps = ''

            if 'x_calibration' in regals_dict:
                self.regals_x_cal = np.array(regals_dict['x_calibration']['x'])
                self.regals_x_type = regals_dict['x_calibration']['x_choice']
            else:
                self.regals_x_cal = np.arange(self.regals_start, self.regals_end+1)
                self.regals_x_type = 'X'

            if self.regals_profile_type == 'Subtracted':
                prof_type = 'sub'
            elif self.regals_profile_type == 'Unsubtracted':
                prof_type = 'unsub'
            elif self.regals_profile_type == 'Basline Corrected':
                prof_type = 'baseline'

            regals_results = run_regals_for_report(secm, self.regals_component_settings,
                prof_type, int(self.regals_start), int(self.regals_end), self.regals_x_cal,
                self.regals_run_settings['min_iter'], self.regals_run_settings['max_iter'],
                self.regals_run_settings['tol'], self.regals_run_settings['conv_type'])

            self.regals_extra_data = True
            self.regals_profiles = [SAXSData(prof) for prof in regals_results[0]]

            self.regals_ifts = []
            for ift in regals_results[1]:
                if ift is None:
                    self.regals_ifts.append(None)
                else:
                    self.regals_ifts.append(IFTData(ift))

            self.regals_chi = np.mean(regals_results[6] ** 2, 0)
            self.regals_conc = regals_results[2]
            self.regals_reg_conc = regals_results[3]

        else:
            self.regals_done = False
            self.regals_ranges = []
            self.regals_frame_ranges = []
            self.regals_start = ''
            self.regals_end = ''
            self.regals_nsvs = ''
            self.regals_component_settings = []
            self.regals_run_settings = {}
            self.regals_background_comps = ''
            self.regals_exp_type = ''
            self.regals_profile_type = ''

            self.regals_extra_data = False
            self.regals_profiles = []
            self.regals_ifts = []
            self.regals_conc = []
            self.regals_reg_conc = []
            self.regals_chi = ''


class SAXSData(object):
    """
    The goal of this class is to contain all the information about a single
    SAXS scattering profile in a single python object, with easily accessible
    info.
    """

    # Left side is key in RAW sasm analysis dict, right side is key in data namedtuple
    _guinier_trans = {
        'Rg'        : 'Rg',
        'I0'        : 'I0',
        'Rg_err'    : 'Rg_err',
        'I0_err'    : 'I0_err',
        'nStart'    : 'n_min',
        'nEnd'      : 'n_max',
        'qStart'    : 'q_min',
        'qEnd'      : 'q_max',
        'qRg_min'   : 'qRg_min',
        'qRg_max'   : 'qRg_max',
        'rsq'       : 'r_sq',
        }

    _absmw_trans = {
        'MW'                        : 'MW',
        'Density_buffer'            : 'Buffer_density',
        'Density_dry_protein'       : 'Protein_density',
        'Partial_specific_volume'   : 'Partial_specific_volume',
        }

    _i0mw_trans = {
        'MW'    : 'MW',
        }

    _vpmw_trans = {
        'MW'                : 'MW',
        'Density'           : 'Density',
        'Q_max'             : 'q_max',
        'VPorod_Corrected'  : 'Porod_volume_corrected',
        'VPorod'            : 'Porod_volume',
        'Cutoff'            : 'cutoff'
        }

    _vcmw_trans = {
        'MW'        : 'MW',
        'Type'      : 'Type',
        'Q_max'     : 'q_max',
        'Vcor'      : 'Volume_of_correlation',
        'Cutoff'    : 'cutoff',
        }

    _ssmw_trans = {
        'MW'    : 'MW',
        'Dmax'  : 'Dmax',
        'Shape' : 'Shape',
        }

    _bayesmw_trans = {
        'MW'                            : 'MW',
        'MWProbability'                 : 'Probability',
        'ConfidenceIntervalLower'       : 'Confidence_interval_lower',
        'ConfidenceIntervalUpper'       : 'Confidence_interval_upper',
        'ConfidenceIntervalProbability' : 'Confidence_interval_probability',
        }

    _mw_trans = collections.OrderedDict([
        ('Absolute',            'Absolute'),
        ('I(0)Concentration',   'Reference'),
        ('PorodVolume',         'Porod_volume'),
        ('VolumeOfCorrelation', 'Volume_of_correlation'),
        ('ShapeAndSize',        'Shape_and_size'),
        ('DatmwBayes',          'Bayesian'),
        ])

    _mw_methods = {
        'Absolute'              : (_absmw_trans, AbsMWData),
        'Reference'             : (_i0mw_trans, I0MWData),
        'Porod_volume'          : (_vpmw_trans, VpMWData),
        'Volume_of_correlation' : (_vcmw_trans, VcMWData),
        'Shape_and_size'        : (_ssmw_trans, SSMWData),
        'Bayesian'              : (_bayesmw_trans, BayesMWData),
        }

    _bift_trans = {
        'Dmax'              : 'Dmax',
        'Real_Space_Rg'     : 'Rg',
        'Real_Space_I0'     : 'I0',
        'Dmax_Err'          : 'Dmax_err',
        'Real_Space_Rg_Err' : 'Rg_err',
        'Real_Space_I0_Err' : 'I0_err',
        'ChiSquared'        : 'Chi_sq',
        'qStart'            : 'q_min',
        'qEnd'              : 'q_max',
        'Evidence'          : 'Evidence',
        'LogAlpha'          : 'log_alpha',
        'Evidence_Err'      : 'Evidence_err',
        'LogAlpha_Err'      : 'log_alpha_err',
        }

    _gnom_trans = {
        'Dmax'                      : 'Dmax',
        'Real_Space_Rg'             : 'Rg',
        'Real_Space_I0'             : 'I0',
        'Real_Space_Rg_Err'         : 'Rg_err',
        'Real_Space_I0_Err'         : 'I0_err',
        'GNOM_ChiSquared'           : 'Chi_sq',
        'Total_Estimate'            : 'Total_estimate',
        'GNOM_Quality_Assessment'   : 'Quality',
        'qStart'                    : 'q_min',
        'qEnd'                      : 'q_max',
        }

    _calib_trans = {
        'Sample-to-detector distance (mm)'  : 'Sample_to_detector_distance',
        'Sample_Detector_Distance'          : 'Sample_to_detector_distance',
        'Wavelength (A)'                    : 'Wavelength',
        'Wavelength'                        : 'Wavelength',
        }

    _counters_trans = {
        'Flow rate (ml/min)'            : 'Flow_rate',
        'LC_flow_rate_mL/min'           : 'Flow_rate',
        'Exposure time/frame (s)'       : 'Exposure_time',
        'Exposure_time/frame_s'         : 'Exposure_time',
        'Exposure_period/frame_s'       : 'Exposure_period',
        'Instrument'                    : 'Instrument',
        'File_prefix'                   : 'File_prefix',
        'Date'                          : 'Date',
        'Experiment_type'               : 'Experiment_type',
        'Sample'                        : 'Sample',
        'Buffer'                        : 'Buffer',
        'Temperature_C'                 : 'Temperature',
        'Loaded_volume_uL'              : 'Loaded_volume',
        'Concentration_mg/ml'           : 'Concentration',
        'Column'                        : 'Column',
        'Mixer'                         : 'Mixer',
        'Nominal_Transmission_12_keV'   : 'Transmission',
        'Notes'                         : 'Notes',
        }

    _metadata_trans = {
        'Detector'  : 'Detector',
        }


    def __init__(self, sasm):
        """
        Takes as input a RAW SASM object, and extracts parameters from there.
        """
        self.filename = sasm.getParameter('filename')

        self.q = sasm.getQ()
        self.i = sasm.getI()
        self.err = sasm.getErr()

        all_params = sasm.getAllParameters()

        if 'analysis' in all_params:
            self._analysis_data = sasm.getParameter('analysis')
        else:
            self._analysis_data = {}

        if 'history' in all_params:
            self._history_data = sasm.getParameter('history')
        else:
            self._history_data = {}

        if 'counters' in all_params:
            self._counters_data = sasm.getParameter('counters')
        else:
            self._counters_data = {}

        if 'calibration_params' in all_params:
            self._calibration_data = sasm.getParameter('calibration_params')
        else:
            self._calibration_data = {}

        if 'metadata' in all_params:
            self._metadata = sasm.getParameter('metadata')
        else:
            self._metadata = {}

        if 'normalizations' in all_params:
            self._normalization_data = sasm.getParameter('normalizations')
        else:
            self._normalization_data = {}

        self._extract_analysis_data()
        self._extract_metadata(all_params)

    def _extract_analysis_data(self):
        """
        Extracts data from the sasm analysis dictionary into sets of named tuples
        defined at the top of this method.

        If you want to add more modify data types, add or modify the appropriate
        named tuple, and then add or modify the translation method in the class
        definition, such as _guinier_trans. This should transparently handle
        missing keys by setting the value to -1 or ''.
        """

        # Grab Guinier data
        data_dict = {}

        if 'guinier' in self._analysis_data:
            guinier_analysis = self._analysis_data['guinier']

            for key, value in self._guinier_trans.items():
                if key in guinier_analysis:
                    val = guinier_analysis[key]

                    if key != 'nStart' and key != 'nEnd':
                        val = float(val)
                    else:
                        val = int(val)

                    data_dict[value] = val

        self.guinier_data = GuinierData(**data_dict)

        #Grab MW data
        self.mw_data = collections.OrderedDict()

        for key, value in self._mw_trans.items():
            trans_dict, data_method = self._mw_methods[value]

            data_dict = {}

            if 'molecularWeight' in self._analysis_data:
                mw_analysis = self._analysis_data['molecularWeight']

                if key in mw_analysis:
                    for data_key, data_item in trans_dict.items():
                        if data_key in mw_analysis[key]:
                            data_dict[data_item] = mw_analysis[key][data_key]

            data_tuple = data_method(**data_dict)

            self.mw_data[value] = data_tuple

        # Grab BIFT data
        data_dict = {}

        if 'BIFT' in self._analysis_data:
            bift_analysis = self._analysis_data['BIFT']

            for key, value in self._bift_trans.items():
                if key in bift_analysis:
                    data_dict[value] = float(bift_analysis[key])

        self.bift_data = BIFTData(**data_dict)

        # Grab GNOM data
        data_dict = {}

        if 'GNOM' in self._analysis_data:
            gnom_analysis = self._analysis_data['GNOM']

            for key, value in self._gnom_trans.items():
                if key in gnom_analysis:
                    val = gnom_analysis[key]

                    if key != 'GNOM_Quality_Assessment':
                        val = float(val)

                    data_dict[value] = val

        self.gnom_data = GNOMData(**data_dict)


    def _extract_metadata(self, all_params):
        """
        Extracts metadata from the sasm header, calibration_params, metadata,
        and normalizations dictionaries into a named tuple defined at the
        top of the method.

        See _extract_analysis_data for how to modify what's read in.
        """
        metadata_dict = {}

        for key, value in self._calib_trans.items():
            if key in self._calibration_data:
                metadata_dict[value] = self._calibration_data[key]

        for key, value in self._counters_trans.items():
            if key in self._counters_data:
                metadata_dict[value] = self._counters_data[key]

        for key, value in self._metadata_trans.items():
            if key in self._metadata:
                metadata_dict[value] = self._metadata[key]

        if 'Absolute_scale' in self._normalization_data:
            metadata_dict['Absolute_scale'] = True

        if 'raw_version' in all_params:
            metadata_dict['RAW_version'] = all_params['raw_version']

        q_i = self.q[0]
        q_f = self.q[-1]
        metadata_dict['q_range'] = '{} to {}'.format(text_round(q_i, 4),
            text_round(q_f, 2))

        self.metadata = Metadata(**metadata_dict)

class IFTData(object):
    """
    The goal of this class is to contain all the information about a IFT
    in a single python ojbect, with easily accessible info.
    """

    def __init__(self, iftm):
        """
        Takes as input a RAW IFTM object, and extracts parameters from there.
        """

        self.filename = iftm.getParameter('filename')

        self.r = iftm.r
        self._p_orig = iftm.p
        self._p_err_orig = iftm.err

        self.q = iftm.q_orig
        self.i = iftm.i_orig
        self.i_err = iftm.err_orig

        self.i_fit = iftm.i_fit

        self.q_extrap = iftm.q_extrap
        self.i_extrap = iftm.i_extrap

        self.dmax = iftm.getParameter('dmax')
        self.rg = iftm.getParameter('rg')
        self.i0 = iftm.getParameter('i0')
        self.rg_err = iftm.getParameter('rger')
        self.i0_err = iftm.getParameter('i0er')
        self.chi_sq = iftm.getParameter('chisq')

        self.type = iftm.getParameter('algorithm')

        if self.type == 'BIFT':
            self.dmax_err = iftm.getParameter('dmaxer')
        elif self.type == 'GNOM':
            self.total_estimate = iftm.getParameter('TE')
            self.quality = iftm.getParameter('quality')

        self.p = self._p_orig/self.i0
        self.p_err = self._p_err_orig/self.i0

        self.a_score = -1
        self.a_cats = -1
        self.a_interp = ''

        self.metadata = Metadata()

class EFAData(object):
    """
    Contains information about EFA that's not contained within the series analysis
    dictionary.
    """

    def __init__(self, frames, conc, chi, forward_efa, backward_efa):
        self.frames = frames
        self.conc = conc
        self.chi = chi
        self.forward_efa = forward_efa
        self.backward_efa = backward_efa
        self.n_svals = self.conc.shape[1]

class DammifData(object):
    """
    Contains information about DAMMIF run from the .csv file RAW saves.
    """

    def __init__(self, prefix, program, mode, sym, aniso, num, damaver,
        damclust, refined, nsd, nsd_std, included, res, res_err, clusters,
        rep_model):

        self.prefix = prefix
        self.program = program
        self.mode = mode
        self.sym = sym
        self.aniso = aniso
        self.num = num
        self.damaver = damaver
        self.damclust = damclust
        self.refined = refined
        self.nsd = nsd
        self.nsd_std = nsd_std
        self.included = included
        self.res = res
        self.res_err = res_err
        self.clusters = clusters
        self.rep_model = rep_model

class DenssDat(object):
    """
    Contains information about DENSS run from the .csv file RAW saves.
    """

    def __init__(self, prefix, mode, sym, sym_axis, sym_factor, num, average,
        refined, rsc, rsc_std, included, res):

        self.prefix = prefix
        self.mode = mode
        self.sym = sym
        self.sym_axis = sym_axis
        self.sym_factor = sym_factor
        self.num = num
        self.average = average
        self.refined = refined
        self.rsc = rsc
        self.rsc_std = rsc_std
        self.included = included
        self.res = res


def parse_efa_file(filename):
    with open(filename, 'r') as f:
        data = f.readlines()

    conc_idx = -1
    chi_idx = -1
    fwd_idx = -1
    bck_idx = -1
    svd_idx = -1

    for j, line in enumerate(data):
        if 'Concentration Matrix' in line:
            conc_idx = j

        elif 'Rotation Chi^2' in line:
            chi_idx = j

        elif 'Forward EFA Results' in line:
            fwd_idx = j

        elif 'Backward EFA Results' in line:
            bck_idx = j

        elif 'Singular Value Results' in line:
            svd_idx = j

    if conc_idx >= 0 and chi_idx >=0:
        conc_data = data[conc_idx+2:chi_idx-1]
    else:
        conc_data = []

    if chi_idx >=0 and fwd_idx >=0:
        chi_data =data[chi_idx+2:fwd_idx-1]
    else:
        chi_data = []

    if fwd_idx >=0 and bck_idx >=0:
        fwd_data =data[fwd_idx+2:bck_idx-1]
    else:
        fwd_data = []

    if bck_idx >=0 and svd_idx >=0:
        bck_data =data[bck_idx+2:svd_idx-1]
    else:
        bck_data = []

    frames = []
    conc = []
    chi = []
    fwd = []
    bck = []

    for line in conc_data:
        data = line.split(',')
        frame = int(float(data[0]))
        temp_data= list(map(float, data[1:]))

        frames.append(frame)
        conc.append(temp_data)

    frames = np.array(frames)
    conc = np.array(conc)

    for line in chi_data:
        data = line.split(',')
        temp_data= float(data[1])

        chi.append(temp_data)

    chi = np.array(chi)

    for line in fwd_data:
        data = line.split(',')
        temp_data= list(map(float, data[1:]))
        fwd.append(temp_data)

    fwd = np.array(fwd)

    for line in bck_data:
        data = line.split(',')
        temp_data= list(map(float, data[1:]))

        bck.append(temp_data)

    bck = np.array(bck)

    efa_data = EFAData(frames, conc, chi, fwd, bck)

    return efa_data


def parse_dammif_file(filename, data=None):

    if filename is not None:
        with open(filename, 'r') as f:
            data = f.readlines()

    prefix = ''
    program = ''
    mode = ''
    sym = ''
    aniso = ''
    num = -1
    damaver = False
    damclust = False
    refined = False
    nsd = -1
    nsd_std = -1
    included = -1
    res = -1
    res_err = -1
    clusters = -1
    rep_model = -1

    for line in data:
        if 'Program used' in line:
            program = line.split(':')[-1].strip()
        elif 'Mode:' in line:
            mode = line.split(':')[-1].strip()
        elif 'Symmetry' in line:
            sym = line.split(':')[-1].strip()
        elif 'Anisometry' in line:
            aniso = line.split(':')[-1].strip()
        elif 'Total number' in line:
            num = int(line.split(':')[-1].strip())
        elif 'Used DAMAVER' in line:
            damaver = (line.split(':')[-1].strip() == 'True')
        elif 'Refined with DAMMIN' in line:
            refined = (line.split(':')[-1].strip() == 'True')
        elif 'Used DAMCLUST' in line:
            damclust = (line.split(':')[-1].strip() == 'True')
        elif 'Mean NSD' in line:
            nsd = float(line.split(':')[-1].strip())
        elif 'Stdev. NSD' in line:
            nsd_std = float(line.split(':')[-1].strip())
        elif 'DAMAVER Included' in line:
            included = int(line.split(':')[-1].strip().split(' ')[0].strip())
        elif 'Representative mode' in line:
            rep_model = int(line.split(':')[-1].strip())
        elif 'Ensemble resolution' in line:
            res_data = line.split(':')[-1].strip()
            res = float(res_data.split('+')[0].strip())
            res_err = float(res_data.split('-')[1].strip().split(' ')[0].strip())
        elif 'Number of clusters' in line:
            clusters = int(line.split(':')[-1].strip())
        elif 'Output prefix' in line:
            prefix = line.split(':')[-1].strip()

    dammif_data = DammifData(prefix, program, mode, sym, aniso, num, damaver,
        damclust, refined, nsd, nsd_std, included, res, res_err, clusters,
        rep_model)

    return dammif_data

def parse_denss_file(filename, data=None):

    if filename is not None:
        with open(filename, 'r') as f:
            data = f.readlines()

    prefix = ''
    mode = ''
    sym = ''
    sym_factor = -1
    sym_axis = ''
    num = -1
    average = False
    refined = False
    rsc = -1
    rsc_std = -1
    included = -1
    res = -1

    for line in data:
        if 'Mode:' in line:
            mode = line.split(':')[-1].strip()
        elif 'Symmetry applied' in line:
            sym = line.split(':')[-1].strip()
        elif 'N-fold' in line:
            sym_factor = int(line.split(':')[-1].strip())
        elif 'Symmetry axis' in line:
            sym_axis = line.split(':')[-1].strip()
        elif 'Total number' in line:
            num = int(line.split(':')[-1].strip())
        elif 'Averaged' in line:
            average = (line.split(':')[-1].strip() == 'True')
        elif 'Refined:' in line:
            refined = (line.split(':')[-1].strip() == 'True')
        elif 'Mean RSC' in line:
            rsc = float(line.split(':')[-1].strip())
        elif 'Stdev. RSC' in line:
            rsc_std = float(line.split(':')[-1].strip())
        elif 'Number of models included' in line:
            included = int(line.split(':')[-1].strip().split(' ')[0].strip())
        elif 'Correlation Resolution' in line:
            res = float(line.split(':')[-1].strip())
        elif 'Output prefix' in line:
            prefix = line.split(':')[-1].strip()

    denss_data = DenssDat(prefix, mode, sym, sym_axis, sym_factor, num, average,
        refined, rsc, rsc_std, included, res)

    return denss_data


##################### Contents of reports/plots.py #####################

def make_patch_spines_invisible(ax):
    # from https://matplotlib.org/examples/pylab_examples/multiple_yaxis_with_spines.html
    ax.set_frame_on(True)
    ax.patch.set_visible(False)
    for sp in ax.spines.values():
        sp.set_visible(False)

class overview_plot(object):
    """
    Makes an overview plot with up to 5 panels. a) Series intensity and rg.
    b) Log-lin profiles. c) Guinier fits. d) Normalized Kratky profiles. e) P(r).
    Plot generated depends on what data is input.
    """

    def __init__(self, profiles, ifts, series, int_type='Total',
        series_data='Rg', img_width=6, img_height=6):
        with mpl.rc_context({'font.size' : 8.0, 'font.family': 'Arial',
            'legend.frameon': False, 'legend.fontsize': 'medium', 'axes.labelsize': 'medium',
            'axes.linewidth': 1, 'axes.facecolor': 'white', 'axes.axisbelow': False,
            'axes.labelpad': 2.5, 'axes.xmargin': 0.015, 'axes.ymargin': 0.02,
            'xtick.labelsize' : 'medium', 'xtick.top' : True, 'xtick.direction' : 'in',
            'ytick.labelsize' : 'medium', 'ytick.right' : True, 'ytick.direction' : 'in',
            'lines.linewidth' : 1, 'mathtext.default': 'regular'}):

            self.profiles = profiles
            self.ifts = ifts
            self.series = series

            self.int_type = int_type
            self.series_data = series_data

            if len(profiles) > 0:
                has_profiles = True

                has_rg = any([prof.guinier_data.Rg > 0 and prof.guinier_data.I0 > 0 for prof in profiles])
            else:
                has_profiles = False
                has_rg = False

            if len(ifts) > 0:
                has_ifts = True
            else:
                has_ifts = False

            if len(series) > 0:
                has_series = True
            else:
                has_series = False

            self.figure = plt.figure(figsize=(img_width, img_height))

            if has_profiles and has_rg and has_ifts and has_series:
                self.gs = self.figure.add_gridspec(3, 2)

                self._make_series_plot('a')
                self._make_profile_plot('b')
                self._make_guinier_plot('c')
                self._make_kratky_plot('d')
                self._make_ift_plot('e')

                self.figure.subplots_adjust(left=0.1, right=0.90, wspace=0.3,
                    bottom=0.07, top=0.98, hspace=0.3)

            elif has_profiles and has_rg and has_ifts and not has_series:
                self.gs = self.figure.add_gridspec(2, 2)

                self._make_profile_plot('a', row=0)
                self._make_guinier_plot('b', row=0)
                self._make_kratky_plot('c', row=1)
                self._make_ift_plot('d', row=1)

                self.figure.subplots_adjust(left=0.1, right=0.97, wspace=0.3,
                    bottom=0.09, top=0.96, hspace=0.3)

            elif has_profiles and has_rg and not has_ifts and has_series:
                self.gs = self.figure.add_gridspec(3, 2)

                self._make_series_plot('a')
                self._make_profile_plot('b', row=1, span=True)
                self._make_guinier_plot('c', row=2, column=0)
                self._make_kratky_plot('d', row=2, column=1)

                self.figure.subplots_adjust(left=0.1, right=0.90, wspace=0.3,
                    bottom=0.07, top=0.98, hspace=0.3)

            elif has_profiles and has_rg and not has_ifts and not has_series:
                self.gs = self.figure.add_gridspec(2, 2)

                self._make_profile_plot('a', row=0, span=True)
                self._make_guinier_plot('b', row=1, column=0)
                self._make_kratky_plot('c', row=1, column=1)

                self.figure.subplots_adjust(left=0.1, right=0.97, wspace=0.3,
                    bottom=0.10, top=0.97, hspace=0.3)

            elif has_profiles and not has_rg and has_ifts and has_series:
                self.gs = self.figure.add_gridspec(2, 2)

                self._make_series_plot('a')
                self._make_profile_plot('b')
                self._make_ift_plot('e', row=1, column=1)

                self.figure.subplots_adjust(left=0.1, right=0.90, wspace=0.3,
                    bottom=0.09, top=0.98, hspace=0.3)

            elif has_profiles and not has_rg and has_ifts and not has_series:
                self.gs = self.figure.add_gridspec(1, 2)

                self._make_profile_plot('a', row=0)
                self._make_ift_plot('b', row=0, column=1)

                self.figure.subplots_adjust(left=0.1, right=0.97, wspace=0.3,
                    bottom=0.18, top=0.96, hspace=0.3)

            elif has_profiles and not has_rg and not has_ifts and has_series:
                self.gs = self.figure.add_gridspec(2, 2)

                self._make_series_plot('a')
                self._make_profile_plot('b', row=1, span=True)

                self.figure.subplots_adjust(left=0.1, right=0.90, wspace=0.3,
                    bottom=0.09, top=0.98, hspace=0.3)

            elif has_profiles and not has_rg and not has_ifts and not has_series:
                self.gs = self.figure.add_gridspec(1, 2)

                self._make_profile_plot('', row=0, span=True)

                self.figure.subplots_adjust(left=0.1, right=0.97, wspace=0.3,
                    bottom=0.17, top=0.98, hspace=0.3)

            elif not has_profiles and has_ifts and has_series:
                self.gs = self.figure.add_gridspec(2, 2)

                self._make_series_plot('a')
                self._make_ift_plot('b', row=1, span=True)

                self.figure.subplots_adjust(left=0.1, right=0.90, wspace=0.3,
                    bottom=0.09, top=0.97, hspace=0.3)

            elif not has_profiles and not has_ifts and has_series:
                self.gs = self.figure.add_gridspec(1, 2)

                self._make_series_plot('')

                self.figure.subplots_adjust(left=0.1, right=0.90, wspace=0.3,
                    bottom=0.15, top=0.98, hspace=0.3)

            elif not has_profiles and has_ifts and not has_series:
                self.gs = self.figure.add_gridspec(1, 2)

                self._make_ift_plot('', row=0, span=True)

                self.figure.subplots_adjust(left=0.1, right=0.97, wspace=0.3,
                    bottom=0.17, top=0.98, hspace=0.3)


    def _make_series_plot(self, label, row=0):
        ax = self.figure.add_subplot(self.gs[row, :])
        ax2 = ax.twinx()

        ax.spines["right"].set_visible(False)
        make_patch_spines_invisible(ax2)
        ax2.spines["right"].set_visible(True)

        lines = []

        ax.axhline(0, 0, 1, linewidth=1.0, color='k')

        for series in self.series:
            x_data = series.frames

            if self.int_type == 'Total':
                y_data = series.total_i
            elif self.int_type == 'Mean':
                y_data = series.mean_i

            if series.has_calc_data:
                if self.series_data == 'Rg':
                    y2_data = series.rg
                elif self.series_data == 'I0':
                    y2_data = series.i0
                elif self.series_data == 'MW_Vc':
                    y2_data = series.vcmw
                elif self.series_data == 'MW_Vp':
                    y2_data = series.vpmw

            line, = ax.plot(x_data, y_data, '-', label=series.filename)

            lines.append(line)

            if series.has_calc_data:
                line2, = ax2.plot(x_data[y2_data>0], y2_data[y2_data>0], 'o',
                    label='{} {}'.format(series.filename, self.series_data),
                    markersize=1)

                lines.append(line2)

        if len(self.series) == 1:
            series = self.series[0]

            int_line = lines[0]
            ax.yaxis.label.set_color(int_line.get_color())
            ax.tick_params(axis='y', colors=int_line.get_color())
            ax.spines['left'].set_color(int_line.get_color())

            calc_color = '#D7191C'

            if series.has_calc_data:
                calc_line = lines[-1]
                calc_line.set_markerfacecolor(calc_color)
                calc_line.set_markeredgecolor(calc_color)

                ax2.yaxis.label.set_color(calc_color)
                ax2.tick_params(axis='y', colors=calc_color)
                ax2.spines['right'].set_color(calc_color)


            if series.buffer_range:
                for buf in series.buffer_range:
                    ax.axvspan(buf[0], buf[1], color='#2ca02c', alpha=0.5)

            if series.sample_range:
                for sam in series.sample_range:
                    ax.axvspan(sam[0], sam[1], color='#B879CB', alpha=0.5)


        labels = [l.get_label() for l in lines]

        if len(self.series) > 1:
            ax.legend(lines, labels, fontsize='small')

        ax.set_xlabel('Frames')

        ax.set_ylabel('{} Intensity [Arb.]'.format(self.int_type))

        if self.series_data == 'Rg':
            ax2.set_ylabel('Rg')
        elif self.series_data == 'I0':
            ax2.set_ylabel('I(0)')
        elif self.series_data == 'MW_Vc':
            ax2.set_ylabel('MW (Vc) [kDa]')
        elif self.series_data == 'MW_Vp':
            ax2.set_ylabel('MW (Vp) [kDa]')

        ax.text(-0.05, 1.0, label, transform = ax.transAxes, fontweight='bold',
            size='large')

    def _make_profile_plot(self, label, row=1, column=0, span=False):
        if span:
            ax = self.figure.add_subplot(self.gs[row, :])
        else:
            ax = self.figure.add_subplot(self.gs[row, column])

        ax.set_yscale('log')

        for profile in self.profiles:
            ax.plot(profile.q, profile.i, markersize=1, label=profile.filename)

        if len(self.profiles) > 1:
            ax.legend(fontsize='small')

        absolute = [profile.metadata.Absolute_scale for profile in self.profiles]

        ax.set_xlabel('q')

        if all(absolute):
            ax.set_ylabel(r'Intensity [$cm^{-1}$]')
        else:
            ax.set_ylabel('Intensity [Arb.]')

        if span:
            offset = -0.05
        else:
            offset = -0.15

        ax.text(offset, 1.0, label, transform = ax.transAxes, fontweight='bold',
            size='large')

    def _make_guinier_plot(self, label, row=1, column=1):
        gssub = mpl.gridspec.GridSpecFromSubplotSpec(2, 1, self.gs[row, column],
            height_ratios=[1, 0.3], hspace=0.03)

        ax = self.figure.add_subplot(gssub[0])
        res_ax = self.figure.add_subplot(gssub[1], sharex=ax)

        plt.setp(ax.get_xticklabels(), visible=False)


        ax.set_yscale('log')
        # ax.yaxis.set_major_formatter(mpl.ticker.FuncFormatter(tick_formatter))
        ax.yaxis.set_minor_formatter(plt.NullFormatter())



        for profile in self.profiles:
            if profile.guinier_data.Rg > 0 and profile.guinier_data.I0 > 0:
                fit = guinier_fit(profile.q, profile.guinier_data.Rg,
                    profile.guinier_data.I0)
                n_min = profile.guinier_data.n_min
                n_max = profile.guinier_data.n_max

                ax.plot(profile.q[:n_max+1]**2, profile.i[:n_max+1], 'o', markersize=3,
                    label=profile.filename)
                ax.plot(profile.q[n_min:n_max+1]**2, fit[n_min:n_max+1], '-', color='k')
                if n_min > 0:
                    ax.plot(profile.q[:n_min]**2, fit[:n_min], '--', color='0.6')

                res_y = (profile.i[n_min:n_max+1]-fit[n_min:n_max+1])/profile.err[n_min:n_max+1]
                res_ax.plot(profile.q[n_min:n_max+1]**2, res_y, 'o', markersize=3)

        res_ax.axhline(0, color='0')

        if len(self.profiles) > 1:
            ax.legend(fontsize='small')

        absolute = [profile.metadata.Absolute_scale for profile in self.profiles]

        if all(absolute):
            ax.set_ylabel(r'Intensity [$cm^{-1}$]')
        else:
            ax.set_ylabel('Intensity [Arb.]')

        res_ax.set_xlabel(r'q$^2$')
        res_ax.set_ylabel(r'$\Delta$I/$\sigma$')

        ax.text(-.15,1.0, label, transform = ax.transAxes, fontweight='bold',
            size='large')

    def _make_kratky_plot(self, label, row=2, column=0):
        ax = self.figure.add_subplot(self.gs[row, column])

        ax.axvline(np.sqrt(3), 0, 1, linestyle = 'dashed', color='0.6')
        ax.axhline(3/np.e, 0, 1, linestyle = 'dashed', color='0.6')

        norm_i_max = 0

        for profile in self.profiles:
            i0 = profile.guinier_data.I0
            rg = profile.guinier_data.Rg

            if i0 > 0 and rg > 0:
                qRg = profile.q*rg
                norm_i = qRg**2*profile.i/i0

                ax.plot(qRg, norm_i, markersize=1, label=profile.filename)

                if len(norm_i) > 51:
                    smoothed_data = scipy.signal.savgol_filter(norm_i, 51, 0)
                    norm_i_max = max(norm_i_max, smoothed_data.max())

                else:
                    norm_i_max = max(norm_i_max, norm_i.max())

        ax.axhline(0, color='k')

        if len(self.profiles) > 1:
            ax.legend(fontsize='small')

        ax.set_xlabel(r'q$R_g$')
        ax.set_ylabel(r'(q$R_g$)$^2$I(q)/I(0)')

        top_lim = norm_i_max*1.1

        ymin, ymax = ax.get_ylim()
        ax.set_ylim(max(-0.1, ymin), min(top_lim, ymax))

        ax.text(-.15,1.0, label, transform = ax.transAxes, fontweight='bold',
            size='large')

    def _make_ift_plot(self, label, row=2, column=1, span=False):
        if span:
            ax = self.figure.add_subplot(self.gs[row, :])
        else:
            ax = self.figure.add_subplot(self.gs[row, column])
        ax.axhline(0, color='k')
        # plt.setp(ax.get_yticklabels(), visible=False)

        for ift in self.ifts:
            ax.plot(ift.r, ift.p, markersize=1, label=ift.filename)

        if len(self.profiles) > 1:
            ax.legend(fontsize='small')

        ax.set_xlabel('r')
        ax.set_ylabel('P(r)/I(0)')

        if span:
            offset = -0.05
        else:
            offset = -0.15

        ax.text(offset, 1.0, label, transform = ax.transAxes, fontweight='bold',
            size='large')

class efa_plot(object):
    """
    Makes an overview plot with 4 panels. a) Series intensity and rg.
    b) Log-lin profiles. c) Normalized Kratky profiles. d) P(r)
    """

    def __init__(self, series, int_type='Total',
        series_data='Rg', img_width=6, img_height=6, is_regals=False):

        with mpl.rc_context({'font.size' : 8.0, 'font.family': 'Arial',
            'legend.frameon': False, 'legend.fontsize': 'medium', 'axes.labelsize': 'medium',
            'axes.linewidth': 1, 'axes.facecolor': 'white', 'axes.axisbelow': False,
            'axes.labelpad': 2.5, 'axes.xmargin': 0.015, 'axes.ymargin': 0.02,
            'xtick.labelsize' : 'medium', 'xtick.top' : True, 'xtick.direction' : 'in',
            'ytick.labelsize' : 'medium', 'ytick.right' : True, 'ytick.direction' : 'in',
            'lines.linewidth' : 1, 'mathtext.default': 'regular'}):

            self.series = series

            self.int_type = int_type
            self.series_data = series_data

            self.is_regals = is_regals


            if not series.efa_extra_data and not self.is_regals:
                if img_width == 6 and img_height == 6:
                    self.figure = plt.figure(figsize=(6, 2))
                else:
                    self.figure = plt.figure(figsize=(img_width, img_height))

                self.gs = self.figure.add_gridspec(1, 2)

            else:
                self.figure = plt.figure(figsize=(img_width, img_height))
                self.gs = self.figure.add_gridspec(3, 2)

            self._make_series_plot()
            self._make_efa_range_plot()

            if series.efa_extra_data or self.is_regals:
                self._make_efa_chi_plot()
                self._make_efa_concentration_plot()
                self._make_efa_profiles_plot()

            if series.efa_extra_data or self.is_regals:

                self.figure.subplots_adjust(left=0.1, right=0.98, wspace=0.3,
                    bottom=0.07, top=0.98, hspace=0.3)
            else:
                self.figure.subplots_adjust(left=0.1, right=0.98, wspace=0.3,
                    bottom=0.16, top=0.93, hspace=0.3)

    def _make_series_plot(self, row=0, column=0):
        ax = self.figure.add_subplot(self.gs[row, column])
        ax2 = ax.twinx()

        ax.spines["right"].set_visible(False)
        make_patch_spines_invisible(ax2)
        ax2.spines["right"].set_visible(True)

        if self.int_type == 'Total':
            y_data = self.series.total_i
        elif self.int_type == 'Mean':
            y_data = self.series.mean_i

        if self.series.has_calc_data:
            if self.series_data == 'Rg':
                y2_data = self.series.rg
            elif self.series_data == 'I0':
                y2_data = self.series.i0
            elif self.series_data == 'MW_Vc':
                y2_data = self.series.vcmw
            elif self.series_data == 'MW_Vp':
                y2_data = self.series.vpmw

        x_data = self.series.frames

        if not self.is_regals:
            start = int(self.series.efa_start)
            end = int(self.series.efa_end)
        else:
            start = int(self.series.regals_start)
            end = int(self.series.regals_end)

        int_line, = ax.plot(x_data, y_data, '-', label=self.series.filename)
        ax.plot(x_data[start:end+1], y_data[start:end+1], '-', color='k')

        if self.series.has_calc_data:
            calc_line, = ax2.plot(x_data[y2_data>0], y2_data[y2_data>0], 'o',
                label='{} {}'.format(self.series.filename, self.series_data),
                markersize=1)


        ax.yaxis.label.set_color(int_line.get_color())
        ax.tick_params(axis='y', colors=int_line.get_color())
        ax.spines['left'].set_color(int_line.get_color())

        calc_color = '#D7191C'

        if self.series.has_calc_data:
            calc_line.set_markerfacecolor(calc_color)
            calc_line.set_markeredgecolor(calc_color)

        ax2.yaxis.label.set_color(calc_color)
        ax2.tick_params(axis='y', colors=calc_color)
        ax2.spines['right'].set_color(calc_color)

        if not self.is_regals:
            ax.set_xlabel('Frames')
        else:
            if np.array_equal(x_data, np.arange(int(self.series.regals_start),
                int(self.series.regals_end)+1)):
                ax.set_xlabel('Frames')
            else:
                ax.set_xlabel(self.series.regals_x_type)

        ax.set_ylabel('{} Intensity [Arb.]'.format(self.int_type))

        if self.series_data == 'Rg':
            ax2.set_ylabel('Rg')
        elif self.series_data == 'I0':
            ax2.set_ylabel('I(0)')
        elif self.series_data == 'MW_Vc':
            ax2.set_ylabel('MW (Vc) [kDa]')
        elif self.series_data == 'MW_Vp':
            ax2.set_ylabel('MW (Vp) [kDa]')

        ax.text(-0.15, 1.0, 'a', transform = ax.transAxes, fontweight='bold',
            size='large')

    def _make_efa_range_plot(self, row=0, column=1):
        if not self.is_regals:
            start = int(self.series.efa_start)
            end = int(self.series.efa_end)
            ranges = self.series.efa_ranges
            frame_data = self.series.frames[start:end+1]
        else:
            start = int(self.series.regals_start)
            end = int(self.series.regals_end)
            ranges = self.series.regals_ranges
            frame_data = self.series.regals_x_cal

        if self.int_type == 'Total':
            int_data = self.series.total_i[start:end+1]
        elif self.int_type == 'Mean':
            int_data = self.series.mean_i[start:end+1]

        ax = self.figure.add_subplot(self.gs[row, column])
        plt.setp(ax.get_yticklabels(), visible=False)

        ax.plot(frame_data, int_data, '-', color='k')
        ax.set_prop_cycle(None)

        for i in range(len(ranges)):
            color = next(ax._get_lines.prop_cycler)['color']

            ax.annotate('', xy=(ranges[i][0], 0.975-0.05*(i)),
                xytext=(ranges[i][1], 0.975-0.05*(i)),
                xycoords=('data', 'axes fraction'),
                arrowprops = dict(arrowstyle = '<->', color = color))

            ax.axvline(ranges[i][0], 0, 0.975-0.05*(i), linestyle='dashed',
                color=color)
            ax.axvline(ranges[i][1], 0, 0.975-0.05*(i), linestyle='dashed',
                color=color)

        if not self.is_regals:
            ax.set_xlabel('Frames')
        else:
            if np.array_equal(frame_data, np.arange(int(self.series.regals_start),
                int(self.series.regals_end)+1)):
                ax.set_xlabel('Frames')
            else:
                ax.set_xlabel(self.series.regals_x_type)
        ax.set_ylabel('{} Intensity [Arb.]'.format(self.int_type))

        ax.text(-0.15, 1.0, 'b', transform = ax.transAxes, fontweight='bold',
            size='large')

    def _make_efa_chi_plot(self, row=1, column=0):
        if not self.is_regals:
            frames = self.series.efa_frames
            chi = self.series.efa_chi
        else:
            frames = self.series.regals_x_cal
            chi = self.series.regals_chi

        ax = self.figure.add_subplot(self.gs[row, column])
        ax.plot(frames, chi, '-', color='k')

        if not self.is_regals:
            ax.set_xlabel('Frames')
        else:
            if np.array_equal(frames, np.arange(int(self.series.regals_start),
                int(self.series.regals_end)+1)):
                ax.set_xlabel('Frames')
            else:
                ax.set_xlabel(self.series.regals_x_type)
        ax.set_ylabel(r'Mean $\chi^2$')

        ax.text(-0.15, 1.0, 'c', transform = ax.transAxes, fontweight='bold',
            size='large')

    def _make_efa_concentration_plot(self, row=1, column=1):
        if not self.is_regals:
            frames = self.series.efa_frames
            conc = self.series.efa_conc
        else:
            frames = self.series.regals_x_cal
            conc_vals = self.series.regals_conc
            conc = [c[1] for c in conc_vals]
            conc = np.column_stack(conc)

            reg_conc_vals = self.series.regals_reg_conc

        ax = self.figure.add_subplot(self.gs[row, column])

        conc_lines = []

        for i in range(conc.shape[1]):
            if not self.is_regals:
                ax.plot(frames, conc[:, i], '-')
            else:
                if conc.shape[0] < 40:
                    line, = ax.plot(frames, conc[:, i], 'o', markersize=2)
                    conc_lines.append(line)
                else:
                    line, = ax.plot(frames, conc[:, i], '-')

        if self.is_regals and conc.shape[0] < 40:
            for i in range(conc.shape[1]):
                line, = ax.plot(reg_conc_vals[i][0], reg_conc_vals[i][1], '-')
                line.set_color(conc_lines[i].get_color())

        if not self.is_regals:
            ax.set_xlabel('Frames')
        else:
            if np.array_equal(frames, np.arange(int(self.series.regals_start),
                int(self.series.regals_end)+1)):
                ax.set_xlabel('Frames')
            else:
                ax.set_xlabel(self.series.regals_x_type)
        ax.set_ylabel('Norm. Concentration')

        ax.text(-0.15, 1.0, 'd', transform = ax.transAxes, fontweight='bold',
            size='large')

    def _make_efa_profiles_plot(self, row=2):
        if not self.is_regals:
            profiles = self.series.efa_profiles
        else:
            profiles = self.series.regals_profiles

        if (self.is_regals and len(self.series.regals_ifts) > 0
            and not all([x is None for x in self.series.regals_ifts])):
            ax = self.figure.add_subplot(self.gs[row, 0])
            span = False
        else:
            ax = self.figure.add_subplot(self.gs[row, :])
            span = True

        ax.set_yscale('log')

        profile_lines = []

        for profile in profiles:
            line, = ax.plot(profile.q, profile.i)
            profile_lines.append(line)

        ax.set_xlabel('q')
        ax.set_ylabel('Intensity [Arb.]')

        if span:
            offset = -0.05
        else:
            offset = -0.15

        ax.text(offset, 1.0, 'e', transform = ax.transAxes, fontweight='bold',
            size='large')

        if (self.is_regals and len(self.series.regals_ifts) > 0
            and not all([x is None for x in self.series.regals_ifts])):
            ax2 = self.figure.add_subplot(self.gs[row, 1])
            ax2.axhline(0, color='k')

            for i, ift in enumerate(self.series.regals_ifts):
                if ift is not None:
                    color = profile_lines[i].get_color()
                    ax2.plot(ift.r, ift.p, markersize=1, label=ift.filename,
                        color=color)

            ax2.set_xlabel('r')
            ax2.set_ylabel('P(r)/I(0)')

            ax2.text(offset, 1.0, 'f', transform = ax2.transAxes, fontweight='bold',
            size='large')

def guinier_fit(q, rg, i0):
    return i0*np.exp(-rg**2*q**2/3)

def tick_formatter(x, pos):
    return "{}".format(x)




##################### Contents of reports/pdf.py #####################

def generate_report(fname, datadir, profiles, ifts, series, extra_data=None):
    """
    Inputs a list of profile data, a list of ift data, and a list of series
    data to be included in the report. Makes a PDF report.
    """

    elements = []

    overview = generate_overview(profiles, ifts, series)
    elements.extend(overview)

    exp = generate_exp_params(profiles, ifts, series)
    elements.extend(exp)

    if len(series) > 0:
        s_elements = generate_series_params(profiles, ifts, series, extra_data)
        elements.extend(s_elements)

    if len(profiles) > 0:
        guinier = generate_guinier_params(profiles, ifts, series)
        elements.extend(guinier)

        mw = generate_mw_params(profiles, ifts, series)
        elements.extend(mw)

    if len(ifts) > 0:
        if any(ift.type == 'GNOM' for ift in ifts):
            gnom = generate_gnom_params(profiles, ifts, series)
            elements.extend(gnom)

        if any(ift.type == 'BIFT' for ift in ifts):
            bift = generate_bift_params(profiles, ifts, series)
            elements.extend(bift)

    if (extra_data is not None and 'dammif' in extra_data and
        len(extra_data['dammif']) > 0 and
        any(dam_data is not None for dam_data in extra_data['dammif'])):
        dammif = generate_dammif_params(extra_data['dammif'])
        elements.extend(dammif)

    if (extra_data is not None and 'denss' in extra_data and
        len(extra_data['denss']) > 0 and
        any(dam_data is not None for dam_data in extra_data['denss'])):
        denss = generate_denss_params(extra_data['denss'])
        elements.extend(denss)

    datadir = os.path.abspath(os.path.expanduser(datadir))
    fname = '{}.pdf'.format(os.path.splitext(fname)[0])

    doc = SimpleDocTemplate(os.path.join(datadir, fname), pagesize=letter,
        leftMargin=1*inch, rightMargin=1*inch, topMargin=1*inch,
        bottomMargin=1*inch)
    doc.build(elements)

    global temp_files

    for fname in temp_files:
        if os.path.isfile(fname):
            os.remove(fname)

    temp_files = []

def generate_overview(profiles, ifts, series):
    """
    Generates the overview portion of the report. Returns a list of flowables.
    """
    styles = getSampleStyleSheet()

    elements = []

    name_list = []
    date_list = []

    if len(series) > 0:
        data_list = series
    elif len(profiles) > 0:
        data_list = profiles
    elif len(ifts) > 0:
        data_list = ifts
    else:
        data_list = []

    for s in data_list:
        if ('File_prefix' in s.metadata._fields
            and getattr(s.metadata, 'File_prefix') != ''):
            name_list.append(getattr(s.metadata, 'File_prefix'))
        else:
            name_list.append(s.filename)

        if 'Date' in s.metadata._fields and getattr(s.metadata, 'Date') != '':
            date_list.append(':'.join(getattr(s.metadata, 'Date').split(':')[:-1]))
        else:
            date_list.append('N/A')

    name_str = ', '.join(name_list)
    date_str = ', '.join(date_list)

    if 'N/A' in name_str:
        title_text = 'SAXS data overview'.format(name_str)
    else:
        title_text = '{} SAXS data overview'.format(name_str)
    ov_title = Paragraph(title_text, styles['Heading1'])

    ov_text = Paragraph('Summary:', styles['Heading2'])

    if any([date != 'N/A' for date in date_list]):
        summary_text = ('Data name(s): {}\n'
            'Collection date(s): {}'.format(name_str, date_str))
    else:
         summary_text = ('Data name(s): {}\n'.format(name_str))

    ov_summary = XPreformatted(summary_text, styles['Normal'])

    elements.append(ov_title)
    elements.append(ov_text)
    elements.append(ov_summary)


    # Make overview figure
    if len(profiles) > 0:
        has_profiles = True
        has_rg = any([prof.guinier_data.Rg > 0 and prof.guinier_data.I0 > 0 for prof in profiles])
    else:
        has_profiles = False
        has_rg = False

    if len(ifts) > 0:
        has_ifts = True
    else:
        has_ifts = False

    if len(series) > 0:
        has_series = True
    else:
        has_series = False

    if 'N/A' in name_str:
        caption = ('SAXS data summary figure.')
    else:
        caption = ('SAXS data summary figure for {}. '.format(name_str))

    if len(series) == 1:
        series_label = ('Series intensity (blue, left axis) vs. frame, and, if '
            'available, Rg vs. frame (red, right axis). Green shaded regions '
            'are buffer regions, purple shaded regions are sample regions.')
    else:
        series_label = ('Series intensity (left axis) vs. frame, and, if '
            'available, Rg vs. frame (right axis). Green shaded regions are '
            'buffer regions, purple shaded regions are sample regions.')

    profile_label = ('Scattering profile(s) on a log-lin scale.')
    guinier_label = ('Guinier fit(s) (top) and fit residuals (bottom).')
    kratky_label = ('Normalized Kratky plot. Dashed lines show where a '
        'globular system would peak.')
    ift_label = ('P(r) function(s), normalized by I(0).')


    img_width = 6

    if has_profiles and has_rg and has_ifts and has_series:
        img_height = 6

        caption = ('{} a) {} b) {} c) {} d) {} e) {}'.format(caption,
            series_label, profile_label, guinier_label, kratky_label,
            ift_label))

    elif has_profiles and has_rg and has_ifts and not has_series:
        img_height = 4

        caption = ('{} a) {} b) {} c) {} d) {}'.format(caption, profile_label,
            guinier_label, kratky_label, ift_label))

    elif has_profiles and has_rg and not has_ifts and has_series:
        img_height = 6

        caption = ('{} a) {} b) {} c) {} d) {}'.format(caption, series_label,
            profile_label, guinier_label, kratky_label))

    elif has_profiles and has_rg and not has_ifts and not has_series:
        img_height = 4

        caption = ('{} a) {} b) {} c) {}'.format(caption, profile_label,
            guinier_label, kratky_label))

    elif has_profiles and not has_rg and has_ifts and has_series:
        img_height = 4

        caption = ('{} a) {} b) {} c) {}'.format(caption,
            series_label, profile_label, ift_label))

    elif has_profiles and not has_rg and has_ifts and not has_series:
        img_height = 2

        caption = ('{} a) {} b) {}'.format(caption, profile_label,
            ift_label))

    elif has_profiles and not has_rg and not has_ifts and has_series:
        img_height = 4

        caption = ('{} a) {} b) {}'.format(caption, series_label,
            profile_label))

    elif has_profiles and not has_rg and not has_ifts and not has_series:
        img_height = 2

        caption = ('{} {}'.format(caption, profile_label))

    elif not has_profiles and has_ifts and has_series:
        img_height = 4

        caption = ('{} a) {} b) {}'.format(caption, series_label, ift_label))

    elif not has_profiles and not has_ifts and has_series:
        img_height = 2

        caption = ('{} {}'.format(caption, series_label))

    elif not has_profiles and has_ifts and not has_series:
        img_height = 2

        caption = ('{} {}'.format(caption, ift_label))

    else:
        img_height = 0

    if img_height > 0:
        ov_plot = overview_plot(profiles, ifts, series,
            img_width=img_width, img_height=img_height)

        ov_figure = make_figure(ov_plot.figure, caption, img_width, img_height,
            styles)

        elements.append(ov_figure)


    # Make overview table
    table_pairs = [
        ('', 'name'),
        ('Guinier Rg', 'gu_rg'),
        ('Guinier I(0)', 'gu_i0'),
        ('M.W. (Vp)', 'mw_vp'),
        ('M.W. (Vc)', 'mw_vc'),
        ('M.W. (S&S)', 'mw_ss'),
        ('M.W. (Bayes)', 'mw_bayes'),
        ('M.W. (Abs.)', 'mw_abs'),
        ('M.W. (Ref.)', 'mw_ref'),
        ('GNOM Dmax', 'gn_dmax'),
        ('GNOM Rg', 'gn_rg'),
        ('GNOM I(0)', 'gn_i0'),
        ('BIFT Dmax', 'b_dmax'),
        ('BIFT Rg', 'b_rg'),
        ('BIFT I(0)', 'b_i0'),
        ]

    table_dict = OrderedDict()

    table_data = []

    required_data = ['']


    for profile in profiles:

        filename = profile.filename

        if profile.guinier_data.Rg != -1:
            rg = profile.guinier_data.Rg
            rg_err = profile.guinier_data.Rg_err
            i0 = profile.guinier_data.I0
            i0_err = profile.guinier_data.I0_err

            guinier_rg = '{} +/- {}'.format(text_round(rg, 2),
                text_round(rg_err, 2))
            guinier_i0 = '{} +/- {}'.format(text_round(i0, 2),
                text_round(i0_err, 2))
        else:
            guinier_rg = ''
            guinier_i0 = ''


        mw_data = defaultdict(str)

        for mw_key in profile.mw_data:
            mw_val = profile.mw_data[mw_key]

            if mw_val.MW != -1 and mw_val.MW != '':
                val = text_round(mw_val.MW, 1)
            else:
                val = ''

            if mw_key == 'Volume_of_correlation':
                table_key = 'mw_vc'
            elif mw_key == 'Porod_volume':
                table_key = 'mw_vp'
            elif mw_key == 'Shape_and_size':
                table_key = 'mw_ss'
            elif mw_key == 'Bayesian':
                table_key = 'mw_bayes'
            elif mw_key == 'Absolute':
                table_key = 'mw_abs'
            elif mw_key == 'Reference':
                table_key = 'mw_ref'

            mw_data[table_key] = val


        if profile.gnom_data.Dmax != -1:
            dmax = profile.gnom_data.Dmax
            rg = profile.gnom_data.Rg
            rg_err = profile.gnom_data.Rg_err
            i0 = profile.gnom_data.I0
            i0_err = profile.gnom_data.I0_err

            gnom_dmax = '{}'.format(text_round(dmax, 0))

            gnom_rg = '{} +/- {}'.format(text_round(rg, 2),
                text_round(rg_err, 2))
            gnom_i0 = '{} +/- {}'.format(text_round(i0, 2),
                text_round(i0_err, 2))

        else:
            gnom_dmax = ''
            gnom_rg = ''
            gnom_i0 = ''

        if profile.bift_data.Dmax != -1:
            dmax = profile.bift_data.Dmax
            dmax_err = profile.bift_data.Dmax_err
            rg = profile.bift_data.Rg
            rg_err = profile.bift_data.Rg_err
            i0 = profile.bift_data.I0
            i0_err = profile.bift_data.I0_err

            bift_dmax = '{} +/- {}'.format(text_round(dmax, 0),
                text_round(dmax_err, 0))

            bift_rg = '{} +/- {}'.format(text_round(rg, 2),
                text_round(rg_err, 2))
            bift_i0 = '{} +/- {}'.format(text_round(i0, 2),
                text_round(i0_err, 2))

        else:
            bift_dmax = ''
            bift_rg = ''
            bift_i0 = ''

        for header, key in table_pairs:
            if key == 'name':
                value = filename
            elif key == 'gu_rg':
                value = guinier_rg
            elif key == 'gu_i0':
                value = guinier_i0
            elif key.startswith('mw'):
                value =mw_data[key]
            elif key == 'gn_dmax':
                value = gnom_dmax
            elif key == 'gn_rg':
                value = gnom_rg
            elif key == 'gn_i0':
                value = gnom_i0
            elif key == 'b_dmax':
                value = bift_dmax
            elif key == 'b_rg':
                value = bift_rg
            elif key == 'b_i0':
                value = bift_i0

            if header in table_dict:
                table_dict[header].append(value)
            else:
                table_dict[header] = [value]

    for header, values in table_dict.items():
        if header in required_data:
            table_entry = [header]
            table_entry.extend(values)
            table_data.append(table_entry)
        else:
            if any(val != '' for val in values):
                table_entry = [header]
                table_entry.extend(values)
                table_data.append(table_entry)

    if len(table_data) > 1:
        ov_table = Table(table_data, spaceBefore=0.25*inch, spaceAfter=0.1*inch)

        table_style = TableStyle(
            [('LINEBELOW', (0, 0), (-1, 0), 1, colors.black),
            ('LINEAFTER', (0, 0), (0,-1), 1, colors.black),
            ])

        ov_table.setStyle(table_style)
        ov_table.hAlign = 'LEFT'

        if 'N/A' in name_str:
            table_caption = ('SAXS data summary table. ')
        else:
            table_caption = ('SAXS data summary table for {}. '.format(name_str))

        table_text = Paragraph(table_caption, styles['Normal'])

        ov_table = KeepTogether([ov_table, table_text])

        elements.append(ov_table)

    return elements


def generate_exp_params(profiles, ifts, series):
    styles = getSampleStyleSheet()

    name_list = []

    if len(series) > 0:
        data_list = series
    elif len(profiles) > 0:
        data_list = profiles
    else:
        data_list = []

    for s in data_list:
        if isinstance(s, SECData):
            if ('File_prefix' in s.metadata._fields
            and getattr(s.metadata, 'File_prefix') != ''):
                name_list.append(getattr(s.metadata, 'File_prefix'))
            else:
                name_list.append(s.filename)
        else:
            name_list.append(s.filename)

    exp_text = Paragraph('Experimental parameters:', styles['Heading2'])

    table_pairs = [
        ('', 'name'),
        ('Date', 'Date'),
        ('Instrument', 'Instrument'),
        ('Experiment Type', 'Experiment_type'),
        ('Column', 'Column'),
        ('Mixer', 'Mixer'),
        ('Sample', 'Sample'),
        ('Buffer', 'Buffer'),
        ('Temperature [C]', 'Temperature'),
        ('Loaded volume [uL]', 'Loaded_volume'),
        ('Concentration [mg/ml]', 'Concentration'),
        ('Detector', 'Detector'),
        ('Wavelength (A)', 'Wavelength'),
        ('Camera length (m)', 'Sample_to_detector_distance'),
        ('q-measurement range (1/A)', 'q_range'),
        ('Exposure time (s)', 'Exposure_time'),
        ('Exposure period (s)', 'Exposure_period'),
        ('Flow rate (ml/min)', 'Flow_rate'),
        ('Attenuation', 'Transmission'),
        ('RAW version', 'RAW_version'),
        ('Notes', 'Notes'),
        ]

    table_dict = OrderedDict()

    table_data = []

    required_data = ['']

    for j, s in enumerate(data_list):
        for header, key in table_pairs:
            if key in s.metadata._fields:
                value = getattr(s.metadata, key)
            else:
                value = ''

            if key == 'Wavelength':
                if value != '' and value != -1:
                    value = text_round(value, 3)
                else:
                    value = ''

            elif key == 'Sample_to_detector_distance':
                if value != '' and value != -1:
                    value = float(value)/1000.
                    value = text_round(value, 3)
                else:
                    value = ''

            elif key == 'name':
                value = name_list[j]

            elif key == 'Date':
                value = ':'.join(value.split(':')[:-1])

            elif key == 'Transmission':
                if value != -1:
                    if float(value) == 1:
                        value = 'None'
                    else:
                        value = str(round(1./float(value),4))
                else:
                    value = ''

            else:
                if value != -1:
                    value = str(value)
                else:
                    value = ''

            if header in table_dict:
                table_dict[header].append(value)
            else:
                table_dict[header] = [value]


    for header, values in table_dict.items():
        if header in required_data:
            table_entry = [header]
            table_entry.extend(values)
            table_data.append(table_entry)
        else:
            if any(val != '' for val in values):
                table_entry = [header]
                table_entry.extend(values)
                table_data.append(table_entry)

    if len(table_data) > 1:
        exp_table = Table(table_data)

        table_style = TableStyle(
            [('LINEBELOW', (0, 0), (-1, 0), 1, colors.black),
            ('LINEAFTER', (0, 0), (0,-1), 1, colors.black),
            ])

        exp_table.setStyle(table_style)
        exp_table.hAlign = 'LEFT'

        elements = [exp_text, exp_table]

    else:
        elements = []

    return elements


def generate_series_params(profiles, ifts, series, extra_data):
    styles = getSampleStyleSheet()

    has_series_data = False

    name_list = []

    for s in series:
        if ('File_prefix' in s.metadata._fields
            and getattr(s.metadata, 'File_prefix') != ''):
            name_list.append(getattr(s.metadata, 'File_prefix'))
        elif s.filename != '':
            name_list.append(s.filename)
        else:
            name_list.append('N/A')

    series_text = Paragraph('Series:', styles['Heading2'])


    table_pairs = [
        ('', 'name'),
        ('Buffer range', 'buf_range'),
        ('Sample range', 'sam_range'),
        ('Baseline correction', 'baseline_type'),
        ('Baseline start range', 'baseline_start'),
        ('Baseline end range', 'baseline_end'),
        ]

    table_dict = OrderedDict()

    table_data = []

    required_data = []


    for j, s in enumerate(series):
        buffer_range = ', '.join(['{} to {}'.format(*br) for br in s.buffer_range])
        sample_range = ', '.join(['{} to {}'.format(*sr) for sr in s.sample_range])

        if s.baseline_corrected:
            baseline_type = s.baseline_type
            baseline_start = '{} to {}'.format(*s.baseline_start_range)
            baseline_end = '{} to {}'.format(*s.baseline_end_range)
        else:
            baseline_type = ''
            baseline_start = ''
            baseline_end = ''

        for header, key in table_pairs:
            if key == 'name':
                value = name_list[j]
            elif key == 'buf_range':
                value = buffer_range
            elif key == 'sam_range':
                value = sample_range
            elif key == 'baseline_type':
                value = baseline_type
            elif key == 'baseline_start':
                value = baseline_start
            elif key == 'baseline_end':
                value = baseline_end

            if header in table_dict:
                table_dict[header].append(value)
            else:
                table_dict[header] = [value]

    for header, values in table_dict.items():
        if header in required_data:
            table_entry = [header]
            table_entry.extend(values)
            table_data.append(table_entry)
        else:
            if any(val != '' for val in values):
                table_entry = [header]
                table_entry.extend(values)
                table_data.append(table_entry)

    if len(table_data) > 1:
        series_table = Table(table_data)

        table_style = TableStyle(
            [('LINEBELOW', (0, 0), (-1, 0), 1, colors.black),
            ('LINEAFTER', (0, 0), (0,-1), 1, colors.black),
            ])

        series_table.setStyle(table_style)
        series_table.hAlign = 'LEFT'
        series_table = KeepTogether([series_text, series_table])

        elements = [series_table]

        has_series_data = True

    else:
        elements = [series_text]

    #EFA
    efa_elements = []

    efa_table_pairs = [
        ('', 'name'),
        ('EFA data range', 'efa_range'),
        ('Number of components', 'nsvs'),
        ]

    efa_table_dict = OrderedDict()

    efa_table_data = []

    efa_required_data = ['', 'EFA data range', 'Number of components']

    for j, s in enumerate(series):
        if s.efa_done:
            if len(series) > 1:
                efa_title = Paragraph('{} EFA results:'.format(name_list[j]),
                    styles['Heading3'])
            else:
                efa_title = Paragraph('EFA results:', styles['Heading3'])

            # Make EFA table
            for header, key in efa_table_pairs:
                if key == 'name':
                    value = name_list[j]
                elif key == 'efa_range':
                    value = '{} to {}'.format(s.efa_start, s.efa_end)
                elif key == 'nsvs':
                    value = '{}'.format(s.efa_nsvs)
                else:
                    value = ''

                if header in efa_table_dict:
                    efa_table_dict[header].append(value)
                else:
                    efa_table_dict[header] = [value]

            for k, efa_range in enumerate(s.efa_ranges):
                header = 'Component {}'.format(k)
                value = '{} to {}'.format(*efa_range)

                if header in efa_table_dict:
                    efa_table_dict[header].append(value)
                else:
                    efa_table_dict[header] = [value]


            for header, values in efa_table_dict.items():
                if header in efa_required_data:
                    efa_table_entry = [header]
                    efa_table_entry.extend(values)
                    efa_table_data.append(efa_table_entry)
                else:
                    if any(val != '' for val in values):
                        efa_table_entry = [header]
                        efa_table_entry.extend(values)
                        efa_table_data.append(efa_table_entry)

            efa_table = Table(efa_table_data)

            table_style = TableStyle(
                [('LINEBELOW', (0, 0), (-1, 0), 1, colors.black),
                ('LINEAFTER', (0, 0), (0,-1), 1, colors.black),
                ])

            efa_table.setStyle(table_style)
            efa_table.hAlign = 'LEFT'
            # efa_table = KeepTogether([efa_table])

            # Make EFA plot

            efa_plot_panel = efa_plot(s)

            img_width = 6
            img_height = 2

            efa_caption = ('EFA deconvolution results. a) The full series '
                'intensity (blue), the selected intensity range for EFA '
                '(black), and (if available) Rg values (red). b) The selected '
                'intensity range for EFA (black), and the individual component '
                'ranges for deconvolution, with component range 0 starting at '
                'the top left, and component number increasing in descending '
                'order to the right.')

            if s.efa_extra_data:
                efa_caption = efa_caption + (' c) Mean chi^2 values between the '
                    'fit of the EFA deconvolution and the original data. d) '
                    'Area normalized concentration profiles for each component. '
                    'Colors match the component range colors in b.')

                efa_caption = efa_caption + (' e) Deconvolved scattering '
                    'profiles. Colors match the component range colors in '
                    'b and the concentration range colors in d.')

                img_height = 6

            efa_figure = make_figure(efa_plot_panel.figure, efa_caption, img_width,
                img_height, styles)

            efa_elements.append(efa_title)
            efa_elements.append(efa_table)
            efa_elements.append(efa_figure)

            has_series_data = True

    elements.extend(efa_elements)

    #REGALS
    regals_elements = []

    regals_table_pairs = [
        ('', 'name'),
        ('REGALS data range', 'regals_range'),
        ('Number of components', 'nsvs'),
        ('Convergence criteria', 'conv_type'),
        ('Max iterations', 'max_iter'),
        ('Min iterations', 'min_iter'),
        ('Convergence Tolerance', 'tol'),
        ]

    regals_table_dict = OrderedDict()

    regals_table_data = []

    regals_required_data = ['', 'REGALS data range', 'Number of components']

    regals_comp_table_dict = OrderedDict()
    regals_comp_table_data = []
    regals_comp_required_data = []

    regals_profile_component_table_pairs = [
        ('Component', 'name'),
        ('Profile type', 'type'),
        ('Prof. Lambda', 'lambda'),
        ('Prof. Control points', 'Nw'),
        ('Dmax', 'dmax'),
        ('Zero at R=0', 'is_zero_at_r0'),
        ('Zero at Dmax', 'is_zero_at_dmax'),
        ]

    regals_conc_component_table_pairs = [
        ('Concentration type', 'type'),
        ('Conc. Lambda', 'lambda'),
        ('Start', 'xmin'),
        ('End', 'xmax'),
        ('Conc. Control points', 'Nw'),
        ('Zero at start', 'is_zero_at_xmin'),
        ('Zero at end', 'is_zero_at_xmax'),
        ]

    for j, s in enumerate(series):
        if s.regals_done:
            if len(series) > 1:
                regals_title = Paragraph('{} REGALS results:'.format(name_list[j]),
                    styles['Heading3'])
            else:
                regals_title = Paragraph('REGALS results:', styles['Heading3'])

            # Make REGALS table
            for header, key in regals_table_pairs:
                if key == 'name':
                    value = name_list[j]
                elif key == 'regals_range':
                    value = '{} to {}'.format(s.regals_start, s.regals_end)
                elif key == 'nsvs':
                    value = '{}'.format(s.regals_nsvs)
                elif key == 'conv_type':
                    value = '{}'.format(s.regals_run_settings['conv_type'])
                elif key == 'max_iter':
                    value = '{}'.format(s.regals_run_settings['max_iter'])
                elif key == 'min_iter':
                    if s.regals_run_settings['conv_type'] != 'Iterations':
                        value = '{}'.format(s.regals_run_settings['min_iter'])
                    else:
                        value = ''
                elif key == 'tol':
                    if s.regals_run_settings['conv_type'] != 'Iterations':
                        value = '{}'.format(s.regals_run_settings['tol'])
                    else:
                        value = ''
                else:
                    value = ''

                if header in regals_table_dict:
                    regals_table_dict[header].append(value)
                else:
                    regals_table_dict[header] = [value]

            for header, values in regals_table_dict.items():
                if header in regals_comp_required_data:
                    regals_table_entry = [header]
                    regals_table_entry.extend(values)
                    regals_table_data.append(regals_table_entry)
                else:
                    if any(val != '' for val in values):
                        regals_table_entry = [header]
                        regals_table_entry.extend(values)
                        regals_table_data.append(regals_table_entry)

            regals_table = Table(regals_table_data)

            table_style = TableStyle(
                [('LINEBELOW', (0, 0), (-1, 0), 1, colors.black),
                ('LINEAFTER', (0, 0), (0,-1), 1, colors.black),
                ])

            regals_table.setStyle(table_style)
            regals_table.hAlign = 'LEFT'
            # regals_table = KeepTogether([regals_table])


            #Make REGALS compoment table
            for k, comp_settings in enumerate(s.regals_component_settings):
                prof_comp = comp_settings[0]
                conc_comp = comp_settings[1]

                for header, key in regals_profile_component_table_pairs:
                    if key == 'name':
                        value = '{}'.format(k)
                    elif key == 'lambda':
                        value = '{}'.format(text_round(prof_comp[key], 2))
                    elif key in prof_comp:
                        value = '{}'.format(prof_comp[key])
                    elif key in prof_comp['kwargs']:
                        value = '{}'.format(prof_comp['kwargs'][key])
                    else:
                        value = ''

                    if header in regals_comp_table_dict:
                        regals_comp_table_dict[header].append(value)
                    else:
                        regals_comp_table_dict[header] = [value]

                for header, key in regals_conc_component_table_pairs:
                    if key == 'lambda':
                        value = '{}'.format(text_round(conc_comp[key], 2))
                    elif key in conc_comp:
                        value = '{}'.format(conc_comp[key])
                    elif key in conc_comp['kwargs']:
                        value = '{}'.format(conc_comp['kwargs'][key])
                    else:
                        value = ''

                    if header in regals_comp_table_dict:
                        regals_comp_table_dict[header].append(value)
                    else:
                        regals_comp_table_dict[header] = [value]

            for header, values in regals_comp_table_dict.items():
                if header in regals_required_data:
                    regals_table_entry = [header]
                    regals_table_entry.extend(values)
                    regals_comp_table_data.append(regals_table_entry)
                else:
                    if any(val != '' for val in values):
                        regals_table_entry = [header]
                        regals_table_entry.extend(values)
                        regals_comp_table_data.append(regals_table_entry)

            regals_comp_table = Table(regals_comp_table_data)

            table_style = TableStyle(
                [('LINEBELOW', (0, 0), (-1, 0), 1, colors.black),
                ('LINEAFTER', (0, 0), (0,-1), 1, colors.black),
                ])

            regals_comp_table.setStyle(table_style)
            regals_comp_table.hAlign = 'LEFT'

            # Make REGALS plot

            regals_plot_panel = efa_plot(s, is_regals=True)

            img_width = 6
            img_height = 6

            regals_caption = ('REGALS deconvolution results. a) The full series '
                'intensity (blue), the selected intensity range for regals '
                '(black), and (if available) Rg values (red). b) The selected '
                'intensity range for regals (black), and the individual component '
                'ranges for deconvolution, with component range 0 starting at '
                'the top left, and component number increasing in descending '
                'order to the right. c) Mean chi^2 values between the '
                'fit of the regals deconvolution and the original data. d) '
                'Area normalized concentration profiles for each component. '
                'Colors match the component range colors in b. e) Deconvolved '
                'scattering profiles. Colors match the component range colors in '
                'b.')

            if len(s.regals_ifts) > 0:
                regals_caption = regals_caption + (' f) P(r) functions. Colors '
                    'match the component range colors in b.')

            regals_figure = make_figure(regals_plot_panel.figure, regals_caption,
                img_width, img_height, styles)

            regals_spacer = Paragraph('<br/><br/>', styles['Normal'])
            regals_elements.append(regals_title)
            regals_elements.append(regals_table)
            regals_elements.append(regals_spacer)
            regals_elements.append(regals_comp_table)
            regals_elements.append(regals_figure)

            has_series_data = True

    elements.extend(regals_elements)

    if not has_series_data:
        elements = []

    return elements

def generate_guinier_params(profiles, ifts, series):
    styles = getSampleStyleSheet()

    guinier_text = Paragraph('Guinier:', styles['Heading2'])

    absolute = [profile.metadata.Absolute_scale for profile in profiles]
    if all(absolute):
        i0_label = 'I(0) [1/cm]'
    else:
        i0_label = 'I(0) [Arb.]'

    table_pairs = [
        ('', 'name'),
        ('Rg [A]', 'rg'),
        (i0_label, 'i0'),
        ('q-range [1/A]', 'q_range'),
        ('qmin*Rg', 'qRg_min'),
        ('qmax*Rg', 'qRg_max'),
        ('r^2', 'rsq'),
        ]

    table_dict = OrderedDict()

    table_data = []

    required_data = ['']


    for profile in profiles:
        filename = profile.filename

        if profile.guinier_data.Rg != -1:
            rg = profile.guinier_data.Rg
            rg_err = profile.guinier_data.Rg_err
            i0 = profile.guinier_data.I0
            i0_err = profile.guinier_data.I0_err
            qmin = profile.guinier_data.q_min
            qmax = profile.guinier_data.q_max
            qRg_min = profile.guinier_data.qRg_min
            qRg_max = profile.guinier_data.qRg_max
            rsq = profile.guinier_data.r_sq

            rg = '{} +/- {}'.format(text_round(rg, 2),
                text_round(rg_err, 2))
            i0 = '{} +/- {}'.format(text_round(i0, 2),
                text_round(i0_err, 2))

            q_range = '{} to {}'.format(text_round(qmin, 4), text_round(qmax, 4))
            qmin_Rg = '{}'.format(text_round(qRg_min, 3))
            qmax_Rg = '{}'.format(text_round(qRg_max, 3))
            rsq = '{}'.format(text_round(rsq, 3))
        else:
            rg = ''
            i0 = ''
            q_range = ''
            qmin_Rg = ''
            qmax_Rg = ''
            rsq = ''


        for header, key in table_pairs:
            if key == 'name':
                value = filename
            elif key == 'rg':
                value = rg
            elif key == 'i0':
                value = i0
            elif key == 'q_range':
                value = q_range
            elif key == 'qRg_min':
                value = qmin_Rg
            elif key == 'qRg_max':
                value = qmax_Rg
            elif key == 'rsq':
                value = rsq

            if header in table_dict:
                table_dict[header].append(value)
            else:
                table_dict[header] = [value]

    for header, values in table_dict.items():
        if header in required_data:
            table_entry = [header]
            table_entry.extend(values)
            table_data.append(table_entry)
        else:
            if any(val != '' for val in values):
                table_entry = [header]
                table_entry.extend(values)
                table_data.append(table_entry)

    if len(table_data) > 1:
        guinier_table = Table(table_data)

        table_style = TableStyle(
            [('LINEBELOW', (0, 0), (-1, 0), 1, colors.black),
            ('LINEAFTER', (0, 0), (0,-1), 1, colors.black),
            ])

        guinier_table.setStyle(table_style)
        guinier_table.hAlign = 'LEFT'
        guinier_table = KeepTogether([guinier_text, guinier_table])

        elements = [guinier_table]

    else:
        elements = []

    return elements

def generate_mw_params(profiles, ifts, series):
    styles = getSampleStyleSheet()

    mw_text = Paragraph('Molecular weight:', styles['Heading2'])

    table_pairs = [
        ('', 'name'),
        ('M.W. (Vp) [kDa]', 'mw_vp'),
        ('Porod Volume [A^3]', 'vp'),
        ('M.W. (Vc) [kDa]', 'mw_vc'),
        ('M.W. (S&S) [kDa]', 'mw_ss'),
        ('Shape (S&S)', 'shape'),
        ('Dmax (S&S)', 'dmax'),
        ('M.W. (Bayes) [kDa]', 'mw_bayes'),
        ('Bayes Probability', 'prob'),
        ('Bayes Confidence\nInterval [kDa]', 'ci'),
        ('Bayes C.I. Prob.', 'ci_prob'),
        ('M.W. (Abs.) [kDa]', 'mw_abs'),
        ('M.W. (Ref.) [kDa]', 'mw_ref'),
        ]

    table_dict = OrderedDict()

    table_data = []

    required_data = ['']


    for profile in profiles:

        filename = profile.filename

        mw_data = defaultdict(str)

        for mw_key in profile.mw_data:
            mw_val = profile.mw_data[mw_key]

            if mw_val.MW != -1 and mw_val.MW != '':
                val = text_round(mw_val.MW, 1)
            else:
                val = ''

            if mw_key == 'Volume_of_correlation':
                table_key = 'mw_vc'
            elif mw_key == 'Porod_volume':
                table_key = 'mw_vp'
            elif mw_key == 'Shape_and_size':
                table_key = 'mw_ss'
            elif mw_key == 'Bayesian':
                table_key = 'mw_bayes'
            elif mw_key == 'Absolute':
                table_key = 'mw_abs'
            elif mw_key == 'Reference':
                table_key = 'mw_ref'

            mw_data[table_key] = val

        p_vol = ''

        if 'Porod_volume' in profile.mw_data:
            mw_val = profile.mw_data['Porod_volume']

            if mw_val.MW != -1 and mw_val.MW != '':
                p_vol = '{}'.format(text_round(mw_val.Porod_volume_corrected, 2))

        prob = ''
        ci = ''
        ci_prob = ''

        if 'Bayesian' in profile.mw_data:
            mw_val = profile.mw_data['Bayesian']

            if mw_val.MW != -1 and mw_val.MW != '':
                prob = '{}'.format(text_round(mw_val.Probability, 1))

                ci_lower = mw_val.Confidence_interval_lower
                ci_upper = mw_val.Confidence_interval_upper

                ci = ('{} to {}'.format(text_round(ci_lower, 1),
                    text_round(ci_upper, 1)))

                ci_prob = '{}'.format(text_round(mw_val.Confidence_interval_probability, 1))

        shape = ''
        dmax = ''

        if 'Shape_and_size' in profile.mw_data:
            mw_val = profile.mw_data['Shape_and_size']

            if mw_val.MW != -1 and mw_val.MW != '':
                shape = mw_val.Shape
                dmax = '{}'.format(text_round(mw_val.Dmax, 1))


        for header, key in table_pairs:
            if key == 'name':
                value = filename
            elif key.startswith('mw'):
                value =mw_data[key]
            elif key == 'vp':
                value = p_vol
            elif key == 'prob':
                value = prob
            elif key == 'ci':
                value = ci
            elif key == 'ci_prob':
                value = ci_prob
            elif key == 'shape':
                value = shape
            elif key == 'dmax':
                value = dmax

            if header in table_dict:
                table_dict[header].append(value)
            else:
                table_dict[header] = [value]

    for header, values in table_dict.items():
        if header in required_data:
            table_entry = [header]
            table_entry.extend(values)
            table_data.append(table_entry)
        else:
            if any(val != '' for val in values):
                table_entry = [header]
                table_entry.extend(values)
                table_data.append(table_entry)

    if len(table_data) > 1:
        mw_table = Table(table_data)

        table_style = TableStyle(
            [('LINEBELOW', (0, 0), (-1, 0), 1, colors.black),
            ('LINEAFTER', (0, 0), (0,-1), 1, colors.black),
            ])

        mw_table.setStyle(table_style)
        mw_table.hAlign = 'LEFT'
        mw_table = KeepTogether([mw_text, mw_table])

        elements = [mw_table]

    else:
        elements = []

    return elements

def generate_gnom_params(profiles, ifts, series):
    styles = getSampleStyleSheet()

    gnom_text = Paragraph('GNOM IFT:', styles['Heading2'])

    table_pairs = [
        ('', 'name'),
        ('Dmax [A]', 'dmax'),
        ('Rg [A]', 'rg'),
        ('I(0)', 'i0'),
        ('Chi^2', 'chi_sq'),
        ('Total Estimate', 'te'),
        ('Quality', 'quality'),
        ('q-range [1/A]', 'q_range'),
        ('Ambiguity score', 'a_score'),
        ('Ambiguity cats.', 'a_cats'),
        ('Ambiguity', 'a_interp'),
        ]

    table_dict = OrderedDict()

    table_data = []

    required_data = ['']


    for ift in ifts:

        if ift.type == 'GNOM':
            filename = ift.filename

            dmax = ift.dmax
            rg = ift.rg
            rg_err = ift.rg_err
            i0 = ift.i0
            i0_err = ift.i0_err
            chi_sq = ift.chi_sq
            te = ift.total_estimate
            quality = ift.quality

            dmax = '{}'.format(text_round(dmax, 0))

            rg = '{} +/- {}'.format(text_round(rg, 2),
                text_round(rg_err, 2))
            i0 = '{} +/- {}'.format(text_round(i0, 2),
                text_round(i0_err, 2))

            chi_sq = '{}'.format(text_round(chi_sq, 3))
            te = '{}'.format(text_round(te, 3))

            q_range = '{} to {}'.format(text_round(ift.q[0], 4),
                text_round(ift.q[-1], 4))

            if ift.a_score != -1:
                a_score = '{}'.format(text_round(ift.a_score, 2))
                a_cats = '{}'.format(ift.a_cats, 0)
                a_interp = ift.a_interp
            else:
                a_score = ''
                a_cats = ''
                a_interp = ''

            for header, key in table_pairs:
                if key == 'name':
                    value = filename
                elif key == 'dmax':
                    value = dmax
                elif key == 'rg':
                    value = rg
                elif key == 'i0':
                    value = i0
                elif key == 'chi_sq':
                    value = chi_sq
                elif key == 'te':
                    value = te
                elif key == 'quality':
                    value = quality
                elif key == 'q_range':
                    value = q_range
                elif key == 'a_score':
                    value = a_score
                elif key == 'a_cats':
                    value = a_cats
                elif key == 'a_interp':
                    value = a_interp

                if header in table_dict:
                    table_dict[header].append(value)
                else:
                    table_dict[header] = [value]

    for header, values in table_dict.items():
        if header in required_data:
            table_entry = [header]
            table_entry.extend(values)
            table_data.append(table_entry)
        else:
            if any(val != '' for val in values):
                table_entry = [header]
                table_entry.extend(values)
                table_data.append(table_entry)

    if len(table_data) > 1:
        gnom_table = Table(table_data)

        table_style = TableStyle(
            [('LINEBELOW', (0, 0), (-1, 0), 1, colors.black),
            ('LINEAFTER', (0, 0), (0,-1), 1, colors.black),
            ])

        gnom_table.setStyle(table_style)
        gnom_table.hAlign = 'LEFT'
        gnom_table = KeepTogether([gnom_text, gnom_table])

        elements = [gnom_table]

    else:
        elements = []

    return elements

def generate_bift_params(profiles, ifts, series):
    styles = getSampleStyleSheet()

    bift_text = Paragraph('BIFT:', styles['Heading2'])

    table_pairs = [
        ('', 'name'),
        ('Dmax [A]', 'dmax'),
        ('Rg [A]', 'rg'),
        ('I(0)', 'i0'),
        ('Chi^2', 'chi_sq'),
        ('q-range [1/A]', 'q_range'),
        ]

    table_dict = OrderedDict()

    table_data = []

    required_data = ['']


    for ift in ifts:

        if ift.type == 'BIFT':
            filename = ift.filename

            dmax = ift.dmax
            dmax_err = ift.dmax_err
            rg = ift.rg
            rg_err = ift.rg_err
            i0 = ift.i0
            i0_err = ift.i0_err
            chi_sq = ift.chi_sq

            dmax = '{} +/- {}'.format(text_round(dmax, 1),
                text_round(dmax_err, 1))

            rg = '{} +/- {}'.format(text_round(rg, 2),
                text_round(rg_err, 2))
            i0 = '{} +/- {}'.format(text_round(i0, 2),
                text_round(i0_err, 2))

            chi_sq = '{}'.format(text_round(chi_sq, 3))

            q_range = '{} to {}'.format(text_round(ift.q[0], 4),
                text_round(ift.q[-1], 4))

            for header, key in table_pairs:
                if key == 'name':
                    value = filename
                elif key == 'dmax':
                    value = dmax
                elif key == 'rg':
                    value = rg
                elif key == 'i0':
                    value = i0
                elif key == 'chi_sq':
                    value = chi_sq
                elif key == 'q_range':
                    value = q_range

                if header in table_dict:
                    table_dict[header].append(value)
                else:
                    table_dict[header] = [value]

    for header, values in table_dict.items():
        if header in required_data:
            table_entry = [header]
            table_entry.extend(values)
            table_data.append(table_entry)
        else:
            if any(val != '' for val in values):
                table_entry = [header]
                table_entry.extend(values)
                table_data.append(table_entry)

    if len(table_data) > 1:
        bift_table = Table(table_data)

        table_style = TableStyle(
            [('LINEBELOW', (0, 0), (-1, 0), 1, colors.black),
            ('LINEAFTER', (0, 0), (0,-1), 1, colors.black),
            ])

        bift_table.setStyle(table_style)
        bift_table.hAlign = 'LEFT'
        bift_table = KeepTogether([bift_text, bift_table])

        elements = [bift_table]

    else:
        elements = []

    return elements

def generate_dammif_params(dammif_data):
    styles = getSampleStyleSheet()

    dammif_text = Paragraph('Bead model reconstructions:', styles['Heading2'])

    table_pairs = [
        ('', 'prefix'),
        ('Program', 'program'),
        ('Mode', 'mode'),
        ('Symmetry', 'sym'),
        ('Anisometry', 'aniso'),
        ('Number of reconstructions', 'num'),
        ('Ran DAMAVER', 'damaver'),
        ('Ran DAMCLUST', 'damclust'),
        ('Refined with DAMMIN', 'refined'),
        ('Mean NSD', 'nsd'),
        ('Included models', 'included'),
        ('Resolution (SASRES)', 'res'),
        ('Representative model', 'rep_model'),
        ('Number of clusters', 'clusters'),
        ]

    table_dict = OrderedDict()

    table_data = []

    required_data = ['']


    for info in dammif_data:
        if info is not None:
            for header, key in table_pairs:
                value = getattr(info, key)

                if value == -1:
                    value = ''

                else:
                    if key == 'nsd':
                        value = '{} +/- {}'.format(text_round(value, 3),
                            text_round(info.nsd_std, 3))
                    elif key == 'res':
                        value = '{} +/- {}'.format(text_round(value, 0),
                            text_round(info.res_err, 0))
                    elif key == 'included':
                        value = '{} of {}'.format(value, info.num)
                    elif not isinstance(value, str):
                        value = '{}'.format(value)

                if header in table_dict:
                    table_dict[header].append(value)
                else:
                    table_dict[header] = [value]

    for header, values in table_dict.items():
        if header in required_data:
            table_entry = [header]
            table_entry.extend(values)
            table_data.append(table_entry)
        else:
            if any(val != '' for val in values):
                table_entry = [header]
                table_entry.extend(values)
                table_data.append(table_entry)

    if len(table_data) > 1:
        dammif_table = Table(table_data)

        table_style = TableStyle(
            [('LINEBELOW', (0, 0), (-1, 0), 1, colors.black),
            ('LINEAFTER', (0, 0), (0,-1), 1, colors.black),
            ])

        dammif_table.setStyle(table_style)
        dammif_table.hAlign = 'LEFT'
        dammif_table = KeepTogether([dammif_text, dammif_table])

        elements = [dammif_table]

    else:
        elements = []

    return elements

def generate_denss_params(denss_data):
    styles = getSampleStyleSheet()

    denss_text = Paragraph('Electron density reconstructions:', styles['Heading2'])

    table_pairs = [
        ('', 'prefix'),
        ('Mode', 'mode'),
        ('Symmetry', 'sym'),
        ('Symmetry axis', 'sym_axis'),
        ('Symmetry factpr', 'sym_factor'),
        ('Number of reconstructions', 'num'),
        ('Averaged', 'average'),
        ('Refined', 'refined'),
        ('Mean RSC', 'rsc'),
        ('Included models', 'included'),
        ('Resolution', 'res'),
        ]

    table_dict = OrderedDict()

    table_data = []

    required_data = ['']


    for info in denss_data:
        if info is not None:
            for header, key in table_pairs:
                value = getattr(info, key)

                if value == -1:
                    value = ''

                else:
                    if key == 'rsc':
                        value = '{} +/- {}'.format(text_round(value, 3),
                            text_round(info.rsc_std, 3))
                    elif key == 'res':
                        value = '{}'.format(text_round(value, 1))
                    elif key == 'included':
                        value = '{} of {}'.format(value, info.num)
                    elif not isinstance(value, str):
                        value = '{}'.format(value)

                if header in table_dict:
                    table_dict[header].append(value)
                else:
                    table_dict[header] = [value]

    for header, values in table_dict.items():
        if header in required_data:
            table_entry = [header]
            table_entry.extend(values)
            table_data.append(table_entry)
        else:
            if any(val != '' for val in values):
                table_entry = [header]
                table_entry.extend(values)
                table_data.append(table_entry)

    if len(table_data) > 1:
        denss_table = Table(table_data)

        table_style = TableStyle(
            [('LINEBELOW', (0, 0), (-1, 0), 1, colors.black),
            ('LINEAFTER', (0, 0), (0,-1), 1, colors.black),
            ])

        denss_table.setStyle(table_style)
        denss_table.hAlign = 'LEFT'
        denss_table = KeepTogether([denss_text, denss_table])

        elements = [denss_table]

    else:
        elements = []

    return elements

def make_figure(figure, caption, img_width, img_height, styles):
    """
    Takes as input matplotlib figure, a string, and image width and height in
    inches and returns a flowable with image and caption thnat will stay together.
    """
    datadir = os.path.abspath(os.path.expanduser(tempfile.gettempdir()))
    filename = tempfile.NamedTemporaryFile(dir=datadir).name
    filename = os.path.split(filename)[-1] + '.png'
    filename = os.path.join(datadir, filename)

    global temp_files
    temp_files.append(filename) #Note defined at a module level

    figure.savefig(filename, dpi=300)
    plt.close(figure)
    image = Image(filename, img_width*inch, img_height*inch, lazy=2)
    image.hAlign = 'CENTER'

    text = Paragraph(caption, styles['Normal'])

    return_fig = KeepTogether([image, text])

    return return_fig


###### New stuff ######

def run_efa_for_report(secm, efa_ranges, prof_type, efa_start, efa_end,
    efa_method, efa_iter_limit, efa_tolerance):
    efa_results = SASCalc.run_full_efa(secm, efa_ranges, prof_type, int(efa_start),
        int(efa_end), efa_method, int(efa_iter_limit), float(efa_tolerance))

    return efa_results

def run_regals_for_report(secm, regals_component_settings, prof_type, regals_start,
    regals_end, regals_x_cal, min_iter, max_iter, tol, conv_type):
    regals_results = SASCalc.run_full_regals(secm, regals_component_settings, prof_type,
        int(regals_start), int(regals_end), regals_x_cal, min_iter, max_iter,
        tol, conv_type)

    return regals_results

def run_ambimeter_for_report(ift, settings):
    atsas_dir = settings.get('ATSASDir')

    a_score, a_cats, a_interp = SASCalc.run_ambimeter_from_ift(ift, atsas_dir)

    return a_score, a_cats, a_interp

def make_report_from_raw(name, out_dir, profiles, ifts, series, settings,
        dammif_data=None):

    profile_data = [SAXSData(copy.deepcopy(profile)) for profile in profiles]

    ift_data = [IFTData(copy.deepcopy(ift)) for ift in ifts]

    for j, ift in enumerate(ift_data):
        if ift.type == 'GNOM':
            try:
                a_score, a_cats, a_interp = run_ambimeter_for_report(ifts[j],
                    settings)

                ift.a_score = a_score
                ift.a_cats = a_cats
                ift.a_interp = a_interp
            except Exception:
                pass

    series_data = [SECData(copy.deepcopy(s)) for s in series]

    dammif_results = []

    if dammif_data is not None:
        for dammif_file in dammif_data:
            if dammif_file is not None:
                results = parse_dammif_file(dammif_file)
            else:
                results = None

            dammif_results.append(results)

    extra_data = {'dammif': dammif_results}

    generate_report(name, out_dir, profile_data, ift_data, series_data,
        extra_data)


