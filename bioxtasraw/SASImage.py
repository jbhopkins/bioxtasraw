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
import RAWGlobals
import polygonMasking as polymask

class Mask(object):
    ''' Mask super class. Masking is used for masking out unwanted regions
    of an image '''

    def __init__(self, mask_id, img_dim, mask_type, negative = False):

        self._is_negative_mask = negative
        self._img_dimension = img_dim            # need image Dimentions to get the correct fill points
        self._mask_id = mask_id
        self._type = mask_type
        self._points = None

    def setAsNegativeMask(self):
        self._is_negative_mask = True

    def setAsPositiveMask(self):
        self._is_negative_mask = False

    def isNegativeMask(self):
        return self._is_negative_mask

    def getPoints(self):
        return self._points

    def setPoints(self, points):
        self._points = points

    def setId(self, id):
        self._mask_id = id

    def getId(self):
        return self._mask_id

    def getType(self):
        return self._type

    def getFillPoints(self):
        pass    # overridden when inherited

    def getSaveFormat(self):
        pass   # overridden when inherited

class CircleMask(Mask):
    ''' Create a circular mask '''

    def __init__(self, center_point, radius_point, id, img_dim, negative = False):

        Mask.__init__(self, id, img_dim, 'circle', negative)

        self.setPoints([center_point, radius_point])

    def getRadius(self):
        return self._radius

    def grow(self, pixels):
        ''' Grow the circle by extending the radius by a number
        of pixels '''

        xy_c, xy_r = self._points

        x_c, y_c = xy_c
        x_r, y_r = xy_r

        if x_r > x_c:
            x_r = x_r + pixels
        else:
            x_r = x_r - pixels

        self.setPoints([(x_c,y_c), (x_r,y_r)])

    def shrink(self, pixels):
        ''' Shrink the circle by shortening the radius by a number
        of pixels '''

        xy_c, xy_r = self._points

        x_c, y_c = xy_c
        x_r, y_r = xy_r

        if x_r > x_c:
            x_r = x_r - pixels
        else:
            x_r = x_r + pixels

        self.setPoints([(x_c,y_c), (x_r,y_r)])

    def setPoints(self, points):
        self._points = points
        self._radius = abs(points[1][0] - points[0][0])

        self._calcFillPoints()

    def _calcFillPoints(self):

        radiusC = abs(self._points[1][0] - self._points[0][0])

        P = calcBresenhamCirclePoints(radiusC, self._points[0][1], self._points[0][0])
        self.coords = []

        for i in range(0, len(P)//8):
            Pp = P[i*8 : i*8 + 8]

            q_ud1 = ( Pp[0][0], list(range(int(Pp[1][1]), int(Pp[0][1]+1))) )
            q_ud2 = ( Pp[2][0], list(range(int(Pp[3][1]), int(Pp[2][1]+1))) )

            q_lr1 = ( Pp[4][1], list(range(int(Pp[6][0]), int(Pp[4][0]+1))) )
            q_lr2 = ( Pp[5][1], list(range(int(Pp[7][0]), int(Pp[5][0]+1))) )

            for i in range(0, len(q_ud1[1])):
                self.coords.append( (int(q_ud1[0]), int(q_ud1[1][i])) )
                self.coords.append( (int(q_ud2[0]), int(q_ud2[1][i])) )
                self.coords.append( (int(q_lr1[1][i]), int(q_lr1[0])) )
                self.coords.append( (int(q_lr2[1][i]), int(q_lr2[0])) )

    def getFillPoints(self):
        ''' Really Clumsy! Can be optimized alot! triplicates the points in the middle!'''

        return self.coords

    def getSaveFormat(self):
        save = {'type'          :   self._type,
                'center_point'  :   self._points[0],
                'radius_point'  :   self._points[1],
                'negative'      :   self._is_negative_mask,
                }
        return save

class RectangleMask(Mask):
    ''' create a retangular mask '''

    def __init__(self, first_point, second_point, id, img_dim, negative = False):

        Mask.__init__(self, id, img_dim, 'rectangle', negative)
        self._points = [first_point, second_point]
        self._calcFillPoints()

    def grow(self, pixels):

        xy1, xy2 = self._points

        x1, y1 = xy1
        x2, y2 = xy2

        if x1 > x2:
            x1 = x1 + pixels
            x2 = x2 - pixels
        else:
            x1 = x1 - pixels
            x2 = x2 + pixels

        if y1 > y2:
            y1 = y1 - pixels
            y2 = y2 + pixels
        else:
            y1 = y1 + pixels
            y2 = y2 - pixels

        self._points = [(x1,y1), (x2,y2)]

        self._calcFillPoints()

    def shrink(self):
        ''' NOT IMPLEMENTED YET '''
        pass

    def _calcFillPoints(self):
        startPoint, endPoint = self._points
        '''  startPoint and endPoint: [(x1,y1) , (x2,y2)]  '''

        startPointX = int(startPoint[1])
        startPointY = int(startPoint[0])

        endPointX = int(endPoint[1])
        endPointY = int(endPoint[0])

        self.coords = []

        if startPointX > endPointX:

            if startPointY > endPointY:

                for c in range(endPointY, startPointY + 1):
                    for i in range(endPointX, startPointX + 1):
                        self.coords.append( (int(i), int(c)) )
            else:
                for c in range(startPointY, endPointY + 1):
                    for i in range(endPointX, startPointX + 1):
                        self.coords.append( (int(i), int(c)) )

        else:

            if startPointY > endPointY:

                for c in range(endPointY, startPointY + 1):
                    for i in range(startPointX, endPointX + 1):
                        self.coords.append( (int(i),int(c)) )
            else:
                for c in range(startPointY, endPointY + 1):
                    for i in range(startPointX, endPointX + 1):
                        self.coords.append( (int(i), int(c)) )

    def getFillPoints(self):

        return self.coords

    def getSaveFormat(self):
        save = {'type'          :   self._type,
                'first_point'   :   self._points[0],
                'second_point'  :   self._points[1],
                'negative'      :   self._is_negative_mask,
                }
        return save

class PolygonMask(Mask):
    ''' create a polygon mask '''

    def __init__(self, points, id, img_dim, negative = False):

        Mask.__init__(self, id, img_dim, 'polygon', negative)

        self._points = points

        self._calcFillPoints()

    def _calcFillPoints(self):
        proper_formatted_points = []
        yDim, xDim = self._img_dimension

        for each in self._points:
            proper_formatted_points.append(list(each))

        proper_formatted_points = np.array(proper_formatted_points)

        pb = polymask.Polygeom(proper_formatted_points)

        grid = np.mgrid[0:xDim,0:yDim].reshape(2,-1).swapaxes(0,1)

        inside = pb.inside(grid)

        p = np.where(inside==True)

        self.coords = polymask.getCoords(p, (int(yDim), int(xDim)))

    def getFillPoints(self):

        return self.coords

    def getSaveFormat(self):
        save = {'type'      :   self._type,
                'vertices'  :   self._points,
                'negative'  :   self._is_negative_mask,
                }
        return save


class _oldMask(object):
    """
    Exists for backwards compatibility for loading old style pickled settings
    with old style object masks.
    """
    pass


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


def calibrateAndNormalize(sasm_list, img_list, raw_settings):
    # Calibrate Q
    sd_distance = raw_settings.get('SampleDistance')
    pixel_size = raw_settings.get('DetectorPixelSize')
    wavelength = raw_settings.get('WaveLength')
    bin_size = raw_settings.get('Binsize')
    calibrate_check = raw_settings.get('CalibrateMan')
    enable_normalization = raw_settings.get('EnableNormalization')
    x_center = raw_settings.get('Xcenter')
    y_center = raw_settings.get('Ycenter')

    pixel_size = pixel_size/1000.

    if not isinstance(sasm_list, list):
        sasm_list = [sasm_list]
        img_list = [img_list]

    for i in range(len(sasm_list)):
        sasm = sasm_list[i]
        img = img_list[i]

        if raw_settings.get('UseHeaderForCalib'):
            img_hdr = sasm.getParameter('imageHeader')
            file_hdr = sasm.getParameter('counters')

            result = getBindListDataFromHeader(raw_settings, img_hdr, file_hdr, keys = ['Sample Detector Distance', 'Detector Pixel Size', 'Wavelength', 'Beam X Center', 'Beam Y Center'])
            if result[0] is not None: sd_distance = result[0]
            if result[1] is not None: pixel_size = result[1]
            if result[2] is not None: wavelength = result[2]
            if result[3] is not None: x_center = result[3]
            if result[4] is not None: y_center = result[4]

        if raw_settings.get('DoSolidAngleCorrection'):
            sc = SASCalib.calcSolidAngleCorrection(sasm, sd_distance, pixel_size)

            sasm.scaleRawIntensity(1.0/sc)

        sasm.setBinning(bin_size)

        if calibrate_check:
            sasm.calibrateQ(sd_distance, pixel_size, wavelength)

        calibrate_dict = {'Sample_Detector_Distance'    : sd_distance,
                        'Detector_Pixel_Size'           : pixel_size,
                        'Wavelength'                    : wavelength,
                        'Beam_Center_X'                 : x_center,
                        'Beam_Center_Y'                 : y_center,
                        'Radial_Average_Method'         : 'RAW',
                        }

        sasm.setParameter('calibration_params', calibrate_dict)
        sasm.setParameter('raw_version', RAWGlobals.version)

        normlist = raw_settings.get('NormalizationList')
        img_hdr = sasm.getParameter('imageHeader')
        file_hdr = sasm.getParameter('counters')

        if raw_settings.get('DoSolidAngleCorrection'):
            sasm.setParameter('normalizations', {'Solid_Angle_Correction': 'On'})
        else:
            sasm.setParameter('normalizations', {})

        if normlist is not None and enable_normalization == True:
            norm_dict = sasm.getParameter('normalizations')
            norm_dict['Counter_norms'] = normlist
            sasm.setParameter('normalizations', norm_dict)

            for each in normlist:
                op, expr = each

                #try:
                val = calcExpression(expr, img_hdr, file_hdr)

                if val is not None:
                    val = float(val)
                else:
                    raise ValueError
                #except:
                #    msg = 'calcExpression error'
                #    raise SASExceptions.NormalizationError('Error normalizing in calibrateAndNormalize: ' + str(msg))

                if op == '/':

                   # if val == 0:
                   #     raise ValueError('Divide by Zero when normalizing')

                    if val != 0:
                        sasm.scaleBinnedIntensity(1./val)
                    else:
                        print('WARNING: Divide by zero when normalizing, normalization value ignore!')

                elif op == '+':
                    sasm.offsetBinnedIntensity(val)
                elif op == '*':

                    # if val == 0:
                    #    raise ValueError('Multiply by Zero when normalizing')
                    if val != 0:
                        sasm.scaleBinnedIntensity(val)
                        print('WARNING: Multiply by zero when normalizing, normalization value ignored!')

                elif op == '-':
                    sasm.offsetBinnedIntensity(-val)

    return sasm_list


def calcBresenhamLinePoints(x0, y0, x1, y1):

    pointList = []
    pointXList = []
    pointYList = []

    Dx = x1 - x0;
    Dy = y1 - y0;

    #Steep
    steep = abs(Dy) > abs(Dx)
    if steep:
        x0, y0 = y0, x0
        x1, y1 = y1, x1

        Dx = x1 - x0
        Dy = y1 - y0

    if Dx < 0:
        Dx = -Dx

        x_range = list(range(x1, x0+1))
        x_range.reverse()
    else:
        x_range = list(range(x0,x1+1))

    ystep = 1

    if Dy < 0:
       ystep = -1
       Dy = -Dy

    TwoDy = 2*Dy
    TwoDyTwoDx = TwoDy - 2*Dx        # 2*Dy - 2*Dx
    E = TwoDy - Dx                   # //2*Dy - Dx
    y = y0

    for x in x_range:     #int x = x0; x != x1; x += xstep)

       if steep:
           xDraw = y
           yDraw = x
       else:
           xDraw = x
           yDraw = y

       #plot(xDraw, yDraw)
       pointList.append((xDraw,yDraw))
       pointXList.append(xDraw)
       pointYList.append(yDraw)

       if E > 0:
           E = E + TwoDyTwoDx             #//E += 2*Dy - 2*Dx;
           y = y + ystep
       else:
           E = E + TwoDy                 #//E += 2*Dy;

    return pointList, pointXList, pointYList

def calcBresenhamCirclePoints(radius, xOffset = 0, yOffset = 0):
    ''' Uses the Bresenham circle algorithm for determining the points
     of a circle with a certain radius '''

    x = 0
    y = radius

    switch = 3 - (2 * radius)
    points = []
    while x <= y:
        points.extend([(x + xOffset, y + yOffset),(x + xOffset,-y + yOffset),
                       (-x + xOffset, y + yOffset),(-x + xOffset,-y + yOffset),
                       (y + xOffset, x + yOffset),(y + xOffset,-x + yOffset),
                       (-y + xOffset, x + yOffset),(-y + xOffset, -x + yOffset)])
        if switch < 0:
            switch = switch + (4 * x) + 6
        else:
            switch = switch + (4 * (x - y)) + 10
            y = y - 1
        x = x + 1

    return points

def createMaskMatrix(img_dim, masks):
    ''' creates a 2D binary matrix of the same size as the image,
    corresponding to the mask pattern '''

    negmasks = []
    posmasks = []
    neg = False

    for each in masks:
        if each.isNegativeMask() == True:
            neg = True
            negmasks.append(each)
        else:
            posmasks.append(each)

    if neg:
        for each in posmasks:
            negmasks.append(each)

            masks = negmasks
        mask = np.zeros(img_dim)
    else:
        mask = np.ones(img_dim)

    maxy = mask.shape[1]
    maxx = mask.shape[0]

    for each in masks:
        fillPoints = each.getFillPoints()

        if each.isNegativeMask() == True:
            for eachp in fillPoints:
                if eachp[0] < maxx and eachp[0] >= 0 and eachp[1] < maxy and eachp[1] >= 0:
                    y = int(eachp[1])
                    x = int(eachp[0])
                    mask[(x,y)] = 1
        else:
            for eachp in fillPoints:
                if eachp[0] < maxx and eachp[0] >= 0 and eachp[1] < maxy and eachp[1] >= 0:
                    y = int(eachp[1])
                    x = int(eachp[0])
                    mask[(x,y)] = 0

    #Mask is flipped (older RAW versions had flipped image)
    mask = np.flipud(mask)

    return mask

def createMaskFromHdr(img, img_hdr, flipped = False):

    try:
        bsmask_info = img_hdr['bsmask_configuration'].split()
        detector_type = img_hdr['detectortype']

        bstop_size = float(bsmask_info[3])/2.0
        arm_width = float(bsmask_info[5])

        if flipped:
            beam_x = float(bsmask_info[1])+1
            beam_y = float(bsmask_info[2])+1
            angle = (2.*np.pi/360.) * (float(bsmask_info[4])+90)
        else:
            beam_x = float(bsmask_info[2])+1
            beam_y = float(bsmask_info[1])+1
            angle = (2.*np.pi/360.) * (float(bsmask_info[4]))

        masks = []
        masks.append(CircleMask((beam_x, beam_y), (beam_x + bstop_size, beam_y + bstop_size), 0, img.shape, False))

        if detector_type == 'PILATUS 300K':
            points = [(191,489), (214,488), (214,0), (192,0)]
            masks.append(PolygonMask(points, 1, img.shape, False))
            points = [(404,489), (426,489), (426,0), (405,0)]
            masks.append(PolygonMask(points, 1, img.shape, False))

        #Making mask as long as the image diagonal (cannot be longer)
        L = np.sqrt( img.shape[0]**2 + img.shape[1]**2 )

        #width of arm mask
        N = arm_width

        x1, y1 = beam_x, beam_y

        x2 = x1 + (L * np.cos(angle))
        y2 = y1 + (L * np.sin(angle))

        dx = x1-x2
        dy = y1-y2
        dist = np.sqrt(dx*dx + dy*dy)
        dx /= dist
        dy /= dist
        x3 = int(x1 + (N/2.)*dy)
        y3 = int(y1 - (N/2.)*dx)
        x4 = int(x1 - (N/2.)*dy)
        y4 = int(y1 + (N/2.)*dx)

        x5 = int(x2 + (N/2.)*dy)
        y5 = int(y2 - (N/2.)*dx)
        x6 = int(x2 - (N/2.)*dy)
        y6 = int(y2 + (N/2.)*dx)

        points = [(x3, y3), (x4, y4), (x6, y6), (x5, y5)]

        masks.append(PolygonMask(points, 2, img.shape, False))

    except ValueError:
        raise ValueError

    return masks

def applyMaskToImage(in_image, mask):
    ''' multiplies the mask matrix to a 2D array (image) to reveal
    the an image where the mask has been applied. '''
    pass


def doFlatfieldCorrection(img, img_hdr, flatfield_img, flatfield_hdr):
    if isinstance(flatfield_img, list):
        flatfield_img = np.average(flatfield_img, axis=0)

    cor_img = img / flatfield_img   #flat field is often water.

    return cor_img

def doDarkBackgroundCorrection(img, img_hdr, dark_img, dark_hdr):
    pass

def removeZingers(intensityArray, startIdx = 0, averagingWindowLength = 10, stds = 4):
    ''' Removes spikes from the radial averaged data
        Threshold is currently 4 times the standard deviation

        averagingWindowLength :     The number of points before the spike
                                    that are averaged and used to replace the spike.

        startIdx :                  Index in intensityArray to start the search for spikes

    '''

    for i in range(averagingWindowLength + startIdx, len(intensityArray)):

        averagingWindow = intensityArray[i - averagingWindowLength : i - 1]

        stdOfAveragingWindow = np.std(averagingWindow)
        meanOfAvergingWindow = np.mean(averagingWindow)

        threshold = meanOfAvergingWindow + (stds * stdOfAveragingWindow)

        if intensityArray[i] > threshold:
            intensityArray[i] = meanOfAvergingWindow

    return intensityArray

def removeZingers2(intensity_array, start_idx = 0, window_length = 10, sensitivity = 4):
    ''' Removes spikes from the radial averaged data
        Threshold is currently 4 times the standard deviation

        averagingWindowLength :     The number of points before the spike
                                    that are averaged and used to replace the spike.

        startIdx :                  Index in intensityArray to start the search for spikes

    '''

    half_window = int(np.ceil(window_length/2.))

    for i in range(0, len(intensity_array)):


        if i >= (half_window + start_idx) and i < (len(intensity_array)-half_window):
            window = intensity_array[i - half_window  : i + half_window]
        elif i >= (len(intensity_array)-half_window):
            window = intensity_array[i - window_length  : i]

        if i >= half_window + start_idx:
            stdwin = np.sort(window)
            std = np.std(stdwin[:-half_window])
            median = np.median(window)

            plus_threshold = median + (std * sensitivity)
            minus_threshold = median - (std * sensitivity)

            if intensity_array[i] > plus_threshold or intensity_array[i] < minus_threshold:
                intensity_array[i] = median

    return intensity_array

def getIntensityFromQmatrix(qmatrix):

    qmatrix = np.flipud(qmatrix)
    qmatrix = np.flipud(np.rot90(qmatrix,3))

    #I = np.zeros(qmatrix.shape[1])
    I2 = np.zeros(qmatrix.shape[1])
    err = np.zeros(qmatrix.shape[1])

    for i in range(0, qmatrix.shape[1]):
        y = qmatrix[np.where(qmatrix[:,i]!=0),i][0]
        #y2 = SASImage.removeZingers2(copy.copy(y), 0, 20, 4)
        #I[i] = np.mean(y2)
        I2[i] = np.mean(y)
        err[i] = np.std(y) / np.sqrt(len(y))

    return I2, err

def radialAverage(in_image, x_cin, y_cin, mask = None, readoutNoise_mask = None, dezingering = 0, dezing_sensitivity = 4.0):
    ''' Radial averaging. and calculation of readout noise from a readout noise mask.
        It also returns the errorbars assuming possion distributed data

        in_image :     Input image
        dim:           Image dimentions
        x_c, y_c :     (x_c, y_c) Center coordinate in the image (Pixels)
        q_range :      q_range specifying [low_q high_q]

    '''

    in_image = np.float64(in_image)

    ylen, xlen = in_image.shape

    xlen = np.int(xlen)
    ylen = np.int(ylen)

    # If no mask is given, the mask is pure ones
    if mask is None:
        mask = np.ones(in_image.shape)

    if readoutNoise_mask is None:
        readoutNoiseFound = 0
        readoutNoise_mask = np.zeros(in_image.shape, dtype = np.float64)
    else:
        readoutNoiseFound = 1

    readoutN = np.zeros((1,4), dtype = np.float64)

    # Find the maximum distance to the edge in the image:
    maxlen1 = int(max(xlen - x_cin, ylen - y_cin, xlen - (xlen - x_cin), ylen - (ylen - y_cin)))

    diag1 = int(np.sqrt((xlen-x_cin)**2 + y_cin**2))
    diag2 = int(np.sqrt((x_cin**2 + y_cin**2)))
    diag3 = int(np.sqrt((x_cin**2 + (ylen-y_cin)**2)))
    diag4 = int(np.sqrt((xlen-x_cin)**2 + (ylen-y_cin)**2))

    maxlen = int(max(diag1, diag2, diag3, diag4, maxlen1))

    #print(diag1, diag2, diag3, diag4, maxlen1)

    # we set the "q_limits" (in pixels) so that it does radial avg on entire image (maximum qrange possible).
    q_range = (0, maxlen)

    ##############################################
    # Reserving memory for radial averaged output:
    ##############################################
    hist = np.zeros(q_range[1], dtype = np.float64)
    hist_count = np.zeros((3,q_range[1]), dtype = np.float64)  # -----" --------- for number of pixels in a circle at a certain q

    qmatrix = np.zeros((q_range[1], 4*xlen), dtype = np.float64)

    low_q = q_range[0]
    high_q = q_range[1]

    # This code is faulty.. x has been switched with y
    x_c = float(y_cin)
    y_c = float(x_cin)

    xlen_1 = ylen
    ylen_1 = xlen

    print('Radial averaging in progress...', end='')

    ravg(readoutNoiseFound, readoutN, readoutNoise_mask, xlen_1, ylen_1, x_c, y_c,
        hist, low_q, high_q, in_image, hist_count, mask, qmatrix, dezingering,
        dezing_sensitivity)

    print("Done!")

    hist_cnt = hist_count[2,:]    #contains x-mean

    hist_count = hist_count[0,:]  #contains N

    std_i = np.sqrt(hist_cnt/hist_count)

    std_i[np.where(np.isnan(std_i))] = 0

    iq = hist / hist_count

    if x_c > 0 and x_c < xlen and y_c > 0 and y_c < ylen and mask[int(round(x_c)), int(round(y_c))] !=0:
        iq[0] = in_image[int(round(x_c)), int(round(y_c))]  #the center is not included in the radial average, so it is set manually here


    #Estimated Standard deviation   - equal to the std of pixels in the area / sqrt(N)
    errorbars = std_i / np.sqrt(hist_count)
    errorbars[np.where(hist_count==1)] = np.sqrt(iq[np.where(hist_count==1)]) #Edge case for 1 pixel in the bin


    if readoutNoiseFound:
        #Average readoutNoise
        readoutNoise = readoutN[0,1] /  readoutN[0,0]   ## sum(img(x,y)) / N
        print('Readout Noise: ', readoutNoise)

        #Estimated Standard deviation   - equal to the std of pixels in the area / sqrt(N)
        std_n = np.sqrt(readoutN[0,3] / readoutN[0,0])    # sqrt((X-MEAN)/N)
        errorbarNoise = std_n / np.sqrt(readoutN[0,0])

        print('Readout Noise Err: ', errorbarNoise)

        #Readoutnoise average subtraction
        iq = iq - readoutNoise
        errorbars = np.sqrt(np.power(errorbars, 2) + np.power(errorbarNoise, 2))


    iq[np.where(np.isnan(iq))] = 0
    errorbars[np.where(np.isnan(errorbars))] = 1e-10

    q = np.linspace(0, len(iq)-1, len(iq))

    if dezingering == 1:
        iq, errorbars = getIntensityFromQmatrix(qmatrix)
        iq[np.where(np.isnan(iq))] = 0
        errorbars[np.where(np.isnan(errorbars))] = 1e-10

    #Trim trailing zeros
    # iq = np.trim_zeros(iq, 'b')
    iq = iq[:-5]        #Last points are usually garbage they're very few pixels
                        #Cutting the last 5 points here.
    q = q[0:len(iq)]
    errorbars = errorbars[0:len(iq)]

    return [iq, q, errorbars, qmatrix]


def pyFAIIntegrateCalibrateNormalize(img, parameters, x_cin, y_cin, raw_settings, mask = None, tbs_mask = None):
    print('using pyfai!!!!')
    # Get appropriate settings
    sd_distance = raw_settings.get('SampleDistance')
    pixel_size = raw_settings.get('DetectorPixelSize')
    wavelength = raw_settings.get('WaveLength')
    bin_size = raw_settings.get('Binsize')
    normlist = raw_settings.get('NormalizationList')

    do_calibration = raw_settings.get('CalibrateMan')
    do_normalization = raw_settings.get('EnableNormalization')
    do_flatfield = raw_settings.get('NormFlatfieldEnabled')
    do_solidangle = raw_settings.get('DoSolidAngleCorrection')
    do_useheaderforcalib = raw_settings.get('UseHeaderForCalib')

    #Put everything in appropriate units
    pixel_size = pixel_size *1e-6 #convert pixel size to m
    wavelength = wavelength*1e-10 #convert wl to m

    if do_useheaderforcalib:
        img_hdr = parameters['imageHeader']
        file_hdr = parameters['counters']

        result = getBindListDataFromHeader(raw_settings, img_hdr, file_hdr, keys = ['Sample Detector Distance', 'Detector Pixel Size', 'Wavelength'])
        if result[0] is not None: sd_distance = result[0]
        if result[1] is not None: pixel_size = result[1]
        if result[2] is not None: wavelength = result[2]

    #Set up mask
    img = np.float64(img)

    ylen, xlen = img.shape

    xlen = int(xlen)
    ylen = int(ylen)

    # If no mask is given, the mask is pure zeroes
    if mask is None:
        mask = np.zeroes(img.shape)

    else:
        mask = np.logical_not(mask)

    # if readoutNoise_mask is None:
    #     readoutNoiseFound = 0
    #     readoutNoise_mask = np.zeros(img.shape, dtype = np.float64)
    # else:
    #     readoutNoiseFound = 1

    # readoutN = np.zeros((1,4), dtype = np.float64)

    # Find the maximum distance to the edge in the image:
    maxlen1 = int(max(xlen - x_cin, ylen - y_cin, xlen - (xlen - x_cin), ylen - (ylen - y_cin)))

    diag1 = int(np.sqrt((xlen-x_cin)**2 + y_cin**2))
    diag2 = int(np.sqrt((x_cin**2 + y_cin**2)))
    diag3 = int(np.sqrt((x_cin**2 + (ylen-y_cin)**2)))
    diag4 = int(np.sqrt((xlen-x_cin)**2 + (ylen-y_cin)**2))

    maxlen = int(max(diag1, diag2, diag3, diag4, maxlen1))

    x_c = float(x_cin)
    y_c = float(y_cin)

    ai = pyFAI.AzimuthalIntegrator()

    if do_calibration:
        ai.wavelength = wavelength
        ai.pixel1 = pixel_size
        ai.pixel2 = pixel_size
        ai.setFit2D(sd_distance, x_c, y_c)

    if do_flatfield:
        flatfield_filename = raw_settings.get('NormFlatfieldFile')
        ai.set_flatfiles(flatfield_filename)

    print(ai)
    qmin_theta = SASCalib.calcTheta(sd_distance*1e-3, pixel_size, 0)
    qmin = ((4 * math.pi * math.sin(qmin_theta)) / (wavelength*1e10))

    qmax_theta = SASCalib.calcTheta(sd_distance*1e-3, pixel_size, maxlen)
    qmax = ((4 * math.pi * math.sin(qmax_theta)) / (wavelength*1e10))

    q_range = (qmin, qmax)

    #Carry out the integration
    q, iq, errorbars = ai.integrate1d(img, maxlen, mask = mask, correctSolidAngle = do_solidangle, error_model = 'poisson', unit = 'q_A^-1', radial_range = q_range, method = 'nosplit_csr')

    i_raw = iq[:-5]        #Last points are usually garbage they're very few pixels
                        #Cutting the last 5 points here.
    q_raw = q[0:len(i_raw)]
    errorbars = errorbars[0:len(i_raw)]

    err_raw_non_nan = np.nan_to_num(errorbars)

    if tbs_mask is not None:
        roi_counter = img[tbs_mask==1].sum()
        parameters['counters']['roi_counter'] = roi_counter

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

    sasm = SASM.SASM(i_raw, q_raw, err_raw_non_nan, parameters)

    img_hdr = sasm.getParameter('imageHeader')
    file_hdr = sasm.getParameter('counters')

    if normlist is not None and do_normalization == True:
        norm_dict = sasm.getParameter('normalizations')
        norm_dict['Counter_norms'] = normlist
        sasm.setParameter('normalizations', norm_dict)

        for each in normlist:
            op, expr = each

            #try:
            val = calcExpression(expr, img_hdr, file_hdr)

            if val is not None:
                val = float(val)
            else:
                raise ValueError
            #except:
            #    msg = 'calcExpression error'
            #    raise SASExceptions.NormalizationError('Error normalizing in calibrateAndNormalize: ' + str(msg))

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


@jit(nopython=True, cache=True, parallel=False)
def ravg(readoutNoiseFound, readoutN, readoutNoise_mask, xlen, ylen, x_c,
                y_c, hist, low_q, high_q, in_image, hist_count, mask, qmatrix,
                dezingering, dezing_sensitivity):

    WINDOW_LENGTH=30

    window = np.empty(WINDOW_LENGTH)

    hist_length = len(hist)

    half_window_size = int(WINDOW_LENGTH / 2.0)
    win_len = WINDOW_LENGTH

    for x in prange(xlen):
        for y in prange(ylen):
            rel_x = x-x_c
            rel_y = y_c-y

            r = int(((rel_y)**2. + (rel_x)**2.)**0.5)

            if r < high_q and r > low_q and mask[x,y] == 1:
                q_idx = r

                hist[r] = hist[r] + in_image[x,y]                    #/* Integration of pixel values */

                qmat_cnt = hist_count[0, q_idx]                      #/* Number of pixels in a bin */
                qmatrix[q_idx, int(qmat_cnt)] = in_image[x,y]        #/* Save pixel value for later analysis */

                hist_count[0, q_idx] = hist_count[0, q_idx] + 1      #/* Number of pixels in a bin */

                delta = in_image[x,y] - hist_count[1, q_idx]         #/* Calculation of variance start */

                hist_count[1, q_idx] = hist_count[1, q_idx] + (delta / hist_count[0, q_idx])
                hist_count[2, q_idx] = hist_count[2, q_idx] + (delta * (in_image[x,y]-hist_count[1, q_idx]))


                # /* *******************   Dezingering   ******************** */

                if hist_count[0, r] >= WINDOW_LENGTH and dezingering == 1:
                # {
                    point_idx = int(hist_count[0, q_idx])
                    window_start_idx = point_idx - win_len

                    window = qmatrix[q_idx, window_start_idx:point_idx]

                    std = np.std(window)
                    median = np.median(window)

                    half_win_len = point_idx - half_window_size


                    if qmatrix[q_idx, half_win_len] > (median + (dezing_sensitivity * std)): #{
                        qmatrix[q_idx, half_win_len] = median

            if readoutNoiseFound == 1 and r < high_q-1 and r > low_q and readoutNoise_mask[x,y] == 0:
                readoutN[0,0] = readoutN[0,0] + 1
                readoutN[0,1] = readoutN[0,1] + in_image[x,y]

                deltaN = in_image[x,y] - readoutN[0,2]
                readoutN[0,2] = readoutN[0,2] + (deltaN / readoutN[0,0]) #Running average
                readoutN[0,3] = readoutN[0,3] + (deltaN * (in_image[x,y]-readoutN[0,2]))

    # /* *********************************************  */
    # /* Remove zingers at the first (window/2) points  */
    # /* *********************************************  */

    if dezingering == 1:
        half_window_size = int(WINDOW_LENGTH / 2.0)
        win_len = WINDOW_LENGTH

        for q_idx in prange(hist_length):
            if hist_count[0, q_idx] > (win_len + half_window_size):
                for i in range(win_len+half_window_size, win_len, -1):
                    point_idx = i
                    window_start_idx = point_idx - win_len

                    window = qmatrix[q_idx, window_start_idx:point_idx]

                    std = np.std(window)
                    median = np.median(window)

                    half_win_len = point_idx - win_len

                    if qmatrix[q_idx, half_win_len] > (median + (dezing_sensitivity * std)):
                        qmatrix[q_idx, half_win_len] = median
