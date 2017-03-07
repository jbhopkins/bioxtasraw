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

import Queue
import sys
import os

global compiled_extensions
compiled_extensions = True

global mainworker_cmd_queue
mainworker_cmd_queue = Queue.Queue()

global cancel_bift
cancel_bift = False

global workspace_saved
workspace_saved = True

global frozen

#Checks whether RAW is running in a compiled (frozen) version or a live interpreter
if getattr(sys, 'frozen', False):
    frozen = True
else:
    frozen = False

global RAWWorkDir
RAWWorkDir = sys.path[0]

if os.path.split(sys.path[0])[1] in ['RAW.exe', 'raw.exe']:
    RAWWorkDir = os.path.split(sys.path[0])[0]

global usepyFAI
# usepyFAI = True

global usepyFAI_integration
usepyFAI_integration = False

global version
version = '1.2.2'
