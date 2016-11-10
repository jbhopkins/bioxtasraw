'''
Created on Jul 11, 2010

@author: specuser
'''

import xml.etree.ElementTree as ET
import RAWGlobals, SASImage, SASM, SASIft, SASExceptions
import numpy as np
import os, sys, re, cPickle, time, binascii, struct, json, copy
from xml.dom import minidom
# import SASMarHeaderReader, packc_ext
import SASMarHeaderReader #Attempting to remove the reliance on compiled packages. Switchin Mar345 reading to fabio.

#switched from PIL to pillow
import PIL
from PIL import Image #pillow
from PIL import TiffImagePlugin #pillow

#Trying to make it work for py2app
# import PIL.Image
# import PIL.TiffImagePlugin

# import Image #PIL
# import TiffImagePlugin #PIL
#Need to hack PIL to make it work with py2exe/cx_freeze:
import tifffile
Image._initialized=2

try:
    import fabio
    use_fabio = True

except Exception, e:
    print e
    use_fabio = False

    if RAWGlobals.compiled_extensions:
        try:
            import packc_ext
            read_mar345=True

        except Exception, e1:
                import SASbuild_Clibs
                try:
                    SASbuild_Clibs.buildAll()
                    import packc_ext
                    read_mar345=True

                except Exception, e1:
                    print e1
                    RAWGlobals.compiled_extensions = False
                    print 'Unable to import fabio or pack_ext, Mar345 files cannot be opened.'
                    read_mar345 = False
    else:
        print 'Unable to import fabio or pack_ext, Mar345 files cannot be opened.'
        read_mar345 = False




# try:
#     import nxs
# except Exception:
#     print 'ERROR Loading NeXus Library!'

def createSASMFromImage(img_array, parameters = {}, x_c = None, y_c = None, mask = None,
                        readout_noise_mask = None, tbs_mask = None, dezingering = 0, dezing_sensitivity = 4):
    ''' 
        Load measurement. Loads an image file, does pre-processing:
        masking, radial average and returns a measurement object
    '''
    if mask != None:
        if mask.shape != img_array.shape:
            raise SASExceptions.MaskSizeError('Beamstop mask is the wrong size. Please' +
                            ' create a new mask or remove the old to make this plot.')

    if readout_noise_mask != None:
        if readout_noise_mask.shape != img_array.shape: 
            raise SASExceptions.MaskSizeError('Readout-noise mask is the wrong size. Please' +
                            ' create a new mask or remove the old to make this plot.')

    if tbs_mask != None:
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

    if tbs_mask != None:
        roi_counter = img_array[tbs_mask==1].sum()
        parameters['counters']['roi_counter'] = roi_counter
    
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

def parseTiffTags(filename):
    tag_dict = {}

    try:
        image = open(filename, 'rb')
    except Exception, e:
        print e
        print filename
        print 'Error opening tiff file!'
        image.close()
        return None
        
    #read the first 2 bytes to know "endian"
    start = image.read(2)
    endian = binascii.hexlify(start).upper()

    if endian == "4949":
        symbol = "<"
    elif endian == "4D4D":
        symbol = ">"
    else:
        print "ERROR!"
        return None

    the_answer = image.read(2)
    the_answer = struct.unpack(symbol+'H',the_answer)[0]
   
    if the_answer != 42:
        print 'answer is not 42!!'
        return None
 
    #Figure out where the Image File Directory is. It can be
    #anywhere in the file believe it or not.
    dir_loc = image.read( 4 )
    dir_loc = struct.unpack( symbol+'L', dir_loc )[0]

    #goto that section of the file              
    image.seek(dir_loc)

    #figure out how many tags there are               
    directory_data = image.read(2)
    num_entries = struct.unpack(symbol+'H',directory_data)[0]

    #loop through the Image File Directory and look for the tags we care about
    #Width, Height, SamplesPerPixel, and ColorProfile
    for i in range( num_entries ):
        a_tag = image.read( 12 )
        tag = struct.unpack( symbol+'HHLL', a_tag )

        #catch in case the type is SHORT
        if tag[1] == 3:
            tag = struct.unpack( symbol+'HHLHH', a_tag )

        #set the class attributes if the tag is one we care about
        if tag[0] == 256:
            print tag
            tag_dict['ImageWidth'] = tag[3]

        if tag[0] == 257:
            tag_dict['ImageLength'] = tag[3]

        if tag[0] == 258:
            tag_dict['ColorsPerSample'] = tag[2]

        if tag[0] == 315:
            metadata_loc = tag[3]
            metadata_length = tag[2]

            image.seek( metadata_loc )
            metadata_bytes = image.read( metadata_length )
            
            struct_format = '%s%s%s' % ( symbol, metadata_length, 's' )
            metadata_string = struct.unpack( struct_format, metadata_bytes )[0]

            tag_dict['Artist'] = metadata_string

        if tag[0] == 34675:
            tag_dict['ColorProfile'] = True
            if tag_dict['ColorProfile'] == True:
                icc_loc = tag[3]
                icc_length = tag[2]

                image.seek( icc_loc )
                icc_data = image.read( icc_length )
                struct_format = '%s%s%s' % ( symbol, icc_length, 's' )
                icc_string = struct.unpack( struct_format, icc_data )[0]

                if "Adobe RGB (1998)" in icc_string:
                    tag_dict['ColorProfile'] = "Adobe RGB (1998)"
                elif "sRGB IEC61966-2-1" in icc_string:
                    tag_dict['ColorProfile'] = "sRGB IEC61966-2-1"
                elif "ProPhoto RGB" in icc_string:
                    tag_dict['ColorProfile'] = "Kodak ProPhoto RGB"
                elif "eciRGB" in icc_string:
                    tag_dict['ColorProfile'] = "eciRGB v2"
                elif "e\0c\0i\0R\0G\0B\0" in icc_string:
                    tag_dict['ColorProfile'] = "eciRGB v4"
                else:
                    tag_dict['ColorProfile'] = "Other"
        else:
            tag_dict['ColorProfile'] = "None"

    image.close()
    
    return tag_dict

def loadFabio(filename):
    fabio_img = fabio.open(filename)

    img = fabio_img.data
    img_hdr = fabio_img.getheader()

    img = np.fliplr(img)

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
    except IOError:
        return None, {}
    
    img_hdr = {}
    
    return img, img_hdr

