import Queue
import sys
import os

global compiled_extensions 
compiled_extensions = True

global mainworker_cmd_queue
mainworker_cmd_queue = Queue.Queue()

global cancel_bift
cancel_bift = False

global application_path

if getattr(sys, 'frozen', False):
    print 'Frozen'
    application_path = os.path.dirname(sys.executable)
elif __file__:
    application_path = os.path.dirname(__file__)

global RAWWorkDir
RAWWorkDir = sys.path[0]

if os.path.split(sys.path[0])[1] in ['RAW.exe', 'raw.exe']:
    RAWWorkDir = os.path.split(sys.path[0])[0]