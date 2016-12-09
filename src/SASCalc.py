"""
Created on December 12, 2015

@author: Jesse B. Hopkins


The purpose of this module is to contain functions for calculating
values from SAXS profiles. These are intended to be automated
functions, including calculation of rg and molecular weight.


"""
import numpy as np
import scipy.interpolate as interp
from scipy import integrate as integrate
import os, copy
import SASExceptions
import time
import subprocess
import scipy.optimize
import wx
import threading
import Queue
import platform
import SASFileIO

def autoRg(sasm):
    #This function automatically calculates the radius of gyration and scattering intensity at zero angle
    #from a given scattering profile. It roughly follows the method used by the autorg function in the atsas package

    q = sasm.q
    i = sasm.i
    err = sasm.err

    #Pick the start of the RG fitting range. Note that in autorg, this is done
    #by looking for strong deviations at low q from aggregation or structure factor
    #or instrumental scattering, and ignoring those. This function isn't that advanced
    #so we start at 0.
    data_start = 0

    #Following the atsas package, the end point of our search space is the q value
    #where the intensity has droped by an order of magnitude from the initial value.
    data_end = np.abs(i-i[data_start]/10).argmin()

    #This makes sure we're not getting some weird fluke at the end of the scattering profile.
    if data_end > len(q)/2.:
        found = False
        idx = 0
        while not found:
            idx = idx +1
            if i[idx]<i[0]/10:
                found = True
            elif idx == len(q) -1:
                found = True
        data_end = idx

    #Define the fit function
    f = lambda x, a, b: a+b*x

    #Start out by transforming as usual.
    qs = np.square(q)
    il = np.log(np.absolute(i))
    iler = np.log(err)

    #Pick a minimum fitting window size. 10 is consistent with atsas autorg.
    min_window = 10

    max_window = data_end-data_start

    fit_list = []

    #It is very time consuming to search every possible window size and every possible starting point.
    #Here we define a subset to search.
    tot_points = max_window
    window_step = tot_points/10
    data_step = tot_points/50

    if window_step == 0:
        window_step =1
    if data_step ==0:
        data_step =1

    window_list = range(min_window,max_window, window_step)
    window_list.append(max_window)


    #This function takes every window size in the window list, stepts it through the data range, and
    #fits it to get the RG and I0. If basic conditions are met, qmin*RG<1 and qmax*RG>1.3, and RG>0.1,
    #We keep the fit.
    for w in window_list:
        for start in range(data_start,data_end-w, data_step):
            opt, cov = scipy.optimize.curve_fit(f, qs[start:start+w], il[start:start+w], sigma = iler[start:start+w])

            if opt[1] < 0 and np.isreal(opt[1]) and np.isreal(opt[0]):
                RG=np.sqrt(-3.*opt[1])
                I0=np.exp(opt[0])

                if q[start]*RG < 1 and q[start+w]*RG<1.3 and RG>0.1:

                    #error in rg and i0 is calculated by noting that q(x)+/-Dq has Dq=abs(dq/dx)Dx, where q(x) is your function you're using 
                    #on the quantity x+/-Dx, with Dq and Dx as the uncertainties and dq/dx the derviative of q with respect to x.
                    RGer=np.absolute(0.5*(np.sqrt(-3/opt[1])))*np.sqrt(np.absolute(cov[1,1,]))
                    I0er=I0*np.sqrt(np.absolute(cov[0,0]))

                    if RGer/RG <= 1:

                        a = opt[0]
                        b = opt[1]

                        r_sqr = 1 - np.square(il[start:start+w]-f(qs[start:start+w], a, b)).sum()/np.square(il[start:start+w]-il[start:start+w].mean()).sum()

                        if r_sqr > .15:
                            chi_sqr = np.square((il[start:start+w]-f(qs[start:start+w], a, b))/iler[start:start+w]).sum()

                            #All of my reduced chi_squared values are too small, so I suspect something isn't right with that.
                            #Values less than one tend to indicate either a wrong degree of freedom, or a serious overestimate
                            #of the error bars for the system.
                            dof = w - 2.
                            reduced_chi_sqr = chi_sqr/dof

                            fit_list.append([start, w, q[start], q[start+w], RG, RGer, I0, I0er, q[start]*RG, q[start+w]*RG, r_sqr, chi_sqr, reduced_chi_sqr])

    #Extreme cases: may need to relax the parameters.
    if len(fit_list)<1:
        #Stuff goes here
        pass

    if len(fit_list)>0:
        fit_list = np.array(fit_list)

        #Now we evaluate the quality of the fits based both on fitting data and on other criteria.

        #Choice of weights is pretty arbitrary. This set seems to yield results similar to the atsas autorg
        #for the few things I've tested.
        qmaxrg_weight = 1
        qminrg_weight = 1
        rg_frac_err_weight = 1
        i0_frac_err_weight = 1
        r_sqr_weight = 4
        reduced_chi_sqr_weight = 0
        window_size_weight = 4

        weights = np.array([qmaxrg_weight, qminrg_weight, rg_frac_err_weight, i0_frac_err_weight, r_sqr_weight, 
                            reduced_chi_sqr_weight, window_size_weight])

        quality = np.zeros(len(fit_list))

        max_window_real = float(window_list[-1])

        all_scores = []

        #This iterates through all the fits, and calculates a score. The score is out of 1, 1 being the best, 0 being the worst.
        for a in range(len(fit_list)):
            #Scores all should be 1 based. Reduced chi_square score is not, hence it not being weighted.

            qmaxrg_score = fit_list[a,9]/1.3
            qminrg_score = 1-fit_list[a,8]
            rg_frac_err_score = 1-fit_list[a,5]/fit_list[a,4]
            i0_frac_err_score = 1 - fit_list[a,7]/fit_list[a,6]
            r_sqr_score = fit_list[a,10]
            reduced_chi_sqr_score = 1/fit_list[a,12] #Not right
            window_size_score = fit_list[a,1]/max_window_real

            scores = np.array([qmaxrg_score, qminrg_score, rg_frac_err_score, i0_frac_err_score, r_sqr_score, 
                               reduced_chi_sqr_score, window_size_score])

            # print scores

            total_score = (weights*scores).sum()/weights.sum()

            quality[a] = total_score

            all_scores.append(scores)


        #I have picked an aribtrary threshold here. Not sure if 0.5 is a good quality cutoff or not.
        if quality.max() > .6:
            # idx = quality.argmax()
            # rg = fit_list[idx,4]
            # rger1 = fit_list[idx,5]
            # i0 = fit_list[idx,6]
            # i0er = fit_list[idx,7]
            # idx_min = fit_list[idx,0]
            # idx_max = fit_list[idx,0]+fit_list[idx,1]

            # try:
            #     #This adds in uncertainty based on the standard deviation of values with high quality scores
            #     #again, the range of the quality score is fairly aribtrary. It should be refined against real
            #     #data at some point.
            #     rger2 = fit_list[:,4][quality>quality[idx]-.1].std()
            #     rger = rger1 + rger2
            # except:
            #     rger = rger1
            try:
                idx = quality.argmax()
                rg = fit_list[:,4][quality>quality[idx]-.1].mean()
                rger = fit_list[:,5][quality>quality[idx]-.1].std()
                i0 = fit_list[:,6][quality>quality[idx]-.1].mean()
                i0er = fit_list[:,7][quality>quality[idx]-.1].std()
                idx_min = fit_list[idx,0]
                idx_max = fit_list[idx,0]+fit_list[idx,1]
            except:
                idx = quality.argmax()
                rg = fit_list[idx,4]
                rger1 = fit_list[idx,5]
                i0 = fit_list[idx,6]
                i0er = fit_list[idx,7]
                idx_min = fit_list[idx,0]
                idx_max = fit_list[idx,0]+fit_list[idx,1]


        else:
            rg = -1
            rger = -1
            i0 = -1
            i0er = -1
            idx_min = -1
            idx_max = -1

    else:
        rg = -1
        rger = -1
        i0 = -1
        i0er = -1
        idx_min = -1
        idx_max = -1
        quality = []
        all_scores = []

    #We could add another function here, if not good quality fits are found, either reiterate through the
    #the data and refit with looser criteria, or accept lower scores, possibly with larger error bars.

    #returns Rg, Rg error, I0, I0 error, the index of the first q point of the fit and the index of the last q point of the fit
    return rg, rger, i0, i0er, idx_min, idx_max


