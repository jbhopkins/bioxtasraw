'''
Created on Nov 29, 2018

@author: Jesse Hopkins

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

This file contains basic functions for processing on one more or scattering profile,
including averaging, subtracting, and merging.
'''

from __future__ import absolute_import, division, print_function, unicode_literals
from builtins import object, range, map, zip
from io import open

import copy

import numpy as np
import scipy.interpolate as interp

import SASExceptions
import SASM


def subtract(sasm1, sasm2, forced = False, full = False):
    ''' Subtract one SASM object from another and propagate errors '''
    if not full:
        q1_min, q1_max = sasm1.getQrange()
        q2_min, q2_max = sasm2.getQrange()
    else:
        q1_min = 0
        q1_max = len(sasm1.q)+1
        q2_min = 0
        q2_max = len(sasm2.q)+1

    if not np.all(np.round(sasm1.q[q1_min:q1_max],5) == np.round(sasm2.q[q2_min:q2_max],5)) and not forced:
        raise SASExceptions.DataNotCompatible('The curves does not have the same q vectors.')

    elif not np.all(np.round(sasm1.q[q1_min:q1_max],5) == np.round(sasm2.q[q2_min:q2_max],5)) and forced:
        q1 = np.round(sasm1.q[q1_min:q1_max],5)
        q2 = np.round(sasm2.q[q2_min:q2_max],5)
        i1 = sasm1.i[q1_min:q1_max]
        i2 = sasm2.i[q2_min:q2_max]
        err1 = sasm1.err[q1_min:q1_max]
        err2 = sasm2.err[q2_min:q2_max]

        if q1[0]>q2[0]:
            start=np.round(q1[0],5)
        else:
            start=np.round(q2[0],5)

        if q1[-1]>q2[-1]:
            end=np.round(q2[-1],5)
        else:
            end=np.round(q1[-1],5)

        if start>end:
            raise SASExceptions.DataNotCompatible('Subtraction failed: the curves have no overlapping q region.')

        shifted = False
        if len(np.argwhere(q1==start))>0 and len(np.argwhere(q1==end))>0 and len(np.argwhere(q2==start))>0 and len(np.argwhere(q2==end))>0:
            q1_idx1 = np.argwhere(q1==start)[0][0]
            q1_idx2 = np.argwhere(q1==end)[0][0]+1
            q2_idx1 = np.argwhere(q2==start)[0][0]
            q2_idx2 = np.argwhere(q2==end)[0][0] +1

            if np.all(q1[q1_idx1:q1_idx2]==q2[q2_idx1:q2_idx2]):
                shifted = True

        if shifted:
            i = i1[q1_idx1:q1_idx2] - i2[q2_idx1:q2_idx2]
            err = np.sqrt( np.power(err1[q1_idx1:q1_idx2], 2) + np.power(err2[q2_idx1:q2_idx2],2))

            q = copy.deepcopy(sasm1.q[q1_idx1:q1_idx2])

        else:
            q1space=q1[1]-q1[0]
            q2space=q2[1]-q2[0]

            if q1space>q2space:
                npts=(end-start)//q1space+1
            else:
                npts=(end-start)//q2space+1

            refq=np.linspace(start,end,npts,endpoint=True)

            q1_idx1 = np.argmin(np.absolute(q1-start))
            q1_idx2 = np.argmin(np.absolute(q1-end))+1
            q2_idx1 = np.argmin(np.absolute(q2-start))
            q2_idx2 = np.argmin(np.absolute(q2-end))+1

            q1b, i1b, err1b=binfixed(sasm1.q[q1_idx1:q1_idx2], i1[q1_idx1:q1_idx2], err1[q1_idx1:q1_idx2], refq=refq)
            q2b, i2b, err2b=binfixed(sasm2.q[q2_idx1:q2_idx2], i2[q2_idx1:q2_idx2], err2[q2_idx1:q2_idx2], refq=refq)

            i = i1b - i2b
            err=np.sqrt(np.square(err1b)+np.square(err2b))

            q = refq

    else:
        i = sasm1.i[q1_min:q1_max] - sasm2.i[q2_min:q2_max]

        q = copy.deepcopy(sasm1.q)[q1_min:q1_max]
        err = np.sqrt( np.power(sasm1.err[q1_min:q1_max], 2) + np.power(sasm2.err[q2_min:q2_max],2))

    parameters = copy.deepcopy(sasm1.getAllParameters())
    sub_parameters = get_shared_header([sasm1, sasm2])
    newSASM = SASM.SASM(i, q, err, sub_parameters)
    newSASM.setParameter('filename', parameters['filename'])

    history = newSASM.getParameter('history')

    history = {}

    history1 = []
    history1.append(copy.deepcopy(sasm1.getParameter('filename')))
    for key in sasm1.getParameter('history'):
        history1.append({ key : copy.deepcopy(sasm1.getParameter('history')[key])})

    history2 = []
    history2.append(copy.deepcopy(sasm2.getParameter('filename')))
    for key in sasm2.getParameter('history'):
        history2.append({key : copy.deepcopy(sasm2.getParameter('history')[key])})

    history['subtraction'] = {'initial_file':history1, 'subtracted_file':history2}

    newSASM.setParameter('history', history)

    return newSASM

