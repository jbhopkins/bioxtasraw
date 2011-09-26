'''
Created on Jul 11, 2010

@author: specuser
'''

import SASImage, SASM, SASIft, SASExceptions
import numpy as np
import os, sys, re, cPickle, time
import SASMarHeaderReader, packc_ext

#Need to hack PIL to make it work with py2exe/cx_freeze:
import Image
import TiffImagePlugin
Image._initialized=2


def createSASMFromImage(img_array, parameters = {}, x_c = None, y_c = None, mask = None,
                        readout_noise_mask = None, dezingering = 0, dezing_sensitivity = 4):
    ''' 
        Load measurement. Loads an image file, does pre-processing:
        masking, radial average and returns a measurement object
    '''
    
    if mask != None:
        if mask.shape != img_array.shape:
            raise Exception('Beamstop mask is wrong size.\n\nPlease' +
                            ' change the mask settings to make this plot')

    if readout_noise_mask != None:
        if readout_noise_mask.shape != img_array.shape: 
            raise Exception('Readout-noise mask is wrong size.\n\nPlease' +
                            ' change the mask settings to make this plot')
    
    try:
        [i_raw, q_raw, err_raw, qmatrix] = SASImage.radialAverage(img_array, x_c, y_c, mask, readout_noise_mask, dezingering, dezing_sensitivity)   
    except IndexError, msg:
        print 'Center coordinates too large: ' + str(msg)

        x_c = img_array.shape[1]/2
        y_c = img_array.shape[0]/2
        
        [i_raw, q_raw, err_raw, qmatrix] = SASImage.radialAverage(img_array, x_c, y_c, mask, readout_noise_mask, dezingering, dezing_sensitivity)        

        #wx.CallAfter(wx.MessageBox, "The center coordinates are too large for this image, used image center instead.",
        # "Center coordinates does not fit image", wx.OK | wx.ICON_ERROR)
    
    err_raw_non_nan = np.nan_to_num(err_raw)
    
    sasm = SASM.SASM(i_raw, q_raw, err_raw_non_nan, parameters)
    
    return sasm

def loadMask(filename):
    ''' Loads a mask  '''

    if os.path.splitext(filename)[1] == 'msk':
        
        FileObj = open(filename, 'r')            
        maskPlotParameters = cPickle.load(FileObj)
        FileObj.close()    
        
        i=0
        for each in maskPlotParameters['storedMasks']:
            each.maskID = i
            i = i + 1
        
        return SASImage.createMaskMatrix(maskPlotParameters), maskPlotParameters

############################
#--- ## Load image files: ##
############################
    
def loadTiffImage(filename):
    ''' Load TIFF image '''
    try:
        im = Image.open(filename)
        img = np.fromstring(im.tostring(), np.uint16)
        img = np.reshape(img, im.size) 
    except IOError:
        return None, {}
    
    img_hdr = {}
    
    return img, img_hdr

def load32BitTiffImage(filename):
    ''' Load TIFF image '''
    try:
        im = Image.open(filename)
        
        x,y = im.size
        
        img = np.fromstring(im.tostring(), np.uint32)
        img = np.reshape(img, (y,x)) 
    #except IOError:
    except Exception, e:
        print e
        return None, {}
    
    img_hdr = {}
    
    return img, img_hdr
    
def loadQuantumImage(filename):
    ''' Load image from quantum detectors (512 byte header) 
    and also obtains the image header '''
    
    f = open(filename, 'rb')
    f.seek(512)                         # Jump over header

    Img = np.fromfile(f, dtype=np.uint16)
    f.close()
    
    xydim = int(np.sqrt(np.shape(Img))[0])  #assuming square image

    Img = Img.reshape((xydim,xydim))
    
    img_hdr = parseQuantumFileHeader(filename)
    
    return Img, img_hdr


