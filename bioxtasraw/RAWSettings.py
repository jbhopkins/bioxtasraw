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
import copy
import os
import shutil

import wx
import numpy as np

import RAWGlobals
import SASFileIO
import SASM
import SASImage

class RawGuiSettings(object):
    '''
    This object contains all the settings nessecary for the GUI.

    '''
    def __init__(self, settings = None):
        '''
        Accepts a dictionary argument for the parameters. Uses default is no settings are given.
        '''

        self._params = settings

        if settings == None:
            self._params = {
                            'RequiredVersion'       : ['1.5.0', wx.NewId(), 'text'],
							'NormFlatfieldEnabled'	: [False,   wx.NewId(),  'bool'],

                            'NormAbsWater'      	: [False,   wx.NewId(),  'bool'],
                            'NormAbsWaterI0'    	: [0.01632, wx.NewId(),  'float'],
                            'NormAbsWaterTemp'  	: ['25',    wx.NewId(),  'choice'],
                            'NormAbsWaterConst' 	: [1.0,     wx.NewId(),  'float'],
                            'NormAbsWaterFile'      : [None, wx.NewId(), 'text'],
                            'NormAbsWaterEmptyFile' : [None, wx.NewId(), 'text'],
                            'NormFlatfieldFile'     : [None, wx.NewId(), 'text'],

                            'NormAbsCarbon'             : [False, wx.NewId(), 'bool'],
                            'NormAbsCarbonIgnoreBkg'    : [True, wx.NewId(), 'bool'],
                            'NormAbsCarbonFile'         : [None, wx.NewId(), 'text'],
                            'NormAbsCarbonEmptyFile'    : [None, wx.NewId(), 'text'],
                            'NormAbsCarbonSamEmptyFile' : [None, wx.NewId(), 'text'],
                            'NormAbsCarbonCalFile'      : [None, wx.NewId(), 'text'],
                            'NormAbsCarbonThick'        : [1.055, wx.NewId(), 'float'],
                            'NormAbsCarbonSamThick'     : [1.0, wx.NewId(), 'float'],
                            'NormAbsCarbonUpstreamCtr'  : [None, wx.NewId(), 'choice'],
                            'NormAbsCarbonDownstreamCtr': [None, wx.NewId(), 'choice'],
                            'NormAbsCarbonConst'        : [1.0, wx.NewId(), 'float'],
                            'NormAbsCarbonSamEmptySASM' : [None],

                            'CalibrateMan'      : [True, wx.NewId(),  'bool'],  # Calibrate manual (wavelength / distance)
                            'AutoBgSubtract'    : [False, wx.NewId(),  'bool'],

                            'AutoBIFT'          : [False, wx.NewId(), 'bool'],
                            'AutoAvg'           : [False, wx.NewId(), 'bool'],
                            'AutoAvgRemovePlots': [False, wx.NewId(), 'bool'],

                            'AutoAvgRegExp'     : ['', wx.NewId(), 'text'],
                            'AutoAvgNameRegExp' : ['', wx.NewId(), 'text'],
                            'AutoAvgNoOfFrames' : [1,  wx.NewId(),  'int'],
                            'AutoBgSubRegExp'   : ['', wx.NewId(), 'text'],

                            'UseHeaderForMask': [False, wx.NewId(), 'bool'],
                            'DetectorFlipped90':[False, wx.NewId(), 'bool'],
                            'DetectorFlipLR' : [True, wx.NewId(), 'bool'],
                            'DetectorFlipUD' : [False, wx.NewId(), 'bool'],

                            #CORRECTIONS
                            'DoSolidAngleCorrection' : [True, wx.NewId(), 'bool'],


                            #CENTER / BINNING
                            'Binsize'    : [1,     wx.NewId(), 'int'],
                            'Xcenter'    : [512.0, wx.NewId(), 'float'],
                            'Ycenter'    : [512.0, wx.NewId(), 'float'],
                            'StartPoint' : [0,     wx.NewId(), 'int'],
                            'EndPoint'   : [0,     wx.NewId(), 'int'],
                            'ImageDim'   : [[1024,1024]],

                            #MASKING
                            'BackgroundSASM'          : [None, wx.NewId(), 'text'],

                            'DataSECM'                : [None, wx.NewId(), 'text'],

                                                                                #mask, mask_patches
                            'Masks'                   : [{'BeamStopMask'     : [None, None],
                                                          'ReadOutNoiseMask' : [None, None],
                                                          'TransparentBSMask': [None, None],
                                                         }],

                            'MaskDimension'          : [1024,1024],

                            #Q-CALIBRATION
                            'WaveLength'          : [1.0,  wx.NewId(), 'float'],
                            'SampleDistance'      : [1000, wx.NewId(), 'float'],
                            'DetectorPixelSize'   : [70.5, wx.NewId(), 'float'],

							#SANS Parameters
							'SampleThickness'		: [0.1,  wx.NewId(), 'float'],
							'DarkCorrEnabled'		: [False,   wx.NewId(),  'bool'],
							'DarkCorrFilename'		: [None, wx.NewId(), 'text'],


                            #DEFAULT BIFT PARAMETERS
                            'maxDmax'     : [400.0,  wx.NewId(), 'float'],
                            'minDmax'     : [10.0,   wx.NewId(), 'float'],
                            'DmaxPoints'  : [10,     wx.NewId(), 'int'],
                            'maxAlpha'    : [1e10,   wx.NewId(), 'float'],
                            'minAlpha'    : [150.0,  wx.NewId(), 'float'],
                            'AlphaPoints' : [16,     wx.NewId(), 'int'],
                            'PrPoints'    : [50,     wx.NewId(), 'int'],

                            #DEFAULT pyGNOM PARAMETERS
                            'pygnomMaxAlpha'    : [60,   wx.NewId(), 'float'],
                            'pygnomMinAlpha'    : [0.01, wx.NewId(), 'float'],
                            'pygnomAlphaPoints' : [100,  wx.NewId(), 'int'],
                            'pygnomPrPoints'    : [50,   wx.NewId(), 'int'],
                            'pygnomFixInitZero' : [True, wx.NewId(), 'bool'],

                            'pyOSCILLweight'    : [3.0, wx.NewId(), 'float'],
                            'pyVALCENweight'    : [1.0, wx.NewId(), 'float'],
                            'pyPOSITVweight'    : [1.0, wx.NewId(), 'float'],
                            'pySYSDEVweight'    : [3.0, wx.NewId(), 'float'],
                            'pySTABILweight'    : [3.0, wx.NewId(), 'float'],
                            'pyDISCRPweight'    : [1.0, wx.NewId(), 'float'],

                            #DEFAULT IFT PARAMETERS:
                            'IFTAlgoList'        : [['BIFT', 'pyGNOM']],
                            'IFTAlgoChoice'      : [['BIFT']],

                            #ARTIFACT REMOVAL:
                            'ZingerRemovalRadAvg'    : [False, wx.NewId(), 'bool'],
                            'ZingerRemovalRadAvgStd' : [4.0,     wx.NewId(), 'float'],

                            'ZingerRemoval'     : [False, wx.NewId(), 'bool'],
                            'ZingerRemoveSTD'   : [4,     wx.NewId(), 'int'],
                            'ZingerRemoveWinLen': [10,    wx.NewId(), 'int'],
                            'ZingerRemoveIdx'   : [10,    wx.NewId(), 'int'],

                            'ZingerRemovalAvgStd'  : [8,     wx.NewId(), 'int'],
                            'ZingerRemovalAvg'     : [False, wx.NewId(), 'bool'],

                            #SAVE DIRECTORIES
                            'ProcessedFilePath'    : [None,  wx.NewId(), 'text'],
                            'AveragedFilePath'     : [None,  wx.NewId(), 'text'],
                            'SubtractedFilePath'   : [None,  wx.NewId(), 'text'],
                            'BiftFilePath'         : [None,  wx.NewId(), 'text'],
                            'GnomFilePath'         : [None,  wx.NewId(), 'text'],
                            'AutoSaveOnImageFiles' : [False, wx.NewId(), 'bool'],
                            'AutoSaveOnAvgFiles'   : [False, wx.NewId(), 'bool'],
                            'AutoSaveOnSub'        : [False, wx.NewId(), 'bool'],
                            'AutoSaveOnBift'       : [False, wx.NewId(), 'bool'],
                            'AutoSaveOnGnom'       : [False, wx.NewId(), 'bool'],

                            #IMAGE FORMATS
                            'ImageFormatList'      : [SASFileIO.all_image_types],
                            'ImageFormat'          : ['Pilatus', wx.NewId(), 'choice'],

                            #HEADER FORMATS
                            'ImageHdrFormatList'   : [SASFileIO.all_header_types],
                            'ImageHdrFormat'       : ['None', wx.NewId(), 'choice'],

                            'ImageHdrList'         : [None],
                            'FileHdrList'          : [None],

                            'UseHeaderForCalib'    : [False, wx.NewId(), 'bool'],

                            # Header bind list with [(Description : parameter key, header_key)]
                            'HeaderBindList'       : [{'Beam X Center'            : ['Xcenter',           None, ''],
                                                       'Beam Y Center'            : ['Ycenter',           None, ''],
                                                       'Sample Detector Distance' : ['SampleDistance',    None, ''],
                                                       'Wavelength'               : ['WaveLength',        None, ''],
                                                       'Detector Pixel Size'      : ['DetectorPixelSize', None, '']}],
                                                       # 'Number of Frames'         : ['NumberOfFrames',    None, '']}],

                            'NormalizationList'    : [None, wx.NewId(), 'text'],
                            'EnableNormalization'  : [True, wx.NewId(), 'bool'],

                            'OnlineFilterList'     : [None, wx.NewId(), 'text'],
                            'EnableOnlineFiltering': [False, wx.NewId(), 'bool'],
                            'OnlineModeOnStartup'  : [False, wx.NewId(), 'bool'],
	                        'OnlineStartupDir'     : [None, wx.NewId(), 'text'],

                            'MWStandardMW'         : [0, wx.NewId(), 'float'],
                            'MWStandardI0'         : [0, wx.NewId(), 'float'],
                            'MWStandardConc'       : [0, wx.NewId(), 'float'],
                            'MWStandardFile'       : ['', wx.NewId(), 'text'],

                            #Initialize volume of correlation molecular mass values.
                            #Values from Rambo, R. P. & Tainer, J. A. (2013). Nature. 496, 477-481.
                            'MWVcType'             : ['Protein', wx.NewId(), 'choice'],
                            'MWVcAProtein'         : [1.0, wx.NewId(), 'float'], #The 'A' coefficient for proteins
                            'MWVcBProtein'         : [0.1231, wx.NewId(), 'float'], #The 'B' coefficient for proteins
                            'MWVcARna'             : [0.808, wx.NewId(), 'float'], #The 'A' coefficient for proteins
                            'MWVcBRna'             : [0.00934, wx.NewId(), 'float'], #The 'B' coefficient for proteins

                            #Initialize porod volume molecularm ass values.
                            'MWVpRho'              : [0.83*10**(-3), wx.NewId(), 'float'], #The density in kDa/A^3

                            #Initialize Absolute scattering calibration values.
                            #Default values from Mylonas & Svergun, J. App. Crys. 2007.
                            'MWAbsRhoMprot'         : [3.22*10**23, wx.NewId(), 'float'], #e-/g, # electrons per dry mass of protein
                            'MWAbsRhoSolv'          : [3.34*10**23, wx.NewId(), 'float'], #e-/cm^-3, # electrons per volume of aqueous solvent
                            'MWAbsNuBar'            : [0.7425, wx.NewId(), 'float'], #cm^3/g, # partial specific volume of the protein
                            'MWAbsR0'               : [2.8179*10**-13, wx.NewId(), 'float'], #cm, scattering lenght of an electron

                            'CurrentCfg'         : [None],
                            'CompatibleFormats'  : [['.rad', '.tiff', '.tif', '.img', '.csv', '.dat', '.txt', '.sfrm', '.dm3', '.edf',
                                                     '.xml', '.cbf', '.kccd', '.msk', '.spr', '.h5', '.mccd', '.mar3450', '.npy', '.pnm',
                                                      '.No', '.imx_0', '.dkx_0', '.dkx_1', '.png', '.mpa', '.ift', '.sub', '.fit', '.fir',
                                                      '.out', '.mar1200', '.mar2400', '.mar2300', '.mar3600', '.int', '.ccdraw'], None],


                            #Series Settings:
                            'secCalcThreshold'      : [1.02, wx.NewId(), 'float'],
                            'IBaselineMinIter'    : [100, wx.NewId(), 'int'],
                            'IBaselineMaxIter'    : [2000, wx.NewId(), 'int'],

                            #GUI Settings:
                            'csvIncludeData'      : [None],
                            'ManipItemCollapsed'  : [False, wx.NewId(), 'bool'] ,

                            'DatHeaderOnTop'      : [False, wx.NewId(), 'bool'],
                            'PromptConfigLoad'    : [True, wx.NewId(), 'bool'],

                            #ATSAS settings:
                            'autoFindATSAS'       : [True, wx.NewId(), 'bool'],
                            'ATSASDir'            : ['', wx.NewId(), 'bool'],

                            #GNOM settings
                            'gnomExpertFile'        : ['', wx.NewId(), 'text'],
                            'gnomForceRminZero'     : ['Y', wx.NewId(), 'choice'],
                            'gnomForceRmaxZero'     : ['Y', wx.NewId(), 'choice'],
                            'gnomNPoints'           : [0, wx.NewId(), 'int'],
                            'gnomInitialAlpha'      : [0.0, wx.NewId(), 'float'],
                            'gnomAngularScale'      : [1, wx.NewId(), 'int'],
                            'gnomSystem'            : [0, wx.NewId(), 'int'],
                            'gnomFormFactor'        : ['', wx.NewId(), 'text'],
                            'gnomRadius56'          : [-1, wx.NewId(), 'float'],
                            'gnomRmin'              : [-1, wx.NewId(), 'float'],
                            'gnomFWHM'              : [-1, wx.NewId(), 'float'],
                            'gnomAH'                : [-1, wx.NewId(), 'float'],
                            'gnomLH'                : [-1, wx.NewId(), 'float'],
                            'gnomAW'                : [-1, wx.NewId(), 'float'],
                            'gnomLW'                : [-1, wx.NewId(), 'float'],
                            'gnomSpot'              : ['', wx.NewId(), 'text'],
                            'gnomExpt'              : [0, wx.NewId(), 'int'],

                            #DAMMIF settings
                            'dammifMode'            : ['Slow', wx.NewId(), 'choice'],
                            'dammifSymmetry'        : ['P1', wx.NewId(), 'choice'],
                            'dammifAnisometry'      : ['Unknown', wx.NewId(), 'choice'],
                            'dammifUnit'            : ['Unknown', wx.NewId(), 'choice'],
                            'dammifChained'         : [False, wx.NewId(), 'bool'],
                            'dammifConstant'        : ['', wx.NewId(), 'text'],
                            'dammifOmitSolvent'     : [True, wx.NewId(), 'bool'],
                            'dammifDummyRadius'     : [-1, wx.NewId(), 'float'],
                            'dammifSH'              : [-1, wx.NewId(), 'int'],
                            'dammifPropToFit'       : [-1, wx.NewId(), 'float'],
                            'dammifKnots'           : [-1, wx.NewId(), 'int'],
                            'dammifCurveWeight'     : ['e', wx.NewId(), 'choice'],
                            'dammifRandomSeed'      : ['', wx.NewId(), 'text'],
                            'dammifMaxSteps'        : [-1, wx.NewId(), 'int'],
                            'dammifMaxIters'        : [-1, wx.NewId(), 'int'],
                            'dammifMaxStepSuccess'  : [-1, wx.NewId(), 'int'],
                            'dammifMinStepSuccess'  : [-1, wx.NewId(), 'int'],
                            'dammifTFactor'         : [-1, wx.NewId(), 'float'],
                            'dammifRgPen'           : [-1, wx.NewId(), 'float'],
                            'dammifCenPen'          : [-1, wx.NewId(), 'float'],
                            'dammifLoosePen'        : [-1, wx.NewId(), 'float'],
                            'dammifAnisPen'         : [-1, wx.NewId(), 'float'],
                            'dammifMaxBeadCount'    : [-1, wx.NewId(), 'int'],
                            'dammifReconstruct'     : [15, wx.NewId(), 'int'],
                            'dammifDamaver'         : [True, wx.NewId(), 'bool'],
                            'dammifDamclust'        : [False, wx.NewId(), 'bool'],
                            'dammifRefine'          : [True, wx.NewId(), 'bool'],
                            'dammifProgram'         : ['DAMMIF', wx.NewId(), 'choice'],
                            'dammifExpectedShape'   : ['u', wx.NewId(), 'choice'],

                            #DAMMIN settings that are not included in DAMMIF settings
                            'damminInitial'         : ['S', wx.NewId(), 'choice'], #Initial DAM
                            'damminKnots'           : [20, wx.NewId(), 'int'],
                            'damminConstant'        : [0, wx.NewId(), 'float'],
                            'damminDiameter'        : [-1, wx.NewId(), 'float'],
                            'damminPacking'         : [-1, wx.NewId(), 'float'],
                            'damminCoordination'    : [-1, wx.NewId(), 'float'],
                            'damminDisconPen'       : [-1, wx.NewId(), 'float'],
                            'damminPeriphPen'       : [-1, wx.NewId(), 'float'],
                            'damminCurveWeight'     : ['1', wx.NewId(), 'choice'],
                            'damminAnealSched'      : [-1, wx.NewId(), 'float'],

                            #Weighted Average Settings
                            'weightCounter'         : ['', wx.NewId(), 'choice'],
                            'weightByError'         : [True, wx.NewId(), 'bool'],

                            #Similarity testing settings
                            'similarityTest'        : ['CorMap', wx.NewId(), 'choice'],
                            'similarityCorrection'  : ['Bonferroni', wx.NewId(), 'choice'],
                            'similarityThreshold'   : [0.01, wx.NewId(), 'float'],
                            'similarityOnAverage'   : [True, wx.NewId(), 'bool'],

                            #Fitting settings
                            'errorWeight'           : [True, wx.NewId(), 'bool'],
                            'normalizedResiduals'   : [True, wx.NewId(), 'bool'],

                            #Denss settings
                            'denssVoxel'            : [5, wx.NewId(), 'float'],
                            'denssOversampling'     : [3, wx.NewId(), 'float'],
                            'denssNElectrons'       : ['', wx.NewId(), 'text'],
                            'denssSteps'            : [10000, wx.NewId(), 'int'],
                            'denssLimitDmax'        : [False, wx.NewId(), 'bool'],
                            'denssLimitDmaxStep'    : ['[500]', wx.NewId(), 'text'],
                            'denssRecenter'         : [True, wx.NewId(), 'bool'],
                            'denssRecenterStep'     : ['%s' %(range(1001, 8002, 500)), wx.NewId(), 'text'],
                            'denssPositivity'       : [True, wx.NewId(), 'bool'],
                            'denssExtrapolate'      : [True, wx.NewId(), 'bool'],
                            'denssShrinkwrap'       : [True, wx.NewId(), 'bool'],
                            'denssShrinkwrapSigmaStart' : [3, wx.NewId(), 'float'],
                            'denssShrinkwrapSigmaEnd'   : [1.5, wx.NewId(), 'float'],
                            'denssShrinkwrapSigmaDecay' : [0.99, wx.NewId(), 'float'],
                            'denssShrinkwrapThresFrac'  : [0.20, wx.NewId(), 'float'],
                            'denssShrinkwrapIter'   : [20, wx.NewId(), 'int'],
                            'denssShrinkwrapMinStep'    : [5000, wx.NewId(), 'int'],
                            'denssConnected'        : [True, wx.NewId(), 'bool'],
                            'denssConnectivitySteps'    : ['[7500]', wx.NewId(), 'text'],
                            'denssChiEndFrac'       : [0.001, wx.NewId(), 'float'],
                            'denssPlotOutput'       : [True, wx.NewId(), 'bool'],
                            'denssAverage'          : [True, wx.NewId(), 'bool'],
                            'denssReconstruct'      : [20, wx.NewId(), 'int'],
                            'denssCutOut'           : [False, wx.NewId(), 'bool'],
                            'denssWriteXplor'       : [True, wx.NewId(), 'bool'],
                            'denssMode'             : ['Slow', wx.NewId(), 'choice'],
                            'denssRecenterMode'     : ['com', wx.NewId(), 'choice'],
                            'denssMinDensity'       : ['None', wx.NewId(), 'text'],
                            'denssMaxDensity'       : ['None', wx.NewId(), 'text'],

                            }

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