def average(sasm_list, forced = False):
    ''' Average the intensity of a list of sasm objects '''

    if len(sasm_list) == 1:
        #Useful for where all but the first profile are rejected due to similarity
        #testing. Otherwise we should never have less than one profile to average
        sasm = sasm_list[0]
        q_min, q_max = sasm.getQrange()

        avg_q = copy.deepcopy(sasm.q[q_min:q_max])
        avg_i = copy.deepcopy(sasm.i[q_min:q_max])
        avg_err = copy.deepcopy(sasm.err[q_min:q_max])
        avg_parameters = copy.deepcopy(sasm.getAllParameters())

        avgSASM = SASM.SASM(avg_i, avg_q, avg_err, avg_parameters)

        history = {}
        history_list = []
        for eachsasm in sasm_list:
            each_history = []
            each_history.append(copy.deepcopy(eachsasm.getParameter('filename')))

            for key in eachsasm.getParameter('history'):
                each_history.append({key : copy.deepcopy(eachsasm.getParameter('history')[key])})

            history_list.append(each_history)


        history['averaged_files'] = history_list
        avgSASM.setParameter('history', history)

    else:
        #Check average is possible with provided curves:
        first_sasm = sasm_list[0]
        first_q_min, first_q_max = first_sasm.getQrange()

        for each in sasm_list:
            each_q_min, each_q_max = each.getQrange()
            if not np.all(np.round(each.q[each_q_min:each_q_max], 5) == np.round(first_sasm.q[first_q_min:first_q_max], 5)) and not forced:
                raise SASExceptions.DataNotCompatible('Average list contains data sets with different q vectors.')

        all_i = first_sasm.i[first_q_min : first_q_max]

        all_err = first_sasm.err[first_q_min : first_q_max]

        avg_filelist = []
        avg_filelist.append(first_sasm.getParameter('filename'))

        for idx in range(1, len(sasm_list)):
            each_q_min, each_q_max = sasm_list[idx].getQrange()
            all_i = np.vstack((all_i, sasm_list[idx].i[each_q_min:each_q_max]))
            all_err = np.vstack((all_err, sasm_list[idx].err[each_q_min:each_q_max]))
            avg_filelist.append(sasm_list[idx].getParameter('filename'))

        avg_i = np.mean(all_i, 0)

        avg_err = np.sqrt( np.sum( np.power(all_err,2), 0 ) ) / len(all_err)  #np.sqrt(len(all_err))

        avg_i = copy.deepcopy(avg_i)
        avg_err = copy.deepcopy(avg_err)

        avg_q = copy.deepcopy(first_sasm.q)[first_q_min:first_q_max]
        avg1_parameters = copy.deepcopy(sasm_list[0].getAllParameters())

        avg_parameters = get_shared_header(sasm_list)

        avgSASM = SASM.SASM(avg_i, avg_q, avg_err, avg_parameters)
        avgSASM.setParameter('filename', avg1_parameters['filename'])

        history = {}

        history_list = []

        for eachsasm in sasm_list:
            each_history = []
            each_history.append(copy.deepcopy(eachsasm.getParameter('filename')))

            for key in eachsasm.getParameter('history'):
                each_history.append({key : copy.deepcopy(eachsasm.getParameter('history')[key])})

            history_list.append(each_history)

        history['averaged_files'] = history_list
        avgSASM.setParameter('history', history)

    return avgSASM

