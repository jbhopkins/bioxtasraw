#******************************************************************************
# This file is part of BioXTAS RAW.
#
#    BioXTAS RAW is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    BioXTAS RAW is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with BioXTAS RAW.  If not, see <http://www.gnu.org/licenses/>.
#
#******************************************************************************

#-------------------------------------------------------------------------------------
#   T(x,y) = I(y cos(2*pi*x)/x_size + x_center  ,  y sin(2*pi*x)/x_size + y_center)
#-------------------------------------------------------------------------------------

from __future__ import division

from pylab import *
import cPickle # time
from math import pi, asin, tan, atan
import Image, os
import scipy, wx
from numpy import *
from scipy import weave
from scipy import io
from scipy.weave import converters
import fileIO
import masking
import cProfile, copy

import ravg_ext

from scipy.weave import ext_tools

#def filterImage(filter, img, dim):
#    
#    xlen = dim[0]
#    ylen = dim[1]
#    
#    newImg = zeros((xlen, ylen))
#    
#    filt_size = 4
#       
#    if filt_size == 4:
#        for y in range(0, ylen-1):
#            print y
#            for x in range(0, xlen-1):
#                newImg[y,x] = int(img[y,x] * filter[0,0] + img[y, x+1] * filter[0,1]+ img[y+1,x+1] * filter[1,1]+ img[y+1, x] * filter[1,0])
#   
#    print 'done!'
#    if filt_size == 2:
#        
#        if filt_dir == 'h':
#            pass
#        
#        if filt_dir == 'v':
#            pass
#        
#    return newImg

#def createFilter(x_c, y_c):
#    
#    filter = zeros((3,3))
#    
#    x = x_c % 1
#    y = y_c % 1
#    
#    l_edge = x - 0.5
#    r_edge = x + 0.5
#    
#    t_edge = y + 0.5
#    b_edge = y - 0.5
#    
#    print l_edge
#    print r_edge
#    print t_edge
#    print b_edge
#    
#    dir = None
#    
##    if l_edge < 0.0 and t_edge < 1.0:
##        filter[1,0] = abs(l_edge * t_edge)
#    
#    if l_edge < 0.0 and t_edge > 1.0:
#        filter[0,0] = abs(l_edge * (t_edge-1))
#    
#    if l_edge < 0.0 and b_edge < 0.0:
#        filter[2,0] = abs(l_edge * b_edge)
#        print "ping!"
#    
#    if l_edge < 0.0 and b_edge > 0.0:
#        filter[1,0] = abs( l_edge * (1-(t_edge-1)) )
#        
#    if l_edge > 0.0 and t_edge > 1.0:
#        filter[0,1] = (t_edge-1)  * (1-(r_edge-1))
#
#    if r_edge < 1.0 and b_edge < 0.0:
#        filter[1,0] = abs(l_edge * t_edge)
#        
#    if r_edge  < 1.0 and b_edge > 0.0:
#        filter[0,1] = abs(r_edge * b_edge)
#        
#    if r_edge  < 1.0 and b_edge < 0.0:
#        filter[2,1] = abs(r_edge * b_edge)
#        
#    if r_edge > 1.0 and b_edge < 0.0:
#        filter[2,1] = abs( b_edge * (1-(r_edge-1)))
#    
#    if r_edge > 1.0 and b_edge < 0.0:
#        filter[2,2] = abs((r_edge-1) * b_edge)
#    
#    if r_edge > 1.0 and b_edge > 0.0:
#        filter[1,2] = abs((r_edge-1) * (1-(t_edge-1)) )
#    
#    if r_edge > 1.0 and b_edge < 0.0:
#        filter[1,2] = abs((r_edge-1) * t_edge)
#        
#    if r_edge > 1.0 and t_edge > 1.0:
#        filter[0,2] = abs((r_edge-1) * (t_edge-1))
#        
#    if r_edge == 1 and t_edge > 1:
#        filter[0,1] = t_edge -1
#        dir = 'v'
#        
#    if r_edge == 1 and t_edge < 1:
#        filter[2,1] = abs(b_edge)
#        dir = 'v'
#        
#    if t_edge == 1 and r_edge > 1:
#        filter[1,2] = abs(r_edge - 1)
#        dir = 'h'
#    
#    if t_edge == 1 and r_edge < 1:
#        filter[1,0] = abs(l_edge)
#        dir = 'h'
#  
#    filter[1,1] = 1.0 - sum(filter)
#    
#    return filter, dir


def radialAverage(in_image, dim, x_c, y_c, mask = None, readoutNoise_mask = None):
    ''' Radial averaging. and calculation of readout noise from a readout noise mask.
        It also returns the errorbars assuming possion distributed data
        
        in_image :     Input image
        dim:           Image dimentions
        x_c, y_c :     (x_c, y_c) Center coordinate in the image (Pixels)
        q_range :      q_range specifying [low_q high_q]
      
    '''
    in_image = np.float64(in_image)
    
    xlen = dim[0]
    ylen = dim[1]
    
    x_c = float(x_c)
    y_c = float(y_c)
    
    #maxPointsPrQ = len(masking.bresenhamCirclePoints(round(xlen / 2)))
  
    # If no mask is given, the mask is pure ones
    if mask == None:
        mask = ones((xlen,ylen))
        
    if readoutNoise_mask == None:
        readoutNoiseFound = 0
        readoutNoise_mask = zeros((xlen,ylen), dtype = np.float64)
    else:
        readoutNoiseFound = 1
    
    readoutN = zeros((1,4), dtype = np.float64)
    
    # Find the maximum distance to the edge in the image:
    maxlen = int(max(xlen - x_c, ylen - y_c, xlen - (xlen - x_c), ylen - (ylen - y_c)))
    
    # we set the "q_limits" (in pixels) so that it does radial avg on entire image (maximum qrange possible).
    q_range = (0, maxlen)           

    ##############################################
    # Reserving memory for radial averaged output:
    ##############################################
    hist = zeros(q_range[1], dtype = np.float64)        
    hist_count = zeros((3,q_range[1]), dtype = np.float64)  # -----" --------- for number of pixels in a circle at a certain q
       
    low_q = q_range[0]
    high_q = q_range[1]
    
    zinger_threshold = 60000        #Too Hardcoded!
            
    print 'Doing  radial average...',
    ravg_ext.ravg(readoutNoiseFound,
                   readoutN,
                   readoutNoise_mask,
                   xlen, ylen,
                   x_c, y_c,
                   hist,
                   low_q, high_q,
                   in_image,
                   hist_count,
                   mask)
    print 'done'
    
    hist_cnt = hist_count[2,:]    #contains x-mean
    hist_count = hist_count[0,:]  #contains N 
    
    std_i = sqrt(hist_cnt/hist_count)
    
    std_i[np.where(np.isnan(std_i))] = 0
    
    iq = hist / hist_count
    iq[0] = in_image[x_c, y_c]  # the center is not included in the radial average, so it is set manually her
    
    errorbars = std_i / sqrt(hist_count)
    
    if readoutNoiseFound:
        #Average readoutNoise
        readoutNoise = readoutN[0,1] /  readoutN[0,0]
        readoutNoise[np.where(np.isnan(readoutNoise))] = 0
        
        #Standard deviation
        std_n = sqrt(readoutN[0,4] / readoutN[0,0])
        errorbarNoise = std_n / sqrt(readoutN[0,0]) 
        
        #Readoutnoise average subtraction
        iq = iq - readoutNoise
        errorbars = sqrt(power(errorbars, 2) + power(errorbarNoise, 2))
    
    res = None #used for testing
    
    return [iq, res, errorbars]

