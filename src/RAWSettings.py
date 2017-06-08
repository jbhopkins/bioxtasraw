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
import wx, cPickle, copy, os
import RAWGlobals, SASFileIO

class RawGuiSettings:
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
                            #'NormalizeConst'    : [1.0,   wx.Window.NewControlId(), 'float'],
                            #'NormalizeConstChk' : [False, wx.Window.NewControlId(),  'bool'],
                            #'NormalizeM2'       : [False, wx.Window.NewControlId(),  'bool'],
                            #'NormalizeTime'     : [False, wx.Window.NewControlId(),  'bool'],
                            #'NormalizeM1'       : [False, wx.Window.NewControlId(),  'bool'],

							'NormFlatfieldEnabled'	: [False,   wx.Window.NewControlId(),  'bool'],

                            'NormAbsWater'      	: [False,   wx.Window.NewControlId(),  'bool'],
                            'NormAbsWaterI0'    	: [0.01632, wx.Window.NewControlId(),  'float'],
                            'NormAbsWaterTemp'  	: ['25',    wx.Window.NewControlId(),  'choice'],
                            'NormAbsWaterConst' 	: [1.0,     wx.Window.NewControlId(),  'float'],

                            'NormalizeTrans'    : [False, wx.Window.NewControlId(),  'bool'],
                            'Calibrate'         : [False, wx.Window.NewControlId(),  'bool'],  # Calibrate AgBe
                            'CalibrateMan'      : [True, wx.Window.NewControlId(),  'bool'],  # Calibrate manual (wavelength / distance)
                            'AutoBgSubtract'    : [False, wx.Window.NewControlId(),  'bool'],
                            'CountNormalize'    : [1.0,   wx.Window.NewControlId(), 'float'],

                            'AutoBIFT'          : [False, wx.Window.NewControlId(), 'bool'],
                            'AutoAvg'           : [False, wx.Window.NewControlId(), 'bool'],
                            'AutoAvgRemovePlots': [False, wx.Window.NewControlId(), 'bool'],

                            'AutoAvgRegExp'     : ['', wx.Window.NewControlId(), 'text'],
                            'AutoAvgNameRegExp' : ['', wx.Window.NewControlId(), 'text'],
                            'AutoAvgNoOfFrames' : [1,  wx.Window.NewControlId(),  'int'],
                            'AutoBgSubRegExp'   : ['', wx.Window.NewControlId(), 'text'],

                            'UseHeaderForMask': [False, wx.Window.NewControlId(), 'bool'],
                            'DetectorFlipped90':[False, wx.Window.NewControlId(), 'bool'],

                            #CORRECTIONS
                            'DoSolidAngleCorrection' : [True, wx.Window.NewControlId(), 'bool'],


                            #CENTER / BINNING
                            'Binsize'    : [1,     wx.Window.NewControlId(), 'int'],
                            'Xcenter'    : [512.0, wx.Window.NewControlId(), 'float'],
                            'Ycenter'    : [512.0, wx.Window.NewControlId(), 'float'],
                            'QrangeLow'  : [25,    wx.Window.NewControlId(), 'int'],
                            'QrangeHigh' : [9999,  wx.Window.NewControlId(), 'int'],
                            'StartPoint' : [0,     wx.Window.NewControlId(), 'int'],
                            'EndPoint'   : [0,     wx.Window.NewControlId(), 'int'],
                            'ImageDim'   : [[1024,1024]],

                            #MASKING
                            'SampleFile'              : [None, wx.Window.NewControlId(), 'text'],
                            'BackgroundSASM'          : [None, wx.Window.NewControlId(), 'text'],

                            'DataSECM'                : [None, wx.Window.NewControlId(), 'text'],

                            'NormAbsWaterFile'        : [None, wx.Window.NewControlId(), 'text'],
                            'NormAbsWaterEmptyFile'   : [None, wx.Window.NewControlId(), 'text'],
							'NormFlatfieldFile'		  : [None, wx.Window.NewControlId(), 'text'],

                            'TransparentBSMask'       : [None],
                            'TransparentBSMaskParams' : [None],
                            'BeamStopMask'            : [None],
                            'BeamStopMaskParams'      : [None],
                            'ReadOutNoiseMask'        : [None],
                            'ReadOutNoiseMaskParams'  : [None],
                                                                                #mask, mask_patches
                            'Masks'                   : [{'BeamStopMask'     : [None, None],
                                                          'ReadOutNoiseMask' : [None, None],
                                                          'TransparentBSMask': [None, None],
                                                         }],

                            'MaskDimension'          : [1024,1024],

                            #Q-CALIBRATION
                            'WaveLength'          : [1.0,  wx.Window.NewControlId(), 'float'],
                            'SampleDistance'      : [1000, wx.Window.NewControlId(), 'float'],
                            'ReferenceQ'          : [0.0, wx.Window.NewControlId(), 'float'],
                            'ReferenceDistPixel'  : [0,   wx.Window.NewControlId(), 'int'],
                            'ReferenceDistMm'     : [0.0, wx.Window.NewControlId(), 'float'],
                            'DetectorPixelSize'   : [70.5, wx.Window.NewControlId(), 'float'],
                            'SmpDetectOffsetDist' : [0.0, wx.Window.NewControlId(), 'float'],


							#SANS Parameters
							'SampleThickness'		: [0.1,  wx.Window.NewControlId(), 'float'],
							'DarkCorrEnabled'		: [False,   wx.Window.NewControlId(),  'bool'],
							'DarkCorrFilename'		: [None, wx.Window.NewControlId(), 'text'],


                            #DEFAULT BIFT PARAMETERS
                            'maxDmax'     : [400.0,  wx.Window.NewControlId(), 'float'],
                            'minDmax'     : [10.0,   wx.Window.NewControlId(), 'float'],
                            'DmaxPoints'  : [10,     wx.Window.NewControlId(), 'int'],
                            'maxAlpha'    : [1e10,   wx.Window.NewControlId(), 'float'],
                            'minAlpha'    : [150.0,  wx.Window.NewControlId(), 'float'],
                            'AlphaPoints' : [16,     wx.Window.NewControlId(), 'int'],
                            'PrPoints'    : [50,     wx.Window.NewControlId(), 'int'],

                            #DEFAULT pyGNOM PARAMETERS
                            'pygnomMaxAlpha'    : [60,   wx.Window.NewControlId(), 'float'],
                            'pygnomMinAlpha'    : [0.01, wx.Window.NewControlId(), 'float'],
                            'pygnomAlphaPoints' : [100,  wx.Window.NewControlId(), 'int'],
                            'pygnomPrPoints'    : [50,   wx.Window.NewControlId(), 'int'],
                            'pygnomFixInitZero' : [True, wx.Window.NewControlId(), 'bool'],

                            'pyOSCILLweight'    : [3.0, wx.Window.NewControlId(), 'float'],
                            'pyVALCENweight'    : [1.0, wx.Window.NewControlId(), 'float'],
                            'pyPOSITVweight'    : [1.0, wx.Window.NewControlId(), 'float'],
                            'pySYSDEVweight'    : [3.0, wx.Window.NewControlId(), 'float'],
                            'pySTABILweight'    : [3.0, wx.Window.NewControlId(), 'float'],
                            'pyDISCRPweight'    : [1.0, wx.Window.NewControlId(), 'float'],

                            #DEFAULT IFT PARAMETERS:
                            'IFTAlgoList'        : [['BIFT', 'pyGNOM']],
                            'IFTAlgoChoice'      : [['BIFT']],

                            #ARTIFACT REMOVAL:
                            'ZingerRemovalRadAvg'    : [False, wx.Window.NewControlId(), 'bool'],
                            'ZingerRemovalRadAvgStd' : [4.0,     wx.Window.NewControlId(), 'float'],

                            'ZingerRemoval'     : [False, wx.Window.NewControlId(), 'bool'],
                            'ZingerRemoveSTD'   : [4,     wx.Window.NewControlId(), 'int'],
                            'ZingerRemoveWinLen': [10,    wx.Window.NewControlId(), 'int'],
                            'ZingerRemoveIdx'   : [10,    wx.Window.NewControlId(), 'int'],

                            'ZingerRemovalAvgStd'  : [8,     wx.Window.NewControlId(), 'int'],
                            'ZingerRemovalAvg'     : [False, wx.Window.NewControlId(), 'bool'],

                            #SAVE DIRECTORIES
                            'ProcessedFilePath'    : [None,  wx.Window.NewControlId(), 'text'],
                            'AveragedFilePath'     : [None,  wx.Window.NewControlId(), 'text'],
                            'SubtractedFilePath'   : [None,  wx.Window.NewControlId(), 'text'],
                            'BiftFilePath'         : [None,  wx.Window.NewControlId(), 'text'],
                            'GnomFilePath'         : [None,  wx.Window.NewControlId(), 'text'],
                            'AutoSaveOnImageFiles' : [False, wx.Window.NewControlId(), 'bool'],
                            'AutoSaveOnAvgFiles'   : [False, wx.Window.NewControlId(), 'bool'],
                            'AutoSaveOnSub'        : [False, wx.Window.NewControlId(), 'bool'],
                            'AutoSaveOnBift'       : [False, wx.Window.NewControlId(), 'bool'],
                            'AutoSaveOnGnom'       : [False, wx.Window.NewControlId(), 'bool'],

                            #IMAGE FORMATS
                            'ImageFormatList'      : [SASFileIO.all_image_types],
                            'ImageFormat'          : ['Pilatus', wx.Window.NewControlId(), 'choice'],

                            #HEADER FORMATS
                            'ImageHdrFormatList'   : [SASFileIO.all_header_types],
                            'ImageHdrFormat'       : ['None', wx.Window.NewControlId(), 'choice'],

                            'ImageHdrList'         : [None],
                            'FileHdrList'          : [None],

                            'UseHeaderForCalib'    : [False, wx.Window.NewControlId(), 'bool'],

                            # Header bind list with [(Description : parameter key, header_key)]
                            'HeaderBindList'       : [{'Beam X Center'            : ['Xcenter',           None, ''],
                                                       'Beam Y Center'            : ['Ycenter',           None, ''],
                                                       'Sample Detector Distance' : ['SampleDistance',    None, ''],
                                                       'Wavelength'               : ['WaveLength',        None, ''],
                                                       'Detector Pixel Size'      : ['DetectorPixelSize', None, '']}],
                                                       # 'Number of Frames'         : ['NumberOfFrames',    None, '']}],

                            'NormalizationList'    : [None, wx.Window.NewControlId(), 'text'],
                            'EnableNormalization'  : [True, wx.Window.NewControlId(), 'bool'],

                            'OnlineFilterList'     : [None, wx.Window.NewControlId(), 'text'],
                            'EnableOnlineFiltering': [False, wx.Window.NewControlId(), 'bool'],
                            'OnlineModeOnStartup'  : [False, wx.Window.NewControlId(), 'bool'],
	                        'OnlineStartupDir'     : [None, wx.Window.NewControlId(), 'text'],

                            'MWStandardMW'         : [0, wx.Window.NewControlId(), 'float'],
                            'MWStandardI0'         : [0, wx.Window.NewControlId(), 'float'],
                            'MWStandardConc'       : [0, wx.Window.NewControlId(), 'float'],
                            'MWStandardFile'       : ['', wx.Window.NewControlId(), 'text'],

                            #Initialize volume of correlation molecular mass values.
                            #Values from Rambo, R. P. & Tainer, J. A. (2013). Nature. 496, 477-481.
                            'MWVcType'             : ['Protein', wx.Window.NewControlId(), 'choice'],
                            'MWVcAProtein'         : [1.0, wx.Window.NewControlId(), 'float'], #The 'A' coefficient for proteins
                            'MWVcBProtein'         : [0.1231, wx.Window.NewControlId(), 'float'], #The 'B' coefficient for proteins
                            'MWVcARna'             : [0.808, wx.Window.NewControlId(), 'float'], #The 'A' coefficient for proteins
                            'MWVcBRna'             : [0.00934, wx.Window.NewControlId(), 'float'], #The 'B' coefficient for proteins

                            #Initialize porod volume molecularm ass values.
                            'MWVpRho'              : [0.83*10**(-3), wx.Window.NewControlId(), 'float'], #The density in kDa/A^3

                            #Initialize Absolute scattering calibration values.
                            #Default values from Mylonas & Svergun, J. App. Crys. 2007.
                            'MWAbsRhoMprot'         : [3.22*10**23, wx.Window.NewControlId(), 'float'], #e-/g, # electrons per dry mass of protein
                            'MWAbsRhoSolv'          : [3.34*10**23, wx.Window.NewControlId(), 'float'], #e-/cm^-3, # electrons per volume of aqueous solvent
                            'MWAbsNuBar'            : [0.7425, wx.Window.NewControlId(), 'float'], #cm^3/g, # partial specific volume of the protein
                            'MWAbsR0'               : [2.8179*10**-13, wx.Window.NewControlId(), 'float'], #cm, scattering lenght of an electron

                            'CurrentCfg'         : [None],
                            'CompatibleFormats'  : [['.rad', '.tiff', '.tif', '.img', '.csv', '.dat', '.txt', '.sfrm', '.dm3', '.edf',
                                                     '.xml', '.cbf', '.kccd', '.msk', '.spr', '.h5', '.mccd', '.mar3450', '.npy', '.pnm',
                                                      '.No', '.imx_0', '.dkx_0', '.dkx_1', '.png', '.mpa', '.ift', '.sub', '.fit', '.fir',
                                                      '.out', '.mar1200', '.mar2400', '.mar2300', '.mar3600', '.int', '.ccdraw'], None],


                            #SEC Settings:
                            'secCalcThreshold'      : [1.02, wx.Window.NewControlId(), 'float'],

                            #GUI Settings:
                            'csvIncludeData'      : [None],
                            'ManipItemCollapsed'  : [False, wx.Window.NewControlId(), 'bool'] ,
                            'CurrentFilePath'     : [None],


                            'DatHeaderOnTop'      : [False, wx.Window.NewControlId(), 'bool'],
                            'PromptConfigLoad'    : [True, wx.Window.NewControlId(), 'bool'],

                            #ATSAS settings:
                            'autoFindATSAS'       : [True, wx.Window.NewControlId(), 'bool'],
                            'ATSASDir'            : ['', wx.Window.NewControlId(), 'bool'],

                            #GNOM settings
                            'gnomExpertFile'        : ['', wx.Window.NewControlId(), 'text'],
                            'gnomForceRminZero'     : ['Y', wx.Window.NewControlId(), 'choice'],
                            'gnomForceRmaxZero'     : ['Y', wx.Window.NewControlId(), 'choice'],
                            'gnomNPoints'           : [171, wx.Window.NewControlId(), 'int'],
                            'gnomInitialAlpha'      : [0.0, wx.Window.NewControlId(), 'float'],
                            'gnomAngularScale'      : [1, wx.Window.NewControlId(), 'int'],
                            'gnomSystem'            : [0, wx.Window.NewControlId(), 'int'],
                            'gnomFormFactor'        : ['', wx.Window.NewControlId(), 'text'],
                            'gnomRadius56'          : [-1, wx.Window.NewControlId(), 'float'],
                            'gnomRmin'              : [-1, wx.Window.NewControlId(), 'float'],
                            'gnomFWHM'              : [-1, wx.Window.NewControlId(), 'float'],
                            'gnomAH'                : [-1, wx.Window.NewControlId(), 'float'],
                            'gnomLH'                : [-1, wx.Window.NewControlId(), 'float'],
                            'gnomAW'                : [-1, wx.Window.NewControlId(), 'float'],
                            'gnomLW'                : [-1, wx.Window.NewControlId(), 'float'],
                            'gnomSpot'              : ['', wx.Window.NewControlId(), 'text'],
                            'gnomExpt'              : [0, wx.Window.NewControlId(), 'int'],

                            #DAMMIF settings
                            'dammifMode'            : ['Fast', wx.Window.NewControlId(), 'choice'],
                            'dammifSymmetry'        : ['P1', wx.Window.NewControlId(), 'choice'],
                            'dammifAnisometry'      : ['Unknown', wx.Window.NewControlId(), 'choice'],
                            'dammifUnit'            : ['Unknown', wx.Window.NewControlId(), 'choice'],
                            'dammifChained'         : [False, wx.Window.NewControlId(), 'bool'],
                            'dammifConstant'        : ['', wx.Window.NewControlId(), 'text'],
                            'dammifOmitSolvent'     : [True, wx.Window.NewControlId(), 'bool'],
                            'dammifDummyRadius'     : [-1, wx.Window.NewControlId(), 'float'],
                            'dammifSH'              : [-1, wx.Window.NewControlId(), 'int'],
                            'dammifPropToFit'       : [-1, wx.Window.NewControlId(), 'float'],
                            'dammifKnots'           : [-1, wx.Window.NewControlId(), 'int'],
                            'dammifCurveWeight'     : ['e', wx.Window.NewControlId(), 'choice'],
                            'dammifRandomSeed'      : ['', wx.Window.NewControlId(), 'text'],
                            'dammifMaxSteps'        : [-1, wx.Window.NewControlId(), 'int'],
                            'dammifMaxIters'        : [-1, wx.Window.NewControlId(), 'int'],
                            'dammifMaxStepSuccess'  : [-1, wx.Window.NewControlId(), 'int'],
                            'dammifMinStepSuccess'  : [-1, wx.Window.NewControlId(), 'int'],
                            'dammifTFactor'         : [-1, wx.Window.NewControlId(), 'float'],
                            'dammifRgPen'           : [-1, wx.Window.NewControlId(), 'float'],
                            'dammifCenPen'          : [-1, wx.Window.NewControlId(), 'float'],
                            'dammifLoosePen'        : [-1, wx.Window.NewControlId(), 'float'],
                            'dammifAnisPen'         : [-1, wx.Window.NewControlId(), 'float'],
                            'dammifMaxBeadCount'    : [-1, wx.Window.NewControlId(), 'int'],
                            'dammifReconstruct'     : [15, wx.Window.NewControlId(), 'int'],
                            'dammifDamaver'         : [True, wx.Window.NewControlId(), 'bool'],
                            'dammifDamclust'        : [False, wx.Window.NewControlId(), 'bool'],
                            'dammifRefine'          : [True, wx.Window.NewControlId(), 'bool'],
                            'dammifProgram'         : ['DAMMIF', wx.Window.NewControlId(), 'choice'],

                            #DAMMIN settings that are not included in DAMMIF settings
                            'damminInitial'         : ['S', wx.Window.NewControlId(), 'choice'], #Initial DAM
                            'damminKnots'           : [20, wx.Window.NewControlId(), 'int'],
                            'damminConstant'        : [0, wx.Window.NewControlId(), 'float'],
                            'damminDiameter'        : [-1, wx.Window.NewControlId(), 'float'],
                            'damminPacking'         : [-1, wx.Window.NewControlId(), 'float'],
                            'damminCoordination'    : [-1, wx.Window.NewControlId(), 'float'],
                            'damminDisconPen'       : [-1, wx.Window.NewControlId(), 'float'],
                            'damminPeriphPen'       : [-1, wx.Window.NewControlId(), 'float'],
                            'damminCurveWeight'     : ['1', wx.Window.NewControlId(), 'choice'],
                            'damminAnealSched'      : [-1, wx.Window.NewControlId(), 'float'],

                            #Weighted Average Settings
                            'weightCounter'         : ['', wx.Window.NewControlId(), 'choice'],
                            'weightByError'         : [True, wx.Window.NewControlId(), 'bool'],

                            #Similarity testing settings
                            'similarityTest'        : ['CorMap', wx.Window.NewControlId(), 'choice'],
                            'similarityCorrection'  : ['Bonferroni', wx.Window.NewControlId(), 'choice'],
                            'similarityThreshold'   : [0.01, wx.Window.NewControlId(), 'float'],
                            'similarityOnAverage'   : [True, wx.Window.NewControlId(), 'bool'],
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

    file_obj = open(loadpath, 'rb')
    try:
        loaded_param = cPickle.load(file_obj)
    except (KeyError, EOFError, ImportError, IndexError, AttributeError, cPickle.UnpicklingError) as e:
        print 'Error type: %s, error: %s' %(type(e).__name__, e)
        file_obj.close()
        return False
    file_obj.close()

    keys = loaded_param.keys()
    all_params = raw_settings.getAllParams()

    for each_key in keys:
        if each_key in all_params:
            all_params[each_key][0] = copy.copy(loaded_param[each_key])
        else:
            print 'WARNING: ' + str(each_key) + " not found in RAWSettings."

    main_frame = wx.FindWindowByName('MainFrame')
    main_frame.queueTaskInWorkerThread('recreate_all_masks', None)

    postProcess(raw_settings)

    return True