def weightedAverage(sasm_list, weightByError, weightCounter, forced = False):
    ''' Weighted average of the intensity of a list of sasm objects '''
    if len(sasm_list) == 1:
        #Useful for where all but the first profile are rejected due to similarity
        #testing. Otherwise we should never have less than one profile to average
        sasm = sasm_list[0]
        q_min, q_max = sasm.getQrange()

        avg_q = copy.deepcopy(sasm.q[q_min:q_max])
        avg_i = copy.deepcopy(sasm.i[q_min:q_max])
        avg_err = copy.deepcopy(sasm.err[q_min:q_max])
        avg_parameters = copy.deepcopy(sasm.getAllParameters())

        avgSASM = SASM.SASM(avg_i, avg_q, avg_err, avg_parameters)

        history = {}
        history_list = []
        for eachsasm in sasm_list:
            each_history = []
            each_history.append(copy.deepcopy(eachsasm.getParameter('filename')))

            for key in eachsasm.getParameter('history'):
                each_history.append({key : copy.deepcopy(eachsasm.getParameter('history')[key])})

            history_list.append(each_history)


        history['averaged_files'] = history_list
        avgSASM.setParameter('history', history)

    else:
        #Check average is possible with provided curves:
        first_sasm = sasm_list[0]
        first_q_min, first_q_max = first_sasm.getQrange()

        for each in sasm_list:
            each_q_min, each_q_max = each.getQrange()
            if not np.all(np.round(each.q[each_q_min:each_q_max], 5) == np.round(first_sasm.q[first_q_min:first_q_max], 5)) and not forced:
                raise SASExceptions.DataNotCompatible('Average list contains data sets with different q vectors.')

        all_i = first_sasm.i[first_q_min : first_q_max]
        all_err = first_sasm.err[first_q_min : first_q_max]

        if not weightByError:
            if 'counters' in first_sasm.getAllParameters():
                file_hdr = first_sasm.getParameter('counters')
            if 'imageHeader' in first_sasm.getAllParameters():
                img_hdr = first_sasm.getParameter('imageHeader')

            if weightCounter in file_hdr:
                all_weight = float(file_hdr[weightCounter])
            else:
                all_weight = float(img_hdr[weightCounter])

        avg_filelist = []
        if not weightByError:
            avg_filelist.append([first_sasm.getParameter('filename'), all_weight])
        else:
            avg_filelist.append([first_sasm.getParameter('filename'), 'error'])

        for idx in range(1, len(sasm_list)):
            each_q_min, each_q_max = sasm_list[idx].getQrange()
            all_i = np.vstack((all_i, sasm_list[idx].i[each_q_min:each_q_max]))
            all_err = np.vstack((all_err, sasm_list[idx].err[each_q_min:each_q_max]))

            if not weightByError:
                if 'counters' in sasm_list[idx].getAllParameters():
                    file_hdr = sasm_list[idx].getParameter('counters')
                if 'imageHeader' in sasm_list[idx].getAllParameters():
                    img_hdr = sasm_list[idx].getParameter('imageHeader')

                if weightCounter in file_hdr:
                    try:
                        all_weight = np.vstack((all_weight, float(file_hdr[weightCounter])))
                    except ValueError:
                        raise SASExceptions.DataNotCompatible('Not all weight counter values were numbers.')

                else:
                    try:
                        all_weight = np.vstack((all_weight, float(img_hdr[weightCounter])))
                    except ValueError:
                        raise SASExceptions.DataNotCompatible('Not all weight counter values were numbers.')

            if not weightByError:
                avg_filelist.append([sasm_list[idx].getParameter('filename'), all_weight])
            else:
                avg_filelist.append([sasm_list[idx].getParameter('filename'), 'error'])

        if not weightByError:
            weight = all_weight.flatten()
            avg_i = np.average(all_i, axis=0, weights=weight)
            avg_err = np.sqrt(np.average(np.square(all_err), axis=0, weights=np.square(weight)))
        else:
            all_err = 1/(np.square(all_err))
            avg_i = np.average(all_i, axis=0, weights = all_err)
            avg_err = np.sqrt(1/np.sum(all_err,0))

        avg_i = copy.deepcopy(avg_i)
        avg_err = copy.deepcopy(avg_err)

        avg_q = copy.deepcopy(first_sasm.q)[first_q_min:first_q_max]
        avg1_parameters = copy.deepcopy(sasm_list[0].getAllParameters())

        avg_parameters = get_shared_header(sasm_list)

        avgSASM = SASM.SASM(avg_i, avg_q, avg_err, avg_parameters)
        avgSASM.setParameter('filename', avg1_parameters['filename'])
        history = avgSASM.getParameter('history')

        history = {}

        history_list = []

        for eachsasm in sasm_list:
            each_history = []
            each_history.append(copy.deepcopy(eachsasm.getParameter('filename')))

            for key in eachsasm.getParameter('history'):
                each_history.append({key : copy.deepcopy(eachsasm.getParameter('history')[key])})

            history_list.append(each_history)


        history['weighted_averaged_files'] = history_list
        avgSASM.setParameter('history', history)

    return avgSASM