def loadMarCCD165Image(filename):
    ''' Loads a MarCCD 165 format image (tif) file and extracts the 
    information in the header '''
    
    img, img_hdr = loadTiffImage(filename)
    
    try:
        img_hdr = SASMarHeaderReader.readHeader(filename)
    except:
        pass
    
    return img, img_hdr

def loadPilatusImage(filename):
    ''' Loads a Pilatus format image (tif) file and extracts the 
    information in the header '''
    
    img, img_hdr = load32BitTiffImage(filename)
    img = np.fliplr(img)

    try:
        img_hdr = parsePilatusHeader(filename)
    except:
        img_hdr = {}
        pass
    
    return img, img_hdr

def loadMar345Image(filename):  
   
    dim = getMar345ImgDim(filename)
    SizeOfImage = dim[0]    
    img_ = np.zeros((SizeOfImage*SizeOfImage), dtype= np.int16)
    
    filename_ = filename.encode('utf8')

    img = packc_ext.packc(filename_,SizeOfImage,img_)
    img = img_.astype(np.uint16) #transform 2byte array to uint16 array
    img_ = np.reshape(img,(SizeOfImage, SizeOfImage))
    img = np.flipud(img_)
    
    #transform image array to matrix and mirror it.      
    del img_ # kill img_ and tempimg to free memory
    
    try: 
        img_hdr = parseMar345FileHeader(filename)
    except:
        pass
    
    return img, img_hdr

def getMar345ImgDim(filename):
    
    mar_file = open(filename, 'r')
    mar_file.seek(4096)
    
    dim = None
    
    for i in range(0, 5):           # search 5 lines from starting point
        line = mar_file.readline()
        
        if 'CCP' in line:
            splitline = line.split()
            
            x = int(splitline[4].strip(','))
            y = int(splitline[6].strip(','))
            
            dim = x,y
            break
                 
    mar_file.close()
    
    return dim

##########################################
#--- ## Parse Counter Files and Headers ##
##########################################

def parsePilatusHeader(filename):
    
    param_pattern = re.compile('\d*[:]\d*[:]\d*\D\d*[:]\d*[:]\d*')
    
    try:
        f = open(filename, 'r')
    
        hdr = {}
    except:
        print 'Reading Quantum header failed'
        return {}
    
    lineNum = 0
    
    for line in f:               
        date_found = param_pattern.search(line)
        
        if date_found:    
            hdr['Exposure_date'] = date_found.group()
            f.seek(580)
        
        try:
            if line.find('#') == 0:
                if line.split()[1] == 'Exposure_time':
                    hdr['Exposure_time'] = float(line.split()[2])
        except:
            print '** error reading the exposure time **'
               
    f.close()
 
    return hdr
    

def parseMar345FileHeader(filename):
    
    mar_file = open(filename, 'r')
    
    mar_file.seek(128)
    
    hdr = {}
    
    line = ''
    
    split_hdr = []
    
    
    while 'END OF HEADER' not in line:
        line = mar_file.readline().strip('/n')
        
        if len(line.split()) > 1:
            split_hdr.append(line.split())
        
    mar_file.close()
    
    for each_line in split_hdr:
        
        if each_line[0] == 'DATE':
            hdr['DATE'] = each_line[1] + ' ' + each_line[2] + ' ' + each_line[3] + ' ' + each_line[4] + ' ' + each_line[5]
            
        elif each_line[0] == 'GENERATOR':
            hdr['GENERATOR'] = each_line[1] + ' ' + each_line[2]
            hdr['GENERATOR_kV'] =  each_line[4]
            hdr['GENERATOR_mA'] =  each_line[6]
        
        elif each_line[0] == 'GAPS':
            c=1
            for i in range(1, len(each_line)):
                hdr['GAPS' + '_' + str(c)] = each_line[i]
                c+=1
        
        elif each_line[0] == 'END':
            break
        
        elif len(each_line) == 2:
            hdr[each_line[0]] = each_line[1]
        
        elif len(each_line) == 4:
            hdr[each_line[0]] = each_line[1]
            hdr[each_line[0] + '_' + each_line[2]] = each_line[3]
            
        elif len(each_line) == 5:
            hdr[each_line[0] + '_' + each_line[1]] = each_line[2]
            hdr[each_line[0] + '_' + each_line[3]] = each_line[4]
        
        elif len(each_line) == 7:
            hdr[each_line[0] + '_' + each_line[1]] = each_line[2]
            hdr[each_line[0] + '_' + each_line[3]] = each_line[4]
            hdr[each_line[0] + '_' + each_line[5]] = each_line[6]
            
        elif len(each_line) == 9:
            hdr[each_line[0] + '_' + each_line[1]] = each_line[2]
            hdr[each_line[0] + '_' + each_line[3]] = each_line[4]
            hdr[each_line[0] + '_' + each_line[5]] = each_line[6]
            hdr[each_line[0] + '_' + each_line[7]] = each_line[8]
            
    return hdr
    