def autoMW(sasm, rg, i0, protein = True):
    #using the rambo tainer 2013 method for molecular mass.
    #Need to properly calculater error!

    raw_settings = wx.FindWindowByName('MainFrame').raw_settings

    q = sasm.q
    i = sasm.i
    err = sasm.err

    #The volume of volume  is the ratio of i0 to $\int q*I dq$
    tot=integrate.simps(q*i,q)

    vc=i0/tot

    #We then take a ratio of the square of vc to rg
    qr=np.square(vc)/rg

    #The molecular weight is then determined in a power law relationship. Note, the 1000 puts it in kDa
    
    if protein:
        A = raw_settings.get('MWVcAProtein')
        B = raw_settings.get('MWVcBProtein')
        #For proteins:
        # mw=qr/0.1231/1000
    else:
        A = raw_settings.get('MWVcARna')
        B = raw_settings.get('MWVcBRna')
        #For RNA
        # mw = np.power(qr/0.00934, 0.808)/1000

    mw = (qr/B)**A/1000.

    return mw, np.sqrt(np.absolute(mw)), tot, vc, qr


def porodInvariant(sasm,start=0,stop=-1):
    return integrate.simps(sasm.i[start:stop]*np.square(sasm.q[start:stop]),sasm.q[start:stop])