def superimpose(sasm_star, sasm_list, choice):
    """
    Find the scale and/or offset factor between a reference curve and the
    curves of interest.
    The reference curve need not be sampled at the same q-space points.

    """

    q_star = sasm_star.q
    i_star = sasm_star.i
    # err_star = sasm_star.err

    q_star_qrange_min, q_star_qrange_max = sasm_star.getQrange()

    q_star = q_star[q_star_qrange_min:q_star_qrange_max]
    i_star = i_star[q_star_qrange_min:q_star_qrange_max]

    for each_sasm in sasm_list:

        each_q = each_sasm.getBinnedQ()
        each_i = each_sasm.getBinnedI()
        # each_err = each_sasm.getBinnedErr()

        each_q_qrange_min, each_q_qrange_max = each_sasm.getQrange()

        # resample standard curve on the data q vector
        min_q_each = each_q[each_q_qrange_min]
        max_q_each = each_q[each_q_qrange_max-1]

        min_q_idx = np.where(q_star >= min_q_each)[0][0]
        max_q_idx = np.where(q_star <= max_q_each)[0][-1]

        if np.all(q_star[min_q_idx:max_q_idx+1] != each_q[each_q_qrange_min:each_q_qrange_max]):
            I_resamp = np.interp(q_star[min_q_idx:max_q_idx+1],
                                 each_q[each_q_qrange_min:each_q_qrange_max],
                                 each_i[each_q_qrange_min:each_q_qrange_max])
        else:
            I_resamp = each_i[each_q_qrange_min:each_q_qrange_max]

        if not np.all(I_resamp ==i_star):
            if choice == 'Scale and Offset':
                A = np.column_stack([I_resamp, np.ones_like(I_resamp)])
                scale, offset = np.linalg.lstsq(A, i_star[min_q_idx:max_q_idx+1])[0]
            elif choice == 'Scale':
                A = np.column_stack([I_resamp, np.zeros_like(I_resamp)])
                scale, offset= np.linalg.lstsq(A, i_star[min_q_idx:max_q_idx+1])[0]
                offset = 0
            elif choice == 'Offset':
                A = np.column_stack([np.zeros_like(I_resamp), np.ones_like(I_resamp)])
                scale, offset= np.linalg.lstsq(A, i_star[min_q_idx:max_q_idx+1]-I_resamp)[0]
                scale = 1

            each_sasm.scale(scale)
            each_sasm.offset(offset)