def postProcess(raw_settings):
    fixBackwardsCompatibility(raw_settings)

    dir_check_list = [('AutoSaveOnImageFiles', 'ProcessedFilePath'), ('AutoSaveOnAvgFiles', 'AveragedFilePath'),
                    ('AutoSaveOnSub', 'SubtractedFilePath'), ('AutoSaveOnBift', 'BiftFilePath'),
                    ('AutoSaveOnGnom', 'GnomFilePath'), ('OnlineModeOnStartup', 'OnlineStartupDir')
                    ]

    file_check_list = [('NormFlatfieldEnabled', 'NormFlatfieldFile')]

    change_list = []

    message_dir = {'AutoSaveOnImageFiles'   : '- AutoSave processed image files',
                    'AutoSaveOnAvgFiles'    : '- AutoSave averaged files',
                    'AutoSaveOnSub'         : '- AutoSave subtracted files',
                    'AutoSaveOnBift'        : '- AutoSave BIFT files',
                    'AutoSaveOnGnom'        : '- AutoSave GNOM files',
                    'OnlineModeOnStartup'   : '- Start online mode when RAW starts',
                    'NormFlatfieldEnabled'  : '- Apply a flatfield correction'
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
    param_dict = raw_settings.getAllParams()
    keys = param_dict.keys()

    exclude_keys = ['ImageFormatList', 'ImageHdrFormatList', 'BackgroundSASM', 'CurrentCfg', 'csvIncludeData', 'CompatibleFormats', 'DataSECM']

    save_dict = {}

    for each_key in keys:
        if each_key not in exclude_keys:
            save_dict[each_key] = param_dict[each_key][0]

    save_dict = copy.deepcopy(save_dict)

    #remove big mask arrays from the cfg file
    masks = save_dict['Masks']

    for key in masks.keys():
        masks[key][0] = None

    file_obj = open(savepath, 'wb')
    try:
        cPickle.dump(save_dict, file_obj, cPickle.HIGHEST_PROTOCOL)
    except Exception as e:
        print '<Error> type: %s, message: %s' %(type(e).__name__, e)
        file_obj.close()
        return False

    file_obj.close()

    ## Make a backup of the config file in case of crash:
    backup_file = os.path.join(RAWGlobals.RAWWorkDir, 'backup.cfg')

    FileObj = open(backup_file, 'wb')
    try:
        cPickle.dump(save_dict, FileObj, cPickle.HIGHEST_PROTOCOL)
    except Exception as e:
        print 'Error type: %s, error: %s' %(type(e).__name__, e)
        FileObj.close()
        return False
    FileObj.close()

    dummy_settings = RawGuiSettings()

    test_load = loadSettings(dummy_settings, savepath)

    if not test_load:
        os.remove(savepath)

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

