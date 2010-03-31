import numpy as np
cimport numpy as np
cimport cython

@cython.boundscheck(False)
@cython.wraparound(False)

def say_hello_to(name):
	print("Hello %s!" % name)
	
cdef extern from "math.h":
		double sqrt(double)
		
def myfuncSanityCheck(in_image, x_c, y_c):

	if in_image is None:
		raise ValueError("Input image matrix can not be None")
	if x_c is None or y_c is None:
		raise ValueError("x and y center coordinates can not be None")
		
	if x_c < 0 or x_c > in_image.shape[0]-1:
		raise ValueError("X center coordiante " + str(x_c) +
		 				 " is not within allowed limits of " +
		 				 "0 to " + str(in_image.shape[0]-1))
	if y_c < 0 or y_c > in_image.shape[1]-1:
		raise ValueError("Y center coordiante " + str(y_c) +
		 				 " is not within allowed limits of " +
		 				 "0 to " + str(in_image.shape[1]-1))
	
def myfunc(np.ndarray[np.float64_t, ndim = 2] in_image,
					np.float64_t x_c,
					np.float64_t y_c,
					np.ndarray[np.float64_t, ndim = 2] mask = None,
					np.ndarray[np.float64_t, ndim = 2] readoutNoise_mask = None):
	
	myfuncSanityCheck(in_image, x_c, y_c)
	
	cdef int maxQlength 
	cdef Py_ssize_t x, y    
	cdef np.float64_t rel_x, rel_y, xlen, ylen
	cdef np.float64_t zinger_threshold = 65500
	cdef int low_q_limit, high_q_limit, r
	
	xlen = in_image.shape[0]
	ylen = in_image.shape[1]
	
	maxQlength = <int> max(xlen - x_c, ylen - y_c, xlen - (xlen - x_c), ylen - (ylen - y_c))
	
	high_q_limit = maxQlength
	low_q_limit = 0
	
	cdef np.ndarray[np.float64_t, ndim=1] hist = \
		np.zeros((maxQlength), dtype = np.float64)
	
	cdef np.ndarray[np.float64_t, ndim=1] hist_count = \
		np.zeros((maxQlength), dtype = np.float64)
	
	for x in range(in_image.shape[0]):
		for y in range(in_image.shape[1]):
		
			rel_x = x-x_c
			rel_y = y_c-y
			
			r = <int> sqrt((rel_y*rel_y) + (rel_x*rel_x))
			
			if r < high_q_limit and r > low_q_limit: #and in_image[x,y] < zinger_threshold and in_image[x,y] > 0:
				hist[r] = hist[r] + in_image[x,y]        #/* Integration of pixel values */
				hist_count[r] = hist_count[r] + 1
	
	
	
				
	return hist, hist_count		
	

#def rad(np.ndarray[np.float64_t, ndim=2] in_image):
	
#	for i in range(0,in_image.shape[0]):
#		print i
		
    
    
    
    
    
    
    #nparray hist, savedPixels, hist_count, in_image, readoutN, readoutNoise_mask
     
    #cdef double rel_x, rel_y, r
    #cdef int x, y, xlen, ylen, idx, zinger_threshold, readoutNoiseFound
    
 #   for( x = 0; x < xlen; x++)
 #          for( y = 0; y < ylen; y++)
 #          {
 #               rel_x = x-x_c;
 #               rel_y = y_c-y;
 #          
 #               r = std::sqrt((rel_y*rel_y) + (rel_x*rel_x));
 #               //res(x,y) = r;
 #   
 #               if( int(r) < high_q-1 && int(r) > low_q && mask(x,y) == 1 && in_image(x,y) < zinger_threshold && in_image(x,y) > 0)
 #               {
 #                   /* res2(x,y) = int(r); */                           /*  A test image, gives the included range image */
 #                   hist(int(r)) = hist(int(r)) + in_image(x,y);        /* Integration of pixel values */
 #                   idx = hist_count(int(r));
 #                   savedPixels(int(r),idx) = in_image(x,y);
 #                   hist_count(int(r)) = hist_count(int(r)) + 1;        /* Number of pixels in a bin */      
 #               
 #               }
 #               
 #               if ( readoutNoiseFound == 1 && int(r) < high_q-1 && int(r) > low_q && readoutNoise_mask(x,y) == 0 && in_image(x,y) < zinger_threshold)
 #               {
 #                   readoutN(0,0) = readoutN(0,0) + 1;
 #                   readoutN(0,1) = readoutN(0,1)     + in_image(x,y);
 #                   savedPixelsRN(int(r), idx) = in_image(x,y);
 #               }
 #           
 #           }
 
 