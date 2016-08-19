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
from scipy.linalg import inv, det, eig
from numpy import *
import numpy
import RAWGlobals
#import saxsmodel
#import autoanalysis
#import random
#import matplotlib.axes3d as p3

import time, Queue, wx, os#, random
# import bift_ext, transmatrix_ext, SASM
import SASM

if not RAWGlobals.frozen:
    from scipy import weave
    from scipy.weave import converters

if RAWGlobals.compiled_extensions:
    try:
        import bift_ext

    except ImportError:
        import SASbuild_Clibs
        try:
            SASbuild_Clibs.buildAll()
            import bift_ext

        except Exception, e:
            print e
            RAWGlobals.compiled_extensions = False

#################################################################################
################# Taken from numpy to add cancel function #######################
#################################################################################
def wrap_function(function, args):
    ncalls = [0]
    def function_wrapper(x):
        ncalls[0] += 1
        return function(x, *args)
    return ncalls, function_wrapper

def fmin(func, x0, args=(), xtol=1e-4, ftol=1e-4, maxiter=None, maxfun=None,
         full_output=0, disp=1, retall=0, callback=None):
    """
    Minimize a function using the downhill simplex algorithm.

    Parameters
    ----------
    func : callable func(x,*args)
        The objective function to be minimized.
    x0 : ndarray
        Initial guess.
    args : tuple
        Extra arguments passed to func, i.e. ``f(x,*args)``.
    callback : callable
        Called after each iteration, as callback(xk), where xk is the
        current parameter vector.

    Returns
    -------
    xopt : ndarray
        Parameter that minimizes function.
    fopt : float
        Value of function at minimum: ``fopt = func(xopt)``.
    iter : int
        Number of iterations performed.
    funcalls : int
        Number of function calls made.
    warnflag : int
        1 : Maximum number of function evaluations made.
        2 : Maximum number of iterations reached.
    allvecs : list
        Solution at each iteration.

    Other parameters
    ----------------
    xtol : float
        Relative error in xopt acceptable for convergence.
    ftol : number
        Relative error in func(xopt) acceptable for convergence.
    maxiter : int
        Maximum number of iterations to perform.
    maxfun : number
        Maximum number of function evaluations to make.
    full_output : bool
        Set to True if fopt and warnflag outputs are desired.
    disp : bool
        Set to True to print convergence messages.
    retall : bool
        Set to True to return list of solutions at each iteration.

    Notes
    -----
    Uses a Nelder-Mead simplex algorithm to find the minimum of function of
    one or more variables.

    """
    
    fcalls, func = wrap_function(func, args)
    x0 = asfarray(x0).flatten()
    N = len(x0)
    rank = len(x0.shape)
    if not -1 < rank < 2:
        raise ValueError("Initial guess must be a scalar or rank-1 sequence.")
    if maxiter is None:
        maxiter = N * 200
    if maxfun is None:
        maxfun = N * 200

    rho = 1; chi = 2; psi = 0.5; sigma = 0.5;
    one2np1 = range(1,N+1)

    if rank == 0:
        sim = numpy.zeros((N+1,), dtype=x0.dtype)
    else:
        sim = numpy.zeros((N+1,N), dtype=x0.dtype)
    fsim = numpy.zeros((N+1,), float)
    sim[0] = x0
    if retall:
        allvecs = [sim[0]]
    fsim[0] = func(x0)
    nonzdelt = 0.05
    zdelt = 0.00025
    for k in range(0,N):
        y = numpy.array(x0,copy=True)
        if y[k] != 0:
            y[k] = (1+nonzdelt)*y[k]
        else:
            y[k] = zdelt

        sim[k+1] = y
        f = func(y)
        fsim[k+1] = f

    ind = numpy.argsort(fsim)
    fsim = numpy.take(fsim,ind,0)
    # sort so sim[0,:] has the lowest function value
    sim = numpy.take(sim,ind,0)

    iterations = 1

    while (fcalls[0] < maxfun and iterations < maxiter):
        
        if RAWGlobals.cancel_bift:
            return
        
        if (max(numpy.ravel(abs(sim[1:]-sim[0]))) <= xtol \
            and max(abs(fsim[0]-fsim[1:])) <= ftol):
            break

        xbar = numpy.add.reduce(sim[:-1],0) / N
        xr = (1+rho)*xbar - rho*sim[-1]
        fxr = func(xr)
        doshrink = 0

        if fxr < fsim[0]:
            xe = (1+rho*chi)*xbar - rho*chi*sim[-1]
            fxe = func(xe)

            if fxe < fxr:
                sim[-1] = xe
                fsim[-1] = fxe
            else:
                sim[-1] = xr
                fsim[-1] = fxr
        else: # fsim[0] <= fxr
            if fxr < fsim[-2]:
                sim[-1] = xr
                fsim[-1] = fxr
            else: # fxr >= fsim[-2]
                # Perform contraction
                if fxr < fsim[-1]:
                    xc = (1+psi*rho)*xbar - psi*rho*sim[-1]
                    fxc = func(xc)

                    if fxc <= fxr:
                        sim[-1] = xc
                        fsim[-1] = fxc
                    else:
                        doshrink=1
                else:
                    # Perform an inside contraction
                    xcc = (1-psi)*xbar + psi*sim[-1]
                    fxcc = func(xcc)

                    if fxcc < fsim[-1]:
                        sim[-1] = xcc
                        fsim[-1] = fxcc
                    else:
                        doshrink = 1

                if doshrink:
                    for j in one2np1:
                        sim[j] = sim[0] + sigma*(sim[j] - sim[0])
                        fsim[j] = func(sim[j])

        ind = numpy.argsort(fsim)
        sim = numpy.take(sim,ind,0)
        fsim = numpy.take(fsim,ind,0)
        if callback is not None:
            callback(sim[0])
        iterations += 1
        if retall:
            allvecs.append(sim[0])
            
    x = sim[0]
    fval = min(fsim)
    warnflag = 0

    if fcalls[0] >= maxfun:
        warnflag = 1
        if disp:
            print "Warning: Maximum number of function evaluations has "\
                  "been exceeded."
    elif iterations >= maxiter:
        warnflag = 2
        if disp:
            print "Warning: Maximum number of iterations has been exceeded"
    else:
        if disp:
            print "Optimization terminated successfully."
            print "         Current function value: %f" % fval
            print "         Iterations: %d" % iterations
            print "         Function evaluations: %d" % fcalls[0]


    if full_output:
        retlist = x, fval, iterations, fcalls[0], warnflag
        if retall:
            retlist += (allvecs,)
    else:
        retlist = x
        if retall:
            retlist = (x, allvecs)

    return retlist


