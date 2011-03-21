'''
Created on Jul 13, 2010

@author: specuser
'''
import unittest, os, sys, Image, copy, cPickle
import matplotlib.pyplot as plt
import numpy as np
sys.path.append("..") 

import SASImage

def loadMaskFile(fullpath_filename, img_dim):        

            filenamepath, extension = os.path.splitext(fullpath_filename)
        
            if extension == '.msk':
                file_obj = open(fullpath_filename, 'r')
                masks = cPickle.load(file_obj)
                file_obj.close()
         
                i=0        
                for each in masks:
                    each.maskID = i
                    i = i + 1
                
                mask = SASImage.createMaskMatrix(img_dim, masks)
                
            return mask

def loadQuantumImage(filename):
    ''' Load image from quantum detectors (512 byte header) 
    and also obtains the image header '''
    
    f = open(filename, 'rb')
    f.seek(512)                         # Jump over header

    Img = np.fromfile(f, dtype=np.uint16)
    f.close()
    
    xydim = int(np.sqrt(np.shape(Img))[0])  #assuming square image

    Img = Img.reshape((xydim,xydim))
    
    return Img

def getBeamIntensity(img, mask, noisemask):

        #roi = mask * img
        noise = noisemask * img
        
        roi = img[(1152-67):(1152-37), 690:785]
        print sum(sum(roi))
        print roi.shape

        roi_points = roi[np.where(roi!=0)]
        noise_points = noise[np.where(noise!=0)]
        
        noise_average = np.average(noise_points)
        
        roi_no_noise = roi_points - noise_average
        
        beam_int = sum(roi_no_noise)
        
#        plt.figure()
#        plt.imshow(roi)
#        plt.figure()
#        plt.plot(roi_no_noise)
        
        return beam_int, roi

class TestBeamstopNormalize(unittest.TestCase):
    
    def setUp(self):
        cwd = os.getcwd()
        self.bsmask_file = os.path.join(cwd, 'TestData', 'TranspBS.msk')
        self.noisemask_file = os.path.join(cwd, 'TestData', 'NoiseBS.msk')
        #self.testimg_path = os.path.join(cwd, 'TestData', 'BSA_1_070.img')
        #self.testimg_path2 = os.path.join(cwd, 'TestData', 'BSA_1_078.img')
        
        self.testimg_path = os.path.join(cwd, 'TestData', 'BSA_1_071.img')
        self.testimg_path2 = os.path.join(cwd, 'TestData', 'BSA_1_073.img')
        self.plot = False
        
        
    def tearDown(self):
        plt.show()
        
    def testBeamstopNoiseRemoval(self):
        self.img = loadQuantumImage(self.testimg_path)
        self.img2 = loadQuantumImage(self.testimg_path2)
        self.mask = loadMaskFile(self.bsmask_file, self.img.shape)
        self.noisemask = loadMaskFile(self.noisemask_file, self.img.shape)
        
        imgplt = plt.imshow(self.img)
        imgplt.set_clim(0,500)
        plt.figure()
        maskplt = plt.imshow(self.mask)
        imgplt.set_clim(0,500)
        plt.figure()
        noisemask = plt.imshow(self.noisemask)
        
        inten, roi = getBeamIntensity(self.img, self.mask, self.noisemask)  
        inten2, roi2 = getBeamIntensity(self.img2, self.mask, self.noisemask)
        
        #plt.plot(self.img[660:800, ])
        
        if self.plot:
            plt.figure()
            plt.plot(roi[17,:]-40)
            plt.plot(roi2[17,:]-40, 'r')
            plt.plot((roi2[17,:]-40)*4, 'g')
        
        plt.figure()
        plt.imshow(roi)    
        
    def testBeamstopIntegration(self):
        pass
    

