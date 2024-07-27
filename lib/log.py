

import sys
import time
import socket

def get_time():
	now = time.localtime()
	return f"{now[3]}:{now[4]}:{now[5]}"

def printlog(*args, **kwargs):
	if "file" in kwargs:
		print(f"HYDRA {get_time()} [{socket.gethostname()}]:\t", *args, **kwargs)
	else:
		print(f"HYDRA {get_time()} [{socket.gethostname()}]:\t", *args, **kwargs, file=sys.stderr)
	return
