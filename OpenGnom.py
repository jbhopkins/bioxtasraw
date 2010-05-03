'''
Created on Mar 8, 2010
@author: specuser
'''
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=UserWarning)


import numpy as np
from scipy import optimize
from scipy import weave
from scipy.weave import converters
from numpy import pi, sqrt, power, exp, linalg
import pylab as pl
from pylab import sin, cos
#from LinearAlgebra import inverse

import fileIO

def shiftLeft(a, shift):
    ''' makes a left circular shift of array '''
    sh = np.shape(a)
    array_length = sh[0] * sh[1]
    
    b = a.reshape(1, array_length)
    
    res = np.zeros(array_length)
    
    start_idx = shift
    
    # SLOW! lets make it in C!
    for i in range(0, array_length):
        
        if i < (array_length - shift):
            res[i] = b[0, shift + i]
        else:
            res[i] = b[0, array_length - 1 - i - shift ]
    
    return res.reshape(sh)

def shiftRight(a, shift):
    ''' makes a right circular shift of array '''
    
    sh = np.shape(a)
    array_length = sh[0] * sh[1]
    
    b = a.reshape(1, array_length)
    
    res = np.zeros(array_length)
    
    start_idx = shift

    # SLOW! lets make it in C!
    for i in range(0, array_length):
        res[i] = b[0, i - shift]
    
    return res.reshape(sh)           

def diff(Pr, r):
    
    dPr = []
    dr = r[1]
    
    for i in range(0, len(Pr) - 1):
        dPr.append((Pr[i + 1] - Pr[i]) / dr)
        
    return dPr


def createStabilityMatrix(r):
    
    N = len(r)
    
    ########################################
    # Regularization matrix T
    ########################################
    
    eyeMat = np.eye(N)
    mat1 = shiftLeft(eyeMat, 1)
    mat2 = shiftRight(eyeMat, 1)
    
    mat2[0, 0] = 0                 #Remove the 1 in the wrong place (in the corner)
    sh = np.shape(mat1)
    mat1[sh[0] - 1, sh[1] - 1] = 0    #Remove the 1 in the wrong place (in the corner)

    dr = r[1]
    
    #from pedersen, svergun article:
    T = (mat1 + mat2) * -1 + 2 * np.eye(np.shape(mat1)[0])    # f(x) -f(x-1)/2 -f(x+1)/2 = f(x) - (f(x-1) + f(x+1))/2
    T[0, 0] = 1
    T[-1, -1] = 1
    
    #T = (mat1 + mat2) * -1 + 3*np.eye(np.shape(mat1)[0])          # sum( f(x)^2 + (f(x)-f(x-1))^2 ) 
    
    #T = (mat1 + mat2) * -1 + np.eye(np.shape(mat1)[0])          # f(x) -f(x-1)/2 -f(x+1)/2 = f(x) - (f(x-1) + f(x+1))/2
     
    #T = mat2 * -1 + 2 * np.eye(np.shape(mat2)[0])              
    
    #T = mat1 * -(1/dr) + (np.eye(np.shape(mat2)[0])*(1+(1/dr)))   # f(x) + f(x)/dr - f(x-1)/dr
    
    #T = -mat1 + (np.eye(np.shape(mat2)[0]))                       # f(x) + f(x)/dr - f(x-1)/dr
    
    #T = ((mat1*(-.5)) + (mat2*.5))                                # f(x+1)/2-f(x-1)/2  
    
    
    
    #T = np.eye(N) * 1
    #T[0, 1] = -0.5
    #T[-1, -2] = -0.5 
    
    return T

def calcPr(alpha, I, q, sigma, dmin, dmax, N, forceEndsZero=True, K = None, T = None):
    ''' Calculates the Pr function for a specified alpha, dmin and dmax '''
    
    r = np.linspace(dmin, dmax, N)
    
    if K == None:
        K = createTransformMatrix(q, r) * 4 * pi * r[1]   # Fourier transformation matrix
    if T == None:
        T = createStabilityMatrix(r)      # Tikhonov regularization matrix 

    #Solving by least squares:
    a = np.vstack((K, alpha * T))  
    b = np.hstack((I, np.zeros(np.shape(T)[0])))
    
    if forceEndsZero:
        a = a[:, 1:-1] # strip first and last column of a
        
    Pr, residues, rank, singularVals = linalg.lstsq(a, b)

    dr = r[1]

    ## Using Singular Value Decomposition:
#    u,s,v = linalg.svd(a)
#    u = np.mat(u).H
#    v = np.mat(v).H
#    S = np.zeros_like(a.T)
#    for n in range(len(s)): S[n,n] = 1. / s[n]
#    pseudoInv = np.dot(v, np.dot(S,u))
#    Pr = np.dot(pseudoInv, b)
    
    ## Using the pinv function instead of SVD
