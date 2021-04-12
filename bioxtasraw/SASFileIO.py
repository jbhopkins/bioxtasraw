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

from __future__ import absolute_import, division, print_function, unicode_literals
from builtins import object, range, map, zip, str
from io import open
from six.moves import cPickle as pickle
import six

import hdf5plugin #This has to be imported before fabio, and h5py (and, I think, PIL/pillow) . . .

import os
import re
import time
import struct
import json
import copy
import collections
import datetime
from xml.dom import minidom
import ast

import numpy as np
import fabio
from PIL import Image
import matplotlib.backends.backend_pdf
import h5py

raw_path = os.path.abspath(os.path.join('.', __file__, '..', '..'))
if raw_path not in os.sys.path:
    os.sys.path.append(raw_path)

import bioxtasraw.RAWGlobals as RAWGlobals
import bioxtasraw.SASImage as SASImage
import bioxtasraw.SASM as SASM
import bioxtasraw.SASExceptions as SASExceptions
import bioxtasraw.SASProc as SASProc
import bioxtasraw.SECM as SECM
import bioxtasraw.SASCalib as SASCalib
import bioxtasraw.SASUtils as SASUtils

############################
#--- ## Load image files: ##
############################

def loadFabio(filename, hdf5_file=None):
    if hdf5_file is None:
        fabio_img = fabio.open(filename)
    else:
        fabio_img = hdf5_file

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

    fabio_img.close()

    return img, img_hdr

def loadTiffImage(filename):
    ''' Load TIFF image '''
    try:
        im = Image.open(filename)
        img = np.fromstring(im.tobytes(), np.uint16) #tobytes is compatible with pillow >=3.0, tostring was depreciated

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
        img = np.fromstring(im.tobytes(), np.uint32) #tobytes is compatible with pillow >=3.0, tostring was depreciated

        img = np.reshape(img, im.size)
        im.close()
    #except IOError:
    except Exception as e:
        print(e)
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
        ints = list(map(int, each_line.split()))
        data = np.append(data, ints)

    img = np.reshape(data, (128,128))

    return img, hdr


def loadSAXSLAB300Image(filename):

    try:
        im1 = Image.open(filename)
        im1a = im1.transpose(Image.FLIP_LEFT_RIGHT)
        im1b = im1a.transpose(Image.ROTATE_90)
        im2 = im1b.transpose(Image.FLIP_TOP_BOTTOM)

        newArr = np.fromstring(im2.tobytes(), np.int32)

        # reduce negative vals
        #newArr = np.where(newArr >= 0, newArr, 0)
        newArr = np.reshape(newArr, (im2.size[1],im2.size[0]))

        try:
          tag = im1.tag
        except AttributeError:
          tag = None
        im1.close()
    except (IOError, ValueError):
        return None, None

    try:
        tag_with_data = tag[315][0]

    except (TypeError, KeyError):
        print("Wrong file format. Missing TIFF tag number")
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
    except KeyError:
        pass
    try:
        d['BEFORE'] = d['saxsconf_Izero']
    except KeyError:
        pass
    try:
        d['AFTER'] = d['saxsconf_Izero']
    except KeyError:
        pass

    try:
        if d['det_flat_field'] != '(nil)':
            d['flatfield_applied'] = 1
        else:
            d['flatfield_applied'] = 0
    except KeyError:
        pass

    d['photons_per_100adu'] = 100

    try:
        (d['beam_x'],d['beam_y']) = d['beamcenter_actual'].split()
    except KeyError:
        pass
    try:
        (d['pixelsize_x'],d['pixelsize_y']) = d['det_pixel_size'].split()
        #unit conversions
        d['pixelsize_x'] = float(d['pixelsize_x']) * 1e6;
        d['pixelsize_y'] = float(d['pixelsize_y']) * 1e6;
    except KeyError:
        pass

    # conversion all possible values to numbers
    for i in d:
        try:
            d[i] = float(d[i])
        except ValueError:
            pass

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

def parseCHESSEIGER4MCountFile(filename):
    ''' Loads information from the counter file at CHESS, id7a from
    the image filename. EIGER .h5 files with 1-based frame numbers '''
    dir, file = os.path.split(filename)
    underscores = file.split('_')

    countFile = underscores[0]

    filenumber = int(underscores[-3])

    try:
        frame_number = int(underscores[-1].split('.')[0])
    except Exception:
        frame_number = 0

    # REG: if user root file name contains underscores, include those
    # note: must start at -3 to leave out "data" in image name

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
            # REG: hdf5 indices start at 1 not 0 as was our Pilatus convention!
            vals = allLines[label_idx+0+frame_number].split()

        for idx in range(0,len(vals)):
            counters[labels[idx+1]] = vals[idx]

        if date_idx:
            counters['date'] = allLines[date_idx][3:-1]

    except:
        print('Error loading CHESS id7a counter file')

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

    except Exception:
        print('Error loading G1 header')

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

    except Exception:
        print('Error loading G1 header')


    return counters

def parseCHESSG1CountFileEiger(filename):
    ''' Loads information from the counter file at CHESS, G1 from
    the image filename '''

    dirname, file = os.path.split(filename)

    dirname = os.path.dirname(dirname)
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

    countFilename = os.path.join(dirname, countFile)

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

    except Exception:
        print('Error loading G1 header')

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
                if key in counters:
                    counters[key] = counters[key] + '\n' + val.strip()
                else:
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

def parseCHESSEigerFilename(filename):
    dir, file = os.path.split(filename)
    underscores = file.split('_')

    countFile = underscores[0]

    filenumber = underscores[-3]

    try:
        frame_number = underscores[-1].split('.')[0]
    except Exception:
        frame_number = 0

    # REG: if user root file name contains underscores, include those
    # note: must start at -3 to leave out "data" in image name

    if len(underscores)>3:
        for each in underscores[1:-3]:
            countFile += '_' + each

    countFilename = os.path.join(dir, countFile)

    return (countFilename, filenumber, frame_number)

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
                    'CHESS EIGER 4M'        : parseCHESSEIGER4MCountFile,
                    'G1 WAXS, CHESS'        : parseCHESSG1CountFileWAXS,
                    'G1 Eiger, CHESS'       : parseCHESSG1CountFileEiger,
                    'I711, MaxLab'          : parseMAXLABI77HeaderFile,
                    'I911-4 Maxlab'         : parseMAXLABI911HeaderFile,
                    'BioCAT, APS'           : parseBioCATlogfile,
                    'BL19U2, SSRF'          : parseBL19U2HeaderFile,
                    'P12 Eiger, Petra III'  : parsePetraIIIP12EigerFile}

