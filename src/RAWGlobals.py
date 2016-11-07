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
usepyFAI = False