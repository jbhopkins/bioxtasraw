'''
Created on Mar 31, 2010

@author: specuser
'''

import hello
import numpy as np
import multiprocessing.synchronize
import fileIO
import cProfile
import pylab as pl

def testQ210():
    
    img, dim = fileIO.loadQuantum210Image('ADSC_Q210_AgBeh.img')
    
    img = np.float64(img)
    
    return img, dim

def testFLI():
    
    img, dim = fileIO.loadImage('FLICAM_AgBeh.tif')

    img = np.float64(img)
    
    return img, dim

def test2(img, y, x):
    
    hist, hist_c = hello.myfunc(img, y, x)  # FLI
#    hist, hist_c = hello.myfunc(img, y, x) # Q210  NB! It's ALWAYS (Y,X)
    
    return hist, hist_c
    

if __name__ == "__main__":

#    cProfile.run('img,dim = testFLI()')
#    cProfile.run('hist, hist_c = test2(img,982, 470)')
    cProfile.run('img,dim = testQ210()')
    cProfile.run('hist, hist_c = test2(img,1925, 1105)')
    
#    img,dim = testFLI()
#    hist, hist_c = test2(img, 982, 470)
##    img,dim = testQ210()
##    hist, hist_c = test2(img, 1925, 1105)
#    
#    hist = hist / hist_c
#    
#    pl.plot(hist)
#    pl.show()