def load32BitTiffImage(filename):
    ''' Load TIFF image '''
    try:
        #im = Image.open(open(filename, 'rb'))
        
        img = tifffile.TiffFile(filename).asarray()
        #im = img.asarray()
        
        #x,y = im.size
        
        #img = np.fromstring(im.tostring(), np.uint32)
        #img = np.reshape(img, (y,x)) 
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
    f.seek(512)                            # Jump over header

    Img = np.fromfile(f, dtype=np.uint16)
    f.close()
    
    xydim = int(np.sqrt(np.shape(Img))[0])    #assuming square image

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
    
    try:
        SizeOfImage = dim[0]
    except TypeError:
        raise SASExceptions.WrongImageFormat("Could not get the dimensions out of the image..")       
    
    
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
        img_hdr = {}
    
    return img, img_hdr

def getMar345ImgDim(filename):
    
    mar_file = open(filename, 'r')
    mar_file.seek(4096)
    
    dim = None
    
    for i in range(0, 5):            # search 5 lines from starting point
        line = mar_file.readline()
        
        if 'CCP' in line:
            splitline = line.split()
            
            x = int(splitline[4].strip(','))
            y = int(splitline[6].strip(','))
            
            dim = x,y
            break
                 
    mar_file.close()
    
    return dim

#fabio only version
# def loadMar345Image(filename):

#     mar345_img = fabio.open(filename)

#     img = mar345_img.data
#     img_hdr = mar345_img.header

#     return img, img_hdr


def loadFrelonImage(filename):
    fo = open(filename, 'rb')
    
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
    
    fo.close()

    img_hdr = header_dict

    return img, img_hdr
    

def loadIllSANSImage(filename):
    
    datafile = open(filename, 'r')
    
    all_lines = datafile.readlines()
    
    datafile.close()
    
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
            image_fount = False
        
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

def loadEdfImage(filename):
    
    fo = open(filename, 'rb')
    
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
    
    img = np.fromfile(fo, dtype='<f4')
    img = np.reshape(img, (dim1, dim2))
    
    fo.close()

    img_hdr = header_dict

    return img, img_hdr

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
        dim = np.shape(newArr)

        
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


def loadMPAFile(filename):

    header_prefix = ''
    data_prefix = ''

    header = {"None" : {}}
    data ={}

    fo = open (filename, 'r')

    lines = fo.readlines()

    fo.close()

    for i in range(len(lines)):
        line = lines[i]
        if line.find('=') > -1:
            key = line.strip().split('=')[0]
            value = '='.join(line.strip().split('=')[1:])

            if header_prefix == '':
                header["None"][key] = value

            else:
                header[header_prefix][key] = value


        else:
            if line.startswith('[DATA') or line.startswith('[CDAT'):
                pos = i
                break

            else:
                header_prefix = line.strip().strip('[]')
                header[header_prefix] = {}

    if header['None']['mpafmt'] == 'asc':
        while pos<len(lines):
            line = lines[pos]

            data_prefix, num = line.strip().strip('[]').split(',')
            # data_lines = np.array([float(fo.readline().strip()) for i in range(int(num))])

            data[data_prefix] = np.array(lines[pos+1:pos+int(num)+1],dtype=float)
            # data[data_prefix] = np.array([float(j.strip()) for j in lines[i+1:i+int(num)+1]])
            pos = pos+int(num)+1
    else:
        print 'cannot recognize the mpa format %s' %(header['None']['mpafmt'])
        return

    img = data['CDAT0'].reshape((int(header['ADC1']['range']), int(header['ADC2']['range'])))

    img_hdr = {}
    for key in header:
        for subkey in header[key]:
            if key == 'None':
                img_hdr[subkey] = header[key][subkey]
            else:
                img_hdr[key+'_'+subkey] = header[key][subkey]

    return img, img_hdr



    

##########################################
#--- ## Parse Counter Files and Headers ##
##########################################

def parseCSVHeaderFile(filename):
    counters = {}
    
    return counters


def parseGaneshaHeader(filename):

        tiff_tags = parseTiffTags( filename )

        xml_header = tiff_tags[ 'Artist' ]

        DOMTree = minidom.parseString( xml_header )
        params = DOMTree.getElementsByTagName( 'param' )

        print params

        return {}


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

def parsePilatusHeader(filename):
    
    param_pattern = re.compile('\d*[:]\d*[:]\d*\D\d*[:]\d*[:]\d*')
    
    try:
        f = open(filename, 'r')
        header = f.read(4096)
        f.close()
        hdr = {}
    except:
        print 'Reading Pilatus header failed'
        return {}
    lineNum = 0
    
    for line in header:
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
            break
               
    # f.close()
 
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
            
    except:
        print 'Reading Quantum header failed'
        return {}

    finally:
        f.close()
        
    return hdr


def parseCHESSF2CTSfile(filename):
    
    timeMonitorPattern = re.compile('\d*-second\s[a-z]*\s[()A-Z,]*\s\d*\s\d*')
    closedShutterCountPattern = re.compile('closed\s\d*')
    datePattern = re.compile('#D\s.*\n')
    
    
    #try:
    f = open(filename[:-3] + 'cts')
    #except Exception as msg:         
    #     error_code = msg.args
    #     raise SASExceptions.FileHeaderNotFoundError(str(msg))
    
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
    
    filenumber = int(underscores[-2].strip('scan'))
    
    try:
        frame_number = int(underscores[-1].split('.')[0])
    except Exception:
        frame_number = 0
        
      
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
    
    file = open(hdr_file,'r')
    
    all_lines = file.readlines()

    file.close()
    
    counters = {}
    
    for each_line in all_lines: 
        split_lines = each_line.split('=')
        key = split_lines[0]
        counters[key] = split_lines[-1][:-1]
        
    return counters


def parseMAXLABI77HeaderFile(filename):
    
    filepath, ext = os.path.splitext(filename)
    hdr_file = filename + '.hdr'
    
    file = open(hdr_file,'r')
    
    all_lines = file.readlines()

    file.close()
    
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

    f=open(countFilename,'r')

    allLines=f.readlines()

    f.close()

    searchName='.'.join(fname.split('.')[:-1])

    line_num=0

    for a in range(1,len(allLines)):
        if searchName in allLines[a]:
            line_num=a

    counters={}

    if line_num>0:
        labels=allLines[0].split('\t')
        vals=allLines[line_num].split('\t')

        for a in range(len(labels)):
            counters[labels[a].strip()]=vals[a].strip()

    else:
        print 'Error loading BioCAT header'


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


