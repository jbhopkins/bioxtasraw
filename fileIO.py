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

from __future__ import division

from pylab import *
import re, wx
import time
import Image
import TiffImagePlugin            # Is needed for py2exe!
from os import path
from numpy import *
from scipy import weave
from scipy import io
from scipy.weave import converters
import MARCCD_headerReader 
import cartToPol


def loadImage(filename):
    ''' Load TIFF image '''
    
    im = Image.open(filename)
    newArr = fromstring(im.tostring(), uint16)
    newArr = reshape(newArr, im.size) 
    dim = shape(newArr)
    
    return newArr, dim

#Default:

#---- ##### MarCCD 165 Images #####
def loadMarccd165File(filename, expParams):
    
    print "Loading an image..."
            
    if expParams != None:
        mask, rdmask, q_range, pixelcal, x_center, y_center, binsize = _getExperimentParameters(expParams)

    hdr = readHeader(filename, fileformat = 'marccd165')
    img, dim = loadImage(filename)
                
    ExpObj, FullImage = cartToPol.loadM(img, dim, mask, rdmask, q_range, hdr, x_center, y_center, pixelcal = None, binsize = binsize)
    ExpObj.param['filename'] = filename
    
    return ExpObj, FullImage
    
#def loadImage(filename):
#    ''' Load MARCCD Image and read header information '''
#    
#    im = Image.open(filename)
#    hdr = readHeader(filename)    # from MARCCD_headerReader
#
#    newArr = fromstring(im.tostring(), int16)
#    newArr = reshape(newArr, im.size) 
#    
#    return newArr, hdr

#---- ##### Quantum210 Images ##### 

def loadQuantum210Image(filename):
    
    f = open(filename, 'rb')
    
    f.seek(512) # Jump over header

    Img = fromfile(f, dtype=np.uint16)
    
    #Img = io.fread(f, 16777216, 'H', 'H', 0)
    
    f.close()
    
    xydim = int(sqrt(shape(Img))[0])  #assuming square image
    
    Img = Img.reshape((xydim,xydim))
    
    SubImg = getSecondQuadrant(Img)

    dim = shape(SubImg)

    return SubImg, dim

#def normalizeQuadrants(img):
        
                           #Y, X
#    firstQuad = avg(Img[60:80, 3040])
    
#    secondQuad = avg(img[60:80, 3070])
    
#    thirdQuad = avg(Img[])
#    fourthQuad = avg(Img[])
    
    


def getSecondQuadrant(Img):
    
    return Img[0:2048,2048:4096]

def parseQuantumFileHeader(filename):
       
    param_pattern = re.compile('[a-zA-Z0-9_]*[=].*\n')
    
    f = open(filename)
    hdr = {}
    
    lineNum = 0
    
    try:
        for line in f:
                        
            match_found = param_pattern.match(line)
            
            if match_found:                
                found = match_found.group().split('=')                
                hdr[found[0]] = found[1].strip(';\n')
            
            lineNum = lineNum + 1
            
            if lineNum > 30: #header ends after line 27.. but just making sure
                break
            
        f.close()
    except:
        print 'Reading Quantum210 header failed'
        
    
    return hdr

def parseCTSfile(filename):
    
    timeMonitorPattern = re.compile('\d*-second\s[a-z]*\s[()A-Z,]*\s\d*\s\d*')
    closedShutterCountPattern = re.compile('closed\s\d*')
    
    try:
        f = open(filename[:-3] + 'cts')
    except:
        #wx.CallAfter(wx.MessageBox, filename[:-3] + 'cts' + ' not found.\n\nNormalization by diodes will not be possible', 'Header file not found!', wx.OK | wx.ICON_ERROR)
        return None, None, None, None
        
    mon1, mon2, exposureTime, closedShutterCount = None, None, None, None
    
    for line in f:
        timeMonitor_match = timeMonitorPattern.search(line)
        closedShutterCount_match = closedShutterCountPattern.search(line)
            
        if timeMonitor_match:           
            exposureTime = int(timeMonitor_match.group().split('-')[0])
            mon1 = int(timeMonitor_match.group().split(' ')[3])
            mon2 = int(timeMonitor_match.group().split(' ')[4])
                 
        if closedShutterCount_match:
            closedShutterCount = int(closedShutterCount_match.group().split(' ')[1])
            
    f.close()
    
    return closedShutterCount, mon1, mon2, exposureTime
    