def checkMaskSize(mask, dim):
    
    masksize = shape(mask)
    
    if masksize != dim:
        print 'masksize is wrong!'
        
        file_db = str(dim) 
        mask_db = str(masksize)
        
        raise Exception('mask: ' + mask_db + ' file: ' + file_db)

def loadM(newArr, dim, mask = None, readout_noise_mask = None, q_range = None, hdr = None, x_center = None, y_center = None, pixelcal = None, binsize = None):
    ''' 
        Load measurement. Loads an image file, does preprocessing: masking, radial average, errrorbars
        and returns a measurement object
    '''
    
    # load sample image
    #newArr, dim = loadImage(img_filename)
    
    # newArr[1085, 1162:1262] = 200            # X and Y is switched!!??   its (Y,X) in SCIPY!! WTF!
    
    # Load matlab mask (if one is given)
    if mask != None:
        try:
            checkMaskSize(mask, dim)
        except Exception, msg:
            print msg
            raise Exception('Beamstop mask is wrong size, ' + str(msg) + '\n\nPlease change the mask settings to make this plot')

    if readout_noise_mask != None:
        try: 
            checkMaskSize(readout_noise_mask, dim)
        except Exception, msg:
            print msg
            raise Exception('Readout-noise mask is wrong size, ' + str(msg) + '\n\nPlease change the mask settings to make this plot')
    
    # If marccd = true (MarCCD camera used) we should get the center coords from the marccd header file
    # the marccd coords can be wrong though!!! 
#    if marccdHeader == True:
#        try:
#            Mar_hdr = readHeader(img_filename)
#        except Exception, msg:
#            print msg
#            raise Exception('Error reading headerfile: ' + str(msg))
        
        #x_center = Mar_hdr['beam_x']                # This is not safe.. the center is entered manually at Maxlab
        #y_center = Mar_hdr['beam_y']                # There should be an override.. and a way to change the center in the header
#    else:
#        Mar_hdr = None

    try:
        [I_raw, res, Errorbars_raw] = radialAverage(newArr, dim, y_center, x_center, mask, readout_noise_mask)
        #cProfile.runctx("[I_raw, res, Errorbars_raw] = radialAverage(newArr, dim, y_center, x_center, mask, readout_noise_mask)", globals(), locals())        # NOTE an error in radialAveraged requires x_cen and y_cen to be switched
                                                                                                                     # the error is caused by scipy using (Y,X) instead of (X,Y)   
    except IndexError, msg:
        
        print 'Center coordinates too large: ' + str(msg)
    
        wx.CallAfter(wx.MessageBox, "The center coordinates are too large, using image center instead.", "Center coordinates does not fit image", wx.OK | wx.ICON_ERROR)
        
        
        [I_raw, res, Errorbars_raw] = radialAverage(newArr, dim, dim[0]/2, dim[1]/2, mask, readout_noise_mask)        # NOTE an error in radialAveraged requires x_cen and y_cen to be switched


    # Insert it all into a measurement object
    q = linspace(0,len(I_raw), len(I_raw))
    
    M = ImageMeasurement(I_raw, q, Errorbars_raw, hdr, q_range, None, binsize)
    
    M.imgdim = dim
    
    if q_range:
        M.setQrange(q_range)
    
    return M, (newArr, dim)

def removeSpikes(intensityArray, startIdx = 0, averagingWindowLength = 10, stds = 4):
    ''' Removes spikes from the radial averaged data          
        Threshold is currently 4 times the standard deviation 
    
        averagingWindowLength :     The number of points before the spike
                                    that are averaged and used to replace the spike. 
        
        startIdx :                  Index in intensityArray to start the search for spikes 
        
    '''
 
    for i in range(averagingWindowLength + startIdx, len(intensityArray)):
        
        averagingWindow = intensityArray[i - averagingWindowLength : i - 1]
        
        stdOfAveragingWindow = scipy.std(averagingWindow)
    
        meanOfAvergingWindow = scipy.mean(averagingWindow)
        
        threshold = meanOfAvergingWindow + (stds * stdOfAveragingWindow)
        
        if intensityArray[i] > threshold:
            intensityArray[i] = meanOfAvergingWindow
        
    return intensityArray


def loadMask(filename, varname = 'mask'):
    ''' Loads a mask form a matlab .mat file. Name of the mask variable in matlab needs to be "mask" for it to work
        otherwise the variable name can be specified in varname.
        
        UPDATE: now also takes BioXTAS RAW mask files
    '''

    if filename[-3:] == 'msk':
        
        FileObj = open(filename, 'r')            
        maskPlotParameters = cPickle.load(FileObj)
        FileObj.close()
        
        return createMaskFromRAWFormat(maskPlotParameters)

    else:    #Try matlab format (from SAXSGUI)
        
        matlab_mask_dict = io.loadmat(filename)
        return matlab_mask_dict[varname]