def parseQuantumFileHeader(filename):
    ''' parses the header in a Quantum detector image '''
       
    param_pattern = re.compile('[a-zA-Z0-9_]*[=].*\n')
    
    try:
        f = open(filename)
        hdr = {}
    except:
        print 'Reading Quantum header failed'
        return {}
    
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
        print 'Reading Quantum header failed'
        return {}
        
    return hdr


def parseCHESSF2CTSfile(filename):
    
    timeMonitorPattern = re.compile('\d*-second\s[a-z]*\s[()A-Z,]*\s\d*\s\d*')
    closedShutterCountPattern = re.compile('closed\s\d*')
    datePattern = re.compile('#D\s.*\n')
    
    
    #try:
    f = open(filename[:-3] + 'cts')
    #except Exception as msg:        
    #    error_code = msg.args
    #    raise SASExceptions.FileHeaderNotFoundError(str(msg))
    
    mon1, mon2, exposure_time, closed_shutter_count = None, None, None, None
    
    for line in f:
        timeMonitor_match = timeMonitorPattern.search(line)
        closedShutterCount_match = closedShutterCountPattern.search(line)
        date_match = datePattern.search(line)
        
        if timeMonitor_match:           
            exposure_time = int(timeMonitor_match.group().split('-')[0])
            mon1 = int(timeMonitor_match.group().split(' ')[3])
            mon2 = int(timeMonitor_match.group().split(' ')[4])
                 
        if closedShutterCount_match:
            closed_shutter_count = int(closedShutterCount_match.group().split(' ')[1])
            
        if date_match:
            try:
                date = date_match.group()[3:-1]
            except Exception:
                date = 'Error loading date'
            
    f.close()
    
    background = closed_shutter_count * exposure_time
    
    counters = {'closedShutterCnt' : closed_shutter_count,
                'mon1': mon1,
                'mon2': mon2,
                'bgcount' : background,
                'exposureTime': exposure_time,
                'date': date}
    
    return counters

def parseCHESSG1CountFile(filename):
    ''' Loads information from the counter file at CHESS, G1 from
    the image filename '''
    
    dir, file = os.path.split(filename)
    underscores = file.split('_')
    
    countFile = underscores[0]
    
    filenumber = int(underscores[-2])
      
    if len(underscores)>3:
        for each in underscores[1:-2]:
            countFile += '_' + each
            
    countFilename = os.path.join(dir, countFile)
    
    file = open(countFilename,'r')
    
    allLines = file.readlines()
    file.close()
    
    line_num = 0
    start_found = False
    start_idx = None
    label_idx = None
    date_idx = None

    for eachLine in allLines:
        splitline = eachLine.split()
        
        if len(splitline) > 1:
            if splitline[0] == '#S' and splitline[1] == str(filenumber):
                start_found = True
                start_idx = line_num
            
            if splitline[0] == '#D' and start_found:
                date_idx = line_num
            
            if splitline[0] == '#L' and start_found:
                label_idx = line_num
                break
        
        line_num = line_num + 1

    counters = {}
    try:
        if start_idx and label_idx:
            labels = allLines[label_idx].split()
            vals = allLines[label_idx+1].split()
            
        for idx in range(0,len(vals)):    
            counters[labels[idx+1]] = vals[idx]
    
        if date_idx:
            counters['date'] = allLines[date_idx][3:-1]
    
    except:
        print 'Error loading G1 header'
    
    return counters