def fixBackwardsCompatibility(raw_settings):

    #Backwards compatibility for BindList:
    bind_list = raw_settings.get('HeaderBindList')
    for each_key in bind_list.keys():
        if len(bind_list[each_key]) == 2:
            bind_list[each_key] = [bind_list[each_key][0], bind_list[each_key][1], '']


def loadSettings(raw_settings, loadpath):

    loaded_param = SASFileIO.readSettings(loadpath)

    if loaded_param is None:
        return False

    keys = loaded_param.keys()
    all_params = raw_settings.getAllParams()

    for each_key in keys:
        if each_key in all_params:
            all_params[each_key][0] = copy.copy(loaded_param[each_key])
        else:
            print 'WARNING: ' + str(each_key) + " not found in RAWSettings."

    default_settings = RawGuiSettings().getAllParams()

    for key in default_settings.keys():
        if key not in loaded_param:
            all_params[key] = default_settings[key]

    postProcess(raw_settings)

    main_frame = wx.FindWindowByName('MainFrame')
    main_frame.queueTaskInWorkerThread('recreate_all_masks', None)

    backup_file = os.path.join(RAWGlobals.RAWWorkDir, 'backup.cfg')

    if backup_file != loadpath:
        shutil.copyfile(loadpath, backup_file)

    if 'RequiredVersion' in all_params:
        rv = raw_settings.get('RequiredVersion')

        rv_maj, rv_min, rv_pt = map(int, rv.split('.'))

        v_maj, v_min, v_pt = map(int, RAWGlobals.version.split('.'))

        update = False

        if rv_maj > v_maj:
            update = True
        else:
            if rv_min > v_min:
                update = True
            else:
                if rv_pt > v_pt:
                    update = True

        if update:
            msg = ('Some settings in this configuration file require '
                'a newer version of RAW: version %s (you are using version %s). '
                'Please update RAW now. If you use these settings with an older '
                'version of RAW, certain functions, including radial averaging of images, '
                'may not work correctly. You can find the newest version of RAW at '
                'http://bioxtas-raw.rftm.io/' %(rv, RAWGlobals.version))

            wx.CallAfter(wx.MessageBox, msg, 'Warning: incompatible version of RAW',
                style = wx.ICON_ERROR | wx.OK)

    return True

