'''
Created on Jul 16, 2010

@author: Soren Nielsen

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
import six
from six.moves import cPickle as pickle

import copy
import os
import json

import wx
import numpy as np

raw_path = os.path.abspath(os.path.join('.', __file__, '..', '..'))
if raw_path not in os.sys.path:
    os.sys.path.append(raw_path)

import bioxtasraw.RAWGlobals as RAWGlobals
import bioxtasraw.SASMask as SASMask
import bioxtasraw.SASUtils as SASUtils

class RawGuiSettings(object):
    '''
    This object contains all the settings nessecary for the GUI.

    '''
    def __init__(self, settings = None):
        '''
        Accepts a dictionary argument for the parameters. Uses default is no settings are given.
        '''

        self._params = settings

        if settings is None:
            file_defs, _ = SASUtils.loadFileDefinitions()
            self._params = {
                'RequiredVersion'       : ['2.0.0', wx.NewIdRef(), 'text'],

                #Water absolute scale
                'NormAbsWater'      	: [False,   wx.NewIdRef(),  'bool'],
                'NormAbsWaterI0'    	: [0.01632, wx.NewIdRef(),  'float'],
                'NormAbsWaterTemp'  	: ['25',    wx.NewIdRef(),  'choice'],
                'NormAbsWaterConst' 	: [1.0,     wx.NewIdRef(),  'float'],
                'NormAbsWaterFile'      : [None, wx.NewIdRef(), 'text'],
                'NormAbsWaterEmptyFile' : [None, wx.NewIdRef(), 'text'],

                #Glassy carbon absolute scale
                'NormAbsCarbon'             : [False, wx.NewIdRef(), 'bool'],
                'NormAbsCarbonIgnoreBkg'    : [True, wx.NewIdRef(), 'bool'],
                'NormAbsCarbonFile'         : [None, wx.NewIdRef(), 'text'],
                'NormAbsCarbonEmptyFile'    : [None, wx.NewIdRef(), 'text'],
                'NormAbsCarbonSamEmptyFile' : [None, wx.NewIdRef(), 'text'],
                'NormAbsCarbonCalFile'      : [None, wx.NewIdRef(), 'text'],
                'NormAbsCarbonThick'        : [1.055, wx.NewIdRef(), 'float'],
                'NormAbsCarbonSamThick'     : [1.0, wx.NewIdRef(), 'float'],
                'NormAbsCarbonUpstreamCtr'  : [None, wx.NewIdRef(), 'choice'],
                'NormAbsCarbonDownstreamCtr': [None, wx.NewIdRef(), 'choice'],
                'NormAbsCarbonConst'        : [1.0, wx.NewIdRef(), 'float'],
                'NormAbsCarbonSamEmptySASM' : [None],

                #AUtomatic processing
                'AutoBgSubtract'        : [False, wx.NewIdRef(),  'bool'],

                'AutoBIFT'              : [False, wx.NewIdRef(), 'bool'],
                'AutoAvg'               : [False, wx.NewIdRef(), 'bool'],
                'AutoAvgRemovePlots'    : [False, wx.NewIdRef(), 'bool'],

                'AutoAvgRegExp'         : ['', wx.NewIdRef(), 'text'],
                'AutoAvgNameRegExp'     : ['', wx.NewIdRef(), 'text'],
                'AutoAvgNoOfFrames'     : [1,  wx.NewIdRef(),  'int'],
                'AutoBgSubRegExp'       : ['', wx.NewIdRef(), 'text'],

                #Detector image orientation
                'DetectorFlipLR' : [True, wx.NewIdRef(), 'bool'],
                'DetectorFlipUD' : [False, wx.NewIdRef(), 'bool'],

                #Special settings for Xenocs/SAXSLAB
                'UseHeaderForMask'      : [False, wx.NewIdRef(), 'bool'],
                'UseHeaderForConfig'    : [False, wx.NewIdRef(), 'bool'],
                'DetectorFlipped90'     :[False, wx.NewIdRef(), 'bool'],

                #pyFAI radial averaging and calibration settings
                'DoSolidAngleCorrection'    : [True, wx.NewIdRef(), 'bool'],
                'DoPolarizationCorrection'  : [False, wx.NewIdRef(), 'bool'],
                'PolarizationFactor'        : [0, wx.NewIdRef(), 'float'],
                'IntegrationMethod'         : ['nosplit_csr', wx.NewIdRef(), 'choice'],
                'AngularUnit'               : ['q_A^-1', wx.NewIdRef(), 'choice'],
                'ErrorModel'                : ['poisson', wx.NewIdRef(), 'choice'],
                'UseImageForVariance'       : [False, wx.NewIdRef(), 'bool'],
                'AzimuthalIntegrator'       : [None],

                #Dark correction
                'DarkCorrEnabled'       : [False,   wx.NewIdRef(),  'bool'],
                'DarkCorrFilename'      : ['', wx.NewIdRef(), 'text'],
                'DarkCorrImage'         : [None],

                #Flatfield correction
                'NormFlatfieldEnabled'  : [False,   wx.NewIdRef(),  'bool'],
                'NormFlatfieldFile'     : ['', wx.NewIdRef(), 'text'],
                'NormFlatfieldImage'    : [None],

                #Q-CALIBRATION
                'WaveLength'            : [1.0,  wx.NewIdRef(), 'float'],
                'SampleDistance'        : [1000, wx.NewIdRef(), 'float'],
                'Detector'              : ['Other', wx.NewIdRef(), 'choice'],
                'DetectorPixelSizeX'    : [172.0, wx.NewIdRef(), 'float'],
                'DetectorPixelSizeY'    : [172.0, wx.NewIdRef(), 'float'],
                'DetectorTilt'          : [0.0, wx.NewIdRef(), 'float'],
                'DetectorTiltPlanRot'   : [0.0, wx.NewIdRef(), 'float'],
                'Xcenter'               : [0.0, wx.NewIdRef(), 'float'],
                'Ycenter'               : [0.0, wx.NewIdRef(), 'float'],

                #BINNING
                'BinType'   : ['Linear', wx.NewIdRef(), 'choice'],
                'Binsize'   : [1,     wx.NewIdRef(), 'int'],

                #Trimming
                'StartPoint'    : [0,     wx.NewIdRef(), 'int'],
                'EndPoint'      : [0,     wx.NewIdRef(), 'int'],

                #MASKING
                'BackgroundSASM'          : [None, wx.NewIdRef(), 'text'],

                'DataSECM'                : [None, wx.NewIdRef(), 'text'],

                                                                    #mask, mask_patches
                'Masks'                   : [{'BeamStopMask'     : [None, None],
                                              'TransparentBSMask': [None, None],
                                             }],

                'MaskDimension'          : [1024,1024],

                #DEFAULT BIFT PARAMETERS
                'maxDmax'     : [400.0,  wx.NewIdRef(), 'float'],
                'minDmax'     : [10.0,   wx.NewIdRef(), 'float'],
                'DmaxPoints'  : [10,     wx.NewIdRef(), 'int'],
                'maxAlpha'    : [1e10,   wx.NewIdRef(), 'float'],
                'minAlpha'    : [150.0,  wx.NewIdRef(), 'float'],
                'AlphaPoints' : [16,     wx.NewIdRef(), 'int'],
                'PrPoints'    : [100,    wx.NewIdRef(), 'int'],
                'mcRuns'      : [300,    wx.NewIdRef(), 'int'],

                #ARTIFACT REMOVAL:
                'ZingerRemovalRadAvg'       : [False,   wx.NewIdRef(), 'bool'],
                'ZingerRemovalRadAvgStd'    : [5.0,     wx.NewIdRef(), 'float'],
                'ZingerRemovalRadAvgIter'   : [5,       wx.NewIdRef(), 'int'],

                'ZingerRemoval'     : [False, wx.NewIdRef(), 'bool'],
                'ZingerRemoveSTD'   : [4,     wx.NewIdRef(), 'int'],
                'ZingerRemoveWinLen': [10,    wx.NewIdRef(), 'int'],
                'ZingerRemoveIdx'   : [10,    wx.NewIdRef(), 'int'],

                #SAVE DIRECTORIES
                'ProcessedFilePath'    : [None,  wx.NewIdRef(), 'text'],
                'AveragedFilePath'     : [None,  wx.NewIdRef(), 'text'],
                'SubtractedFilePath'   : [None,  wx.NewIdRef(), 'text'],
                'BiftFilePath'         : [None,  wx.NewIdRef(), 'text'],
                'GnomFilePath'         : [None,  wx.NewIdRef(), 'text'],
                'AutoSaveOnImageFiles' : [False, wx.NewIdRef(), 'bool'],
                'AutoSaveOnAvgFiles'   : [False, wx.NewIdRef(), 'bool'],
                'AutoSaveOnSub'        : [False, wx.NewIdRef(), 'bool'],
                'AutoSaveOnBift'       : [False, wx.NewIdRef(), 'bool'],
                'AutoSaveOnGnom'       : [False, wx.NewIdRef(), 'bool'],

                #IMAGE FORMATS
                'ImageFormat'          : ['Pilatus', wx.NewIdRef(), 'choice'],

                #HEADER FORMATS
                'ImageHdrFormat'       : ['None', wx.NewIdRef(), 'choice'],

                'ImageHdrList'         : [None],
                'FileHdrList'          : [None],

                'UseHeaderForCalib'    : [False, wx.NewIdRef(), 'bool'],

                # Header bind list with [(Description : parameter key, header_key)]
                'HeaderBindList'       : [{'Beam X Center'              : ['Xcenter',           None, ''],
                                           'Beam Y Center'              : ['Ycenter',           None, ''],
                                           'Sample Detector Distance'   : ['SampleDistance',    None, ''],
                                           'Wavelength'                 : ['WaveLength',        None, ''],
                                           'Detector X Pixel Size'      : ['DetectorPixelSizeX', None, ''],
                                           'Detector Y Pixel Size'      : ['DetectorPixelSizeY', None, ''],
                                           'Detector Tilt'              : ['DetectorTilt', None, ''],
                                           'Detector Tilt Plane Rotation':['DetectorTiltPlanRot', None, ''],
                                           }],
                                           # 'Number of Frames'         : ['NumberOfFrames',    None, '']}],

                'NormalizationList'    : [None, wx.NewIdRef(), 'text'],
                'EnableNormalization'  : [True, wx.NewIdRef(), 'bool'],

                'MetadataList'         : [None, wx.NewIdRef(), 'text'],
                'EnableMetadata'       : [True, wx.NewIdRef(), 'bool'],

                'OnlineFilterList'     : [None, wx.NewIdRef(), 'text'],
                'EnableOnlineFiltering': [False, wx.NewIdRef(), 'bool'],
                'OnlineModeOnStartup'  : [False, wx.NewIdRef(), 'bool'],
                'OnlineStartupDir'     : [None, wx.NewIdRef(), 'text'],
                'HdrLoadConfigDir'     : [None, wx.NewIdRef(), 'text'],

                'MWStandardMW'         : [0, wx.NewIdRef(), 'float'],
                'MWStandardI0'         : [0, wx.NewIdRef(), 'float'],
                'MWStandardConc'       : [0, wx.NewIdRef(), 'float'],
                'MWStandardFile'       : ['', wx.NewIdRef(), 'text'],

                #Initialize volume of correlation molecular mass values.
                #Values from Rambo, R. P. & Tainer, J. A. (2013). Nature. 496, 477-481.
                'MWVcType'      : ['Protein', wx.NewIdRef(), 'choice'],
                'MWVcAProtein'  : [1.0, wx.NewIdRef(), 'float'], #The 'A' coefficient for proteins
                'MWVcBProtein'  : [0.1231, wx.NewIdRef(), 'float'], #The 'B' coefficient for proteins
                'MWVcARna'      : [0.808, wx.NewIdRef(), 'float'], #The 'A' coefficient for proteins
                'MWVcBRna'      : [0.00934, wx.NewIdRef(), 'float'], #The 'B' coefficient for proteins
                'MWVcCutoff'    : ['Default', wx.NewIdRef(), 'choice'],
                'MWVcQmax'      : [0.5, wx.NewIdRef(), 'float'], #qmax if 'Manual' is selected for cutoff

                #Initialize porod volume molecularm ass values.
                'MWVpRho'               : [0.83*10**(-3), wx.NewIdRef(), 'float'], #The density in kDa/A^3
                'MWVpCutoff'            : ['Default', wx.NewIdRef(), 'choice'],
                'MWVpQmax'              : [0.5, wx.NewIdRef(), 'float'], #qmax if 'Manual' is selected for cutoff

                #Initialize Absolute scattering calibration values.
                #Default values from Mylonas & Svergun, J. App. Crys. 2007.
                'MWAbsRhoMprot'         : [3.22*10**23, wx.NewIdRef(), 'float'], #e-/g, # electrons per dry mass of protein
                'MWAbsRhoSolv'          : [3.34*10**23, wx.NewIdRef(), 'float'], #e-/cm^-3, # electrons per volume of aqueous solvent
                'MWAbsNuBar'            : [0.7425, wx.NewIdRef(), 'float'], #cm^3/g, # partial specific volume of the protein
                'MWAbsR0'               : [2.8179*10**-13, wx.NewIdRef(), 'float'], #cm, scattering lenght of an electron

                'CurrentCfg'         : [None],
                'CompatibleFormats'  : [['.rad', '.tiff', '.tif', '.img', '.csv', '.dat', '.txt', '.sfrm', '.dm3', '.edf',
                                         '.xml', '.cbf', '.kccd', '.msk', '.spr', '.h5', '.mccd', '.mar3450', '.npy', '.pnm',
                                          '.No', '.imx_0', '.dkx_0', '.dkx_1', '.png', '.mpa', '.ift', '.sub', '.fit', '.fir',
                                          '.out', '.mar1200', '.mar2400', '.mar2300', '.mar3600', '.int', '.ccdraw'], None],


                #Series Settings:
                'secCalcThreshold'      : [1.02, wx.NewIdRef(), 'float'],
                'IBaselineMinIter'    : [100, wx.NewIdRef(), 'int'],
                'IBaselineMaxIter'    : [2000, wx.NewIdRef(), 'int'],

                #GUI Settings:
                'csvIncludeData'      : [None],
                'ManipItemCollapsed'  : [False, wx.NewIdRef(), 'bool'] ,

                'DatHeaderOnTop'      : [False, wx.NewIdRef(), 'bool'],
                'PromptConfigLoad'    : [True, wx.NewIdRef(), 'bool'],

                #ATSAS settings:
                'autoFindATSAS'       : [True, wx.NewIdRef(), 'bool'],
                'ATSASDir'            : ['', wx.NewIdRef(), 'bool'],

                #GNOM settings
                'gnomExpertFile'        : ['', wx.NewIdRef(), 'text'],
                'gnomForceRminZero'     : ['Y', wx.NewIdRef(), 'choice'],
                'gnomForceRmaxZero'     : ['Y', wx.NewIdRef(), 'choice'],
                'gnomNPoints'           : [0, wx.NewIdRef(), 'int'],
                'gnomInitialAlpha'      : [0.0, wx.NewIdRef(), 'float'],
                'gnomAngularScale'      : [1, wx.NewIdRef(), 'int'],
                'gnomSystem'            : [0, wx.NewIdRef(), 'int'],
                'gnomFormFactor'        : ['', wx.NewIdRef(), 'text'],
                'gnomRadius56'          : [-1, wx.NewIdRef(), 'float'],
                'gnomRmin'              : [-1, wx.NewIdRef(), 'float'],
                'gnomFWHM'              : [-1, wx.NewIdRef(), 'float'],
                'gnomAH'                : [-1, wx.NewIdRef(), 'float'],
                'gnomLH'                : [-1, wx.NewIdRef(), 'float'],
                'gnomAW'                : [-1, wx.NewIdRef(), 'float'],
                'gnomLW'                : [-1, wx.NewIdRef(), 'float'],
                'gnomSpot'              : ['', wx.NewIdRef(), 'text'],
                'gnomExpt'              : [0, wx.NewIdRef(), 'int'],
                'gnomCut8Rg'            : [False, wx.NewIdRef(), 'bool'],

                #DAMMIF settings
                'dammifMode'            : ['Slow', wx.NewIdRef(), 'choice'],
                'dammifSymmetry'        : ['P1', wx.NewIdRef(), 'choice'],
                'dammifAnisometry'      : ['Unknown', wx.NewIdRef(), 'choice'],
                'dammifUnit'            : ['Unknown', wx.NewIdRef(), 'choice'],
                'dammifChained'         : [False, wx.NewIdRef(), 'bool'],
                'dammifConstant'        : ['', wx.NewIdRef(), 'text'],
                'dammifOmitSolvent'     : [True, wx.NewIdRef(), 'bool'],
                'dammifDummyRadius'     : [-1, wx.NewIdRef(), 'float'],
                'dammifSH'              : [-1, wx.NewIdRef(), 'int'],
                'dammifPropToFit'       : [-1, wx.NewIdRef(), 'float'],
                'dammifKnots'           : [-1, wx.NewIdRef(), 'int'],
                'dammifCurveWeight'     : ['e', wx.NewIdRef(), 'choice'],
                'dammifRandomSeed'      : ['', wx.NewIdRef(), 'text'],
                'dammifMaxSteps'        : [-1, wx.NewIdRef(), 'int'],
                'dammifMaxIters'        : [-1, wx.NewIdRef(), 'int'],
                'dammifMaxStepSuccess'  : [-1, wx.NewIdRef(), 'int'],
                'dammifMinStepSuccess'  : [-1, wx.NewIdRef(), 'int'],
                'dammifTFactor'         : [-1, wx.NewIdRef(), 'float'],
                'dammifRgPen'           : [-1, wx.NewIdRef(), 'float'],
                'dammifCenPen'          : [-1, wx.NewIdRef(), 'float'],
                'dammifLoosePen'        : [-1, wx.NewIdRef(), 'float'],
                'dammifAnisPen'         : [-1, wx.NewIdRef(), 'float'],
                'dammifMaxBeadCount'    : [-1, wx.NewIdRef(), 'int'],
                'dammifReconstruct'     : [15, wx.NewIdRef(), 'int'],
                'dammifDamaver'         : [True, wx.NewIdRef(), 'bool'],
                'dammifDamclust'        : [False, wx.NewIdRef(), 'bool'],
                'dammifRefine'          : [True, wx.NewIdRef(), 'bool'],
                'dammifProgram'         : ['DAMMIF', wx.NewIdRef(), 'choice'],
                'dammifExpectedShape'   : ['u', wx.NewIdRef(), 'choice'],

                #DAMMIN settings that are not included in DAMMIF settings
                'damminInitial'         : ['S', wx.NewIdRef(), 'choice'], #Initial DAM
                'damminKnots'           : [20, wx.NewIdRef(), 'int'],
                'damminConstant'        : [0, wx.NewIdRef(), 'float'],
                'damminDiameter'        : [-1, wx.NewIdRef(), 'float'],
                'damminPacking'         : [-1, wx.NewIdRef(), 'float'],
                'damminCoordination'    : [-1, wx.NewIdRef(), 'float'],
                'damminDisconPen'       : [-1, wx.NewIdRef(), 'float'],
                'damminPeriphPen'       : [-1, wx.NewIdRef(), 'float'],
                'damminCurveWeight'     : ['1', wx.NewIdRef(), 'choice'],
                'damminAnealSched'      : [-1, wx.NewIdRef(), 'float'],

                #Weighted Average Settings
                'weightCounter'         : ['', wx.NewIdRef(), 'choice'],
                'weightByError'         : [True, wx.NewIdRef(), 'bool'],

                #Similarity testing settings
                'similarityTest'        : ['CorMap', wx.NewIdRef(), 'choice'],
                'similarityCorrection'  : ['Bonferroni', wx.NewIdRef(), 'choice'],
                'similarityThreshold'   : [0.01, wx.NewIdRef(), 'float'],
                'similarityOnAverage'   : [True, wx.NewIdRef(), 'bool'],

                #Fitting settings
                'errorWeight'           : [True, wx.NewIdRef(), 'bool'],
                'normalizedResiduals'   : [True, wx.NewIdRef(), 'bool'],

                #Denss settings
                'denssVoxel'            : [5, wx.NewIdRef(), 'float'],
                'denssOversampling'     : [3., wx.NewIdRef(), 'float'],
                'denssNElectrons'       : ['', wx.NewIdRef(), 'text'],
                'denssSteps'            : [10000, wx.NewIdRef(), 'int'],
                'denssLimitDmax'        : [False, wx.NewIdRef(), 'bool'],
                'denssLimitDmaxStep'    : ['[500]', wx.NewIdRef(), 'text'],
                'denssRecenter'         : [True, wx.NewIdRef(), 'bool'],
                'denssRecenterStep'     : ['%s' %(list(range(1001, 8002, 500))), wx.NewIdRef(), 'text'],
                'denssPositivity'       : [True, wx.NewIdRef(), 'bool'],
                'denssExtrapolate'      : [True, wx.NewIdRef(), 'bool'],
                'denssShrinkwrap'       : [True, wx.NewIdRef(), 'bool'],
                'denssShrinkwrapSigmaStart' : [3., wx.NewIdRef(), 'float'],
                'denssShrinkwrapSigmaEnd'   : [1.5, wx.NewIdRef(), 'float'],
                'denssShrinkwrapSigmaDecay' : [0.99, wx.NewIdRef(), 'float'],
                'denssShrinkwrapThresFrac'  : [0.20, wx.NewIdRef(), 'float'],
                'denssShrinkwrapIter'   : [20, wx.NewIdRef(), 'int'],
                'denssShrinkwrapMinStep'    : [5000, wx.NewIdRef(), 'int'],
                'denssConnected'        : [True, wx.NewIdRef(), 'bool'],
                'denssConnectivitySteps'    : ['[7500]', wx.NewIdRef(), 'text'],
                'denssChiEndFrac'       : [0.001, wx.NewIdRef(), 'float'],
                'denssAverage'          : [True, wx.NewIdRef(), 'bool'],
                'denssReconstruct'      : [20, wx.NewIdRef(), 'int'],
                'denssCutOut'           : [False, wx.NewIdRef(), 'bool'],
                'denssWriteXplor'       : [True, wx.NewIdRef(), 'bool'],
                'denssMode'             : ['Slow', wx.NewIdRef(), 'choice'],
                'denssRecenterMode'     : ['com', wx.NewIdRef(), 'choice'],
                'denssMinDensity'       : ['None', wx.NewIdRef(), 'text'],
                'denssMaxDensity'       : ['None', wx.NewIdRef(), 'text'],
                'denssFlattenLowDensity': [False, wx.NewIdRef(), 'bool'],
                'denssNCS'              : [0, wx.NewIdRef(), 'int'],
                'denssNCSSteps'         : ['[3000,5000,7000,9000]', wx.NewIdRef(), 'text'],
                'denssNCSAxis'          : [1, wx.NewIdRef(), 'int'],
                'denssRefine'           : [True, wx.NewIdRef(), 'bool'],

                #File definitions
                'fileDefinitions'       : [file_defs, wx.NewIdRef(), 'dict'],
                }

        else:
            file_defs, _ = SASUtils.loadFileDefinitions()
            for ftype, fdefs in file_defs.items():
                for fname, defs in fdefs.items():
                    self._params['fileDefinitions'][0][ftype][fname] = defs

    def get(self, key):
        return self._params[key][0]

    def set(self, key, value):
        self._params[key][0] = value

    def getId(self, key):
        return self._params[key][1]

    def getType(self, key):
        return self._params[key][2]

    def getIdAndType(self, key):
        return (self._params[key][1], self._params[key][2])

    def getAllParams(self):
        return self._params

    def findParamById(self, param_id):
        for key in self._params:
            if len(self._params[key]) > 2:
                if self._params[key][1] == param_id:
                    return key

        return None

def fixBackwardsCompatibility(raw_settings, loaded_param):
    #Backwards compatibility for BindList:
    bind_list = raw_settings.get('HeaderBindList')
    for each_key in bind_list:
        if len(bind_list[each_key]) == 2:
            bind_list[each_key] = [bind_list[each_key][0], bind_list[each_key][1], '']

    masks = copy.copy(raw_settings.get('Masks'))

    for mask_type in masks:
        mask_list = masks[mask_type][1]
        if mask_list is not None:

            for i, mask in enumerate(mask_list):
                if isinstance(mask, SASMask.Mask):
                    mask._calcFillPoints()

                elif isinstance(mask, SASMask._oldMask):
                    if mask._type == 'rectangle':
                        mask = SASMask.RectangleMask(mask._points[0],
                            mask._points[1], mask._mask_id, mask._img_dimension,
                            mask._is_negative_mask)

                    elif mask._type == 'circle':
                        mask = SASMask.CircleMask(mask._points[0],
                            mask._points[1], mask._mask_id, mask._img_dimension,
                            mask._is_negative_mask)

                    if mask._type == 'polygon':
                        mask = SASMask.PolygonMask(mask._points,
                            mask._mask_id, mask._img_dimension,
                            mask._is_negative_mask)

                mask_list[i] = mask

            masks[mask_type][1] = mask_list

    raw_settings.set('Masks', masks)

    if 'DetectorPixelSize' in loaded_param:
        raw_settings.set('DetectorPixelSizeX', loaded_param['DetectorPixelSize'])
        raw_settings.set('DetectorPixelSizeY', loaded_param['DetectorPixelSize'])

    if 'HeaderbindList' in loaded_param and 'DetectorPixelSize' in loaded_param['HeaderBindList']:
        header_bind_list = raw_settings.get('HeaderBindList')
        header_bind_list['Detector X Pixel Size'] = loaded_param['HeaderBindList']['DetectorPixelSize']
        header_bind_list['Detector Y Pixel Size'] = loaded_param['HeaderBindList']['DetectorPixelSize']
        raw_settings.set('HeaderBindList', header_bind_list)


def loadSettings(raw_settings, filename, auto_load = False):

    loaded_param = readSettings(filename)

    if loaded_param is None:
        return False

    all_params = raw_settings.getAllParams()

    for each_key in loaded_param:
        if each_key in all_params:
            all_params[each_key][0] = copy.copy(loaded_param[each_key])

    default_settings = RawGuiSettings().getAllParams()

    for key in default_settings:
        if key not in loaded_param:
            all_params[key] = default_settings[key]

    postProcess(raw_settings, default_settings, loaded_param)

    msg = ''

    if 'RequiredVersion' in all_params:
        rv = raw_settings.get('RequiredVersion')

        rv_maj, rv_min, rv_pt = map(int, rv.split('.'))

        v_maj, v_min, v_pt = map(int, RAWGlobals.version.split('.'))

        dv_maj, dv_min, dv_pt = map(int, default_settings['RequiredVersion'][0].split('.'))

        update = False

        if rv_maj > v_maj:
            update = True
        else:
            if rv_min > v_min and rv_maj == v_maj:
                update = True
            else:
                if rv_pt > v_pt and rv_maj == v_maj and rv_min == v_min:
                    update = True

        if update:
            msg = ('Some settings in this configuration file require '
                'a newer version of RAW: version %s (you are using version %s). '
                'Please update RAW now. If you use these settings with an older '
                'version of RAW, certain functions, including radial averaging of images, '
                'may not work correctly. You can find the newest version of RAW at '
                'http://bioxtas-raw.rftm.io/' %(rv, RAWGlobals.version))

        update_settings = False
        if dv_maj > rv_maj:
            update_settings = True
        else:
            if dv_min > rv_min:
                update_settings = True
            else:
                if dv_pt > rv_pt:
                    update = True
        if update_settings:
            raw_settings.set('RequiredVersion', default_settings['RequiredVersion'][0])

    return True, msg

def postProcess(raw_settings, default_settings, loaded_param):
    fixBackwardsCompatibility(raw_settings, loaded_param)

    masks = copy.copy(raw_settings.get('Masks'))

    for mask_type in masks:
        mask_list = masks[mask_type][1]
        if mask_list is not None:
            img_dim = raw_settings.get('MaskDimension')

            for i, mask in enumerate(mask_list):
                if isinstance(mask, dict):
                    if mask['type'] == 'circle':
                        mask = SASMask.CircleMask(mask['center_point'],
                            mask['radius_point'], i, img_dim, mask['negative'])
                    elif mask['type'] == 'rectangle':
                        mask = SASMask.RectangleMask(mask['first_point'],
                            mask['second_point'], i, img_dim, mask['negative'])
                    elif mask['type'] == 'polygon':
                        mask = SASMask.PolygonMask(mask['vertices'], i, img_dim,
                            mask['negative'])
                mask_list[i] = mask

            masks[mask_type][1] = mask_list

    raw_settings.set('Masks', masks)

    if 'ocl' in raw_settings.get('IntegrationMethod') and not RAWGlobals.has_pyopencl:
        raw_settings.set('IntegrationMethod', default_settings['IntegrationMethod'][0])

    dir_check_list = [('AutoSaveOnImageFiles', 'ProcessedFilePath'), ('AutoSaveOnAvgFiles', 'AveragedFilePath'),
                    ('AutoSaveOnSub', 'SubtractedFilePath'), ('AutoSaveOnBift', 'BiftFilePath'),
                    ('AutoSaveOnGnom', 'GnomFilePath'), ('OnlineModeOnStartup', 'OnlineStartupDir'),
                    ]

    file_check_list = [('NormFlatfieldEnabled', 'NormFlatfieldFile'),
        ('DarkCorrEnabled', 'DarkCorrFilename'),]

    file_check_list_inverted = [('NormAbsCarbonIgnoreBkg', 'NormAbsCarbonSamEmptyFile'),]

    change_list = []

    message_dir = {'AutoSaveOnImageFiles'   : '- AutoSave processed image files',
                    'AutoSaveOnAvgFiles'    : '- AutoSave averaged files',
                    'AutoSaveOnSub'         : '- AutoSave subtracted files',
                    'AutoSaveOnBift'        : '- AutoSave BIFT files',
                    'AutoSaveOnGnom'        : '- AutoSave GNOM files',
                    'OnlineModeOnStartup'   : '- Start online mode when RAW starts',
                    'NormFlatfieldEnabled'  : '- Apply a flatfield correction',
                    'NormAbsCarbonIgnoreBkg': '- Full (background subtracted) absolute scale using glassy carbon',
                    }

    for item in dir_check_list:
        if raw_settings.get(item[0]):
            if not os.path.isdir(raw_settings.get(item[1])):
                raw_settings.set(item[0], False)
                change_list.append(item[0])

    for item in file_check_list:
        if raw_settings.get(item[0]):
            if not os.path.isfile(raw_settings.get(item[1])):
                raw_settings.set(item[0], False)
                change_list.append(item[0])

    for item in file_check_list_inverted:
        if not raw_settings.get(item[0]):
            if not os.path.isfile(raw_settings.get(item[1])):
                raw_settings.set(item[0], True)
                change_list.append(item[0])

    text = ''
    for item in change_list:
        text = text + message_dir[item] +'\n'

    if len(change_list) > 0:
        wx.CallAfter(wx.MessageBox, 'The following settings have been disabled because the appropriate directory/file could not be found:\n'+text+'\nIf you are using a config file from a different computer please go into Advanced Options to change the settings, or save you config file to avoid this message next time.', 'Load Settings Warning', style = wx.ICON_ERROR | wx.OK | wx.STAY_ON_TOP)

    if raw_settings.get('autoFindATSAS'):
        atsas_dir = SASUtils.findATSASDirectory()
        raw_settings.set('ATSASDir', atsas_dir)

    return

def saveSettings(raw_settings, savepath):
    main_frame = wx.FindWindowByName('MainFrame')
    RAWGlobals.save_in_progress = True
    wx.CallAfter(main_frame.setStatus, 'Saving settings', 0)

    param_dict = raw_settings.getAllParams()

    exclude_keys = ['ImageFormatList', 'ImageHdrFormatList', 'BackgroundSASM',
    'CurrentCfg', 'csvIncludeData', 'CompatibleFormats', 'DataSECM',
    'NormAbsCarbonSamEmptySASM', 'AzimuthalIntegrator', 'NormFlatfieldImage',
    'DarkCorrImage', 'fileDefinitions']

    save_dict = {}

    for each_key in param_dict:
        if each_key not in exclude_keys:
            save_dict[each_key] = param_dict[each_key][0]

    save_dict = copy.deepcopy(save_dict)

    #remove big mask arrays from the cfg file
    masks = save_dict['Masks']

    for key in masks:
        masks[key][0] = None
        if masks[key][1] is not None:
            masks[key][1] = [mask.getSaveFormat() for mask in masks[key][1]]

    success = writeSettings(savepath, save_dict)

    if not success:
        RAWGlobals.save_in_progress = False
        wx.CallAfter(main_frame.setStatus, '', 0)
        return False

    ## Make a backup of the config file in case of crash:
    backup_file = os.path.join(RAWGlobals.RAWWorkDir, 'backup.cfg')

    success = writeSettings(backup_file, save_dict)

    if not success:
        RAWGlobals.save_in_progress = False
        wx.CallAfter(main_frame.setStatus, '', 0)
        return False

    dummy_settings = RawGuiSettings()

    test_load = loadSettings(dummy_settings, savepath)

    if not test_load:
        os.remove(savepath)

    RAWGlobals.save_in_progress = False
    wx.CallAfter(main_frame.setStatus, '', 0)

    return test_load


def writeSettings(filename, settings):
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            settings_str = json.dumps(settings, indent = 4, sort_keys = True,
                cls = SASUtils.MyEncoder, ensure_ascii=False)

            f.write(settings_str)
        return True
    except Exception as e:
        print(e)
        return False

def readSettings(filename):

    try:
        with open(filename, 'r') as f:
            settings = f.read()
        settings = dict(json.loads(settings))
    except Exception as e:
        try:
            with open(filename, 'rb') as f:
                if six.PY3:
                    pickle_obj = SASUtils.SafeUnpickler(f, encoding='latin-1')
                else:
                    pickle_obj = pickle.Unpickler(f)
                    pickle_obj.find_global = SASUtils.find_global
                settings = pickle_obj.load()
        except Exception as e:
            print('Error type: %s, error: %s' %(type(e).__name__, e))
            return None

    return settings


# Table from http://physchem.kfunigraz.ac.at/sm/Services.htm
water_scattering_table = {0 : 0.01692,
                        1 : 0.01686,
                        2 : 0.01680,
                        3 : 0.01675,
                        4 : 0.01670,
                        5 : 0.01665,
                        6 : 0.01661,
                        7 : 0.01657,
                        8 : 0.01653,
                        9 : 0.01650,
                        10 : 0.01647,
                        11 : 0.01645,
                        12 : 0.01642,
                        13 : 0.01640,
                        14 : 0.01638,
                        15 : 0.01637,
                        16 : 0.01635,
                        17 : 0.01634,
                        18 : 0.01633,
                        19 : 0.01633,
                        20 : 0.01632,
                        21 : 0.01632,
                        22 : 0.01632,
                        23 : 0.01632,
                        24 : 0.01632,
                        25 : 0.01633,
                        26 : 0.01634,
                        27 : 0.01635,
                        28 : 0.01636,
                        29 : 0.01637,
                        30 : 0.01638,
                        31 : 0.01640,
                        32 : 0.01641,
                        33 : 0.01643,
                        34 : 0.01645,
                        35 : 0.01647,
                        36 : 0.01650,
                        37 : 0.01652,
                        38 : 0.01655,
                        39 : 0.01658,
                        40 : 0.01660,
                        41 : 0.01663,
                        42 : 0.01666,
                        43 : 0.01670,
                        44 : 0.01673,
                        45 : 0.01677,
                        46 : 0.01680,
                        47 : 0.01684,
                        48 : 0.01688,
                        49 : 0.01692,
                        50 : 0.01696,
                        51 : 0.01700,
                        52 : 0.01704,
                        53 : 0.01709,
                        54 : 0.01713,
                        55 : 0.01718,
                        56 : 0.01723,
                        57 : 0.01728,
                        58 : 0.01732,
                        59 : 0.01738,
                        60 : 0.01743,
                        61 : 0.01748,
                        62 : 0.01753,
                        63 : 0.01759,
                        64 : 0.01764,
                        65 : 0.01770,
                        66 : 0.01776,
                        67 : 0.01781,
                        68 : 0.01787,
                        69 : 0.01793,
                        70 : 0.01800,
                        71 : 0.01806,
                        72 : 0.01812,
                        73 : 0.01818,
                        74 : 0.01825,
                        75 : 0.01831,
                        76 : 0.01838,
                        77 : 0.01845,
                        78 : 0.01852,
                        79 : 0.01859,
                        80 : 0.01866,
                        81 : 0.01873,
                        82 : 0.01880,
                        83 : 0.01887,
                        84 : 0.01895,
                        85 : 0.01902,
                        86 : 0.01909,
                        87 : 0.01917,
                        88 : 0.01925,
                        89 : 0.01932,
                        90 : 0.01940,
                        91 : 0.01948,
                        92 : 0.01956,
                        93 : 0.01964,
                        94 : 0.01973,
                        95 : 0.01981,
                        96 : 0.01989,
                        97 : 0.01998,
                        98 : 0.02006,
                        99 : 0.02015,
                        100 : 0.02023}

"""Data follows for glassy carbon calibration. It is taken from the
"3600_DataFile_2016-05016.xlsx" file that can be downloaded from NIST
as material for the SRM 3600 - Absolute Intensity Calibration Standard
for Small-Angle X-ray Scattering:
https://nemo.nist.gov/srmors/view_detail.cfm?srm=3600
or
https://www.nist.gov/srm
"""
carbon_cal_q = np.array([0.00827568,
                0.00888450,
                0.00954735,
                0.01026900,
                0.01105780,
                0.01191830,
                0.01286110,
                0.01389340,
                0.01502510,
                0.01626850,
                0.01763650,
                0.01914320,
                0.02080510,
                0.02264220,
                0.02467500,
                0.02692890,
                0.02943170,
                0.03221560,
                0.03531810,
                0.03878270,
                0.04265880,
                0.04700390,
                0.05188580,
                0.05738140,
                0.06358290,
                0.07059620,
                0.07854840,
                0.08758630,
                0.09788540,
                0.10965500,
                0.11431200,
                0.11839500,
                0.12262400,
                0.12314200,
                0.12700400,
                0.13154000,
                0.13623900,
                0.13864300,
                0.14110500,
                0.14614500,
                0.15136500,
                0.15651300,
                0.15677100,
                0.16237100,
                0.16817000,
                0.17417700,
                0.17718100,
                0.18039800,
                0.18684100,
                0.19351500,
                0.20042700,
                0.20116500,
                0.20758600,
                0.21500000,
                0.22267900,
                0.22909500,
                0.23063300,
                0.23887100,
                0.24740200,
                ])

carbon_cal_i = np.array([34.933380,
                34.427156,
                34.042170,
                33.698553,
                33.352529,
                33.027533,
                32.665045,
                32.306665,
                31.970485,
                31.559099,
                31.183763,
                30.861805,
                30.514300,
                30.084982,
                29.690414,
                29.249965,
                28.889970,
                28.449341,
                28.065980,
                27.704965,
                27.331304,
                26.974065,
                26.676952,
                26.401158,
                26.177427,
                25.904683,
                25.528734,
                24.917743,
                23.946472,
                22.472101,
                21.777228,
                21.112938,
                20.401110,
                20.287060,
                19.685107,
                18.909809,
                18.089242,
                17.679572,
                17.264117,
                16.372848,
                15.458350,
                14.587700,
                14.563071,
                13.616671,
                12.668549,
                11.752287,
                11.311460,
                10.862157,
                9.961979,
                9.116906,
                8.325578,
                8.224897,
                7.541931,
                6.854391,
                6.216070,
                5.715911,
                5.582366,
                4.999113,
                4.463604,])

carbon_cal_err = np.array([0.398241,
                0.392470,
                0.388081,
                0.384164,
                0.380219,
                0.376514,
                0.372382,
                0.368296,
                0.364464,
                0.359774,
                0.355495,
                0.351825,
                0.347863,
                0.342969,
                0.338471,
                0.333450,
                0.329346,
                0.324322,
                0.319952,
                0.315837,
                0.311577,
                0.307504,
                0.304117,
                0.300973,
                0.298423,
                0.295313,
                0.291028,
                0.284062,
                0.272990,
                0.256182,
                0.248260,
                0.240687,
                0.232573,
                0.231272,
                0.224410,
                0.215572,
                0.206217,
                0.201547,
                0.196811,
                0.186650,
                0.176225,
                0.166300,
                0.166019,
                0.155230,
                0.144421,
                0.133976,
                0.128951,
                0.123829,
                0.113567,
                0.103933,
                0.094912,
                0.093764,
                0.085978,
                0.078140,
                0.070863,
                0.065161,
                0.063639,
                0.056990,
                0.050885,])

glassy_carbon_cal = [carbon_cal_q, carbon_cal_i, carbon_cal_err]