def parseMAXLABI77HeaderFile(filename):
    
    filepath, ext = os.path.splitext(filename)
    hdr_file = filepath + '.hdr'
    
    file = open(hdr_file,'r')
    
    all_lines = file.readlines()
    
    counters = {}
    
    for each_line in all_lines:
    
        split_lines = each_line.split()
        key = split_lines[0]
        
        if key == 'Start:':
            counters['date'] = " ".join(split_lines[1:6])
            counters['end_time'] = split_lines[-1]
        elif key == 'Sample:':
            counters['sample'] = split_lines[1]
            counters['code'] = split_lines[-1]
        elif key == 'MAXII':
            counters['current_begin'] = split_lines[4]
            counters['current_end'] = split_lines[6]
            counters['current_mean'] = split_lines[-1]
        elif key == 'SampleTemperature:':
            counters['temp_begin'] = split_lines[2]
            counters['temp_end'] = split_lines[2]
            counters['temp_mean'] = split_lines[6]
        elif key == 'SampleDiode:':
            counters['SmpDiode_begin'] = split_lines[2]
            counters['SmpDiode_end'] = split_lines[2]
            counters['SmpDiode_mean'] = split_lines[6]
        elif key == 'BeamstopDiode:':
            counters['BmStpDiode_avg'] = split_lines[2]
        elif key == 'IonChamber:':
            counters['IonDiode_avg'] = split_lines[2]
        elif key == 'Tube':
            counters['vacuum'] = split_lines[-1]
        elif key == 'ExposureTime:':
            counters['exposureTime'] = split_lines[1]
        elif key == 'MarCCD':
            counters['diameter'] = split_lines[4]
            counters['binning'] = split_lines[-1]
        elif key == 'BeamCenterX:':
            counters['xCenter'] = split_lines[1]
            counters['yCenter'] = split_lines[3]
            

    return counters
        
   

#################################################################
#--- ** Header and Image formats **
#################################################################
# To add new header types, write a parse function and append the
# dictionary header_types below
#################################################################

all_header_types = {'None'         : None,
                    'F2, CHESS'    : parseCHESSF2CTSfile, 
                    'G1, CHESS'    : parseCHESSG1CountFile,
                    'I711, MaxLab' : parseMAXLABI77HeaderFile}
   
all_image_types = {'Quantum'       : loadQuantumImage,
                   'MarCCD 165'    : loadMarCCD165Image,
                   'Mar345'        : loadMar345Image, 
                   'Medoptics'     : loadTiffImage,
                   'FLICAM'        : loadTiffImage,
                   'Pilatus'       : loadPilatusImage,
                   '16 bit TIF'    : loadTiffImage,
                   '32 bit TIF'    : load32BitTiffImage}


def loadAllHeaders(filename, image_type, header_type):
    ''' returns the image header and the info from the header file only. '''
    
    img, imghdr = loadImage(filename, image_type)
    
    if header_type != 'None':
        hdr = loadHeader(filename, header_type)
    else:
        hdr = None
    
    return imghdr, hdr

def loadHeader(filename, header_type):
    ''' returns header information based on the *image* filename
     and the type of headerfile  '''
    
    if header_type != 'None':
        try:
            hdr = all_header_types[header_type](filename)
        except IOError as io:
            error_type = io[0]
            raise SASExceptions.HeaderLoadError(str(io).replace("u'",''))
        #except:
        #    raise SASExceptions.HeaderLoadError('Header file for : ' + str(filename) + ' could not be read or contains incorrectly formatted data. ')
    else:
        return {}
    
    return hdr

