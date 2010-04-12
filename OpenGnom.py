'''
Created on Mar 8, 2010

@author: specuser
'''
import numpy as np
from scipy import optimize
from scipy import weave
from scipy.weave import converters
from numpy import pi, sqrt, power, exp, linalg
import pylab as pl
from pylab import sin, cos
#from LinearAlgebra import inverse

import fileIO

def shiftLeft(a,shift):
    ''' makes a left circular shift of array '''
    sh = np.shape(a)
    array_length = sh[0] * sh[1]
    
    b = a.reshape(1, array_length)
    
    res = np.zeros(array_length)
    
    start_idx = shift
    
    # SLOW! lets make it in C!
    for i in range(0,array_length):
        
        if i < (array_length - shift):
            res[i] = b[0, shift + i]
        else:
            res[i] = b[0, array_length-1 - i - shift ]
    
    return res.reshape(sh)

def shiftRight(a, shift):
    ''' makes a right circular shift of array '''
    
    sh = np.shape(a)
    array_length = sh[0] * sh[1]
    
    b = a.reshape(1,array_length)
    
    res = np.zeros(array_length)
    
    start_idx = shift

    # SLOW! lets make it in C!
    for i in range(0,array_length):
        res[i] = b[0, i - shift]
    
    return res.reshape(sh)           

def diff(Pr, r):
    
    dPr = []
    dr = r[1]
    
    for i in range(0,len(Pr)-1):
        dPr.append((Pr[i+1]-Pr[i])/dr)
        
    return dPr

#def constraint(Pr, r):
#        
#    Omega = sqrt(sum(power(diff(Pr, r),2)))
#    
#    return Omega
#
#def chiSquared(Pr, r, I, q, sigma, K):
#    
#    I_alpha = np.dot( Pr, np.transpose(K))
#    
#    chiSquare = sqrt( sum( power(I - I_alpha,2)/power(sigma,2) ) )
#  
#    return chiSquare     
#
#def lossFunc(Pr, r, I, q, sigma, K, alpha):
#    
#    return chiSquared(Pr, r, I, q, sigma, K) + alpha*constraint(Pr,r)

def calcPr(alpha, I, q, sigma, dmin, dmax, N, forceInitZero = True):
    ''' Calculates the Pr function for a specified alpha, dmin and dmax '''
    
    r = np.linspace(dmin, dmax, N)
    K = createTransformMatrix(q, r)   #Fourier transformation matrix
        
    #Solving it explicit:
    #T = np.eye(N)   # Identity matrix (NB not the derivative)
    #Pr = np.dot(linalg.inv((alpha * T) + np.dot(np.transpose(K),K)) , np.dot(np.transpose(K), I))
    
    ########################################
    # Regularization matrix T
    # -------------------------------------- 
    # Derivative matrix consists of ones in
    # the diagonal with -1/2 adjacent
    # to the diagonal and zero otherwise
    ########################################
    eyeMat = np.eye(N)
    mat1 = shiftLeft(eyeMat,1)
    mat2 = shiftRight(eyeMat, 1)
    
    mat2[0,0] = 0                 #Remove the 1 in the wrong place (in the corner)
    sh = np.shape(mat1)
    mat1[sh[0]-1, sh[1]-1] = 0    #Remove the 1 in the wrong place (in the corner)

    T = (mat1 + mat2) * -0.5 + np.eye(np.shape(mat1)[0])
    ########################################
    
    #T = mat2 * 0.5 -0.5*np.eye(np.shape(mat2)[0])
    
    #Solving by least squares:
    a = np.vstack((K, alpha*T))  
    b = np.hstack((I, np.zeros(np.shape(T)[0])))
    
    if forceInitZero:
        a = a[:,1:-1] #strip first and last column of a
        
        
    Pr, residues, rank, singularVals = linalg.lstsq(a,b)
    
    if forceInitZero:
        Pr = np.insert(Pr, [0],0) #insert fixed zero
        Pr = np.insert(Pr, [-1],0) #insert fixed zero

    dr = r[1]
    #Pr = Pr / 4 * pi * dr
    
    return Pr