def merge(sasm_star, sasm_list):

    """ Merge one or more sasms by averaging and possibly interpolating
    points if all values are not on the same q scale """

    #Sort sasms according to lowest q value:
    sasm_list.extend([sasm_star])
    sasm_list = sorted(sasm_list, key=lambda each: each.q[each.getQrange()[0]])

    s1 = sasm_list[0]
    s2 = sasm_list[1]

    sasm_list.pop(0)
    sasm_list.pop(0)

    #find overlapping s2 points
    highest_q = s1.q[s1.getQrange()[1]-1]
    min, max = s2.getQrange()
    overlapping_q2 = s2.q[min:max][np.where(s2.q[min:max] <= highest_q)]

    #find overlapping s1 points
    lowest_s2_q = s2.q[s2.getQrange()[0]]
    min, max = s1.getQrange()
    overlapping_q1 = s1.q[min:max][np.where(s1.q[min:max] >= lowest_s2_q)]

    tmp_s2i = s2.i.copy()
    tmp_s2q = s2.q.copy()
    tmp_s2err = s2.err.copy()

    if len(overlapping_q1) == 1 and len(overlapping_q2) == 1: #One point overlap
        q1idx = s1.getQrange()[1]
        q2idx = s2.getQrange()[0]

        avg_i = (s1.i[q1idx] + s2.i[q2idx])/2.0

        tmp_s2i[q2idx] = avg_i

        minq, maxq = s1.getQrange()
        q1_indexs = [maxq-1, minq]

    elif len(overlapping_q1) == 0 and len(overlapping_q2) == 0: #No overlap
        minq, maxq = s1.getQrange()
        q1_indexs = [maxq, minq]

    else:   #More than 1 point overlap

        added_index = False
        if overlapping_q2[0] < overlapping_q1[0]:
            #add the point before overlapping_q1[0] to overlapping_q1
            idx, = np.where(s1.q == overlapping_q1[0])
            overlapping_q1 = np.insert(overlapping_q1, 0, s1.q[idx-1][0])
            added_index = True

        #get indexes for overlapping_q2 and q1
        q2_indexs = []
        q1_indexs = []

        for each in overlapping_q2:
            idx, = np.where(s2.q == each)
            q2_indexs.append(idx[0])

        for each in overlapping_q1:
            idx, = np.where(s1.q == each)
            q1_indexs.append(idx[0])

        #interpolate overlapping s2 onto s1
        f = interp.interp1d(s1.q[q1_indexs], s1.i[q1_indexs])
        intp_I = f(s2.q[q2_indexs])
        averaged_I = (intp_I + s2.i[q2_indexs])/2.0

        if added_index:
            q1_indexs = np.delete(q1_indexs, 0)

        tmp_s2i[q2_indexs] = averaged_I


    #Merge the two parts
    #cut away the overlapping part on s1 and append s2 to it
    min, max = s1.getQrange()
    newi = s1.i[min:q1_indexs[0]]
    newq = s1.q[min:q1_indexs[0]]
    newerr = s1.err[min:q1_indexs[0]]

    min, max = s2.getQrange()
    newi = np.append(newi, tmp_s2i[min:max])
    newq = np.append(newq, tmp_s2q[min:max])
    newerr = np.append(newerr, tmp_s2err[min:max])

    #create a new SASM object with the merged parts.
    merge1_parameters = copy.deepcopy(s1.getAllParameters())

    merge_parameters = get_shared_header([s1, s2])

    newSASM = SASM.SASM(newi, newq, newerr, merge_parameters)
    newSASM.setParameter('filename', merge1_parameters['filename'])

    history = newSASM.getParameter('history')

    history = {}

    history_list = []

    for eachsasm in [s1, s2]:
        each_history = []
        each_history.append(copy.deepcopy(eachsasm.getParameter('filename')))
        for key in eachsasm.getParameter('history'):
            each_history.append({key : copy.deepcopy(eachsasm.getParameter('history')[key])})

        history_list.append(each_history)

    history['merged_files'] = history_list
    newSASM.setParameter('history', history)

    if len(sasm_list) == 0:
        return newSASM
    else:
        return merge(newSASM, sasm_list)