def createMaskFromRAWFormat(maskPlotParameters):
    
    border = maskPlotParameters['imageBorder']
    imageDimentions = maskPlotParameters['imageDimentions']
    storedMasks = maskPlotParameters['storedMasks']
    
    mask = ones(imageDimentions)
    
    for each in storedMasks:
        fillPoints = each.getFillPoints()
                
        for eachp in fillPoints:
            mask[eachp] = 0

    # Raw masks are created with a border to make edgemasking easier, this will remove the border:
    finalMask = mask[ border/2 : imageDimentions[1] - border/2, border/2 : imageDimentions[0] - border/2]
    
    return finalMask
        
#def saveMeasurement(Exp):
#    
#    full_path_filename = Exp.param['filename']
#    no_path_filename = os.path.split(full_path_filename)[1]
#    
#    path = os.path.split(full_path_filename)[0]
#              
#    Exp.param['filename'] = no_path_filename
#               
#    if Exp.isBgSubbed:        
#        filename = path + '\BSUB_' + no_path_filename + '.rad'    
#    else:
#        filename = full_path_filename + '.rad'    
#               
#    fileIO.writeRadFile(Exp, filename)
#                    
#    return filename


def averageMeasurements(ExpList, expParams):
    
    noOfFiles = len(ExpList)
    size1 = len(ExpList[0].i)
    
    for idx in range(1, noOfFiles):
        size2 = len(ExpList[idx].i)
    
        if size1 != size2:
            wx.MessageBox('All datasets must be of same length!', 'Averaging aborted')
            return None
    
    if expParams['ZingerRemovalAvg']:
        print "Removing Zingers!!!"
        
        sensitivity = float(expParams['ZingerRemovalAvgStd'])
        avg, err = removeOutliersAndAverage(ExpList, sensitivity)
        
        CopyExpObj = ExpList[0]
        AvgExpObj = RadFileMeasurement(avg, CopyExpObj.q.copy(), err, CopyExpObj.param.copy())
        
        AvgExpObj.i_raw = AvgExpObj.i.copy()
        AvgExpObj.errorbars_raw = AvgExpObj.errorbars.copy()
        
        path_file = os.path.split(AvgExpObj.param['filename'])
        AvgExpObj.param['filename'] = os.path.join(path_file[0], 'AVG_' + path_file[1])
        
        return AvgExpObj
    
    else:
    
        I_all = ExpList[0].i
        E_all = ExpList[0].errorbars
    
        for i in range(1,len(ExpList)):
            I_all = vstack((I_all, ExpList[i].i))
            E_all = vstack((E_all, ExpList[i].errorbars))
        
        avg = mean(I_all, 0)
                
        err = sqrt(sum(power(E_all,2),0))/ len(E_all)
        
        CopyExpObj = ExpList[0]
        AvgExpObj = RadFileMeasurement(avg, CopyExpObj.q.copy(), err, CopyExpObj.param.copy())
    
        path_file = os.path.split(AvgExpObj.param['filename'])
        AvgExpObj.param['filename'] = os.path.join(path_file[0], 'AVG_' + path_file[1])
    
        return AvgExpObj

def applyDataManipulations(ExpObj, expParams, checkedTreatments):
    
    if ExpObj.filetype == 'image':
            
            filename = os.path.split(ExpObj.param['filename'])[1]
            
            # Go through all of the chosen treatments in the GUI
            if expParams['ZingerRemoval'] == True:
                std = expParams['ZingerRemoveSTD']
                window = expParams['ZingerRemoveWinLen']
                startIdx = expParams['ZingerRemoveIdx']
                
                removeSpikes(ExpObj.i_raw, startIdx, window, std)
            
            if checkedTreatments:
                for each in checkedTreatments:
                    
                    if each == 'ScaleCurve':
                        try:
                            ExpObj.scale((expParams['CurveScaleVal']))
                        except Exception, msg:
                            wx.CallAfter(wx.MessageBox,str(msg) + '\n\n' + filename + '. Scale by constant: ' + str(expParams['CurveScaleVal']) + ' failed!', 'Scale by constant failed!', wx.OK | wx.ICON_ERROR)
                    
                    if each == 'OffsetCurve':
                        try:
                            ExpObj.offset((expParams['CurveOffsetVal']))
                        except Exception, msg:
                            wx.CallAfter(wx.MessageBox,str(msg) + '\n\n' + filename + '. Offset by constant: ' + str(expParams['CurveOffsetVal']) + ' failed!', 'Offset by constant failed!', wx.OK | wx.ICON_ERROR)
                
                    if each == 'NormalizeM2':
                        try:
                            ExpObj.normalizeM2()
                        except Exception, msg:
                            wx.CallAfter(wx.MessageBox,str(msg) + '\n\n' + filename + ' will not be normalized by M2.', 'Normalization by M2 Failed!', wx.OK | wx.ICON_ERROR)
                            
                    elif each == 'NormalizeM1':
                        try:
                            ExpObj.normalizeM1()
                        except Exception, msg:
                            wx.CallAfter(wx.MessageBox,str(msg) + '\n\n' + filename + ' will not be normalized by M1.', 'Normalization by M1 Failed!', wx.OK | wx.ICON_ERROR)
                            
                    elif each == 'NormalizeTime':
                        try:
                            ExpObj.normalizeByTime()
                        except Exception, msg:
                            wx.CallAfter(wx.MessageBox,str(msg) + '\n\n' + filename + ' will not be normalized by exposure time.', 'Normalization by exposure time Failed!', wx.OK | wx.ICON_ERROR)
                            
                    elif each == 'Calibrate':
                        agbeCalibration(ExpObj, expParams)
                              
                    elif each == 'CalibrateMan':
                        manualCalibration(ExpObj, expParams)
                        
                    elif each == 'NormalizeAbs':
                        normalizeAbsoluteScale(ExpObj, expParams)

                    elif each == 'NormalizeTrans':
                        try:
                            ExpObj.normalizeByTransmission()
                        except Exception, msg:
                            wx.CallAfter(wx.MessageBox,str(msg) + '\n\n' + filename + ' will not be normalized by transmission.', 'Normalization by Transmission Failed!', wx.OK | wx.ICON_ERROR)
                    
            binsize = expParams['Binsize']
            ExpObj.setBinning(binsize)
    
    # IF ITS NOT AN IMAGE FILE:
    else:
        
        if expParams['ZingerRemoval'] == True:
            
            std = expParams['ZingerRemoveSTD']
            window = expParams['ZingerRemoveWinLen']
            startIdx = expParams['ZingerRemoveIdx']
            
            removeSpikes(ExpObj.i, startIdx, window, std)
            