#    Pr = np.dot(linalg.pinv(a), b)
        
    #Solving it explicit:
    #T = np.eye(N)   # Identity matrix (NB not the derivative)
    #Pr = np.dot(linalg.inv((alpha * T) + np.dot(K.T,K)) , np.dot(K.T, I))

    if forceEndsZero:
        Pr = np.insert(Pr, [0], 0)  #insert fixed zero
        Pr = np.insert(Pr, [-1], 0) #insert fixed zero
    
    return Pr

def normalDistribution(mu, sigma, N, x_min=0, x_max=1):
    
    mu = 5
    sigma = 1.5
    bins = np.linspace(x_min, x_max, N)
    
    normdist = 1 / (sigma * np.sqrt(2 * np.pi)) * np.exp(-(bins - mu) ** 2 / (2 * sigma ** 2))
    
    return normdist, bins

def createTransformMatrix(q, r):
    ''' Creates the Transformation Matrix T   I_m = sum( T[i,j] * p[j] + e ) i.e. the Fourier transform '''
    
    #Reserve memory
    T = np.zeros((len(q), len(r)))
    
    qlen = len(q)
    rlen = len(r)
    
    q = np.array(q)
    r = np.array(r)
    
    #Stepsize in r
    dr = r[1]
    
    # Leaving out 4 * pi * dr! 
    c = 1 #4 * pi * dr   
    #================================================
    #                C++ CODE
    #================================================
    code = """
    
    float chk, qr;
    int i, j;
    
    for( i = 0; i < qlen; i++)
           for( j = 0; j < rlen; j++)
           {
                 
                 qr = q(i) * r(j);
                 chk = float(c) * sin(qr) / qr ;

                  if(chk != chk) {
                      T(i,j) = 0.5;
                  }
                  else {
                      T(i,j) = chk; 
                  }
                      
           }
           
    """   
    weave.inline(code, ['qlen', 'rlen', 'T', 'r', 'q', 'c'], type_converters=converters.blitz, compiler="gcc")    
            
    return T

def distDistribution_Sphere(N, scale_factor, dmax):    
    ''' 
        P(r) for a sphere 
        N = distribution length 
        scale_factor = I_exp(0) (Just the first value in I_exp)
        
        "Neutrons X-rays and light scattering methods applied to soft condensed matter.", Page 84 
    '''
    R = dmax / 2.
    r = np.linspace(0, dmax, N)                  # the r-axis in P(r)
       
    P = (3 / (4 * pi)) * (power(r, 2) / power(R, 2)) * (2 - (3 / 2.) * (r / R) + (power(r, 3) / (8 * power(R, 3)))) * scale_factor
    
    return P, r

def sphereFormFactor(q, r = 60, scale=1, contrast=1e-6, bkg=0):
    
    V = 1
    
    F = scale / V * power((3 * V * contrast * (sin(q * r) - q * r * cos(q * r))) / power(q * r, 3), 2)
    
    F = F + bkg
    
    return F

def norm(pr):
    ''' Calculates the norm of the incomming vector '''

    norm = sqrt(sum(power(pr, 2)))
    
    return norm
    
def OSCILL(Pr, r):
    ''' If the criterion OSCILL is close to 1, P(r) is a smooth function.
    For sphere OSCILL = 1.1. OSCILL ~= 2 corresponds to a smooth bimodal
    or an oscillating monomodal '''
    
    dPr = []
    dr = r[1]
    
    for i in range(0, len(Pr) - 1):
        dPr.append((Pr[i + 1] - Pr[i]) / dr)
      
    D_min = r[0]
    D_max = r[-1]
    
    OSC = (norm(dPr) / norm(Pr)) / (pi / (D_max - D_min))
        
    return OSC

def SYSDEV(Pr, r, I, q):
    ''' In the absence of systematic deviations in reciprocal space, the
    the value of the criterion SYSDEV must be close to 1''' 
    
    dr = r[2] - r[1]
    K = createTransformMatrix(q, r) * 4 * pi * dr
    
    I_Pr = np.dot(Pr, np.transpose(K))
    
    deltaI = I - I_Pr
    
    N_s = 0
                
    for k in range(0, len(deltaI) - 1):
        prod = deltaI[k] * deltaI[k+1]
        if (prod < 0):
            N_s = N_s + 1
    
    N = len(I)
    
    print 'SysDev_Ns : ',N_s
    
    SYS = N_s / np.floor(((N - 1) / 2.))
     
    return SYS

def STABIL(Pr, r, I, q, sigma, alpha, dmin, dmax, N, forceEndsZero=True):
    ''' According to the point-of-inflection and quasi-optimality methods (Glatter)
    a value of STABIL << 1 can be expected in the vicinity of the correct solution '''
        
    Pr_dAlpha = calcPr(2 * alpha, I, q, sigma, dmin, dmax, N, forceEndsZero)
    
    #Pr_dAlpha = Pr_dAlpha / (4 * pi * r[1])
    
    STA = (norm(Pr - Pr_dAlpha) / norm(Pr)) # / (dAlpha/alpha)
    
    return STA
    