class TestZingerRemoval(unittest.TestCase):
    
    def setUp(self):
        cwd = os.getcwd()
        #self.testimg_path = os.path.join(cwd, 'TestData', 'AgBe_Quantum.img')
        #self.x_c, self.y_c = 623, 1073
        self.testimg_path = os.path.join(cwd, 'TestData', 'BSA_1_078.img')
        self.x_c, self.y_c = 512, 640
        
        #self.testimg_path = os.path.join(cwd, 'TestData', 'GACdc100_0_003.img')
        #self.x_c, self.y_c = 738, 1128
        
        
        mask_file = os.path.join(cwd, 'TestData', 'mask3.msk')
        
        self.img = loadQuantumImage(self.testimg_path)
        #self.mask = loadMaskFile(mask_file, self.img.shape)
        self.mask = None
        
    def tearDown(self):
        plt.show()

    def testRemoveSingleZinger(self):
         
        cutoff = 0 #400
        line = 47#110#765#1010#1010#765#300#634
        
        #110 Big zinger at the end (outside normal window reach)
        
        iq, q, errorbars, qmatrix = SASImage.radialAverage(self.img, self.x_c, self.y_c, self.mask)
        qmatrix = np.flipud(qmatrix)
        qmatrix = np.flipud(np.rot90(qmatrix,3))
        
        y = qmatrix[np.where(qmatrix[:,line]!=0),line][0]
        x = range(0,len(y))
        
        y2 = copy.copy(y)
        y2 = y2[cutoff:]
        
        #intensity_array, start_idx = 0, window_length = 10, sensitivity = 4
        y3 = SASImage.removeZingers2(y2, 0, 30, 4)
        
        plt.plot(x[cutoff:], y[cutoff:], color = 'blue')
        plt.plot(x[cutoff:], y3, color = 'red')
        
        print y[-15:]
    
    def testRemoveAllZingers(self):
        iq, q, errorbars, qmatrix = SASImage.radialAverage(self.img, self.x_c, self.y_c, self.mask)
        
        qmatrix = np.flipud(qmatrix)
        qmatrix = np.flipud(np.rot90(qmatrix,3))
        
        I = np.zeros(qmatrix.shape[1])
        I2 = np.zeros(qmatrix.shape[1])
        
        for i in range(0, qmatrix.shape[1]):
            y = qmatrix[np.where(qmatrix[:,i]!=0),i][0]
            y2 = SASImage.removeZingers2(copy.copy(y), 0, 30, 4)
            I[i] = np.mean(y2)
            I2[i] = np.mean(y)
        
        plt.figure()
        plt.plot(I, 'blue')
        plt.plot(I2, 'red')
#
#class TestRadialAverage(unittest.TestCase):
#
#    def setUp(self):
#        cwd = os.getcwd()
#        self.quantum_path = os.path.join(cwd, 'TestData', 'AgBe_Quantum.img')
#        self.testimg_path = os.path.join(cwd, 'TestData', 'testimg2.png')
#        
#        self.plot = True
#
#    def tearDown(self):
#        plt.show()
#
#    def testRadialAverage_Quantum(self):
#        self.img = loadQuantumImage(self.quantum_path)
#        self.x_c, self.y_c = 623, 1073
#        
#        iq, q, errorbars, qmatrix = SASImage.radialAverage(self.img, self.x_c, self.y_c)
#        
#        
#        imgplt = plt.imshow(qmatrix)
#        imgplt.set_clim(0,500)
#        
#        plt.figure()
#        
#        qmatrix = np.flipud(qmatrix)
#        qmatrix = np.flipud(np.rot90(qmatrix,3))
#        
#        if self.plot:
#            imgplt = plt.imshow(self.img)
#            imgplt.set_clim(0,500)
#            plt.figure()
#            imgplt = plt.imshow(qmatrix)
#            imgplt.set_clim(0,500)
#            plt.figure()
#                
#        #plt.plot(qmatrix[:,634])
#        #plt.plot(qmatrix[:,605])   
##        y = qmatrix[np.where(qmatrix[:,634]!=0),634][0]
##        #y = qmatrix[:,634]    
#        
#    def testRadialAverage_testimg2(self):
#        img = Image.open(self.testimg_path)
#        x_c, y_c = 512, 512
#        
#        iq, q, errorbars, qmatrix = SASImage.radialAverage(img, x_c, y_c)
#        qmatrix = np.flipud(qmatrix)
#        qmatrix = np.flipud(np.rot90(qmatrix,3))
#        
#        if self.plot:
#            imgplt = plt.imshow(img)
#            imgplt.set_clim(0,1)
#            plt.figure()
#            imgplt = plt.imshow(qmatrix)
#            imgplt.set_clim(0,1)
        
        
if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()