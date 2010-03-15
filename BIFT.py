#******************************************************************************
# This file is part of BioXTAS RAW.
#
#    BioXTAS RAW is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    BioXTAS RAW is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with BioXTAS RAW.  If not, see <http://www.gnu.org/licenses/>.
#
#******************************************************************************

from __future__ import division
from scipy import *
from scipy import optimize
from scipy import weave
from scipy.weave import converters
from scipy.linalg import inv, det, eig
from numpy import *
#import saxsmodel
#import autoanalysis
#import random
#import matplotlib.axes3d as p3

import cartToPol
import time#, random
#import bift_ext
#import transmatrix_ext


def C_seeksol(I_exp, m, q, sigma, alpha, dmax, T):
    
 #   beg = time.time()  
    
    N = max(shape(m))

    m = matrix(m)                #m is the prior distribution
   
    P = m.copy()                        #multiply(m, 1.0005) # first guess is set equal to priror distribution
    
    m2 = m.copy()
    
    I_exp = matrix(I_exp)
        
    sigma_sq = matrix(sigma)            # std to variance
    
    # Calculate factors for the gradient:
    sum_dia = matrix(sum( multiply(T, transpose(I_exp) / transpose(sigma_sq)) , 0))    # works!  makes sum( (d_i * a_ik) / s^2_i) over i, giver f_k vektor 
    
    B = dot(transpose(T),( T / transpose(sigma_sq)))     # this one was a bitch!  this is b_kj 
   
    Bdiag = matrix(multiply(B,eye(len(B))))              # The diagonal of B
    
    bkk = sum(Bdiag, 0)                                  # k col-vektor
    
    Bmat = B-Bdiag
    


    
    # ************  convert before C++  *************************
    Psumi = zeros((1,N))                   ## all should be arrays!         NB matrix and array dont mix in weave C!!!!
    sum_dia = array(sum_dia,'float64')
    bkk = array(bkk)
    dP = array(zeros((1,N)), 'float64')
    #m = array(m, 'float64')
    #m = zeros((1,N))
    m = array(m, 'float64')            # important! otherwise C will only make an Int array, and kill floats!
    
    Pold = array(zeros((1,N)),'float64')
    
    I_exp = array(I_exp,'float64')
    Bmat = array(Bmat,'float64')
    B = array(B,'float64')
    
    omegareduction = 2.0
    omega = 0.5
    minit = 10
    maxit = 1000
    dotsptol = 0.001
    omegamin = 0.001
    
    bkkmax = bkk.max() * 10
    
    P = array(P,'float64')            # important! otherwise C will only make an Int array, and kill floats!
    
    dotsp = 0.0
    
    alpha = float(alpha)              # Important! otherwise C code will crash
    
#    s = bift_ext.bift(dotsp, dotsptol, maxit, minit, bkkmax, omega, omegamin, omegareduction, B, N, m, P, Psumi, Bmat, alpha, sum_dia, bkk, dP, Pold)
    
    # ********************** C++ CODE *******************************