def POSITV(Pr):
    ''' In many cases it is known that p(r) should be non-negative function.
    For a non-negative function POSITIV = 1''' 
    
    Pr_plus = Pr.copy()
    
    Pr_plus[np.where(Pr_plus < 0)] = 0
    
    POS = norm(Pr_plus) / norm(Pr)
    
    return POS

def VALCEN(Pr, r):
    ''' When dmax is correctly specified, the most information should be contained
     in the central part of P(r). For a solid sphere VALCEN = 0.95 ''' 
    
    Pr_star = Pr.copy()
    
    D_min = r[0]
    D_max = r[-1]
    
    dD = D_max - D_min
    
    low_limit = D_min + (dD / 4.) 
    high_limit = D_max - (dD / 4.)
    
    for c in range(0, len(r)):
        
        if r[c] > low_limit and r[c] < high_limit:
            pass
        else:
            Pr_star[c] = 0
            
    Pr_star_neg = Pr_star.copy()
    Pr_star_neg[np.where(Pr_star_neg > 0)] = 0
    
    Pr_star_pos = Pr_star.copy()
    Pr_star_pos[np.where(Pr_star_pos < 0)] = 0
        
    maxPr_star = max([norm(Pr_star_neg), norm(Pr_star_pos)])
        
    VAL = maxPr_star / norm(Pr)


    return VAL

def DISCRP(I, I_Pr, sigma, Chi):
        
    N = len(I)

    Idif = sum( ((I - I_Pr) / sigma)**2) / (N-1) 
    
    dis = sqrt(Idif - Chi)
    #print dis
    
    return dis

def CalcProbability(DISCRP, OSCILL, STABIL, SYSDEV, POSITV, VALCEN, WCA_Parameters=None):
    ''' WARNING TAKING OUT DISCRP BY SETTING W = 0 '''
    
    # (   B  ,  W ,   C ,  A )
    #Values taken from "Determination of the regularization parameter
    #in indirect-transformmethods using perceptual criteria, Svergun (1992)"
    
    Prob = []
    Weights = []
    
    if WCA_Parameters == None:
        WCA_Parameters = [(DISCRP, 0.0, 0.3, 0.7), (OSCILL, 3.0, 0.6, 1.1), (STABIL, 3.0, 0.12, 0.0),
                          (SYSDEV, 3.0, 0.12, 1.0), (POSITV, 1.0, 0.12, 1.0), (VALCEN, 1.0, 0.12, 0.95)]
        
        for B, W, C, A in WCA_Parameters:    
            Prob.append(exp(-power((A - B) / C, 2)))
            Weights.append(W)
        
    else:
        #Ugly hack to easier fit into RAW
        WCA_Param = []
        
        lst = [DISCRP, OSCILL, STABIL, SYSDEV, POSITV, VALCEN]
        
        for i in range(0, len(WCA_Parameters)):
            W = WCA_Parameters[i][0]
            C = WCA_Parameters[i][1]
            A = WCA_Parameters[i][2]
            B = lst[i]
            
            Prob.append(exp(-power((A - B) / C, 2)))
            Weights.append(W)
    
    TOTAL = sum(np.array(Weights) * np.array(Prob)) / sum(Weights)
    
    return TOTAL

def costFuncChiSquared(alpha, r, I, q, sigma, dmax, N, ChiSq, WCA_Params=None, forceEndsZero=True, K = None, T = None):
    
    alpha = np.exp(alpha)
    
    Pr = calcPr(alpha, I, q, sigma, 0, dmax, N, forceEndsZero = forceEndsZero, K= K, T= T)
    
    if K==None:
        K = createTransformMatrix(q, r)

    I_Pr = np.dot(K, Pr)
       
    ChiSquared = sum( ((I-I_Pr)/sigma)**2 )

    #print ChiSquared / (len(I)-1)

    return ChiSquared
    
def costFunc(alpha, r, I, q, sigma, dmax, N, ChiSq=0, WCA_Params=None, forceEndsZero=True, K = None, T = None):
    
    alpha = np.exp(alpha)
    
    if K == None:
        K = createTransformMatrix(q, r) * 4 * pi * r[1]
    if T == None:
        T = createStabilityMatrix(r)
    
    Pr = calcPr(alpha, I, q, sigma, 0, dmax, N, forceEndsZero, K, T)
    
    I_Pr = np.dot(K, Pr)
    
    TOTAL = CalcProbability(DISCRP(I, I_Pr, sigma, ChiSq),
                            OSCILL(Pr, r),
                            STABIL(Pr, r, I, q, sigma, alpha, 0, dmax, N, forceEndsZero = forceEndsZero),
                            SYSDEV(Pr, r, I, q),
                            POSITV(Pr),
                            VALCEN(Pr, r), WCA_Params)
            
    return -TOTAL      #negative since we want to maximize TOTAL


#def goldenSectionSearch(F, a, c, b, absolutePrecision):
#
#    if abs(a-b) < absolutePrecision:
#        return (a+b)/2
#    
#    #Create a new possible center, in the area between c and b, pushed against c
#    d = c + resphi*(b-c)
#    
#    if F(d) > F(c):
#    
#        return goldenSectionSearch(F, c, d, b, absolutePrecision)
#    return goldenSectionSearch(F, d, c, a, absolutePrecision)
# 

