'''
Created on Jul 14, 2010

@author: Soren S. Nielsen
'''
import unittest, sys
sys.path.append("..") 
import SASFileIO
import RAWSettings
import os
import numpy as np 
from numpy.testing import assert_almost_equal

def Config_GetTestDataPath(filename):
    ''' returns the testfile with full path '''
    
    path = os.path.join(os.getcwd(), 'TestData', filename)
    return path


#--- UNIT TESTS 

class Test_loadTiffImage(unittest.TestCase):
    
    def setUp(self):        
        self.filename = Config_GetTestDataPath('FLICAM_AgBeh_001_c.tif')
        self.img, self.img_hdr = SASFileIO.loadTiffImage(self.filename)

    def test_ImageHasCorrectShape(self):
        self.failUnlessEqual(self.img.shape, (1024,1024))    # a bit weak
        
    def test_headerIsEmpty_ShouldBeZeroLength(self):
        self.failUnlessEqual(len(self.img_hdr), 0)
        
        
class Test_loadQuantumImage(unittest.TestCase):
    
    def setUp(self):        
        self.filename = Config_GetTestDataPath('AgBe_Quantum.img')
        self.img, self.img_hdr = SASFileIO.loadQuantumImage(self.filename)

    def test_ImageHasCorrectShape(self):
        self.failUnlessEqual(self.img.shape, (1152,1152))
        
    def test_headerIsNotEmpty_ShouldBeLargerThanZero(self):
        self.failIfEqual(len(self.img_hdr), 0)
        
class Test_loadMarCCD165Image(unittest.TestCase):
    
    def setUp(self):
        self.filename = Config_GetTestDataPath('MaxlabMarCCD165.tif')
        self.img, self.img_hdr = SASFileIO.loadMarCCD165Image(self.filename)
    
    def tearDown(self):
        unittest.TestCase.tearDown(self)
        
    def test_headerNotEmpty_ShouldNotBeLengthZero(self):
        self.failIfEqual(len(self.img_hdr), 0)
        
    def test_imageIsCorrectSize(self):
        self.failUnlessEqual(self.img.shape, (2048,2048))      
        
        
class Test_parseCHESSF2QuantumFileHeader(unittest.TestCase):
    
    def setUp(self):        
        self.filename = Config_GetTestDataPath('AgBe_Quantum.img')
        self.hdr = SASFileIO.parseQuantumFileHeader(self.filename)

    def test_parserReadCorrectWavelenght(self):
        self.failUnlessEqual(float(self.hdr['WAVELENGTH']), 1.60830)
        
    def test_parserReadCorrectPixelsize(self):
        self.failUnlessEqual(float(self.hdr['PIXEL_SIZE']), 0.0707)
        
        
class Test_parseCHESSF2CTSfile(unittest.TestCase):
    
    def setUp(self):      
        self.filename = Config_GetTestDataPath('AgBe_Quantum.img') 
        self.counters = SASFileIO.parseCHESSF2CTSfile(self.filename)

    def test_countersIsNotNone(self):
        self.failIf(self.counters == None)
        
    def test_parserReadCorrectBgCount(self):
        self.failUnlessEqual(self.counters['bgcount'], 0)
        
    def test_parserReadCorretExposureTime(self):
        self.failUnlessEqual(self.counters['exposureTime'], 0)
        
class Test_parseCHESSF2CTSfile(unittest.TestCase):
    
    def setUp(self):      
        self.filename = Config_GetTestDataPath('Pilatus100K_scan030_033.tiff') 
        self.counters = SASFileIO.parsePilatusHeader(self.filename)

    def test_countersIsNotNone(self):
        self.failIf(self.counters == None)
        
    def test_parserReadCorrectBgCount(self):
        self.failUnlessEqual(self.counters['Exposure_date'], '2011:03:15 04:11:32')
            
    def test_parserReadCorretExposureTime(self):
        self.failUnlessEqual(self.counters['Exposure_time'], 60.0)
        

class Test_loadFile_loadRadAsciiFile(unittest.TestCase):
    
    def setUp(self):
        self.raw_settings = RAWSettings.RawGuiSettings()
        self.filename = Config_GetTestDataPath('Lys12_1_001_plot.rad') 
        self.sasm, self.img = SASFileIO.loadFile(self.filename, self.raw_settings)
    
    def tearDown(self):
        del(self.raw_settings)
        
    def test_imageIsNone_ShouldBeNone(self):
        self.failUnlessEqual(self.img, None)
    
    def test_loadedAllPoints(self):
        self.failUnlessEqual(len(self.sasm.i), 447)
        
    def test_filenameInParametersIsCorrect(self):
        self.failUnlessEqual(self.sasm.getParameter('filename'), os.path.split(self.filename)[1])
        
      