def normalizeAbsoluteScale(ExpObj, expParams):
    #Absolute Calibration
                        
    #ExpObj.normalizeByTransmission()
    #ExpObj.normalizeByTime()
                       
    EmptyCellObj = expParams['EmptyFile']
    WaterObj = expParams['WaterFile']
                        
    WaterBgSubObj = subtractMeasurement(WaterObj, EmptyCellObj)
                       
    waterAvgMaxPoint = expParams['WaterAvgMaxPoint']
    waterAvgMinPoint = expParams['WaterAvgMinPoint']

    avgWater = scipy.mean(WaterBgSubObj.i[waterAvgMinPoint:waterAvgMaxPoint])
                        
    absScaleConstant = 0.0162 / avgWater

    ExpObj.multiplyByConstant(absScaleConstant)
                        
    infoPanel = wx.FindWindowByName('InfoPanel')
    infoPanel.WriteText("Average water value: " + str(avgWater) + '\n\n')
    infoPanel.WriteText("Average water value: " + str(avgWater) + '\n\n')

#--- *** CALIBRATION ***
def agbeCalibration(ExpObj, expParams):
    ''' calculate q-range based on a AgBe measurement 
    
        This in fact only calculates the Sample-Detector distance using the AgBe Measurement
        and then uses manualCalibration()
        
        pixelcal = distance from center to first ring of AgBe
    
    '''
    
    #Number of pixels from center to 1st ring of AgBe
    pixelcal = (expParams['PixelCalX'], expParams['PixelCalY'])

    pixelSizeInMM = expParams['DetectorPixelSize'] / 1000
                        
    SD_Distance = calcAgBeSampleDetectorDist(expParams['PixelCalX'],
                                             expParams['WaveLength'], pixelSizeInMM)

    #Insert Sample-Detector distance in option parameters
    expParams['SampleDistance'] = SD_Distance
      
    manualCalibration(ExpObj, expParams)
                                                                                             
def manualCalibration(ExpObj, expParams):
    
    offsetDist = expParams['SmpDetectOffsetDist']
                        
    xlen = ExpObj.imgdim[0]
    ylen = ExpObj.imgdim[1]
                        
    x_c = expParams['Xcenter']
    y_c = expParams['Ycenter']
    pixelSizeInMM = expParams['DetectorPixelSize'] / 1000
    SD_Distance   = expParams['SampleDistance']
                        
    #Maximum q-vector length (pixels)                    
    maxlen = int(max(xlen - x_c, ylen - y_c, xlen - (xlen - x_c), ylen - (ylen - y_c)))
    
    if offsetDist != 0:
        SD_Distance = SD_Distance + offsetDist
                        
    q = range(0,maxlen)
    
    for i in range(0,maxlen):
        theta = getTheta(SD_Distance, pixelSizeInMM, i)
        q[i] = ((4 * pi * sin(theta)) / expParams['WaveLength']) 
  
    
    
    ExpObj.calibrate(q)
  
def getTheta(SD_Distance, pixelSize, pixelLength):
    ''' 
     Calculates theta for a sample-detector distance,
     the detector pixel size and the length of the pixels.
     
     SD_Distance = sample detector distance
     pixelSize = Detector pixel size
     pixelLength = length of q-vector in pixels. 
    '''
    
    if pixelLength == 0:
        return 0
    else:
        
        theta = .5 * atan(  (pixelLength * pixelSize)/SD_Distance  )

        return theta

def getSolidAngleCorrection(SD_Distance, pixelSize, maxLength):
    '''
      returns an array that should be multiplied to the intensityvalues
      calulated from the detector pixel size to apply the solid
      angle correction.
      
      pixelSize = Detector Pixel Size in milimeters!
      maxLength = maximum q-vector length in pixels
      SD_Distance = Sample-Detector distance
      
    '''

    q_pixel = range(0, maxLength)
    sac = ones((1, maxLength))
    
    for each in range(0,maxLength):
        sac[0,each] = pow(cos(2*getTheta(SD_Distance, pixelSize, each)),3)    #cos^3(2*theta)
        
    return sac

def calcAgBeSampleDetectorDist(agbeDist, wavelength, pixelSizeInMM):
    ''' Calculates the distance between sample and detector based on
     the distance to the 1st circle in the AgBe measurement in pixels 
     
     Input:
     agbeDist = Distance to 1st circle in AgBe measurement in pixels
     wavelength = lambda in q formula
     
     q = ( 4 * pi * sin(theta)) / lambda
     
     tan(theta) = opposite / adjacent 
     
     Ouput:
     SD_Distance = Sample Detector Distance
    '''
    
    q = 0.1076  # Q for 1st cirle in AgBe
    
    sinTheta = (q * wavelength) / (4 * pi)
    
    theta = arcsin(sinTheta)
    
    opposite = agbeDist * pixelSizeInMM
    adjacent = opposite / tan(2*theta)
    
    SD_Distance = adjacent
    
    return SD_Distance
            
def subtractMeasurement(ExpObjSample, ExpObjBackgrnd):
    ''' Subtracts another measurement object.. only meant for background subtraction
        raw data is overwritten to be able to scale and change q-range afterwards. '''
        
    #Do subtraction
    i = ExpObjSample.i - ExpObjBackgrnd.i
    q = ExpObjSample.q
        
    errorbars = sqrt( power(ExpObjSample.errorbars,2) + power(ExpObjBackgrnd.errorbars,2) )
    param = ExpObjSample.param.copy()
        
    # Set subtracted flag
    SubtractedExpObj = RadFileMeasurement(i, q, errorbars, param)
    SubtractedExpObj.isBgSubbed = True
    
    return SubtractedExpObj