def C_seeksol(I_exp, m, q, sigma, alpha, dmax, T):
    # print 'In C_seeksol'
    # RAWGlobals.compiled_extensions = False
    # print 'RAWGlobals.compiled_extensions: ' + str(RAWGlobals.compiled_extensions)
    
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
    
    if RAWGlobals.compiled_extensions:
        s = bift_ext.bift(dotsp, dotsptol, maxit, minit, bkkmax, omega, omegamin, omegareduction, B, N, m, P, Psumi, Bmat, alpha, sum_dia, bkk, dP, Pold)
    else:
        #Warning, slower!
        s = bift_python(dotsp, dotsptol, maxit, minit, bkkmax, omega, omegamin, omegareduction, B, N, m, P, Psumi, Bmat, alpha, sum_dia, bkk, dP, Pold)
    
    # s_ext = bift_ext.bift(dotsp, dotsptol, maxit, minit, bkkmax, omega, omegamin, omegareduction, B, N, m, P, Psumi, Bmat, alpha, sum_dia, bkk, dP, Pold)
    # s_python = bift_python(dotsp, dotsptol, maxit, minit, bkkmax, omega, omegamin, omegareduction, B, N, m, P, Psumi, Bmat, alpha, sum_dia, bkk, dP, Pold)

    # print 's from bift_ext is ' + str(s_ext)
    # print 's from bift_python is ' + str(s_python)

    # ********************** C++ CODE *******************************

