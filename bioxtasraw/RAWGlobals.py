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
from future import standard_library
from builtins import object, range, map, zip
from io import open
standard_library.install_aliases()

import queue
import sys

mainworker_cmd_queue = queue.Queue()

#Checks whether RAW is running in a compiled (frozen) version or a live interpreter
if getattr(sys, 'frozen', False):
    frozen = True
else:
    frozen = False

RAWWorkDir = ''
RAWResourcesDir = ''
RAWDefinitionsDir = ''

usepyFAI_integration = False

version = '1.6.0'

save_in_progress = False