def removeOutliersAndAverage(allDataSets, sensitivity = 8):

    I_all = allDataSets[0].i
    E_all = allDataSets[0].errorbars
    
    avg = zeros((size(allDataSets[0].i)))
    err = zeros((size(allDataSets[0].i)))
    
    for i in range(1,len(allDataSets)):
        I_all = vstack((I_all, allDataSets[i].i))
        E_all = vstack((E_all, allDataSets[i].errorbars))
        
    for x in range(0, len(I_all[0,:])):
        
        data = I_all[:,x]
        error = E_all[:,x]
        
        min, max = determineOutlierMaxMin(data, sensitivity)
        
        outliermax = nonzero(data>max)[0]
        outliermin = nonzero(data<min)[0]
        
        if size(outliermax) != 0 and size(outliermin) != 0:
     #       print 'BOTH:', outliermax, outliermin
            outliers = concatenate((outliermax, outliermin))
            nonoutliers = delete(data, outliers)
            nonoutliers_err = delete(error, outliers)
            
            for each in outliers:
                data[each] = mean(nonoutliers)
                error[each] = mean(nonoutliers_err) 
        
        if size(outliermax) != 0 and size(outliermin) == 0:
     #       print 'MAX:', outliermax
            
            nonoutliers = delete(data, outliermax)
            nonoutliers_err = delete(error, outliermax)
            
            for each in outliermax:
                data[each] = mean(nonoutliers)
                error[each] = mean(nonoutliers_err) 
            
        if size(outliermax) == 0 and size(outliermin) != 0:
     #       print 'MIN:', outliermin
            
            nonoutliers = delete(data, outliermin)
            nonoutliers_err = delete(error, outliermax)
            
            for each in outliermin:
                data[each] = mean(nonoutliers)
                error[each] = mean(nonoutliers_err) 
        
        avg[x] = mean(data)
        err[x] = sqrt(sum(power(error,2))) / len(error)
        
    return avg, err            

def determineOutlierMaxMin(data, sensitivity):
    ''' Determines the max and min borders for outliers using 
        interquantile range-based fences '''
            
    N = len(data)
    data_sorted = sort(data)
        
    P25_idx = round((25.0/100) * N)
    P75_idx = round((75.0/100) * (N-1))
        
    P25 = data_sorted[P25_idx]
    P75 = data_sorted[P75_idx]
        
    IQR = P75-P25
        
    min = P25 - (sensitivity * IQR)
    max = P75 + (sensitivity * IQR)
        
    return (min, max)

#--- *** MEASUREMENT CLASSES ***

class Measurement:
    def __init__(self, i, q, errorbars):
        
        self.i = i
        self.q = q
        
        self.i_raw = i        # Backup of q and i arrays. (in case of scaling etc.)
        self.q_raw = q
        
        self.q_range = (0, len(self.q))
        
        self.errorbars_raw = errorbars
        self.scaleval = 1.0
        self.offsetval = 0.0
        
        self.fileformat = 'unknown'
        self.filetype = 'unknown'
        self.errorbars = errorbars
        
        self.isNormalized = False
        self.isCalibrated = False
        self.isBgSubbed = False
        self.isBinned = False
        self.isPlotted = False
        self.isBifted = False
        
        self.idx = [0, len(q)-1]
        
        # For the plotting:
        self.line = None          # A reference to the line on the plot (set in _PlotOnSelectedAxesScale in RAW.py)
        self.axes = None
        self.canvas = None
        self.plotPanel = None
        
        self.itempanel = None
        
    def copy(self):
        
        NewExpObj = copy.copy(self)
        
        NewExpObj.cleanPlotVars()
        NewExpObj.param = copy.copy(self.param)
        
        return NewExpObj
        
    def cleanPlotVars(self):
        
        self.line = None
        self.axes = None
        self.canvas = None
        self.plotPanel = None
        self.itempanel = None
    
    def getFileType(self):
        return self.filetype
        
    def getLine(self):
        return self.line
    
    def setLine(self, line):
        self.line = line
        
    def subtract(self, bg):
        ''' Subtracts another measurement object.. only meant for background subtraction
            raw data is overwritten to be able to scale and change q-range afterwards. '''
        
        #Do subtraction
        self.i = self.i - bg.i
        
        self.i_raw = self.i
        
        #Update errorbars
        self.errorbars = sqrt( power(self.errorbars,2) + power(bg.errorbars,2) )
        self.errorbars_raw = self.errorbars
        
        # Set subtracted flag
        self.isBgSubbed = True

        SubtractedExpObj = RadFileMeasurement(self.i, self.q, self.errorbars, self.param)
        
        return SubtractedExpObj
    
    def scale(self, scaleval):
        
        if scaleval != 1.0:
            self.i = self.i_raw * float(scaleval)
            self.errorbars = self.errorbars_raw * abs(float(scaleval))
            self.scaleval = float(scaleval)
            
            self.setQrange(self.q_range)
            
    def offset(self, offsetValue):
            
        if self.scaleval != 1.0:
            self.i = self.i_raw * float(self.scaleval) + float(offsetValue)
        else:
            self.i = self.i_raw + float(offsetValue)
            
        self.offsetval = float(offsetValue)

        self.setQrange(self.q_range)
        
   
    def setQrange(self, q_range):
        ''' q_min and q_max are in PIXELS! '''
        
        if q_range:
            self.q_range = q_range
        
            q_min, q_max = self.q_range
            
            ## NB! Careful if the background has been subtracted! ..needs to be done
            self.i = self.i_raw[q_min:q_max] * self.scaleval + self.offsetval        # truncate I curve to q_min, q_max
            self.q = self.q_raw[q_min:q_max]                                         #linspace(q_min, q_max, len(self.i))       
            self.errorbars = self.errorbars_raw[q_min:q_max] * self.scaleval
   
        else:
            pass
 
