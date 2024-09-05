

import sys
import traceback
from io import StringIO
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

def printerr(e):
	io = StringIO()
	traceback.print_exception(e, file=io)
	for line in io.getvalue().splitlines():
		printlog(">", line)
