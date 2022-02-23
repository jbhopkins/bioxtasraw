'''
Created on Jul 11, 2010

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

from math import atan
import sys
import os

import numpy as np
import pyFAI, pyFAI.geometryRefinement, pyFAI.massif

raw_path = os.path.abspath(os.path.join('.', __file__, '..', '..'))
if raw_path not in os.sys.path:
    os.sys.path.append(raw_path)

import bioxtasraw.SASExceptions as SASExceptions
import bioxtasraw.SASProc as SASProc

def calcTheta(sd_distance, pixel_size, q_length_pixels):
    '''
     Calculates theta for a sample-detector distance,
     the detector pixel size and the length of the pixels.

     sd_distance = sample detector distance
     pixel_size = Detector pixel size
     q__pixel_length = length of q-vector in pixels.
    '''

    if q_length_pixels == 0:
        return 0
    else:
        theta = .5 * atan( (q_length_pixels * pixel_size) / sd_distance )
        return theta

#########################################
#Methods adapted from pyFAI methods of the same or similar name to automatically get points in calibrant rings and fit them

def new_grp(img, loc, gpt, defaultNbPoints, ring, mask):
    # some weirdness in making the image axis go from 0 to max in y, instead of max to 0
    mask = np.flipud(mask)

    massif = pyFAI.massif.Massif(img, mask=mask)
    points = massif.find_peaks([loc[1], loc[0]], defaultNbPoints)

    if points:
        gpt.append(points, ring=ring)

    return points, gpt


class RAWCalibration(object):
    # A mash up of the pyFAI.calibration AbstractCalibration and Calibration classes

    PARAMETERS = ["dist", "poni1", "poni2", "rot1", "rot2", "rot3", "wavelength"]

    def __init__(self, img, wavelength = None, detector = None, calibrant = None,
        pixelSize = None, gaussianWidth = None):
        self.gaussianWidth = gaussianWidth
        self.detector = detector
        self.calibrant = calibrant
        self.pixelSize = pixelSize
        self.wavelength = wavelength
        self.img = img

        self.fixed = pyFAI.utils.FixedParameters()
        self.fixed.add_or_discard("wavelength", True)
        self.fixed.add_or_discard("rot1", True)
        self.fixed.add_or_discard("rot2", True)
        self.fixed.add_or_discard("rot3", True)
        self.max_iter = 1000
        self.interactive = False
        self.weighted = False

    def initgeoRef(self):
        # Modified initgeoRef from the pyFAI.calibration.Calibration class
            """
            Tries to initialise the GeometryRefinement (dist, poni, rot)
            Returns a dictionary of key value pairs
            """
            defaults = {"dist": 0.1, "poni1": 0.0, "poni2": 0.0,
                        "rot1": 0.0, "rot2": 0.0, "rot3": 0.0}
            if self.detector:
                try:
                    p1, p2, _p3 = self.detector.calc_cartesian_positions()
                    defaults["poni1"] = p1.max() / 2.
                    defaults["poni2"] = p2.max() / 2.
                except Exception as err:
                    print(err)
            if self.ai:
                for key in defaults:  # not PARAMETERS which holds wavelength
                    val = getattr(self.ai, key, None)
                    if val is not None:
                        defaults[key] = val
            return defaults

    def refine(self):
        # Modified refine from the pyFAI.calibration.Calibration class
        """
        Contains the geometry refinement part specific to Calibration
        Sets up the initial guess when starting pyFAI-calib
        """
        # First attempt
        defaults = self.initgeoRef()
        self.geoRef = pyFAI.geometryRefinement.GeometryRefinement(self.data,
                                         detector=self.detector,
                                         wavelength=self.wavelength,
                                         calibrant=self.calibrant,
                                         **defaults)
        self.geoRef.refine2(1000000, fix=self.fixed)
        scor = self.geoRef.chi2()
        pars = [getattr(self.geoRef, p) for p in self.PARAMETERS]

        scores = [(scor, pars), ]

        # Second attempt
        defaults = self.initgeoRef()
        self.geoRef = pyFAI.geometryRefinement.GeometryRefinement(self.data,
                                         detector=self.detector,
                                         wavelength=self.wavelength,
                                         calibrant=self.calibrant,
                                         **defaults)
        self.geoRef.guess_poni()
        self.geoRef.refine2(1000000, fix=self.fixed)
        scor = self.geoRef.chi2()
        pars = [getattr(self.geoRef, p) for p in self.PARAMETERS]

        scores.append((scor, pars))

        # Choose the best scoring method: At this point we might also ask
        # a user to just type the numbers in?
        scores.sort()
        scor, pars = scores[0]
        for parval, parname in zip(pars, self.PARAMETERS):
            setattr(self.geoRef, parname, parval)

        # Now continue as before
        self.refine2()

    def refine2(self):
        # Modified refine from the pyFAI.calibration.AbstractCalibration class
        """
        Contains the common geometry refinement part
        """
        try:
            previous = sys.maxint
        except Exception:
            previous = sys.maxsize
        finished = False
        while not finished:
            count = 0
            if "wavelength" in self.fixed:
                while (previous > self.geoRef.chi2()) and (count < self.max_iter):
                    if (count == 0):
                        previous = sys.maxsize
                    else:
                        previous = self.geoRef.chi2()
                    self.geoRef.refine2(1000000, fix=self.fixed)
                    count += 1
            else:
                while previous > self.geoRef.chi2_wavelength() and (count < self.max_iter):
                    if (count == 0):
                        previous = sys.maxsize
                    else:
                        previous = self.geoRef.chi2()
                    self.geoRef.refine2_wavelength(1000000, fix=self.fixed)
                    count += 1
                self.points.setWavelength_change2th(self.geoRef.wavelength)
            # self.geoRef.save(self.basename + ".poni")
            self.geoRef.del_ttha()
            self.geoRef.del_dssa()
            self.geoRef.del_chia()
            # tth = self.geoRef.twoThetaArray(self.img.shape)
            # dsa = self.geoRef.solidAngleArray(self.img.shape)
#            self.geoRef.chiArray(self.peakPicker.shape)
#            self.geoRef.cornerArray(self.peakPicker.shape)

            if self.interactive:
                finished = self.prompt()
            else:
                finished = True
            if not finished:
                previous = sys.maxsize

def calcAbsoluteScaleWaterConst(water_sasm, emptycell_sasm, I0_water, raw_settings):

    if emptycell_sasm is None or emptycell_sasm == 'None' or water_sasm == 'None' or water_sasm is None:
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

def normalizeAbsoluteScaleCarbon(sasm, raw_settings):
    abs_scale_constant = float(raw_settings.get('NormAbsCarbonConst'))
    sam_thick = float(raw_settings.get('NormAbsCarbonSamThick'))

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
    sasm.scaleRawIntensity(1./sample_ctr_ups_val)
    bkg_sasm.scale((1./bkg_ctr_ups_val)*sample_trans)

    try:
        sub_sasm = SASProc.subtract(sasm, bkg_sasm, forced = True, full = True)
    except SASExceptions.DataNotCompatible:
        sasm.scaleRawIntensity(sample_ctr_ups_val)
        raise SASExceptions.AbsScaleNormFailed('Absolute scale failed because empty scattering could not be subtracted')

    sub_sasm.scaleRawIntensity(1./(sample_trans)/sam_thick)
    sub_sasm.scaleRawIntensity(abs_scale_constant)

    sasm.setRawQ(sub_sasm.getRawQ())
    sasm.setRawI(sub_sasm.getRawI())
    sasm.setRawErr(sub_sasm.getRawErr())
    sasm.scale(1.)
    sasm.setQrange((0,len(sasm.q)))

    bkg_sasm.scale(1.)

    abs_scale_params = {
        'Method'    : 'Glassy_carbon',
        'Absolute_scale_factor': abs_scale_constant,
        'Sample_thickness_[mm]': sam_thick,
        'Ignore_background': False,
        }

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
    if (raw_settings.get('NormAbsCarbon') and
        not raw_settings.get('NormAbsCarbonIgnoreBkg')):
        normalizeAbsoluteScaleCarbon(sasm, raw_settings)