def porodVolume(sasm, rg, i0, start = 0, stop = -1, interp = False):

    q_exp = sasm.q
    i_exp = sasm.i


    if interp:
        def f(x):
            i0*np.exp((-1./3.)*np.square(rg)*np.square(x))

        q_interp = np.arange(0,q_exp[0],100)

        i_interp = f(x)

        q = np.concatenate((q_interp,q_exp))
        i = np.concatenate((i_interp,i_exp))
    else:
        q = q_exp
        i = i_exp

    pInvar = integrate.simps(i[start:stop]*np.square(q[start:stop]),q[start:stop])

    pVolume = 2*np.square(np.pi)*i0/pInvar

    return pVolume


def runGnom(fname, outname, dmax, args, cfg = True):
    #This program runs GNOM from the atsas package. It can do so without writing a GNOM cfg file.
    #It takes as input the filename to run GNOM on, the output name from the GNOM file, the dmax to evaluate
    #at, and a dictionary of arguments, which can be used to set the optional GNOM arguments.
    #Using the GNOM cfg file is significantly faster than catching the interactive input and pass arguments there.

    #Solution for non-blocking reads adapted from stack overflow
    #http://stackoverflow.com/questions/375427/non-blocking-read-on-a-subprocess-pipe-in-python
    def enqueue_output(out, queue):
        line = 'test'
        line2=''
        while line != '':
            line = out.read(1)
            line2+=line
            if line == ':':
                queue.put_nowait([line2])
                line2=''

        out.close()

    raw_settings = wx.FindWindowByName('MainFrame').raw_settings
    atsasDir = raw_settings.get('ATSASDir')

    opsys = platform.system()
    if opsys == 'Windows':
        gnomDir = os.path.join(atsasDir, 'gnom.exe')
    else:
        gnomDir = os.path.join(atsasDir, 'gnom')

    datadir = os.path.dirname(fname)

    if cfg:
        writeGnomCFG(fname, outname, dmax, args)

    if os.path.exists(gnomDir):

        if cfg:
            proc = subprocess.Popen('%s' %(gnomDir), shell=True, stdin = subprocess.PIPE, stdout = subprocess.PIPE, stderr = subprocess.STDOUT)
            proc.communicate('\r\n')

        else:
            if os.isfile(os.path.join(datadir, 'gnom.cfg')):
                os.remove(os.path.join(datadir, 'gnom.cfg'))

            gnom_q = Queue.Queue()

            proc = subprocess.Popen('%s' %(gnomDir), shell=True, stdin = subprocess.PIPE, stdout = subprocess.PIPE, stderr = subprocess.STDOUT)
            gnom_t = threading.Thread(target=enqueue_output, args=(proc.stdout, gnom_q))
            gnom_t.daemon = True
            gnom_t.start()

            while proc.poll() == None:
                data = None
                try: 
                    data = gnom_q.get_nowait()
                    data = data[0]
                    # print 'New Line of Data!!!!!!!!!!!!!!!!!!!'
                    # print data
                    gnom_q.task_done()
                    # err = q2.get_nowait()
                    # print data[0],
                    # print err
                except Queue.Empty:
                    pass

                if data != None:

                    if data.find('[ postscr     ] :') > -1:
                        proc.stdin.write('\r\n') #Printer type, default is postscr

                    elif data.find('Input data, first file') > -1:
                        proc.stdin.write('%s\r\n' %(fname)) #Input data, first file. No default.

                    elif data.find('Output file') > -1:
                        proc.stdin.write('%s\r\n' %(outname)) #Output file, default is gnom.out

                    elif data.find('No of start points to skip') > -1:
                        if 's_skip' in args and args['s_skip'] != '':
                            proc.stdin.write('%s\r\n' %(args['s_skip']))
                        else:
                            proc.stdin.write('\r\n') #Number of start points to skip, default is 0

                    elif data.find('Input data, second file') > -1:
                        proc.stdin.write('\r\n') #Input data, second file, default is none

                    elif data.find('No of end points to omit') > -1:
                        if 'e_skip' in args and args['e_skip'] != '':
                            proc.stdin.write('%s\r\n' %(args['e_skip']))
                        else:
                            proc.stdin.write('\r\n') #Number of end poitns to omit, default is 0

                    elif data.find('Default input errors level') > -1:
                        proc.stdin.write('\r\n') #Default input errors level, default 0.0

                    elif data.find('Angular scale') > -1:
                        if 'angular' in args and args['angular'] != '':
                            proc.stdin.write('%s\r\n' %(args['angular']))
                        else:
                            proc.stdin.write('\r\n') #Angular scale, default 1

                    elif data.find('Plot input data') > -1:
                        proc.stdin.write('n\r\n') #Plot input data, default yes

                    elif data.find('File containing expert parameters') > -1:
                        if 'expert' in args and args['expert'] != '':
                            proc.stdin.write('%s\r\n' %(args['expert']))
                        else:
                            proc.stdin.write('\r\n') #File containing expert parameters, default none

                    elif data.find('Kernel already calculated') > -1:
                        proc.stdin.write('\r\n') #Kernel already calculated, default no

                    elif data.find('Type of system') > -1:
                        if 'system' in args and args['system'] != '':
                            proc.stdin.write('%s\r\n' %(args['system']))
                        else:
                            proc.stdin.write('\r\n') #Type of system, default 0 (P(r) function)

                    elif data.find('Zero condition at r=rmin') > -1:
                        if 'rmin_zero' in args and args['rmin_zero'] != '':
                            proc.stdin.write('%s\r\n' %(args['rmin_zero']))
                        else:
                            proc.stdin.write('\r\n') #Zero condition at r=rmin, default is yes

                    elif data.find('Zero condition at r=rmax') > -1:
                        if 'rmax_zero' in args and args['rmax_zero'] != '':
                            proc.stdin.write('%s\r\n' %(args['rmax_zero']))
                        else:
                            proc.stdin.write('\r\n') #Zero condition at r=rmax, default is yes

                    elif data.find('Rmax for evaluating p(r)') > -1:
                        proc.stdin.write('%s\r\n' %(str(dmax))) #Rmax for evaluating p(r), no default (DMAX!)

                    elif data.find('Number of points in real space') != 101:
                        if 'npts' in args and args['npts'] != -1:
                            proc.stdin.write('%s\r\n' %(str(args['npts'])))
                        else:
                            proc.stdin.write('\r\n') #Number of points in real space, default is 111

                    elif data.find('Kernel-storage file name') > -1:
                        proc.stdin.write('\r\n') #Kernal-storage file name, default is kern.bin

                    elif data.find('Experimental setup') > -1:
                        proc.stdin.write('\r\n') #Experimental setup, default is 0 (no smearing)

                    elif data.find('Initial ALPHA') > -1:
                        if 'alpha' in args and args['alpha'] != 0.0:
                            proc.stdin.write('%s\r\n' %(str(args['alpha'])))
                        else:
                            proc.stdin.write('\r\n') #Initial ALPHA, default is 0.0

                    elif data.find('Plot alpha distribution') > -1:
                        proc.stdin.write('n\r\n') #Plot alpha distribution, default is yes

                    elif data.find('Plot results') > -1:
                        proc.stdin.write('n\r\n') #Plot results, default is no

                    elif data.find('Your choice') > -1:
                        proc.stdin.write('\r\n') #Choice when selecting one of the following options, CR for EXIT

                    elif data.find('Evaluate errors') > -1:
                        proc.stdin.write('\r\n') #Evaluate errors, default yes

                    elif data.find('Plot p(r) with errors') > -1:
                        proc.stdin.write('n\r\n') #Plot p(r) with errors, default yes

                    elif data.find('Next data set') > -1:
                        proc.stdin.write('\r\n') #Next data set, default no
        

        iftm=SASFileIO.loadOutFile(outname)[0]

        if cfg:
            try:
                os.remove(os.path.join(datadir, 'gnom.cfg'))
            except Exception as e:
                print e
                print 'GNOM cleanup failed to delete gnom.cfg!'

        try:
            os.remove(os.path.join(datadir, 'kern.bin'))
        except Exception as e:
            print e
            print 'GNOM cleanup failed to delete kern.bin!'

        # if os.path.isfile(outname):
        #     try:
        #         os.remove(outname)
        #     except Exception, e:
        #         print e
        #         print 'GNOM cleanup failed!'

        return iftm

    else:
        print 'Cannot find ATSAS'
        raise SASExceptions.NoATSASError('Cannot find gnom.')
        return None