def postProcess(raw_settings):
    fixBackwardsCompatibility(raw_settings)

    masks = copy.copy(raw_settings.get('Masks'))

    for mask_type in masks.keys():
        mask_list = masks[mask_type][1]
        if mask_list is not None:
            img_dim = raw_settings.get('MaskDimension')

            for i, mask in enumerate(mask_list):
                if isinstance(mask, dict):
                    if mask['type'] == 'circle':
                        mask = SASImage.CircleMask(mask['center_point'],
                            mask['radius_point'], i, img_dim, mask['negative'])
                    elif mask['type'] == 'rectangle':
                        mask = SASImage.RectangleMask(mask['first_point'],
                            mask['second_point'], i, img_dim, mask['negative'])
                    elif mask['type'] == 'polygon':
                        mask = SASImage.PolygonMask(mask['vertices'], i, img_dim,
                            mask['negative'])
                mask_list[i] = mask

            masks[mask_type][1] = mask_list

    raw_settings.set('Masks', masks)

    dir_check_list = [('AutoSaveOnImageFiles', 'ProcessedFilePath'), ('AutoSaveOnAvgFiles', 'AveragedFilePath'),
                    ('AutoSaveOnSub', 'SubtractedFilePath'), ('AutoSaveOnBift', 'BiftFilePath'),
                    ('AutoSaveOnGnom', 'GnomFilePath'), ('OnlineModeOnStartup', 'OnlineStartupDir'),
                    ]

    file_check_list = [('NormFlatfieldEnabled', 'NormFlatfieldFile'),]

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
        main_frame = wx.FindWindowByName('MainFrame')
        main_frame.findAtsas()

    return