#    mod = ext_tools.ext_module('bift_ext')
#    
#    code = """
#    #include <iostream.h>
#    #include <math.h>
#  
#    py::object sout;
#    
#    // Initiate Variables
#    int ite = 0;
#  
#    double s = 0,
#          wgrads = 0,
#          wgradc = 0,
#          gradci = 0,
#          gradsi = 0;
#
#    while( ite < maxit && omega > omegamin && fabs(1-dotsp) > dotsptol || (ite < minit) )
#    {
#            if (ite != 0)
#            {
#                /* Calculating smoothness constraint vector m */
#            
#                for(int k = 1; k < N-1; k++)
#                {
#                     m(0, k) =  ((P(0,k-1) + P(0,k+1)) / 2.0);
#                }
#                
#                m(0,0) =  P(0,1) / 2.0;
#                m(0,N-1) =  P(0,N-2) /2.0;
#                
#   
#                /* This calculates the Matrix Psumi */
#                
#                for(int j = 0; j < N; j++)
#                    for(int k = 0; k < N; k++)
#                        Psumi(0,j) = Psumi(0,j) + P(0,k) * Bmat(k,j);
#    
#               // cout << "    " << Psumi(0,50);
#    
#               /* Now calculating dP, and updating P */
#        
#                for(int k = 0; k < N; k++)
#                {        
#                    dP(0,k) = ( m(0,k) * alpha + sum_dia(0,k) - Psumi(0,k) ) / (bkk(0,k) + alpha);      /* ATTENTION! remember C division!, if its all int's then it will be a int result! .. maybe cast it to float()? */
#                    
#                    Psumi(0,k) = 0;    // Reset values in Psumi for next iteration..otherwise Psumi = Psumi + blah will be wrong!
#        
#                    Pold(0,k) = P(0,k);
#         
#                    P(0,k) = (1-omega) * P(0,k) + omega * dP(0,k);
#                    
#                    /* Pin first and last point to zero! */
#    
#                    //P(0,0) = 0.0;
#                    //P(0,N-1) = 0.0;
#                }    
#      
#                //cout << "    " << m(0,50);
#                //cout << "    " << P(0,50);
#                //cout << "    " << dP(0,50);
#                //cout << " | ";
#        
#            } // end if ite != 0
#        
#      
# 
#       ite = ite + 1;
#    
#       /* Calculating Dotsp */
#      
#       dotsp = 0;
#       wgrads = 0;
#       wgradc = 0;
#       s = 0;
#       for(int k = 0; k < N; k++)
#       {
#             s = s - pow( P(0,k) - m(0,k) , 2);                        // sum(-power((P-m),2))
#             
#             gradsi = -2*( P(0,k) - m(0,k) );                            // gradsi = (-2*(P-m))
#             wgrads = wgrads + pow(gradsi, 2);
#       
#             gradci = 0;
#             for(int j = 0; j < N; j++)
#             {
#                 gradci = gradci + 2*( P(0,j) * B(j,k) );     
#             }
#             gradci = gradci - 2*sum_dia(0,k);
#            
#             wgradc = wgradc + pow(gradci , 2);
#             dotsp = dotsp + (gradci * gradsi);
#       }
#      
#//      cout << dotsp;
#//      cout << "    " << wgrads;
#//      cout << "    " << wgradc;
#//      cout << "    " << s;
#//      cout << " | ";
#  
#  
#       /* internal loop to reduce search step (omega) when it's too large */
#         
#       while( dotsp < 0 && double(alpha) < double(bkkmax) && ite > 1 && omega > omegamin)
#       {
#                omega = omega / omegareduction;
#                
#                /* Updating P */
#                 
#                for(int k = 0; k < N; k++)
#                {
#                    P(0,k) = (1-omega) * Pold(0,k) + omega * dP(0,k);
#                }
#                
#                /* Calculating Dotsp */
#                
#                dotsp = 0;
#                wgrads = 0;
#                wgradc = 0;
#                s = 0;
#                for(int k = 0; k < N; k++)
#                {
#                    s = s - pow( P(0,k)-m(0,k) , 2);                        // sum(-power((P-m),2))     
#                    gradsi = -2*(P(0,k)-m(0,k));                            // gradsi = (-2*(P-m))
#                    wgrads = wgrads + pow(gradsi, 2);
#            
#                    gradci = 0;
#                    for(int j = 0; j < N; j++)
#                    {
#                        gradci = gradci + 2*( P(0,j) * B(j,k));     
#                    }
#                    gradci = gradci - 2*sum_dia(0,k);
#                      
#                    wgradc = wgradc + pow(gradci , 2);
#                    dotsp = dotsp + (gradci * gradsi);
#                }    
#                
#       } // end inner whileloop
#     
#        
#       if(wgrads == 0 || wgradc == 0)
#       {
#            dotsp = 1;
#       }
#       else
#       {
#            wgrads = std::sqrt(wgrads);
#            wgradc = std::sqrt(wgradc);
#            dotsp = dotsp / (wgrads * wgradc);
#       }
#     
#          
#    } // end Outer while loop
#    
#    
#    // cout << "ite C: " << ite;
#    // cout << "alpha: " << double(alpha);
#    // cout << "omega: " << omega;
#    //cout << ",   m: " << m(0,20);
#    //cout << ",   dotsp C: " << dotsp;
#    //cout << ",   dP:" << dP(0,20);
#    //cout << "cnt:" << cnt;
#    //cout << ",   wgrads C: " << wgrads;
#    //cout << ",   wgradc C: " << wgradc;
#    
#    
#    //tst(0,1) = wgradc;
#    sout = s;
#    return_val = sout;
#    """
#
#    s = weave.inline(code,['dotsp', 'dotsptol', 'maxit', 'minit', 'bkkmax', 'omega', 'omegamin', 'omegareduction', 'B', 'N', 'm', 'P', 'Psumi', 'Bmat', 'alpha', 'sum_dia', 'bkk', 'dP', 'Pold'], type_converters = converters.blitz, compiler = "gcc")
#    # ***************************************************************
    
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
    
    min, max = Ep.getQrange()
    
    r = linspace(0, dmax, N)
    T = createTransMatrix(Ep.q[min:max], r)
    P = makePriorDistDistribution(Ep, N, dmax, T, 'sphere', Ep.q[min:max])
    
    # print 'Alpha : ' ,alpha
    # print 'Dmax  : ' , dmax
    
    Pout, evd, c  = C_seeksol(Ep.i[min:max], P, Ep.q[min:max], Ep.err[min:max], alpha, dmax, T)
        
    return -evd, c, Pout