def runDatgnom(datname, sasm):
    #This runs the ATSAS package DATGNOM program, to automatically find the Dmax and P(r) function 
    #of a scattering profile.
    analysis = sasm.getParameter('analysis')
    if 'guinier' in analysis:
        rg = float(analysis['guinier']['Rg'])
    else:
        rg = -1


    raw_settings = wx.FindWindowByName('MainFrame').raw_settings
    atsasDir = raw_settings.get('ATSASDir')

    opsys = platform.system()

    if opsys == 'Windows':
        datgnomDir = os.path.join(atsasDir, 'datgnom.exe')
    else:
        datgnomDir = os.path.join(atsasDir, 'datgnom')
    

    if os.path.exists(datgnomDir):

        outname = 't_datgnom.out'
        while os.path.isfile(outname):
            outname = 't'+outname

        if rg <= 0:
            process=subprocess.Popen('%s %s -o %s' %(datgnomDir, datname, outname), stdout=subprocess.PIPE,stderr=subprocess.PIPE,shell=True)
        else:
            process=subprocess.Popen('%s %s -o %s -r %f' %(datgnomDir, datname, outname, rg),stdout=subprocess.PIPE,stderr=subprocess.PIPE,shell=True)

        output, error = process.communicate()

        error = error.strip()
        
        if error == 'Cannot define Dmax' or error=='Could not find Rg':

            if rg <= 0:
                rg, rger, i0, i0er, idx_min, idx_max =autoRg(sasm)
                if rg>10:
                    process=subprocess.Popen('%s %s -o %s -r %f' %(datgnomDir, datname, outname, rg),stdout=subprocess.PIPE,stderr=subprocess.PIPE,shell=True)

                    output, error = process.communicate()
            else:
                # print 'No Dmax found, trying datgnom without an rg input'
                process=subprocess.Popen('%s %s -o %s' %(datgnomDir, datname, outname), stdout=subprocess.PIPE,stderr=subprocess.PIPE,shell=True)

                output, error = process.communicate()

        error = error.strip()


        if error == 'Cannot define Dmax' or error=='Could not find Rg' or error=='No intensity values (positive) found' or error == 'LOADATF --E- No data lines recognized.':
            print 'Unable to run datgnom successfully'
            datgnom_success = False
        # elif error != None:
        #     datgnom_success = False
        else:
            datgnom_success = True

        # print 'DATGNOM output:'
        # print output

        if datgnom_success:
            iftm=SASFileIO.loadOutFile(outname)[0]
        else:
            iftm = None

        if os.path.isfile(outname):
            try:
                os.remove(outname)
            except Exception, e:
                print e
                print 'DATGNOM cleanup failed to remove the .out file!'

        return iftm

    else:
        print 'Cannot find ATSAS'
        raise SASExceptions.NoATSASError('Cannot find datgnom.')


