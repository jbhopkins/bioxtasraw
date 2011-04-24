'''
Created on Jul 16, 2010

@author: Soren Nielsen
'''
import wx, cPickle, copy
import SASFileIO

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
                            #'NormalizeConst'    : [1.0,   wx.NewId(), 'float'],
                            #'NormalizeConstChk' : [False, wx.NewId(),  'bool'],
                            #'NormalizeM2'       : [False, wx.NewId(),  'bool'],
                            #'NormalizeTime'     : [False, wx.NewId(),  'bool'],  
                            #'NormalizeM1'       : [False, wx.NewId(),  'bool'],
                            'NormAbsWater'      : [False,   wx.NewId(),  'bool'],
                            'NormAbsWaterI0'    : [0.01632, wx.NewId(),  'float'],
                            'NormAbsWaterTemp'  : ['25',    wx.NewId(),  'choice'],
                            'NormAbsWaterConst' : [1.0,     wx.NewId(),  'float'],
                            
                            
                            
                            'NormalizeTrans'    : [False, wx.NewId(),  'bool'],
                            'Calibrate'         : [False, wx.NewId(),  'bool'],  # Calibrate AgBe
                            'CalibrateMan'      : [True, wx.NewId(),  'bool'],  # Calibrate manual (wavelength / distance)
                            'AutoBgSubtract'    : [False, wx.NewId(),  'bool'],
                            'CountNormalize'    : [1.0,   wx.NewId(), 'float'],
                            
                            'AutoBIFT'          : [False, wx.NewId(), 'bool'],
                            'AutoAvg'           : [False, wx.NewId(), 'bool'],
                            'AutoAvgRemovePlots': [False, wx.NewId(), 'bool'],
             
                            'AutoAvgRegExp'     : ['', wx.NewId(), 'text'],
                            'AutoAvgNameRegExp' : ['', wx.NewId(), 'text'],
                            'AutoAvgNoOfFrames' : [1,  wx.NewId(),  'int'],
                            'AutoBgSubRegExp'   : ['', wx.NewId(), 'text'],
             
                            'UseOnlineFilter' : [False, wx.NewId(), 'bool'],
                            'OnlineFilterExt' : ['',    wx.NewId(), 'text'],
             
             
                            #CENTER / BINNING
                            'Binsize'    : [2,     wx.NewId(), 'int'],
                            'Xcenter'    : [512.0, wx.NewId(), 'float'],
                            'Ycenter'    : [512.0, wx.NewId(), 'float'],
                            'QrangeLow'  : [25,    wx.NewId(), 'int'],
                            'QrangeHigh' : [9999,  wx.NewId(), 'int'],
                            'StartPoint' : [0,     wx.NewId(), 'int'],
                            'PixelCalX'  : [200,   wx.NewId(), 'int'],
                            'PixelCalY'  : [200,   wx.NewId(), 'int'],
                            'ImageDim'   : [[1024,1024]],
             
                            #MASKING
                            'SampleFile'              : [None, wx.NewId(), 'text'],
                            'BackgroundSASM'          : [None, wx.NewId(), 'text'],
                            
                            #'TransparentBSMaskFilename': [None, wx.NewId(), 'maskFilename'],
                            #'BeamStopMaskFilename'     : [None, wx.NewId(), 'maskFilename'],
                            #'ReadOutNoiseMaskFilename' : [None, wx.NewId(), 'maskFilename'],
                            'NormAbsWaterFile'        : [None, wx.NewId(), 'text'],
                            'NormAbsWaterEmptyFile'   : [None, wx.NewId(), 'text'],
                                    
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
                            'WaveLength'          : [1.0,  wx.NewId(), 'float'],
                            'SampleDistance'      : [1000, wx.NewId(), 'float'],
                            'SampleThickness'     : [0.0, wx.NewId(), 'float'],
                            'ReferenceQ'          : [0.0, wx.NewId(), 'float'],
                            'ReferenceDistPixel'  : [0,   wx.NewId(), 'int'],
                            'ReferenceDistMm'     : [0.0, wx.NewId(), 'float'],
                            'DetectorPixelSize'   : [70.5, wx.NewId(), 'float'],
                            'SmpDetectOffsetDist' : [0.0, wx.NewId(), 'float'],
                            #'WaterAvgMinPoint'    : [30,  wx.NewId(), 'int'],
                            #'WaterAvgMaxPoint'    : [500, wx.NewId(), 'int'],
             
                            #DEFAULT BIFT PARAMETERS
                            'maxDmax'     : [400.0,  wx.NewId(), 'float'],
                            'minDmax'     : [10.0,   wx.NewId(), 'float'],
                            'DmaxPoints'  : [10,     wx.NewId(), 'int'],
                            'maxAlpha'    : [1e10,   wx.NewId(), 'float'],
                            'minAlpha'    : [150.0,  wx.NewId(), 'float'],
                            'AlphaPoints' : [16,     wx.NewId(), 'int'],
                            'PrPoints'    : [50,     wx.NewId(), 'int'],
             
                            #DEFAULT GNOM PARAMETERS
                            'gnomMaxAlpha'    : [60,   wx.NewId(), 'float'],
                            'gnomMinAlpha'    : [0.01, wx.NewId(), 'float'],
                            'gnomAlphaPoints' : [100,  wx.NewId(), 'int'],
                            'gnomPrPoints'    : [50,   wx.NewId(), 'int'],
                            'gnomFixInitZero' : [True, wx.NewId(), 'bool'],
             
                            'OSCILLweight'    : [3.0, wx.NewId(), 'float'],
                            'VALCENweight'    : [1.0, wx.NewId(), 'float'],
                            'POSITVweight'    : [1.0, wx.NewId(), 'float'],
                            'SYSDEVweight'    : [3.0, wx.NewId(), 'float'],
                            'STABILweight'    : [3.0, wx.NewId(), 'float'],
                            'DISCRPweight'    : [1.0, wx.NewId(), 'float'],
             
                            #DEFAULT IFT PARAMETERS:
                            'IFTAlgoList'        : [['BIFT', 'GNOM']],
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
                            'AutoSaveOnImageFiles' : [False, wx.NewId(), 'bool'],
                            'AutoSaveOnAvgFiles'   : [False, wx.NewId(), 'bool'],
                            'AutoSaveOnSub'        : [False, wx.NewId(), 'bool'],
                
                            #IMAGE FORMATS
                            'ImageFormatList'      : [SASFileIO.all_image_types],
                            'ImageFormat'          : ['Quantum', wx.NewId(), 'choice'],
                            
                            #HEADER FORMATS
                            'ImageHdrFormatList'   : [SASFileIO.all_header_types],
                            'ImageHdrFormat'       : ['None', wx.NewId(), 'choice'],
                            
                            'ImageHdrList'         : [None],
                            'FileHdrList'          : [None],
                             
                            'UseHeaderForCalib'    : [False, wx.NewId(), 'bool'],
                            
                            # Header bind list with [(Description : parameter key, header_key)] 
                            'HeaderBindList'       : [{'Beam X Center'            : ['Xcenter',           None],
                                                       'Beam Y Center'            : ['Ycenter',           None],
                                                       'Sample Detector Distance' : ['SampleDistance',    None],
                                                       'Wavelength'               : ['WaveLength',        None],
                                                       'Detector Pixel Size'      : ['DetectorPixelSize', None]}],
                                                       
                            'NormalizationList'    : [None, wx.NewId(), 'text'],
                            'EnableNormalization'  : [True, wx.NewId(), 'bool'],
                            
                            #List of available processing commands:
                            'PreProcessingList'    : [None],
                            'PostProcessingList'   : [None],
                            
                            #List containing processing names to be executed:
                            'PreProcessing'        : [None],
                            'PostProcessing'       : [None],
                            
                            'CurrentCfg'         : [None],
                             
                            'CurveOffsetVal'       : [0.0,   wx.NewId(), 'float'],
                            'OffsetCurve'          : [False, wx.NewId(), 'bool'],
                            'CurveScaleVal'        : [1.0,   wx.NewId(), 'float'],
                            'ScaleCurve'           : [False, wx.NewId(), 'bool'],
                            
                            
                            #GUI Settings:
                            
                            'ManipItemCollapsed'  : [False, wx.NewId(), 'bool'] 
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
    
