#******************************************************************************
# This file is part of BioXTAS RAW.
#
#    BioXTAS RAW is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    Foobar is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with Foobar.  If not, see <http://www.gnu.org/licenses/>.
#
#******************************************************************************


################################################################
# MARCCD_headerReader.py                             25/04-2007
#
# Reads the header information from a MARCCD camera
#
# input: filename
# output: dictionary containing all header variables
#
# Author: Soren Skou Nielsen                            
################################################################

from __future__ import division
import struct
import sys
import re

def stringvar(s):
    ''' Removes empty spaces from read string '''

    endString = ""
    for i in s:
        if i != '\x00':
            endString = endString + i
    
    return endString


def fread(f, type, endian = "<"):
    ''' An easier fread that reads AND returns the read byte(S). little endian by default '''

    bytes = struct.calcsize(type)
    s = f.read(bytes)

    out = struct.unpack(endian + type, s)
   
    if len(out) == 1:
        out = out[0]
        
    return out


def readHeader(filename):
    ''' Read the MARCCD header information in a MARCCD TIFF file '''
    
    d = {}
    
    f = open(filename, "rb")              # Open in binary mode for portability
    tiff_tst = stringvar(fread(f,'cc'))

    # Test if file is a TIFF file (first two bytes are "II")
    if tiff_tst != 'II':
        raise NotTiffException(filename)
              
    f.seek(1024)

    d['header_type'] = fread(f, 'i')
    d['header_name'] = stringvar(fread(f, 'c'*16))
    d['header_major_version'] = fread(f, 'i')
    d['header_minor_version'] = fread(f, 'i')
    d['header_byte_order'] = fread(f, 'i')
    d['data_byte_order'] = fread(f, 'i')
    d['header_size'] = fread(f, 'i')
    d['frame_type'] = fread(f, 'i')
    d['magic_number'] = fread(f, 'I')
    d['compression_type'] = fread(f, 'i')
    d['compression1'] = fread(f, 'i')
    d['compression2'] = fread(f, 'i')
    d['compression3'] = fread(f, 'i')
    d['compression4'] = fread(f, 'i')
    d['compression5'] = fread(f, 'i')
    d['compression6'] = fread(f, 'i')
    d['nheaders'] = fread(f, 'i')            # Total Number of headers
    d['nfast'] = fread(f, 'i')               # numbers of pixels in one line
    d['nslow'] = fread(f, 'i')               # number of lines in image
    d['depth'] = fread(f, 'i')               # number of bytes per pixel
    d['record_length'] = fread(f, 'i')       # number of pixels between succesuve rows
    d['signig_bits'] = fread(f, 'i')         # True depth of data, in bits
    d['data_type'] = fread(f, 'i')           # signed, unsigned, float...
    d['saturated_value'] = fread(f, 'i')     # value marks pixel as saturated
    d['sequence'] = fread(f, 'i')            # TRUE or FALSE
    d['nimages'] = fread(f, 'i')             # Total number of images, size of each is nfast
    d['origin'] = fread(f, 'i')              # Corner of origin
    d['orientation'] = fread(f, 'i')         # Direction of fast axis
    d['view_direction'] = fread(f, 'i')      # direction to view frame
    d['overflow_location'] = fread(f, 'i')   # FOLLOWING_HEADER, FOLLOWING_ DATA
    d['over_8_bits'] = fread(f, 'i')         # number of pixels with counts > 255
    d['over_16_bits'] = fread(f, 'i')        # number of pixels with counts > 65535
    d['multiplexed'] = fread(f, 'i')         # multiplex flag
    d['nfastimages'] = fread(f, 'i')         # number of images in fast direction
    d['nslowimages'] = fread(f, 'i')         # number of images in slow direction
    d['background_applied'] = fread(f, 'i')  # flag correction has been applied
    d['bias_applied'] = fread(f, 'i')        # flag correction has been applied
    d['flatfield_applied'] = fread(f, 'i')   # flag correction has been applied
    d['distortion_applied'] = fread(f, 'i')  # flag correction has been applied
    d['original_header_type'] = fread(f, 'i')# flag correction has been applied
    d['file_saved'] = fread(f, 'i')          # should be zero if modified
    
    d['reserve1'] = fread(f, 'c'*80)
    
    d['total_counts'] = fread(f, 'i'*2)
    d['special_counts1'] = fread(f, 'i'*2)
    d['special_counts2'] = fread(f, 'i'*2)
    
    d['min'] = fread(f, 'i')
    d['max'] = fread(f, 'i')
    d['mean'] = fread(f, 'i')/1000
    d['rms'] = fread(f, 'i')/1000
    d['p10'] = fread(f, 'i')/1000
    d['p90'] = fread(f, 'i')
    d['stats_uptodate'] = fread(f, 'i')
    d['pixel_noise'] = fread(f, 'i')
    
    d['reserve2'] = fread(f, 'i'*18)
    d['percentile'] = fread(f, 'h'*128)
    
    d['xtal_to_detector'] = fread(f, 'i')/1000
    d['beam_x'] = fread(f, 'i')/1000            #1000*x beam position (pixels)
    d['beam_y'] = fread(f, 'i')/1000            #1000*x beam position (pixels)
    d['integration_time'] = fread(f, 'i')/1000  # in seconds
    d['exposure_time'] = fread(f, 'i')/1000     # in seconds
    d['readout_time'] = fread(f, 'i')/1000      # in seconds
    d['nreads'] = fread(f, 'i')
    
    d['start_twotheta'] = fread(f, 'i')/1000
    d['start_omega'] = fread(f, 'i')/1000
    d['start_chi'] = fread(f, 'i')/1000
    d['start_kappa'] = fread(f, 'i')/1000
    d['start_phi'] = fread(f, 'i')/1000
    d['start_delta'] = fread(f, 'i')/1000
    d['start_gamma'] = fread(f, 'i')/1000
    d['start_xtal_to_detector'] = fread(f, 'i')/1000
    d['end_twotheta'] = fread(f, 'i')/1000
    d['end_omega'] = fread(f, 'i')/1000
    d['end_chi'] = fread(f, 'i')/1000
    d['end_kappa'] = fread(f, 'i')/1000
    d['end_phi'] = fread(f, 'i')/1000
    d['end_delta'] = fread(f, 'i')/1000
    d['end_gamma'] = fread(f, 'i')/1000
    d['end_xtal_to_detector'] = fread(f, 'i')/1000
    
    d['rotation_axis'] = fread(f, 'i')/1000
    d['rotation_range'] = fread(f, 'i')/1000
    d['detector_rotx'] = fread(f, 'i')/1000
    d['detector_roty'] = fread(f, 'i')/1000
    d['detector_rotz'] = fread(f, 'i')/1000
    
    d['reserve3'] = fread(f, 'c'*16)
    
    d['detector_type'] = fread(f, 'i')
    d['pixelsize_x'] = fread(f, 'i')/1000
    d['pixelsize_y'] = fread(f, 'i')/1000
    d['mean_bias'] = fread(f, 'i')/1000
    d['photons_per_100adu'] = fread(f, 'i')
    d['measured_bias'] = fread(f, 'i')/1000
    d['measured_temperature'] = fread(f, 'i')
    d['measured_pressure'] = fread(f, 'i')
    
    d['reserve4'] = fread(f, 'B'*12)
    
    d['source_type'] = fread(f, 'i')
    d['source_dx'] = fread(f, 'i')
    d['source_dy'] = fread(f, 'i')
    d['source_wavelength'] = fread(f, 'i')
    d['source_power'] = fread(f, 'i')
    d['source_voltage'] = fread(f, 'i')
    d['source_current'] = fread(f, 'i')
    d['source_bias'] = fread(f, 'i')
    d['source_polarization_x'] = fread(f, 'i')
    d['source_polarization_y'] = fread(f, 'i')
    
    d['reserve4_source'] = fread(f, 'B'*44)
    
    d['optics_type'] = fread(f, 'i')
    d['optics_dx'] = fread(f, 'i')
    d['optics_dy'] = fread(f, 'i')
    d['optics_wavelength'] = fread(f, 'i')/1000;  # was microns
    d['optics_dispersion'] = fread(f, 'i')
    d['optics_crossfire_x'] = fread(f, 'i')
    d['optics_crossfire_y'] = fread(f, 'i')
    d['optics_angle'] = fread(f, 'i')
    d['optics_polarization_x'] = fread(f, 'i')
    d['optics_polarization_y'] = fread(f, 'i')
    
    d['reserve5'] = fread(f, 'B'*44)
    
    d['filetitle'] = stringvar(fread(f, 'c'*128))
    d['filepath'] = stringvar(fread(f, 'c'*128))
    d['filename'] = stringvar(fread(f, 'c'*102))
    
    d['aquire_timestamp'] = stringvar(fread(f, 'c'*32))
    d['header_timestamp'] = stringvar(fread(f, 'c'*32))
    d['save_timestamp'] = stringvar(fread(f, 'c'*32))
    d['file_comments'] = stringvar(fread(f, 'c'*512))
    d['dataset_comments'] = stringvar(fread(f, 'c'*512))
    
    #d = ParseDatasetComments(d)
    
    # These wont be needed for anything... so I'll remove them
    d.pop('reserve4_source')
    d.pop('reserve1')
    d.pop('reserve2')
    d.pop('reserve3')
    d.pop('reserve4')
    d.pop('reserve5')
    d.pop('percentile')
    
    d.pop('compression6')
    d.pop('compression4')
    d.pop('compression5')
    d.pop('compression2')
    d.pop('compression3')
    d.pop('compression1')
    
    d.pop('start_chi')
    d.pop('start_kappa')
    
    d.pop('start_twotheta')
    d.pop('start_omega')
    d.pop('start_phi')
    d.pop('start_delta')
    d.pop('start_gamma')
    d.pop('start_xtal_to_detector')
    
    d.pop('end_twotheta')
    d.pop('end_omega')
    d.pop('end_chi')
    d.pop('end_kappa')
    d.pop('end_phi')
    d.pop('end_delta')
    d.pop('end_gamma')
    d.pop('end_xtal_to_detector')
    
    d.pop('detector_roty')
    d.pop('detector_rotx')
    #d.pop('original_header_type') : 2
    d.pop('detector_rotz')
    d.pop('rotation_axis')
    d.pop('rotation_range')
  
    #d.pop('over_16_bits')
    d.pop('magic_number')
    
    d.pop('sequence')            # TRUE or FALSE
    d.pop('nimages') # Total number of images, size of each is nfast
    d.pop('origin')            # Corner of origin
    d.pop('orientation')         # Direction of fast axis
    d.pop('view_direction')     # direction to view frame
    d.pop('overflow_location')    # FOLLOWING_HEADER, FOLLOWING_ DATA
    d.pop('over_8_bits')       # number of pixels with counts > 255
    d.pop('over_16_bits')     # number of pixels with counts > 65535
    d.pop('multiplexed')         # multiplex flag
    d.pop('nfastimages')        # number of images in fast direction
    d.pop('nslowimages')        # number of images in slow direction
    
    d.pop('optics_type') 
    d.pop('optics_dx') 
    d.pop('optics_dy') 
    #d.pop('optics_wavelength') = fread(f, 'i')/1000;  # was microns
    d.pop('optics_dispersion')
    d.pop('optics_crossfire_x') 
    d.pop('optics_crossfire_y') 
    d.pop('optics_angle') 
    d.pop('optics_polarization_x')
    d.pop('optics_polarization_y')
    
    d.pop('source_type')
    d.pop('source_dx')
    d.pop('source_dy')
    #d.pop('source_wavelength')
    d.pop('source_power')
    d.pop('source_voltage')
    d.pop('source_current')
    d.pop('source_bias')
    d.pop('source_polarization_x')
    d.pop('source_polarization_y')
    
    d.pop('nreads')
    
    d.pop('header_type')
    d.pop('header_name')
    d.pop('header_major_version')
    d.pop('header_minor_version')
    d.pop('header_byte_order')
    d.pop('data_byte_order')
    d.pop('header_size')
    d.pop('frame_type')
    
    d.pop('measured_bias')
    d.pop('measured_pressure')
    d.pop('measured_temperature')
    d.pop('mean_bias')
    d.pop('readout_time')
    d.pop('signig_bits')
    
    d.pop('special_counts1')
    d.pop('special_counts2')
    d.pop('stats_uptodate')
    d.pop('total_counts')
    d.pop('rms')
    d.pop('pixel_noise')
    d.pop('data_type')
    d.pop('detector_type')
    d.pop('file_saved')
    d.pop('nheaders')
    d.pop('original_header_type')
    
    return d