def writeGnomCFG(fname, outname, dmax, args):
    #This writes the GNOM CFG file, using the arguments passed into the function.
    datadir = os.path.dirname(fname)

    f = open(os.path.join(datadir, 'gnom.cfg'),'w')
    
    f.write('This line intentionally left blank\n')
    f.write('PRINTER C [      postscr     ]  Printer type\n')
    if 'form' in args and args['form'] != '':
        f.write('FORFAC  C [         %s         ]  Form factor file (valid for JOB=2)\n' %s(args['form']))
    else:
        f.write('FORFAC  C [                  ]  Form factor file (valid for JOB=2)\n')
    if 'expert' in args and args['expert'] != '':
        f.write('EXPERT  C [     %s         ]  File containing expert parameters\n' %(args['expert']))
    else:
        f.write('EXPERT  C [     none         ]  File containing expert parameters\n')
    f.write('INPUT1  C [        %s        ]  Input file name (first file)\n' %(fname))
    f.write('INPUT2  C [       none       ]  Input file name (second file)\n')
    f.write('NSKIP1  I [       0         ]  Number of initial points to skip\n')
    f.write('NSKIP2  I [        0         ]  Number of final points to skip\n')
    f.write('OUTPUT  C [       %s         ]  Output file\n' %(outname))
    if 'angular' in args and args['angular'] != 1:
        f.write('ISCALE  I [       %s         ]  Angular scale of input data\n' %(args['angular']))
    else:
        f.write('ISCALE  I [        1         ]  Angular scale of input data\n')
    f.write('PLOINP  C [       n          ]  Plotting flag: input data (Y/N)\n')
    f.write('PLORES  C [       n          ]  Plotting flag: results    (Y/N)\n')
    f.write('EVAERR  C [       y          ]  Error flags: calculate errors   (Y/N)\n')
    f.write('PLOERR  C [       n          ]  Plotting flag: p(r) with errors (Y/N)\n')
    f.write('PLOALPH C [       n          ]  Plotting flag: alpha distribution (Y/N)\n')
    f.write('LKERN   C [       n          ]  Kernel file status (Y/N)\n')
    if 'system' in args and args['system'] != 0:
        f.write('JOBTYP  I [       %s         ]  Type of system (0/1/2/3/4/5/6)\n' %(args['system']))
    else:
        f.write('JOBTYP  I [       0          ]  Type of system (0/1/2/3/4/5/6)\n')
    if 'rmin' in args and args['rmin'] != -1:
        f.write('RMIN    R [        %s         ]  Rmin for evaluating p(r)\n' %(args['rmin']))
    else:
        f.write('RMIN    R [                 ]  Rmin for evaluating p(r)\n')
    f.write('RMAX    R [        %s        ]  Rmax for evaluating p(r)\n' %(str(dmax)))
    if 'rmin_zero' in args and args['rmin_zero'] != '':
        f.write('LZRMIN  C [      %s          ]  Zero condition at r=RMIN (Y/N)\n' %(args['rmin_zero']))
    else:
        f.write('LZRMIN  C [       Y          ]  Zero condition at r=RMIN (Y/N)\n')
    if 'rmax_zero' in args and args['rmax_zero'] != '':
        f.write('LZRMAX  C [      %s          ]  Zero condition at r=RMAX (Y/N)\n' %(args['rmax_zero']))
    else:
        f.write('LZRMAX  C [       Y          ]  Zero condition at r=RMAX (Y/N)\n')
    f.write('KERNEL  C [       kern.bin   ]  Kernel-storage file\n')
    f.write('DEVIAT  R [      0.0         ]  Default input errors level\n')
    f.write('IDET    I [       0          ]  Experimental set up (0/1/2)\n')
    f.write('FWHM1   R [       0.0        ]  FWHM for 1st run\n')
    f.write('FWHM2   R [                  ]  FWHM for 2nd run\n')
    f.write('AH1     R [                  ]  Slit-height parameter AH (first  run)\n')
    f.write('LH1     R [                  ]  Slit-height parameter LH (first  run)\n')
    f.write('AW1     R [                  ]  Slit-width  parameter AW (first  run)\n')
    f.write('LW1     R [                  ]  Slit-width  parameter LW (first  run)\n')
    f.write('AH2     R [                  ]  Slit-height parameter AH (second run)\n')
    f.write('LH2     R [                  ]  Slit-height parameter LH (second run)\n')
    f.write('AW2     R [                  ]  Slit-width  parameter AW (second run)\n')
    f.write('LW2     R [                  ]  Slit-width  parameter LW (second run)\n')
    f.write('SPOT1   C [                  ]  Beam profile file (first run)\n')
    f.write('SPOT2   C [                  ]  Beam profile file (second run)\n')
    if 'alpha' in args and args['alpha'] !=0.0:
        f.write('ALPHA   R [      %s         ]  Initial ALPHA\n' %s(str(args['alpha'])))
    else:
        f.write('ALPHA   R [      0.0         ]  Initial ALPHA\n')
    if 'npts' in args and args['npts'] !=101:
        f.write('NREAL   R [       %s        ]  Number of points in real space\n' %(str(args['npts'])))
    else:
        f.write('NREAL   R [       101        ]  Number of points in real space\n')
    f.write('COEF    R [                  ]\n')
    if 'radius56' in args and args['radius56'] != -1:
        f.write('RAD56   R [         %s         ]  Radius/thickness (valid for JOB=5,6)\n' %(args['radius56']))
    else:
        f.write('RAD56   R [                  ]  Radius/thickness (valid for JOB=5,6)\n')
    f.write('NEXTJOB C [        n         ]\n')


    f.close()