def parseBL19U2HeaderFile(filename):
    fname, ext = os.path.splitext(filename)

    countFilename=fname + '.txt'

    counters = {}

    with open(countFilename, 'r') as f:
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

all_header_types = {'None'           : None,
 #                     'CSV'            : parseCSVHeaderFile,
                    'F2, CHESS'         : parseCHESSF2CTSfile, 
                    'G1, CHESS'         : parseCHESSG1CountFile,
                    'G1 WAXS, CHESS'    : parseCHESSG1CountFileWAXS,
                    'I711, MaxLab'      : parseMAXLABI77HeaderFile,
                    'I911-4 Maxlab'     : parseMAXLABI911HeaderFile,
                    'BioCAT, APS'       : parseBioCATlogfile,
                    'BL19U2, SSRF'      : parseBL19U2HeaderFile}

if use_fabio:
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
                       'MPA (multiwire)'    : loadMPAFile
                       # 'NeXus'           : loadNeXusFile,
                                          }

else:
    if read_mar345:   
        all_image_types = {'Quantum'       : loadQuantumImage,
                           'MarCCD 165'       : loadMarCCD165Image,
                           'Mar345'           : loadMar345Image, 
                           'Medoptics'       : loadTiffImage,
                           'FLICAM'           : loadTiffImage,
                           'Pilatus'       : loadPilatusImage,
                           'SAXSLab300'       : loadSAXSLAB300Image,
                           'ESRF EDF'       : loadEdfImage,
                           'FReLoN'           : loadFrelonImage,
                           '16 bit TIF'       : loadTiffImage,
                           '32 bit TIF'       : load32BitTiffImage,
                           # 'NeXus'           : loadNeXusFile,
                           'ILL SANS D11'  : loadIllSANSImage,
                           'MPA (multiwire)'    : loadMPAFile                   }
    else:
        all_image_types = {'Quantum'       : loadQuantumImage,
                       'MarCCD 165'       : loadMarCCD165Image,
                       'Medoptics'       : loadTiffImage,
                       'FLICAM'           : loadTiffImage,
                       'Pilatus'       : loadPilatusImage,
                       'SAXSLab300'       : loadSAXSLAB300Image,
                       'ESRF EDF'       : loadEdfImage,
                       'FReLoN'           : loadFrelonImage,
                       '16 bit TIF'       : loadTiffImage,
                       '32 bit TIF'       : load32BitTiffImage,
                       # 'NeXus'           : loadNeXusFile,
                       'ILL SANS D11'  : loadIllSANSImage,
                       'MPA (multiwire)'    : loadMPAFile                   }


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
     and the type of headerfile     '''
    
    if header_type != 'None':
        try:
            hdr = all_header_types[header_type](filename)
        except IOError as io:
            error_type = io[0]
            raise SASExceptions.HeaderLoadError(str(io).replace("u'",''))
        except Exception as e:
            print e
            raise SASExceptions.HeaderLoadError('Header file for : ' + str(filename) + ' could not be read or contains incorrectly formatted data. ')
    else:
        return {}
    
    return hdr

def loadImage(filename, image_type):
    ''' returns the loaded image based on the image filename
    and image type. '''

    try:
        img, imghdr = all_image_types[image_type](filename)
    except (ValueError, TypeError, KeyError) as msg:
        # print msg
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
        # print 'checking file type'
        print file_type
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
            # print 'using standard RAW calibration and normalization'
            try:
                sasm = SASImage.calibrateAndNormalize(sasm, img, raw_settings)
            except (ValueError, NameError), msg:
                print msg
        
        sasm.setParameter('config_file', raw_settings.get('CurrentCfg'))
          
    else:
        sasm = loadAsciiFile(filename, file_type)
        img = None
    
    if type(sasm) != list:
        SASM.postProcessSasm(sasm, raw_settings)
    
    if file_type == 'image' and no_processing == False:
            SASM.postProcessImageSasm(sasm, raw_settings)
        
    if type(sasm) != list and (sasm is None or len(sasm.i) == 0):
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
        
    img, tmp_hdr = loadImage(filename, img_fmt)

    img_hdr = {}

    for key in tmp_hdr:
        img_hdr[key.replace(' ', '_')] = tmp_hdr[key]

    try:
        json.dumps(img_hdr)
    except UnicodeDecodeError as e:
        for key in img_hdr:
            if type(img_hdr[key]) == str:
                img_hdr[key] = unicode(img_hdr[key], errors='ignore')

    tmp_hdrfile_info = loadHeader(filename, hdr_fmt)

    hdrfile_info = {}

    for key in tmp_hdrfile_info:
        hdrfile_info[key.replace(' ', '_')] = tmp_hdrfile_info[key]


    parameters = {'imageHeader' : img_hdr,
                  'counters'    : hdrfile_info,
                  'filename'    : os.path.split(filename)[1],
                  'load_path'    : filename}

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
        
            if x_y[0] != None: x_c = x_y[0]
            if x_y[1] != None: y_c = x_y[1]
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

            if bs_mask_patches != None:
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
            flatfield_filename = raw_settings.get('NormFlatfieldFile')
            flatfield_img, flatfield_img_hdr = loadImage(flatfield_filename, img_fmt)
            flatfield_hdr = loadHeader(flatfield_filename, hdr_fmt)
            
            if flatfield_filename != None:
                img, img_hdr = SASImage.doFlatfieldCorrection(img, img_hdr, flatfield_img, flatfield_hdr)
            else:
                pass #Raise some error
        
        dezingering = raw_settings.get('ZingerRemovalRadAvg')
        dezing_sensitivity = raw_settings.get('ZingerRemovalRadAvgStd')
        
        sasm = createSASMFromImage(img, parameters, x_c, y_c, bs_mask, dc_mask, tbs_mask, dezingering, dezing_sensitivity)

    else:
        sasm = SASImage.pyFAIIntegrateCalibrateNormalize(img, parameters, x_c, y_c, raw_settings, bs_mask, tbs_mask)

    return sasm, img


def loadOutFile(filename):
    #Loads GNOM .out files into IFTM objects
    qfull = []
    qshort = []
    Jexp = []
    Jerr  = []
    Jreg = []
    Ireg = []

    R = []
    P = []
    Perr = []

    fline = open(filename).readlines()

    outfile = copy.copy(fline)
    
    i = 0
    
    while (i < len(fline)):
        if (fline[i].find('The measure of inconsistency AN1 equals to') > -1): 
            tmp = fline[i].split()
            AN1 = float(tmp[7])
            break 
        i = i + 1
        
    while (i < len(fline)):
        if (fline[i].find('Current') > -1): 
            tmp = fline[i].split()
            Actual_DISCRP = float(tmp[1])
            Actual_OSCILL = float(tmp[2])
            Actual_STABIL = float(tmp[3])
            Actual_SYSDEV = float(tmp[4])
            Actual_POSITV = float(tmp[5])
            Actual_VALCEN = float(tmp[6])
            break
        i = i + 1

    while (i < len(fline)):
        if (fline[i].find('Total  estimate') > -1): 
            tmp = fline[i].split()
            TE_out = float(tmp[3])
            quality = ' '.join(tmp[6:])
            break
        i = i + 1

            
    while (i < len(fline)):
        if (fline[i].find('S          J EXP       ERROR       J REG       I REG') > -1): break 
        i = i + 1

    i = i + 2
      
# extract experimental and fitted profiles
      
    while (i < len(fline)):
          
        tmp = fline[i].split()
          
        if (len(tmp) == 2):
            qfull.append(float(tmp[0]))
            Ireg.append(float(tmp[1]))
        elif (len(tmp)==5):
            qfull.append(float(tmp[0]))
            qshort.append(float(tmp[0]))
            Jexp.append(float(tmp[1]))
            Jerr.append(float(tmp[2]))
            Jreg.append(float(tmp[3]))
            Ireg.append(float(tmp[4]))
        else: 
            break
        
        i = i + 1
          
# now search for P(r)
          
    i = i + 6
          
    while (i < len(fline)):
              
        tmp = fline[i].split()
            
        if (len(tmp) == 3):
            R.append(float(tmp[0]))
            P.append(float(tmp[1]))
            Perr.append(float(tmp[2]))
        else: 
            break
        
        i = i + 1

    i = i + 1
    tmp = fline[i].split()
    if len(tmp)==12:
        Rg_out = float(tmp[4])
        rger = float(tmp[6])
        I0=float(tmp[9])
        I0er=float(tmp[11])

    else:
        tmp=fline[i]
        Rg_out=float(tmp[tmp.find('=')+1:tmp.find('+-')])
        if tmp[tmp.find('+-')+2:tmp.find('I(0)')].startswith('**'):
            rger=-1
        else:
            rger=float(tmp[tmp.find('+-')+2:tmp.find('I(0)')])
        index1=tmp.find('I(0)')
        tmp2=tmp[index1:]
        I0=float(tmp2[tmp2.find('=')+1:tmp2.find('+-')])
        I0er=float(tmp2[tmp2.find('+-')+2:])

    # Output variables not in the results file:
    # 'r'         : R,            #R, note R[-1] == Dmax
    #             'p'         : P,            #P(r)
    #             'perr'      : Perr,         #P(r) error
    #             'qlong'     : qfull,        #q down to q=0
    #             'qexp'      : qshort,       #experimental q range
    #             'jexp'      : Jexp,         #Experimental intensities
    #             'jerr'      : Jerr,         #Experimental errors
    #             'jreg'      : Jreg,         #Experimental intensities from P(r)
    #             'ireg'      : Ireg,         #Experimental intensities extrapolated to q=0

    name = os.path.basename(filename)

    results = { 'dmax'      : R[-1],        #Dmax
                'TE'        : TE_out,       #Total estimate
                'rg'        : Rg_out,       #Real space Rg
                'rger'      : rger,         #Real space rg error
                'i0'        : I0,           #Real space I0
                'i0er'      : I0er,         #Real space I0 error,
                'out'       : outfile,      #Full contents of the outfile, for writing later
                'quality'   : quality,      #Quality of GNOM out file
                'chisq'     : Actual_DISCRP,#DISCRIP, chi squared
                'oscil'     : Actual_OSCILL,#Oscillation of solution
                'stabil'    : Actual_STABIL,#Stability of solution
                'sysdev'    : Actual_SYSDEV,#Systematic deviation of solution
                'positv'    : Actual_POSITV,#Relative norm of the positive part of P(r)
                'valcen'    : Actual_VALCEN,#Validity of the chosen interval in real space
                'filename'  : name,         #GNOM filename
                'algorithm' : 'GNOM'        #Lets us know what algorithm was used to find the IFT
                    }

    iftm = SASM.IFTM(P, R, Perr, Jexp, qshort, Jerr, Jreg, results, Ireg, qfull)

    return [iftm]


def loadSECFile(filename):
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

    new_secm, line_data, calc_line_data = makeSECFile(secm_data)

    new_secm.setParameter('filename', os.path.split(filename)[1])

    return new_secm


def makeSECFile(secm_data):

    default_dict =     {'sasm_list'             : [],
                        'file_list'             : [],
                        'frame_list'            : [],
                        'parameters'            : {},
                        'initial_buffer_frame'  : -1,
                        'final_buffer_frame'    : -1,
                        'window_size'           : -1,
                        'mol_type'              : '',
                        'threshold'             : -1,
                        'rg'                    : [],
                        'rger'                  : [],
                        'i0'                    : [],
                        'i0er'                  : [],
                        'mw'                    : [],
                        'mwer'                  : [],
                        'calc_has_data'         : False,
                        'subtracted_sasm_list'  : [],
                        'use_subtracted_sasm'   : [],
                        'average_buffer_sasm'   : None                        
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

    # print sasm_list

    new_secm = SASM.SECM(secm_data['file_list'], sasm_list, secm_data['frame_list'], secm_data['parameters'])

    new_secm.setCalcParams(secm_data['intial_buffer_frame'], secm_data['final_buffer_frame'], secm_data['window_size'], secm_data['mol_type'], secm_data['threshold'])
    new_secm.setRgAndI0(secm_data['rg'], secm_data['rger'], secm_data['i0'], secm_data['i0er'])
    new_secm.setMW(secm_data['mw'], secm_data['mwer'])
    new_secm.calc_has_data = secm_data['calc_has_data']

    subtracted_sasm_list = []

    for item in secm_data['subtracted_sasm_list']:
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

        subtracted_sasm_list.append(new_sasm)

    new_secm.setSubtractedSASMList(subtracted_sasm_list, secm_data['use_subtracted_sasm'])


    sasm_data = secm_data['average_buffer_sasm']
        
    if sasm_data != -1 and sasm_data != None:
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

    new_secm.setAverageBufferSASM(new_sasm)


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
    except KeyError:
        line_data = None    #Backwards compatibility
        secm_data['line_visible'] = True

    return new_secm, line_data, calc_line_data


def loadIftFile(filename):
    #Loads RAW BIFT .ift files into IFTM objects
    iq_pattern = re.compile('\s*\d*[.]\d*[+eE-]*\d+\s+-?\d*[.]\d*[+eE-]*\d+\s+\d*[.]\d*[+eE-]*\d+\s+\d*[.]\d*[+eE-]*\d+\s*$')
    three_col_fit = re.compile('\s*\d*[.]\d*[+eE-]*\d+\s+-?\d*[.]\d*[+eE-]*\d+\s+\d*[.]\d*[+eE-]*\d+\s*$')
    
    p = []
    r = []
    err = []

    f = open(filename)
        
    # parameters = {'filename' : os.path.split(filename)[1],
    #               'counters' : {}}
    
    path_noext, ext = os.path.splitext(filename)
    
    try:
        
        for line in f:

            threecol_match = three_col_fit.match(line)

            if threecol_match:
                #print line
                found = threecol_match.group().split()

                r.append(float(found[0]))
                p.append(float(found[1]))
                err.append(float(found[2]))
            
        err = np.ones(len(p))

    finally:
        f.close()

    p = np.array(p)
    r = np.array(r)
    err = np.array(err)
    
    # sasm = SASM.SASM(p, r, err, parameters)
   
    ######################### LOAD FIT ###########################
    i = []
    q = []
    err_orig = []
    fit = []

    sasm_orig = None
    sasm_fit = None

    f = open(filename)
    
    # parameters_orig = {'filename' : os.path.split(filename)[1] + '_ORIG',
    #                   'counters' : {}}
    
    # parameters_fit = {'filename' : os.path.split(filename)[1] + '_FIT',
    #                   'counters' : {}}
    
    # path_noext, ext = os.path.splitext(filename)
    
    try:  
        for line in f:

            fourcol_match = iq_pattern.match(line)

            if fourcol_match:
                #print line
                found = fourcol_match.group().split()

                q.append(float(found[0]))
                i.append(float(found[1]))
                err_orig.append(float(found[2]))
                fit.append(float(found[3]))
                
        
        i = np.array(i)
        q = np.array(q)
        err_orig = np.array(err_orig)
        fit = np.array(fit)
    
        # orig_sasm = SASM.SASM(i, q, err, parameters_orig)
        # fit_sasm = SASM.SASM(fit, q, err, parameters_fit)
    
        # parameters['orig_sasm'] = orig_sasm
        # parameters['fit_sasm'] = fit_sasm
    except Exception, e:
        print 'No fit data found, or error loading fit data'
        print e

    finally:
        f.close()


    #Check to see if there is any header from RAW, and if so get that.
    f = open(filename)
    all_lines = f.readlines()
    f.close()
    header = []
    for j in range(len(all_lines)):
        if '### HEADER:' in all_lines[j]:
            header = all_lines[j+1:]

    hdict = None

    if len(header)>0:
        hdr_str = ''
        for each_line in header:
            hdr_str=hdr_str+each_line
        try:
            hdict = dict(json.loads(hdr_str))
            print 'Loading RAW info/analysis...'
        except Exception, e:
            print 'Unable to load header/analysis information. Maybe the file was not generated by RAW or was generated by an old version of RAW?'
            hdict = {}

    parameters = hdict
    parameters['filename'] = os.path.split(filename)[1]

    iftm = SASM.IFTM(p, r, err, i, q, err_orig, fit, parameters)
    
    return [iftm]
    
    
def loadFitFile(filename):

    iq_pattern = re.compile('\s*\d*[.]\d*[+eE-]*\d+\s+-?\d*[.]\d*[+eE-]*\d+\s+\d*[.]\d*[+eE-]*\d+\s+\d*[.]\d*[+eE-]*\d+\s*$')
    three_col_fit = re.compile('\s*\d*[.]\d*[+eE-]*\d+\s+-?\d*[.]\d*[+eE-]*\d+\s+\d*[.]\d*[+eE-]*\d+\s*$')
    five_col_fit = re.compile('\s*\d*[.]\d*[+eE-]*\d+\s+-?\d*[.]\d*[+eE-]*\d+\s+\d*[.]\d*[+eE-]*\d+\s+\d*[.]\d*[+eE-]*\d+\s+-?\d*[.]\d*[+eE-]*\d+\s*$')

    i = []
    q = []
    err = []
    fit = []

    has_three_columns = False

    f = open(filename)
    
    firstLine = f.readline()
    
    three_col_match = three_col_fit.match(firstLine)
    if three_col_match:
        has_three_columns = True
        fileHeader = {}
    else:
        fileHeader = {'comment':firstLine}
    
    
    if "Experimental" in firstLine:
        sasref = True      #SASREFMX Fit file (Damn those hamburg boys and their 50 different formats!)
    else:
        sasref = False
    
    parameters = {'filename' : os.path.split(filename)[1],
                  'counters' : fileHeader}
    
    path_noext, ext = os.path.splitext(filename)

    fit_parameters = {'filename'  : os.path.split(path_noext)[1] + '_FIT',
                      'counters' : {}}
    
    try:
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

    finally:
        f.close()

    if len(i) == 0:
        raise SASExceptions.UnrecognizedDataFormat('No data could be retrieved from the file, unknown format.')
    
    i = np.array(i)
    q = np.array(q)
    err = np.array(err)
    fit = np.array(fit)
    
    
    fit_sasm = SASM.SASM(fit, np.copy(q), np.copy(err), fit_parameters)
   
    sasm = SASM.SASM(i, q, err, parameters)
    
    return [sasm, fit_sasm]



def loadPrimusDatFile(filename):
    ''' Loads a Primus .dat format file '''
    
    iq_pattern = re.compile('\s*\d*[.]\d*[+eE-]*\d+\s+-?\d*[.]\d*[+eE-]*\d+\s+\d*[.]\d*[+eE-]*\d+\s*')

    i = []
    q = []
    err = []

    f = open(filename)
    
    # firstLine = f.readline()

    lines = f.readlines()

    firstLine = lines[0]

    iq_match = iq_pattern.match(firstLine)

    if iq_match:
        firstLine = ''
    
    fileHeader = {'comment':firstLine}
    parameters = {'filename' : os.path.split(filename)[1],
                  'counters' : fileHeader}

    

    f.close()

    if len(lines) == 0:
        raise SASExceptions.UnrecognizedDataFormat('No data could be retrieved from the file.')

    if lines[1].find('model_intensity') > -1:
        #FoXS file with a fit! has four data columns
        is_foxs_fit=True
        comment = firstLine+'\n'+lines[0]+lines[1]
        parameters['comment']=comment
        lines = lines[2:]
        imodel = []

    else:
        is_foxs_fit = False
    
    
    for line in lines:

        if not is_foxs_fit:

            iq_match = iq_pattern.match(line)

            if iq_match:
                #print line
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
    f = open(filename)
    all_lines = f.readlines()
    f.close()
    header = []
    for j in range(len(all_lines)):
        if '### HEADER:' in all_lines[j]:
            header = all_lines[j+1:]

    hdict = None

    if len(header)>0:
        hdr_str = ''
        for each_line in header:
            hdr_str=hdr_str+each_line
        try:
            hdict = dict(json.loads(hdr_str))
            print 'Loading RAW info/analysis...'
        except Exception, e:
            # print 'Unable to load header/analysis information. Maybe the file was not generated by RAW or was generated by an old version of RAW?'
            hdict = {}


    i = np.array(i)
    q = np.array(q)
    err = np.array(err)

    if hdict:
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

    iq_pattern = re.compile('\s*\d*[.]\d*[+eE-]*\d+\s+-?\d*[.]\d*[+eE-]*\d+\s+-?\d*[.]\d*[+eE-]*\d+\s*\n')
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


def loadCsvFile(filename):
    ''' Loads a comma separated file, ignores everything except a three column line'''
    
    
    iq_pattern = re.compile('\s*\d*[.]?\d*[+eE-]*\d+[,]\s*-?\d*[.]?\d*[+eE-]*\d+[,]\s*-?\d*[.]?\d*[+eE-]*\d*\s*\n')
    param_pattern = re.compile('[a-zA-Z0-9_]*\s*[=].*')

    i = []
    q = []
    err = []
    
    fileheader = {}

    f = open(filename)
    
    try:
        for line in f:

            iq_match = iq_pattern.match(line)
            param_match = param_pattern.match(line)

            if iq_match:
                found = iq_match.group().split(',')
                
                q.append(float(found[0].rstrip('\r\n')))
                
                i.append(float(found[1].rstrip('\r\n')))
                
                err.append(float(found[2].rstrip('\r\n')))
                
            else:
                print 'No match:'
                print line
                
            if param_match:
                found = param_match.group().split('=')

                if len(found) == 2:
                    try:
                        val = float(found[1].rstrip('\r\n'))
                    except ValueError:
                        val = found[1].rstrip('\r\n')
                
                    fileheader[found[0]] = val
                    
    finally:
        f.close()

    parameters = {'filename' : os.path.split(filename)[1],
                  'counters' : fileheader}

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


# def loadBiftFile(filename):
    
#     iq_pattern = re.compile('\s*\d*[.]\d*[+eE-]*\d+\s+[+-]*\d*[.]\d*[+Ee-]*\d+\s+\d*[.]\d*[+eE-]*\d+\s*\n')
#     param_pattern = re.compile('[a-zA-Z0-9_]*\s*[:]\s+.*')
    
#     bift_param_pattern = re.compile('\s\s\s[a-zA-Z0-9_]*\s*[:]\s+.*')
    
#     iq_orig_pattern = re.compile('\s*\d*[.]\d*[+eE-]*\d+\s+-?\d*[.]\d*[+eE-]*\d+\s+\d*[.]\d*[+eE-]*\d+\s+\d*[.]\d*[+eE-]*\d+\s*\n')

#     i = []
#     q = []
#     err = []
    
#     i_orig = []
#     q_orig = []
#     err_orig = []
#     fit = []
#     d = {}
#     allData = {}
     

#     f = open(filename)
    
#     try:
#         for line in f:

#             iq_match = iq_pattern.match(line)
#             param_match = param_pattern.match(line)
#             iq_orig_match = iq_orig_pattern.match(line)
#             bift_param_match = bift_param_pattern.match(line)

#             if iq_match:
#                 found = iq_match.group().split()
#                 q.append(float(found[0]))
#                 i.append(float(found[1]))
#                 err.append(float(found[2]))
                
#             if iq_orig_match:
#                 found = iq_orig_match.group().split()
#                 q_orig.append(float(found[0]))
#                 i_orig.append(float(found[1]))
#                 err_orig.append(float(found[2]))
#                 fit.append(float(found[3]))
            
#             if bift_param_match:
#                 found = bift_param_match.group().split()
                
#                 try:
#                     val = float(found[2])
#                 except ValueError:
#                     val = found[2]
                
#                 allData[found[0]] = val
                
                
#             if param_match:
#                 found = param_match.group().split()

#                 if len(found) == 3:
#                     try:
#                         val = float(found[2])
#                     except ValueError:
#                         val = found[2]
                
#                     d[found[0]] = val
                
#                 elif len(found) > 3:
#                     arr = []
#                     for each in range(2,len(found)):
#                         try:
#                             val = float(found[each])
#                         except ValueError:
#                             val = found[each]
                        
#                         arr.append(val)
                    
#                     d[found[0]] = arr
#                 else:
#                     d[found[0]] = ''

#     finally:
#         f.close()
    
#     P = np.array(i)
#     R = np.array(q)
#     err = np.array(err)
   
#     allData['orig_q'] = q_orig
#     allData['orig_i'] = i_orig
#     allData['orig_err'] = err_orig

#     return SASIft.IFTM(P, R, err, d, fit, allData)

#####################################
#--- ## Write RAW Generated Files: ##
#####################################

# WORK IN PROGRESS:
def saveMeasurement(sasm, save_path, raw_settings, filetype = '.dat'):
    ''' Saves a Measurement Object to a .rad file.
        Returns the filename of the saved file '''
    
    filename, ext = os.path.splitext(sasm.getParameter('filename'))
    
    header_on_top = raw_settings.get('DatHeaderOnTop')
    
    if filetype == '.ift':
        writeIftFile(sasm, os.path.join(save_path, filename + filetype))
    elif filetype == '.out':
        writeOutFile(sasm, os.path.join(save_path, filename + filetype))
    else:
        writeRadFile(sasm, os.path.join(save_path, filename + filetype), header_on_top)


def saveSECItem(save_path, secm_dict):

    file = open(save_path, 'wb')

    cPickle.dump(secm_dict, file, cPickle.HIGHEST_PROTOCOL)
    
    file.close()


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
            
    file.close()
    
    return True

def saveAllAnalysisData(save_path, sasm_list, delim=','):
    #Exports all analysis data from multiple sasm objects into delimited form. Default is space delimited
    f=open(save_path, 'w')

    date = time.ctime()
    
    #Write the first lines in the file: 
    f.write('RAW_ANALYSIS_DATA\n')
    f.write(str(date).replace(' ', '_') + '\n')
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


    f.write(delim.join(header_list)+'\n')


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
            
    f.close()

def saveSECData(save_path, selected_secm, delim=','):
    #Exports the data from a SEC object into delimited form. Default is space delimited
    f=open(save_path, 'w')

    if selected_secm.qref != 0:
        saveq=True
    else:
        saveq=False

    time = selected_secm.getTime()

    if len(time)>0 and time[0] != -1 and len(time) == len(selected_secm.frame_list):
        savetime = True
    else:
        savetime = False

    savecalc = selected_secm.calc_has_data


    f.write('Frame_#%sIntegrated_Intensity%sMean_Intensity%s' %(delim, delim, delim))
    if saveq:
        f.write('I_at_q=%f%s' %(selected_secm.qref, delim))
    if savetime:
        f.write('Time_(s)%s' %(delim))
    if savecalc:
        f.write('Rg_(A)%sRger_(A)%sI0%sI0er%sMW_(kDa)%s' %(delim, delim, delim, delim, delim))
    f.write('File_Name\n')

    for a in range(len(selected_secm._sasm_list)):
        f.write('%i%s%f%s%f%s' %(selected_secm.frame_list[a], delim, selected_secm.total_i[a], delim, selected_secm.mean_i[a], delim))
        if saveq:
            f.write('%f%s' %(selected_secm.I_of_q[a], delim))
        if savetime:
            f.write('%f%s' %(time[a], delim))
        if savecalc:
            f.write('%f%s%f%s%f%s%f%s%f%s' %(selected_secm.rg_list[a], delim, selected_secm.rger_list[a], delim, selected_secm.i0_list[a], delim, selected_secm.i0er_list[a], delim, selected_secm.mw_list[a], delim))
        f.write('%s\n' %(selected_secm._file_list[a].split('/')[-1]))
            
    f.close()
    
def saveWorkspace(sasm_dict, save_path):

    file = open(save_path, 'wb')

    cPickle.dump(sasm_dict, file, cPickle.HIGHEST_PROTOCOL)
    
    file.close()


def saveCSVFile(filename, data, header = ''):
    if header != '':
        np.savetxt(filename, data, delimiter = ',', header = header, comments = '')
    else:
        np.savetxt(filename, data, delimiter = ',', comments ='')


def saveSVDData(filename, svd_data, u_data, v_data):

    with open(filename, 'w') as fsave:
        fsave.write('Singular_values,U_Autocorrelation,V_Autocorrelation\n')

        for line in svd_data:
            fsave.write(','.join(map(str, line))+'\n')

        fsave.write('\n\n')
        fsave.write('U_matrix_(left_singular_vectors)\n')

        for line in u_data:
            fsave.write(','.join(map(str, line))+'\n')

        fsave.write('\n\n')
        fsave.write('V_matrix_(right_singular_vectors)\n')

        for line in v_data:
            fsave.write(','.join(map(str, line))+'\n')


def saveEFAData(filename, panel1_results, panel2_results, panel3_results):
    framei = panel1_results['fstart']
    framef = panel1_results['fend']
    index = range(framei, framef+1)

    nvals = panel1_results['input']

    qvals = panel1_results['q']

    header_string = ''

    header_string = header_string + '# SEC data name: %s\n' %(panel1_results['filename'])
    header_string = header_string + '# Started at SEC frame: %s\n' %(str(framei))
    header_string = header_string + '# Ended at SEC frame: %s\n' %(str(framef))
    header_string = header_string + '# Used: %s\n' %(panel1_results['profile'])
    header_string = header_string + '# Number of significant singular values: %s\n' %(str(nvals))
    header_string = header_string + '# Component Ranges:\n'
    for i in range(len(panel3_results['ranges'])):
        header_string = header_string + '#\tRange %i: %i to %i\n' %(i, panel3_results['ranges'][i][0], panel3_results['ranges'][i][1])
    header_string = header_string + '# Rotation setings: Iterations: %s   Convergence threshold: %s\n' %(panel3_results['options']['niter'], panel3_results['options']['tol'])
    header_string = header_string + '# Rotation converged: %s\n' %(str(panel3_results['converged']))
    if panel3_results['converged']:
        header_string = header_string + '# Rotation results: Iterations: %s\n' %(panel3_results['iterations'])
    header_string = header_string + '\n'

    body_string = ''
    if panel3_results['converged']:
        body_string = body_string+'Concentration Matrix Results\n'
        body_string = body_string+'Index,'+','.join(['Value_%i' %i for i in range(nvals)])+'\n'

        conc = panel3_results['conc']

        conc_output = np.column_stack((index, conc))

        for line in conc_output:
            body_string = body_string+','.join(map(str, line)) + '\n'

        body_string = body_string +'\n'


        body_string = body_string+'Rotation Chi^2\n'
        body_string = body_string+'Index,Chi^2\n'

        chisq = panel3_results['chisq']

        chisq_output = np.column_stack((index, chisq))

        for line in chisq_output:
            body_string = body_string+','.join(map(str, line)) + '\n'

        body_string = body_string +'\n'


    body_string = body_string + 'Forward EFA Results\n'
    body_string = body_string + 'Index,'+','.join(['Value_%i' %i for i in range(nvals+1)])+'\n'

    fefa = panel2_results['forward_efa'].T[:,:nvals+1]
    fefa_output = np.column_stack((index, fefa))

    for line in fefa_output:
        body_string = body_string+','.join(map(str, line)) + '\n'

    body_string = body_string +'\n'


    body_string = body_string + 'Backward EFA Results\n'
    body_string = body_string + 'Index,'+','.join(['Value_%i' %i for i in range(nvals)])+'\n'

    befa = panel2_results['backward_efa'][:, ::-1].T[:,:nvals+1]
    befa_output = np.column_stack((index, befa))

    for line in befa_output:
        body_string = body_string+','.join(map(str, line)) + '\n'

    body_string = body_string +'\n'


    body_string = body_string + 'Singular Value Results\n\n'
    body_string = body_string + 'Singular Values\n'
    body_string = body_string + 'Index,Value\n'

    svs = panel1_results['svd_s']

    svs_output = np.column_stack((range(len(svs)),svs))

    for line in svs_output:
        body_string = body_string+','.join(map(str, line)) + '\n'

    body_string = body_string +'\n'


    body_string = body_string + 'Left Singular Vectors (U)\n'
    body_string = body_string + 'Q,'+','.join(['Column_%i' %i for i in range(nvals)])+'\n'

    svd_u = panel1_results['svd_u'].T[:,:nvals]
    svd_u_output = np.column_stack((qvals, svd_u))

    for line in svd_u_output:
        body_string = body_string+','.join(map(str, line)) + '\n'

    body_string = body_string +'\n'


    body_string = body_string + 'Right Singular Vectors (V)\n'
    body_string = body_string + 'Index,'+','.join(['Column_%i' %i for i in range(nvals)])+'\n'

    svd_v = panel1_results['svd_v'][:,:nvals]
    svd_v_output = np.column_stack((index, svd_v))

    for line in svd_v_output:
        body_string = body_string+','.join(map(str, line)) + '\n'

    body_string = body_string +'\n'

    save_string = header_string + body_string


    with open(filename, 'w') as fsave:
        fsave.write(save_string)

    
def loadWorkspace(load_path):
    
    file = open(load_path, 'r')

    try:
        sasm_dict = cPickle.load(file)
    except (ImportError, EOFError), e:
        print e
        print 'Error loading wsp file, trying different method.'
        file.close()
        file = open(load_path, 'rb')
        sasm_dict = cPickle.load(file)
    finally:
        file.close()
    
    return sasm_dict


def writeHeader(d, f2, ignore_list = []):
    f2.write('### HEADER:\n\n')
    
    ignore_list.append('fit_sasm')
    ignore_list.append('orig_sasm')

    for ignored_key in ignore_list:
        if ignored_key in d.keys():
            del d[ignored_key]

    f2.write(json.dumps(d,indent = 4, sort_keys = True))
    
    f2.write('\n\n')
    

def writeRadFile(m, filename, header_on_top = True):
    ''' Writes an ASCII file from a measurement object, using the RAD format '''
    
    d = m.getAllParameters()
    
    f2 = open(filename, 'w')
    
    if header_on_top == True:
        writeHeader(d, f2)
    
    q_min, q_max = m.getQrange()

    f2.write('### DATA:\n\n')
    f2.write('         Q               I              Error\n')
    f2.write('%d\n' % len(m.i[q_min:q_max]))
        
    fit = np.zeros(np.size(m.q))
    
    for idx in range(q_min, q_max):
        line = ('%.8E %.8E %.8E\n') % ( m.q[idx], m.i[idx], m.err[idx])
        f2.write(line)
    
    f2.write('\n')
    if header_on_top == False:
        f2.write('\n')
        writeHeader(d, f2)
     
    f2.close()

def printDict(d, each):

    tmpline = each + ' '+ json.dumps(d[each], indent = 4, sort_keys=True)+'\n'
    
    return tmpline

def writeIftFile(m, filename):
    ''' Writes an ASCII file from an IFT measurement object created by BIFT'''
    
    d = m.getAllParameters()
    f2 = open(filename, 'w')
    no_path_filename = m.getParameter('filename')
    
    f2.write('BIFT\n')
    f2.write('Filename: ' + no_path_filename + '\n\n' )
    f2.write('         R            P(R)             Error\n')
    
    for idx in range(0,len(m.p)):
        line = ('%.8E %.8E %.8E\n') %( m.r[idx], m.p[idx], m.err[idx])
        f2.write(line)
    
    f2.write('\n\n')
     
     
    bift_info = m.getParameter('bift_info')
    
    orig_q = m.q_orig
    orig_i = m.i_orig
    orig_err = m.err_orig
    fit = m.i_fit
     
    f2.write('            Q              I(q)             Error          Fit\n')
    for idx in range(0,len(orig_q)):
        line = ('%.8E %.8E %.8E %.8E\n') %( orig_q[idx], orig_i[idx], orig_err[idx], fit[idx])
        f2.write(line)
    
    f2.write('\n')
    
    ignore_list = ['all_posteriors', 'alpha_points', 'fit', 'orig_i', 'orig_q',
                   'orig_err', 'dmax_points', 'orig_sasm', 'fit_sasm']
    
    writeHeader(d, f2, ignore_list)
    
    f2.close()
    

def writeOutFile(m, filename):
    ''' Writes an ASCII file from an IFT measurement object created by GNOM'''
    
    outfile = outfile = m.getParameter('out')

    f = open(filename, 'w')

    for line in outfile:
        f.write(line)

    f.close()
     


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

    if type_tst == 'RR':
        return 'image'
    elif type_tst == 'II':   # Test if file is a TIFF file (first two bytes are "II")
        return 'image'
    elif ext == '.fit':
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
    #elif type_tst == 'BI':
    #    return 'bift'
    elif ext == '.dat' or ext == '.sub':
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
        
        
        
