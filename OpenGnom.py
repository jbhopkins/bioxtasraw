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
from LinearAlgebra import inverse

def diff(Pr, r):
    
    dPr = []
    dr = r[1]
    
    for i in range(0,len(Pr)-1):
        dPr.append((Pr[i+1]-Pr[i])/dr)
        
    return dPr

def constraint(Pr, r):
        
    Omega = sqrt(sum(power(diff(Pr, r),2)))
    
    return Omega

def chiSquared(Pr, r, I, q, sigma, K):
    
    I_alpha = np.dot( Pr, np.transpose(K))
    
    N = len(q)
    chiSquare = sqrt( (1/(N-1)) * sum( power(I - I_alpha,2)/power(sigma,2) ) )
    
    return chiSquare     

def calcPr(alpha, I, q, dmin, dmax, N):
    
    r = np.linspace(dmin, dmax, N)
    
    K = createTransformMatrix(q, r)
    
    Pr = np.dot(linalg.inv((alpha * np.eye(N)) + np.dot(np.transpose(K),K)) , np.dot(np.transpose(K), I))
       
    return Pr


def lossFunc(Pr, r, I, q, sigma, K, alpha):
    
    return chiSquared(Pr, r, I, q, sigma, K) + alpha*constraint(Pr,r)

def normalDistribution(mu, sigma, N, x_min =0, x_max=1):
    
    mu = 5
    sigma = 1.5
    bins = np.linspace(x_min,x_max,N)
    
    normdist = 1/(sigma * np.sqrt(2 * np.pi)) * np.exp( - (bins - mu)**2 / (2 * sigma**2) )
    
    return normdist, bins

def createTransformMatrix(q, r):
    ''' Creates the Transformation Matrix T   I_m = sum( T[i,j] * p[j] + e )'''
    
    #Reserve memory
    T = np.zeros((len(q), len(r)))
    
    qlen = len(q)
    rlen = len(r)
    
    q = np.array(q)
    r = np.array(r)
    
    #Stepsize in r
    dr = r[1]
    
    # Leaving out 4 * pi * dr! That means the solution will include these three factors!
    c = 1 # 4 * pi * dr   
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
       
    P = (3/(4*pi))*(power(r,2)/power(R,2)) * (2-(3/2.)*(r/R)+(power(r,3)/(8*power(R,3))))
    
    return P, r

def sphereFormFactor(q, r, scale = 1, radius = 60, contrast = 1e-6, bkg = 0):
    
    V = 1
    
    F = scale / V * power( ( 3*V*contrast*(sin(q*r)-q*r*cos(q*r)) )/ power(q*r,3), 2)
    
    return F

def norm(pr):

    norm = sqrt( sum(power(pr,2)) )
    
    return norm
    
def OSCILL(Pr, r):
    ''' If the criterion OSCILL is close to 1, P(r) is a smooth function.
    For sphere OSCILL = 1.1. OSCILL ~= 2 corresponds to a smooth bimodal
    or an oscillating monomodal '''
    
    #dPr = np.diff(Pr, 1, 0)
    dPr = []
    dr = r[1]
    
    #print dr
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
    
    I_alpha = np.dot( Pr, np.transpose(K))
    
    deltaI = I - I_alpha
    
    N_s = 0
    for c in range(0, len(deltaI)-1):
        if np.sign(deltaI[c]) != np.sign(deltaI[c+1]):
            
            bothPos1 = np.sign(deltaI[c]) == 0 and np.sign(deltaI[c+1]) == 1
            bothPos2 = np.sign(deltaI[c]) == 1 and np.sign(deltaI[c+1]) == 0
             
            if not (bothPos1 and bothPos2):
                N_s = N_s + 1
    
    N = len(I)
    
    SYS = N_s / (N/2.)
     
    return SYS

def STABIL(Pr, r, I, q, alpha, dAlpha, dmin, dmax, N):
    ''' According to the point-of-inflection and quasi-optimality methods (Glatter)
    a value of STABIL << 1 can be expected in the vicinity of the correct solution '''
        
    Pr_dAlpha = calcPr(alpha, I, q, dmin, dmax, N)
    
    STA = (norm( Pr-Pr_dAlpha ) /norm(Pr)) / (dAlpha/alpha)
    
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

def DISCRP():
    
    return 1.0

