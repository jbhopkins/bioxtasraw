#******************************************************************************
# This file is part of RAW.
#
#    RAW is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    RAW is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with RAW.  If not, see <http://www.gnu.org/licenses/>.
#
#******************************************************************************

#import setuptools
#from setuptools import setup
#from setuptools import Extension

try:
    from weave import ext_tools, converters, build_tools
except ImportError:
    from scipy.weave import ext_tools, converters, build_tools
import numpy as np
import os, sys, shutil

workdir = os.getcwd()

temp_dir = os.path.join(workdir, 'temp')

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

    success = build_tools.build_extension(file, temp_dir = temp_dir,
                                              compiler_name = 'gcc',
                                              verbose = 0, **kw)

    if success:
        print '\n****** bift_ext module compiled succesfully! *********\n'

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

    success = build_tools.build_extension(file, temp_dir = temp_dir,
                                              compiler_name = 'gcc',
                                              verbose = 0, **kw)

    if success:
        print '\n****** transmatrix_ext module compiled succesfully! *********\n'


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
    histlen = int(len(hist))
    hist_count = np.zeros((10,10), dtype = np.float64) # -----" --------- for number of pixels in a circle at a certain q

    zinger_threshold = np.int(60000.0)        # Too Hardcoded!

    res = np.zeros((1,1), dtype = np.float64)

    qmatrix = np.zeros((100, 1000), dtype = np.float64)

    dezingering = 1
    dezing_sensitivity = 4.0

    code = """

    #define WINDOW_LENGTH 30

    double rel_x, rel_y, r, delta, deltaN, qmat_cnt, std;
    int i, x, y, half_window_size, window_start_idx, q_idx, point_idx;

    double window[WINDOW_LENGTH];
    double median;
    double *window_ptr, *data;
    int win_len = WINDOW_LENGTH;
    int half_win_len;
    int hist_length;

    hist_length = PyObject_Length(py_hist);
    half_window_size = 15;

    data = (double *) qmatrix_array->data;             /* Pointer to the numpy array version of qmatrix */

    window_ptr = window;

    half_window_size = (WINDOW_LENGTH / 2.0);
    win_len = WINDOW_LENGTH;

    for( x = 0; x < xlen; x++)
           for( y = 0; y < ylen; y++)
           {
                rel_x = x-x_c;
                rel_y = y_c-y;

                r = int( std::sqrt((rel_y*rel_y) + (rel_x*rel_x)) );

                //res(x,y) = r;

                if( r < high_q && r > low_q && mask(x,y) == 1) // && in_image(x,y) > 0)
                {
                    q_idx = int(r);

                    /* res2(x,y) = r; */                                  /*  A test image, gives the included range image */

                    hist(r) = hist(r) + in_image(x,y);                    /* Integration of pixel values */

                    qmat_cnt = hist_count(0, q_idx);                      /* Number of pixels in a bin */
                    qmatrix(q_idx, int(qmat_cnt)) = in_image(x,y);        /* Save pixel value for later analysis */

                    hist_count(0, q_idx) = hist_count(0, q_idx) + 1;      /* Number of pixels in a bin */

                    delta = in_image(x,y) - hist_count(1, q_idx);         /* Calculation of variance start */

                    hist_count(1, q_idx) = hist_count(1, q_idx) + (delta / hist_count(0, q_idx));
                    hist_count(2, q_idx) = hist_count(2, q_idx) + (delta * (in_image(x,y)-hist_count(1, q_idx)));


                    /* *******************   Dezingering   ******************** */

                    if ( (hist_count(0, int(r)) >= WINDOW_LENGTH) && (dezingering == 1))
                    {
                        point_idx = (int) hist_count(0, q_idx);
                        window_start_idx = point_idx - win_len;

                        window_ptr = window;                                                        /* Reset pointers */
                        data = (double *) PyArray_GETPTR2(qmatrix_array, q_idx, point_idx);

                        moveDataToWindow(window_ptr, data, win_len);
                        quicksort(window, 0, WINDOW_LENGTH-1);

                        std = getStd(window_ptr, win_len);
                        window_ptr = window;                                                        /* Reset pointers */
                        median = window_ptr[half_window_size];

                        //printf("median: %f\\n", median);

                        half_win_len = point_idx - half_window_size;


                        if (qmatrix(q_idx, half_win_len) > (median + (dezing_sensitivity * std))){
                            qmatrix(q_idx, half_win_len) = median;
                        }

                    } // end dezinger if case


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

    /* *********************************************  */
    /* Remove zingers at the first (window/2) points  */
    /* *********************************************  */

   if (dezingering == 1){

        half_window_size = (int) (WINDOW_LENGTH / 2.0);
        win_len = WINDOW_LENGTH;

        for(q_idx = 0; q_idx < hist_length; q_idx++){

            if (hist_count(0, q_idx) > (win_len + half_window_size)){

                for(i = (win_len + half_window_size); i > win_len; i--){

                    point_idx = (int) i;
                    data = (double *) PyArray_GETPTR2(qmatrix_array, q_idx, point_idx);

                    window_start_idx = point_idx - win_len;
                    window_ptr = window;

                    moveDataToWindow(window_ptr, data, win_len);
                    quicksort(window, 0, WINDOW_LENGTH-1);

                    std = getStd(window_ptr, win_len);
                    window_ptr = window;                      /* Reset pointers */
                    median = window_ptr[half_window_size];

                    half_win_len = point_idx - win_len;

                    if (qmatrix(q_idx, half_win_len) > (median + (dezing_sensitivity * std))){
                        qmatrix(q_idx, half_win_len) = median;

                    }
                }
            }
        }
    }

    printf("\\n\\n********* Radial Averaging and dezingering ********\\n");
    printf("Done!");

    """

    code2 = """

    double getStd(double *window_ptr, int win_len)
    {
        int half_win_len;
        double mean, variance, M2, n, delta;

        M2 = 0;
        n = 0.0;
        mean = 0;
        variance = 1;
        delta = 0;

        half_win_len = win_len / 2;

        while(half_win_len--)
        {
            ++n;
            delta = ((double) *window_ptr) - mean;
            mean = mean + (delta/n);

            M2 = M2 + (delta * (((double) *window_ptr) - mean));

            ++window_ptr;
        }

        if(n > 1)
                variance = M2/(n - 1);     /* To avoid devide by zero */

        return sqrt(variance);
    }

    void moveDataToWindow(double *window_ptr, double *data, int win_len)
    {
        data++;                                        /* Pointers needs to be moved back/forward since */
        window_ptr--;                                  /* *data++ doesn't work, but *++data does.. strange! */

        while(win_len--)
        {
            *++window_ptr = *--data;                  /* Move values from data array to the window array */
        }

    }

    void swap(double *x, double *y)
    {
       long temp;
       temp = *x;
       *x = *y;
       *y = temp;
    }

    long choose_pivot(long i, long j)
    {
       return((i+j) /2);
    }

    void quicksort(double list[], long m, long n)
    {
       long key,i,j,k;
       if( m < n)
       {
          k = choose_pivot(m, n);
          swap(&list[m], &list[k]);
          key = list[m];
          i = m+1;
          j = n;

          while(i <= j)
          {
             while((i <= n) && (list[i] <= key))
                i++;
             while((j >= m) && (list[j] > key))
                j--;
             if( i < j)
                swap(&list[i], &list[j]);
            }

          // swap two elements
          swap(&list[m], &list[j]);

          // recursively sort the lesser list
          quicksort(list, m, j-1);
          quicksort(list, j+1, n);
       }
    }

    """