def runDammif(fname, prefix, args):
    #Note: This run dammif command must be run with the current working directory as the directory
    #where the file is located. Otherwise, there are issues if the filepath contains a space.

    fname = os.path.split(fname)[1]

    raw_settings = wx.FindWindowByName('MainFrame').raw_settings
    atsasDir = raw_settings.get('ATSASDir')

    opsys = platform.system()

    if opsys == 'Windows':
        dammifDir = os.path.join(atsasDir, 'dammif.exe')
    else:
        dammifDir = os.path.join(atsasDir, 'dammif')
    

    if os.path.exists(dammifDir):
        if args['mode'].lower() == 'fast' or args['mode'].lower() == 'slow':

            command = '%s --quiet --mode=%s --prefix=%s --unit=%s --symmetry=%s --anisometry=%s' %(dammifDir, args['mode'], prefix, args['unit'], args['sym'], args['anisometry'])
            if args['omitSolvent']:
                command = command + ' --omit-solvent'
            if args['chained']:
                command = command + ' --chained'
            if args['constant'] != '':
                command = command + ' --constant=%s' %(args['constant'])

            command = command + ' %s' %(fname)
            
            process=subprocess.Popen(command, shell= True)

            return process

        else:
            #Solution for non-blocking reads adapted from stack overflow
            #http://stackoverflow.com/questions/375427/non-blocking-read-on-a-subprocess-pipe-in-python
            def enqueue_output(out, queue):
                dammifRunning = False
                line = 'test'
                line2=''
                while line != '' and not dammifRunning:
                    line = out.read(1)
                    line2+=line
                    if line == ':':
                        if line2.find('Log opened') > -1:
                            dammifRunning = True
                        queue.put_nowait([line2])
                        line2=''

            dammif_q = Queue.Queue()

            dammifStarted = False

            proc = subprocess.Popen('%s' %(dammifDir), shell = True, stdin = subprocess.PIPE, stdout = subprocess.PIPE, stderr = subprocess.STDOUT)
            dammif_t = threading.Thread(target=enqueue_output, args=(proc.stdout, dammif_q))
            dammif_t.daemon = True
            dammif_t.start()
            previous_line = ''

            

            while proc.poll() == None and not dammifStarted:
                data = None
                try: 
                    data = dammif_q.get_nowait()
                    data = data[0]
                    # print 'New Line of Data!!!!!!!!!!!!!!!!!!!'
                    # print data
                    dammif_q.task_done()
                    # err = q2.get_nowait()
                    # print data[0],
                    # print err
                except Queue.Empty:
                    pass

                if data != None:
                    current_line = data
                    # print 'Previous line: %s' %(previous_line)
                    if data.find('GNOM output file to read?') > -1:
                        proc.stdin.write('%s\r\n' %(fname)) #Dammif input file, no default
                   
                    elif previous_line.find('nanometer') > -1:
                        proc.stdin.write('%s\r\n' %(args['unit'])) #Dammif input file units, default unknown
                    
                    elif previous_line.find('Output file prefix?') > -1:
                        proc.stdin.write('%s\r\n' %(prefix)) #Dammif output file prefix, default dammif
                    
                    elif previous_line.find('Omit output of solvent') > -1:
                        if args['omitSolvent']:
                            proc.stdin.write('%s\r\n' %('no')) #Omit solvent bead output file, default yes
                        else:
                            proc.stdin.write('\r\n')
                    
                    elif previous_line.find('Create pseudo chains') > -1:
                        if args['chained']:
                            proc.stdin.write('%s\r\n' %('yes')) #Make pseudo chains, default no
                        else:
                            proc.stdin.write('\r\n')

                    elif data.find('p1)') > -1:
                        proc.stdin.write('%s\r\n' %(args['sym'])) #Particle symmetry, default P1

                    elif previous_line.find('prolate, (o) oblate') > -1:
                        proc.stdin.write('%s\r\n' %(args['anisometry'])) #Particle anisometry, default Unknown

                    elif data.find('for automatic (default)') > -1:
                        if args['constant'] != '':
                            proc.stdin.write('%s\r\n' %(args['constant'])) #Subtract constant offset, default automatic
                        else:
                            proc.stdin.write('\r\n')

                    elif previous_line.find('(s) slow') > -1:
                        proc.stdin.write('i\r\n') #Annealing setup, default slow

                    elif previous_line.find('Maximum bead count') > -1:
                        if args['maxBead'] > -1:
                            proc.stdin.write('%i\r\n' %(args['maxBead'])) #Maximum beads to be used, default unlimited
                        else:
                            proc.stdin.write('\r\n')

                    elif previous_line.find('Dummy atom radius?') > -1:
                        if args['radius'] > -1:
                            proc.stdin.write('%f\r\n' %(args['radius'])) #Dummy atom radius, default 1.0
                        else:
                            proc.stdin.write('\r\n')

                    elif previous_line.find('Maximum number of spherical harmonics') > -1:
                        if args['harmonics'] > -1:
                            proc.stdin.write('%i\r\n' %(args['harmonics'])) #Maximum number of spherical harmonics to use (1-50), default 20
                        else:
                            proc.stdin.write('\r\n')

                    elif previous_line.find('Proportion of the curve to be fitted') > -1:
                        if args['propFit'] > -1:
                            proc.stdin.write('%f\r\n' %(args['propFit'])) #Proportion of curve to be fitted, default 1.00
                        else:
                            proc.stdin.write('\r\n')

                    elif data.find('emphasised porod)') > -1:
                        if args['curveWeight'] != '':
                            proc.stdin.write('%s\r\n' %(args['curveWeight'])) #Curve weighting function, default emphasised porod
                        else:
                            proc.stdin.write('\r\n')

                    elif previous_line.find('Initial random seed?') > -1:
                        if args['seed'] != '':
                            proc.stdin.write('%s\r\n' %(args['seed'])) #Initial random seed, default current time
                        else:
                            proc.stdin.write('\r\n')

                    elif previous_line.find('Maximum number of temperature steps') > -1:
                        if args['maxSteps'] > -1:
                            proc.stdin.write('%i\r\n' %(args['maxSteps'])) #Maximum number of temperature steps, default 200
                        else:
                            proc.stdin.write('\r\n')

                    elif previous_line.find('Minimum number of successes') > -1:
                        if args['minSuccess'] > -1:
                            proc.stdin.write('%i\r\n' %(args['minSuccess'])) #Minimum number of success per temperature step to continue, default 200
                        else:
                            proc.stdin.write('\r\n')

                    elif previous_line.find('Maximum number of iterations within a single temperature step?') > -1:
                        if args['maxIters'] > -1:
                            proc.stdin.write('%i\r\n' %(args['maxIters'])) #Maximum number of iterations per temperature step, default 200000
                        else:
                            proc.stdin.write('\r\n')

                    elif previous_line.find('is decreased?') > -1:
                        if args['maxSuccess'] > -1:
                            proc.stdin.write('%i\r\n' %(args['maxSuccess'])) #Maximum number of successes per T step, before T is decrease, defaul 20000
                        else:
                            proc.stdin.write('\r\n')

                    elif previous_line.find('Temperature schedule factor?') > -1:
                        if args['TFactor'] > -1:
                            proc.stdin.write('%f\r\n' %(args['TFactor'])) #Maximum number of successes per T step, before T is decrease, defaul 20000
                        else:
                            proc.stdin.write('\r\n')

                    elif previous_line.find('Rg penalty weight?') > -1:
                        if args['RgWeight'] > -1:
                            proc.stdin.write('%f\r\n' %(args['RgWeight'])) #Maximum number of successes per T step, before T is decrease, defaul 20000
                        else:
                            proc.stdin.write('\r\n')

                    elif previous_line.find('Center penalty weight?') > -1:
                        if args['cenWeight'] > -1:
                            proc.stdin.write('%f\r\n' %(args['cenWeight'])) #Maximum number of successes per T step, before T is decrease, defaul 20000
                        else:
                            proc.stdin.write('\r\n')

                    elif previous_line.find('Looseness penalty weight?') > -1:
                        if args['looseWeight'] > -1:
                            proc.stdin.write('%f\r\n' %(args['looseWeight'])) #Maximum number of successes per T step, before T is decrease, defaul 20000
                        else:
                            proc.stdin.write('\r\n')
                    elif data.find('Log opened') > -1:
                        dammifStarted = True

                    previous_line = current_line

            proc.stdout.close()
            proc.stdin.close()

            return proc
    else:
        print 'Cannot find ATSAS'
        raise SASExceptions.NoATSASError('Cannot find dammif.')
        return None