def loadQuantum210File(filename, expParams):
    
    if expParams != None:
        mask, rdmask, q_range, pixelcal, x_center, y_center, binsize = _getExperimentParameters(expParams)
    
    img, dim = loadQuantum210Image(filename)
    
    hdr = readHeader(filename, fileformat = 'quantum210')
    
    closedShutterCount, mon1, mon2, exposureTime = parseCTSfile(filename) 
    
    print closedShutterCount, mon1, mon2, exposureTime
    
    print dim
    
    ExpObj, FullImage = cartToPol.loadM(img, dim, mask, rdmask, q_range, hdr, x_center, y_center, pixelcal = None, binsize = binsize)
    ExpObj.param['filename'] = filename
    
    if mon1:
        background = closedShutterCount * exposureTime
        
        ExpObj.param['before'] = mon2 - background
        ExpObj.param['after'] = mon2 - background
        ExpObj.param['ic'] = mon1 - background
        ExpObj.param['exposure_time'] = exposureTime

    return ExpObj, FullImage

#---- ##### Standard Tiff Images #####

def loadTiffFile(filename, expParams):
    
    print "Loading an image..."
            
    if expParams != None:
        mask, rdmask, q_range, pixelcal, x_center, y_center, binsize = _getExperimentParameters(expParams)

    hdr = {}
    img, dim = loadImage(filename)
                
    ExpObj, FullImage = cartToPol.loadM(img, dim, mask, rdmask, q_range, hdr, x_center, y_center, pixelcal = None, binsize = binsize)
    ExpObj.param['filename'] = filename
    
    return ExpObj, FullImage

#---- ######################
    
def readHeader(filename, fileformat):
    
    hdr = None
    
    if fileformat == 'quantum210':
        hdr = parseQuantumFileHeader(filename)
        
    elif fileformat == 'marccd165':
        hdr = MARCCD_headerReader.readHeader(filename)
    
    return hdr

# WORK IN PROGRESS:
def _getExperimentParameters(expParams):
        
        q_range = (expParams['QrangeLow'], expParams['QrangeHigh'])
        pixelcal = [expParams['PixelCalX'], expParams['PixelCalY']]
        x_center, y_center = expParams['Xcenter'], expParams['Ycenter']
        binsize = expParams['Binsize']
        mask = expParams['BeamStopMask']      
        rdmask = expParams['ReadOutNoiseMask'] 
        
        return mask, rdmask, q_range, pixelcal, x_center, y_center, binsize

def loadFile(filename, expParams = None):
        ''' Loads a file an returns a Measurement Object (ExpObj) and the full image if the
            selected file was an Image file
            
            NB: This is the function used to load any type of file in RAW
        '''
        try:
            file_type = checkFileType(filename)
        except Exception, msg:
            print >> sys.stderr, str(msg)
            file_type = None
    
        print file_type
        FullImage = None
        
        ############### ASCII Files #####################
        
        if file_type == 'rad':
            ExpObj = loadRadFile(filename)
            ExpObj.param['filename'] = filename
            
            if not ExpObj.i:
                ExpObj = loadPrimusDatFile(filename)
                ExpObj.param['filename'] = filename
                            
        elif file_type == 'soleil_rad':
            ExpObj = loadSoleilRadFile(filename)
            ExpObj.param['filename'] = filename
        elif file_type == 'primus':
            ExpObj = loadPrimusDatFile(filename)
            ExpObj.param['filename'] = filename
        elif file_type == 'bift':
            ExpObj = loadBiftFile(filename)
            ExpObj.param['filename'] = filename
            
            # If its not a Primus dat file, try Rad (can be .dat in old versions) 
            if not ExpObj.i != []:    #Very strange that == [] doesnt work.. but it doesnt!
                ExpObj = loadRadFile(filename)
                ExpObj.param['filename'] = filename
        
        elif file_type == None:
            ExpObj = None
            
        ########### IMAGE Files #######################################
        
        elif expParams['ImageFormat'] == 'Quantum 210, CHESS':
            ExpObj, FullImage = loadQuantum210File(filename, expParams)
        
        elif expParams['ImageFormat'] == 'MarCCD 165, MaxLab':
            ExpObj, FullImage = loadMarccd165File(filename, expParams)
            
        elif expParams['ImageFormat'] == 'Medoptics, CHESS':
            ExpObj, FullImage = loadTiffFile(filename, expParams)
            
        elif expParams['ImageFormat'] == 'FLICAM, CHESS':
            ExpObj, FullImage = loadTiffFile(filename, expParams)

        return ExpObj, FullImage
        
        
        #    raise Exception('Filename: ' + filename + '\nDoes not contain any recognisable data.')
        
        ## NB! WHat a F'd UP case!! if I do ExpObj.i == [] .. I get False even if its []
        ## if i use ExpObj.i != [] .. it works! 
        