def interpolateToFit(sasm_star, sasm):
    s1 = sasm_star
    s2 = sasm

    #find overlapping s2 points
    min_q1, max_q1 = s1.getQrange()
    min_q2, max_q2 = s2.getQrange()

    lowest_q1, highest_q1 = s1.q[s1.getQrange()[0]], s1.q[s1.getQrange()[1]-1]

    #fuck hvor besvaerligt!
    overlapping_q2_top = s2.q[min_q2:max_q2][np.where( (s2.q[min_q2:max_q2] <= highest_q1))]
    overlapping_q2 = overlapping_q2_top[np.where(overlapping_q2_top >= lowest_q1)]

    if overlapping_q2[0] != s2.q[0]:
        idx = np.where(s2.q == overlapping_q2[0])
        overlapping_q2 = np.insert(overlapping_q2, 0, s2.q[idx[0]-1])

    if overlapping_q2[-1] != s2.q[-1]:
        idx = np.where(s2.q == overlapping_q2[-1])
        overlapping_q2 = np.append(overlapping_q2, s2.q[idx[0]+1])

    overlapping_q1_top = s1.q[min_q1:max_q1][np.where( (s1.q[min_q1:max_q1] <= overlapping_q2[-1]))]
    overlapping_q1 = overlapping_q1_top[np.where(overlapping_q1_top >= overlapping_q2[0])]

    q2_indexs = []
    q1_indexs = []
    for each in overlapping_q2:
        idx, = np.where(s2.q == each)
        q2_indexs.append(idx[0])

    for each in overlapping_q1:
        idx, = np.where(s1.q == each)
        q1_indexs.append(idx[0])

    #interpolate find the I's that fits the q vector of s1:
    f = interp.interp1d(s2.q[q2_indexs], s2.i[q2_indexs])

    intp_i_s2 = f(s1.q[q1_indexs])
    intp_q_s2 = s1.q[q1_indexs].copy()
    newerr = s1.err[q1_indexs].copy()

    parameters = copy.deepcopy(s1.getAllParameters())

    newSASM = SASM.SASM(intp_i_s2, intp_q_s2, newerr, parameters)

    history = newSASM.getParameter('history')

    history = {}

    history1 = []
    history1.append(copy.deepcopy(s1.getParameter('filename')))
    for key in s1.getParameter('history'):
        history1.append({key:copy.deepcopy(s1.getParameter('history')[key])})

    history2 = []
    history2.append(copy.deepcopy(s2.getParameter('filename')))
    for key in s2.getParameter('history'):
        history2.append({key:copy.deepcopy(s2.getParameter('history')[key])})

    history['interpolation'] = {'initial_file':history1, 'interpolated_to_q_of':history2}
    newSASM.setParameter('history', history)

    return newSASM

def logBinning(sasm, no_points):

    #if end_idx == -1:
#       end_idx = len(self._i_raw)

    i_roi = sasm._i_binned
    q_roi = sasm._q_binned
    err_roi = sasm._err_binned

    bins = np.logspace(1, np.log10(len(q_roi)), no_points)

    binned_q = []
    binned_i = []
    binned_err = []

    idx = 0
    for i in range(0, len(bins)):
        no_of_bins = int(np.floor(bins[i] - bins[i-1]))

        if no_of_bins > 1:
            mean_q = np.mean( q_roi[ idx : idx + no_of_bins ] )
            mean_i = np.mean( i_roi[ idx : idx + no_of_bins ] )

            mean_err = np.sqrt( sum( np.power( err_roi[ idx : idx + no_of_bins ], 2) ) ) / np.sqrt( no_of_bins )

            binned_q.append(mean_q)
            binned_i.append(mean_i)
            binned_err.append(mean_err)

            idx = idx + no_of_bins
        else:
            binned_q.append(q_roi[idx])
            binned_i.append(i_roi[idx])
            binned_err.append(err_roi[idx])
            idx = idx + 1

    parameters = copy.deepcopy(sasm.getAllParameters())

    newSASM = SASM.SASM(binned_i, binned_q, binned_err, parameters)

    history = newSASM.getParameter('history')

    history = {}

    history1 = []
    history1.append(copy.deepcopy(sasm.getParameter('filename')))

    for key in sasm.getParameter('history'):
        history1.append({key:copy.deepcopy(sasm.getParameter('history')[key])})

    history['log_binning'] = {'initial_file' : history1, 'initial_points' : len(q_roi), 'final_points': len(bins)}

    newSASM.setParameter('history', history)

    return newSASM