def runDamaver(flist):

    raw_settings = wx.FindWindowByName('MainFrame').raw_settings
    atsasDir = raw_settings.get('ATSASDir')

    opsys = platform.system()

    if opsys == 'Windows':
        damaverDir = os.path.join(atsasDir, 'damaver.exe')
    else:
        damaverDir = os.path.join(atsasDir, 'damaver')
    

    if os.path.exists(damaverDir):
        command = '%s --automatic' %(damaverDir)

        for item in flist:
            command = command + ' %s' %(item)
        
        process=subprocess.Popen(command, shell= True, stdout = subprocess.PIPE)

        return process

def runAmbimeter(fname, prefix, args):
    raw_settings = wx.FindWindowByName('MainFrame').raw_settings
    atsasDir = raw_settings.get('ATSASDir')

    opsys = platform.system()

    if opsys == 'Windows':
        ambimeterDir = os.path.join(atsasDir, 'ambimeter.exe')
    else:
        ambimeterDir = os.path.join(atsasDir, 'ambimeter')
    
    if os.path.exists(ambimeterDir):
        command = '%s --srg=%s --prefix=%s --files=%s %s' %(ambimeterDir, args['sRg'], prefix, args['files'], fname)
        process=subprocess.Popen(command, shell= True, stdout=subprocess.PIPE,stderr=subprocess.PIPE)

        start = time.time()
        while process.poll() == None:
            if time.time()-start > 60:
                raise SASExceptions.NoATSASError('Ambimeter timed out. Try running it from the command line to diagnose this problem.')
                return None

        output, error = process.communicate()

        lines = output.split('\n')
        ambiCats = lines[0].split(':')[-1].strip()
        ambiScore = lines[1].split(':')[-1].strip()
        ambiEval = lines[2]

        return ambiCats, ambiScore, ambiEval

    else:
        print 'Cannot find ATSAS'
        raise SASExceptions.NoATSASError('Cannot find ambimeter.')
        return None

def runDamclust(flist):

    raw_settings = wx.FindWindowByName('MainFrame').raw_settings
    atsasDir = raw_settings.get('ATSASDir')

    opsys = platform.system()

    if opsys == 'Windows':
        damclustDir = os.path.join(atsasDir, 'damclust.exe')
    else:
        damclustDir = os.path.join(atsasDir, 'damclust')
    

    if os.path.exists(damclustDir):
        command = '%s' %(damclustDir)

        for item in flist:
            command = command + ' %s' %(item)
        
        process=subprocess.Popen(command, shell= True, stdout = subprocess.PIPE)

        return process