def CalcProbability(DISCRP, OSCILL, STABIL, SYSDEV, POSITV, VALCEN):
    ''' WARNING TAKING OUT DISCRP BY SETTING W = 0 '''
                        # DISCRP, OSCILL, STABIL, SYSDEV, POSITV, VALCEN
    WCA_Parameters = [(DISCRP, 0.0, 0.3, 0.7), (OSCILL, 3.0, 0.6, 1.1), (STABIL, .0, 0.12, 0.0),
                      (SYSDEV, 3.0, 0.12, 1.0), (POSITV, 1.0, 0.12, 1.0), (VALCEN, 1.0, 0.12, 0.95)]
                    #   B,   W,    C,   A
                    #Values taken from "Determination of the regularization parameter
                    #in indirect-transformmethods using perceptual criteria, Svergun (1992)"     
    Prob = []
    Weights = []
    
    for B, W, C, A in WCA_Parameters:
                
        Prob.append(exp(-power((A-B)/C,2)))
        Weights.append(W)
    
    TOTAL = sum( np.array(Weights)*np.array(Prob) )/sum(Weights)
    
    return TOTAL


def searchfunc(alpha, r, I_alpha, q, dmax, N):
    
    PrC = calcPr(alpha, I_alpha, q, 0, dmax, N)
    
    TOTAL = CalcProbability(DISCRP(),
                            OSCILL(PrC, r),
                            STABIL(PrC, r, I_alpha, q, alpha, 2*alpha, 0, dmax, N),
                            SYSDEV(Pr, r, I_alpha, q),
                            POSITV(Pr),
                            VALCEN(Pr,r))
            
    return -TOTAL

def searchAlpha(r, I_alpha, q, dmax, N):
    
    alpha = 60
    
    Pr = optimize.fmin_powell(searchfunc, alpha, (r, I_alpha, q, dmax, N))
    
    return Pr
    
if __name__ == '__main__':
    
    #FIGURES IN THE ARTCILE:
    #normdist = (np.cos(2*pi*1*bins)+1)/2                  #F
    #normdist = np.sin(2*pi*1.5*bins)                      #E
    #normdist = np.sin(2*pi*.5*bins)                       #A
    #normdist = np.sin(2*pi*6*bins) * np.sin(2*pi*.5*bins) #D
           
#    print 'Valcen: ', str(round(VALCEN(Pr, r),2))
#    print 'Oscill: ', str(round(OSCILL(Pr, r),2))
#    print 'Positv: ', str(round(POSITV(Pr),2))

#    tst = sphereFormFactor(q, 30)

    #Simulate P(r) for a sphere:
    Pr, r = distDistribution_Sphere(50, 1, 60)
    
    q = np.linspace(0.005, 0.35, 250)
    
    #Transform simulated 
    K = createTransformMatrix(q, r)
    I_alpha = np.dot( Pr, np.transpose(K) )
        
    alpha = 1000
    dmax = 60
    
    dAlpha = 2*alpha
    
    N = 50
    
    alpha = searchAlpha(r, I_alpha, q, dmax, N)
    print 'ALPHA: ', str(alpha)
    PrC = calcPr(alpha, I_alpha, q, 0, dmax, N)
    I_PrC = np.dot( PrC, np.transpose(K) )
    
    print 'TOTAL : ', str(CalcProbability(DISCRP(), OSCILL(PrC,r), STABIL(PrC, r, I_alpha, q, alpha, dAlpha, 0, dmax, N), SYSDEV(PrC, r, I_alpha, q), POSITV(PrC), VALCEN(PrC,r)))
    
    print 'Valcen: ', str(round(VALCEN(PrC, r),2))
    print 'Oscill: ', str(round(OSCILL(PrC, r),2))
    print 'Positv: ', str(round(POSITV(PrC),2))
    print 'Sysdev: ', str(round(SYSDEV(PrC, r, I_alpha, q),2))
    print 'Stabil: ', str(round(STABIL(PrC, r, I_alpha, q, alpha, dAlpha, 0, dmax, N)))
    
    pl.figure()
    pl.subplot(211)
    pl.plot(r, PrC, 'red')
    pl.plot(r, Pr)
    pl.subplot(212)
    pl.loglog(q, I_PrC, 'red')
    pl.loglog(q, I_alpha)
    
#    pl.figure()
#    pl.subplot(311)
#    pl.loglog(q, I_alpha)
#    pl.subplot(312)
#    pl.plot(r, Pr)
#    pl.subplot(313)
#    pl.loglog(q, tst)
    
    pl.show()
    
    
    
    