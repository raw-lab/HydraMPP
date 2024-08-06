import pickle
import socket
import multiprocessing as mp

from .log import *
from .net import *

MANAGER = mp.Manager()

def host_start(NODES:list, timeout=5):
	h_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	h_socket.settimeout(0.5)
	h_socket.bind(("", port))
	h_socket.listen(10)
	NODES[0]['socket'] = h_socket
	start = time.time()
	printlog("HOST INFO: waiting for clients")
	hostnames = set()
	for node in NODES:
		if "hostname" in node:
			hostnames.add(node['hostname'])
	while time.time() < start+timeout:
		try:
			(sock, (addr, port)) = h_socket.accept()
			printlog("HOST Accepted connection from:", addr)
			msg = sock.recv(1024).decode("utf-8")
			match = re.search(r'cpus:(\d+),hostname:(.+)', msg)
			if match:
				cpus = int(match.group(1))
				hostname = match.group(2)
			else:
				printlog("HOST ERROR: bad handshake from client")
				break
			re_add = re.compile(r'\((\d+)\)$')
			while hostname in hostnames:
				match = re_add.search(hostname)
				if match:
					d = int(match.group(1)) + 1
					hostname = re_add.sub(f"({d})", hostname)
				else:
					hostname += "(1)"
			hostnames.add(hostname)
			NODES += [MANAGER.dict(
				hostname = hostname,
				address = addr,
				socket = sock,
				cpus = cpus,
				num_cpus = cpus
			)]
		except socket.timeout:
			pass
		except Exception as e:
			printlog("HOST ERROR: Socket error")
			printlog(e)
	return True