def loadSettings(raw_settings, loadpath):
    
    file_obj = open(loadpath, 'r')
    loaded_param = cPickle.load(file_obj)
    file_obj.close()
    
    keys = loaded_param.keys()
    all_params = raw_settings.getAllParams()
    
    for each_key in keys:
        if each_key in all_params:
            all_params[each_key][0] = copy.copy(loaded_param[each_key])
        else:
            print 'ERROR: ' + str(each_key) + " not found in RAWSettings."  
    
    main_frame = wx.FindWindowByName('MainFrame')
    main_frame.queueTaskInWorkerThread('recreate_all_masks', None)
    
    return True

def saveSettings(raw_settings, savepath):
    param_dict = raw_settings.getAllParams() 
    keys = param_dict.keys()
    
    exclude_keys = ['ImageFormatList', 'ImageHdrFormatList', 'BackgroundSASM', 'CurrentCfg']
    
    save_dict = {}
    
    for each_key in keys:
        if each_key not in exclude_keys:
            save_dict[each_key] = copy.copy(param_dict[each_key][0])
    
    #remove big mask arrays from the cfg file
    masks = save_dict['Masks'] 
    oldMasks = {}
    
    # Saving created image masks that will be removed for the cfg file.
    for key in masks.keys():
        oldMasks[key] = copy.deepcopy(masks[key][0]) 
        masks[key][0] = None

    file_obj = open(savepath, 'w')
    cPickle.dump(save_dict, file_obj)
    file_obj.close()
    
    for key in masks.keys():
        masks[key][0] = oldMasks[key] 
        
    return True
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
    