#    mod = ext_tools.ext_module('bift_ext')
    
    code = """
    #include <iostream.h>
    #include <math.h>
  
    py::object sout;
    
    // Initiate Variables
    int ite = 0;
  
    double s = 0,
          wgrads = 0,
          wgradc = 0,
          gradci = 0,
          gradsi = 0;

    while( ite < maxit && omega > omegamin && fabs(1-dotsp) > dotsptol || (ite < minit) )
    {
            if (ite != 0)
            {
                /* Calculating smoothness constraint vector m */
            
                for(int k = 1; k < N-1; k++)
                {
                     m(0, k) =  ((P(0,k-1) + P(0,k+1)) / 2.0);
                }
                
                m(0,0) =  P(0,1) / 2.0;
                m(0,N-1) =  P(0,N-2) /2.0;
                
   
                /* This calculates the Matrix Psumi */
                
                for(int j = 0; j < N; j++)
                    for(int k = 0; k < N; k++)
                        Psumi(0,j) = Psumi(0,j) + P(0,k) * Bmat(k,j);
    
               // cout << "    " << Psumi(0,50);
    
               /* Now calculating dP, and updating P */
        
                for(int k = 0; k < N; k++)
                {        
                    dP(0,k) = ( m(0,k) * alpha + sum_dia(0,k) - Psumi(0,k) ) / (bkk(0,k) + alpha);      /* ATTENTION! remember C division!, if its all int's then it will be a int result! .. maybe cast it to float()? */
                    
                    Psumi(0,k) = 0;    // Reset values in Psumi for next iteration..otherwise Psumi = Psumi + blah will be wrong!
        
                    Pold(0,k) = P(0,k);
         
                    P(0,k) = (1-omega) * P(0,k) + omega * dP(0,k);
                    
                    /* Pin first and last point to zero! */
    
                    //P(0,0) = 0.0;
                    //P(0,N-1) = 0.0;
                }    
      
                //cout << "    " << m(0,50);
                //cout << "    " << P(0,50);
                //cout << "    " << dP(0,50);
                //cout << " | ";
        
            } // end if ite != 0
        
      
 
       ite = ite + 1;
    
       /* Calculating Dotsp */
      
       dotsp = 0;
       wgrads = 0;
       wgradc = 0;
       s = 0;
       for(int k = 0; k < N; k++)
       {
             s = s - pow( P(0,k) - m(0,k) , 2);                        // sum(-power((P-m),2))
             
             gradsi = -2*( P(0,k) - m(0,k) );                            // gradsi = (-2*(P-m))
             wgrads = wgrads + pow(gradsi, 2);
       
             gradci = 0;
             for(int j = 0; j < N; j++)
             {
                 gradci = gradci + 2*( P(0,j) * B(j,k) );     
             }
             gradci = gradci - 2*sum_dia(0,k);
            
             wgradc = wgradc + pow(gradci , 2);
             dotsp = dotsp + (gradci * gradsi);
       }
      
//      cout << dotsp;
//      cout << "    " << wgrads;
//      cout << "    " << wgradc;
//      cout << "    " << s;
//      cout << " | ";
  
  
       /* internal loop to reduce search step (omega) when it's too large */
         
       while( dotsp < 0 && double(alpha) < double(bkkmax) && ite > 1 && omega > omegamin)
       {
                omega = omega / omegareduction;
                
                /* Updating P */
                 
                for(int k = 0; k < N; k++)
                {
                    P(0,k) = (1-omega) * Pold(0,k) + omega * dP(0,k);
                }
                
                /* Calculating Dotsp */
                
                dotsp = 0;
                wgrads = 0;
                wgradc = 0;
                s = 0;
                for(int k = 0; k < N; k++)
                {
                    s = s - pow( P(0,k)-m(0,k) , 2);                        // sum(-power((P-m),2))     
                    gradsi = -2*(P(0,k)-m(0,k));                            // gradsi = (-2*(P-m))
                    wgrads = wgrads + pow(gradsi, 2);
            
                    gradci = 0;
                    for(int j = 0; j < N; j++)
                    {
                        gradci = gradci + 2*( P(0,j) * B(j,k));     
                    }
                    gradci = gradci - 2*sum_dia(0,k);
                      
                    wgradc = wgradc + pow(gradci , 2);
                    dotsp = dotsp + (gradci * gradsi);
                }    
                
       } // end inner whileloop
     
        
       if(wgrads == 0 || wgradc == 0)
       {
            dotsp = 1;
       }
       else
       {
            wgrads = std::sqrt(wgrads);
            wgradc = std::sqrt(wgradc);
            dotsp = dotsp / (wgrads * wgradc);
       }
     
          
    } // end Outer while loop
    
    
    // cout << "ite C: " << ite;
    // cout << "alpha: " << double(alpha);
    // cout << "omega: " << omega;
    //cout << ",   m: " << m(0,20);
    //cout << ",   dotsp C: " << dotsp;
    //cout << ",   dP:" << dP(0,20);
    //cout << "cnt:" << cnt;
    //cout << ",   wgrads C: " << wgrads;
    //cout << ",   wgradc C: " << wgradc;
    
    
    //tst(0,1) = wgradc;
    sout = s;
    return_val = sout;
    """

    s = weave.inline(code,['dotsp', 'dotsptol', 'maxit', 'minit', 'bkkmax', 'omega', 'omegamin', 'omegareduction', 'B', 'N', 'm', 'P', 'Psumi', 'Bmat', 'alpha', 'sum_dia', 'bkk', 'dP', 'Pold'], type_converters = converters.blitz, compiler = "gcc")
    # ***************************************************************
    
    #biftext = ext_tools.ext_function('bift', code, ['dotsp', 'dotsptol', 'maxit', 'minit', 'bkkmax', 'omega', 'omegamin', 'omegareduction', 'B', 'N', 'm', 'P', 'Psumi', 'Bmat', 'alpha', 'sum_dia', 'bkk', 'dP', 'Pold'], type_converters = converters.blitz)   
    #mod.add_function(biftext)
    #mod.compile(compiler = 'gcc')

    
    #Forcing negative values to zero:
    #P[nonzero(P<0)] = 0

    I_m = dot( P, transpose(T) )

    difftst = power( (I_exp[0] - I_m[0]), 2) / power(sigma, 2)
    
    #Chi Squared:
    c = sum( array(difftst) )
    
    post = calcPosterior( alpha, dmax, s, c, B )
    
    return P, post, c