def searchAlpha(r, I_alpha, q, sigma, dmax, N,
                alphamin=10e-8,
                alphamax=1000,
                alphapoints=100,
                WCA_Params=None,
                forceEndsZero=True,
                costFunction=costFunc,
                ChiSq=0,
                PlotSearch=False):
    
    #alphaGuess = sum(np.power(norm(K),2)) / norm(I_alpha)
    
    #Determine TOTAL for different alpha values to determine a good starting point
    alphatotal = []
    
    alphavals = np.linspace(-20, 15, 100)
    alphavals = np.exp(alphavals)
    
    K = createTransformMatrix(q, r) * 4 * pi * r[1]
    T = createStabilityMatrix(r)
    
    for alpha in alphavals:
        alphatotal.append(costFunction(np.log(alpha), r, I_alpha, q, sigma, dmax, N, ChiSq, WCA_Params, forceEndsZero, K, T))
        
    alphaGuess = alphavals[ alphatotal.index(min(alphatotal)) ] 

    #print np.log(alphavals)
    if PlotSearch == True:
        print 'GUESS : ', alphaGuess, np.log(alphaGuess)
                
        fig = pl.figure(1)
        pl.plot(np.log(alphavals), -1 * np.array(alphatotal), '.')
        
        
        pl.xlabel('log(alpha)')
        pl.ylabel('TOTAL')
        pl.show()
    
    alpha = optimize.fmin(costFunction, np.log(alphaGuess), (r, I_alpha, q, sigma, dmax, N, ChiSq, WCA_Params, forceEndsZero, K, T))
    
    return alpha


def searchAN1(r, I, q, sigma, dmax, N,
                WCA_Params=None,
                forceEndsZero=True,
                costFunction=costFunc,
                ChiSq=0,
                PlotSearch=False):
    
    #alphaGuess = sum(np.power(norm(K),2)) / norm(I)
    
    #Determine TOTAL for different alpha values to determine a good starting point
    alphatotal = []
    
    alphavals = np.linspace(-20, 5, 200)
    alphavals = np.exp(alphavals)
    
    K = createTransformMatrix(q, r) * 4 * pi * r[1]
    T = createStabilityMatrix(r)
    
    for alpha in alphavals:
        alphatotal.append(costFunction(np.log(alpha), r, I, q, sigma, dmax, N, ChiSq, WCA_Params, forceEndsZero, K, T))
        
    alphaGuess = alphavals[ alphatotal.index(min(alphatotal)) ] 

    if PlotSearch == True:
        print 'GUESS : ', alphaGuess, np.log(alphaGuess)
                
        fig = pl.figure(1)
        pl.plot(np.log(alphavals), -1 * np.array(alphatotal), '.')
        
        
        pl.xlabel('log(alpha)')
        pl.ylabel('TOTAL')
        pl.show()
    
    alpha = optimize.fmin(costFunction, np.log(alphaGuess), (r, I, q, sigma, dmax, N, ChiSq, WCA_Params, forceEndsZero, K, T))
    
    AN1 = costFunction(alpha, r, I, q, sigma, dmax, N, ChiSq, WCA_Params, forceEndsZero, K, T)
    print 'Final AN1 : ', AN1 / (len(I)-1)
    
    return AN1 / (len(I)-1)

def getGnomPr(I, q, sigma, N, dmax, dmin=0, alphamin=0.01, alphamax=60, alphapoints=100, WCA_Params=None, forceEndsZero=True, ChiSq=0):
    ''' Returns the optimal Pr function according to the GNOM algorithm (GNOM calulates alpha) '''
    
    r = np.linspace(dmin, dmax, N)
    
    #Find optimal alpha:
    alpha = searchAlpha(r, I, q, sigma, dmax, N, alphamin, alphamax, alphapoints, WCA_Params, forceEndsZero)
    
    K = createTransformMatrix(q, r)
    
    Pr = calcPr(alpha, I, q, sigma, dmin, dmax, N, forceEndsZero)
    I_Pr = np.dot(Pr, np.transpose(K))
    
    TOTAL = -costFunc(alpha[0], r, I, q, sigma, dmax, N, WCA_Params=WCA_Params, forceEndsZero=forceEndsZero)
    
    I0, Rg = calcRgI0(Pr, r)
    
    ChiSq = sum(np.power(np.array(I) - np.array(I_Pr), 2) / np.power(sigma, 2))
    
    allcrit = getAllCriteriaResults(Pr, r, I, q, sigma, alpha, dmin, dmax, N, forceEndsZero=forceEndsZero)
    
    info = {'dmax_points' : 0,
                'alpha_points' : 0,
                'all_posteriors' : allcrit,
                'alpha' : alpha[0],
                'dmax' : dmax,
                'orig_i' : I,
                'orig_q' : q,
                'orig_err': sigma,
                'I0' : I0,
                'ChiSquared' : ChiSq,
                'gnomTOTAL' : round(TOTAL, 4),
                'Rg' : Rg}
    
    return Pr, r, I_Pr, info

