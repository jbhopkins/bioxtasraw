"""
Created on March 17, 2020

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

This file contains functions used in several places in the program that don't really
fit anywhere else.
"""

from __future__ import absolute_import, division, print_function, unicode_literals
from builtins import object, range, map, zip
from io import open

import copy

import pyFAI

def get_det_list():

    extra_det_list = ['detector']

    final_dets = pyFAI.detectors.ALL_DETECTORS

    for key in extra_det_list:
        if key in final_dets:
            final_dets.pop(key)

    for key in copy.copy(list(final_dets.keys())):
        if '_' in key:
            reduced_key = ''.join(key.split('_'))
            if reduced_key in final_dets:
                final_dets.pop(reduced_key)

    det_list = list(final_dets.keys()) + [str('Other')]
    det_list = sorted(det_list, key=str.lower)

    return det_list
