'''
Created on Jul 11, 2010

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

import hdf5plugin #This has to be imported before fabio, and h5py (and, I think, PIL/pillow) . . .

import os
import sys
import re
import cPickle
import time
import struct
import json
import copy
import collections
import datetime
from xml.dom import minidom
import glob
import subprocess
import platform

import numpy as np
import fabio
import PIL
from PIL import Image
import matplotlib.backends.backend_pdf

import RAWGlobals
import SASImage
import SASM
import SASExceptions
import SASProc

def createSASMFromImage(img_array, parameters = {}, x_c = None, y_c = None, mask = None,
                        readout_noise_mask = None, tbs_mask = None, dezingering = 0, dezing_sensitivity = 4):
    '''
        Load measurement. Loads an image file, does pre-processing:
        masking, radial average and returns a measurement object
    '''
    if mask is not None:
        if mask.shape != img_array.shape:
            raise SASExceptions.MaskSizeError('Beamstop mask is the wrong size. Please' +
                            ' create a new mask or remove the old to make this plot.')

    if readout_noise_mask is not None:
        if readout_noise_mask.shape != img_array.shape:
            raise SASExceptions.MaskSizeError('Readout-noise mask is the wrong size. Please' +
                            ' create a new mask or remove the old to make this plot.')

    if tbs_mask is not None:
        if tbs_mask.shape != img_array.shape:
            raise SASExceptions.MaskSizeError('ROI Counter mask is the wrong size. Please' +
                            ' create a new mask or remove the old to make this plot.')

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

    if tbs_mask is not None:
        roi_counter = img_array[tbs_mask==1].sum()
        parameters['counters']['roi_counter'] = roi_counter

    sasm = SASM.SASM(i_raw, q_raw, err_raw_non_nan, parameters)

    return sasm

def loadMask(filename):
    ''' Loads a mask  '''

    if os.path.splitext(filename)[1] == 'msk':

        with open(filename, 'r') as FileObj:
            maskPlotParameters = cPickle.load(FileObj)

        i=0
        for each in maskPlotParameters['storedMasks']:
            each.maskID = i
            i = i + 1

        return SASImage.createMaskMatrix(maskPlotParameters), maskPlotParameters

############################
#--- ## Load image files: ##
############################

def loadFabio(filename):
    fabio_img = fabio.open(filename)

    if fabio_img.nframes == 1:
        data = fabio_img.data
        hdr = fabio_img.getheader()

        img = [data]
        img_hdr = [hdr]

    else:
        img = [None for i in range(fabio_img.nframes)]
        img_hdr = [None for i in range(fabio_img.nframes)]

        img[0] = fabio_img.data
        img_hdr[0] = fabio_img.getheader()

        for i in range(1,fabio_img.nframes):
            fabio_img = fabio_img.next()
            img[i] = fabio_img.data
            img_hdr[i] = fabio_img.getheader()

    return img, img_hdr

def loadTiffImage(filename):
    ''' Load TIFF image '''
    try:
        im = Image.open(filename)
        if int(PIL.PILLOW_VERSION.split('.')[0])>2:
            img = np.fromstring(im.tobytes(), np.uint16) #tobytes is compatible with pillow >=3.0, tostring was depreciated
        else:
            img = np.fromstring(im.tostring(), np.uint16)

        img = np.reshape(img, im.size)
        im.close()
    except IOError:
        return None, {}

    img_hdr = {}

    return img, img_hdr

def load32BitTiffImage(filename):
    ''' Load TIFF image '''
    try:
        im = Image.open(filename)
        if int(PIL.PILLOW_VERSION.split('.')[0])>2:
            img = np.fromstring(im.tobytes(), np.uint32) #tobytes is compatible with pillow >=3.0, tostring was depreciated
        else:
            img = np.fromstring(im.tostring(), np.uint32)

        img = np.reshape(img, im.size)
        im.close()
    #except IOError:
    except Exception, e:
        print e
        return None, {}

    img_hdr = {}

    return img, img_hdr



def loadFrelonImage(filename):

    with open(filename, 'rb') as fo:

        ############## FIND HEADER LENGTH AND READ IMAGE ###########
        fo.seek(0, 2)
        eof = fo.tell()
        fo.seek(0)

        hdr_size = 1
        byte = None
        while byte != '}' and hdr_size !=eof:
            byte = fo.read(1)
            hdr_size = hdr_size + 1
            if hdr_size > 10000:
                raise ValueError

        ######################## PARSE HEADER ###################
        fo.seek(0)
        header = fo.read(hdr_size)
        header = header.split('\n')

        header_dict = {}
        for each in header:
            sp_line = each.split('=')

            if sp_line[0].strip() == '{' or sp_line[0].strip() == '}' or sp_line[0].strip() == '':
                continue

            if len(sp_line) == 2:
                header_dict[sp_line[0].strip()] = sp_line[1].strip()[:-2]
            elif len>2:
                header_dict[sp_line[0].strip()] = each[each.find('=')+2:-2]

        #print header_dict

        fo.seek(hdr_size)

        dim1 = int(header_dict['Dim_1'])
        dim2 = int(header_dict['Dim_2'])

        img = np.fromfile(fo, dtype='<i2')
        img = np.reshape(img, (dim1, dim2))

    img_hdr = header_dict

    return img, img_hdr


def loadIllSANSImage(filename):

    with open(filename, 'r') as datafile:
        all_lines = datafile.readlines()


    ############################################
    # Find image location:
    lineidx = 0
    header_idx = 0
    image_found = False
    for line in all_lines:

        if len(line.split()) > 0:
            if image_found and line.split()[0] == '16384':
                break

        if line[0] == 'I':
            image_found = True
        else:
            image_found = False

        try:
            if line[0:10] == 'F'*10:
                header_idx = lineidx
        except Exception:
            pass

        lineidx = lineidx + 1
    ##############################################

    if header_idx == 0:
        raise ValueError

    header_idx = header_idx + 2 ## header starts 2 lines down

    no_header_lines = 25 # I dont know where to get this number.. 128 is written in the beginning.. but thats wrong
    no_header_colums = 5

    hdr_labels = {}
    hdr_label_idx = 0
    for each in all_lines[ header_idx : header_idx + no_header_lines + 1 ]:
        for col in range( 0, no_header_colums ):
            hdr_labels[ hdr_label_idx ] = each[ 16*col : 16*col + 16].lstrip().replace(' ', '_').replace('.', '_')
            hdr_label_idx += 1

    hdr = {}
    ############ Read header values ###########
    hdr_label_idx = 0
    for each in all_lines[ header_idx + no_header_lines + 1: header_idx + ( 2*no_header_lines ) + 1 ]:
        for col in range( 0, no_header_colums ):
            hdr[hdr_labels[ hdr_label_idx ]] = float(each[ 16*col : 16*col + 16].lstrip())
            hdr_label_idx += 1

    hdr.pop('', None)
    ##################    READ IMAGE    ######################
    datalines = all_lines[ lineidx + 1 : ]

    data = np.array([])
    for each_line in datalines:
        ints = map(int, each_line.split())
        data = np.append(data, ints)

    img = np.reshape(data, (128,128))

    return img, hdr


def loadSAXSLAB300Image(filename):

    try:
        im1 = Image.open(filename)
        im1a = im1.transpose(Image.FLIP_LEFT_RIGHT)
        im1b = im1a.transpose(Image.ROTATE_90)
        im2 = im1b.transpose(Image.FLIP_TOP_BOTTOM)

        # newArr = np.fromstring(im2.tobytes(), np.int32)
        if int(PIL.PILLOW_VERSION.split('.')[0])<3:
            newArr = np.fromstring(im2.tostring(), np.int32)
        else:
            newArr = np.fromstring(im2.tobytes(), np.int32)

        # reduce negative vals
        newArr = np.where(newArr >= 0, newArr, 0)
        newArr = np.reshape(newArr, (im2.size[1],im2.size[0]))

        try:
          tag = im1.tag
        except AttributeError:
          tag = None
        im1.close()
    except (IOError, ValueError):
        return None, None

    try:
        print tag
        if int(PIL.PILLOW_VERSION.split('.')[0])<3:
            tag_with_data = tag[315]
        else:
            tag_with_data = tag[315][0]

    except (TypeError, KeyError):
        print "Wrong file format. Missing TIFF tag number"
        raise

    img = newArr
    img_hdr = parseSAXSLAB300Header(tag_with_data)

    return img, img_hdr



##########################################
#--- ## Parse Counter Files and Headers ##
##########################################

def parseCSVHeaderFile(filename):
    counters = {}

    return counters


def parseSAXSLAB300Header(tag_with_data):
    ''' Read the header information from a TIFF file tag '''

    #d = odict()
    d = {}
    DOMTree = minidom.parseString(tag_with_data)

    params = DOMTree.getElementsByTagName('param')

    for p in params:
      try:
        d[p.attributes['name'].value] = p.childNodes[0].data
      except IndexError:
        pass

    tr={} # dictionary for transaltion :)
    tr['det_exposure_time'] = 'exposure_time'
    tr['livetime'] = 'integration_time'
    tr['det_count_cutoff'] = 'saturated_value'
    tr['Img.Description'] = 'file_comments'
    tr['data_p10'] = 'p10'
    tr['data_p90'] = 'p90'
    tr['data_min'] = 'min'
    tr['data_max'] = 'max'
    tr['data_mean'] = 'mean'
    tr['start_timestamp'] = 'aquire_timestamp'
    tr['Meas.Description'] = 'dataset_comments'

    # make parameters name substitution
    for i in tr:
      try:
        val = d[i]
        #del(d[i])
        d[tr[i]] = val
      except KeyError:
        pass

    try:
      d['IC'] = d['saxsconf_Izero']
    except KeyError: pass
    try:
      d['BEFORE'] = d['saxsconf_Izero']
    except KeyError: pass
    try:
      d['AFTER'] = d['saxsconf_Izero']
    except KeyError: pass

    try:
      if d['det_flat_field'] != '(nil)':
          d['flatfield_applied'] = 1
      else:
          d['flatfield_applied'] = 0
    except KeyError: pass
    d['photons_per_100adu'] = 100

    try:
      (d['beam_x'],d['beam_y']) = d['beamcenter_actual'].split()
    except KeyError: pass
    try:
      (d['pixelsize_x'],d['pixelsize_y']) = d['det_pixel_size'].split()
      #unit conversions
      d['pixelsize_x'] = float(d['pixelsize_x']) * 1e6;
      d['pixelsize_y'] = float(d['pixelsize_y']) * 1e6;
    except KeyError: pass

    # conversion all possible values to numbers
    for i in d.keys():
      try:
        d[i] = float(d[i])
      except ValueError: pass

    return d



def parseCHESSF2CTSfile(filename):

    timeMonitorPattern = re.compile('\d*-second\s[a-z]*\s[()A-Z,]*\s\d*\s\d*')
    closedShutterCountPattern = re.compile('closed\s\d*')
    datePattern = re.compile('#D\s.*\n')


    with open(filename[:-3] + 'cts', 'rU') as f:

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

    filenumber = int(underscores[-2].strip('scan'))

    try:
        frame_number = int(underscores[-1].split('.')[0])
    except Exception:
        frame_number = 0


    if len(underscores)>3:
        for each in underscores[1:-2]:
            countFile += '_' + each

    countFilename = os.path.join(dir, countFile)

    with open(countFilename,'rU') as f:
        allLines = f.readlines()

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
            vals = allLines[label_idx+1+frame_number].split()

        for idx in range(0,len(vals)):
            counters[labels[idx+1]] = vals[idx]

        if date_idx:
            counters['date'] = allLines[date_idx][3:-1]

    except:
        print 'Error loading G1 header'

    return counters

def parseCHESSG1CountFileWAXS(filename):
    ''' Loads information from the counter file at CHESS, G1 from
    the image filename '''

    dir, file = os.path.split(filename)
    underscores = file.split('_')

    countFile = underscores[0]

    filenumber = int(underscores[-2].strip('scan'))

    try:
        frame_number = int(underscores[-1].split('.')[0])
    except Exception:
        frame_number = 0


    if len(underscores)>3:
        for each in underscores[1:-3]:
            countFile += '_' + each

    countFilename = os.path.join(dir, countFile)

    with open(countFilename,'rU') as f:
        allLines = f.readlines()

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
            vals = allLines[label_idx+1+frame_number].split()

        for idx in range(0,len(vals)):
            counters[labels[idx+1]] = vals[idx]

        if date_idx:
            counters['date'] = allLines[date_idx][3:-1]

    except:
        print 'Error loading G1 header'


    return counters

def parseCHESSG1CountFileEiger(filename):
    ''' Loads information from the counter file at CHESS, G1 from
    the image filename '''

    dir, file = os.path.split(filename)

    dir = os.path.dirname(dir)
    underscores = file.split('_')

    countFile = underscores[0]

    filenumber = int(underscores[-3].strip('scan'))

    try:
        frame_number = int(underscores[-1].split('.')[0])-1
    except Exception:
        frame_number = 0


    if len(underscores)>3:
        for each in underscores[1:-3]:
            countFile += '_' + each

    countFilename = os.path.join(dir, countFile)

    with open(countFilename,'rU') as f:
        allLines = f.readlines()

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
            vals = allLines[label_idx+1+frame_number].split()

        for idx in range(0,len(vals)):
            counters[labels[idx+1]] = vals[idx]

        if date_idx:
            counters['date'] = allLines[date_idx][3:-1]

    except:
        print 'Error loading G1 header'

    return counters

def parseMAXLABI911HeaderFile(filename):

    filepath, ext = os.path.splitext(filename)
    hdr_file = filename + '.hdr'

    with open(hdr_file,'rU') as f:
        all_lines = f.readlines()

    counters = {}

    for each_line in all_lines:
        split_lines = each_line.split('=')
        key = split_lines[0]
        counters[key] = split_lines[-1][:-1]

    return counters


def parseMAXLABI77HeaderFile(filename):

    filepath, ext = os.path.splitext(filename)
    hdr_file = filename + '.hdr'

    with open(hdr_file,'rU') as f:
        all_lines = f.readlines()

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


def parseBioCATlogfile(filename):
    datadir, fname = os.path.split(filename)

    countFilename=os.path.join(datadir, '_'.join(fname.split('_')[:-1])+'.log')

    with open(countFilename,'rU') as f:
        allLines=f.readlines()

    searchName='.'.join(fname.split('.')[:-1])

    line_num=0

    counters = {}

    for i, line in enumerate(allLines):
        if line.startswith('#'):
            if line.startswith('#Filename') or line.startswith('#image'):
                labels = line.strip('#').split('\t')
                offset = i
            else:
                key = line.strip('#').split(':')[0].strip()
                val = ':'.join(line.strip('#').split(':')[1:])
                counters[key] = val.strip()
        else:
            break

    test_idx = int(searchName.split('_')[-1]) + offset

    if searchName in allLines[test_idx]:
        line_num = test_idx
    else:
        for a in range(1,len(allLines)):
            if searchName in allLines[a]:
                line_num=a

    if line_num>0:
        vals=allLines[line_num].split('\t')

        for a in range(len(labels)):
            counters[labels[a]] = vals[a]

    return counters


def parseCHESSG1Filename(filename):
    ''' Parses CHESS G1 Filenames '''

    directory, filename = os.path.split(filename)
    underscores = filename.split('_')

    countFile = underscores[0]

    filenumber = underscores[-2].strip('scan')

    try:
        frame_number = underscores[-1].split('.')[0]
    except Exception:
        frame_number = 0


    if len(underscores)>3:
        for each in underscores[1:-2]:
            countFile += '_' + each

    countFilename = os.path.join(directory, countFile)

    return (countFilename, filenumber, frame_number)

def parseBiocatFilename(filename):
    """Parses BioCAT filenames"""

    directory, filename = os.path.split(filename)
    underscores = filename.split('_')

    fprefix = '_'.join(underscores[:-1])
    frame_number = underscores[-1].split('.')[0]

    countFilename = os.path.join(directory, fprefix)

    return (countFilename, frame_number)


def parseBL19U2HeaderFile(filename):
    fname, ext = os.path.splitext(filename)

    countFilename=fname + '.txt'

    counters = {}

    with open(countFilename, 'rU') as f:
        for line in f:
            name = line.split(':')[0]
            value = ':'.join(line.split(':')[1:])
            counters[name.strip()] = value.strip()

    return counters


def parsePetraIIIP12EigerFile(filename, new_filename = None):
    if new_filename:
        fnum = int(new_filename.split('_')[-1].split('.')[0])
    else:
        fnum = 1

    data_path, data_name = os.path.split(filename)

    header_name = '_'.join(data_name.split('_')[:2])+'_%05i.txt' %(fnum)

    header_path = os.path.join(os.path.split(data_path)[0], 'header')

    countFilename = os.path.join(header_path, header_name)

    counters = {}

    with open(countFilename, 'rU') as f:
        for line in f:
            name = line.split(':')[0]
            value = ':'.join(line.split(':')[1:])
            counters[name.strip()] = value.strip()

    return counters



#################################################################
#--- ** Header and Image formats **
#################################################################
# To add new header types, write a parse function and append the
# dictionary header_types below
#################################################################

all_header_types = {'None'                  : None,
 #                     'CSV'                : parseCSVHeaderFile,
                    'F2, CHESS'             : parseCHESSF2CTSfile,
                    'G1, CHESS'             : parseCHESSG1CountFile,
                    'G1 WAXS, CHESS'        : parseCHESSG1CountFileWAXS,
                    'G1 Eiger, CHESS'       : parseCHESSG1CountFileEiger,
                    'I711, MaxLab'          : parseMAXLABI77HeaderFile,
                    'I911-4 Maxlab'         : parseMAXLABI911HeaderFile,
                    'BioCAT, APS'           : parseBioCATlogfile,
                    'BL19U2, SSRF'          : parseBL19U2HeaderFile,
                    'P12 Eiger, Petra III'  : parsePetraIIIP12EigerFile}

all_image_types = {
                   'Pilatus'       : loadFabio,
                   'CBF'                : loadFabio,
                   'SAXSLab300'         : loadSAXSLAB300Image,
                   'ADSC Quantum'       : loadFabio,
                   'Bruker'             : loadFabio,
                   'Gatan Digital Micrograph' : loadFabio,
                   'EDNA-XML'           : loadFabio,
                   'ESRF EDF'           : loadFabio,
                   'FReLoN'             : loadFrelonImage,
                   'Nonius KappaCCD'    : loadFabio,
                   'Fit2D spreadsheet'  : loadFabio,
                   'FLICAM'             : loadTiffImage,
                   'General Electric'   : loadFabio,
                   'Hamamatsu CCD'      : loadFabio,
                   'HDF5 (Hierarchical data format)'  : loadFabio,
                   'ILL SANS D11'       : loadIllSANSImage,
                   'MarCCD 165'         : loadFabio,
                   'Mar345'             : loadFabio,
                   'Medoptics'          : loadTiffImage,
                   'Numpy 2D Array'     : loadFabio,
                   'Oxford Diffraction' : loadFabio,
                   'Pixi'               : loadFabio,
                   'Portable aNy Map'   : loadFabio,
                   'Rigaku SAXS format' : loadFabio,
                   '16 bit TIF'         : loadFabio,
                   '32 bit TIF'         : load32BitTiffImage,
                   'MPA (multiwire)'    : loadFabio,
                   'Eiger'              : loadFabio,
                   'Rigaku HiPix'       : loadFabio,
                   # 'NeXus'           : loadNeXusFile,
                                      }


def loadAllHeaders(filename, image_type, header_type, raw_settings):
    ''' returns the image header and the info from the header file only. '''

    img, imghdr = loadImage(filename, raw_settings)

    if len(img) > 1:
        temp_filename = os.path.split(filename)[1].split('.')
        if len(temp_filename) > 1:
            temp_filename[-2] = temp_filename[-2] + '_%05i' %(1)
        else:
            temp_filename[0] = temp_filename[0] + '_%05i' %(1)

        new_filename = '.'.join(temp_filename)
    else:
        new_filename = os.path.split(filename)[1]

    if header_type != 'None':
        hdr = loadHeader(filename, new_filename, header_type)
    else:
        hdr = None

    masks = raw_settings.get('Masks')
    tbs_mask = masks['TransparentBSMask'][0]

    if tbs_mask is not None:
        if isinstance(img, list):
            roi_counter = img[0][tbs_mask==1].sum() #In the case of multiple images in the same file, load the ROI for the first one
        else:
            roi_counter = img[tbs_mask==1].sum()

        if hdr is None:
            hdr = {'roi_counter': roi_counter}
        else:
            hdr['roi_counter'] = roi_counter

    return imghdr, hdr

def loadHeader(filename, new_filename, header_type):
    ''' returns header information based on the *image* filename
     and the type of headerfile     '''

    if header_type != 'None':
        try:
            if new_filename != os.path.split(filename)[1]:
                hdr = all_header_types[header_type](filename, new_filename)
            else:
                hdr = all_header_types[header_type](filename)
        except IOError as io:
            raise SASExceptions.HeaderLoadError(str(io).replace("u'",''))
        except Exception as e:
            print e
            raise SASExceptions.HeaderLoadError('Header file for : ' + str(filename) + ' could not be read or contains incorrectly formatted data. ')
    else:
        hdr = {}

    #Clean up headers by removing spaces in header names and non-unicode characters)
    if hdr is not None:
        hdr = {key.replace(' ', '_').translate(None, '()[]') if isinstance(key, str) else key : hdr[key] for key in hdr}
        hdr = {key : unicode(hdr[key], errors='ignore') if isinstance(hdr[key], str) else hdr[key] for key in hdr}

    return hdr

def loadImage(filename, raw_settings):
    ''' returns the loaded image based on the image filename
    and image type. '''
    image_type = raw_settings.get('ImageFormat')
    fliplr = raw_settings.get('DetectorFlipLR')
    flipud = raw_settings.get('DetectorFlipUD')

    try:
        img, imghdr = all_image_types[image_type](filename)
    except (ValueError, TypeError, KeyError, fabio.fabioutils.NotGoodReader, Exception) as msg:
        # print msg
        raise SASExceptions.WrongImageFormat('Error loading image, ' + str(msg))

    if type(img) != list:
        img = [img]
    if type(imghdr) != list:
        imghdr = [imghdr]

    #Clean up headers by removing spaces in header names and non-unicode characters)
    for hdr in imghdr:
        if hdr is not None:
            hdr = {key.replace(' ', '_').translate(None, '()[]') if isinstance(key, str) else key: hdr[key] for key in hdr}
            hdr = { key : unicode(hdr[key], errors='ignore') if isinstance(hdr[key], str) else hdr[key] for key in hdr}


    if image_type != 'SASLab300':
        for i in range(len(img)):
            if fliplr:
                img[i] = np.fliplr(img[i])
            if flipud:
                img[i] = np.flipud(img[i])
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
        # print file_type
    except IOError:
        raise
    except Exception, msg:
        print >> sys.stderr, str(msg)
        file_type = None

    if file_type == 'image':
        try:
            sasm, img = loadImageFile(filename, raw_settings)
        except (ValueError, AttributeError), msg:
            print 'SASFileIO.loadFile : ' + str(msg)
            raise SASExceptions.UnrecognizedDataFormat('No data could be retrieved from the file, unknown format.')

        if not RAWGlobals.usepyFAI_integration:
            try:
                sasm = SASImage.calibrateAndNormalize(sasm, img, raw_settings)
            except (ValueError, NameError), msg:
                print msg

        #Always do some post processing for image files
        if not isinstance(sasm, list):
            sasm = [sasm]
        for current_sasm in sasm:
            current_sasm.setParameter('config_file', raw_settings.get('CurrentCfg'))
            SASM.postProcessSasm(current_sasm, raw_settings)

            # Add meta data if any is defined.
            if raw_settings.get('EnableMetadata'):
                meta_list = raw_settings.get('MetadataList')
                if meta_list is not None and len(meta_list) > 0:
                    metadata = {key:value for (key, value) in meta_list}
                    current_sasm.setParameter('metadata', metadata)

            if not no_processing:
                #Need to do a little work before we can do glassy carbon normalization
                if raw_settings.get('NormAbsCarbon') and not raw_settings.get('NormAbsCarbonIgnoreBkg'):
                    bkg_filename = raw_settings.get('NormAbsCarbonSamEmptyFile')
                    bkg_sasm = raw_settings.get('NormAbsCarbonSamEmptySASM')
                    if bkg_sasm is None or bkg_sasm.getParameter('filename') != os.path.split(bkg_filename)[1]:
                        bkg_sasm, junk_img = loadFile(bkg_filename, raw_settings, no_processing=True)
                        if isinstance(bkg_sasm,list):
                            if len(bkg_sasm) > 1:
                                bkg_sasm = SASProc.average(bkg_sasm)
                            else:
                                bkg_sasm = bkg_sasm[0]
                        raw_settings.set('NormAbsCarbonSamEmptySASM', bkg_sasm)

                try:
                    SASM.postProcessImageSasm(current_sasm, raw_settings)
                except SASExceptions.AbsScaleNormFailed:
                    raise
    else:
        sasm = loadAsciiFile(filename, file_type)
        img = None

        #If you don't want to post process asci files, return them as a list
        if type(sasm) != list:
            SASM.postProcessSasm(sasm, raw_settings)

    if not isinstance(sasm, list) and (sasm is None or len(sasm.i) == 0):
        raise SASExceptions.UnrecognizedDataFormat('No data could be retrieved from the file, unknown format.')

    return sasm, img

def loadAsciiFile(filename, file_type):
    ascii_formats = {'rad'        : loadRadFile,
                     'new_rad'    : loadNewRadFile,
                     'primus'     : loadPrimusDatFile,
                     # 'bift'       : loadBiftFile, #'ift' is used instead
                     '2col'       : load2ColFile,
                     'int'        : loadIntFile,
                     'fit'        : loadFitFile,
                     'fir'        : loadFitFile,
                     'ift'        : loadIftFile,
                     'csv'        : loadCsvFile,
                     'out'        : loadOutFile}

    if file_type is None:
        return None

    sasm = None

    if ascii_formats.has_key(file_type):
        sasm = ascii_formats[file_type](filename)

    if sasm is not None and file_type != 'ift' and file_type != 'out':
        if type(sasm) != list and len(sasm.i) == 0:
            sasm = None

    if file_type == 'rad' and sasm is None:

        sasm = ascii_formats['new_rad'](filename)

        if sasm is None:
            sasm = ascii_formats['primus'](filename)

    if file_type == 'primus' and sasm is None:
        sasm = ascii_formats['2col'](filename)

    if sasm is not None and type(sasm) != list:
        sasm.setParameter('filename', os.path.split(filename)[1])

    return sasm


def loadImageFile(filename, raw_settings):
    img_fmt = raw_settings.get('ImageFormat')
    hdr_fmt = raw_settings.get('ImageHdrFormat')

    loaded_data, loaded_hdr = loadImage(filename, raw_settings)

    sasm_list = [None for i in range(len(loaded_data))]

    #Pre-load the flatfield file, so it's not loaded every time
    if raw_settings.get('NormFlatfieldEnabled'):
        flatfield_filename = raw_settings.get('NormFlatfieldFile')
        if flatfield_filename is not None:
            flatfield_img, flatfield_img_hdr = loadImage(flatfield_filename, raw_settings)
            flatfield_hdr = loadHeader(flatfield_filename, flatfield_filename, hdr_fmt)
            flatfield_img = np.average(flatfield_img, axis=0)

    #Process all loaded images into sasms
    for i in range(len(loaded_data)):
        img = loaded_data[i]
        img_hdr = loaded_hdr[i]

        if len(loaded_data) > 1:
            temp_filename = os.path.split(filename)[1].split('.')
            if len(temp_filename) > 1:
                temp_filename[-2] = temp_filename[-2] + '_%05i' %(i+1)
            else:
                temp_filename[0] = temp_filename[0] + '_%05i' %(i+1)

            new_filename = '.'.join(temp_filename)
        else:
            new_filename = os.path.split(filename)[1]

        hdrfile_info = loadHeader(filename, new_filename, hdr_fmt)

        parameters = {'imageHeader' : img_hdr,
                      'counters'    : hdrfile_info,
                      'filename'    : new_filename,
                      'load_path'   : filename}

        for key in parameters['counters']:
            if key.lower().find('concentration') > -1 or key.lower().find('mg/ml') > -1:
                parameters['Conc'] = parameters['counters'][key]
                break

        x_c = raw_settings.get('Xcenter')
        y_c = raw_settings.get('Ycenter')

        ## Read center coordinates from header?
        if raw_settings.get('UseHeaderForCalib'):
            try:
                x_y = SASImage.getBindListDataFromHeader(raw_settings, img_hdr, hdrfile_info, keys = ['Beam X Center', 'Beam Y Center'])

                if x_y[0] is not None: x_c = x_y[0]
                if x_y[1] is not None: y_c = x_y[1]
            except ValueError:
                pass
            except TypeError:
                raise SASExceptions.HeaderLoadError('Error loading header, file corrupt?')

        # ********************
        # If the file is a SAXSLAB file, then get mask parameters from the header and modify the mask
        # then apply it...
        #
        # Mask should be not be changed, but should be created here. If no mask information is found, then
        # use the user created mask. There should be a force user mask setting.
        #
        # ********************

        masks = raw_settings.get('Masks')

        use_hdr_mask = raw_settings.get('UseHeaderForMask')

        if use_hdr_mask and img_fmt == 'SAXSLab300':
            try:
                mask_patches = SASImage.createMaskFromHdr(img, img_hdr, flipped = raw_settings.get('DetectorFlipped90'))
                bs_mask_patches = masks['BeamStopMask'][1]

                if bs_mask_patches is not None:
                    all_mask_patches = mask_patches + bs_mask_patches
                else:
                    all_mask_patches = mask_patches

                bs_mask = SASImage.createMaskMatrix(img.shape, all_mask_patches)
            except KeyError:
                raise SASExceptions.HeaderMaskLoadError('bsmask_configuration not found in header.')

            dc_mask = masks['ReadOutNoiseMask'][0]
        else:
            bs_mask = masks['BeamStopMask'][0]
            dc_mask = masks['ReadOutNoiseMask'][0]


        tbs_mask = masks['TransparentBSMask'][0]

        # ********* WARNING WARNING WARNING ****************#
        # Hmm.. axes start from the lower left, but array coords starts
        # from upper left:
        #####################################################
        y_c = img.shape[0]-y_c

        if not RAWGlobals.usepyFAI_integration:
            # print 'Using standard RAW integration'
            ## Flatfield correction.. this part gets moved to a image correction function later
            if raw_settings.get('NormFlatfieldEnabled'):
                if flatfield_filename is not None:
                    img, img_hdr = SASImage.doFlatfieldCorrection(img, img_hdr, flatfield_img, flatfield_hdr)
                else:
                    pass #Raise some error

            dezingering = raw_settings.get('ZingerRemovalRadAvg')
            dezing_sensitivity = raw_settings.get('ZingerRemovalRadAvgStd')

            sasm = createSASMFromImage(img, parameters, x_c, y_c, bs_mask, dc_mask, tbs_mask, dezingering, dezing_sensitivity)

        else:
            sasm = SASImage.pyFAIIntegrateCalibrateNormalize(img, parameters, x_c, y_c, raw_settings, bs_mask, tbs_mask)

        sasm_list[i] = sasm


    return sasm_list, loaded_data


def loadOutFile(filename):

    five_col_fit = re.compile('\s*\d*[.]\d*[+eE-]*\d+\s+-?\d*[.]\d*[+eE-]*\d+\s+\d*[.]\d*[+eE-]*\d+\s+\d*[.]\d*[+eE-]*\d+\s+\d*[.]\d*[+eE-]*\d+\s*$')
    three_col_fit = re.compile('\s*\d*[.]\d*[+eE-]*\d+\s+-?\d*[.]\d*[+eE-]*\d+\s+\d*[.]\d*[+eE-]*\d+\s*$')
    two_col_fit = re.compile('\s*\d*[.]\d*[+eE-]*\d+\s+-?\d*[.]\d*[+eE-]*\d+\s*$')

    results_fit = re.compile('\s*Current\s+\d*[.]\d*[+eE-]*\d*\s+\d*[.]\d*[+eE-]*\d*\s+\d*[.]\d*[+eE-]*\d*\s+\d*[.]\d*[+eE-]*\d*\s+\d*[.]\d*[+eE-]*\d*\s+\d*[.]\d*[+eE-]*\d*\s*\d*[.]?\d*[+eE-]*\d*\s*$')

    te_fit = re.compile('\s*Total\s+[Ee]stimate\s*:\s+\d*[.]\d+\s*\(?[A-Za-z\s]+\)?\s*$')
    te_num_fit = re.compile('\d*[.]\d+')
    te_quality_fit = re.compile('[Aa][A-Za-z\s]+\)?\s*$')

    p_rg_fit = re.compile('\s*Real\s+space\s*\:?\s*Rg\:?\s*\=?\s*\d*[.]\d+[+eE-]*\d*\s*\+-\s*\d*[.]\d+[+eE-]*\d*')
    q_rg_fit = re.compile('\s*Reciprocal\s+space\s*\:?\s*Rg\:?\s*\=?\s*\d*[.]\d+[+eE-]*\d*\s*')

    p_i0_fit = re.compile('\s*Real\s+space\s*\:?[A-Za-z0-9\s\.,+-=]*\(0\)\:?\s*\=?\s*\d*[.]\d+[+eE-]*\d*\s*\+-\s*\d*[.]\d+[+eE-]*\d*')
    q_i0_fit = re.compile('\s*Reciprocal\s+space\s*\:?[A-Za-z0-9\s\.,+-=]*\(0\)\:?\s*\=?\s*\d*[.]\d+[+eE-]*\d*\s*')

    alpha_fit = re.compile('\s*Current\s+ALPHA\s*\:?\s*\=?\s*\d*[.]\d+[+eE-]*\d*\s*')

    qfull = []
    qshort = []
    Jexp = []
    Jerr  = []
    Jreg = []
    Ireg = []

    R = []
    P = []
    Perr = []

    outfile = []

    #In case it returns NaN for either value, and they don't get picked up in the regular expression
    q_rg=None         #Reciprocal space Rg
    q_i0=None         #Reciprocal space I0


    with open(filename, 'rU') as f:
        for line in f:
            twocol_match = two_col_fit.match(line)
            threecol_match = three_col_fit.match(line)
            fivecol_match = five_col_fit.match(line)
            results_match = results_fit.match(line)
            te_match = te_fit.match(line)
            p_rg_match = p_rg_fit.match(line)
            q_rg_match = q_rg_fit.match(line)
            p_i0_match = p_i0_fit.match(line)
            q_i0_match = q_i0_fit.match(line)
            alpha_match = alpha_fit.match(line)

            outfile.append(line)

            if twocol_match:
                # print line
                found = twocol_match.group().split()

                qfull.append(float(found[0]))
                Ireg.append(float(found[1]))

            elif threecol_match:
                #print line
                found = threecol_match.group().split()

                R.append(float(found[0]))
                P.append(float(found[1]))
                Perr.append(float(found[2]))

            elif fivecol_match:
                #print line
                found = fivecol_match.group().split()

                qfull.append(float(found[0]))
                qshort.append(float(found[0]))
                Jexp.append(float(found[1]))
                Jerr.append(float(found[2]))
                Jreg.append(float(found[3]))
                Ireg.append(float(found[4]))

            elif results_match:
                found = results_match.group().split()
                Actual_DISCRP = float(found[1])
                Actual_OSCILL = float(found[2])
                Actual_STABIL = float(found[3])
                Actual_SYSDEV = float(found[4])
                Actual_POSITV = float(found[5])
                Actual_VALCEN = float(found[6])

                if len(found) == 8:
                    Actual_SMOOTH = float(found[7])
                else:
                    Actual_SMOOTH = -1

            elif te_match:
                te_num_search = te_num_fit.search(line)
                te_quality_search = te_quality_fit.search(line)

                TE_out = float(te_num_search.group().strip())
                quality = te_quality_search.group().strip().rstrip(')').strip()


            if p_rg_match:
                found = p_rg_match.group().split()
                try:
                    rg = float(found[-3])
                except:
                    rg = float(found[-2])
                try:
                    rger = float(found[-1])
                except:
                    rger = float(found[-1].strip('+-'))

            elif q_rg_match:
                found = q_rg_match.group().split()
                q_rg = float(found[-1])

            if p_i0_match:
                found = p_i0_match.group().split()
                i0 = float(found[-3])
                i0er = float(found[-1])

            elif q_i0_match:
                found = q_i0_match.group().split()
                q_i0 = float(found[-1])

            if alpha_match:
                found = alpha_match.group().split()
                alpha = float(found[-1])

    # Output variables not in the results file:
    #             'r'         : R,            #R, note R[-1] == Dmax
    #             'p'         : P,            #P(r)
    #             'perr'      : Perr,         #P(r) error
    #             'qlong'     : qfull,        #q down to q=0
    #             'qexp'      : qshort,       #experimental q range
    #             'jexp'      : Jexp,         #Experimental intensities
    #             'jerr'      : Jerr,         #Experimental errors
    #             'jreg'      : Jreg,         #Experimental intensities from P(r)
    #             'ireg'      : Ireg,         #Experimental intensities extrapolated to q=0

    name = os.path.basename(filename)

    chisq = np.sum(np.square(np.array(Jexp)-np.array(Jreg))/np.square(Jerr))/(len(Jexp)-1) #DOF normalied chi squared

    results = { 'dmax'      : R[-1],        #Dmax
                'TE'        : TE_out,       #Total estimate
                'rg'        : rg,           #Real space Rg
                'rger'      : rger,         #Real space rg error
                'i0'        : i0,           #Real space I0
                'i0er'      : i0er,         #Real space I0 error
                'q_rg'      : q_rg,         #Reciprocal space Rg
                'q_i0'      : q_i0,         #Reciprocal space I0
                'out'       : outfile,      #Full contents of the outfile, for writing later
                'quality'   : quality,      #Quality of GNOM out file
                'discrp'    : Actual_DISCRP,#DISCRIP, kind of chi squared (normalized by number of points, with a regularization parameter thing thrown in)
                'oscil'     : Actual_OSCILL,#Oscillation of solution
                'stabil'    : Actual_STABIL,#Stability of solution
                'sysdev'    : Actual_SYSDEV,#Systematic deviation of solution
                'positv'    : Actual_POSITV,#Relative norm of the positive part of P(r)
                'valcen'    : Actual_VALCEN,#Validity of the chosen interval in real space
                'smooth'    : Actual_SMOOTH,#Smoothness of the chosen interval? -1 indicates no real value, for versions of GNOM < 5.0 (ATSAS <2.8)
                'filename'  : name,         #GNOM filename
                'algorithm' : 'GNOM',       #Lets us know what algorithm was used to find the IFT
                'chisq'     : chisq,        #Actual chi squared value
                'alpha'     : alpha,        #Alpha used for the IFT
                    }

    iftm = SASM.IFTM(P, R, Perr, Jexp, qshort, Jerr, Jreg, results, Ireg, qfull)

    return [iftm]


def loadSeriesFile(filename, settings):
    file = open(filename, 'r')

    try:
        secm_data = cPickle.load(file)
    except (ImportError, EOFError), e:
        print e
        # print 'Error loading wsp file, trying different method.'
        file.close()
        file = open(filename, 'rb')
        secm_data = cPickle.load(file)
    finally:
        file.close()

    new_secm, line_data, calc_line_data = makeSeriesFile(secm_data, settings)

    new_secm.setParameter('filename', os.path.split(filename)[1])

    return new_secm


def makeSeriesFile(secm_data, settings):

    default_dict =     {'sasm_list'             : [],
                        'file_list'             : [],
                        'frame_list'            : [],
                        'parameters'            : {},
                        'window_size'           : -1,
                        'mol_type'              : '',
                        'threshold'             : -1,
                        'rg'                    : [],
                        'rger'                  : [],
                        'i0'                    : [],
                        'i0er'                  : [],
                        'calc_has_data'         : False,
                        'subtracted_sasm_list'  : [],
                        'use_subtracted_sasm'   : [],
                        'average_buffer_sasm'   : None,
                        'mol_density'           : -1,
                        'already_subtracted'    : False,
                        'baseline_subtracted_sasm_list' : [],
                        'use_baseline_subtracted_sasm' : [],
                        'buffer_range'          : [],
                        'sample_range'          : [],
                        'baseline_start_range'  : (-1, -1),
                        'baseline_end_range'    : (-1, -1),
                        'baseline_corr'         : [],
                        'baseline_type'         : '',
                        'baseline_extrap'       : True,
                        'baseline_fit_results'  : [],
                        }

    for key in default_dict:
        if key not in secm_data:
            secm_data[key] = default_dict[key]

    sasm_list = []

    for item in secm_data['sasm_list']:
        sasm_data = item

        new_sasm = SASM.SASM(sasm_data['i_raw'], sasm_data['q_raw'], sasm_data['err_raw'], sasm_data['parameters'])
        new_sasm.setBinnedI(sasm_data['i_binned'])
        new_sasm.setBinnedQ(sasm_data['q_binned'])
        new_sasm.setBinnedErr(sasm_data['err_binned'])

        new_sasm.setScaleValues(sasm_data['scale_factor'], sasm_data['offset_value'],
                                sasm_data['norm_factor'], sasm_data['q_scale_factor'],
                                sasm_data['bin_size'])

        new_sasm.setQrange(sasm_data['selected_qrange'])

        try:
            new_sasm.setParameter('analysis', sasm_data['parameters_analysis'])
        except KeyError:
            pass

        new_sasm._update()

        sasm_list.append(new_sasm)


    new_secm = SASM.SECM(secm_data['file_list'], sasm_list,
        secm_data['frame_list'], secm_data['parameters'], settings)

    new_secm.window_size = secm_data['window_size']
    new_secm.mol_type = secm_data['mol_type']
    new_secm.calc_has_data = secm_data['calc_has_data']
    new_secm.mol_density = secm_data['mol_density']
    new_secm.already_subtracted = secm_data['already_subtracted']
    new_secm.sample_range = secm_data['sample_range']

    if 'intial_buffer_frame' in secm_data:     #Old style secm, complete with typo!
        if secm_data['intial_buffer_frame'] != -1:
            new_secm.buffer_range = [(secm_data['intial_buffer_frame'],
                secm_data['final_buffer_frame'])]
    else:
        new_secm.buffer_range = secm_data['buffer_range']

    if 'mw' in secm_data:       #Old style secm
        new_secm.setCalcValues(secm_data['rg'], secm_data['rger'], secm_data['i0'],
            secm_data['i0er'], secm_data['mw'], secm_data['mwer'],
            np.zeros_like(secm_data['mw'])-1)
    else:
        new_secm.setCalcValues(secm_data['rg'], secm_data['rger'], secm_data['i0'],
            secm_data['i0er'], secm_data['vcmw'], secm_data['vcmwer'],
            secm_data['vpmw'])


    subtracted_sasm_list = []

    for item in secm_data['subtracted_sasm_list']:
        sasm_data = item

        if sasm_data != -1:
            new_sasm = SASM.SASM(sasm_data['i_raw'], sasm_data['q_raw'],
                sasm_data['err_raw'], sasm_data['parameters'])
            new_sasm.setBinnedI(sasm_data['i_binned'])
            new_sasm.setBinnedQ(sasm_data['q_binned'])
            new_sasm.setBinnedErr(sasm_data['err_binned'])

            new_sasm.setScaleValues(sasm_data['scale_factor'], sasm_data['offset_value'],
                                    sasm_data['norm_factor'], sasm_data['q_scale_factor'],
                                    sasm_data['bin_size'])

            new_sasm.setQrange(sasm_data['selected_qrange'])

            try:
                new_sasm.setParameter('analysis', sasm_data['parameters_analysis'])
            except KeyError:
                pass

            new_sasm._update()
        else:
            new_sasm = -1

        subtracted_sasm_list.append(new_sasm)

    new_secm.setSubtractedSASMs(subtracted_sasm_list, secm_data['use_subtracted_sasm'])

    new_secm.baseline_start_range = secm_data['baseline_start_range']
    new_secm.baseline_end_range = secm_data['baseline_end_range']
    new_secm.baseline_type = secm_data['baseline_type']
    new_secm.baseline_extrap = secm_data['baseline_extrap']
    new_secm.baseline_fit_results = secm_data['baseline_fit_results']

    baseline_subtracted_sasm_list = []

    for item in secm_data['baseline_subtracted_sasm_list']:
        sasm_data = item

        if sasm_data != -1:
            new_sasm = SASM.SASM(sasm_data['i_raw'], sasm_data['q_raw'], sasm_data['err_raw'], sasm_data['parameters'])
            new_sasm.setBinnedI(sasm_data['i_binned'])
            new_sasm.setBinnedQ(sasm_data['q_binned'])
            new_sasm.setBinnedErr(sasm_data['err_binned'])

            new_sasm.setScaleValues(sasm_data['scale_factor'], sasm_data['offset_value'],
                                    sasm_data['norm_factor'], sasm_data['q_scale_factor'],
                                    sasm_data['bin_size'])

            new_sasm.setQrange(sasm_data['selected_qrange'])

            try:
                new_sasm.setParameter('analysis', sasm_data['parameters_analysis'])
            except KeyError:
                pass

            new_sasm._update()
        else:
            new_sasm = -1

        baseline_subtracted_sasm_list.append(new_sasm)

    new_secm.setBCSubtractedSASMs(baseline_subtracted_sasm_list, secm_data['use_baseline_subtracted_sasm'])

    baseline_corr = []

    for item in secm_data['baseline_corr']:
        sasm_data = item

        if sasm_data != -1:
            new_sasm = SASM.SASM(sasm_data['i_raw'], sasm_data['q_raw'], sasm_data['err_raw'], sasm_data['parameters'])
            new_sasm.setBinnedI(sasm_data['i_binned'])
            new_sasm.setBinnedQ(sasm_data['q_binned'])
            new_sasm.setBinnedErr(sasm_data['err_binned'])

            new_sasm.setScaleValues(sasm_data['scale_factor'], sasm_data['offset_value'],
                                    sasm_data['norm_factor'], sasm_data['q_scale_factor'],
                                    sasm_data['bin_size'])

            new_sasm.setQrange(sasm_data['selected_qrange'])

            try:
                new_sasm.setParameter('analysis', sasm_data['parameters_analysis'])
            except KeyError:
                pass

            new_sasm._update()
        else:
            new_sasm = -1

        baseline_corr.append(new_sasm)

    new_secm.baseline_corr = baseline_corr


    sasm_data = secm_data['average_buffer_sasm']

    if sasm_data != -1 and sasm_data is not None:
        new_sasm = SASM.SASM(sasm_data['i_raw'], sasm_data['q_raw'],
            sasm_data['err_raw'], sasm_data['parameters'])
        new_sasm.setBinnedI(sasm_data['i_binned'])
        new_sasm.setBinnedQ(sasm_data['q_binned'])
        new_sasm.setBinnedErr(sasm_data['err_binned'])

        new_sasm.setScaleValues(sasm_data['scale_factor'], sasm_data['offset_value'],
                                sasm_data['norm_factor'], sasm_data['q_scale_factor'],
                                sasm_data['bin_size'])

        new_sasm.setQrange(sasm_data['selected_qrange'])

        try:
            new_sasm.setParameter('analysis', sasm_data['parameters_analysis'])
        except KeyError:
            pass

        new_sasm._update()
    else:
        new_sasm = -1

    new_secm.average_buffer_sasm = new_sasm


    try:
        line_data = {'line_color' : secm_data['line_color'],
                     'line_width' : secm_data['line_width'],
                     'line_style' : secm_data['line_style'],
                     'line_marker': secm_data['line_marker'],
                     'line_visible' :secm_data['line_visible']}

        calc_line_data = {'line_color' : secm_data['calc_line_color'],
                     'line_width' : secm_data['calc_line_width'],
                     'line_style' : secm_data['calc_line_style'],
                     'line_marker': secm_data['calc_line_marker'],
                     'line_visible' :secm_data['calc_line_visible']}

        try:
            line_data['line_marker_face_color'] = secm_data['line_marker_face_color']
            line_data['line_marker_edge_color'] = secm_data['line_marker_edge_color']

            calc_line_data['line_marker_face_color'] = secm_data['calc_line_marker_face_color']
            calc_line_data['line_marker_edge_color'] = secm_data['calc_line_marker_edge_color']
        except KeyError:
            pass #Version <1.3.0 doesn't have these keys

    except KeyError:
        line_data = None    #Backwards compatibility
        calc_line_data = None

    return new_secm, line_data, calc_line_data


def loadIftFile(filename):
    #Loads RAW BIFT .ift files into IFTM objects
    iq_pattern = re.compile('\s*\d*[.]\d*[+eE-]*\d+\s+-?\d*[.]\d*[+eE-]*\d+\s+\d*[.]\d*[+eE-]*\d+\s+\d*[.]\d*[+eE-]*\d+\s*$')
    pr_pattern = re.compile('\s*\d*[.]\d*[+eE-]*\d+\s+-?\d*[.]\d*[+eE-]*\d+\s+\d*[.]\d*[+eE-]*\d+\s*$')
    extrap_pattern = re.compile('\s*\d*[.]\d*[+eE-]*\d+\s+-?\d*[.]\d*[+eE-]*\d+\s*$')

    r = []
    p = []
    err = []

    q = []
    i = []
    err_orig = []
    fit = []

    q_extrap = []
    fit_extrap = []

    with open(filename, 'rU') as f:

        path_noext, ext = os.path.splitext(filename)

        for line in f:

            pr_match = pr_pattern.match(line)
            iq_match = iq_pattern.match(line)
            extrap_match = extrap_pattern.match(line)

            if pr_match:
                found = pr_match.group().split()

                r.append(float(found[0]))
                p.append(float(found[1]))
                err.append(float(found[2]))

            elif iq_match:
                found = iq_match.group().split()

                q.append(float(found[0]))
                i.append(float(found[1]))
                err_orig.append(float(found[2]))
                fit.append(float(found[3]))

            elif extrap_match:
                found = extrap_match.group().split()

                q_extrap.append(float(found[0]))
                fit_extrap.append(float(found[1]))

    p = np.array(p)
    r = np.array(r)
    err = np.array(err)
    i = np.array(i)
    q = np.array(q)
    err_orig = np.array(err_orig)
    fit = np.array(fit)
    q_extrap = np.array(q_extrap)
    fit_extrap = np.array(fit_extrap)


    #Check to see if there is any header from RAW, and if so get that.
    with open(filename, 'rU') as f:
        all_lines = f.readlines()

    header = []
    for j in range(len(all_lines)):
        if '### HEADER:' in all_lines[j]:
            header = all_lines[j+1:]

    hdict = {}

    if len(header)>0:
        hdr_str = ''
        for each_line in header:
            hdr_str=hdr_str+each_line.lstrip('#')
        try:
            hdict = dict(json.loads(hdr_str))
        except Exception:
            pass

    parameters = hdict
    parameters['filename'] = os.path.split(filename)[1]

    if q.size == 0:
        q = np.array([0, 0])
        i = q
        err_orig = q
        fit = q

    if q_extrap.size == 0:
        q_extrap = q
        fit_extrap = fit

    iftm = SASM.IFTM(p, r, err, i, q, err_orig, fit, parameters, fit_extrap, q_extrap)

    return [iftm]


def loadFitFile(filename):

    iq_pattern = re.compile('\s*-?\d*[.]\d*[+eE-]*\d+\s+-?\d*[.]\d*[+eE-]*\d+\s+-?\d*[.]\d*[+eE-]*\d+\s+-?\d*[.]\d*[+eE-]*\d+\s*$')
    three_col_fit = re.compile('\s*-?\d*[.]\d*[+eE-]*\d+\s+-?\d*[.]\d*[+eE-]*\d+\s+-?\d*[.]\d*[+eE-]*\d+\s*$')
    five_col_fit = re.compile('\s*-?\d*[.]\d*[+eE-]*\d+\s+-?\d*[.]\d*[+eE-]*\d+\s+-?\d*[.]\d*[+eE-]*\d+\s+-?\d*[.]\d*[+eE-]*\d+\s+-?\d*[.]\d*[+eE-]*\d+\s*$')

    i = []
    q = []
    err = []
    fit = []

    with open(filename, 'rU') as f:

        firstLine = f.readline()

        three_col_match = three_col_fit.match(firstLine)
        if three_col_match:
            fileHeader = {}
        else:
            fileHeader = {'comment':firstLine}
            if 'Chi^2' in firstLine:
                chisq = firstLine.split('Chi^2')[-1].strip('= ').strip()
                fileHeader['Chi_squared'] = chisq


        if "Experimental" in firstLine:
            sasref = True      #SASREFMX Fit file (Damn those hamburg boys and their 50 different formats!)
        else:
            sasref = False

        parameters = {'filename' : os.path.split(filename)[1],
                      'counters' : fileHeader}

        path_noext, ext = os.path.splitext(filename)

        fit_parameters = {'filename'  : os.path.split(path_noext)[1] + '_FIT',
                          'counters' : {}}

        for line in f:

            three_col_match = three_col_fit.match(line)
            five_col_match = five_col_fit.match(line)

            if three_col_match:
                iq_match = three_col_fit.match(line)

                if iq_match:

                    if not sasref:
                        found = iq_match.group().split()
                        q.append(float(found[0]))
                        i.append(float(found[1]))
                        fit.append(float(found[2]))

                        err = np.ones(len(i))
                    else: #SASREF fit file
                        found = line.split()
                        q.append(float(found[0]))
                        i.append(float(found[1]))
                        fit.append(float(found[3]))
                        err.append(float(found[2]))

            elif five_col_match:
                #iq_match = five_col_fit.match(line)
                found = line.split()
                q.append(float(found[0]))
                i.append(float(found[1]))
                fit.append(float(found[2]))
                err.append(float(found[3]))

            else:

                iq_match = iq_pattern.match(line)

                if iq_match:
                    found = iq_match.group().split()
                    q.append(float(found[0]))
                    i.append(float(found[1]))
                    err.append(float(found[2]))
                    fit.append(float(found[3]))


    if len(i) == 0:
        raise SASExceptions.UnrecognizedDataFormat('No data could be retrieved from the file, unknown format.')

    i = np.array(i)
    q = np.array(q)
    err = np.array(err)
    fit = np.array(fit)


    fit_sasm = SASM.SASM(fit, np.copy(q), np.copy(err), fit_parameters)

    sasm = SASM.SASM(i, q, err, parameters)

    return [sasm, fit_sasm]

def loadDamselLogFile(filename):
    """Loads data from a damsel log file"""
    res_pattern = re.compile('\s*Ensemble\s*Resolution\s*=?\s*\d+\.?\d*\s*\+?-?\s*\d+\s*[a-zA-Z]*')

    with open(filename, 'rU') as f:
        process_includes = False
        result_dict = {}
        include_list = []
        discard_list = []
        res = ''
        res_err = ''
        res_unit = ''

        for line in f:
            res_match = res_pattern.match(line)

            if process_includes:
                if len(line.strip()) > 0:
                    rec, nsd, fname = line.strip().split()
                    result_dict[fname] = [rec.strip(), nsd.strip()]

                    if rec == 'Include':
                        include_list.append([fname, rec, nsd])
                    else:
                        discard_list.append([fname, rec, nsd])

            if 'Mean' in line and 'Standard' not in line:
                mean_nsd = line.strip().split()[-1]
            elif 'Mean' not in line and 'Standard' in line:
                stdev_nsd = line.strip().split()[-1]
            elif 'Recommendation' in line:
                process_includes = True
            elif res_match:
                if '+-' in line:
                    part1, part2 = line.strip().split('+-')
                    res = part1.strip().split()[-1]
                    res_err = part2.strip().split()[0]

                    if part2.strip().split()[-1].isalpha():
                        res_unit = part2.strip().split()[-1]

    return mean_nsd, stdev_nsd, include_list, discard_list, result_dict, res, res_err, res_unit

def loadDamsupLogFile(filename):
    model_data = []
    representative_model = ''

    with open(filename, 'rU') as f:
        for line in f:
            results = line.strip().split()

            try:
                nsd = float(results[0])
            except Exception:
                nsd = -1

            if nsd >= 0:
                model_data.append([nsd, results[1]])

            if nsd == 0:
                representative_model = results[1]

    return model_data, representative_model

def loadDamclustLogFile(filename):
    """Loads data from a damclust log file"""
    cluster_pattern = re.compile('\s*Cluster\s*\d')
    distance_pattern = re.compile('\s*\d\s*\d\s*\d+[.]\d+\s*$')

    cluster_tuple = collections.namedtuple('Clusters', ['num', 'rep_model', 'dev'])
    distance_tuple = collections.namedtuple('Distances', ['cluster1', 'cluster2', 'cluster_dist'])

    cluster_list = []
    distance_list = []

    with open(filename, 'rU') as f:
        for line in f:
            cluster_match = cluster_pattern.match(line)
            distance_match = distance_pattern.match(line)

            if cluster_match:
                found = line.split()
                if '.pdb' in found[-1]:
                    isolated = True
                else:
                    isolated = False

                cluster_num = found[1].strip()

                if isolated:
                    rep_model = found[-1].strip()
                    cluster_dev = -1
                else:
                    cluster_dev = found[-1].strip()
                    rep_model = found[-2].strip()

                cluster_list.append(cluster_tuple(cluster_num, rep_model, cluster_dev))

            elif distance_match:
                found = distance_match.group().split()
                distance_list.append(distance_tuple(*found))

    return cluster_list, distance_list

def loadPDBFile(filename):
    """
    Read the PDB file,
    extract coordinates of each dummy atom,
    extract the R-factor of the model, coordinates of each dummy atom and pdb file header.

    :param filename: name of the pdb file to read

    This code was modified from the fresas package (https://github.com/kif/freesas)
    Original license information:
    __author__ = "Guillaume"
    __license__ = "MIT"
    __copyright__ = "2015, ESRF"
    """
    header = []
    atoms = []
    useful_params = collections.defaultdict(str)

    for line in open(filename, 'rU'):
        if line.startswith("ATOM"):
            x = float(line[30:38])
            y = float(line[38:46])
            z = float(line[46:54])
            atoms.append([x, y, z])
        elif not line.startswith("TER"):
            header.append(line)
            if 'atom radius' in line.lower() or 'packing radius' in line.lower() or 'atomic radius' in line.lower():
                useful_params['atom_radius'] = str(float(line.split(':')[-1].strip()))
            elif 'excluded dam volume' in line.lower() or 'average excluded volume' in line.lower():
                useful_params['excluded_volume'] = str(float(line.split(':')[-1].strip()))
            elif 'filtered volume' in line.lower():
                useful_params['excluded_volume'] = str(float(line.split(':')[-1].strip()))
            elif 'maximum diameter' in line.lower() or 'maximum phase diameter' in line.lower():
                useful_params['dmax'] = str(float(line.split(':')[-1].strip()))
            elif 'radius of gyration' in line.lower():
                useful_params['rg'] = str(float(line.split(':')[-1].strip()))

    if 'excluded_volume' in useful_params:
        useful_params['mw'] = str(round(float(useful_params['excluded_volume'])/1.66/1000.,2))

    return np.array(atoms), header, useful_params


def loadPrimusDatFile(filename):
    ''' Loads a Primus .dat format file '''

    iq_pattern = re.compile('\s*\d*[.]\d*[+eE-]*\d+\s+-?\d*[.]\d*[+eE-]*\d+\s+\d*[.]\d*[+eE-]*\d+\s*')

    i = []
    q = []
    err = []

    with open(filename, 'rU') as f:
        lines = f.readlines()

    if len(lines) == 0:
        raise SASExceptions.UnrecognizedDataFormat('No data could be retrieved from the file.')

    comment = ''
    line = lines[0]
    j=0
    while line.split() and line.split()[0].strip()[0] == '#':
        comment = comment+line
        j = j+1
        line = lines[j]

    fileHeader = {'comment':comment}
    parameters = {'filename' : os.path.split(filename)[1],
                  'counters' : fileHeader}

    if comment.find('model_intensity') > -1:
        #FoXS file with a fit! has four data columns
        is_foxs_fit=True
        imodel = []
    else:
        is_foxs_fit = False

    for line in lines:
        iq_match = iq_pattern.match(line)

        if iq_match:
            if not is_foxs_fit:
                found = iq_match.group().split()
                q.append(float(found[0]))
                i.append(float(found[1]))
                err.append(float(found[2]))
            else:
                found = line.split()
                q.append(float(found[0]))
                i.append(float(found[1]))
                imodel.append(float(found[2]))
                err.append(float(found[3]))


    #Check to see if there is any header from RAW, and if so get that.
    header = []
    for j in range(len(lines)):
        if '### HEADER:' in lines[j]:
            header = lines[j+1:]

    hdict = None

    if len(header)>0:
        hdr_str = ''
        for each_line in header:
            hdr_str=hdr_str+each_line.lstrip('#')
        try:
            hdict = dict(json.loads(hdr_str))
            # print 'Loading RAW info/analysis...'
        except Exception:
            # print 'Unable to load header/analysis information. Maybe the file was not generated by RAW or was generated by an old version of RAW?'
            hdict = {}


    i = np.array(i)
    q = np.array(q)
    err = np.array(err)

    if hdict:
        hdict = translateHeader(hdict, to_sasbdb=False)
        for each in hdict.iterkeys():
            if each != 'filename':
                parameters[each] = hdict[each]

    sasm = SASM.SASM(i, q, err, parameters)

    if is_foxs_fit:
        parameters2 = copy.copy(parameters)
        parameters2['filename'] = os.path.splitext(os.path.split(filename)[1])[0]+'_FIT'

        sasm_model = SASM.SASM(imodel,q,err,parameters2)

        return [sasm, sasm_model]

    return sasm

def loadRadFile(filename):
    ''' NOTE : THIS IS THE OLD RAD FORMAT..     '''
    ''' Loads a .rad file into a SASM object and attaches the filename and header into the parameters  '''

    iq_pattern = re.compile('\s*\d*[.]\d*[+eE-]*\d+\s+-?\d*[.]\d*[+eE-]*\d+\s+\d*[.]\d*[+eE-]*\d+\s+-?\d*[.]\d*[+eE-]*\d+\s*\n')
    param_pattern = re.compile('[a-zA-Z0-9_]*\s*[:]\s+.*')

    i = []
    q = []
    err = []
    parameters = {'filename' : os.path.split(filename)[1]}

    fileheader = {}

    with open(filename, 'rU') as f:

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


    parameters = {'filename' : os.path.split(filename)[1],
                  'fileHeader' : fileheader}

    i = np.array(i)
    q = np.array(q)
    err = np.array(err)

    return SASM.SASM(i, q, err, parameters)


def loadNewRadFile(filename):
    ''' NOTE : This is a load function for the new rad format '''
    ''' Loads a .rad file into a SASM object and attaches the filename and header into the parameters  '''

    iq_pattern = re.compile('\s*\d*[.]\d*[+eE-]*\d+\s+-?\d*[.]\d*[+eE-]*\d+\s+-?\d*[.]\d*[+eE-]*\d+\s*\n')
    param_pattern = re.compile('[a-zA-Z0-9_]*\s*[:]\s+.*')

    i = []
    q = []
    err = []
    parameters = {'filename' : os.path.split(filename)[1]}

    fileheader = {}

    with open(filename, 'rU') as f:

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


    parameters = {'filename' : os.path.split(filename)[1],
                  'counters' : fileheader}

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

    with open(filename, 'rU') as f:
        all_lines = f.readlines()

    for each_line in all_lines:
        split_line = each_line.split()

        if len(split_line) == 5:
            q.append(float(split_line[0]))
            i.append(float(split_line[1]))

    i = np.array(i)
    q = np.array(q)
    err = np.sqrt(abs(i))

    return SASM.SASM(i, q, err, parameters)


def loadCsvFile(filename):
    ''' Loads a comma separated file, ignores everything except a three column line'''


    iq_pattern = re.compile('\s*\d*[.]?\d*[+eE-]*\d+[,]\s*-?\d*[.]?\d*[+eE-]*\d+[,]\s*-?\d*[.]?\d*[+eE-]*\d*\s*')
    param_pattern = re.compile('[a-zA-Z0-9_]*\s*[=].*')

    i = []
    q = []
    err = []

    fileheader = {}

    with open(filename, 'rU') as f:

        for line in f:

            iq_match = iq_pattern.match(line)
            param_match = param_pattern.match(line)

            if iq_match:
                found = iq_match.group().split(',')

                q.append(float(found[0].rstrip('\r\n')))

                i.append(float(found[1].rstrip('\r\n')))

                err.append(float(found[2].rstrip('\r\n')))

            elif param_match:
                found = param_match.group().split('=')

                if len(found) == 2:
                    try:
                        val = float(found[1].rstrip('\r\n'))
                    except ValueError:
                        val = found[1].rstrip('\r\n')

                    fileheader[found[0]] = val


    parameters = {'filename' : os.path.split(filename)[1],
                  'counters' : fileheader}

    return SASM.SASM(i, q, err, parameters)



def load2ColFile(filename):
    ''' Loads a two column file (q I) separated by whitespaces '''

    iq_pattern = re.compile('\s*\d*[.]\d*\s+-?\d*[.]\d*.*\n')
    param_pattern = re.compile('[a-zA-Z0-9_]*\s*[=].*')

    i = []
    q = []
    err = []
    fileheader = {}

    with open(filename, 'rU') as f:

        for line in f:
            iq_match = iq_pattern.match(line)
            param_match = param_pattern.match(line)

            if iq_match:
                found = iq_match.group().split()
                q.append(float(found[0]))
                i.append(float(found[1]))

            elif param_match:
                found = param_match.group().split('=')

                if len(found) == 2:
                    try:
                        val = float(found[1].rstrip('\r\n'))
                    except ValueError:
                        val = found[1].rstrip('\r\n')

                    fileheader[found[0]] = val
#

    i = np.array(i)
    q = np.array(q)
    err = np.sqrt(abs(i))

    parameters = {'filename' : os.path.split(filename)[1],
                  'counters' : fileheader}

    return SASM.SASM(i, q, err, parameters)




#####################################
#--- ## Write RAW Generated Files: ##
#####################################

# WORK IN PROGRESS:
def saveMeasurement(sasm, save_path, raw_settings, filetype = '.dat'):
    ''' Saves a Measurement Object to a .rad file.
        Returns the filename of the saved file '''

    if type(sasm) != list:
        sasm = [sasm]

    for each_sasm in sasm:
        filename, ext = os.path.splitext(each_sasm.getParameter('filename'))

        header_on_top = raw_settings.get('DatHeaderOnTop')

        if filetype == '.ift':
            try:
                writeIftFile(each_sasm, os.path.join(save_path, filename + filetype))
            except TypeError as e:
                print 'Error in saveMeasurement, type: %s, error: %s' %(type(e).__name__, e)
                print 'Resaving file without header'
                print each_sasm.getAllParameters()
                writeIftFile(each_sasm, os.path.join(save_path, filename + filetype), False)

                raise SASExceptions.HeaderSaveError(e)
        elif filetype == '.out':
            writeOutFile(each_sasm, os.path.join(save_path, filename + filetype))
        else:
            try:
                writeRadFile(each_sasm, os.path.join(save_path, filename + filetype), header_on_top)
            except TypeError as e:
                print 'Error in saveMeasurement, type: %s, error: %s' %(type(e).__name__, e)
                print 'Resaving file without header'
                print each_sasm.getAllParameters()
                writeRadFile(each_sasm, os.path.join(save_path, filename + filetype), header_on_top, False)

                raise SASExceptions.HeaderSaveError(e)


def saveSECItem(save_path, secm_dict):

    with open(save_path, 'wb') as f:
        cPickle.dump(secm_dict, f, cPickle.HIGHEST_PROTOCOL)


def saveAnalysisCsvFile(sasm_list, include_data, save_path):

    with open(save_path, 'w') as file:

        if len(sasm_list) == 0:
            return None

        date = time.ctime()

        #Write the first line in the csv:
        file.write('# RAW ANALYSIS DATA\n')
        file.write('# ' + str(date) + '\n')
        file.write('# Filename')

        all_included_keys = sorted(include_data.keys())

        for each_data in all_included_keys:
            var = include_data[each_data][0]
            key = include_data[each_data][1]
            try:
                key2 = include_data[each_data][2]
            except:
                key2=None

            if key2:
                line = ',' + str(key)+'_'+str(key2)
            else:
                line = ',' + str(key)
            file.write(line)

        file.write('\n')

        for each_sasm in sasm_list:

            parameters = each_sasm.getAllParameters()

            file.write(each_sasm.getParameter('filename'))

            for each_data in all_included_keys:
                var = include_data[each_data][0]
                key = include_data[each_data][1]
                try:
                    key2 = include_data[each_data][2]
                except:
                    key2=None

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

                elif var == 'molecularWeight':
                    if parameters.has_key('analysis'):
                        analysis_dict = each_sasm.getParameter('analysis')

                        if analysis_dict.has_key('molecularWeight'):
                            mw = analysis_dict['molecularWeight']

                            if mw.has_key(key):
                                file.write(str(mw[key][key2]))
                            else:
                                file.write(' ')
                        else:
                            file.write(' ')
                    else:
                        file.write(' ')

                elif var =='GNOM':
                    if parameters.has_key('analysis'):
                        analysis_dict = each_sasm.getParameter('analysis')

                        if analysis_dict.has_key('GNOM'):
                            gnom = analysis_dict['GNOM']

                            if gnom.has_key(key):
                                file.write(str(gnom[key]))
                            else:
                                file.write(' ')
                        else:
                            file.write(' ')
                    else:
                        file.write(' ')

                elif var == 'BIFT':
                    if parameters.has_key('analysis'):
                        analysis_dict = each_sasm.getParameter('analysis')

                        if analysis_dict.has_key('BIFT'):
                            bift = analysis_dict['BIFT']

                            if bift.has_key(key):
                                file.write(str(bift[key]))
                            else:
                                file.write(' ')
                        else:
                            file.write(' ')
                    else:
                        file.write(' ')


            file.write('\n')

    return True

def saveAllAnalysisData(save_path, sasm_list, delim=','):
    #Exports all analysis data from multiple sasm objects into delimited form. Default is space delimited
    with open(save_path, 'w') as f:

        date = time.ctime()

        #Write the first lines in the file:
        f.write('# RAW_ANALYSIS_DATA\n')
        f.write('# ' + str(date).replace(' ', '_') + '\n')
        header_list = ['Filename', 'Concentration']

        for sasm in sasm_list:
            analysis = sasm.getParameter('analysis')

            analysis_done = analysis.keys()

            if 'guinier' in analysis_done and 'Guinier_Rg' not in header_list:
                for key in sorted(analysis['guinier'].keys()):
                    header_list.append('Guinier_'+key)

            if 'molecularWeight' in analysis_done and 'VolumeOfCorrelation_MW_(kDa)' not in header_list:
                for key in sorted(analysis['molecularWeight'].keys()):
                    for subkey in sorted(analysis['molecularWeight'][key].keys()):
                        if subkey.endswith('MW'):
                            header_list.append(key+'_'+subkey+'_(kDa)')
                        elif subkey.endswith('VPorod') or subkey.endswith('VPorod_Corrected'):
                            header_list.append(key+'_'+subkey+'_(A^3)')
                        elif subkey.endswith('Vc'):
                            header_list.append(key+'_'+subkey+'_(A^2)')
                        else:
                            header_list.append(key+'_'+subkey)

            if 'GNOM' in analysis_done and 'GNOM_Dmax' not in header_list:
                for key in sorted(analysis['GNOM'].keys()):
                    header_list.append('GNOM_'+key)

            if 'BIFT' in analysis_done and 'BIFT_Dmax' not in header_list:
                for key in sorted(analysis['BIFT'].keys()):
                    header_list.append('BIFT_'+key)


        f.write('# ' + delim.join(header_list)+'\n')


        for sasm in sasm_list:
            analysis = sasm.getParameter('analysis')

            all_params = sasm.getAllParameters()

            analysis_done = analysis.keys()

            if 'guinier' in analysis_done:
                has_guinier = True
            else:
                has_guinier = False

            if 'molecularWeight' in analysis_done:
                has_mw = True
            else:
                has_mw = False

            if 'GNOM' in analysis_done:
                has_gnom = True
            else:
                has_gnom = False

            if 'BIFT' in analysis_done:
                has_bift = True
            else:
                has_bift = False

            data_list = []

            for header in header_list:
                if header == 'Filename':
                    data_list.append(sasm.getParameter('filename'))

                elif header == 'Concentration':
                    if 'Conc' in all_params.keys():
                        data_list.append(str(all_params['Conc']))
                    else:
                        data_list.append('')


                elif header.startswith('Guinier'):
                    temp = header.split('_')
                    if len(temp[1:])>1:
                        key = '_'.join(temp[1:])
                    else:
                        key = temp[1]

                    if has_guinier:
                        data_list.append(str(analysis['guinier'][key]))
                    else:
                        data_list.append('N/A')


                elif header.startswith('Absolute') or header.startswith('I(0)Concentration') or header.startswith('PorodVolume') or header.startswith('VolumeOfCorrelation'):
                    temp = header.split('_')
                    key1 = temp[0]
                    if len(temp[1:])>1:
                        if temp[-1].endswith(')'):
                            key2 = '_'.join(temp[1:-1])
                        else:
                            key2 = '_'.join(temp[1:])
                    else:
                        key2 = temp[1]

                    if has_mw:
                        data_list.append(str(analysis['molecularWeight'][key1][key2]))
                    else:
                        data_list.append('N/A')


                elif header.startswith('GNOM'):
                    temp = header.split('_')
                    if len(temp[1:])>1:
                        key = '_'.join(temp[1:])
                    else:
                        key = temp[1]

                    if has_gnom:
                        data_list.append(str(analysis['GNOM'][key]))
                    else:
                        data_list.append('N/A')


                elif header.startswith('BIFT'):
                    temp = header.split('_')
                    if len(temp[1:])>1:
                        key = '_'.join(temp[1:])
                    else:
                        key = temp[1]

                    if has_bift:
                        data_list.append(str(analysis['BIFT'][key]))
                    else:
                        data_list.append('N/A')


                else:
                    data_list.append('N/A')

            f.write(delim.join(data_list)+'\n')

def saveSeriesData(save_path, selected_secm, delim=','):
    #Exports the data from a SEC object into delimited form. Default is space delimited
    with open(save_path, 'w') as f:

        if selected_secm.qref != 0:
            saveq=True
        else:
            saveq=False

        if selected_secm.qrange[0] != 0 and selected_secm.qrange[1] != 0:
            save_qrange = True
        else:
            save_qrange = False

        time = selected_secm.getTime()

        if len(time)>0 and time[0] != -1 and len(time) == len(selected_secm.frame_list):
            savetime = True
        else:
            savetime = False

        savecalc = selected_secm.calc_has_data

        if selected_secm.subtracted_sasm_list:
            if selected_secm.already_subtracted:
                f.write('# Initial profiles were already subtracted\n')
            else:
                f.write('# Buffer range for subtraction:\n')
                for (r1, r2) in selected_secm.buffer_range:
                    f.write('#    {} to {}\n'.format(r1, r2))

            f.write('# Average window size: {}\n'.format(selected_secm.window_size))
            f.write('# Molecule type (Vc MW): {}\n'.format(selected_secm.mol_type))
            f.write('# Molecule density (Vp MW): {}\n#\n'.format(selected_secm.mol_density))

        if selected_secm.baseline_subtracted_sasm_list:
            f.write('# Baseline type: {}\n'.format(selected_secm.baseline_type))

            if selected_secm.baseline_type == 'Linear':
                f.write('# Extrapolate baseline to all frames: {}\n'.format(selected_secm.baseline_extrap))

            f.write('# Baseline start range: {} to {}\n'.format(selected_secm.baseline_start_range[0], selected_secm.baseline_start_range[1]))
            f.write('# Baseline end range: {} to {}\n#\n'.format(selected_secm.baseline_end_range[0], selected_secm.baseline_end_range[1]))

        f.write('#Frame_#%sIntegrated_Intensity%sMean_Intensity%s' %(delim, delim, delim))
        if saveq:
            f.write('I_at_q=%f%s' %(selected_secm.qref, delim))
        if save_qrange:
            f.write('I_from_q=%f_to_q=%f%s' %(selected_secm.qrange[0], selected_secm.qrange[1], delim))
        if selected_secm.subtracted_sasm_list:
            f.write('Subtracted_Integrated_Intensity%sSubtracted_Mean_Intensity%s' %(delim, delim))
            if saveq:
                f.write('Subtracted_I_at_q=%f%s' %(selected_secm.qref, delim))
            if save_qrange:
                f.write('Subtracted_I_from_q=%f_to_q=%f%s' %(selected_secm.qrange[0], selected_secm.qrange[1], delim))
        if selected_secm.baseline_subtracted_sasm_list:
            f.write('Baseline_Corrected_Integrated_Intensity%sBaseline_Corrected_Mean_Intensity%s' %(delim, delim))
            if saveq:
                f.write('Baseline_Corrected_I_at_q=%f%s' %(selected_secm.qref, delim))
            if save_qrange:
                f.write('Baseline_Corrected_I_from_q=%f_to_q=%f%s' %(selected_secm.qrange[0], selected_secm.qrange[1], delim))
        if savetime:
            f.write('Time_(s)%s' %(delim))
        if savecalc:
            f.write('Rg_(A)%sRger_(A)%sI0%sI0er%sMW_Vc_(kDa)%sMWer_Vc_(kDa)%sMW_Vp_(kDa)%s' %(delim, delim, delim, delim, delim, delim, delim))
        f.write('File_Name\n')

        for a in range(len(selected_secm._sasm_list)):
            f.write('%i%s%.8E%s%.8E%s' %(selected_secm.frame_list[a], delim, selected_secm.total_i[a], delim, selected_secm.mean_i[a], delim))
            if saveq:
                f.write('%.8E%s' %(selected_secm.I_of_q[a], delim))
            if save_qrange:
                f.write('%.8E%s' %(selected_secm.qrange_I[a], delim))
            if selected_secm.subtracted_sasm_list:
                f.write('%.8E%s%.8E%s' %(selected_secm.total_i_sub[a], delim, selected_secm.mean_i_sub[a], delim))
                if saveq:
                    f.write('%.8E%s' %(selected_secm.I_of_q_sub[a], delim))
                if save_qrange:
                    f.write('%.8E%s' %(selected_secm.qrange_I_sub[a], delim))
            if selected_secm.baseline_subtracted_sasm_list:
                f.write('%.8E%s%.8E%s' %(selected_secm.total_i_bcsub[a], delim, selected_secm.mean_i_bcsub[a], delim))
                if saveq:
                    f.write('%.8E%s' %(selected_secm.I_of_q_bcsub[a], delim))
                if save_qrange:
                    f.write('%.8E%s' %(selected_secm.qrange_I_bcsub[a], delim))
            if savetime:
                f.write('%.8E%s' %(time[a], delim))
            if savecalc:
                calc_str = ('%.8E%s%.8E%s%.8E%s%.8E%s%.8E%s%.8E%s%.8E%s' %(selected_secm.rg_list[a],
                    delim, selected_secm.rger_list[a], delim, selected_secm.i0_list[a],
                    delim, selected_secm.i0er_list[a], delim, selected_secm.vcmw_list[a],
                    delim, selected_secm.vcmwer_list[a], delim, selected_secm.vpmw_list[a],
                    delim))
                f.write(calc_str)
            f.write('%s\n' %(selected_secm._file_list[a].split('/')[-1]))


def saveWorkspace(sasm_dict, save_path):

    with open(save_path, 'wb') as f:

        cPickle.dump(sasm_dict, f, cPickle.HIGHEST_PROTOCOL)


def saveCSVFile(filename, data, header = ''):
    if isinstance(data, list):
        body_string = ''
        for item in data:
            body_string = body_string + ','.join(map(str, item))+'\n'

        if header != '':
            save_string = header + '\n' + body_string
        else:
            save_string = body_string

        with open(filename, 'w') as fsave:
            fsave.write(save_string)

    else:
        if header != '':
            np.savetxt(filename, data, delimiter = ',', header = header, comments = '')
        else:
            np.savetxt(filename, data, delimiter = ',', comments ='')

def saveUnevenCSVFile(filename, data, header = ''):
    maxlen = max([len(item) for item in data])
    body_string = ''

    for i in range(maxlen):
        line = ''
        for item in data:
            if i < len(item):
                item_data = str(item[i])
            else:
                item_data = ''

            line = line + '%s,' %(item_data)

        line.strip(',')
        line = line + '\n'
        body_string = body_string+line

    if header != '':
        save_string = header + '\n' + body_string
    else:
        save_string = body_string

    with open(filename, 'w') as fsave:
        fsave.write(save_string)

def saveSVDData(filename, svd_data, u_data, v_data):

    with open(filename, 'w') as fsave:
        fsave.write('# Singular_values,U_Autocorrelation,V_Autocorrelation\n')

        for line in svd_data:
            fsave.write(','.join(map(str, line))+'\n')

        fsave.write('\n\n')
        fsave.write('# U_matrix_(left_singular_vectors)\n')

        for line in u_data:
            fsave.write(','.join(map(str, line))+'\n')

        fsave.write('\n\n')
        fsave.write('# V_matrix_(right_singular_vectors)\n')

        for line in v_data:
            fsave.write(','.join(map(str, line))+'\n')


def saveEFAData(filename, panel1_results, panel2_results, panel3_results):
    framei = panel1_results['fstart']
    framef = panel1_results['fend']
    index = range(framei, framef+1)

    nvals = panel1_results['input']

    qvals = panel1_results['q']

    header_string = ''

    header_string = header_string + '# Series data name: %s\n' %(panel1_results['filename'])
    header_string = header_string + '# Started at series frame: %s\n' %(str(framei))
    header_string = header_string + '# Ended at series frame: %s\n' %(str(framef))
    header_string = header_string + '# Used: %s\n' %(panel1_results['profile'])
    header_string = header_string + '# Number of significant singular values: %s\n' %(str(nvals))
    header_string = header_string + '# Component Ranges:\n'
    for i in range(len(panel3_results['ranges'])):
        header_string = header_string + '#\tRange %i: %i to %i\n' %(i, panel3_results['ranges'][i][0], panel3_results['ranges'][i][1])
    header_string = header_string + '# Rotation setings: Method: %s\n' %(panel3_results['options']['method'])
    if panel3_results['options']['method'] != 'Explicit':
        header_string = header_string + '# Rotation setings: Iterations: %s   Convergence threshold: %s\n' %(panel3_results['options']['niter'], panel3_results['options']['tol'])
    header_string = header_string + '# Rotation converged: %s\n' %(str(panel3_results['converged']))
    if panel3_results['converged'] and panel3_results['options']['method'] != 'Explicit':
        header_string = header_string + '# Rotation results: Iterations: %s\n' %(panel3_results['iterations'])
    header_string = header_string + '\n'

    body_string = ''
    if panel3_results['converged']:
        body_string = body_string+'# Concentration Matrix Results\n'
        body_string = body_string+'# Index,'+','.join(['Value_%i' %i for i in range(nvals)])+'\n'

        conc = panel3_results['conc']

        conc_output = np.column_stack((index, conc))

        for line in conc_output:
            body_string = body_string+','.join(map(str, line)) + '\n'

        body_string = body_string +'\n'


        body_string = body_string+'# Rotation Chi^2\n'
        body_string = body_string+'# Index,Chi^2\n'

        chisq = panel3_results['chisq']

        chisq_output = np.column_stack((index, chisq))

        for line in chisq_output:
            body_string = body_string+','.join(map(str, line)) + '\n'

        body_string = body_string +'\n'


    body_string = body_string + '# Forward EFA Results\n'
    body_string = body_string + '# Index,'+','.join(['Value_%i' %i for i in range(nvals+1)])+'\n'

    fefa = panel2_results['forward_efa'].T[:,:nvals+1]
    fefa_output = np.column_stack((index, fefa))

    for line in fefa_output:
        body_string = body_string+','.join(map(str, line)) + '\n'

    body_string = body_string +'\n'


    body_string = body_string + '# Backward EFA Results\n'
    body_string = body_string + '# Index,'+','.join(['Value_%i' %i for i in range(nvals)])+'\n'

    befa = panel2_results['backward_efa'][:, ::-1].T[:,:nvals+1]
    befa_output = np.column_stack((index, befa))

    for line in befa_output:
        body_string = body_string+','.join(map(str, line)) + '\n'

    body_string = body_string +'\n'


    body_string = body_string + '# Singular Value Results\n\n'
    body_string = body_string + '# Singular Values\n'
    body_string = body_string + '# Index,Value\n'

    svs = panel1_results['svd_s']

    svs_output = np.column_stack((range(len(svs)),svs))

    for line in svs_output:
        body_string = body_string+','.join(map(str, line)) + '\n'

    body_string = body_string +'\n'


    body_string = body_string + '# Left Singular Vectors (U)\n'
    body_string = body_string + '# Q,'+','.join(['Column_%i' %i for i in range(nvals)])+'\n'

    svd_u = panel1_results['svd_u'].T[:,:nvals]
    svd_u_output = np.column_stack((qvals, svd_u))

    for line in svd_u_output:
        body_string = body_string+','.join(map(str, line)) + '\n'

    body_string = body_string +'\n'


    body_string = body_string + '# Right Singular Vectors (V)\n'
    body_string = body_string + '# Index,'+','.join(['Column_%i' %i for i in range(nvals)])+'\n'

    svd_v = panel1_results['svd_v'][:,:nvals]
    svd_v_output = np.column_stack((index, svd_v))

    for line in svd_v_output:
        body_string = body_string+','.join(map(str, line)) + '\n'

    body_string = body_string +'\n'

    save_string = header_string + body_string


    with open(filename, 'w') as fsave:
        fsave.write(save_string)


def saveDammixData(filename, ambi_data, nsd_data, res_data, clust_num, clist_data,
                dlist_data, model_data, setup_data, model_plots):

    header_string = '# DAMMIF/N results summary\n'
    for item in setup_data:
        header_string = header_string + '# %s\n' %(' '.join(map(str, item)))

    body_string = '\n# AMBIMETER results\n'

    for item in ambi_data:
        body_string = body_string + '# %s\n' %(' '.join(map(str, item)))

    if len(nsd_data) > 0:
        body_string = body_string + '\n# Normalized spatial discrepancy results\n'
        for item in nsd_data:
            body_string =  body_string + '# %s\n' %(' '.join(map(str, item)))

    if len(res_data) > 0:
        body_string = body_string + '\n# Reconstruction resolution (SASRES) results\n'
        for item in res_data:
            body_string =  body_string + '# %s\n' %(' '.join(map(str, item)))

    if len(clist_data) > 0:
        body_string = body_string + '\n# Clustering results\n'
        body_string = body_string + '# %s\n' %(' '.join(map(str, clust_num)))

        body_string = body_string+'# Cluster,Isolated,Rep_Model,Deviation\n'
        for item in clist_data:
            body_string =  body_string + '%s\n' %(','.join(map(str, item)))

        body_string = body_string+'\n#Cluster1,Cluster2,Distance\n'
        for item in dlist_data:
            body_string =  body_string + '%s\n' %(','.join(map(str, item)))


    body_string = body_string + '\n# Individual model results\n'
    body_string = body_string + '# Model,Chi^2,Rg,Dmax,Excluded_Vol,Est_Protein_MW,Mean_NSD\n'
    for item in model_data:
        body_string =  body_string + '%s\n' %(','.join(map(str, item)))

    save_string = header_string + body_string

    with open(filename, 'w') as fsave:
        fsave.write(save_string)

    pdf = matplotlib.backends.backend_pdf.PdfPages(os.path.splitext(filename)[0]+'.pdf')

    for data in model_plots:
        for fig in data[1]:
            fig.suptitle('Model: %s' %(data[0]))
            fig.subplots_adjust(top=0.9)
            pdf.savefig(fig)
            fig.suptitle('')
            fig.subplots_adjust(top=0.95)

    pdf.close()


def saveDenssData(filename, ambi_data, res_data, model_plots, setup_data,
    rsc_data, model_data):

    header_string = '# DENSS results summary\n'
    for item in setup_data:
        header_string = header_string + '# %s\n' %(' '.join(map(str, item)))

    body_string = '\n# AMBIMETER results\n'

    for item in ambi_data:
        body_string = body_string + '# %s\n' %(' '.join(map(str, item)))

    if len(rsc_data)>0:
        body_string = '\n# RSC results\n'
        for item in rsc_data:
            body_string =  body_string + '# %s\n' %(' '.join(map(str, item)))

    if len(res_data) > 0:
        body_string = body_string + '\n# Reconstruction resolution (FSC) results\n'
        for item in res_data:
            body_string =  body_string + '# %s\n' %(' '.join(map(str, item)))

    body_string = body_string + '\n# Individual model results\n'
    body_string = body_string + 'Model,Chi^2,Rg,Support_Volume,Mean_RSC\n'
    for item in model_data:
        body_string =  body_string + '%s\n' %(','.join(map(str, item)))

    save_string = header_string + body_string

    with open(filename, 'w') as fsave:
        fsave.write(save_string)

    pdf = matplotlib.backends.backend_pdf.PdfPages(os.path.splitext(filename)[0]+'.pdf')

    for data in model_plots:
        for fig in data[1]:
            fig.suptitle('Model: %s' %(data[0]))
            fig.subplots_adjust(top=0.9)
            pdf.savefig(fig)
            fig.suptitle('')
            fig.subplots_adjust(top=0.95)

    pdf.close()


def saveDensityMrc(filename, rho, side):
    """Write an MRC formatted electron density map.
       See here: http://www2.mrc-lmb.cam.ac.uk/research/locally-developed-software/image-processing-software/#image
    """
    xs, ys, zs = rho.shape
    nxstart = -xs/2+1
    nystart = -ys/2+1
    nzstart = -zs/2+1
    with open(filename, "wb") as fout:
        # NC, NR, NS, MODE = 2 (image : 32-bit reals)
        fout.write(struct.pack('<iiii', xs, ys, zs, 2))
        # NCSTART, NRSTART, NSSTART
        fout.write(struct.pack('<iii', nxstart, nystart, nzstart))
        # MX, MY, MZ
        fout.write(struct.pack('<iii', xs, ys, zs))
        # X length, Y, length, Z length
        fout.write(struct.pack('<fff', side, side, side))
        # Alpha, Beta, Gamma
        fout.write(struct.pack('<fff', 90.0, 90.0, 90.0))
        # MAPC, MAPR, MAPS
        fout.write(struct.pack('<iii', 1, 2, 3))
        # DMIN, DMAX, DMEAN
        fout.write(struct.pack('<fff', np.min(rho), np.max(rho), np.average(rho)))
        # ISPG, NSYMBT, mlLSKFLG
        fout.write(struct.pack('<iii', 1, 0, 0))
        # EXTRA
        fout.write(struct.pack('<'+'f'*12, 1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0))
        for i in range(0, 12):
            fout.write(struct.pack('<f', 0.0))

        # XORIGIN, YORIGIN, ZORIGIN
        fout.write(struct.pack('<fff', nxstart*(side/xs), nystart*(side/ys), nzstart*(side/zs)))
        # MAP
        fout.write('MAP ')
        # MACHST (little endian)
        fout.write(struct.pack('<BBBB', 0x44, 0x41, 0x00, 0x00))
        # RMS (std)
        fout.write(struct.pack('<f', np.std(rho)))
        # NLABL
        fout.write(struct.pack('<i', 0))
        # LABEL(20,10) 10 80-character text labels
        for i in xrange(0, 800):
            fout.write(struct.pack('<B', 0x00))

        # Write out data
        for k in range(zs):
            for j in range(ys):
                for i in range(xs):
                    s = struct.pack('<f', rho[i,j,k])
                    fout.write(s)


def saveDensityXplor(filename, rho,side):
    """Write an XPLOR formatted electron density map."""
    xs, ys, zs = rho.shape
    title_lines = ['REMARK FILENAME="'+os.path.split(filename)[-1]+'"','REMARK DATE= '+str(datetime.datetime.today())]
    with open(filename,'wb') as f:
        f.write("\n")
        f.write("%8d !NTITLE\n" % len(title_lines))
        for line in title_lines:
            f.write("%-264s\n" % line)
        #f.write("%8d%8d%8d%8d%8d%8d%8d%8d%8d\n" % (xs,0,xs-1,ys,0,ys-1,zs,0,zs-1))
        f.write("%8d%8d%8d%8d%8d%8d%8d%8d%8d\n" % (xs,-xs/2+1,xs/2,ys,-ys/2+1,ys/2,zs,-zs/2+1,zs/2))
        f.write("% -.5E% -.5E% -.5E% -.5E% -.5E% -.5E\n" % (side,side,side,90,90,90))
        f.write("ZYX\n")
        for k in range(zs):
            f.write("%8s\n" % k)
            for j in range(ys):
                for i in range(xs):
                    if (i+j*ys) % 6 == 5:
                        f.write("% -.5E\n" % rho[i,j,k])
                    else:
                        f.write("% -.5E" % rho[i,j,k])
            f.write("\n")
        f.write("    -9999\n")
        f.write("  %.4E  %.4E" % (np.average(rho), np.std(rho)))


def loadWorkspace(load_path):
    try:
        with open(load_path, 'r') as f:
            sasm_dict = cPickle.load(f)
    except (ImportError, EOFError):
        try:
            with open(load_path, 'rb') as f:
                sasm_dict = cPickle.load(f)
        except (ImportError, EOFError):
            raise SASExceptions.UnrecognizedDataFormat(('Workspace could not be '
                'loaded. It may be an invalid file type, or the file may be '
                'corrupted.'))

    return sasm_dict

def writeSettings(filename, settings):
    try:
        with open(filename, 'w') as f:
            f.write(json.dumps(settings, indent = 4, sort_keys = True, cls = MyEncoder))
        return True
    except Exception as e:
        print e
        return False

def readSettings(filename):

    try:
        with open(filename, 'r') as f:
            settings = f.read()
        settings = dict(json.loads(settings))
    except Exception as e:
        try:
            with open(filename, 'rb') as f:
                pickle_obj = cPickle.Unpickler(f)
                pickle_obj.find_global = find_global
                settings = pickle_obj.load()
        except (KeyError, EOFError, ImportError, IndexError, AttributeError, cPickle.UnpicklingError) as e:
            print 'Error type: %s, error: %s' %(type(e).__name__, e)
            return None

    return settings

def find_global(module, name):
    if module == 'SASImage':
        if name == 'RectangleMask':
            name = '_oldMask'
        elif name == 'CircleMask':
            name = '_oldMask'
        elif name == 'PolygonMask':
            name = '_oldMask'

    __import__(module)
    mod = sys.modules[module]

    klass = getattr(mod, name)
    return klass

def writeHeader(d, f2, ignore_list = []):
    f2.write('### HEADER:\n#\n#')

    ignore_list.append('fit_sasm')
    ignore_list.append('orig_sasm')

    for ignored_key in ignore_list:
        if ignored_key in d.keys():
            del d[ignored_key]

    d = translateHeader(d)

    header = json.dumps(d, indent = 4, sort_keys = True, cls = MyEncoder)
    header = header.replace('\n', '\n#')
    f2.write(header)

    f2.write('\n\n')


#This class goes with write header, and was lifted from:
#https://stackoverflow.com/questions/27050108/convert-numpy-type-to-python/27050186#27050186
class MyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        else:
            return super(MyEncoder, self).default(obj)

def translateHeader(header, to_sasbdb=True):
    """
    Translates the header keywords to or from matching SASBDB format. This is
    to add compatibility with SASBDB while maintaining compatibility with older
    RAW formats and RAW internals.
    """
    for key in header:
        if isinstance(header[key], dict):
            header[key] = translateHeader(header[key], to_sasbdb)
        else:
            if to_sasbdb:
                if key in sasbdb_trans:
                    header[sasbdb_trans[key]] = header.pop(key)
            else:
                if key in sasbdb_back_trans:
                    header[sasbdb_back_trans[key]] = header.pop(key)

    return header

sasbdb_trans = {
    # First general RAW keywords
    'Sample_Detector_Distance'  : 'Sample-to-detector distance (mm)',
    'Wavelength'                : 'Wavelength (A)',
    #Next BioCAT specific keywords
    'Exposure_time/frame_s'     : 'Exposure time/frame (s)',
    'LC_flow_rate_mL/min'       : 'Flow rate (ml/min)',
}

sasbdb_back_trans = {value : key for (key, value) in sasbdb_trans.items()}


def writeRadFile(m, filename, header_on_top = True, use_header = True):
    ''' Writes an ASCII file from a measurement object, using the RAD format '''

    if use_header:
        d = m.getAllParameters()
    else:
        d = {}

    with open(filename, 'w') as f:

        if header_on_top == True:
            writeHeader(d, f)

        q_min, q_max = m.getQrange()

        f.write('### DATA:\n#\n')
        f.write('# %d\n' % len(m.i[q_min:q_max]))
        f.write('#{:^13}  {:^14}  {:^14}\n'.format('Q', 'I(Q)', 'Error'))

        for idx in range(q_min, q_max):
            line = ('%.8E  %.8E  %.8E\n') % ( m.q[idx], m.i[idx], m.err[idx])
            f.write(line)

        f.write('\n')
        if header_on_top == False:
            f.write('\n')
            writeHeader(d, f)

def writeIftFile(m, filename, use_header = True):
    ''' Writes an ASCII file from an IFT measurement object created by BIFT'''

    if use_header:
        d = m.getAllParameters()
    else:
        d = {}

    with open(filename, 'w') as f:
        f.write('# BIFT\n')
        f.write('#{:^13}  {:^14}  {:^14}\n'.format('R', 'P(R)', 'Error'))

        for idx in range(0,len(m.p)):
            line = ('%.8E  %.8E  %.8E\n') %( m.r[idx], m.p[idx], m.err[idx])
            f.write(line)

        f.write('\n\n')

        orig_q = m.q_orig
        orig_i = m.i_orig
        orig_err = m.err_orig
        fit = m.i_fit

        f.write('#{:^13}  {:^14}  {:^14}  {:^14}\n'.format('Q', 'I(Q)', 'Error', 'Fit'))
        for idx in range(0,len(orig_q)):
            line = ('%.8E  %.8E  %.8E  %.8E\n') %( orig_q[idx], orig_i[idx], orig_err[idx], fit[idx])
            f.write(line)

        f.write('\n\n')
        f.write('#{:^13}  {:^14}\n'.format('Q_extrap', 'Fit_extrap'))
        for idx in range(len(m.q_extrap)):
            line = '{:.8E}  {:.8E}\n'.format(m.q_extrap[idx],m.i_extrap[idx])
            f.write(line)

        ignore_list = ['all_posteriors', 'alpha_points', 'fit', 'orig_i', 'orig_q',
                       'orig_err', 'dmax_points', 'orig_sasm', 'fit_sasm']

        f.write('\n\n')

        writeHeader(d, f, ignore_list)


def writeOutFile(m, filename):
    ''' Writes an ASCII file from an IFT measurement object created by GNOM'''

    outfile = outfile = m.getParameter('out')

    with open(filename, 'w') as f:

        for line in outfile:
            f.write(line)

def findATSASDirectory():
    opsys= platform.system()

    if opsys== 'Darwin':
        default_path = '/Applications/ATSAS/bin'
    elif opsys== 'Windows':
        default_path = 'C:\\atsas\\bin'
    elif opsys== 'Linux':
        default_path = '~/atsas'
        default_path = os.path.expanduser(default_path)

        if os.path.exists(default_path):
            dirs = glob.glob(default_path+'/*')

            for item in dirs:
                if item.split('/')[-1].lower().startswith('atsas'):
                    default_path = item
                    break

            default_path = os.path.join(default_path, 'bin')

    is_path = os.path.exists(default_path)

    if is_path:
        return default_path

    if opsys == 'Windows':
        which = subprocess.Popen('where dammif', stdout=subprocess.PIPE,shell=True)
        output = which.communicate()

        atsas_path = output[0].strip()

    else:
        which = subprocess.Popen('which dammif', stdout=subprocess.PIPE,shell=True)
        output = which.communicate()

        atsas_path = output[0].strip()

    if atsas_path != '':
        return os.path.dirname(atsas_path)

    try:
        path = os.environ['PATH']
    except Exception:
        path = None

    if path != None:
        if opsys == 'Windows':
            split_path = path.split(';')
        else:
            split_path = path.split(':')

        for item in split_path:
            if item.lower().find('atsas') > -1 and item.lower().find('bin') > -1:
                if os.path.exists(item):
                    return item


    try:
        atsas_path = os.environ['ATSAS']
    except Exception:
        atsas_path = None

    if atsas_path != None:
        if atsas_path.lower().find('atsas') > -1:
            atsas_path = atsas_path.rstrip('\\')
            atsas_path = atsas_path.rstrip('/')
            if atsas_path.endswith('bin'):
                return atsas_path
            else:
                if os.path.exists(os.path.join(atsas_path, 'bin')):
                        return os.path.join(atsas_path, 'bin')

    return ''


def checkFileType(filename):
    ''' Tries to find out what file type it is and reports it back '''

    path, ext = os.path.splitext(filename)

    if ext == '.fit':
        return 'fit'
    elif ext == '.fir':
        return 'fir'
    elif ext == '.out':
        return 'out'
    elif ext == '.nxs': #Nexus file
        return 'image'
    elif ext == '.edf':
        return 'image'
    elif ext == '.ccdraw':
        return 'image'
    elif ext == '.int':
        return 'int'
    elif ext == '.img' or ext == '.imx_0' or ext == '.dkx_0' or ext == '.dkx_1' or ext == '.png' or ext == '.mpa':
        return 'image'
    elif ext == '.dat' or ext == '.sub' or ext =='.txt':
        return 'primus'
    elif ext == '.mar1200' or ext == '.mar2400' or ext == '.mar2300' or ext == '.mar3600':
        return 'image'
    elif (ext == '.img' or ext == '.sfrm' or ext == '.dm3' or ext == '.edf' or ext == '.xml' or ext == '.cbf' or ext == '.kccd' or
        ext == '.msk' or ext == '.spr' or ext == '.tif' or ext == '.h5' or ext == '.mccd' or ext == '.mar3450' or ext =='.npy' or
        ext == '.pnm' or ext == '.No'):
        return 'image'
    elif ext == '.ift':
        return 'ift'
    elif ext == '.csv':
        return 'csv'
    else:
        try:
            fabio.open(filename)
            return 'image'
        except:
            try:
                float(ext.strip('.'))
            except Exception:
                return 'rad'
            return 'csv'
