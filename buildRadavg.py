from scipy.weave import ext_tools
from scipy.weave import converters
import numpy as np
from scipy import weave
from scipy.weave import build_tools
import os

def build_fibonacci():
    """ Builds an extension module with fibonacci calculators.
    """
    mod = ext_tools.ext_module('fibonacci_ext')
    a = 1 # this is effectively a type declaration

    # recursive fibonacci in C
    fib_code = """
                   int fib1(int a)
                   {
                       if(a <= 2)
                           return 1;
                       else
                           return fib1(a-2) + fib1(a-1);
                   }
               """
    ext_code = """
                   int val = fib1(a);
                   return_val = val;
               """
    fib = ext_tools.ext_function('fib',ext_code,['a'])
    fib.customize.add_support_code(fib_code)
    mod.add_function(fib)

    #mod.compile()
    
    kw,file = mod.build_kw_and_file('.', {})
    
    success = build_tools.build_extension(file, temp_dir = os.path.join('.', 'temp'),
                                              compiler_name = 'gcc',
                                              verbose = 0, **kw)

   
def build_radavg():

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

#    maxPointsPrQ = 40
#    savedPixels = np.ones((10, maxPointsPrQ), dtype = np.float64) * -1
#    savedPixelsRN = np.ones((10, maxPointsPrQ), dtype = np.float64) * -1
    
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
  
    ravg = ext_tools.ext_function('ravg', code, ['readoutNoiseFound', 'readoutN', 'readoutNoise_mask', 'xlen','ylen','x_c','y_c', 'hist', 'low_q', 'high_q', 'in_image', 'hist_count', 'mask'], type_converters = converters.blitz)
    mod.add_function(ravg)
    
    #SYSTEM TEMP DIR MIGHT NOT HAVE WRITE PERMISSION OR HAS SPACES IN IT = FAIL!
    #EXTREMELY ANNOYING THAT THE TEMP DIR CAN'T BE SET FROM mod.compile()! .. This is a work around:
    
    kw, file = mod.build_kw_and_file('.', {})
    
    success = build_tools.build_extension(file, temp_dir = './temp/',
                                              compiler_name = 'gcc',
                                              verbose = 0, **kw)
   
    if success:
        print '\n\n****** ravg_ext module compiled succesfully! *********'


if __name__ == "__main__":
    
    
    if os.path.isfile('ravg_ext.so'):
        os.remove('ravg_ext.so')
    if os.path.isfile('ravg_ext.cpp'):
        os.remove('ravg_ext.cpp')
    
    build_radavg()


    
    
    
    
    
    