# WORK IN PROGRESS:

#def loadTxtFile(filename):
    
#    iq_pattern = re.compile('\s*\d*[.]\d*[+E-]*\d+\s+-?\d*[.]\d*[+E-]*\d+\s+\d*[.]\d*[+E-]*\d+\s*\n')


def loadPrimusDatFile(filename):
    
    iq_pattern = re.compile('\s*\d*[.]\d*[+E-]*\d+\s+-?\d*[.]\d*[+E-]*\d+\s+\d*[.]\d*[+E-]*\d+\s*\n')

    i = []
    q = []
    err = []
    d = {}

    f = open(filename)

    try:
        for line in f:

            iq_match = iq_pattern.match(line)
            #param_match = param_pattern.match(line)

            if iq_match:
                #print line
                found = iq_match.group().split()
                q.append(float(found[0]))
                i.append(float(found[1]))
                err.append(float(found[2]))

    finally:
        f.close()

    i = array(i)
    q = array(q)
    err = array(err)
    #q = q / 10
   
    return cartToPol.RadFileMeasurement(i, q, err, d)

def loadBiftFile(filename):
    
    iq_pattern = re.compile('\s*\d*[.]\d*[+E-]*\d+\s+[+-]*\d*[.]\d*[+E-]*\d+\s+\d*[.]\d*[+E-]*\d+\s*\n')
    param_pattern = re.compile('[a-zA-Z0-9_]*\s*[:]\s+.*')
    
    bift_param_pattern = re.compile('\s\s\s[a-zA-Z0-9_]*\s*[:]\s+.*')
    
    iq_orig_pattern = re.compile('\s*\d*[.]\d*[+E-]*\d+\s+-?\d*[.]\d*[+E-]*\d+\s+\d*[.]\d*[+E-]*\d+\s+\d*[.]\d*[+E-]*\d+\s*\n')

    i = []
    q = []
    err = []
    
    i_orig = []
    q_orig = []
    err_orig = []
    fit = []
    d = {}
    allData = {}
     

    f = open(filename)
    
    try:
        for line in f:

            iq_match = iq_pattern.match(line)
            param_match = param_pattern.match(line)
            iq_orig_match = iq_orig_pattern.match(line)
            bift_param_match = bift_param_pattern.match(line)

            if iq_match:
                found = iq_match.group().split()
                q.append(float(found[0]))
                i.append(float(found[1]))
                err.append(float(found[2]))
                
            if iq_orig_match:
                found = iq_orig_match.group().split()
                q_orig.append(float(found[0]))
                i_orig.append(float(found[1]))
                err_orig.append(float(found[2]))
                fit.append(float(found[3]))
            
            if bift_param_match:
                found = bift_param_match.group().split()
                
                try:
                    val = float(found[2])
                except ValueError:
                    val = found[2]
                
                allData[found[0]] = val
                
                
            if param_match:
                found = param_match.group().split()

                if len(found) == 3:
                    try:
                        val = float(found[2])
                    except ValueError:
                        val = found[2]
                
                    d[found[0]] = val
                
                elif len(found) > 3:
                    arr = []
                    for each in range(2,len(found)):
                        try:
                            val = float(found[each])
                        except ValueError:
                            val = found[each]
                        
                        arr.append(val)
                    
                    d[found[0]] = arr
                else:
                    d[found[0]] = ''

    finally:
        f.close()
    
    P = array(i)
    R = array(q)
    err = array(err)
   
    allData['orig_q'] = q_orig
    allData['orig_i'] = i_orig
    allData['orig_err'] = err_orig

    return cartToPol.BIFTMeasurement(P, R, err, d, fit, allData)