def rebin(sasm, rebin_factor):
    ''' Sets the bin size of the I_q plot
        end_idx will be lowered to fit the bin_size
        if needed.
    '''

    len_iq = len(sasm._i_binned)

    no_of_bins = int(np.floor(len_iq / rebin_factor))

    end_idx = no_of_bins * rebin_factor

    start_idx = 0
    i_roi = sasm._i_binned[start_idx:end_idx]
    q_roi = sasm._q_binned[start_idx:end_idx]
    err_roi = sasm._err_binned[start_idx:end_idx]

    new_i = np.zeros(no_of_bins)
    new_q = np.zeros(no_of_bins)
    new_err = np.zeros(no_of_bins)

    for eachbin in range(0, no_of_bins):
        first_idx = eachbin * rebin_factor
        last_idx = (eachbin * rebin_factor) + rebin_factor

        new_i[eachbin] = sum(i_roi[first_idx:last_idx]) / rebin_factor
        new_q[eachbin] = sum(q_roi[first_idx:last_idx]) / rebin_factor
        new_err[eachbin] = np.sqrt(sum(np.power(err_roi[first_idx:last_idx],2))) / np.sqrt(rebin_factor)


    parameters = copy.deepcopy(sasm.getAllParameters())

    newSASM = SASM.SASM(new_i, new_q, new_err, parameters)

    qstart, qend = sasm.getQrange()

    new_qstart = int(qstart/float(rebin_factor)+.5)
    new_qend = int(qend/float(rebin_factor))

    newSASM.setQrange([new_qstart, new_qend])

    history = newSASM.getParameter('history')

    history = {}

    history1 = []
    history1.append(copy.deepcopy(sasm.getParameter('filename')))

    for key in sasm.getParameter('history'):
        history1.append({key:copy.deepcopy(sasm.getParameter('history')[key])})

    history['log_binning'] = {'initial_file' : history1, 'initial_points' : len_iq, 'final_points': no_of_bins}

    newSASM.setParameter('history', history)

    return newSASM


def binfixed(q, I, er, refq):
    """
    This function bins the input q, I, and er into the fixed bins of qref
    """
    dq=refq[1]-refq[0]

    qn=np.linspace(refq[0]-dq/2.,refq[-1]+1.5*dq, np.around((refq[-1]+2*dq-refq[0])/dq,0)+1,endpoint=True )


    dig=np.digitize(q,qn)

    In=np.array([I[dig==i].mean() for i in range(1,len(qn)-1)])


    mI = np.ma.masked_equal(I,0)

    Iern=np.array([np.sqrt(np.sum(np.square(er[dig==i]/mI[dig==i])))/len(I[dig==i]) for i in range(1,len(qn)-1)])

    Iern=Iern*In

    qn=refq

    return qn, In, np.nan_to_num(Iern)

def get_shared_header(sasm_list):
    params_list = [sasm.getAllParameters() for sasm in sasm_list]

    shared_params = get_shared_values(params_list)

    if 'analysis' in shared_params:
        del shared_params['analysis']

    return shared_params

def get_shared_values(dict_list):
    shared_keys = set(dict_list[0].keys())


    for params in dict_list[1:]:
        param_keys = set(params.keys())

        shared_keys = shared_keys & param_keys

    shared_params = {}

    for key in shared_keys:
        if isinstance(dict_list[0][key], dict):
            svals = get_shared_values([d[key] for d in dict_list])

            if svals:
                shared_params[key] = svals

        else:
            if all(param[key] == dict_list[0][key] for param in dict_list):
                shared_params[key] = dict_list[0][key]

    return shared_params