def GetEvidence(alpha, dmax, Ep, N):
    
    alpha = exp(alpha)    # alpha is log(alpha)!!! to improve search
    
    r = linspace(0, dmax, N)
    T = createTransMatrix(Ep.q, r)
    P = makePriorDistDistribution(Ep, N, dmax, T, 'sphere', Ep.q)
    
    print 'Alpha : ' ,alpha
    print 'Dmax  : ' , dmax
    
    Pout, evd, c  = C_seeksol(Ep.i, P, Ep.q, Ep.errorbars, alpha, dmax, T)
        
    return -evd, c, Pout

def SingleSolve(alpha, dmax, Ep, N):
    ''' Fit to data with forced Dmax and Alpha values '''
    
    alphafin = alpha
    dmaxfin = dmax
    
    r = linspace(0, dmaxfin, N)
    T = createTransMatrix(Ep.q, r)
    P = makePriorDistDistribution(Ep, N, dmaxfin, T, 'sphere', Ep.q)
    
    Pr, post, c = C_seeksol(Ep.i, P, Ep.q, Ep.errorbars, alphafin, dmaxfin, T)

    # Reconstructed Fit line
    Fit = dot(Pr, transpose(T))
    
    #Create the r vector
    r = linspace(0, dmaxfin, len(transpose(Pr))+2)  # + 2 since we add a zero in each end
    dr = r[2]-r[1]

    # Insert 0 in the beginning and the end (Pinning the result to Zero!)
    Pr = transpose(Pr)
    Pr = list(Pr)
        
    #Pr = Pr[0]
    Pr.insert(0,0)
    Pr.append(0)
    
    #Calc I0 and Rg:
    area = 0
    area2 = 0
    area3 = 0
    
    for x in range(1, len(Pr)):                        # watch out! Pr = Pr * dr !!
        #area = area + dr * Pr[x]    
        area = area + dr * ((Pr[x-1]+Pr[x])/2)                   # Trapez integration
        area2 = area2 + dr * ((Pr[x-1]+Pr[x])/2) * pow(r[x], 2)  # For Rg^2 calc
    
    area = area / dr         # watch out! Pr = Pr 4 * pi * dr !!
    area2 = area2 / dr
        
    RgSq = area2 / (2 * area)
    
    Rg = sqrt(abs(RgSq))[0]
    
    print 'Rg : ', Rg
    print 'dr : ', dr
    print 'Area2 : ', area2
    
    I0 = mean(Fit[0, 0:5])
    print Fit[0, 0:5]
    print 'I(0) from avg of 5 first points :', I0
    print 'I(0) from area under P(r) : ', area
    
    I0 = area
    
    Pr = array(Pr)
    
    Pr = Pr / (4*pi*dr)   # Since what we got from the optimization is 4*pi*dr * p(r) 
                          #(we excluded 4*pi*dr in the trans matrix!)
    
    #Pr = Pr[0]  ## ..need this if we dont add zeros
    
    Pr = transpose(Pr)
    
    #alphafin = exp(alphafin)
    
    # Save all information from the search
    plotinfo = {'alpha' : alphafin,
                'dmax' : dmaxfin,
                'orig_i' : Ep.i,
                'orig_q' : Ep.q,
                'orig_err': Ep.errorbars,
                'I0' : I0,
                'ChiSquared' : c,
                'Rg' : Rg,
                'post':post}
        
    ExpObj = cartToPol.BIFTMeasurement(transpose(Pr), r, ones((len(transpose(Pr)),1)), Ep.param, Fit, plotinfo)

    return ExpObj
    