def normalDistribution(mu, sigma, N, x_min =0, x_max=1):
    
    mu = 5
    sigma = 1.5
    bins = np.linspace(x_min,x_max,N)
    
    normdist = 1/(sigma * np.sqrt(2 * np.pi)) * np.exp( - (bins - mu)**2 / (2 * sigma**2) )
    
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
    
    # Leaving out 4 * pi * dr! That means the solution will include these three factors!
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
                      T(i,j) = 1;
                  }
                  else {
                      T(i,j) = chk; 
                  }
                      
           }
           
    """   
    weave.inline(code,['qlen', 'rlen', 'T', 'r', 'q', 'c'], type_converters = converters.blitz, compiler = "gcc")    
            
    return T

def distDistribution_Sphere(N, scale_factor, dmax):    
    ''' 
        P(r) for a sphere 
        N = distribution length 
        scale_factor = I_exp(0) (Just the first value in I_exp)
        
        "Neutrons X-rays and light scattering methods applied to soft condensed matter.", Page 84 
    '''
    R = dmax/2.
    r = np.linspace(0, dmax, N)                  # the r-axis in P(r)
       
    P = (3/(4*pi))*(power(r,2)/power(R,2)) * (2-(3/2.)*(r/R)+(power(r,3)/(8*power(R,3)))) * scale_factor
    
    return P, r

def sphereFormFactor(q, r, scale = 1, radius = 60, contrast = 1e-6, bkg = 0):
    
    V = 1
    
    F = scale / V * power( ( 3*V*contrast*(sin(q*r)-q*r*cos(q*r)) )/ power(q*r,3), 2)
    
    return F

def norm(pr):
    ''' Calculates the norm of the incomming vector '''

    norm = sqrt( sum(power(pr,2)) )
    
    return norm
    
def OSCILL(Pr, r):
    ''' If the criterion OSCILL is close to 1, P(r) is a smooth function.
    For sphere OSCILL = 1.1. OSCILL ~= 2 corresponds to a smooth bimodal
    or an oscillating monomodal '''
    
    dPr = []
    dr = r[1]
    
    for i in range(0,len(Pr)-1):
        dPr.append((Pr[i+1]-Pr[i])/dr)
      
    D_min = r[0]
    D_max = r[-1]
    
    OSC = (norm(dPr) / norm(Pr)) / (pi/(D_max-D_min))
        
    return OSC

def SYSDEV(Pr, r, I, q):
    ''' In the absence of systematic deviations in reciprocal space, the
    the value of the criterion SYSDEV must be close to 1''' 
    
    K = createTransformMatrix(q, r)
    
    dr = r[2]-r[1]
    I_Pr = np.dot( Pr, np.transpose(K)) #* 4 * pi * dr
    
    deltaI = I - I_Pr
    
    N_s = 0
    
    for c in range(0, len(deltaI)-1):
        if np.sign(deltaI[c]) != np.sign(deltaI[c+1]):
            
            bothPos1 = np.sign(deltaI[c]) == 0 and np.sign(deltaI[c+1]) == 1
            bothPos2 = np.sign(deltaI[c]) == 1 and np.sign(deltaI[c+1]) == 0
             
            if not (bothPos1 and bothPos2):
                N_s = N_s + 1
    
    N = len(I)
    
   # print N_s
    
    SYS = N_s / (N/2.)
     
    return SYS

def STABIL(Pr, r, I, q, sigma, alpha, dAlpha, dmin, dmax, N, forceInitZero = True):
    ''' According to the point-of-inflection and quasi-optimality methods (Glatter)
    a value of STABIL << 1 can be expected in the vicinity of the correct solution '''
        
    Pr_dAlpha = calcPr(2*alpha, I, q, sigma, dmin, dmax, N, forceInitZero)
    
    #Pr_dAlpha = Pr_dAlpha / (4 * pi * r[1])
    
    STA = (norm( Pr-Pr_dAlpha ) /norm(Pr)) # / (dAlpha/alpha)
    
    return STA
    
def POSITV(Pr):
    ''' In many cases it is known that p(r) should be non-negative function.
    For a non-negative function POSITIV = 1''' 
    
    Pr_plus = Pr.copy()
    
    Pr_plus[np.where(Pr_plus<0)] = 0
    
    POS = norm(Pr_plus) / norm(Pr)
    
    return POS

def VALCEN(Pr, r):
    ''' When dmax is correctly specified, the most information should be contained
     in the central part of P(r). For a solid sphere VALCEN = 0.95 ''' 
    
    Pr_star = Pr.copy()
    
    D_min = r[0]
    D_max = r[-1]
    
    dD = D_max - D_min
    
    low_limit = D_min + (dD/4.) 
    high_limit = D_max - (dD/4.)
    
    for c in range(0,len(r)):
        
        if r[c] > low_limit and r[c] < high_limit:
            pass
        else:
            Pr_star[c] = 0
            
    Pr_star_neg = Pr_star.copy()
    Pr_star_neg[np.where(Pr_star_neg>0)] = 0
    
    Pr_star_pos = Pr_star.copy()
    Pr_star_pos[np.where(Pr_star_pos<0)] = 0
        
    maxPr_star = max([norm(Pr_star_neg), norm(Pr_star_pos)])
        
    VAL = maxPr_star / norm(Pr)


    return VAL

def DISCRP(I, I_Pr, sigma, Chi):
    
    dis = sqrt(sum(np.power((np.array(I)-np.array(I_Pr)),2)/np.power(sigma,2))-Chi)
    
    print dis
    
    return dis

def CalcProbability(DISCRP, OSCILL, STABIL, SYSDEV, POSITV, VALCEN, WCA_Parameters = None):
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
            Prob.append(exp(-power((A-B)/C,2)))
            Weights.append(W)
        
    else:
        #Ugly hack to easier fit into RAW
        WCA_Param = []
        
        lst = [DISCRP, OSCILL, STABIL, SYSDEV, POSITV, VALCEN]
        
        for i in range(0,len(WCA_Parameters)):
            W = WCA_Parameters[i][0]
            C = WCA_Parameters[i][1]
            A = WCA_Parameters[i][2]
            B = lst[i]
            
            Prob.append(exp(-power((A-B)/C,2)))
            Weights.append(W)
    
    TOTAL = sum( np.array(Weights)*np.array(Prob) )/sum(Weights)
    
    return TOTAL

def costFuncChiSquared(alpha, r, I, q, sigma, dmax, N, ChiSq, WCA_Params = None, forceInitZero = True):
    
    alpha = np.exp(alpha)
    
    Pr = calcPr(alpha, I, q, sigma, 0, dmax, N, forceInitZero)
    
    K = createTransformMatrix(q, r)
    I_Pr = np.dot(Pr, np.transpose(K))
    
    ChiSquared = np.sum(np.power(I - I_Pr,2) / np.power(sigma,2))
    
    print ChiSquared
    
    return ChiSquared
    

def costFunc(alpha, r, I, q, sigma, dmax, N, ChiSq, WCA_Params = None, forceInitZero = True):
    
    alpha = np.exp(alpha)
    
    PrC = calcPr(alpha, I, q, sigma, 0, dmax, N, forceInitZero)
    
    K = createTransformMatrix(q, r)
    I_Pr = np.dot( PrC, np.transpose(K) )# * 4 * pi * r[1]
    
    TOTAL = CalcProbability(DISCRP(I, I_Pr, sigma, ChiSq),
                            OSCILL(PrC, r),
                            STABIL(PrC, r, I, q, sigma, alpha, 2*alpha, 0, dmax, N),
                            SYSDEV(PrC, r, I, q),
                            POSITV(PrC),
                            VALCEN(PrC,r), WCA_Params)
            
    return -TOTAL #negative since we want to maximize TOTAL


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

def searchAlpha(r, I_alpha, q, sigma, dmax, N, ChiSq, alphamin = 0.0001, alphamax = 100, alphapoints = 100, WCA_Params = None, forceInitZero = True, costFunction = costFunc):
    
    #alphaGuess = sum(np.power(norm(K),2)) / norm(I_alpha)
    
    #Determine TOTAL for different alpha values to determine a good starting point
    alphatotal = []
    alphavals = np.linspace(alphamin, alphamax, alphapoints)
    
    for alpha in alphavals:
        alphatotal.append(costFunction(np.log(alpha), r, I_alpha, q, sigma, dmax, N, ChiSq, WCA_Params ))
        
    alphaGuess = alphavals[ alphatotal.index(min(alphatotal)) ] 
    
    print 'GUESS : ',alphaGuess
    
    fig = pl.figure(1)
    pl.plot(np.log(alphavals), -1*np.array(alphatotal), '.')
    pl.xlabel('log(alpha)')
    pl.ylabel('TOTAL')
    
    pl.show()
    
    alpha = optimize.fmin(costFunction, np.log(alphaGuess), (r, I_alpha, q, sigma, dmax, N, ChiSq, WCA_Params))
    
    return alpha

def getGnomPr(I, q, sigma, N, dmax, dmin = 0, alphamin = 0.01, alphamax = 60, alphapoints = 100, WCA_Params = None, forceInitZero = True):
    ''' Returns the optimal Pr function according to the GNOM algorithm (GNOM calulates alpha) '''
    
    r = np.linspace(dmin, dmax, N)
    
    #Find optimal alpha:
    alpha = searchAlpha(r, I, q, sigma, dmax, N, alphamin, alphamax, alphapoints, WCA_Params, forceInitZero)
    
    K = createTransformMatrix(q, r)
    
    Pr = calcPr(alpha, I, q, sigma, dmin, dmax, N, forceInitZero)
    I_Pr = np.dot( Pr, np.transpose(K) )
    
    TOTAL = -costFunc(alpha[0], r, I, q, sigma, dmax, N, WCA_Params, forceInitZero)
    
    I0, Rg = calcRgI0(Pr, r)
    
    ChiSq = sum(np.power(np.array(I)-np.array(I_Pr),2) / np.power(sigma,2))
    
    allcrit = getAllCriteriaResults(Pr, r, I, q, sigma, alpha, dmin, dmax, N, forceInitZero)
    
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
                'gnomTOTAL' : TOTAL,
                'Rg' : Rg}
    
    return Pr, r, I_Pr, info

def singleSolveInRAW(alpha, dmax, SelectedExpObj, N, dmin = 0, forceInitZero = True, WCA_Params = None):
    ''' Solves optimal Pr for a given dmax and alpha.. this routine also calculates info needed by RAW ''' 
    
    I = SelectedExpObj.i
    q = SelectedExpObj.q
    sigma = SelectedExpObj.errorbars
    
    Pr = calcPr(alpha, I, q, sigma, dmin, dmax, N, forceInitZero)
    r = np.linspace(dmin, dmax, N)
    
    K = createTransformMatrix(q, r)
    
    Pr = calcPr(alpha, I, q, sigma, dmin, dmax, N)
    I_Pr = np.dot( Pr, np.transpose(K) )
    
    TOTAL = -costFunc(alpha, r, I, q, sigma, dmax, N, WCA_Params)
    
    I0, Rg = calcRgI0(Pr, r)
    
    ChiSq = sum(np.power(np.array(I)-np.array(I_Pr),2) / np.power(sigma,2))
    
    allcrit = getAllCriteriaResults(Pr, r, I, q, sigma, alpha, dmin, dmax, N, forceInitZero)
    
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

def getAllCriteriaResults(Pr, r, I, q, sigma, alpha, dmin, dmax, N, ChiSq, forceInitZero):
    
    val = round(VALCEN(Pr, r),4)
    osc = round(OSCILL(Pr, r),4)
    pos = round(POSITV(Pr),4)
    sysd = round(SYSDEV(Pr, r, I, q),4)
    sta = round(STABIL(Pr, r, I, q, sigma, alpha, 2*alpha, 0, dmax, N, forceInitZero),4)
    
    K = createTransformMatrix(q, r)
    I_Pr = np.dot( Pr, np.transpose(K * 4 * pi * r[1]) )
    
    dsc = round(DISCRP(I, I_Pr, sigma, ChiSq),2)
    
    allcrit = [('VALCEN', val),
               ('OSCILL', osc),
               ('POSITV' ,pos),
               ('SYSDEV', sysd),
               ('STABIL', sta),
               ('DISCRP', dsc)]
    
    return allcrit
    
def calcRgI0(Pr, r):
    
    dr = r[1]
    
    area = 0
    area2= 0
    for x in range(1, len(Pr)):                       
        area = area + dr * ((Pr[x-1]+Pr[x])/2)                   # Trapez integration
        area2 = area2 + dr * ((Pr[x-1]+Pr[x])/2) * pow(r[x], 2)  # For Rg^2 calc
        
    RgSq = area2 / (2 * area)
    Rg = sqrt(abs(RgSq))
    
    I0 = area
    
    return I0, Rg


def loadGnomFit(filename):
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


def Test_GnomPr():
    
    #S, J_EXP, ERROR, J_REG, I_REG = loadGnomFit('/home/specuser/GnomFitLyzExp.txt')
    S, J_EXP, ERROR, J_REG, I_REG = loadGnomFit('/home/specuser/diff.txt.txt')
    
    #Load Pr function
    ExpObj, FullImage = fileIO.loadFile('/home/specuser/diffpr.txt.txt')
    #ExpObj, FullImage = fileIO.loadFile('/home/specuser/GnomLyzExp.txt')
    
    Pr = ExpObj.i
    r = ExpObj.q
    Pr_sigma = ExpObj.errorbars
    
    dr = r[2]-r[1]
   
    I = J_EXP
    q = S
    I_sigma = ERROR
        
#   PrSph, r_sph = distDistribution_Sphere(len(r), 1, 45)
#    pl.figure()
#    pl.plot(r_sph, PrSph)
#    pl.show()

    crit = getAllCriteriaResults(Pr, r, I, q, ERROR, 0.601, 0, 45, len(r), forceInitZero = True)
    
    for each in crit:
        print each[0] + ' :' + str(each[1])
    
    K = createTransformMatrix(q, r)
    I_Pr = np.dot( Pr, np.transpose(K) ) * (4 * pi * dr)
    
    pl.figure()
    pl.plot(r, Pr)
    
    pl.figure()
    pl.semilogy(I)
    pl.semilogy(I_Pr,'r')
    pl.semilogy(J_REG, 'g')
    pl.show()
    

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
    
    alpha = searchAlpha(r, I, q, sigma, dmax, N, costFunction = costFuncChiSquared) 
    alpha = np.exp(alpha)
    
    print 'Optimal Alpha : ', alpha
    
    Pr = calcPr(alpha, I, q, sigma, 0, dmax, N, forceInitZero = True)
    
    pl.plot(r, Pr)
    
    pl.show()
    
def FindOptimalChiSquared(I, q, sigma, dmax, N):
    
    r = np.linspace(0, dmax, N)
    K = createTransformMatrix(q, r)
    
    alpha = searchAlpha(r, I, q, sigma, dmax, N, 0, costFunction = costFuncChiSquared) 
    alpha = np.exp(alpha)
    
    Pr = calcPr(alpha, I, q, sigma, 0, dmax, N, forceInitZero = True)
    I_Pr = np.dot(Pr, np.transpose(K))
    
    ChiSq = np.sum(np.power(I-I_Pr,2)/np.power(sigma,2))
    
    print 'Optimal Alpha : ', alpha
    print 'Optimal ChiSq : ', ChiSq
    
    return ChiSq

def Test_RunGnomOnFile(filename, dmax, N):
    
    r = np.linspace(0, dmax, N)
    K = createTransformMatrix(q, r)
    
    ChiSq = FindOptimalChiSquared(I, q, sigma, dmax, N)
        
    alpha = searchAlpha(r, I, q, sigma, dmax, N, ChiSq, costFunction = costFunc)
    dAlpha = 2*alpha
    
    alpha = np.exp(alpha)
    
    print 'Optimal Alpha: ', str(alpha)
    
    Pr = calcPr(alpha, I, q, sigma, 0, dmax, N)
    dr = r[2]-r[1]
    
    Pr = Pr / (4 *np.pi*dr)
    
    I_Pr = np.dot( Pr, np.transpose(K) * (4*np.pi*dr) ) 
    
    chi = np.sum(np.power(I-I_Pr,2)/np.power(sigma,2))
    
    print 'ChiSq: ', ChiSq 
    print 'ChiSq_Gnom : ', chi
    print calcRgI0(Pr, r)
    
    print 'TOTAL : ', str(CalcProbability(DISCRP(I, I_Pr, sigma, ChiSq), OSCILL(Pr,r), STABIL(Pr, r, I, q, sigma, alpha, dAlpha, 0, dmax, N), SYSDEV(Pr, r, I, q), POSITV(Pr), VALCEN(Pr,r)))
    
    #Print Criteria:
    crit = getAllCriteriaResults(Pr, r, I, q, sigma, alpha, 0, dmax, len(r), ChiSq, forceInitZero = True)
    
    for each in crit:
        print each[0] + ' :' + str(each[1])
        
    pl.figure()
    pl.subplot(211)
    pl.plot(r, Pr, 'red')
    pl.subplot(212)
    pl.loglog(q, I_Pr, 'red')
    pl.loglog(q, I)
    pl.show()

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
    crit = getAllCriteriaResults(Pr, r, I, q, sigma, alpha, 0, dmax, len(r), ChiSq, forceInitZero = True)
    
    for each in crit:
        print each[0] + ' :' + str(each[1])

if __name__ == '__main__':
    
    ####### CAREFUL!!! ####################################
    #SYSDEV HAS THE 4 * pi *dr on it to test the GNOM data! and Check STABILL TOO!
    ######################################################## 
    
    #testGnomPr()
    #testChiSquaredSearch()

    Test_RunGnomOnFile('lyzexp.dat', dmax = 45, N=50)
    Test_RunGnomOnFile('diff.dat', dmax = 45, N=50)
        
    
    #q, I, sigma, J_REG, I_REG = loadGnomFit('/home/specuser/diff.txt.txt')
    
    
    
    
    