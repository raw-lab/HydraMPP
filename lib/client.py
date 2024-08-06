import pickle
import socket
import multiprocessing as mp

from .log import *
from .net import *


def client_init(address, port, num_cpus):
	sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	try:
		sock.connect((address, port))
	except:
		printlog("CLIENT ERROR: unable to connect to host:", address, port)
		return False
	try:
		printlog("CLIENT INFO: Securing connection")
		sock.send(f"cpus:{num_cpus},hostname:{socket.gethostname()}".encode("utf-8"))
	except Exception as e:
		printlog("CLIENT ERROR:", e)
		return False
	return sock
