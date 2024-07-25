# -*- coding: utf-8 -*-

"""hydraMPP: Module for Distributed Parallel Processing

Hydra MPP is a Python library for Distributed Parallel Processing.
DPP utilizes multiple nodes/computers to distribute workloads for
faster processing.

Currently this module is compatible as a basic stand in for Ray.
Not all features are fully implemented yet.

Implemented:
local MPP

Not implemented;
DPP
  sockets
  password
  error reporting
  pickle objects
  compression?
  encryption
Error checking
  if more CPUs are requested than available
"""

__version__ = "0.0.1"


import sys
import socket
import atexit
import multiprocessing as mp
import socket
import psutil
import time
from pathlib import Path
import re


## GLOBAL VARIABLES ##
RUNNING = False
manager = mp.Manager()
P = None
CURR_ID = 0
NODES = list()
WORKERS = dict()
QUEUE = manager.dict()


## CLASS ##
class Worker:
	def __init__(self, func):
		self.func = func
		self.num_cpus = 1
		return
	
	def options(self, num_cpus=1):
		self.num_cpus = num_cpus
		return self

	def remote(self, *args, **kwargs):
		def __worker(func, id, args, kwargs):
			start = time.time()
			res = None
			try:
				res = func(*args, **kwargs)
			except Exception as e:
				print("ERROR REMOTE:", id, func)
				print(e)
			finally:
				QUEUE[id] = [True, func.__name__, res, time.time()-start, socket.gethostname()]
		global CURR_ID
		CURR_ID += 1
		QUEUE[CURR_ID] = [False, self.func.__name__, args, self.num_cpus]
		p = mp.Process(target=__worker, args=[self.func, CURR_ID, args, kwargs])
		cpus = sum([x[3] for x in QUEUE.values() if not x[0]])
		while NODES[0]['num_cpus'] < cpus:
			time.sleep(0.001)
			cpus = sum([x[3] for x in QUEUE.values() if not x[0]])
		p.start()
		self.num_cpus = 1
		return CURR_ID


## METHODS ##
def init(address="local", num_cpus=None, log_to_driver=False, timeout=5, port=24515):
	def is_ip(a,p):
		return True #TODO: Actually check for valid ip address format
	global P
	global NODES
	global RUNNING
	if RUNNING:
		print("WARNING: Hydra MPP Already running")
		return
	RUNNING = True
	print("INFO: Workers Available:")
	for k,v in WORKERS.items():
		print("",v,k, sep='\t')
	if not num_cpus:
		num_cpus = psutil.cpu_count()
	NODES = [dict(
		num_cpus = num_cpus,
		temp = Path("tmp-hydra"),
		ObjectStoreSocketName = Path("tmp-hydra", "current", "objects"))]
	NODES[0]['temp'].mkdir(parents=True, exist_ok=True)
	print("Starting Hydra DPP (Distributed Parallel Processing)")
	print("CPUS:", NODES[0]['num_cpus'])

	# Network connection
	print("Connecting to:", address)
	if address == "local":
		print("INFO: local path")
		NODES[0]['address'] = "local"
	elif address == "host":
		print("INFO: host path")
		NODES[0]['address'] = "host"
		h_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		h_socket.settimeout(0.5)
		h_socket.bind(("", port))
		h_socket.listen(5)
		start = time.time()
		print("INFO: waiting for clients")
		while time.time() < start+timeout:
			try:
				(sock, (addr, port)) = h_socket.accept()
				print("Accepted connection from:", addr)
				msg = sock.recv(1024).decode("utf-8")
				cpus = re.search(r'cpus:(\d+)', msg)
				if cpus:
					print("RECEIVED:", cpus)
					cpus = int(cpus.group(1))
				else:
					print("ERROR: bad handshake from client")
					break
				NODES += [dict(
					address = addr,
					socket = sock,
					num_cpus = cpus
				)]
			except socket.timeout:
				pass
			except Exception as e:
				print("ERROR: Socket error")
				print(e)
	elif is_ip(address, port):
		print("INFO: client path")
		NODES[0]['address'] = address
		NODES[0]['socket'] = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		try:
			NODES[0]['socket'].connect((address, port))
		except:
			print("ERROR: unable to connect to host:", address, port)
		try:
			print("INFO: sending CPU count")
			NODES[0]['socket'].send(f"cpus:{num_cpus}".encode("utf-8"))
		except Exception as e:
			print("ERROR:", e)
		msg = NODES[0]['socket'].recv(1024)
		while(msg):
			msg = NODES[0]['socket'].recv(1024)
			time.sleep(0.01)
		print("INFO: Host disconnected")
		print("INFO: Terminating program")
		sys.exit(0)
	else:
		print("ERROR: address needs to be one of 'local', 'host', or an ip-address of a host to connect to.")
		return False

	P = mp.Process(target=main_loop)
	P.start()
	return True

def main_loop():
	start = time.time()
	while RUNNING:
		time.sleep(0.001)
		if time.time() > start+1:
			with open(NODES[0]["temp"]/"queue.log", 'w') as writer:
				print("QUEUE:", NODES[0]['num_cpus'], file=writer)
				for k,v in QUEUE.items():
					try:
						now = time.localtime()
						print(f"{now[3]}:{now[4]}:{now[5]}", file=writer)
						print(f"{k}\t{v[2]}", file=writer)
						print(f"{v[3]}\t{v[1]}", file=writer)
					except Exception as e:
						#print("QUEUE ERROR:", k, v)
						print(e)
						pass
				start = time.time()
	return

def nodes():
	return NODES

def get(id:int):
	if QUEUE[id][0]:
		return QUEUE.pop(id)[1:]
	else:
		return QUEUE[id]

def put(name:str, obj:tuple):
	global CURR_ID
	CURR_ID += 1
	QUEUE[CURR_ID] = [True, name, obj, 0, socket.gethostname()]
	return CURR_ID

def wait(objects:list, timeout=0, max=1):
	ready = list()
	objects = list(objects)
	start = time.time()
	while objects and len(ready) < max:
		time.sleep(0.001)
		for i in range(len(objects)):
			id = objects[i]
			if QUEUE[id][0]:
				ready += [objects.pop(i)]
				break
		if time.time() < start+timeout:
			break
	return ready, objects

def remote(func):
	worker = Worker(func)
	WORKERS[func.__name__] = worker
	return worker

def shutdown():
	global RUNNING
	if not RUNNING:
		return
	RUNNING = False
	print("Hydra DMPP: Shutdown")
	try:
		P.kill()
		P.join()
	except: pass
	manager.shutdown()
	#if self.paccept:
	#	self.paccept.kill()
	for p in mp.active_children():
		p.kill()
	#for id,p in self.procs.items():
	#	p.kill()
	#print(self.curr_id)
	time.sleep(1)
	return

atexit.register(shutdown)