def fineGetEvidence(data, Ep, N):
    
    alpha = data[0]
    dmax = data[1]
    
    alpha = exp(alpha)
    
    r = linspace(0, dmax, N)
    T = createTransMatrix(Ep.q, r)
    P = makePriorDistDistribution(Ep, N, dmax, T, 'sphere', Ep.q)
    print alpha
    print dmax
    
    Pout, evd, c  = C_seeksol(Ep.i, P, Ep.q, Ep.errorbars, alpha, dmax, T)
        
    return -evd


def doBift(Exp, N, alphamax, alphamin, alphaN, maxDmax, minDmax, dmaxN):
    '''
        Runs the BIFT algorithm on an Experiment Object or a filename
        
        N = Number of points in the P(r) function
        DmaxUbound = Upper bound for Dmax
        DmaxLbound = Lower bound for Dmax
        
        AlphaUbound = Upper bound of Alpha
        AlphaLbound = Lower bound of Alpha
    '''
    Ep = Exp
    

    # NB!!! ALPHA MUST BE DECIMAL NUMBER OTHERWISE C CODE WILL CRASH!!!!!!!
    
    # alpha/dmax points to cycle though:
    
    alphamin = log(alphamin)
    alphamax = log(alphamax)
    
    alpha_points = linspace(alphamin, alphamax, alphaN)          # alpha points are log(alpha) for better search
    dmax_points = linspace(minDmax, maxDmax, dmaxN)
    #dmax_points = array(range(minDmax, maxDmax, dmaxN))
    
    # Set inital error to infinity:
    finalpost = 1e20            
    bestc = 1e22
    
    beg = time.time()  
    
    # Cycle though dmax/alpha points and find best posterior / evidence
    all_posteriors = zeros((len(dmax_points), len(alpha_points)))
    dmax_idx = 0
       
    for each_dmax in dmax_points:
        
        alpha_idx = 0
        for each_alpha in alpha_points:      
                    
            post, c, result = GetEvidence(each_alpha, each_dmax, Ep, N)
            
            if c == '1.#QNAN':
                print 'ERROR !! GOT #QNAN!'

            print ''
            print "alphaC =", exp(each_alpha)
            print "evdC =", post
            print "C = ", str(c)
            print "Dmax =", each_dmax
    
            if post < finalpost:
                finalpost = post
                
                alphafin = exp(each_alpha)
                dmaxfin = each_dmax
                best_result = result
                
            if c < bestc:
                bestc = c
                alphac = exp(each_alpha)
                dmaxc = each_dmax
           
            all_posteriors[dmax_idx, alpha_idx] = post  
            alpha_idx = alpha_idx + 1
        
        dmax_idx = dmax_idx + 1
    
    print "final alpha: ", alphafin      
    print "final dmax: ", dmaxfin
    print "c_alpha: ", alphac
    print "c_dmax: ", dmaxc
    
    end = time.time()
    dt = end - beg
    print 'Search took %9.6f Seconds' % dt 
    
    print "Making fine search..."
    alphafin, dmaxfin = fineSearch(Ep, N, log(alphafin), dmaxfin)

    ###########################################
    # Pr = P(r) function, Fit = Fitted curve
    ###########################################

    r = linspace(0, dmaxfin, N)
    T = createTransMatrix(Ep.q, r)
    P = makePriorDistDistribution(Ep, N, dmaxfin, T, 'sphere', Ep.q)
    
    Pr, post, c = C_seeksol(Ep.i, P, Ep.q, Ep.errorbars, alphafin, dmaxfin, T)

    # Reconstructed Fit line
    Fit = dot(Pr, transpose(T))
    
    #Create the r vector
    r = linspace(0, dmaxfin, len(transpose(Pr))+2)  # + 2 since we add a zero in each end
    dr = r[2]-r[1]

    # Insert 0 in the beginning and the end (Pinning the result to Zero!)
    Pr = transpose(Pr)
    Pr = list(Pr)
        
    #Pr = Pr[0]
    Pr.insert(0,0)
    Pr.append(0)
    
    #Normalize P(r) funcion so that the area is equal to I0
    area = 0
    area2 = 0
    area3 = 0
    
    for x in range(1, len(Pr)):                        # watch out! Pr = Pr * dr !!
        #area = area + dr * Pr[x]    
        area = area + dr * ((Pr[x-1]+Pr[x])/2)                   # Trapez integration
        area2 = area2 + dr * ((Pr[x-1]+Pr[x])/2) * pow(r[x], 2)  # For Rg^2 calc
    
    area = area / dr   # watch out! Pr = Pr 4 * pi * dr !!
    area2 = area2 / dr
        
    RgSq = area2 / (2 * area)
    
    Rg = sqrt(abs(RgSq))[0]
    
    print 'Rg : ', Rg
    print 'dr : ', dr
    print 'Area2 : ', area2
    
    I0 = mean(Fit[0, 0:5])
    print Fit[0, 0:5]
    print 'I(0) from avg of 5 first points :', I0
    print 'I(0) from area under P(r) : ', area
    
    I0 = area
    
    Pr = array(Pr)    # Since what we got from the optimization is 4*pi*dr * p(r) 
                      #(we excluded 4*pi*dr in the trans matrix!)
    
    Pr = Pr / (4*pi*dr)
    
    Pr = transpose(Pr)
    
    # Save all information from the search
    plotinfo = {'dmax_points' : dmax_points,
                'alpha_points' : alpha_points,
                'all_posteriors' : all_posteriors,
                'alpha' : alphafin,
                'dmax' : dmaxfin,
                'orig_i' : Ep.i,
                'orig_q' : Ep.q,
                'orig_err': Ep.errorbars,
                'I0' : I0,
                'ChiSquared' : c,
                'Rg' : Rg}
    
    ExpObj = cartToPol.BIFTMeasurement(transpose(Pr), r, ones((len(transpose(Pr)),1)), Ep.param, Fit, plotinfo)

    #return Out, Pout, r, Ep.i, plotinfo
    return ExpObj

