'''
Created on Apr 29, 2010

@author: specuser

'''

import numpy as np
from transmatrix_ext import trans_matrix

def HouseholderTransform(A,k = 1):
    
    n = len(A[:,k-1])
    v = np.zeros(n)
    
    alpha = -np.sign(A[k,k-1]) * np.sqrt( ((A[k:,k-1])**2).sum() )   
    r = np.sqrt( (alpha**2-(A[k,k-1]*alpha))/2 )
    
    for i in range(k, n):    
        if i == k:
            v[i] = (A[i,k-1] - alpha)/(2*r)
        else:
            v[i] = A[i,k-1]/(2*r)
    
    Q = np.eye(A.shape[0],A.shape[1])-2*np.outer(v,v.T)
        
    A1 = np.dot(Q, np.dot(A,Q))
    
    if k == n-2:
        return A1
    else:
        A_out = HouseholderTransform(A1,k+1)
    
    return A_out


def fouriermatrix(q,r):
    
    A = np.zeros((len(q), len(r)))
    
    for i in range(0,len(q)):
        for j in range(0,len(r)):
    
            qr = q[i] * r[j]
            A[i,j] = np.sin(qr) 
    
    return A


if __name__ == '__main__':
    
    #A = np.array([[4,1,-2,2], [1,2,0,1], [-2,0,3,-2], [2,1,-2,-1]])
    
    q = np.linspace(0.001, 0.3, 10)
    r = np.linspace(0,40,5)
    
    F = fouriermatrix(q,r)
    
    print F
    
    #A = np.array([[4,2,2,1], [2,-3,1,1], [2,1,3,1], [1,1,1,2]], dtype = np.float128)

    Q = HouseholderTransform(T)
    print Q
    
    print np.diag(Q)
    print np.diag(Q, k=1)
    print np.diag(Q, k=-1)
    

    
    
    