class ImageMeasurement(Measurement):
    
    def __init__(self, i, q, errorbars, mar_hdr, q_range = None, binning = None, pixelcal = None):
        
        Measurement.__init__(self, i, q, errorbars)
        
        self.param = mar_hdr             # Measurement parameters
        self.filetype = 'image'
        self.i_raw = i
        self.q_raw = q
        self.errorbars_raw = errorbars
        self.pixelcal = pixelcal
        self.type = 'image'
        self.imgdim = None
        
        if binning != None:
            self.binning = binning
        else:
            self.binning = 1
        
        if q_range != None:
            self.q_range = q_range                # ability to define q_range
        else:
            self.q_range = (0, len(self.i_raw)-1)
                    
    def normalizeM1(self):
        
        if self.param:
            
            try:
                normFact = self.param['ic']
            except KeyError:
                raise Exception('Error normalizing, IC diode measurement not found')
            
            # Write to status window
            infoPanel = wx.FindWindowByName('InfoPanel')
            infoPanel.WriteText('Normfactor M1: ' + str(normFact) + '\n\n')
            
            print 'M1: ' + str(normFact)
            
            if normFact > 0.0001:
            
                self.i = self.i / normFact
                self.errorbars = self.errorbars / normFact
                
                self.i_raw = self.i_raw / normFact
                self.errorbars_raw = self.errorbars_raw / normFact
            
                self.isNormalized = True
                return normFact
            else:
                raise Exception('Error normalizing, IC diode measurement is below threshold (0.0001) or corrupt')
            
    def normalizeM2(self):
        
        if self.param:
            
            try:
                normFact = (self.param['before'] + self.param['after']) / 2
            except KeyError:
                raise Exception('Error normalizing, "before" and/or "after" measurement not found')
            
            # Write to status window
            infoPanel = wx.FindWindowByName('InfoPanel')
            infoPanel.WriteText(str(os.path.split(self.param['filename'])[1])+ ':\n')
            infoPanel.WriteText('Before: ' + str(self.param['before']) + '\n')
            infoPanel.WriteText('After: ' + str(self.param['after']) + '\n')
            infoPanel.WriteText('Normfactor M2: ' + str(normFact) + '\n\n')
            
            print 'M2: ' + str(normFact)
            
            if normFact > 0.0001:
                self.i = self.i / normFact
                self.errorbars = self.errorbars / normFact
                
                self.i_raw = self.i_raw / normFact
                self.errorbars_raw = self.errorbars_raw / normFact
            
                self.isNormalized = True
            
                return normFact
            
            else:
                raise Exception('Error normalizing, norm factor (before+after)/2\n is below threshold (0.0001) or diode measurements are corrupt')
        
        else:
            return False
        
    def normalizeByTransmission(self):
        
        try:
                M2fact = (self.param['before'] + self.param['after']) / 2
        except KeyError:
                raise Exception('Error normalizing, "before" and/or "after" measurement not found')
            
        try:
                M1fact = self.param['ic']
        except KeyError:
                raise Exception('Error normalizing, IC diode measurement not found')
            
        normFact = M2fact / M1fact
        
        infoPanel = wx.FindWindowByName('InfoPanel')
        wx.CallAfter(infoPanel.WriteText,str(os.path.split(self.param['filename'])[1])+ ':\n')
        wx.CallAfter(infoPanel.WriteText,'Transmission: ' + str(normFact) + '\n')
        
        if normFact > 0.0001:
                self.i = self.i / normFact
                self.errorbars = self.errorbars / normFact
                
                self.i_raw = self.i_raw / normFact
                self.errorbars_raw = self.errorbars_raw / normFact
            
                self.isNormalized = True
                return normFact
        else:
                raise Exception('Error normalizing, transmission norm factor is below threshold (0.0001) or diode measurements are corrupt')
        
        
    def normalizeByTime(self):
        
        if self.param:
            
            try:
                exposureTime = self.param['exposure_time']
            except KeyError:
                raise Exception('Error normalizing, exposure time not found in header')    
            
            print 'Exposure Time: ', str(exposureTime)
            
            if exposureTime > 0:
                self.i = self.i / exposureTime
                self.errorbars = self.errorbars / exposureTime
                
                self.i_raw = self.i_raw / exposureTime
                self.errorbars_raw = self.errorbars_raw / exposureTime
                
                self.isNormalized = True
            else:
                raise Exception('Error normalizing, exposure time is 0 or corrupt!')
        else:
            raise Exception('Header parameters not found')
    
    def multiplyByConstant(self, constant):
        
        self.i = self.i * constant
        self.errorbars = self.errorbars * constant
                
        self.i_raw = self.i_raw * constant
        self.errorbars_raw = self.errorbars_raw * constant
        
    def getM2NormFact(self):
        if self.param:
            fact = (self.param['before'] + self.param['after']) / 2
            return fact
        else:
            return False

    def normalizeM2BgSub(self, factSample):

        if self.param:
            fact = (self.param['before'] + self.param['after']) / 2
            self.i = (self.i * factSample)/ fact 
            self.errorbars = self.errorbars / fact
            
            self.isNormalized = True
            

    def setBinning(self, bins):
        ''' Sets the bin size of the I_q plot '''
        self.binning = bins

        len_iq = len(self.i_raw)
        
        noOfBins = int(floor(len_iq / bins))
    
        new_i = zeros(noOfBins)
        new_q = zeros(noOfBins)
        new_err = zeros(noOfBins)
    
        for eachbin in range(0, noOfBins):
            start_idx = eachbin * bins
            end_idx = (eachbin*bins) + bins
            tst = range(start_idx, end_idx)
            
            new_i[eachbin] = sum(self.i_raw[start_idx:end_idx]) / bins
            new_q[eachbin] = sum(self.q_raw[start_idx:end_idx]) / bins
            new_err[eachbin] = sum(self.errorbars_raw[start_idx:end_idx]) / bins
        
        self.i_raw = new_i
        self.q_raw = new_q
        self.errorbars_raw = new_err
        
        self.isBinned = True
        
        if self.q_range != None:
            newQmin = int(self.q_range[0] / bins)
            newQmax = int(self.q_range[1] / bins)
            
            self.q_range = (newQmin, newQmax)
            
            self.setQrange(self.q_range)
        
    def calibrate(self, q, solidangCorr = None):
        