class Test_loadFile_loadQuantumImageFile(unittest.TestCase):
    
    def setUp(self):
        self.raw_settings = RAWSettings.RawGuiSettings()
        self.filename = Config_GetTestDataPath('AgBe_Quantum.img') 
        self.raw_settings.set('ImageFormat', 'Quantum')
        self.sasm, self.img = SASFileIO.loadFile(self.filename, self.raw_settings)
            
    def test_imageNotNone(self):
        self.failIfEqual(self.img, None)
        
    def test_imageIsCorrectSize(self):
        self.failUnlessEqual(self.img.shape, (1152,1152))
    
    def test_sasmContainsCorrectNumberOfPoints(self):        
        self.failUnlessEqual(len(self.sasm.i), 450)
        
    def test_filenameInParametersIsCorrect(self):
        self.failUnlessEqual(self.sasm.getParameter('filename'), os.path.split(self.filename)[1])
        

class Test_parseCHESSG1CountFile(unittest.TestCase):
        
    def setUp(self):
        self.filename = Config_GetTestDataPath('FLICAM_AgBeh_001_c.tif') 
        self.counters = SASFileIO.parseCHESSG1CountFile(self.filename)
 
    def test_countersIsNotNone(self):
        self.failIf(self.counters == None)
        
    def test_parserReadCorrectExposureTime(self):
        self.failUnlessEqual(float(self.counters['Seconds']), 1.0)
        
    def test_parserReadCorrectGdoor(self):
        self.failUnlessEqual(int(self.counters['gdoor']), 1668)
        
    def test_partserReadCorrectS7(self):
        self.failUnlessEqual(int(self.counters['s7']), 0)

    
class Test_loadMaxlabI711Header(unittest.TestCase):
    
    def setUp(self):
        self.filename = Config_GetTestDataPath('MaxlabMarCCD165.tif')
        self.hdr = SASFileIO.loadHeader(self.filename, 'I711, MaxLab')
        
#    def test_fileHdrNotEmpty_shouldBeLargerThanZero(self):
#        file_hdr = self.hdr['counters']
#        self.failIfEqual(len(file_hdr), 0)
                

class Test_loadPrimusDatFile(unittest.TestCase):
    
    def Config_createSasmFromPrimusFile(self, filename):
        
        self.filename = Config_GetTestDataPath(filename)
        self.sasm = SASFileIO.loadPrimusDatFile(self.filename)
    
    def setUp(self):
        self.Config_createSasmFromPrimusFile('lyzexp.dat')
        
    def test_sasmHasCorrectFilename(self):
        sasm_filename = self.sasm.getParameter('filename')
        correct_filename = os.path.split(self.filename)[1]
            
        self.failUnlessEqual(sasm_filename, correct_filename)
        
    def test_firstItensityPointLoadedCorrectly(self):
        self.failUnlessAlmostEqual(self.sasm.i[0], 5.904029, 6) 
        
    def test_lastIntensityPointLoadedCorrectly(self):
        self.failUnlessAlmostEqual(self.sasm.i[-1], 4.550579e-02, 6)
        
    def test_firstQPointLoadedCorrectly(self):
        self.failUnlessAlmostEqual(self.sasm.q[0], 4.138455e-02, 6)
        
    def test_lastQPointLoadedCorrectly(self):
        self.failUnlessAlmostEqual(self.sasm.q[-1], 4.983631e-01, 6)
        
    def test_loadedCorrectNumberOfPoints(self):
        points = len(self.sasm.i)
        self.failUnlessEqual(points, 197)

    def test_headerLoadedCorrectly(self):
        hdr = self.sasm.getParameter('fileHeader')['comment']
        
        correct_header = '#Lysozyme, high angles (>.22) 46 mg/ml, small angles (<.22) 15 mg/ml\n' 
        self.failUnlessEqual(hdr, correct_header)
        
