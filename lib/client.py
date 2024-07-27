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


def client_listen(sock:socket.socket, WORKERS:dict):
	def __worker(func, id, sock, args, kwargs):
		start = time.time()
		ret = None
		try:
			ret = func(*args, **kwargs)
		except Exception as e:
			printlog("CLIENT ERROR REMOTE:", id, func)
			printlog(e)
		finally:
			packet = {id:[func.__name__, ret, time.time()-start]}
			send_msg(sock, pickle.dumps(packet))
		return

	# Listening Loop
	while is_connected(sock):
		msg = recv_msg(sock)
		if msg:
			(id,(func_name, args, kwargs, num_cpus)), = pickle.loads(msg).items()
			func = WORKERS[func_name]
			mp.Process(target=__worker, args=[func, id, sock, args, kwargs]).start()
		time.sleep(0.1)

	sock.close()

	printlog("INFO: Host disconnected")
	printlog("INFO: Terminating program")
	return