def loadImage(filename, image_type):
    ''' returns the loaded image based on the image filename
    and image type. '''

    try:
        img, imghdr = all_image_types[image_type](filename)
    except ValueError, msg:
        raise SASExceptions.WrongImageFormat('Error loading image, ' + str(msg))
    
    return img, imghdr

#################################
#--- ** MAIN LOADING FUNCTION **
#################################

def loadFile(filename, raw_settings, no_processing = False):
    ''' Loads a file an returns a SAS Measurement Object (SASM) and the full image if the
        selected file was an Image file
            
         NB: This is the function used to load any type of file in RAW
    '''
    try:
        file_type = checkFileType(filename)
    except IOError:
        raise
    except Exception, msg:
        print >> sys.stderr, str(msg)
        file_type = None
    
    if file_type == 'image':
        try:
            sasm, img = loadImageFile(filename, raw_settings)
        except AttributeError, msg:
            print 'SASFileIO.loadFile : ' + str(msg)
            raise SASExceptions.UnrecognizedDataFormat('No data could be retrieved from the file, unknown format.')
        
        try:
            sasm = SASImage.calibrateAndNormalize(sasm, img, raw_settings)
        except ValueError, msg:
            print msg
        
        sasm.setParameter('normalizations', raw_settings.get('NormalizationList'))
        sasm.setParameter('config_file', raw_settings.get('CurrentCfg'))
          
    else:
        sasm = loadAsciiFile(filename, file_type)
        img = None
    
    SASM.postProcessSasm(sasm, raw_settings)
    
    if file_type == 'image' and no_processing == False:
            SASM.postProcessImageSasm(sasm, raw_settings)
        
    if sasm == None or len(sasm.i) == 0:
        raise SASExceptions.UnrecognizedDataFormat('No data could be retrieved from the file, unknown format.')
         
    return sasm, img

def loadAsciiFile(filename, file_type):
    
    ascii_formats = {'rad'        : loadRadFile,
                     'new_rad'    : loadNewRadFile,
                     'primus'     : loadPrimusDatFile,
                     'bift'       : loadBiftFile,
                     '2col'       : load2ColFile,
                     'int'        : loadIntFile}
    
    if file_type == None:
        return None
    
    sasm = None
        
    if ascii_formats.has_key(file_type):
        sasm = ascii_formats[file_type](filename)
    
    if sasm != None:
        if len(sasm.i) == 0:
            sasm = None
            
    if file_type == 'rad' and sasm == None:
        
        sasm = ascii_formats['new_rad'](filename)
        
        if sasm == None:
            sasm = ascii_formats['primus'](filename)
        
    if file_type == 'primus' and sasm == None:
        sasm = ascii_formats['2col'](filename)
   
    if sasm != None:
        sasm.setParameter('filename', os.path.split(filename)[1])
     
    return sasm

def loadImageFile(filename, raw_settings):
    
    img_fmt = raw_settings.get('ImageFormat')
    hdr_fmt = raw_settings.get('ImageHdrFormat')
        
    img, img_hdr = loadImage(filename, img_fmt)

    hdrfile_info = loadHeader(filename, hdr_fmt)
 
    parameters = {'imageHeader' : img_hdr,
                  'counters'    : hdrfile_info,
                  'filename'    : os.path.split(filename)[1],
                  'load_path'   : filename}
        
    x_c = raw_settings.get('Xcenter')
    y_c = raw_settings.get('Ycenter')
    
    masks = raw_settings.get('Masks')
    bs_mask = masks['BeamStopMask'][0]
    dc_mask = masks['ReadOutNoiseMask'][0]
    
    # ********* WARNING WARNING WARNING ****************#
    # Hmm.. axes start from the lower left, but array coords starts
    # from upper left:
    #####################################################
    y_c = img.shape[0]-y_c
    
    dezingering = raw_settings.get('ZingerRemovalRadAvg')
    dezing_sensitivity = raw_settings.get('ZingerRemovalRadAvgStd')
    
    sasm = createSASMFromImage(img, parameters, x_c, y_c, bs_mask, dc_mask, dezingering, dezing_sensitivity)

    return sasm, img

