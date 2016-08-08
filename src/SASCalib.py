'''
Created on Jul 11, 2010

@author: Soren S. Nielsen
'''
import numpy as np
from math import pi, asin, tan, atan, cos, sin, asin

def calcAbsScaleConstWater(water_sasm, start_idx, end_idx):
    '''
        Calculates the absolute scaling constant using water (with empty cell subtracted).
        (This constant is multiplied to the background subtracted samples to obtain
        it on absolute scale.)
        
        Currently only precise for 25 deg and 9.47 keV
        Should be extended to include other temperatures and energies     
        see http://www.ncnr.nist.gov/resources/sldcalc.html to calc for other temperatures
    '''

    avg_water = np.average(water_sasm.i[start_idx:end_idx])
    
    abs_scale_constant = 0.0162 / avg_water

    return abs_scale_constant
                        
def calcTheta(sd_distance, pixel_size, q_length_pixels):
    ''' 
     Calculates theta for a sample-detector distance,
     the detector pixel size and the length of the pixels.
     
     sd_distance = sample detector distance
     pixel_size = Detector pixel size
     q__pixel_length = length of q-vector in pixels. 
    '''
    
    if q_length_pixels == 0:
        return 0
    else:
        theta = .5 * atan( (q_length_pixels * pixel_size) / sd_distance )
        return theta

def calcSolidAngleCorrection(sasm, sd_distance, pixel_size):
    '''
      returns an array that should be multiplied to the intensity values
      calculated to apply the solid angle correction. 
      
      This compensates for the fact that the detector face is assumed to be planar.
      Thus, as you move out on the detector, each pixel subtends a smaller solid angle,
      and so absorbs fewer pixels. This results in artificially low intensities at high
      q. This can be compensated for by dividing by the ratio of the solid angles,
      which is proportional to cos(2*theta)^3. 

      pixel_size = Detector Pixel Size in millimeters
      max_length = maximum q-vector length in pixels
      sd_distance = Sample-Detector distance
      
    '''

    q_list = sasm.q
    iac = np.ones(len(q_list))
    
    for idx in range(0,len(iac)):
        iac[idx] = np.power( cos( 2 * calcTheta(sd_distance, pixel_size, q_list[idx]) ),3 )    #cos^3(2*theta)
        
    return iac
  
def calcDistanceFromAgBeh(first_ring_dist, pixel_size, wavelength):
    ''' Calculates sample detector distance from the rings 
        of Silver Behenate. 
        
         first_ring_dist = Distance to 1st circle in AgBe measurement in pixels
        
         q = ( 4 * pi * sin(theta)) / wavelength
         tan(theta) = opposite / adjacent
         
         pixel_size : detector pixelsize in mm 
     
         Ouput:
         sd_distance = Sample Detector Distance in mm
    '''
    
    q = 0.107625  # Q for 1st cirle in AgBeh
    
    sin_theta = (q * wavelength) / (4 * pi)
    
    theta = asin(sin_theta)
    
    opposite = first_ring_dist * pixel_size
    adjacent = opposite / tan(2*theta)
    
    sd_distance = adjacent
    
    return sd_distance