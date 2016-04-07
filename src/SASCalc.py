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


def runAutoRg(sasm, start=-1, end=-1, initialrg=-1):

    #This function runs the atsas autorg function. It is currently not used in the program, but could be useful
    #if the program is ever tied more closely to that software package.

    #save the file in the current working directory
    q = sasm.q
    i = sasm.i
    err = sasm.err
    tname='temp.dat'
    f=open(tname,'w')
    for a in range(len(q)):
        f.write(str(q[a]) + ' ' + str(i[a]) + ' ' + str(err[a])+'\n')
    f.close()

    done=False

    # print tname

    while not done:
        done=os.path.isfile(tname)
        time.sleep(0.01)

    process=subprocess.Popen('autorg ' + tname, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    process.wait()
    output=process.stdout.read().split('\n')
    # print output
    # print output[0]

    process=subprocess.Popen('rm -f '+tname, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    process.wait()

    if output[0] != '' and not output[0].startswith('No Rg'):
        rgt=output[0]
        I0t=output[1]

        rg=float(rgt[rgt.find('=')+1:rgt.find('/')-1].strip())
        I0=float(I0t[I0t.find('=')+1:I0t.find('/')-1].strip())

        rger=float(rgt[rgt.find('/')+2:rgt.find('(')].strip())
        I0er=float(I0t[I0t.find('/')+2:].strip())

    else:
        rg=-1
        I0=-1
        rger=-1
        I0er=-1


    return rg, rger, I0, I0er


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