def SingleSolve(alpha, dmax, Ep, N):
    ''' Fit to data with forced Dmax and Alpha values '''
    
    alphafin = float(alpha)
    dmaxfin = float(dmax)
    min, max = Ep.getQrange()
    
    print dmaxfin, N
    
    r = linspace(0, dmaxfin, int(N))
    T = createTransMatrix(Ep.q[min:max], r)
    P = makePriorDistDistribution(Ep, N, dmaxfin, T, 'sphere', Ep.q[min:max])
    
    Pr, post, c = C_seeksol(Ep.i[min:max], P, Ep.q[min:max], Ep.err[min:max], alphafin, dmaxfin, T)

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
    
    # print 'Rg : ', Rg
    # print 'dr : ', dr
    # print 'Area2 : ', area2
    
    I0 = mean(Fit[0, 0:5])
    # print Fit[0, 0:5]
    # print 'I(0) from avg of 5 first points :', I0
    # print 'I(0) from area under P(r) : ', area
    
    I0 = area
    
    Pr = array(Pr)
    
    Pr = Pr / (4*pi*dr)   # Since what we got from the optimization is 4*pi*dr * p(r) 
                          #(we excluded 4*pi*dr in the trans matrix!)
    
    #Pr = Pr[0]  ## ..need this if we dont add zeros
    
    Pr = transpose(Pr)
    
    #alphafin = exp(alphafin)
    
    # Save all information from the search
    bift_info = {'alpha' : alphafin,
                'dmax' : dmaxfin,
                'I0' : I0,
                'ChiSquared' : c,
                'Rg' : Rg,
                'post': post,
                'filename': os.path.splitext(Ep.getParameter('filename'))[0]+'.ift',
                'algorithm' : 'BIFT'}
        
    #ExpObj = cartToPol.BIFTMeasurement(transpose(Pr), r, ones((len(transpose(Pr)),1)), Ep.param, Fit, plotinfo)

    ift_sasm = SASM.IFTM(transpose(Pr), r, ones(len(transpose(Pr))), Ep.i[min:max], Ep.q[min:max], Ep.err[min:max], Fit[0], bift_info) 
    
    return ift_sasm
    