def pinnedFineSearch(Ep, N, alpha, dmax):
    
    arg = (Ep, N)
    
    opt = optimize.fmin(fineGetEvidence, [alpha, dmax], args = arg)
    
    print "Optimum found: "
    print exp(opt[0]), opt[1]

    return exp(opt[0]), opt[1]

def fineSearch(Ep, N, alpha, dmax):
    
    arg = (Ep, N)
    
    opt = optimize.fmin(fineGetEvidence, [alpha, dmax], args = arg)
    
    print "Optimum found: "
    print exp(opt[0]), opt[1]

    return exp(opt[0]), opt[1]

def distDistribution_Sphere(N, scale_factor, dmax):    
    ''' 
        P(r) for a sphere 
    
        N = distribution length 
        scale_factor = I_exp(0) (Just the first value in I_exp)
    '''
    
    R_axis_vector = linspace(0, dmax, N)                  # the r-axis in P(r)
    delta_R = R_axis_vector[1]                            # stepsize in R
    
    pmin = 0.005
    
    psum = pow(dmax, 3)/24                                  # meget mystisk ?? 
    
    strange_norm_factor = scale_factor / psum * delta_R     # Some kind of norm factor
    
    # Calculate P(r) for sphere
    P = pow(R_axis_vector,2) * (1-1.5 * (R_axis_vector/dmax) + 0.5 * pow( (R_axis_vector/dmax), 3)) * strange_norm_factor

#    M(J)=                        (1-1.5 *        (R/D)         +  .5 *             (R/D)**3)
#    
#    DO 20 J=1,NTOT
#      R=DR*j
#      IF(R.GT.D) THEN
#      M(J)=0.
#      GOTO 20
#      ENDIF
#      M(J)=(1-1.5*(R/D)+.5*(R/D)**3)
#   20 CONTINUE
#      RETURN
#      END

#===============================================================================
#     The following makes sure that the values below pmin are not zero???
#===============================================================================

    av = pmin * max(P)                    
    #M = M * (R<=dmax)
    sum1 = sum(P)
    avm = pmin * max(P)    
    P = P * (P > avm) + avm * (P <= avm)
    sum2 = sum(P)
    P = P * sum1/sum2
    
    #R_axis_vector[0] = 1e-20        # To avoid divide by zero errors in convertPrToI()
 #   P = ones(N)
    return P, R_axis_vector

def shiftLeft(a,shift):
    ''' makes a left circular shift of array '''
    sh = shape(a)
    array_length = sh[0] * sh[1]
    
    b = a.reshape(1, array_length)
    
    res = zeros(array_length)
    
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
    
    sh = shape(a)
    array_length = sh[0] * sh[1]
    
    b = a.reshape(1,array_length)
    
    res = zeros(array_length)
    
    start_idx = shift

    # SLOW! lets make it in C!
    for i in range(0,array_length):
        
        res[i] = b[0, i - shift]
    
    return res.reshape(sh)           