def singleSolveInRAW(alpha, dmax, SelectedExpObj, N, dmin=0, forceEndsZero=True, WCA_Params=None):
    ''' Solves optimal Pr for a given dmax and alpha.. this routine also calculates info needed by RAW ''' 
    
    I = SelectedExpObj.i
    q = SelectedExpObj.q
    sigma = SelectedExpObj.errorbars
    
    Pr = calcPr(alpha, I, q, sigma, dmin, dmax, N, forceEndsZero)
    r = np.linspace(dmin, dmax, N)
    
    K = createTransformMatrix(q, r)
    
    Pr = calcPr(alpha, I, q, sigma, dmin, dmax, N)
    I_Pr = np.dot(Pr, np.transpose(K))
    
    TOTAL = -costFunc(alpha, r, I, q, sigma, dmax, N, WCA_Params)
    
    I0, Rg = calcRgI0(Pr, r)
    
    ChiSq = sum(np.power(np.array(I) - np.array(I_Pr), 2) / np.power(sigma, 2))
    
    allcrit = getAllCriteriaResults(Pr, r, I, q, sigma, alpha, dmin, dmax, N, forceEndsZero)
    
    info = {'dmax_points' : 0,
                'alpha_points' : 0,
                'all_posteriors' : allcrit,
                'alpha' : alpha,
                'dmax' : dmax,
                'orig_i' : I,
                'orig_q' : q,
                'orig_err': sigma,
                'I0' : I0,
                'ChiSquared' : ChiSq,
                'gnomTOTAL' : TOTAL,
                'Rg' : Rg}
    
    return Pr, r, I_Pr, info

def getAllCriteriaResults(Pr, r, I, q, sigma, alpha, dmin, dmax, N, ChiSq=0, forceEndsZero=False):
    
    val = round(VALCEN(Pr, r), 4)
    osc = round(OSCILL(Pr, r), 4)
    pos = round(POSITV(Pr), 4)
    sysd = round(SYSDEV(Pr, r, I, q), 4)
    sta = round(STABIL(Pr, r, I, q, sigma, alpha, 0, dmax, N, forceEndsZero), 4)
    
    K = createTransformMatrix(q, r) * 4 * pi * r[1]
    I_Pr = np.dot(Pr, np.transpose(K))
    
    dsc = round(DISCRP(I, I_Pr, sigma, ChiSq), 4)
    
    allcrit = [('VALCEN', val),
               ('OSCILL', osc),
               ('POSITV' , pos),
               ('SYSDEV', sysd),
               ('STABIL', sta),
               ('DISCRP', dsc)]
    
    return allcrit
    
def calcRgI0(Pr, r):
    
    dr = r[1]
    
    area = 0
    area2 = 0
    for x in range(1, len(Pr)):                       
        area = area + dr * ((Pr[x - 1] + Pr[x]) / 2)                   # Trapez integration
        area2 = area2 + dr * ((Pr[x - 1] + Pr[x]) / 2) * pow(r[x], 2)  # For Rg^2 calc
        
    RgSq = area2 / (2 * area)
    Rg = sqrt(abs(RgSq))
    
    I0 = area
    
    return I0, Rg

def FindOptimalChiSquared(I, q, sigma, dmax, N):
    
    r = np.linspace(0, dmax, N)
    K = createTransformMatrix(q, r) * 4 * pi * r[1]
    
    Pr, residues, rank, singularVals = linalg.lstsq(K, I)
    
    I_Pr = np.dot(K, Pr)
    
    ChiSq = np.sum(((I_Pr-I)/sigma)**2 )
    
    print 'CHIII : ', ChiSq
    
#    pl.figure()
#    pl.semilogy(I_Pr)
#    pl.semilogy(I, 'r')
#    pl.figure()
#    pl.plot(r, Pr)
#    pl.show()

    return ChiSq

def loadGnomFit(filename):
    ''' For loading a chopped .out file with only the experimental data and the fit '''
    
    import re
    
    iq_pattern = re.compile('\s*\d*[.]\d*[+E-]*\d+\s+-?\d*[.]\d*[+E-]*\d+\s+-?\d*[.]\d*[+E-]*\d+\s+-?\d*[.]\d*[+E-]*\d+\s+?\d*[.]\d*[+E-]*\d+\r?\n')
    
    f = open(filename)
    
    S = []
    J_EXP = []
    ERROR = []
    J_REG = []
    I_REG = []
        
    try:
        for line in f:
            iq_match = iq_pattern.match(line)
            
            if iq_match:
                found = iq_match.group().split()
                
                S.append(float(found[0]))
                J_EXP.append(float(found[1]))
                ERROR.append(float(found[2]))
                J_REG.append(float(found[3]))
                I_REG.append(float(found[4]))
                        
    finally:
        f.close()
        
    return S, J_EXP, ERROR, J_REG, I_REG