#        if referenceQ == None:
#            first_ring_dist = 0.1076          # Distance in Angstroem from the center to the first ring of AgBe
#        else:
#            first_ring_dist = referenceQ
#        
#        if pixelcal:
#            p2q = [ first_ring_dist/pixelcal[0] , first_ring_dist/pixelcal[0] ]   # Pixel to q calulation
#            self.isCalibrated = True
#        else:
#            p2q = [1, 1]
#            self.isCalibrated = False
#
#        if scale == None:
#            self.q_raw = (self.q_raw * p2q[0])# * cos(theta))                 #Biosas:   / 1.2008
#        else:
#            self.q_raw = (self.q_raw * p2q[0])# * cos(theta) * scale)

        self.q_raw = q
        self.isCalibrated = True
        
        if solidangCorr != None:
            self.i_raw = self.i_raw * solidangCorr
            self.errorbars_raw = self.errorbars_raw * solidangCorr
            
         # Set Q_range to selected q_range after calibration:
        self.setQrange(self.q_range)       
    
    def calibrateManual(self, sampDetecDist, detectorPixelSize, wavelength):

        detectorPixelSizeInMM = detectorPixelSize / 1000
        ''' Calibrate using sample/detector distance and wavelength '''
        
        h = sqrt( pow(detectorPixelSizeInMM,2) / pow(sampDetecDist,2)  )
        
        sinT = detectorPixelSizeInMM / h
        
        self.q_raw = self.q_raw * (((detectorPixelSizeInMM / sampDetecDist) * 2 * pi) / wavelength)
        
    
    def unCalibrate(self):
        self.q_raw = linspace(0, len(self.i_raw), len(self.i_raw))
        self.calibrated = False
        
    def scale(self, scaleval):
            
        if scaleval != 1.0:
            
            if self.offsetval != 0.0:
                self.i = self.i_raw * float(scaleval) + self.offsetval
            else:
                self.i = self.i_raw * float(scaleval)
                
            self.errorbars = self.errorbars_raw * abs(float(scaleval))
            
            self.scaleval = float(scaleval)
    
            # Setting correct Qscale:
            q_min, q_max = self.q_range
            self.i = self.i[q_min:q_max]        # truncate I curve to q_min, q_max
            self.errorbars = self.errorbars_raw[q_min:q_max]
    
    def setQrange(self, q_range):
        ''' q_min and q_max are in PIXELS! '''
        
        if q_range:
            self.q_range = q_range
        
            q_min, q_max = self.q_range
            
            if q_max > len(self.q_raw):
                q_max = len(self.q_raw)
                self.q_range = (self.q_range[0], q_max)
                
            ## NB! Careful if the background has been subtracted! ..needs to be done
            self.i = self.i_raw[q_min:q_max] * self.scaleval + self.offsetval       # truncate I curve to q_min, q_max
            self.q = self.q_raw[q_min:q_max]                                        # linspace(q_min, q_max, len(self.i))       
            self.errorbars = self.errorbars_raw[q_min:q_max] * self.scaleval
            
        else:
            pass
    
    def getQrange(self):
        return self.q_range
    
    def resetQrange(self):
    
        self.i = self.i_raw
        self.q = self.q_raw
        self.q_range = (0, len(self.i)-1)
        
        self._updateAfterAdjustment()
    
    def reset(self):
        
        self.i = self.i_raw
        self.q = self.q_raw
        self.errorbars = self.errorbars_raw
        self.unCalibrate()
        self.isNormalized = False
        self.isCalibrated = False
    
    def _updateAfterAdjustment(self):
        
        if self.q_range:
            self.setQrange(self.q_range)
        
        if self.isCalibrated:
            self.calibrate(self.pixelcal)
            
class RadFileMeasurement(Measurement):
    
    def __init__(self, i, q, errorbars, param):
        
        Measurement.__init__(self, i, q, errorbars)

        self.param = param      #insert loaded parameters
        self.filetype = 'rad'   #
        self.isCalibrated = True
        self.type = 'rad'
        
    def normalizeM2(self):
        
        if self.param:
            fact = (self.param['before'] + self.param['after']) / 2
            self.i = self.i / fact
            self.isNormalized = True
            return True
        
        else:
            return False
        
    def normalizeByTransmission(self):
        
        try:
                M2fact = (self.param['before'] + self.param['after']) / 2
        except KeyError:
                raise Exception('Error normalizing, "before" and/or "after" measurement not found')
            
        try:
                M1fact = self.param['ic']
        except KeyError:
                raise Exception('Error normalizing, IC diode measurement not found')
            
        normFact = M2fact / M1fact
        
        infoPanel = wx.FindWindowByName('InfoPanel')
        infoPanel.WriteText(str(os.path.split(self.param['filename'])[1])+ ':\n')
        infoPanel.WriteText('Transmission: ' + str(normFact) + '\n')
        
        if normFact > 0.0001:
                self.i = self.i / normFact
                self.errorbars = self.errorbars / normFact
            
                self.isNormalized = True
            
                return normFact
        else:
                raise Exception('Error normalizing, transmission norm factor is below threshold (0.0001) or diode measurements are corrupt')
        
        
class BIFTMeasurement(Measurement):
    
    def __init__(self, i, q, errorbars, param, fit, allData):
        
        Measurement.__init__(self, i, q, errorbars)

        self.param = param      #insert loaded parameters
        self.filetype = 'rad'   #
        self.isCalibrated = True
        self.fit = fit
        self.allData = allData
        self.errorbars = errorbars
        self.type = 'bift'
    
        
##############################################################        
        
       

# **************************************************************************************************************
#                               MAIN TEST
# **************************************************************************************************************
    
if __name__ == "__main__":
    
    t, dir = createFilter(1086.18, 1164.85)
    t2 = zeros((2,2))
    
    print t
    t2 = t[where(t>0)]

    if len(t2) == 4:
        t2 = reshape(t2, (2,2))
         
    print shape(t2)
    print t2
    print dir
    
    in_image, dim = loadImage('AgBe')
    
    newImg = filterImage(t, in_image, dim)

    figure(1)
    in_image[where(in_image==0.0)] = 1
    imshow(log(in_image), interpolation = 'nearest')
    #show()

    title('Original')
    figure(2)
    newImg[where(newImg==0.0)] = 1
    imshow(log(newImg), interpolation = 'nearest')
    title('New')
   
    x_c, y_c = (1086.18,1164.85)