def sphereForm(R, N, qmax):
    
    q = linspace(0.01, qmax, N)
    
    qR = q*R
    
    I = (4/3) * pi * pow(R, 3) * ( (3* ( sin(qR) - qR * cos(qR))) / pow(qR,3))
    
    return pow(abs(I),2), q
        
def createTransMatrix(q, r):
    ''' Creates the Transformation Matrix T   I_m = sum( T[i,j] * p[j] + e )'''
    
    #Reserve memory
    T = zeros((len(q), len(r)))
    
    qlen = len(q)
    rlen = len(r)
    
    q = array(q)
    r = array(r)
    
    #Stepsize in r
    dr = r[1]
    
    # Leaving out 4 * pi * dr! That means the solution will include these three factors!
    c = 1 # 4 * pi * dr   
   #================================================
   #                C++ CODE
   #================================================
 #   transmatrix_ext.trans_matrix(qlen, rlen, T, r, q, c)
    
#    mod = ext_tools.ext_module('transmatrix_ext')
#   
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

#    transext = ext_tools.ext_function('trans_matrix', code, ['qlen', 'rlen', 'T', 'r', 'q', 'c'], type_converters = converters.blitz)   
#    mod.add_function(transext)
#    mod.compile(compiler = 'gcc')
            
    return T

def makePriorDistDistribution(E, N, dmax, T, type = 'sphere', q = None):

    if isinstance(E, cartToPol.Measurement):
        scale_factor = E.i[0]
    else:
        scale_factor = E.i[0]
    
    priorTypes = {'sphere' : distDistribution_Sphere}
    
    P, R = priorTypes.get(type, distDistribution_Sphere)(N, scale_factor, dmax)     # A python switch, default is distDistribution_Sphere(). return is P(R) R is nm
    
    return P

def calcPosterior(alpha, dmax, s, Chi, B):
    '''
        ---------------------------------
        | Q = alpha * s - (1/2) * Chi^2 |
        ---------------------------------
    
        s = constraint = sum(f-m)^2
        c = sum((y-fm).^2./ sd.^2 = Chi^2    hvorfor mean?? naar han alligevel ganger med mtot naar "evidencen" skal udregnes, brug SUM!
        
        NB! the A matrix is NOT the transition matrix.. it's the hessian of the constraint.. which is described
        in the article, but it's wrong in the article!.. it still works..  since its a constant for constant N!
    
        We use A and B to denote the hessians, since this is what is used in the article
        
        B = Hessian of Chi^2 / 2
        A = Hessian of s
                
    '''
    
    # signmat = 2 * (-ones(shape(B)) + 2*eye(max(shape(B))))         # A matrix of twos with positive sign in the diagonal and neg sign otherwise
    # B = B * signmat                                                # B * signmat = the hessian of Chi^2
    # setting the correct signs on B is the correct way! .. but it gives a negative determinant!! .. which leads to rubbish when doing
    # log(detAB) ... i.e. - Infinity... Is there another way around? 


    #* ******************************************************************************
    #* Create A matrix from description in article (It's wrong! its not a diagonal matrix with -1/2 on the sides!
    #* But it's a constant for constant N! .. seems pretty stupid to include it then.. but for constant
    #* N the posterior is really only Q! = chi + s! ... since P(a) = 1/alpha = constant!
    
    sizeA = max(shape(B))
    
    eyeMat = eye(sizeA)
    mat1 = shiftLeft(eyeMat,1)
    mat2 = shiftRight(eyeMat, 1)
    
    mat2[0,0] = 0                 #Remove the 1 in the wrong place (in the corner)
    sh = shape(mat1)
    mat1[sh[0]-1, sh[1]-1] = 0    #Remove the 1 in the wrong place (in the corner)

    A = (mat1 + mat2) * -0.5 + eye(shape(mat1)[0])
    #* ****************************************************************************** *#
    
    detAB = det(B / alpha + A)

    N = max(shape(B))
    
    logdetA = log(N+1) - log(2) * N
    
    alphaPrior = 1/alpha                                       # a uniform prior P(alpha)
    
    Q = alpha * s - 0.5 * Chi
    
    Evidence = 0.5 * logdetA + Q - 0.5 * log(detAB) - log(alphaPrior)         #- log(dmaxPrior)
    
    return Evidence
    
    