def loadPrimusDatFile(filename):
    ''' Loads a Primus .dat format file '''
    
    iq_pattern = re.compile('\s*\d*[.]\d*[+E-]*\d+\s+-?\d*[.]\d*[+E-]*\d+\s+\d*[.]\d*[+E-]*\d+\s*')

    i = []
    q = []
    err = []

    f = open(filename)
    
    firstLine = f.readline()
    
    fileHeader = {'comment':firstLine}
    parameters = {'filename' : os.path.split(filename)[1],
                  'fileHeader' : fileHeader}
    
    try:
        for line in f:

            iq_match = iq_pattern.match(line)

            if iq_match:
                #print line
                found = iq_match.group().split()
                q.append(float(found[0]))
                i.append(float(found[1]))
                err.append(float(found[2]))

    finally:
        f.close()

    i = np.array(i)
    q = np.array(q)
    err = np.array(err)
   
    sasm = SASM.SASM(i, q, err, parameters)
   
    return sasm

def loadRadFile(filename):
    ''' NOTE : THIS IS THE OLD RAD FORMAT..  '''
    ''' Loads a .rad file into a SASM object and attaches the filename and header into the parameters  '''
    
    iq_pattern = re.compile('\s*\d*[.]\d*[+E-]*\d+\s+-?\d*[.]\d*[+E-]*\d+\s+\d*[.]\d*[+E-]*\d+\s+-?\d*[.]\d*[+E-]*\d+\s*\n')
    param_pattern = re.compile('[a-zA-Z0-9_]*\s*[:]\s+.*')

    i = []
    q = []
    err = []
    parameters = {'filename' : os.path.split(filename)[1]}

    fileheader = {}

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
                
                    fileheader[found[0]] = val
                
                elif len(found) > 3:
                    arr = []
                    for each in range(2,len(found)):
                        try:
                            val = float(found[each])
                        except ValueError:
                            val = found[each]
                        
                        arr.append(val)
                    
                    fileheader[found[0]] = arr
                else:
                    fileheader[found[0]] = ''

    finally:
        f.close()
    
    
    parameters = {'filename' : os.path.split(filename)[1],
                  'fileHeader' : fileheader}
    
    i = np.array(i)
    q = np.array(q)
    err = np.array(err)
   
    return SASM.SASM(i, q, err, parameters)


def loadNewRadFile(filename):
    ''' NOTE : This is a load function for the new rad format '''
    ''' Loads a .rad file into a SASM object and attaches the filename and header into the parameters  '''

    iq_pattern = re.compile('\s*\d*[.]\d*[+E-]*\d+\s+-?\d*[.]\d*[+E-]*\d+\s+-?\d*[.]\d*[+E-]*\d+\s*\n')
    param_pattern = re.compile('[a-zA-Z0-9_]*\s*[:]\s+.*')

    i = []
    q = []
    err = []
    parameters = {'filename' : os.path.split(filename)[1]}

    fileheader = {}

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
                
                    fileheader[found[0]] = val
                
                elif len(found) > 3:
                    arr = []
                    for each in range(2,len(found)):
                        try:
                            val = float(found[each])
                        except ValueError:
                            val = found[each]
                        
                        arr.append(val)
                    
                    fileheader[found[0]] = arr
                else:
                    fileheader[found[0]] = ''

    finally:
        f.close()
    
    
    parameters = {'filename' : os.path.split(filename)[1],
                  'fileHeader' : fileheader}
    
    i = np.array(i)
    q = np.array(q)
    err = np.array(err)
   
    return SASM.SASM(i, q, err, parameters)


