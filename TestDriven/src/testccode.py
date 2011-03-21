from test_ext import *
import numpy as np

#t = np.array(range(0,40), dtype = np.long)
#t = np.zeros((10,10), dtype = np.long)

#t[:,1] = 1
t = (np.random.rand(40)*100)
for i in range(0,len(t)):
    t[i] = int(t[i])
t =  np.array(list(t), dtype = np.long)

qmatrix = np.zeros((5, 10), dtype = np.float64)

qmatrix[:,1] = 2

qmatrix[1,:] = range(0,10)

print qmatrix

test(t, qmatrix)
print 
print
print t
print np.var(t)
#print ' '
#print t