#    
    [iq, res, errorbars] = radialAverage(in_image, dim, x_c, y_c, mask = None, readoutNoise_mask = None)
    
    x_c, y_c = (1086.5,1164.5)
    
    [iq2, res2, errorbars2] = radialAverage(newImg, dim, x_c, y_c, mask = None, readoutNoise_mask = None)
#
    figure(3)
    plot(iq)
#    plot(iq2)
#    legend(('orig','filt'))
    figure(4)
    loglog(iq)
#    loglog(iq2)
#    legend(('orig','filt'))
#
    show()
    
#    x_c = 1165
#    y_c = 1089
#    
#    [iq, res, errorbars] = radialAverage(in_image, dim, x_c, y_c, mask = None, readoutNoise_mask = None)
#    
#    figure(1)
#    imshow(res)
#    
#    x_c2 = 1165.5
#    y_c2 = 1089.5
#    
#    [iq2, res2, errorbars2] = radialAverage(in_image, dim, x_c2, y_c2, mask = None, readoutNoise_mask = None)
#    
#    x_c3 = 1165.8
#    y_c3 = 1089.2
#    
#    [iq3, res3, errorbars3] = radialAverage(in_image, dim, x_c3, y_c3, mask = None, readoutNoise_mask = None)
#    
#    
#    figure(2)
#    plot(iq)
#    plot(iq2)
#    plot(iq3)
#    show() 
#    
    
    
    
    
#    
#    
#    
#    
#    SD_Distance = 1600
#    pixelSize = 78.886/1000
#    maxLength = 1024
#    
#    print getSolidAngleCorrection(SD_Distance, pixelSize, maxLength)
#    
#    #x_center = 467            # image center x
#    #y_center = 486            # image center y
#    #pixelcal = [167.3,167.3];
#    
#    #q_range = (25,450)              # q_range in pixels
#    #pixelcal = [200,200]            # The program currently only works for X-axis calibration and averaging
#
#    #mask = 'C:\\Documents and Settings\\user\\Desktop\\ssn\\Biosas2\\biosasmaskdb4.mat'
#    #rdmask = 'C:\\Documents and Settings\\user\\Desktop\\ssn\\Biosas2\\noisemaskdb4.mat'
#    Ep1 = fileIO.loadSoleilRadFile('NDX3_00016_bufT1NBC_00001_im_05_00.txt')
#    Ep2 = fileIO.loadSoleilRadFile('NDX3_00016_bufT1NBC_00001_im_06_00.txt')
#    Ep3 = fileIO.loadSoleilRadFile('NDX3_00016_bufT1NBC_00001_im_07_00.txt')
#    Ep4 = fileIO.loadSoleilRadFile('NDX3_00016_bufT1NBC_00001_im_08_00.txt')
#    Ep5 = fileIO.loadSoleilRadFile('NDX3_00016_bufT1NBC_00001_im_09_00.txt')
#
#
#    tst = [Ep1,Ep2,Ep3,Ep4,Ep5]
#    
#    tst2, err2 = removeOutliersAndAverage(tst)
#    
#    I_all = tst[0].i
#    for i in range(1,len(tst)):
#       I_all = vstack((I_all, tst[i].i))
#   
#    tst3 = mean(I_all,0)
#    
#    #Ep = loadM("13bsa_300sec", None, None, q_range, True, 556, 544)        # These give 886 points to the nearest edge
#    #Eb = loadM("14_buffer_300sec", None, None, q_range, True, 556, 544)        # These give 886 points to the nearest edge
#
#    #Ep = Ep[0]
#    #Eb = Eb[0]
#    #Ep.setBinning(2)
#    #Eb.setBinning(2)
#    #Eb.calibrate(pixelcal)
#    #Ep.calibrate(pixelcal)
#    
#    print "ok!"
#
#  #  Ep2 = loadM("x6gp1.tiff", mask, rdmask, q_range, True, 556, 544)        # These give 886 points to the nearest edge
#  #  Eb2 = loadM("x6gb1.tiff", mask, rdmask, q_range, True, 556, 544)
#
#  #  Ep2.setBinning(2)
#  #  Eb2.setBinning(2)
#  #  Eb2.calibrate(pixelcal)
#  #  Ep2.calibrate(pixelcal)
#    
#    # *******************************************
#    #  PLOT RESULTS
#    # *******************************************
#    #print Ep.i
#
#    figure(1)
#    plot(Ep1.i)
#    plot(Ep2.i)
#    plot(Ep3.i)
#    plot(Ep4.i)
#    plot(Ep5.i)
#    #plot(Eb.q, Eb.i)
#  #  plot(Eb2.q, Eb2.i)
#  #  plot(Ep2.q, Ep2.i)
#    
##    title('RAW IQ plot')
##    xlabel(r'$q ({nm}^{-1})$')
##    ylabel('Intensity (Pixel Counts)')
##    legend(('x6gp4','x6gb4','x6gp1','x6gb1'))
#    
#    figure(2)
#    plot(tst2)
#    plot(tst3)
##    loglog(Ep.i-Eb.i)
##    title('Background Subtracted Image')
##    ylabel('Intensity (Pixel Counts)')
#
##    print '---- x6gp4 -----'
##    print 'Backgrnd:'
##    print Eb.param['before']
##    print Eb.param['after']
##    print Eb.param['bsd']
##    print 'Protein:'
##    print Ep.param['before']
##    print Ep.param['after']
##    print Ep.param['bsd']
##    print ''
##    print '---- x6gp1 -----'
##    print 'Backgrnd:'
##    print Eb2.param['before']
##    print Eb2.param['after']
##    print Eb2.param['bsd']
##    print 'Protein:'
##    print Ep2.param['before']
##    print Ep2.param['after']
##    print Ep2.param['bsd']
            