def loadRadFile(filename):
    ''' This only works for our own rad format i think '''
    
    iq_pattern = re.compile('\s*\d*[.]\d*[+E-]*\d+\s+-?\d*[.]\d*[+E-]*\d+\s+\d*[.]\d*[+E-]*\d+\s+\d*[.]\d*[+E-]*\d+\s*\n')
    param_pattern = re.compile('[a-zA-Z0-9_]*\s*[:]\s+.*')

    i = []
    q = []
    err = []
    d = {}

    f = open(filename)
    
    try:
        for line in f:

            iq_match = iq_pattern.match(line)
            param_match = param_pattern.match(line)

            if iq_match:
                found = iq_match.group().split()
                q.append(float(found[0]))
                
                i.append(float(found[1]))
                
                err.append(float(found[2]))

            if param_match:
                found = param_match.group().split()

                if len(found) == 3:
                    try:
                        val = float(found[2])
                    except ValueError:
                        val = found[2]
                
                    d[found[0]] = val
                
                elif len(found) > 3:
                    arr = []
                    for each in range(2,len(found)):
                        try:
                            val = float(found[each])
                        except ValueError:
                            val = found[each]
                        
                        arr.append(val)
                    
                    d[found[0]] = arr
                else:
                    d[found[0]] = ''

    finally:
        f.close()
    
    i = array(i)
    q = array(q)
    #q = q / 10
    err = array(err)
   
    return cartToPol.RadFileMeasurement(i, q, err, d)


# WORK IN PROGRESS:
def saveMeasurement(Exp, NoChange = False):
    ''' Saves a Measurement Object to a .rad file.
        Returns the filename of the saved file '''
    
    full_path_filename = Exp.param['filename']
    
    no_path_filename = path.split(filenameWithoutExtension(Exp))[1]    
    filePath = path.split(full_path_filename)[0]
    
    if NoChange == False:
        if Exp.isBgSubbed:        
            filename = filePath + "\\" + "BSUB_" + no_path_filename + ".rad"
        elif Exp.isBifted:
            filename = filePath + "\\" + "BIFT_" + no_path_filename + ".rad"
        else:
            filename = filePath + "\\" + no_path_filename + ".rad"
    else:
        filename = full_path_filename
    
    # Insert new filename
    #Exp.param['filename'] = path.split(filename)[1]
    
    if Exp.type == 'bift':
        writeBiftFile(Exp, filename)
    else:
        writeRadFile(Exp, filename)
                    
    return filename


def filenameWithoutExtension(Exp):
    ''' removes the extension of a file '''
    
    full_path_filename = Exp.param['filename']
    
    filePath = path.split(full_path_filename)[0]
    
    no_path_filename = path.split(full_path_filename)[1]
    
    
    if len(no_path_filename) > 4:
        if no_path_filename[-4] == '.':
            new_filename = no_path_filename[:-4]
        elif no_path_filename[-5] == '.':
            new_filename = no_path_filename[:-5]
        else:
            new_filename = no_path_filename
    else:
        new_filename = no_path_filename
            
    filename = filePath + "\\" + new_filename
    
    return new_filename 

def writeRadFile(m, filename = None):
    ''' Writes an ASCII file from a measurement object, using the RAD format '''
    
    d = m.param
    
    f2 = open(filename, 'w')
    
    if m.type != 'bift':
        f2.write('   Exposure Time (sec): 1\n')
        f2.write('       Q             I                   Error           DeltaQ\n')
        f2.write('    %d\n' % len(m.i))
        
        fit = zeros(size(m.q))
    else:
        f2.write('   Exposure Time (sec): 1\n')
        f2.write('       R                P(R)             Error              Fit\n')
        f2.write('    %d\n' % len(m.i))
        
        fit = m.fit[0]
        
    for idx in range(0,len(m.i)):
        line = ('   %.8E  %.8E  %.8E  %.8E\n') %( m.q[idx], m.i[idx], m.errorbars[idx], float(fit[idx]) )
        f2.write(line)

    f2.write('\n\n')
    
    
    sortedKeys = d.keys()
    sortedKeys.sort()
    
    for each in sortedKeys:#d.iterkeys():
    
        if type(d[each]) == type([]):
            tmpline = ''
            for every in d[each]:
                tmpline = tmpline + str(every) + ' '

            tmpline = tmpline.strip()
        
            line = each + ' : ' + tmpline + '\n'
        else:
            line = each + ' : ' + str(d[each]) + '\n'

        f2.write(line)
    
    f2.close()


