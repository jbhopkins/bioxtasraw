import Queue

global compiled_extensions 
compiled_extensions = True

global mainworker_cmd_queue
mainworker_cmd_queue = Queue.Queue()

global cancel_bift
cancel_bift = False