def saveSettings(raw_settings, savepath):
    main_frame = wx.FindWindowByName('MainFrame')
    RAWGlobals.save_in_progress = True
    wx.CallAfter(main_frame.setStatus, 'Saving settings', 0)

    param_dict = raw_settings.getAllParams()
    keys = param_dict.keys()

    exclude_keys = ['ImageFormatList', 'ImageHdrFormatList', 'BackgroundSASM', 'CurrentCfg', 'csvIncludeData', 'CompatibleFormats', 'DataSECM', 'NormAbsCarbonSamEmptySASM']

    save_dict = {}

    for each_key in keys:
        if each_key not in exclude_keys:
            save_dict[each_key] = param_dict[each_key][0]

    save_dict = copy.deepcopy(save_dict)

    #remove big mask arrays from the cfg file
    masks = save_dict['Masks']

    for key in masks.keys():
        masks[key][0] = None
        if masks[key][1] is not None:
            masks[key][1] = [mask.getSaveFormat() for mask in masks[key][1]]

    success = SASFileIO.writeSettings(savepath, save_dict)

    if not success:
        RAWGlobals.save_in_progress = False
        wx.CallAfter(main_frame.setStatus, '', 0)
        return False

    ## Make a backup of the config file in case of crash:
    backup_file = os.path.join(RAWGlobals.RAWWorkDir, 'backup.cfg')

    success = SASFileIO.writeSettings(backup_file, save_dict)

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
