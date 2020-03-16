'''
Created on Jul 7, 2010

@author: specuser

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

import sys
import math

import numpy as np
from numba import jit, prange
import pyFAI

import SASParser
import SASCalib
import SASM
import SASMask
import RAWGlobals
import RAWSettings

def calcExpression(expr, img_hdr, file_hdr):

        if expr != '':
            mathparser = SASParser.PyMathParser()
            mathparser.addDefaultFunctions()
            mathparser.addDefaultVariables()
            mathparser.addSpecialVariables(file_hdr)
            mathparser.addSpecialVariables(img_hdr)
            mathparser.expression = expr

            val = mathparser.evaluate()
            return val
        else:
            return None

def getBindListDataFromHeader(raw_settings, img_hdr, file_hdr, keys):

    bind_list = raw_settings.get('HeaderBindList')

    result = []

    for each_key in keys:
        if each_key in bind_list and bind_list[each_key][1] is not None:
            data = bind_list[each_key][1]
            hdr_choice = data[1]
            key = data[0]

            if hdr_choice == 'imghdr': hdr = img_hdr
            else: hdr = file_hdr

            if key in hdr:
                try:
                    val = float(hdr[key])

                except ValueError:
                    sys.stderr.write('\n** ' + each_key + ' bound to header value "' + str(key) + ': ' + str(hdr[key]) + '" could not be converted to a float! **\n')
                    result.append(None)
                    continue

                try:
                    # Calculate value with modifier
                    if bind_list[each_key][2] != '':
                        expr = bind_list[each_key][2]

                        val = calcExpression(expr, img_hdr, file_hdr)
                        result.append(val)
                    else:
                        result.append(val)
                except ValueError:
                    sys.stderr.write('\n** Expression: ' + expr + ' does not give a valid result when calculating ' +str(each_key)+' **\n')
                    result.append(None)
            else:
                result.append(None)
        else:
            result.append(None)

    return result

def integrateCalibrateNormalize(img, parameters, raw_settings):
    use_hdr_config = raw_settings.get('UseHeaderForConfig')

    img_hdr = parameters['imageHeader']
    file_hdr = parameters['counters']

    # Loads a different configuration file based on definition in the image header
    if use_hdr_config:
        prefix = SASImage.getBindListDataFromHeader(raw_settings, img_hdr, file_hdr, keys = ['Config Prefix'])[0]

        if prefix is None:
           raise SASExceptions.ImageLoadError(['"Use header for new config load" is enabled in General Settings.\n',
                                               'The binding "Config Prefix" was however not found in header,',
                                               'not set in header options (See "Image/Header Format" in options) or not a number.'])
        else:
            prefix = str(int(prefix))

        settings_folder = raw_settings.get('HdrLoadConfigDir')

        # If the folder is not set.. look in the folder where the image is
        if settings_folder == 'None' or settings_folder == '':
            settings_folder, fname = os.path.split(filename)

        settings_path = os.path.join(settings_folder, str(prefix) + '.cfg')

        if not os.path.exists(settings_path):
            raise SASExceptions.ImageLoadError(['"Use header for new config load" is enabled in General Settings.\n',
                                                'Config file ' + settings_path + ' does not exist.',
                                                'Check the path in the "General Settings" options. Clear the field to make RAW look for the config file in the same folder as the image.'])

        RAWSettings.loadSettings(raw_settings, settings_path, auto_load = True)

        mask_dict = raw_settings.get('Masks')
        img_dim = raw_settings.get('MaskDimension')

        #Create the masks
        for each_key in mask_dict:
            masks = mask_dict[each_key][1]

            if masks is not None:
                mask_img = SASMask.createMaskMatrix(img_dim, masks)
                mask_param = mask_dict[each_key]
                mask_param[0] = mask_img
                mask_param[1] = masks

    # Get settings
    use_hdr_mask = raw_settings.get('UseHeaderForMask')
    use_hdr_calib = raw_settings.get('UseHeaderForCalib')
    do_normalization = raw_settings.get('EnableNormalization')
    do_flatfield = raw_settings.get('NormFlatfieldEnabled')
    do_solidangle = raw_settings.get('DoSolidAngleCorrection')
    normlist = raw_settings.get('NormalizationList')

    #Absolute scale values
    abs_scale_water = raw_settings.get('NormAbsWater')
    abs_scale_water_factor = float(raw_settings.get('NormAbsWaterConst'))
    abs_scale_gc = raw_settings.get('NormAbsCarbon')
    abs_scale_gc_ignore_bkg = raw_settings.get('NormAbsCarbonIgnoreBkg')
    abs_scale_gc_factor = float(raw_settings.get('NormAbsCarbonConst'))

    sd_distance = raw_settings.get('SampleDistance')
    pixel_size = raw_settings.get('DetectorPixelSizeX')
    wavelength = raw_settings.get('WaveLength')
    bin_size = int(raw_settings.get('Binsize'))
    x_c = float(raw_settings.get('Xcenter'))
    y_c = float(raw_settings.get('Ycenter'))


    # Load mask
    if use_hdr_mask and img_fmt == 'SAXSLab300':
        # ********************
        # If the file is a SAXSLAB file, then get mask parameters from the header and modify the mask
        # then apply it...
        #
        # Mask should be not be changed, but should be created here. If no mask information is found, then
        # use the user created mask. There should be a force user mask setting.
        #
        # ********************
        try:
            mask_patches = SASMask.createMaskFromHdr(img, img_hdr, flipped = raw_settings.get('DetectorFlipped90'))
            bs_mask_patches = masks['BeamStopMask'][1]

            if bs_mask_patches is not None:
                all_mask_patches = mask_patches + bs_mask_patches
            else:
                all_mask_patches = mask_patches

            bs_mask = SASMask.createMaskMatrix(img.shape, all_mask_patches)
        except KeyError:
            raise SASExceptions.HeaderMaskLoadError('bsmask_configuration not found in header.')

    else:
        masks = raw_settings.get('Masks')
        bs_mask = masks['BeamStopMask'][0]
        dc_mask = masks['ReadOutNoiseMask'][0]
        tbs_mask = masks['TransparentBSMask'][0]

    if bs_mask is None:
        bs_mask = np.zeroes(img.shape)
    else:
        bs_mask = np.logical_not(bs_mask) #Invert mask for pyFAI

    # Get values from image header if applicable
    if use_hdr_calib:
        result = getBindListDataFromHeader(raw_settings, img_hdr, file_hdr,
            keys=['Sample Detector Distance', 'Detector Pixel Size', 'Wavelength',
            'Beam X Center', 'Beam Y Center'])

        if result[0] is not None:
            sd_distance = result[0]
        if result[1] is not None:
            pixel_size = result[1]
        if result[2] is not None:
            wavelength = result[2]
        if result[3] is not None:
            x_c = result[3]
        if result[4] is not None:
            y_c = result[4]

    # ********* WARNING WARNING WARNING ****************#
    # Hmm.. axes start from the lower left, but array coords starts
    # from upper left:
    #####################################################
    y_c = img.shape[0]-y_c


    # if readoutNoise_mask is None:
    #     readoutNoiseFound = 0
    #     readoutNoise_mask = np.zeros(img.shape, dtype = np.float64)
    # else:
    #     readoutNoiseFound = 1

    # readoutN = np.zeros((1,4), dtype = np.float64)

    # Find the maximum distance to the edge in the image:
    img = np.float64(img)
    ylen, xlen = img.shape

    xlen = int(xlen)
    ylen = int(ylen)
    maxlen1 = int(max(xlen - x_c, ylen - y_c, xlen - (xlen - x_c), ylen - (ylen - y_c)))

    diag1 = int(np.sqrt((xlen-x_c)**2 + y_c**2))
    diag2 = int(np.sqrt((x_c**2 + y_c**2)))
    diag3 = int(np.sqrt((x_c**2 + (ylen-y_c)**2)))
    diag4 = int(np.sqrt((xlen-x_c)**2 + (ylen-y_c)**2))

    maxlen = int(max(diag1, diag2, diag3, diag4, maxlen1))
    npts = maxlen//bin_size


    # Create radially averaged file metadata
    parameters['normalizations'] = {}
    if do_solidangle:
        parameters['normalizations']['Solid_Angle_Correction'] = 'On'

    calibrate_dict = {'Sample_Detector_Distance'    : sd_distance,
                    'Detector_Pixel_Size'           : pixel_size,
                    'Wavelength'                    : wavelength,
                    'Beam_Center_X'                 : x_c,
                    'Beam_Center_Y'                 : y_c,
                    'Radial_Average_Method'         : 'pyFAI',
                    }

    parameters['calibration_params'] = calibrate_dict
    parameters['raw_version'] = RAWGlobals.version
    parameters['config_file'] = raw_settings.get('CurrentCfg')

    if raw_settings.get('EnableMetadata'):
        meta_list = raw_settings.get('MetadataList')
        if meta_list is not None and len(meta_list) > 0:
            metadata = {key:value for (key, value) in meta_list}
            parameters['metadata'] = metadata

    # Calculate the ROI if applicable
    if tbs_mask is not None:
        roi_counter = img[tbs_mask==1].sum()
        parameters['counters']['roi_counter'] = roi_counter

    all_norms_mult = True
    norm_factor = 1.0
    #Calculate the normalization parameter if applicable
    if normlist is not None and do_normalization:
        parameters['normalizations']['Counter_norms'] = normlist

        for op, expr in normlist:
            if op != '/' and op != '*':
                all_norms_mult = False
                break

            else:
                val = calcExpression(expr, img_hdr, file_hdr)

                if val is not None:
                    val = float(val)
                else:
                    raise ValueError
                if op == '/':
                    if val == 0:
                        raise ValueError('Divide by Zero when normalizing')
                    else:
                        norm_factor = norm_factor/val

                elif op == '*':
                    if val == 0:
                       raise ValueError('Multiply by Zero when normalizing')
                    else:
                        norm_factor = norm_factor*val

        if not all_norms_mult:
            norm_factor = 1.0

    if abs_scale_water:
        parameters['normalizations']['Absolute_scale'] = {}
        parameters['normalizations']['Absolute_scale']['Method'] = 'Water'
        parameters['normalizations']['Absolute_scale']['Absolute_scale_factor'] = abs_scale_water_factor

        norm_factor = norm_factor * abs_scale_water_factor

    elif abs_scale_gc and abs_scale_gc_ignore_bkg:
        parameters['normalizations']['Absolute_scale'] = {}
        parameters['normalizations']['Absolute_scale']['Method'] = 'Glassy_carbon'
        parameters['normalizations']['Absolute_scale']['Ignore_background'] = True
        parameters['normalizations']['Absolute_scale']['Absolute_scale_factor'] = abs_scale_gc_factor

        norm_factor = norm_factor * abs_scale_gc_factor

    # pyFAI expects a divisible normalization factor
    norm_factor = 1./norm_factor

    #Put everything in appropriate units
    pixel_size = pixel_size *1e-6 #convert pixel size to m
    wavelength = wavelength*1e-10 #convert wl to m

    ai = pyFAI.AzimuthalIntegrator()

    ai.wavelength = wavelength
    ai.pixel1 = pixel_size
    ai.pixel2 = pixel_size
    ai.setFit2D(sd_distance, x_c, y_c)

    if do_flatfield:
        flatfield_filename = raw_settings.get('NormFlatfieldFile')
        ai.set_flatfiles(flatfield_filename)

    qmin_theta = SASCalib.calcTheta(sd_distance*1e-3, pixel_size, 0)
    qmin = ((4 * math.pi * math.sin(qmin_theta)) / (wavelength*1e10))

    qmax_theta = SASCalib.calcTheta(sd_distance*1e-3, pixel_size, maxlen)
    qmax = ((4 * math.pi * math.sin(qmax_theta)) / (wavelength*1e10))

    q_range = (qmin, qmax)

    #Carry out the integration
    q, iq, errorbars = ai.integrate1d(img, npts, mask=bs_mask,
        correctSolidAngle=do_solidangle, error_model='poisson', unit='q_A^-1',
        radial_range = q_range, method='nosplit_csr',
        normalization_factor=norm_factor)

    errorbars = np.nan_to_num(errorbars)

    sasm = SASM.SASM(iq, q, errorbars, parameters)

    img_hdr = sasm.getParameter('imageHeader')
    file_hdr = sasm.getParameter('counters')

    if normlist is not None and do_normalization and not all_norms_mult:
        for each in normlist:
            op, expr = each

            val = calcExpression(expr, img_hdr, file_hdr)

            if val is not None:
                val = float(val)
            else:
                raise ValueError

            if op == '/':
               if val == 0:
                   raise ValueError('Divide by Zero when normalizing')

               sasm.scaleBinnedIntensity(1./val)

            elif op == '+':
                sasm.offsetBinnedIntensity(val)

            elif op == '*':
                if val == 0:
                   raise ValueError('Multiply by Zero when normalizing')

                sasm.scaleBinnedIntensity(val)

            elif op == '-':
                sasm.offsetBinnedIntensity(-val)

    return sasm