def writeBiftFile(m, filename = None):
    ''' Writes an ASCII file from a measurement object, using the RAD format '''
    
    d = m.param
    
    f2 = open(filename, 'w')
    
    no_path_filename = path.split(filenameWithoutExtension(m))[1]    
    
    if m.type != 'bift':
        print "ERROR! trying to write a bift file and its not a bift file!"
    else:
        f2.write('BIFT\n')
        f2.write('Filename: ' + no_path_filename + '\n\n' )
        f2.write('       R                P(R)             Error\n')
    
    for idx in range(0,len(m.i)):
        line = ('   %.8E  %.8E  %.8E\n') %( m.q[idx], m.i[idx], m.errorbars[idx])
        f2.write(line)
    
    f2.write('\n')
     
     
    ###########################################################
    # Write IFT parameters:
    ###########################################################
    savedParams = ['dmax', 'alpha', 'I0', 'Rg', 'ChiSquared']
    
    for each in savedParams:
        
        val = float(m.allData[each])

        strval = str(val)
        
        line = '   ' + each + ' : ' + strval + '\n'
        f2.write(line)
    

    f2.write('\n')
    line = ('***********************************************************************')
    f2.write(line)
    f2.write('\n\n')
    f2.write('         Q                I              Error              Fit\n')

    orig_data = m.allData
    fit = m.fit[0]
    orig_q = orig_data['orig_q']
    orig_I = orig_data['orig_i']
    orig_err = orig_data['orig_err']
    
    for idx in range(0,len(orig_I)):
        line = ('   %.8E  %.8E  %.8E  %.8E\n') %( orig_q[idx], orig_I[idx], orig_err[idx], float(fit[idx]) )
        f2.write(line)
    
    
    f2.write('\n\n')
    
    
    sortedKeys = d.keys()
    sortedKeys.sort()
    
    for each in sortedKeys:#d.iterkeys():
    
        if type(d[each]) == type([]):
            tmpline = ''
            for every in d[each]:
                tmpline = tmpline + str(every) + ' '

            tmpline = tmpline.strip()
        
            line = each + ' : ' + tmpline + '\n'
        else:
            line = each + ' : ' + str(d[each]) + '\n'

        f2.write(line)
    
    f2.close()
        
    
def loadSoleilRadFile(filename):
    
    data_pattern = re.compile('\d[.0-9E\-]*\s+\d[.0-9E\-]*\s+\d[.0-9E\-]*', re.IGNORECASE)
    
    q = []
    i = []
    err = []
    hdr = {}
    
    f = open(filename)
    
    for line in f:
        try:
            qval, ival, eval = data_pattern.match(line).group().split()
            q.append(float(qval))
            i.append(float(ival))
            err.append(float(eval))
        except Exception, e:
            pass

    f.close()
    
    q = array(q)
    i = array(i)
    err = array(err)
    
    return cartToPol.RadFileMeasurement(i, q, err, hdr)
    
def checkFileType(filename):
    
    f = open(filename, "rb")              # Open in binary mode for portability
    try:
        type_tst = MARCCD_headerReader.stringvar(MARCCD_headerReader.fread(f,'cc'))
    except:
        f.close()
        raise Exception('Reading file failed')
        
    f.close()
    
    # Test if file is a TIFF file (first two bytes are "II")
    
    print filename[-6:]
    
    if filename[-4:] == '.img' or filename[-6:] == '.imx_0' or filename[-6:] == '.dkx_0' or filename[-6:] == '.dkx_1':
        return 'quantum210'
    
    if type_tst == 'II':
        return 'tiff'
    
    if type_tst == '{\n':
        return 'soleil_rad'
    
    if type_tst == 'BI':
        return 'bift'
    
    if filename[-4:] == '.dat':
        return 'primus'
    else:
        return 'rad'
   

if __name__ == "__main__":
    
    print checkFileType('lise_192.dat')
    M = loadFile('lise_192.dat')
    print M[0].q
    