def fineGetEvidence(data, Ep, N):
    
    alpha = data[0]
    dmax = data[1]
    
    min, max = Ep.getQrange()
    
    
    alpha = exp(alpha)
    
    r = linspace(0, dmax, N)
    T = createTransMatrix(Ep.q[min:max], r)
    P = makePriorDistDistribution(Ep, N, dmax, T, 'sphere', Ep.q[min:max])
    
    # print alpha
    # print dmax
    
    ########################################################################
    # THIS IS A BIG NO NO!.. need to change it later. 
    ########################################################################
    bift_status = {'alpha'    : alpha,
                   'evidence' : '',
                   'chi'      : '',
                   'dmax'     : dmax,
                   'spoint': '',
                   'tpoint': '',
                   'filename' : Ep.getParameter('filename')}
        
    # statusdlg = wx.FindWindowByName('BIFTStatusDlg')
    # if statusdlg != None:
    #     wx.CallAfter(statusdlg.updateData, bift_status)
    #########################################################################
    
    Pout, evd, c  = C_seeksol(Ep.i[min:max], P, Ep.q[min:max], Ep.err[min:max], alpha, dmax, T)
        
    return -evd


def doBift(Exp, queue, N, alphamax, alphamin, alphaN, maxDmax, minDmax, dmaxN):
    '''
        Runs the BIFT algorithm on an Experiment Object or a filename
        
        N = Number of points in the P(r) function
        DmaxUbound = Upper bound for Dmax
        # DmaxLbound = Lower bound for Dmax
        
        AlphaUbound = Upper bound of Alpha
        AlphaLbound = Lower bound of Alpha
    '''

    
    Ep = Exp
    
    min, max = Exp.getQrange()
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
    
    # Cycle though dmax/alpha points and find best posterior / evidence
    all_posteriors = zeros((len(dmax_points), len(alpha_points)))
    dmax_idx = 0
    
    total_points = len(dmax_points) * len(alpha_points)
    current_point = 0

    alphafin = -1
    dmaxfin = -1
    
    for each_dmax in dmax_points:
        
        alpha_idx = 0
        for each_alpha in alpha_points:
            
            if RAWGlobals.cancel_bift:
                queue.put({'canceled' : True})
                return None
                    
            post, c, result = GetEvidence(each_alpha, each_dmax, Ep, N)
            
            if c == '1.#QNAN':
                print 'ERROR !! GOT #QNAN!'

            # print ''
            # print "alphaC =", exp(each_alpha)
            # print "evdC =", post
            # print "C = ", str(c)
            # print "Dmax =", each_dmax
    
            bift_status = {'alpha'    : each_alpha,
                           'evidence' : post,
                           'chi'      : c,
                           'dmax'     : each_dmax,
                           'spoint'   : current_point,
                           'tpoint'   : total_points}

            queue.put({'update' : bift_status})
           
            # ########################################################################
            # # THIS IS A BIG NO NO!.. need to change it later. 
            # ########################################################################
            # statusdlg = wx.FindWindowByName('BIFTStatusDlg')
            # if statusdlg != None:
            #     # wx.CallAfter(statusdlg.updateData, bift_status)
            #     pass
            # ########################################################################
            
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
            
            current_point+= 1
        
        dmax_idx = dmax_idx + 1
    
    # print "final alpha: ", alphafin      
    # print "final dmax: ", dmaxfin
    # print "c_alpha: ", alphac
    # print "c_dmax: ", dmaxc
    
    # print 'Search took %9.6f Seconds' % dt 
    if alphafin == -1 and dmaxfin == -1:
        queue.put({'failed':True})
        return
    
    bift_status = {'alpha'      : alphafin,
                   'evidence'   : finalpost,
                   'chi'        : bestc,
                   'dmax'       : dmaxfin,
                   'spoint'     : current_point,
                   'tpoint'     : total_points,
                   'status'     : 'Running a fine search'}
    
    # wx.CallAfter(statusdlg.updateData, bift_status, True)
    
    queue.put({'update' : bift_status})
    
    # print "Making fine search..."
    src_result = fineSearch(Ep, N, log(alphafin), dmaxfin)
    
    if src_result != None:
        alphafin, dmaxfin = src_result
    else:
        queue.put({'canceled' : True})
        return None

    ###########################################
    # Pr = P(r) function, Fit = Fitted curve
    ###########################################

    r = linspace(0, dmaxfin, N)
    T = createTransMatrix(Ep.q[min:max], r)
    P = makePriorDistDistribution(Ep, N, dmaxfin, T, 'sphere', Ep.q[min:max])
    
    Pr, post, c = C_seeksol(Ep.i[min:max], P, Ep.q[min:max], Ep.err[min:max], alphafin, dmaxfin, T)

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
    
    # print 'Rg : ', Rg
    # print 'dr : ', dr
    # print 'Area2 : ', area2
    
    I0 = mean(Fit[0, 0:5])
    # print Fit[0, 0:5]
    # print 'I(0) from avg of 5 first points :', I0
    # print 'I(0) from area under P(r) : ', area
    
    I0 = area
    
    Pr = array(Pr)    # Since what we got from the optimization is 4*pi*dr * p(r) 
                      #(we excluded 4*pi*dr in the trans matrix!)
    
    Pr = Pr / (4*pi*dr)
    
    Pr = transpose(Pr)
    
    # Save all information from the search
    bift_info = {'dmax_points' : dmax_points,
                'alpha_points' : alpha_points,
                'all_posteriors' : all_posteriors,
                'alpha' : alphafin,
                'dmax' : dmaxfin,
                'I0' : I0[0],
                'ChiSquared' : c,
                'Rg' : Rg,
                'filename': os.path.splitext(Ep.getParameter('filename'))[0]+'.ift',
                'algorithm' : 'BIFT'}
    
    ift_sasm = SASM.IFTM(transpose(Pr), r, ones(len(transpose(Pr))), Ep.i[min:max], Ep.q[min:max], Ep.err[min:max], Fit[0], bift_info) 
    
    bift_status = {'alpha'      : alphafin,
                   'evidence'   : post,
                   'chi'        : c,
                   'dmax'       : dmaxfin,
                   'spoint'     : current_point,
                   'tpoint'     : total_points}
    
    queue.put({'update' : bift_status})
    #return Out, Pout, r, Ep.i, plotinfo
    
    return ift_sasm