class Test_loadRadFile(unittest.TestCase):
    
    def Config_createSasmFromRadFile(self, filename):
        self.filename = Config_GetTestDataPath(filename)
        self.sasm = SASFileIO.loadRadFile(self.filename)
        
    def setUp(self):
        self.Config_createSasmFromRadFile('Lys12_1_001_plot.rad')
        
    def test_sasmHasCorrectFilename(self):
        sasm_filename = self.sasm.getParameter('filename')
        correct_filename = os.path.split(self.filename)[1]
            
        self.failUnlessEqual(sasm_filename, correct_filename)
        
    def test_loadedFirstPointCorrectly(self):
        i = 2.30312000e+01
        q = 1.00000000e-03
        err = 8.48400000e-01
        
        act_i = self.sasm.i[0]
        act_q = self.sasm.q[0]
        act_err = self.sasm.err[0]
        
        desired = np.array([q,i,err])
        actual = np.array([act_q, act_i, act_err])
        
        assert_almost_equal(actual, desired, 6)
   
    def test_loadedLastPointCorrectly(self):
        i = 3.96690000
        q = 4.47000000e-01
        err = 2.43020000e-02
       
        act_i, act_q, act_err = self.sasm.i[-1], self.sasm.q[-1], self.sasm.err[-1]

        desired = np.array([q,i,err])
        actual = np.array([act_q, act_i, act_err])
        
        assert_almost_equal(actual, desired, 6)
            
    def test_loadedCorrectNumberOfPoints(self):
        points = len(self.sasm.i)
        self.failUnlessEqual(points, 447)
        
    def test_headerLoadedCorrectly(self):
        hdr = self.sasm.getParameter('fileHeader')['filename']
        
        correct_header = '/home/specuser/workspace/Lys12_1_001_plot.rad'
        self.failUnlessEqual(hdr, correct_header)
    
    
    
#### Possible Integration test?:    

class Test_writeRadFile_LoadAndWriteRadFile(unittest.TestCase):
    
    def Config_loadARadFile(self, filename):
        self.filename = Config_GetTestDataPath(filename)
        self.sasm = SASFileIO.loadNewRadFile(self.filename)

    def setUp(self):
        self.Config_loadARadFile('lyzexp.dat')
    
        self.save_filename = Config_GetTestDataPath('lyzexp.rad')
        
        SASFileIO.writeRadFile(self.sasm, self.save_filename)
        
        self.Config_loadARadFile(self.save_filename)
        
        if os.path.exists(self.save_filename):
            os.remove(self.save_filename)

    def test_loadedCorrectNumberOfPoints(self):
        points = len(self.sasm.i)
        self.failUnlessEqual(points, 196)
        
    def test_correctFilename(self):
        filename = self.sasm.getParameter('filename')
        correct_filename = os.path.split(self.save_filename)[1]
        self.failUnlessEqual(filename, correct_filename)
    
   
class Test_writeRadFile_LoadAndWriteImageFile(unittest.TestCase):
    
    def Config_loadARadFile(self, filename):
        self.filename = Config_GetTestDataPath(filename)
        self.sasm = SASFileIO.loadRadFile(self.filename)
    
    def Config_loadAFlicamFile(self, filename):
        self.filename = Config_GetTestDataPath(filename)
        self.sasm, self.img = SASFileIO.loadFile(self.filename, self.raw_settings)
    
    def setUp(self):
        self.save_filename = Config_GetTestDataPath('TestAgBeh_001_c.rad')
        self.raw_settings = RAWSettings.RawGuiSettings()
        self.raw_settings.set('ImageFormat', 'FLICAM')
        
        if os.path.exists(self.save_filename):
            os.remove(self.save_filename)
    
    def test_correctFilename(self):
        self.Config_loadAFlicamFile('FLICAM_AgBeh_001_c.tif')
        
        SASFileIO.writeRadFile(self.sasm, self.save_filename)
        
        self.Config_loadARadFile(self.save_filename)
        
        filename = self.sasm.getParameter('filename')
        correct_filename = os.path.split(self.save_filename)[1]
        
        self.failUnlessEqual(filename, correct_filename)
        
        
#--- INTEGRATION TESTS
        
    
#class  Test_writeRadFile_TwoTimesLoadWriteImage(unittest.TestCase):
      
#        self.Config_loadAFlicamFile('AgBeh_001_c.tif')
#        SASFileIO.writeRadFile(self.sasm, self.save_filename)
#        self.Config_loadARadFile(self.save_filename)
#        SASFileIO.writeRadFile(self.sasm, self.save_filename)
#        self.Config_loadARadFile(self.save_filename)
#        
#        print self.sasm.getAllParameters()  
#    
        
#class Test_load2ColFile(unittest.TestCase):
#    
#    def Config_createSasmFromRadFile(self, filename):
#        self.filename = Config_GetTestDataPath(filename)
#        self.sasm = SASFileIO.load2ColFile(self.filename)
#        
#    def setUp(self):
#        self.Config_createSasmFromRadFile('Lys12_1_001_plot.rad')
#        
    
if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()