def ParseDatasetComments(d):

    comments = d['dataset_comments']

    icpattern = re.compile('Ic=(\d*\.\d*)', re.IGNORECASE)
    bsdpattern = re.compile('BSd=(\d*\.\d*)', re.IGNORECASE)
    beforepattern = re.compile('before=(\d*\.\d*)', re.IGNORECASE)
    afterpattern = re.compile('after=(\d*\.\d*)', re.IGNORECASE)
    #temppattern = re.compile('temp=(\d*\.\d*\s\d*\.\d*)', re.IGNORECASE)
    #temppattern = re.compile('temp=[0-9\W]*', re.IGNORECASE)
    #vacuumpattern = re.compile('vacuum=\d*.*', re.IGNORECASE)            # CAREFULL! THIS IS A NASTY HACK..
                                                                          # TO MAKE IT OK FOR VACUUM = 0
                                                                          # .. I NEED TO LEARN REGULAR EXPERSSIONS BETTER

    try:
        d['ic'] = float(icpattern.search(comments).group().split('=')[1])
    except Exception, msg:
        print 'ERROR reading headervalue "IC": ', str(msg)
        
    try:
        d['bsd'] = float(bsdpattern.search(comments).group().split('=')[1])
    except Exception, msg:
        print 'ERROR reading headervalue "BSD": ', str(msg)
        
    try:
        d['before'] = float(beforepattern.search(comments).group().split('=')[1])
    except Exception, msg:
        print 'ERROR reading headervalue "BEFORE": ', str(msg)
    
    try:
        d['after'] = float(afterpattern.search(comments).group().split('=')[1])
    except Exception, msg:
        print 'ERROR reading headervalue "AFTER": ', str(msg)
    
    #d['temp'] = temppattern.search(comments).group().split('=')[1].strip(';')

    #d['vacuum'] = float(vacuumpattern.search(comments).group().split('=')[1])

    return d

class NotTiffException(Exception):

    def __init__(self, filename):
        self.value = filename + " is not a TIFF format file!"
    
    def __str__(self):
        return repr(self.value)


if __name__ == "__main__":
    
    filename = '/home/specuser/workspace/TestDrivenRaw/src/Tests/TestData/MaxlabMarCCD165.tif'
    
    d = readHeader(filename)
        
    print "testing headerReader.py on " + filename + "...."
    print
    
    print "filename:", d['filename']    
    print "Exposure time:" , d['exposure_time']
    print "Data comment:", d['dataset_comments']
    print ''
    print 'before:',d['before']
    print 'after:', d['after']
    #print 'vacuum:', d['vacuum']
    print 'ic:', d['ic']
    print 'bsd:',d['bsd']
    #print 'temp:' ,d['temp']
    
    print d
    
    
    