def pinnedFineSearch(Ep, N, alpha, dmax):
    
    arg = (Ep, N)
    
    opt = optimize.fmin(fineGetEvidence, [alpha, dmax], args = arg)
    
    print "Optimum found: "
    print exp(opt[0]), opt[1]

    return exp(opt[0]), opt[1]

def fineSearch(Ep, N, alpha, dmax):
    
    arg = (Ep, N)
    
    #opt = optimize.fmin(fineGetEvidence, [alpha, dmax], args = arg)
    opt = fmin(fineGetEvidence, [alpha, dmax], args = arg, disp = False)
    
    if opt == None:
        return
    
    # print "Optimum found: "
    # print exp(opt[0]), opt[1]

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

    if not RAWGlobals.frozen and RAWGlobals.compiled_extensions:
        weave.inline(code,['qlen', 'rlen', 'T', 'r', 'q', 'c'], type_converters = converters.blitz, compiler = "gcc")    

    else:
        for i in range(qlen):
            for j in range(rlen):
                qr = q[i]*r[j]
                chk = c*math.sin(qr)/qr

                if chk != chk:      #Checks for nan values?
                    T[i, j] = 1
                else:
                    T[i,j] = chk
#    transext = ext_tools.ext_function('trans_matrix', code, ['qlen', 'rlen', 'T', 'r', 'q', 'c'], type_converters = converters.blitz)   
#    mod.add_function(transext)
#    mod.compile(compiler = 'gcc')
            
    return T

def makePriorDistDistribution(E, N, dmax, T, type = 'sphere', q = None):

#    if isinstance(E, cartToPol.Measurement):
#        scale_factor = E.i[0]
#    else:
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