#% s regulariseringsconstraint 
#% alpha*s vaegtning af reg
#% c reduc chi
#% mtot antallet af datapkt

#% krumning -- ng
#% evidensen bestaar af 4 bidrag:
#% rnorm.                en normaliseringsfaktor
#% (alpha*s-0.5*c*mtot): chi kvadratet korrigeret med regulariseringen
#% -0.5*rlogdet :        krumning af max i evidensen - giver antallet af
#%                       store egenvaeerdier i B = Ng
#% -log(alpha):          a priori sandsynligheden for at faa alpha naar vi
#%                       ikke ved noget om hvad alpha skal vaere - obs for
#%                       Dmax ved vi at den skal ligge mellem 10 og 1000 A,
#%                       saa den har en konstant sandsynlighed, derfor
#%                       bidrager den ikke til evidensen.
  
    
def MonteCarloErrorbars(BiftObj, iterations, std_dmax, std_alpha):
    
    dmax_mean = 206.81
    alpha_mean = 642214.43
    
    posteriors = zeros(iterations)
    I0 = zeros(iterations)
    Rg = zeros(iterations)
    
    for i in range(0, iterations):
        
        random_dmax = random.gauss(dmax_mean, std_dmax)
        random_alpha = random.gauss(alpha_mean, std_alpha)
        
        ExpObj = SingleSolve(random_alpha, random_dmax, BiftObj, 50)
        
        posteriors[i] = ExpObj.allData['post']
        I0[i] = ExpObj.allData['I0']
        Rg[i] = ExpObj.allData['Rg']
        
    
    print std(I0)
    print std(Rg)
    
    
class test:
    
    def __init__(self, q, I, err):
        self.q = q
        self.i = I
        self.errorbars = err
        self.param = {}
    
    
#**************************************************************************
# TESTING: 
#**************************************************************************
if __name__ == "__main__":
    import fileIO
    import pylab as p
  
    #********************* TEST distDistribution_Sphere ********************
    N = 50
    scale_factor = 1
    dmax = 200
    P, R = distDistribution_Sphere(N, scale_factor, dmax)
    
    I, Q = sphereForm(60, 50, 0.2)
    
    p.figure(4)
    p.plot(R,P)
    p.title('Starting guess for P(r)')
    
    #***********************************************************************
    
    tst = fileIO.loadRadFile('BSUB_012_bsa_16mg.rad')

    #                Radius, N, Qmax (Dmax = 2*Radius)
    #I, q = sphereForm(60, 400, 0.2)
    
    #Rg for sphere should be:
    #Rg = sqrt(3/5) * 60 # sqrt(3/5) * d_max/2
    #err = ones(len(I)) * I[0] * 0.001
    
    # Create ExpObject: (doBift only takes experiment objects)
    #tst = test(q, I, err)    
    #MonteCarloErrorbars(tst, 500, 100, 10000)
    
    E = doBift(tst, 50, 1e10, 10.0, 16, 400, 10, 20)
    print '****************************'
    print ''

    #r = linspace(0, 60, 50)
    #T = autoanalysis.createTransMatrix(tst.q, r)
    #P1 = autoanalysis.makePriorDistDistribution(tst, 50, 60, T, type = 'sphere', q = None)
    #I_m = dot( P1, transpose(T))
    
    ei = E.allData['orig_i']
    eq = E.allData['orig_q']
    
    post = E.allData['all_posteriors']
    
    alpha = E.allData['dmax_points']
    dmax = E.allData['alpha_points']
    
    p.rc('image', origin = 'lower')
    p.figure(1)
    
    a = p.imshow(log(post), interpolation = 'nearest')
    p.colorbar()
    p.axis('equal')
    
    p.figure(2)    
    p.plot(E.q, E.i)

    p.figure(3)
    p.loglog(eq, ei)
    p.loglog(eq, E.fit[0])

    
    #X, Y = meshgrid(exp(plotinfo[1]), plotinfo[0])
    #ax.plot_wireframe(X,Y, 1/plotinfo[2])
    #ax.set_xlabel('alpha')
    #ax.set_ylabel('dmax')
    #ax.set_zlabel('1 / posterior')

    p.show()
        
