'''
Created on Jul 11, 2010

@author: Soren S. Nielsen

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
import unittest, sys
sys.path.append("..") 
import SASCalib
import SASM
import numpy as np
from numpy.testing import assert_almost_equal


class newTestSASM(SASM.SASM):
    
    def __init__(self, i_scale, q_scale, err_scale, filename):
        
        i = np.array([0.0,2.0,3.0,4.0,5.0,6.0]) * i_scale 
        q = np.array([0.0,1.0,2.0,3.0,4.0,5.0]) * q_scale
        err = np.array([0.0,1.0,2.0,3.0,4.0,5.0]) * err_scale
        
        parameters = {'filename': filename}
        
        SASM.SASM.__init__(self, i, q, err, parameters)
        
class TestSASCalib(unittest.TestCase):


    def setUp(self):
        self.sasm = newTestSASM(1,1,1,'foo.bar')
        
        self.sd_distance = 1000 #mm
        self.pixel_size = 70e-3 #mm
        self.q_length_pixels = 1.2 #A

    def tearDown(self):
        del(self.sasm)

    def test_calcAbsScaleConstWater(self):    
        absscale = SASCalib.calcAbsScaleConstWater(self.sasm, 2, 4)
        self.failUnlessAlmostEqual(absscale, 0.004628, 5, str(absscale) + ' != ' + str(0.004628))
               
    def test_calcTheta(self):
         
        self.q_length_pixels = 500
        answer = 0.01749
         
        angle = SASCalib.calcTheta(self.sd_distance, self.pixel_size, self.q_length_pixels)
        self.failUnlessAlmostEqual(angle, answer, 5, str(angle) + ' != ' + str(answer))

    def test_IncidentAngleCorrection(self):
        
        iac = SASCalib.calcSolidAngleCorrection(self.sasm, self.sd_distance, self.pixel_size)
                
        answer = np.array([ 1.0, 0.99999999, 0.99999997, 0.99999993, 0.99999988, 0.99999982])
        assert_almost_equal(iac, answer, 8)
    
    def test_calcDistanceFromAgBeh(self):
        
        first_ring_dist = 380
        pixel_size = 70e-3
        wavelength = 1.1946
        
        sd = SASCalib.calcDistanceFromAgBeh(first_ring_dist, pixel_size, wavelength)
        self.failUnlessAlmostEqual(sd, 1299.7, 1)
        

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()