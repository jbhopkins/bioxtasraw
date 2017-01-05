'''
Created on Jul 5, 2010

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

import sys
sys.path.append("..") 

import unittest
import SASM, SASExceptions
import numpy as np
import os, copy
import numpy.testing as npt 

    
class newTestSASM(SASM.SASM):
    
    def __init__(self, i_scale, q_scale, err_scale, filename):
        
        i = np.array([0.0,2.0,3.0,4.0,5.0,6.0]) * i_scale 
        q = np.array([0.0,1.0,2.0,3.0,4.0,5.0]) * q_scale
        err = np.array([0.0,1.0,2.0,3.0,4.0,5.0]) * err_scale
        
        parameters = {'filename': filename}
        
        SASM.SASM.__init__(self, i, q, err, parameters)

class TestSASM(unittest.TestCase):
    
    def setUp(self):
        self.i = np.array([0.0,1.0,3.0,2.0,0.0,6.0])
        self.q = np.array([0.0,1.0,2.0,3.0,4.0,5.0])
        self.err = np.array([0.0,1.5,1.5,2.0,1.5,2.0])
        
        self.parameters = {}
        
        self.sasm = SASM.SASM(self.i, self.q, self.err, self.parameters)
        
    def tearDown(self):
        del(self.sasm)
    
    def test_SASM(self):
        ''' Tests if input is assigned to local variables correctly '''
        
        self.assertTrue(np.all(self.sasm.i == self.i))
        
        self.assertTrue(np.all(self.sasm.q == self.q))
        self.assertTrue(np.all(self.sasm.err == self.err))
        
        self.assertTrue(np.all(self.sasm.i == self.i))
        self.assertTrue(np.all(self.sasm.q == self.q))
        self.assertTrue(np.all(self.sasm.err == self.err))

        self.assertEqual(self.sasm._scale_factor, 1)
                
    def test_scaling(self):
        ''' Tests proper scaling '''
        
        self.sasm.scale(5)
        answer = np.array([0,5,15,10,0,30])
        self.assertTrue(np.all(self.sasm.i == answer))
        self.assertEqual(self.sasm._scale_factor, 5)
        
        errScaled = self.err * 5
        self.assertTrue(np.all(self.sasm.err == errScaled))
        
    def test_normalize(self):
        ''' test normalization function '''
        
        normvalue = 5.0
        i_norm = self.i / normvalue
        err_norm = self.err / normvalue
        
        self.sasm.normalize(normvalue)  
        self.assertTrue(np.all(self.sasm.i == i_norm))
        self.assertTrue(np.all(self.sasm.err == err_norm))
        self.assertFalse(np.all(self.sasm._err_raw == err_norm))
        self.assertFalse(np.all(self.sasm._i_raw == i_norm))        
    
    def test_offset(self):
        ''' Test offsetting '''
        
        self.sasm.offset(5)
        offsetval = self.i + 5
        self.assert_(np.all(self.sasm.i == offsetval))
        self.failUnless((np.all(self.sasm._i_raw == self.i)))
        
        
    def test_setQrange(self):
        qrange = (0, 5)
        self.sasm.setQrange(qrange)
        self.failUnless(self.sasm.getQrange(), qrange)
        self.assertRaises(SASExceptions.InvalidQrange, self.sasm.setQrange, (0, 50))
        self.assertRaises(SASExceptions.InvalidQrange, self.sasm.setQrange, (-4, 2))
        
    def test_scaleAndOffset(self):
        
        offsca = (self.i + 10) * 5 
        offsca_err = self.err * 5
        
        self.sasm.offset(10)
        self.sasm.scale(5)
        
        self.assert_(np.all(self.sasm.i == offsca))
        self.assert_(np.all(self.sasm.err == offsca_err))
        
        self.sasm.offset(10+10)
        
        offsca += (10 * 5)
        
        self.assert_(np.all(self.sasm.i == offsca))
        
    def test_getParameters(self):
        self.parameters['test'] = 5
        val = self.sasm.getParameter('test')
        self.assertEqual(val, 5)
        self.assertEqual(self.sasm.getParameter('hello'), None)
        
    def test_scaleQ(self):
        qscaled = self.q * 5.0
        self.sasm.scaleQ(5.0)
        self.assert_(np.all(self.sasm.q == qscaled))
        self.assertEqual(self.sasm._q_scale_factor, 5.0) 
        
    def test_reset(self):   
        self.sasm.scale(5)
        self.sasm.offset(10)
        self.sasm.normalize(20)
        self.sasm.reset()
        
        self.assert_(np.all(self.sasm.i == self.i))
        self.assert_(np.all(self.sasm.err == self.err))
        self.assert_(np.all(self.sasm.q == self.q))
        self.assert_(np.all(self.sasm._q_binned == self.q))
        self.assert_(np.all(self.sasm._i_binned == self.i))
        self.assert_(np.all(self.sasm._err_binned == self.err))
            
    def test_getSetBinning(self):
        #self.i = np.array([0.0,1.0,3.0,2.0,0.0,6.0])
        #self.q = np.array([0.0,1.0,2.0,3.0,4.0,5.0])
        #self.err = np.array([0.0,1.5,2.5,2.0,1.5,2.0])
        
        self.sasm.setBinning(2, start_idx = 0, end_idx = -1)
        
        I_bin = np.array([0.5, 2.5, 3.0])
        q_bin = np.array([0.5, 2.5, 4.5])
        err_bin = np.array([1.5/np.sqrt(2), 2.5/np.sqrt(2), 2.5/np.sqrt(2)])
        
        self.failUnless(np.all(self.sasm.i == I_bin), str(self.sasm.i) + '!=' + str(I_bin))
        self.failUnless(np.all(self.sasm.q == q_bin), str(self.sasm.q) + '!=' + str(q_bin))
        self.failUnless(np.all(self.sasm.err == err_bin), str(self.sasm.err) + '!=' + str(err_bin))
        
        self.failUnlessEqual(self.sasm.getBinning(), 2)
        
    def test_setBinning2(self):
        ''' tests binning from differnt start_index value '''
        
        self.sasm.setBinning(2, start_idx = 3, end_idx = -1)

        I_bin = np.array([0.0, 1.0, 3.0, 1.0, 6.0])
        q_bin = np.array([0.0, 1.0, 2.0, 3.5, 5.0])
        
        self.failUnless(np.all(self.sasm.i == I_bin), str(self.sasm.i) + '!=' + str(I_bin))
        self.failUnless(np.all(self.sasm.q == q_bin), str(self.sasm.q) + '!=' + str(q_bin))
        
    def test_setBinning3(self):
        ''' tests binning from differnt start_index and end_idx value '''
        
        self.sasm.setBinning(2, start_idx = 2, end_idx = 4)
    
        I_bin = np.array([0.0, 1.0, 2.5, 0.0, 6.0])
        q_bin = np.array([0.0, 1.0, 2.5, 4.0, 5.0])
        
        self.failUnless(np.all(self.sasm.i == I_bin), str(self.sasm.i) + '!=' + str(I_bin))
        self.failUnless(np.all(self.sasm.q == q_bin), str(self.sasm.q) + '!=' + str(q_bin))
        
    def test_removeZingers(self):

        self.sasm._i_binned = np.array([1.0, 2.0, 1.0, 2.0, 10.0, 2.0, 1.0, 2.0, 1.0, 2.0])
        self.sasm.removeZingers(0, 2, 4.0)
        self.failUnless(np.all(self.sasm.i == np.array([1, 2, 1, 2, 1.5, 2, 1, 2, 1, 2])), str(self.sasm.i) + ' != ' + str([1,2,1,2,1.5,2,1,2,1,2]))
        
        #Pure integers (maybe for counting detectors, will only reveal integer values)
        #self.sasm.i = np.array([1,2,1,2,10,2,1,2,1,2])
        #self.sasm.removeZingers(0,2,4.0)
        #self.failUnless(np.all(self.sasm.i == np.array([1,2,1,2,1,2,1,2,1,2])), str(self.sasm.i) + ' != ' + str([1,2,1,2,1,2,1,2,1,2]))
    
    def test_calibrateQ(self):
         
        sd_distance = 1000 #mm
        delta_q_length = 70e-3 #um
        wavelength = 1.2 #angstroem
        
        q_calib = np.array([ 0.0, 0.00036, 0.00073, 0.00109, 0.00146, 0.0018])
        
        self.sasm.calibrateQ(sd_distance, delta_q_length, wavelength)
        
        self.failUnlessAlmostEqual(np.sum(self.sasm.q-q_calib), 0, 3, str(self.sasm.q) + ' != ' + str(q_calib))


class Test_subtract(unittest.TestCase):
    
    def setUp(self):
        self.sasm1 = newTestSASM(1,1,1, 'foo.bar')
        self.sasm2 = newTestSASM(1.4,5,1.5, 'foo.bar2')
        
        self.subSASM = SASM.subtract(self.sasm1, self.sasm2)
        
    def test_subtract_intensityCorrectlySubtracted(self):
        self.i_sub = self.sasm1.i - self.sasm2.i
        npt.assert_equal(self.subSASM.i, self.i_sub)
    
    def test_errorCorrectlyPropagated(self):
        self.err_sub = np.sqrt( np.power(self.sasm1.err,2) + np.power(self.sasm2.err,2))
        npt.assert_equal(self.subSASM.err, self.err_sub)
        
        
class Test_average(unittest.TestCase):

    def setUp(self):
        self.sasm1 = newTestSASM(1, 1, 1, 'foo.bar')
        self.sasm2 = newTestSASM(1.4, 5, 1.5, 'foo.bar2')
        self.sasm3 = newTestSASM(2.5, 10, 2.5, 'foo.bar3')
        
        self.avgsasm = SASM.average([self.sasm1, self.sasm2, self.sasm3])
        
    def test_IntensityCorrectlyAveraged(self):
        iavg = (self.sasm1.i + self.sasm2.i + self.sasm3.i) / 3
        npt.assert_equal(self.avgsasm.i, iavg)
        
    def test_ErrorCorrectlyPropagated(self):
        erravg = np.sqrt( np.power(self.sasm1.err,2) + np.power(self.sasm2.err,2) + np.power(self.sasm3.err,2) ) / np.sqrt(3)
        npt.assert_equal(self.avgsasm.err, erravg)
        
    def test_ParameterContainsAllFilenamesOfAveragedFiles(self):
        avgfiles = ['foo.bar', 'foo.bar2', 'foo.bar3']
        filelist = self.avgsasm.getParameter('avg_filelist')
        npt.assert_equal(filelist, avgfiles)
        
    

class Test_testAddFilenamePrefix(unittest.TestCase):
    
    def setUp(self):
        self.sasm1 = newTestSASM(1,1,1, 'foo.bar')
                
    def test_addPrefixCorrectly(self):
        SASM.addFilenamePrefix(self.sasm1, 'TEST_')
        self.assertEqual(self.sasm1.getParameter('filename'), 'TEST_foo.bar')
    
    
class Test_addFilenameSuffix(unittest.TestCase):
        
    def setUp(self):
        self.sasm1 = newTestSASM(1,1,1, 'foo.bar')
    
    def test_addSuffixCorrectly(self):
        SASM.addFilenameSuffix(self.sasm1, '_TEST')
        self.assertEqual(self.sasm1.getParameter('filename'), 'foo_TEST.bar')
    
        
class Test_removeZingersAndAverage(unittest.TestCase):  
    
    def tearDown(self):
        unittest.TestCase.tearDown(self)
        
    def testMet1(self):
        pass
    
class Test_determineOutlierMaxMin(unittest.TestCase):
    
    def setUp(self):
        unittest.TestCase.setUp(self)
    
    def tearDown(self):
        unittest.TestCase.tearDown(self)
        
    def testMet1(self):
        pass


#class Test_superimpose(unittest.TestCase):  
#    
#    def setUp(self):
#        self.i = np.array([0.0,1.0,3.0,2.0,0.0,6.0])
#        self.q = np.array([0.0,1.0,2.0,3.0,4.0,5.0])
#        self.err = np.array([0.0,1.5,1.5,2.0,1.5,2.0])
#        
#        self.parameters = {}
#        
#        self.sasm = SASM.SASM(self.i, self.q, self.err, self.parameters)
#    
#    def tearDown(self):
#        pass
#        
#    def test_superimpose_offset(self):
#        offset_sasm = copy.copy(self.sasm)
#        offset_sasm.i = offset_sasm.i + 5.0
#        
#        SASM.superimpose(self.sasm, [offset_sasm])
#
#        self.assertEqual(offset_sasm.getOffset(), 5.0)
#
#    def test_superimpose_scale(self):
#        offset_sasm = copy.copy(self.sasm)
#        offset_sasm.i = offset_sasm.i * 1.5
#        
#        SASM.superimpose(self.sasm, [offset_sasm])
#
#        self.assertEqual(offset_sasm.getScale(), 1.5)        
#
#    def test_superimpose_scale_and_offset(self):
#        offset_sasm = copy.copy(self.sasm)
#        offset_sasm.i = offset_sasm.i * 1.5 + 3.0
#        
#        SASM.superimpose(self.sasm, [offset_sasm])
#
#        self.assertEqual(offset_sasm.getScale(), 1.5)   
#        self.assertEqual(offset_sasm.getOffset(), 3.0)


class Test_merge(unittest.TestCase):  
    
    def setUp(self):
        self.i = np.array([0.0,1.0,3.0,2.0,0.0,6.0])
        self.q = np.array([0.0,1.0,2.0,3.0,4.0,5.0])
        self.err = np.array([0.0,1.5,1.5,2.0,1.5,2.0])
        
        
        self.i2 = np.array([1.0,1.0,3.0,2.0,0.0,6.0, 3.0, 5.0, 2.0, 1.0])
        self.q2 = np.array([0.0,1.0,2.0,3.0,3.5,5.0, 6.2, 7.3, 8.4, 9.5])
        self.err2 = np.array([0.0,1.5,1.5,2.0,1.5,2.0,1.5,2.0,1.5,2.0])
        
        self.parameters = {}
        self.parameters2 = {}
        
        self.sasm = SASM.SASM(self.i, self.q, self.err, self.parameters)
        self.sasm2 = SASM.SASM(self.i2, self.q2, self.err2, self.parameters2)
        
        self.sasm2.setQrange((4,10))
        
    def tearDown(self):
        pass
        
    def test_merge_sort(self):
        
        SASM.merge(self.sasm, [self.sasm2])

        




def main():
    unittest.main()
    
    
if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    main()
    
    