all_image_types = {
                   'Pilatus'            : loadFabio,
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
            # print(e)
            raise SASExceptions.HeaderLoadError('Header file for : ' + str(filename) + ' could not be read or contains incorrectly formatted data. ')
    else:
        hdr = {}

    #Clean up headers by removing spaces in header names and non-unicode characters)
    if hdr is not None:
        hdr = {key.replace(' ', '_').translate(str.maketrans('', '', '()[]'))
            if isinstance(key, str) else key: hdr[key] for key in hdr}
        # hdr = { key : str(hdr[key], errors='ignore') if isinstance(hdr[key], str)
        #     else hdr[key] for key in hdr}

    return hdr

def loadImage(filename, raw_settings, hdf5_file=None):
    ''' returns the loaded image based on the image filename
    and image type. '''
    image_type = raw_settings.get('ImageFormat')
    fliplr = raw_settings.get('DetectorFlipLR')
    flipud = raw_settings.get('DetectorFlipUD')

    try:
        if all_image_types[image_type] == loadFabio:
            img, imghdr = all_image_types[image_type](filename, hdf5_file)
        else:
            img, imghdr = all_image_types[image_type](filename)
    except (ValueError, TypeError, KeyError, fabio.fabioutils.NotGoodReader, Exception) as msg:
        raise SASExceptions.WrongImageFormat('Error loading image, ' + str(msg))

    if not isinstance(img, list):
        img = [img]
    if not isinstance(imghdr, list):
        imghdr = [imghdr]

    #Clean up headers by removing spaces in header names and non-unicode characters)
    for hdr in imghdr:
        if hdr is not None:
            hdr = {key.replace(' ', '_').translate(str.maketrans('', '', '()[]'))
                if isinstance(key, str) else key: hdr[key] for key in hdr}
            # hdr = { key : str(hdr[key], errors='ignore') if isinstance(hdr[key], str)
            #     else hdr[key] for key in hdr}


    if image_type != 'SAXSLab300':
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
    except Exception as msg:
        print(str(msg))
        file_type = None

    if file_type == 'hdf5':
        try:
            hdf5_file = fabio.open(filename)
            file_type = 'image'
        except Exception:
            pass
    else:
        hdf5_file = None

    if file_type == 'image':
        try:
            sasm, img = loadImageFile(filename, raw_settings, hdf5_file)
        except (ValueError, AttributeError) as msg:
            raise SASExceptions.UnrecognizedDataFormat('No data could be retrieved from the file, unknown format.')

        #Always do some post processing for image files
        if not isinstance(sasm, list):
            sasm = [sasm]

        for current_sasm in sasm:
            postProcessProfile(current_sasm, raw_settings, no_processing)

    elif file_type == 'hdf5':
        sasm = loadHdf5File(filename, raw_settings)
        img = None
    else:
        sasm = loadAsciiFile(filename, file_type)
        img = None

        #If you don't want to post process asci files, return them as a list
        if not isinstance(sasm, list):
            SASM.postProcessSasm(sasm, raw_settings)

    if not isinstance(sasm, list) and (sasm is None or len(sasm.i) == 0):
        raise SASExceptions.UnrecognizedDataFormat('No data could be retrieved from the file, unknown format.')

    return sasm, img

def postProcessProfile(sasm, raw_settings, no_processing):
    """
    Does post-processing on profiles created from images.
    """
    SASM.postProcessSasm(sasm, raw_settings) #Does dezingering

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
            #Does fully glassy carbon abs scale
            SASCalib.postProcessImageSasm(sasm, raw_settings)
        except SASExceptions.AbsScaleNormFailed:
            raise

def loadAsciiFile(filename, file_type):
    ascii_formats = {'rad'        : loadRadFile,
                     'new_rad'    : loadNewRadFile,
                     'primus'     : loadDatFile,
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

    if file_type in ascii_formats:
        sasm = ascii_formats[file_type](filename)

    if sasm is not None and file_type != 'ift' and file_type != 'out':
        if not isinstance(sasm, list) and len(sasm.i) == 0:
            sasm = None

    if file_type == 'rad' and sasm is None:

        sasm = ascii_formats['new_rad'](filename)

        if sasm is None:
            sasm = ascii_formats['primus'](filename)

    if file_type == 'primus' and sasm is None:
        sasm = ascii_formats['2col'](filename)

    if sasm is not None and not isinstance(sasm, list):
        sasm.setParameter('filename', os.path.split(filename)[1])

    return sasm


def loadImageFile(filename, raw_settings, hdf5_file=None):
    hdr_fmt = raw_settings.get('ImageHdrFormat')

    loaded_data, loaded_hdr = loadImage(filename, raw_settings, hdf5_file)

    sasm_list = [None for i in range(len(loaded_data))]

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

        sasm = processImage(img, parameters, raw_settings)

        sasm_list[i] = sasm


    return sasm_list, loaded_data

def processImage(img, parameters, raw_settings):
    for key in parameters['counters']:
        if key.lower().find('concentration') > -1 or key.lower().find('mg/ml') > -1:
            if ('BioCAT' in raw_settings.get('ImageHdrFormat') and
                'Experiment_type' in parameters['counters'] and
                'batch' in parameters['counters']['Experiment_type'].lower()):
                parameters['Conc'] = parameters['counters'][key]
                break
            elif ('BioCAT' in raw_settings.get('ImageHdrFormat') and
                'Experiment_type' not in parameters['counters']):
                parameters['Conc'] = parameters['counters'][key]
                break
            elif 'BioCAT' not in raw_settings.get('ImageHdrFormat'):
                parameters['Conc'] = parameters['counters'][key]
                break


    sasm = SASImage.integrateCalibrateNormalize(img, parameters, raw_settings)

    img_hdr = parameters['imageHeader']
    hdrfile_info = parameters['counters']

    ### Check for UV data if set in bindlist
    if raw_settings.get('UseHeaderForCalib'):
        uvvis = SASImage.getBindListDataFromHeader(raw_settings, img_hdr,
            hdrfile_info, keys=['UV Path Length', 'UV Transmission', 'UV Dark Transmission'])

        if not all(v is None for v in uvvis):
            sasm._parameters['analysis']['uvvis'] = {'UVPathlength'       : uvvis[0],
                                                     'UVTransmission'     : uvvis[1],
                                                     'UVDarkTransmission' : uvvis[2]}

    return sasm

def loadHdf5File(filename, raw_settings):
    """
    General notes:
    1) Doesn't yet do many things. These include using the load_only_series key,
    the load_only_batch key, load images, or do any other metadata.
    2) Not very thoroughly tested.
    """
    # Get the file defintions needed to load hdf5 files.
    file_defs = raw_settings.get('fileDefinitions')
    if 'hdf5' in file_defs:
        hdf5_defs = file_defs['hdf5']
    else:
        hdf5_defs = {}

    if not hdf5_defs:
        return []

    is_data_def = False
    loaded_data = []

    with h5py.File(filename, 'r') as data_file:

        #Figure out which of the definitions files, if any, match the hdf5 file
        for def_type, data_defs in hdf5_defs.items():
            data_id_name = data_defs['id']['name']
            data_id_loc = data_defs['id']['location']
            data_id_attr = data_defs['id']['is_attribute']
            data_id_val = data_defs['id']['value']

            if data_id_loc in data_file:
                if data_id_attr:
                    if data_id_name in data_file[data_id_loc].attrs:
                        if data_id_val == data_file[data_id_loc].attrs[data_id_name]:
                            is_data_def = True
                else:
                    dataset = data_file['{}/{}'.format(data_id_loc.rstrip('/'), data_id_name.lstrip('/'))]
                    if data_id_val == dataset[()]:
                        is_data_def = True

            if is_data_def:
                break

        #If we have definitions for this kind of file, determine what kind of data it is, batch of series
        if is_data_def:
            data_type_name = data_defs['data_type']['name']
            data_type_loc = data_defs['data_type']['location']
            data_type_attr = data_defs['data_type']['is_attribute']
            data_type_batch_val = data_defs['data_type']['batch_value']
            data_type_series_val = data_defs['data_type']['series_value']

            data_type = None

            if data_type_loc in data_file:
                if data_type_attr:
                    if data_type_name in data_file[data_type_loc].attrs:
                        data_type = data_file[data_type_loc].attrs[data_type_name]

                else:
                    dataset = data_file['{}/{}'.format(data_type_loc.rstrip('/'), data_type_name.lstrip('/'))]
                    data_type = dataset[()]

                if data_type is not None:
                    if data_type in data_type_batch_val:
                        data_type = 'batch'
                    elif data_type in data_type_series_val:
                        data_type = 'series'
                    else:
                        data_type = None

        #If it has a recognizeable data type, load in the data
        if data_type is not None:

            #Get various locations for the data and what data to load
            if data_type == 'batch':
                to_load_reduced = data_defs['to_load_batch']['reduced']
                to_load_image = data_defs['to_load_batch']['image']
                ordered = data_defs['to_load_batch']['ordered']

                image_data = data_defs['image_data_batch']
                reduced_data = data_defs['reduced_data_batch']

                if 'reduced_cond' in data_defs['to_load_batch']:
                    to_load_reduced_cond = data_defs['to_load_batch']['reduced_cond']
                else:
                    to_load_reduced_cond = []

                if 'image_cond' in data_defs['to_load_batch']:
                    to_load_image_cond = data_defs['to_load_batch']['image_cond']
                else:
                    to_load_image_cond = []

            elif data_type == 'series':
                to_load_reduced = data_defs['to_load_series']['reduced']
                to_load_image = data_defs['to_load_series']['image']
                ordered = data_defs['to_load_series']['ordered']

                image_data = data_defs['image_data_series']
                reduced_data = data_defs['reduced_data_series']

                if 'reduced_cond' in data_defs['to_load_series']:
                    to_load_reduced_cond = data_defs['to_load_series']['reduced_cond']
                else:
                    to_load_reduced_cond = []

                if 'image_cond' in data_defs['to_load_series']:
                    to_load_image_cond = data_defs['to_load_series']['image_cond']
                else:
                    to_load_image_cond = []

            if not ordered:
                if 'unsub' in to_load_reduced:
                    to_load_reduced.insert(0, to_load_reduced.pop(to_load_reduced.index('unsub')))
                if 'unsub' in to_load_image:
                    to_load_image.insert(0, to_load_image.pop(to_load_image.index('unsub')))

                if 'unsub' in to_load_reduced_cond:
                    to_load_reduced_cond.insert(0, to_load_reduced_cond.pop(to_load_reduced_cond.index('unsub')))
                if 'unsub' in to_load_image_cond:
                    to_load_image_cond.insert(0, to_load_image_cond.pop(to_load_image_cond.index('unsub')))

            #Get all the datasets in the file
            dataset_location = data_defs['dataset_location']
            datasets = []

            if dataset_location in data_file:
                for dataset in data_file[dataset_location]:
                    if isinstance(data_file[dataset], h5py.Group):
                        datasets.append(data_file[dataset].name)

            #Get the q data, if it isn't packaged with the data
            if data_defs['q_data']['with_intensity']:
                data_dim = 3
            else:
                data_dim = 2
                if data_defs['q_data']['is_attribute']:
                    q_vals = data_file[data_defs['q_data']['location']].attrs[data_defs['q_data']['name']]
                    q_vals = q_vals[:]
                else:
                    q_vals = data_file[data_defs['q_data']['location']]['name']
                    q_vals = q_vals[:]

            #For each dataset, load the data
            for dataset in datasets:
                # print dataset.lstrip('/')
                basename = os.path.basename(dataset)

                if data_type == 'series':
                    series_list = []
                    br_range = None
                    threshold = raw_settings.get('secCalcThreshold')

                    #Get the buffer range used for subtraction, if any
                    if 'metadata_series' in data_defs and 'buffer_range' in data_defs['metadata_series']:
                        br_loc = data_defs['metadata_series']['buffer_range']['location']
                        br_attr = data_defs['metadata_series']['buffer_range']['is_attribute']
                        br_name = data_defs['metadata_series']['buffer_range']['name']

                        br_loc = "{}/{}".format(dataset.rstrip('/'), br_loc.lstrip('/'))

                        if br_loc in data_file:
                            if br_attr:
                                if br_name in data_file[br_loc].attrs:
                                    br_range = data_file[br_loc].attrs[br_name]
                            else:
                                if br_name in br_loc:
                                    br_range = data_file['{}/{}'.format(br_loc.rstrip('/'), br_name.lstrip('/'))]
                                    br_range = [br_range]

                        if br_range is not None:
                            if isinstance(br_range, str):
                                if '[' in br_range or '(' in br_range:
                                    br_range = ast.literal_eval(br_range)
                                else:
                                    br_range = br_range.split(',')
                                    for j in range(len(br_range)):
                                        br_range[j] = int(br_range[j].strip())

                                    br_range = [(br_range[0], br_range[1])]

                            if isinstance(br_range, np.ndarray):
                                if len(br_range.shape) == 1:
                                    br_range = [(int(br_range[0]), int(br_range[1]))]

                    if 'metadata_series' in data_defs and 'calc_thresh' in data_defs['metadata_series']:
                        threshold = float(data_defs['metadata_series']['calc_thresh'])

                if data_type == 'batch':
                    batch_list = []

                #For each type of data to load (unsubtracted, subtracted, etc) for the data set, do so
                if len(to_load_reduced)+len(to_load_reduced_cond) > 0:
                    data_loaded = False
                else:
                    data_loaded = True

                load_pos = 0

                while not data_loaded:
                    if load_pos < len(to_load_reduced):
                        to_load = to_load_reduced[load_pos]
                    else:
                        to_load = to_load_reduced_cond[load_pos-len(to_load_reduced)]

                    data_loc = "{}/{}".format(dataset.rstrip('/'),
                       reduced_data[to_load].lstrip('/'))

                    if data_loc in data_file:
                        data = data_file[data_loc]

                        temp_data_list = []

                        if len(data.shape) == 2:
                            #Single profile
                            if data_dim == data.shape[0]:
                                if data_dim == 3:
                                    q_vals = data[0, :]
                                    i = data[1, :]
                                    ierr = data[2, :]
                                else:
                                    i = data[0, :]
                                    ierr = data[1, :]

                            else:
                                if data_dim == 3:
                                    q_vals = data[:, 0]
                                    i = data[:, 1]
                                    ierr = data[:, 2]
                                else:
                                    i = data[:, 0]
                                    ierr = data[:, 1]


                            if to_load == 'sub':
                                parameters = {'filename'    : 'S_{}_{:04d}'.format(basename, 1)}
                            else:
                                parameters = {'filename'    : '{}_{:04d}'.format(basename, 1)}

                            sasm = SASM.SASM(i, q_vals, ierr, parameters)

                            temp_data_list.append(sasm)

                        else:
                            #Multiple profiles
                            for num, each in enumerate(data):
                                if data_dim == each.shape[0]:
                                    if data_dim == 3:
                                        q_vals = each[0, :]
                                        i = each[1, :]
                                        ierr = each[2, :]
                                    else:
                                        i = each[0, :]
                                        ierr = each[1, :]

                                else:
                                    if data_dim == 3:
                                        q_vals = each[:, 0]
                                        i = each[:, 1]
                                        ierr = each[:, 2]
                                    else:
                                        i = each[:, 0]
                                        ierr = each[:, 1]

                                if to_load == 'sub':
                                    parameters = {'filename'    : 'S_{}_{:04d}'.format(basename, num+1)}
                                else:
                                    parameters = {'filename'    : '{}_{:04d}'.format(basename, num+1)}

                                sasm = SASM.SASM(i, q_vals, ierr, parameters)

                                temp_data_list.append(sasm)

                        if data_type == 'batch':
                            batch_list = temp_data_list
                            loaded_data = loaded_data + temp_data_list

                        elif data_type == 'series':
                            #If it's a series, make a series from the individual sasms
                            if to_load == 'unsub':
                                frame_list = list(range(len(temp_data_list)))
                                filename_list = [tsasm.getParameter('filename') for tsasm in temp_data_list]

                                secm = SECM.SECM(filename_list, temp_data_list,
                                    frame_list, {}, raw_settings)

                            elif to_load == 'sub':
                                if len(series_list) == 0:
                                    frame_list = list(range(len(temp_data_list)))
                                    filename_list = [tsasm.getParameter('filename') for tsasm in temp_data_list]

                                    secm = SECM.SECM(filename_list, temp_data_list,
                                        frame_list, {}, raw_settings)

                                    secm.already_subtracted = True

                                    use_subtracted_sasm = [True for tsasm in temp_data_list]
                                    secm.setSubtractedSASMs(temp_data_list, use_subtracted_sasm)
                                else:
                                    if br_range is not None:
                                        secm = series_list[0]
                                        unsub_sasms = secm.getAllSASMs()

                                        buf_sasms = []
                                        use_subtracted_sasm = []

                                        for start, end in br_range:
                                            buf_sasms = buf_sasms + unsub_sasms[start:end+1]

                                        avg_buf_sasm = SASProc.average(buf_sasms)

                                        ref_int = avg_buf_sasm.getTotalI()

                                        for sasm in unsub_sasms:
                                            if abs(sasm.getTotalI()/ref_int) > threshold:
                                                use_subtracted_sasm.append(True)
                                            else:
                                                use_subtracted_sasm.append(False)

                                        secm.buffer_range = br_range

                                    else:
                                        use_subtracted_sasm = [True for tsasm in temp_data_list]

                                    secm.setSubtractedSASMs(temp_data_list, use_subtracted_sasm)

                            series_list.append(secm)

                    load_pos = load_pos + 1

                    if load_pos >= len(to_load_reduced)+len(to_load_reduced_cond):
                        data_loaded = True
                    elif data_type == 'series' and load_pos == len(to_load_reduced) and len(series_list) > 0:
                        data_loaded = True
                    elif data_type == 'batch' and load_pos == len(to_load_reduced) and len(batch_list) > 0:
                        data_loaded = True


                if data_type == 'series':
                    if len(series_list)>0:
                        loaded_data.extend(series_list)

    return loaded_data


def loadOutFile(filename):

    five_col_fit = re.compile('\s*-?\d*[.]\d*[+eE-]*\d+\s+-?\d*[.]\d*[+eE-]*\d+\s+-?\d*[.]\d*[+eE-]*\d+\s+-?\d*[.]\d*[+eE-]*\d+\s+-?\d*[.]\d*[+eE-]*\d+\s*$')
    three_col_fit = re.compile('\s*-?\d*[.]\d*[+eE-]*\d+\s+-?\d*[.]\d*[+eE-]*\d+\s+-?\d*[.]\d*[+eE-]*\d+\s*$')
    two_col_fit = re.compile('\s*-?\d*[.]\d*[+eE-]*\d+\s+-?\d*[.]\d*[+eE-]*\d+\s*$')

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
    rg = None
    rger = None
    i0 = None
    i0er = None

    #Set some defaults in case the .out file isn't perfect. I've encountered
    #at least one case where no DISCRIP is returned, which messes up loading in
    #the .out file.
    Actual_DISCRP = -1
    Actual_OSCILL = -1
    Actual_STABIL = -1
    Actual_SYSDEV = -1
    Actual_POSITV = -1
    Actual_VALCEN = -1
    Actual_SMOOTH = -1


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
        # 'r'         : R,            #R, note R[-1] == Dmax
        # 'p'         : P,            #P(r)
        # 'perr'      : Perr,         #P(r) error
        # 'qlong'     : qfull,        #q down to q=0
        # 'qexp'      : qshort,       #experimental q range
        # 'jexp'      : Jexp,         #Experimental intensities
        # 'jerr'      : Jerr,         #Experimental errors
        # 'jreg'      : Jreg,         #Experimental intensities from P(r)
        # 'ireg'      : Ireg,         #Experimental intensities extrapolated to q=0

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
                'qmin'      : qshort[0],    #Minimum q
                'qmax'      : qshort[-1],   #Maximum q
                    }

    iftm = SASM.IFTM(P, R, Perr, Jexp, qshort, Jerr, Jreg, results, Ireg, qfull)

    return [iftm]



def load_series_sasm(group, data_name, q_raw=None, use_group_q=True, q_err_raw=None):

    if 'raw' in group and data_name in group['raw']:
        load_group = group['raw']
        load_dataset = load_group[data_name]
        attrs_dataset = group[data_name]
    else:
        load_group = group
        load_dataset = load_group[data_name]
        attrs_dataset = load_dataset

    sasm_data = {}

    if ('q' in load_group or q_raw is not None) and use_group_q:
        if q_raw is None:
            q_vals = load_group['q'][()]

            if q_vals.ndim == 2:
                sasm_data['q_raw'] = q_vals[:, 0]
                sasm_data['q_err_raw'] = q_vals[:, 1]
            else:
                sasm_data['q_raw'] = q_vals
                sasm_data['q_err_raw'] = None
        else:
            sasm_data['q_raw'] = copy.copy(q_raw)
            sasm_data['q_err_raw'] = copy.copy(q_err_raw)

        data = load_dataset[()]
        sasm_data['i_raw'] = data[:,0]
        sasm_data['err_raw'] = data[:,1]

    else:
        data = load_dataset[()]
        sasm_data['q_raw'] = data[:,0]
        sasm_data['i_raw'] = data[:,1]
        sasm_data['err_raw'] = data[:,2]

        if data.shape[1] == 4:
            sasm_data['q_err_raw'] = data[:,3]
        else:
            sasm_data['q_err_raw'] = None

    if not 'raw' in group or data_name not in group['raw']:
        sasm_data['scale_factor'] = 1.0
        sasm_data['offset_value'] = 0.0
        sasm_data['q_scale_factor'] = 1.0
        sasm_data['selected_qrange'] = (0, len(sasm_data['q_raw']))
    else:
        sasm_data['scale_factor'] = float(attrs_dataset.attrs['scale_factor'][()])
        sasm_data['offset_value'] = float(attrs_dataset.attrs['offset_value'][()])
        sasm_data['q_scale_factor'] = float(attrs_dataset.attrs['q_scale_factor'][()])
        sasm_data['selected_qrange'] = list(map(int, attrs_dataset.attrs['selected_qrange'][()]))

    sasm_data['parameters'] = loadDatHeader(attrs_dataset.attrs['parameters'])

    return sasm_data

def load_series_sasm_list(group, excluded_keys=['raw', 'q', 'q_err']):
    q_raw = None
    q_err_raw = None
    sasm_list = []

    if 'raw' in group:
        raw_group = group['raw']

        if 'q' in raw_group:
            q_raw = raw_group['q'][()]

        elif 'q' in group:
            q_raw = group['q'][()]

    elif 'q' in group:
        q_raw = group['q'][()]

    if q_raw is not None and q_raw.ndim == 2:
        q_err_raw = q_raw[:,1]
        q_raw = q_raw[:,0]

    for data in group:
        if data not in excluded_keys:
            sasm_list.append(load_series_sasm(group, data, q_raw,
                q_err_raw=q_err_raw))

    return sasm_list

def load_series(name):
    seriesm_data = {}

    with h5py.File(name, 'r', driver='core', backing_store=False) as f:
        seriesm_data['series_type'] = str(f.attrs['series_type'])
        seriesm_data['parameters'] = loadDatHeader(f.attrs['parameters'])

        seriesm_data['file_list'] = f['file_names'][()]
        seriesm_data['frame_list'] = list(map(int, f['frame_numbers'][()]))
        seriesm_data['time'] = list(map(float, f['times'][()]))

        # Get data from unsubtracted group
        profiles = f['profiles']
        seriesm_data['sasm_list'] = load_series_sasm_list(profiles, ['raw', 'q',
            'q_err', 'average_buffer_profile'])

        if len(profiles['average_buffer_profile']) > 0:
            seriesm_data['average_buffer_sasm'] = load_series_sasm(profiles,
                'average_buffer_profile', use_group_q=False)
        else:
            seriesm_data['average_buffer_sasm'] = None

        # Get data from subtracted group

        sub_profiles = f['subtracted_profiles']
        seriesm_data['subtracted_sasm_list'] = load_series_sasm_list(sub_profiles)

        seriesm_data['use_subtracted_sasm'] = sub_profiles.attrs['use_subtracted_sasm'][()]

        # Get data from baseline subtracted group
        baseline_profiles = f['baseline_subtracted_profiles']
        seriesm_data['baseline_subtracted_sasm_list'] = load_series_sasm_list(baseline_profiles)

        seriesm_data['use_baseline_subtracted_sasm'] = baseline_profiles.attrs['use_baseline_subtracted_sasm'][()]

        # Get data from intensity groups
        intensity = f['intensities']
        if (isinstance(intensity.attrs['buffer_range'][()], np.ndarray)
            and intensity.attrs['buffer_range'][()].ndim ==1
            and intensity.attrs['buffer_range'][()].size > 1):
            seriesm_data['buffer_range'] = [(intensity.attrs['buffer_range'][()][0],
                intensity.attrs['buffer_range'][()][1])]
        else:
            seriesm_data['buffer_range'] = list(map(tuple, intensity.attrs['buffer_range'][()]))

        seriesm_data['already_subtracted'] = intensity.attrs['already_subtracted'][()]
        seriesm_data['qref'] = float(intensity['qref_intensities'].attrs['q_value'][()])
        seriesm_data['qrange'] = tuple(intensity['qrange_intensities'].attrs['q_range'][()])

        sub_intensity = f['subtracted_intensities']
        if (isinstance(sub_intensity.attrs['sample_range'][()], np.ndarray)
            and sub_intensity.attrs['sample_range'][()].ndim ==1 and
            sub_intensity.attrs['sample_range'][()].size > 1):
            seriesm_data['sample_range'] = [(sub_intensity.attrs['sample_range'][()][0],
                sub_intensity.attrs['sample_range'][()][1])]
        else:
            seriesm_data['sample_range'] = list(map(tuple, sub_intensity.attrs['sample_range'][()]))

        # Get calculated data
        calc_data = f['calculated_data']
        seriesm_data['rg'] = calc_data['rg'][:,0]
        seriesm_data['rger'] = calc_data['rg'][:,1]
        seriesm_data['i0'] = calc_data['I0'][:,0]
        seriesm_data['i0er'] = calc_data['I0'][:,1]
        seriesm_data['vpmw'] = calc_data['vp_mw'][()]
        seriesm_data['vcmw'] = calc_data['vc_mw'][:,0]
        seriesm_data['vcmwer'] = calc_data['vc_mw'][:,1]

        seriesm_data['window_size'] = int(calc_data.attrs['window_size'][()])
        seriesm_data['mol_type'] = str(calc_data.attrs['molecule_type'][:])
        seriesm_data['mol_density'] = float(calc_data.attrs['molecule_density'][()])
        seriesm_data['calc_has_data'] = calc_data.attrs['has_data'][()]

        # Get baseline
        baseline = f['baseline']
        seriesm_data['baseline_corr'] = load_series_sasm_list(baseline['correction'])

        seriesm_data['baseline_fit_results'] = baseline['fit_parameters'][:]

        if (isinstance(baseline.attrs['baseline_start_range'][()], np.ndarray)
            and baseline.attrs['baseline_start_range'][()].ndim ==1
            and baseline.attrs['baseline_start_range'][()].size >1):
            seriesm_data['baseline_start_range'] = (int(baseline.attrs['baseline_start_range'][0]),
                int(baseline.attrs['baseline_start_range'][1]))
        else:
            seriesm_data['baseline_start_range'] = list(map(tuple, baseline.attrs['baseline_start_range'][()]))

        if (isinstance(baseline.attrs['baseline_end_range'][()], np.ndarray)
            and baseline.attrs['baseline_end_range'][()].ndim ==1
            and baseline.attrs['baseline_end_range'][()].size >1):
            seriesm_data['baseline_end_range'] = (int(baseline.attrs['baseline_end_range'][0]),
                int(baseline.attrs['baseline_end_range'][1]))
        else:
            seriesm_data['baseline_end_range'] = list(map(tuple, baseline.attrs['baseline_end_range'][()]))

        seriesm_data['baseline_type'] = str(baseline.attrs['baseline_type'])
        seriesm_data['baseline_extrapolation'] = baseline.attrs['baseline_extrapolation']

        try:
            seriesm_data['item_font_color'] = f.attrs['item_font_color'][()]
            seriesm_data['item_selected_for_plot'] = f.attrs['item_selected_for_plot'][()]

            seriesm_data['line_color'] = profiles.attrs['line_color'][()]
            seriesm_data['line_width'] = profiles.attrs['line_width'][()]
            seriesm_data['line_style'] = profiles.attrs['line_style'][()]
            seriesm_data['line_marker'] = profiles.attrs['line_marker'][()]
            seriesm_data['line_visible'] = profiles.attrs['line_visible'][()]
            seriesm_data['line_marker_face_color'] = profiles.attrs['line_marker_face_color'][()]
            seriesm_data['line_marker_edge_color'] = profiles.attrs['line_marker_edge_color'][()]
            seriesm_data['line_visible'] = profiles.attrs['line_visible'][()]
            seriesm_data['line_legend_label'] = profiles.attrs['line_legend_label'][()]

            seriesm_data['line_color'] = calc_data.attrs['calc_line_color'][()]
            seriesm_data['line_width'] = calc_data.attrs['calc_line_width'][()]
            seriesm_data['line_style'] = calc_data.attrs['calc_line_style'][()]
            seriesm_data['line_marker'] = calc_data.attrs['calc_line_marker'][()]
            seriesm_data['line_visible'] = calc_data.attrs['calc_line_visible'][()]
            seriesm_data['line_marker_face_color'] = calc_data.attrs['calc_line_marker_face_color'][()]
            seriesm_data['line_marker_edge_color'] = calc_data.attrs['calc_line_marker_edge_color'][()]
            seriesm_data['line_visible'] = calc_data.attrs['calc_line_visible'][()]
            seriesm_data['line_legend_label'] = calc_data.attrs['calc_line_legend_label'][()]

        except Exception:
            pass

    # Deals with a change in how h5py reads in strings between version 2 and 3.
    if h5py.version.version_tuple.major >= 3:
        seriesm_data['file_list'] = [fname.decode('utf-8') for fname in seriesm_data['file_list']]

    else:
        seriesm_data['file_list'] = list(map(str, seriesm_data['file_list']))

    return seriesm_data

def loadSeriesFile(filename, settings):

    name, ext = os.path.splitext(filename)

    if ext == '.sec':
        #old stype
        file = open(filename, 'rb')
        secm_data = None

        try:
            if six.PY3:
                secm_data = pickle.load(file, encoding='latin-1')
            else:
                secm_data = pickle.load(file)
        except Exception as e:
            print(e)
            file.close()
            file = open(filename, 'rU')
            if six.PY3:
                secm_data = pickle.load(file, encoding='latin-1')
            else:
                secm_data = pickle.load(file)
        finally:
            file.close()

    else:
        secm_data = load_series(filename)

    if secm_data is not None:
        new_secm, line_data, calc_line_data = makeSeriesFile(secm_data, settings)

        new_secm.setParameter('filename', os.path.split(filename)[1])
    else:
        raise SASExceptions.UnrecognizedDataFormat('No data could be retrieved from the file, unknown format.')

    return new_secm


def makeSeriesFile(secm_data, settings):

    default_dict =     {
        'sasm_list'                     : [],
        'file_list'                     : [],
        'frame_list'                    : [],
        'parameters'                    : {},
        'window_size'                   : -1,
        'mol_type'                      : '',
        'threshold'                     : -1,
        'rg'                            : [],
        'rger'                          : [],
        'i0'                            : [],
        'i0er'                          : [],
        'calc_has_data'                 : False,
        'subtracted_sasm_list'          : [],
        'use_subtracted_sasm'           : [],
        'average_buffer_sasm'           : None,
        'mol_density'                   : -1,
        'already_subtracted'            : False,
        'baseline_subtracted_sasm_list' : [],
        'use_baseline_subtracted_sasm'  : [],
        'buffer_range'                  : [],
        'sample_range'                  : [],
        'baseline_start_range'          : (-1, -1),
        'baseline_end_range'            : (-1, -1),
        'baseline_corr'                 : [],
        'baseline_type'                 : '',
        'baseline_extrap'               : True,
        'baseline_fit_results'          : [],
        'series_type'                   : '',
        }

    for key in default_dict:
        if key not in secm_data:
            secm_data[key] = default_dict[key]

    sasm_list = []

    for sasm_data in secm_data['sasm_list']:

        if 'q_binned' in sasm_data:
            q = sasm_data['q_binned']
            i = sasm_data['i_binned']
            err = sasm_data['err_binned']
            q_err = None
        else:
            q = sasm_data['q_raw']
            i = sasm_data['i_raw']
            err = sasm_data['err_raw']
            q_err = sasm_data['q_err_raw']

        new_sasm = SASM.SASM(i, q, err, sasm_data['parameters'], q_err)

        new_sasm.setScaleValues(sasm_data['scale_factor'], sasm_data['offset_value'],
            sasm_data['q_scale_factor'])

        new_sasm.setQrange(sasm_data['selected_qrange'])

        try:
            new_sasm.setParameter('analysis', sasm_data['parameters_analysis'])
        except KeyError:
            pass

        new_sasm._update()

        sasm_list.append(new_sasm)

    new_secm = SECM.SECM(secm_data['file_list'], sasm_list,
        secm_data['frame_list'], secm_data['parameters'], settings)

    new_secm.setScaleValues(sasm_data['scale_factor'], sasm_data['offset_value'],
            sasm_data['q_scale_factor'])

    new_secm.series_type = secm_data['series_type']
    new_secm.window_size = secm_data['window_size']
    new_secm.mol_type =secm_data['mol_type']
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

    for sasm_data in secm_data['subtracted_sasm_list']:

        if sasm_data != -1:
            if 'q_binned' in sasm_data:
                q = sasm_data['q_binned']
                i = sasm_data['i_binned']
                err = sasm_data['err_binned']
                q_err = None
            else:
                q = sasm_data['q_raw']
                i = sasm_data['i_raw']
                err = sasm_data['err_raw']
                q_err = sasm_data['q_err_raw']

            new_sasm = SASM.SASM(i, q, err, sasm_data['parameters'], q_err)

            new_sasm.setScaleValues(sasm_data['scale_factor'], sasm_data['offset_value'],
                sasm_data['q_scale_factor'])

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

    for sasm_data in secm_data['baseline_subtracted_sasm_list']:

        if sasm_data != -1:
            if 'q_binned' in sasm_data:
                q = sasm_data['q_binned']
                i = sasm_data['i_binned']
                err = sasm_data['err_binned']
                q_err = None
            else:
                q = sasm_data['q_raw']
                i = sasm_data['i_raw']
                err = sasm_data['err_raw']
                q_err = sasm_data['q_err_raw']

            new_sasm = SASM.SASM(i, q, err, sasm_data['parameters'], q_err)

            new_sasm.setScaleValues(sasm_data['scale_factor'], sasm_data['offset_value'],
                sasm_data['q_scale_factor'])

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

    for sasm_data in secm_data['baseline_corr']:

        if sasm_data != -1:
            new_sasm = SASM.SASM(sasm_data['i_raw'], sasm_data['q_raw'],
                sasm_data['err_raw'], sasm_data['parameters'])

            new_sasm.setScaleValues(sasm_data['scale_factor'], sasm_data['offset_value'],
                sasm_data['q_scale_factor'])

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
        if sasm_data != -1:
            if 'q_binned' in sasm_data:
                q = sasm_data['q_binned']
                i = sasm_data['i_binned']
                err = sasm_data['err_binned']
                q_err = None
            else:
                q = sasm_data['q_raw']
                i = sasm_data['i_raw']
                err = sasm_data['err_raw']
                q_err = sasm_data['q_err_raw']

            new_sasm = SASM.SASM(i, q, err, sasm_data['parameters'], q_err)

        new_sasm.setScaleValues(sasm_data['scale_factor'], sasm_data['offset_value'],
            sasm_data['q_scale_factor'])

        new_sasm.setQrange(sasm_data['selected_qrange'])

        try:
            new_sasm.setParameter('analysis', sasm_data['parameters_analysis'])
        except KeyError:
            pass

    else:
        new_sasm = None

    new_secm.average_buffer_sasm = new_sasm

    new_secm._update()

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
    iq_pattern = re.compile('\s*-?\d*[.]\d*[+eE-]*\d+\s+-?\d*[.]\d*[+eE-]*\d+\s+-?\d*[.]\d*[+eE-]*\d+\s+-?\d*[.]\d*[+eE-]*\d+\s*$')
    pr_pattern = re.compile('\s*-?\d*[.]\d*[+eE-]*\d+\s+-?\d*[.]\d*[+eE-]*\d+\s+-?\d*[.]\d*[+eE-]*\d+\s*$')
    extrap_pattern = re.compile('\s*-?\d*[.]\d*[+eE-]*\d+\s+-?\d*[.]\d*[+eE-]*\d+\s*$')

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


def loadDatFile(filename):
    ''' Loads a .dat format file '''

    with open(filename, 'rU') as f:
        lines = f.readlines()

    if len(lines) == 0:
        raise SASExceptions.UnrecognizedDataFormat('No data could be retrieved from the file.')

    sasm = makeDatFile(lines, filename)

    return sasm

def makeDatFile(lines, filename):
    iq_pattern = re.compile('\s*-?\d*\.?\d*[+eE-]*\d+\s*[\s,]\s*-?\d*\.?\d*[+eE-]*\d+\s*[\s,]\s*-?\d*\.?\d*[+eE-]*\d+\s*')

    i = []
    q = []
    err = []

    comment = ''
    line = lines[0]
    j=0
    while line.split() and line.strip()[0] == '#':
        comment = comment+line
        j = j+1
        line = lines[j]

    fileHeader = {'comment':comment}
    parameters = {'filename' : os.path.split(filename)[1],
                  'counters' : fileHeader}

    if comment.find('model_intensity') > -1:
        #FoXS file with a fit! has four data columns
        is_foxs_fit=True
        is_sans_data = False
        imodel = []

    elif comment.find('dQ') > -1:
        #ORNL SANS instrument file
        is_foxs_fit = False
        is_sans_data = True
        qerr = []
    else:
        is_foxs_fit = False
        is_sans_data = False

    header = []
    header_start = False

    for j, line in enumerate(lines):
        iq_match = iq_pattern.match(line)

        if iq_match:
            if is_foxs_fit:
                if ',' in line:
                    found = line.split(',')
                else:
                    found = line.split()
                q.append(float(found[0]))
                i.append(float(found[1]))
                imodel.append(float(found[2]))
                err.append(abs(float(found[3])))

            elif is_sans_data:
                found = iq_match.group()
                if ',' in found:
                    found = line.split(',')
                else:
                    found = line.split()
                q.append(float(found[0]))
                i.append(float(found[1]))
                err.append(abs(float(found[2])))
                qerr.append(abs(float(found[3])))

            else:
                found = iq_match.group()
                if ',' in found:
                    found = found.split(',')
                else:
                    found = found.split()
                q.append(float(found[0]))
                i.append(float(found[1]))
                err.append(abs(float(found[2])))



        #Check to see if there is any header from RAW, and if so get that.
        #Header at the bottom
        if '### HEADER:' in line and len(q) > 0:
            header = lines[j+1:]

            # For headers at the bottom, stop trying the regex
            if len(q) > 0:
                break

        # Header at top
        elif '### HEADER:' in line and len(q) == 0:
            header_start = True

        elif header_start and '### DATA:' in line:
            header_start = False

        elif header_start and not iq_match:
            header.append(lines[j])

    if len(header)>0:
        hdr_str = ''
        for each_line in header:
            hdr_str=hdr_str+each_line.lstrip('#')

        hdict = loadDatHeader(hdr_str)

        for each in hdict:
            if each != 'filename':
                parameters[each] = hdict[each]

    i = np.array(i)
    q = np.array(q)
    err = np.array(err)

    sasm = SASM.SASM(i, q, err, parameters)

    if is_foxs_fit:
        parameters2 = copy.copy(parameters)
        parameters2['filename'] = os.path.splitext(os.path.split(filename)[1])[0]+'_FIT'

        sasm_model = SASM.SASM(imodel, q, err, parameters2)

        return [sasm, sasm_model]

    elif is_sans_data:
        sasm.setRawQErr(np.array(qerr))
        sasm._update()

    return sasm

def loadDatHeader(header):
    try:
        hdict = dict(json.loads(header))
        # print 'Loading RAW info/analysis...'
    except Exception:
        # print 'Unable to load header/analysis information. Maybe the file was not generated by RAW or was generated by an old version of RAW?'
        hdict = {}

    if hdict:
        hdict = translateHeader(hdict, to_sasbdb=False)

    return hdict


def loadRadFile(filename):
    ''' NOTE : THIS IS THE OLD RAD FORMAT..     '''
    ''' Loads a .rad file into a SASM object and attaches the filename and header into the parameters  '''

    iq_pattern = re.compile('\s*-?\d*[.]\d*[+eE-]*\d+\s+-?\d*[.]\d*[+eE-]*\d+\s+-?\d*[.]\d*[+eE-]*\d+\s+-?\d*[.]\d*[+eE-]*\d+\s*\n')
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

    iq_pattern = re.compile('\s*-?\d*[.]\d*[+eE-]*\d+\s+-?\d*[.]\d*[+eE-]*\d+\s+-?\d*[.]\d*[+eE-]*\d+\s*\n')
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

        if len(split_line) == 5 or len(split_line) == 7:
            q.append(float(split_line[0]))
            i.append(float(split_line[1]))

    i = np.array(i)
    q = np.array(q)
    err = np.sqrt(abs(i))

    return SASM.SASM(i, q, err, parameters)


def loadCsvFile(filename):
    ''' Loads a comma separated file, ignores everything except a three column line'''


    iq_pattern = re.compile('\s*-?\d*[.]?\d*[+eE-]*\d+[,]\s*-?\d*[.]?\d*[+eE-]*\d+[,]\s*-?\d*[.]?\d*[+eE-]*\d*\s*')
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

    iq_pattern = re.compile('\s*-?\d*[.]\d*\s+-?\d*[.]\d*.*\n')
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

    if not isinstance(sasm, list):
        sasm = [sasm]

    for each_sasm in sasm:
        filename, ext = os.path.splitext(each_sasm.getParameter('filename'))

        header_on_top = raw_settings.get('DatHeaderOnTop')

        if filetype == '.ift':
            try:
                writeIftFile(each_sasm, os.path.join(save_path, filename + filetype))
            except TypeError as e:
                print('Error in saveMeasurement, type: %s, error: %s' %(type(e).__name__, e))
                print('Resaving file without header')
                print(each_sasm.getAllParameters())
                writeIftFile(each_sasm, os.path.join(save_path, filename + filetype), False)

                raise SASExceptions.HeaderSaveError(e)
        elif filetype == '.out':
            writeOutFile(each_sasm, os.path.join(save_path, filename + filetype))
        else:
            try:
                writeRadFile(each_sasm, os.path.join(save_path, filename + filetype), header_on_top)
            except TypeError as e:
                print('Error in saveMeasurement, type: %s, error: %s' %(type(e).__name__, e))
                print('Resaving file without header')
                print(each_sasm.getAllParameters())
                writeRadFile(each_sasm, os.path.join(save_path, filename + filetype), header_on_top, False)

                raise SASExceptions.HeaderSaveError(e)

def saveSECItem(save_path, secm_dict):

    with open(save_path, 'wb') as f:
        pickle.dump(secm_dict, f, protocol=2)

def save_series_sasm(profile_group, sasm_data, dataset_name, descrip='',
    descrip_raw='', save_single_q=False, save_single_q_raw=False):

    if descrip == '':
        if save_single_q:
            descrip = ('A single scattering profile. Columns correspond to '
                'I(q), and sigma(q) from columns 0 to 1 respecitvely. Q vector '
                'is stored in a separate dataset called "q" in the same group.')
        else:
            descrip = ('A single scattering profile. Columns correspond to q, '
                'I(q), and sigma(q) from columns 0 to 2 respecitvely. If present '
                'column 3 is dQ.')

    if descrip_raw == '':
        if save_single_q_raw:
            descrip_raw = ('A single scattering profile without scaling, offset, '
                'or q trimming. Columns correspond to I(q), and sigma(q) from '
                'columns 0 to 1 respecitvely. Q vector is stored in a separate '
                'dataset called "q" in the same group.')
        else:
            descrip_raw = ('A single scattering profile without scaling, offset, '
                'or q trimming. Columns correspond to q, I(q), and sigma(q) from '
                'columns 0 to 2 respecitvely. If present column 3 is dQ.')

    q_raw = sasm_data['q_raw']
    iq_raw = sasm_data['i_raw']
    err_raw = sasm_data['err_raw']
    q_err_raw = sasm_data['q_err_raw']

    q = sasm_data['q']
    iq = sasm_data['i']
    err = sasm_data['err']
    q_err = sasm_data['q_err']

    if (np.array_equal(q, q_raw) and np.array_equal(iq, iq_raw)
        and np.array_equal(err, err_raw)):
        save_raw = False
    else:
        save_raw = True

    if save_raw:
        if not 'raw' in profile_group.keys():
            raw_group = profile_group.create_group('raw')
        else:
            raw_group = profile_group['raw']

        if save_single_q_raw:
            data = np.column_stack((iq_raw, err_raw))
        else:
            if q_err_raw is None:
                data = np.column_stack((q_raw, iq_raw, err_raw))
            else:
                data = np.column_stack((q_raw, iq_raw, err_raw, q_err_raw))

        dset_raw = raw_group.create_dataset(dataset_name, data=data)

        dset_raw.attrs['description'] = descrip_raw

    if save_single_q:
        data = np.column_stack((iq, err))
    else:
        if q_err is None:
            data = np.column_stack((q, iq, err))
        else:
            data = np.column_stack((q, iq, err, q_err))

    dset = profile_group.create_dataset(dataset_name, data=data)

    if save_raw:
        dset.attrs['scale_factor'] = sasm_data['scale_factor']
        dset.attrs['offset_value'] = sasm_data['offset_value']
        dset.attrs['q_scale_factor'] = sasm_data['q_scale_factor']
        dset.attrs['selected_qrange'] = sasm_data['selected_qrange']
    dset.attrs['parameters'] = formatHeader(sasm_data['parameters'])
    dset.attrs['description'] = descrip

def save_series_sasm_list(profile_group, sasm_list, frame_num_offset=0):

    if len(sasm_list) > 1:
        save_single_q = all([np.array_equal(sasm['q'], sasm_list[0]['q']) for sasm in sasm_list[1:]])
        save_single_q_raw = all([np.array_equal(sasm['q_raw'], sasm_list[0]['q_raw']) for sasm in sasm_list[1:]])

        q_err_exists = all([sasm['q_err'] is not None for sasm in sasm_list])
        q_err_raw_exists = all([sasm['q_err_raw'] is not None for sasm in sasm_list])

        if q_err_exists:
            save_single_q_err = all([np.array_equal(sasm['q_err'], sasm_list[0]['q_err']) for sasm in sasm_list[1:]])

            save_single_q = save_single_q and save_single_q_err

        if q_err_raw_exists:
            save_single_q_err_raw = all([np.array_equal(sasm['q_err'], sasm_list[0]['q_err']) for sasm in sasm_list[1:]])

            save_single_q_raw = save_single_q_raw and save_single_q_err_raw

        if save_single_q and save_single_q_raw:
            q_equal = np.array_equal(sasm_list[0]['q'], sasm_list[0]['q_raw'])

            if q_err_exists and q_err_raw_exists:
                q_err_equal = np.array_equal(sasm_list[0]['q_err'], sasm_list[0]['q_err_raw'])

                q_equal = q_equal and q_err_equal

    else:
        save_single_q_raw = False
        save_single_q = False

    if save_single_q:
        q = sasm_list[0]['q']
        q_err = sasm_list[0]['q_err']

        if q_err is not None:
            data = np.column_stack((q, q_err))
        else:
            data = q

        q_dataset = profile_group.create_dataset('q', data=data)
        q_dataset.attrs['description'] = ('the q vector for all numbered (e.g. '
            '00001) data in this group (note: named data, such as the average '
            'buffer, will have a separate q vector in that dataset). If present, '
            'column 1 is dQ.')

    if save_single_q_raw and not q_equal:
        if not 'raw' in profile_group.keys():
            raw_group = profile_group.create_group('raw')
        else:
            raw_group = profile_group['raw']

        q_raw = sasm_list[0]['q_raw']
        q_err_raw = sasm_list[0]['q_err_raw']

        if q_err_raw is not None:
            data = np.column_stack((q_raw, q_err_raw))
        else:
            data = q_raw

        q_raw_dataset = raw_group.create_dataset('q', data=data)
        q_raw_dataset.attrs['description'] = ('the q vector for all numbered (e.g. '
            '"00001") data in this group (note: named data, such as the "average_'
            'buffer_profile", will have a separate q vector in that dataset). '
            'If present, column 1 is dQ.')

    for j, sasm_data in enumerate(sasm_list):
        frame_num = j + frame_num_offset
        save_series_sasm(profile_group, sasm_data, "{:06d}".format(frame_num),
            save_single_q=save_single_q, save_single_q_raw=save_single_q_raw)

def save_series(save_name, seriesm, save_gui_data=False):

    seriesm_dict = seriesm.extractAll()

    if save_gui_data:
        try:
            seriesm_dict['line_color'] = seriesm.line.get_color()
            seriesm_dict['line_width'] = seriesm.line.get_linewidth()
            seriesm_dict['line_style'] = seriesm.line.get_linestyle()
            seriesm_dict['line_marker'] = seriesm.line.get_marker()
            seriesm_dict['line_marker_face_color'] = seriesm.line.get_markerfacecolor()
            seriesm_dict['line_marker_edge_color'] = seriesm.line.get_markeredgecolor()
            seriesm_dict['line_visible'] = seriesm.line.get_visible()
            seriesm_dict['line_legend_label'] = seriesm.line.get_label()

            seriesm_dict['calc_line_color'] = seriesm.calc_line.get_color()
            seriesm_dict['calc_line_width'] = seriesm.calc_line.get_linewidth()
            seriesm_dict['calc_line_style'] = seriesm.calc_line.get_linestyle()
            seriesm_dict['calc_line_marker'] = seriesm.calc_line.get_marker()
            seriesm_dict['calc_line_marker_face_color'] = seriesm.calc_line.get_markerfacecolor()
            seriesm_dict['calc_line_marker_edge_color'] = seriesm.calc_line.get_markeredgecolor()
            seriesm_dict['calc_line_visible'] = seriesm.calc_line.get_visible()
            seriesm_dict['calc_line_legend_label'] = seriesm.calc_line.get_label()

            seriesm_dict['item_font_color'] = seriesm.item_panel.getFontColour()
            seriesm_dict['item_selected_for_plot'] = seriesm.item_panel.getSelectedForPlot()
        except Exception:
            pass

    seriesm_dict['parameters_analysis'] = seriesm_dict['parameters']['analysis']  #pickle wont save this unless its raised up

    seriesm_data = copy.deepcopy(seriesm_dict)

    with h5py.File(save_name, 'w', driver='core', libver='earliest') as f:
        f.attrs['file_type'] = 'RAW_Series'
        f.attrs['raw_version'] = RAWGlobals.version
        f.attrs['parameters'] = formatHeader(seriesm_data['parameters'])
        f.attrs['series_type'] = seriesm_data['series_type']

        if save_gui_data:
            try:
                f.attrs['item_font_color'] = seriesm_data['item_font_color']
                f.attrs['item_selected_for_plot'] = seriesm_data['item_selected_for_plot']
            except Exception:
                pass

        # Add filename info
        for j in range(len(seriesm_data['file_list'])):
            seriesm_data['file_list'][j] = seriesm_data['file_list'][j].encode('utf-8')

        try:
            dtype = h5py.string_dtype() #h5py 2.10, python 3
        except Exception:
            if six.PY3:
                dtype = h5py.special_dtype(vlen=str) #h5py < 2.10, python3
            else:
                dtype = h5py.special_dtype(vlen=unicode) #h5py < 2.10, python2

        fname_data = f.create_dataset('file_names', data=seriesm_data['file_list'],
            dtype=dtype)
        fname_data.attrs['description'] = ('Ordered list of filenames, '
            'corresponding to profile numbering order.')

        # Add frame numbers
        frames = f.create_dataset('frame_numbers', data=seriesm_data['frame_list'])
        frames.attrs['description'] = ('List of frame numbers, corresponding to '
            'profile numbers.')

        # Add time
        times = f.create_dataset('times', data=seriesm_data['time'])
        times.attrs['description'] = ('Ordered list of acquisition time of the profiles, '
            'corresponding to the profile numbering order (may not be available).')
        times.attrs['unit'] = 's'


        # Add individual profiles
        profiles = f.create_group('profiles')
        profiles.attrs['profile_type'] = 'input'
        profiles.attrs['description'] = ('Input scattering profiles without processing.')
        save_series_sasm_list(profiles, seriesm_data['sasm_list'])

        if (seriesm_data['average_buffer_sasm'] is None
            or seriesm_data['average_buffer_sasm'] == -1):
            profiles.create_dataset('average_buffer_profile', data=[])
        else:
            sasm = seriesm_data['average_buffer_sasm']
            descrip = ('A single scattering profile giving the averaged buffer '
                'scattering profile. Columns correspond to q, I(q), and sigma(q) '
                'from columns 0 to 2 respecitvely. If present, column 3 is dQ.')

            save_series_sasm(profiles, sasm, "average_buffer_profile", descrip, descrip)

        if save_gui_data:
            try:
                profiles.attrs['line_color'] = seriesm_data['line_color']
                profiles.attrs['line_width'] = seriesm_data['line_width']
                profiles.attrs['line_style'] = seriesm_data['line_style']
                profiles.attrs['line_marker'] = seriesm_data['line_marker']
                profiles.attrs['line_visible'] = seriesm_data['line_visible']
                profiles.attrs['line_marker_face_color'] = seriesm_data['line_marker_face_color']
                profiles.attrs['line_marker_edge_color'] = seriesm_data['line_marker_edge_color']
                profiles.attrs['line_visible'] = seriesm_data['line_visible']
                profiles.attrs['line_legend_label'] = seriesm_data['line_legend_label']
            except Exception:
                pass

        sub_profiles = f.create_group('subtracted_profiles')
        sub_profiles.attrs['profile_type'] = 'subtracted'
        sub_profiles.attrs['description'] = ('Subtracted scattering profiles.')
        sub_profiles.attrs['use_subtracted_sasm'] = seriesm_data['use_subtracted_sasm']
        save_series_sasm_list(sub_profiles, seriesm_data['subtracted_sasm_list'])

        baseline_profiles = f.create_group('baseline_subtracted_profiles')
        baseline_profiles.attrs['profile_type'] = 'subtracted_and_baseline_corrected'
        baseline_profiles.attrs['description'] = ('Baseline corrected and subtracted '
            'scattering profiles.')
        baseline_profiles.attrs['use_baseline_subtracted_sasm'] = seriesm_data['use_baseline_subtracted_sasm']
        save_series_sasm_list(baseline_profiles, seriesm_data['baseline_subtracted_sasm_list'])


        # Add intensities
        intensity = f.create_group('intensities')
        intensity.attrs['intensity_type'] = 'input'
        intensity.attrs['description'] = ('Intensities for each input scattering profile')
        intensity.attrs['buffer_range'] = seriesm_data['buffer_range']
        intensity.attrs['already_subtracted'] = seriesm_data['already_subtracted']

        total_i_dset = intensity.create_dataset('total_intensities',
            data=seriesm_data['total_i'])
        total_i_dset.attrs['description'] = ('Total integrated intensity for each '
            'input scattering profile.')

        mean_i_dset = intensity.create_dataset('mean_intensities',
            data=seriesm_data['mean_i'])
        mean_i_dset.attrs['description'] = ('Mean intensity for each input '
            'scattering profile.')

        qref_i_dset = intensity.create_dataset('qref_intensities',
            data=seriesm_data['i_of_q'])
        qref_i_dset.attrs['description'] = ('Intensity at a single q value for each input '
            'scattering profile (may not be available).')
        qref_i_dset.attrs['q_value'] = seriesm_data['qref']

        qrange_i_dset = intensity.create_dataset('qrange_intensities',
            data=seriesm_data['qrange_I'])
        qrange_i_dset.attrs['description'] = ('Intensity in a range q values '
            'for each input scattering profile (may not be available).')
        qrange_i_dset.attrs['q_range'] = seriesm_data['qrange']

        # Add subtracted intensities
        intensity = f.create_group('subtracted_intensities')
        intensity.attrs['intensity_type'] = 'subtracted'
        intensity.attrs['description'] = ('Intensities for each subtracted '
            'scattering profile (if available)')
        intensity.attrs['sample_range'] = seriesm_data['sample_range']

        total_i_dset = intensity.create_dataset('total_intensities',
            data=seriesm_data['total_i_sub'])
        total_i_dset.attrs['description'] = ('Total integrated intensity for each '
            'subtracted scattering profile.')

        mean_i_dset = intensity.create_dataset('mean_intensities',
            data=seriesm_data['mean_i_sub'])
        mean_i_dset.attrs['description'] = ('Mean intensity for each subtracted '
            'scattering profile.')

        qref_i_dset = intensity.create_dataset('qref_intensities',
            data=seriesm_data['I_of_q_sub'])
        qref_i_dset.attrs['description'] = ('Intensity at a single q value for '
            'each subtracted scattering profile (may not be available).')
        qref_i_dset.attrs['q_value'] = seriesm_data['qref']

        qrange_i_dset = intensity.create_dataset('qrange_intensities',
            data=seriesm_data['qrange_I_sub'])
        qrange_i_dset.attrs['description'] = ('Intensity in a range of q values for '
            'each subtracted scattering profile (may not be available).')
        qrange_i_dset.attrs['q_range'] = seriesm_data['qrange']

        # Add baseline corrected intensities
        intensity = f.create_group('baseline_subtracted_intensities')
        intensity.attrs['intensity_type'] = 'subtracted_and_baseline_corrected'
        intensity.attrs['description'] = ('Intensities for each baseline '
            'corrected and subtracted scattering profile (if available)')

        total_i_dset = intensity.create_dataset('total_intensities',
            data=seriesm_data['total_i_bcsub'])
        total_i_dset.attrs['description'] = ('Total integrated intensity for each '
            'subtracted scattering profile.')

        mean_i_dset = intensity.create_dataset('mean_intensities',
            data=seriesm_data['mean_i_bcsub'])
        mean_i_dset.attrs['description'] = ('Mean intensity for each baseline '
            'corrected and subtracted scattering profile.')

        qref_i_dset = intensity.create_dataset('qref_intensities',
            data=seriesm_data['I_of_q_bcsub'])
        qref_i_dset.attrs['description'] = ('Intensity at a single q value for '
            'each baseline corrected and subtracted scattering profile (may not '
            'be available).')
        qref_i_dset.attrs['q_value'] = seriesm_data['qref']

        qrange_i_dset = intensity.create_dataset('qrange_intensities',
            data=seriesm_data['qrange_I_bcsub'])
        qrange_i_dset.attrs['description'] = ('Intensity in a range of q values for '
            'each baseline corrected and subtracted scattering profile (may not '
            'be available).')
        qrange_i_dset.attrs['q_range'] = seriesm_data['qrange']


        # Add calculated data
        calc_data = f.create_group('calculated_data')
        calc_data.attrs['description'] = ('Automatically calculated parameters '
            'for subtracted or baseline corrected data. Default value of -1 '
            'for any value indiciates either no calculation or an unsuccessful '
            'automatic result.')
        calc_data.attrs['window_size'] = seriesm_data['window_size']
        calc_data.attrs['molecule_type'] = seriesm_data['mol_type']
        calc_data.attrs['molecule_density'] = seriesm_data['mol_density']
        calc_data.attrs['has_data'] = seriesm_data['calc_has_data']

        if save_gui_data:
            try:
                calc_data.attrs['line_color'] = seriesm_data['calc_line_color']
                calc_data.attrs['line_width'] = seriesm_data['calc_line_width']
                calc_data.attrs['line_style'] = seriesm_data['calc_line_style']
                calc_data.attrs['line_marker'] = seriesm_data['calc_line_marker']
                calc_data.attrs['line_visible'] = seriesm_data['calc_line_visible']
                calc_data.attrs['line_marker_face_color'] = seriesm_data['calc_line_marker_face_color']
                calc_data.attrs['line_marker_edge_color'] = seriesm_data['calc_line_marker_edge_color']
                calc_data.attrs['line_visible'] = seriesm_data['calc_line_visible']
                calc_data.attrs['line_legend_label'] = seriesm_data['calc_line_legend_label']
            except Exception:
                pass

        rg_data = calc_data.create_dataset('rg',
            data=np.column_stack((seriesm_data['rg'], seriesm_data['rger'])))
        rg_data.attrs['description'] = ('Radius of gyration (Rg) calculated on a '
            'frame by frame basis. Column 0 and 1 are Rg and Rg uncertainty '
            'respectively')

        rg_data = calc_data.create_dataset('I0',
            data=np.column_stack((seriesm_data['i0'], seriesm_data['i0er'])))
        rg_data.attrs['description'] = ('Scattering intensity at zero angle '
            '(I(0)) calculated on a frame by frame basis. Column 0 and 1 are '
            'I(0) and I(0) uncertainty respectively')

        vp_data = calc_data.create_dataset('vp_mw', data=seriesm_data['vpmw'])
        vp_data.attrs['description'] = ('Molecular weight calculated using the '
            'adjusted Porod volume method calculated on a frame by frame basis.')

        vc_data = calc_data.create_dataset('vc_mw',
            data=np.column_stack((seriesm_data['vcmw'], seriesm_data['vcmwer'])))
        vc_data.attrs['description'] = ('Molecular weight calculated using the '
            'adjusted Porod volume method calculated on a frame by frame basis. '
            'Columns 0 and 1 and MW and MW uncertainty respectively.')


        # Add baseline
        baseline = f.create_group('baseline')
        baseline.attrs['description'] = ('Values for the baseline correction.')
        baseline.attrs['baseline_start_range'] = seriesm_data['baseline_start_range']
        baseline.attrs['baseline_end_range'] = seriesm_data['baseline_end_range']
        baseline.attrs['baseline_type'] = seriesm_data['baseline_type']
        baseline.attrs['baseline_extrapolation'] = seriesm_data['baseline_extrap']

        correction = baseline.create_group('correction')
        correction.attrs['description'] = ('The q dependent baseline correction '
            'on a frame by frame basis.')

        if seriesm_data['baseline_type'] == 'Linear' and not seriesm_data['baseline_extrap']:
            frame_num_offset = seriesm_data['baseline_start_range'][0]
        elif seriesm_data['baseline_type'] == 'Integral':
            frame_num_offset = seriesm_data['baseline_start_range'][1]
        else:
            frame_num_offset = 0

        save_series_sasm_list(correction, seriesm_data['baseline_corr'])

        fit_params = baseline.create_dataset("fit_parameters",
            data=seriesm_data['baseline_fit_results'])
        fit_params.attrs['description'] = ('Fit parameters for each q value '
            'for a linear baseline correction. Columns 0-4 correspond to '
            'intercept, slope, and the covariance for intercept and slope '
            'respectively.')


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
                    if key in parameters:
                        file.write('"' + str(each_sasm.getParameter(key)) + '"')
                    elif key == 'scale':
                        file.write('"' + str(each_sasm.getScale()) + '"')
                    elif key == 'offset':
                        file.write('"' + str(each_sasm.getOffset()) + '"')


                elif var == 'imageHeader':
                    if 'imageHeader' in parameters:
                        img_hdr = each_sasm.getParameter('imageHeader')
                        if key in img_hdr:
                            file.write(str(img_hdr[key]))
                        else:
                            file.write(' ')
                    else:
                            file.write(' ')

                elif var == 'counters':
                    if 'counters' in parameters:
                        file_hdr = each_sasm.getParameter('counters')
                        if key in file_hdr:
                            file.write(str(file_hdr[key]))
                        else:
                            file.write(' ')
                    else:
                        file.write(' ')


                elif var == 'guinier':
                    if 'analysis' in parameters:
                        analysis_dict = each_sasm.getParameter('analysis')

                        if 'guinier' in analysis_dict:
                            guinier = analysis_dict['guinier']

                            if key in guinier:
                                file.write(str(guinier[key]))
                            else:
                                file.write(' ')
                        else:
                            file.write(' ')
                    else:
                        file.write(' ')

                elif var == 'molecularWeight':
                    if 'analysis' in parameters:
                        analysis_dict = each_sasm.getParameter('analysis')

                        if 'molecularWeight' in analysis_dict:
                            mw = analysis_dict['molecularWeight']

                            if key in mw:
                                file.write(str(mw[key][key2]))
                            else:
                                file.write(' ')
                        else:
                            file.write(' ')
                    else:
                        file.write(' ')

                elif var =='GNOM':
                    if 'analysis' in parameters:
                        analysis_dict = each_sasm.getParameter('analysis')

                        if 'GNOM' in analysis_dict:
                            gnom = analysis_dict['GNOM']

                            if key in gnom:
                                file.write(str(gnom[key]))
                            else:
                                file.write(' ')
                        else:
                            file.write(' ')
                    else:
                        file.write(' ')

                elif var == 'BIFT':
                    if 'analysis' in parameters:
                        analysis_dict = each_sasm.getParameter('analysis')

                        if 'BIFT' in analysis_dict:
                            bift = analysis_dict['BIFT']

                            if key in bift:
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

            analysis_done = list(analysis.keys())

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

            analysis_done = list(analysis.keys())

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
                    if 'Conc' in all_params:
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


                elif (header.startswith('Absolute')
                    or header.startswith('I(0)Concentration')
                    or header.startswith('PorodVolume')
                    or header.startswith('VolumeOfCorrelation')
                    or header.startswith('DatmwBayes')
                    or header.startswith('ShapeAndSize')):
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

        pickle.dump(sasm_dict, f, protocol=2)


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
    index = list(range(framei, framef+1))

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

    svs_output = np.column_stack((list(range(len(svs))),svs))

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


def saveREGALSData(filename, panel_results):
    svd_results = panel_results[0]
    efa_results = panel_results[1]
    regals_results = panel_results[-1]['regals_results']

    framei = svd_results['fstart']
    framef = svd_results['fend']

    nvals = len(panel_results[-1]['profiles'])

    qvals = svd_results['q']

    header_string = ''

    header_string = header_string + '# Series data name: %s\n' %(svd_results['filename'])
    header_string = header_string + '# Started at series frame: %s\n' %(str(framei))
    header_string = header_string + '# Ended at series frame: %s\n' %(str(framef))
    header_string = header_string + '# Used: %s\n' %(svd_results['profile'])
    header_string = header_string + '# Number of significant singular values: %s\n' %(str(nvals))
    header_string = header_string + '# Component Ranges:\n'
    for i in range(len(regals_results['settings']['ranges'])):
        header_string = header_string + '#\tRange %i: %i to %i\n' %(i,
            regals_results['settings']['ranges'][i][0],
            regals_results['settings']['ranges'][i][1])

    header_string = header_string + '# Rotation setings: Convergence criteria: %s\n' %(regals_results['settings']['ctrl_settings']['conv_type'])
    if regals_results['settings']['ctrl_settings']['conv_type'] != 'Iterations':
        header_string = header_string + '# Rotation setings: Maximum iterations: %s\n' %(regals_results['settings']['ctrl_settings']['max_iter'])
        header_string = header_string + '# Rotation setings: Minimum iterations: %s\n' %(regals_results['settings']['ctrl_settings']['min_iter'])
        header_string = header_string + '# Rotation setings: Convergence tolerance: %s\n' %(regals_results['settings']['ctrl_settings']['tol'])

    else:
        header_string = header_string + '# Rotation setings: Iterations: %s\n' %(regals_results['settings']['ctrl_settings']['max_iter'])

    header_string = header_string + '# Rotation setings: Start with previous results: %s\n' %(regals_results['settings']['ctrl_settings']['seed_previous'])

    header_string = header_string + '# Rotation results: Iterations: %s\n' %(regals_results['params']['total_iter'])
    header_string = header_string + '# Rotation results: Average Chi^2: %s\n' %(regals_results['params']['x2'])
    header_string = header_string + '\n'

    comp_str = '# Components\n'

    components = regals_results['settings']['comp_settings']

    for i, comp in enumerate(components):
        prof_settings = comp[0]
        conc_settings = comp[1]

        comp_str = comp_str + ('# Component {}: Profile Regularizer: {}'
            '\n'.format(i, prof_settings['type']))
        comp_str = comp_str + ('# Component {}: Profile Lambda: {}'
            '\n'.format(i, prof_settings['lambda']))
        comp_str = comp_str + ('# Component {}: Profile Automatically '
            'determine lambda: {}\n'.format(i, prof_settings['auto_lambda']))

        if prof_settings['type'] != 'simple':
            comp_str = comp_str + ('# Component {}: Profile Grid points: {}'
                '\n'.format(i, prof_settings['kwargs']['Nw']))

        if prof_settings['type'] == 'realspace':
            comp_str = comp_str + ('# Component {}: Profile Dmax: {}'
                '\n'.format(i, prof_settings['kwargs']['dmax']))
            comp_str = comp_str + ('# Component {}: Profile is zero at r0: {}'
                '\n'.format(i, prof_settings['kwargs']['is_zero_at_r0']))
            comp_str = comp_str + ('# Component {}: Profile is zero at Dmax: {}'
                '\n'.format(i, prof_settings['kwargs']['is_zero_at_dmax']))

        comp_str = comp_str + ('# Component {}: Concentration Regularizer: {}'
            '\n'.format(i, conc_settings['type']))
        comp_str = comp_str + ('# Component {}: Concentration Lambda: {}'
            '\n'.format(i, conc_settings['lambda']))
        comp_str = comp_str + ('# Component {}: Concentration Automatically '
            'determine lambda: {}\n'.format(i, conc_settings['auto_lambda']))
        comp_str = comp_str + ('# Component {}: Concentration Range: {} '
            'to {}\n'.format(i, conc_settings['kwargs']['xmin'],
                conc_settings['kwargs']['xmax']))

        if conc_settings['type'] == 'smooth':
            comp_str = comp_str + ('# Component {}: Concentration Grid '
                'points: {}\n'.format(i, conc_settings['kwargs']['Nw']))
            comp_str = comp_str + ('# Component {}: Concentration is zero '
                'at x min: {}\n'.format(i, conc_settings['kwargs']['is_zero_at_xmin']))
            comp_str = comp_str + ('# Component {}: Concentration is zero '
                'at x max: {}\n'.format(i, conc_settings['kwargs']['is_zero_at_xmax']))

    comp_str = comp_str+'\n'

    body_string = ''
    body_string = body_string+'# Concentration Matrix Results\n'
    body_string = body_string+'# X,'+','.join(['Comp_%i' %i for i in range(nvals)])+'\n'

    conc = regals_results['mixture'].concentrations

    conc_output = np.column_stack((regals_results['x'], conc))

    for line in conc_output:
        body_string = body_string+','.join(map(str, line)) + '\n'

    body_string = body_string +'\n'

    body_string = body_string+'# Regularized Concentration Results\n'
    for j, conc in enumerate(regals_results['reg_conc']):
        body_string = body_string+'# X,Comp_{}\n' .format(j)

        conc_output = np.column_stack((conc[0], conc[1]))

        for line in conc_output:
            body_string = body_string+','.join(map(str, line)) + '\n'

        body_string = body_string +'\n'


    body_string = body_string+'# Rotation Chi^2\n'
    body_string = body_string+'# X,Chi^2\n'

    chisq = regals_results['chisq']

    chisq_output = np.column_stack((regals_results['x'], chisq))

    for line in chisq_output:
        body_string = body_string+','.join(map(str, line)) + '\n'

    body_string = body_string +'\n'

    for j, comp in enumerate(components):
        prof_settings = comp[0]

        if prof_settings['type'] == 'realspace':
            prof_comp = regals_results['mixture'].components[j].profile
            r = prof_comp.w
            pr = regals_results['mixture'].u_profile[j]

            if prof_comp._regularizer.is_zero_at_r0:
                pr = np.concatenate(([0], pr))

            if prof_comp._regularizer.is_zero_at_dmax:
                pr = np.concatenate((pr, [0]))

            body_string = body_string+'# Component {} P(r)\n'.format(j)
            body_string = body_string+'# r,P(r)\n'

            pr_output = np.column_stack((r, pr))

            for line in pr_output:
                body_string = body_string+','.join(map(str, line)) + '\n'

            body_string = body_string + '\n'

    if efa_results is not None and svd_results['use_efa']:
        body_string = body_string + '# Forward EFA Results\n'
        body_string = body_string + '# X,'+','.join(['Value_%i' %i for i in range(nvals+1)])+'\n'

        fefa = efa_results['forward_efa'].T[:,:nvals+1]
        fefa_output = np.column_stack((regals_results['x'], fefa))

        for line in fefa_output:
            body_string = body_string+','.join(map(str, line)) + '\n'

        body_string = body_string +'\n'


        body_string = body_string + '# Backward EFA Results\n'
        body_string = body_string + '# X,'+','.join(['Value_%i' %i for i in range(nvals)])+'\n'

        befa = efa_results['backward_efa'][:, ::-1].T[:,:nvals+1]
        befa_output = np.column_stack((regals_results['x'], befa))

        for line in befa_output:
            body_string = body_string+','.join(map(str, line)) + '\n'

        body_string = body_string +'\n'


    body_string = body_string + '# Singular Value Results\n\n'
    body_string = body_string + '# Singular Values\n'
    body_string = body_string + '# X,Value\n'

    svs = svd_results['svd_s']

    svs_output = np.column_stack((list(range(len(svs))),svs))

    for line in svs_output:
        body_string = body_string+','.join(map(str, line)) + '\n'

    body_string = body_string +'\n'


    body_string = body_string + '# Left Singular Vectors (U)\n'
    body_string = body_string + '# Q,'+','.join(['Column_%i' %i for i in range(nvals)])+'\n'

    svd_u = svd_results['svd_u'].T[:,:nvals]
    svd_u_output = np.column_stack((qvals, svd_u))

    for line in svd_u_output:
        body_string = body_string+','.join(map(str, line)) + '\n'

    body_string = body_string +'\n'


    body_string = body_string + '# Right Singular Vectors (V)\n'
    body_string = body_string + '# X,'+','.join(['Column_%i' %i for i in range(nvals)])+'\n'

    svd_v = svd_results['svd_v'][:,:nvals]
    svd_v_output = np.column_stack((regals_results['x'], svd_v))

    for line in svd_v_output:
        body_string = body_string+','.join(map(str, line)) + '\n'

    body_string = body_string +'\n'

    save_string = header_string + comp_str + body_string


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

    return save_string


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

    return save_string

def loadWorkspace(load_path):
    try:
        with open(load_path, 'rb') as f:
            if six.PY3:
                sasm_dict = pickle.load(f, encoding='latin-1')
            else:
                sasm_dict = pickle.load(f)
    except (ImportError, EOFError):
        try:
            with open(load_path, 'r') as f:
                if six.PY3:
                    sasm_dict = pickle.load(f, encoding='latin-1')
                else:
                    sasm_dict = pickle.load(f)
        except (ImportError, EOFError):
            raise SASExceptions.UnrecognizedDataFormat(('Workspace could not be '
                'loaded. It may be an invalid file type, or the file may be '
                'corrupted.'))

    return sasm_dict

def writeHeader(d, f2, ignore_list = []):
    f2.write('### HEADER:\n#\n#')

    ignore_list.append('fit_sasm')
    ignore_list.append('orig_sasm')

    for ignored_key in ignore_list:
        if ignored_key in d:
            del d[ignored_key]

    header = formatHeader(d)

    header = header.replace('\n', '\n#')
    f2.write(header)

    f2.write('\n\n')

def formatHeader(d):
    d = translateHeader(d)

    header = json.dumps(d, indent = 4, sort_keys = True, cls = SASUtils.MyEncoder)

    if header.count('\n') > 3000:
        try:
            del d['history']
            header = json.dumps(d, indent = 4, sort_keys = True, cls = SASUtils.MyEncoder)
        except Exception:
            pass

    return header

def translateHeader(header, to_sasbdb=True):
    """
    Translates the header keywords to or from matching SASBDB format. This is
    to add compatibility with SASBDB while maintaining compatibility with older
    RAW formats and RAW internals.
    """
    new_header = copy.deepcopy(header)

    for key in header.keys():
        if isinstance(header[key], dict):
            new_header[key] = translateHeader(header[key], to_sasbdb)
        else:
            if to_sasbdb:
                if key in sasbdb_trans:
                    new_header[sasbdb_trans[key]] = new_header.pop(key)
            else:
                if key in sasbdb_back_trans:
                    new_header[sasbdb_back_trans[key]] = new_header.pop(key)

    return new_header

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

        if m.q_err is None:
            f.write('#{:^13}  {:^14}  {:^14}\n'.format('Q', 'I(Q)', 'Error'))
        else:
            f.write('#{:^13}  {:^14}  {:^14}  {:^14}\n'.format('Q', 'I(Q)', 'Error', 'dQ'))

        for idx in range(q_min, q_max):
            if m.q_err is None:
                line = ('%.8E  %.8E  %.8E\n') % ( m.q[idx], m.i[idx], m.err[idx])
            else:
                line = ('%.8E  %.8E  %.8E  %.8E\n') % ( m.q[idx], m.i[idx], m.err[idx], m.q_err[idx])
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
        ext == '.msk' or ext == '.spr' or ext == '.tif' or ext == '.mccd' or ext == '.mar3450' or ext =='.npy' or
        ext == '.pnm' or ext == '.No'):
        return 'image'
    elif ext == '.ift':
        return 'ift'
    elif ext == '.csv':
        return 'csv'
    elif ext == '.h5':
        return 'hdf5'
    else:
        try:
            fabio.open(filename)
            return 'image'
        except Exception:
            try:
                float(ext.strip('.'))
            except Exception:
                return 'rad'
            return 'csv'