def loadGnomOutFile(filename):
    ''' For loading an entire .out file '''
    
    qfull = []
    qshort = []
    Jexp = []
    Jerr = []
    Jreg = []
    Ireg = []

    R = []
    P = []
    Perr = []

    fname = filename

    print "reading ", fname
    
    fline = open(fname).readlines()

    i = 0
    crit = {}
    
    while (i < len(fline)):
        if (fline[i].find('The measure of inconsistency AN1 equals to') > -1): 
            tmp = fline[i].split()
            crit['AN1'] = float(tmp[7])
            #print "AN1 = ", AN1
            break 
        i = i + 1
        
    
    while(i < len(fline)):
        if(fline[i].find('Parameter    DISCRP    OSCILL    STABIL    SYSDEV    POSITV    VALCEN') > -1):
           names = fline[i].split()
           i = i + 4
           values = fline[i].split()
           
           for c in range(1, len(names)):
               crit[names[c]] = float(values[c])
           break
        i = i + 1
        
    while(i < len(fline)):
        if(fline[i].find('Current ALPHA') > -1):
           alphastring = fline[i].split()
           crit['ALPHA'] = float(alphastring[3])
           crit['RG'] = float(alphastring[6])
           crit['I0'] = float(alphastring[9])
           break
        i = i + 1
        
    while(i < len(fline)):
        if(fline[i].find('Total') > -1):
           totalstr = fline[i].split()
           crit['TOTAL'] = float(totalstr[3])
           break
        i = i + 1
    

    while (i < len(fline)):
        if (fline[i].find('S          J EXP       ERROR       J REG       I REG') > -1): break 
        i = i + 1

    print "found data profile section at ", i

    i = i + 2

    # extract experimental and fitted profiles
    
    while (i < len(fline)):

         tmp = fline[i].split()

         if (len(tmp) == 2):
            qfull.append(float(tmp[0]))
            Ireg.append(float(tmp[1]))
            
         elif (len(tmp) == 5):
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
         
    qshort = np.array(qshort)
    Jexp = np.array(Jexp)
    Jerr = np.array(Jerr)
    Jreg = np.array(Jreg)
    Ireg = np.array(Ireg)
    R = np.array(R)
    P = np.array(P)
    Perr = np.array(Perr)
              
    return qshort, Jexp, Jerr, Jreg, Ireg, R, P, Perr, crit

#---- *** TEST FUNCTIONS ***

def Test_GnomPr(filename):
    
    S, J_EXP, J_ERR, J_REG, I_REG, r, Pr, Pr_sigma, gnomcrit = loadGnomOutFile(filename)

    print 'Gnom Alpha :', gnomcrit['ALPHA']
    crit = getAllCriteriaResults(Pr, r, J_EXP, S, J_ERR, gnomcrit['ALPHA'], 0, r[-1], len(r), forceEndsZero=False)

    print 'N (I) : ', len(J_EXP)
    print 'M (Pr) : ', len(Pr)
    
    #J_EXP2, S2, J_ERR2 = binCurve(J_EXP, S, J_ERR, 1)

    ChiSq = FindOptimalChiSquared(J_EXP, S, J_ERR, dmax=r[-1], N=len(Pr))
    AN2 = ChiSq / (len(J_EXP)-1)
    crit.append(('AN1', AN2))
    
    DISCRP_RAW = DISCRP(J_EXP, J_REG, J_ERR, AN2)
    
    for i in range(0,len(crit)):
        if crit[i][0] == 'DISCRP':crit[i] = ('DISCRP', DISCRP_RAW)
    
    total = CalcProbability(crit[5][1], crit[1][1], crit[4][1], crit[3][1], crit[2][1], crit[0][1])
    crit.append(('TOTAL', total))
    
    ################ PLOT TABLE ###########################
    
    print ' '*9 + 'RAW' + ' '*5 + 'GNOM' + ' '*4 + 'DIFF'
    print '-'*30
    for each in crit:
        print each[0] + ' '*(6-len(each[0])) + ' :' + '%.4f'% each[1] + '  ' + '%.4f'% gnomcrit[each[0]] + '  ' + '%.2f'% abs(((1-(each[1]/gnomcrit[each[0]]))*100)) + '%'
    print '-'*30
    
    #######################################################
    
    AN1 = gnomcrit['AN1']
    Idif2 = ((np.array(J_EXP) - np.array(J_REG)) / J_ERR) ** 2
    disc = np.sqrt((Idif2.sum() / (len(J_EXP) - 1)) - AN1**2)
    
    print 'Discrp using gnom AN1: ' + '%.4f'%disc + '  %.4f'% gnomcrit['DISCRP'] + '  %.2f'%abs((1-(disc/gnomcrit['DISCRP']))*100) + '%'
    
    dr = r[1]
    K = createTransformMatrix(S, r) * (4 * pi * dr)
    I_Pr = np.dot(K, Pr)
    
    tst1 = np.sum(J_EXP**2)
    tst2 = np.sum(K**2)
    print 'Max Alpha: ', tst2 / np.sqrt(tst1)
    
    print 'AN solution: ', Idif2.sum() / (len(J_EXP)-1)  
      
    pl.figure()
    pl.plot(r, Pr)
    pl.title(filename)
    pl.figure()
    pl.semilogy(S, J_EXP)
    pl.semilogy(S, I_Pr, 'r')
    pl.semilogy(S, J_REG, 'g')
    pl.title(filename)
    pl.show()