def bift_python(dotsp, dotsptol, maxit, minit, bkkmax, omega, omegamin, omegareduction, B, N, m, P, Psumi, Bmat, alpha, sum_dia, bkk, dP, Pold):


    # // Initiate Variables
    ite = 0
  
    s = 0.
    wgrads = 0.
    wgradc = 0.
    gradci = 0.
    gradsi = 0.

    while (ite < maxit and omega > omegamin and abs(1-dotsp) > dotsptol) or ite < minit:

        if ite != 0:
        
            #/* Calculating smoothness constraint vector m */
            
            for k in range(1,N-1):            
                m[0, k] =  ((P[0,k-1] + P[0,k+1]) / 2.0)
            

            m[0,0] =  P[0,1] / 2.0
            m[0,N-1] =  P[0,N-2] /2.0
            

            # /* This calculates the Matrix Psumi */
            
            for j in range(N):
                for k in range(N):
                    Psumi[0,j] = Psumi[0,j] + P[0,k] * Bmat[k,j]

           # // cout << "    " << Psumi(0,50);

           # /* Now calculating dP, and updating P */
    
            for k in range(N):        
                dP[0,k] = (m[0,k]*alpha + sum_dia[0,k] - Psumi[0,k])/(bkk[0,k] + alpha)      #/* ATTENTION! remember C division!, if its all int's then it will be a int result! .. maybe cast it to float()? */
                
                Psumi[0,k] = 0    #// Reset values in Psumi for next iteration..otherwise Psumi = Psumi + blah will be wrong!
    
                Pold[0,k] = P[0,k]
     
                P[0,k] = (1-omega)*P[0,k] + omega*dP[0,k]
                
                # /* Pin first and last point to zero! */

                # //P(0,0) = 0.0;
                # //P(0,N-1) = 0.0;   
  
            # //cout << "    " << m(0,50);
            # //cout << "    " << P(0,50);
            # //cout << "    " << dP(0,50);
            # //cout << " | ";
    
        # // end if ite != 0

        ite = ite + 1

       # /* Calculating Dotsp */
      
        dotsp = 0.
        wgrads = 0.
        wgradc = 0.
        s = 0.
        for k in range(N):       
            s = s - pow(P[0,k] - m[0,k], 2)                        #// sum(-power((P-m),2))
             
            gradsi = -2*(P[0,k] - m[0,k])                           # // gradsi = (-2*(P-m))
            wgrads = wgrads + pow(gradsi, 2)
       
            gradci = 0

            for j in range(N):
                gradci = gradci + 2*(P[0,j] * B[j,k])     

            gradci = gradci - 2*sum_dia[0,k]
            
            wgradc = wgradc + pow(gradci, 2)
            dotsp = dotsp + (gradci * gradsi)

      
    # //      cout << dotsp;
    # //      cout << "    " << wgrads;
    # //      cout << "    " << wgradc;
    # //      cout << "    " << s;
    # //      cout << " | ";


       # /* internal loop to reduce search step (omega) when it's too large */
         
        while dotsp < 0 and float(alpha) < float(bkkmax) and ite > 1 and omega > omegamin:
            omega = omega / omegareduction
            
            # /* Updating P */
             
            for k in range(N):
                P[0,k] = (1-omega)*Pold[0,k] + omega*dP[0,k]
                        
            # /* Calculating Dotsp */
            
            dotsp = 0.
            wgrads = 0.
            wgradc = 0.
            s = 0.

            for k in range(N):
                s = s - pow(P[0,k]-m[0,k], 2)                        #// sum(-power((P-m),2))     
                gradsi = -2*(P[0,k]-m[0,k])                            #// gradsi = (-2*(P-m))
                wgrads = wgrads + pow(gradsi, 2)
        
                gradci = 0
            
                for j in range(N):
                    gradci = gradci + 2*(P[0,j]*B[j,k])     
            
                gradci = gradci - 2*sum_dia[0,k]
                  
                wgradc = wgradc + pow(gradci, 2)
                dotsp = dotsp + (gradci * gradsi)
                
                
        # // end inner whileloop
         
        
        if wgrads == 0 or wgradc == 0:
            dotsp = 1.
        else:
            wgrads = pow(wgrads, 0.5)
            wgradc = pow(wgradc, 0.5)
            dotsp = dotsp / (wgrads * wgradc)
   
          
    # } // end Outer while loop

    # // cout << "ite C: " << ite;
    # // cout << "alpha: " << double(alpha);
    # // cout << "omega: " << omega;
    # //cout << ",   m: " << m(0,20);
    # //cout << ",   dotsp C: " << dotsp;
    # //cout << ",   dP:" << dP(0,20);
    # //cout << "cnt:" << cnt;
    # //cout << ",   wgrads C: " << wgrads;
    # //cout << ",   wgradc C: " << wgradc;
    
    
    # //tst(0,1) = wgradc;
    sout = s
    
    return sout
  
    
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
        self.err = err
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

    #Radius, N, Qmax (Dmax = 2*Radius)
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
        