def loadIntFile(filename):
    ''' Loads a simulated SAXS data curve .int file '''
    
    i = []
    q = []
    err = []
    parameters = {'filename' : os.path.split(filename)[1]}
    
    f = open(filename)
    all_lines = f.readlines()
    f.close()
    
    for each_line in all_lines:
        split_line = each_line.split()
        
        if len(split_line) == 5:
            q.append(float(split_line[0]))
            i.append(float(split_line[1]))
    
    i = np.array(i)
    q = np.array(q)
    err = np.sqrt(abs(i))
    
    return SASM.SASM(i, q, err, parameters) 
    

def load2ColFile(filename):
    ''' Loads a two column file (q I) separated by whitespaces '''
    
    iq_pattern = re.compile('\s*\d*[.]\d*\s+-?\d*[.]\d*.*\n')
    
    i = []
    q = []
    err = []
    parameters = {'filename' : os.path.split(filename)[1]}
 
    f = open(filename)
    
    try:
        for line in f:
            iq_match = iq_pattern.match(line)

            if iq_match:
                found = iq_match.group().split()
                q.append(float(found[0]))
                i.append(float(found[1]))
#
    finally:
        f.close()
    
    i = np.array(i)
    q = np.array(q)
    err = np.sqrt(abs(i))
   
    return SASM.SASM(i, q, err, parameters)


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
    
    P = np.array(i)
    R = np.array(q)
    err = np.array(err)
   
    allData['orig_q'] = q_orig
    allData['orig_i'] = i_orig
    allData['orig_err'] = err_orig

    return SASIft.IFTM(P, R, err, d, fit, allData)

#####################################
#--- ## Write RAW Generated Files: ##
#####################################

# WORK IN PROGRESS:
def saveMeasurement(sasm, save_path, filetype = '.dat'):
    ''' Saves a Measurement Object to a .rad file.
        Returns the filename of the saved file '''
    
    filename, ext = os.path.splitext(sasm.getParameter('filename'))
    
    #if sasm.type == 'bift':
     #writeBiftFile(sasm, os.path.join(save_path, filename + '.rad'))
    #else:
    writeRadFile(sasm, os.path.join(save_path, filename + filetype))


def saveAnalysisCsvFile(sasm_list, include_data, save_path):
    
    file = open(save_path, 'w')
    
    if len(sasm_list) == 0:
        return None
    
    date = time.ctime()
    
    #Write the first line in the csv: 
    file.write('RAW ANALYSIS DATA\n')
    file.write(str(date) + '\n')
    file.write('Filename')
    
    all_included_keys = sorted(include_data.keys())
    
    for each_data in all_included_keys:
        var = include_data[each_data][0]
        key = include_data[each_data][1]
            
        line = ',' + str(key)
        file.write(line)
    
    file.write('\n')
        
    for each_sasm in sasm_list:
        
        parameters = each_sasm.getAllParameters()
        
        file.write(each_sasm.getParameter('filename'))
        
        for each_data in all_included_keys:
            var = include_data[each_data][0]
            key = include_data[each_data][1]
            
            file.write(',')
            
            if var == 'general':
                if parameters.has_key(key):
                    file.write('"' + str(each_sasm.getParameter(key)) + '"')
                elif key == 'scale':
                    file.write('"' + str(each_sasm.getScale()) + '"')
                elif key == 'offset':
                    file.write('"' + str(each_sasm.getOffset()) + '"')
                
            
            elif var == 'imageHeader':
                if parameters.has_key('imageHeader'):
                    img_hdr = each_sasm.getParameter('imageHeader')
                    if img_hdr.has_key(key):
                        file.write(str(img_hdr[key]))
                    else:
                        file.write(' ')
                else:
                        file.write(' ')
            
            elif var == 'counters':
                if parameters.has_key('counters'):
                    file_hdr = each_sasm.getParameter('counters')
                    if file_hdr.has_key(key):
                        file.write(str(file_hdr[key]))
                    else:
                        file.write(' ')
                else:
                    file.write(' ')
                    
                    
            elif var == 'guinier':
                if parameters.has_key('analysis'):
                    analysis_dict = each_sasm.getParameter('analysis')
                    
                    if analysis_dict.has_key('guinier'):
                        guinier = analysis_dict['guinier']
                    
                        if guinier.has_key(key):
                            file.write(str(guinier[key]))
                        else:
                            file.write(' ')
                    else:
                        file.write(' ')
                else:
                    file.write(' ')
            
            
        file.write('\n')   
            
    file.close()
    
    return True
    
    
