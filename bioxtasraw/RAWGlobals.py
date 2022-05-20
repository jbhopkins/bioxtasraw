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

from __future__ import absolute_import, division, print_function, unicode_literals
from builtins import object, range, map, zip
from io import open

try:
    import queue
except Exception:
    import Queue as queue

import sys
import os

try:
    import pyopencl
    has_pyopencl = True
except Exception:
    has_pyopencl = False

try:
    import wx
    has_wx = True
except Exception:
    has_wx = False #Installed as API

raw_path = os.path.abspath(os.path.join('.', __file__, '..', '..'))
if raw_path not in os.sys.path:
    os.sys.path.append(raw_path)

import bioxtasraw

mainworker_cmd_queue = queue.Queue()

#Checks whether RAW is running in a compiled (frozen) version or a live interpreter
if getattr(sys, 'frozen', False):
    frozen = True
else:
    frozen = False

RAWWorkDir = ''
RAWResourcesDir = ''
RAWDefinitionsDir = ''
RAWDocsDir = ''

usepyFAI_integration = True

version = bioxtasraw.__version__ #Defined in __init__.py

save_in_progress = False

if has_wx:
    highlight_color = wx.Colour(178, 215, 255)
    general_text_color = 'black'
    list_bkg_color = 'white'
    list_item_bkg_color = 'white'
    tab_color = 'white'
    bift_item_color = 'blue'