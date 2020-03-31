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

try:
    import pyopencl
    has_pyopencl = True
except Exception:
    has_pyopencl = False

import wx

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

version = '2.0.0'

save_in_progress = False

highlight_color = wx.Colour(178, 215, 255)