def saveWorkspace(sasm_dict, save_path):

    file = open(save_path, 'w')

    cPickle.dump(sasm_dict, file)
    
def loadWorkspace(load_path):
    
    file = open(load_path, 'r')
    
    sasm_dict = cPickle.load(file)
    
    return sasm_dict


def writeCommaSeparatedAnalysisInfo():
    ''' Coming soon '''
    pass

def writeRadFile(m, filename):
    ''' Writes an ASCII file from a measurement object, using the RAD format '''
    
    d = m.getAllParameters()
    
    f2 = open(filename, 'w')
    
    f2.write('### HEADER:\n\n')
    
    sortedKeys = d.keys()
    sortedKeys.sort()
    
    for each in sortedKeys:#d.iterkeys():
    
        if type(d[each]) == type([]):
            tmpline = ''
            for every in d[each]:
                tmpline = tmpline + str(every) + ' '

            tmpline = tmpline.strip()
        
            line = each + ': ' + tmpline + '\n'
            
        elif type(d[each]) == type({}):
            line = printDict(d, each)
            
        else:
            line = each + ': ' + str(d[each]) + '\n'

        if each != 'fileHeader':
            f2.write(line)
    
    f2.write('\n\n')
    
    f2.write('### DATA:\n\n')
    f2.write('       Q             I                   Error\n')
    f2.write('    %d\n' % len(m.i))
        
    fit = np.zeros(np.size(m.q))

    q_min, q_max = m.getQrange()
    
    #print q_min, q_max, len(m.q), len(m.i), len(m.err)
    
    for idx in range(q_min, q_max):
        line = ('   %.8E  %.8E  %.8E\n') % ( m.q[idx], m.i[idx], m.err[idx])
        f2.write(line)
     
    f2.close()

def printDict(d, each):
    tmpline = each + ' {'
            
    newline = False
    for every_key in d[each].keys():
        if not newline:
            tmpline = tmpline + '\n'
            newline = True
        
        if type(d[each][every_key]) == type({}):
            tmpline = tmpline + ' ' + printDict(d[each], every_key)
        else:
            tmpline = tmpline + '   ' + str(every_key) + ': ' + str(d[each][every_key]) + '\n'
            
    tmpline = tmpline + '}\n'
    
    return tmpline

def writeBiftFile(m, filename = None):
    ''' Writes an ASCII file from a measurement object, using the RAD format '''
    
    d = m.param
    
    f2 = open(filename, 'w')
    
    no_path_filename = os.path.split(filename)    
    
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

def checkFileType(filename):
    ''' Tries to find out what file type it is and reports it back '''
    
    try:
        f = open(filename, "rb")              # Open in binary mode for portability
    except IOError:
        raise Exception('Reading file ' + filename + ' failed..')
    
    
    #Read first byte off file:
    try:
        type_tst = SASMarHeaderReader.stringvar(SASMarHeaderReader.fread(f,'cc'))
    except:
        f.close()
        raise Exception('Reading a byte of file ' + filename + ' failed..')
        
    f.close()
    
    path, ext = os.path.splitext(filename)

    #print type_tst

    if type_tst == 'II':   # Test if file is a TIFF file (first two bytes are "II")
        return 'image'
    elif ext == '.int':
        return 'int'
    elif ext == '.img' or ext == '.imx_0' or ext == '.dkx_0' or ext == '.dkx_1' or ext == '.png':
        return 'image'
    elif type_tst == 'BI':
        return 'bift'
    elif ext == '.dat':
        return 'primus'
    elif ext == '.mar1200' or ext == '.mar2400' or ext == '.mar3600':
        return 'image'
    else:
        return 'rad'
        