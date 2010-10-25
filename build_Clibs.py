from scipy.weave import ext_tools
from scipy.weave import converters
import numpy as np
from scipy import weave
from scipy.weave import build_tools
import os

def build_bift():
    
    print 'Compiling bift_ext...'
    
    #(I_exp, m, q, sigma, alpha, dmax, T)
  
    I_exp = [1.0,2.0,3.0,4.0]
    q = [1.0,2.0,3.0,4.0]
    sigma = [1.0,2.0,3.0,4.0]
    dmax = 10.0
    alpha = 10.0
    T = np.ones((4,4), dtype = np.float64)
    
    m = [1,2,3,4]
    
    N = max(np.shape(m))
    N = np.int(N)

    m = np.matrix(m)         #m is the prior distribution
   
    P = m.copy()          #multiply(m, 1.0005) # first guess is set equal to priror distribution
    
    m2 = m.copy()
    
    I_exp = np.matrix(I_exp)
        
    sigma_sq = np.matrix(sigma)            # std to variance
    
    # Calculate factors for the gradient:
    sum_dia = np.matrix(np.sum( np.multiply(T, np.transpose(I_exp) / np.transpose(sigma_sq)) , 0))    # works!  makes sum( (d_i * a_ik) / s^2_i) over i, giver f_k vektor 
    
    B = np.dot(np.transpose(T),( T / np.transpose(sigma_sq)))     # this one was a bitch!  this is b_kj 
   
    Bdiag = np.matrix(np.multiply(B,np.eye(len(B))))              # The diagonal of B
    
    bkk = np.sum(Bdiag, 0)                                  # k col-vektor
    
    Bmat = B-Bdiag
     
    # ************  convert before C++  *************************
    Psumi = np.zeros((1,N))                   ## all should be arrays!         NB matrix and array dont mix in weave C!!!!
    sum_dia = np.array(sum_dia, dtype = np.float64)
    bkk = np.array(bkk, dtype = np.float64)
    dP = np.array(np.zeros((1,N)), dtype = np.float64)
    
    #m = array(m, 'float64')
    m = np.zeros((1,N), dtype = np.float64)
    
    #m = array(m, 'float64')            # important! otherwise C will only make an Int array, and kill floats!
    
    Pold = np.array(np.zeros((1,N)), dtype = np.float64)
    
    I_exp = np.array(I_exp,dtype = np.float64)
    Bmat = np.array(Bmat, dtype = np.float64)
    B = np.array(B, dtype = np.float64)
    
    omegareduction = 2.0
    omega = 0.5
    minit = 10
    maxit = 1000
    dotsptol = 0.001
    omegamin = 0.001
    
    bkkmax = bkk.max() * 10
    
    P = np.array(P, dtype = np.float64)            # important! otherwise C will only make an Int array, and kill floats!
    
    dotsp = 0.0
    
    alpha = float(alpha)              # Important! otherwise C code will crash
    
    
    'bkkmax', 'B', 'N', 'm', 'P', 'Psumi', 'Bmat', 'alpha', 'sum_dia', 'bkk', 'dP', 'Pold'
    
    # ********************** C++ CODE *******************************
    mod = ext_tools.ext_module('bift_ext')
    
    code = """
    //#include <iostream.h>
    //#include <math.h>
  
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

    #s = weave.inline(code,['dotsp', 'dotsptol', 'maxit', 'minit', 'bkkmax', 'omega', 'omegamin', 'omegareduction', 'B', 'N', 'm', 'P', 'Psumi', 'Bmat', 'alpha', 'sum_dia', 'bkk', 'dP', 'Pold'], type_converters = converters.blitz, compiler = "gcc")
    # ***************************************************************
    
    biftext = ext_tools.ext_function('bift',
                                     code,
                                     ['dotsp', 'dotsptol',
                                      'maxit', 'minit', 'bkkmax',
                                      'omega', 'omegamin',
                                      'omegareduction', 'B', 'N',
                                      'm', 'P', 'Psumi', 'Bmat',
                                      'alpha', 'sum_dia', 'bkk',
                                      'dP', 'Pold'],
                                      type_converters = converters.blitz) 
      
    mod.add_function(biftext)
    
    kw, file = mod.build_kw_and_file('.', {})
    
    success = build_tools.build_extension(file, temp_dir = './temp/',
                                              compiler_name = 'gcc',
                                              verbose = 0, **kw)
   
    if success:
        print '\n\n****** bift_ext module compiled succesfully! *********'
    
def build_transmatrix():
    
    print 'Compiling transmatrix_ext...'
    
    q = [1.0, 2.0, 3.0, 4.0, 6.0]
    i = [0.1, 23.3, 21.3, 45.0, 23.0]
    r = [1.0,2.0,3.0,4.0,5.0,6.0]
    
    mod = ext_tools.ext_module('transmatrix_ext')
    
    T = np.zeros((len(q), len(r)), dtype = np.float64)
    
    qlen = len(q)
    rlen = len(r)
    
    q = np.array(q)
    r = np.array(r)

    dr = r[1]
    
    # Leaving out 4 * pi * dr! That means the solution will include these three factors!
    c = 1
   
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
#    weave.inline(code,['qlen', 'rlen', 'T', 'r', 'q', 'c'], type_converters = converters.blitz, compiler = "gcc")    

    transext = ext_tools.ext_function('trans_matrix',
                                      code,
                                      ['qlen', 'rlen',
                                       'T', 'r', 'q', 'c'],
                                       type_converters = converters.blitz)   
    mod.add_function(transext)

    kw, file = mod.build_kw_and_file('.', {})
    
    success = build_tools.build_extension(file, temp_dir = './temp/',
                                              compiler_name = 'gcc',
                                              verbose = 0, **kw)
   
    if success:
        print '\n\n****** transmatrix_ext module compiled succesfully! *********'
        
def build_sinfouriermatrix():
    
    print 'Compiling fouriermatrix_ext...'
    
    q = [1.0, 2.0, 3.0, 4.0, 6.0]
    i = [0.1, 23.3, 21.3, 45.0, 23.0]
    r = [1.0,2.0,3.0,4.0,5.0,6.0]
    
    mod = ext_tools.ext_module('sinefouriermatrix_ext')
    
    T = np.zeros((len(q), len(r)), dtype = np.float64)
    
    qlen = len(q)
    rlen = len(r)
    
    q = np.array(q)
    r = np.array(r)

    dr = r[1]
   
    code = """
    
    float chk, qr;
    int i, j;
    
    for( i = 0; i < qlen; i++)
           for( j = 0; j < rlen; j++)
           {
                 
                 qr = q(i) * r(j);
                 chk = sin(qr) ;

                  if(chk != chk) {
                      T(i,j) = 1;
                  }
                  else {
                      T(i,j) = chk; 
                  }
                      
           }
           
    """   
#    weave.inline(code,['qlen', 'rlen', 'T', 'r', 'q', 'c'], type_converters = converters.blitz, compiler = "gcc")    

    transext = ext_tools.ext_function('trans_matrix',
                                      code,
                                      ['qlen', 'rlen',
                                       'T', 'r', 'q'],
                                       type_converters = converters.blitz)   
    mod.add_function(transext)

    kw, file = mod.build_kw_and_file('.', {})
    
    success = build_tools.build_extension(file, temp_dir = './temp/',
                                              compiler_name = 'gcc',
                                              verbose = 0, **kw)
   
    if success:
        print '\n\n****** fouriermatrix_ext module compiled succesfully! *********'
   
def build_radavg():
    
    print 'Compiling ravg_ext...'

    mod = ext_tools.ext_module('ravg_ext')
    
    #################################################
    # Type definitions:
    #################################################
    in_image = np.ones((10,10), dtype=np.float64)
    
    xlen = np.int(in_image.shape[0])
    ylen = np.int(in_image.shape[1])
    
    x_c = np.float(1.0)
    y_c = np.float(1.0)
    
    mask = np.ones((xlen,ylen), dtype = np.float64)
        
    readoutNoiseFound = np.int(1)
    readoutNoise_mask = np.zeros((xlen,ylen), dtype = np.float64)
    readoutN = np.zeros((1,4), dtype = np.float64)
        
    low_q = np.int(0)
    high_q = np.int(5)           
    
    hist = np.zeros(5, dtype = np.float64)
    hist_count = np.zeros((10,10), dtype = np.float64) # -----" --------- for number of pixels in a circle at a certain q
       
    zinger_threshold = np.int(60000.0)        # Too Hardcoded!
    
    res = np.zeros((1,1), dtype = np.float64)
            
    code = """
    
    double rel_x, rel_y, r, delta, deltaN;
    int x, y;
    //int idx;
     
    for( x = 0; x < xlen; x++)
           for( y = 0; y < ylen; y++)
           {
                rel_x = x-x_c;
                rel_y = y_c-y;
           
                r = int(std::sqrt((rel_y*rel_y) + (rel_x*rel_x)));
                
                //res(x,y) = r;
    
                if( r < high_q && r > low_q && mask(x,y) == 1 && in_image(x,y) > 0)
                {
                    /* res2(x,y) = r; */               /*  A test image, gives the included range image */
                    
                    hist(r) = hist(r) + in_image(x,y);                   /* Integration of pixel values */
                    
                    hist_count(0, int(r)) = hist_count(0, int(r)) + 1;     /* Number of pixels in a bin */
                    
                    delta = in_image(x,y) - hist_count(1, int(r));         /* Calculation of variance */
                    hist_count(1, int(r)) = hist_count(1, int(r)) + (delta / hist_count(0, int(r)));              
                    hist_count(2, int(r)) = hist_count(2, int(r)) + (delta * (in_image(x,y)-hist_count(1, int(r))));   
                
                }
                
                if ( readoutNoiseFound == 1 && r < high_q-1 && r > low_q && readoutNoise_mask(x,y) == 0)
                {
                    
                    readoutN(0,0) = readoutN(0,0) + 1;
                    readoutN(0,1) = readoutN(0,1) + in_image(x,y);
                    
                    deltaN = in_image(x,y) - readoutN(0,2);
                    readoutN(0,2) = readoutN(0,2) + (deltaN / readoutN(0,0));
                    readoutN(0,3) = readoutN(0,3) + (deltaN * (in_image(x,y)-readoutN(0,2)));        
                    
                }
            
            }
    
    """
  
    ravg = ext_tools.ext_function('ravg',
                                  code,
                                  ['readoutNoiseFound', 'readoutN',
                                   'readoutNoise_mask', 'xlen',
                                   'ylen','x_c','y_c', 'hist',
                                   'low_q', 'high_q', 'in_image',
                                   'hist_count', 'mask'], 
                                   type_converters = converters.blitz)
    mod.add_function(ravg)
    
    #SYSTEM TEMP DIR MIGHT NOT HAVE WRITE PERMISSION OR HAS SPACES IN IT => FAIL!
    #EXTREMELY ANNOYING THAT THE TEMP DIR CAN'T BE SET FROM mod.compile()! .. This is a work around:
    
    kw, file = mod.build_kw_and_file('.', {})
    
    success = build_tools.build_extension(file, temp_dir = './temp/',
                                              compiler_name = 'gcc',
                                              verbose = 0, **kw)
   
    if success:
        print '\n\n****** ravg_ext module compiled succesfully! *********'


def build_HouseholderTransform():
    pass
    

def build_Polygonmask():
    
    pass
    verts = np.array([[549.,1096.],[144.,51.],[989.,38.],[549.,1096.]]) 
    points = np.array([[0, 0],[0, 1],[0, 2]])    

    verts = verts.astype(np.float64)
    points = points.astype(np.float64)

    xp = np.ascontiguousarray(verts[:,0])
    yp = np.ascontiguousarray(verts[:,1])
    x = np.ascontiguousarray(points[:,0])
    y = np.ascontiguousarray(points[:,1])
    out = np.empty(len(points),dtype=np.uint8)

    mod = ext_tools.ext_module('polygonmask_ext')

    code = """
        /* Code from:
           http://www.ecse.rpi.edu/Homepages/wrf/Research/Short_Notes/pnpoly.html
   
           Copyright (c) 1970-2003, Wm. Randolph Franklin
   
           Permission is hereby granted, free of charge, to any person
           obtaining a copy of this software and associated documentation
           files (the "Software"), to deal in the Software without
           restriction, including without limitation the rights to use, copy,
           modify, merge, publish, distribute, sublicense, and/or sell copies
           of the Software, and to permit persons to whom the Software is
           furnished to do so, subject to the following conditions:
   
        1. Redistributions of source code must retain the above
                 copyright notice, this list of conditions and the following
                 disclaimers.
        2. Redistributions in binary form must reproduce the above
                 copyright notice in the documentation and/or other materials
                 provided with the distribution.
        3. The name of W. Randolph Franklin may not be used to endorse
                 or promote products derived from this Software without
                 specific prior written permission.
   
           THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
           EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
           MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
           NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS
           BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN
           ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
           CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
           SOFTWARE. */
       
        int i,j,n;
        unsigned int c;
        int nr_verts = Nxp[0];
        for (n = 0; n < Nx[0]; n++) {
            c = 0;
        for (i = 0, j = nr_verts-1; i < nr_verts; j = i++) {
                if ((((yp(i)<=y(n)) && (y(n)<yp(j))) ||
                  ((yp(j)<=y(n)) && (y(n)<yp(i)))) &&
                (x(n) < (xp(j) - xp(i)) * (y(n) - yp(i)) / (yp(j) - yp(i)) + xp(i)))
           
        c = !c;
        }
    out(n) = c;
        }
        """
        #weave.inline(code, ['xp','yp','x','y','out'], type_converters=weave.converters.blitz)
        
    polymsk = ext_tools.ext_function('polymsk', 
                                         code, 
                                         ['xp','yp','x','y','out'], 
                                         type_converters = converters.blitz)
        
    mod.add_function(polymsk)
    
    kw, file = mod.build_kw_and_file('.', {})
    success = build_tools.build_extension(file, temp_dir = './temp/',
                                              compiler_name = 'gcc',
                                              verbose = 0, **kw)

    if success:
        print '\n\n****** polymask_ext module compiled succesfully! *********'        
        #mod.compile(compiler = 'gcc')
 #       polygonmask_ext.polymsk(xp, yp, x, y, out)

def build_TridiagonalSolve(): 
    ''' See http://en.wikipedia.org/wiki/Tridiagonal_matrix_algorithm '''

    #/* Fills solution into x. Warning: will modify c and d! */
    #TridiagonalSolve (const double *a, const double *b, double *c, double *d, double *x, unsigned int n)
    
    print 'Compiling tridiagsolve_ext...'
    
    mod = ext_tools.ext_module('tridiagsolve_ext')
    
    c = np.ones(9, dtype = np.float64)
    b = np.ones(10, dtype = np.float64)*5
    a = np.ones(9, dtype = np.float64)
    
    d = np.ones(5, dtype = np.float64)
    x = np.ones(5, dtype = np.float64)
    n = 5
    
    
    code = """
    
    /* Modify the coefficients. */
    c[0] /= b[0];    /* Division by zero risk. */
    d[0] /= b[0];    /* Division by zero would imply a singular matrix. */
    for (int i = 1; i < n; i++){
        double id = 1 / (b[i] - c[i-1] * a[i]);  /* Division by zero risk. */
        c[i] *= id;                              /* Last value calculated is redundant. */
        d[i] = (d[i] - d[i-1] * a[i]) * id;
    }
 
    /* Now back substitute. */
    x[n - 1] = d[n - 1];
    for (int i = n - 2; i >= 0; i--)
        x[i] = d[i] - c[i] * x[i + 1];

    """
    
    ravg = ext_tools.ext_function('tridiagsolve',
                                  code,
                                  ['a','b', 'c', 'd', 'x', 'n'], 
                                  type_converters = converters.blitz)

    kw, file = mod.build_kw_and_file('.', {})
    
    success = build_tools.build_extension(file, temp_dir = './temp/',
                                              compiler_name = 'gcc',
                                              verbose = 0, **kw)
   
    if success:
        print '\n\n****** tridiagsolve_ext module compiled succesfully! *********'


if __name__ == "__main__":
    
    build_radavg()
    build_transmatrix()
    
    build_bift()
    build_Polygonmask()
    build_TridiagonalSolve()
    
    build_sinfouriermatrix()
    
    
    
