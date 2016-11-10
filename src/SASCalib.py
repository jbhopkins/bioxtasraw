'''
Created on Jul 11, 2010

@author: Soren S. Nielsen
'''
import numpy as np
from math import pi, asin, tan, atan, cos, sin, asin
import sys
import RAWGlobals

try:
    import pyFAI, pyFAI.calibrant, pyFAI.calibration
    RAWGlobals.usepyFAI = True
except:
    RAWGlobals.usepyFAI = False

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

      Inputs:
      pixel_size = Detector Pixel Size in millimeters
      sd_distance = Sample-Detector distance
      sasm, with the q vector still in pixel units, rather than calibrated to A^-1.
      
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


#########################################
#Methods adapted from pyFAI methods of the same or similar name to automatically get points in calibrant rings and fit them

def new_grp(img, loc, gpt, defaultNbPoints, ring):

    massif = pyFAI.massif.Massif(img)
    points = massif.find_peaks([loc[1], loc[0]], defaultNbPoints)
    if points:
        gpt.append(points, ring=ring)

    return points, gpt


class RAWCalibration():
    # A mash up of the pyFAI.calibration AbstractCalibration and Calibration classes

    PARAMETERS = ["dist", "poni1", "poni2", "rot1", "rot2", "rot3", "wavelength"]

    def __init__(self, img, wavelength = None, detector = None, calibrant = None, pixelSize = None, gaussianWidth = None):
        self.gaussianWidth = gaussianWidth
        self.detector = detector
        self.calibrant = calibrant
        self.pixelSize = pixelSize
        self.wavelength = wavelength
        self.img = img

        self.fixed = pyFAI.utils.FixedParameters()
        self.fixed.add_or_discard("wavelength", True)
        self.fixed.add_or_discard("rot1", True)
        self.fixed.add_or_discard("rot2", True)
        self.fixed.add_or_discard("rot3", True)
        self.max_iter = 1000
        self.interactive = False
        self.weighted = False

    def initgeoRef(self):
        # Modified initgeoRef from the pyFAI.calibration.Calibration class
            """
            Tries to initialise the GeometryRefinement (dist, poni, rot)
            Returns a dictionary of key value pairs
            """
            defaults = {"dist": 0.1, "poni1": 0.0, "poni2": 0.0,
                        "rot1": 0.0, "rot2": 0.0, "rot3": 0.0}
            if self.detector:
                try:
                    p1, p2, _p3 = self.detector.calc_cartesian_positions()
                    defaults["poni1"] = p1.max() / 2.
                    defaults["poni2"] = p2.max() / 2.
                except Exception as err:
                    print err
            if self.ai:
                for key in defaults.keys():  # not PARAMETERS which holds wavelength
                    val = getattr(self.ai, key, None)
                    if val is not None:
                        defaults[key] = val
            return defaults

    def refine(self):
        # Modified refine from the pyFAI.calibration.Calibration class
        """
        Contains the geometry refinement part specific to Calibration
        Sets up the initial guess when starting pyFAI-calib
        """
        # First attempt
        defaults = self.initgeoRef()
        self.geoRef = pyFAI.geometryRefinement.GeometryRefinement(self.data,
                                         detector=self.detector,
                                         wavelength=self.wavelength,
                                         calibrant=self.calibrant,
                                         **defaults)
        self.geoRef.refine2(1000000, fix=self.fixed)
        scor = self.geoRef.chi2()
        pars = [getattr(self.geoRef, p) for p in self.PARAMETERS]

        scores = [(scor, pars), ]

        # Second attempt
        defaults = self.initgeoRef()
        self.geoRef = pyFAI.geometryRefinement.GeometryRefinement(self.data,
                                         detector=self.detector,
                                         wavelength=self.wavelength,
                                         calibrant=self.calibrant,
                                         **defaults)
        self.geoRef.guess_poni()
        self.geoRef.refine2(1000000, fix=self.fixed)
        scor = self.geoRef.chi2()
        pars = [getattr(self.geoRef, p) for p in self.PARAMETERS]

        scores.append((scor, pars))

        # Choose the best scoring method: At this point we might also ask
        # a user to just type the numbers in?
        scores.sort()
        scor, pars = scores[0]
        for parval, parname in zip(pars, self.PARAMETERS):
            setattr(self.geoRef, parname, parval)

        # Now continue as before
        self.refine2()

    def refine2(self):
        # Modified refine from the pyFAI.calibration.AbstractCalibration class
        """
        Contains the common geometry refinement part
        """
        previous = sys.maxint
        finished = False
        while not finished:
            count = 0
            if "wavelength" in self.fixed:
                while (previous > self.geoRef.chi2()) and (count < self.max_iter):
                    if (count == 0):
                        previous = sys.maxsize
                    else:
                        previous = self.geoRef.chi2()
                    self.geoRef.refine2(1000000, fix=self.fixed)
                    count += 1
            else:
                while previous > self.geoRef.chi2_wavelength() and (count < self.max_iter):
                    if (count == 0):
                        previous = sys.maxsize
                    else:
                        previous = self.geoRef.chi2()
                    self.geoRef.refine2_wavelength(1000000, fix=self.fixed)
                    count += 1
                self.points.setWavelength_change2th(self.geoRef.wavelength)
            # self.geoRef.save(self.basename + ".poni")
            self.geoRef.del_ttha()
            self.geoRef.del_dssa()
            self.geoRef.del_chia()
            tth = self.geoRef.twoThetaArray(self.img.shape)
            dsa = self.geoRef.solidAngleArray(self.img.shape)
#            self.geoRef.chiArray(self.peakPicker.shape)
#            self.geoRef.cornerArray(self.peakPicker.shape)

            if self.interactive:
                finished = self.prompt()
            else:
                finished = True
            if not finished:
                previous = sys.maxsize