#
#    stdwin = np.sort(window)
#    std = np.std(stdwin[:-half_window])
#    median = np.median(window)
#
#    plus_threshold = median + (std * sensitivity)
#    minus_threshold = median - (std * sensitivity)
#
#    if intensity_array[i] > plus_threshold or intensity_array[i] < minus_threshold:
#        intensity_array[i] = median


    ravg = ext_tools.ext_function('ravg', code,
                                  ['readoutNoiseFound', 'readoutN',
                                   'readoutNoise_mask', 'xlen',
                                   'ylen','x_c','y_c', 'hist',
                                   'low_q', 'high_q', 'in_image',
                                   'hist_count', 'mask', 'qmatrix',
                                   'dezingering', 'dezing_sensitivity'],
                                   type_converters = converters.blitz)

    ravg.customize.add_support_code(code2)

    mod.add_function(ravg)

    #SYSTEM TEMP DIR MIGHT NOT HAVE WRITE PERMISSION OR HAS SPACES IN IT => FAIL!
    #EXTREMELY ANNOYING THAT THE TEMP DIR CAN'T BE SET FROM mod.compile()! .. This is a work around:

    kw, file = mod.build_kw_and_file('.', {})

    success = build_tools.build_extension(file, temp_dir = temp_dir,
                                              compiler_name = 'gcc',
                                              verbose = 0, **kw)

    if success:
        print '\n****** ravg_ext module compiled succesfully! *********\n'


def build_polygonmask():
    print 'Compiling polymask_ext...'

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
    success = build_tools.build_extension(file, temp_dir = temp_dir,
                                              compiler_name = 'gcc',
                                              verbose = 0, **kw)

    if success:
        print '\n****** polymask_ext module compiled succesfully! *********\n'




def buildAll():

    try:
        #workdir = os.getcwd()
        workdir = sys.path[0]
        os.mkdir(os.path.join(workdir, 'temp'))
    except:
        pass

    try:
        build_radavg()
        build_polygonmask()
        build_bift()
    except Exception, e:
        print e
        print 'Failed to compile extensions ravg, polygonmask, bift!'

        try:
            shutil.rmtree('./temp/')
            os.remove('./bift_ext.cpp')
            os.remove('./ravg_ext.cpp')
            os.remove('./polygonmask_ext.cpp')
        except Exception, e:
            print 'Cleanup failed : ', e

        return


    print ''
    print '*********** Cleaning Up *****************'

    ## Clean up:

    try:
        shutil.rmtree('./temp/')
        os.remove('./bift_ext.cpp')
        os.remove('./ravg_ext.cpp')
        os.remove('./polygonmask_ext.cpp')
    except Exception, e:
        print 'Cleanup failed : ', e

    print ''
    print '*********** ALL DONE!!! *****************'

    #sys.exit()
    return

if __name__ == "__main__":
    buildAll()