#    
def binCurve(I, q, err, binsize):
        
    noOfBins = int(np.floor(len(I) / binsize))
    
    new_i = np.zeros(noOfBins)
    new_q = np.zeros(noOfBins)
    new_err = np.zeros(noOfBins)
    
    for eachbin in range(0, noOfBins):
        start_idx = eachbin * binsize
        end_idx = (eachbin * binsize) + binsize
        tst = range(start_idx, end_idx)
            
        new_i[eachbin] = sum(I[start_idx:end_idx]) / binsize
        new_q[eachbin] = sum(q[start_idx:end_idx]) / binsize
        
        new_err[eachbin] = sqrt(sum(err[start_idx:end_idx]**2))
    
    return new_i, new_q, new_err
        

def Test_ChiSquaredSearch():
    
    ExpObj, FullImage = fileIO.loadFile('lyzexp.dat')
    #ExpObj, FullImage = fileIO.loadFile('diff.dat')
    
    I = ExpObj.i
    q = ExpObj.q
    sigma = ExpObj.errorbars
    
    dmax = 45
    N = 50

    r = np.linspace(0, dmax, N)
    K = createTransformMatrix(q, r)
    
    alpha = searchAlpha(r, I, q, sigma, dmax, N, costFunction=costFuncChiSquared) 
    alpha = np.exp(alpha)
    
    print 'Optimal Alpha : ', alpha
    
    Pr = calcPr(alpha, I, q, sigma, 0, dmax, N, forceEndsZero=True)
    
    pl.plot(r, Pr)
    
    pl.show()
    
def Test_RunGnomOnFile(filename,
                        dmax, N,
                        alpha = None,
                        AN1 = None,
                        PlotSearch = False,
                        forceEndsZero = False,
                        filetype = None,
                        startIdx = None, 
                        PlotResult = True):
        
    if filetype == 'GnomOut':
        q, I, sigma, J_REG, I_REG, r, Pr, Pr_sigma, AN1Gnom = loadGnomOutFile(filename)
        N = len(Pr)
        I = I + 0.1
        
    else:
        ExpObj, Img = fileIO.loadFile(filename)
        q = ExpObj.q
        I = ExpObj.i
        sigma = ExpObj.errorbars
        r = np.linspace(0, dmax, N)
        
#    I = sphereFormFactor(q, r = 22.5)
#    err = 0.05 * I
#    sigma = np.abs(np.random.rand(len(I))) * err
#    I = I - np.random.rand(len(I)) * (0.05*I)
        
    print 'Number of points : ', len(I)
    print 'Dmax : ', dmax

    ######### Calculate Chi squared without stabilisation #######
    if AN1 == None:
        # Simply solve equation Kp = I  by least squares approximation:
        #ChiSq = FindOptimalChiSquared(I, q, sigma, dmax, N)
        
        # Searching for best ChiSquare for different alpha values:
        AN1 = searchAN1(r, I, q, sigma, dmax, N, ChiSq=0, costFunction=costFuncChiSquared, PlotSearch = PlotSearch, forceEndsZero=forceEndsZero)
    else:
        ChiSq = 1

    K = createTransformMatrix(q, r) * 4 * pi * r[1]

    ########## Calculate optimal Alpha ###########
    if alpha == None:
        alpha = searchAlpha(r, I, q, sigma, dmax, N, ChiSq=AN1, costFunction=costFunc, PlotSearch = PlotSearch, forceEndsZero=forceEndsZero)
        alpha = np.exp(alpha)
        
    print '\nOptimal Alpha: ', str(alpha)
    
    ########## Get Pr function for optimal alpha #########
    Pr = calcPr(alpha, I, q, sigma, 0, dmax, N, forceEndsZero=forceEndsZero)
    dr = r[2] - r[1]
    
    crit = getAllCriteriaResults(Pr, r, I, q, sigma, alpha, 0, dmax, len(r), AN1, forceEndsZero=forceEndsZero)
    
    for each in crit:
        print each[0] + ' :', each[1]
    
    I_Pr = np.dot(K, Pr)
    
    Total = CalcProbability(DISCRP(I, I_Pr, sigma, AN1), OSCILL(Pr, r), STABIL(Pr, r, I, q, sigma, alpha, 0, dmax, N, forceEndsZero = forceEndsZero), SYSDEV(Pr, r, I, q), POSITV(Pr), VALCEN(Pr, r))
    print 'TOTAL  :', Total
         
    chi = sum( ((I - I_Pr)/sigma)**2 )
    
    I0, Rg = calcRgI0(Pr, r)
    
    print '\nRg   :', Rg
    print 'I0     :', I0
    print 'AN1    : ', AN1
    print 'ChiSqFit : ', chi
    print 'ChiSqFitDivN : ', chi / (len(I)-1)
    
    if PlotResult == True:
        #Print Criteria:
        pl.figure()
        #pl.subplot(211)
        pl.plot(r, Pr, 'r')
        #pl.subplot(212)
        pl.figure()
        pl.semilogy(q, I_Pr, 'red')
        pl.semilogy(q, I, '.')
        pl.show()
    
    return r, Pr, I_Pr, I, Total

def Test_GnomOnFiguresInArticle():
    pass

################################################################
        
    #FIGURES SIMILAR TO THOSE IN THE ARTCILE:
    #normdist = (np.cos(2*pi*1*bins)+1)/2                  #F
    #normdist = np.sin(2*pi*1.5*bins)                      #E
    #normdist = np.sin(2*pi*.5*bins)                       #A
    #normdist = np.sin(2*pi*6*bins) * np.sin(2*pi*.5*bins) #D       
#    tst = sphereFormFactor(q, 30)

########################################################
# Simulated Sphere
########################################################
#    #Simulate P(r) for a sphere:
     #N = 50
     #scale = 1
     #dmax = 45
#    Pr, r = distDistribution_Sphere(N, scale, dmax)    
#    q = np.linspace(0.005, 0.35, 250)
#    
#    #Transform simulated p(r)
#    K = createTransformMatrix(q, r)
#    I_alpha = np.dot( Pr, np.transpose(K) )
#    
#    #Add Noise:
#    sigma =  0.5 * np.random.randn(np.size(I_alpha))
#    I_alpha = I_alpha + sigma
#########################################################

    ChiSq = 0 # The ChiSquared part of the Discrepancy Criteria
    crit = getAllCriteriaResults(Pr, r, I, q, sigma, alpha, 0, dmax, len(r), ChiSq, forceEndsZero=True)
    
    for each in crit:
        print each[0] + ' :' + str(each[1])

if __name__ == '__main__':
    
    ####### CAREFUL!!! ####################################
    #SYSDEV HAS THE 4 * pi *dr on it to test the GNOM data! and Check STABILL too before running Test_GnomPr
    #######################################################
    
    #Test_GnomPr('/home/specuser/lyzgnom.out')
    Test_GnomPr('/home/specuser/lyzgnomNotForced.out')
    print 'Hello!'
#    Test_GnomPr('diffgnom.out')
#    Test_GnomPr('/home/specuser/diffgnomNotForced.out')
#    
#    Test_GnomPr('virgnom.out')
#    Test_GnomPr('/home/specuser/virgnomForced.out')
    
    #testChiSquaredSearch()

    #Test_RunGnomOnFile('lyzexp.dat', dmax = 45, N=100, PlotSearch = True, forceEndsZero = False)
    #r, Pr, I_Pr, I, Total = Test_RunGnomOnFile('/home/specuser/diffgnom.out', dmax = 45, N=101, PlotSearch = True, forceEndsZero = False, filetype = 'GnomOut')
    #r, Pr, I_Pr, I, Total = Test_RunGnomOnFile('/home/specuser/virgnom.out', dmax = 280, N=100, alpha = 1, PlotSearch = False, forceEndsZero = False, filetype = 'GnomOut')




############## Loop over different Dmax values ###############

#    Iplotted = False
#    prleg = []
#    fitleg = []
#    dmaxrange = range(270,310)
#    
#    save = []
#    for dmax in dmaxrange:
#    
#        #r, Pr, I_Pr, I, Total = Test_RunGnomOnFile('/home/specuser/diffgnom.out', dmax = dmax, N=100, PlotSearch = False, forceEndsZero = True, filetype = 'GnomOut')
#        #r, Pr, I_Pr, I, Total = Test_RunGnomOnFile('/home/specuser/lyzgnom.out', dmax = dmax, N=100, PlotSearch = False, forceEndsZero = False, filetype = 'GnomOut')
#        #r, Pr, I_Pr, I, Total = Test_RunGnomOnFile('/home/specuser/Subtr00.dat', dmax = dmax, N=100, PlotSearch = False, forceEndsZero = False)
#        r, Pr, I_Pr, I, Total = Test_RunGnomOnFile('/home/specuser/virgnom.out', dmax = dmax, N=100, PlotSearch = False, forceEndsZero = False, filetype = 'GnomOut')
#        
#        save.append((Total, r, Pr, I_Pr, I))
#        
#    totals = []
#    print save
#    for each in save:
#        totals.append(each[0])
#    
#    print totals
#    #maxidx = totals.index[max(totals)]
#    
#    pl.figure()
#    pl.plot(dmaxrange, totals)
#    #pl.plot(save[maxidx][3])
#    #pl.plot(save[maxidx][4],'.b')
#    
#    pl.show()
        
    #q, I, sigma, J_REG, I_REG = loadGnomFit('/home/specuser/diff.txt.txt')
    
    
    
